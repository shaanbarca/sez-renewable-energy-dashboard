"""
build_buildable_raster — Nationwide solar buildable area raster.

Applies the same 4-layer buildability cascade used per-KEK in build_fct_kek_resource.py,
but across the entire Indonesia PVOUT grid. Produces a GeoTIFF where:
  - Buildable pixels retain their PVOUT value (daily kWh/kWp)
  - Excluded pixels are NaN

Layers applied (same order as per-KEK pipeline):
  1a. Kawasan Hutan (forest estate) — vector exclusion
  1b. Peatland (KLHK) — vector exclusion
  1c. Land cover (ESA WorldCover v200) — categorical exclusion
  2.  Slope (>8°) and elevation (>1500m) — DEM-derived exclusion

Output:
  outputs/assets/buildable_pvout_web.tif — downsampled for dashboard overlay

Usage:
  uv run python -m src.pipeline.build_buildable_raster
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as transform_from_bounds
from rasterio.warp import reproject

from src.pipeline.buildability_filters import (
    LAND_COVER_BUILDABLE_THRESHOLD,
    LAND_COVER_EXCLUDE_CODES,
    apply_exclusion_mask,
    apply_slope_elevation_mask,
    compute_slope_degrees,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
BUILD_DIR = DATA_DIR / "buildability"
GEOTIFF_ZIP = DATA_DIR / "Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip"
PVOUT_TIF_PATH = "Indonesia_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/PVOUT.tif"
OUT_DIR = REPO_ROOT / "outputs" / "assets"

# Minimum buildable pixels required in a 4×4 block for the web raster.
# At 1 (old default), a single isolated buildable pixel would appear as a large blob
# on the map due to 4× downsampling. Requiring ≥2 reduces visual false positives.
MIN_BUILDABLE_PER_BLOCK: int = 2


def _load_pvout() -> tuple[np.ndarray, rasterio.profiles.Profile]:
    """Load full PVOUT raster from zip."""
    with zipfile.ZipFile(GEOTIFF_ZIP) as z:
        tif_bytes = z.read(PVOUT_TIF_PATH)

    with rasterio.open(io.BytesIO(tif_bytes)) as src:
        data = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        data[data <= 0] = np.nan
        return data, profile


def _rasterize_shp_full(
    shp_path: Path,
    out_shape: tuple[int, int],
    transform: rasterio.transform.Affine,
) -> np.ndarray:
    """Rasterize a shapefile to match the PVOUT grid. Returns binary mask (1=excluded)."""
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
    """Read a raster and resample to the PVOUT grid."""
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
    threshold: float = LAND_COVER_BUILDABLE_THRESHOLD,
) -> np.ndarray | None:
    """Resample categorical land cover to a binary buildability mask.

    Instead of mode resampling (which discards sub-pixel detail at 10m→1km),
    this reads the source data, creates a binary buildable/excluded array,
    then resamples with average to get a buildable fraction per output pixel.
    Pixels with fraction >= threshold are buildable (0), else excluded (1).

    Returns:
        uint8 mask array (1=excluded, 0=buildable), or None on failure.
    """
    print(f"    Resampling {raster_path.name} (binary-threshold at {threshold:.0%})...")
    try:
        with rasterio.open(raster_path) as src:
            # Read full source data
            raw = src.read(1)

            # Binary: 1.0 = buildable (not excluded), 0.0 = excluded
            binary = np.ones_like(raw, dtype=np.float32)
            for code in exclude_codes:
                binary[raw == code] = 0.0

            # Handle nodata
            nodata = src.nodata
            if nodata is not None:
                binary[raw == nodata] = 0.0

            # Resample binary with average → buildable fraction (0.0–1.0)
            fraction = np.zeros(out_shape, dtype=np.float32)
            reproject(
                source=binary,
                destination=fraction,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:4326",
                resampling=Resampling.average,
                src_nodata=None,
                dst_nodata=np.nan,
            )

            # Threshold: excluded (1) where buildable fraction < threshold
            mask = np.zeros(out_shape, dtype=np.uint8)
            mask[~np.isfinite(fraction) | (fraction < threshold)] = 1
            return mask
    except Exception as e:
        print(f"    WARNING: Could not read {raster_path.name}: {e}")
        return None


def build_buildable_raster():
    """Generate the nationwide buildable PVOUT raster."""
    print("\n=== Building nationwide buildable PVOUT raster ===\n")

    # 1. Load PVOUT
    print("  Loading PVOUT raster...")
    pvout, profile = _load_pvout()
    h, w = pvout.shape
    transform = profile["transform"]
    print(f"    Shape: {h}x{w}, bounds: {rasterio.transform.array_bounds(h, w, transform)}")

    valid_before = np.count_nonzero(np.isfinite(pvout))
    result = pvout.copy()

    # 2. Kawasan Hutan
    kh_path = BUILD_DIR / "kawasan_hutan.shp"
    if kh_path.exists():
        kh_mask = _rasterize_shp_full(kh_path, (h, w), transform)
        result = apply_exclusion_mask(result, kh_mask)
        excluded = valid_before - np.count_nonzero(result > 0)
        print(
            f"    Kawasan Hutan: excluded {excluded:,} pixels ({excluded / valid_before * 100:.1f}%)"
        )
        del kh_mask
    else:
        print("    Kawasan Hutan: not found, skipping")

    # 3. Peatland
    peat_path = BUILD_DIR / "peatland_klhk.shp"
    if peat_path.exists():
        before = np.count_nonzero(result > 0)
        peat_mask = _rasterize_shp_full(peat_path, (h, w), transform)
        result = apply_exclusion_mask(result, peat_mask)
        excluded = before - np.count_nonzero(result > 0)
        print(f"    Peatland: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
        del peat_mask
    else:
        print("    Peatland: not found, skipping")

    # 4. Land cover (ESA WorldCover) — binary-threshold resampling (M13)
    lc_path = BUILD_DIR / "esa_worldcover.vrt"
    if lc_path.exists():
        before = np.count_nonzero(result > 0)
        lc_mask = _resample_landcover_binary(lc_path, (h, w), transform, LAND_COVER_EXCLUDE_CODES)
        if lc_mask is not None:
            result = apply_exclusion_mask(result, lc_mask)
            excluded = before - np.count_nonzero(result > 0)
            print(f"    Land cover: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
            del lc_mask
    else:
        print("    Land cover VRT: not found, skipping")

    # 5. Slope & elevation (DEM)
    dem_path = BUILD_DIR / "dem_indonesia.tif"
    if dem_path.exists():
        before = np.count_nonzero(result > 0)
        dem_arr = _resample_raster_to_grid(dem_path, (h, w), transform, categorical=False)
        if dem_arr is not None:
            # Compute pixel size in metres for slope calculation
            import math

            mid_lat = (
                profile["transform"].f + profile["transform"].f + h * profile["transform"].e
            ) / 2
            pixel_size_m = (
                abs(profile["transform"].a) * 111320 * math.cos(math.radians(abs(mid_lat)))
            )
            slope = compute_slope_degrees(dem_arr, pixel_size_m)
            result = apply_slope_elevation_mask(result, slope, dem_arr)
            excluded = before - np.count_nonzero(result > 0)
            print(f"    Slope/elev: excluded {excluded:,} pixels ({excluded / before * 100:.1f}%)")
            del dem_arr, slope
    else:
        print("    DEM: not found, skipping")

    # Set non-buildable pixels to NaN
    result[result <= 0] = np.nan
    valid_after = np.count_nonzero(np.isfinite(result))
    print(
        f"\n  Summary: {valid_before:,} valid → {valid_after:,} buildable ({valid_after / valid_before * 100:.1f}% retained)"
    )

    # Save web-resolution version (downsampled ~4x)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "buildable_pvout_web.tif"

    out_h, out_w = h // 4, w // 4
    out_transform = transform_from_bounds(
        *rasterio.transform.array_bounds(h, w, transform), out_w, out_h
    )

    # Downsample using average (preserves buildable pixel density)
    downsampled = np.full((out_h, out_w), np.nan, dtype=np.float32)
    for i in range(out_h):
        for j in range(out_w):
            block = result[i * 4 : (i + 1) * 4, j * 4 : (j + 1) * 4]
            finite = block[np.isfinite(block)]
            if len(finite) >= MIN_BUILDABLE_PER_BLOCK:
                downsampled[i, j] = np.mean(finite)

    out_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": out_w,
        "height": out_h,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": out_transform,
        "nodata": np.nan,
        "compress": "deflate",
    }

    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(downsampled, 1)

    print(f"\n  Output: {out_path.relative_to(REPO_ROOT)} ({out_h}x{out_w})")
    print(f"  File size: {out_path.stat().st_size / 1024:.0f} KB")

    return out_path


if __name__ == "__main__":
    build_buildable_raster()
