# Frontend Migration Plan: Dash to React + MapLibre

## 1. Why Migrate

The Dash dashboard works as a proof-of-concept but has hit a design ceiling:

- **CSS wars**: Every style override requires `!important`. DataTable dark theme took 40+ lines of CSS hacks. Leaflet controls needed manual repositioning to avoid overlaps.
- **Limited interactivity**: No smooth animations, no drag-to-resize panels, no custom tooltips with rich HTML. Dash callbacks are server-roundtrips for what should be client-side state changes.
- **Component ecosystem**: Mantine components half-work in Dash. No access to the React ecosystem (Framer Motion, Radix, Headless UI, TanStack). Every UI pattern is a workaround.
- **Map constraints**: dash-leaflet wraps Leaflet with Python callbacks. No vector tiles, no 3D terrain, no smooth client-side marker clustering. MapLibre GL JS is the standard for web map applications.
- **Performance**: Every slider change triggers a full server roundtrip through Dash callbacks. In React, only the scorecard computation needs the server... everything else is client-side state.

**What's NOT broken**: The Python backend. The modeling (`src/model/`), pipeline (`src/pipeline/`), data loaders, and computation logic are solid, well-tested, and stay exactly as they are.

## 2. What Stays (Python Backend)

These files are untouched. They become the API's internal implementation:

| Module | Purpose | Key functions |
|--------|---------|---------------|
| `src/model/basic_model.py` | Core LCOE model, action flags, GEAS allocation | `lcoe_solar()`, `action_flags()`, `build_scorecard()` |
| `src/pipeline/` | All pipeline steps (PDF extractors, fact tables, dim tables) | `run_pipeline.py` orchestrates |
| `src/assumptions.py` | Default constants (CAPEX, WACC, thresholds) | Single source of truth |
| `src/dash/logic.py` | Live computation (LCOE recomputation, scorecard assembly) | `compute_scorecard_live()`, `compute_lcoe_live()`, `UserAssumptions`, `UserThresholds` |
| `src/dash/map_layers.py` | Geospatial layer loading (substations, rasters, polygons) | `get_all_layers()`, `load_peatland()`, `load_protected_forest()` |
| `src/dash/data_loader.py` | CSV loading + validation | `load_all_data()`, `prepare_resource_df()` |
| `src/dash/constants.py` | Colors, labels, slider configs | `ACTION_FLAG_COLORS`, `TABLE_COLUMNS`, `TIER1/2/3_SLIDERS` |
| `outputs/data/processed/` | Precomputed CSVs (scorecard, LCOE, resource, demand, RUPTL, grid cost) | 7 CSV files |

## 3. Architecture

```
                    React / Next.js Frontend
                    ========================
                    MapLibre GL JS (map)
                    TanStack Table (data grid)
                    Recharts (charts)
                    Tailwind CSS (styling)
                    Zustand (state)
                            |
                            | HTTP/JSON
                            |
                    FastAPI Backend
                    ==============
                    Thin API layer (~150 lines)
                    Calls existing Python functions
                    Serves cached GeoJSON/rasters
                    No new modeling code
                            |
                            | Direct import
                            |
                    Existing Python Modules
                    =======================
                    src/model/basic_model.py
                    src/dash/logic.py
                    src/dash/map_layers.py
                    src/dash/data_loader.py
```

The FastAPI server starts, loads all data once (same as current `_load_data()`), caches map layers, and serves endpoints. The React app fetches data and handles all UI state client-side.

## 4. Backend API Specification

### 4.1 GET `/api/defaults`

Returns default assumptions, thresholds, and slider configurations.

```json
{
  "assumptions": {
    "capex_usd_per_kw": 960,
    "lifetime_yr": 27,
    "wacc_pct": 10.0,
    "fom_usd_per_kw_yr": 7.5,
    "gentie_cost_per_kw_km": 7.0,
    "substation_works_per_kw": 165.0,
    "transmission_lease_mid_usd_mwh": 8.0,
    "firming_adder_mid_usd_mwh": 10.0,
    "idr_usd_rate": 16000.0
  },
  "thresholds": {
    "pvout_threshold": 1550.0,
    "plan_late_threshold": 0.6,
    "geas_threshold": 0.3,
    "resilience_gap_pct": 20.0,
    "min_viable_mwp": 10.0,
    "reliability_threshold": 0.6
  },
  "slider_configs": {
    "tier1": { ... },
    "tier2": { ... },
    "tier3": { ... },
    "wacc": { "min": 4, "max": 20, "step": 2, "marks": [...] }
  }
}
```

**Implementation**: Calls `get_default_assumptions().to_dict()` + `get_default_thresholds().to_dict()` + serializes `TIER1/2/3_SLIDERS` from constants.

### 4.2 POST `/api/scorecard`

The main computation endpoint. Recomputes LCOE and action flags for all 25 KEKs at user-adjusted assumptions.

**Request**:
```json
{
  "assumptions": { "capex_usd_per_kw": 960, "wacc_pct": 10.0, ... },
  "thresholds": { "pvout_threshold": 1550, ... },
  "benchmark_mode": "bpp"
}
```

**Response**:
```json
{
  "scorecard": [
    {
      "kek_id": "kek-kendal",
      "kek_name": "Kendal",
      "province": "Central Java",
      "latitude": -6.92,
      "longitude": 110.18,
      "action_flag": "solar_now",
      "lcoe_mid_usd_mwh": 54.2,
      "lcoe_low_usd_mwh": 48.1,
      "lcoe_high_usd_mwh": 61.3,
      "solar_competitive_gap_pct": -14.1,
      "dashboard_rate_usd_mwh": 63.08,
      "carbon_breakeven_usd_tco2": 0,
      "buildable_area_ha": 2477.4,
      "max_captive_capacity_mwp": 247.7,
      "project_viable": true,
      "best_re_technology": "solar",
      "grid_cost_usd_mwh": 63.08
    },
    ...
  ]
}
```

**Implementation**: Calls `compute_scorecard_live(resource_df, assumptions, thresholds, ruptl_metrics, demand_df, grid_df)`. ~5ms for 25 KEKs.

### 4.3 GET `/api/layers/{layer_name}`

Serves cached geospatial layers. Layer names: `substations`, `kek_polygons`, `pvout`, `wind`, `buildable`, `peatland`, `protected_forest`, `industrial`.

**Response for vector layers** (substations, kek_polygons, peatland, protected_forest):
```json
{
  "type": "FeatureCollection",
  "features": [...]
}
```

**Response for point layers** (substations, industrial):
```json
{
  "points": [
    { "lat": -6.92, "lon": 110.18, "name": "Kendal 150kV", "voltage": "150kV", "capacity_mva": 60 },
    ...
  ]
}
```

**Response for raster layers** (pvout, wind, buildable):
```json
{
  "image_url": "data:image/png;base64,...",
  "bounds": [[lat_min, lon_min], [lat_max, lon_max]]
}
```

**Implementation**: Returns from `get_all_layers()` cache. Loaded once at startup.

### 4.4 GET `/api/kek/{kek_id}/polygon`

Returns a single KEK's polygon geometry with bounding box.

```json
{
  "feature": { "type": "Feature", "geometry": {...}, "properties": {...} },
  "bbox": { "min_lon": 110.1, "min_lat": -7.0, "max_lon": 110.3, "max_lat": -6.8 },
  "center": { "lat": -6.92, "lon": 110.18 }
}
```

**Implementation**: `get_kek_polygon_by_id(kek_id)` + `polygon_bbox()`.

### 4.5 GET `/api/kek/{kek_id}/substations?radius_km=50`

Returns substations near a KEK, with nearest highlighted.

```json
{
  "substations": [
    { "lat": -6.95, "lon": 110.2, "name": "Kendal 150kV", "dist_km": 3.2, "is_nearest": true },
    ...
  ]
}
```

**Implementation**: `filter_substations_near_point()` + lookup in `fct_substation_proximity`.

### 4.6 POST `/api/charts/quadrant`

Returns Plotly figure JSON for the LCOE vs grid cost quadrant chart.

**Request**: `{ "scorecard": [...], "benchmark_mode": "bpp" }`
**Response**: `{ "data": [...], "layout": {...} }` (Plotly figure dict)

**Implementation**: Same logic as current `update_quadrant` callback.

### 4.7 POST `/api/charts/ruptl`

Returns Plotly figure JSON for the RUPTL capacity additions chart.

**Request**: `{ "scorecard": [...], "region_filter": "all", "scenario": "baseline", "selected_kek": null }`
**Response**: `{ "data": [...], "layout": {...} }` (Plotly figure dict)

**Implementation**: Same logic as current `update_ruptl` callback.

### 4.8 GET `/api/tables/scorecard`

Returns the precomputed scorecard as JSON (no live computation, default assumptions).

```json
{
  "columns": ["kek_name", "province", "action_flag", ...],
  "records": [...]
}
```

**Implementation**: Reads `_DATA["fct_kek_scorecard"]`.

## 5. Frontend Components

### Component tree (maps to current Dash layout)

```
<App>
  <Header>
    <Title />
    <EnergyToggle />          // SegmentedControl → radio group
    <ActionFlagLegend />      // horizontal dot legend
    <KEKCounter />            // "25 KEKs" badge
  </Header>
  <MapView>                   // MapLibre GL JS
    <MapLibreMap />
    <LayerControl />          // overlay toggle panel
    <BackButton />            // "Back to National View"
    <AssumptionsPanel />      // collapsible slider card
  </MapView>
  <ScoreDrawer>               // right slide-over panel
    <KEKName />
    <Tabs>
      <ResourceTab />
      <LCOETab />
      <DemandTab />
      <PipelineTab />
      <FlagsTab />
    </Tabs>
  </ScoreDrawer>
  <BottomPanel>               // resizable bottom panel
    <DragHandle />
    <Tabs>
      <DataTable />           // TanStack Table
      <QuadrantChart />       // Recharts scatter
      <RUPTLChart />          // Recharts bar
      <FlipScenario />        // future
    </Tabs>
  </BottomPanel>
</App>
```

### Component mapping (Dash to React)

| Dash Component | React Replacement | Library |
|----------------|-------------------|---------|
| `dl.Map` + `dl.TileLayer` | `<Map>` + dark Mapbox/MapTiler style | `react-map-gl` + MapLibre GL JS |
| `dl.CircleMarker` (KEK dots) | MapLibre circle layer or custom HTML markers | MapLibre GL JS |
| `dl.GeoJSON` (polygons) | MapLibre `fill` + `line` layers | MapLibre GL JS |
| `dl.ImageOverlay` (rasters) | MapLibre raster source | MapLibre GL JS |
| `dl.LayersControl` | Custom `<LayerControl>` component | Headless (custom) |
| `dash.DataTable` | `<DataTable>` with TanStack | `@tanstack/react-table` |
| `dmc.Drawer` | `<Sheet>` or `<Drawer>` | Radix / Vaul |
| `dmc.Tabs` | `<Tabs>` | Radix Tabs |
| `dmc.Accordion` | `<Accordion>` | Radix Accordion |
| `dmc.Paper` | `<div>` with Tailwind classes | Tailwind |
| `dcc.Slider` | `<Slider>` | Radix Slider or rc-slider |
| `dcc.Dropdown` | `<Select>` | Radix Select |
| `dcc.Graph` (Plotly) | Recharts or Plotly.js React | `recharts` or `react-plotly.js` |
| `dcc.Store` (5x) | Zustand store | `zustand` |
| `dmc.SegmentedControl` | `<ToggleGroup>` | Radix Toggle Group |
| `dmc.Tooltip` | `<Tooltip>` | Radix Tooltip |

## 6. State Management

Current Dash stores map to a single Zustand store:

```typescript
interface DashboardStore {
  // Current dcc.Store equivalents
  assumptions: UserAssumptions;       // user-assumptions
  thresholds: UserThresholds;         // user-thresholds
  selectedKek: string | null;         // selected-kek
  scorecard: ScorecardRow[] | null;   // scorecard-live-data
  drawerOpen: boolean;                // drawer-open

  // UI state (currently implicit in Dash)
  assumptionsExpanded: boolean;
  scorecardDrawerOpen: boolean;
  activeTab: 'table' | 'quadrant' | 'ruptl' | 'flip';
  layerVisibility: Record<string, boolean>;
  benchmarkMode: 'bpp' | 'tariff';

  // Actions
  setAssumptions: (a: Partial<UserAssumptions>) => void;
  setThresholds: (t: Partial<UserThresholds>) => void;
  selectKek: (id: string | null) => void;
  recomputeScorecard: () => Promise<void>;  // calls POST /api/scorecard
  resetDefaults: () => void;
}
```

**Data flow**:
1. User adjusts slider → `setAssumptions({ capex: 900 })`
2. Debounce 300ms → `recomputeScorecard()` → `POST /api/scorecard`
3. Response updates `scorecard` in store
4. All subscribed components (map markers, table, charts) re-render automatically
5. No server roundtrip for UI-only changes (drawer toggle, tab switch, layer visibility)

## 7. Map Layers Migration

### Vector layers

| Current (Dash-Leaflet) | React (MapLibre) |
|------------------------|-------------------|
| `dl.CircleMarker` per KEK with `n_clicks` callback | MapLibre `circle` layer with `on('click')` event. Color from `ACTION_FLAG_COLORS`. Cursor changes on hover. |
| `dl.GeoJSON(data=kek_polygons)` | `map.addSource('kek-polygons', { type: 'geojson', data })` + `fill` layer (transparent) + `line` layer (colored border) |
| `dl.CircleMarker` per substation | MapLibre `circle` layer, separate source. Toggle via `setLayoutProperty('visibility')` |
| `dl.GeoJSON(data=peatland)` | MapLibre `fill` layer, brown, 30% opacity. Toggle via visibility. |
| `dl.GeoJSON(data=protected_forest)` | MapLibre `fill` layer, green, 25% opacity. Toggle via visibility. |
| `dl.CircleMarker` per industrial facility | MapLibre `circle` layer, orange, small radius. Toggle via visibility. |

### Raster layers

| Current | React |
|---------|-------|
| `dl.ImageOverlay(url=base64_png, bounds=bounds)` | MapLibre `raster` source with `image` type: `map.addSource('pvout', { type: 'image', url: base64, coordinates: bounds })` + `raster` layer |

### Interactions

| Current | React |
|---------|-------|
| Pattern-matching `Input({"type": "kek-marker", "kek_id": ALL}, "n_clicks")` | `map.on('click', 'kek-markers', (e) => selectKek(e.features[0].properties.kek_id))` |
| `Output("leaflet-map", "viewport")` with `transition="flyTo"` | `map.flyTo({ center: [lon, lat], zoom: 12 })` |
| `dl.Tooltip(...)` on markers | MapLibre popup on hover: `map.on('mouseenter', 'kek-markers', showPopup)` |
| Layer toggle via `dl.LayersControl` | Custom `<LayerControl>` component toggling `map.setLayoutProperty(layerId, 'visibility', 'visible'/'none')` |

## 8. Callback-to-React Mapping

Every current Dash callback and where it goes:

| # | Current Callback | React Equivalent | Server? |
|---|-----------------|-------------------|---------|
| 1 | `toggle_assumptions` | `useState` toggle | No |
| 2 | `toggle_drawer` | `useState` or CSS transition | No |
| 3 | `update_drawer_state` | Zustand `drawerOpen` | No |
| 4 | `update_assumptions` | Zustand `setAssumptions()` on slider change | No |
| 5 | `update_summary` | Derived from `store.assumptions` (computed in render) | No |
| 6 | `update_thresholds` | Zustand `setThresholds()` on slider change | No |
| 7 | `reset_defaults` | `resetDefaults()` resets store to initial values | No |
| 8 | `recompute_scorecard` | `POST /api/scorecard` via `recomputeScorecard()` | **Yes** |
| 9 | `update_map` | MapLibre re-renders from `store.scorecard` (client-side) | No |
| 10 | `update_table` | TanStack Table re-filters from `store.scorecard` (client-side) | No |
| 11 | `update_quadrant` | Recharts scatter re-renders from `store.scorecard` | No (or Yes if keeping Plotly) |
| 12 | `update_ruptl` | Recharts bar re-renders, or `POST /api/charts/ruptl` | Optional |
| 13 | `marker_click` | `map.on('click')` → `selectKek(id)` | No |
| 14 | `back_to_national` | `selectKek(null)` + `map.flyTo(national)` | No |
| 15 | `table_click` | `onRowClick` → `selectKek(id)` | No |
| 16 | `clear_kek_on_close` | Drawer `onClose` → `selectKek(null)` | No |
| 17 | `update_scorecard` | `<ScoreDrawer>` reads `store.scorecard` + fetches polygon/substations | Partial (polygon + substations) |

**Result**: Only 1-3 endpoints actually need the server. The rest is client-side state. This is the whole performance gain.

## 9. Migration Phases

### Phase 1: FastAPI Backend (1 day)

Create `src/api/main.py`:

```
src/api/
  __init__.py
  main.py          # FastAPI app, CORS, startup loader
  routes/
    scorecard.py   # POST /api/scorecard, GET /api/defaults
    layers.py      # GET /api/layers/{name}, GET /api/kek/{id}/polygon
    charts.py      # POST /api/charts/quadrant, POST /api/charts/ruptl
```

- Import existing `logic.py`, `map_layers.py`, `data_loader.py` directly
- Same `_load_data()` at startup, same `get_all_layers()` cache
- Add CORS middleware for local dev
- Pydantic models for request/response (generated from `UserAssumptions`/`UserThresholds` dataclasses)

**Test**: `curl http://localhost:8000/api/defaults` returns JSON. `curl -X POST http://localhost:8000/api/scorecard -d '{"assumptions": {...}}'` returns 25 rows.

### Phase 2: React Scaffold + MapLibre Map (2 days)

```
frontend/
  package.json
  next.config.js
  tailwind.config.js
  src/
    app/
      layout.tsx
      page.tsx
    components/
      map/
        MapView.tsx        # MapLibre container
        LayerControl.tsx   # toggle panel
        markers.ts         # KEK circle layer config
      layout/
        Header.tsx
        BottomPanel.tsx
    store/
      dashboard.ts         # Zustand store
    lib/
      api.ts               # fetch wrappers
      types.ts             # TypeScript interfaces
    styles/
      globals.css          # Tailwind + dark theme
```

- MapLibre GL JS with dark Mapbox style (same tile URL)
- KEK markers as circle layer, colored by action_flag
- Click marker → fly to polygon → open scorecard drawer
- Layer toggles for all 8 overlays

**Test**: Map renders, markers show, click flies to KEK.

### Phase 3: Table + Charts (1 day)

- TanStack Table with dark theme, colored action flag dots, sorting
- Quadrant chart (Recharts scatter or keep Plotly.js)
- RUPTL chart (Recharts stacked bar)
- Wire to Zustand store so they update when scorecard changes

**Test**: Slider change → table/charts update. Sort works. Action flag filter works.

### Phase 4: Assumptions Panel + Scorecard Drawer (2 days)

- Slider card with Tier 1/2/3 grouping (Radix Accordion)
- Scorecard drawer with 5 tabs (Resource, LCOE, Demand, Pipeline, Flags)
- Debounced slider → `POST /api/scorecard` → store update → map/table/chart re-render
- Reset to defaults button

**Test**: Adjust WACC slider → LCOE values change → map colors update → table re-sorts.

### Phase 5: Polish + Responsive (1 day)

- Smooth transitions (Framer Motion for drawer, panel resize)
- Responsive layout (mobile: bottom panel full-width, no side drawer)
- Loading states (skeleton on scorecard recompute)
- Keyboard shortcuts (Escape to close drawer, arrow keys for slider)
- Export CSV from table
- URL state (selected KEK in query param for shareability)

**Test**: Resize window. Open on mobile. Share URL with KEK selected.

## 10. Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 14** (App Router) | File-based routing, server components for initial data, great DX |
| Map | **MapLibre GL JS** via `react-map-gl` | Vector tiles, smooth fly-to, custom markers, free, no token needed for self-hosted styles |
| Map style | **Mapbox Dark v11** (current) or **MapTiler Dark** | Already using Mapbox tiles, keep the same look |
| Table | **TanStack Table v8** | Headless, virtual scrolling, full styling control, sorting/filtering built in |
| Charts | **Recharts** or **Plotly.js React** | Recharts for simple charts (lighter), Plotly.js if we want feature parity fast |
| Styling | **Tailwind CSS** | Utility-first, dark theme trivial, no CSS-in-JS overhead |
| State | **Zustand** | Tiny, no boilerplate, works great with React 18 |
| UI primitives | **Radix UI** | Headless, accessible, composable (Slider, Tooltip, Tabs, Accordion, Dialog) |
| HTTP | **fetch** or **ky** | Simple, no need for axios |
| Backend | **FastAPI** | Already Python, async, auto-generated OpenAPI docs, Pydantic validation |

## 11. Proposed File Structure

```
eez/
  src/
    api/                          # NEW: FastAPI backend
      main.py
      routes/
        scorecard.py
        layers.py
        charts.py
    model/                        # UNCHANGED
    pipeline/                     # UNCHANGED
    dash/                         # KEEP (Dash app still works as fallback)
      app.py
      logic.py                    # Imported by api/routes/scorecard.py
      map_layers.py               # Imported by api/routes/layers.py
      data_loader.py              # Imported by api/main.py
      constants.py                # Imported by both
  frontend/                       # NEW: React app
    package.json
    next.config.js
    tailwind.config.js
    tsconfig.json
    public/
    src/
      app/
        layout.tsx
        page.tsx
        globals.css
      components/
        map/
          MapView.tsx
          LayerControl.tsx
          KekMarkers.tsx
          RasterOverlay.tsx
        panels/
          AssumptionsPanel.tsx
          ScoreDrawer.tsx
          BottomPanel.tsx
        table/
          DataTable.tsx
          columns.tsx
        charts/
          QuadrantChart.tsx
          RuptlChart.tsx
        ui/
          Header.tsx
          ActionFlagLegend.tsx
          Slider.tsx
          Tabs.tsx
      store/
        dashboard.ts
      lib/
        api.ts
        types.ts
        constants.ts
      hooks/
        useScorecard.ts
        useMapLayers.ts
```

## 12. Running Both During Migration

During development, both apps can run simultaneously:

```bash
# Terminal 1: FastAPI backend (replaces Dash for data)
uv run uvicorn src.api.main:app --reload --port 8000

# Terminal 2: React frontend
cd frontend && npm run dev    # localhost:3000, proxies API to :8000

# Terminal 3: Dash app (still works as fallback)
uv run python -m src.dash.app   # localhost:8050
```

The Dash app remains functional throughout migration. Switch over when the React app reaches feature parity. No big-bang cutover.

## 13. Performance Expectations

| Action | Current (Dash) | After (React) |
|--------|---------------|---------------|
| Slider → scorecard update | ~500ms (server roundtrip + re-render all) | ~50ms (debounce + fetch + client re-render) |
| Map fly-to on KEK click | ~300ms (callback → rebuild MapContainer) | ~100ms (client-side flyTo, no server) |
| Layer toggle | ~200ms (callback → rebuild layers) | ~5ms (CSS visibility toggle) |
| Table sort | ~150ms (callback) | ~10ms (client-side TanStack sort) |
| Initial page load | ~3s (load all layers + compute scorecard) | ~1.5s (parallel fetch + streaming) |

## 14. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| MapLibre learning curve | `react-map-gl` abstracts most complexity. Mapbox GL JS docs apply 1:1. |
| Raster overlay compatibility | MapLibre supports `image` source type. Same base64 PNG approach works. |
| Chart parity | Start with `react-plotly.js` for exact parity, migrate to Recharts later for bundle size. |
| Two apps to maintain during migration | Phase-by-phase approach. Dash app stays until React has full parity. |
| Deployment complexity | Frontend: Vercel or static export. Backend: same Python server. Or combine with Next.js API routes if backend is simple enough. |
