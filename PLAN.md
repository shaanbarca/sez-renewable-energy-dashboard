# Plan: Indonesia KEK Power Competitiveness Dashboard

<!-- /autoplan restore point: /Users/shaanbarca/.gstack/projects/sbarca10-eez/main-autoplan-restore-20260325-135101.md -->

**Branch**: main | **Commit**: 9477595 | **Date**: 2026-03-26 | **Phase 1: COMPLETE**

---

## What We're Building

A Dash-based dashboard that answers: **"Which of Indonesia's 24 KEK (Special Economic Zones) can offer low-cost, low-carbon, reliable electricity — and what must change to get there?"**

**Primary audience**: Development banks and energy investors (ADB, IFC, Macquarie Green, AIIB) doing due diligence on industrial location decisions or captive solar projects.

**Core unique insight**: The LCOE vs. grid cost gap at KEK level + "flip scenario" (which KEKs are one policy lever from solar-competitive) — this data join doesn't exist anywhere as an interactive tool.

---

## Architecture

**Stack**: Python / Dash / Plotly / Pandas / GeoPandas. Precomputed flat tables loaded at startup. No live raster operations at runtime.

**Data model (star schema)**:
- `dim_kek` — 24 KEK master table (name, province, sectors, status, lat/lon, geometry)
- `dim_tech_cost` — CAPEX/OPEX/lifetime from ESDM technology catalogue (already in `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv`)
- `fct_kek_resource` — PVOUT at centroid + best-within-50km + wind CF (precomputed from GeoTIFFs)
- `fct_lcoe` — Solar (and wind) LCOE bands per KEK × WACC assumption
- `fct_grid_cost_proxy` — PLN BPP per system/region (official when available, provisional otherwise)
- `fct_ruptl_pipeline` — Planned capacity by region/year/tech from RUPTL 2025–2034

**Key computed outputs**:
- `lcoe_usd_mwh` from `lcoe_solar(capex, fom, wacc, lifetime, cf)`
- `cf` derived from PVOUT via `capacity_factor_from_pvout(pvout) = pvout / 8760`
- Action flags: `solar_now`, `grid_first`, `firming_needed`, `plan_late`
- `solar_competitive_gap` — % by which solar LCOE exceeds grid cost proxy (negative = already competitive)

---

## Dashboard Modules (MVP)

1. **Indonesia overview map** — 24 KEK locations colored by clean power advantage score. Click → drill down.
2. **Quadrant chart** — Grid cost proxy (y) vs. Solar LCOE (x). Four zones: Go solar now / Grid first / Needs firming / Watch pipeline.
3. **WACC/scenario sidebar** — WACC slider (6–15%), CAPEX multiplier toggle, storage adder checkbox. All update the quadrant chart live.
4. **Ranked table** — KEKs sorted by clean power advantage. Drill-down into assumptions. CSV export.
5. **KEK scorecard** — Single-zone view: PVOUT, LCOE bands, grid cost proxy, action flag, RUPTL context, nearest substation distance.
6. **Flip scenario panel** — Which KEKs are within X% of solar-competitive under a given policy scenario.

---

## User Journey

1. Land on overview map → see spatial distribution at a glance
2. Set WACC slider to fund's hurdle rate → map and quadrant update live
3. Read quadrant chart → identify 3–5 candidate KEKs
4. Toggle flip scenario assumptions → see which KEKs cross the competitive threshold
5. Export ranked table as CSV → paste into investment memo
6. Drill into KEK scorecard → full data for due diligence
7. Cite GitHub Release version tag in investment committee report

---

## Delivery Phases

### Phase 1 — Data pipeline ✅ COMPLETE (2026-03-26)

All 8 tables built, 127 tests passing. Pipeline: `uv run python run_pipeline.py`

| Table | Rows | Status | Notes |
|-------|------|--------|-------|
| `dim_kek` | 25 | ✅ | Province, grid_region_id, reliability_req, polygon dedup |
| `dim_tech_cost` | 1 | ✅ | TECH006 solar PV; CAPEX=960 USD/kW, FOM=7.5 USD/kW/yr, lifetime=27yr — verified from p.66 |
| `fct_kek_resource` | 25 | ✅ | PVOUT centroid + best-50km; CF computed |
| `fct_grid_cost_proxy` | 7 | ✅ | I-4/TT OFFICIAL @$63.08/MWh (Permen ESDM 7/2024) |
| `fct_ruptl_pipeline` | 70 | ✅ | 7 regions × 10 years, RE Base + ARED; PDF extractor included |
| `fct_lcoe` | 75 | ✅ | 25 KEKs × 3 WACC (8/10/12%); is_capex_provisional propagated |
| `fct_kek_demand` | 25 | ✅ | 2030 demand by area × intensity; `demand_mwh_user` override column (nullable Float64) |
| `fct_kek_scorecard` | 25 | ✅ | All joins + action flags + green_share_geas (real, not hardcoded 0) + competitive gap |

**Architecture delivered:**
- Config-driven orchestrator (`run_pipeline.py`) with topological sort
- Builder pattern: each table = one `build_*()` function in `src/pipeline/`
- RAW/STAGING/TRANSFORM sections within every builder
- Centralized assumptions: `src/assumptions.py` (all constants + source citations, two-factor demand intensity)
- PDF extractors: `src/pipeline/pdf_extract_ruptl.py` and `pdf_extract_esdm_tech.py` — shared pattern: try pdfplumber → fall back to `VERIFIED_*` hardcoded dict on failure (image-based pages, missing PDF, layout change). Callers never see None.
- Template: `src/pipeline/TEMPLATE.py` for new datasources
- `resolve_demand()` in `basic_model.py` — single entry point for demand overrides (pipeline + Dash app)
- Demand override hook: `demand_mwh_user` column in `fct_kek_demand` → Dash app populates for live recalculation

**Deferred to Phase 2:**
- Wind CF (Global Wind Atlas GeoTIFF) — same rasterio pipeline, additive
- Substation proximity (`dist_to_nearest_substation_km`) — data in repo

### Phase 2 — Model layer + scorecard enhancements ✅ COMPLETE

**Built (commits d9b2c77 → a6017b1):**

| Feature | What was built | Decision |
|---------|---------------|----------|
| Substation proximity | `fct_substation_proximity.csv` — haversine distance to nearest PLN substation; `siting_scenario` (within_boundary / remote_captive). Gen-tie CAPEX adder integrated into `fct_lcoe`. | `d92189e` |
| `invest_resilience` flag | Fires when 0 < solar_competitive_gap ≤ 20% AND reliability_req ≥ 0.75. At WACC=10%: 4 KEKs (Kendal, Gresik, Batang, Bitung — all manufacturing). Rationale: manufacturing outage cost (~$50–200/MWh lost production) justifies premium over grid parity. | `d9b2c77` |
| `carbon_breakeven_usd_tco2` | `lcoe_gap / grid_emission_factor` (USD/tCO2). Uses Operating Margin (OM) — emission intensity of existing plants displaced by captive solar. Range: $3.4 (Mandalika, diesel grid) → $36.6 (Morotai). | `d9b2c77` |
| Grid emission factors | Replaced provisional estimates with **KESDM Tier 2 OM values, 2019** (`data/grid_emission_factors.xlsx`). All 7 grid_region_ids explicitly mapped. Largest corrections: KALIMANTAN 0.72→1.16, NTB 0.78→1.27, MALUKU/PAPUA now correctly mapped (were using wrong default). | `2bb0771` |
| WACC=8% flip columns | `lcoe_mid_wacc8_usd_mwh`, `solar_competitive_gap_wacc8_pct`, `solar_now_at_wacc8`. 8 KEKs flip at WACC=8% (vs 0 at WACC=10%). Answers DFI question: "what financing de-risking is needed?" | `e4f003d` |
| Industrial tariff docs | I-3/I-4 implementation confirmed as complete (OFFICIAL). BPP explicitly deferred — using I-4/TT ($63.08/MWh) is correct; BPP would overstate grid cost. | `4b7b1d3` |
| Methodology "why it matters" | Added purpose rationale for `invest_resilience` thresholds, GEAS green share (GEAS vs. captive solar as substitutes), and emission factor table. | `2bb0771` |
| Stale doc cleanup | TECH006 "not yet extracted" → verified values; `kek_grid_region_mapping` "does not exist" → ✅ 26 rows; all Phase 1 open questions marked resolved or explicitly deferred. | `a6017b1` |

**Deferred from Phase 2 original scope:**
- ⏳ Land cover buildability filter — `pvout_best_50km` still upper bound; deferred to v1.1
- ⏳ 3-page Dash app — moved to Phase 3 (validate data model with personas first)
- ⏳ Wind CF — no Global Wind Atlas integration yet

**Phase 2 closeout state:** 25 KEKs, 43-column scorecard, all `data_completeness: complete`, 171 tests passing.

### Phase 3 — Dash app + open data release

**Design doc:** [DESIGN.md](DESIGN.md) — 6 views, component architecture, colour system, open decisions.
**Persona journeys:** [PERSONAS.md](PERSONAS.md) — what each audience needs from the dashboard.

#### Step 3.0 — Scorecard pre-flight ✅ COMPLETE

Two columns that personas need are in separate tables but not yet in `fct_kek_scorecard`. Add them in `build_fct_kek_scorecard.py` so the Dash app reads one flat table:

| Column | Source table | Needed by |
|--------|-------------|-----------|
| `dist_to_nearest_substation_km` | `fct_substation_proximity` | DFI Investor — gen-tie cost screen |
| `siting_scenario` | `fct_substation_proximity` | DFI Investor + Energy Investor — `within_boundary` vs `remote_captive` |
| `demand_mwh_2030` | `fct_kek_demand` | Energy Investor — PPA size screen |

Also fix two column name mismatches between the scorecard and PERSONAS.md references:
- `solar_competitive_gap_pct` → document as WACC=10% baseline (already correct, just needs clear label in dashboard)
- `green_share_geas` → document as 2030 figure (already correct, just needs label)

After this step: `fct_kek_scorecard` is the single source of truth for all four personas. Re-run `uv run python run_pipeline.py fct_kek_scorecard` + confirm 195 tests still pass.

#### Step 3.1 — Resolve design decisions (before writing Dash code)

Resolve the 5 open questions in [DESIGN.md §6](DESIGN.md#6-open-design-questions):
1. WACC selector: snap to 8/10/12% (recommended) vs. continuous interpolation
2. Map tile: Carto/Plotly built-in (recommended for MVP) vs. Mapbox
3. Mobile: desktop-only for MVP (recommended) vs. responsive
4. Provisional data: dagger per cell (recommended) vs. page banner
5. Export: CSV + GeoJSON (recommended) vs. CSV only

#### Step 3.2 — Build Dash app

Six views per [DESIGN.md §2](DESIGN.md#2-information-architecture), in build order:

| Order | View | Primary data | Key feature |
|-------|------|-------------|------------|
| 1 | Ranked Table | `fct_kek_scorecard` | Sort, filter, CSV export — fastest to build, validates data |
| 2 | Quadrant Chart | `fct_lcoe` + `fct_grid_cost_proxy` | WACC selector drives positions |
| 3 | Overview Map | `fct_kek_scorecard` | Click marker → load scorecard |
| 4 | KEK Scorecard | All joined tables | 4 tabs: Resource / LCOE / Demand / Pipeline |
| 5 | Flip Scenario Panel | `fct_lcoe` WACC=8% columns | Competitive-gap threshold slider |
| 6 | RUPTL Context | `fct_ruptl_pipeline` | Year-range filter, region grouping |

Build Ranked Table first — it validates the full scorecard data against all four personas before any mapping or charting work.

#### Step 3.3 — Open data release

- Versioned GitHub Releases: `kek_scorecard_v{N}.csv`, `kek_lcoe_scenarios_v{N}.csv`, `kek_map_v{N}.geojson`, `SOURCES.md`
- Deploy Dash app on Render (free tier)

---

## Data Sources (public)
- Global Solar Atlas GeoTIFFs — already in `data/` (zipped)
- ESDM Technology Catalogue — already parsed into `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv`
- KEK scraped data — `outputs/data/raw/kek_info_and_markers.csv`, `kek_polygons.geojson`
- PLN Statistik PLN 2024 — BPP regional tables
- RUPTL 2025–2034 — PDF, extraction via tabula-py
- Substation locations — `data/substation.geojson`

---

## Open Questions
1. **[RESOLVED]** PLN BPP vs. I-3/I-4 tariff — using I-4/TT from Permen ESDM 7/2024 as primary dashboard rate. OFFICIAL, nationwide uniform at ~$63.08/MWh. BPP retained as null column for future addition.
2. KEK polygon quality: accuracy of scraped `kek_polygons.geojson`? — acceptable for MVP (centroid and area used; boundary display in v2).
3. **[RESOLVED]** RUPTL extraction — manually transcribed with table attribution; pdfplumber extractor available for future updates.
4. Wind GeoTIFF: download Global Wind Atlas Indonesia and add `cf_wind` to `fct_kek_resource` — same rasterio pipeline, Phase 2.
5. **[RESOLVED]** TECH006 verification: CAPEX=0.96 MUSD/MWe, FOM=7,500 USD/MWe/yr, lifetime=27yr verified from datasheet p.66. `source_page=66`, `is_provisional=False`.
5. Hosting: Render free tier vs. Fly.io cold-start tradeoff

---

## Success Criteria
- All 24 KEKs have computed LCOE band + grid cost proxy
- WACC slider updates quadrant chart in < 1s
- Flip scenario panel correctly flags KEKs within 20% of solar-competitive threshold
- All data fields source-attributed; provisional values visually flagged
- CSV/GeoJSON exports clean enough for ADB analyst use
- GitHub Release v1.0 tagged with full dataset

---

## What Exists Today

**Model layer** — `src/model/basic_model.py` — fully implemented (100 tests passing):
- `pvout_daily_to_annual()`, `capacity_factor_from_pvout()`, `lcoe_solar()`, `lcoe_solar_with_firming()`
- `action_flags()` — returns {solar_now, grid_first, firming_needed, plan_late}
- `geas_baseline_allocation()`, `geas_policy_allocation()`, `build_scorecard()`

**Pipeline** — `run_pipeline.py` (orchestrator) + `src/pipeline/` (7 builders):
- All 7 processed tables in `outputs/data/processed/`
- `src/pipeline/assumptions.py` — centralized constants with source citations
- `src/pipeline/pdf_extract_ruptl.py` — pdfplumber-based RUPTL extractor

**Data**:
- `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv` — ESDM tech catalogue (TECH006 added)
- `data/Indonesia_GISdata_LTAym_*_GlobalSolarAtlas-v2_GEOTIFF.zip` — solar raster data
- `data/substation.geojson` — substation locations (✅ used by `fct_substation_proximity`)
- `data/industrial_data/` — industrial facility shapefile (deferred)
- `outputs/data/raw/` — scraped KEK data (markers, polygons, business sectors)
- `docs/` — RUPTL PDF, Permen ESDM 7/2024, ESDM technology cost PDF

**Utilities**: `utils/S3_loading.py`, `config/settings.py`

---

## CEO REVIEW FINDINGS (Phase 1 — /autoplan)

### Critical Issues

**CRITICAL: BPP vs. Industrial Tariff (unresolved)**
PLN BPP (cost of supply) is NOT the same as the industrial tariff paid by KEK tenants. Golongan I-3/I-4 tariff may be 30–40% lower than BPP due to subsidies. Using BPP on the quadrant y-axis may systematically overstate solar competitiveness. MUST be resolved before Phase 2. Research path: Permen ESDM No. 7 Tahun 2024 (already referenced) has the I-3/I-4 tariff schedule. Cross-reference with PLN Statistik PLN 2024 BPP tables.

### Key Architecture Decisions (auto-decided)

- **WACC computation**: Live callback (not precomputed grid). Dash callback receives WACC value → computes `lcoe_usd_mwh` on the fly for 24 KEKs in < 1ms. CAPEX/FOM/lifetime stored as app constants loaded from `dim_tech_cost`.
- **KEK list**: Include all 24 with NaN-safe handling. Missing data shows "unavailable" — never silently drops a KEK.
- **Model extraction**: `lcoe_solar()` and `capacity_factor_from_pvout()` must move from notebook to `src/model/basic_model.py` before Dash app can import them.
- **Wind CF**: Add to `fct_kek_resource` pipeline (Global Wind Atlas GeoTIFF, same rasterio pipeline). One additional column.
- **Substation proximity**: Add `dist_to_nearest_substation_km` to KEK scorecard (data in `data/substation.geojson`).
- **Fix `requirements.txt`**: Add dash, pandas, geopandas, plotly, rasterio, rioxarray, tabula-py, pytest.

### Error & Rescue Registry

```
METHOD                    | FAILURE                     | RESCUED? | USER SEES
──────────────────────────|──────────────────────────── |──────────|──────────────
GeoTIFF extraction        | File not found/corrupt      | YES      | "unavailable"
                          | CRS mismatch                | YES      | auto-reproject
                          | Point outside bounds        | YES      | "unavailable"
tabula-py RUPTL parse     | PDF layout changed          | NO ← GAP | silent NaN
                          | Table not found             | NO ← GAP | silent omit
BPP CSV parse             | Column schema changed       | NO ← GAP | silent NaN
                          | Region name mismatch        | NO ← GAP | silent NaN
lcoe_solar()              | WACC = 0 (div by zero)      | YES      | clamp to 1%
                          | CF = 0 (div by zero)        | YES      | "unavailable"
Dash WACC callback        | stale_data from dcc.Store   | NO ← GAP | broken chart
```
3 CRITICAL GAPS: tabula parse, RUPTL table missing, BPP merge mismatch → all must be caught and logged explicitly.

### Failure Modes Registry

```
CODEPATH           | FAILURE MODE       | RESCUED? | TEST? | USER SEES     | LOGGED?
───────────────────|────────────────────|──────────|──────  |───────────────|────────
Data pipeline      | GeoTIFF missing    | YES      | NO    | "unavailable" | YES
                   | BPP data missing   | NO       | NO    | Silent NaN    | NO ← GAP
                   | RUPTL parse fail   | NO       | NO    | Silent omit   | NO ← GAP
WACC callback      | Zero division      | YES      | NO    | Clamp shown   | NO
                   | Stale store data   | NO       | NO    | Wrong chart   | NO ← GAP
CSV export         | Empty data         | NO       | NO    | Broken file   | NO ← GAP
```

### NOT in Scope (CEO phase)

- Datasette REST API mirror — deferred (new infra, v2)
- SAIDI/SAIFI reliability indicators — deferred (external data source needed)
- Industrial clusters map layer — TASTE DECISION (surfaced at final gate)
- Distribution strategy / user acquisition — flagged as risk but out of code scope
- Methods note / SSRN working paper — recommended but out of code scope

### What Already Exists

- `lcoe_solar()` + `capacity_factor_from_pvout()` — in `notebooks/sample_end_to_end_policy_planning.ipynb`
- Action flags (`solar_now`, `grid_first`, `firming_needed`, `plan_late`) — in notebook
- GEAS allocation logic + policy scenario — in notebook
- ESDM tech catalogue data — `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv`
- Solar GeoTIFFs — `data/Indonesia_GISdata_LTAym_*_GlobalSolarAtlas-v2_GEOTIFF.zip`
- KEK scraped data — `outputs/data/raw/kek_info_and_markers.csv` + `kek_polygons.geojson`
- Substation data — `data/substation.geojson`
- S3 utilities — `utils/S3_loading.py`

### Dream State Delta

This plan closes ~60% of the gap to the 12-month ideal. Remaining 40%: wind CF addition, industrial tariff resolution, distribution to target users, Datasette API layer. The architecture is clean enough that all of these are additive, not structural changes.

### Open Questions (updated)

1. **[BLOCKING for Phase 2]** PLN BPP vs. I-3/I-4 industrial tariff — which to use on quadrant y-axis? Research: Permen ESDM No. 7/2024 + PLN Statistik 2024.
2. PLN BPP 2024: "Statistik PLN 2024 (Unaudited)" tables vs. Permen ESDM No.7/2024 — which to use as primary?
3. KEK polygon quality: accuracy of scraped `kek_polygons.geojson`?
4. RUPTL extraction: tabula-py vs. camelot-py vs. manual CSV — prototype first
5. Wind GeoTIFF: confirm Global Wind Atlas Indonesia download format matches solar pipeline
6. Hosting: Render free tier vs. Fly.io cold-start tradeoff
7. `kek_id` scheme: slug format recommended (e.g., `kek_kendal_java`) for stability
8. GitHub Release trigger: manual `gh release create` for v0.1 — automate later

## Decision Audit Trail

| # | Phase | Decision | Principle | Rationale | Rejected |
|---|-------|----------|-----------|-----------|----------|
| 1 | CEO | Mode = SELECTIVE EXPANSION | P1 | Greenfield feature, hold scope + surface expansions | EXPANSION (too early), HOLD (misses obvious wins) |
| 2 | CEO | Include all 25 KEKs with NaN handling | P1 | Complete > filtered; missing data is still information | Filter to data-complete KEKs only |
| 3 | CEO | WACC = live callback computation | P5 | 25 rows × 1 formula = microseconds; precomputed grid reduces user freedom | 5-value precomputed grid |
| 4 | CEO | Fix requirements.txt | P6 | Obvious gap; no working deps recorded | Defer |
| 5 | CEO | Extract model from notebook to src/model/ | P4 (DRY) | Dash app can't import from notebook; only copy is in notebook | Leave in notebook |
| 6 | CEO | Add wind CF (Global Wind Atlas) | P2 | Same rasterio pipeline; architecture identical; data available | Solar-only |
| 7 | CEO | Add substation proximity | P2 | Data in repo already; investor scorecard value | Defer to v2 |
| 8 | CEO | Defer Datasette REST API | P3 | New infra; v2 item | In scope now |
| 9 | CEO | Defer SAIDI/SAIFI | P3 | External data source; not yet available | In scope now |
| 10 | CEO | Use I-4/TT tariff as dashboard_rate | — | Permen ESDM 7/2024 is OFFICIAL; BPP adds complexity without better accuracy for investor signal | Use BPP proxy |
| 11 | Eng | Topological sort for pipeline depends_on | DRY + correctness | Prevents silent wrong-order execution; O(n) cost | Manual ordering only |
| 12 | Eng | Standardize builder pattern + TEMPLATE.py | DRY + extensibility | Adding new datasource = copy TEMPLATE, write one fn, add one line to PIPELINE | Ad-hoc per-builder structure |
| 13 | Eng | Propagate is_provisional from dim_tech_cost to fct_lcoe | Traceability | Downstream tables inherit uncertainty from upstream; shown in data_completeness | Drop flag at source |
| 14 | Eng | Full pipeline test suite (tests/test_pipeline.py) | Quality | Integration tests catch schema changes, unit conversion errors, and ordering bugs | Unit tests for model only |
| 15 | Eng | Build fct_kek_scorecard now (Phase 1) | Completeness | Dashboard needs one flat table; building it now surfaces join issues early | Defer to Phase 2 |
| 16 | Eng | Centralize constants in assumptions.py | DRY + traceability | All magic numbers in one file with source citations; no hunting across builders | Per-file constants |
| 17 | Eng | PDF extractor for RUPTL as verification utility | Traceability | Hardcoded data is manually verified; extractor provides audit trail and update path | Live extraction only |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | ✅ | BPP vs tariff issue flagged; resolved with Permen ESDM 7/2024 |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | ✅ | 5 decisions; all implemented (see Decision Audit Trail below) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | Phase 2 |

**VERDICT:** Phase 1 pipeline complete. Phase 2 (Dash app) is the next major milestone.
