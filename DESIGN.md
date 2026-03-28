# Design — Indonesia KEK Power Competitiveness Dashboard

**Status:** Phase 3 design spec (pre-build). Finalise §6 open questions before writing Dash code.
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
- [§6 Open Design Questions](#6-open-design-questions)

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
                                         │
Quadrant Chart ◄── WACC selector ───────┤
    │                                    │
    ▼                                    │
Flip Scenario Panel                      │
    │                                    │
    ▼                                    │
Ranked Table ◄──────────────────────────┘
    │ CSV export
    ▼
Investment memo / policy brief
```

---

## §3 Component Architecture

### State management

| Store | Content | Drives |
|-------|---------|--------|
| `dcc.Store("scorecard-data")` | Full `fct_kek_scorecard` loaded once at startup | Ranked table, map marker colours, scorecard panel |
| `dcc.Store("lcoe-data")` | Full `fct_lcoe` (150 rows) loaded once at startup | Quadrant chart, flip scenario panel |
| `dcc.Store("wacc-selection")` | Current WACC value (8 / 10 / 12) | Quadrant chart, flip scenario, ranked table LCOE column |
| `dcc.Store("selected-kek")` | Currently selected `kek_id` | Scorecard panel content, map highlight |

### Callback architecture

```
[WACC radio buttons] ──► wacc-selection store
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
             Quadrant     Ranked     Flip
              chart       table     scenario

[Map click] ──► selected-kek store
                     │
                     ▼
              KEK Scorecard panel
```

### Component choices

| Component | Implementation | Rationale |
|-----------|---------------|-----------|
| Map | `plotly.Scatter_mapbox` with Carto tile provider | No Mapbox token required for Carto; fallback to `plotly.Scatter_geo` if token absent |
| Quadrant chart | `plotly.Scatter` with `shapes` for zone shading | Full control over quadrant lines; no external dep |
| Ranked table | `dash_table.DataTable` | Built-in sorting, filtering, CSV export |
| Scorecard cards | `dbc.Card` (dash-bootstrap-components) | Clean layout without custom CSS |
| WACC selector | `dcc.RadioItems` (3 options: 8 / 10 / 12%) | Snaps to precomputed values; see §6 for continuous option |

---

## §4 Colour & Visual Language

### Action flag colours

| Flag | Colour | Hex | Meaning |
|------|--------|-----|---------|
| `solar_now` | Green | `#2E7D32` | Solar LCOE < grid cost at current WACC |
| `invest_resilience` | Amber | `#F57C00` | Within 20% of parity + high reliability requirement |
| `grid_first` | Blue | `#1565C0` | Grid upgrade (RUPTL) brings cost down before 2030 |
| `not_competitive` | Red | `#C62828` | Solar not competitive; no near-term trigger |

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
| LCOE bands | Precomputed at WACC = 8 / 10 / 12% | Three `fct_lcoe` rows per KEK; WACC selector snaps to these |
| Quadrant positions | Read from `fct_lcoe` filtered by WACC selection | No calculation in browser |
| Competitive gap | Read from `fct_kek_scorecard` (WACC=10% baseline) | Precomputed; recalculated server-side if WACC changes |
| Demand | `resolve_demand()` in `basic_model.py` | Called server-side if user overrides `demand_mwh_user` |
| Green share (GEAS) | Precomputed in `fct_kek_scorecard.green_share_geas_2030_pct` | Recalculated if demand override changes |
| Flip scenario | Filter `fct_lcoe` to WACC=8% columns | Precomputed; threshold slider is client-side filter only |

### WACC slider behaviour

The dashboard ships with three precomputed WACC values (8 / 10 / 12%). The WACC selector snaps to one of these three. Continuous interpolation is deferred to v2 (requires additional `fct_lcoe` rows or a formula-based callback).

### Demand override hook

The `demand_mwh_user` column in `fct_kek_demand` is nullable (`Float64`). If a user enters a custom demand value in the Scorecard panel, the app calls `resolve_demand(demand_mwh_modelled, demand_mwh_user)` from `src/model/basic_model.py` to get the effective demand, then recalculates `green_share_geas` server-side and updates the scorecard display only (does not write back to CSV).

---

## §6 Open Design Questions

These must be resolved before Dash code is written:

| # | Question | Options | Recommendation |
|---|----------|---------|---------------|
| 1 | **WACC slider** — snap to 3 precomputed values or continuous? | A) Snap (3 values, instant) B) Continuous (requires interpolation callback) | **A** — simpler, faster, matches how DFIs actually quote WACC (8/10/12% are standard hurdle rates) |
| 2 | **Map tile provider** — Carto (no token) or Mapbox (prettier)? | A) Carto/OpenStreetMap via plotly built-in B) Mapbox (requires `MAPBOX_TOKEN` in `.env`) | **A for MVP** — removes auth dependency; upgrade to B in v2 if visual quality matters |
| 3 | **Mobile layout** — responsive or desktop-only? | A) Desktop-only (simpler, target users are analysts) B) Responsive (wider reach) | **A for MVP** — primary users are analysts with laptops; mobile adds CSS complexity |
| 4 | **Provisional data warning** — inline dagger or banner? | A) Dagger suffix per cell B) Yellow banner at top of page | **A** — cell-level is more precise; banner creates noise |
| 5 | **Export format** — CSV only or CSV + GeoJSON? | A) CSV (`fct_kek_scorecard`) only B) CSV + GeoJSON (`kek_polygons` joined) | **B** — DFI investors need GeoJSON for site team handoff (see PERSONAS.md §DFI Investor) |
