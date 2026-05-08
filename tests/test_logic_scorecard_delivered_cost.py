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
    disp_re_cov: float | None = None,  # F1: dispatchable RE coverage (geothermal/hydro)
    disp_re_lcoe: float | None = None,  # F1: dispatchable RE LCOE
) -> SiteContext:
    """Construct a minimal SiteContext with only the fields the enricher reads."""
    wb_row = pd.Series({"lcoe_mid_usd_mwh": wb_lcoe}) if wb_lcoe is not None else None
    gc_row = pd.Series({"lcoe_mid_usd_mwh": gc_lcoe}) if gc_lcoe is not None else None

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
        dispatchable_re_coverage_pct=disp_re_cov if disp_re_cov is not None else 0.0,
        dispatchable_re_lcoe_usd_mwh=disp_re_lcoe,
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


# ─── F1: dispatchable RE layer tests (2026-05-07) ───────────────────────────


def test_f1_no_dispatchable_re_data_preserves_v40_cascade():
    """When dispatchable_re columns don't exist, cascade behaves bit-identically to v4.0.

    Critical invariant: F1 ships the structural layer in v4.0.5 BEFORE F2 populates the
    underlying data. Sites with no dispatchable_re_coverage_pct must produce the exact
    same delivered_cost as the pre-F1 cascade.
    """
    ctx = _make_ctx(wb_lcoe=40.0, gc_lcoe=60.0, grid_cost=80.0, eff_cov=0.2)
    out = enrich_delivered_cost(ctx, {})

    # No dispatchable_re fraction surfaced when columns are absent
    assert out["delivered_cost_dispatchable_re_fraction"] is None
    assert out["delivered_cost_dispatchable_re_lcoe_used_usd_mwh"] is None
    # Cascade matches the original v4.0 three-layer formula exactly
    expected = 0.2 * 40.0 + (DAYTIME_CAP - 0.2) * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_f1_dispatchable_re_fills_overnight_gap():
    """Dispatchable RE (geothermal-style 24h) reduces grid backfill, not solar share."""
    # Site has 30% wb solar, 50% dispatchable RE coverage at $90/MWh, grid at $120/MWh.
    # Geothermal runs 24h, so it competes for both daytime and overnight demand.
    ctx = _make_ctx(
        wb_lcoe=40.0,
        gc_lcoe=None,  # no remote IPP, simplifies the math
        grid_cost=120.0,
        eff_cov=0.30,
        disp_re_cov=0.50,
        disp_re_lcoe=90.0,
    )
    out = enrich_delivered_cost(ctx, {})

    # Layer 1: f_wb = min(0.30, daytime_cap) = 0.30 (below cap)
    # Layer 2: f_disp_re = min(0.50, 1 - 0.30) = 0.50
    # Layer 4: f_grid = 1 - 0.30 - 0.50 = 0.20 (overnight + un-siteable)
    assert out["captive_fraction"] == pytest.approx(0.30, abs=1e-4)
    assert out["delivered_cost_dispatchable_re_fraction"] == pytest.approx(0.50, abs=1e-4)
    assert out["delivered_cost_dispatchable_re_lcoe_used_usd_mwh"] == 90.0
    assert out["grid_fraction"] == pytest.approx(0.20, abs=1e-4)

    expected = 0.30 * 40.0 + 0.50 * 90.0 + 0.20 * 120.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)


def test_f1_dispatchable_re_capped_by_remaining_demand():
    """If wb covers a lot, dispatchable_re is capped at remaining demand."""
    # Site has 40% wb (near daytime cap), 70% disp_re *available* but only 60% room left.
    ctx = _make_ctx(
        wb_lcoe=50.0,
        gc_lcoe=None,
        grid_cost=110.0,
        eff_cov=0.40,
        disp_re_cov=0.70,  # would over-fill if not capped
        disp_re_lcoe=85.0,
    )
    out = enrich_delivered_cost(ctx, {})

    # Layer 2 cap: f_disp_re = min(0.70, 1 - 0.40) = 0.60
    assert out["delivered_cost_dispatchable_re_fraction"] == pytest.approx(0.60, abs=1e-4)
    # Total wb + disp_re = 1.0 → no grid
    assert out["grid_fraction"] == pytest.approx(0.0, abs=1e-4)


def test_f1_dispatchable_re_with_remote_ipp_competes_for_daytime():
    """When remote IPP also exists, disp_re's daytime share competes with remote solar."""
    # f_wb = 0.20, disp_re = 0.30 (24h) → disp_re_daytime_share = 0.30 × 0.4167 ≈ 0.125
    # daytime_headroom = 0.4167 - 0.20 - 0.125 ≈ 0.092 → f_remote = 0.092
    # f_grid = 1 - 0.20 - 0.30 - 0.092 ≈ 0.408
    ctx = _make_ctx(
        wb_lcoe=40.0,
        gc_lcoe=55.0,  # remote IPP available
        grid_cost=100.0,
        eff_cov=0.20,
        disp_re_cov=0.30,
        disp_re_lcoe=80.0,
    )
    out = enrich_delivered_cost(ctx, {})

    expected_disp_daytime = 0.30 * DAYTIME_CAP
    expected_remote = max(DAYTIME_CAP - 0.20 - expected_disp_daytime, 0.0)
    expected_grid = 1.0 - 0.20 - 0.30 - expected_remote

    assert out["captive_fraction"] == pytest.approx(0.20, abs=1e-4)
    assert out["delivered_cost_dispatchable_re_fraction"] == pytest.approx(0.30, abs=1e-4)
    assert out["delivered_cost_remote_fraction"] == pytest.approx(expected_remote, abs=1e-4)
    assert out["grid_fraction"] == pytest.approx(expected_grid, abs=1e-4)

    expected_total = 0.20 * 40.0 + 0.30 * 80.0 + expected_remote * 55.0 + expected_grid * 100.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected_total, abs=0.01)


def test_f1_dispatchable_re_lcoe_only_no_coverage_is_no_op():
    """Coverage column missing/zero -> layer stays a no-op even if LCOE is present."""
    ctx = _make_ctx(
        wb_lcoe=40.0,
        gc_lcoe=60.0,
        grid_cost=80.0,
        eff_cov=0.2,
        disp_re_cov=0.0,  # explicit zero
        disp_re_lcoe=85.0,
    )
    out = enrich_delivered_cost(ctx, {})

    # Layer is no-op when coverage is 0
    assert out["delivered_cost_dispatchable_re_fraction"] is None
    # Cascade matches v4.0 three-layer
    expected = 0.2 * 40.0 + (DAYTIME_CAP - 0.2) * 60.0 + (1 - DAYTIME_CAP) * 80.0
    assert out["delivered_cost_usd_mwh"] == pytest.approx(expected, abs=0.01)
