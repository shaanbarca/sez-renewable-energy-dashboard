"""
preprocess_open_buildings.py — Stream-filter the GoB v3 Indonesia raw extract
to the per-site buffered region of interest, producing the Layer 2 GeoParquet.

# What this script does

1. Loads 81 site polygons (KEKs from kek_polygons.geojson; non-KEKs are buffered
   centroids — proxy until per-site polygons exist for industrial rows).
2. Buffers each site by 2 km in EPSG:23830 (UTM Zone 50S) for accurate metric
   buffering, reproject back to EPSG:4326.
3. Streams the 6.7 GB raw GoB v3 CSV in chunks. For each chunk:
     a. Compute S2 level-4 cell for each row's centroid
     b. Apply the 90% precision confidence threshold per S2 cell
     c. Spatial-join with the site buffers (point-in-polygon)
     d. Append surviving rows to a running list, with `site_id` attached
4. Writes data/processed/sites_buildings_filtered.parquet (Layer 2 from
   `docs/rooftop_solar_potential_feature_spec.md` §13).

# Output schema

| col            | type   | description                                            |
|----------------|--------|--------------------------------------------------------|
| building_id    | str    | Source-prefixed: "gob_v3:1234567" (forward-compat §13.10) |
| source_name    | str    | Constant `"gob_v3"` in v4.1; varies in v4.2 (forward-compat §13.10) |
| source_vintage | str    | Constant `"2023-05"` for GoB v3 imagery; varies per source in v4.2 |
| site_id        | str    | The site whose 2km-buffer contains the building point  |
| latitude       | float  | Building centroid latitude                             |
| longitude      | float  | Building centroid longitude                            |
| area_in_meters | float  | Original GoB v3 detected area                          |
| confidence     | float  | Original GoB v3 confidence score                       |
| s2_token_l4    | str    | S2 level-4 cell token (for threshold audit)            |
| geometry       | shape  | Building polygon (Shapely, EPSG:4326)                  |

A building can match multiple sites if their buffers overlap — one row per
(site_id, building_id) pair. The §14 classifier runs LATER (in the runtime
pipeline), against this output. We don't apply geometric type classification
here — that decision lives in the pipeline so threshold tuning per
`assumptions.py` is hot-reloadable.

# Usage

    uv run python scripts/preprocess_open_buildings.py
    uv run python scripts/preprocess_open_buildings.py --chunk-size 2000000
    uv run python scripts/preprocess_open_buildings.py --check-only

# Performance

Indonesia raw extract: 63.6M rows / 6.7 GB gzipped. Stream filter takes
5-15 minutes depending on disk speed. Typical reduction:
  raw 63,589,524 rows → ~50,000-200,000 buildings inside site buffers
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import s2sphere
from shapely import wkt as shp_wkt
from shapely.geometry import Point
from shapely.ops import unary_union
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DATA_DIR = REPO_ROOT / "data" / "open_buildings"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

DEFAULT_RAW = DATA_DIR / "idn_open_buildings.csv.gz"
DEFAULT_THRESHOLDS = DATA_DIR / "score_thresholds_s2_level_4.csv"
DEFAULT_SITES = PROCESSED / "dim_sites.csv"
DEFAULT_POLYGONS = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
DEFAULT_OUTPUT = DATA_PROCESSED / "sites_buildings_filtered.parquet"

DEFAULT_BUFFER_KM = 2.0
DEFAULT_CHUNK_SIZE = 1_000_000
# Indonesian National DGN95 / UTM Zone 50S — accurate metric distances for
# the bulk of Indonesian industrial sites (Sumatra to Maluku). Papua-extreme
# sites have ~few-meter error vs a perfect projection, well within our 2 km
# buffer slop.
PROJECTED_CRS = "EPSG:23830"

# Use the 90%-precision threshold per cell. Trades recall for precision —
# better to undercount than to include hallucinated buildings.
PRECISION_COL = "confidence_threshold_90%_precision"

# Fallback when an S2 cell isn't in the thresholds table (rare — we only
# use cells inside Indonesia, which are all in the table).
DEFAULT_THRESHOLD = 0.65

# Forward-compat invariants (spec §13.10). v4.1 has only one source; these
# constants are provider-specific and become per-row when v4.2 adds MS GMLBF.
SOURCE_NAME = "gob_v3"
SOURCE_VINTAGE = "2023-05"  # Imagery date — Google Open Buildings v3 release


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream-filter Google Open Buildings v3 raw extract to "
        "the per-site 2 km buffered region of interest.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--raw-data", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    parser.add_argument("--polygons", type=Path, default=DEFAULT_POLYGONS)
    parser.add_argument(
        "--confidence-thresholds",
        type=Path,
        default=DEFAULT_THRESHOLDS,
        help="If file missing, falls back to a flat threshold (0.65).",
    )
    parser.add_argument("--buffer-km", type=float, default=DEFAULT_BUFFER_KM)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate inputs + report stats without writing parquet.",
    )
    return parser.parse_args()


def load_site_buffers(
    sites_csv: Path,
    polygons_geojson: Path,
    buffer_km: float,
) -> gpd.GeoDataFrame:
    """Load site polygons + buffer them by `buffer_km` in projected CRS.

    KEKs use polygons from kek_polygons.geojson. Non-KEK industrial sites use
    a buffered centroid (Point → buffer_km circle) as a proxy. Output is a
    GeoDataFrame in EPSG:4326 with columns: site_id, geometry.
    """
    sites = pd.read_csv(sites_csv)
    print(f"Loaded {len(sites)} sites from {sites_csv.name}")

    # KEK polygons keyed by site_id
    kek_polygons: dict[str, "Polygon"] = {}  # noqa: F821
    if polygons_geojson.exists():
        kek_gdf = gpd.read_file(polygons_geojson)
        id_col = next(
            (c for c in ("site_id", "kek_id", "id", "name") if c in kek_gdf.columns), None
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

    # Buffer in projected CRS for accurate metric distance, then back to 4326
    gdf_proj = gdf.to_crs(PROJECTED_CRS)
    gdf_proj["geometry"] = gdf_proj.geometry.buffer(buffer_km * 1000)
    gdf = gdf_proj.to_crs("EPSG:4326")

    print(
        f"Buffered {len(gdf)} sites by {buffer_km} km "
        f"(union bbox: {unary_union(gdf.geometry).bounds})"
    )
    return gdf


def load_thresholds(thresholds_csv: Path) -> dict[str, float]:
    """Load the 90%-precision threshold per S2 level-4 cell."""
    if not thresholds_csv.exists():
        print(
            f"WARNING: thresholds CSV not found at {thresholds_csv}; "
            f"using flat threshold {DEFAULT_THRESHOLD}",
        )
        return {}
    df = pd.read_csv(thresholds_csv)
    if PRECISION_COL not in df.columns:
        raise ValueError(f"Expected column {PRECISION_COL!r} in {thresholds_csv}")
    return dict(zip(df["s2_token"].astype(str), df[PRECISION_COL].astype(float), strict=False))


def s2_token_l4_for_point(lat: float, lon: float) -> str:
    """Return the S2 level-4 cell token containing (lat, lon)."""
    ll = s2sphere.LatLng.from_degrees(lat, lon)
    cell_id = s2sphere.CellId.from_lat_lng(ll).parent(4)
    return cell_id.to_token()


def process_chunk(
    chunk: pd.DataFrame,
    sites_gdf: gpd.GeoDataFrame,
    site_centroids: pd.DataFrame,  # site_id, centroid_lat, centroid_lon (deg)
    thresholds: dict[str, float],
    chunk_offset: int,
) -> gpd.GeoDataFrame:
    """Filter one chunk: confidence threshold → spatial join to site buffers."""
    # Compute S2 level-4 token per row (vectorize via Python loop — s2sphere
    # has no vectorized API; this is the bottleneck per chunk)
    chunk["s2_token_l4"] = [
        s2_token_l4_for_point(lat, lon)
        for lat, lon in zip(chunk["latitude"], chunk["longitude"], strict=False)
    ]

    # Apply per-cell confidence threshold (fallback to default for missing keys)
    chunk["threshold"] = chunk["s2_token_l4"].map(thresholds).fillna(DEFAULT_THRESHOLD)
    chunk = chunk[chunk["confidence"] >= chunk["threshold"]].drop(columns=["threshold"])

    if chunk.empty:
        return gpd.GeoDataFrame(
            columns=["site_id", "geometry"], geometry="geometry", crs="EPSG:4326"
        )

    # Convert to GeoDataFrame using the WKT polygon column — note this is the
    # building polygon, not the centroid point. We keep the polygon for the
    # downstream §14 classifier (needs full geometry for circularity / aspect).
    chunk["geometry"] = chunk["geometry"].apply(shp_wkt.loads)
    bldg_gdf = gpd.GeoDataFrame(chunk, geometry="geometry", crs="EPSG:4326")
    # Forward-compat invariant #2: building_id is a source-prefixed STRING
    # so MS GMLBF / manual / OSM rows in v4.2+ don't collide with GoB v3 IDs.
    raw_idx = chunk_offset + bldg_gdf.index.to_numpy()
    bldg_gdf["building_id"] = [f"{SOURCE_NAME}:{i}" for i in raw_idx]
    # Forward-compat invariant #1: source_name + source_vintage on every row.
    bldg_gdf["source_name"] = SOURCE_NAME
    bldg_gdf["source_vintage"] = SOURCE_VINTAGE

    # Spatial join: keep buildings whose CENTROID falls inside any site buffer.
    # Centroid-based is faster than polygon-based and the 2 km buffer is
    # plenty of slop for buildings that straddle the boundary.
    centroids = gpd.GeoDataFrame(
        bldg_gdf[["building_id"]].copy(),
        geometry=gpd.points_from_xy(bldg_gdf["longitude"], bldg_gdf["latitude"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(centroids, sites_gdf, predicate="within", how="inner")

    if joined.empty:
        return gpd.GeoDataFrame(
            columns=["site_id", "geometry"], geometry="geometry", crs="EPSG:4326"
        )

    # Attach site_id back to the polygon GDF; emit one row per (site, building)
    matches = joined.merge(
        bldg_gdf,
        on="building_id",
        suffixes=("_pt", ""),
    )

    # ─── Dedup: each building → ONE site (RV5 fix, 2026-04-27) ────────────────
    # Without this, a warehouse near 3 nearby sites (Master Steel, Gunung Raja
    # Paksi, Jakarta Prima Steel — all within 2 km of each other in Jakarta's
    # industrial belt) gets summed into all 3 sites' rooftop MWp. Inflated the
    # 81-site total by ~2× pre-dedup. Assignment rule: nearest site centroid by
    # haversine distance — fast, correct enough at <50 km buffer scale.
    matches = matches.merge(site_centroids, on="site_id", how="left")
    # Vectorized haversine in km — same formula as src/pipeline/geo_utils
    lat1 = np.radians(matches["latitude"].to_numpy())
    lat2 = np.radians(matches["centroid_lat"].to_numpy())
    dlat = lat2 - lat1
    dlon = np.radians(matches["centroid_lon"].to_numpy() - matches["longitude"].to_numpy())
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    matches["dist_to_site_km"] = 2 * 6371.0 * np.arcsin(np.sqrt(a))
    # For each building, keep only the row whose site centroid is nearest
    matches = matches.sort_values("dist_to_site_km").drop_duplicates("building_id", keep="first")

    keep_cols = [
        "building_id",
        "site_id",
        "latitude",
        "longitude",
        "area_in_meters",
        "confidence",
        "source_name",
        "source_vintage",
        "s2_token_l4",
        "geometry",
    ]
    return gpd.GeoDataFrame(matches[keep_cols], geometry="geometry", crs="EPSG:4326")


def stream_filter(
    raw_csv: Path,
    sites_gdf: gpd.GeoDataFrame,
    site_centroids: pd.DataFrame,  # site_id, centroid_lat, centroid_lon
    thresholds: dict[str, float],
    chunk_size: int,
) -> gpd.GeoDataFrame:
    """Stream-read the raw CSV in chunks, accumulating filtered buildings."""
    print(f"\nStreaming {raw_csv} (chunk_size={chunk_size:,})")
    all_matches: list[gpd.GeoDataFrame] = []
    total_raw = 0
    total_post_threshold = 0

    reader = pd.read_csv(
        raw_csv,
        compression="gzip",
        chunksize=chunk_size,
        dtype={
            "latitude": float,
            "longitude": float,
            "area_in_meters": float,
            "confidence": float,
            "geometry": str,
            "full_plus_code": str,
        },
    )

    chunk_offset = 0
    for chunk in tqdm(reader, desc="chunks", unit="chunk"):
        chunk_size_actual = len(chunk)
        total_raw += chunk_size_actual
        matches = process_chunk(chunk, sites_gdf, site_centroids, thresholds, chunk_offset)
        # Track post-threshold count (before spatial filter)
        # Approximate: matches gives us post-everything; intermediate count
        # is dropped during process_chunk. For now log final-only.
        total_post_threshold += len(matches)
        if not matches.empty:
            all_matches.append(matches)
        chunk_offset += chunk_size_actual

    print(f"\n  raw rows read:        {total_raw:>15,}")
    print(f"  rows after filtering: {total_post_threshold:>15,}")

    if not all_matches:
        return gpd.GeoDataFrame(
            columns=["building_id", "site_id", "geometry"],
            geometry="geometry",
            crs="EPSG:4326",
        )
    return gpd.GeoDataFrame(pd.concat(all_matches, ignore_index=True), crs="EPSG:4326")


def main() -> int:
    args = parse_args()

    for label, path in [
        ("raw data", args.raw_data),
        ("sites", args.sites),
        ("polygons", args.polygons),
    ]:
        if not path.exists():
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            return 1

    print("preprocess_open_buildings.py")
    print(f"  raw data:    {args.raw_data}")
    print(f"  sites:       {args.sites}")
    print(f"  polygons:    {args.polygons}")
    print(f"  thresholds:  {args.confidence_thresholds}")
    print(f"  buffer:      {args.buffer_km} km")
    print(f"  chunk size:  {args.chunk_size:,}")
    print(f"  output:      {args.output}")

    if args.check_only:
        print("\n--check-only: inputs validated, exiting.")
        return 0

    t0 = time.time()
    sites_gdf = load_site_buffers(args.sites, args.polygons, args.buffer_km)
    # Site centroids in EPSG:4326 — passed to dedup step (RV5). For KEK polygons
    # this is the polygon centroid; for non-KEK sites it's the dim_sites lat/lon
    # we used to build the buffer originally. Either way, distance-from-centroid
    # is the canonical "which site does this building belong to" rule.
    site_centroids = pd.DataFrame(
        {
            "site_id": sites_gdf["site_id"].values,
            "centroid_lat": sites_gdf.geometry.centroid.y.values,
            "centroid_lon": sites_gdf.geometry.centroid.x.values,
        }
    )
    thresholds = load_thresholds(args.confidence_thresholds)
    print(
        f"Loaded {len(thresholds):,} per-cell confidence thresholds "
        f"(or flat fallback {DEFAULT_THRESHOLD})"
    )

    filtered = stream_filter(args.raw_data, sites_gdf, site_centroids, thresholds, args.chunk_size)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {args.output}")
    filtered.to_parquet(args.output, index=False)
    out_size_mb = args.output.stat().st_size / 1_000_000
    elapsed = time.time() - t0

    # Stats
    site_counts = filtered["site_id"].value_counts() if not filtered.empty else pd.Series()
    print(f"\n  output size:       {out_size_mb:.1f} MB")
    print(f"  buildings matched: {len(filtered):,}")
    print(f"  unique sites:      {site_counts.shape[0]:,} / {len(sites_gdf)}")
    if site_counts.shape[0] > 0:
        print(f"  most:  {site_counts.index[0]} → {int(site_counts.iloc[0]):,} buildings")
        print(f"  least: {site_counts.index[-1]} → {int(site_counts.iloc[-1]):,} buildings")
    print(f"  elapsed:           {elapsed:.0f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
