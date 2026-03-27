"""
build_fct_kek_scorecard — dashboard-ready fact table, one row per KEK.

Joins all upstream tables into a single flat table for the Dash app to query.
This is the final output of the pipeline — everything else feeds into this.

Sources:
    processed: dim_kek.csv               identity, province, grid_region_id
    processed: fct_kek_resource.csv      PVOUT, CF
    processed: fct_lcoe.csv              LCOE bands at WACC=10% (base case)
    processed: fct_grid_cost_proxy.csv   dashboard_rate, is_provisional
    processed: fct_ruptl_pipeline.csv    pre/post-2030 solar pipeline per region

Output columns: see DATA_DICTIONARY.md Section 2.8
Key computed fields:
    solar_competitive_gap_pct   (lcoe_mid − dashboard_rate) / dashboard_rate × 100
                                Negative = solar is already cheaper than grid.
    action_flag                 One of: solar_now / grid_first / firming_needed / plan_late
    solar_now                   solar_attractive AND grid pipeline adequate
    grid_first                  grid upgrade needed before solar makes sense
    firming_needed              solar resource is good but intermittency is a barrier
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

from src.model.basic_model import action_flags, geas_baseline_allocation, resolve_demand
from src.pipeline.assumptions import BASE_WACC, FIRMING_PVOUT_THRESHOLD

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
FKR_CSV = PROCESSED / "fct_kek_resource.csv"
FLCOE_CSV = PROCESSED / "fct_lcoe.csv"
FGCP_CSV = PROCESSED / "fct_grid_cost_proxy.csv"
FRUPTL_CSV = PROCESSED / "fct_ruptl_pipeline.csv"
FCT_DEMAND_CSV = PROCESSED / "fct_kek_demand.csv"


def _ruptl_region_summary(ruptl: pd.DataFrame) -> pd.DataFrame:
    """Compute pre/post-2030 PLTS summary per grid_region_id (RE Base scenario)."""
    pre = (
        ruptl[ruptl["year"] <= 2030]
        .groupby("grid_region_id")["plts_new_mw_re_base"].sum()
        .rename("pre2030_solar_mw")
    )
    total = (
        ruptl
        .groupby("grid_region_id")["plts_new_mw_re_base"].sum()
        .rename("total_solar_mw")
    )
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
    fct_grid_cost_proxy_csv: Path = FGCP_CSV,
    fct_ruptl_pipeline_csv: Path = FRUPTL_CSV,
    fct_kek_demand_csv: Path = FCT_DEMAND_CSV,
    base_wacc: float = BASE_WACC,
) -> pd.DataFrame:
    """Join all upstream tables into one dashboard-ready scorecard."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_kek = pd.read_csv(dim_kek_csv)
    resource = pd.read_csv(fct_kek_resource_csv)
    lcoe_all = pd.read_csv(fct_lcoe_csv)
    grid_cost = pd.read_csv(fct_grid_cost_proxy_csv)
    ruptl = pd.read_csv(fct_ruptl_pipeline_csv)
    fct_demand_raw = pd.read_csv(fct_kek_demand_csv)
    fct_demand = resolve_demand(fct_demand_raw)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    # LCOE at base WACC, within_boundary scenario (on-site solar, no gen-tie cost)
    lcoe = lcoe_all[
        (lcoe_all["wacc_pct"] == base_wacc) & (lcoe_all["scenario"] == "within_boundary")
    ].copy()
    lcoe = lcoe.rename(columns={
        "lcoe_usd_mwh": "lcoe_mid_usd_mwh",
        "lcoe_low_usd_mwh": "lcoe_low_usd_mwh",
        "lcoe_high_usd_mwh": "lcoe_high_usd_mwh",
    })

    # Grid cost: one row per grid_region_id
    grid_cost = grid_cost[[
        "grid_region_id", "dashboard_rate_usd_mwh", "dashboard_rate_label",
        "dashboard_rate_flag", "tariff_i3_usd_mwh", "tariff_i4_usd_mwh",
    ]].rename(columns={"dashboard_rate_flag": "is_grid_cost_provisional"})
    # Normalize flag to boolean
    grid_cost["is_grid_cost_provisional"] = (
        grid_cost["is_grid_cost_provisional"].str.upper() != "OFFICIAL"
    )

    # RUPTL: pre/post-2030 summary per region
    ruptl_summary = _ruptl_region_summary(ruptl)

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    df = (
        dim_kek
        .merge(resource[["kek_id", "pvout_centroid", "cf_centroid",
                          "pvout_best_50km", "cf_best_50km"]], on="kek_id", how="left")
        .merge(lcoe[["kek_id", "lcoe_low_usd_mwh", "lcoe_mid_usd_mwh", "lcoe_high_usd_mwh",
                     "cf_used", "is_cf_provisional", "is_capex_provisional"]], on="kek_id", how="left")
        .merge(grid_cost, on="grid_region_id", how="left")
        .merge(ruptl_summary[["grid_region_id", "pre2030_solar_mw", "post2030_share"]],
               on="grid_region_id", how="left")
    )

    # Solar competitive gap: negative = solar already cheaper than grid
    df["solar_competitive_gap_pct"] = np.where(
        df["dashboard_rate_usd_mwh"].notna() & df["lcoe_mid_usd_mwh"].notna(),
        (df["lcoe_mid_usd_mwh"] - df["dashboard_rate_usd_mwh"])
        / df["dashboard_rate_usd_mwh"] * 100,
        np.nan,
    ).round(1)

    # Solar attractiveness: good resource AND LCOE <= grid cost
    df["solar_attractive"] = (
        df["pvout_best_50km"].fillna(0) >= FIRMING_PVOUT_THRESHOLD
    ) & (
        df["lcoe_mid_usd_mwh"].fillna(np.inf) <= df["dashboard_rate_usd_mwh"].fillna(0)
    )

    # Derive grid_upgrade_pre2030: True if any solar MW is planned before 2030 in this region
    df["grid_upgrade_pre2030"] = df["pre2030_solar_mw"].fillna(0) > 0

    # GEAS allocation — compute green_share_geas per KEK from real demand
    demand_yr = (
        fct_demand[fct_demand["year"] == 2030][["kek_id", "demand_mwh"]]
        .merge(dim_kek[["kek_id", "grid_region_id"]], on="kek_id", how="left")
    )
    geas_df = geas_baseline_allocation(demand_yr, ruptl)
    # geas_df has kek_id + green_share_geas columns
    df = df.merge(geas_df[["kek_id", "green_share_geas"]], on="kek_id", how="left")
    df["green_share_geas"] = df["green_share_geas"].fillna(0.0)

    # Action flags — compute row by row using model function
    # Signature: action_flags(solar_attractive, grid_upgrade_pre2030, reliability_req,
    #                          green_share_geas, post2030_share)
    flag_rows = []
    for _, row in df.iterrows():
        has_grid_cost = pd.notna(row["dashboard_rate_usd_mwh"])
        has_lcoe = pd.notna(row["lcoe_mid_usd_mwh"])
        has_ruptl = pd.notna(row["post2030_share"])

        if not has_grid_cost or not has_lcoe:
            flags = {"solar_now": None, "grid_first": None,
                     "firming_needed": None, "plan_late": None}
        else:
            flags = action_flags(
                solar_attractive=bool(row["solar_attractive"]),
                grid_upgrade_pre2030=bool(row["grid_upgrade_pre2030"]),
                reliability_req=float(row["reliability_req"]) if pd.notna(row.get("reliability_req")) else 0.6,
                green_share_geas=float(row["green_share_geas"]),
                post2030_share=float(row["post2030_share"]) if has_ruptl else 0.0,
            )

        flag_rows.append(flags)

    flags_df = pd.DataFrame(flag_rows)
    df = pd.concat([df.reset_index(drop=True), flags_df], axis=1)

    # Derive primary action flag label (first True flag, else "data_missing")
    def _flag_label(row: pd.Series) -> str:
        for flag in ["solar_now", "grid_first", "firming_needed", "plan_late"]:
            if row.get(flag) is True:
                return flag
        return "data_missing"

    df["action_flag"] = df.apply(_flag_label, axis=1)

    # Clean power advantage (for map coloring): higher = more competitive
    df["clean_power_advantage"] = (-df["solar_competitive_gap_pct"]).round(1)

    # RUPTL context summary string
    df["ruptl_summary"] = df.apply(
        lambda r: (
            f"{r['pre2030_solar_mw']:.0f} MW solar planned in {r['grid_region_id']} by 2030"
            if pd.notna(r["pre2030_solar_mw"]) else "RUPTL data unavailable"
        ),
        axis=1,
    )

    # Data completeness flag
    key_cols = ["pvout_best_50km", "lcoe_mid_usd_mwh", "dashboard_rate_usd_mwh",
                "post2030_share"]
    n_missing = df[key_cols].isna().sum(axis=1)
    is_provisional = df.get("is_capex_provisional", pd.Series([False] * len(df)))
    df["data_completeness"] = np.select(
        [n_missing == 0, n_missing <= 1],
        ["complete", "partial"],
        default="provisional",
    )
    # Downgrade to provisional if capex inputs are provisional
    df.loc[is_provisional, "data_completeness"] = "provisional"

    return df[[
        "kek_id", "kek_name", "province", "grid_region_id",
        "kek_type", "status", "latitude", "longitude",
        "pvout_centroid", "cf_centroid", "pvout_best_50km", "cf_best_50km",
        "lcoe_low_usd_mwh", "lcoe_mid_usd_mwh", "lcoe_high_usd_mwh",
        "cf_used", "is_cf_provisional", "is_capex_provisional",
        "dashboard_rate_usd_mwh", "dashboard_rate_label", "is_grid_cost_provisional",
        "tariff_i3_usd_mwh", "tariff_i4_usd_mwh",
        "solar_competitive_gap_pct", "solar_attractive",
        "action_flag", "solar_now", "grid_first", "firming_needed", "plan_late",
        "green_share_geas",
        "pre2030_solar_mw", "post2030_share", "grid_upgrade_pre2030", "ruptl_summary",
        "clean_power_advantage", "data_completeness",
    ]]


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
    print("\nSolar competitive gap (WACC=10%, base CAPEX):")
    cols = ["kek_id", "lcoe_mid_usd_mwh", "dashboard_rate_usd_mwh",
            "solar_competitive_gap_pct", "action_flag"]
    print(df[cols].sort_values("solar_competitive_gap_pct").to_string(index=False))


if __name__ == "__main__":
    main()
