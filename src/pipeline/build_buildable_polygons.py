"""
build_buildable_polygons — Convert buildable raster to polygon GeoJSON.

Reads the precomputed buildable PVOUT raster (buildable_pvout_web.tif) and
converts contiguous buildable areas into polygon geometries with per-polygon
properties (area, average PVOUT, capacity).

Output:
  outputs/assets/buildable_polygons.geojson — vector layer for dashboard map

Usage:
  uv run python -m src.pipeline.build_buildable_polygons
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

from src.pipeline.buildability_filters import HA_PER_MWP

REPO_ROOT = Path(__file__).resolve().parents[2]
RASTER_PATH = REPO_ROOT / "outputs" / "assets" / "buildable_pvout_web.tif"
OUT_PATH = REPO_ROOT / "outputs" / "assets" / "buildable_polygons.geojson"

# Minimum polygon area to keep (hectares). At ~3.7km pixel size, one pixel ≈ 1,370 ha.
# Filter out sub-pixel noise fragments.
MIN_AREA_HA: float = 50.0

# Geometry simplification tolerance in degrees (~0.5km at equator).
SIMPLIFY_TOLERANCE: float = 0.005


def _approx_area_ha(geom, centroid_lat: float) -> float:
    """Approximate polygon area in hectares from WGS84 coordinates.

    Uses cos(lat) correction for longitude distortion.
    1 degree ≈ 111.32 km at equator, so 1 deg² ≈ 111.32² × cos(lat) km² = × 100 ha/km².
    """
    deg2_to_km2 = 111.32**2 * math.cos(math.radians(abs(centroid_lat)))
    return geom.area * deg2_to_km2 * 100  # km² → ha


def build_buildable_polygons() -> Path:
    """Generate buildable area polygons from the raster."""
    print("\n=== Building buildable area polygons (M14) ===\n")

    if not RASTER_PATH.exists():
        raise FileNotFoundError(
            f"Buildable raster not found: {RASTER_PATH}\n"
            "Run 'uv run python -m src.pipeline.build_buildable_raster' first."
        )

    # Read raster
    with rasterio.open(RASTER_PATH) as src:
        data = src.read(1)
        transform = src.transform
        crs = src.crs

    print(f"  Raster: {data.shape[0]}x{data.shape[1]}, CRS={crs}")

    # Binary mask: True where buildable (finite and > 0)
    mask = np.isfinite(data) & (data > 0)
    mask_uint8 = mask.astype(np.uint8)
    n_buildable = int(mask.sum())
    print(f"  Buildable pixels: {n_buildable:,}")

    # Vectorize: extract polygon geometries from contiguous buildable regions
    print("  Vectorizing...")
    records = []
    for geom_dict, value in shapes(mask_uint8, mask=mask, transform=transform):
        if value == 0:
            continue
        geom = shape(geom_dict)
        centroid = geom.centroid
        area_ha = _approx_area_ha(geom, centroid.y)

        if area_ha < MIN_AREA_HA:
            continue

        # Compute average PVOUT for pixels within this polygon
        # Use the polygon's bounding box to extract raster values
        minx, miny, maxx, maxy = geom.bounds
        # Convert bounds to pixel coordinates
        col_min = max(0, int((minx - transform.c) / transform.a))
        col_max = min(data.shape[1], int((maxx - transform.c) / transform.a) + 1)
        row_min = max(0, int((maxy - transform.f) / transform.e))
        row_max = min(data.shape[0], int((miny - transform.f) / transform.e) + 1)

        patch = data[row_min:row_max, col_min:col_max]
        finite_vals = patch[np.isfinite(patch) & (patch > 0)]
        avg_pvout_daily = float(np.mean(finite_vals)) if len(finite_vals) > 0 else 0.0
        avg_pvout_annual = round(avg_pvout_daily * 365, 0)

        capacity_mwp = round(area_ha / HA_PER_MWP, 1)

        records.append(
            {
                "geometry": geom,
                "area_ha": round(area_ha, 0),
                "avg_pvout_annual": avg_pvout_annual,
                "capacity_mwp": capacity_mwp,
                "centroid_lat": round(centroid.y, 4),
                "centroid_lon": round(centroid.x, 4),
            }
        )

    print(f"  Polygons (after {MIN_AREA_HA} ha filter): {len(records):,}")

    if not records:
        print("  WARNING: No polygons generated. Check raster data.")
        # Write empty FeatureCollection
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        return OUT_PATH

    # Build GeoDataFrame
    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")

    # Simplify geometries for web performance
    gdf["geometry"] = gdf.geometry.simplify(SIMPLIFY_TOLERANCE, preserve_topology=True)

    # Remove any empty geometries after simplification
    gdf = gdf[~gdf.geometry.is_empty]
    print(f"  After simplification: {len(gdf):,} polygons")

    # Sort by area descending (largest first for rendering)
    gdf = gdf.sort_values("area_ha", ascending=False).reset_index(drop=True)

    # Save
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(OUT_PATH, driver="GeoJSON")

    size_kb = OUT_PATH.stat().st_size / 1024
    size_mb = size_kb / 1024
    print(f"\n  Output: {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"  File size: {size_mb:.1f} MB ({size_kb:.0f} KB)")
    print(f"  Total buildable area: {gdf['area_ha'].sum():,.0f} ha")
    print(f"  Total capacity: {gdf['capacity_mwp'].sum():,.0f} MWp")

    return OUT_PATH


if __name__ == "__main__":
    build_buildable_polygons()
