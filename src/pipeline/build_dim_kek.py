# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_dim_kek — master KEK dimension table.

Sources:
    outputs/data/raw/kek_info_and_markers.csv     lat/lon, kek_name, legal_basis, developer
    outputs/data/raw/kek_distribution_points.csv  category, status
    outputs/data/raw/kek_polygons.geojson         kek_type (JenisKEK), area_ha (Luas_ha)
    data/kek_grid_region_mapping.csv              grid_region_id, province, reliability_req

Output columns:
    kek_id           slug from portal — primary key
    kek_name         display name
    province         from kek_grid_region_mapping
    grid_region_id   PLN system (JAVA_BALI, SUMATERA, etc.)
    kek_type         JenisKEK from polygon file (Indonesian, e.g. "Industri dan Pariwisata")
    category         English category from distribution endpoint (e.g. "Manufacturing")
    status           operational status (Active / etc.)
    area_ha          Luas_ha from polygon file
    legal_basis      government decree reference from markers
    developer        developer entity from markers
    reliability_req  reliability requirement 0–1 (from mapping; category-based)
    latitude         centroid latitude
    longitude        centroid longitude
    data_vintage     ISO date this row was last built
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW = REPO_ROOT / "outputs" / "data" / "raw"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

MARKERS_CSV = RAW / "kek_info_and_markers.csv"
DIST_CSV = RAW / "kek_distribution_points.csv"
POLYGONS_GEOJSON = RAW / "kek_polygons.geojson"
MAPPING_CSV = REPO_ROOT / "data" / "kek_grid_region_mapping.csv"


def _load_polygon_attrs(geojson_path: Path) -> pd.DataFrame:
    """Extract kek_type and area_ha from kek_polygons.geojson keyed on slug.

    Polygon file has 30 features for 25 KEKs (some KEKs have sub-zone polygons).
    We keep the row with the largest area so we get the main KEK boundary.
    """
    with open(geojson_path) as f:
        gj = json.load(f)

    rows = []
    for feat in gj["features"]:
        props = feat.get("properties") or {}
        slug = props.get("slug")
        if not slug:
            continue
        rows.append(
            {
                "kek_id": slug,
                "kek_type": props.get("JenisKEK"),
                "area_ha": props.get("Luas_ha"),
            }
        )

    df = pd.DataFrame(rows)
    df["area_ha"] = pd.to_numeric(df["area_ha"], errors="coerce")
    # Dedup: keep the largest-area polygon per KEK (main boundary wins)
    df = df.sort_values("area_ha", ascending=False).drop_duplicates("kek_id")
    return df.reset_index(drop=True)


def build_dim_kek(
    markers_csv: Path = MARKERS_CSV,
    dist_csv: Path = DIST_CSV,
    polygons_geojson: Path = POLYGONS_GEOJSON,
    mapping_csv: Path = MAPPING_CSV,
) -> pd.DataFrame:
    """Join raw KEK sources into a clean dimension table. Returns DataFrame."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    markers_raw = pd.read_csv(markers_csv)
    dist_raw = pd.read_csv(dist_csv)
    mapping_raw = pd.read_csv(mapping_csv)
    poly_raw = _load_polygon_attrs(polygons_geojson)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    markers = markers_raw[
        ["slug", "title", "latitude", "longitude", "legalBasis", "developer"]
    ].rename(
        columns={
            "slug": "kek_id",
            "title": "kek_name",
            "legalBasis": "legal_basis",
        }
    )

    dist = dist_raw[["slug", "category.name", "status.name"]].rename(
        columns={
            "slug": "kek_id",
            "category.name": "category",
            "status.name": "status",
        }
    )

    mapping = mapping_raw[
        ["kek_id", "grid_region_id", "province", "reliability_req", "reliability_notes"]
    ]

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    df = (
        markers.merge(dist, on="kek_id", how="left")
        .merge(mapping, on="kek_id", how="left")
        .merge(poly_raw, on="kek_id", how="left")
    )

    df["data_vintage"] = date.today().isoformat()

    df = df[
        [
            "kek_id",
            "kek_name",
            "province",
            "grid_region_id",
            "kek_type",
            "category",
            "status",
            "area_ha",
            "legal_basis",
            "developer",
            "reliability_req",
            "reliability_notes",
            "latitude",
            "longitude",
            "data_vintage",
        ]
    ]

    missing = df["grid_region_id"].isna().sum()
    if missing:
        print(f"  WARNING: {missing} KEK(s) missing grid_region_id:")
        print(f"    {df.loc[df['grid_region_id'].isna(), 'kek_id'].tolist()}")

    return df


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "dim_kek.csv"
    df = build_dim_kek()
    df.to_csv(out, index=False)
    print(f"dim_kek: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print(
        df[["kek_id", "province", "grid_region_id", "kek_type", "area_ha"]].to_string(index=False)
    )


if __name__ == "__main__":
    main()
