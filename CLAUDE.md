# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This repo is a Python modelling and analysis project for **Indonesia's KEK (Special Economic Zone) power competitiveness**. The goal is to build a dashboard that answers: "Which KEK can offer low-cost, low-carbon, reliable electricity — and what must change to get there?"

**Core documents — read these before making changes:**

| File | Purpose |
|------|---------|
| [PLAN.md](PLAN.md) | Full implementation plan: architecture, phases, data pipeline, Dash app design (with design review decisions) |
| [METHODOLOGY.md](METHODOLOGY.md) | Analytical methodology spec: LCOE formulas, PVOUT conversion, GEAS allocation, geospatial buildability filters — `src/model/basic_model.py` must implement this exactly |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Data pipeline contract: every raw input column and every derived column we need to produce, with status (✅/⚠️/❌/🔒) |
| [docs/Power_competitiveness_KEK_dashboard_plan.pdf](docs/Power_competitiveness_KEK_dashboard_plan.pdf) | Original product spec PDF |

## Setup

```bash
uv sync          # install all deps (creates .venv automatically)
uv run jupyter notebook notebooks/   # run notebooks
uv run pytest tests/                 # run tests
uv run ruff check src/ tests/        # lint
uv run ruff format src/ tests/       # format
```

Copy `.env_template` to `.env` and fill in credentials before running anything that touches S3 or maps:
```
MAPBOX_TOKEN=
S3_ACCESS_KEY=
S3_SECRET_ACCESS_KEY=
```

## Running code

There is no build step. The primary entry points are Jupyter notebooks:

```bash
jupyter notebook notebooks/
```

Key notebooks:
- [notebooks/kek_scraper.ipynb](notebooks/kek_scraper.ipynb) — scrapes KEK data from OSS/KEK portals using Playwright; produces raw outputs in `outputs/data/raw/`
- [notebooks/sample_end_to_end_policy_planning.ipynb](notebooks/sample_end_to_end_policy_planning.ipynb) — full baseline vs. policy scenario model: joins KEK attributes, PVOUT, RUPTL pipeline data, computes LCOE and action flags, produces charts
- [notebooks/sample_notebook.ipynb](notebooks/sample_notebook.ipynb) — template/scratch notebook

## Running tests

```bash
uv run pytest tests/
```

Test files are in `tests/`. `tests/test_model.py` has 60 tests across all functions in `src/model/basic_model.py` — all should pass.

## Model module

`src/model/basic_model.py` is the core pure-Python model (zero Dash dependency). Key functions:
- `pvout_daily_to_annual(pvout_daily)` — converts GeoTIFF daily kWh/kWp/day → annual (multiplies by 365, validates range)
- `capacity_factor_from_pvout(pvout_annual)` — divides by 8760
- `lcoe_solar(capex_usd_per_kw, fom, wacc, lifetime_yr, cf)` — CRF annuity LCOE formula; expects CAPEX in USD/kW
- `lcoe_solar_with_firming(...)` — adds firming adder (low/mid/high = +6/11/16 USD/MWh)
- `action_flags(...)` — returns `{solar_now, grid_first, firming_needed, plan_late}` boolean dict
- `geas_baseline_allocation(kek_df, ruptl_df)` — pro-rata GEAS allocation by demand share
- `geas_policy_allocation(kek_df, ruptl_df)` — priority-weighted by demand × PVOUT
- `build_scorecard(dim_kek, fct_demand, fct_pvout, fct_ruptl, ...)` — end-to-end pipeline

**CAPEX unit note**: `data/fct_tech_parameter.csv` stores CAPEX in MUSD/MWe — convert with `× 1000` before passing to `lcoe_solar()`.

## Architecture

The codebase follows a **star-schema data model** aligned with the dashboard plan. Data flows from raw inputs → precomputed fact/dimension tables → model outputs:

**Dimension tables** (`dim_*`):
- `dim_kek` — master KEK list with name, province, grid region, lat/lon
- `dim_tech_cost` (`data/dim_tech_variant.csv`, `data/fct_tech_parameter.csv`) — solar CAPEX/OPEX/lifetime from ESDM technology catalogue

**Fact tables** (`fct_*`):
- `fct_kek_resource` — PVOUT at centroid + best within 50–100 km (precomputed from GeoTIFF)
- `fct_kek_demand` — per-KEK demand estimates
- `fct_lcoe` — computed LCOE bands per KEK & tech (WACC-adjustable)
- `fct_ruptl_pipeline` — planned capacity additions by region/year from RUPTL
- `fct_grid_cost_proxy` — grid cost proxy (BPP when available, otherwise provisional)

**Key computed outputs** (see `sample_end_to_end_policy_planning.ipynb`):
- `lcoe_usd_mwh` — solar LCOE from `lcoe_solar(capex, fom, wacc, lifetime, cf)`
- `cf` derived from PVOUT via `capacity_factor_from_pvout(pvout) = pvout / 8760`
- Action flags: `solar_now`, `grid_first`, `firming_needed`, `plan_late` — boolean tags per KEK under baseline and policy scenarios
- `green_share_geas` — share of 2030 demand met by GEAS-allocated solar

**Solar resource data**: Global Solar Atlas GeoTIFFs in `data/` (zipped). PVOUT is extracted per KEK centroid and best-within-radius offline; the dashboard reads precomputed flat tables only.

**Utilities**:
- [utils/S3_loading.py](utils/S3_loading.py) — boto3 helpers for listing bucket contents and generating presigned URLs (eu-north-1 endpoint)
- [config/settings.py](config/settings.py) — `Config` class; reads all secrets from env vars

**Scraped raw data** lives in `outputs/data/raw/`:
- `kek_info_and_markers.csv`, `kek_polygons.geojson`, `kek_business_sectors.csv`, `oss_kek_all_pages.csv`

## Data notes

- The grid cost proxy uses PLN BPP (cost of supply), **not** the industrial tariff paid by KEK tenants. These differ — industrial tariffs are often subsidized below BPP. Label this distinction clearly in any output.
- RUPTL data (`fct_ruptl_pipeline`) is region/system-level, not KEK-specific. It provides grid system context only.
- `data/substation.geojson` contains substation locations for proximity analysis.
- `data/industrial_data/` contains a shapefile of Indonesian industrial facilities (50k+ employee firms, 2023).