"""
tests/test_build_dim_sites.py — unified dimension table builder tests.

Covers:
  - KEK rows preserved (25 rows, original data intact)
  - Industrial sites added with correct site_type
  - No duplicate site_ids
  - Grid region auto-assignment for new sites
  - Schema has all required columns
  - Total row count = 25 KEKs + 46 standalone + 10 clusters = 81
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.build_dim_sites import build_dim_sites

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"


@pytest.fixture(scope="module")
def dim_sites() -> pd.DataFrame:
    """Build dim_sites once for all tests in this module."""
    return build_dim_sites()


class TestDimSitesBasic:
    def test_total_row_count(self, dim_sites: pd.DataFrame):
        """25 KEKs + 46 standalone + 10 cluster = 81 total."""
        assert len(dim_sites) == 81

    def test_no_duplicate_site_ids(self, dim_sites: pd.DataFrame):
        assert dim_sites["site_id"].is_unique

    def test_site_type_counts(self, dim_sites: pd.DataFrame):
        counts = dim_sites["site_type"].value_counts().to_dict()
        assert counts["kek"] == 25
        assert counts["standalone"] == 46
        assert counts["cluster"] == 10


class TestKekPreservation:
    def test_kek_rows_have_grid_region(self, dim_sites: pd.DataFrame):
        keks = dim_sites[dim_sites["site_type"] == "kek"]
        assert keks["grid_region_id"].notna().all()

    def test_kek_rows_have_coordinates(self, dim_sites: pd.DataFrame):
        keks = dim_sites[dim_sites["site_type"] == "kek"]
        assert keks["latitude"].notna().all()
        assert keks["longitude"].notna().all()

    def test_kek_zone_classification_populated(self, dim_sites: pd.DataFrame):
        """KEKs should have zone_classification (mapped from kek_type)."""
        keks = dim_sites[dim_sites["site_type"] == "kek"]
        # Most KEKs have kek_type; a few might be null from source data
        populated = keks["zone_classification"].notna().sum()
        assert populated >= 20, f"Only {populated}/25 KEKs have zone_classification"


class TestIndustrialSites:
    def test_industrial_sectors(self, dim_sites: pd.DataFrame):
        ind = dim_sites[dim_sites["site_type"].isin(["standalone", "cluster"])]
        sectors = set(ind["sector"].unique())
        assert "steel" in sectors
        assert "cement" in sectors
        assert "aluminium" in sectors
        assert "fertilizer" in sectors
        assert "nickel" in sectors

    def test_industrial_grid_region_assigned(self, dim_sites: pd.DataFrame):
        ind = dim_sites[dim_sites["site_type"].isin(["standalone", "cluster"])]
        assert ind["grid_region_id"].notna().all(), "All industrial sites need grid_region_id"

    def test_industrial_grid_regions_valid(self, dim_sites: pd.DataFrame):
        ind = dim_sites[dim_sites["site_type"].isin(["standalone", "cluster"])]
        valid_regions = {
            "JAVA_BALI",
            "SUMATERA",
            "KALIMANTAN",
            "SULAWESI",
            "MALUKU",
            "PAPUA",
            "NTB",
        }
        actual = set(ind["grid_region_id"].unique())
        assert actual.issubset(valid_regions), f"Unknown regions: {actual - valid_regions}"

    def test_industrial_capacity_populated(self, dim_sites: pd.DataFrame):
        # Standalone industrial sites must have positive capacity.
        # Nickel clusters (tracker-driven IIA) may have NaN if no Processing children
        # fell within the child-aggregation radius — known gap documented in
        # build_industrial_sites.py. Clusters with capacity must still be positive.
        standalone = dim_sites[dim_sites["site_type"] == "standalone"]
        assert standalone["capacity_annual_tonnes"].notna().all()
        assert (standalone["capacity_annual_tonnes"] > 0).all()

        clusters = dim_sites[dim_sites["site_type"] == "cluster"]
        with_capacity = clusters[clusters["capacity_annual_tonnes"].notna()]
        assert (with_capacity["capacity_annual_tonnes"] > 0).all()

    def test_industrial_cbam_product_type(self, dim_sites: pd.DataFrame):
        ind = dim_sites[dim_sites["site_type"].isin(["standalone", "cluster"])]
        assert ind["cbam_product_type"].notna().all()

    def test_kek_cbam_product_type_null(self, dim_sites: pd.DataFrame):
        """KEKs use 3-signal detection, so cbam_product_type should be null."""
        keks = dim_sites[dim_sites["site_type"] == "kek"]
        assert keks["cbam_product_type"].isna().all()


class TestSchema:
    def test_required_columns_present(self, dim_sites: pd.DataFrame):
        required = [
            "site_id",
            "site_name",
            "site_type",
            "sector",
            "province",
            "latitude",
            "longitude",
            "grid_region_id",
            "reliability_req",
            "data_vintage",
        ]
        for col in required:
            assert col in dim_sites.columns, f"Missing column: {col}"

    def test_coordinates_in_indonesia(self, dim_sites: pd.DataFrame):
        """All sites should be within Indonesia's bounding box."""
        assert (dim_sites["latitude"] >= -12).all()
        assert (dim_sites["latitude"] <= 8).all()
        assert (dim_sites["longitude"] >= 94).all()
        assert (dim_sites["longitude"] <= 142).all()
