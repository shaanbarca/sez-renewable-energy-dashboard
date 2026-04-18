# Contributing

Thanks for your interest in contributing to the SEZ Renewable Energy Dashboard.

## Prerequisites

- Python 3.13+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Dev setup

```bash
# Clone and install Python dependencies
git clone https://github.com/shaanbarca/sez-renewable-energy-dashboard.git
cd sez-renewable-energy-dashboard
uv sync

# Set up environment variables
cp .env_template .env
# Fill in MAPBOX_TOKEN (free at mapbox.com) for map terrain rendering.
# S3 keys are only needed if you're running data pipeline scripts.

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Running the dashboard

```bash
# Terminal 1: API server
uv run uvicorn src.api.main:app --port 8000

# Terminal 2: Frontend dev server (proxies /api to :8000)
cd frontend && npm run dev
```

Open http://localhost:5173.

## Running tests

```bash
# Backend: 541 tests across model, pipeline, and API modules
uv run pytest tests/

# Frontend: type-check
cd frontend && npx tsc --noEmit
```

Tests work without GeoTIFF data files. The pipeline modules fall back to `VERIFIED_*` hardcoded values when source files are missing, so all tests pass on a fresh clone.

## Linting

```bash
# Python
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Frontend
cd frontend && npm run lint      # biome check
cd frontend && npm run format    # biome check --write
```

Both ruff and biome run as pre-commit hooks.

## Making changes

1. Create a branch from `main`.
2. Make your changes. If you're modifying the model (`src/model/basic_model.py`), add or update tests in `tests/`.
3. Run `uv run pytest tests/` and `cd frontend && npx tsc --noEmit` before pushing.
4. Open a PR. Describe what you changed and why. CI will run tests automatically.

## Data notes

Large geospatial files (GeoTIFFs, wind rasters) are gitignored. If you need them for pipeline work:

```bash
python scripts/download_buildability_data.py   # solar buildability rasters
# Wind data: download Global Wind Atlas v3 GeoTIFF manually into data/wind/
```

These are only needed for re-running the spatial pipeline, not for the dashboard or tests.

## Architecture

Before making changes, read:

- [ARCHITECTURE.md](ARCHITECTURE.md) for the system design and data flow
- [docs/METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) for the analytical methodology
- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for column definitions and data provenance
