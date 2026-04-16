# Executive Summary — SEZ Renewable Energy Dashboard

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

Indonesia has 25 **Special Economic Zones** (called KEKs — *Kawasan Ekonomi Khusus*) spread across the archipelago. These are industrial parks and tourism zones where the government has created special rules to attract foreign investment. One of the biggest questions investors ask before committing to a KEK is: **"How much will electricity cost here, and can we get clean energy?"**

Today, answering that question requires piecing together data from multiple government PDFs, energy tariff regulations, and satellite datasets — work that takes weeks and is rarely done consistently. This project automates that process and produces a single, transparent scorecard for all 25 KEKs.

---

## The Core Question

For each KEK, the model answers one question:

> **Is building your own solar power plant cheaper than buying electricity from PLN (the state utility) — and if not, how close is it, and what would change that?**

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
| **KEK** | Special Economic Zone — an industrial or tourism park with government incentives |
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
A set of Python scripts that pull from eight public data sources and produce thirteen clean, analysis-ready tables. The pipeline runs end-to-end with a single command (`python run_pipeline.py`) and outputs structured CSV files for all 25 KEKs.

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
A pure Python model (`src/model/basic_model.py`) that implements all five calculation steps above. It is fully tested (433 automated tests) and produces a scorecard table covering all 25 KEKs with LCOE bands, competitive gap, action flags, 2D classification (economic tier x infrastructure readiness), and green energy share estimates.

### 3. Dashboard
An interactive web dashboard (React + Vite frontend with FastAPI backend) that lets analysts adjust assumptions — financing rate, capital cost, BESS parameters — and instantly see how the rankings change. Six views:
- **Map** — 25 KEKs with 2D classification encoding (circle fill = economic tier, stroke = infrastructure readiness, outer ring = modifier badges) on MapLibre GL with 3D terrain, buildable area overlays, substation markers
- **Ranked table** — sortable, filterable TanStack Table with column filters, CSV export
- **Quadrant chart** — solar cost vs. grid cost scatter with action flag zones
- **RUPTL context** — regional grid pipeline timing by technology
- **KEK Scorecard** — 6-tab deep-dive (Overview / Solar / Grid / Economics / Industry / Action) with info badges, CBAM cost trajectory, and interactive LCOE curve chart
- **Assumptions panel** — WACC, CAPEX, FOM, lifetime, BESS CAPEX, substation utilization sliders for live recomputation

> **Roadmap details:** See [PLAN.md](PLAN.md) for the full delivery plan and phase status.

---

## The Data (What's Available Today)

All thirteen output tables are produced by the pipeline. Key outputs:

| What it tells you | Table | Status |
|-------------------|-------|--------|
| Which KEK is where, what sector, what grid region | `dim_kek` | ✅ Complete |
| Solar radiation quality per KEK | `fct_kek_resource` | ✅ Filtered — 4-layer buildability applied (ESA WorldCover, GFW Peatlands, DEM slope/elev, Kawasan Hutan) |
| Estimated 2030 electricity demand per KEK | `fct_kek_demand` | ⚠️ Provisional estimate |
| Solar LCOE at 9 financing rates (4–20% WACC, 2% steps) | `fct_lcoe` | ✅ CAPEX verified (ESDM p.66). See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for full column specs. |
| Grid electricity cost per PLN region | `fct_grid_cost_proxy` | ✅ Official tariff |
| PLN's planned solar additions 2025–2034 | `fct_ruptl_pipeline` | ✅ Manually verified |
| Captive coal, nickel, steel, cement within 50km | `fct_captive_*` | ✅ GEM + CGSP trackers. 4 industry overlays. |
| EU CBAM exposure: cost trajectory 2026-2034 | Scorecard fields | ✅ 12/25 KEKs exposed. 3-signal detection. |
| Full scorecard: LCOE vs. grid cost + action flags | `fct_kek_scorecard` | ⚠️ Provisional until CAPEX verified |

> **Column-by-column reference:** See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for every table, every column, its source, and its status.

---

## Known Limitations

Three things to be aware of when interpreting results:

1. **Buildable area is a modelled estimate, not a surveyed figure.** The pipeline applies four land exclusion layers (protected forests, peatlands, croplands/urban, steep slopes) using satellite and open datasets. This produces a realistic buildable area per KEK, but field surveys will differ — local land tenure disputes, micro-terrain, and access constraints are not captured. Use `buildable_area_ha` and `max_captive_capacity_mwp` as order-of-magnitude screening figures, not engineering inputs.

2. **Construction costs are provisional.** The CAPEX and O&M figures from the ESDM Technology Catalogue still need to be manually verified against the source PDF. Once verified, all LCOE outputs will be updated and marked as confirmed.

3. **Demand is estimated, not measured.** KEK electricity demand is estimated from zone area and sector type (industrial parks use more power per hectare than tourism zones). Real figures require tenant load surveys that aren't publicly available.

> **Full limitations list:** See [METHODOLOGY_CONSOLIDATED.md — Section 11](docs/METHODOLOGY_CONSOLIDATED.md) for a complete catalogue of model limitations and planned fixes.

---

## Who This Is For and How to Use It

**Primary audience:** Development bank analysts (ADB, IFC, AIIB) and energy investors doing due diligence on industrial location decisions or captive solar project financing.

**How a typical analyst uses this:**
1. Open the dashboard → see all 25 KEKs on a map colored by clean power score
2. Set the WACC slider to their fund's hurdle rate → rankings update live
3. Identify 3–5 candidate KEKs from the quadrant chart
4. Toggle the "flip scenario" → see which KEKs become solar-competitive under a concessional finance rate or CAPEX reduction
5. Export the ranked table as CSV → paste into an investment memo
6. Drill into a KEK scorecard → full assumptions and source citations for due diligence

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
