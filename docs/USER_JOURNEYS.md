# User Journeys — KEK Power Competitiveness Dashboard

Step-by-step walkthroughs for each persona, mapped to the actual dashboard UI. Each step names the exact component and interaction.

*Derived from [PERSONAS.md](../PERSONAS.md). See [METHODOLOGY_CONSOLIDATED.md](METHODOLOGY_CONSOLIDATED.md) for analytical details.*

---

## Dashboard UI Reference

Before diving into journeys, here's what you're working with:

| Component | Location | What it does |
|-----------|----------|-------------|
| **Map View** | Full-screen background | KEK markers color-coded by action flag. Click a marker to select. |
| **Assumptions Panel** | Left side, draggable | WACC slider, cost sliders (Tier 1/2), threshold sliders (Tier 3), Benchmark toggle (Tariff vs BPP), Reset button. |
| **Bottom Panel** | Bottom, collapsible | 3 tabs: **Ranked Table**, **Quadrant Chart**, **RUPTL Context**. |
| **Score Drawer** | Right side, slides in | 6 tabs: Info, Resource, LCOE, Demand, Pipeline, Flags. Opens when a KEK is selected. |
| **Header** | Top bar | Guide button (restarts walkthrough), Methodology button, Energy toggle (Solar/Wind/Overall), KEK count. |
| **Layer Control** | Top-right, draggable | 9 layer checkboxes + 4 map style buttons. |
| **Action Flag Legend** | Header dropdown | All 8 flags with color dots and hover descriptions. |

### Key interactions

- **Select a KEK:** Click a map marker or a table row. Opens the Score Drawer.
- **Change assumptions:** Drag sliders in the Assumptions Panel. Scorecard recomputes automatically via `POST /api/scorecard`.
- **Switch benchmark:** Toggle between I-4/TT Tariff ($63/MWh, uniform) and Regional BPP ($57-133/MWh). Changes the Quadrant Chart Y-axis and all gap calculations.
- **Filter the table:** Click the filter icon in the Ranked Table toolbar. Dropdown filters for action flag, province, grid integration, etc. Range filters for LCOE, gap, capacity.
- **Export CSV:** Button in the Ranked Table toolbar. Downloads `kek_scorecard.csv` with 10 columns.
- **Switch energy mode:** Header toggle: Solar / Wind / Overall. Controls which technology's LCOE drives the display.

---

## Journey 1: Energy Economist

**Role:** Multilateral development bank analyst (ADB, IFC, World Bank)
**Primary question:** At our fund's hurdle rate, which KEKs already make economic sense for solar, and what policy change would unlock the others?

### Steps

| # | Action | Component | What to look for |
|---|--------|-----------|-----------------|
| 1 | **Scan the map** | Map View | Green markers = `solar_now`. Red = `not_competitive`. Notice geographic clustering: Java manufacturing belt vs. eastern islands. |
| 2 | **Open Quadrant Chart** | Bottom Panel > Quadrant tab | KEKs above the diagonal line have grid costs higher than solar LCOE = solar is already competitive. Four color zones: green (solar now), orange (invest resilience), blue (grid first), red (not competitive). |
| 3 | **Set WACC to 8%** | Assumptions Panel > WACC slider | Watch which KEKs shift from red to green. These are the concessional-finance flip cases, the core policy argument for DFI involvement. |
| 4 | **Adjust thresholds** | Assumptions Panel > Advanced > Flag Thresholds | Slide the resilience gap to 20% to see all KEKs within striking distance. Note which ones have `invest_resilience` flags. |
| 5 | **Sort by competitive gap** | Bottom Panel > Ranked Table | Sort `Gap (%)` ascending. KEKs closest to zero are the easiest wins. Add `carbon_breakeven_usd_tco2` to your mental shortlist. |
| 6 | **Export CSV** | Bottom Panel > Ranked Table > Export button | Downloads `kek_scorecard.csv`. Paste into Excel for the economic analysis annex. |
| 7 | **Drill into 2-3 KEKs** | Score Drawer (click any marker/row) | **LCOE tab:** verify LCOE bands at your target WACC. **Demand tab:** check `carbon_breakeven_usd_tco2` and `green_share_geas`. **Info tab:** note `is_capex_provisional` flag for caveating. |
| 8 | **Cite in report** | — | Reference the GitHub Release version tag, ESDM catalogue CAPEX, grid cost source, and METHODOLOGY_CONSOLIDATED.md. |

### What gets exported
Ranked table CSV with LCOE, gap, carbon breakeven, grid region, BPP. Goes into Excel for the economic comparison annex.

### Walkthrough tour
The in-app guided tour (click "Guide" in Header, select "Energy Economist") covers 8 steps: Overview Map, Quadrant Chart, Adjust WACC, Ranked Table, Carbon Breakeven, KEK Scorecard, Export Data, Ready.

---

## Journey 2: DFI Infrastructure Investor

**Role:** Infrastructure investment analyst, development finance institution (ADB, AIIB, World Bank/IFC)
**Primary question:** Where does grid investment unlock the most solar potential per infrastructure dollar?

### Steps

| # | Action | Component | What to look for |
|---|--------|-----------|-----------------|
| 1 | **Scan map by grid integration** | Map View | Color-coded by `grid_integration_category`. `grid_ready` (no investment needed) vs. `invest_transmission`/`invest_substation` (targeted opportunity) vs. `grid_first` (major investment). |
| 2 | **Filter to investment opportunities** | Bottom Panel > Ranked Table > Filter | Set action flag filter to `invest_transmission` and `invest_substation`. These are your opportunity set: solar resource exists, demand exists, grid is the bottleneck. |
| 3 | **Sort by capacity** | Bottom Panel > Ranked Table | Sort `Capacity (MWp)` descending. You want sites large enough for utility-scale: at least 50 MWp. |
| 4 | **Check grid integration column** | Bottom Panel > Ranked Table | `invest_transmission` = solar near substation but KEK far (build transmission). `invest_substation` = KEK near grid but solar far (build substation). The distinction tells you what to fund. |
| 5 | **Cross-reference demand** | Score Drawer > Demand tab | Click top candidates. Check `2030 Demand Estimate (GWh)`. Grid investment at a low-demand KEK may not be justified. |
| 6 | **Check substation capacity** | Score Drawer > Pipeline tab | Look at the capacity traffic light: green (can absorb), yellow (tight), red (upgrade needed), unknown (no data). Check `Available Capacity (MVA)`. |
| 7 | **Assess BPP economics** | Score Drawer > LCOE tab | Where `Gap vs BPP (%)` is negative, solar is cheaper than PLN's cost of supply. The investment case is self-supporting. |
| 8 | **Check grid connectivity** | Score Drawer > Pipeline tab | `Transmission Line: Connected` or `None`. `Same PLN Region: Yes/No`. If disconnected, `New Line Cost ($/kW)` estimates the infrastructure gap. |
| 9 | **Export ranked list** | Bottom Panel > Ranked Table > Export | CSV with grid integration category, gap, and capacity for investment committee screening memo. |

### What gets exported
Ranked CSV of `invest_transmission`/`invest_substation` KEKs with investment signals, solar potential, and demand data.

### Walkthrough tour
In-app tour (select "DFI Infrastructure Investor"): Overview Map, Rank by Capacity, Check Grid Integration, Buildability Constraints, KEK Resource Tab, LCOE at Hurdle Rate, Grid Connection, Ready.

---

## Journey 3: Policy Maker

**Role:** BKPM/KESDM official or energy think-tank adviser (IESR, RMI Indonesia)
**Primary question:** Where should grid infrastructure investment be prioritized to unlock solar potential at KEKs?

### Steps

| # | Action | Component | What to look for |
|---|--------|-----------|-----------------|
| 1 | **Scan action flag distribution** | Map View | Spatial clustering of flags. If `not_competitive` KEKs cluster in one region, it's a system-level grid problem, not site-specific. |
| 2 | **Identify invest_transmission vs. invest_substation** | Bottom Panel > Ranked Table | Filter by these flags. V3 tells you exactly what's missing. Transmission = KEK far from grid. Substation = solar far from grid. The policy question: should RUPTL adjust? |
| 2b | **Size the grid investment** | Score Drawer > Pipeline tab | For `invest_substation`/`invest_transmission` KEKs, note `New Line Cost ($/kW)` and `Available Capacity (MVA)`. The ratio (MW solar unlocked / $M grid investment) is the policy efficiency metric. |
| 3 | **Check RUPTL pipeline** | Bottom Panel > RUPTL Context tab | Stacked area chart of planned MW by grid region. Flat regions = low grid improvement expected by 2030. |
| 4 | **Find plan_late KEKs** | Bottom Panel > Ranked Table | Filter action flag to `plan_late`. These KEKs have grid improvement coming but after 2030. Recommend RUPTL acceleration. |
| 5 | **Check BPP economics** | Bottom Panel > Ranked Table | Toggle benchmark to BPP (Assumptions Panel). Sort by gap. Where solar undercuts BPP, the economic case for enabling procurement is self-evident. |
| 6 | **Model concessional finance** | Assumptions Panel > WACC slider | Set WACC to 8%. Count how many KEKs flip to `solar_now`. This is the case for concessional finance or WACC de-risking instruments. |
| 7 | **Check GEAS allocation** | Score Drawer > Demand tab | `GEAS Green Share (%)` shows how much of 2030 demand GEAS-allocated solar could cover. High values = GEAS is a viable policy lever. |
| 8 | **Drill into top candidates** | Score Drawer > Pipeline tab | Review grid upgrade plans, substation capacity traffic light, connectivity status, RUPTL summary text. |
| 9 | **Export for policy brief** | Bottom Panel > Ranked Table > Export | CSV filtered to plan_late and investment KEKs for RUPTL review or KEK development strategy. |

### What gets exported
Ranked table CSV filtered by `grid_integration_category`. Screenshots of map and RUPTL chart for presentation slides.

### Walkthrough tour
In-app tour (select "Policy Maker"): Action Flag Distribution, RUPTL Pipeline, Plan Late KEKs, Concessional Finance Case, GEAS Allocation, KEK Pipeline Detail, Export for Policy Brief, Ready.

---

## Journey 4: IPP / Solar Developer

**Role:** Solar IPP developer (ACEN, Vena Energy, local developer) selling to PLN via PPA
**Primary question:** Where are the strongest solar-to-BPP economics, and where should we pre-position for PLN procurement?

### Steps

| # | Action | Component | What to look for |
|---|--------|-----------|-----------------|
| 1 | **Rank by capacity** | Bottom Panel > Ranked Table | Sort `Capacity (MWp)` descending. IPP threshold: >= 30 MWp. Below this, project economics are marginal. |
| 2 | **Filter to actionable sites** | Bottom Panel > Ranked Table > Filter | Filter action flag to `solar_now` or `invest_resilience`. These are sites where the PPA pitch is straightforward. |
| 3 | **Check grid readiness** | Bottom Panel > Ranked Table | Look at `Grid Integration` column. `grid_ready` or `within_boundary` = low connection cost. `invest_transmission`/`invest_substation` = needs infrastructure. |
| 4 | **Build the economic case** | Assumptions Panel > Benchmark toggle | Switch to BPP mode. Sort by gap. Where `Gap (%)` is negative, solar would reduce PLN's cost of supply. This is the argument for procurement. |
| 5 | **Review substation capacity** | Score Drawer > Pipeline tab | Can the local substation absorb your project output? Check capacity traffic light and `Available Capacity (MVA)`. If red, consider downsizing to match existing capacity or factor in upgrade cost. |
| 5b | **Size the project** | Score Drawer > Resource tab | Check `Max Capacity (MWp)` vs. substation available capacity. If max capacity exceeds substation headroom, the project may need to downsize or fund a substation upgrade. Export CF values to compute LCOE in your own financial model at your exact CAPEX. *(Future: capacity slider with LCOE curve, see TODOS.md M16)* |
| 6 | **Assess buildability** | Score Drawer > Resource tab | Check buildable area (ha), PVOUT quality, and constraint type. `slope`/`unconstrained` = low risk. `peat`/`kawasan_hutan` = high risk. `agriculture` = negotiation. |
| 7 | **Confirm on Quadrant Chart** | Bottom Panel > Quadrant tab | Visually verify your shortlisted KEKs sit in the green "Solar Now" zone at WACC=10%. |
| 8 | **Deep dive top 3-5** | Score Drawer (all tabs) | **Resource:** PVOUT, solar site distance. **LCOE:** bands at your target WACC. **Demand:** 2030 estimate. **Pipeline:** grid connectivity, RUPTL context. |
| 9 | **Export** | Bottom Panel > Ranked Table > Export | Top 10 regions CSV for BD pipeline tracker or PLN/ESDM engagement. |

### What gets exported
Ranked table CSV (top 10 sites) for BD pipeline tracker. KEK Scorecard details for PLN engagement deck.

### Walkthrough tour
In-app tour (select "IPP / Solar Developer"): Rank by Capacity, Filter Actionable Sites, Sort by Demand, Check Grid Integration, Buildability Risk, Quadrant Confirmation, KEK Deep Dive, Ready.

---

## Journey 5: Industrial Investor / KEK Tenant

**Role:** Site selection manager, industrial manufacturer or smelter operator
**Primary question:** Which KEK offers the lowest risk for electricity cost and reliability over the next 10-15 years?

*No in-app walkthrough tour for this persona (4 tours implemented; this persona's journey is simpler).*

### Steps

| # | Action | Component | What to look for |
|---|--------|-----------|-----------------|
| 1 | **Understand the baseline** | — | All KEKs pay the same PLN I-4 tariff today ($63/MWh). The differentiation is about **risk and trajectory**, not current price. |
| 2 | **Check BPP vs. tariff gap** | Assumptions Panel > Benchmark toggle (BPP) | KEKs in high-BPP regions are more exposed to future tariff adjustments. PLN's subsidy burden is unsustainable where BPP significantly exceeds tariff. |
| 3 | **Check grid reliability proxies** | Score Drawer > Pipeline tab | Substation distance, capacity traffic light, connectivity status. Continuous-process industries (smelters, chemicals, data centers) need strong grid. KEKs close to large substations offer better reliability. |
| 4 | **Assess green credentials** | Score Drawer > Demand tab | `GEAS Green Share (%)` shows the renewable trajectory. ESG-conscious manufacturers need credible green pathways. `grid_ready` KEKs near strong solar resource are the best bet. |
| 5 | **Check plan_late flag** | Bottom Panel > Ranked Table | Filter to see `plan_late` KEKs. An industrial investor committing to a 15-year facility needs confidence that grid capacity keeps pace. |
| 6 | **Compare across KEKs** | Bottom Panel > Ranked Table | Sort by grid integration, BPP, green share. Build a comparison matrix of risk factors. |
| 7 | **Export comparison matrix** | Bottom Panel > Ranked Table > Export | CSV ranked by risk factors (BPP gap, substation proximity, green share, plan_late) for site selection decision. |

### What gets exported
Comparison matrix CSV for site selection team. Screenshots of grid integration map for management presentation.

---

## Score Drawer Tab Reference

When you click a KEK (map marker or table row), the Score Drawer slides in with 6 tabs:

### Info
- KEK type, category, area (ha), province, grid region, developer, legal basis, estimated 2030 demand (GWh).

### Resource
- PVOUT at centroid and best within 50km (kWh/kWp/yr), capacity factor (%), buildable area (ha), max capacity (MWp), nearest substation name and distance (km).

### LCOE
- LCOE low/mid/high ($/MWh), grid-connected LCOE (if available), connection cost ($/kW), I-4 tariff cost ($/MWh), gap vs tariff (%), BPP ($/MWh), gap vs BPP (%).

### Demand
- 2030 demand estimate (GWh), GEAS green share (%), carbon breakeven ($/tCO2).

### Pipeline
- Grid region, grid upgrade planned (bool), grid integration category.
- **Substation capacity:** traffic light (green/yellow/red/unknown), available capacity (MVA), KEK-to-substation distance, solar-to-substation distance.
- **Grid connectivity:** transmission line connected (yes/no), same PLN region (yes/no), inter-substation distance (km), new line cost ($/kW) if needed.
- RUPTL summary text.

### Flags
- All 8 action flags listed. Active flag highlighted with explanation. Inactive flags shown muted. Grid cost proxy, BPP, project viable status.

---

## Assumptions Panel Reference

### Summary block (always visible)
Three cards showing current WACC %, CAPEX ($/kW), and Lifetime (years).

### WACC slider
Single slider with named marks: 4% (DFI Concessional), 8% (De-risked), 10% (Base Case), 14% (Equity Premium), 20% (Ceiling).

### Tier 1: Core assumptions
CAPEX, Lifetime, Fixed O&M, Connection cost per km, Grid connection fixed cost, BESS CAPEX, Land cost, Substation utilization, IDR/USD rate.

### Tier 2: Advanced (accordion)
Additional cost parameters.

### Tier 3: Flag thresholds (accordion)
PVOUT threshold, Plan-late threshold, GEAS threshold, Resilience gap %, Min viable capacity (MWp), Reliability threshold.

### Benchmark toggle
Two-button switch: **I-4/TT Tariff** (default, $63/MWh uniform) vs. **Regional BPP** ($57-133/MWh by region). Switching recomputes all gap calculations, action flags, and the Quadrant Chart Y-axis.

### Reset to defaults
Resets all sliders to their default values.
