---
type: synthesis
synthesis_subtype: feature-plan
name: v4.3 Methodology Transparency Refinement
description: Paired feature plan for v4.3 covering M-AT1 (Substation Utilization Transparency) + M-T1 (Transmission Feasibility Action-Flag Flip). Both surface RUPTL-inferred defaults to the user — badged by confidence, methodology-linked, and overridable where appropriate. Establishes the assumption-transparency pattern for further inferred-default rollouts (M-AT2 GEAS, M-AT3 demand intensity, etc.).
tags: [feature-plan, dashboard, methodology, transparency, substation, transmission, ruptl, grid, v4.3, persona-dfi, persona-energy-economist]
research_method: feature-plan
research_date: 2026-05-10
relates_to_milestone: M-AT1 (Substation Utilization Transparency) + M-T1 (Transmission Feasibility Action-Flag Flip), both proposed for v4.3 release theme "Methodology Transparency"
syntheses_consulted:
  - "[[Indonesia Dashboard Methodology Review]] — finding 13 (GEAS allocation isn't how PLN actually allocates) is the closest precedent for the pattern"
  - "[[Indonesia Grid Infrastructure and Renewable Adoption]] — structural framing of why grid build-out is the binding constraint and why §V.11 corridor feasibility is load-bearing"
  - "[[The Grid Bottleneck Decomposition]] — substation + transmission as named components with anchored cost / lead-time"
  - "[[Electricity Grids]] — first-principles primer"
external_inputs_consulted:
  - "eez/docs/METHODOLOGY_CONSOLIDATED.md §8.4a (substation utilization tiers, V3.8) + §8.5a (F5 §V.9 transmission link feasibility, 2026-05-09)"
  - "eez/EXECUTIVE_SUMMARY.md (audience, what's shipped, action flag taxonomy)"
  - "eez/PERSONAS.md (P1 Energy Economist, P2 DFI Infrastructure Investor, P4 IPP / Solar Developer primarily; P3 Policy Maker / P5 Industrial Investor / P6 Green Industry Roadmap Planner secondary)"
  - "eez/docs/refinement/RUPTL_INTEGRATION_review_2026-05-10.md (the fact-check review that surfaced both gaps)"
personas_affected: [DFI Infrastructure Investor (P2, primary for both), Energy Economist (P1, primary for both), IPP / Solar Developer (P4, secondary), Policy Maker (P3, low), Industrial Investor (P5, low), Green Industry Roadmap Planner (P6, low)]
status: proposed
---

# v4.3 Methodology Transparency Refinement

## Contents

- [Situation](#situation)
- [What needs to happen](#what-needs-to-happen)
- [Why it matters](#why-it-matters)
- [How to do it](#how-to-do-it)
- [Feature M-AT1: Substation Utilization Transparency](#feature-m-at1-substation-utilization-transparency)
- [Feature M-T1: Transmission Feasibility Action-Flag Flip](#feature-m-t1-transmission-feasibility-action-flag-flip)
- [Why these two are paired](#why-these-two-are-paired)
- [Joint milestone scope (v4.3 release theme)](#joint-milestone-scope-v43-release-theme)
- [Risks and open product questions](#risks-and-open-product-questions)
- [Pattern: why these are the prototypes](#pattern-why-these-are-the-prototypes)
- [Connections](#connections)
- [Sources](#sources)
- [Open questions](#open-questions)

## Situation

**Topic state (from wiki + dashboard methodology):** The dashboard makes two structurally similar inferential leaps from RUPTL data to action recommendations. Both leaps are defensible at the directional level, both are calibrated rather than measured, and both currently land in the UI as if they were authoritative facts.

1. **Substation utilization (V3.8, §8.4a):** RUPTL upgrade plan → utilization tier (`uprate = 85%`, `extension = 75%`, `line_bay = 70%`, `matched but no upgrade = 55%`, unmatched = 65% fleet default) → `available_capacity_mva` → `invest_substation` action flag. The empirical signal (PLN prioritizes uprates for capacity-constrained assets) is real. The specific tier values are calibrated guesses; no public dataset confirms "uprate-planned substations average 85% utilization in Indonesia."
2. **Transmission link feasibility (F5 / PR #33, §8.5a, 2026-05-09):** RUPTL §V.9 / §V.11 corridor status → region-worst-case rollup → `comparator_feasibility` column. Today the column is *informational only* — the action-flag flip (use captive cost as comparator when feasibility is `pln_tariff_infeasible_captive_only`) is **explicitly deferred** because *"this changes outputs — sites in Sulawesi might switch from `invest_transmission` to a captive-cost-based label. Risky to ship without domain validation."*

**Dashboard state:**

For substation utilization (M-AT1):
- Inference is built; per-substation tier applied via `fct_substation_ruptl_signal`
- A **global override exists** (`assumptions.substation_utilization_pct` slider) — but it's all-or-nothing across all sites
- **Per-substation override is missing**, **confidence visibility is partial** (narrative only, no badge), **methodology link from UI is missing**

For transmission feasibility (M-T1):
- Region-rollup is built; columns are in the API + types
- Action-flag flip is **deferred pending domain validation**
- 8 seed entries in `data/raw/ruptl_v9_transmission_links.csv` are manually compiled readings of RUPTL prose (`tidak layak`, `kajian lebih lanjut`)
- Nothing rendered in the UI today

The result is methodology-heavy but visibility-light for both. Users with domain knowledge cannot intervene where they have ground truth (M-AT1); reviewers cannot challenge the calibrated tier values without reading the full methodology doc (M-AT1); and the dashboard tells the wrong story for the most consequential industrial sites in Indonesia — the Sulawesi nickel cluster — because Feed 3's structurally-correct comparator flip isn't yet wired (M-T1).

## What needs to happen

Both features ship as a paired v4.3 release theme (*"Methodology Transparency"*). Sequenced order:

1. **Build the shared confidence-tier UI pattern** — a 3-tier badge component (`PLN-published` / `RUPTL-estimated` / `User-set`) plus a Methodology Drawer side-panel reusable across multiple inferred-default disclosures. Single design lift.
2. **M-AT1 — Substation Utilization Transparency**: per-substation override input on the Score Drawer Grid tab; badge surfaces alongside utilization narrative; methodology link opens drawer to §8.4a.
3. **M-T1 — Transmission Feasibility Action-Flag Flip**: domain-validate the 8 seed entries (Tier 1 = expert-confirmed, Tier 2 = single-source, Tier 3 = inferred-from-RUPTL-prose-only). Wire the action-flag flip per §8.5a. Render `comparator_feasibility` on the Score Drawer with the same confidence-tier badge.
4. **Methodology section updates** — `METHODOLOGY_CONSOLIDATED.md` §8.4a gains an "Override and confidence tiering" sub-section; §8.5a's "Action-flag flip deferred" paragraph gets replaced with the as-shipped logic.
5. **URL state** — both features encode their overrides / validation acknowledgements into URL state so shareable links carry them.
6. **Reset to defaults** — global "Reset all overrides" affordance.

Out of scope (deferred):
- Backend account-state persistence of overrides — URL state only for v4.3.
- Per-link transmission match (replaces region rollup) — v4.4 captive deep-dive will produce the inter-substation graph; M-T1 stays at region-rollup resolution.
- Extending the pattern to other inferred defaults (M-AT2 GEAS, M-AT3 demand intensity, M-AT4 captive cost) — separate feature plans.

## Why it matters

The dashboard's stated objective per `EXECUTIVE_SUMMARY.md`: *"How much will electricity cost here, can we get clean energy, and how exposed is this site to EU CBAM?"* Both inferences directly determine the answer to *"can we get clean energy?"* for the most consequential sites:

- **Without M-AT1**, sites whose investment thesis turns on substation headroom (DFI investor portfolio screening, IPP pre-feasibility) get a confident answer that cannot be challenged with ground truth. The dashboard's confidence and the underlying signal's confidence are mismatched.
- **Without M-T1**, sites in Sulawesi (the largest single decarbonization gap in Indonesia per JETP CPS) are recommended actions PLN's own plan flags as infeasible. The dashboard tells DFI investors to fund transmission projects PLN hasn't FID'd. This is the **structurally wrong story** for the cluster of sites that matter most.

**Persona moves on the Readiness scale:**

| Persona | Current | After M-AT1 + M-T1 | Why |
|---|---|---|---|
| **DFI Infrastructure Investor (P2)** | 85% | **~92%** | Both features serve the same core decision variable (`grid_integration_category` + sub-flag). Override + correct comparator flip turn the screen from "directionally useful" into "due-diligence-grade." |
| **Energy Economist (P1)** | 85% | **~89%** | Targeted sensitivity analysis for both inferred defaults. Confidence-tier badge tells them which assumptions are most outcome-determining. |
| **IPP / Solar Developer (P4)** | 85% | **~88%** | Pre-feasibility screening becomes more accurate when developers can substitute local intelligence. |
| **Policy Maker (P3)** | 85% | ~86% | Marginal — citation discipline improves; aggregates dominate. |
| **Industrial Investor (P5)** | 85% | ~85% | Site economics dominate over substation- or corridor-specific signals. |
| **Green Industry Roadmap Planner (P6)** | 87% | ~87% | Aggregates again. |

Combined, these features close approximately half of the assumption-transparency gap for the two primary personas, and establish the pattern (badge + override + methodology link) for closing the remainder across other inferred defaults.

## How to do it

The shared design pattern is the v4.3 architectural lift. Both features ride on top of it.

### Shared design pattern (build once, reuse)

| Component | Description | Effort |
|---|---|---|
| **Confidence-tier badge component** | 3-tier (`PLN published` green, `RUPTL estimated` amber, `User set` blue, plus `Inferred — pending validation` for M-T1's Tier 3 entries). Renders at small/medium sizes. | Small |
| **Methodology Drawer** | New side-panel `<MethodologyDrawer>` populated from methodology-doc content at build time. Reusable across all inferred defaults. v4.3 ships it for §8.4a + §8.5a; v4.4+ extends to other sections. | Medium |
| **URL state encoding** | Compact `?ovr=GI_CILEGON:72,...&val=link_sumatra_java:T1...` syntax. Round-trip-safe. | Small–Medium |
| **Live recompute infrastructure** | Override / validation change → recompute downstream variables (action flag, available capacity, comparator feasibility) within 200ms without page reload. Existing `compute_grid_integration()` and scorecard-enricher patterns extend cleanly. | Small |
| **Global "Reset all overrides"** | One affordance in Assumptions panel; clears both M-AT1 and M-T1 user-set values. | Small |

### Per-feature levers

Beyond the shared pattern, each feature has a small number of feature-specific levers detailed in the per-feature sections below.

---

## Feature M-AT1: Substation Utilization Transparency

### Specific scope

Per-substation override of `substation_utilization_pct_effective`, surfaced on the Score Drawer Grid tab's Substation Capacity card. Override propagates through `compute_grid_integration()` to recompute `available_capacity_mva`, `grid_integration_category`, and `invest_substation` flag.

### Component table (M-AT1 specific)

| Component | Change | Reference | Effort |
|---|---|---|---|
| **Backend: schema** | Add `substation_utilization_override_pct` (nullable) and `substation_utilization_source` (enum) to `fct_site_scorecard`. | `src/pipeline/build_fct_substation_proximity.py` | Small |
| **Backend: live recompute** | Override priority extended in `compute_grid_integration()` and `compute_lcoe()`. | `src/dash/logic/grid.py:95`, `src/dash/logic/lcoe.py` | Small |
| **Frontend: substation card** | Override input + reset link + badge + "How is this estimated?" link → Methodology Drawer with §8.4a content. Override input collapsed behind "Customize" toggle by default (avoid weighting down casual readers). | `frontend/src/components/panels/scoredrawer/GridTab.tsx` | Medium |
| **Map / table integration** | Map fill colour and Ranked Table column reflect override-recomputed values. New filterable column `substation_utilization_source`. | Map renderer + Ranked Table column config | Small |

### Methodology delta — §8.4a

`METHODOLOGY_CONSOLIDATED.md` §8.4a gains a new sub-section **§8.4a.1 Override and confidence tiering** (~80 lines):

> The tier-derived utilization values in §8.4a are *estimates* — calibrated to the empirical signal that PLN prioritizes uprates for capacity-constrained substations, but not measured against a publicly available dataset of actual utilization. To make this transparent and actionable, every substation utilization value is tagged with a confidence source:
>
> | Source | Meaning | Default colour |
> |---|---|---|
> | `pln_published` | Substation has a PLN-published nameplate AND historical loading data (rare in current pipeline) | Green |
> | `ruptl_estimated` | Tier inferred from RUPTL upgrade plan — the V3.8 default for matched substations | Amber |
> | `fleet_default` | Substation not matched to any RUPTL upgrade row — defaults to 65% | Amber |
> | `user_set` | Analyst has entered a specific value via the dashboard UI | Blue |
>
> **Override priority** (extends §8.4a):
> 1. If `substation_utilization_override_pct` is set, use it.
> 2. Else if `assumptions.substation_utilization_pct` differs from fleet-default 65% (global slider), use the slider value uniformly.
> 3. Else use the per-substation tier from `substation_utilization_pct_effective`.
>
> **Justification for the tier values** (calibration record, not measurement): the 85 / 75 / 70 / 55 / 65 values were chosen to (a) preserve directional ordering aligned with PLN's own capex prioritization signals, (b) span a plausible range (55–85%) consistent with utility-industry rule-of-thumb ranges in mid-development markets, (c) produce a `none (matched)` value below the fleet default to distinguish "matched but no upgrade" (mild headroom) from "unmatched" (no information). These values should be treated as defensible defaults, not measurements.

---

## Feature M-T1: Transmission Feasibility Action-Flag Flip

### Why this is structurally distinct from M-AT1

M-AT1 makes an inferred *parameter* (utilization %) overridable. M-T1 wires a **deferred output flip** that's already been speced and built but explicitly left informational pending validation. The blocker is **not** engineering — it's that flipping the action flag changes the headline finding for ~8–15 sites (mostly Sulawesi nickel) and shouldn't ship without confidence in the underlying RUPTL §V.9 / §V.11 reading.

So M-T1's critical path is **validation**, not code.

### Validation prerequisite (gating step)

The 8 seed entries in `data/raw/ruptl_v9_transmission_links.csv` need confidence tagging:

| Entry | Currently flagged | Validation needed |
|---|---|---|
| Sumatra–Java HVDC SKTET (§V.9.2 / §V.11.2) | `under_study` | T1 expert review — IESR or similar |
| Java–Lombok | `under_study` | T2 single-source confirmation |
| Bangka–Belitung | `under_study` | T2 |
| Sulawesi internal Tongkonan–Bangkir (§V.9.4) | `not_feasible` | **T1 critical** — drives the highest-impact action-flag flip for Morowali / Weda Bay |
| Sulbagsel–Baubau floating tower | `under_study` | T2 |
| Seram–Ambon deep-sea trench (§V.9.6) | `under_study` | T2 |
| Malaka GI (§V.11.3 if cross-border) | `under_study` | T2 |
| Papua–PNG (§V.11.3) | `cross_border` | T1 expert review — Papua decarbonization is a separate frame |

**Validation source candidates:** IESR (Indonesia Energy Studies Institute), ESDM transmission planning division contacts, JETP CPS transmission annexes, IEA SEA Energy Outlook 2024 grid build-out section. Outreach window: pre-v4.3 spec finalization.

### Specific scope

Once validated:

1. **Action-flag flip wired** — when `comparator_feasibility = pln_tariff_infeasible_captive_only`, replace PLN tariff with captive cost in `compute_action_flag()`. `invest_transmission` flag becomes `not_competitive` or `captive_locked` for affected sites.
2. **UI rendering** — `comparator_feasibility` surfaces on Score Drawer Grid tab with confidence-tier badge. Tier 3 entries show *"Inferred from RUPTL §V.9 / §V.11 prose — pending domain validation"* with the same badge UX as M-AT1.
3. **Map + Ranked Table** — affected sites get a visible "transmission-blocked" indicator on the map; Ranked Table gains a `comparator_feasibility` column.
4. **Methodology disclosure** — same Methodology Drawer pattern, populated from §8.5a content.

### Component table (M-T1 specific)

| Component | Change | Reference | Effort |
|---|---|---|---|
| **Domain validation** | 8 seed entries → T1/T2/T3 confidence tagging via expert outreach. **Bottleneck on calendar, not code.** | `data/raw/ruptl_v9_transmission_links.csv` validation column | Medium (calendar-bound) |
| **Backend: action-flag flip** | Extend `compute_action_flag()` in `src/model/basic_model.py` to use captive cost as comparator when feasibility is `pln_tariff_infeasible_captive_only`. | `src/model/basic_model.py::compute_action_flag()` | Small |
| **Backend: validation enum** | Add `feasibility_validation_tier` enum (`expert_confirmed` / `single_source` / `prose_inferred`) to `fct_transmission_link_ruptl_signal`. | `src/pipeline/build_fct_transmission_link_ruptl_signal.py` | Small |
| **Frontend: substation/grid card** | New "Transmission Outlook" section on Grid tab — comparator status + validation badge + methodology link. | `frontend/src/components/panels/scoredrawer/GridTab.tsx` | Small–Medium |
| **Map indicator** | Add a small icon or border treatment to sites whose recommended transmission is `not_feasible` or `under_study`. | Map renderer | Small |

### Methodology delta — §8.5a

`METHODOLOGY_CONSOLIDATED.md` §8.5a's *"Action-flag flip deferred"* paragraph gets **replaced** with as-shipped logic:

> **§8.5a.1 Action-flag flip wiring (v4.3)**
>
> When `comparator_feasibility = pln_tariff_infeasible_captive_only`, `compute_action_flag()` substitutes the local captive cost (`captive_coal_cost_proxy_usd_mwh` or site-specific override) for the PLN tariff comparator. Sites previously flagged `invest_transmission` re-evaluate against captive cost; depending on local solar LCOE, they may flip to `not_competitive`, `captive_locked` (new flag), or remain solar-attractive on captive comparator basis.
>
> **Validation tiering** — every transmission link feasibility entry carries a `feasibility_validation_tier` source enum:
>
> | Tier | Meaning | UI badge |
> |---|---|---|
> | `expert_confirmed` | Validated against domain expert (IESR, ESDM, JETP CPS authors) | Green |
> | `single_source` | Single-source confirmation (RUPTL prose + one corroborating reference) | Amber |
> | `prose_inferred` | RUPTL prose only — manual reading of §V.9 / §V.11 status text | Red |
>
> Tier-3 (`prose_inferred`) entries are flagged in the UI as *"Inferred — pending domain validation"* and downstream action-flag flips for these entries are reversible by user override.

---

## Why these two are paired

Three reasons to ship M-AT1 and M-T1 together as a v4.3 release theme:

1. **Shared design pattern.** Both depend on the confidence-tier badge + Methodology Drawer + URL state pattern. Building that infrastructure once and exercising it twice is materially cheaper than two separate releases.
2. **Mutually-reinforcing narrative.** A v4.3 substack post titled *"How a dashboard handles assumptions it can't prove"* lands stronger with two demonstrated examples than one. M-AT1 shows it for an inferred parameter; M-T1 shows it for a deferred output flip. Same template, different shape.
3. **Captive deep-dive (v4.4) consumes both.** v4.4's per-site captive economics needs correct site classification (which sites are captive-realistic) as input. If M-T1's flip lands in v4.4, the captive deep-dive starts on a moving target. Better to flip first, then deepen.

## Joint milestone scope (v4.3 release theme)

**Release theme:** *"Methodology Transparency"* — the v4.3 release in which the dashboard graduates from "methodology-heavy and visibility-light" to "methodology-heavy with visibility-and-overridability."

**In scope:**
- Shared confidence-tier badge component
- Shared Methodology Drawer side-panel (populated initially from §8.4a + §8.5a)
- M-AT1: per-substation utilization override + badge + methodology link (Score Drawer Grid tab)
- M-T1: transmission feasibility action-flag flip + validation tier badge + methodology link
- METHODOLOGY §8.4a sub-section addition + §8.5a re-write
- URL-state persistence of overrides + validation acknowledgements
- Global "Reset all overrides" affordance

**Out of scope (deferred):**
- Backend account-state persistence
- Per-link transmission match (v4.4 — needs inter-substation graph)
- Extension to other inferred defaults (M-AT2 GEAS, M-AT3 demand intensity, M-AT4 captive cost)
- Per-site (rather than per-substation) override semantics — see Risks
- **M-AT5 rooftop estimated multiplier**: currently flagged as a *conditional* in-scope candidate — see Pattern section. Decision pending effort confirmation. If effort is ~1–2 days, include in v4.3; if heavier than expected, defer to v4.4.

**Acceptance criteria:**
- User can set GI Cilegon utilization to 72% on the Score Drawer; `invest_substation` re-evaluates within 200ms (M-AT1).
- Sites in Sulawesi whose nearest recommended transmission corridor is `not_feasible` (T1-validated) show a captive-cost-based action flag, not `invest_transmission` (M-T1).
- Confidence badge renders correctly across Map, Ranked Table, and Site Scorecard for both features.
- All 8 transmission link entries carry an explicit validation tier; T3 entries surface as *"pending validation"* in the UI.
- Sharing a URL with overrides + validation acknowledgements preserves them on a fresh load.
- "Reset all overrides" returns every site to default behavior.
- Methodology Drawer renders §8.4a + §8.5a content cleanly with link out to full methodology doc.
- Test suite passes; new override-propagation + flip-propagation tests cover downstream variable recomputation.

**Estimated effort tier: Medium-Large**
- Shared infrastructure (badge + drawer + URL state + recompute hooks): ~3–4 days
- M-AT1-specific work (override input, schema, propagation): ~2–3 days
- M-T1-specific code work (action-flag flip wiring, UI surfacing): ~2 days
- M-T1 domain validation: **calendar-bounded; depends on expert availability** — recommend opening outreach 2–3 weeks before v4.3 spec finalization
- Methodology updates + tests: ~2 days

**Total: ~9–11 working days** plus the validation calendar cycle.

**Dependencies:**
- V3.8 substation utilization tiers (already shipped — no blocker)
- F5 / PR #33 transmission link feasibility region rollup (already shipped — no blocker)
- URL state encoding pattern (verify current state machine; if absent, this release introduces it)
- Methodology doc owner sign-off on §8.4a + §8.5a edits
- Domain validation outreach for M-T1 — **start before code work**

## Risks and open product questions

**Cross-cutting (both features):**

1. **Per-substation vs per-site override semantics (M-AT1).** A substation has one physical utilization, but multiple sites may share their nearest substation. Recommend per-substation keying with "this override affects N sites that share this substation" disclosure in the UI.
2. **Override / acknowledgement persistence model.** URL state for v4.3; backend deferred until user demand surfaces.
3. **Methodology Drawer reuse scope.** Build minimally usable for §8.4a + §8.5a only. Extract into a generalized `<MethodologyDrawer>` component when M-AT2 (GEAS) lands. Avoid speculative generality.
4. **Power user vs casual reader.** Override input + badge + methodology link adds visual weight to scorecard cards. Recommend collapsing override inputs behind "Customize" toggles by default; confidence badges stay always-visible (no extra weight).

**M-AT1 specific:**
- *None additional beyond the cross-cutting items above.*

**M-T1 specific:**
- **Validation availability.** If T1 expert validation isn't achievable for the Tongkonan–Bangkir entry within v4.3's calendar window, the action-flag flip should ship with that entry **excluded** (T3-locked) until validation lands. Alternative: ship with all entries badged but action-flag flip applied only to T1-validated entries — gradual rollout.
- **Output reversibility.** Sites that flip from `invest_transmission` to `captive_locked` or `not_competitive` lose a previous "DFI infrastructure investment opportunity" framing. This is the **correct** result methodologically (PLN's plan flagged the corridor as infeasible) but is communicatively heavier than a parameter override. Recommend Score Drawer narrative treatment that explains the flip in plain language: *"PLN's RUPTL §V.9.4 flags the Tongkonan–Bangkir corridor as `tidak layak`. The realistic comparator for this site is captive coal continuation, not PLN tariff."*
- **Reverse override.** If a user has independent confirmation that a `not_feasible` corridor is actually under FID negotiation, they should be able to override the feasibility status. Same UI pattern as M-AT1's per-substation override; same URL state encoding.
- **Outreach friction.** Domain validation requires contacts the dashboard author may not currently have. Recommend opening with IESR (a known accessible institution) before exploring direct PLN engineering contacts.

## Pattern: why these are the prototypes

Substation utilization (M-AT1) and transmission feasibility (M-T1) are the **first two** of a class of inferred defaults that need transparency:

| Inferred default | Where it lives | Status | Future feature plan |
|---|---|---|---|
| Substation utilization | §8.4a tier mapping | M-AT1 (this plan) | shipped v4.3 |
| Transmission link feasibility | §8.5a F5 deferral | M-T1 (this plan) | shipped v4.3 |
| **Rooftop estimated multiplier** | §4A rooftop solar potential + `src/assumptions.py` (hardcoded). Assumptions panel currently exposes panel power, area, and layout density — but NOT the multiplier that turns the §14 geometric classifier output into a deployment-realistic nameplate. | inferred only — flagged 2026-05-11 | **M-AT5** (proposed v4.3 if effort is small; else v4.4) |
| GEAS proportional allocation | §11 + Methodology Review finding 13 | inferred only | **M-AT2** (proposed v4.4) |
| Demand intensity (KEKs: area × intensity; industrial: capacity × sectoral intensity) | §3 + EXECUTIVE_SUMMARY Known Limitations §3 | inferred only | **M-AT3** (proposed v4.4) |
| Captive coal cost defaults (only 3 anchor sites have site-specific overrides) | §13 | inferred only | **M-AT4** (proposed v4.5 alongside captive deep-dive) |
| Wind nighttime fraction (14/24 uniform) | §6A.2 + Methodology Review finding 3 | inferred only | candidate for v4.4 or v5.0 PyPSA |
| RE-addressable fraction sectoral defaults (cement 0.12, ammonia 0.10, etc.) | §14 + assumptions.py | speced, has source | low priority; values are well-cited |

### M-AT5 — rooftop estimated multiplier (late-added candidate, 2026-05-11)

The v4.1 rooftop solar potential layer (per `EXECUTIVE_SUMMARY.md` §4A — total fleet 2,743 MWp across 78/81 sites) applies a hardcoded estimated multiplier on top of the §14 geometric classifier output (the 7-category roof typology with residential-pattern filter and OSM fence-boundary clips). That multiplier is the **load-bearing parameter** that turns the geometric ceiling into a deployment-realistic nameplate — the difference between *"this much roof exists"* and *"this much is plausibly installable for solar."* It is currently invisible to the user.

The Assumptions panel today exposes three rooftop-related parameters: **panel power** (W/m² conversion), **area** (buildable footprint post-exclusions), and **layout density** (packing factor). The estimated multiplier should be a fourth user-control slider, following the same UX pattern as M-AT1.

**Why this is lower-effort than M-AT1:**
- No per-substation / per-site keying — global slider on the Assumptions panel suffices initially (subsequent per-category multipliers — `standard_roof` vs `complex` vs `conveyor` etc. — could come in a follow-on).
- No methodology drawer content beyond §4A (already documented in EXECUTIVE_SUMMARY and the rooftop spec).
- Reuses the existing Assumptions-panel slider pattern + live-recompute infrastructure (rooftop nameplate → downstream LCOE → action flag) that's already wired for the existing three parameters.
- Effort estimate: **~1–2 days** if scoped to a single global multiplier slider; **~3–4 days** if also exposing per-category multipliers behind a "Customize" toggle.

**Recommendation:** include in v4.3 scope as M-AT5 if the rooftop pipeline's recompute path can be confirmed as cheap (likely yes given the existing slider precedent). If the recompute path turns out to be heavier than expected, defer to v4.4 alongside M-AT2 / M-AT3 — same template, no design rework needed.

**Open question for the user:** what's the current default multiplier value, and is there a documented justification (calibration record, source) for it? If the value is itself an undocumented guess, that's worth surfacing in the methodology drawer alongside the slider — same disclosure discipline as M-AT1's tier-table justification block.

Each entry above is currently a **silent assumption**: user sees a number, doesn't see the inference chain, can't override at the relevant resolution. The v4.3 release theme establishes the **template** for transparency on inferred defaults:

1. **Confidence badge** distinguishing measured vs estimated vs user-set
2. **Override at the methodologically correct resolution** (per-substation, per-site, per-sector — depends on the assumption)
3. **Inline methodology link** to the canonical doc section
4. **URL-encodable state** so overrides persist in shareable links
5. **Live recompute** of all downstream variables

If M-AT1 + M-T1 land cleanly in v4.3, M-AT2 / M-AT3 / M-AT4 become structured rollouts of the same template, not bespoke designs. That's the long-term scope multiplier of getting v4.3's release theme right.

## Connections

- [[Indonesia Dashboard Methodology Review]] — finding 13 (GEAS proportional isn't how PLN allocates) is the closest precedent; the wiki has been thinking about this pattern. M-AT2 operationalizes finding 13.
- [[Indonesia Grid Infrastructure and Renewable Adoption]] — situates *why* transmission feasibility is load-bearing for DFI investors and why Sulawesi's `tidak layak` corridors are the most consequential application of M-T1.
- [[The Grid Bottleneck Decomposition]] — substation + transmission as named components with anchored cost / lead-time data the wiki carries.
- [[Electricity Grids]] — first-principles grounding for what utilization and corridor feasibility mean physically.
- `eez/docs/refinement/RUPTL_INTEGRATION_review_2026-05-10.md` — fact-check that surfaced both gaps. M-AT1 closes "Issue #1" (substation utilization direction); M-T1 closes the §V.9 / §V.11 ambiguity by forcing validation.
- `eez/docs/refinement/strategic_reprioritization_2026-05-08.md` — May 2026 reprioritization that named transparency as a v4.3 priority and shifted analytical weight onto financing-stack composition.
- **Dashboard sections affected**: METHODOLOGY §8.4a + §8.5a (sub-section additions / re-writes), GridTab.tsx (major change), AssumptionsPanel.tsx (minor change), data_loader.py + URL state, grid.py + scorecard.py (override + flip propagation), basic_model.py::compute_action_flag().

## Sources

- **Internal (wiki):**
  - [[Indonesia Dashboard Methodology Review]] (synthesis, ~395 lines, 2026-05) — finding 13 sets the precedent
  - [[Indonesia Grid Infrastructure and Renewable Adoption]] (synthesis) — DFI persona's *why-it-matters*
  - [[Electricity Grids]] (concept) — first-principles grounding
  - [[The Grid Bottleneck Decomposition]] (synthesis) — component-level cost/lead-time data
- **Dashboard docs (live):**
  - `eez/docs/METHODOLOGY_CONSOLIDATED.md` §8.4a (substation utilization tiers) + §8.5a (F5 §V.9 transmission link feasibility) + §11 (GEAS allocation, the pattern's next target)
  - `eez/EXECUTIVE_SUMMARY.md` (Known Limitations, persona summaries, action-flag taxonomy)
  - `eez/PERSONAS.md` Persona 2 (DFI, primary), Persona 1 (Energy Economist, primary), Persona 4 (IPP)
  - `eez/docs/refinement/RUPTL_INTEGRATION_review_2026-05-10.md` (fact-check that triggered this plan)
  - `eez/docs/refinement/strategic_reprioritization_2026-05-08.md` (v4.3 framing context)
- **External:** none for this plan. Validation outreach for M-T1 will surface external sources (IESR, ESDM, JETP CPS authors) — those become T1/T2 references attached to the validation tiering.

## Open questions

- **Per-substation vs per-site override resolution (M-AT1).** Recommendation in plan is per-substation; awaits user decision before implementation.
- **Override persistence (URL vs localStorage vs backend).** Recommendation: URL state for v4.3; awaits user decision.
- **Methodology Drawer reuse scope.** Build minimally for §8.4a + §8.5a; generalize when M-AT2 (GEAS) lands.
- **Default visibility of override input.** Always-visible vs collapsed-behind-Customize? Recommendation: collapsed; awaits UX validation.
- **M-T1 validation outreach plan and calendar.** Who is the primary validator for the Tongkonan–Bangkir entry? IESR is the recommended starting point but may not have specific corridor expertise. Worth opening the conversation 2–3 weeks before v4.3 spec finalization.
- **Should M-T1 ship gradually (T1-only flip first, T2 flip in patch) or all-at-once (all 8 entries flip with confidence-tier UI)?** Plan recommends all-at-once with T3 entries badged as *"pending validation"* but with the action-flag flip already applied — reversible via user override. Awaits user decision.
- **Should this plan also propose M-AT2 (GEAS) explicitly?** Currently flagged as the natural next step but not scoped. If user wants M-AT2 planned together with M-AT1 + M-T1 for sequencing visibility, that's a follow-on `feature-plan` run.
- **Cross-release dependency check** — does v4.3 multi-pathway analysis (the headline release work, with the financing/transmission/carbon/buyer/regulatory pathway dimensions) have any conflicts with Methodology Transparency Refinement landing in the same release? Recommend reviewing v4.3 spec against this plan before v4.3 sprint planning.
