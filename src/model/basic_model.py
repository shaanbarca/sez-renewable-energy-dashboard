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

from typing import Literal

import numpy as np
import pandas as pd

from src.assumptions import (
    BASE_WACC_DECIMAL,
    CAPEX_USD_PER_KW_MAX,
    CAPEX_USD_PER_KW_MIN,
    FIRMING_ADDER_HIGH_USD_MWH,
    FIRMING_ADDER_LOW_USD_MWH,
    FIRMING_ADDER_MID_USD_MWH,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    GENTIE_COST_PER_KW_KM,
    HOURS_PER_YEAR,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PVOUT_ANNUAL_MAX,
    PVOUT_ANNUAL_MIN,
    REGION_CF_DEFAULT,
    RUPTL_PRE2030_END,
    SUBSTATION_WORKS_PER_KW,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
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

    Used for 'firming_needed' KEKs where reliability requirements mean
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


def gentie_cost_per_kw(
    dist_km: float,
    cost_per_kw_km: float = GENTIE_COST_PER_KW_KM,
    substation_works_per_kw: float = SUBSTATION_WORKS_PER_KW,
) -> float:
    """Capital cost of gen-tie line + substation works for remote captive solar.

    gen_tie_capex [USD/kW] = dist_km × cost_per_kw_km + substation_works_per_kw

    Parameters
    ----------
    dist_km:
        Distance from solar plant to nearest PLN substation (km). Use
        dist_to_nearest_substation_km from fct_substation_proximity.csv.
    cost_per_kw_km:
        Transmission line construction cost (USD/kW-km). Default: central estimate
        from METHODOLOGY.md §2A.2 (range $3–10/kW-km).
    substation_works_per_kw:
        Substation works at both ends — step-up/step-down transformer, protection,
        metering (USD/kW). Default: central estimate from METHODOLOGY.md §2A.2
        (range $100–200/kW).

    Returns
    -------
    float
        One-time gen-tie capital cost per kW of plant capacity (USD/kW).
        Pass 0 for within-boundary captive (no gen-tie needed).
    """
    if dist_km < 0:
        raise ValueError(f"dist_km must be >= 0, got {dist_km}")
    return dist_km * cost_per_kw_km + substation_works_per_kw


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
    """LCOE for remote captive solar including gen-tie capital cost.

    Treats gen-tie line + substation works as additional overnight CAPEX,
    annualized via the same CRF as the solar plant. This is consistent with
    how CAPEX is handled in lcoe_solar() — all capital costs are annualized
    together, which is correct when the gen-tie is sized and financed with
    the plant.

    effective_capex = capex + gentie_cost_per_kw(dist_km, ...)
    LCOE = lcoe_solar(effective_capex, ...)

    Parameters
    ----------
    capex_usd_per_kw:
        Solar plant overnight CAPEX only (USD/kW) — not including gen-tie.
    dist_km:
        Distance to nearest PLN substation (km) from fct_substation_proximity.csv.
    cost_per_kw_km, substation_works_per_kw:
        Gen-tie cost parameters — see gentie_cost_per_kw().

    Returns
    -------
    float
        All-in LCOE including gen-tie cost (USD/MWh).
    """
    gen_tie = gentie_cost_per_kw(dist_km, cost_per_kw_km, substation_works_per_kw)
    effective_capex = capex_usd_per_kw + gen_tie
    return lcoe_solar(effective_capex, fixed_om_usd_per_kw_yr, wacc, lifetime_yr, cf)


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

def action_flags(
    solar_attractive: bool,
    grid_upgrade_pre2030: bool,
    reliability_req: float,
    green_share_geas: float,
    post2030_share: float,
) -> dict[str, bool]:
    """Compute the four binary action flags for a single KEK.

    Flag logic (see METHODOLOGY.md Section 5.2):
    - solar_now:      solar attractive AND grid ready AND sufficient GEAS allocation
    - grid_first:     solar attractive AND grid upgrade NOT yet pre-2030
    - firming_needed: solar attractive AND KEK reliability requirement >= 0.75
    - plan_late:      >= 60 % of RUPTL solar additions slip to post-2030

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

    Returns
    -------
    dict with keys: solar_now, grid_first, firming_needed, plan_late
    """
    plan_late = post2030_share >= PLAN_LATE_POST2030_SHARE_THRESHOLD
    grid_first = solar_attractive and not grid_upgrade_pre2030
    firming_needed = solar_attractive and reliability_req >= FIRMING_RELIABILITY_REQ_THRESHOLD
    solar_now = (
        solar_attractive
        and not grid_first
        and green_share_geas >= GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD
    )
    return {
        "solar_now": solar_now,
        "grid_first": grid_first,
        "firming_needed": firming_needed,
        "plan_late": plan_late,
    }


# ---------------------------------------------------------------------------
# 5. GEAS allocation
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
            bucket=lambda d: d["year"].apply(
                lambda y: "pre" if y <= RUPTL_PRE2030_END else "post"
            )
        )
        .groupby(["grid_region_id", "bucket"])[capacity_col]
        .sum()
        .unstack(fill_value=0)
    )
    pre = by_region.get("pre", pd.Series(dtype=float))
    post = by_region.get("post", pd.Series(dtype=float))

    shift = shift_fraction * post
    pre_policy = pre + shift

    supply_policy = pd.DataFrame({
        "grid_region_id": pre_policy.index,
        "allocatable_green_mwh_policy": pre_policy.values * HOURS_PER_YEAR * region_cf,
    })

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
    df["bucket"] = df["year"].apply(
        lambda y: "pre" if y <= RUPTL_PRE2030_END else "post"
    )
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
        dim_kek
        .merge(demand_yr[["kek_id", "demand_mwh"]], on="kek_id", how="left")
        .merge(fct_pvout[["kek_id", "pvout_centroid", "pvout_best_50km"]], on="kek_id", how="left")
        .merge(
            ruptl_metrics[["grid_region_id", "post2030_share", "grid_upgrade_pre2030",
                            "earliest_grid_upgrade_year"]],
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
    df = df.merge(df_geas[["kek_id", "geas_alloc_mwh", "green_share_geas"]], on="kek_id", how="left")

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
        for flag in ("solar_now", "grid_first", "firming_needed", "plan_late"):
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
