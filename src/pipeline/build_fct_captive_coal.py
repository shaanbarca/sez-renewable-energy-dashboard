# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: GEM captive coal plant spatial join against KEK polygons.

Source: Global Energy Monitor — Global Coal Plant Tracker (CC BY 4.0)
URL: https://globalenergymonitor.org/projects/global-coal-plant-tracker/
Data mirror: KAPSARC OpenDataSoft portal

Produces per-plant rows with kek_id (null if outside all KEKs + 50km buffer),
plus per-KEK aggregates for scorecard enrichment.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "captive_power"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"

# Keywords that indicate captive/industrial power (not PLN grid plants)
_CAPTIVE_KEYWORDS = re.compile(
    r"nickel|smelter|steel|cement|alumin|mining|mineral|industrial|chemical|paper|pulp|"
    r"delong|tsingshan|virtue dragon|obsidian|imip|iwip|obi|weda bay|"
    r"nanshan|lygend|harita|huayou|gunbuster|sulawesi mining",
    re.IGNORECASE,
)


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


def _is_captive(row: pd.Series) -> bool:
    """Heuristic: check if plant name/parent suggests captive industrial power."""
    text = f"{row.get('plant', '')} {row.get('parent', '')} {row.get('unit', '')}"
    return bool(_CAPTIVE_KEYWORDS.search(text))


def build_fct_captive_coal(
    gem_path: Path | str = DATA_DIR / "gem_coal_plant_tracker_indonesia.csv",
    kek_path: Path | str = PROCESSED_DIR / "dim_kek.csv",
    buffer_km: float = 50.0,
    include_all: bool = False,
) -> pd.DataFrame:
    """Load GEM coal data, filter to captive/industrial, spatial-join against KEKs.

    Parameters
    ----------
    include_all : bool
        If True, include all Indonesian plants (not just captive). Default False.

    Returns DataFrame with one row per plant: plant_name, lat, lon,
    capacity_mw, status, parent, is_captive, kek_id, dist_km.
    """
    gem_path = Path(gem_path)
    if not gem_path.exists():
        print(f"  GEM data not found at {gem_path} — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.read_csv(gem_path)
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)

    # Tag captive plants
    df["is_captive"] = df.apply(_is_captive, axis=1)

    if not include_all:
        df = df[df["is_captive"]].copy()

    # Aggregate to plant level (sum unit capacities)
    plants = (
        df.groupby("plant")
        .agg(
            latitude=("latitude", "first"),
            longitude=("longitude", "first"),
            capacity_mw=("capacity_mw", "sum"),
            status=("status", lambda x: x.value_counts().index[0]),
            parent=("parent", "first"),
            unit_count=("unit", "count"),
            subnational_unit=("subnational_unit", "first"),
            is_captive=("is_captive", "first"),
        )
        .reset_index()
    )

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

    # For each plant, find nearest KEK within buffer
    rows = []
    for _, p in plants.iterrows():
        best_kek = None
        best_dist = float("inf")
        for kek in kek_points:
            d = _haversine_km(p["latitude"], p["longitude"], kek["lat"], kek["lon"])
            if d < best_dist:
                best_dist = d
                best_kek = kek["kek_id"]

        rows.append(
            {
                "plant_name": p["plant"],
                "latitude": p["latitude"],
                "longitude": p["longitude"],
                "capacity_mw": p["capacity_mw"],
                "unit_count": p["unit_count"],
                "status": p["status"],
                "parent": p["parent"],
                "province": p.get("subnational_unit", ""),
                "is_captive": p["is_captive"],
                "kek_id": best_kek if best_dist <= buffer_km else None,
                "dist_to_kek_km": round(best_dist, 1) if best_dist <= buffer_km else None,
            }
        )

    return pd.DataFrame(rows)


def build_captive_coal_summary(
    coal_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate captive coal data per KEK for scorecard enrichment.

    Returns one row per KEK with: captive_coal_count, captive_coal_mw,
    captive_coal_plants (names).
    """
    if coal_df is None:
        coal_df = build_fct_captive_coal()

    if coal_df.empty:
        return pd.DataFrame()

    matched = coal_df[coal_df["kek_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("kek_id")
        .agg(
            captive_coal_count=("plant_name", "count"),
            captive_coal_mw=("capacity_mw", "sum"),
            captive_coal_plants=("plant_name", lambda x: "; ".join(x.unique())),
        )
        .reset_index()
    )
    summary["captive_coal_mw"] = summary["captive_coal_mw"].round(0).astype(int)
    return summary


if __name__ == "__main__":
    df = build_fct_captive_coal()
    print(f"Captive coal plants: {len(df)}")
    print(f"Matched to KEKs: {df['kek_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_coal.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_coal_summary(df)
        if not summary.empty:
            print(f"\nPer-KEK summary ({len(summary)} KEKs):")
            print(summary.to_string(index=False))
