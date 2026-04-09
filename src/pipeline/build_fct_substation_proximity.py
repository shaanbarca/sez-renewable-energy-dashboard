"""
build_fct_substation_proximity — nearest PLN substation per KEK + grid integration category.

Sources:
    data/substation.geojson                      2,913 PLN substations (WGS84 point features)
    outputs/data/processed/dim_kek.csv           KEK centroids (lat, lon)
    outputs/data/processed/fct_kek_resource.csv  best solar site coordinates (V2)
    outputs/data/raw/kek_polygons.geojson        KEK boundary polygons (MultiPolygon)

Output columns (one row per kek_id):
    kek_id                             join key
    kek_name                           display name
    nearest_substation_name            namobj of nearest operational PLN substation (to KEK)
    nearest_substation_voltage_kv      teggi field (e.g. "150 kV")
    nearest_substation_capacity_mva    kapgi field (MVA)
    dist_to_nearest_substation_km      haversine distance from KEK centroid, 2 decimals
    has_internal_substation            True if any operational substation is inside KEK polygon
    siting_scenario                    'within_boundary' or 'remote_captive' (V1 compat)
    dist_solar_to_nearest_substation_km  haversine from best solar site to nearest substation (V2)
    nearest_substation_to_solar_name   name of nearest substation to solar site (V2)
    grid_integration_category          'within_boundary'|'grid_ready'|'invest_grid'|'grid_first' (V2)

Methodology:
    - Only operational substations (statopr == "Operasi") are considered.
    - Nearest substation is found by haversine distance from KEK centroid.
    - has_internal_substation uses shapely point-in-polygon against KEK MultiPolygon.
    - V2 three-point proximity: (A) best solar site → (B) nearest substation → (C) KEK centroid.
    - grid_integration_category derived from thresholds (see METHODOLOGY_V2.md §2).

See METHODOLOGY_V2.md §2 for three-point proximity analysis.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from src.model.basic_model import grid_integration_category

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW = REPO_ROOT / "outputs" / "data" / "raw"

SUBSTATION_GEOJSON = REPO_ROOT / "data" / "substation.geojson"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
FKT_KEK_RESOURCE_CSV = PROCESSED / "fct_kek_resource.csv"
KEK_POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"

_OPERATIONAL_STATUS = "Operasi"

# kapgi unit normalization thresholds (see DATA_DICTIONARY.md §3.5)
# PLN encodes capacity inconsistently: some rows in MVA, others in VA.
# Rule: values 1–9,999 are already in MVA; values ≥ 10,000 are in VA (divide by 1e6).
_KAPGI_VA_THRESHOLD = 10_000  # above this → raw value is in VA, not MVA


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


# ─── Unit helpers ─────────────────────────────────────────────────────────────


def _normalize_capacity_mva(raw: float | None) -> float | None:
    """Return capacity in MVA, normalising raw kapgi which uses mixed units.

    PLN's substation GeoJSON encodes kapgi inconsistently:
    - Values 1–9,999  → already in MVA (e.g. 30, 60, 150, 315)
    - Values ≥ 10,000 → in VA (e.g. 30,000,000 VA = 30 MVA)
    - Zero or None    → unknown, return None

    The 10,000 threshold is safe because no real transmission substation
    has a capacity between 10,000 MVA and 10,000 VA (0.01 MVA).
    """
    if raw is None or raw == 0:
        return None
    if raw >= _KAPGI_VA_THRESHOLD:
        return round(raw / 1_000_000, 1)
    return float(raw)


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
                "capacity_mva": _normalize_capacity_mva(props.get("kapgi")),
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
    fct_kek_resource_csv: Path = FKT_KEK_RESOURCE_CSV,
) -> pd.DataFrame:
    """Compute nearest PLN substation distance, siting scenario, and grid integration category.

    V2 adds three-point proximity analysis: solar site → substation → KEK centroid.
    Reads best_solar_site_lat/lon from fct_kek_resource.csv (produced by V2-B1).
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    substations = _load_substations(substation_geojson)
    kek_polygons = _load_kek_polygons(kek_polygons_geojson)
    dim_kek = pd.read_csv(dim_kek_csv)[["kek_id", "kek_name", "latitude", "longitude"]]

    # V2: Load best solar site coordinates from fct_kek_resource
    solar_coords: dict[str, tuple[float, float]] = {}
    if fct_kek_resource_csv.exists():
        resource_df = pd.read_csv(fct_kek_resource_csv)
        if "best_solar_site_lat" in resource_df.columns:
            for _, r in resource_df.iterrows():
                lat = r.get("best_solar_site_lat")
                lon = r.get("best_solar_site_lon")
                if pd.notna(lat) and pd.notna(lon):
                    solar_coords[r["kek_id"]] = (float(lat), float(lon))
            print(
                f"  V2: Loaded solar site coordinates for {len(solar_coords)}/{len(resource_df)} KEKs"
            )
        else:
            print(
                "  V2: fct_kek_resource.csv exists but missing best_solar_site_lat — skipping solar proximity"
            )
    else:
        print(f"  V2: {fct_kek_resource_csv.name} not found — solar proximity columns will be NaN")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    records = []
    for _, row in dim_kek.iterrows():
        kek_id = row["kek_id"]
        kek_lat = float(row["latitude"])
        kek_lon = float(row["longitude"])

        nearest_to_kek, dist_km = _nearest_substation(kek_lat, kek_lon, substations)
        internal = _has_internal_substation(kek_id, kek_polygons, substations)

        # V2: Compute solar-to-substation distance
        dist_solar_to_sub = np.nan
        nearest_to_solar_name = None
        if kek_id in solar_coords:
            solar_lat, solar_lon = solar_coords[kek_id]
            nearest_to_solar, dist_solar = _nearest_substation(solar_lat, solar_lon, substations)
            if nearest_to_solar:
                dist_solar_to_sub = round(dist_solar, 2)
                nearest_to_solar_name = nearest_to_solar["name"]

        # V2: Derive grid integration category
        category = grid_integration_category(
            has_internal_substation=internal,
            dist_solar_to_substation_km=dist_solar_to_sub
            if np.isfinite(dist_solar_to_sub)
            else None,
            dist_kek_to_substation_km=dist_km,
            substation_capacity_mva=nearest_to_kek["capacity_mva"] if nearest_to_kek else None,
        )

        records.append(
            {
                "kek_id": kek_id,
                "kek_name": row["kek_name"],
                "nearest_substation_name": nearest_to_kek["name"] if nearest_to_kek else None,
                "nearest_substation_voltage_kv": nearest_to_kek["voltage_kv"]
                if nearest_to_kek
                else None,
                "nearest_substation_capacity_mva": nearest_to_kek["capacity_mva"]
                if nearest_to_kek
                else None,
                "dist_to_nearest_substation_km": round(dist_km, 2),
                "has_internal_substation": internal,
                "siting_scenario": "within_boundary" if internal else "remote_captive",
                # V2: three-point proximity
                "dist_solar_to_nearest_substation_km": dist_solar_to_sub,
                "nearest_substation_to_solar_name": nearest_to_solar_name,
                "grid_integration_category": category,
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
    print("\nGrid integration categories (V2):")
    print(df["grid_integration_category"].value_counts().to_dict())
    print("\nDistance KEK→substation (km):")
    print(df["dist_to_nearest_substation_km"].describe().round(2).to_string())
    solar_dists = df["dist_solar_to_nearest_substation_km"].dropna()
    if len(solar_dists) > 0:
        print(f"\nDistance solar→substation (km) [{len(solar_dists)} KEKs with solar coords]:")
        print(solar_dists.describe().round(2).to_string())
    print("\nSample:")
    print(
        df[
            [
                "kek_id",
                "nearest_substation_name",
                "dist_to_nearest_substation_km",
                "grid_integration_category",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
