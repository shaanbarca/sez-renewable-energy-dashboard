# Design — Indonesia KEK Power Competitiveness Dashboard

**Status:** V3.6 design spec (2026-04-15). React + Vite + TypeScript SPA with FastAPI backend. Map-forward layout, 4 energy modes, 14 map layers, CBAM Layer 3.
**Related:** [PERSONAS.md](PERSONAS.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [PLAN.md](PLAN.md) | [Layer 3 Spec](docs/layer3_green_industrial_products_spec.md)
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
- [§6 Open Design Questions (all resolved)](#6-open-design-questions-all-resolved)
- [§7 CBAM / Green Industrial Products (Layer 3)](#7-cbam--green-industrial-products-layer-3)
- [§8 Architecture Notes](#8-architecture-notes)
- [§9 Changelog](#9-changelog)

---

## §1 Problem Statement

Indonesia's 25 Special Economic Zones (KEKs) face a fragmented energy landscape: captive solar may already be cheaper than grid power at some sites, but no single tool shows which KEKs are competitive today, which are one policy lever away, and which are genuinely grid-dependent. This dashboard answers that question for the four audiences who most need it — development bank analysts, infrastructure investors, Indonesian policymakers, and IPP developers — using precomputed LCOE bands, buildable solar resource estimates, and RUPTL pipeline data joined at KEK level for the first time.

---

## §2 Information Architecture

Five named views arranged in a **map-forward layout**. The map is always visible. Other views appear as overlays (right panel, bottom drawer).

| # | View | Container | Purpose | Primary data source | Key interaction |
|---|------|-----------|---------|-------------------|----------------|
| 1 | **Overview Map** | Full-screen (always visible) | Spatial distribution of clean power competitiveness across all 25 KEKs. 14 toggle-able overlay layers. | `scorecard[].action_flag`, 4 energy modes | Click marker → zoom to KEK + show ScoreDrawer |
| 2 | **Ranked Table** | Bottom drawer (tab 1) | Sortable, filterable comparison of all 25 KEKs. 19 columns, dropdown + range filters, CBAM toggle, CSV export. | `POST /api/scorecard` response | Column sort; global search; CBAM filter; CSV export |
| 3 | **Quadrant Chart** | Bottom drawer (tab 2) | LCOE vs. grid cost proxy scatter with competitive zone shading | Scorecard LCOE + grid cost | Benchmark toggle (BPP / Tariff) |
| 4 | **KEK ScoreDrawer** | Right side panel (slides in on KEK click) | Single-zone deep-dive: 6 tabs with embedded charts (EnergyBalance, LcoeCurve, CbamTrajectory, SubstationComparison) | All scorecard fields for selected KEK | Tab between Overview / Resource / Grid / Economics / Industry / Action |
| 5 | **RUPTL Context** | Bottom drawer (tab 3) | Regional grid pipeline timing — when does PLN's solar come online near each KEK? | `GET /api/ruptl-metrics` | Region filter; scenario toggle (RE Base / ARED) |

### Layout containers

```
┌─────────────────────────────────────────────────────────────────┐
│  Indonesia KEK Power Competitiveness  [Solar|Wind|Hybrid|All]   │  ← liquid glass header
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
│                      │ 6 tabs: Overview,   │   on KEK click    │
│                      │ Resource, Grid,     │                   │
│                      │ Economics, Industry,│                   │
│                      │ Action              │                   │
│                      └─────────────────────┘                   │
├─────────────────────────────────────────────────────────────────┤
│  ═══ grab handle ═══                                            │
│  [Table] [Quadrant Chart] [RUPTL]                               │
│  Bottom drawer (~40% height, translucent dark glass)            │
│  OPEN BY DEFAULT. Toggle via grab handle.                       │
└─────────────────────────────────────────────────────────────────┘
```

All floating panels (Assumptions, Layer Control, Raster Legends) are draggable to avoid overlapping map features.

### Interaction states (2 states + persistent elements)

See mockups in [docs/designs/2026-04-dashboard-refresh/](docs/designs/2026-04-dashboard-refresh/).

**Persistent UI elements** (always visible in both states):
- **Header bar**: Liquid glass overlay (`backdrop-filter: blur(48px)`). Title + energy mode toggle (`EnergyToggle`: Solar / Wind / Hybrid / Overall) + benchmark toggle (BPP / Tariff) + map style selector
- **Assumptions panel** (top-left, draggable): Compact summary of WACC, CAPEX, Lifetime, FOM. Expandable to Tier 1/2/3 sliders including BESS CAPEX, CBAM certificate price, EUR/USD rate. Scenario Manager (save/load up to 3 named scenarios to localStorage).
- **Layer control** (draggable): Toggle panel for 14 map overlay layers. Energy mode auto-shows/hides relevant layers (e.g. solar mode hides wind layers).
- **Action flag legend** (top-right): Color-coded legend for all 14 action flags (see §4)
- **Bottom drawer** (open by default, collapsible via grab handle): Translucent dark glass panel (~40vh). Contains 3 tabs:
  1. Ranked Table — 19 columns, TanStack Table v8, dropdown + range filters, global search, CBAM-only toggle, CSV export
  2. Quadrant Chart — Recharts scatter, LCOE vs grid cost with competitive zone shading
  3. RUPTL Context — Recharts grouped bar chart of planned solar additions by region and year

**State 1 — National view** (default) ([state-1-default-map.png](docs/designs/2026-04-dashboard-refresh/state-1-default-map.png)):
Full-screen dark map (MapLibre GL JS via `react-map-gl`) with all 25 KEK markers color-coded by action flag. Markers pulse on first load (~5s breathing animation) to signal interactivity. No KEK selected. All persistent elements visible. Drawer open by default. 4 map style options: Dark, Light, Voyager, Satellite.

**State 2 — Zoomed KEK** ([state-2-kek-zoomed.png](docs/designs/2026-04-dashboard-refresh/state-2-kek-zoomed.png)):
Triggered by clicking a KEK marker on map or a row in the ranked table.
- Map flies to fit the selected KEK polygon (`flyTo` with bounding box padding)
- KEK polygon boundary rendered (action-flag color outline, 0.15 opacity fill) via `GET /api/kek/{id}/polygon`
- 50km radius circle renders around KEK centroid (visualizes captive solar siting radius)
- Buildable area radiate animation: within-boundary (green) pulses first, then remote (teal) 1s later
- Solar Buildable Areas layer auto-enables on KEK selection
- PLN substations within radius: rank-coded markers (gold = rank 1, silver = rank 2, cyan = rank 3) from `GET /api/kek/{id}/substations`
- Selected KEK marker enlarged with yellow halo (28px outer + 20px inner)
- ScoreDrawer slides in from right (6 tabs: Overview / Resource / Grid / Economics / Industry / Action)
  - Close (X) keeps spatial context (radius, polygon visible). Separate from KEK deselection.
- Bottom drawer still available. RUPTL tab auto-filters to this KEK's grid region.
- Click a different KEK in table → transitions directly (no return to State 1 first)
- All slider changes update scorecard + map markers + polygon fill live in zoomed state

### View flow (updated)

```
National View (State 1)
    │ click KEK marker or table row
    ▼
Zoomed KEK (State 2)
    │ polygon + 50km radius + substations + ScoreDrawer side panel
    │ close drawer (X) → keeps spatial context; deselect KEK → back to State 1
    │ click different KEK in table → stay in State 2, switch KEK
    │
    │ RUPTL tab auto-filters to KEK's region
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

*Changed 2026-04-08: Map-forward redesign. Changed 2026-04-15: Updated to reflect React/Vite/TypeScript SPA, 4 energy modes, 3 bottom tabs (Flip Scenario removed), 14 map layers.*

---

## §3 Component Architecture

### State management

Single Zustand store (`frontend/src/store/dashboard.ts`):

| Slice | Content | Drives |
|-------|---------|--------|
| `assumptions` | All user-adjustable model params (CAPEX, FOM, lifetime, WACC, BESS CAPEX, CBAM price, EUR/USD). Defaults from `GET /api/defaults`. | `POST /api/scorecard` recomputation |
| `thresholds` | Flag thresholds (PVOUT, plan-late, GEAS, resilience gap, reliability) | Included in scorecard POST |
| `scorecard` | Array of `ScorecardRow` (25 KEKs, ~80 fields each) from API response | Table, map markers, ScoreDrawer, charts |
| `selectedKek` | Currently selected `kek_id` (nullable) | ScoreDrawer content, map highlight, polygon/radius |
| `energyMode` | `solar` / `wind` / `hybrid` / `overall` | Action flag display, layer visibility, ScoreDrawer fields |
| `benchmarkMode` | `bpp` / `tariff` | Grid cost column in table, competitive gap calculation |
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
  src/dash/logic.py: compute_scorecard_live()
  (LCOE, action flags, CBAM, wind, hybrid, grid costs — all recomputed)
         │
         ▼
  JSON response: ScorecardRow[] (25 rows × ~80 fields)
         │
         ├──► Map marker colours (action_flag per KEK)
         ├──► Ranked Table (19 columns, filters, sort)
         ├──► Quadrant Chart (LCOE vs grid cost scatter)
         └──► ScoreDrawer (selected KEK detail + embedded charts)

User clicks KEK marker or table row
         │
         ├──► GET /api/kek/{id}/polygon → boundary GeoJSON
         ├──► GET /api/kek/{id}/substations → nearby substations with costs
         └──► ScoreDrawer slides in with selected KEK data

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
| Ranked table | TanStack Table v8 (`@tanstack/react-table`) | 19 columns. Dropdown filters (categorical), range filters (numeric), global search, CBAM-only toggle, CSV export. Bottom drawer tab 1. |
| RUPTL chart | Recharts `BarChart` (grouped) | Region filter, scenario toggle. Bottom drawer tab 3. |
| ScoreDrawer | React slide-in panel (right side) | 6 tabs: Overview / Resource / Grid / Economics / Industry / Action. Close (X) separate from KEK deselect. |
| Bottom panel | `BottomPanel` with grab handle | Translucent dark glass (~40vh). 3 tabs. Toggle open/closed. |
| Energy toggle | `EnergyToggle` (4 modes) | Solar / Wind / Hybrid / Overall. Changes action flags, layer visibility, ScoreDrawer fields. |
| Embedded charts | 4 chart components in ScoreDrawer | `EnergyBalanceChart` (Overview), `LcoeCurveChart` (Economics), `CbamTrajectoryChart` (Industry), `SubstationComparison` (Grid) |
| Scenario manager | `ScenarioManager` in AssumptionsPanel | Save/load up to 3 named scenarios. localStorage persistence. |
| Methodology modal | `MethodologyModal` | Renders `METHODOLOGY_CONSOLIDATED.md` in-app with KaTeX math notation. |
| KEK markers | MapLibre circle layers | Color-coded by action flag. Pulse animation on first load. Yellow halo on selection. |
| Buildable polygons | MapLibre fill+line layers | Clickable: popup shows area (ha), avg PVOUT, max capacity (MWp). Green = in-boundary, teal = remote. |
| 50km radius | MapLibre circle layer | Renders on KEK selection. Visualizes captive solar siting radius. |
| Substation markers | MapLibre layers (rank-coded) | Gold (rank 1), silver (rank 2), cyan (rank 3) in zoomed view. |

### Assumption sliders

All sliders configured via `GET /api/defaults` (ranges, steps, defaults from `src/dash/constants.py`).

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
| CBAM certificate price | 2 | €30–150, step 5 | 80 | CBAM cost trajectory |
| EUR/USD rate | 2 | 1.00–1.30, step 0.01 | 1.10 | CBAM cost conversion |
| IDR/USD rate | 2 | 14,000–18,000, step 100 | 15,800 | Grid cost conversion |
| PVOUT threshold | 3 | 1,200–1,600, step 50 | 1,350 | no_solar_resource cutoff |
| Reliability requirement | 3 | 0–1, step 0.05 | 0.50 | invest_resilience trigger |

### Interaction States

| State | Trigger | Display |
|-------|---------|---------|
| Loading | App startup, `GET /api/defaults` + initial `POST /api/scorecard` | Loading overlay while data fetches |
| National | Default after load | All 25 KEK markers, pulsing animation (~5s), drawer open |
| Selected KEK | Click marker or table row | Yellow halo, flyTo polygon bbox, 50km radius, ScoreDrawer slides in |
| Drawer Open | Default; toggle via grab handle | Translucent bottom drawer (~40vh) with 3 tabs |
| Drawer Closed | Toggle grab handle | Only handle bar visible, map expands to full height |
| Empty filter | Table filters produce zero rows | Empty state message in table area |
| Partial data | Null cell values | Em-dash "—" per cell. Never hides rows with partial data. |

### ScoreDrawer Tab Fields

Fields sourced from `POST /api/scorecard` response (~80 fields per KEK). See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full column definitions.

**Overview tab** — "What's the story for this KEK?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `kek_name`, `province`, `kek_type`, `area_ha` | KEK identity | Header section |
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

**Grid tab** — "How does this KEK connect to the grid?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `grid_integration_category` | Integration category | within_boundary / grid_ready / invest_transmission / invest_substation / grid_first |
| 3 distances | Solar→Sub, Sub→KEK, Solar→KEK | km |
| `line_connected`, `inter_substation_connected` | Grid line connectivity | Boolean (geometric check against `pln_grid_lines.geojson`) |
| `capacity_assessment` | Substation capacity | Green/yellow/red traffic light |
| **SubstationComparison** | Top 3 substations | Per-substation costs (connection, upgrade, transmission, all-in LCOE). Rank-coded map markers. |

**Economics tab** — "What does the energy cost?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `lcoe_low/mid/high_usd_mwh` | LCOE variance | 3 WACC scenarios |
| Battery storage | BESS CAPEX slider (100-500 $/kWh), sizing slider (1-16h) | Live recomputation of `battery_adder_usd_mwh`. "Reset to auto" restores per-KEK sizing. |
| `hybrid_lcoe_usd_mwh`, `hybrid_bess_hours` | Hybrid BESS reduction | % reduction from wind nighttime coverage |
| `carbon_breakeven_usd_tco2` | Carbon breakeven price | USD/tCO2 |
| `green_share_geas` | GEAS green share | % of 2030 demand met by allocated RE |
| **LcoeCurveChart** | LCOE vs project scale | Shows how LCOE drops as capacity increases (transmission cost spreading) |

**Industry tab** — "What industry is here and what's the CBAM exposure?"
| Field | Display label | Notes |
|-------|--------------|-------|
| `demand_mwh_2030` | Demand estimation | MWh |
| Solar/wind generation capacity | 50km radius + within-boundary | MWh |
| `captive_coal_count`, `captive_coal_mw` | Captive coal plants | GEM tracker |
| `nickel_smelter_count`, `dominant_process_type` | Nickel smelters | CGSP tracker |
| `steel_plant_count`, `steel_total_tpa` | Steel plants | GEM tracker |
| `cement_plant_count`, `cement_total_mtpa` | Cement plants | GEM tracker |
| `cbam_exposed`, `cbam_product_type` | CBAM exposure | 3-signal detection: process type + plant counts + KEK sectors |
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
| RUPTL context | Regional grid pipeline | Planned capacity additions for this KEK's grid region |

---

## §4 Colour & Visual Language

### 2D Classification Visual System (V3.7)

KEKs are now classified on two independent axes plus overlay modifier badges. The map encodes all three dimensions on a single circle marker:

- **Circle fill** = Economic Tier (how viable is RE?)
- **Circle stroke** = Infrastructure Readiness (what infrastructure exists?)
- **Outer ring** = Modifier Badge (CBAM urgency, plan-late, storage)

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
| `within_boundary` | Green | `#4CAF50` | Solar buildable inside KEK boundary |
| `grid_ready` | Blue | `#42A5F5` | Existing grid infrastructure sufficient |
| `invest_transmission` | Orange | `#FF9800` | Build transmission line to KEK |
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

| Flag | Colour | Hex | Meaning |
|------|--------|-----|---------|
| `solar_now` | Green | `#2E7D32` | Solar LCOE < grid cost. Act now. |
| `cbam_urgent` | Amber | `#FF6F00` | CBAM-adjusted gap < 0. RE + avoided border tax beats grid. See [Layer 3 spec](docs/layer3_green_industrial_products_spec.md). |
| `wind_now` | Dark Green | `#1B5E20` | Wind LCOE < grid cost. |
| `hybrid_now` | Green | `#2E7D32` | Hybrid solar+wind all-in LCOE < grid cost. |
| `invest_resilience` | Orange | `#F57C00` | Within 20% of parity + high reliability requirement. |
| `invest_battery` | Light Orange | `#FFA726` | Competitive with battery storage investment. |
| `invest_transmission` | Blue | `#0277BD` | Solar near substation but KEK far. Build transmission. |
| `invest_substation` | Teal | `#00838F` | KEK near substation but solar far. Upgrade substation. |
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
| Filtered resource | "(filtered)" label | `resource_quality = "filtered"` — all 25 KEKs currently |
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

---

## §5 Data Decisions for the UI

### What is precomputed vs. computed live

| Data | Approach | Why |
|------|----------|-----|
| **Precomputed (pipeline)** | | |
| Solar resource (PVOUT, CF) | `fct_kek_resource.csv` loaded at startup | Requires GeoTIFF processing; cannot be live |
| Substation distances | `fct_substation_proximity.csv` loaded at startup | Requires geospatial computation |
| RUPTL pipeline | `fct_ruptl_pipeline.csv` loaded at startup | Static government data |
| Grid cost proxy | `fct_grid_cost_proxy.csv` loaded at startup | Static regulatory data |
| Demand estimates | `fct_kek_demand.csv` loaded at startup | User can override via `resolve_demand()` |
| `fct_lcoe.csv` (450 rows) | Still produced by pipeline for reproducibility/export | Default-assumption reference; dashboard computes live instead |
| **Live (dashboard callback)** | | |
| LCOE bands (all scenarios) | `compute_lcoe_live()` in `src/dash/logic.py` | User adjusts CAPEX, FOM, lifetime, WACC, gen-tie, lease via sliders. ~5ms for 25 KEKs × 2 scenarios |
| Competitive gap | `solar_competitive_gap()` from `basic_model.py` | Recalculated when LCOE or grid benchmark changes |
| Action flags | `action_flags()` + `invest_resilience()` from `basic_model.py` | Recalculated when LCOE or thresholds change |
| Carbon breakeven | `carbon_breakeven_price()` from `basic_model.py` | Recalculated when LCOE or grid cost changes |
| GEAS green share | `geas_baseline_allocation()` from `basic_model.py` | Recalculated if demand override changes |
| Flip scenario | Filter live LCOE results by gap threshold | Client-side filter on live-computed data |

### WACC slider behaviour

The dashboard ships with nine precomputed WACC values (4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20%). The WACC selector is a `dcc.Slider` with snap marks at each value, default = 10%. This covers the full range from DFI concessional financing (4–6%) through SE Asia equity ceiling (20%). No continuous interpolation is needed. See [METHODOLOGY_CONSOLIDATED.md §6](docs/METHODOLOGY_CONSOLIDATED.md) for the full WACC methodology.

### Demand override hook

The `demand_mwh_user` column in `fct_kek_demand` is nullable (`Float64`). If a user enters a custom demand value in the Scorecard panel, the app calls `resolve_demand(demand_mwh_modelled, demand_mwh_user)` from `src/model/basic_model.py` to get the effective demand, then recalculates `green_share_geas` server-side and updates the scorecard display only (does not write back to CSV).

---

## §6 Open Design Questions (all resolved)

All resolved during Phase 3 autoplan review (2026-04-07):

| # | Question | Resolution | Decision # |
|---|----------|-----------|------------|
| 1 | **WACC slider** | ✅ **9-value `dcc.Slider`** with snap points at [4,6,8,10,12,14,16,18,20], default=10%. Covers full concessional-to-equity range. | #21, #27 |
| 2 | **Map tile provider** | ✅ **Mapbox dark-v11** via dash-leaflet. Token loaded from `.env` via python-dotenv. Native `dl.LayersControl` for overlay toggling. | — |
| 3 | **Mobile layout** | ✅ **Desktop-only for MVP**. Primary users are analysts with laptops. Responsive deferred to v2 (see [TODOS.md](TODOS.md) L7). | — |
| 4 | **Provisional data warning** | ✅ **Dagger (†) per cell**. Cell-level precision; no banner noise. | — |
| 5 | **Export format** | ✅ **CSV + GeoJSON**. DFI investors need GeoJSON for site team handoff (see [PERSONAS.md §DFI Investor](PERSONAS.md)). | — |

---

## §7 CBAM / Green Industrial Products (Layer 3)

**Feature spec:** [docs/layer3_green_industrial_products_spec.md](docs/layer3_green_industrial_products_spec.md)

EU CBAM entered its definitive phase January 2026. Indonesian exporters of iron, steel, aluminum, and fertilizers to the EU pay a carbon price at the border. This feature layer adds CBAM exposure analysis to the dashboard, transforming it from an energy analysis tool into a trade competitiveness tool.

### What shipped (all P0-P2 items from spec)

| Feature | Location | Status |
|---------|----------|--------|
| CBAM exposure flag per KEK | Scorecard + table column | ✅ 12/25 KEKs exposed. 3-signal detection: (1) nickel process types (RKEF/FeNi → iron_steel), (2) plant counts (steel_plant_count > 0, cement_plant_count > 0), (3) KEK business sectors. |
| CBAM cost trajectory 2026-2034 | `CbamTrajectoryChart` in ScoreDrawer Industry tab | ✅ Per-product breakdown (nickel_rkef, steel_eaf, steel_bfbof, cement, aluminium, fertilizer). Free allocation phase-out: 97.5% (2026) → 0% (2034). |
| 2030 crossover year marker | ReferenceLine on trajectory chart | ✅ Dashed line at 2030 with "50% exposed" label. 2030 = inflection point (51.5% free allocation remaining). |
| CBAM-adjusted competitive gap | `cbam_adjusted_gap_pct` column in table | ✅ `(LCOE - grid_cost - cbam_savings_per_mwh) / grid_cost × 100`. Negative = RE + avoided border tax beats grid. |
| CBAM cost per tonne at 2030 | `cbam_cost_2030_usd_per_tonne` column in table | ✅ Amber-colored $/t values. Range-filterable. |
| `cbam_urgent` action flag | Action flag system | ✅ Fires when CBAM-adjusted gap < 0. Overrides `not_competitive` and `invest_resilience`. |
| CBAM assumption sliders | AssumptionsPanel (Tier 2) | ✅ Certificate price (€30-150), EUR/USD rate (1.00-1.30). |
| CBAM-only table filter | DataTable toolbar | ✅ Amber toggle filters to 12 exposed KEKs. |
| CBAM visual indicators | Map + Table + Legend | ✅ Map: amber ring (`#FF6F00`) around CBAM-exposed marker dots + "CBAM" label in hover tooltip. Table: amber outer ring around action flag dot for exposed KEKs. Legend: `cbam_urgent` shown as ring (not solid dot) with hover description. |

### Connection to existing features

- **Action flags:** `cbam_urgent` is ranked above `not_competitive` in all 4 energy mode hierarchies. A KEK that would be `not_competitive` on energy alone becomes `cbam_urgent` if CBAM savings make RE cheaper.
- **Competitive gap:** CBAM savings (~$33-34/MWh for exposed KEKs) are subtracted from the gap calculation. Converts energy cost comparisons into trade cost comparisons.
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

`src/api/` wraps existing pipeline modules. All computation happens server-side in `src/dash/logic.py`.

**Key endpoints:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/defaults` | GET | Default assumptions, thresholds, slider configs |
| `/api/scorecard` | POST | Recompute all 25 KEKs with user assumptions |
| `/api/layers/{name}` | GET | Lazy-load GeoJSON layers (14 available) |
| `/api/kek/{id}/polygon` | GET | KEK boundary polygon |
| `/api/kek/{id}/substations` | GET | Substations within radius with per-substation costs |
| `/api/ruptl-metrics` | GET | RUPTL pipeline metrics by region |
| `/api/methodology` | GET | Raw METHODOLOGY_CONSOLIDATED.md for in-app rendering |

### Business logic extraction

All computation in `src/dash/logic.py` as pure functions. `compute_scorecard_live()` takes assumptions + thresholds, returns full scorecard DataFrame. Testable with pytest, no server dependency. 402 tests cover model, pipeline, and API.

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
