# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Geospatial map layers for the dashboard.

Loads and prepares overlay layers (substations, KEK boundaries, PVOUT raster,
wind raster, peatland) for toggling on the Plotly Mapbox map.
"""

from __future__ import annotations

import base64
import io
import json
import zipfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
LAYERS_CACHE_DIR = REPO_ROOT / "outputs" / "layers"

# ---------------------------------------------------------------------------
# Vector layer loaders
# ---------------------------------------------------------------------------


def load_substations() -> list[dict]:
    """Load PLN substation points from GeoJSON. Returns list of {lat, lon, name, voltage, capacity}."""
    path = DATA_DIR / "substation.geojson"
    if not path.exists():
        return []
    with open(path) as f:
        gj = json.load(f)

    stations = []
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [])
        if len(coords) >= 2:
            stations.append(
                {
                    "lon": coords[0],
                    "lat": coords[1],
                    "name": props.get("namobj", "Unknown"),
                    "voltage": props.get("teggi", ""),
                    "capacity_mva": props.get("kapgi", ""),
                    "regpln": props.get("regpln", ""),
                }
            )
    return stations


def load_nickel_smelters() -> list[dict]:
    """Load CGSP nickel smelter points from processed CSV.

    Returns list of {lat, lon, name, project_type, capacity_tons, cost_usd,
    shareholder, esg_ecological, esg_social, status, province,
    is_chinese_owned, kek_id, dist_to_kek_km}.
    """
    path = REPO_ROOT / "outputs" / "data" / "processed" / "fct_captive_nickel.csv"
    if not path.exists():
        # Fall back to raw data
        path = DATA_DIR / "captive_power" / "cgsp_nickel_tracker.csv"
        if not path.exists():
            return []
        import pandas as pd

        df = pd.read_csv(path)
        df = df[df["parent_project_type"] == "Processing"]
        df = df[df["latitude"].notna() & df["longitude"].notna()]
        return [
            {
                "lon": float(r["longitude"]),
                "lat": float(r["latitude"]),
                "name": r.get("project_name", "Unknown"),
                "project_type": r.get("project_type", ""),
                "capacity_tons": float(r["capacity"]) if pd.notna(r.get("capacity")) else None,
                "cost_usd": float(r["cost"])
                if pd.notna(r.get("cost")) and str(r.get("cost", "")).strip() not in ("", "-")
                else None,
                "shareholder": str(r.get("shareholder_ownership", ""))
                if pd.notna(r.get("shareholder_ownership"))
                else "",
                "esg_ecological": str(r.get("esg_impact_ecological", ""))
                if pd.notna(r.get("esg_impact_ecological"))
                else "",
                "esg_social": str(r.get("esg_impact_social", ""))
                if pd.notna(r.get("esg_impact_social"))
                else "",
                "status": r.get("status", ""),
                "province": r.get("province_city", ""),
                "is_chinese_owned": "China" in str(r.get("country_ownership", "")),
            }
            for _, r in df.iterrows()
        ]

    import pandas as pd

    df = pd.read_csv(path)
    results = []
    for _, r in df.iterrows():
        if not (pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))):
            continue
        results.append(
            {
                "lon": float(r["longitude"]),
                "lat": float(r["latitude"]),
                "name": str(r.get("project_name", "Unknown"))
                if pd.notna(r.get("project_name"))
                else "Unknown",
                "project_type": str(r.get("project_type", ""))
                if pd.notna(r.get("project_type"))
                else "",
                "capacity_tons": float(r["capacity_tons"])
                if pd.notna(r.get("capacity_tons"))
                else None,
                "cost_usd": float(r["cost_usd"]) if pd.notna(r.get("cost_usd")) else None,
                "shareholder": str(r.get("shareholder", ""))
                if pd.notna(r.get("shareholder"))
                else "",
                "esg_ecological": str(r.get("esg_ecological", ""))
                if pd.notna(r.get("esg_ecological"))
                else "",
                "esg_social": str(r.get("esg_social", "")) if pd.notna(r.get("esg_social")) else "",
                "status": str(r.get("status", "")) if pd.notna(r.get("status")) else "",
                "province": str(r.get("province", "")) if pd.notna(r.get("province")) else "",
                "is_chinese_owned": bool(r.get("is_chinese_owned", False))
                if pd.notna(r.get("is_chinese_owned"))
                else False,
                "kek_id": str(r["kek_id"]) if pd.notna(r.get("kek_id")) else None,
                "dist_to_kek_km": float(r["dist_to_kek_km"])
                if pd.notna(r.get("dist_to_kek_km"))
                else None,
            }
        )
    return results


def load_captive_coal() -> list[dict]:
    """Load GEM captive coal plant points from processed CSV.

    Returns list of {lat, lon, name, capacity_mw, status, parent, province,
    kek_id, dist_to_kek_km}.
    """
    path = REPO_ROOT / "outputs" / "data" / "processed" / "fct_captive_coal.csv"
    if not path.exists():
        return []

    import pandas as pd

    df = pd.read_csv(path)
    results = []
    for _, r in df.iterrows():
        if not (pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))):
            continue
        results.append(
            {
                "lon": float(r["longitude"]),
                "lat": float(r["latitude"]),
                "name": str(r.get("plant_name", "Unknown"))
                if pd.notna(r.get("plant_name"))
                else "Unknown",
                "capacity_mw": float(r["capacity_mw"]) if pd.notna(r.get("capacity_mw")) else 0,
                "unit_count": int(r.get("unit_count", 1)) if pd.notna(r.get("unit_count")) else 1,
                "status": str(r.get("status", "")) if pd.notna(r.get("status")) else "",
                "parent": str(r.get("parent", "")) if pd.notna(r.get("parent")) else "",
                "province": str(r.get("province", "")) if pd.notna(r.get("province")) else "",
                "kek_id": str(r["kek_id"]) if pd.notna(r.get("kek_id")) else None,
                "dist_to_kek_km": float(r["dist_to_kek_km"])
                if pd.notna(r.get("dist_to_kek_km"))
                else None,
            }
        )
    return results


def load_steel_plants() -> list[dict]:
    """Load GEM steel plant points from processed CSV."""
    path = REPO_ROOT / "outputs" / "data" / "processed" / "fct_captive_steel.csv"
    if not path.exists():
        return []

    import pandas as pd

    df = pd.read_csv(path)
    results = []
    for _, r in df.iterrows():
        if not (pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))):
            continue
        results.append(
            {
                "lon": float(r["longitude"]),
                "lat": float(r["latitude"]),
                "name": str(r.get("plant_name", "Unknown"))
                if pd.notna(r.get("plant_name"))
                else "Unknown",
                "capacity_tpa": float(r["capacity_tpa"]) if pd.notna(r.get("capacity_tpa")) else 0,
                "technology": str(r.get("technology", "")) if pd.notna(r.get("technology")) else "",
                "status": str(r.get("status", "")) if pd.notna(r.get("status")) else "",
                "parent_company": str(r.get("parent_company", ""))
                if pd.notna(r.get("parent_company"))
                else "",
                "province": str(r.get("province", "")) if pd.notna(r.get("province")) else "",
                "is_chinese_owned": bool(r.get("is_chinese_owned", False))
                if pd.notna(r.get("is_chinese_owned"))
                else False,
                "kek_id": str(r["kek_id"]) if pd.notna(r.get("kek_id")) else None,
                "dist_to_kek_km": float(r["dist_to_kek_km"])
                if pd.notna(r.get("dist_to_kek_km"))
                else None,
            }
        )
    return results


def load_cement_plants() -> list[dict]:
    """Load GEM cement plant points from processed CSV."""
    path = REPO_ROOT / "outputs" / "data" / "processed" / "fct_captive_cement.csv"
    if not path.exists():
        return []

    import pandas as pd

    df = pd.read_csv(path)
    results = []
    for _, r in df.iterrows():
        if not (pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))):
            continue
        results.append(
            {
                "lon": float(r["longitude"]),
                "lat": float(r["latitude"]),
                "name": str(r.get("plant_name", "Unknown"))
                if pd.notna(r.get("plant_name"))
                else "Unknown",
                "capacity_mtpa": float(r["capacity_mtpa"])
                if pd.notna(r.get("capacity_mtpa"))
                else 0,
                "plant_type": str(r.get("plant_type", "")) if pd.notna(r.get("plant_type")) else "",
                "status": str(r.get("status", "")) if pd.notna(r.get("status")) else "",
                "parent_company": str(r.get("parent_company", ""))
                if pd.notna(r.get("parent_company"))
                else "",
                "province": str(r.get("province", "")) if pd.notna(r.get("province")) else "",
                "is_chinese_owned": bool(r.get("is_chinese_owned", False))
                if pd.notna(r.get("is_chinese_owned"))
                else False,
                "kek_id": str(r["kek_id"]) if pd.notna(r.get("kek_id")) else None,
                "dist_to_kek_km": float(r["dist_to_kek_km"])
                if pd.notna(r.get("dist_to_kek_km"))
                else None,
            }
        )
    return results


def load_kek_polygons() -> dict | None:
    """Load KEK boundary polygons as raw GeoJSON dict for Choroplethmapbox."""
    path = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def get_kek_polygon_by_id(kek_id: str) -> dict | None:
    """Extract a single KEK polygon feature from the full GeoJSON by slug/kek_id.

    Returns the GeoJSON feature dict with geometry and properties, or None.
    """
    gj = load_kek_polygons()
    if not gj:
        return None
    for feat in gj.get("features", []):
        props = feat.get("properties", {})
        if props.get("slug") == kek_id:
            return feat
    return None


def polygon_bbox(feature: dict) -> tuple[float, float, float, float, float, float]:
    """Compute bounding box and centroid from a GeoJSON polygon feature.

    Returns (min_lon, min_lat, max_lon, max_lat, center_lat, center_lon).
    """
    geom = feature.get("geometry", {})
    coords_list = geom.get("coordinates", [])
    all_points = []
    if geom.get("type") == "MultiPolygon":
        for poly in coords_list:
            for ring in poly:
                all_points.extend(ring)
    elif geom.get("type") == "Polygon":
        for ring in coords_list:
            all_points.extend(ring)
    if not all_points:
        return (0, 0, 0, 0, 0, 0)
    lons = [p[0] for p in all_points]
    lats = [p[1] for p in all_points]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    return (min_lon, min_lat, max_lon, max_lat, (min_lat + max_lat) / 2, (min_lon + max_lon) / 2)


def load_peatland() -> dict | None:
    """Load Indonesian peatland polygons. Uses pre-processed cache if available."""
    # Try pre-processed cache first
    cache = LAYERS_CACHE_DIR / "peatland.geojson"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)

    # Fall back to raw processing
    path = DATA_DIR / "Indonesia_peat_lands.geojson"
    if not path.exists():
        return None

    import geopandas as gpd

    gdf = gpd.read_file(path)
    if gdf.empty:
        return None
    # Dissolve all into one multipolygon and simplify for performance
    gdf["geometry"] = gdf.geometry.simplify(0.01)
    dissolved = gdf.dissolve()
    dissolved["geometry"] = dissolved.geometry.simplify(0.05)
    return json.loads(dissolved.to_json())


def load_protected_forest() -> dict | None:
    """Load kawasan hutan (conservation + protected). Uses pre-processed cache if available."""
    # Try pre-processed cache first
    cache = LAYERS_CACHE_DIR / "protected_forest.geojson"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)

    # Fall back to raw processing
    path = DATA_DIR / "buildability" / "kawasan_hutan.shp"
    if not path.exists():
        return None

    import geopandas as gpd

    gdf = gpd.read_file(path)
    if gdf.empty:
        return None
    # Only conservation and protected forest (actual no-build zones)
    protected = gdf[gdf["kelas"].isin(["Hutan Konservasi", "Hutan Lindung"])]
    if protected.empty:
        return None
    dissolved = protected.dissolve(by="kelas")
    dissolved["geometry"] = dissolved.geometry.simplify(0.05)
    return json.loads(dissolved.to_json())


def load_industrial_facilities() -> list[dict]:
    """Load industrial facilities (50k+ employees). Uses pre-processed cache if available."""
    # Try pre-processed cache first
    cache = LAYERS_CACHE_DIR / "industrial.json"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)

    # Fall back to raw shapefile processing
    import glob

    shp_files = glob.glob(str(DATA_DIR / "industrial_data" / "*.shp"))
    if not shp_files:
        return []

    import geopandas as gpd

    gdf = gpd.read_file(shp_files[0])
    facilities = []
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        facilities.append(
            {
                "lon": geom.x,
                "lat": geom.y,
                "name": row.get("namobj", "Unknown"),
                "province": row.get("wadmpr", ""),
                "district": row.get("wadmkk", ""),
            }
        )
    return facilities


def load_grid_lines() -> dict | None:
    """Load PLN transmission grid lines. Uses pre-processed cache if available."""
    # Try pre-processed cache first
    cache = LAYERS_CACHE_DIR / "grid_lines.geojson"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)

    # Fall back to raw data
    grid_path = DATA_DIR / "pln_grid_lines.geojson"
    if not grid_path.exists():
        return None
    with open(grid_path) as f:
        return json.load(f)


def filter_substations_near_point(lat: float, lon: float, radius_km: float = 50.0) -> list[dict]:
    """Filter substations within radius_km of a point using haversine distance."""
    import math

    stations = load_substations()
    nearby = []
    for s in stations:
        # Haversine
        lat1, lon1 = math.radians(lat), math.radians(lon)
        lat2, lon2 = math.radians(s["lat"]), math.radians(s["lon"])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        dist_km = 6371.0 * 2 * math.asin(math.sqrt(a))
        if dist_km <= radius_km:
            nearby.append({**s, "dist_km": round(dist_km, 1)})
    return nearby


# ---------------------------------------------------------------------------
# Raster layer helpers
# ---------------------------------------------------------------------------


def _raster_to_base64_png(
    data: np.ndarray,
    bounds: tuple[float, float, float, float],
    colormap: str = "YlOrRd",
    vmin: float | None = None,
    vmax: float | None = None,
    alpha: float = 0.6,
    max_width: int = 800,
    pad_degrees: float = 5.0,
) -> tuple[str, list[list[float]]]:
    """Convert a 2D numpy array to a base64 PNG with transparency.

    Returns (base64_png_string, coordinates) where coordinates is the
    Mapbox image layer format: [[lon_min, lat_max], [lon_max, lat_max],
    [lon_max, lat_min], [lon_min, lat_min]].

    pad_degrees: extend bounds by this many degrees on each side with
    transparent pixels. Prevents hard cutoff when the map is pitched (3D).
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

    # Pad the raster with transparent (NaN) pixels to extend geographic bounds.
    # This prevents a hard visible edge when the map is tilted for 3D terrain.
    if pad_degrees > 0:
        left, bottom, right, top = bounds
        lat_span = top - bottom
        lon_span = right - left
        h, w = data.shape
        # Compute how many pixels the padding corresponds to
        pad_rows = max(1, int(h * pad_degrees / lat_span))
        pad_cols = max(1, int(w * pad_degrees / lon_span))
        data = np.pad(data, ((pad_rows, pad_rows), (pad_cols, pad_cols)), constant_values=np.nan)
        bounds = (left - pad_degrees, bottom - pad_degrees, right + pad_degrees, top + pad_degrees)

    # Downsample if too wide
    h, w = data.shape
    if w > max_width:
        factor = max_width / w
        new_h = max(1, int(h * factor))
        new_w = max_width
        # Simple block averaging for downsampling
        from scipy.ndimage import zoom

        data = zoom(data, (new_h / h, new_w / w), order=1)

    # Create RGBA image
    if vmin is None:
        vmin = (
            float(np.nanpercentile(data[np.isfinite(data)], 2)) if np.any(np.isfinite(data)) else 0
        )
    if vmax is None:
        vmax = (
            float(np.nanpercentile(data[np.isfinite(data)], 98)) if np.any(np.isfinite(data)) else 1
        )

    cmap = plt.get_cmap(colormap)
    norm = Normalize(vmin=vmin, vmax=vmax)
    rgba = cmap(norm(data))

    # Set nodata pixels to transparent
    mask = ~np.isfinite(data)
    rgba[mask] = [0, 0, 0, 0]
    # Apply alpha to valid pixels
    rgba[~mask, 3] = alpha

    # Convert to PNG bytes
    fig, ax = plt.subplots(1, 1, figsize=(rgba.shape[1] / 100, rgba.shape[0] / 100), dpi=100)
    ax.imshow(rgba, interpolation="nearest", aspect="auto")
    ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, dpi=100, transparent=True)
    plt.close(fig)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")

    left, bottom, right, top = [float(x) for x in bounds]
    coordinates = [
        [left, top],
        [right, top],
        [right, bottom],
        [left, bottom],
    ]

    return f"data:image/png;base64,{b64}", coordinates


def load_pvout_raster() -> tuple[str, list[list[float]]] | None:
    """Load PVOUT raster overlay. Uses pre-processed cache if available."""
    # Try pre-processed cache first (outputs/layers/pvout.json)
    cache = LAYERS_CACHE_DIR / "pvout.json"
    if cache.exists():
        data = json.loads(cache.read_text())
        return data["image_url"], data["coordinates"]

    # Fall back to raw GeoTIFF processing
    import rasterio
    from rasterio.enums import Resampling

    zip_path = DATA_DIR / "Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip"
    tif_name = "Indonesia_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/PVOUT.tif"

    if not zip_path.exists():
        return None

    import shutil
    import tempfile

    tmpdir = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(zip_path) as z:
            z.extract(tif_name, tmpdir)

        tif_path = Path(tmpdir) / tif_name
        with rasterio.open(tif_path) as src:
            # Read at reduced resolution (~4km instead of 1km)
            out_shape = (src.height // 4, src.width // 4)
            data = src.read(1, out_shape=out_shape, resampling=Resampling.average)
            bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)

        # Convert daily kWh/kWp to annual
        data = data * 365.0
        # Mask nodata
        data[data <= 0] = np.nan

        return _raster_to_base64_png(
            data, bounds, colormap="YlOrRd", vmin=1000, vmax=1800, alpha=0.5, max_width=600
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def load_wind_raster() -> tuple[str, list[list[float]]] | None:
    """Load wind speed raster overlay. Uses pre-processed cache if available."""
    # Try pre-processed cache first (outputs/layers/wind.json)
    cache = LAYERS_CACHE_DIR / "wind.json"
    if cache.exists():
        data = json.loads(cache.read_text())
        return data["image_url"], data["coordinates"]

    # Fall back to raw GeoTIFF processing
    import rasterio
    from rasterio.enums import Resampling

    tif_path = DATA_DIR / "wind" / "IDN_wind-speed_100m.tif"
    if not tif_path.exists():
        return None

    with rasterio.open(tif_path) as src:
        # Aggressive downsample: 19757x8707 → ~500x220
        factor = 40
        out_shape = (src.height // factor, src.width // factor)
        data = src.read(1, out_shape=out_shape, resampling=Resampling.average)
        bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)

    data[data <= 0] = np.nan

    return _raster_to_base64_png(
        data, bounds, colormap="Blues", vmin=2, vmax=8, alpha=0.5, max_width=600
    )


def load_buildable_polygons() -> dict | None:
    """Load solar buildable area polygons (M14: raster-to-polygon conversion)."""
    path = REPO_ROOT / "outputs" / "assets" / "buildable_polygons.geojson"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def load_wind_buildable_polygons() -> dict | None:
    """Load wind buildable area polygons (from build_wind_buildable_polygons)."""
    path = REPO_ROOT / "outputs" / "assets" / "wind_buildable_polygons.geojson"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _strip_z(geojson_geom: dict) -> None:
    """Remove z-coordinates from a GeoJSON geometry dict in-place."""
    coords = geojson_geom.get("coordinates")
    if coords is None:
        return
    geojson_geom["coordinates"] = _strip_z_coords(coords)


def _strip_z_coords(coords: list | tuple) -> list:
    """Recursively strip z-values from nested coordinate arrays."""
    if not coords:
        return list(coords)
    if isinstance(coords[0], (int, float)):
        return list(coords[:2])
    return [_strip_z_coords(c) for c in coords]


def get_within_boundary_buildable(kek_id: str) -> dict | None:
    """Return buildable polygon fragments clipped to a KEK boundary.

    Loads the KEK polygon and all buildable polygons, buffers the buildable
    polygons by ~150m to catch near-misses from raster vectorization, then
    clips to the KEK boundary. Returns a GeoJSON FeatureCollection of the
    clipped fragments, or None if no overlap.
    """
    from shapely.geometry import mapping, shape

    kek_feat = get_kek_polygon_by_id(kek_id)
    if kek_feat is None:
        return None

    bp = load_buildable_polygons()
    if bp is None or not bp.get("features"):
        return None

    kek_geom = shape(kek_feat["geometry"])
    # Buffer KEK slightly outward to catch polygons just outside boundary
    BUFFER_DEG = 0.002  # ~220m at equator, ~200m at Indonesian latitudes
    kek_buffered = kek_geom.buffer(BUFFER_DEG)

    # Find buildable polygons that intersect the buffered KEK
    clipped_features = []
    for feat in bp["features"]:
        bp_geom = shape(feat["geometry"])
        if not kek_buffered.intersects(bp_geom):
            continue
        # Clip to the actual KEK boundary (not the buffer)
        clipped = kek_geom.intersection(bp_geom.buffer(BUFFER_DEG))
        if clipped.is_empty or clipped.area == 0:
            continue
        geojson_geom = mapping(clipped)
        # Strip z-coordinates (shapely intersection can produce 3D coords)
        _strip_z(geojson_geom)
        clipped_features.append(
            {
                "type": "Feature",
                "geometry": geojson_geom,
                "properties": feat.get("properties", {}),
            }
        )

    if not clipped_features:
        return None

    return {"type": "FeatureCollection", "features": clipped_features}


# def load_buildable_raster() -> tuple[str, list[list[float]]] | None:
#     """Load pre-computed buildable PVOUT raster (output of build_buildable_raster.py).
#
#     Removed from frontend — buildable_polygons is the single source of truth.
#     """
#     import rasterio
#
#     path = REPO_ROOT / "outputs" / "assets" / "buildable_pvout_web.tif"
#     if not path.exists():
#         return None
#
#     with rasterio.open(path) as src:
#         data = src.read(1)
#         bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)
#
#     # Convert daily kWh/kWp to annual for display
#     data = data * 365.0
#     data[data <= 0] = np.nan
#
#     return _raster_to_base64_png(
#         data, bounds, colormap="YlGn", vmin=1000, vmax=1800, alpha=0.55, max_width=800
#     )


# ---------------------------------------------------------------------------
# Cached layer store (loaded once at startup)
# ---------------------------------------------------------------------------

_LAYERS_CACHE: dict | None = None


def get_all_layers() -> dict:
    """Load all map layers, caching the result.

    Returns dict with keys:
        substations: list of dicts
        kek_polygons: GeoJSON dict or None
        pvout: (base64_png, coordinates) or None
        wind: (base64_png, coordinates) or None
    """
    global _LAYERS_CACHE
    if _LAYERS_CACHE is not None:
        return _LAYERS_CACHE

    print("  Loading map layers...")
    layers: dict = {}

    layers["substations"] = load_substations()
    print(f"    Substations: {len(layers['substations'])} points")

    layers["kek_polygons"] = load_kek_polygons()
    print(f"    KEK polygons: {'loaded' if layers['kek_polygons'] else 'not found'}")

    try:
        layers["pvout"] = load_pvout_raster()
        print(f"    PVOUT raster: {'loaded' if layers['pvout'] else 'not found'}")
    except Exception as e:
        print(f"    PVOUT raster: failed ({e})")
        layers["pvout"] = None

    try:
        layers["wind"] = load_wind_raster()
        print(f"    Wind raster: {'loaded' if layers['wind'] else 'not found'}")
    except Exception as e:
        print(f"    Wind raster: failed ({e})")
        layers["wind"] = None

    try:
        layers["buildable_polygons"] = load_buildable_polygons()
        n_bp = len(layers["buildable_polygons"]["features"]) if layers["buildable_polygons"] else 0
        print(f"    Buildable polygons: {n_bp} polygons")
    except Exception as e:
        print(f"    Buildable polygons: failed ({e})")
        layers["buildable_polygons"] = None

    try:
        layers["wind_buildable_polygons"] = load_wind_buildable_polygons()
        n_wbp = (
            len(layers["wind_buildable_polygons"]["features"])
            if layers["wind_buildable_polygons"]
            else 0
        )
        print(f"    Wind buildable polygons: {n_wbp} polygons")
    except Exception as e:
        print(f"    Wind buildable polygons: failed ({e})")
        layers["wind_buildable_polygons"] = None

    try:
        layers["peatland"] = load_peatland()
        print(f"    Peatland: {'loaded' if layers['peatland'] else 'not found'}")
    except Exception as e:
        print(f"    Peatland: failed ({e})")
        layers["peatland"] = None

    try:
        layers["protected_forest"] = load_protected_forest()
        print(f"    Protected forest: {'loaded' if layers['protected_forest'] else 'not found'}")
    except Exception as e:
        print(f"    Protected forest: failed ({e})")
        layers["protected_forest"] = None

    try:
        layers["industrial"] = load_industrial_facilities()
        print(f"    Industrial facilities: {len(layers['industrial'])} points")
    except Exception as e:
        print(f"    Industrial facilities: failed ({e})")
        layers["industrial"] = []

    try:
        layers["grid_lines"] = load_grid_lines()
        n = len(layers["grid_lines"]["features"]) if layers["grid_lines"] else 0
        print(f"    Grid lines: {n} lines")
    except Exception as e:
        print(f"    Grid lines: failed ({e})")
        layers["grid_lines"] = None

    try:
        layers["nickel_smelters"] = load_nickel_smelters()
        print(f"    Nickel smelters: {len(layers['nickel_smelters'])} points")
    except Exception as e:
        print(f"    Nickel smelters: failed ({e})")
        layers["nickel_smelters"] = []

    try:
        layers["captive_coal"] = load_captive_coal()
        print(f"    Captive coal plants: {len(layers['captive_coal'])} points")
    except Exception as e:
        print(f"    Captive coal plants: failed ({e})")
        layers["captive_coal"] = []

    try:
        layers["steel_plants"] = load_steel_plants()
        print(f"    Steel plants: {len(layers['steel_plants'])} points")
    except Exception as e:
        print(f"    Steel plants: failed ({e})")
        layers["steel_plants"] = []

    try:
        layers["cement_plants"] = load_cement_plants()
        print(f"    Cement plants: {len(layers['cement_plants'])} points")
    except Exception as e:
        print(f"    Cement plants: failed ({e})")
        layers["cement_plants"] = []

    _LAYERS_CACHE = layers
    return layers


# Available layer options for the UI checklist
LAYER_OPTIONS = [
    {"label": "Substations (PLN)", "value": "substations"},
    {"label": "KEK Boundaries", "value": "kek_polygons"},
    {"label": "Solar Potential (PVOUT)", "value": "pvout"},
    {"label": "Solar Buildable Areas", "value": "buildable_polygons"},
    {"label": "Wind Buildable Areas", "value": "wind_buildable_polygons"},
    {"label": "Wind Speed (100m)", "value": "wind"},
]
