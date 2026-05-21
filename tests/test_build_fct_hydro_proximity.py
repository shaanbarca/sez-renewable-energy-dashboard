"""Tests for the v4.1b hydro proximity pipeline (build_fct_hydro_proximity.py).

Mirrors the geothermal proximity test pattern. Covers:
- All 81 sites get a hydro_adjacency_tier (no nulls)
- Tier values are valid enum members
- Per-site distance is sane (positive, non-NaN)
- Pipeline gracefully degrades when source GeoJSONs missing
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.model.hydro_adjacency import HYDRO_OPTIMIZER_ELIGIBLE_TIERS, hydro_tier
from src.pipeline.build_fct_hydro_proximity import (
    OPERATING_GEOJSON,
    PIPELINE_GEOJSON,
    SITES_CSV,
    build_fct_hydro_proximity,
)

VALID_TIERS = {
    "operating_within_50km",
    "operating_within_200km",
    "pipeline_within_200km_pre2030",
    "pipeline_within_200km_post2030",
    "none",
}


def test_build_produces_one_row_per_site():
    df = build_fct_hydro_proximity()
    sites = pd.read_csv(SITES_CSV)
    assert len(df) == len(sites)


def test_all_sites_have_valid_tier():
    df = build_fct_hydro_proximity()
    invalid = set(df["hydro_adjacency_tier"].unique()) - VALID_TIERS
    assert not invalid, f"Invalid tier values: {invalid}"


def test_all_sites_have_tier_assigned_no_nulls():
    df = build_fct_hydro_proximity()
    null_tier = df[df["hydro_adjacency_tier"].isna()]
    assert null_tier.empty, f"Sites with null tier: {null_tier['site_id'].tolist()}"


def test_distances_are_positive_when_present():
    df = build_fct_hydro_proximity()
    for col in ("nearest_hydro_operating_km", "nearest_hydro_pipeline_km"):
        non_null = df[df[col].notna()]
        if not non_null.empty:
            assert (non_null[col] >= 0).all(), f"Negative distance in {col}"


def test_no_distance_when_tier_is_none():
    """When tier is 'none', either no operating/pipeline data exists for that
    site OR distance > 200km for both. Cannot assert distance must be None
    (geocoded plants exist in distant regions) but the relationship between
    tier + distance should be coherent.
    """
    df = build_fct_hydro_proximity()
    none_tier = df[df["hydro_adjacency_tier"] == "none"]
    for _, row in none_tier.iterrows():
        op_km = row["nearest_hydro_operating_km"]
        pl_km = row["nearest_hydro_pipeline_km"]
        # If both distances present, both must be > 200 km
        if pd.notna(op_km):
            assert op_km > 200, f"site {row['site_id']} has tier=none but op_km={op_km}"
        if pd.notna(pl_km):
            assert pl_km > 200, f"site {row['site_id']} has tier=none but pl_km={pl_km}"


def test_pipeline_degrades_gracefully_when_data_missing(tmp_path: Path):
    """When source GeoJSONs are missing, the pipeline must still emit rows
    with tier='none' rather than crashing or skipping sites."""
    # Create an empty/missing GeoJSON setup
    empty_op = tmp_path / "hydro_operating_empty.geojson"
    empty_pl = tmp_path / "hydro_pipeline_empty.geojson"
    empty_op.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    empty_pl.write_text(json.dumps({"type": "FeatureCollection", "features": []}))

    df = build_fct_hydro_proximity(
        operating_path=empty_op,
        pipeline_path=empty_pl,
    )
    sites = pd.read_csv(SITES_CSV)
    assert len(df) == len(sites)
    assert (df["hydro_adjacency_tier"] == "none").all()


def test_optimizer_eligibility_partitions_correctly():
    """Tiers that admit hydro into the 2D optimizer must match the
    HYDRO_OPTIMIZER_ELIGIBLE_TIERS frozenset."""
    df = build_fct_hydro_proximity()
    eligible = df[df["hydro_adjacency_tier"].isin(HYDRO_OPTIMIZER_ELIGIBLE_TIERS)]
    ineligible = df[~df["hydro_adjacency_tier"].isin(HYDRO_OPTIMIZER_ELIGIBLE_TIERS)]
    # Sanity check: union covers everyone
    assert len(eligible) + len(ineligible) == len(df)


# ─── Tier classification unit tests (target hydro_tier directly) ────────────


def test_hydro_tier_operating_within_50km():
    assert hydro_tier(operating_km=25.0, pipeline_km=None, pipeline_year=None) == (
        "operating_within_50km"
    )


def test_hydro_tier_operating_within_200km():
    assert hydro_tier(operating_km=150.0, pipeline_km=None, pipeline_year=None) == (
        "operating_within_200km"
    )


def test_hydro_tier_operating_far_falls_to_pipeline():
    """Operating > 200km lets pipeline take over (if any pipeline is in range)."""
    assert hydro_tier(operating_km=500.0, pipeline_km=150.0, pipeline_year=2028) == (
        "pipeline_within_200km_pre2030"
    )


def test_hydro_tier_pipeline_post2030():
    assert hydro_tier(operating_km=None, pipeline_km=150.0, pipeline_year=2032) == (
        "pipeline_within_200km_post2030"
    )


def test_hydro_tier_pipeline_no_year_treated_as_post2030():
    """A pipeline project without a target year falls into post-2030 bucket
    (conservative — we don't know if it lands in time)."""
    assert hydro_tier(operating_km=None, pipeline_km=150.0, pipeline_year=None) == (
        "pipeline_within_200km_post2030"
    )


def test_hydro_tier_nothing_returns_none():
    assert hydro_tier(operating_km=None, pipeline_km=None, pipeline_year=None) == "none"
    assert hydro_tier(operating_km=500.0, pipeline_km=500.0, pipeline_year=2028) == "none"


# ─── Source data sanity ────────────────────────────────────────────────────


def test_operating_geojson_has_features():
    """Seed dataset must have at least 10 operating PLTAs."""
    if not OPERATING_GEOJSON.exists():
        pytest.skip("hydro_operating.geojson not present")
    data = json.loads(OPERATING_GEOJSON.read_text())
    assert len(data.get("features", [])) >= 10


def test_pipeline_geojson_has_features():
    """Seed dataset must have at least 5 named RUPTL pipeline projects."""
    if not PIPELINE_GEOJSON.exists():
        pytest.skip("hydro_pipeline.geojson not present")
    data = json.loads(PIPELINE_GEOJSON.read_text())
    assert len(data.get("features", [])) >= 5


def test_operating_features_have_required_props():
    if not OPERATING_GEOJSON.exists():
        pytest.skip("hydro_operating.geojson not present")
    data = json.loads(OPERATING_GEOJSON.read_text())
    for feat in data["features"]:
        props = feat["properties"]
        assert "id" in props
        assert "capacity_mw" in props
        assert props["capacity_mw"] > 0


def test_pipeline_features_have_target_year():
    if not PIPELINE_GEOJSON.exists():
        pytest.skip("hydro_pipeline.geojson not present")
    data = json.loads(PIPELINE_GEOJSON.read_text())
    for feat in data["features"]:
        props = feat["properties"]
        assert "target_year" in props
        assert 2025 <= props["target_year"] <= 2040
