# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Unit tests for src.model.geothermal_adjacency.

Covers (1) tier classification at the boundary distances + the pipeline
horizon split, and (2) the dispatchable_re_from_geothermal_tier translator
that converts a tier into the (coverage_pct, lcoe) inputs that F1's Supply
Blend cascade reads off SiteContext.
"""

from __future__ import annotations

import pytest

from src.model.geothermal_adjacency import (
    DISPATCHABLE_RE_COVERAGE_BY_TIER,
    GEOTHERMAL_LCOE_USD_MWH_PROXY,
    OPERATING_FAR_KM,
    OPERATING_NEAR_KM,
    PIPELINE_DECISION_HORIZON_YEAR,
    PIPELINE_REACH_KM,
    dispatchable_re_from_geothermal_tier,
    geothermal_tier,
)

# ── Tier classification ──────────────────────────────────────────────────────


def test_tier_operating_within_50km_inside_boundary():
    assert geothermal_tier(operating_km=10.0, pipeline_km=None, pipeline_year=None) == (
        "operating_within_50km"
    )


def test_tier_operating_within_50km_at_boundary():
    """Boundary is inclusive — 50 km exact still counts as 'within 50 km'."""
    assert geothermal_tier(OPERATING_NEAR_KM, None, None) == "operating_within_50km"


def test_tier_operating_within_200km_just_past_50():
    assert geothermal_tier(operating_km=51.0, pipeline_km=None, pipeline_year=None) == (
        "operating_within_200km"
    )


def test_tier_operating_within_200km_at_boundary():
    assert geothermal_tier(OPERATING_FAR_KM, None, None) == "operating_within_200km"


def test_tier_pipeline_pre2030():
    assert geothermal_tier(operating_km=None, pipeline_km=150.0, pipeline_year=2027) == (
        "pipeline_within_200km_pre2030"
    )


def test_tier_pipeline_post2030_at_horizon():
    """The horizon year (2030) is treated as 'post' since RUPTL COD won't help a 2030 decision."""
    assert geothermal_tier(operating_km=None, pipeline_km=150.0, pipeline_year=2030) == (
        "pipeline_within_200km_post2030"
    )


def test_tier_pipeline_post2030():
    assert geothermal_tier(operating_km=None, pipeline_km=150.0, pipeline_year=2033) == (
        "pipeline_within_200km_post2030"
    )


def test_tier_pipeline_outside_reach():
    assert geothermal_tier(
        operating_km=None, pipeline_km=PIPELINE_REACH_KM + 1, pipeline_year=2027
    ) == ("none")


def test_tier_no_data():
    assert geothermal_tier(operating_km=None, pipeline_km=None, pipeline_year=None) == "none"


def test_tier_operating_wins_over_pipeline_when_both_close():
    """Operating realised RE > planned future. If a site has both within reach,
    classify by the operating bucket."""
    result = geothermal_tier(operating_km=20.0, pipeline_km=10.0, pipeline_year=2027)
    assert result == "operating_within_50km"


def test_tier_pipeline_year_required_for_split():
    """No pipeline year → conservative: treat as post-2030 (don't claim pre-2030 relief)."""
    assert geothermal_tier(operating_km=None, pipeline_km=100.0, pipeline_year=None) == (
        "pipeline_within_200km_post2030"
    )


# ── Translator ───────────────────────────────────────────────────────────────


def test_translator_none_returns_no_op():
    assert dispatchable_re_from_geothermal_tier(None) == (0.0, None)


def test_translator_unknown_tier_returns_no_op():
    assert dispatchable_re_from_geothermal_tier("operating_within_25km") == (0.0, None)


def test_translator_operating_within_50km_uses_30pct():
    cov, lcoe = dispatchable_re_from_geothermal_tier("operating_within_50km")
    assert cov == 0.30
    assert lcoe == GEOTHERMAL_LCOE_USD_MWH_PROXY


def test_translator_operating_within_200km_uses_15pct():
    cov, lcoe = dispatchable_re_from_geothermal_tier("operating_within_200km")
    assert cov == 0.15
    assert lcoe == GEOTHERMAL_LCOE_USD_MWH_PROXY


def test_translator_pipeline_pre2030_uses_10pct():
    cov, lcoe = dispatchable_re_from_geothermal_tier("pipeline_within_200km_pre2030")
    assert cov == 0.10
    assert lcoe == GEOTHERMAL_LCOE_USD_MWH_PROXY


def test_translator_pipeline_post2030_no_op():
    """post-2030 pipeline doesn't relieve a 2030 decision — translator returns no contribution."""
    assert dispatchable_re_from_geothermal_tier("pipeline_within_200km_post2030") == (0.0, None)


def test_translator_none_tier_string_no_op():
    assert dispatchable_re_from_geothermal_tier("none") == (0.0, None)


def test_translator_custom_lcoe_passes_through():
    cov, lcoe = dispatchable_re_from_geothermal_tier("operating_within_50km", lcoe_usd_mwh=72.0)
    assert cov == 0.30
    assert lcoe == 72.0


def test_translator_coverage_table_is_monotone_decreasing():
    """Realised RE > pipeline pre-2030 > pipeline post-2030 / none.
    Catches accidental re-ordering of the dispatch table.
    """
    by_tier = DISPATCHABLE_RE_COVERAGE_BY_TIER
    assert by_tier["operating_within_50km"] >= by_tier["operating_within_200km"]
    assert by_tier["operating_within_200km"] >= by_tier["pipeline_within_200km_pre2030"]
    assert by_tier["pipeline_within_200km_pre2030"] >= by_tier["pipeline_within_200km_post2030"]
    assert by_tier["pipeline_within_200km_post2030"] == 0.0
    assert by_tier["none"] == 0.0


# ── Constants sanity ─────────────────────────────────────────────────────────


def test_constants_are_in_expected_ranges():
    assert OPERATING_NEAR_KM == 50.0
    assert OPERATING_FAR_KM == 200.0
    assert PIPELINE_REACH_KM == 200.0
    assert PIPELINE_DECISION_HORIZON_YEAR == 2030


def test_lcoe_proxy_in_esdm_2024_band():
    """ESDM Tech Catalogue 2024 §1 Table 1.5 lists geothermal HT/LT in $80-110/MWh."""
    assert 70.0 <= GEOTHERMAL_LCOE_USD_MWH_PROXY <= 120.0


@pytest.mark.parametrize(
    "operating_km,pipeline_km,year,expected_cov",
    [
        (10.0, None, None, 0.30),  # operating_within_50km
        (100.0, None, None, 0.15),  # operating_within_200km
        (None, 100.0, 2027, 0.10),  # pipeline pre-2030
        (None, 100.0, 2032, 0.0),  # pipeline post-2030
        (None, 500.0, 2027, 0.0),  # outside reach
        (None, None, None, 0.0),  # no data
    ],
)
def test_end_to_end_tier_to_coverage(
    operating_km: float | None,
    pipeline_km: float | None,
    year: int | None,
    expected_cov: float,
):
    """End-to-end: distance + year → tier → coverage. Mirrors the F1 cascade activation path."""
    tier = geothermal_tier(operating_km, pipeline_km, year)
    cov, _ = dispatchable_re_from_geothermal_tier(tier)
    assert cov == expected_cov
