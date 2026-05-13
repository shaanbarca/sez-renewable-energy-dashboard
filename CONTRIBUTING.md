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
# Backend: 847 tests across model, pipeline, API, and rooftop solar pipeline modules
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
5. If the work surfaced **follow-ups** that aren't being fixed in the same PR — file a GitHub issue for each (see "Tracking follow-ups" below).

## Tracking follow-ups

Whenever a PR or review surfaces a follow-up that isn't being fixed in the current branch — a deferred bug, a bucket of sites needing validation, a methodology gap, a "we'll do this in v4.1" item — **file a GitHub issue immediately**. Don't rely on memory, chat threads, or PR-body bullets alone. Issues are the only durable tracking layer; everything else decays.

### What warrants an issue

- A bug found but explicitly deferred (e.g., "21 polygon-missing sites — buffer fallback now, real polygons later")
- A scope split surfaced during root-cause analysis or review ("bucket B is a separate UX problem from bucket A")
- A methodology gap noted in passing ("KEK coarse-raster optimism — measure properly in v4.1")
- A `/codex review` or `/plan-eng-review` finding classified as deferred / non-blocking
- A `TODO` / `FIXME` / `HACK` comment that represents real future work, not a trivial inline note
- Tier-3 polygon hunts, sector-specific calibrations, or any "the dashboard isn't lying but we know it could be better" item

### What doesn't

- Things you're fixing in the same PR (those go in the PR body)
- Polish ideas without acceptance criteria (those go in `TODOS.md` if anywhere)
- Anything already covered by an open issue (link to it, don't duplicate)

### Pattern

```bash
gh issue create --repo shaanbarca/eez \
  --title "v<target-release>: <one-liner>" \
  --body "<context: what was found + why deferred + acceptance criteria>"
```

Reference the new issue number in the surfacing PR's body (`Closes #X` if fixed here; `Follow-up: #Y` if deferred) and add it to `TODOS.md`'s "Today's deltas" section so the next session sees it. The next "what's next" question starts with:

```bash
gh issue list --repo shaanbarca/eez --state open
```

**Why this matters in practice.** The PR #44 → #45 / #46 / #43-rescope / #47 / #48 chain in May 2026 surfaced 5+ loose threads across one feature. Every one of them got a GitHub issue at the moment it was identified — that's why none got lost when the session ended. Without that discipline, half of them would be sitting in a Slack thread or a forgotten PR comment, and we'd rediscover them as "didn't we already know about this?" weeks later.

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
