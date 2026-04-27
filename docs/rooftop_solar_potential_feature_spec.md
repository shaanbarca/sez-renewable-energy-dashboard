# Feature Spec: Within-Boundary Solar Potential (Rooftop + Ground-Mount)

**Status:** Refined v4.1 (2026-04-27). Scope reduced to *raw potential only* — Supply Blend integration, ESDM cap, and Tenant view all deferred to v4.2+. v4 adds visual tile-grid rendering for sanity-check + alternative data sourcing for sites GoB v3 misses. v4.1 adds design-review fixes: §3.6.1 user journey, §3.6.2 DESIGN.md alignment, §3.8 interaction state matrix, §3.9 responsive + a11y, plus 4 new test files.
**Target version:** v4.1
**Estimated effort:** ~3-4 weeks (added tile-generation pipeline + alt-data fallback; trimmed by data-already-on-disk).

## Table of Contents

- [0. Decisions Resolved](#0-decisions-resolved-post-review) — top-of-doc snapshot of every architectural choice
- [1. Purpose](#1-purpose)
- [2. Why This Matters](#2-why-this-matters)
  - [2.1 Regulatory regimes differ](#21-the-decision-types-are-regulatorily-different)
  - [2.2 Indonesian rooftop is underutilized](#22-rooftop-solar-is-genuinely-underutilized-in-indonesia)
  - [2.3 Closes Persona 5 gap](#23-persona-5-industrial-investortenant-is-your-weakest-scored-persona)
  - [2.4 CBAM story becomes actionable](#24-the-cbam-story-gets-more-actionable)
- [3. Requirements](#3-requirements)
  - [3.1 Functional requirements (F1-F7, F13)](#31-functional-requirements)
  - [3.2 Non-functional requirements](#32-non-functional-requirements)
  - [3.3 Out of scope for v1](#33-out-of-scope-for-v1)
  - [3.4 Supply Blend integration — DEFERRED to v4.2](#34-supply-blend-integration--deferred-to-v42)
  - [3.6 Visual panel-tile grid (F8-F12, "show your work")](#36-visual-panel-tile-grid-the-show-your-work-layer)
    - [3.6.1 User journey (CFO validation arc)](#361-user-journey-validating-a-rooftop-number-the-headline-interaction)
    - [3.6.2 DESIGN.md alignment](#362-designmd-alignment)
  - [3.7 Missing-data sites — flag, don't hide](#37-missing-data-sites--flag-dont-hide)
  - [3.8 Interaction state coverage (loading / empty / error / success / partial)](#38-interaction-state-coverage)
  - [3.9 Responsive & Accessibility](#39-responsive--accessibility)
- [4. Success KPIs](#4-success-kpis)
  - [4.1 Data coverage](#41-data-coverage-kpis)
  - [4.2 User value](#42-user-value-kpis)
  - [4.3 Quality](#43-quality-kpis)
  - [4.4 Methodological honesty](#44-methodological-honesty-kpis)
- [5. Data Inputs and Sources](#5-data-inputs-and-sources)
  - [5.1 Primary: Google Open Buildings v3](#51-primary-data-source)
  - [5.2 Supplementary (validation only)](#52-supplementary-data-sources-for-spot-checks-and-validation)
  - [5.3 Derating factors — 4-stage decomposed model](#53-derating-factors-with-citations)
  - [5.4 Confidence score threshold](#54-confidence-score-threshold)
- [6. Step-by-Step Implementation Process](#6-step-by-step-implementation-process)
  - [Phase 0: Rename PR (✅ merged in PR #20)](#phase-0-prerequisite-rename-pr-05-day)
  - [Pipeline integration point](#pipeline-integration-point)
  - [CRS handling (EPSG:23830)](#crs-handling)
  - [Phase 1: Data acquisition + POC (✅ done)](#phase-1-data-acquisition-and-proof-of-concept-3-4-days-was-2-3)
  - [Phase 2: Core pipeline integration](#phase-2-core-pipeline-integration-2-3-days)
  - [Phase 3: Frontend integration](#phase-3-frontend-integration-3-4-days)
  - [Phase 4: Validation and publication](#phase-4-validation-and-publication-2-3-days)
- [7. Risks and Mitigations](#7-risks-and-mitigations)
- [8. Dependencies and Prerequisites](#8-dependencies-and-prerequisites)
- [9. Open Questions](#9-open-questions)
  - [9.1 Resolved](#91-resolved-post-review)
  - [9.2 Still open](#92-still-open)
- [10. Success Criteria for v1](#10-success-criteria-for-v1)
- [11. Follow-On Features (Post v1)](#11-follow-on-features-post-v1)
- [12. Estimated Timeline](#12-estimated-timeline)
- [13. Lightweight Data Strategy](#13-lightweight-data-strategy)
  - [13.1 The tension](#131-the-tension)
  - [13.2 Three-layer architecture](#132-three-layer-architecture)
  - [13.3 Why the 2 km buffer](#133-why-the-2-km-buffer)
  - [13.4 Preprocessing script design](#134-preprocessing-script-design)
  - [13.5 Runtime pipeline changes](#135-runtime-pipeline-changes)
  - [13.6 Deployment and CI](#136-deployment-and-ci)
  - [13.7 Data refresh policy](#137-data-refresh-policy)
  - [13.8 Size budget summary](#138-size-budget-summary)
  - [13.9 Failure modes and mitigations](#139-failure-modes-and-mitigations)
  - [13.10 Forward-compatibility invariants (v4.1 → v4.2)](#1310-forward-compatibility-invariants-for-multi-source-data-v41--v42)
  - [13.11 Storage policy](#1311-storage-policy--keep-raw-locally-discard-waste-commit-post-processed)
- [14. Building-Type Filtering for Rooftop Suitability](#14-building-type-filtering-for-rooftop-suitability)
  - [14.1 The problem (tanks/silos/conveyors detected as buildings)](#141-the-problem)
  - [14.2 Geometric filtering approach](#142-geometric-filtering-approach)
  - [14.3 Classification logic (4-category classifier)](#143-classification-logic)
  - [14.4 Effect on rooftop calculation](#144-effect-on-rooftop-calculation)
  - [14.5 New output fields](#145-new-output-fields)
  - [14.6 Validation strategy](#146-validation-strategy)
  - [14.7 Honest limitations](#147-honest-limitations)
  - [14.8 Alternative: OSM building tags](#148-alternative-osm-building-tags-where-available)
  - [14.9 Recommended v1 implementation](#149-recommended-v1-implementation)
- [15. Explicitly NOT in scope (v4.1)](#15-explicitly-not-in-scope-v41)
- [16. Test Plan](#16-test-plan)
  - [16.1 Unit tests](#161-unit-tests)
  - [16.2 Integration tests](#162-integration-tests)
  - [16.3 Golden-master tests](#163-golden-master-tests)
  - [16.4 Regression tests](#164-regression-tests)
  - [16.5 Failure-mode coverage](#165-failure-mode-coverage)
- [17. Worktree Parallelization Plan](#17-worktree-parallelization-plan)
- [18. Deferred TODOs (captured for follow-up)](#18-deferred-todos-captured-for-follow-up)

---

## 0. Decisions Resolved (post-review)

| Decision | Resolution | Rationale |
|---|---|---|
| **Scope of v4.1** | **Raw potential + map cross-check only.** Compute rooftop + within-site ground MWp per site. Show building polygons as a map overlay so users can eyeball the data. Add a BottomPanel table tab. **Defer all cost-cascade integration.** | "Where can rooftop solar go and how much" is a complete story by itself. Map overlay is the trust mechanism — better epistemic hygiene than burying derating in tooltips. |
| Where does rooftop sit in the Supply Blend cascade? | **Deferred to v4.2.** Rooftop number stands alone in v4.1, doesn't feed Supply Blend. | Lets us ship the raw-potential story now without forcing the (still-unresolved) per-tenant vs estate-level architecture choice. Captured in §18 TODOs. |
| Rename `max_captive_capacity_mwp` → `regional_groundmount_potential_mwp_50km` | **Separate prerequisite PR**, lands before this feature. | Breaking change to API + frontend. Bundling with methodology change tangles two unrelated things. See §3.1 F5. |
| §14 geometric classifier (tanks/silos/conveyors filter) | **Ships in v4.1.** | Without it, rooftop MW is overstated 30-50% on heavy industry. Map overlay catches some misclassifications visually, but the headline number must be defensible without requiring the user to manually exclude tank tops. |
| Confidence flag based on hard-coded site lists | **Derived signals only.** Building density vs polygon area + imagery vintage from `dim_sites`. | Per project rule: site classification must be pipeline-driven, not hand-curated. See §3.1 F4. |
| Rooftop CAPEX = ground-mount LCOE for v1? | **Moot in v4.1** since rooftop doesn't feed cost cascades. Differentiate when integration lands in v4.2. | Avoids blocking v4.1 on a CAPEX modeling exercise. |
| §14.3 geometric classifier thresholds | **Starting points, calibrated by §14.6 manual validation before merge.** | Shipping unverified thresholds as defaults gives precision the data doesn't support. |
| Validation target | **±20% on 10 manual sites** (was ±30%). | A 35 MW number with ±30% band could be 25–45 MW; even without cost integration, that's too loose to publish. |
| **Visual sanity-check via panel tiles** (NEW v4) | Pre-generate a panel-tile grid per `standard_roof` building, render at zoom ≥14 as small filled rectangles. Tile capacity is configurable via slider. Live re-compute as user changes panel power / size assumptions. | "Show your work" — counting visible tiles must reproduce the headline MWp number. Eliminates the "trust the spreadsheet" failure mode for DFI / industrial investor personas. See §5.3.1 + §3.6. |
| **Missing-data sites flagged for alt-data hunt** (NEW v4) | For the 14 sites where GoB v3 finds 0 buildings, write a pipeline-flagged shortlist with provenance hooks. Don't ship "low confidence" silently — make alt-data sourcing a first-class follow-up. | Verified in v4.1 build: 14 / 81 sites missing (post-2023 nickel IIA + Bali tourism KEKs). Microsoft GMLBF and Indonesia-specific sources (BIG ortho, BPS) likely close the gap. See §3.7 + L21 / L22 / L26 in §18. |
| **Forward-compatibility invariants for multi-source data** (NEW v4, replaces "full plugin architecture") | Defer the `_base.py` abstraction to v4.2 (when MS GMLBF gives us a second concrete shape to fit). v4.1 instead enforces 6 forward-compat invariants in the existing concrete code (no `_base.py`, no canonical-schema module): (1) parquet has `source_name` + `source_vintage` columns, (2) `building_id` is prefixed string, (3) `dim_sites.preferred_building_source` column exists, (4) single `load_buildings_for_pipeline()` function as the parquet entry point, (5) confidence handling treats null/NaN as "no score", (6) F4 reads `source_vintage` from data not from a hardcoded year. | Eng-review insight (2026-04-27): the contract as originally specified didn't fit MS GMLBF (no confidence scores), manual KML (no s2 token), or OSM (rich tag info). Shaping an abstraction from one concrete example is premature. v4.2's MS GMLBF migration becomes "new module + register it + merge by building_id" — additive, not a rewrite, as long as v4.1 ships the 6 invariants. See §13.10. |
| **Storage policy: keep raw locally, discard waste, commit post-processed** (NEW v4) | Three storage layers with explicit policy: (Layer 1) Raw GoB v3 extract — gitignored, kept locally to support re-merge when sites are added; cleanup deletes per-cell intermediate files outside site buffers (saved ~6 GB on the v4.1 build). (Layer 2) Site-buffered parquet (12.3 MB) — committed. (Layer 2.5) Tile parquet (~50 MB est.) — committed if under 50 MB, else gitignored + regenerated. (Layer 3) Aggregated CSV (~10 KB) — committed. | "Re-running with new sites should be cheap; checking out the repo shouldn't drag 7 GB of unused data; the dashboard's runtime should never see anything bigger than the post-processed layers." See §13.11. |
| **Mobile: outlines-only for tile layer** (NEW v4 — design review) | Below tablet breakpoint (768px), render building polygon outlines but NOT individual tiles. Score Drawer numbers still show. BottomPanel solar potential tab is the keyboard / mobile alternative for site comparison. Tile toggle in `LayerControl` shows "Desktop only" disabled state. | 47k tiles at 375px = unusable. CFO persona uses laptop; mobile is graceful degradation, not a blocker. See §3.9. |
| **Keyboard a11y: Tab focus on tile clusters** (NEW v4 — design review) | Each contiguous rooftop CLUSTER (DBSCAN, ε=50m) gets `tabindex="0"` + ARIA role at cluster centroid. Tab navigates clusters in spatial reading order; Enter opens the popup. Screen reader gets `aria-label` with full cluster summary. | WCAG 2.1.1 keyboard requirement; aligns with adding the click-aggregate feature without locking out keyboard users. See §3.9. |

---

## 1. Purpose

The current dashboard estimates solar potential by searching for buildable land within 50 km of each industrial site. This produces `max_captive_capacity_mwp` — a number that's useful for "is there enough renewable potential in the region" but doesn't answer the question a factory operator, DFI analyst, or policymaker actually asks:

**How much solar can be built *inside* this industrial site itself?**

This feature splits that question into three distinguishable numbers:

- **Rooftop solar potential** — behind-the-meter, on existing factory and warehouse roofs. No land acquisition, no gen-tie, simplest regulatory path under ESDM Regulation 2/2024.
- **Ground-mount solar potential within site boundary** — on vacant land inside the industrial estate fence. Requires land allocation but no external gen-tie.
- **Ground-mount solar potential within 50 km** — the existing metric, renamed for clarity. Requires land acquisition outside the site, gen-tie infrastructure, and often PLN procurement.

Each answers a different decision. Rooftop for a factory CFO asking "what can I do on my own buildings without external approvals?" Within-boundary ground for an industrial estate operator asking "how much of our common area can host solar?" External ground for a DFI asking "what utility-scale potential exists in this region?"

**Architecture principle:** the dashboard stays lightweight. Bulky satellite-derived datasets are preprocessed once into tiny aggregated outputs that the runtime pipeline consumes. See §13 for the three-layer data strategy.

---

## 2. Why This Matters

### 2.1 The decision types are regulatorily different

In Indonesia, these three options fall under different regulatory regimes:

| Option | Regulatory basis | Procurement requirement | Typical timeline |
|---|---|---|---|
| Rooftop solar (on-site) | ESDM Regulation 2/2024 (PLTS Atap) | None; self-installation | 3-6 months |
| Ground-mount within estate | Industrial estate by-laws + internal PPA | None if same legal entity | 6-12 months |
| Ground-mount external (utility-scale) | Perpres 112/2022 + PLN PPA | PLN procurement required | 18-36 months |

A dashboard that conflates these gives misleading answers about feasibility. "You have 500 MW of solar potential" means different things depending on which category it sits in.

### 2.2 Rooftop solar is genuinely underutilized in Indonesia

Indonesian rooftop solar penetration is far below neighbors (Vietnam, Thailand) despite similar irradiance and cheaper panel costs. The gap is mostly regulatory and awareness-based, not physical. Quantifying the physical rooftop potential at specific industrial sites creates a forcing function — a factory owner seeing "your facility has 35 MW of rooftop solar potential" is more likely to act than one reading a general statement about rooftop solar policy.

### 2.3 Persona 5 (Industrial Investor/Tenant) is your weakest-scored persona

At 80% readiness, this persona needs more to make location decisions. A factory operator comparing "which KEK should I locate my new plant in?" currently sees grid costs, CBAM exposure, and regional solar LCOE. Adding "how much solar can I put on my own roof at each site, and what does that do to my electricity cost?" directly closes the gap.

### 2.4 The CBAM story gets more actionable

Currently CBAM analysis says "switching to renewable electricity reduces exposure." With rooftop potential quantified, it becomes "your facility can cover X% of demand from your own rooftop, reducing CBAM exposure by $Y per tonne — without any external approvals." That's a CFO-ready finding.

---

## 3. Requirements

### 3.1 Functional requirements

**F1. For each of the 81 sites, compute and display:**
- Total building footprint area within the site polygon (m²)
- Estimated usable rooftop area (m²) after applying usability derating
- Rooftop solar capacity potential (MWp)
- Ground-mount buildable area within site polygon (ha), with existing 5-layer exclusion mask applied
- Ground-mount capacity potential within site polygon (MWp)
- Existing within-50km ground-mount metric, renamed for clarity

**F2. Surface these in the Score Drawer.** New sub-tab or section in the Resource tab showing the three-way split with a visualization (stacked bar chart is sufficient).

**F3. Update the methodology document** to describe the data source, vintage, derating factors, and limitations.

**F4. Add a data quality flag per site** indicating confidence in the footprint data, derived from pipeline signals (no hard-coded site lists):
- `building_data_confidence`: `high` | `medium` | `low`
- Logic (all derived, no curated lists):
  - **`low`** if: building count < 3 AND known site `capacity_annual_tonnes` > 100k (suggests undercount), OR site polygon area > 500 ha AND building footprint < 1% of polygon (suggests imagery gap), OR `dim_sites` commissioning vintage > 2023 (post-imagery)
  - **`high`** if: building count ≥ 10 AND building footprint between 5–40% of site polygon (typical industrial ratio)
  - **`medium`** otherwise
- All thresholds live in `src/assumptions.py` so they're tunable + auditable

**F5. PREREQUISITE PR — rename `max_captive_capacity_mwp` → `regional_groundmount_potential_mwp_50km`.** This rename lands BEFORE this feature, in its own small PR. It's a breaking change to the scorecard API + every frontend column reference (`columns.tsx`, `OverviewTab`, `ResourceTab`, `DataTable.tsx`). Bundling it with the methodology change tangles two unrelated risks.

The prerequisite PR:
1. Adds `regional_groundmount_potential_mwp_50km` as a new column in `fct_site_resource`
2. Keeps `max_captive_capacity_mwp` as a deprecation alias (same value) for one release
3. Updates frontend to read the new name
4. Adds a deprecation warning to API responses for the old name
5. Removes the alias in v4.2

**F6. Map overlay layer showing detected building footprints + classified usable rooftops.** This is the user's primary cross-check mechanism. A user opens the map, toggles the layer, and visually confirms the buildings are real and the classified rooftops are sensible.

Implementation:
- New map layer: `building_footprints` — all detected polygons within site boundaries
- New map layer: `usable_rooftops` — subset after §14 classifier filtering
- Color-code by classification: green = standard roof, orange = elongated/derated, gray = excluded (tank/silo/conveyor/too-small)
- Toggleable in `LayerControl` alongside existing layers (substations, KEK polygons, etc.)
- Source: `data/processed/sites_buildings_filtered.parquet` (Layer 2 from §13) served as GeoJSON via new endpoint `GET /api/layers/building_footprints`
- Render in MapLibre alongside existing vector overlays

**F7. New tab in BottomPanel data table for solar potential.**
- New view/tab in `frontend/src/components/ui/BottomPanel.tsx` showing per-site rooftop + within-site ground numbers
- Columns: site_name, sector, rooftop_solar_mwp, within_site_groundmount_mwp, regional_groundmount_potential_mwp_50km, building_count, data_confidence
- Sortable, filterable consistent with existing table behavior
- Lets users compare all 81 sites' solar potential at a glance without opening Score Drawers

### 3.6 Visual panel-tile grid (the "show your work" layer)

**The premise.** A user viewing a site needs to validate the rooftop MWp number without opening a calculator. The map should render simulated panel placement on each rooftop. Counting visible tiles × per-tile capacity must reproduce the headline MWp number, transparent end-to-end.

**F8. Pre-generate a panel-tile grid per `standard_roof` building.** Stored as a parquet (Layer 2.5 alongside `sites_buildings_filtered.parquet`). One row per tile, schema: `site_id`, `building_id`, `tile_idx`, `geometry` (small rectangle in EPSG:4326), `panels_in_tile`, `tile_kw_dc`, `tile_kw_ac`.

**F9. Render at zoom ≥ 14.** New MapLibre layer `rooftop_panel_tiles`, fill = solar-panel-blue (#1a3a8a), opacity 0.85. Hover shows: "X panels × Y W = Z kW (this rooftop: N tiles → M kW total)". Below zoom 14, render only as the building polygon outline (count is in the tooltip — no clutter).

**F10. Tile assumptions live in `assumptions.py`, exposed to the user as sliders.** When the user drags `panel_power_w` or `layout_density`, both the headline rooftop MWp AND the tile rendering recompute live. This is the "show your work" loop: change a number, watch the panels redraw to match.

**F11. Click interaction — per-rooftop and per-cluster aggregate.** Clicking on the map should produce three levels of information depending on what was hit:

| Click target | Popup shows |
|---|---|
| Single tile | "1 tile · 6 panels · 2.4 kW DC · 2.1 kW AC · ~3.2 MWh/yr" |
| One rooftop (any tile within a single building polygon) | "32 tiles · 192 panels · 76.8 kW DC · 67.6 kW AC · ~104 MWh/yr" |
| Contiguous rooftop cluster (tiles from buildings whose centroids are within `ROOFTOP_CLUSTER_RADIUS_M = 50 m` of each other) | "8 buildings · 187 tiles · 1,122 panels · 449 kW DC · 395 kW AC · ~607 MWh/yr" |

Annual MWh derived from the site's `pvout_centroid` (or `pvout_within_boundary` if available) × tile AC kW. Same PVOUT the existing pipeline already computes — no new data sources.

Implementation:
- Tile parquet has a `cluster_id` column (NEW — computed at preprocess time via DBSCAN on building centroids with `eps = ROOFTOP_CLUSTER_RADIUS_M / 1000` km, `min_samples = 1`)
- MapLibre `click` handler queries which tile / rooftop / cluster was hit
- Frontend looks up neighbours in the cluster, sums on the fly
- No backend round-trip for the aggregate (data is already in the tile parquet served per-site)

**F12. Score Drawer Resource tab aggregate.** The site-wide totals shown in the Score Drawer are the sum of all tiles for that site. Already covered by §3.1 F2 and the `fct_site_solar_potential.csv` columns. Adding one detail:

```
┌─ Solar Potential ──────────────────────────────────────┐
│  Rooftop:    287.4 MWp DC ·  253 MWp AC ·  389 GWh/yr  │
│             ↳  47,818 tiles · 287,008 panels           │
│             ↳  8,923 standard roofs (excluded: 3,208)  │
│  Within-site ground:  412.1 MWp DC                     │
│  50 km regional:    2,580.0 MWp DC                     │
└────────────────────────────────────────────────────────┘
```

The dual MWp (DC nameplate vs AC at meter) + tile/panel counts make the cross-check loop trivial: if the user hovers a single building, sees "32 tiles · 67.6 kW AC", and the headline says "47,818 tiles · 253 MWp AC", they can verify by sampling.

The four user-tunable parameters and their defaults:

| Slider | Default | Range | Meaning |
|---|---|---|---|
| `ROOFTOP_PANEL_POWER_W_DC` | **400** | 300-600 | Per-panel DC nameplate. 400 W = mainstream commercial 2024-2026; 550-600 W = high-end utility N-type. |
| `ROOFTOP_PANEL_AREA_M2` | **2.0** | 1.6-2.6 | Per-panel physical area. 2.0 m² = common commercial-class (~1.76 m × 1.13 m). |
| `ROOFTOP_LAYOUT_DENSITY` | **0.50** | 0.40-0.65 | Panel area as fraction of building footprint. 0.50 typical for industrial flat roof after walkways, setbacks, HVAC. |
| `ROOFTOP_PANELS_PER_TILE` | **6** | 1-24 | Visualization-only. How many panels = 1 visible tile rectangle. Smaller = more tiles to count, denser map. 6 = good balance. |

`panels_per_tile = 1` shows individual panels (most accurate, dense map at zoom 17+). `panels_per_tile = 24` shows utility-scale "string blocks" (cleaner map at zoom 14). The total MWp doesn't depend on this parameter — only the visual granularity.

**Information-architecture note (Score Drawer placement).** The rooftop section in the existing Score Drawer Resource tab sits BELOW the within-boundary solar block and ABOVE the regional 50 km block. Section heading `Rooftop solar potential` follows DESIGN.md §4 typographic convention for stat-block headings. This anchors the new feature inside the existing solar reading order (within-site → rooftop → regional) without breaking established visual rhythm.

**Credibility-recovery rule.** If summed visible tile capacity diverges from the headline number by more than 5%, the click-cluster popup MUST say "Note: small rounding from per-site classifier exclusions" instead of silently disagreeing. Never let the dashboard contradict itself in front of the user.

### 3.6.1 User journey: validating a rooftop number (the headline interaction)

The CFO persona's emotional arc through the "show your work" loop. Spec drives the UI to support each step.

```
STEP | USER DOES                       | USER FEELS                | UI SUPPORTS
─────|─────────────────────────────────|───────────────────────────|────────────────────────────────
 1   | Opens site (IMIP Morowali)      | Curious, slight skepticism| Score Drawer reveals "287 MWp"
 2   | Reads big number                | "Is that real?"           | Caption: "47k tiles · 287k panels"
 3   | Looks at map                    | "Where are these?"        | Building polygons outlined
 4   | Toggles "Rooftop tiles" layer   | "Show me"                 | Layer fades in; zoom hint visible
 5   | Zooms to a warehouse            | "Let me count"            | Tiles render at 6m × 5m each
 6   | Counts a 12-tile rooftop        | "60 kW... yeah, plausible"| Hover popup: "12 tiles · 60 kW"
 7   | Drags `panel_power_w` 400→500   | "What if panels improved?"| Number → 358 MWp; tiles redraw
 8   | Closes the site                 | Trust earned              | (next site benefits from belief)
```

Time horizons (Norman): 5-second visceral (the big number), 5-minute behavioral (the validation), 5-year reflective (trust the dashboard's other numbers because this one was inspectable).

### 3.6.2 DESIGN.md alignment

The rooftop UI MUST conform to existing dashboard patterns; new visual elements only where genuinely needed.

| Element | Reuse from DESIGN.md | New? |
|---|---|---|
| Tile fill color | Pick from existing accent palette (DESIGN.md §4); `#1a3a8a` was a placeholder. If no current accent is "solar blue", define a new CSS variable `--solar-panel-fill` in `globals.css` with a one-line comment about the addition. | Possibly |
| AssumptionsPanel sliders for panel power / area / density | Reuse the existing slider component used for WACC / CAPEX (DESIGN.md §3 component choices) | No |
| Score Drawer rooftop section heading + stat block | Reuse existing stat-block typography from the Resource tab's solar / wind blocks | No |
| Map layer toggle entry in `LayerControl` | Reuse existing `LayerControl` row pattern (icon + label + active-count badge) | No |
| Tile rendering zoom threshold (≥14) | Confirm against existing vector layer zoom strategy (DESIGN.md §6) — match unless strong reason to differ | TBD |
| Click popup style | Reuse existing MapLibre tooltip component used by site markers + nickel smelters | No |
| BottomPanel "Solar Potential" tab | Reuse existing TanStack Table column-header + sort UI from RankedTable | No |

**Implementation rule:** if the implementer can't find an existing pattern in 5 minutes, escalate before inventing a new one.

### 3.7 Missing-data sites — flag, don't hide

**F13. The pipeline must produce an explicit shortlist of sites with `building_data_confidence = 'low'` and an alt-data search hook.** Don't silently flag and move on; surface them so the next step is obvious.

Two outputs:

1. **`outputs/data/processed/fct_site_solar_potential.csv` row:** `building_data_confidence` = `low`, `building_data_source` = `gob_v3` (always for now; becomes `gob_v3+ms_gmlbf` or `gob_v3+manual` after fallback work).

2. **`outputs/data/processed/sites_missing_buildings.csv`** (NEW): lightweight CSV with `site_id`, `site_name`, `commissioning_year`, `province`, `sector`, `reason_flagged` (one of: `post_2023_imagery`, `low_count_for_capacity`, `polygon_imagery_gap`), `recommended_alt_data` (one of: `microsoft_gmlbf`, `manual_kml`, `bps_industrial_directory`).

The 14 sites the v4.1 build flagged (verified 2026-04-26):

| Reason flagged | Sites | Recommended fallback |
|---|---|---|
| Post-2023 imagery | IWIP, Pomalaa (IPIP), Buli, Konawe (IKIP), Stardust Estate, Red Lion Hongshi, Tanjung Sauh, Pupuk Iskandar Muda Lhokseumawe | **Microsoft GMLBF** (refreshed quarterly, may catch post-2023 builds). Then **manual KML** for residual gaps. |
| Tourism KEK (low industrial density) | KEK Kura Kura, KEK Mandalika, KEK Sanur, KEK Morotai | **No alt-data needed**; document as "predominantly tourism, minimal rooftop solar potential" in UI tooltip. |
| Coordinates / polygon issues | Cemindo Gemilang Bayah, KEK Maloy Batuta, KEK Arun Lhokseumawe | **Manual coordinate verification** + Microsoft GMLBF cross-check. |

This becomes the input to L21 (Microsoft GMLBF integration) — a concrete punch list, not a vague "sometime later" TODO.

**Empty-state copy for missing-data sites in the Score Drawer.** Don't show "0 MWp" — that reads as "this site has no rooftop potential" which is wrong. Show the explanation:

```
┌─ Rooftop solar potential ──────────────────────────┐
│  ⓘ Building data unavailable for this site.        │
│    Reason: {reason_flagged_human_readable}         │
│    Estimated rooftop potential: pending Microsoft  │
│    GMLBF integration (v4.2 / L26).                 │
└────────────────────────────────────────────────────┘
```

`{reason_flagged_human_readable}` is one of:
- `post_2023_imagery` → "Imagery vintage (May 2023) predates site commissioning ({commissioning_year})"
- `low_count_for_capacity` → "Detected building count below threshold for facility scale"
- `polygon_imagery_gap` → "Imagery gap inside the site polygon"
- Tourism KEK → "Predominantly tourism land use; minimal rooftop solar potential expected"

This copy lives in `frontend/src/lib/missingDataMessages.ts` (single source for translation later).

### 3.8 Interaction state coverage

The spec previously described mostly the happy path. Real UI needs explicit specs for every state. Below is the matrix that v4.1 ships.

| Feature | Loading | Empty | Error | Success | Partial |
|---|---|---|---|---|---|
| Map tile layer fetch | Skeleton overlay (faded blue rectangles at building centroids) while parquet streams in. Disappears on first paint. | Polygon outline rendered in gray dashed; no tiles. Score Drawer footnote: "No standard rooftops detected after §14 classification." | Toast: "Tile data unavailable. Retry." + retry button. Polygon outline stays. | F9 specified | If <50% of expected tiles arrive in 3s: render what we have + grey placeholder for missing buildings; no error toast unless 0 arrive |
| Score Drawer rooftop section | Skeleton bars in the rooftop section while `fct_site_solar_potential.csv` loads | F11 in §3.7 (missing-data copy) | Inline "Rooftop data couldn't load. Retry?" with retry button | F12 specified | If aggregate is partial (some buildings still classifying), show "Updating…" indicator next to the number |
| BottomPanel Solar Potential tab | Skeleton rows | Empty-state row: "No sites match current filters" with "Clear filters" link | Toast on column-fetch failure | F7 specified | Greyed cells with "—" if a single site's data is missing |
| Slider mid-drag (panel power / area / density) | Number recomputes immediately frontend-only; no backend round-trip; no spinner | N/A | Frontend can't fail (pure JS multiply); if it does, log to console and freeze last known value | Number updates < 16ms; tile capacity labels redraw | N/A |
| Slider mid-drag (layout density / setback — these change tile geometry) | Tile layer shows "Updating…" overlay while pipeline regenerates (~200ms-1s) | N/A | Toast "Couldn't recompute tiles. Last value: X" + slider snaps back | Tiles redraw at new positions | N/A |
| Click cluster | N/A (instant) | "Clicked area has no tiles" subtitle in popup | "Couldn't load cluster summary. Try clicking a single tile instead." | F11 specified | Show partial sum if some tile capacities haven't loaded yet |
| AssumptionsPanel slider reset | Sliders animate back to defaults (250ms ease-out) | N/A | N/A | N/A | N/A |

**No silent failures.** Every state listed gets a test in §16 and a corresponding UI element. The dashboard's existing toast system handles error notifications uniformly.

### 3.9 Responsive & Accessibility

v4.1 is laptop-first per DESIGN.md, but the rooftop layer's density forces explicit responsive + a11y specs.

#### Responsive breakpoints

| Breakpoint | Behavior |
|---|---|
| Desktop (≥1024px) | Full feature set — tiles render at zoom ≥14, click aggregation, slider live recompute, BottomPanel tab. |
| Tablet (768-1024px) | Same as desktop; tiles render but Score Drawer collapses to half-width to leave map room. |
| **Mobile (<768px)** | **Outlines only** — building polygons render but TILES DO NOT. 47k tile rectangles destroy mobile perf + are unreadable at 375px. Score Drawer numbers still show. BottomPanel solar tab is the keyboard / mobile alternative for site comparison. Tile-toggle in `LayerControl` shows "Desktop only" disabled state with explainer tooltip. |

This is decision-resolved (eng review 2026-04-27, user choice "outlines only on mobile"). The CFO persona uses laptop; mobile is a graceful degradation, not a blocker.

#### Accessibility

| Concern | Specification |
|---|---|
| Keyboard navigation for tile click | Each contiguous rooftop CLUSTER (DBSCAN, ε=50m) gets a `tabindex="0"` + ARIA-role attached at cluster centroid. Tab moves through clusters in spatial reading order (top-left → bottom-right). Enter triggers the click popup. (Eng review 2026-04-27 user choice; aligns with WCAG 2.1.1 keyboard requirement.) |
| Screen reader text for click popup | `aria-label="Cluster of {N} buildings: {tiles} solar tiles totaling {kw_ac} kilowatts AC, estimated {mwh_yr} megawatt-hours per year"`. Popup also has a `role="dialog"` + `aria-modal="false"` (it's a transient tooltip, not a modal). |
| Color contrast | The `--solar-panel-fill` color (per DESIGN.md §4 alignment, see §3.6.2) must meet WCAG AA 3:1 for non-text UI against the dashboard's basemap. Verify via Chrome DevTools color picker after the color is finalized. Document the measured ratio in the implementation PR. |
| Touch targets | Cluster click target is the convex hull of the cluster's tiles. Minimum interactive area 44×44 CSS pixels per WCAG 2.5.5 — clusters smaller than that get a padded invisible click region. |
| Focus ring | Use the existing `--focus-ring` CSS variable from DESIGN.md, not a one-off ring style. |
| Reduced motion | `prefers-reduced-motion: reduce` skips the layer fade-in and the slider redraw animation; tiles appear instantly. |

#### Tab order through the rooftop UI

```
1. LayerControl "Rooftop tiles" toggle
2. AssumptionsPanel: panel_power slider → panel_area → layout_density → setback
3. Map: each contiguous rooftop cluster (visible at current zoom), spatial reading order
4. Score Drawer rooftop section heading
5. BottomPanel Solar Potential tab (when active)
```

Test: a keyboard-only user must be able to (a) toggle the layer, (b) drag a slider via arrow keys, (c) reach a cluster popup via Tab+Enter, (d) read the popup content via screen reader. All four covered by the test plan §16.

### 3.2 Non-functional requirements

**N1. Reproducibility.** All computations derived from public datasets with documented versions. Methodology published on Zenodo alongside v4.x release.

**N2. Performance.** Polygon-based spatial joins for 81 sites should run in under 5 minutes on standard hardware. Acceptable to cache results rather than recompute on every page load.

**N3. Transparent limitations.** Every number in the UI links to or surfaces its data vintage. A user hovering over "35 MW rooftop potential" should be able to see "based on Google Open Buildings v3, imagery from May 2023, derating factor 0.5."

**N4. Testable.** Golden-master tests on 3-5 fixture sites with known-good outputs. If a pipeline update changes rooftop area by more than 10%, tests fail.

### 3.3 Out of scope for v1

- Time-of-day or hourly generation profiles (PyPSA will handle this separately)
- Parking canopy / solar carport potential (requires separate paved-area detection, defer to Phase 3)
- Rooftop structural load assessment (requires building height + construction type data, not generally available)
- Rooftop solar cost modeling (assume same $/kW as ground-mount for now; differentiate in v2)
- Shading analysis from nearby tall structures (requires DSM; defer)

### 3.4 Supply Blend Integration — DEFERRED to v4.2

v4.1 ships rooftop + within-site ground potential as **standalone metrics**. They appear in the Score Drawer, the BottomPanel table, and the map overlay. They do **NOT** feed `enrich_delivered_cost` or change the Supply Blend headline.

Why deferred: how rooftop integrates with the estate-level cascade is a real architectural question (per-tenant vs estate-level scales). v4.1 has enough value standing alone — "where can rooftop go and how much" — that it doesn't need the cost story to ship. Captured as a v4.2 TODO with two integration options to evaluate at that point (4-layer cascade vs. separate Tenant view).

The v4.1 numbers are forward-compatible: when v4.2 adds the integration, the same `rooftop_solar_mwp_potential` column feeds it. No data churn, no schema rework.

---

## 4. Success KPIs

### 4.1 Data coverage KPIs

| KPI | Target | Measurement |
|---|---|---|
| Sites with rooftop potential computed | ≥ 75 of 81 | Count of sites with non-null `rooftop_solar_mwp_potential` |
| Sites flagged `high` confidence | ≥ 60 of 81 | Count with `building_data_confidence = 'high'` |
| Sites flagged `low` confidence | ≤ 10 of 81 | Mostly post-2023 nickel IIA expansions |
| Methodology documented on Zenodo | Yes | v4.x DOI includes this feature |

### 4.2 User value KPIs

| KPI | Target | Measurement |
|---|---|---|
| Persona 5 readiness score | 80% → 88% | Updated PERSONAS.md scorecard |
| New field in top-10 CBAM-exposed sites analysis | 10/10 sites show rooftop MW | Manual review of top-10 list |
| UI hover/drill-through for every reported number | 100% | Manual QA of Score Drawer |

### 4.3 Quality KPIs

| KPI | Target | Measurement |
|---|---|---|
| Golden-master test coverage | ≥ 5 fixture sites | `tests/test_rooftop_solar.py` |
| Spot-check accuracy vs manual Google Earth measurement | Within ±20% on 10 random sites | Manual validation report (was ±30% pre-review) |
| Methodology consistency check | Rooftop footprint + within-site ground area ≤ total site polygon area | Unit assertion in `compute_within_boundary_groundmount_potential` (raises `AssertionError` if violated) |
| Geometric classifier validation | ≥ 80% agreement with manual classification on 100 buildings (5 sites × 20 each) | `tests/test_classify_building.py` with manual labels in fixtures |

### 4.4 Methodological honesty KPIs

| KPI | Target | Measurement |
|---|---|---|
| Every field has documented data vintage | 100% | Methodology audit |
| Sites with significant undercount flagged | Yes | Manual list in methodology doc |
| Derating factors documented with citations | 100% | Methodology appendix |

---

## 5. Data Inputs and Sources

### 5.1 Primary data source

**Google Open Buildings v3**
- URL: https://sites.research.google/gr/open-buildings/
- Version: v3, inference performed May 2023
- Coverage: Indonesia included in country list
- Format: CSVs sharded by S2 cell level 4
- Size: 178 GB for all polygons globally; much smaller if filtered to Indonesia
- License: CC BY-4.0 OR ODbL v1.0 (pick one)
- Access method: Download via `gsutil`, or query via Earth Engine, or region-specific subset via Colab notebook
- Fields used: `latitude`, `longitude`, `area_in_meters`, `confidence`, `geometry`

### 5.2 Supplementary data sources (for spot-checks and validation)

**OpenStreetMap (OSM) building polygons**
- For well-mapped industrial zones in Java, OSM often has better coverage for specific facilities
- Use for cross-validation, not as primary source
- Access via Overpass API or Geofabrik Indonesia extract

**Microsoft Global Building Footprints**
- Alternative ML-derived building footprint dataset
- Use for sites where Google Open Buildings v3 shows low coverage or obvious gaps
- GitHub: https://github.com/microsoft/GlobalMLBuildingFootprints

**Manual polygon drawing (fallback)**
- For post-2023 nickel IIA expansions where automated data is incomplete
- Use Google Earth Pro to visually identify buildings and export KML
- Document as manual override in a residual CSV

### 5.3 Derating factors (with citations)

The model decomposes into FOUR explicit stages, all named constants in `src/assumptions.py` (per project rule: tunable, auditable, no magic numbers):

```
                                         ╭─ §5.3.1 Panel ────────────╮
                                         │ panel_power_W_DC = 400    │
                                         │ panel_area_m²    = 2.0    │  → 200 W/m² of panel area
                                         ╰───────────────────────────╯
                                                       ↓
                                         ╭─ §5.3.2 Layout ───────────╮
                                         │ layout_density   = 0.50   │  → fraction of footprint covered
                                         ╰───────────────────────────╯  in panels (vs walkways/HVAC/setback)
                                                       ↓
                                         ╭─ §5.3.3 Climate ──────────╮
                                         │ thermal_derate   = 0.88   │
                                         ╰───────────────────────────╯  → tropical hot-module loss
                                                       ↓
                                         ╭─ §5.3.4 Composite ────────╮
                                         │ rooftop_kW_AC =           │
                                         │   footprint_m² × 0.50     │
                                         │   × 200 W/m² × 0.88 ÷ 1k  │
                                         │   ≈ footprint × 0.088     │  → 88 W/m² AC of footprint
                                         ╰───────────────────────────╯

     Worked example: 1,000 m² flat warehouse → ≈88 kW AC ≈ 22 visible tiles (at 6 panels/tile)
```

All numbers below come from current (2024-2026) commercial PV datasheets + NREL technical reports + IEC / SNI installation codes. Replaced the v3 spec's collapsed `ROOFTOP_W_PER_M2 = 170` with explicit panel + layout decomposition so the slider story is honest.

#### 5.3.1 Panel (the physical module)

| Constant | Default | Range | Source |
|---|---|---|---|
| `ROOFTOP_PANEL_POWER_W_DC` | 400 | 300-600 | Mainstream commercial 2024-2026 N-type bifacial monocrystalline. Tier-1 datasheets (JinkoSolar Tiger Neo 415-435W, JA Solar JAM72D40 410-430W, Trina Vertex S+ 425-450W). High-end utility N-type now 550-620W (Trina Vertex N TSM-NEG21C.20, LONGi Hi-MO 7). |
| `ROOFTOP_PANEL_AREA_M2` | 2.0 | 1.6-2.6 | 1.76 m × 1.13 m commercial-class (≈2.0 m²) or 2.28 m × 1.13 m utility-class (≈2.6 m²). 1.6 m² = older small-format. |
| Derived: panel-area density | **200 W/m²** | 150-260 | At default 400 W / 2.0 m². Modern N-type bifacial achieves 210-240 W/m² panel-area peak. |

#### 5.3.2 Layout (panel area / footprint area)

| Constant | Default | Range | Source |
|---|---|---|---|
| `ROOFTOP_LAYOUT_DENSITY` | 0.50 | 0.40-0.65 | NREL TP-6A20-65298 (rooftop technical potential). 0.50 = industrial flat roof after 1m edge setback (SNI 03-1736-2000, IEC 62548), 0.6-1.0m row-walkway aisles every few rows, HVAC / skylights / structural penetrations. Higher (0.55-0.65) if the rooftop is empty + low-tilt; lower (0.40) if heavy HVAC. |
| `ROOFTOP_EDGE_SETBACK_M` | 1.0 | 0.5-2.0 | Industrial fire access code (SNI 03-1736-2000 §7.4, also IEC 62548:2016). 1m minimum; 1.5m more conservative. |
| `ROOFTOP_PANELS_PER_TILE` | 6 | 1-24 | Visualization-only — see §3.6 F10. 6 = ~1 string-half (typical industrial inverter input is 12-24 panels per string). 1 = render individual panels. |
| `ROOFTOP_CLUSTER_RADIUS_M` | 50 | 20-200 | DBSCAN epsilon for click-interaction "contiguous rooftop cluster" (see §3.6 F11). 50 m groups buildings sharing a continuous roofscape (e.g. an industrial estate's main hall + adjoining warehouses) without merging unrelated structures across roads. |

#### 5.3.3 Climate / system derating

| Constant | Default | Range | Source |
|---|---|---|---|
| `THERMAL_DERATE_TROPICAL` | 0.88 | 0.85-0.92 | Indonesian climate. Module temp coefficient typically -0.30 to -0.36 %/°C; module cell temp runs 25-30°C above ambient under STC; gives ~12% production loss vs nameplate. NREL PVWatts default for equatorial tropical. v4.2 will replace with regional variation (L23 in §18). |

**v4.1 uses thermal derate only.** Other system losses (inverter ~0.97, DC wiring ~0.98, soiling ~0.95, mismatch ~0.98) compose to ~0.88 of their own. We absorb them implicitly by reading the headline number as "deliverable AC at the meter" rather than nameplate DC. v4.2 may unbundle if the single-derate model creates persona confusion — see L27 in §18.

#### 5.3.4 §14 geometric building-type classifier

| Constant | Default | Source |
|---|---|---|
| `BUILDING_CIRCULARITY_TANK_THRESHOLD` | 0.85 | §14.3 starting point, calibrated by §14.6 validation before merge. |
| `BUILDING_ASPECT_CONVEYOR_THRESHOLD` | 8.0 | §14.3 starting point. |
| `BUILDING_MIN_AREA_M2` | 200 | Below this: too small for commercial rooftop solar regardless of type. |
| `BUILDING_HULL_RATIO_COMPLEX_THRESHOLD` | 0.70 | §14.3 starting point. |

#### 5.3.5 F4 confidence-flag thresholds (derived signals only)

| Constant | Default | Used to set `building_data_confidence` to |
|---|---|---|
| `BUILDING_FOOTPRINT_TYPICAL_RATIO_LOW` | 0.05 | `low` if site polygon area > 500 ha and footprint < 5% — likely imagery gap |
| `BUILDING_FOOTPRINT_TYPICAL_RATIO_HIGH` | 0.40 | `low` if footprint > 40% — implausibly dense, suggests miscount |
| `BUILDING_COUNT_HIGH_CONFIDENCE_MIN` | 10 | `high` requires ≥10 buildings + footprint in 5-40% band |
| `BUILDING_COUNT_LOW_CONFIDENCE_MAX` | 3 | `low` if known major facility (capacity > 100k tonnes/yr) has < 3 buildings |
| `BUILDING_DATA_VINTAGE_YEAR_CUTOFF` | 2023 | `low` if site commissioned > 2023 (post-GoB v3 imagery) |
| `SITE_POLYGON_LARGE_AREA_HA` | 500 | Threshold for the imagery-gap heuristic |

### 5.4 Confidence score threshold

Google Open Buildings provides confidence scores per building. Use their **90% precision threshold** for each S2 cell (published in `score_thresholds_s2_level_4.csv`) to filter low-confidence detections. This trades recall for precision — better to undercount than to include hallucinated buildings.

---

## 6. Step-by-Step Implementation Process

### Phase 0: Prerequisite rename PR (0.5 day)

Land the `max_captive_capacity_mwp` → `regional_groundmount_potential_mwp_50km` rename in its own small PR. See §3.1 F5 for the deprecation alias plan. **Do not start Phase 1 until this is merged.**

### Pipeline integration point

Where this work slots into `run_pipeline.py`:
- `preprocess_open_buildings.py` is **NOT** a pipeline step. It runs once externally (or when refreshing data) and produces `data/processed/sites_buildings_filtered.parquet` (Layer 2 from §13).
- `build_fct_site_resource.py` (existing pipeline step) gets extended to read the parquet, compute rooftop + within-site ground potential, and emit the new columns. Insertion point: same step as today, no new dependencies in the DAG.
- `build_fct_site_solar_potential.py` (NEW pipeline step) consumes the parquet + `dim_sites` + `fct_site_resource` and produces the aggregated `fct_site_solar_potential.csv` (Layer 3). Depends on: `dim_sites`, `fct_site_resource`. Add to `run_pipeline.py` after `build_fct_site_resource`.

### CRS handling

All area calculations use **EPSG:23830 (Indonesian National DGN95 / UTM zone 50S)** as the projected CRS for area-preserving operations. Indonesia spans the equator and zones 46N–54S; UTM 50S is the centroid-best fit for the 81 sites we have today. Document the choice; allow per-site CRS override for sites in extreme east (Papua) where 50S has measurable error.

Implementation:
- Reproject site polygon + clipped buildings to EPSG:23830 before computing intersection areas
- Convert back to EPSG:4326 (WGS84) for storage
- Add unit test `tests/test_crs_reprojection.py` covering: equator-crossing site (Pomalaa), east extreme (Weda Bay), Java (Cilegon)

### Phase 1: Data acquisition and proof of concept (3-4 days, was 2-3)

**Step 1.1: Download Indonesia subset of Google Open Buildings v3**

Use the official Colab notebook to download only Indonesia polygons:
```
https://colab.research.google.com/github/google-research/google-research/blob/master/building_detection/open_buildings_download_region_polygons.ipynb
```

Input: Indonesia country boundary (ADM0 from GADM or Natural Earth)
Output: One or more CSVs with building polygons within Indonesia
Expected size: 5-15 GB compressed, 50-100 million building polygons

**Step 1.2: Load as GeoDataFrame**

Convert WKT polygons to Shapely geometries. Build a spatial index (R-tree) for efficient querying. Persist as GeoParquet for fast reload.

```python
# src/pipeline/load_google_open_buildings.py
import geopandas as gpd
from shapely import wkt

def load_indonesia_buildings(path_to_csv):
    df = pd.read_csv(path_to_csv)
    df['geometry'] = df['geometry'].apply(wkt.loads)
    gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
    gdf.to_parquet('data/processed/idn_open_buildings_v3.parquet')
    return gdf
```

**Step 1.3: Apply confidence threshold per S2 cell**

Load `score_thresholds_s2_level_4.csv`. For each building, determine its S2 cell and apply the 90%-precision threshold. Drop buildings below threshold.

**Step 1.4: Spot-check 5 fixture sites**

Pick 5 sites with different characteristics:
- Krakatau Steel Cilegon (well-established, dense Java coverage)
- Petrokimia Gresik (well-established fertilizer complex)
- IMIP Morowali (rapidly expanding nickel, post-2023 additions likely missing)
- IWIP Weda Bay (remote, newer)
- KEK Sei Mangkei (smaller, mixed development)

For each, load the site polygon, spatially join with buildings, sum the footprint area. Compare visually against recent Google Earth imagery. Document undercount where it exists.

### Phase 2: Core pipeline integration (2-3 days)

**Step 2.1: Add rooftop computation to site resource pipeline**

Modify `src/pipeline/build_fct_site_resource.py`:

```python
def compute_rooftop_solar_potential(
    site_polygon,
    buildings_gdf,
    rooftop_usable_share=0.50,
    power_density_w_per_m2=170,
    thermal_derate=0.88,
):
    """
    Returns rooftop solar potential in MWp for a given site polygon.
    """
    buildings_in_site = buildings_gdf[buildings_gdf.intersects(site_polygon)]
    if len(buildings_in_site) == 0:
        return {
            'total_building_footprint_m2': 0,
            'usable_rooftop_area_m2': 0,
            'rooftop_solar_mwp_potential': 0,
            'building_count': 0,
            'data_confidence': 'low',  # no buildings detected; suspicious
        }

    total_footprint = buildings_in_site.intersection(site_polygon).area.sum()
    # Convert from decimal degrees to meters using equal-area projection
    total_footprint_m2 = reproject_to_equal_area(total_footprint)

    usable_rooftop_m2 = total_footprint_m2 * rooftop_usable_share
    rooftop_mwp = (
        usable_rooftop_m2 *
        power_density_w_per_m2 *
        thermal_derate /
        1_000_000
    )

    return {
        'total_building_footprint_m2': total_footprint_m2,
        'usable_rooftop_area_m2': usable_rooftop_m2,
        'rooftop_solar_mwp_potential': rooftop_mwp,
        'building_count': len(buildings_in_site),
        'data_confidence': determine_confidence(site_id, buildings_in_site),
    }
```

**Step 2.2: Compute within-boundary ground-mount potential**

Subtract building footprints from the site polygon. Apply existing 5-layer buildability mask. Compute remaining buildable area and convert to MWp.

```python
def compute_within_boundary_groundmount_potential(
    site_polygon,
    buildings_gdf,
    buildability_filters,
):
    # Subtract buildings
    buildings_in_site = buildings_gdf[buildings_gdf.intersects(site_polygon)]
    non_building_area = site_polygon.difference(buildings_in_site.unary_union)

    # Apply buildability mask (existing logic)
    buildable = apply_buildability_mask(non_building_area, buildability_filters)

    area_ha = buildable.area_in_hectares()
    mwp = area_ha / HA_PER_MWP
    return {
        'within_site_groundmount_area_ha': area_ha,
        'within_site_groundmount_mwp': mwp,
    }
```

**Step 2.3: Rename existing 50 km metric for clarity**

Rename `max_captive_capacity_mwp` to `regional_groundmount_potential_mwp_50km`. Add alias for backward compatibility. Update all references in pipeline, API, and UI. Document the rename in CHANGELOG.

**Step 2.4: Write confidence flag logic**

```python
def determine_confidence(site_id, buildings_detected):
    # Post-2023 nickel IIA expansions: low confidence
    if site_id in POST_2023_EXPANSION_SITES:
        return 'low'
    # Very few buildings detected for a known major facility: low
    if site_id in KNOWN_MAJOR_FACILITIES and len(buildings_detected) < 5:
        return 'low'
    # Java industrial estates with good OSM overlap: high
    if site_id in WELL_MAPPED_SITES:
        return 'high'
    # Default: medium
    return 'medium'
```

Maintain `POST_2023_EXPANSION_SITES` and similar lists as data files, not code.

### Phase 3: Frontend integration (3-4 days)

**Step 3.1: Add fields to API response**

Update `src/api/routes/scorecard.py` to include new fields:
- `rooftop_solar_mwp_potential`
- `within_site_groundmount_mwp`
- `regional_groundmount_potential_mwp_50km`
- `total_building_footprint_m2`
- `usable_roof_area_m2` (after §14 classifier)
- `building_count_total`, `building_count_standard_roof`, `building_count_tank_silo`, `building_count_conveyor`, `building_count_other_excluded`
- `building_data_confidence`
- `building_data_vintage` (static: "2023-05 Google Open Buildings v3")

Add new endpoint:
- `GET /api/layers/building_footprints` — returns GeoJSON of detected polygons within all 81 site boundaries, with `classification` property (`standard_roof` | `elongated` | `tank_silo` | `conveyor` | `too_small` | `complex`)

**Step 3.2: Map overlay (F6) — primary cross-check mechanism**

Add the map layer in `frontend/src/components/map/`:
- New layer entry in `LayerControl.tsx` LAYER_ITEMS: `building_footprints` and `usable_rooftops`
- Render as MapLibre vector layers, color-coded by classification:
  - `standard_roof` → green, full opacity 0.6
  - `elongated` → orange (derated), opacity 0.5
  - `tank_silo`, `conveyor`, `complex`, `too_small` → gray, opacity 0.3
- Layers visible only when at least one site is selected OR zoom level > 12 (avoid loading 81 sites worth of polygons at world view)
- Click on polygon → tooltip shows classification + area + which site it belongs to

**Step 3.3: BottomPanel table tab (F7)**

Add a new view in `frontend/src/components/ui/BottomPanel.tsx`:
- New tab/segment: "Solar Potential"
- Columns: site_name, sector, rooftop_solar_mwp, within_site_groundmount_mwp, regional_groundmount_potential_mwp_50km, building_count_total, building_count_standard_roof, data_confidence
- Sortable, filterable consistent with existing BottomPanel behavior
- Data source: the same scorecard API response — no new fetch

**Step 3.4: Score Drawer — solar potential section**

Add a section to the existing Resource tab in `frontend/src/components/panels/scoredrawer/ResourceTab.tsx`:

```
┌─ Solar Potential ──────────────────────────────────────┐
│                                                         │
│  [Stacked bar: Rooftop | Within-site | 50 km region]   │
│                                                         │
│  Rooftop:           35 MWp  (12 buildings, 8 excluded) │
│  Within-site:      120 MWp  (Y hectares buildable)     │
│  50 km regional:  2500 MWp  (external utility-scale)   │
│                                                         │
│  ⓘ Building data: Google Open Buildings v3 (May 2023)  │
│     Confidence: high                                    │
│     Toggle "Building footprints" map layer to verify   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

No new tab — section lives within the existing Resource tab to avoid Score Drawer tab proliferation.

**Step 3.5: Add tooltips linking each number to methodology**

Each number is hover-clickable to show data source, vintage, derating factors, and known limitations for that site.

**Step 3.6: Update PERSONAS.md**

Add rooftop and within-site ground-mount to Persona 5 (Industrial Investor) user journey. Note that v4.1 ships raw potential; cost integration follows in v4.2.

### Phase 4: Validation and publication (2-3 days)

**Step 4.1: Golden-master tests**

Write `tests/test_rooftop_solar.py` with 5 fixture sites. Lock in expected rooftop MWp values. Tests fail if any site changes by >10%.

**Step 4.2: Manual validation on 10 sites**

Use Google Earth Pro to manually measure rooftop area on 10 random sites. Compare to automated output. Target: ±20% agreement (tightened from ±30% pre-review). Document discrepancies.

**Step 4.2b: Classifier calibration (§14.6)**

Manually classify 100 buildings (5 sites × 20 each) and compare to §14.3 classifier output. If accuracy < 80%, tune thresholds in `assumptions.py` and re-run. Do NOT merge with unverified thresholds.

**Step 4.3: Methodology documentation**

Add new section to `METHODOLOGY_CONSOLIDATED.md`:
- §X.1 Within-boundary solar potential — rationale
- §X.2 Rooftop potential methodology
- §X.3 Within-site ground-mount methodology
- §X.4 Relationship to 50km regional potential
- §X.5 Data sources and vintage
- §X.6 Derating factors with citations
- §X.7 Known limitations and confidence flagging

**Step 4.4: Publish v4.1 to Zenodo**

New DOI for the version with rooftop potential. Include download link to the processed Indonesia Open Buildings extract (if license permits) or instructions to reproduce.

**Step 4.5: Write Substack Post 3 or 4 featuring rooftop potential**

The rooftop potential analysis is genuinely novel for Indonesia. No other public tool does this at the industrial site level. This becomes a standalone story: "I mapped rooftop solar potential across Indonesia's 81 biggest industrial sites. Here's how much behind-the-meter solar is available without any new land or grid approvals."

---

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Google Open Buildings v3 undercounts post-2023 nickel expansions | High | Medium | Confidence flagging; manual fallback for 4-5 flagged sites; document limitation prominently |
| Building footprints from wrong imagery date misalign with current reality | Medium | Low | Cross-check with current Google Earth imagery during QA; note in methodology |
| Usability derating (0.50) too aggressive or too lenient for Indonesian industrial rooftops | Medium | Medium | Document the assumption; allow user override via adjustable slider; add Indonesia-specific study to backlog |
| Thermal derating underestimates tropical losses | Low | Low | Cross-check against PVGIS simulated yield for 3 sites; adjust if needed |
| Spatial join performance issues at scale | Low | Low | Pre-build R-tree; use GeoParquet; profile before optimizing |
| Rooftop ≠ roof because Google detects building footprints (ground area), not roof area | Low | Low | For flat industrial roofs (majority case), footprint ≈ roof. For sloped roofs (rare in industrial), adds ~20% undercount. Document. |
| Misalignment between site polygons and actual site boundaries causes over- or under-counting | Medium | Low | Review site polygons during QA; note any obviously incorrect boundaries |
| License compliance confusion (CC BY vs ODbL) | Low | Low | Pick CC BY-4.0; provide attribution in Zenodo publication and GitHub README |

---

## 8. Dependencies and Prerequisites

**Data:**
- Site polygons for all 81 sites (already exist in `fct_industrial_sites.csv`)
- Google Open Buildings v3 Indonesia extract (needs download)
- Existing buildability filter logic (already in pipeline)

**Code:**
- `geopandas` for spatial operations (check if already in dependencies)
- `shapely` for geometry ops (already in dependencies)
- `pyarrow` for GeoParquet (check)
- Google Cloud `gsutil` CLI for data download (one-time)

**Infrastructure:**
- ~15 GB disk space for processed building data
- ~2-4 GB RAM for spatial joins across 81 sites

**Other:**
- Zenodo account for v4.1 DOI publication
- GitHub repo access for code changes

---

## 9. Open Questions

### 9.1 Resolved (post-review)

| Q | Resolution |
|---|---|
| Q1: Rooftop usable share — 50% or 65%? | **50% for v4.1**, exposed as `ROOFTOP_USABLE_SHARE` slider in AssumptionsPanel (range 0.40–0.70). Document NREL source. |
| Q4: Should rooftop LCOE differ from ground-mount? | **Same as ground-mount for v4.1**, with explicit UI flag "Rooftop LCOE assumed equal to ground-mount; differentiation pending v4.2." |
| Q (new): How does rooftop integrate with Supply Blend cascade? | **Two views.** Estate Supply Blend unchanged; new Tenant Supply Blend includes rooftop. See §3.4. |
| Q (new): When does the rename land? | **Separate prerequisite PR before this feature.** See §3.1 F5. |

### 9.2 Still open

**Q2: Thermal derating regional variation.**
Bontang is coastal and humid. Morowali is equatorial tropical. Indonesian thermal derating varies 10-15% across regions. For v4.1, use a flat 12% (0.88 factor). Regional variation deferred to v4.2 — captured as TODO.

**Q3: Imprecise site polygons.**
Some site polygons are tight around factories; others are loose boundaries including wide buffers. This affects what "within-boundary" means. For v4.1, use polygons as-is and document this as a §14.7 limitation. Polygon tightening is a separate workstream.

**Q5: Publishing the processed Indonesia building extract on Zenodo.**
Check Google Open Buildings license. CC BY-4.0 allows redistribution with attribution. Decision: yes, publish as a derived dataset alongside v4.1 DOI if the filtered file is under 100 MB. Useful public good.

---

## 10. Success Criteria for v1

Before declaring the feature shipped:

- [ ] All 81 sites have rooftop_solar_mwp_potential populated (null only if data confidence = low, with explanation)
- [ ] All 81 sites have within_site_groundmount_mwp populated
- [ ] Existing max_captive_capacity_mwp renamed to regional_groundmount_potential_mwp_50km
- [ ] Score Drawer displays three-way split with tooltips
- [ ] Golden-master tests pass for 5 fixture sites
- [ ] Manual validation on 10 random sites shows ±30% agreement
- [ ] Methodology document updated with full data source and derating documentation
- [ ] PERSONAS.md updated with rooftop potential in Persona 5 journey
- [ ] v4.1 published to Zenodo with new DOI
- [ ] CHANGELOG.md entry under Unreleased → v4.1

---

## 11. Follow-On Features (Post v1)

**v4.2 — Rooftop vs ground-mount LCOE differentiation.** Model higher CAPEX for rooftop, no land cost. Produces rooftop-specific LCOE that may flip more sites to competitive.

**v4.3 — Parking canopy / solar carport potential.** Add land-cover classification from Sentinel-2 to detect paved lots. Meaningful additional potential (10-30% of building footprint area) for sites with large parking areas.

**v5.0 — Temporal tracking.** Monitor rooftop area changes using Google Open Buildings Temporal Dataset. For rapidly expanding sites, track "how much new rooftop solar potential was created last year?"

**v5.1 — Shade analysis.** Use DSM (Digital Surface Model) to compute shading from adjacent tall structures. Relevant for dense industrial estates.

**v5.2 — Structural load assessment.** Pull building construction type data where available; derate rooftops that can't support solar mounting loads. Mostly speculative — no public dataset exists for Indonesia.

---

## 12. Estimated Timeline

Revised again post-scope-cut (was 2 weeks → 3-4 weeks → now 3 weeks after deferring Supply Blend integration):

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 0: Prerequisite rename PR | 0.5 day | `regional_groundmount_potential_mwp_50km` lands; deprecation alias for one release |
| Phase 1: Data acquisition + POC | 3-4 days | Indonesia GoB v3 extract, GeoParquet, R-tree, 5 sites computed end-to-end |
| Phase 2: Pipeline integration | 4-5 days | All 81 sites computed; assumptions.py wired; CRS unit tests; classify_building tests |
| Phase 3: Frontend integration | 3-4 days | Map overlay (F6) + BottomPanel tab (F7) + Score Drawer section in Resource tab |
| Phase 4: Validation + publication | 3-4 days | Manual validation on 10 sites; classifier calibration on 100 buildings; methodology + Zenodo |
| **Total** | **~3 weeks** | **v4.1 release** |

What was cut from the 3-4 week v2 estimate: Tenant Supply Blend cascade (~3-4 days), connection capacity sourcing, two-view UI toggle. All deferred to v4.2 (§18). Classifier calibration stays — it's what makes the headline number defensible.

Compressed: 2 focused weeks if other work pauses. Realistic 3 weeks with normal parallel work.

---

## 13. Lightweight Data Strategy

### 13.1 The tension

Google Open Buildings v3 globally is 178 GB. The Indonesia subset could be 5-15 GB. The current dashboard pipeline produces compact CSVs, runs quickly, and clones in seconds. Adding a multi-GB building dataset to every pipeline run, every developer checkout, and every deployment would break the "fast to clone, fast to run, fast to deploy" principle.

The solution is a three-layer data strategy: bulky raw data stays external and one-time, spatially-filtered intermediate data is small and cached, and only aggregated site-level outputs touch the runtime pipeline.

### 13.2 Three-layer architecture

**Layer 1: Raw data (external, one-time download, never committed)**

- Full Indonesia building footprint extract from Google Open Buildings v3
- Size: estimated 5-15 GB (CSV with WKT geometries)
- Location: local disk during preprocessing OR cloud bucket (Google Cloud Storage, S3)
- Access: only via preprocessing script, never by runtime pipeline
- NOT in git repo, NOT in deployment artifact, NOT in Docker image

**Layer 2: Spatially-filtered intermediate (cached, optionally committed)**

- Buildings within a 2 km buffer of any of the 81 site polygons
- Filter logic: union all site polygons buffered by 2 km, clip Indonesia building dataset to this union
- Confidence filter: apply 90% precision threshold per S2 cell
- Size: estimated 15-60 MB as GeoParquet (after 99%+ spatial reduction + Parquet compression)
- Location: `data/processed/sites_buildings_filtered.parquet`
- Decision: commit to git if under 50 MB, otherwise store externally with download script

**Layer 3: Aggregated site-level outputs (always committed)**

- Per-site precomputed metrics: rooftop area, usable rooftop, rooftop MWp, within-site groundmount area, within-site groundmount MWp, building count, confidence flag
- Size: 81 rows × 10 columns ≈ 10 KB CSV
- Location: `data/processed/fct_site_solar_potential.csv`
- Always committed, always the single source of truth for the runtime pipeline

### 13.3 Why the 2 km buffer

Industrial site polygons may not perfectly match actual fence boundaries. A 2 km buffer captures buildings that are logically part of the site but fall outside the polygon due to geocoding imprecision. It also catches satellite facilities (warehouses, shipping terminals) that belong to the same industrial operation but sit just outside the main polygon.

The buffer must be large enough to forgive polygon error but small enough to maintain the spatial filter's effectiveness. 2 km is the balance. At 2 km, Indonesia's 1.9 million km² reduces to roughly 10,000-30,000 km² of buffered industrial areas. That's a 99%+ reduction in data volume while preserving coverage.

### 13.4 Preprocessing script design

Write `scripts/preprocess_open_buildings.py` as a standalone, idempotent script:

```python
"""
One-time preprocessing: filter Google Open Buildings v3 Indonesia
to buffered areas around the 81 industrial sites.

Usage:
    python scripts/preprocess_open_buildings.py \
        --raw-data /path/to/idn_open_buildings.csv \
        --sites data/raw/fct_industrial_sites.csv \
        --buffer-km 2 \
        --output data/processed/sites_buildings_filtered.parquet

Outputs:
    sites_buildings_filtered.parquet  # spatially filtered buildings
    sites_buildings_filter_stats.json  # filter stats for audit
"""
```

Key properties:
- Runs once after data refresh, not on every pipeline run
- Takes 5-15 minutes on standard hardware
- Produces reproducible outputs (same inputs + same buffer = identical output)
- Logs filter statistics (input count, output count, total area, reduction ratio)
- Script itself is small and committed; its output is gated on size

### 13.5 Runtime pipeline changes

The daily/per-run pipeline (`build_fct_site_resource.py`) should:

1. Read the pre-filtered GeoParquet (or aggregated CSV, if that exists)
2. For each site, do an in-memory spatial join with the ~15-60 MB filtered dataset
3. Compute aggregates and write `fct_site_solar_potential.csv`

This is fast (under 1 minute for 81 sites) and uses under 500 MB RAM. No access to the 5-15 GB raw dataset required at runtime.

### 13.6 Deployment and CI

**Option A: Commit the filtered intermediate (if under 50 MB).** Simpler, self-contained repo, but repo grows slightly.

**Option B: External storage with download script (if over 50 MB).** Publish the filtered intermediate on Zenodo alongside the methodology, or on Google Cloud Storage. Runtime pipeline downloads once and caches. Slightly more complex deployment but keeps repo small.

**Recommendation: Option A if possible.** At 15-60 MB, it's within git-LFS territory. Treat as a standard data artifact. Only move to external storage if the filtered intermediate grows above 100 MB (which would require an unexpectedly large number of buildings near your sites — unlikely given Indonesia's industrial geography).

### 13.7 Data refresh policy

When Google Open Buildings v4 is released (or when you want to refresh with newer imagery):

1. Download new raw data externally (one time, ~15 GB)
2. Re-run `preprocess_open_buildings.py` with same buffer and threshold settings
3. Re-run `build_fct_site_resource.py` to update aggregated outputs
4. Check `fct_site_solar_potential.csv` diff — which sites changed meaningfully?
5. Update CHANGELOG and publish new Zenodo DOI
6. Document the vintage update in methodology

The raw dataset never enters the normal dev workflow. Only refreshing it is a "big data" operation, and it happens maybe once a year.

### 13.8 Size budget summary

| Artifact | Size | Lifecycle | In Repo? |
|---|---|---|---|
| Google Open Buildings raw Indonesia | 5-15 GB | External, one-time | No |
| Filtered buildings GeoParquet | 15-60 MB | Cached, refreshable | Yes (if <50 MB) or External |
| Aggregated site outputs CSV | 10 KB | Always fresh | Yes |
| Preprocessing script | <20 KB | Permanent | Yes |
| Methodology doc updates | <20 KB | Permanent | Yes |

**Repo growth from this feature: <100 MB. Runtime pipeline memory: <500 MB. Deployment size impact: negligible.**

This maintains the lightweight character of the existing architecture. The heavy data work happens once, externally, and produces small cached outputs that the runtime pipeline consumes efficiently.

### 13.9 Failure modes and mitigations

| Risk | Detection | Mitigation |
|---|---|---|
| Filtered intermediate grows above 100 MB unexpectedly | File size check in preprocessing | Move to external storage; add download script |
| Spatial filter misses relevant buildings | Site-level building count drops significantly after re-filter | Spot-check flagged sites; increase buffer if systematic |
| Raw dataset URL changes or is removed | Preprocessing script fails | Document download alternatives (HDX, Earth Engine); pin v3 as long as available |
| Preprocessing runs slowly | Script runtime >30 min | Profile; likely the spatial join is the bottleneck; pre-build spatial index |
| Git-LFS adds deployment complexity | Deploy takes longer | Evaluate Option B if impact is meaningful |

### 13.10 Forward-compatibility invariants for multi-source data (v4.1 → v4.2)

**Why this section.** v4.1 ships Google Open Buildings v3 as the only source. v4.2+ will need Microsoft GMLBF (post-2023 sites), manual KMLs (coordinate-corrected sites), and possibly OSM. The original v4 spec proposed a full `_base.py` plugin architecture in v4.1 — eng review (2026-04-27) flagged this as YAGNI: the contract was shaped from one example and didn't actually fit MS GMLBF (no confidence scores), manual KML (no s2 token), or OSM (rich tag info classifier could exploit).

**Resolution.** Defer the abstraction to v4.2 (when MS GMLBF gives us a second concrete shape to fit). Instead, v4.1 enforces SIX forward-compatibility invariants in the existing concrete code. Together they make v4.2's "add MS GMLBF" PR additive (new module + register it) instead of a rewrite.

#### The 6 invariants

| # | Invariant | What it prevents in v4.2 |
|---|---|---|
| **1** | `sites_buildings_filtered.parquet` has columns `source_name` (str) and `source_vintage` (str) — single value `"gob_v3"` / `"2023-05"` in v4.1, varies in v4.2. | Without these columns, adding MS GMLBF rows means migrating the parquet schema and every reader. With them, MS GMLBF rows just have different values. |
| **2** | `building_id` is a STRING with source prefix (`"gob_v3:1234567"`), not int64. | When MS GMLBF rows arrive with their own integer IDs, prefix prevents collisions. Sets the merge key for v4.2. **Real change to the v4.1 implementation as currently shipped — preprocess_open_buildings.py writes int64.** |
| **3** | `dim_sites` gains a nullable `preferred_building_source` column. All null in v4.1; v4.2 populates per-site overrides ("post-2023 nickel IIA → ms_gmlbf"). | Avoids a dim_sites schema migration in v4.2. |
| **4** | One single function `load_buildings_for_pipeline()` in `src/pipeline/build_fct_site_solar_potential.py` is the only place that knows the parquet path. | v4.2 changes ONE function (fan out to multiple sources + merge); downstream callers see no change. Whole abstraction collapses into one function signature. |
| **5** | Confidence handling treats `None` / `NaN` as "no score" gracefully. F4 logic uses `source_name` / `vintage` to set confidence flags when score is null. | MS GMLBF doesn't publish confidence scores. Code must NOT assume `confidence ∈ [0, 1)`. |
| **6** | F4 confidence flag reads `source_vintage` from the data, not from a hardcoded `BUILDING_DATA_VINTAGE_YEAR_CUTOFF` compared against `commissioning_year`. | When MS GMLBF rows arrive (refreshed quarterly), vintage cutoff is per-row, not global. Same logic, vintage-driven. |

#### v4.2 additive PR (when MS GMLBF lands as L26)

1. New module `src/pipeline/building_sources/ms_gmlbf.py` — produces same parquet schema (~100 LOC).
2. Modify `load_buildings_for_pipeline()` to fan out + merge by (`building_id`, `dedup_radius_m`) — change one function.
3. Populate `dim_sites.preferred_building_source` for the 8 post-2023 sites.
4. New tests for source-merge behavior.

**Zero changes to:** §14 classifier, aggregator, tile generator, API endpoints, frontend. The 6 invariants buy this without the upfront `_base.py` cost.

#### What to test in v4.1 to lock the invariants

- `sites_buildings_filtered.parquet` schema includes `source_name`, `source_vintage`, prefixed `building_id` — assertion in `tests/test_preprocess_open_buildings.py`
- `dim_sites.preferred_building_source` exists (all null) — schema test
- `load_buildings_for_pipeline()` is the only `pd.read_parquet("sites_buildings_filtered.parquet")` callsite — grep test in `tests/test_invariants.py`
- F4 logic accepts null/NaN confidence without crashing — unit test
- F4 logic uses per-row `source_vintage` — unit test

---

### 13.11 Storage policy — keep raw locally, discard waste, commit post-processed

**Three storage layers, three policies.**

```
┌───────────────────────────────────────────────────────────────────────────┐
│ Layer 1: data/open_buildings/idn_open_buildings.csv.gz       (~6.7 GB)    │
│ Raw merged GoB v3 extract for the 41 cells covering all 81 sites.         │
│   ↳ gitignored (data/open_buildings/ in .gitignore)                       │
│   ↳ kept on disk locally to support cheap re-runs when sites change       │
│   ↳ not part of the deploy artifact                                        │
└───────────────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ Layer 1 waste: data/open_buildings/_tmp_cells/*.csv.gz       (~6 GB)      │
│ Per-cell intermediates outside the 41-cell site footprint.                │
│   ↳ ALWAYS DELETE after the merge step succeeds                           │
│   ↳ scripts/merge_open_buildings_cells.py --cleanup-wasted does this      │
│   ↳ regenerable from Layer 1 via fetch_missing_cells.py                   │
└───────────────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ Layer 2: data/processed/sites_buildings_filtered.parquet     (~12.3 MB)   │
│ Site-buffered, confidence-thresholded buildings. The dashboard's input.   │
│   ↳ COMMITTED to git (per spec §13.2 Option A: <50 MB threshold)          │
│   ↳ regenerated by scripts/preprocess_open_buildings.py from Layer 1      │
└───────────────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ Layer 2.5: data/processed/sites_rooftop_tiles.parquet         (~50 MB est)│
│ Per-building panel-tile geometry for visual rendering.                    │
│   ↳ COMMITTED if <50 MB; gitignored + regenerable if larger               │
│   ↳ regenerated by src/pipeline/build_rooftop_tiles.py                    │
└───────────────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────────────┐
│ Layer 3: outputs/data/processed/fct_site_solar_potential.csv  (~10 KB)    │
│ Per-site aggregated rooftop MWp / building counts / confidence flag.      │
│   ↳ COMMITTED — the runtime pipeline reads this directly                  │
│   ↳ regenerated by src/pipeline/build_fct_site_solar_potential.py         │
└───────────────────────────────────────────────────────────────────────────┘
```

**When sites are added (M22 / M28 / M29 → expanded site list):**

1. Re-run `check_open_buildings_coverage.py` → identify newly-needed S2 cells
2. Run `fetch_missing_cells.py --auto` → grab the new cells (typically 0-5 cells)
3. Run `merge_open_buildings_cells.py --cleanup-wasted` → rebuild Layer 1, delete new waste
4. Run `preprocess_open_buildings.py` → rebuild Layer 2
5. Run `build_rooftop_tiles.py` + `build_fct_site_solar_potential.py` → rebuild Layers 2.5 and 3
6. Commit only the regenerated parquet/CSV (Layers 2, 2.5, 3). Layer 1 stays gitignored.

Total marginal cost of adding 1-5 sites: ~10 minutes of recompute, ~10 KB of git diff.

**Failure mode coverage.**

| Risk | Detection | Mitigation |
|---|---|---|
| Layer 1 deleted accidentally | Pipeline fails at preprocess step | Re-run `download_open_buildings.py` (~hour) or `fetch_missing_cells.py` (~minutes if cells partial) |
| Layer 2 grows above 50 MB after site additions | `git status` shows large file | Move to gitignored + add download script; document in §13.2 |
| Layer 2.5 grows above 50 MB | Pre-commit hook checks file size | Switch to gitignored + add to pipeline regenerate step |
| `_tmp_cells/` not cleaned up after merge | Disk usage check in CI / manual | `merge_open_buildings_cells.py --cleanup-wasted` as part of the standard run |

---

## 14. Building-Type Filtering for Rooftop Suitability

### 14.1 The problem

Google Open Buildings detects building *footprints* — the ground area occupied by any structure. It does not distinguish roof type, structure type, or whether the building has a solar-compatible flat roof. For industrial sites, this matters enormously because the detected "buildings" include:

| Structure type | Typical share at heavy industry | Solar suitability |
|---|---|---|
| Flat-roof warehouse/factory | 40-60% | High (ideal) |
| Pitched-roof office/admin | 5-15% | Medium (possible with mounting adapters) |
| Storage tanks (round, cylindrical) | 10-25% | None (curved top, no flat surface) |
| Silos (conical, domed) | 5-15% | None (sloped top, not accessible) |
| Cooling towers | 2-5% | None (open top, evaporative) |
| Process vessels and reactors | 5-15% | None (complex geometry) |
| Conveyor sheds (long, narrow) | 2-10% | Low (narrow footprint, limited panel rows) |
| Chimneys and stacks | 1-3% | None (vertical, negligible roof) |

For a commercial warehouse district, 80-90% of detected footprints are usable roofs. For a nickel RKEF smelter or fertilizer complex, maybe 40-50%. For a petrochemical refinery, possibly 20-30%. Applying a flat 50% usable-share across all sites systematically overstates rooftop potential for heavy industry and understates it for light industry.

This is a bigger issue than the initial spec (§5.3) captured. The existing 5-layer buildability filters don't help — they filter *land*, not *building types*.

### 14.2 Geometric filtering approach

Google Open Buildings provides polygon geometry for each detected structure. From geometry alone, you can compute shape characteristics that correlate strongly with structure type:

**Circularity (roundness index)**

Formula: `circularity = 4π × area / perimeter²`

- Perfect circle: 1.0
- Regular rectangle: ~0.6-0.7
- Irregular warehouse with protrusions: ~0.4-0.5
- Elongated shapes: <0.3

A circularity above 0.85 is almost certainly a tank, silo, or storage vessel. These should be excluded from rooftop calculations.

**Aspect ratio**

Formula: `aspect_ratio = bounding_box_length / bounding_box_width`

- Square-ish warehouse: 1.0-2.0
- Typical factory: 2.0-4.0
- Conveyor shed or pipe rack: 6.0+

Very elongated structures (aspect ratio > 6) are typically conveyors or covered walkways with limited practical solar area. Derate heavily or exclude.

**Minimum size threshold**

Structures below ~200 m² are typically too small for commercial solar (below the economic threshold for a meaningful installation) or are likely non-buildings (equipment housings, guard posts, small tanks).

**Convex hull ratio**

Formula: `convex_ratio = actual_polygon_area / convex_hull_area`

- Simple rectangular roof: 0.95-1.0
- Warehouse with loading docks: 0.85-0.95
- Complex process equipment cluster: <0.7

Highly irregular shapes (ratio <0.75) are often process equipment clusters detected as a single polygon rather than a single clean roof surface.

### 14.3 Classification logic

**Important: thresholds below are starting points, not defaults to ship.** §14.6 manual validation on 100 buildings runs BEFORE merge. If classifier accuracy is < 80%, tune thresholds and re-run validation until met. Do not ship unverified thresholds — that's giving the data more precision than it earned.

All thresholds live in `src/assumptions.py` (see §5.3 table). The values below are hypotheses to be confirmed:

Combine the geometric filters into a four-category classification:

```python
def classify_building(polygon, area_m2):
    circularity = 4 * math.pi * polygon.area / polygon.length**2
    bbox = polygon.minimum_rotated_rectangle
    width, length = sorted(bbox.edge_lengths())
    aspect = length / width if width > 0 else float('inf')
    hull_ratio = polygon.area / polygon.convex_hull.area

    # Reject outright
    if area_m2 < 200:
        return 'too_small', 0.0
    if circularity > 0.85:
        return 'likely_tank_silo', 0.0
    if aspect > 8:
        return 'likely_conveyor', 0.1  # minimal usable roof

    # Derate for complexity
    if hull_ratio < 0.70:
        return 'complex_process', 0.2  # partial roof at best

    # Derate for slightly round (could be dome or tank)
    if circularity > 0.75:
        return 'possibly_round', 0.3

    # Derate for narrow/elongated
    if aspect > 5:
        return 'elongated', 0.6

    # Default: standard industrial roof
    return 'standard_roof', 1.0  # full usable fraction applies
```

Each category returns a **building-type usability multiplier** (0.0 to 1.0) that's applied on top of the generic rooftop-usable-share factor (0.50).

### 14.4 Effect on rooftop calculation

Revised rooftop area calculation per site:

```python
def compute_site_usable_rooftop_area(buildings_in_site):
    total_usable = 0
    excluded_by_type = 0
    for building in buildings_in_site:
        category, type_multiplier = classify_building(building.geometry, building.area)
        usable_fraction = ROOFTOP_USABLE_SHARE * type_multiplier  # e.g. 0.50 × 1.0 = 0.50
        usable_area = building.area * usable_fraction
        total_usable += usable_area
        if type_multiplier == 0:
            excluded_by_type += building.area
    return total_usable, excluded_by_type
```

Where `ROOFTOP_USABLE_SHARE = 0.50` remains the blanket "accounting for HVAC, skylights, setbacks" derating, now stacked on top of building-type classification.

Expected effect:
- Heavy industry sites (nickel, steel, refining): 30-50% lower rooftop MWp vs v1 (uncorrected)
- Light industry sites (cement, fertilizer with large warehouses): 10-20% lower
- Commercial/logistics sites: 0-10% lower
- Net: more accurate and more honest numbers

### 14.5 New output fields

Add to `fct_site_solar_potential.csv`:

```
building_count_total              # raw count detected
building_count_standard_roof      # classified as standard rooftop
building_count_tank_silo          # excluded as tanks/silos
building_count_conveyor           # excluded as conveyors
building_count_other_excluded     # too small, complex process, etc.
total_footprint_m2                # raw sum of all building areas
usable_roof_area_m2               # after type classification + usable share
type_filter_excluded_m2           # how much area filtered by type
```

Surface the type-filter-excluded number in the Score Drawer tooltip. A user should be able to see: "We detected 145 buildings totaling 240,000 m² of footprint. Of these, 38 buildings (85,000 m²) were classified as tanks, silos, or non-rooftop structures and excluded. Usable rooftop area after typing: 72,000 m² → 12 MWp."

That transparency is worth the extra columns. It lets users understand why the rooftop potential at a refinery is lower than at a cement plant even though total footprint might be similar.

### 14.6 Validation strategy

Manual validation on 20 random buildings per site, for 5 fixture sites (100 buildings total). For each:
- Load polygon in QGIS or Google Earth Pro
- Visually inspect against current satellite imagery
- Record: is it classified correctly?
- Target: >80% agreement between automated classification and manual inspection

If the classifier fails systematically on certain structure types, tune the thresholds. If it fails randomly, the geometric approach is hitting its limit and you'd need a CNN-based classifier on the underlying imagery — which is out of scope for v1.

### 14.7 Honest limitations

Geometric filtering is a proxy for what you actually want to know (can I put solar on this roof?) and it has known failure modes:

- **Flat-topped silos** can look similar in footprint to warehouses. Without height data, you can't distinguish.
- **Buildings with unusual shapes** that happen to be rooftop-suitable might get over-filtered.
- **Roof pitch** is invisible to 2D geometric analysis. A pitched warehouse roof looks the same as a flat one in footprint.
- **Structural load capacity** varies wildly and is completely invisible. A 50-year-old warehouse might not support modern solar mounting loads.

These limitations stack with the Google Open Buildings vintage limitation (§13). Document them prominently. The rooftop MWp numbers are estimates with meaningful uncertainty bands, not precise values.

### 14.8 Alternative: OSM building tags (where available)

OpenStreetMap has a `building=*` tag that, where populated, directly classifies structure type. Values include:
- `building=warehouse`, `building=industrial`, `building=factory` → likely rooftop-suitable
- `building=silo`, `building=storage_tank`, `building=water_tower` → excluded
- `building=yes` (generic, ~80% of OSM buildings) → no information

For well-mapped Java industrial zones, OSM tags give you ground-truth building types for a meaningful fraction. Use OSM tags where available as an override for the geometric classifier. Where OSM says `building=silo` on a polygon, trust OSM. Where OSM says `building=yes` or no tag exists, fall back to geometric classification.

This is a supplementary improvement for Phase 2 or v4.2, not blocking for v1.

### 14.9 Recommended v1 implementation

Start with the four-category geometric classifier (§14.3). It catches the most obvious misclassifications (tanks, conveyors, very small structures) without requiring additional data sources or models. Ship this in v4.1 alongside the main rooftop feature.

Track the per-site "excluded by type" area and flag sites where >30% of detected footprint got filtered out. These are the heavy industry sites where the correction matters most — and where the naive rooftop number would have been most wrong.

---

## 15. Explicitly NOT in scope (v4.1)

Captured to prevent scope creep. **The big cuts from the v2 spec are in the top three rows** — these were originally in scope and got deferred during refinement:

| Item | Why deferred | Target version |
|---|---|---|
| **Supply Blend cascade integration (Tenant view)** | Architectural decision on per-tenant vs estate-level scales not yet resolved; v4.1 raw-potential story stands alone | **v4.2** |
| **ESDM 2/2024 deliverability cap** | Requires `connection_capacity_kva` per site (data sourcing exercise of its own) | **v4.2** |
| **Connection capacity data sourcing** | Tied to ESDM cap above | **v4.2** |
| Rooftop CAPEX differentiation | Has its own scope; rooftop doesn't feed cost cascades in v4.1 anyway | v4.2 |
| Time-of-day or hourly generation profiles | PyPSA handles separately | Future PyPSA work |
| Parking canopy / solar carport potential | Requires paved-area detection; separate Sentinel-2 land-cover classification | v4.3 |
| Rooftop structural load assessment | No public dataset for Indonesia building construction types | Speculative |
| Shading from adjacent tall structures | Requires DSM (Digital Surface Model) | v5.1 |
| Regional thermal derating variation | Flat 0.88 factor for v4.1 | v4.2 |
| Polygon tightening for imprecise site boundaries | Separate workstream | Independent |
| Microsoft Global Building Footprints comparison | TODO for v4.2 evaluation | TODO |
| Open Buildings 2.5D height integration | Better tank/silo classification once height data is integrated | TODO |
| OSM building tag override (§14.8) | Supplementary Phase 2 / v4.2 work | v4.2 |

---

## 16. Test Plan

100% coverage from day one. Every codepath introduced has tests written alongside, not deferred.

### 16.1 Unit tests

| Test file | What it covers | Critical assertions |
|---|---|---|
| `tests/test_classify_building.py` | §14.3 geometric classifier per category | One fixture polygon per category (tank, conveyor, complex, standard); accuracy ≥80% on 100 manually-labeled fixtures (§14.6) |
| `tests/test_crs_reprojection.py` | EPSG:23830 reprojection edge cases | Equator-crossing site (Pomalaa); east extreme (Weda Bay); Java (Cilegon); area preservation within 1% of authoritative source |
| `tests/test_compute_rooftop_solar_potential.py` | Per-site rooftop calc | Empty buildings list → returns 0 with `low` confidence; standard mix → matches golden value within 5%; missing parquet → `FileNotFoundError`, NOT silent zero |
| `tests/test_compute_within_boundary_groundmount.py` | Within-site ground calc | Building subtraction → buildable area = polygon - buildings - 5-layer mask; assertion `rooftop + within_site_ground ≤ polygon_area` |
| `tests/test_confidence_flag.py` | F4 derived signals | Each branch (low/high/medium) has a fixture; thresholds read from `assumptions.py` |
| `tests/test_building_footprints_layer.py` | F6 map overlay GeoJSON shape | Returns valid GeoJSON; classification field present on every feature; respects site-bounds filter |
| `tests/test_rooftop_tiles.py` | F8/F9 tile generation | Tile area sums to `layout_density × footprint_m²` ±2%; tiles fit inside polygon (no negative-buffer overflow); no overlapping tiles within a building |
| `tests/test_tile_aggregation.py` | F11/F12 click aggregation math | Single-tile, single-rooftop, and cluster sums match the per-site total to ±0.5% (rounding tolerance); MWh/yr derived from PVOUT exactly |
| `tests/test_panel_assumptions_live_recompute.py` | F10 slider recompute path | Changing `panel_power_w_dc` from 400 → 500 increases all rooftop_kw_dc rows by 25% exactly; tile geometry unchanged (only the per-tile capacity label changes) |
| `tests/test_missing_data_flag.py` | F13 alt-data shortlist | `sites_missing_buildings.csv` has expected 14 rows on the v4.1 fixture; each row has a non-null `recommended_alt_data` |
| `tests/test_interaction_states.py` | §3.8 state matrix coverage | Every (feature × state) cell has the expected UI element wired (loading skeleton renders, empty-state copy matches `missingDataMessages.ts`, error toast appears on parquet 500, partial-data spinner shows). |
| `tests/e2e/test_keyboard_a11y.spec.ts` | §3.9 keyboard navigation | Tab through `LayerControl → AssumptionsPanel sliders → map clusters → Score Drawer`. Arrow-key drag on slider. Enter on focused cluster opens popup. Screen reader (axe-core) reports no critical violations. |
| `tests/e2e/test_mobile_outlines.spec.ts` | §3.9 mobile responsive | At 375px viewport, tile toggle is disabled with "Desktop only" tooltip. Building outlines render. Score Drawer numbers still display. BottomPanel solar tab fully usable. |
| `tests/test_credibility_recovery.py` | §3.6 5% divergence rule | When summed cluster tile capacity diverges from headline by >5%, popup includes the rounding note string. ≤5% no note. Headline always wins. |

### 16.2 Integration tests

| Test file | What it covers |
|---|---|
| `tests/test_fct_site_solar_potential.py` | End-to-end pipeline run on 5 fixture sites; assert all new columns populated |
| `tests/test_estate_view_unchanged.py` | Existing Supply Blend cascade in `enrich_delivered_cost` returns identical values pre/post-feature for all 81 sites (rooftop must not leak into the cascade in v4.1) |

### 16.3 Golden-master tests

| Test file | What it covers |
|---|---|
| `tests/test_rooftop_solar_golden.py` | 5 fixture sites with locked rooftop MWp values; tolerance ±10%; sites: Krakatau Steel Cilegon, Petrokimia Gresik, IMIP Morowali, IWIP Weda Bay, KEK Sei Mangkei |

### 16.4 Regression tests

| Test file | What it covers |
|---|---|
| `tests/test_rename_alias.py` | Prerequisite PR — `max_captive_capacity_mwp` deprecation alias returns same value as `regional_groundmount_potential_mwp_50km` |

### 16.5 Failure-mode coverage

For each new codepath, one realistic production failure:

| Codepath | Failure mode | Test? | Error handling? | UX? |
|---|---|---|---|---|
| `preprocess_open_buildings.py` | GoB CSV download fails mid-stream | No (external one-time script) | Idempotent retry on next run | N/A — preprocessing |
| `build_fct_site_resource` extension | Buildings parquet missing | YES (`test_compute_rooftop_solar_potential`) | `FileNotFoundError`, NOT silent zero | Pipeline fails loud |
| `classify_building` | Polygon with zero area | YES (fixture) | Returns `too_small`, multiplier 0.0 | N/A — classifier internal |
| `compute_within_boundary_groundmount` | Building subtraction empties polygon | YES | Returns area=0, mwp=0; logs warning | UI shows "0 MWp" with explanation |
| `enrich_delivered_cost` | Rooftop must NOT leak into cascade in v4.1 | YES (`test_estate_view_unchanged`) | N/A — feature is intentionally isolated | Estate Supply Blend unchanged |
| API `/api/scorecard` response | New column null for low-confidence sites | YES (integration test) | Frontend handles null gracefully | UI shows "Data not available" |

**No silent failures.** Every error path either raises or logs + returns explicit null with a confidence flag.

---

## 17. Worktree Parallelization Plan

Steps to land in parallel after Phase 0 (rename PR) merges:

| Lane | Workstream | Modules touched | Depends on |
|---|---|---|---|
| **A** (parallel) | Backend pipeline | `src/pipeline/` (new + extended), `src/assumptions.py`, new API endpoint `/api/layers/building_footprints` | Phase 0 |
| **B** (parallel) | Frontend integration | `frontend/src/components/map/LayerControl.tsx`, `frontend/src/components/ui/BottomPanel.tsx`, `frontend/src/components/panels/scoredrawer/ResourceTab.tsx`, `frontend/src/lib/types.ts` | Lane A schema (column names) |
| **C** (parallel) | Methodology docs | `docs/METHODOLOGY_CONSOLIDATED.md`, `docs/TAXONOMY.md`, `DATA_DICTIONARY.md`, `PERSONAS.md` | Phase 0 |
| **D** (sequential after A) | Validation + Zenodo | `tests/`, methodology updates, classifier calibration | Lane A complete |

**Execution:**
- Phase 0 (rename PR) — solo, blocking
- Lane A + B + C — parallel worktrees after Phase 0 merges
- Lane B waits ~1 day for Lane A to publish the column schema + GeoJSON endpoint contract (in spec or draft API stub)
- Lane D — single worktree after Lane A merges; classifier calibration must complete before merge

**Conflict flags:**
- Lane A and B both touch the schema contract (`fct_site_solar_potential` columns + `/api/layers/building_footprints` GeoJSON); coordinate via spec, not via merge
- Lane C touches doc files that A and B don't; clean separation

---

## 18. Deferred TODOs (captured for follow-up)

Add to `TODOS.md` after the prerequisite rename PR merges. **The top three are scope cuts from v4.1 that need landing in v4.2** — they're the cost-integration story the v4.1 raw-potential ships without.

| Priority | TODO | Why | Effort estimate (CC) |
|---|---|---|---|
| **HIGH** | **Rooftop → Supply Blend integration (v4.2)** | v4.1 ships standalone potential; v4.2 connects it to the cost cascade. Two architectures to evaluate at that point: (a) 4-layer cascade `rooftop → wb → remote → grid`; (b) two-view UI with separate Tenant Supply Blend. | ~3-4 days |
| **HIGH** | **ESDM 2/2024 deliverability cap** | Apply `min(technical, connection_capacity_kva × pf / 1000)` so rooftop number reflects what's actually deliverable under PLTS Atap regulation, not just what's geometrically possible. | ~1 day after data sourcing |
| **HIGH** | **`connection_capacity_kva` field in `dim_sites`** | Required by ESDM cap above. Tier 1: KEK tenants from filings. Tier 2: peak demand × 1.2 proxy. Tier 3: intensity proxy. | ~3 days research |
| medium | Rooftop CAPEX differentiation (v4.2) | Higher $/kW than ground-mount; needs separate slider | ~2 days |
| medium | Microsoft Global Building Footprints comparison | Cross-validate GoB v3 on flagged-low sites; potentially better Indonesia coverage post-2023 | ~1 day |
| medium | Open Buildings 2.5D height integration | Building heights would replace geometric tank-vs-warehouse heuristic with ground truth | ~3 days |
| low | Regional thermal derating variation (Q2) | Currently flat 0.88; varies 10-15% across Indonesia regions | ~1 day |
| low | OSM building tag override (§14.8) | OSM has authoritative `building=*` tags for well-mapped Java zones | ~2 days |
| low | Polygon tightening for imprecise site boundaries (Q3) | Improves all "within-boundary" metrics | ~1-2 weeks (separate workstream) |
| **HIGH** (post-v4.1) | **L26 — Microsoft GMLBF integration for the 8 post-2023 missing sites** | Cross-reference `sites_missing_buildings.csv` against Microsoft Global Building Footprints (refreshed quarterly). Likely closes the gap on IWIP, Pomalaa, Buli, Konawe, Stardust, Red Lion Hongshi, Tanjung Sauh, Pupuk Iskandar Muda. | ~2 days |
| medium (post-v4.1) | **L27 — Unbundle thermal derate into full system loss chain** | v4.1 absorbs inverter / wiring / soiling / mismatch losses into the same `THERMAL_DERATE_TROPICAL` factor. v4.2 should expose `INVERTER_EFFICIENCY`, `DC_WIRING_LOSS`, `SOILING_LOSS`, `MISMATCH_LOSS` as separate constants — improves model transparency and lets users compare against PVGIS / NREL SAM. | ~1 day |
| medium (post-v4.1) | Manual coordinate verification for 3 sites with imagery gaps | Cemindo Gemilang Bayah, KEK Maloy Batuta, KEK Arun Lhokseumawe — Google Earth Pro spot-check + correct dim_sites coords if needed | ~half day |

---
