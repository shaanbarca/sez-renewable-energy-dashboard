# Personas — Indonesia KEK Power Competitiveness Dashboard

Five primary user personas. Each section covers: who they are, what unique insight they get from this dashboard, their step-by-step journey, what they export, and how they'd cite the tool.

*Updated for Methodology V3.3+ — grid-connected solar model, 9 action flags, BESS bridge-hours + RTE storage model, firm solar coverage metrics, three-point proximity with grid connectivity check, captive power context (coal/nickel/steel/cement), EU CBAM exposure (12 KEKs, 3-signal detection). See [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) for the single authoritative reference.*

**Related:** [DESIGN.md](DESIGN.md) | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

---

## Why This Dashboard Exists

Indonesia is pursuing the most aggressive nickel downstreaming strategy on earth. The country holds the world's largest nickel reserves and is building smelters, battery plants, and industrial parks at pace to capture more of the value chain. This requires massive new electricity — and right now, that electricity comes overwhelmingly from captive coal.

The transition question isn't *should Indonesia decarbonize its industrial zones?* — it's *can Indonesia industrialize and decarbonize simultaneously without sacrificing cost or reliability?*

This dashboard answers that question, site by site, for all 25 KEKs. It is the first tool that maps the intersection of:

- **Solar economics** — LCOE at adjustable financing rates (Global Solar Atlas, ESDM cost catalogue)
- **Grid infrastructure** — substation proximity, capacity, connectivity, upgrade costs (PLN SIMOL, PLN grid lines)
- **Captive power exposure** — coal plants, nickel smelters, steel mills, and cement plants within 50km, subject to Perpres 112/2022 phase-out (GEM GCPT, CGSP Nickel Tracker, GEM Steel/Cement Trackers)
- **EU CBAM exposure** — 12 KEKs with CBAM-liable products (iron/steel, aluminium, fertilizer, cement); emission intensity, cost trajectory 2026-2034, RE savings quantified
- **Industrial demand** — estimated 2030 electricity demand by KEK type and area
- **Policy pipeline** — RUPTL planned additions by region and year, GEAS solar allocations
- **Regional grid cost** — BPP (PLN's actual cost of supply) and I-4 industrial tariff by grid region

No single dataset tells this story. IRENA publishes country-level LCOE ranges. Global Solar Atlas shows radiation but not economics or grid context. RUPTL is a raw PDF. The GEM coal tracker maps plants but not their solar replacement potential. The value is the *cross* — six datasets joined at KEK level with adjustable assumptions, producing 9 action flags that are not labels but specific policy recommendations.

At the current default assumptions, 7 of 25 KEKs flip to solar-competitive under concessional finance (8% WACC). Four more are within 20% of grid parity. The remaining gaps are specific and nameable: a substation upgrade here, a transmission line there, a RUPTL acceleration somewhere else. Each action flag tells you exactly what needs to happen.

---

## Table of Contents

- [Readiness Summary](#readiness-summary)
- [Gap Priority](#gap-priority)
- [Persona 1: Energy Economist](#persona-1-energy-economist) — multilateral development bank analyst (ADB, IFC)
- [Persona 2: DFI Infrastructure Investor](#persona-2-dfi-infrastructure-investor) — grid infrastructure fund analyst (ADB, AIIB, World Bank)
- [Persona 3: Policy Maker](#persona-3-policy-maker) — BKPM/KESDM official or energy think-tank adviser *(primary persona)*
- [Persona 4: IPP / Solar Developer](#persona-4-ipp--solar-developer) — solar IPP (ACEN, Vena Energy) selling to PLN via PPA
- [Persona 5: Industrial Investor / KEK Tenant](#persona-5-industrial-investor--kek-tenant) — factory or smelter operator choosing which KEK to locate in

---

## Readiness Summary

*Last assessed: 2026-04-13 (V3.3 physics model fixes: bridge-hours BESS, round-trip efficiency, firm solar coverage). Re-assess after each major pipeline change.*

| Persona | Score | Status | Top blocking gap |
|---------|-------|--------|-----------------|
| Energy Economist | **85%** | Full WACC spectrum (4-20%), carbon breakeven, BPP sourced, V3.3 physically grounded BESS costs (bridge-hours + RTE), firm solar coverage metric | Grid emission factor is 2019 vintage; CAPEX from ESDM catalogue (not market data) |
| DFI Infrastructure Investor | **85%** | V3.1 grid connectivity, capacity traffic light, transmission cost; V3.2 `grid_investment_needed_usd`; V3.3 honest storage economics | Panel degradation not in LCOE (~6-7% understatement) |
| Policy Maker *(primary)* | **85%** | 9 action flags; V3.3 firm solar coverage shows daytime-direct vs storage-dependent demand split; honest BESS costs for 24/7 industrial loads | `reliability_req` is type-based proxy, not PLN SAIDI/SAIFI |
| IPP / Solar Developer | **85%** | Buildability + resource screening solid; V3.3 bridge-hours BESS sizing + RTE makes `lcoe_with_battery` credible for project finance | Power factor not in capacity assessment (~10-15% overstatement, rarely changes traffic light) |
| Industrial Investor / KEK Tenant | **65%** | I-4 tariff + BPP (FY2020) available; V3.1 grid infrastructure quality signals (capacity assessment, connectivity) | BPP is FY2020 vintage; no PLN SAIDI/SAIFI data |

---

## Gap Priority

Ranked by impact across personas × implementation effort. See each persona's `### Data gaps` section for full detail.

**V2 gaps** are new items introduced by the grid-connected solar pivot. **V1 gaps** are carried forward from the original model.

| Priority | Gap | Personas affected | Effort |
|----------|-----|------------------|--------|
| 🟠 4 | **BPP data freshness** — regional BPP sourced from Kepmen ESDM 169/2021 (FY2020 vintage). More recent PLN Statistik 2024 data would strengthen procurement economics. | P1, P3, P4, P5 | Medium — external data, not code |
| 🟠 5 | **Grid emission factor update** — KESDM 2019 → IEA SEA 2024; affects `carbon_breakeven_usd_tco2` (7 years old) | P1, P3 | Low code / medium research |
| ✅ DONE | **Wind LCOE per KEK** — onshore wind fully implemented (Global Wind Atlas v3, ESDM TECH_WIND_ONSHORE). `best_re_technology` selects cheaper of solar vs wind. | P3 | Done |
| 🟡 7 | **KEK operational status enrichment** — distinguish operating (tenants present) vs. greenfield | P4 | Medium — BKPM/KEK management data required |
| 🟢 8 | **Road proximity (Layer 3a)** — construction access cost; OSM PBF processing | P2, P4 | High effort |
| 🟢 9 | **Flood hazard (Layer 2d)** — BNPB portal inaccessible; low incremental value over slope layer | P2 | High effort / blocked |
| ✅ DONE | **`grid_integration_category` pipeline** — V2: three-point proximity. V3.1: geometric grid line connectivity check (1,595 PLN lines), substation capacity utilization, `invest_transmission` / `invest_substation` split flags, transmission cost model. | P2, P3, P4, P5 | Done (V3.1) |
| ✅ DONE | **`solar_vs_bpp_gap_pct`** — solar LCOE vs. regional BPP gap. BPP data now sourced (Kepmen ESDM 169/2021). Gap computed in scorecard. | P1, P3, P4 | Done |
| ✅ DONE | **`dist_solar_to_nearest_substation_km`** — distance from best buildable solar site to nearest PLN substation. | P2, P4 | Done (V2) |
| ✅ DONE | **Transmission lease fee in all-in LCOE** — deprecated in V2 (transmission is PLN's system cost, reflected in BPP). | — | Done / deprecated |
| ✅ DONE | **`project_viable` boolean** — in `fct_kek_scorecard`; V2 splits threshold. | P2, P4 | Done |
| ✅ DONE | **WACC expansion 4–20%** — `WACC_VALUES` now `[4, 6, 8, 10, 12, 14, 16, 18, 20]`; 450 rows in `fct_lcoe` | P1 | Done |

---

## Persona 1: Energy Economist

**Role:** Economic analyst, multilateral development bank (ADB, IFC, World Bank)
**Context:** Preparing a country energy competitiveness assessment or a renewable energy policy brief. Needs to compare solar LCOE against grid cost across many sites simultaneously and quantify the carbon arbitrage opportunity. Works in Excel and PowerPoint; exports data for colleagues.
**Primary question:** *At our fund's hurdle rate, which KEKs already make economic sense for solar — and what policy change would unlock the others?*

### What only this dashboard shows them

This is the first site-level evidence base showing that concessional finance directly changes outcomes for Indonesian industrial zones. Move the WACC slider from 10% to 8% and watch 7 of 25 KEKs flip to solar-competitive. That number *is* the DFI lending program's impact, quantified, at site level, with transparent assumptions anyone can reproduce. The carbon breakeven column ($X/tCO2 per KEK) sizes the carbon pricing opportunity — where even modest pricing ($10-15/tCO2) closes the gap. IRENA publishes country-level LCOE ranges for Indonesia. This shows it for each of 25 industrial zones, at 9 financing rates, with a CSV export that drops straight into an investment memo annex. No other public tool does this.

### Readiness — 85%

**What works:**
- Full LCOE bands (low/mid/high) at WACC 4/6/8/10/12/14/16/18/20% — full concessional-to-equity spectrum; the 4-6% DFI policy argument is directly modelable
- `carbon_breakeven_usd_tco2` populated for all 25 KEKs — carbon finance desk can use this directly
- `green_share_geas` and GEAS allocation methodology complete
- Provisional flags (`is_cf_provisional`, `is_capex_provisional`) so the economist can caveat outputs
- V3 model uses realistic grid-connected solar cost structure with BESS storage model — more credible for policy briefs than the V1 private gen-tie model
- `bpp_usd_mwh` sourced (Kepmen ESDM 169/2021, FY2020) for all 7 grid regions. Java-Bali ~$57/MWh, Papua ~$133/MWh
- `solar_vs_bpp_gap_pct` computed as a first-class metric — shows where solar undercuts PLN's cost of supply
- Wind LCOE computed per KEK; `best_re_technology` selects cheaper of solar vs wind
- ✅ V3.3: BESS costs now physically grounded — 14h bridge-hours for high-reliability loads (not the old 2h default), with 87% round-trip efficiency. An energy economist reviewing `lcoe_with_battery_usd_mwh` can defend the storage cost estimate to peer reviewers.
- ✅ V3.3: `firm_solar_coverage_pct` alongside `solar_supply_coverage_pct` — the first is daytime-direct, the second is total annual. The distinction is the core temporal mismatch that MacKay (Ch. 26) highlights.

**What's missing:**
- **Grid emission factor is 2019 vintage** — `carbon_breakeven_usd_tco2` uses KESDM data now 7 years old (Gap priority 5)
- **BPP is FY2020 vintage** — Kepmen ESDM 169/2021 data sourced, but more recent PLN Statistik 2024 values would be preferable (Gap priority 4)
- **CAPEX from ESDM catalogue** — $960/kW may be +/-15-20% from current Indonesian EPC market pricing
- **Panel degradation not in LCOE** — ~6-7% understatement; standard IEA/IRENA simplification but should be noted in economic analysis

### Key data needs

- `lcoe_mid_wacc10_usd_mwh` — baseline LCOE at 10% WACC
- `solar_competitive_gap_wacc10_pct` — how far from grid parity (positive = solar more expensive)
- `solar_vs_bpp_gap_pct` — is solar cheaper than PLN's cost of supply? If yes, PLN has economic incentive to procure
- `solar_now_at_wacc8` — does the KEK flip to competitive under DFI concessional financing?
- `carbon_breakeven_usd_tco2` — carbon price at which solar becomes cost-competitive (useful for carbon finance desk)
- `green_share_geas_2030_pct` — how much of this KEK's 2030 demand could GEAS-allocated solar cover?

### User journey

1. **Land on Overview Map** — scan which KEKs are green (`solar_now`) vs. red. Note geographic clustering (Java manufacturing belt vs. eastern islands).
2. **Open Quadrant Chart** — set WACC radio to 10% (standard hurdle rate). Read which KEKs sit in the "Solar now" quadrant vs. "Grid first".
3. **Switch WACC to 8%** — observe which KEKs shift into "Solar now". These are the concessional-finance flip cases — the core policy argument.
4. **Adjust Assumptions Panel** — slide the competitive-gap threshold to 20% to see all KEKs within striking distance. Note grid integration categories.
5. **Open Ranked Table** — sort by `solar_competitive_gap_wacc10_pct` ascending. Add `carbon_breakeven_usd_tco2` column to identify carbon finance candidates.
6. **Export CSV** — download `fct_kek_scorecard` for the economic analysis annex.
7. **Drill into 2–3 KEK Scorecards** — verify PVOUT source, confirm `is_capex_provisional` flag, note `grid_emission_factor_t_co2_mwh` for carbon math. Review grid-connected solar LCOE (V2 realistic cost structure).
8. **Cite in report** — reference the GitHub Release version tag for reproducibility.

### What they export
Ranked table CSV → paste into Excel economic comparison table. Carbon breakeven column → input to carbon finance sensitivity model.

### What they'd cite
> "Source: KEK Power Competitiveness Dashboard v3.1 (github.com/.../releases/tag/v3.1). LCOE computed using ESDM Technology Catalogue 2023 CAPEX ($960/kW), grid cost from Permen ESDM 7/2024 I-4/TT tariff ($63.08/MWh) and BPP Pembangkitan (Kepmen ESDM 169/2021), PVOUT from Global Solar Atlas v2. Grid-connected solar model per METHODOLOGY_CONSOLIDATED.md."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| ~~`bpp_usd_mwh` is null~~ | BPP (PLN cost of supply) is 15-35% higher than the I-4/TT tariff. An economist needs both: tariff and BPP. | ✅ Built — BPP sourced from Kepmen ESDM 169/2021 (FY2020). $57/MWh (Java-Bali) to $133/MWh (Papua). |
| ~~`solar_vs_bpp_gap_pct` not yet computed~~ | Shows where solar LCOE undercuts PLN's cost of supply. | ✅ Built — computed in scorecard as first-class column. |
| BPP data is FY2020 vintage | Kepmen ESDM 169/2021 data is 6 years old. More recent PLN Statistik 2024 values may differ. | ⚠️ Partial — FY2020 data available, more recent data desirable. |
| Grid emission factor is 2019 vintage | `grid_emission_factor_t_co2_mwh` (KESDM Tier 2 OM 2019) is 7 years old. `carbon_breakeven_usd_tco2` inherits this staleness. | Deferred — update to 2023 KESDM or IEA SEA 2024 data. |
| ~~WACC range limited to 8/10/12%~~ | Concessional DFI financing at 4-6% and equity at 14-20% were not modelable. | ✅ Built — full concessional-to-equity spectrum available. |
| CAPEX from ESDM catalogue, not Indonesia market data | ESDM 2023 catalogue value ($960/kW) may be +/-15-20% from current Indonesian EPC market pricing. | Deferred — source 2023-2024 Indonesia solar EPC tender data. |

---

## Persona 2: DFI Infrastructure Investor

**Role:** Infrastructure investment analyst, development finance institution (ADB, AIIB, World Bank/IFC) or green infrastructure fund (Climate Fund Managers, OPIC/DFC)
**Context:** Identifying where grid infrastructure investment unlocks solar potential at Indonesian industrial zones. DFIs regularly finance transmission lines, substations, and grid reinforcement in developing countries. This persona invests in the **grid** that connects solar supply to industrial demand — not in solar projects directly.
**Primary question:** *Where does grid investment unlock the most solar potential per infrastructure dollar — and what instrument (concessional loan, viability gap funding, blended finance) fits each case?*

### What only this dashboard shows them

The biggest bottleneck to clean industrial power in Indonesia isn't solar economics — it's grid infrastructure. This dashboard shows exactly where the bottleneck is and what it costs to fix. Not "invest in Indonesian grid" — but specifically: "this KEK needs a transmission line from substation X, Y km away, costing ~$Z/kW, unlocking W MWp of solar that undercuts PLN's cost of supply by N%." The three-point proximity model (solar site → substation → KEK) with geometric connectivity check and capacity traffic light provides the kind of infrastructure gap specificity that normally requires a pre-feasibility study. A DFI can filter to `invest_transmission` and `invest_substation` KEKs, rank by solar potential per infrastructure dollar, and walk into a board meeting with a ranked grid investment pipeline. No other tool combines solar resource, grid topology, substation capacity, and industrial demand at this resolution.

**V2 note:** This persona was fundamentally reframed from V1. The V1 "DFI Investor" screened captive solar projects with private gen-tie infrastructure — an approach with no global precedent at 50km scale. V2 reframes the DFI as an infrastructure investor, which aligns with how DFIs actually operate in the power sector.

### Readiness — 85%

**What works:**
- Full 4-layer buildability filter: `buildable_area_ha`, `max_captive_capacity_mwp`, `buildability_constraint` all populated for all 25 KEKs
- `dist_to_nearest_substation_km` and `nearest_substation_capacity_mva` (19/25 KEKs) — KEK-side grid data available
- Solar resource data (`pvout_buildable_best_50km`) solid for screening
- `demand_mwh_2030` provides relative demand ranking for investment prioritization
- ✅ V3.1: `grid_integration_category` built — classifies `within_boundary` / `grid_ready` / `invest_substation` / `invest_transmission` / `grid_first`
- ✅ V3.1: `dist_solar_to_nearest_substation_km` computed — solar-side distance for grid investment sizing
- ✅ V3.1: Geometric grid line connectivity check (1,595 PLN transmission lines) + PLN region fallback
- ✅ V3.1: Substation capacity traffic light (`capacity_assessment`: green/yellow/red/unknown) with `available_capacity_mva`
- ✅ V3.1: `transmission_cost_per_kw` — inter-substation new line cost estimate when connectivity is missing
- ✅ V3.2: `grid_investment_needed_usd` — aggregate grid infrastructure cost per KEK ($8M to $2.4B). Surfaced in DataTable and ScoreDrawer.
- ✅ V3.3: Honest BESS economics with bridge-hours (14h) and round-trip efficiency (87%). `lcoe_with_battery_usd_mwh` is now credible for DFI investment committee presentations.

**What's missing:**
- **BPP partially sourced** — regional BPP from Kepmen ESDM 169/2021 (FY2020 vintage). More recent PLN Statistik 2024 data would strengthen the procurement economics case.
- **Panel degradation not in LCOE** — ~6-7% understatement; standard for screening but should be flagged for detailed investment cases.

### Key data needs

- `grid_integration_category` — primary decision variable: `within_boundary` / `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first`
- `dist_solar_to_nearest_substation_km` — infrastructure gap metric: how far from best solar site to nearest grid injection point
- `grid_investment_needed_usd` — order-of-magnitude investment estimate (derivable from `transmission_cost_per_kw x solar_mwp x 1000`)
- `solar_capacity_unlocked_mwp` — how much solar capacity the grid investment would enable (reuse `max_captive_capacity_mwp`)
- `demand_mwh_2030` — is there industrial demand to justify grid investment at this KEK?
- `nearest_substation_capacity_mva` — can the existing substation absorb new solar generation? (V3.1: `capacity_assessment` traffic light)
- `solar_vs_bpp_gap_pct` — does solar reduce PLN's cost of supply? Stronger gap = stronger investment case

### User journey

1. **Open dashboard** — map color-coded by `grid_integration_category`. Immediately see which KEKs are `grid_ready` (no investment needed), `invest_transmission`/`invest_substation` (targeted investment opportunity), or `grid_first` (major investment needed).
2. **Filter to `invest_transmission` and `invest_substation` categories** — these are the DFI opportunity set: KEKs where solar resource exists, industrial demand exists, but specific grid infrastructure is the bottleneck. V3 tells you exactly what's missing (transmission line vs. substation).
3. **Sort by solar ROI per infrastructure dollar** — rank investment KEKs by `solar_capacity_unlocked_mwp / grid_investment_needed_usd`. Highest ratio = most efficient use of DFI capital.
4. **Cross-reference demand** — prioritize KEKs where `demand_mwh_2030` is high. Grid investment at a low-demand KEK may not be justified.
5. **Drill into top candidates** — check solar resource quality (`pvout_buildable_best_50km`), RUPTL alignment (`plan_late` flag), substation capacity (`nearest_substation_capacity_mva`).
6. **Assess BPP economics** — where `solar_vs_bpp_gap_pct` is negative (solar cheaper than PLN's cost), the investment case is self-supporting: grid investment enables solar that reduces PLN's operating cost.
7. **Export ranked list** — CSV with grid integration category, investment estimate, and solar potential for internal investment committee review.

### Investment instruments

| Instrument | When applicable | Example |
|---|---|---|
| Concessional loan to PLN | Transmission line or substation near an `invest_transmission`/`invest_substation` KEK | ADB loan for Sulawesi grid reinforcement enabling solar procurement |
| Viability gap funding | Grid cost exceeds PLN's recoverable tariff revenue | IFC viability gap for remote substation where industrial tariff alone doesn't cover grid CAPEX |
| Blended finance | DFI funds grid, private IPP funds solar, PLN operates connection | AIIB + private IPP co-investment at a Java industrial KEK |
| Green bond with DFI credit enhancement | Large-scale grid modernization program across multiple KEKs | World Bank-backed green bond for PLN's renewable-enabling grid program |

### What they export
Ranked CSV of `invest_transmission`/`invest_substation` KEKs with investment estimate, solar potential, and demand data for investment committee screening memo. GeoJSON for spatial analysis.

### What they'd cite
> "Grid infrastructure gap analysis: KEK Power Competitiveness Dashboard v3.1. Solar resource from Global Solar Atlas v2, substation locations from PLN SIMOL dataset, grid connectivity from PLN grid lines GeoJSON (1,595 lines), grid integration categories per METHODOLOGY_CONSOLIDATED.md three-point proximity analysis."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| ~~`grid_integration_category` not yet built~~ | ~~The primary decision variable.~~ | ✅ Built (V3.1) — classifies `invest_substation`, `invest_transmission`, `grid_first`. Geometric grid line connectivity + capacity utilization check. |
| ~~`dist_solar_to_nearest_substation_km` not yet computed~~ | ~~Required for grid investment sizing.~~ | ✅ Built (V2) — solar-to-substation distance computed for all KEKs with solar coords. |
| ~~`grid_investment_needed_usd` not yet a first-class column~~ | ~~Order-of-magnitude total investment estimate.~~ | ✅ Built — precomputed in pipeline, surfaced as sortable DataTable column ($XM format, color-coded) + ScoreDrawer Overview and Grid tabs. 18/25 KEKs have values ($8M to $2.4B). Also in CSV export. |
| BPP data vintage | Regional BPP from Kepmen ESDM 169/2021 (FY2020). More recent PLN Statistik 2024 data would strengthen procurement economics. | ⚠️ Partial — FY2020 data available, more recent data desirable. |
| Substation capacity partial | 6 of 25 KEKs have null `nearest_substation_capacity_mva`. V3.1 `capacity_assessment` shows `unknown` for these. | Available with gaps — 19/25 KEKs have data. |
| Flood hazard layer (Layer 2d) missing | Coastal sites may have buildable land on flood-prone ground. | Deferred — BNPB portal inaccessible. |

---

## Persona 3: Policy Maker

**Role:** Senior official, BKPM (Investment Coordinating Board) or KESDM (Ministry of Energy), or technical adviser at an energy think-tank (IESR, Rocky Mountain Institute Indonesia)
**Context:** Preparing input for a RUPTL review, a KEK electricity regulation update, or a green industrial park policy. V2 makes this persona the **primary audience** because the dashboard now directly answers: "Where should grid infrastructure investment go to unlock cheap solar for industrial zones?"
**Primary question:** *Where should grid infrastructure investment be prioritized to unlock solar potential at KEKs — and which KEKs are already grid-ready for solar procurement?*

### What only this dashboard shows them

No other public tool crosses solar economics, grid topology, captive coal exposure, RUPTL pipeline timing, and nickel smelter locations at KEK level. A KESDM official can see in one screen: "Galang Batang has a 2,880 MW captive coal plant within 50km. Solar is 34% above grid cost today, but at 8% WACC the gap narrows to single digits. The substation needs capacity, and RUPTL solar additions for this region are mostly post-2030 — accelerate the pipeline." The 9 action flags are not labels — they are the policy playbook. Each one names the specific intervention: build a substation, extend a transmission line, accelerate RUPTL, invest in battery storage. The dashboard maps exactly where Indonesia's industrial ambitions and decarbonization goals align, and where they need a specific policy lever to close the gap. A policymaker preparing input for a RUPTL review or KEK electricity regulation update gets site-by-site, evidence-based recommendations that would take weeks to assemble manually.

### Readiness — 85%

**What works:**
- Action flags now include 9 categories: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive`, `no_solar_resource`. V3 split `invest_grid` into actionable sub-flags.
- Full RUPTL pipeline context: `pre2030_solar_mw`, `post2030_share`, `grid_upgrade_pre2030`, `ruptl_summary`
- `green_share_geas` quantifies GEAS allocation as a policy lever
- `carbon_breakeven_usd_tco2` supports carbon market design arguments
- ✅ V3.1: `grid_integration_category` built with geometric grid line connectivity check and capacity utilization assessment
- ✅ V3.1: Substation capacity traffic light helps identify where grid reinforcement is needed
- ✅ V3.1: `transmission_cost_per_kw` quantifies inter-substation infrastructure gap
- ✅ V3.3: `firm_solar_coverage_pct` and `storage_gap_pct` show what fraction of demand solar can serve directly (daytime) vs what requires storage (nighttime ~58%). Grounds the "100% RE coverage" claim in physical reality.
- ✅ V3.3: BESS costs now reflect bridge-hours sizing (14h for 24/7 industrial loads) with round-trip efficiency. `invest_battery` flag carries honest economics, not understated 2h sizing.

**Note on technology scope:** Wind LCOE is now included (Global Wind Atlas v3, ESDM TECH_WIND_ONSHORE parameters). `best_re_technology` selects the cheaper of solar vs wind per KEK. Geothermal remains deferred. A KESDM adviser reviewing Sulawesi KEKs (which have known geothermal resources) should note that geothermal is not yet in the model.

**What's missing:**
- **Geothermal not yet modeled** — Sulawesi/Maluku KEKs with known geothermal resources may appear less favorable than they are
- **`reliability_req` is hardcoded by KEK type**, not sourced from PLN SAIDI/SAIFI data — weakening credibility with KESDM technical reviewers
- **`demand_mwh_2030` is a proxy** — GEAS `green_share_geas` inherits area x intensity uncertainty

### Key data needs

- `grid_integration_category` — where does each KEK sit: `within_boundary` / `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first`
- `invest_transmission` / `invest_substation` action flags — which KEKs need what specific grid investment to unlock solar
- `solar_vs_bpp_gap_pct` — where does solar reduce PLN's cost of supply
- `plan_late` — is the RUPTL pipeline arriving after 2030? (flags KEKs that need grid acceleration)
- `green_share_geas_2030_pct` — share of 2030 demand potentially met by GEAS-allocated solar
- `ruptl_re_base_2030_mw` — PLN's own RE pipeline for this region by 2030
- `solar_competitive_gap_wacc10_pct` — economic gap at market WACC
- `solar_now_at_wacc8` — does concessional finance (8%) close the gap?
- `carbon_breakeven_usd_tco2` — carbon price needed for solar competitiveness (relevant to carbon market design)

### User journey

1. **Open dashboard** — map shows `grid_integration_category` (color-coded). Immediately see which KEKs are `grid_ready` vs. `invest_transmission`/`invest_substation` vs. `grid_first`.
2. **Identify `invest_transmission` and `invest_substation` KEKs** — V3 tells you exactly what's missing. Transmission = KEK far from grid; substation = solar far from grid. The policy question: should RUPTL be adjusted to prioritize these locations?
3. **Cross-reference with RUPTL pipeline** — are grid upgrades already planned? Check `plan_late` flag: if grid improvement is coming but after 2030, recommend RUPTL acceleration.
4. **Prioritize** — sort investment KEKs by: solar resource (strong) + demand (high) + grid gap (small = cheapest to fix). These are the highest-impact policy targets.
5. **Check `solar_vs_bpp_gap_pct`** — where solar is cheaper than PLN's cost of supply, the economic case for enabling procurement is self-evident. Use this in budget planning discussions with PLN.
6. **Adjust Assumptions Panel** — set WACC to 8%. Count how many KEKs flip to `solar_now`. This is the policy case for concessional finance or WACC de-risking instruments.
7. **Export CSV** — download ranked table with `grid_integration_category`, action flags, `plan_late`, `green_share_geas_2030_pct` for RUPTL review or KEK development strategy presentation.
8. **Cite in policy brief** — reference data sources and methodology for credibility with technical reviewers.

### Policy levers the dashboard illuminates

- Where to prioritize PLN grid expansion (RUPTL influence)
- Where to direct DFI infrastructure funding
- Which KEKs are `grid_ready` for solar IPP development today
- Where carbon pricing would tip the economics
- Where concessional finance (lower WACC) closes the competitiveness gap

### What they export
Ranked table CSV filtered by `grid_integration_category`. Screenshot of three-point proximity map for presentation slides. Green share column for GEAS policy memo.

### What they'd cite
> "KEK-level solar and wind competitiveness and grid integration analysis, KEK Power Competitiveness Dashboard v3.1. Grid cost: Permen ESDM 7/2024 + BPP Pembangkitan (Kepmen ESDM 169/2021). RUPTL pipeline: RUPTL PLN 2025-2034. Grid integration methodology: METHODOLOGY_CONSOLIDATED.md."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| ~~`grid_integration_category` not yet built~~ | ~~The primary decision variable for V2.~~ | ✅ Built (V3.1) — with geometric grid line connectivity, capacity utilization, `invest_transmission` / `invest_substation` split. |
| ~~`solar_vs_bpp_gap_pct` not yet computed~~ | ~~Critical for PLN engagement.~~ | ✅ Built — BPP sourced (Kepmen ESDM 169/2021), gap computed in scorecard. |
| `reliability_req` is hardcoded by KEK type | `invest_battery` flag depends on assumed reliability scores, not actual PLN SAIDI/SAIFI data. Weakens credibility with KESDM technical reviewers. | Deferred — PLN publishes SAIDI/SAIFI by grid system but not by KEK; requires manual mapping. |
| `demand_mwh_2030` is area x intensity proxy | GEAS `green_share_geas` is allocated against proxy demand, not actual tenant consumption. Policy allocation recommendations inherit this uncertainty. | Deferred — requires tenant surveys or KESDM KEK energy consumption registry. |
| ~~No wind resource layer~~ | ~~Model was solar-only.~~ | ✅ Built — wind LCOE computed per KEK (Global Wind Atlas v3, ESDM TECH_WIND_ONSHORE). `best_re_technology` selects cheaper of solar vs wind. |
| No geothermal resource layer | Sulawesi KEKs with known geothermal resources may appear less favorable. A policy maker advising on Sulawesi needs the full clean energy picture. | Deferred — geothermal requires separate data source and methodology. |
| Carbon price trajectory not modelled | `carbon_breakeven_usd_tco2` is a static threshold. No link to Indonesia's ETS trajectory. | Deferred — requires IDR carbon price forecast data. |
| GEAS allocation is a modelled approximation | Real GEAS depends on PLN tender design, offtake eligibility, and transmission access rights. | Fundamental limitation — label clearly in dashboard. |

---

## Persona 4: IPP / Solar Developer

**Role:** Business development manager or country director, solar IPP developer (ACEN, Vena Energy, SolarEdge Indonesia, local developer)
**Context:** Building a pipeline of solar projects that sell to PLN via PPA. In Indonesia, PLN controls the procurement process — IPPs do not independently choose where to build. PLN issues tenders for specific regions based on RUPTL planning, negotiates PPAs, and allocates grid capacity. The dashboard serves IPPs in two ways:

1. **Pre-positioning:** Identifying regions where solar economics are strongest, so the IPP can prepare (secure land options, complete pre-feasibility studies) ahead of PLN procurement tenders.
2. **Advocacy:** Building the economic case for PLN to prioritize solar procurement in specific regions. An IPP can use the dashboard's data to support proposals showing that solar in a given grid region would reduce BPP — aligning the IPP's commercial interest with PLN's cost-reduction mandate.

**Primary question:** *Where are the strongest solar-to-BPP economics — and where should we pre-position for PLN procurement or advocate for solar prioritization?*

### What only this dashboard shows them

The `solar_vs_bpp_gap` reveals where PLN *saves money* by procuring solar — not just where solar is cheap, but where it undercuts PLN's actual cost of supply (BPP), which is often 15-35% higher than the subsidized industrial tariff. Where that gap is negative, the IPP's pitch to PLN writes itself: "procure solar here and your generation cost drops." Combined with `grid_integration_category` (is the substation ready or does the IPP need to factor in grid delay?), `max_captive_capacity_mwp` (how big can the project be?), and `capacity_assessment` (can the local grid absorb the output?), this is a pre-feasibility screening tool that narrows 25 KEKs to 3-5 viable target regions before expensive site visits and land acquisition. The buildability data (slope, forest, peat, land cover filters) tells the IPP what percentage of nearby land is actually buildable — saving months of field screening. No other tool combines solar resource quality, grid injection readiness, BPP economics, and land buildability at this resolution.

**V2 note:** V1 framed the IPP as selling captive power directly to KEK tenants via PPA. V2 reframes the offtake model: IPP sells to PLN, PLN delivers to KEK tenants. This is the standard Indonesian model.

### Readiness — 85%

**What works:**
- Full buildability screening: `max_captive_capacity_mwp`, `buildable_area_ha`, `pvout_buildable_best_50km` all populated
- `nearest_substation_capacity_mva` available for 19/25 KEKs — grid absorption signal. V3.1 adds `capacity_assessment` traffic light.
- `demand_mwh_2030` for relative site ranking (not PPA sizing)
- `project_viable` boolean in scorecard
- `solar_vs_bpp_gap_pct` computed — shows where solar undercuts PLN's cost of supply, the core argument for procurement prioritization
- `dist_solar_to_nearest_substation_km` computed — grid injection distance for 18/25 KEKs with solar site coordinates
- `grid_integration_category` built (V3.1) — `within_boundary` / `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first` with connectivity check and capacity traffic light
- ✅ V3.3: `lcoe_with_battery_usd_mwh` now uses bridge-hours sizing (14h for high-reliability loads) with round-trip efficiency (87%) — credible for project finance screening
- ✅ V3.3: `firm_solar_coverage_pct` shows daytime-direct coverage vs storage-dependent demand — honest metric for PPA sizing

**What's missing:**
- **`demand_mwh_2030` is a proxy** — area x intensity estimate, not actual tenant consumption (fundamental limitation)
- **KEK operational status is coarse** — doesn't distinguish operating KEKs with tenants from greenfield development (Gap priority 7)
- **Panel degradation not in LCOE** — ~6-7% understatement; standard for screening models but IPPs doing detailed project finance should adjust

### Key data needs

- `pvout_buildable_best_50km` — best solar yield in buildable land
- `solar_vs_bpp_gap_pct` — is solar cheaper than PLN's cost of supply? Negative = PLN saves money by procuring solar
- `dist_solar_to_nearest_substation_km` — how far from best solar site to grid injection point
- `grid_integration_category` — `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first`
- `nearest_substation_capacity_mva` — can the local grid absorb the project's output? (`capacity_assessment` traffic light)
- `max_captive_capacity_mwp` — maximum buildable capacity
- `demand_mwh_2030` — is there sufficient industrial demand to justify solar procurement in this region?
- `buildability_constraint` — land constraint type affects site development complexity

### User journey

1. **Identify regions with strong solar resource** — sort by `pvout_buildable_best_50km`. Same starting point as V1.
2. **Check grid readiness** — filter to `grid_ready` or `solar_now`. Is there a substation near the best solar site with sufficient capacity? These regions are ready for solar procurement.
3. **Build the economic case** — `solar_vs_bpp_gap_pct` shows where solar would reduce PLN's cost of supply. This is the core argument for procurement prioritization: "if PLN procures solar here, it saves money."
4. **Review substation capacity** — `nearest_substation_capacity_mva`: can the local grid absorb the planned project output, or does the proposal need to include grid reinforcement?
5. **Assess buildability constraints** — `slope` and `unconstrained` are low-risk. `agriculture` means land acquisition negotiation. `peat` or `kawasan_hutan` are high-risk.
6. **Drill into top 3–5 KEK Scorecards** — review PVOUT map, grid-connected solar LCOE bands, demand profile. Download for BD deck or PLN engagement materials.
7. **Export CSV** — top 10 regions with solar resource, grid readiness, and BPP economics for BD pipeline tracker or PLN/ESDM engagement.

**The IPP and policymaker journeys are complementary:** the policymaker uses the dashboard to identify where solar procurement should be enabled; the IPP uses it to prepare for and advocate toward those same procurement decisions.

**Note:** IPP developers typically know their own EPC costs better than the ESDM catalogue ($960/kW). The dashboard shows LCOE at 3 CAPEX bands (low/mid/high = $840/$960/$1,080/kW, ±12.5%). Custom CAPEX input is planned — until then, an IPP can use the exported CSV and recompute LCOE in their own financial model using the CF values provided.

### What they export
Ranked table CSV (top 10 sites) for BD pipeline tracker. KEK Scorecard screenshots for PLN engagement deck. GeoJSON for desktop site analysis.

### What they'd cite
> "Solar resource and land buildability: KEK Power Competitiveness Dashboard v3.1. Buildable area uses Kawasan Hutan + peatland + ESA WorldCover + DEM slope/elevation filters. Grid integration analysis per METHODOLOGY_CONSOLIDATED.md. Demand estimates are provisional (area x intensity proxy); field surveys required for PPA sizing."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| ~~`solar_vs_bpp_gap_pct` not yet computed~~ | ~~The primary competitiveness metric for V2.~~ | ✅ Built — BPP sourced, gap computed in scorecard. |
| ~~`dist_solar_to_nearest_substation_km` not yet computed~~ | ~~Grid injection distance.~~ | ✅ Built (V2) — computed for all KEKs with solar coords. |
| ~~`grid_integration_category` not yet built~~ | ~~Replaces V1 `siting_scenario`.~~ | ✅ Built (V3.1) — with connectivity check and capacity traffic light. |
| `demand_mwh_2030` is area × intensity proxy | PPA sizing requires actual tenant electricity consumption. The proxy exists only for relative ranking. | Deferred — requires field surveys or KEK management data. |
| KEK operational status is coarse | `status` field does not distinguish "operating with tenants" from "under development". An IPP needs to know if offtake demand is real. | Deferred — requires KEK management outreach or BKPM tenant occupancy registry. |
| Substation capacity partial | 6 of 25 KEKs have null `nearest_substation_capacity_mva`. V3.1 `capacity_assessment` shows `unknown` for these. | Available with gaps — 19/25 KEKs have data. |

---

## Persona 5: Industrial Investor / KEK Tenant

**Role:** Site selection manager or country director, industrial manufacturer or smelter operator (e.g., nickel processing, petrochemicals, automotive components, data center operator)
**Context:** Deciding which KEK to locate a factory or processing facility in. This persona does **not** build solar — they buy electricity from PLN at the regulated industrial tariff. Their decision is driven by electricity cost, reliability, and increasingly by green energy credentials (ESG requirements from buyers and investors).
**Primary question:** *Which KEK offers the lowest risk for electricity cost and reliability over the next 10–15 years — and which ones will have the greenest power mix?*

### What only this dashboard shows them

All KEKs pay the same PLN industrial tariff today — the differentiation is *risk*. This dashboard exposes the subsidy gap (BPP vs. tariff) by region. In regions like Papua, PLN's actual cost of supply is $133/MWh but the tariff is $63/MWh — a $70/MWh subsidy that is a future tariff hike waiting to happen. KEKs in regions where solar could lower the BPP are safer 15-year bets for electricity cost stability. For ESG-sensitive operators — nickel processors selling to EV battery supply chains, data centers with carbon commitments — the `green_share_geas` metric shows which KEKs will have the greenest power mix by 2030. The captive power context shows existing coal plants and nickel smelters within 50km, many subject to Perpres 112/2022 phase-out by 2050 — a regulatory risk (and transition opportunity) for co-located industry. No other tool maps subsidy exposure, green energy trajectory, and captive power regulatory risk at KEK level for industrial site selection.

**V2 note:** This persona was implicit in V1 but not separately modeled. They are the demand side of the equation — the factories and smelters that create the industrial electricity demand the dashboard quantifies.

**Honest limitation:** The PLN I-4 industrial tariff is **nationally uniform** within the same voltage category. This means the dashboard cannot differentiate KEKs by *current* electricity cost — today, it's the same everywhere. The dashboard's value to this persona lies in areas where KEKs **do** differ: subsidy exposure risk, grid reliability trajectory, and future green energy access.

**Forward-looking note on wheeling:** If PLN ever adopts grid wheeling for industrial consumers (legally authorized but rejected in practice), KEKs near strong solar potential and `grid_ready` substations would benefit first. This makes `grid_integration_category` a forward-looking site selection criterion, not just an infrastructure gap indicator.

### Readiness — 65%

**What works:**
- PLN I-4 tariff ($63.08/MWh) available as baseline electricity cost
- `bpp_usd_mwh` sourced (Kepmen ESDM 169/2021, FY2020) — reveals subsidy exposure by region. High BPP = high tariff adjustment risk.
- `dist_kek_to_nearest_substation_km` as a proxy for grid connection quality
- `nearest_substation_capacity_mva` for 19/25 KEKs — can PLN's local grid handle industrial-scale load? V3.1 adds `capacity_assessment` traffic light.
- `grid_integration_category` built (V3.1) — proxy for future grid quality. `grid_ready` KEKs near cheap solar are more likely to see infrastructure investment.
- `green_share_geas_2030_pct` — how much of their power will be renewable by 2030
- `plan_late` flag — timeline risk for grid infrastructure arrival
- RUPTL pipeline context for regional grid development trajectory

**What's missing:**
- **BPP is FY2020 vintage** — more recent PLN Statistik 2024 values would strengthen subsidy exposure analysis (Gap priority 🟠 4)
- **No PLN SAIDI/SAIFI data** — actual grid reliability by region is not available. Substation distance, capacity, and `capacity_assessment` are proxies only.
- **KEK operational status is coarse** — doesn't distinguish operating KEKs with tenants from greenfield development

### Key data needs

- `bpp_usd_mwh` — true cost of supply in this grid region. High BPP = high subsidy exposure = tariff adjustment risk
- `grid_integration_category` — proxy for future grid quality and solar integration trajectory
- `green_share_geas_2030_pct` — how much of this KEK's power will be renewable by 2030
- `plan_late` — RUPTL pipeline timeline risk
- `dist_kek_to_nearest_substation_km` — proxy for grid connection quality and outage restoration time
- `nearest_substation_capacity_mva` — can PLN's local grid handle industrial-scale load expansion?
- `grid_cost_usd_mwh` — current I-4 tariff (nationally uniform, but useful as baseline)

### User journey

1. **Start from the baseline:** All KEKs pay the same PLN I-4 tariff today. The differentiation is about **risk and trajectory**, not current price.
2. **Check BPP vs. tariff gap** — KEKs in high-BPP regions are more exposed to future tariff adjustments. PLN's subsidy burden is unsustainable at regions where BPP significantly exceeds the tariff. KEKs where solar could lower the regional BPP are better long-term bets for tariff stability.
3. **Check grid reliability proxies** — `dist_kek_to_nearest_substation_km` and `nearest_substation_capacity_mva`. Continuous-process industries (smelters, chemicals, data centers) cannot tolerate frequent outages. KEKs close to large substations offer better reliability prospects.
4. **Assess green credentials** — ESG-conscious manufacturers and their buyers increasingly require renewable energy sourcing. `grid_ready` KEKs near strong solar resource offer a credible green pathway. Check `green_share_geas_2030_pct` for the regional renewable trajectory.
5. **Check `plan_late` flag** — KEKs where RUPTL grid improvements arrive after 2030 face infrastructure risk. An industrial investor committing to a 15-year facility needs confidence that grid capacity will keep pace.
6. **Export comparison matrix** — CSV with all KEKs ranked by risk factors (BPP gap, substation proximity, green share, plan_late) for site selection decision. Differentiated by risk, not current price.

### What they export
Comparison matrix CSV for site selection team. Screenshots of grid integration map for management presentation.

### What they'd cite
> "KEK electricity infrastructure comparison: KEK Power Competitiveness Dashboard v3.1. Grid cost: Permen ESDM 7/2024 I-4/TT tariff + BPP Pembangkitan (Kepmen ESDM 169/2021). Substation data from PLN SIMOL dataset, grid connectivity from PLN grid lines GeoJSON. Note: current industrial tariff is nationally uniform; differentiation is based on grid infrastructure quality, BPP subsidy exposure, and renewable energy trajectory. Methodology: METHODOLOGY_CONSOLIDATED.md."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| BPP data vintage | BPP from Kepmen ESDM 169/2021 (FY2020). Subsidy exposure analysis uses FY2020 cost of supply, which may differ from current values. | ⚠️ Partial — FY2020 data available, more recent PLN Statistik desirable. |
| ~~`grid_integration_category` not yet built~~ | ~~Proxy for future grid quality.~~ | ✅ Built (V3.1) — with capacity traffic light and connectivity check. 5 categories: `within_boundary`, `grid_ready`, `invest_substation`, `invest_transmission`, `grid_first`. |
| No PLN SAIDI/SAIFI data | Actual grid reliability by region is unavailable. Substation distance and capacity are proxies only. V3.1 `capacity_assessment` traffic light adds a signal but is still a proxy. | Deferred — PLN publishes SAIDI/SAIFI by grid system but not by KEK; requires manual mapping. |
| KEK operational status is coarse | `status` field does not show tenant occupancy or infrastructure readiness. An industrial investor choosing between KEKs needs to know if peers are already operating there. | Deferred — requires BKPM/KEK management data. |
| No logistics or transport cost data | Electricity is one input; transport, labor, and raw material access also matter for site selection. Dashboard covers electricity only. | Out of scope — fundamental limitation. |
| EU CBAM tariff exposure by KEK | Manufacturers in iron/steel, aluminium, fertilizer, and cement face EU carbon border tariffs rising from ~$2/tCO₂ (2026) to ~$88/tCO₂ (2034) as free allocation phases out. Site selection must factor CBAM cost trajectory and RE availability. | ✅ Built (2026-04-14) — 3-signal detection (nickel process, plant counts, business sectors). 12 KEKs exposed. `cbam_cost_2030_usd_per_tonne` + `cbam_savings` quantify RE switching value. ScoreDrawer Industry tab shows full trajectory. |
| Steel/cement plant proximity | Industrial investors choosing manufacturing KEKs need to know existing heavy industry (supply chain, clustering effects, infrastructure sharing). | ✅ Built (2026-04-14) — GEM Steel (7 plants, 2 KEKs matched) and Cement (32 plants, 5 KEKs matched) Trackers. Map overlays + ScoreDrawer Industry tab + table Industry badge column. |
