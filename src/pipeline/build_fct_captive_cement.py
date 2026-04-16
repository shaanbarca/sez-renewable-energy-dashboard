# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: GEM cement plant spatial join against KEK polygons.

Source: Global Energy Monitor Global Cement Plant Tracker
URL: https://globalenergymonitor.org/projects/global-cement-plant-tracker/

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


def build_fct_captive_cement(
    cement_path: Path | str = DATA_DIR / "gem_cement_plants.csv",
    sites_path: Path | str = PROCESSED_DIR / "dim_sites.csv",
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Spatial-join GEM cement plants against KEK centroids within buffer_km."""
    cement_path = Path(cement_path)
    if not cement_path.exists():
        print(f"  Cement data not found at {cement_path}")
        return pd.DataFrame()

    df = pd.read_csv(cement_path)
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
                "capacity_mtpa": s.get("capacity_mtpa"),
                "plant_type": s.get("plant_type", ""),
                "status": s.get("status", ""),
                "province": s.get("province", ""),
                "parent_company": s.get("parent_company", ""),
                "is_chinese_owned": is_chinese,
                "site_id": best_kek if best_dist <= buffer_km else None,
                "dist_to_site_km": round(best_dist, 1) if best_dist <= buffer_km else None,
            }
        )

    return pd.DataFrame(rows)


def build_captive_cement_summary(plant_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Aggregate cement plants per KEK for scorecard enrichment."""
    if plant_df is None:
        plant_df = build_fct_captive_cement()
    if plant_df.empty:
        return pd.DataFrame()

    matched = plant_df[plant_df["site_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("site_id")
        .agg(
            cement_plant_count=("plant_name", "count"),
            cement_capacity_mtpa=("capacity_mtpa", "sum"),
            cement_plants=("plant_name", lambda x: "; ".join(x.unique())),
            cement_has_chinese_ownership=("is_chinese_owned", "any"),
        )
        .reset_index()
    )
    return summary


if __name__ == "__main__":
    df = build_fct_captive_cement()
    print(f"Total cement plants: {len(df)}")
    print(f"Matched to sites: {df['site_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_cement.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_cement_summary(df)
        if not summary.empty:
            print(f"\nPer-KEK summary ({len(summary)} KEKs):")
            print(summary.to_string(index=False))
