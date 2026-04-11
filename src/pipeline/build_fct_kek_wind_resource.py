"""
build_fct_kek_wind_resource — wind speed and CF at centroid and best-within-50km for each KEK.

Sources:
    processed: dim_kek.csv                       KEK centroids (lat/lon)
    data/wind/IDN_wind-speed_100m.tif            Global Wind Atlas v3, mean wind speed at 100m

Output columns:
    kek_id                      slug from dim_kek — join key
    kek_name                    display name
    latitude                    centroid latitude
    longitude                   centroid longitude
    wind_speed_centroid_ms      mean wind speed at centroid (m/s)
    wind_speed_best_50km_ms     max mean wind speed within 50km radius (m/s)
    cf_wind_centroid             capacity factor at centroid (from empirical lookup)
    cf_wind_best_50km            capacity factor best within 50km
    wind_class                  IEC wind class: "I" (>8.5), "II" (7.5-8.5), "III" (<7.5)
    wind_source                 "GlobalWindAtlas-v3"

Wind speed → CF conversion:
    Empirical piecewise linear lookup calibrated to ESDM catalogue (p.90):
    Class III turbine, CF=27% at ~7.5 m/s (catalogue central value).
    See wind_speed_to_cf() in src/model/basic_model.py.

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
from src.pipeline.buildability_filters import compute_distance_mask_km

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


# ─── Builder ──────────────────────────────────────────────────────────────────


def build_fct_kek_wind_resource(
    wind_tif: Path = WIND_TIF,
    kek_csv: Path = DIM_KEK_CSV,
) -> pd.DataFrame:
    """Extract wind speed and CF at centroid and best-within-50km for all KEKs.

    Reads the Global Wind Atlas GeoTIFF directly (no zip).
    Converts wind speed to capacity factor via empirical lookup.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    kek_df = pd.read_csv(kek_csv)

    if not wind_tif.exists():
        raise FileNotFoundError(
            f"Wind GeoTIFF not found: {wind_tif}\n"
            "Download from globalwindatlas.info and place in data/wind/"
        )

    # ─── STAGING + TRANSFORM ──────────────────────────────────────────────────
    records = []
    with rasterio.open(wind_tif) as src:
        arr = src.read(1)
        for _, row in kek_df.iterrows():
            lat = float(row["latitude"])
            lon = float(row["longitude"])

            ws_centroid = _sample_centroid(src, arr, lon, lat)
            ws_best = _sample_best_50km(src, lon, lat)

            cf_c = wind_speed_to_cf(ws_centroid) if np.isfinite(ws_centroid) else np.nan
            cf_b = wind_speed_to_cf(ws_best) if np.isfinite(ws_best) else np.nan

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
                }
            )

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

    out = PROCESSED / "fct_kek_wind_resource.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nWrote {out.relative_to(REPO_ROOT)}")
    display_cols = [
        "kek_id",
        "wind_speed_centroid_ms",
        "wind_speed_best_50km_ms",
        "cf_wind_centroid",
        "cf_wind_best_50km",
        "wind_class",
    ]
    print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
