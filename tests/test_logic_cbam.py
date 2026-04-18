# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.cbam`.

Covers the 3-signal vs direct detection dispatch, type normalization, and the
CBAM cost-trajectory aggregator. These tests are intentionally shallow — the
scorecard-level behaviour is covered by the golden-master fixture.
"""

from __future__ import annotations

import pandas as pd

from src.dash.logic.cbam import _detect_cbam_types, _normalize_cbam_type, compute_cbam_trajectory


def test_normalize_cbam_iron_steel_dispatches_on_technology() -> None:
    assert _normalize_cbam_type("iron_steel", "RKEF") == "nickel_rkef"
    assert _normalize_cbam_type("iron_steel", "BF-BOF") == "steel_bfbof"
    assert _normalize_cbam_type("iron_steel", "EAF") == "steel_eaf"
    assert _normalize_cbam_type("iron_steel", "") == "steel_eaf"


def test_normalize_cbam_passthrough_for_other_types() -> None:
    assert _normalize_cbam_type("cement", "") == "cement"
    assert _normalize_cbam_type("aluminium", "") == "aluminium"
    assert _normalize_cbam_type("", "") is None


def test_detect_cbam_direct_mode_reads_dim_sites_column() -> None:
    kek = pd.Series(
        {
            "site_type": "standalone",
            "cbam_product_type": "cement",
            "technology": "",
        }
    )
    assert _detect_cbam_types(kek, {}) == ["cement"]


def test_detect_cbam_direct_mode_handles_comma_list() -> None:
    kek = pd.Series(
        {
            "site_type": "cluster",
            "cbam_product_type": "iron_steel,cement",
            "technology": "RKEF",
        }
    )
    assert _detect_cbam_types(kek, {}) == ["nickel_rkef", "cement"]


def test_detect_cbam_direct_mode_empty_returns_empty() -> None:
    kek = pd.Series({"site_type": "standalone", "cbam_product_type": "", "technology": ""})
    assert _detect_cbam_types(kek, {}) == []


def test_detect_cbam_kek_3signal_uses_process() -> None:
    kek = pd.Series(
        {
            "site_type": "kek",
            "steel_plant_count": 0,
            "cement_plant_count": 0,
            "business_sectors": "",
        }
    )
    row = {"dominant_process_type": "Nickel Pig Iron"}
    assert _detect_cbam_types(kek, row) == ["nickel_rkef"]


def test_detect_cbam_kek_3signal_combines_signals() -> None:
    kek = pd.Series(
        {
            "site_type": "kek",
            "steel_plant_count": 1,
            "steel_dominant_technology": "BF-BOF",
            "cement_plant_count": 1,
            "business_sectors": "Bauxite Industry",
        }
    )
    row = {"dominant_process_type": ""}
    result = _detect_cbam_types(kek, row)
    assert "steel_bfbof" in result
    assert "cement" in result
    assert "aluminium" in result


def test_compute_cbam_trajectory_empty_types() -> None:
    out = compute_cbam_trajectory([], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08)
    assert out["cbam_exposed"] is False
    assert out["cbam_product_type"] is None
    for year in (2026, 2030, 2034):
        assert out[f"cbam_cost_{year}_usd_per_tonne"] is None


def test_compute_cbam_trajectory_returns_full_year_set() -> None:
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08
    )
    assert out["cbam_exposed"] is True
    assert out["cbam_product_type"] == "cement"
    assert "cement" in out["cbam_per_product"]
    for year in (2026, 2030, 2034):
        assert out[f"cbam_cost_{year}_usd_per_tonne"] is not None
        assert out[f"cbam_savings_{year}_usd_per_tonne"] is not None


def test_compute_cbam_trajectory_cost_monotone_increasing_2026_to_2034() -> None:
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08
    )
    assert out["cbam_cost_2026_usd_per_tonne"] <= out["cbam_cost_2030_usd_per_tonne"]
    assert out["cbam_cost_2030_usd_per_tonne"] <= out["cbam_cost_2034_usd_per_tonne"]


def test_detect_cbam_direct_mode_ammonia() -> None:
    """Standalone merchant ammonia plant dispatches to the 'ammonia' cost key."""
    kek = pd.Series(
        {
            "site_type": "standalone",
            "cbam_product_type": "ammonia",
            "technology": "Haber-Bosch",
        }
    )
    assert _detect_cbam_types(kek, {}) == ["ammonia"]


def test_compute_cbam_trajectory_ammonia_uses_indonesia_scope1() -> None:
    """Ammonia Scope 1 = 2.3 tCO2/t Indonesia (ICGD) must flow into cost trajectory."""
    out = compute_cbam_trajectory(
        ["ammonia"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["cbam_exposed"] is True
    assert out["cbam_product_type"] == "ammonia"
    # emission_intensity_solar is pure Scope 1 after switching to RE (no grid Scope 2).
    # 2.3 tCO2/t (rounded) — Indonesia gas-SMR route.
    assert out["cbam_emission_intensity_solar"] == 2.3
    # Current intensity = Scope 1 (2.3) + Scope 2 (elec × grid) = 2.3 + 10.0 × 0.8 = 10.3 tCO2/t
    assert out["cbam_emission_intensity_current"] == 10.3
    # 2034 cost should be > 0 (free allocation = 0)
    assert out["cbam_cost_2034_usd_per_tonne"] > 0


def test_detect_cbam_petrochemical_is_not_exposed() -> None:
    """Petrochemical rows carry an empty cbam_product_type → not CBAM-exposed."""
    kek = pd.Series(
        {
            "site_type": "standalone",
            "cbam_product_type": "",
            "technology": "Steam Cracker",
        }
    )
    assert _detect_cbam_types(kek, {}) == []


# ── M30: RE-addressable fraction ─────────────────────────────────────────────
# CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE is thermal-inclusive for cement /
# fertilizer / ammonia. Scope 2 savings must be multiplied by the sector
# RE-addressable fraction so cost relief reflects only electric share.
# See docs/cbam_sector_data_collection_plan.md §4.1.


def test_cement_savings_use_re_addressable_fraction() -> None:
    """Cement RE savings ≈ 12% of naive Scope 2 savings (fraction = 0.12)."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # Naive Scope 2 (without fraction) at 2034 (free alloc = 0):
    #   elec_intensity × grid_ef × (price_eur × fx)
    #   = 0.9 × 0.8 × (80 × 1.10) = 63.36 USD/t
    # Post-fix: × 0.12 → ~7.60 USD/t
    savings_2034 = out["cbam_savings_2034_usd_per_tonne"]
    assert 7 <= savings_2034 <= 9, f"cement 2034 savings {savings_2034} out of expected ~7.6 range"


def test_nickel_savings_unchanged_by_fraction() -> None:
    """Nickel RKEF fraction = 1.0 → savings equal full Scope 2 (no reduction)."""
    out = compute_cbam_trajectory(
        ["nickel_rkef"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # 37.5 MWh/t × 0.8 tCO2/MWh × 80 × 1.10 = 2640 USD/t at 2034
    savings_2034 = out["cbam_savings_2034_usd_per_tonne"]
    assert 2600 <= savings_2034 <= 2680


def test_ammonia_savings_use_re_addressable_fraction() -> None:
    """Ammonia fraction = 0.10 → savings ≈ 10% of naive Scope 2."""
    out = compute_cbam_trajectory(
        ["ammonia"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # Naive: 10.0 × 0.8 × 80 × 1.10 = 704 USD/t; post-fix × 0.10 = 70.4 USD/t
    savings_2034 = out["cbam_savings_2034_usd_per_tonne"]
    assert 65 <= savings_2034 <= 75


def test_cost_unchanged_by_re_fraction() -> None:
    """Total CBAM cost (Scope 1 + Scope 2) is NOT affected by re_fraction — only savings are."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # Total EI = Scope 1 (0.52) + Scope 2 (0.9 × 0.8 = 0.72) = 1.24 tCO2/t
    # Cost 2034 = 1.24 × 80 × 1.10 = 109.12 USD/t
    cost_2034 = out["cbam_cost_2034_usd_per_tonne"]
    assert 105 <= cost_2034 <= 115
