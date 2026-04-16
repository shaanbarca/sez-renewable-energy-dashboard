# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: GEM steel plant spatial join against KEK polygons.

Source: Global Energy Monitor Global Iron and Steel Plant Tracker
URL: https://globalenergymonitor.org/projects/global-iron-and-steel-tracker/

Produces per-plant rows with site_id (null if outside all sites + 50km buffer),
plus per-KEK aggregates for scorecard enrichment and CBAM calculations.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "captive_power"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def build_fct_captive_steel(
    steel_path: Path | str = DATA_DIR / "gem_steel_plants.csv",
    sites_path: Path | str = PROCESSED_DIR / "dim_sites.csv",
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Spatial-join GEM steel plants against KEK centroids within buffer_km."""
    steel_path = Path(steel_path)
    if not steel_path.exists():
        print(f"  Steel data not found at {steel_path}")
        return pd.DataFrame()

    df = pd.read_csv(steel_path)
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()

    sites_path = Path(sites_path)
    if not sites_path.exists():
        print(f"  dim_sites not found at {sites_path}")
        return pd.DataFrame()

    keks = pd.read_csv(sites_path)
    kek_points = [
        {"site_id": r["site_id"], "lat": r["latitude"], "lon": r["longitude"]}
        for _, r in keks.iterrows()
        if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))
    ]

    rows = []
    for _, s in df.iterrows():
        best_kek = None
        best_dist = float("inf")
        for kek in kek_points:
            d = _haversine_km(s["latitude"], s["longitude"], kek["lat"], kek["lon"])
            if d < best_dist:
                best_dist = d
                best_kek = kek["site_id"]

        is_chinese = "china" in str(s.get("parent_company", "")).lower()

        rows.append(
            {
                "plant_name": s.get("plant_name", ""),
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "capacity_tpa": s.get("capacity_tpa"),
                "technology": s.get("technology", ""),
                "status": s.get("status", ""),
                "province": s.get("province", ""),
                "parent_company": s.get("parent_company", ""),
                "is_chinese_owned": is_chinese,
                "site_id": best_kek if best_dist <= buffer_km else None,
                "dist_to_site_km": round(best_dist, 1) if best_dist <= buffer_km else None,
            }
        )

    return pd.DataFrame(rows)


def build_captive_steel_summary(plant_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate steel plants per KEK for scorecard enrichment."""
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
            print(f"\nPer-KEK summary ({len(summary)} KEKs):")
            print(summary.to_string(index=False))
