"""Geospatial layer and KEK-specific endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.dash.constants import RUPTL_REGION_COLORS
from src.dash.map_layers import (
    filter_substations_near_point,
    get_kek_polygon_by_id,
    get_within_boundary_buildable,
    polygon_bbox,
)

router = APIRouter()

# Valid layer names and their types
_POINT_LAYERS = {"substations", "industrial", "nickel_smelters", "captive_coal"}
_GEOJSON_LAYERS = {
    "kek_polygons",
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
    """Return all infrastructure markers flattened with kek_id."""
    from src.api.main import infrastructure

    markers = []
    for kek_id, items in infrastructure.items():
        for item in items:
            markers.append(
                {
                    "kek_id": kek_id,
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
    from src.api.main import layers

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


@router.get("/kek/{kek_id}/polygon")
def get_kek_polygon(kek_id: str):
    """Return a single KEK polygon feature with bounding box."""
    feature = get_kek_polygon_by_id(kek_id)
    if feature is None:
        raise HTTPException(status_code=404, detail=f"KEK '{kek_id}' polygon not found")

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


@router.get("/kek/{kek_id}/buildable")
def get_kek_buildable(kek_id: str):
    """Return buildable polygon fragments clipped to a KEK boundary."""
    result = get_within_boundary_buildable(kek_id)
    if result is None:
        return {"type": "FeatureCollection", "features": []}
    return result


@router.get("/kek/{kek_id}/substations")
def get_kek_substations(kek_id: str, radius_km: float = Query(default=50.0, ge=0)):
    """Return substations near a KEK, with nearest marked and top 3 costed."""
    import math

    import numpy as np
    import pandas as pd

    from src.api.main import resource_df, tables
    from src.assumptions import (
        BASE_WACC_DECIMAL,
        TECH006_CAPEX_USD_PER_KW,
        TECH006_FOM_USD_PER_KW_YR,
        TECH006_LIFETIME_YR,
    )
    from src.model.basic_model import (
        capacity_assessment,
        capacity_factor_from_pvout,
        grid_connection_cost_per_kw,
        lcoe_solar,
        new_transmission_cost_per_kw,
        substation_upgrade_cost_per_kw,
    )

    dim_kek = tables.get("dim_kek")
    if dim_kek is None:
        raise HTTPException(status_code=500, detail="dim_kek not loaded")

    kek_row = dim_kek[dim_kek["kek_id"] == kek_id]
    if kek_row.empty:
        raise HTTPException(status_code=404, detail=f"KEK '{kek_id}' not found")

    lat = float(kek_row.iloc[0]["latitude"])
    lon = float(kek_row.iloc[0]["longitude"])

    nearby = filter_substations_near_point(lat, lon, radius_km)

    # Sort by distance and mark nearest
    nearby.sort(key=lambda s: s["dist_km"])
    for i, s in enumerate(nearby):
        s["is_nearest"] = i == 0

    # --- M15: Compute per-substation costs for top 3 ---
    # Get KEK resource data for cost computation
    res_row = (
        resource_df[resource_df["kek_id"] == kek_id] if not resource_df.empty else pd.DataFrame()
    )
    solar_mwp = None
    pvout_annual = None
    solar_lat = None
    solar_lon = None
    utilization_pct = 0.65  # default

    if not res_row.empty:
        r = res_row.iloc[0]
        solar_mwp = (
            float(r["max_captive_capacity_mwp"])
            if pd.notna(r.get("max_captive_capacity_mwp"))
            else None
        )
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
    import numpy as np

    from src.api.main import tables

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
