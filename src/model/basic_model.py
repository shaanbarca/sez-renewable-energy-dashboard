# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
KEK Power Competitiveness — core model functions.

All functions are pure Python / NumPy-free where possible. No Dash imports.
This module is the single source of truth for analytical logic; it is imported
identically by notebooks, pipeline scripts, tests, and the Dash app.

Methodology reference: METHODOLOGY_CONSOLIDATED.md
Data column definitions:  DATA_DICTIONARY.md

Units are explicit in every function signature and docstring. When in doubt, read
the unit comments — unit bugs (PVOUT daily vs annual, CAPEX MUSD/MWe vs USD/kW)
have historically produced ~10–100x errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import numpy as np
import pandas as pd

from src.assumptions import (
    BASE_WACC_DECIMAL,
    BESS_CAPEX_USD_PER_KWH,
    BESS_DISCHARGE_HOURS,
    BESS_FOM_USD_PER_KW_YR,
    BESS_LIFETIME_YR,
    BESS_ROUND_TRIP_EFFICIENCY,
    BESS_SIZING_HOURS,
    CAPEX_USD_PER_KW_MAX,
    CAPEX_USD_PER_KW_MIN,
    CONNECTION_COST_PER_KW_KM,
    CURTAILMENT_BROAD_GRID_BPP_THRESHOLD_USD_MWH,
    CURTAILMENT_BROAD_GRID_DEFAULT_PCT,
    CURTAILMENT_EXTREME_OVERSUPPLY_PCT,
    CURTAILMENT_HIGH_OVERSUPPLY_PCT,
    CURTAILMENT_LOW_OVERSUPPLY_PCT,
    CURTAILMENT_MID_OVERSUPPLY_PCT,
    CURTAILMENT_OVERSUPPLY_HIGH_RATIO,
    CURTAILMENT_OVERSUPPLY_LOW_RATIO,
    CURTAILMENT_OVERSUPPLY_MID_RATIO,
    FIRMING_ADDER_HIGH_USD_MWH,
    FIRMING_ADDER_LOW_USD_MWH,
    FIRMING_ADDER_MID_USD_MWH,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_DISTANCE_DECAY_FAR_KM,
    GEAS_DISTANCE_DECAY_FLOOR,
    GEAS_DISTANCE_DECAY_NEAR_KM,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    # V1 aliases — kept for backward compatibility
    GENTIE_COST_PER_KW_KM,
    GRID_CONNECTION_FIXED_PER_KW,
    HOURS_PER_YEAR,
    HYBRID_OPTIMIZATION_STEP,
    HYBRID_WIND_NIGHTTIME_FRACTION,
    KEK_TO_SUBSTATION_THRESHOLD_KM,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PVOUT_ANNUAL_MAX,
    PVOUT_ANNUAL_MIN,
    REGION_CF_DEFAULT,
    REGION_GEAS_MULT,
    REGION_GEAS_MULT_DEFAULT,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    RUPTL_PRE2030_END,
    SOLAR_DEGRADATION_ANNUAL_PCT,
    SOLAR_LIFECYCLE_EF_TCO2_PER_MWH,
    SOLAR_PRODUCTION_HOURS,
    SOLAR_TO_SUBSTATION_THRESHOLD_KM,
    SUBSTATION_MIN_CAPACITY_MVA,
    SUBSTATION_POWER_FACTOR,
    SUBSTATION_UPGRADE_COST_PER_KW,
    SUBSTATION_UTILIZATION_PCT,
    SUBSTATION_WORKS_PER_KW,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
    TRANSMISSION_LINE_COST_USD_PER_KM,
    WIND_CF_MAX,
    WIND_CF_MIN,
    WIND_LIFECYCLE_EF_TCO2_PER_MWH,
)

# ---------------------------------------------------------------------------
# 0. Data structures
# ---------------------------------------------------------------------------


@dataclass
class RESource:
    """One renewable energy source's contribution to a hybrid system.

    Extensibility point: hydro slots in with nighttime_fraction=1.0 (dispatchable).
    """

    technology: str  # "solar", "wind", "hydro"
    lcoe_usd_mwh: float  # standalone LCOE (no BESS)
    generation_mwh: float  # annual generation from available capacity
    cf: float  # capacity factor (0-1)
    nighttime_fraction: float  # fraction of generation during nighttime hours
    # solar=0.0 (all daytime), wind~=0.583 (uniform), hydro=1.0 (dispatchable)
    capacity_mwp: float = 0.0  # installed capacity


# ---------------------------------------------------------------------------
# 1. Resource helpers
# ---------------------------------------------------------------------------


def pvout_daily_to_annual(pvout_daily_kwh_per_kwp: float) -> float:
    """Convert PVOUT from kWh/kWp/day to kWh/kWp/year.

    The Global Solar Atlas GeoTIFF filename contains 'AvgDailyTotals', meaning
    the raster stores average daily values. The model requires annual totals.

    Parameters
    ----------
    pvout_daily_kwh_per_kwp:
        Daily PVOUT from the GeoTIFF (kWh/kWp/day).

    Returns
    -------
    float
        Annual PVOUT (kWh/kWp/year).

    Raises
    ------
    ValueError
        If the result falls outside plausibility bounds [1000, 2500] kWh/kWp/year.
    """
    annual = pvout_daily_kwh_per_kwp * 365.0
    if not (PVOUT_ANNUAL_MIN <= annual <= PVOUT_ANNUAL_MAX):
        raise ValueError(
            f"pvout_annual={annual:.1f} kWh/kWp/yr is outside plausible range "
            f"[{PVOUT_ANNUAL_MIN}, {PVOUT_ANNUAL_MAX}]. "
            "Check input units — GeoTIFF stores daily values."
        )
    return annual


def capacity_factor_from_pvout(pvout_kwh_per_kwp_yr: float) -> float:
    """Derive capacity factor from annual PVOUT.

    CF = PVOUT_annual / 8760

    Parameters
    ----------
    pvout_kwh_per_kwp_yr:
        Annual PVOUT (kWh/kWp/year). Must be an annual value, not daily.

    Returns
    -------
    float
        Capacity factor (0–1). Typical Indonesia solar: 0.17–0.21.
    """
    return float(pvout_kwh_per_kwp_yr) / HOURS_PER_YEAR


def estimate_curtailment_loss_pct(
    solar_generation_mwh: float,
    local_grid_demand_mwh: float,
    inter_substation_connected: bool,
    grid_region_bpp_usd_mwh: float,
) -> float:
    """Estimate the fraction of grid-connected solar generation that gets curtailed.

    Background (METHODOLOGY §9.5.2 — F8). §9.5's `firm_solar_coverage_pct` caps
    overproduction *physically* (limits dispatchable solar to daytime demand)
    but the curtailed energy still costs money to build. For grid-connected
    scenarios in low-demand regions (Maluku/Papua) where local grids can't
    absorb daytime surplus, that's a real $/MWh haircut. Within-boundary
    captive bypasses curtailment because the load is behind-the-meter — the
    captive offtaker takes whatever the panels make.

    Logic (matches v4.0 fixes spec §3.4):
      • Broad interconnected grid (inter-substation connected AND BPP <
        threshold, i.e. Java/Sumatera) → flat 5% baseline. Surplus finds a
        load somewhere in the system.
      • Local grid sized for the project (oversupply < 0.5×) → 5%.
      • Solar 50-100% of demand → 10%.
      • Solar 100-200% of demand → 20%.
      • Solar > 200% (small-island, large solar) → 35% (Maluku/Papua case).

    Parameters
    ----------
    solar_generation_mwh:
        Annual solar generation, MWh. Typically `cf × HOURS_PER_YEAR × MWp`.
    local_grid_demand_mwh:
        Annual demand on the local grid system the site connects into, MWh.
        Use the grid_region demand sum, not just the site's own demand.
    inter_substation_connected:
        From `fct_substation_proximity` — does the site's solar substation
        connect (geometrically or via PLN region) to the broader grid?
    grid_region_bpp_usd_mwh:
        Regional cost-of-supply ($/MWh) — used as a proxy for grid maturity.
        Low BPP (<$100/MWh) signals dense, high-utilization grid; high BPP
        signals diesel-dominant island grid with poor surplus absorption.

    Returns
    -------
    float
        Curtailment loss fraction in [0, 1]. Apply as
        `effective_cf = cf × (1 - curtailment_loss_pct)`.

    Sources
    -------
    - IEA SEA Outlook 2024 Figure 5.7 — regional curtailment under APS.
    - Bali Energy Vision case study — VRE flexibility.
    - Sumba MEG case study — small-island grid absorption limits.
    """
    if (
        inter_substation_connected
        and grid_region_bpp_usd_mwh < CURTAILMENT_BROAD_GRID_BPP_THRESHOLD_USD_MWH
    ):
        return CURTAILMENT_BROAD_GRID_DEFAULT_PCT

    oversupply_ratio = solar_generation_mwh / max(local_grid_demand_mwh, 1.0)
    if oversupply_ratio < CURTAILMENT_OVERSUPPLY_LOW_RATIO:
        return CURTAILMENT_LOW_OVERSUPPLY_PCT
    if oversupply_ratio < CURTAILMENT_OVERSUPPLY_MID_RATIO:
        return CURTAILMENT_MID_OVERSUPPLY_PCT
    if oversupply_ratio < CURTAILMENT_OVERSUPPLY_HIGH_RATIO:
        return CURTAILMENT_HIGH_OVERSUPPLY_PCT
    return CURTAILMENT_EXTREME_OVERSUPPLY_PCT


def geas_alloc_empirical(
    green_energy_regional_mwh: float,
    demand_kek_mwh: float,
    demand_total_region_mwh: float,
    distance_to_load_centre_km: float,
    region: str,
) -> float:
    """PLN-empirical GEAS allocation (METHODOLOGY §11.B — F13).

    The proportional baseline (`geas_baseline_allocation`) gives every site
    `green_energy × demand_share`. PLN's actual allocation is urban-anchored
    and slower-rural — Java industrial tenants get more than their pro-rata
    share, remote eastern KEKs get less. F13 surfaces both views so users
    can see what *should* happen vs what *likely will* happen.

    Formula:
        empirical = green_energy
                  × (demand_kek / demand_region)
                  × distance_decay
                  × region_multiplier

      • distance_decay: 1.0 within `GEAS_DISTANCE_DECAY_NEAR_KM` (100 km),
        linearly falling to `GEAS_DISTANCE_DECAY_FLOOR` (0.4) at
        `GEAS_DISTANCE_DECAY_FAR_KM` (500 km).
      • region_multiplier: from `REGION_GEAS_MULT` — 1.2 for JAVA_BALI down
        to 0.4 for MALUKU / PAPUA.

    Returns
    -------
    float
        Empirical GEAS allocation in MWh. May be lower than proportional for
        remote KEKs; ~equal for sites near load centres on Java.

    Sources
    -------
    - PLN 2024 generation-mix split by region (urban vs. rural pattern).
    - METHODOLOGY §11 footnote on substation density.
    """
    if demand_total_region_mwh <= 0:
        return 0.0
    proportional_share = demand_kek_mwh / demand_total_region_mwh

    # Distance decay: linear interpolation between NEAR and FAR distance
    # thresholds, floored at GEAS_DISTANCE_DECAY_FLOOR.
    excess_km = max(0.0, distance_to_load_centre_km - GEAS_DISTANCE_DECAY_NEAR_KM)
    span_km = GEAS_DISTANCE_DECAY_FAR_KM - GEAS_DISTANCE_DECAY_NEAR_KM
    decay_drop = (1.0 - GEAS_DISTANCE_DECAY_FLOOR) * min(1.0, excess_km / span_km)
    distance_decay = 1.0 - decay_drop

    region_mult = REGION_GEAS_MULT.get(region, REGION_GEAS_MULT_DEFAULT)
    return green_energy_regional_mwh * proportional_share * distance_decay * region_mult


def wind_speed_to_cf(speed_ms: float) -> float:
    """Convert mean annual wind speed at 100m hub height to onshore wind capacity factor.

    Empirical piecewise linear approximation calibrated to:
    - ESDM Technology Catalogue 2024, p.90 (IEC Class III onshore turbine):
      best Indonesian sites (>6 m/s) achieve CF ~27% incl. outages.
    - ESDM catalogue notes: majority of Indonesia has very low wind (CF <20%).
    - Reference turbine: Vestas V126/3.45 MW (Class III low-wind).

    Breakpoints (m/s → CF):
        ≤3.0  →  0.00   (below cut-in, no generation)
        4.0   →  0.08   (marginal, near cut-in)
        5.0   →  0.15   (low wind)
        6.0   →  0.22   (moderate, calibrated to ESDM lower range)
        7.5   →  0.27   (ESDM catalogue central CF for best Indonesian sites)
        8.5   →  0.32   (IEC Class II/III boundary)
        10.0  →  0.38   (IEC Class I, excellent)
        ≥12.0 →  0.42   (plateau — turbine at rated power most of the time)

    Parameters
    ----------
    speed_ms : float
        Mean annual wind speed at 100m hub height (m/s).

    Returns
    -------
    float
        Estimated capacity factor (0–1). Clamped to [WIND_CF_MIN, WIND_CF_MAX].

    Raises
    ------
    ValueError
        If speed_ms is negative.
    """
    if speed_ms < 0:
        raise ValueError(f"Wind speed must be >= 0, got {speed_ms}")

    # Piecewise linear breakpoints: (speed_ms, cf)
    breakpoints = [
        (3.0, 0.00),
        (4.0, 0.08),
        (5.0, 0.15),
        (6.0, 0.22),
        (7.5, 0.27),
        (8.5, 0.32),
        (10.0, 0.38),
        (12.0, 0.42),
    ]

    if speed_ms <= breakpoints[0][0]:
        return 0.0
    if speed_ms >= breakpoints[-1][0]:
        return min(breakpoints[-1][1], WIND_CF_MAX)

    # Linear interpolation between breakpoints
    for i in range(len(breakpoints) - 1):
        s0, cf0 = breakpoints[i]
        s1, cf1 = breakpoints[i + 1]
        if s0 <= speed_ms <= s1:
            t = (speed_ms - s0) / (s1 - s0)
            cf = cf0 + t * (cf1 - cf0)
            return max(WIND_CF_MIN, min(cf, WIND_CF_MAX))

    return 0.0


# ---------------------------------------------------------------------------
# 2. Economics — LCOE
# ---------------------------------------------------------------------------


def capital_recovery_factor(wacc: float, lifetime_yr: int) -> float:
    """Annuity factor (Capital Recovery Factor).

    CRF = wacc * (1+wacc)^n / ((1+wacc)^n - 1)

    Parameters
    ----------
    wacc : float
        Weighted average cost of capital (fraction, e.g. 0.09 for 9 %).
    lifetime_yr : int
        Asset lifetime in years.

    Returns
    -------
    float
        CRF (dimensionless annual fraction of total capital).

    Raises
    ------
    ValueError
        If wacc <= 0 or lifetime_yr <= 0.
    """
    if wacc <= 0:
        raise ValueError(f"wacc must be > 0, got {wacc}")
    if lifetime_yr <= 0:
        raise ValueError(f"lifetime_yr must be > 0, got {lifetime_yr}")
    factor = (1 + wacc) ** lifetime_yr
    return wacc * factor / (factor - 1)


def lcoe_solar(
    capex_usd_per_kw: float,
    fixed_om_usd_per_kw_yr: float,
    wacc: float,
    lifetime_yr: int,
    cf: float,
    degradation_annual_pct: float = SOLAR_DEGRADATION_ANNUAL_PCT,
) -> float:
    """Levelised Cost of Energy for utility-scale solar PV.

    LCOE = (CAPEX × CRF + FOM) / (CF × 8.76 × degradation_factor)

    where:
        8.76 = 8760 h/yr ÷ 1000 (converts kW-based costs to MWh)
        degradation_factor = 1 − (degradation_rate × lifetime / 2)

    The degradation factor uses a midpoint linear approximation of annual
    panel output loss (~0.5%/yr). Over 27yr: factor ≈ 0.9325.

    Parameters
    ----------
    capex_usd_per_kw:
        Overnight capital cost (USD/kW).
        If reading from fct_tech_parameter.csv (units: MUSD/MWe), multiply by 1000
        before passing here. See METHODOLOGY_CONSOLIDATED.md Section 3.2 for unit conversion.
    fixed_om_usd_per_kw_yr:
        Annual fixed O&M (USD/kW/year).
    wacc:
        Weighted average cost of capital (fraction, e.g. 0.09).
    lifetime_yr:
        Asset lifetime (years).
    cf:
        Capacity factor (0–1). Derive from pvout via capacity_factor_from_pvout().
    degradation_annual_pct:
        Annual panel output degradation (%, e.g. 0.5 for 0.5%/yr).
        Default from SOLAR_DEGRADATION_ANNUAL_PCT.

    Returns
    -------
    float
        LCOE in USD/MWh.

    Raises
    ------
    ValueError
        If capex is outside plausibility bounds, cf <= 0, or wacc/lifetime invalid.
    """
    if not (CAPEX_USD_PER_KW_MIN <= capex_usd_per_kw <= CAPEX_USD_PER_KW_MAX):
        raise ValueError(
            f"capex_usd_per_kw={capex_usd_per_kw} is outside plausibility bounds "
            f"[{CAPEX_USD_PER_KW_MIN}, {CAPEX_USD_PER_KW_MAX}]. "
            "Check units — fct_tech_parameter.csv stores MUSD/MWe; multiply by 1000."
        )
    if cf <= 0:
        raise ValueError(f"cf must be > 0, got {cf}")
    crf = capital_recovery_factor(wacc, lifetime_yr)
    annual_cost_per_kw = capex_usd_per_kw * crf + fixed_om_usd_per_kw_yr
    degradation_factor = 1.0 - (degradation_annual_pct / 100.0) * lifetime_yr / 2.0
    annual_mwh_per_kw = cf * HOURS_PER_YEAR / 1000.0 * degradation_factor
    return annual_cost_per_kw / annual_mwh_per_kw


def lcoe_solar_with_firming(
    capex_usd_per_kw: float,
    fixed_om_usd_per_kw_yr: float,
    wacc: float,
    lifetime_yr: int,
    cf: float,
    firming_adder: Literal["low", "mid", "high"] = "mid",
) -> float:
    """All-in captive solar cost: LCOE + firming/wheeling adder.

    Used for 'invest_battery' KEKs where reliability requirements mean
    LCOE alone understates the real investor cost. See METHODOLOGY_CONSOLIDATED.md Section 5.5.

    Parameters
    ----------
    firming_adder:
        'low' ($6/MWh), 'mid' ($11/MWh), or 'high' ($16/MWh).

    Returns
    -------
    float
        All-in cost in USD/MWh.
    """
    adder_map = {
        "low": FIRMING_ADDER_LOW_USD_MWH,
        "mid": FIRMING_ADDER_MID_USD_MWH,
        "high": FIRMING_ADDER_HIGH_USD_MWH,
    }
    base = lcoe_solar(capex_usd_per_kw, fixed_om_usd_per_kw_yr, wacc, lifetime_yr, cf)
    return base + adder_map[firming_adder]


def bess_bridge_hours(
    solar_production_hours: float = SOLAR_PRODUCTION_HOURS,
) -> float:
    """Hours of BESS needed to bridge overnight gap for 24/7 industrial loads.

    bridge_hours = 24 - solar_production_hours

    At equatorial Indonesian latitudes with ~10h effective solar production,
    the bridge is 14h. This is the physically grounded BESS sizing for
    high-reliability loads (MacKay Ch. 26).
    """
    return 24.0 - solar_production_hours


def hybrid_bess_hours(
    sources: list[RESource],
    total_demand_mwh: float,
    solar_production_hours: float = SOLAR_PRODUCTION_HOURS,
) -> float:
    """BESS hours needed in a hybrid multi-source system.

    Wind (and later hydro) partially fill solar's nighttime gap, reducing
    storage needs. Assumes each source's nighttime output is proportional
    to its nighttime_fraction (conservative uniform-CF assumption for wind).

    Returns hours of BESS needed (0 to bridge_hours range).
    """
    bridge = bess_bridge_hours(solar_production_hours)
    if total_demand_mwh <= 0:
        return bridge

    nighttime_demand = total_demand_mwh * (bridge / 24.0)
    if nighttime_demand <= 0:
        return 0.0

    # Sum nighttime generation across all sources
    nighttime_gen = sum(s.generation_mwh * s.nighttime_fraction for s in sources)
    coverage = min(nighttime_gen / nighttime_demand, 1.0)
    return bridge * (1.0 - coverage)


def hybrid_lcoe_optimized(
    sources: list[RESource],
    demand_mwh: float,
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH,
    wacc: float = BASE_WACC_DECIMAL,
    bess_lifetime_yr: int = BESS_LIFETIME_YR,
    bess_fom_usd_per_kw_yr: float = BESS_FOM_USD_PER_KW_YR,
    bess_discharge_hours: float = BESS_DISCHARGE_HOURS,
    round_trip_efficiency: float = BESS_ROUND_TRIP_EFFICIENCY,
    solar_share_override: float | None = None,
    optimization_step: float = HYBRID_OPTIMIZATION_STEP,
) -> dict[str, float | None]:
    """Optimize solar/wind mix to minimize all-in LCOE + BESS.

    Sweeps solar_share from 0% to 100% in `optimization_step` increments.
    For each candidate, computes blended LCOE + BESS adder at reduced sizing.
    Picks the share that minimizes all-in cost.

    Accepts list[RESource] for N-technology extensibility. Currently expects
    at most one solar and one wind source.

    Returns dict with hybrid_lcoe_usd_mwh, hybrid_bess_hours,
    hybrid_bess_adder_usd_mwh, hybrid_allin_usd_mwh, optimal_solar_share,
    hybrid_supply_coverage_pct, hybrid_nighttime_coverage_pct.
    """
    _none = {
        "hybrid_lcoe_usd_mwh": None,
        "hybrid_bess_hours": None,
        "hybrid_bess_adder_usd_mwh": None,
        "hybrid_allin_usd_mwh": None,
        "optimal_solar_share": None,
        "hybrid_supply_coverage_pct": None,
        "hybrid_nighttime_coverage_pct": None,
    }

    solar = next((s for s in sources if s.technology == "solar"), None)
    wind = next((s for s in sources if s.technology == "wind"), None)

    if solar is None or solar.generation_mwh <= 0 or np.isnan(solar.lcoe_usd_mwh):
        return _none
    if wind is None or wind.generation_mwh <= 0 or np.isnan(wind.lcoe_usd_mwh):
        # No wind: hybrid = solar-only
        bess_hrs = bess_bridge_hours()
        adder = bess_storage_adder(
            bess_capex_usd_per_kwh,
            solar.cf,
            wacc,
            bess_hrs,
            bess_lifetime_yr,
            bess_fom_usd_per_kw_yr,
            bess_discharge_hours,
            round_trip_efficiency,
        )
        return {
            "hybrid_lcoe_usd_mwh": round(solar.lcoe_usd_mwh, 2),
            "hybrid_bess_hours": round(bess_hrs, 1),
            "hybrid_bess_adder_usd_mwh": round(adder, 2),
            "hybrid_allin_usd_mwh": round(solar.lcoe_usd_mwh + adder, 2),
            "optimal_solar_share": 1.0,
            "hybrid_supply_coverage_pct": round(solar.generation_mwh / demand_mwh, 3)
            if demand_mwh > 0
            else None,
            "hybrid_nighttime_coverage_pct": 0.0,
        }

    # Build candidate shares
    if solar_share_override is not None:
        candidates = [solar_share_override]
    else:
        n_steps = int(round(1.0 / optimization_step)) + 1
        candidates = [i * optimization_step for i in range(n_steps)]

    best_allin = float("inf")
    best_result = _none

    for share in candidates:
        s_gen = solar.generation_mwh * share
        w_gen = wind.generation_mwh * (1.0 - share)
        total_gen = s_gen + w_gen
        if total_gen <= 0:
            continue

        # Blended LCOE weighted by generation
        blended_lcoe = (s_gen * solar.lcoe_usd_mwh + w_gen * wind.lcoe_usd_mwh) / total_gen

        # Blended CF for BESS denominator calculation
        blended_cf = solar.cf * share + wind.cf * (1.0 - share)
        if blended_cf <= 0:
            continue

        # Build scaled sources for BESS hours calculation
        scaled_sources = [
            RESource("solar", solar.lcoe_usd_mwh, s_gen, solar.cf, 0.0),
            RESource("wind", wind.lcoe_usd_mwh, w_gen, wind.cf, HYBRID_WIND_NIGHTTIME_FRACTION),
        ]
        h_bess = hybrid_bess_hours(scaled_sources, demand_mwh)

        # BESS adder at reduced hours, using blended CF
        if h_bess > 0 and blended_cf > 0:
            adder = bess_storage_adder(
                bess_capex_usd_per_kwh,
                blended_cf,
                wacc,
                h_bess,
                bess_lifetime_yr,
                bess_fom_usd_per_kw_yr,
                bess_discharge_hours,
                round_trip_efficiency,
            )
        else:
            adder = 0.0

        allin = blended_lcoe + adder
        if allin < best_allin:
            best_allin = allin
            # Nighttime coverage
            bridge = bess_bridge_hours()
            night_demand = demand_mwh * (bridge / 24.0) if demand_mwh > 0 else 0.0
            night_gen = w_gen * HYBRID_WIND_NIGHTTIME_FRACTION
            night_cov = min(night_gen / night_demand, 1.0) if night_demand > 0 else 0.0

            best_result = {
                "hybrid_lcoe_usd_mwh": round(blended_lcoe, 2),
                "hybrid_bess_hours": round(h_bess, 1),
                "hybrid_bess_adder_usd_mwh": round(adder, 2),
                "hybrid_allin_usd_mwh": round(allin, 2),
                "optimal_solar_share": round(share, 2),
                "hybrid_supply_coverage_pct": round(total_gen / demand_mwh, 3)
                if demand_mwh > 0
                else None,
                "hybrid_nighttime_coverage_pct": round(night_cov, 3),
            }

    # Floor: hybrid all-in should never exceed standalone wind (no BESS).
    # If the optimizer can't beat wind alone, report 100% wind with no storage.
    # Skip when user explicitly set a solar_share_override — respect their choice.
    if solar_share_override is None and wind.lcoe_usd_mwh < best_allin:
        bridge = bess_bridge_hours()
        night_demand = demand_mwh * (bridge / 24.0) if demand_mwh > 0 else 0.0
        night_gen = wind.generation_mwh * HYBRID_WIND_NIGHTTIME_FRACTION
        night_cov = min(night_gen / night_demand, 1.0) if night_demand > 0 else 0.0
        best_result = {
            "hybrid_lcoe_usd_mwh": round(wind.lcoe_usd_mwh, 2),
            "hybrid_bess_hours": 0.0,
            "hybrid_bess_adder_usd_mwh": 0.0,
            "hybrid_allin_usd_mwh": round(wind.lcoe_usd_mwh, 2),
            "optimal_solar_share": 0.0,
            "hybrid_supply_coverage_pct": round(wind.generation_mwh / demand_mwh, 3)
            if demand_mwh > 0
            else None,
            "hybrid_nighttime_coverage_pct": round(night_cov, 3),
        }

    return best_result


_BINDING_CONSTRAINT_THRESHOLD = 0.05
# Below this max shift in solar_share, the model reports "none_meaningful"
# rather than the technically-largest-but-trivial constraint.

_BINDING_CONSTRAINT_PERTURBATIONS: dict[str, tuple[float, float]] = {
    # multiplicative pct unless noted; (low, high) e.g. (-0.30, +0.30) = ±30%
    "bess_capex": (-0.30, 0.30),
    "solar_capex": (-0.15, 0.15),  # proxy: scale solar LCOE
    "wind_capex": (-0.15, 0.15),  # proxy: scale wind LCOE
    "wacc": (-0.02, 0.02),  # ABSOLUTE (e.g. 0.10 → 0.08 / 0.12)
    "storage_duration": (-0.25, 0.25),  # bess_discharge_hours multiplier
}


def _label_solar_wind_split(share: float) -> str:
    """Render an optimum like 0.65 as '65/35 solar/wind'."""
    s = round(share * 100)
    return f"{s}/{100 - s} solar/wind"


def _format_binding_narrative(
    binding: str,
    base_share: float,
    low_share: float,
    high_share: float,
    inputs: dict[str, float],
) -> str:
    """One-sentence binding-constraint narrative for the dashboard callout."""
    if binding == "none_meaningful":
        return (
            f"{_label_solar_wind_split(base_share)} optimum is robust — "
            f"no single perturbation flips it by more than 5 percentage points."
        )
    base_label = _label_solar_wind_split(base_share)
    low_label = _label_solar_wind_split(low_share)
    high_label = _label_solar_wind_split(high_share)
    bess_capex = inputs.get("bess_capex_usd_per_kwh")
    wacc = inputs.get("wacc")
    if binding == "bess_capex" and bess_capex is not None:
        return (
            f"{base_label} today; flips to {low_label} if BESS drops to "
            f"${round(bess_capex * 0.7)}/kWh or to {high_label} at ${round(bess_capex * 1.3)}/kWh."
        )
    if binding == "solar_capex":
        return (
            f"{base_label} today; flips to {high_label} on a 15% solar CAPEX cut "
            f"or {low_label} on a 15% increase."
        )
    if binding == "wind_capex":
        return (
            f"{base_label} today; flips to {low_label} on a 15% wind CAPEX cut "
            f"or {high_label} on a 15% increase."
        )
    if binding == "wacc" and wacc is not None:
        return (
            f"{base_label} today; flips to {low_label} at {round((wacc - 0.02) * 100)}% WACC "
            f"or {high_label} at {round((wacc + 0.02) * 100)}% WACC."
        )
    if binding == "storage_duration":
        return (
            f"{base_label} today; flips to {low_label} on 25% shorter BESS "
            f"or {high_label} on 25% longer."
        )
    return f"{base_label} today; binding constraint: {binding}."


def compute_hybrid_binding_constraint(  # noqa: PLR0913 — pure helper; one arg per perturbed input
    *,
    sources: list[RESource],
    demand_mwh: float,
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH,
    wacc: float = BASE_WACC_DECIMAL,
    bess_lifetime_yr: int = BESS_LIFETIME_YR,
    bess_fom_usd_per_kw_yr: float = BESS_FOM_USD_PER_KW_YR,
    bess_discharge_hours: float = BESS_DISCHARGE_HOURS,
    round_trip_efficiency: float = BESS_ROUND_TRIP_EFFICIENCY,
) -> dict[str, str | float | None]:
    """Per-site binding-constraint signal for the hybrid solar+wind optimum.

    Perturbs five inputs, re-runs `hybrid_lcoe_optimized` for each, and reports
    which parameter shifts the optimum solar/wind mix most. Surfaces the lever
    a developer or policy analyst should pull to flip the recommended mix.

    Returns:
        binding_constraint: enum (bess_capex / solar_capex / wind_capex / wacc /
            storage_duration / none_meaningful)
        narrative: one-sentence English description of the lever
        sensitivity: max |delta_solar_share| under the binding perturbation

    Returns None values when the base optimum is itself None (e.g. no solar).
    """
    base = hybrid_lcoe_optimized(
        sources=sources,
        demand_mwh=demand_mwh,
        bess_capex_usd_per_kwh=bess_capex_usd_per_kwh,
        wacc=wacc,
        bess_lifetime_yr=bess_lifetime_yr,
        bess_fom_usd_per_kw_yr=bess_fom_usd_per_kw_yr,
        bess_discharge_hours=bess_discharge_hours,
        round_trip_efficiency=round_trip_efficiency,
    )
    base_share = base.get("optimal_solar_share")
    if base_share is None:
        return {
            "hybrid_binding_constraint": None,
            "hybrid_binding_narrative": None,
            "hybrid_constraint_sensitivity": None,
        }

    solar = next((s for s in sources if s.technology == "solar"), None)
    wind = next((s for s in sources if s.technology == "wind"), None)

    def _run(
        *,
        bess_cx: float = bess_capex_usd_per_kwh,
        wacc_: float = wacc,
        sd_hours: float = bess_discharge_hours,
        scale_solar_lcoe: float = 1.0,
        scale_wind_lcoe: float = 1.0,
    ) -> float | None:
        srcs = []
        if solar is not None:
            srcs.append(
                RESource(
                    technology=solar.technology,
                    lcoe_usd_mwh=solar.lcoe_usd_mwh * scale_solar_lcoe,
                    generation_mwh=solar.generation_mwh,
                    cf=solar.cf,
                    nighttime_fraction=solar.nighttime_fraction,
                    capacity_mwp=solar.capacity_mwp,
                )
            )
        if wind is not None:
            srcs.append(
                RESource(
                    technology=wind.technology,
                    lcoe_usd_mwh=wind.lcoe_usd_mwh * scale_wind_lcoe,
                    generation_mwh=wind.generation_mwh,
                    cf=wind.cf,
                    nighttime_fraction=wind.nighttime_fraction,
                    capacity_mwp=wind.capacity_mwp,
                )
            )
        out = hybrid_lcoe_optimized(
            sources=srcs,
            demand_mwh=demand_mwh,
            bess_capex_usd_per_kwh=bess_cx,
            wacc=wacc_,
            bess_lifetime_yr=bess_lifetime_yr,
            bess_fom_usd_per_kw_yr=bess_fom_usd_per_kw_yr,
            bess_discharge_hours=sd_hours,
            round_trip_efficiency=round_trip_efficiency,
        )
        return out.get("optimal_solar_share")

    runs = {
        "bess_capex": (
            _run(
                bess_cx=bess_capex_usd_per_kwh
                * (1 + _BINDING_CONSTRAINT_PERTURBATIONS["bess_capex"][0])
            ),
            _run(
                bess_cx=bess_capex_usd_per_kwh
                * (1 + _BINDING_CONSTRAINT_PERTURBATIONS["bess_capex"][1])
            ),
        ),
        "solar_capex": (
            _run(scale_solar_lcoe=1 + _BINDING_CONSTRAINT_PERTURBATIONS["solar_capex"][0]),
            _run(scale_solar_lcoe=1 + _BINDING_CONSTRAINT_PERTURBATIONS["solar_capex"][1]),
        ),
        "wind_capex": (
            _run(scale_wind_lcoe=1 + _BINDING_CONSTRAINT_PERTURBATIONS["wind_capex"][0]),
            _run(scale_wind_lcoe=1 + _BINDING_CONSTRAINT_PERTURBATIONS["wind_capex"][1]),
        ),
        "wacc": (
            _run(wacc_=wacc + _BINDING_CONSTRAINT_PERTURBATIONS["wacc"][0]),
            _run(wacc_=wacc + _BINDING_CONSTRAINT_PERTURBATIONS["wacc"][1]),
        ),
        "storage_duration": (
            _run(
                sd_hours=bess_discharge_hours
                * (1 + _BINDING_CONSTRAINT_PERTURBATIONS["storage_duration"][0])
            ),
            _run(
                sd_hours=bess_discharge_hours
                * (1 + _BINDING_CONSTRAINT_PERTURBATIONS["storage_duration"][1])
            ),
        ),
    }

    deltas = {}
    low_high_shares: dict[str, tuple[float, float]] = {}
    for param, (low_share, high_share) in runs.items():
        if low_share is None or high_share is None:
            continue
        d_low = abs(low_share - base_share)
        d_high = abs(high_share - base_share)
        deltas[param] = max(d_low, d_high)
        low_high_shares[param] = (low_share, high_share)

    if not deltas:
        return {
            "hybrid_binding_constraint": "none_meaningful",
            "hybrid_binding_narrative": _format_binding_narrative(
                "none_meaningful", base_share, base_share, base_share, {}
            ),
            "hybrid_constraint_sensitivity": 0.0,
        }

    binding = max(deltas, key=deltas.get)
    sensitivity = deltas[binding]
    if sensitivity < _BINDING_CONSTRAINT_THRESHOLD:
        binding = "none_meaningful"
        narrative = _format_binding_narrative(
            "none_meaningful", base_share, base_share, base_share, {}
        )
    else:
        low_share, high_share = low_high_shares[binding]
        narrative = _format_binding_narrative(
            binding,
            base_share,
            low_share,
            high_share,
            {"bess_capex_usd_per_kwh": bess_capex_usd_per_kwh, "wacc": wacc},
        )

    return {
        "hybrid_binding_constraint": binding,
        "hybrid_binding_narrative": narrative,
        "hybrid_constraint_sensitivity": round(sensitivity, 3),
    }


def bess_storage_adder(
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH,
    solar_cf: float = 0.18,
    wacc: float = BASE_WACC_DECIMAL,
    sizing_hours: float = BESS_SIZING_HOURS,
    bess_lifetime_yr: int = BESS_LIFETIME_YR,
    bess_fom_usd_per_kw_yr: float = BESS_FOM_USD_PER_KW_YR,
    bess_discharge_hours: float = BESS_DISCHARGE_HOURS,
    round_trip_efficiency: float = BESS_ROUND_TRIP_EFFICIENCY,
) -> float:
    """Battery storage cost adder per MWh of solar generation (USD/MWh).

    Computes the incremental cost of adding battery storage to a solar plant,
    expressed per MWh of total solar generation. Uses battery-specific CRF
    (15yr lifetime) separate from the solar plant's 25yr lifetime.

    V3.3: Includes round-trip efficiency loss. Energy passing through storage
    loses (1 - RTE) per cycle. The denominator is reduced by the storage
    fraction × efficiency loss to reflect that less net energy is delivered.

    Parameters
    ----------
    bess_capex_usd_per_kwh:
        Installed battery cost per kWh of capacity (default $150).
    solar_cf:
        Solar capacity factor at the site (0-1).
    wacc:
        Weighted average cost of capital (decimal).
    sizing_hours:
        Hours of battery per kW of solar. Use bess_bridge_hours() for
        physically grounded sizing of 24/7 loads, or BESS_SIZING_HOURS
        for cloud-firming only.
    bess_lifetime_yr:
        Battery calendar lifetime (default 15 years).
    bess_fom_usd_per_kw_yr:
        Battery fixed O&M per kW of battery power capacity per year.
    bess_discharge_hours:
        Battery system discharge duration (for FOM pro-rating).
    round_trip_efficiency:
        AC-to-AC round-trip efficiency (0-1). Default 0.87.
        Energy loss = storage_fraction × (1 - RTE).

    Returns
    -------
    float
        USD/MWh adder to solar LCOE.
    """
    crf = capital_recovery_factor(wacc, bess_lifetime_yr)
    # BESS must be oversized by 1/RTE to deliver required energy after losses
    effective_sizing_hours = sizing_hours / round_trip_efficiency
    bess_capex_per_kw_solar = bess_capex_usd_per_kwh * effective_sizing_hours
    fom_adj = bess_fom_usd_per_kw_yr * (effective_sizing_hours / bess_discharge_hours)
    annual_cost_per_kw = bess_capex_per_kw_solar * crf + fom_adj
    # Denominator: net delivered solar MWh (reduced by RTE loss on stored fraction)
    nighttime_fraction = (24.0 - SOLAR_PRODUCTION_HOURS) / 24.0
    efficiency_loss = nighttime_fraction * (1.0 - round_trip_efficiency)
    effective_cf = solar_cf * (1.0 - efficiency_loss)
    annual_solar_mwh = effective_cf * HOURS_PER_YEAR / 1000
    return annual_cost_per_kw / annual_solar_mwh


def lcoe_solar_with_battery(
    capex_usd_per_kw: float,
    fixed_om_usd_per_kw_yr: float,
    wacc: float,
    lifetime_yr: int,
    cf: float,
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH,
) -> float:
    """Solar + battery storage bundled LCOE (USD/MWh).

    Adds the battery storage adder (2h firming) to the base solar LCOE.
    """
    base = lcoe_solar(capex_usd_per_kw, fixed_om_usd_per_kw_yr, wacc, lifetime_yr, cf)
    storage = bess_storage_adder(bess_capex_usd_per_kwh, solar_cf=cf, wacc=wacc)
    return base + storage


def firm_solar_metrics(
    solar_generation_mwh: float,
    demand_mwh: float,
    solar_production_hours: float = SOLAR_PRODUCTION_HOURS,
    round_trip_efficiency: float = BESS_ROUND_TRIP_EFFICIENCY,
) -> dict[str, float | None]:
    """Temporal-aware solar coverage metrics (MacKay balance sheet).

    Splits total annual solar supply coverage into daytime-direct and
    nighttime-requires-storage components. Provides the companion metrics
    that make solar_supply_coverage_pct physically honest.

    Parameters
    ----------
    solar_generation_mwh:
        Total annual solar generation (MWh/yr) from buildable area.
    demand_mwh:
        Total annual demand (MWh/yr) for the KEK.
    solar_production_hours:
        Effective hours/day of solar production (default 10h equatorial).
    round_trip_efficiency:
        BESS round-trip efficiency (default 0.87).

    Returns
    -------
    dict with keys:
        daytime_fraction: fraction of daily hours with solar (0.42 for 10h)
        nighttime_fraction: fraction of daily hours without solar (0.58 for 14h)
        daytime_demand_mwh: annual demand during solar hours
        nighttime_demand_mwh: annual demand during non-solar hours
        firm_solar_coverage_pct: solar generation / daytime demand only
        storage_required_mwh: MWh of storage throughput needed per year
            (nighttime demand / RTE, accounts for round-trip losses)
        storage_gap_pct: fraction of total demand that requires storage to serve
    """
    if demand_mwh <= 0 or solar_generation_mwh <= 0:
        return {
            "daytime_fraction": None,
            "nighttime_fraction": None,
            "daytime_demand_mwh": None,
            "nighttime_demand_mwh": None,
            "firm_solar_coverage_pct": None,
            "storage_required_mwh": None,
            "storage_gap_pct": None,
        }

    daytime_frac = solar_production_hours / 24.0
    nighttime_frac = 1.0 - daytime_frac

    # Assume flat industrial demand profile (24/7 loads)
    daytime_demand = demand_mwh * daytime_frac
    nighttime_demand = demand_mwh * nighttime_frac

    # Firm coverage: solar can directly serve daytime demand without storage
    firm_coverage = solar_generation_mwh / daytime_demand if daytime_demand > 0 else 0.0

    # Storage needed: nighttime demand must pass through BESS, losing (1-RTE)
    storage_throughput = nighttime_demand / round_trip_efficiency

    # What fraction of total demand needs storage to be served?
    storage_gap = nighttime_frac  # 58% for 14h night / 24h

    return {
        "daytime_fraction": round(daytime_frac, 3),
        "nighttime_fraction": round(nighttime_frac, 3),
        "daytime_demand_mwh": round(daytime_demand, 1),
        "nighttime_demand_mwh": round(nighttime_demand, 1),
        "firm_solar_coverage_pct": round(firm_coverage, 3),
        "storage_required_mwh": round(storage_throughput, 1),
        "storage_gap_pct": round(storage_gap, 3),
    }


def firm_wind_metrics(
    wind_generation_mwh: float,
    demand_mwh: float,
    wind_cf: float,
) -> dict[str, float | None]:
    """Wind temporal coverage analysis.

    Unlike solar (10h production / 14h gap), wind produces ~24/7 at variable output.
    The gap is intermittency (output variability), not a day/night split.

    Typical onshore wind: 70-80% of hours produce above 25% of rated capacity.
    The firming requirement is shorter-duration (2-4h gaps vs solar's 14h overnight).

    Parameters
    ----------
    wind_generation_mwh:
        Total annual wind generation (MWh/yr) from buildable area.
    demand_mwh:
        Total annual demand (MWh/yr) for the KEK.
    wind_cf:
        Wind capacity factor (0-1).

    Returns
    -------
    dict with keys:
        firm_wind_coverage_pct: wind generation / demand (raw supply ratio)
        wind_firming_gap_pct: fraction of demand needing firming for intermittency
        wind_firming_hours: typical gap duration (hours) between production lulls
    """
    if demand_mwh <= 0 or wind_generation_mwh <= 0 or wind_cf <= 0:
        return {
            "firm_wind_coverage_pct": None,
            "wind_firming_gap_pct": None,
            "wind_firming_hours": None,
        }

    # Raw coverage ratio
    raw_coverage = wind_generation_mwh / demand_mwh

    # Wind intermittency model: at CF < 0.30, ~35% of hours have near-zero output.
    # At CF 0.30-0.40, ~20% of hours are near-zero. Higher CF = less intermittency.
    if wind_cf >= 0.35:
        intermittency_gap = 0.15  # 15% of hours need firming
        gap_hours = 2.0
    elif wind_cf >= 0.25:
        intermittency_gap = 0.25  # 25% of hours need firming
        gap_hours = 3.0
    else:
        intermittency_gap = 0.35  # 35% of hours need firming
        gap_hours = 4.0

    return {
        "firm_wind_coverage_pct": round(raw_coverage, 3),
        "wind_firming_gap_pct": round(intermittency_gap, 3),
        "wind_firming_hours": gap_hours,
    }


def grid_connection_cost_per_kw(
    dist_km: float,
    cost_per_kw_km: float = CONNECTION_COST_PER_KW_KM,
    connection_fixed_per_kw: float = GRID_CONNECTION_FIXED_PER_KW,
) -> float:
    """Capital cost of grid connection line + switchgear for grid-connected solar.

    V2: replaces gentie_cost_per_kw(). Solar farm connects to nearest PLN
    substation via short MV/HV line. No private gen-tie to KEK.

    connection_capex [USD/kW] = dist_km × cost_per_kw_km + connection_fixed_per_kw

    Parameters
    ----------
    dist_km:
        Distance from solar farm to nearest PLN substation (km). Use
        dist_solar_to_nearest_substation_km from fct_substation_proximity.csv.
    cost_per_kw_km:
        Connection line cost (USD/kW-km). Default $5/kW-km, range $2–15.
        See METHODOLOGY_V2.md §3.
    connection_fixed_per_kw:
        Fixed connection cost — step-up transformer, switchgear, protection,
        metering at solar farm end (USD/kW). Default $80/kW, range $30–200.

    Returns
    -------
    float
        One-time grid connection capital cost per kW of solar capacity (USD/kW).
        Pass 0 for within-boundary solar (no connection needed).
    """
    if dist_km < 0:
        raise ValueError(f"dist_km must be >= 0, got {dist_km}")
    return dist_km * cost_per_kw_km + connection_fixed_per_kw


# V1 alias — kept for backward compatibility until all consumers migrated.
def gentie_cost_per_kw(
    dist_km: float,
    cost_per_kw_km: float = GENTIE_COST_PER_KW_KM,
    substation_works_per_kw: float = SUBSTATION_WORKS_PER_KW,
) -> float:
    """Deprecated V1 alias for grid_connection_cost_per_kw()."""
    return grid_connection_cost_per_kw(dist_km, cost_per_kw_km, substation_works_per_kw)


def new_transmission_cost_per_kw(
    inter_substation_dist_km: float,
    solar_capacity_mwp: float,
    cost_per_km: float = TRANSMISSION_LINE_COST_USD_PER_KM,
) -> float:
    """Capital cost per kW of building a new transmission line between two substations.

    V3.1: When the solar site's nearest substation (B_solar) differs from the KEK's
    nearest substation (B_kek) and no existing line connects them, this cost is
    added to effective CAPEX for grid-connected LCOE.

    Parameters
    ----------
    inter_substation_dist_km:
        Haversine distance between B_solar and B_kek (km).
    solar_capacity_mwp:
        Proposed solar farm capacity (MWp). Must be > 0.
    cost_per_km:
        Transmission line construction cost (USD/km). Default $1.25M/km.
        Range: $0.6–1.9M/km depending on voltage, terrain, permitting.

    Returns
    -------
    float
        Transmission line cost per kW of solar capacity (USD/kW).
        Returns 0 if distance is 0 (same substation) or capacity is 0.
    """
    if inter_substation_dist_km <= 0 or solar_capacity_mwp <= 0:
        return 0.0
    total_cost = inter_substation_dist_km * cost_per_km
    return total_cost / (solar_capacity_mwp * 1_000)  # MWp → kW


def lcoe_solar_grid_connected(
    capex_usd_per_kw: float,
    fixed_om_usd_per_kw_yr: float,
    wacc: float,
    lifetime_yr: int,
    cf: float,
    dist_km: float,
    cost_per_kw_km: float = CONNECTION_COST_PER_KW_KM,
    connection_fixed_per_kw: float = GRID_CONNECTION_FIXED_PER_KW,
) -> float:
    """LCOE for grid-connected solar including connection cost to nearest substation.

    V2: replaces lcoe_solar_remote_captive(). Connection cost is for a short
    MV/HV line from solar farm to nearest PLN substation (typically <10km),
    not a private 50km gen-tie.

    effective_capex = capex + grid_connection_cost_per_kw(dist_km, ...)
    LCOE = lcoe_solar(effective_capex, ...)

    Parameters
    ----------
    capex_usd_per_kw:
        Solar plant overnight CAPEX only (USD/kW) — not including connection.
    dist_km:
        Distance from solar farm to nearest PLN substation (km).
    cost_per_kw_km, connection_fixed_per_kw:
        Connection cost parameters — see grid_connection_cost_per_kw().

    Returns
    -------
    float
        All-in LCOE including grid connection cost (USD/MWh).
    """
    conn = grid_connection_cost_per_kw(dist_km, cost_per_kw_km, connection_fixed_per_kw)
    effective_capex = capex_usd_per_kw + conn
    return lcoe_solar(effective_capex, fixed_om_usd_per_kw_yr, wacc, lifetime_yr, cf)


# V1 alias — kept for backward compatibility until all consumers migrated.
def lcoe_solar_remote_captive(
    capex_usd_per_kw: float,
    fixed_om_usd_per_kw_yr: float,
    wacc: float,
    lifetime_yr: int,
    cf: float,
    dist_km: float,
    cost_per_kw_km: float = GENTIE_COST_PER_KW_KM,
    substation_works_per_kw: float = SUBSTATION_WORKS_PER_KW,
) -> float:
    """Deprecated V1 alias for lcoe_solar_grid_connected()."""
    return lcoe_solar_grid_connected(
        capex_usd_per_kw,
        fixed_om_usd_per_kw_yr,
        wacc,
        lifetime_yr,
        cf,
        dist_km,
        cost_per_kw_km,
        substation_works_per_kw,
    )


# ---------------------------------------------------------------------------
# 3. Competitiveness metrics
# ---------------------------------------------------------------------------


def solar_competitive_gap(lcoe_mid: float, grid_cost_usd_mwh: float) -> float:
    """Fractional gap between solar LCOE and grid reference cost.

    gap = (lcoe_mid - grid_cost) / grid_cost * 100

    Negative values mean solar is cheaper than the grid (competitive).
    Positive values mean solar is more expensive.

    Parameters
    ----------
    lcoe_mid:
        Solar LCOE at mid WACC (USD/MWh).
    grid_cost_usd_mwh:
        Grid reference cost — use I-4 industrial tariff (USD/MWh).
        See METHODOLOGY_CONSOLIDATED.md Section 4 and DATA_DICTIONARY.md for BPP vs tariff guidance.

    Returns
    -------
    float
        Percentage gap. Negative = solar competitive.
    """
    if grid_cost_usd_mwh <= 0:
        raise ValueError(f"grid_cost_usd_mwh must be > 0, got {grid_cost_usd_mwh}")
    return (lcoe_mid - grid_cost_usd_mwh) / grid_cost_usd_mwh * 100.0


def is_solar_attractive(
    lcoe_usd_mwh: float,
    grid_cost_usd_mwh: float,
    pvout_best_50km: float | None = None,
    pvout_threshold: float = 1350.0,
) -> bool:
    """Return True if solar economics AND resource both meet the attractiveness bar.

    Conditions (METHODOLOGY_CONSOLIDATED.md Section 5.2, Option B):
        1. lcoe_mid ≤ grid_cost  — economics are competitive at current WACC
        2. pvout_best_50km ≥ pvout_threshold  — resource is sufficient (≥1,350 kWh/kWp/yr)

    Condition 2 is skipped if pvout_best_50km is None (keeps the function usable
    in notebook contexts where only LCOE is available).

    Parameters
    ----------
    lcoe_usd_mwh:
        Solar LCOE (USD/MWh).
    grid_cost_usd_mwh:
        Grid reference cost (USD/MWh). Use I-4 tariff; BPP as provisional fallback.
    pvout_best_50km:
        Annual PVOUT within 50km radius (kWh/kWp/yr). If None, resource check is skipped.
    pvout_threshold:
        Minimum PVOUT for the resource to be considered sufficient (default 1,350 kWh/kWp/yr).
    """
    lcoe_ok = lcoe_usd_mwh <= grid_cost_usd_mwh
    if pvout_best_50km is None:
        return lcoe_ok
    return lcoe_ok and pvout_best_50km >= pvout_threshold


# ---------------------------------------------------------------------------
# 4. Action flags
# ---------------------------------------------------------------------------


class ActionFlag(StrEnum):
    """Recommended action for a KEK based on solar economics and grid readiness."""

    SOLAR_NOW = "solar_now"
    CBAM_URGENT = "cbam_urgent"  # CBAM savings flip RE economics — switch now
    INVEST_TRANSMISSION = (
        "invest_transmission"  # solar near substation; KEK far — build transmission
    )
    INVEST_SUBSTATION = (
        "invest_substation"  # KEK near substation; solar far — build substation near solar
    )
    INVEST_BATTERY = "invest_battery"  # high reliability req — add battery storage
    INVEST_RESILIENCE = "invest_resilience"
    GRID_FIRST = "grid_first"
    PLAN_LATE = "plan_late"
    NOT_COMPETITIVE = "not_competitive"
    NO_SOLAR_RESOURCE = "no_solar_resource"  # buildable area = 0, no land for solar


class EconomicTier(StrEnum):
    """Economic competitiveness tier for RE investment at a KEK.

    Two-dimensional classification (Option C): this axis captures
    *how viable* RE is, independent of infrastructure readiness.
    """

    FULL_RE = "full_re"  # RE + storage beats grid 24/7
    PARTIAL_RE = "partial_re"  # daytime RE beats grid, storage too expensive
    NEAR_PARITY = "near_parity"  # RE LCOE within 20% of grid
    NOT_COMPETITIVE = "not_competitive"  # RE LCOE > 20% above grid
    NO_RESOURCE = "no_resource"  # no buildable area or insufficient resource


class CostBasis(StrEnum):
    """Which layer of the cost stack feeds action_flag / economic_tier / gap / carbon_breakeven.

    User-selectable toggle (TAXONOMY §6.5, §7.3). Parallel to EnergyMode and
    BenchmarkMode on the frontend. Resolution matrix:

        | EnergyMode | raw (T1)                   | firmed (T2)                    | delivered (T3)              | firmed_24_7_solar_only      |
        | solar      | lcoe_mid_usd_mwh           | lcoe_with_battery_usd_mwh      | delivered_cost_usd_mwh      | lcoe_with_battery_usd_mwh   |
        | wind       | lcoe_wind_mid_usd_mwh      | lcoe_wind_allin_mid_usd_mwh    | (empty)                     | (empty — solar-only basis)  |
        | hybrid     | hybrid_lcoe_usd_mwh        | hybrid_allin_usd_mwh           | (empty)                     | (empty — solar-only basis)  |
        | overall    | (empty)                    | best_re_lcoe_mid_usd_mwh       | (empty)                     | lcoe_with_battery_usd_mwh   |

    Empty cells → toggle option disabled on the UI. Default CostBasis:
    firmed for overall, raw otherwise.

    FIRMED_24_7_SOLAR_ONLY (F1, 2026-05-07): explicit "scenario 3 sanity-check"
    basis that forces the comparator to be solar+12h-battery LCOE regardless of
    energy mode. This is the wiki's six-scenario sanity-check baseline (~3× the
    cost of captive coal for 24/7 industrial loads), surfaced as a deliberate
    user toggle rather than a default. The default `firmed` basis routes to the
    HYBRID firmed cost (solar + wind + storage at the optimal mix) for `overall`
    mode, which is the recommended cost-min path. `firmed_24_7_solar_only` is
    the "what if I really did pure solar + 12h battery?" view — useful for
    showing why a hybrid mix wins on cost, not as a recommendation.
    """

    RAW = "raw"  # T1: generation LCOE, no firming
    FIRMED = "firmed"  # T2: + BESS / storage adder (hybrid mix at optimum for overall mode)
    DELIVERED = "delivered"  # T3: captive + grid-import blend (tenant view)
    FIRMED_24_7_SOLAR_ONLY = "firmed_24_7_solar_only"  # F1: scenario-3 sanity-check baseline


def economic_tier(
    lcoe_re: float | None,
    allin_24_7: float | None,
    grid_cost: float,
    has_resource: bool,
    near_parity_threshold_pct: float = 20.0,
) -> EconomicTier:
    """Classify a KEK into an economic competitiveness tier.

    Args:
        lcoe_re: Best bare RE LCOE (solar, wind, or hybrid) in USD/MWh.
        allin_24_7: Best all-in cost including storage for 24/7 coverage.
        grid_cost: Grid electricity cost (BPP or tariff) in USD/MWh.
        has_resource: Whether buildable RE land exists (solar or wind).
        near_parity_threshold_pct: Max gap % for near-parity (default 20).
    """
    if not has_resource:
        return EconomicTier.NO_RESOURCE
    if lcoe_re is None or grid_cost <= 0:
        return EconomicTier.NOT_COMPETITIVE
    if allin_24_7 is not None and allin_24_7 <= grid_cost:
        return EconomicTier.FULL_RE
    if lcoe_re <= grid_cost:
        return EconomicTier.PARTIAL_RE
    gap_pct = (lcoe_re - grid_cost) / grid_cost * 100
    if gap_pct <= near_parity_threshold_pct:
        return EconomicTier.NEAR_PARITY
    return EconomicTier.NOT_COMPETITIVE


def action_flags(
    solar_attractive: bool,
    grid_upgrade_pre2030: bool,
    reliability_req: float,
    green_share_geas: float,
    post2030_share: float,
    grid_integration_cat: str | None = None,
) -> dict[str, bool]:
    """Compute action flags for a single KEK.

    Flag logic (see METHODOLOGY_CONSOLIDATED.md Section 5.2):
    - solar_now:            solar attractive AND grid ready AND sufficient GEAS allocation
    - invest_transmission:  solar near substation but KEK far — build transmission to KEK
    - invest_substation:    KEK near substation but solar far — build substation near solar
    - invest_battery:       solar attractive AND KEK reliability requirement >= 0.75
    - grid_first:           solar attractive AND grid upgrade NOT yet pre-2030
    - plan_late:            >= 60% of RUPTL solar additions slip to post-2030

    Parameters
    ----------
    solar_attractive:
        Output of is_solar_attractive().
    grid_upgrade_pre2030:
        True if the grid region's earliest upgrade year is <= 2030.
    reliability_req:
        KEK reliability requirement (0–1 scale; industrial = 0.8+).
    green_share_geas:
        Share of 2030 demand covered by GEAS-allocated solar (0–1).
    post2030_share:
        Share of RUPTL-planned solar additions scheduled after 2030 (0–1).
    grid_integration_cat:
        Grid integration category from grid_integration_category(). One of
        'within_boundary', 'grid_ready', 'invest_transmission',
        'invest_substation', 'grid_first', or None.

    Returns
    -------
    dict with keys: solar_now, invest_transmission, invest_substation,
    invest_battery, grid_first, plan_late
    """
    plan_late = post2030_share >= PLAN_LATE_POST2030_SHARE_THRESHOLD
    grid_first = (
        solar_attractive
        and not grid_upgrade_pre2030
        and grid_integration_cat
        not in (
            "invest_transmission",
            "invest_substation",
            "grid_ready",
            "within_boundary",
        )
    )
    invest_battery = solar_attractive and reliability_req >= FIRMING_RELIABILITY_REQ_THRESHOLD
    invest_transmission = solar_attractive and grid_integration_cat == "invest_transmission"
    invest_substation = solar_attractive and grid_integration_cat == "invest_substation"

    solar_now = (
        solar_attractive
        and not grid_first
        and not invest_transmission
        and not invest_substation
        and green_share_geas >= GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD
    )
    return {
        "solar_now": solar_now,
        "invest_transmission": invest_transmission,
        "invest_substation": invest_substation,
        "invest_battery": invest_battery,
        "grid_first": grid_first,
        "plan_late": plan_late,
    }


# ---------------------------------------------------------------------------
# 5. Resilience flag + carbon breakeven
# ---------------------------------------------------------------------------


def invest_resilience(
    solar_competitive_gap_pct: float,
    reliability_req: float,
    gap_threshold_pct: float = RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    reliability_threshold: float = FIRMING_RELIABILITY_REQ_THRESHOLD,
) -> bool:
    """Return True if solar merits investment on resilience grounds despite being above grid parity.

    A KEK qualifies when:
      1. LCOE > grid cost (gap > 0) — cost-parity not yet reached
      2. LCOE is within gap_threshold_pct of grid cost — not far off
      3. The KEK has high reliability requirements — downtime avoidance justifies the premium

    Parameters
    ----------
    solar_competitive_gap_pct:
        (lcoe_mid - grid_cost) / grid_cost × 100. Positive = solar more expensive.
    reliability_req:
        KEK reliability requirement (0–1 scale; manufacturing = 0.8+).
    gap_threshold_pct:
        Upper bound of the resilience zone (default 20%).
    reliability_threshold:
        Minimum reliability requirement to qualify (default 0.75).
    """
    return (
        solar_competitive_gap_pct > 0
        and solar_competitive_gap_pct <= gap_threshold_pct
        and reliability_req >= reliability_threshold
    )


def carbon_breakeven_price(
    lcoe_mid_usd_mwh: float,
    grid_cost_usd_mwh: float,
    grid_emission_factor_t_co2_mwh: float,
    technology: str = "solar",
) -> float | None:
    """Return the carbon price (USD/tCO2) at which the renewable becomes cost-competitive.

    Interpretation: if Indonesia (or a buyer) prices carbon at or above this level,
    renewable LCOE + carbon cost of grid electricity cross — renewable wins.

    F4 (2026-05-07): now subtracts the renewable's lifecycle emission factor from
    the grid EF before dividing. Previous version treated solar/wind as zero
    lifecycle emissions, biasing breakeven prices 5-8% optimistic. The IPCC AR6
    median lifecycle EFs (0.040 tCO2/MWh solar, 0.013 wind) are baked into the
    denominator. METHODOLOGY §9.2.

    Returns 0.0 if renewable is already competitive (LCOE ≤ grid cost).
    Returns None if grid EF is missing or zero (cannot compute).

    Parameters
    ----------
    lcoe_mid_usd_mwh:
        Renewable LCOE mid estimate (USD/MWh).
    grid_cost_usd_mwh:
        Grid reference cost (USD/MWh).
    grid_emission_factor_t_co2_mwh:
        Grid emission intensity (tCO2/MWh). Use GRID_EMISSION_FACTOR_T_CO2_MWH[region].
    technology:
        F4: "solar" (default), "wind", or "hybrid". "hybrid" uses solar's EF as a
        conservative approximation since solar typically dominates the mix.
    """
    if grid_emission_factor_t_co2_mwh <= 0:
        return None
    lcoe_gap = lcoe_mid_usd_mwh - grid_cost_usd_mwh
    if lcoe_gap <= 0:
        return 0.0
    # F4: subtract lifecycle EF; floor at 1e-3 to avoid divide-by-zero when grid
    # EF is near-zero (a future hypothetical, not today's Indonesian grid).
    lifecycle_ef = (
        WIND_LIFECYCLE_EF_TCO2_PER_MWH if technology == "wind" else SOLAR_LIFECYCLE_EF_TCO2_PER_MWH
    )
    delta_ef = max(grid_emission_factor_t_co2_mwh - lifecycle_ef, 1e-3)
    return round(lcoe_gap / delta_ef, 1)


# ---------------------------------------------------------------------------
# 5b. Grid integration category (V2: three-point proximity)
# ---------------------------------------------------------------------------


def grid_integration_category(
    has_internal_substation: bool,
    dist_solar_to_substation_km: float | None,
    dist_kek_to_substation_km: float,
    substation_capacity_mva: float | None = None,
    solar_to_sub_threshold_km: float = SOLAR_TO_SUBSTATION_THRESHOLD_KM,
    kek_to_sub_threshold_km: float = KEK_TO_SUBSTATION_THRESHOLD_KM,
    min_capacity_mva: float = SUBSTATION_MIN_CAPACITY_MVA,
    substation_utilization_pct: float = SUBSTATION_UTILIZATION_PCT,
    solar_capacity_mwp: float | None = None,
    inter_substation_connected: bool | None = None,
    within_boundary_coverage_pct: float | None = None,
    meaningful_share_pct: float = 1.0,
    site_type: str | None = None,
) -> str:
    """Classify a KEK's grid integration readiness using three-point proximity.

    Three points: (A) best buildable solar site, (B) nearest PLN substation, (C) KEK centroid.

    Categories (METHODOLOGY_CONSOLIDATED.md §2):
        within_boundary      — substation inside KEK polygon OR within-boundary solar
                               covers >= 100% of demand (behind-the-meter, no grid needed)
        grid_ready           — substation near both solar AND KEK (short connection feasible)
        invest_transmission  — solar near substation, KEK far — build transmission to KEK
        invest_substation    — KEK near substation, solar far — build substation near solar
        grid_first           — no substations near either; major grid investment needed

    Parameters
    ----------
    has_internal_substation:
        True if any operational PLN substation is inside the KEK boundary.
    dist_solar_to_substation_km:
        Distance from best buildable solar site to nearest substation (km).
        None if solar site coordinates are unavailable.
    dist_kek_to_substation_km:
        Distance from KEK centroid to nearest substation (km).
    substation_capacity_mva:
        Rated capacity of nearest substation (MVA). None if unknown.
        If below min_capacity_mva, treated as if substation is not near
        (grid reinforcement needed).
    solar_to_sub_threshold_km:
        Max distance for solar-to-substation to be "near" (default 5 km).
    kek_to_sub_threshold_km:
        Max distance for KEK-to-substation to be "well-connected" (default 15 km).
    min_capacity_mva:
        Min substation capacity to absorb solar generation (default 30 MVA).
    substation_utilization_pct:
        Assumed fraction of substation capacity already in use (0–1). Default 0.65.
        Used with solar_capacity_mwp to check if available capacity is sufficient.
    solar_capacity_mwp:
        Proposed solar farm capacity (MWp). If provided with substation_capacity_mva,
        triggers capacity sufficiency check: available = rated × (1 − utilization).
    inter_substation_connected:
        V3.1: Whether B_solar and B_kek are connected by an existing transmission line.
        True = line exists (checked geometrically or via same PLN region).
        False = no line found, new transmission build needed.
        None = unknown / same substation / not checked (falls back to distance logic).
    within_boundary_coverage_pct:
        V3.2: Fraction of KEK demand coverable by within-boundary solar (0.0–N).
        If >= `meaningful_share_pct` and site_type == "kek", the KEK is treated as
        self-sufficient with on-site solar and classifies as 'within_boundary'
        regardless of substation distances.
    meaningful_share_pct:
        V3.9: Threshold (0.0–1.0) for declaring a KEK self-sufficient via
        within-boundary solar. Defaults to 1.0 (full self-supply) to preserve
        legacy behaviour when callers don't pass the slider value. When the
        dashboard passes the live slider, sites whose buildable solar covers at
        least this share of demand skip substation/transmission/connection costs.
    site_type:
        V3.9: 'kek' | 'ki' | 'standalone' | 'cluster' | None. The partial-coverage
        within_boundary rule applies only to 'kek' sites because they have real
        polygon boundaries and realistic `within_boundary_coverage_pct`. Non-KEK
        sites have point coordinates and a 50km-radius buildability buffer, so
        their coverage figure is a synthetic artifact — applying the gate there
        would zero out real grid costs based on made-up land.

    Returns
    -------
    str
        One of: 'within_boundary', 'grid_ready', 'invest_transmission',
        'invest_substation', 'grid_first'.
    """
    if has_internal_substation:
        return "within_boundary"

    # V3.9: If within-boundary solar covers >= meaningful_share_pct of demand AND
    # the site is a KEK (real polygon boundary), treat as self-sufficient. Non-KEK
    # sites are excluded because their `within_boundary_coverage_pct` is computed
    # over a 50km-radius buffer around point coordinates — not a real site boundary.
    if (
        site_type == "kek"
        and within_boundary_coverage_pct is not None
        and within_boundary_coverage_pct >= meaningful_share_pct
    ):
        return "within_boundary"

    # Check substation rated capacity — if too small, treat as if grid is not ready
    capacity_ok = substation_capacity_mva is None or substation_capacity_mva >= min_capacity_mva

    kek_near = dist_kek_to_substation_km <= kek_to_sub_threshold_km and capacity_ok
    solar_near = (
        dist_solar_to_substation_km is not None
        and dist_solar_to_substation_km <= solar_to_sub_threshold_km
        and capacity_ok
    )

    # V3.X: If within-boundary solar exists and KEK is near a substation, the on-site
    # solar can connect to the nearby substation. Don't penalise based on remote solar
    # site distance. Capacity sizing is handled separately by capacity_assessment().
    if within_boundary_coverage_pct is not None and within_boundary_coverage_pct > 0 and kek_near:
        return "grid_ready"

    # V3.1: Capacity utilization check — substation may be rated high enough but
    # too loaded to absorb proposed solar generation. Only applies when within-boundary
    # solar isn't available (that case is handled above as grid_ready).
    if (
        capacity_ok
        and substation_capacity_mva is not None
        and solar_capacity_mwp is not None
        and solar_capacity_mwp > 0
    ):
        available_mva = substation_capacity_mva * (1 - substation_utilization_pct)
        if solar_capacity_mwp > available_mva:
            return "invest_substation"

    # V3.1: If inter-substation connectivity is explicitly known, use it
    if inter_substation_connected is False:
        # No existing line between B_solar and B_kek
        if solar_near:
            return "invest_transmission"  # solar can reach a sub, but KEK's sub is disconnected
        return "grid_first"

    if solar_near and kek_near:
        return "grid_ready"
    elif solar_near and not kek_near:
        return "invest_transmission"
    elif kek_near and not solar_near:
        return "invest_substation"
    else:
        return "grid_first"


def capacity_assessment(
    substation_capacity_mva: float | None,
    solar_capacity_mwp: float | None,
    utilization_pct: float = SUBSTATION_UTILIZATION_PCT,
    power_factor: float = SUBSTATION_POWER_FACTOR,
) -> tuple[str, float | None]:
    """Classify substation capacity adequacy for proposed solar injection.

    Converts available MVA to MW via power factor before comparing to solar MWp.
    The returned available value remains in MVA (for display purposes).

    Returns (traffic_light, available_mva):
        'green'   — available real power >= solar potential (fits, no uprating)
        'yellow'  — available real power 0.5×–1× solar potential (partial overflow)
        'red'     — available real power < 0.5× solar potential (major upgrade)
        'unknown' — capacity data unavailable

    Bands are aligned with `substation_upgrade_cost_per_kw`: green is exactly
    the regime where the upgrade cost is $0. This keeps the UI's traffic light
    and the cost column from contradicting each other.
    """
    if substation_capacity_mva is None or substation_capacity_mva <= 0:
        return "unknown", None
    available = substation_capacity_mva * (1 - utilization_pct)
    if solar_capacity_mwp is None or solar_capacity_mwp <= 0:
        return "unknown", round(available, 1)
    available_mw = available * power_factor
    ratio = available_mw / solar_capacity_mwp
    if ratio >= 1.0:
        return "green", round(available, 1)
    elif ratio >= 0.5:
        return "yellow", round(available, 1)
    else:
        return "red", round(available, 1)


def substation_upgrade_cost_per_kw(
    substation_capacity_mva: float | None,
    solar_capacity_mwp: float | None,
    utilization_pct: float = SUBSTATION_UTILIZATION_PCT,
    upgrade_cost_per_kw: float = SUBSTATION_UPGRADE_COST_PER_KW,
    power_factor: float = SUBSTATION_POWER_FACTOR,
) -> float:
    """Additional cost ($/kW) when substation capacity is insufficient for solar injection.

    Converts available MVA to MW via power factor before comparing to solar MWp.
    When available real power < solar capacity, the deficit fraction determines
    the upgrade cost. Covers transformer expansion, new bays, buswork, and
    protection upgrades at the substation.

    Returns 0.0 when capacity data is unknown (conservative: no penalty).
    """
    if substation_capacity_mva is None or substation_capacity_mva <= 0:
        return 0.0
    if solar_capacity_mwp is None or solar_capacity_mwp <= 0:
        return 0.0
    available_mw = substation_capacity_mva * (1 - utilization_pct) * power_factor
    if available_mw >= solar_capacity_mwp:
        return 0.0
    deficit_fraction = (solar_capacity_mwp - max(0.0, available_mw)) / solar_capacity_mwp
    return round(deficit_fraction * upgrade_cost_per_kw, 2)


# ---------------------------------------------------------------------------
# 6. GEAS allocation
# ---------------------------------------------------------------------------


def geas_baseline_allocation(
    kek_df: pd.DataFrame,
    ruptl_df: pd.DataFrame,
    region_cf: float = REGION_CF_DEFAULT,
    target_year: int = 2030,
    capacity_col: str = "plts_new_mw_re_base",
) -> pd.DataFrame:
    """Pro-rata GEAS allocation of pre-2030 RUPTL solar to KEKs by demand share.

    Formula (METHODOLOGY_CONSOLIDATED.md Section 5.3):
        allocatable_green_mwh = pre2030_solar_mw * 8760 * region_cf
        geas_alloc_site = allocatable_green_mwh * (site_demand / region_demand)
        green_share_geas = min(1, geas_alloc_site / site_demand)

    Parameters
    ----------
    kek_df:
        DataFrame with columns: site_id, grid_region_id, demand_mwh.
        Must be filtered to target_year rows only.
    ruptl_df:
        DataFrame with columns: grid_region_id, year, <capacity_col>.
        One row per planned addition.
    region_cf:
        Assumed capacity factor for RUPTL-planned solar (default 0.20).
    target_year:
        Allocation target year (default 2030).
    capacity_col:
        Column name for solar capacity in ruptl_df. Default "plts_new_mw_re_base"
        matches fct_ruptl_pipeline.csv output. Use "capacity_mw" for legacy data.

    Returns
    -------
    pd.DataFrame
        kek_df with additional columns: geas_alloc_mwh, green_share_geas.
    """
    pre2030 = ruptl_df[ruptl_df["year"] <= RUPTL_PRE2030_END].copy()
    supply = (
        pre2030.groupby("grid_region_id")[capacity_col]
        .sum()
        .reset_index()
        .rename(columns={capacity_col: "pre2030_solar_mw"})
    )
    supply["allocatable_green_mwh"] = supply["pre2030_solar_mw"] * HOURS_PER_YEAR * region_cf

    region_demand = (
        kek_df.groupby("grid_region_id")["demand_mwh"]
        .sum()
        .reset_index()
        .rename(columns={"demand_mwh": "region_demand_mwh"})
    )

    out = (
        kek_df.copy()
        .merge(region_demand, on="grid_region_id", how="left")
        .merge(supply[["grid_region_id", "allocatable_green_mwh"]], on="grid_region_id", how="left")
    )
    out["allocatable_green_mwh"] = out["allocatable_green_mwh"].fillna(0)
    out["geas_alloc_mwh"] = np.where(
        out["region_demand_mwh"] > 0,
        out["allocatable_green_mwh"] * (out["demand_mwh"] / out["region_demand_mwh"]),
        0.0,
    )
    out["green_share_geas"] = np.where(
        out["demand_mwh"] > 0,
        np.minimum(1.0, out["geas_alloc_mwh"] / out["demand_mwh"]),
        0.0,  # zero demand → zero green share (avoids 0/0 NaN)
    )
    return out


def geas_policy_allocation(
    kek_df: pd.DataFrame,
    ruptl_df: pd.DataFrame,
    region_cf: float = REGION_CF_DEFAULT,
    shift_fraction: float = 0.20,
    n_priority_regions: int = 2,
    capacity_col: str = "plts_new_mw_re_base",
) -> pd.DataFrame:
    """Priority-weighted GEAS allocation under the policy scenario.

    Policy accelerates 20% of post-2030 RUPTL solar into the pre-2030 window,
    then allocates by demand * PVOUT score (not pure pro-rata).

    Priority regions (top N by aggregate demand) receive accelerated grid upgrades
    (earliest_grid_upgrade_year capped at 2030).

    Parameters
    ----------
    kek_df:
        DataFrame with columns: site_id, grid_region_id, demand_mwh, pvout_best_50km.
    ruptl_df:
        DataFrame with columns: grid_region_id, year, <capacity_col>.
    shift_fraction:
        Share of post-2030 capacity pulled forward (default 0.20 = 20%).
    n_priority_regions:
        Number of highest-demand regions to prioritise (default 2).
    capacity_col:
        Column name for solar capacity in ruptl_df. Default "plts_new_mw_re_base"
        matches fct_ruptl_pipeline.csv output. Use "capacity_mw" for legacy data.

    Returns
    -------
    pd.DataFrame
        kek_df with additional columns: geas_alloc_mwh_policy, green_share_geas_policy.
    """
    by_region = (
        ruptl_df.assign(
            bucket=lambda d: d["year"].apply(lambda y: "pre" if y <= RUPTL_PRE2030_END else "post")
        )
        .groupby(["grid_region_id", "bucket"])[capacity_col]
        .sum()
        .unstack(fill_value=0)
    )
    pre = by_region.get("pre", pd.Series(dtype=float))
    post = by_region.get("post", pd.Series(dtype=float))

    shift = shift_fraction * post
    pre_policy = pre + shift

    supply_policy = pd.DataFrame(
        {
            "grid_region_id": pre_policy.index,
            "allocatable_green_mwh_policy": pre_policy.values * HOURS_PER_YEAR * region_cf,
        }
    )

    region_demand = (
        kek_df.groupby("grid_region_id")["demand_mwh"]
        .sum()
        .reset_index()
        .rename(columns={"demand_mwh": "region_demand_mwh"})
    )

    out = (
        kek_df.copy()
        .merge(region_demand, on="grid_region_id", how="left")
        .merge(supply_policy, on="grid_region_id", how="left")
    )
    out["allocatable_green_mwh_policy"] = out["allocatable_green_mwh_policy"].fillna(0)

    # Priority weighting: demand * pvout
    out["priority_score"] = out["demand_mwh"] * out["pvout_best_50km"]
    region_score = (
        out.groupby("grid_region_id")["priority_score"]
        .sum()
        .reset_index()
        .rename(columns={"priority_score": "region_priority_score"})
    )
    out = out.merge(region_score, on="grid_region_id", how="left")

    out["geas_alloc_mwh_policy"] = np.where(
        out["region_priority_score"] > 0,
        out["allocatable_green_mwh_policy"]
        * (out["priority_score"] / out["region_priority_score"]),
        0.0,
    )
    out["green_share_geas_policy"] = np.where(
        out["demand_mwh"] > 0,
        np.minimum(1.0, out["geas_alloc_mwh_policy"] / out["demand_mwh"]),
        0.0,  # zero demand → zero green share (avoids 0/0 NaN)
    )
    return out


# ---------------------------------------------------------------------------
# 6. RUPTL region metrics
# ---------------------------------------------------------------------------


def ruptl_region_metrics(
    ruptl_df: pd.DataFrame,
    capacity_col: str = "plts_new_mw_re_base",
) -> pd.DataFrame:
    """Compute post2030_share and earliest_grid_upgrade_year per grid region.

    post2030_share = post-2030 MW / (pre-2030 MW + post-2030 MW)
    A value >= 0.60 triggers the plan_late flag.

    Parameters
    ----------
    ruptl_df:
        DataFrame with columns: grid_region_id, year, <capacity_col>.
    capacity_col:
        Column name for solar capacity. Default "plts_new_mw_re_base" matches
        fct_ruptl_pipeline.csv output. Use "capacity_mw" for legacy data.

    Returns
    -------
    pd.DataFrame
        One row per grid_region_id with columns:
        grid_region_id, pre2030_mw, post2030_mw, post2030_share, earliest_grid_upgrade_year.
    """
    df = ruptl_df.copy()
    df["bucket"] = df["year"].apply(lambda y: "pre" if y <= RUPTL_PRE2030_END else "post")
    bucket = (
        df.groupby(["grid_region_id", "bucket"])[capacity_col]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    bucket["pre2030_mw"] = bucket.get("pre", 0)
    bucket["post2030_mw"] = bucket.get("post", 0)
    total = bucket["pre2030_mw"] + bucket["post2030_mw"]
    bucket["post2030_share"] = np.where(total == 0, 1.0, bucket["post2030_mw"] / total)

    earliest = (
        ruptl_df.groupby("grid_region_id")["year"]
        .min()
        .reset_index()
        .rename(columns={"year": "earliest_grid_upgrade_year"})
    )
    earliest["grid_upgrade_pre2030"] = earliest["earliest_grid_upgrade_year"] <= RUPTL_PRE2030_END

    out = bucket[["grid_region_id", "pre2030_mw", "post2030_mw", "post2030_share"]].merge(
        earliest, on="grid_region_id", how="left"
    )
    return out


# ---------------------------------------------------------------------------
# 7. Demand override resolver
# ---------------------------------------------------------------------------


def resolve_demand(fct_demand: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of fct_demand with demand_mwh resolved to the user override when present.

    If demand_mwh_user is non-null for a row, it replaces demand_mwh.
    Otherwise demand_mwh (model-computed from area × intensity) is used.

    This is the single entry point for demand override in both the pipeline
    (build_fct_site_scorecard) and the Dash app callbacks.
    """
    df = fct_demand.copy()
    if "demand_mwh_user" in df.columns:
        mask = df["demand_mwh_user"].notna()
        df.loc[mask, "demand_mwh"] = df.loc[mask, "demand_mwh_user"]
    return df


# ---------------------------------------------------------------------------
# 8. Scenario pipeline  (assembles above functions into end-to-end outputs)
# ---------------------------------------------------------------------------


def build_scorecard(
    dim_kek: pd.DataFrame,
    fct_demand: pd.DataFrame,
    fct_pvout: pd.DataFrame,
    fct_ruptl: pd.DataFrame,
    capex_usd_per_kw: float = TECH006_CAPEX_USD_PER_KW,
    fom_usd_per_kw_yr: float = TECH006_FOM_USD_PER_KW_YR,
    wacc: float = BASE_WACC_DECIMAL,
    lifetime_yr: int = TECH006_LIFETIME_YR,
    grid_cost_usd_mwh: float | None = None,
    target_year: int = 2030,
) -> pd.DataFrame:
    """End-to-end scorecard: joins inputs, computes LCOE + action flags (baseline).

    This is the main entry point for the Dash app and notebooks. All individual
    helper functions above feed into this pipeline.

    Parameters
    ----------
    dim_kek:
        Columns: site_id, site_name, province, grid_region_id, reliability_req.
    fct_demand:
        Columns: site_id, year, demand_mwh.
    fct_pvout:
        Columns: site_id, pvout_centroid (annual kWh/kWp/yr), pvout_best_50km (annual).
        Values must already be annual (kWh/kWp/year). Use pvout_daily_to_annual()
        when reading from GeoTIFF before passing here.
    fct_ruptl:
        Columns: grid_region_id, year, capacity_mw.
    capex_usd_per_kw:
        Solar CAPEX (USD/kW). Default is TECH006 placeholder — replace with extracted value.
    fom_usd_per_kw_yr:
        Solar FOM (USD/kW/year).
    wacc:
        Discount rate (fraction).
    lifetime_yr:
        Asset lifetime (years).
    grid_cost_usd_mwh:
        Grid reference cost (USD/MWh). If None, solar_attractive is left null.
        Provide I-4 tariff once available; BPP as provisional fallback.
    target_year:
        Year of analysis (default 2030).

    Returns
    -------
    pd.DataFrame
        One row per KEK with all computed columns. See DATA_DICTIONARY.md
        Section 2.8 (fct_site_scorecard) for full column spec.
    """
    demand_yr = fct_demand[fct_demand["year"] == target_year].copy()

    ruptl_metrics = ruptl_region_metrics(fct_ruptl)

    df = (
        dim_kek.merge(demand_yr[["site_id", "demand_mwh"]], on="site_id", how="left")
        .merge(
            fct_pvout[["site_id", "pvout_centroid", "pvout_best_50km"]], on="site_id", how="left"
        )
        .merge(
            ruptl_metrics[
                [
                    "grid_region_id",
                    "post2030_share",
                    "grid_upgrade_pre2030",
                    "earliest_grid_upgrade_year",
                ]
            ],
            on="grid_region_id",
            how="left",
        )
    )

    df["cf_best_50km"] = df["pvout_best_50km"].apply(capacity_factor_from_pvout)
    df["lcoe_usd_mwh"] = df["cf_best_50km"].apply(
        lambda cf: lcoe_solar(capex_usd_per_kw, fom_usd_per_kw_yr, wacc, lifetime_yr, cf)
    )

    if grid_cost_usd_mwh is not None:
        df["solar_competitive_gap_pct"] = df["lcoe_usd_mwh"].apply(
            lambda lcoe: solar_competitive_gap(lcoe, grid_cost_usd_mwh)
        )
        df["solar_attractive"] = df["lcoe_usd_mwh"].apply(
            lambda lcoe: is_solar_attractive(lcoe, grid_cost_usd_mwh)
        )
    else:
        df["solar_competitive_gap_pct"] = None
        df["solar_attractive"] = None

    df_geas = geas_baseline_allocation(
        kek_df=df[["site_id", "grid_region_id", "demand_mwh"]].copy(),
        ruptl_df=fct_ruptl,
        target_year=target_year,
    )
    df = df.merge(
        df_geas[["site_id", "geas_alloc_mwh", "green_share_geas"]], on="site_id", how="left"
    )

    if df["solar_attractive"].notna().all():
        flags = df.apply(
            lambda row: action_flags(
                solar_attractive=bool(row["solar_attractive"]),
                grid_upgrade_pre2030=bool(row.get("grid_upgrade_pre2030", False)),
                reliability_req=float(row.get("reliability_req", 0.0)),
                green_share_geas=float(row.get("green_share_geas", 0.0)),
                post2030_share=float(row.get("post2030_share", 1.0)),
            ),
            axis=1,
            result_type="expand",
        )
        df = pd.concat([df, flags], axis=1)
    else:
        for flag in (
            "solar_now",
            "invest_transmission",
            "invest_substation",
            "grid_first",
            "invest_battery",
            "plan_late",
        ):
            df[flag] = None

    df["wacc"] = wacc
    df["capex_usd_per_kw"] = capex_usd_per_kw
    df["grid_cost_usd_mwh"] = grid_cost_usd_mwh
    df["target_year"] = target_year

    return df


def time_bucket(year: int) -> str:
    """Map a year to the RUPTL analysis bucket string.

    Returns '2025-2030' or '2031-2034'.
    """
    return "2025-2030" if year <= RUPTL_PRE2030_END else "2031-2034"
