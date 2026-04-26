"""
check_open_buildings_coverage.py — Diagnose which S2 level-6 cells we
ACTUALLY need vs what's already downloaded.

The download script pulls all S2 cells covering Indonesia's bbox (~497 cells).
Most are ocean. Most of the ~150-200 land cells are nowhere near our 81
industrial sites. We don't need them.

This script computes which S2 cells intersect a 2 km buffer around any of
the 81 site polygons (the actual "region of interest" for v4.1 rooftop
work) and tells you:

  - which cells you NEED
  - which you ALREADY HAVE
  - which are STILL MISSING

If MISSING is empty → you're done; concatenate and move on.
If MISSING is small → run the downloader with a manual list of just those.
If MISSING is large → keep the country-wide download going.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import s2sphere
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

REPO_ROOT = Path(__file__).resolve().parents[1]
DIM_SITES = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
KEK_POLYGONS = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
TMP_CELLS_DIR = REPO_ROOT / "data" / "open_buildings" / "_tmp_cells"

BUFFER_KM = 2.0
# Convert km to degrees for buffering in EPSG:4326 (rough but fine at
# Indonesian latitudes — we'd reproject for production code, but this
# diagnostic just needs to be approximately right).
DEG_PER_KM_LAT = 1.0 / 111.0
DEG_PER_KM_LON_AT_EQUATOR = 1.0 / 111.0  # Indonesia is near equator


def s2_token_to_polygon(token: str) -> Polygon:
    cell_id = s2sphere.CellId.from_token(token)
    cell = s2sphere.Cell(cell_id)
    coords = []
    for i in range(4):
        ll = s2sphere.LatLng.from_point(cell.get_vertex(i))
        coords.append((ll.lng().degrees, ll.lat().degrees))
    return Polygon(coords)


def s2_token_for_point(lat: float, lon: float, level: int = 6) -> str:
    ll = s2sphere.LatLng.from_degrees(lat, lon)
    cell_id = s2sphere.CellId.from_lat_lng(ll).parent(level)
    return cell_id.to_token()


def get_s2_tokens_for_region(geom: Polygon, level: int = 6) -> set[str]:
    """All S2 level-N cells covering the region's bounding box that
    intersect the region itself."""
    min_lng, min_lat, max_lng, max_lat = geom.bounds
    lo = s2sphere.LatLng.from_degrees(min_lat, min_lng)
    hi = s2sphere.LatLng.from_degrees(max_lat, max_lng)
    rect = s2sphere.LatLngRect.from_point_pair(lo, hi)

    coverer = s2sphere.RegionCoverer()
    coverer.min_level = level
    coverer.max_level = level
    coverer.max_cells = 1_000_000

    cells = coverer.get_covering(rect)
    prepared = prep(geom)
    return {c.to_token() for c in cells if prepared.intersects(s2_token_to_polygon(c.to_token()))}


def main() -> None:
    sites = pd.read_csv(DIM_SITES)
    print(f"Loaded {len(sites)} sites from dim_sites.csv")

    # KEK polygons (~25); for non-KEK sites, buffer the centroid as a circle
    # ~5 km radius (proxy for site footprint until we have polygons for them)
    kek_polygons: dict[str, Polygon] = {}
    if KEK_POLYGONS.exists():
        kek_gdf = gpd.read_file(KEK_POLYGONS)
        # Best-effort: id column varies. Try a few candidates.
        id_col = None
        for c in ("site_id", "kek_id", "id", "name"):
            if c in kek_gdf.columns:
                id_col = c
                break
        if id_col:
            for _, row in kek_gdf.iterrows():
                kek_polygons[str(row[id_col]).lower().replace(" ", "-")] = row.geometry
        print(f"Loaded {len(kek_polygons)} KEK polygons")

    # Build buffered geometry for each site
    site_buffers: list[Polygon] = []
    for _, row in sites.iterrows():
        site_id = row["site_id"]
        if site_id in kek_polygons:
            geom = kek_polygons[site_id]
        else:
            # Non-KEK site — buffer the centroid as a circle of ~5 km radius
            # (proxy until polygons exist)
            geom = Point(row["longitude"], row["latitude"])
        # Buffer by 2 km
        # In EPSG:4326 degrees this is approximate; adequate for cell-coverage
        buffered = geom.buffer(BUFFER_KM * DEG_PER_KM_LAT)
        site_buffers.append(buffered)

    roi = unary_union(site_buffers)
    print(f"ROI bounds: {roi.bounds}")

    needed_tokens = get_s2_tokens_for_region(roi, level=6)
    print(f"\nS2 level-6 cells we NEED: {len(needed_tokens)}")

    have_tokens = {p.stem.replace(".csv", "") for p in TMP_CELLS_DIR.glob("*.csv.gz")}
    have_tokens = {t.split(".")[0] for t in have_tokens}  # strip .csv from .csv.gz
    print(f"S2 cells we HAVE downloaded: {len(have_tokens)}")

    overlap = needed_tokens & have_tokens
    missing = needed_tokens - have_tokens
    extra = have_tokens - needed_tokens

    print("\n" + "=" * 60)
    print(f"ALREADY HAVE (good): {len(overlap)} cells")
    print(f"STILL MISSING:       {len(missing)} cells")
    print(f"WASTED DOWNLOAD:     {len(extra)} cells (not near sites)")
    print("=" * 60)

    if missing:
        print(f"\nMissing tokens to download: {sorted(missing)}")
        # Compute approx download size from neighboring cells
        if have_tokens:
            avg_size_mb = (
                sum(p.stat().st_size for p in TMP_CELLS_DIR.glob("*.csv.gz")) / len(have_tokens)
            ) / 1_000_000
            print(f"Estimated remaining size: ~{avg_size_mb * len(missing):.0f} MB")
    else:
        print("\n✅ ALL NEEDED CELLS ARE ALREADY DOWNLOADED.")
        print("   You can stop the download script and proceed to concatenation.")


if __name__ == "__main__":
    main()
