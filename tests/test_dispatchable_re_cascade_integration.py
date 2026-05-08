# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""F2 cascade activation: kek row → SiteContext → enrich_delivered_cost.

Verifies the gluing layer that's specific to F2 (the F2 PR's load-bearing
contract): when a site row carries `geothermal_adjacency_tier`,
`build_site_context` MUST translate that into the
`dispatchable_re_coverage_pct` / `dispatchable_re_lcoe_usd_mwh` fields, and
F1's cascade MUST then read those fields and produce a delivered-cost row
distinct from the v4.0 three-layer baseline.

Without this test, F1 and F2 could each pass their own units and still ship
a regression where the cascade silently falls through to v4.0 because the
glue stops working.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import SOLAR_PRODUCTION_HOURS
from src.dash.logic.assumptions import get_default_assumptions, get_default_thresholds
from src.dash.logic.scorecard import enrich_delivered_cost
from src.dash.logic.site_context import build_site_context

DAYTIME_CAP = SOLAR_PRODUCTION_HOURS / 24.0


def _make_kek(tier: str | None) -> pd.Series:
    """Build a minimum kek row that build_site_context can consume."""
    return pd.Series(
        {
            "site_id": "test-site",
            "site_name": "Test",
            "grid_region_id": "JAVA_BALI",
            "latitude": -7.0,
            "longitude": 107.5,
            "reliability_req": 0.6,
            "green_share_geas": 0.0,
            "max_captive_capacity_mwp": 100.0,
            "max_wind_capacity_mwp": 0.0,
            "cf_wind_buildable_best": 0.0,
            "pvout_centroid": 1700.0,
            "pvout_best_50km": 1750.0,
            "within_boundary_coverage_pct": 0.30,
            "geothermal_adjacency_tier": tier,
        }
    )


def _build_ctx(tier: str | None, gc_row: pd.Series | None = None):
    """gc_row defaults to None — geothermal at ~$90/MWh competes with grid
    backfill in the overnight slot, not with cheap remote IPP solar in the
    daytime slot. Tests that want both should pass gc_row explicitly.
    """
    return build_site_context(
        kek=_make_kek(tier),
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        gc_row=gc_row,
        wb_row=pd.Series({"lcoe_mid_usd_mwh": 45.0, "cf": 0.18}),
        wind_row=None,
        default_grid_cost=110.0,
        grid_cost_by_region=None,
        grid_df=None,
        ruptl_metrics_df=None,
        demand_by_site={"test-site": 1_000_000.0},
    )


def test_no_tier_cascade_falls_through_to_v40():
    ctx = _build_ctx(tier=None)
    assert ctx.dispatchable_re_coverage_pct == 0.0
    assert ctx.dispatchable_re_lcoe_usd_mwh is None
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_dispatchable_re_fraction"] is None


def test_tier_none_cascade_falls_through_to_v40():
    ctx = _build_ctx(tier="none")
    assert ctx.dispatchable_re_coverage_pct == 0.0
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_dispatchable_re_fraction"] is None


def test_operating_within_50km_activates_layer():
    """The headline F2 win — sites near operating PLTPs see Supply Blend reduction."""
    ctx_with = _build_ctx(tier="operating_within_50km")
    ctx_without = _build_ctx(tier=None)

    assert ctx_with.dispatchable_re_coverage_pct == 0.30
    assert ctx_with.dispatchable_re_lcoe_usd_mwh == 90.0

    out_with = enrich_delivered_cost(ctx_with, {})
    out_without = enrich_delivered_cost(ctx_without, {})

    # Layer activates
    assert out_with["delivered_cost_dispatchable_re_fraction"] == 0.30
    # Delivered cost falls vs v4.0 (geothermal $90 displaces grid $110)
    assert out_with["delivered_cost_usd_mwh"] < out_without["delivered_cost_usd_mwh"]


def test_operating_within_200km_smaller_relief():
    ctx_near = _build_ctx(tier="operating_within_50km")
    ctx_far = _build_ctx(tier="operating_within_200km")

    # 30% > 15% coverage → near tier produces lower delivered cost
    out_near = enrich_delivered_cost(ctx_near, {})
    out_far = enrich_delivered_cost(ctx_far, {})
    assert out_near["delivered_cost_usd_mwh"] < out_far["delivered_cost_usd_mwh"]


def test_pipeline_post2030_no_relief_for_2030_decision():
    """Pipeline projects landing post-2030 don't reduce a 2030 supply-blend decision."""
    ctx = _build_ctx(tier="pipeline_within_200km_post2030")
    assert ctx.dispatchable_re_coverage_pct == 0.0
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_dispatchable_re_fraction"] is None


def test_pipeline_pre2030_partial_relief():
    ctx = _build_ctx(tier="pipeline_within_200km_pre2030")
    assert ctx.dispatchable_re_coverage_pct == 0.10
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_dispatchable_re_fraction"] == 0.10
