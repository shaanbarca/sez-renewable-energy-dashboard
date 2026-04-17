# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.0] - 2026-04-17

V4.1 Industrial Parks Expansion + internal refactors.

### Added
- **Industrial parks expansion: 25 KEKs → 79 sites** (32 cement + 7 steel + 10 nickel IIA clusters + 2 aluminium + 3 fertilizer added)
- Tracker-driven site selection (`build_industrial_sites.py`) reads GEM Global Cement/Iron-and-Steel Plant Trackers and CGSP Nickel Tracker; cement/steel/nickel rows generated programmatically with explicit filter rules; only aluminium + fertilizer remain residual manual rows (with required `source_url`)
- Site-types registry (`src/model/site_types.py` + `frontend/src/lib/siteTypes.ts`) — single `SITE_TYPES` dict drives per-type demand estimation, captive power matching, CBAM detection, and marker shape; mirrored in TypeScript for the frontend
- Dual-mode dispatch via `SiteTypeConfig`: KEKs/KIs use area-based demand + proximity captive matching + 3-signal CBAM; standalone/cluster sites use sector-intensity demand + direct captive matching + direct CBAM via `cbam_product_type`
- Sector summary chart (`SectorSummaryChart.tsx`) — sector-aggregated CBAM cost + 2030 demand + action-flag distribution
- Site-type and sector dropdown filters in the data table; registry-driven identity card in ScoreDrawer (renders fields per `SiteTypeConfig.identityFields`)
- CI workflow: pytest + ruff lint + TypeScript type-check on every push and PR
- CONTRIBUTING.md with dev setup, testing, and PR process
- CSV export now includes assumptions, thresholds, energy mode, benchmark mode, and export date
- RUPTL Context chart connects to selected site: highlights grid region, shows post-2030 % with plan_late badge, 2030 reference line
- Bottom panel drag-to-resize (200-700px range)
- Golden-master test (`tests/test_scorecard_golden.py`) locks `compute_scorecard_live` output against a fixture pickle so future refactors can verify bit-identical behavior

### Changed
- **`src/dash/logic.py` (1,437 LOC) split into `src/dash/logic/` package** by domain: `assumptions.py`, `lcoe.py`, `cbam.py`, `grid.py`, `technology.py`, `scorecard.py`. Public API preserved via `__init__.py` re-exports — external callers unchanged.
- **`frontend/src/components/panels/ScoreDrawer.tsx` (2,244 LOC) split into `scoredrawer/` folder** (9 files): one file per tab (Overview/Resource/Grid/Economics/Demand/Action), shared `StatComponents.tsx`, `IdentityCard.tsx`, `formatting.ts`. Shell file is now 237 LOC.
- Renamed `kek_id` → `site_id` and `/api/kek/{id}/...` → `/api/site/{id}/...` across backend, frontend, and tests for consistency with the broader site-type model
- Renamed pipeline outputs `fct_kek_*` → `fct_site_*` (resource, demand, scorecard, wind_resource)
- 532 tests now pass (up from 422); added module-boundary tests for each new logic submodule + site-types/geo-utils/demand-intensity tests

### Fixed
- Hybrid LCOE floor: optimizer now returns standalone wind when no hybrid mix can beat it (was adding BESS to 100% wind unnecessarily)
- Wind energy balance chart now renders in wind mode (was only showing in hybrid mode)
- QuadrantChart tooltip now reads correct grid cost in BPP mode (was showing tariff value)
- Show/Hide toggle centered in both collapsed and expanded states
- `data_loader.prepare_resource_df()` now merges `site_type`/`cbam_product_type`/`technology`/`capacity_annual_tonnes` from `dim_sites` onto resource_df so industrial sites correctly route through direct CBAM detection (previously fell through to 3-signal and showed $0)

### Removed
- Quadrant Chart tab disabled (file retained for future use)
- `src/dash/logic.py` monolith (split into package; legacy file deleted)

## [1.0.0] - 2026-04-14

Initial public release.

### Added
- LCOE model for solar, wind, and hybrid (solar+wind) with BESS storage
- 25 KEK scorecard with action flags (solar_now, invest_transmission, invest_substation, grid_first, invest_battery, invest_resilience, plan_late, not_competitive, no_solar_resource)
- 5-layer solar buildability filter (kawasan hutan, peatland, land cover, road proximity, slope/elevation)
- 6-layer wind buildability filter with buildable polygon overlay
- Grid integration: 3-point proximity, PLN substation capacity traffic lights, grid line connectivity
- CBAM exposure analysis: 3-signal detection (nickel process, plant counts, KEK sectors), cost trajectories 2026-2034, 12/25 KEKs exposed
- Captive power overlays: coal (GEM), nickel (CGSP), steel (GEM), cement (GEM)
- React + Vite + TypeScript frontend with MapLibre GL map, liquid glass UI
- FastAPI backend serving precomputed pipeline data
- Energy mode toggle: Solar / Wind / Hybrid / Overall
- Benchmark toggle: BPP (cost of supply) vs I-4 industrial tariff
- User-adjustable assumptions panel with 3-tier sliders
- Persona-driven walkthroughs (Economist, DFI Investor, Policy Maker, IPP Developer, Industrial Investor)
- Scenario save/load with URL sharing
- RUPTL pipeline context chart by grid region
- Ranked table with dropdown/range filters, CBAM filter, CSV export
- ScoreDrawer with 6 tabs (Resource, Grid, Economics, Action, CBAM, Energy Balance)
- Distance measurement tool on map
- Auth gate for deployment
- Docker + Render deploy config
- 422 tests across model, pipeline, and API modules
- Zenodo DOI for citation
