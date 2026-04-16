"""
build_fct_substation_proximity — nearest PLN substation per KEK + grid integration category.

Sources:
    data/substation.geojson                      2,913 PLN substations (WGS84 point features)
    data/pln_grid_lines.geojson                  1,595 PLN transmission lines (WGS84 line features)
    outputs/data/processed/dim_sites.csv           site centroids (lat, lon)
    outputs/data/processed/fct_site_resource.csv  best solar site coordinates (V2)
    outputs/data/raw/kek_polygons.geojson        site boundary polygons (MultiPolygon)

Output columns (one row per site_id):
    site_id                            join key
    site_name                          display name
    nearest_substation_name            namobj of nearest operational PLN substation (to KEK)
    nearest_substation_voltage_kv      teggi field (e.g. "150 kV")
    nearest_substation_capacity_mva    kapgi field (MVA)
    nearest_substation_regpln          regpln field — PLN region of KEK's nearest substation
    dist_to_nearest_substation_km      haversine distance from KEK centroid, 2 decimals
    has_internal_substation            True if any operational substation is inside KEK polygon
    siting_scenario                    'within_boundary' or 'remote_captive' (V1 compat)
    dist_solar_to_nearest_substation_km  haversine from best solar site to nearest substation (V2)
    nearest_substation_to_solar_name   name of nearest substation to solar site (V2)
    nearest_substation_to_solar_regpln regpln of nearest substation to solar site (V3.1)
    grid_integration_category          'within_boundary'|'grid_ready'|'invest_transmission'|'invest_substation'|'grid_first' (V3)
    same_grid_region                   True if KEK & solar nearest substations share regpln (V3.1)
    line_connected                     True if grid line geometrically connects both substations (V3.1)
    inter_substation_connected         True if line_connected OR same_grid_region (V3.1)
    inter_substation_dist_km           haversine between B_solar and B_kek, NaN if same sub (V3.1)
    available_capacity_mva             rated × (1 − utilization), None if unknown (V3.1)
    capacity_assessment                green|yellow|red|unknown traffic light (V3.1)

Methodology:
    - Only operational substations (statopr == "Operasi") are considered.
    - Nearest substation is found by haversine distance from KEK centroid.
    - has_internal_substation uses shapely point-in-polygon against KEK MultiPolygon.
    - V2 three-point proximity: (A) best solar site → (B) nearest substation → (C) KEK centroid.
    - V3.1: geometric connectivity check using pln_grid_lines.geojson.
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

from src.assumptions import (
    GRID_LINE_BUFFER_KM,
    SUBSTATION_UTILIZATION_PCT,
)
from src.model.basic_model import capacity_assessment, grid_integration_category

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW = REPO_ROOT / "outputs" / "data" / "raw"

SUBSTATION_GEOJSON = REPO_ROOT / "data" / "substation.geojson"
GRID_LINES_GEOJSON = REPO_ROOT / "data" / "pln_grid_lines.geojson"
DIM_SITES_CSV = PROCESSED / "dim_sites.csv"
FKT_SITE_RESOURCE_CSV = PROCESSED / "fct_site_resource.csv"
KEK_POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"

_OPERATIONAL_STATUS = "Operasi"

# kapgi unit normalization thresholds (see DATA_DICTIONARY.md §3.5)
# PLN encodes capacity inconsistently: some rows in MVA, others in VA.
# Rule: values 1–9,999 are already in MVA; values ≥ 10,000 are in VA (divide by 1e6).
_KAPGI_VA_THRESHOLD = 10_000  # above this → raw value is in VA, not MVA

# Approximate degrees per km at Indonesian latitudes (~5°S)
_DEG_PER_KM = 1.0 / 111.32


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
                "regpln": props.get("regpln", ""),
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


def _load_grid_lines(path: Path) -> list[dict]:
    """Load PLN transmission grid lines from GeoJSON.

    Returns list of {geometry: shapely LineString/MultiLineString, voltage_kv, name}.
    """
    if not path.exists():
        return []
    with path.open() as f:
        gj = json.load(f)

    lines = []
    for feat in gj["features"]:
        geom = shape(feat["geometry"])
        props = feat["properties"]
        lines.append(
            {
                "geometry": geom,
                "voltage_kv": props.get("tegjar", 0),
                "name": props.get("namobj", ""),
            }
        )
    return lines


# ─── Connectivity check ──────────────────────────────────────────────────────


def _check_line_connectivity(
    sub_a_lat: float,
    sub_a_lon: float,
    sub_b_lat: float,
    sub_b_lon: float,
    grid_lines: list[dict],
    buffer_km: float = GRID_LINE_BUFFER_KM,
) -> bool:
    """Check if any grid line passes near both substations (geometric connectivity proxy).

    Uses approximate degree-to-km conversion at Indonesian latitudes.
    A line "connects" two substations if it passes within buffer_km of both points.
    """
    if not grid_lines:
        return False

    buffer_deg = buffer_km * _DEG_PER_KM
    point_a = Point(sub_a_lon, sub_a_lat)
    point_b = Point(sub_b_lon, sub_b_lat)

    for line in grid_lines:
        geom = line["geometry"]
        if geom.distance(point_a) <= buffer_deg and geom.distance(point_b) <= buffer_deg:
            return True
    return False


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
    grid_lines_geojson: Path = GRID_LINES_GEOJSON,
    dim_sites_csv: Path = DIM_SITES_CSV,
    kek_polygons_geojson: Path = KEK_POLYGONS_GEOJSON,
    fct_site_resource_csv: Path = FKT_SITE_RESOURCE_CSV,
    substation_utilization_pct: float = SUBSTATION_UTILIZATION_PCT,
) -> pd.DataFrame:
    """Compute nearest PLN substation distance, siting scenario, and grid integration category.

    V2 adds three-point proximity analysis: solar site → substation → KEK centroid.
    V3.1 adds geometric grid line connectivity check and capacity utilization.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    substations = _load_substations(substation_geojson)
    kek_polygons = _load_kek_polygons(kek_polygons_geojson)
    grid_lines = _load_grid_lines(grid_lines_geojson)
    dim_sites = pd.read_csv(dim_sites_csv)[["site_id", "site_name", "latitude", "longitude"]]

    print(f"  Substations: {len(substations)} operational")
    print(f"  Grid lines: {len(grid_lines)} loaded")

    # V2: Load best solar site coordinates from fct_site_resource
    solar_data: dict[str, dict] = {}
    if fct_site_resource_csv.exists():
        resource_df = pd.read_csv(fct_site_resource_csv)
        if "best_solar_site_lat" in resource_df.columns:
            for _, r in resource_df.iterrows():
                lat = r.get("best_solar_site_lat")
                lon = r.get("best_solar_site_lon")
                cap = r.get("max_captive_capacity_mwp")
                if pd.notna(lat) and pd.notna(lon):
                    solar_data[r["site_id"]] = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "capacity_mwp": float(cap) if pd.notna(cap) else None,
                    }
            print(
                f"  V2: Loaded solar site coordinates for {len(solar_data)}/{len(resource_df)} KEKs"
            )
        else:
            print(
                "  V2: fct_site_resource.csv exists but missing best_solar_site_lat — skipping solar proximity"
            )
    else:
        print(f"  V2: {fct_site_resource_csv.name} not found — solar proximity columns will be NaN")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    records = []
    for _, row in dim_sites.iterrows():
        site_id = row["site_id"]
        kek_lat = float(row["latitude"])
        kek_lon = float(row["longitude"])

        nearest_to_kek, dist_km = _nearest_substation(kek_lat, kek_lon, substations)
        internal = _has_internal_substation(site_id, kek_polygons, substations)

        # V2: Compute solar-to-substation distance
        dist_solar_to_sub = np.nan
        nearest_to_solar_name = None
        nearest_to_solar_regpln = None
        nearest_to_solar_sub = None
        solar_cap_mwp = None
        if site_id in solar_data:
            sd = solar_data[site_id]
            solar_lat, solar_lon = sd["lat"], sd["lon"]
            solar_cap_mwp = sd.get("capacity_mwp")
            nearest_to_solar_sub, dist_solar = _nearest_substation(
                solar_lat, solar_lon, substations
            )
            if nearest_to_solar_sub:
                dist_solar_to_sub = round(dist_solar, 2)
                nearest_to_solar_name = nearest_to_solar_sub["name"]
                nearest_to_solar_regpln = nearest_to_solar_sub.get("regpln", "")

        # V3.1: Grid connectivity check
        kek_sub_regpln = nearest_to_kek.get("regpln", "") if nearest_to_kek else ""
        same_region = bool(
            kek_sub_regpln and nearest_to_solar_regpln and kek_sub_regpln == nearest_to_solar_regpln
        )

        # Compute inter-substation distance
        inter_sub_dist = np.nan
        line_connected: bool | None = None
        inter_connected: bool | None = None

        if (
            nearest_to_kek
            and nearest_to_solar_sub
            and nearest_to_kek["name"] != nearest_to_solar_sub["name"]
        ):
            # Different substations — check connectivity
            inter_sub_dist = round(
                _haversine_km(
                    nearest_to_kek["lat"],
                    nearest_to_kek["lon"],
                    nearest_to_solar_sub["lat"],
                    nearest_to_solar_sub["lon"],
                ),
                2,
            )
            line_connected = _check_line_connectivity(
                nearest_to_kek["lat"],
                nearest_to_kek["lon"],
                nearest_to_solar_sub["lat"],
                nearest_to_solar_sub["lon"],
                grid_lines,
            )
            inter_connected = line_connected or same_region
        elif nearest_to_kek and nearest_to_solar_sub:
            # Same substation — inherently connected
            inter_connected = True

        # V3.1: Capacity assessment
        cap_light, avail_mva = capacity_assessment(
            nearest_to_kek["capacity_mva"] if nearest_to_kek else None,
            solar_cap_mwp,
            utilization_pct=substation_utilization_pct,
        )

        # Derive grid integration category
        category = grid_integration_category(
            has_internal_substation=internal,
            dist_solar_to_substation_km=dist_solar_to_sub
            if np.isfinite(dist_solar_to_sub)
            else None,
            dist_kek_to_substation_km=dist_km,
            substation_capacity_mva=nearest_to_kek["capacity_mva"] if nearest_to_kek else None,
            substation_utilization_pct=substation_utilization_pct,
            solar_capacity_mwp=solar_cap_mwp,
            inter_substation_connected=inter_connected,
        )

        records.append(
            {
                "site_id": site_id,
                "site_name": row["site_name"],
                "nearest_substation_name": nearest_to_kek["name"] if nearest_to_kek else None,
                "nearest_substation_voltage_kv": nearest_to_kek["voltage_kv"]
                if nearest_to_kek
                else None,
                "nearest_substation_capacity_mva": nearest_to_kek["capacity_mva"]
                if nearest_to_kek
                else None,
                "nearest_substation_regpln": kek_sub_regpln,
                "dist_to_nearest_substation_km": round(dist_km, 2),
                "has_internal_substation": internal,
                "siting_scenario": "within_boundary" if internal else "remote_captive",
                # V2: three-point proximity
                "dist_solar_to_nearest_substation_km": dist_solar_to_sub,
                "nearest_substation_to_solar_name": nearest_to_solar_name,
                "nearest_substation_to_solar_regpln": nearest_to_solar_regpln,
                "grid_integration_category": category,
                # V3.1: connectivity and capacity
                "same_grid_region": same_region,
                "line_connected": line_connected,
                "inter_substation_connected": bool(inter_connected)
                if inter_connected is not None
                else None,
                "inter_substation_dist_km": inter_sub_dist,
                "available_capacity_mva": avail_mva,
                "capacity_assessment": cap_light,
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
    print("\nGrid integration categories (V3.1):")
    print(df["grid_integration_category"].value_counts().to_dict())
    print("\nConnectivity (V3.1):")
    print(f"  Same grid region: {df['same_grid_region'].sum()} KEKs")
    print(f"  Line connected: {df['line_connected'].sum()} KEKs")
    conn = df["inter_substation_connected"]
    print(f"  Inter-substation connected: {conn.sum()} of {conn.notna().sum()} checked")
    print("\nCapacity assessment (V3.1):")
    print(df["capacity_assessment"].value_counts().to_dict())
    print("\nDistance KEK→substation (km):")
    print(df["dist_to_nearest_substation_km"].describe().round(2).to_string())
    solar_dists = df["dist_solar_to_nearest_substation_km"].dropna()
    if len(solar_dists) > 0:
        print(f"\nDistance solar→substation (km) [{len(solar_dists)} KEKs with solar coords]:")
        print(solar_dists.describe().round(2).to_string())
    inter_dists = df["inter_substation_dist_km"].dropna()
    if len(inter_dists) > 0:
        print(f"\nInter-substation distance (km) [{len(inter_dists)} KEKs with different subs]:")
        print(inter_dists.describe().round(2).to_string())
    print("\nSample:")
    print(
        df[
            [
                "site_id",
                "nearest_substation_name",
                "dist_to_nearest_substation_km",
                "grid_integration_category",
                "line_connected",
                "capacity_assessment",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
