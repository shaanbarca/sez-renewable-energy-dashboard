"""
merge_open_buildings_cells.py — Concatenate the per-cell gzipped CSVs that
are within the site-buffered region of interest into a single output file.

Skips cells that are downloaded but not near any of the 81 sites (the
"wasted" cells flagged by check_open_buildings_coverage.py). Concatenated
gzip is itself a valid gzip stream, so we just stream-copy with a header
prepended.

Usage:
    uv run python scripts/merge_open_buildings_cells.py
    uv run python scripts/merge_open_buildings_cells.py --cleanup-wasted

The --cleanup-wasted flag deletes the unused per-cell files after the
merge to reclaim disk (~6 GB for our case). Output stays untouched.
"""

from __future__ import annotations

import argparse
import gzip
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_CELLS_DIR = REPO_ROOT / "data" / "open_buildings" / "_tmp_cells"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "open_buildings" / "idn_open_buildings.csv.gz"
HEADER = "latitude,longitude,area_in_meters,confidence,geometry,full_plus_code"


def get_needed_tokens() -> set[str]:
    """Re-run the coverage check, parse the needed token list out of stdout."""
    result = subprocess.run(
        ["uv", "run", "python", "scripts/check_open_buildings_coverage.py"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    # We re-import the helper from check_open_buildings_coverage rather than
    # re-implementing the ROI logic — keeps the two scripts aligned.
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import geopandas as gpd
    import pandas as pd
    from check_open_buildings_coverage import (
        BUFFER_KM,
        DEG_PER_KM_LAT,
        DIM_SITES,
        KEK_POLYGONS,
        get_s2_tokens_for_region,
    )
    from shapely.geometry import Point
    from shapely.ops import unary_union

    sites = pd.read_csv(DIM_SITES)
    kek_polygons = {}
    if KEK_POLYGONS.exists():
        kek_gdf = gpd.read_file(KEK_POLYGONS)
        id_col = next(
            (c for c in ("site_id", "kek_id", "id", "name") if c in kek_gdf.columns), None
        )
        if id_col:
            for _, row in kek_gdf.iterrows():
                kek_polygons[str(row[id_col]).lower().replace(" ", "-")] = row.geometry

    site_buffers = []
    for _, row in sites.iterrows():
        site_id = row["site_id"]
        if site_id in kek_polygons:
            geom = kek_polygons[site_id]
        else:
            geom = Point(row["longitude"], row["latitude"])
        site_buffers.append(geom.buffer(BUFFER_KM * DEG_PER_KM_LAT))

    roi = unary_union(site_buffers)
    return get_s2_tokens_for_region(roi, level=6)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--cleanup-wasted",
        action="store_true",
        help="Delete cells not in the needed set after merge.",
    )
    args = parser.parse_args()

    needed = get_needed_tokens()
    available = {p.stem.replace(".csv", "") for p in TMP_CELLS_DIR.glob("*.csv.gz")}
    have = needed & available
    missing = needed - available
    wasted = available - needed

    print(f"NEEDED:    {len(needed)}")
    print(f"AVAILABLE: {len(available)}")
    print(f"USING:     {len(have)} (in --output)")
    print(f"MISSING:   {len(missing)} (run fetch_missing_cells.py --auto first)")
    print(f"WASTED:    {len(wasted)} (cells not near sites)")

    if missing:
        print(
            f"\nERROR: {len(missing)} required cells missing: {sorted(missing)}",
            file=sys.stderr,
        )
        print("Run: uv run python scripts/fetch_missing_cells.py --auto", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {args.output}")

    # Header first
    with gzip.open(args.output, "wt") as f:
        f.write(HEADER + "\n")

    # Then concat the needed gzip files (concatenated gzip = valid gzip)
    total_size = 0
    with open(args.output, "ab") as out:
        for token in sorted(have):
            cell_path = TMP_CELLS_DIR / f"{token}.csv.gz"
            with open(cell_path, "rb") as src:
                shutil.copyfileobj(src, out)
            total_size += cell_path.stat().st_size

    out_size_mb = args.output.stat().st_size / 1_000_000
    print(f"  output size: {out_size_mb:.1f} MB ({len(have)} cells merged)")

    if args.cleanup_wasted and wasted:
        wasted_size = (
            sum((TMP_CELLS_DIR / f"{t}.csv.gz").stat().st_size for t in wasted) / 1_000_000_000
        )
        print(f"\nDeleting {len(wasted)} wasted cells ({wasted_size:.2f} GB)")
        for token in wasted:
            (TMP_CELLS_DIR / f"{token}.csv.gz").unlink()
        print("  done.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
