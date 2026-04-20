"""Region→tier dispatch coverage test.

Guards against silent fallback to the default 15 km radius when a new grid region
appears in dim_sites.grid_region_id or a new PLN region appears in substation.geojson.regpln.

The anchored solar picker uses `_search_radius_km(grid_region_id)` which dispatches via
`_REGION_TO_TIER_KEY` to `KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM` (5 tiers). Any value
missing from the dispatch map falls back to `KEK_TO_SUBSTATION_THRESHOLD_KM` (15 km) —
fine for JAMALI, wrong for Kalimantan/Sulawesi/Papua. This test fails loudly when a
new region is added to data but not to the dispatch map.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.assumptions import (
    KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM,
    KEK_TO_SUBSTATION_THRESHOLD_KM,
)
from src.pipeline.build_fct_site_resource import _REGION_TO_TIER_KEY, _search_radius_km

REPO_ROOT = Path(__file__).resolve().parents[1]
DIM_SITES_PATH = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
SUBSTATIONS_PATH = REPO_ROOT / "data" / "substation.geojson"


def test_every_grid_region_id_resolves_to_a_tier() -> None:
    """Every dim_sites.grid_region_id value must resolve to a non-default tier."""
    df = pd.read_csv(DIM_SITES_PATH)
    values = sorted(df["grid_region_id"].dropna().unique().tolist())
    assert values, "dim_sites.grid_region_id is empty — check the pipeline"

    missing: list[str] = []
    for region_id in values:
        tier_key = _REGION_TO_TIER_KEY.get(region_id)
        if tier_key is None:
            missing.append(region_id)
            continue
        assert tier_key in KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM, (
            f"tier key '{tier_key}' (from grid_region_id '{region_id}') not in "
            f"KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM"
        )

    assert not missing, (
        f"grid_region_id values missing from _REGION_TO_TIER_KEY: {missing}. "
        f"They will fall through to {KEK_TO_SUBSTATION_THRESHOLD_KM} km default — "
        f"wrong for sparse regions like Kalimantan/Papua."
    )


def test_every_regpln_resolves_to_a_tier() -> None:
    """Every substation.regpln value must resolve to a non-default tier."""
    gdf = gpd.read_file(SUBSTATIONS_PATH)
    values = sorted(gdf["regpln"].dropna().unique().tolist())
    assert values, "substation.geojson has no regpln values"

    missing: list[str] = []
    for regpln in values:
        tier_key = _REGION_TO_TIER_KEY.get(regpln)
        if tier_key is None:
            missing.append(regpln)
            continue
        assert tier_key in KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM, (
            f"tier key '{tier_key}' (from regpln '{regpln}') not in "
            f"KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM"
        )

    assert not missing, (
        f"regpln values missing from _REGION_TO_TIER_KEY: {missing}. "
        f"They will fall through to {KEK_TO_SUBSTATION_THRESHOLD_KM} km default."
    )


def test_search_radius_returns_tier_value_for_known_regions() -> None:
    """Sanity check: `_search_radius_km` returns tier radius for known regions, not the default."""
    # JAVA_BALI is dense → 15 km (happens to equal the default, but that's a coincidence)
    assert _search_radius_km("JAVA_BALI") == 15.0
    # Kalimantan is sparse → 30 km (confirms we're not hitting the default)
    assert _search_radius_km("KALIMANTAN") == 30.0
    # PAPUA maps to MALUKU_PAPUA → 40 km
    assert _search_radius_km("PAPUA") == 40.0
    # Unmapped region falls back to default
    assert _search_radius_km("UNKNOWN_REGION") == KEK_TO_SUBSTATION_THRESHOLD_KM
    # None also falls back
    assert _search_radius_km(None) == KEK_TO_SUBSTATION_THRESHOLD_KM
