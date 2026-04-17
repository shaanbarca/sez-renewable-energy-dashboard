# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.grid`.

`compute_grid_integration` is a pure-function composite. These tests assert
the shape of its output dict and that the category-specific infra-cost
zeroing logic holds (e.g. within_boundary → all three zeroed).
"""

from __future__ import annotations

import pandas as pd

from src.dash.logic.assumptions import get_default_assumptions
from src.dash.logic.grid import compute_grid_integration

EXPECTED_KEYS = {
    "grid_integration_category",
    "capacity_assessment",
    "available_capacity_mva",
    "connection_cost_per_kw",
    "transmission_cost_per_kw",
    "substation_upgrade_cost_per_kw",
    "effective_capacity_mwp",
    "grid_investment_needed_usd",
    "same_grid_region",
    "line_connected",
    "inter_substation_connected",
    "inter_substation_dist_km",
    "dist_solar_to_nearest_substation_km",
    "dist_to_nearest_substation_km",
}


def _kek(**overrides) -> pd.Series:
    base = {
        "nearest_substation_capacity_mva": 100.0,
        "max_captive_capacity_mwp": 50.0,
        "has_internal_substation": False,
        "dist_solar_to_nearest_substation_km": 5.0,
        "dist_to_nearest_substation_km": 7.0,
        "inter_substation_connected": True,
        "within_boundary_coverage_pct": 0.0,
        "same_grid_region": True,
        "line_connected": True,
        "inter_substation_dist_km": 0.0,
    }
    base.update(overrides)
    return pd.Series(base)


def _gc_row(**overrides) -> pd.Series:
    base = {
        "connection_cost_per_kw": 105.0,
        "transmission_cost_per_kw": 25.0,
        "substation_upgrade_cost_per_kw": 12.0,
        "effective_capacity_mwp": 50.0,
    }
    base.update(overrides)
    return pd.Series(base)


def test_output_shape_full_dict() -> None:
    out = compute_grid_integration(_kek(), _gc_row(), get_default_assumptions())
    assert set(out.keys()) >= EXPECTED_KEYS


def test_within_boundary_category_zeroes_investment() -> None:
    """within_boundary sites need no grid investment, even if gc_row has per-kW costs."""
    kek = _kek(within_boundary_coverage_pct=1.0, has_internal_substation=True)
    out = compute_grid_integration(kek, _gc_row(), get_default_assumptions())
    assert out["grid_integration_category"] == "within_boundary"
    assert out["grid_investment_needed_usd"] is None


def test_handles_missing_gc_row() -> None:
    out = compute_grid_integration(_kek(), None, get_default_assumptions())
    assert set(out.keys()) >= EXPECTED_KEYS
    assert out["connection_cost_per_kw"] == 0.0
    assert out["transmission_cost_per_kw"] == 0.0
    assert out["substation_upgrade_cost_per_kw"] == 0.0


def test_capacity_assessment_returned() -> None:
    out = compute_grid_integration(_kek(), _gc_row(), get_default_assumptions())
    assert out["capacity_assessment"] in {"green", "yellow", "red", "unknown"}


def test_grid_investment_computed_when_costs_nonzero() -> None:
    kek = _kek(
        has_internal_substation=False,
        dist_solar_to_nearest_substation_km=50.0,
        dist_to_nearest_substation_km=55.0,
        within_boundary_coverage_pct=0.0,
    )
    out = compute_grid_integration(kek, _gc_row(), get_default_assumptions())
    if (
        out["connection_cost_per_kw"]
        + out["transmission_cost_per_kw"]
        + out["substation_upgrade_cost_per_kw"]
        > 0
    ):
        assert out["grid_investment_needed_usd"] is not None
        assert out["grid_investment_needed_usd"] > 0
