# F13 GEAS Empirical Allocation — Deprioritization

**Decision date:** 2026-05-08
**Status:** Defer to v5.0+ (pending user demand)
**GitHub issue:** [shaanbarca/eez#15](https://github.com/shaanbarca/eez/issues/15) — recommend `deferred` label
**Source of decision:** May 2026 wiki-side strategic reprioritization (`refinement/strategic_reprioritization_2026-05-08.md` Section A1)

---

## TL;DR

**F13 (GEAS empirical allocation alongside proportional) is deferred to v5.0+, not built in v4.0.5 or v4.1.**

Two findings drove this. First, the buyer classes that matter most for Indonesian decarbonization decisions — hyperscalers seeking 24/7 CFE, CBAM-exposed industrial exporters seeking scope-2 attestation — **explicitly reject REC-based decarbonization accounting** regardless of allocation method. Modeling the difference between proportional and empirical REC allocation precisely is academic if the customer set rejects both. Second, the F13 work was scoped under "improve fidelity of GEAS modeling"; if developers don't want GEAS attribution as a decarbonization signal, that fidelity isn't load-bearing for the dashboard's analytical output.

**What stays:** the proportional-default GEAS allocation (already in v4.0). It's still useful for the buyer class that does accept REC attribution (mid-tier industrial buyers under softer ESG reporting frameworks).

**What goes:** the empirical-alternative implementation work (`geas_alloc_empirical()`, distance-decay parameters, region multipliers, `geas_alloc_empirical_gwh` column, `green_share_geas_empirical_pct`, the v4.1a UI toggle).

---

## What was planned (preserved for reference)

The original F13 spec (from `v4_0_dashboard_fixes_spec.md` / Finding 13):

> **F13 — GEAS empirical allocation alongside proportional**
> PLN's actual allocation pattern is urban-anchored and slower-rural. The proportional baseline over-credits remote KEKs. Now:
> 
> - `geas_alloc_empirical()` = `proportional_share × distance_decay × region_multiplier`
> - Decay is 1.0 within 100 km of regional load centre, linearly to 0.4 at 500 km
> - Multipliers: JAVA_BALI 1.2, SUMATERA/BATAM 1.0, KALIMANTAN 0.7, SULAWESI 0.6, NTB 0.5, MALUKU/PAPUA 0.4
> - `REGION_LOAD_CENTRE_LATLON` constants — Jakarta / Medan / Makassar / etc. as distance-decay anchors
> - Both allocations computed in `build_fct_site_scorecard`, surfaced on every site
> - New scorecard columns: `geas_alloc_proportional_gwh`, `geas_alloc_empirical_gwh`, `green_share_geas_proportional_pct`, `green_share_geas_empirical_pct`, `geas_allocation_used` (default proportional; UI toggle deferred to v4.1a)

The methodology itself is sound. The deprioritization is about **whether to build it now**, not about its analytical correctness.

---

## Why deferred — the full reasoning

### 1. The buyer classes that matter most reject REC attribution entirely

The dashboard's primary analytical audiences for power-allocation decisions are:

- **Hyperscalers** (Microsoft, Google, AWS) procuring power for Indonesian data centers
- **CBAM-exposed industrial exporters** (nickel, cement, steel, ammonia, aluminum) needing scope-2 attestation for European, Korean, Japanese OEM buyers
- **DFI investors** evaluating project finance for clean-energy investments

All three categories have explicitly rejected unbundled REC matching as decarbonization accounting:

- Google's **24/7 Carbon-Free Energy (CFE)** methodology, adopted by Microsoft and AWS, requires hourly physical matching with additionality. Annual REC matching is explicitly devalued.
- CBAM's destination-market attestation framework (EU, Korea ETS, Japanese trading house premiums) requires verifiable scope-2 emissions reduction, not REC certificates.
- Major DFIs increasingly screen for additionality + hourly matching in green-finance project assessments.

For these audiences, **the difference between proportional and empirical REC allocation is irrelevant** — they don't accept REC-based attribution at any allocation method.

### 2. F13's load-bearing assumption no longer holds

F13's framing in the original v4.0.5 spec assumed that GEAS-fidelity work was load-bearing for the dashboard's analytical output — that getting REC allocation "right" mattered for the decisions the dashboard supports. Per finding #1 above, that assumption is reversed. The dashboard's primary analytical audiences need:

- **24/7 CFE-compatible accounting** (hourly physical matching), which GEAS doesn't provide regardless of allocation method
- **Direct PPA cost / capacity analysis**, not REC-attributed renewable share
- **Buyer-procurement-requirements taxonomy** (hyperscaler-grade vs CBAM-attestable vs REC-acceptable) — modeled at the buyer-class level, not the GEAS-allocation level

### 3. The proportional default is still useful — for a different (smaller) buyer class

The buyer class that *does* accept REC-based attribution is **mid-tier industrial buyers under softer ESG reporting frameworks** — domestic Indonesian buyers, smaller export markets without strict scope-2 attestation requirements, voluntary corporate ESG reporters. For this class, the v4.0 proportional GEAS allocation is sufficient as a directional signal. Empirical refinement is overkill.

The proportional default **stays in place** as v4.0 already implemented. F13's deprioritization is specifically about **not adding the empirical alternative**, not about removing the proportional baseline.

### 4. Effort budget reallocation

The ~0.5–1 day of v4.0.5 effort that F13 would have consumed reallocates to higher-value work surfaced by the May 2026 strategic reprioritization:

- **Buyer-procurement-requirements dimension** (new feature for v4.3 §7.2) — distinguishes hyperscaler-grade vs CBAM-attestable vs REC-acceptable buyer classes per site. This is what actually drives whether the financing-stack levers can pull for a given site.
- **`pr112_loosened_2026` scenario** (new realistic baseline) — reflects late-2025 trajectory of Perpres 112 revision direction.

Both of these are downstream of buyer-class procurement requirements; F13's deferred effort can rotate into the buyer-class taxonomy work instead.

---

## Concrete actions for the v4.x roadmap

### What to remove from `v4_0_dashboard_fixes_spec.md`

Strike the F13 implementation work:

- `geas_alloc_empirical()` function definition
- `distance_decay` and `region_multiplier` parameters
- `REGION_LOAD_CENTRE_LATLON` constants (Jakarta / Medan / Makassar / etc. as distance-decay anchors)
- New scorecard columns: `geas_alloc_empirical_gwh`, `green_share_geas_empirical_pct`, `geas_allocation_used`
- v4.1a UI toggle for allocation method

Keep:
- v4.0's existing `geas_alloc_proportional_gwh` and `green_share_geas_proportional_pct` columns
- `build_fct_site_scorecard` proportional-only computation (no `geas_allocation_used` column needed if only one method is implemented)

### What to add as a deferral note

Mark the F13 section in `v4_0_dashboard_fixes_spec.md` as:

> **DEFERRED to v5.0+ pending user demand (decided 2026-05-08)** — see `refinement/F13_GEAS_deprioritization_2026-05-08.md` for full reasoning. Empirical-allocation methodology preserved here for reference; not built. Proportional default in v4.0 remains as the operative GEAS allocation.

### What to update in `dashboard_roadmap_v4_v5.md`

If F13 appears in v4.0.5 release scope: remove from the v4.0.5 deliverable list, move to v5.0+ or remove entirely. Note in roadmap notes that the deferral is one of the May 2026 strategic reprioritization changes.

### What to do with the GitHub issue

Recommend: add the `deferred` label to issue #15 ([shaanbarca/eez#15](https://github.com/shaanbarca/eez/issues/15)). Optionally close as deferred. Don't delete the issue — keep it as the canonical record if F13 is ever revisited.

---

## When to revisit (criteria for un-deferring)

F13 implementation should be reconsidered if any of these become true:

1. **A buyer class that accepts REC-based attribution emerges as the dashboard's primary use case.** E.g., domestic Indonesian industrial buyers under emerging ESG reporting frameworks, or a regional Asia-only ESG taxonomy that relies on annual REC matching.
2. **PLN's GEAS framework evolves to support hourly matching or additionality verification** — at that point empirical-allocation precision could become load-bearing again.
3. **A user explicitly requests the empirical alternative** for a specific use case where allocation method changes the analytical conclusion.

Until then: F13 stays deferred. The v4.0 proportional baseline is sufficient for the directional GEAS signal it provides.

---

## Connections

- **Wiki strategic doc** (full May 2026 reprioritization): `refinement/strategic_reprioritization_2026-05-08.md` — Section A1 covers this deprioritization in the context of the broader strategic shift. This file extracts and expands on Section A1 specifically.
- **Wiki concept page**: `concepts/Perpres 112-2022.md` (companion wiki page) — covers the GEAS / REC framework in the context of Indonesian renewable energy regulation and why hyperscalers reject it.
- **Wiki concept page**: `concepts/Transition Finance.md` — covers the buyer-procurement-requirements hierarchy (hyperscaler-grade > CBAM-attestable > REC-acceptable) that drives the deprioritization logic.
- **GitHub issue**: [shaanbarca/eez#15 (F13)](https://github.com/shaanbarca/eez/issues/15) — recommend `deferred` label.
- **Related (replacement work)**: the buyer-procurement-requirements dimension proposed for v4.3 §7.2 in the strategic reprioritization doc — Section B2. This is where the F13 effort budget reallocates.
