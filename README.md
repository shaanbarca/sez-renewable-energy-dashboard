# Indonesia KEK Power Competitiveness Dashboard

Interactive dashboard that answers: **"Which of Indonesia's 25 Special Economic Zones (KEKs) can offer low-cost, low-carbon, reliable electricity, and what must change to get there?"**

Combines satellite solar resource data (Global Solar Atlas), PLN grid costs, RUPTL pipeline plans, and geospatial buildability analysis into a single, transparent scorecard.

## Quick Start

```bash
# Backend (Python)
uv sync

# Copy .env_template to .env and set MAPBOX_TOKEN if you want 3D terrain.
uv run uvicorn src.api.main:app --port 8000

# Frontend (React)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API loads pipeline data at startup (~10s), then the dashboard is ready.

## What It Does

For each KEK, the model computes:

1. **Solar LCOE** from CRF annuity method (CAPEX, FOM, WACC, capacity factor from PVOUT)
2. **Competitiveness gap** vs PLN grid cost (I-4 industrial tariff or BPP by region)
3. **Action flags**: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive`, `no_solar_resource`
4. **Buildable area** within 50km (filtered by forest, peat, slope, land cover)
5. **Carbon breakeven price** (USD/tCO2 at which solar wins)

All assumptions are adjustable via sliders in the dashboard.

## Architecture

```
Data Pipeline (Python)          API (FastAPI)           Frontend (React + Vite)
--------------------           ----------------        ----------------------
GeoTIFF + PDFs + CSVs          7 REST endpoints        MapLibre GL map
  -> dim/fct tables              /api/defaults          TanStack Table
  -> outputs/data/processed/     /api/scorecard         Recharts charts
                                 /api/layers/{name}     Zustand state
                                 /api/methodology       Tailwind CSS
```

## Project Structure

```
src/model/          Pure Python model (LCOE, action flags, GEAS allocation)
src/pipeline/       Data pipeline builders (dim_kek, fct_lcoe, etc.)
src/api/            FastAPI backend (routes, scorecard recomputation)
src/dash/           Shared modules (data_loader, map_layers, logic, constants)
frontend/src/       React SPA (components, store, hooks, lib)
tests/              383 tests (model, pipeline, API)
notebooks/          Jupyter notebooks for exploration
data/               Input data (GeoTIFFs, GeoJSON, shapefiles)
outputs/            Pipeline output CSVs
docs/               Design mockups, reference PDFs
```

## Documentation

| File | Purpose |
|------|---------|
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Plain-language project overview |
| [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) | LCOE formulas, PVOUT conversion, action flags, GEAS allocation |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every column in every pipeline table |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System diagram, pipeline dependency graph |
| [DESIGN.md](DESIGN.md) | Dashboard UX spec, component architecture, color system |
| [PERSONAS.md](PERSONAS.md) | User journeys (Energy Economist, DFI Investor, Policy Maker, Energy Investor) |
| [TODOS.md](TODOS.md) | Deferred items with priority tiers |

## Tests

```bash
uv run pytest tests/       # 383 tests
uv run ruff check src/     # Python lint
cd frontend && npm run lint # TypeScript lint (Biome)
```

## License

This project is licensed under the **MIT License** with the **Commons Clause** restriction.

**In plain terms:**
- **Free to use** — you can use, copy, modify, and redistribute this software freely
- **Attribution required** — you must keep the copyright notice and credit the original author in all copies
- **No selling** — you may not sell the software or any product/service whose value derives substantially from it

See [LICENSE](LICENSE) and [NOTICE](NOTICE) for full terms.

## Author

Shaan Barca (shaan.b1223@gmail.com)
