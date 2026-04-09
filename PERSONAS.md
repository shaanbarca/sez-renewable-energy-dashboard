# Personas — Indonesia KEK Power Competitiveness Dashboard

Five primary user personas. Each section covers: who they are, what they need from the data, their step-by-step journey through the dashboard, what they export, and how they'd cite the tool.

*Updated for Methodology V2 — grid-connected solar model. See [METHODOLOGY_V2.md](docs/METHODOLOGY_V2.md) for full rationale.*

**Related:** [DESIGN.md](DESIGN.md) | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

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

*Last assessed: 2026-04-09 (V2 pivot). Re-assess after each major pipeline change.*

| Persona | Score | Status | Top blocking gap |
|---------|-------|--------|-----------------|
| Energy Economist | **70%** | Full WACC spectrum + carbon breakeven built; V2 adds `solar_vs_bpp_gap_pct` (not yet computed) | `bpp_usd_mwh` null — BPP comparison unavailable; `solar_vs_bpp_gap_pct` not yet in pipeline |
| DFI Infrastructure Investor | **40%** | Fundamentally reframed for V2 — most new metrics not yet built | `grid_integration_category`, `grid_investment_needed_usd`, `dist_solar_to_nearest_substation_km` all unbuilt |
| Policy Maker *(primary)* | **55%** | Action flags + RUPTL solid; V2 elevates this persona but key metrics unbuilt | `grid_integration_category` and `invest_grid` flag not yet in pipeline; solar-only caveat remains |
| IPP / Solar Developer | **65%** | Buildability + resource screening solid; V2 reframes offtake model (PLN PPA) | `solar_vs_bpp_gap_pct` and `dist_solar_to_nearest_substation_km` not yet computed |
| Industrial Investor / KEK Tenant | **50%** | NEW persona — I-4 tariff available but differentiation metrics unbuilt | `bpp_usd_mwh` null; `grid_integration_category` unbuilt; no PLN SAIDI/SAIFI data |

---

## Gap Priority

Ranked by impact across personas × implementation effort. See each persona's `### Data gaps` section for full detail.

**V2 gaps** are new items introduced by the grid-connected solar pivot. **V1 gaps** are carried forward from the original model.

| Priority | Gap | Personas affected | Effort |
|----------|-----|------------------|--------|
| 🔴 1 V2 | **`grid_integration_category` pipeline** — three-point proximity analysis not yet built; requires best solar site coordinates + solar-to-substation distance computation. Unblocks `invest_grid` flag and DFI/policymaker core workflows. | P2, P3, P4, P5 | Medium — pipeline code (V2-B1, V2-B2) |
| 🔴 2 V2 | **`solar_vs_bpp_gap_pct`** — solar LCOE vs. regional BPP gap not yet computed. Critical for PLN procurement economics and IPP advocacy. Blocked by BPP sourcing (gap #4). | P1, P3, P4 | Low code / blocked by BPP data |
| 🔴 3 V2 | **`dist_solar_to_nearest_substation_km`** — distance from best buildable solar site to nearest PLN substation. Requires best solar site lat/lon (V2-B1). | P2, P4 | Medium — pipeline code (V2-B1, V2-B2) |
| 🟠 4 | **BPP data sourcing** — PLN Statistik 2024 regional BPP; `bpp_usd_mwh` column exists but null. Now even more critical: BPP is the denominator for `solar_vs_bpp_gap_pct` and the basis for PLN procurement incentive analysis. | P1, P3, P4, P5 | Medium — external data, not code |
| 🟠 5 | **Grid emission factor update** — KESDM 2019 → IEA SEA 2024; affects `carbon_breakeven_usd_tco2` | P1, P3 | Low code / medium research |
| 🟡 6 | **Wind CF layer for Sulawesi** — fixes misleading `not_competitive` at kek-palu, kek-bitung, kek-morotai | P3 | Medium — new data source + pipeline step |
| 🟡 7 | **KEK operational status enrichment** — distinguish operating (tenants present) vs. greenfield | P4 | Medium — BKPM/KEK management data required |
| 🟢 8 | **Road proximity (Layer 3a)** — construction access cost; OSM PBF processing | P2, P4 | High effort |
| 🟢 9 | **Flood hazard (Layer 2d)** — BNPB portal inaccessible; low incremental value over slope layer | P2 | High effort / blocked |
| ✅ DONE | **Transmission lease fee in all-in LCOE** — deprecated in V2 (transmission is PLN's system cost, reflected in BPP). Was `lcoe_remote_captive_allin_*` with $10/MWh adder. | — | Done / deprecated |
| ✅ DONE | **`project_viable` boolean** — in `fct_kek_scorecard`; V2 splits threshold: 0.5 MWp (within-boundary) / 20 MWp (grid-connected) | P2, P4 | Done / updating for V2 |
| ✅ DONE | **WACC expansion 4–20%** — `WACC_VALUES` now `[4, 6, 8, 10, 12, 14, 16, 18, 20]`; 450 rows in `fct_lcoe` | P1 | Done |

---

## Persona 1: Energy Economist

**Role:** Economic analyst, multilateral development bank (ADB, IFC, World Bank)
**Context:** Preparing a country energy competitiveness assessment or a renewable energy policy brief. Needs to compare solar LCOE against grid cost across many sites simultaneously and quantify the carbon arbitrage opportunity. Works in Excel and PowerPoint; exports data for colleagues.
**Primary question:** *At our fund's hurdle rate, which KEKs already make economic sense for solar — and what policy change would unlock the others?*

### Readiness — 70%

**What works:**
- Full LCOE bands (low/mid/high) at WACC 4/6/8/10/12/14/16/18/20% — full concessional-to-equity spectrum; the 4–6% DFI policy argument is now directly modelable
- `carbon_breakeven_usd_tco2` populated for all 25 KEKs — carbon finance desk can use this directly
- `green_share_geas` and GEAS allocation methodology complete
- Provisional flags (`is_cf_provisional`, `is_capex_provisional`) so the economist can caveat outputs
- V2 model uses realistic grid-connected solar cost structure — more credible for policy briefs than the V1 private gen-tie model

**What's missing:**
- **BPP is null** — grid reference is I-4 tariff ($63.08). PLN's true cost of supply is 15–35% higher at most regions; the LCOE gap vs. BPP (more favourable for solar) can't be shown (Gap priority 🟠 4)
- **`solar_vs_bpp_gap_pct` not yet computed** — V2 elevates this to a first-class metric (is solar cheaper than PLN's cost of supply?), but it's blocked by BPP sourcing (Gap priority 🔴 2)
- **Grid emission factor is 2019 vintage** — `carbon_breakeven_usd_tco2` uses stale KESDM data (Gap priority 🟠 5)

### Key data needs

- `lcoe_mid_wacc10_usd_mwh` — baseline LCOE at 10% WACC
- `solar_competitive_gap_wacc10_pct` — how far from grid parity (positive = solar more expensive)
- `solar_vs_bpp_gap_pct` — is solar cheaper than PLN's cost of supply? If yes, PLN has economic incentive to procure. *(V2 — not yet computed)*
- `solar_now_at_wacc8` — does the KEK flip to competitive under DFI concessional financing?
- `carbon_breakeven_usd_tco2` — carbon price at which solar becomes cost-competitive (useful for carbon finance desk)
- `green_share_geas_2030_pct` — how much of this KEK's 2030 demand could GEAS-allocated solar cover?

### User journey

1. **Land on Overview Map** — scan which KEKs are green (`solar_now`) vs. red. Note geographic clustering (Java manufacturing belt vs. eastern islands).
2. **Open Quadrant Chart** — set WACC radio to 10% (standard hurdle rate). Read which KEKs sit in the "Solar now" quadrant vs. "Grid first".
3. **Switch WACC to 8%** — observe which KEKs shift into "Solar now". These are the concessional-finance flip cases — the core policy argument.
4. **Open Flip Scenario Panel** — slide the competitive-gap threshold to 20% to see all KEKs within striking distance. Note grid integration categories.
5. **Open Ranked Table** — sort by `solar_competitive_gap_wacc10_pct` ascending. Add `carbon_breakeven_usd_tco2` column to identify carbon finance candidates.
6. **Export CSV** — download `fct_kek_scorecard` for the economic analysis annex.
7. **Drill into 2–3 KEK Scorecards** — verify PVOUT source, confirm `is_capex_provisional` flag, note `grid_emission_factor_t_co2_mwh` for carbon math. Review grid-connected solar LCOE (V2 realistic cost structure).
8. **Cite in report** — reference the GitHub Release version tag for reproducibility.

### What they export
Ranked table CSV → paste into Excel economic comparison table. Carbon breakeven column → input to carbon finance sensitivity model.

### What they'd cite
> "Source: KEK Power Competitiveness Dashboard v2.0 (github.com/…/releases/tag/v2.0). LCOE computed using ESDM Technology Catalogue 2023 CAPEX ($960/kW), grid cost from Permen ESDM 7/2024 I-4/TT tariff ($63.08/MWh), PVOUT from Global Solar Atlas v2. Grid-connected solar model per METHODOLOGY_V2.md."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `bpp_usd_mwh` is null | BPP (PLN cost of supply) is 15–35% higher than the I-4/TT tariff used today. An economist needs both: tariff (what tenants pay) and BPP (what grid electricity costs PLN). The LCOE gap vs. BPP would look more favourable for solar at high-BPP regions. | Blocked — PLN Statistik 2024 regional BPP not yet sourced; column exists in `fct_grid_cost_proxy` but is null. |
| `solar_vs_bpp_gap_pct` not yet computed | V2 elevates this to a first-class column — shows where solar LCOE undercuts PLN's cost of supply, making the procurement incentive argument. Blocked by BPP sourcing. | V2 gap — pipeline code ready (V2-B7), blocked by BPP data. |
| Grid emission factor is 2019 vintage | `grid_emission_factor_t_co2_mwh` (KESDM Tier 2 OM 2019) is 5+ years old. `carbon_breakeven_usd_tco2` inherits this staleness — the carbon price threshold may be over- or under-stated. | Deferred to v1.2 — update to 2023 KESDM or IEA SEA 2024 data. |
| ~~WACC range limited to 8/10/12%~~ | Concessional DFI financing at 4–6% and equity at 14–20% were not modelable. | ✅ Built — full concessional-to-equity spectrum available. |
| CAPEX from ESDM catalogue, not Indonesia market data | ESDM 2023 catalogue value ($960/kW) may be ±15–20% from current Indonesian EPC market pricing. LCOE bands partially capture this but no market comparables have been sourced. | Deferred to v1.2 — source 2023–2024 Indonesia solar EPC tender data. |

---

## Persona 2: DFI Infrastructure Investor

**Role:** Infrastructure investment analyst, development finance institution (ADB, AIIB, World Bank/IFC) or green infrastructure fund (Climate Fund Managers, OPIC/DFC)
**Context:** Identifying where grid infrastructure investment unlocks solar potential at Indonesian industrial zones. DFIs regularly finance transmission lines, substations, and grid reinforcement in developing countries. This persona invests in the **grid** that connects solar supply to industrial demand — not in solar projects directly.
**Primary question:** *Where does grid investment unlock the most solar potential per infrastructure dollar — and what instrument (concessional loan, viability gap funding, blended finance) fits each case?*

**V2 note:** This persona was fundamentally reframed from V1. The V1 "DFI Investor" screened captive solar projects with private gen-tie infrastructure — an approach with no global precedent at 50km scale. V2 reframes the DFI as an infrastructure investor, which aligns with how DFIs actually operate in the power sector.

### Readiness — 40%

**What works:**
- Full 4-layer buildability filter: `buildable_area_ha`, `max_captive_capacity_mwp`, `buildability_constraint` all populated for all 25 KEKs
- `dist_to_nearest_substation_km` and `nearest_substation_capacity_mva` (19/25 KEKs) — KEK-side grid data available
- Solar resource data (`pvout_buildable_best_50km`) solid for screening
- `demand_mwh_2030` provides relative demand ranking for investment prioritization

**What's missing:**
- **`grid_integration_category` not yet built** — the primary decision variable for this persona. Without it, cannot identify `invest_grid` KEKs (the DFI opportunity set). (Gap priority 🔴 1)
- **`dist_solar_to_nearest_substation_km` not yet computed** — the solar-side distance is needed for grid investment sizing. (Gap priority 🔴 3)
- **`grid_investment_needed_usd` not yet computed** — order-of-magnitude estimate of transmission/substation investment per KEK. Derived from solar-to-substation distance × cost per km.
- **BPP is null** — without BPP, cannot show that solar procurement reduces PLN's cost of supply (the economic justification for grid investment). (Gap priority 🟠 4)

### Key data needs

- `grid_integration_category` — primary decision variable: `within_boundary` / `grid_ready` / `invest_grid` / `grid_first` *(V2 — not yet built)*
- `dist_solar_to_nearest_substation_km` — infrastructure gap metric: how far from best solar site to nearest grid injection point *(V2 — not yet built)*
- `grid_investment_needed_usd` — order-of-magnitude investment estimate: `dist_solar_to_substation × transmission_cost_per_km` *(V2 — not yet built)*
- `solar_capacity_unlocked_mwp` — how much solar capacity the grid investment would enable (reuse `max_captive_capacity_mwp`)
- `demand_mwh_2030` — is there industrial demand to justify grid investment at this KEK?
- `nearest_substation_capacity_mva` — can the existing substation absorb new solar generation, or is reinforcement needed?
- `solar_vs_bpp_gap_pct` — does solar reduce PLN's cost of supply? Stronger gap = stronger investment case *(V2 — not yet computed)*

### User journey

1. **Open dashboard** — map color-coded by `grid_integration_category`. Immediately see which KEKs are `grid_ready` (no investment needed), `invest_grid` (targeted investment opportunity), or `grid_first` (major investment needed).
2. **Filter to `invest_grid` category** — these are the DFI opportunity set: KEKs where solar resource exists, industrial demand exists, but grid infrastructure is the bottleneck.
3. **Sort by solar ROI per infrastructure dollar** — rank `invest_grid` KEKs by `solar_capacity_unlocked_mwp / grid_investment_needed_usd`. Highest ratio = most efficient use of DFI capital.
4. **Cross-reference demand** — prioritize KEKs where `demand_mwh_2030` is high. Grid investment at a low-demand KEK may not be justified.
5. **Drill into top candidates** — check solar resource quality (`pvout_buildable_best_50km`), RUPTL alignment (`plan_late` flag), substation capacity (`nearest_substation_capacity_mva`).
6. **Assess BPP economics** — where `solar_vs_bpp_gap_pct` is negative (solar cheaper than PLN's cost), the investment case is self-supporting: grid investment enables solar that reduces PLN's operating cost.
7. **Export ranked list** — CSV with grid integration category, investment estimate, and solar potential for internal investment committee review.

### Investment instruments

| Instrument | When applicable | Example |
|---|---|---|
| Concessional loan to PLN | Transmission line or substation near an `invest_grid` KEK | ADB loan for Sulawesi grid reinforcement enabling solar procurement |
| Viability gap funding | Grid cost exceeds PLN's recoverable tariff revenue | IFC viability gap for remote substation where industrial tariff alone doesn't cover grid CAPEX |
| Blended finance | DFI funds grid, private IPP funds solar, PLN operates connection | AIIB + private IPP co-investment at a Java industrial KEK |
| Green bond with DFI credit enhancement | Large-scale grid modernization program across multiple KEKs | World Bank-backed green bond for PLN's renewable-enabling grid program |

### What they export
Ranked CSV of `invest_grid` KEKs with investment estimate, solar potential, and demand data for investment committee screening memo. GeoJSON for spatial analysis.

### What they'd cite
> "Grid infrastructure gap analysis: KEK Power Competitiveness Dashboard v2.0. Solar resource from Global Solar Atlas v2, substation locations from PLN SIMOL dataset, grid integration categories per METHODOLOGY_V2.md three-point proximity analysis."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `grid_integration_category` not yet built | The primary decision variable. Without it, this persona cannot identify the DFI opportunity set (`invest_grid` KEKs). | V2 gap — requires V2-B1 (solar coords) + V2-B2 (three-point proximity pipeline). |
| `dist_solar_to_nearest_substation_km` not yet computed | Required for grid investment sizing. Currently only KEK-to-substation distance exists. | V2 gap — requires V2-B1 (best solar site lat/lon). |
| `grid_investment_needed_usd` not yet computed | Order-of-magnitude investment estimate. Derived from solar-to-substation distance × cost parameters. | V2 gap — requires V2-B2 + V2-B7 (dashboard logic). |
| `bpp_usd_mwh` is null | Without BPP, cannot show that solar procurement reduces PLN's cost of supply — the economic justification for grid investment. | Blocked — PLN Statistik 2024 regional BPP not yet sourced. |
| Substation capacity partial | 5 of 25 KEKs have null `nearest_substation_capacity_mva`. Grid absorption capacity is critical for this persona. | Available with gaps — 20/25 KEKs have data. |
| Flood hazard layer (Layer 2d) missing | Coastal sites may have buildable land on flood-prone ground. | Deferred to v1.2 — BNPB portal inaccessible. |

---

## Persona 3: Policy Maker

**Role:** Senior official, BKPM (Investment Coordinating Board) or KESDM (Ministry of Energy), or technical adviser at an energy think-tank (IESR, Rocky Mountain Institute Indonesia)
**Context:** Preparing input for a RUPTL review, a KEK electricity regulation update, or a green industrial park policy. V2 makes this persona the **primary audience** because the dashboard now directly answers: "Where should grid infrastructure investment go to unlock cheap solar for industrial zones?"
**Primary question:** *Where should grid infrastructure investment be prioritized to unlock solar potential at KEKs — and which KEKs are already grid-ready for solar procurement?*

### Readiness — 55%

**What works:**
- Action flags (`solar_now`, `grid_first`, `firming_needed`, `plan_late`) populated for all 25 KEKs. V2 adds `invest_grid` (not yet built).
- Full RUPTL pipeline context: `pre2030_solar_mw`, `post2030_share`, `grid_upgrade_pre2030`, `ruptl_summary`
- `green_share_geas` quantifies GEAS allocation as a policy lever
- `carbon_breakeven_usd_tco2` supports carbon market design arguments

**Critical caveat:** Model is **solar-only**. A KESDM adviser reading `grid_first` at kek-palu or kek-bitung (which have known geothermal and wind resources) may lose trust in the tool. The dashboard must clearly label that competitiveness assessment covers solar PV only — wind and geothermal are planned for future versions (see TODOS.md).

**What's missing:**
- **`grid_integration_category` not yet built** — the primary decision variable for V2. Without it, cannot show the three-point proximity map or identify where targeted grid investment unlocks solar. (Gap priority 🔴 1)
- **`invest_grid` action flag not yet implemented** — V2 adds this flag to show where solar exists but grid connection is missing. (Gap priority 🔴 1)
- **`solar_vs_bpp_gap_pct` not yet computed** — shows where solar would reduce PLN's system cost. Critical for budget planning and PLN engagement. (Gap priority 🔴 2)
- **Model is solar-only** — Sulawesi/Maluku KEKs with known geothermal and wind resources may appear less favorable than they are (Gap priority 🟡 6)
- **`reliability_req` is hardcoded by KEK type**, not sourced from PLN SAIDI/SAIFI data — weakening credibility with KESDM technical reviewers
- **`demand_mwh_2030` is a proxy** — GEAS `green_share_geas` inherits area × intensity uncertainty

### Key data needs

- `grid_integration_category` — where does each KEK sit: `within_boundary` / `grid_ready` / `invest_grid` / `grid_first`? *(V2 — not yet built)*
- `invest_grid` action flag — which KEKs need targeted grid investment to unlock solar? *(V2 — not yet built)*
- `solar_vs_bpp_gap_pct` — where does solar reduce PLN's cost of supply? *(V2 — not yet computed)*
- `plan_late` — is the RUPTL pipeline arriving after 2030? (flags KEKs that need grid acceleration)
- `green_share_geas_2030_pct` — share of 2030 demand potentially met by GEAS-allocated solar
- `ruptl_re_base_2030_mw` — PLN's own RE pipeline for this region by 2030
- `solar_competitive_gap_wacc10_pct` — economic gap at market WACC
- `solar_now_at_wacc8` — does concessional finance (8%) close the gap?
- `carbon_breakeven_usd_tco2` — carbon price needed for solar competitiveness (relevant to carbon market design)

### User journey

1. **Open dashboard** — map shows `grid_integration_category` (color-coded). Immediately see which KEKs are `grid_ready` vs. `invest_grid` vs. `grid_first`.
2. **Identify `invest_grid` KEKs** — these are where targeted infrastructure investment unlocks solar potential. The policy question: should RUPTL be adjusted to prioritize these locations?
3. **Cross-reference with RUPTL pipeline** — are grid upgrades already planned for `invest_grid` KEKs? Check `plan_late` flag: if grid improvement is coming but after 2030, recommend RUPTL acceleration.
4. **Prioritize** — sort `invest_grid` KEKs by: solar resource (strong) + demand (high) + grid gap (small = cheapest to fix). These are the highest-impact policy targets.
5. **Check `solar_vs_bpp_gap_pct`** — where solar is cheaper than PLN's cost of supply, the economic case for enabling procurement is self-evident. Use this in budget planning discussions with PLN.
6. **Open Flip Scenario Panel** — set WACC to 8%. Count how many KEKs flip to `solar_now`. This is the policy case for concessional finance or WACC de-risking instruments.
7. **Export CSV** — download ranked table with `grid_integration_category`, `invest_grid`, `plan_late`, `green_share_geas_2030_pct` for RUPTL review or KEK development strategy presentation.
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
> "KEK-level solar competitiveness and grid integration analysis, KEK Power Competitiveness Dashboard v2.0. Grid cost: Permen ESDM 7/2024. RUPTL pipeline: RUPTL PLN 2025–2034. Grid integration methodology: METHODOLOGY_V2.md."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `grid_integration_category` not yet built | The primary decision variable for V2. Without it, cannot show the three-point proximity map or identify `invest_grid` KEKs. | V2 gap — requires V2-B1 + V2-B2. |
| `solar_vs_bpp_gap_pct` not yet computed | Critical for PLN engagement: shows where solar reduces PLN's cost of supply, making the budget case for enabling procurement. | V2 gap — blocked by BPP data sourcing. |
| `reliability_req` is hardcoded by KEK type | `firming_needed` flag depends on assumed reliability scores, not actual PLN SAIDI/SAIFI data. Weakens credibility with KESDM technical reviewers. | Deferred — PLN publishes SAIDI/SAIFI by grid system but not by KEK; requires manual mapping. |
| `demand_mwh_2030` is area × intensity proxy | GEAS `green_share_geas` is allocated against proxy demand, not actual tenant consumption. Policy allocation recommendations inherit this uncertainty. | Deferred — requires tenant surveys or KESDM KEK energy consumption registry. |
| No wind or geothermal resource layer | Model is solar-only. Sulawesi KEKs with known geothermal/wind resources may appear less favorable. A policy maker advising on Sulawesi needs the full clean energy picture. | Deferred — add wind CF layer; geothermal requires separate data source. |
| Carbon price trajectory not modelled | `carbon_breakeven_usd_tco2` is a static threshold. No link to Indonesia's ETS trajectory. | Deferred — requires IDR carbon price forecast data. |
| GEAS allocation is a modelled approximation | Real GEAS depends on PLN tender design, offtake eligibility, and transmission access rights. | Fundamental limitation — label clearly in dashboard. |

---

## Persona 4: IPP / Solar Developer

**Role:** Business development manager or country director, solar IPP developer (ACEN, Vena Energy, SolarEdge Indonesia, local developer)
**Context:** Building a pipeline of solar projects that sell to PLN via PPA. In Indonesia, PLN controls the procurement process — IPPs do not independently choose where to build. PLN issues tenders for specific regions based on RUPTL planning, negotiates PPAs, and allocates grid capacity. The dashboard serves IPPs in two ways:

1. **Pre-positioning:** Identifying regions where solar economics are strongest, so the IPP can prepare (secure land options, complete pre-feasibility studies) ahead of PLN procurement tenders.
2. **Advocacy:** Building the economic case for PLN to prioritize solar procurement in specific regions. An IPP can use the dashboard's data to support proposals showing that solar in a given grid region would reduce BPP — aligning the IPP's commercial interest with PLN's cost-reduction mandate.

**Primary question:** *Where are the strongest solar-to-BPP economics — and where should we pre-position for PLN procurement or advocate for solar prioritization?*

**V2 note:** V1 framed the IPP as selling captive power directly to KEK tenants via PPA. V2 reframes the offtake model: IPP sells to PLN, PLN delivers to KEK tenants. This is the standard Indonesian model.

### Readiness — 65%

**What works:**
- Full buildability screening: `max_captive_capacity_mwp`, `buildable_area_ha`, `pvout_buildable_best_50km` all populated
- `nearest_substation_capacity_mva` available for 19/25 KEKs — grid absorption signal for initial screening
- `demand_mwh_2030` for relative site ranking (not PPA sizing)
- `project_viable` boolean in scorecard

**What's missing:**
- **`solar_vs_bpp_gap_pct` not yet computed** — the primary competitiveness metric for V2. Shows where solar undercuts PLN's cost of supply — the core argument for procurement prioritization. (Gap priority 🔴 2)
- **`dist_solar_to_nearest_substation_km` not yet computed** — the grid injection distance. Replaces the V1 gen-tie distance concept. (Gap priority 🔴 3)
- **`grid_integration_category` not yet built** — replaces V1 `siting_scenario`. Shows grid readiness at each KEK. (Gap priority 🔴 1)
- **`demand_mwh_2030` is a proxy** — area × intensity estimate, not actual tenant consumption (fundamental limitation)
- **KEK operational status is coarse** — doesn't distinguish operating KEKs with tenants from greenfield development (Gap priority 🟡 7)

### Key data needs

- `pvout_buildable_best_50km` — best solar yield in buildable land
- `solar_vs_bpp_gap_pct` — is solar cheaper than PLN's cost of supply? Negative = PLN saves money by procuring solar. *(V2 — not yet computed)*
- `dist_solar_to_nearest_substation_km` — how far from best solar site to grid injection point *(V2 — not yet computed)*
- `grid_integration_category` — `grid_ready` (substation near solar) vs. `invest_grid` (grid gap) vs. `grid_first` (no nearby infrastructure) *(V2 — not yet built)*
- `nearest_substation_capacity_mva` — can the local grid absorb the project's output?
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
> "Solar resource and land buildability: KEK Power Competitiveness Dashboard v2.0. Buildable area uses ESA WorldCover + GFW Peatlands exclusions. Grid integration analysis per METHODOLOGY_V2.md. Demand estimates are provisional (area × intensity proxy); field surveys required for PPA sizing."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `solar_vs_bpp_gap_pct` not yet computed | The primary competitiveness metric for V2. Shows where solar undercuts PLN's cost of supply — the core argument for procurement advocacy. | V2 gap — blocked by BPP data sourcing. |
| `dist_solar_to_nearest_substation_km` not yet computed | Grid injection distance — critical for pre-feasibility and grid connection cost estimates. | V2 gap — requires V2-B1 (best solar site lat/lon). |
| `grid_integration_category` not yet built | Replaces V1 `siting_scenario`. Without it, IPP cannot filter to `grid_ready` sites. | V2 gap — requires V2-B1 + V2-B2. |
| `demand_mwh_2030` is area × intensity proxy | PPA sizing requires actual tenant electricity consumption. The proxy exists only for relative ranking. | Deferred — requires field surveys or KEK management data. |
| KEK operational status is coarse | `status` field does not distinguish "operating with tenants" from "under development". An IPP needs to know if offtake demand is real. | Deferred — requires KEK management outreach or BKPM tenant occupancy registry. |
| Substation capacity partial | 5 of 25 KEKs have null `nearest_substation_capacity_mva`. | Available with gaps — 20/25 KEKs have data. |

---

## Persona 5: Industrial Investor / KEK Tenant

**Role:** Site selection manager or country director, industrial manufacturer or smelter operator (e.g., nickel processing, petrochemicals, automotive components, data center operator)
**Context:** Deciding which KEK to locate a factory or processing facility in. This persona does **not** build solar — they buy electricity from PLN at the regulated industrial tariff. Their decision is driven by electricity cost, reliability, and increasingly by green energy credentials (ESG requirements from buyers and investors).
**Primary question:** *Which KEK offers the lowest risk for electricity cost and reliability over the next 10–15 years — and which ones will have the greenest power mix?*

**V2 note:** This persona was implicit in V1 but not separately modeled. They are the demand side of the equation — the factories and smelters that create the industrial electricity demand the dashboard quantifies.

**Honest limitation:** The PLN I-4 industrial tariff is **nationally uniform** within the same voltage category. This means the dashboard cannot differentiate KEKs by *current* electricity cost — today, it's the same everywhere. The dashboard's value to this persona lies in areas where KEKs **do** differ: subsidy exposure risk, grid reliability trajectory, and future green energy access.

### Readiness — 50%

**What works:**
- PLN I-4 tariff ($63.08/MWh) available as baseline electricity cost
- `dist_kek_to_nearest_substation_km` as a proxy for grid connection quality
- `nearest_substation_capacity_mva` for 19/25 KEKs — can PLN's local grid handle industrial-scale load?
- `green_share_geas_2030_pct` — how much of their power will be renewable by 2030
- `plan_late` flag — timeline risk for grid infrastructure arrival
- RUPTL pipeline context for regional grid development trajectory

**What's missing:**
- **`bpp_usd_mwh` is null** — BPP is critical for this persona because it reveals subsidy exposure. KEKs in high-BPP regions are more exposed to future tariff adjustments (PLN cannot subsidize indefinitely). (Gap priority 🟠 4)
- **`grid_integration_category` not yet built** — proxy for future grid quality and cost trajectory. `grid_ready` KEKs near cheap solar are more likely to see infrastructure investment and improved service. (Gap priority 🔴 1)
- **No PLN SAIDI/SAIFI data** — actual grid reliability by region is not available. Substation distance and capacity are proxies only.

### Key data needs

- `bpp_usd_mwh` — true cost of supply in this grid region. High BPP = high subsidy exposure = tariff adjustment risk *(not yet sourced)*
- `grid_integration_category` — proxy for future grid quality and solar integration trajectory *(V2 — not yet built)*
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
> "KEK electricity infrastructure comparison: KEK Power Competitiveness Dashboard v2.0. Grid cost: Permen ESDM 7/2024 I-4/TT tariff. Substation data from PLN SIMOL dataset. Note: current industrial tariff is nationally uniform; differentiation is based on grid infrastructure quality, BPP subsidy exposure, and renewable energy trajectory."

### Data gaps

| Gap | Impact on this persona | Status |
|-----|----------------------|--------|
| `bpp_usd_mwh` is null | BPP reveals subsidy exposure — the primary risk differentiator for this persona. Without it, cannot show which KEKs face the highest tariff adjustment risk. | Blocked — PLN Statistik 2024 regional BPP not yet sourced. |
| `grid_integration_category` not yet built | Proxy for future grid quality. `grid_ready` KEKs are more likely to see infrastructure investment and improved service. | V2 gap — requires V2-B1 + V2-B2. |
| No PLN SAIDI/SAIFI data | Actual grid reliability by region is unavailable. Substation distance and capacity are proxies only. An industrial investor making a 15-year commitment needs better reliability data. | Deferred — PLN publishes SAIDI/SAIFI by grid system but not by KEK; requires manual mapping. |
| KEK operational status is coarse | `status` field does not show tenant occupancy or infrastructure readiness. An industrial investor choosing between KEKs needs to know if peers are already operating there. | Deferred — requires BKPM/KEK management data. |
| No logistics or transport cost data | Electricity is one input; transport, labor, and raw material access also matter for site selection. Dashboard covers electricity only. | Out of scope — fundamental limitation. |
