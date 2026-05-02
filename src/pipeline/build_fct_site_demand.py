"""
build_fct_site_demand — estimated 2030 electricity demand per site.

# Dual-mode dispatch (V4.1 — fixed 2026-05-02)

Per `SITE_TYPES[site_type].demand_method` in `src/model/site_types.py`:

  • KEK / KI sites           → `area_based`
        demand = area_ha × ENERGY_INTENSITY_MWH_PER_HA_YR[zone_classification]
        (existing logic — area_ha sourced from kek_polygons.geojson;
        ENERGY_INTENSITY_MWH_PER_HA_YR keyed on JenisKEK / zone)

  • standalone / cluster     → `sector_intensity`
        demand = capacity_annual_tonnes × SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE[key]
        where `key` is resolved by `(sector, technology)` via
        `src/pipeline/demand_intensity.py::get_intensity_key`. Industrial
        sites without a usable capacity_annual_tonnes (data error) fall
        through to a dimension-less placeholder so the pipeline doesn't
        produce NaN demand.

Before this fix, the builder hardcoded `area_based` for all sites and
all 56 non-KEK sites silently received the fleet-median area_fallback
value (~376 GWh). Real per-site demand spans 2,000 GWh (Pupuk Sriwidjaja)
to 226,000 GWh (IMIP). See TODOS RV-pipeline-demand-regression.

# Output schema (forward-compat — new columns added, none removed)

    site_id                         str    primary key
    year                            int    target year (2030)
    area_ha                         float  KEK area; NaN for non-KEK
    zone_classification             str    KEK JenisKEK; NaN for non-KEK
    energy_intensity_mwh_per_ha_yr  float  area-mode value; NaN for non-KEK
    capacity_annual_tonnes          float  NEW — sector-mode input
    sector_intensity_key            str    NEW — which key in
                                           SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE
                                           was used (e.g. "steel_eaf")
    sector_intensity_mwh_per_tonne  float  NEW — sector-mode multiplier
    demand_mwh                      float  annual electricity demand
    demand_mwh_user                 float  user override (Float64 nullable)
    demand_source                   str    "area_x_intensity" |
                                           "area_fallback_median" |
                                           "sector_intensity"
    is_demand_provisional           bool   always True (placeholder)

Sources:
    processed: dim_sites.csv      — site_id, site_type, sector,
                                    capacity_annual_tonnes, technology,
                                    zone_classification, grid_region_id
    raw: kek_polygons.geojson     — Luas_ha (KEK area in hectares)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.assumptions import (
    DEMAND_TARGET_YEAR,
    ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
    ENERGY_INTENSITY_MWH_PER_HA_YR,
    SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE,
)
from src.model.site_types import SITE_TYPES, SiteType
from src.pipeline.demand_intensity import get_intensity_key

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "outputs" / "data" / "raw"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"
DIM_SITES_CSV = PROCESSED / "dim_sites.csv"


def _load_polygon_areas(geojson_path: Path) -> pd.DataFrame:
    """Extract site_id → area_ha from kek_polygons.geojson.

    The geojson contains duplicate slugs for multi-polygon KEKs (e.g. tanjung-sauh
    appears 6 times). We take the max Luas_ha per slug — the largest polygon is the
    primary zone boundary; smaller entries are sub-zones or artefacts.
    """
    with geojson_path.open() as f:
        features = json.load(f)["features"]

    rows = []
    for feat in features:
        props = feat["properties"]
        slug = props.get("slug") or props.get("id")
        if not slug:
            continue
        rows.append(
            {
                "site_id": slug,
                "area_ha": props.get("Luas_ha"),
            }
        )

    df = pd.DataFrame(rows)
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce")
    df = df.groupby("site_id", as_index=False)["area_ha"].max()
    return df


def _resolve_sector_intensity(sector: object, technology: object) -> tuple[str | None, float]:
    """Return (key, MWh-per-tonne) for the sector_intensity path.

    Falls back to (None, 0) if the sector isn't in the registry. Caller
    propagates NaN demand in that case so the pipeline doesn't silently
    publish a wrong number.
    """
    if sector is None or pd.isna(sector):
        return None, 0.0
    sector_str = str(sector).lower()
    tech_str = (
        str(technology).strip()
        if technology is not None and not pd.isna(technology) and str(technology).strip()
        else None
    )
    try:
        key = get_intensity_key(sector_str, tech_str)
    except KeyError:
        return None, 0.0
    return key, float(SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE[key])


def build_fct_site_demand(
    dim_sites_csv: Path = DIM_SITES_CSV,
    polygons_geojson: Path = POLYGONS_GEOJSON,
    target_year: int = DEMAND_TARGET_YEAR,
) -> pd.DataFrame:
    """Build one row per site with estimated 2030 electricity demand.

    Dispatches via SITE_TYPES[site_type].demand_method:
      - "area_based" (KEK, KI) → area_ha × intensity_per_ha
      - "sector_intensity" (standalone, cluster) → capacity_tonnes × intensity_per_tonne

    Schema additions (capacity_annual_tonnes, sector_intensity_key,
    sector_intensity_mwh_per_tonne) are forward-compat — older readers
    that ignore them keep working.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_sites = pd.read_csv(dim_sites_csv)
    poly_areas = _load_polygon_areas(polygons_geojson)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    keep_cols = [
        c
        for c in (
            "site_id",
            "site_type",
            "sector",
            "zone_classification",
            "capacity_annual_tonnes",
            "technology",
        )
        if c in dim_sites.columns
    ]
    df = dim_sites[keep_cols].copy()
    df = df.merge(poly_areas, on="site_id", how="left")

    # ─── DISPATCH ─────────────────────────────────────────────────────────────
    # Default to area_based for unknown site_types (legacy safety).
    def _method_for(site_type: object) -> str:
        if site_type is None or pd.isna(site_type):
            return "area_based"
        try:
            return SITE_TYPES[SiteType(site_type)].demand_method
        except (ValueError, KeyError):
            return "area_based"

    df["_method"] = (
        df["site_type"].apply(_method_for) if "site_type" in df.columns else "area_based"
    )

    # ─── area_based path (KEK / KI) ───────────────────────────────────────────
    area_mask = df["_method"] == "area_based"
    df["energy_intensity_mwh_per_ha_yr"] = float("nan")
    df.loc[area_mask, "energy_intensity_mwh_per_ha_yr"] = (
        df.loc[area_mask, "zone_classification"]
        .map(ENERGY_INTENSITY_MWH_PER_HA_YR)
        .fillna(ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR)
    )

    # Impute missing area_ha for area_based sites only — non-KEK sites
    # don't have an area to fall back to and shouldn't be muddled with
    # the KEK fleet median.
    area_missing = area_mask & df["area_ha"].isna()
    if area_missing.any():
        # Within the area_based subset, compute category and overall medians.
        area_subset = df.loc[area_mask, ["zone_classification", "area_ha"]]
        category_medians = area_subset.groupby("zone_classification")["area_ha"].median()
        overall_median = area_subset["area_ha"].median()
        df.loc[area_missing, "area_ha"] = (
            df.loc[area_missing, "zone_classification"].map(category_medians).fillna(overall_median)
        )

    # ─── sector_intensity path (standalone / cluster) ─────────────────────────
    df["sector_intensity_key"] = pd.NA
    df["sector_intensity_mwh_per_tonne"] = float("nan")
    sector_mask = df["_method"] == "sector_intensity"
    if sector_mask.any():
        resolved = df.loc[sector_mask].apply(
            lambda r: _resolve_sector_intensity(r.get("sector"), r.get("technology")),
            axis=1,
            result_type="expand",
        )
        # `resolved` is a 2-col frame: 0 = key, 1 = mwh_per_tonne.
        df.loc[sector_mask, "sector_intensity_key"] = resolved[0].values
        df.loc[sector_mask, "sector_intensity_mwh_per_tonne"] = resolved[1].values

    # ─── COMPUTE demand_mwh + provenance ──────────────────────────────────────
    df["demand_mwh"] = float("nan")
    df["demand_source"] = pd.NA

    # area_x_intensity (with successful imputation)
    df.loc[area_mask, "demand_mwh"] = (
        df.loc[area_mask, "area_ha"] * df.loc[area_mask, "energy_intensity_mwh_per_ha_yr"]
    )
    df.loc[area_mask, "demand_source"] = "area_x_intensity"
    df.loc[area_missing, "demand_source"] = "area_fallback_median"

    # sector_intensity (successful resolution + valid capacity)
    sector_valid = (
        sector_mask
        & df["capacity_annual_tonnes"].notna()
        & (df["capacity_annual_tonnes"] > 0)
        & df["sector_intensity_mwh_per_tonne"].gt(0)
    )
    df.loc[sector_valid, "demand_mwh"] = (
        df.loc[sector_valid, "capacity_annual_tonnes"]
        * df.loc[sector_valid, "sector_intensity_mwh_per_tonne"]
    )
    df.loc[sector_valid, "demand_source"] = "sector_intensity"

    # sector_mask sites that didn't resolve (missing capacity / unknown sector)
    sector_unresolved = sector_mask & ~sector_valid
    df.loc[sector_unresolved, "demand_source"] = "sector_intensity_missing_inputs"

    df["is_demand_provisional"] = True
    df["demand_mwh_user"] = pd.NA
    df["demand_mwh_user"] = df["demand_mwh_user"].astype("Float64")
    df["year"] = target_year

    return df[
        [
            "site_id",
            "year",
            "area_ha",
            "zone_classification",
            "energy_intensity_mwh_per_ha_yr",
            "capacity_annual_tonnes",
            "sector_intensity_key",
            "sector_intensity_mwh_per_tonne",
            "demand_mwh",
            "demand_mwh_user",
            "demand_source",
            "is_demand_provisional",
        ]
    ]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = build_fct_site_demand()
    out = PROCESSED / "fct_site_demand.csv"
    df.to_csv(out, index=False)

    print(f"fct_site_demand: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print()
    print("Demand by source:")
    summary = (
        df.groupby("demand_source", dropna=False)
        .agg(
            count=("site_id", "count"),
            median_mwh=("demand_mwh", "median"),
            total_gwh=("demand_mwh", lambda x: x.sum() / 1000),
        )
        .round(1)
    )
    print(summary.to_string())
    total_gwh = df["demand_mwh"].sum() / 1000
    print(f"\nTotal 2030 demand: {total_gwh:,.0f} GWh")


if __name__ == "__main__":
    main()
