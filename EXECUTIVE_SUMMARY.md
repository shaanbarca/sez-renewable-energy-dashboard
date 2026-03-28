# Executive Summary — Indonesia KEK Clean Power Competitiveness

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

Indonesia has 24 **Special Economic Zones** (called KEKs — *Kawasan Ekonomi Khusus*) spread across the archipelago. These are industrial parks and tourism zones where the government has created special rules to attract foreign investment. One of the biggest questions investors ask before committing to a KEK is: **"How much will electricity cost here, and can we get clean energy?"**

Today, answering that question requires piecing together data from multiple government PDFs, energy tariff regulations, and satellite datasets — work that takes weeks and is rarely done consistently. This project automates that process and produces a single, transparent scorecard for all 24 KEKs.

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
    Based on the gap and grid conditions, we assign one of four flags:
    • Go solar now     — already cost-competitive, grid is ready
    • Grid first       — solar is attractive but the grid upgrade isn't
                         scheduled until after 2030
    • Firming needed   — solar works economically, but the KEK needs
                         reliable 24/7 power (storage or backup required)
    • Watch pipeline   — PLN's planned solar additions for this region
                         are mostly scheduled post-2030
```

> **Deeper dive:** See [METHODOLOGY.md](METHODOLOGY.md) for the full formulas, data sources, and known limitations.

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
| **Action flag** | A one-line recommendation per KEK based on the analysis: `solar_now`, `grid_first`, `firming_needed`, or `plan_late`. |

---

## What's Been Built

The project has three layers:

### 1. Data Pipeline
A set of Python scripts that pull from six public data sources and produce eight clean, analysis-ready tables. The pipeline runs end-to-end with a single command (`python run_pipeline.py`) and outputs structured CSV files for all 24 KEKs.

**Data sources used:**
- Global Solar Atlas v2 satellite data (sun radiation per location)
- Indonesia Ministry of Energy (ESDM) technology cost catalogue
- Permen ESDM No. 7/2024 (official electricity tariff regulation)
- PLN RUPTL 2025–2034 (national electricity supply plan PDF)
- KEK portal (scraped zone boundaries, coordinates, and sector types)
- Substation locations (for grid access proximity analysis)

### 2. Analytical Model
A pure Python model (`src/model/basic_model.py`) that implements all five calculation steps above. It is fully tested (127 automated tests) and produces a scorecard table covering all 24 KEKs with LCOE bands, competitive gap, action flags, and green energy share estimates.

### 3. Dashboard *(in progress)*
An interactive web dashboard (built in Dash/Plotly) that lets analysts adjust assumptions — financing rate, capital cost — and instantly see how the rankings change. Planned views:
- **Map** — 24 KEKs colored by clean power advantage
- **Quadrant chart** — solar cost vs. grid cost, with four action zones
- **WACC slider** — adjust financing assumptions to match a fund's hurdle rate
- **Ranked table** — sortable, exportable to CSV
- **Flip scenario** — which KEKs are within reach of solar-competitive with one policy lever

> **Roadmap details:** See [PLAN.md](PLAN.md) for the full delivery plan and phase status.

---

## The Data (What's Available Today)

All eight output tables are produced by the pipeline. Key outputs:

| What it tells you | Table | Status |
|-------------------|-------|--------|
| Which KEK is where, what sector, what grid region | `dim_kek` | ✅ Complete |
| Solar radiation quality per KEK | `fct_kek_resource` | ✅ Filtered — 4-layer buildability applied (ESA WorldCover, GFW Peatlands, DEM slope/elev, Kawasan Hutan) |
| Estimated 2030 electricity demand per KEK | `fct_kek_demand` | ⚠️ Provisional estimate |
| Solar LCOE at 3 financing rates (8/10/12% WACC) | `fct_lcoe` | ⚠️ CAPEX needs PDF verification |
| Grid electricity cost per PLN region | `fct_grid_cost_proxy` | ✅ Official tariff |
| PLN's planned solar additions 2025–2034 | `fct_ruptl_pipeline` | ✅ Manually verified |
| Full scorecard: LCOE vs. grid cost + action flags | `fct_kek_scorecard` | ⚠️ Provisional until CAPEX verified |

> **Column-by-column reference:** See [DATA_DICTIONARY.md](DATA_DICTIONARY.md) for every table, every column, its source, and its status.

---

## Known Limitations

Three things to be aware of when interpreting results:

1. **Buildable area is a modelled estimate, not a surveyed figure.** The pipeline applies four land exclusion layers (protected forests, peatlands, croplands/urban, steep slopes) using satellite and open datasets. This produces a realistic buildable area per KEK, but field surveys will differ — local land tenure disputes, micro-terrain, and access constraints are not captured. Use `buildable_area_ha` and `max_captive_capacity_mwp` as order-of-magnitude screening figures, not engineering inputs.

2. **Construction costs are provisional.** The CAPEX and O&M figures from the ESDM Technology Catalogue still need to be manually verified against the source PDF. Once verified, all LCOE outputs will be updated and marked as confirmed.

3. **Demand is estimated, not measured.** KEK electricity demand is estimated from zone area and sector type (industrial parks use more power per hectare than tourism zones). Real figures require tenant load surveys that aren't publicly available.

> **Full limitations list:** See [METHODOLOGY.md — Section 6](METHODOLOGY.md) for a complete catalogue of model limitations and planned fixes.

---

## Who This Is For and How to Use It

**Primary audience:** Development bank analysts (ADB, IFC, AIIB) and energy investors doing due diligence on industrial location decisions or captive solar project financing.

**How a typical analyst uses this:**
1. Open the dashboard → see all 24 KEKs on a map colored by clean power score
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
| [PERSONAS.md](PERSONAS.md) | Detailed user journeys for all four audiences — Energy Economist, DFI Investor, Policy Maker, Energy Investor |
| [DESIGN.md](DESIGN.md) | Dashboard UX design: 6 views, component architecture, colour system, open design decisions |
| [PLAN.md](PLAN.md) | Full implementation roadmap: phases, status, dashboard design decisions |
| [METHODOLOGY.md](METHODOLOGY.md) | All formulas, data sources, assumptions, and limitations (for energy economists and peer reviewers) |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every data table and column: source, formula, status, and lineage |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture and data flow diagram |
| [CLAUDE.md](CLAUDE.md) | Developer setup guide: how to run the pipeline, tests, and notebooks |
