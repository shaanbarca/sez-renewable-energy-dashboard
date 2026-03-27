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
    geas_baseline_allocation,
    geas_policy_allocation,
    is_solar_attractive,
    lcoe_solar,
    lcoe_solar_with_firming,
    pvout_daily_to_annual,
    resolve_demand,
    ruptl_region_metrics,
    solar_competitive_gap,
    time_bucket,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_kek_df():
    return pd.DataFrame({
        "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
        "kek_name": ["Kendal", "Bitung", "Sungai Liat", "Arun"],
        "province": ["Central Java", "North Sulawesi", "Bangka Belitung", "Aceh"],
        "grid_region_id": ["JAVA_BALI", "SULAWESI", "SUMATERA", "SUMATERA"],
        "reliability_req": [0.4, 0.8, 0.6, 0.9],
    })


@pytest.fixture
def sample_demand_df():
    return pd.DataFrame({
        "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
        "year": [2030, 2030, 2030, 2030],
        "demand_mwh": [800_000, 250_000, 120_000, 600_000],
    })


@pytest.fixture
def sample_pvout_df():
    # Annual values (kWh/kWp/year)
    return pd.DataFrame({
        "kek_id": ["KEK_A", "KEK_B", "KEK_C", "KEK_D"],
        "pvout_centroid": [1650, 1505, 1420, 1550],
        "pvout_best_50km": [1780, 1620, 1500, 1670],
    })


@pytest.fixture
def sample_ruptl_df():
    return pd.DataFrame({
        "grid_region_id": ["JAVA_BALI", "JAVA_BALI", "SULAWESI", "SULAWESI", "SUMATERA", "SUMATERA"],
        "year": [2028, 2032, 2029, 2033, 2027, 2032],
        "plts_new_mw_re_base": [800, 2500, 100, 600, 300, 1800],
    })


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
            assert lcoe_solar_with_firming(700, 12, 0.09, 25, cf, adder) > lcoe_solar(700, 12, 0.09, 25, cf)


# ---------------------------------------------------------------------------
# 6. Solar competitive gap
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
            grid_upgrade_pre2030=True,   # grid ready
            reliability_req=0.4,          # below firming threshold
            green_share_geas=0.35,        # above 0.30
            post2030_share=0.30,          # below plan_late threshold
        )
        assert flags["solar_now"] is True
        assert flags["grid_first"] is False
        assert flags["firming_needed"] is False
        assert flags["plan_late"] is False

    def test_grid_first(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=False,   # grid NOT ready
            reliability_req=0.4,
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["grid_first"] is True
        assert flags["solar_now"] is False  # blocked by grid_first

    def test_firming_needed(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.80,         # at threshold (0.75)
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["firming_needed"] is True

    def test_firming_below_threshold(self):
        flags = action_flags(
            solar_attractive=True,
            grid_upgrade_pre2030=True,
            reliability_req=0.74,         # just below threshold
            green_share_geas=0.5,
            post2030_share=0.3,
        )
        assert flags["firming_needed"] is False

    def test_plan_late(self):
        flags = action_flags(
            solar_attractive=False,
            grid_upgrade_pre2030=True,
            reliability_req=0.4,
            green_share_geas=0.1,
            post2030_share=0.65,          # above 0.60 threshold
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
        assert flags["firming_needed"] is False

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
            green_share_geas=0.25,        # below 0.30 threshold
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


# ---------------------------------------------------------------------------
# 9. GEAS baseline allocation
# ---------------------------------------------------------------------------

class TestGeasBaselineAllocation:
    def test_pro_rata_within_region(self, sample_kek_df, sample_ruptl_df):
        kek_demand = pd.DataFrame({
            "kek_id": ["KEK_C", "KEK_D"],
            "grid_region_id": ["SUMATERA", "SUMATERA"],
            "demand_mwh": [120_000, 600_000],
        })
        result = geas_baseline_allocation(kek_demand, sample_ruptl_df)

        # KEK_D should receive 600/(120+600) = 83.3% of regional allocation
        kek_c = result[result["kek_id"] == "KEK_C"].iloc[0]
        kek_d = result[result["kek_id"] == "KEK_D"].iloc[0]
        ratio = kek_d["geas_alloc_mwh"] / kek_c["geas_alloc_mwh"]
        assert math.isclose(ratio, 600_000 / 120_000)

    def test_green_share_capped_at_1(self, sample_ruptl_df):
        # Tiny demand => GEAS supply >> demand => green_share = 1.0
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_X"],
            "grid_region_id": ["JAVA_BALI"],
            "demand_mwh": [1.0],   # 1 MWh — trivially covered
        })
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas"] == 1.0

    def test_no_ruptl_in_region_gives_zero(self):
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_X"],
            "grid_region_id": ["UNKNOWN_REGION"],
            "demand_mwh": [500_000],
        })
        ruptl_df = pd.DataFrame({
            "grid_region_id": ["JAVA_BALI"],
            "year": [2028],
            "plts_new_mw_re_base": [500],
        })
        result = geas_baseline_allocation(kek_df, ruptl_df)
        assert result.iloc[0]["geas_alloc_mwh"] == 0.0
        assert result.iloc[0]["green_share_geas"] == 0.0

    def test_total_allocation_equals_supply(self, sample_ruptl_df):
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_C", "KEK_D"],
            "grid_region_id": ["SUMATERA", "SUMATERA"],
            "demand_mwh": [120_000, 600_000],
        })
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        # Total allocated should equal SUMATERA pre-2030 supply (300 MW * 8760 * 0.20)
        expected_supply = 300 * HOURS_PER_YEAR * 0.20
        total_alloc = result["geas_alloc_mwh"].sum()
        assert math.isclose(total_alloc, expected_supply, rel_tol=1e-6)

    def test_zero_demand_returns_zero_not_nan(self, sample_ruptl_df):
        # Regression: demand=0 previously produced NaN via 0/0 division
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_X"],
            "grid_region_id": ["JAVA_BALI"],
            "demand_mwh": [0],
        })
        result = geas_baseline_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas"] == 0.0
        assert not math.isnan(result.iloc[0]["green_share_geas"])


# ---------------------------------------------------------------------------
# 10. GEAS policy allocation
# ---------------------------------------------------------------------------

class TestGeasPolicyAllocation:
    def test_policy_ge_baseline_for_high_pvout(self, sample_ruptl_df):
        # High-pvout KEK should get >= baseline share in policy scenario
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_C", "KEK_D"],
            "grid_region_id": ["SUMATERA", "SUMATERA"],
            "demand_mwh": [120_000, 600_000],
            "pvout_best_50km": [1400, 1700],  # KEK_D has higher PVOUT
        })
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
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_A"],
            "grid_region_id": ["JAVA_BALI"],
            "demand_mwh": [800_000],
            "pvout_best_50km": [1780],
        })
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        baseline = geas_baseline_allocation(
            kek_df[["kek_id", "grid_region_id", "demand_mwh"]], sample_ruptl_df
        )
        assert result.iloc[0]["geas_alloc_mwh_policy"] >= baseline.iloc[0]["geas_alloc_mwh"]

    def test_green_share_capped_at_1(self, sample_ruptl_df):
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_X"],
            "grid_region_id": ["JAVA_BALI"],
            "demand_mwh": [1.0],
            "pvout_best_50km": [1750],
        })
        result = geas_policy_allocation(kek_df, sample_ruptl_df)
        assert result.iloc[0]["green_share_geas_policy"] == 1.0

    def test_zero_demand_returns_zero_not_nan(self, sample_ruptl_df):
        # Regression: demand=0 previously produced NaN via 0/0 division
        kek_df = pd.DataFrame({
            "kek_id": ["KEK_X"],
            "grid_region_id": ["JAVA_BALI"],
            "demand_mwh": [0],
            "pvout_best_50km": [1750],
        })
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
        ruptl_df = pd.DataFrame({
            "grid_region_id": ["REGION_X"],
            "year": [2035],
            "plts_new_mw_re_base": [500],
        })
        result = ruptl_region_metrics(ruptl_df)
        rx = result[result["grid_region_id"] == "REGION_X"].iloc[0]
        assert rx["post2030_share"] == 1.0
        assert bool(rx["grid_upgrade_pre2030"]) is False

    def test_all_pre2030(self):
        ruptl_df = pd.DataFrame({
            "grid_region_id": ["REGION_Y"],
            "year": [2027],
            "plts_new_mw_re_base": [300],
        })
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
        for flag in ("solar_now", "grid_first", "firming_needed", "plan_late"):
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
        for flag in ("solar_now", "grid_first", "firming_needed", "plan_late"):
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
        df = pd.DataFrame({
            "kek_id": ["a", "b", "c"],
            "demand_mwh": [1000.0, 2000.0, 3000.0],
        })
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
