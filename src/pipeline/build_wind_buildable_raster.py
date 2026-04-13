"""
build_wind_buildable_raster — Nationwide wind buildable area raster.

Applies the wind-adapted buildability cascade to the Global Wind Atlas
wind speed raster across all of Indonesia. Produces a GeoTIFF where:
  - Buildable pixels retain their wind speed value (m/s)
  - Excluded pixels are NaN

Strategy: The native wind raster is 250m (8707x19757). Processing at that
resolution requires rasterizing the 555MB kawasan_hutan.shp at 172M pixels,
which is slow and memory-heavy. Instead, we first downsample to ~1km
(matching PVOUT resolution: 2280x5760), then apply all filters at ~1km.
This is 11x less work and the web output is at ~1km anyway.

Layers applied (wind-adapted thresholds):
  1a. Kawasan Hutan (forest estate) — vector exclusion
  1b. Peatland (KLHK) — vector exclusion
  1c. Land cover (ESA WorldCover v200) — categorical exclusion
      KEY DIFF: cropland (40) is NOT excluded (turbines coexist)
  2.  Slope (>20°) and elevation (>1500m) — DEM-derived exclusion
      KEY DIFF: slope relaxed from 8° (solar) to 20° (wind)
  2.5 Wind speed <3.0 m/s — below IEC Class III cut-in

Output:
  outputs/assets/buildable_wind_web.tif — ~1km resolution for dashboard

Usage:
  uv run python -m src.pipeline.build_wind_buildable_raster
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.warp import reproject

from src.pipeline.buildability_filters import (
    apply_exclusion_mask,
    apply_slope_elevation_mask,
    compute_slope_degrees,
)
from src.pipeline.wind_buildability_filters import (
    WIND_LAND_COVER_BUILDABLE_THRESHOLD,
    WIND_LAND_COVER_EXCLUDE_CODES,
    WIND_MAX_ELEV_M,
    WIND_MAX_SLOPE_DEG,
    WIND_MIN_SPEED_MS,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
BUILD_DIR = DATA_DIR / "buildability"
WIND_TIF = DATA_DIR / "wind" / "IDN_wind-speed_100m.tif"
OUT_DIR = REPO_ROOT / "outputs" / "assets"

# Target resolution matches PVOUT raster (~0.00833° per pixel, ~1km)
TARGET_PIXEL_DEG: float = 0.008333

# Minimum buildable pixels per 4x4 block (same as solar)
MIN_BUILDABLE_PER_BLOCK: int = 2


def _rasterize_shp_full(
    shp_path: Path,
    out_shape: tuple[int, int],
    transform: rasterio.transform.Affine,
) -> np.ndarray:
    """Rasterize a shapefile to match the target grid. Returns binary mask (1=excluded)."""
    import geopandas as gpd
    import rasterio.features

    print(f"    Rasterizing {shp_path.name}...")
    gdf = gpd.read_file(shp_path)

    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    valid_geoms = [geom for geom in gdf.geometry if geom is not None and geom.is_valid]
    if not valid_geoms:
        return np.zeros(out_shape, dtype=np.uint8)

    return rasterio.features.rasterize(
        [(geom, 1) for geom in valid_geoms],
        out_shape=out_shape,
        transform=transform,
        fill=0,
        dtype=np.uint8,
    )


def _resample_raster_to_grid(
    raster_path: Path,
    out_shape: tuple[int, int],
    dst_transform: rasterio.transform.Affine,
    categorical: bool = False,
) -> np.ndarray | None:
    """Read a raster and resample to the target grid."""
    resampling = Resampling.mode if categorical else Resampling.average

    print(f"    Resampling {raster_path.name}...")
    try:
        with rasterio.open(raster_path) as src:
            output = np.zeros(out_shape, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=output,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                resampling=resampling,
                dst_nodata=np.nan,
            )
            nodata = src.nodata
            if nodata is not None:
                output[output == nodata] = np.nan
            return output
    except Exception as e:
        print(f"    WARNING: Could not read {raster_path.name}: {e}")
        return None


def _resample_landcover_binary(
    raster_path: Path,
    out_shape: tuple[int, int],
    dst_transform: rasterio.transform.Affine,
    exclude_codes: frozenset[int],
    threshold: float = WIND_LAND_COVER_BUILDABLE_THRESHOLD,
) -> np.ndarray | None:
    """Resample categorical land cover to a binary exclusion mask.

    Uses Resampling.mode via rasterio.band() lazy reference to stream tiles
    without loading the full 10m source into memory. The modal land cover
    class at ~1km resolution is checked against exclude_codes.

    Wind-adapted: cropland (code 40) is NOT excluded.
    """
    print(f"    Reprojecting {raster_path.name} to target grid...")
    try:
        with rasterio.open(raster_path) as src:
            # Stream-reproject via lazy band reference (never loads full source)
            output = np.zeros(out_shape, dtype=np.float32)
            reproject(
                source=rasterio.band(src, 1),
                destination=output,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                resampling=Resampling.mode,
                dst_nodata=np.nan,
            )

            # Build exclusion mask from modal class
            mask = np.zeros(out_shape, dtype=np.uint8)
            lc_int = np.round(output).astype(np.int16)
            for code in exclude_codes:
                mask[lc_int == code] = 1
            mask[~np.isfinite(output)] = 1
            return mask
    except Exception as e:
        print(f"    WARNING: Could not read {raster_path.name}: {e}")
        return None


def build_wind_buildable_raster() -> Path:
    """Generate the nationwide buildable wind speed raster."""
    print("\n=== Building nationwide buildable wind raster ===\n")

    if not WIND_TIF.exists():
        raise FileNotFoundError(
            f"Wind GeoTIFF not found: {WIND_TIF}\n"
            "Download from globalwindatlas.info and place in data/wind/"
        )

    # 1. Read wind raster, downsampling to ~1km via out_shape (avoids full-res in memory)
    with rasterio.open(WIND_TIF) as src:
        native_h, native_w = src.height, src.width
        bounds = src.bounds
        native_pix = abs(src.transform.a)

        print(f"  Native: {native_h}x{native_w} ({native_pix * 111.32:.2f} km/px)")

        # Target grid: ~1km (matching PVOUT resolution)
        target_w = int((bounds.right - bounds.left) / TARGET_PIXEL_DEG)
        target_h = int((bounds.top - bounds.bottom) / TARGET_PIXEL_DEG)
        print(f"  Target: {target_h}x{target_w} ({TARGET_PIXEL_DEG * 111.32:.2f} km/px)")

        # Read at target resolution directly (memory-efficient, no full-res copy)
        print("  Downsampling wind to ~1km...")
        data = src.read(
            1,
            out_shape=(target_h, target_w),
            resampling=Resampling.average,
        ).astype(np.float32)

    target_transform = transform_from_bounds(
        bounds.left, bounds.bottom, bounds.right, bounds.top, target_w, target_h
    )

    data[data <= 0] = np.nan
    valid_before = np.count_nonzero(np.isfinite(data))
    result = data.copy()
    print(f"    Valid pixels: {valid_before:,}")

    # 3. Kawasan Hutan
    kh_path = BUILD_DIR / "kawasan_hutan.shp"
    if kh_path.exists():
        kh_mask = _rasterize_shp_full(kh_path, (target_h, target_w), target_transform)
        result = apply_exclusion_mask(result, kh_mask)
        excluded = valid_before - np.count_nonzero(result > 0)
        print(
            f"    Kawasan Hutan: excluded {excluded:,} pixels ({excluded / valid_before * 100:.1f}%)"
        )
        del kh_mask
    else:
        print("    Kawasan Hutan: not found, skipping")

    # 4. Peatland
    peat_path = BUILD_DIR / "peatland_klhk.shp"
    if peat_path.exists():
        before = np.count_nonzero(result > 0)
        peat_mask = _rasterize_shp_full(peat_path, (target_h, target_w), target_transform)
        result = apply_exclusion_mask(result, peat_mask)
        excluded = before - np.count_nonzero(result > 0)
        print(f"    Peatland: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
        del peat_mask
    else:
        print("    Peatland: not found, skipping")

    # 5. Land cover (wind-adapted: cropland ALLOWED)
    lc_path = BUILD_DIR / "esa_worldcover.vrt"
    if lc_path.exists():
        before = np.count_nonzero(result > 0)
        lc_mask = _resample_landcover_binary(
            lc_path, (target_h, target_w), target_transform, WIND_LAND_COVER_EXCLUDE_CODES
        )
        if lc_mask is not None:
            result = apply_exclusion_mask(result, lc_mask)
            excluded = before - np.count_nonzero(result > 0)
            print(f"    Land cover: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
            del lc_mask
    else:
        print("    Land cover VRT: not found, skipping")

    # 6. Slope & elevation (wind: slope <=20°, elev <=1500m)
    dem_path = BUILD_DIR / "dem_indonesia.tif"
    if dem_path.exists():
        before = np.count_nonzero(result > 0)
        dem_arr = _resample_raster_to_grid(
            dem_path, (target_h, target_w), target_transform, categorical=False
        )
        if dem_arr is not None:
            mid_lat = (bounds.top + bounds.bottom) / 2
            pixel_size_m = TARGET_PIXEL_DEG * 111320 * math.cos(math.radians(abs(mid_lat)))
            slope = compute_slope_degrees(dem_arr, pixel_size_m)
            result = apply_slope_elevation_mask(
                result,
                slope,
                dem_arr,
                max_slope_deg=WIND_MAX_SLOPE_DEG,
                max_elev_m=WIND_MAX_ELEV_M,
            )
            excluded = before - np.count_nonzero(result > 0)
            print(f"    Slope/elev: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
            del dem_arr, slope
    else:
        print("    DEM: not found, skipping")

    # 7. Wind speed minimum (<3.0 m/s excluded)
    before = np.count_nonzero(result > 0)
    result[np.isfinite(result) & (result < WIND_MIN_SPEED_MS)] = np.nan
    excluded = before - np.count_nonzero(np.isfinite(result))
    print(
        f"    Wind <{WIND_MIN_SPEED_MS} m/s: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)"
    )

    # Set non-buildable pixels to NaN
    result[result <= 0] = np.nan
    valid_after = np.count_nonzero(np.isfinite(result))
    print(
        f"\n  Summary: {valid_before:,} valid -> {valid_after:,} buildable "
        f"({valid_after / valid_before * 100:.1f}% retained)"
    )

    # Save output at target resolution (already ~1km, no further downsampling needed)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "buildable_wind_web.tif"

    out_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": target_w,
        "height": target_h,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": target_transform,
        "nodata": np.nan,
        "compress": "deflate",
    }

    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(result, 1)

    print(f"\n  Output: {out_path.relative_to(REPO_ROOT)} ({target_h}x{target_w})")
    print(f"  File size: {out_path.stat().st_size / 1024:.0f} KB")

    return out_path


if __name__ == "__main__":
    build_wind_buildable_raster()
