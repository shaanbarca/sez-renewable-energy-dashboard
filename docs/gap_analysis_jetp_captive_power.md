# Gap Analysis: JETP Captive Power Study → KEK Dashboard Integration

**Source:** JETP Captive Power Study (December 2025), 187 pages
**Authors:** JETP Secretariat TWG (IEA, IESR, RMI, INDODEPP, World Bank)
**Relevance:** Directly covers captive power at industrial sites — the demand-side counterpart to your supply-side solar analysis

---

## Part 1: What the JETP Report Brings That You Don't Have

### 1.1 Captive Power Database (173 sites, 25.9 GW operating)

The JETP team built an asset-level database of captive power across Indonesia: 500+ power plant units grouped into 173 sites. This includes capacity, fuel type, operational status, owner, associated industry, and coordinates.

**Why it matters for your app:** Your app analyzes 25 KEKs. Many KEKs host captive power plants (especially nickel KEKs in Sulawesi). Knowing which KEKs already have captive coal — and how much — directly affects:
- The within-boundary solar scenario (captive solar competes against captive coal, not PLN tariff)
- The `invest_resilience` flag (sites with existing captive coal have proven they need reliable power — they're prime candidates for captive solar transition)
- Demand estimation (captive power sites have known electricity consumption, not proxied from area × intensity)

**Gap:** Your app doesn't have captive power asset data per KEK. You estimate demand from area × intensity proxy.

### 1.2 Grid Integration Assessment with 30 km Substation Threshold

The JETP report uses a **30 km radius** from captive sites to PLN substations as the threshold for grid integration feasibility. Your app uses 5 km (solar-to-substation) and 15 km (KEK-to-substation).

**Why this matters:** The JETP threshold is more permissive because they're asking a different question — "can this captive site connect to PLN at all?" vs. your question of "is the connection cost-effective for solar?" Both are valid for their purposes, but the JETP's 30 km threshold aligns with the 20-40 km Indonesian IPP corridor norm we discussed. Your 5 km threshold may be too tight for some scenarios.

**Gap:** Your app could benefit from a secondary, more permissive threshold (e.g., 30 km) for the policymaker view showing "technically possible" grid connections, while keeping the 5 km threshold for the investor view showing "economically attractive" connections.

### 1.3 Industrial Clustering Analysis

The JETP report evaluates whether captive sites can cluster — sharing infrastructure, demand management, and access to renewables at scale. 96 of 173 sites were identified as clustering candidates. Their criteria:
- Already in an industrial park
- Within the area of an existing industrial park (via GIS)
- Within 10 km of another captive site with a different owner

**Why it matters:** Industrial clustering directly affects solar economics. A cluster of 5 factories with 500 MW total demand justifies a much larger solar + BESS installation than a single 100 MW factory. Economies of scale improve LCOE. Your KEKs ARE industrial clusters by design — but your app doesn't model the clustering benefit on LCOE.

**Gap:** Your app treats each KEK as a single demand point. It doesn't model how aggregated demand within a KEK (multiple tenants) affects the viability of larger-scale solar. This could strengthen the investment case for KEKs with multiple tenants.

### 1.4 Multi-Resource Screening (Not Just Solar)

The JETP report screens each site for 6 interventions: solar PV (10 km radius), onshore wind (10 km), hydropower (30 km), geothermal (30 km), biomass (province-level), and gas fuel-switching (10 km to pipeline or coast).

**Your app already has:** Solar + wind LCOE comparison, `best_re_technology` selection.

**Your app doesn't have:** Hydropower potential (30 km radius from MEMR One Map), geothermal potential (30 km from MEMR One Map), biomass potential (province-level from MEMR). The JETP report found hydropower is particularly important for remote nickel sites in Sulawesi where solar alone can't provide baseload.

**Gap:** Your app is solar-and-wind-only. For KEKs in regions with strong hydro or geothermal potential (Sulawesi, North Sumatra), the cheapest renewable option might not be solar.

### 1.5 Presidential Regulation 112/2022 Compliance Framework

The JETP report operationalizes Perpres 112/2022, which:
- Prohibits new captive coal (with limited exemptions for downstreaming industries)
- Requires existing captive coal to cut emissions 35% within 10 years
- Mandates all captive coal to cease by 2050

**Why it matters:** This is a hard regulatory deadline that your app doesn't currently reflect. KEKs with existing captive coal face a regulatory clock — they MUST transition. This creates urgency that strengthens the case for solar investment at those specific KEKs.

**Gap:** Your action flags don't account for Perpres 112/2022 compliance timelines. A flag like `regulatory_deadline` could identify KEKs where captive coal must reduce emissions by X date — making the solar investment case time-sensitive.

### 1.6 Renewable Energy Certificate (REC) Pathway

The JETP report analyzes RECs as a decarbonization pathway — where a factory stays on PLN grid power but purchases certificates to claim renewable energy use. This is relevant to your Persona 5 (KEK Tenant) who cares about ESG credentials.

**Gap:** Your GEAS green share metric partially captures this, but RECs are a distinct commercial mechanism. A tenant might achieve ESG compliance through REC purchases without any physical solar infrastructure near their KEK. This is a substitute pathway that your app could flag.

### 1.7 Balmorel System Modelling with Hourly Dispatch

The JETP report uses Balmorel (same tool MEMR uses for RUKN) with hourly dispatch optimization. This captures the reality that captive industrial loads run 24/7 while solar only produces during daylight. The mismatch drives BESS sizing requirements.

**Your app has:** A BESS storage adder model ($250/kWh default, 4h discharge, 2h sizing).

**Gap:** Your BESS model is parametric, not dispatch-optimized. The JETP report's hourly modeling shows that optimal BESS sizing varies significantly by site — some need 2h, some need 4h+. Your flat 2h sizing assumption may underestimate storage costs for 24/7 industrial loads and overestimate for lighter loads.

### 1.8 Financial Assessment with Indonesian-Specific Instruments

The JETP case studies model specific Indonesian financial instruments:
- Income tax waivers (PMK 130/2020): 100% CIT waiver for 10 years if investment > IDR 100 billion
- Grant funding for transmission CAPEX (e.g., UK MENTARI programme)
- Green bonds (SGX benchmark ~5.31%, China benchmark ~2.5%)
- Carbon credit revenue at Indonesian market prices ($2-5/tCO₂)

**Gap:** Your WACC slider captures the blended cost of capital but doesn't model specific Indonesian incentive instruments. Adding a checkbox for "CIT waiver applied" that adjusts the effective LCOE would be valuable for the IPP and DFI personas.

---

## Part 2: Methodological Gaps to Improve What You Already Have

### 2.1 Solar Search Radius: 50 km vs. 10 km

**Your app:** 50 km radius for `pvout_buildable_best_50km`
**JETP report:** 10 km radius for on-site solar PV potential per captive site

These serve different purposes. Your 50 km captures the best solar resource in the region for a grid-connected IPP. The JETP's 10 km captures what's buildable near the factory for captive/on-site solar.

**Recommendation:** You already have both scenarios (within-boundary and grid-connected). But consider:
- Your within-boundary scenario uses `pvout_centroid` (KEK centroid). A 10 km radius around the KEK boundary (not centroid) might find better solar sites that are still "captive-feasible" without needing PLN grid.
- The JETP report notes that for industrial clusters, "far-away solar PV (based on province-level potential)" is enabled. This validates your 50 km approach for grid-connected scenarios.

### 2.2 Capacity Factor Derivation

**Your app:** `CF = PVOUT_annual / 8,760` — derived from actual Global Solar Atlas data, location-specific.
**JETP report:** Uses daily average estimated generation from Global Solar Atlas × solar PV power density from ESDM/DEA Technology Catalogue 2024.

Both approaches use Global Solar Atlas. The JETP report references the **2024** edition of the ESDM Technology Catalogue (your app uses the **2023** edition). The 2024 catalogue may have updated power density and cost assumptions.

**Recommendation:** Check if the 2024 ESDM catalogue has materially different parameters. If so, update your `VERIFIED_TECH006_DATA`.

### 2.3 BESS Sizing for Industrial Loads

**Your app:** Fixed 2h sizing, 4h discharge, $250/kWh.
**JETP report:** The Balmorel model optimizes BESS sizing per site based on hourly dispatch needs. The scenario projects 0.7 GW of BESS by 2030 growing to 13.2 GW by 2050 — suggesting storage becomes critical only at high renewable penetration.

**Recommendation:** Your parametric approach is fine for screening. But consider adding a note that for 24/7 industrial loads (like nickel RKEF), actual BESS requirements may be 2-3x higher than your default. Perhaps add a "high-reliability load" BESS multiplier toggle.

### 2.4 Grid Emission Factors

**Your app:** KESDM 2019 vintage (7 years old). Flagged as known limitation.
**JETP report:** Also acknowledges emissions factor uncertainty but works with more recent data from their Balmorel model outputs.

**Recommendation:** The JETP report's Table 3.1-1 shows projected generation mix by technology through 2050. You could derive implied emission factors from this mix for 2030 as a cross-check against your 2019 factors.

### 2.5 Demand Estimation

**Your app:** Area × intensity proxy. Flagged as a known limitation.
**JETP report:** Asset-level demand modeling with:
- Activity-driven approach for metals (production volume × electricity intensity per tonne)
- Utilization rate assumptions for other industries
- Historical PPU data from MEMR RUKN 2025

**Recommendation:** For KEKs that overlap with JETP database sites, you could import their demand estimates directly — they're more granular than your area proxy. Cross-reference the 173 JETP sites against your 25 KEKs by coordinates.

### 2.6 Connection Cost Formulation

**Your app:** `$5/kW-km + $80/kW` for gen-tie.
**JETP report:** Doesn't provide a per-km cost formula but notes transmission CAPEX as a major sensitivity in case studies. Their financial assessment tests grant-funded transmission as a scenario variant.

**Recommendation:** No change needed to your formula, but consider adding a "grant-funded transmission" toggle that sets the connection cost contribution to zero — reflecting the DFI grant scenario the JETP report models. This would show: "if a DFI covers the gen-tie cost, here's the LCOE impact."

---

## Part 3: New Features to Build (Priority Order)

### P0 — Quick Wins (Low Effort, High Value)

| # | Feature | Source | Effort | Impact |
|---|---|---|---|---|
| 1 | **Add Perpres 112/2022 compliance flag** | JETP Ch.1, Ch.5 | Low — add a boolean per KEK: "has captive coal subject to 35% emission reduction mandate" | High — creates urgency signal for investors and policymakers |
| 2 | **Add ESDM Technology Catalogue 2024 update check** | JETP Ch.2 references 2024 catalogue | Low — compare 2023 vs 2024 CAPEX/performance parameters | Medium — keeps cost assumptions current |
| 3 | **Add grid integration 30 km threshold as secondary view** | JETP Ch.2 uses 30 km for grid integration screening | Low — compute additional distance field, display as layer | Medium — policymaker persona sees broader "technically possible" set |
| 4 | **Cross-reference JETP 173 sites with 25 KEKs** | JETP Captive Power Database | Low-Medium — GIS overlay of JETP site coordinates against KEK polygons | High — imports actual demand data for overlapping KEKs |

### P1 — Meaningful Additions (Medium Effort)

| # | Feature | Source | Effort | Impact |
|---|---|---|---|---|
| 5 | **Add captive coal presence per KEK** | JETP database | Medium — data integration, new field in `dim_kek` | High — distinguishes KEKs with captive coal (transition urgency) from those without (greenfield opportunity) |
| 6 | **Add hydropower potential layer** | JETP Ch.2 uses MEMR One Map run-of-river data, 30 km radius | Medium — new data source, GIS processing, LCOE calculation for hydro | High — some KEKs (Sulawesi) have strong hydro that beats solar |
| 7 | **Add "grant-funded transmission" scenario toggle** | JETP Ch.4 financial assessment | Low-Medium — set connection cost to zero when toggled | Medium — models DFI intervention directly |
| 8 | **Add CIT waiver impact on LCOE** | JETP Ch.4 cites PMK 130/2020 | Medium — model post-tax LCOE with/without CIT waiver | Medium — relevant for IPP persona evaluating real project economics |
| 9 | **Add BESS "high-reliability" multiplier** | JETP Ch.3 shows BESS scaling with penetration | Low — add toggle that doubles BESS sizing for 24/7 industrial loads | Medium — more realistic for manufacturing KEKs |

### P2 — Deeper Integration (Higher Effort)

| # | Feature | Source | Effort | Impact |
|---|---|---|---|---|
| 10 | **Add geothermal potential layer** | JETP Ch.2 uses MEMR One Map, 30 km radius | Medium-High — new data source, new LCOE model for geothermal | Medium — fills gap flagged in your PERSONAS.md |
| 11 | **Add biomass potential layer** | JETP Ch.2 uses MEMR One Map, province-level | Medium — province-level data, simpler than point-based | Low-Medium — biomass is niche but relevant for pulp/paper KEKs |
| 12 | **Import JETP demand projections** | JETP Ch.3 Table 3.1-1 | Medium — parse and integrate scenario data | Medium — replaces area proxy with modeled demand for overlapping sites |
| 13 | **Add REC pathway indicator** | JETP Ch.4 REC analysis | Medium — model REC cost vs. solar LCOE as alternative decarbonization path | Low-Medium — relevant for Tenant persona only |
| 14 | **Industrial clustering benefit on LCOE** | JETP Ch.2 clustering methodology | High — model how aggregated demand within KEK affects solar+BESS sizing and LCOE | Medium — strengthens multi-tenant KEK investment cases |

---

## Part 4: Methodological Alignment Check

| Topic | Your App | JETP Report | Aligned? | Action |
|---|---|---|---|---|
| LCOE formula | CRF-based annuity | Same (via Balmorel) | ✅ Yes | None |
| Solar data source | Global Solar Atlas v2 | Global Solar Atlas (version not specified, likely v2+) | ✅ Yes | None |
| Wind data source | Global Wind Atlas v3 | Not primary focus, but references similar | ✅ Yes | None |
| Buildability filters | Kawasan Hutan, peatland, WorldCover, DEM | UNEP-WCMC protected areas, restricted areas, roads, airports, electricity networks | ⚠️ Partial | JETP includes roads and airport buffers you deferred. Low priority but noted. |
| CAPEX source | ESDM Catalogue 2023 ($960/kW) | ESDM/DEA Catalogue 2024 | ⚠️ Update needed | Check if 2024 values differ materially |
| WACC / discount rate | 10% default, 4-20% slider | 10% (Table 3.2-1) | ✅ Yes | None |
| Substation distance threshold | 5 km (solar), 15 km (KEK) | 30 km (grid integration) | ⚠️ Different purpose | Add 30 km as secondary "technically possible" threshold |
| Solar search radius | 50 km | 10 km (on-site) / province-level (clustered) | ✅ Both valid | Your 50 km is for grid-connected scenario, JETP 10 km is for on-site. Different questions. |
| BESS model | Parametric: $250/kWh, 2h sizing | Balmorel hourly dispatch optimization | ⚠️ Your model is simpler | Fine for screening. Add high-reliability multiplier for 24/7 loads. |
| Grid emission factors | KESDM 2019 | Model-derived, more current | ⚠️ Yours is dated | Update if JETP publishes their derived factors |
| Demand estimation | Area × intensity proxy | Activity-driven (metals) + utilization rates (others) | ⚠️ JETP is better | Import JETP estimates for overlapping KEKs |
| Carbon price | Model output in Balmorel | $2-5/tCO₂ (Indonesian market, 2025) | ⚠️ Your breakeven is static | Consider adding Indonesian carbon price trajectory |
| Regulatory compliance | Not modeled | Perpres 112/2022: 35% reduction in 10 years, cease by 2050 | ❌ Missing | Add compliance flag — high priority |

---

## Part 5: Key Takeaways

1. **The biggest single gap is captive power data.** The JETP database has 173 sites with actual capacity, fuel type, and demand data. Overlaying this onto your 25 KEKs would immediately improve demand estimation, strengthen the within-boundary scenario, and enable the Perpres 112/2022 compliance flag.

2. **Your methodology is sound and largely aligned with JETP.** Same solar data source, same LCOE approach, same WACC assumptions. The differences are scope (they model more technologies) and depth (they do hourly dispatch), not methodology.

3. **The JETP report validates several of your design choices:** the 50 km search radius, the grid-connected IPP-to-PLN model, the recognition that wheeling isn't practical in Indonesia, and the separation of IPP economics (vs. BPP) from tenant economics (vs. tariff).

4. **Hydropower is the biggest technology gap.** For Sulawesi KEKs, hydro may be more important than solar. The JETP report's technical screening found 3.2 GW of run-of-river potential within 30 km of captive sites. Adding this layer would significantly strengthen your tool for eastern Indonesia KEKs.

5. **The Perpres 112/2022 compliance flag is the highest-ROI addition.** It's low effort (a boolean per KEK) but creates a time-sensitive investment signal that none of your current 8 flags capture. It turns your tool from "here's the economics" to "here's the economics AND the regulatory deadline."

---

## Part 6: Public Data Sources for Captive Power Integration

Instead of the full JETP Captive Power Database (not publicly available), three public sources together cover ~80-85% of the same ground.

### 6.1 CGSP Nickel Tracker (PRIMARY for nickel)

**Source:** China-Global South Project — https://nickel.chinaglobalsouth.com/
**License:** Creative Commons (free to use, quote, republish with credit)
**Coverage:** All nickel mining, processing, and battery production projects in Indonesia
**Format:** Interactive map + project list, downloadable data

**What it provides:**
- Project-level coordinates (GIS-ready)
- Industrial process type: RKEF vs. HPAL (critical — determines electricity intensity and reliability needs)
- Capacity and investment amounts
- Ownership structure (which are Chinese-backed)
- Industrial park association (maps to KEKs)
- Operational status (operating, under construction, planned)
- Social and ecological impact flags
- Updated quarterly

**Why it's better than GEM for nickel:** GEM has plant-level data but doesn't distinguish RKEF from HPAL. CGSP does. This distinction directly affects your BESS sizing (RKEF needs 24/7 baseload, HPAL is less intensive) and your `reliability_req` parameter.

**Integration effort:** Low-Medium. Spatial join CGSP coordinates against KEK polygons and 50 km buffer. Each KEK gets: nickel smelter count, total nickel capacity, dominant process type, ownership profile.

### 6.2 Global Energy Monitor (PRIMARY for non-nickel captive power)

**Source:** Global Coal Plant Tracker — https://globalenergymonitor.org/projects/global-coal-plant-tracker/
**License:** Creative Commons (CC BY 4.0)
**Coverage:** All coal power plants globally, including Indonesian captive plants
**Format:** Downloadable spreadsheet with coordinates

**What it provides:**
- Plant-level coordinates
- Capacity (MW)
- Fuel type (coal subtypes)
- Operational status
- Owner/parent company
- Commissioning year (critical for Perpres 112/2022 compliance timeline)
- Heat rate and technology type

**What it doesn't provide:** Industrial process association, electricity intensity, demand projections.

**Use case:** Covers captive coal in pulp & paper, aluminum, steel, mining, and other non-nickel industries that CGSP doesn't track. Combined with CGSP, gives near-complete captive coal coverage.

**Integration effort:** Low. Download spreadsheet, filter to Indonesia captive, spatial join against KEKs.

### 6.3 ESDM Minerba Geoportal (VALIDATION + government authority)

**Source:** https://geoportal.esdm.go.id/minerba/
**License:** Government public data
**Coverage:** Mining concessions (IUP/IUPK), smelter locations, mineral processing facilities

**What it provides:**
- Official government-authoritative smelter and mining locations
- Mining concession boundaries
- Processing facility permits
- Regulatory status

**Use case:** Validates CGSP and GEM data against official government records. Also identifies planned smelters and new concessions that may not yet appear in CGSP or GEM.

**Integration effort:** Medium. Geoportal data may require manual extraction or screen-scraping. GIS layers may be available for download depending on portal capabilities.

### Combined coverage vs. JETP database

| Data Field | JETP Database | CGSP + GEM + ESDM |
|---|---|---|
| Plant coordinates | ✅ 173 sites | ✅ ~80-90% coverage |
| Capacity (MW) | ✅ All | ✅ All |
| Fuel type | ✅ All | ✅ All |
| Operational status | ✅ All | ✅ All |
| Industrial process type | ✅ All (RKEF/HPAL/etc.) | ⚠️ CGSP has nickel process types; GEM doesn't for others |
| Ownership | ✅ All | ✅ CGSP has detailed Chinese ownership; GEM has parent company |
| Industrial park association | ✅ All | ✅ CGSP maps to industrial parks |
| Electricity intensity (kWh/tonne) | ✅ Metals sector | ❌ Not available — would need to use JETP report benchmarks as assumptions |
| Demand projections | ✅ Asset-level through 2050 | ❌ Not available — continue using area × intensity proxy + CGSP capacity as supplement |
| Grid integration assessment | ✅ 30 km substation screening | ✅ You already do this (5 km / 15 km thresholds) |
| Commissioning year | ✅ All | ✅ GEM has this; enables Perpres 112/2022 compliance flag |
| Social/environmental impact | ❌ Limited | ✅ CGSP has social and ecological impact flags for nickel |

---

## Part 7: Revised Priority List (with data sources mapped)

### P0 — Quick Wins

| # | Feature | Data Source | Effort | Impact |
|---|---|---|---|---|
| 1 | **Overlay CGSP nickel smelters on KEK map** | CGSP Nickel Tracker (CC license) | Low | High — immediately shows which KEKs have nickel processing, process type, and captive power demand |
| 2 | **Overlay GEM captive coal on KEK map** | Global Energy Monitor (CC BY 4.0) | Low | High — shows non-nickel captive coal presence per KEK |
| 3 | **Add Perpres 112/2022 compliance flag** | GEM commissioning year + regulation text | Low | High — time-sensitive investment signal. Plants post-2022 must cut 35% in 10 years. All captive coal must cease by 2050. |
| 4 | **Add captive coal summary per KEK** | CGSP + GEM combined | Low | High — new field: `captive_coal_mw`, `captive_coal_count`, `dominant_process_type` |
| 5 | **Check ESDM Tech Catalogue 2024 vs. 2023** | ESDM website | Low | Medium — ensure CAPEX/performance assumptions are current |

### P1 — Meaningful Additions

| # | Feature | Data Source | Effort | Impact |
|---|---|---|---|---|
| 6 | **Interactive scale selector → scorecard LCOE recalculation** | Existing LCOE vs Scale chart + model | Medium — add `target_capacity_mwp` parameter; scorecard recomputes LCOE at user-chosen capacity instead of `max_captive_capacity_mwp`. Gen-tie cost and substation capacity check also respond (at 50 MW substation may suffice; at 200 MW needs upgrade). Let users click a point on existing LCOE curve or use a slider. | High — answers IPP's core question "how big should I build?" Read-only curve shows the sweet spot; this lets them act on it. |
| 7 | **Add 30 km "technically possible" grid integration layer** | Existing substation data | Low-Medium | Medium — policymaker view of broader connection potential |
| 8 | **Add "grant-funded transmission" scenario toggle** | JETP report financial assessment methodology | Low-Medium | Medium — models DFI intervention on gen-tie cost |
| 9 | **Add BESS "high-reliability" multiplier for RKEF KEKs** | CGSP process type data | Low | Medium — RKEF sites need more storage than default 2h |
| 10 | **Compute `grid_investment_needed_usd` as first-class column** | Existing model fields | Low | Medium — multiply `transmission_cost_per_kw × solar_mwp × 1000` |
| 11 | **Add CIT waiver impact on LCOE** | PMK 130/2020 tax incentive rules | Medium | Medium — relevant for IPP evaluating project economics |
| 12 | **Add hydropower potential layer** | MEMR One Map run-of-river data (30 km radius) | Medium | High for Sulawesi KEKs — hydro may beat solar |

### P2 — Deeper Integration

| # | Feature | Data Source | Effort | Impact |
|---|---|---|---|---|
| 12 | **Cross-reference ESDM Minerba Geoportal for validation** | ESDM Geoportal | Medium | Medium — government-authoritative validation of CGSP/GEM data |
| 13 | **Add geothermal potential layer** | MEMR One Map | Medium-High | Medium — fills gap for Sulawesi, North Sumatra KEKs |
| 14 | **Add biomass potential layer** | MEMR One Map (province-level) | Medium | Low-Medium — niche but relevant for pulp/paper KEKs |
| 15 | **Import JETP demand projections** (if database obtained) | JETP Secretariat | Medium | Medium — replaces area proxy with modeled demand |
| 16 | **Add REC pathway indicator** | JETP report REC analysis methodology | Medium | Low-Medium — alternative decarbonization path for Tenant persona |
| 17 | **Industrial clustering benefit on LCOE** | CGSP industrial park associations | High | Medium — models how aggregated demand improves solar+BESS sizing |
| 18 | **Add social/environmental impact flags from CGSP** | CGSP impact data | Low | Low-Medium — ESG-relevant for Tenant and DFI personas |

---

## Part 8: Usefulness Rating

### Rating Framework

Scored on 4 dimensions, each out of 10:
- **Unique Value:** Does anything else do this? How differentiated is it?
- **Analytical Depth:** How rigorous and defensible is the methodology?
- **Actionability:** Can a user make a real decision based on the output?
- **Audience Reach:** How many personas/stakeholders find it useful?

### Current State (v3.1, as built today) — CORRECTED

*Original assessment scored 7.3/10 based on incorrect assumption that buildable polygons and LCOE scale visualization were missing. Corrected after reviewing implementation details: polygons are fully built (`build_buildable_polygons.py`), LCOE vs Scale chart exists (read-only). The missing piece is an interactive scale selector that recalculates scorecard LCOE at a user-chosen build size.*

| Dimension | Score | Rationale |
|---|---|---|
| Unique Value | **9/10** | Nothing else combines KEK-level solar/wind LCOE + grid infrastructure gap analysis + action flags + buildable polygons + adjustable assumptions in an interactive dashboard for Indonesia. |
| Analytical Depth | **8/10** | Strong on solar resource, LCOE methodology, grid proximity, and buildability (polygons with area/capacity/PVOUT). LCOE vs Scale chart shows the economics curve. Weak on demand estimation (area proxy), captive power baseline (not modeled), and single-technology focus (solar + wind only). |
| Actionability | **7/10** | Polygons let IPPs see actual site options on the map. LCOE curve shows the sweet spot visually. But scorecard always computes at max capacity — users can't test specific build sizes interactively. No captive power data limits demand-side insight. |
| Audience Reach | **7.5/10** | 5 well-defined personas. Polygons strengthen IPP persona significantly (they can see sites, not just dots). Tenant persona still weakest (65% readiness). |
| **Overall** | **7.9/10** | A strong screening tool with genuine spatial analysis capabilities. The read-only LCOE curve and polygon visualization put it ahead of most comparable tools. Main gaps: interactive scale selection, captive power data, and technology scope. |

### Competitive Position (Current State)

| Competitor / Alternative | What it does | What it doesn't do (that you do) |
|---|---|---|
| Global Solar Atlas | Solar resource mapping globally, PVOUT at any point | No LCOE with grid costs, no KEK/SEZ context, no action flags, no grid infrastructure assessment, no policy view |
| Solargis / PVcase Prospect | Professional solar siting with high resolution, project design | Commercial (paid), no Indonesia regulatory context, no KEK targeting, no grid gap analysis, no policy personas |
| NREL reV Model | Spatial LCOE optimization with transmission access (US-focused) | Not available for Indonesia, no industrial zone targeting, no adjustable assumptions dashboard, requires technical expertise to run |
| IESR "Beyond 443 GW" | Indonesia-wide renewable potential assessment | Static report (not interactive), no KEK-level analysis, no grid infrastructure gap analysis, no LCOE calculator |
| JETP Captive Power Study | Asset-level captive power transition pathways with Balmorel modeling | Static 187-page PDF report, not interactive, no user-adjustable assumptions, no spatial dashboard |
| ETP/BAPPENAS Solar Mapping | Indonesia solar potential for BAPPENAS grid planning | Not publicly available as interactive tool, no KEK targeting, no LCOE, no action flags |
| PLN RUPTL | Official grid development plans | PDF document, not interactive, no solar potential overlay, no gap analysis |

**Your niche:** You are the only tool that sits at the intersection of renewable energy potential + industrial demand at specific economic zones + grid infrastructure constraints + policy-relevant action flags, in an interactive format. Nobody else occupies this space.

### With Full Integration (CGSP + GEM + ESDM + JETP features + interactive scale selector)

| Dimension | Current | Integrated | Change | What drives the improvement |
|---|---|---|---|---|
| Unique Value | 9/10 | **10/10** | +1 | Adding captive power overlay and Perpres 112/2022 compliance creates a completely unique tool. No one else connects renewable supply potential to existing captive coal assets at specific industrial zones with regulatory transition timelines. |
| Analytical Depth | 8/10 | **9/10** | +1 | CGSP gives real industrial process data (RKEF/HPAL), GEM gives commissioning years for compliance analysis, hydropower adds technology coverage. Interactive scale selector makes LCOE analysis dynamic, not static. |
| Actionability | 7/10 | **9/10** | +2 | Biggest jump. Interactive scale selector lets IPPs answer "how big should I build?" Captive coal presence + compliance deadlines create urgency. Process types inform BESS sizing. A DFI analyst could write an investment memo from this. A policymaker could draft a RUPTL recommendation. |
| Audience Reach | 7.5/10 | **9/10** | +1.5 | Tenant persona strengthens with captive coal data and compliance timelines. IPP persona gains interactive project sizing. New potential audience: ESG/sustainability teams at nickel companies, JETP Secretariat staff. |
| **Overall** | **7.9/10** | **9.3/10** | **+1.4** | Moves from "strong screening tool" to "reference platform for KEK clean energy transition analysis." |

### What the remaining 0.7 points would require

To reach a hypothetical 10/10:
- Hourly dispatch modeling (Balmorel-level, not parametric BESS) → requires significant engineering investment
- Actual PLN demand data per KEK (not proxy) → requires PLN partnership or JETP database access
- Real-time or frequently updated grid capacity data from PLN → requires PLN data sharing agreement
- Geothermal + biomass potential layers → requires additional MEMR data integration

These require institutional partnerships, not just engineering. The 9.3/10 integrated version is the realistic ceiling for what you can build with publicly available data and your current architecture.
