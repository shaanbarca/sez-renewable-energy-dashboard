# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_industrial_sites — unified industrial-site CSV, tracker-driven where possible.

This step replaces the hand-curated ``data/industrial_sites/priority1_sites.csv``
as the direct input to ``build_dim_sites``. It produces a generated CSV whose rows
come from two kinds of sources:

1. **Public trackers** — deterministic filter over an upstream tracker. Currently:
   - Cement: all Active Indonesian plants in the GEM Global Cement Plant Tracker
     (``data/captive_power/gem_cement_plants.csv``).
   - Steel: all Active Indonesian plants in the GEM Global Iron & Steel Plant
     Tracker (``data/captive_power/gem_steel_plants.csv``).
   - Nickel: all Active "Integrated Industrial Area" entries in the CGSP nickel
     tracker (``data/captive_power/cgsp_nickel_tracker.csv``), with capacity
     summed from Processing-type child facilities within 10km, and any IIA
     falling within 5km of an existing KEK centroid excluded (avoids double-
     counting with KEK rows like Palu SEZ).
2. **Residual manual input** — rows from ``priority1_sites.csv`` for sectors that
   do not yet have an automated tracker step (aluminium, fertilizer). The CSV
   carries ``source_name`` / ``source_url`` / ``retrieved_date`` columns so
   every manually added row has explicit provenance.

Why this exists: the project requires site selection to be reproducible from
public source data. Anyone cloning the repo and running the pipeline must get the
same ``dim_sites`` — hand-editing CSVs breaks that. Tracker-driven sectors have
a deterministic filter rule; residual sectors stay manual until a tracker step is
added for them (see TODOS.md).

Output: ``outputs/data/processed/industrial_sites_generated.csv``
Schema matches ``priority1_sites.csv`` (minus provenance columns, which apply
only to residual manual rows).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.pipeline.geo_utils import haversine_km

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DATA_DIR = REPO_ROOT / "data"

GEM_CEMENT_CSV = DATA_DIR / "captive_power" / "gem_cement_plants.csv"
GEM_STEEL_CSV = DATA_DIR / "captive_power" / "gem_steel_plants.csv"
CGSP_NICKEL_CSV = DATA_DIR / "captive_power" / "cgsp_nickel_tracker.csv"
PRIORITY1_CSV = DATA_DIR / "industrial_sites" / "priority1_sites.csv"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"

OUTPUT_COLUMNS = [
    "site_id",
    "site_name",
    "site_type",
    "sector",
    "primary_product",
    "province",
    "latitude",
    "longitude",
    "area_ha",
    "capacity_annual",
    "capacity_annual_tonnes",
    "technology",
    "parent_company",
    "cbam_product_type",
]

# Sectors whose rows come from a tracker step and must be excluded from the
# residual manual CSV to prevent duplicates.
TRACKER_DRIVEN_SECTORS: set[str] = {"cement", "steel", "nickel"}

# Nickel filter knobs.
NICKEL_KEK_EXCLUSION_KM = 5.0  # drop CGSP IIA rows within this radius of any KEK
NICKEL_IIA_CHILD_RADIUS_KM = 20.0  # radius for summing child Processing capacity into IIA
# Rationale: most IIAs have children within 10km, but IWIP and IPIP need 20km to
# capture all on-site processing lines. IKIP and Stardust Estate still yield 0
# capacity at 20km (their nearest Processing facility is 37km and 21km respectively);
# those rows are retained as cluster sites but carry NaN capacity_annual_tonnes,
# which means the sector-intensity demand formula will produce NaN demand for them
# (acceptable — treated as placeholder until coord alignment improves).


def _slugify(name: str) -> str:
    """Deterministic slug for site_id — lowercase, spaces→dashes, alnum only."""
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _build_cement_rows(gem_cement_csv: Path = GEM_CEMENT_CSV) -> pd.DataFrame:
    """Read GEM cement tracker and emit dim-sites-compatible rows.

    Filter rule: all rows with ``status == "Active"``. Both Integrated and
    Grinding plant types are retained — Grinding stations still produce
    CBAM-covered cement product, though with lower electricity intensity
    (see TODOS.md for the grinding-vs-integrated demand refinement).
    """
    if not gem_cement_csv.exists():
        raise FileNotFoundError(f"GEM cement tracker not found: {gem_cement_csv}")

    gem = pd.read_csv(gem_cement_csv)
    active = gem[gem["status"] == "Active"].copy()

    rows = pd.DataFrame(
        {
            "site_id": active["plant_name"].map(_slugify),
            "site_name": active["plant_name"],
            "site_type": "standalone",
            "sector": "cement",
            "primary_product": "clinker",
            "province": active["province"],
            "latitude": active["latitude"],
            "longitude": active["longitude"],
            "area_ha": pd.NA,
            "capacity_annual": active["capacity_mtpa"].map(lambda x: f"{x} MTPA"),
            "capacity_annual_tonnes": active["capacity_mtpa"] * 1_000_000,
            "technology": active["plant_type"],
            "parent_company": active["parent_company"],
            "cbam_product_type": "cement",
        }
    )

    if not rows["site_id"].is_unique:
        dupes = rows[rows["site_id"].duplicated(keep=False)]["site_id"].tolist()
        raise ValueError(f"Duplicate cement site_id slugs from GEM tracker: {dupes}")

    return rows[OUTPUT_COLUMNS]


def _build_steel_rows(gem_steel_csv: Path = GEM_STEEL_CSV) -> pd.DataFrame:
    """Read GEM steel tracker and emit dim-sites-compatible rows.

    Filter rule: all rows with ``status == "Active"``. Both EAF and BF-BOF
    technologies are retained — both produce CBAM-covered crude steel but
    have very different electricity intensity. The ``technology`` column
    carries this forward so ``demand_intensity`` can branch on it.
    """
    if not gem_steel_csv.exists():
        raise FileNotFoundError(f"GEM steel tracker not found: {gem_steel_csv}")

    gem = pd.read_csv(gem_steel_csv)
    active = gem[gem["status"] == "Active"].copy()

    rows = pd.DataFrame(
        {
            "site_id": active["plant_name"].map(_slugify),
            "site_name": active["plant_name"],
            "site_type": "standalone",
            "sector": "steel",
            "primary_product": active["product_type"],
            "province": active["province"],
            "latitude": active["latitude"],
            "longitude": active["longitude"],
            "area_ha": pd.NA,
            "capacity_annual": active["capacity_tpa"].map(lambda x: f"{int(x)} TPA"),
            "capacity_annual_tonnes": active["capacity_tpa"].astype(float),
            "technology": active["technology"],
            "parent_company": active["parent_company"],
            "cbam_product_type": "iron_steel",
        }
    )

    if not rows["site_id"].is_unique:
        dupes = rows[rows["site_id"].duplicated(keep=False)]["site_id"].tolist()
        raise ValueError(f"Duplicate steel site_id slugs from GEM tracker: {dupes}")

    return rows[OUTPUT_COLUMNS]


def _province_from_city(province_city: str | float) -> str | None:
    """CGSP stores 'province_city' as 'Sulawesi Tengah, Morowali' — split off province."""
    if pd.isna(province_city):
        return None
    return str(province_city).split(",")[0].strip()


def _load_kek_centroids(dim_kek_csv: Path = DIM_KEK_CSV) -> list[tuple[float, float]]:
    """Load (lat, lon) tuples for every KEK. Empty list if dim_kek not yet built."""
    if not dim_kek_csv.exists():
        return []
    dk = pd.read_csv(dim_kek_csv)
    return [
        (float(r["latitude"]), float(r["longitude"]))
        for _, r in dk.iterrows()
        if pd.notna(r.get("latitude")) and pd.notna(r.get("longitude"))
    ]


def _within_any_kek(
    lat: float, lon: float, kek_centroids: list[tuple[float, float]], radius_km: float
) -> bool:
    return any(haversine_km(lat, lon, klat, klon) <= radius_km for klat, klon in kek_centroids)


def _sum_child_capacity(
    iia_lat: float,
    iia_lon: float,
    processing: pd.DataFrame,
    radius_km: float,
) -> tuple[float, str | None]:
    """Sum capacity (tons/yr) from Processing children within radius of an IIA centroid.

    Returns (total_capacity_tonnes, dominant_project_type). If no children found,
    returns (0.0, None).
    """
    if processing.empty:
        return 0.0, None

    dists = processing.apply(
        lambda r: haversine_km(iia_lat, iia_lon, r["latitude"], r["longitude"])
        if pd.notna(r["latitude"]) and pd.notna(r["longitude"])
        else float("inf"),
        axis=1,
    )
    within = processing[dists <= radius_km].copy()
    if within.empty:
        return 0.0, None

    capacity = pd.to_numeric(within["capacity"], errors="coerce").fillna(0).sum()
    type_counts = within["project_type"].value_counts()
    dominant = type_counts.index[0] if len(type_counts) else None
    return float(capacity), dominant


def _build_nickel_rows(
    cgsp_csv: Path = CGSP_NICKEL_CSV,
    dim_kek_csv: Path = DIM_KEK_CSV,
    kek_exclusion_km: float = NICKEL_KEK_EXCLUSION_KM,
    child_radius_km: float = NICKEL_IIA_CHILD_RADIUS_KM,
) -> pd.DataFrame:
    """Read CGSP nickel tracker and emit one cluster row per Integrated Industrial Area.

    Filter rules:
      1. ``status == "Active"``
      2. ``parent_project_type == "Integrated Industrial Area"`` (park-level entries)
      3. Exclude any IIA whose centroid lies within ``kek_exclusion_km`` of an
         existing KEK centroid — prevents double-counting with KEK rows like
         Palu SEZ (already in ``dim_kek``).

    For each surviving IIA, capacity is summed from Processing-type children
    within ``child_radius_km`` of the IIA centroid. Rationale: CGSP IIA rows
    carry the park boundary but not the production capacity; child Processing
    rows (NPI / FeNi / MHP / Nickel Sulfate / Nickel Matte) carry capacity but
    not park membership. Joining by geographic proximity is the only signal.

    All nickel IIAs are modeled as ``site_type = cluster`` with
    ``cbam_product_type = iron_steel`` (ferronickel and NPI fall under the EU
    CBAM iron & steel category per Annex I).
    """
    if not cgsp_csv.exists():
        raise FileNotFoundError(f"CGSP nickel tracker not found: {cgsp_csv}")

    df = pd.read_csv(cgsp_csv)
    iia = df[
        (df["status"] == "Active") & (df["parent_project_type"] == "Integrated Industrial Area")
    ].copy()
    processing = df[(df["status"] == "Active") & (df["parent_project_type"] == "Processing")].copy()

    kek_centroids = _load_kek_centroids(dim_kek_csv)
    if kek_centroids:
        iia = iia[
            ~iia.apply(
                lambda r: _within_any_kek(
                    r["latitude"], r["longitude"], kek_centroids, kek_exclusion_km
                ),
                axis=1,
            )
        ].copy()

    out_rows = []
    for _, r in iia.iterrows():
        name = str(r["project_name"]).strip()
        lat, lon = float(r["latitude"]), float(r["longitude"])
        cap_tonnes, dominant_type = _sum_child_capacity(lat, lon, processing, child_radius_km)
        out_rows.append(
            {
                "site_id": _slugify(name),
                "site_name": name,
                "site_type": "cluster",
                "sector": "nickel",
                "primary_product": "mixed_nickel",
                "province": _province_from_city(r.get("province_city")),
                "latitude": lat,
                "longitude": lon,
                "area_ha": pd.NA,
                "capacity_annual": f"{int(cap_tonnes)} TPA" if cap_tonnes else pd.NA,
                "capacity_annual_tonnes": cap_tonnes if cap_tonnes else pd.NA,
                "technology": dominant_type or "Mixed RKEF/HPAL",
                "parent_company": pd.NA,  # CGSP IIA rows carry no shareholder_ownership
                "cbam_product_type": "iron_steel",
            }
        )

    rows = pd.DataFrame(out_rows, columns=OUTPUT_COLUMNS)

    if rows.empty:
        return rows

    if not rows["site_id"].is_unique:
        dupes = rows[rows["site_id"].duplicated(keep=False)]["site_id"].tolist()
        raise ValueError(f"Duplicate nickel site_id slugs from CGSP tracker: {dupes}")

    return rows


def _load_residual_manual_rows(priority1_csv: Path = PRIORITY1_CSV) -> pd.DataFrame:
    """Load residual manual rows from priority1_sites.csv, excluding tracker-driven sectors.

    Provenance columns (``source_name`` / ``source_url`` / ``retrieved_date``)
    are kept on the source CSV for auditability but dropped here because
    ``dim_sites`` does not yet surface provenance. Every residual row must carry
    a non-empty ``source_url`` — the loader raises if any are missing.
    """
    if not priority1_csv.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    df = pd.read_csv(priority1_csv)
    residual = df[~df["sector"].isin(TRACKER_DRIVEN_SECTORS)].copy()

    # Enforce provenance: every residual manual row must carry a source URL.
    if "source_url" in residual.columns:
        missing = residual[residual["source_url"].isna() | (residual["source_url"] == "")]
        if not missing.empty:
            missing_ids = missing["site_id"].tolist()
            raise ValueError(
                f"Residual manual rows missing source_url (add to priority1_sites.csv): {missing_ids}"
            )

    for col in OUTPUT_COLUMNS:
        if col not in residual.columns:
            residual[col] = pd.NA
    return residual[OUTPUT_COLUMNS]


def build_industrial_sites(
    gem_cement_csv: Path = GEM_CEMENT_CSV,
    gem_steel_csv: Path = GEM_STEEL_CSV,
    cgsp_nickel_csv: Path = CGSP_NICKEL_CSV,
    priority1_csv: Path = PRIORITY1_CSV,
    dim_kek_csv: Path = DIM_KEK_CSV,
) -> pd.DataFrame:
    """Union tracker-driven rows with residual manual rows into one industrial-sites frame."""
    frames = [
        _build_cement_rows(gem_cement_csv),
        _build_steel_rows(gem_steel_csv),
        _build_nickel_rows(cgsp_nickel_csv, dim_kek_csv),
        _load_residual_manual_rows(priority1_csv),
    ]
    unified = pd.concat(frames, ignore_index=True)

    if not unified["site_id"].is_unique:
        dupes = unified[unified["site_id"].duplicated(keep=False)]["site_id"].tolist()
        raise ValueError(f"Duplicate site_id between tracker and residual manual rows: {dupes}")

    return unified


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df = build_industrial_sites()
    out = PROCESSED / "industrial_sites_generated.csv"
    df.to_csv(out, index=False)

    print(f"industrial_sites_generated: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    print(f"\nSectors: {df['sector'].value_counts().to_dict()}")
    print(f"Site types: {df['site_type'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
