# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
geo_utils — shared geospatial utilities for pipeline builders.

Extracts haversine_km, proximity_match, and direct_match from the 5 files
that previously duplicated this logic:
  - build_fct_captive_coal.py
  - build_fct_captive_steel.py
  - build_fct_captive_cement.py
  - build_fct_captive_nickel.py
  - build_fct_substation_proximity.py
"""

from __future__ import annotations

import math
from typing import Literal

import pandas as pd

from src.model.site_types import SITE_TYPES


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres.

    Uses the haversine formula. Accurate to ~0.5% for distances under 10,000 km.
    """
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


def proximity_match(
    sites_df: pd.DataFrame,
    plants_df: pd.DataFrame,
    buffer_km: float,
    site_id_col: str = "site_id",
    site_lat_col: str = "latitude",
    site_lon_col: str = "longitude",
    plant_lat_col: str = "latitude",
    plant_lon_col: str = "longitude",
) -> pd.DataFrame:
    """For each site, find the nearest plant within buffer_km.

    Returns a copy of plants_df with added columns:
      - `{site_id_col}`: matched site ID (or None if no match)
      - `dist_km`: distance to matched site in km (or None)

    Each plant is matched to its nearest site within the buffer.
    Plants outside the buffer of all sites get None for both columns.
    """
    if sites_df.empty or plants_df.empty:
        result = plants_df.copy()
        result[site_id_col] = None
        result["dist_km"] = None
        return result

    site_points = [
        {
            "id": r[site_id_col],
            "lat": r[site_lat_col],
            "lon": r[site_lon_col],
        }
        for _, r in sites_df.iterrows()
        if pd.notna(r.get(site_lat_col)) and pd.notna(r.get(site_lon_col))
    ]

    matched_ids = []
    matched_dists = []

    for _, plant in plants_df.iterrows():
        plat = plant[plant_lat_col]
        plon = plant[plant_lon_col]

        if pd.isna(plat) or pd.isna(plon):
            matched_ids.append(None)
            matched_dists.append(None)
            continue

        best_id = None
        best_dist = float("inf")

        for site in site_points:
            d = haversine_km(plat, plon, site["lat"], site["lon"])
            if d < best_dist:
                best_dist = d
                best_id = site["id"]

        if best_dist <= buffer_km:
            matched_ids.append(best_id)
            matched_dists.append(round(best_dist, 1))
        else:
            matched_ids.append(None)
            matched_dists.append(None)

    result = plants_df.copy()
    result[site_id_col] = matched_ids
    result["dist_km"] = matched_dists
    return result


def direct_match(
    sites_df: pd.DataFrame,
    plants_df: pd.DataFrame,
    site_id_col: str = "site_id",
    plant_id_col: str = "site_id",
) -> pd.DataFrame:
    """Match sites to plants by shared ID column.

    For standalone sites that ARE the plant, no proximity search needed.
    Returns plants_df rows where the plant's ID column matches a site's ID column.

    Returns empty DataFrame if either input is empty OR plants_df lacks plant_id_col
    (silent no-op for captive builders whose plant CSVs don't yet carry site_id).
    """
    if sites_df.empty or plants_df.empty:
        return pd.DataFrame(columns=plants_df.columns)

    if plant_id_col not in plants_df.columns:
        return pd.DataFrame(columns=plants_df.columns)

    valid_ids = set(sites_df[site_id_col].dropna())
    matched = plants_df[plants_df[plant_id_col].isin(valid_ids)].copy()
    return matched


def sites_by_captive_method(
    sites_df: pd.DataFrame,
    method: Literal["proximity", "direct"],
    site_type_col: str = "site_type",
) -> pd.DataFrame:
    """Return the subset of sites whose SiteTypeConfig.captive_power_method == method.

    If sites_df lacks a `site_type` column (e.g. legacy dim_kek), all sites are
    treated as proximity-type for back-compat.
    """
    matching_types = {
        st.value for st, cfg in SITE_TYPES.items() if cfg.captive_power_method == method
    }

    if site_type_col not in sites_df.columns:
        return sites_df if method == "proximity" else sites_df.iloc[0:0]

    return sites_df[sites_df[site_type_col].isin(matching_types)]
