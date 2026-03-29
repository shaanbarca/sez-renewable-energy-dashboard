# Personas — Indonesia KEK Power Competitiveness Dashboard

Four primary user personas. Each section covers: who they are, what they need from the data, their step-by-step journey through the dashboard, what they export, and how they'd cite the tool.

**Related:** [DESIGN.md](DESIGN.md) | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

---

## Table of Contents

- [Readiness Summary](#readiness-summary)
- [Gap Priority](#gap-priority)
- [Persona 1: Energy Economist](#persona-1-energy-economist) — multilateral development bank analyst (ADB, IFC)
- [Persona 2: DFI Investor](#persona-2-dfi-investor) — infrastructure fund analyst (Macquarie Green, AIIB)
- [Persona 3: Policy Maker](#persona-3-policy-maker) — BKPM/KESDM official or energy think-tank adviser
- [Persona 4: Energy Investor (IPP Developer)](#persona-4-energy-investor-ipp-developer) — captive solar developer (ACEN, Vena Energy)

---

## Readiness Summary

*Last assessed: 2026-03-29. Re-assess after each major pipeline change.*

| Persona | Score | Status | Top blocking gap |
|---------|-------|--------|-----------------|
| Energy Economist | **68%** | Core LCOE + carbon breakeven built; concessional finance story incomplete | WACC range stops at 8% — can't model 4–6% blended DFI financing; BPP null |
| DFI Investor | **85%** | All-in LCOE + project_viable + buildability + substation all present | Flood hazard (Layer 2d) and road proximity (Layer 3a) not yet sourced |
| Policy Maker | **62%** | Action flags + RUPTL pipeline solid | Model is solar-only — misleading `not_competitive` at Sulawesi KEKs with known wind/geothermal |
| Energy Investor (IPP) | **80%** | All-in PPA cost + project_viable + buildability + substation screening complete | `demand_mwh_2030` is a proxy — can rank sites but cannot size a PPA |

---

## Gap Priority

Ranked by impact across personas × implementation effort. See each persona's `### Data gaps` section for full detail.

| Priority | Gap | Personas affected | Effort |
|----------|-----|------------------|--------|
| ✅ 1 DONE | **Transmission lease fee in all-in LCOE** — `lcoe_remote_captive_allin_*` now in scorecard; adder = $10/MWh mid ($5–$15 range) for all 23 remote_captive KEKs | P2, P4 | Done |
| ✅ 2 DONE | **`project_viable` boolean** — in `fct_kek_scorecard`; threshold `max_captive_capacity_mwp ≥ 20 MWp`; all 25 KEKs = True at 1km resolution | P2, P4 | Done |
| 🟠 3 | **WACC expansion to 6% and 14%** — concessional-to-equity full range; stops at 8% today | P1 | Low — 2 extra rows per KEK in `fct_lcoe` |
| 🟠 4 | **BPP data sourcing** — PLN Statistik 2024 regional BPP; `bpp_usd_mwh` column exists but null | P1 | Medium — external data, not code |
| 🟠 5 | **Grid emission factor update** — KESDM 2019 → IEA SEA 2024; affects `carbon_breakeven_usd_tco2` | P1, P3 | Low code / medium research |
| 🟡 6 | **Wind CF layer for Sulawesi** — fixes misleading `not_competitive` at kek-palu, kek-bitung, kek-morotai | P3 | Medium — new data source + pipeline step |
| 🟡 7 | **KEK operational status enrichment** — distinguish operating (tenants present) vs. greenfield | P4 | Medium — BKPM/KEK management data required |
| 🟢 8 | **Road proximity (Layer 3a)** — construction access cost; OSM PBF processing | P2, P4 | High effort |
| 🟢 9 | **Flood hazard (Layer 2d)** — BNPB portal inaccessible; low incremental value over slope layer | P2 | High effort / blocked |

---

## Persona 1: Energy Economist

**Role:** Economic analyst, multilateral development bank (ADB, IFC, World Bank)
**Context:** Preparing a country energy competitiveness assessment or a captive renewable energy policy brief. Needs to compare solar LCOE against grid cost across many sites simultaneously and quantify the carbon arbitrage opportunity. Works in Excel and PowerPoint; exports data for colleagues.
**Primary question:** *At our fund's hurdle rate, which KEKs already make economic sense for captive solar — and what policy change would unlock the others?*

### Readiness — 68%

**What works:**
- Full LCOE bands (low/mid/high) at WACC 8/10/12% — competitive gap and concessional-finance flip case are computable
- `carbon_breakeven_usd_tco2` populated for all 25 KEKs — carbon finance desk can use this directly
- `green_share_geas` and GEAS allocation methodology complete
- Provisional flags (`is_cf_provisional`, `is_capex_provisional`) so the economist can caveat outputs

**What's missing:**
- **WACC range stops at 8%** — concessional DFI financing at 4–6% is the core policy argument; the tool can't model it without adding more WACC snaps to `fct_lcoe` (Gap priority 🔴 3)
- **BPP is null** — grid reference is I-4 tariff ($63.08). PLN's true cost of supply is 15–35% higher at most regions; the LCOE gap vs. BPP (more favourable for solar) can't be shown (Gap priority 🟠 4)
- **Grid emission factor is 2019 vintage** — `carbon_breakeven_usd_tco2` uses stale KESDM data (Gap priority 🟠 5)

### Key data needs

- `lcoe_mid_wacc10_usd_mwh` — baseline LCOE at 10% WACC
- `solar_competitive_gap_wacc10_pct` — how far from grid parity (positive = solar more expensive)
- `solar_now_at_wacc8` — does the KEK flip to competitive under DFI concessional financing?
- `carbon_breakeven_usd_tco2` — carbon price at which solar becomes cost-competitive (useful for carbon finance desk)
- `green_share_geas_2030_pct` — how much of this KEK's 2030 demand could GEAS-allocated solar cover?

### User journey

1. **Land on Overview Map** — scan which KEKs are green (`solar_now`) vs. red (`not_competitive`). Note geographic clustering (Java manufacturing belt vs. eastern islands).
2. **Open Quadrant Chart** — set WACC radio to 10% (standard hurdle rate). Read which KEKs sit in the "Solar now" quadrant vs. "Grid first".
3. **Switch WACC to 8%** — observe which KEKs shift into "Solar now". These are the concessional-finance flip cases — the core policy argument.
4. **Open Flip Scenario Panel** — slide the competitive-gap threshold to 20% to see all KEKs within striking distance. Note which ones are `invest_resilience` (manufacturing, high reliability requirement).
5. **Open Ranked Table** — sort by `solar_competitive_gap_wacc10_pct` ascending. Add `carbon_breakeven_usd_tco2` column to identify carbon finance candidates.
6. **Export CSV** — download `fct_kek_scorecard` for the economic analysis annex.
7. **Drill into 2–3 KEK Scorecards** — verify PVOUT source, confirm `is_capex_provisional` flag, note `grid_emission_factor_t_co2_mwh` for carbon math.
8. **Cite in report** — reference the GitHub Release version tag for reproducibility.

### What they export
Ranked table CSV → paste into Excel economic comparison table. Carbon breakeven column → input to carbon finance sensitivity model.

### What they'd cite
> "Source: KEK Power Competitiveness Dashboard v1.0 (github.com/…/releases/tag/v1.0). LCOE computed using ESDM Technology Catalogue 2023 CAPEX ($960/kW), grid cost from Permen ESDM 7/2024 I-4/TT tariff ($63.08/MWh), PVOUT from Global Solar Atlas v2."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `bpp_usd_mwh` is null | BPP (PLN cost of supply) is 15–35% higher than the I-4/TT tariff used today. An economist needs both: tariff (what tenants pay) and BPP (what grid electricity costs PLN). The LCOE gap vs. BPP would look more favourable for solar at high-BPP regions. | Blocked — PLN Statistik 2024 regional BPP not yet sourced; column exists in `fct_grid_cost_proxy` but is null. |
| Grid emission factor is 2019 vintage | `grid_emission_factor_t_co2_mwh` (KESDM Tier 2 OM 2019) is 5+ years old. `carbon_breakeven_usd_tco2` inherits this staleness — the carbon price threshold may be over- or under-stated. | Deferred to v1.2 — update to 2023 KESDM or IEA SEA 2024 data. |
| WACC range limited to 8/10/12% | Concessional DFI financing can go to 4–6%; some equity hurdles are 14–16%. The 3-snap WACC range doesn't cover the full spectrum an economist would model. | Deferred to Phase 3 Step 3.1 (design decision: snap vs. continuous interpolation). |
| CAPEX from ESDM catalogue, not Indonesia market data | ESDM 2023 catalogue value ($960/kW) may be ±15–20% from current Indonesian EPC market pricing. LCOE bands partially capture this but no market comparables have been sourced. | Deferred to v1.2 — source 2023–2024 Indonesia solar EPC tender data. |

---

## Persona 2: DFI Investor

**Role:** Infrastructure fund analyst or investment director, development finance institution or green infrastructure fund (Macquarie Green Infrastructure, AIIB, OPIC/DFC)
**Context:** Screening Indonesian industrial sites for a captive solar PPA or equity investment. Needs to know: is there enough buildable land, how far is the grid connection, and what does the LCOE look like at their fund's cost of capital? Will hand off promising sites to a site development team.
**Primary question:** *Which KEKs have sufficient buildable solar land, acceptable grid connection cost, and an LCOE that works at our 8% target return?*

### Readiness — 85%

**What works:**
- Full 4-layer buildability filter: `buildable_area_ha`, `max_captive_capacity_mwp`, `buildability_constraint` all populated for all 25 KEKs
- `dist_to_nearest_substation_km` and `nearest_substation_capacity_mva` (19/25 KEKs) — screening-level grid connection data available
- `siting_scenario` (`within_boundary` / `remote_captive`) drives gen-tie cost in LCOE
- `lcoe_mid_wacc8_usd_mwh` and `solar_now_at_wacc8` — fund hurdle rate scenario built
- `lcoe_remote_captive_allin_usd_mwh` (+ low/high bands) in scorecard — full all-in cost including ~$10/MWh transmission lease for 23/25 remote_captive KEKs
- `project_viable` boolean in scorecard — True when `max_captive_capacity_mwp ≥ 20 MWp` (all 25 KEKs pass at current 1km resolution)

**What's missing:**
- Flood hazard (Layer 2d) and road proximity (Layer 3a) not yet sourced — relevant for coastal and remote KEKs (Gap priority 🟢 8, 9)

### Key data needs

- `pvout_buildable_best_50km` — best solar yield in buildable (non-excluded) land within 50km
- `max_captive_capacity_mwp` — maximum installable capacity given buildable area
- `buildable_area_ha` — raw land area passing all four buildability filters
- `buildability_constraint` — which layer is the binding land constraint (peat / forest / agriculture / slope)
- `dist_to_nearest_substation_km` — gen-tie distance proxy
- `siting_scenario` — `within_boundary` (no gen-tie cost) vs. `remote_captive` (gen-tie CAPEX adder)
- `lcoe_mid_wacc8_usd_mwh` — LCOE at fund's 8% hurdle rate
- `solar_now_at_wacc8` — binary competitive flag at that rate

### User journey

1. **Land on Overview Map** — filter to `solar_now_at_wacc8 = True` or `invest_resilience = True`. These are the actionable sites.
2. **Open Ranked Table** — sort by `max_captive_capacity_mwp` descending to find sites large enough for a utility-scale captive plant (≥ 50 MWp threshold).
3. **Filter table** — keep only sites where `siting_scenario = within_boundary` (prefer sites where the solar plant fits inside the KEK, minimising gen-tie risk).
4. **Check buildability constraint** — sites with `buildability_constraint = peat` or `kawasan_hutan` flag land tenure risk; sites with `agriculture` flag negotiation risk.
5. **Drill into KEK Scorecard (Resource tab)** — review `pvout_buildable_best_50km`, `buildable_area_ha`, and the 50km radius map for 3–5 shortlisted KEKs.
6. **Switch to LCOE tab** — verify LCOE bands at WACC=8% (within_boundary vs. remote_captive scenarios). Note whether `is_capex_provisional` is flagged.
7. **Check substation distance** — confirm `dist_to_nearest_substation_km` for remote_captive sites; large distances (+50km) escalate gen-tie CAPEX beyond the adder.
8. **Export GeoJSON** — download `kek_polygons` joined with scorecard for site team hand-off to GIS analyst.

### What they export
GeoJSON for site team GIS analysis. CSV with LCOE + buildable area columns for investment committee screening memo.

### What they'd cite
> "Buildable solar resource estimated using ESA WorldCover v200 land cover exclusions, Copernicus DEM slope/elevation, and GFW peatland data. Source: KEK Power Competitiveness Dashboard v1.0."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| Flood hazard layer (Layer 2d) missing | Coastal sites (tanjung-sauh, kek-tanjung-lesung, kek-morotai) may have buildable land on flood-prone ground not yet excluded. `buildable_area_ha` may be slightly overstated at these sites. | Deferred to v1.2 — BNPB portal inaccessible; low overlap with slope layer. |
| Road proximity (Layer 3a) missing | Remote sites with poor road access have higher EPC construction costs not reflected in any current column. A DFI site team needs this to estimate total development cost. | Deferred to v1.2 — requires OSM PBF processing. |
| ~~Substation capacity unknown~~ | `nearest_substation_capacity_mva` is now in the scorecard — normalized from the PLN `kapgi` field (mixed VA/MVA units corrected). 5 of 25 KEKs have null capacity (data not recorded in PLN's dataset). | ✅ Built — available in `fct_kek_scorecard` as `nearest_substation_capacity_mva`. |
| ~~Transmission lease fee not modelled~~ | ~5–15 USD/MWh for large remote captive projects was excluded from all-in LCOE. | ✅ Built — `lcoe_remote_captive_allin_usd_mwh` (+ low/high bands) in `fct_kek_scorecard`. Adder = $10/MWh mid ($5–$15 range) for all remote_captive KEKs. |
| ~~No minimum viable project flag~~ | `buildable_area_ha` was present but no derived boolean for investor viability threshold. | ✅ Built — `project_viable` boolean in `fct_kek_scorecard` (threshold: `max_captive_capacity_mwp ≥ 20 MWp`). All 25 KEKs = True at 1km resolution. |

---

## Persona 3: Policy Maker

**Role:** Senior official, BKPM (Investment Coordinating Board) or KESDM (Ministry of Energy), or technical adviser at an energy think-tank (IESR, Rocky Mountain Institute Indonesia)
**Context:** Preparing input for a RUPTL review, a KEK electricity regulation update, or a green industrial park policy. Needs to understand which KEKs will be left behind by the current grid plan, which ones could benefit from WACC de-risking (concessional finance), and how much of 2030 demand could be met by GEAS-allocated solar.
**Primary question:** *Which KEKs need policy intervention — and what specific intervention (WACC de-risking, RUPTL acceleration, GEAS allocation) would have the most impact?*

### Readiness — 62%

**What works:**
- All 5 action flags (`solar_now`, `grid_first`, `firming_needed`, `invest_resilience`, `plan_late`) populated for all 25 KEKs
- Full RUPTL pipeline context: `pre2030_solar_mw`, `post2030_share`, `grid_upgrade_pre2030`, `ruptl_summary`
- `green_share_geas` quantifies GEAS allocation as a policy lever
- `carbon_breakeven_usd_tco2` supports carbon market design arguments

**What's missing:**
- **Model is solar-only** — kek-palu, kek-bitung, kek-morotai are Sulawesi/Maluku KEKs where geothermal and wind are the primary clean energy opportunity; `not_competitive` at these sites is potentially misleading to a KESDM adviser (Gap priority 🟡 6)
- **21/25 KEKs show `not_competitive`** — the flag is binary; a policy maker needs to see the *distance* to competitiveness (a 5% gap vs. 35% gap require entirely different interventions), which requires drilling into `solar_competitive_gap_pct` rather than reading the flag
- **`reliability_req` is hardcoded by KEK type**, not sourced from PLN SAIDI/SAIFI data — the `invest_resilience` flag (4 KEKs) rests on assumed outage scores, weakening its credibility with KESDM technical reviewers (Gap priority 🟡 — deferred to v2)
- **`demand_mwh_2030` is a proxy** — GEAS `green_share_geas` inherits area × intensity uncertainty; cannot be cited as a precise policy target

### Key data needs

- `action_flag` — the recommended action per KEK (`solar_now`, `invest_resilience`, `grid_first`, `not_competitive`)
- `plan_late` — is the RUPTL pipeline arriving after 2030? (flags KEKs that need grid acceleration)
- `green_share_geas_2030_pct` — share of 2030 demand potentially met by GEAS-allocated solar
- `ruptl_re_base_2030_mw` — PLN's own RE pipeline for this region by 2030
- `solar_competitive_gap_wacc10_pct` — economic gap at market WACC
- `solar_now_at_wacc8` — does concessional finance (8%) close the gap?
- `carbon_breakeven_usd_tco2` — carbon price needed for solar competitiveness (relevant to carbon market design)

### User journey

1. **Land on Overview Map** — view spatial distribution of action flags. Note whether `not_competitive` KEKs are clustered in a specific region (suggesting a grid system-level problem, not a site-specific one).
2. **Open RUPTL Context view** — set year range to 2025–2030. Identify which grid regions have a significant RE pipeline vs. which are flat (low grid improvement expected by 2030).
3. **Filter Ranked Table to `plan_late = True`** — these KEKs are most at risk: grid improvement is coming, but after 2030. Flag for RUPTL acceleration recommendation.
4. **Open Flip Scenario Panel** — set WACC to 8%. Count how many currently `not_competitive` KEKs flip to `solar_now`. This is the policy case for concessional finance or WACC de-risking instruments.
5. **Check `green_share_geas_2030_pct`** — for KEKs with high `solar_now` probability, assess whether GEAS allocation is a viable substitute for captive solar or a complement.
6. **Drill into KEK Scorecard (Pipeline tab)** — for 3–5 KEKs of interest, verify which RUPTL scenario (RE Base vs. ARED) changes the `plan_late` flag.
7. **Export CSV** — download ranked table with `action_flag`, `plan_late`, `green_share_geas_2030_pct` for use in RUPTL review submission.
8. **Cite in policy brief** — reference data sources and methodology for credibility with technical reviewers.

### What they export
Ranked table CSV filtered to `plan_late = True` KEKs. Screenshot of RUPTL Context view for presentation slide. Green share column for GEAS policy memo.

### What they'd cite
> "KEK-level solar competitiveness analysis, KEK Power Competitiveness Dashboard v1.0. Grid cost: Permen ESDM 7/2024. RUPTL pipeline: RUPTL PLN 2025–2034. GEAS allocation methodology: METHODOLOGY.md §5."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `reliability_req` is hardcoded by KEK type | `invest_resilience` and `firming_needed` flags depend on `reliability_req` set by KEK type (manufacturing=0.8, tourism=0.4) in `kek_grid_region_mapping.csv` — not from actual PLN SAIDI/SAIFI outage data. A policy maker needs real grid reliability data to make the resilience case credible to KESDM. | Deferred to v2 — PLN publishes SAIDI/SAIFI by grid system but not by KEK; requires manual mapping. |
| `demand_mwh_2030` is area × intensity proxy | GEAS `green_share_geas` is allocated against proxy demand, not actual tenant consumption. Policy allocation recommendations inherit this uncertainty. | Deferred — requires tenant surveys or KESDM KEK energy consumption registry. |
| No wind or geothermal resource layer | Model is solar-only. Sulawesi KEKs (kek-palu, kek-bitung, kek-morotai) have known geothermal and wind resources. A `not_competitive` or `grid_first` label at these sites may be misleading — a policy maker advising on Sulawesi needs the full clean energy picture. | Deferred to v1.2 — add wind CF layer; geothermal requires a separate data source. |
| Carbon price trajectory not modelled | `carbon_breakeven_usd_tco2` is a static threshold (the price that closes today's gap). No link to Indonesia's ETS trajectory (Article 6 commitments, IDR carbon market). Policy makers need: "at Indonesia's projected carbon price path, when does solar become competitive?" | Deferred to v1.2 — requires IDR carbon price forecast data. |
| GEAS allocation is a modelled approximation | Real GEAS depends on PLN tender design, offtake eligibility, and transmission access rights. Pro-rata allocation is an indicative estimate, not a contractual figure. | Fundamental limitation — label clearly in dashboard; cannot be resolved without PLN tender rules. |

---

## Persona 4: Energy Investor (IPP Developer)

**Role:** Business development manager or country director, captive solar IPP developer (ACEN, SolarEdge Indonesia, Vena Energy, local developer)
**Context:** Building a project pipeline of captive solar PPAs with industrial tenants at KEKs. Needs to prioritise outreach — which KEKs have the largest demand, best solar resource, and weakest grid (making the PPA pitch easiest)? Will use this data to rank sites for BD outreach, then hand off top 5 to technical team for desktop feasibility.
**Primary question:** *Which KEKs offer the best PPA opportunity — large captive demand, good solar, high grid cost, and buildable land inside the zone?*

### Readiness — 80%

**What works:**
- Full buildability screening: `max_captive_capacity_mwp`, `buildable_area_ha`, `pvout_buildable_best_50km` all populated
- `nearest_substation_capacity_mva` available for 19/25 KEKs — gives grid absorption signal for initial screening
- `siting_scenario` and gen-tie cost baked into `remote_captive` LCOE — IPP can see the real economics
- `demand_mwh_2030` for relative site ranking (not PPA sizing)
- `lcoe_remote_captive_allin_usd_mwh` in scorecard — lease adder ($10/MWh mid) applied; all-in PPA cost for remote sites accurately stated
- `project_viable` boolean in scorecard — IPP threshold (≥ 20 MWp) automated; all 25 KEKs pass at current buildability resolution

**What's missing:**
- **`demand_mwh_2030` is a proxy** — area × intensity estimate cannot be used for PPA term sheet sizing; field surveys required before commercial conversations (Gap priority 🟡 7 for status enrichment; demand proxy is a fundamental limitation)
- **KEK operational status is coarse** — `status` from scraper doesn't distinguish operating KEKs with paying tenants from greenfield development; an IPP pitching into a greenfield KEK faces speculative demand (Gap priority 🟡 7)
- Substation capacity partial — 6/25 KEKs have null `nearest_substation_capacity_mva` (data not recorded in PLN dataset)

### Key data needs

- `demand_mwh_2030` — total electricity demand at KEK in 2030 (PPA size proxy)
- `max_captive_capacity_mwp` — maximum buildable capacity (determines if a utility-scale PPA is feasible)
- `pvout_buildable_best_50km` — best solar yield in buildable land (determines PPA competitiveness)
- `grid_cost_usd_mwh` — the benchmark the PPA must beat (higher = easier to win)
- `siting_scenario` — `within_boundary` preferred (no gen-tie cost = better PPA economics)
- `solar_competitive_gap_wacc10_pct` — gap at market WACC; negative = solar already wins at market rate
- `buildability_constraint` — land constraint type affects site development complexity

### User journey

1. **Open Ranked Table** — sort by `max_captive_capacity_mwp` descending. IPP threshold: ≥ 30 MWp (below this, project economics are marginal for a developer). Note initial list of ~10 KEKs above threshold.
2. **Filter to `solar_now = True` or `invest_resilience = True`** — these are the sites where the PPA pitch is straightforward (solar already cheaper or within striking distance).
3. **Sort by `demand_mwh_2030` descending** — larger demand = larger PPA = better project economics. Prioritise KEKs where both capacity and demand are large.
4. **Check `siting_scenario`** — prefer `within_boundary` sites. For `remote_captive` sites, check `dist_to_nearest_substation_km`; > 30 km adds meaningful gen-tie cost that erodes PPA margin.
5. **Check `buildability_constraint`** — `slope` and `unconstrained` are low-risk. `agriculture` means land acquisition negotiation. `peat` or `kawasan_hutan` are high-risk (regulatory / environmental).
6. **Open Quadrant Chart** — confirm shortlisted KEKs are in the "Solar now" or "Invest: resilience" quadrant at WACC=10%.
7. **Drill into KEK Scorecard for top 3–5 sites** — review PVOUT map (Resource tab), LCOE bands (LCOE tab), demand profile (Demand tab). Download scorecard PDF or screenshot for BD deck.
8. **Export CSV** — top 10 KEKs with all relevant columns for BD pipeline tracker spreadsheet.

### What they export
Ranked table CSV (top 10 sites) for BD pipeline tracker. KEK Scorecard screenshots for project pitch deck. GeoJSON for desktop site analysis.

### What they'd cite
> "Solar resource and land buildability: KEK Power Competitiveness Dashboard v1.0. Buildable area uses ESA WorldCover + GFW Peatlands exclusions. Demand estimates are provisional (area × intensity proxy); field surveys required for PPA sizing."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `demand_mwh_2030` is area × intensity proxy | PPA sizing requires actual tenant electricity consumption or signed LOIs. The proxy figure must not be used for PPA term sheet calculations — it exists only for relative ranking between KEKs. | Deferred — requires field surveys or KEK management data. Caveat already noted in "What they'd cite". |
| ~~No minimum PPA size flag~~ | `max_captive_capacity_mwp` was present but no derived boolean for IPP viability threshold. | ✅ Built — `project_viable` boolean in `fct_kek_scorecard`. IPP threshold: `max_captive_capacity_mwp ≥ 20 MWp`. All 25 KEKs = True at 1km resolution. |
| ~~Transmission lease fee not modelled~~ | ~5–15 USD/MWh excluded from `remote_captive` LCOE; all-in PPA cost was understated for remote sites. | ✅ Built — `lcoe_remote_captive_allin_usd_mwh` in `fct_kek_scorecard`. All-in cost for remote sites now includes ~$10/MWh lease adder ($5–$15 range). |
| KEK operational status is coarse | `status` field (from OSS scraper) does not distinguish "operating with paying tenants" (offtake certainty) from "under development" (speculative demand). An IPP needs to know if tenants are actually there. | Deferred — requires KEK management outreach or BKPM tenant occupancy registry. |
| Substation capacity coverage is partial | `nearest_substation_capacity_mva` is available (normalized from PLN `kapgi` field) but 5 of 25 KEKs have null capacity — PLN did not record it for those substations. | Available with gaps — 20/25 KEKs have capacity data. |
| No road proximity layer | Construction access cost for remote sites is not captured. A site with poor road access has higher EPC cost not reflected in any current column. | Deferred to v1.2 — requires OSM PBF processing (Layer 3a). |
