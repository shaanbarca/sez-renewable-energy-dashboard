# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""End-to-end test for build_fct_geothermal_proximity.

Builds a tiny in-memory operating + pipeline geojson + sites CSV and runs
the pipeline. Catches schema regressions and tier-assignment bugs before
they can flow through the scorecard.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.build_fct_geothermal_proximity import build_fct_geothermal_proximity


def _write_geojson(path: Path, features: list[dict]) -> None:
    fc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [f["long"], f["lat"]]},
                "properties": {k: v for k, v in f.items() if k not in {"lat", "long"}},
            }
            for f in features
        ],
    }
    path.write_text(json.dumps(fc))


@pytest.fixture
def fixture_paths(tmp_path: Path) -> dict[str, Path]:
    operating = tmp_path / "geothermal_operating.geojson"
    _write_geojson(
        operating,
        [
            {  # Java — close to the Java site
                "id": "pltp_test_java",
                "name": "Test Java PLTP",
                "capacity_mw": 100.0,
                "lat": -7.0,
                "long": 107.5,
                "emission_factor_g_per_kwh": 50,
            }
        ],
    )

    pipeline = tmp_path / "geothermal_pipeline.geojson"
    _write_geojson(
        pipeline,
        [
            {  # Sumatra — pre-2030 pipeline
                "id": "pipeline_test_sumatra",
                "name": "Test Sumatra Pipeline",
                "capacity_mw": 50.0,
                "lat": 1.0,
                "long": 99.0,
                "target_year": 2028,
            },
            {  # Sulawesi — post-2030 pipeline
                "id": "pipeline_test_sulawesi",
                "name": "Test Sulawesi Pipeline",
                "capacity_mw": 25.0,
                "lat": 0.0,
                "long": 121.0,
                "target_year": 2033,
            },
        ],
    )

    sites = tmp_path / "dim_sites.csv"
    pd.DataFrame(
        [
            {
                "site_id": "java-near",
                "site_name": "Java Near",
                "latitude": -7.05,
                "longitude": 107.55,
            },
            {"site_id": "java-far", "site_name": "Java Far", "latitude": -8.5, "longitude": 110.0},
            {
                "site_id": "sumatra-pre",
                "site_name": "Sumatra",
                "latitude": 1.05,
                "longitude": 99.05,
            },
            {
                "site_id": "sulawesi-post",
                "site_name": "Sulawesi",
                "latitude": 0.05,
                "longitude": 121.05,
            },
            {"site_id": "papua-none", "site_name": "Papua", "latitude": -3.0, "longitude": 138.0},
        ]
    ).to_csv(sites, index=False)

    return {"operating": operating, "pipeline": pipeline, "sites": sites}


def test_pipeline_returns_one_row_per_site(fixture_paths: dict[str, Path]) -> None:
    df = build_fct_geothermal_proximity(
        operating_path=fixture_paths["operating"],
        pipeline_path=fixture_paths["pipeline"],
        sites_path=fixture_paths["sites"],
    )
    assert len(df) == 5
    assert set(df["site_id"]) == {
        "java-near",
        "java-far",
        "sumatra-pre",
        "sulawesi-post",
        "papua-none",
    }


def test_pipeline_emits_required_columns(fixture_paths: dict[str, Path]) -> None:
    """Schema contract — these columns are read by data_loader / SiteContext / map_layers."""
    df = build_fct_geothermal_proximity(
        operating_path=fixture_paths["operating"],
        pipeline_path=fixture_paths["pipeline"],
        sites_path=fixture_paths["sites"],
    )
    required = {
        "site_id",
        "nearest_geothermal_operating_id",
        "nearest_geothermal_operating_km",
        "nearest_geothermal_operating_mw",
        "nearest_geothermal_operating_emission_factor_g_per_kwh",
        "nearest_geothermal_pipeline_id",
        "nearest_geothermal_pipeline_km",
        "nearest_geothermal_pipeline_mw",
        "nearest_geothermal_pipeline_target_year",
        "geothermal_adjacency_tier",
    }
    assert required.issubset(df.columns)


def test_tier_assignment_matches_geometry(fixture_paths: dict[str, Path]) -> None:
    df = build_fct_geothermal_proximity(
        operating_path=fixture_paths["operating"],
        pipeline_path=fixture_paths["pipeline"],
        sites_path=fixture_paths["sites"],
    )
    by_id = df.set_index("site_id")["geothermal_adjacency_tier"].to_dict()
    assert by_id["java-near"] == "operating_within_50km"
    # java-far is ~280 km from operating Java plant — outside both operating brackets.
    # And no pipeline plant within 200 km. Confirm "none".
    assert by_id["java-far"] == "none"
    assert by_id["sumatra-pre"] == "pipeline_within_200km_pre2030"
    assert by_id["sulawesi-post"] == "pipeline_within_200km_post2030"
    assert by_id["papua-none"] == "none"


def test_pipeline_passes_through_emission_factor(fixture_paths: dict[str, Path]) -> None:
    """Per-plant NCG EF must reach the output (consumed by v4.1b CBAM Scope 2 correction)."""
    df = build_fct_geothermal_proximity(
        operating_path=fixture_paths["operating"],
        pipeline_path=fixture_paths["pipeline"],
        sites_path=fixture_paths["sites"],
    )
    java_near = df[df["site_id"] == "java-near"].iloc[0]
    assert java_near["nearest_geothermal_operating_emission_factor_g_per_kwh"] == 50.0


def test_pipeline_handles_missing_source_files(tmp_path: Path) -> None:
    """Absent source files → still emits one row per site with tier='none'.
    Lets the data_loader merge stay a no-op without errors.
    """
    sites = tmp_path / "dim_sites.csv"
    pd.DataFrame(
        [{"site_id": "s1", "site_name": "S1", "latitude": -7.0, "longitude": 107.0}]
    ).to_csv(sites, index=False)

    df = build_fct_geothermal_proximity(
        operating_path=tmp_path / "missing_operating.geojson",
        pipeline_path=tmp_path / "missing_pipeline.geojson",
        sites_path=sites,
    )
    assert len(df) == 1
    assert df.iloc[0]["geothermal_adjacency_tier"] == "none"
