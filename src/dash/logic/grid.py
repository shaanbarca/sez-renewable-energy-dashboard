# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Grid integration: capacity assessment, category classification, infra cost.

Single public helper `compute_grid_integration` takes the site row + the
grid-connected LCOE row (for pre-computed transmission/upgrade/connection
per-kW costs) + user assumptions, and returns a dict to merge into the
scorecard row. Includes pass-through connectivity columns and the
category-conditioned infra cost rollup.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.dash.logic.assumptions import UserAssumptions
from src.model.basic_model import capacity_assessment as compute_capacity_assessment
from src.model.basic_model import grid_integration_category as compute_grid_integration_category


def _get_float(src: Any, key: str, default: float | None = None) -> float | None:
    val = src.get(key) if src is not None else None
    if val is None or pd.isna(val):
        return default
    return float(val)


def compute_grid_integration(
    kek: pd.Series,
    gc_row: pd.Series | None,
    assumptions: UserAssumptions,
) -> dict:
    """Grid category + capacity + infra cost + connectivity pass-throughs.

    Parameters
    ----------
    kek:
        Single row from `resource_df` — source of distances, substation
        capacity, connectivity flags, buildable capacity.
    gc_row:
        Single row from the grid-connected LCOE result (or None when the
        site has no grid-connected scenario). Supplies `connection_cost_per_kw`,
        `transmission_cost_per_kw`, `substation_upgrade_cost_per_kw`,
        `effective_capacity_mwp`.
    assumptions:
        Supplies `substation_utilization_pct` and `target_capacity_mwp` (H10).

    Returns
    -------
    dict with keys:
        grid_integration_category, capacity_assessment, available_capacity_mva,
        connection_cost_per_kw, transmission_cost_per_kw,
        substation_upgrade_cost_per_kw, effective_capacity_mwp,
        grid_investment_needed_usd, same_grid_region, line_connected,
        inter_substation_connected, inter_substation_dist_km,
        dist_solar_to_nearest_substation_km, dist_to_nearest_substation_km.
    """
    sub_cap_mva = _get_float(kek, "nearest_substation_capacity_mva")
    solar_cap_mwp = _get_float(kek, "max_captive_capacity_mwp")

    # H10: cap buildable capacity with user target
    effective_cap = solar_cap_mwp
    if assumptions.target_capacity_mwp and solar_cap_mwp:
        effective_cap = min(assumptions.target_capacity_mwp, solar_cap_mwp)

    cap_light, avail_mva = compute_capacity_assessment(
        sub_cap_mva, effective_cap, assumptions.substation_utilization_pct
    )

    has_internal = kek.get("has_internal_substation", False)
    has_internal = bool(has_internal) if pd.notna(has_internal) else False
    dist_solar = _get_float(kek, "dist_solar_to_nearest_substation_km")
    dist_kek = _get_float(kek, "dist_to_nearest_substation_km", 0.0)
    inter_raw = kek.get("inter_substation_connected")
    inter_connected = bool(inter_raw) if pd.notna(inter_raw) else None
    wb_coverage = _get_float(kek, "within_boundary_coverage_pct")

    gi_cat = compute_grid_integration_category(
        has_internal_substation=has_internal,
        dist_solar_to_substation_km=dist_solar,
        dist_kek_to_substation_km=dist_kek,
        substation_capacity_mva=sub_cap_mva,
        substation_utilization_pct=assumptions.substation_utilization_pct,
        solar_capacity_mwp=effective_cap,
        inter_substation_connected=inter_connected,
        within_boundary_coverage_pct=wb_coverage,
    )

    if gc_row is not None:
        conn_cost = float(gc_row.get("connection_cost_per_kw", 0.0) or 0.0)
        trans_cost = float(gc_row.get("transmission_cost_per_kw", 0.0) or 0.0)
        upgrade_cost = float(gc_row.get("substation_upgrade_cost_per_kw", 0.0) or 0.0)
        eff_mwp_out = gc_row.get("effective_capacity_mwp")
        eff_mwp_out = float(eff_mwp_out) if pd.notna(eff_mwp_out) else None
    else:
        conn_cost = 0.0
        trans_cost = 0.0
        upgrade_cost = 0.0
        eff_mwp_out = None

    # Category-specific cost zeroing: only include components that actually
    # apply to this site's infrastructure situation.
    if gi_cat == "within_boundary":
        gc_conn, gc_trans, gc_upgrade = 0.0, 0.0, 0.0
    elif gi_cat == "grid_ready":
        gc_conn, gc_trans, gc_upgrade = conn_cost, 0.0, 0.0
    elif gi_cat == "invest_transmission":
        gc_conn, gc_trans, gc_upgrade = conn_cost, trans_cost, 0.0
    elif gi_cat == "invest_substation":
        gc_conn, gc_trans, gc_upgrade = conn_cost, 0.0, upgrade_cost
    else:  # grid_first — all three apply
        gc_conn, gc_trans, gc_upgrade = conn_cost, trans_cost, upgrade_cost

    infra_cost = gc_conn + gc_trans + gc_upgrade
    eff_mwp_for_invest = eff_mwp_out if eff_mwp_out is not None else (solar_cap_mwp or 0.0)
    if infra_cost > 0 and eff_mwp_for_invest and eff_mwp_for_invest > 0:
        grid_investment_needed_usd: int | None = round(infra_cost * eff_mwp_for_invest * 1000)
    else:
        grid_investment_needed_usd = None

    return {
        "grid_integration_category": gi_cat,
        "capacity_assessment": cap_light,
        "available_capacity_mva": avail_mva,
        "connection_cost_per_kw": conn_cost,
        "transmission_cost_per_kw": trans_cost,
        "substation_upgrade_cost_per_kw": upgrade_cost,
        "effective_capacity_mwp": eff_mwp_out,
        "grid_investment_needed_usd": grid_investment_needed_usd,
        "same_grid_region": kek.get("same_grid_region", None),
        "line_connected": kek.get("line_connected", None),
        "inter_substation_connected": kek.get("inter_substation_connected", None),
        "inter_substation_dist_km": kek.get("inter_substation_dist_km", None),
        "dist_solar_to_nearest_substation_km": kek.get("dist_solar_to_nearest_substation_km", None),
        "dist_to_nearest_substation_km": kek.get("dist_to_nearest_substation_km", None),
    }
