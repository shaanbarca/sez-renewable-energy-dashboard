# Multi-RE Integration: Solar + Wind + Hydro + Geothermal

## Context

This is a **renewables dashboard**, not a solar dashboard. Every technology that can serve a KEK's electricity needs deserves the same analytical depth. For several KEKs (Morowali, Konawe in Sulawesi; Sei Mangkei in Sumatra), solar alone can't beat grid cost. Wind, hydro, or geothermal might. And even where solar wins on daytime LCOE, combining it with other RE sources could eliminate BESS cost entirely.

The goal: evolve from a solar-only tool to a "best renewable energy source" decision tool where every technology gets equal treatment in buildability, capacity, supply coverage, and economics.

---

## What Already Exists

### Wind

| Component | Status | Location |
|-----------|--------|----------|
| Wind speed raster (Global Wind Atlas v3, 100m) | ✅ Built | `data/wind/IDN_wind-speed_100m.tif` |
| Wind CF lookup (speed → CF, piecewise linear) | ✅ Built | `basic_model.py:123-186`, `wind_speed_to_cf()` |
| Wind LCOE precomputed (25 KEKs × 9 WACC × 2 scenarios) | ✅ Built | `build_fct_lcoe_wind.py`, reuses `lcoe_solar()` |
| Wind LCOE live computation (responds to WACC slider) | ✅ Built | `logic.py:compute_lcoe_wind_live()` |
| Wind tech cost (ESDM 2024, $1,650/kW, $40 FOM, 27yr) | ✅ Built | `dim_tech_cost_wind.csv` |
| `best_re_technology` selection (solar vs wind, live) | ✅ Built | `logic.py` in `compute_scorecard_live()` |
| Wind raster map layer | ✅ Built | `map_layers.py:454-487`, `RasterOverlay.tsx` |
| EnergyMode toggle (Solar/Wind/Overall) | ✅ Functional | `EnergyToggle.tsx`, wired to all tabs + map + table |
| Wind columns in ScoreDrawer (all 6 tabs) | ✅ Built | `ScoreDrawer.tsx` reads `energyMode` |
| Wind LCOE in table | ✅ Built | `columns.tsx` Wind LCOE column |
| Wind competitive gap (live, BPP-based) | ✅ Built | `wind_competitive_gap_pct` in scorecard output |
| **Wind buildable area analysis** | ❌ Not built | No land-use filtering for wind sites |
| **Wind capacity constraint** | ❌ Not built | No `max_wind_capacity_mwp` |
| **Wind buildable polygons (map layer)** | ❌ Not built | No equivalent of solar's `buildable_polygons.geojson` |
| **Wind supply coverage** | ❌ Not built | No wind generation vs demand calculation |
| **Wind within-boundary analysis** | ❌ Not built | No on-site wind potential |

### Hydro: data exists, no pipeline

| Component | Status | Location |
|-----------|--------|----------|
| Hydro potential GeoJSON (150+ MEMR/JICA projects) | ✅ Data exists | `data/hydro_potential.geojson` (115MB) |
| Pre-calculated LCOE per hydro project | ✅ In GeoJSON | `lcoe_o`, `mw_o`, `annual_o`, `irr_o` fields |
| ESDM tech IDs (TECH003/004/005) | ✅ Catalogued | `dim_tech_variant.csv` |
| ESDM tech parameters (CAPEX, FOM, lifetime) | ❌ Not extracted | No `build_dim_tech_cost_hydro.py` |
| Hydro LCOE pipeline | ❌ Not built | No `build_fct_lcoe_hydro.py` |
| Hydro map layer | ❌ Not built | GeoJSON exists but not loaded |
| Hydro in scorecard | ❌ Not built | No `lcoe_hydro_mid` column |

### Geothermal: aspirational, no data

| Component | Status |
|-----------|--------|
| MEMR One Map geothermal prospects | ❌ Not sourced |
| Tech parameters | ❌ Not extracted |
| Everything else | ❌ Not started |

---

## Key Architectural Insight

**The LCOE formula is already technology-agnostic.** `lcoe_solar()` in `basic_model.py:224` is just a CRF annuity formula. Wind already calls it (line 136 of `build_fct_lcoe_wind.py`). The name is misleading. The only solar-specific part is `degradation_annual_pct` (default 0.5%), which can be set to 0 for hydro/wind/geothermal.

This means adding a new RE technology is not a formula problem. It's a data + UI problem.

---

## Phased Plan

### Phase 1: Activate Wind — ✅ COMPLETE

All three sub-phases shipped on `feature/multi-re-integration`:

**1a. Wire EnergyMode toggle + frontend integration** — ✅ Done
- EnergyToggle wired to all 6 ScoreDrawer tabs, table columns, map layers
- Auto-switches PVOUT/wind rasters, hides solar buildable polygons in wind mode
- Economics, Demand, Overview tabs all energyMode-aware

**1b. Fix wind integration issues (from testing)** — ✅ Done
- Moved EnergyToggle near Layers button
- Auto-switch map layers on mode change
- Economics shows "Wind vs BPP" / "Best RE vs BPP" per mode
- Demand tab honest labeling ("Solar-Based" when in wind/overall)

**1c. Live wind LCOE computation** — ✅ Done
- `compute_lcoe_wind_live()` in `logic.py` — WACC slider now affects wind LCOE
- `best_re_technology` live-computed (flips solar/wind as WACC changes)
- `wind_competitive_gap_pct` computed by backend
- Removed precomputed wind merge from fct_kek_scorecard

### Phase 1D: Wind Analytical Parity (estimated 2-3 sessions)

Wind frontend is wired, but the analysis is shallow compared to solar. Solar has 4-layer buildability filtering, capacity constraints, supply coverage, within-boundary analysis, and buildable polygon map overlays. Wind has none of that. This phase brings wind to the same analytical depth.

#### What Solar Has That Wind Doesn't

| Analysis | Solar | Wind |
|----------|-------|------|
| Buildable area (land-use filtered) | `buildable_area_ha` via 4-layer cascade | Raw wind speed, no filtering |
| Capacity constraint | `max_captive_capacity_mwp = area / 1.5` | Unconstrained (infinite) |
| Buildable polygon map layer | `buildable_polygons.geojson` | Nothing |
| Within-boundary analysis | `within_boundary_capacity_mwp`, `pvout_within_boundary` | Nothing |
| Supply coverage | `solar_supply_coverage_pct = generation / demand` | Nothing |
| Temporal coverage | `firm_solar_coverage_pct`, `storage_gap_pct` | Nothing |
| Buildability constraint label | `"kawasan_hutan"`, `"slope"`, `"peat"`, etc. | Nothing |

#### 1D-1. Wind Buildability Filters

**New file:** `src/pipeline/wind_buildability_filters.py`

Wind turbines have different siting constraints than solar panels. Reuse some solar filters, modify others:

| Filter | Solar | Wind | Rationale |
|--------|-------|------|-----------|
| Kawasan Hutan (conservation forest) | ✅ Exclude | ✅ Exclude | Same legal constraint |
| Peatland | ✅ Exclude | ✅ Exclude | Same foundation issues |
| Land cover: water, wetland, mangrove | ✅ Exclude | ✅ Exclude | Same physical constraint |
| Land cover: tree cover | ✅ Exclude | ⚠️ Partial | Turbines can sit among trees if canopy is <hub height. **Exclude dense forest, allow sparse.** |
| Land cover: cropland | ✅ Exclude | ✅ Allow | Wind turbines coexist with agriculture (small footprint) |
| Land cover: built-up/urban | ✅ Exclude | ✅ Exclude | Noise/setback constraints |
| Slope >8° | ✅ Exclude | ❌ Allow up to 20° | Ridgelines are ideal for wind (speed-up effect). Steeper terrain = better wind. |
| Elevation >1,500m | ✅ Exclude | ✅ Exclude | Air density drops, CF degrades. Keep same threshold. |
| Minimum wind speed | N/A | ✅ NEW: >3.0 m/s | Below cut-in speed, no generation possible |

**Implementation:** Adapt `buildability_filters.py` functions. Most work is creating the wind-specific `_compute_buildable_wind()` function in `build_fct_kek_wind_resource.py` that:
1. Reads the wind speed raster (`IDN_wind-speed_100m.tif`) in a 50km window
2. Applies the wind-adapted filter cascade
3. Outputs buildable wind pixels (speed ≥ 3.0 m/s, suitable terrain)

**Constants to add to `wind_buildability_filters.py`:**
```python
WIND_MAX_SLOPE_DEG = 20.0          # Ridgelines OK for turbines
WIND_MIN_SPEED_MS = 3.0            # Below cut-in, no generation
WIND_HA_PER_MWP = 25.0             # ~4 MW/km² typical onshore spacing
WIND_LAND_COVER_EXCLUDED = {10, 50, 80, 90, 95}  # Tree, urban, water, wetland, mangrove
# Note: cropland (40) INCLUDED for wind (coexistence)
```

**Key difference: `WIND_HA_PER_MWP = 25.0`** (vs solar's 1.5). Wind turbines need 25 ha/MWp due to inter-turbine spacing (5-7 rotor diameters, ~630-880m for a 126m rotor). This is the industry standard ~4 MW/km² for onshore wind. Source: IRENA 2023, ESDM Technology Catalogue 2024.

#### 1D-2. Wind Buildable Area & Capacity

**File:** `src/pipeline/build_fct_kek_wind_resource.py` (extend existing)

Add to the existing wind resource pipeline:

```
New output columns in fct_kek_wind_resource.csv:
  - wind_buildable_area_ha        # Land area passing wind filters within 50km
  - max_wind_capacity_mwp         # = wind_buildable_area_ha / 25.0
  - wind_buildability_constraint  # Dominant binding constraint
  - best_wind_site_lat/lon        # Location of highest wind speed in buildable area
  - wind_speed_buildable_best_ms  # Best wind speed among buildable pixels
  - cf_wind_buildable_best        # CF at best buildable site
```

**Within-boundary wind analysis** (mirrors solar's `_compute_within_boundary_buildable()`):
```
  - within_boundary_wind_area_ha
  - within_boundary_wind_capacity_mwp
  - wind_speed_within_boundary_ms
  - cf_wind_within_boundary
```

#### 1D-3. Wind Buildable Polygons

**New script:** `src/pipeline/build_wind_buildable_polygons.py`

Same pattern as `build_buildable_polygons.py` for solar:
1. Apply wind buildability cascade to the wind speed raster
2. Vectorize buildable pixels to polygons (`rasterio.features.shapes()`)
3. Filter by minimum area (50 ha)
4. Per polygon: `area_ha`, `avg_wind_speed_ms`, `capacity_mwp`
5. Output: `outputs/assets/wind_buildable_polygons.geojson`

**Map layer:** Add `wind_buildable_polygons` to `map_layers.py` and `LayerControl.tsx`. Show in Wind mode (replaces solar buildable polygons).

**API endpoint:** `GET /layers/wind_buildable_polygons` + `GET /kek/{id}/wind_buildable`

#### 1D-4. Wind Supply Coverage

**File:** `src/dash/logic.py` (extend `compute_scorecard_live()`)

Mirror solar's supply coverage calculations:

```python
# Wind generation estimate
max_wind_generation_gwh = max_wind_capacity_mwp * cf_wind_best * 8760 / 1000

# Wind supply coverage
wind_supply_coverage_pct = max_wind_generation_gwh / demand_2030_gwh

# Within-boundary wind coverage
within_boundary_wind_generation_gwh = within_boundary_wind_capacity_mwp * cf_wind_within * 8760 / 1000
within_boundary_wind_coverage_pct = within_boundary_wind_generation_gwh / demand_2030_gwh
```

**Frontend types to add:**
```ts
max_wind_capacity_mwp?: number;
wind_buildable_area_ha?: number;
max_wind_generation_gwh?: number;
wind_supply_coverage_pct?: number;
within_boundary_wind_capacity_mwp?: number;
within_boundary_wind_coverage_pct?: number;
wind_buildability_constraint?: string;
```

**DemandTab update:** When `energyMode === 'wind'`, show wind-specific supply coverage instead of the current "(Solar-Based)" caveat. When `energyMode === 'overall'`, show both.

#### 1D-5. Wind Temporal Profile

Wind produces power differently than solar (more evenly distributed, peaks at night in many Indonesian coastal locations). This changes the storage/firming story.

**File:** `src/model/basic_model.py`

```python
def firm_wind_metrics(
    wind_generation_mwh: float,
    demand_mwh: float,
    wind_cf: float,
) -> dict:
    """Wind temporal coverage analysis.

    Unlike solar (10h production / 14h gap), wind produces ~24/7 at its CF.
    The gap is intermittency (variability), not day/night.
    Typical wind variability: 70-80% of hours at >50% of average output.
    """
    if demand_mwh <= 0:
        return {"firm_wind_coverage_pct": None, ...}

    # Wind covers demand proportional to CF (no day/night split)
    firm_coverage = min(wind_generation_mwh / demand_mwh, 1.0) * wind_cf / 0.27
    # ... simplified: wind at 27% CF covers ~27% of hours at full output
```

This is a simpler model than solar's temporal analysis. The main message: wind doesn't need 14-hour BESS, it needs shorter-duration firming for intermittency.

#### 1D-6. Scorecard & Frontend Parity

Ensure the scorecard output has the same columns for wind as it does for solar:

| Solar Column | Wind Equivalent | Status |
|-------------|----------------|--------|
| `buildable_area_ha` | `wind_buildable_area_ha` | 1D-2 |
| `max_captive_capacity_mwp` | `max_wind_capacity_mwp` | 1D-2 |
| `solar_supply_coverage_pct` | `wind_supply_coverage_pct` | 1D-4 |
| `within_boundary_coverage_pct` | `within_boundary_wind_coverage_pct` | 1D-2 |
| `firm_solar_coverage_pct` | `firm_wind_coverage_pct` | 1D-5 |
| `storage_gap_pct` | `wind_firming_gap_pct` | 1D-5 |
| `lcoe_within_boundary_usd_mwh` | `lcoe_wind_within_boundary_usd_mwh` | 1D-2 |

**ScoreDrawer updates:**
- Resource tab: show `wind_buildable_area_ha`, `max_wind_capacity_mwp`, `wind_buildability_constraint` in Wind mode
- Demand tab: show wind supply coverage (real, not solar-based caveat) in Wind mode
- Overview tab: show wind capacity + coverage in "At a Glance" section

#### Files to Create/Modify

| File | Action |
|------|--------|
| `src/pipeline/wind_buildability_filters.py` | **NEW** — wind-adapted filter constants + functions |
| `src/pipeline/build_fct_kek_wind_resource.py` | **EXTEND** — add buildability cascade, capacity, within-boundary |
| `src/pipeline/build_wind_buildable_polygons.py` | **NEW** — vectorize wind buildable raster to GeoJSON |
| `src/dash/map_layers.py` | Add `wind_buildable_polygons` layer |
| `src/api/routes/layers.py` | Add `/layers/wind_buildable_polygons` endpoint |
| `src/dash/logic.py` | Add wind supply coverage to `compute_scorecard_live()` |
| `src/dash/data_loader.py` | Load wind buildable columns into `resource_df` |
| `src/model/basic_model.py` | Add `firm_wind_metrics()` |
| `frontend/src/lib/types.ts` | Add wind parity columns to `ScorecardRow` |
| `frontend/src/components/panels/ScoreDrawer.tsx` | Show real wind metrics instead of "(Solar-Based)" caveats |
| `frontend/src/components/map/LayerControl.tsx` | Wind buildable polygons toggle |
| `run_pipeline.py` | Add wind buildability + polygons steps |

#### Sequencing

1. **1D-1 + 1D-2** (pipeline): Wind buildability filters + area/capacity extraction. Can run offline.
2. **1D-3** (pipeline): Wind buildable polygons GeoJSON. Depends on 1D-1.
3. **1D-4** (backend): Wind supply coverage in scorecard. Depends on 1D-2 output columns.
4. **1D-5** (model): Wind temporal metrics. Independent.
5. **1D-6** (frontend): Wire everything to ScoreDrawer/table/map. Depends on 1D-2 through 1D-5.

---

### Phase 2: Hydro Potential Layer (estimated 1 session)

Hydro data exists as GeoJSON with pre-calculated LCOE. No new model needed.

**2a. Load hydro_potential.geojson as map layer**
- `src/dash/map_layers.py` — add `load_hydro_potential()` (pattern: same as nickel/coal layers)
- `src/api/routes/layers.py` — add `/api/layers/hydro` endpoint
- `frontend/src/components/map/VectorOverlay.tsx` — render as blue circles with popup (MW, LCOE, river name)

**2b. Per-KEK hydro summary**
- For each KEK: find hydro projects within 30km (same radius pattern as captive coal/nickel)
- Create `fct_kek_hydro_proximity.csv`: `kek_id`, `hydro_count`, `hydro_total_mw`, `hydro_best_lcoe`, `hydro_projects`
- Add to scorecard merge in `logic.py`

**2c. ScoreDrawer "Hydro Potential" card**
- In Pipeline tab (alongside Captive Power card)
- Show: number of hydro projects nearby, best LCOE, total MW potential
- Key insight: "If hydro at $X/MWh is available, it can cover nighttime demand instead of BESS at $Y/MWh"

**Files touched:** `map_layers.py`, `layers.py`, `VectorOverlay.tsx`, `LayerControl.tsx`, new `build_fct_kek_hydro_proximity.py`, `logic.py`, `ScoreDrawer.tsx`, `types.ts`

### Phase 3: Hybrid RE Scenarios (estimated 2-3 sessions)

This is the big conceptual shift. Instead of "which single RE source wins?", the question becomes "what's the optimal RE mix?"

**3a. Solar + Hydro hybrid LCOE**
- Daytime: solar (cheapest per MWh when sun is shining)
- Nighttime: hydro (firm baseload, no storage needed)
- Eliminates BESS cost entirely for KEKs near hydro
- Formula: `hybrid_lcoe = (solar_lcoe × daytime_share + hydro_lcoe × nighttime_share)`
- This is the killer feature for Sulawesi KEKs (Morowali near hydro potential)

**3b. Solar + Wind complementarity**
- Wind produces at night (offshore/coastal wind peaks in evening)
- Reduces BESS sizing requirement
- Requires hourly production profile data (not available, would need proxy assumptions)

**3c. "Best Available RE Mix" scorecard column**
- For each KEK: compute standalone solar LCOE, standalone wind LCOE, standalone hydro LCOE (if nearby), and hybrid solar+hydro LCOE
- Display the lowest-cost option with breakdown

**3d. EnergyBalanceChart v2: multi-source stacked supply**
- Demand bar: daytime + nighttime
- Supply bar: solar (daytime) + wind (partial) + hydro (firm) + BESS (gap)
- Shows visually how the gap shrinks when you combine sources

**Files touched:** `basic_model.py` (new `hybrid_lcoe()` function), `logic.py`, `build_fct_kek_scorecard.py`, `ScoreDrawer.tsx`, `EnergyBalanceChart.tsx`, `types.ts`

### Phase 4: Geothermal (estimated 1-2 sessions, blocked on data)

**Blocked:** MEMR One Map geothermal prospect data not yet sourced.

**4a. Data sourcing**
- MEMR geothermal prospects GeoJSON/shapefile
- Or: manually compile from EBTKE geothermal database (~200 prospects)
- Need: location, estimated MW, temperature, depth, development stage

**4b. Tech parameters**
- CAPEX: $2,500-4,000/kW (binary cycle, flash)
- FOM: ~$100-150/kW/yr
- CF: 0.70-0.85 (baseload)
- Lifetime: 30-50 years
- No degradation, no storage needed

**4c. Same integration pattern as hydro**
- Map layer → 30km proximity → scorecard card → hybrid LCOE option

---

## How the Dashboard Design Changes

### Phase 1 (done): Solar + Wind comparison
- EnergyMode toggle fully functional: switches table columns, ScoreDrawer metrics, map raster + layers
- "Resource" tab dynamically shows PVOUT or wind speed based on mode
- Economics/Demand/Overview tabs all mode-aware
- Map: PVOUT raster + solar buildable polygons (solar mode) or wind speed raster (wind mode)
- Wind LCOE responds to WACC slider, `best_re_technology` flips dynamically

### After Phase 1D: Wind as first-class citizen
- **Wind buildable polygons on map:** same visual treatment as solar (colored by capacity or wind speed)
- **Real wind supply coverage:** Demand tab shows wind-specific generation vs demand, not "(Solar-Based)" caveats
- **Wind capacity constraints:** `max_wind_capacity_mwp` limits what's buildable (25 ha/MWp spacing)
- **Resource tab parity:** wind mode shows buildable area, capacity, buildability constraint just like solar
- **No analytical shortcuts:** every metric solar has, wind has too

### After Phase 3: Multi-RE decision tool
- **New "RE Mix" section in Overview tab:** shows optimal combination
- **EnergyBalanceChart:** stacked multi-source supply vs demand
- **New action flags or badges:** "Solar+Hydro beats grid" / "Wind competitive here"
- **Table sort by best RE LCOE** (not just solar LCOE)

### Design principles
- Don't add 4 tabs per technology (tab explosion)
- Keep 6-tab structure. Make "Resource" tab technology-aware
- Add "Hydro Potential" and "Geothermal" as cards in Pipeline tab (like Captive Power)
- The hybrid LCOE goes in Economics tab alongside solar LCOE
- EnergyMode toggle drives the whole view, not per-section toggles

---

## Sequencing Recommendation

| Phase | Work | Depends On | Sessions | Status |
|-------|------|------------|----------|--------|
| **1a-c: Activate Wind** | Frontend + live LCOE | Nothing | 3 | ✅ COMPLETE |
| **1D: Wind Analytical Parity** | Buildability, capacity, coverage, polygons | Phase 1 | 2-3 | **NEXT** |
| **2: Hydro Layer** | Pipeline + map + ScoreDrawer card | Nothing (GeoJSON exists) | 1 | Pending |
| **3: Hybrid RE** | New model + scorecard + chart rewrite | Phase 1D + 2 | 2-3 | Pending |
| **4: Geothermal** | Same as Phase 2 pattern | MEMR data sourcing | 1-2 | Blocked on data |

**Phase 1D is the priority.** Wind is visible but analytically thin. Users switching to Wind mode see LCOE and competitive gap but no buildable area, no capacity constraints, no supply coverage, and no buildable polygons on the map. This makes wind look like a second-class citizen. Phase 1D fixes that.

Phase 2 (hydro) can run in parallel since it's an independent GeoJSON pipeline.

**Total estimated:** 7-10 sessions for Phases 1D through 3. Phase 4 blocked on data.

---

## Verification per Phase

**Phase 1 (complete):**
- ✅ EnergyMode toggle switches table columns, ScoreDrawer metrics, map layers
- ✅ Wind LCOE visible and responsive to WACC slider for all 25 KEKs
- ✅ `best_re_technology` live-computed, flips between solar/wind as WACC changes
- ✅ `npx tsc --noEmit` clean, `npm run lint` clean, 402 tests pass

**Phase 1D:**
- Wind buildable polygons visible on map in Wind mode (replaces solar polygons)
- Resource tab shows `wind_buildable_area_ha` and `max_wind_capacity_mwp` in Wind mode
- Demand tab shows real wind supply coverage (not "Solar-Based" caveat)
- Wind capacity is constrained (not infinite) in scorecard
- `uv run pytest tests/` passes with new wind buildability tests
- Spot-check: KEK with large buildable solar area but poor wind → low `max_wind_capacity_mwp`

**Phase 2:**
- Hydro layer renders on map with popups
- ScoreDrawer shows hydro proximity card for KEKs near hydro projects
- Pipeline test: `uv run pytest tests/` passes

**Phase 3:**
- Hybrid LCOE computed for KEKs with nearby hydro
- EnergyBalanceChart shows multi-source supply
- Morowali/Konawe show dramatically lower hybrid LCOE vs solar-only
