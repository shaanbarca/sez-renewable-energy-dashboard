"""
tests/test_build_fct_site_demand.py — demand dispatch regression test.

Locks in the fix for RV-pipeline-demand-regression (PR #22, commit 692fcc5).

Before the fix, all 56 non-KEK sites silently received the fleet-median
fallback (~376 GWh), masking real per-site demand that spans 2,000 GWh
(Pupuk Sriwidjaja) to 226,000 GWh (IMIP).

The builder now dispatches via SITE_TYPES[site_type].demand_method:
  - kek / ki           -> area_based         (area_ha x intensity_per_ha)
  - standalone / cluster -> sector_intensity (capacity_tonnes x intensity_per_tonne)

These tests fail loudly if the dispatch ever regresses.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.model.site_types import SITE_TYPES, SiteType
from src.pipeline.build_fct_site_demand import build_fct_site_demand

REPO_ROOT = Path(__file__).resolve().parents[1]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"


@pytest.fixture(scope="module")
def demand_with_types() -> pd.DataFrame:
    """fct_site_demand joined with site_type/sector from dim_sites."""
    demand = build_fct_site_demand()
    sites = pd.read_csv(PROCESSED / "dim_sites.csv")[["site_id", "site_type", "sector"]]
    return demand.merge(sites, on="site_id", how="left")


class TestDispatch:
    def test_at_least_one_sector_intensity_row(self, demand_with_types: pd.DataFrame):
        """Sector-intensity branch must actually fire — was 0 before the fix."""
        n = (demand_with_types["demand_source"] == "sector_intensity").sum()
        assert n > 0, "sector_intensity branch did not fire for any site"

    def test_no_standalone_or_cluster_uses_area_fallback(self, demand_with_types: pd.DataFrame):
        """The original regression: all 56 non-KEK sites fell into area_fallback_median."""
        non_kek = demand_with_types[demand_with_types["site_type"].isin(["standalone", "cluster"])]
        bad = non_kek[non_kek["demand_source"] == "area_fallback_median"]
        assert bad.empty, (
            f"{len(bad)} standalone/cluster sites are using area_fallback_median; "
            f"sample: {bad['site_id'].head(3).tolist()}"
        )

    def test_no_standalone_or_cluster_uses_area_x_intensity(self, demand_with_types: pd.DataFrame):
        """Standalone/cluster sites should never go through the area-based path at all."""
        non_kek = demand_with_types[demand_with_types["site_type"].isin(["standalone", "cluster"])]
        bad = non_kek[non_kek["demand_source"] == "area_x_intensity"]
        assert bad.empty, (
            f"{len(bad)} standalone/cluster sites went through area_x_intensity; dispatch is wrong"
        )

    def test_kek_sites_use_area_based_path(self, demand_with_types: pd.DataFrame):
        """KEKs must stay on the area_based path (area_x_intensity or area_fallback_median)."""
        kek_rows = demand_with_types[demand_with_types["site_type"] == "kek"]
        valid = {"area_x_intensity", "area_fallback_median"}
        offenders = kek_rows[~kek_rows["demand_source"].isin(valid)]
        assert offenders.empty, (
            f"{len(offenders)} KEK sites have a non-area demand_source; "
            f"sample: {offenders[['site_id', 'demand_source']].head(3).to_dict('records')}"
        )


class TestDemandSpread:
    def test_demand_is_not_constant_across_non_kek_sites(self, demand_with_types: pd.DataFrame):
        """The original symptom: every non-KEK site had the identical 376,205 MWh.

        Real demand should span at least one order of magnitude.
        """
        non_kek = demand_with_types[
            demand_with_types["site_type"].isin(["standalone", "cluster"])
        ].dropna(subset=["demand_mwh"])
        assert len(non_kek) >= 10, "expected at least 10 non-KEK sites with demand"
        ratio = non_kek["demand_mwh"].max() / non_kek["demand_mwh"].min()
        assert ratio >= 10, (
            f"non-KEK demand spread is only {ratio:.1f}x; expected >=10x. "
            f"Likely regressed to a near-constant fleet value."
        )

    def test_demand_uniqueness_in_non_kek_set(self, demand_with_types: pd.DataFrame):
        """Beyond spread: most non-KEK sites should have distinct demand values."""
        non_kek = demand_with_types[
            demand_with_types["site_type"].isin(["standalone", "cluster"])
        ].dropna(subset=["demand_mwh"])
        unique_ratio = non_kek["demand_mwh"].nunique() / len(non_kek)
        assert unique_ratio >= 0.5, (
            f"only {unique_ratio:.0%} of non-KEK demand values are unique; "
            f"suggests fleet-median regression"
        )


class TestSchema:
    def test_audit_columns_present(self, demand_with_types: pd.DataFrame):
        """The fix added three audit columns — make sure they survive future refactors."""
        for col in (
            "capacity_annual_tonnes",
            "sector_intensity_key",
            "sector_intensity_mwh_per_tonne",
        ):
            assert col in demand_with_types.columns, f"missing audit column: {col}"

    def test_sector_intensity_rows_carry_a_resolved_key(self, demand_with_types: pd.DataFrame):
        """If demand_source == sector_intensity, the key + multiplier must be populated."""
        rows = demand_with_types[demand_with_types["demand_source"] == "sector_intensity"]
        assert rows["sector_intensity_key"].notna().all()
        assert (rows["sector_intensity_mwh_per_tonne"] > 0).all()


class TestRegistryAlignment:
    def test_every_demand_source_is_consistent_with_registry(self, demand_with_types: pd.DataFrame):
        """Cross-check each row's demand_source against SITE_TYPES[site_type].demand_method."""
        area_sources = {"area_x_intensity", "area_fallback_median"}
        sector_sources = {"sector_intensity", "sector_intensity_missing_inputs"}
        for _, row in demand_with_types.iterrows():
            site_type = row["site_type"]
            if pd.isna(site_type):
                continue
            try:
                method = SITE_TYPES[SiteType(site_type)].demand_method
            except (ValueError, KeyError):
                continue
            source = row["demand_source"]
            if pd.isna(source):
                continue
            if method == "area_based":
                assert source in area_sources, (
                    f"{row['site_id']} ({site_type}) expected area-based source, got {source}"
                )
            elif method == "sector_intensity":
                assert source in sector_sources, (
                    f"{row['site_id']} ({site_type}) expected sector source, got {source}"
                )
