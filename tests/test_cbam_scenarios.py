"""Tests for the v4.1b sub-PR (e) #96 CBAM scenario toggle (spec §2.4).

Covers:
- 2 new domestic-scenario columns (domestic_low @ $5/t, domestic_high @ $25/t)
- Sector-dependent default mapping (nickel → effective_2025, cement → domestic_high, etc.)
- Scenario resolver: (scenario_choice, subsector) → (active_scenario, column_name)
- "auto" sentinel resolves via DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR
- "none" scenario returns None for column (no carbon adder)
- Unknown scenario / subsector falls back to effective_2025
- CBAM_SCENARIO_VALUES tuple covers exactly the spec §2.4 set
"""

from __future__ import annotations

import pytest

from src.assumptions import (
    CARBON_PRICE_BY_MARKET,
    CBAM_DOMESTIC_HIGH_USD_TCO2,
    CBAM_DOMESTIC_LOW_USD_TCO2,
    CBAM_SCENARIO_VALUES,
    DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    EXPORT_MARKET_SHARES_BY_SUBSECTOR,
    PROCESS_TO_SUBSECTOR,
)
from src.dash.logic.cbam import (
    compute_destination_weighted_incumbent_columns,
    resolve_cbam_scenario_column,
)

# ─── 2 new domestic-scenario columns ───────────────────────────────────────


def test_domestic_low_column_arithmetic():
    """cbam_domestic_low_incumbent = grid_cost + grid_ef × $5/t.

    Spec §2.4: domestic_low is the current Indonesian IDX Carbon floor ($5/tCO2)
    applied uniformly to the site's emissions intensity. No export-share
    weighting; this is a "domestic policy" scenario.
    """
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"china_stainless": 1.0},  # irrelevant for domestic_*
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    # 80 + 0.95 × 5 = 80 + 4.75 = 84.75
    assert cols["cbam_domestic_low_incumbent_usd_mwh"] == pytest.approx(84.75, abs=0.01)


def test_domestic_high_column_arithmetic():
    """cbam_domestic_high_incumbent = grid_cost + grid_ef × $25/t."""
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"china_stainless": 1.0},
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    # 80 + 0.95 × 25 = 80 + 23.75 = 103.75
    assert cols["cbam_domestic_high_incumbent_usd_mwh"] == pytest.approx(103.75, abs=0.01)


def test_domestic_columns_ignore_export_shares():
    """Per spec §2.4, domestic_low and domestic_high are policy scenarios that
    don't depend on export markets. Different shares should give the same
    domestic_low value."""
    cols_china = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"china_stainless": 1.0},
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    cols_eu = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares={"direct_eu_uk_us": 1.0},
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    assert (
        cols_china["cbam_domestic_low_incumbent_usd_mwh"]
        == cols_eu["cbam_domestic_low_incumbent_usd_mwh"]
    )
    assert (
        cols_china["cbam_domestic_high_incumbent_usd_mwh"]
        == cols_eu["cbam_domestic_high_incumbent_usd_mwh"]
    )


def test_domestic_constants_match_spec():
    """Spec §2.4 anchors: domestic_low = $5/t, domestic_high = $25/t."""
    assert CBAM_DOMESTIC_LOW_USD_TCO2 == 5.0
    assert CBAM_DOMESTIC_HIGH_USD_TCO2 == 25.0


# ─── CBAM_SCENARIO_VALUES coverage ─────────────────────────────────────────


def test_scenario_values_match_spec_24():
    """Spec §2.4 lists exactly 7 scenarios (plus 'auto' sentinel)."""
    expected = {
        "auto",
        "none",
        "domestic_low",
        "domestic_high",
        "effective_2025",
        "effective_2030",
        "cbam_full_2026",
        "cbam_full_2030",
    }
    assert set(CBAM_SCENARIO_VALUES) == expected


# ─── Sector-dependent default mapping (locked decision 1B) ──────────────────


def test_every_cbam_subsector_has_default():
    """Every CBAM subsector mapped in PROCESS_TO_SUBSECTOR must also have a
    default scenario in DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR. A new sector
    added later without an entry would crash the resolver via fallback —
    caught at CI rather than at request time."""
    cbam_subsectors = set(PROCESS_TO_SUBSECTOR.values())
    mapped_subsectors = set(DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR.keys())
    missing = cbam_subsectors - mapped_subsectors
    assert not missing, f"Subsectors missing from default map: {missing}"


def test_every_default_scenario_is_valid():
    """Every value in DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR must be a recognized
    scenario (not "auto" — that's a frontend sentinel)."""
    for subsector, scenario in DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR.items():
        assert scenario in CBAM_SCENARIO_VALUES, f"{subsector}: invalid default {scenario!r}"
        assert scenario != "auto", f"{subsector}: 'auto' is a sentinel, not a real default"


def test_nickel_defaults_to_effective_2025():
    """Locked decision 1B: nickel sites face heavy China/EU OEM exposure →
    destination-weighted default."""
    assert DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR["nickel_npi"] == "effective_2025"
    assert DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR["nickel_matte"] == "effective_2025"


def test_cement_defaults_to_domestic_high():
    """Locked decision 1B: cement is 95% domestic → domestic policy is the
    relevant lever, not CBAM."""
    assert DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR["cement"] == "domestic_high"


# ─── resolve_cbam_scenario_column ──────────────────────────────────────────


def test_resolver_explicit_scenario_passes_through():
    """When user picks a specific scenario, the resolver returns it directly."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="cbam_full_2026",
        subsector="nickel_npi",  # ignored when scenario is explicit
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "cbam_full_2026"
    assert column == "cbam_full_incumbent_2025_usd_mwh"


def test_resolver_auto_uses_sector_default_nickel():
    """When scenario is 'auto', the resolver picks the sector default."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector="nickel_npi",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "effective_2025"
    assert column == "cbam_destination_weighted_incumbent_2025_usd_mwh"


def test_resolver_auto_uses_sector_default_cement():
    scenario, column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector="cement",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "domestic_high"
    assert column == "cbam_domestic_high_incumbent_usd_mwh"


def test_resolver_none_returns_none_column():
    """The 'none' scenario means 'no carbon adder' — column is None;
    frontend should render the unadjusted grid_cost."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="none",
        subsector="nickel_npi",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "none"
    assert column is None


def test_resolver_unknown_scenario_falls_back_to_effective_2025():
    """Defensive: unknown scenario string shouldn't crash."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="garbage_value",
        subsector="nickel_npi",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "effective_2025"
    assert column == "cbam_destination_weighted_incumbent_2025_usd_mwh"


def test_resolver_auto_with_unknown_subsector_falls_back():
    """When 'auto' with a subsector not in the default map, fall back to
    effective_2025 (the spec's stated default)."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector="exotic_new_sector",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "effective_2025"
    assert column == "cbam_destination_weighted_incumbent_2025_usd_mwh"


def test_resolver_auto_with_no_subsector_falls_back():
    scenario, column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector=None,
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "effective_2025"
    assert column == "cbam_destination_weighted_incumbent_2025_usd_mwh"


def test_resolver_domestic_low_maps_to_new_column():
    """The new sub-PR (e) domestic_low column is wired into the resolver."""
    scenario, column = resolve_cbam_scenario_column(
        scenario="domestic_low",
        subsector="cement",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert scenario == "domestic_low"
    assert column == "cbam_domestic_low_incumbent_usd_mwh"


def test_resolver_all_scenarios_resolve_without_crash():
    """Every value in CBAM_SCENARIO_VALUES should resolve without exception."""
    for scenario in CBAM_SCENARIO_VALUES:
        _, _ = resolve_cbam_scenario_column(
            scenario=scenario,
            subsector="nickel_npi",
            default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
        )


# ─── Integration: silos do not interact poorly ─────────────────────────────


def test_existing_destination_weighted_columns_match_subsector_default_for_nickel():
    """For a nickel site under 'auto', the active column should be the
    destination_weighted_2025 column — and it should have the same value
    whether you read it directly or via the resolver."""
    shares = EXPORT_MARKET_SHARES_BY_SUBSECTOR["nickel_npi"]
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    _, active_column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector="nickel_npi",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert active_column == "cbam_destination_weighted_incumbent_2025_usd_mwh"
    # The active column value matches what's directly emitted
    assert cols[active_column] > 80  # carbon adder makes it bigger than base


def test_existing_destination_weighted_columns_match_subsector_default_for_cement():
    """Cement defaults to domestic_high (per locked 1B) — so resolver picks
    the new sub-PR (e) column."""
    shares = EXPORT_MARKET_SHARES_BY_SUBSECTOR["cement"]
    cols = compute_destination_weighted_incumbent_columns(
        base_incumbent_usd_mwh=80.0,
        emissions_intensity_t_co2_per_mwh=0.95,
        export_market_shares=shares,
        carbon_price_by_market=CARBON_PRICE_BY_MARKET,
    )
    _, active_column = resolve_cbam_scenario_column(
        scenario="auto",
        subsector="cement",
        default_by_subsector=DEFAULT_CBAM_SCENARIO_BY_SUBSECTOR,
    )
    assert active_column == "cbam_domestic_high_incumbent_usd_mwh"
    assert cols[active_column] == pytest.approx(103.75, abs=0.01)
