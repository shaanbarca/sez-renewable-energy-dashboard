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
  - [T3. Supply Blend (tenant view)](#t3-supply-blend-tenant-view--54)
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

**BPP (Biaya Pokok Penyediaan).** PLN's cost of supply per region. What it costs PLN to deliver a MWh, not what the tenant pays. Category B benchmark. Varies by grid region.

**Tariff.** What industrial tenants actually pay PLN. Often subsidized below BPP. Not the same as BPP. The UI lets the user compare RE cost against either benchmark via `BenchmarkMode`.

**Captive / remote / grid fractions.** Three weights that sum to 1 in the §5.4 cascade. `captive_fraction` = within-boundary solar share (capped at the daytime ceiling). `delivered_cost_remote_fraction` = remote captive solar share (fills the headroom between WB and the daytime ceiling, when a grid-connected siting exists). `grid_fraction` = 1 − captive − remote. Formalised by V3.11 (previously just captive + grid — the remote layer was folded silently into grid).

**Daytime ceiling.** `SOLAR_PRODUCTION_HOURS / 24 ≈ 0.417`. The physical cap on how much of a 24-hour load any un-firmed solar mix can serve. The cascade never assigns more than this to solar (WB + remote combined). Night demand goes to grid by construction.

**Supply Blend / Delivered cost (tenant view).** What the tenant actually pays per MWh under a three-layer cascade: `captive × wb_LCOE + remote × gc_LCOE + grid × grid_rate`. WB solar first, then remote captive (grid-connected IPP with gentie) up to the daytime ceiling, grid for the rest. This is §5.4. UI label is "Supply Blend". **Do not confuse with "hybrid LCOE" in §6A.3** — that's a different blend (solar + wind generation mix).

**Blended.** Ambiguous term. Used for two unrelated blends in earlier drafts:
1. **§5.4 "Supply Blend" (formerly "blended delivered cost")** = captive WB + remote captive + grid-import cascade (T3, tenant view).
2. **§6A.3 "Blended LCOE"** = solar + wind generation mix (T1, hybrid RE tech).

Column names already de-ambiguated: `delivered_cost_usd_mwh` (T3) and `hybrid_lcoe_usd_mwh` (T1 hybrid). UI label in the cost-view toggle is now "Supply Blend" rather than "Delivered".

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
| **T3. Supply Blend (tenant view)** | What the tenant actually pays per MWh under a three-layer cascade: WB solar first, then remote captive (grid-connected IPP) up to the daytime ceiling (~42%), then grid. This is §5.4. | T1 (within-boundary) × captive + T1 (grid-connected) × remote + grid_rate × grid_fraction | `delivered_cost` + its input/diagnostic companions. |

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

### T3. Supply Blend (tenant view) — §5.4

| Column | Tier | Meaning | Produced by | Status |
|--------|------|---------|-------------|--------|
| `delivered_cost_usd_mwh` | T3 | **§5.4 "Supply Blend" (cascade)**: `captive × wb_LCOE + remote × gc_LCOE + grid × grid_rate`. What the tenant pays. | `scorecard.py::enrich_delivered_cost` | ✅ live (V3.11) |
| `captive_fraction` | T3 (weight) | Within-boundary solar share. `min(within_boundary_coverage_effective_pct, daytime_cap)` where `daytime_cap = SOLAR_PRODUCTION_HOURS/24`. | same | ✅ live |
| `delivered_cost_remote_fraction` | T3 (weight) | Remote captive solar share. Fills `daytime_cap - captive_fraction` when a grid-connected siting exists (`gc_row` present); else 0. | same | ✅ live (V3.11) |
| `grid_fraction` | T3 (weight) | `1 - captive_fraction - delivered_cost_remote_fraction`. By construction, ≥ `1 - daytime_cap ≈ 0.583` (night demand always goes to grid). | same | ✅ live |
| `delivered_cost_wb_lcoe_used_usd_mwh` | T3 (diagnostic) | The within-boundary LCOE that went into the captive layer. Echoes `lcoe_within_boundary_usd_mwh`. Null if no WB row. | same | ✅ live |
| `delivered_cost_gc_lcoe_used_usd_mwh` | T3 (diagnostic) | The grid-connected LCOE that went into the remote layer. Echoes `lcoe_mid_usd_mwh`. Null if no GC row. | same | ✅ live (V3.11) |
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
| `solar_competitive_gap_pct` | `lcoe_mid_usd_mwh` vs `dashboard_rate_usd_mwh` | T1 vs B. Answers "is raw solar cheaper than grid?" |
| `gap_vs_bpp_pct` | `lcoe_mid_usd_mwh` vs `bpp_usd_mwh` | T1 vs B (BPP-only). |
| `wind_competitive_gap_pct` | `lcoe_wind_mid_usd_mwh` vs `bpp_usd_mwh` | T1 vs B. |
| `delivered_cost_gap_vs_grid_pct` | `delivered_cost` vs `grid_rate_used` | **T3 vs B.** The tenant-view equivalent of `solar_competitive_gap_pct`. |
| `cbam_adjusted_gap_pct` | `(lcoe_mid − grid_cost − cbam_savings_per_mwh) / grid_cost` | T1 vs B (CBAM-adjusted). Currently T1-driven; see §7.3. |
| `carbon_breakeven_usd_tco2` | `lcoe_mid` gap ÷ `grid_emission_factor` | T1-based carbon breakeven. |
| `wind_carbon_breakeven_usd_tco2` | wind LCOE gap ÷ emission factor | T1-based. |
| `hybrid_carbon_breakeven_usd_tco2` | `hybrid_allin` gap ÷ emission factor | T2-based. |
| `economic_tier` | `lcoe_mid` + `hybrid_allin` + `grid_cost` | Classifies into `full_re / partial_re / near_parity / not_competitive / no_resource`. |
| action flags (`solar_now`, `not_competitive`, etc.) | `lcoe_mid` vs `grid_cost` | T1-driven. |

**All of the above (except `delivered_cost_gap_vs_grid_pct`) use T1 (`lcoe_mid`) or T2 (`hybrid_allin`) as the cost input compared against B (grid), never T3 (`delivered_cost`).** Whether to let the user pick which basis feeds each derived metric is the open question — see §7.3 `CostBasis` toggle (PR3, TODOS M31).

---

## 4. Known collisions and misleading names

These are the sharp edges this taxonomy exists to kill. **None are fixed in code yet** — this doc is the spec for the eventual rename PR.

### 4.1 "Blended" means two different things

| Where | What "blended" means | Formula |
|-------|---------------------|---------|
| §5.4 `delivered_cost_usd_mwh` ("Supply Blend") | WB + remote captive + grid cascade (T3) | `captive × wb_LCOE + remote × gc_LCOE + grid × grid_rate` |
| §6A.3 `hybrid_lcoe_usd_mwh` ("Blended LCOE") | Solar + wind mix (T1) | `solar_share × LCOE_solar + wind_share × LCOE_wind` |

A reader of the methodology doc sees "Blended" as a section title in two places and has no way to know which blending is meant without reading the formula. Same problem for a new engineer grepping the codebase.

**Fix applied:**
- `delivered_cost_blended_usd_mwh` → `delivered_cost_usd_mwh` ✅ done (see §8 changelog).
- `hybrid_lcoe_usd_mwh` unchanged. §6A.3 section title "Blended LCOE" → "Hybrid generation LCOE" pending.

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

Three overlapping B-category names. Not broken, but confusing. `grid_cost` and `dashboard_rate` are the same value, echoed under two names. Worth documenting (done above §2.B) and eventually consolidating to one canonical field in the row.

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

### 6.5 `CostBasis` (user-facing toggle — see §7.3)

```python
class CostBasis(StrEnum):
    RAW = "raw"             # T1: generation LCOE, no firming — UI label "Solar LCOE"
    FIRMED = "firmed"       # T2: +BESS adder — UI label "Solar 24/7"
    DELIVERED = "delivered" # T3: WB + remote captive + grid cascade — UI label "Supply Blend"
```

Enum keys stay `raw / firmed / delivered` (internal identifiers, stable across UI copy changes). User-facing labels live in `frontend/src/lib/costBasis.ts::COST_BASIS_LABELS`.

Unlike the other enums (which are column-level metadata), `CostBasis` is a **user-selectable UI state** parallel to `BenchmarkMode` and `EnergyMode`. It controls which cost column feeds `action_flag` / `economic_tier` / `solar_competitive_gap_pct` / `carbon_breakeven_usd_tco2`. Resolution table in §7.3.

**Usage idea.** A `CostMetric` registry (dict keyed on column name) maps every `*_usd_mwh` field to its `(category, tech, siting, band)` tuple. Then:
- API responses self-describe.
- Frontend `columns.tsx` can derive display labels from the registry instead of hardcoding them.
- Methodology doc can generate its cost-column table from the registry.
- The `(EnergyMode, CostBasis)` → column resolver (§7.3) becomes a one-line registry lookup.

Not needed for PR2. Valuable once §7.3 ships.

---

## 7. Deferred decisions

These are real, open questions. This doc's job is to name them, not answer them.

### 7.1 Rename `delivered_cost_blended` → `delivered_cost`?
**Status:** ✅ done (2026-04-21). Renamed in scorecard.py, test fixture, types.ts, columns.tsx, EconomicsTab.tsx, METHODOLOGY §5.4, DATA_DICTIONARY. Golden fixture regenerated. M31 `CostBasis` PR can now reference the stable name.

### 7.2 Rename `lcoe_mid` → `lcoe_grid_connected`?
**Status:** proposed, not done.
**Scope:** large — touches scorecard.py, site_context.py, basic_model.py, 80+ test files, golden fixture, types.ts, every column.tsx header, methodology §5.
**Effort:** ~4–6 hr with a careful search/replace.
**Blocking:** PR2 stability. Do after PR1+PR2 merge.

### 7.3 `CostBasis` toggle — let the user pick which layer of the stack feeds the action flags

**Status:** ✅ done (2026-04-21). Three-way **Solar LCOE / Solar 24/7 / Supply Blend** toggle in the header (`frontend/src/components/ui/CostBasisToggle.tsx`). Frontend-derivation via `resolveCost(row, mode, basis)` — flags/tiers/gap/carbon re-compute at render time per the matrix below. Unsupported cells disabled with "Not modelled for {mode}" tooltip. Each option has a hover tooltip explaining what's inside the number. See METHODOLOGY §10.5 for the implementation detail and the one deviation from the original spec (frontend derivation instead of backend fan-out).

**Framing change.** An earlier version of this item asked "should we repoint action flags from `lcoe_mid` to `delivered_cost`?" — a one-way methodology swap. Better framing: **don't pick, let the user pick.** The dashboard already has two cost-related user toggles (`BenchmarkMode`, `EnergyMode`). Adding a third, `CostBasis`, completes the matrix.

**The matrix.** `action_flag` / `economic_tier` / `solar_competitive_gap_pct` / `carbon_breakeven_usd_tco2` resolve to a specific cost column at evaluation time, looked up from `(EnergyMode, CostBasis)`. UI labels in parentheses:

| | `raw` — "Solar LCOE" (T1) | `firmed` — "Solar 24/7" (T2) | `delivered` — "Supply Blend" (T3) |
|---|---|---|---|
| **solar** | `lcoe_mid_usd_mwh` | `lcoe_with_battery_usd_mwh` | `delivered_cost_usd_mwh` |
| **wind** | `lcoe_wind_mid_usd_mwh` | `lcoe_wind_allin_mid_usd_mwh` | *(empty today — Supply Blend cascade not defined for wind)* |
| **hybrid** | `hybrid_lcoe_usd_mwh` | `hybrid_allin_usd_mwh` | *(empty today)* |
| **overall** | — (no single raw) | `best_re_lcoe_mid_usd_mwh` | *(empty today)* |

Empty cells today → **grey out the toggle option** when the user picks an unsupported combo. Do not fall back silently; silent fallback is the "why is my gap chart showing a different number than my column" bug waiting to happen.

**Default.** `CostBasis = firmed` for `EnergyMode = overall`, `CostBasis = raw` otherwise. This preserves today's behaviour (flags currently driven by `lcoe_mid` for solar-only mode) and gives the best-RE mode the firmed answer it was already computing for `best_re_lcoe_mid`.

**CBAM as a third axis, not a fourth basis.** "CBAM-adjusted" is not a new CostBasis cell. It's a modifier on the **benchmark side** (`BenchmarkMode`): effective_grid_cost = `grid_cost` − `cbam_savings_per_mwh`. Treat it as a new `BenchmarkMode` value (`bpp`, `tariff`, `bpp_cbam_adjusted`, `tariff_cbam_adjusted`) rather than polluting `CostBasis`. Keeps the two axes orthogonal.

**Why this matters (per persona).**
- **Energy economist** picks `(solar, raw)` — "can the cheapest MWh of solar beat BPP somewhere?"
- **Industrial investor / tenant** picks `(solar, delivered)` — "what will the tenant actually pay vs I-4 tariff?"
- **DFI / 24/7 operator** picks `(solar, firmed)` or `(hybrid, firmed)` — "what's the firm-power price per MWh?"
- **ESG / CBAM-exposed exporter** picks any basis + `bpp_cbam_adjusted` benchmark — "does cleanup pay for itself once CBAM is priced in?"

Today they all share one answer (T1 vs BPP). Post-toggle, they see the right answer for their question.

**UI changes.**
- New toggle in AssumptionsPanel (or top bar) — three-way segmented: Raw / Firmed / Delivered. Disabled states for empty cells.
- Zustand store: add `costBasis: CostBasis` to `dashboard.ts`, default per rule above.
- Map / table action-flag legend: always shows "Flags computed on: {basis} × {energy_mode}" so the user knows what they're looking at. No exceptions — one of the most common usability bugs in multi-mode dashboards is the user forgetting what mode they're in.
- Economic tier tooltip: include the active basis in its explanation.

**Backend changes.**
- `src/model/basic_model.py::action_flags` — accept a `cost_basis: CostBasis` arg (default preserves current behaviour). Internally, the cost input to the gate becomes `resolve_cost_column(energy_mode, cost_basis, row)`.
- `src/model/basic_model.py::economic_tier` — same signature change.
- `src/dash/logic/scorecard.py` — compute the flag/tier for *every* valid (EnergyMode, CostBasis) combo and return as a nested dict (e.g. `action_flags_by_basis: {raw: ..., firmed: ..., delivered: ...}`). Frontend picks the active one. Keeps precomputation flat and makes toggle changes instant (no API roundtrip).
- `carbon_breakeven_usd_tco2` — same fan-out.

**Scope estimate.** 3–4 engineering days. Touches: basic_model, scorecard enricher, types.ts, zustand store, AssumptionsPanel, map legend, ScoreDrawer, methodology §5+§7, golden fixture, new tests for the resolver table.

**Actual scope (shipped).** 1 day. Backend: `CostBasis` StrEnum + resolver unit tests, one extra line in `enrich_grid_passthroughs` to surface `grid_emission_factor_t_co2_mwh` (also fixed a latent CBAM EF bug where the enricher read a field that was never written). Frontend: `costBasis.ts` resolver, `getEffective*` helpers accept `(row, mode, basis)`, Zustand slice + auto-flip (no persist middleware), Radix-based `CostBasisToggle` in the header, `resolveCost` threaded through map markers, table cells + facet filter + CSV export, ScoreDrawer header, ActionTab, QuadrantChart. Golden fixture regenerated (81 × 142 → 81 × 143 cols).

**Blocking:**
- §7.1 (delivered_cost rename) should land first so the resolver doesn't bake in a name that changes.
- §7.2 (lcoe_mid → lcoe_grid_connected rename) optional but clean — the resolver can still use the old name, just read worse.
- §6.5 `CostBasis` enum should ship with this PR, not before.

**Rejected alternatives.**
- *One-way repoint from T1 to T3.* Changes outputs every persona has been staring at for weeks without warning, forces a methodology debate that doesn't have a single right answer.
- *Four bases including `cbam_adjusted`.* Conflates the cost side with the benchmark side — CBAM adjustment is about what the tenant *saves* by decarbonizing (benchmark-side), not about what it *costs* to produce (cost-side).
- *User-editable formulas.* Overbuilt. Three basis options covers ~95% of the persona slicing.

### 7.4 Introduce `CostMetric` registry + enums (§6)?
**Status:** proposed, not done.
**Effort:** ~4 hr initial build, pays back on every future column addition.
**Blocking:** 7.1 and 7.2 should land first so the registry encodes the final names.

---

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-04-21 | Initial taxonomy doc. Captures state after PR1 (`enrich_delivered_cost`) and during PR2 (UI surfacing). No code renames yet. |
| 2026-04-21 | §7.3 reframed from "one-way repoint T1 → T3" to **`CostBasis` user toggle** (raw / firmed / delivered). Matches existing `BenchmarkMode` + `EnergyMode` toggle pattern. Added `CostBasis` StrEnum to §6.5. Added `(EnergyMode × CostBasis)` resolver matrix and per-persona default mapping. CBAM framed as a `BenchmarkMode` extension, not a fourth basis. |
| 2026-04-21 | DESIGN.md / TAXONOMY.md cohesion pass. Cleaned up stale "T4" refs in §0, §3, §4.5 (now consistently "B" / "B-category" per §1 rename). Added `cbam_adjusted_gap_pct` row to §3. DESIGN.md updated in parallel to acknowledge T1/T2/T3/B vocabulary, CostBasis toggle, and delivered cost. |
| 2026-04-21 | §7.1 executed: `delivered_cost_blended_usd_mwh` → `delivered_cost_usd_mwh` across scorecard.py, test fixture, types.ts, columns.tsx, EconomicsTab.tsx, METHODOLOGY §5.4, DATA_DICTIONARY, TAXONOMY tables. Historical CHANGELOG + DESIGN §9 entries left frozen. Unblocks M31 `CostBasis` resolver (§7.3). |
| 2026-04-21 | §7.3 shipped (M31). `CostBasis` enum + resolver + three-way header toggle (Raw / Firmed / Delivered) wired through map / table / ScoreDrawer / QuadrantChart / CSV export. Frontend-derivation (not backend fan-out) — see METHODOLOGY §10.5. Surfaced `grid_emission_factor_t_co2_mwh` on the scorecard so carbon breakeven re-derives against the real EF per basis. Golden fixture regenerated to 81 × 143 cols. |
| 2026-04-21 | **V3.11: Supply Blend cascade.** T3 `delivered_cost` rebuilt from 2-way blend (`f_captive × wb_LCOE + f_grid × grid_rate`) to 3-layer cascade (`captive × wb_LCOE + remote × gc_LCOE + grid × grid_rate`) with physical daytime ceiling `SOLAR_PRODUCTION_HOURS/24 ≈ 0.417`. Added two T3 columns: `delivered_cost_remote_fraction`, `delivered_cost_gc_lcoe_used_usd_mwh`. UI: cost-view toggle relabeled Raw/Firmed/Delivered → **Solar LCOE / Solar 24/7 / Supply Blend** with hover tooltips; tier chips (T1/T2/T3) dropped from `CostBasisToggle`. Enum keys (`raw` / `firmed` / `delivered`) unchanged — labels live in `COST_BASIS_LABELS`. Golden fixture regenerated to 81 × 145 cols. |
