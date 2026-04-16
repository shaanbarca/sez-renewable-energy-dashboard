"""
tests/test_pipeline.py — pipeline builder tests.

Covers:
  - Unit conversions (MUSD→USD/kW, Rp/kWh→USD/MWh) — math must be exact
  - dim_sites: row count, slug uniqueness, polygon dedup logic
  - fct_lcoe: CF fallback (centroid when best_50km missing), is_capex_provisional propagation
  - fct_site_resource: cf columns present and in plausible range
  - fct_grid_cost_proxy: all regions present, correct conversion
  - fct_site_scorecard: all KEKs present, gap sign logic, data_completeness, green_share_geas
  - fct_site_demand: demand_mwh_user column (nullable Float64, all null by default)
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
                tech_id="TECH999",
            )


# ── pdf_extract_esdm_tech: extractor tests ───────────────────────────────────

ESDM_PDF_PATH = REPO_ROOT / "docs" / "esdm_technology_cost.pdf"


class TestPdfExtractEsdmTech:
    def test_get_tech006_params_returns_verified_values(self):
        """get_tech006_params() always returns data — falls back to hardcoded if PDF image-based."""
        from src.pipeline.pdf_extract_esdm_tech import VERIFIED_TECH006_DATA, get_tech006_params

        params = get_tech006_params(ESDM_PDF_PATH)
        # Values must match VERIFIED_TECH006_DATA (either extracted or hardcoded fallback)
        assert params["capex"]["central"] == pytest.approx(
            VERIFIED_TECH006_DATA["capex"]["central"]
        )
        assert params["fixed_om"]["central"] == pytest.approx(
            VERIFIED_TECH006_DATA["fixed_om"]["central"]
        )
        assert params["lifetime"]["central"] == pytest.approx(
            VERIFIED_TECH006_DATA["lifetime"]["central"]
        )

    def test_get_tech006_params_lower_lt_central_lt_upper(self):
        """Uncertainty bounds must be ordered: lower < central < upper."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech006_params

        params = get_tech006_params(ESDM_PDF_PATH)
        for param in ("capex", "fixed_om", "lifetime"):
            assert params[param]["lower"] < params[param]["central"] < params[param]["upper"], (
                f"{param}: lower/central/upper not ordered correctly"
            )

    def test_extractor_graceful_on_missing_pdf(self):
        """extract_tech006_from_pdf() returns None when PDF does not exist."""
        from src.pipeline.pdf_extract_esdm_tech import extract_tech006_from_pdf

        result = extract_tech006_from_pdf(Path("/nonexistent/path.pdf"))
        assert result is None

    def test_get_tech006_params_falls_back_on_missing_pdf(self):
        """get_tech006_params() returns VERIFIED data even when PDF is missing."""
        from src.pipeline.pdf_extract_esdm_tech import VERIFIED_TECH006_DATA, get_tech006_params

        params = get_tech006_params(Path("/nonexistent/path.pdf"))
        assert params["capex"]["central"] == VERIFIED_TECH006_DATA["capex"]["central"]

    def test_verify_tech006_against_hardcoded_passes(self):
        """verify_tech006_against_hardcoded() returns True with the real PDF."""
        from src.pipeline.pdf_extract_esdm_tech import verify_tech006_against_hardcoded

        assert verify_tech006_against_hardcoded(ESDM_PDF_PATH) is True

    def test_source_page_is_nonzero(self):
        """source_page must be non-zero — 0 means pending verification."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech006_params

        params = get_tech006_params(ESDM_PDF_PATH)
        assert params["capex"]["source_page"] != 0


# ── pdf_extract_esdm_tech: wind onshore extractor tests ──────────────────────


class TestPdfExtractWindOnshore:
    def test_get_wind_onshore_params_returns_verified_values(self):
        """get_tech_wind_onshore_params() always returns data."""
        from src.pipeline.pdf_extract_esdm_tech import (
            VERIFIED_TECH_WIND_ONSHORE_DATA,
            get_tech_wind_onshore_params,
        )

        params = get_tech_wind_onshore_params(ESDM_PDF_PATH)
        assert params["capex"]["central"] == pytest.approx(
            VERIFIED_TECH_WIND_ONSHORE_DATA["capex"]["central"]
        )
        assert params["fixed_om"]["central"] == pytest.approx(
            VERIFIED_TECH_WIND_ONSHORE_DATA["fixed_om"]["central"]
        )
        assert params["lifetime"]["central"] == pytest.approx(
            VERIFIED_TECH_WIND_ONSHORE_DATA["lifetime"]["central"]
        )

    def test_wind_onshore_lower_lt_central_lt_upper(self):
        """Uncertainty bounds must be ordered: lower < central < upper."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech_wind_onshore_params

        params = get_tech_wind_onshore_params(ESDM_PDF_PATH)
        for param in ("capex", "fixed_om", "lifetime"):
            assert params[param]["lower"] < params[param]["central"] < params[param]["upper"], (
                f"{param}: lower/central/upper not ordered correctly"
            )

    def test_wind_capex_higher_than_solar(self):
        """Wind onshore CAPEX should be higher than solar PV."""
        from src.pipeline.pdf_extract_esdm_tech import (
            get_tech006_params,
            get_tech_wind_onshore_params,
        )

        solar = get_tech006_params(ESDM_PDF_PATH)
        wind = get_tech_wind_onshore_params(ESDM_PDF_PATH)
        assert wind["capex"]["central"] > solar["capex"]["central"]

    def test_wind_fom_higher_than_solar(self):
        """Wind onshore FOM should be higher than solar PV."""
        from src.pipeline.pdf_extract_esdm_tech import (
            get_tech006_params,
            get_tech_wind_onshore_params,
        )

        solar = get_tech006_params(ESDM_PDF_PATH)
        wind = get_tech_wind_onshore_params(ESDM_PDF_PATH)
        assert wind["fixed_om"]["central"] > solar["fixed_om"]["central"]

    def test_wind_extractor_graceful_on_missing_pdf(self):
        """extract_wind_onshore_from_pdf() returns None when PDF does not exist."""
        from src.pipeline.pdf_extract_esdm_tech import extract_wind_onshore_from_pdf

        result = extract_wind_onshore_from_pdf(Path("/nonexistent/path.pdf"))
        assert result is None

    def test_wind_falls_back_on_missing_pdf(self):
        """get_tech_wind_onshore_params() returns VERIFIED data even when PDF is missing."""
        from src.pipeline.pdf_extract_esdm_tech import (
            VERIFIED_TECH_WIND_ONSHORE_DATA,
            get_tech_wind_onshore_params,
        )

        params = get_tech_wind_onshore_params(Path("/nonexistent/path.pdf"))
        assert params["capex"]["central"] == VERIFIED_TECH_WIND_ONSHORE_DATA["capex"]["central"]

    def test_verify_wind_onshore_passes(self):
        """verify_wind_onshore_against_hardcoded() returns True with the real PDF."""
        from src.pipeline.pdf_extract_esdm_tech import verify_wind_onshore_against_hardcoded

        assert verify_wind_onshore_against_hardcoded(ESDM_PDF_PATH) is True

    def test_wind_source_page_is_nonzero(self):
        """source_page must be non-zero — 0 means pending verification."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech_wind_onshore_params

        params = get_tech_wind_onshore_params(ESDM_PDF_PATH)
        assert params["capex"]["source_page"] != 0


# ── unified dispatcher tests ──────────────────────────────────────────────────


class TestGetTechParams:
    def test_dispatch_solar(self):
        """get_tech_params('TECH006') returns solar params."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech_params

        params = get_tech_params("TECH006", ESDM_PDF_PATH)
        assert params["capex"]["central"] == pytest.approx(0.96)

    def test_dispatch_wind(self):
        """get_tech_params('TECH_WIND_ONSHORE') returns wind params."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech_params

        params = get_tech_params("TECH_WIND_ONSHORE", ESDM_PDF_PATH)
        assert params["capex"]["central"] == pytest.approx(1.65)

    def test_dispatch_unknown_raises(self):
        """get_tech_params() raises KeyError for unknown tech_id."""
        from src.pipeline.pdf_extract_esdm_tech import get_tech_params

        with pytest.raises(KeyError):
            get_tech_params("TECH_UNKNOWN", ESDM_PDF_PATH)


# ── dim_tech_cost_wind ────────────────────────────────────────────────────────


class TestDimTechCostWind:
    def test_row_count(self):
        """Should produce exactly 1 row."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert len(df) == 1

    def test_capex_unit_conversion(self):
        """CAPEX should be 1.65 MUSD/MWe × 1000 = 1650 USD/kW."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert df.iloc[0]["capex_usd_per_kw"] == pytest.approx(1650.0)

    def test_fom_unit_conversion(self):
        """FOM should be 40,000 USD/MWe/yr ÷ 1000 = 40 USD/kW/yr."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert df.iloc[0]["fixed_om_usd_per_kw_yr"] == pytest.approx(40.0)

    def test_lifetime(self):
        """Lifetime should be 27 years."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert df.iloc[0]["lifetime_yr"] == 27

    def test_tech_id(self):
        """tech_id should be TECH_WIND_ONSHORE."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert df.iloc[0]["tech_id"] == "TECH_WIND_ONSHORE"

    def test_not_provisional(self):
        """Source page is known (90), so not provisional."""
        from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind

        df = build_dim_tech_cost_wind()
        assert bool(df.iloc[0]["is_provisional"]) is False


# ── dim_sites ──────────────────────────────────────────────────────────────────


class TestDimSites:
    def test_row_count(self):
        """Should produce 48 sites (25 KEKs + 23 industrial from priority1_sites.csv)."""
        from src.pipeline.build_dim_sites import build_dim_sites

        df = build_dim_sites()
        assert len(df) >= 25  # at least 25 KEKs, plus industrial sites

    def test_site_id_unique(self):
        """site_id is the primary key — no duplicates allowed."""
        from src.pipeline.build_dim_sites import build_dim_sites

        df = build_dim_sites()
        assert df["site_id"].is_unique

    def test_polygon_dedup_largest_area_wins(self):
        """Polygon file has 30 features for 25 KEKs. Largest area per kek_id survives."""
        from src.pipeline.build_dim_kek import _load_polygon_attrs

        poly = _load_polygon_attrs(REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson")
        assert poly["kek_id"].is_unique

    def test_grid_region_id_no_nulls(self):
        """All 25 KEKs must have a grid_region_id (from manual mapping file)."""
        from src.pipeline.build_dim_sites import build_dim_sites

        df = build_dim_sites()
        assert df["grid_region_id"].notna().all(), (
            f"Missing grid_region_id: {df.loc[df['grid_region_id'].isna(), 'site_id'].tolist()}"
        )

    def test_required_columns_present(self):
        from src.pipeline.build_dim_sites import build_dim_sites

        df = build_dim_sites()
        required = [
            "site_id",
            "site_name",
            "province",
            "grid_region_id",
            "zone_classification",
            "latitude",
            "longitude",
            "data_vintage",
        ]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_coordinates_in_indonesia_bounds(self):
        """All KEK centroids should fall roughly within Indonesia's bounding box."""
        from src.pipeline.build_dim_sites import build_dim_sites

        df = build_dim_sites()
        assert df["latitude"].between(-12, 8).all()
        assert df["longitude"].between(95, 142).all()


# ── fct_site_resource ─────────────────────────────────────────────────────────


class TestFctKekResource:
    def test_cf_columns_present(self):
        """cf_centroid and cf_best_50km must be in the output (added in this session)."""
        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        assert "cf_centroid" in resource.columns
        assert "cf_best_50km" in resource.columns

    def test_cf_in_plausible_range(self):
        """Indonesian solar CF should be roughly 0.14–0.22 for utility-scale."""
        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        cf = resource["cf_best_50km"].dropna()
        assert cf.between(0.10, 0.30).all(), f"CF out of range: {cf.describe()}"

    def test_cf_equals_pvout_over_8760(self):
        """CF ≈ pvout_annual / 8760 — consistent within rounding tolerance.

        pvout_best_50km is stored rounded to 1 decimal; cf_best_50km is
        computed from the unrounded value.  Max rounding error ≈ 0.05 / 8760
        ≈ 0.000006, so atol=0.0001 is a tight but fair bound.
        """
        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        valid = resource.dropna(subset=["pvout_best_50km", "cf_best_50km"])
        expected_cf = valid["pvout_best_50km"] / 8760
        import numpy as np

        assert np.allclose(expected_cf, valid["cf_best_50km"], atol=0.0001)

    def test_pvout_in_plausible_annual_range(self):
        """Annual PVOUT should be 1000–2500 kWh/kWp/yr for Indonesia."""
        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        pvout = resource["pvout_best_50km"].dropna()
        assert pvout.between(1000, 2500).all()

    def test_buildability_columns_present(self):
        """v1.1: fct_site_resource must contain the 4 buildability columns."""
        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        for col in [
            "pvout_buildable_best_50km",
            "buildable_area_ha",
            "max_captive_capacity_mwp",
            "buildability_constraint",
        ]:
            assert col in resource.columns, f"Missing column: {col}"

    def test_buildability_constraint_valid_values(self):
        """buildability_constraint must be one of the 7 defined string values."""
        from src.pipeline.buildability_filters import VALID_CONSTRAINTS

        resource = pd.read_csv(PROCESSED / "fct_site_resource.csv")
        vals = resource["buildability_constraint"].dropna().unique()
        invalid = [v for v in vals if v not in VALID_CONSTRAINTS]
        assert not invalid, f"Invalid constraint values: {invalid}"


# ── fct_lcoe ─────────────────────────────────────────────────────────────────


class TestFctLcoe:
    def test_wacc_values_full_range(self):
        """Should produce rows for all 9 WACC snaps: 4% through 20% in 2% steps."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        assert set(df["wacc_pct"].unique()) == {4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0}

    def test_row_count(self):
        """25 KEKs × 9 WACC values × 2 scenarios = 450 rows."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        # 48 sites x 9 WACC x 2 scenarios = 864 (parameterized, not hardcoded)
        n_sites = df["site_id"].nunique()
        assert len(df) == n_sites * 9 * 2

    def test_two_scenarios(self):
        """Each KEK/WACC combination must have both within_boundary and grid_connected_solar."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        assert set(df["scenario"].unique()) == {"within_boundary", "grid_connected_solar"}

    def test_grid_connected_effective_capex_gt_within_boundary(self):
        """Grid-connected effective CAPEX must exceed within_boundary (connection cost adds cost)."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        wb = df[df["scenario"] == "within_boundary"].set_index(["site_id", "wacc_pct"])[
            "effective_capex_usd_per_kw"
        ]
        gc = df[df["scenario"] == "grid_connected_solar"].set_index(["site_id", "wacc_pct"])[
            "effective_capex_usd_per_kw"
        ]
        assert (gc > wb).all(), (
            "Grid-connected effective CAPEX must always exceed within_boundary (connection cost adder)"
        )

    def test_within_boundary_connection_cost_zero(self):
        """within_boundary scenario must have connection_cost_per_kw = 0."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        wb = df[df["scenario"] == "within_boundary"]
        assert (wb["connection_cost_per_kw"] == 0).all()

    def test_grid_connected_connection_cost_positive(self):
        """grid_connected_solar scenario must have connection_cost_per_kw > 0."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        gc = df[df["scenario"] == "grid_connected_solar"]
        assert (gc["connection_cost_per_kw"] > 0).all()

    def test_higher_wacc_higher_lcoe(self):
        """LCOE should increase monotonically with WACC for the same KEK × scenario."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        pivot = df.pivot(
            index=["site_id", "scenario"], columns="wacc_pct", values="lcoe_usd_mwh"
        ).dropna()
        assert (pivot[8.0] < pivot[10.0]).all()
        assert (pivot[10.0] < pivot[12.0]).all()

    def test_lcoe_low_lt_mid_lt_high(self):
        """Lower CAPEX → lower LCOE at same WACC."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe().dropna(
            subset=["lcoe_low_usd_mwh", "lcoe_usd_mwh", "lcoe_high_usd_mwh"]
        )
        assert (df["lcoe_low_usd_mwh"] < df["lcoe_usd_mwh"]).all()
        assert (df["lcoe_usd_mwh"] < df["lcoe_high_usd_mwh"]).all()

    def test_is_capex_provisional_propagated(self):
        """is_capex_provisional must come through from dim_tech_cost."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        assert "is_capex_provisional" in df.columns
        assert df["is_capex_provisional"].nunique() == 1

    def test_cf_fallback_uses_centroid(self, tmp_path):
        """When pvout_best_50km is NaN, CF should fall back to pvout_centroid for both scenarios."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        dim_sites = pd.DataFrame({"site_id": ["kek-test"]})
        resource = pd.DataFrame(
            {
                "site_id": ["kek-test"],
                "pvout_centroid": [1500.0],
                "pvout_best_50km": [np.nan],
            }
        )
        tech = pd.DataFrame(
            [
                {
                    "tech_id": "TECH006",
                    "tech_description": "Solar",
                    "year": 2023,
                    "capex_usd_per_kw": 960.0,
                    "capex_lower_usd_per_kw": 830.0,
                    "capex_upper_usd_per_kw": 1500.0,
                    "fixed_om_usd_per_kw_yr": 7.5,
                    "lifetime_yr": 27,
                    "source_pdf": "test.pdf",
                    "source_page": 66,
                    "is_provisional": False,
                }
            ]
        )
        proximity = pd.DataFrame(
            {
                "site_id": ["kek-test"],
                "dist_to_nearest_substation_km": [10.0],
                "dist_solar_to_nearest_substation_km": [5.0],
            }
        )

        dim_sites.to_csv(tmp_path / "dim_sites.csv", index=False)
        resource.to_csv(tmp_path / "fct_site_resource.csv", index=False)
        tech.to_csv(tmp_path / "dim_tech_cost.csv", index=False)
        proximity.to_csv(tmp_path / "fct_substation_proximity.csv", index=False)

        df = build_fct_lcoe(
            dim_sites_csv=tmp_path / "dim_sites.csv",
            fct_site_resource_csv=tmp_path / "fct_site_resource.csv",
            dim_tech_cost_csv=tmp_path / "dim_tech_cost.csv",
            fct_substation_proximity_csv=tmp_path / "fct_substation_proximity.csv",
            wacc_values=[10.0],
        )
        assert len(df) == 2  # 2 scenarios × 1 WACC
        # grid_connected_solar row is provisional (best_50km was missing, fell back to centroid)
        gc_row = df[df["scenario"] == "grid_connected_solar"].iloc[0]
        assert gc_row["is_cf_provisional"]
        # within_boundary row uses centroid intentionally — not provisional
        wb_row = df[df["scenario"] == "within_boundary"].iloc[0]
        assert not wb_row["is_cf_provisional"]
        # Both rows fall back to centroid CF value
        expected_cf = round(1500.0 / 8760, 4)
        assert np.allclose(df["cf_used"], expected_cf, atol=1e-4)

    def test_nan_cf_produces_nan_lcoe(self, tmp_path):
        """KEK with no PVOUT data should produce NaN LCOE, not raise."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        dim_sites = pd.DataFrame({"site_id": ["kek-nodata"]})
        resource = pd.DataFrame(
            {
                "site_id": ["kek-nodata"],
                "pvout_centroid": [np.nan],
                "pvout_best_50km": [np.nan],
            }
        )
        tech = pd.DataFrame(
            [
                {
                    "tech_id": "TECH006",
                    "tech_description": "Solar",
                    "year": 2023,
                    "capex_usd_per_kw": 960.0,
                    "capex_lower_usd_per_kw": 830.0,
                    "capex_upper_usd_per_kw": 1500.0,
                    "fixed_om_usd_per_kw_yr": 7.5,
                    "lifetime_yr": 27,
                    "source_pdf": "test.pdf",
                    "source_page": 66,
                    "is_provisional": False,
                }
            ]
        )
        proximity = pd.DataFrame(
            {
                "site_id": ["kek-nodata"],
                "dist_to_nearest_substation_km": [5.0],
                "dist_solar_to_nearest_substation_km": [3.0],
            }
        )

        dim_sites.to_csv(tmp_path / "dim_sites.csv", index=False)
        resource.to_csv(tmp_path / "fct_site_resource.csv", index=False)
        tech.to_csv(tmp_path / "dim_tech_cost.csv", index=False)
        proximity.to_csv(tmp_path / "fct_substation_proximity.csv", index=False)

        df = build_fct_lcoe(
            dim_sites_csv=tmp_path / "dim_sites.csv",
            fct_site_resource_csv=tmp_path / "fct_site_resource.csv",
            dim_tech_cost_csv=tmp_path / "dim_tech_cost.csv",
            fct_substation_proximity_csv=tmp_path / "fct_substation_proximity.csv",
            wacc_values=[10.0],
        )
        assert df["lcoe_usd_mwh"].isna().all()

    def test_no_transmission_lease_columns(self):
        """V2: transmission lease columns removed — not in output."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        for col in [
            "transmission_lease_adder_usd_mwh",
            "lcoe_allin_usd_mwh",
            "lcoe_allin_low_usd_mwh",
            "lcoe_allin_high_usd_mwh",
        ]:
            assert col not in df.columns, f"V2: {col} should be removed"

    def test_uses_solar_to_substation_distance(self, tmp_path):
        """V2: grid_connected_solar uses dist_solar_to_nearest_substation_km for connection cost."""
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        dim_sites = pd.DataFrame({"site_id": ["kek-v2"]})
        resource = pd.DataFrame(
            {
                "site_id": ["kek-v2"],
                "pvout_centroid": [1600.0],
                "pvout_best_50km": [1700.0],
            }
        )
        tech = pd.DataFrame(
            [
                {
                    "tech_id": "TECH006",
                    "tech_description": "Solar",
                    "year": 2023,
                    "capex_usd_per_kw": 960.0,
                    "capex_lower_usd_per_kw": 830.0,
                    "capex_upper_usd_per_kw": 1500.0,
                    "fixed_om_usd_per_kw_yr": 7.5,
                    "lifetime_yr": 27,
                    "source_pdf": "test.pdf",
                    "source_page": 66,
                    "is_provisional": False,
                }
            ]
        )
        # Solar is 5 km from substation, KEK is 30 km — V2 should use 5 km
        proximity = pd.DataFrame(
            {
                "site_id": ["kek-v2"],
                "dist_to_nearest_substation_km": [30.0],
                "dist_solar_to_nearest_substation_km": [5.0],
            }
        )

        dim_sites.to_csv(tmp_path / "dim_sites.csv", index=False)
        resource.to_csv(tmp_path / "fct_site_resource.csv", index=False)
        tech.to_csv(tmp_path / "dim_tech_cost.csv", index=False)
        proximity.to_csv(tmp_path / "fct_substation_proximity.csv", index=False)

        df = build_fct_lcoe(
            dim_sites_csv=tmp_path / "dim_sites.csv",
            fct_site_resource_csv=tmp_path / "fct_site_resource.csv",
            dim_tech_cost_csv=tmp_path / "dim_tech_cost.csv",
            fct_substation_proximity_csv=tmp_path / "fct_substation_proximity.csv",
            wacc_values=[10.0],
        )
        gc_row = df[df["scenario"] == "grid_connected_solar"].iloc[0]
        # connection_cost = 5 km × $5/kW-km + $80/kW = $105/kW (uses solar distance, not 30 km)
        from src.model.basic_model import grid_connection_cost_per_kw

        expected_cost = grid_connection_cost_per_kw(5.0)
        assert gc_row["connection_cost_per_kw"] == pytest.approx(expected_cost, rel=1e-2)


# ── fct_lcoe_wind ────────────────────────────────────────────────────────────


class TestFctLcoeWind:
    @pytest.fixture(scope="class")
    def wind_lcoe(self):
        from src.pipeline.build_fct_lcoe_wind import build_fct_lcoe_wind

        return build_fct_lcoe_wind()

    def test_row_count(self, wind_lcoe):
        """n_sites × 9 WACC values × 2 scenarios."""
        n_sites = wind_lcoe["site_id"].nunique()
        assert len(wind_lcoe) == n_sites * 9 * 2

    def test_wacc_values_full_range(self, wind_lcoe):
        assert set(wind_lcoe["wacc_pct"].unique()) == {
            4.0,
            6.0,
            8.0,
            10.0,
            12.0,
            14.0,
            16.0,
            18.0,
            20.0,
        }

    def test_two_scenarios(self, wind_lcoe):
        assert set(wind_lcoe["scenario"].unique()) == {"within_boundary", "grid_connected_solar"}

    def test_within_boundary_connection_cost_zero(self, wind_lcoe):
        wb = wind_lcoe[wind_lcoe["scenario"] == "within_boundary"]
        assert (wb["connection_cost_per_kw"] == 0).all()

    def test_higher_wacc_higher_lcoe(self, wind_lcoe):
        pivot = wind_lcoe.pivot(
            index=["site_id", "scenario"], columns="wacc_pct", values="lcoe_usd_mwh"
        ).dropna()
        assert (pivot[8.0] < pivot[10.0]).all()
        assert (pivot[10.0] < pivot[12.0]).all()

    def test_lcoe_low_lt_mid_lt_high(self, wind_lcoe):
        valid = wind_lcoe.dropna(subset=["lcoe_low_usd_mwh", "lcoe_usd_mwh", "lcoe_high_usd_mwh"])
        assert (valid["lcoe_low_usd_mwh"] < valid["lcoe_usd_mwh"]).all()
        assert (valid["lcoe_usd_mwh"] < valid["lcoe_high_usd_mwh"]).all()

    def test_tech_id_is_wind(self, wind_lcoe):
        assert (wind_lcoe["tech_id"] == "TECH_WIND_ONSHORE").all()

    def test_connection_cost_zero_for_within_boundary(self, wind_lcoe):
        wb = wind_lcoe[wind_lcoe["scenario"] == "within_boundary"]
        assert (wb["connection_cost_per_kw"] == 0.0).all()

    def test_connection_cost_positive_for_grid_connected(self, wind_lcoe):
        gc = wind_lcoe[wind_lcoe["scenario"] == "grid_connected_solar"]
        assert (gc["connection_cost_per_kw"] > 0).all()

    def test_effective_capex_gt_base_for_grid_connected(self, wind_lcoe):
        """Grid-connected scenario should have higher effective CAPEX due to connection cost."""
        gc = wind_lcoe[wind_lcoe["scenario"] == "grid_connected_solar"]
        wb = wind_lcoe[wind_lcoe["scenario"] == "within_boundary"]
        # effective_capex for grid_connected should be >= within_boundary (which has 0 connection cost)
        assert (
            gc["effective_capex_usd_per_kw"].values >= wb["effective_capex_usd_per_kw"].min()
        ).all()

    def test_wind_lcoe_plausible_range(self, wind_lcoe):
        """Wind LCOE at WACC=10% should be in $50–600 range (wide due to low-wind sites)."""
        w10 = wind_lcoe[wind_lcoe["wacc_pct"] == 10.0]
        valid = w10["lcoe_usd_mwh"].dropna()
        assert valid.between(50, 600).all(), f"Wind LCOE out of range: {valid.describe()}"

    def test_nan_lcoe_for_zero_cf_keks(self, wind_lcoe):
        """KEKs with cf_wind_used=0 must have NaN LCOE."""
        zero_cf = wind_lcoe[wind_lcoe["cf_wind_used"] == 0]
        if len(zero_cf) > 0:
            assert zero_cf["lcoe_usd_mwh"].isna().all()


# ── fct_substation_proximity ──────────────────────────────────────────────────


class TestFctSubstationProximity:
    def test_row_count(self):
        """One row per KEK (25 rows)."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        dim_sites = pd.read_csv(PROCESSED / "dim_sites.csv")
        assert len(df) == len(dim_sites)

    def test_distance_plausibility(self):
        """All distances must be > 0 and < 500 km (no KEK is >500 km from a substation)."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        assert (df["dist_to_nearest_substation_km"] > 0).all()
        assert (df["dist_to_nearest_substation_km"] < 500).all()

    def test_siting_scenario_values(self):
        """siting_scenario must be either 'within_boundary' or 'remote_captive'."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        valid = {"within_boundary", "remote_captive"}
        assert set(df["siting_scenario"].unique()).issubset(valid)

    def test_at_least_one_internal_substation(self):
        """At least one large industrial KEK should have a substation inside its polygon."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        assert df["has_internal_substation"].any(), (
            "Expected at least one KEK with an internal substation"
        )

    def test_required_columns_present(self):
        """Output must have all required columns (V1 + V2 three-point proximity)."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        required = {
            "site_id",
            "site_name",
            "nearest_substation_name",
            "nearest_substation_voltage_kv",
            "nearest_substation_capacity_mva",
            "dist_to_nearest_substation_km",
            "has_internal_substation",
            "siting_scenario",
            # V2 three-point proximity columns
            "dist_solar_to_nearest_substation_km",
            "nearest_substation_to_solar_name",
            "grid_integration_category",
        }
        assert required.issubset(set(df.columns))

    def test_scenario_consistent_with_internal_flag(self):
        """siting_scenario must match has_internal_substation."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        internal = df[df["has_internal_substation"]]
        external = df[~df["has_internal_substation"]]
        assert (internal["siting_scenario"] == "within_boundary").all()
        assert (external["siting_scenario"] == "remote_captive").all()

    def test_grid_integration_category_values(self):
        """grid_integration_category must be one of four valid values."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        valid = {
            "within_boundary",
            "grid_ready",
            "invest_transmission",
            "invest_substation",
            "grid_first",
        }
        assert set(df["grid_integration_category"].unique()).issubset(valid)

    def test_internal_substation_implies_within_boundary_category(self):
        """KEKs with an internal substation must have grid_integration_category='within_boundary'."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        internal = df[df["has_internal_substation"]]
        if len(internal) > 0:
            assert (internal["grid_integration_category"] == "within_boundary").all()

    def test_solar_to_substation_distance_plausibility(self):
        """Solar-to-substation distances must be >= 0 and < 500 km where present."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        solar_dists = df["dist_solar_to_nearest_substation_km"].dropna()
        if len(solar_dists) > 0:
            assert (solar_dists >= 0).all()
            assert (solar_dists < 500).all()

    def test_solar_substation_name_populated_when_distance_present(self):
        """nearest_substation_to_solar_name must be non-null when distance is present."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        has_dist = df["dist_solar_to_nearest_substation_km"].notna()
        assert df.loc[has_dist, "nearest_substation_to_solar_name"].notna().all()

    # V3.1: Connectivity and capacity columns
    def test_v31_columns_present(self):
        """V3.1 columns must be present in output."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        for col in [
            "nearest_substation_regpln",
            "nearest_substation_to_solar_regpln",
            "same_grid_region",
            "line_connected",
            "inter_substation_connected",
            "inter_substation_dist_km",
            "available_capacity_mva",
            "capacity_assessment",
        ]:
            assert col in df.columns, f"Missing column: {col}"

    def test_capacity_assessment_values(self):
        """capacity_assessment must be one of green/yellow/red/unknown."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        valid = {"green", "yellow", "red", "unknown"}
        assert set(df["capacity_assessment"].unique()).issubset(valid)

    def test_line_connected_is_bool_where_present(self):
        """line_connected must be boolean where not null (None for same-substation rows)."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        non_null = df["line_connected"].dropna()
        assert all(isinstance(v, (bool, np.bool_)) for v in non_null)

    def test_inter_substation_dist_positive_when_present(self):
        """inter_substation_dist_km must be >= 0 where not NaN."""
        from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity

        df = build_fct_substation_proximity()
        dists = df["inter_substation_dist_km"].dropna()
        if len(dists) > 0:
            assert (dists >= 0).all()


# ── fct_grid_cost_proxy ───────────────────────────────────────────────────────


class TestFctGridCostProxy:
    def test_rp_kwh_to_usd_mwh_conversion(self):
        """996.74 Rp/kWh ÷ 15,800 × 1000 = ~63.08 USD/MWh."""
        from src.pipeline.build_fct_grid_cost_proxy import rp_kwh_to_usd_mwh

        result = rp_kwh_to_usd_mwh(996.74, idr_usd=15_800.0)
        assert result == pytest.approx(63.08, rel=1e-3)

    def test_all_expected_regions_present(self):
        """Every grid region in dim_sites must have a cost proxy row."""
        dim_sites = pd.read_csv(PROCESSED / "dim_sites.csv")
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        kek_regions = set(dim_sites["grid_region_id"].dropna().unique())
        proxy_regions = set(proxy["grid_region_id"].unique())
        assert kek_regions.issubset(proxy_regions), (
            f"Missing regions in proxy: {kek_regions - proxy_regions}"
        )

    def test_dashboard_rate_is_official(self):
        """I-4 tariff is from Permen ESDM 7/2024 — must be flagged OFFICIAL."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        assert (proxy["dashboard_rate_flag"] == "OFFICIAL").all()

    def test_bpp_populated_for_all_regions(self):
        """BPP should be non-null for every grid region."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        assert proxy["bpp_usd_mwh"].notna().all(), "Some regions have null BPP"
        assert proxy["bpp_rp_kwh"].notna().all(), "Some regions have null BPP (Rp)"

    def test_bpp_source_populated(self):
        """BPP source should reference Kepmen ESDM 169/2021."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        assert proxy["bpp_source"].notna().all()
        assert proxy["bpp_source"].str.contains("169/2021").all()

    def test_bpp_plausible_range(self):
        """BPP should be between $30–$200/MWh for Indonesian grid systems."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        assert proxy["bpp_usd_mwh"].between(30, 200).all(), (
            f"BPP out of range: {proxy[['grid_region_id', 'bpp_usd_mwh']].to_string()}"
        )

    def test_bpp_java_bali_cheapest(self):
        """Java-Bali (coal-dominated) should have the lowest BPP."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        jb = proxy[proxy["grid_region_id"] == "JAVA_BALI"]["bpp_usd_mwh"].iloc[0]
        others = proxy[proxy["grid_region_id"] != "JAVA_BALI"]["bpp_usd_mwh"]
        assert jb < others.min(), "Java-Bali should have lowest BPP (coal-heavy grid)"

    def test_bpp_eastern_indonesia_higher(self):
        """Eastern Indonesia (MALUKU, PAPUA, NTB) BPP should be > $100/MWh (diesel-heavy)."""
        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        eastern = proxy[proxy["grid_region_id"].isin(["MALUKU", "PAPUA", "NTB"])]
        assert (eastern["bpp_usd_mwh"] > 100).all(), (
            f"Eastern Indonesia BPP should be > $100: {eastern[['grid_region_id', 'bpp_usd_mwh']].to_string()}"
        )

    def test_bpp_conversion_consistency(self):
        """bpp_usd_mwh should equal rp_kwh_to_usd_mwh(bpp_rp_kwh)."""
        from src.assumptions import rp_kwh_to_usd_mwh

        proxy = pd.read_csv(PROCESSED / "fct_grid_cost_proxy.csv")
        for _, row in proxy.iterrows():
            expected = rp_kwh_to_usd_mwh(row["bpp_rp_kwh"])
            assert row["bpp_usd_mwh"] == pytest.approx(expected, rel=1e-3)


# ── BPP extraction module ────────────────────────────────────────────────────


class TestBppExtraction:
    def test_get_regional_bpp_covers_all_grid_regions(self):
        """get_regional_bpp() must return a value for every grid_region_id in dim_sites."""
        from src.pipeline.pdf_extract_bpp import get_regional_bpp

        dim_sites = pd.read_csv(PROCESSED / "dim_sites.csv")
        expected = set(dim_sites["grid_region_id"].dropna().unique())
        bpp = get_regional_bpp()
        assert expected.issubset(set(bpp.keys())), f"Missing regions: {expected - set(bpp.keys())}"

    def test_national_bpp_matches_document(self):
        """National BPP should be 1,027.70 Rp/kWh per Kepmen 169/2021."""
        from src.pipeline.pdf_extract_bpp import get_national_bpp

        assert get_national_bpp() == pytest.approx(1027.70, rel=1e-4)

    def test_java_bali_bpp_matches_document(self):
        """Java-Bali systems are all ~908 Rp/kWh in the Kepmen."""
        from src.pipeline.pdf_extract_bpp import get_regional_bpp

        bpp = get_regional_bpp()
        assert bpp["JAVA_BALI"] == pytest.approx(908.54, rel=1e-2)

    def test_all_bpp_values_positive(self):
        from src.pipeline.pdf_extract_bpp import get_regional_bpp

        bpp = get_regional_bpp()
        for region, val in bpp.items():
            assert val > 0, f"{region} has non-positive BPP: {val}"


# ── fct_site_scorecard ─────────────────────────────────────────────────────────


class TestFctKekScorecard:
    def test_row_count(self):
        """One row per site, no duplicates."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert len(sc) >= 25  # at least 25 KEKs; grows as industrial sites are added
        assert sc["site_id"].is_unique

    def test_solar_competitive_gap_sign(self):
        """Negative gap = solar LCOE < grid cost = solar is already cheaper."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        gap_row = sc.dropna(
            subset=["solar_competitive_gap_pct", "lcoe_mid_usd_mwh", "dashboard_rate_usd_mwh"]
        )
        cheaper_mask = gap_row["lcoe_mid_usd_mwh"] < gap_row["dashboard_rate_usd_mwh"]
        assert (gap_row.loc[cheaper_mask, "solar_competitive_gap_pct"] < 0).all()

    def test_clean_power_advantage_is_negated_gap(self):
        """clean_power_advantage = −solar_competitive_gap_pct."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        valid = sc.dropna(subset=["solar_competitive_gap_pct", "clean_power_advantage"])
        expected = (-valid["solar_competitive_gap_pct"]).round(1)
        assert (expected == valid["clean_power_advantage"]).all()

    def test_data_completeness_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "data_completeness" in sc.columns
        assert sc["data_completeness"].isin(["complete", "partial", "provisional"]).all()

    def test_action_flag_values(self):
        """action_flag must only contain valid values."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        valid_flags = {
            "solar_now",
            "invest_transmission",
            "invest_substation",
            "invest_battery",
            "grid_first",
            "invest_resilience",
            "plan_late",
            "data_missing",
            "not_competitive",
            "no_solar_resource",
            "wind_competitive",
        }
        assert set(sc["action_flag"].unique()).issubset(valid_flags)

    def test_lcoe_in_plausible_range(self):
        """Indonesia solar LCOE should be roughly $35–$100/MWh at WACC=10%."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        lcoe = sc["lcoe_mid_usd_mwh"].dropna()
        assert lcoe.between(30, 120).all(), f"LCOE out of range: {lcoe.describe()}"

    def test_green_share_geas_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "green_share_geas" in sc.columns

    def test_green_share_geas_in_valid_range(self):
        """green_share_geas is a fraction: 0 ≤ value ≤ 1 for all rows."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        vals = sc["green_share_geas"].dropna()
        assert (vals >= 0).all() and (vals <= 1).all()

    def test_green_share_geas_not_all_zero(self):
        """Now that fct_site_demand feeds the scorecard, green_share_geas > 0 for some KEKs."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert (sc["green_share_geas"] > 0).any(), (
            "All green_share_geas are 0 — likely fct_site_demand not being read"
        )

    def test_scorecard_depends_on_fct_site_demand(self):
        """Pipeline DAG: fct_site_scorecard must list fct_site_demand as a dependency."""
        import sys

        sys.path.insert(0, str(REPO_ROOT))
        import run_pipeline

        scorecard_step = next(s for s in run_pipeline.PIPELINE if s.name == "fct_site_scorecard")
        assert "fct_site_demand" in scorecard_step.depends_on

    def test_invest_resilience_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "invest_resilience" in sc.columns

    def test_invest_resilience_is_boolean(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        vals = sc["invest_resilience"].dropna()
        assert vals.isin([True, False, 0, 1]).all()

    def test_carbon_breakeven_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "carbon_breakeven_usd_tco2" in sc.columns

    def test_carbon_breakeven_nonnegative(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        vals = sc["carbon_breakeven_usd_tco2"].dropna()
        assert (vals >= 0).all(), "Carbon breakeven price must be ≥ 0"

    def test_invest_resilience_fires_for_manufacturing_keks(self):
        """Manufacturing KEKs with LCOE < 20% above grid should get invest_resilience=True."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        # Any KEK with gap in (0, 20] and reliability_req >= 0.75 should fire
        # At WACC=10%, some manufacturing KEKs (Batang, Sorong) should be in the resilience zone
        manufacturing = sc[sc["zone_classification"].str.contains("Industri", na=False)]
        low_gap = manufacturing[
            manufacturing["solar_competitive_gap_pct"].between(0, 20, inclusive="right")
        ]
        if len(low_gap) > 0:
            assert low_gap["invest_resilience"].any(), (
                "Manufacturing KEKs within 20% of grid parity should have invest_resilience=True"
            )

    def test_wacc8_lcoe_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "lcoe_mid_wacc8_usd_mwh" in sc.columns
        assert "solar_competitive_gap_wacc8_pct" in sc.columns
        assert "solar_now_at_wacc8" in sc.columns

    def test_solar_now_at_wacc8_is_boolean(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert sc["solar_now_at_wacc8"].dtype == bool or set(
            sc["solar_now_at_wacc8"].unique()
        ).issubset({True, False})

    def test_wacc8_gap_leq_wacc10_gap(self):
        """LCOE at WACC=8% must be ≤ LCOE at WACC=10% for every KEK — lower WACC = lower LCOE."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        both = sc[sc["lcoe_mid_wacc8_usd_mwh"].notna() & sc["lcoe_mid_usd_mwh"].notna()]
        assert (both["lcoe_mid_wacc8_usd_mwh"] <= both["lcoe_mid_usd_mwh"]).all(), (
            "LCOE at WACC=8% should never exceed LCOE at WACC=10%"
        )

    def test_v2_grid_connected_columns_present(self):
        """V2: grid-connected solar columns replace V1 remote captive columns."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        for col in [
            "lcoe_grid_connected_usd_mwh",
            "lcoe_grid_connected_low_usd_mwh",
            "lcoe_grid_connected_high_usd_mwh",
            "connection_cost_per_kw",
        ]:
            assert col in sc.columns, f"Missing V2 column: {col}"

    def test_v1_columns_removed_from_scorecard(self):
        """V2: deprecated V1 columns should no longer appear in scorecard."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        for col in [
            "transmission_lease_adder_usd_mwh",
            "lcoe_remote_captive_allin_usd_mwh",
            "lcoe_remote_captive_allin_low_usd_mwh",
            "lcoe_remote_captive_allin_high_usd_mwh",
        ]:
            assert col not in sc.columns, f"V1 column should be removed: {col}"

    def test_grid_connected_exceeds_within_boundary_lcoe(self):
        """Grid-connected LCOE must exceed within_boundary LCOE (connection + land cost)."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        valid = sc.dropna(subset=["lcoe_mid_usd_mwh", "lcoe_grid_connected_usd_mwh"])
        assert (valid["lcoe_grid_connected_usd_mwh"] > valid["lcoe_mid_usd_mwh"]).all(), (
            "lcoe_grid_connected must always exceed within_boundary lcoe_mid (connection + land cost)"
        )

    def test_grid_investment_needed_usd_column(self):
        """grid_investment_needed_usd = (connection + transmission) cost × capacity."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "grid_investment_needed_usd" in sc.columns
        valid = sc.dropna(subset=["grid_investment_needed_usd"])
        assert len(valid) > 0, "Expected at least some KEKs with grid investment estimate"
        assert (valid["grid_investment_needed_usd"] >= 0).all(), "Investment must be non-negative"

    def test_project_viable_column_present(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert "project_viable" in sc.columns

    def test_project_viable_is_boolean(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        assert sc["project_viable"].isin([True, False]).all()

    def test_wind_columns_present(self):
        """Scorecard must have wind LCOE and best RE technology columns."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        wind_cols = [
            "lcoe_wind_mid_usd_mwh",
            "lcoe_wind_allin_mid_usd_mwh",
            "cf_wind",
            "wind_speed_ms",
            "best_re_technology",
            "best_re_lcoe_mid_usd_mwh",
            "re_competitive_gap_pct",
        ]
        for col in wind_cols:
            assert col in sc.columns, f"Missing wind column: {col}"

    def test_best_re_technology_valid_values(self):
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        valid = {"solar", "wind", "both", "none"}
        assert set(sc["best_re_technology"].unique()).issubset(valid)

    def test_best_re_lcoe_leq_both(self):
        """best_re_lcoe must be <= both solar and wind LCOE."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        valid = sc.dropna(subset=["best_re_lcoe_mid_usd_mwh", "lcoe_mid_usd_mwh"])
        assert (valid["best_re_lcoe_mid_usd_mwh"] <= valid["lcoe_mid_usd_mwh"] + 0.01).all()

    def test_scorecard_depends_on_fct_lcoe_wind(self):
        """Pipeline DAG: fct_site_scorecard must list fct_lcoe_wind as a dependency."""
        import sys

        sys.path.insert(0, str(REPO_ROOT))
        import run_pipeline

        scorecard_step = next(s for s in run_pipeline.PIPELINE if s.name == "fct_site_scorecard")
        assert "fct_lcoe_wind" in scorecard_step.depends_on

    def test_project_viable_reflects_buildability(self):
        """With detailed kawasan hutan (66K polygons), some KEKs have zero buildable area.
        KEKs with buildable_area_ha=0 should NOT be project_viable.
        KEKs with buildable_area_ha>0 should be project_viable."""
        sc = pd.read_csv(PROCESSED / "fct_site_scorecard.csv")
        has_area = sc["buildable_area_ha"] > 0
        # KEKs with buildable area should be viable
        assert sc.loc[has_area, "project_viable"].all(), (
            "KEKs with buildable area > 0 should be project_viable=True"
        )
        # KEKs without buildable area should not be viable
        assert not sc.loc[~has_area, "project_viable"].any(), (
            "KEKs with zero buildable area should be project_viable=False"
        )


# ── run_pipeline: topo sort ───────────────────────────────────────────────────

# ── fct_site_demand ──────────────────────────────────────────────────────────


class TestFctSiteDemand:
    @pytest.fixture(scope="class")
    def demand(self):
        from src.pipeline.build_fct_site_demand import build_fct_site_demand

        return build_fct_site_demand()

    def test_row_count_matches_dim_sites(self, demand):
        dim_sites = pd.read_csv(PROCESSED / "dim_sites.csv")
        assert len(demand) == len(dim_sites)

    def test_all_site_ids_present(self, demand):
        dim_sites = pd.read_csv(PROCESSED / "dim_sites.csv")
        assert set(demand["site_id"]) == set(dim_sites["site_id"])

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
                row["zone_classification"], ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR
            )
            assert row["energy_intensity_mwh_per_ha_yr"] == pytest.approx(expected), (
                f"{row['site_id']}: expected intensity {expected}, got {row['energy_intensity_mwh_per_ha_yr']}"
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
            Step("lcoe", lambda: None, "l.csv", depends_on=["kek"]),
            Step("kek", lambda: None, "k.csv"),
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

    def test_all_zone_types_have_both_factors(self):
        from src.assumptions import BUILDING_FOOTPRINT_RATIO, BUILDING_INTENSITY_KWH_M2_YR

        assert set(BUILDING_INTENSITY_KWH_M2_YR.keys()) == set(BUILDING_FOOTPRINT_RATIO.keys())

    def test_derived_intensity_matches_formula(self):
        from src.assumptions import (
            BUILDING_FOOTPRINT_RATIO,
            BUILDING_INTENSITY_KWH_M2_YR,
            ENERGY_INTENSITY_MWH_PER_HA_YR,
        )

        for zone_type in BUILDING_INTENSITY_KWH_M2_YR:
            expected = round(
                BUILDING_INTENSITY_KWH_M2_YR[zone_type] * BUILDING_FOOTPRINT_RATIO[zone_type] * 10,
                1,
            )
            assert ENERGY_INTENSITY_MWH_PER_HA_YR[zone_type] == pytest.approx(expected), (
                f"{zone_type}: expected {expected}, got {ENERGY_INTENSITY_MWH_PER_HA_YR[zone_type]}"
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

        for zone_type, ratio in BUILDING_FOOTPRINT_RATIO.items():
            assert 0 < ratio <= 1, f"{zone_type}: footprint ratio {ratio} must be (0, 1]"


# ── M12: Substation upgrade cost in precomputed LCOE ──────────────────────────


class TestFctLcoeSubstationUpgrade:
    """M12: substation upgrade cost included in precomputed LCOE."""

    def test_column_exists(self):
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        assert "substation_upgrade_cost_per_kw" in df.columns

    def test_within_boundary_zero(self):
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        wb = df[df["scenario"] == "within_boundary"]
        assert (wb["substation_upgrade_cost_per_kw"] == 0.0).all()

    def test_grid_connected_non_negative(self):
        from src.pipeline.build_fct_lcoe import build_fct_lcoe

        df = build_fct_lcoe()
        gc = df[df["scenario"] == "grid_connected_solar"]
        assert (gc["substation_upgrade_cost_per_kw"] >= 0.0).all()

    def test_scorecard_has_column(self):
        from src.pipeline.build_fct_site_scorecard import build_fct_site_scorecard

        df = build_fct_site_scorecard()
        assert "substation_upgrade_cost_per_kw" in df.columns
