# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
KEK Power Competitiveness — core model functions.

All functions are pure Python / NumPy-free where possible. No Dash imports.
This module is the single source of truth for analytical logic; it is imported
identically by notebooks, pipeline scripts, tests, and the Dash app.

Methodology reference: METHODOLOGY.md
Data column definitions:  DATA_DICTIONARY.md

Units are explicit in every function signature and docstring. When in doubt, read
the unit comments — unit bugs (PVOUT daily vs annual, CAPEX MUSD/MWe vs USD/kW)
have historically produced ~10–100x errors.
"""

from __future__ import annotations

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
    BESS_SIZING_HOURS,
    CAPEX_USD_PER_KW_MAX,
    CAPEX_USD_PER_KW_MIN,
    CONNECTION_COST_PER_KW_KM,
    FIRMING_ADDER_HIGH_USD_MWH,
    FIRMING_ADDER_LOW_USD_MWH,
    FIRMING_ADDER_MID_USD_MWH,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    # V1 aliases — kept for backward compatibility
    GENTIE_COST_PER_KW_KM,
    GRID_CONNECTION_FIXED_PER_KW,
    HOURS_PER_YEAR,
    KEK_TO_SUBSTATION_THRESHOLD_KM,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PVOUT_ANNUAL_MAX,
    PVOUT_ANNUAL_MIN,
    REGION_CF_DEFAULT,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    RUPTL_PRE2030_END,
    SOLAR_TO_SUBSTATION_THRESHOLD_KM,
    SUBSTATION_MIN_CAPACITY_MVA,
    SUBSTATION_UTILIZATION_PCT,
    SUBSTATION_WORKS_PER_KW,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
    TRANSMISSION_LINE_COST_USD_PER_KM,
    WIND_CF_MAX,
    WIND_CF_MIN,
)

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
) -> float:
    """Levelised Cost of Energy for utility-scale solar PV.

    LCOE = (CAPEX × CRF + FOM) / (CF × 8.76)

    where 8.76 = 8760 h/yr ÷ 1000 (converts kW-based costs to MWh).

    Parameters
    ----------
    capex_usd_per_kw:
        Overnight capital cost (USD/kW).
        If reading from fct_tech_parameter.csv (units: MUSD/MWe), multiply by 1000
        before passing here. See METHODOLOGY.md Section 3.2 for unit conversion.
    fixed_om_usd_per_kw_yr:
        Annual fixed O&M (USD/kW/year).
    wacc:
        Weighted average cost of capital (fraction, e.g. 0.09).
    lifetime_yr:
        Asset lifetime (years).
    cf:
        Capacity factor (0–1). Derive from pvout via capacity_factor_from_pvout().

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
    annual_mwh_per_kw = cf * HOURS_PER_YEAR / 1000.0
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
    LCOE alone understates the real investor cost. See METHODOLOGY.md Section 5.5.

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


def bess_storage_adder(
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH,
    solar_cf: float = 0.18,
    wacc: float = BASE_WACC_DECIMAL,
    sizing_hours: float = BESS_SIZING_HOURS,
    bess_lifetime_yr: int = BESS_LIFETIME_YR,
    bess_fom_usd_per_kw_yr: float = BESS_FOM_USD_PER_KW_YR,
    bess_discharge_hours: float = BESS_DISCHARGE_HOURS,
) -> float:
    """Battery storage cost adder per MWh of solar generation (USD/MWh).

    Computes the incremental cost of adding battery storage to a solar plant,
    expressed per MWh of total solar generation. Uses battery-specific CRF
    (15yr lifetime) separate from the solar plant's 25yr lifetime.

    Parameters
    ----------
    bess_capex_usd_per_kwh:
        Installed battery cost per kWh of capacity (default $250).
    solar_cf:
        Solar capacity factor at the site (0-1).
    wacc:
        Weighted average cost of capital (decimal).
    sizing_hours:
        Hours of battery per kW of solar (default 2h for firming).
    bess_lifetime_yr:
        Battery calendar lifetime (default 15 years).
    bess_fom_usd_per_kw_yr:
        Battery fixed O&M per kW of battery power capacity per year.
    bess_discharge_hours:
        Battery system discharge duration (for FOM pro-rating).

    Returns
    -------
    float
        USD/MWh adder to solar LCOE.
    """
    crf = capital_recovery_factor(wacc, bess_lifetime_yr)
    bess_capex_per_kw_solar = bess_capex_usd_per_kwh * sizing_hours
    fom_adj = bess_fom_usd_per_kw_yr * (sizing_hours / bess_discharge_hours)
    annual_cost_per_kw = bess_capex_per_kw_solar * crf + fom_adj
    annual_solar_mwh = solar_cf * HOURS_PER_YEAR / 1000
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
        See METHODOLOGY.md Section 4 and DATA_DICTIONARY.md for BPP vs tariff guidance.

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
    pvout_threshold: float = 1550.0,
) -> bool:
    """Return True if solar economics AND resource both meet the attractiveness bar.

    Conditions (METHODOLOGY.md Section 5.2, Option B):
        1. lcoe_mid ≤ grid_cost  — economics are competitive at current WACC
        2. pvout_best_50km ≥ pvout_threshold  — resource is sufficient (≥1,550 kWh/kWp/yr)

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
        Minimum PVOUT for the resource to be considered sufficient (default 1,550 kWh/kWp/yr).
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


def action_flags(
    solar_attractive: bool,
    grid_upgrade_pre2030: bool,
    reliability_req: float,
    green_share_geas: float,
    post2030_share: float,
    grid_integration_cat: str | None = None,
) -> dict[str, bool]:
    """Compute action flags for a single KEK.

    Flag logic (see METHODOLOGY.md Section 5.2):
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
) -> float | None:
    """Return the carbon price (USD/tCO2) at which solar becomes cost-competitive with the grid.

    Interpretation: if Indonesia (or a buyer) prices carbon at or above this level,
    solar LCOE + carbon cost of grid electricity cross — solar wins on adjusted cost.

    Returns 0.0 if solar is already competitive (LCOE ≤ grid cost).
    Returns None if the emission factor is missing or zero (cannot compute).

    Parameters
    ----------
    lcoe_mid_usd_mwh:
        Solar LCOE mid estimate (USD/MWh).
    grid_cost_usd_mwh:
        Grid reference cost (USD/MWh).
    grid_emission_factor_t_co2_mwh:
        Grid emission intensity (tCO2/MWh). Use GRID_EMISSION_FACTOR_T_CO2_MWH[region].
    """
    if grid_emission_factor_t_co2_mwh <= 0:
        return None
    lcoe_gap = lcoe_mid_usd_mwh - grid_cost_usd_mwh
    if lcoe_gap <= 0:
        return 0.0
    return round(lcoe_gap / grid_emission_factor_t_co2_mwh, 1)


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
) -> str:
    """Classify a KEK's grid integration readiness using three-point proximity.

    Three points: (A) best buildable solar site, (B) nearest PLN substation, (C) KEK centroid.

    Categories (METHODOLOGY.md §2):
        within_boundary      — substation inside KEK polygon; solar can connect directly
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

    Returns
    -------
    str
        One of: 'within_boundary', 'grid_ready', 'invest_transmission',
        'invest_substation', 'grid_first'.
    """
    if has_internal_substation:
        return "within_boundary"

    # Check substation rated capacity — if too small, treat as if grid is not ready
    capacity_ok = substation_capacity_mva is None or substation_capacity_mva >= min_capacity_mva

    kek_near = dist_kek_to_substation_km <= kek_to_sub_threshold_km and capacity_ok
    solar_near = (
        dist_solar_to_substation_km is not None
        and dist_solar_to_substation_km <= solar_to_sub_threshold_km
        and capacity_ok
    )

    # V3.1: Capacity utilization check — substation may be rated high enough but
    # too loaded to absorb proposed solar generation. This triggers invest_substation
    # (upgrade needed) rather than grid_first, because the substation IS physically near.
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
) -> tuple[str, float | None]:
    """Classify substation capacity adequacy for proposed solar injection.

    Returns (traffic_light, available_mva):
        'green'   — available capacity > 2× solar potential
        'yellow'  — available capacity between 0.5× and 2× solar potential
        'red'     — available capacity < 0.5× solar potential (upgrade needed)
        'unknown' — capacity data unavailable
    """
    if substation_capacity_mva is None or substation_capacity_mva <= 0:
        return "unknown", None
    available = substation_capacity_mva * (1 - utilization_pct)
    if solar_capacity_mwp is None or solar_capacity_mwp <= 0:
        return "unknown", round(available, 1)
    ratio = available / solar_capacity_mwp
    if ratio > 2.0:
        return "green", round(available, 1)
    elif ratio >= 0.5:
        return "yellow", round(available, 1)
    else:
        return "red", round(available, 1)


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

    Formula (METHODOLOGY.md Section 5.3):
        allocatable_green_mwh = pre2030_solar_mw * 8760 * region_cf
        geas_alloc_kek = allocatable_green_mwh * (kek_demand / region_demand)
        green_share_geas = min(1, geas_alloc_kek / kek_demand)

    Parameters
    ----------
    kek_df:
        DataFrame with columns: kek_id, grid_region_id, demand_mwh.
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
        DataFrame with columns: kek_id, grid_region_id, demand_mwh, pvout_best_50km.
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
    (build_fct_kek_scorecard) and the Dash app callbacks.
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
        Columns: kek_id, kek_name, province, grid_region_id, reliability_req.
    fct_demand:
        Columns: kek_id, year, demand_mwh.
    fct_pvout:
        Columns: kek_id, pvout_centroid (annual kWh/kWp/yr), pvout_best_50km (annual).
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
        Section 2.8 (fct_kek_scorecard) for full column spec.
    """
    demand_yr = fct_demand[fct_demand["year"] == target_year].copy()

    ruptl_metrics = ruptl_region_metrics(fct_ruptl)

    df = (
        dim_kek.merge(demand_yr[["kek_id", "demand_mwh"]], on="kek_id", how="left")
        .merge(fct_pvout[["kek_id", "pvout_centroid", "pvout_best_50km"]], on="kek_id", how="left")
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
        kek_df=df[["kek_id", "grid_region_id", "demand_mwh"]].copy(),
        ruptl_df=fct_ruptl,
        target_year=target_year,
    )
    df = df.merge(
        df_geas[["kek_id", "geas_alloc_mwh", "green_share_geas"]], on="kek_id", how="left"
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
