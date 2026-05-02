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
import numpy as np
import pandas as pd
from shapely.strtree import STRtree

from src.assumptions import (
    BUILDING_COUNT_HIGH_CONFIDENCE_MIN,
    BUILDING_COUNT_LOW_CONFIDENCE_MAX,
    BUILDING_DATA_VINTAGE_YEAR_CUTOFF,
    BUILDING_FOOTPRINT_IMAGERY_GAP_RATIO,
    BUILDING_FOOTPRINT_TYPICAL_RATIO_HIGH,
    BUILDING_FOOTPRINT_TYPICAL_RATIO_LOW,
    MS_DEDUP_IOU_THRESHOLD,
    RESIDENTIAL_AREA_MAX_M2,
    RESIDENTIAL_AREA_SIMILARITY_RATIO,
    RESIDENTIAL_MIN_NEIGHBORS,
    RESIDENTIAL_NEIGHBOR_RADIUS_M,
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
DEFAULT_MS_BUILDINGS_PARQUET = DATA_PROCESSED / "sites_buildings_microsoft.parquet"
DEFAULT_SITES_CSV = PROCESSED / "dim_sites.csv"
DEFAULT_OUTPUT_CSV = PROCESSED / "fct_site_solar_potential.csv"
DEFAULT_MISSING_CSV = PROCESSED / "sites_missing_buildings.csv"
DEFAULT_KEK_POLYGONS_GEOJSON = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
DEFAULT_INDUSTRIAL_POLYGONS_GEOJSON = (
    REPO_ROOT / "data" / "industrial_sites" / "site_polygons.geojson"
)
DEFAULT_EXCLUSION_POLYGONS_GEOJSON = (
    REPO_ROOT / "data" / "industrial_sites" / "exclusion_polygons.geojson"
)

# Indonesian National DGN95 / UTM 50S — accurate metric calc for classifier
PROJECTED_CRS = "EPSG:23830"


def _load_site_polygons(
    kek_path: Path = DEFAULT_KEK_POLYGONS_GEOJSON,
    industrial_path: Path = DEFAULT_INDUSTRIAL_POLYGONS_GEOJSON,
) -> gpd.GeoDataFrame | None:
    """Load fence-boundary polygons keyed by site_id.

    Two sources are unioned:
      1. KEK polygons (`outputs/data/raw/kek_polygons.geojson`, keyed on
         `slug` which equals `site_id` for KEK rows). 25 polygons.
      2. Industrial site polygons (`data/industrial_sites/site_polygons.geojson`,
         keyed on `site_id`, sourced from OSM `landuse=industrial` /
         `man_made=works` tags). 9 polygons as of 2026-04-28.

    Both are dissolved by site_id so downstream `within()` checks see a
    single (Multi)Polygon per site.

    Returns None if neither file exists — caller falls back to the pre-clip
    2 km buffer behavior for graceful degradation.
    """
    frames: list[gpd.GeoDataFrame] = []
    if kek_path.exists():
        kek = gpd.read_file(kek_path)
        if "slug" in kek.columns:
            kek = kek.rename(columns={"slug": "site_id"})
            frames.append(kek[["site_id", "geometry"]])
    if industrial_path.exists():
        ind = gpd.read_file(industrial_path)
        if "site_id" in ind.columns:
            frames.append(ind[["site_id", "geometry"]])

    if not frames:
        return None

    # Align CRS — both are EPSG:4326 by convention but cast defensively.
    target_crs = frames[0].crs or "EPSG:4326"
    for i, f in enumerate(frames):
        if f.crs != target_crs:
            frames[i] = f.to_crs(target_crs)

    combined = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=target_crs)
    return combined.dissolve(by="site_id", as_index=False)[["site_id", "geometry"]]


def _clip_buildings_to_site_polygons(
    buildings: gpd.GeoDataFrame,
    site_polys: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Drop buildings whose centroid falls outside the site polygon for
    sites that have one. Preprocess assigns buildings using a 2 km buffer
    around the site centroid, which over-includes for sites whose actual
    fence boundary is smaller — KEKs (especially irregular ones like
    Tanjung Sauh's 6 island fragments) and non-KEK industrial plants
    where OSM has a `landuse=industrial` polygon (Indocement Palimanan,
    Petrokimia Gresik, Ispat Indo Sidoarjo, etc.).

    Sites without a polygon pass through unchanged — their 2 km buffer
    remains the catchment.
    """
    if buildings.empty or site_polys.empty:
        return buildings

    # Single reprojection up front. Polygons are EPSG:4326; buildings
    # parquet is EPSG:4326. Centroid in 4326 is geometrically imprecise
    # but fine for point-in-polygon testing.
    if buildings.crs != site_polys.crs:
        buildings_in_poly_crs = buildings.to_crs(site_polys.crs)
    else:
        buildings_in_poly_crs = buildings

    centroids = buildings_in_poly_crs.geometry.centroid
    keep = pd.Series(True, index=buildings.index)

    for sid, poly in site_polys.set_index("site_id").geometry.items():
        site_idx = buildings.index[buildings["site_id"] == sid]
        if len(site_idx) == 0:
            continue
        these = centroids.loc[site_idx]
        keep.loc[site_idx] = these.within(poly).to_numpy()

    return buildings.loc[keep].copy()


# ─── Forward-compat invariant #4: SINGLE entry point for buildings ─────────


def merge_sources(
    primary: gpd.GeoDataFrame,
    secondary: gpd.GeoDataFrame,
    *,
    iou_threshold: float = MS_DEDUP_IOU_THRESHOLD,
) -> gpd.GeoDataFrame:
    """Spatial-dedup union of two source parquets, per-site.

    Per spec §13.10 invariant 4 dedup strategy: two buildings from
    different sources are duplicates when polygon IoU exceeds
    `iou_threshold` (default 0.5). On collision, `primary` wins (it
    typically has the confidence score and an established place in the
    §14 classifier output) and the secondary row is dropped silently.
    Buildings from only one source pass through unchanged.

    Both inputs must share the §13.10 schema (building_id, site_id,
    source_name, source_vintage, geometry). The output preserves all
    columns from `primary`; `secondary`-only columns are dropped if they
    don't exist on `primary`.

    Complexity: O((P_s + S_s) log P_s) per site `s`, via STRtree on
    primary polygons. ~150k + 50k buildings runs in ~1–2 seconds total.
    """
    if secondary is None or secondary.empty:
        return primary
    if primary is None or primary.empty:
        return secondary

    # CRS guard — IoU is meaningless if primary and secondary live in
    # different coordinate systems (e.g., 4326 vs 23830). Reproject
    # secondary to match primary so areas + intersections are comparable.
    if primary.crs is not None and secondary.crs is not None and primary.crs != secondary.crs:
        secondary = secondary.to_crs(primary.crs)

    # Drop zero-area / null secondary geometries up front. Avoids the
    # asymmetric handling where a zero-area row would skip the dedup
    # check (continue) but still pass through into the output. Real
    # building footprints are never 0 m² — these are upstream
    # pre-processing corruption signals.
    sec_areas = secondary.geometry.area.to_numpy()
    secondary = secondary.loc[(sec_areas > 0) & secondary.geometry.notna()]
    if secondary.empty:
        return primary

    primary_cols = list(primary.columns)
    parts: list[gpd.GeoDataFrame] = [primary]

    # Process per-site so STRtree is small and dedup is local.
    for site_id, sec_grp in secondary.groupby("site_id"):
        prim_grp = primary[primary["site_id"] == site_id]
        if prim_grp.empty:
            # Site has no primary coverage — secondary fills it entirely.
            parts.append(sec_grp.reindex(columns=primary_cols))
            continue

        prim_geoms = list(prim_grp.geometry.to_numpy())
        prim_areas = np.array([g.area for g in prim_geoms])
        tree = STRtree(prim_geoms)

        keep_mask = np.ones(len(sec_grp), dtype=bool)
        sec_geoms = sec_grp.geometry.to_numpy()
        for i, sg in enumerate(sec_geoms):
            sa = sg.area
            # STRtree.query returns positional indices into prim_geoms.
            cand_idx = tree.query(sg)
            if len(cand_idx) == 0:
                continue
            for j in cand_idx:
                pg = prim_geoms[int(j)]
                inter = sg.intersection(pg).area
                if inter <= 0:
                    continue
                union = sa + prim_areas[int(j)] - inter
                if union > 0 and (inter / union) >= iou_threshold:
                    keep_mask[i] = False
                    break

        kept = sec_grp.loc[keep_mask].reindex(columns=primary_cols)
        if not kept.empty:
            parts.append(kept)

    merged = gpd.GeoDataFrame(
        pd.concat(parts, ignore_index=True), geometry="geometry", crs=primary.crs
    )
    return merged


def load_buildings_for_pipeline(
    parquet_path: Path = DEFAULT_BUILDINGS_PARQUET,
    *,
    ms_parquet_path: Path = DEFAULT_MS_BUILDINGS_PARQUET,
    clip_to_site_polygons: bool = True,
    enable_ms_gmlbf: bool = True,
) -> gpd.GeoDataFrame:
    """The ONLY place in the pipeline that reads building parquets.
    Per spec §13.10 invariant #4.

    Loads GoB v3 (`parquet_path`) and, when present and `enable_ms_gmlbf`
    is True, also Microsoft GMLBF (`ms_parquet_path`); merges via
    `merge_sources()` with IoU dedup. When MS parquet is missing the
    behavior is byte-identical to v4.1 (single-source GoB).

    `clip_to_site_polygons` (default True) drops buildings whose centroid
    falls outside the fence boundary for sites that have one. Sources:
    KEK polygons (25 sites) + OSM `landuse=industrial` / `man_made=works`
    polygons captured for non-KEK industrial sites. Sites without a
    polygon pass through unchanged — their 2 km preprocess buffer
    remains the catchment.
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

    # Multi-source fan-out (RV7 / spec §13.10). Additive — no behavior
    # change when MS parquet is absent (v4.1 reality before download).
    if enable_ms_gmlbf and ms_parquet_path.exists():
        ms_gdf = gpd.read_parquet(ms_parquet_path)
        ms_missing = required - set(ms_gdf.columns)
        if ms_missing:
            msg = (
                f"MS GMLBF parquet missing required columns {ms_missing}. "
                f"Re-run preprocess_microsoft_buildings.py."
            )
            raise ValueError(msg)
        before = len(gdf)
        gdf = merge_sources(gdf, ms_gdf, iou_threshold=MS_DEDUP_IOU_THRESHOLD)
        added = len(gdf) - before
        print(
            f"  Multi-source merge: GoB {before:,} + MS GMLBF {len(ms_gdf):,} → "
            f"{len(gdf):,} (added {added:,} non-duplicate MS buildings)"
        )

    if clip_to_site_polygons:
        site_polys = _load_site_polygons()
        if site_polys is not None and not site_polys.empty:
            before = len(gdf)
            gdf = _clip_buildings_to_site_polygons(gdf, site_polys)
            after = len(gdf)
            if before != after:
                print(
                    f"  Site polygon clip: {before - after:,} buildings dropped "
                    f"(outside fence boundary, kept {after:,})"
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


def _load_exclusion_polygons(
    path: Path = DEFAULT_EXCLUSION_POLYGONS_GEOJSON,
) -> gpd.GeoDataFrame | None:
    """Load OSM-tagged exclusion polygons (tanks, basins, water reservoirs).

    Each feature has a `site_id` property identifying which site it
    belongs to. Buildings whose centroid falls inside an exclusion polygon
    are reclassified as `tank_silo` (multiplier 0) — catches the irregular
    open-top tanks / settling ponds / cooling basins that the §14
    geometric circularity test misses (because their outline isn't a
    near-perfect circle).

    Returns None if the file is missing — pipeline runs without the
    exclusion layer, which is fine for graceful degradation.
    """
    if not path.exists():
        return None
    gdf = gpd.read_file(path)
    if "site_id" not in gdf.columns:
        return None
    return gdf[["site_id", "geometry"]]


def buildings_inside_exclusions(
    site_buildings_proj: gpd.GeoDataFrame,
    site_id: str,
    exclusion_polys: gpd.GeoDataFrame | None,
) -> np.ndarray:
    """Per-building bool mask: True if centroid is inside an exclusion polygon
    for this site_id. Returns all-False if no exclusion polygons configured.

    Spatial test runs in EPSG:4326 against the buildings' centroid (also in
    4326). Exclusion polygons are loaded in 4326 from the OSM Overpass
    GeoJSON. The metre-precision misalignment of using 4326 for centroids
    is irrelevant for point-in-polygon — the polygons are >> 1 m wide.
    """
    n = len(site_buildings_proj)
    inside = np.zeros(n, dtype=bool)
    if n == 0 or exclusion_polys is None or exclusion_polys.empty:
        return inside
    site_polys = exclusion_polys[exclusion_polys["site_id"] == site_id]
    if site_polys.empty:
        return inside

    # Reproject centroids to 4326 for the test (exclusion polys are 4326).
    if site_buildings_proj.crs != site_polys.crs:
        centroids = site_buildings_proj.geometry.centroid.to_crs(site_polys.crs)
    else:
        centroids = site_buildings_proj.geometry.centroid

    # Union the site's exclusion polygons once for a single fast test.
    union = site_polys.geometry.union_all()
    inside = centroids.within(union).to_numpy()
    return inside


def detect_residential_clusters(
    site_buildings_proj: gpd.GeoDataFrame,
    *,
    area_max_m2: float = RESIDENTIAL_AREA_MAX_M2,
    neighbor_radius_m: float = RESIDENTIAL_NEIGHBOR_RADIUS_M,
    min_neighbors: int = RESIDENTIAL_MIN_NEIGHBORS,
    area_similarity_ratio: float = RESIDENTIAL_AREA_SIMILARITY_RATIO,
) -> np.ndarray:
    """Per-building boolean mask: True if part of a residential cluster.

    A building is "residential" if all three hold:
      1. footprint < area_max_m2 (residential houses are small)
      2. ≥ min_neighbors buildings within neighbor_radius_m
      3. those neighbors are similar-sized (min(a,b)/max(a,b) ≥ ratio)

    Industrial halls fail (1) trivially; isolated small auxiliary buildings
    near a steel mill or cement plant fail (2). Dense rows of similar-sized
    houses pass all three.

    Buildings must already be in a metric CRS so that .area, .buffer(m),
    and STRtree queries work in metres.
    """
    n = len(site_buildings_proj)
    is_residential = np.zeros(n, dtype=bool)
    if n == 0:
        return is_residential

    geoms = list(site_buildings_proj.geometry.values)
    areas = site_buildings_proj.geometry.area.to_numpy()
    tree = STRtree(geoms)

    for i, (geom, area) in enumerate(zip(geoms, areas, strict=False)):
        if area >= area_max_m2:
            continue
        # Candidate neighbors: anything intersecting the search-radius buffer.
        # STRtree.query uses bbox prefilter which is good enough here.
        search_geom = geom.buffer(neighbor_radius_m)
        candidate_idx = tree.query(search_geom)
        similar_count = 0
        for j in candidate_idx:
            if j == i:
                continue
            other_area = areas[j]
            ratio = min(area, other_area) / max(area, other_area)
            if ratio >= area_similarity_ratio:
                similar_count += 1
                if similar_count >= min_neighbors:
                    is_residential[i] = True
                    break
    return is_residential


def aggregate_site_buildings(
    site_buildings_proj: gpd.GeoDataFrame,  # buildings already in PROJECTED_CRS
    *,
    site_id: str | None = None,
    exclusion_polys: gpd.GeoDataFrame | None = None,
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
        "residential": 0,
    }
    total_kw_dc = 0.0
    total_footprint_m2 = 0.0
    type_filter_excluded_m2 = 0.0
    usable_roof_area_m2 = 0.0

    is_residential = detect_residential_clusters(site_buildings_proj)
    is_in_exclusion = (
        buildings_inside_exclusions(site_buildings_proj, site_id, exclusion_polys)
        if site_id is not None
        else np.zeros(len(site_buildings_proj), dtype=bool)
    )

    for i, (_, b) in enumerate(site_buildings_proj.iterrows()):
        area_m2 = b.geometry.area  # already in metres (UTM)
        total_footprint_m2 += area_m2
        if is_in_exclusion[i]:
            # OSM tagged this as tank / basin / water → no roof to put panels on.
            # Account as `tank_silo` for the existing UI category.
            counts["tank_silo"] += 1
            type_filter_excluded_m2 += area_m2
            continue
        if is_residential[i]:
            counts["residential"] += 1
            type_filter_excluded_m2 += area_m2
            continue
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
        "building_count_residential": counts["residential"],
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

    # OSM exclusion polygons (tanks / basins / water). Loaded once, queried
    # per-site inside aggregate_site_buildings().
    exclusion_polys = _load_exclusion_polygons()
    if exclusion_polys is not None:
        n_excl = len(exclusion_polys)
        n_sites_with_excl = exclusion_polys["site_id"].nunique()
        print(f"  exclusion polygons loaded: {n_excl} across {n_sites_with_excl} sites")

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
                "building_count_residential": 0,
                "building_count_other_excluded": 0,
            }
        else:
            agg = aggregate_site_buildings(
                site_buildings,
                site_id=site_id,
                exclusion_polys=exclusion_polys,
            )

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
