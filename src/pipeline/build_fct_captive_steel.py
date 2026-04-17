# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: GEM steel plant spatial join against site polygons.

Source: Global Energy Monitor Global Iron and Steel Plant Tracker
URL: https://globalenergymonitor.org/projects/global-iron-and-steel-tracker/

Produces per-plant rows with site_id (null if outside all sites + 50km buffer),
plus per-site aggregates for scorecard enrichment and CBAM calculations.

Uses SiteTypeConfig.captive_power_method dispatch: KEK/KI sites use haversine
proximity matching; standalone/cluster sites use direct site_id matching
(no-op today; activates when plant CSV gains site_id in Step 10).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.geo_utils import direct_match, proximity_match, sites_by_captive_method

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "captive_power"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"


def build_fct_captive_steel(
    steel_path: Path | str = DATA_DIR / "gem_steel_plants.csv",
    sites_path: Path | str = PROCESSED_DIR / "dim_sites.csv",
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Spatial-join GEM steel plants against site centroids within buffer_km."""
    steel_path = Path(steel_path)
    if not steel_path.exists():
        print(f"  Steel data not found at {steel_path}")
        return pd.DataFrame()

    df = pd.read_csv(steel_path)
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    df["is_chinese_owned"] = df["parent_company"].astype(str).str.lower().str.contains("china")

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
        prox = prox[~prox["plant_name"].isin(direct["plant_name"])]

    matched = pd.concat([prox, direct], ignore_index=True)

    return pd.DataFrame(
        {
            "plant_name": matched.get("plant_name", ""),
            "latitude": matched["latitude"],
            "longitude": matched["longitude"],
            "capacity_tpa": matched.get("capacity_tpa"),
            "technology": matched.get("technology", ""),
            "status": matched.get("status", ""),
            "province": matched.get("province", ""),
            "parent_company": matched.get("parent_company", ""),
            "is_chinese_owned": matched["is_chinese_owned"],
            "site_id": matched["site_id"],
            "dist_to_site_km": matched["dist_km"],
        }
    )


def build_captive_steel_summary(plant_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate steel plants per site for scorecard enrichment."""
    if plant_df is None:
        plant_df = build_fct_captive_steel()
    if plant_df.empty:
        return pd.DataFrame()

    matched = plant_df[plant_df["site_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("site_id")
        .agg(
            steel_plant_count=("plant_name", "count"),
            steel_capacity_tpa=("capacity_tpa", "sum"),
            steel_plants=("plant_name", lambda x: "; ".join(x.unique())),
            steel_has_chinese_ownership=("is_chinese_owned", "any"),
            steel_dominant_technology=(
                "technology",
                lambda x: x.mode().iloc[0] if not x.mode().empty else "",
            ),
        )
        .reset_index()
    )
    return summary


if __name__ == "__main__":
    df = build_fct_captive_steel()
    print(f"Total steel plants: {len(df)}")
    print(f"Matched to sites: {df['site_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_steel.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_steel_summary(df)
        if not summary.empty:
            summary_out = PROCESSED_DIR / "fct_captive_steel_summary.csv"
            summary.to_csv(summary_out, index=False)
            print(f"Saved summary to {summary_out}")
            print(f"\nPer-site summary ({len(summary)} sites):")
            print(summary.to_string(index=False))
