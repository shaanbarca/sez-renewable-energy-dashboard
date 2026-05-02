"""Tests for the fence-boundary polygon clip + exclusion-polygon paths.

`_clip_buildings_to_site_polygons` drops buildings whose centroid falls
outside the fence boundary for sites that HAVE one. Sites without a
polygon (no KEK polygon, no OSM industrial polygon) pass through
unchanged on the upstream 2 km buffer.

`buildings_inside_exclusions` returns a per-building mask of buildings
whose centroid is inside an OSM-tagged tank/basin/water polygon —
those get reclassified `tank_silo` (multiplier 0) downstream.

These tests use synthetic site polygons + buildings in EPSG:4326 so
the geometry is trivially verifiable without needing real-world data.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

from src.pipeline.build_fct_site_solar_potential import (
    _clip_buildings_to_site_polygons,
    buildings_inside_exclusions,
)


def _bldg_gdf(rows: list[dict]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


def _poly_gdf(rows: list[dict]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


# ─── _clip_buildings_to_site_polygons ─────────────────────────────────────


def test_clip_drops_buildings_outside_polygon():
    """Buildings whose centroid falls outside the fence boundary are dropped.

    Real example: a 2 km buffer around Cemindo Bayah's centroid pulls in
    nearby coastal village. The OSM industrial polygon clip drops the
    village rows while keeping the in-fence buildings.
    """
    site_poly = box(0, 0, 10, 10)  # the "fence boundary"
    polys = _poly_gdf([{"site_id": "site-a", "geometry": site_poly}])
    bldgs = _bldg_gdf(
        [
            {"site_id": "site-a", "building_id": "in1", "geometry": box(2, 2, 4, 4)},
            {"site_id": "site-a", "building_id": "in2", "geometry": box(5, 5, 7, 7)},
            {"site_id": "site-a", "building_id": "out", "geometry": box(20, 20, 22, 22)},
        ]
    )
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    assert len(out) == 2
    assert set(out["building_id"]) == {"in1", "in2"}


def test_clip_passthrough_for_sites_without_polygon():
    """A site without a fence polygon keeps all its 2 km-buffer buildings.

    Polygon coverage is partial (11 of 81 sites). Untouched sites must
    not be silently emptied just because a polygon was added for a
    different site."""
    site_a = box(0, 0, 10, 10)
    polys = _poly_gdf([{"site_id": "site-a", "geometry": site_a}])
    bldgs = _bldg_gdf(
        [
            {"site_id": "site-a", "building_id": "a-in", "geometry": box(2, 2, 4, 4)},
            {"site_id": "site-b", "building_id": "b-far", "geometry": box(20, 20, 22, 22)},
            {"site_id": "site-b", "building_id": "b-also-far", "geometry": box(50, 50, 52, 52)},
        ]
    )
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    # site-a: clipped to in-polygon. site-b: kept as-is (no polygon).
    site_b_kept = out[out["site_id"] == "site-b"]
    assert len(site_b_kept) == 2  # both b- rows kept
    assert (out[out["site_id"] == "site-a"]["building_id"] == "a-in").all()


def test_clip_empty_buildings_input():
    """Zero buildings → zero output, no crash."""
    polys = _poly_gdf([{"site_id": "site-a", "geometry": box(0, 0, 10, 10)}])
    bldgs = gpd.GeoDataFrame(
        {"site_id": [], "building_id": [], "geometry": []},
        geometry="geometry",
        crs="EPSG:4326",
    )
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    assert len(out) == 0


def test_clip_empty_polygons_input():
    """Zero polygons → input passes through unchanged.

    First-run reality: before any polygons existed, every site relied on
    the upstream 2 km buffer. The clip must be a no-op when polygons
    aren't loaded yet."""
    polys = gpd.GeoDataFrame({"site_id": [], "geometry": []}, geometry="geometry", crs="EPSG:4326")
    bldgs = _bldg_gdf([{"site_id": "site-a", "building_id": "any", "geometry": box(0, 0, 1, 1)}])
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    assert len(out) == 1


def test_clip_per_site_isolation():
    """Each site's polygon only clips THAT site's buildings — buildings at
    site-b aren't dropped because they're outside site-a's polygon."""
    polys = _poly_gdf(
        [
            {"site_id": "site-a", "geometry": box(0, 0, 10, 10)},
            {"site_id": "site-b", "geometry": box(100, 100, 110, 110)},
        ]
    )
    bldgs = _bldg_gdf(
        [
            {"site_id": "site-a", "building_id": "a-in", "geometry": box(2, 2, 4, 4)},
            {"site_id": "site-b", "building_id": "b-in", "geometry": box(102, 102, 104, 104)},
        ]
    )
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    assert len(out) == 2  # both buildings are inside their own site's polygon
    assert set(out["building_id"]) == {"a-in", "b-in"}


def test_clip_irregular_polygon_works():
    """Irregular polygons (e.g. Tanjung Sauh's 6 island fragments) — the
    `within()` test handles non-rectangular boundaries correctly."""
    # An L-shape polygon — only the corner pieces are inside.
    L = Polygon([(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)])
    polys = _poly_gdf([{"site_id": "L", "geometry": L}])
    bldgs = _bldg_gdf(
        [
            {"site_id": "L", "building_id": "in-corner", "geometry": box(1, 1, 3, 3)},
            {"site_id": "L", "building_id": "in-arm", "geometry": box(1, 7, 3, 9)},
            {"site_id": "L", "building_id": "out-notch", "geometry": box(7, 7, 9, 9)},
        ]
    )
    out = _clip_buildings_to_site_polygons(bldgs, polys)
    assert set(out["building_id"]) == {"in-corner", "in-arm"}


# ─── buildings_inside_exclusions ──────────────────────────────────────────


def test_exclusions_returns_false_when_no_polys():
    """No exclusion file loaded → all-False mask, no crash."""
    bldgs = _bldg_gdf([{"site_id": "s", "building_id": "1", "geometry": box(0, 0, 1, 1)}])
    mask = buildings_inside_exclusions(bldgs, "s", None)
    assert mask.sum() == 0
    assert len(mask) == 1


def test_exclusions_flags_buildings_inside_tank():
    """Building centroid inside an OSM tank polygon → flagged True.

    Real example: water tanks at Cemindo Bayah that the geometric
    classifier misses (irregular shape → low circularity) but OSM has
    tagged as `man_made=storage_tank`."""
    bldgs = _bldg_gdf(
        [
            {"site_id": "s", "building_id": "in-tank", "geometry": box(2, 2, 3, 3)},
            {"site_id": "s", "building_id": "off-tank", "geometry": box(20, 20, 21, 21)},
        ]
    )
    excl = _poly_gdf([{"site_id": "s", "geometry": box(0, 0, 10, 10)}])
    mask = buildings_inside_exclusions(bldgs, "s", excl)
    assert mask.tolist() == [True, False]


def test_exclusions_per_site_isolation():
    """An exclusion polygon at site-A doesn't flag a building at site-B."""
    bldgs = _bldg_gdf(
        [
            {"site_id": "site-b", "building_id": "b-bldg", "geometry": box(2, 2, 3, 3)},
        ]
    )
    # Exclusion polygon at site-A overlaps the b-bldg coords but applies
    # only to site-A's buildings.
    excl = _poly_gdf([{"site_id": "site-a", "geometry": box(0, 0, 10, 10)}])
    mask = buildings_inside_exclusions(bldgs, "site-b", excl)
    assert mask.sum() == 0  # site-b has no exclusions → all False


def test_exclusions_empty_buildings():
    """Empty buildings input → empty mask."""
    bldgs = gpd.GeoDataFrame(
        {"site_id": [], "building_id": [], "geometry": []},
        geometry="geometry",
        crs="EPSG:4326",
    )
    excl = _poly_gdf([{"site_id": "s", "geometry": box(0, 0, 10, 10)}])
    mask = buildings_inside_exclusions(bldgs, "s", excl)
    assert len(mask) == 0
