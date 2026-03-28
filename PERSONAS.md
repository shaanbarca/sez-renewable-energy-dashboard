# Personas — Indonesia KEK Power Competitiveness Dashboard

Four primary user personas. Each section covers: who they are, what they need from the data, their step-by-step journey through the dashboard, what they export, and how they'd cite the tool.

**Related:** [DESIGN.md](DESIGN.md) | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | [DATA_DICTIONARY.md](DATA_DICTIONARY.md)

---

## Persona 1: Energy Economist

**Role:** Economic analyst, multilateral development bank (ADB, IFC, World Bank)
**Context:** Preparing a country energy competitiveness assessment or a captive renewable energy policy brief. Needs to compare solar LCOE against grid cost across many sites simultaneously and quantify the carbon arbitrage opportunity. Works in Excel and PowerPoint; exports data for colleagues.
**Primary question:** *At our fund's hurdle rate, which KEKs already make economic sense for captive solar — and what policy change would unlock the others?*

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

---

## Persona 2: DFI Investor

**Role:** Infrastructure fund analyst or investment director, development finance institution or green infrastructure fund (Macquarie Green Infrastructure, AIIB, OPIC/DFC)
**Context:** Screening Indonesian industrial sites for a captive solar PPA or equity investment. Needs to know: is there enough buildable land, how far is the grid connection, and what does the LCOE look like at their fund's cost of capital? Will hand off promising sites to a site development team.
**Primary question:** *Which KEKs have sufficient buildable solar land, acceptable grid connection cost, and an LCOE that works at our 8% target return?*

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

---

## Persona 3: Policy Maker

**Role:** Senior official, BKPM (Investment Coordinating Board) or KESDM (Ministry of Energy), or technical adviser at an energy think-tank (IESR, Rocky Mountain Institute Indonesia)
**Context:** Preparing input for a RUPTL review, a KEK electricity regulation update, or a green industrial park policy. Needs to understand which KEKs will be left behind by the current grid plan, which ones could benefit from WACC de-risking (concessional finance), and how much of 2030 demand could be met by GEAS-allocated solar.
**Primary question:** *Which KEKs need policy intervention — and what specific intervention (WACC de-risking, RUPTL acceleration, GEAS allocation) would have the most impact?*

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

---

## Persona 4: Energy Investor (IPP Developer)

**Role:** Business development manager or country director, captive solar IPP developer (ACEN, SolarEdge Indonesia, Vena Energy, local developer)
**Context:** Building a project pipeline of captive solar PPAs with industrial tenants at KEKs. Needs to prioritise outreach — which KEKs have the largest demand, best solar resource, and weakest grid (making the PPA pitch easiest)? Will use this data to rank sites for BD outreach, then hand off top 5 to technical team for desktop feasibility.
**Primary question:** *Which KEKs offer the best PPA opportunity — large captive demand, good solar, high grid cost, and buildable land inside the zone?*

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
