# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Per-row site context for `compute_scorecard_live`.

The scorecard orchestrator walks each site and assembles a row by running a
pipeline of enrichers. Each enricher is a pure `(ctx, row) -> dict` function.
`SiteContext` is the read-only scratchpad passed to every enricher: raw inputs
plus scalars computed once per site that multiple enrichers need (LCOE, gap,
grid integration bundle, rates, generation totals).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.dash.logic.assumptions import UserAssumptions, UserThresholds
from src.dash.logic.grid import compute_grid_integration
from src.model.basic_model import is_solar_attractive, solar_competitive_gap
from src.model.columns import Col
from src.model.geothermal_adjacency import dispatchable_re_from_geothermal_tier


@dataclass(slots=True)
class SiteContext:
    kek: pd.Series
    site_id: str
    grid_region_id: Any
    assumptions: UserAssumptions
    thresholds: UserThresholds

    # Rates and per-region grid data
    grid_cost: float
    tariff_rate: float
    bpp_rate: float
    emission_factor: float
    post2030_share: float
    grid_upgrade_pre2030: bool

    # Site attributes (resolved to concrete floats/bools)
    reliability_req: float
    green_share: float
    max_mwp: float
    wind_cap: float
    wind_cf_best: float
    demand_mwh: float

    # Resolved generation totals (MWh, unrounded)
    solar_gen_mwh: float
    wind_gen_mwh: float
    solar_data_valid: bool

    # Joined scenario rows from LCOE tables
    gc_row: pd.Series | None
    wb_row: pd.Series | None
    wind_row: pd.Series | None

    # Primary derivations (solar)
    lcoe_mid: float
    primary_cf: float
    gap_pct: float
    attractive: bool
    gap_vs_tariff_pct: float
    gap_vs_bpp_pct: float

    # Grid integration bundle (category + infra cost + connectivity + capacity)
    grid_out: dict[str, Any]

    # F2: Dispatchable-RE (geothermal today, hydro in v4.1b) — feeds F1's
    # Supply Blend cascade. coverage_pct=0 + lcoe=None means the cascade falls
    # through to its v4.0 3-layer behavior.
    dispatchable_re_coverage_pct: float
    dispatchable_re_lcoe_usd_mwh: float | None

    # v4.3 M-AT8b — captive incumbent for non-grid_only sites.
    # The site drawer's "Competitive Gap" surfaces the gap to the *actual*
    # incumbent: captive_incumbent_lcoe for pure_captive / hybrid sites,
    # grid_cost for grid_only sites. `effective_incumbent_lcoe` is the
    # value used in gap_pct math. `gap_vs_grid_pct` always references
    # grid_cost so the secondary comparator stays visible in the drawer.
    # Hybrid sites surface both via the secondary field.
    #
    # Defaults set so existing test code constructing SiteContext directly
    # with v4.0 positional args keeps working — captive fields default to
    # None and effective_incumbent collapses back to grid_cost in
    # build_site_context's resolution logic.
    electricity_arrangement: str | None = None
    captive_fuel_type: str | None = None
    captive_incumbent_lcoe: float | None = None
    captive_lcoe_tier: str | None = None
    captive_classification_confidence: str | None = None
    effective_incumbent_lcoe: float = 0.0
    effective_incumbent_kind: str = "grid"
    gap_vs_grid_pct: float = float("nan")


def _as_float(x: Any, default: float = 0.0) -> float:
    return float(x) if pd.notna(x) else default


def build_site_context(  # noqa: PLR0913 — single builder collects all per-site inputs
    *,
    kek: pd.Series,
    assumptions: UserAssumptions,
    thresholds: UserThresholds,
    gc_row: pd.Series | None,
    wb_row: pd.Series | None,
    wind_row: pd.Series | None,
    default_grid_cost: float,
    grid_cost_by_region: dict[str, float] | None,
    grid_df: pd.DataFrame | None,
    ruptl_metrics_df: pd.DataFrame | None,
    demand_by_site: dict[str, float],
) -> SiteContext:
    site_id = kek["site_id"]
    grid_region_id = kek.get("grid_region_id")

    if grid_cost_by_region and grid_region_id and grid_region_id in grid_cost_by_region:
        grid_cost = grid_cost_by_region[grid_region_id]
    else:
        grid_cost = default_grid_cost
    tariff_rate = default_grid_cost

    bpp_rate = np.nan
    emission_factor = 0.0
    if grid_df is not None and grid_region_id:
        rows = grid_df[grid_df["grid_region_id"] == grid_region_id]
        if len(rows):
            r0 = rows.iloc[0]
            bpp_val = r0.get("bpp_usd_mwh")
            if pd.notna(bpp_val):
                bpp_rate = float(bpp_val)
            emission_factor = _as_float(r0.get("grid_emission_factor_t_co2_mwh"))

    post2030_share = 1.0
    grid_upgrade_pre2030 = False
    if grid_region_id and ruptl_metrics_df is not None:
        ru = ruptl_metrics_df[ruptl_metrics_df["grid_region_id"] == grid_region_id]
        if len(ru):
            post2030_share = float(ru.iloc[0]["post2030_share"])
            grid_upgrade_pre2030 = bool(ru.iloc[0]["grid_upgrade_pre2030"])

    reliability_req = _as_float(kek.get("reliability_req"), default=0.6)
    green_share = _as_float(kek.get("green_share_geas"))
    max_mwp = _as_float(kek.get(Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM))
    wind_cap = _as_float(kek.get("max_wind_capacity_mwp"))

    # wind_cf_best: prefer per-site buildable best, fall back to wind LCOE table
    if pd.notna(kek.get("cf_wind_buildable_best")):
        wind_cf_best = float(kek.get("cf_wind_buildable_best"))
    elif wind_row is not None and pd.notna(wind_row.get("cf_wind")):
        wind_cf_best = float(wind_row["cf_wind"])
    else:
        wind_cf_best = 0.0

    demand_mwh = demand_by_site.get(site_id, 0.0)

    # Generation totals (MWh, unrounded — enrichers that care about coverage use these)
    solar_data_valid = pd.notna(kek.get(Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM)) and pd.notna(
        kek.get("pvout_best_50km")
    )
    solar_gen_mwh = (
        float(kek.get(Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM))
        * float(kek.get("pvout_best_50km"))
        if solar_data_valid
        else 0.0
    )
    wind_gen_mwh = wind_cap * wind_cf_best * 8760 if wind_cap > 0 and wind_cf_best > 0 else 0.0

    # V3.9: Compute grid integration first so the primary LCOE pick can respect
    # `grid_integration_category`. When a site qualifies as within_boundary
    # (on-site solar covers >= meaningful_share_pct of demand, KEK-only), the
    # displayed LCOE must use the within-boundary scenario (centroid PVOUT, no
    # conn/trans/upgrade costs) — otherwise we'd contradict the zeroed infra
    # cost rollup shown in the GridTab.
    grid_out = compute_grid_integration(kek=kek, gc_row=gc_row, assumptions=assumptions)
    gi_cat = grid_out.get("grid_integration_category")

    if gi_cat == "within_boundary" and wb_row is not None:
        lcoe_mid = wb_row["lcoe_mid_usd_mwh"]
        primary_cf = _as_float(wb_row.get("cf"))
    elif gc_row is not None:
        lcoe_mid = gc_row["lcoe_mid_usd_mwh"]
        primary_cf = _as_float(gc_row.get("cf"))
    elif wb_row is not None:
        lcoe_mid = wb_row["lcoe_mid_usd_mwh"]
        primary_cf = _as_float(wb_row.get("cf"))
    else:
        lcoe_mid = np.nan
        primary_cf = 0.0

    # v4.3 M-AT8b — resolve the effective incumbent comparator.
    # For pure_captive / hybrid_captive_primary / grid_primary_with_captive,
    # the incumbent the user actually pays is the captive plant LCOE, not
    # the PLN grid tariff. Use captive_incumbent_lcoe when available;
    # fall back to grid_cost when the site is grid_only or the captive
    # LCOE wasn't populated (shouldn't happen post-M-AT8a for classified sites).
    arrangement_raw = kek.get("electricity_arrangement")
    electricity_arrangement = (
        str(arrangement_raw) if arrangement_raw is not None and pd.notna(arrangement_raw) else None
    )
    captive_fuel_raw = kek.get("captive_fuel_type")
    captive_fuel_type = (
        str(captive_fuel_raw)
        if captive_fuel_raw is not None
        and pd.notna(captive_fuel_raw)
        and captive_fuel_raw != "none"
        else None
    )
    captive_inc_val = kek.get("captive_incumbent_lcoe_usd_mwh")
    captive_incumbent_lcoe = (
        float(captive_inc_val)
        if captive_inc_val is not None and pd.notna(captive_inc_val)
        else None
    )
    captive_lcoe_tier_val = kek.get("captive_lcoe_tier")
    captive_lcoe_tier = (
        str(captive_lcoe_tier_val)
        if captive_lcoe_tier_val is not None and pd.notna(captive_lcoe_tier_val)
        else None
    )
    captive_classification_confidence_val = kek.get("captive_classification_confidence")
    captive_classification_confidence = (
        str(captive_classification_confidence_val)
        if captive_classification_confidence_val is not None
        and pd.notna(captive_classification_confidence_val)
        else None
    )

    use_captive = (
        electricity_arrangement is not None
        and electricity_arrangement != "grid_only"
        and captive_incumbent_lcoe is not None
        and captive_incumbent_lcoe > 0
    )
    if use_captive:
        effective_incumbent_lcoe = captive_incumbent_lcoe
        if captive_fuel_type and captive_fuel_type.startswith("coal_"):
            effective_incumbent_kind = "captive_coal"
        elif captive_fuel_type == "natural_gas":
            effective_incumbent_kind = "captive_gas"
        elif captive_fuel_type == "hydro":
            effective_incumbent_kind = "captive_hydro"
        else:
            effective_incumbent_kind = "captive_other"
    else:
        effective_incumbent_lcoe = grid_cost
        effective_incumbent_kind = "grid"

    if pd.notna(lcoe_mid) and effective_incumbent_lcoe > 0:
        gap_pct = solar_competitive_gap(lcoe_mid, effective_incumbent_lcoe)
        attractive = is_solar_attractive(
            lcoe_mid,
            effective_incumbent_lcoe,
            pvout_best_50km=kek.get("pvout_best_50km"),
            pvout_threshold=thresholds.pvout_threshold,
        )
    else:
        gap_pct = np.nan
        attractive = False

    gap_vs_grid_pct = (
        solar_competitive_gap(lcoe_mid, grid_cost)
        if pd.notna(lcoe_mid) and grid_cost > 0
        else np.nan
    )

    gap_vs_tariff_pct = (
        solar_competitive_gap(lcoe_mid, tariff_rate)
        if pd.notna(lcoe_mid) and tariff_rate > 0
        else np.nan
    )
    gap_vs_bpp_pct = (
        solar_competitive_gap(lcoe_mid, bpp_rate)
        if pd.notna(lcoe_mid) and pd.notna(bpp_rate) and bpp_rate > 0
        else np.nan
    )

    # F2: Translate geothermal adjacency tier into Supply Blend cascade inputs.
    # Returns (0.0, None) when fct_geothermal_proximity hasn't been merged yet
    # OR when the site has no useful adjacency — both no-op the F1 layer.
    geothermal_tier_val = kek.get("geothermal_adjacency_tier")
    geothermal_tier_str = (
        str(geothermal_tier_val)
        if geothermal_tier_val is not None and pd.notna(geothermal_tier_val)
        else None
    )
    disp_re_coverage, disp_re_lcoe = dispatchable_re_from_geothermal_tier(geothermal_tier_str)

    return SiteContext(
        kek=kek,
        site_id=site_id,
        grid_region_id=grid_region_id,
        assumptions=assumptions,
        thresholds=thresholds,
        grid_cost=grid_cost,
        tariff_rate=tariff_rate,
        bpp_rate=bpp_rate,
        emission_factor=emission_factor,
        post2030_share=post2030_share,
        grid_upgrade_pre2030=grid_upgrade_pre2030,
        reliability_req=reliability_req,
        green_share=green_share,
        max_mwp=max_mwp,
        wind_cap=wind_cap,
        wind_cf_best=wind_cf_best,
        demand_mwh=demand_mwh,
        solar_gen_mwh=solar_gen_mwh,
        wind_gen_mwh=wind_gen_mwh,
        solar_data_valid=bool(solar_data_valid),
        gc_row=gc_row,
        wb_row=wb_row,
        wind_row=wind_row,
        lcoe_mid=lcoe_mid,
        primary_cf=primary_cf,
        gap_pct=gap_pct,
        attractive=attractive,
        gap_vs_tariff_pct=gap_vs_tariff_pct,
        gap_vs_bpp_pct=gap_vs_bpp_pct,
        electricity_arrangement=electricity_arrangement,
        captive_fuel_type=captive_fuel_type,
        captive_incumbent_lcoe=captive_incumbent_lcoe,
        captive_lcoe_tier=captive_lcoe_tier,
        captive_classification_confidence=captive_classification_confidence,
        effective_incumbent_lcoe=effective_incumbent_lcoe,
        effective_incumbent_kind=effective_incumbent_kind,
        gap_vs_grid_pct=gap_vs_grid_pct,
        grid_out=grid_out,
        dispatchable_re_coverage_pct=disp_re_coverage,
        dispatchable_re_lcoe_usd_mwh=disp_re_lcoe,
    )
