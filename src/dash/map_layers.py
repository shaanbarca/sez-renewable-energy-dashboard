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
                }
            )
    return stations


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
    """Load Indonesian peatland polygons, simplified + dissolved for web display."""
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
    """Load kawasan hutan (conservation + protected forest), dissolved + simplified."""
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
    """Load industrial facilities (50k+ employees) as point markers."""
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
    """Load PLN transmission grid lines from pre-extracted GeoJSON."""
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
    """Load PVOUT GeoTIFF from zip, downsample, return as base64 PNG overlay."""
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
    """Load wind speed GeoTIFF, downsample, return as base64 PNG overlay."""
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


def load_buildable_raster() -> tuple[str, list[list[float]]] | None:
    """Load pre-computed buildable PVOUT raster (output of build_buildable_raster.py)."""
    import rasterio

    path = REPO_ROOT / "outputs" / "assets" / "buildable_pvout_web.tif"
    if not path.exists():
        return None

    with rasterio.open(path) as src:
        data = src.read(1)
        bounds = (src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top)

    # Convert daily kWh/kWp to annual for display
    data = data * 365.0
    data[data <= 0] = np.nan

    return _raster_to_base64_png(
        data, bounds, colormap="YlGn", vmin=1000, vmax=1800, alpha=0.55, max_width=800
    )


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
        buildable: (base64_png, coordinates) or None
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
        layers["buildable"] = load_buildable_raster()
        print(f"    Buildable solar: {'loaded' if layers['buildable'] else 'not found'}")
    except Exception as e:
        print(f"    Buildable solar: failed ({e})")
        layers["buildable"] = None

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

    _LAYERS_CACHE = layers
    return layers


# Available layer options for the UI checklist
LAYER_OPTIONS = [
    {"label": "Substations (PLN)", "value": "substations"},
    {"label": "KEK Boundaries", "value": "kek_polygons"},
    {"label": "Solar Potential (PVOUT)", "value": "pvout"},
    {"label": "Solar Buildable Area", "value": "buildable"},
    {"label": "Wind Speed (100m)", "value": "wind"},
]
