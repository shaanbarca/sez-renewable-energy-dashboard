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


def apply_contractual_overrides(
    matched_plants: pd.DataFrame,
    overrides_df: pd.DataFrame,
    sites_df: pd.DataFrame,
    plant_name_col: str = "plant",
    site_id_col: str = "site_id",
    *,
    site_lat_col: str = "latitude",
    site_lon_col: str = "longitude",
    plant_lat_col: str = "latitude",
    plant_lon_col: str = "longitude",
) -> pd.DataFrame:
    """F12 (2026-05-09): apply contractual site-id overrides to a spatial match.

    Sumatran mine-mouth coal plants supplying smelters > 50 km away are common.
    Pure haversine matching misses these; this layer re-routes such plants to
    their contractual site (or pulls them in if they were unmatched).

    Match key is the plant name (case-insensitive, whitespace-normalised).
    Coordinates in the override file are advisory — only used to log warnings
    when an override matches a plant whose GEM coordinates differ by > 1 km.

    Adds two provenance columns to every row:
      - `captive_match_method`: 'spatial' (haversine) or 'contractual' (override)
      - `captive_match_source`: source citation from the override (or None)

    Override site_id resolution:
      - If override site_id is in sites_df → applied; recomputes `dist_km`
        from the site's coordinates to the plant's coordinates
      - If override site_id is NOT in sites_df → row left untouched, warning
        printed to stderr (don't silently swallow typos)

    Returns a copy of matched_plants with same shape + the two new columns.
    Rows that don't match any override get `captive_match_method = 'spatial'`.
    """
    result = matched_plants.copy()
    result["captive_match_method"] = "spatial"
    result["captive_match_source"] = None

    if overrides_df is None or overrides_df.empty or matched_plants.empty:
        return result

    site_lookup = {
        r[site_id_col]: (r[site_lat_col], r[site_lon_col])
        for _, r in sites_df.iterrows()
        if pd.notna(r.get(site_lat_col)) and pd.notna(r.get(site_lon_col))
    }

    def _norm(name: object) -> str:
        return str(name).strip().lower() if pd.notna(name) else ""

    plant_name_index = {_norm(n): idx for idx, n in result[plant_name_col].items()}

    for _, override in overrides_df.iterrows():
        ov_site_id = override.get(site_id_col)
        ov_plant_name = _norm(override.get("plant_name"))
        ov_source = override.get("source")

        if not ov_plant_name or pd.isna(ov_site_id):
            continue
        if ov_site_id not in site_lookup:
            print(
                f"  apply_contractual_overrides: site_id '{ov_site_id}' not in dim_sites — skipping override for plant '{override.get('plant_name')}'"
            )
            continue
        if ov_plant_name not in plant_name_index:
            print(
                f"  apply_contractual_overrides: plant '{override.get('plant_name')}' not in plants_df (likely filtered out as non-captive) — skipping"
            )
            continue

        row_idx = plant_name_index[ov_plant_name]
        plant_lat = result.at[row_idx, plant_lat_col]
        plant_lon = result.at[row_idx, plant_lon_col]
        site_lat, site_lon = site_lookup[ov_site_id]
        dist_km = round(haversine_km(plant_lat, plant_lon, site_lat, site_lon), 1)

        # Defensive: warn if override coordinates disagree with GEM by > 1 km
        ov_lat = override.get("plant_lat")
        ov_lon = override.get("plant_lon")
        if pd.notna(ov_lat) and pd.notna(ov_lon):
            coord_drift = haversine_km(plant_lat, plant_lon, ov_lat, ov_lon)
            if coord_drift > 1.0:
                print(
                    f"  apply_contractual_overrides: coord drift {coord_drift:.1f}km for plant '{override.get('plant_name')}' — override CSV may be stale vs GEM"
                )

        result.at[row_idx, site_id_col] = ov_site_id
        result.at[row_idx, "dist_km"] = dist_km
        result.at[row_idx, "captive_match_method"] = "contractual"
        result.at[row_idx, "captive_match_source"] = ov_source

    return result


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
