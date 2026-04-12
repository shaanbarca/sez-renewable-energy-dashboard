# Design — Indonesia KEK Power Competitiveness Dashboard

**Status:** Phase 4 design spec (post design-shotgun refresh, 2026-04-08). Map-forward layout with zoomed KEK detail, bottom drawer, and RUPTL Context view.
**Related:** [PERSONAS.md](PERSONAS.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [PLAN.md](PLAN.md)
**Design mockups:** [docs/designs/2026-04-dashboard-refresh/](docs/designs/2026-04-dashboard-refresh/) (4 interaction states + 3 exploration variants)

---

## Table of Contents

- [§1 Problem Statement](#1-problem-statement)
- [§2 Information Architecture](#2-information-architecture)
- [§3 Component Architecture](#3-component-architecture)
  - [State management](#state-management)
  - [Callback architecture](#callback-architecture)
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
- [§7 Wind CF Integration](#7-wind-cf-integration)
- [§8 Architecture Notes](#8-architecture-notes)
- [§9 Changelog](#9-changelog)

---

## §1 Problem Statement

Indonesia's 25 Special Economic Zones (KEKs) face a fragmented energy landscape: captive solar may already be cheaper than grid power at some sites, but no single tool shows which KEKs are competitive today, which are one policy lever away, and which are genuinely grid-dependent. This dashboard answers that question for the four audiences who most need it — development bank analysts, infrastructure investors, Indonesian policymakers, and IPP developers — using precomputed LCOE bands, buildable solar resource estimates, and RUPTL pipeline data joined at KEK level for the first time.

---

## §2 Information Architecture

Six named views arranged in a **map-forward layout**. The map is always visible. Other views appear as overlays (right panel, bottom drawer).

| # | View | Container | Purpose | Primary data source | Key interaction |
|---|------|-----------|---------|-------------------|----------------|
| 1 | **Overview Map** | Full-screen (always visible) | Spatial distribution of clean power competitiveness across all 25 KEKs | `fct_kek_scorecard.action_flag`, `solar_competitive_gap_wacc10_pct` | Click marker → zoom to KEK + show Scorecard |
| 2 | **Quadrant Chart** | Bottom drawer (tab 2) | LCOE vs. grid cost proxy for all KEKs simultaneously — four zones visible at once | `fct_lcoe` (WACC-filtered) + `fct_grid_cost_proxy` | WACC selector updates positions live |
| 3 | **Ranked Table** | Bottom drawer (tab 1) | Sortable, filterable comparison of all 25 KEKs | `fct_kek_scorecard` | Column sort; action flag filter; CSV export |
| 4 | **KEK Scorecard** | Right side panel (slides in on KEK click) | Single-zone deep-dive: LCOE bands, resource, demand, grid context, action flag | All joined tables (one row per KEK) | Tab between Resource / LCOE / Demand / Pipeline / Flags |
| 5 | **Flip Scenario Panel** | Bottom drawer (tab 4) | "Which KEKs become competitive under changed assumptions?" | `fct_lcoe` WACC=8% columns + threshold slider | WACC selector + competitive-gap threshold slider |
| 6 | **RUPTL Context** | Bottom drawer (tab 3) | Regional grid pipeline timing — when does PLN's solar come online near each KEK? | `fct_ruptl_pipeline` | Region filter; scenario toggle (RE Base / ARED) |

### Layout containers

```
┌─────────────────────────────────────────────────────────────┐
│  Indonesia KEK Power Competitiveness  [Solar|Wind|Overall]  │  ← header bar
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐                    ┌──────────────────┐   │
│  │ Assumptions  │                    │ ACTION FLAG      │   │
│  │ WACC   10%   │    FULL-SCREEN     │ LEGEND           │   │
│  │ CAPEX  960   │       MAP          │ ● Solar Now      │   │
│  │ Life   27yr  │                    │ ● Invest Res.    │   │
│  │ FOM    7.5   │                    │ ● Grid First     │   │
│  │ [▼ expand]   │                    │ ● Plan Late      │   │
│  └──────────────┘                    │ ● Not Competitive│   │
│                                      └──────────────────┘   │
│                      ┌─────────────────────┐                │
│                      │ KEK Scorecard       │ ← slides in    │
│                      │ (right panel,       │   on KEK click  │
│                      │  only in State 2)   │                │
│                      └─────────────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  ═══ grab handle ═══                                        │
│  [Table] [Quadrant Chart] [RUPTL] [Flip Scenario]           │
│  Bottom drawer (~40% height, translucent dark glass)        │
│  OPEN BY DEFAULT. Slides up/down via grab handle.           │
└─────────────────────────────────────────────────────────────┘
```

### Interaction states (2 states + persistent elements)

See mockups in [docs/designs/2026-04-dashboard-refresh/](docs/designs/2026-04-dashboard-refresh/).

**Persistent UI elements** (always visible in both states):
- **Header bar**: Title + energy source segmented control (Solar / Wind / Overall) — `dmc.SegmentedControl`
- **Assumptions card** (top-left): Compact summary of WACC, CAPEX, Lifetime, FOM. Expandable to full Tier 1/2/3 slider panels — `dmc.Accordion` or `dmc.Collapse`
- **Action flag legend** (top-right): Color-coded legend for all 5 action flags
- **Bottom drawer** (open by default, collapsible via grab handle): Translucent dark glass panel (~40vh). Contains 4 tabs (`dmc.Tabs`):
  1. Ranked Table — sortable, filterable, CSV/GeoJSON export
  2. Quadrant Chart — LCOE vs grid cost scatter with zone shading
  3. RUPTL Context — grouped bar chart of planned solar additions by region and year
  4. Flip Scenario — before/after comparison when assumptions change

**State 1 — National view** (default) ([state-1-default-map.png](docs/designs/2026-04-dashboard-refresh/state-1-default-map.png)):
Full-screen dark map with all 25 KEK markers color-coded by action flag. No KEK selected. All persistent elements visible. Drawer open by default.

**State 2 — Zoomed KEK** ([state-2-kek-zoomed.png](docs/designs/2026-04-dashboard-refresh/state-2-kek-zoomed.png)):
Triggered by clicking a KEK `dl.CircleMarker` on map or a row in the ranked table.
- Map zooms to fit the selected KEK polygon (bounding box + padding via `polygon_bbox()`)
- KEK polygon boundary rendered via `dl.GeoJSON` (action-flag color outline, 0.15 opacity fill)
- Infrastructure markers shown within/near KEK as `dl.CircleMarker` with `dl.Tooltip`:
  - PLN substations from `data/substation.geojson` (filtered to ~50km radius via `filter_substations_near_point()`; nearest highlighted yellow)
  - Scraped infrastructure from `kek_info_and_markers.csv` → `infrastructures` JSON (green = inside SEZ, blue = outside SEZ)
- Selected KEK marker enlarged (radius 14, yellow border) to indicate selection
- "Back to National View" button appears (top-center, `dmc.Button`) to exit zoomed state
- Scorecard panel slides in from right (`dmc.Drawer`, 380px, title "KEK Scorecard", visible close X button)
  - 5 tabs: Resource / LCOE / Demand / Pipeline / Flags
  - Close (X) or click outside → zoom back to national view, return to State 1
- Bottom drawer still available — RUPTL tab auto-filters to this KEK's grid region
- Click a different KEK in table → transitions directly (no return to State 1 first)

### View flow (updated)

```
National View (State 1)
    │ click KEK marker or table row
    ▼
Zoomed KEK (State 2)
    │ polygon + infra markers + scorecard side panel
    │ "Back to National View" button OR close drawer (X) → back to State 1
    │ click different KEK in table → stay in State 2, switch KEK
    │
    │ RUPTL tab auto-filters to KEK's region
    │ slider changes → everything updates live (scorecard + map colors)
    │
Bottom Drawer (persistent, open by default, toggle via grab handle)
    ├─ Tab 1: Ranked Table → click row → State 2
    ├─ Tab 2: Quadrant Chart
    ├─ Tab 3: RUPTL Context
    └─ Tab 4: Flip Scenario

Energy Toggle (persistent, header bar) → switches Solar/Wind/Overall context
```

*Changed 2026-04-08: Map-forward redesign with 2-state model. Drawer and energy toggle are persistent UI elements, not states. Full dbc → DMC migration for consistent dark theme.*

---

## §3 Component Architecture

### State management

| Store | Content | Drives |
|-------|---------|--------|
| `dcc.Store("scorecard-data")` | Full `fct_kek_scorecard` loaded once at startup | Ranked table, map marker colours, scorecard panel |
| `dcc.Store("lcoe-data")` | Full `fct_lcoe` (450 rows: 25 KEKs × 9 WACC × 2 scenarios) loaded once at startup | Quadrant chart, flip scenario panel |
| `dcc.Store("wacc-selection")` | Current WACC value (4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20) | Quadrant chart, flip scenario, ranked table LCOE column |
| `dcc.Store("selected-kek")` | Currently selected `kek_id` | Scorecard panel content, map highlight |
| `dcc.Store("grid-benchmark")` | User-supplied grid cost override, USD/MWh (default: 63.08, I-4/TT) | Quadrant chart competitive line, ranked table competitive gap |
| `dcc.Store("user-assumptions")` | All user-adjustable model assumptions (CAPEX, FOM, lifetime, gen-tie, lease, firming, IDR/USD). Defaults from `src/assumptions.py`. | Live LCOE recomputation callback |
| `dcc.Store("user-thresholds")` | All user-adjustable flag thresholds (PVOUT, plan-late, GEAS, resilience gap, min viable, reliability). Defaults from `src/assumptions.py`. | Live action flag recomputation |

### Callback architecture

```
[Tier 1: WACC + CAPEX + Lifetime sliders] ──► user-assumptions store
[Tier 2: FOM + gen-tie + lease sliders]   ──┘
                                              │
                                              ▼
                                    compute_lcoe_live()     ← src/dash/logic.py
                                    compute_flags_live()    ← src/dash/logic.py
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                   Quadrant              Ranked table         Map colours
                    chart                                     + Scorecard

[Grid benchmark input] ──► grid-benchmark store ──► competitive gap recalc
                                                         │
                                               ┌─────────┴─────────┐
                                               ▼                   ▼
                                        Quadrant              Ranked table

[Tier 3: threshold sliders] ──► user-thresholds store ──► compute_flags_live()
                                                                │
                                                     ┌──────────┴──────────┐
                                                     ▼                     ▼
                                              Action flags            Map colours

[Demand override input] ──► server-side resolve_demand()
                                │
                                ▼
                           GEAS recalc → Scorecard panel

[Map click] ──► selected-kek store
                     │
                     ▼
              KEK Scorecard panel
```

All callbacks use `prevent_initial_call=True` except startup data loaders.

### Component choices

| Component | Implementation | Rationale |
|-----------|---------------|-----------|
| Map | `dash-leaflet.MapContainer` with Mapbox dark-v11 tiles | Full-screen, always visible. Mapbox token loaded from `.env` via python-dotenv. Native `dl.LayersControl` (bottom-left) for toggling overlays |
| Map layers | `dl.LayersControl` with `dl.Overlay` wrappers | Native Leaflet layer control (expandable checkbox panel). Overlays: Substations, KEK Boundaries, PVOUT, Solar Buildable Areas (vector polygons), Wind Speed |
| Raster overlays | `dl.ImageOverlay` inside `dl.Overlay` | Base64 PNG rasters toggled via LayersControl. Opacity 0.7 when active |
| Quadrant chart | `plotly.Scatter` with `shapes` for zone shading | Full control over quadrant lines; lives in bottom drawer tab 2 |
| Ranked table | `dash_table.DataTable` | Built-in sorting, filtering, CSV export; lives in bottom drawer tab 1 |
| RUPTL Context chart | `plotly.Bar` (grouped) with region dropdown + scenario toggle | Bottom drawer tab 3. Shows 7 regions × 10 years of planned solar capacity |
| KEK Scorecard panel | `dmc.Drawer(position="right", size="380px")` | Right-side slide-in panel, dark translucent. Title "KEK Scorecard" with visible close (X) button. `closeOnClickOutside=True` |
| Bottom drawer | `html.Div` with CSS transform + grab handle | Translucent dark glass (~40% height), slides up/down. Contains Table/Quadrant/RUPTL/Flip tabs |
| Energy toggle | `dmc.SegmentedControl` (Solar/Wind/Overall) | Header bar, right of title |
| Infrastructure markers | `dl.CircleMarker` with `dl.Tooltip` | Green (inside SEZ) / blue (outside SEZ). Shown only in State 2 (zoomed KEK view) |
| KEK polygon fill | `dl.GeoJSON` with fillOpacity style | Action-flag color at 0.15 opacity fill, 2px outline |
| KEK markers | `dl.CircleMarker` with pattern-matching `n_clicks` callback | Color-coded by action flag. Click to zoom + open scorecard |
| Back to National | `dmc.Button` (top-center, visible in State 2 only) | Clears selected KEK, closes scorecard, returns to national view |
| Scorecard cards | `dmc.Paper` (dash-mantine-components) | Clean layout in side panel, dark theme |
| WACC selector | `dcc.Slider` with marks at [4, 6, 8, 10, 12, 14, 16, 18, 20], default=10 | 9 snap points covering full concessional-to-equity range; no interpolation needed |
| Grid benchmark override | `dcc.Input(type="number")`, default=63.08, USD/MWh | Allows users to test competitive gap against a custom grid cost (e.g., negotiated PPA rate) |
| Demand override | `dcc.Input(type="number")` in Scorecard Demand tab | Calls `resolve_demand()` server-side; recalculates GEAS green share |
| CAPEX slider | `dcc.Slider`, range 600–1,500 $/kW, step 10, default=960 | **Tier 1.** Biggest LCOE driver. Triggers live LCOE recomputation |
| Lifetime slider | `dcc.Slider`, range 20–35 yr, step 1, default=27 | **Tier 1.** Third-biggest LCOE driver (via CRF). Triggers live recomputation |
| FOM slider | `dcc.Slider`, range 3–15 $/kW/yr, step 0.5, default=7.5 | **Tier 2.** Collapsible "Advanced Assumptions" panel |
| Gen-tie cost slider | `dcc.Slider`, range 2–12 $/kW-km, step 0.5, default=5.0 | **Tier 2.** Affects remote captive LCOE only |
| Substation works slider | `dcc.Slider`, range 80–250 $/kW, step 10, default=150 | **Tier 2.** Affects remote captive LCOE only |
| Transmission lease slider | `dcc.Slider`, range 3–20 $/MWh, step 1, default=10 | **Tier 2.** Affects all-in remote LCOE |
| Firming adder slider | `dcc.Slider`, range 5–20 $/MWh, step 1, default=11 | **Tier 2.** Affects firming scenario |
| IDR/USD rate | `dcc.Input(type="number")`, default=15,800 | **Tier 2.** Grid cost conversion |
| Reset to Defaults button | `dbc.Button` per tier | Resets all slider values in that tier to `assumptions.py` defaults |

### Interaction States

| State | Trigger | Display |
|-------|---------|---------|
| Loading | App startup while CSVs load into stores | ✅ `dcc.Loading` fullscreen spinner, replaced by app layout once data ready |
| Empty | Ranked Table filters produce zero matching rows | ✅ "No KEKs match the current filter. Try adjusting the action flag selection." below table |
| Error | CSV files not found at startup | ✅ Inline red `dbc.Alert`: "Data not found. Run `uv run python run_pipeline.py`." |
| Partial data | Any cell value is null (e.g., `nearest_substation_capacity_mva` for 5 KEKs) | ✅ Em-dash "---" per cell via `_val()` helper. Never hides rows with partial data. |
| Selected KEK | User clicks a KEK on map or table | ✅ Yellow halo (28px outer + 20px inner) highlights selected marker on map |
| KEK Zoomed | User clicks KEK marker or table row | Map zooms to KEK polygon bbox. Polygon fill + outline rendered. Infrastructure markers (substations, airports, ports, railways) shown. Scorecard slides in from right. |
| Drawer Open | Default state; user can also pull up after collapsing | Translucent bottom drawer (~40% height) with Table/Quadrant Chart/RUPTL/Flip Scenario tabs |
| Drawer Closed | User pushes down grab handle or clicks collapse | Only grab handle bar visible at bottom of screen. Map expands to full height. |

### Input Validation

| Input | Valid range | Invalid handling |
|-------|------------|-----------------|
| Grid benchmark (USD/MWh) | [1, 500] | Clamp to nearest bound; reject NaN/Inf; reset to 63.08 on invalid |
| Demand override (MWh) | [0, 10,000,000] | Clamp to nearest bound; reject NaN/Inf/negative; clear to show modelled value |

### Scorecard Tab Fields

Fields sourced from `fct_kek_scorecard` (57 columns). See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full column definitions.

**Resource tab:**
| Field | Display label | Unit |
|-------|--------------|------|
| `pvout_centroid` | Annual PVOUT (centroid) | kWh/kWp/yr |
| `pvout_best_50km` | Best PVOUT within 50 km | kWh/kWp/yr |
| `pvout_buildable_best_50km` | Best buildable PVOUT within 50 km | kWh/kWp/yr |
| `cf_centroid` | Capacity factor (centroid) | % |
| `cf_best_50km` | Capacity factor (best 50 km) | % |
| `buildable_area_ha` | Buildable area | ha |
| `max_captive_capacity_mwp` | Max captive capacity | MWp |
| `resource_quality` | Resource quality flag | text |
| `project_viable` | Project viable (≥ 20 MWp) | boolean |

**LCOE tab** (values update when WACC slider changes):
| Field | Display label | Unit |
|-------|--------------|------|
| `lcoe_low_usd_mwh` | LCOE (low) | USD/MWh |
| `lcoe_mid_usd_mwh` | LCOE (mid) | USD/MWh |
| `lcoe_high_usd_mwh` | LCOE (high) | USD/MWh |
| `lcoe_remote_captive_allin_low_usd_mwh` | All-in remote LCOE (low) | USD/MWh |
| `lcoe_remote_captive_allin_usd_mwh` | All-in remote LCOE (mid) | USD/MWh |
| `lcoe_remote_captive_allin_high_usd_mwh` | All-in remote LCOE (high) | USD/MWh |
| `solar_competitive_gap_pct` | Solar competitive gap | % |
| `solar_now` | Solar competitive now? | boolean |
| `invest_resilience` | Resilience investment case? | boolean |
| `carbon_breakeven_usd_tco2` | Carbon breakeven price | USD/tCO2 |

**Demand tab:**
| Field | Display label | Unit |
|-------|--------------|------|
| `demand_mwh_2030` | Estimated 2030 demand | MWh |
| `demand_mwh_user` | User override (editable) | MWh |
| `green_share_geas` | GEAS green share (2030) | % |
| `kek_type` | KEK sector type | text |

**Pipeline tab** (joined from `fct_ruptl_pipeline` via `grid_region_id`):
| Field | Display label | Unit |
|-------|--------------|------|
| `pre2030_solar_mw` | RUPTL solar planned pre-2030 | MW |
| `post2030_share` | Share of solar post-2030 | % |
| `grid_upgrade_pre2030` | Grid upgrade pre-2030? | boolean |
| `grid_first` | Grid-first flag | boolean |
| `plan_late` | Planning-late flag | boolean |

---

## §4 Colour & Visual Language

### Action flag colours

| Flag | Colour | Hex | Meaning |
|------|--------|-----|---------|
| `solar_now` | Green | `#2E7D32` | Solar LCOE < grid cost at current WACC |
| `invest_resilience` | Amber | `#F57C00` | Within 20% of parity + high reliability requirement |
| `grid_first` | Blue | `#1565C0` | Grid upgrade (RUPTL) brings cost down before 2030 |
| `not_competitive` | Red | `#C62828` | Solar not competitive; no near-term trigger |

### Future data colours

| Data series | Colour | Hex | When |
|-------------|--------|-----|------|
| Wind CF | Teal | `#00796B` | v1.1 — differentiates from solar green `#2E7D32` |

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

## §7 Wind CF Integration

Wind capacity factor will be added using the same pipeline architecture as solar. See [TODOS.md](TODOS.md) H2 for tracking.

**Data flow:** Global Wind Atlas GeoTIFF → `build_fct_kek_resource.py` (window read at KEK centroid + best-50km) → CF → `build_fct_lcoe.py` → LCOE bands.

**New columns in `fct_kek_resource`:**
- `cf_wind` — wind capacity factor at KEK centroid
- `pvout_wind_equivalent` — normalised wind output for comparison with solar PVOUT

**Dashboard impact:**
- Scorecard Resource tab: show wind CF alongside solar CF
- Quadrant chart: toggle to show wind LCOE series (teal `#00796B`, see §4)
- Ranked table: add `cf_wind` column

**Tech cost:** Wind CAPEX/OPEX/lifetime will be sourced from ESDM Technology Catalogue (same pattern as TECH006 solar). New `dim_tech_cost` row for wind.

**Priority:** v1.1 (decision #19, user accepted at premise gate). Architecture is identical to solar; purely additive.

---

## §8 Architecture Notes

From Phase 3 engineering review (decisions #29–#33). These patterns must be followed when building the Dash app.

### Callback logic extraction

Extract all callback business logic to `src/dash/logic.py` as pure functions with no Dash dependency. Callbacks in `app.py` become thin wrappers that read from stores, call logic functions, and return component updates. This keeps logic unit-testable with pytest, without running a Dash server.

Example:
```python
# src/dash/logic.py (testable)
def filter_lcoe_by_wacc(lcoe_df, wacc_value, siting_scenario="within_boundary"):
    return lcoe_df[(lcoe_df["wacc_pct"] == wacc_value) & ...]

# app.py (thin wrapper)
@app.callback(Output(...), Input("wacc-selection", "data"))
def update_quadrant(wacc):
    return filter_lcoe_by_wacc(lcoe_store, wacc)
```

### Startup data validation

On app startup, before loading data into `dcc.Store`:
1. Check CSV file existence in `outputs/data/processed/`
2. Validate expected row counts (`fct_kek_scorecard` = 25, `fct_lcoe` = 450)
3. Validate required columns are present (list defined in `src/dash/logic.py`)
4. On failure: display error state (§3 Interaction States) instead of crashing

### Callback configuration

- `prevent_initial_call=True` on all non-startup callbacks
- Startup loaders (`scorecard-data`, `lcoe-data`) fire once at app load
- All user-triggered callbacks (WACC change, map click, grid benchmark, demand override) use `prevent_initial_call=True` to avoid callback storm on startup

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
| 2026-04-08 | — | Expand scorecard: add Demand tab + Pipeline tab, complete Resource/LCOE fields | Scorecard was missing ~half of DESIGN.md §3 fields, 2 of 4 tabs |
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
| 2026-04-08 | — | Buildable area fragmentation warning in ScoreDrawer Resource tab | 1km PVOUT resolution makes contiguity filter a no-op; UI caveat for small buildable areas |
| 2026-04-09 | — | Thesis pivot: remote captive → grid-connected solar; three-point proximity replaces gen-tie model | No global precedent for 50km private gen-tie; realistic model is IPP → PLN PPA → grid delivery → KEK |
| 2026-04-09 | — | DFI persona reframed: captive solar investor → grid infrastructure investor | DFIs fund grid infra (ADB/WB precedent), not private gen-ties |
| 2026-04-09 | — | New persona: Industrial Investor / KEK Tenant (buys from PLN, doesn't build solar) | Separates power consumer from power producer decision-making |
| 2026-04-09 | — | New action flag: invest_grid (solar exists but grid connection missing) | Policymaker needs to see WHERE grid investment unlocks solar |
| 2026-04-12 | — | Removed raster "Solar Buildable Area" layer; polygon layer renamed to "Solar Buildable Areas" | Raster at ~3.7km was coarse and inconsistent with vector polygons. Single source of truth now. |
| 2026-04-12 | — | Buildable polygons are clickable: popup shows area (ha), avg PVOUT, max capacity (MWp) | Users can inspect individual contiguous buildable sites on the map |
| 2026-04-12 | — | Within-boundary theoretical fallback zeroed out | KEKs with no spatial buildable pixels now show 0% coverage instead of a fake 20% estimate |
| 2026-04-12 | — | Methodology files consolidated: archived v0.4 + V2 + testing notes → `docs/archives/` | Single canonical methodology: `docs/METHODOLOGY_CONSOLIDATED.md` |
| 2026-04-12 | — | M12: Substation upgrade cost in precomputed LCOE pipeline + live scorecard API | `substation_upgrade_cost_per_kw` and `transmission_cost_per_kw` now flow through live API; `grid_investment_needed_usd` includes all 3 cost components |
| 2026-04-12 | — | M16: LCOE vs project scale curve chart (`LcoeCurveChart.tsx`) in ScoreDrawer LCOE tab | Shows how LCOE drops as capacity increases (transmission cost spreading). Client-side CRF formula. |
| 2026-04-12 | — | M7: Scenario save/compare (`ScenarioManager.tsx`) in AssumptionsPanel | Save up to 3 named scenarios to localStorage. Load/delete inline UI. |
| 2026-04-12 | — | Buildable radiate animation on KEK selection + auto-enable Solar Buildable Areas layer | Within-boundary (green) pulses first, then remote (teal) 1s later. 4.5s total. L10-adjacent spatial storytelling. |
| 2026-04-12 | — | Buildable legend in RasterLegend: in-boundary green, remote teal, 50km radius | Color distinction: green = inside KEK (no grid cost), teal = remote 50km (needs connection) |
| 2026-04-12 | — | Renamed "Gap" → "LCOE Gap" across ScoreDrawer, DataTable, QuadrantChart, walkthrough | Clearer labeling: "LCOE Gap to BPP", "LCOE Gap to Tariff", "LCOE Gap (%)" |
