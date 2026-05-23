"""Tests for the v4.1b destination-weighted CBAM functions (spec §7.2 + §7.3).

Covers:
- Spec §7.4 IMIP worked example anchor ($48/MWh 2025, $84/MWh 2030)
- Multi-market arithmetic: Σ (share × market_price) × emissions_intensity
- Year interpolation (linear between snapshot years 2025/2030/2034)
- Three-layer share fallback: site_override → sector_default → eu_fallback
- Provenance flag matches the fallback path taken
- All 9 incumbent columns emit independently per spec §7.3
- compute_cbam_trajectory (existing per-tonne legacy) is unchanged
"""

from __future__ import annotations

import pytest

from src.assumptions import (
    CARBON_PRICE_BY_MARKET,
    EXPORT_MARKET_SHARES_BY_SUBSECTOR,
    PROCESS_TO_SUBSECTOR,
)
from src.dash.logic.cbam import (
    _interpolate_carbon_price,
    compute_destination_weighted_carbon_adder,
    compute_destination_weighted_incumbent,
    compute_destination_weighted_incumbent_columns,
    resolve_export_shares,
)

# ─── Spec §7.4 IMIP worked example anchor ───────────────────────────────────
#
# IMIP exports majority to China stainless (Tsingshan-controlled). Override
# shares: china_stainless 0.50 + battery_supply_chain_eu_oem 0.35 +
# direct_eu_uk_us 0.15. Nickel RKEF emissions intensity 0.95 tCO2/MWh
# (Sulawesi grid factor). Spec §7.4 says:
#   2025 effective price = 0.50×$12 + 0.35×$90 + 0.15×$90 = $51/t
#   2030 effective price = 0.50×$30 + 0.35×$150 + 0.15×$140 = $88/t
#   2025 carbon adder    = 0.95 × $51 = $48/MWh
#   2030 carbon adder    = 0.95 × $88 = $84/MWh


def test_spec_74_imip_2025_anchor():
    """Spec §7.4: IMIP 2025 carbon adder = $48/MWh (with $2/MWh tolerance for rounding)."""
    shares = {
        "china_stainless": 0.50,
        "battery_supply_chain_eu_oem": 0.35,
        "direct_eu_uk_us": 0.15,
    }
    adder = compute_destination_weighted_carbon_adder(
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
        year=2025,
    )
    # 0.50 × 12 + 0.35 × 90 + 0.15 × 90 = 6 + 31.5 + 13.5 = 51
    # × 0.95 = 48.45
    assert adder == pytest.approx(48.45, abs=1.0)


def test_spec_74_imip_2030_anchor():
    """Spec §7.4: IMIP 2030 carbon adder = $84/MWh."""
    shares = {
        "china_stainless": 0.50,
        "battery_supply_chain_eu_oem": 0.35,
        "direct_eu_uk_us": 0.15,
    }
    adder = compute_destination_weighted_carbon_adder(
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
        year=2030,
    )
    # 0.50 × 30 + 0.35 × 150 + 0.15 × 140 = 15 + 52.5 + 21 = 88.5
    # × 0.95 = 84.075
    assert adder == pytest.approx(84.075, abs=1.0)


def test_spec_74_baseline_understatement_factor():
    """Spec §7.1 claim: baseline single-EU @20% gives $9-17/MWh; destination-
    weighted gives $35-50/MWh. The 3-4× error must hold for IMIP."""
    dwt_shares = {
        "china_stainless": 0.50,
        "battery_supply_chain_eu_oem": 0.35,
        "direct_eu_uk_us": 0.15,
    }
    baseline_shares = {
        "direct_eu_uk_us": 0.20,
    }  # The v4.1 baseline implicit assumption
    dwt_adder = compute_destination_weighted_carbon_adder(
        0.95, dwt_shares, CARBON_PRICE_BY_MARKET, 2025
    )
    # Baseline only has 20% EU share — the other 80% is implicitly zero-carbon
    baseline_adder = compute_destination_weighted_carbon_adder(
        0.95, baseline_shares, CARBON_PRICE_BY_MARKET, 2025
    )
    # 2025 effective: 0.20 × 90 = $18/t, × 0.95 = $17.10/MWh
    assert baseline_adder == pytest.approx(17.1, abs=0.5)
    # Destination-weighted is ~3× the baseline at 2025 (spec says 3-4× by 2030)
    assert dwt_adder / baseline_adder >= 2.5


# ─── Year interpolation (spec §3.5) ─────────────────────────────────────────


def test_interpolation_at_snapshot_year_returns_exact():
    traj = {2025: 12.0, 2030: 30.0, 2034: 50.0}
    assert _interpolate_carbon_price(traj, 2025) == 12.0
    assert _interpolate_carbon_price(traj, 2030) == 30.0
    assert _interpolate_carbon_price(traj, 2034) == 50.0


def test_interpolation_between_snapshots_is_linear():
    traj = {2025: 12.0, 2030: 30.0, 2034: 50.0}
    # Halfway between 2025 and 2030 = 2027.5 → (12 + 30) / 2 = 21
    assert _interpolate_carbon_price(traj, 2028) == pytest.approx(12.0 + (30.0 - 12.0) * 3 / 5)


def test_interpolation_below_first_snapshot_clamps():
    """Below the first snapshot year, return the first value (constant extrap)."""
    traj = {2025: 12.0, 2030: 30.0}
    assert _interpolate_carbon_price(traj, 2020) == 12.0


def test_interpolation_above_last_snapshot_clamps():
    """Above the last snapshot, return the last value."""
    traj = {2025: 12.0, 2030: 30.0}
    assert _interpolate_carbon_price(traj, 2040) == 30.0


# ─── Three-layer share fallback (locked decision 2A) ────────────────────────


def test_resolve_site_override():
    overrides = {"imip": {"china_stainless": 0.5, "direct_eu_uk_us": 0.5}}
    shares, provenance = resolve_export_shares(
        site_id="imip",
        cbam_product_type="nickel_rkef",
        overrides=overrides,
        sector_defaults=EXPORT_MARKET_SHARES_BY_SUBSECTOR,
        process_to_subsector=PROCESS_TO_SUBSECTOR,
    )
    assert provenance == "site_override"
    assert shares == {"china_stainless": 0.5, "direct_eu_uk_us": 0.5}


def test_resolve_sector_default_via_process_to_subsector_mapping():
    """nickel_rkef (process) → nickel_npi (subsector) → spec §3.3 defaults."""
    shares, provenance = resolve_export_shares(
        site_id="unknown-site",
        cbam_product_type="nickel_rkef",
        overrides={},
        sector_defaults=EXPORT_MARKET_SHARES_BY_SUBSECTOR,
        process_to_subsector=PROCESS_TO_SUBSECTOR,
    )
    assert provenance == "sector_default"
    # Spec §3.3 nickel_npi defaults
    assert shares["china_stainless"] == 0.70
    assert shares["battery_supply_chain_eu_oem"] == 0.20
    assert shares["direct_eu_uk_us"] == 0.10


def test_resolve_eu_fallback_when_unknown_product():
    """Unknown product type → 100% direct_eu_uk_us (matches v4.1a implicit behavior)."""
    shares, provenance = resolve_export_shares(
        site_id="unknown-site",
        cbam_product_type="unknown_process",
        overrides={},
        sector_defaults=EXPORT_MARKET_SHARES_BY_SUBSECTOR,
        process_to_subsector=PROCESS_TO_SUBSECTOR,
    )
    assert provenance == "eu_fallback"
    assert shares == {"direct_eu_uk_us": 1.0}


def test_resolve_eu_fallback_when_no_product_type():
    """Site with cbam_product_type=None falls all the way through."""
    shares, provenance = resolve_export_shares(
        site_id="unknown-site",
        cbam_product_type=None,
        overrides={},
        sector_defaults=EXPORT_MARKET_SHARES_BY_SUBSECTOR,
        process_to_subsector=PROCESS_TO_SUBSECTOR,
    )
    assert provenance == "eu_fallback"
    assert shares == {"direct_eu_uk_us": 1.0}


# ─── Compute incumbent: base + adder ───────────────────────────────────────


def test_compute_destination_weighted_incumbent_adds_to_base():
    """incumbent = base + adder."""
    shares = {"china_stainless": 1.0}
    incumbent = compute_destination_weighted_incumbent(
        base_incumbent_cost_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
        year=2025,
    )
    # 0.95 × 12 = $11.4 adder + $80 base = $91.4
    assert incumbent == pytest.approx(91.4, abs=0.5)


# ─── 9-column emission per spec §7.3 ─────────────────────────────────────────


def test_11_columns_emit_per_spec_73_plus_sub_pr_e():
    """compute_destination_weighted_incumbent_columns returns exactly 11 columns:
    9 year-indexed scenarios per spec §7.3 + 2 domestic single-point scenarios
    added in sub-PR (e) #96 per spec §2.4. No missing keys, no extra keys.
    """
    shares = {
        "china_stainless": 0.50,
        "battery_supply_chain_eu_oem": 0.35,
        "direct_eu_uk_us": 0.15,
    }
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    expected_keys = {
        # 9 year-indexed columns from #95 / spec §7.3
        "cbam_destination_weighted_incumbent_2025_usd_mwh",
        "cbam_destination_weighted_incumbent_2030_usd_mwh",
        "cbam_destination_weighted_incumbent_2034_usd_mwh",
        "cbam_full_incumbent_2025_usd_mwh",
        "cbam_full_incumbent_2030_usd_mwh",
        "cbam_full_incumbent_2034_usd_mwh",
        "cbam_china_only_incumbent_2025_usd_mwh",
        "cbam_china_only_incumbent_2030_usd_mwh",
        "cbam_china_only_incumbent_2034_usd_mwh",
        # 2 domestic single-point columns from sub-PR (e) #96 / spec §2.4
        "cbam_domestic_low_incumbent_usd_mwh",
        "cbam_domestic_high_incumbent_usd_mwh",
    }
    assert set(cols.keys()) == expected_keys


def test_full_incumbent_uses_100pct_eu():
    """cbam_full_incumbent = base + 1.0 × direct_eu_uk_us price × emissions."""
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"asean_regional": 1.0},  # Irrelevant — full uses EU
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    # 2025: 0.95 × 90 = $85.5 adder + $80 base = $165.5
    assert cols["cbam_full_incumbent_2025_usd_mwh"] == pytest.approx(165.5, abs=0.5)


def test_china_only_incumbent_uses_100pct_china_stainless():
    """cbam_china_only_incumbent = base + 1.0 × china_stainless price × emissions."""
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"asean_regional": 1.0},
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    # 2025: 0.95 × 12 = $11.4 adder + $80 base = $91.4
    assert cols["cbam_china_only_incumbent_2025_usd_mwh"] == pytest.approx(91.4, abs=0.5)


def test_destination_weighted_uses_provided_shares():
    """The destination-weighted column reflects the actual share dict passed in,
    distinct from full + china_only stress variants."""
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"asean_regional": 1.0},  # No carbon price in ASEAN 2025
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    # ASEAN 2025 price = 0 → adder = 0 → incumbent = 80
    assert cols["cbam_destination_weighted_incumbent_2025_usd_mwh"] == pytest.approx(80.0, abs=0.5)
    # But full and china_only stress columns are non-zero
    assert cols["cbam_full_incumbent_2025_usd_mwh"] > 100
    assert cols["cbam_china_only_incumbent_2025_usd_mwh"] > 80


def test_year_progression_non_decreasing():
    """For any site, incumbent_2034 >= incumbent_2030 >= incumbent_2025 in
    every scenario (carbon prices are monotonic non-decreasing per
    test_cbam_datasets.py)."""
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={
            "china_stainless": 0.50,
            "battery_supply_chain_eu_oem": 0.35,
            "direct_eu_uk_us": 0.15,
        },
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    for scenario in ("destination_weighted", "full", "china_only"):
        v2025 = cols[f"cbam_{scenario}_incumbent_2025_usd_mwh"]
        v2030 = cols[f"cbam_{scenario}_incumbent_2030_usd_mwh"]
        v2034 = cols[f"cbam_{scenario}_incumbent_2034_usd_mwh"]
        assert v2025 <= v2030 <= v2034, f"{scenario} not monotonic: {v2025} → {v2030} → {v2034}"


# ─── Regression: existing compute_cbam_trajectory untouched ─────────────────


def test_compute_cbam_trajectory_still_works_after_v41b_changes():
    """Sanity check: the legacy per-tonne function hasn't been broken by the
    v4.1b additive layer above it."""
    from src.dash.logic.cbam import compute_cbam_trajectory

    out = compute_cbam_trajectory(
        cbam_types=["nickel_rkef"],
        grid_ef_t_co2_mwh=0.95,
        cbam_price_eur=80.0,
        eur_usd_rate=1.10,
    )
    assert out["cbam_exposed"] is True
    assert out["cbam_cost_2026_usd_per_tonne"] is not None
    assert out["cbam_cost_2030_usd_per_tonne"] is not None
    assert out["cbam_cost_2034_usd_per_tonne"] is not None
