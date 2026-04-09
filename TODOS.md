# TODOs — Indonesia KEK Power Competitiveness Dashboard

Consolidated deferred items from [PLAN.md](PLAN.md), [PERSONAS.md](PERSONAS.md), Phase 3 autoplan review, and methodology/persona audit.
Last updated: 2026-04-09.

**Related:** [PLAN.md](PLAN.md) | [PERSONAS.md](PERSONAS.md) | [DESIGN.md](DESIGN.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

---

## High Priority (v1.1)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| ~~H1~~ | ~~**Wind CF pipeline integration**~~ | ~~PLAN.md decision #19~~ | ~~P3~~ | ✅ Complete — see Completed table below |
| ~~H2~~ | ~~**BPP data sourcing**~~ | ~~PERSONAS.md gap priority 4~~ | ~~P1~~ | ✅ Complete — see Completed table below |
| ~~H3~~ | ~~**Land cover buildability refinement**~~ | ~~PLAN.md Phase 2 deferred~~ | ~~P2, P4~~ | ✅ Complete — see Completed table below |
| ~~H4~~ | ~~**Configurable assumptions — Phase B (infrastructure costs)**~~ | ~~DESIGN.md §3, decision #34~~ | ~~P2, P4~~ | ✅ Complete — see Completed table below |
| ~~H5~~ | ~~**Configurable assumptions — Phase C (flag thresholds)**~~ | ~~DESIGN.md §3, decision #34~~ | ~~P3~~ | ✅ Complete — see Completed table below |

---

## Medium Priority (v1.2)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| M1 | **Grid emission factor update** | PERSONAS.md gap priority 5 | P1, P3 | KESDM 2019 Tier 2 OM → 2023 KESDM or IEA SEA 2024 data. Affects `carbon_breakeven_usd_tco2` accuracy. See [METHODOLOGY.md §4](METHODOLOGY.md) for current emission factor methodology. |
| M2 | **Road proximity layer (Layer 3a)** | PERSONAS.md gap priority 8 | P2, P4 | OSM PBF processing → `dist_to_nearest_road_km`. Construction access cost proxy for remote captive sites. |
| M3 | **CAPEX market comparables** | PERSONAS.md P1 data gaps | P1 | 2023–2024 Indonesia solar EPC tender data. ESDM catalogue value ($960/kW) may be ±15–20% from market reality. |
| M4 | **KEK operational status enrichment** | PERSONAS.md gap priority 7 | P4 | Distinguish operating (tenants present) vs. greenfield KEKs. Requires BKPM/KEK management data sourcing. |
| M5 | **Custom CAPEX input for IPP** | PERSONAS.md P4 audit finding | P4 | Slider exists ($600–1,500/kW). Still needs free-text input for exact $/kW. Workaround: export CSV with CF values and recompute in own model. |
| M6 | **Configurable assumptions — Phase D (UX polish)** | DESIGN.md §3, decision #34 | All | Reset-to-defaults ✅ done. Still TODO: URL state persistence (`?capex=840&wacc=8`), "scenario changed" badge, export-with-assumptions metadata. |
| M7 | **Scenario save/compare** | Methodology audit | All | Save up to 3 named assumption sets and compare side-by-side. Requires Zustand persist + local storage. |
| M8 | **Floating solar modelling** | User observation (2026-04-08) | P2, P4 | Current model excludes water bodies (ESA WorldCover code 80) from buildable area. Floating PV on reservoirs, coastal lagoons, and nearshore waters could unlock viable capacity for land-constrained KEKs (e.g., Bali's Sanur/Kura Kura show ~1,000 ha buildable but fragmented). Floating solar CAPEX is ~20-30% higher than ground-mount ($1,100-1,400/kW vs $960/kW). Requires: (1) identify water bodies within 50km of each KEK, (2) add floating solar CAPEX assumption, (3) new `siting_scenario: floating` in `fct_lcoe`, (4) update buildability filters to include water surfaces as a separate category. |

---

## Low Priority (v2.0)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| L1 | **Datasette REST API** | PLAN.md CEO review | All | Mirror processed CSVs via REST API for programmatic access. New infrastructure dependency. |
| L2 | **SAIDI/SAIFI reliability indicators** | PLAN.md CEO review | P3 | Replace hardcoded `reliability_req` with PLN SAIDI/SAIFI by grid system. Strengthens `invest_resilience` flag credibility. |
| L3 | **Flood hazard layer (Layer 2d)** | PERSONAS.md gap priority 9 | P2 | BNPB portal inaccessible. Low incremental value over existing slope exclusion layer. Blocked on data access. |
| L4 | **Excel/PDF export pipeline** | Autoplan CEO subagent | All | Beyond CSV + GeoJSON: formatted Excel workbook with embedded charts and PDF scorecard per KEK. Distribution format for analysts who won't bookmark a Dash URL. |
| L5 | **Multilingual (EN/ID)** | — | P3 | Indonesian language option for BKPM/KESDM officials. Adds i18n complexity. |
| L6 | **Mapbox basemap upgrade from Carto** | DESIGN.md §6 Q2 | All | Currently using Carto dark-matter tiles. Mapbox token exists (used for 3D terrain DEM) but basemap still Carto. Prettier tiles but adds dependency. |
| L7 | **Mobile responsive layout** | DESIGN.md §6 Q3 | All | Primary users are analysts with laptops. Mobile adds CSS complexity. Deferred from MVP. |
| L8 | **KEK Management persona (P5)** | Methodology/persona audit | — | Zone administrators (BKPM-appointed) who use the tool to attract tenants. Distinct journey from P1–P4. Good v2.0 addition. |
| L9 | **Carbon price trajectory modelling** | PERSONAS.md P3 data gaps | P3 | Link `carbon_breakeven_usd_tco2` to Indonesia's ETS trajectory (Article 6 commitments, IDR carbon market). Policy makers need: "at projected carbon price path, when does solar win?" |

---

## Completed

| # | Item | Date | Notes |
|---|------|------|-------|
| ✅ H2 | **BPP data sourcing** | 2026-04-07 | Regional BPP Pembangkitan from Kepmen ESDM 169/2021 (FY2020). `bpp_usd_mwh` populated for all 7 grid regions via `pdf_extract_bpp.py`. Java-Bali ~$57/MWh, Papua ~$133/MWh. 10 BPP tests added. |
| ✅ H3 | **Land cover buildability refinement** | 2026-04-07 | Upgraded kawasan hutan to full KLHK 66K-polygon shapefile (555MB). Integrated KLHK peatland vector boundaries (1,524 features). All 4 buildability layers now active. 7/25 KEKs show zero buildable area. |
| ✅ | **Configurable assumptions — Phase A (core LCOE controls)** | 2026-04-07 | `src/dash/logic.py` created: `UserAssumptions`, `UserThresholds`, `compute_lcoe_live()`, `compute_scorecard_live()`. 22 tests passing. CAPEX slider + Lifetime slider ready for Dash wiring. |
| ✅ | **Methodology expert review** | 2026-04-07 | 10 fixes applied to METHODOLOGY.md: stale WACC range, buildability caveats, slope threshold, degradation note, GSA temperature de-rating, carbon lifecycle emissions, FX sensitivity. |
| ✅ | **Personas expert review** | 2026-04-07 | P3 solar-only caveat added, P4 custom CAPEX note added. `solar_now_at_wacc8` column verified in scorecard CSV. |
| ✅ | **DESIGN.md configurable assumptions spec** | 2026-04-07 | Decision #34: 3-tier slider controls, hybrid precomputed/live architecture, callback diagram, component choices for 16 controls. |
| ✅ | **React + Vite migration (Lanes A-E)** | 2026-04-08 | Full Dash → React migration. FastAPI backend (7 endpoints), Vite + React 18 SPA, MapLibre map, TanStack Table, Recharts, Zustand store. All features at parity. |
| ✅ | **Raster layer color legends** | 2026-04-08 | Gradient legend strips for PVOUT (YlOrRd), Wind (Blues), Buildable (YlGn) when layers toggled on. Draggable, includes 50km radius legend. |
| ✅ | **Methodology modal with KaTeX** | 2026-04-08 | METHODOLOGY.md rendered in-app via react-markdown + KaTeX. Anchor links scroll within modal. All formulas converted to LaTeX notation. |
| ✅ | **Biome formatter** | 2026-04-08 | Biome added as pre-commit hook for TypeScript/React formatting and linting. `npm run lint` / `npm run format` scripts. |
| ✅ | **Liquid glass UI** | 2026-04-08 | Header bar, Back to National View button use backdrop-filter glass styling. Map is full-screen with overlaying UI. |
| ✅ | **Draggable panels** | 2026-04-08 | Assumptions, Layer Control, Raster Legends all movable via `useDraggable` hook. |
| ✅ | **50km radius circle** | 2026-04-08 | GeoJSON circle renders on map when KEK selected. Stays visible when drawer closed (only clears on Back to National View). |
| ✅ | **Buildable area fragmentation warning** | 2026-04-08 | Amber warning in ScoreDrawer Resource tab for KEKs with <2,000 ha buildable area. |
| ✅ H1 | **Wind CF pipeline integration** | 2026-04-08 | Full wind pipeline: `build_fct_kek_wind_resource.py` → `cf_wind_centroid`, `cf_wind_best_50km`, `wind_class`. EnergyToggle (Solar/Wind/Overall) in frontend. Wind speed raster layer with legend. `best_re_technology` column shows wind where applicable. |
| ✅ H4 | **Configurable assumptions — Phase B (infrastructure costs)** | 2026-04-08 | All 6 sliders in tier2 accordion: FOM, gen-tie, substation, transmission lease, firming adder, IDR/USD rate. Live recomputation via `compute_scorecard_live()`. |
| ✅ H5 | **Configurable assumptions — Phase C (flag thresholds)** | 2026-04-08 | All 6 thresholds in tier3 accordion: PVOUT threshold, plan-late %, GEAS %, resilience gap %, min viable MWp, reliability threshold. Action flags recompute live. |
| ✅ | **Infrastructure typed icons** | 2026-04-09 | Replaced generic green circles with 9 typed SVG icons (airport, port, road, railway, power, water, telecom, facility, other). Substations use lightning bolt icons (blue=nearby, yellow=nearest). |
| ✅ | **Persona-based walkthrough tour** | 2026-04-09 | 4 persona cards on first load, 8-step spotlight tour per persona. Steps drive UI (switch tabs, select KEK). Guide button in header to re-launch. |
| ✅ | **3D terrain rendering** | 2026-04-09 | Mapbox terrain-rgb DEM tiles via MapLibre `setTerrain()`. Toggle in layer control. Auto-pitches to 50° when enabled. |
| ✅ | **Capacity (MWp) column** | 2026-04-09 | `max_captive_capacity_mwp` column in ranked table, sortable. |
| ✅ | **Column filters (dropdown + range)** | 2026-04-09 | Dropdown filters for categorical columns, min/max range filters for numeric columns. Filter toggle with count badge and clear-all. |
| ✅ | **Column header tooltips** | 2026-04-09 | Info icon (?) on every column header with hover tooltip explaining the column. Action flag cells show contextual explanation of why that flag was assigned. |
| ✅ | **Benchmark-aware grid rate column** | 2026-04-09 | Grid Rate column switches between BPP and Tariff based on benchmarkMode toggle. Scorecard recomputes on toggle. |

---

## Dashboard Caveats (document only, no code fix)

These are data limitations. The dashboard should display clear labels/tooltips for each.

| # | Caveat | Display treatment | Source |
|---|--------|------------------|--------|
| C1 | `demand_mwh_2030` is area x intensity proxy | Tooltip: "Estimated from KEK area x industrial intensity. Not suitable for PPA sizing; field surveys required." | PERSONAS.md P4 data gaps |
| C2 | GEAS pro-rata allocation is indicative | Label: "Indicative GEAS allocation, not contractual. Actual allocation depends on PLN tender design." | PERSONAS.md P3 data gaps |
| C3 | Substation capacity nulls (5/25 KEKs) | Display "—" with tooltip: "Capacity not recorded by PLN" | PERSONAS.md P2 data gaps |
| C4 | `reliability_req` is type-based proxy | Label on `invest_resilience` flag: "Based on KEK type (manufacturing=0.8, tourism=0.4), pending PLN SAIDI/SAIFI data" | PERSONAS.md P3 data gaps |
| C5 | Panel degradation not modeled | Tooltip on LCOE values: "Screening-level LCOE; does not include ~0.5%/yr panel degradation (~6–7% understatement). Standard for IEA/IRENA screening models." | Methodology audit F7 |
| C6 | Carbon breakeven excludes solar lifecycle emissions | Tooltip on carbon breakeven: "Assumes zero solar lifecycle emissions. Actual ~40 gCO2/MWh (IPCC AR6). Breakeven ~5–8% optimistic." | Methodology audit F9 |
| C7 | IDR/USD rate hardcoded | Tooltip on grid cost: "Grid cost converted at 15,800 IDR/USD (2024). A 5% FX move changes grid cost by ~$3/MWh." | Methodology audit F10 |
