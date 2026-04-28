"""Geospatial layer and KEK-specific endpoints."""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from src.assumptions import (
    BASE_WACC_DECIMAL,
    HOSTING_CAPACITY_AVAILABILITY_PCT,
    SUBSTATION_UTILIZATION_PCT,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
)
from src.dash.constants import RUPTL_REGION_COLORS
from src.dash.map_layers import (
    filter_substations_near_point,
    get_kek_polygon_by_id,
    get_within_boundary_buildable,
    polygon_bbox,
)
from src.model.basic_model import (
    capacity_assessment,
    capacity_factor_from_pvout,
    grid_connection_cost_per_kw,
    lcoe_solar,
    new_transmission_cost_per_kw,
    substation_upgrade_cost_per_kw,
)
from src.model.columns import Col

router = APIRouter()

# Valid layer names and their types
_POINT_LAYERS = {
    "substations",
    "industrial",
    "nickel_smelters",
    "captive_coal",
    "steel_plants",
    "cement_plants",
}
_GEOJSON_LAYERS = {
    "site_polygons",
    "kek_polygons",  # alias — same data as site_polygons; frontend uses this key
    "industrial_polygons",  # OSM landuse=industrial / man_made=works for non-KEK plants
    "peatland",
    "protected_forest",
    "grid_lines",
    "buildable_polygons",
    "wind_buildable_polygons",
}
_RASTER_LAYERS = {"pvout", "wind"}
_ALL_LAYERS = _POINT_LAYERS | _GEOJSON_LAYERS | _RASTER_LAYERS


# NOTE: /layers/infrastructure must be defined BEFORE /layers/{layer_name}
# so FastAPI matches the specific route first.


@router.get("/layers/infrastructure")
def get_infrastructure():
    """Return all infrastructure markers flattened with site_id."""
    from src.api.main import infrastructure  # noqa: PLC0415 — avoid circular import (main ← routes)

    markers = []
    for site_id, items in infrastructure.items():
        for item in items:
            markers.append(
                {
                    "site_id": site_id,
                    "lat": item["lat"],
                    "lon": item["lon"],
                    "title": item["title"],
                    "category": item["category"],
                }
            )

    return {"markers": markers}


@router.get("/layers/{layer_name}")
def get_layer(layer_name: str):
    """Return a cached geospatial layer by name."""
    from src.api.main import layers  # noqa: PLC0415 — avoid circular import (main ← routes)

    if layer_name not in _ALL_LAYERS:
        raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")

    data = layers.get(layer_name)

    if layer_name in _POINT_LAYERS:
        points = data if data else []
        return {"points": points}

    if layer_name in _GEOJSON_LAYERS:
        if data is None:
            raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' data not available")
        return data

    if layer_name in _RASTER_LAYERS:
        if data is None:
            raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' data not available")
        image_url, coordinates = data
        # coordinates is [[lon_min, lat_max], [lon_max, lat_max], [lon_max, lat_min], [lon_min, lat_min]]
        lat_min = coordinates[2][1]
        lat_max = coordinates[0][1]
        lon_min = coordinates[0][0]
        lon_max = coordinates[1][0]
        return {
            "image_url": image_url,
            "bounds": [[lat_min, lon_min], [lat_max, lon_max]],
        }

    raise HTTPException(status_code=404, detail=f"Layer '{layer_name}' not found")


@router.get("/site/{site_id}/polygon")
def get_site_polygon(site_id: str):
    """Return a single site polygon feature with bounding box."""
    feature = get_kek_polygon_by_id(site_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' polygon not found")

    min_lon, min_lat, max_lon, max_lat, center_lat, center_lon = polygon_bbox(feature)
    return {
        "feature": feature,
        "bbox": {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        },
        "center": {
            "lat": center_lat,
            "lon": center_lon,
        },
    }


@router.get("/site/{site_id}/buildable")
def get_site_buildable(site_id: str):
    """Return buildable polygon fragments clipped to a site boundary."""
    result = get_within_boundary_buildable(site_id)
    if result is None:
        return {"type": "FeatureCollection", "features": []}
    return result


# ─── Rooftop solar layers (v4.1) ────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUILDINGS_PARQUET = _REPO_ROOT / "data" / "processed" / "sites_buildings_filtered.parquet"
_TILES_PARQUET = _REPO_ROOT / "data" / "processed" / "sites_rooftop_tiles.parquet"


@lru_cache(maxsize=1)
def _load_buildings_parquet() -> gpd.GeoDataFrame | None:
    """Cached load of the Layer 2 buildings parquet. Returns None if missing
    (graceful degradation — endpoint returns empty FeatureCollection)."""
    if not _BUILDINGS_PARQUET.exists():
        return None
    return gpd.read_parquet(_BUILDINGS_PARQUET)


@lru_cache(maxsize=1)
def _load_tiles_parquet() -> gpd.GeoDataFrame | None:
    """Cached load of the Layer 2.5 tiles parquet."""
    if not _TILES_PARQUET.exists():
        return None
    return gpd.read_parquet(_TILES_PARQUET)


@router.get("/site/{site_id}/buildings")
def get_site_buildings(site_id: str):
    """Return GoB v3 building footprints inside a site's 2 km buffer.

    Renders as the gray "what was detected" layer beneath the rooftop tiles.
    Empty FeatureCollection if no buildings (e.g. post-2023 site or tourism
    KEK) — frontend should show the missing-data tooltip from the
    fct_site_solar_potential row's `building_data_reason_flagged`.
    """
    gdf = _load_buildings_parquet()
    if gdf is None:
        return {"type": "FeatureCollection", "features": []}
    site_buildings = gdf[gdf["site_id"] == site_id]
    if site_buildings.empty:
        return {"type": "FeatureCollection", "features": []}
    # Slim payload — drop columns the frontend doesn't render
    keep = ["building_id", "area_in_meters", "confidence", "source_name"]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {k: row[k] for k in keep},
            }
            for _, row in site_buildings.iterrows()
        ],
    }


@router.get("/site/{site_id}/rooftop-tiles")
def get_site_rooftop_tiles(site_id: str):
    """Return panel-tile rectangles for the rooftop solar map layer.

    Each feature is a 6m × 4m tile rectangle in EPSG:4326. Properties:
        tile_idx        — per-building index (0-based)
        cluster_id      — DBSCAN cluster (50m radius) for click-aggregation
        building_id     — parent building (source-prefixed string)
        panels_in_tile  — constant (default 6)
        tile_kw_dc      — per-tile DC nameplate (default 2.4)
        tile_kw_ac      — per-tile AC after thermal derate (default 2.11)

    Frontend should render at zoom ≥ 14 only — under that, fall back to the
    building outline layer. See spec §3.6 F9 + §3.9 (responsive: outlines-only
    on mobile).
    """
    gdf = _load_tiles_parquet()
    if gdf is None:
        return {"type": "FeatureCollection", "features": []}
    site_tiles = gdf[gdf["site_id"] == site_id]
    if site_tiles.empty:
        return {"type": "FeatureCollection", "features": []}
    keep = [
        "tile_idx",
        "cluster_id",
        "building_id",
        "panels_in_tile",
        "tile_kw_dc",
        "tile_kw_ac",
    ]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {k: row[k] for k in keep},
            }
            for _, row in site_tiles.iterrows()
        ],
    }


@router.get("/site/{site_id}/substations")
def get_site_substations(site_id: str, radius_km: float = Query(default=50.0, ge=0)):
    """Return substations near a KEK, with nearest marked and top 3 costed."""
    from src.api.main import (  # noqa: PLC0415 — avoid circular import (main ← routes)
        resource_df,
        tables,
    )

    dim_sites = tables.get("dim_sites")
    if dim_sites is None:
        raise HTTPException(status_code=500, detail="dim_sites not loaded")

    site_row = dim_sites[dim_sites["site_id"] == site_id]
    if site_row.empty:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found")

    lat = float(site_row.iloc[0]["latitude"])
    lon = float(site_row.iloc[0]["longitude"])

    nearby = filter_substations_near_point(lat, lon, radius_km)

    # Sort by distance and mark nearest
    nearby.sort(key=lambda s: s["dist_km"])
    for i, s in enumerate(nearby):
        s["is_nearest"] = i == 0

    # --- M15: Compute per-substation costs for top 3 ---
    # Get KEK resource data for cost computation
    res_row = (
        resource_df[resource_df["site_id"] == site_id] if not resource_df.empty else pd.DataFrame()
    )
    solar_mwp = None
    pvout_annual = None
    solar_lat = None
    solar_lon = None
    utilization_pct = SUBSTATION_UTILIZATION_PCT

    anchor_name: str | None = None
    if not res_row.empty:
        r = res_row.iloc[0]
        # V3.7: prefer anchored project scale; fall back to 50km envelope for
        # pre-anchor rows (wind-only, industrial sites without picker output).
        anchor_mwp_val = r.get("project_scale_solar_mwp")
        envelope_mwp_val = r.get(Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM)
        if pd.notna(anchor_mwp_val):
            solar_mwp = float(anchor_mwp_val)
        elif pd.notna(envelope_mwp_val):
            solar_mwp = float(envelope_mwp_val)
        # Per-site proxy-aware utilization — mirror build_fct_substation_proximity
        # derating so top-3 comparison matches the scorecard. Note: this applies
        # the KEK's nearest-substation source to all 3 candidates; strictly each
        # candidate could have its own source, but substations in the same area
        # tend to share voltage class — acceptable approximation.
        cap_source = r.get("nearest_substation_capacity_source")
        cap_source_str = str(cap_source) if pd.notna(cap_source) else ""
        if cap_source_str.startswith("proxy_"):
            utilization_pct = 1.0 - HOSTING_CAPACITY_AVAILABILITY_PCT
        # Column is pvout_best_50km (annual kWh/kWp/yr), fallback to pvout_centroid
        pvout_val = (
            r.get("pvout_best_50km")
            if pd.notna(r.get("pvout_best_50km"))
            else r.get("pvout_centroid")
        )
        pvout_annual = float(pvout_val) if pd.notna(pvout_val) else None
        solar_lat = (
            float(r["best_solar_site_lat"]) if pd.notna(r.get("best_solar_site_lat")) else None
        )
        solar_lon = (
            float(r["best_solar_site_lon"]) if pd.notna(r.get("best_solar_site_lon")) else None
        )
        anchor_val = r.get("chosen_anchor_substation_name")
        if pd.notna(anchor_val):
            anchor_name = str(anchor_val)

    # Mark the picker's anchor substation (the one that co-chose the amber polygon).
    # Falls through to is_nearest when no anchor exists (fallback picker).
    for s in nearby:
        s["is_anchor"] = anchor_name is not None and s["name"] == anchor_name

    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in km."""
        la1, lo1 = math.radians(lat1), math.radians(lon1)
        la2, lo2 = math.radians(lat2), math.radians(lon2)
        dlat, dlon = la2 - la1, lo2 - lo1
        a = math.sin(dlat / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dlon / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(a))

    for rank_idx, s in enumerate(nearby[:3]):
        s["rank"] = rank_idx + 1

        # Distance from solar site to this substation
        if solar_lat is not None and solar_lon is not None:
            dist_solar = round(_haversine(solar_lat, solar_lon, s["lat"], s["lon"]), 1)
        else:
            dist_solar = s["dist_km"]  # fallback: use KEK centroid distance
        s["dist_solar_km"] = dist_solar

        # Parse capacity_mva (may be string or number)
        cap_mva_raw = s.get("capacity_mva")
        cap_mva = None
        if cap_mva_raw is not None and cap_mva_raw != "":
            try:
                cap_mva = float(cap_mva_raw)
            except (ValueError, TypeError):
                pass

        # Capacity assessment
        ca_result, available = capacity_assessment(cap_mva, solar_mwp, utilization_pct)
        s["available_capacity_mva"] = available
        s["capacity_assessment"] = ca_result

        # Connection cost (solar → this substation)
        conn_cost = grid_connection_cost_per_kw(dist_solar)
        s["connection_cost_per_kw"] = round(conn_cost, 1)

        # Upgrade cost
        upgrade = substation_upgrade_cost_per_kw(cap_mva, solar_mwp, utilization_pct)
        s["upgrade_cost_per_kw"] = round(upgrade, 1)

        # Transmission cost: only if this substation differs from KEK's nearest
        # and would require a new line
        trans_cost = 0.0
        if rank_idx > 0 and nearby[0].get("dist_km", 0) > 0:
            # Inter-substation distance approximation: distance between this and nearest
            inter_dist = _haversine(nearby[0]["lat"], nearby[0]["lon"], s["lat"], s["lon"])
            if solar_mwp and solar_mwp > 0:
                trans_cost = new_transmission_cost_per_kw(inter_dist, solar_mwp)
        s["transmission_cost_per_kw"] = round(trans_cost, 1)

        # Total grid CAPEX
        total = conn_cost + upgrade + trans_cost
        s["total_grid_capex_per_kw"] = round(total, 1)

        # LCOE estimate with this substation's grid costs
        if pvout_annual and pvout_annual > 0:
            try:
                cf = capacity_factor_from_pvout(pvout_annual)
                # conn_cost already includes fixed $80/kW; don't double-count
                effective_capex = TECH006_CAPEX_USD_PER_KW + total
                lcoe_est = lcoe_solar(
                    effective_capex,
                    TECH006_FOM_USD_PER_KW_YR,
                    BASE_WACC_DECIMAL,
                    TECH006_LIFETIME_YR,
                    cf,
                )
                s["lcoe_estimate_usd_mwh"] = round(lcoe_est, 1)
            except (ValueError, ZeroDivisionError):
                s["lcoe_estimate_usd_mwh"] = None
        else:
            s["lcoe_estimate_usd_mwh"] = None

    # Substations beyond top 3 get rank=None
    for s in nearby[3:]:
        s["rank"] = None
        s["dist_solar_km"] = None
        s["available_capacity_mva"] = None
        s["capacity_assessment"] = None
        s["connection_cost_per_kw"] = None
        s["upgrade_cost_per_kw"] = None
        s["transmission_cost_per_kw"] = None
        s["total_grid_capex_per_kw"] = None
        s["lcoe_estimate_usd_mwh"] = None

    # Clean any NaN/inf values for JSON serialization
    for s in nearby:
        for k, v in s.items():
            if isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
                s[k] = None

    return {"substations": nearby}


@router.get("/ruptl-metrics")
def get_ruptl_metrics():
    """Return RUPTL pipeline data and region color mapping."""
    from src.api.main import tables  # noqa: PLC0415 — avoid circular import (main ← routes)

    ruptl_df = tables["fct_ruptl_pipeline"]
    records = ruptl_df.to_dict(orient="records")
    # Clean NaN for JSON
    clean_records = [
        {
            k: (None if isinstance(v, float) and (np.isnan(v) or np.isinf(v)) else v)
            for k, v in row.items()
        }
        for row in records
    ]

    return {
        "pipeline": clean_records,
        "region_colors": RUPTL_REGION_COLORS,
    }
