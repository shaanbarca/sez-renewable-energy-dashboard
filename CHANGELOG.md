# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- CI workflow: pytest (422 tests) + ruff lint + TypeScript type-check on every push and PR
- CONTRIBUTING.md with dev setup, testing, and PR process
- CSV export now includes assumptions, thresholds, energy mode, benchmark mode, and export date
- RUPTL Context chart connects to selected KEK: highlights grid region, shows post-2030 % with plan_late badge, 2030 reference line
- Bottom panel drag-to-resize (200-700px range)

### Fixed
- QuadrantChart tooltip now reads correct grid cost in BPP mode (was showing tariff value)
- Show/Hide toggle centered in both collapsed and expanded states

### Removed
- Quadrant Chart tab disabled (file retained for future use)

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
