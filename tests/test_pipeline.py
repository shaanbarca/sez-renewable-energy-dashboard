"""
tests/test_pipeline.py — pipeline builder tests.

Covers:
  - Unit conversions (MUSD→USD/kW, Rp/kWh→USD/MWh) — math must be exact
  - dim_kek: row count, slug uniqueness, polygon dedup logic
  - fct_lcoe: CF fallback (centroid when best_50km missing), is_capex_provisional propagation
  - fct_kek_resource: cf columns present and in plausible range
  - fct_grid_cost_proxy: all regions present, correct conversion
  - fct_kek_scorecard: all KEKs present, gap sign logic, data_completeness, green_share_geas
  - fct_kek_demand: demand_mwh_user column (nullable Float64, all null by default)
  - assumptions: two-factor derivation (BUILDING_INTENSITY × BUILDING_FOOTPRINT_RATIO × 10)
  - run_pipeline: topo_sort correctness, cycle detection, unknown dep error
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# ── Absolute path helpers ────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"


# ── dim_tech_cost: unit conversions ─────────────────────────────────────────

class TestDimTechCost:
    def test_capex_unit_conversion(self):
        """0.96 MUSD/MWe × 1000 = 960 USD/kW. Wrong multiplier → LCOE off by 3 orders."""
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        df = build_dim_tech_cost()
        assert df["capex_usd_per_kw"].iloc[0] == pytest.approx(960.0)

    def test_capex_lower_upper_bounds(self):
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        df = build_dim_tech_cost()
        assert df["capex_lower_usd_per_kw"].iloc[0] < df["capex_usd_per_kw"].iloc[0]
        assert df["capex_upper_usd_per_kw"].iloc[0] > df["capex_usd_per_kw"].iloc[0]

    def test_fixed_om_unit_conversion(self):
        """7,500 USD/MWe/yr ÷ 1000 = 7.5 USD/kW/yr."""
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        df = build_dim_tech_cost()
        assert df["fixed_om_usd_per_kw_yr"].iloc[0] == pytest.approx(7.5)

    def test_lifetime_is_integer_years(self):
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        df = build_dim_tech_cost()
        assert df["lifetime_yr"].iloc[0] == 27

    def test_is_provisional_false_after_pdf_verification(self):
        """source_page=66 means values were verified from PDF datasheet; not provisional."""
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        df = build_dim_tech_cost()
        assert not df["is_provisional"].iloc[0]

    def test_missing_tech_id_raises(self):
        """build_dim_tech_cost raises ValueError for unknown tech_id."""
        from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
        with pytest.raises(ValueError, match="not found"):
            build_dim_tech_cost(
                tech_variant_csv=REPO_ROOT / "data" / "dim_tech_variant.csv",
                tech_param_csv=REPO_ROOT / "data" / "fct_tech_parameter.csv",
                tech_id="TECH999",
            )


# ── dim_kek ──────────────────────────────────────────────────────────────────

class TestDimKek:
    def test_row_count(self):
        """Should produce exactly 25 KEKs (one per scraper row)."""
        from src.pipeline.build_dim_kek import build_dim_kek
        df = build_dim_kek()
        assert len(df) == 25

    def test_kek_id_unique(self):
        """kek_id is the primary key — no duplicates allowed."""
        from src.pipeline.build_dim_kek import build_dim_kek
        df = build_dim_kek()
        assert df["kek_id"].is_unique

    def test_polygon_dedup_largest_area_wins(self):
        """Polygon file has 30 features for 25 KEKs. Largest area per kek_id survives."""
        from src.pipeline.build_dim_kek import _load_polygon_attrs
        poly = _load_polygon_attrs(
            REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
        )
        assert poly["kek_id"].is_unique

    def test_grid_region_id_no_nulls(self):
        """All 25 KEKs must have a grid_region_id (from manual mapping file)."""
        from src.pipeline.build_dim_kek import build_dim_kek
        df = build_dim_kek()
        assert df["grid_region_id"].notna().all(), (
            f"Missing grid_region_id: {df.loc[df['grid_region_id'].isna(), 'kek_id'].tolist()}"
        )

    def test_required_columns_present(self):
        from src.pipeline.build_dim_kek import build_dim_kek
        df = build_dim_kek()
        required = ["kek_id", "kek_name", "province", "grid_region_id",
                    "kek_type", "latitude", "longitude", "data_vintage"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_coordinates_in_indonesia_bounds(self):
        """All KEK centroids should fall roughly within Indonesia's bounding box."""
        from src.pipeline.build_dim_kek import build_dim_kek
        df = build_dim_kek()
        assert df["latitude"].between(-12, 8).all()
        assert df["longitude"].between(95, 142).all()


# ── fct_kek_resource ─────────────────────────────────────────────────────────

class TestFctKekResource:
    def test_cf_columns_present(self):
        """cf_centroid and cf_best_50km must be in the output (added in this session)."""
        resource = pd.read_csv(PROCESSED / "fct_kek_resource.csv")
        assert "cf_centroid" in resource.columns
        assert "cf_best_50km" in resource.columns

    def test_cf_in_plausible_range(self):
        """Indonesian solar CF should be roughly 0.14–0.22 for utility-scale."""
        resource = pd.read_csv(PROCESSED / "fct_kek_resource.csv")
        cf = resource["cf_best_50km"].dropna()
        assert cf.between(0.10, 0.30).all(), f"CF out of range: {cf.describe()}"

    def test_cf_equals_pvout_over_8760(self):
        """CF ≈ pvout_annual / 8760 — consistent within rounding tolerance.

        pvout_best_50km is stored rounded to 1 decimal; cf_best_50km is
        computed from the unrounded value.  Max rounding error ≈ 0.05 / 8760
        ≈ 0.000006, so atol=0.0001 is a tight but fair bound.
        """
        resource = pd.read_csv(PROCESSED / "fct_kek_resource.csv")
        valid = resource.dropna(subset=["pvout_best_50km", "cf_best_50km"])
        expected_cf = valid["pvout_best_50km"] / 8760
        import numpy as np
        assert np.allclose(expected_cf, valid["cf_best_50km"], atol=0.0001)

    def test_pvout_in_plausible_annual_range(self):
        """Annual PVOUT should be 1000–2500 kWh/kWp/yr for Indonesia."""
        resource = pd.read_csv(PROCESSED / "fct_kek_resource.csv")
        pvout = resource["pvout_best_50km"].dropna()
        assert pvout.between(1000, 2500).all()


# ── fct_lcoe ─────────────────────────────────────────────────────────────────

class TestFctLcoe:
    def test_three_wacc_values(self):
        """Should produce rows for WACC = 8, 10, 12%."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe
        df = build_fct_lcoe()
        assert set(df["wacc_pct"].unique()) == {8.0, 10.0, 12.0}

    def test_row_count(self):
        """25 KEKs × 3 WACC values = 75 rows."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe
        df = build_fct_lcoe()
        assert len(df) == 75

    def test_higher_wacc_higher_lcoe(self):
        """LCOE should increase monotonically with WACC for the same KEK."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe
        df = build_fct_lcoe()
        pivot = df.pivot(index="kek_id", columns="wacc_pct", values="lcoe_usd_mwh").dropna()
        assert (pivot[8.0] < pivot[10.0]).all()
        assert (pivot[10.0] < pivot[12.0]).all()

    def test_lcoe_low_lt_mid_lt_high(self):
        """Lower CAPEX → lower LCOE at same WACC."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe
        df = build_fct_lcoe().dropna(subset=["lcoe_low_usd_mwh", "lcoe_usd_mwh", "lcoe_high_usd_mwh"])
        assert (df["lcoe_low_usd_mwh"] < df["lcoe_usd_mwh"]).all()
        assert (df["lcoe_usd_mwh"] < df["lcoe_high_usd_mwh"]).all()

    def test_is_capex_provisional_propagated(self):
        """is_capex_provisional must come through from dim_tech_cost."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe
        df = build_fct_lcoe()
        assert "is_capex_provisional" in df.columns
        # All rows share the same value (one tech row)
        assert df["is_capex_provisional"].nunique() == 1

    def test_cf_fallback_uses_centroid(self, tmp_path):
        """When pvout_best_50km is NaN, CF should fall back to pvout_centroid."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        # Build minimal fixtures
        dim_kek = pd.DataFrame({"kek_id": ["kek-test"]})
        resource = pd.DataFrame({
            "kek_id": ["kek-test"],
            "pvout_centroid": [1500.0],
            "pvout_best_50km": [np.nan],  # missing best_50km
        })
        tech = pd.DataFrame([{
            "tech_id": "TECH006", "tech_description": "Solar",
            "year": 2023, "capex_usd_per_kw": 700.0,
            "capex_lower_usd_per_kw": 560.0, "capex_upper_usd_per_kw": 840.0,
            "fixed_om_usd_per_kw_yr": 12.0, "lifetime_yr": 25,
            "source_pdf": "test.pdf", "source_page": 0, "is_provisional": True,
        }])

        dim_kek.to_csv(tmp_path / "dim_kek.csv", index=False)
        resource.to_csv(tmp_path / "fct_kek_resource.csv", index=False)
        tech.to_csv(tmp_path / "dim_tech_cost.csv", index=False)

        df = build_fct_lcoe(
            dim_kek_csv=tmp_path / "dim_kek.csv",
            fct_kek_resource_csv=tmp_path / "fct_kek_resource.csv",
            dim_tech_cost_csv=tmp_path / "dim_tech_cost.csv",
            wacc_values=[10.0],
        )
        assert len(df) == 1
        assert df["is_cf_provisional"].iloc[0]
        expected_cf = round(1500.0 / 8760, 4)
        assert df["cf_used"].iloc[0] == pytest.approx(expected_cf)

    def test_nan_cf_produces_nan_lcoe(self, tmp_path):
        """KEK with no PVOUT data should produce NaN LCOE, not raise."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        dim_kek = pd.DataFrame({"kek_id": ["kek-nodata"]})
        resource = pd.DataFrame({
            "kek_id": ["kek-nodata"],
            "pvout_centroid": [np.nan],
            "pvout_best_50km": [np.nan],
        })
        tech = pd.DataFrame([{
            "tech_id": "TECH006", "tech_description": "Solar",
            "year": 2023, "capex_usd_per_kw": 700.0,
            "capex_lower_usd_per_kw": 560.0, "capex_upper_usd_per_kw": 840.0,
            "fixed_om_usd_per_kw_yr": 12.0, "lifetime_yr": 25,
            "source_pdf": "test.pdf", "source_page": 0, "is_provisional": True,
        }])

        dim_kek.to_csv(tmp_path / "dim_kek.csv", index=False)
        resource.to_csv(tmp_path / "fct_kek_resource.csv", index=False)
        tech.to_csv(tmp_path / "dim_tech_cost.csv", index=False)

        df = build_fct_lcoe(
            dim_kek_csv=tmp_path / "dim_kek.csv",
            fct_kek_resource_csv=tmp_path / "fct_kek_resource.csv",
            dim_tech_cost_csv=tmp_path / "dim_tech_cost.csv",
            wacc_values=[10.0],
        )
        assert df["lcoe_usd_mwh"].isna().all()


# ── fct_grid_cost_proxy ───────────────────────────────────────────────────────

class TestFctGridCostProxy:
    def test_rp_kwh_to_usd_mwh_conversion(self):
        """996.74 Rp/kWh ÷ 15,800 × 1000 = ~63.08 USD/MWh."""
        from src.pipeline.build_fct_grid_cost_proxy import rp_kwh_to_usd_mwh
        result = rp_kwh_to_usd_mwh(996.74, idr_usd=15_800.0)
        assert result == pytest.approx(63.08, rel=1e-3)

    def test_all_expected_regions_present(self):
        """Every grid region in dim_kek must have a cost proxy row."""
        dim_kek = pd.read_csv(PROCESSED / "dim_kek.csv")
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        kek_regions = set(dim_kek["grid_region_id"].dropna().unique())
        proxy_regions = set(proxy["grid_region_id"].unique())
        assert kek_regions.issubset(proxy_regions), (
            f"Missing regions in proxy: {kek_regions - proxy_regions}"
        )

    def test_dashboard_rate_is_official(self):
        """I-4 tariff is from Permen ESDM 7/2024 — must be flagged OFFICIAL."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        assert (proxy["dashboard_rate_flag"] == "OFFICIAL").all()


# ── fct_kek_scorecard ─────────────────────────────────────────────────────────

class TestFctKekScorecard:
    def test_row_count(self):
        """One row per KEK, no duplicates."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        assert len(sc) == 25
        assert sc["kek_id"].is_unique

    def test_solar_competitive_gap_sign(self):
        """Negative gap = solar LCOE < grid cost = solar is already cheaper."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        gap_row = sc.dropna(subset=["solar_competitive_gap_pct", "lcoe_mid_usd_mwh",
                                     "dashboard_rate_usd_mwh"])
        cheaper_mask = gap_row["lcoe_mid_usd_mwh"] < gap_row["dashboard_rate_usd_mwh"]
        assert (gap_row.loc[cheaper_mask, "solar_competitive_gap_pct"] < 0).all()

    def test_clean_power_advantage_is_negated_gap(self):
        """clean_power_advantage = −solar_competitive_gap_pct."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        valid = sc.dropna(subset=["solar_competitive_gap_pct", "clean_power_advantage"])
        expected = (-valid["solar_competitive_gap_pct"]).round(1)
        assert (expected == valid["clean_power_advantage"]).all()

    def test_data_completeness_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        assert "data_completeness" in sc.columns
        assert sc["data_completeness"].isin(["complete", "partial", "provisional"]).all()

    def test_action_flag_values(self):
        """action_flag must only contain valid values."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        valid_flags = {"solar_now", "grid_first", "firming_needed", "plan_late", "data_missing"}
        assert set(sc["action_flag"].unique()).issubset(valid_flags)

    def test_lcoe_in_plausible_range(self):
        """Indonesia solar LCOE should be roughly $35–$100/MWh at WACC=10%."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        lcoe = sc["lcoe_mid_usd_mwh"].dropna()
        assert lcoe.between(30, 120).all(), f"LCOE out of range: {lcoe.describe()}"

    def test_green_share_geas_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        assert "green_share_geas" in sc.columns

    def test_green_share_geas_in_valid_range(self):
        """green_share_geas is a fraction: 0 ≤ value ≤ 1 for all rows."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        vals = sc["green_share_geas"].dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_green_share_geas_not_all_zero(self):
        """Now that fct_kek_demand feeds the scorecard, green_share_geas > 0 for some KEKs."""
        sc = pd.read_csv(PROCESSED / "fct_kek_scorecard.csv")
        assert (sc["green_share_geas"] > 0).any(), (
            "All green_share_geas are 0 — likely fct_kek_demand not being read"
        )

    def test_scorecard_depends_on_fct_kek_demand(self):
        """Pipeline DAG: fct_kek_scorecard must list fct_kek_demand as a dependency."""
        import sys
        sys.path.insert(0, str(REPO_ROOT))
        import run_pipeline
        scorecard_step = next(s for s in run_pipeline.PIPELINE if s.name == "fct_kek_scorecard")
        assert "fct_kek_demand" in scorecard_step.depends_on


# ── run_pipeline: topo sort ───────────────────────────────────────────────────

# ── fct_kek_demand ──────────────────────────────────────────────────────────

class TestFctKekDemand:
    @pytest.fixture(scope="class")
    def demand(self):
        from src.pipeline.build_fct_kek_demand import build_fct_kek_demand
        return build_fct_kek_demand()

    def test_row_count_matches_dim_kek(self, demand):
        dim_kek = pd.read_csv(PROCESSED / "dim_kek.csv")
        assert len(demand) == len(dim_kek)

    def test_all_kek_ids_present(self, demand):
        dim_kek = pd.read_csv(PROCESSED / "dim_kek.csv")
        assert set(demand["kek_id"]) == set(dim_kek["kek_id"])

    def test_demand_positive_for_all_rows(self, demand):
        assert (demand["demand_mwh"] > 0).all(), "Every KEK must have demand_mwh > 0"

    def test_demand_mwh_equals_area_times_intensity(self, demand):
        """Core arithmetic: demand_mwh = area_ha × energy_intensity_mwh_per_ha_yr."""
        expected = demand["area_ha"] * demand["energy_intensity_mwh_per_ha_yr"]
        assert np.allclose(demand["demand_mwh"], expected, rtol=1e-6)

    def test_energy_intensity_matches_assumptions(self, demand):
        from src.assumptions import (
            ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
            ENERGY_INTENSITY_MWH_PER_HA_YR,
        )
        for _, row in demand.iterrows():
            expected = ENERGY_INTENSITY_MWH_PER_HA_YR.get(
                row["kek_type"], ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR
            )
            assert row["energy_intensity_mwh_per_ha_yr"] == pytest.approx(expected), (
                f"{row['kek_id']}: expected intensity {expected}, got {row['energy_intensity_mwh_per_ha_yr']}"
            )

    def test_all_provisional(self, demand):
        assert demand["is_demand_provisional"].all()

    def test_fallback_rows_flagged(self, demand):
        """KEKs with missing area_ha must have demand_source == area_fallback_median."""
        fallback = demand[demand["demand_source"] == "area_fallback_median"]
        assert len(fallback) >= 1, "Expected at least one fallback row (setangga, tanjung-sauh)"

    def test_no_null_demand(self, demand):
        assert demand["demand_mwh"].notna().all()
        assert demand["area_ha"].notna().all()

    def test_year_column_is_target_year(self, demand):
        from src.assumptions import DEMAND_TARGET_YEAR
        assert (demand["year"] == DEMAND_TARGET_YEAR).all()

    def test_industri_demand_higher_than_pariwisata(self, demand):
        """Manufacturing intensity (800) > tourism intensity (150) — so per-ha demand differs."""
        from src.assumptions import ENERGY_INTENSITY_MWH_PER_HA_YR
        industri_intensity = ENERGY_INTENSITY_MWH_PER_HA_YR["Industri"]
        pariwisata_intensity = ENERGY_INTENSITY_MWH_PER_HA_YR["Pariwisata"]
        assert industri_intensity > pariwisata_intensity

    def test_demand_mwh_user_column_exists(self, demand):
        assert "demand_mwh_user" in demand.columns

    def test_demand_mwh_user_is_all_null(self, demand):
        assert demand["demand_mwh_user"].isna().all()

    def test_demand_mwh_user_is_nullable_float(self, demand):
        assert str(demand["demand_mwh_user"].dtype) == "Float64"


class TestTopoSort:
    def _make_steps(self):
        """Return minimal Step objects for topo sort testing."""
        from run_pipeline import Step, _topo_sort
        return Step, _topo_sort

    def test_empty_pipeline(self):
        Step, _topo_sort = self._make_steps()
        result = _topo_sort([])
        assert result == []

    def test_no_deps_preserves_any_order(self):
        Step, _topo_sort = self._make_steps()
        steps = [
            Step("a", lambda: None, "a.csv"),
            Step("b", lambda: None, "b.csv"),
        ]
        result = _topo_sort(steps)
        assert {s.name for s in result} == {"a", "b"}

    def test_dep_runs_before_dependent(self):
        Step, _topo_sort = self._make_steps()
        steps = [
            Step("scorecard", lambda: None, "s.csv", depends_on=["lcoe"]),
            Step("lcoe",      lambda: None, "l.csv", depends_on=["kek"]),
            Step("kek",       lambda: None, "k.csv"),
        ]
        result = _topo_sort(steps)
        names = [s.name for s in result]
        assert names.index("kek") < names.index("lcoe")
        assert names.index("lcoe") < names.index("scorecard")

    def test_misordered_list_is_fixed(self):
        """Topo sort should reorder even if list has deps after dependents."""
        Step, _topo_sort = self._make_steps()
        steps = [
            Step("c", lambda: None, "c.csv", depends_on=["b"]),
            Step("b", lambda: None, "b.csv", depends_on=["a"]),
            Step("a", lambda: None, "a.csv"),
        ]
        result = _topo_sort(steps)
        names = [s.name for s in result]
        assert names == ["a", "b", "c"]

    def test_cycle_raises(self):
        Step, _topo_sort = self._make_steps()
        steps = [
            Step("a", lambda: None, "a.csv", depends_on=["b"]),
            Step("b", lambda: None, "b.csv", depends_on=["a"]),
        ]
        with pytest.raises(ValueError, match="Circular"):
            _topo_sort(steps)

    def test_unknown_dep_raises(self):
        Step, _topo_sort = self._make_steps()
        steps = [
            Step("a", lambda: None, "a.csv", depends_on=["does_not_exist"]),
        ]
        with pytest.raises(ValueError, match="Unknown dependency"):
            _topo_sort(steps)


# ── assumptions: two-factor derivation ───────────────────────────────────────

class TestAssumptions:
    """Verify the two-factor zone intensity derivation in src/assumptions.py.

    Formula: ENERGY_INTENSITY_MWH_PER_HA_YR[k] = BUILDING_INTENSITY_KWH_M2_YR[k]
                                                  × BUILDING_FOOTPRINT_RATIO[k]
                                                  × 10
    (unit conversion: kWh/m² × 10,000 m²/ha ÷ 1,000 kWh/MWh = × 10)
    """

    def test_all_kek_types_have_both_factors(self):
        from src.assumptions import BUILDING_FOOTPRINT_RATIO, BUILDING_INTENSITY_KWH_M2_YR
        assert set(BUILDING_INTENSITY_KWH_M2_YR.keys()) == set(BUILDING_FOOTPRINT_RATIO.keys())

    def test_derived_intensity_matches_formula(self):
        from src.assumptions import (
            BUILDING_FOOTPRINT_RATIO,
            BUILDING_INTENSITY_KWH_M2_YR,
            ENERGY_INTENSITY_MWH_PER_HA_YR,
        )
        for kek_type in BUILDING_INTENSITY_KWH_M2_YR:
            expected = round(
                BUILDING_INTENSITY_KWH_M2_YR[kek_type]
                * BUILDING_FOOTPRINT_RATIO[kek_type]
                * 10,
                1,
            )
            assert ENERGY_INTENSITY_MWH_PER_HA_YR[kek_type] == pytest.approx(expected), (
                f"{kek_type}: expected {expected}, got {ENERGY_INTENSITY_MWH_PER_HA_YR[kek_type]}"
            )

    def test_industri_dan_pariwisata_is_weighted_average(self):
        """Industri dan Pariwisata building intensity = 0.6×Industri + 0.4×Pariwisata."""
        from src.assumptions import BUILDING_INTENSITY_KWH_M2_YR
        expected = round(
            0.6 * BUILDING_INTENSITY_KWH_M2_YR["Industri"]
            + 0.4 * BUILDING_INTENSITY_KWH_M2_YR["Pariwisata"],
            1,
        )
        assert BUILDING_INTENSITY_KWH_M2_YR["Industri dan Pariwisata"] == pytest.approx(
            expected, abs=1.0
        )

    def test_default_intensity_is_average_of_four_categories(self):
        from src.assumptions import (
            ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
            ENERGY_INTENSITY_MWH_PER_HA_YR,
        )
        expected = round(
            sum(ENERGY_INTENSITY_MWH_PER_HA_YR.values()) / len(ENERGY_INTENSITY_MWH_PER_HA_YR),
            1,
        )
        assert ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR == pytest.approx(expected)

    def test_building_footprint_ratio_is_fraction(self):
        from src.assumptions import BUILDING_FOOTPRINT_RATIO
        for kek_type, ratio in BUILDING_FOOTPRINT_RATIO.items():
            assert 0 < ratio <= 1, f"{kek_type}: footprint ratio {ratio} must be (0, 1]"
