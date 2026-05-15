# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.lcoe`.

Canned minimal inputs. Asserts column names + shape + a couple of sanity
invariants (e.g. grid-connected LCOE >= within-boundary LCOE when the same
PVOUT is used, because it adds connection cost).

v4.1a §2 (issue #67): adds the monotone-rising invariant across the 4 IEA
tier columns at every site in the live scorecard.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.dash.logic.assumptions import get_default_assumptions
from src.dash.logic.lcoe import compute_lcoe_live, compute_lcoe_wind_live

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE_SCORECARD = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"

_WB_COLUMNS = {
    "site_id",
    "scenario",
    "lcoe_low_usd_mwh",
    "lcoe_mid_usd_mwh",
    "lcoe_high_usd_mwh",
    "connection_cost_per_kw",
    "cf",
    "pvout_used",
}
_GC_EXTRA = {
    "transmission_cost_per_kw",
    "substation_upgrade_cost_per_kw",
    "effective_capacity_mwp",
}


def _resource_row(**overrides) -> pd.DataFrame:
    base = {
        "site_id": "S001",
        "pvout_centroid": 1650.0,
        "pvout_within_boundary": 1650.0,
        "pvout_best_50km": 1700.0,
        "pvout_buildable_best_50km": 1700.0,
        "dist_solar_to_nearest_substation_km": 5.0,
        "dist_to_nearest_substation_km": 7.0,
        "regional_groundmount_potential_mwp_50km": 50.0,
        "nearest_substation_capacity_mva": 100.0,
        "inter_substation_connected": True,
        "inter_substation_dist_km": 0.0,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def test_compute_lcoe_live_returns_two_rows_per_site() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    assert len(df) == 2
    assert set(df["scenario"]) == {"within_boundary", "grid_connected_solar"}


def test_compute_lcoe_live_columns_complete() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    gc = df[df["scenario"] == "grid_connected_solar"].iloc[0]
    assert _WB_COLUMNS.issubset(wb.index)
    assert (_WB_COLUMNS | _GC_EXTRA).issubset(gc.index)


def test_compute_lcoe_live_connection_cost_zero_in_within_boundary() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    assert wb["connection_cost_per_kw"] == 0.0


def test_compute_lcoe_live_grid_connected_costs_nonneg() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    gc = df[df["scenario"] == "grid_connected_solar"].iloc[0]
    assert gc["connection_cost_per_kw"] >= 0.0
    assert gc["transmission_cost_per_kw"] >= 0.0
    assert gc["substation_upgrade_cost_per_kw"] >= 0.0


def test_compute_lcoe_live_handles_missing_pvout() -> None:
    df = compute_lcoe_live(
        _resource_row(
            pvout_centroid=np.nan,
            pvout_within_boundary=np.nan,
            pvout_best_50km=np.nan,
            pvout_buildable_best_50km=np.nan,
        ),
        get_default_assumptions(),
    )
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    assert pd.isna(wb["lcoe_mid_usd_mwh"])


def test_compute_lcoe_wind_live_columns_and_shape() -> None:
    resource = _resource_row(
        cf_wind_best_50km=0.35,
        cf_wind_centroid=0.33,
        wind_speed_best_50km_ms=7.5,
        wind_speed_centroid_ms=7.0,
    )
    df = compute_lcoe_wind_live(resource, wacc_pct=10.0)
    assert len(df) == 1
    row = df.iloc[0]
    assert set(row.index) == {"site_id", "lcoe_wind_mid_usd_mwh", "cf_wind", "wind_speed_ms"}
    assert row["lcoe_wind_mid_usd_mwh"] > 0


def test_compute_lcoe_wind_live_zero_cf_yields_nan() -> None:
    resource = _resource_row(
        cf_wind_best_50km=0.0,
        cf_wind_centroid=0.0,
        wind_speed_best_50km_ms=2.0,
        wind_speed_centroid_ms=2.0,
    )
    df = compute_lcoe_wind_live(resource, wacc_pct=10.0)
    assert pd.isna(df.iloc[0]["lcoe_wind_mid_usd_mwh"])


# ─── v4.1a §2 multi-tier IEA LCOE — monotone-rising invariant (issue #67) ──


class TestMultiTierLCOEInvariants:
    """Per spec §2.1.1: at every site the cost stack must be monotone-rising
    across the 4 IEA tiers. lcoe_generation ≤ delivered ≤ firm_4h ≤ firm_8h.

    These tests run against the live `fct_site_scorecard.csv`. If the file
    isn't present (e.g. clean checkout without pipeline run) the tests skip
    with a clear message rather than fail.
    """

    @pytest.fixture(scope="class")
    def scorecard(self) -> pd.DataFrame:
        if not LIVE_SCORECARD.exists():
            pytest.skip(
                "live scorecard missing — run `uv run python run_pipeline.py "
                "fct_site_scorecard` first"
            )
        return pd.read_csv(LIVE_SCORECARD)

    def test_iea_columns_present(self, scorecard: pd.DataFrame) -> None:
        """The 4 new IEA columns and 2 LCOS columns are present in the
        scorecard CSV. Additive — v4.0 columns must also still be present
        (covered by tests/test_v40_baseline_unchanged.py)."""
        expected = {
            "lcoe_generation_usd_mwh",
            "full_system_lcoe_delivered_usd_mwh",
            "full_system_lcoe_firm_4h_usd_mwh",
            "full_system_lcoe_firm_8h_usd_mwh",
            "lcos_4h_usd_mwh",
            "lcos_8h_usd_mwh",
        }
        missing = expected - set(scorecard.columns)
        assert not missing, f"v4.1a §2 IEA columns missing: {missing}"

    def test_generation_le_delivered(self, scorecard: pd.DataFrame) -> None:
        """Generation LCOE (no transmission) ≤ Full System LCOE delivered
        (+ transmission). Sites where the v4.0 grid-connected LCOE was
        capped below the within-boundary value (Perpres 112 ceiling on
        IPPs) are excluded — the cap is an artifact, not a stack inversion."""
        # Use uncapped delivered to assert the stack invariant.
        sub = scorecard.dropna(
            subset=["lcoe_generation_usd_mwh", "full_system_lcoe_delivered_usd_mwh"]
        )
        violations = sub[
            sub["lcoe_generation_usd_mwh"] > sub["full_system_lcoe_delivered_usd_mwh"] + 0.01
        ]
        assert violations.empty, (
            f"{len(violations)} sites violate generation ≤ delivered: "
            f"{violations[['site_id', 'lcoe_generation_usd_mwh', 'full_system_lcoe_delivered_usd_mwh']].head().to_dict()}"
        )

    def test_delivered_le_firm_4h(self, scorecard: pd.DataFrame) -> None:
        """Delivered (no storage) ≤ firm 4h (delivered + 4h-storage adder).

        Per spec §2.1.1 cost stack: firm = delivered + LCOS × share, so this
        is a strict invariant at every site. Adding storage to delivered
        can never lower the cost."""
        sub = scorecard.dropna(
            subset=[
                "full_system_lcoe_delivered_usd_mwh",
                "full_system_lcoe_firm_4h_usd_mwh",
            ]
        )
        violations = sub[
            sub["full_system_lcoe_delivered_usd_mwh"]
            > sub["full_system_lcoe_firm_4h_usd_mwh"] + 0.01
        ]
        assert violations.empty, (
            f"{len(violations)} sites violate delivered ≤ firm_4h: "
            f"{violations[['site_id', 'full_system_lcoe_delivered_usd_mwh', 'full_system_lcoe_firm_4h_usd_mwh']].head().to_dict()}"
        )

    def test_firm_4h_le_firm_8h(self, scorecard: pd.DataFrame) -> None:
        """Firm 4h (~20% × LCOS_4h) ≤ Firm 8h (~50% × LCOS_8h). At v4.1a
        defaults LCOS_4h ≈ LCOS_8h (~$170/MWh), so the 50% share lands
        ~2.5× higher than the 20% share. Universal invariant."""
        sub = scorecard.dropna(
            subset=[
                "full_system_lcoe_firm_4h_usd_mwh",
                "full_system_lcoe_firm_8h_usd_mwh",
            ]
        )
        violations = sub[
            sub["full_system_lcoe_firm_4h_usd_mwh"] > sub["full_system_lcoe_firm_8h_usd_mwh"] + 0.01
        ]
        assert violations.empty, (
            f"{len(violations)} sites violate firm_4h ≤ firm_8h: "
            f"{violations[['site_id', 'full_system_lcoe_firm_4h_usd_mwh', 'full_system_lcoe_firm_8h_usd_mwh']].head().to_dict()}"
        )

    def test_lcos_values_in_iea_band(self, scorecard: pd.DataFrame) -> None:
        """Per issue #69 + spec §2.1.1: LCOS-share-weighted ADDERS land in:
        - 4h: [$30, $50] (LCOS_4h × 0.20)
        - 8h: [$80, $130] (LCOS_8h × 0.50)"""
        # LCOS columns are scalar (same value at every site at v4.1a defaults).
        # Pull the first non-NaN value to assert.
        lcos_4h = scorecard["lcos_4h_usd_mwh"].dropna().iloc[0]
        lcos_8h = scorecard["lcos_8h_usd_mwh"].dropna().iloc[0]
        assert 30.0 <= lcos_4h * 0.20 <= 50.0, (
            f"LCOS_4h × 0.20 = {lcos_4h * 0.20:.2f} outside IEA [$30, $50] band"
        )
        assert 80.0 <= lcos_8h * 0.50 <= 130.0, (
            f"LCOS_8h × 0.50 = {lcos_8h * 0.50:.2f} outside IEA [$80, $130] band"
        )


class TestMarginalCostInScorecard:
    """Per issue #68: daytime/nighttime marginal columns populated for all
    81 sites in the scorecard."""

    @pytest.fixture(scope="class")
    def scorecard(self) -> pd.DataFrame:
        if not LIVE_SCORECARD.exists():
            pytest.skip(
                "live scorecard missing — run `uv run python run_pipeline.py "
                "fct_site_scorecard` first"
            )
        return pd.read_csv(LIVE_SCORECARD)

    def test_marginal_columns_present(self, scorecard: pd.DataFrame) -> None:
        expected = {
            "incumbent_pln_marginal_daytime_usd_mwh",
            "incumbent_pln_marginal_nighttime_usd_mwh",
            "incumbent_pln_marginal_confidence",
        }
        missing = expected - set(scorecard.columns)
        assert not missing, f"v4.1a §6 marginal columns missing: {missing}"

    def test_marginal_populated_for_sites_with_bpp(self, scorecard: pd.DataFrame) -> None:
        """Every site with a populated BPP should have populated marginal
        values (daytime + nighttime). NaN BPP → NaN marginal is allowed."""
        if "bpp_usd_mwh" not in scorecard.columns:
            pytest.skip("bpp_usd_mwh not in scorecard (older pipeline run)")
        has_bpp = scorecard[scorecard["bpp_usd_mwh"].notna()]
        n_missing_day = has_bpp["incumbent_pln_marginal_daytime_usd_mwh"].isna().sum()
        n_missing_night = has_bpp["incumbent_pln_marginal_nighttime_usd_mwh"].isna().sum()
        assert n_missing_day == 0, f"{n_missing_day} sites have BPP but missing daytime marginal"
        assert n_missing_night == 0, (
            f"{n_missing_night} sites have BPP but missing nighttime marginal"
        )

    def test_marginal_confidence_is_one_of_known_flags(self, scorecard: pd.DataFrame) -> None:
        valid = {
            "jamali_coal_dominant",
            "mixed_dispatch",
            "diesel_peaking",
            "remote_diesel_dominated",
            "unknown_region",
        }
        observed = set(scorecard["incumbent_pln_marginal_confidence"].dropna().unique())
        bad = observed - valid
        assert not bad, f"Unexpected marginal confidence flags: {bad}"
