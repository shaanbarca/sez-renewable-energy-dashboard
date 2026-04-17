# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Golden-master test: compute_scorecard_live output must match the fixture exactly.

Fixture captured pre-refactor via scripts/capture_scorecard_golden.py.
Re-run the capture script ONLY when the pipeline or model intentionally changes output.

This test is the safety net for the src/dash/logic.py package split. Every refactor
step must keep this test green.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_wind_tech_defaults,
    prepare_resource_df,
)
from src.dash.logic import compute_scorecard_live, get_default_assumptions, get_default_thresholds

FIXTURE = Path(__file__).parent / "fixtures" / "scorecard_golden.pkl"


@pytest.fixture(scope="module")
def scorecard_current() -> pd.DataFrame:
    tables = load_all_data()
    resource_df = prepare_resource_df(tables)
    ruptl_metrics_df = compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"])
    wind_tech = load_wind_tech_defaults()

    df = compute_scorecard_live(
        resource_df=resource_df,
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        ruptl_metrics_df=ruptl_metrics_df,
        demand_df=tables["fct_site_demand"],
        grid_df=tables["fct_grid_cost_proxy"],
        grid_cost_by_region=None,
        wind_tech=wind_tech,
    )
    df = df.sort_values("site_id").reset_index(drop=True)
    df = df.reindex(sorted(df.columns), axis=1)
    return df


@pytest.fixture(scope="module")
def scorecard_golden() -> pd.DataFrame:
    if not FIXTURE.exists():
        pytest.skip(f"golden fixture missing: {FIXTURE.relative_to(Path.cwd())}")
    return pd.read_pickle(FIXTURE)


def test_row_count_matches(scorecard_current: pd.DataFrame, scorecard_golden: pd.DataFrame) -> None:
    assert len(scorecard_current) == len(scorecard_golden)


def test_columns_match(scorecard_current: pd.DataFrame, scorecard_golden: pd.DataFrame) -> None:
    assert list(scorecard_current.columns) == list(scorecard_golden.columns)


def test_site_ids_match(scorecard_current: pd.DataFrame, scorecard_golden: pd.DataFrame) -> None:
    assert list(scorecard_current["site_id"]) == list(scorecard_golden["site_id"])


def test_full_dataframe_equals(
    scorecard_current: pd.DataFrame, scorecard_golden: pd.DataFrame
) -> None:
    """Bit-identical comparison. If this fails, inspect per-column diffs."""
    pd.testing.assert_frame_equal(scorecard_current, scorecard_golden, check_like=False)
