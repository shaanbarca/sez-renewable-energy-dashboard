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


# ─── F9 (2026-05-07): Scope 1 abatement pathway flags ───────────────────────


def test_f9_cement_has_alt_fuels_pathway() -> None:
    """Cement: alt fuels + SCM + electric kiln, ~30% additional Scope 1 addressable."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert "alt_fuels" in out["scope1_abatement_pathways"]
    assert "scm_substitution" in out["scope1_abatement_pathways"]
    assert "electric_kiln" in out["scope1_abatement_pathways"]
    assert out["scope1_abatement_indicative_addressable_pct"] == 0.30
    assert "Indicative" in out["scope1_abatement_methodology_note"]


def test_f9_ammonia_has_green_h2_pathway() -> None:
    """Ammonia: green-H2 SMR retrofit, ~50% additional Scope 1 addressable."""
    out = compute_cbam_trajectory(
        ["ammonia"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["scope1_abatement_pathways"] == "green_h2_smr"
    assert out["scope1_abatement_indicative_addressable_pct"] == 0.50


def test_f9_steel_bfbof_has_hydrogen_dri_pathway() -> None:
    """Steel BF-BOF: hydrogen DRI + scrap substitution, ~70% additional addressable."""
    out = compute_cbam_trajectory(
        ["steel_bfbof"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert "hydrogen_dri" in out["scope1_abatement_pathways"]
    assert "scrap_substitution" in out["scope1_abatement_pathways"]
    assert out["scope1_abatement_indicative_addressable_pct"] == 0.70


def test_f9_nickel_rkef_has_no_pathway() -> None:
    """Nickel RKEF: process chemistry can't be electrified — no Scope 1 abatement."""
    out = compute_cbam_trajectory(
        ["nickel_rkef"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["scope1_abatement_pathways"] is None
    assert out["scope1_abatement_indicative_addressable_pct"] is None
    assert out["scope1_abatement_methodology_note"] is None


def test_f9_no_cbam_exposure_no_abatement_flags() -> None:
    """Empty cbam_types → all Scope 1 abatement fields null."""
    out = compute_cbam_trajectory([], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10)
    assert out["scope1_abatement_pathways"] is None
    assert out["scope1_abatement_indicative_addressable_pct"] is None
    assert out["scope1_abatement_methodology_note"] is None


def test_f9_methodology_note_is_explicit_about_indicative_status() -> None:
    """Methodology note must signal that pathway availability is qualitative."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    note = out["scope1_abatement_methodology_note"]
    assert note is not None
    assert "Indicative" in note
    assert "deferred" in note.lower()


# ─── #63 (v4.0.7) — CBAM Scope 2 sectoral pricing per EU Reg 2025/2547 ─────────


def test_scope_2_priced_flag_true_for_cement() -> None:
    """EU Implementing Reg 2025/2547: cement prices both Scope 1 and Scope 2 in
    the initial definitive phase."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["cbam_scope_2_priced"] is True


def test_scope_2_priced_flag_true_for_fertilizer_and_ammonia() -> None:
    out_f = compute_cbam_trajectory(
        ["fertilizer"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    out_a = compute_cbam_trajectory(
        ["ammonia"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out_f["cbam_scope_2_priced"] is True
    assert out_a["cbam_scope_2_priced"] is True


def test_scope_2_priced_flag_false_for_aluminium() -> None:
    """EU Implementing Reg 2025/2547: aluminium prices Scope 1 only in initial
    phase. Scope 2 is reported but not in the CBAM bill."""
    out = compute_cbam_trajectory(
        ["aluminium"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["cbam_scope_2_priced"] is False


def test_scope_2_priced_flag_false_for_steel_eaf_and_bfbof() -> None:
    out_eaf = compute_cbam_trajectory(
        ["steel_eaf"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    out_bfbof = compute_cbam_trajectory(
        ["steel_bfbof"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out_eaf["cbam_scope_2_priced"] is False
    assert out_bfbof["cbam_scope_2_priced"] is False


def test_aluminium_re_savings_are_zero_under_current_rules() -> None:
    """Core regression for #63 / refinement Finding 1. Pre-v4.0.7 the dashboard
    showed aluminium RE-switching saving the full Scope 2 × CBAM rate (~$500/t
    by 2030). Under EU Reg 2025/2547 those savings are not creditable until the
    EU extends Scope 2 — RE-addressable savings must be exactly zero."""
    out = compute_cbam_trajectory(
        ["aluminium"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["cbam_savings_2026_usd_per_tonne"] == 0.0
    assert out["cbam_savings_2030_usd_per_tonne"] == 0.0
    assert out["cbam_savings_2034_usd_per_tonne"] == 0.0


def test_steel_eaf_re_savings_are_zero_under_current_rules() -> None:
    out = compute_cbam_trajectory(
        ["steel_eaf"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    assert out["cbam_savings_2030_usd_per_tonne"] == 0.0


def test_cement_re_savings_remain_positive_under_current_rules() -> None:
    """Scope-2-priced sectors keep their CBAM savings. The fix must not regress
    the cement / fertilizer / ammonia signal."""
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # Cement is 12% RE-addressable on 0.9 MWh/t * 0.8 t/MWh * $88 * (1-0.485)
    # ≈ $3.9 — must be positive, not silently zero.
    assert out["cbam_savings_2030_usd_per_tonne"] > 0


def test_aluminium_cost_drops_when_scope_2_not_priced() -> None:
    """Cost calculation must use Scope 1 only for aluminium. With Scope 1 = 1.5
    tCO2/t (anode consumption) and the 2030 effective rate $88 × 1.10 × (1 −
    0.485) ≈ $43.32/t, aluminium 2030 cost should be ≈ $65, not the previous
    1.5 + 12.0 = 13.5 × $43.32 ≈ $585."""
    out = compute_cbam_trajectory(
        ["aluminium"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    cost_2030 = out["cbam_cost_2030_usd_per_tonne"]
    # Hard bounds — must be in the Scope-1-only zone, not the (Scope 1 + 2) zone.
    assert 50 <= cost_2030 <= 80, (
        f"Expected aluminium 2030 cost in [50, 80] (Scope 1 only); got {cost_2030}. "
        "If this is in the ~500 range, the Scope 2 priced gate is broken."
    )


def test_steel_bfbof_cost_dominated_by_scope_1() -> None:
    """BF-BOF Scope 1 (1.8 tCO2/t coke) dominates. Removing the Scope 2 component
    (0.25 MWh/t × 0.8 = 0.2 tCO2/t) drops the cost by only ~10%."""
    out = compute_cbam_trajectory(
        ["steel_bfbof"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    cost_2030 = out["cbam_cost_2030_usd_per_tonne"]
    # Scope 1 only: 1.8 × $43.32 ≈ $78.
    assert 70 <= cost_2030 <= 85, f"Expected BF-BOF 2030 cost ~$78 (Scope 1 only); got {cost_2030}."


def test_emission_intensity_current_reports_total_even_when_unpriced() -> None:
    """The reported `emission_intensity_current` includes Scope 2 even for
    sectors where it isn't priced — the EU reg still requires Scope 2
    reporting. Only the cost/savings math gates on `scope_2_priced`."""
    out = compute_cbam_trajectory(
        ["aluminium"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10
    )
    # Aluminium: 1.5 Scope 1 + (15.0 × 0.8 = 12.0 Scope 2) = 13.5 reported.
    assert out["cbam_emission_intensity_current"] == 13.5
    # Solar/Scope-1-only is just the process emissions.
    assert out["cbam_emission_intensity_solar"] == 1.5


def test_scope_2_priced_is_none_for_non_cbam_site() -> None:
    """Sites with no CBAM exposure get null for the flag too."""
    out = compute_cbam_trajectory([], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.10)
    assert out["cbam_scope_2_priced"] is None


def test_unknown_ctype_defaults_to_scope_2_priced_true() -> None:
    """Conservative default: a new sector that lands without an explicit entry
    in CBAM_SCOPE_2_PRICED falls back to True (pre-v4.0.7 behavior). Prevents
    silent under-counting of new sectors before the assumption is reviewed."""
    out = compute_cbam_trajectory(
        ["new_sector_xyz"],
        grid_ef_t_co2_mwh=0.8,
        cbam_price_eur=80.0,
        eur_usd_rate=1.10,
    )
    # When unknown, the function returns 0 intensity (missing dict entries) so
    # cost will be 0 but the FLAG defaults to True. Verify the flag specifically.
    assert out["cbam_scope_2_priced"] is True
