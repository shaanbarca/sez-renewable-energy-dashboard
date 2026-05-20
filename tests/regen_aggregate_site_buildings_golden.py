"""Regenerate `tests/fixtures/aggregate_site_buildings_golden.json`.

Run after intentional changes to the cascade (residential cluster detection,
factory-anchor filter, classifier thresholds) to update the locked baseline.

Usage:
    uv run python -m tests.regen_aggregate_site_buildings_golden

The output is a JSON dict keyed by site_id with the 13-field aggregate dict
(or null for sites with zero buildings — matches the skip-empty behavior in
`build_fct_site_solar_potential.py:837-852`).
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.pipeline.build_fct_site_solar_potential import (
    DEFAULT_BUILDINGS_PARQUET,
    DEFAULT_SITES_CSV,
    PROJECTED_CRS,
    _load_exclusion_polygons,
    aggregate_site_buildings,
)

GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "aggregate_site_buildings_golden.json"


def regenerate() -> None:
    if not DEFAULT_BUILDINGS_PARQUET.exists():
        raise SystemExit(f"Parquet missing: {DEFAULT_BUILDINGS_PARQUET}")

    sites = pd.read_csv(DEFAULT_SITES_CSV)
    site_ids = sorted(sites["site_id"].tolist())

    buildings = gpd.read_parquet(DEFAULT_BUILDINGS_PARQUET).to_crs(PROJECTED_CRS)
    exclusion_polys = _load_exclusion_polygons()

    out: dict[str, dict | None] = {}
    for sid in site_ids:
        sb = buildings[buildings["site_id"] == sid]
        if sb.empty:
            out[sid] = None
            continue
        out[sid] = aggregate_site_buildings(sb, site_id=sid, exclusion_polys=exclusion_polys)

    GOLDEN_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_FIXTURE.write_text(json.dumps(out, indent=2, sort_keys=True))
    nonempty = sum(1 for v in out.values() if v is not None)
    print(f"Wrote {GOLDEN_FIXTURE} — {len(out)} sites, {nonempty} non-empty")


if __name__ == "__main__":
    regenerate()
