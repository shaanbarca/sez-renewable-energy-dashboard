"""
tests/test_geo_utils.py — shared geospatial utility tests.

Covers:
  - haversine_km: zero distance, known distance (Jakarta→Surabaya)
  - proximity_match: nearby match, no match, empty inputs
  - direct_match: matching IDs, missing IDs, empty inputs
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.pipeline.geo_utils import (
    apply_contractual_overrides,
    direct_match,
    haversine_km,
    proximity_match,
)


class TestHaversine:
    def test_zero_distance(self):
        assert haversine_km(-6.2, 106.8, -6.2, 106.8) == 0.0

    def test_known_distance_jakarta_surabaya(self):
        """Jakarta (-6.2, 106.8) to Surabaya (-7.25, 112.75) ≈ 660 km."""
        d = haversine_km(-6.2, 106.8, -7.25, 112.75)
        assert 650 < d < 680, f"Expected ~660 km, got {d:.0f} km"

    def test_symmetric(self):
        d1 = haversine_km(-6.2, 106.8, -7.25, 112.75)
        d2 = haversine_km(-7.25, 112.75, -6.2, 106.8)
        assert d1 == pytest.approx(d2)

    def test_short_distance(self):
        """Two points ~1 km apart should return ~1 km."""
        # ~0.009 degrees latitude ≈ 1 km
        d = haversine_km(0.0, 0.0, 0.009, 0.0)
        assert 0.9 < d < 1.1


class TestProximityMatch:
    def _make_sites(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def _make_plants(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_finds_nearby_plant(self):
        sites = self._make_sites([{"site_id": "site-a", "latitude": -6.0, "longitude": 106.0}])
        plants = self._make_plants([{"plant": "P1", "latitude": -6.01, "longitude": 106.01}])
        result = proximity_match(sites, plants, buffer_km=50)
        assert result.iloc[0]["site_id"] == "site-a"
        assert result.iloc[0]["dist_km"] is not None
        assert result.iloc[0]["dist_km"] < 50

    def test_no_match_outside_buffer(self):
        sites = self._make_sites([{"site_id": "site-a", "latitude": -6.0, "longitude": 106.0}])
        plants = self._make_plants([{"plant": "P1", "latitude": 0.0, "longitude": 110.0}])
        result = proximity_match(sites, plants, buffer_km=50)
        assert result.iloc[0]["site_id"] is None
        assert result.iloc[0]["dist_km"] is None

    def test_empty_sites(self):
        sites = pd.DataFrame(columns=["site_id", "latitude", "longitude"])
        plants = self._make_plants([{"plant": "P1", "latitude": -6.0, "longitude": 106.0}])
        result = proximity_match(sites, plants, buffer_km=50)
        assert len(result) == 1
        assert result.iloc[0]["site_id"] is None

    def test_empty_plants(self):
        sites = self._make_sites([{"site_id": "site-a", "latitude": -6.0, "longitude": 106.0}])
        plants = pd.DataFrame(columns=["plant", "latitude", "longitude"])
        result = proximity_match(sites, plants, buffer_km=50)
        assert len(result) == 0

    def test_picks_nearest_site(self):
        sites = self._make_sites(
            [
                {"site_id": "far", "latitude": -6.5, "longitude": 106.5},
                {"site_id": "near", "latitude": -6.001, "longitude": 106.001},
            ]
        )
        plants = self._make_plants([{"plant": "P1", "latitude": -6.0, "longitude": 106.0}])
        result = proximity_match(sites, plants, buffer_km=100)
        assert result.iloc[0]["site_id"] == "near"

    def test_custom_id_column(self):
        sites = pd.DataFrame([{"site_id": "s1", "latitude": -6.0, "longitude": 106.0}])
        plants = pd.DataFrame([{"plant": "P1", "latitude": -6.01, "longitude": 106.01}])
        result = proximity_match(sites, plants, buffer_km=50, site_id_col="site_id")
        assert result.iloc[0]["site_id"] == "s1"


class TestDirectMatch:
    def test_matching_id(self):
        sites = pd.DataFrame([{"site_id": "plant-a"}])
        plants = pd.DataFrame(
            [
                {"site_id": "plant-a", "capacity": 100},
                {"site_id": "plant-b", "capacity": 200},
            ]
        )
        result = direct_match(sites, plants)
        assert len(result) == 1
        assert result.iloc[0]["site_id"] == "plant-a"

    def test_no_matching_id(self):
        sites = pd.DataFrame([{"site_id": "plant-x"}])
        plants = pd.DataFrame([{"site_id": "plant-a", "capacity": 100}])
        result = direct_match(sites, plants)
        assert len(result) == 0

    def test_empty_sites(self):
        sites = pd.DataFrame(columns=["site_id"])
        plants = pd.DataFrame([{"site_id": "plant-a", "capacity": 100}])
        result = direct_match(sites, plants)
        assert len(result) == 0

    def test_empty_plants(self):
        sites = pd.DataFrame([{"site_id": "plant-a"}])
        plants = pd.DataFrame(columns=["site_id", "capacity"])
        result = direct_match(sites, plants)
        assert len(result) == 0


class TestApplyContractualOverrides:
    """F12 (2026-05-09): contractual overrides on top of haversine match."""

    def _matched(self, rows: list[dict]) -> pd.DataFrame:
        # Mimics the output of proximity_match + direct_match concat
        return pd.DataFrame(rows)

    def _sites(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_override_pulls_in_unmatched_plant(self):
        """Plant outside spatial buffer (site_id=None) gets routed via override."""
        matched = self._matched(
            [
                {
                    "plant": "Mine-Mouth Coal A",
                    "latitude": -2.0,
                    "longitude": 103.0,
                    "site_id": None,
                    "dist_km": None,
                }
            ]
        )
        sites = self._sites([{"site_id": "smelter_x", "latitude": -3.0, "longitude": 105.0}])
        overrides = pd.DataFrame(
            [
                {
                    "site_id": "smelter_x",
                    "plant_name": "Mine-Mouth Coal A",
                    "plant_lat": -2.0,
                    "plant_lon": 103.0,
                    "source": "Annual report 2024",
                }
            ]
        )
        result = apply_contractual_overrides(matched, overrides, sites)
        assert result.iloc[0]["site_id"] == "smelter_x"
        assert result.iloc[0]["captive_match_method"] == "contractual"
        assert result.iloc[0]["captive_match_source"] == "Annual report 2024"
        assert result.iloc[0]["dist_km"] > 0  # recomputed from coords

    def test_override_replaces_wrong_spatial_match(self):
        """Plant matched to wrong nearest-neighbour gets re-routed."""
        matched = self._matched(
            [
                {
                    "plant": "Coal Plant B",
                    "latitude": -6.0,
                    "longitude": 106.0,
                    "site_id": "wrong_site",
                    "dist_km": 5.0,
                }
            ]
        )
        sites = self._sites(
            [
                {"site_id": "wrong_site", "latitude": -6.05, "longitude": 106.05},
                {"site_id": "right_site", "latitude": -6.5, "longitude": 106.5},
            ]
        )
        overrides = pd.DataFrame(
            [{"site_id": "right_site", "plant_name": "Coal Plant B", "source": "Disclosure"}]
        )
        result = apply_contractual_overrides(matched, overrides, sites)
        assert result.iloc[0]["site_id"] == "right_site"
        assert result.iloc[0]["captive_match_method"] == "contractual"

    def test_unmatched_plants_stay_spatial(self):
        """Plants not in the override file get captive_match_method='spatial'."""
        matched = self._matched(
            [
                {
                    "plant": "Some Plant",
                    "latitude": -6.0,
                    "longitude": 106.0,
                    "site_id": "site_y",
                    "dist_km": 3.0,
                }
            ]
        )
        sites = self._sites([{"site_id": "site_y", "latitude": -6.0, "longitude": 106.0}])
        overrides = pd.DataFrame(columns=["site_id", "plant_name", "source"])
        result = apply_contractual_overrides(matched, overrides, sites)
        assert result.iloc[0]["captive_match_method"] == "spatial"
        assert result.iloc[0]["captive_match_source"] is None

    def test_override_with_unknown_site_id_skipped(self):
        """Override pointing to a non-existent site_id is skipped, not crashed."""
        matched = self._matched(
            [
                {
                    "plant": "Plant C",
                    "latitude": -1.0,
                    "longitude": 100.0,
                    "site_id": None,
                    "dist_km": None,
                }
            ]
        )
        sites = self._sites([{"site_id": "real_site", "latitude": -2.0, "longitude": 101.0}])
        overrides = pd.DataFrame([{"site_id": "TYPO_SITE", "plant_name": "Plant C", "source": "x"}])
        result = apply_contractual_overrides(matched, overrides, sites)
        # Override is ignored — row stays unmatched
        assert result.iloc[0]["site_id"] is None
        assert result.iloc[0]["captive_match_method"] == "spatial"

    def test_plant_name_match_is_case_insensitive(self):
        matched = self._matched(
            [
                {
                    "plant": "Borneo Coal",
                    "latitude": 0.0,
                    "longitude": 113.0,
                    "site_id": None,
                    "dist_km": None,
                }
            ]
        )
        sites = self._sites([{"site_id": "kal_smelter", "latitude": 0.5, "longitude": 113.5}])
        overrides = pd.DataFrame(
            [{"site_id": "kal_smelter", "plant_name": "BORNEO COAL", "source": "report"}]
        )
        result = apply_contractual_overrides(matched, overrides, sites)
        assert result.iloc[0]["site_id"] == "kal_smelter"
        assert result.iloc[0]["captive_match_method"] == "contractual"

    def test_empty_overrides_is_noop(self):
        matched = self._matched(
            [
                {
                    "plant": "P",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "site_id": "s",
                    "dist_km": 1.0,
                }
            ]
        )
        result = apply_contractual_overrides(matched, pd.DataFrame(), pd.DataFrame())
        assert result.iloc[0]["captive_match_method"] == "spatial"
        assert result.iloc[0]["site_id"] == "s"
        assert "captive_match_source" in result.columns
