# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: CGSP nickel smelter spatial join against site polygons.

Source: China-Global South Project Nickel Tracker (CC license)
URL: https://nickel.chinaglobalsouth.com/

Produces per-smelter rows with site_id (null if outside all sites + 50km buffer),
plus per-site aggregates for scorecard enrichment.

Uses SiteTypeConfig.captive_power_method dispatch: KEK/KI sites use haversine
proximity matching; standalone/cluster sites use direct site_id matching
(no-op today; activates when smelter CSV gains site_id in Step 10).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.geo_utils import direct_match, proximity_match, sites_by_captive_method

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "captive_power"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"


def build_fct_captive_nickel(
    cgsp_path: Path | str = DATA_DIR / "cgsp_nickel_tracker.csv",
    sites_path: Path | str = PROCESSED_DIR / "dim_sites.csv",
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Load CGSP nickel data and spatial-join processing smelters against sites."""
    cgsp_path = Path(cgsp_path)
    if not cgsp_path.exists():
        print(f"  CGSP data not found at {cgsp_path} — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.read_csv(cgsp_path)

    df = df[df["parent_project_type"] == "Processing"].copy()
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)

    df["is_chinese_owned"] = df["country_ownership"].astype(str).str.contains("China", na=False)
    df["cost_usd"] = df["cost"].where(df["cost"].notna() & (df["cost"] != "-"), None)

    sites_path = Path(sites_path)
    if not sites_path.exists():
        print(f"  dim_sites not found at {sites_path}")
        return pd.DataFrame()

    sites = pd.read_csv(sites_path)

    prox_sites = sites_by_captive_method(sites, "proximity")
    direct_sites = sites_by_captive_method(sites, "direct")

    prox = proximity_match(prox_sites, df, buffer_km=buffer_km)
    direct = direct_match(direct_sites, df)
    if not direct.empty:
        direct["dist_km"] = 0.0
        prox = prox[~prox["project_name"].isin(direct["project_name"])]

    matched = pd.concat([prox, direct], ignore_index=True)

    return pd.DataFrame(
        {
            "project_name": matched.get("project_name", ""),
            "project_type": matched.get("project_type", ""),
            "latitude": matched["latitude"],
            "longitude": matched["longitude"],
            "capacity_tons": matched.get("capacity"),
            "capacity_unit": matched.get("capacity_unit", "ton"),
            "cost_usd": matched.get("cost_usd"),
            "status": matched.get("status", ""),
            "province": matched.get("province_city", ""),
            "shareholder": matched.get("shareholder_ownership", ""),
            "is_chinese_owned": matched["is_chinese_owned"],
            "esg_ecological": matched.get("esg_impact_ecological", ""),
            "esg_social": matched.get("esg_impact_social", ""),
            "site_id": matched["site_id"],
            "dist_to_site_km": matched["dist_km"],
        }
    )


def build_captive_nickel_summary(
    smelter_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate smelter data per site for scorecard enrichment."""
    if smelter_df is None:
        smelter_df = build_fct_captive_nickel()

    if smelter_df.empty:
        return pd.DataFrame()

    matched = smelter_df[smelter_df["site_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("site_id")
        .agg(
            nickel_smelter_count=("project_name", "count"),
            nickel_projects=("project_name", lambda x: "; ".join(x.unique())),
            dominant_process_type=(
                "project_type",
                lambda x: x.value_counts().index[0] if len(x) > 0 else "",
            ),
            has_chinese_ownership=("is_chinese_owned", "any"),
        )
        .reset_index()
    )
    return summary


if __name__ == "__main__":
    df = build_fct_captive_nickel()
    print(f"Total processing smelters: {len(df)}")
    print(f"Matched to sites: {df['site_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_nickel.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_nickel_summary(df)
        if not summary.empty:
            print(f"\nPer-site summary ({len(summary)} sites):")
            print(summary.to_string(index=False))
