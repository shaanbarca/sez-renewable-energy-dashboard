"""Generate panel-tile geometries for the map's "show your work" feature.

# What this produces

`data/processed/sites_rooftop_tiles.parquet` — one row per visible tile
rectangle. The frontend renders these at zoom ≥14 so users can count panels
and validate the headline rooftop MWp number from the per-site aggregator.

# Pipeline position

```
sites_buildings_filtered.parquet (Layer 2)
    │
    ▼   classify_building() per row → keep only standard_roof + soft-derate
    ▼
build_rooftop_tiles.py
    │
    ▼   for each suitable building:
    ▼     reproject to UTM 50S
    ▼     inset by ROOFTOP_EDGE_SETBACK_M (1m)
    ▼     tile a 6m × 4m grid filling the inset
    ▼     keep tiles whose intersection with inset is ≥95% of tile area
    ▼     attach DBSCAN cluster_id (per spec §3.6 F11 click aggregation)
    │
    ▼
sites_rooftop_tiles.parquet (Layer 2.5, ~30-50 MB est.)
```

# Output schema (spec §3.6 F8)

| col              | type   | description                                      |
|------------------|--------|--------------------------------------------------|
| site_id          | str    | Site this tile belongs to                        |
| building_id      | str    | Source-prefixed building (e.g. "gob_v3:1234567") |
| tile_idx         | int    | Per-building tile index (0..N-1)                 |
| cluster_id       | int    | DBSCAN cluster of the parent building (≥-1)      |
| panels_in_tile   | int    | Constant = ROOFTOP_PANELS_PER_TILE (default 6)   |
| tile_kw_dc       | float  | Per-tile DC nameplate (panels × W per panel /1k) |
| tile_kw_ac       | float  | DC × thermal_derate                              |
| geometry         | shape  | Tile rectangle in EPSG:4326                      |

# Performance reality

50-70k standard_roof buildings × ~10-20 tiles avg = 500k-1.4M tile rows.
Tile generation per-building is a tight grid loop in shapely. Expect
~1-3 minutes for the full 81-site run on standard hardware.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box
from sklearn.cluster import DBSCAN

from src.assumptions import (
    ROOFTOP_CLUSTER_RADIUS_M,
    ROOFTOP_EDGE_SETBACK_M,
    ROOFTOP_PANEL_POWER_W_DC,
    ROOFTOP_PANELS_PER_TILE,
    THERMAL_DERATE_TROPICAL,
)
from src.model.buildings import classify_building
from src.pipeline.build_fct_site_solar_potential import (
    PROJECTED_CRS,
    load_buildings_for_pipeline,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DEFAULT_OUTPUT = DATA_PROCESSED / "sites_rooftop_tiles.parquet"

# Tile dimensions (visual rectangles drawn on the map). 6 panels per tile,
# arranged 3 panels wide × 2 panels deep, plus walkway slack at the
# layout-density factor → ~6m × 4m visual rectangle.
#
#   ┌─────┬─────┬─────┐  ↑
#   │  ▥  │  ▥  │  ▥  │  4m   (2 panels deep × 1m + walkway)
#   ├─────┼─────┼─────┤
#   │  ▥  │  ▥  │  ▥  │  ↓
#   └─────┴─────┴─────┘
#       ←   6m   →     (3 panels long × 2m)
#
# Scaling with the panel area: tile_w × tile_h ≈ panel_area × panels_per_tile / layout_density
TILE_WIDTH_M = 6.0
TILE_HEIGHT_M = 4.0


# ─── Tile generation ──────────────────────────────────────────────────────


def tile_rooftop(
    polygon_utm,
    tile_width_m: float = TILE_WIDTH_M,
    tile_height_m: float = TILE_HEIGHT_M,
    setback_m: float = ROOFTOP_EDGE_SETBACK_M,
    min_overlap: float = 0.95,
) -> list:
    """Generate panel tiles filling a rooftop polygon (in projected CRS).

    Returns a list of tile polygons (also in projected CRS). Caller is
    responsible for reprojecting back to EPSG:4326 if needed.

    Algorithm:
      1. Inset polygon by setback_m to reserve fire-access edge
      2. Get bounding box of the inset
      3. Generate a regular grid of tile_width_m × tile_height_m rectangles
      4. Keep only tiles whose intersection with the inset is ≥ min_overlap
         of their own area (≥ 95% inside)
    """
    if polygon_utm.is_empty or polygon_utm.area < tile_width_m * tile_height_m:
        return []

    inset = polygon_utm.buffer(-setback_m)
    if inset.is_empty or inset.area < tile_width_m * tile_height_m:
        return []

    minx, miny, maxx, maxy = inset.bounds
    tiles = []
    x = minx
    while x + tile_width_m <= maxx:
        y = miny
        while y + tile_height_m <= maxy:
            tile = box(x, y, x + tile_width_m, y + tile_height_m)
            if inset.intersection(tile).area / tile.area >= min_overlap:
                tiles.append(tile)
            y += tile_height_m
        x += tile_width_m
    return tiles


# ─── Cluster ID (spec §3.6 F11) ────────────────────────────────────────────


def assign_clusters(
    buildings_proj: gpd.GeoDataFrame,
    eps_m: float = ROOFTOP_CLUSTER_RADIUS_M,
) -> np.ndarray:
    """DBSCAN over building centroids → cluster_id per building.

    eps_m: neighbours within this distance share a cluster. 50m default
    groups buildings sharing a continuous roofscape (industrial estate's
    main hall + adjoining warehouses) without merging across roads.
    min_samples=1 means singletons get their own cluster (no -1 noise).
    """
    if buildings_proj.empty:
        return np.array([], dtype=int)
    centroids = np.column_stack(
        [
            buildings_proj.geometry.centroid.x.to_numpy(),
            buildings_proj.geometry.centroid.y.to_numpy(),
        ]
    )
    return DBSCAN(eps=eps_m, min_samples=1).fit_predict(centroids)


# ─── Per-tile capacity (spec §5.3) ─────────────────────────────────────────

PER_TILE_KW_DC = (ROOFTOP_PANELS_PER_TILE * ROOFTOP_PANEL_POWER_W_DC) / 1000.0
PER_TILE_KW_AC = PER_TILE_KW_DC * THERMAL_DERATE_TROPICAL


# ─── Main build ────────────────────────────────────────────────────────────


def build_rooftop_tiles(
    buildings_parquet: Path | None = None,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """Generate tiles for every standard_roof building in Layer 2 parquet."""
    buildings = (
        load_buildings_for_pipeline(buildings_parquet)
        if buildings_parquet
        else load_buildings_for_pipeline()
    )
    print(f"Loaded {len(buildings):,} buildings from Layer 2 parquet")

    buildings_proj = buildings.to_crs(PROJECTED_CRS)

    # Classify upfront — only standard_roof + soft-derate buildings get tiles.
    # Hard-rejects (tank_silo, conveyor, complex, too_small) get no tiles.
    print("Classifying buildings...")
    keep_mask = []
    for _, row in buildings_proj.iterrows():
        cls = classify_building(row.geometry, row.geometry.area)
        # Tile only standard_roof + soft-derated categories that get >0 multiplier.
        # `possibly_round` and `complex` skipped (too uncertain to draw panels for).
        keep_mask.append(cls.category in {"standard_roof", "elongated"})
    keep_mask = np.array(keep_mask, dtype=bool)
    suitable = buildings_proj.loc[keep_mask].copy()
    print(f"  {keep_mask.sum():,} suitable buildings (standard_roof + elongated)")

    # Cluster IDs per site (so cluster numbering doesn't span unrelated areas)
    print("Assigning DBSCAN clusters per site...")
    suitable["cluster_id"] = -1
    cluster_offset = 0
    for site_id, group in suitable.groupby("site_id"):
        labels = assign_clusters(group)
        # Globally-unique cluster IDs by offsetting per site
        suitable.loc[group.index, "cluster_id"] = labels + cluster_offset
        cluster_offset += int(labels.max()) + 1 if len(labels) else 0
    print(f"  {cluster_offset:,} unique clusters across all sites")

    # Tile each suitable building
    print("Generating tiles...")
    rows = []
    for i, (_, row) in enumerate(suitable.iterrows(), 1):
        tiles = tile_rooftop(row.geometry)
        for t_idx, tile in enumerate(tiles):
            rows.append(
                {
                    "site_id": row["site_id"],
                    "building_id": row["building_id"],
                    "tile_idx": t_idx,
                    "cluster_id": int(row["cluster_id"]),
                    "panels_in_tile": ROOFTOP_PANELS_PER_TILE,
                    "tile_kw_dc": PER_TILE_KW_DC,
                    "tile_kw_ac": PER_TILE_KW_AC,
                    "geometry": tile,
                }
            )
        if i % 10_000 == 0:
            print(f"  {i:,}/{len(suitable):,} buildings tiled, {len(rows):,} tiles so far")

    if not rows:
        print("WARNING: zero tiles generated — output will be empty.")

    tiles_gdf = gpd.GeoDataFrame(rows, crs=PROJECTED_CRS)
    # Reproject back to EPSG:4326 for storage / map rendering
    tiles_gdf = tiles_gdf.to_crs("EPSG:4326")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {output_path}")
    tiles_gdf.to_parquet(output_path, index=False)

    out_size_mb = output_path.stat().st_size / 1_000_000
    n_tiles = len(tiles_gdf)
    n_buildings_tiled = tiles_gdf["building_id"].nunique() if not tiles_gdf.empty else 0
    n_sites = tiles_gdf["site_id"].nunique() if not tiles_gdf.empty else 0
    n_clusters = tiles_gdf["cluster_id"].nunique() if not tiles_gdf.empty else 0
    total_kw_ac = n_tiles * PER_TILE_KW_AC
    print(f"\n  output size:        {out_size_mb:.1f} MB")
    print(f"  total tiles:        {n_tiles:,}")
    print(f"  buildings tiled:    {n_buildings_tiled:,}")
    print(f"  sites with tiles:   {n_sites} / 81")
    print(f"  unique clusters:    {n_clusters:,}")
    print(f"  total kW AC:        {total_kw_ac:,.0f}")
    return tiles_gdf


def main() -> None:
    build_rooftop_tiles()


if __name__ == "__main__":
    main()
