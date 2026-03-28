"""
buildability_filters.py — Pure filter functions for the land suitability cascade.

All functions accept numpy arrays (no file I/O). This enables unit testing with
synthetic rasters without requiring real geospatial data files.

Layers implemented (v1.1):
    Layer 1a: Kawasan Hutan hard exclusion (shapefile → rasterized mask)
    Layer 1b: Peatland (gambut) exclusion
    Layer 1c/d: Land cover exclusions (mangrove, water, cropland, urban) — ESA WorldCover v200
    Layer 2a: Slope > 8° exclusion (derived from Copernicus DEM)
    Layer 2c: Elevation > 1,500m exclusion

Deferred to v1.2:
    Layer 2d: Flood hazard (BNPB portal inaccessible; low overlap with slope)
    Layer 3a: Road proximity (soft constraint; requires OSM PBF processing)

Layer 3b (substation proximity) is already captured in fct_substation_proximity.

Resolution note:
    The PVOUT GeoTIFF (Global Solar Atlas v2) is at ~1km resolution (~86 ha/pixel).
    At this resolution, Layer 4 (minimum contiguous area ≥ 10 ha) is a no-op because
    a single pixel already exceeds the 10 ha threshold. Layer 4 is retained as a count
    of contiguous buildable pixels for completeness and future use at higher resolution.

Reference: METHODOLOGY.md Section 2.5
"""

from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

# Thresholds — match METHODOLOGY.md §2.5
MAX_SLOPE_DEG: float = 8.0  # Layer 2a hard exclusion threshold (degrees)
MAX_ELEV_M: float = 1500.0  # Layer 2c hard exclusion threshold (metres)
MIN_AREA_HA: float = 10.0  # Layer 4 minimum contiguous buildable patch (ha)
HA_PER_MWP: float = 1.5  # 1.5 ha/MWp (tropical fixed-tilt, GCR ~0.45–0.55)

VALID_CONSTRAINTS: frozenset[str] = frozenset(
    [
        "kawasan_hutan",
        "slope",
        "peat",
        "land_cover",  # ESA WorldCover layer 1c/d: tree cover, cropland, urban, water, wetland, mangrove
        "area_too_small",
        "unconstrained",
        "data_unavailable",
    ]
)

# ESA WorldCover v200 (2021) — land cover codes to exclude from buildable area.
# 10m global land cover; public AWS S3, no authentication required.
# Full class table: https://esa-worldcover.org/en/data
# Downloaded automatically by scripts/download_buildability_data.py → esa_worldcover.tif
LAND_COVER_EXCLUDE_CODES: frozenset[int] = frozenset(
    [
        10,  # Tree cover (primary + secondary forest)
        40,  # Cropland (rice paddies / sawah + other agriculture)
        50,  # Built-up (settlements, urban — avoids land-use conflict)
        80,  # Permanent water bodies
        90,  # Herbaceous wetland (peat / swamp proxy)
        95,  # Mangroves (explicit class in v200)
    ]
)


# ─── Pure filter functions ─────────────────────────────────────────────────────


def apply_exclusion_mask(pvout_arr: np.ndarray, mask_arr: np.ndarray) -> np.ndarray:
    """Zero out PVOUT pixels where mask_arr == 1 (excluded).

    Args:
        pvout_arr: 2D float array of PVOUT values (any unit). NaN = no-data.
        mask_arr:  2D array (same shape); 1 = excluded, 0 = potentially buildable.

    Returns:
        Copy of pvout_arr with excluded pixels set to 0.0.
    """
    result = pvout_arr.copy().astype(float)
    result[mask_arr == 1] = 0.0
    return result


def apply_slope_elevation_mask(
    pvout_arr: np.ndarray,
    slope_arr: np.ndarray,
    elev_arr: np.ndarray,
    max_slope_deg: float = MAX_SLOPE_DEG,
    max_elev_m: float = MAX_ELEV_M,
) -> np.ndarray:
    """Zero out PVOUT pixels that exceed slope or elevation thresholds.

    NaN values in slope_arr / elev_arr are treated conservatively as excluded.

    Args:
        pvout_arr:    2D float PVOUT array.
        slope_arr:    2D float slope array (degrees). NaN = no-data → excluded.
        elev_arr:     2D float elevation array (metres). NaN = no-data → excluded.
        max_slope_deg: Hard exclusion threshold (default 8°, per METHODOLOGY §2a).
        max_elev_m:    Hard exclusion threshold (default 1,500m, per METHODOLOGY §2c).

    Returns:
        Copy of pvout_arr with terrain-excluded pixels set to 0.0.
    """
    result = pvout_arr.copy().astype(float)
    steep = ~np.isfinite(slope_arr) | (slope_arr > max_slope_deg)
    high = ~np.isfinite(elev_arr) | (elev_arr > max_elev_m)
    result[steep | high] = 0.0
    return result


def apply_min_area_filter(
    buildable_mask: np.ndarray,
    pixel_area_ha: float,
    min_area_ha: float = MIN_AREA_HA,
) -> np.ndarray:
    """Remove contiguous patches smaller than min_area_ha.

    Uses scipy.ndimage.label to identify 4-connected components, then discards
    patches where total area (n_pixels × pixel_area_ha) < min_area_ha.

    Note on resolution: At ~1km PVOUT pixel size (≈86 ha/pixel), a single pixel
    already exceeds the 10 ha threshold, so this filter is a no-op in practice.
    It is included for correctness and for future use at higher resolution.

    Args:
        buildable_mask: 2D boolean array; True = buildable pixel.
        pixel_area_ha:  Area of one pixel in hectares.
        min_area_ha:    Minimum contiguous area to retain (default 10 ha).

    Returns:
        Boolean array with small-patch pixels set to False.
    """
    labeled, n_features = ndimage.label(buildable_mask)
    if n_features == 0:
        return np.zeros_like(buildable_mask, dtype=bool)

    min_pixels = max(1, int(math.ceil(min_area_ha / pixel_area_ha)))
    sizes = ndimage.sum(buildable_mask, labeled, range(1, n_features + 1))
    large_labels = np.where(np.array(sizes) >= min_pixels)[0] + 1  # labels start at 1
    return np.isin(labeled, large_labels)


def compute_slope_degrees(dem: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """Compute slope (degrees) from a DEM array using central-difference gradient.

    Args:
        dem:          2D float array of elevation values (metres).
        pixel_size_m: Ground sampling distance of the DEM (metres/pixel).
                      For geographic CRS, compute as degrees × 111,320 × cos(lat).

    Returns:
        2D float array of slope values in degrees.
    """
    dzdx = np.gradient(dem.astype(float), pixel_size_m, axis=1)
    dzdy = np.gradient(dem.astype(float), pixel_size_m, axis=0)
    slope_rad = np.arctan(np.sqrt(dzdx**2 + dzdy**2))
    return np.degrees(slope_rad)


def compute_buildability_constraint(
    n_pixels_raw: int,
    n_after_layer1a: int,
    n_after_layer1b: int,
    n_after_layer1cd: int,
    n_after_layer2: int,
    n_after_layer4: int,
) -> str:
    """Identify the dominant binding constraint.

    Finds which filter layer removed the most pixels and returns a label for it.

    Args:
        n_pixels_raw:    Total valid pixels before any filter.
        n_after_layer1a: Remaining after Kawasan Hutan exclusion.
        n_after_layer1b: Remaining after peatland exclusion.
        n_after_layer1cd: Remaining after land-cover exclusions.
        n_after_layer2:  Remaining after slope + elevation filter.
        n_after_layer4:  Remaining after minimum-area filter.

    Returns:
        One of: "kawasan_hutan" | "peat" | "land_cover" | "slope" |
                "area_too_small" | "unconstrained"

        Note: "land_cover" covers the full ESA WorldCover exclusion set (tree cover /
        forest, cropland, urban, water, wetland, mangrove). It is the dominant constraint
        at most Indonesian sites because forest cover (code 10) is pervasive — even when
        peat or kawasan_hutan layers are also active and removing pixels.
    """
    if n_pixels_raw == 0:
        return "unconstrained"

    removed = {
        "kawasan_hutan": n_pixels_raw - n_after_layer1a,
        "peat": n_after_layer1a - n_after_layer1b,
        "land_cover": n_after_layer1b - n_after_layer1cd,
        "slope": n_after_layer1cd - n_after_layer2,
        "area_too_small": n_after_layer2 - n_after_layer4,
    }

    if n_after_layer4 >= n_pixels_raw:
        return "unconstrained"

    return max(removed, key=lambda k: removed[k])
