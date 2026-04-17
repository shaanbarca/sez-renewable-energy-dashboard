# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_fct_site_resource — PVOUT at centroid and best-within-50km for each site.

Sources:
    processed: dim_sites.csv                                 site centroids (lat/lon)
    data: Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip
    data/buildability/: optional — Copernicus DEM, KLHK Kawasan Hutan, peatland,
                        and Peta Penutupan Lahan (30m land cover raster).
                        If absent, buildability columns are NaN (graceful degradation).

Output columns (PVOUT values in kWh/kWp/year, CF values unitless 0–1):
    site_id                  slug from dim_sites — join key
    site_name                display name
    latitude                 centroid latitude
    longitude                centroid longitude
    pvout_daily_centroid     raw daily value from GeoTIFF (kWh/kWp/day) — for audit
    pvout_centroid           annual PVOUT at centroid (kWh/kWp/year) = daily × 365
    cf_centroid              capacity factor at centroid = pvout_centroid / 8760
    pvout_daily_best_50km    raw daily max within 50km radius — for audit
    pvout_best_50km          annual PVOUT best within 50km (kWh/kWp/year)
    cf_best_50km             capacity factor best within 50km = pvout_best_50km / 8760
    pvout_source             "GlobalSolarAtlas-v2"
    pvout_buildable_best_50km  annual PVOUT best within 50km after buildability filter
                               NaN if buildability data not present in data/buildability/
    buildable_area_ha          total buildable area within 50km after all filters (ha)
    max_captive_capacity_mwp   buildable_area_ha / 1.5 (1.5 ha/MWp tropical fixed-tilt)
    buildability_constraint    dominant binding constraint:
                               "kawasan_hutan"|"slope"|"peat"|"agriculture"|
                               "area_too_small"|"unconstrained"|"data_unavailable"
    best_solar_site_lat        latitude of the best buildable PVOUT pixel (V2)
                               NaN if buildability data not present
    best_solar_site_lon        longitude of the best buildable PVOUT pixel (V2)
                               NaN if buildability data not present
    within_boundary_area_ha    buildable area within KEK polygon boundary (V2.1)
                               Computed by clipping the 4-layer buildable mask to KEK polygon.
                               Falls back to area_ha × WB_SOLAR_FRACTION when KEK polygon
                               is too small for raster resolution or data is unavailable.
    within_boundary_capacity_mwp  max solar capacity within boundary (V2)
                               = within_boundary_area_ha / 1.5 ha/MWp
    pvout_within_boundary      avg annual PVOUT from buildable pixels within KEK boundary (V2.1)
                               NaN when fallback (theoretical) — uses pvout_centroid instead
    within_boundary_source     "raster" if spatial intersection, "theoretical" if fallback

Methodology reference: METHODOLOGY_CONSOLIDATED.md Sections 2.4 and 2.5, METHODOLOGY_V2.md §2
50km buffer formula: lat_buf = 50/111.32, lon_buf = 50/(111.32×cos(lat_rad))
"""

from __future__ import annotations

import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import rasterio.features
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import unary_union

from src.model.basic_model import pvout_daily_to_annual
from src.pipeline.assumptions import (
    HOURS_PER_YEAR,
    KM_PER_DEGREE_LAT,
    PVOUT_BUFFER_KM,
    PVOUT_SOURCE,
)
from src.pipeline.buildability_filters import (
    HA_PER_MWP,
    LAND_COVER_BUILDABLE_THRESHOLD,
    apply_exclusion_mask,
    apply_min_area_filter,
    apply_road_distance_mask,
    apply_slope_elevation_mask,
    compute_buildability_constraint,
    compute_distance_mask_km,
    compute_slope_degrees,
    haversine_km,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
GEOTIFF_ZIP = (
    REPO_ROOT / "data" / "Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip"
)
PVOUT_TIF_PATH = "Indonesia_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/PVOUT.tif"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DIM_SITES_CSV = PROCESSED / "dim_sites.csv"

# Directory where buildability data files are expected to live.
# Populated by scripts/download_buildability_data.py (see that script for instructions).
BUILDABILITY_DIR = REPO_ROOT / "data" / "buildability"

# KEK polygon boundaries for spatial intersection with buildable raster
KEK_POLYGONS_GEOJSON = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"

_REQUIRED_BUILD_FILES = [
    "dem_indonesia.tif",
    "kawasan_hutan.shp",
    "peatland_klhk.shp",
    "peatland.vrt",
    "esa_worldcover.vrt",
    "road_distance_km.tif",
]


# ─── Raster extraction helpers ────────────────────────────────────────────────


def _load_pvout_tif_bytes() -> bytes:
    """Extract PVOUT.tif bytes from the zip archive."""
    with zipfile.ZipFile(GEOTIFF_ZIP) as z:
        return z.read(PVOUT_TIF_PATH)


def _sample_centroid(src: rasterio.DatasetReader, arr: np.ndarray, lon: float, lat: float) -> float:
    """Return the PVOUT pixel value at (lon, lat). Returns np.nan if out of bounds."""
    try:
        row, col = src.index(lon, lat)
        if 0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]:
            val = float(arr[row, col])
            return val if np.isfinite(val) else np.nan
        return np.nan
    except Exception:
        return np.nan


def _sample_best_50km(src: rasterio.DatasetReader, lon: float, lat: float) -> float:
    """Return the max valid PVOUT daily value within 50km of (lon, lat).

    Uses a bounding-box window for raster extraction, then applies a circular
    haversine mask to exclude corner pixels beyond the true 50km radius.
    """
    lat_buf = PVOUT_BUFFER_KM / KM_PER_DEGREE_LAT
    lon_buf = PVOUT_BUFFER_KM / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
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
    patch = np.where(dist_km <= PVOUT_BUFFER_KM, patch, np.nan)

    valid = patch[np.isfinite(patch)]
    return float(valid.max()) if len(valid) > 0 else np.nan


# ─── Buildability helpers ─────────────────────────────────────────────────────


def _available_build_files(data_dir: Path = BUILDABILITY_DIR) -> set[str]:
    """Return the set of required buildability filenames that currently exist in data_dir.

    Layers with missing files are skipped in _compute_buildable_pvout (pass-through).
    An empty set means no buildability filtering is possible at all.
    """
    return {f for f in _REQUIRED_BUILD_FILES if (data_dir / f).exists()}


def _pixel_area_ha(win_transform: rasterio.transform.Affine, lat: float) -> float:
    """Compute approximate area of one PVOUT pixel in hectares at the given latitude."""
    x_res_deg = abs(win_transform.a)
    y_res_deg = abs(win_transform.e)
    pixel_w_m = x_res_deg * KM_PER_DEGREE_LAT * 1000 * math.cos(math.radians(lat))
    pixel_h_m = y_res_deg * KM_PER_DEGREE_LAT * 1000
    return (pixel_w_m * pixel_h_m) / 10_000


def _rasterize_shp(
    shp_path: Path,
    bbox: tuple[float, float, float, float],
    out_shape: tuple[int, int],
    win_transform: rasterio.transform.Affine,
) -> np.ndarray:
    """Rasterize a vector shapefile to a binary mask matching the PVOUT window.

    Returns:
        uint8 array; 1 = polygon present (excluded), 0 = clear.
        Returns zeros array if shapefile is empty or read fails.
    """
    import geopandas as gpd
    import rasterio.features

    try:
        gdf = gpd.read_file(shp_path, bbox=bbox)
    except Exception as e:
        print(f"  WARNING: Could not read {shp_path.name}: {e}")
        return np.zeros(out_shape, dtype=np.uint8)

    if gdf.empty:
        return np.zeros(out_shape, dtype=np.uint8)

    # Reproject to EPSG:4326 if needed (PVOUT raster is in WGS84)
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    valid_geoms = [geom for geom in gdf.geometry if geom is not None and geom.is_valid]
    if not valid_geoms:
        return np.zeros(out_shape, dtype=np.uint8)

    return rasterio.features.rasterize(
        [(geom, 1) for geom in valid_geoms],
        out_shape=out_shape,
        transform=win_transform,
        fill=0,
        dtype=np.uint8,
    )


def _load_kek_polygons(path: Path) -> dict[str, object]:
    """Return {slug: shapely_geometry} for all KEK polygon features.

    Unions duplicate slugs (e.g. tanjung-sauh has 6 separate MultiPolygons).
    """
    if not path.exists():
        return {}
    with path.open() as f:
        gj = json.load(f)
    polygons: dict[str, object] = {}
    for feat in gj["features"]:
        slug = feat["properties"].get("slug", "")
        if not slug:
            continue
        geom = shape(feat["geometry"])
        if slug in polygons:
            polygons[slug] = unary_union([polygons[slug], geom])
        else:
            polygons[slug] = geom
    return polygons


def _compute_within_boundary_buildable(
    filtered_mask: np.ndarray,
    pvout_patch: np.ndarray,
    win_transform: rasterio.transform.Affine,
    kek_polygon: object,
    pixel_area_ha: float,
    kek_area_ha: float,
) -> tuple[float, float, float]:
    """Clip buildable mask to KEK polygon, return (area_ha, avg_pvout_daily, capacity_mwp).

    Rasterizes the KEK polygon onto the same grid as filtered_mask, then
    intersects to find buildable pixels within the KEK boundary.

    Area is capped at kek_area_ha to prevent inflation when coarse raster
    pixels (~1370 ha each) partially overlap small KEKs.

    Returns (0.0, NaN, 0.0) if no buildable pixels fall within the KEK polygon.
    """
    height, width = filtered_mask.shape

    # Rasterize KEK polygon onto the buildable mask grid
    kek_rasterized = rasterio.features.rasterize(
        [(kek_polygon, 1)],
        out_shape=(height, width),
        transform=win_transform,
        fill=0,
        dtype=np.uint8,
    )

    # Intersect: buildable AND within KEK boundary
    within_kek_buildable = filtered_mask & (kek_rasterized == 1)
    n_pixels = int(within_kek_buildable.sum())

    if n_pixels == 0:
        return 0.0, np.nan, 0.0

    area_ha = round(n_pixels * pixel_area_ha, 1)
    # Cap at actual KEK area: coarse pixels can overcount when they
    # partially overlap a KEK smaller than the pixel itself
    area_ha = round(min(area_ha, kek_area_ha), 1)
    capacity_mwp = round(area_ha / HA_PER_MWP, 1)

    # Average PVOUT from buildable pixels within KEK
    pvout_vals = pvout_patch[within_kek_buildable]
    finite_vals = pvout_vals[np.isfinite(pvout_vals) & (pvout_vals > 0)]
    avg_pvout_daily = float(np.mean(finite_vals)) if len(finite_vals) > 0 else np.nan

    return area_ha, avg_pvout_daily, capacity_mwp


def _read_raster_window_to_pvout_grid(
    raster_path: Path,
    bbox: tuple[float, float, float, float],
    out_shape: tuple[int, int],
    win_transform: rasterio.transform.Affine,
    pvout_crs: str = "EPSG:4326",
    categorical: bool = False,
) -> np.ndarray | None:
    """Read a raster and resample it to match the PVOUT window grid.

    Args:
        categorical: If True, use mode resampling (preserves integer class codes).
                     If False (default), use average resampling (for continuous data
                     like DEM elevation).

    Returns:
        Float32 array matching out_shape, or None if the file could not be read.
    """
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    resampling = Resampling.mode if categorical else Resampling.average

    try:
        with rasterio.open(raster_path) as src:
            output = np.zeros(out_shape, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=output,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=win_transform,
                dst_crs=pvout_crs,
                resampling=resampling,
                dst_nodata=np.nan,
            )
            # Replace sentinel nodata with NaN
            nodata = src.nodata
            if nodata is not None:
                output[output == nodata] = np.nan
            return output
    except Exception as e:
        print(f"  WARNING: Could not read/resample {raster_path.name}: {e}")
        return None


def _build_land_cover_mask(
    lc_arr: np.ndarray | None,
    exclude_codes: frozenset[int],
) -> np.ndarray:
    """Return a binary mask (1 = excluded) for land-cover pixels in exclude_codes."""
    if lc_arr is None:
        return np.zeros(1, dtype=np.uint8)  # shape unknown; caller handles None
    lc_int = np.round(np.nan_to_num(lc_arr, nan=0)).astype(int)
    mask = np.zeros_like(lc_int, dtype=np.uint8)
    for code in exclude_codes:
        mask[lc_int == code] = 1
    return mask


def _resample_landcover_binary_window(
    raster_path: Path,
    bbox: tuple[float, float, float, float],
    out_shape: tuple[int, int],
    win_transform: rasterio.transform.Affine,
    exclude_codes: frozenset[int],
    threshold: float = LAND_COVER_BUILDABLE_THRESHOLD,
    pvout_crs: str = "EPSG:4326",
) -> np.ndarray | None:
    """Binary-threshold resampling of land cover for a windowed region.

    Instead of mode resampling (loses sub-pixel detail at 10m→1km), creates a
    binary buildable/excluded array at source resolution, then resamples with
    average to get a buildable fraction per output pixel. Pixels with fraction
    < threshold are excluded.

    Returns:
        uint8 mask (1=excluded, 0=buildable), or None on failure.
    """
    from rasterio.enums import Resampling
    from rasterio.warp import reproject
    from rasterio.windows import from_bounds as _from_bounds

    try:
        with rasterio.open(raster_path) as src:
            # Read only the bbox window — the ESA VRT is 216000×432000 (≈87 GB
            # if fully read); windowed read keeps memory to ~100 MB per site.
            src_window = _from_bounds(
                left=bbox[0],
                bottom=bbox[1],
                right=bbox[2],
                top=bbox[3],
                transform=src.transform,
            )
            raw = src.read(1, window=src_window, boundless=True, fill_value=0)
            src_win_transform = rasterio.windows.transform(src_window, src.transform)

            # Binary: 1.0 = buildable, 0.0 = excluded
            binary = np.ones_like(raw, dtype=np.float32)
            for code in exclude_codes:
                binary[raw == code] = 0.0
            nodata = src.nodata
            if nodata is not None:
                binary[raw == nodata] = 0.0

            # Resample to target grid with average
            fraction = np.zeros(out_shape, dtype=np.float32)
            reproject(
                source=binary,
                destination=fraction,
                src_transform=src_win_transform,
                src_crs=src.crs,
                dst_transform=win_transform,
                dst_crs=pvout_crs,
                resampling=Resampling.average,
                src_nodata=None,
                dst_nodata=np.nan,
            )

            # Threshold to binary mask
            mask = np.zeros(out_shape, dtype=np.uint8)
            mask[~np.isfinite(fraction) | (fraction < threshold)] = 1
            return mask
    except Exception as e:
        print(f"  WARNING: Could not read/resample {raster_path.name}: {e}")
        return None


def _compute_buildable_pvout(
    pvout_patch: np.ndarray,
    window: rasterio.windows.Window,
    src_transform: rasterio.transform.Affine,
    lon: float,
    lat: float,
    data_dir: Path = BUILDABILITY_DIR,
) -> tuple[float, float, float, str, float, float, float, np.ndarray | None, object | None]:
    """Apply the 4-layer land suitability filter to a PVOUT patch.

    Applies whatever data files are present in data_dir — layers with missing
    files are skipped (pass-through). Returns "data_unavailable" only when
    NO buildability files at all are present.

    Args:
        pvout_patch:   2D daily PVOUT values (kWh/kWp/day) from the raw raster window.
        window:        rasterio Window corresponding to the patch.
        src_transform: Affine transform of the source PVOUT raster.
        lon, lat:      KEK centroid coordinates (for pixel-area computation).
        data_dir:      Directory containing buildability data files.

    Returns:
        (pvout_buildable_daily, buildable_area_ha, max_captive_mwp, constraint_str,
         best_solar_site_lat, best_solar_site_lon, best_solar_site_dist_km,
         filtered_mask, win_transform)
        Returns (NaN, ..., None, None) when no files are present.

    Note on resolution:
        PVOUT raster is at ~1km (≈86 ha/pixel). At this resolution, the minimum-area
        filter (Layer 4, 10 ha) is a no-op — every valid pixel exceeds the threshold.
        Layer 4 is retained to count buildable pixels and compute total area.
    """
    from src.pipeline.buildability_filters import LAND_COVER_EXCLUDE_CODES

    available = _available_build_files(data_dir)
    if not available:
        return np.nan, np.nan, np.nan, "data_unavailable", np.nan, np.nan, np.nan, None, None

    win_transform = rasterio.windows.transform(window, src_transform)
    height, width = pvout_patch.shape

    # Bounding box of this window (left, bottom, right, top)
    left = win_transform.c
    top = win_transform.f
    right = left + abs(win_transform.a) * width
    bottom = top - abs(win_transform.e) * height
    bbox = (left, bottom, right, top)

    pix_ha = _pixel_area_ha(win_transform, lat)

    # Build a "valid pixel" mask — start with where we have real PVOUT data
    valid = np.isfinite(pvout_patch) & (pvout_patch > 0)
    n_raw = int(valid.sum())

    if n_raw == 0:
        return np.nan, 0.0, 0.0, "unconstrained", np.nan, np.nan, np.nan, None, None

    pvout_working = np.where(valid, pvout_patch, 0.0).astype(float)

    # ── Layer 1a: Kawasan Hutan (skip if file absent) ─────────────────────────
    if "kawasan_hutan.shp" in available:
        kh_mask = _rasterize_shp(
            data_dir / "kawasan_hutan.shp", bbox, (height, width), win_transform
        )
        pvout_after_1a = apply_exclusion_mask(pvout_working, kh_mask)
    else:
        pvout_after_1a = pvout_working
    n_after_1a = int((pvout_after_1a > 0).sum())

    # ── Layer 1b: Peatland (vector shapefile preferred, raster fallback) ─────
    if "peatland_klhk.shp" in available:
        peat_mask = _rasterize_shp(
            data_dir / "peatland_klhk.shp", bbox, (height, width), win_transform
        )
        pvout_after_1b = apply_exclusion_mask(pvout_after_1a, peat_mask)
    elif "peatland.vrt" in available:
        peat_arr = _read_raster_window_to_pvout_grid(
            data_dir / "peatland.vrt",
            bbox,
            (height, width),
            win_transform,
            categorical=True,
        )
        if peat_arr is not None:
            peat_mask = (np.nan_to_num(peat_arr, nan=0) > 0).astype(np.uint8)
            pvout_after_1b = apply_exclusion_mask(pvout_after_1a, peat_mask)
        else:
            pvout_after_1b = pvout_after_1a
    else:
        pvout_after_1b = pvout_after_1a
    n_after_1b = int((pvout_after_1b > 0).sum())

    # ── Layer 1c/d: Land cover — binary-threshold resampling (M13) ─────────────
    if "esa_worldcover.vrt" in available:
        lc_mask = _resample_landcover_binary_window(
            data_dir / "esa_worldcover.vrt",
            bbox,
            (height, width),
            win_transform,
            LAND_COVER_EXCLUDE_CODES,
        )
        if lc_mask is not None:
            pvout_after_1cd = apply_exclusion_mask(pvout_after_1b, lc_mask)
        else:
            pvout_after_1cd = pvout_after_1b
    else:
        pvout_after_1cd = pvout_after_1b
    n_after_1cd = int((pvout_after_1cd > 0).sum())

    # ── Layer 3a: Road proximity (skip if file absent) ───────────────────────
    if "road_distance_km.tif" in available:
        road_dist = _read_raster_window_to_pvout_grid(
            data_dir / "road_distance_km.tif", bbox, (height, width), win_transform
        )
        if road_dist is not None:
            pvout_after_3a = apply_road_distance_mask(pvout_after_1cd, road_dist)
        else:
            pvout_after_3a = pvout_after_1cd
    else:
        pvout_after_3a = pvout_after_1cd
    n_after_3a = int((pvout_after_3a > 0).sum())

    # ── Layer 2: Slope + elevation (skip if DEM absent) ───────────────────────
    if "dem_indonesia.tif" in available:
        dem_arr = _read_raster_window_to_pvout_grid(
            data_dir / "dem_indonesia.tif", bbox, (height, width), win_transform
        )
        if dem_arr is not None:
            pix_m = abs(win_transform.a) * KM_PER_DEGREE_LAT * 1000
            slope_arr = compute_slope_degrees(np.nan_to_num(dem_arr, nan=0.0), pix_m)
            pvout_after_2 = apply_slope_elevation_mask(pvout_after_3a, slope_arr, dem_arr)
        else:
            pvout_after_2 = pvout_after_3a
    else:
        pvout_after_2 = pvout_after_3a
    n_after_2 = int((pvout_after_2 > 0).sum())

    # ── Layer 4: Minimum contiguous area ─────────────────────────────────────
    buildable_mask = pvout_after_2 > 0
    filtered_mask = apply_min_area_filter(buildable_mask, pix_ha)
    n_after_4 = int(filtered_mask.sum())

    # Outputs
    buildable_area_ha = round(n_after_4 * pix_ha, 1)
    max_mwp = round(buildable_area_ha / HA_PER_MWP, 1)

    # Find best buildable pixel and its geographic coordinates
    buildable_pvout = np.where(filtered_mask & np.isfinite(pvout_patch), pvout_patch, -np.inf)
    if buildable_pvout.max() > -np.inf:
        best_idx = np.unravel_index(buildable_pvout.argmax(), buildable_pvout.shape)
        pvout_buildable_daily = float(pvout_patch[best_idx])
        # Convert pixel row/col to geographic coordinates using the window transform
        best_lon, best_lat = rasterio.transform.xy(
            win_transform, best_idx[0], best_idx[1], offset="center"
        )
        best_solar_lat = round(float(best_lat), 5)
        best_solar_lon = round(float(best_lon), 5)
        best_solar_dist_km = round(haversine_km(lat, lon, best_solar_lat, best_solar_lon), 2)
    else:
        pvout_buildable_daily = np.nan
        best_solar_lat = np.nan
        best_solar_lon = np.nan
        best_solar_dist_km = np.nan

    constraint = compute_buildability_constraint(
        n_raw, n_after_1a, n_after_1b, n_after_1cd, n_after_3a, n_after_2, n_after_4
    )

    # Per-layer diagnostic — helps verify each layer is active at each KEK
    def _pct(removed: int) -> str:
        return f"{removed / n_raw * 100:.1f}%" if n_raw > 0 else "—"

    print(
        f"    layers: raw={n_raw}"
        f"  -kh={n_raw - n_after_1a}({_pct(n_raw - n_after_1a)})"
        f"  -peat={n_after_1a - n_after_1b}({_pct(n_after_1a - n_after_1b)})"
        f"  -lc={n_after_1b - n_after_1cd}({_pct(n_after_1b - n_after_1cd)})"
        f"  -road={n_after_1cd - n_after_3a}({_pct(n_after_1cd - n_after_3a)})"
        f"  -slope={n_after_3a - n_after_2}({_pct(n_after_3a - n_after_2)})"
        f"  buildable={n_after_4}  constraint={constraint}"
    )

    return (
        pvout_buildable_daily,
        buildable_area_ha,
        max_mwp,
        constraint,
        best_solar_lat,
        best_solar_lon,
        best_solar_dist_km,
        filtered_mask,
        win_transform,
    )


# ─── Builder ──────────────────────────────────────────────────────────────────


def build_fct_site_resource(
    geotiff_zip: Path = GEOTIFF_ZIP,
    sites_csv: Path = DIM_SITES_CSV,
    buildability_dir: Path = BUILDABILITY_DIR,
) -> pd.DataFrame:
    """Extract PVOUT and CF at centroid and best-within-50km for all KEKs.

    When buildability data is available in buildability_dir, also computes
    pvout_buildable_best_50km and related columns (see module docstring).
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    sites_df = pd.read_csv(sites_csv)
    tif_bytes = (
        _load_pvout_tif_bytes()
    )  # uses module-level GEOTIFF_ZIP; geotiff_zip param reserved for override

    available = _available_build_files(buildability_dir)
    n_avail = len(available)
    n_total = len(_REQUIRED_BUILD_FILES)
    if n_avail == n_total:
        print(f"  Buildability data: all {n_total} files present — full filter applied")
    elif n_avail > 0:
        missing = [f for f in _REQUIRED_BUILD_FILES if f not in available]
        print(
            f"  Buildability data: {n_avail}/{n_total} files present — partial filter "
            f"(missing: {', '.join(missing)})"
        )
    else:
        print(
            f"  Buildability data not found in {buildability_dir.relative_to(REPO_ROOT)} — "
            "pvout_buildable_best_50km will be NaN. "
            "Run scripts/download_buildability_data.py to acquire data."
        )

    # Load KEK polygon geometries for spatial within-boundary intersection
    kek_polygons = _load_kek_polygons(KEK_POLYGONS_GEOJSON)
    if kek_polygons:
        print(f"  KEK polygons: {len(kek_polygons)} loaded for within-boundary intersection")
    else:
        print("  KEK polygons not found — using theoretical within-boundary estimate")

    # ─── STAGING + TRANSFORM ──────────────────────────────────────────────────
    records = []
    with rasterio.open(io.BytesIO(tif_bytes)) as src:
        arr = src.read(1)
        for _, row in sites_df.iterrows():
            lat = float(row["latitude"])
            lon = float(row["longitude"])

            pvout_daily_c = _sample_centroid(src, arr, lon, lat)
            pvout_daily_b = _sample_best_50km(src, lon, lat)

            # Build the 50km window for the buildability filter (same geometry as best_50km)
            lat_buf = PVOUT_BUFFER_KM / KM_PER_DEGREE_LAT
            lon_buf = PVOUT_BUFFER_KM / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
            window_50km = from_bounds(
                left=lon - lon_buf,
                bottom=lat - lat_buf,
                right=lon + lon_buf,
                top=lat + lat_buf,
                transform=src.transform,
            )
            try:
                pvout_patch = src.read(1, window=window_50km)
            except Exception:
                pvout_patch = np.array([[]], dtype=float)

            # Apply circular distance mask — exclude corner pixels beyond true 50km radius
            if pvout_patch.size > 0:
                win_tf = rasterio.windows.transform(window_50km, src.transform)
                dist_km = compute_distance_mask_km(lat, lon, win_tf, pvout_patch.shape)
                pvout_patch = np.where(dist_km <= PVOUT_BUFFER_KM, pvout_patch, np.nan)

            # Daily → annual. pvout_daily_to_annual validates plausibility range.
            try:
                pvout_c = (
                    pvout_daily_to_annual(pvout_daily_c) if np.isfinite(pvout_daily_c) else np.nan
                )
            except ValueError as e:
                print(f"  WARNING centroid {row['site_id']}: {e}")
                pvout_c = np.nan

            try:
                pvout_b = (
                    pvout_daily_to_annual(pvout_daily_b) if np.isfinite(pvout_daily_b) else np.nan
                )
            except ValueError as e:
                print(f"  WARNING best_50km {row['site_id']}: {e}")
                pvout_b = np.nan

            # Buildability filter (graceful degradation when data absent)
            (
                pvout_buildable_daily,
                buildable_area_ha,
                max_mwp,
                constraint,
                best_solar_lat,
                best_solar_lon,
                best_solar_dist_km,
                build_mask,
                build_win_tf,
            ) = _compute_buildable_pvout(
                pvout_patch, window_50km, src.transform, lon, lat, buildability_dir
            )
            try:
                pvout_buildable = (
                    pvout_daily_to_annual(pvout_buildable_daily)
                    if np.isfinite(pvout_buildable_daily)
                    else np.nan
                )
            except ValueError as e:
                print(f"  WARNING buildable {row['site_id']}: {e}")
                pvout_buildable = np.nan

            # Within-boundary: spatial intersection with KEK polygon
            site_id = row["site_id"]
            kek_polygon = kek_polygons.get(site_id)
            wb_area_ha = np.nan
            wb_pvout_annual = np.nan
            wb_capacity_mwp = np.nan
            wb_source = "theoretical"

            if build_mask is not None and build_win_tf is not None and kek_polygon is not None:
                pix_ha = _pixel_area_ha(build_win_tf, lat)
                # Compute KEK polygon area in ha for capping
                kek_geom_area_ha = (
                    kek_polygon.area
                    * (KM_PER_DEGREE_LAT**2)
                    * math.cos(math.radians(lat))
                    * 100  # km² → ha
                )
                wb_area_ha, wb_pvout_daily, wb_capacity_mwp = _compute_within_boundary_buildable(
                    build_mask, pvout_patch, build_win_tf, kek_polygon, pix_ha, kek_geom_area_ha
                )
                if wb_area_ha > 0 and np.isfinite(wb_pvout_daily):
                    try:
                        wb_pvout_annual = pvout_daily_to_annual(wb_pvout_daily)
                    except ValueError:
                        wb_pvout_annual = np.nan
                    wb_source = "raster"
                elif wb_area_ha == 0:
                    # KEK polygon too small for raster resolution — fall back
                    wb_source = "theoretical"

            # No fallback: if spatial intersection found 0 buildable pixels,
            # within-boundary buildable area is genuinely 0.
            if wb_source == "theoretical":
                wb_area_ha = 0.0
                wb_capacity_mwp = 0.0
                wb_pvout_annual = np.nan

            records.append(
                {
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "latitude": lat,
                    "longitude": lon,
                    "pvout_daily_centroid": round(pvout_daily_c, 4)
                    if np.isfinite(pvout_daily_c)
                    else np.nan,
                    "pvout_centroid": round(pvout_c, 1) if np.isfinite(pvout_c) else np.nan,
                    "cf_centroid": round(pvout_c / HOURS_PER_YEAR, 4)
                    if np.isfinite(pvout_c)
                    else np.nan,
                    "pvout_daily_best_50km": round(pvout_daily_b, 4)
                    if np.isfinite(pvout_daily_b)
                    else np.nan,
                    "pvout_best_50km": round(pvout_b, 1) if np.isfinite(pvout_b) else np.nan,
                    "cf_best_50km": round(pvout_b / HOURS_PER_YEAR, 4)
                    if np.isfinite(pvout_b)
                    else np.nan,
                    "pvout_source": PVOUT_SOURCE,
                    # Buildability columns — NaN when data/buildability/ files absent
                    "pvout_buildable_best_50km": round(pvout_buildable, 1)
                    if np.isfinite(pvout_buildable)
                    else np.nan,
                    "buildable_area_ha": buildable_area_ha
                    if np.isfinite(buildable_area_ha)
                    else np.nan,
                    "max_captive_capacity_mwp": max_mwp if np.isfinite(max_mwp) else np.nan,
                    "buildability_constraint": constraint,
                    # V2: coordinates of the best buildable solar site (for three-point proximity)
                    "best_solar_site_lat": best_solar_lat
                    if np.isfinite(best_solar_lat)
                    else np.nan,
                    "best_solar_site_lon": best_solar_lon
                    if np.isfinite(best_solar_lon)
                    else np.nan,
                    "best_solar_site_dist_km": best_solar_dist_km
                    if np.isfinite(best_solar_dist_km)
                    else np.nan,
                    # V2.1: within-boundary solar from spatial KEK×raster intersection
                    "within_boundary_area_ha": round(wb_area_ha, 1)
                    if np.isfinite(wb_area_ha)
                    else np.nan,
                    "within_boundary_capacity_mwp": round(wb_capacity_mwp, 1)
                    if np.isfinite(wb_capacity_mwp)
                    else np.nan,
                    "pvout_within_boundary": round(wb_pvout_annual, 1)
                    if np.isfinite(wb_pvout_annual)
                    else np.nan,
                    "within_boundary_source": wb_source,
                }
            )

    return pd.DataFrame(records)


def main() -> None:
    print(f"Loading site centroids from {DIM_SITES_CSV.relative_to(REPO_ROOT)}")
    print(f"Loading PVOUT raster from {GEOTIFF_ZIP.relative_to(REPO_ROOT)}")

    df = build_fct_site_resource()

    n_miss_c = df["pvout_centroid"].isna().sum()
    n_miss_b = df["pvout_best_50km"].isna().sum()
    n_miss_build = df["pvout_buildable_best_50km"].isna().sum()
    print(f"\nExtracted {len(df)} KEKs")
    print(f"  pvout_centroid:          {len(df) - n_miss_c}/{len(df)} valid")
    print(f"  pvout_best_50km:         {len(df) - n_miss_b}/{len(df)} valid")
    print(
        f"  pvout_buildable_best_50km: {len(df) - n_miss_build}/{len(df)} valid"
        + (
            " (buildability data present)"
            if n_miss_build == 0
            else " (data/buildability/ files missing)"
        )
    )
    print(f"  cf range (best): {df['cf_best_50km'].min():.3f} – {df['cf_best_50km'].max():.3f}")

    # Within-boundary source breakdown
    if "within_boundary_source" in df.columns:
        n_raster = (df["within_boundary_source"] == "raster").sum()
        n_theoretical = (df["within_boundary_source"] == "theoretical").sum()
        print(f"  within-boundary source: {n_raster} raster, {n_theoretical} theoretical")

    out = PROCESSED / "fct_site_resource.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nWrote {out.relative_to(REPO_ROOT)}")
    display_cols = [
        "site_id",
        "pvout_centroid",
        "cf_centroid",
        "pvout_best_50km",
        "cf_best_50km",
        "pvout_buildable_best_50km",
        "buildable_area_ha",
        "buildability_constraint",
        "best_solar_site_dist_km",
    ]
    print(df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
