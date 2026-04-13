"""
build_fct_kek_wind_resource — wind speed, CF, and buildable area for each KEK.

Sources:
    processed: dim_kek.csv                       KEK centroids (lat/lon)
    data/wind/IDN_wind-speed_100m.tif            Global Wind Atlas v3, mean wind speed at 100m
    data/buildability/                           Shared buildability layers (DEM, forest, peat, land cover)

Output columns:
    kek_id                          slug from dim_kek — join key
    kek_name                        display name
    latitude                        centroid latitude
    longitude                       centroid longitude
    wind_speed_centroid_ms          mean wind speed at centroid (m/s)
    wind_speed_best_50km_ms         max mean wind speed within 50km radius (m/s)
    cf_wind_centroid                capacity factor at centroid (from empirical lookup)
    cf_wind_best_50km               capacity factor best within 50km
    wind_class                      IEC wind class: "I" (>8.5), "II" (7.5-8.5), "III" (<7.5)
    wind_source                     "GlobalWindAtlas-v3"
    wind_buildable_area_ha          Buildable area for wind within 50km (land-use filtered)
    max_wind_capacity_mwp           = wind_buildable_area_ha / 25.0 (4 MW/km² spacing)
    wind_buildability_constraint    Dominant constraint: kawasan_hutan/peat/land_cover/slope/low_wind
    wind_speed_buildable_best_ms    Best wind speed among buildable pixels
    cf_wind_buildable_best          CF at best buildable site
    best_wind_site_lat              Latitude of best buildable wind site
    best_wind_site_lon              Longitude of best buildable wind site
    best_wind_site_dist_km          Distance from KEK centroid to best wind site

Wind speed → CF conversion:
    Empirical piecewise linear lookup calibrated to ESDM catalogue (p.90):
    Class III turbine, CF=27% at ~7.5 m/s (catalogue central value).
    See wind_speed_to_cf() in src/model/basic_model.py.

Wind buildability filters (vs solar):
    - Slope: relaxed to 20° (ridgelines ideal for wind speed-up)
    - Cropland: ALLOWED (turbines coexist with agriculture)
    - Min wind speed: 3.0 m/s (below cut-in, no generation)
    - Space: 25 ha/MWp (inter-turbine spacing ~4 MW/km²)
    See wind_buildability_filters.py for full constants.

Methodology reference: ESDM Technology Catalogue 2024, Chapter 4 (Wind Turbines)
50km buffer formula: same as solar — lat_buf = 50/111.32, lon_buf = 50/(111.32×cos(lat_rad))
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

from src.model.basic_model import wind_speed_to_cf
from src.pipeline.assumptions import (
    KM_PER_DEGREE_LAT,
    WIND_BUFFER_KM,
    WIND_SOURCE,
)
from src.pipeline.build_fct_kek_resource import _pixel_area_ha
from src.pipeline.buildability_filters import (
    compute_distance_mask_km,
    haversine_km,
)
from src.pipeline.wind_buildability_filters import WIND_HA_PER_MWP

REPO_ROOT = Path(__file__).resolve().parents[2]
WIND_TIF = REPO_ROOT / "data" / "wind" / "IDN_wind-speed_100m.tif"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"


# ─── Raster extraction helpers ────────────────────────────────────────────────


def _sample_centroid(src: rasterio.DatasetReader, arr: np.ndarray, lon: float, lat: float) -> float:
    """Return the wind speed pixel value at (lon, lat). Returns np.nan if out of bounds."""
    try:
        row, col = src.index(lon, lat)
        if 0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]:
            val = float(arr[row, col])
            return val if np.isfinite(val) and val > 0 else np.nan
        return np.nan
    except Exception:
        return np.nan


def _sample_best_50km(src: rasterio.DatasetReader, lon: float, lat: float) -> float:
    """Return the max valid wind speed within 50km of (lon, lat).

    Uses a bounding-box window for raster extraction, then applies a circular
    haversine mask to exclude corner pixels beyond the true 50km radius.
    """
    lat_buf = WIND_BUFFER_KM / KM_PER_DEGREE_LAT
    lon_buf = WIND_BUFFER_KM / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    window = from_bounds(
        left=lon - lon_buf,
        bottom=lat - lat_buf,
        right=lon + lon_buf,
        top=lat + lat_buf,
        transform=src.transform,
    )
    try:
        patch = src.read(1, window=window)
    except Exception:
        return np.nan

    # Apply circular distance mask — exclude pixels beyond true 50km radius
    win_transform = rasterio.windows.transform(window, src.transform)
    dist_km = compute_distance_mask_km(lat, lon, win_transform, patch.shape)
    patch = np.where(dist_km <= WIND_BUFFER_KM, patch, np.nan)

    valid = patch[(np.isfinite(patch)) & (patch > 0)]
    return float(valid.max()) if len(valid) > 0 else np.nan


def _wind_class(speed_ms: float) -> str:
    """Classify wind speed into IEC wind class."""
    if not np.isfinite(speed_ms):
        return "unknown"
    if speed_ms >= 8.5:
        return "I"
    if speed_ms >= 7.5:
        return "II"
    return "III"


# ─── Wind buildability from pre-built raster ────────────────────────────────

BUILDABLE_WIND_TIF = REPO_ROOT / "outputs" / "assets" / "buildable_wind_web.tif"


def _extract_buildable_from_raster(
    buildable_src: rasterio.DatasetReader,
    lon: float,
    lat: float,
) -> tuple[float, float, float, str, float, float, float]:
    """Extract wind buildability stats for a KEK from the pre-built raster.

    Reads a 50km circular window from buildable_wind_web.tif (produced by
    build_wind_buildable_raster.py). Much faster than re-rasterizing
    shapefiles per-KEK since all exclusion layers are already baked in.

    Returns:
        (wind_speed_buildable_best_ms, wind_buildable_area_ha, max_wind_capacity_mwp,
         constraint_str, best_wind_site_lat, best_wind_site_lon, best_wind_site_dist_km)
    """
    lat_buf = WIND_BUFFER_KM / KM_PER_DEGREE_LAT
    lon_buf = WIND_BUFFER_KM / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    window = from_bounds(
        left=lon - lon_buf,
        bottom=lat - lat_buf,
        right=lon + lon_buf,
        top=lat + lat_buf,
        transform=buildable_src.transform,
    )
    try:
        patch = buildable_src.read(1, window=window)
    except Exception:
        return np.nan, 0.0, 0.0, "data_unavailable", np.nan, np.nan, np.nan

    win_transform = rasterio.windows.transform(window, buildable_src.transform)

    # Apply circular distance mask (50km radius)
    dist_km = compute_distance_mask_km(lat, lon, win_transform, patch.shape)
    patch = np.where(dist_km <= WIND_BUFFER_KM, patch, np.nan)

    # Pixel area at this latitude
    pix_ha = _pixel_area_ha(win_transform, lat)

    buildable = np.isfinite(patch) & (patch > 0)
    n_buildable = int(buildable.sum())

    if n_buildable == 0:
        # Check if there were any raw wind pixels at all
        return np.nan, 0.0, 0.0, "unconstrained", np.nan, np.nan, np.nan

    buildable_area_ha = round(n_buildable * pix_ha, 1)
    max_mwp = round(buildable_area_ha / WIND_HA_PER_MWP, 1)

    # Find best buildable wind pixel and its coordinates
    buildable_ws = np.where(buildable, patch, -np.inf)
    best_idx = np.unravel_index(buildable_ws.argmax(), buildable_ws.shape)
    ws_buildable_best = float(patch[best_idx])
    best_x, best_y = rasterio.transform.xy(win_transform, best_idx[0], best_idx[1], offset="center")
    best_wind_lat = round(float(best_y), 5)
    best_wind_lon = round(float(best_x), 5)
    best_wind_dist_km = round(haversine_km(lat, lon, best_wind_lat, best_wind_lon), 2)

    print(
        f"    buildable: {n_buildable} px, {buildable_area_ha:.0f} ha, "
        f"{max_mwp:.0f} MWp, best={ws_buildable_best:.2f} m/s"
    )

    return (
        ws_buildable_best,
        buildable_area_ha,
        max_mwp,
        "unconstrained",  # constraint detail requires full cascade (run raster builder)
        best_wind_lat,
        best_wind_lon,
        best_wind_dist_km,
    )


# ─── Builder ──────────────────────────────────────────────────────────────────


def build_fct_kek_wind_resource(
    wind_tif: Path = WIND_TIF,
    kek_csv: Path = DIM_KEK_CSV,
) -> pd.DataFrame:
    """Extract wind speed, CF, and buildable area for all KEKs.

    Reads the Global Wind Atlas GeoTIFF directly (no zip).
    Converts wind speed to capacity factor via empirical lookup.
    If buildable_wind_web.tif exists (from build_wind_buildable_raster),
    extracts per-KEK buildability stats from the pre-built raster.
    """

    kek_df = pd.read_csv(kek_csv)

    if not wind_tif.exists():
        raise FileNotFoundError(
            f"Wind GeoTIFF not found: {wind_tif}\n"
            "Download from globalwindatlas.info and place in data/wind/"
        )

    has_buildable = BUILDABLE_WIND_TIF.exists()
    if has_buildable:
        print(f"  Using pre-built buildable raster: {BUILDABLE_WIND_TIF.name}")
    else:
        print("  No pre-built buildable raster. Run build_wind_buildable_raster first.")
        print("  Buildability columns will be empty.")

    records = []
    buildable_ctx = rasterio.open(BUILDABLE_WIND_TIF) if has_buildable else None
    try:
        with rasterio.open(wind_tif) as src:
            arr = src.read(1)
            for _, row in kek_df.iterrows():
                lat = float(row["latitude"])
                lon = float(row["longitude"])

                ws_centroid = _sample_centroid(src, arr, lon, lat)
                ws_best = _sample_best_50km(src, lon, lat)

                cf_c = wind_speed_to_cf(ws_centroid) if np.isfinite(ws_centroid) else np.nan
                cf_b = wind_speed_to_cf(ws_best) if np.isfinite(ws_best) else np.nan

                print(
                    f"  {row['kek_id']}: centroid={ws_centroid:.2f} m/s, best50km={ws_best:.2f} m/s"
                )

                # Buildability from pre-built raster
                if buildable_ctx is not None:
                    (
                        ws_build_best,
                        build_area_ha,
                        build_mwp,
                        build_constraint,
                        best_lat,
                        best_lon_val,
                        best_dist_km,
                    ) = _extract_buildable_from_raster(buildable_ctx, lon, lat)
                else:
                    ws_build_best = np.nan
                    build_area_ha = np.nan
                    build_mwp = np.nan
                    build_constraint = "data_unavailable"
                    best_lat = best_lon_val = best_dist_km = np.nan

                cf_build = wind_speed_to_cf(ws_build_best) if np.isfinite(ws_build_best) else np.nan

                records.append(
                    {
                        "kek_id": row["kek_id"],
                        "kek_name": row["kek_name"],
                        "latitude": lat,
                        "longitude": lon,
                        "wind_speed_centroid_ms": round(ws_centroid, 2)
                        if np.isfinite(ws_centroid)
                        else np.nan,
                        "wind_speed_best_50km_ms": round(ws_best, 2)
                        if np.isfinite(ws_best)
                        else np.nan,
                        "cf_wind_centroid": round(cf_c, 4) if np.isfinite(cf_c) else np.nan,
                        "cf_wind_best_50km": round(cf_b, 4) if np.isfinite(cf_b) else np.nan,
                        "wind_class": _wind_class(ws_best),
                        "wind_source": WIND_SOURCE,
                        "wind_buildable_area_ha": build_area_ha,
                        "max_wind_capacity_mwp": build_mwp,
                        "wind_buildability_constraint": build_constraint,
                        "wind_speed_buildable_best_ms": round(ws_build_best, 2)
                        if np.isfinite(ws_build_best)
                        else np.nan,
                        "cf_wind_buildable_best": round(cf_build, 4)
                        if np.isfinite(cf_build)
                        else np.nan,
                        "best_wind_site_lat": best_lat if np.isfinite(best_lat) else np.nan,
                        "best_wind_site_lon": best_lon_val if np.isfinite(best_lon_val) else np.nan,
                        "best_wind_site_dist_km": best_dist_km
                        if np.isfinite(best_dist_km)
                        else np.nan,
                    }
                )
    finally:
        if buildable_ctx is not None:
            buildable_ctx.close()

    return pd.DataFrame(records)


def main() -> None:
    print(f"Loading KEK centroids from {DIM_KEK_CSV.relative_to(REPO_ROOT)}")
    print(f"Loading wind speed raster from {WIND_TIF.relative_to(REPO_ROOT)}")

    df = build_fct_kek_wind_resource()

    n_miss_c = df["wind_speed_centroid_ms"].isna().sum()
    n_miss_b = df["wind_speed_best_50km_ms"].isna().sum()
    print(f"\nExtracted {len(df)} KEKs")
    print(f"  wind_speed_centroid:  {len(df) - n_miss_c}/{len(df)} valid")
    print(f"  wind_speed_best_50km: {len(df) - n_miss_b}/{len(df)} valid")
    print(
        f"  cf_wind range (best): "
        f"{df['cf_wind_best_50km'].min():.3f} – {df['cf_wind_best_50km'].max():.3f}"
    )
    print(f"  wind class distribution: {df['wind_class'].value_counts().to_dict()}")

    # Buildability summary
    total_build_ha = df["wind_buildable_area_ha"].sum()
    total_build_mwp = df["max_wind_capacity_mwp"].sum()
    n_constrained = (df["wind_buildability_constraint"] != "unconstrained").sum()
    print("\n  Buildability:")
    print(f"    total buildable area: {total_build_ha:,.0f} ha")
    print(f"    total wind capacity:  {total_build_mwp:,.0f} MWp")
    print(f"    constrained KEKs:     {n_constrained}/{len(df)}")
    print(
        f"    constraint breakdown: {df['wind_buildability_constraint'].value_counts().to_dict()}"
    )

    out = PROCESSED / "fct_kek_wind_resource.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nWrote {out.relative_to(REPO_ROOT)}")
    display_cols = [
        "kek_id",
        "wind_speed_best_50km_ms",
        "cf_wind_best_50km",
        "wind_class",
        "wind_buildable_area_ha",
        "max_wind_capacity_mwp",
        "wind_buildability_constraint",
    ]
    print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
