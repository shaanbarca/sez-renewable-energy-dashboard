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
) -> tuple[str, list[list[float]]]:
    """Convert a 2D numpy array to a base64 PNG with transparency.

    Returns (base64_png_string, coordinates) where coordinates is the
    Mapbox image layer format: [[lon_min, lat_max], [lon_max, lat_max],
    [lon_max, lat_min], [lon_min, lat_min]].
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize

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
