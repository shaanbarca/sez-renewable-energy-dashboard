# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Tests for F5 RUPTL §V.9 transmission-link feasibility helpers."""

from __future__ import annotations

import pandas as pd

from src.pipeline.build_fct_transmission_link_ruptl_signal import (
    _worst_status,
    comparator_feasibility_for_region,
    region_worst_status_map,
)


class TestWorstStatus:
    def test_picks_most_pessimistic(self):
        assert _worst_status(["under_study", "not_feasible", "in_construction"]) == "not_feasible"

    def test_under_study_beats_in_construction(self):
        assert _worst_status(["in_construction", "under_study"]) == "under_study"

    def test_empty_list_returns_none(self):
        assert _worst_status([]) is None

    def test_unknown_status_treated_as_lowest_severity(self):
        # Unknown statuses get severity 99, so a known status wins
        assert _worst_status(["unknown", "not_feasible"]) == "not_feasible"


class TestRegionWorstStatusMap:
    def test_rollup_picks_worst_per_region(self):
        df = pd.DataFrame(
            [
                {"from_region": "SULAWESI", "to_region": "SULAWESI", "status": "in_construction"},
                {"from_region": "SULAWESI", "to_region": "SULAWESI", "status": "not_feasible"},
                {"from_region": "JAVA_BALI", "to_region": "SUMATERA", "status": "under_study"},
            ]
        )
        m = region_worst_status_map(df)
        assert m["SULAWESI"] == "not_feasible"
        # Both endpoints of an inter-region link get the status applied
        assert m["JAVA_BALI"] == "under_study"
        assert m["SUMATERA"] == "under_study"

    def test_cross_border_endpoint_excluded(self):
        df = pd.DataFrame(
            [{"from_region": "PAPUA", "to_region": "CROSS_BORDER", "status": "cross_border"}]
        )
        m = region_worst_status_map(df)
        assert m["PAPUA"] == "cross_border"
        assert "CROSS_BORDER" not in m  # no rollup entry for the synthetic endpoint

    def test_empty_dataframe_returns_empty_map(self):
        assert region_worst_status_map(pd.DataFrame()) == {}


class TestComparatorFeasibilityForRegion:
    def test_grid_ready_site_always_feasible(self):
        # Sites that don't need new transmission stay feasible regardless
        assert (
            comparator_feasibility_for_region(
                "SULAWESI",
                {"SULAWESI": "not_feasible"},
                grid_integration_category="grid_ready",
            )
            == "pln_tariff_feasible"
        )

    def test_invest_transmission_in_infeasible_region(self):
        assert (
            comparator_feasibility_for_region(
                "SULAWESI",
                {"SULAWESI": "not_feasible"},
                grid_integration_category="invest_transmission",
            )
            == "pln_tariff_infeasible_captive_only"
        )

    def test_invest_substation_in_under_study_region(self):
        assert (
            comparator_feasibility_for_region(
                "MALUKU",
                {"MALUKU": "under_study"},
                grid_integration_category="invest_substation",
            )
            == "pln_tariff_uncertain_grid_first_required"
        )

    def test_grid_first_with_cross_border_link(self):
        assert (
            comparator_feasibility_for_region(
                "PAPUA",
                {"PAPUA": "cross_border"},
                grid_integration_category="grid_first",
            )
            == "pln_tariff_uncertain_grid_first_required"
        )

    def test_region_not_in_map_defaults_feasible(self):
        # Regions with no flagged links → feasible (the default outcome)
        assert (
            comparator_feasibility_for_region(
                "JAVA_BALI",
                {},
                grid_integration_category="invest_transmission",
            )
            == "pln_tariff_feasible"
        )

    def test_in_construction_status_is_feasible(self):
        assert (
            comparator_feasibility_for_region(
                "JAVA_BALI",
                {"JAVA_BALI": "in_construction"},
                grid_integration_category="invest_transmission",
            )
            == "pln_tariff_feasible"
        )
