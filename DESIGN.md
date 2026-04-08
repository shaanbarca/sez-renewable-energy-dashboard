# Design — Indonesia KEK Power Competitiveness Dashboard

**Status:** Phase 3 design spec (post-autoplan review, 2026-04-07). All §6 questions resolved. Ready for Dash build.
**Related:** [PERSONAS.md](PERSONAS.md) | [ARCHITECTURE.md](ARCHITECTURE.md) | [PLAN.md](PLAN.md)

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

Six named views. Each is a page or panel within the single-page Dash app.

| # | View | Purpose | Primary data source | Key interaction |
|---|------|---------|-------------------|----------------|
| 1 | **Overview Map** | Spatial distribution of clean power competitiveness across all 25 KEKs | `fct_kek_scorecard.action_flag`, `solar_competitive_gap_wacc10_pct` | Click marker → load KEK Scorecard |
| 2 | **Quadrant Chart** | LCOE vs. grid cost proxy for all KEKs simultaneously — four zones visible at once | `fct_lcoe` (WACC-filtered) + `fct_grid_cost_proxy` | WACC selector updates positions live |
| 3 | **Ranked Table** | Sortable, filterable comparison of all 25 KEKs | `fct_kek_scorecard` | Column sort; action flag filter; CSV export |
| 4 | **KEK Scorecard** | Single-zone deep-dive: LCOE bands, resource, demand, grid context, action flag | All joined tables (one row per KEK) | Tab between Resource / LCOE / Demand / Pipeline |
| 5 | **Flip Scenario Panel** | "Which KEKs become competitive under changed assumptions?" | `fct_lcoe` WACC=8% columns + threshold slider | WACC selector + competitive-gap threshold slider |
| 6 | **RUPTL Context** | Regional grid pipeline timing — when does PLN's solar come online near each KEK? | `fct_ruptl_pipeline` | Year range slider; region filter |

### View flow

```
Overview Map
    │ click KEK
    ▼
KEK Scorecard ──────────────────────────┐
    │ tab: Pipeline                      │
    ▼                                    │
RUPTL Context                           │
    │ return                             │
    ▼                                    │
Flip Scenario Panel                      │
    │ "which KEKs flip?"                 │
    ▼                                    │
Quadrant Chart ◄── WACC slider ─────────┤
    │              + Grid benchmark      │
    ▼                                    │
Ranked Table ◄──────────────────────────┘
    │ CSV + GeoJSON export
    ▼
Investment memo / policy brief
```

*Changed 2026-04-07 (decision #25): Flip Scenario moved after Scorecard. Users confirm individual KEK picks before stress-testing assumptions.*

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
| Map | `plotly.Scatter_mapbox` with Carto tile provider | No Mapbox token required for Carto; fallback to `plotly.Scatter_geo` if token absent |
| Quadrant chart | `plotly.Scatter` with `shapes` for zone shading | Full control over quadrant lines; no external dep |
| Ranked table | `dash_table.DataTable` | Built-in sorting, filtering, CSV export |
| Scorecard cards | `dbc.Card` (dash-bootstrap-components) | Clean layout without custom CSS |
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

The dashboard ships with nine precomputed WACC values (4 / 6 / 8 / 10 / 12 / 14 / 16 / 18 / 20%). The WACC selector is a `dcc.Slider` with snap marks at each value, default = 10%. This covers the full range from DFI concessional financing (4–6%) through SE Asia equity ceiling (20%). No continuous interpolation is needed. See [METHODOLOGY.md §3.3](METHODOLOGY.md) for the full WACC methodology.

### Demand override hook

The `demand_mwh_user` column in `fct_kek_demand` is nullable (`Float64`). If a user enters a custom demand value in the Scorecard panel, the app calls `resolve_demand(demand_mwh_modelled, demand_mwh_user)` from `src/model/basic_model.py` to get the effective demand, then recalculates `green_share_geas` server-side and updates the scorecard display only (does not write back to CSV).

---

## §6 Open Design Questions (all resolved)

All resolved during Phase 3 autoplan review (2026-04-07):

| # | Question | Resolution | Decision # |
|---|----------|-----------|------------|
| 1 | **WACC slider** | ✅ **9-value `dcc.Slider`** with snap points at [4,6,8,10,12,14,16,18,20], default=10%. Covers full concessional-to-equity range. | #21, #27 |
| 2 | **Map tile provider** | ✅ **Carto for MVP**. No Mapbox token required. Mapbox deferred to v2 (see [TODOS.md](TODOS.md) L6). | — |
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
