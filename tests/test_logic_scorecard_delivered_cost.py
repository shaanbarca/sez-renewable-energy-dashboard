"""Tests for `enrich_delivered_cost` — METHODOLOGY §5.4 cascaded delivered cost.

Unit-tests the enricher in isolation by constructing minimal `SiteContext`
instances. Does not go through `compute_scorecard_live`.

The V3.11 cascade is:
    f_wb     = min(wb_coverage, daytime_cap)
    f_remote = (daytime_cap - f_wb) if gc_row exists else 0
    f_grid   = 1 - f_wb - f_remote
    delivered = f_wb × wb_LCOE + f_remote × gc_LCOE + f_grid × grid_rate
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.assumptions import SOLAR_PRODUCTION_HOURS
from src.dash.logic.assumptions import get_default_assumptions, get_default_thresholds
from src.dash.logic.scorecard import enrich_delivered_cost
from src.dash.logic.site_context import SiteContext


def _make_ctx(
    *,
    wb_lcoe: float | None = 50.0,
    gc_lcoe: float | None = 65.0,
    grid_cost: float = 80.0,
    eff_cov: float | None = 0.5,
) -> SiteContext:
    """Construct a minimal SiteContext with only the fields the enricher reads."""
    wb_row = None if wb_lcoe is None else pd.Series({"lcoe_mid_usd_mwh": wb_lcoe})
    gc_row = None if gc_lcoe is None else pd.Series({"lcoe_mid_usd_mwh": gc_lcoe})

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
        gc_row=gc_row,
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


DAYTIME_CAP = SOLAR_PRODUCTION_HOURS / 24.0  # 10/24 ≈ 0.4167


def test_cascade_three_layer_blend():
    """Undersized WB + gc_row present -> WB fills f_wb, remote fills headroom, grid rest."""
    ctx = _make_ctx(wb_lcoe=40.0, gc_lcoe=60.0, grid_cost=80.0, eff_cov=0.2)
    out = enrich_delivered_cost(ctx, {})

    # f_wb = 0.2 (below cap), f_remote fills headroom to daytime_cap, grid = 1 - cap
    assert out["captive_fraction"] == pytest.approx(0.2, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(DAYTIME_CAP - 0.2, abs=1e-4)
    assert out["grid_fraction"] == pytest.approx(1 - DAYTIME_CAP, abs=1e-4)

    expected = 0.2 * 40.0 + (DAYTIME_CAP - 0.2) * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)
    assert out["delivered_cost_gc_lcoe_used_usd_mwh"] == 60.0


def test_cascade_wb_at_or_above_cap_no_remote():
    """WB coverage alone hits daytime cap -> no headroom for remote."""
    ctx = _make_ctx(wb_lcoe=50.0, gc_lcoe=70.0, grid_cost=80.0, eff_cov=1.0)
    out = enrich_delivered_cost(ctx, {})

    assert out["captive_fraction"] == pytest.approx(DAYTIME_CAP, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(0.0, abs=1e-4)
    assert out["grid_fraction"] == pytest.approx(1 - DAYTIME_CAP, abs=1e-4)

    expected = DAYTIME_CAP * 50.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_cascade_no_wb_row_remote_only():
    """wb_row missing but gc_row present -> remote captive fills daytime, grid rest."""
    ctx = _make_ctx(wb_lcoe=None, gc_lcoe=60.0, grid_cost=80.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})

    assert out["captive_fraction"] == pytest.approx(0.0, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(DAYTIME_CAP, abs=1e-4)
    assert out["grid_fraction"] == pytest.approx(1 - DAYTIME_CAP, abs=1e-4)

    expected = DAYTIME_CAP * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)
    assert out["delivered_cost_wb_lcoe_used_usd_mwh"] is None
    assert out["delivered_cost_gc_lcoe_used_usd_mwh"] == 60.0


def test_cascade_no_gc_row_wb_plus_grid_only():
    """gc_row missing -> no remote layer; matches the pre-V3.11 2-way behavior."""
    ctx = _make_ctx(wb_lcoe=40.0, gc_lcoe=None, grid_cost=60.0, eff_cov=0.2)
    out = enrich_delivered_cost(ctx, {})

    assert out["captive_fraction"] == pytest.approx(0.2, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(0.0, abs=1e-4)
    assert out["grid_fraction"] == pytest.approx(0.8, abs=1e-4)

    expected = 0.2 * 40.0 + 0.8 * 60.0  # 8 + 48 = 56
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)
    assert out["delivered_cost_gc_lcoe_used_usd_mwh"] is None


def test_cascade_zero_wb_coverage_remote_fills_cap():
    """eff_cov = 0 but gc_row present -> remote captive fills daytime cap alone."""
    ctx = _make_ctx(wb_lcoe=50.0, gc_lcoe=60.0, grid_cost=80.0, eff_cov=0.0)
    out = enrich_delivered_cost(ctx, {})

    assert out["captive_fraction"] == pytest.approx(0.0, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(DAYTIME_CAP, abs=1e-4)
    expected = DAYTIME_CAP * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_cascade_clamps_oversized_wb_coverage():
    """eff_cov > daytime_cap -> f_wb clamped to cap, no remote, no negative headroom."""
    ctx = _make_ctx(wb_lcoe=50.0, gc_lcoe=60.0, grid_cost=80.0, eff_cov=1.5)
    out = enrich_delivered_cost(ctx, {})

    assert out["captive_fraction"] == pytest.approx(DAYTIME_CAP, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(0.0, abs=1e-4)
    expected = DAYTIME_CAP * 50.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_cascade_returns_none_when_no_solar_siting():
    """Both wb_row and gc_row missing -> all cascade columns null."""
    ctx = _make_ctx(wb_lcoe=None, gc_lcoe=None, grid_cost=80.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_usd_mwh"] is None
    assert out["captive_fraction"] is None
    assert out["delivered_cost_remote_fraction"] is None
    assert out["grid_fraction"] is None
    assert out["delivered_cost_grid_rate_used_usd_mwh"] is None
    assert out["delivered_cost_wb_lcoe_used_usd_mwh"] is None
    assert out["delivered_cost_gc_lcoe_used_usd_mwh"] is None
    assert out["delivered_cost_gap_vs_grid_pct"] is None


def test_cascade_returns_none_when_grid_rate_zero():
    """grid_cost = 0 -> all cascade columns null (safety-net)."""
    ctx = _make_ctx(wb_lcoe=50.0, gc_lcoe=60.0, grid_cost=0.0, eff_cov=0.5)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_usd_mwh"] is None
    assert out["captive_fraction"] is None
    assert out["delivered_cost_remote_fraction"] is None
    assert out["delivered_cost_gap_vs_grid_pct"] is None


def test_cascade_with_nan_coverage_treats_as_zero():
    """NaN eff_cov + gc_row present -> f_wb = 0, remote fills cap."""
    ctx = _make_ctx(wb_lcoe=50.0, gc_lcoe=60.0, grid_cost=80.0, eff_cov=np.nan)
    out = enrich_delivered_cost(ctx, {})
    assert out["captive_fraction"] == pytest.approx(0.0, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(DAYTIME_CAP, abs=1e-4)
    expected = DAYTIME_CAP * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_cascade_bpp_mode_uses_resolved_grid_cost():
    """Whatever grid_cost the SiteContext resolved (tariff or BPP) feeds the blend."""
    # BPP mode: ctx.grid_cost resolved to a regional BPP (e.g. $55/MWh), no gc_row
    ctx = _make_ctx(wb_lcoe=40.0, gc_lcoe=None, grid_cost=55.0, eff_cov=0.3)
    out = enrich_delivered_cost(ctx, {})
    assert out["delivered_cost_grid_rate_used_usd_mwh"] == 55.0
    # delivered = 0.3 × 40 + 0.7 × 55 = 12 + 38.5 = 50.5
    assert out["delivered_cost_usd_mwh"] == pytest.approx(50.5)
