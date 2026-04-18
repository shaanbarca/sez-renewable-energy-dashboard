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
    max_mwp = _as_float(kek.get("max_captive_capacity_mwp"))
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
    solar_data_valid = pd.notna(kek.get("max_captive_capacity_mwp")) and pd.notna(
        kek.get("pvout_best_50km")
    )
    solar_gen_mwh = (
        float(kek.get("max_captive_capacity_mwp")) * float(kek.get("pvout_best_50km"))
        if solar_data_valid
        else 0.0
    )
    wind_gen_mwh = wind_cap * wind_cf_best * 8760 if wind_cap > 0 and wind_cf_best > 0 else 0.0

    # Primary LCOE: grid-connected first, fall back to within-boundary
    if gc_row is not None:
        lcoe_mid = gc_row["lcoe_mid_usd_mwh"]
        primary_cf = _as_float(gc_row.get("cf"))
    elif wb_row is not None:
        lcoe_mid = wb_row["lcoe_mid_usd_mwh"]
        primary_cf = _as_float(wb_row.get("cf"))
    else:
        lcoe_mid = np.nan
        primary_cf = 0.0

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

    grid_out = compute_grid_integration(kek=kek, gc_row=gc_row, assumptions=assumptions)

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
        grid_out=grid_out,
    )
