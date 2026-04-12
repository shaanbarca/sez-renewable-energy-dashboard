# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: CGSP nickel smelter spatial join against KEK polygons.

Source: China-Global South Project Nickel Tracker (CC license)
URL: https://nickel.chinaglobalsouth.com/

Produces per-smelter rows with kek_id (null if outside all KEKs + 50km buffer),
plus per-KEK aggregates for scorecard enrichment.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "captive_power"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def build_fct_captive_nickel(
    cgsp_path: Path | str = DATA_DIR / "cgsp_nickel_tracker.csv",
    kek_path: Path | str = PROCESSED_DIR / "dim_kek.csv",
    kek_polygons_path: Path | str = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson",
    buffer_km: float = 50.0,
) -> pd.DataFrame:
    """Load CGSP nickel data and spatial-join against KEKs.

    Returns DataFrame with one row per smelter: project_name, lat, lon,
    project_type, capacity, status, owner, kek_id (nearest within buffer), dist_km.
    """
    cgsp_path = Path(cgsp_path)
    if not cgsp_path.exists():
        print(f"  CGSP data not found at {cgsp_path} — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.read_csv(cgsp_path)

    # Filter to processing (smelter) projects with coordinates
    df = df[df["parent_project_type"] == "Processing"].copy()
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)

    # Load KEK centroids
    kek_path = Path(kek_path)
    if not kek_path.exists():
        print(f"  dim_kek not found at {kek_path}")
        return pd.DataFrame()

    keks = pd.read_csv(kek_path)
    kek_points = [
        {"kek_id": r["kek_id"], "lat": r["latitude"], "lon": r["longitude"]}
        for _, r in keks.iterrows()
        if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))
    ]

    # For each smelter, find nearest KEK within buffer
    rows = []
    for _, s in df.iterrows():
        best_kek = None
        best_dist = float("inf")
        for kek in kek_points:
            d = _haversine_km(s["latitude"], s["longitude"], kek["lat"], kek["lon"])
            if d < best_dist:
                best_dist = d
                best_kek = kek["kek_id"]

        # Parse ownership
        ownership = s.get("country_ownership", "")
        is_chinese = "China" in str(ownership) if pd.notna(ownership) else False

        rows.append(
            {
                "project_name": s.get("project_name", ""),
                "project_type": s.get("project_type", ""),
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "capacity_tons": s.get("capacity"),
                "capacity_unit": s.get("capacity_unit", "ton"),
                "cost_usd": s.get("cost")
                if pd.notna(s.get("cost")) and s.get("cost") != "-"
                else None,
                "status": s.get("status", ""),
                "province": s.get("province_city", ""),
                "shareholder": s.get("shareholder_ownership", ""),
                "is_chinese_owned": is_chinese,
                "esg_ecological": s.get("esg_impact_ecological", ""),
                "esg_social": s.get("esg_impact_social", ""),
                "kek_id": best_kek if best_dist <= buffer_km else None,
                "dist_to_kek_km": round(best_dist, 1) if best_dist <= buffer_km else None,
            }
        )

    return pd.DataFrame(rows)


def build_captive_nickel_summary(
    smelter_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate smelter data per KEK for scorecard enrichment.

    Returns one row per KEK with: nickel_smelter_count, nickel_projects (names),
    dominant_process_type, has_chinese_ownership.
    """
    if smelter_df is None:
        smelter_df = build_fct_captive_nickel()

    if smelter_df.empty:
        return pd.DataFrame()

    matched = smelter_df[smelter_df["kek_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("kek_id")
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
    print(f"Matched to KEKs: {df['kek_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_nickel.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_nickel_summary(df)
        if not summary.empty:
            print(f"\nPer-KEK summary ({len(summary)} KEKs):")
            print(summary.to_string(index=False))
