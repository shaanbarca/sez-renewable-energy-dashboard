"""Regression-pin + branch coverage for `aggregate_site_buildings()`.

This function had no direct tests before #82 — it was only covered indirectly
via `test_scorecard_golden.py`. The #82 refactor restructures the internal flow
into a per-row dispositions helper, so an explicit byte-identical pin is
required before the refactor lands.

Two test groups:

1. **Real-data golden pin** (`test_aggregate_site_buildings_byte_identical_golden`).
   Runs the function across all 81 real sites and asserts the 13-field dict
   matches `tests/fixtures/aggregate_site_buildings_golden.json` exactly. Pre-
   refactor: locks current behavior. Post-refactor: proves no drift.

   Regenerate intentionally with:
       uv run python -m tests.regen_aggregate_site_buildings_golden

2. **Synthetic branch coverage**. Each test triggers exactly one cascade
   branch (residential cluster, OSM exclusion, factory-anchor isolated,
   classifier category) so we know which path is broken when something
   fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box

from src.pipeline.build_fct_site_solar_potential import (
    DEFAULT_BUILDINGS_PARQUET,
    DEFAULT_SITES_CSV,
    PROJECTED_CRS,
    _load_exclusion_polygons,
    aggregate_site_buildings,
)

GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "aggregate_site_buildings_golden.json"


# ─── Real-data golden pin ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def buildings_proj() -> gpd.GeoDataFrame:
    if not DEFAULT_BUILDINGS_PARQUET.exists():
        pytest.skip(f"parquet not present at {DEFAULT_BUILDINGS_PARQUET}")
    gdf = gpd.read_parquet(DEFAULT_BUILDINGS_PARQUET)
    return gdf.to_crs(PROJECTED_CRS)


@pytest.fixture(scope="module")
def exclusion_polys() -> gpd.GeoDataFrame | None:
    return _load_exclusion_polygons()


@pytest.fixture(scope="module")
def site_ids() -> list[str]:
    sites = pd.read_csv(DEFAULT_SITES_CSV)
    return sorted(sites["site_id"].tolist())


def _aggregate_all_sites(
    buildings_proj: gpd.GeoDataFrame,
    exclusion_polys: gpd.GeoDataFrame | None,
    site_ids: list[str],
) -> dict[str, dict | None]:
    """Run aggregate_site_buildings for every site; None for empty sites
    (matches `build_fct_site_solar_potential()` skip behavior at line 837).
    """
    out: dict[str, dict | None] = {}
    for sid in site_ids:
        sb = buildings_proj[buildings_proj["site_id"] == sid]
        if sb.empty:
            out[sid] = None
            continue
        out[sid] = aggregate_site_buildings(
            sb,
            site_id=sid,
            exclusion_polys=exclusion_polys,
        )
    return out


def test_aggregate_site_buildings_byte_identical_golden(
    buildings_proj: gpd.GeoDataFrame,
    exclusion_polys: gpd.GeoDataFrame | None,
    site_ids: list[str],
):
    """All 81 sites must produce dict output byte-identical to the locked golden.

    The 13 fields locked: rooftop_kw_dc, rooftop_kw_ac, rooftop_solar_mwp_potential,
    total_building_footprint_m2, usable_roof_area_m2, type_filter_excluded_m2,
    building_count_total, building_count_standard_roof, building_count_elongated,
    building_count_tank_silo, building_count_conveyor, building_count_residential,
    building_count_isolated_cluster, building_count_other_excluded.

    The #82 two-mode refactor (split aggregate into per-row dispositions helper
    + aggregate dict derived from list) must not move any of these values.
    """
    if not GOLDEN_FIXTURE.exists():
        pytest.fail(
            f"Golden fixture missing: {GOLDEN_FIXTURE}.\n"
            f"Regenerate: uv run python -m tests.regen_aggregate_site_buildings_golden"
        )

    current = _aggregate_all_sites(buildings_proj, exclusion_polys, site_ids)
    expected = json.loads(GOLDEN_FIXTURE.read_text())

    # Per-site comparison gives clearer failure messages than one giant diff.
    drift: list[str] = []
    for sid in site_ids:
        if current.get(sid) != expected.get(sid):
            drift.append(
                f"  {sid}:\n    expected: {expected.get(sid)}\n    actual:   {current.get(sid)}"
            )
    if drift:
        joined = "\n".join(drift)
        pytest.fail(
            f"aggregate_site_buildings() drift on {len(drift)} site(s):\n{joined}\n\n"
            f"If this drift is intentional, regenerate the golden:\n"
            f"    uv run python -m tests.regen_aggregate_site_buildings_golden"
        )


# ─── Synthetic branch coverage ─────────────────────────────────────────────
#
# Each test builds a tiny in-memory GeoDataFrame in PROJECTED_CRS and asserts
# the cascade routes the building(s) to the expected category. Synthetic
# buildings use simple shapely shapes that trivially trigger one classifier
# branch each — see test_buildings_classifier.py for the classifier specs we
# inherit.
#
# Coordinates are in meters (PROJECTED_CRS = EPSG:23830, Indonesia UTM 50S),
# placed near Jakarta to keep the lat/lon legal but the values don't matter —
# the cascade only cares about shape + area + neighbor distance.


def _proj_gdf(rows: list[dict], origin_x: float = 700_000.0, origin_y: float = 9_300_000.0):
    """Build a synthetic GeoDataFrame in PROJECTED_CRS from a list of {geom, ...} dicts.

    Each row gets a unique building_id; site_id defaults to 'synthetic-site'.
    """
    enriched = []
    for i, r in enumerate(rows):
        enriched.append(
            {
                "building_id": r.get("building_id", f"synth_{i}"),
                "site_id": r.get("site_id", "synthetic-site"),
                "source_name": r.get("source_name", "synthetic"),
                "source_vintage": r.get("source_vintage", "2023-05"),
                **r,
            }
        )
    return gpd.GeoDataFrame(enriched, geometry="geom", crs=PROJECTED_CRS).rename_geometry(
        "geometry"
    )


def test_synthetic_single_standard_roof_classified():
    """A 240 m² rectangular roof classifies as standard_roof.

    Note: a lone standard_roof without a factory anchor (>1000 m²) nearby
    gets flipped to isolated_cluster by Pass 2. We assert only the classifier
    result (count) here; the anchor-survives behavior is tested separately.
    """
    rect = box(0, 0, 30, 8)  # 240 m², standard shape
    gdf = _proj_gdf([{"geom": rect}])
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_standard_roof"] == 1
    assert out["total_building_footprint_m2"] == pytest.approx(240.0, rel=1e-3)


def test_synthetic_standard_roof_with_anchor_produces_solar():
    """Standard roof + factory anchor in same cluster → usable solar.

    The end-to-end happy path: classify as standard_roof AND survive the
    factory-anchor filter → contributes to rooftop_solar_mwp_potential.
    """
    anchor = box(0, 0, 50, 30)  # 1500 m² anchor (>FACTORY_ANCHOR_MIN_AREA_M2)
    roof = box(70, 0, 100, 8)  # 240 m² standard roof
    gdf = _proj_gdf([{"geom": anchor}, {"geom": roof}])
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_standard_roof"] == 2
    assert out["building_count_isolated_cluster"] == 0
    # Both buildings × multiplier 1.0
    assert out["usable_roof_area_m2"] == pytest.approx(1500.0 + 240.0, rel=1e-3)
    assert out["rooftop_solar_mwp_potential"] > 0


def test_synthetic_too_small_excluded():
    """Below 200 m² → too_small bucket → other_excluded, zero solar."""
    tiny = box(0, 0, 5, 5)  # 25 m²
    gdf = _proj_gdf([{"geom": tiny}])
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_other_excluded"] == 1
    assert out["rooftop_solar_mwp_potential"] == 0.0
    assert out["type_filter_excluded_m2"] == pytest.approx(25.0, rel=1e-3)


def test_synthetic_tank_silo_geometric():
    """Near-circular polygon → geometric tank_silo → tank_silo bucket, zero solar."""
    circle = Point(100, 100).buffer(20, quad_segs=16)
    gdf = _proj_gdf([{"geom": circle}])
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_tank_silo"] == 1
    assert out["rooftop_solar_mwp_potential"] == 0.0


def test_synthetic_conveyor_long_thin_classified():
    """Aspect ratio >15 → conveyor (lone → isolated; usable area asserted with anchor)."""
    anchor = box(0, 0, 50, 30)  # 1500 m² anchor
    thin = box(70, 0, 270, 5)  # aspect 40:1, 1000 m²
    gdf = _proj_gdf([{"geom": anchor}, {"geom": thin}])
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_conveyor"] == 1
    # anchor (1500 × 1.0) + conveyor (1000 × 0.1)
    assert out["usable_roof_area_m2"] == pytest.approx(1500.0 + 100.0, rel=1e-3)


def test_synthetic_residential_cluster_excluded():
    """Many small similar buildings clustered → residential cluster → excluded.

    Residential detection requires:
      - building area ≤ RESIDENTIAL_AREA_MAX_M2 (default 250)
      - similar-sized neighbors within RESIDENTIAL_NEIGHBOR_RADIUS_M (default 30)
      - at least RESIDENTIAL_MIN_NEIGHBORS (default 5) such neighbors

    8 houses in a 30m-spacing grid trigger the filter for all of them.
    """
    rows = []
    for i in range(8):
        x = (i % 4) * 15  # 4 per row, 15m apart
        y = (i // 4) * 15  # 2 rows, 15m apart
        rows.append({"geom": box(x, y, x + 10, y + 10)})  # 100 m² each
    gdf = _proj_gdf(rows)
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_residential"] == 8
    assert out["rooftop_solar_mwp_potential"] == 0.0


def test_synthetic_isolated_cluster_factory_anchor_filter():
    """Suitable buildings without a large factory anchor → isolated_cluster.

    The factory-anchor filter drops suitable-class buildings whose spatial
    cluster lacks any building ≥ FACTORY_ANCHOR_MIN_AREA_M2 (default 1000).
    Three modest warehouses (300 m² each) clustered together with no large
    factory anchor → all three flip to isolated_cluster.
    """
    rows = []
    for i in range(3):
        x = i * 40
        rows.append({"geom": box(x, 0, x + 20, 15)})  # 300 m² each, standard roof shape
    gdf = _proj_gdf(rows)
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    # All 3 classify as standard_roof but flip to isolated_cluster post-Pass 2
    assert out["building_count_isolated_cluster"] == 3
    assert out["rooftop_solar_mwp_potential"] == 0.0


def test_synthetic_factory_anchor_rescues_cluster():
    """When the cluster has a factory anchor (>=FACTORY_ANCHOR_MIN_AREA_M2 = 1500),
    the suitable warehouses stay suitable and survive the isolation filter."""
    anchor = box(0, 0, 50, 40)  # 2000 m², well above 1500 threshold
    # Three medium warehouses nearby (>=300 m² avoids residential filter)
    warehouses = [box(70 + i * 40, 0, 70 + i * 40 + 25, 15) for i in range(3)]  # 375 m² each
    rows = [{"geom": anchor}] + [{"geom": w} for w in warehouses]
    gdf = _proj_gdf(rows)
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_isolated_cluster"] == 0
    assert out["building_count_total"] == 4


def test_synthetic_osm_exclusion_polygon_drops_building():
    """A building inside an OSM tank/basin/water polygon → forced into tank_silo bucket.

    The exclusion check runs BEFORE the geometric classifier — even a standard
    rectangular warehouse footprint gets re-tagged as tank_silo when its
    centroid falls inside the exclusion polygon.
    """
    warehouse = box(0, 0, 30, 20)  # 600 m² standard roof shape
    gdf = _proj_gdf([{"geom": warehouse}])

    # Build an exclusion polygon that covers the warehouse (in lon/lat for
    # the load_exclusion path; here we bypass the loader and pass a hand-built
    # GeoDataFrame in PROJECTED_CRS that buildings_inside_exclusions accepts).
    exclusion = gpd.GeoDataFrame(
        {
            "site_id": ["synthetic-site"],
            "exclusion_type": ["tank"],
            "geometry": [Polygon([(-5, -5), (35, -5), (35, 25), (-5, 25)])],
        },
        geometry="geometry",
        crs=PROJECTED_CRS,
    )
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=exclusion)
    assert out["building_count_tank_silo"] == 1
    assert out["rooftop_solar_mwp_potential"] == 0.0
    assert out["type_filter_excluded_m2"] == pytest.approx(600.0, rel=1e-3)


def test_synthetic_mixed_categories_count_correctly():
    """Mixed cascade — one of each category survives to the right bucket."""
    rows = [
        {"geom": box(0, 0, 30, 8)},  # standard_roof (240 m²)
        {"geom": box(100, 0, 200, 12)},  # elongated (1200 m², aspect 8.3)
        {"geom": Point(300, 0).buffer(20, quad_segs=16)},  # tank_silo (geometric)
        {"geom": box(400, 0, 600, 5)},  # conveyor (1000 m², aspect 40)
        {"geom": box(700, 0, 705, 5)},  # too_small (25 m²)
    ]
    gdf = _proj_gdf(rows)
    out = aggregate_site_buildings(gdf, site_id="synthetic-site", exclusion_polys=None)
    assert out["building_count_standard_roof"] == 1
    assert out["building_count_elongated"] == 1
    assert out["building_count_tank_silo"] == 1
    assert out["building_count_conveyor"] == 1
    # too_small lands in other_excluded
    assert out["building_count_other_excluded"] >= 1
