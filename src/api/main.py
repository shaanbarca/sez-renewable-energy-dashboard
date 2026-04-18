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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from src.dash.data_loader import (
    compute_ruptl_region_metrics,
    load_all_data,
    load_kek_infrastructure,
    load_wind_tech_defaults,
    prepare_resource_df,
)
from src.dash.map_layers import get_all_layers

# ---------------------------------------------------------------------------
# Module-level data store (populated at startup)
# ---------------------------------------------------------------------------

tables: dict[str, pd.DataFrame] = {}
resource_df: pd.DataFrame = pd.DataFrame()
ruptl_metrics_df: pd.DataFrame = pd.DataFrame()
wind_tech: dict = {}
layers: dict = {}
infrastructure: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all data and map layers once at startup."""
    global tables, resource_df, ruptl_metrics_df, wind_tech, layers, infrastructure

    print("Loading pipeline data...")
    tables.update(load_all_data())
    resource_df = prepare_resource_df(tables)
    ruptl_metrics_df = compute_ruptl_region_metrics(tables["fct_ruptl_pipeline"])
    wind_tech.update(load_wind_tech_defaults())

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

app.add_middleware(GZipMiddleware, minimum_size=1000)

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

from src.api.auth import is_authenticated  # noqa: E402
from src.api.auth import router as auth_router  # noqa: E402
from src.api.routes.layers import router as layers_router  # noqa: E402
from src.api.routes.scorecard import router as scorecard_router  # noqa: E402

app.include_router(auth_router)
app.include_router(scorecard_router, prefix="/api")
app.include_router(layers_router, prefix="/api")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@app.get("/api/health")
async def health():
    """Health check for Render / load balancers."""
    return {"status": "ok", "sites": len(tables.get("dim_sites", []))}


# ---------------------------------------------------------------------------
# Auth middleware — protect /api routes (except /api/auth/*)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    # Allow auth endpoints, static assets, and the root page through
    if (
        path.startswith("/api/auth/")
        or path == "/api/health"
        or path.startswith("/assets/")
        or not path.startswith("/api/")
    ):
        return await call_next(request)
    # All other /api routes require auth
    if not is_authenticated(request):
        return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return await call_next(request)


@app.get("/api/methodology", response_class=PlainTextResponse)
async def get_methodology():
    """Return the raw METHODOLOGY_CONSOLIDATED.md content for rendering in the frontend."""
    md_path = PROJECT_ROOT / "docs" / "METHODOLOGY_CONSOLIDATED.md"
    if not md_path.exists():
        return PlainTextResponse("Methodology document not found.", status_code=404)
    return PlainTextResponse(md_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Serve frontend build (production only — in dev, Vite handles this)
# ---------------------------------------------------------------------------

if FRONTEND_DIST.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    # SPA fallback: serve index.html for all non-API routes
    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        # Try to serve the exact file first (with path traversal protection)
        file_path = (FRONTEND_DIST / path).resolve()
        if file_path.is_relative_to(FRONTEND_DIST.resolve()) and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html (SPA routing)
        return FileResponse(FRONTEND_DIST / "index.html")
