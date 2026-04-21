# Design — Indonesia Industrial Decarbonization Dashboard

**Status:** V3.7 design spec (2026-04-21). React + Vite + TypeScript SPA with FastAPI backend. 81 sites (25 KEK + 46 standalone + 10 cluster), 2D classification, 4 energy modes, 14 map layers, CBAM Layer 3, Scenario Compare.
**Related:** [PERSONAS.md](PERSONAS.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [PLAN.md](PLAN.md) | [TAXONOMY.md](docs/TAXONOMY.md) (cost-column names & tiers) | [Layer 3 Spec](docs/layer3_green_industrial_products_spec.md)
**Design mockups:** [docs/designs/2026-04-dashboard-refresh/](docs/designs/2026-04-dashboard-refresh/) (4 interaction states + 3 exploration variants)

---

## Table of Contents

- [§1 Problem Statement](#1-problem-statement)
- [§2 Information Architecture](#2-information-architecture)
- [§3 Component Architecture](#3-component-architecture)
  - [State management](#state-management)
  - [Data flow](#data-flow)
  - [Component choices](#component-choices)
- [§4 Colour & Visual Language](#4-colour--visual-language)
  - [Action flag colours](#action-flag-colours)
  - [Data quality indicators](#data-quality-indicators)
  - [Quadrant zones](#quadrant-zones)
- [§5 Data Decisions for the UI](#5-data-decisions-for-the-ui)
  - [What is precomputed vs. computed live](#what-is-precomputed-vs-computed-live)
  - [WACC slider behaviour](#wacc-slider-behaviour)
  - [Demand override hook](#demand-override-hook)
- [§6 Resolved Design Questions (Phase 3)](#6-resolved-design-questions-phase-3)
- [§7 CBAM / Green Industrial Products (Layer 3)](#7-cbam--green-industrial-products-layer-3)
- [§8 Architecture Notes](#8-architecture-notes)
- [§9 Changelog](#9-changelog)

---

## §1 Problem Statement

Indonesia's industrial sector faces a fragmented energy market: captive solar and wind may already be cheaper than grid power at many sites, but no single tool shows which locations are competitive today, which are one policy lever away, and which are genuinely grid-dependent — or which are exposed to EU CBAM carbon costs. This dashboard answers that question across **81 industrial sites** (25 KEKs + 32 cement plants + 7 steel plants + 10 nickel IIA clusters + 2 aluminium + 5 fertilizer) for the five audiences who most need it — energy economists, DFI investors, Indonesian policymakers, IPP developers, and CBAM-exposed industrial investors — using precomputed LCOE bands, buildable solar/wind resource estimates, RUPTL pipeline data, and EU CBAM exposure joined at site level for the first time.

---

## §2 Information Architecture

Five named views arranged in a **map-forward layout**. The map is always visible. Other views appear as overlays (right panel, bottom drawer).

| # | View | Container | Purpose | Primary data source | Key interaction |
|---|------|-----------|---------|-------------------|----------------|
| 1 | **Overview Map** | Full-screen (always visible) | Spatial distribution of clean power competitiveness across all 81 sites. 14 toggle-able overlay layers. | `scorecard[].action_flag`, 4 energy modes | Click marker → zoom to site + show ScoreDrawer |
| 2 | **Ranked Table** | Bottom drawer (tab 1) | Sortable, filterable comparison of all 81 sites. 20 columns (delivered cost hidden when `captive_fraction == 0`), dropdown + range filters, CBAM toggle, CSV export. | `POST /api/scorecard` response | Column sort; global search; CBAM filter; CSV export |
| 3 | **Quadrant Chart** | Bottom drawer (tab 2) | LCOE vs. grid cost proxy scatter with competitive zone shading | Scorecard LCOE + grid cost | Benchmark toggle (BPP / Tariff) |
| 4 | **Site ScoreDrawer** | Right side panel (slides in on site click) | Single-site deep-dive: 7 tabs with embedded charts (EnergyBalance, LcoeCurve, CbamTrajectory, SubstationComparison) | All scorecard fields for selected site | Tab between Overview / Resource / Grid / Economics / Industry / Action / Flip |
| 5 | **RUPTL Context** | Bottom drawer (tab 3) | Regional grid pipeline timing — when does PLN's solar come online near each site? | `GET /api/ruptl-metrics` | Region filter; scenario toggle (RE Base / ARED) |

### Layout containers

```
┌─────────────────────────────────────────────────────────────────┐
│  Indonesia Industrial Decarbonization [Solar|Wind|Hybrid|All]   │  ← liquid glass header
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Assumptions  │  │ Layer Control│  │ ACTION FLAG LEGEND    │  │
│  │ WACC   10%   │  │ ☑ Substations│  │ ● Solar Now  ● CBAM  │  │
│  │ CAPEX  960   │  │ ☑ PVOUT      │  │ ● Wind Now   ● Grid  │  │
│  │ Life   27yr  │  │ ☑ Wind Speed │  │ ● Not Competitive    │  │
│  │ [▼ Tier 2/3] │  │ ☑ Grid Lines │  │ (14 flags total)     │  │
│  │ [Scenarios]  │  │ ... (14 more)│  └──────────────────────┘  │
│  └──────────────┘  └──────────────┘                            │
│                FULL-SCREEN MAP (MapLibre GL JS)                │
│                      ┌─────────────────────┐                   │
│                      │ ScoreDrawer         │ ← slides in       │
│                      │ 7 tabs: Overview,   │   on site click   │
│                      │ Resource, Grid,     │                   │
│                      │ Economics, Industry,│                   │
│                      │ Action, Flip        │                   │
│                      └─────────────────────┘                   │
├─────────────────────────────────────────────────────────────────┤
│  ═══ grab handle ═══                                            │
│  [Table] [Quadrant Chart] [RUPTL]                               │
│  Bottom drawer (~40% height, translucent dark glass)            │
│  OPEN BY DEFAULT. Toggle via grab handle.                       │
└─────────────────────────────────────────────────────────────────┘
```

All floating panels (Assumptions, Layer Control, Raster Legends) are draggable to avoid overlapping map features.

### Interaction states (3 states + persistent elements)

See mockups in [docs/designs/2026-04-dashboard-refresh/](docs/designs/2026-04-dashboard-refresh/).

**Persistent UI elements** (always visible in both states):
- **Header bar**: Liquid glass overlay (`backdrop-filter: blur(48px)`). Title + energy mode toggle (`EnergyToggle`: Solar / Wind / Hybrid / Overall) + benchmark toggle (BPP / Tariff) + map style selector
- **Assumptions panel** (top-left, draggable): Compact summary of WACC, CAPEX, Lifetime, FOM. Expandable to Tier 1/2/3 sliders including BESS CAPEX, CBAM certificate price, EUR/USD rate. Scenario Manager (save/load up to 3 named scenarios to localStorage).
- **Layer control** (draggable): Toggle panel for 14 map overlay layers. Energy mode auto-shows/hides relevant layers (e.g. solar mode hides wind layers).
- **Action flag legend** (top-right): Color-coded legend for all 14 action flags (see §4)
- **Bottom drawer** (open by default, collapsible via grab handle): Translucent dark glass panel (~40vh). Contains 3 tabs:
  1. Ranked Table — 20 columns (delivered cost hidden when `captive_fraction == 0`), TanStack Table v8, dropdown + range filters, global search, CBAM-only toggle, CSV export
  2. Quadrant Chart — Recharts scatter, LCOE vs grid cost with competitive zone shading
  3. RUPTL Context — Recharts grouped bar chart of planned solar additions by region and year

**State 1 — National view** (default) ([state-1-default-map.png](docs/designs/2026-04-dashboard-refresh/state-1-default-map.png)):
Full-screen dark map (MapLibre GL JS via `react-map-gl`) with all 81 site markers color-coded by action flag (marker shape varies by `site_type`: circle/square/diamond/hexagon). Markers pulse on first load (~5s breathing animation) to signal interactivity. No site selected. All persistent elements visible. Drawer open by default. 4 map style options: Dark, Light, Voyager, Satellite.

**State 2 — Zoomed Site** ([state-2-kek-zoomed.png](docs/designs/2026-04-dashboard-refresh/state-2-kek-zoomed.png)):
Triggered by clicking a site marker on map or a row in the ranked table.
- Map flies to fit the selected site boundary (`flyTo` with bounding box padding)
- Site boundary rendered (action-flag color outline, 0.15 opacity fill) via `GET /api/site/{id}/polygon` (KEK polygon for `kek` site type, circular footprint for non-KEK types)
- 50km radius circle renders around site centroid (visualizes captive solar siting radius)
- Buildable area radiate animation: within-boundary (green) pulses first, then remote (teal) 1s later
- Solar Buildable Areas layer auto-enables on site selection
- PLN substations within radius: rank-coded markers (gold = rank 1, silver = rank 2, cyan = rank 3) from `GET /api/site/{id}/substations`
- Selected site marker enlarged with yellow halo (28px outer + 20px inner)
- ScoreDrawer slides in from right (7 tabs: Overview / Resource / Grid / Economics / Industry / Action / Flip — Flip tab visible when Scenario Compare is active)
  - Close (X) keeps spatial context (radius, polygon visible). Separate from site deselection.
- Bottom drawer still available. RUPTL tab auto-filters to this site's grid region.
- Click a different site in table → transitions directly (no return to State 1 first)
- All slider changes update scorecard + map markers + polygon fill live in zoomed state

**State 3 — LCOE Drilldown** (modal overlay on top of State 2):
Triggered from the Economics tab by clicking the LCOE value (solar mode only, `activeLcoe != null`). Affordance: dashed blue underline on the LCOE stat + hover tint + tooltip "Click for LCOE cost breakdown".
- Modal overlay (liquid glass) rendered by `LcoeWaterfallModal.tsx`
- Header shows site name + infra-readiness badge (color-coded via `INFRA_READINESS_COLORS`)
- Recharts stacked BarChart as a **waterfall**: each bar spans `[running_start, running_end]` so components visually stack from 0 → total
- Components (in order): CAPEX annuity, FOM, land lease, grid connection, new transmission, substation upgrade, Total
- Each component colored per `COMPONENT_COLORS` (capex=blue, fom=purple, land=amber, connection=cyan, transmission=teal, upgrade=orange, total=green)
- Tooltip per bar: component label + `$/MWh` + description + share-of-total %
- Close (X) or Escape returns to State 2 with site context intact
- Map and drawer remain behind the modal (scrim darkens but does not hide them)
- Only renders when `energyMode === 'solar'` and `lcoe_usd_mwh` is defined — hybrid/wind/overall modes don't expose this click path

### View flow (updated)

```
National View (State 1)
    │ click site marker or table row
    ▼
Zoomed Site (State 2)
    │ polygon + 50km radius + substations + ScoreDrawer side panel
    │ close drawer (X) → keeps spatial context; deselect site → back to State 1
    │ click different site in table → stay in State 2, switch site
    │
    │ Economics tab LCOE click (solar mode only)
    │          ▼
    │     LCOE Drilldown (State 3)
    │     modal waterfall of LCOE components → Esc/X → State 2
    │
    │ RUPTL tab auto-filters to site's region
    │ slider changes → POST /api/scorecard → everything updates live
    │
Bottom Drawer (persistent, open by default, toggle via grab handle)
    ├─ Tab 1: Ranked Table → click row → State 2
    ├─ Tab 2: Quadrant Chart
    └─ Tab 3: RUPTL Context

Energy Toggle (persistent, header bar) → switches Solar/Wind/Hybrid/Overall context
  Solar mode: hides wind layers, shows solar-specific action flags
  Wind mode: hides solar layers, shows wind-specific flags
  Hybrid mode: shows both, flags reflect best-of-both analysis
  Overall mode: user controls all layers, flags show best RE technology
```

*Changed 2026-04-08: Map-forward redesign. Changed 2026-04-15: Updated to reflect React/Vite/TypeScript SPA, 4 energy modes, 3 bottom tabs, 14 map layers. Changed 2026-04-17: 25 KEKs → 81 sites; routes renamed `/api/kek/` → `/api/site/`. Changed 2026-04-18: Added 7th `Flip` tab to ScoreDrawer for Scenario Compare (Phase 5). Changed 2026-04-21: Added State 3 (LCOE Drilldown modal) — previously undocumented.*

---

## §3 Component Architecture

### State management

Single Zustand store (`frontend/src/store/dashboard.ts`):

| Slice | Content | Drives |
|-------|---------|--------|
| `assumptions` | All user-adjustable model params (CAPEX, FOM, lifetime, WACC, BESS CAPEX, CBAM price, EUR/USD). Defaults from `GET /api/defaults`. | `POST /api/scorecard` recomputation |
| `thresholds` | Flag thresholds (PVOUT, plan-late, GEAS, resilience gap, reliability) | Included in scorecard POST |
| `scorecard` | Array of `ScorecardRow` (81 sites, ~80 fields each) from API response | Table, map markers, ScoreDrawer, charts |
| `selectedSite` | Currently selected `site_id` (nullable) | ScoreDrawer content, map highlight, polygon/radius |
| `filteredSiteIds` | Array of site IDs passing active dropdown + range filters | Map marker visibility, table row visibility |
| `flipAssumptions` / `flipPreset` / `flipScorecard` / `flipLoading` / `flipStale` | Scenario Compare (A/B flip) state: flip-scenario overrides + recomputed scorecard + loading/stale flags | Map flip rings (green/red halos on sites that change tier), ScoreDrawer Flip tab |
| `activeTab` | Current bottom drawer tab (`table` / `quadrant` / `ruptl` / `compare`) | Bottom drawer content; `compare` tab enables Scenario Compare UI and gates flip-ring map layers |
| `drawerOpen` / `bottomPanelCollapsed` / `assumptionsExpanded` | Panel open/close booleans | Layout visibility |
| `walkthroughPersona` / `walkthroughStep` / `walkthroughDismissed` | Persona-based onboarding state | WalkthroughModal visibility + current step |
| `flyToTarget` | `{ lat, lon, zoom? }` or null | One-shot map fly-to trigger; cleared after animation |
| `energyMode` | `solar` / `wind` / `hybrid` / `overall` | Action flag display, layer visibility, ScoreDrawer fields |
| `benchmarkMode` | `bpp` / `tariff` (today); `bpp_cbam_adjusted` / `tariff_cbam_adjusted` deferred per [TAXONOMY.md](docs/TAXONOMY.md) §7.3 | Grid cost column in table, competitive gap calculation |
| `costBasis` | `raw` / `firmed` / `delivered` — **deferred (PR3)**, see [TAXONOMY.md](docs/TAXONOMY.md) §7.3 | Resolves which cost column feeds `action_flag` / `economic_tier` / gap / `carbon_breakeven` at evaluation time. Default `firmed` for `overall`, `raw` otherwise. |
| `layerVisibility` | Record of 14 layer toggle states | Map overlay rendering |
| `mapStyle` | `dark` / `light` / `voyager` / `satellite` | Map tile source |
| `savedScenarios` | Up to 3 named scenarios in localStorage | ScenarioManager load/save |
| `layers` | Cached GeoJSON for lazy-loaded layers | Map overlays (fetched on first toggle via `GET /api/layers/{name}`) |

### Data flow

```
User adjusts sliders (Zustand store)
         │
         ▼
  POST /api/scorecard { assumptions, thresholds }
         │
         ▼
  src/dash/logic/scorecard.py: compute_scorecard_live()
  (LCOE, action flags, CBAM, wind, hybrid, grid costs — all recomputed)
         │
         ▼
  JSON response: ScorecardRow[] (81 rows × ~80 fields)
         │
         ├──► Map marker colours (action_flag per site)
         ├──► Ranked Table (20 columns, filters, sort)
         ├──► Quadrant Chart (LCOE vs grid cost scatter)
         └──► ScoreDrawer (selected site detail + embedded charts)

User clicks site marker or table row
         │
         ├──► GET /api/site/{id}/polygon → boundary GeoJSON
         ├──► GET /api/site/{id}/substations → nearby substations with costs
         └──► ScoreDrawer slides in with selected site data

Layer toggle
         │
         └──► GET /api/layers/{name} → GeoJSON (cached after first fetch)
```

### Component choices

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Map | MapLibre GL JS via `react-map-gl` | Full-screen, 4 style options (Dark/Light/Voyager/Satellite). Mapbox token for 3D terrain. |
| Map layers (14) | Custom `LayerControl` panel (draggable) | Substations, KEK Boundaries, PVOUT, Wind Speed, Solar Buildable (vector polygons, clickable), Wind Buildable (vector polygons), Peatland, Protected Forest, Industrial Facilities, Grid Lines, Nickel Smelters, Captive Coal, Steel Plants, Cement Plants |
| Raster overlays | `react-map-gl` raster sources | PVOUT + Wind heatmaps with gradient legend strips. Opacity 0.7. |
| Quadrant chart | Recharts `ScatterChart` | Zone shading (green/red). Benchmark toggle (BPP/Tariff). Bottom drawer tab 2. |
| Ranked table | TanStack Table v8 (`@tanstack/react-table`) | 20 columns (delivered cost hidden when `captive_fraction == 0`). Dropdown filters (categorical), range filters (numeric), global search, CBAM-only toggle, CSV export. Bottom drawer tab 1. |
| RUPTL chart | Recharts `BarChart` (grouped) | Region filter, scenario toggle. Bottom drawer tab 3. |
| ScoreDrawer | React slide-in panel (right side) | 7 tabs: Overview / Resource / Grid / Economics / Industry / Action / Flip (Flip shown when Scenario Compare is active). Close (X) separate from site deselect. |
| Bottom panel | `BottomPanel` with grab handle | Translucent dark glass (~40vh). 3 tabs. Toggle open/closed. |
| Energy toggle | `EnergyToggle` (4 modes) | Solar / Wind / Hybrid / Overall. Changes action flags, layer visibility, ScoreDrawer fields. |
| Embedded charts | 4 chart components in ScoreDrawer | `EnergyBalanceChart` (Overview), `LcoeCurveChart` (Economics), `CbamTrajectoryChart` (Industry), `SubstationComparison` (Grid) |
| Scenario manager | `ScenarioManager` in AssumptionsPanel | Save/load up to 3 named scenarios. localStorage persistence. |
| Methodology modal | `MethodologyModal` | Renders `METHODOLOGY_CONSOLIDATED.md` in-app with KaTeX math notation. |
| Site markers (`SiteMarkers.tsx`) | MapLibre layers, shape by `site_type` (circle=KEK, square=KI, diamond=standalone, hexagon=cluster) | Color-coded by action flag. Pulse animation on first load. Yellow halo on selection. Amber CBAM ring + green/red flip ring layers overlaid when applicable. |
| Buildable polygons | MapLibre fill+line layers | Clickable: popup shows area (ha), avg PVOUT, max capacity (MWp). Green = in-boundary, teal = remote. |
| 50km radius | MapLibre circle layer | Renders on site selection. Visualizes captive solar siting radius. |
| Substation markers | MapLibre layers (rank-coded) | Gold (rank 1), silver (rank 2), cyan (rank 3) in zoomed view. |

### Assumption sliders

All sliders configured via `GET /api/defaults` (ranges, steps, defaults from `src/dash/constants.py`).

**Slider-change contract** (`frontend/src/hooks/useScorecard.ts`): every change to `assumptions` / `thresholds` / `benchmarkMode` triggers a 300 ms debounce, then `POST /api/scorecard` via `AbortController`. A newer change aborts the in-flight request. Loading flag is consumed by `AssumptionsPanel` as a 1.5 px pulsing accent dot in the header — sliders stay interactive during recompute. No overlay, no disable. See "Scorecard recomputing" state in §3 Interaction States.

| Slider | Tier | Range | Default | Impact |
|--------|------|-------|---------|--------|
| WACC | 1 | 4–20%, step 2 | 10% | Biggest LCOE driver via CRF |
| CAPEX | 1 | 600–1,500 $/kW, step 10 | 960 | Direct LCOE component |
| Lifetime | 1 | 20–35 yr, step 1 | 27 | CRF denominator |
| FOM | 2 | 3–15 $/kW/yr, step 0.5 | 7.5 | O&M component |
| Connection cost | 2 | 2–12 $/kW-km, step 0.5 | 5.0 | Grid-connected LCOE |
| Substation upgrade | 2 | 50–250 $/kW, step 10 | 80 | Substation capacity deficit |
| Transmission cost | 2 | 0.5–3.0 $M/km, step 0.1 | 1.25 | New line cost |
| BESS CAPEX | 2 | 100–500 $/kWh, step 10 | 250 | Battery storage adder |
| BESS Sizing | 2 | 1–16h, step 1 | auto | Override auto-sizing (2h/4h/14h) |
| Substation utilization | 2 | 0.3–0.95, step 0.05 | 0.65 | **V3.8.** Default applies per-site RUPTL tiers (uprate=85%, extension=75%, line_bay=70%, none=55%) via `substation_utilization_pct_effective`. Override applies globally. See Substation Utilization state rows in §3. |
| WB buildout footprint ratio | 2 | 0.1–1.0, step 0.05 | 0.35 | **V3.9.1.** Haircut applied to raw within-boundary buildable area. Gates `within_boundary` grid_integration_category. Inline in GridTab coverage panel. |
| Meaningful share threshold | 2 | 0.5–1.0, step 0.05 | 1.0 | **V3.9.1.** Effective coverage must exceed this to classify as `within_boundary`. Inline in GridTab Substation Capacity card. |
| CBAM certificate price | 2 | €30–150, step 5 | 80 | CBAM cost trajectory |
| EUR/USD rate | 2 | 1.00–1.30, step 0.01 | 1.10 | CBAM cost conversion |
| IDR/USD rate | 2 | 14,000–18,000, step 100 | 15,800 | Grid cost conversion |
| PVOUT threshold | 3 | 1,200–1,600, step 50 | 1,350 | no_solar_resource cutoff |
| Reliability requirement | 3 | 0–1, step 0.05 | 0.50 | invest_resilience trigger |

### Interaction States

See [PERSONAS.md](PERSONAS.md) for the full persona journeys referenced in the *Persona moment* column.

| State | Trigger | Display | Persona moment | Emotional beat |
|-------|---------|---------|----------------|----------------|
| Loading | App startup, `GET /api/defaults` + initial `POST /api/scorecard` | Loading overlay while data fetches | Any first-time arrival | Anticipation. "Is this going to be heavy?" Sub-2s load keeps trust. |
| National | Default after load | All 81 site markers, pulsing animation (~5s), drawer open | Energy Economist first landing | Scale hits first: "81 of these, and the red ones are where PLN is losing money today." |
| Selected Site | Click marker or table row | Yellow halo, flyTo polygon bbox, 50km radius, ScoreDrawer slides in | IPP/RE Developer evaluating a specific site | Commitment. "Is this the site I pitch the client on?" Zoom + drawer is the focus moment. |
| Drawer Open | Default; toggle via grab handle | Translucent bottom drawer (~40vh) with 3 tabs | DFI Investor ranking pipeline | Comfort. Ranked table is always one glance away. Never buried. |
| Drawer Closed | Toggle grab handle | Only handle bar visible, map expands to full height | Policy Maker in a presentation | Clarity. Full-screen map for briefings. Noise off. |
| Empty filter | Table filters produce zero rows | Empty state message in table area | Any filtering user | Mild confusion. "Did I over-filter?" Clear empty state prevents dead-end feeling. |
| Partial data | Null cell values | Em-dash "—" per cell. Never hides rows with partial data. | All personas on edge-case sites | Honesty. We don't fake numbers. Em-dash signals "we don't know yet" not "zero." |
| **Error (silent fail)** | `POST /api/scorecard` or any `GET /api/*` throws (5xx, timeout, network) | **Known gap.** Today: error is caught in `store/dashboard.ts` actions (`recomputeScorecard`, `computeFlipScorecard`, `initializeDashboard`), logged to `console.error`, and `loading` is flipped back to `false`. No toast, no banner, no error boundary, no retry affordance. Stale scorecard data remains visible to the user. See TODOS entry (to be filed) for shipping an error UX. | Any user after a network blip | Silent confusion — the worst emotion in a data tool. Slider moves, nothing changes, user wonders "did it register?" This is the gap. |
| **Flip loading** | User toggles a flip-scenario assumption in Scenario Compare | `flipLoading: true` while `POST /api/scorecard` for flip scenario is pending; map flip rings and Flip tab values suppressed or show placeholder during compute | Energy Economist / DFI Investor stress-testing | Expectation. "About to see which sites flip tier under a carbon tax." Loading suppression prevents flicker during the compute. |
| **Flip stale** | Base `assumptions` changed after flip scorecard was computed | `flipStale: true`; flip rings dim / Flip tab shows "Recompute" affordance; clears on next `computeFlipScorecard` | Same | Caution. "My base numbers changed — the flip comparison is now out of date." Dim rings signal "don't trust this yet." |
| **LCOE Drilldown (modal)** | Economics tab LCOE click (solar mode, `activeLcoe != null`) | See §2 State 3. Modal overlay on top of State 2. Escape or X closes; State 2 intact. | IPP/RE Developer pressure-testing cost stack | Curiosity. "Why is this site's LCOE $X?" Waterfall answers it without leaving site context. |
| **Substation Utilization — per-site (default)** | `assumptions.substation_utilization_pct === fleet_default` (0.65) | Green status text (`#81C784`): *"Per-site RUPTL tiers active (each site uses its own estimated utilization)"*. Slider value = fleet default but per-substation tiers (uprate=85%, extension=75%, line_bay=70%, none=55%) drive `substation_utilization_pct_effective`. No Reset button shown. | Energy Economist / IPP Developer | Trust. Green status means "we're using real RUPTL plans per substation, not a fleet average." |
| **Substation Utilization — global override** | User drags slider away from fleet default | Amber status text (`#FFB74D`): *"Global override — applies to all sites at XX%"*. Per-site RUPTL tiers are bypassed; slider value applied fleet-wide. *"Reset to per-site"* button appears; clicking restores default and re-enables per-site tiers. | Power user running sensitivity | Deliberate tradeoff. Amber warning signals "you're overriding ground truth — use for what-if, reset for reality." |
| **Grid tab — On-site coverage covered (V3.9.1)** | `grid_integration_category === 'within_boundary'` | Green panel at top of GridTab Grid Integration card. Background `rgba(76,175,80,0.08)`, border `rgba(76,175,80,0.25)`. Header `#66BB6A`: *"Covered on-site — no grid infrastructure required"*. Body narrates raw buildable coverage % → `wb_buildout_footprint_ratio` haircut → effective coverage % → meaningful-share threshold. Inline `wb_buildout_footprint_ratio` slider. Gen-tie / new transmission / substation-upgrade costs zero out. | IPP Developer surveying a self-sufficient site | Relief. Green panel = "you don't need to fight PLN for this one." |
| **Grid tab — On-site coverage partial** | `!isWithinBoundary && hasWbCoverage` (raw coverage > 0 but effective coverage below meaningful-share threshold) | Neutral grey panel. Background `rgba(255,255,255,0.03)`, subtle border. Header muted: *"On-site solar below self-sufficiency threshold"*. Body narrates raw coverage → haircut → effective coverage → *"below threshold, so grid infrastructure still applies"*. Inline `wb_buildout_footprint_ratio` slider. | Energy Economist pressure-testing buildout assumptions | Informed tradeoff. "If I loosen the footprint ratio, does this site flip into self-sufficient?" |
| **Grid tab — RUPTL substation upgrade (V3.8)** | `row.substation_utilization_pct_effective != null && row.ruptl_project_type != null` | Blue-tinted panel in Substation Capacity card. Background `rgba(33,150,243,0.08)`, border `rgba(33,150,243,0.25)`, header `#64B5F6`. Body: *"PLN RUPTL plans a {project_type} adding +{MVA} MVA by {target_year} ({status})"*. Explains why effective utilization defaults to tier-specific value (uprate=85%, extension=75%, line_bay=70%) vs 65% fleet. | Any user at a site with an upgrade in the pipeline | Confidence. "PLN is actively planning capacity here — this isn't speculative." |
| **Grid tab — No RUPTL match** | `row.substation_utilization_pct_effective != null && !ruptl_project_type` | Same location, neutral styling. Body: *"No RUPTL upgrade plan matched this substation — using the fleet-average utilization (65%). Override via the global Substation utilization slider if you have local intel."* | Same | Honest. No invented signal. Slider escape hatch offered. |
| **Scorecard recomputing** | Any slider / threshold / `benchmarkMode` change | 300 ms debounce in `useScorecard.ts` → `POST /api/scorecard` with `AbortController` (new change aborts in-flight request). Visible indicator: 1.5×1.5 px accent-colored dot with `animate-pulse` in AssumptionsPanel header (line 297). No overlay, no slider disable. | Any user dragging a slider | Reassurance. Dot flickers = "it heard you." No heavy overlay mid-drag. |

### ScoreDrawer Tab Fields

Fields sourced from `POST /api/scorecard` response (~80 fields per site). See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full column definitions.

**Overview tab** — "What's the story for this site?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `site_name`, `site_type`, `sector`, `province`, `area_ha` | Site identity | Header section (registry-driven per `SITE_TYPES[site_type].identityFields` in `frontend/src/lib/siteTypes.ts` — field list varies by site type) |
| `demand_mwh_2030` | Estimated 2030 demand | MWh |
| LCOE (mode-aware) | Solar / Wind / Hybrid LCOE | Changes with energy mode toggle |
| `dashboard_rate_usd_mwh` | Grid cost (BPP or Tariff) | Benchmark-mode-aware |
| `solar_competitive_gap_pct` | LCOE Gap | % (negative = competitive) |
| `solar_supply_coverage_pct` | Solar supply coverage | % of demand from 50km buildable |
| `grid_investment_needed_usd` | Grid investment needed | $ (connection + upgrade + transmission) |
| **EnergyBalanceChart** | MacKay-style supply vs demand | Dual stacked bars: day/night demand vs solar/gap. Hidden in wind mode. |

**Resource tab** — "What renewable resource is available?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `pvout_centroid`, `pvout_best_50km`, `pvout_buildable_best_50km` | Solar PVOUT | kWh/kWp/yr, 3 siting scenarios |
| `cf_centroid`, `cf_best_50km` | Solar capacity factor | % |
| `buildable_area_ha`, `max_captive_capacity_mwp` | Buildable area + capacity | With fragmentation warning for small areas |
| `wind_speed_centroid_ms`, `cf_wind_centroid` | Wind resource | m/s + CF |
| `lcoe_wind_mid_usd_mwh` | Wind LCOE | USD/MWh |
| `best_re_technology` | Best RE technology | solar / wind / hybrid |
| Technology comparison | Solar vs Wind vs Hybrid | Side-by-side LCOE + coverage |

**Grid tab** — "How does this site connect to the grid?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `grid_integration_category` | Integration category | within_boundary / grid_ready / invest_transmission / invest_substation / grid_first |
| **On-site coverage panel (V3.9.1)** | Green or neutral conditional panel | Renders at top of Grid Integration card. Two modes: green "Covered on-site" when `within_boundary`, neutral "below self-sufficiency threshold" when raw coverage > 0 but effective < meaningful_share. See §3 state table for exact styling. |
| `within_boundary_coverage_pct`, `within_boundary_coverage_effective_pct` | Raw & effective coverage | Used inside the coverage panel narrative |
| `wb_buildout_footprint_ratio` slider | Inline in coverage panel | Tier 2 slider embedded in both coverage-panel modes. Changes buildout haircut; flips sites between self-sufficient and partial coverage live |
| 3 distances | Solar→Sub, Sub→Site, Solar→Site | km |
| `line_connected`, `inter_substation_connected` | Grid line connectivity | Boolean (geometric check against `pln_grid_lines.geojson`) |
| `capacity_assessment` | Substation capacity | Green/yellow/red traffic light |
| **RUPTL upgrade plan panel (V3.8)** | Blue-tinted conditional panel | Renders in Substation Capacity card when `ruptl_project_type` is non-null. Describes the specific PLN plan (type, added MVA, target year, status). Explains per-site utilization tier (vs 65% fleet default). |
| `substation_utilization_pct_effective`, `ruptl_project_type`, `ruptl_mva_added_total`, `ruptl_earliest_target_year`, `ruptl_strongest_status` | Per-substation RUPTL fields | V3.8 fields. Drive the RUPTL upgrade plan panel. |
| `meaningful_share_pct` slider | Inline in Substation Capacity card | Tier 2 slider controlling the "meaningful share" threshold that gates `within_boundary` classification |
| **SubstationComparison** | Top 3 substations | Per-substation costs (connection, upgrade, transmission, all-in LCOE). Rank-coded map markers. |

**Economics tab** — "What does the energy cost?"

Tier tags (T1 / T2 / T3 / B) reference [TAXONOMY.md §1](docs/TAXONOMY.md#1-three-tiers--a-benchmark). Once the CostBasis toggle ships (TAXONOMY §7.3), rows tagged T1 / T2 / T3 are what the toggle picks between.

| Field | Display label | Tier | Notes |
|-------|--------------|------|-------|
| `lcoe_low/mid/high_usd_mwh` | LCOE variance | T1 | 3 WACC scenarios (grid-connected, best-50km PVOUT) |
| Battery storage | BESS CAPEX slider (100-500 $/kWh), sizing slider (1-16h) | T2 (component) | Live recomputation of `battery_adder_usd_mwh`. "Reset to auto" restores per-site sizing. |
| `hybrid_lcoe_usd_mwh`, `hybrid_bess_hours` | Hybrid BESS reduction | T1 (hybrid gen) / T2 (allin) | % reduction from wind nighttime coverage |
| `delivered_cost_blended_usd_mwh` | Delivered Cost (Blended) | T3 | Shown when within-boundary captive > 0. `f_captive × LCOE_wb + f_grid × grid_rate`. See [TAXONOMY §2.T3](docs/TAXONOMY.md#t3-delivered-cost-tenant-view--54). |
| `carbon_breakeven_usd_tco2` | Carbon breakeven price | T1-derived | USD/tCO2 |
| `green_share_geas` | GEAS green share | — | % of 2030 demand met by allocated RE |
| **LcoeCurveChart** | LCOE vs project scale | T1 | Shows how LCOE drops as capacity increases (transmission cost spreading) |

**Industry tab** — "What industry is here and what's the CBAM exposure?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `demand_mwh_2030` | Demand estimation | MWh |
| Solar/wind generation capacity | 50km radius + within-boundary | MWh |
| `captive_coal_count`, `captive_coal_mw` | Captive coal plants | GEM tracker |
| `nickel_smelter_count`, `dominant_process_type` | Nickel smelters | CGSP tracker |
| `steel_plant_count`, `steel_total_tpa` | Steel plants | GEM tracker |
| `cement_plant_count`, `cement_total_mtpa` | Cement plants | GEM tracker |
| `cbam_exposed`, `cbam_product_type` | CBAM exposure | **Dual-mode dispatch** via `SITE_TYPES[site_type].cbam_method`: KEKs use 3-signal inference (process type + plant counts + business sectors); standalone/cluster/KI sites read `cbam_product_type` directly from `dim_sites`. 68/81 sites exposed (12 KEK + 56 industrial). |
| `cbam_cost_2026/2030/2034_usd_per_tonne` | CBAM cost trajectory | Free allocation phase-out schedule (97.5% → 0%) |
| `cbam_savings_2026/2030/2034_usd_per_tonne` | CBAM savings from RE | Avoided border tax |
| **CbamTrajectoryChart** | CBAM cost trajectory 2026-2034 | Per-product breakdown (nickel_rkef, steel_eaf, steel_bfbof, cement, aluminium, fertilizer). 2030 crossover year marker ("50% exposed"). User-adjustable certificate price + EUR/USD rate. |

**Action tab** — "What should be done?" (V3.7: 2D classification layout)
| Field | Display label | Notes |
|-------|--------------|-------|
| `economic_tier` | RE Viability | Two-column layout: left column shows economic tier with mode-specific label (Full Solar/Full Wind/Full RE) |
| `infrastructure_readiness` | Infrastructure | Right column shows infrastructure readiness with context-aware label (Upgrade vs Build Substation) |
| `modifier_badges` | Modifier badges | Pill badges for cbam_urgent, plan_late, storage_info |
| `action_flag` | Legacy action flag | Retained for backwards compatibility |
| Implementation guidance | Explanation text | Per-tier and per-readiness actionable descriptions |
| RUPTL context | Regional grid pipeline | Planned capacity additions for this site's grid region |

**Flip tab** — "What changes under the flip scenario?" (visible only when Scenario Compare mode is active, i.e. `activeTab === 'compare' && flipScorecard != null`)
| Field | Display label | Notes |
|-------|--------------|-------|
| Scenario banner | Active flip preset name | e.g. "WACC −2pp + CBAM €120" or "custom" |
| Tier transition | Before → After pill | Economic tier change between base and flip scenarios (green = improved, red = worsened) |
| `Δ lcoe_mid_usd_mwh` | Delta LCOE | Signed USD/MWh |
| `Δ solar_competitive_gap_pct` | Delta Gap-to-Grid | Signed % |
| CBAM urgency chips | NEW / CLEARED | `cbam_urgent` status change between base and flip scenarios |
| Source | `useFlipDiff()` / `computeFlipDiff()` | Store selector returns per-site diff payload from `scorecard` vs `flipScorecard` |

See 2026-04-18 changelog (Scenario Compare Phase 5) for the full flip-scenario mechanics (map flip rings, `FlipTab.tsx`, gated on `activeTab === 'compare'`).

---

## §4 Colour & Visual Language

### 2D Classification Visual System (V3.7)

Sites are now classified on two independent axes plus overlay modifier badges. The map encodes all three dimensions on a single marker (shape varies by `site_type`):

- **Marker fill** = Economic Tier (how viable is RE?)
- **Marker stroke** = Infrastructure Readiness (what infrastructure exists?)
- **Outer ring** = Modifier Badge (CBAM urgency, plan-late, storage)
- **Marker shape** (added V4.0) = Site Type (circle=KEK, square=KI, diamond=standalone plant, hexagon=cluster)
- **Flip halo** (added Phase 5, Scenario Compare mode only) = Tier-change direction (green = improved, red = worsened)

#### Economic Tier colours (circle fill)

| Tier | Colour | Hex | Meaning |
|------|--------|-----|---------|
| `full_re` | Green | `#2E7D32` | RE + storage beats grid 24/7 |
| `partial_re` | Light Green | `#66BB6A` | Daytime RE beats grid, storage too expensive |
| `near_parity` | Yellow | `#FFA726` | RE LCOE within 20% of grid |
| `not_competitive` | Red | `#C62828` | RE LCOE > 20% above grid |
| `no_resource` | Grey | `#78909C` | No buildable RE land |

Mode-aware labels: Solar mode shows "Full Solar"/"Partial Solar", Wind mode shows "Full Wind"/"Partial Wind", Overall/Hybrid shows "Full RE"/"Partial RE". Derived in `frontend/src/lib/actionFlags.ts:getEconomicTierLabel()`.

#### Infrastructure Readiness colours (circle stroke)

| Readiness | Colour | Hex | Meaning |
|-----------|--------|-----|---------|
| `within_boundary` | Green | `#4CAF50` | Solar buildable inside site boundary |
| `grid_ready` | Blue | `#42A5F5` | Existing grid infrastructure sufficient |
| `invest_transmission` | Orange | `#FF9800` | Build transmission line to site |
| `invest_substation` | Deep Orange | `#FF5722` | Build/upgrade substation near solar site |
| `grid_first` | Red | `#F44336` | Grid infrastructure must come first |

Context-aware labels: `invest_substation` shows "Upgrade Substation" when capacity_assessment is yellow/red (existing substation, insufficient capacity) vs "Build Substation" when no nearby substation. Derived in `frontend/src/lib/actionFlags.ts:getInfraReadinessLabel()`.

#### Modifier Badge colours (outer ring / badge pills)

| Badge | Colour | Hex | Meaning |
|-------|--------|-----|---------|
| `cbam_urgent` | Amber | `#FF6F00` | CBAM-adjusted gap < 0. RE + avoided border tax beats grid. |
| `plan_late` | Purple | `#7B1FA2` | >60% of RUPTL solar planned after 2030. |
| `storage_info` | Blue-grey | `#546E7A` | BESS sizing > 2h (bridge or overnight firming). |

### Legacy action flag colours

14 flags still defined in `frontend/src/lib/constants.ts` for backwards compatibility with `action_flag` column. Energy mode determines which flags are shown (e.g. solar mode shows `solar_now`, wind mode shows `wind_now`, overall mode shows `best_re_technology`-aware flags).

Flags are currently T1-driven (raw `lcoe_mid` vs `grid_cost`). Once the CostBasis toggle ships ([TAXONOMY §7.3](docs/TAXONOMY.md#7-deferred-decisions)), the legend will append "Flags computed on: {basis} × {energy_mode}" so the active cost basis is visible.

| Flag | Colour | Hex | Meaning |
|------|--------|-----|---------|
| `solar_now` | Green | `#2E7D32` | Solar LCOE < grid cost. Act now. |
| `cbam_urgent` | Amber | `#FF6F00` | CBAM-adjusted gap < 0. RE + avoided border tax beats grid. See [Layer 3 spec](docs/layer3_green_industrial_products_spec.md). |
| `wind_now` | Dark Green | `#1B5E20` | Wind LCOE < grid cost. |
| `hybrid_now` | Green | `#2E7D32` | Hybrid solar+wind all-in LCOE < grid cost. |
| `invest_resilience` | Orange | `#F57C00` | Within 20% of parity + high reliability requirement. |
| `invest_battery` | Light Orange | `#FFA726` | Competitive with battery storage investment. |
| `invest_transmission` | Blue | `#0277BD` | Solar near substation but site far. Build transmission. |
| `invest_substation` | Teal | `#00838F` | Site near substation but solar far. Upgrade substation. |
| `grid_first` | Blue | `#1565C0` | Grid upgrade needed before RE is viable. |
| `plan_late` | Purple | `#7B1FA2` | RUPTL solar planned but after 2030. |
| `not_competitive` | Red | `#C62828` | RE not competitive; no near-term trigger. |
| `no_solar_resource` | Grey | `#78909C` | PVOUT below threshold (1,350 kWh/kWp/yr). |
| `no_wind_resource` | Grey | `#78909C` | Wind CF below cut-in threshold. |
| `no_re_resource` | Grey | `#78909C` | Neither solar nor wind resource available. |

### Data quality indicators

| Indicator | Display | Applies to |
|-----------|---------|-----------|
| Provisional value | Dagger suffix (†) + italic | `is_capex_provisional`, `bpp_provisional` |
| Upper bound resource | "(upper bound)" label | `resource_quality = "upper_bound"` |
| Filtered resource | "(filtered)" label | `resource_quality = "filtered"` — all 81 sites currently |
| Missing data | "—" (em dash) | Any null column |

### Quadrant zones

```
        │ Grid cost proxy
        │
  High  │  [Grid first]     [Not competitive]
        │
  Low   │  [Solar now]      [Invest: resilience]
        │
        └──────────────────────────────────────
           Low LCOE              High LCOE
```

**Naming:** `grid_cost_usd_mwh` / `bpp_usd_mwh` / `dashboard_rate_usd_mwh` / "grid cost proxy" all refer to the same B-category benchmark. See [TAXONOMY §2.B](docs/TAXONOMY.md#b-grid-benchmark).

---

## §5 Data Decisions for the UI

### What is precomputed vs. computed live

| Data | Approach | Why |
|------|----------|-----|
| **Precomputed (pipeline)** | | |
| Solar resource (PVOUT, CF) | `fct_site_resource.csv` loaded at startup | Requires GeoTIFF processing; cannot be live |
| Substation distances | `fct_substation_proximity.csv` loaded at startup | Requires geospatial computation |
| RUPTL pipeline | `fct_ruptl_pipeline.csv` loaded at startup | Static government data |
| Grid cost proxy | `fct_grid_cost_proxy.csv` loaded at startup | Static regulatory data |
| Demand estimates | `fct_site_demand.csv` loaded at startup | User can override via `resolve_demand()` |
| `fct_lcoe.csv` (1,458 rows = 81 sites × 9 WACCs × 2 siting scenarios) | Still produced by pipeline for reproducibility/export | Default-assumption reference; dashboard computes live instead |
| **Live (dashboard callback)** | | |
| LCOE bands (all scenarios) | `compute_lcoe_live()` in `src/dash/logic/lcoe.py` | User adjusts CAPEX, FOM, lifetime, WACC, gen-tie, lease via sliders. ~5ms for 81 sites × 2 scenarios |
| Competitive gap | `solar_competitive_gap()` from `basic_model.py` | Recalculated when LCOE or grid benchmark changes |
| Action flags | `action_flags()` + `invest_resilience()` from `basic_model.py` | Recalculated when LCOE or thresholds change |
| Carbon breakeven | `carbon_breakeven_price()` from `basic_model.py` | Recalculated when LCOE or grid cost changes |
| GEAS green share | `geas_baseline_allocation()` from `basic_model.py` | Recalculated if demand override changes |
| Flip scenario | Filter live LCOE results by gap threshold | Client-side filter on live-computed data |

### WACC slider behaviour

The dashboard ships with nine precomputed WACC values (4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20%). The WACC selector is a React range slider with snap marks at each value, default = 10%. This covers the full range from DFI concessional financing (4–6%) through SE Asia equity ceiling (20%). No continuous interpolation is needed. See [METHODOLOGY_CONSOLIDATED.md §6](docs/METHODOLOGY_CONSOLIDATED.md) for the full WACC methodology.

### Demand override hook

The `demand_mwh_user` column in `fct_site_demand` is nullable (`Float64`). If a user enters a custom demand value in the Scorecard panel, the app calls `resolve_demand(demand_mwh_modelled, demand_mwh_user)` from `src/model/basic_model.py` to get the effective demand, then recalculates `green_share_geas` server-side and updates the scorecard display only (does not write back to CSV).

---

## §6 Resolved Design Questions (Phase 3)

All resolved during Phase 3 autoplan review (2026-04-07):

| # | Question | Resolution | Decision # |
|---|----------|-----------|------------|
| 1 | **WACC slider** | ✅ **9-value `dcc.Slider`** with snap points at [4,6,8,10,12,14,16,18,20], default=10%. Covers full concessional-to-equity range. | #21, #27 |
| 2 | **Map tile provider** | ✅ **Mapbox dark-v11** via dash-leaflet. Token loaded from `.env` via python-dotenv. Native `dl.LayersControl` for overlay toggling. | — |
| 3 | **Mobile layout** | ✅ **Desktop-only for MVP**. Primary users are analysts with laptops. Responsive deferred to v2 (see [TODOS.md](TODOS.md) L7). | — |
| 4 | **Provisional data warning** | ✅ **Dagger (†) per cell**. Cell-level precision; no banner noise. | — |
| 5 | **Export format** | ✅ **CSV + GeoJSON**. DFI investors need GeoJSON for site team handoff (see [PERSONAS.md §DFI Investor](PERSONAS.md)). | — |

**Active open items:** Cost-column renames + CostBasis toggle are tracked in [TAXONOMY.md §7](docs/TAXONOMY.md#7-deferred-decisions).

---

## §6.5 Accessibility Floor (MVP)

Desktop-only doesn't excuse skipping keyboard users. The floor spec — verified today, enforced in review:

| Surface | Keyboard contract | Status |
|---------|-------------------|--------|
| `LcoeWaterfallModal` (State 3) | Esc closes; focus returns to the LCOE button that opened it; focus trapped inside modal while open | Spec — verify in `/qa` |
| `ScoreDrawer` (State 2) | Esc closes the drawer; Tab cycles across the 7 tabs in left-to-right order; close (X) reachable via Tab | Spec — verify in `/qa` |
| `BottomPanel` (drawer) | Tab cycles tab pills (Table / Quadrant / RUPTL); grab handle reachable via Tab | Spec — verify in `/qa` |
| All sliders (~17) | Arrow keys adjust by slider step; Home/End snap to min/max; visible focus ring matches `--focus-ring` token | Spec — verify in `/qa` |
| Filter dropdowns + CBAM toggle | Space/Enter activate; Arrow keys move within menus | Spec — verify in `/qa` |
| Map markers | MapLibre default keyboard pan/zoom supported (+/-/arrows); marker click reachable via keyboard is **deferred** to v2 (documented limitation) | Known gap |
| Focus rings | Visible on all interactive elements; never `outline: none` without a replacement | Spec |

**ARIA polish deferred to v2**: `aria-label` on icon-only buttons, `role="dialog"` + `aria-modal` on modal, live-region announcements on scorecard recompute. Track in TODOS.md.

*Changed 2026-04-21: added §6.5 to establish a11y floor (previously unspecified).*

---

## §7 CBAM / Green Industrial Products (Layer 3)

**Feature spec:** [docs/layer3_green_industrial_products_spec.md](docs/layer3_green_industrial_products_spec.md)

EU CBAM entered its definitive phase January 2026. Indonesian exporters of iron, steel, aluminum, and fertilizers to the EU pay a carbon price at the border. This feature layer adds CBAM exposure analysis to the dashboard, transforming it from an energy analysis tool into a trade competitiveness tool.

### What shipped (all P0-P2 items from spec)

| Feature | Location | Status |
|---------|----------|--------|
| CBAM exposure flag per site | Scorecard + table column | ✅ 68/81 sites exposed via **dual-mode dispatch** (see `SITE_TYPES[site_type].cbam_method`): (A) 12 KEKs via `3_signal` inference — nickel process types, plant counts, KEK business sectors; (B) 56 industrial sites (32 cement + 17 iron_steel + 5 fertilizer + 2 aluminium) via `direct` — reads `cbam_product_type` straight from `dim_sites`. |
| CBAM cost trajectory 2026-2034 | `CbamTrajectoryChart` in ScoreDrawer Industry tab | ✅ Per-product breakdown (nickel_rkef, steel_eaf, steel_bfbof, cement, aluminium, fertilizer). Free allocation phase-out: 97.5% (2026) → 0% (2034). |
| 2030 crossover year marker | ReferenceLine on trajectory chart | ✅ Dashed line at 2030 with "50% exposed" label. 2030 = inflection point (51.5% free allocation remaining). |
| CBAM-adjusted competitive gap | `cbam_adjusted_gap_pct` column in table | ✅ `(LCOE - grid_cost - cbam_savings_per_mwh) / grid_cost × 100`. Negative = RE + avoided border tax beats grid. |
| CBAM cost per tonne at 2030 | `cbam_cost_2030_usd_per_tonne` column in table | ✅ Amber-colored $/t values. Range-filterable. |
| `cbam_urgent` action flag | Action flag system | ✅ Fires when CBAM-adjusted gap < 0. Overrides `not_competitive` and `invest_resilience`. |
| CBAM assumption sliders | AssumptionsPanel (Tier 2) | ✅ Certificate price (€30-150), EUR/USD rate (1.00-1.30). |
| CBAM-only table filter | DataTable toolbar | ✅ Amber toggle filters to 68 exposed sites. |
| CBAM visual indicators | Map + Table + Legend | ✅ Map: amber ring (`#FF6F00`) around CBAM-exposed marker + "CBAM" label in hover tooltip. Table: amber outer ring around action flag dot for exposed sites. Legend: `cbam_urgent` shown as ring (not solid dot) with hover description. |

### Connection to existing features

- **Action flags:** `cbam_urgent` is ranked above `not_competitive` in all 4 energy mode hierarchies. A site that would be `not_competitive` on energy alone becomes `cbam_urgent` if CBAM savings make RE cheaper.
- **Competitive gap:** CBAM savings (~$33-34/MWh for exposed sites) are subtracted from the gap calculation. Converts energy cost comparisons into trade cost comparisons.
- **Perpres 112/2022:** Creates a domestic-international pincer: Perpres = domestic regulatory stick, CBAM = international financial stick.

---

## §8 Architecture Notes

### Frontend: React + Vite + TypeScript SPA

The dashboard is a Vite + React 18 + TypeScript SPA with Tailwind CSS. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system diagram.

**Key patterns:**
- **Zustand store** (`frontend/src/store/dashboard.ts`): Single store for all state. No prop drilling. Components subscribe to slices.
- **API layer** (`frontend/src/lib/api.ts`): Fetch wrappers for all 7 endpoints. The scorecard endpoint (`POST /api/scorecard`) is the hot path, called on every assumption change.
- **Liquid glass styling**: All floating panels use CSS custom properties from `globals.css`: `--glass-heavy` background, `--blur-heavy` backdrop-filter, `--glass-border-bright` border.
- **Biome** for formatting/linting (pre-commit hook).

### Backend: FastAPI

`src/api/` wraps existing pipeline modules. All computation happens server-side in the `src/dash/logic/` package (split by domain: assumptions, lcoe, cbam, grid, technology, scorecard).

**Key endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/defaults` | GET | Default assumptions, thresholds, slider configs |
| `/api/scorecard` | POST | Recompute all 81 sites with user assumptions |
| `/api/layers/{name}` | GET | Lazy-load GeoJSON layers (14 available) |
| `/api/site/{id}/polygon` | GET | Site boundary polygon (KEK polygon, or circular marker for non-KEK sites) |
| `/api/site/{id}/substations` | GET | Substations within radius with per-substation costs |
| `/api/ruptl-metrics` | GET | RUPTL pipeline metrics by region |
| `/api/methodology` | GET | Raw METHODOLOGY_CONSOLIDATED.md for in-app rendering |

### Business logic extraction

All computation in the `src/dash/logic/` package as pure functions. `compute_scorecard_live()` (orchestrator in `logic/scorecard.py`) takes assumptions + thresholds, returns full scorecard DataFrame. Domain-split into `assumptions.py`, `lcoe.py`, `cbam.py`, `grid.py`, `technology.py`; public API re-exported via `logic/__init__.py` so external callers stay stable. Testable with pytest, no server dependency. 610 tests cover model, pipeline, API, module boundaries, and golden-master parity.

---

## §9 Changelog

All design changes tracked with date, autoplan decision number, and rationale.

| Date | Decision # | Change | Rationale |
|------|-----------|--------|-----------|
| 2026-04-07 | #21, #27 | WACC selector: 3-value radio → 9-value slider | Data expanded to 4–20%; radio too wide for 9 options |
| 2026-04-07 | #18 | Add grid benchmark override input | I-4/TT may not apply to negotiated-PPA KEKs (PP 112/2022) |
| 2026-04-07 | #19 | Add wind CF integration (§7) | Architecture supports it identically; user accepted at premise gate |
| 2026-04-07 | #25 | Move Flip Scenario after Scorecard in view flow | Previous placement broke hope → confirmation → conviction arc |
| 2026-04-07 | #23 | Add demand override UI widget in Scorecard | Model already supports `resolve_demand()`; just needs `dcc.Input` |
| 2026-04-07 | #26 | Add Interaction States subsection | Loading/empty/error/partial states were entirely unspecified |
| 2026-04-07 | #28 | Define Scorecard tab fields | "4 tabs" had no field specification; implementer would guess |
| 2026-04-07 | #29 | Extract callback logic to `src/dash/logic.py` | Testability: pure functions, no Dash dependency |
| 2026-04-17 | — | Split `src/dash/logic.py` (1,437 LOC) → `src/dash/logic/` package (7 files: assumptions, lcoe, cbam, grid, technology, scorecard, __init__) | Readability + cohesion: each domain owns one module. Bit-identical outputs verified via golden-master fixture. Public API frozen via `__init__.py` re-export shim — external callers unchanged. 537 tests (up from 498): 6 new module-boundary test files + 1 parity test. |
| 2026-04-07 | #30 | Add startup CSV validation | 8 error paths unhandled; app crashed silently on missing data |
| 2026-04-07 | #34 | Configurable assumptions: 3-tier slider controls + live LCOE recomputation | Hardcoded assumptions limited all 4 personas; 25 KEKs makes live computation trivial (~5ms) |
| 2026-04-08 | — | Implement interaction states: loading spinner, empty table, selected KEK highlight | Design review found all 4 interaction states unimplemented |
| 2026-04-08 | — | Expand scorecard: add Demand tab + Pipeline tab, complete Resource/LCOE fields (now Solar/Economics/Grid tabs) | Scorecard was missing ~half of DESIGN.md §3 fields, 2 of 4 tabs |
| 2026-04-08 | — | Add quadrant zone shading (green/red) with labels | Parity line alone didn't communicate competitive zones |
| 2026-04-08 | — | Polish: rgba() table colors, Badge tooltips, consistent helper naming | Design review polish findings (hex hack, inconsistent "?" style) |
| 2026-04-08 | — | Map-forward redesign: full-screen map, right slide-in scorecard, bottom drawer with Table/Quadrant/RUPTL/Flip tabs | Design-shotgun exploration chose variant C (map-forward) refined to 4 interaction states |
| 2026-04-08 | — | Add zoomed KEK detail: polygon boundary, infrastructure markers, substation proximity on click | KEK click should show spatial context (polygon, nearby infra) not just data |
| 2026-04-08 | — | Add RUPTL Context view as bottom drawer tab 3 | DESIGN.md View 6 was unimplemented; grouped bar chart of planned solar by region/year |
| 2026-04-08 | — | Energy source segmented control (Solar/Wind/Overall) in header bar | Supports wind integration (§7) and overall best-RE view |
| 2026-04-08 | — | Bottom drawer open by default; assumptions as compact summary card (expandable) | Default state should show data immediately, not require interaction to access table/charts |
| 2026-04-08 | — | Simplify to 2-state model (National View + Zoomed KEK); drawer and energy toggle are persistent elements | States 3/4 weren't separate states, just UI elements available in both states |
| 2026-04-08 | — | Full migration from dash-bootstrap-components to dash-mantine-components (DMC) | DMC has native dark theme, SegmentedControl, Drawer, better Tabs. Single component library. |
| 2026-04-08 | — | Live updates in Zoomed KEK state: scorecard + map markers + polygon fill all recompute when sliders change | User should see impact immediately without returning to national view |
| 2026-04-08 | — | Drawer toggle: click grab handle to toggle between collapsed (0%) and open (40vh), no drag-to-resize | Simple, predictable. Avoids custom JS and Plotly resize complexity |
| 2026-04-08 | — | Migrate map from Plotly Scattermapbox to dash-leaflet with native `dl.LayersControl` | Leaflet provides native layer toggle UI (expandable checkbox panel), no custom sidebar needed |
| 2026-04-08 | — | Switch from Carto tiles to Mapbox dark-v11 via `dl.TileLayer` | User added Mapbox token to `.env`; Mapbox has better styling and satellite options |
| 2026-04-08 | — | Add python-dotenv + dash-leaflet dependencies | Token loaded from `.env` at startup; dash-leaflet replaces Plotly map rendering |
| 2026-04-08 | — | Add "Back to National View" button (top-center, State 2 only) | No way to exit zoomed KEK state without closing scorecard drawer; explicit back button is clearer |
| 2026-04-08 | — | Scorecard drawer: title "KEK Scorecard", visible close X, closeOnClickOutside | Close button was invisible with empty title; clicking outside should also close |
| 2026-04-08 | — | Dark theme CSS overrides for slider marks, tooltips, and Mantine Accordion | Slider mark text and tooltip values were illegible (dark text on dark background) |
| 2026-04-08 | — | LayersControl positioned at bottom-left to avoid overlap with action flag legend | Default top-right position overlapped with the legend panel |
| 2026-04-08 | — | Full migration from Dash to React + Vite + TypeScript SPA with FastAPI backend | Dash limitations (no lazy layer loading, no rich map interactions, bundle size). React + MapLibre gives native layer control, fly-to, polygon rendering. |
| 2026-04-08 | — | Liquid glass header: translucent backdrop-filter overlay on map | Map is always full-screen, header floats above with blur(48px) glass effect |
| 2026-04-08 | — | 50km radius circle renders on map when KEK is selected | Visualizes the captive solar siting radius used by the model |
| 2026-04-08 | — | Raster layer legends (PVOUT, Wind) with color gradient strips | User couldn't interpret heatmap colors without a legend |
| 2026-04-08 | — | Draggable panels: Assumptions, Layer Control, and Raster Legends all movable | Panels can overlap map features; drag to reposition |
| 2026-04-08 | — | Drawer close (X) separated from KEK deselection; radius stays visible | User wants to close the detail panel but keep the spatial context (radius, polygon) |
| 2026-04-08 | — | Methodology modal: renders METHODOLOGY_CONSOLIDATED.md in-app with KaTeX math notation | Stakeholders can review analytical methodology without leaving the dashboard |
| 2026-04-08 | — | Pulsing KEK markers on first load (~5s breathing animation) | Signals that markers are interactive/clickable |
| 2026-04-08 | — | Biome formatter added to pre-commit hook for TypeScript/React | Consistent code style across all frontend files |
| 2026-04-08 | — | Buildable area fragmentation warning in ScoreDrawer Solar tab | 1km PVOUT resolution makes contiguity filter a no-op; UI caveat for small buildable areas |
| 2026-04-09 | — | Thesis pivot: remote captive → grid-connected solar; three-point proximity replaces gen-tie model | No global precedent for 50km private gen-tie; realistic model is IPP → PLN PPA → grid delivery → KEK |
| 2026-04-09 | — | DFI persona reframed: captive solar investor → grid infrastructure investor | DFIs fund grid infra (ADB/WB precedent), not private gen-ties |
| 2026-04-09 | — | New persona: Industrial Investor / KEK Tenant (buys from PLN, doesn't build solar) | Separates power consumer from power producer decision-making |
| 2026-04-09 | — | New action flag: invest_grid (solar exists but grid connection missing) | Policymaker needs to see WHERE grid investment unlocks solar |
| 2026-04-12 | — | Removed raster "Solar Buildable Area" layer; polygon layer renamed to "Solar Buildable Areas" | Raster at ~3.7km was coarse and inconsistent with vector polygons. Single source of truth now. |
| 2026-04-12 | — | Buildable polygons are clickable: popup shows area (ha), avg PVOUT, max capacity (MWp) | Users can inspect individual contiguous buildable sites on the map |
| 2026-04-12 | — | Within-boundary theoretical fallback zeroed out | KEKs with no spatial buildable pixels now show 0% coverage instead of a fake 20% estimate |
| 2026-04-12 | — | Methodology files consolidated: archived v0.4 + V2 + testing notes → `docs/archives/` | Single canonical methodology: `docs/METHODOLOGY_CONSOLIDATED.md` |
| 2026-04-12 | — | M12: Substation upgrade cost in precomputed LCOE pipeline + live scorecard API | `substation_upgrade_cost_per_kw` and `transmission_cost_per_kw` now flow through live API; `grid_investment_needed_usd` includes all 3 cost components |
| 2026-04-12 | — | M16: LCOE vs project scale curve chart (`LcoeCurveChart.tsx`) in ScoreDrawer Solar tab | Shows how LCOE drops as capacity increases (transmission cost spreading). Client-side CRF formula. |
| 2026-04-12 | — | M7: Scenario save/compare (`ScenarioManager.tsx`) in AssumptionsPanel | Save up to 3 named scenarios to localStorage. Load/delete inline UI. |
| 2026-04-12 | — | Buildable radiate animation on KEK selection + auto-enable Solar Buildable Areas layer | Within-boundary (green) pulses first, then remote (teal) 1s later. 4.5s total. L10-adjacent spatial storytelling. |
| 2026-04-12 | — | Buildable legend in RasterLegend: in-boundary green, remote teal, 50km radius | Color distinction: green = inside KEK (no grid cost), teal = remote 50km (needs connection) |
| 2026-04-12 | — | Renamed "Gap" → "LCOE Gap" across ScoreDrawer, DataTable, QuadrantChart, walkthrough | Clearer labeling: "LCOE Gap to BPP", "LCOE Gap to Tariff", "LCOE Gap (%)" |
| 2026-04-12 | — | M15: Multi-substation comparison in ScoreDrawer Grid tab | `/api/kek/{id}/substations` computes per-substation costs (connection, upgrade, transmission, LCOE) for top 3. `SubstationComparison.tsx` side-by-side table. Map markers rank-coded: gold (rank 1), silver (rank 2), cyan (rank 3). |
| 2026-04-12 | — | ScoreDrawer tab reorganization: 6 story-focused tabs with ~35 info badges | Renamed: KEK Info→Overview, Resource→Solar, LCOE→Economics, Pipeline→Grid. Each tab answers one question. Content reshuffled: LCOE bands→Solar, grid infra→Grid, captive power→Demand, carbon/GEAS→Economics. SectionHeader + ColoredStatRow components. WalkthroughModal updated. |
| 2026-04-13 | — | V3.3 physics: BESS bridge-hours (14h), round-trip efficiency (87%), firm solar coverage metrics | MacKay-grounded storage model: `bess_bridge_hours()`, `firm_solar_metrics()`. 4 new scorecard fields. 12 new tests. |
| 2026-04-13 | — | P4 Energy Balance chart in ScoreDrawer Overview tab | MacKay-style dual stacked bars (demand day/night vs supply solar/gap) with dynamic summary. `EnergyBalanceChart.tsx`. |
| 2026-04-13 | — | ScoreDrawer UX reorg: "so what" subtitles, Flags→Action, BPP before Tariff, RUPTL moved to Action tab | Every SectionHeader gets decision-relevant subtitle. Coverage bars consolidated. Firm coverage metrics removed from Overview At a Glance (now in Energy Balance). |
| 2026-04-13 | — | V3.4 P5: Panel degradation in LCOE (0.5%/yr midpoint approximation) | `lcoe_solar()` now includes `degradation_annual_pct` param. Factor = 0.9325 over 27yr. LCOE ~7% higher. Source: NREL Jordan & Kurtz 2013. |
| 2026-04-13 | — | V3.4 P6: Power factor in capacity assessment (MVA→MW via PF 0.85) | `capacity_assessment()` and `substation_upgrade_cost_per_kw()` now convert MVA to MW before comparison. Source: PLN grid code PF 0.85 minimum. |
| 2026-04-14 | — | Layer 3 P0-P1: CBAM exposure detection + cost trajectory + adjusted competitive gap | 3-signal detection (12/25 KEKs), `CbamTrajectoryChart` with per-product breakdown, `cbam_adjusted_gap_pct` column. See [Layer 3 spec](docs/layer3_green_industrial_products_spec.md). |
| 2026-04-14 | — | Layer 3 P2: `cbam_urgent` action flag + CBAM assumption sliders + table filter | Overrides `not_competitive` when CBAM-adjusted gap < 0. Certificate price (€30-150) + EUR/USD sliders. Amber CBAM-only toggle in table. |
| 2026-04-15 | — | Layer 3 P2: CBAM 2030 cost column + 2030 crossover year marker | `cbam_cost_2030_usd_per_tonne` column (amber $/t), `ReferenceLine` at 2030 ("50% exposed") on trajectory chart. |
| 2026-04-15 | — | Documentation overhaul: DESIGN.md updated to reflect React/Vite/TypeScript SPA, 4 energy modes, 14 map layers, 19 table columns, 14 action flags, CBAM Layer 3 | Previous spec described Dash/dcc/dmc architecture with 4 bottom tabs and 5 map layers. |
| 2026-04-17 | — | **V4.0 Industrial Parks Expansion — 25 KEKs → 48 sites.** Added 23 Priority 1 industrial sites (7 steel, 8 cement, 1 aluminium, 1 copper smelter, 3 fertilizer, 3 non-KEK nickel). | Indonesia's industrial CO₂ comes overwhelmingly from sites outside KEK boundaries. KEK-only screening missed the biggest point-source emitters. |
| 2026-04-17 | — | `site_type` / `sector` columns + dropdown filters added to DataTable; `zone_classification` replaces legacy `kek_type` | Discriminator drives registry-based rendering in ScoreDrawer; sector filter enables sectoral decarbonization views. |
| 2026-04-17 | — | `SiteMarkers.tsx` (renamed from `KekMarkers.tsx`) renders site_type-specific shapes: circle (KEK), square (KI), diamond (standalone), hexagon (cluster) | Visual differentiation on the map separates KEK-mode proximity sites from direct-match industrial sites. |
| 2026-04-17 | — | ScoreDrawer identity section: registry-driven via `SITE_TYPES[site_type].identityFields` in `frontend/src/lib/siteTypes.ts` | Adding a new site type (e.g., "mining_concession") is now a 1-entry dict change in both Python `site_types.py` and TS `siteTypes.ts` — no `if/else` blocks in the 2,200-line drawer. |
| 2026-04-17 | — | `SectorSummaryChart.tsx` added to bottom drawer — CBAM cost trajectory + 2030 demand by sector + action-flag distribution table | Policy Maker persona needs sector-level rollups (steel, cement, aluminium, fertilizer, nickel, mixed) to see where the biggest decarbonization levers sit. |
| 2026-04-17 | — | State slice renames: `selectedKek` → `selectedSite`, `filteredKekIds` → `filteredSiteIds` | Terminology follows the data model — store is site-agnostic across all four site_types. |
| 2026-04-17 | — | API route renames: `/api/kek/{kek_id}/*` → `/api/site/{site_id}/*` (polygon, buildable, substations) | Clean break with no alias; frontend + backend deploy together, no public API consumers. |
| 2026-04-17 | — | Runtime validation in `/api/scorecard`: every `identityFields` column in the registry must exist in the response payload | Fails fast if Python and TypeScript registries drift. Catches rename bugs at the API boundary instead of in the UI. |
| 2026-04-17 | — | CBAM coverage: 12/25 KEKs → 35/48 sites (12 KEK via 3-signal + 23 industrial via direct `cbam_product_type`) | Industrial expansion's direct-mode dispatch via `SITE_TYPES[site_type].cbam_method` unlocks CBAM exposure for every standalone/cluster plant with a known product type. |
| 2026-04-17 | — | Header title: "Indonesia KEK Power Competitiveness" → "Indonesia Industrial Decarbonization" | Scope is no longer KEK-only; the dashboard is now Indonesia's first open-source industrial decarbonization planning platform. |
| 2026-04-17 | — | **V4.1 Tracker-driven site selection — 48 → 79 sites.** `build_industrial_sites.py` now programmatically unions GEM Global Cement Plant Tracker (32 operating), GEM Global Iron & Steel Plant Tracker (7 active), CGSP Nickel Tracker (10 Integrated Industrial Area parents, 5km KEK exclusion + 20km child aggregation), and a residual manual CSV (5 rows: 2 aluminium + 3 fertilizer, `source_url` required — loader raises if missing). | Hand-curated site lists aren't reproducible. Trackers update quarterly; pipeline-driven selection means refreshing a CSV from GEM/CGSP regenerates the universe. Residual manual CSV is the documented fallback for sectors without a tracker. |
| 2026-04-17 | — | CBAM coverage: 35/48 → 66/79 sites (12 KEK via 3-signal + 54 industrial via direct `cbam_product_type`) | Tracker expansion brings 32 cement plants and 10 nickel IIA clusters into CBAM scope, which were previously invisible. |
| 2026-04-17 | — | `fct_lcoe` row count: 864 → 1,422 (79 × 9 WACC × 2 scenarios). Test assertions parameterized as `len(dim_sites) * 18`, never hardcoded. | Row-count drift was the most common rename-era bug; parameterizing against `dim_sites` length fixes it permanently. |
| 2026-04-18 | — | **Ammonia + petrochemical scaffolding** (no rows). `Sector` enum extended; demand intensities + CBAM 2.3 tCO₂/t (ammonia, ICGD gas-SMR) wired in; `SectorSummaryChart` reserves rollup colors (ammonia teal, petrochemical purple). Site rows deferred to TODOS M28/M29 pending top-down universe discovery (state-holding + association + government-filing + trade-stat intersection). | First attempt at hand-picking ammonia rows missed Pupuk Kaltim Bontang (Indonesia's largest ammonia plant). Reverting and waiting for a systematic universe-discovery pass keeps the dataset honest about completeness. |
| 2026-04-18 | — | CBAM scope unchanged (66/79). Ammonia calibration (CN 2814 fertilizer basket, 2.3 tCO₂/t Scope 1) sits ready in the cost model for when M28 ships. Petrochemical will remain **intentionally excluded** per EU CBAM Annex I once M29 lands — blank `cbam_product_type`, electricity demand still flows through LCOE/grid analysis. | Calibrate the model first, ingest the universe second. Avoids re-doing CBAM math when the universe expands. |
| 2026-04-18 | — | `fct_lcoe` row count unchanged at 1,422 (79 × 9 × 2). Test count 532. | No row-count change since site count didn't change. |
| 2026-04-18 | — | **Fertilizer universe closure (M26).** 4-source intersection gate (state holdings + APPI + ESDM gas allocations + BPS/Comtrade) recorded in `data/industrial_sites/fertilizer_universe_v1.csv`. Added 2 missing Pupuk sites to `priority1_sites.csv`: **Pupuk Kujang (Cikampek, West Java)** and **Pupuk Iskandar Muda (Lhokseumawe, Aceh)**. Site count 79 → 81 (25 KEK + 46 standalone + 10 cluster). Fertilizer rows 3 → 5 (full Pupuk Indonesia operating fleet). `fct_lcoe` 1,422 → 1,458 rows. CBAM exposed 66/79 → 68/81. | Hand-picking missed 2 of 5 Pupuk subsidiaries. Documenting the discovery gate in a versioned CSV makes the universe auditable, not just the rows we happened to include. |
| 2026-04-18 | — | **CBAM `CBAM_RE_ADDRESSABLE_FRACTION` fix (M30).** `src/assumptions.py` gets a new dict (cement 0.12, fertilizer/ammonia 0.10, steel_bfbof 0.80, else 1.0). `src/dash/logic/cbam.py::compute_cbam_trajectory` multiplies Scope 2 savings by the sector's fraction before rate × FX conversion. Scope 1 path unchanged. 4 new tests in `tests/test_logic_cbam.py`. Golden-master fixture `tests/fixtures/scorecard_golden.pkl` regenerated (intentional behaviour change for cement/fertilizer/ammonia savings; nickel/steel/aluminium savings unchanged). Test count 537 → 541. | `CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` is thermal-inclusive for cement and ammonia/fertilizer. Treating the full Scope 2 drop as "avoided by solar" would implicitly promise thermal electrification + RE, a larger claim than the model supports. Bounding savings to the electric share keeps the CBAM number honest. |
| 2026-04-18 | — | **Scenario Compare — Phase 5: map flip rings + ScoreDrawer Flip tab.** Sites that change economic tier under the flip scenario wear a coloured halo on the map (green = improved, red = worsened) sized just outside the CBAM amber ring, plus a second `kek-flip-pulse` layer that expands 14→26 px and fades 0.85→0 over a 2 s `requestAnimationFrame` loop. Both layers are gated on `activeTab === 'compare' && flipScorecard != null`. New 7th `Flip` tab in `ScoreDrawer` (`scoredrawer/FlipTab.tsx`) shows per-site scenario banner, tier transition, delta LCOE, gap-to-grid delta, and CBAM-urgency NEW / CLEARED chips. `ScoreDrawer` tab list tightened (`px-4 gap-0.5` → `px-3 gap-0`; per-tab `px-2.5` → `px-1.5`) with `overflow-x-auto` safety net so 7 tabs fit the 420 px drawer. | Summary-level diff in the bottom drawer didn't make it obvious *which* sites moved. Map-level visual anchoring + per-site drawer detail closes the loop from "summary says 12 sites improved" to "I can see them and drill into one." The pulse animation tested better than the static ring — it signals liveness and interactivity without being loud. |
| 2026-04-21 | — | **DESIGN.md / TAXONOMY.md cohesion pass (docs-only).** TAXONOMY: swept residual "T4" references (§0, §3, §4.5) to "B" / "B-category" per §1 rename; added `cbam_adjusted_gap_pct` row to §3 derived-metrics table. DESIGN: updated site/column counts (25 KEK / 19 cols → 81 sites / 20 cols with delivered-cost hide rule) in §2 table, bottom-drawer description, and component-choices table; extended `benchmarkMode` row in §3 state slice to flag `bpp_cbam_adjusted` / `tariff_cbam_adjusted` as deferred; added new `costBasis` slice row (deferred PR3); rewrote Economics tab field table to include Tier column (T1/T2/T3/B) and `delivered_cost_blended_usd_mwh` row; retitled §6 "Open Design Questions (all resolved)" → "Resolved Design Questions (Phase 3)" and added pointer to TAXONOMY §7 for live items; added T1-driven caveat to legacy action-flag legend; added naming-convergence note at end of §4 pointing grid-cost column variants at TAXONOMY §2.B. | DESIGN and TAXONOMY drifted: DESIGN had zero mention of "delivered" / CostBasis / T1-T3 vocabulary despite TAXONOMY being the new canonical cost-metric spec and PR2 having shipped delivered cost. TAXONOMY itself carried 6 stale "T4" references from the §1 rename. Closing the loop so the two docs read as one story. |
| 2026-04-21 | — | **DESIGN.md plan-design-review 7-pass sweep (docs-only).** Pass 1 (IA): added §2 State 3 "LCOE Drilldown" for `LcoeWaterfallModal` — previously undocumented modal layer; updated view-flow diagram to show modal path from Economics tab. Pass 2 (states): expanded §3 Interaction States table with Error (known gap, silent `console.error` today), Flip loading, Flip stale, LCOE Drilldown, Substation Utilization per-site (default, V3.8), Substation Utilization global override, Scorecard recomputing (300 ms debounce + AbortController + pulsing header dot). Pass 3 (journey): added Persona moment + Emotional beat columns to the state table so every state carries its user-outcome "why." Pass 4 (AI slop): §1 "fragmented energy landscape" → "fragmented energy market." Pass 5 (design-system alignment): added Grid tab state rows for Covered-on-site (green panel, V3.9.1), On-site coverage partial (neutral panel), RUPTL substation upgrade (blue-tinted, V3.8), No RUPTL match; expanded §3 Grid tab field table with new conditional panels, `within_boundary_coverage_pct/effective_pct`, inline `wb_buildout_footprint_ratio` slider, RUPTL upgrade plan panel, `substation_utilization_pct_effective` + full RUPTL field family, `meaningful_share_pct` slider; added Substation utilization / WB buildout footprint ratio / Meaningful share threshold rows to the §3 Assumption Sliders table. Pass 6 (a11y): added new §6.5 "Accessibility Floor (MVP)" — Esc on modal + drawer, Tab order across 7 ScoreDrawer tabs, slider arrow/Home/End support, visible focus rings; ARIA polish + map marker keyboard click flagged as deferred to v2. Pass 7 (decisions): added slider-change contract note under §3 Assumption Sliders documenting 300 ms debounce + AbortController cancellation + pulsing-dot loading indicator. | Post full-staleness audit, DESIGN.md matched live terminology but still omitted 5 shipped V3.8/V3.9.1 UI features (`LcoeWaterfallModal`, Substation Utilization dual-mode slider, Grid tab coverage panels, `wb_buildout_footprint_ratio` slider, RUPTL per-substation upgrade panel). 7-pass review surfaced them plus three new doc gaps (error UX, a11y floor, recompute contract). All closed so this branch ships with DESIGN.md at 10/10 on every pass. |
| 2026-04-21 | — | **DESIGN.md full staleness audit sweep (docs-only).** Title + status line: "Indonesia KEK Power Competitiveness" → "Indonesia Industrial Decarbonization"; V3.6/2026-04-15 → V3.7/2026-04-21; added 81-site + 2D-classification + Scenario-Compare scope. §1 Problem Statement rewritten (25 KEKs → 81 industrial sites; 4 → 5 audiences with CBAM-exposed industrial investors added). §2: "25 KEKs" → "81 sites" everywhere; "6 tabs" → "7 tabs"; "KEK click" → "site click"; layout ASCII + view-flow diagram swept. §3 state slice table expanded with `selectedSite`, `filteredSiteIds`, `flipAssumptions`, `flipPreset`, `flipScorecard`, `flipLoading`, `flipStale`, `activeTab`, `drawerOpen`, `walkthroughPersona`, `flyToTarget`. Data-flow block "25 rows × ~80 fields" → "81 rows × ~80 fields"; "19 columns" → "20 columns". Component choices: ScoreDrawer 7 tabs; marker shapes by `site_type` (circle/square/diamond/hexagon); amber CBAM + flip halo layers; 50 km radius on site selection. Interaction states: "All 25 KEK markers" → "All 81 site markers"; KEK routes → site routes (`/api/kek/*` → `/api/site/*`); Flip tab visible when Scenario Compare active. ScoreDrawer tab-fields section: Overview/Grid/Industry/Action tabs all swept from "KEK" → "site" wording; new Flip tab section added (scenario banner, tier transition, delta LCOE, delta gap-to-grid, CBAM chips, `useFlipDiff`/`computeFlipDiff`). §4 2D classification: "KEKs are now classified" → "Sites are now classified"; added marker-shape + flip-halo bullets; infrastructure-readiness + legacy-action-flag rows swept. §4.5 data-quality table: "all 25 KEKs" → "all 81 sites". §5 precomputed table: `fct_kek_resource.csv` → `fct_site_resource.csv`; `fct_kek_demand.csv` → `fct_site_demand.csv`; "450 rows" → "1,458 rows (81 × 9 × 2)"; "~5ms for 25 KEKs × 2 scenarios" → "~5ms for 81 sites × 2 scenarios". §5 WACC subsection: `dcc.Slider` → "React range slider". §5 demand-override hook: `fct_kek_demand` → `fct_site_demand`. §7 CBAM table: "12/25 KEKs exposed" → "68/81 sites exposed" with dual-mode dispatch explanation (12 KEK 3-signal + 56 industrial direct); "Amber toggle filters to 12 exposed KEKs" → "68 exposed sites"; "exposed KEKs" → "exposed sites" in visual-indicators row and connection-to-existing-features bullets. §8 endpoints table: "Recompute all 25 KEKs" → "Recompute all 81 sites"; `/api/kek/{id}/polygon` → `/api/site/{id}/polygon`; `/api/kek/{id}/substations` → `/api/site/{id}/substations`; boundary-polygon description notes KEK polygon vs circular marker for non-KEK. | Layered on top of the morning cohesion pass: DESIGN still carried KEK-era terminology, 25-site counts, Dash `dcc.Slider` references, pre-V4.0 view-flow diagrams, and 6-tab ScoreDrawer descriptions despite the 2026-04-17 industrial expansion (V4.0/V4.1), 2026-04-18 Scenario Compare Phase 5 (7th Flip tab), and 2026-04-19 API route renames having all shipped. Audit of the file against the live codebase (`frontend/src/store/dashboard.ts`, `src/api/main.py`, `SITE_TYPES` registry) surfaced 15 findings; this row closes the 6 HIGH ones plus the MED string swaps that fell out naturally. |
