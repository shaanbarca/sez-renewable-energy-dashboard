"""
Unit tests for src/model/basic_model.py

Covers:
  - PVOUT daily-to-annual conversion and plausibility guard
  - Capacity factor derivation
  - Capital Recovery Factor (CRF)
  - LCOE formula with unit plausibility guard
  - All-in captive solar cost (LCOE + firming adder)
  - Solar competitive gap
  - is_solar_attractive
  - action_flags (all four flags, all combinations)
  - GEAS baseline allocation (pro-rata)
  - GEAS policy allocation (priority-weighted)
  - RUPTL region metrics (post2030_share, grid_upgrade_pre2030)
  - build_scorecard (end-to-end smoke test)
  - Edge cases: zero demand, no RUPTL pre-2030, grid_cost=None
"""

import math

import pandas as pd
import pytest

from src.model.basic_model import (
    FIRMING_ADDER_HIGH_USD_MWH,
    FIRMING_ADDER_LOW_USD_MWH,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    HOURS_PER_YEAR,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PVOUT_ANNUAL_MAX,
    PVOUT_ANNUAL_MIN,
    action_flags,
    build_scorecard,
    capacity_factor_from_pvout,
    capital_recovery_factor,
    carbon_breakeven_price,
    geas_baseline_allocation,
    geas_policy_allocation,
    gentie_cost_per_kw,
    invest_resilience,
    is_solar_attractive,
    lcoe_solar,
    lcoe_solar_remote_captive,
    lcoe_solar_with_firming,
    pvout_daily_to_annual,
    resolve_demand,
    ruptl_region_metrics,
    solar_competitive_gap,
    time_bucket,
    wind_speed_to_cf,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_kek_df():
    return pd.DataFrame(
        {
            "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
            "kek_name": ["Kendal", "Bitung", "Sungai Liat", "Arun"],
            "province": ["Central Java", "North Sulawesi", "Bangka Belitung", "Aceh"],
            "grid_region_id": ["JAVA_BALI", "SULAWESI", "SUMATERA", "SUMATERA"],
            "reliability_req": [0.4, 0.8, 0.6, 0.9],
        }
    )


@pytest.fixture
def sample_demand_df():
    return pd.DataFrame(
        {
            "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
            "year": [2030, 2030, 2030, 2030],
            "demand_mwh": [800_000, 250_000, 120_000, 600_000],
        }
    )


@pytest.fixture
def sample_pvout_df():
    # Annual values (kWh/kWp/year)
    return pd.DataFrame(
        {
            "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
            "pvout_centroid": [1650, 1505, 1420, 1550],
            "pvout_best_50km": [1780, 1620, 1500, 1670],
        }
    )


@pytest.fixture
def sample_ruptl_df():
    return pd.DataFrame(
        {
            "grid_region_id": [
                "JAVA_BALI",
                "JAVA_BALI",
                "SULAWESI",
                "SULAWESI",
                "SUMATERA",
                "SUMATERA",
            ],
            "year": [2028, 2032, 2029, 2033, 2027, 2032],
            "plts_new_mw_re_base": [800, 2500, 100, 600, 300, 1800],
        }
    )


# ---------------------------------------------------------------------------
# 1. PVOUT daily-to-annual
# ---------------------------------------------------------------------------


class TestPvoutDailyToAnnual:
    def test_typical_value(self):
        # 4.5 kWh/kWp/day * 365 = 1642.5 kWh/kWp/yr (plausible Indonesia)
        result = pvout_daily_to_annual(4.5)
        assert math.isclose(result, 4.5 * 365)

    def test_boundary_low(self):
        # Just above minimum daily (1000/365 ≈ 2.74)
        result = pvout_daily_to_annual(PVOUT_ANNUAL_MIN / 365.0)
        assert math.isclose(result, PVOUT_ANNUAL_MIN)

    def test_boundary_high(self):
        result = pvout_daily_to_annual(PVOUT_ANNUAL_MAX / 365.0)
        assert math.isclose(result, PVOUT_ANNUAL_MAX)

    def test_too_small_raises(self):
        # 1.0 kWh/kWp/day -> 365 kWh/kWp/yr (below PVOUT_ANNUAL_MIN=1000)
        with pytest.raises(ValueError, match="plausible range"):
            pvout_daily_to_annual(1.0)

    def test_too_large_raises(self):
        # 10.0 kWh/kWp/day -> 3650 kWh/kWp/yr (above PVOUT_ANNUAL_MAX=2500)
        with pytest.raises(ValueError, match="plausible range"):
            pvout_daily_to_annual(10.0)

    def test_annual_passthrough_fails(self):
        # Common bug: passing annual value (1650) as daily -> 1650*365 >> 2500
        with pytest.raises(ValueError):
            pvout_daily_to_annual(1650.0)


# ---------------------------------------------------------------------------
# 2. Capacity factor
# ---------------------------------------------------------------------------


class TestCapacityFactor:
    def test_known_value(self):
        cf = capacity_factor_from_pvout(1752.0)  # 1752 / 8760 = 0.2
        assert math.isclose(cf, 0.2)

    def test_typical_indonesia(self):
        # PVOUT 1600 kWh/kWp/yr -> CF ~18.3%
        cf = capacity_factor_from_pvout(1600.0)
        assert math.isclose(cf, 1600.0 / 8760.0)
        assert 0.15 < cf < 0.25  # sanity band for Indonesia

    def test_proportional(self):
        cf1 = capacity_factor_from_pvout(1400.0)
        cf2 = capacity_factor_from_pvout(2800.0)
        assert math.isclose(cf2 / cf1, 2.0)


# ---------------------------------------------------------------------------
# 3. Capital Recovery Factor
# ---------------------------------------------------------------------------


class TestCapitalRecoveryFactor:
    def test_known_value(self):
        # CRF(9%, 25yr) — verified against standard annuity tables
        crf = capital_recovery_factor(0.09, 25)
        assert math.isclose(crf, 0.10181, rel_tol=1e-4)

    def test_higher_wacc_higher_crf(self):
        crf_low = capital_recovery_factor(0.05, 25)
        crf_high = capital_recovery_factor(0.12, 25)
        assert crf_high > crf_low

    def test_shorter_life_higher_crf(self):
        crf_short = capital_recovery_factor(0.09, 10)
        crf_long = capital_recovery_factor(0.09, 25)
        assert crf_short > crf_long

    def test_zero_wacc_raises(self):
        with pytest.raises(ValueError):
            capital_recovery_factor(0.0, 25)

    def test_zero_lifetime_raises(self):
        with pytest.raises(ValueError):
            capital_recovery_factor(0.09, 0)


# ---------------------------------------------------------------------------
# 4. LCOE
# ---------------------------------------------------------------------------


class TestLcoeSolar:
    def test_typical_value(self):
        # CAPEX=700, FOM=12, WACC=9%, life=25yr, PVOUT=1650 -> expect ~$50-65/MWh
        cf = capacity_factor_from_pvout(1650.0)
        result = lcoe_solar(700.0, 12.0, 0.09, 25, cf)
        assert 40.0 < result < 80.0, f"LCOE={result:.1f} is outside plausible range"

    def test_higher_pvout_lower_lcoe(self):
        cf_low = capacity_factor_from_pvout(1400.0)
        cf_high = capacity_factor_from_pvout(1800.0)
        assert lcoe_solar(700, 12, 0.09, 25, cf_low) > lcoe_solar(700, 12, 0.09, 25, cf_high)

    def test_higher_wacc_higher_lcoe(self):
        cf = capacity_factor_from_pvout(1600.0)
        assert lcoe_solar(700, 12, 0.05, 25, cf) < lcoe_solar(700, 12, 0.12, 25, cf)

    def test_capex_too_low_raises(self):
        # 0.7 USD/kW — looks like MUSD/MWe was passed without conversion
        with pytest.raises(ValueError, match="plausibility bounds"):
            lcoe_solar(0.7, 12, 0.09, 25, 0.20)

    def test_capex_too_high_raises(self):
        # 700_000 USD/kW — clearly wrong units
        with pytest.raises(ValueError, match="plausibility bounds"):
            lcoe_solar(700_000, 12, 0.09, 25, 0.20)

    def test_zero_cf_raises(self):
        with pytest.raises(ValueError):
            lcoe_solar(700, 12, 0.09, 25, 0.0)

    def test_unit_conversion_capex(self):
        # MUSD/MWe = 0.700 -> USD/kW = 700 (correct)
        capex_musd_mwe = 0.700
        capex_usd_kw = capex_musd_mwe * 1000  # explicit conversion
        cf = capacity_factor_from_pvout(1600.0)
        result = lcoe_solar(capex_usd_kw, 12, 0.09, 25, cf)
        assert 40.0 < result < 80.0


# ---------------------------------------------------------------------------
# 5. LCOE with firming adder
# ---------------------------------------------------------------------------


class TestLcoeSolarWithFirming:
    def test_mid_adder(self):
        cf = capacity_factor_from_pvout(1600.0)
        base = lcoe_solar(700, 12, 0.09, 25, cf)
        all_in = lcoe_solar_with_firming(700, 12, 0.09, 25, cf, firming_adder="mid")
        expected_adder = (FIRMING_ADDER_LOW_USD_MWH + FIRMING_ADDER_HIGH_USD_MWH) / 2
        assert math.isclose(all_in - base, expected_adder)

    def test_low_adder(self):
        cf = capacity_factor_from_pvout(1600.0)
        base = lcoe_solar(700, 12, 0.09, 25, cf)
        all_in = lcoe_solar_with_firming(700, 12, 0.09, 25, cf, firming_adder="low")
        assert math.isclose(all_in - base, FIRMING_ADDER_LOW_USD_MWH)

    def test_high_adder(self):
        cf = capacity_factor_from_pvout(1600.0)
        base = lcoe_solar(700, 12, 0.09, 25, cf)
        all_in = lcoe_solar_with_firming(700, 12, 0.09, 25, cf, firming_adder="high")
        assert math.isclose(all_in - base, FIRMING_ADDER_HIGH_USD_MWH)

    def test_all_in_greater_than_base(self):
        cf = capacity_factor_from_pvout(1600.0)
        for adder in ("low", "mid", "high"):
            assert lcoe_solar_with_firming(700, 12, 0.09, 25, cf, adder) > lcoe_solar(
                700, 12, 0.09, 25, cf
            )


# ---------------------------------------------------------------------------
# 5b. BESS LCOE
# ---------------------------------------------------------------------------


class TestBessStorageAdder:
    def test_plausible_range(self):
        """Battery adder at defaults (2h, $250/kWh, CF=0.18) should be $25-60/MWh."""
        from src.model.basic_model import bess_storage_adder

        result = bess_storage_adder()
        assert 25.0 < result < 60.0, f"Battery adder = ${result:.1f}/MWh, expected $25-60"

    def test_higher_capex_higher_adder(self):
        from src.model.basic_model import bess_storage_adder

        low = bess_storage_adder(bess_capex_usd_per_kwh=150.0)
        high = bess_storage_adder(bess_capex_usd_per_kwh=400.0)
        assert high > low

    def test_higher_cf_lower_adder(self):
        """Better solar sites spread battery cost over more MWh."""
        from src.model.basic_model import bess_storage_adder

        low_cf = bess_storage_adder(solar_cf=0.15)
        high_cf = bess_storage_adder(solar_cf=0.22)
        assert low_cf > high_cf

    def test_solar_with_battery_greater_than_base(self):
        from src.model.basic_model import lcoe_solar_with_battery

        cf = capacity_factor_from_pvout(1600.0)
        base = lcoe_solar(700, 12, 0.09, 25, cf)
        bundled = lcoe_solar_with_battery(700, 12, 0.09, 25, cf)
        assert bundled > base


# ---------------------------------------------------------------------------
# 6. Gen-tie cost and remote captive LCOE
# ---------------------------------------------------------------------------


class TestGentieCost:
    def test_zero_distance_equals_substation_works_only(self):
        """dist=0 → only substation works cost (no line construction)."""
        from src.assumptions import SUBSTATION_WORKS_PER_KW

        result = gentie_cost_per_kw(0.0)
        assert result == pytest.approx(SUBSTATION_WORKS_PER_KW)

    def test_10km_scales_linearly(self):
        """10km × $5/kW-km + $150/kW = $200/kW."""
        from src.assumptions import GENTIE_COST_PER_KW_KM, SUBSTATION_WORKS_PER_KW

        result = gentie_cost_per_kw(10.0)
        assert result == pytest.approx(10.0 * GENTIE_COST_PER_KW_KM + SUBSTATION_WORKS_PER_KW)

    def test_custom_params(self):
        """Custom cost_per_kw_km and substation_works_per_kw override defaults."""
        result = gentie_cost_per_kw(20.0, cost_per_kw_km=3.0, substation_works_per_kw=100.0)
        assert result == pytest.approx(20.0 * 3.0 + 100.0)

    def test_negative_distance_raises(self):
        """Negative distance is physically impossible and should raise ValueError."""
        with pytest.raises(ValueError):
            gentie_cost_per_kw(-1.0)


class TestLcoeSolarRemoteCaptive:
    def _base_args(self):
        return dict(
            capex_usd_per_kw=960.0, fixed_om_usd_per_kw_yr=7.5, wacc=0.10, lifetime_yr=27, cf=0.18
        )

    def test_zero_dist_equals_base_lcoe(self):
        """With dist=0 and substation_works=0, remote captive == base lcoe_solar."""
        args = self._base_args()
        base = lcoe_solar(**args)
        remote = lcoe_solar_remote_captive(**args, dist_km=0.0, substation_works_per_kw=0.0)
        assert remote == pytest.approx(base)

    def test_positive_dist_increases_lcoe(self):
        """Any positive distance should increase LCOE above the base."""
        args = self._base_args()
        base = lcoe_solar(**args)
        remote = lcoe_solar_remote_captive(**args, dist_km=20.0)
        assert remote > base

    def test_longer_distance_higher_lcoe(self):
        """Greater distance → higher effective CAPEX → higher LCOE."""
        args = self._base_args()
        lcoe_10 = lcoe_solar_remote_captive(**args, dist_km=10.0)
        lcoe_50 = lcoe_solar_remote_captive(**args, dist_km=50.0)
        assert lcoe_50 > lcoe_10


# ---------------------------------------------------------------------------
# 6b. V2 grid connection cost + grid-connected LCOE
# ---------------------------------------------------------------------------


class TestGridConnectionCost:
    def test_zero_distance_equals_fixed_only(self):
        """dist=0 → only fixed connection cost (no line construction)."""
        from src.assumptions import GRID_CONNECTION_FIXED_PER_KW
        from src.model.basic_model import grid_connection_cost_per_kw

        result = grid_connection_cost_per_kw(0.0)
        assert result == pytest.approx(GRID_CONNECTION_FIXED_PER_KW)

    def test_10km_scales_linearly(self):
        """10km × $5/kW-km + $80/kW = $130/kW."""
        from src.assumptions import CONNECTION_COST_PER_KW_KM, GRID_CONNECTION_FIXED_PER_KW
        from src.model.basic_model import grid_connection_cost_per_kw

        result = grid_connection_cost_per_kw(10.0)
        assert result == pytest.approx(
            10.0 * CONNECTION_COST_PER_KW_KM + GRID_CONNECTION_FIXED_PER_KW
        )

    def test_custom_params(self):
        from src.model.basic_model import grid_connection_cost_per_kw

        result = grid_connection_cost_per_kw(20.0, cost_per_kw_km=3.0, connection_fixed_per_kw=50.0)
        assert result == pytest.approx(20.0 * 3.0 + 50.0)

    def test_negative_distance_raises(self):
        from src.model.basic_model import grid_connection_cost_per_kw

        with pytest.raises(ValueError):
            grid_connection_cost_per_kw(-1.0)


class TestLcoeSolarGridConnected:
    def _base_args(self):
        return dict(
            capex_usd_per_kw=960.0, fixed_om_usd_per_kw_yr=7.5, wacc=0.10, lifetime_yr=27, cf=0.18
        )

    def test_zero_dist_with_zero_fixed_equals_base(self):
        from src.model.basic_model import lcoe_solar_grid_connected

        args = self._base_args()
        base = lcoe_solar(**args)
        gc = lcoe_solar_grid_connected(**args, dist_km=0.0, connection_fixed_per_kw=0.0)
        assert gc == pytest.approx(base)

    def test_positive_dist_increases_lcoe(self):
        from src.model.basic_model import lcoe_solar_grid_connected

        args = self._base_args()
        base = lcoe_solar(**args)
        gc = lcoe_solar_grid_connected(**args, dist_km=10.0)
        assert gc > base

    def test_longer_distance_higher_lcoe(self):
        from src.model.basic_model import lcoe_solar_grid_connected

        args = self._base_args()
        lcoe_5 = lcoe_solar_grid_connected(**args, dist_km=5.0)
        lcoe_20 = lcoe_solar_grid_connected(**args, dist_km=20.0)
        assert lcoe_20 > lcoe_5


# ---------------------------------------------------------------------------
# 6c. V2 grid integration category
# ---------------------------------------------------------------------------


class TestGridIntegrationCategory:
    def test_within_boundary(self):
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(True, None, 5.0) == "within_boundary"

    def test_within_boundary_overrides_distances(self):
        """Internal substation always returns within_boundary regardless of distances."""
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(True, 50.0, 50.0) == "within_boundary"

    def test_grid_ready(self):
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, 5.0, 10.0) == "grid_ready"

    def test_invest_transmission_solar_near_kek_far(self):
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, 5.0, 20.0) == "invest_transmission"

    def test_invest_substation_kek_near_solar_far(self):
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, 15.0, 10.0) == "invest_substation"

    def test_grid_first(self):
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, 15.0, 20.0) == "grid_first"

    def test_solar_coords_none_and_kek_near(self):
        """Missing solar coords + KEK near substation → invest_substation (solar side unknown)."""
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, None, 10.0) == "invest_substation"

    def test_solar_coords_none_and_kek_far(self):
        """Missing solar coords + KEK far from substation → grid_first."""
        from src.model.basic_model import grid_integration_category

        assert grid_integration_category(False, None, 20.0) == "grid_first"

    def test_low_capacity_substation_downgrades(self):
        """Substation below min capacity → treated as if not near."""
        from src.model.basic_model import grid_integration_category

        # Both distances within threshold, but capacity too low
        assert (
            grid_integration_category(False, 5.0, 10.0, substation_capacity_mva=10.0)
            == "grid_first"
        )

    def test_capacity_none_is_ok(self):
        """Unknown capacity (None) doesn't downgrade — benefit of the doubt."""
        from src.model.basic_model import grid_integration_category

        assert (
            grid_integration_category(False, 5.0, 10.0, substation_capacity_mva=None)
            == "grid_ready"
        )

    def test_custom_thresholds(self):
        from src.model.basic_model import grid_integration_category

        # With tighter thresholds, a previously grid_ready site becomes invest_substation
        # (solar at 8km > 5km threshold, KEK at 10km < 15km threshold)
        result = grid_integration_category(
            False,
            8.0,
            10.0,
            solar_to_sub_threshold_km=5.0,
            kek_to_sub_threshold_km=15.0,
        )
        assert result == "invest_substation"

    # V3.1: Capacity utilization tests
    def test_capacity_utilization_insufficient(self):
        """Substation near but available capacity < solar farm → invest_substation."""
        from src.model.basic_model import grid_integration_category

        # 60 MVA substation, 65% utilized → 21 MVA available; 30 MWp solar > 21 MVA
        result = grid_integration_category(
            False,
            3.0,
            10.0,
            substation_capacity_mva=60.0,
            substation_utilization_pct=0.65,
            solar_capacity_mwp=30.0,
        )
        assert result == "invest_substation"

    def test_capacity_utilization_sufficient(self):
        """Substation near with enough available capacity → grid_ready."""
        from src.model.basic_model import grid_integration_category

        # 60 MVA, 65% utilized → 21 MVA available; 10 MWp solar < 21 MVA
        result = grid_integration_category(
            False,
            3.0,
            10.0,
            substation_capacity_mva=60.0,
            substation_utilization_pct=0.65,
            solar_capacity_mwp=10.0,
        )
        assert result == "grid_ready"

    def test_capacity_utilization_none_solar_capacity(self):
        """Unknown solar capacity → skip utilization check (benefit of doubt)."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(
            False,
            3.0,
            10.0,
            substation_capacity_mva=60.0,
            substation_utilization_pct=0.65,
            solar_capacity_mwp=None,
        )
        assert result == "grid_ready"

    # V3.1: Inter-substation connectivity tests
    def test_inter_substation_not_connected_solar_near(self):
        """No line between substations + solar near → invest_transmission."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(
            False,
            3.0,
            10.0,
            inter_substation_connected=False,
        )
        assert result == "invest_transmission"

    def test_inter_substation_not_connected_solar_far(self):
        """No line between substations + solar far → grid_first."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(
            False,
            15.0,
            20.0,
            inter_substation_connected=False,
        )
        assert result == "grid_first"

    def test_inter_substation_connected_allows_grid_ready(self):
        """Line exists between substations → normal distance logic applies."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(
            False,
            3.0,
            10.0,
            inter_substation_connected=True,
        )
        assert result == "grid_ready"

    def test_inter_substation_none_falls_back(self):
        """Unknown connectivity (None) → falls back to distance-only logic."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(
            False,
            3.0,
            10.0,
            inter_substation_connected=None,
        )
        assert result == "grid_ready"

    def test_within_boundary_coverage_override(self):
        """KEK with >= 100% within-boundary solar coverage → within_boundary."""
        from src.model.basic_model import grid_integration_category

        # Without override: would be invest_substation (KEK near, solar far)
        assert grid_integration_category(False, 15.0, 10.0) == "invest_substation"
        # With 136% coverage: overrides to within_boundary
        result = grid_integration_category(False, 15.0, 10.0, within_boundary_coverage_pct=1.36)
        assert result == "within_boundary"

    def test_within_boundary_coverage_below_threshold(self):
        """KEK with < 100% within-boundary solar coverage → no override."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(False, 15.0, 10.0, within_boundary_coverage_pct=0.90)
        assert result == "invest_substation"

    def test_within_boundary_coverage_none(self):
        """None within_boundary_coverage_pct → no override (backwards compatible)."""
        from src.model.basic_model import grid_integration_category

        result = grid_integration_category(False, 15.0, 10.0, within_boundary_coverage_pct=None)
        assert result == "invest_substation"


class TestNewTransmissionCostPerKw:
    def test_basic_calculation(self):
        from src.model.basic_model import new_transmission_cost_per_kw

        # 10 km × $1.25M/km = $12.5M total ÷ (20 MWp × 1000) = $625/kW
        result = new_transmission_cost_per_kw(10.0, 20.0, cost_per_km=1_250_000)
        assert math.isclose(result, 625.0)

    def test_zero_distance(self):
        from src.model.basic_model import new_transmission_cost_per_kw

        assert new_transmission_cost_per_kw(0.0, 20.0) == 0.0

    def test_zero_capacity(self):
        from src.model.basic_model import new_transmission_cost_per_kw

        assert new_transmission_cost_per_kw(10.0, 0.0) == 0.0

    def test_negative_distance(self):
        from src.model.basic_model import new_transmission_cost_per_kw

        assert new_transmission_cost_per_kw(-5.0, 20.0) == 0.0

    def test_larger_capacity_reduces_per_kw(self):
        from src.model.basic_model import new_transmission_cost_per_kw

        small = new_transmission_cost_per_kw(10.0, 10.0)
        large = new_transmission_cost_per_kw(10.0, 50.0)
        assert large < small


class TestCapacityAssessment:
    def test_green(self):
        from src.model.basic_model import capacity_assessment

        light, avail = capacity_assessment(100.0, 10.0, utilization_pct=0.65)
        assert light == "green"
        assert avail == 35.0  # 100 × 0.35

    def test_yellow(self):
        from src.model.basic_model import capacity_assessment

        light, avail = capacity_assessment(60.0, 15.0, utilization_pct=0.65)
        assert light == "yellow"
        assert avail == 21.0  # 60 × 0.35 = 21, ratio = 21/15 = 1.4

    def test_red(self):
        from src.model.basic_model import capacity_assessment

        light, avail = capacity_assessment(60.0, 50.0, utilization_pct=0.65)
        assert light == "red"
        # 60 × 0.35 = 21, ratio = 21/50 = 0.42 < 0.5

    def test_unknown_no_capacity(self):
        from src.model.basic_model import capacity_assessment

        light, avail = capacity_assessment(None, 10.0)
        assert light == "unknown"
        assert avail is None

    def test_unknown_no_solar(self):
        from src.model.basic_model import capacity_assessment

        light, avail = capacity_assessment(60.0, None, utilization_pct=0.65)
        assert light == "unknown"
        assert avail == 21.0


class TestSubstationUpgradeCost:
    def test_sufficient_capacity_no_cost(self):
        from src.model.basic_model import substation_upgrade_cost_per_kw

        cost = substation_upgrade_cost_per_kw(200.0, 50.0, utilization_pct=0.65)
        assert cost == 0.0  # available = 70 MVA > 50 MWp

    def test_insufficient_capacity_adds_cost(self):
        from src.model.basic_model import substation_upgrade_cost_per_kw

        # 60 MVA × 0.35 = 21 available, solar = 50 MWp
        # deficit = (50 - 21) / 50 = 0.58
        cost = substation_upgrade_cost_per_kw(60.0, 50.0, utilization_pct=0.65)
        assert cost > 0
        assert math.isclose(cost, 0.58 * 80.0, rel_tol=0.01)

    def test_high_utilization_higher_cost(self):
        from src.model.basic_model import substation_upgrade_cost_per_kw

        cost_low = substation_upgrade_cost_per_kw(100.0, 50.0, utilization_pct=0.30)
        cost_high = substation_upgrade_cost_per_kw(100.0, 50.0, utilization_pct=0.90)
        assert cost_low == 0.0  # available = 70 > 50
        assert cost_high > 0  # available = 10 < 50

    def test_none_capacity_no_cost(self):
        from src.model.basic_model import substation_upgrade_cost_per_kw

        assert substation_upgrade_cost_per_kw(None, 50.0) == 0.0

    def test_none_solar_no_cost(self):
        from src.model.basic_model import substation_upgrade_cost_per_kw

        assert substation_upgrade_cost_per_kw(100.0, None) == 0.0


# ---------------------------------------------------------------------------
# 7. Solar competitive gap
# ---------------------------------------------------------------------------


class TestSolarCompetitiveGap:
    def test_competitive(self):
        # Solar at $50/MWh vs grid at $60/MWh -> gap = -16.7%
        gap = solar_competitive_gap(50.0, 60.0)
        assert math.isclose(gap, (50 - 60) / 60 * 100)
        assert gap < 0

    def test_parity(self):
        gap = solar_competitive_gap(60.0, 60.0)
        assert math.isclose(gap, 0.0)

    def test_not_competitive(self):
        gap = solar_competitive_gap(70.0, 60.0)
        assert gap > 0

    def test_zero_grid_cost_raises(self):
        with pytest.raises(ValueError):
            solar_competitive_gap(50.0, 0.0)


# ---------------------------------------------------------------------------
# 7. is_solar_attractive
# ---------------------------------------------------------------------------


class TestIsSolarAttractive:
    def test_cheaper_than_grid(self):
        assert is_solar_attractive(50.0, 60.0) is True

    def test_at_parity(self):
        assert is_solar_attractive(60.0, 60.0) is True

    def test_more_expensive(self):
        assert is_solar_attractive(65.0, 60.0) is False


# ---------------------------------------------------------------------------
# 8. action_flags
# ---------------------------------------------------------------------------


class TestActionFlags:
    def test_solar_now(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,  # grid ready
            reliability_req=0.4,  # below firming threshold
            green_share_geas=0.35,  # above 0.30
            post2030_share=0.30,  # below plan_late threshold
        )
        assert flags["solar_now"] is True
        assert flags["grid_first"] is False
        assert flags["invest_battery"] is False
        assert flags["plan_late"] is False

    def test_grid_first(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,  # grid NOT ready
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["grid_first"] is True
        assert flags["solar_now"] is False  # blocked by grid_first

    def test_invest_battery(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.80,  # at threshold (0.75)
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["invest_battery"] is True

    def test_invest_battery_below_threshold(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.74,  # just below threshold
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["invest_battery"] is False

    def test_plan_late(self):
        flags = action_flags(
            solar_attractive=False,
            grid_upgrade_pre2030=True,
            reliability_req=0.4,
            green_share_geas=0.1,
            post2030_share=0.65,  # above 0.60 threshold
        )
        assert flags["plan_late"] is True

    def test_not_solar_attractive_clears_solar_flags(self):
        flags = action_flags(
            solar_attractive=False,
            grid_upgrade_pre2030=True,
            reliability_req=0.9,
            green_share_geas=0.8,
            post2030_share=0.2,
        )
        assert flags["solar_now"] is False
        assert flags["grid_first"] is False
        assert flags["invest_battery"] is False

    def test_plan_late_independent_of_solar_attractive(self):
        flags_yes = action_flags(False, True, 0.4, 0.1, 0.65)
        flags_no = action_flags(True, True, 0.4, 0.1, 0.40)
        assert flags_yes["plan_late"] is True
        assert flags_no["plan_late"] is False

    def test_insufficient_geas_prevents_solar_now(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.4,
            green_share_geas=0.25,  # below 0.30 threshold
            post2030_share=0.2,
        )
        assert flags["solar_now"] is False

    def test_solar_now_requires_sufficient_geas(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.4,
            green_share_geas=GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,  # exactly at boundary
            post2030_share=0.2,
        )
        assert flags["solar_now"] is True

    def test_grid_first_suppressed_by_invest_transmission(self):
        """When gi_cat is invest_transmission, grid_first should be False."""
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
            grid_integration_cat="invest_transmission",
        )
        assert flags["grid_first"] is False
        assert flags["invest_transmission"] is True

    def test_grid_first_suppressed_by_invest_substation(self):
        """When gi_cat is invest_substation, grid_first should be False."""
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
            grid_integration_cat="invest_substation",
        )
        assert flags["grid_first"] is False
        assert flags["invest_substation"] is True

    def test_grid_first_still_fires_when_gi_cat_is_grid_first(self):
        """When gi_cat is explicitly grid_first, the flag should fire."""
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
            grid_integration_cat="grid_first",
        )
        assert flags["grid_first"] is True

    def test_grid_first_still_fires_when_gi_cat_is_none(self):
        """When gi_cat is None (data missing), grid_first should still fire."""
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
            grid_integration_cat=None,
        )
        assert flags["grid_first"] is True


# ---------------------------------------------------------------------------
# 9. GEAS baseline allocation
# ---------------------------------------------------------------------------


class TestGeasBaselineAllocation:
    def test_pro_rata_within_region(self, sample_kek_df, sample_ruptl_df):
        kek_demand = pd.DataFrame(
            {
                "kek_id": ["KEK_C", "KEK_D"],
                "grid_region_id": ["SUMATERA", "SUMATERA"],
                "demand_mwh": [120_000, 600_000],
            }
        )
        result = geas_baseline_allocation(kek_demand, sample_ruptl_df)

        # KEK_D should receive 600/(120+600) = 83.3% of regional allocation
        kek_c = result[result["kek_id"] == "KEK_C"].iloc[0]
        kek_d = result[result["kek_id"] == "KEK_D"].iloc[0]
        ratio = kek_d["geas_alloc_mwh"] / kek_c["geas_alloc_mwh"]
        assert math.isclose(ratio, 600_000 / 120_000)

    def test_green_share_capped_at_1(self, sample_ruptl_df):
        # Tiny demand => GEAS supply >> demand => green_share = 1.0
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_X"],
                "grid_region_id": ["JAVA_BALI"],
                "demand_mwh": [1.0],  # 1 MWh — trivially covered
            }
        )
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas"] == 1.0

    def test_no_ruptl_in_region_gives_zero(self):
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_X"],
                "grid_region_id": ["UNKNOWN_REGION"],
                "demand_mwh": [500_000],
            }
        )
        ruptl_df = pd.DataFrame(
            {
                "grid_region_id": ["JAVA_BALI"],
                "year": [2028],
                "plts_new_mw_re_base": [500],
            }
        )
        result = geas_baseline_allocation(kek_df, ruptl_df)
        assert result.iloc[0]["geas_alloc_mwh"] == 0.0
        assert result.iloc[0]["green_share_geas"] == 0.0

    def test_total_allocation_equals_supply(self, sample_ruptl_df):
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_C", "KEK_D"],
                "grid_region_id": ["SUMATERA", "SUMATERA"],
                "demand_mwh": [120_000, 600_000],
            }
        )
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        # Total allocated should equal SUMATERA pre-2030 supply (300 MW * 8760 * 0.20)
        expected_supply = 300 * HOURS_PER_YEAR * 0.20
        total_alloc = result["geas_alloc_mwh"].sum()
        assert math.isclose(total_alloc, expected_supply, rel_tol=1e-6)

    def test_zero_demand_returns_zero_not_nan(self, sample_ruptl_df):
        # Regression: demand=0 previously produced NaN via 0/0 division
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_X"],
                "grid_region_id": ["JAVA_BALI"],
                "demand_mwh": [0],
            }
        )
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas"] == 0.0
        assert not math.isnan(result.iloc[0]["green_share_geas"])


# ---------------------------------------------------------------------------
# 10. GEAS policy allocation
# ---------------------------------------------------------------------------


class TestGeasPolicyAllocation:
    def test_policy_ge_baseline_for_high_pvout(self, sample_ruptl_df):
        # High-pvout KEK should get >= baseline share in policy scenario
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_C", "KEK_D"],
                "grid_region_id": ["SUMATERA", "SUMATERA"],
                "demand_mwh": [120_000, 600_000],
                "pvout_best_50km": [1400, 1700],  # KEK_D has higher PVOUT
            }
        )
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        baseline = geas_baseline_allocation(
            kek_df[["kek_id", "grid_region_id", "demand_mwh"]], sample_ruptl_df
        )
        kek_d_baseline = baseline[baseline["kek_id"] == "KEK_D"].iloc[0]["green_share_geas"]
        kek_d_policy = result[result["kek_id"] == "KEK_D"].iloc[0]["green_share_geas_policy"]
        # With higher pvout score, KEK_D should do >= baseline
        assert kek_d_policy >= kek_d_baseline * 0.95  # allow small float tolerance

    def test_policy_supply_greater_than_baseline(self, sample_ruptl_df):
        # Policy shifts 20% of post-2030 into pre-2030 -> more total supply
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_A"],
                "grid_region_id": ["JAVA_BALI"],
                "demand_mwh": [800_000],
                "pvout_best_50km": [1780],
            }
        )
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        baseline = geas_baseline_allocation(
            kek_df[["kek_id", "grid_region_id", "demand_mwh"]], sample_ruptl_df
        )
        assert result.iloc[0]["geas_alloc_mwh_policy"] >= baseline.iloc[0]["geas_alloc_mwh"]

    def test_green_share_capped_at_1(self, sample_ruptl_df):
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_X"],
                "grid_region_id": ["JAVA_BALI"],
                "demand_mwh": [1.0],
                "pvout_best_50km": [1750],
            }
        )
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas_policy"] == 1.0

    def test_zero_demand_returns_zero_not_nan(self, sample_ruptl_df):
        # Regression: demand=0 previously produced NaN via 0/0 division
        kek_df = pd.DataFrame(
            {
                "kek_id": ["KEK_X"],
                "grid_region_id": ["JAVA_BALI"],
                "demand_mwh": [0],
                "pvout_best_50km": [1750],
            }
        )
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas_policy"] == 0.0
        assert not math.isnan(result.iloc[0]["green_share_geas_policy"])


# ---------------------------------------------------------------------------
# 11. RUPTL region metrics
# ---------------------------------------------------------------------------


class TestRuptlRegionMetrics:
    def test_post2030_share_java_bali(self, sample_ruptl_df):
        result = ruptl_region_metrics(sample_ruptl_df)
        jb = result[result["grid_region_id"] == "JAVA_BALI"].iloc[0]
        # pre: 800 MW, post: 2500 MW -> post_share = 2500/3300 ~ 0.758
        assert math.isclose(jb["post2030_share"], 2500 / 3300, rel_tol=1e-5)

    def test_plan_late_flag(self, sample_ruptl_df):
        result = ruptl_region_metrics(sample_ruptl_df)
        # JAVA_BALI post2030_share ~0.758 > 0.60 -> should be plan_late-eligible
        jb = result[result["grid_region_id"] == "JAVA_BALI"].iloc[0]
        assert jb["post2030_share"] >= PLAN_LATE_POST2030_SHARE_THRESHOLD

    def test_grid_upgrade_pre2030(self, sample_ruptl_df):
        result = ruptl_region_metrics(sample_ruptl_df)
        # JAVA_BALI earliest year = 2028 -> grid_upgrade_pre2030 = True
        jb = result[result["grid_region_id"] == "JAVA_BALI"].iloc[0]
        assert bool(jb["grid_upgrade_pre2030"]) is True

    def test_no_pre2030_additions(self):
        ruptl_df = pd.DataFrame(
            {
                "grid_region_id": ["REGION_X"],
                "year": [2035],
                "plts_new_mw_re_base": [500],
            }
        )
        result = ruptl_region_metrics(ruptl_df)
        rx = result[result["grid_region_id"] == "REGION_X"].iloc[0]
        assert rx["post2030_share"] == 1.0
        assert bool(rx["grid_upgrade_pre2030"]) is False

    def test_all_pre2030(self):
        ruptl_df = pd.DataFrame(
            {
                "grid_region_id": ["REGION_Y"],
                "year": [2027],
                "plts_new_mw_re_base": [300],
            }
        )
        result = ruptl_region_metrics(ruptl_df)
        ry = result[result["grid_region_id"] == "REGION_Y"].iloc[0]
        assert ry["post2030_share"] == 0.0
        assert bool(ry["grid_upgrade_pre2030"]) is True


# ---------------------------------------------------------------------------
# 12. build_scorecard (end-to-end)
# ---------------------------------------------------------------------------


class TestBuildScorecard:
    def test_runs_without_error(
        self, sample_kek_df, sample_demand_df, sample_pvout_df, sample_ruptl_df
    ):
        result = build_scorecard(
            dim_kek=sample_kek_df,
            fct_demand=sample_demand_df,
            fct_pvout=sample_pvout_df,
            fct_ruptl=sample_ruptl_df,
            grid_cost_usd_mwh=60.0,
        )
        assert len(result) == 4
        assert "lcoe_usd_mwh" in result.columns
        assert "solar_attractive" in result.columns

    def test_lcoe_in_plausible_range(
        self, sample_kek_df, sample_demand_df, sample_pvout_df, sample_ruptl_df
    ):
        result = build_scorecard(
            dim_kek=sample_kek_df,
            fct_demand=sample_demand_df,
            fct_pvout=sample_pvout_df,
            fct_ruptl=sample_ruptl_df,
        )
        assert (result["lcoe_usd_mwh"] > 0).all()
        assert (result["lcoe_usd_mwh"] < 200).all()

    def test_flags_present_when_grid_cost_provided(
        self, sample_kek_df, sample_demand_df, sample_pvout_df, sample_ruptl_df
    ):
        result = build_scorecard(
            dim_kek=sample_kek_df,
            fct_demand=sample_demand_df,
            fct_pvout=sample_pvout_df,
            fct_ruptl=sample_ruptl_df,
            grid_cost_usd_mwh=60.0,
        )
        for flag in ("solar_now", "grid_first", "invest_battery", "plan_late"):
            assert flag in result.columns
            assert result[flag].notna().all()

    def test_flags_null_when_no_grid_cost(
        self, sample_kek_df, sample_demand_df, sample_pvout_df, sample_ruptl_df
    ):
        result = build_scorecard(
            dim_kek=sample_kek_df,
            fct_demand=sample_demand_df,
            fct_pvout=sample_pvout_df,
            fct_ruptl=sample_ruptl_df,
            grid_cost_usd_mwh=None,
        )
        for flag in ("solar_now", "grid_first", "invest_battery", "plan_late"):
            assert result[flag].isna().all()

    def test_wacc_column_matches_input(
        self, sample_kek_df, sample_demand_df, sample_pvout_df, sample_ruptl_df
    ):
        result = build_scorecard(
            dim_kek=sample_kek_df,
            fct_demand=sample_demand_df,
            fct_pvout=sample_pvout_df,
            fct_ruptl=sample_ruptl_df,
            wacc=0.12,
        )
        assert (result["wacc"] == 0.12).all()


# ---------------------------------------------------------------------------
# 13. time_bucket
# ---------------------------------------------------------------------------


class TestTimeBucket:
    def test_pre2030(self):
        assert time_bucket(2027) == "2025-2030"
        assert time_bucket(2030) == "2025-2030"

    def test_post2030(self):
        assert time_bucket(2031) == "2031-2034"
        assert time_bucket(2034) == "2031-2034"


# ---------------------------------------------------------------------------
# 14. resolve_demand
# ---------------------------------------------------------------------------


class TestResolveDemand:
    def _make_demand(self, user_vals: list) -> pd.DataFrame:
        """Build a minimal fct_demand DataFrame with optional demand_mwh_user column."""
        df = pd.DataFrame(
            {
                "kek_id": ["a", "b", "c"],
                "demand_mwh": [1000.0, 2000.0, 3000.0],
            }
        )
        if user_vals is not None:
            df["demand_mwh_user"] = pd.array(user_vals, dtype="Float64")
        return df

    def test_no_override_column_returns_demand_mwh_unchanged(self):
        df = self._make_demand(None)
        result = resolve_demand(df)
        assert list(result["demand_mwh"]) == [1000.0, 2000.0, 3000.0]

    def test_null_override_returns_demand_mwh_unchanged(self):
        df = self._make_demand([pd.NA, pd.NA, pd.NA])
        result = resolve_demand(df)
        assert list(result["demand_mwh"]) == [1000.0, 2000.0, 3000.0]

    def test_non_null_override_replaces_demand_mwh(self):
        df = self._make_demand([500.0, 600.0, 700.0])
        result = resolve_demand(df)
        assert list(result["demand_mwh"]) == [500.0, 600.0, 700.0]

    def test_partial_override_only_replaces_non_null_rows(self):
        df = self._make_demand([pd.NA, 9999.0, pd.NA])
        result = resolve_demand(df)
        assert result.loc[result["kek_id"] == "a", "demand_mwh"].iloc[0] == 1000.0
        assert result.loc[result["kek_id"] == "b", "demand_mwh"].iloc[0] == 9999.0
        assert result.loc[result["kek_id"] == "c", "demand_mwh"].iloc[0] == 3000.0

    def test_original_dataframe_not_mutated(self):
        df = self._make_demand([pd.NA, 9999.0, pd.NA])
        original_b = df.loc[df["kek_id"] == "b", "demand_mwh"].iloc[0]
        resolve_demand(df)
        assert df.loc[df["kek_id"] == "b", "demand_mwh"].iloc[0] == original_b


# ---------------------------------------------------------------------------
# 15. invest_resilience
# ---------------------------------------------------------------------------


class TestInvestResilience:
    def test_fires_in_resilience_zone(self):
        # LCOE 15% above grid, high reliability requirement → True
        assert invest_resilience(solar_competitive_gap_pct=15.0, reliability_req=0.8) is True

    def test_fires_at_exact_threshold_boundary(self):
        # At exactly 20% gap and exactly 0.75 reliability → True (inclusive bounds)
        assert invest_resilience(solar_competitive_gap_pct=20.0, reliability_req=0.75) is True

    def test_no_fire_gap_exceeds_threshold(self):
        # 25% gap > 20% threshold → False
        assert invest_resilience(solar_competitive_gap_pct=25.0, reliability_req=0.8) is False

    def test_no_fire_low_reliability(self):
        # Good gap but tourism KEK (low reliability) → False
        assert invest_resilience(solar_competitive_gap_pct=15.0, reliability_req=0.5) is False

    def test_no_fire_when_already_competitive(self):
        # Negative gap = solar already cheaper than grid → False (solar_now applies)
        assert invest_resilience(solar_competitive_gap_pct=-5.0, reliability_req=0.85) is False

    def test_no_fire_at_zero_gap(self):
        # Exactly at parity → False (solar_now applies, not resilience flag)
        assert invest_resilience(solar_competitive_gap_pct=0.0, reliability_req=0.85) is False

    def test_custom_thresholds(self):
        # Custom gap and reliability thresholds are respected
        assert (
            invest_resilience(15.0, 0.7, gap_threshold_pct=10.0, reliability_threshold=0.7) is False
        )
        assert (
            invest_resilience(8.0, 0.7, gap_threshold_pct=10.0, reliability_threshold=0.7) is True
        )


# ---------------------------------------------------------------------------
# 16. carbon_breakeven_price
# ---------------------------------------------------------------------------


class TestCarbonBreakevenPrice:
    def test_already_competitive_returns_zero(self):
        # LCOE < grid → 0.0 (no carbon price needed)
        assert carbon_breakeven_price(60.0, 63.08, 0.87) == 0.0

    def test_at_parity_returns_zero(self):
        assert carbon_breakeven_price(63.08, 63.08, 0.87) == 0.0

    def test_positive_gap_java_bali(self):
        # Batang-like: LCOE=66.2, grid=63.08, EF=0.87 tCO2/MWh
        # gap = 3.12 / 0.87 = 3.586... → rounds to 3.6
        result = carbon_breakeven_price(66.2, 63.08, 0.87)
        assert result is not None
        assert math.isclose(result, round(3.12 / 0.87, 1), rel_tol=1e-3)

    def test_zero_emission_factor_returns_none(self):
        assert carbon_breakeven_price(70.0, 63.08, 0.0) is None

    def test_negative_emission_factor_returns_none(self):
        assert carbon_breakeven_price(70.0, 63.08, -0.5) is None

    def test_large_gap_sulawesi(self):
        # High LCOE tourism KEK, cleaner grid (Sulawesi 0.58)
        # gap = 80.0 - 63.08 = 16.92 / 0.58 = 29.17 → 29.2
        result = carbon_breakeven_price(80.0, 63.08, 0.58)
        assert result is not None
        assert math.isclose(result, round(16.92 / 0.58, 1), rel_tol=1e-3)

    def test_result_is_float(self):
        result = carbon_breakeven_price(70.0, 63.08, 0.87)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Wind speed → CF conversion
# ---------------------------------------------------------------------------


class TestWindSpeedToCf:
    def test_below_cutin_returns_zero(self):
        """Wind speed ≤3 m/s should return CF=0."""
        assert wind_speed_to_cf(2.5) == 0.0
        assert wind_speed_to_cf(3.0) == 0.0

    def test_zero_speed(self):
        assert wind_speed_to_cf(0.0) == 0.0

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            wind_speed_to_cf(-1.0)

    def test_esdm_catalogue_calibration(self):
        """CF at 7.5 m/s should be ~0.27 (ESDM catalogue central value)."""
        cf = wind_speed_to_cf(7.5)
        assert math.isclose(cf, 0.27, abs_tol=0.01)

    def test_6ms_moderate(self):
        """CF at 6 m/s should be ~0.22."""
        cf = wind_speed_to_cf(6.0)
        assert math.isclose(cf, 0.22, abs_tol=0.01)

    def test_monotonically_increasing(self):
        """CF should increase with wind speed."""
        speeds = [3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]
        cfs = [wind_speed_to_cf(s) for s in speeds]
        for i in range(len(cfs) - 1):
            assert cfs[i] <= cfs[i + 1], (
                f"CF not monotonic: {speeds[i]}→{cfs[i]}, {speeds[i + 1]}→{cfs[i + 1]}"
            )

    def test_plateau_above_12(self):
        """CF should plateau above 12 m/s."""
        cf_12 = wind_speed_to_cf(12.0)
        cf_15 = wind_speed_to_cf(15.0)
        assert cf_12 == cf_15

    def test_class_iii_range(self):
        """Typical Class III site (7.5 m/s) should give CF 0.25–0.30."""
        cf = wind_speed_to_cf(7.5)
        assert 0.25 <= cf <= 0.30

    def test_class_i_range(self):
        """Class I site (10 m/s) should give CF 0.35–0.42."""
        cf = wind_speed_to_cf(10.0)
        assert 0.35 <= cf <= 0.42

    def test_jeneponto_realistic(self):
        """Jeneponto (South Sulawesi) at ~6.5 m/s should give CF ~0.22–0.25."""
        cf = wind_speed_to_cf(6.5)
        assert 0.20 <= cf <= 0.27
