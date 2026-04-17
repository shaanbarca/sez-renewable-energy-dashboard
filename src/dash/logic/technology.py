# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""BESS sizing, firm coverage, and hybrid solar+wind optimization.

Three pure helpers extracted from `compute_scorecard_live`:

- `compute_bess_metrics` picks BESS sizing hours (user override > bridge-hours
  for high-reliability > cloud-firming 2h/4h) and returns storage adder + LCOE.
- `compute_firm_coverage` runs temporal-mismatch models for solar (day/night)
  and wind (CF-tiered intermittency).
- `compute_hybrid_metrics` sweeps solar_share 0-100% to pick the mix that
  minimizes all-in LCOE + reduced BESS adder.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.assumptions import (
    BESS_BRIDGE_HOURS_ENABLED,
    BESS_SIZING_HOURS,
    HYBRID_WIND_NIGHTTIME_FRACTION,
)
from src.dash.logic.assumptions import UserAssumptions, UserThresholds
from src.model.basic_model import (
    RESource,
    bess_bridge_hours,
    bess_storage_adder,
    carbon_breakeven_price,
    firm_solar_metrics,
    firm_wind_metrics,
    hybrid_lcoe_optimized,
)


def _nan_round(value: float, decimals: int = 2) -> float:
    if pd.isna(value):
        return np.nan
    return round(float(value), decimals)


def compute_bess_metrics(  # noqa: PLR0913 — pure helper; each arg is an independent site input
    lcoe_mid: float,
    primary_cf: float,
    reliability_req: float,
    dominant_process: str,
    assumptions: UserAssumptions,
    thresholds: UserThresholds,
    grid_cost: float,
) -> dict:
    """BESS sizing + storage adder + LCOE-with-BESS + grid competitiveness flag.

    Sizing precedence:
      1. `assumptions.bess_sizing_hours_override` (user slider)
      2. Bridge hours (14h for 24/7 loads) when reliability_req ≥ threshold
      3. RKEF smelter: 2× default (8h)
      4. Default 4h cloud-firming
    """
    if assumptions.bess_sizing_hours_override is not None:
        bess_sizing = assumptions.bess_sizing_hours_override
    else:
        is_rkef = dominant_process.strip().upper() == "RKEF"
        high_reliability = reliability_req >= thresholds.reliability_threshold
        if BESS_BRIDGE_HOURS_ENABLED and high_reliability:
            bess_sizing = bess_bridge_hours()
        elif is_rkef:
            bess_sizing = BESS_SIZING_HOURS * 2.0
        else:
            bess_sizing = BESS_SIZING_HOURS

    if primary_cf and primary_cf > 0:
        adder = round(
            bess_storage_adder(
                assumptions.bess_capex_usd_per_kwh,
                solar_cf=primary_cf,
                wacc=assumptions.wacc_decimal,
                sizing_hours=bess_sizing,
            ),
            2,
        )
        lcoe_with_bess = round(lcoe_mid + adder, 2) if pd.notna(lcoe_mid) else np.nan
    else:
        adder = 0.0
        lcoe_with_bess = _nan_round(lcoe_mid)

    competitive: bool | None
    if pd.notna(lcoe_with_bess) and grid_cost and grid_cost > 0:
        competitive = bool(lcoe_with_bess <= grid_cost)
    else:
        competitive = None

    return {
        "bess_sizing_hours": bess_sizing,
        "battery_adder_usd_mwh": adder,
        "lcoe_with_battery_usd_mwh": lcoe_with_bess,
        "bess_competitive": competitive,
    }


def compute_firm_coverage(
    solar_gen_mwh: float,
    wind_gen_mwh: float,
    demand_mwh: float,
    wind_cf_best: float,
) -> dict:
    """Temporal-mismatch metrics for solar (day/night) and wind (intermittency)."""
    solar = firm_solar_metrics(solar_gen_mwh, demand_mwh)
    wind = firm_wind_metrics(wind_gen_mwh, demand_mwh, wind_cf_best)
    return {
        "firm_solar_coverage_pct": solar["firm_solar_coverage_pct"],
        "nighttime_demand_mwh": solar["nighttime_demand_mwh"],
        "storage_required_mwh": solar["storage_required_mwh"],
        "storage_gap_pct": solar["storage_gap_pct"],
        "firm_wind_coverage_pct": wind["firm_wind_coverage_pct"],
        "wind_firming_gap_pct": wind["wind_firming_gap_pct"],
        "wind_firming_hours": wind["wind_firming_hours"],
    }


def compute_hybrid_metrics(  # noqa: PLR0913 — pure helper; kwarg-only for clarity
    *,
    solar_lcoe: float,
    wind_lcoe: float,
    solar_gen_mwh: float,
    wind_gen_mwh: float,
    primary_cf: float,
    wind_cf_best: float,
    solar_capacity_mwp: float,
    wind_capacity_mwp: float,
    demand_mwh: float,
    assumptions: UserAssumptions,
    grid_cost: float,
    emission_factor: float,
) -> dict:
    """Optimal solar+wind mix + reduced-BESS all-in LCOE + hybrid carbon breakeven."""
    solar_source = RESource(
        technology="solar",
        lcoe_usd_mwh=float(solar_lcoe) if pd.notna(solar_lcoe) else np.nan,
        generation_mwh=solar_gen_mwh,
        cf=primary_cf,
        nighttime_fraction=0.0,
        capacity_mwp=solar_capacity_mwp,
    )
    wind_source = RESource(
        technology="wind",
        lcoe_usd_mwh=float(wind_lcoe) if pd.notna(wind_lcoe) else np.nan,
        generation_mwh=wind_gen_mwh,
        cf=wind_cf_best,
        nighttime_fraction=HYBRID_WIND_NIGHTTIME_FRACTION,
        capacity_mwp=wind_capacity_mwp,
    )
    hybrid = hybrid_lcoe_optimized(
        sources=[solar_source, wind_source],
        demand_mwh=demand_mwh,
        bess_capex_usd_per_kwh=assumptions.bess_capex_usd_per_kwh,
        wacc=assumptions.wacc_decimal,
        solar_share_override=assumptions.hybrid_solar_share,
    )

    solar_bess = bess_bridge_hours()
    h_bess = hybrid["hybrid_bess_hours"]
    reduction_pct = (
        round((solar_bess - h_bess) / solar_bess * 100, 1) if h_bess is not None else None
    )

    h_allin = hybrid["hybrid_allin_usd_mwh"]
    carbon_breakeven = (
        carbon_breakeven_price(h_allin, grid_cost, emission_factor)
        if h_allin is not None and pd.notna(h_allin) and emission_factor > 0
        else None
    )

    return {
        "hybrid_lcoe_usd_mwh": hybrid["hybrid_lcoe_usd_mwh"],
        "hybrid_bess_hours": hybrid["hybrid_bess_hours"],
        "hybrid_bess_adder_usd_mwh": hybrid["hybrid_bess_adder_usd_mwh"],
        "hybrid_allin_usd_mwh": h_allin,
        "hybrid_solar_share": hybrid["optimal_solar_share"],
        "hybrid_supply_coverage_pct": hybrid["hybrid_supply_coverage_pct"],
        "hybrid_nighttime_coverage_pct": hybrid["hybrid_nighttime_coverage_pct"],
        "hybrid_bess_reduction_pct": reduction_pct,
        "hybrid_carbon_breakeven_usd_tco2": carbon_breakeven,
    }
