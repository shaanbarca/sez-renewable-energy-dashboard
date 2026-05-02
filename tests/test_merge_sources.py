"""Tests for `merge_sources()` — IoU-based spatial dedup of two building
parquets per spec §13.10 invariant 4 (RV7 / Microsoft GMLBF integration).

Synthetic-fixture tests using small polygon grids so the IoU geometry is
trivially verifiable. Real-data integration test runs once Phase 2's
sites_buildings_microsoft.parquet exists.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from src.pipeline.build_fct_site_solar_potential import merge_sources

REQUIRED_COLS = ["building_id", "site_id", "source_name", "source_vintage", "geometry"]


def _row(bid: str, site: str, source: str, geom, vintage: str = "2023-05") -> dict:
    return {
        "building_id": bid,
        "site_id": site,
        "source_name": source,
        "source_vintage": vintage,
        "geometry": geom,
    }


def _gdf(rows: list[dict]) -> gpd.GeoDataFrame:
    if not rows:
        return gpd.GeoDataFrame(
            {col: [] for col in REQUIRED_COLS}, geometry="geometry", crs="EPSG:4326"
        )
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


def test_merge_empty_secondary_returns_primary():
    """Phase 1 reality: only GoB parquet exists. Behavior must be byte-identical."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    secondary = _gdf([])
    out = merge_sources(primary, secondary)
    assert len(out) == 1
    assert out.iloc[0]["source_name"] == "gob_v3"


def test_merge_drops_high_iou_duplicate():
    """Same building seen by both sources → primary kept, secondary dropped."""
    geom = box(0, 0, 1, 1)
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", geom)])
    # Slight wobble (~95% IoU) — clearly the same building.
    secondary = _gdf([_row("ms_gmlbf:1", "site-a", "ms_gmlbf", box(0.02, 0.02, 1.02, 1.02))])
    out = merge_sources(primary, secondary)
    assert len(out) == 1
    assert out.iloc[0]["source_name"] == "gob_v3"  # primary wins


def test_merge_keeps_low_iou_disjoint():
    """Different buildings nearby → both kept (no false dedup)."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    secondary = _gdf([_row("ms_gmlbf:1", "site-a", "ms_gmlbf", box(2, 2, 3, 3))])  # disjoint
    out = merge_sources(primary, secondary)
    assert len(out) == 2
    assert set(out["source_name"]) == {"gob_v3", "ms_gmlbf"}


def test_merge_keeps_partial_overlap_below_threshold():
    """50%-area overlap of equal squares → IoU = 0.33 < 0.5 → both kept.

    A real-world case: GoB detected one continuous warehouse, MS split
    the same hall into two abutting polygons. Below the threshold, we
    keep both to avoid over-dedup. The classifier downstream may merge
    based on shared edges (RV9, separate concern)."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    # Shifted by 0.5 → intersection 0.5, union 1.5, IoU = 0.33
    secondary = _gdf([_row("ms_gmlbf:1", "site-a", "ms_gmlbf", box(0.5, 0, 1.5, 1))])
    out = merge_sources(primary, secondary, iou_threshold=0.5)
    assert len(out) == 2


def test_merge_site_isolation():
    """Dedup is per-site — a building at site A doesn't dedup a building
    with the same geometry at site B. Buffers are 2 km; sites don't share."""
    geom = box(0, 0, 1, 1)
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", geom)])
    # Same geometry but tagged to a different site (e.g. nickel cluster
    # near a cement plant — geographically same building zone but each
    # site_id has its own buffer + dim_sites row).
    secondary = _gdf([_row("ms_gmlbf:1", "site-b", "ms_gmlbf", geom)])
    out = merge_sources(primary, secondary)
    assert len(out) == 2
    assert set(out["site_id"]) == {"site-a", "site-b"}


def test_merge_secondary_only_site_passes_through():
    """Site has no GoB rows but has MS rows — MS fills the gap entirely
    (the RV7 / Cemindo Bayah pattern: GoB returns zero, MS sees the plant)."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    secondary = _gdf(
        [
            _row("ms_gmlbf:1", "site-b", "ms_gmlbf", box(10, 10, 11, 11)),
            _row("ms_gmlbf:2", "site-b", "ms_gmlbf", box(11, 10, 12, 11)),
        ]
    )
    out = merge_sources(primary, secondary)
    assert len(out) == 3
    assert (out["site_id"] == "site-b").sum() == 2


def test_merge_threshold_parameter_respected():
    """At threshold=0.9, the +0.5 shift case (IoU 0.33) is still kept;
    at threshold=0.3 the same case becomes a duplicate."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    secondary = _gdf([_row("ms_gmlbf:1", "site-a", "ms_gmlbf", box(0.5, 0, 1.5, 1))])
    assert len(merge_sources(primary, secondary, iou_threshold=0.9)) == 2  # both kept
    assert len(merge_sources(primary, secondary, iou_threshold=0.3)) == 1  # MS dropped


def test_merge_preserves_primary_columns_only():
    """Secondary may carry extra columns (e.g. MS height); merge output
    should only carry primary's columns to avoid surprising downstream
    callers."""
    primary = _gdf([_row("gob_v3:1", "site-a", "gob_v3", box(0, 0, 1, 1))])
    secondary_rows = [
        {**_row("ms_gmlbf:1", "site-a", "ms_gmlbf", box(5, 5, 6, 6)), "ms_height_m": 12.3}
    ]
    secondary = gpd.GeoDataFrame(pd.DataFrame(secondary_rows), geometry="geometry", crs="EPSG:4326")
    out = merge_sources(primary, secondary)
    assert "ms_height_m" not in out.columns
    assert set(out.columns) == set(primary.columns)
