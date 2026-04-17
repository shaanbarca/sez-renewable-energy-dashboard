# Stage 1: Build frontend
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app
FROM python:3.13-slim
WORKDIR /app

# System libs required by pyexpat (XML parsing) and GDAL/GEOS/PROJ runtime
# deps pulled in by geopandas/shapely/rasterio wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python deps
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Copy app code
COPY src/ src/
COPY config/ config/
COPY data/ data/
COPY outputs/ outputs/
COPY docs/METHODOLOGY_CONSOLIDATED.md docs/METHODOLOGY_CONSOLIDATED.md

# Copy frontend build from stage 1
COPY --from=frontend /app/frontend/dist frontend/dist

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
