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
| [PERSONAS.md](PERSONAS.md) | User journeys for all five personas: Energy Economist, DFI Investor, Policy Maker, IPP/RE Developer, Industrial Investor |
| [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) | Analytical methodology spec (single canonical source): LCOE formulas, PVOUT conversion, GEAS allocation, geospatial buildability filters — `src/model/basic_model.py` must implement this exactly |
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

The React frontend reads the same token for 3D terrain via `frontend/vite.config.ts`, so a root-level `MAPBOX_TOKEN` is sufficient. If you prefer a frontend-local env file, `frontend/.env` can also define `VITE_MAPBOX_TOKEN=...`.

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
- `frontend/src/components/charts/` — Recharts (QuadrantChart, RuptlChart), EnergyBalanceChart (P4 MacKay supply vs demand), LcoeCurveChart, CbamTrajectoryChart (CBAM cost trajectory 2026–2034)
- `frontend/src/components/ui/` — Header, BottomPanel, EnergyToggle, MethodologyModal

UI conventions:
- **Liquid glass styling** — all floating panels, tooltips, and overlays use the CSS custom properties defined in `globals.css`: `--glass-heavy` background, `--blur-heavy` backdrop-filter, `--glass-border-bright` border, plus `inset 0 1px 0 rgba(255,255,255,0.06)` shine. Never use opaque backgrounds for tooltips or popups.

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
- `GET /api/methodology` — raw METHODOLOGY_CONSOLIDATED.md content for in-app rendering

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

Test files are in `tests/`. 402 tests across model, pipeline, and API modules — all should pass.

## Model module

`src/model/basic_model.py` is the core pure-Python model (zero Dash dependency). Key functions:
- `pvout_daily_to_annual(pvout_daily)` — converts GeoTIFF daily kWh/kWp/day → annual (multiplies by 365, validates range)
- `capacity_factor_from_pvout(pvout_annual)` — divides by 8760
- `lcoe_solar(capex_usd_per_kw, fom, wacc, lifetime_yr, cf, degradation_annual_pct)` — CRF annuity LCOE formula with panel degradation midpoint approximation; expects CAPEX in USD/kW; V3.4: `degradation_annual_pct` default 0.5%/yr increases LCOE ~7%
- `lcoe_solar_with_firming(...)` — adds firming adder (low/mid/high = +6/11/16 USD/MWh)
- `action_flags(...)` — returns `ActionFlag` enum value; 9 flags ranked best→worst: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive`, `no_solar_resource`
- `grid_integration_category(...)` — returns `within_boundary`/`grid_ready`/`invest_transmission`/`invest_substation`/`grid_first` from three-point proximity; V3.2: `within_boundary` also fires when `within_boundary_coverage_pct >= 1.0` (on-site solar covers 100%+ of demand)
- `bess_bridge_hours(...)` — V3.3: overnight gap hours = 24 - SOLAR_PRODUCTION_HOURS (default 14h)
- `bess_storage_adder(...)` — V3.3: BESS storage cost per MWh; includes round-trip efficiency (87%) and bridge-hours sizing for 24/7 loads; V3.6: `bess_sizing_hours_override` in UserAssumptions lets users override auto-sizing (2h/4h/14h) via ScoreDrawer slider (1-16h)
- `lcoe_solar_with_battery(...)` — V3: solar LCOE + BESS storage adder
- `firm_solar_metrics(...)` — V3.3: temporal-aware solar coverage (daytime-direct vs storage-dependent), returns `firm_solar_coverage_pct`, `storage_gap_pct`, `storage_required_mwh`, `nighttime_demand_mwh`
- `wind_speed_to_cf(wind_speed_ms)` — piecewise-linear wind capacity factor from wind speed (3.0-12.0 m/s → CF 0.00-0.42), calibrated to Vestas V126/3.45 MW
- `compute_lcoe_wind_live(capex, fom, wacc, lifetime, cf_wind)` — live wind LCOE via CRF annuity (same formula as solar, wind-specific parameters)
- `firm_wind_metrics(cf_wind, demand_mwh, wind_generation_mwh)` — CF-dependent intermittency model: >=35% CF → 15% firming/2h, >=25% → 25%/3h, <25% → 35%/4h; returns `firm_wind_coverage_pct`, `wind_firming_gap_pct`, `wind_firming_hours`
- `RESource` — dataclass for multi-technology hybrid optimization. Fields: `technology`, `lcoe_usd_mwh`, `generation_mwh`, `cf`, `nighttime_fraction` (solar=0.0, wind=14/24, hydro=1.0), `capacity_mwp`
- `hybrid_bess_hours(sources, total_demand_mwh, solar_production_hours)` — computes reduced BESS sizing from wind nighttime coverage: `14 × (1 - min(nighttime_supply/nighttime_demand, 1.0))`
- `hybrid_lcoe_optimized(sources, demand_mwh, bess_capex, wacc, ..., solar_share_override, optimization_step)` — sweeps solar_share 0-100% in 5% steps, picks mix minimizing all-in (blended LCOE + reduced BESS adder); returns dict with `hybrid_lcoe_usd_mwh`, `hybrid_bess_hours`, `hybrid_bess_adder_usd_mwh`, `hybrid_allin_usd_mwh`, `optimal_solar_share`, `hybrid_supply_coverage_pct`, `hybrid_nighttime_coverage_pct`
- `grid_connection_cost_per_kw(dist_km)` — V2: connection cost = dist × $5/kW-km + $80/kW fixed
- `new_transmission_cost_per_kw(inter_substation_dist_km, solar_capacity_mwp)` — V3.1: new line cost when substations not connected = dist × $1.25M/km ÷ capacity
- `capacity_assessment(substation_capacity_mva, solar_capacity_mwp, utilization_pct, power_factor)` — V3.4: traffic light (green/yellow/red/unknown); converts MVA to MW via power factor (0.85) before comparing to solar MWp
- `substation_upgrade_cost_per_kw(substation_capacity_mva, solar_capacity_mwp, utilization_pct, upgrade_cost_per_kw, power_factor)` — V3.4: additional $/kW when substation capacity insufficient; applies PF correction then deficit_fraction × $80/kW
- `lcoe_solar_grid_connected(...)` — V2: LCOE with grid connection cost included in effective CAPEX
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
- `fct_kek_resource` — PVOUT at centroid + best within 50km (from GeoTIFF); v1.2: adds `pvout_buildable_best_50km`, `buildable_area_ha`, `max_captive_capacity_mwp`, `buildability_constraint` (NaN until `data/buildability/` populated — run `scripts/download_buildability_data.py`); 5-layer filter: kawasan hutan, peatland, land cover, road proximity (>10km from OSM motorable road), slope/elevation
- `fct_kek_demand` — per-KEK demand estimates
- `fct_substation_proximity` — nearest PLN substation per KEK; V3: three-point proximity (solar→substation→KEK) + `grid_integration_category`; V3.1: adds geometric grid line connectivity check (`line_connected`, `inter_substation_connected`), capacity utilization (`available_capacity_mva`, `capacity_assessment` traffic light), PLN region (`regpln`), inter-substation distance
- `fct_lcoe` — computed LCOE bands per KEK × WACC × siting scenario (450 rows: 25 × 9 × 2); `within_boundary` uses centroid PVOUT + no connection cost; `grid_connected_solar` uses best PVOUT + connection cost from solar-to-substation distance
- `fct_ruptl_pipeline` — planned capacity additions by region/year from RUPTL
- `fct_grid_cost_proxy` — grid cost proxy (BPP when available, otherwise provisional) + `grid_emission_factor_t_co2_mwh` (KESDM Tier 2 OM by grid region)
- `fct_captive_coal` — GEM Global Coal Plant Tracker: captive coal plants within 50km of each KEK (count, total MW, plant names)
- `fct_captive_nickel` — CGSP Nickel Tracker: nickel smelters within 50km of each KEK (count, process type, Chinese ownership, project names)
- `fct_captive_steel` — GEM Global Iron and Steel Plant Tracker: steel plants within 50km of each KEK (count, total TPA capacity, technology, plant names, Chinese ownership)
- `fct_captive_cement` — GEM Global Cement Plant Tracker: cement plants within 50km of each KEK (count, total MTPA capacity, plant type, plant names, Chinese ownership)
- `fct_kek_wind_resource` — wind speed, capacity factor, and buildability per KEK (centroid + best 50km + buildable-area metrics from `buildable_wind_web.tif`); columns: `wind_speed_centroid_ms`, `cf_wind_centroid`, `wind_buildable_area_ha`, `max_wind_capacity_mwp`, `wind_buildability_constraint`, `cf_wind_buildable_best`

**Wind pipeline** (`scripts/build_wind_pipeline.sh` runs all three steps):
- `src/pipeline/build_wind_buildable_raster.py` — 6-layer buildability filter (kawasan hutan, peatland, land cover, road proximity >10km, slope/elevation 20deg, wind speed 3.0 m/s cut-in) → `buildable_wind_web.tif`
- `src/pipeline/build_wind_buildable_polygons.py` — vectorizes raster → `wind_buildable_polygons.geojson` (3,402 polygons, 50 ha min area)
- `src/pipeline/wind_buildability_filters.py` — wind-adapted filter thresholds (slope relaxed 8→20deg, cropland allowed, 25 ha/MWp spacing)
- `src/pipeline/build_fct_kek_wind_resource.py` — extracts per-KEK wind buildability from raster

**Key computed outputs** (see `sample_end_to_end_policy_planning.ipynb`):
- `lcoe_usd_mwh` — solar LCOE from `lcoe_solar(capex, fom, wacc, lifetime, cf)`
- `cf` derived from PVOUT via `capacity_factor_from_pvout(pvout) = pvout / 8760`
- Action flags: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive` — 8 flags per KEK via `ActionFlag` enum (V3); `invest_transmission` = solar near substation but KEK far; `invest_substation` = KEK near but solar far; `invest_battery` = high reliability req, BESS storage needed; `invest_resilience` fires when LCOE is 0–20% above grid cost AND reliability_req ≥ 0.75
- `green_share_geas` — share of 2030 demand met by GEAS-allocated solar (GEAS and captive solar are substitutes — see METHODOLOGY_CONSOLIDATED.md §8)
- `carbon_breakeven_usd_tco2` — carbon price (USD/tCO2) at which solar becomes cost-competitive; derived from LCOE gap ÷ grid emission factor (KESDM 2019 OM)
- `best_re_technology` — `"solar"`, `"wind"`, or `"hybrid"`, whichever has lower all-in LCOE per KEK (3-way comparison: solar+BESS vs wind standalone vs hybrid all-in)
- `wind_competitive_gap_pct` — wind LCOE competitive gap vs grid cost (same formula as solar gap)
- `wind_supply_coverage_pct` — fraction of KEK demand coverable by buildable wind capacity
- `wind_carbon_breakeven_usd_tco2` — carbon price at which wind becomes cost-competitive
- `firm_wind_coverage_pct`, `wind_firming_gap_pct`, `wind_firming_hours` — wind temporal/intermittency metrics (live-computed in `logic.py`)
- `hybrid_lcoe_usd_mwh`, `hybrid_allin_usd_mwh`, `hybrid_bess_hours`, `hybrid_solar_share`, `hybrid_supply_coverage_pct`, `hybrid_nighttime_coverage_pct`, `hybrid_bess_reduction_pct`, `hybrid_carbon_breakeven_usd_tco2` — hybrid solar+wind metrics (live-computed in `logic.py` via `hybrid_lcoe_optimized()`; see METHODOLOGY_CONSOLIDATED.md §6A)
- `cbam_exposed`, `cbam_product_type`, `cbam_emission_intensity_current`, `cbam_emission_intensity_solar`, `cbam_cost_2026/2030/2034_usd_per_tonne`, `cbam_savings_2026/2030/2034_usd_per_tonne` — EU CBAM exposure metrics; 3-signal detection: (1) nickel process types (RKEF/FeNi → iron_steel), (2) plant-level counts (steel_plant_count > 0 → iron_steel, cement_plant_count > 0 → cement), (3) KEK business sectors (Base Metal → iron_steel, Bauxite → aluminium, Petrochemical → fertilizer); 12/25 KEKs exposed; cost trajectory uses EU ETS ~€80/tCO₂ × free allocation phase-out schedule (97.5% free in 2026 → 0% in 2034)

**Solar resource data**: Global Solar Atlas GeoTIFFs in `data/` (zipped). PVOUT is extracted per KEK centroid and best-within-radius offline; the dashboard reads precomputed flat tables only.

**Wind resource data**: Global Wind Atlas v3 GeoTIFF (`data/wind/`). Wind speed at 100m hub height, extracted per KEK. Wind buildable polygons served as a map overlay layer (`GET /api/layers/wind_buildable_polygons`).

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
| Analytical method or formula changed | `docs/METHODOLOGY_CONSOLIDATED.md` (update the relevant section; remove "deferred" notes once implemented) |
| Deferred item now implemented (e.g. a buildability layer, a new flag) | `docs/METHODOLOGY_CONSOLIDATED.md` (remove deferred note), `DATA_DICTIONARY.md` (update status ✅), `PERSONAS.md` (update data gap entry from "Deferred" or "Blocked" to "✅ Built") |
| Bug fix that changes output values | `docs/METHODOLOGY_CONSOLIDATED.md` if the fix changes analytical behaviour; `DATA_DICTIONARY.md` if column semantics changed |
| New assumption or threshold added | `docs/METHODOLOGY_CONSOLIDATED.md` (document the value and rationale), `src/assumptions.py` (single source of truth for constants) |
| Persona-relevant capability added or gap closed | `PERSONAS.md` — update the relevant persona's key data needs or data gaps table |
| Phase or step completed | `PLAN.md` — mark the step ✅ COMPLETE |
| Design or architecture change | `DESIGN.md` (update relevant section + add §9 Changelog entry), `ARCHITECTURE.md` (if system boundary changed), `EXECUTIVE_SUMMARY.md` (if user-facing capability changed) |
| Deferred item identified | `TODOS.md` (add with priority tier, source reference, and affected personas) |

**The commit checklist prompt (shown before every commit) checks item 3: "Docs updated?". This rule defines what "docs updated" means.**

The review checklist (`/review`) will flag stale documentation as an INFORMATIONAL finding. Keeping docs in sync with code prevents the next Claude session from making incorrect assumptions about the data model.

## Data notes

- The grid cost proxy uses PLN BPP (cost of supply), **not** the industrial tariff paid by KEK tenants. These differ — industrial tariffs are often subsidized below BPP. Label this distinction clearly in any output.
- RUPTL data (`fct_ruptl_pipeline`) is region/system-level, not KEK-specific. It provides grid system context only.
- `data/substation.geojson` contains substation locations for proximity analysis (2,913 PLN substations with `namobj`, `kapgi` MVA, `teggi` voltage, `regpln` PLN region, `statopr` status).
- `data/pln_grid_lines.geojson` contains 1,595 PLN transmission lines for geometric connectivity checking (V3.1). Properties: `namobj` (line name with endpoints), `tegjar` (voltage kV), geometry (LineString/MultiLineString).
- `data/industrial_data/` contains a shapefile of Indonesian industrial facilities (50k+ employee firms, 2023).
- `data/captive_power/gem_steel_plants.csv` contains 7 Indonesian steel plants from GEM Global Iron and Steel Plant Tracker (capacity TPA, technology BF-BOF/EAF, ownership).
- `data/captive_power/gem_cement_plants.csv` contains 32 Indonesian cement plants from GEM Global Cement Plant Tracker (capacity MTPA, plant type, ownership).
