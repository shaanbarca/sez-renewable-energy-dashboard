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
    substation_utilization_pct_effective  RUPTL-tiered per-substation utilization (V3.8)
    ruptl_project_type                 uprate|extension|line_bay|none|None (V3.8)
    ruptl_strongest_status             konstruksi|committed|pengadaan|rencana|None (V3.8)
    ruptl_earliest_target_year         earliest RUPTL target year across matches (V3.8)
    ruptl_mva_added_total              sum of MVA added across RUPTL rows (V3.8)
    ruptl_match_confidence             high|medium|low|None (V3.8)
    nearest_substation_capacity_source 'actual'|'proxy_{voltage}kV'|'unknown' (V3.7)
    solar_search_method                'substation_anchored'|'best_pvout_fallback'|... (V3.7)
    chosen_anchor_substation_name      name of substation the anchored picker latched onto (V3.7)
    solar_supply_share_pct             nameplate supply share of 2030 demand (V3.7)
    solar_delivered_share_pct          CF-corrected delivered-energy share of demand (V3.7)

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
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import Point, shape

from src.assumptions import (
    GRID_LINE_BUFFER_KM,
    HOSTING_CAPACITY_AVAILABILITY_PCT,
    MEANINGFUL_SHARE_PCT,
    SUBSTATION_HOSTING_CAPACITY_PROXY_MVA,
    SUBSTATION_UTILIZATION_PCT,
    SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL,
)
from src.model.basic_model import capacity_assessment, grid_integration_category
from src.pipeline.geo_utils import haversine_km

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW = REPO_ROOT / "outputs" / "data" / "raw"

SUBSTATION_GEOJSON = REPO_ROOT / "data" / "substation.geojson"
GRID_LINES_GEOJSON = REPO_ROOT / "data" / "pln_grid_lines.geojson"
DIM_SITES_CSV = PROCESSED / "dim_sites.csv"
FKT_SITE_RESOURCE_CSV = PROCESSED / "fct_site_resource.csv"
FKT_SITE_DEMAND_CSV = PROCESSED / "fct_site_demand.csv"
FKT_SUBSTATION_RUPTL_SIGNAL_CSV = PROCESSED / "fct_substation_ruptl_signal.csv"
KEK_POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"

_OPERATIONAL_STATUS = "Operasi"

# Demand year used to size the project for capacity_assessment (V3.7).
# Picked to match the scorecard's 2030 demand reference horizon.
DEMAND_YEAR_FOR_SIZING = 2030

# kapgi unit normalization thresholds (see DATA_DICTIONARY.md §3.5)
# PLN encodes capacity inconsistently: some rows in MVA, others in VA.
# Rule: values 1–9,999 are already in MVA; values ≥ 10,000 are in VA (divide by 1e6).
_KAPGI_VA_THRESHOLD = 10_000  # above this → raw value is in VA, not MVA

# Approximate degrees per km at Indonesian latitudes (~5°S)
_DEG_PER_KM = 1.0 / 111.32


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


def _voltage_class_from_teggi(teggi: str | None) -> str | None:
    """Parse the PLN `teggi` string (e.g. '150 kV', '70kv', '500') → voltage-class key.

    Returns the voltage number as a string (e.g. '150'), matching the keys in
    SUBSTATION_HOSTING_CAPACITY_PROXY_MVA. Returns None when parsing fails.
    """
    if not teggi:
        return None
    digits = "".join(ch for ch in str(teggi) if ch.isdigit())
    if not digits:
        return None
    return digits


def _resolve_capacity(raw_kapgi: float | None, teggi: str | None) -> tuple[float | None, str]:
    """Return (rated_capacity_mva, capacity_source).

    Precedence:
        1. Actual kapgi (normalized)                          → ('actual')
        2. Voltage-class proxy nameplate (see PROXY_MVA dict) → ('proxy_<kv>kV')
        3. Unknown                                            → ('unknown')

    The returned MVA is the *rated nameplate*, not the effective available
    capacity. Downstream code derates via utilization_pct (SUBSTATION_UTILIZATION_PCT
    for actual rows, 1 - HOSTING_CAPACITY_AVAILABILITY_PCT for proxy rows).
    Keeping rated nameplate here means the SUBSTATION_MIN_CAPACITY_MVA threshold
    inside grid_integration_category() still compares apples-to-apples.
    """
    actual = _normalize_capacity_mva(raw_kapgi)
    if actual is not None:
        return actual, "actual"

    voltage_class = _voltage_class_from_teggi(teggi)
    proxy_nameplate = SUBSTATION_HOSTING_CAPACITY_PROXY_MVA.get(voltage_class)
    if proxy_nameplate is not None:
        return float(proxy_nameplate), f"proxy_{voltage_class}kV"

    return None, "unknown"


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
        teggi = props.get("teggi", "")
        capacity_mva, capacity_source = _resolve_capacity(props.get("kapgi"), teggi)
        substations.append(
            {
                "name": props.get("namobj", ""),
                "voltage_kv": teggi,
                "capacity_mva": capacity_mva,
                "capacity_source": capacity_source,
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


def _load_ruptl_signal(path: Path) -> dict[tuple[str, str], dict]:
    """Load the RUPTL per-substation signal CSV → {(namobj, regpln): signal_dict}.

    Returns empty dict (silently) if the file is missing — callers then fall
    back to the fleet-default utilization. This keeps the pipeline runnable on
    a fresh clone that hasn't yet executed the RUPTL extractor.
    """
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    lookup: dict[tuple[str, str], dict] = {}
    for _, r in df.iterrows():
        key = (str(r["namobj"]), str(r["regpln"]))
        lookup[key] = {
            "has_planned_upgrade": bool(r.get("has_planned_upgrade", False)),
            "project_type_strongest": (
                str(r["project_type_strongest"])
                if pd.notna(r.get("project_type_strongest"))
                else None
            ),
            "strongest_status": (
                str(r["strongest_status"]) if pd.notna(r.get("strongest_status")) else None
            ),
            "earliest_target_year": (
                int(r["earliest_target_year"]) if pd.notna(r.get("earliest_target_year")) else None
            ),
            "mva_added_total": (
                float(r["mva_added_total"]) if pd.notna(r.get("mva_added_total")) else None
            ),
            "match_confidence": (
                str(r["match_confidence"]) if pd.notna(r.get("match_confidence")) else None
            ),
        }
    return lookup


def _ruptl_utilization_for_substation(
    namobj: str | None,
    regpln: str | None,
    ruptl_lookup: dict[tuple[str, str], dict],
    fallback_pct: float,
) -> tuple[float, dict | None]:
    """Return (utilization_pct, ruptl_signal_dict) for a substation.

    Lookup precedence:
        1. Exact (namobj, regpln) match in RUPTL signal table.
           - uprate    → 0.85
           - extension → 0.75
           - line_bay  → 0.70
           - none (matched row but no upgrade) → 0.55
        2. No match in signal table → fleet-default fallback (0.65).

    The fallback fires for substations outside the RUPTL appendices entirely
    (a statopr-Operasi substation absent from Lampiran A/B/C). For those we
    can't distinguish "no upgrade planned" from "PLN didn't publish a detail
    row", so we default to the neutral fleet-average utilization.
    """
    if not namobj or not regpln:
        return fallback_pct, None

    signal = ruptl_lookup.get((str(namobj), str(regpln)))
    if signal is None:
        return fallback_pct, None

    project_type = signal.get("project_type_strongest")
    if (
        signal.get("has_planned_upgrade")
        and project_type in SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL
    ):
        return SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL[project_type], signal

    # Matched but no actionable upgrade signal → "none" tier.
    return SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL["none"], signal


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
        d = haversine_km(kek_lat, kek_lon, sub["lat"], sub["lon"])
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


def build_fct_substation_proximity(  # noqa: PLR0913
    substation_geojson: Path = SUBSTATION_GEOJSON,
    grid_lines_geojson: Path = GRID_LINES_GEOJSON,
    dim_sites_csv: Path = DIM_SITES_CSV,
    kek_polygons_geojson: Path = KEK_POLYGONS_GEOJSON,
    fct_site_resource_csv: Path = FKT_SITE_RESOURCE_CSV,
    fct_site_demand_csv: Path = FKT_SITE_DEMAND_CSV,
    fct_substation_ruptl_signal_csv: Path = FKT_SUBSTATION_RUPTL_SIGNAL_CSV,
    substation_utilization_pct: float = SUBSTATION_UTILIZATION_PCT,
) -> pd.DataFrame:
    """Compute nearest PLN substation distance, siting scenario, and grid integration category.

    V2 adds three-point proximity analysis: solar site → substation → KEK centroid.
    V3.1 adds geometric grid line connectivity check and capacity utilization.
    V3.8 replaces the fleet-default utilization with a per-substation default
    derived from PLN RUPTL upgrade plans (fct_substation_ruptl_signal).
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    substations = _load_substations(substation_geojson)
    kek_polygons = _load_kek_polygons(kek_polygons_geojson)
    grid_lines = _load_grid_lines(grid_lines_geojson)
    ruptl_lookup = _load_ruptl_signal(fct_substation_ruptl_signal_csv)
    dim_sites = pd.read_csv(dim_sites_csv)[["site_id", "site_name", "latitude", "longitude"]]

    print(f"  Substations: {len(substations)} operational")
    print(f"  Grid lines: {len(grid_lines)} loaded")
    print(f"  RUPTL signal rows: {len(ruptl_lookup)} loaded")

    # V2: Load best solar site coordinates from fct_site_resource.
    # V3.7: also surface the anchored-picker diagnostics so the scorecard can
    # distinguish "Build Substation" caused by a real gap from a fallback artefact.
    solar_data: dict[str, dict] = {}
    if fct_site_resource_csv.exists():
        resource_df = pd.read_csv(fct_site_resource_csv)
        if "best_solar_site_lat" in resource_df.columns:
            for _, r in resource_df.iterrows():
                lat = r.get("best_solar_site_lat")
                lon = r.get("best_solar_site_lon")
                cap = r.get("max_captive_capacity_mwp")
                if pd.notna(lat) and pd.notna(lon):
                    # V3.7 fix: when centroid pixel is NaN (raster hole / edge pixel),
                    # fall back to the best-in-50km buildable PVOUT so project_scale_mwp
                    # still gets sized from real resource data rather than silently
                    # defaulting to full buildable patch (which reintroduces the exact
                    # false "Build Substation" flags this V3.7 step was meant to kill).
                    cf_centroid_val = (
                        float(r["cf_centroid"]) if pd.notna(r.get("cf_centroid")) else None
                    )
                    cf_fallback = None
                    pvout_buildable_annual = r.get("pvout_buildable_best_50km")
                    if pd.notna(pvout_buildable_annual) and pvout_buildable_annual > 0:
                        cf_fallback = float(pvout_buildable_annual) / 8760.0
                    cf_for_sizing = (
                        cf_centroid_val
                        if (cf_centroid_val is not None and cf_centroid_val > 0)
                        else cf_fallback
                    )
                    solar_data[r["site_id"]] = {
                        "lat": float(lat),
                        "lon": float(lon),
                        "capacity_mwp": float(cap) if pd.notna(cap) else None,
                        "cf_centroid": cf_centroid_val,
                        "cf_for_sizing": cf_for_sizing,
                        "solar_search_method": r.get("solar_search_method"),
                        "chosen_anchor_substation_name": r.get("chosen_anchor_substation_name"),
                        "solar_supply_share_pct": r.get("solar_supply_share_pct"),
                        "solar_delivered_share_pct": r.get("solar_delivered_share_pct"),
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

    # V3.7: Load 2030 site demand so we can size the project at actual required_mwp
    # instead of total buildable patch. Without this, capacity_assessment compares
    # substation capacity against the whole buildable area (e.g. 2,351 MWp for Batam
    # Aero Technic when only ~12 MWp is needed) and silently flags invest_substation.
    demand_lookup: dict[str, float] = {}
    if fct_site_demand_csv.exists():
        demand_df = pd.read_csv(fct_site_demand_csv)
        demand_2030 = demand_df[demand_df["year"] == DEMAND_YEAR_FOR_SIZING]
        for _, r in demand_2030.iterrows():
            if pd.notna(r.get("demand_mwh")):
                demand_lookup[r["site_id"]] = float(r["demand_mwh"])
        print(f"  V3.7: Loaded {DEMAND_YEAR_FOR_SIZING} demand for {len(demand_lookup)} sites")

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
        project_scale_mwp: float | None = None
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

            # V3.7: Size the project at Phase-1 = MEANINGFUL_SHARE_PCT × required_mwp,
            # capped by the buildable patch. This aligns cost math with the picker's
            # viability floor: the anchored picker qualifies patches at 30% of demand,
            # so sizing the project (and substation-upgrade costs) at 100% coverage
            # creates a logical gap — inflates $/kW and triggers false "Build
            # Substation" flags. Full-demand coverage is a later phase, not this model.
            # max_captive_capacity_mwp is the upper bound on the land.
            #
            # V3.7 NaN-safety: use cf_for_sizing (cf_centroid with buildable-best
            # fallback) so raster holes / edge pixels at the centroid don't silently
            # leave project_scale_mwp=None → capacity check falls back to full
            # buildable patch → false "Build Substation".
            demand_mwh = demand_lookup.get(site_id)
            cf = sd.get("cf_for_sizing")
            if demand_mwh and cf and cf > 0:
                required_mwp = demand_mwh / (8760.0 * cf)
                phase1_mwp = required_mwp * MEANINGFUL_SHARE_PCT
                if solar_cap_mwp is not None:
                    project_scale_mwp = round(min(phase1_mwp, solar_cap_mwp), 2)
                else:
                    project_scale_mwp = round(phase1_mwp, 2)

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
                haversine_km(
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

        # V3.1 + V3.7: Capacity assessment — proxy rows represent the rated nameplate
        # of an unmeasured substation at a given voltage class. We derate with a
        # different utilization (1 - HOSTING_CAPACITY_AVAILABILITY_PCT = 0.70, i.e.
        # only 30% of rated is assumed free for new injection) to reflect that the
        # proxy is an upper bound.
        # V3.8: For actual kapgi rows, look up the RUPTL signal to pick a tiered
        # default (uprate=85%, extension=75%, line_bay=70%, none=55%, unmatched=65%).
        # Proxy rows bypass RUPTL because their nameplate is already a guess — the
        # availability fraction (30%) already subsumes utilization uncertainty.
        kek_capacity_source = (
            nearest_to_kek.get("capacity_source", "unknown") if nearest_to_kek else "unknown"
        )
        if kek_capacity_source.startswith("proxy_"):
            kek_util_pct = 1.0 - HOSTING_CAPACITY_AVAILABILITY_PCT
            kek_ruptl_signal: dict | None = None
        else:
            kek_util_pct, kek_ruptl_signal = _ruptl_utilization_for_substation(
                nearest_to_kek["name"] if nearest_to_kek else None,
                nearest_to_kek.get("regpln") if nearest_to_kek else None,
                ruptl_lookup,
                fallback_pct=substation_utilization_pct,
            )

        # V3.7: Use project_scale_mwp (required capacity) for capacity checks, not the
        # buildable-patch maximum. The latter gave false invest_substation flags at
        # small-demand sites like Batam Aero Technic where a 2,351 MWp patch dwarfed
        # any realistic substation yet only ~12 MWp of solar was actually needed.
        assessed_mwp = project_scale_mwp if project_scale_mwp is not None else solar_cap_mwp

        cap_light, avail_mva = capacity_assessment(
            nearest_to_kek["capacity_mva"] if nearest_to_kek else None,
            assessed_mwp,
            utilization_pct=kek_util_pct,
        )

        # Derive grid integration category
        category = grid_integration_category(
            has_internal_substation=internal,
            dist_solar_to_substation_km=dist_solar_to_sub
            if np.isfinite(dist_solar_to_sub)
            else None,
            dist_kek_to_substation_km=dist_km,
            substation_capacity_mva=nearest_to_kek["capacity_mva"] if nearest_to_kek else None,
            substation_utilization_pct=kek_util_pct,
            solar_capacity_mwp=assessed_mwp,
            inter_substation_connected=inter_connected,
        )

        sd = solar_data.get(site_id, {})
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
                "nearest_substation_capacity_source": kek_capacity_source,
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
                # V3.8: RUPTL-derived per-substation utilization signal
                "substation_utilization_pct_effective": round(kek_util_pct, 3),
                "ruptl_project_type": (
                    kek_ruptl_signal.get("project_type_strongest") if kek_ruptl_signal else None
                ),
                "ruptl_strongest_status": (
                    kek_ruptl_signal.get("strongest_status") if kek_ruptl_signal else None
                ),
                "ruptl_earliest_target_year": (
                    kek_ruptl_signal.get("earliest_target_year") if kek_ruptl_signal else None
                ),
                "ruptl_mva_added_total": (
                    kek_ruptl_signal.get("mva_added_total") if kek_ruptl_signal else None
                ),
                "ruptl_match_confidence": (
                    kek_ruptl_signal.get("match_confidence") if kek_ruptl_signal else None
                ),
                # V3.7: surface anchored-picker diagnostics + project-scale sizing
                "solar_search_method": sd.get("solar_search_method"),
                "chosen_anchor_substation_name": sd.get("chosen_anchor_substation_name"),
                "solar_supply_share_pct": sd.get("solar_supply_share_pct"),
                "solar_delivered_share_pct": sd.get("solar_delivered_share_pct"),
                "project_scale_solar_mwp": project_scale_mwp,
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
    print("\nSubstation capacity source (V3.7):")
    print(df["nearest_substation_capacity_source"].value_counts(dropna=False).to_dict())
    print("\nRUPTL signal tier (V3.8):")
    print(df["ruptl_project_type"].value_counts(dropna=False).to_dict())
    print("\nEffective utilization % (V3.8):")
    print(df["substation_utilization_pct_effective"].describe().round(3).to_string())
    if "solar_search_method" in df.columns and df["solar_search_method"].notna().any():
        print("\nSolar picker method (V3.7):")
        print(df["solar_search_method"].value_counts(dropna=False).to_dict())
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
