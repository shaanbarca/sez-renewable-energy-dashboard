"""
run_pipeline.py — KEK power competitiveness data pipeline orchestrator.

Usage:
    uv run python run_pipeline.py            # run all steps
    uv run python run_pipeline.py dim_sites  # run one step by name

Adding a new data source:
    1. Copy src/pipeline/TEMPLATE.py → src/pipeline/build_<name>.py
    2. Implement build_<name>() → pd.DataFrame following the RAW/STAGING/TRANSFORM pattern
    3. Import it below and add one Step(...) entry to PIPELINE

DAG (dependencies enforced by topological sort at runtime):

    raw/                          ← source files, never modified
    data/                         ← manual lookups + ESDM catalogue

    Stage 1 — Dimensions (no processed deps)
    ├── dim_kek                      raw: kek_info_and_markers + kek_polygons.geojson
    ├── industrial_sites_generated   data: GEM cement tracker + priority1_sites.csv (residual manual)
    ├── dim_sites                    processed: dim_kek + industrial_sites_generated
    │                                data: substation.geojson (grid region auto-assign)
    └── dim_tech_cost                data: dim_tech_variant + fct_tech_parameter (TECH006)

    Stage 2 — Facts (read from processed/dim_*)
    ├── fct_site_resource    processed: dim_sites + data: GlobalSolarAtlas GeoTIFF
    ├── fct_site_demand      processed: dim_sites + raw: kek_polygons.geojson (area_ha × intensity)
    ├── fct_grid_cost_proxy  processed: dim_sites + hardcoded Permen ESDM 7/2024 tariffs
    └── fct_ruptl_pipeline   hardcoded RUPTL 2025-2034 extraction

    Stage 3 — Computed (read from processed/fct_* + dim_*)
    ├── fct_substation_proximity  processed: dim_sites + data/substation.geojson + raw/kek_polygons.geojson
    └── fct_lcoe          processed: dim_sites + fct_site_resource + dim_tech_cost + fct_substation_proximity

    Stage 4 — Final scorecard (joins everything)
    └── fct_site_scorecard processed: all above

All outputs → outputs/data/processed/
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

from src.pipeline.build_dim_kek import build_dim_kek
from src.pipeline.build_dim_sites import build_dim_sites
from src.pipeline.build_dim_tech_cost import build_dim_tech_cost
from src.pipeline.build_dim_tech_cost_wind import build_dim_tech_cost_wind
from src.pipeline.build_fct_captive_coal import build_captive_coal_summary
from src.pipeline.build_fct_captive_nickel import build_captive_nickel_summary
from src.pipeline.build_fct_grid_cost_proxy import build_fct_grid_cost_proxy
from src.pipeline.build_fct_lcoe import build_fct_lcoe
from src.pipeline.build_fct_lcoe_wind import build_fct_lcoe_wind
from src.pipeline.build_fct_ruptl_pipeline import build_fct_ruptl_pipeline
from src.pipeline.build_fct_site_demand import build_fct_site_demand
from src.pipeline.build_fct_site_resource import build_fct_site_resource
from src.pipeline.build_fct_site_scorecard import build_fct_site_scorecard
from src.pipeline.build_fct_site_wind_resource import build_fct_site_wind_resource
from src.pipeline.build_fct_substation_proximity import build_fct_substation_proximity
from src.pipeline.build_industrial_sites import build_industrial_sites


@dataclass
class Step:
    name: str
    fn: Callable[[], pd.DataFrame]
    output: str  # filename under out_dir
    depends_on: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline definition — add new data sources here (one Step per source)
# ─────────────────────────────────────────────────────────────────────────────
PIPELINE: list[Step] = [
    # Stage 1: Dimensions
    Step("dim_kek", build_dim_kek, "dim_kek.csv"),
    Step(
        "industrial_sites_generated",
        build_industrial_sites,
        "industrial_sites_generated.csv",
    ),
    Step(
        "dim_sites",
        build_dim_sites,
        "dim_sites.csv",
        depends_on=["dim_kek", "industrial_sites_generated"],
    ),
    Step("dim_tech_cost", build_dim_tech_cost, "dim_tech_cost.csv"),
    Step("dim_tech_cost_wind", build_dim_tech_cost_wind, "dim_tech_cost_wind.csv"),
    # Stage 2: Facts
    Step(
        "fct_site_resource",
        build_fct_site_resource,
        "fct_site_resource.csv",
        depends_on=["dim_sites"],
    ),
    Step(
        "fct_site_wind_resource",
        build_fct_site_wind_resource,
        "fct_site_wind_resource.csv",
        depends_on=["dim_sites"],
    ),
    Step("fct_site_demand", build_fct_site_demand, "fct_site_demand.csv", depends_on=["dim_sites"]),
    Step(
        "fct_grid_cost_proxy",
        build_fct_grid_cost_proxy,
        "fct_grid_cost_proxy.csv",
        depends_on=["dim_sites"],
    ),
    Step("fct_ruptl_pipeline", build_fct_ruptl_pipeline, "fct_ruptl_pipeline.csv"),
    Step(
        "fct_captive_coal_summary",
        build_captive_coal_summary,
        "fct_captive_coal_summary.csv",
        depends_on=["dim_sites"],
    ),
    Step(
        "fct_captive_nickel_summary",
        build_captive_nickel_summary,
        "fct_captive_nickel_summary.csv",
        depends_on=["dim_sites"],
    ),
    # Stage 3: Computed
    Step(
        "fct_substation_proximity",
        build_fct_substation_proximity,
        "fct_substation_proximity.csv",
        depends_on=["dim_sites"],
    ),
    Step(
        "fct_lcoe",
        build_fct_lcoe,
        "fct_lcoe.csv",
        depends_on=["dim_sites", "fct_site_resource", "dim_tech_cost", "fct_substation_proximity"],
    ),
    Step(
        "fct_lcoe_wind",
        build_fct_lcoe_wind,
        "fct_lcoe_wind.csv",
        depends_on=[
            "dim_sites",
            "fct_site_wind_resource",
            "dim_tech_cost_wind",
            "fct_substation_proximity",
        ],
    ),
    # Stage 4: Final scorecard
    Step(
        "fct_site_scorecard",
        build_fct_site_scorecard,
        "fct_site_scorecard.csv",
        depends_on=[
            "dim_sites",
            "fct_lcoe",
            "fct_lcoe_wind",
            "fct_grid_cost_proxy",
            "fct_ruptl_pipeline",
            "fct_site_demand",
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Topological sort — enforces depends_on ordering at runtime
# ─────────────────────────────────────────────────────────────────────────────
def _topo_sort(steps: list[Step]) -> list[Step]:
    """Return steps in dependency order. Raises ValueError on unknown deps or cycles."""
    index = {s.name: s for s in steps}
    visited: set[str] = set()
    in_progress: set[str] = set()
    order: list[Step] = []

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in in_progress:
            raise ValueError(f"Circular dependency detected involving '{name}'")
        if name not in index:
            raise ValueError(f"Unknown dependency '{name}'")
        in_progress.add(name)
        for dep in index[name].depends_on:
            visit(dep)
        in_progress.discard(name)
        visited.add(name)
        order.append(index[name])

    for step in steps:
        visit(step.name)

    return order


def run(
    steps: list[Step] = PIPELINE,
    out_dir: Path = PROCESSED,
    only: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Run all pipeline steps in dependency order, writing each output to out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, pd.DataFrame] = {}

    if only:
        available = [s.name for s in steps]
        if only not in available:
            print(f"No step named '{only}'. Available: {available}")
            sys.exit(1)
        # Single-step mode: skip topo sort (deps assumed already built on disk)
        steps = [s for s in steps if s.name == only]
    else:
        steps = _topo_sort(steps)

    print(f"Pipeline: {len(steps)} step(s) → {out_dir.relative_to(REPO_ROOT)}/\n")

    for i, step in enumerate(steps, 1):
        print(f"  [{i}/{len(steps)}] {step.name}", end=" ... ", flush=True)
        try:
            df = step.fn()
            out_path = out_dir / step.output
            df.to_csv(out_path, index=False)
            results[step.name] = df
            print(f"{len(df)} rows  →  {step.output}")
        except Exception as exc:
            print("FAILED")
            print(f"          {type(exc).__name__}: {exc}")
            sys.exit(1)

    print(f"\n  Done. {len(steps)} table(s) written to {out_dir.relative_to(REPO_ROOT)}/")
    return results


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    run(only=only)
