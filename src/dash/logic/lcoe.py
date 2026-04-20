# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Live LCOE computation for solar and wind technologies.

Pure functions that take `UserAssumptions` + resource DataFrame and return
per-site LCOE rows. No scorecard orchestration, no action flags, no CBAM.
All formulas delegate to `src.model.basic_model` (no math duplication here).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import SUBSTATION_UTILIZATION_PCT, TRANSMISSION_FALLBACK_CAPACITY_MWP
from src.dash.logic.assumptions import UserAssumptions
from src.model.basic_model import (
    capacity_factor_from_pvout,
    grid_connection_cost_per_kw,
    lcoe_solar,
    new_transmission_cost_per_kw,
    substation_upgrade_cost_per_kw,
)


def _round(value: float, decimals: int = 2) -> float:
    """Round a value, returning NaN unchanged."""
    if pd.isna(value):
        return np.nan
    return round(float(value), decimals)


def live_effective_mwp(
    demand_mwh: float | None,
    cf: float | None,
    max_buildable_mwp: float | None,
    meaningful_share_pct: float,
    target_capacity_mwp: float | None = None,
) -> float:
    """Phase-1 sized project capacity the substation sees.

    Priority: explicit ``target_capacity_mwp`` override wins. Otherwise derive
    phase-1 from demand coverage: `meaningful_share_pct` of the capacity
    required to meet annual site demand. Always capped by the buildable upper
    bound. Falls back to full buildable when demand/cf are unknown.
    """
    max_mwp = float(max_buildable_mwp) if max_buildable_mwp and max_buildable_mwp > 0 else 0.0
    if target_capacity_mwp:
        return min(float(target_capacity_mwp), max_mwp) if max_mwp else float(target_capacity_mwp)
    if not demand_mwh or not cf or cf <= 0:
        return max_mwp
    required_mwp = float(demand_mwh) / (8760.0 * float(cf))
    phase1_mwp = required_mwp * float(meaningful_share_pct)
    return min(phase1_mwp, max_mwp) if max_mwp else phase1_mwp


def compute_lcoe_live(
    resource_df: pd.DataFrame,
    assumptions: UserAssumptions,
    demand_by_site: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compute LCOE for all KEKs at user-specified assumptions.

    V2: Produces 2 rows per KEK (within_boundary + grid_connected_solar).
    Grid-connected uses dist_solar_to_nearest_substation_km (solar→substation)
    instead of dist_to_nearest_substation_km (KEK→substation).

    Parameters
    ----------
    resource_df:
        Must have columns: site_id, pvout_centroid, pvout_best_50km (or
        pvout_buildable_best_50km). Optional: dist_solar_to_nearest_substation_km,
        dist_to_nearest_substation_km (fallback).
    assumptions:
        User-adjustable model assumptions from dashboard sliders.

    Returns
    -------
    pd.DataFrame
        Columns: site_id, scenario, lcoe_low/mid/high_usd_mwh,
        connection_cost_per_kw, cf, pvout_used.
    """
    wacc = assumptions.wacc_decimal
    lifetime = assumptions.lifetime_yr
    capex_c = assumptions.capex_usd_per_kw
    capex_l = assumptions.capex_low
    capex_h = assumptions.capex_high
    fom = assumptions.fom_usd_per_kw_yr

    gc_pvout_col = (
        "pvout_buildable_best_50km"
        if "pvout_buildable_best_50km" in resource_df.columns
        and resource_df["pvout_buildable_best_50km"].notna().any()
        else "pvout_best_50km"
    )

    rows = []
    for _, kek in resource_df.iterrows():
        site_id = kek["site_id"]
        demand_mwh = (demand_by_site or {}).get(site_id, 0.0)

        dist_solar = kek.get("dist_solar_to_nearest_substation_km")
        dist_kek = kek.get("dist_to_nearest_substation_km", 0.0)
        if pd.isna(dist_solar):
            dist_solar = None
        if pd.isna(dist_kek):
            dist_kek = 0.0
        dist_km = dist_solar if dist_solar is not None else dist_kek

        pvout_wb = kek.get("pvout_within_boundary")
        if pd.isna(pvout_wb) or pvout_wb is None or pvout_wb <= 0:
            pvout_wb = kek.get("pvout_centroid")
        if pd.notna(pvout_wb) and pvout_wb > 0:
            cf_wb = capacity_factor_from_pvout(pvout_wb)
            lcoe_c_wb = lcoe_solar(capex_c, fom, wacc, lifetime, cf_wb)
            lcoe_l_wb = lcoe_solar(capex_l, fom, wacc, lifetime, cf_wb)
            lcoe_h_wb = lcoe_solar(capex_h, fom, wacc, lifetime, cf_wb)
        else:
            cf_wb = lcoe_c_wb = lcoe_l_wb = lcoe_h_wb = np.nan

        rows.append(
            {
                "site_id": site_id,
                "scenario": "within_boundary",
                "lcoe_low_usd_mwh": _round(lcoe_l_wb),
                "lcoe_mid_usd_mwh": _round(lcoe_c_wb),
                "lcoe_high_usd_mwh": _round(lcoe_h_wb),
                "connection_cost_per_kw": 0.0,
                "cf": _round(cf_wb, 4),
                "pvout_used": pvout_wb,
            }
        )

        pvout_gc = kek.get(gc_pvout_col)
        if pd.isna(pvout_gc) or pvout_gc <= 0:
            pvout_gc = kek.get("pvout_best_50km")
        if pd.isna(pvout_gc) or pvout_gc <= 0:
            pvout_gc = pvout_wb

        if pd.notna(pvout_gc) and pvout_gc > 0:
            cf_gc = capacity_factor_from_pvout(pvout_gc)
            if assumptions.grant_funded_transmission:
                conn_cost = 0.0
            else:
                conn_cost = grid_connection_cost_per_kw(
                    dist_km,
                    assumptions.connection_cost_per_kw_km,
                    assumptions.grid_connection_fixed_per_kw,
                )
            land_cost = assumptions.land_cost_usd_per_kw

            anchor_mwp_val = kek.get("project_scale_solar_mwp")
            envelope_mwp_val = kek.get("max_captive_capacity_mwp")
            if pd.notna(anchor_mwp_val) and float(anchor_mwp_val) > 0:
                max_mwp = float(anchor_mwp_val)
            elif pd.notna(envelope_mwp_val) and float(envelope_mwp_val) > 0:
                max_mwp = float(envelope_mwp_val)
            else:
                max_mwp = TRANSMISSION_FALLBACK_CAPACITY_MWP
            effective_mwp = live_effective_mwp(
                demand_mwh=demand_mwh,
                cf=cf_gc,
                max_buildable_mwp=max_mwp,
                meaningful_share_pct=assumptions.meaningful_share_pct,
                target_capacity_mwp=assumptions.target_capacity_mwp,
            )

            inter_connected = kek.get("inter_substation_connected")
            inter_sub_dist = kek.get("inter_substation_dist_km", 0.0)
            if pd.isna(inter_connected):
                inter_connected = None
            if pd.isna(inter_sub_dist):
                inter_sub_dist = 0.0
            if assumptions.grant_funded_transmission:
                trans_cost = 0.0
            elif inter_connected is False and inter_sub_dist > 0:
                trans_cost = new_transmission_cost_per_kw(inter_sub_dist, effective_mwp)
            else:
                trans_cost = 0.0

            sub_cap = kek.get("nearest_substation_capacity_mva")
            sub_cap = float(sub_cap) if pd.notna(sub_cap) else None
            if assumptions.grant_funded_transmission:
                upgrade_cost = 0.0
            else:
                # V3.8: same priority rule as grid.py — slider wins when dragged
                # off the fleet default, else RUPTL-derived per-site value wins.
                if assumptions.substation_utilization_pct != SUBSTATION_UTILIZATION_PCT:
                    upgrade_util = assumptions.substation_utilization_pct
                else:
                    effective_util = kek.get("substation_utilization_pct_effective")
                    upgrade_util = (
                        float(effective_util)
                        if pd.notna(effective_util)
                        else assumptions.substation_utilization_pct
                    )
                upgrade_cost = substation_upgrade_cost_per_kw(sub_cap, effective_mwp, upgrade_util)

            eff_c = capex_c + conn_cost + land_cost + trans_cost + upgrade_cost
            eff_l = capex_l + conn_cost + land_cost + trans_cost + upgrade_cost
            eff_h = capex_h + conn_cost + land_cost + trans_cost + upgrade_cost
            lcoe_c_gc = lcoe_solar(eff_c, fom, wacc, lifetime, cf_gc)
            lcoe_l_gc = lcoe_solar(eff_l, fom, wacc, lifetime, cf_gc)
            lcoe_h_gc = lcoe_solar(eff_h, fom, wacc, lifetime, cf_gc)
        else:
            cf_gc = lcoe_c_gc = lcoe_l_gc = lcoe_h_gc = np.nan
            conn_cost = 0.0
            trans_cost = 0.0
            upgrade_cost = 0.0
            effective_mwp = 0.0

        rows.append(
            {
                "site_id": site_id,
                "scenario": "grid_connected_solar",
                "lcoe_low_usd_mwh": _round(lcoe_l_gc),
                "lcoe_mid_usd_mwh": _round(lcoe_c_gc),
                "lcoe_high_usd_mwh": _round(lcoe_h_gc),
                "connection_cost_per_kw": _round(conn_cost, 1),
                "transmission_cost_per_kw": _round(trans_cost, 1),
                "substation_upgrade_cost_per_kw": _round(upgrade_cost, 1),
                "effective_capacity_mwp": _round(effective_mwp, 1),
                "cf": _round(cf_gc, 4),
                "pvout_used": pvout_gc,
            }
        )

    return pd.DataFrame(rows)


def compute_lcoe_wind_live(
    resource_df: pd.DataFrame,
    wacc_pct: float,
    wind_capex: float = 1650.0,
    wind_fom: float = 40.0,
    wind_lifetime: int = 27,
) -> pd.DataFrame:
    """Compute wind LCOE for all KEKs at user-specified WACC.

    Uses precomputed CF from fct_site_wind_resource and the same CRF annuity
    formula as solar (lcoe_solar is technology-agnostic).

    Parameters
    ----------
    resource_df:
        Must have wind columns from fct_site_wind_resource merge:
        cf_wind_best_50km, cf_wind_centroid, wind_speed_best_50km_ms,
        wind_speed_centroid_ms.
    wacc_pct:
        WACC percentage (e.g. 10.0 for 10%).
    wind_capex, wind_fom, wind_lifetime:
        Wind technology cost parameters from dim_tech_cost_wind.

    Returns
    -------
    pd.DataFrame
        One row per KEK: site_id, lcoe_wind_mid_usd_mwh, cf_wind, wind_speed_ms.
    """
    wacc = wacc_pct / 100.0
    rows = []

    for _, kek in resource_df.iterrows():
        site_id = kek["site_id"]

        cf_best = kek.get("cf_wind_best_50km")
        cf_centroid = kek.get("cf_wind_centroid")
        ws_best = kek.get("wind_speed_best_50km_ms")
        ws_centroid = kek.get("wind_speed_centroid_ms")

        cf = (
            float(cf_best)
            if pd.notna(cf_best) and cf_best > 0
            else (float(cf_centroid) if pd.notna(cf_centroid) and cf_centroid > 0 else 0.0)
        )
        ws = (
            float(ws_best)
            if pd.notna(ws_best)
            else (float(ws_centroid) if pd.notna(ws_centroid) else 0.0)
        )

        if cf > 0:
            lcoe_wind = lcoe_solar(
                wind_capex,
                wind_fom,
                wacc,
                wind_lifetime,
                cf,
                degradation_annual_pct=0.0,
            )
        else:
            lcoe_wind = np.nan

        rows.append(
            {
                "site_id": site_id,
                "lcoe_wind_mid_usd_mwh": _round(lcoe_wind),
                "cf_wind": _round(cf, 4),
                "wind_speed_ms": _round(ws, 2),
            }
        )

    return pd.DataFrame(rows)
