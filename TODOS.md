# TODOs — Indonesia KEK Power Competitiveness Dashboard

Consolidated deferred items from [PLAN.md](PLAN.md), [PERSONAS.md](PERSONAS.md), [gap analysis](docs/gap_analysis_existing_vs_conversation_spec.md), and methodology/persona audit.
Last updated: 2026-04-12 (within-boundary buildable overlay, light mode theme, stale items cleaned).

**Related:** [PLAN.md](PLAN.md) | [PERSONAS.md](PERSONAS.md) | [DESIGN.md](DESIGN.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | [docs/METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) | [docs/USER_JOURNEYS.md](docs/USER_JOURNEYS.md)

---

## Quick-Win Priority (docs only, no code)

Items from the gap analysis that are documentation additions or trivial column derivations.

| # | Item | Source | Files | Status |
|---|------|--------|-------|--------|
| ~~Q1~~ | ~~**Indonesia transmission corridor context note**~~ | Gap analysis P0 | `METHODOLOGY_CONSOLIDATED.md` §8.3 | ✅ Done (2026-04-11) — added Norton Rose Fulbright 20-40km context and $5/kW-km → $/km translation. |
| ~~Q2~~ | ~~**Gen-tie cost unit translation note**~~ | Gap analysis P0 | `METHODOLOGY_CONSOLIDATED.md` §6.2 | ✅ Done (2026-04-11) — example: 25 MW at 5 km = $2.625M total = ~$0.5M/km. |
| ~~Q3~~ | ~~**Build vs. buy wheeling note for Tenant persona**~~ | Gap analysis P0 | `PERSONAS.md` P5 | ✅ Done (2026-04-11) — forward-looking wheeling note added. |
| ~~Q4~~ | ~~**`grid_investment_needed_usd` as first-class column**~~ | Gap analysis P0, PERSONAS.md P2 | `build_fct_kek_scorecard.py`, `logic.py`, `types.ts` | ✅ Done (2026-04-11) — `(connection_cost_per_kw + transmission_cost_per_kw) x max_captive_capacity_mwp x 1000`. 18/25 KEKs have values ($8M to $2.4B). |

---

## Medium Priority (v1.2)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| M1 | **Grid emission factor update** | PERSONAS.md gap 5 | P1, P3 | KESDM 2019 Tier 2 OM → 2023 KESDM or IEA SEA 2024 data. Affects `carbon_breakeven_usd_tco2` accuracy (7 years stale). |
| M2 | **Road proximity layer (Layer 3a)** | PERSONAS.md gap 8 | P2, P4 | OSM PBF processing → `dist_to_nearest_road_km`. Construction access cost proxy. |
| M3 | **CAPEX market comparables** | PERSONAS.md P1 gaps | P1 | 2023-2024 Indonesia solar EPC tender data. ESDM catalogue ($960/kW) may be +/-15-20% from market. |
| M4 | **KEK operational status enrichment** | PERSONAS.md gap 7 | P4 | Distinguish operating (tenants present) vs. greenfield. Requires BKPM/KEK management data. |
| ~~M5~~ | ~~**Custom CAPEX input for IPP**~~ | PERSONAS.md P4 audit | P4 | ✅ Done (2026-04-11) — `CapexInput.tsx` free-text input with slider, validates range, tab/enter commit. |
| ~~M6~~ | ~~**Configurable assumptions — Phase D (UX polish)**~~ | DESIGN.md §3 | All | ✅ Done (2026-04-11) — URL state persistence (`urlState.ts`, `useUrlSync.ts`), "Modified" badge, reset-to-defaults. |
| M7 | **Scenario save/compare** | Methodology audit | All | Save up to 3 named assumption sets, compare side-by-side. Zustand persist + local storage. |
| M8 | **Floating solar modelling** | User obs (2026-04-08) | P2, P4 | Water bodies excluded from buildable area. Floating PV on reservoirs/lagoons could unlock capacity for land-constrained KEKs. CAPEX ~20-30% higher ($1,100-1,400/kW). Requires new siting scenario. |
| M9 | **Raster overlay bounds expansion** | UI bug (2026-04-09) | All | Raster overlays clip when map is pitched (3D terrain). Backend `map_layers.py` bounding box needs padding (+/-5 deg). Workaround: auto-pitch only at zoom > 7. |
| M10 | **Substation-name-to-line-name matching** | V3.1 deferred | All | Grid line names encode endpoints but naming is inconsistent. Geometric check is more reliable. Nice-to-have refinement. |
| M11 | **Night-time light proxy for utilization** | V3.1 deferred | P2 | VIIRS/DMSP satellite data as proxy for substation load. Improves `capacity_assessment` vs. fixed 65% assumption. |
| M12 | **Substation upgrade cost in LCOE** | Gap analysis P1, V3.1 deferred | P2, P3 | When `capacity_assessment == "red"`, fold parametric upgrade cost (capacity_gap_mva x $/MVA) into grid-connected LCOE. Turns qualitative flag into quantitative impact. |
| M13 | **Sub-pixel buildable fraction from ESA WorldCover** | Buildability review (2026-04-10) | P2 | Current `Resampling.mode` at 10m→1km loses sub-pixel detail. Replace with binary-threshold + average resampling at 50%. |
| ~~M14~~ | ~~**Buildable land polygons (in-boundary + remote)**~~ | Gap analysis P1 | P2, P4 | ✅ **Done (2026-04-12):** Remote/50km buildable polygons live as "Solar Buildable Areas" layer with clickable popups. Within-boundary polygons clipped to KEK boundary via `/api/kek/{id}/buildable` endpoint (`get_within_boundary_buildable` in `map_layers.py`). Displayed as green overlay on KEK zoom. Area capped at KEK polygon area to prevent raster pixel inflation. |
| M15 | **Multi-substation comparison** | Gap analysis P2 | P4 | Evaluate top 3 substations within search radius. Compare total interconnection cost: closer-but-constrained vs. farther-but-available. Medium priority, becomes important for investment-grade analysis. |
| M16 | **Capacity slider with LCOE curve** | Gap analysis P1 | P4 | Slider for "desired build capacity" (10 MW to max). Shows how LCOE changes with scale: fixed costs dominate at small sizes, grid constraints push cost up at large sizes. High value for IPP "how big should I build?" question. |

---

## Low Priority (v2.0)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| L1 | **Datasette REST API** | PLAN.md CEO review | All | Mirror processed CSVs via REST API for programmatic access. |
| L2 | **SAIDI/SAIFI reliability indicators** | PLAN.md CEO review | P3 | Replace hardcoded `reliability_req` with PLN SAIDI/SAIFI by grid system. Strengthens `invest_resilience` flag. |
| L3 | **Flood hazard layer (Layer 2d)** | PERSONAS.md gap 9 | P2 | BNPB portal inaccessible. Low incremental value over slope layer. Blocked on data access. |
| L4 | **Excel/PDF export pipeline** | Autoplan CEO subagent | All | Formatted Excel workbook with charts + PDF scorecard per KEK. |
| L5 | **Multilingual (EN/ID)** | — | P3 | Indonesian language option for BKPM/KESDM officials. |
| ~~L6~~ | ~~**Mapbox basemap upgrade from Carto**~~ | DESIGN.md §6 Q2 | All | ❌ Won't do — MapLibre can't resolve `mapbox://` protocol URLs in style JSON. `transformRequest` workaround attempted but unreliable. Carto Dark Matter is the dark basemap. |
| L7 | **Mobile responsive layout** | DESIGN.md §6 Q3 | All | Primary users are analysts with laptops. |
| L8 | **KEK Management persona (P6)** | Methodology/persona audit | — | Zone administrators (BKPM-appointed) who use the tool to attract tenants. |
| L9 | **Carbon price trajectory modelling** | PERSONAS.md P3 gaps | P3 | Link `carbon_breakeven_usd_tco2` to Indonesia ETS trajectory. |
| L10 | **Spatial story / SEZ-anchored map view** | Gap analysis P2 | P3 | Start from KEK, radiate outward to show solar, color-code by gap type. More of a UX change than data model. Backend data already supports this. |

---

## Completed

### V2 Pivot (all complete)

The remote captive solar thesis was replaced with a grid-connected solar model. All 8 backend items (V2-B1 through V2-B8), 6 frontend items (V2-F1 through V2-F6), and 5 documentation items (V2-D1 through V2-D5) are done. See [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) for the final methodology.

### High Priority items (all complete)

H1 Wind CF pipeline, H2 BPP data sourcing, H3 Land cover buildability, H4 Infrastructure cost sliders, H5 Flag threshold sliders — all done.

### Feature completions

| # | Item | Date | Notes |
|---|------|------|-------|
| ✅ | React + Vite migration | 2026-04-08 | Full Dash → React. FastAPI backend, Vite SPA, MapLibre, TanStack Table, Recharts, Zustand. |
| ✅ | Wind CF pipeline | 2026-04-08 | `build_fct_kek_wind_resource.py`, EnergyToggle, wind raster layer, `best_re_technology`. |
| ✅ | BPP data sourcing | 2026-04-07 | Kepmen ESDM 169/2021 (FY2020). 7 grid regions. `pdf_extract_bpp.py`. |
| ✅ | Land cover buildability | 2026-04-07 | KLHK 66K polygons + peatland 1,524 features. All 4 layers active. |
| ✅ | Configurable assumptions (A/B/C) | 2026-04-07/08 | 3-tier slider system, benchmark toggle, reset-to-defaults. |
| ✅ | Persona walkthrough tour | 2026-04-09 | 4 personas x 8 steps, spotlight overlay, Guide button. |
| ✅ | 3D terrain rendering | 2026-04-09 | Mapbox terrain-rgb DEM, auto-pitch at zoom >= 7. |
| ✅ | V3.1 grid infrastructure | 2026-04-10 | Grid line connectivity (1,595 lines), capacity traffic light, action flag split, threshold tightening. |
| ✅ | Buildability circular mask | 2026-04-10 | Haversine mask replaces bounding box. `best_solar_site_dist_km` column. |
| ✅ | Methodology consolidation | 2026-04-11 | Merged METHODOLOGY.md + METHODOLOGY_V2.md + methodology_testing.md → single METHODOLOGY_CONSOLIDATED.md. |
| ✅ | PERSONAS.md V3.1 update | 2026-04-11 | Readiness scores, stale references, flag names, data gaps all updated. |
| ✅ | USER_JOURNEYS.md | 2026-04-11 | Standalone user journey doc mapped to actual UI components. |
| ✅ | Gap analysis integration | 2026-04-11 | P0 doc additions (transmission corridor context, gen-tie cost translation, tenant wheeling note). Deferred items added to methodology with TODOS.md cross-references. |
| ✅ | Methodology archival | 2026-04-12 | Archived METHODOLOGY.md (v0.4), METHODOLOGY_V2.md (draft), methodology_testing.md → `docs/archives/`. METHODOLOGY_CONSOLIDATED.md is now the single canonical reference. All doc links updated. |
| ✅ | Remove raster buildable layer | 2026-04-12 | Removed coarse raster "Solar Buildable Area" from frontend + API. Polygon layer renamed to "Solar Buildable Areas". Clickable popups added. |
| ✅ | Fix within-boundary 20% fallback | 2026-04-12 | Theoretical fallback zeroed: KEKs with no spatial buildable pixels report 0 area/capacity instead of fake 10% estimate. |
| ✅ | Within-boundary buildable overlay | 2026-04-12 | `/api/kek/{id}/buildable` clips buildable polygons to KEK boundary with 220m buffer. Green fill overlay on map. Area capped at KEK polygon area to prevent raster inflation. |
| ✅ | Light mode theme system | 2026-04-12 | 15+ CSS custom properties for theme-aware styling. All components migrated from hardcoded dark colors to `var(--*)`. Light mode glass opacity, contrast, and popup theming. LayerControl moved to header dropdown. |

---

## Dashboard Caveats (document only, no code fix)

These are data limitations. The dashboard should display clear labels/tooltips for each.

| # | Caveat | Display treatment | Source |
|---|--------|------------------|--------|
| C1 | `demand_mwh_2030` is area x intensity proxy | Tooltip: "Estimated from KEK area x industrial intensity. Not suitable for PPA sizing; field surveys required." | PERSONAS.md P4 data gaps |
| C2 | GEAS pro-rata allocation is indicative | Label: "Indicative GEAS allocation, not contractual. Actual allocation depends on PLN tender design." | PERSONAS.md P3 data gaps |
| C3 | Substation capacity nulls (6/25 KEKs) | Display "—" with tooltip: "Capacity not recorded by PLN" | PERSONAS.md P2 data gaps |
| C4 | `reliability_req` is type-based proxy | Label on `invest_resilience` flag: "Based on KEK type (manufacturing=0.8, tourism=0.4), pending PLN SAIDI/SAIFI data" | PERSONAS.md P3 data gaps |
| C5 | Panel degradation not modeled | Tooltip on LCOE values: "Screening-level LCOE; does not include ~0.5%/yr panel degradation (~6-7% understatement). Standard for IEA/IRENA screening models." | Methodology audit F7 |
| C6 | Carbon breakeven excludes solar lifecycle emissions | Tooltip on carbon breakeven: "Assumes zero solar lifecycle emissions. Actual ~40 gCO2/MWh (IPCC AR6). Breakeven ~5-8% optimistic." | Methodology audit F9 |
| C7 | IDR/USD rate hardcoded | Tooltip on grid cost: "Grid cost converted at 15,800 IDR/USD (2024). A 5% FX move changes grid cost by ~$3/MWh." | Methodology audit F10 |
