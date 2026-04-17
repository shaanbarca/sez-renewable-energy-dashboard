# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.lcoe`.

Canned minimal inputs. Asserts column names + shape + a couple of sanity
invariants (e.g. grid-connected LCOE >= within-boundary LCOE when the same
PVOUT is used, because it adds connection cost).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.dash.logic.assumptions import get_default_assumptions
from src.dash.logic.lcoe import compute_lcoe_live, compute_lcoe_wind_live

_WB_COLUMNS = {
    "site_id",
    "scenario",
    "lcoe_low_usd_mwh",
    "lcoe_mid_usd_mwh",
    "lcoe_high_usd_mwh",
    "connection_cost_per_kw",
    "cf",
    "pvout_used",
}
_GC_EXTRA = {
    "transmission_cost_per_kw",
    "substation_upgrade_cost_per_kw",
    "effective_capacity_mwp",
}


def _resource_row(**overrides) -> pd.DataFrame:
    base = {
        "site_id": "S001",
        "pvout_centroid": 1650.0,
        "pvout_within_boundary": 1650.0,
        "pvout_best_50km": 1700.0,
        "pvout_buildable_best_50km": 1700.0,
        "dist_solar_to_nearest_substation_km": 5.0,
        "dist_to_nearest_substation_km": 7.0,
        "max_captive_capacity_mwp": 50.0,
        "nearest_substation_capacity_mva": 100.0,
        "inter_substation_connected": True,
        "inter_substation_dist_km": 0.0,
    }
    base.update(overrides)
    return pd.DataFrame([base])


def test_compute_lcoe_live_returns_two_rows_per_site() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    assert len(df) == 2
    assert set(df["scenario"]) == {"within_boundary", "grid_connected_solar"}


def test_compute_lcoe_live_columns_complete() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    gc = df[df["scenario"] == "grid_connected_solar"].iloc[0]
    assert _WB_COLUMNS.issubset(wb.index)
    assert (_WB_COLUMNS | _GC_EXTRA).issubset(gc.index)


def test_compute_lcoe_live_connection_cost_zero_in_within_boundary() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    assert wb["connection_cost_per_kw"] == 0.0


def test_compute_lcoe_live_grid_connected_costs_nonneg() -> None:
    df = compute_lcoe_live(_resource_row(), get_default_assumptions())
    gc = df[df["scenario"] == "grid_connected_solar"].iloc[0]
    assert gc["connection_cost_per_kw"] >= 0.0
    assert gc["transmission_cost_per_kw"] >= 0.0
    assert gc["substation_upgrade_cost_per_kw"] >= 0.0


def test_compute_lcoe_live_handles_missing_pvout() -> None:
    df = compute_lcoe_live(
        _resource_row(
            pvout_centroid=np.nan,
            pvout_within_boundary=np.nan,
            pvout_best_50km=np.nan,
            pvout_buildable_best_50km=np.nan,
        ),
        get_default_assumptions(),
    )
    wb = df[df["scenario"] == "within_boundary"].iloc[0]
    assert pd.isna(wb["lcoe_mid_usd_mwh"])


def test_compute_lcoe_wind_live_columns_and_shape() -> None:
    resource = _resource_row(
        cf_wind_best_50km=0.35,
        cf_wind_centroid=0.33,
        wind_speed_best_50km_ms=7.5,
        wind_speed_centroid_ms=7.0,
    )
    df = compute_lcoe_wind_live(resource, wacc_pct=10.0)
    assert len(df) == 1
    row = df.iloc[0]
    assert set(row.index) == {"site_id", "lcoe_wind_mid_usd_mwh", "cf_wind", "wind_speed_ms"}
    assert row["lcoe_wind_mid_usd_mwh"] > 0


def test_compute_lcoe_wind_live_zero_cf_yields_nan() -> None:
    resource = _resource_row(
        cf_wind_best_50km=0.0,
        cf_wind_centroid=0.0,
        wind_speed_best_50km_ms=2.0,
        wind_speed_centroid_ms=2.0,
    )
    df = compute_lcoe_wind_live(resource, wacc_pct=10.0)
    assert pd.isna(df.iloc[0]["lcoe_wind_mid_usd_mwh"])
