# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""build_fct_geothermal_proximity — nearest geothermal plant per site + adjacency tier.

Sources
-------
- ``data/raw/geothermal_operating.geojson``  18 operating PLTPs (~2,460 MW).
  Compiled by ``scripts/compile_geothermal_operating.py`` from ESDM Technology
  Catalogue 2024 §1 + PLN PLTP list. Carries per-plant emission factors
  (g CO2/kWh) — Wayang Windu 73, Kamojang 73, Ulubelu 43, default 50.
- ``data/raw/geothermal_pipeline.geojson``  22 RUPTL 2025–2034 named pipeline
  projects (~2,191 MW). Compiled by ``scripts/compile_geothermal_pipeline.py``.
  Captures the largest projects from RUPTL Tabel 3.2 (RE Base) + 3.3 (ARED) —
  ~70% of the 5,157 MW total. Lower-confidence working-area aggregates fill the tail.
- ``outputs/data/processed/dim_sites.csv``  site centroids.

Output (one row per site_id)
----------------------------
- ``site_id`` — join key
- ``nearest_geothermal_operating_id``
- ``nearest_geothermal_operating_km`` — haversine distance to nearest operating PLTP
- ``nearest_geothermal_operating_mw``
- ``nearest_geothermal_operating_emission_factor_g_per_kwh``
- ``nearest_geothermal_pipeline_id``
- ``nearest_geothermal_pipeline_km``
- ``nearest_geothermal_pipeline_mw``
- ``nearest_geothermal_pipeline_target_year``
- ``geothermal_adjacency_tier`` —
  ``operating_within_50km`` / ``operating_within_200km`` /
  ``pipeline_within_200km_pre2030`` / ``pipeline_within_200km_post2030`` /
  ``none``

Methodology
-----------
- Reuses ``haversine_km`` from ``src.pipeline.geo_utils``.
- Tier logic lives in ``src.model.geothermal_adjacency.geothermal_tier`` (single
  source of truth so tests can target the function directly).
- ``geothermal_transmission_feasibility`` (same_island_connected / grid_first /
  cross_island_unconnected) is intentionally deferred — it requires merging
  site ``regpln`` with plant ``regpln`` plus ``inter_substation_connected``,
  which is more useful once the v4.1b hydro extension lands the broader
  dispatchable-RE adjacency model. Today the tier alone drives the F1 cascade
  via the ``dispatchable_re_coverage_pct`` translator.

See ``docs/refinement/v4_0_dashboard_fixes_spec.md`` §2.2 (Finding 2) and
METHODOLOGY_CONSOLIDATED.md §5.4 (Supply Blend cascade — F1 layer).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.model.geothermal_adjacency import geothermal_tier
from src.pipeline.geo_utils import haversine_km

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW = REPO_ROOT / "data" / "raw"

OPERATING_GEOJSON = RAW / "geothermal_operating.geojson"
PIPELINE_GEOJSON = RAW / "geothermal_pipeline.geojson"
SITES_CSV = PROCESSED / "dim_sites.csv"


def _load_geojson_points(path: Path) -> pd.DataFrame:
    """Load a GeoJSON FeatureCollection of Points → DataFrame."""
    if not path.exists():
        return pd.DataFrame()
    with path.open() as f:
        gj = json.load(f)
    rows = []
    for feat in gj.get("features", []):
        props = dict(feat.get("properties") or {})
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:  # noqa: PLR2004 — Point geometry needs [lon, lat]
            continue
        props["longitude"] = float(coords[0])
        props["latitude"] = float(coords[1])
        rows.append(props)
    return pd.DataFrame(rows)


def _nearest(
    site_lat: float,
    site_lon: float,
    plants: pd.DataFrame,
) -> tuple[str | None, float | None, dict | None]:
    """Return (id, dist_km, full_row_dict) for the plant closest to (site_lat, site_lon)."""
    if plants.empty:
        return None, None, None
    best_idx, best_dist = None, float("inf")
    for idx, plant in plants.iterrows():
        d = haversine_km(site_lat, site_lon, plant["latitude"], plant["longitude"])
        if d < best_dist:
            best_dist = d
            best_idx = idx
    if best_idx is None:
        return None, None, None
    row = plants.loc[best_idx].to_dict()
    return str(row.get("id") or ""), round(best_dist, 1), row


def build_fct_geothermal_proximity(
    operating_path: Path | str = OPERATING_GEOJSON,
    pipeline_path: Path | str = PIPELINE_GEOJSON,
    sites_path: Path | str = SITES_CSV,
) -> pd.DataFrame:
    """Match each site to its nearest operating + pipeline PLTP and assign a tier."""
    sites = pd.read_csv(sites_path)
    operating = _load_geojson_points(Path(operating_path))
    pipeline = _load_geojson_points(Path(pipeline_path))

    if sites.empty:
        return pd.DataFrame()
    if operating.empty and pipeline.empty:
        # Without source data we can still emit one "none" row per site so the
        # downstream merge doesn't drop columns.
        operating = pd.DataFrame(columns=["id", "latitude", "longitude"])
        pipeline = pd.DataFrame(
            columns=["id", "latitude", "longitude", "capacity_mw", "target_year"]
        )

    rows = []
    for _, site in sites.iterrows():
        slat, slon = site.get("latitude"), site.get("longitude")
        if pd.isna(slat) or pd.isna(slon):
            continue

        op_id, op_km, op_row = _nearest(float(slat), float(slon), operating)
        pl_id, pl_km, pl_row = _nearest(float(slat), float(slon), pipeline)

        op_mw = (op_row or {}).get("capacity_mw") if op_row else None
        op_ef = (op_row or {}).get("emission_factor_g_per_kwh") if op_row else None
        pl_mw = (pl_row or {}).get("capacity_mw") if pl_row else None
        pl_year = (pl_row or {}).get("target_year") if pl_row else None

        tier = geothermal_tier(
            operating_km=op_km,
            pipeline_km=pl_km,
            pipeline_year=int(pl_year) if pl_year is not None else None,
        )

        rows.append(
            {
                "site_id": site["site_id"],
                "nearest_geothermal_operating_id": op_id,
                "nearest_geothermal_operating_km": op_km,
                "nearest_geothermal_operating_mw": float(op_mw) if op_mw is not None else None,
                "nearest_geothermal_operating_emission_factor_g_per_kwh": (
                    float(op_ef) if op_ef is not None else None
                ),
                "nearest_geothermal_pipeline_id": pl_id,
                "nearest_geothermal_pipeline_km": pl_km,
                "nearest_geothermal_pipeline_mw": float(pl_mw) if pl_mw is not None else None,
                "nearest_geothermal_pipeline_target_year": (
                    int(pl_year) if pl_year is not None else None
                ),
                "geothermal_adjacency_tier": tier,
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = build_fct_geothermal_proximity()
    out = PROCESSED / "fct_geothermal_proximity.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    counts = df["geothermal_adjacency_tier"].value_counts(dropna=False)
    print(f"  Wrote {len(df)} rows → {out}")
    print(f"  Tier distribution:\n{counts.to_string()}")
