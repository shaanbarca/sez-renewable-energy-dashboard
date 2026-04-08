# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This repo is a Python modelling and analysis project for **Indonesia's KEK (Special Economic Zone) power competitiveness**. The goal is to build a dashboard that answers: "Which KEK can offer low-cost, low-carbon, reliable electricity — and what must change to get there?"

**Core documents — read these before making changes:**

| File | Purpose |
|------|---------|
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Plain-language project overview — start here if you're new to the project |
| [PLAN.md](PLAN.md) | Full implementation plan: architecture, phases, data pipeline, dashboard design (with design review decisions) |
| [DESIGN.md](DESIGN.md) | Dashboard UX design spec: 6 views, component architecture, colour system, open decisions |
| [PERSONAS.md](PERSONAS.md) | User journeys for all four personas: Energy Economist, DFI Investor, Policy Maker, Energy Investor |
| [METHODOLOGY.md](METHODOLOGY.md) | Analytical methodology spec: LCOE formulas, PVOUT conversion, GEAS allocation, geospatial buildability filters — `src/model/basic_model.py` must implement this exactly |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Data pipeline contract: every raw input column and every derived column we need to produce, with status (✅/⚠️/❌/🔒) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture: data flow diagram, pipeline dependency graph, key design decisions |
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

## Running the dashboard

The dashboard is a React + Vite frontend served by a FastAPI backend:

```bash
# Terminal 1: Start the API (loads pipeline data at startup)
uv run uvicorn src.api.main:app --port 8000

# Terminal 2: Start the frontend (Vite dev server, proxies /api to :8000)
cd frontend && npm run dev
```

The frontend is at `http://localhost:5173`. The API is at `http://localhost:8000`.

## Frontend

`frontend/` is a Vite + React 18 + TypeScript SPA with Tailwind CSS.

Key directories:
- `frontend/src/store/dashboard.ts` — Zustand state management (assumptions, scorecard, UI state)
- `frontend/src/lib/api.ts` — fetch wrappers for all 7 API endpoints
- `frontend/src/lib/types.ts` — TypeScript interfaces matching API response shapes
- `frontend/src/components/map/` — MapLibre GL JS map (via react-map-gl), KEK markers, raster/vector overlays, layer control
- `frontend/src/components/panels/` — AssumptionsPanel (LCOE sliders), ScoreDrawer (KEK detail)
- `frontend/src/components/table/` — TanStack Table v8 with sortable columns
- `frontend/src/components/charts/` — Recharts (QuadrantChart, RuptlChart)
- `frontend/src/components/ui/` — Header, BottomPanel, EnergyToggle, MethodologyModal

Formatting and linting:
```bash
cd frontend
npm run lint     # biome check (no auto-fix)
npm run format   # biome check --write (auto-fix)
npx tsc --noEmit # type-check
```

Biome is also wired into the pre-commit hook (`.pre-commit-config.yaml`).

## API

`src/api/` is a FastAPI backend that wraps the existing pipeline modules (`src/dash/logic.py`, `src/dash/data_loader.py`, `src/dash/map_layers.py`).

Key endpoints:
- `GET /api/defaults` — returns default assumptions, thresholds, and slider configs
- `POST /api/scorecard` — recomputes scorecard with user-adjusted assumptions
- `GET /api/layers/{name}` — lazy-loads geospatial layers (substations, peatland, etc.)
- `GET /api/kek/{id}/polygon` — returns KEK boundary polygon GeoJSON
- `GET /api/kek/{id}/substations` — substations within radius of a KEK
- `GET /api/ruptl-metrics` — RUPTL pipeline metrics by region
- `GET /api/methodology` — raw METHODOLOGY.md content for in-app rendering

## Notebooks

The data pipeline entry points are Jupyter notebooks:

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

Test files are in `tests/`. 302 tests across model, pipeline, and API modules — all should pass.

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

**CAPEX unit note**: CAPEX is sourced from `pdf_extract_esdm_tech.py` (VERIFIED_TECH006_DATA) in MUSD/MWe — `build_dim_tech_cost.py` converts with `× 1000` to USD/kW before passing to `lcoe_solar()`.

## Architecture

The codebase follows a **star-schema data model** aligned with the dashboard plan. Data flows from raw inputs → precomputed fact/dimension tables → model outputs:

**PDF extractor pattern** (used by `fct_ruptl_pipeline` and `dim_tech_cost`):
- Each PDF source has a `src/pipeline/pdf_extract_*.py` module
- Pattern: try pdfplumber extraction → fall back to `VERIFIED_*` hardcoded dict if extraction fails (image-based pages, PDF missing, layout change)
- The public API (`get_tech006_params()`, `extract_plts_from_pdf()`) always returns data — callers never handle None
- `VERIFIED_*` dicts are the single source of truth for hardcoded values and are used as ground truth in verification tests

**Dimension tables** (`dim_*`):
- `dim_kek` — master KEK list with name, province, grid region, lat/lon
- `dim_tech_cost` — solar CAPEX/OPEX/lifetime sourced from `pdf_extract_esdm_tech.py` → `VERIFIED_TECH006_DATA` (ESDM Technology Catalogue 2023, p.66)

**Fact tables** (`fct_*`):
- `fct_kek_resource` — PVOUT at centroid + best within 50km (from GeoTIFF); v1.1: adds `pvout_buildable_best_50km`, `buildable_area_ha`, `max_captive_capacity_mwp`, `buildability_constraint` (NaN until `data/buildability/` populated — run `scripts/download_buildability_data.py`)
- `fct_kek_demand` — per-KEK demand estimates
- `fct_substation_proximity` — nearest PLN substation per KEK; haversine distance + point-in-polygon → `siting_scenario`
- `fct_lcoe` — computed LCOE bands per KEK × WACC × siting scenario (450 rows: 25 × 9 × 2); `within_boundary` uses centroid PVOUT + no gen-tie; `remote_captive` uses `pvout_buildable_best_50km` when available, else `pvout_best_50km`, + gen-tie CAPEX adder
- `fct_ruptl_pipeline` — planned capacity additions by region/year from RUPTL
- `fct_grid_cost_proxy` — grid cost proxy (BPP when available, otherwise provisional) + `grid_emission_factor_t_co2_mwh` (KESDM Tier 2 OM by grid region)

**Key computed outputs** (see `sample_end_to_end_policy_planning.ipynb`):
- `lcoe_usd_mwh` — solar LCOE from `lcoe_solar(capex, fom, wacc, lifetime, cf)`
- `cf` derived from PVOUT via `capacity_factor_from_pvout(pvout) = pvout / 8760`
- Action flags: `solar_now`, `grid_first`, `firming_needed`, `invest_resilience`, `plan_late` — boolean tags per KEK; `invest_resilience` fires when LCOE is 0–20% above grid cost AND reliability_req ≥ 0.75
- `green_share_geas` — share of 2030 demand met by GEAS-allocated solar (GEAS and captive solar are substitutes — see METHODOLOGY.md §5.3)
- `carbon_breakeven_usd_tco2` — carbon price (USD/tCO2) at which solar becomes cost-competitive; derived from LCOE gap ÷ grid emission factor (KESDM 2019 OM)

**Solar resource data**: Global Solar Atlas GeoTIFFs in `data/` (zipped). PVOUT is extracted per KEK centroid and best-within-radius offline; the dashboard reads precomputed flat tables only.

**Utilities**:
- [utils/S3_loading.py](utils/S3_loading.py) — boto3 helpers for listing bucket contents and generating presigned URLs (eu-north-1 endpoint)
- [config/settings.py](config/settings.py) — `Config` class; reads all secrets from env vars

**Scraped raw data** lives in `outputs/data/raw/`:
- `kek_info_and_markers.csv`, `kek_polygons.geojson`, `kek_business_sectors.csv`, `oss_kek_all_pages.csv`

## Before every commit — required checklist

**When the user says "commit" or asks you to commit, ALWAYS prompt them with this checklist first:**

```
Before I commit, quick checklist:

1. /review run? — catch breaking changes before they're in git history
   (run it now if not done: two bugs slipped through without it last time)

2. Output CSVs spot-checked? — if a pipeline step ran this session,
   paste the printed output so we can sanity-check real numbers vs. theory
   (e.g. distances, row counts, LCOE values look plausible?)

3. Docs updated? — check the Documentation update rule table below; every change type
   has a specific list of files that must be updated before committing

Ready to commit? Or do any of these need attention first?
```

**Before big phase transitions** (e.g. moving from data pipeline → Dash app):
- Run `/autoplan` for full CEO + Eng + Design review simultaneously
- Catches strategic gaps before they're built in

## Documentation update rule

**Every code change — new feature, new column, bug fix that changes output, or deferred item now implemented — must update the relevant docs before committing.** Use the table below to decide which files need touching. When in doubt, update it.

| What changed | Files to update |
|---|---|
| New pipeline step or new `fct_*` / `dim_*` table | `DATA_DICTIONARY.md` (table index + full column spec), `CLAUDE.md` (Fact tables list), `run_pipeline.py` (Step entry + depends_on), `ARCHITECTURE.md` (pipeline graph if topology changed) |
| New column added to existing table | `DATA_DICTIONARY.md` (column row in the relevant section), `PERSONAS.md` (if relevant to a persona's key data needs or data gaps), `fct_kek_scorecard` column list in `CLAUDE.md` if scorecard grows |
| Analytical method or formula changed | `METHODOLOGY.md` (update the relevant section; remove "deferred" notes once implemented) |
| Deferred item now implemented (e.g. a buildability layer, a new flag) | `METHODOLOGY.md` (remove deferred note), `DATA_DICTIONARY.md` (update status ✅), `PERSONAS.md` (update data gap entry from "Deferred" or "Blocked" to "✅ Built") |
| Bug fix that changes output values | `METHODOLOGY.md` if the fix changes analytical behaviour; `DATA_DICTIONARY.md` if column semantics changed |
| New assumption or threshold added | `METHODOLOGY.md` (document the value and rationale), `src/assumptions.py` (single source of truth for constants) |
| Persona-relevant capability added or gap closed | `PERSONAS.md` — update the relevant persona's key data needs or data gaps table |
| Phase or step completed | `PLAN.md` — mark the step ✅ COMPLETE |
| Design or architecture change | `DESIGN.md` (update relevant section + add §9 Changelog entry), `ARCHITECTURE.md` (if system boundary changed), `EXECUTIVE_SUMMARY.md` (if user-facing capability changed) |
| Deferred item identified | `TODOS.md` (add with priority tier, source reference, and affected personas) |

**The commit checklist prompt (shown before every commit) checks item 3: "Docs updated?". This rule defines what "docs updated" means.**

The review checklist (`/review`) will flag stale documentation as an INFORMATIONAL finding. Keeping docs in sync with code prevents the next Claude session from making incorrect assumptions about the data model.

## Data notes

- The grid cost proxy uses PLN BPP (cost of supply), **not** the industrial tariff paid by KEK tenants. These differ — industrial tariffs are often subsidized below BPP. Label this distinction clearly in any output.
- RUPTL data (`fct_ruptl_pipeline`) is region/system-level, not KEK-specific. It provides grid system context only.
- `data/substation.geojson` contains substation locations for proximity analysis.
- `data/industrial_data/` contains a shapefile of Indonesian industrial facilities (50k+ employee firms, 2023).