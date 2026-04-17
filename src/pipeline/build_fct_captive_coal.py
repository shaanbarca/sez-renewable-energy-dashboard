# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Pipeline: GEM captive coal plant spatial join against site polygons.

Source: Global Energy Monitor — Global Coal Plant Tracker (CC BY 4.0)
URL: https://globalenergymonitor.org/projects/global-coal-plant-tracker/
Data mirror: KAPSARC OpenDataSoft portal

Produces per-plant rows with site_id (null if outside all sites + 50km buffer),
plus per-site aggregates for scorecard enrichment.

Uses SiteTypeConfig.captive_power_method dispatch: KEK/KI sites use haversine
proximity matching; standalone/cluster sites use direct site_id matching
(no-op today; activates when plant CSVs gain site_id in Step 10).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.pipeline.geo_utils import direct_match, proximity_match, sites_by_captive_method

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


def _is_captive(row: pd.Series) -> bool:
    """Heuristic: check if plant name/parent suggests captive industrial power."""
    text = f"{row.get('plant', '')} {row.get('parent', '')} {row.get('unit', '')}"
    return bool(_CAPTIVE_KEYWORDS.search(text))


def build_fct_captive_coal(
    gem_path: Path | str = DATA_DIR / "gem_coal_plant_tracker_indonesia.csv",
    sites_path: Path | str = PROCESSED_DIR / "dim_sites.csv",
    buffer_km: float = 50.0,
    include_all: bool = False,
) -> pd.DataFrame:
    """Load GEM coal data, filter to captive/industrial, spatial-join against sites.

    Parameters
    ----------
    include_all : bool
        If True, include all Indonesian plants (not just captive). Default False.

    Returns DataFrame with one row per plant: plant_name, lat, lon,
    capacity_mw, status, parent, is_captive, site_id, dist_to_site_km.
    """
    gem_path = Path(gem_path)
    if not gem_path.exists():
        print(f"  GEM data not found at {gem_path} — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.read_csv(gem_path)
    df = df[df["latitude"].notna() & df["longitude"].notna()].copy()
    df["latitude"] = df["latitude"].astype(float)
    df["longitude"] = df["longitude"].astype(float)

    df["is_captive"] = df.apply(_is_captive, axis=1)

    if not include_all:
        df = df[df["is_captive"]].copy()

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

    sites_path = Path(sites_path)
    if not sites_path.exists():
        print(f"  dim_sites not found at {sites_path}")
        return pd.DataFrame()

    sites = pd.read_csv(sites_path)

    prox_sites = sites_by_captive_method(sites, "proximity")
    direct_sites = sites_by_captive_method(sites, "direct")

    prox = proximity_match(prox_sites, plants, buffer_km=buffer_km)
    direct = direct_match(direct_sites, plants)
    if not direct.empty:
        direct["dist_km"] = 0.0
        prox = prox[~prox["plant"].isin(direct["plant"])]

    matched = pd.concat([prox, direct], ignore_index=True)

    return pd.DataFrame(
        {
            "plant_name": matched["plant"],
            "latitude": matched["latitude"],
            "longitude": matched["longitude"],
            "capacity_mw": matched["capacity_mw"],
            "unit_count": matched["unit_count"],
            "status": matched["status"],
            "parent": matched["parent"],
            "province": matched.get("subnational_unit", ""),
            "is_captive": matched["is_captive"],
            "site_id": matched["site_id"],
            "dist_to_site_km": matched["dist_km"],
        }
    )


def build_captive_coal_summary(
    coal_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate captive coal data per site for scorecard enrichment.

    Returns one row per site with: captive_coal_count, captive_coal_mw,
    captive_coal_plants (names).
    """
    if coal_df is None:
        coal_df = build_fct_captive_coal()

    if coal_df.empty:
        return pd.DataFrame()

    matched = coal_df[coal_df["site_id"].notna()].copy()
    if matched.empty:
        return pd.DataFrame()

    summary = (
        matched.groupby("site_id")
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
    print(f"Matched to sites: {df['site_id'].notna().sum()}")
    if not df.empty:
        out = PROCESSED_DIR / "fct_captive_coal.csv"
        df.to_csv(out, index=False)
        print(f"Saved to {out}")

        summary = build_captive_coal_summary(df)
        if not summary.empty:
            print(f"\nPer-site summary ({len(summary)} sites):")
            print(summary.to_string(index=False))
