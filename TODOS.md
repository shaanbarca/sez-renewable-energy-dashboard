# TODOs — Indonesia KEK Power Competitiveness Dashboard

Consolidated deferred items from [PLAN.md](PLAN.md), [PERSONAS.md](PERSONAS.md), Phase 3 autoplan review, and methodology/persona audit.
Last updated: 2026-04-07.

**Related:** [PLAN.md](PLAN.md) | [PERSONAS.md](PERSONAS.md) | [DESIGN.md](DESIGN.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

---

## High Priority (v1.1)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| H1 | **Wind CF pipeline integration** | PLAN.md decision #19 (user accepted) | P3 (Policy Maker) | Global Wind Atlas GeoTIFF → same rasterio pipeline as solar. New columns: `cf_wind`, `pvout_wind_equivalent` in `fct_kek_resource`. Fixes misleading `not_competitive` at Sulawesi KEKs (kek-palu, kek-bitung, kek-morotai). See [DESIGN.md §7](DESIGN.md#7-wind-cf-integration). |
| H2 | **BPP data sourcing** | PERSONAS.md gap priority 4 | P1 (Energy Economist) | PLN Statistik 2024 regional BPP → populate `bpp_usd_mwh` in `fct_grid_cost_proxy`. Column exists but is null. Gives economists both tariff (I-4/TT) and cost-of-supply (BPP) comparison. |
| H3 | **Land cover buildability refinement** | PLAN.md Phase 2 deferred | P2 (DFI Investor), P4 (IPP) | `pvout_best_50km` → `pvout_buildable_best_50km` uses upper-bound when `data/buildability/` layers incomplete. Refine with full 4-layer cascade when data populated. Currently 2/4 layers automated (DEM + ESA WorldCover); Kawasan Hutan and peatland shapefiles require manual download from KLHK geoportal. |
| H4 | **Configurable assumptions — Phase B (infrastructure costs)** | DESIGN.md §3, decision #34 | P2, P4 | Add collapsible "Advanced Assumptions" panel: FOM ($3–15), gen-tie ($2–12/kW-km), substation ($80–250/kW), transmission lease ($3–20/MWh), firming adder ($5–20/MWh), IDR/USD rate. Extends Phase A live computation in `src/dash/logic.py`. |
| H5 | **Configurable assumptions — Phase C (flag thresholds)** | DESIGN.md §3, decision #34 | P3 | Add collapsible "Flag Thresholds" panel: PVOUT threshold, plan-late %, GEAS %, resilience gap %, min viable MWp, reliability threshold. All wire to `compute_scorecard_live()`. |

---

## Medium Priority (v1.2)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| M1 | **Grid emission factor update** | PERSONAS.md gap priority 5 | P1, P3 | KESDM 2019 Tier 2 OM → 2023 KESDM or IEA SEA 2024 data. Affects `carbon_breakeven_usd_tco2` accuracy. See [METHODOLOGY.md §4](METHODOLOGY.md) for current emission factor methodology. |
| M2 | **Road proximity layer (Layer 3a)** | PERSONAS.md gap priority 8 | P2, P4 | OSM PBF processing → `dist_to_nearest_road_km`. Construction access cost proxy for remote captive sites. |
| M3 | **CAPEX market comparables** | PERSONAS.md P1 data gaps | P1 | 2023–2024 Indonesia solar EPC tender data. ESDM catalogue value ($960/kW) may be ±15–20% from market reality. |
| M4 | **KEK operational status enrichment** | PERSONAS.md gap priority 7 | P4 | Distinguish operating (tenants present) vs. greenfield KEKs. Requires BKPM/KEK management data sourcing. |
| M5 | **Custom CAPEX input for IPP** | PERSONAS.md P4 audit finding | P4 | IPP developers know their EPC costs better than the ESDM catalogue. Phase A provides CAPEX slider ($600–1,500); v1.2 adds free-text input for exact $/kW value. Workaround: export CSV with CF values and recompute in own model. |
| M6 | **Configurable assumptions — Phase D (UX polish)** | DESIGN.md §3, decision #34 | All | URL state persistence (`?capex=840&wacc=8`), "scenario changed" badge, export-with-assumptions metadata, reset-to-defaults buttons per tier. |
| M7 | **Scenario save/compare** | Methodology audit | All | Save up to 3 named assumption sets (e.g., "Optimistic", "Base", "Pessimistic") and compare side-by-side. Requires `dcc.Store` + local storage. |

---

## Low Priority (v2.0)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| L1 | **Datasette REST API** | PLAN.md CEO review | All | Mirror processed CSVs via REST API for programmatic access. New infrastructure dependency. |
| L2 | **SAIDI/SAIFI reliability indicators** | PLAN.md CEO review | P3 | Replace hardcoded `reliability_req` with PLN SAIDI/SAIFI by grid system. Strengthens `invest_resilience` flag credibility. |
| L3 | **Flood hazard layer (Layer 2d)** | PERSONAS.md gap priority 9 | P2 | BNPB portal inaccessible. Low incremental value over existing slope exclusion layer. Blocked on data access. |
| L4 | **Excel/PDF export pipeline** | Autoplan CEO subagent | All | Beyond CSV + GeoJSON: formatted Excel workbook with embedded charts and PDF scorecard per KEK. Distribution format for analysts who won't bookmark a Dash URL. |
| L5 | **Multilingual (EN/ID)** | — | P3 | Indonesian language option for BKPM/KESDM officials. Adds i18n complexity. |
| L6 | **Mapbox upgrade from Carto** | DESIGN.md §6 Q2 | All | Prettier tiles. Requires `MAPBOX_TOKEN` in `.env`. Deferred from MVP. |
| L7 | **Mobile responsive layout** | DESIGN.md §6 Q3 | All | Primary users are analysts with laptops. Mobile adds CSS complexity. Deferred from MVP. |
| L8 | **KEK Management persona (P5)** | Methodology/persona audit | — | Zone administrators (BKPM-appointed) who use the tool to attract tenants. Distinct journey from P1–P4. Good v2.0 addition. |
| L9 | **Carbon price trajectory modelling** | PERSONAS.md P3 data gaps | P3 | Link `carbon_breakeven_usd_tco2` to Indonesia's ETS trajectory (Article 6 commitments, IDR carbon market). Policy makers need: "at projected carbon price path, when does solar win?" |

---

## Completed (this session)

| # | Item | Date | Notes |
|---|------|------|-------|
| ✅ | **Configurable assumptions — Phase A (core LCOE controls)** | 2026-04-07 | `src/dash/logic.py` created: `UserAssumptions`, `UserThresholds`, `compute_lcoe_live()`, `compute_scorecard_live()`. 22 tests passing. CAPEX slider + Lifetime slider ready for Dash wiring. |
| ✅ | **Methodology expert review** | 2026-04-07 | 10 fixes applied to METHODOLOGY.md: stale WACC range, buildability caveats, slope threshold, degradation note, GSA temperature de-rating, carbon lifecycle emissions, FX sensitivity. |
| ✅ | **Personas expert review** | 2026-04-07 | P3 solar-only caveat added, P4 custom CAPEX note added. `solar_now_at_wacc8` column verified in scorecard CSV. |
| ✅ | **DESIGN.md configurable assumptions spec** | 2026-04-07 | Decision #34: 3-tier slider controls, hybrid precomputed/live architecture, callback diagram, component choices for 16 controls. |

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
