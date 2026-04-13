# Multi-RE Integration: Solar + Wind + Hydro + Geothermal

## Context

The dashboard currently shows solar LCOE for 25 Indonesian KEKs. But for several KEKs (Morowali, Konawe in Sulawesi; Sei Mangkei in Sumatra), solar alone can't beat grid cost. Hydro or geothermal might. And even where solar wins on daytime LCOE, combining it with hydro or wind could eliminate the BESS cost entirely, since those sources can cover nighttime demand.

The user wants a plan for evolving from a solar-only tool to a "best renewable energy source" decision tool.

---

## What Already Exists (surprisingly a lot)

### Wind: 90% built, needs frontend wiring

| Component | Status | Location |
|-----------|--------|----------|
| Wind speed raster (Global Wind Atlas v3, 100m) | ✅ Built | `data/wind/IDN_wind-speed_100m.tif` |
| Wind CF lookup (speed → CF, piecewise linear) | ✅ Built | `basic_model.py:123-176`, `wind_speed_to_cf()` |
| Wind LCOE precomputed (25 KEKs × 9 WACC × 2 scenarios) | ✅ Built | `build_fct_lcoe_wind.py`, reuses `lcoe_solar()` |
| Wind tech cost (ESDM 2024, $1,650/kW, 40 FOM, 27yr) | ✅ Built | `build_dim_tech_cost_wind.py` |
| `best_re_technology` selection (solar vs wind) | ✅ Built | `build_fct_kek_scorecard.py:317-345` |
| Wind raster map layer | ✅ Built | `map_layers.py:454-487`, `RasterOverlay.tsx` |
| EnergyMode toggle (Solar/Wind/Overall) | ✅ UI built | `EnergyToggle.tsx`, store tracks state |
| **Toggle wiring to data/display** | ❌ Not built | Toggle does nothing. No filtering, no column switching |
| **Wind columns in ScoreDrawer** | ❌ Not built | `cf_wind`, `lcoe_wind_mid`, `wind_speed_ms` returned by API but not displayed |
| **Wind in table columns** | ❌ Not built | Only `best_re_technology` shown, no wind CF or wind LCOE columns |

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

### Phase 1: Activate Wind (estimated 1-2 sessions)

Wind data and LCOE are fully computed. This is purely a frontend integration job.

**1a. Wire the EnergyMode toggle**
- `frontend/src/store/dashboard.ts` — `energyMode` already stored
- When `energyMode = 'wind'`: show wind columns in table, wind metrics in ScoreDrawer
- When `energyMode = 'overall'`: show `best_re_technology` and best LCOE across both

**1b. Add wind fields to ScorecardRow type**
- `frontend/src/lib/types.ts` — add `lcoe_wind_mid_usd_mwh`, `cf_wind`, `wind_speed_ms`, `wind_class`
- These are already returned by the API but TypeScript doesn't know about them

**1c. ScoreDrawer "Solar" tab → "Resource" tab**
- Rename tab. When solar mode: show PVOUT, solar CF, buildable area
- When wind mode: show wind speed, wind CF, wind class
- When overall: show both side-by-side or show best RE

**1d. Table columns respond to energyMode**
- `columns.tsx` — show `lcoe_mid_usd_mwh` (solar) or `lcoe_wind_mid_usd_mwh` (wind) based on toggle
- Or: always show both, highlight the better one

**1e. EnergyBalanceChart multi-source**
- Currently hardcoded to 10h solar / 14h gap
- Wind has different production profile (more even, ~30-40% CF round-the-clock)
- Show: "Solar covers X% daytime + Wind covers Y% baseload" when overall mode

**Files touched:** `types.ts`, `ScoreDrawer.tsx`, `columns.tsx`, `DataTable.tsx`, `EnergyBalanceChart.tsx`, `dashboard.ts`
**No backend changes needed.** Data already flows through API.

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

### Current: Solar-only tool
- Header: Solar/Wind/Overall toggle (non-functional)
- ScoreDrawer: 6 tabs, all solar-centric
- Table: solar LCOE, solar gap %, solar coverage
- Map: solar PVOUT raster, solar buildable areas

### After Phase 1: Solar + Wind comparison
- **EnergyMode toggle becomes functional:** switching between Solar/Wind/Overall changes table columns, ScoreDrawer metrics, and map raster
- **"Solar" tab → "Resource" tab:** dynamically shows PVOUT or wind speed based on mode
- **Table:** conditional columns per mode, or dual-column layout
- **Map:** PVOUT raster (solar mode) or wind speed raster (wind mode)

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

| Phase | Work | Depends On | Sessions |
|-------|------|------------|----------|
| **1: Activate Wind** | Frontend only, wire toggle | Nothing (data exists) | 1-2 |
| **2: Hydro Layer** | Pipeline + map + ScoreDrawer card | Nothing (GeoJSON exists) | 1 |
| **3: Hybrid RE** | New model + scorecard + chart rewrite | Phase 1 + 2 | 2-3 |
| **4: Geothermal** | Same as Phase 2 pattern | MEMR data sourcing | 1-2 (blocked) |

**Start with Phase 1** because it's zero backend work and makes the existing wind data visible. Phase 2 can run in parallel (independent pipeline). Phase 3 is the high-value integration that combines them.

**Total estimated:** 5-8 sessions for Phases 1-3. Phase 4 blocked on data.

---

## Verification per Phase

**Phase 1:**
- EnergyMode toggle switches table columns and ScoreDrawer metrics
- Wind LCOE visible for all 25 KEKs
- `best_re_technology` filter works in table
- `npx tsc --noEmit` clean, `npm run lint` clean

**Phase 2:**
- Hydro layer renders on map with popups
- ScoreDrawer shows hydro proximity card for KEKs near hydro projects
- Pipeline test: `uv run pytest tests/` passes

**Phase 3:**
- Hybrid LCOE computed for KEKs with nearby hydro
- EnergyBalanceChart shows multi-source supply
- Morowali/Konawe show dramatically lower hybrid LCOE vs solar-only
