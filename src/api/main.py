# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""FastAPI backend for KEK Dashboard — thin API layer over existing modules.

Phase 1 of Dash-to-React migration. Wraps logic.py, data_loader.py, and
map_layers.py without modifying them.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_kek_infrastructure,
    prepare_resource_df,
)
from src.dash.map_layers import get_all_layers

# ---------------------------------------------------------------------------
# Module-level data store (populated at startup)
# ---------------------------------------------------------------------------

tables: dict[str, pd.DataFrame] = {}
resource_df: pd.DataFrame = pd.DataFrame()
ruptl_metrics_df: pd.DataFrame = pd.DataFrame()
layers: dict = {}
infrastructure: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all data and map layers once at startup."""
    global tables, resource_df, ruptl_metrics_df, layers, infrastructure

    print("Loading pipeline data...")
    tables.update(load_all_data())
    resource_df = prepare_resource_df(tables)
    ruptl_metrics_df = compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"])

    print("Loading map layers...")
    layers.update(get_all_layers())

    print("Loading infrastructure markers...")
    infrastructure.update(load_kek_infrastructure())

    print("Startup complete.")
    yield


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="KEK Power Competitiveness API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount route modules
# ---------------------------------------------------------------------------

from src.api.routes.layers import router as layers_router  # noqa: E402
from src.api.routes.scorecard import router as scorecard_router  # noqa: E402

app.include_router(scorecard_router, prefix="/api")
app.include_router(layers_router, prefix="/api")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@app.get("/api/methodology", response_class=PlainTextResponse)
async def get_methodology():
    """Return the raw METHODOLOGY_CONSOLIDATED.md content for rendering in the frontend."""
    md_path = PROJECT_ROOT / "docs" / "METHODOLOGY_CONSOLIDATED.md"
    if not md_path.exists():
        return PlainTextResponse("Methodology document not found.", status_code=404)
    return PlainTextResponse(md_path.read_text(encoding="utf-8"))
