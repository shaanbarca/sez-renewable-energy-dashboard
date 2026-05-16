"""v4.3 M-AT8b regression: competitive gap for captive sites is computed against
captive_incumbent_lcoe, NOT grid_cost.

This is the user-facing payoff of M-AT8a: IMIP solar gets compared to its actual
incumbent ($50 captive coal at DMO pricing), not the PLN grid tariff (~$70).
The gap signal that lands in the score drawer must reflect that.

If this test fails, the most likely cause is `src/dash/logic/site_context.py`
losing the `use_captive` branch — the gap_pct reverted to `solar_competitive_gap(
lcoe, grid_cost)`. Fix: restore the effective_incumbent_lcoe + electricity_arrangement
gating, see methodology §13.10.
"""

from __future__ import annotations

import pytest

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_wind_tech_defaults,
    prepare_resource_df,
)
from src.dash.logic import get_default_assumptions, get_default_thresholds
from src.dash.logic.scorecard import compute_scorecard_live


@pytest.fixture(scope="module")
def live_scorecard():
    tables = load_all_data()
    return compute_scorecard_live(
        resource_df=prepare_resource_df(tables),
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        ruptl_metrics_df=compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"]),
        demand_df=tables["fct_site_demand"],
        grid_df=tables["fct_grid_cost_proxy"],
        wind_tech=load_wind_tech_defaults(),
    )


def _row(df, site_id: str):
    matches = df[df["site_id"] == site_id]
    assert len(matches) == 1, f"expected exactly one row for {site_id}, got {len(matches)}"
    return matches.iloc[0]


# ─── pure_captive ──────────────────────────────────────────────────────────


def test_imip_gap_uses_captive_coal_not_grid_tariff(live_scorecard):
    """IMIP is `pure_captive` with `coal_subcritical` (T1 anchor at $50/MWh).
    The competitive gap must be computed against $50, not against grid_cost."""
    row = _row(live_scorecard, "indonesia-morowali-industrial-park-imip")
    assert row["electricity_arrangement"] == "pure_captive"
    assert row["captive_fuel_type"] == "coal_subcritical"
    assert row["effective_incumbent_lcoe_usd_mwh"] == pytest.approx(50.0, abs=0.5), (
        f"IMIP effective incumbent expected $50 (T1 captive coal), got "
        f"${row['effective_incumbent_lcoe_usd_mwh']}/MWh"
    )
    assert row["effective_incumbent_kind"] == "captive_coal"
    # Gap must be strictly larger than the gap-vs-grid (captive coal $50 < grid $70).
    assert row["solar_competitive_gap_pct"] > row["gap_vs_grid_pct"], (
        f"IMIP captive coal ($50) is cheaper than grid ($70+), so the gap to "
        f"captive should be LARGER than gap-vs-grid. "
        f"gap={row['solar_competitive_gap_pct']}, gap_vs_grid={row['gap_vs_grid_pct']}"
    )


def test_pupuk_kaltim_gap_uses_hgbt_gas_not_grid_tariff(live_scorecard):
    """Pupuk Kaltim Bontang is `pure_captive` with `natural_gas` (T1 HGBT $50)."""
    row = _row(live_scorecard, "pupuk-kaltim-bontang")
    assert row["electricity_arrangement"] == "pure_captive"
    assert row["captive_fuel_type"] == "natural_gas"
    assert row["effective_incumbent_lcoe_usd_mwh"] == pytest.approx(50.0, abs=0.5)
    assert row["effective_incumbent_kind"] == "captive_gas"
    assert row["captive_lcoe_tier"] == "T1"


def test_inalum_gap_uses_hydro_30(live_scorecard):
    """Inalum is `hybrid_captive_primary` with `hydro` (T1 anchor at $30/MWh).
    Hydro is scenario-invariant — fuel-price scenarios don't apply."""
    row = _row(live_scorecard, "inalum-asahan")
    assert row["captive_fuel_type"] == "hydro"
    assert row["effective_incumbent_lcoe_usd_mwh"] == pytest.approx(30.0, abs=0.5)
    assert row["effective_incumbent_kind"] == "captive_hydro"
    assert row["captive_lcoe_tier"] == "T1"


# ─── grid_only (control case — no regression) ──────────────────────────────


def test_grid_only_site_gap_unchanged(live_scorecard):
    """KEK Kendal is `grid_only` — the competitive gap should match
    gap_vs_grid_pct exactly (no captive incumbent in play)."""
    row = _row(live_scorecard, "kek-kendal")
    assert row["electricity_arrangement"] == "grid_only"
    assert row["effective_incumbent_kind"] == "grid"
    # Effective incumbent equals grid_cost; gap equals gap_vs_grid.
    assert row["effective_incumbent_lcoe_usd_mwh"] == pytest.approx(
        row["grid_cost_usd_mwh"], abs=0.5
    )
    assert row["solar_competitive_gap_pct"] == pytest.approx(row["gap_vs_grid_pct"], abs=0.5)


# ─── hybrid (Krakatau Posco) ──────────────────────────────────────────────


def test_krakatau_posco_hybrid_uses_captive_coal(live_scorecard):
    """Krakatau Posco is `grid_primary_with_captive` with `coal_supercritical`
    (T1 anchor at $62/MWh). M-AT8b decision: hybrid sites use captive as
    primary comparator, with grid shown as a secondary reference row in the UI."""
    row = _row(live_scorecard, "krakatau-posco-cilegon")
    assert row["captive_fuel_type"] == "coal_supercritical"
    assert row["effective_incumbent_lcoe_usd_mwh"] == pytest.approx(62.0, abs=0.5)
    assert row["effective_incumbent_kind"] == "captive_coal"
    assert row["captive_lcoe_tier"] == "T1"
    # gap_vs_grid is still surfaced for hybrid sites' secondary comparator.
    assert row["gap_vs_grid_pct"] is not None
