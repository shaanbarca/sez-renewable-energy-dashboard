# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Capture golden-master scorecard output for refactor parity testing.

Runs compute_scorecard_live with default assumptions against the currently
processed pipeline outputs and writes the result to
tests/fixtures/scorecard_golden.pkl (pickle, since list-valued columns like
modifier_badges don't round-trip cleanly through CSV).

Re-run this ONLY when the pipeline or model intentionally changes output.
"""

from __future__ import annotations

from pathlib import Path

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_wind_tech_defaults,
    prepare_resource_df,
)
from src.dash.logic import compute_scorecard_live, get_default_assumptions, get_default_thresholds

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "scorecard_golden.pkl"


def main() -> None:
    tables = load_all_data()
    resource_df = prepare_resource_df(tables)
    ruptl_metrics_df = compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"])
    wind_tech = load_wind_tech_defaults()

    scorecard = compute_scorecard_live(
        resource_df=resource_df,
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        ruptl_metrics_df=ruptl_metrics_df,
        demand_df=tables["fct_site_demand"],
        grid_df=tables["fct_grid_cost_proxy"],
        grid_cost_by_region=None,
        wind_tech=wind_tech,
    )

    # Deterministic ordering so cross-platform parquet comparison works
    scorecard = scorecard.sort_values("site_id").reset_index(drop=True)
    scorecard = scorecard.reindex(sorted(scorecard.columns), axis=1)

    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    scorecard.to_pickle(FIXTURE)

    print(
        f"Wrote {len(scorecard)} rows x {len(scorecard.columns)} cols → {FIXTURE.relative_to(REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
