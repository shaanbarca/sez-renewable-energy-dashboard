# Dashboard v4.x Reprioritization — May 2026

**Status:** strategic-direction document. To be applied as edits to `dashboard/refinement/dashboard_roadmap_v4_v5.md`, `dashboard/refinement/v4_1_foundation_spec.md`, and (when reached) the v4.3 spec.

**Audience:** Claude Code working through the dashboard implementation. Read this in full before continuing v4.1+ work.

**Date:** 2026-05-08
**Prepared during:** wiki health-check session that surfaced two ripple-effect findings in the same conversation.

---

## TL;DR — what changes and why

Two findings from the wiki work this week reshape the v4.x roadmap's narrative spine:

1. **Perpres 112 implementation reality** — the 2030 public-grid coal moratorium **is not holding**. RUPTL 2025–2034 plans 6.3 GW of *new* grid coal; captive coal nearly **quadrupled** from 5.5 GW (2019) to ~20 GW (2025); a late-2025 government draft revision would *loosen* restrictions further (adding "system reliability / urgent government needs" exemptions). Sources: [Mongabay April 2025](https://news.mongabay.com/2025/04/indonesia-defies-global-coal-retreat-with-captive-plant-boom/), [Ember Feb 2025 RUKN paper](https://ember-energy.org/app/uploads/2025/02/EN-Indonesia-RUKN-2025_14022025.pdf), [Trend Asia 2025](https://trendasia.org/en/revision-of-presidential-regulation-on-renewable-energy-legitimizes-new-coal-plants-and-false-solutions-adding-to-the-futility-of-cop30/), [CREA Nov 2025](https://energyandcleanair.org/wp/wp-content/uploads/2025/11/EN-CREA-JETP-responsive-Nov-2025.pdf), [CREA Feb 2026](https://energyandcleanair.org/publication/indonesias-captive-coal-on-the-uptick/), [Ashurst RUPTL briefing](https://www.ashurst.com/en/insights/indonesias-new-power-development-plan/). Full treatment in `concepts/Perpres 112-2022.md`.

2. **Hyperscaler / buyer-class procurement requirements** — the highest-value buyer classes (hyperscalers, CBAM-exposed exporters seeking scope-2 attestation) **reject REC-based decarbonization** as accounting greenwash. They want hourly 24/7 CFE matching, additionality, and direct PPAs — none of which Indonesia's GEAS framework provides. The dashboard's existing GEAS-fidelity work was scoped to the wrong buyer class.

**Net effect on the roadmap:** regulation is the lever that *won't* pull (it's moving the wrong direction), and REC-based features serve the wrong buyer class. **The financing stack composition (v4.3 §7.2) is now the dashboard's headline lever**, not a feature among several. Pupuk Kaltim Bontang's anchor narrative shifts from "easy because regulation will handle it" to "easy because a buyer (Japanese/Korean blue ammonia premium) pays for the lever directly."

---

## Concrete changes — edits and removals

### A. Drops (deprioritize / remove from v4.x scope)

#### A1. Drop: GEAS empirical allocation (v4.1 Finding 13 sub-item)

**Where:** `dashboard/refinement/v4_1_foundation_spec.md` and the parent [[Indonesia Dashboard Methodology Review]] Finding #13.

**Why:** Modeling the difference between proportional and empirical REC allocation is academic if the relevant buyer classes reject all REC attribution. The work was scoped under "improve fidelity of GEAS modeling"; if developers don't want GEAS, that fidelity isn't load-bearing.

**Action:**
- In v4.1 spec: remove the "GEAS empirical allocation alternative (alongside proportional default)" feature. Mark the section as "deferred to v5.0+ pending user demand."
- Keep the rest of Finding 13 (multi-buyer-class taxonomy if any) — only the empirical allocation work is removed.
- **Don't break** existing GEAS-related code in v4.0; the proportional default stays as is. The deprioritization is about *not adding* the empirical alternative.

#### A2. Demote: `pr112_strict_2026` and `pr112_full_phaseout` from primary baselines to counterfactual scenarios

**Where:** `dashboard/refinement/dashboard_roadmap_v4_v5.md` §6.2 (Architectural Foundations: pathway dimensions), §7.2 (v4.3 scope: regulatory mandate row), §7.6 ("Why v4.3 is the strongest narrative release"), §1 (refinement notes), §3 (overview table).

**Why:** Both scenarios assume PR 112 tightens. The actual late-2025 trajectory is *loosening* — the government drafted a revision that adds new exemptions. Continuing to present these as primary baselines misleads anyone reading the dashboard.

**Action:**
- In §6.2, keep the scenarios but add an explicit "(*aspirational counterfactuals — actual late-2025 trajectory is loosening; see also `pr112_loosened_2026`*)" annotation to each.
- In §7.2 / §7.6, soften the language "PR 112 reform unlocks more decarbonization than any single financing intervention" to: "*If* PR 112 reform happens, regulatory pathway unlocks more decarbonization than any single financing intervention. Late-2025 trajectory is loosening, so this is presented as counterfactual analysis — what's at stake — rather than baseline projection." Cross-reference `concepts/Perpres 112-2022.md`.

#### A3. (Already complete from prior May 2026 work — keep slim) Drop captive deep dive items in v4.4

`v4.4 §9.2` already lists these as dropped in the prior May refinement. Don't re-add. Specifically: stranded asset risk, captive plant retirement scenarios, captive vs grid arbitrage, coal supply chain mining, expanding overrides 4–6 → 10–15.

### B. Adds (new scope items)

#### B1. Add: `pr112_loosened_2026` scenario as the realistic baseline

**Where:** `dashboard_roadmap_v4_v5.md` §6.2 pathway dimensions; §7.2 v4.3 scope.

**Specification:**
```
regulatory_mandate:
    - status_quo_pr112_exempt           # current Perpres 112/2022 exemption (as today)
    - pr112_loosened_2026               # NEW: realistic late-2025 trajectory; new exemptions (system reliability, urgent gov needs); 6.3 GW new grid coal in RUPTL adds ~5-8 GW additional captive eligible
    - pr112_strict_2026                 # ASPIRATIONAL counterfactual: exemption tightened, new captive coal > 50 MW unbuildable
    - pr112_full_phaseout               # ASPIRATIONAL counterfactual: all new captive fossil unbuildable
```

For `pr112_loosened_2026`: the specific dashboard behavior is that sites with `captive_perpres_112_exempt = True` AND `commissioning_year > 2026` continue to have captive coal as the modeled incumbent (same as status quo today), AND additional sites previously assumed to *transition off* captive coal (those affected only under `pr112_strict_2026`) revert to captive coal as the modeled incumbent. The Perpres 112 revision draft explicitly adds "system reliability" exemptions which would cover most strategic-industry sites.

#### B2. Add: Buyer-procurement-requirements dimension (~1 day of new spec work)

**Where:** new feature in `dashboard_roadmap_v4_v5.md` §7.2 (v4.3 scope: pathway toggles). Add a new pathway dimension.

**Specification:**
```
buyer_procurement_requirements:
    - hyperscaler_grade            # rejects RECs; needs 24/7 CFE + additionality + direct PPA. Examples: Microsoft, Google, AWS as buyers
    - cbam_scope2_attestable       # accepts bundled RECs from new projects; needs hourly matching nice-to-have, additionality required. Examples: EU OEMs (Tesla, BMW, VW), Japanese trading houses sourcing blue ammonia
    - rec_acceptable               # accepts unbundled RECs from any source. Examples: domestic Indonesian buyers, ESG reporting-only customers
```

Per-site default: assigned based on `export_market_shares` and `product_type` — nickel sulphate to EU/US OEMs is `cbam_scope2_attestable` or `hyperscaler_grade`; blue ammonia to Japanese trading houses is `cbam_scope2_attestable`; cement to domestic market is `rec_acceptable`. Manual overrides via site-level config.

**Why this matters for the dashboard's analytical output:** the financing-stack analysis (v4.3 §7.2 financing stack columns) needs to know whether the *premium pricing* lever even applies for a given site. A REC-acceptable buyer doesn't pay a premium; a hyperscaler-grade buyer does (sometimes substantially). This is the per-site qualifier that explains why Pupuk Kaltim's single-lever close-the-gap works (Japanese blue ammonia premium exists) but Indocement requires four-lever stacking (mostly domestic, no premium buyer for low-carbon cement at scale yet).

**Effort:** ~1 day of feature spec work + data table; OEM scope-3 dataset from v4.1 already provides most input data.

### C. Promotions (elevate prominence)

#### C1. Promote: Financing stack composition is now v4.3's headline (not a section)

**Where:** `dashboard_roadmap_v4_v5.md` §7.2, §7.6, §3 (overview table), §1 (refinement notes).

**Why:** With regulation as a lever-that-won't-pull, the financing stack (concessional WACC + destination-weighted CBAM + IDX Carbon trajectory + premium pricing) is the only mechanism that closes the gap. The work was already speced; now it should be the v4.3 narrative spine.

**Action:**
- In §7.6, rewrite "Why v4.3 is the strongest narrative release" to lead with: "v4.3's central finding is which combination of financing levers closes the gap on a per-site basis, given that regulation can't be relied on. Three anchor cases tell three different stories: Pupuk Kaltim (single lever sufficient because Japanese blue ammonia premium pays for it); IMIP Morowali (architecture menu does the work, financing stack supplements); Indocement Palimanan (all four levers must stack, and even then closes the gap only partially)."
- In §3 overview table, update v4.3 description from "Multi-pathway analysis (regulatory + CCS retrofit overlays)" to "Multi-pathway analysis with **financing stack composition as the headline lever** (regulatory pathway as counterfactual; CCS retrofit overlays still in scope)."
- Substack post 1 narrative shifts from "Two ceilings — what solar can't reach, and what CCS can" to also include the financing-stack framing. Possibly retitled or split into two posts.

#### C2. Reframe anchor case narratives

**Where:** `dashboard_roadmap_v4_v5.md` §1 refinement notes (the three anchor cases description).

**Updated framing:**
- **Pupuk Kaltim Bontang** — *cheapest decarbonization in the dataset ($10–30/tCO₂ blue ammonia + Tier A CCS) closes single-lever via Japanese/Korean blue ammonia premium pricing*. The narrative isn't "PR 112 reform makes it easy" — it's "a buyer who values low-carbon ammonia exists and pays the premium directly, regardless of Indonesian regulation." Tests `buyer_procurement_requirements = cbam_scope2_attestable`.
- **IMIP Morowali** — *largest emissions volume; M30 = 1.0 power-dominant; architecture menu (scenario 5 or 6) does the work; financing stack supplements but isn't decisive*. Tests `buyer_procurement_requirements = hyperscaler_grade` for battery-supply-chain nickel.
- **Indocement Palimanan** — *Type 1 calcination chemistry; M30 = 0.12 demand-side ceiling; all four financing levers must stack and even then closes only partially because most production is domestic (no premium buyer)*. Tests `buyer_procurement_requirements = rec_acceptable` showing the limit case.

### D. No changes (these stay as currently scoped)

- v4.0.5 methodological fixes — all 13 findings except the GEAS empirical allocation sub-item
- v4.1 foundation refactor — all other items including destination-weighted CBAM, hydro hybrid, captive cost overrides for the three anchor cases (already in `v4_1_foundation_spec.md` §4.4 / §5.4)
- v4.2 project finance module
- v4.3 §7.5 CCS retrofit overlays — *unchanged in scope.* Cement kiln + ammonia SMR + steel BF stack CCS retrofits + captive coal/gas CCS retrofits + CCS basin proximity tiers all stay. CCS retrofit is still the answer for the chemistry-dominant half of the dataset
- v4.3.5 architecture menu primacy + two-ceiling decomposition output
- v4.4 RUPTL feedback + captive cost validation (already slimmed)
- v4.5 buyer pressure analytical layer
- v5.0 PyPSA dispatch (deferred post-applications)

### E. Lint findings (already applied — no action needed)

The same conversation surfaced wiki-side fixes that have already been applied by the wiki-maintaining Claude on 2026-05-08. Listed here for completeness; the receiving Claude does NOT need to act on these:

1. ✅ **`entities/Indonesia (energy case study).md`** — captive coal numbers reconciled to "25.9 GW operating + 36.7 GW total (JETP CPS Dec 2025)"; JETP date 2023 → 2025; growth framing (5.5 → 20 GW, 2019–2025) added; Perpres 112 row updated with implementation reality; link to `concepts/Perpres 112-2022.md` and `concepts/Captive Coal in Indonesia.md` added.
2. ✅ **[[Indonesia Dashboard Methodology Review]] Finding #21** — updated with 2026-05-08 note clarifying that the regulatory pathway is now counterfactual analysis (not baseline projection); cross-references this strategic reprioritization doc.
3. ✅ **`concepts/Captive Coal in Indonesia.md`** — created. Headline framing: fastest-growing coal segment in Asia, 5.5 → 20 GW (2019–2025), 173 sites (JETP CPS), mine-mouth coal sub-section, JETP scope gap, RUKN +20 GW projection, late-2025 revision direction.

---

## Headline narrative shift for v4.3

**Before this reprioritization:**
> "v4.3 is the climax — financing stack analysis with Java Sea hub timing as the binding sensitivity. The headline narrative answers 'how can Indonesia decarbonize and industrialize at the same time' with a complete and site-specific answer that distinguishes power-dominant from chemistry-dominant cases. **PR 112 reform unlocks more decarbonization than any single financing intervention.**"

**After:**
> "v4.3 is the climax — financing stack composition is the *only* lever that reliably moves Indonesian industrial decarbonization given the late-2025 reality that PR 112 is loosening, not tightening. The headline finding: **per CBAM-exposed site, only the right combination of concessional WACC + destination-weighted CBAM + IDX Carbon + premium pricing closes the gap, AND only when a premium-paying buyer class exists.** Three anchor cases show this:
>
> - **Pupuk Kaltim Bontang** — single-lever sufficient because Japanese/Korean blue ammonia buyers pay the premium directly (cbam_scope2_attestable buyer class)
> - **IMIP Morowali** — architecture menu does the work; financing stack supplements (hyperscaler-grade buyer class via battery supply chain)
> - **Indocement Palimanan** — four-lever stack required and even then closes partially because mostly domestic / rec_acceptable buyer class
>
> The regulatory pathway dimension is preserved as **counterfactual analysis** — what's at stake — but the realistic baseline is `pr112_loosened_2026`. The dashboard is honest about regulation as a lever-that-won't-pull, and shifts the analytical weight to the levers that can be pulled by individual project / buyer / financing decisions, even with policy headwinds."

This is a sharper, more defensible, and more actionable thesis than the prior framing.

---

## Effort and timing implications

**Net effort delta vs prior roadmap:**

- Drop GEAS empirical allocation: **−0.5 to −1 day** of v4.1 work
- Drop nothing else (scenarios stay, just reframed)
- Add `pr112_loosened_2026` scenario: **+0.25 day** (essentially a config flip + flag)
- Add buyer-procurement-requirements dimension: **+1 day** (spec + per-site classification + integration with financing stack)
- Promote financing stack as headline (no new code, just narrative tightening + per-site stories): **+0.5 day** (documentation + UI polish)

**Net: roughly neutral on effort.** Maybe +0.25 day. Calendar timing for v4.x core unchanged from the May 2026 ~38–53 days estimate.

**The user's value-per-day improves substantially**, however — sharper narrative, more defensible thesis, smaller chance of the dashboard being criticized for ignoring policy reality.

---

## What to do next (action items for receiving Claude Code)

1. **Read `concepts/Perpres 112-2022.md`** in full — full source-cited treatment of the implementation reality.
2. **Apply Section A edits** (drops) to `dashboard/refinement/v4_1_foundation_spec.md` and `dashboard/refinement/dashboard_roadmap_v4_v5.md`. The GEAS empirical-allocation removal from v4.1 is the biggest concrete deletion.
3. **Apply Section B edits** (adds) — `pr112_loosened_2026` scenario + buyer-procurement-requirements dimension.
4. **Apply Section C edits** (promotions) — financing stack as v4.3 headline; anchor case narrative reframing.
5. ~~**Apply Section E lint fixes**~~ — already applied; Section E now records what was done, not what to do.
6. **Append a log entry** to `log.md`:
   ```
   ## [YYYY-MM-DD] schema | Dashboard v4.x reprioritization per strategic_reprioritization_2026-05-08.md
   ```
   with bullets summarizing the changes made.
7. **Verify** that the changes are internally consistent — `pr112_loosened_2026` referenced in §6.2, §7.2, and §7.6 all align; financing-stack headline framing is consistent across narrative sections; anchor cases reframed everywhere they're mentioned.
8. **Don't change** the rest of the roadmap (v4.0.5 fixes, v4.1 other items, v4.2, v4.3 §7.5 CCS retrofit, v4.3.5, v4.4, v4.5, v5.0). The strategic shift is narrow — only the regulatory-pathway / GEAS-fidelity / financing-stack-prominence axes.

## Cross-references for context

- `concepts/Perpres 112-2022.md` — full regulatory treatment with current-state citations
- `concepts/Electricity Grids.md` — anatomy and grid-bottleneck framing (recently expanded)
- `concepts/Renewables and Grid Stability.md` — IBR / inverter / system-services framing
- `syntheses/Indonesia Grid Infrastructure and Renewable Adoption.md` — the dashboard's transmission-side counterpart
- `syntheses/Indonesia Dashboard Methodology Review.md` — Finding #21 specifically needs the update per Section E2 above
- `entities/Indonesia (energy case study).md` — entity-level summary; partially updated already
- `todo/Data Center Extension.md` — data-center / hyperscaler-PPA backlog (not on critical path for v4.x; the buyer-procurement-requirements work in §B2 is the closest dashboard touch-point until that backlog is picked up)
