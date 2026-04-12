# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_fct_kek_scorecard — dashboard-ready fact table, one row per KEK.

Joins all upstream tables into a single flat table for the Dash app to query.
This is the final output of the pipeline — everything else feeds into this.

Sources:
    processed: dim_kek.csv                    identity, province, grid_region_id
    processed: fct_kek_resource.csv           PVOUT, CF
    processed: fct_lcoe.csv                   LCOE bands at WACC=10% (base case)
    processed: fct_grid_cost_proxy.csv        dashboard_rate, is_provisional
    processed: fct_ruptl_pipeline.csv         pre/post-2030 solar pipeline per region
    processed: fct_kek_demand.csv             2030 demand estimate per KEK
    processed: fct_substation_proximity.csv   substation distance + siting scenario

Output columns: see DATA_DICTIONARY.md Section 2.8
Key computed fields:
    solar_competitive_gap_pct   (lcoe_mid − dashboard_rate) / dashboard_rate × 100
                                Negative = solar is already cheaper than grid.
    action_flag                 One of: solar_now / invest_transmission / invest_substation / grid_first / invest_battery / plan_late
    solar_now                   solar_attractive AND grid pipeline adequate
    invest_transmission         solar near substation but KEK far — build transmission (V3)
    invest_substation           KEK near substation but solar far — build substation (V3)
    grid_first                  grid upgrade needed before solar makes sense
    invest_battery              solar resource is good but intermittency needs battery storage (V3)
    plan_late                   ≥60% of RUPTL additions are post-2030 (matches basic_model.PLAN_LATE_POST2030_SHARE_THRESHOLD)
    clean_power_advantage       −solar_competitive_gap_pct (higher = more competitive)
    data_completeness           "complete" / "partial" / "provisional"

WACC note: scorecard uses WACC=10% as the base case for action flags and gap calc.
           The Dash app recomputes LCOE live for other WACC values.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.model.basic_model import (
    action_flags,
    carbon_breakeven_price,
    geas_baseline_allocation,
    invest_resilience,
    resolve_demand,
)
from src.pipeline.assumptions import BASE_WACC, FIRMING_PVOUT_THRESHOLD, PROJECT_VIABLE_MIN_MWP

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
FKR_CSV = PROCESSED / "fct_kek_resource.csv"
FLCOE_CSV = PROCESSED / "fct_lcoe.csv"
FLCOE_WIND_CSV = PROCESSED / "fct_lcoe_wind.csv"
FGCP_CSV = PROCESSED / "fct_grid_cost_proxy.csv"
FRUPTL_CSV = PROCESSED / "fct_ruptl_pipeline.csv"
FCT_DEMAND_CSV = PROCESSED / "fct_kek_demand.csv"
FSUB_CSV = PROCESSED / "fct_substation_proximity.csv"


def _ruptl_region_summary(ruptl: pd.DataFrame) -> pd.DataFrame:
    """Compute pre/post-2030 PLTS summary per grid_region_id (RE Base scenario)."""
    pre = (
        ruptl[ruptl["year"] <= 2030]
        .groupby("grid_region_id")["plts_new_mw_re_base"]
        .sum()
        .rename("pre2030_solar_mw")
    )
    total = ruptl.groupby("grid_region_id")["plts_new_mw_re_base"].sum().rename("total_solar_mw")
    summary = pd.concat([pre, total], axis=1).reset_index()
    summary["post2030_share"] = np.where(
        summary["total_solar_mw"] > 0,
        1 - summary["pre2030_solar_mw"] / summary["total_solar_mw"],
        0.0,
    )
    return summary


def build_fct_kek_scorecard(
    dim_kek_csv: Path = DIM_KEK_CSV,
    fct_kek_resource_csv: Path = FKR_CSV,
    fct_lcoe_csv: Path = FLCOE_CSV,
    fct_lcoe_wind_csv: Path = FLCOE_WIND_CSV,
    fct_grid_cost_proxy_csv: Path = FGCP_CSV,
    fct_ruptl_pipeline_csv: Path = FRUPTL_CSV,
    fct_kek_demand_csv: Path = FCT_DEMAND_CSV,
    fct_substation_proximity_csv: Path = FSUB_CSV,
    base_wacc: float = BASE_WACC,
) -> pd.DataFrame:
    """Join all upstream tables into one dashboard-ready scorecard."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_kek = pd.read_csv(dim_kek_csv)
    resource = pd.read_csv(fct_kek_resource_csv)
    lcoe_all = pd.read_csv(fct_lcoe_csv)
    lcoe_wind_all = pd.read_csv(fct_lcoe_wind_csv)
    grid_cost = pd.read_csv(fct_grid_cost_proxy_csv)
    ruptl = pd.read_csv(fct_ruptl_pipeline_csv)
    fct_demand_raw = pd.read_csv(fct_kek_demand_csv)
    fct_demand = resolve_demand(fct_demand_raw)
    fct_sub = pd.read_csv(fct_substation_proximity_csv)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    # LCOE at base WACC, within_boundary scenario (on-site solar, no connection cost)
    lcoe = lcoe_all[
        (lcoe_all["wacc_pct"] == base_wacc) & (lcoe_all["scenario"] == "within_boundary")
    ].copy()
    lcoe = lcoe.rename(
        columns={
            "lcoe_usd_mwh": "lcoe_mid_usd_mwh",
            "lcoe_low_usd_mwh": "lcoe_low_usd_mwh",
            "lcoe_high_usd_mwh": "lcoe_high_usd_mwh",
        }
    )

    # LCOE at WACC=8% (de-risked finance scenario) — same scenario, different WACC row
    lcoe_wacc8 = lcoe_all[
        (lcoe_all["wacc_pct"] == 8.0) & (lcoe_all["scenario"] == "within_boundary")
    ][["kek_id", "lcoe_usd_mwh"]].rename(columns={"lcoe_usd_mwh": "lcoe_mid_wacc8_usd_mwh"})

    # V2: Grid-connected solar LCOE at base WACC (includes connection cost to nearest substation)
    _gc_scenario = (
        "grid_connected_solar"
        if "grid_connected_solar" in lcoe_all["scenario"].values
        else "remote_captive"
    )
    lcoe_gc = lcoe_all[
        (lcoe_all["wacc_pct"] == BASE_WACC) & (lcoe_all["scenario"] == _gc_scenario)
    ][
        ["kek_id"]
        + [
            c
            for c in [
                "lcoe_usd_mwh",
                "lcoe_low_usd_mwh",
                "lcoe_high_usd_mwh",
                "connection_cost_per_kw",
                "transmission_cost_per_kw",
                "substation_upgrade_cost_per_kw",
            ]
            if c in lcoe_all.columns
        ]
    ].copy()
    # Rename to dashboard column names
    _gc_renames = {"lcoe_usd_mwh": "lcoe_grid_connected_usd_mwh"}
    if "lcoe_low_usd_mwh" in lcoe_gc.columns:
        _gc_renames["lcoe_low_usd_mwh"] = "lcoe_grid_connected_low_usd_mwh"
    if "lcoe_high_usd_mwh" in lcoe_gc.columns:
        _gc_renames["lcoe_high_usd_mwh"] = "lcoe_grid_connected_high_usd_mwh"
    lcoe_gc = lcoe_gc.rename(columns=_gc_renames)

    # Wind LCOE at base WACC, within_boundary
    lcoe_wind_wb = lcoe_wind_all[
        (lcoe_wind_all["wacc_pct"] == base_wacc) & (lcoe_wind_all["scenario"] == "within_boundary")
    ][["kek_id", "lcoe_usd_mwh", "cf_wind_used", "wind_speed_ms"]].rename(
        columns={
            "lcoe_usd_mwh": "lcoe_wind_mid_usd_mwh",
            "cf_wind_used": "cf_wind",
            "wind_speed_ms": "wind_speed_ms",
        }
    )

    # Wind remote captive all-in at base WACC
    lcoe_wind_rc = lcoe_wind_all[
        (lcoe_wind_all["wacc_pct"] == base_wacc) & (lcoe_wind_all["scenario"] == "remote_captive")
    ][["kek_id", "lcoe_allin_usd_mwh"]].rename(
        columns={"lcoe_allin_usd_mwh": "lcoe_wind_allin_mid_usd_mwh"}
    )

    # Grid cost: one row per grid_region_id
    grid_cost = grid_cost[
        [
            "grid_region_id",
            "dashboard_rate_usd_mwh",
            "dashboard_rate_label",
            "dashboard_rate_flag",
            "tariff_i3_usd_mwh",
            "tariff_i4_usd_mwh",
            "grid_emission_factor_t_co2_mwh",
        ]
    ].rename(columns={"dashboard_rate_flag": "is_grid_cost_provisional"})
    # Normalize flag to boolean
    grid_cost["is_grid_cost_provisional"] = (
        grid_cost["is_grid_cost_provisional"].str.upper() != "OFFICIAL"
    )

    # RUPTL: pre/post-2030 summary per region
    ruptl_summary = _ruptl_region_summary(ruptl)

    # Substation proximity: distance + siting scenario + V2 grid integration per KEK
    # V3.1: also pull connectivity + capacity assessment columns
    _sub_cols = [
        "kek_id",
        "dist_to_nearest_substation_km",
        "nearest_substation_capacity_mva",
        "siting_scenario",
    ]
    for _col in [
        "grid_integration_category",
        "dist_solar_to_nearest_substation_km",
        "same_grid_region",
        "line_connected",
        "inter_substation_connected",
        "inter_substation_dist_km",
        "available_capacity_mva",
        "capacity_assessment",
    ]:
        if _col in fct_sub.columns:
            _sub_cols.append(_col)
    sub = fct_sub[_sub_cols].copy()

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    # Merge buildability columns when present in fct_kek_resource
    _build_cols = [
        "pvout_buildable_best_50km",
        "buildable_area_ha",
        "max_captive_capacity_mwp",
        "buildability_constraint",
        "pvout_within_boundary",
        "within_boundary_source",
    ]
    _resource_base = ["kek_id", "pvout_centroid", "cf_centroid", "pvout_best_50km", "cf_best_50km"]
    _resource_cols = _resource_base + [c for c in _build_cols if c in resource.columns]

    df = (
        dim_kek.merge(resource[_resource_cols], on="kek_id", how="left")
        .merge(
            lcoe[
                [
                    "kek_id",
                    "lcoe_low_usd_mwh",
                    "lcoe_mid_usd_mwh",
                    "lcoe_high_usd_mwh",
                    "cf_used",
                    "is_cf_provisional",
                    "is_capex_provisional",
                ]
            ],
            on="kek_id",
            how="left",
        )
        .merge(grid_cost, on="grid_region_id", how="left")
        .merge(
            ruptl_summary[["grid_region_id", "pre2030_solar_mw", "post2030_share"]],
            on="grid_region_id",
            how="left",
        )
        .merge(lcoe_wacc8, on="kek_id", how="left")
        .merge(lcoe_gc, on="kek_id", how="left")
        .merge(sub, on="kek_id", how="left")
        .merge(lcoe_wind_wb, on="kek_id", how="left")
        .merge(lcoe_wind_rc, on="kek_id", how="left")
    )

    # Ensure buildability columns exist (NaN if data/buildability/ not yet populated)
    for col in _build_cols:
        if col not in df.columns:
            df[col] = np.nan if col != "buildability_constraint" else "data_unavailable"

    # Resource quality label — reflects how much of the buildability filter was applied
    # "filtered": all 4 data files applied (Kawasan Hutan + peat + land cover + DEM)
    # "partial_filter": some data files applied (e.g. DEM-only for slope/elevation)
    # "provisional": no buildability data present
    from src.pipeline.build_fct_kek_resource import (
        _REQUIRED_BUILD_FILES,
        BUILDABILITY_DIR,
        _available_build_files,
    )

    _n_avail = len(_available_build_files(BUILDABILITY_DIR))
    _n_total = len(_REQUIRED_BUILD_FILES)
    _has_any = _n_avail > 0
    _has_all = _n_avail == _n_total

    def _resource_quality(row: pd.Series) -> str:
        buildable = row.get("pvout_buildable_best_50km")
        if pd.isna(buildable) or buildable <= 0:
            return "provisional (no buildability filter)"
        if _has_all:
            return "filtered"
        return f"partial_filter ({_n_avail}/{_n_total} layers)"

    df["resource_quality"] = df.apply(_resource_quality, axis=1)

    # Solar competitive gap: negative = solar already cheaper than grid
    df["solar_competitive_gap_pct"] = np.where(
        df["dashboard_rate_usd_mwh"].notna() & df["lcoe_mid_usd_mwh"].notna(),
        (df["lcoe_mid_usd_mwh"] - df["dashboard_rate_usd_mwh"])
        / df["dashboard_rate_usd_mwh"]
        * 100,
        np.nan,
    ).round(1)

    # WACC=8% gap and flip flag (de-risked finance scenario)
    df["solar_competitive_gap_wacc8_pct"] = np.where(
        df["dashboard_rate_usd_mwh"].notna() & df["lcoe_mid_wacc8_usd_mwh"].notna(),
        (df["lcoe_mid_wacc8_usd_mwh"] - df["dashboard_rate_usd_mwh"])
        / df["dashboard_rate_usd_mwh"]
        * 100,
        np.nan,
    ).round(1)
    df["solar_now_at_wacc8"] = df["lcoe_mid_wacc8_usd_mwh"].fillna(np.inf) <= df[
        "dashboard_rate_usd_mwh"
    ].fillna(0)

    # Solar attractiveness: good resource AND LCOE <= grid cost
    df["solar_attractive"] = (df["pvout_best_50km"].fillna(0) >= FIRMING_PVOUT_THRESHOLD) & (
        df["lcoe_mid_usd_mwh"].fillna(np.inf) <= df["dashboard_rate_usd_mwh"].fillna(0)
    )

    # Best RE technology: pick whichever has lower LCOE (solar vs wind)
    solar_lcoe = df["lcoe_mid_usd_mwh"].fillna(np.inf)
    wind_lcoe = df["lcoe_wind_mid_usd_mwh"].fillna(np.inf)

    df["best_re_lcoe_mid_usd_mwh"] = np.where(
        solar_lcoe <= wind_lcoe,
        df["lcoe_mid_usd_mwh"],
        df["lcoe_wind_mid_usd_mwh"],
    )
    # Replace inf with NaN (both were NaN)
    df.loc[
        df["lcoe_mid_usd_mwh"].isna() & df["lcoe_wind_mid_usd_mwh"].isna(),
        "best_re_lcoe_mid_usd_mwh",
    ] = np.nan

    def _best_re(row: pd.Series) -> str:
        s = row["lcoe_mid_usd_mwh"]
        w = row["lcoe_wind_mid_usd_mwh"]
        if pd.isna(s) and pd.isna(w):
            return "none"
        if pd.isna(w):
            return "solar"
        if pd.isna(s):
            return "wind"
        if abs(s - w) < 1.0:  # within $1/MWh = effectively tied
            return "both"
        return "solar" if s < w else "wind"

    df["best_re_technology"] = df.apply(_best_re, axis=1)

    # RE competitive gap: uses best RE LCOE vs grid cost
    df["re_competitive_gap_pct"] = np.where(
        df["dashboard_rate_usd_mwh"].notna() & df["best_re_lcoe_mid_usd_mwh"].notna(),
        (df["best_re_lcoe_mid_usd_mwh"] - df["dashboard_rate_usd_mwh"])
        / df["dashboard_rate_usd_mwh"]
        * 100,
        np.nan,
    ).round(1)

    # Derive grid_upgrade_pre2030: True if any solar MW is planned before 2030 in this region
    df["grid_upgrade_pre2030"] = df["pre2030_solar_mw"].fillna(0) > 0

    # GEAS allocation — compute green_share_geas per KEK from real demand
    demand_yr = fct_demand[fct_demand["year"] == 2030][["kek_id", "demand_mwh"]].merge(
        dim_kek[["kek_id", "grid_region_id"]], on="kek_id", how="left"
    )
    geas_df = geas_baseline_allocation(demand_yr, ruptl)
    # geas_df has kek_id + green_share_geas columns
    df = df.merge(geas_df[["kek_id", "green_share_geas"]], on="kek_id", how="left")

    # 2030 demand — join for persona/dashboard use (PPA sizing, green share context)
    demand_2030 = demand_yr[["kek_id", "demand_mwh"]].rename(
        columns={"demand_mwh": "demand_mwh_2030"}
    )
    df = df.merge(demand_2030, on="kek_id", how="left")
    df["green_share_geas"] = df["green_share_geas"].fillna(0.0)

    # Project viability flag — True if buildable capacity meets minimum IPP threshold
    df["project_viable"] = df["max_captive_capacity_mwp"].fillna(0) >= PROJECT_VIABLE_MIN_MWP

    # Action flags — compute row by row using model function
    # Signature: action_flags(solar_attractive, grid_upgrade_pre2030, reliability_req,
    #                          green_share_geas, post2030_share)
    flag_rows = []
    for _, row in df.iterrows():
        has_grid_cost = pd.notna(row["dashboard_rate_usd_mwh"])
        has_lcoe = pd.notna(row["lcoe_mid_usd_mwh"])
        has_ruptl = pd.notna(row["post2030_share"])

        reliability = float(row["reliability_req"]) if pd.notna(row.get("reliability_req")) else 0.6

        if not has_grid_cost or not has_lcoe:
            flags = {
                "solar_now": None,
                "invest_transmission": None,
                "invest_substation": None,
                "invest_battery": None,
                "grid_first": None,
                "plan_late": None,
                "invest_resilience": None,
            }
        else:
            gi_cat = (
                row.get("grid_integration_category")
                if pd.notna(row.get("grid_integration_category"))
                else None
            )
            flags = action_flags(
                solar_attractive=bool(row["solar_attractive"]),
                grid_upgrade_pre2030=bool(row["grid_upgrade_pre2030"]),
                reliability_req=reliability,
                green_share_geas=float(row["green_share_geas"]),
                post2030_share=float(row["post2030_share"]) if has_ruptl else 0.0,
                grid_integration_cat=gi_cat,
            )
            flags["invest_resilience"] = invest_resilience(
                solar_competitive_gap_pct=float(row["solar_competitive_gap_pct"])
                if pd.notna(row["solar_competitive_gap_pct"])
                else float("inf"),
                reliability_req=reliability,
            )

        flag_rows.append(flags)

    flags_df = pd.DataFrame(flag_rows)
    df = pd.concat([df.reset_index(drop=True), flags_df], axis=1)

    # Derive primary action flag label
    # - "data_missing": one or more required inputs were NaN (flags set to None above)
    # - "not_competitive": all data present but BOTH solar AND wind LCOE > grid cost
    # - otherwise: first True flag wins
    def _flag_label(row: pd.Series) -> str:
        if any(
            row.get(f) is None for f in ["solar_now", "grid_first", "invest_battery", "plan_late"]
        ):
            return "data_missing"
        for flag in [
            "solar_now",
            "invest_transmission",
            "invest_substation",
            "grid_first",
            "invest_battery",
            "invest_resilience",
            "plan_late",
        ]:
            if row.get(flag) is True:
                return flag
        # Check if wind makes this KEK competitive even if solar isn't
        wind_lcoe = row.get("lcoe_wind_mid_usd_mwh")
        grid_rate = row.get("dashboard_rate_usd_mwh")
        if pd.notna(wind_lcoe) and pd.notna(grid_rate) and wind_lcoe <= grid_rate:
            return "wind_competitive"
        return "not_competitive"

    df["action_flag"] = df.apply(_flag_label, axis=1)

    # Carbon breakeven price: USD/tCO2 at which solar becomes cost-competitive
    df["carbon_breakeven_usd_tco2"] = df.apply(
        lambda r: (
            carbon_breakeven_price(
                lcoe_mid_usd_mwh=float(r["lcoe_mid_usd_mwh"]),
                grid_cost_usd_mwh=float(r["dashboard_rate_usd_mwh"]),
                grid_emission_factor_t_co2_mwh=float(r["grid_emission_factor_t_co2_mwh"]),
            )
            if pd.notna(r["lcoe_mid_usd_mwh"])
            and pd.notna(r["dashboard_rate_usd_mwh"])
            and pd.notna(r["grid_emission_factor_t_co2_mwh"])
            else None
        ),
        axis=1,
    )

    # Clean power advantage (for map coloring): higher = more competitive
    df["clean_power_advantage"] = (-df["solar_competitive_gap_pct"]).round(1)

    # RUPTL context summary string
    df["ruptl_summary"] = df.apply(
        lambda r: (
            f"{r['pre2030_solar_mw']:.0f} MW solar planned in {r['grid_region_id']} by 2030"
            if pd.notna(r["pre2030_solar_mw"])
            else "RUPTL data unavailable"
        ),
        axis=1,
    )

    # Data completeness flag
    key_cols = ["pvout_best_50km", "lcoe_mid_usd_mwh", "dashboard_rate_usd_mwh", "post2030_share"]
    n_missing = df[key_cols].isna().sum(axis=1)
    is_provisional = df.get("is_capex_provisional", pd.Series([False] * len(df)))
    df["data_completeness"] = np.select(
        [n_missing == 0, n_missing <= 1],
        ["complete", "partial"],
        default="provisional",
    )
    # Downgrade to provisional if capex inputs are provisional
    df.loc[is_provisional, "data_completeness"] = "provisional"

    # V3.1: Ensure optional columns exist (NaN if upstream didn't produce them)
    for _opt_col in [
        "same_grid_region",
        "line_connected",
        "inter_substation_connected",
        "inter_substation_dist_km",
        "available_capacity_mva",
        "capacity_assessment",
        "transmission_cost_per_kw",
        "substation_upgrade_cost_per_kw",
    ]:
        if _opt_col not in df.columns:
            df[_opt_col] = np.nan

    # Grid investment needed (USD): total grid infrastructure cost × capacity (kW)
    # Includes gen-tie (connection_cost_per_kw) + new transmission line if needed
    _infra_cost = (
        df["connection_cost_per_kw"].fillna(0)
        + df["transmission_cost_per_kw"].fillna(0)
        + df["substation_upgrade_cost_per_kw"].fillna(0)
    )
    df["grid_investment_needed_usd"] = np.where(
        (_infra_cost > 0) & (df["max_captive_capacity_mwp"] > 0),
        (_infra_cost * df["max_captive_capacity_mwp"] * 1000).round(0),
        np.nan,
    )

    return df[
        [
            "kek_id",
            "kek_name",
            "province",
            "grid_region_id",
            "kek_type",
            "status",
            "latitude",
            "longitude",
            "pvout_centroid",
            "cf_centroid",
            "pvout_best_50km",
            "cf_best_50km",
            "pvout_buildable_best_50km",
            "buildable_area_ha",
            "max_captive_capacity_mwp",
            "buildability_constraint",
            "resource_quality",
            "dist_to_nearest_substation_km",
            "nearest_substation_capacity_mva",
            "siting_scenario",
            "grid_integration_category",
            "same_grid_region",
            "line_connected",
            "inter_substation_connected",
            "inter_substation_dist_km",
            "available_capacity_mva",
            "capacity_assessment",
            "project_viable",
            "demand_mwh_2030",
            "lcoe_low_usd_mwh",
            "lcoe_mid_usd_mwh",
            "lcoe_high_usd_mwh",
            "lcoe_grid_connected_usd_mwh",
            "lcoe_grid_connected_low_usd_mwh",
            "lcoe_grid_connected_high_usd_mwh",
            "connection_cost_per_kw",
            "transmission_cost_per_kw",
            "substation_upgrade_cost_per_kw",
            "grid_investment_needed_usd",
            "cf_used",
            "is_cf_provisional",
            "is_capex_provisional",
            "lcoe_wind_mid_usd_mwh",
            "lcoe_wind_allin_mid_usd_mwh",
            "cf_wind",
            "wind_speed_ms",
            "best_re_technology",
            "best_re_lcoe_mid_usd_mwh",
            "re_competitive_gap_pct",
            "dashboard_rate_usd_mwh",
            "dashboard_rate_label",
            "is_grid_cost_provisional",
            "tariff_i3_usd_mwh",
            "tariff_i4_usd_mwh",
            "solar_competitive_gap_pct",
            "solar_attractive",
            "lcoe_mid_wacc8_usd_mwh",
            "solar_competitive_gap_wacc8_pct",
            "solar_now_at_wacc8",
            "action_flag",
            "solar_now",
            "invest_transmission",
            "invest_substation",
            "invest_battery",
            "grid_first",
            "invest_resilience",
            "plan_late",
            "green_share_geas",
            "pre2030_solar_mw",
            "post2030_share",
            "grid_upgrade_pre2030",
            "ruptl_summary",
            "grid_emission_factor_t_co2_mwh",
            "carbon_breakeven_usd_tco2",
            "clean_power_advantage",
            "data_completeness",
        ]
    ]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "fct_kek_scorecard.csv"
    df = build_fct_kek_scorecard()
    df.to_csv(out, index=False)
    print(f"fct_kek_scorecard: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print("\nAction flag distribution:")
    print(df["action_flag"].value_counts().to_string())
    print("\nData completeness:")
    print(df["data_completeness"].value_counts().to_string())
    print("\nCompetitive gap (WACC=10%, base CAPEX):")
    cols = [
        "kek_id",
        "lcoe_mid_usd_mwh",
        "lcoe_wind_mid_usd_mwh",
        "best_re_technology",
        "dashboard_rate_usd_mwh",
        "re_competitive_gap_pct",
        "action_flag",
    ]
    print(df[cols].sort_values("re_competitive_gap_pct").to_string(index=False))


if __name__ == "__main__":
    main()
