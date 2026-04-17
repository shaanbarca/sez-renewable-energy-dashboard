# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_dim_sites — unified master dimension table for all site types.

Unions the existing 25 KEKs from dim_kek.csv with the industrial-sites frame
produced by ``build_industrial_sites`` (tracker-driven cement + residual manual
rows for steel/aluminium/fertilizer/nickel).

For KEKs: reads existing dim_kek.csv, maps columns to unified schema.
For industrial sites: reads ``industrial_sites_generated.csv`` (from the
``build_industrial_sites`` step), auto-assigns grid_region_id from nearest
substation's regpln field.

Output columns:
    site_id, site_name, site_type, sector, primary_product, province,
    latitude, longitude, area_ha, zone_classification, category, status,
    legal_basis, developer, reliability_req, grid_region_id,
    capacity_annual, capacity_annual_tonnes, technology, parent_company,
    cbam_product_type, business_sectors, data_vintage
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.model.site_types import SITE_TYPES, SiteType
from src.pipeline.geo_utils import haversine_km

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DATA_DIR = REPO_ROOT / "data"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
INDUSTRIAL_SITES_CSV = PROCESSED / "industrial_sites_generated.csv"
SUBSTATIONS_GEOJSON = DATA_DIR / "substation.geojson"

# Maps PLN region codes from substation.geojson regpln to our grid_region_id
_REGPLN_TO_GRID_REGION: dict[str, str] = {
    # Substation GeoJSON regpln values → our grid_region_id convention
    "Jawa-Bali": "JAVA_BALI",
    "Sumatera": "SUMATERA",
    "Kalimantan": "KALIMANTAN",
    "Sulawesi": "SULAWESI",
    "Maluku": "MALUKU",
    "Maluku-Papua": "MALUKU",
    "Papua": "PAPUA",
    "Nusa Tenggara": "NTB",
    # Pass-through for already-correct uppercase values
    "JAVA_BALI": "JAVA_BALI",
    "SUMATERA": "SUMATERA",
    "KALIMANTAN": "KALIMANTAN",
    "SULAWESI": "SULAWESI",
    "MALUKU": "MALUKU",
    "PAPUA": "PAPUA",
    "NTB": "NTB",
}


def _load_substation_points(geojson_path: Path) -> list[dict]:
    """Load substation lat/lon/regpln from substation.geojson."""
    if not geojson_path.exists():
        return []

    with open(geojson_path) as f:
        gj = json.load(f)

    points = []
    for feat in gj["features"]:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) >= 2 and props.get("regpln"):  # noqa: PLR2004  # [lon, lat] pair
            points.append(
                {
                    "lon": coords[0],
                    "lat": coords[1],
                    "regpln": props["regpln"],
                }
            )
    return points


def _assign_grid_region(lat: float, lon: float, substations: list[dict]) -> str | None:
    """Find the nearest substation and return its grid_region_id."""
    if not substations or pd.isna(lat) or pd.isna(lon):
        return None

    best_region = None
    best_dist = float("inf")

    for sub in substations:
        d = haversine_km(lat, lon, sub["lat"], sub["lon"])
        if d < best_dist:
            best_dist = d
            best_region = sub["regpln"]

    if best_region:
        return _REGPLN_TO_GRID_REGION.get(best_region, best_region)
    return None


def _prepare_kek_rows(dim_kek: pd.DataFrame) -> pd.DataFrame:
    """Map dim_kek columns to the unified schema."""
    df = dim_kek.copy()

    df["site_id"] = df["kek_id"]
    df["site_name"] = df["kek_name"]
    df["site_type"] = SiteType.KEK.value
    df["sector"] = "mixed"
    df["primary_product"] = None
    df["zone_classification"] = df.get("kek_type")
    df["capacity_annual"] = None
    df["capacity_annual_tonnes"] = None
    df["technology"] = None
    df["parent_company"] = df.get("developer")
    df["cbam_product_type"] = None  # KEKs use 3-signal detection

    return df


def build_dim_sites(
    dim_kek_csv: Path = DIM_KEK_CSV,
    industrial_sites_csv: Path = INDUSTRIAL_SITES_CSV,
    substations_geojson: Path = SUBSTATIONS_GEOJSON,
) -> pd.DataFrame:
    """Build unified dimension table with all site types.

    Parameters
    ----------
    dim_kek_csv
        Existing processed dim_kek.csv (25 KEKs).
    industrial_sites_csv
        Generated industrial sites CSV (output of ``build_industrial_sites``).
    substations_geojson
        PLN substation GeoJSON for grid region auto-assignment.
    """
    # Load substations for grid region assignment
    substations = _load_substation_points(substations_geojson)

    # ─── KEK rows ─────────────────────────────────────────────────────────────
    frames = []

    if dim_kek_csv.exists():
        dim_kek = pd.read_csv(dim_kek_csv)
        kek_rows = _prepare_kek_rows(dim_kek)
        frames.append(kek_rows)

    # ─── Industrial site rows ─────────────────────────────────────────────────
    if industrial_sites_csv.exists():
        industrial = pd.read_csv(industrial_sites_csv)

        # Set defaults for columns from the KEK schema
        industrial["zone_classification"] = None
        industrial["category"] = None
        industrial["status"] = "Active"
        industrial["legal_basis"] = None

        # Auto-assign grid_region_id from nearest substation
        if "grid_region_id" not in industrial.columns:
            industrial["grid_region_id"] = None

        missing_grid = industrial["grid_region_id"].isna()
        if missing_grid.any() and substations:
            industrial.loc[missing_grid, "grid_region_id"] = industrial.loc[missing_grid].apply(
                lambda r: _assign_grid_region(r["latitude"], r["longitude"], substations),
                axis=1,
            )

        # Set reliability_req from SiteTypeConfig defaults
        industrial["reliability_req"] = industrial["site_type"].map(
            lambda st: SITE_TYPES.get(SiteType(st), SITE_TYPES[SiteType.KEK]).default_reliability
        )

        industrial["business_sectors"] = None

        frames.append(industrial)

    if not frames:
        return pd.DataFrame()

    # ─── Union ────────────────────────────────────────────────────────────────
    unified = pd.concat(frames, ignore_index=True)

    # Stamp data vintage
    unified["data_vintage"] = date.today().isoformat()

    # Select and order final columns
    output_cols = [
        "site_id",
        "site_name",
        "site_type",
        "sector",
        "primary_product",
        "province",
        "latitude",
        "longitude",
        "area_ha",
        "zone_classification",
        "category",
        "status",
        "legal_basis",
        "developer",
        "reliability_req",
        "grid_region_id",
        "capacity_annual",
        "capacity_annual_tonnes",
        "technology",
        "parent_company",
        "cbam_product_type",
        "business_sectors",
        "data_vintage",
    ]

    # Only include columns that exist (graceful for missing optional cols)
    final_cols = [c for c in output_cols if c in unified.columns]
    unified = unified[final_cols]

    # Validate uniqueness
    if not unified["site_id"].is_unique:
        dupes = unified[unified["site_id"].duplicated(keep=False)]["site_id"].tolist()
        raise ValueError(f"Duplicate site_id values: {dupes}")

    return unified


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = build_dim_sites()
    out = PROCESSED / "dim_sites.csv"
    df.to_csv(out, index=False)

    print(f"dim_sites: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print(f"\nSite types: {df['site_type'].value_counts().to_dict()}")
    print(f"Sectors: {df['sector'].value_counts().to_dict()}")

    missing_grid = df["grid_region_id"].isna().sum()
    if missing_grid:
        print(f"\nWARNING: {missing_grid} site(s) missing grid_region_id:")
        print(f"  {df.loc[df['grid_region_id'].isna(), 'site_id'].tolist()}")


if __name__ == "__main__":
    main()
