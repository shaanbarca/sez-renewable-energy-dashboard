"""Tests for `detect_residential_clusters` (RV11) — per-building residential
filter that drops dense clusters of similar-sized small houses before they
inflate per-site rooftop totals.

The filter fires only when ALL THREE conditions hold:
  1. footprint < RESIDENTIAL_AREA_MAX_M2 (default 300 m²)
  2. ≥ RESIDENTIAL_MIN_NEIGHBORS within RESIDENTIAL_NEIGHBOR_RADIUS_M (default 5 within 100m)
  3. those neighbors are similar-sized (ratio ≥ RESIDENTIAL_AREA_SIMILARITY_RATIO, default 0.5)

Industrial halls fail (1). Isolated auxiliary buildings near a plant
fail (2). Mixed-size building zones fail (3). Dense rows of houses
pass all three.

These tests use grids of synthetic boxes in a metric CRS so neighbor
counts + spacings are trivially verifiable.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from src.pipeline.build_fct_site_solar_potential import detect_residential_clusters

# Buildings must be in a metric CRS for area + buffer to be in metres.
METRIC_CRS = "EPSG:23830"


def _grid(n_x: int, n_y: int, spacing: float, size: float, origin=(0.0, 0.0)) -> gpd.GeoDataFrame:
    """Build a grid of n_x×n_y identical boxes on `spacing` m centers."""
    rows = []
    ox, oy = origin
    for i in range(n_x):
        for j in range(n_y):
            x = ox + i * spacing
            y = oy + j * spacing
            rows.append({"building_id": f"b{i}_{j}", "geometry": box(x, y, x + size, y + size)})
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=METRIC_CRS)


def test_dense_grid_of_houses_flagged_residential():
    """5x5 grid of 10x10 m houses on 25 m spacing → all 25 are residential.

    Each interior house has 8 neighbors within 100 m, all same size → all
    three conditions fire. Edge houses still have 3-5 close neighbors —
    above the min-neighbors floor."""
    gdf = _grid(n_x=5, n_y=5, spacing=25.0, size=10.0)
    mask = detect_residential_clusters(gdf)
    # Every house should be flagged in this dense same-size grid.
    assert mask.sum() == 25
    assert all(mask)


def test_isolated_building_not_flagged():
    """A single small building with no neighbors → not residential.

    Auxiliary structures near a plant (gatehouse, scale house, etc.)
    must not be filtered just because they're small."""
    gdf = gpd.GeoDataFrame(
        pd.DataFrame([{"building_id": "lone", "geometry": box(0, 0, 10, 10)}]),
        geometry="geometry",
        crs=METRIC_CRS,
    )
    mask = detect_residential_clusters(gdf)
    assert mask.sum() == 0


def test_large_industrial_halls_not_flagged():
    """A grid of large halls (above area_max) is never residential, no
    matter how dense or similar-sized."""
    # 5x5 grid of 50x50 = 2500 m² halls — well above 300 m² default
    gdf = _grid(n_x=5, n_y=5, spacing=80.0, size=50.0)
    mask = detect_residential_clusters(gdf)
    assert mask.sum() == 0  # all fail condition (1) — too big


def test_mixed_sizes_break_similarity():
    """Big and tiny buildings together fail the similarity check.

    Realistic case: a small auxiliary building next to several big halls.
    The aux building has neighbors but they're not similar-sized."""
    rows = []
    # 1 small (10x10 = 100 m²) + 6 big (50x50 = 2500 m²) within 50 m.
    rows.append({"building_id": "small", "geometry": box(0, 0, 10, 10)})
    for i in range(6):
        rows.append(
            {
                "building_id": f"big_{i}",
                "geometry": box(20 + i * 5, 20 + i * 5, 70 + i * 5, 70 + i * 5),
            }
        )
    gdf = gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs=METRIC_CRS)
    mask = detect_residential_clusters(gdf)
    # The small one fails similarity (ratio 100/2500 = 0.04 < 0.5).
    # The big ones fail condition (1) — too big.
    assert mask.sum() == 0


def test_at_threshold_min_neighbors():
    """Below min_neighbors → not residential. At threshold → residential.

    With min_neighbors=5 default, a row of 4 houses can't fire (each has
    1-3 neighbors); a row of 6+ on tight spacing does."""
    # 4 houses on 25 m spacing — every house has ≤3 close neighbors.
    sparse = _grid(n_x=4, n_y=1, spacing=25.0, size=10.0)
    mask_sparse = detect_residential_clusters(sparse)
    assert mask_sparse.sum() == 0  # below min_neighbors

    # 8 houses on same spacing — interior houses have 5+ neighbors.
    dense = _grid(n_x=8, n_y=1, spacing=25.0, size=10.0)
    mask_dense = detect_residential_clusters(dense)
    # At minimum the interior houses should fire.
    assert mask_dense.sum() >= 4


def test_threshold_overrides_propagate():
    """Passing custom thresholds overrides defaults — F10 / test hook."""
    # 3 houses, modest density. Default min_neighbors=5 → no fire.
    gdf = _grid(n_x=3, n_y=1, spacing=25.0, size=10.0)
    assert detect_residential_clusters(gdf).sum() == 0
    # With min_neighbors=2, the middle one has 2 neighbors → fires.
    mask_lenient = detect_residential_clusters(gdf, min_neighbors=2)
    assert mask_lenient.sum() >= 1


def test_empty_input_safe():
    """Zero buildings → empty mask, no crash."""
    gdf = gpd.GeoDataFrame({"building_id": [], "geometry": []}, geometry="geometry", crs=METRIC_CRS)
    mask = detect_residential_clusters(gdf)
    assert len(mask) == 0


def test_widely_spaced_houses_not_flagged():
    """Houses spaced far apart (no neighbors within radius) → not residential.

    Real-world: a rural farmstead with a few outbuildings 300 m apart.
    They're small but isolated, so they shouldn't be filtered."""
    # 200 m spacing — no neighbors within 100 m radius.
    gdf = _grid(n_x=4, n_y=4, spacing=200.0, size=10.0)
    mask = detect_residential_clusters(gdf)
    assert mask.sum() == 0
