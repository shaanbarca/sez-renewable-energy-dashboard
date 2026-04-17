# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Scorecard orchestrator — live per-site computation for the dashboard.

`compute_scorecard_live` is the single entry point called on every assumption-
slider change. It walks each site and assembles the row by delegating domain
work to sibling modules:

- `lcoe` — solar + wind LCOE at user WACC / CAPEX
- `grid` — capacity + category + infra cost + connectivity pass-throughs
- `technology` — BESS sizing, firm coverage, hybrid solar+wind optimization
- `cbam` — product-type detection + 2026/2030/2034 cost trajectory
- `assumptions` — UserAssumptions / UserThresholds dataclasses

All formulas live in `src/model/basic_model.py`. This module only orchestrates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import (
    CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE,
)
from src.dash.logic.assumptions import (
    UserAssumptions,
    UserThresholds,
)
from src.dash.logic.cbam import (
    _detect_cbam_types,
    compute_cbam_trajectory,
)
from src.dash.logic.grid import compute_grid_integration
from src.dash.logic.lcoe import (
    _round,
    compute_lcoe_live,
    compute_lcoe_wind_live,
)
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
    is_solar_attractive,
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
# Live scorecard computation (flags, gap, carbon breakeven)
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

    This is the main entry point called by the dashboard callback whenever any
    assumption slider changes. Returns one row per KEK.

    Parameters
    ----------
    resource_df:
        fct_site_resource with PVOUT columns + dist_to_nearest_substation_km.
    assumptions:
        User-adjustable model assumptions.
    thresholds:
        User-adjustable flag thresholds.
    ruptl_metrics_df:
        Pre-aggregated RUPTL metrics per grid_region_id (from ruptl_region_metrics()).
        Columns: grid_region_id, post2030_share, grid_upgrade_pre2030.
    demand_df:
        fct_site_demand filtered to target year. Columns: site_id, demand_mwh.
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
    wind_by_site = wind_lcoe_df.set_index("site_id")

    # Extract within_boundary rows for primary comparison
    wb = lcoe_df[lcoe_df["scenario"] == "within_boundary"].set_index("site_id")
    gc = lcoe_df[lcoe_df["scenario"] == "grid_connected_solar"].set_index("site_id")

    default_grid_cost = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH, assumptions.idr_usd_rate)

    # Index demand by site_id for fast lookup
    demand_by_site: dict[str, float] = {}
    if demand_df is not None and not demand_df.empty:
        for _, d_row in demand_df.iterrows():
            demand_by_site[d_row["site_id"]] = float(d_row["demand_mwh"])

    rows = []
    for _, kek in resource_df.iterrows():
        site_id = kek["site_id"]
        grid_region_id = kek.get("grid_region_id")

        # Per-region grid cost (BPP mode) or uniform tariff
        if grid_cost_by_region and grid_region_id and grid_region_id in grid_cost_by_region:
            grid_cost = grid_cost_by_region[grid_region_id]
        else:
            grid_cost = default_grid_cost

        # Primary LCOE: prefer grid-connected (includes connection + upgrade costs)
        # Fall back to within-boundary if gc unavailable
        if site_id in gc.index:
            lcoe_mid = gc.loc[site_id, "lcoe_mid_usd_mwh"]
            primary_cf = float(gc.loc[site_id, "cf"]) if pd.notna(gc.loc[site_id, "cf"]) else 0.0
        else:
            lcoe_mid = wb.loc[site_id, "lcoe_mid_usd_mwh"] if site_id in wb.index else np.nan
            primary_cf = (
                float(wb.loc[site_id, "cf"])
                if site_id in wb.index and pd.notna(wb.loc[site_id, "cf"])
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

        # Grid integration: capacity + category + infra cost (extracted to grid.py)
        grid_out = compute_grid_integration(
            kek=kek,
            gc_row=gc.loc[site_id] if site_id in gc.index else None,
            assumptions=assumptions,
        )
        gi_cat = grid_out["grid_integration_category"]
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

        # BESS sizing + storage adder + LCOE-with-BESS (extracted to technology.py)
        _bess = compute_bess_metrics(
            lcoe_mid=lcoe_mid,
            primary_cf=primary_cf,
            reliability_req=float(reliability_req),
            dominant_process=str(kek.get("dominant_process_type", "")),
            assumptions=assumptions,
            thresholds=thresholds,
            grid_cost=grid_cost,
        )
        bess_sizing = _bess["bess_sizing_hours"]
        _bess_adder = _bess["battery_adder_usd_mwh"]
        _lcoe_with_bess = _bess["lcoe_with_battery_usd_mwh"]
        _bess_competitive = _bess["bess_competitive"]

        row = {
            "site_id": site_id,
            "action_flag": action_flag,
            "lcoe_mid_usd_mwh": _round(lcoe_mid),
            "lcoe_low_usd_mwh": _round(gc.loc[site_id, "lcoe_low_usd_mwh"])
            if site_id in gc.index
            else (_round(wb.loc[site_id, "lcoe_low_usd_mwh"]) if site_id in wb.index else np.nan),
            "lcoe_high_usd_mwh": _round(gc.loc[site_id, "lcoe_high_usd_mwh"])
            if site_id in gc.index
            else (_round(wb.loc[site_id, "lcoe_high_usd_mwh"]) if site_id in wb.index else np.nan),
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
            "demand_2030_gwh": round(demand_by_site[site_id] / 1000, 1)
            if site_id in demand_by_site
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
                / demand_by_site[site_id],
                3,
            )
            if site_id in demand_by_site
            and demand_by_site[site_id] > 0
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
                / demand_by_site[site_id],
                3,
            )
            if site_id in demand_by_site
            and demand_by_site[site_id] > 0
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
        if site_id in wind_by_site.index:
            w = wind_by_site.loc[site_id]
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
        _demand_mwh = demand_by_site.get(site_id, 0.0)
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

        # V3.3: Firm solar + wind temporal metrics (extracted to technology.py)
        solar_gen_mwh = (
            (float(kek.get("max_captive_capacity_mwp", 0)) * float(kek.get("pvout_best_50km", 0)))
            if pd.notna(kek.get("max_captive_capacity_mwp"))
            and pd.notna(kek.get("pvout_best_50km"))
            else 0.0
        )
        demand_mwh_val = demand_by_site.get(site_id, 0.0)
        wind_gen_mwh = wind_gen_gwh * 1000
        row.update(
            compute_firm_coverage(
                solar_gen_mwh=solar_gen_mwh,
                wind_gen_mwh=wind_gen_mwh,
                demand_mwh=demand_mwh_val,
                wind_cf_best=wind_cf_best,
            )
        )

        # Hybrid solar+wind (extracted to technology.py)
        solar_cap_mwp_val = (
            float(kek.get("max_captive_capacity_mwp", 0))
            if pd.notna(kek.get("max_captive_capacity_mwp"))
            else 0.0
        )
        row.update(
            compute_hybrid_metrics(
                solar_lcoe=lcoe_mid,
                wind_lcoe=wind_lcoe_val,
                solar_gen_mwh=solar_gen_mwh,
                wind_gen_mwh=wind_gen_mwh,
                primary_cf=primary_cf,
                wind_cf_best=wind_cf_best,
                solar_capacity_mwp=solar_cap_mwp_val,
                wind_capacity_mwp=wind_cap,
                demand_mwh=demand_mwh_val,
                assumptions=assumptions,
                grid_cost=grid_cost,
                emission_factor=emission_factor,
            )
        )

        # Within-boundary LCOE (secondary, for reference — captive solar, no connection costs)
        if site_id in wb.index:
            row["lcoe_within_boundary_usd_mwh"] = _round(wb.loc[site_id, "lcoe_mid_usd_mwh"])
            row["lcoe_within_boundary_low_usd_mwh"] = _round(wb.loc[site_id, "lcoe_low_usd_mwh"])
            row["lcoe_within_boundary_high_usd_mwh"] = _round(wb.loc[site_id, "lcoe_high_usd_mwh"])
        else:
            row["lcoe_within_boundary_usd_mwh"] = np.nan
            row["lcoe_within_boundary_low_usd_mwh"] = np.nan
            row["lcoe_within_boundary_high_usd_mwh"] = np.nan

        # Grid integration + capacity + infra cost + connectivity pass-throughs
        # (all fields pre-computed by compute_grid_integration above).
        row.update(grid_out)

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

        # Steel plant context (GEM Iron and Steel Plant Tracker)
        row["steel_plant_count"] = (
            int(kek.get("steel_plant_count", 0)) if pd.notna(kek.get("steel_plant_count")) else None
        )
        row["steel_capacity_tpa"] = (
            float(kek.get("steel_capacity_tpa", 0))
            if pd.notna(kek.get("steel_capacity_tpa"))
            else None
        )
        row["steel_plants"] = (
            str(kek.get("steel_plants", "")) if pd.notna(kek.get("steel_plants")) else None
        )
        row["steel_has_chinese_ownership"] = (
            bool(kek.get("steel_has_chinese_ownership"))
            if pd.notna(kek.get("steel_has_chinese_ownership"))
            else False
        )

        # Cement plant context (GEM Global Cement Plant Tracker)
        row["cement_plant_count"] = (
            int(kek.get("cement_plant_count", 0))
            if pd.notna(kek.get("cement_plant_count"))
            else None
        )
        row["cement_capacity_mtpa"] = (
            float(kek.get("cement_capacity_mtpa", 0))
            if pd.notna(kek.get("cement_capacity_mtpa"))
            else None
        )
        row["cement_plants"] = (
            str(kek.get("cement_plants", "")) if pd.notna(kek.get("cement_plants")) else None
        )
        row["cement_has_chinese_ownership"] = (
            bool(kek.get("cement_has_chinese_ownership"))
            if pd.notna(kek.get("cement_has_chinese_ownership"))
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

        # CBAM exposure: dispatch on SiteTypeConfig.cbam_method
        #   - "direct"   → read cbam_product_type from dim_sites (standalone/cluster/KI)
        #   - "3_signal" → detect from nickel process + plant counts + business sectors (KEK)
        cbam_types = _detect_cbam_types(kek, row)
        row.update(
            compute_cbam_trajectory(
                cbam_types,
                grid_ef_t_co2_mwh=row.get("grid_emission_factor_t_co2_mwh"),
                cbam_price_eur=assumptions.cbam_certificate_price_eur,
                eur_usd_rate=assumptions.cbam_eur_usd_rate,
            )
        )

        # CBAM-adjusted competitive gap: subtract avoided CBAM cost per MWh from effective LCOE
        if row.get("cbam_exposed") and pd.notna(lcoe_mid) and grid_cost > 0:
            primary_type = cbam_types[0] if cbam_types else None
            elec_intensity = (
                CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE.get(primary_type, 0) if primary_type else 0
            )
            if elec_intensity > 0:
                savings_per_tonne = row.get("cbam_savings_2030_usd_per_tonne") or 0
                cbam_savings_mwh = savings_per_tonne / elec_intensity
                row["cbam_savings_per_mwh"] = round(cbam_savings_mwh, 1)
                adjusted_lcoe = lcoe_mid - cbam_savings_mwh
                row["cbam_adjusted_gap_pct"] = round(
                    ((adjusted_lcoe - grid_cost) / grid_cost) * 100, 1
                )
            else:
                row["cbam_savings_per_mwh"] = None
                row["cbam_adjusted_gap_pct"] = None
        else:
            row["cbam_savings_per_mwh"] = None
            row["cbam_adjusted_gap_pct"] = None

        # CBAM urgent: CBAM-adjusted gap is negative (RE + avoided CBAM beats grid)
        # even though standard gap may be positive (RE alone doesn't beat grid)
        adj_gap = row.get("cbam_adjusted_gap_pct")
        row["cbam_urgent"] = bool(row.get("cbam_exposed") and adj_gap is not None and adj_gap < 0)

        # Override action flag: if CBAM makes RE win and current flag is not_competitive,
        # upgrade to cbam_urgent (solar alone doesn't beat grid, but CBAM flips it)
        if row["cbam_urgent"] and row["action_flag"] in (
            ActionFlag.NOT_COMPETITIVE,
            ActionFlag.INVEST_RESILIENCE,
        ):
            row["action_flag"] = ActionFlag.CBAM_URGENT

        # ── 2D Economic Tier × Infrastructure Readiness ──────────────────────
        # Resolve best bare LCOE and best all-in (with storage) across technologies.
        _solar_lcoe_val = float(lcoe_mid) if pd.notna(lcoe_mid) else None
        _wind_lcoe_val = (
            float(row["lcoe_wind_mid_usd_mwh"])
            if pd.notna(row.get("lcoe_wind_mid_usd_mwh"))
            else None
        )
        _hybrid_lcoe_val = (
            float(row["hybrid_lcoe_usd_mwh"])
            if row.get("hybrid_lcoe_usd_mwh") is not None
            and pd.notna(row.get("hybrid_lcoe_usd_mwh"))
            else None
        )

        _lcoe_candidates = [
            v for v in [_solar_lcoe_val, _wind_lcoe_val, _hybrid_lcoe_val] if v is not None
        ]
        _best_lcoe_re = min(_lcoe_candidates) if _lcoe_candidates else None

        # All-in with storage for 24/7 coverage
        _solar_allin = float(_lcoe_with_bess) if pd.notna(_lcoe_with_bess) else None
        _hybrid_allin = (
            float(row["hybrid_allin_usd_mwh"])
            if row.get("hybrid_allin_usd_mwh") is not None
            and pd.notna(row.get("hybrid_allin_usd_mwh"))
            else None
        )
        # Wind all-in: wind LCOE + BESS for firming hours
        _wind_allin = None
        _wind_firming_h = row.get("wind_firming_hours")
        if (
            _wind_lcoe_val is not None
            and wind_cf_best > 0
            and _wind_firming_h
            and _wind_firming_h > 0
        ):
            _w_bess_adder = bess_storage_adder(
                assumptions.bess_capex_usd_per_kwh,
                solar_cf=wind_cf_best,
                wacc=assumptions.wacc_decimal,
                sizing_hours=float(_wind_firming_h),
            )
            _wind_allin = round(_wind_lcoe_val + _w_bess_adder, 2)

        _allin_candidates = [v for v in [_solar_allin, _wind_allin, _hybrid_allin] if v is not None]
        _best_allin = min(_allin_candidates) if _allin_candidates else None
        row["lcoe_wind_allin_mid_usd_mwh"] = _wind_allin

        _has_re_resource = max_mwp > 0 or wind_cap > 0

        _econ_tier = economic_tier(
            lcoe_re=_best_lcoe_re,
            allin_24_7=_best_allin,
            grid_cost=grid_cost,
            has_resource=_has_re_resource,
            near_parity_threshold_pct=thresholds.resilience_gap_pct,
        )

        row["economic_tier"] = _econ_tier
        row["infrastructure_readiness"] = gi_cat

        # Modifier badges
        _badges: list[str] = []
        if flags["plan_late"]:
            _badges.append("plan_late")
        if row.get("cbam_urgent"):
            _badges.append("cbam_urgent")
        if _econ_tier in (EconomicTier.PARTIAL_RE, EconomicTier.NEAR_PARITY):
            if reliability_req >= thresholds.reliability_threshold:
                _badges.append("storage_info")
        row["modifier_badges"] = _badges

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


def _round_add(base: float, adder: float, decimals: int = 2) -> float:
    """Add two values and round, returning NaN if base is NaN."""
    if pd.isna(base):
        return np.nan
    return round(float(base) + float(adder), decimals)
