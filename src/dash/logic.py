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
    FIRMING_ADDER_MID_USD_MWH,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    GENTIE_COST_PER_KW_KM,
    IDR_USD_RATE,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PROJECT_VIABLE_MIN_MWP,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    SUBSTATION_WORKS_PER_KW,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
    TRANSMISSION_LEASE_MID_USD_MWH,
)
from src.model.basic_model import (
    action_flags,
    capacity_factor_from_pvout,
    carbon_breakeven_price,
    is_solar_attractive,
    lcoe_solar,
    lcoe_solar_remote_captive,
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
    gentie_cost_per_kw_km: float = GENTIE_COST_PER_KW_KM
    substation_works_per_kw: float = SUBSTATION_WORKS_PER_KW
    transmission_lease_mid_usd_mwh: float = TRANSMISSION_LEASE_MID_USD_MWH
    firming_adder_mid_usd_mwh: float = FIRMING_ADDER_MID_USD_MWH
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

    @property
    def transmission_lease_low(self) -> float:
        return self.transmission_lease_mid_usd_mwh - 5.0

    @property
    def transmission_lease_high(self) -> float:
        return self.transmission_lease_mid_usd_mwh + 5.0

    def to_dict(self) -> dict:
        """Serialise for dcc.Store."""
        return {
            "capex_usd_per_kw": self.capex_usd_per_kw,
            "lifetime_yr": self.lifetime_yr,
            "wacc_pct": self.wacc_pct,
            "fom_usd_per_kw_yr": self.fom_usd_per_kw_yr,
            "gentie_cost_per_kw_km": self.gentie_cost_per_kw_km,
            "substation_works_per_kw": self.substation_works_per_kw,
            "transmission_lease_mid_usd_mwh": self.transmission_lease_mid_usd_mwh,
            "firming_adder_mid_usd_mwh": self.firming_adder_mid_usd_mwh,
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

    Produces 2 rows per KEK (within_boundary + remote_captive) with low/mid/high
    LCOE bands and all-in columns for remote captive.

    Parameters
    ----------
    resource_df:
        Must have columns: kek_id, pvout_centroid, pvout_best_50km (or
        pvout_buildable_best_50km), dist_to_nearest_substation_km.
    assumptions:
        User-adjustable model assumptions from dashboard sliders.

    Returns
    -------
    pd.DataFrame
        Columns: kek_id, scenario, lcoe_low, lcoe_mid, lcoe_high,
        lcoe_allin_low, lcoe_allin_mid, lcoe_allin_high,
        transmission_lease_adder_usd_mwh, cf, pvout_used.
    """
    wacc = assumptions.wacc_decimal
    lifetime = assumptions.lifetime_yr
    capex_c = assumptions.capex_usd_per_kw
    capex_l = assumptions.capex_low
    capex_h = assumptions.capex_high
    fom = assumptions.fom_usd_per_kw_yr

    # Choose the best available remote PVOUT column
    remote_pvout_col = (
        "pvout_buildable_best_50km"
        if "pvout_buildable_best_50km" in resource_df.columns
        and resource_df["pvout_buildable_best_50km"].notna().any()
        else "pvout_best_50km"
    )

    rows = []
    for _, kek in resource_df.iterrows():
        kek_id = kek["kek_id"]
        dist_km = kek.get("dist_to_nearest_substation_km", 0.0)
        if pd.isna(dist_km):
            dist_km = 0.0

        # Within-boundary scenario: use centroid PVOUT, no gen-tie
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
                "lcoe_allin_low_usd_mwh": _round(lcoe_l_wb),  # no lease for within_boundary
                "lcoe_allin_mid_usd_mwh": _round(lcoe_c_wb),
                "lcoe_allin_high_usd_mwh": _round(lcoe_h_wb),
                "transmission_lease_adder_usd_mwh": 0.0,
                "cf": _round(cf_wb, 4),
                "pvout_used": pvout_wb,
            }
        )

        # Remote captive scenario: use best PVOUT + gen-tie + lease
        pvout_rc = kek.get(remote_pvout_col)
        if pd.isna(pvout_rc) or pvout_rc <= 0:
            pvout_rc = kek.get("pvout_best_50km")
        if pd.isna(pvout_rc) or pvout_rc <= 0:
            pvout_rc = pvout_wb  # fallback to centroid

        if pd.notna(pvout_rc) and pvout_rc > 0:
            cf_rc = capacity_factor_from_pvout(pvout_rc)
            lcoe_c_rc = lcoe_solar_remote_captive(
                capex_c,
                fom,
                wacc,
                lifetime,
                cf_rc,
                dist_km,
                assumptions.gentie_cost_per_kw_km,
                assumptions.substation_works_per_kw,
            )
            lcoe_l_rc = lcoe_solar_remote_captive(
                capex_l,
                fom,
                wacc,
                lifetime,
                cf_rc,
                dist_km,
                assumptions.gentie_cost_per_kw_km,
                assumptions.substation_works_per_kw,
            )
            lcoe_h_rc = lcoe_solar_remote_captive(
                capex_h,
                fom,
                wacc,
                lifetime,
                cf_rc,
                dist_km,
                assumptions.gentie_cost_per_kw_km,
                assumptions.substation_works_per_kw,
            )
            lease_mid = assumptions.transmission_lease_mid_usd_mwh
            lease_low = assumptions.transmission_lease_low
            lease_high = assumptions.transmission_lease_high
        else:
            cf_rc = lcoe_c_rc = lcoe_l_rc = lcoe_h_rc = np.nan
            lease_mid = lease_low = lease_high = 0.0

        rows.append(
            {
                "kek_id": kek_id,
                "scenario": "remote_captive",
                "lcoe_low_usd_mwh": _round(lcoe_l_rc),
                "lcoe_mid_usd_mwh": _round(lcoe_c_rc),
                "lcoe_high_usd_mwh": _round(lcoe_h_rc),
                "lcoe_allin_low_usd_mwh": _round_add(lcoe_l_rc, lease_low),
                "lcoe_allin_mid_usd_mwh": _round_add(lcoe_c_rc, lease_mid),
                "lcoe_allin_high_usd_mwh": _round_add(lcoe_h_rc, lease_high),
                "transmission_lease_adder_usd_mwh": lease_mid,
                "cf": _round(cf_rc, 4),
                "pvout_used": pvout_rc,
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
    rc = lcoe_df[lcoe_df["scenario"] == "remote_captive"].set_index("kek_id")

    default_grid_cost = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH, assumptions.idr_usd_rate)

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

        # Competitive gap
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
        flags = action_flags(
            solar_attractive=attractive,
            grid_upgrade_pre2030=grid_upgrade_pre2030,
            reliability_req=reliability_req,
            green_share_geas=green_share,
            post2030_share=post2030_share,
        )

        # Override thresholds: use user values instead of hardcoded defaults
        flags["plan_late"] = post2030_share >= thresholds.plan_late_threshold
        flags["solar_now"] = (
            attractive and not flags["grid_first"] and green_share >= thresholds.geas_threshold
        )
        flags["firming_needed"] = attractive and reliability_req >= thresholds.reliability_threshold
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
        action_flag = "not_competitive"
        for flag_name in [
            "solar_now",
            "grid_first",
            "firming_needed",
            "invest_resilience",
            "plan_late",
        ]:
            flag_val = (
                resilience if flag_name == "invest_resilience" else flags.get(flag_name, False)
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
            "solar_attractive": attractive,
            "solar_now": flags["solar_now"],
            "grid_first": flags["grid_first"],
            "firming_needed": flags["firming_needed"],
            "firming_adder_usd_mwh": assumptions.firming_adder_mid_usd_mwh
            if flags["firming_needed"]
            else 0.0,
            "lcoe_with_firming_usd_mwh": _round_add(lcoe_mid, assumptions.firming_adder_mid_usd_mwh)
            if flags["firming_needed"]
            else _round(lcoe_mid),
            "plan_late": flags["plan_late"],
            "invest_resilience": resilience,
            "carbon_breakeven_usd_tco2": carbon_be,
            "project_viable": project_viable,
            "grid_cost_usd_mwh": grid_cost,
            "wacc_pct": assumptions.wacc_pct,
            "capex_usd_per_kw": assumptions.capex_usd_per_kw,
        }

        # Add remote captive all-in columns
        if kek_id in rc.index:
            row["lcoe_remote_captive_allin_usd_mwh"] = _round(
                rc.loc[kek_id, "lcoe_allin_mid_usd_mwh"]
            )
            row["lcoe_remote_captive_allin_low_usd_mwh"] = _round(
                rc.loc[kek_id, "lcoe_allin_low_usd_mwh"]
            )
            row["lcoe_remote_captive_allin_high_usd_mwh"] = _round(
                rc.loc[kek_id, "lcoe_allin_high_usd_mwh"]
            )
        else:
            row["lcoe_remote_captive_allin_usd_mwh"] = np.nan
            row["lcoe_remote_captive_allin_low_usd_mwh"] = np.nan
            row["lcoe_remote_captive_allin_high_usd_mwh"] = np.nan

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
