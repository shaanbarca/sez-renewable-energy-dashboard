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
    BESS_BRIDGE_HOURS_ENABLED,
    BESS_CAPEX_USD_PER_KWH,
    BESS_SIZING_HOURS,
    CBAM_CERTIFICATE_PRICE_EUR_TCO2,
    CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE,
    CBAM_EUR_USD_RATE,
    CBAM_FREE_ALLOCATION,
    CBAM_SCOPE1_TCO2_PER_TONNE,
    CONNECTION_COST_PER_KW_KM,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    GRID_CONNECTION_FIXED_PER_KW,
    HYBRID_WIND_NIGHTTIME_FRACTION,
    IDR_USD_RATE,
    LAND_COST_USD_PER_KW,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PROJECT_VIABLE_MIN_MWP,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    SUBSTATION_UTILIZATION_PCT,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
    TRANSMISSION_FALLBACK_CAPACITY_MWP,
)
from src.model.basic_model import (
    ActionFlag,
    RESource,
    action_flags,
    bess_bridge_hours,
    bess_storage_adder,
    capacity_factor_from_pvout,
    carbon_breakeven_price,
    firm_solar_metrics,
    firm_wind_metrics,
    grid_connection_cost_per_kw,
    hybrid_lcoe_optimized,
    is_solar_attractive,
    lcoe_solar,
    new_transmission_cost_per_kw,
    solar_competitive_gap,
    substation_upgrade_cost_per_kw,
)
from src.model.basic_model import capacity_assessment as compute_capacity_assessment
from src.model.basic_model import grid_integration_category as compute_grid_integration_category
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
    substation_utilization_pct: float = SUBSTATION_UTILIZATION_PCT
    idr_usd_rate: float = IDR_USD_RATE
    grid_benchmark_usd_mwh: float = 63.08

    # BESS sizing override — None = auto (2h/4h/14h by reliability), set = fixed hours
    bess_sizing_hours_override: float | None = None

    # M18: DFI grant scenario — zero out grid connection costs
    grant_funded_transmission: bool = False

    # Project sizing — optional capacity override (H10)
    target_capacity_mwp: float | None = None

    # Hybrid RE: solar/wind mix ratio (None = auto-optimize per KEK)
    hybrid_solar_share: float | None = None

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
        d = {
            "capex_usd_per_kw": self.capex_usd_per_kw,
            "lifetime_yr": self.lifetime_yr,
            "wacc_pct": self.wacc_pct,
            "fom_usd_per_kw_yr": self.fom_usd_per_kw_yr,
            "connection_cost_per_kw_km": self.connection_cost_per_kw_km,
            "grid_connection_fixed_per_kw": self.grid_connection_fixed_per_kw,
            "bess_capex_usd_per_kwh": self.bess_capex_usd_per_kwh,
            "land_cost_usd_per_kw": self.land_cost_usd_per_kw,
            "substation_utilization_pct": self.substation_utilization_pct,
            "idr_usd_rate": self.idr_usd_rate,
            "grid_benchmark_usd_mwh": self.grid_benchmark_usd_mwh,
        }
        if self.bess_sizing_hours_override is not None:
            d["bess_sizing_hours_override"] = self.bess_sizing_hours_override
        if self.target_capacity_mwp is not None:
            d["target_capacity_mwp"] = self.target_capacity_mwp
        if self.grant_funded_transmission:
            d["grant_funded_transmission"] = True
        if self.hybrid_solar_share is not None:
            d["hybrid_solar_share"] = self.hybrid_solar_share
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "UserAssumptions":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class UserThresholds:
    """Action flag thresholds adjustable via dashboard sliders (Tier 3)."""

    pvout_threshold: float = 1350.0
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

        # Within-boundary scenario: prefer spatial PVOUT, fallback to centroid
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
            if assumptions.grant_funded_transmission:
                conn_cost = 0.0
            else:
                conn_cost = grid_connection_cost_per_kw(
                    dist_km,
                    assumptions.connection_cost_per_kw_km,
                    assumptions.grid_connection_fixed_per_kw,
                )
            land_cost = assumptions.land_cost_usd_per_kw

            # H10: effective capacity = min(user target, max buildable)
            max_mwp_val = kek.get("max_captive_capacity_mwp")
            max_mwp = (
                float(max_mwp_val)
                if pd.notna(max_mwp_val) and float(max_mwp_val) > 0
                else TRANSMISSION_FALLBACK_CAPACITY_MWP
            )
            effective_mwp = (
                min(assumptions.target_capacity_mwp, max_mwp)
                if assumptions.target_capacity_mwp
                else max_mwp
            )

            # V3.1: transmission line cost when substations are not connected
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

            # V3.2: substation upgrade cost when capacity is insufficient
            sub_cap = kek.get("nearest_substation_capacity_mva")
            sub_cap = float(sub_cap) if pd.notna(sub_cap) else None
            if assumptions.grant_funded_transmission:
                upgrade_cost = 0.0
            else:
                upgrade_cost = substation_upgrade_cost_per_kw(
                    sub_cap, effective_mwp, assumptions.substation_utilization_pct
                )

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
                "kek_id": kek_id,
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


# ---------------------------------------------------------------------------
# Live wind LCOE computation
# ---------------------------------------------------------------------------


def compute_lcoe_wind_live(
    resource_df: pd.DataFrame,
    wacc_pct: float,
    wind_capex: float = 1650.0,
    wind_fom: float = 40.0,
    wind_lifetime: int = 27,
) -> pd.DataFrame:
    """Compute wind LCOE for all KEKs at user-specified WACC.

    Uses precomputed CF from fct_kek_wind_resource and the same CRF annuity
    formula as solar (lcoe_solar is technology-agnostic).

    Parameters
    ----------
    resource_df:
        Must have wind columns from fct_kek_wind_resource merge:
        cf_wind_best_50km, cf_wind_centroid, wind_speed_best_50km_ms,
        wind_speed_centroid_ms.
    wacc_pct:
        WACC percentage (e.g. 10.0 for 10%).
    wind_capex, wind_fom, wind_lifetime:
        Wind technology cost parameters from dim_tech_cost_wind.

    Returns
    -------
    pd.DataFrame
        One row per KEK: kek_id, lcoe_wind_mid_usd_mwh, cf_wind, wind_speed_ms.
    """
    wacc = wacc_pct / 100.0
    rows = []

    for _, kek in resource_df.iterrows():
        kek_id = kek["kek_id"]

        # Use precomputed CF (best 50km, fallback centroid)
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
                "kek_id": kek_id,
                "lcoe_wind_mid_usd_mwh": _round(lcoe_wind),
                "cf_wind": _round(cf, 4),
                "wind_speed_ms": _round(ws, 2),
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
    wind_tech: dict | None = None,
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
    wind_tech:
        Wind technology cost parameters: capex_usd_per_kw, fom_usd_per_kw_yr,
        lifetime_yr. If None, uses defaults ($1,650/kW, $40/kW-yr, 27yr).
    """
    lcoe_df = compute_lcoe_live(resource_df, assumptions)

    # Wind LCOE (shares WACC with solar, uses wind-specific tech costs)
    wind_defaults = wind_tech or {
        "capex_usd_per_kw": 1650.0,
        "fom_usd_per_kw_yr": 40.0,
        "lifetime_yr": 27,
    }
    wind_lcoe_df = compute_lcoe_wind_live(
        resource_df,
        wacc_pct=assumptions.wacc_pct,
        wind_capex=wind_defaults["capex_usd_per_kw"],
        wind_fom=wind_defaults["fom_usd_per_kw_yr"],
        wind_lifetime=wind_defaults["lifetime_yr"],
    )
    wind_by_kek = wind_lcoe_df.set_index("kek_id")

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

        # Primary LCOE: prefer grid-connected (includes connection + upgrade costs)
        # Fall back to within-boundary if gc unavailable
        if kek_id in gc.index:
            lcoe_mid = gc.loc[kek_id, "lcoe_mid_usd_mwh"]
            primary_cf = float(gc.loc[kek_id, "cf"]) if pd.notna(gc.loc[kek_id, "cf"]) else 0.0
        else:
            lcoe_mid = wb.loc[kek_id, "lcoe_mid_usd_mwh"] if kek_id in wb.index else np.nan
            primary_cf = (
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

        # Live recalculate capacity assessment and grid integration category
        # using the user's substation utilization assumption + optional capacity override (H10)
        sub_cap_mva = kek.get("nearest_substation_capacity_mva")
        sub_cap_mva = float(sub_cap_mva) if pd.notna(sub_cap_mva) else None
        solar_cap_mwp = kek.get("max_captive_capacity_mwp")
        solar_cap_mwp = float(solar_cap_mwp) if pd.notna(solar_cap_mwp) else None

        # H10: override capacity with user target (capped at max buildable)
        effective_cap = solar_cap_mwp
        if assumptions.target_capacity_mwp and solar_cap_mwp:
            effective_cap = min(assumptions.target_capacity_mwp, solar_cap_mwp)

        cap_light, avail_mva = compute_capacity_assessment(
            sub_cap_mva, effective_cap, assumptions.substation_utilization_pct
        )

        has_internal = kek.get("has_internal_substation", False)
        has_internal = bool(has_internal) if pd.notna(has_internal) else False
        dist_solar = kek.get("dist_solar_to_nearest_substation_km")
        dist_solar = float(dist_solar) if pd.notna(dist_solar) else None
        dist_kek = kek.get("dist_to_nearest_substation_km", 0.0)
        dist_kek = float(dist_kek) if pd.notna(dist_kek) else 0.0
        inter_connected = kek.get("inter_substation_connected")
        inter_connected = bool(inter_connected) if pd.notna(inter_connected) else None

        # Within-boundary coverage: if on-site solar covers >= 100% of demand,
        # classify as within_boundary regardless of substation distances.
        wb_coverage = kek.get("within_boundary_coverage_pct")
        wb_coverage = float(wb_coverage) if pd.notna(wb_coverage) else None

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
        # No buildable land → no solar resource, skip all solar-dependent flags
        if max_mwp <= 0:
            action_flag = ActionFlag.NO_SOLAR_RESOURCE
        else:
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

        # BESS sizing: user override > bridge-hours for high-reliability > cloud-firming
        if assumptions.bess_sizing_hours_override is not None:
            bess_sizing = assumptions.bess_sizing_hours_override
        else:
            dominant_process = str(kek.get("dominant_process_type", "")).strip().upper()
            is_rkef = dominant_process == "RKEF"
            reliability = (
                float(kek.get("reliability_req", 0.6))
                if pd.notna(kek.get("reliability_req"))
                else 0.6
            )
            high_reliability = reliability >= thresholds.reliability_threshold
            if BESS_BRIDGE_HOURS_ENABLED and high_reliability:
                bess_sizing = bess_bridge_hours()
            elif is_rkef:
                bess_sizing = BESS_SIZING_HOURS * 2.0
            else:
                bess_sizing = BESS_SIZING_HOURS

        # BESS economics for all KEKs with solar resource (not gated by invest_battery)
        if primary_cf and primary_cf > 0:
            _bess_adder = round(
                bess_storage_adder(
                    assumptions.bess_capex_usd_per_kwh,
                    solar_cf=primary_cf,
                    wacc=assumptions.wacc_decimal,
                    sizing_hours=bess_sizing,
                ),
                2,
            )
            _lcoe_with_bess = round(lcoe_mid + _bess_adder, 2)
        else:
            _bess_adder = 0.0
            _lcoe_with_bess = _round(lcoe_mid)

        _bess_competitive = (
            bool(_lcoe_with_bess <= grid_cost)
            if pd.notna(_lcoe_with_bess) and grid_cost and grid_cost > 0
            else None
        )

        row = {
            "kek_id": kek_id,
            "action_flag": action_flag,
            "lcoe_mid_usd_mwh": _round(lcoe_mid),
            "lcoe_low_usd_mwh": _round(gc.loc[kek_id, "lcoe_low_usd_mwh"])
            if kek_id in gc.index
            else (_round(wb.loc[kek_id, "lcoe_low_usd_mwh"]) if kek_id in wb.index else np.nan),
            "lcoe_high_usd_mwh": _round(gc.loc[kek_id, "lcoe_high_usd_mwh"])
            if kek_id in gc.index
            else (_round(wb.loc[kek_id, "lcoe_high_usd_mwh"]) if kek_id in wb.index else np.nan),
            "solar_competitive_gap_pct": _round(gap_pct),
            "gap_vs_tariff_pct": _round(gap_vs_tariff_pct),
            "gap_vs_bpp_pct": _round(gap_vs_bpp_pct),
            "solar_attractive": attractive,
            "solar_now": flags["solar_now"],
            "invest_transmission": flags["invest_transmission"],
            "invest_substation": flags["invest_substation"],
            "invest_battery": flags["invest_battery"],
            "grid_first": flags["grid_first"],
            "battery_adder_usd_mwh": _bess_adder,
            "lcoe_with_battery_usd_mwh": _lcoe_with_bess,
            "bess_competitive": _bess_competitive,
            "bess_sizing_hours": bess_sizing,
            "land_cost_usd_per_kw": assumptions.land_cost_usd_per_kw,
            "demand_2030_gwh": round(demand_by_kek[kek_id] / 1000, 1)
            if kek_id in demand_by_kek
            else None,
            "max_solar_generation_gwh": _round(
                float(kek.get("max_captive_capacity_mwp", 0))
                * float(kek.get("pvout_best_50km", 0))
                / 1000
            )
            if pd.notna(kek.get("max_captive_capacity_mwp"))
            and pd.notna(kek.get("pvout_best_50km"))
            else None,
            "solar_supply_coverage_pct": round(
                (
                    float(kek.get("max_captive_capacity_mwp", 0))
                    * float(kek.get("pvout_best_50km", 0))
                )
                / demand_by_kek[kek_id],
                3,
            )
            if kek_id in demand_by_kek
            and demand_by_kek[kek_id] > 0
            and pd.notna(kek.get("max_captive_capacity_mwp"))
            and pd.notna(kek.get("pvout_best_50km"))
            else None,
            "within_boundary_generation_gwh": _round(
                float(kek.get("within_boundary_capacity_mwp", 0))
                * float(
                    kek.get("pvout_within_boundary")
                    if pd.notna(kek.get("pvout_within_boundary"))
                    else kek.get("pvout_centroid", 0)
                )
                / 1000
            )
            if pd.notna(kek.get("within_boundary_capacity_mwp"))
            and (pd.notna(kek.get("pvout_within_boundary")) or pd.notna(kek.get("pvout_centroid")))
            else None,
            "within_boundary_coverage_pct": round(
                (
                    float(kek.get("within_boundary_capacity_mwp", 0))
                    * float(
                        kek.get("pvout_within_boundary")
                        if pd.notna(kek.get("pvout_within_boundary"))
                        else kek.get("pvout_centroid", 0)
                    )
                )
                / demand_by_kek[kek_id],
                3,
            )
            if kek_id in demand_by_kek
            and demand_by_kek[kek_id] > 0
            and pd.notna(kek.get("within_boundary_capacity_mwp"))
            and (pd.notna(kek.get("pvout_within_boundary")) or pd.notna(kek.get("pvout_centroid")))
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

        # Wind LCOE (live-computed, responds to WACC slider)
        if kek_id in wind_by_kek.index:
            w = wind_by_kek.loc[kek_id]
            row["lcoe_wind_mid_usd_mwh"] = w["lcoe_wind_mid_usd_mwh"]
            row["cf_wind"] = w["cf_wind"]
            row["wind_speed_ms"] = w["wind_speed_ms"]
        else:
            row["lcoe_wind_mid_usd_mwh"] = np.nan
            row["cf_wind"] = 0.0
            row["wind_speed_ms"] = 0.0

        # Best RE technology: compare solar (with BESS), wind, and hybrid all-in
        wind_lcoe_val = row.get("lcoe_wind_mid_usd_mwh")
        solar_lcoe_val = row.get("lcoe_mid_usd_mwh")
        hybrid_allin_val = row.get("hybrid_allin_usd_mwh")

        candidates: dict[str, float] = {}
        if pd.notna(solar_lcoe_val):
            candidates["solar"] = float(solar_lcoe_val)
        if pd.notna(wind_lcoe_val):
            candidates["wind"] = float(wind_lcoe_val)
        if hybrid_allin_val is not None and pd.notna(hybrid_allin_val):
            candidates["hybrid"] = float(hybrid_allin_val)

        if candidates:
            best_tech = min(candidates, key=candidates.get)
            row["best_re_technology"] = best_tech
            row["best_re_lcoe_mid_usd_mwh"] = candidates[best_tech]
        else:
            row["best_re_technology"] = "solar"
            row["best_re_lcoe_mid_usd_mwh"] = np.nan

        # Wind competitive gap vs BPP
        if pd.notna(wind_lcoe_val) and pd.notna(bpp_rate) and bpp_rate > 0:
            row["wind_competitive_gap_pct"] = _round(solar_competitive_gap(wind_lcoe_val, bpp_rate))
        else:
            row["wind_competitive_gap_pct"] = np.nan

        # Wind buildability + supply coverage (from pipeline data)
        wind_cap = (
            float(kek.get("max_wind_capacity_mwp", 0))
            if pd.notna(kek.get("max_wind_capacity_mwp"))
            else 0.0
        )
        wind_cf_best = (
            float(kek.get("cf_wind_buildable_best", 0))
            if pd.notna(kek.get("cf_wind_buildable_best"))
            else row.get("cf_wind", 0.0)
        )
        wind_gen_gwh = (
            wind_cap * wind_cf_best * 8760 / 1000 if wind_cap > 0 and wind_cf_best > 0 else 0.0
        )
        _demand_mwh = demand_by_kek.get(kek_id, 0.0)
        demand_gwh = _demand_mwh / 1000 if _demand_mwh > 0 else 0.0

        row["max_wind_capacity_mwp"] = _round(wind_cap, 1)
        row["wind_buildable_area_ha"] = (
            _round(float(kek.get("wind_buildable_area_ha", 0)))
            if pd.notna(kek.get("wind_buildable_area_ha"))
            else 0.0
        )
        row["wind_buildability_constraint"] = (
            str(kek.get("wind_buildability_constraint", "unknown"))
            if pd.notna(kek.get("wind_buildability_constraint"))
            else "unknown"
        )
        row["max_wind_generation_gwh"] = _round(wind_gen_gwh, 1)
        row["wind_supply_coverage_pct"] = (
            round(wind_gen_gwh / demand_gwh, 3) if demand_gwh > 0 and wind_gen_gwh > 0 else None
        )

        # Wind carbon breakeven (same formula as solar, different LCOE input)
        row["wind_carbon_breakeven_usd_tco2"] = (
            carbon_breakeven_price(wind_lcoe_val, grid_cost, emission_factor)
            if pd.notna(wind_lcoe_val) and emission_factor > 0
            else None
        )

        # V3.3: Firm solar metrics — temporal mismatch awareness
        solar_gen_mwh = (
            (float(kek.get("max_captive_capacity_mwp", 0)) * float(kek.get("pvout_best_50km", 0)))
            if pd.notna(kek.get("max_captive_capacity_mwp"))
            and pd.notna(kek.get("pvout_best_50km"))
            else 0.0
        )
        demand_mwh_val = demand_by_kek.get(kek_id, 0.0)
        firm_metrics = firm_solar_metrics(solar_gen_mwh, demand_mwh_val)
        row["firm_solar_coverage_pct"] = firm_metrics["firm_solar_coverage_pct"]
        row["nighttime_demand_mwh"] = firm_metrics["nighttime_demand_mwh"]
        row["storage_required_mwh"] = firm_metrics["storage_required_mwh"]
        row["storage_gap_pct"] = firm_metrics["storage_gap_pct"]

        # Wind temporal metrics (intermittency-based, not day/night)
        wind_gen_mwh = wind_gen_gwh * 1000
        wind_firm = firm_wind_metrics(wind_gen_mwh, demand_mwh_val, wind_cf_best)
        row["firm_wind_coverage_pct"] = wind_firm["firm_wind_coverage_pct"]
        row["wind_firming_gap_pct"] = wind_firm["wind_firming_gap_pct"]
        row["wind_firming_hours"] = wind_firm["wind_firming_hours"]

        # Hybrid solar+wind: blended LCOE with reduced BESS from complementary profiles
        solar_source = RESource(
            technology="solar",
            lcoe_usd_mwh=float(lcoe_mid) if pd.notna(lcoe_mid) else np.nan,
            generation_mwh=solar_gen_mwh,
            cf=primary_cf,
            nighttime_fraction=0.0,
            capacity_mwp=float(kek.get("max_captive_capacity_mwp", 0))
            if pd.notna(kek.get("max_captive_capacity_mwp"))
            else 0.0,
        )
        wind_source = RESource(
            technology="wind",
            lcoe_usd_mwh=float(wind_lcoe_val) if pd.notna(wind_lcoe_val) else np.nan,
            generation_mwh=wind_gen_mwh,
            cf=wind_cf_best,
            nighttime_fraction=HYBRID_WIND_NIGHTTIME_FRACTION,
            capacity_mwp=wind_cap,
        )
        hybrid = hybrid_lcoe_optimized(
            sources=[solar_source, wind_source],
            demand_mwh=demand_mwh_val,
            bess_capex_usd_per_kwh=assumptions.bess_capex_usd_per_kwh,
            wacc=assumptions.wacc_decimal,
            solar_share_override=assumptions.hybrid_solar_share,
        )
        row["hybrid_lcoe_usd_mwh"] = hybrid["hybrid_lcoe_usd_mwh"]
        row["hybrid_bess_hours"] = hybrid["hybrid_bess_hours"]
        row["hybrid_bess_adder_usd_mwh"] = hybrid["hybrid_bess_adder_usd_mwh"]
        row["hybrid_allin_usd_mwh"] = hybrid["hybrid_allin_usd_mwh"]
        row["hybrid_solar_share"] = hybrid["optimal_solar_share"]
        row["hybrid_supply_coverage_pct"] = hybrid["hybrid_supply_coverage_pct"]
        row["hybrid_nighttime_coverage_pct"] = hybrid["hybrid_nighttime_coverage_pct"]
        # BESS reduction: how much hybrid cuts from solar-only 14h bridge
        solar_bess = bess_bridge_hours()
        h_bess = hybrid["hybrid_bess_hours"]
        row["hybrid_bess_reduction_pct"] = (
            round((solar_bess - h_bess) / solar_bess * 100, 1) if h_bess is not None else None
        )
        # Hybrid carbon breakeven
        h_allin = hybrid["hybrid_allin_usd_mwh"]
        row["hybrid_carbon_breakeven_usd_tco2"] = (
            carbon_breakeven_price(h_allin, grid_cost, emission_factor)
            if h_allin is not None and pd.notna(h_allin) and emission_factor > 0
            else None
        )

        # Within-boundary LCOE (secondary, for reference — captive solar, no connection costs)
        if kek_id in wb.index:
            row["lcoe_within_boundary_usd_mwh"] = _round(wb.loc[kek_id, "lcoe_mid_usd_mwh"])
            row["lcoe_within_boundary_low_usd_mwh"] = _round(wb.loc[kek_id, "lcoe_low_usd_mwh"])
            row["lcoe_within_boundary_high_usd_mwh"] = _round(wb.loc[kek_id, "lcoe_high_usd_mwh"])
        else:
            row["lcoe_within_boundary_usd_mwh"] = np.nan
            row["lcoe_within_boundary_low_usd_mwh"] = np.nan
            row["lcoe_within_boundary_high_usd_mwh"] = np.nan

        # Connection cost from gc scenario (for display)
        row["connection_cost_per_kw"] = (
            gc.loc[kek_id, "connection_cost_per_kw"] if kek_id in gc.index else 0.0
        )

        # V3.1: Live-computed grid integration + capacity (uses user's utilization slider)
        row["grid_integration_category"] = gi_cat
        row["capacity_assessment"] = cap_light
        row["available_capacity_mva"] = avail_mva

        # V3.1: Pass through connectivity columns from resource_df (not affected by utilization)
        row["same_grid_region"] = kek.get("same_grid_region", None)
        row["line_connected"] = kek.get("line_connected", None)
        row["inter_substation_connected"] = kek.get("inter_substation_connected", None)
        row["inter_substation_dist_km"] = kek.get("inter_substation_dist_km", None)

        # V3.2: Use live-computed transmission + upgrade costs from compute_lcoe_live
        row["transmission_cost_per_kw"] = (
            gc.loc[kek_id, "transmission_cost_per_kw"] if kek_id in gc.index else 0.0
        )
        row["substation_upgrade_cost_per_kw"] = (
            gc.loc[kek_id, "substation_upgrade_cost_per_kw"] if kek_id in gc.index else 0.0
        )

        # H10: effective capacity used for this KEK (may be capped by user target)
        row["effective_capacity_mwp"] = (
            gc.loc[kek_id, "effective_capacity_mwp"] if kek_id in gc.index else None
        )

        # Grid investment needed (USD): total infra cost × effective capacity (kW)
        gc_conn = (
            float(row["connection_cost_per_kw"]) if pd.notna(row["connection_cost_per_kw"]) else 0.0
        )
        gc_trans = (
            float(row["transmission_cost_per_kw"])
            if pd.notna(row["transmission_cost_per_kw"])
            else 0.0
        )
        gc_upgrade = (
            float(row["substation_upgrade_cost_per_kw"])
            if pd.notna(row["substation_upgrade_cost_per_kw"])
            else 0.0
        )
        infra_cost = gc_conn + gc_trans + gc_upgrade
        # Use effective capacity for investment calculation (respects user target)
        eff_mwp = row.get("effective_capacity_mwp") or kek.get("max_captive_capacity_mwp", 0.0)
        if pd.isna(eff_mwp):
            eff_mwp = 0.0
        if infra_cost > 0 and eff_mwp > 0:
            row["grid_investment_needed_usd"] = round(infra_cost * eff_mwp * 1000)
        else:
            row["grid_investment_needed_usd"] = None

        row["dist_solar_to_nearest_substation_km"] = kek.get(
            "dist_solar_to_nearest_substation_km", None
        )
        row["dist_to_nearest_substation_km"] = kek.get("dist_to_nearest_substation_km", None)

        # H9: Captive power context (pass-through from resource_df summaries)
        row["captive_coal_count"] = (
            int(kek.get("captive_coal_count", 0))
            if pd.notna(kek.get("captive_coal_count"))
            else None
        )
        row["captive_coal_mw"] = (
            int(kek.get("captive_coal_mw", 0)) if pd.notna(kek.get("captive_coal_mw")) else None
        )
        row["captive_coal_plants"] = (
            str(kek.get("captive_coal_plants", ""))
            if pd.notna(kek.get("captive_coal_plants"))
            else None
        )
        row["nickel_smelter_count"] = (
            int(kek.get("nickel_smelter_count", 0))
            if pd.notna(kek.get("nickel_smelter_count"))
            else None
        )
        row["nickel_projects"] = (
            str(kek.get("nickel_projects", "")) if pd.notna(kek.get("nickel_projects")) else None
        )
        row["dominant_process_type"] = (
            str(kek.get("dominant_process_type", ""))
            if pd.notna(kek.get("dominant_process_type"))
            else None
        )
        row["has_chinese_ownership"] = (
            bool(kek.get("has_chinese_ownership"))
            if pd.notna(kek.get("has_chinese_ownership"))
            else False
        )

        # H8: Perpres 112/2022 compliance status
        coal_count = row.get("captive_coal_count")
        if coal_count and coal_count > 0:
            row["has_captive_coal"] = True
            row["perpres_112_status"] = "Subject to 2050 phase-out"
        else:
            row["has_captive_coal"] = False
            row["perpres_112_status"] = None

        # CBAM exposure: EU Carbon Border Adjustment Mechanism (2026+)
        # Two signals: (1) nickel pipeline process types, (2) KEK business sectors
        cbam_types: list[str] = []

        # Signal 1: RKEF nickel process → iron/steel CN codes
        process = str(row.get("dominant_process_type") or "").strip()
        if process in {"Nickel Pig Iron", "Ferro Nickel"}:
            cbam_types.append("iron_steel")

        # Signal 2: KEK business sectors → CBAM categories
        # Mapping: KEK sector name → CBAM product type
        _SECTOR_CBAM_MAP = {
            "Base Metal Industry": "iron_steel",
            "Nickel Smelter Industry": "iron_steel",
            "Bauxite Industry": "aluminium",
            "Petrochemical Industry": "fertilizer",
        }
        sectors_str = str(kek.get("business_sectors") or "")
        for sector_name, cbam_type in _SECTOR_CBAM_MAP.items():
            if sector_name in sectors_str and cbam_type not in cbam_types:
                cbam_types.append(cbam_type)

        row["cbam_exposed"] = len(cbam_types) > 0
        row["cbam_product_type"] = ",".join(cbam_types) if cbam_types else None

        # CBAM cost trajectory: compute costs at key years (2026, 2030, 2034)
        # Uses grid emission factor + sector electricity intensity + scope 1 process emissions
        if cbam_types:
            # Use the first (primary) CBAM type for cost estimates
            primary_type = cbam_types[0]
            elec_intensity = CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE.get(primary_type, 0)
            scope1 = CBAM_SCOPE1_TCO2_PER_TONNE.get(primary_type, 0)
            grid_ef = row.get("grid_emission_factor_t_co2_mwh") or 0.8  # fallback: Indonesia avg

            # Total emission intensity (tCO₂/tonne product) = scope2 + scope1
            scope2 = elec_intensity * grid_ef
            total_ei = scope2 + scope1
            row["cbam_emission_intensity_current"] = round(total_ei, 1)

            # Emission intensity if renewables adopted (scope 1 remains, scope 2 ≈ 0)
            row["cbam_emission_intensity_solar"] = round(scope1, 1)

            # Cost per tonne at key years (USD)
            price_usd = CBAM_CERTIFICATE_PRICE_EUR_TCO2 * CBAM_EUR_USD_RATE
            for year in [2026, 2030, 2034]:
                free_alloc = CBAM_FREE_ALLOCATION.get(year, 0.0)
                effective_rate = price_usd * (1 - free_alloc)
                row[f"cbam_cost_{year}_usd_per_tonne"] = round(total_ei * effective_rate, 0)
                row[f"cbam_savings_{year}_usd_per_tonne"] = round(
                    scope2 * effective_rate, 0
                )  # savings from eliminating scope 2
        else:
            row["cbam_emission_intensity_current"] = None
            row["cbam_emission_intensity_solar"] = None
            for year in [2026, 2030, 2034]:
                row[f"cbam_cost_{year}_usd_per_tonne"] = None
                row[f"cbam_savings_{year}_usd_per_tonne"] = None

        # Solar replacement potential: what % of captive coal generation can solar replace?
        # Assumes 40% capacity factor for coal (Indonesian captive coal typical)
        coal_mw = row.get("captive_coal_mw")
        solar_gen = row.get("max_solar_generation_gwh")
        if coal_mw and coal_mw > 0 and solar_gen and solar_gen > 0:
            coal_gen_gwh = coal_mw * 8.76 * 0.40  # MW → GWh/yr at 40% CF
            row["captive_coal_generation_gwh"] = round(coal_gen_gwh, 1)
            row["solar_replacement_pct"] = round(solar_gen / coal_gen_gwh * 100, 0)
        else:
            row["captive_coal_generation_gwh"] = None
            row["solar_replacement_pct"] = None

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
