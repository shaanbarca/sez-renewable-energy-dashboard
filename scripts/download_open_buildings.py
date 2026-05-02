"""
download_open_buildings.py — Local equivalent of the Google Open Buildings v3
Colab notebook, without TensorFlow.

Downloads the Indonesia subset of Google Open Buildings v3 from the public
GCS bucket `gs://open-buildings-data/v3/polygons_s2_level_6_gzip_no_header`,
clips rows to inside the country boundary, and concatenates into a single
gzipped CSV at `data/open_buildings/idn_open_buildings.csv.gz`.

# Why a local script (vs the Colab)

- Colab free tier lags hard on Indonesia (many S2 cells, free CPU/network).
- Colab requires `swig` + `tensorflow` (~2 GB) just to read public GCS files.
- Local script uses `gcsfs` (anonymous mode) + `s2sphere` (pure Python).
  No swig compile step, no TF, no auth.

# Dependencies

Already in pyproject.toml: pandas, geopandas, shapely, tqdm.

NEW deps this script needs (install before first run):
    uv add gcsfs s2sphere

# Usage

    uv run python scripts/download_open_buildings.py \\
        --output data/open_buildings/idn_open_buildings.csv.gz

Optional flags:
    --workers N         Parallel download workers (default: 4)
    --resume            Skip S2 cells already present in --tmp-dir
    --tmp-dir PATH      Where to stash per-cell intermediate files
                        (default: data/open_buildings/_tmp_cells)

# Output schema

CSV with header: latitude,longitude,area_in_meters,confidence,geometry,full_plus_code

`geometry` column is a WKT polygon string in EPSG:4326. Same schema as the
Colab notebook produces, so `scripts/preprocess_open_buildings.py` consumes
it directly.

# Disk + time

- Indonesia covers ~50-100 S2 level-6 cells.
- Each cell is 100-500 MB compressed.
- Total output: estimated 5-15 GB compressed.
- Time on standard fiber + 4 workers: 30-60 minutes.

# Resumability

Per-cell intermediate files in --tmp-dir are kept on disk. If the script
fails mid-download, re-run with --resume to skip cells already finished.
The final concatenation step is fast (~1 minute).
"""

from __future__ import annotations

import argparse
import functools
import glob
import gzip
import multiprocessing
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data" / "open_buildings" / "idn_open_buildings.csv.gz"
DEFAULT_TMP_DIR = REPO_ROOT / "data" / "open_buildings" / "_tmp_cells"

# GCS bucket — public, anonymous access works.
GCS_BUCKET = "gs://open-buildings-data/v3/polygons_s2_level_6_gzip_no_header"

# Natural Earth low-res Indonesia boundary (110m resolution — fine for our
# downstream 2 km buffer; see spec §13.3).
NE_URL = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"

# CSV column order produced by GoB v3 polygon files (no header in source).
OUTPUT_HEADER = "latitude,longitude,area_in_meters,confidence,geometry,full_plus_code"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Google Open Buildings v3 Indonesia subset "
        "(local equivalent of the official Colab notebook).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output gzipped CSV path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--tmp-dir",
        type=Path,
        default=DEFAULT_TMP_DIR,
        help=f"Per-cell intermediate file dir (default: {DEFAULT_TMP_DIR.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Parallel download workers (default: 4).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip S2 cells already present in --tmp-dir from a prior run.",
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Verify deps are installed and exit. Run this first to catch missing packages.",
    )
    return parser.parse_args()


def check_deps() -> None:
    missing = []
    for mod in ("gcsfs", "s2sphere", "geopandas", "shapely", "pandas", "tqdm"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(f"ERROR: missing dependencies: {missing}", file=sys.stderr)
        print(f"  install with: uv add {' '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    print("All deps available.")


def load_indonesia_polygon():
    """Download Natural Earth ne_110m, return Indonesia geometry in EPSG:4326."""
    import io
    import zipfile

    import geopandas as gpd
    import requests

    print(f"Fetching Indonesia boundary from Natural Earth ({NE_URL})")
    r = requests.get(NE_URL, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        # Extract to tmp and read the .shp
        tmp = Path(tempfile.mkdtemp(prefix="ne_110m_"))
        zf.extractall(tmp)
        shp = next(tmp.glob("*.shp"))
        gdf = gpd.read_file(shp)
    idn = gdf[gdf["ISO_A3"] == "IDN"]
    if idn.empty:
        raise RuntimeError("Indonesia (ISO_A3=IDN) not found in Natural Earth shapefile")
    return idn.dissolve(by="ISO_A3").iloc[0].geometry


def get_s2_tokens(region_geometry) -> list[str]:
    """Return S2 level-6 cell tokens covering the region's bounding box."""
    import s2sphere

    min_lng, min_lat, max_lng, max_lat = region_geometry.bounds
    lo = s2sphere.LatLng.from_degrees(min_lat, min_lng)
    hi = s2sphere.LatLng.from_degrees(max_lat, max_lng)
    rect = s2sphere.LatLngRect.from_point_pair(lo, hi)

    coverer = s2sphere.RegionCoverer()
    coverer.min_level = 6
    coverer.max_level = 6
    coverer.max_cells = 1_000_000

    cells = coverer.get_covering(rect)
    return [c.to_token() for c in cells]


def s2_token_to_polygon(s2_token: str):
    """Convert an S2 token to a Shapely polygon in EPSG:4326."""
    import s2sphere
    from shapely.geometry import Polygon

    cell_id = s2sphere.CellId.from_token(s2_token)
    cell = s2sphere.Cell(cell_id)
    coords = []
    for i in range(4):
        ll = s2sphere.LatLng.from_point(cell.get_vertex(i))
        coords.append((ll.lng().degrees, ll.lat().degrees))
    return Polygon(coords)


def download_one_cell(
    s2_token: str,
    *,
    region_wkt: str,
    tmp_dir: str,
    resume: bool,
) -> tuple[str, str | None]:
    """Download buildings for one S2 cell, filter to inside the region, save to tmp.

    Returns (s2_token, tmp_filepath_or_None). None means no buildings inside region.
    Designed to be called via multiprocessing.Pool — args via partial.
    """
    import gcsfs
    import pandas as pd
    from shapely import wkt as shp_wkt
    from shapely.prepared import prep

    out_path = Path(tmp_dir) / f"{s2_token}.csv.gz"
    if resume and out_path.exists():
        return s2_token, str(out_path)

    region_geom = shp_wkt.loads(region_wkt)
    cell_geom = s2_token_to_polygon(s2_token)
    prepared = prep(region_geom)

    if not prepared.intersects(cell_geom):
        return s2_token, None

    fs = gcsfs.GCSFileSystem(token="anon")
    gcs_path = f"{GCS_BUCKET[5:]}/{s2_token}_buildings.csv.gz"  # strip gs://

    if not fs.exists(gcs_path):
        return s2_token, None

    fully_inside = prepared.covers(cell_geom)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fully_inside:
        # Whole cell inside region — copy through.
        with fs.open(gcs_path, "rb") as src, open(out_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        return s2_token, str(out_path)

    # Partial overlap — read in chunks, point-in-polygon filter, write filtered rows.
    import geopandas as gpd
    from geopandas import points_from_xy

    chunks = pd.read_csv(
        fs.open(gcs_path, "rb"),
        chunksize=2_000_000,
        dtype=object,
        compression="gzip",
        header=None,
    )
    wrote_any = False
    for chunk in chunks:
        pts = gpd.GeoDataFrame(
            geometry=points_from_xy(chunk[1].astype(float), chunk[0].astype(float)),
            crs="EPSG:4326",
        )
        # Spatial join — keep points inside region.
        keep = pts[pts.geometry.within(region_geom)]
        if keep.empty:
            continue
        chunk_filtered = chunk.iloc[keep.index]
        chunk_filtered.to_csv(
            out_path,
            mode="ab",
            index=False,
            header=False,
            compression={"method": "gzip", "compresslevel": 1},
        )
        wrote_any = True

    if wrote_any:
        return s2_token, str(out_path)
    if out_path.exists():
        out_path.unlink()
    return s2_token, None


def concatenate_cells(cell_files: list[str], output_path: Path) -> None:
    """Concatenate per-cell gzipped CSVs into one output, with header prepended.

    Note: concatenating gzip files produces a valid gzip stream. We only need
    to prepend the header (which the source files lack) once.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing header + concatenating {len(cell_files)} cell files → {output_path}")
    with gzip.open(output_path, "wt") as f:
        f.write(OUTPUT_HEADER + "\n")
    # Append the gzip cell files. Concatenated gzip = valid gzip.
    with open(output_path, "ab") as out:
        for cf in cell_files:
            with open(cf, "rb") as src:
                shutil.copyfileobj(src, out)


def main() -> int:
    args = parse_args()
    if args.check_deps:
        check_deps()
        return 0
    check_deps()  # also runs at the top of every full run

    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    if not args.resume:
        # Clean tmp dir for a fresh run
        for f in glob.glob(str(args.tmp_dir / "*.csv.gz")):
            os.remove(f)

    region_geom = load_indonesia_polygon()
    s2_tokens = get_s2_tokens(region_geom)
    print(f"Found {len(s2_tokens)} S2 level-6 tokens covering Indonesia bbox")

    region_wkt = region_geom.wkt  # serialize once for worker passing
    download_fn = functools.partial(
        download_one_cell,
        region_wkt=region_wkt,
        tmp_dir=str(args.tmp_dir),
        resume=args.resume,
    )

    from tqdm import tqdm

    cell_files: list[str] = []
    with multiprocessing.Pool(args.workers) as pool:
        for _, tmp_path in tqdm(
            pool.imap_unordered(download_fn, s2_tokens),
            total=len(s2_tokens),
            desc="cells",
        ):
            if tmp_path:
                cell_files.append(tmp_path)

    if not cell_files:
        print("ERROR: no cells produced data — something is wrong", file=sys.stderr)
        return 2

    concatenate_cells(cell_files, args.output)
    size_mb = args.output.stat().st_size / 1_000_000
    print(f"Done. {args.output} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
