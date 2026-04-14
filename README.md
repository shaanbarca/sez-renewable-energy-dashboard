# SEZ Renewable Energy Dashboard

[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MapLibre GL](https://img.shields.io/badge/MapLibre_GL-4-396CB2?logo=maplibre&logoColor=white)](https://maplibre.org)
[![License: MIT](https://img.shields.io/badge/License-MIT_+_Commons_Clause-yellow)](LICENSE)
[![Tests: 421](https://img.shields.io/badge/Tests-421_passing-brightgreen)](tests/)

An analytical model and interactive dashboard assessing renewable energy competitiveness across Indonesia's 25 Special Economic Zones (KEKs). Computes solar and wind LCOE, grid integration costs, BESS storage requirements, CBAM exposure, and action flags under user-adjustable assumptions.

Built for development bank analysts, energy investors, and policy advisors.

---

## Features

**Analytical Model**
- Solar and wind LCOE via CRF annuity method with panel degradation and firming costs
- Hybrid solar+wind optimization (sweeps blended mix to minimize all-in cost)
- BESS storage sizing with bridge-hour model (round-trip efficiency, overnight gap)
- 5-layer geospatial buildability filter (forest, peatland, slope, land cover, road proximity)
- Grid integration assessment (3-point proximity: solar site, substation, KEK)
- EU CBAM exposure flagging for nickel smelter zones

**Dashboard**
- Interactive map with 25 KEK markers, color-coded by action flag
- Solar PVOUT and wind speed raster overlays with buildable area polygons
- Adjustable assumptions panel (WACC, CAPEX, lifetime, grid benchmark, BESS sizing)
- Sortable/filterable scorecard table with CSV export
- Per-KEK detail drawer with 6 analysis tabs
- Quadrant chart, LCOE curve, energy balance, and RUPTL pipeline visualizations
- 5 guided walkthrough tours (one per persona)
- Light, dark, and satellite map themes

## Quick Start

```bash
# Backend
uv sync
cp .env_template .env   # set MAPBOX_TOKEN for 3D terrain (optional)
uv run uvicorn src.api.main:app --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The API loads pipeline data at startup (~10s), then the dashboard is ready.

## Architecture

```
Data Pipeline (Python)          API (FastAPI)           Frontend (React + Vite)
----------------------         ----------------        -----------------------
GeoTIFF + PDFs + CSVs          7 REST endpoints        MapLibre GL JS map
  -> dim/fct star schema         /api/defaults          TanStack Table v8
  -> outputs/data/processed/     /api/scorecard         Recharts charts
                                 /api/layers/{name}     Zustand state
                                 /api/kek/{id}/*        Tailwind CSS
                                 /api/methodology
```

## Data Sources

| Source | What it provides |
|--------|-----------------|
| [Global Solar Atlas](https://globalsolaratlas.info/) | PVOUT GeoTIFF (kWh/kWp/day) at 250m resolution |
| [Global Wind Atlas](https://globalwindatlas.info/) | Wind speed at 100m hub height |
| [PLN RUPTL 2021-2030](https://web.pln.co.id/) | Grid capacity pipeline by region |
| ESDM Technology Catalogue 2023 | Solar CAPEX, FOM, lifetime parameters |
| PLN BPP 2023 | Regional cost of supply (grid benchmark) |
| [GEM Coal Plant Tracker](https://globalenergymonitor.org/) | Captive coal plants within 50km of each KEK |
| [CGSP Nickel Tracker](https://www.cgsp.or.id/) | Nickel smelters, process types, CBAM exposure |
| OpenStreetMap | Road network for buildability filtering |

## Project Structure

```
src/
  model/             Pure Python model (LCOE, action flags, GEAS allocation)
  pipeline/          Data pipeline builders (dim_kek, fct_lcoe, fct_captive_coal, etc.)
  api/               FastAPI backend (routes, scorecard recomputation)
  dash/              Shared modules (data_loader, map_layers, logic, constants)
frontend/
  src/components/    Map, panels, charts, table, UI components
  src/store/         Zustand state management
  src/lib/           API client, types, formatting utilities
tests/               421 tests across model, pipeline, and API
notebooks/           Jupyter notebooks for exploration and data pipeline
docs/                Methodology, design specs, reference documents
data/                Input data (GeoTIFFs, GeoJSON, shapefiles)
outputs/             Pipeline output CSVs
```

## Documentation

| Document | Description |
|----------|-------------|
| [Executive Summary](EXECUTIVE_SUMMARY.md) | Plain-language project overview |
| [Methodology](docs/METHODOLOGY_CONSOLIDATED.md) | LCOE formulas, PVOUT conversion, action flag logic, GEAS allocation |
| [Data Dictionary](DATA_DICTIONARY.md) | Every column in every pipeline table with source attribution |
| [Architecture](ARCHITECTURE.md) | System diagram, pipeline dependency graph, design decisions |
| [Design Spec](DESIGN.md) | Dashboard UX spec, component architecture, color system |
| [Personas](PERSONAS.md) | User journeys for 5 target personas |

## Testing

```bash
uv run pytest tests/            # 421 tests
uv run ruff check src/ tests/   # Python lint
cd frontend && npm run lint     # TypeScript lint (Biome)
cd frontend && npx tsc --noEmit # Type check
```

## License

MIT License with [Commons Clause](LICENSE). Free to use, modify, and redistribute with attribution. Commercial resale of the software itself is restricted.

## Citation

If you use this software or dataset in your research, please cite:

```bibtex
@software{barca2026sez,
  author    = {Barca, Shaan},
  title     = {SEZ Renewable Energy Dashboard},
  year      = {2026},
  version   = {1.0.0},
  url       = {https://github.com/shaanbarca/sez-renewable-energy-dashboard}
}
```

## Author

**Shaan Barca** — [shaan.b1223@gmail.com](mailto:shaan.b1223@gmail.com)
