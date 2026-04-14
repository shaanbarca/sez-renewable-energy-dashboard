# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
download_road_data.py — Build road proximity raster from OpenStreetMap.

Downloads the Geofabrik Indonesia PBF extract, filters for motorable roads,
and computes a nationwide distance-to-nearest-road raster at ~1km resolution.

Usage:
    uv run python scripts/download_road_data.py [--check-only] [--skip-download]

Output:
    data/buildability/road_distance_km.tif   (~50MB, float32, deflate)
    data/osm/indonesia-latest.osm.pbf        (~1.7GB, cached)

Road types included:
    motorway, trunk, primary, secondary, tertiary
    (residential, service, track, footway, path, cycleway excluded)

Distance is Euclidean (great-circle approximated via latitude-corrected EDT).
At Indonesia's equatorial latitude (-11 to +6), the distortion is <2%.

Reference: METHODOLOGY_CONSOLIDATED.md Section 3.3, Layer 3a
"""

from __future__ import annotations

import argparse
import math
import sys
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import geopandas as gpd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
OSM_DIR = DATA_DIR / "osm"
BUILD_DIR = DATA_DIR / "buildability"

GEOFABRIK_URL = "https://download.geofabrik.de/asia/indonesia-latest.osm.pbf"
PBF_PATH = OSM_DIR / "indonesia-latest.osm.pbf"
OUT_PATH = BUILD_DIR / "road_distance_km.tif"

# Target grid matches wind/PVOUT resolution (~0.00833 deg, ~1km)
TARGET_PIXEL_DEG: float = 0.008333

# Indonesia extent (generous bounding box covering all islands)
BOUNDS_LEFT: float = 92.0
BOUNDS_RIGHT: float = 142.0
BOUNDS_BOTTOM: float = -14.0
BOUNDS_TOP: float = 8.0

# Road types to include (motorable roads suitable for construction access)
MOTORABLE_HIGHWAY_TYPES: tuple[str, ...] = (
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
)

# Approximate km per degree latitude (equatorial)
KM_PER_DEG_LAT: float = 111.32

# Minimum PBF file size to consider complete (1 GB)
MIN_PBF_SIZE_BYTES: int = 1_000_000_000


def download_indonesia_pbf(check_only: bool = False) -> bool:
    """Download the Indonesia OSM PBF extract from Geofabrik.

    Args:
        check_only: If True, only check if file exists without downloading.

    Returns:
        True if the PBF file is ready (exists and appears complete).
    """
    if PBF_PATH.exists() and PBF_PATH.stat().st_size >= MIN_PBF_SIZE_BYTES:
        size_gb = PBF_PATH.stat().st_size / 1e9
        print(f"  PBF exists: {PBF_PATH} ({size_gb:.1f} GB)")
        return True

    if check_only:
        print(f"  PBF not found or incomplete: {PBF_PATH}")
        return False

    OSM_DIR.mkdir(parents=True, exist_ok=True)
    print("  Downloading Indonesia PBF from Geofabrik (~1.7 GB)...")
    print(f"  URL: {GEOFABRIK_URL}")
    print(f"  Destination: {PBF_PATH}")

    try:

        def _progress(block_num: int, block_size: int, total_size: int) -> None:
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 / total_size)
                mb = downloaded / 1e6
                print(f"\r  {mb:.0f} MB ({pct:.0f}%)", end="", flush=True)

        urllib.request.urlretrieve(GEOFABRIK_URL, PBF_PATH, reporthook=_progress)
        print()  # newline after progress
    except Exception as e:
        print(f"\n  ERROR: Download failed: {e}")
        if PBF_PATH.exists():
            PBF_PATH.unlink()
        return False

    if PBF_PATH.stat().st_size < MIN_PBF_SIZE_BYTES:
        print(f"  WARNING: PBF file seems too small ({PBF_PATH.stat().st_size} bytes)")
        return False

    size_gb = PBF_PATH.stat().st_size / 1e9
    print(f"  Downloaded: {size_gb:.1f} GB")
    return True


def extract_motorable_roads(pbf_path: Path) -> gpd.GeoDataFrame:
    """Extract motorable road geometries from an OSM PBF file.

    Uses pyogrio to read the PBF with a SQL filter on the highway tag.
    Returns a GeoDataFrame with LineString geometries in EPSG:4326.
    """
    import geopandas as gpd

    highway_list = ", ".join(f"'{h}'" for h in MOTORABLE_HIGHWAY_TYPES)
    where_clause = f"highway IN ({highway_list})"

    print(f"  Extracting roads: {where_clause}")
    print(f"  Source: {pbf_path}")

    gdf = gpd.read_file(
        pbf_path,
        layer="lines",
        where=where_clause,
        engine="pyogrio",
    )

    # Keep only valid geometries
    gdf = gdf[gdf.geometry.notna() & gdf.geometry.is_valid]
    print(f"  Extracted {len(gdf):,} road segments")

    return gdf


def build_road_distance_raster(roads_gdf: gpd.GeoDataFrame, out_path: Path) -> Path:
    """Compute a nationwide distance-to-nearest-road raster.

    Strategy:
    1. Rasterize road geometries to a binary mask at ~1km resolution
    2. Compute Euclidean distance transform on the inverted mask
    3. Convert pixel distances to km using latitude-corrected sampling

    Args:
        roads_gdf: GeoDataFrame of road LineString geometries (EPSG:4326).
        out_path:  Output path for the distance raster.

    Returns:
        Path to the output GeoTIFF.
    """
    import rasterio
    import rasterio.features
    import rasterio.transform
    from scipy.ndimage import distance_transform_edt

    # Compute target grid dimensions
    width = int((BOUNDS_RIGHT - BOUNDS_LEFT) / TARGET_PIXEL_DEG)
    height = int((BOUNDS_TOP - BOUNDS_BOTTOM) / TARGET_PIXEL_DEG)
    print(f"  Target grid: {height}x{width} ({TARGET_PIXEL_DEG * KM_PER_DEG_LAT:.2f} km/px)")

    transform = rasterio.transform.from_bounds(
        BOUNDS_LEFT, BOUNDS_BOTTOM, BOUNDS_RIGHT, BOUNDS_TOP, width, height
    )

    # 1. Rasterize roads to binary presence mask
    print("  Rasterizing road geometries...")
    valid_geoms = [geom for geom in roads_gdf.geometry if geom is not None]
    if not valid_geoms:
        print("  WARNING: No valid road geometries found")
        # Write an all-NaN raster (conservatively excludes everything)
        distance_km = np.full((height, width), np.nan, dtype=np.float32)
    else:
        road_mask = rasterio.features.rasterize(
            [(geom, 1) for geom in valid_geoms],
            out_shape=(height, width),
            transform=transform,
            fill=0,
            dtype=np.uint8,
        )
        road_pixels = int(road_mask.sum())
        print(f"    Road pixels: {road_pixels:,} ({road_pixels / (height * width) * 100:.1f}%)")

        # 2. Distance transform on inverted mask (1 = no road, compute distance to nearest road)
        print("  Computing distance transform...")
        no_road = road_mask == 0
        del road_mask

        # Latitude-corrected sampling: at equatorial Indonesia, 1 pixel of latitude
        # is ~0.926 km, 1 pixel of longitude varies with cos(lat).
        # Use midpoint latitude for the x-sampling correction.
        mid_lat = (BOUNDS_TOP + BOUNDS_BOTTOM) / 2.0
        pixel_km_y = TARGET_PIXEL_DEG * KM_PER_DEG_LAT
        pixel_km_x = TARGET_PIXEL_DEG * KM_PER_DEG_LAT * math.cos(math.radians(abs(mid_lat)))

        distance_km = distance_transform_edt(
            no_road,
            sampling=(pixel_km_y, pixel_km_x),
        ).astype(np.float32)
        del no_road

        # Road pixels themselves get distance 0
        print(f"    Distance range: {distance_km.min():.1f} - {distance_km.max():.1f} km")

    # 3. Write output GeoTIFF
    out_path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": width,
        "height": height,
        "count": 1,
        "crs": "EPSG:4326",
        "transform": transform,
        "compress": "deflate",
        "predictor": 2,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "nodata": None,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(distance_km, 1)

    size_mb = out_path.stat().st_size / 1e6
    print(f"  Written: {out_path} ({size_mb:.1f} MB)")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build road proximity raster from OpenStreetMap")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check file status, do not download or process",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip PBF download (use existing file)",
    )
    args = parser.parse_args()

    print("\n=== Road Proximity Raster Builder ===\n")

    # Check output status
    if OUT_PATH.exists():
        size_mb = OUT_PATH.stat().st_size / 1e6
        print(f"  Output exists: {OUT_PATH} ({size_mb:.1f} MB)")
        if args.check_only:
            print("  Status: READY")
            return

    # 1. Get PBF
    if not args.skip_download:
        if not download_indonesia_pbf(check_only=args.check_only):
            if args.check_only:
                print("\n  Status: PBF not available")
                return
            print("\nFailed to obtain PBF file.")
            sys.exit(1)
    else:
        if not PBF_PATH.exists():
            print(f"  ERROR: --skip-download but PBF not found at {PBF_PATH}")
            sys.exit(1)
        print(f"  Using existing PBF: {PBF_PATH}")

    if args.check_only:
        print("\n  Status: PBF ready, raster needs building")
        return

    # 2. Extract roads
    roads = extract_motorable_roads(PBF_PATH)
    if len(roads) == 0:
        print("  WARNING: No roads extracted. Check PBF file integrity.")
        sys.exit(1)

    # 3. Build distance raster
    build_road_distance_raster(roads, OUT_PATH)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
