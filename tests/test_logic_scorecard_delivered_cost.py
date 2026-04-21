"""Tests for `enrich_delivered_cost` — METHODOLOGY §5.4 blended delivered cost.

Unit-tests the enricher in isolation by constructing minimal `SiteContext`
instances. Does not go through `compute_scorecard_live`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.dash.logic.assumptions import get_default_assumptions, get_default_thresholds
from src.dash.logic.scorecard import enrich_delivered_cost
from src.dash.logic.site_context import SiteContext


def _make_ctx(
    *,
    wb_lcoe: float | None = 50.0,
    grid_cost: float = 80.0,
    eff_cov: float | None = 0.5,
) -> SiteContext:
    """Construct a minimal SiteContext with only the fields the enricher reads."""
    wb_row: pd.Series | None
    if wb_lcoe is None:
        wb_row = None
    else:
        wb_row = pd.Series({"lcoe_mid_usd_mwh": wb_lcoe})

    grid_out: dict[str, Any] = {
        "within_boundary_coverage_effective_pct": eff_cov,
        "grid_integration_category": "grid_ready",
    }

    return SiteContext(
        kek=pd.Series({"site_id": "test-site"}),
        site_id="test-site",
        grid_region_id="JAVA_BALI",
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        grid_cost=grid_cost,
        tariff_rate=grid_cost,
        bpp_rate=np.nan,
        emission_factor=0.0,
        post2030_share=1.0,
        grid_upgrade_pre2030=False,
        reliability_req=0.6,
        green_share=0.0,
        max_mwp=0.0,
        wind_cap=0.0,
        wind_cf_best=0.0,
        demand_mwh=0.0,
        solar_gen_mwh=0.0,
        wind_gen_mwh=0.0,
        solar_data_valid=False,
        gc_row=None,
        wb_row=wb_row,
        wind_row=None,
        lcoe_mid=wb_lcoe if wb_lcoe is not None else np.nan,
        primary_cf=0.18,
        gap_pct=np.nan,
        attractive=False,
        gap_vs_tariff_pct=np.nan,
        gap_vs_bpp_pct=np.nan,
        grid_out=grid_out,
    )


def test_delivered_cost_degenerate_full_captive_equals_wb_lcoe():
    """f_captive = 1.0 -> delivered equals wb_LCOE, grid_fraction = 0."""
    ctx = _make_ctx(wb_lcoe=50.0, grid_cost=80.0, eff_cov=1.0)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(50.0)
    assert out["captive_fraction"] == 1.0
    assert out["grid_fraction"] == 0.0
    assert out["delivered_cost_wb_lcoe_used_usd_mwh"] == 50.0
    assert out["delivered_cost_grid_rate_used_usd_mwh"] == 80.0


def test_delivered_cost_fifty_fifty_blend():
    """50% captive @ $40 + 50% grid @ $60 = $50."""
    ctx = _make_ctx(wb_lcoe=40.0, grid_cost=60.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(50.0)
    assert out["captive_fraction"] == 0.5
    assert out["grid_fraction"] == 0.5
    # gap = (50 - 60) / 60 * 100 = -16.67% (delivered cheaper than grid)
    assert out["delivered_cost_gap_vs_grid_pct"] == pytest.approx(-16.67, abs=0.01)


def test_delivered_cost_zero_captive_equals_grid_rate():
    """f_captive = 0 -> delivered equals grid_rate, gap = 0."""
    ctx = _make_ctx(wb_lcoe=50.0, grid_cost=80.0, eff_cov=0.0)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(80.0)
    assert out["captive_fraction"] == 0.0
    assert out["grid_fraction"] == 1.0
    assert out["delivered_cost_gap_vs_grid_pct"] == pytest.approx(0.0, abs=0.01)


def test_delivered_cost_coverage_clamped_to_one():
    """eff_cov > 1.0 -> f_captive clamped to 1.0, delivered equals wb_LCOE."""
    ctx = _make_ctx(wb_lcoe=50.0, grid_cost=80.0, eff_cov=1.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["captive_fraction"] == 1.0
    assert out["grid_fraction"] == 0.0
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(50.0)


def test_delivered_cost_returns_none_when_wb_row_missing():
    """No wb_row -> all six columns None."""
    ctx = _make_ctx(wb_lcoe=None, grid_cost=80.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_blended_usd_mwh"] is None
    assert out["captive_fraction"] is None
    assert out["grid_fraction"] is None
    assert out["delivered_cost_grid_rate_used_usd_mwh"] is None
    assert out["delivered_cost_wb_lcoe_used_usd_mwh"] is None
    assert out["delivered_cost_gap_vs_grid_pct"] is None


def test_delivered_cost_returns_none_when_grid_rate_zero():
    """grid_cost = 0 -> all six columns None (safety-net)."""
    ctx = _make_ctx(wb_lcoe=50.0, grid_cost=0.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_blended_usd_mwh"] is None
    assert out["captive_fraction"] is None
    assert out["delivered_cost_gap_vs_grid_pct"] is None


def test_delivered_cost_with_nan_coverage_treats_as_zero():
    """NaN within_boundary_coverage_effective_pct -> f_captive = 0, delivered = grid_rate."""
    ctx = _make_ctx(wb_lcoe=50.0, grid_cost=80.0, eff_cov=np.nan)
    out = enrich_delivered_cost(ctx, {})
    assert out["captive_fraction"] == 0.0
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(80.0)


def test_delivered_cost_bpp_mode_uses_resolved_grid_cost():
    """Whatever grid_cost the SiteContext resolved (tariff or BPP) is what feeds the blend."""
    # Simulate BPP mode: ctx.grid_cost resolved to a regional BPP (e.g. $55/MWh)
    ctx = _make_ctx(wb_lcoe=40.0, grid_cost=55.0, eff_cov=0.3)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_grid_rate_used_usd_mwh"] == 55.0
    # delivered = 0.3 × 40 + 0.7 × 55 = 12 + 38.5 = 50.5
    assert out["delivered_cost_blended_usd_mwh"] == pytest.approx(50.5)
