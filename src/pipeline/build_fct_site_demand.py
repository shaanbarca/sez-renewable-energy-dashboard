"""
build_fct_site_demand — estimated 2030 electricity demand per site.

Method: area_ha (from kek_polygons.geojson) × energy intensity (MWh/ha/yr by zone_classification).
All estimates are provisional — replace with site-specific tenant load data when available.

Sources:
    processed: dim_sites.csv              — site_id, zone_classification, grid_region_id
    raw: kek_polygons.geojson             — Luas_ha (area in hectares), JenisKEK

Energy intensity assumptions: src/assumptions.py ENERGY_INTENSITY_MWH_PER_HA_YR
    Industri                → 800 MWh/ha/yr
    Industri dan Pariwisata → 500 MWh/ha/yr
    Pariwisata              → 150 MWh/ha/yr
    Jasa lainnya            → 250 MWh/ha/yr
    unknown/missing         → 400 MWh/ha/yr (default)

Fallback for missing area_ha (2 KEKs): category-median area among KEKs with known area.
If category has no peers with area, uses overall median.

Output columns:
    site_id                         str    primary key (matches dim_sites)
    year                            int    target year (2030)
    area_ha                         float  from kek_polygons; NaN if unavailable
    zone_classification             str    JenisKEK category
    energy_intensity_mwh_per_ha_yr  float  from ENERGY_INTENSITY_MWH_PER_HA_YR
    demand_mwh                      float  area_ha × energy_intensity (annual)
    demand_source                   str    "area_x_intensity" | "area_fallback_median"
    is_demand_provisional           bool   always True — placeholder until real load data
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.assumptions import (
    DEMAND_TARGET_YEAR,
    ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
    ENERGY_INTENSITY_MWH_PER_HA_YR,
)

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
    # Deduplicate: keep max area per site_id (largest polygon = primary boundary)
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce")
    df = df.groupby("site_id", as_index=False)["area_ha"].max()
    return df


def build_fct_site_demand(
    dim_sites_csv: Path = DIM_SITES_CSV,
    polygons_geojson: Path = POLYGONS_GEOJSON,
    target_year: int = DEMAND_TARGET_YEAR,
) -> pd.DataFrame:
    """Build one row per KEK with estimated 2030 electricity demand.

    Parameters
    ----------
    dim_sites_csv:
        Processed dim_sites.csv — provides site_id + zone_classification for all sites.
    polygons_geojson:
        Raw kek_polygons.geojson — provides Luas_ha per KEK.
    target_year:
        Year to stamp on demand rows (default: DEMAND_TARGET_YEAR = 2030).

    Returns
    -------
    pd.DataFrame
        One row per KEK. See module docstring for column spec.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_sites = pd.read_csv(dim_sites_csv)
    poly_areas = _load_polygon_areas(polygons_geojson)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    # Keep only what we need from dim_sites
    df = dim_sites[["site_id", "zone_classification"]].copy()

    # Join polygon areas (left join — dim_sites is authoritative for site list)
    df = df.merge(poly_areas, on="site_id", how="left")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────

    # 1. Map zone_classification → energy intensity
    df["energy_intensity_mwh_per_ha_yr"] = (
        df["zone_classification"]
        .map(ENERGY_INTENSITY_MWH_PER_HA_YR)
        .fillna(ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR)
    )

    # 2. Impute missing area_ha with category median, then overall median as last resort
    missing_mask = df["area_ha"].isna()
    if missing_mask.any():
        category_medians = df.groupby("zone_classification")["area_ha"].median()
        overall_median = df["area_ha"].median()

        df.loc[missing_mask, "area_ha"] = (
            df.loc[missing_mask, "zone_classification"].map(category_medians).fillna(overall_median)
        )

    # 3. Compute demand
    df["demand_mwh"] = df["area_ha"] * df["energy_intensity_mwh_per_ha_yr"]

    # 4. Provenance flags
    df["demand_source"] = "area_x_intensity"
    df.loc[missing_mask, "demand_source"] = "area_fallback_median"
    df["is_demand_provisional"] = True

    # 5. User override column — null by default; non-null = user-supplied value takes precedence
    df["demand_mwh_user"] = pd.NA
    df["demand_mwh_user"] = df["demand_mwh_user"].astype("Float64")

    # 6. Target year
    df["year"] = target_year

    return df[
        [
            "site_id",
            "year",
            "area_ha",
            "zone_classification",
            "energy_intensity_mwh_per_ha_yr",
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
    print("\nDemand by KEK type (MWh/yr):")
    summary = (
        df.groupby("zone_classification")
        .agg(
            count=("site_id", "count"),
            median_area_ha=("area_ha", "median"),
            total_demand_gwh=("demand_mwh", lambda x: x.sum() / 1000),
        )
        .round(1)
    )
    print(summary.to_string())
    print(f"\nFallback imputed: {(df['demand_source'] == 'area_fallback_median').sum()} KEKs")
    print(f"Total 2030 demand: {df['demand_mwh'].sum() / 1000:,.0f} GWh")


if __name__ == "__main__":
    main()
