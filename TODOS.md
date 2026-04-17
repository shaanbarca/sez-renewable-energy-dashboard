# TODOs — Indonesia KEK Power Competitiveness Dashboard

Consolidated deferred items from [PLAN.md](PLAN.md), [PERSONAS.md](PERSONAS.md), [gap analysis](docs/gap_analysis_existing_vs_conversation_spec.md), [JETP captive power gap analysis](docs/gap_analysis_jetp_captive_power.md), and methodology/persona audit.
Last updated: 2026-04-17 (`logic.py` → `logic/` package split complete; docs refreshed).

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
| Q5 | **ESDM Technology Catalogue 2024 vs. 2023 parameter check** | JETP gap analysis P0 #5 | `METHODOLOGY_CONSOLIDATED.md`, `src/assumptions.py` | JETP report references 2024 edition. Compare CAPEX/performance parameters — if materially different, update `VERIFIED_TECH006_DATA`. |

---

## High Priority (JETP Captive Power Integration)

From [JETP captive power gap analysis](docs/gap_analysis_jetp_captive_power.md). Data sources: [CGSP Nickel Tracker](https://nickel.chinaglobalsouth.com/) (CC), [GEM Coal Tracker](https://globalenergymonitor.org/projects/global-coal-plant-tracker/) (CC BY 4.0). See gap analysis §6 for coverage details.

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| ~~H6~~ | ~~**Overlay CGSP nickel smelters on KEK map**~~ | JETP P0 #1 | P2, P4 | ✅ Done (2026-04-12) — 107 nickel smelters via CGSP Nickel Tracker. `VectorOverlay.tsx` source layer + `map_layers.py:load_nickel_smelters()`. Popup with capacity, ownership, process type. Orange circle+factory icon. |
| ~~H7~~ | ~~**Overlay GEM captive coal on KEK map**~~ | JETP P0 #2 | P2, P3, P4 | ✅ Done (2026-04-12) — 26 captive coal plants via GEM GCPT. `VectorOverlay.tsx` source layer + `map_layers.py:load_captive_coal()`. Popup with capacity, status, parent. Dark red circle+smokestack icon. |
| ~~H8~~ | ~~**Add Perpres 112/2022 compliance flag**~~ | JETP P0 #3 | P2, P3 | ✅ Done (2026-04-12) — `has_captive_coal` boolean + `perpres_112_status` string on scorecard. Status-based proxy (GEM KAPSARC mirror lacks commissioning_year). Shows in ScoreDrawer Captive Power card. |
| ~~H9~~ | ~~**Add captive coal summary per KEK**~~ | JETP P0 #4 | All | ✅ Done (2026-04-12) — 7 new scorecard fields: `captive_coal_count`, `captive_coal_mw`, `captive_coal_plants`, `nickel_smelter_count`, `nickel_projects`, `dominant_process_type`, `has_chinese_ownership`. Pipeline CSVs → data_loader merge → scorecard → ScoreDrawer card. |
| ~~H10~~ | ~~**Interactive scale selector → scorecard LCOE recalculation**~~ | JETP P1 #6 | P4 | ✅ Done (2026-04-12) — `target_capacity_mwp` parameter recalculates LCOE at user-chosen capacity. Gen-tie cost and substation capacity respond to selected scale. `effective_capacity_mwp` flows through scorecard. |

---

## Critical Priority — Physics Model Gaps

From [physics_vs_tool_technical_gaps.md](docs/physics_vs_tool_technical_gaps.md). Cross-referenced against MacKay's *Sustainable Energy Without the Hot Air* framework. These are gaps where the model's simplifications meaningfully misrepresent physical reality. Verified against codebase 2026-04-13.

| # | Item | Gap | LCOE / Metric Impact | Files | Status |
|---|------|-----|---------------------|-------|--------|
| ~~P1~~ | ~~**BESS sizing proportional to bridge hours**~~ | Gap 2: BESS fixed at 2h (4h for RKEF via M19). Physics requires ~14h for 24/7 industrial loads. | LCOE now reflects **14h bridge-hours** for high-reliability loads (≥75% reliability_req). | `src/assumptions.py` (`BESS_BRIDGE_HOURS_ENABLED`, `SOLAR_PRODUCTION_HOURS`), `src/model/basic_model.py` (`bess_bridge_hours()`), `src/dash/logic.py` | ✅ Done (2026-04-13). `bess_bridge_hours() = 24 - SOLAR_PRODUCTION_HOURS = 14h`. High-reliability loads auto-sized; RKEF fallback preserved for non-bridge mode. |
| ~~P2~~ | ~~**Round-trip efficiency in BESS model**~~ | Gap 4: `bess_storage_adder()` now accounts for 87% round-trip efficiency. | BESS CAPEX oversized by 1/RTE, denominator reduced by nighttime efficiency loss. | `src/model/basic_model.py` (`bess_storage_adder`), `src/assumptions.py` (`BESS_ROUND_TRIP_EFFICIENCY = 0.87`) | ✅ Done (2026-04-13). Added `BESS_ROUND_TRIP_EFFICIENCY`. `effective_sizing = sizing / RTE`. `effective_CF = CF × (1 - nighttime_frac × (1 - RTE))`. |
| ~~P3~~ | ~~**Firm solar supply coverage (temporal mismatch)**~~ | Gap 1: New `firm_solar_coverage_pct` metric splits daytime-direct vs nighttime-requires-storage. | Dashboard now shows both annual and firm (daytime) coverage, plus storage gap %. | `src/model/basic_model.py` (`firm_solar_metrics()`), `src/dash/logic.py`, `src/pipeline/build_fct_kek_scorecard.py`, `frontend/src/components/panels/ScoreDrawer.tsx` | ✅ Done (2026-04-13). 4 new scorecard fields: `firm_solar_coverage_pct`, `nighttime_demand_mwh`, `storage_required_mwh`, `storage_gap_pct`. Displayed in ScoreDrawer Overview tab. |
| ~~P4~~ | ~~**Energy balance visualization**~~ | Gap 7: Supply and demand now shown side-by-side in Overview tab via MacKay-style balance chart. | Demand split (daytime/nighttime) vs supply (solar/gap), with dynamic summary line. | `frontend/src/components/charts/EnergyBalanceChart.tsx`, `frontend/src/components/panels/ScoreDrawer.tsx` | ✅ Done (2026-04-13). `EnergyBalanceChart` in Overview tab between Identity and At a Glance. Two stacked bars (demand day/night, supply solar/gap), legend, dynamic summary. Also: ScoreDrawer reorg (Flags→Action, BPP before Tariff, RUPTL moved to Action tab, section "so what" subtitles). |
| ~~P5~~ | ~~**Panel degradation in LCOE denominator**~~ | Gap 3: `lcoe_solar()` now includes midpoint degradation factor. 0.5%/yr over 27yr = factor 0.9325. | LCOE corrected upward by ~7.2%. Borderline KEKs now properly flagged. | `src/model/basic_model.py` (`lcoe_solar`), `src/assumptions.py` (`SOLAR_DEGRADATION_ANNUAL_PCT`) | ✅ Done (2026-04-13). Midpoint linear approximation: `degradation_factor = 1 - (rate × lifetime / 2)`. New param `degradation_annual_pct` with default 0.5%. 2 new tests. Source: NREL Jordan & Kurtz 2013. |
| ~~P6~~ | ~~**Power factor in capacity assessment**~~ | Gap 6: `capacity_assessment()` and `substation_upgrade_cost_per_kw()` now convert MVA to MW via PF 0.85. | Capacity assessment corrected by 15%. Some borderline substations shift yellow→red. | `src/model/basic_model.py` (`capacity_assessment`, `substation_upgrade_cost_per_kw`), `src/assumptions.py` (`SUBSTATION_POWER_FACTOR`) | ✅ Done (2026-04-13). New param `power_factor` with default 0.85. Returned `available_capacity_mva` stays in MVA for display. 2 new tests. Source: PLN grid code PF 0.85 minimum. |
| — | ~~Power density ha/MW consistency~~ | Gap 5: 1.5 ha/MWp used consistently across `buildability_filters.py:41`, `build_fct_kek_resource.py:28`, and `assumptions.py:354`. | No gap. | — | ✅ Verified consistent (2026-04-13). |
| — | ~~Transmission loss~~ | Gap 8: Not modeled. At gen-tie distances (<40 km), losses are <1% (~$0.30/MWh). | Negligible. | — | ✅ Correctly omitted. Add one-line methodology note. |

**All physics model gaps resolved.** P1-P3 (BESS/storage realism), P4 (energy balance visualization), P5 (panel degradation), P6 (power factor) — all done.

---

## Medium Priority (v1.2)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| M1 | **Grid emission factor update** | PERSONAS.md gap 5 | P1, P3 | KESDM 2019 Tier 2 OM → 2023 KESDM or IEA SEA 2024 data. Affects `carbon_breakeven_usd_tco2` accuracy (7 years stale). |
| ~~M2~~ | ~~**Road proximity layer (Layer 3a)**~~ | ~~PERSONAS.md gap 8~~ | ~~P2, P4~~ | ✅ Done. `road_distance_km.tif` from Geofabrik PBF, 10km hard exclusion for both solar and wind. |
| M3 | **CAPEX market comparables** | PERSONAS.md P1 gaps | P1 | 2023-2024 Indonesia solar EPC tender data. ESDM catalogue ($960/kW) may be +/-15-20% from market. |
| M4 | **KEK operational status enrichment** | PERSONAS.md gap 7 | P4 | Distinguish operating (tenants present) vs. greenfield. Requires BKPM/KEK management data. |
| ~~M5~~ | ~~**Custom CAPEX input for IPP**~~ | PERSONAS.md P4 audit | P4 | ✅ Done (2026-04-11) — `CapexInput.tsx` free-text input with slider, validates range, tab/enter commit. |
| ~~M6~~ | ~~**Configurable assumptions — Phase D (UX polish)**~~ | DESIGN.md §3 | All | ✅ Done (2026-04-11) — URL state persistence (`urlState.ts`, `useUrlSync.ts`), "Modified" badge, reset-to-defaults. |
| ~~M7~~ | ~~**Scenario save/compare**~~ | Methodology audit | All | ✅ Done (2026-04-12) — Save up to 3 named scenarios to localStorage. `ScenarioManager.tsx` in AssumptionsPanel with save/load/delete. Comparison view deferred to v2. |
| M8 | **Floating solar modelling** | User obs (2026-04-08) | P2, P4 | Water bodies excluded from buildable area. Floating PV on reservoirs/lagoons could unlock capacity for land-constrained KEKs. CAPEX ~20-30% higher ($1,100-1,400/kW). Requires new siting scenario. |
| M9 | **Raster overlay bounds expansion** | UI bug (2026-04-09) | All | Raster overlays clip when map is pitched (3D terrain). Backend `map_layers.py` bounding box needs padding (+/-5 deg). Workaround: auto-pitch only at zoom > 7. |
| M10 | **Substation-name-to-line-name matching** | V3.1 deferred | All | Grid line names encode endpoints but naming is inconsistent. Geometric check is more reliable. Nice-to-have refinement. |
| M11 | **Night-time light proxy for utilization** | V3.1 deferred | P2 | VIIRS/DMSP satellite data as proxy for substation load. Improves `capacity_assessment` vs. fixed 65% assumption. |
| ~~M12~~ | ~~**Substation upgrade cost in LCOE**~~ | Gap analysis P1, V3.1 deferred | P2, P3 | ✅ Done (2026-04-12) — `substation_upgrade_cost_per_kw` added to precomputed LCOE pipeline (`build_fct_lcoe.py`). Deficit fraction × $80/kW folded into grid-connected effective CAPEX. Surfaced in scorecard + `grid_investment_needed_usd`. 4 new tests. |
| M13 | **Sub-pixel buildable fraction from ESA WorldCover** | Buildability review (2026-04-10) | P2 | Current `Resampling.mode` at 10m→1km loses sub-pixel detail. Replace with binary-threshold + average resampling at 50%. |
| ~~M14~~ | ~~**Buildable land polygons (in-boundary + remote)**~~ | Gap analysis P1 | P2, P4 | ✅ **Done (2026-04-12):** Remote/50km buildable polygons live as "Solar Buildable Areas" layer with clickable popups. Within-boundary polygons clipped to KEK boundary via `/api/kek/{id}/buildable` endpoint (`get_within_boundary_buildable` in `map_layers.py`). Displayed as green overlay on KEK zoom. Area capped at KEK polygon area to prevent raster pixel inflation. |
| ~~M15~~ | ~~**Multi-substation comparison**~~ | Gap analysis P2 | P4 | ✅ **Done (2026-04-12):** `/api/kek/{id}/substations` now computes per-substation costs (connection, upgrade, transmission, total grid CAPEX, LCOE estimate) for top 3 by distance. `SubstationComparison.tsx` card in ScoreDrawer Pipeline tab shows side-by-side comparison with capacity traffic lights. Map markers rank-coded: gold (1st), silver (2nd), cyan (3rd). 4 new API tests. |
| ~~M16~~ | ~~**Capacity slider with LCOE curve**~~ | Gap analysis P1 | P4 | ✅ Done (2026-04-12) — `LcoeCurveChart.tsx` renders LCOE vs. project scale (5 MW → max capacity). Recharts AreaChart with grid cost reference line and max capacity marker. Client-side CRF formula. Theme-aware. |

### JETP Remaining P1 Items (from [gap analysis](docs/gap_analysis_jetp_captive_power.md))

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| M17 | **30 km "technically possible" grid integration layer** | JETP P1 #7 | P3 | Secondary, more permissive threshold (30km to substation) for policymaker view. JETP uses 30km for grid integration screening. Aligns with Norton Rose Fulbright 20-40km Indonesian IPP corridor. Keep existing 5km/15km thresholds for investor view. **Expansion note:** New standalone plants outside KEK 5km/15km thresholds benefit from the 30km view. Scope expands to cover non-KEK sites. |
| M18 | **Grant-funded transmission scenario toggle** | JETP P1 #8 | P2, P4 | Toggle that sets connection cost contribution to zero — models DFI grant scenario (e.g. UK MENTARI programme). Shows: "if a DFI covers the gen-tie cost, here's the LCOE impact." |
| ~~M19~~ | ~~**BESS high-reliability multiplier for RKEF KEKs**~~ | JETP P1 #9 | P4 | ✅ Done (2026-04-12) — Auto-doubles BESS sizing (2h → 4h) when `dominant_process_type == "RKEF"`. Doubles battery CAPEX component ($500→$1,000/kW-solar). Visible in `invest_battery` flag description and `lcoe_with_battery_usd_mwh`. |
| M20 | **CIT waiver impact on LCOE** | JETP P1 #11 | P2, P4 | Model post-tax LCOE with/without corporate income tax waiver (PMK 130/2020: 100% CIT waiver for 10 years if investment > IDR 100B). Checkbox toggle in assumptions. |
| M21 | **Hydropower potential layer** | JETP P1 #12 | P2, P3 | MEMR One Map run-of-river data, 30km radius from KEKs. JETP found 3.2 GW run-of-river potential near captive sites. For Sulawesi KEKs (Morowali, Konawe), hydro may beat solar. Needs new LCOE model for hydro. |
| M22 | **Priority 2-3 industrial sites** | Industrial Parks Expansion | All | Petrochemical (Chandra Asri, TPPI), refining. SiteTypeConfig registry makes this a data-only addition (1 dict entry per type). Non-KEK nickel expansion now handled automatically via CGSP IIA tracker (2026-04-17). |
| M23 | **Col class for column name constants** | Industrial Parks Expansion | All | Replace string literals with `Col.SITE_ID` etc. Prevents rename bugs (silent NaN joins from Pandas). Incremental adoption, one pipeline file at a time. See `docs/PLAN_INDUSTRIAL_PARKS_EXPANSION.md` Design Decision 4. |
| M24 | **Ruff cleanup: PLC0415 / PLR2004 / PLR0913 in src/** | Ruff rule expansion (2026-04-17) | All | After adding PLC0415/PLR2004/PLR0913 to `pyproject.toml`: 52 PLC0415 violations remain in `src/` after exempting `tests/*`. Plan: hoist ~22 cheap/stale imports (`math`, `json`, `ast`, `shutil`, already-imported `pandas`/`numpy`) to top-level; `# noqa: PLC0415  # lazy: {reason}` for ~25 legit heavy imports (`rasterio`, `geopandas`, `matplotlib`, `plotly.graph_objects`); `# noqa: PLC0415  # circular` for ~5 `from src.api.main import ...` cases inside route handlers. Add `src/dash/app.py` to per-file-ignores (legacy 1,763-line file, dead code per Expansion R4). Also audit 150 PLR2004 + 13 PLR0913 in src/. Tests already exempted. |
| M25 | **Aluminium tracker (GEM GAST) integration** | Industrial Parks Expansion (2026-04-17) | P1, P2 | Only 2 residual manual rows remain for aluminium (Inalum Asahan, Freeport Smelter Gresik). Plan: download [GEM Global Aluminum Smelter Tracker](https://globalenergymonitor.org/projects/global-aluminum-smelter-tracker/) to `data/captive_power/gem_aluminum_plants.csv`, add `_build_aluminium_rows()` to `build_industrial_sites.py` filtered by `country_name == "Indonesia"` and `status == "Active"`, drop the manual rows. Reproducibility goal: all site selection driven by trackers, not hand-curated CSVs. |
| M26 | **Fertilizer tracker (or equivalent) integration** | Industrial Parks Expansion (2026-04-17) | P1, P2 | 3 residual manual rows remain for fertilizer (Pupuk Kaltim Bontang, Pupuk Sriwidjaja Palembang, Petrokimia Gresik). No free global fertilizer tracker equivalent to GEM exists (IFA data is paywalled). Options: (1) scrape Pupuk Indonesia holding-company reports for canonical plant list, (2) use MEMR one-map ammonia/urea permits, (3) accept residual CSV with tight provenance. Status quo (option 3) is acceptable until a public tracker appears. |
| M27 | **Nickel IIA capacity aggregation: widen or geocode-fix** | Industrial Parks Expansion (2026-04-17) | P2 | Two CGSP IIA rows (IKIP Konawe, Stardust Estate Investment) yield NaN `capacity_annual_tonnes` because their nearest `Processing` child is 37km and 21km respectively, outside the 20km `NICKEL_IIA_CHILD_RADIUS_KM` aggregation window. Options: (1) widen the radius to 40km (risks false-positive attribution to adjacent parks), (2) manually verify CGSP geocodes for these two rows and file an upstream correction, (3) add a manual override map in `build_industrial_sites.py`. Current behaviour: cluster retained with NaN capacity so sector-intensity demand = 0 for these sites. |

---

## Low Priority (v2.0)

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| L1 | **Datasette REST API** | PLAN.md CEO review | All | Mirror processed CSVs via REST API for programmatic access. |
| L2 | **SAIDI/SAIFI reliability indicators** | PLAN.md CEO review | P3 | Replace hardcoded `reliability_req` with PLN SAIDI/SAIFI by grid system. Strengthens `invest_resilience` flag. **Expansion note:** `SECTOR_RELIABILITY_REQUIREMENT` now provides sector-based defaults for non-KEK sites (steel=0.90, aluminium=0.95). SAIDI/SAIFI data would replace both KEK type-based and sector-based proxies. |
| L3 | **Flood hazard layer (Layer 2d)** | PERSONAS.md gap 9 | P2 | BNPB portal inaccessible. Low incremental value over slope layer. Blocked on data access. |
| L4 | **Excel/PDF export pipeline** | Autoplan CEO subagent | All | Formatted Excel workbook with charts + PDF scorecard per KEK. |
| L5 | **Multilingual (EN/ID)** | — | P3 | Indonesian language option for BKPM/KESDM officials. |
| ~~L6~~ | ~~**Mapbox basemap upgrade from Carto**~~ | DESIGN.md §6 Q2 | All | ❌ Won't do — MapLibre can't resolve `mapbox://` protocol URLs in style JSON. `transformRequest` workaround attempted but unreliable. Carto Dark Matter is the dark basemap. |
| L7 | **Mobile responsive layout** | DESIGN.md §6 Q3 | All | Primary users are analysts with laptops. |
| L8 | **KEK Management persona (P6)** | Methodology/persona audit | — | Zone administrators (BKPM-appointed) who use the tool to attract tenants. |
| L9 | **Carbon price trajectory modelling** | PERSONAS.md P3 gaps | P3 | Link `carbon_breakeven_usd_tco2` to Indonesia ETS trajectory. |
| L10 | **Spatial story / SEZ-anchored map view** | Gap analysis P2 | P3 | Partially done (2026-04-12): buildable polygons radiate outward on KEK click (green in-boundary → teal remote, 4.5s pulse animation). Auto-enables Solar Buildable Areas layer. Color-coding by gap type still deferred. |

### JETP Deeper Integration

| # | Item | Source | Personas | Notes |
|---|------|--------|----------|-------|
| L11 | **Cross-reference ESDM Minerba Geoportal** | JETP P2 #12 | All | Government-authoritative validation of CGSP/GEM data. Mining concession boundaries, processing facility permits, regulatory status. May require manual extraction. |
| L12 | **Geothermal potential layer** | JETP P2 #13 | P2, P3 | MEMR One Map, 30km radius. Fills gap for Sulawesi and North Sumatra KEKs. Needs new LCOE model for geothermal. |
| L13 | **Biomass potential layer** | JETP P2 #14 | P3 | MEMR One Map, province-level. Niche but relevant for pulp & paper KEKs. Simpler than point-based layers. |
| L14 | **Import JETP demand projections** | JETP P2 #15 | All | Replaces area x intensity proxy with activity-driven demand for overlapping KEKs. Requires JETP Secretariat data sharing or database access. **Expansion note:** sector-intensity demand estimation now provides production-based demand for non-KEK sites, partially addressing this gap. JETP projections would further improve accuracy for overlapping KEK/industrial sites. |
| L15 | **REC pathway indicator** | JETP P2 #16 | P5 | Model REC cost vs. solar LCOE as alternative decarbonization path. Tenant can achieve ESG compliance via certificate purchase without physical solar. Distinct from GEAS green share. |
| L16 | **Industrial clustering benefit on LCOE** | JETP P2 #17 | P2, P4 | Model how aggregated demand within KEK (multiple tenants) affects solar+BESS sizing and LCOE. KEKs are clusters by design but app doesn't model the scaling benefit. High effort. **Expansion note:** Cluster `site_type` now models aggregated demand. BESS sizing reflects cluster-level demand. Full shared-infrastructure LCOE discount still deferred. |
| L17 | **Social/environmental impact flags from CGSP** | JETP P2 #18 | P2, P5 | CGSP includes social and ecological impact flags for nickel projects. ESG-relevant for Tenant and DFI personas. Low effort once CGSP data (H6) is integrated. |
| L18 | **Process emissions (Scope 1) for CBAM** | Industrial Parks Expansion | P1, P2, P3 | Cement calcination, aluminum electrolysis, steel reduction. Current CBAM model covers Scope 2 (electricity) only. Requires sector-specific process emission models. See `docs/PLAN_INDUSTRIAL_PARKS_EXPANSION.md` Phase 5. |
| L19 | **PyPSA grid optimization integration** | Industrial Parks Expansion | P2, P3 | Export dim_sites + fact tables as `pypsa.Network` for capacity expansion planning. Star schema join path `site -> substation -> grid_region -> RUPTL` is the natural adapter boundary. Public data first, private data later. |
| L20 | **PLN Supergrid corridor visualization** | Industrial Parks Expansion | P2, P3 | RUPTL Super Grid corridor data -> map overlay + `corridor_arrival_year` column per site. `pln_grid_lines.geojson` (1,595 lines) already exists. Requires RUPTL data parsing for corridor schedule. |

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
| ✅ | Persona walkthrough tour | 2026-04-09 | 5 personas (8-10 steps each), spotlight overlay, Guide button. V3.3: energy mode, wind/hybrid, captive power, firm solar coverage, BESS bridge-hours, grid investment. |
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
| ✅ | M12: Substation upgrade cost in LCOE | 2026-04-12 | `substation_upgrade_cost_per_kw` added to precomputed LCOE pipeline. Deficit fraction × $80/kW in grid-connected effective CAPEX. Surfaced in scorecard + `grid_investment_needed_usd`. |
| ✅ | M16: LCOE vs capacity curve chart | 2026-04-12 | `LcoeCurveChart.tsx` — Recharts AreaChart showing LCOE vs project scale (5 MW → max). Grid cost reference line, max capacity marker, client-side CRF formula. |
| ✅ | M7: Scenario save/compare | 2026-04-12 | `ScenarioManager.tsx` — save up to 3 named scenarios to localStorage. Zustand store actions for save/load/delete. Inline UI in AssumptionsPanel. |
| ✅ | M15: Multi-substation comparison | 2026-04-12 | `/api/kek/{id}/substations` extended with per-substation cost breakdown (top 3). `SubstationComparison.tsx` side-by-side table in ScoreDrawer Pipeline tab. Rank-coded map markers (gold/silver/cyan). 4 API tests. |
| ✅ | H6: CGSP nickel smelter overlay | 2026-04-12 | 107 smelters from CGSP Nickel Tracker. VectorOverlay source layer, orange circle+factory icon, popup with capacity/ownership/process. LayerControl toggle. |
| ✅ | H7: GEM captive coal overlay | 2026-04-12 | 26 captive coal plants from GEM GCPT. VectorOverlay source layer, dark red circle+smokestack icon, popup with capacity/status/parent. LayerControl toggle. |
| ✅ | H8: Perpres 112/2022 flag | 2026-04-12 | `has_captive_coal` + `perpres_112_status` on scorecard. Status-based proxy (commissioning_year unavailable). ScoreDrawer Captive Power card. |
| ✅ | H9: Captive power scorecard enrichment | 2026-04-12 | 7 new fields from CGSP/GEM summaries. Pipeline CSVs → data_loader merge → scorecard pass-through → ScoreDrawer card. |
| ✅ | H10: Interactive scale selector | 2026-04-12 | `target_capacity_mwp` recalculates LCOE at user-chosen capacity. `effective_capacity_mwp` flows through scorecard. |
| ✅ | Icon fix: Nickel/coal map icons | 2026-04-12 | Replaced custom canvas drawing with `createIconImage()` pattern (colored circle + white SVG path). Consistent with InfraMarkers. |
| ✅ | M19: BESS RKEF high-reliability multiplier | 2026-04-12 | Auto-doubles BESS sizing (2h→4h) for RKEF nickel process KEKs. Doubles battery CAPEX component. Visible in invest_battery flag + LCOE. |
| ✅ | Solar replacement potential | 2026-04-12 | `solar_replacement_pct` in Captive Power card. Calculates what % of captive coal generation is replaceable by buildable solar (40% coal CF assumption). |
| ✅ | Enriched nickel popups | 2026-04-12 | CGSP fields now in map popup: capacity (tons), investment cost (USD), shareholder, ESG ecological/social flags. Both raw and processed data paths. |
| ✅ | GEM steel plant overlay + pipeline | 2026-04-14 | 7 steel plants from GEM Global Iron and Steel Plant Tracker. `build_fct_captive_steel.py` spatial join (50km). Map layer: indigo icon, popup with capacity/technology/ownership. 2 KEKs matched. |
| ✅ | GEM cement plant overlay + pipeline | 2026-04-14 | 32 cement plants from GEM Global Cement Plant Tracker. `build_fct_captive_cement.py` spatial join (50km). Map layer: blue-grey icon, popup with capacity/type/ownership. 5 KEKs matched. |
| ✅ | CBAM 3-signal detection expansion | 2026-04-14 | CBAM detection expanded from nickel-only to 3 signals: (1) nickel process types, (2) plant-level steel/cement counts, (3) KEK business sectors. 8→12 KEKs exposed. Products: iron_steel, aluminium, fertilizer, cement. |
| ✅ | ScoreDrawer Industry tab redesign | 2026-04-14 | "Demand" tab renamed "Industry". Sections reordered: Demand → Industry/CBAM → Supply → Temporal. Table condensed from 4 captive columns to 2 (Industry badges + CBAM '30 cost). |
| ✅ | Steel site automation via GEM tracker | 2026-04-17 | `build_industrial_sites.py:_build_steel_rows()` now reads the 7 active Indonesian steel plants straight from `data/captive_power/gem_steel_plants.csv`. Removed 7 hand-curated rows from `priority1_sites.csv`. Automated filter: `status == "Active"`. Provenance (`source_name`/`source_url`/`retrieved_date`) stamped per row. |
| ✅ | Nickel IIA cluster automation via CGSP | 2026-04-17 | `build_industrial_sites.py:_build_nickel_rows()` unions CGSP Nickel Tracker: `parent_project_type == "Integrated Industrial Area"` → 11 park rows, minus 5km KEK-overlap exclusion (Palu SEZ) → 10 cluster rows. Each cluster aggregates capacity from `Processing` children within 20km (IMIP=5.4M t/yr, etc.). IKIP/SEI yield no capacity because their nearest Processing row is >20km; cluster retained with NaN capacity (documented gap). Removed 3 hand-curated nickel rows. |
| ✅ | Residual CSV provenance enforcement | 2026-04-17 | `priority1_sites.csv` reduced to 5 residual rows (2 aluminium + 3 fertilizer, the sectors without a tracker step). All rows carry `source_name`/`source_url`/`retrieved_date`. Loader raises on any row missing `source_url`. Total pipeline: 79 sites (25 KEK + 44 standalone + 10 cluster). |
| ✅ | `src/dash/logic.py` → `logic/` package split | 2026-04-17 | Refactor-only (no behavior change). 1,437 LOC monolith split into 7 domain modules: `assumptions.py`, `lcoe.py`, `cbam.py`, `grid.py`, `technology.py`, `scorecard.py`, `__init__.py` (re-export shim). Public API frozen so external callers (`src/api/routes/scorecard.py`, `tests/test_dash_logic.py`) stay unchanged. Verified via bit-identical golden-master pickle (`tests/test_scorecard_golden.py`). Added 30 module-boundary tests across 5 new test files + 1 parity test → 532 total (up from 498). |

---

## Dashboard Caveats (document only, no code fix)

These are data limitations. The dashboard should display clear labels/tooltips for each.

| # | Caveat | Display treatment | Source |
|---|--------|------------------|--------|
| C1 | `demand_mwh_2030` is area x intensity proxy (KEKs) / production-based (industrial sites) | Tooltip: "KEK demand estimated from area x industrial intensity. Industrial sites use production-based calculation (capacity x sector electricity intensity). Not suitable for PPA sizing; field surveys required." | PERSONAS.md P4 data gaps, Industrial Parks Expansion |
| C2 | GEAS pro-rata allocation is indicative | Label: "Indicative GEAS allocation, not contractual. Actual allocation depends on PLN tender design." | PERSONAS.md P3 data gaps |
| C3 | Substation capacity nulls (6/25 KEKs) | Display "—" with tooltip: "Capacity not recorded by PLN" | PERSONAS.md P2 data gaps |
| C4 | `reliability_req` is type-based proxy (KEKs) / sector-based (industrial sites) | Label on `invest_resilience` flag: "KEKs: based on KEK type (manufacturing=0.8, tourism=0.4). Industrial sites: based on sector (steel=0.90, aluminium=0.95). Pending PLN SAIDI/SAIFI data." | PERSONAS.md P3 data gaps, Industrial Parks Expansion |
| ~~C5~~ | ~~Panel degradation not modeled~~ | ✅ Resolved (V3.4, P5): 0.5%/yr midpoint degradation now included in `lcoe_solar()`. LCOE corrected upward ~7%. | Methodology audit F7 |
| C6 | Carbon breakeven excludes solar lifecycle emissions | Tooltip on carbon breakeven: "Assumes zero solar lifecycle emissions. Actual ~40 gCO2/MWh (IPCC AR6). Breakeven ~5-8% optimistic." | Methodology audit F9 |
| ~~C7~~ | ~~IDR/USD rate hardcoded~~ | ✅ Resolved: IDR/USD rate is now a Tier 2 slider (range 14,000-18,000, step 100). User-adjustable. | Methodology audit F10 |
