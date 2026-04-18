# Executive Summary — Indonesia Industrial Decarbonization Dashboard

> **Who this is for:** Development bank analysts, energy investors, and policy advisors who want to understand what this project does and why — without needing a background in data engineering or energy economics.
>
> **For technical details**, follow the links in each section to the relevant reference document.

---

## Table of Contents

- [The Problem This Solves](#the-problem-this-solves)
- [The Core Question](#the-core-question)
- [How It Works — Five Steps](#how-it-works--five-steps)
- [Key Concepts (Plain English)](#key-concepts-plain-english)
- [What's Been Built](#whats-been-built)
- [The Data (What's Available Today)](#the-data-whats-available-today)
- [Known Limitations](#known-limitations)
- [Who This Is For and How to Use It](#who-this-is-for-and-how-to-use-it)
- [Document Map](#document-map)

---

## The Problem This Solves

Indonesia's industrial CO2 emissions come overwhelmingly from heavy industry: steel, cement, aluminium, fertilizer, and nickel smelting. Some of these sites sit inside Special Economic Zones (KEKs — *Kawasan Ekonomi Khusus*), but the largest emitters (Krakatau Steel in Cilegon, cement clusters across Java, Inalum in Asahan, Pupuk Kaltim in Bontang) are **standalone plants and industrial parks outside KEK boundaries**. Any serious analysis of industrial decarbonization has to cover both.

This dashboard covers **79 sites**: 25 KEKs plus 54 industrial sites (32 cement plants, 7 steel mills, 10 non-KEK nickel IIA clusters, 2 aluminium smelters, 3 fertilizer plants). Ammonia and petrochemical scaffolding (enums, demand intensities, CBAM 2.3 tCO₂/t Indonesia-specific ammonia Scope 1) is wired in but no rows have been added yet — see TODOS M28/M29 for the planned top-down universe-discovery pass. For each in-scope site, it answers the same question investors and policymakers ask: **"How much will electricity cost here, can we get clean energy, and how exposed is this site to the EU Carbon Border Adjustment Mechanism (CBAM)?"**

Today, answering that question requires piecing together data from multiple government PDFs, energy tariff regulations, asset-level trackers (GEM, CGSP), and satellite datasets — work that takes weeks and is rarely done consistently. This project automates that process and produces a single, transparent scorecard for all 79 sites.

---

## The Core Question

For each site, the model answers one question:

> **Is building your own solar (or wind, or hybrid) power plant cheaper than buying electricity from PLN (the state utility) — and if not, how close is it, and what would change that?**

This matters because industrial electricity in Indonesia costs around **$63 USD per megawatt-hour** (the official I-4 industrial tariff from the Ministry of Energy). If a company can build solar for less than that, captive solar is a no-brainer. If it's close, the right policy nudge (a better financing rate, a government energy allocation) could tip the balance.

---

## How It Works — Five Steps

The model follows a simple chain of calculations. Plain-English version:

```
Step 1 — How much sun does this KEK get?
    Satellite data (Global Solar Atlas) tells us the average daily solar
    radiation at each KEK's location. We convert that to an annual number
    and then to a "capacity factor" — the fraction of time the solar plant
    is effectively producing at full power.

Step 2 — What would solar cost to build and operate?
    Using cost data from Indonesia's own Energy Ministry catalogue, we
    calculate the Levelized Cost of Energy (LCOE) — the all-in cost per
    megawatt-hour over the plant's 25-year life. This accounts for
    construction cost, annual maintenance, and the cost of financing.

Step 3 — What does the grid charge?
    The official industrial electricity tariff (Permen ESDM No. 7/2024)
    sets a uniform national rate of ~$63/MWh for large industrial users.
    This is the benchmark solar must beat.

Step 4 — How big is the gap?
    We compute the "competitive gap" — how much more (or less) solar costs
    vs. the grid. A negative gap means solar is already cheaper.

Step 5 — What action does each KEK need?
    Based on the gap and grid conditions, we assign one of nine action flags:
    • Solar now             — already cost-competitive, grid is ready
    • Invest: transmission  — solar can reach a substation, but the KEK
                              is far from grid. Build transmission.
    • Invest: substation    — KEK is grid-connected, but solar is far
                              from any substation. Build a new one.
    • Grid first            — solar is attractive but grid upgrade isn't
                              scheduled until after 2030
    • Invest: battery       — solar economics work, but battery storage
                              is needed for reliability
    • Invest: resilience    — solar is near grid parity and the KEK has
                              high reliability requirements
    • Plan late             — 60%+ of RUPTL solar is scheduled post-2030.
                              Planning is behind.
    • Not competitive       — solar LCOE exceeds grid cost or resource
                              quality is below minimum threshold
    • No solar resource     — insufficient solar resource for viable project
```

> **Deeper dive:** See [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) for the full formulas, data sources, and known limitations.

---

## Key Concepts (Plain English)

| Term | What it means |
|------|---------------|
| **Site** | A location the dashboard analyzes. Four types: **KEK** (Special Economic Zone), **KI** (industrial park / *Kawasan Industri*), **standalone** (a single large plant like Krakatau Steel), **cluster** (multiple plants sharing infrastructure, e.g. the Cilegon steel corridor). |
| **KEK** | Special Economic Zone — an industrial or tourism park with government incentives |
| **Sector** | Industrial sector of the site: steel, cement, aluminium, fertilizer, nickel, or mixed (KEKs with multiple tenant sectors). Drives CBAM exposure and electricity intensity assumptions. |
| **CBAM** | EU Carbon Border Adjustment Mechanism. From 2026, EU importers pay a carbon certificate fee on embedded emissions in imported steel, cement, aluminium, and fertilizer. Free allocation phases out 2026→2034 (97.5% → 0%). Indonesian exporters pay roughly €80/tCO2 × embedded intensity. |
| **LCOE** | Levelized Cost of Energy — the total lifetime cost of a power plant divided by total electricity produced, expressed in $/MWh. Think of it as the "break-even price" the plant needs to charge to cover all costs. |
| **PVOUT** | How much electricity one kilowatt of solar panels produces in a year at a given location, based on satellite solar radiation data. Higher = sunnier = cheaper solar. |
| **Capacity Factor (CF)** | The fraction of the year a solar plant operates at full output. Indonesian solar averages 15–20%. |
| **WACC** | Weighted Average Cost of Capital — the financing rate used to fund the solar plant. Higher WACC = more expensive borrowing = higher LCOE. Development banks like ADB can offer lower rates, directly improving competitiveness. |
| **GEAS** | Government Energy Allocation for Solar — the share of planned grid-scale solar (from the national electricity plan, RUPTL) that a KEK can claim as "green energy" toward its sustainability targets. |
| **RUPTL** | PLN's 10-year electricity supply plan (2025–2034), which sets the schedule for new power plants by region. |
| **I-4/TT tariff** | The official industrial electricity rate for large users connected to the high-voltage grid. ~$63/MWh nationwide. |
| **Action flag** | A one-line recommendation per KEK based on the analysis. Nine flags from best to worst: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive`, `no_solar_resource`. |
| **Economic tier** | 2D classification axis: how economically viable is RE at this KEK? Five tiers: `full_re` (RE+storage beats grid 24/7), `partial_re` (daytime RE beats grid), `near_parity` (within 20%), `not_competitive`, `no_resource`. |
| **Infrastructure readiness** | 2D classification axis: what grid infrastructure exists? Five levels: `within_boundary`, `grid_ready`, `invest_transmission`, `invest_substation`, `grid_first`. |

---

## What's Been Built

The project has three layers:

### 1. Data Pipeline
A set of Python scripts that pull from eight public data sources and produce thirteen clean, analysis-ready tables. The pipeline runs end-to-end with a single command (`python run_pipeline.py`) and outputs structured CSV files for all 79 sites (25 KEK + 54 industrial). Industrial site selection is itself pipeline-driven: `build_industrial_sites.py` reads GEM Global Cement Plant Tracker (32 operating Indonesian plants), GEM Global Iron & Steel Plant Tracker (7 active plants), and CGSP Nickel Tracker (10 Integrated Industrial Area parent projects, filtered to exclude KEK overlaps and aggregate capacity from nearby Processing children) and unions them with a residual manual CSV for the sectors without a tracker step (2 aluminium + 3 fertilizer = 5 rows, each row provenance-enforced with `source_url`). Site-type behavior (demand method, captive power matching, CBAM detection, marker shape) is driven by a single registry (`src/model/site_types.py`, mirrored in `frontend/src/lib/siteTypes.ts`) — adding a new site type is a one-entry change, not a 10-file refactor.

**Data sources used:**
- Global Solar Atlas v2 satellite data (sun radiation per location)
- Indonesia Ministry of Energy (ESDM) technology cost catalogue
- Permen ESDM No. 7/2024 (official electricity tariff regulation)
- PLN RUPTL 2025–2034 (national electricity supply plan PDF)
- KEK portal (scraped zone boundaries, coordinates, and sector types)
- Substation locations (for grid access proximity analysis)
- GEM Global Coal, Steel, and Cement Plant Trackers (captive power and CBAM-exposed industry)
- CGSP Nickel Tracker (nickel smelter locations, process types, ownership)

### 2. Analytical Model
A pure Python model (`src/model/basic_model.py`) that implements all five calculation steps above. It is fully tested (532 automated tests) and produces a scorecard table covering all 79 sites with LCOE bands, competitive gap, action flags, 2D classification (economic tier x infrastructure readiness), green energy share estimates, and CBAM cost trajectories (2026, 2030, 2034). CBAM detection is dual-mode: KEKs use a 3-signal inference (business sector + captive infrastructure + nickel process type), industrial sites use direct assignment from the `cbam_product_type` column. Result: 66 of 79 sites are flagged CBAM-exposed (12 KEK + 54 industrial: 32 cement + 17 iron_steel + 3 fertilizer + 2 aluminium). Ammonia calibration (Indonesia-specific Scope 1 = 2.3 tCO₂/t, ICGD gas-SMR) is wired into the cost model and ready for when ammonia rows land via TODOS M28; petrochemical is intentionally outside EU CBAM Annex I.

### 3. Dashboard
An interactive web dashboard (React + Vite frontend with FastAPI backend) that lets analysts adjust assumptions — financing rate, capital cost, BESS parameters — and instantly see how the rankings change. Seven views:
- **Map** — 79 sites with 2D classification encoding (circle fill = economic tier, stroke = infrastructure readiness, outer ring = modifier badges) on MapLibre GL with 3D terrain, buildable area overlays, substation markers; filterable by site type (KEK / KI / standalone / cluster) and sector (steel / cement / aluminium / fertilizer / nickel / mixed; ammonia/petrochemical reserved in registry)
- **Ranked table** — sortable, filterable TanStack Table with column filters, sector + site-type dropdowns, CSV export
- **Quadrant chart** — solar cost vs. grid cost scatter with action flag zones
- **RUPTL context** — regional grid pipeline timing by technology
- **Sector Summary** — aggregated CBAM cost trajectory by sector ($M/year in 2026/2030/2034), 2030 electricity demand by sector, action-flag distribution per sector
- **Site Scorecard** — 6-tab deep-dive (Overview / Solar / Grid / Economics / Industry / Action) with site-type-aware identity fields (KEK: developer, legal basis; standalone: primary product, technology, parent company; cluster: member facilities), info badges, CBAM cost trajectory, and interactive LCOE curve chart
- **Assumptions panel** — WACC, CAPEX, FOM, lifetime, BESS CAPEX, substation utilization sliders for live recomputation

> **Roadmap details:** See [PLAN.md](PLAN.md) for the full delivery plan and phase status.

---

## The Data (What's Available Today)

All thirteen output tables are produced by the pipeline. Key outputs:

| What it tells you | Table | Status |
|-------------------|-------|--------|
| Which site is where, what sector, what grid region, what type (KEK/KI/standalone/cluster) | `dim_sites` | ✅ 79 rows — 25 KEK + 54 industrial (tracker-driven + residual CSV) |
| Solar radiation quality per site | `fct_site_resource` | ✅ Filtered — 4-layer buildability applied (ESA WorldCover, GFW Peatlands, DEM slope/elev, Kawasan Hutan) |
| Wind resource per site (speed, CF, buildability) | `fct_site_wind_resource` | ✅ Global Wind Atlas v3 + 6-layer filter |
| Estimated 2030 electricity demand per site | `fct_site_demand` | ✅ Dual-mode — KEKs use area × intensity, industrial sites use capacity × sector intensity (steel/cement/aluminium/fertilizer/nickel) |
| Solar LCOE at 9 financing rates (4–20% WACC, 2% steps) | `fct_lcoe` | ✅ CAPEX verified (ESDM p.66). 1,422 rows (79 × 9 × 2). |
| Grid electricity cost per PLN region | `fct_grid_cost_proxy` | ✅ Official tariff |
| PLN's planned solar additions 2025–2034 | `fct_ruptl_pipeline` | ✅ Manually verified |
| Captive coal, nickel, steel, cement matched to each site | `fct_captive_*` | ✅ Dual-mode — KEKs use 50km proximity scan; standalone/cluster sites matched directly by site_id. Shared `src/pipeline/geo_utils.py` (haversine + proximity_match + direct_match). |
| EU CBAM exposure: cost trajectory 2026-2034 | Scorecard fields | ✅ 66/79 sites exposed (12 KEK 3-signal + 54 industrial direct). Ammonia calibration (2.3 tCO₂/t Indonesia-specific Scope 1) wired in pending row ingestion (TODOS M28). |
| Full scorecard: LCOE vs. grid cost + action flags + 2D classification + CBAM | `fct_site_scorecard` | ✅ 79 rows. |

> **Column-by-column reference:** See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for every table, every column, its source, and its status.

---

## Known Limitations

Three things to be aware of when interpreting results:

1. **Buildable area is a modelled estimate, not a surveyed figure.** The pipeline applies four land exclusion layers (protected forests, peatlands, croplands/urban, steep slopes) using satellite and open datasets. This produces a realistic buildable area per KEK, but field surveys will differ — local land tenure disputes, micro-terrain, and access constraints are not captured. Use `buildable_area_ha` and `max_captive_capacity_mwp` as order-of-magnitude screening figures, not engineering inputs.

2. **Construction costs are provisional.** The CAPEX and O&M figures from the ESDM Technology Catalogue still need to be manually verified against the source PDF. Once verified, all LCOE outputs will be updated and marked as confirmed.

3. **Demand is estimated, not measured.** For KEKs, demand is estimated from zone area and sector type (industrial parks use more power per hectare than tourism zones). For standalone and cluster industrial sites, demand is computed from annual production tonnes × sector electricity intensity (steel EAF 0.5 MWh/t, cement 0.11 MWh/t, aluminium 15 MWh/t, fertilizer 1.0 MWh/t, nickel RKEF 37.5 MWh/t). Real figures require tenant load surveys that aren't publicly available.

4. **CBAM covers Scope 2 (electricity) only.** The CBAM cost trajectories reflect embedded emissions from electricity consumption. Process emissions (Scope 1 — cement calcination, aluminium electrolysis carbon anodes) require sector-specific models not yet implemented. Reported CBAM exposure is a lower bound for heavy-industry sites.

> **Full limitations list:** See [METHODOLOGY_CONSOLIDATED.md — Section 11](docs/METHODOLOGY_CONSOLIDATED.md) for a complete catalogue of model limitations and planned fixes.

---

## Who This Is For and How to Use It

**Primary audience:** Development bank analysts (ADB, IFC, AIIB) and energy investors doing due diligence on industrial location decisions or captive solar project financing.

**How a typical analyst uses this:**
1. Open the dashboard → see all 79 sites on a map colored by clean power score
2. Filter by sector (e.g. steel) to compare all CBAM-exposed steel plants side by side
3. Set the WACC slider to their fund's hurdle rate → rankings update live
4. Identify 3–5 candidate sites from the quadrant chart or sector summary
5. Toggle the "flip scenario" → see which sites become solar-competitive under a concessional finance rate or CAPEX reduction
6. Export the ranked table as CSV → paste into an investment memo
7. Drill into a site scorecard → full assumptions, CBAM cost trajectory, and source citations for due diligence

---

## Document Map

| Document | What it covers |
|----------|---------------|
| **This file** | Plain-language overview of the project |
| [PERSONAS.md](PERSONAS.md) | Detailed user journeys for all five audiences — Energy Economist, DFI Investor, Policy Maker, IPP/RE Developer, Industrial Investor |
| [DESIGN.md](DESIGN.md) | Dashboard UX design: 6 views, component architecture, colour system, open design decisions |
| [PLAN.md](PLAN.md) | Full implementation roadmap: phases, status, dashboard design decisions |
| [METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) | All formulas, data sources, assumptions, and limitations (for energy economists and peer reviewers) |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every data table and column: source, formula, status, and lineage |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture and data flow diagram |
| [CLAUDE.md](CLAUDE.md) | Developer setup guide: how to run the pipeline, tests, and notebooks |
