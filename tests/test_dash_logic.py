"""Tests for src/dash/logic.py — live LCOE computation.

Verifies that compute_lcoe_live() produces the same results as the
precomputed pipeline at default assumptions, and that changing
assumptions produces expected directional effects.
"""

import pandas as pd
import pytest

from src.dash.logic import (
    UserAssumptions,
    UserThresholds,
    compute_lcoe_live,
    compute_scorecard_live,
    get_default_assumptions,
    get_default_thresholds,
)
from src.model.basic_model import (
    lcoe_solar,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_resource_df():
    """Minimal resource DataFrame for 3 KEKs."""
    return pd.DataFrame(
        {
            "kek_id": ["kek-kendal", "kek-mandalika", "kek-sorong"],
            "pvout_centroid": [1550.0, 1650.0, 1400.0],
            "pvout_best_50km": [1650.0, 1730.0, 1500.0],
            "dist_to_nearest_substation_km": [15.0, 25.0, 40.0],
            "grid_region_id": ["JAVA_BALI", "NTB", "PAPUA"],
            "reliability_req": [0.8, 0.4, 0.6],
            "max_captive_capacity_mwp": [50.0, 30.0, 25.0],
            "green_share_geas": [0.35, 0.10, 0.05],
        }
    )


@pytest.fixture
def sample_ruptl_metrics():
    return pd.DataFrame(
        {
            "grid_region_id": ["JAVA_BALI", "NTB", "PAPUA"],
            "post2030_share": [0.45, 0.70, 0.90],
            "grid_upgrade_pre2030": [True, True, False],
        }
    )


@pytest.fixture
def sample_demand_df():
    return pd.DataFrame(
        {
            "kek_id": ["kek-kendal", "kek-mandalika", "kek-sorong"],
            "demand_mwh": [100_000.0, 50_000.0, 20_000.0],
        }
    )


@pytest.fixture
def sample_grid_df():
    return pd.DataFrame(
        {
            "grid_region_id": ["JAVA_BALI", "NTB", "PAPUA"],
            "grid_emission_factor_t_co2_mwh": [0.80, 1.27, 0.56],
        }
    )


# ---------------------------------------------------------------------------
# UserAssumptions / UserThresholds
# ---------------------------------------------------------------------------


class TestUserAssumptions:
    def test_defaults_match_assumptions_py(self):
        a = get_default_assumptions()
        assert a.capex_usd_per_kw == 960.0
        assert a.lifetime_yr == 27
        assert a.wacc_pct == 10.0
        assert a.fom_usd_per_kw_yr == 7.5
        assert a.connection_cost_per_kw_km == 5.0
        assert a.grid_connection_fixed_per_kw == 80.0

    def test_wacc_decimal(self):
        a = UserAssumptions(wacc_pct=8.0)
        assert a.wacc_decimal == 0.08

    def test_capex_bands(self):
        a = UserAssumptions(capex_usd_per_kw=1000.0)
        assert a.capex_low == 875.0
        assert a.capex_high == 1125.0

    def test_round_trip_serialisation(self):
        a = UserAssumptions(capex_usd_per_kw=840.0, wacc_pct=8.0)
        d = a.to_dict()
        b = UserAssumptions.from_dict(d)
        assert b.capex_usd_per_kw == 840.0
        assert b.wacc_pct == 8.0

    def test_from_dict_ignores_extra_keys(self):
        d = {"capex_usd_per_kw": 900.0, "unknown_key": 42}
        a = UserAssumptions.from_dict(d)
        assert a.capex_usd_per_kw == 900.0


class TestUserThresholds:
    def test_defaults(self):
        t = get_default_thresholds()
        assert t.pvout_threshold == 1550.0
        assert t.plan_late_threshold == 0.60
        assert t.geas_threshold == 0.30
        assert t.resilience_gap_pct == 20.0

    def test_round_trip(self):
        t = UserThresholds(pvout_threshold=1400.0)
        d = t.to_dict()
        t2 = UserThresholds.from_dict(d)
        assert t2.pvout_threshold == 1400.0


# ---------------------------------------------------------------------------
# compute_lcoe_live
# ---------------------------------------------------------------------------


class TestComputeLcoeLive:
    def test_output_shape(self, sample_resource_df):
        """Should produce 2 rows per KEK (within_boundary + grid_connected_solar)."""
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        assert len(result) == 6  # 3 KEKs × 2 scenarios

    def test_scenarios_present(self, sample_resource_df):
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        scenarios = set(result["scenario"])
        assert scenarios == {"within_boundary", "grid_connected_solar"}

    def test_within_boundary_no_connection_cost(self, sample_resource_df):
        """Within-boundary should have zero connection cost."""
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        wb = result[result["scenario"] == "within_boundary"]
        assert (wb["connection_cost_per_kw"] == 0.0).all()

    def test_grid_connected_has_connection_cost(self, sample_resource_df):
        """Grid-connected solar should include connection cost."""
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        gc = result[result["scenario"] == "grid_connected_solar"]
        assert (gc["connection_cost_per_kw"] > 0.0).all()

    def test_lcoe_matches_basic_model(self, sample_resource_df):
        """Live LCOE at defaults should match direct basic_model.lcoe_solar() call."""
        assumptions = get_default_assumptions()
        result = compute_lcoe_live(sample_resource_df, assumptions)
        wb = result[result["scenario"] == "within_boundary"]

        # Check kek-kendal (pvout_centroid=1550)
        kendal = wb[wb["kek_id"] == "kek-kendal"].iloc[0]
        cf = 1550.0 / 8760.0
        expected = lcoe_solar(960.0, 7.5, 0.10, 27, cf)
        assert abs(kendal["lcoe_mid_usd_mwh"] - round(expected, 2)) < 0.01

    def test_lower_capex_lowers_lcoe(self, sample_resource_df):
        """Reducing CAPEX should reduce LCOE."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        low_capex = UserAssumptions(capex_usd_per_kw=800.0)
        low_result = compute_lcoe_live(sample_resource_df, low_capex)

        wb_default = default_result[default_result["scenario"] == "within_boundary"]
        wb_low = low_result[low_result["scenario"] == "within_boundary"]

        for kek_id in sample_resource_df["kek_id"]:
            default_val = wb_default[wb_default["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            low_val = wb_low[wb_low["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            assert low_val < default_val, f"LCOE should decrease with lower CAPEX for {kek_id}"

    def test_longer_lifetime_lowers_lcoe(self, sample_resource_df):
        """Longer lifetime should reduce LCOE (lower CRF)."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        long_life = UserAssumptions(lifetime_yr=30)
        long_result = compute_lcoe_live(sample_resource_df, long_life)

        wb_default = default_result[default_result["scenario"] == "within_boundary"]
        wb_long = long_result[long_result["scenario"] == "within_boundary"]

        for kek_id in sample_resource_df["kek_id"]:
            default_val = wb_default[wb_default["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            long_val = wb_long[wb_long["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            assert long_val < default_val, f"LCOE should decrease with longer lifetime for {kek_id}"

    def test_higher_wacc_raises_lcoe(self, sample_resource_df):
        """Higher WACC should increase LCOE (higher CRF)."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        high_wacc = UserAssumptions(wacc_pct=14.0)
        high_result = compute_lcoe_live(sample_resource_df, high_wacc)

        wb_default = default_result[default_result["scenario"] == "within_boundary"]
        wb_high = high_result[high_result["scenario"] == "within_boundary"]

        for kek_id in sample_resource_df["kek_id"]:
            d = wb_default[wb_default["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            h = wb_high[wb_high["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            assert h > d, f"LCOE should increase with higher WACC for {kek_id}"

    def test_lcoe_band_ordering(self, sample_resource_df):
        """low < mid < high for both scenarios."""
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        for _, row in result.iterrows():
            if pd.notna(row["lcoe_mid_usd_mwh"]):
                assert row["lcoe_low_usd_mwh"] < row["lcoe_mid_usd_mwh"]
                assert row["lcoe_mid_usd_mwh"] < row["lcoe_high_usd_mwh"]

    def test_grid_connected_higher_than_within_boundary(self, sample_resource_df):
        """Grid-connected LCOE should be >= within-boundary LCOE (connection cost adds cost)."""
        result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        wb = result[result["scenario"] == "within_boundary"].set_index("kek_id")
        gc = result[result["scenario"] == "grid_connected_solar"].set_index("kek_id")

        for kek_id in sample_resource_df["kek_id"]:
            wb_lcoe = wb.loc[kek_id, "lcoe_mid_usd_mwh"]
            gc_lcoe = gc.loc[kek_id, "lcoe_mid_usd_mwh"]
            if pd.notna(wb_lcoe) and pd.notna(gc_lcoe):
                assert gc_lcoe >= wb_lcoe, f"Grid-connected should be >= within for {kek_id}"


# ---------------------------------------------------------------------------
# compute_scorecard_live
# ---------------------------------------------------------------------------


class TestComputeScorecardLive:
    def test_output_shape(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """One row per KEK."""
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        assert len(result) == 3

    def test_has_required_columns(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        required = [
            "kek_id",
            "lcoe_mid_usd_mwh",
            "solar_competitive_gap_pct",
            "solar_now",
            "grid_first",
            "invest_battery",
            "plan_late",
            "invest_resilience",
            "carbon_breakeven_usd_tco2",
            "project_viable",
        ]
        for col in required:
            assert col in result.columns, f"Missing column: {col}"

    def test_plan_late_respects_user_threshold(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Sorong has post2030_share=0.90. Should be plan_late at default (0.60)
        but NOT plan_late at threshold 0.95."""
        default = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        sorong_default = default[default["kek_id"] == "kek-sorong"].iloc[0]
        assert bool(sorong_default["plan_late"]) is True

        high_threshold = UserThresholds(plan_late_threshold=0.95)
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            high_threshold,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        sorong_high = result[result["kek_id"] == "kek-sorong"].iloc[0]
        assert bool(sorong_high["plan_late"]) is False

    def test_lower_capex_improves_gap(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Lower CAPEX should reduce the competitive gap (make solar more attractive)."""
        default = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        low_capex = UserAssumptions(capex_usd_per_kw=700.0)
        result = compute_scorecard_live(
            sample_resource_df,
            low_capex,
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        for kek_id in sample_resource_df["kek_id"]:
            gap_default = default[default["kek_id"] == kek_id]["solar_competitive_gap_pct"].iloc[0]
            gap_low = result[result["kek_id"] == kek_id]["solar_competitive_gap_pct"].iloc[0]
            if pd.notna(gap_default) and pd.notna(gap_low):
                assert gap_low < gap_default, f"Gap should decrease with lower CAPEX for {kek_id}"

    def test_carbon_breakeven_present(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Carbon breakeven should be computed when emission factor is available."""
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        # All 3 KEKs have emission factors, so carbon_breakeven should be non-null
        assert result["carbon_breakeven_usd_tco2"].notna().all()


# ---------------------------------------------------------------------------
# H4: Infrastructure cost wiring tests
# ---------------------------------------------------------------------------


class TestInfrastructureCosts:
    def test_higher_fom_raises_lcoe(self, sample_resource_df):
        """Increasing FOM should increase LCOE."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        high_fom = UserAssumptions(fom_usd_per_kw_yr=15.0)
        high_result = compute_lcoe_live(sample_resource_df, high_fom)

        wb_default = default_result[default_result["scenario"] == "within_boundary"]
        wb_high = high_result[high_result["scenario"] == "within_boundary"]

        for kek_id in sample_resource_df["kek_id"]:
            d = wb_default[wb_default["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            h = wb_high[wb_high["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            assert h > d, f"LCOE should increase with higher FOM for {kek_id}"

    def test_higher_connection_cost_raises_grid_connected_only(self, sample_resource_df):
        """Higher connection cost should raise grid_connected_solar LCOE but not within_boundary."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        high_cc = UserAssumptions(connection_cost_per_kw_km=12.0)
        high_result = compute_lcoe_live(sample_resource_df, high_cc)

        # Within-boundary should be unchanged
        wb_d = default_result[default_result["scenario"] == "within_boundary"]
        wb_h = high_result[high_result["scenario"] == "within_boundary"]
        for kek_id in sample_resource_df["kek_id"]:
            assert (
                wb_d[wb_d["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
                == wb_h[wb_h["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            )

        # Grid-connected should increase
        gc_d = default_result[default_result["scenario"] == "grid_connected_solar"]
        gc_h = high_result[high_result["scenario"] == "grid_connected_solar"]
        for kek_id in sample_resource_df["kek_id"]:
            d = gc_d[gc_d["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            h = gc_h[gc_h["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            if pd.notna(d) and pd.notna(h):
                assert h > d, (
                    f"Grid-connected LCOE should increase with higher connection cost for {kek_id}"
                )

    def test_higher_fixed_connection_raises_grid_connected_only(self, sample_resource_df):
        """Higher fixed connection cost should raise grid_connected_solar LCOE only."""
        default_result = compute_lcoe_live(sample_resource_df, get_default_assumptions())
        high_fixed = UserAssumptions(grid_connection_fixed_per_kw=200.0)
        high_result = compute_lcoe_live(sample_resource_df, high_fixed)

        gc_d = default_result[default_result["scenario"] == "grid_connected_solar"]
        gc_h = high_result[high_result["scenario"] == "grid_connected_solar"]
        for kek_id in sample_resource_df["kek_id"]:
            d = gc_d[gc_d["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            h = gc_h[gc_h["kek_id"] == kek_id]["lcoe_mid_usd_mwh"].iloc[0]
            if pd.notna(d) and pd.notna(h):
                assert h > d, (
                    f"Grid-connected LCOE should increase with higher fixed cost for {kek_id}"
                )

    def test_idr_usd_rate_affects_grid_benchmark(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Weaker rupiah (higher IDR/USD) should lower grid benchmark in USD terms."""
        default = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        weak_rupiah = UserAssumptions(idr_usd_rate=17_000.0)
        result = compute_scorecard_live(
            sample_resource_df,
            weak_rupiah,
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        # Grid cost in USD should decrease when rupiah weakens
        assert result.iloc[0]["grid_cost_usd_mwh"] < default.iloc[0]["grid_cost_usd_mwh"]

    def test_utilization_slider_changes_capacity_assessment(
        self, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Changing substation_utilization_pct must change capacity_assessment live.

        Thresholds: green > 2× solar, yellow 0.5×–2×, red < 0.5×.
        Substation 200 MVA, solar 50 MWp:
          At 0.10 util: available = 200 × 0.90 = 180 MVA, ratio = 3.6 → green
          At 0.90 util: available = 200 × 0.10 = 20 MVA, ratio = 0.4 → red
        """
        resource_df = pd.DataFrame(
            {
                "kek_id": ["kek-kendal"],
                "pvout_centroid": [1550.0],
                "pvout_best_50km": [1650.0],
                "dist_to_nearest_substation_km": [5.0],
                "grid_region_id": ["JAVA_BALI"],
                "reliability_req": [0.6],
                "max_captive_capacity_mwp": [50.0],
                "green_share_geas": [0.35],
                "nearest_substation_capacity_mva": [200.0],
                "has_internal_substation": [False],
                "dist_solar_to_nearest_substation_km": [3.0],
            }
        )
        low_util = compute_scorecard_live(
            resource_df,
            UserAssumptions(substation_utilization_pct=0.10),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        high_util = compute_scorecard_live(
            resource_df,
            UserAssumptions(substation_utilization_pct=0.90),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        low_row = low_util.iloc[0]
        high_row = high_util.iloc[0]

        # Low utilization → plenty of capacity → green
        assert low_row["capacity_assessment"] == "green"
        # High utilization → overloaded → red
        assert high_row["capacity_assessment"] == "red"
        # Available capacity should decrease with higher utilization
        assert low_row["available_capacity_mva"] > high_row["available_capacity_mva"]

    def test_utilization_slider_changes_lcoe(
        self, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """High utilization should raise grid-connected LCOE via substation upgrade cost.

        Substation 60 MVA, solar 50 MWp:
          At 0.10 util: available = 54 MVA > 50 MWp → no upgrade cost
          At 0.90 util: available = 6 MVA < 50 MWp → upgrade cost added → LCOE rises
        """
        resource_df = pd.DataFrame(
            {
                "kek_id": ["kek-kendal"],
                "pvout_centroid": [1550.0],
                "pvout_best_50km": [1650.0],
                "dist_to_nearest_substation_km": [5.0],
                "grid_region_id": ["JAVA_BALI"],
                "reliability_req": [0.6],
                "max_captive_capacity_mwp": [50.0],
                "green_share_geas": [0.35],
                "nearest_substation_capacity_mva": [60.0],
                "has_internal_substation": [False],
                "dist_solar_to_nearest_substation_km": [3.0],
            }
        )
        low_util = compute_scorecard_live(
            resource_df,
            UserAssumptions(substation_utilization_pct=0.10),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        high_util = compute_scorecard_live(
            resource_df,
            UserAssumptions(substation_utilization_pct=0.90),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        low_lcoe = low_util.iloc[0]["lcoe_mid_usd_mwh"]
        high_lcoe = high_util.iloc[0]["lcoe_mid_usd_mwh"]

        # High utilization → substation can't absorb solar → upgrade cost → higher LCOE
        assert high_lcoe > low_lcoe, (
            f"Primary LCOE should increase with utilization: "
            f"low_util={low_lcoe}, high_util={high_lcoe}"
        )

    def test_battery_adder_applied_when_invest_battery(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """KEKs with invest_battery=True should have non-zero battery adder."""
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        battery_rows = result[result["invest_battery"]]
        if len(battery_rows) > 0:
            assert (battery_rows["battery_adder_usd_mwh"] > 0).all()
            for _, row in battery_rows.iterrows():
                if pd.notna(row["lcoe_mid_usd_mwh"]):
                    assert row["lcoe_with_battery_usd_mwh"] > row["lcoe_mid_usd_mwh"]

    def test_battery_adder_zero_when_not_needed(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """KEKs with invest_battery=False should have zero battery adder."""
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        no_battery = result[~result["invest_battery"]]
        assert (no_battery["battery_adder_usd_mwh"] == 0.0).all()

    def test_scorecard_has_battery_columns(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Scorecard output should include battery adder columns."""
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            get_default_thresholds(),
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        assert "battery_adder_usd_mwh" in result.columns
        assert "lcoe_with_battery_usd_mwh" in result.columns


# ---------------------------------------------------------------------------
# H5: Flag threshold wiring tests
# ---------------------------------------------------------------------------


class TestThresholdWiring:
    def test_geas_threshold_affects_solar_now(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Lowering GEAS threshold should allow more KEKs to be solar_now."""
        # Use low CAPEX to make solar attractive for all KEKs
        low_capex = UserAssumptions(capex_usd_per_kw=600.0)
        strict = UserThresholds(geas_threshold=0.50)
        lenient = UserThresholds(geas_threshold=0.05)

        strict_result = compute_scorecard_live(
            sample_resource_df,
            low_capex,
            strict,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        lenient_result = compute_scorecard_live(
            sample_resource_df,
            low_capex,
            lenient,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        # Lenient threshold should produce >= solar_now count
        assert lenient_result["solar_now"].sum() >= strict_result["solar_now"].sum()

    def test_reliability_threshold_affects_invest_battery(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Lowering reliability threshold should flag more KEKs as invest_battery."""
        low_capex = UserAssumptions(capex_usd_per_kw=600.0)
        strict = UserThresholds(reliability_threshold=0.90)
        lenient = UserThresholds(reliability_threshold=0.30)

        strict_result = compute_scorecard_live(
            sample_resource_df,
            low_capex,
            strict,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        lenient_result = compute_scorecard_live(
            sample_resource_df,
            low_capex,
            lenient,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        # Lower threshold means more KEKs meet it, so more invest_battery
        assert lenient_result["invest_battery"].sum() >= strict_result["invest_battery"].sum()

    def test_extreme_thresholds_no_crash(
        self, sample_resource_df, sample_ruptl_metrics, sample_demand_df, sample_grid_df
    ):
        """Extreme threshold values should not cause crashes."""
        extreme = UserThresholds(
            pvout_threshold=0.0,
            plan_late_threshold=0.0,
            geas_threshold=0.0,
            resilience_gap_pct=0.0,
            min_viable_mwp=0.0,
            reliability_threshold=0.0,
        )
        result = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            extreme,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        assert len(result) == 3

        extreme_high = UserThresholds(
            pvout_threshold=9999.0,
            plan_late_threshold=1.0,
            geas_threshold=1.0,
            resilience_gap_pct=100.0,
            min_viable_mwp=9999.0,
            reliability_threshold=1.0,
        )
        result2 = compute_scorecard_live(
            sample_resource_df,
            get_default_assumptions(),
            extreme_high,
            sample_ruptl_metrics,
            sample_demand_df,
            sample_grid_df,
        )
        assert len(result2) == 3
