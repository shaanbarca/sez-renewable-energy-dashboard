# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Scorecard orchestrator — live per-site computation for the dashboard.

`compute_scorecard_live` is the single entry point called on every assumption-
slider change. For each site it:

  1. Builds a read-only `SiteContext` (rates, LCOE, grid integration bundle,
     generation totals). See `src.dash.logic.site_context`.
  2. Runs the `STAGES` pipeline of enrichers. Each enricher is a pure
     `(ctx, row) -> dict` that merges new fields into the row.

All math lives in `src.model.basic_model` and sibling domain modules
(`lcoe`, `grid`, `technology`, `cbam`). This module is pure orchestration —
no formulas, only wiring.

Adding a new column or domain: write one enricher, append it to `STAGES`.
Do not grow the per-row loop.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from src.assumptions import CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE
from src.dash.logic.assumptions import UserAssumptions, UserThresholds
from src.dash.logic.cbam import _detect_cbam_types, compute_cbam_trajectory
from src.dash.logic.lcoe import _round, compute_lcoe_live, compute_lcoe_wind_live
from src.dash.logic.site_context import SiteContext, build_site_context
from src.dash.logic.technology import (
    compute_bess_metrics,
    compute_firm_coverage,
    compute_hybrid_metrics,
)
from src.model.basic_model import (
    ActionFlag,
    EconomicTier,
    action_flags,
    bess_storage_adder,
    carbon_breakeven_price,
    economic_tier,
    solar_competitive_gap,
)
from src.model.basic_model import invest_resilience as invest_resilience_fn
from src.pipeline.assumptions import TARIFF_I4_RP_KWH, rp_kwh_to_usd_mwh

Enricher = Callable[[SiteContext, dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# Enrichers — each takes (ctx, row_so_far) and returns dict to merge.
# ---------------------------------------------------------------------------


def enrich_lcoe_and_gaps(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Primary LCOE (mid/low/high), competitive gaps, secondary within-boundary LCOE."""
    out: dict[str, Any] = {
        "lcoe_mid_usd_mwh": _round(ctx.lcoe_mid),
        "solar_competitive_gap_pct": _round(ctx.gap_pct),
        "gap_vs_tariff_pct": _round(ctx.gap_vs_tariff_pct),
        "gap_vs_bpp_pct": _round(ctx.gap_vs_bpp_pct),
        "solar_attractive": ctx.attractive,
    }

    # low/high: prefer grid-connected, fall back to within-boundary
    if ctx.gc_row is not None:
        out["lcoe_low_usd_mwh"] = _round(ctx.gc_row["lcoe_low_usd_mwh"])
        out["lcoe_high_usd_mwh"] = _round(ctx.gc_row["lcoe_high_usd_mwh"])
    elif ctx.wb_row is not None:
        out["lcoe_low_usd_mwh"] = _round(ctx.wb_row["lcoe_low_usd_mwh"])
        out["lcoe_high_usd_mwh"] = _round(ctx.wb_row["lcoe_high_usd_mwh"])
    else:
        out["lcoe_low_usd_mwh"] = np.nan
        out["lcoe_high_usd_mwh"] = np.nan

    # Secondary within-boundary LCOE (captive solar, no connection cost)
    if ctx.wb_row is not None:
        out["lcoe_within_boundary_usd_mwh"] = _round(ctx.wb_row["lcoe_mid_usd_mwh"])
        out["lcoe_within_boundary_low_usd_mwh"] = _round(ctx.wb_row["lcoe_low_usd_mwh"])
        out["lcoe_within_boundary_high_usd_mwh"] = _round(ctx.wb_row["lcoe_high_usd_mwh"])
    else:
        out["lcoe_within_boundary_usd_mwh"] = np.nan
        out["lcoe_within_boundary_low_usd_mwh"] = np.nan
        out["lcoe_within_boundary_high_usd_mwh"] = np.nan

    return out


def enrich_grid_passthroughs(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Grid integration fields (category, infra cost, connectivity, capacity)."""
    return dict(ctx.grid_out)


def enrich_action_flags(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Individual flag booleans + resilience + priority-winner `action_flag`."""
    gi_cat = ctx.grid_out["grid_integration_category"]
    flags = action_flags(
        solar_attractive=ctx.attractive,
        grid_upgrade_pre2030=ctx.grid_upgrade_pre2030,
        reliability_req=ctx.reliability_req,
        green_share_geas=ctx.green_share,
        post2030_share=ctx.post2030_share,
        grid_integration_cat=gi_cat,
    )
    t = ctx.thresholds
    flags["plan_late"] = ctx.post2030_share >= t.plan_late_threshold
    flags["invest_transmission"] = ctx.attractive and gi_cat == "invest_transmission"
    flags["invest_substation"] = ctx.attractive and gi_cat == "invest_substation"
    flags["solar_now"] = (
        ctx.attractive
        and not flags["grid_first"]
        and not flags["invest_transmission"]
        and not flags["invest_substation"]
        and ctx.green_share >= t.geas_threshold
    )
    flags["invest_battery"] = ctx.attractive and ctx.reliability_req >= t.reliability_threshold
    resilience = invest_resilience_fn(
        solar_competitive_gap_pct=ctx.gap_pct if pd.notna(ctx.gap_pct) else 0.0,
        reliability_req=ctx.reliability_req,
        gap_threshold_pct=t.resilience_gap_pct,
        reliability_threshold=t.reliability_threshold,
    )

    # Priority winner: first True in rank order, or NO_SOLAR_RESOURCE / NOT_COMPETITIVE
    if ctx.max_mwp <= 0:
        action_flag: ActionFlag = ActionFlag.NO_SOLAR_RESOURCE
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

    return {
        "action_flag": action_flag,
        "solar_now": flags["solar_now"],
        "invest_transmission": flags["invest_transmission"],
        "invest_substation": flags["invest_substation"],
        "invest_battery": flags["invest_battery"],
        "grid_first": flags["grid_first"],
        "plan_late": flags["plan_late"],
        "invest_resilience": resilience,
    }


def enrich_carbon_and_viability(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Carbon breakeven + project_viable + raw assumption echoes used by the UI."""
    carbon_be = (
        carbon_breakeven_price(ctx.lcoe_mid, ctx.grid_cost, ctx.emission_factor)
        if pd.notna(ctx.lcoe_mid) and ctx.emission_factor > 0
        else None
    )
    return {
        "carbon_breakeven_usd_tco2": carbon_be,
        "project_viable": ctx.max_mwp >= ctx.thresholds.min_viable_mwp,
        "grid_cost_usd_mwh": ctx.grid_cost,
        "wacc_pct": ctx.assumptions.wacc_pct,
        "capex_usd_per_kw": ctx.assumptions.capex_usd_per_kw,
        "land_cost_usd_per_kw": ctx.assumptions.land_cost_usd_per_kw,
    }


def enrich_bess(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """BESS sizing, $/MWh adder, LCOE-with-battery, competitiveness flag."""
    m = compute_bess_metrics(
        lcoe_mid=ctx.lcoe_mid,
        primary_cf=ctx.primary_cf,
        reliability_req=ctx.reliability_req,
        dominant_process=str(ctx.kek.get("dominant_process_type", "")),
        assumptions=ctx.assumptions,
        thresholds=ctx.thresholds,
        grid_cost=ctx.grid_cost,
    )
    return {
        "bess_sizing_hours": m["bess_sizing_hours"],
        "battery_adder_usd_mwh": m["battery_adder_usd_mwh"],
        "lcoe_with_battery_usd_mwh": m["lcoe_with_battery_usd_mwh"],
        "bess_competitive": m["bess_competitive"],
    }


def enrich_generation(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Demand, solar generation, supply coverage, within-boundary generation."""
    kek = ctx.kek
    out: dict[str, Any] = {}

    out["demand_2030_gwh"] = round(ctx.demand_mwh / 1000, 1) if ctx.demand_mwh > 0 else None
    out["green_share_geas"] = round(ctx.green_share, 4)

    if ctx.solar_data_valid:
        out["max_solar_generation_gwh"] = _round(ctx.solar_gen_mwh / 1000)
        out["solar_supply_coverage_pct"] = (
            round(ctx.solar_gen_mwh / ctx.demand_mwh, 3) if ctx.demand_mwh > 0 else None
        )
    else:
        out["max_solar_generation_gwh"] = None
        out["solar_supply_coverage_pct"] = None

    # Within-boundary generation: use pvout_within_boundary if present, else pvout_centroid
    wb_cap = kek.get("within_boundary_capacity_mwp")
    pvout_wb = kek.get("pvout_within_boundary")
    pvout_cent = kek.get("pvout_centroid")
    pvout_for_wb = pvout_wb if pd.notna(pvout_wb) else pvout_cent
    if pd.notna(wb_cap) and pd.notna(pvout_for_wb):
        wb_gen_mwh = float(wb_cap) * float(pvout_for_wb)
        out["within_boundary_generation_gwh"] = _round(wb_gen_mwh / 1000)
        out["within_boundary_coverage_pct"] = (
            round(wb_gen_mwh / ctx.demand_mwh, 3) if ctx.demand_mwh > 0 else None
        )
    else:
        out["within_boundary_generation_gwh"] = None
        out["within_boundary_coverage_pct"] = None

    return out


def enrich_wind(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Wind LCOE, CF, speed, buildability, supply coverage, carbon breakeven, BPP gap."""
    out: dict[str, Any] = {}
    w = ctx.wind_row
    if w is not None:
        out["lcoe_wind_mid_usd_mwh"] = w["lcoe_wind_mid_usd_mwh"]
        out["cf_wind"] = w["cf_wind"]
        out["wind_speed_ms"] = w["wind_speed_ms"]
    else:
        out["lcoe_wind_mid_usd_mwh"] = np.nan
        out["cf_wind"] = 0.0
        out["wind_speed_ms"] = 0.0

    wind_lcoe_val = out["lcoe_wind_mid_usd_mwh"]
    out["wind_competitive_gap_pct"] = (
        _round(solar_competitive_gap(wind_lcoe_val, ctx.bpp_rate))
        if pd.notna(wind_lcoe_val) and pd.notna(ctx.bpp_rate) and ctx.bpp_rate > 0
        else np.nan
    )

    wind_gen_gwh = ctx.wind_gen_mwh / 1000
    demand_gwh = ctx.demand_mwh / 1000 if ctx.demand_mwh > 0 else 0.0

    out["max_wind_capacity_mwp"] = _round(ctx.wind_cap, 1)
    out["wind_buildable_area_ha"] = (
        _round(float(ctx.kek.get("wind_buildable_area_ha", 0)))
        if pd.notna(ctx.kek.get("wind_buildable_area_ha"))
        else 0.0
    )
    out["wind_buildability_constraint"] = (
        str(ctx.kek.get("wind_buildability_constraint", "unknown"))
        if pd.notna(ctx.kek.get("wind_buildability_constraint"))
        else "unknown"
    )
    out["max_wind_generation_gwh"] = _round(wind_gen_gwh, 1)
    out["wind_supply_coverage_pct"] = (
        round(wind_gen_gwh / demand_gwh, 3) if demand_gwh > 0 and wind_gen_gwh > 0 else None
    )
    out["wind_carbon_breakeven_usd_tco2"] = (
        carbon_breakeven_price(wind_lcoe_val, ctx.grid_cost, ctx.emission_factor)
        if pd.notna(wind_lcoe_val) and ctx.emission_factor > 0
        else None
    )
    return out


def enrich_firm_coverage(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Temporal-aware solar + wind coverage metrics (firm / gap / firming hours)."""
    return compute_firm_coverage(
        solar_gen_mwh=ctx.solar_gen_mwh,
        wind_gen_mwh=ctx.wind_gen_mwh,
        demand_mwh=ctx.demand_mwh,
        wind_cf_best=ctx.wind_cf_best,
    )


def enrich_hybrid(ctx: SiteContext, row: dict[str, Any]) -> dict[str, Any]:
    """Hybrid solar+wind optimisation (LCOE, BESS reduction, coverage, carbon breakeven).

    Requires: enrich_wind (reads `lcoe_wind_mid_usd_mwh` from row).
    """
    return compute_hybrid_metrics(
        solar_lcoe=ctx.lcoe_mid,
        wind_lcoe=row.get("lcoe_wind_mid_usd_mwh"),
        solar_gen_mwh=ctx.solar_gen_mwh,
        wind_gen_mwh=ctx.wind_gen_mwh,
        primary_cf=ctx.primary_cf,
        wind_cf_best=ctx.wind_cf_best,
        solar_capacity_mwp=ctx.max_mwp,
        wind_capacity_mwp=ctx.wind_cap,
        demand_mwh=ctx.demand_mwh,
        assumptions=ctx.assumptions,
        grid_cost=ctx.grid_cost,
        emission_factor=ctx.emission_factor,
    )


def _opt_int(kek: pd.Series, key: str) -> int | None:
    v = kek.get(key)
    return int(v) if pd.notna(v) else None


def _opt_float(kek: pd.Series, key: str) -> float | None:
    v = kek.get(key)
    return float(v) if pd.notna(v) else None


def _opt_str(kek: pd.Series, key: str) -> str | None:
    v = kek.get(key)
    return str(v) if pd.notna(v) else None


def _bool_or_false(kek: pd.Series, key: str) -> bool:
    v = kek.get(key)
    return bool(v) if pd.notna(v) else False


def enrich_captive_context(ctx: SiteContext, _row: dict[str, Any]) -> dict[str, Any]:
    """Captive power context: coal, nickel, steel, cement + Perpres 112 status."""
    k = ctx.kek
    out: dict[str, Any] = {
        "captive_coal_count": _opt_int(k, "captive_coal_count"),
        "captive_coal_mw": _opt_int(k, "captive_coal_mw"),
        "captive_coal_plants": _opt_str(k, "captive_coal_plants"),
        "nickel_smelter_count": _opt_int(k, "nickel_smelter_count"),
        "nickel_projects": _opt_str(k, "nickel_projects"),
        "dominant_process_type": _opt_str(k, "dominant_process_type"),
        "has_chinese_ownership": _bool_or_false(k, "has_chinese_ownership"),
        "steel_plant_count": _opt_int(k, "steel_plant_count"),
        "steel_capacity_tpa": _opt_float(k, "steel_capacity_tpa"),
        "steel_plants": _opt_str(k, "steel_plants"),
        "steel_has_chinese_ownership": _bool_or_false(k, "steel_has_chinese_ownership"),
        "cement_plant_count": _opt_int(k, "cement_plant_count"),
        "cement_capacity_mtpa": _opt_float(k, "cement_capacity_mtpa"),
        "cement_plants": _opt_str(k, "cement_plants"),
        "cement_has_chinese_ownership": _bool_or_false(k, "cement_has_chinese_ownership"),
    }
    coal_count = out["captive_coal_count"] or 0
    if coal_count > 0:
        out["has_captive_coal"] = True
        out["perpres_112_status"] = "Subject to 2050 phase-out"
    else:
        out["has_captive_coal"] = False
        out["perpres_112_status"] = None
    return out


def enrich_cbam(ctx: SiteContext, row: dict[str, Any]) -> dict[str, Any]:
    """CBAM detection, trajectory, adjusted gap, urgent flag, and action-flag override.

    Requires: enrich_grid_passthroughs (`grid_emission_factor_t_co2_mwh`),
    enrich_action_flags (`action_flag`) — both read from row.
    """
    cbam_types = _detect_cbam_types(ctx.kek, row)
    out = dict(
        compute_cbam_trajectory(
            cbam_types,
            grid_ef_t_co2_mwh=row.get("grid_emission_factor_t_co2_mwh"),
            cbam_price_eur=ctx.assumptions.cbam_certificate_price_eur,
            eur_usd_rate=ctx.assumptions.cbam_eur_usd_rate,
        )
    )

    if out.get("cbam_exposed") and pd.notna(ctx.lcoe_mid) and ctx.grid_cost > 0:
        primary_type = cbam_types[0] if cbam_types else None
        elec_intensity = (
            CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE.get(primary_type, 0) if primary_type else 0
        )
        if elec_intensity > 0:
            savings_per_tonne = out.get("cbam_savings_2030_usd_per_tonne") or 0
            cbam_savings_mwh = savings_per_tonne / elec_intensity
            out["cbam_savings_per_mwh"] = round(cbam_savings_mwh, 1)
            adjusted_lcoe = ctx.lcoe_mid - cbam_savings_mwh
            out["cbam_adjusted_gap_pct"] = round(
                ((adjusted_lcoe - ctx.grid_cost) / ctx.grid_cost) * 100, 1
            )
        else:
            out["cbam_savings_per_mwh"] = None
            out["cbam_adjusted_gap_pct"] = None
    else:
        out["cbam_savings_per_mwh"] = None
        out["cbam_adjusted_gap_pct"] = None

    adj_gap = out.get("cbam_adjusted_gap_pct")
    out["cbam_urgent"] = bool(out.get("cbam_exposed") and adj_gap is not None and adj_gap < 0)

    # Override action flag: CBAM flips the economics even when RE alone doesn't beat grid
    current_flag = row.get("action_flag")
    if out["cbam_urgent"] and current_flag in (
        ActionFlag.NOT_COMPETITIVE,
        ActionFlag.INVEST_RESILIENCE,
    ):
        out["action_flag"] = ActionFlag.CBAM_URGENT

    return out


def enrich_cross_domain(ctx: SiteContext, row: dict[str, Any]) -> dict[str, Any]:
    """Cross-domain derivations: best RE tech, 2D tier, badges, wind all-in, coal replacement.

    Requires: enrich_lcoe_and_gaps, enrich_wind, enrich_hybrid, enrich_bess,
    enrich_action_flags, enrich_firm_coverage, enrich_cbam — reads many fields
    from row (lcoe_*_usd_mwh, hybrid_allin_usd_mwh, bess_*_allin_usd_mwh,
    action_flag, firm_solar_coverage_pct, cbam_urgent, plan_late, etc.).
    """
    out: dict[str, Any] = {}

    # Best RE technology by bare LCOE (solar/wind/hybrid)
    candidates: dict[str, float] = {}
    if pd.notna(row.get("lcoe_mid_usd_mwh")):
        candidates["solar"] = float(row["lcoe_mid_usd_mwh"])
    if pd.notna(row.get("lcoe_wind_mid_usd_mwh")):
        candidates["wind"] = float(row["lcoe_wind_mid_usd_mwh"])
    h = row.get("hybrid_allin_usd_mwh")
    if h is not None and pd.notna(h):
        candidates["hybrid"] = float(h)

    if candidates:
        best_tech = min(candidates, key=candidates.get)
        out["best_re_technology"] = best_tech
        out["best_re_lcoe_mid_usd_mwh"] = candidates[best_tech]
    else:
        out["best_re_technology"] = "solar"
        out["best_re_lcoe_mid_usd_mwh"] = np.nan

    # 2D classification inputs
    solar_lcoe = float(ctx.lcoe_mid) if pd.notna(ctx.lcoe_mid) else None
    wind_lcoe = (
        float(row["lcoe_wind_mid_usd_mwh"]) if pd.notna(row.get("lcoe_wind_mid_usd_mwh")) else None
    )
    hybrid_lcoe = (
        float(row["hybrid_lcoe_usd_mwh"])
        if row.get("hybrid_lcoe_usd_mwh") is not None and pd.notna(row.get("hybrid_lcoe_usd_mwh"))
        else None
    )
    lcoe_candidates = [v for v in [solar_lcoe, wind_lcoe, hybrid_lcoe] if v is not None]
    best_lcoe_re = min(lcoe_candidates) if lcoe_candidates else None

    solar_allin = (
        float(row["lcoe_with_battery_usd_mwh"])
        if pd.notna(row.get("lcoe_with_battery_usd_mwh"))
        else None
    )
    hybrid_allin = (
        float(row["hybrid_allin_usd_mwh"])
        if row.get("hybrid_allin_usd_mwh") is not None and pd.notna(row.get("hybrid_allin_usd_mwh"))
        else None
    )

    # Wind all-in = wind LCOE + BESS sized to firming hours
    wind_allin: float | None = None
    wind_firming_h = row.get("wind_firming_hours")
    if wind_lcoe is not None and ctx.wind_cf_best > 0 and wind_firming_h and wind_firming_h > 0:
        w_bess_adder = bess_storage_adder(
            ctx.assumptions.bess_capex_usd_per_kwh,
            solar_cf=ctx.wind_cf_best,
            wacc=ctx.assumptions.wacc_decimal,
            sizing_hours=float(wind_firming_h),
        )
        wind_allin = round(wind_lcoe + w_bess_adder, 2)
    out["lcoe_wind_allin_mid_usd_mwh"] = wind_allin

    allin_candidates = [v for v in [solar_allin, wind_allin, hybrid_allin] if v is not None]
    best_allin = min(allin_candidates) if allin_candidates else None

    has_resource = ctx.max_mwp > 0 or ctx.wind_cap > 0
    econ_tier = economic_tier(
        lcoe_re=best_lcoe_re,
        allin_24_7=best_allin,
        grid_cost=ctx.grid_cost,
        has_resource=has_resource,
        near_parity_threshold_pct=ctx.thresholds.resilience_gap_pct,
    )
    out["economic_tier"] = econ_tier
    out["infrastructure_readiness"] = ctx.grid_out["grid_integration_category"]

    # Modifier badges (overlay signals that cross-cut the 2D grid)
    badges: list[str] = []
    if row.get("plan_late"):
        badges.append("plan_late")
    if row.get("cbam_urgent"):
        badges.append("cbam_urgent")
    if (
        econ_tier in (EconomicTier.PARTIAL_RE, EconomicTier.NEAR_PARITY)
        and ctx.reliability_req >= ctx.thresholds.reliability_threshold
    ):
        badges.append("storage_info")
    out["modifier_badges"] = badges

    # Solar replacement potential for captive coal (assumes 40% coal CF)
    coal_mw = row.get("captive_coal_mw")
    solar_gen = row.get("max_solar_generation_gwh")
    if coal_mw and coal_mw > 0 and solar_gen and solar_gen > 0:
        coal_gen_gwh = coal_mw * 8.76 * 0.40
        out["captive_coal_generation_gwh"] = round(coal_gen_gwh, 1)
        out["solar_replacement_pct"] = round(solar_gen / coal_gen_gwh * 100, 0)
    else:
        out["captive_coal_generation_gwh"] = None
        out["solar_replacement_pct"] = None

    return out


# ---------------------------------------------------------------------------
# Pipeline — STAGES run in order. Each reads ctx + row-so-far, returns dict to
# merge into row. New columns = new enricher + append here.
# ---------------------------------------------------------------------------

STAGES: list[Enricher] = [
    enrich_lcoe_and_gaps,
    enrich_grid_passthroughs,
    enrich_action_flags,
    enrich_carbon_and_viability,
    enrich_bess,
    enrich_generation,
    enrich_wind,
    enrich_firm_coverage,
    enrich_hybrid,
    enrich_captive_context,
    enrich_cbam,
    enrich_cross_domain,
]


# ---------------------------------------------------------------------------
# Orchestrator — thin loop, no domain math.
# ---------------------------------------------------------------------------


def compute_scorecard_live(  # noqa: PLR0913 — main dashboard entry point; each arg is an independent pipeline input
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

    Main entry point called by the dashboard on every assumption-slider change.
    Returns one row per site.

    Parameters
    ----------
    resource_df:
        fct_site_resource with PVOUT columns + dist_to_nearest_substation_km.
    assumptions, thresholds:
        User-adjustable model assumptions and flag thresholds.
    ruptl_metrics_df:
        Pre-aggregated RUPTL metrics per grid_region_id.
    demand_df:
        fct_site_demand filtered to target year. Columns: site_id, demand_mwh.
    grid_df:
        fct_grid_cost_proxy. Columns: grid_region_id, bpp_usd_mwh, grid_emission_factor_t_co2_mwh.
    grid_cost_by_region:
        Optional BPP override (BPP benchmark mode). If None, uses PLN I-4/TT tariff.
    wind_tech:
        Wind tech cost parameters (capex, FOM, lifetime). If None, uses defaults.
    """
    # Shared setup (computed once, indexed for fast per-row lookup)
    lcoe_df = compute_lcoe_live(resource_df, assumptions)
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
    wind_by_site = wind_lcoe_df.set_index("site_id")
    wb = lcoe_df[lcoe_df["scenario"] == "within_boundary"].set_index("site_id")
    gc = lcoe_df[lcoe_df["scenario"] == "grid_connected_solar"].set_index("site_id")

    default_grid_cost = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH, assumptions.idr_usd_rate)

    demand_by_site: dict[str, float] = {}
    if demand_df is not None and not demand_df.empty:
        for _, d_row in demand_df.iterrows():
            demand_by_site[d_row["site_id"]] = float(d_row["demand_mwh"])

    # Per-row pipeline
    rows: list[dict[str, Any]] = []
    for _, kek in resource_df.iterrows():
        site_id = kek["site_id"]
        ctx = build_site_context(
            kek=kek,
            assumptions=assumptions,
            thresholds=thresholds,
            gc_row=gc.loc[site_id] if site_id in gc.index else None,
            wb_row=wb.loc[site_id] if site_id in wb.index else None,
            wind_row=wind_by_site.loc[site_id] if site_id in wind_by_site.index else None,
            default_grid_cost=default_grid_cost,
            grid_cost_by_region=grid_cost_by_region,
            grid_df=grid_df,
            ruptl_metrics_df=ruptl_metrics_df,
            demand_by_site=demand_by_site,
        )
        row: dict[str, Any] = {"site_id": site_id}
        for stage in STAGES:
            row.update(stage(ctx, row))
        rows.append(row)

    return pd.DataFrame(rows)
