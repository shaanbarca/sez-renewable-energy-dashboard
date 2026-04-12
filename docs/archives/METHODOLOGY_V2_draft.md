# METHODOLOGY V2 — Grid-Connected Solar Thesis

**Status:** Draft for review. Does not replace `METHODOLOGY.md` yet.
**Date:** 2026-04-09
**Author:** Shaan Barca

---

## Table of Contents

1. [Motivation: Why the Remote Captive Thesis Is Flawed](#motivation-why-the-remote-captive-thesis-is-flawed)
2. [Revised Siting Scenarios](#revised-siting-scenarios)
3. [Three-Point Proximity Analysis](#three-point-proximity-analysis)
4. [Revised LCOE Formulas](#revised-lcoe-formulas)
5. [Revised Action Flags](#revised-action-flags)
6. [Revised Competitive Gap](#revised-competitive-gap)
7. [DFI Grid Infrastructure Investment Model](#dfi-grid-infrastructure-investment-model)
8. [What Remains Valid from V1](#what-remains-valid-from-v1)
9. [What Changes from V1](#what-changes-from-v1)
10. [Persona Impact Analysis](#persona-impact-analysis)

---

## Motivation: Why the Remote Captive Thesis Is Flawed

### The V1 assumption

The original methodology assumed KEKs could build **remote captive solar plants** connected by a **private gen-tie transmission line** of up to 50 km. The model added ~$400/kW in gen-tie and substation infrastructure costs (50 km × $5/kW-km + $150/kW substation works) to the solar CAPEX, plus a $5–15/MWh transmission lease operating cost.

### Why this doesn't work

Research into global precedents reveals that **no remote captive solar plant with a dedicated private gen-tie of 50 km exists anywhere in the world** — not in Indonesia, not in India (the most mature captive solar market), not in any other jurisdiction.

**The economics don't support it:**

| Cost component | Estimate |
|---|---|
| 50 km transmission line | ~$25–30M (at ~$1M/mile) |
| Step-up substation (generation end) | ~$5–10M |
| Step-down substation (load end) | ~$5–10M |
| Land acquisition / easements for 50 km corridor | Variable, potentially $5M+ |
| **Total** | **~$40–55M** for a single consumer |

This infrastructure cost rivals or exceeds the solar plant itself for typical captive-scale projects (20–100 MWp).

**What actually exists globally:**

- **On-site / behind-the-meter captive solar** — plant within or immediately adjacent to the industrial facility. Common worldwide.
- **Grid-wheeled captive solar (India model)** — plant located remotely but power is transmitted through the state utility's existing grid infrastructure via open access wheeling. The plant is "financially captive" but not "physically captive." India has hundreds of these arrangements, but they rely on the grid, not private lines.
- **IPP → utility PPA** — the dominant model globally. Developer builds solar, sells to the utility (PLN in Indonesia's case), utility delivers to consumers through its grid.

**Indonesia-specific context:**

- **IMIP Morowali**, Indonesia's largest captive power complex (nickel smelters, 5+ GW coal), builds power plants **inside** the industrial park, not 50 km away.
- PLN has historically **rejected all wheeling requests** in practice, despite Permen ESDM No. 1/2015 legally authorizing it.
- The 2023–2024 renewable energy regulations are pushing toward more open grid access, but implementation remains uncertain.
- IPPs that build transmission lines to connect to PLN's grid typically **transfer ownership to PLN** post-commissioning (Permen ESDM No. 27/2017).

### The revised thesis

> **The realistic model for delivering cheap solar electricity to KEKs is through PLN's grid — not through private infrastructure. The dashboard answers: "Where do good solar sites, grid infrastructure, and industrial demand overlap, and what grid investment is needed to connect them?"**

This reframes the dashboard from a **captive solar feasibility tool** to a **grid-solar integration planning tool** — serving policymakers, IPPs, DFIs, and industrial investors.

### Limitations and key assumptions

This methodology rests on several assumptions that should be understood by all users:

**1. Grid-connected solar requires PLN partnership.**

The grid-connected solar scenario assumes PLN is willing to procure solar power and deliver it to KEK regions through its grid. Today, PLN's procurement priorities are shaped by existing long-term contracts (including coal take-or-pay agreements), system planning constraints, and evolving government mandates on renewable energy targets.

The dashboard is most useful when read as: *"If solar procurement is enabled in this region, here is what the economics look like."*

For policymakers, this framing highlights where enabling solar procurement would yield the greatest economic benefit — information that can inform RUPTL planning, renewable energy target discussions, and procurement reform priorities.

**2. BPP data is incomplete.**

Regional BPP (Biaya Pokok Penyediaan — PLN's true cost of supply) is the correct benchmark for IPP competitiveness, but published BPP data is not available for all grid regions. Where BPP is unavailable, the dashboard falls back to the I-4 industrial tariff as a conservative proxy.

Importantly, the I-4 tariff is subsidized below BPP in most regions — meaning PLN is currently supplying electricity to industrial consumers at a loss in those regions. This subsidy gap is itself a policy-relevant insight: regions where PLN's supply cost significantly exceeds the tariff are regions where cheaper solar generation could reduce PLN's financial burden, creating a natural alignment between PLN's interests and solar procurement.

**3. Connection costs are highly site-specific.**

Land acquisition, permitting, terrain, and local construction costs vary enormously across Indonesia's 25 KEK locations. Rather than assert fixed costs, the dashboard makes connection cost parameters **user-adjustable inputs** with wide ranges (see Revised LCOE Formulas section). Users should apply local knowledge when evaluating specific sites.

**4. The grid-connected solar scenario is forward-looking.**

Today, within-boundary (on-site captive solar) is the most bankable scenario because it requires no PLN cooperation. The grid-connected solar scenario represents the policy direction signaled by recent regulations (Permen ESDM No. 7/2024) and becomes increasingly realistic as renewable procurement frameworks mature.

The dashboard presents both scenarios so users can assess:
- **Current opportunities** — within-boundary captive solar (no PLN dependency)
- **Future potential** — grid-connected solar (requires PLN procurement reform)

---

## Revised Siting Scenarios

V1 had two scenarios: `within_boundary` (solar inside KEK) and `remote_captive` (solar 50 km away, private gen-tie). V2 replaces `remote_captive` with `grid_connected_solar`.

| Aspect | `within_boundary` | `grid_connected_solar` |
|---|---|---|
| **Description** | Solar plant inside KEK boundary, behind-the-meter captive | Solar farm connects to nearest PLN substation, sells to PLN via PPA |
| **PVOUT source** | `pvout_centroid` | `pvout_buildable_best_50km` |
| **Who builds it** | KEK tenant or on-site IPP | Independent IPP |
| **Who buys the power** | KEK tenant directly (no PLN) | PLN (via PPA), then PLN delivers to KEK |
| **Grid infrastructure needed** | None — internal distribution only | Solar-to-substation connection (typically <5 km) |
| **Cost to model** | Base LCOE only | Base LCOE + short grid connection cost |
| **PLN involvement** | None | Central — PLN is the offtaker and deliverer |
| **KEK tenant's cost** | Solar LCOE (direct) | PLN I-4 tariff or negotiated PPA rate |

### Within-boundary solar: capacity and viability

V1 computed `max_captive_capacity_mwp` from buildable area **within 50 km** of the KEK — but this is the remote resource potential, not the on-site potential. For `within_boundary` solar, what matters is how much capacity fits **inside the KEK polygon itself**.

V2 adds a new metric: **`within_boundary_capacity_mwp`** — estimated from the KEK polygon area, discounted for built-up land, roads, and setbacks. This is necessarily rough (satellite land-use classification, not site surveys), but gives a screening estimate.

**Viability thresholds differ by scenario:**

| Scenario | Minimum viable capacity | Rationale |
|---|---|---|
| `within_boundary` | **0.5 MWp** (500 kW) | Indonesian regulatory floor: installations >500 kW require an IUPTLS license (Permen ESDM No. 11/2021), signaling a "real project." Below 500 kW, only a report to MEMR/governor is needed — still viable, but more akin to building-level rooftop than a dedicated solar project. |
| `grid_connected_solar` | **20 MWp** (user-adjustable, default from V1) | Utility-scale threshold: fixed development costs (permitting, grid connection studies, legal, engineering) make smaller projects uneconomical for an IPP selling to PLN. DFI investors typically screen ≥ 33 MWp. |

The 0.5 MWp within-boundary threshold is intentionally low — the economics of on-site captive solar work at almost any scale because there are no grid connection costs, no transmission losses, and no PLN involvement. A factory roof with 500 kW of panels directly offsets the tenant's electricity bill. The dashboard should not screen out these opportunities with a utility-scale threshold.

Both thresholds are **user-adjustable** in the dashboard.

### Key insight: separation of producer and consumer economics

Under V1, the KEK tenant's electricity cost was modeled as the captive solar LCOE (including gen-tie). Under V2, the economics split:

1. **IPP economics**: "Can I build solar here and sell profitably to PLN?" → solar LCOE vs. regional BPP
2. **KEK tenant economics**: "What will my electricity cost from PLN?" → I-4 tariff, grid reliability, future rate trajectory
3. **Policy economics**: "Where should grid investment go to enable cheap solar?" → three-point proximity analysis

---

## Three-Point Proximity Analysis

V1 measured one distance: KEK centroid to nearest PLN substation. V2 introduces a **three-point proximity model** that captures the full solar-to-grid-to-KEK chain.

### Three geographic points

| Point | Source | Description |
|---|---|---|
| **A** — Best solar site | `fct_kek_resource` (NEW: `best_solar_site_lat`, `best_solar_site_lon`) | Location of the highest-PVOUT buildable pixel within 50 km of the KEK |
| **B** — Nearest PLN substation | `data/substation.geojson` (existing) | Nearest operational PLN substation to point A or C (may differ) |
| **C** — KEK centroid | `dim_kek` (existing) | Geographic center of the KEK polygon |

### Distance matrix

For each KEK, compute:

- **d(A, B_solar)**: distance from best solar site to the nearest substation to that solar site
- **d(C, B_kek)**: distance from KEK centroid to the nearest substation to the KEK (existing `dist_to_nearest_substation_km`)
- **d(A, C)**: direct distance from solar site to KEK (for reference)

Note: B_solar and B_kek may be different substations. The solar site's nearest substation is not necessarily the KEK's nearest substation.

### Grid integration categories

| Category | Condition | Meaning | Cost implication |
|---|---|---|---|
| `within_boundary` | Has operational substation inside KEK polygon | Solar can be built on-site, no grid needed | Lowest — base LCOE only |
| `grid_ready` | d(A, B_solar) < threshold AND d(C, B_kek) < threshold AND B_solar capacity ≥ minimum | Substation near both solar and KEK with sufficient capacity — grid can absorb and deliver | Low — short connection + existing grid |
| `invest_transmission` | d(A, B_solar) < threshold AND d(C, B_kek) ≥ threshold | Solar site CAN reach a substation, but the KEK is far from grid infrastructure. Action: **build transmission line from substation area to KEK**. | Medium — transmission line construction |
| `invest_substation` | d(C, B_kek) < threshold AND d(A, B_solar) ≥ threshold | KEK IS near a substation, but the best solar site is far from any substation. Action: **build a new substation or connection point near the solar farm**. | Medium — substation construction near solar |
| `grid_first` | Both distances > thresholds AND no nearby substations with meaningful capacity | No grid infrastructure near solar or KEK — major grid expansion needed before solar is relevant | High — systemic grid investment required |

**Substation capacity check:** Distance alone is insufficient. A substation 2 km from a solar site but rated at 20 MVA cannot absorb a 50 MWp solar farm's output. The grid integration category incorporates a capacity check:

- `nearest_substation_to_solar_capacity_mva` is compared against `max_captive_capacity_mwp` (the buildable solar potential)
- **Rule of thumb:** a substation can absorb solar injection up to roughly 70–80% of its rated capacity (to maintain voltage stability and reserve margin). If the solar potential exceeds this, the substation would require upgrade — pushing the category toward `invest_transmission` or `invest_substation` even if distance is short.
- Where substation capacity data is unavailable or unreliable (some entries in `substation.geojson` have normalized values from inconsistent source formats), the dashboard flags this as **"capacity unverified"** and relies on distance alone.

### Threshold values (user-adjustable)

| Parameter | Default | Range | Rationale |
|---|---|---|---|
| `SOLAR_TO_SUBSTATION_THRESHOLD_KM` | 5.0 km | 2–10 km | V3.1: Tightened from 10km. Source: YSG Solar (ideal ≤ 2 miles / 3.2 km), IFC Utility-Scale Solar Guide (max 5 miles / 8 km). Gen-tie costs of ~$1–3M/mile make longer connections uneconomic. |
| `KEK_TO_SUBSTATION_LOW_THRESHOLD_KM` | 15.0 km | 5–30 km | PLN distribution reach to industrial estates. Indonesia's grid density varies dramatically between Java (dense) and eastern islands (sparse); adjust accordingly. |
| `SUBSTATION_MIN_CAPACITY_MVA` | 30 MVA | 10–100 MVA | Minimum substation capacity to qualify as a viable grid injection point. Lower for small solar projects; higher for large-scale development. |

These thresholds are user-adjustable in the dashboard. **No universal "correct" value exists** — the appropriate threshold depends on the specific region's grid topology, terrain, and regulatory environment. The dashboard's value is in allowing users to test sensitivity across these ranges.

### V3.1: Substation capacity utilization check

Distance alone is insufficient. A substation may be physically nearby but already loaded near capacity. V3.1 adds a **capacity utilization check**:

```
available_capacity_mva = rated_capacity_mva × (1 - utilization_pct)
```

- `utilization_pct` defaults to 65% (user-adjustable, range 30–95%)
- If `solar_capacity_mwp > available_capacity_mva`, the substation needs an upgrade, producing `invest_substation` even if physically near
- Proxies for smarter defaults (future): night-time light intensity (VIIRS/DMSP), industrial load presence, PLN RUPTL upgrade flags

**Traffic light display:**

| Status | Criteria |
|---|---|
| Green | Available capacity > 2× solar potential |
| Yellow | Available capacity 0.5–2× solar potential |
| Red | Available capacity < 0.5× solar potential (upgrade needed) |
| Unknown | Capacity data unavailable |

Disclaimer: "Actual available capacity requires a formal PLN grid study."

### V3.1: Inter-substation connectivity check

When B_solar and B_kek are different substations, the model checks whether an existing transmission line connects them.

**Data source:** `data/pln_grid_lines.geojson` — 1,595 PLN transmission lines with geometry and voltage (`tegjar` kV). Voltage distribution: 150 kV (1,286 lines), 500 kV (86), 275 kV (34), 70 kV (177).

**Geometric check:** For each pair of substations, the pipeline checks if ANY grid line geometry passes within 2 km of BOTH substations (using shapely distance calculations with approximate degree-to-km conversion at Indonesian latitudes).

**Fallback:** If no grid line geometrically connects the substations, the PLN region (`regpln`) field is used as a secondary proxy. Substations in the same PLN region are assumed connected through the regional 150 kV mesh.

**Connectivity output:**
- `line_connected` — True if a grid line geometrically passes near both substations
- `same_grid_region` — True if both substations share the same `regpln`
- `inter_substation_connected` — True if `line_connected OR same_grid_region`

If `inter_substation_connected == False`, the category becomes `invest_transmission` or `grid_first` depending on other conditions.

### V3.1: Infrastructure cost layers

Three layers of grid infrastructure cost affect the economics of connecting solar to a KEK:

| # | Cost | Description | Who pays | Model status |
|---|---|---|---|---|
| 1 | **Gen-tie** (solar → B_solar) | Short MV/HV line from solar farm to nearest substation | Developer/IPP | ✅ `grid_connection_cost_per_kw()` — dist × $5/kW-km + $80/kW fixed |
| 2 | **New transmission line** (B_solar → B_kek) | If no existing line connects the two substations | PLN / DFI | ✅ V3.1: `new_transmission_cost_per_kw()` — dist × $1.25M/km ÷ solar capacity |
| 3 | **Substation upgrade** | If substation lacks capacity for solar injection | PLN / DFI | ⚠️ Flagged via capacity assessment; cost estimation deferred |

Sources: YSG Solar (gen-tie distances), IFC Utility-Scale Solar Guide (cost ranges), docs/methodology_testing.md (research notes).

### Data requirement

V1 stored only the PVOUT value of the best buildable site, not its coordinates. V2 requires the pipeline to also record **`best_solar_site_lat`** and **`best_solar_site_lon`** — the geographic coordinates of the pixel where `pvout_buildable_best_50km` was found. This is a minor extension to `build_fct_kek_resource.py`: the raster search already iterates pixels and tracks the max; it just needs to also record the argmax location.

Resolution limitation: the Global Solar Atlas GeoTIFF is ~1 km resolution, so solar site coordinates are accurate to approximately ±500 m. This is sufficient for screening-level substation proximity analysis.

---

## Revised LCOE Formulas

### Within-boundary LCOE (unchanged)

```
LCOE_wb = (CAPEX_solar × CRF + FOM) / (CF × 8.76)
```

Where:
- `CRF = WACC × (1 + WACC)^n / ((1 + WACC)^n - 1)` — capital recovery factor
- `CF = PVOUT_centroid / 8760` — capacity factor
- `CAPEX_solar` in USD/kW (default $960/kW from ESDM Technology Catalogue 2023)
- `FOM` = fixed O&M in USD/kW/yr
- `n` = lifetime in years (default 25)

### Grid-connected solar LCOE (replaces remote captive)

```
LCOE_gc = (CAPEX_solar + C_connection + C_land) × CRF + FOM) / (CF × 8.76)
```

Where:
- `CF = PVOUT_buildable_best_50km / 8760`
- `C_connection = dist_solar_to_substation × C_per_kw_km + C_fixed`
- `C_per_kw_km` = connection cost per kW per km (**user-adjustable**, see below)
- `C_fixed` = grid interconnection fixed cost (**user-adjustable**, see below)
- `dist_solar_to_substation` = distance from solar site to nearest PLN substation (km)
- `C_land` = land acquisition cost in USD/kW (**user-adjustable**, default $45/kW)

### Land acquisition cost (V3)

For grid-connected solar, the IPP must acquire land for the solar farm. Within-boundary solar uses existing KEK land (zero land cost).

| Parameter | Default | Range | Derivation |
|---|---|---|---|
| `LAND_COST_USD_PER_KW` | $45/kW | $0–300/kW | $3/m² × 15,000 m²/MW = $45,000/MW = $45/kW |

Land costs in Indonesia vary enormously — from near-zero on government-owned or marginal land to $10+/m² on productive agricultural land near population centers. The default assumes $3/m² (reasonable for semi-rural Indonesia) and a land requirement of ~15,000 m²/MW (1.5 ha/MW, typical for fixed-tilt solar in tropical latitudes).

Users should adjust upward for sites near Java's populated north coast or downward for remote eastern Indonesia locations.

### Connection cost parameters (user-adjustable)

Connection costs vary significantly by location due to terrain, land acquisition difficulty, permitting requirements, and local construction costs. Rather than assert fixed values, these are **dashboard inputs with default values and wide ranges**:

| Parameter | Default | Range | What it covers |
|---|---|---|---|
| `CONNECTION_COST_PER_KW_KM` | $5/kW-km | $2–15/kW-km | Transmission/distribution line from solar plant to PLN substation. Lower end: flat terrain, existing right-of-way. Upper end: mountainous terrain, difficult land acquisition, HV line required. |
| `GRID_CONNECTION_FIXED_PER_KW` | $80/kW | $30–200/kW | Grid interconnection works at the PLN substation (switchgear, protection, metering). Lower end: simple MV connection, cooperative utility. Upper end: HV connection requiring substation expansion, complex permitting. |

**Note on land costs:** Land acquisition for transmission corridors in Indonesia is notoriously variable — from negligible (government-owned land near industrial zones) to prohibitive (dense agricultural or contested land). Users with local knowledge should adjust `CONNECTION_COST_PER_KW_KM` upward for sites where land acquisition is expected to be difficult.

### Why V2 connection costs differ from V1's gen-tie costs

| Component | V1 (remote captive) | V2 (grid connected) | Reason |
|---|---|---|---|
| Distance | Up to 50 km (solar to KEK) | Typically <10 km (solar to nearest substation) | Solar connects to nearest grid injection point, not to distant consumer |
| Fixed cost | $150/kW (two substations: generation + load end) | $30–200/kW (one interconnection point) | Only need connection works at the grid injection point; the solar plant's step-up transformer is already in CAPEX |
| Transmission lease | $5–15/MWh (ongoing operating cost) | $0 (removed) | Power is sold to PLN at the substation; delivery to KEK is PLN's system cost, reflected in BPP/tariff |

### Example: 5 km solar-to-substation connection (at defaults)

```
Connection cost = 5 km × $5/kW-km + $80/kW = $105/kW
Effective CAPEX = $960 + $105 = $1,065/kW
```

At pessimistic end (difficult terrain, 8 km):
```
Connection cost = 8 km × $10/kW-km + $150/kW = $230/kW
Effective CAPEX = $960 + $230 = $1,190/kW
```

Users should test sensitivity across the parameter range to understand how connection costs affect competitiveness for specific KEK locations.

### KEK tenant's electricity cost

Under V2, the KEK tenant does **not** pay the solar LCOE directly (unless using `within_boundary` captive solar). For `grid_connected_solar`, the tenant pays the **PLN I-4 industrial tariff** (currently ~$63/MWh or Rp 1,035/kWh for the I-4/TT category).

The relevant comparison for the tenant is:
- Current PLN tariff vs. future tariff trajectory
- Grid reliability in this region
- Whether increased solar penetration in the regional grid will lower future BPP

The relevant comparison for the **IPP** is:
- Solar LCOE vs. regional BPP (if solar < BPP, PLN has economic incentive to procure)

---

## Revised Action Flags

V1 flags were designed around the captive solar decision: "should this KEK build captive solar?" V2 reframes flags around the grid-solar integration question: "what needs to happen for this KEK to benefit from cheap solar?" V3 splits the generic `invest_grid` into actionable sub-flags and replaces the flat firming adder with a proper BESS storage model.

### Flag definitions (V3)

| Flag | Condition | Meaning | Primary audience |
|---|---|---|---|
| **`solar_now`** | `grid_ready` category AND solar LCOE < regional BPP AND PVOUT ≥ threshold AND NOT invest_transmission AND NOT invest_substation | Good solar resource, grid infrastructure in place, economics favorable. An IPP can build now and PLN should procure. | IPP, Policy Maker |
| **`invest_transmission`** | `invest_transmission` grid category AND solar_attractive | Solar site CAN reach a substation, but the KEK is far from grid infrastructure. Action: **build transmission line from substation to KEK**. | Policy Maker, DFI |
| **`invest_substation`** | `invest_substation` grid category AND solar_attractive | KEK IS near a substation, but the best solar site is far from any substation. Action: **build a new substation or connection point near the solar farm**. | Policy Maker, DFI |
| **`grid_first`** | `grid_first` category | No solar connectivity and no nearby grid infrastructure. Major grid expansion needed before solar is relevant. | Policy Maker |
| **`invest_battery`** | solar_attractive AND reliability requirement ≥ 0.75 | Solar can contribute but the KEK's industrial processes require high reliability. Battery storage needed alongside solar. Cost computed from BESS LCOE model (see below). | IPP, KEK Tenant |
| **`invest_resilience`** | solar_attractive AND LCOE within 0-20% of grid cost AND reliability_req ≥ 0.75 | Solar is near grid parity. Investing now builds resilience against future grid cost increases. | IPP, Policy Maker |
| **`plan_late`** | RUPTL post-2030 share ≥ 60% | Most planned grid capacity additions in this region are post-2030. Grid infrastructure to support solar integration won't arrive on current timeline. | Policy Maker, DFI |
| **`not_competitive`** | Solar LCOE > grid cost by wide margin | Solar is not economical under current assumptions. | All |

### Priority ordering (V3)

When multiple flags apply, the dashboard displays the **primary** flag in this priority order:

1. `solar_now` (highest — actionable now)
2. `invest_transmission` (actionable: build transmission)
3. `invest_substation` (actionable: build substation)
4. `grid_first` (requires systemic investment)
5. `invest_battery` (solar works, needs storage)
6. `invest_resilience` (near parity, invest for resilience)
7. `plan_late` (timeline risk)
8. `not_competitive` (solar LCOE > BPP even with grid access)

### Battery Energy Storage System (BESS) model (V3)

V2 used a flat firming adder ($6/$11/$16 per MWh low/mid/high) for KEKs with high reliability requirements. V3 replaces this with a proper **BESS storage cost model** derived from battery economics.

**Formula:**

```
bess_storage_adder = (BESS_CAPEX_per_kWh × sizing_hours × CRF_bess + FOM_bess_adj) / (CF_solar × 8760 / 1000)
```

Where:
- `BESS_CAPEX_per_kWh` = battery installed cost (default $250/kWh, **user-adjustable** $100-500/kWh)
- `sizing_hours` = hours of battery per kW of solar capacity (default 2h)
- `CRF_bess` = capital recovery factor at WACC over battery lifetime (default 15 years)
- `FOM_bess_adj` = battery fixed O&M, adjusted for sizing ratio ($5/kW-yr × sizing/discharge ratio)
- `CF_solar` = solar capacity factor for this KEK

**Default parameters:**

| Parameter | Default | Range | Source |
|---|---|---|---|
| `BESS_CAPEX_USD_PER_KWH` | $250/kWh | $100–500/kWh | BNEF 2024 Asia utility-scale Li-ion |
| `BESS_DISCHARGE_HOURS` | 4.0h | — | Standard 4-hour system |
| `BESS_SIZING_HOURS` | 2.0h | — | Hours of battery per kW-solar for firming |
| `BESS_LIFETIME_YR` | 15 years | — | Li-ion warranty period |
| `BESS_FOM_USD_PER_KW_YR` | $5/kW-yr | — | Monitoring, HVAC, insurance |

**Result at defaults ($250/kWh, 2h sizing, 10% WACC, CF=0.18):** ~$43/MWh battery adder.

This is higher than the old flat $11/MWh adder because the old value was unrealistically low. Real battery storage for industrial reliability adds meaningful cost. The user-adjustable BESS CAPEX slider ($100-500/kWh) produces a range of ~$17-86/MWh, allowing users to explore how battery cost trajectories affect the economics.

**Solar + battery bundled LCOE:**
```
LCOE_with_battery = LCOE_solar + bess_storage_adder
```

### Comparison with V1/V2 flags

| V1/V2 Flag | V3 Equivalent | Change |
|---|---|---|
| `solar_now` | `solar_now` | Now excludes `invest_transmission` and `invest_substation` (must have full grid access) |
| `invest_grid` | `invest_transmission` + `invest_substation` | Split into two actionable sub-flags specifying WHAT to build |
| `grid_first` | `grid_first` | Unchanged |
| `firming_needed` | `invest_battery` | Renamed. Flat $11/MWh adder replaced with BESS LCOE model (~$43/MWh at defaults) |
| `invest_resilience` | `invest_resilience` | Unchanged |
| `plan_late` | `plan_late` | Unchanged |
| `not_competitive` | `not_competitive` | Unchanged |

---

## Revised Competitive Gap

### Two separate gap calculations

V1 had one gap: captive solar LCOE vs. PLN tariff (or BPP). V2 separates the IPP perspective from the KEK tenant perspective.

#### IPP gap: solar LCOE vs. regional BPP

```
gap_IPP = (LCOE_gc - BPP_region) / BPP_region × 100%
```

- **Negative gap**: solar is cheaper than PLN's cost of supply → PLN has economic incentive to procure via PPA
- **Positive gap**: solar is more expensive → needs policy support (feed-in tariff, carbon price) to be viable
- **BPP** (Biaya Pokok Penyediaan) = PLN's true cost of supply by grid region, not the subsidized tariff

**BPP fallback rule:** Where regional BPP data is not yet available, the dashboard uses the **I-4 industrial tariff** as a conservative proxy and flags the KEK with **`bpp_status: "estimated — BPP not yet sourced"`**. Since the I-4 tariff is subsidized below BPP in most regions, using the tariff as proxy means the IPP gap will appear *less* favorable than reality — this is deliberately conservative. When actual BPP data is sourced for a region, the flag updates to `"verified"` and the gap recalculates. The dashboard UI should clearly distinguish verified-BPP and estimated-BPP KEKs so users know which results to trust for decision-making.

#### KEK tenant gap: within-boundary solar vs. PLN tariff

```
gap_tenant = (LCOE_wb - Tariff_I4) / Tariff_I4 × 100%
```

This only applies to `within_boundary` captive solar. For `grid_connected_solar`, the tenant pays the PLN tariff regardless — the gap question is irrelevant from the tenant's perspective.

#### Carbon breakeven (unchanged)

```
P_carbon = (LCOE_gc - BPP_region) / EF_grid    [USD/tCO2]
```

Where `EF_grid` = grid emission factor (tCO2/MWh) from KESDM 2019 OM data.

Interpretation: the carbon price at which solar becomes cost-competitive with PLN's current generation mix. If the carbon breakeven is low (e.g., <$20/tCO2), solar is nearly competitive even without carbon pricing.

---

## DFI Grid Infrastructure Investment Model

This is a new analytical dimension not present in V1. It directly serves the reframed DFI persona.

### Background

Development Finance Institutions (ADB, World Bank, IFC, AIIB, JICA) regularly finance grid infrastructure in developing countries. This is not theoretical — it's a well-established investment category:

- **World Bank**: "Indonesia Power Transmission Development Project" — concessional loans to PLN for transmission expansion
- **ADB**: multiple PLN grid modernization loans across Java, Sulawesi, and Kalimantan
- **IFC**: blended finance facilities that pair grid investment with renewable energy procurement

### Investment instruments

| Instrument | How it works | Dashboard relevance |
|---|---|---|
| **Concessional loan to PLN** | DFI lends to PLN at below-market rates for transmission/substation construction | `invest_transmission` / `invest_substation` KEKs show where PLN needs grid investment |
| **Viability gap funding** | DFI covers the gap between infrastructure cost and what PLN can recover through tariffs | `grid_investment_needed_usd` estimates the gap |
| **Blended finance** | DFI funds the grid, private IPP funds the solar farm, PLN operates the connection | `solar_now` + `invest_transmission`/`invest_substation` KEKs are the co-investment opportunities |
| **Green bonds** | PLN issues bonds for renewable-enabling grid investment, DFI provides credit enhancement | Regional aggregation of grid-investment KEKs sizes the bond |

### Grid investment estimation

For each KEK in the `invest_transmission` or `invest_substation` category, the dashboard provides a rough order-of-magnitude grid investment estimate:

```
I_grid = d_gap × C_transmission_per_km + N_substations × C_substation
```

Where:
- `d_gap` = the missing link distance (either solar-to-substation or substation-to-KEK, whichever is the bottleneck)
- `C_transmission_per_km` is approximately $500K–1M/km for 150 kV transmission in Indonesia (source: PLN RUPTL cost benchmarks)
- `N_substations` = number of new substations needed (0, 1, or 2)
- `C_substation` is approximately $5–15M per 150/20 kV step-down substation

This is a screening estimate, not a bankable figure. Its purpose is to help DFIs identify the most cost-effective grid investment opportunities relative to the solar potential unlocked.

### Screening heuristic: solar potential per grid investment dollar

As a first-pass screening tool, the dashboard enables DFIs to rank KEK regions by **solar potential unlocked per dollar of grid investment**:

```
Screening ratio = Solar_capacity_unlocked_MWp / I_grid_USD_million
```

Where `Solar_capacity_unlocked_MWp` comes from the buildable area analysis. A high ratio means a small grid investment unlocks large solar potential.

**This is a screening heuristic, not a bankable investment metric.** A full DFI investment assessment would additionally require: demand certainty at the KEK (occupancy, tenant pipeline), PLN's financial health and tariff recovery outlook, environmental and social safeguard compliance, co-financing availability (is an IPP ready to build the solar side?), and sovereign/regulatory risk assessment. The dashboard provides the **first filter** — narrowing 25 KEKs to a shortlist worth deeper due diligence.

---

## What Remains Valid from V1

The following V1 components are **unchanged** and carry over directly:

| Component | File(s) | Notes |
|---|---|---|
| PVOUT extraction (centroid + best-50km) | `build_fct_kek_resource.py` | Just add coordinate tracking |
| Buildability filters (forest, peat, slope, land cover) | `buildability_filters.py`, `build_buildable_raster.py` | No change |
| Core LCOE formula (CRF-based) | `basic_model.py::lcoe_solar()` | Same function, unchanged |
| CRF computation | `basic_model.py` | No change |
| RUPTL pipeline extraction | `build_fct_ruptl_pipeline.py` | No change |
| Demand estimation | `build_fct_kek_demand.py` | No change |
| Grid cost proxy (BPP + I-4 tariff) | `build_fct_grid_cost_proxy.py` | No change |
| Grid emission factors | `build_fct_grid_cost_proxy.py` | No change |
| Carbon breakeven calculation | `basic_model.py` | Formula unchanged, input (BPP) may shift in importance |
| GEAS green share | `basic_model.py` | No change |
| Wind resource pipeline | `build_fct_kek_wind_resource.py`, `build_fct_lcoe_wind.py` | No change |
| KEK dimension table | `build_dim_kek.py` | No change |
| Technology cost extraction | `build_dim_tech_cost.py` | No change |

---

## What Changes from V1

| Change | V1 | V2/V3 | Affected files |
|---|---|---|---|
| Siting scenario | `remote_captive` (50km private gen-tie) | `grid_connected_solar` (solar→nearest substation) | `assumptions.py`, `build_fct_lcoe.py`, `basic_model.py`, `logic.py` |
| Gen-tie cost model | $5/kW-km + $150/kW fixed | $5/kW-km + $80/kW fixed (short connection) | `assumptions.py`, `basic_model.py` |
| Distance used | KEK-to-substation (for gen-tie length) | Solar-to-substation (for connection length) | `build_fct_substation_proximity.py` |
| Proximity analysis | 1-point (KEK→substation) | 3-point (solar→substation→KEK) | `build_fct_substation_proximity.py`, `build_fct_kek_resource.py` |
| Transmission lease | $5–15/MWh operating adder | Removed (PLN's system cost, in BPP) | `assumptions.py`, `build_fct_lcoe.py`, `logic.py` |
| Action flags | `solar_now`, `grid_first`, `firming_needed`, `invest_resilience`, `plan_late` | V3: `solar_now`, `invest_transmission`, `invest_substation`, `grid_first`, `invest_battery`, `invest_resilience`, `plan_late`, `not_competitive` (8 flags) | `basic_model.py`, `logic.py` |
| Grid integration category | Not present | V3: `within_boundary` / `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first` | `build_fct_substation_proximity.py` |
| Firming/battery model | Flat $6/$11/$16 adder | V3: BESS LCOE model from battery CAPEX ($250/kWh default, user-adjustable) → ~$43/MWh | `basic_model.py`, `logic.py`, `assumptions.py` |
| Land acquisition cost | Not modeled | V3: $45/kW default (grid-connected only), user-adjustable $0-300/kW | `assumptions.py`, `build_fct_lcoe.py`, `logic.py` |
| Competitive gap | Captive LCOE vs. tariff/BPP | Split: IPP gap (LCOE vs BPP) + tenant gap (within-boundary only) | `basic_model.py`, `logic.py` |
| Solar site coordinates | Not stored | `best_solar_site_lat`, `best_solar_site_lon` | `build_fct_kek_resource.py` |
| Within-boundary capacity | Not modeled (used 50km buildable area for all scenarios) | `within_boundary_capacity_mwp` from KEK polygon area | `build_fct_kek_resource.py` |
| Viability threshold | Single 20 MWp for all scenarios | 0.5 MWp for within-boundary, 20 MWp for grid-connected (both adjustable) | `assumptions.py`, `logic.py` |

### Constants deprecated or renamed

| V1 constant | V2/V3 replacement | Old default | New default | New range |
|---|---|---|---|---|
| `GENTIE_COST_PER_KW_KM` | `CONNECTION_COST_PER_KW_KM` | $5.0 | $5.0 | $2–15/kW-km |
| `SUBSTATION_WORKS_PER_KW` | `GRID_CONNECTION_FIXED_PER_KW` | $150.0 | $80.0 | $30–200/kW |
| `TRANSMISSION_LEASE_LOW_USD_MWH` | Deprecated | $5.0 | — | — |
| `TRANSMISSION_LEASE_MID_USD_MWH` | Deprecated | $10.0 | — | — |
| `TRANSMISSION_LEASE_HIGH_USD_MWH` | Deprecated | $15.0 | — | — |
| `FIRMING_ADDER_MID_USD_MWH` | `BESS_CAPEX_USD_PER_KWH` (V3) | $11.0 flat | $250/kWh (→~$43/MWh) | $100–500/kWh |
| — | `LAND_COST_USD_PER_KW` (V3 NEW) | — | $45.0 | $0–300/kW |
| — | `SOLAR_TO_SUBSTATION_LOW_THRESHOLD_KM` (NEW) | — | 10.0 | — |
| — | `KEK_TO_SUBSTATION_LOW_THRESHOLD_KM` (NEW) | — | 15.0 | — |

---

## Persona Impact Analysis

### Persona 1: Energy Economist (ADB/IFC analyst)

**Impact: LOW**

The Energy Economist's core workflow — comparing LCOE across KEK sites at various WACC rates — is unchanged for `within_boundary` solar. The main enhancement is the addition of `solar_vs_bpp_gap_pct` as a first-class metric, which strengthens policy brief arguments.

| Metric | V1 | V2 | Change |
|---|---|---|---|
| `lcoe_mid_usd_mwh` (within-boundary) | Primary | Primary | Unchanged |
| `solar_competitive_gap_pct` | vs. tariff or BPP | Split: IPP gap vs BPP, tenant gap vs tariff | Clearer framing |
| `carbon_breakeven_usd_tco2` | Present | Present | Unchanged |
| `solar_vs_bpp_gap_pct` | Implicit | First-class column | NEW — elevated |
| `lcoe_remote_captive_allin_usd_mwh` | Present | Replaced by `lcoe_grid_connected_usd_mwh` | Lower values (cheaper connection) |

**Journey change:** When presenting to development bank colleagues, the economist can now show a more credible model — "this is the realistic cost structure for grid-connected solar" rather than an unprecedented private gen-tie scenario.

### Persona 2: DFI Infrastructure Investor (was "DFI Investor")

**Impact: HIGH — persona fundamentally reframed**

V1 positioned this persona as screening captive solar projects with gen-tie infrastructure. This was unrealistic — no DFI has funded a 50 km private gen-tie for captive solar in Indonesia.

V2 reframes the DFI as an **infrastructure investor** — someone investing in the grid that connects solar supply to industrial demand.

| Metric | V1 | V2 | Change |
|---|---|---|---|
| `lcoe_remote_captive_allin_usd_mwh` | Primary screening metric | Removed | Was unrealistic |
| `siting_scenario` | Filter criterion | Replaced by `grid_integration_category` | More granular |
| `grid_integration_category` | Not present | Primary decision variable | NEW |
| `grid_investment_needed_usd` | Not present | Order-of-magnitude investment estimate | NEW |
| `solar_capacity_unlocked_mwp` | Present (as `max_captive_capacity_mwp`) | Elevated — used in ROI calculation | Reframed |
| `dist_solar_to_nearest_substation_km` | Not present | Key infrastructure gap metric | NEW |

**New user journey:**

1. Open dashboard → map color-coded by `grid_integration_category`
2. Filter to `invest_transmission` / `invest_substation` categories — these are the DFI opportunity set
3. Sort by `solar_capacity_unlocked_mwp / grid_investment_needed_usd` — highest solar ROI per infrastructure dollar
4. Drill into top candidates: check solar resource quality, KEK demand, RUPTL alignment
5. Export ranked list for internal investment committee review

**Investment instruments available:**
- Concessional loans to PLN for transmission/substation construction
- Viability gap funding where grid cost exceeds PLN's recoverable tariff revenue
- Blended finance: DFI funds grid, private IPP funds solar, PLN operates connection
- Green bonds for renewable-enabling grid investment with DFI credit enhancement

### Persona 3: Policy Maker (BKPM/KESDM)

**Impact: HIGH — elevated to primary persona**

V1 treated the policy maker as a secondary user interested in action flags and RUPTL context. V2 makes the policy maker the **primary audience** because the dashboard now directly answers their core question: "Where should grid infrastructure investment go to unlock cheap solar for industrial zones?"

| Metric | V1 | V2 | Change |
|---|---|---|---|
| Action flags | `solar_now`, `grid_first`, etc. | V3: `invest_transmission`, `invest_substation`, `invest_battery` (specific) | More actionable |
| `grid_integration_category` | Not present | Primary decision variable | NEW |
| RUPTL context | Secondary context | Directly tied to `plan_late` flag | Elevated |
| Three-point proximity | Not present | Map visualization of solar-grid-KEK gaps | NEW |
| `solar_vs_bpp_gap_pct` | Not explicit | Shows where solar reduces PLN system cost | NEW |

**New user journey:**

1. Open dashboard → map shows grid integration categories (color-coded)
2. Identify `invest_transmission` / `invest_substation` KEKs — where targeted infrastructure investment unlocks solar
3. Cross-reference with RUPTL pipeline — are grid upgrades already planned? (`plan_late` flag shows timeline risk)
4. Prioritize: KEKs where solar resource is strong + demand is high + grid gap is small (cheapest to fix)
5. Use `grid_investment_needed_usd` for budget planning discussions with PLN
6. Export for RUPTL review meeting or KEK development strategy presentation

**Policy levers the dashboard now illuminates:**
- Where to prioritize PLN grid expansion (RUPTL influence)
- Where to direct DFI infrastructure funding
- Which KEKs are "grid ready" for solar IPP development today
- Where carbon pricing would tip the economics

### Persona 4: IPP / Solar Developer (ACEN, Vena Energy, etc.)

**Impact: MEDIUM — reframed**

V1 had the IPP selling power directly to KEK tenants via captive PPA. V2 reframes the IPP as selling to PLN via PPA — the standard Indonesian model.

**Important context on IPP agency:** In Indonesia, IPPs do not independently choose where to build. PLN controls the procurement process — issuing tenders for specific regions based on RUPTL planning, negotiating PPAs, and allocating grid capacity. The dashboard is therefore **not** a site-selection tool in the direct sense. Instead, it serves IPPs in two ways:

1. **Pre-positioning:** Identifying regions where solar economics are strongest, so the IPP can prepare (secure land options, complete pre-feasibility studies) ahead of PLN procurement tenders.
2. **Advocacy:** Building the economic case for PLN to prioritize solar procurement in specific regions. An IPP can use the dashboard's data to support proposals to ESDM or PLN showing that solar in a given grid region would reduce BPP — aligning the IPP's commercial interest with PLN's cost-reduction mandate.

This is a collaborative framing: the dashboard helps IPPs demonstrate value to PLN and policymakers, not circumvent the procurement process.

| Metric | V1 | V2 | Change |
|---|---|---|---|
| `pvout_buildable_best_50km` | Primary resource metric | Primary resource metric | Unchanged |
| `lcoe_remote_captive_allin_usd_mwh` | Primary cost metric | Replaced by `lcoe_grid_connected_usd_mwh` | Lower (cheaper connection) |
| `dist_to_nearest_substation_km` | Gen-tie length proxy | `dist_solar_to_nearest_substation_km` — grid injection distance | Reframed |
| `solar_vs_bpp_gap_pct` | Implicit | Primary competitiveness metric | NEW — elevated |
| `siting_scenario` | Filter criterion | Replaced by `grid_integration_category` | More useful |
| Substation capacity | Present but secondary | Elevated — can the grid absorb output? | Reframed |

**New user journey:**

1. Identify regions with strong solar resource (`pvout_buildable_best_50km`) — same as V1
2. Check grid readiness (`grid_ready` or `solar_now`) — is there a substation near the best solar site with sufficient capacity?
3. Build the economic case: `solar_vs_bpp_gap_pct` shows where solar would reduce PLN's cost of supply — this is the core argument for procurement prioritization
4. Review substation capacity — can the local grid absorb the planned project output, or does the proposal need to include grid reinforcement?
5. Assess buildability constraints — same as V1
6. Export analysis for PLN/ESDM engagement or internal BD pipeline prioritization

**The IPP and policymaker journeys are complementary:** the policymaker uses the dashboard to identify where solar procurement should be enabled; the IPP uses it to prepare for and advocate toward those same procurement decisions.

### Persona 5: Industrial Investor / KEK Tenant (NEW)

**Impact: NEW persona**

This persona was implicit in V1 but not separately modeled. They are the factory or smelter operator deciding **which KEK to locate in**. They do not build solar — they buy electricity from PLN.

**Honest limitation:** The I-4 industrial tariff is **nationally uniform** within the same voltage category. This means the dashboard cannot differentiate KEKs by *current* electricity cost — it's the same everywhere. The dashboard's value to this persona lies in three areas where KEKs *do* differ:

| Metric | Purpose | Why it varies by KEK |
|---|---|---|
| `bpp_usd_mwh` | True cost of supply — indicates subsidy exposure and tariff stability risk | BPP varies by grid region; high-BPP regions face greater tariff adjustment pressure |
| `grid_integration_category` | Proxy for future grid quality and cost trajectory | `grid_ready` KEKs near cheap solar are more likely to see infrastructure investment and improved service |
| `green_share_geas_2030_pct` | How much of their power will be renewable by 2030 | Varies by region's solar/wind resource and RUPTL allocation |
| `plan_late` flag | Timeline risk for grid infrastructure arrival | RUPTL pipeline varies significantly by region |
| `dist_kek_to_nearest_substation_km` | Proxy for grid reliability and connection quality | Remote KEKs with distant substations face higher outage risk and longer restoration times |
| `nearest_substation_capacity_mva` | Can PLN's local grid handle industrial-scale load? | Small substations may constrain future expansion |

**User journey:**

1. **All KEKs pay the same tariff today** — the differentiation is about risk and trajectory
2. Check **BPP vs. tariff gap**: KEKs in high-BPP regions are more exposed to future tariff adjustments (PLN cannot subsidize indefinitely). KEKs where solar could lower the regional BPP are better long-term bets.
3. Check **grid reliability**: substation proximity and capacity as proxies. Continuous-process industries (smelters, chemicals, data centers) cannot tolerate frequent outages.
4. Assess **green credentials**: ESG-conscious manufacturers and their buyers increasingly require renewable energy sourcing. `grid_ready` KEKs near solar resource offer a credible green pathway.
5. Export comparison matrix for site selection decision — differentiated by risk factors, not current price

---

## Appendix: Regulatory References

| Regulation | Relevance |
|---|---|
| Permen ESDM No. 1/2015 | Authorizes grid wheeling (not implemented in practice) |
| Permen ESDM No. 27/2017 | Grid connection standards; gen-tie ownership transfers to PLN post-commissioning |
| PP No. 112/2022 | KEK-specific power procurement exemptions |
| Permen ESDM No. 7/2024 | Updated renewable energy procurement framework |
| Permen ESDM No. 8/2023 | ESDM Technology Catalogue (solar CAPEX source) |
| UU No. 30/2009 | Electricity Law — PLN as sole grid operator, captive power provisions |
