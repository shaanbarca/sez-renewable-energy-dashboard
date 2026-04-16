# Feature: KEK Planning Mode — Draw, Analyze, Save/Load

## Context

Users want to evaluate hypothetical KEK locations before they exist. The workflow: draw a polygon on the map, specify industry type and demand, get a full ScoreDrawer analysis, then save the spec as a JSON file they can share or re-upload later. No database needed... the file IS the storage.

This matters because the dashboard currently only analyzes the 25 existing KEKs. Investors and policy makers evaluating new sites have to mentally interpolate. Planning Mode turns the dashboard from a reference tool into a decision tool.

---

## User Flow

1. Click "Plan a KEK" button (header or map toolbar)
2. Map enters drawing mode. User clicks to place polygon vertices, double-click to close.
3. Side panel shows a form: name, industry type (dropdown), estimated demand (GWh), reliability requirement (slider)
4. Click "Analyze" — backend samples PVOUT/wind from GeoTIFF, finds nearest substations, computes full scorecard
5. ScoreDrawer opens with the hypothetical KEK's analysis (all 6 tabs)
6. User can adjust assumptions sliders and re-analyze (same as existing KEKs)
7. "Save Plan" — downloads `.kek.json` file containing polygon + params + results
8. "Load Plan" — uploads file, restores polygon on map + ScoreDrawer analysis

---

## Architecture

### Save/Load File Format (`.kek.json`)

```json
{
  "version": 1,
  "type": "kek_plan",
  "created_at": "2026-04-16T14:30:00Z",
  "name": "Proposed Sulawesi Nickel Zone",
  "polygon": {
    "type": "Feature",
    "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] },
    "properties": {}
  },
  "centroid": { "lat": -2.45, "lon": 121.34 },
  "parameters": {
    "industry_type": "nickel_smelting",
    "demand_gwh": 2.5,
    "reliability_req": 0.8
  },
  "assumptions": { "wacc_pct": 10, "capex_usd_per_kw": 750, "..." : "..." },
  "thresholds": { "pvout_threshold": 1350, "..." : "..." },
  "energy_mode": "hybrid",
  "benchmark_mode": "bpp",
  "results": { "...ScorecardRow fields..." }
}
```

The `results` field caches the full scorecard so the file can be viewed without re-computing. On upload, the frontend renders from `results` immediately, then optionally re-analyzes with current assumptions.

---

## Implementation Plan

### Phase 1: Polygon Drawing Tool

**New file: `frontend/src/components/map/PolygonDrawTool.tsx`**

Follow the `MeasureTool.tsx` pattern (click accumulation, GeoJSON rendering, keyboard handlers):
- Toggle via `planningMode` state in store
- Accumulate click points into polygon ring
- Render as GeoJSON Polygon (fill + outline) while drawing
- Close on double-click or Enter
- Undo last point with Backspace
- Cancel with Escape
- Compute area (ha) from polygon using `@turf/area` (add dependency)
- Compute centroid using `@turf/centroid` (add dependency)
- Validate: minimum 3 points, non-self-intersecting

**Modify: `frontend/src/components/map/MapView.tsx`**
- Add `<PolygonDrawTool />` component
- Disable KEK click handlers when `planningMode` is active (same pattern as measuring)

**Modify: `frontend/src/store/dashboard.ts`**
- Add state: `planningMode: boolean`, `plannedPolygon: GeoJSON.Feature<Polygon> | null`, `plannedKek: ScorecardRow | null`
- Add actions: `startPlanning()`, `finishDrawing(polygon)`, `setPlannedKek(row)`, `clearPlan()`

### Phase 2: Planning Form Panel

**New file: `frontend/src/components/panels/PlanningPanel.tsx`**

A side panel (or modal) that appears after polygon is drawn:
- Text input: KEK name
- Dropdown: industry type (nickel smelting, steel, cement, petrochemical, general manufacturing, data center, other)
- Number input: estimated annual demand (GWh/year), with preset buttons for common sizes (0.5, 1.0, 2.5, 5.0, 10.0)
- Slider: reliability requirement (0.5-1.0, default 0.8)
- Shows computed polygon area (ha) and centroid coordinates
- "Analyze" button -> calls new API endpoint
- "Save Plan" button -> serializes to JSON, triggers file download
- "Load Plan" button -> file input, parses JSON, restores state

**Industry type mapping** (for CBAM analysis and demand estimation):
```typescript
const INDUSTRY_PRESETS: Record<string, {
  cbam_product?: string;
  emission_intensity?: number;
  default_demand_gwh?: number;
}> = {
  nickel_smelting: { cbam_product: 'iron_steel', emission_intensity: 8.0, default_demand_gwh: 3.0 },
  steel:           { cbam_product: 'iron_steel', emission_intensity: 1.8, default_demand_gwh: 2.0 },
  cement:          { cbam_product: 'cement',     emission_intensity: 0.6, default_demand_gwh: 1.0 },
  aluminium:       { cbam_product: 'aluminium',  emission_intensity: 14.0, default_demand_gwh: 5.0 },
  petrochemical:   { cbam_product: 'fertilizer', emission_intensity: 2.5, default_demand_gwh: 2.0 },
  general_manufacturing: { default_demand_gwh: 1.0 },
  data_center:           { default_demand_gwh: 2.0 },
  other:                 { default_demand_gwh: 1.0 },
};
```

### Phase 3: Backend — On-the-Fly Resource Sampling

**New file: `src/api/routes/planning.py`**

New endpoint:
```
POST /api/plan/analyze
Body: {
  "polygon": GeoJSON Feature,
  "centroid": { "lat": float, "lon": float },
  "area_ha": float,
  "name": string,
  "industry_type": string,
  "demand_gwh": float,
  "reliability_req": float,
  "assumptions": UserAssumptions,
  "thresholds": UserThresholds,
  "energy_mode": string,
  "benchmark_mode": string
}
Returns: ScorecardRow (same shape as existing scorecard rows)
```

**New file: `src/pipeline/sample_resource.py`**

On-the-fly GeoTIFF sampling utilities (extract from existing `build_fct_kek_resource.py`):
- `sample_pvout_centroid(lat, lon)` — sample PVOUT at point from GeoTIFF
- `sample_pvout_best_50km(lat, lon)` — find max PVOUT within 50km radius
- `sample_wind_speed(lat, lon)` — sample wind speed at 100m hub height
- `sample_wind_best_50km(lat, lon)` — find max wind speed within 50km

These reuse the existing `_sample_centroid()` and `_sample_best_50km()` internal functions from `build_fct_kek_resource.py`, refactored into importable utilities.

**New file: `src/planning/score_hypothetical.py`**

Orchestrator that assembles a ScorecardRow for a hypothetical location:

```python
def score_hypothetical_kek(
    polygon: dict,          # GeoJSON geometry
    centroid: tuple,        # (lat, lon)
    area_ha: float,
    name: str,
    industry_type: str,
    demand_gwh: float,
    reliability_req: float,
    assumptions: dict,
    thresholds: dict,
    energy_mode: str,
    benchmark_mode: str,
) -> dict:
    """Build a full ScorecardRow for a hypothetical KEK location."""
```

Steps inside:
1. **Sample solar resource**: `sample_pvout_centroid(lat, lon)` + `sample_pvout_best_50km(lat, lon)`
2. **Sample wind resource**: `sample_wind_speed(lat, lon)` + `sample_wind_best_50km(lat, lon)`
3. **Find nearest substations**: haversine scan over `substation.geojson` (2,913 points, fast in-memory)
4. **Determine grid region**: reverse-lookup from nearest substation's `regpln` field
5. **Get grid cost proxy**: lookup BPP/tariff from `fct_grid_cost_proxy` by grid region
6. **Compute LCOE** (solar, wind, hybrid): reuse existing `basic_model.py` functions with sampled CF
7. **Compute grid integration**: reuse `grid_integration_category()` with computed distances
8. **Compute action flags**: reuse `action_flags()` with all derived inputs
9. **Compute CBAM exposure**: from `industry_type` mapping
10. **Assemble ScorecardRow**: merge all computed fields into the standard row shape

**What degrades gracefully without GeoTIFFs on server:**
- If PVOUT GeoTIFF missing: return error asking user to provide PVOUT estimate manually (add optional override field to form)
- Buildability layers missing: `buildable_area_ha` = NaN, `max_captive_capacity_mwp` = NaN (same as existing KEKs without buildability data)

### Phase 4: ScoreDrawer Integration

**Modify: `frontend/src/components/panels/ScoreDrawer.tsx`**

- Check if rendering a planned KEK (`plannedKek` in store) vs real KEK
- If planned: use `plannedKek` data, show "Hypothetical" badge on header
- If planned: show "Save Plan" / "Re-analyze" buttons in header
- No changes to tab components... they already render from ScorecardRow fields

**Modify: `frontend/src/components/ui/Header.tsx`**

- Add "Plan a KEK" button (map pin + plus icon)
- Add "Load Plan" button (upload icon) with hidden file input
- Planning mode indicator when active

### Phase 5: Save/Load Implementation

**Save (frontend only, no API needed):**
```typescript
function savePlan() {
  const plan = {
    version: 1,
    type: 'kek_plan',
    created_at: new Date().toISOString(),
    name: plannedKek.kek_name,
    polygon: plannedPolygon,
    centroid: { lat, lon },
    parameters: { industry_type, demand_gwh, reliability_req },
    assumptions: store.assumptions,
    thresholds: store.thresholds,
    energy_mode: store.energyMode,
    benchmark_mode: store.benchmarkMode,
    results: plannedKek,
  };
  const blob = new Blob([JSON.stringify(plan, null, 2)], { type: 'application/json' });
  // trigger download as "{name}.kek.json"
}
```

**Load (frontend, optional re-analyze):**
```typescript
function loadPlan(file: File) {
  const plan = JSON.parse(await file.text());
  if (plan.version !== 1 || plan.type !== 'kek_plan') throw new Error('Invalid plan file');
  // Restore polygon on map
  store.setPlannedPolygon(plan.polygon);
  // Restore assumptions (optional: user might want current assumptions)
  // Render cached results immediately
  store.setPlannedKek(plan.results);
  // Fly to centroid
  store.flyTo(plan.centroid.lat, plan.centroid.lon, 10);
}
```

---

## Critical Files

| File | Change | New/Modify |
|------|--------|------------|
| `frontend/src/components/map/PolygonDrawTool.tsx` | Polygon drawing component | New |
| `frontend/src/components/map/MapView.tsx` | Integrate drawing tool, disable KEK clicks in planning mode | Modify |
| `frontend/src/components/panels/PlanningPanel.tsx` | Form for KEK parameters + save/load buttons | New |
| `frontend/src/components/panels/ScoreDrawer.tsx` | Hypothetical KEK badge, save/re-analyze buttons | Modify |
| `frontend/src/components/ui/Header.tsx` | Plan/Load buttons | Modify |
| `frontend/src/store/dashboard.ts` | Planning mode state, planned polygon/KEK | Modify |
| `frontend/src/lib/api.ts` | `analyzePlannedKek()` fetch wrapper | Modify |
| `frontend/src/lib/types.ts` | `KekPlan` type for save/load format | Modify |
| `src/api/routes/planning.py` | `POST /api/plan/analyze` endpoint | New |
| `src/api/main.py` | Register planning router | Modify |
| `src/pipeline/sample_resource.py` | On-the-fly PVOUT/wind GeoTIFF sampling utilities | New |
| `src/planning/score_hypothetical.py` | Orchestrator: assemble ScorecardRow for hypothetical location | New |

---

## Dependencies to Add

**Frontend (npm):**
- `@turf/area` — polygon area calculation
- `@turf/centroid` — polygon centroid

(`@turf/distance` and `@turf/helpers` already installed for MeasureTool)

**Backend:** No new dependencies. `rasterio` already in `pyproject.toml` for GeoTIFF work.

---

## What's NOT in Scope (V1)

- **Buildability filtering for hypothetical sites**: Existing KEKs have 5-layer buildability from the pipeline. Hypothetical KEKs skip this... they get raw PVOUT/wind, not buildable-area-filtered values. Can add later.
- **Multiple planned KEKs simultaneously**: V1 supports one planned KEK at a time. Clear before starting a new one.
- **Collaborative sharing via URL**: The file-based approach covers this. URL-sharing could come later via base64-encoded plan in query params (for small plans).
- **Comparison view**: Side-by-side planned vs existing KEK. Can be added later since planned KEKs produce the same ScorecardRow shape.

---

## Implementation Order

Build bottom-up so each layer is testable:

1. **`src/pipeline/sample_resource.py`** — extract sampling utilities, write tests
2. **`src/planning/score_hypothetical.py`** — orchestrator, write tests with mock PVOUT
3. **`src/api/routes/planning.py`** — API endpoint, test with curl
4. **Store changes** (`dashboard.ts`, `types.ts`, `api.ts`) — state management
5. **`PolygonDrawTool.tsx`** — drawing component
6. **`PlanningPanel.tsx`** — form + save/load
7. **ScoreDrawer + Header integration** — wire everything together
8. **Manual testing** — draw polygon, analyze, save, reload, verify all 6 tabs

---

## Verification

1. `uv run pytest tests/` — all existing tests pass + new planning tests
2. `npx tsc --noEmit` — frontend type-check clean
3. Draw polygon at known location (e.g., near existing KEK) — PVOUT and LCOE should be similar to the real KEK
4. Save plan -> open JSON file -> verify all fields present
5. Load saved plan -> polygon appears on map, ScoreDrawer shows same results
6. Switch energy modes (solar/wind/hybrid) with planned KEK — all tabs update correctly
7. Adjust assumption sliders -> re-analyze -> results change appropriately
8. Load plan with different assumptions than current -> cached results show immediately
