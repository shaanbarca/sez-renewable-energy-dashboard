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
    regional_groundmount_potential_mwp_50km   buildable_area_ha / 1.5 (1.5 ha/MWp tropical fixed-tilt)
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
    solar_search_method        V3.7: "substation_anchored" if a co-located patch met
                               MEANINGFUL_SHARE_PCT, else "best_pvout_fallback".
                               Only fallback should produce "Build Substation" labels.
    chosen_anchor_substation_name  V3.7: substation that anchors the chosen patch
                               (None when fallback fires).
    solar_supply_share_pct     V3.7: chosen patch nameplate ÷ required_mwp (capped 1.0).
    solar_delivered_share_pct  V3.7: chosen patch generation_mwh ÷ demand_mwh (capped 1.0).

Methodology reference: METHODOLOGY_CONSOLIDATED.md Sections 2.4 and 2.5, METHODOLOGY_V2.md §2
50km buffer formula: lat_buf = 50/111.32, lon_buf = 50/(111.32×cos(lat_rad))
"""

from __future__ import annotations

import io
import json
import math
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.features
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import unary_union

from src.model.basic_model import (
    capacity_factor_from_pvout,
    grid_connection_cost_per_kw,
    lcoe_solar,
    pvout_daily_to_annual,
)
from src.model.columns import Col
from src.pipeline.assumptions import (
    ANCHOR_SEARCH_RADIUS_KM,
    BASE_WACC_DECIMAL,
    HOURS_PER_YEAR,
    KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM,
    KEK_TO_SUBSTATION_THRESHOLD_KM,
    KM_PER_DEGREE_LAT,
    MEANINGFUL_SHARE_PCT,
    PVOUT_BUFFER_KM,
    PVOUT_SOURCE,
)
from src.pipeline.buildability_filters import (
    HA_PER_MWP,
    LAND_COVER_BUILDABLE_THRESHOLD,
    LAND_COVER_EXCLUDE_CODES,
    apply_exclusion_mask,
    apply_min_area_filter,
    apply_road_distance_mask,
    apply_slope_elevation_mask,
    compute_buildability_constraint,
    compute_distance_mask_km,
    compute_slope_degrees,
    haversine_km,
)
from src.pipeline.demand_intensity import required_solar_mwp

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

    try:
        with rasterio.open(raster_path) as src:
            # Read only the bbox window — the ESA VRT is 216000×432000 (≈87 GB
            # if fully read); windowed read keeps memory to ~100 MB per site.
            src_window = from_bounds(
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


# ─── Substation-anchored picker (V3.7) ────────────────────────────────────────


_REGION_TO_TIER_KEY: dict[str, str] = {
    # dim_sites.grid_region_id values
    "JAVA_BALI": "JAMALI",
    "SUMATERA": "SUMATRA",
    "KALIMANTAN": "KALIMANTAN",
    "SULAWESI": "SULAWESI",
    "MALUKU": "MALUKU_PAPUA",
    "PAPUA": "MALUKU_PAPUA",
    "NTB": "MALUKU_PAPUA",  # eastern islands behave like Maluku/Papua sparsity-wise
    # PLN regpln values (Title-Case with hyphens)
    "Jawa-Bali": "JAMALI",
    "Sumatera": "SUMATRA",
    "Kalimantan": "KALIMANTAN",
    "Sulawesi": "SULAWESI",
    "Maluku": "MALUKU_PAPUA",
    "Maluku-Papua": "MALUKU_PAPUA",
    "Papua": "MALUKU_PAPUA",
    "Nusa Tenggara": "MALUKU_PAPUA",
}


def _search_radius_km(grid_region_id: str | None) -> float:
    """Geography-tiered KEK→substation search radius. Falls back to legacy 15 km."""
    if not grid_region_id:
        return KEK_TO_SUBSTATION_THRESHOLD_KM
    tier = _REGION_TO_TIER_KEY.get(grid_region_id)
    if tier is None:
        return KEK_TO_SUBSTATION_THRESHOLD_KM
    return KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM.get(tier, KEK_TO_SUBSTATION_THRESHOLD_KM)


def _annuity_factor(wacc: float, lifetime_yr: int) -> float:
    """Capital recovery factor — same convention as basic_model.lcoe_solar."""
    factor = (1 + wacc) ** lifetime_yr
    return wacc * factor / (factor - 1)


def _pick_anchored_patch(
    filtered_mask: np.ndarray,
    pvout_patch: np.ndarray,
    win_transform: rasterio.transform.Affine,
    site_lat: float,
    site_lon: float,
    site_demand_mwh: float,
    cf_centroid: float,
    substations: list[dict],
    grid_region_id: str | None,
    pix_ha: float,
    tech_params: dict,
) -> dict | None:
    """Find the lowest-LCOE buildable patch co-located with an existing substation.

    Returns a dict with patch coordinates, capacity, anchor substation name, and
    delivered/supply share. Returns None when no candidate substation has enough
    buildable area to meet meaningful_mwp — caller then falls back to argmax.

    Algorithm (METHODOLOGY_CONSOLIDATED.md §8 — V3.7):
      1. required_mwp  = demand_mwh / (8760 × cf_centroid)
      2. meaningful_mwp = required_mwp × MEANINGFUL_SHARE_PCT  (default 30%)
      3. For each substation within KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM[region]:
           - intersect filtered_mask with circular ANCHOR_SEARCH_RADIUS_KM
             buffer around the substation
           - if buildable_mwp >= meaningful_mwp → keep as candidate
      4. For each candidate, compute LCOE proxy:
           lcoe_solar(cf_candidate) + amortised connection cost(dist)
      5. Pick lowest-LCOE candidate → solar_search_method = "substation_anchored"
    """
    if site_demand_mwh <= 0 or cf_centroid <= 0 or not substations:
        return None
    if filtered_mask is None or filtered_mask.sum() == 0:
        return None

    required_mwp = required_solar_mwp(site_demand_mwh, cf_centroid)
    if required_mwp <= 0:
        return None
    meaningful_mwp = required_mwp * MEANINGFUL_SHARE_PCT

    radius_km = _search_radius_km(grid_region_id)

    # Pre-compute pixel grids for distance masking — one mask per substation.
    height, width = filtered_mask.shape
    rows = np.arange(height)
    cols = np.arange(width)
    # Pixel center coordinates via affine transform (offset="center")
    pixel_lons, pixel_lats = rasterio.transform.xy(
        win_transform,
        np.repeat(rows, width),
        np.tile(cols, height),
        offset="center",
    )
    pixel_lats = np.asarray(pixel_lats, dtype=float).reshape(height, width)
    pixel_lons = np.asarray(pixel_lons, dtype=float).reshape(height, width)

    candidates: list[dict] = []
    for sub in substations:
        sub_lat = sub["lat"]
        sub_lon = sub["lon"]
        site_to_sub = haversine_km(site_lat, site_lon, sub_lat, sub_lon)
        if site_to_sub > radius_km:
            continue

        # Distance from each pixel to the substation
        dlat = np.radians(pixel_lats - sub_lat)
        dlon = np.radians(pixel_lons - sub_lon)
        a = (
            np.sin(dlat / 2) ** 2
            + np.cos(np.radians(sub_lat)) * np.cos(np.radians(pixel_lats)) * np.sin(dlon / 2) ** 2
        )
        dist_to_sub_km = 6_371.0 * 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        co_located = dist_to_sub_km <= ANCHOR_SEARCH_RADIUS_KM

        candidate_mask = filtered_mask & co_located & np.isfinite(pvout_patch)
        n_pixels = int(candidate_mask.sum())
        if n_pixels == 0:
            continue

        candidate_area_ha = n_pixels * pix_ha
        candidate_mwp = candidate_area_ha / HA_PER_MWP
        if candidate_mwp < meaningful_mwp:
            continue

        # Mean PVOUT (daily) over the candidate patch
        patch_vals = pvout_patch[candidate_mask]
        finite_vals = patch_vals[np.isfinite(patch_vals) & (patch_vals > 0)]
        if len(finite_vals) == 0:
            continue
        mean_pvout_daily = float(np.mean(finite_vals))

        try:
            mean_pvout_annual = pvout_daily_to_annual(mean_pvout_daily)
        except ValueError:
            continue
        cf_candidate = capacity_factor_from_pvout(mean_pvout_annual)
        if cf_candidate <= 0:
            continue

        # LCOE proxy: solar LCOE at candidate CF + amortised connection cost.
        # Use the SITE→substation distance — that's the relevant gen-tie length
        # because the patch is BY DEFINITION ≤ 10 km from the substation.
        try:
            lcoe_base = lcoe_solar(
                tech_params["capex_usd_per_kw"],
                tech_params["fixed_om_usd_per_kw_yr"],
                tech_params["wacc"],
                tech_params["lifetime_yr"],
                cf_candidate,
            )
        except ValueError:
            continue

        conn_capex = grid_connection_cost_per_kw(site_to_sub)
        # Amortise connection capex over lifetime, divide by annual generation.
        # generation_per_kw_yr = cf × 8760 h × 1 kW = cf × 8760 kWh = cf × 8.76 MWh
        crf = _annuity_factor(tech_params["wacc"], tech_params["lifetime_yr"])
        conn_lcoe = (conn_capex * crf) / (cf_candidate * 8.76)
        lcoe_proxy = lcoe_base + conn_lcoe

        # Area-weighted patch centroid (for downstream best_solar_site_lat/lon)
        patch_lat = float(np.mean(pixel_lats[candidate_mask]))
        patch_lon = float(np.mean(pixel_lons[candidate_mask]))

        # Delivered-energy share corrects for capacity-factor reality:
        # nameplate MWp × 8760 h × cf = annual MWh actually generated.
        candidate_generation_mwh = candidate_mwp * 8760 * cf_candidate
        supply_share = min(candidate_mwp / required_mwp, 1.0)
        delivered_share = min(candidate_generation_mwh / site_demand_mwh, 1.0)

        candidates.append(
            {
                "anchor_name": sub["name"],
                "site_to_sub_km": site_to_sub,
                "patch_lat": round(patch_lat, 5),
                "patch_lon": round(patch_lon, 5),
                "mean_pvout_daily": mean_pvout_daily,
                "patch_area_ha": round(candidate_area_ha, 1),
                "patch_capacity_mwp": round(candidate_mwp, 1),
                "supply_share_pct": round(supply_share, 4),
                "delivered_share_pct": round(delivered_share, 4),
                "lcoe_proxy": lcoe_proxy,
            }
        )

    if not candidates:
        return None

    # Pick lowest LCOE proxy
    best = min(candidates, key=lambda c: c["lcoe_proxy"])
    return best


def _compute_buildable_pvout(
    pvout_patch: np.ndarray,
    window: rasterio.windows.Window,
    src_transform: rasterio.transform.Affine,
    lon: float,
    lat: float,
    data_dir: Path = BUILDABILITY_DIR,
    site_demand_mwh: float = 0.0,
    cf_centroid: float = 0.0,
    substations: list[dict] | None = None,
    grid_region_id: str | None = None,
    tech_params: dict | None = None,
) -> tuple[
    float,
    float,
    float,
    str,
    float,
    float,
    float,
    np.ndarray | None,
    np.ndarray | None,
    object | None,
    str,
    str | None,
    float,
    float,
]:
    """Apply the 4-layer land suitability filter to a PVOUT patch.

    Applies whatever data files are present in data_dir — layers with missing
    files are skipped (pass-through). Returns "data_unavailable" only when
    NO buildability files at all are present.

    V3.7: when site_demand_mwh > 0 and substations are provided, picks the best
    *substation-anchored* buildable patch (lowest LCOE proxy) instead of the
    naive argmax(PVOUT) pixel. Falls back to argmax when no candidate substation
    has enough buildable area to meet MEANINGFUL_SHARE_PCT of demand.
    See METHODOLOGY_CONSOLIDATED.md §8 for the search algorithm.

    v4.0.5 (methodology #40): in addition to the full 4-layer filtered_mask, the
    function also returns a hard_filtered_mask — the result of running ONLY the
    HARD-classified layers (slope/elev, Kawasan Hutan, peat) and skipping the
    SOFT layers (land cover, road distance). The hard mask represents land that
    is physically and legally buildable regardless of zoning; downstream the
    `wb_buildout_footprint_ratio` slider expresses what fraction of
    (hard_max - baseline) the site owner overrides for solar deployment.
    See src/dash/constants.py:BUILDABILITY_LAYER_CLASSIFICATION.

    Args:
        pvout_patch:       2D daily PVOUT values (kWh/kWp/day) from the raw raster window.
        window:            rasterio Window corresponding to the patch.
        src_transform:     Affine transform of the source PVOUT raster.
        lon, lat:          KEK centroid coordinates (for pixel-area computation).
        data_dir:          Directory containing buildability data files.
        site_demand_mwh:   Annual demand for sizing the meaningful-share floor.
        cf_centroid:       Capacity factor at site centroid (sizes required_mwp).
        substations:       Operational substations [{"name", "lat", "lon", ...}, ...].
        grid_region_id:    Site's grid region (drives geography-tiered search radius).
        tech_params:       Dict with capex_usd_per_kw, fixed_om_usd_per_kw_yr,
                           wacc, lifetime_yr — used for LCOE-proxy ranking.

    Returns:
        (pvout_buildable_daily, buildable_area_ha, max_captive_mwp, constraint_str,
         best_solar_site_lat, best_solar_site_lon, best_solar_site_dist_km,
         filtered_mask, hard_filtered_mask, win_transform,
         solar_search_method, chosen_anchor_substation_name,
         solar_supply_share_pct, solar_delivered_share_pct)
        Returns (NaN, ..., None, None, None, "data_unavailable", None, NaN, NaN)
        when no files are present.

    Note on resolution:
        PVOUT raster is at ~1km (≈86 ha/pixel). At this resolution, the minimum-area
        filter (Layer 4, 10 ha) is a no-op — every valid pixel exceeds the threshold.
        Layer 4 is retained to count buildable pixels and compute total area.

    Invariant:
        hard_filtered_mask is always a superset of filtered_mask
        (since hard_filtered_mask drops SOFT exclusions). The caller can compute
        soft_excluded = hard_filtered_mask.sum() - filtered_mask.sum() to surface
        the land that's only excluded by zoning/use.
    """

    available = _available_build_files(data_dir)
    if not available:
        return (
            np.nan,
            np.nan,
            np.nan,
            "data_unavailable",
            np.nan,
            np.nan,
            np.nan,
            None,
            None,
            None,
            "data_unavailable",
            None,
            np.nan,
            np.nan,
        )

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
        return (
            np.nan,
            0.0,
            0.0,
            "unconstrained",
            np.nan,
            np.nan,
            np.nan,
            None,
            None,
            None,
            "no_pvout",
            None,
            np.nan,
            np.nan,
        )

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
    # Hoist slope/elev computation so the HARD-only cascade below can reuse it.
    dem_arr = None
    slope_arr = None
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

    # ── HARD-only cascade (v4.0.5, methodology #40) ─────────────────────────
    # Re-apply only the HARD exclusion layers (Kawasan Hutan, peat, slope+elev)
    # — skipping SOFT layers (land cover, road distance) — to produce a parallel
    # mask of land that's physically/legally buildable regardless of zoning.
    # See src/dash/constants.py:BUILDABILITY_LAYER_CLASSIFICATION.
    #
    #   FULL cascade:  pvout_working → Kawasan Hutan → peat → land cover →
    #                                  road distance → slope+elev → min_area
    #   HARD cascade:  pvout_working → Kawasan Hutan → peat → slope+elev → min_area
    #
    # The site owner can override SOFT exclusions (canopy over parking, etc.);
    # HARD exclusions are physical/legal facts that the dashboard cannot waive.
    # The frontend slider expresses what fraction of (hard_max - baseline) the
    # user wants to override.
    if slope_arr is not None and dem_arr is not None:
        pvout_hard_after_2 = apply_slope_elevation_mask(pvout_after_1b, slope_arr, dem_arr)
    else:
        pvout_hard_after_2 = pvout_after_1b
    hard_buildable_mask = pvout_hard_after_2 > 0
    hard_filtered_mask = apply_min_area_filter(hard_buildable_mask, pix_ha)

    # Outputs
    buildable_area_ha = round(n_after_4 * pix_ha, 1)
    max_mwp = round(buildable_area_ha / HA_PER_MWP, 1)

    # ── Substation-anchored picker (V3.7) ────────────────────────────────────
    # Try the anchored picker first when demand + substation context is supplied.
    # If it returns None (no candidate hits MEANINGFUL_SHARE_PCT), fall back to
    # the legacy argmax(PVOUT) pixel. The "fallback" path is exactly what should
    # produce a legitimate "Build Substation" recommendation downstream.
    anchored = None
    if (
        substations is not None
        and tech_params is not None
        and site_demand_mwh > 0
        and cf_centroid > 0
    ):
        anchored = _pick_anchored_patch(
            filtered_mask=filtered_mask,
            pvout_patch=pvout_patch,
            win_transform=win_transform,
            site_lat=lat,
            site_lon=lon,
            site_demand_mwh=site_demand_mwh,
            cf_centroid=cf_centroid,
            substations=substations,
            grid_region_id=grid_region_id,
            pix_ha=pix_ha,
            tech_params=tech_params,
        )

    if anchored is not None:
        pvout_buildable_daily = anchored["mean_pvout_daily"]
        best_solar_lat = anchored["patch_lat"]
        best_solar_lon = anchored["patch_lon"]
        best_solar_dist_km = round(haversine_km(lat, lon, best_solar_lat, best_solar_lon), 2)
        solar_search_method = "substation_anchored"
        chosen_anchor_substation_name = anchored["anchor_name"]
        solar_supply_share_pct = anchored["supply_share_pct"]
        solar_delivered_share_pct = anchored["delivered_share_pct"]
    else:
        # Fallback: legacy argmax(PVOUT) pixel
        buildable_pvout = np.where(filtered_mask & np.isfinite(pvout_patch), pvout_patch, -np.inf)
        if buildable_pvout.max() > -np.inf:
            best_idx = np.unravel_index(buildable_pvout.argmax(), buildable_pvout.shape)
            pvout_buildable_daily = float(pvout_patch[best_idx])
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
        solar_search_method = "best_pvout_fallback"
        chosen_anchor_substation_name = None
        # When fallback fires, derive shares from the chosen pixel's nameplate
        # (max_mwp covers the whole 50km radius; the fallback pixel's "patch"
        # is effectively the entire buildable area).
        if site_demand_mwh > 0 and cf_centroid > 0 and np.isfinite(pvout_buildable_daily):
            required_mwp = required_solar_mwp(site_demand_mwh, cf_centroid)
            if required_mwp > 0:
                solar_supply_share_pct = round(min(max_mwp / required_mwp, 1.0), 4)
                try:
                    pvout_annual_fb = pvout_daily_to_annual(pvout_buildable_daily)
                    cf_fb = capacity_factor_from_pvout(pvout_annual_fb)
                    # nameplate MWp × 8760 h × cf = annual MWh actually generated.
                    gen_mwh = max_mwp * 8760 * cf_fb
                    solar_delivered_share_pct = round(min(gen_mwh / site_demand_mwh, 1.0), 4)
                except ValueError:
                    solar_delivered_share_pct = np.nan
            else:
                solar_supply_share_pct = np.nan
                solar_delivered_share_pct = np.nan
        else:
            solar_supply_share_pct = np.nan
            solar_delivered_share_pct = np.nan

    constraint = compute_buildability_constraint(
        n_raw, n_after_1a, n_after_1b, n_after_1cd, n_after_3a, n_after_2, n_after_4
    )

    # Per-layer diagnostic — helps verify each layer is active at each KEK
    def _pct(removed: int) -> str:
        return f"{removed / n_raw * 100:.1f}%" if n_raw > 0 else "—"

    anchor_tag = f" anchor={chosen_anchor_substation_name}" if chosen_anchor_substation_name else ""
    print(
        f"    layers: raw={n_raw}"
        f"  -kh={n_raw - n_after_1a}({_pct(n_raw - n_after_1a)})"
        f"  -peat={n_after_1a - n_after_1b}({_pct(n_after_1a - n_after_1b)})"
        f"  -lc={n_after_1b - n_after_1cd}({_pct(n_after_1b - n_after_1cd)})"
        f"  -road={n_after_1cd - n_after_3a}({_pct(n_after_1cd - n_after_3a)})"
        f"  -slope={n_after_3a - n_after_2}({_pct(n_after_3a - n_after_2)})"
        f"  buildable={n_after_4}  constraint={constraint}"
        f"  picker={solar_search_method}{anchor_tag}"
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
        hard_filtered_mask,
        win_transform,
        solar_search_method,
        chosen_anchor_substation_name,
        solar_supply_share_pct,
        solar_delivered_share_pct,
    )


# ─── Builder ──────────────────────────────────────────────────────────────────


def _load_substations_for_picker(path: Path) -> list[dict]:
    """Load operational PLN substations as a flat list for the anchored picker.

    Mirrors _load_substations() in build_fct_substation_proximity.py but lives
    here to avoid a circular dependency (proximity reads fct_site_resource).
    """
    if not path.exists():
        return []
    with path.open() as f:
        gj = json.load(f)
    subs: list[dict] = []
    for feat in gj["features"]:
        props = feat["properties"]
        if props.get("statopr", "").strip() != "Operasi":
            continue
        lon, lat = feat["geometry"]["coordinates"]
        subs.append(
            {
                "name": props.get("namobj", ""),
                "lat": float(lat),
                "lon": float(lon),
            }
        )
    return subs


def _load_site_demand_2030_mwh(path: Path) -> dict[str, float]:
    """Return {site_id: demand_mwh_2030} from fct_site_demand.csv. Missing → 0.0."""
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df = df[df["year"] == 2030]
    return {str(r["site_id"]): float(r["demand_mwh"]) for _, r in df.iterrows()}


def _load_tech_params(path: Path) -> dict:
    """Load TECH006 (utility-scale solar) parameters for LCOE-proxy ranking."""
    if not path.exists():
        # Hardcoded fallback matches dim_tech_cost.csv ground truth
        return {
            "capex_usd_per_kw": 960.0,
            "fixed_om_usd_per_kw_yr": 7.5,
            "wacc": BASE_WACC_DECIMAL,
            "lifetime_yr": 27,
        }
    df = pd.read_csv(path)
    row = df[df["tech_id"] == "TECH006"].iloc[0]
    return {
        "capex_usd_per_kw": float(row["capex_usd_per_kw"]),
        "fixed_om_usd_per_kw_yr": float(row["fixed_om_usd_per_kw_yr"]),
        "wacc": BASE_WACC_DECIMAL,
        "lifetime_yr": int(row["lifetime_yr"]),
    }


def build_fct_site_resource(
    geotiff_zip: Path = GEOTIFF_ZIP,
    sites_csv: Path = DIM_SITES_CSV,
    buildability_dir: Path = BUILDABILITY_DIR,
) -> pd.DataFrame:
    """Extract PVOUT and CF at centroid and best-within-50km for all KEKs.

    When buildability data is available in buildability_dir, also computes
    pvout_buildable_best_50km and related columns (see module docstring).

    V3.7: substation-anchored picker requires fct_site_demand.csv + substation.geojson
    + dim_tech_cost.csv. If any are missing, falls back to legacy argmax(PVOUT).
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    sites_df = pd.read_csv(sites_csv)
    tif_bytes = (
        _load_pvout_tif_bytes()
    )  # uses module-level GEOTIFF_ZIP; geotiff_zip param reserved for override

    # V3.7: substation-anchored picker context
    substation_geojson = REPO_ROOT / "data" / "substation.geojson"
    fct_site_demand_csv = PROCESSED / "fct_site_demand.csv"
    dim_tech_cost_csv = PROCESSED / "dim_tech_cost.csv"
    substations = _load_substations_for_picker(substation_geojson)
    site_demand_lookup = _load_site_demand_2030_mwh(fct_site_demand_csv)
    tech_params = _load_tech_params(dim_tech_cost_csv)
    if substations and site_demand_lookup:
        print(
            f"  V3.7 anchored picker: {len(substations)} substations, "
            f"{len(site_demand_lookup)} site demands"
        )
    else:
        print(
            "  V3.7 anchored picker: prerequisites missing — falling back to "
            "argmax(PVOUT) for all sites"
        )

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

            # V3.7: per-site picker context — demand, region, centroid CF
            site_id_for_lookup = str(row["site_id"])
            site_demand_mwh = site_demand_lookup.get(site_id_for_lookup, 0.0)
            grid_region_id = (
                str(row["grid_region_id"]) if pd.notna(row.get("grid_region_id")) else None
            )
            cf_centroid_for_picker = (
                float(pvout_c) / HOURS_PER_YEAR if np.isfinite(pvout_c) else 0.0
            )

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
                build_mask_hard,
                build_win_tf,
                solar_search_method,
                chosen_anchor_substation_name,
                solar_supply_share_pct,
                solar_delivered_share_pct,
            ) = _compute_buildable_pvout(
                pvout_patch,
                window_50km,
                src.transform,
                lon,
                lat,
                buildability_dir,
                site_demand_mwh=site_demand_mwh,
                cf_centroid=cf_centroid_for_picker,
                substations=substations or None,
                grid_region_id=grid_region_id,
                tech_params=tech_params,
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
            wb_hard_max_area_ha = np.nan
            wb_hard_max_capacity_mwp = np.nan
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

                # v4.0.5 (methodology #40): hard-only mask within-boundary —
                # what would be buildable if the site owner could override all
                # SOFT zoning exclusions (land cover, road distance). The
                # frontend slider expresses what fraction of (hard - baseline)
                # to actually override. hard_filtered_mask is a superset of
                # filtered_mask (only drops SOFT exclusions), so
                # wb_hard_max_area_ha >= wb_area_ha by construction.
                if build_mask_hard is not None:
                    wb_hard_max_area_ha, _, wb_hard_max_capacity_mwp = (
                        _compute_within_boundary_buildable(
                            build_mask_hard,
                            pvout_patch,
                            build_win_tf,
                            kek_polygon,
                            pix_ha,
                            kek_geom_area_ha,
                        )
                    )

            # No fallback: if spatial intersection found 0 buildable pixels,
            # within-boundary buildable area is genuinely 0.
            if wb_source == "theoretical":
                wb_area_ha = 0.0
                wb_capacity_mwp = 0.0
                wb_pvout_annual = np.nan
                # If baseline fell back to theoretical/zero, hard_max should
                # also be zero (no polygon match means no surface to compute on).
                if not np.isfinite(wb_hard_max_area_ha):
                    wb_hard_max_area_ha = 0.0
                    wb_hard_max_capacity_mwp = 0.0

            # Guard the invariant: hard_max >= baseline. If a pipeline edge
            # case violates this, clamp + log. Better to ship a consistent
            # number than a confusing negative soft_excluded downstream.
            if (
                np.isfinite(wb_hard_max_area_ha)
                and np.isfinite(wb_area_ha)
                and wb_hard_max_area_ha < wb_area_ha
            ):
                print(
                    f"  WARNING {site_id}: hard_max_area_ha ({wb_hard_max_area_ha}) "
                    f"< baseline area_ha ({wb_area_ha}); clamping to baseline."
                )
                wb_hard_max_area_ha = wb_area_ha
                wb_hard_max_capacity_mwp = wb_capacity_mwp

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
                    Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM: max_mwp
                    if np.isfinite(max_mwp)
                    else np.nan,
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
                    # v4.0.5 (methodology #40): HARD-only mask within-boundary —
                    # area that's physically/legally buildable regardless of
                    # zoning. The frontend slider expresses what fraction of
                    # (hard_max - baseline) the site owner overrides.
                    # Invariant: within_boundary_hard_max_ha >= within_boundary_area_ha
                    "within_boundary_hard_max_ha": round(wb_hard_max_area_ha, 1)
                    if np.isfinite(wb_hard_max_area_ha)
                    else np.nan,
                    "within_boundary_capacity_hard_max_mwp": round(wb_hard_max_capacity_mwp, 1)
                    if np.isfinite(wb_hard_max_capacity_mwp)
                    else np.nan,
                    # V3.7: substation-anchored picker outputs
                    "solar_search_method": solar_search_method,
                    "chosen_anchor_substation_name": chosen_anchor_substation_name,
                    "solar_supply_share_pct": solar_supply_share_pct
                    if np.isfinite(solar_supply_share_pct)
                    else np.nan,
                    "solar_delivered_share_pct": solar_delivered_share_pct
                    if np.isfinite(solar_delivered_share_pct)
                    else np.nan,
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

    # V3.7: substation-anchored picker distribution
    if "solar_search_method" in df.columns:
        method_counts = df["solar_search_method"].value_counts().to_dict()
        method_summary = ", ".join(f"{k}={v}" for k, v in sorted(method_counts.items()))
        print(f"  solar_search_method: {method_summary}")

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
