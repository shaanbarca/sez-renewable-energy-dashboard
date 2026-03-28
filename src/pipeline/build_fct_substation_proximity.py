"""
build_fct_substation_proximity — nearest PLN substation per KEK + siting scenario.

Sources:
    data/substation.geojson             2,913 PLN substations (WGS84 point features)
    outputs/data/processed/dim_kek.csv  KEK centroids (lat, lon)
    outputs/data/raw/kek_polygons.geojson  KEK boundary polygons (MultiPolygon)

Output columns (one row per kek_id):
    kek_id                        join key
    kek_name                      display name
    nearest_substation_name       namobj of nearest operational PLN substation
    nearest_substation_voltage_kv teggi field (e.g. "150 kV")
    nearest_substation_capacity_mva kapgi field (MVA)
    dist_to_nearest_substation_km haversine distance from KEK centroid, 2 decimals
    has_internal_substation       True if any operational substation is inside KEK polygon
    siting_scenario               'within_boundary' or 'remote_captive'

Methodology:
    - Only operational substations (statopr == "Operasi") are considered.
    - Nearest substation is found by haversine distance from KEK centroid.
    - has_internal_substation uses shapely point-in-polygon against KEK MultiPolygon.
    - siting_scenario = 'within_boundary' if has_internal_substation else 'remote_captive'.
    - 'within_boundary' KEKs use pvout_centroid + no gen-tie cost in LCOE.
    - 'remote_captive' KEKs use pvout_best_50km + gen-tie CAPEX adder in LCOE.

See METHODOLOGY.md Section 2A for legal framework and cost assumptions.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
from shapely.geometry import Point, shape

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW = REPO_ROOT / "outputs" / "data" / "raw"

SUBSTATION_GEOJSON = REPO_ROOT / "data" / "substation.geojson"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
KEK_POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"

_OPERATIONAL_STATUS = "Operasi"


# ─── Geometry helpers ─────────────────────────────────────────────────────────


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6_371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))


# ─── Loaders ──────────────────────────────────────────────────────────────────


def _load_substations(path: Path) -> list[dict]:
    """Load substation GeoJSON and return only operational substations."""
    with path.open() as f:
        gj = json.load(f)

    substations = []
    for feat in gj["features"]:
        props = feat["properties"]
        if props.get("statopr", "").strip() != _OPERATIONAL_STATUS:
            continue
        lon, lat = feat["geometry"]["coordinates"]
        substations.append(
            {
                "name": props.get("namobj", ""),
                "voltage_kv": props.get("teggi", ""),
                "capacity_mva": props.get("kapgi"),
                "lat": lat,
                "lon": lon,
            }
        )
    return substations


def _load_kek_polygons(path: Path) -> dict[str, object]:
    """Return {slug: shapely_geometry} for all KEK polygon features."""
    with path.open() as f:
        gj = json.load(f)

    polygons: dict[str, object] = {}
    for feat in gj["features"]:
        slug = feat["properties"].get("slug", "")
        if slug:
            polygons[slug] = shape(feat["geometry"])
    return polygons


# ─── Per-KEK computation ──────────────────────────────────────────────────────


def _nearest_substation(
    kek_lat: float, kek_lon: float, substations: list[dict]
) -> tuple[dict, float]:
    """Return (substation_dict, distance_km) for the nearest substation."""
    best_sub = None
    best_dist = float("inf")
    for sub in substations:
        d = _haversine_km(kek_lat, kek_lon, sub["lat"], sub["lon"])
        if d < best_dist:
            best_dist = d
            best_sub = sub
    return best_sub, best_dist


def _has_internal_substation(
    kek_slug: str,
    kek_polygons: dict[str, object],
    substations: list[dict],
) -> bool:
    """Return True if any operational substation point falls inside the KEK polygon."""
    polygon = kek_polygons.get(kek_slug)
    if polygon is None:
        return False
    for sub in substations:
        if polygon.contains(Point(sub["lon"], sub["lat"])):
            return True
    return False


# ─── Main builder ─────────────────────────────────────────────────────────────


def build_fct_substation_proximity(
    substation_geojson: Path = SUBSTATION_GEOJSON,
    dim_kek_csv: Path = DIM_KEK_CSV,
    kek_polygons_geojson: Path = KEK_POLYGONS_GEOJSON,
) -> pd.DataFrame:
    """Compute nearest PLN substation distance and siting scenario per KEK."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    substations = _load_substations(substation_geojson)
    kek_polygons = _load_kek_polygons(kek_polygons_geojson)
    dim_kek = pd.read_csv(dim_kek_csv)[["kek_id", "kek_name", "latitude", "longitude"]]

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    records = []
    for _, row in dim_kek.iterrows():
        kek_id = row["kek_id"]
        kek_lat = float(row["latitude"])
        kek_lon = float(row["longitude"])

        nearest, dist_km = _nearest_substation(kek_lat, kek_lon, substations)
        internal = _has_internal_substation(kek_id, kek_polygons, substations)

        records.append(
            {
                "kek_id": kek_id,
                "kek_name": row["kek_name"],
                "nearest_substation_name": nearest["name"] if nearest else None,
                "nearest_substation_voltage_kv": nearest["voltage_kv"] if nearest else None,
                "nearest_substation_capacity_mva": nearest["capacity_mva"] if nearest else None,
                "dist_to_nearest_substation_km": round(dist_km, 2),
                "has_internal_substation": internal,
                "siting_scenario": "within_boundary" if internal else "remote_captive",
            }
        )

    return pd.DataFrame(records)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "fct_substation_proximity.csv"
    df = build_fct_substation_proximity()
    df.to_csv(out, index=False)
    print(f"fct_substation_proximity: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print(f"\nSiting scenarios: {df['siting_scenario'].value_counts().to_dict()}")
    print(f"Has internal substation: {df['has_internal_substation'].sum()} KEKs")
    print("\nDistance summary (km):")
    print(df["dist_to_nearest_substation_km"].describe().round(2).to_string())
    print("\nSample:")
    print(
        df[
            [
                "kek_id",
                "nearest_substation_name",
                "dist_to_nearest_substation_km",
                "siting_scenario",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
