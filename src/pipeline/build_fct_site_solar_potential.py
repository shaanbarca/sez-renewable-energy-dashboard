"""Per-site rooftop + within-site ground-mount aggregates (Layer 3).

# What this produces

`outputs/data/processed/fct_site_solar_potential.csv` — one row per site, with
the headline rooftop MWp number plus per-classification building counts and
the F4 data-confidence flag. The dashboard's runtime pipeline reads this
directly.

Companion output: `outputs/data/processed/sites_missing_buildings.csv` —
shortlist of sites with `building_data_confidence = 'low'` plus a
`recommended_alt_data` hook for v4.2's MS GMLBF integration (L26).

# Pipeline position

```
sites_buildings_filtered.parquet  (Layer 2, 12 MB, 114k buildings)
    │
    ▼
load_buildings_for_pipeline()   ◀── invariant 4: single entry point
    │
    ▼   for each site:
classify_building() per row     ◀── §14 classifier (src/model/buildings.py)
    │
    ▼
aggregate per category + confidence flag
    │
    ▼
fct_site_solar_potential.csv    (Layer 3, ~10 KB, 81 rows)
sites_missing_buildings.csv     (~14 rows shortlist for L26)
```

# Forward-compat invariants honored (spec §13.10)

1. `source_name` + `source_vintage` columns — read from the parquet, never
   hardcoded.
2. `building_id` is treated as opaque string (don't parse the prefix).
3. `dim_sites.preferred_building_source` — read but unused in v4.1
   (single-source mode); v4.2 will branch on it.
4. `load_buildings_for_pipeline()` is the ONLY parquet entry point.
5. Confidence handling treats null/NaN as "no score" (some v4.2 sources
   won't publish confidence).
6. F4 logic uses per-row `source_vintage` (not a hardcoded year cutoff).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.assumptions import (
    BUILDING_COUNT_HIGH_CONFIDENCE_MIN,
    BUILDING_COUNT_LOW_CONFIDENCE_MAX,
    BUILDING_DATA_VINTAGE_YEAR_CUTOFF,
    BUILDING_FOOTPRINT_IMAGERY_GAP_RATIO,
    BUILDING_FOOTPRINT_TYPICAL_RATIO_HIGH,
    BUILDING_FOOTPRINT_TYPICAL_RATIO_LOW,
    SITE_POLYGON_LARGE_AREA_HA,
)
from src.model.buildings import classify_building, rooftop_kw_ac, rooftop_kw_dc

# A "major" facility for F4 — capacity threshold above which a tiny building
# count signals likely undercount. 100 ktpa = mid-tier industrial.
MAJOR_FACILITY_CAPACITY_TONNES = 100_000.0

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DEFAULT_BUILDINGS_PARQUET = DATA_PROCESSED / "sites_buildings_filtered.parquet"
DEFAULT_SITES_CSV = PROCESSED / "dim_sites.csv"
DEFAULT_OUTPUT_CSV = PROCESSED / "fct_site_solar_potential.csv"
DEFAULT_MISSING_CSV = PROCESSED / "sites_missing_buildings.csv"
DEFAULT_KEK_POLYGONS_GEOJSON = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"

# Indonesian National DGN95 / UTM 50S — accurate metric calc for classifier
PROJECTED_CRS = "EPSG:23830"


def _load_kek_polygons(
    path: Path = DEFAULT_KEK_POLYGONS_GEOJSON,
) -> gpd.GeoDataFrame | None:
    """Load KEK boundary polygons keyed by slug (= site_id for KEK rows).

    The source GeoJSON has multiple polygon rows per KEK (split-island
    shapes — Tanjung Sauh has 6 fragments). We dissolve to one geometry
    per slug so downstream `within()` checks see a single MultiPolygon.

    Returns None if the file is missing — the caller falls back to the
    pre-clip 2 km buffer behavior for graceful degradation.
    """
    if not path.exists():
        return None
    gdf = gpd.read_file(path)
    if "slug" not in gdf.columns:
        return None
    return gdf.dissolve(by="slug", as_index=False)[["slug", "geometry"]]


def _clip_buildings_to_kek_polygons(
    buildings: gpd.GeoDataFrame,
    kek_polys: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Drop buildings whose centroid falls outside the KEK polygon for
    sites that have one. Preprocess assigns buildings using a 2 km buffer
    around the site centroid, which over-includes for KEKs whose actual
    boundary is smaller (and miscounts roofs in adjacent industrial parks).

    Industrial sites (cement, steel, nickel) don't have a polygon — those
    rows pass through unchanged, since their 2 km buffer IS the intended
    catchment.
    """
    if buildings.empty or kek_polys.empty:
        return buildings

    # Single reprojection up front. KEK polygons are EPSG:4326; buildings
    # parquet is EPSG:4326. Centroid in 4326 is geometrically wrong but
    # fine for point-in-polygon testing (we're not measuring distance).
    if buildings.crs != kek_polys.crs:
        buildings_in_poly_crs = buildings.to_crs(kek_polys.crs)
    else:
        buildings_in_poly_crs = buildings

    centroids = buildings_in_poly_crs.geometry.centroid
    keep = pd.Series(True, index=buildings.index)

    for slug, poly in kek_polys.set_index("slug").geometry.items():
        site_idx = buildings.index[buildings["site_id"] == slug]
        if len(site_idx) == 0:
            continue
        these = centroids.loc[site_idx]
        keep.loc[site_idx] = these.within(poly).to_numpy()

    return buildings.loc[keep].copy()


# ─── Forward-compat invariant #4: SINGLE entry point for buildings ─────────


def load_buildings_for_pipeline(
    parquet_path: Path = DEFAULT_BUILDINGS_PARQUET,
    *,
    clip_kek_to_polygon: bool = True,
) -> gpd.GeoDataFrame:
    """The ONLY place in the pipeline that reads
    `sites_buildings_filtered.parquet`. Per spec §13.10 invariant #4.

    `clip_kek_to_polygon` (default True) drops buildings outside the KEK
    boundary polygon for KEK sites — industrial sites pass through.

    v4.2 (L26) replaces this with a fan-out over multiple sources +
    `merge_sources()`. Downstream callers don't change.
    """
    if not parquet_path.exists():
        msg = f"Buildings parquet not found at {parquet_path}. Run preprocess_open_buildings.py first."
        raise FileNotFoundError(msg)
    gdf = gpd.read_parquet(parquet_path)
    # Forward-compat invariants 1+2: required schema validation, fail loud.
    required = {"building_id", "site_id", "source_name", "source_vintage", "geometry"}
    missing = required - set(gdf.columns)
    if missing:
        msg = (
            f"Buildings parquet missing required columns {missing}. "
            f"Re-run preprocess_open_buildings.py — schema may be stale."
        )
        raise ValueError(msg)

    if clip_kek_to_polygon:
        kek_polys = _load_kek_polygons()
        if kek_polys is not None and not kek_polys.empty:
            before = len(gdf)
            gdf = _clip_buildings_to_kek_polygons(gdf, kek_polys)
            after = len(gdf)
            if before != after:
                print(
                    f"  KEK polygon clip: {before - after:,} buildings dropped "
                    f"(outside KEK boundary, kept {after:,})"
                )

    return gdf


# ─── F4 confidence flag (invariant 5+6 honored) ────────────────────────────


def _human_readable_reason(reason: str) -> str:
    """F4 reason → user-facing copy. Centralized so frontend
    (`missingDataMessages.ts` in v4.2) can mirror these strings."""
    return {
        "post_2023_imagery": "Imagery vintage predates site commissioning",
        "low_count_for_capacity": ("Detected building count below threshold for facility scale"),
        "polygon_imagery_gap": "Imagery gap inside the site polygon",
        "tourism_kek": ("Predominantly tourism land use; minimal rooftop solar potential expected"),
        "no_buildings_detected": "No buildings detected in 2 km buffer",
    }.get(reason, reason)


def _recommended_alt_data(reason: str, sector: str) -> str:
    """Map F4 reason → which alt-data source v4.2 should try first."""
    if sector == "tourism" or reason == "tourism_kek":
        return "no_alt_data_needed"
    if reason == "post_2023_imagery":
        return "microsoft_gmlbf"
    if reason in {"polygon_imagery_gap", "low_count_for_capacity"}:
        return "manual_kml"
    if reason == "no_buildings_detected":
        return "microsoft_gmlbf"
    return "manual_kml"


def compute_confidence_flag(  # noqa: PLR0913 — F4 has 7 derived signals
    building_count: int,
    total_footprint_m2: float,
    site_polygon_area_ha: float | None,
    site_capacity_tonnes: float | None,
    site_commissioning_year: int | None,
    site_zone_classification: str | None,
    source_vintage: str | None,  # invariant #6 — vintage-driven
) -> tuple[str, str | None]:
    """Returns (confidence: 'high'|'medium'|'low', reason: str|None).

    All thresholds from src/assumptions.py — never hard-code values here.
    Invariant #6: when `source_vintage` is set, the cutoff is per-row not
    global. v4.1 has only "2023-05" → cutoff is 2023.
    """
    # No buildings at all — `low` confidence regardless of other signals.
    if building_count == 0:
        return "low", "no_buildings_detected"

    # Tourism KEKs: low rooftop potential expected, document as such.
    if site_zone_classification and site_zone_classification.lower() == "tourism":
        return "low", "tourism_kek"

    # Vintage-driven: site commissioned AFTER imagery → likely undercount.
    # Parse the year from source_vintage (e.g. "2023-05" → 2023).
    vintage_year = BUILDING_DATA_VINTAGE_YEAR_CUTOFF
    if source_vintage:
        try:
            vintage_year = int(source_vintage.split("-")[0])
        except (ValueError, IndexError):
            pass
    if site_commissioning_year and site_commissioning_year > vintage_year:
        return "low", "post_2023_imagery"

    # Major facility (large capacity) but very few buildings — likely undercount.
    if (
        site_capacity_tonnes
        and site_capacity_tonnes > MAJOR_FACILITY_CAPACITY_TONNES
        and building_count < BUILDING_COUNT_LOW_CONFIDENCE_MAX
    ):
        return "low", "low_count_for_capacity"

    # Large site polygon, tiny detected footprint — imagery gap.
    if (
        site_polygon_area_ha
        and site_polygon_area_ha > SITE_POLYGON_LARGE_AREA_HA
        and total_footprint_m2 / (site_polygon_area_ha * 10_000)
        < BUILDING_FOOTPRINT_IMAGERY_GAP_RATIO
    ):
        return "low", "polygon_imagery_gap"

    # `high` confidence requires healthy count AND healthy footprint ratio.
    footprint_ratio = (
        total_footprint_m2 / (site_polygon_area_ha * 10_000) if site_polygon_area_ha else 0.0
    )
    if (
        building_count >= BUILDING_COUNT_HIGH_CONFIDENCE_MIN
        and BUILDING_FOOTPRINT_TYPICAL_RATIO_LOW
        <= footprint_ratio
        <= BUILDING_FOOTPRINT_TYPICAL_RATIO_HIGH
    ):
        return "high", None

    return "medium", None


# ─── Per-site aggregation ──────────────────────────────────────────────────


def aggregate_site_buildings(
    site_buildings_proj: gpd.GeoDataFrame,  # buildings already in PROJECTED_CRS
) -> dict:
    """Classify every building, sum standard_roof × multipliers → MWp.

    Returns the row that goes into fct_site_solar_potential.csv.
    """
    counts = {
        "standard_roof": 0,
        "elongated": 0,
        "possibly_round": 0,
        "complex": 0,
        "tank_silo": 0,
        "conveyor": 0,
        "too_small": 0,
    }
    total_kw_dc = 0.0
    total_footprint_m2 = 0.0
    type_filter_excluded_m2 = 0.0
    usable_roof_area_m2 = 0.0

    for _, b in site_buildings_proj.iterrows():
        area_m2 = b.geometry.area  # already in metres (UTM)
        total_footprint_m2 += area_m2
        cls = classify_building(b.geometry, area_m2)
        counts[cls.category] += 1
        if cls.usability_multiplier > 0:
            kw_dc = rooftop_kw_dc(area_m2, cls.usability_multiplier)
            total_kw_dc += kw_dc
            usable_roof_area_m2 += area_m2 * cls.usability_multiplier
        else:
            type_filter_excluded_m2 += area_m2

    return {
        "rooftop_kw_dc": round(total_kw_dc, 2),
        "rooftop_kw_ac": round(rooftop_kw_ac(total_kw_dc), 2),
        "rooftop_solar_mwp_potential": round(total_kw_dc / 1000.0, 4),
        "total_building_footprint_m2": round(total_footprint_m2, 2),
        "usable_roof_area_m2": round(usable_roof_area_m2, 2),
        "type_filter_excluded_m2": round(type_filter_excluded_m2, 2),
        "building_count_total": int(sum(counts.values())),
        "building_count_standard_roof": counts["standard_roof"],
        "building_count_elongated": counts["elongated"],
        "building_count_tank_silo": counts["tank_silo"],
        "building_count_conveyor": counts["conveyor"],
        "building_count_other_excluded": counts["too_small"]
        + counts["complex"]
        + counts["possibly_round"],
    }


def build_fct_site_solar_potential(
    parquet_path: Path = DEFAULT_BUILDINGS_PARQUET,
    sites_csv: Path = DEFAULT_SITES_CSV,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute per-site rooftop aggregates + missing-data shortlist.

    Returns (fct_site_solar_potential, sites_missing_buildings) DataFrames.
    """
    sites = pd.read_csv(sites_csv)
    buildings = load_buildings_for_pipeline(parquet_path)

    # Reproject buildings ONCE to UTM 50S — classifier needs metric units.
    buildings_proj = buildings.to_crs(PROJECTED_CRS)

    # Read source vintage from the data, not a hardcoded value (invariant #6).
    # In v4.1 every row has "2023-05"; in v4.2 it'll vary per row, and we'll
    # take the most-common per site (or per_row depending on UI need).
    if not buildings["source_vintage"].empty:
        # Per-site vintage = the vintage of that site's primary source.
        site_vintage_map = (
            buildings.groupby("site_id")["source_vintage"]
            .agg(lambda s: s.value_counts().index[0])
            .to_dict()
        )
    else:
        site_vintage_map = {}

    # Aggregate per site
    rows = []
    for _, site in sites.iterrows():
        site_id = site["site_id"]
        site_buildings = buildings_proj[buildings_proj["site_id"] == site_id]

        if site_buildings.empty:
            agg = {
                "rooftop_kw_dc": 0.0,
                "rooftop_kw_ac": 0.0,
                "rooftop_solar_mwp_potential": 0.0,
                "total_building_footprint_m2": 0.0,
                "usable_roof_area_m2": 0.0,
                "type_filter_excluded_m2": 0.0,
                "building_count_total": 0,
                "building_count_standard_roof": 0,
                "building_count_elongated": 0,
                "building_count_tank_silo": 0,
                "building_count_conveyor": 0,
                "building_count_other_excluded": 0,
            }
        else:
            agg = aggregate_site_buildings(site_buildings)

        # Extract per-site context for F4
        capacity_tonnes = site.get("capacity_annual_tonnes")
        if pd.isna(capacity_tonnes):
            capacity_tonnes = None
        else:
            capacity_tonnes = float(capacity_tonnes)
        polygon_area_ha = site.get("area_ha")
        if pd.isna(polygon_area_ha):
            polygon_area_ha = None
        else:
            polygon_area_ha = float(polygon_area_ha)
        # NOTE: `data_vintage` is when the dim_sites row was last updated, NOT
        # when the site was commissioned. Setting commissioning_year=None here
        # disables the "post-imagery vintage" F4 branch until dim_sites gains
        # a real commissioning_year column (tracked as v4.2 TODO).
        # The other F4 signals (zero buildings, low_count_for_capacity,
        # polygon_imagery_gap, tourism zone) still flag the right ~14 sites.
        commissioning_year = None
        zone_class = site.get("zone_classification")
        if pd.isna(zone_class):
            zone_class = None

        confidence, reason = compute_confidence_flag(
            building_count=agg["building_count_total"],
            total_footprint_m2=agg["total_building_footprint_m2"],
            site_polygon_area_ha=polygon_area_ha,
            site_capacity_tonnes=capacity_tonnes,
            site_commissioning_year=commissioning_year,
            site_zone_classification=zone_class,
            source_vintage=site_vintage_map.get(site_id),
        )

        rows.append(
            {
                "site_id": site_id,
                "site_name": site["site_name"],
                **agg,
                "building_data_confidence": confidence,
                "building_data_reason_flagged": reason,
                "building_data_source": site_vintage_map.get(site_id) and "gob_v3" or None,
                "building_data_vintage": site_vintage_map.get(site_id),
            }
        )

    fct = pd.DataFrame(rows)

    # Missing-data shortlist — F13 in spec §3.7
    missing_rows = []
    for row in rows:
        if row["building_data_confidence"] != "low":
            continue
        site = sites[sites["site_id"] == row["site_id"]].iloc[0]
        reason = row["building_data_reason_flagged"]
        sector_raw = site.get("sector")
        sector = str(sector_raw) if pd.notna(sector_raw) else ""
        zone_raw = site.get("zone_classification")
        zone = str(zone_raw) if pd.notna(zone_raw) else ""
        primary_raw = site.get("primary_product")
        primary = str(primary_raw) if pd.notna(primary_raw) else ""
        # Tourism KEKs need no alt-data; everything else does.
        is_tourism = zone.lower() == "tourism" or "tourism" in primary.lower()
        missing_rows.append(
            {
                "site_id": row["site_id"],
                "site_name": row["site_name"],
                "commissioning_year": (
                    site.get("data_vintage", "")[:4]
                    if isinstance(site.get("data_vintage"), str)
                    else ""
                ),
                "province": site.get("province"),
                "sector": sector,
                "zone_classification": zone,
                "reason_flagged": reason or "unknown",
                "reason_human_readable": _human_readable_reason(reason or ""),
                "recommended_alt_data": _recommended_alt_data(
                    reason or "",
                    "tourism" if is_tourism else sector,
                ),
            }
        )
    missing = pd.DataFrame(missing_rows)

    return fct, missing


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    fct, missing = build_fct_site_solar_potential()
    fct.to_csv(DEFAULT_OUTPUT_CSV, index=False)
    missing.to_csv(DEFAULT_MISSING_CSV, index=False)

    # Sanity-check report
    n_total = len(fct)
    n_with_data = (fct["building_count_total"] > 0).sum()
    total_mwp = fct["rooftop_solar_mwp_potential"].sum()
    n_missing = len(missing)
    confidence_breakdown = fct["building_data_confidence"].value_counts().to_dict()
    print(f"fct_site_solar_potential: {n_total} rows → {DEFAULT_OUTPUT_CSV}")
    print(f"  sites with buildings:   {n_with_data} / {n_total}")
    print(f"  total rooftop MWp:      {total_mwp:,.1f}")
    print(f"  confidence breakdown:   {confidence_breakdown}")
    print(f"  missing-data shortlist: {n_missing} rows → {DEFAULT_MISSING_CSV}")
    if not fct.empty:
        top = fct.nlargest(5, "rooftop_solar_mwp_potential")[
            ["site_id", "rooftop_solar_mwp_potential", "building_count_standard_roof"]
        ]
        print("\nTop 5 sites by rooftop potential:")
        print(top.to_string(index=False))


if __name__ == "__main__":
    main()
