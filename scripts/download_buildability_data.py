"""
download_buildability_data.py — Acquire geospatial data for the land suitability filter.

Run this script ONCE before running the buildability pipeline steps.

Usage:
    uv run python scripts/download_buildability_data.py [--check-only]

What this script does automatically:
    1. Creates data/buildability/ directory
    2. Downloads Copernicus DEM GLO-30 tiles for all KEK 50km catchment areas
       from the public AWS S3 mirror (no authentication required)
    3. Mosaics tiles → data/buildability/dem_indonesia.tif
    4. Downloads ESA WorldCover v200 (2021) 3°×3° tiles covering all KEK catchments
       from the public AWS S3 mirror (no authentication required)
    5. Mosaics tiles → data/buildability/esa_worldcover.tif

What requires MANUAL download (KLHK portal requires a logged-in browser session):
    See printed instructions below.

Disk requirements:
    Copernicus DEM tiles: ~5–15 MB per 1°×1° tile, ~50–200 tiles needed → 0.5–3 GB
    ESA WorldCover tiles: ~100–400 MB per 3°×3° tile, ~20–40 tiles needed → 2–15 GB
    KLHK Kawasan Hutan shapefile: ~200–500 MB (national coverage)
    KLHK Peatland zones: ~50–150 MB
"""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
BUILD_DIR = REPO_ROOT / "data" / "buildability"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"

# Copernicus DEM GLO-30 on AWS S3 (public, no auth)
COP_DEM_BASE = (
    "https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/"
    "Copernicus_DSM_COG_10_{NS}{lat:02d}_00_{EW}{lon:03d}_00_DEM/"
    "Copernicus_DSM_COG_10_{NS}{lat:02d}_00_{EW}{lon:03d}_00_DEM.tif"
)

# ESA WorldCover v200 (2021) on AWS S3 (public, no auth)
# Tiles are 3°×3°, named by SW corner: {NS}{lat:02d}{EW}{lon:03d}
ESA_WC_BASE = (
    "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
    "v200/2021/map/"
    "ESA_WorldCover_10m_2021_v200_{TILE}_Map.tif"
)

# Buffer around each KEK centroid when computing needed tiles (degrees, ~50km at equator)
TILE_BUFFER_DEG = 0.5


# ─── DEM helpers ──────────────────────────────────────────────────────────────


def _needed_tiles(kek_df: pd.DataFrame) -> list[tuple[int, int]]:
    """Return a deduplicated list of (lat_floor, lon_floor) 1°×1° DEM tiles needed."""
    tiles: set[tuple[int, int]] = set()
    for _, row in kek_df.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        lat_min = int(math.floor(lat - TILE_BUFFER_DEG))
        lat_max = int(math.floor(lat + TILE_BUFFER_DEG))
        lon_min = int(math.floor(lon - TILE_BUFFER_DEG))
        lon_max = int(math.floor(lon + TILE_BUFFER_DEG))
        for la in range(lat_min, lat_max + 1):
            for lo in range(lon_min, lon_max + 1):
                tiles.add((la, lo))
    return sorted(tiles)


def _tile_url(lat_floor: int, lon_floor: int) -> str:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return COP_DEM_BASE.format(NS=ns, lat=abs(lat_floor), EW=ew, lon=abs(lon_floor))


def _tile_path(lat_floor: int, lon_floor: int) -> Path:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    name = f"cop_dem_{ns}{abs(lat_floor):02d}_{ew}{abs(lon_floor):03d}.tif"
    return BUILD_DIR / "dem_tiles" / name


def download_cop_dem(kek_df: pd.DataFrame, check_only: bool = False) -> bool:
    """Download Copernicus DEM tiles for all KEK catchment areas."""
    tiles = _needed_tiles(kek_df)
    print(f"\n[DEM] {len(tiles)} Copernicus GLO-30 tiles needed for {len(kek_df)} KEKs")

    tile_dir = BUILD_DIR / "dem_tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)

    missing = [t for t in tiles if not _tile_path(*t).exists()]
    print(f"[DEM] {len(tiles) - len(missing)} already downloaded, {len(missing)} to fetch")

    if check_only:
        if missing:
            print(f"[DEM] Missing tiles: {missing[:5]}{'...' if len(missing) > 5 else ''}")
        return len(missing) == 0

    for i, (lat_floor, lon_floor) in enumerate(missing, 1):
        url = _tile_url(lat_floor, lon_floor)
        dest = _tile_path(lat_floor, lon_floor)
        print(f"[DEM] ({i}/{len(missing)}) Downloading {dest.name} ...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"OK ({dest.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"FAILED: {e}")
            print(f"       URL: {url}")
            print("       Tile may not exist (ocean tile or polar region). Continuing.")

    # Mosaic all tiles into a single GeoTIFF
    out_path = BUILD_DIR / "dem_indonesia.tif"
    if not out_path.exists() or missing:
        _mosaic_dem_tiles(tile_dir, out_path)

    return out_path.exists()


def _mosaic_dem_tiles(tile_dir: Path, out_path: Path) -> None:
    """Merge all DEM tiles into a single GeoTIFF using rasterio."""
    try:
        import rasterio
        from rasterio.merge import merge
    except ImportError:
        print("[DEM] rasterio not available — cannot mosaic. Install it and re-run.")
        return

    tif_files = sorted(tile_dir.glob("*.tif"))
    if not tif_files:
        print("[DEM] No tiles to mosaic.")
        return

    print(f"[DEM] Mosaicking {len(tif_files)} tiles → {out_path.name} ...", end=" ", flush=True)
    datasets = [rasterio.open(f) for f in tif_files]
    try:
        mosaic, transform = merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update(
            {
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": transform,
                "driver": "GTiff",
                "compress": "deflate",
                "tiled": True,
                "blockxsize": 512,
                "blockysize": 512,
            }
        )
        with rasterio.open(out_path, "w", **profile) as dst:
            dst.write(mosaic)
        print(f"OK ({out_path.stat().st_size // (1024 * 1024)} MB)")
    finally:
        for ds in datasets:
            ds.close()


# ─── ESA WorldCover helpers ────────────────────────────────────────────────────


def _needed_esa_tiles(kek_df: pd.DataFrame) -> list[tuple[int, int]]:
    """Return deduplicated list of (lat_sw, lon_sw) 3°×3° ESA WorldCover tiles needed.

    Tile SW corner is the floor of the coordinate rounded down to the nearest 3°.
    Example: lat=-3.2 → lat_sw=-6 (tile covers -6° to -3°).
    """
    tiles: set[tuple[int, int]] = set()
    for _, row in kek_df.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        # expand by buffer, then snap to 3° grid
        for edge_lat in [lat - TILE_BUFFER_DEG, lat + TILE_BUFFER_DEG]:
            for edge_lon in [lon - TILE_BUFFER_DEG, lon + TILE_BUFFER_DEG]:
                lat_sw = int(math.floor(edge_lat / 3.0)) * 3
                lon_sw = int(math.floor(edge_lon / 3.0)) * 3
                tiles.add((lat_sw, lon_sw))
    return sorted(tiles)


def _esa_tile_name(lat_sw: int, lon_sw: int) -> str:
    """Return ESA WorldCover tile name from SW corner coordinates.

    Examples: (0, 96) → 'N00E096', (-3, 96) → 'S03E096'
    """
    ns = "N" if lat_sw >= 0 else "S"
    ew = "E" if lon_sw >= 0 else "W"
    return f"{ns}{abs(lat_sw):02d}{ew}{abs(lon_sw):03d}"


def _esa_tile_url(lat_sw: int, lon_sw: int) -> str:
    return ESA_WC_BASE.format(TILE=_esa_tile_name(lat_sw, lon_sw))


def _esa_tile_path(lat_sw: int, lon_sw: int) -> Path:
    name = f"esa_wc_{_esa_tile_name(lat_sw, lon_sw)}.tif"
    return BUILD_DIR / "esa_tiles" / name


def download_esa_worldcover(kek_df: pd.DataFrame, check_only: bool = False) -> bool:
    """Download ESA WorldCover v200 (2021) tiles for all KEK catchment areas.

    Builds a VRT (virtual mosaic) rather than a full GeoTIFF to avoid loading
    all tiles into memory at once. rasterio reads windows from the VRT on demand.
    """
    tiles = _needed_esa_tiles(kek_df)
    print(f"\n[ESA] {len(tiles)} ESA WorldCover 3°×3° tiles needed for {len(kek_df)} KEKs")

    tile_dir = BUILD_DIR / "esa_tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)

    missing = [t for t in tiles if not _esa_tile_path(*t).exists()]
    print(f"[ESA] {len(tiles) - len(missing)} already downloaded, {len(missing)} to fetch")

    if check_only:
        if missing:
            print(
                f"[ESA] Missing tiles: {[_esa_tile_name(*t) for t in missing[:5]]}{'...' if len(missing) > 5 else ''}"
            )
        return (BUILD_DIR / "esa_worldcover.vrt").exists()

    for i, (lat_sw, lon_sw) in enumerate(missing, 1):
        url = _esa_tile_url(lat_sw, lon_sw)
        dest = _esa_tile_path(lat_sw, lon_sw)
        print(
            f"[ESA] ({i}/{len(missing)}) Downloading {_esa_tile_name(lat_sw, lon_sw)} ...",
            end=" ",
            flush=True,
        )
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"OK ({dest.stat().st_size // (1024 * 1024)} MB)")
        except Exception as e:
            print(f"FAILED: {e}")
            print(f"       URL: {url}")
            print("       Tile may not exist (ocean-only tile). Continuing.")

    out_vrt = BUILD_DIR / "esa_worldcover.vrt"
    if not out_vrt.exists() or missing:
        _build_esa_vrt(tile_dir, out_vrt)

    return out_vrt.exists()


def _build_esa_vrt(tile_dir: Path, out_vrt: Path) -> None:
    _build_vrt(tile_dir, out_vrt, label="ESA")


# ─── GFW Peatlands helpers ────────────────────────────────────────────────────

GFW_PEATLANDS_INDEX = BUILD_DIR / "Global_Peatlands.geojson"
IDN_BOUNDS = (
    95.0,
    -11.0,
    141.0,
    6.0,
)  # Indonesia bounding box (lon_min, lat_min, lon_max, lat_max)


def download_gfw_peatland(check_only: bool = False) -> bool:
    """Download GFW Peatlands raster tiles for Indonesia using the tile index GeoJSON.

    Reads data/buildability/Global_Peatlands.geojson (tile index downloaded from GFW),
    filters tiles that intersect Indonesia, downloads each GeoTIFF, then builds a VRT.
    """
    if not GFW_PEATLANDS_INDEX.exists():
        print(f"\n[PEAT] {GFW_PEATLANDS_INDEX.name} not found — skipping peatland download.")
        print("       Download from: https://www.globalforestwatch.org/dashboards/global/")
        return (BUILD_DIR / "peatland.vrt").exists()

    import json

    with open(GFW_PEATLANDS_INDEX) as f:
        tile_index = json.load(f)

    try:
        import shapely.geometry as sg

        idn_box = sg.box(*IDN_BOUNDS)
        idn_tiles = [
            feat
            for feat in tile_index["features"]
            if sg.shape(feat["geometry"]).intersects(idn_box)
        ]
    except ImportError:
        # Fallback: include all tiles (shapely not available)
        idn_tiles = tile_index["features"]

    print(f"\n[PEAT] {len(idn_tiles)} GFW peatland tiles cover Indonesia")

    tile_dir = BUILD_DIR / "peat_tiles"
    tile_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        t for t in idn_tiles if not (tile_dir / f"peat_{t['properties']['tile_id']}.tif").exists()
    ]
    print(f"[PEAT] {len(idn_tiles) - len(missing)} already downloaded, {len(missing)} to fetch")

    if check_only:
        return (BUILD_DIR / "peatland.vrt").exists()

    for i, feat in enumerate(missing, 1):
        tile_id = feat["properties"]["tile_id"]
        url = feat["properties"]["download_url"]
        dest = tile_dir / f"peat_{tile_id}.tif"
        print(f"[PEAT] ({i}/{len(missing)}) Downloading {tile_id} ...", end=" ", flush=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"OK ({dest.stat().st_size // (1024 * 1024)} MB)")
        except Exception as e:
            print(f"FAILED: {e}")
            print(f"       URL: {url[:80]}...")

    out_vrt = BUILD_DIR / "peatland.vrt"
    if not out_vrt.exists() or missing:
        _build_vrt(tile_dir, out_vrt, label="PEAT")

    return out_vrt.exists()


def _build_vrt(tile_dir: Path, out_vrt: Path, label: str = "") -> None:
    """Build a VRT mosaic from all GeoTIFF tiles in tile_dir using gdalbuildvrt."""
    tif_files = sorted(tile_dir.glob("*.tif"))
    if not tif_files:
        print(f"[{label}] No tiles to build VRT from.")
        return
    print(
        f"[{label}] Building VRT from {len(tif_files)} tiles → {out_vrt.name} ...",
        end=" ",
        flush=True,
    )
    try:
        subprocess.run(
            ["gdalbuildvrt", str(out_vrt)] + [str(f) for f in tif_files],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"OK ({out_vrt.stat().st_size} bytes)")
    except FileNotFoundError:
        print("FAILED — gdalbuildvrt not found. Install GDAL (brew install gdal) and re-run.")
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {e.stderr.strip()}")


# ─── Manual instructions ──────────────────────────────────────────────────────


def print_manual_instructions() -> None:
    """Print step-by-step instructions for downloading remaining KLHK files manually."""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║          MANUAL DOWNLOAD REQUIRED — KLHK Geospatial Data                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

One file must be downloaded manually from the KLHK (Ministry of Environment
and Forestry) geoportal. A registered account may be required.

Portal: https://geoportal.menlhk.go.id/

─────────────────────────────────────────────────────────────────────────────
FILE 1: Kawasan Hutan (Forest Estate Boundary)   [Layer 1a — highest impact]
─────────────────────────────────────────────────────────────────────────────
  Navigate: Peta Tematik → Kehutanan → Kawasan Hutan
  Download: National shapefile (all provinces)
  Save as:  data/buildability/kawasan_hutan.shp
            (the .dbf, .prj, .shx files in the same folder)

  Covers all KH sub-categories (conservation, protection, production forest).
  All are treated as hard exclusions. See METHODOLOGY_CONSOLIDATED.md §2.5 Layer 1a.

─────────────────────────────────────────────────────────────────────────────
NOTE: Peatland (Layer 1b) and land cover (Layer 1c/d) are now automated:
  - Peatland: from Global_Peatlands.geojson tile index (GFW v20230315)
  - Land cover: from ESA WorldCover v200 2021 (AWS public S3)
─────────────────────────────────────────────────────────────────────────────
After downloading, re-run the pipeline:

  uv run python run_pipeline.py fct_kek_resource

The pipeline gracefully handles missing files — active layers are applied
and resource_quality reflects how many of the 4 layers were applied.
─────────────────────────────────────────────────────────────────────────────
""")


def check_status() -> None:
    """Print current status of all required buildability files."""
    files = {
        "dem_indonesia.tif": BUILD_DIR / "dem_indonesia.tif",
        "esa_worldcover.vrt": BUILD_DIR / "esa_worldcover.vrt",
        "kawasan_hutan.shp": BUILD_DIR / "kawasan_hutan.shp",
        "peatland.vrt": BUILD_DIR / "peatland.vrt",
    }
    print("\n[STATUS] data/buildability/ file check:")
    for name, path in files.items():
        status = "✅" if path.exists() else "❌"
        size = f"({path.stat().st_size // (1024 * 1024)} MB)" if path.exists() else "(missing)"
        print(f"  {status}  {name:45s} {size}")

    all_present = all(p.exists() for p in files.values())
    if all_present:
        print("\n✅ All buildability data files present. Run the pipeline:")
        print("   uv run python run_pipeline.py fct_kek_resource")
    else:
        missing_count = sum(1 for p in files.values() if not p.exists())
        print(f"\n⚠️  {missing_count} file(s) missing. See instructions above.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check status; do not download anything.",
    )
    args = parser.parse_args()

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    if not DIM_KEK_CSV.exists():
        print(f"ERROR: {DIM_KEK_CSV} not found. Run the pipeline first:")
        print("  uv run python run_pipeline.py dim_kek")
        sys.exit(1)

    kek_df = pd.read_csv(DIM_KEK_CSV)[["kek_id", "latitude", "longitude"]]
    print(f"Loaded {len(kek_df)} KEKs from {DIM_KEK_CSV.relative_to(REPO_ROOT)}")

    if not args.check_only:
        download_cop_dem(kek_df, check_only=False)
        download_esa_worldcover(kek_df, check_only=False)
        download_gfw_peatland(check_only=False)

    print_manual_instructions()
    check_status()


if __name__ == "__main__":
    main()
