# Cost-Metric Taxonomy

**Purpose.** One place that names every `$/MWh` column in the dashboard, says what it means, who produces it, and who consumes it. Eliminates the "wait, is `lcoe_mid` the within-boundary one or the grid-connected one?" problem and flags the two different meanings of "blended" that are live in the model today.

**Scope.** Backend (`src/dash/logic/`), API payload (`src/api/`), frontend types (`frontend/src/lib/types.ts`), UI labels (`columns.tsx`, `EconomicsTab.tsx`), and methodology (`docs/METHODOLOGY_CONSOLIDATED.md`).

**Not yet implemented.** This doc is the spec. Code rename + enum introduction is a separate PR. See §7.

---

## Table of contents

- [0. Key terms](#0-key-terms) — LCOE, firming, allin, adder, within-boundary vs grid-connected, PVOUT, BPP, tariff, captive/grid fraction, delivered cost, the two "blended" meanings, gate, tier/benchmark shorthand
- [1. Three tiers + a benchmark](#1-three-tiers--a-benchmark)
  - The stack (T1 → T2 → T3)
  - The benchmark (B)
  - Why T4 isn't a real tier
- [2. Column inventory](#2-column-inventory)
  - [T1. Generation LCOE](#t1-generation-lcoe)
  - [T2. Firmed LCOE](#t2-firmed-lcoe)
  - [T3. Delivered cost (tenant view)](#t3-delivered-cost-tenant-view--54)
  - [B. Grid benchmark](#b-grid-benchmark)
- [3. Derived / comparison metrics](#3-derived--comparison-metrics) — gap %, carbon breakeven, economic tier, action flags
- [4. Known collisions and misleading names](#4-known-collisions-and-misleading-names)
  - 4.1 "Blended" means two different things
  - 4.2 `lcoe_mid` hides its siting scenario
  - 4.3 `best_re_lcoe_mid` is firmed, not raw
  - 4.4 Inconsistent firmed-LCOE naming
  - 4.5 `grid_cost` vs `dashboard_rate` vs `bpp`
- [5. Naming conventions (target state)](#5-naming-conventions-target-state)
- [6. Proposed enums (future work)](#6-proposed-enums-future-work)
- [7. Deferred decisions](#7-deferred-decisions) — PR scope for rename, repoint flags, registry
- [8. Changelog](#8-changelog)

---

## 0. Key terms

Read this section first. The rest of the doc assumes these definitions.

**LCOE (Levelized Cost of Electricity).** The steady $/MWh price a plant must earn over its life to recover CAPEX, OPEX, and financing and hit its WACC target. Think "the break-even price per MWh." Formula is annuity-based: `LCOE = (CRF × CAPEX + FOM) / (CF × 8760)` where CRF is the capital recovery factor. See §6 of `METHODOLOGY_CONSOLIDATED.md`.

**Firming.** Making an intermittent RE source behave like dispatchable power by adding storage or backup. Solar produces ~14 hours/day; the other ~10 need to come from somewhere. Firming = pricing that "somewhere." In this model it means adding a **BESS (battery energy storage system) adder** sized to bridge the gap hours for the load's reliability requirement.
- **"Firmed LCOE"** = generation LCOE + firming adder. The all-in $/MWh to deliver power when the load needs it, not just when the sun is up.
- **Example.** Solar LCOE = $48/MWh. BESS adder for a 24/7 industrial load = $14/MWh. Firmed LCOE = $62/MWh.
- **Why it matters.** Comparing raw solar LCOE ($48) to grid tariff ($63) makes solar look cheap. Comparing firmed solar ($62) to grid ($63) is closer to what the tenant actually experiences for 24/7 load. Tier T2 in §1.

**Allin.** Shorthand used in column names for "firmed, all-in." `hybrid_allin_usd_mwh` = hybrid generation LCOE + hybrid BESS adder. `lcoe_wind_allin_mid` = wind LCOE + wind BESS adder. Synonym for "firmed." See naming collision in §4.4.

**Adder.** A $/MWh component added to a base LCOE. Two live in this model: the grid-connection adder (transmission + fixed cost per kW of capacity, amortized over generation) and the BESS adder (storage CAPEX sized to bridge hours, amortized over generation). Adders are Tier T2 components, not standalone costs.

**Within-boundary (captive).** Solar built inside the site's fence, serving the load directly with no transmission. Uses PVOUT at the site centroid. No line cost, no substation. Tenant-owned in most cases. This is the §5.1 siting scenario. `lcoe_within_boundary_usd_mwh` is the LCOE for this case.

**Grid-connected.** Solar built wherever the best PVOUT within 50 km is, connected back through a substation, selling to the grid. Uses best-50km PVOUT + a grid-connection adder for the line. This is the §5.2 siting scenario. `lcoe_mid_usd_mwh` is today's (misleadingly named) field for this case.

**PVOUT.** Specific annual photovoltaic output from the Global Solar Atlas, kWh/kWp/year. Divide by 8760 to get solar capacity factor. Higher PVOUT = cheaper solar.

**Capacity factor (CF).** Average output as a fraction of nameplate. Solar CF in Indonesia is ~17–19%. Wind CF varies 10–35% depending on wind speed.

**BPP (Biaya Pokok Penyediaan).** PLN's cost of supply per region. What it costs PLN to deliver a MWh, not what the tenant pays. Tier T4 benchmark. Varies by grid region.

**Tariff.** What industrial tenants actually pay PLN. Often subsidized below BPP. Not the same as BPP. The UI lets the user compare RE cost against either benchmark via `BenchmarkMode`.

**Captive fraction / grid fraction.** If within-boundary solar can only cover 15% of the tenant's demand (because of rooftop/land limits or buildout ratio), `f_captive = 0.15` and `f_grid = 0.85` — the rest comes from the grid. Used in the §5.4 delivered-cost blend.

**Delivered cost (tenant view).** The blended $/MWh the tenant actually pays: `f_captive × LCOE_within_boundary + f_grid × grid_rate`. This is §5.4. **Do not confuse with "hybrid LCOE" or "blended LCOE" in §6A.3** — that's a different blend (solar + wind generation mix).

**Blended.** Ambiguous term in this model. Used for two unrelated blends:
1. **§5.4 "Blended delivered cost"** = captive + grid-import mix (T3, tenant view).
2. **§6A.3 "Blended LCOE"** = solar + wind generation mix (T1, hybrid RE tech).

Every use of "blended" in code, UI, or docs should specify which. Proposed rename in §4.1 kills the ambiguity by calling the first one just "delivered cost."

**Gate.** A threshold or cost level something is compared *against*. Grid cost is the gate raw-solar LCOE has to beat for the `solar_now` action flag to fire. Category B provides the gates.

**Tier (T1/T2/T3).** Shorthand for the three conceptual **layers** every cost we *produce* falls into. They stack: T1 raw generation → T2 + firming → T3 + tenant grid-mix. Each builds on the previous.

**Benchmark (B).** The grid reference prices we compare T1/T2/T3 *against*. Not in the stack — they're on the other side of the comparison. Called out separately because "B is the fourth tier" is a bad mental model; there's no ordering between BPP and tariff, and neither is a cost we produce.

---

## 1. Three tiers + a benchmark

Every cost number in the system falls into one of four categories. Three of them stack (T1 → T2 → T3), each layer adding cost to the previous. The fourth (B) is the benchmark we compare them against — it sits on the other side of the equation.

### The stack (T1 → T2 → T3): costs we *produce*

| Tier | What it represents | Stacks on | Includes |
|------|--------------------|-----------|----------|
| **T1. Generation LCOE** | Levelized cost to produce 1 MWh at the plant gate. No firming, no delivery, no tenant mixing. | — (base layer) | Solar, wind, hybrid (solar+wind) generation LCOEs, in WACC bands (low/mid/high) and siting scenarios (within-boundary / grid-connected). |
| **T2. Firmed LCOE** | T1 + BESS or firming adder. "What it costs per MWh to deliver *firm* power at the plant gate." | T1 + firming adder | `lcoe_with_battery`, `hybrid_allin`, `lcoe_wind_allin`, `best_re_lcoe`. |
| **T3. Delivered cost (tenant view)** | What the tenant actually pays per MWh when captive + grid are mixed. This is §5.4. | T1 (within-boundary) × captive_fraction + grid_rate × grid_fraction | `delivered_cost_blended` + its input/diagnostic companions. |

### The benchmark (B): prices we compare *against*

| Category | What it represents | Includes |
|----------|--------------------|----------|
| **B. Grid benchmark** | Reference prices from the grid side of the market. Not a cost we produce — the thing T1/T2/T3 have to beat for solar/wind/hybrid to be "competitive." | `bpp`, `dashboard_rate`, `grid_cost`, industrial tariff. |

**Why this split matters.** Mixing the stack with the benchmark in a UI comparison is almost always a bug. "Solar LCOE ($48) beats grid ($63)" is T1 vs B. "Delivered cost ($61) vs grid ($63)" is T3 vs B. The tenant lives in T3. The generation economist lives in T1+T2. The grid, unchanged, is B. Keep them separate.

**Why T4 isn't a real tier.** An earlier draft called the grid benchmark "T4." Wrong framing — there's no ordering between the grid and the cost-stack layers (BPP doesn't "stack on" T3), and BPP/tariff/dashboard-rate aren't a hierarchy among themselves either. Calling it "B" (or just "the benchmark") reflects that it's a different axis, not the next layer up.

---

## 2. Column inventory

### T1. Generation LCOE

| Column | Tier | Siting scenario | WACC | Meaning | Produced by | Status |
|--------|------|-----------------|------|---------|-------------|--------|
| `lcoe_mid_usd_mwh` | T1 | **grid-connected, best PVOUT within 50km** | mid | The default solar generation LCOE shown in the table. Uses best PVOUT within 50km of the site + grid-connection cost adder. | `src/dash/logic/lcoe.py::compute_lcoe_live` (GC branch) → `scorecard.py::enrich_lcoe_and_gaps` | ✅ live |
| `lcoe_low_usd_mwh` | T1 | grid-connected | low | Low-WACC band of `lcoe_mid`. | same | ✅ live |
| `lcoe_high_usd_mwh` | T1 | grid-connected | high | High-WACC band. | same | ✅ live |
| `lcoe_within_boundary_usd_mwh` | T1 | **within KEK boundary, centroid PVOUT** | mid | Solar LCOE if the plant is built inside the fence. No transmission adder, centroid PVOUT (not best-50km). | `scorecard.py::enrich_lcoe_and_gaps` | ✅ live |
| `lcoe_within_boundary_low_usd_mwh` | T1 | within-boundary | low | Low-WACC band. | same | ✅ live |
| `lcoe_within_boundary_high_usd_mwh` | T1 | within-boundary | high | High-WACC band. | same | ✅ live |
| `lcoe_grid_connected_capped_usd_mwh` | T1 | grid-connected, capacity-capped | mid | `lcoe_mid` recomputed when the sized project is capped by substation capacity. | `scorecard.py::enrich_grid_connected_capped_lcoe` | ✅ live |
| `lcoe_wind_mid_usd_mwh` | T1 | (wind has no siting scenarios today) | mid | Wind generation LCOE. No firming. | `lcoe.py::compute_lcoe_wind_live` → `scorecard.py::enrich_wind` | ✅ live |
| `hybrid_lcoe_usd_mwh` | T1 | — | mid | **§6A.3 "blended LCOE"**: solar_share × solar_lcoe + wind_share × wind_lcoe. Pre-firming. | `technology.py::compute_hybrid_metrics` | ✅ live |

### T2. Firmed LCOE

| Column | Tier | Meaning | Produced by | Status |
|--------|------|---------|-------------|--------|
| `battery_adder_usd_mwh` | T2 (component) | BESS $/MWh adder given demand, bridge hours, BESS CAPEX. | `technology.py::compute_bess_metrics` | ✅ live |
| `lcoe_with_battery_usd_mwh` | T2 | `lcoe_mid` + `battery_adder`. Solar firmed. | same | ✅ live |
| `hybrid_bess_adder_usd_mwh` | T2 (component) | BESS adder for the hybrid mix (reduced by wind's nighttime coverage). | `technology.py::compute_hybrid_metrics` | ✅ live |
| `hybrid_allin_usd_mwh` | T2 | `hybrid_lcoe` + `hybrid_bess_adder`. Solar+wind firmed. | same | ✅ live |
| `lcoe_wind_allin_mid_usd_mwh` | T2 | `lcoe_wind` + wind-specific BESS adder (CF-dependent firming hours). | `scorecard.py::enrich_best_re_technology` | ✅ live |
| `best_re_lcoe_mid_usd_mwh` | **T2** (despite name) | min(`lcoe_with_battery`, `lcoe_wind_allin`, `hybrid_allin`) — the cheapest firmed RE option per site. **Name says `lcoe` but the value is firmed.** See §4 naming issues. | `scorecard.py::enrich_best_re_technology` | ⚠️ misleading name |

### T3. Delivered cost (tenant view) — §5.4

| Column | Tier | Meaning | Produced by | Status |
|--------|------|---------|-------------|--------|
| `delivered_cost_blended_usd_mwh` | T3 | **§5.4 "blended delivered cost"**: `f_captive × LCOE_wb + f_grid × grid_rate`. What the tenant pays. | `scorecard.py::enrich_delivered_cost` | ✅ live (PR1) |
| `captive_fraction` | T3 (weight) | Share of demand covered by within-boundary solar after buildout-footprint haircut. Same as `within_boundary_coverage_effective_pct`, exposed here for clarity. | same | ✅ live |
| `grid_fraction` | T3 (weight) | `1 - captive_fraction`. | same | ✅ live |
| `delivered_cost_wb_lcoe_used_usd_mwh` | T3 (diagnostic) | The within-boundary LCOE that went into the blend. Echoes `lcoe_within_boundary_usd_mwh`. | same | ✅ live |
| `delivered_cost_grid_rate_used_usd_mwh` | T3 (diagnostic) | The grid rate that went into the blend (user's dashboard benchmark). | same | ✅ live |
| `delivered_cost_gap_vs_grid_pct` | T3 (derived) | `(grid_rate - delivered) / grid_rate`. Percent cheaper than pure grid. | same | ✅ live |

### B. Grid benchmark

| Column | Category | Meaning | Source |
|--------|----------|---------|--------|
| `bpp_usd_mwh` | B | PLN Biaya Pokok Penyediaan — cost of supply, by grid region. Not the tariff the tenant pays. | `fct_grid_cost_proxy` (KESDM) |
| `dashboard_rate_usd_mwh` | B | Whichever rate the user picked in the UI (`BenchmarkMode`: `bpp` or `tariff`). The number the dashboard actually compares against in flags and gaps. | `site_context.py::build_ctx` |
| `grid_cost_usd_mwh` | B | Alias for whatever `dashboard_rate` resolves to during scorecard enrichment. Echoed into the row for consumers that don't carry the mode. | `scorecard.py::enrich_carbon_and_grid` |

**Note:** `bpp`, `dashboard_rate`, `grid_cost` are three names for **one conceptual thing** (the grid benchmark). `bpp` is the raw input, `dashboard_rate` is the user's chosen mode, `grid_cost` is the resolved value handed to downstream enrichers. Not a bug, but worth knowing.

---

## 3. Derived / comparison metrics

These aren't $/MWh themselves but they reference the columns above. Listing here so future readers can trace which generation-cost number is feeding which gate.

| Column | References | Note |
|--------|------------|------|
| `solar_competitive_gap_pct` | `lcoe_mid_usd_mwh` vs `dashboard_rate_usd_mwh` | T1 vs T4. Answers "is raw solar cheaper than grid?" |
| `gap_vs_bpp_pct` | `lcoe_mid_usd_mwh` vs `bpp_usd_mwh` | T1 vs T4 (BPP-only). |
| `wind_competitive_gap_pct` | `lcoe_wind_mid_usd_mwh` vs `bpp_usd_mwh` | T1 vs T4. |
| `delivered_cost_gap_vs_grid_pct` | `delivered_cost_blended` vs `grid_rate_used` | **T3 vs T4.** The tenant-view equivalent of `solar_competitive_gap_pct`. |
| `carbon_breakeven_usd_tco2` | `lcoe_mid` gap ÷ `grid_emission_factor` | T1-based carbon breakeven. |
| `wind_carbon_breakeven_usd_tco2` | wind LCOE gap ÷ emission factor | T1-based. |
| `hybrid_carbon_breakeven_usd_tco2` | `hybrid_allin` gap ÷ emission factor | T2-based. |
| `economic_tier` | `lcoe_mid` + `hybrid_allin` + `grid_cost` | Classifies into `full_re / partial_re / near_parity / not_competitive / no_resource`. |
| action flags (`solar_now`, `not_competitive`, etc.) | `lcoe_mid` vs `grid_cost` | T1-driven. |

**All of the above use T1 (`lcoe_mid`) or T2 (`hybrid_allin`) as the cost input compared against B (grid), never T3 (`delivered_cost`).** Whether to repoint any of them at T3 is an open methodology question — see §7 "Deferred decisions" (PR3, TODOS M31).

---

## 4. Known collisions and misleading names

These are the sharp edges this taxonomy exists to kill. **None are fixed in code yet** — this doc is the spec for the eventual rename PR.

### 4.1 "Blended" means two different things

| Where | What "blended" means | Formula |
|-------|---------------------|---------|
| §5.4 `delivered_cost_blended_usd_mwh` | Captive + grid mix (T3) | `f_captive × LCOE_wb + f_grid × grid_rate` |
| §6A.3 `hybrid_lcoe_usd_mwh` ("Blended LCOE") | Solar + wind mix (T1) | `solar_share × LCOE_solar + wind_share × LCOE_wind` |

A reader of the methodology doc sees "Blended" as a section title in two places and has no way to know which blending is meant without reading the formula. Same problem for a new engineer grepping the codebase.

**Proposed fix (defer to rename PR):**
- `delivered_cost_blended_usd_mwh` → `delivered_cost_usd_mwh` (delivered cost *is* the blend; "blended" is redundant).
- Keep `hybrid_lcoe_usd_mwh` as-is. Rename §6A.3 section title from "Blended LCOE" → "Hybrid generation LCOE".

### 4.2 `lcoe_mid` hides its siting scenario

`lcoe_mid_usd_mwh` is the **grid-connected, best-PVOUT-within-50km** LCOE. But `lcoe_within_boundary_usd_mwh` *does* name its siting scenario. The asymmetry is the problem — one name says the scenario, the other doesn't.

A reader assumes `lcoe_mid` is a neutral/default number and `lcoe_within_boundary` is the variant. It's the opposite conceptually: within-boundary is the "no grid adder" baseline; grid-connected adds transmission cost and uses a different PVOUT.

**Proposed fix (defer):** rename `lcoe_mid` → `lcoe_grid_connected_usd_mwh` (matches `lcoe_within_boundary_usd_mwh` pattern), keep low/mid/high WACC bands as a separate suffix.

### 4.3 `best_re_lcoe_mid_usd_mwh` is firmed, not raw

The `_lcoe_` token in the name suggests T1 (generation). The value is T2 (min of firmed options). This tripped up at least one code review already.

**Proposed fix:** rename → `best_re_allin_usd_mwh`. Matches the `hybrid_allin` / `wind_allin` convention.

### 4.4 Inconsistent firmed-LCOE naming

| Form | Tech | Pattern |
|------|------|---------|
| `lcoe_with_battery_usd_mwh` | solar | `lcoe_with_battery` |
| `hybrid_allin_usd_mwh` | solar+wind | `allin` |
| `lcoe_wind_allin_mid_usd_mwh` | wind | `allin_mid` |
| `best_re_lcoe_mid_usd_mwh` | best-of | `lcoe_mid` (but firmed — see 4.3) |

Four patterns for the same concept (LCOE + firming). **Proposed fix:** unify on `{tech}_allin_usd_mwh` — `solar_allin`, `wind_allin`, `hybrid_allin`, `best_re_allin`.

### 4.5 `grid_cost` vs `dashboard_rate` vs `bpp`

Three overlapping T4 names. Not broken, but confusing. `grid_cost` and `dashboard_rate` are the same value, echoed under two names. Worth documenting (done above §2.T4) and eventually consolidating to one canonical field in the row.

---

## 5. Naming conventions (target state)

When the rename PR lands, every new cost column should follow these rules. Until then this section is aspirational.

**5.1 Column name shape.** `{tech}_{siting}_{band}_usd_mwh` where unambiguous, else drop components.

- `tech` ∈ `solar`, `wind`, `hybrid`, `best_re` (optional; defaults to solar when omitted for historical reasons — to be removed once `lcoe_mid` is renamed).
- `siting` ∈ `within_boundary`, `grid_connected`, `capped` (optional; grid-connected is the default for solar once rename lands).
- `band` ∈ `low`, `mid`, `high` (optional; mid is the default).

**5.2 Concept suffix.**
- `_lcoe_` → T1 generation only.
- `_allin_` → T2 firmed (includes BESS).
- `_adder_` → T2 component (BESS adder, firming adder).
- `delivered_cost_` → T3 tenant view.
- Grid benchmarks → no tech prefix, just `grid_cost`, `bpp`, `dashboard_rate`.

**5.3 WACC bands.** Always `low` / `mid` / `high`. Never `p10` / `p50` / `p90` or `optimistic` / `base` / `pessimistic`.

**5.4 Gap/comparison columns.** `{metric}_gap_vs_{benchmark}_pct`. Examples: `solar_gap_vs_bpp_pct`, `delivered_cost_gap_vs_grid_pct`.

---

## 6. Proposed enums (future work)

Follows the existing `ActionFlag` / `EconomicTier` / `InfrastructureReadiness` / `SiteType` / `Sector` pattern. Python `StrEnum` in `src/model/cost_metrics.py`, TS mirror in `frontend/src/lib/costMetrics.ts`.

### 6.1 `CostCategory` (T1–T3 stack + B benchmark)

```python
class CostCategory(StrEnum):
    GENERATION = "generation"         # T1: raw LCOE (stack base)
    FIRMED = "firmed"                 # T2: T1 + BESS adder
    DELIVERED = "delivered"           # T3: T1 (wb) × f_captive + grid × f_grid
    GRID_BENCHMARK = "grid_benchmark" # B: comparison price (not in the stack)
```

`GENERATION / FIRMED / DELIVERED` form an ordered stack. `GRID_BENCHMARK` is a different axis — code that cares about "which layer of the stack is this?" should exclude `GRID_BENCHMARK` from the ordering.

### 6.2 `SitingScenario`

```python
class SitingScenario(StrEnum):
    WITHIN_BOUNDARY = "within_boundary"   # centroid PVOUT, no line cost
    GRID_CONNECTED = "grid_connected"     # best-50km PVOUT, + connection cost
    GRID_CONNECTED_CAPPED = "grid_connected_capped"  # capacity-capped variant
```

### 6.3 `WaccBand`

```python
class WaccBand(StrEnum):
    LOW = "low"
    MID = "mid"
    HIGH = "high"
```

### 6.4 `Technology`

```python
class Technology(StrEnum):
    SOLAR = "solar"
    WIND = "wind"
    HYBRID = "hybrid"      # solar + wind
    BEST_RE = "best_re"    # min of the above firmed
```

**Usage idea.** A `CostMetric` registry (dict keyed on column name) maps every `*_usd_mwh` field to its `(tier, tech, siting, band)` tuple. Then:
- API responses self-describe.
- Frontend `columns.tsx` can derive display labels from the registry instead of hardcoding them.
- Methodology doc can generate its cost-column table from the registry.

Not needed for PR2. Valuable for PR3+.

---

## 7. Deferred decisions

These are real, open questions. This doc's job is to name them, not answer them.

### 7.1 Rename `delivered_cost_blended` → `delivered_cost`?
**Status:** proposed, not done.
**Scope:** types.ts, columns.tsx, EconomicsTab.tsx, scorecard.py column name, golden fixture, §5.4 methodology.
**Effort:** ~30 min.
**Blocking:** nothing. Can go in PR2 or a tiny follow-up PR.

### 7.2 Rename `lcoe_mid` → `lcoe_grid_connected`?
**Status:** proposed, not done.
**Scope:** large — touches scorecard.py, site_context.py, basic_model.py, 80+ test files, golden fixture, types.ts, every column.tsx header, methodology §5.
**Effort:** ~4–6 hr with a careful search/replace.
**Blocking:** PR2 stability. Do after PR1+PR2 merge.

### 7.3 Repoint action flags / economic tier / competitive gap / carbon breakeven from T1 (`lcoe_mid`) to T3 (`delivered_cost`)?
**Status:** TODOS M31. This is PR3.
**Why it matters:** currently `solar_competitive_gap_pct` answers "is raw solar cheaper than grid?" (T1 vs T4). If we repoint at `delivered_cost`, it answers "does the tenant pay less than pure grid after mixing in captive?" (T3 vs T4) — which is closer to what most personas actually want to know. But it changes outputs every persona has been looking at for weeks.
**Scope:** methodology §5 + §7 rewrite, flag-logic in `basic_model.py::action_flags`, golden fixture, new persona validation pass.
**Blocking:** this taxonomy doc (so the rename is stable before flag logic depends on it).

### 7.4 Introduce `CostMetric` registry + enums (§6)?
**Status:** proposed, not done.
**Effort:** ~4 hr initial build, pays back on every future column addition.
**Blocking:** 7.1 and 7.2 should land first so the registry encodes the final names.

---

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-04-21 | Initial taxonomy doc. Captures state after PR1 (`enrich_delivered_cost`) and during PR2 (UI surfacing). No code renames yet. |
