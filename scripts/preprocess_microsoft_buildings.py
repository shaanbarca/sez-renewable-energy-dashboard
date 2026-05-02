"""
preprocess_microsoft_buildings.py — Stream-filter MS GMLBF Indonesia tiles
to the per-site buffered region of interest, producing a parquet that
MATCHES the GoB v3 schema (spec §13.10 invariants 1–6).

# What this script does

1. Loads 81 site polygons (KEKs from kek_polygons.geojson; non-KEKs are
   buffered centroids — same logic as preprocess_open_buildings.py).
2. Buffers each site by 2 km in EPSG:23830 (UTM Zone 50S).
3. Streams `data/microsoft_buildings/raw/*.geojsonl.gz` tile by tile.
   Each line is a GeoJSON Feature with a Polygon. Per tile:
     a. Load the lines into a GeoDataFrame
     b. Compute polygon centroid (lat, lon) + area_in_meters
     c. Spatial-join with site buffers (point-in-polygon on centroid)
     d. Append surviving rows with `site_id` attached
4. Writes data/processed/sites_buildings_microsoft.parquet.

# Output schema (matches preprocess_open_buildings.py per spec §13.10)

| col            | type   | description                                         |
|----------------|--------|-----------------------------------------------------|
| building_id    | str    | "ms_gmlbf:<quadkey>:<line_idx>" (forward-compat #2) |
| source_name    | str    | Constant `"ms_gmlbf"` for this source               |
| source_vintage | str    | Per-tile UploadDate from the dataset-links index    |
| site_id        | str    | Site whose 2 km buffer contains the building        |
| latitude       | float  | Polygon centroid latitude (EPSG:4326)               |
| longitude      | float  | Polygon centroid longitude (EPSG:4326)              |
| area_in_meters | float  | Computed from polygon (EPSG:23830)                  |
| confidence     | float  | NaN (MS GMLBF doesn't publish confidence scores)    |
| s2_token_l4    | str    | "" (not applicable — MS isn't S2-cell partitioned)  |
| geometry       | shape  | Building polygon (Shapely, EPSG:4326)               |

A building → ONE site (nearest centroid wins). Same dedup as GoB to
prevent double-counting in Jakarta's industrial belt where multiple
sites are within 2 km.

# Usage

    uv run python scripts/preprocess_microsoft_buildings.py
    uv run python scripts/preprocess_microsoft_buildings.py --check-only
    uv run python scripts/preprocess_microsoft_buildings.py --max-tiles 5
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW_DIR = REPO_ROOT / "data" / "microsoft_buildings" / "raw"
INDEX_CACHE = REPO_ROOT / "data" / "microsoft_buildings" / "dataset-links.csv"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

DEFAULT_SITES = PROCESSED / "dim_sites.csv"
DEFAULT_POLYGONS = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
DEFAULT_OUTPUT = DATA_PROCESSED / "sites_buildings_microsoft.parquet"

DEFAULT_BUFFER_KM = 2.0
PROJECTED_CRS = "EPSG:23830"

# Spec §13.10 invariants 1+5: source_name constant; confidence is null.
SOURCE_NAME = "ms_gmlbf"
DEFAULT_VINTAGE = "ms_gmlbf_unknown"  # Fallback if index doesn't carry UploadDate


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    p.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    p.add_argument("--index", type=Path, default=INDEX_CACHE)
    p.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    p.add_argument("--polygons", type=Path, default=DEFAULT_POLYGONS)
    p.add_argument("--buffer-km", type=float, default=DEFAULT_BUFFER_KM)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument(
        "--max-tiles",
        type=int,
        default=None,
        help="Process at most N tiles (smoke-test).",
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Validate inputs + report stats without writing parquet.",
    )
    return p.parse_args()


def load_site_buffers(
    sites_csv: Path, polygons_geojson: Path, buffer_km: float
) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Same logic as preprocess_open_buildings.py.

    Returns (buffered_sites_gdf, site_centroids_df). Centroids feed the
    nearest-site dedup (one building → one site).
    """
    sites = pd.read_csv(sites_csv)
    print(f"Loaded {len(sites)} sites from {sites_csv.name}")

    kek_polygons: dict[str, object] = {}
    if polygons_geojson.exists():
        kek_gdf = gpd.read_file(polygons_geojson)
        # `slug` is the actual key in kek_polygons.geojson; the other fallbacks
        # are defensive for differently-keyed GeoJSONs.
        id_col = next(
            (c for c in ("site_id", "slug", "kek_id", "id", "name") if c in kek_gdf.columns),
            None,
        )
        if id_col:
            for _, r in kek_gdf.iterrows():
                key = str(r[id_col]).lower().replace(" ", "-")
                kek_polygons[key] = r.geometry
        print(f"Loaded {len(kek_polygons)} KEK polygons from {polygons_geojson.name}")

    rows = []
    for _, r in sites.iterrows():
        sid = r["site_id"]
        geom = kek_polygons.get(sid) or Point(r["longitude"], r["latitude"])
        rows.append({"site_id": sid, "geometry": geom})

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    gdf_proj = gdf.to_crs(PROJECTED_CRS)
    gdf_proj["geometry"] = gdf_proj.geometry.buffer(buffer_km * 1000)
    gdf = gdf_proj.to_crs("EPSG:4326")

    centroids = sites[["site_id", "latitude", "longitude"]].rename(
        columns={"latitude": "centroid_lat", "longitude": "centroid_lon"}
    )

    print(
        f"Buffered {len(gdf)} sites by {buffer_km} km "
        f"(union bbox: {unary_union(gdf.geometry).bounds})"
    )
    return gdf, centroids


def load_tile_vintages(index_csv: Path) -> dict[str, str]:
    """Map quadkey → upload date string (per-row vintage per spec §13.10 #6)."""
    if not index_csv.exists():
        print(
            f"WARNING: {index_csv} missing — every row will get vintage "
            f"{DEFAULT_VINTAGE!r}. Run download_microsoft_buildings.py first."
        )
        return {}
    df = pd.read_csv(index_csv)
    qk_col = next((c for c in df.columns if c.lower() in ("quadkey",)), None)
    date_col = next((c for c in df.columns if "uploaddate" in c.lower().replace("_", "")), None)
    if qk_col is None or date_col is None:
        print(f"WARNING: index missing QuadKey or UploadDate column. Got: {list(df.columns)}")
        return {}
    return dict(zip(df[qk_col].astype(str), df[date_col].astype(str), strict=False))


def process_tile(
    tile_path: Path,
    sites_gdf: gpd.GeoDataFrame,
    site_centroids: pd.DataFrame,
    vintage: str,
) -> gpd.GeoDataFrame:
    """Read one gzipped GeoJSONL tile, filter to site buffers, dedup."""
    quadkey = tile_path.stem.replace(".geojsonl", "")
    rows: list[dict] = []
    with gzip.open(tile_path, "rt") as f:
        for line_idx, raw_line in enumerate(f):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                feat = json.loads(stripped)
                geom = shape(feat["geometry"])
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            rows.append(
                {
                    "building_id": f"{SOURCE_NAME}:{quadkey}:{line_idx}",
                    "geometry": geom,
                }
            )

    if not rows:
        return gpd.GeoDataFrame(
            columns=["site_id", "geometry"], geometry="geometry", crs="EPSG:4326"
        )

    bldg_gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # Compute centroids for spatial join + lat/lon columns.
    centroids = bldg_gdf.geometry.centroid
    bldg_gdf["latitude"] = centroids.y.to_numpy()
    bldg_gdf["longitude"] = centroids.x.to_numpy()

    # Compute area in projected CRS (matches GoB's area_in_meters).
    bldg_gdf["area_in_meters"] = bldg_gdf.to_crs(PROJECTED_CRS).geometry.area.to_numpy()

    # Invariants 1 + 5: source_name + null confidence.
    bldg_gdf["source_name"] = SOURCE_NAME
    bldg_gdf["source_vintage"] = vintage
    bldg_gdf["confidence"] = np.nan
    bldg_gdf["s2_token_l4"] = ""

    # Spatial join — building centroid within any site buffer.
    centroid_gdf = gpd.GeoDataFrame(
        bldg_gdf[["building_id"]].copy(),
        geometry=gpd.points_from_xy(bldg_gdf["longitude"], bldg_gdf["latitude"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(centroid_gdf, sites_gdf, predicate="within", how="inner")
    if joined.empty:
        return gpd.GeoDataFrame(
            columns=["site_id", "geometry"], geometry="geometry", crs="EPSG:4326"
        )

    matches = joined.merge(bldg_gdf, on="building_id", suffixes=("_pt", ""))

    # One building → one site (nearest centroid). Same as GoB preprocessor.
    matches = matches.merge(site_centroids, on="site_id", how="left")
    lat1 = np.radians(matches["latitude"].to_numpy())
    lat2 = np.radians(matches["centroid_lat"].to_numpy())
    dlat = lat2 - lat1
    dlon = np.radians(matches["centroid_lon"].to_numpy() - matches["longitude"].to_numpy())
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    matches["dist_to_site_km"] = 2 * 6371.0 * np.arcsin(np.sqrt(a))
    matches = matches.sort_values("dist_to_site_km").drop_duplicates("building_id", keep="first")

    keep_cols = [
        "building_id",
        "site_id",
        "source_name",
        "source_vintage",
        "latitude",
        "longitude",
        "area_in_meters",
        "confidence",
        "s2_token_l4",
        "geometry",
    ]
    return gpd.GeoDataFrame(matches[keep_cols].reset_index(drop=True), crs="EPSG:4326")


def main() -> int:
    args = parse_args()

    if not args.raw_dir.exists():
        print(f"ERROR: {args.raw_dir} not found. Run download_microsoft_buildings.py first.")
        return 1

    tiles = sorted(args.raw_dir.glob("*.geojsonl.gz"))
    if args.max_tiles:
        tiles = tiles[: args.max_tiles]
    if not tiles:
        print(f"ERROR: no tiles in {args.raw_dir}. Did the download finish?")
        return 1
    print(f"Found {len(tiles):,} tiles to process.")

    sites_gdf, centroids = load_site_buffers(args.sites, args.polygons, args.buffer_km)
    vintages = load_tile_vintages(args.index)

    if args.check_only:
        print("--check-only: skipping tile processing.")
        return 0

    parts: list[gpd.GeoDataFrame] = []
    n_buildings_out = 0
    for tile_path in tqdm(tiles, unit="tile"):
        quadkey = tile_path.stem.replace(".geojsonl", "")
        vintage = vintages.get(quadkey, DEFAULT_VINTAGE)
        result = process_tile(tile_path, sites_gdf, centroids, vintage)
        n_buildings_out += len(result)
        if not result.empty:
            parts.append(result)

    if not parts:
        print("WARNING: 0 buildings matched any site buffer. Spec mismatch?")
        return 1

    out = pd.concat(parts, ignore_index=True)
    out_gdf = gpd.GeoDataFrame(out, geometry="geometry", crs="EPSG:4326")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out_gdf.to_parquet(args.output, index=False)

    print()
    print(f"Wrote {len(out_gdf):,} buildings to {args.output}")
    by_site = out_gdf.groupby("site_id").size().sort_values(ascending=False)
    print(f"Sites covered: {len(by_site):,} / 81")
    print("Top 5 sites by MS GMLBF building count:")
    print(by_site.head(5).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
