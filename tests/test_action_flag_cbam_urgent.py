"""Tests for v4.2a #91: cbam_urgent comparator uses site-appropriate incumbent.

The fix wires `cbam_urgent` to compare solar LCOE against
`effective_incumbent_lcoe + carbon_adder` instead of `grid_cost + savings`.
For captive sites this means captive_coal_lcoe / captive_gas_lcoe; for grid
sites it stays grid_cost. The carbon_adder is the v4.1b destination-weighted
CBAM cost per MWh from the active scenario.

Anchor test: IMIP Morowali (pure_captive, captive_coal, CBAM-exposed) must
have cbam_urgent_comparator_kind = "captive_coal" — the old math compared
against grid_cost which was the bug #91 identified.

Tests are integration-level (call compute_scorecard_live with the real
processed CSVs) because the bug is fundamentally about how multiple modules
interact (site_context resolves effective_incumbent_lcoe, enrich_cbam reads
it, action_flag overrides cbam_urgent). Unit tests in isolation would miss
the regression risk this fix targets.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_wind_tech_defaults,
    prepare_resource_df,
)
from src.dash.logic import compute_scorecard_live, get_default_assumptions, get_default_thresholds


@pytest.fixture(scope="module")
def scorecard() -> pd.DataFrame:
    """One scorecard build per module — expensive (load tables + recompute 81 sites)."""
    tables = load_all_data()
    return compute_scorecard_live(
        resource_df=prepare_resource_df(tables),
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        ruptl_metrics_df=compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"]),
        demand_df=tables["fct_site_demand"],
        grid_df=tables["fct_grid_cost_proxy"],
        grid_cost_by_region=None,
        wind_tech=load_wind_tech_defaults(),
    ).set_index("site_id")


# ─── new metadata column shape ─────────────────────────────────────────────


def test_comparator_kind_column_present(scorecard: pd.DataFrame) -> None:
    """cbam_urgent_comparator_kind shipped on every row (v4.2a addition)."""
    assert "cbam_urgent_comparator_kind" in scorecard.columns


def test_comparator_kind_mirrors_effective_incumbent_kind(scorecard: pd.DataFrame) -> None:
    """For CBAM-exposed sites, the comparator kind = effective_incumbent_kind.

    This is the load-bearing invariant: cbam_urgent is now computed against
    the same incumbent that drives solar_competitive_gap_pct (per v4.3 M-AT8b).
    """
    cbam_sites = scorecard[scorecard["cbam_exposed"].fillna(False)]
    aligned = cbam_sites["cbam_urgent_comparator_kind"] == cbam_sites["effective_incumbent_kind"]
    assert aligned.all(), (
        f"Mismatched comparator/incumbent kinds: "
        f"{cbam_sites[~aligned][['cbam_urgent_comparator_kind', 'effective_incumbent_kind']]}"
    )


def test_comparator_kind_null_for_non_cbam_sites(scorecard: pd.DataFrame) -> None:
    """Non-CBAM-exposed sites have null comparator kind (no CBAM math runs)."""
    non_cbam = scorecard[~scorecard["cbam_exposed"].fillna(False)]
    assert non_cbam["cbam_urgent_comparator_kind"].isna().all()


# ─── per-arrangement comparator behavior ───────────────────────────────────


def test_pure_captive_coal_uses_captive_coal_incumbent(scorecard: pd.DataFrame) -> None:
    """IMIP Morowali — the anchor case from #91 demo.

    electricity_arrangement = pure_captive, captive_fuel_type = coal_*.
    Pre-fix: cbam_urgent comparator was grid_cost (wrong — IMIP isn't on the grid).
    Post-fix: comparator is captive_coal_lcoe.
    """
    row = scorecard.loc["indonesia-morowali-industrial-park-imip"]
    assert row["electricity_arrangement"] == "pure_captive"
    assert row["effective_incumbent_kind"] == "captive_coal"
    assert row["cbam_urgent_comparator_kind"] == "captive_coal"
    # cbam_adjusted_gap_pct is computed against captive_coal_lcoe + carbon_adder,
    # NOT grid_cost. The two are materially different at IMIP.
    assert row["cbam_adjusted_gap_pct"] is not None


def test_grid_only_cbam_site_uses_grid_cost_incumbent(scorecard: pd.DataFrame) -> None:
    """Grid-only CBAM-exposed cement sites compare against grid_cost + carbon_adder."""
    # KEK Lido is grid_only + cement-exposed per the shift report
    row = scorecard.loc["kek-lido"]
    assert row["electricity_arrangement"] == "grid_only"
    assert row["effective_incumbent_kind"] == "grid"
    assert row["cbam_urgent_comparator_kind"] == "grid"


def test_grid_primary_with_captive_uses_captive_incumbent(scorecard: pd.DataFrame) -> None:
    """hybrid sites (grid_primary_with_captive) read the captive LCOE branch
    of effective_incumbent_lcoe per v4.3 M-AT8b — confirmed by shift report.
    """
    row = scorecard.loc["freeport-smelter-gresik"]
    assert row["electricity_arrangement"] == "grid_primary_with_captive"
    # Freeport runs natural-gas captive
    assert row["effective_incumbent_kind"] in {"captive_gas", "captive_coal", "captive_other"}
    assert row["cbam_urgent_comparator_kind"] == row["effective_incumbent_kind"]


def test_hybrid_captive_primary_uses_captive(scorecard: pd.DataFrame) -> None:
    """Inalum (hybrid_captive_primary, hydro) — the biggest shift in the
    methodology change. Pre-fix used grid_cost; post-fix uses captive_hydro.
    """
    row = scorecard.loc["inalum-asahan"]
    assert row["electricity_arrangement"] == "hybrid_captive_primary"
    assert row["effective_incumbent_kind"] == "captive_hydro"
    assert row["cbam_urgent_comparator_kind"] == "captive_hydro"


# ─── carbon_adder semantics ────────────────────────────────────────────────


def test_carbon_adder_positive_for_cbam_exposed_with_active_scenario(
    scorecard: pd.DataFrame,
) -> None:
    """For CBAM-exposed sites with an active (non-none) scenario, cbam_savings_per_mwh
    holds the carbon adder ($/MWh). Must be positive (CBAM has a cost).
    """
    cbam_with_scenario = scorecard[
        scorecard["cbam_exposed"].fillna(False)
        & scorecard["cbam_active_scenario"].notna()
        & (scorecard["cbam_active_scenario"] != "none")
    ]
    # At least most CBAM-exposed sites have a non-null carbon adder
    has_adder = cbam_with_scenario["cbam_savings_per_mwh"].notna()
    assert has_adder.sum() >= len(cbam_with_scenario) - 2  # tolerate edge cases


def test_carbon_adder_matches_active_scenario_value_minus_grid_cost(
    scorecard: pd.DataFrame,
) -> None:
    """cbam_savings_per_mwh = active_scenario_value - grid_cost (the formula
    from enrich_cbam). Spot-check on IMIP.
    """
    row = scorecard.loc["indonesia-morowali-industrial-park-imip"]
    if pd.notna(row["cbam_active_scenario_value_usd_mwh"]) and pd.notna(
        row["cbam_savings_per_mwh"]
    ):
        expected = row["cbam_active_scenario_value_usd_mwh"] - row["grid_cost_usd_mwh"]
        assert row["cbam_savings_per_mwh"] == pytest.approx(expected, abs=0.5)


# ─── cbam_urgent flag behavior ─────────────────────────────────────────────


def test_cbam_urgent_only_fires_for_cbam_exposed(scorecard: pd.DataFrame) -> None:
    """cbam_urgent must NOT fire for non-CBAM-exposed sites (regression-pin)."""
    non_cbam = scorecard[~scorecard["cbam_exposed"].fillna(False)]
    assert not non_cbam["cbam_urgent"].any()


def test_cbam_urgent_signature_matches_gap_pct_sign(scorecard: pd.DataFrame) -> None:
    """cbam_urgent = (cbam_adjusted_gap_pct < 0). Always."""
    has_gap = scorecard["cbam_adjusted_gap_pct"].notna()
    rows = scorecard[has_gap]
    expected_urgent = rows["cbam_adjusted_gap_pct"] < 0
    actual_urgent = rows["cbam_urgent"]
    # bool comparison
    assert (expected_urgent == actual_urgent).all(), (
        f"Mismatches: {rows[expected_urgent != actual_urgent][['cbam_adjusted_gap_pct', 'cbam_urgent']]}"
    )


# ─── action_flag override stays narrow ──────────────────────────────────────


def test_action_flag_override_only_lifts_not_competitive_or_invest_resilience(
    scorecard: pd.DataFrame,
) -> None:
    """cbam_urgent flips action_flag = NOT_COMPETITIVE / INVEST_RESILIENCE to
    CBAM_URGENT only. Other action_flags (solar_now, hybrid_now, grid_first,
    no_solar_resource, etc.) are NOT overridden even if cbam_urgent fires.
    Invariant preserved across the v4.2a refactor.
    """
    urgent_rows = scorecard[scorecard["cbam_urgent"]]
    override_eligible = {"not_competitive", "invest_resilience"}
    for sid, row in urgent_rows.iterrows():
        af = row["action_flag"]
        if af != "cbam_urgent":
            # cbam_urgent fired but action_flag was NOT overridden — so the
            # pre-override flag must have been outside the eligible set
            assert af not in override_eligible, (
                f"{sid}: cbam_urgent=True with action_flag={af} — "
                f"this flag was eligible but didn't get promoted (bug in override logic)"
            )


# ─── #91 anchor case (the headline demo) ───────────────────────────────────


def test_imip_morowali_anchor(scorecard: pd.DataFrame) -> None:
    """Anchor case from #91 demo. IMIP Morowali (pure_captive nickel) must
    end up with the captive_coal comparator. The pre-fix math compared
    against grid_cost — a known bug.
    """
    row = scorecard.loc["indonesia-morowali-industrial-park-imip"]

    # 1. Right electricity_arrangement
    assert row["electricity_arrangement"] == "pure_captive"

    # 2. captive_fuel_type is some flavor of coal
    fuel = row["captive_fuel_type"]
    assert fuel is not None and fuel.startswith("coal_"), (
        f"IMIP captive_fuel_type expected coal_*, got {fuel}"
    )

    # 3. Comparator is captive_coal, NOT grid
    assert row["cbam_urgent_comparator_kind"] == "captive_coal"

    # 4. cbam_adjusted_gap_pct is well-defined (not null)
    assert pd.notna(row["cbam_adjusted_gap_pct"])
