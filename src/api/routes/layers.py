"""Geospatial layer and KEK-specific endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from src.dash.constants import RUPTL_REGION_COLORS
from src.dash.map_layers import (
    filter_substations_near_point,
    get_kek_polygon_by_id,
    polygon_bbox,
)

router = APIRouter()

# Valid layer names and their types
_POINT_LAYERS = {"substations", "industrial"}
_GEOJSON_LAYERS = {"kek_polygons", "peatland", "protected_forest", "grid_lines"}
_RASTER_LAYERS = {"pvout", "wind", "buildable"}
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


@router.get("/kek/{kek_id}/substations")
def get_kek_substations(kek_id: str, radius_km: float = Query(default=50.0, ge=0)):
    """Return substations near a KEK, with nearest marked."""
    from src.api.main import tables

    dim_kek = tables.get("dim_kek")
    if dim_kek is None:
        raise HTTPException(status_code=500, detail="dim_kek not loaded")

    kek_row = dim_kek[dim_kek["kek_id"] == kek_id]
    if kek_row.empty:
        raise HTTPException(status_code=404, detail=f"KEK '{kek_id}' not found")

    lat = float(kek_row.iloc[0]["latitude"])
    lon = float(kek_row.iloc[0]["longitude"])

    nearby = filter_substations_near_point(lat, lon, radius_km)

    # Mark the nearest one
    if nearby:
        nearest_idx = min(range(len(nearby)), key=lambda i: nearby[i]["dist_km"])
        for i, s in enumerate(nearby):
            s["is_nearest"] = i == nearest_idx

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
