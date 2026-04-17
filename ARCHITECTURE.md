# Architecture — Indonesia Industrial Decarbonization

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Pipeline Dependency Graph](#pipeline-dependency-graph)
- [Key Design Decisions](#key-design-decisions)
  - [1. Star Schema — Dim + Fact Tables](#1-star-schema--dim--fact-tables)
  - [2. Precomputed Flat Tables — No Runtime Raster Operations](#2-precomputed-flat-tables--no-runtime-raster-operations)
  - [3. Builder Pattern — One Function Per Pipeline Step](#3-builder-pattern--one-function-per-pipeline-step)
  - [4. PDF Extractor Pattern — Pdfplumber + Hardcoded Fallback](#4-pdf-extractor-pattern--pdfplumber--hardcoded-fallback)
  - [5. Pure-Function Buildability Filters — No I/O, Fully Testable](#5-pure-function-buildability-filters--no-io-fully-testable)
  - [6. SiteTypeConfig Registry — One Dict Entry Per Site Type](#6-sitetypeconfig-registry--one-dict-entry-per-site-type)
- [Buildability Data Flow](#buildability-data-flow)
- [Module Map](#module-map)

---

## System Overview

```mermaid
flowchart TD
    subgraph RAW["Raw Inputs"]
        A1["KEK portal\n(scraped CSV/GeoJSON)"]
        A2["Global Solar Atlas\nGeoTIFFs (data/)"]
        A3["RUPTL 2025–2034\n(PDF)"]
        A4["Permen ESDM 7/2024\n(hardcoded tariffs)"]
        A5["ESDM Tech Catalogue\n(CSV + PDF p.66)"]
        A6["PLN substation.geojson"]
        A7["GEM Cement Tracker\n(32 operating plants)"]
        A8["GEM Iron & Steel Tracker\n(7 active plants)"]
        A9["CGSP Nickel Tracker\n(IIA filter → 10 clusters)"]
        A10["Residual manual CSV\n(priority1_sites.csv — 5 rows:\n2 aluminium + 3 fertilizer,\nprovenance-enforced)"]
    end

    subgraph BUILDABILITY["Buildability Data (data/buildability/)"]
        B1["Copernicus DEM GLO-30\n(dem_tiles/ + dem.vrt)"]
        B2["ESA WorldCover v200\n(worldcover_tiles/ + esa_worldcover.vrt)"]
        B3["GFW Peatlands v20230315\n(peat_tiles/ + peatland.vrt)"]
        B4["Kawasan Hutan\n(kawasan_hutan.shp — OSM/WDPA)"]
    end

    DL["scripts/download_buildability_data.py\n(downloads B1, B2, B3 automatically)"]

    subgraph PIPELINE["Pipeline (run_pipeline.py → src/pipeline/build_*.py)"]
        P1["dim_sites\n(25 KEK + 44 standalone + 10 cluster = 79 rows)"]
        P2["dim_tech_cost"]
        P3["fct_site_resource\n(PVOUT + buildability)"]
        P4["fct_site_demand\n(area-based OR sector-intensity)"]
        P5["fct_grid_cost_proxy"]
        P6["fct_ruptl_pipeline"]
        P7["fct_substation_proximity"]
        P8["fct_lcoe\n(1,422 rows: 79 × 9 × 2)"]
        P9["fct_site_scorecard"]
        P10["fct_captive_coal"]
        P11["fct_captive_nickel"]
        P12["fct_captive_steel"]
        P13["fct_captive_cement"]
        P14["fct_site_wind_resource"]
    end

    subgraph OUTPUTS["outputs/data/processed/"]
        O1["flat CSV tables\n(14 files)"]
    end

    API["FastAPI Backend\nsrc/api/main.py — loads CSVs at startup,\nserves JSON via 7 endpoints"]
    FRONTEND["React + Vite SPA\nfrontend/src/ — MapLibre map,\nTanStack Table, Recharts"]
    BROWSER["End-user browser"]

    A1 --> P1
    A7 --> P1
    A8 --> P1
    A9 --> P1
    A10 --> P1
    A2 --> P3
    A3 --> P6
    A4 --> P5
    A5 --> P2
    A6 --> P7
    BUILDABILITY --> P3
    DL --> BUILDABILITY

    P1 --> P3
    P1 --> P4
    P1 --> P5
    P1 --> P7
    P1 --> P8
    P1 --> P10
    P1 --> P11
    P1 --> P12
    P1 --> P13
    P1 --> P14
    P2 --> P8
    P3 --> P8
    P7 --> P8
    P8 --> P9
    P5 --> P9
    P6 --> P9
    P4 --> P9

    P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8 & P9 & P10 & P11 & P12 & P13 & P14 --> O1
    O1 --> API
    API --> FRONTEND
    FRONTEND --> BROWSER
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend runtime | Python | 3.11 | Pipeline, model, and API code |
| Backend API | FastAPI | latest | REST API serving scorecard and layer data |
| Package manager | uv | latest | Python dependency resolution + venv |
| Frontend | React + TypeScript | 18.x | SPA dashboard |
| Frontend bundler | Vite | 5.x | Dev server + production build |
| Map | MapLibre GL JS | 4.x | Interactive map via react-map-gl |
| Table | TanStack Table | 8.x | Sortable, filterable data table |
| Charts | Recharts | 2.x | Quadrant chart, RUPTL bar chart |
| State | Zustand | 5.x | Client-side state management |
| CSS | Tailwind CSS | 3.4 | Utility-first dark theme styling |
| Formatting (Python) | ruff | latest | Python linting + formatting (pre-commit) |
| Formatting (TS) | Biome | 2.x | TypeScript linting + formatting (pre-commit) |
| Geospatial raster | rasterio | 1.3+ | GeoTIFF window reads, VRT operations |
| Geospatial vector | geopandas | 0.14+ | KEK polygons, substation proximity |
| Numerical | numpy, scipy | — | Raster array ops, connected-component labeling |
| Data | pandas | 2.x | All tabular transforms |
| PDF extraction | pdfplumber | — | RUPTL + ESDM Tech Catalogue tables |
| Testing | pytest | — | 498 tests, all pure-function |
| Linting | ruff | — | Format + lint (configured in pyproject.toml) |

---

## Pipeline Dependency Graph

Topological order enforced by `run_pipeline.py` at runtime:

```
Stage 1 — Dimensions (no deps)
  industrial_sites_generated ← build_industrial_sites.py unions GEM Cement (32) + GEM Steel (7)
                               + CGSP Nickel IIA (10, with 5km KEK exclusion + 20km child aggregation)
                               + residual manual CSV (5, source_url required)
  dim_sites                 ← 25 KEK rows + industrial_sites_generated (54 rows) = 79 total;
                              auto-assigns grid_region_id from nearest substation regpln
  dim_tech_cost

Stage 2 — Facts (depend on dim_sites)
  fct_site_resource         ← dim_sites  [+ data/buildability/ when populated]
  fct_site_wind_resource    ← dim_sites
  fct_site_demand           ← dim_sites  [dual-mode: area_based (KEK/KI) | sector_intensity (standalone/cluster)]
  fct_grid_cost_proxy       ← dim_sites
  fct_ruptl_pipeline        (no deps)
  fct_substation_proximity  ← dim_sites

Stage 3 — Computed
  fct_lcoe                  ← dim_sites, fct_site_resource, dim_tech_cost, fct_substation_proximity
                              (1,422 rows = 79 sites × 9 WACC × 2 scenarios)

Stage 4 — Captive power  [dual-mode: proximity_match (KEK/KI) | direct_match (standalone/cluster)]
  fct_captive_coal          ← dim_sites
  fct_captive_nickel        ← dim_sites
  fct_captive_steel         ← dim_sites
  fct_captive_cement        ← dim_sites

Stage 5 — Final scorecard
  fct_site_scorecard        ← dim_sites, fct_lcoe, fct_grid_cost_proxy, fct_ruptl_pipeline, fct_site_demand,
                              fct_captive_{coal, nickel, steel, cement}
```

Run a single step: `uv run python run_pipeline.py fct_site_scorecard`
Run full pipeline: `uv run python run_pipeline.py`

---

## Key Design Decisions

### 1. Star Schema — Dim + Fact Tables

All data is stored as a star schema (dimension + fact tables) rather than a single denormalised CSV. `dim_sites` is the central entity; every fact table joins to it on `site_id`. This allows each pipeline step to be independently rebuilt without invalidating the full dataset, and keeps the API's startup load small — fourteen small CSVs instead of one wide join. `site_id` replaces the legacy `kek_id` — the unified schema covers both KEK zones (`site_type="kek"`) and industrial sites (`site_type` in `{"ki","standalone","cluster"}`).

### 2. Precomputed Flat Tables — No Runtime Raster Operations

The API reads precomputed CSV tables at startup. All raster operations (PVOUT extraction, slope/elevation masking, ESA WorldCover land cover, peatland exclusion, Kawasan Hutan rasterisation) happen offline in `build_fct_site_resource.py`. This keeps the dashboard stateless and fast — the heaviest raster job (~17 peatland tiles + DEM) takes ~3 minutes once; the app never touches a GeoTIFF.

### 3. Builder Pattern — One Function Per Pipeline Step

Each pipeline step is a single `build_<name>() → pd.DataFrame` function in `src/pipeline/build_<name>.py`. The orchestrator (`run_pipeline.py`) handles dependency ordering via topological sort and writes each output to `outputs/data/processed/`. Adding a new step means: write one builder file, add one `Step(...)` entry. See `src/pipeline/TEMPLATE.py` for the canonical pattern.

### 4. PDF Extractor Pattern — Pdfplumber + Hardcoded Fallback

Two PDF sources (RUPTL, ESDM Tech Catalogue) are parsed by `src/pipeline/pdf_extract_*.py`. Each extractor tries pdfplumber first; if the page is image-based, the PDF is missing, or the layout changes, it falls back to a `VERIFIED_*` hardcoded dict that was manually verified against the source. The public API always returns data — callers never receive None. The `VERIFIED_*` dicts are the single source of truth for hardcoded values and are tested for exact match.

### 5. Pure-Function Buildability Filters — No I/O, Fully Testable

`src/pipeline/buildability_filters.py` contains zero file I/O. Every filter function accepts numpy arrays and returns numpy arrays. This makes the four buildability layers (slope/elevation, ESA WorldCover, GFW peatlands, Kawasan Hutan) independently unit-testable with synthetic rasters — no real GeoTIFFs required in the test suite. The integration (reading VRTs, windowing to site bounding boxes) lives exclusively in `build_fct_site_resource.py`.

### 6. SiteTypeConfig Registry — One Dict Entry Per Site Type

Per-site-type behavior (demand estimation, captive power matching, CBAM detection, marker shape, default reliability, drawer identity fields) is centralised in one place: `src/model/site_types.py`. A frozen dataclass `SiteTypeConfig` + dict `SITE_TYPES` keyed on `SiteType` StrEnum. The frontend mirrors this contract at `frontend/src/lib/siteTypes.ts` (TypeScript `Record<SiteType, SiteTypeConfig>`).

Every pipeline builder, live-compute function, and drawer component dispatches via `SITE_TYPES[row["site_type"]].{demand_method, captive_power_method, cbam_method, marker_shape, identity_fields}` — no `if site_type == "kek"` branches in business logic. Adding a new type (e.g. `"mining"`) is a two-file diff: one Python dict entry, one TypeScript dict entry. Data changes live in `data/industrial_sites/priority1_sites.csv`, not code.

Shared geometry utilities (`haversine_km`, `proximity_match`, `direct_match`) live in `src/pipeline/geo_utils.py` — imported by all five callers (`fct_substation_proximity` + four captive-power builders), eliminating 5× haversine duplication.

---

## Buildability Data Flow

`fct_site_resource` is the only pipeline step that reads raster data at build time. When `data/buildability/` is populated (run `scripts/download_buildability_data.py`), the four layers are applied in cascade per site:

```
PVOUT GeoTIFF (Global Solar Atlas, ~1km)
  ↓
Window to site 50km bounding box
  ↓
Layer 1a: kawasan_hutan.shp   → rasterize → binary mask → zero excluded pixels
Layer 1b: peatland.vrt        → read window → pixel > 0 = peat → zero excluded pixels
Layer 1c/d: esa_worldcover.vrt → read window → codes 10,40,50,80,90,95 → zero excluded pixels
Layer 2a/c: dem.vrt           → read window → compute slope → exclude slope>8° or elev>1500m
Layer 4: min area filter      → drop contiguous buildable patches < 10 ha
  ↓
buildable_area_ha             = n_buildable_pixels × pixel_area_ha
max_captive_capacity_mwp      = buildable_area_ha / 1.5 ha/MWp
pvout_buildable_best_50km     = max PVOUT value across all buildable pixels
buildability_constraint       = dominant filter layer (kawasan_hutan / peat / agriculture / slope / unconstrained)
```

When `data/buildability/` is absent, all four buildability columns are `NaN` and `resource_quality = "upper_bound"`.

---

## Module Map

```
src/
  model/
    basic_model.py              — Pure LCOE + action flag functions (no API dep)
    site_types.py               — SiteTypeConfig registry + SiteType/Sector StrEnums
  pipeline/
    build_dim_sites.py          ← unions 25 KEK + 54 industrial sites (tracker-driven + residual CSV)
    build_industrial_sites.py   ← GEM Cement (32) + GEM Steel (7) + CGSP Nickel IIA (10) + residual manual (5)
    build_dim_tech_cost.py
    build_fct_site_resource.py  ← heaviest; raster reads + buildability cascade
    build_fct_site_wind_resource.py
    build_fct_site_demand.py    ← dispatches on SITE_TYPES[...].demand_method
    build_fct_grid_cost_proxy.py
    build_fct_ruptl_pipeline.py
    build_fct_substation_proximity.py
    build_fct_lcoe.py
    build_fct_site_scorecard.py
    build_fct_captive_coal.py   ← dual-mode: proximity_match | direct_match
    build_fct_captive_nickel.py ← dual-mode
    build_fct_captive_steel.py  ← dual-mode; GEM Global Iron & Steel Plant Tracker
    build_fct_captive_cement.py ← dual-mode; GEM Global Cement Plant Tracker
    buildability_filters.py     ← pure filter functions, zero I/O
    geo_utils.py                ← shared haversine_km, proximity_match, direct_match
    demand_intensity.py         ← sector electricity intensity lookup (MWh/tonne)
    pdf_extract_ruptl.py
    pdf_extract_esdm_tech.py
    TEMPLATE.py                 ← canonical template for new pipeline steps
  assumptions.py                — All model constants with source citations

data/
  industrial_sites/
    priority1_sites.csv         ← residual manual rows only (5 sites: 2 aluminium + 3 fertilizer),
                                  provenance-enforced (source_url required; loader raises if missing)

scripts/
  download_buildability_data.py — Downloads DEM + ESA WorldCover + GFW peatlands; builds VRTs

tests/
  test_model.py                 — tests for basic_model.py
  test_pipeline.py              — tests for pipeline + buildability filters
  test_site_types.py            — SiteTypeConfig registry invariants
  test_geo_utils.py             — haversine + proximity/direct match functions
  test_demand_intensity.py      — sector-intensity formula for standalone/cluster
  test_captive_dual_mode.py     — proximity vs direct-assignment behavior

498 tests total (all pure-function).

frontend/src/
  lib/
    siteTypes.ts                — TypeScript mirror of SiteTypeConfig registry
    types.ts                    — ScorecardRow, SiteType, Sector contracts
  components/
    charts/SectorSummaryChart.tsx   — CBAM cost trajectory + demand by sector

run_pipeline.py                 — Orchestrator: topological sort + step runner
```
