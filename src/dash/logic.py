# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
Dashboard computation logic — pure functions, no Dash dependency.

This module replaces the precomputed fct_lcoe lookup with live LCOE computation
driven by user-adjustable assumptions. All functions are testable with pytest.

Architecture:
  - Pipeline still precomputes fct_lcoe.csv at default assumptions (for export/reproducibility)
  - Dashboard calls these functions with user-supplied slider values
  - All functions delegate to src/model/basic_model.py (no formula duplication)
  - ~5ms for 25 KEKs x 2 scenarios on any modern machine

See DESIGN.md §3 (callback architecture) and §5 (precomputed vs live).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.assumptions import (
    BASE_WACC,
    BESS_CAPEX_USD_PER_KWH,
    CONNECTION_COST_PER_KW_KM,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    GRID_CONNECTION_FIXED_PER_KW,
    IDR_USD_RATE,
    LAND_COST_USD_PER_KW,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PROJECT_VIABLE_MIN_MWP,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
)
from src.model.basic_model import (
    ActionFlag,
    action_flags,
    bess_storage_adder,
    capacity_factor_from_pvout,
    carbon_breakeven_price,
    grid_connection_cost_per_kw,
    is_solar_attractive,
    lcoe_solar,
    solar_competitive_gap,
)
from src.model.basic_model import (
    invest_resilience as invest_resilience_fn,
)
from src.pipeline.assumptions import (
    TARIFF_I4_RP_KWH,
    rp_kwh_to_usd_mwh,
)

# ---------------------------------------------------------------------------
# Dataclasses for user-adjustable assumptions (serialisable to/from dcc.Store)
# ---------------------------------------------------------------------------


@dataclass
class UserAssumptions:
    """Model assumptions adjustable via dashboard sliders (Tier 1 + Tier 2)."""

    # Tier 1: Primary controls
    capex_usd_per_kw: float = TECH006_CAPEX_USD_PER_KW
    lifetime_yr: int = TECH006_LIFETIME_YR
    wacc_pct: float = BASE_WACC  # percent, e.g. 10.0

    # Tier 2: Advanced panel
    fom_usd_per_kw_yr: float = TECH006_FOM_USD_PER_KW_YR
    connection_cost_per_kw_km: float = CONNECTION_COST_PER_KW_KM
    grid_connection_fixed_per_kw: float = GRID_CONNECTION_FIXED_PER_KW
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH
    land_cost_usd_per_kw: float = LAND_COST_USD_PER_KW
    idr_usd_rate: float = IDR_USD_RATE
    grid_benchmark_usd_mwh: float = 63.08

    @property
    def wacc_decimal(self) -> float:
        return self.wacc_pct / 100.0

    @property
    def capex_low(self) -> float:
        """Lower bound: -12.5% of central CAPEX (matches ESDM band)."""
        return self.capex_usd_per_kw * 0.875

    @property
    def capex_high(self) -> float:
        """Upper bound: +12.5% of central CAPEX (matches ESDM band)."""
        return self.capex_usd_per_kw * 1.125

    def to_dict(self) -> dict:
        """Serialise for dcc.Store."""
        return {
            "capex_usd_per_kw": self.capex_usd_per_kw,
            "lifetime_yr": self.lifetime_yr,
            "wacc_pct": self.wacc_pct,
            "fom_usd_per_kw_yr": self.fom_usd_per_kw_yr,
            "connection_cost_per_kw_km": self.connection_cost_per_kw_km,
            "grid_connection_fixed_per_kw": self.grid_connection_fixed_per_kw,
            "bess_capex_usd_per_kwh": self.bess_capex_usd_per_kwh,
            "land_cost_usd_per_kw": self.land_cost_usd_per_kw,
            "idr_usd_rate": self.idr_usd_rate,
            "grid_benchmark_usd_mwh": self.grid_benchmark_usd_mwh,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserAssumptions":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class UserThresholds:
    """Action flag thresholds adjustable via dashboard sliders (Tier 3)."""

    pvout_threshold: float = 1550.0
    plan_late_threshold: float = PLAN_LATE_POST2030_SHARE_THRESHOLD
    geas_threshold: float = GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD
    resilience_gap_pct: float = RESILIENCE_LCOE_GAP_THRESHOLD_PCT
    min_viable_mwp: float = PROJECT_VIABLE_MIN_MWP
    reliability_threshold: float = FIRMING_RELIABILITY_REQ_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "pvout_threshold": self.pvout_threshold,
            "plan_late_threshold": self.plan_late_threshold,
            "geas_threshold": self.geas_threshold,
            "resilience_gap_pct": self.resilience_gap_pct,
            "min_viable_mwp": self.min_viable_mwp,
            "reliability_threshold": self.reliability_threshold,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserThresholds":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Live LCOE computation
# ---------------------------------------------------------------------------


def compute_lcoe_live(
    resource_df: pd.DataFrame,
    assumptions: UserAssumptions,
) -> pd.DataFrame:
    """Compute LCOE for all KEKs at user-specified assumptions.

    V2: Produces 2 rows per KEK (within_boundary + grid_connected_solar).
    Grid-connected uses dist_solar_to_nearest_substation_km (solar→substation)
    instead of dist_to_nearest_substation_km (KEK→substation).

    Parameters
    ----------
    resource_df:
        Must have columns: kek_id, pvout_centroid, pvout_best_50km (or
        pvout_buildable_best_50km). Optional: dist_solar_to_nearest_substation_km,
        dist_to_nearest_substation_km (fallback).
    assumptions:
        User-adjustable model assumptions from dashboard sliders.

    Returns
    -------
    pd.DataFrame
        Columns: kek_id, scenario, lcoe_low/mid/high_usd_mwh,
        connection_cost_per_kw, cf, pvout_used.
    """
    wacc = assumptions.wacc_decimal
    lifetime = assumptions.lifetime_yr
    capex_c = assumptions.capex_usd_per_kw
    capex_l = assumptions.capex_low
    capex_h = assumptions.capex_high
    fom = assumptions.fom_usd_per_kw_yr

    # Choose the best available remote PVOUT column
    gc_pvout_col = (
        "pvout_buildable_best_50km"
        if "pvout_buildable_best_50km" in resource_df.columns
        and resource_df["pvout_buildable_best_50km"].notna().any()
        else "pvout_best_50km"
    )

    rows = []
    for _, kek in resource_df.iterrows():
        kek_id = kek["kek_id"]

        # V2: prefer solar-to-substation distance; fallback to KEK-to-substation
        dist_solar = kek.get("dist_solar_to_nearest_substation_km")
        dist_kek = kek.get("dist_to_nearest_substation_km", 0.0)
        if pd.isna(dist_solar):
            dist_solar = None
        if pd.isna(dist_kek):
            dist_kek = 0.0
        dist_km = dist_solar if dist_solar is not None else dist_kek

        # Within-boundary scenario: use centroid PVOUT, no connection cost
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
                "kek_id": kek_id,
                "scenario": "within_boundary",
                "lcoe_low_usd_mwh": _round(lcoe_l_wb),
                "lcoe_mid_usd_mwh": _round(lcoe_c_wb),
                "lcoe_high_usd_mwh": _round(lcoe_h_wb),
                "connection_cost_per_kw": 0.0,
                "cf": _round(cf_wb, 4),
                "pvout_used": pvout_wb,
            }
        )

        # Grid-connected solar: use best PVOUT + connection cost (solar→substation)
        pvout_gc = kek.get(gc_pvout_col)
        if pd.isna(pvout_gc) or pvout_gc <= 0:
            pvout_gc = kek.get("pvout_best_50km")
        if pd.isna(pvout_gc) or pvout_gc <= 0:
            pvout_gc = pvout_wb  # fallback to centroid

        if pd.notna(pvout_gc) and pvout_gc > 0:
            cf_gc = capacity_factor_from_pvout(pvout_gc)
            conn_cost = grid_connection_cost_per_kw(
                dist_km,
                assumptions.connection_cost_per_kw_km,
                assumptions.grid_connection_fixed_per_kw,
            )
            land_cost = assumptions.land_cost_usd_per_kw
            eff_c = capex_c + conn_cost + land_cost
            eff_l = capex_l + conn_cost + land_cost
            eff_h = capex_h + conn_cost + land_cost
            lcoe_c_gc = lcoe_solar(eff_c, fom, wacc, lifetime, cf_gc)
            lcoe_l_gc = lcoe_solar(eff_l, fom, wacc, lifetime, cf_gc)
            lcoe_h_gc = lcoe_solar(eff_h, fom, wacc, lifetime, cf_gc)
        else:
            cf_gc = lcoe_c_gc = lcoe_l_gc = lcoe_h_gc = np.nan
            conn_cost = 0.0

        rows.append(
            {
                "kek_id": kek_id,
                "scenario": "grid_connected_solar",
                "lcoe_low_usd_mwh": _round(lcoe_l_gc),
                "lcoe_mid_usd_mwh": _round(lcoe_c_gc),
                "lcoe_high_usd_mwh": _round(lcoe_h_gc),
                "connection_cost_per_kw": _round(conn_cost, 1),
                "cf": _round(cf_gc, 4),
                "pvout_used": pvout_gc,
            }
        )

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Live scorecard computation (flags, gap, carbon breakeven)
# ---------------------------------------------------------------------------


def compute_scorecard_live(
    resource_df: pd.DataFrame,
    assumptions: UserAssumptions,
    thresholds: UserThresholds,
    ruptl_metrics_df: pd.DataFrame,
    demand_df: pd.DataFrame,
    grid_df: pd.DataFrame,
    grid_cost_by_region: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Full live scorecard: LCOE + competitive gap + action flags + carbon breakeven.

    This is the main entry point called by the dashboard callback whenever any
    assumption slider changes. Returns one row per KEK.

    Parameters
    ----------
    resource_df:
        fct_kek_resource with PVOUT columns + dist_to_nearest_substation_km.
    assumptions:
        User-adjustable model assumptions.
    thresholds:
        User-adjustable flag thresholds.
    ruptl_metrics_df:
        Pre-aggregated RUPTL metrics per grid_region_id (from ruptl_region_metrics()).
        Columns: grid_region_id, post2030_share, grid_upgrade_pre2030.
    demand_df:
        fct_kek_demand filtered to target year. Columns: kek_id, demand_mwh.
    grid_df:
        fct_grid_cost_proxy. Columns: grid_region_id, grid_emission_factor_t_co2_mwh.
    """
    lcoe_df = compute_lcoe_live(resource_df, assumptions)

    # Extract within_boundary rows for primary comparison
    wb = lcoe_df[lcoe_df["scenario"] == "within_boundary"].set_index("kek_id")
    gc = lcoe_df[lcoe_df["scenario"] == "grid_connected_solar"].set_index("kek_id")

    default_grid_cost = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH, assumptions.idr_usd_rate)

    # Index demand by kek_id for fast lookup
    demand_by_kek: dict[str, float] = {}
    if demand_df is not None and not demand_df.empty:
        for _, d_row in demand_df.iterrows():
            demand_by_kek[d_row["kek_id"]] = float(d_row["demand_mwh"])

    rows = []
    for _, kek in resource_df.iterrows():
        kek_id = kek["kek_id"]
        grid_region_id = kek.get("grid_region_id")

        # Per-region grid cost (BPP mode) or uniform tariff
        if grid_cost_by_region and grid_region_id and grid_region_id in grid_cost_by_region:
            grid_cost = grid_cost_by_region[grid_region_id]
        else:
            grid_cost = default_grid_cost

        # LCOE from within_boundary (primary)
        lcoe_mid = wb.loc[kek_id, "lcoe_mid_usd_mwh"] if kek_id in wb.index else np.nan
        wb_cf = (
            float(wb.loc[kek_id, "cf"])
            if kek_id in wb.index and pd.notna(wb.loc[kek_id, "cf"])
            else 0.0
        )

        # Competitive gap (benchmark-dependent — uses grid_cost which may be BPP or tariff)
        if pd.notna(lcoe_mid) and grid_cost > 0:
            gap_pct = solar_competitive_gap(lcoe_mid, grid_cost)
            attractive = is_solar_attractive(
                lcoe_mid,
                grid_cost,
                pvout_best_50km=kek.get("pvout_best_50km"),
                pvout_threshold=thresholds.pvout_threshold,
            )
        else:
            gap_pct = np.nan
            attractive = False

        # Always compute both tariff and BPP gaps (independent of benchmark mode)
        tariff_rate = default_grid_cost  # PLN I-4/TT industrial tariff
        gap_vs_tariff_pct = (
            solar_competitive_gap(lcoe_mid, tariff_rate)
            if pd.notna(lcoe_mid) and tariff_rate > 0
            else np.nan
        )

        bpp_rate = np.nan
        if grid_df is not None and grid_region_id:
            bpp_rows = grid_df[grid_df["grid_region_id"] == grid_region_id]
            if len(bpp_rows):
                bpp_val = bpp_rows.iloc[0].get("bpp_usd_mwh")
                if pd.notna(bpp_val):
                    bpp_rate = float(bpp_val)
        gap_vs_bpp_pct = (
            solar_competitive_gap(lcoe_mid, bpp_rate)
            if pd.notna(lcoe_mid) and pd.notna(bpp_rate) and bpp_rate > 0
            else np.nan
        )

        # RUPTL metrics
        ruptl_row = (
            ruptl_metrics_df[ruptl_metrics_df["grid_region_id"] == grid_region_id]
            if grid_region_id and ruptl_metrics_df is not None
            else pd.DataFrame()
        )
        grid_upgrade_pre2030 = (
            bool(ruptl_row.iloc[0]["grid_upgrade_pre2030"]) if len(ruptl_row) else False
        )
        post2030_share = float(ruptl_row.iloc[0]["post2030_share"]) if len(ruptl_row) else 1.0

        # GEAS
        green_share = kek.get("green_share_geas", 0.0)
        if pd.isna(green_share):
            green_share = 0.0

        reliability_req = kek.get("reliability_req", 0.6)
        if pd.isna(reliability_req):
            reliability_req = 0.6

        # Action flags with user thresholds
        gi_cat = kek.get("grid_integration_category")
        gi_cat = gi_cat if pd.notna(gi_cat) else None
        flags = action_flags(
            solar_attractive=attractive,
            grid_upgrade_pre2030=grid_upgrade_pre2030,
            reliability_req=reliability_req,
            green_share_geas=green_share,
            post2030_share=post2030_share,
            grid_integration_cat=gi_cat,
        )

        # Override thresholds: use user values instead of hardcoded defaults
        flags["plan_late"] = post2030_share >= thresholds.plan_late_threshold
        flags["invest_transmission"] = attractive and gi_cat == "invest_transmission"
        flags["invest_substation"] = attractive and gi_cat == "invest_substation"
        flags["solar_now"] = (
            attractive
            and not flags["grid_first"]
            and not flags["invest_transmission"]
            and not flags["invest_substation"]
            and green_share >= thresholds.geas_threshold
        )
        flags["invest_battery"] = attractive and reliability_req >= thresholds.reliability_threshold
        resilience = invest_resilience_fn(
            solar_competitive_gap_pct=gap_pct if pd.notna(gap_pct) else 0.0,
            reliability_req=reliability_req,
            gap_threshold_pct=thresholds.resilience_gap_pct,
            reliability_threshold=thresholds.reliability_threshold,
        )

        # Carbon breakeven
        emission_factor = 0.0
        if grid_df is not None and grid_region_id:
            ef_row = grid_df[grid_df["grid_region_id"] == grid_region_id]
            if len(ef_row):
                ef_val = ef_row.iloc[0].get("grid_emission_factor_t_co2_mwh", 0.0)
                emission_factor = float(ef_val) if pd.notna(ef_val) else 0.0

        carbon_be = (
            carbon_breakeven_price(lcoe_mid, grid_cost, emission_factor)
            if pd.notna(lcoe_mid) and emission_factor > 0
            else None
        )

        # Project viable with user threshold
        max_mwp = kek.get("max_captive_capacity_mwp", 0.0)
        if pd.isna(max_mwp):
            max_mwp = 0.0
        project_viable = max_mwp >= thresholds.min_viable_mwp

        # Derive action_flag: first True flag wins (priority order)
        action_flag = ActionFlag.NOT_COMPETITIVE
        for flag_name in [
            ActionFlag.SOLAR_NOW,
            ActionFlag.INVEST_TRANSMISSION,
            ActionFlag.INVEST_SUBSTATION,
            ActionFlag.GRID_FIRST,
            ActionFlag.INVEST_BATTERY,
            ActionFlag.INVEST_RESILIENCE,
            ActionFlag.PLAN_LATE,
        ]:
            flag_val = (
                resilience
                if flag_name == ActionFlag.INVEST_RESILIENCE
                else flags.get(flag_name, False)
            )
            if flag_val is True:
                action_flag = flag_name
                break

        row = {
            "kek_id": kek_id,
            "action_flag": action_flag,
            "lcoe_mid_usd_mwh": _round(lcoe_mid),
            "lcoe_low_usd_mwh": _round(wb.loc[kek_id, "lcoe_low_usd_mwh"])
            if kek_id in wb.index
            else np.nan,
            "lcoe_high_usd_mwh": _round(wb.loc[kek_id, "lcoe_high_usd_mwh"])
            if kek_id in wb.index
            else np.nan,
            "solar_competitive_gap_pct": _round(gap_pct),
            "gap_vs_tariff_pct": _round(gap_vs_tariff_pct),
            "gap_vs_bpp_pct": _round(gap_vs_bpp_pct),
            "solar_attractive": attractive,
            "solar_now": flags["solar_now"],
            "invest_transmission": flags["invest_transmission"],
            "invest_substation": flags["invest_substation"],
            "invest_battery": flags["invest_battery"],
            "grid_first": flags["grid_first"],
            "battery_adder_usd_mwh": round(
                bess_storage_adder(
                    assumptions.bess_capex_usd_per_kwh,
                    solar_cf=wb_cf,
                    wacc=assumptions.wacc_decimal,
                ),
                2,
            )
            if flags["invest_battery"] and wb_cf and wb_cf > 0
            else 0.0,
            "lcoe_with_battery_usd_mwh": round(
                lcoe_mid
                + bess_storage_adder(
                    assumptions.bess_capex_usd_per_kwh,
                    solar_cf=wb_cf,
                    wacc=assumptions.wacc_decimal,
                ),
                2,
            )
            if flags["invest_battery"] and wb_cf and wb_cf > 0
            else _round(lcoe_mid),
            "land_cost_usd_per_kw": assumptions.land_cost_usd_per_kw,
            "demand_2030_gwh": round(demand_by_kek[kek_id] / 1000, 1)
            if kek_id in demand_by_kek
            else None,
            "green_share_geas": round(float(green_share), 4) if pd.notna(green_share) else None,
            "plan_late": flags["plan_late"],
            "invest_resilience": resilience,
            "carbon_breakeven_usd_tco2": carbon_be,
            "project_viable": project_viable,
            "grid_cost_usd_mwh": grid_cost,
            "wacc_pct": assumptions.wacc_pct,
            "capex_usd_per_kw": assumptions.capex_usd_per_kw,
        }

        # V2: Add grid-connected solar LCOE columns
        if kek_id in gc.index:
            row["lcoe_grid_connected_usd_mwh"] = _round(gc.loc[kek_id, "lcoe_mid_usd_mwh"])
            row["lcoe_grid_connected_low_usd_mwh"] = _round(gc.loc[kek_id, "lcoe_low_usd_mwh"])
            row["lcoe_grid_connected_high_usd_mwh"] = _round(gc.loc[kek_id, "lcoe_high_usd_mwh"])
            row["connection_cost_per_kw"] = gc.loc[kek_id, "connection_cost_per_kw"]
        else:
            row["lcoe_grid_connected_usd_mwh"] = np.nan
            row["lcoe_grid_connected_low_usd_mwh"] = np.nan
            row["lcoe_grid_connected_high_usd_mwh"] = np.nan
            row["connection_cost_per_kw"] = 0.0

        # V2: Pass through grid_integration_category from resource_df
        row["grid_integration_category"] = kek.get("grid_integration_category", None)

        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _round(value: float, decimals: int = 2) -> float:
    """Round a value, returning NaN unchanged."""
    if pd.isna(value):
        return np.nan
    return round(float(value), decimals)


def _round_add(base: float, adder: float, decimals: int = 2) -> float:
    """Add two values and round, returning NaN if base is NaN."""
    if pd.isna(base):
        return np.nan
    return round(float(base) + float(adder), decimals)


def get_default_assumptions() -> UserAssumptions:
    """Return default assumptions from src/assumptions.py constants."""
    return UserAssumptions()


def get_default_thresholds() -> UserThresholds:
    """Return default thresholds from src/assumptions.py constants."""
    return UserThresholds()
