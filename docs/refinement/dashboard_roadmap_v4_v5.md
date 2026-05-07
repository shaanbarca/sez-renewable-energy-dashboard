# Dashboard Roadmap: v4.0.5 → v5.x (Refined)

**Status:** Living document. Refined post-[[Indonesia Dashboard Methodology Review]].
**Time horizon:** ~14 weeks for v4.x core (May–August 2026), v5.0 post-applications (Spring 2027).
**Architectural principle:** Foundation-first, then feature layers. Avoid rework by getting core abstractions right early.
**Velocity assumption:** Claude Code as implementation partner; aggressive but realistic timelines.

**Refinement note (vs roadmap baseline):** This refined roadmap supersedes the original `dashboard_roadmap_v4_v5.md`. The adjustments surfaced in [[Indonesia Dashboard Methodology Review]] §Adjustments needed are integrated: a new v4.0.5 release (current-dashboard methodological fixes) inserted before v4.1; v4.3 gains the regulatory pathway dimension; v4.4 includes the RUPTL → demand → RUPTL feedback loop; v4.5 buyer-pressure data work splits forward to v4.1; the architecture-menu primacy decision is sequenced as a v4.3.5 bridging release.

**Further refinement (May 2026 — scope discipline):**
1. **Dashboard scope locked to power-side + CCS retrofit.** The line that holds is *overlay on existing infrastructure (in)* vs *process change (out)*. Captive-power CCS retrofit (coal + gas) and process-stack CCS retrofit (cement kiln, ammonia SMR, steel BF) are all in scope as capture+T&S overlays. Process chemistry change (alt fuels, SCM, DRI-EAF, inert anodes, green H₂ as chemistry substitute) is out of scope — flagged in Score Drawer with cross-reference to Mission Possible Partnership / IEA / ETC. See [[Carbon Capture and Storage for Indonesian Industrial Decarbonization]] for the methodology source.
2. **v4.3 §7.5 rescoped** as "CCS retrofit scenarios — captive power and process stacks." Drops biomass feedstock proximity, blue/green H₂ flip-point, 4-pathway pathway-stack. Adds captive coal+CCS, captive gas+CCS, cement kiln+CCS, ammonia SMR+CCS, steel BF+CCS retrofit modeling — all as overlays gated by storage proximity. **Pupuk Kaltim Bontang at Tier A (50 km from Tangguh) is the anchor case — cheapest decarbonization in the dataset at $10–30/tCO₂.**
3. **v4.3.5 extended** with the two-ceiling decomposition output (5 derived columns: `achievable_re_blend_pct`, `dispatchable_residual_pct`, `dispatchable_backup_type`, `dispatchable_residual_addressable_via_ccs`, `dispatchable_residual_addressable_pct`, plus headline `dashboard_addressable_cbam_relief_pct`). Surfaces what the dashboard already imposes mechanically (M30 demand-side + supply-side solar-share cap) as a unified per-site output.
4. **PyPSA PoC reverted from v4.4 to v5.0.** Schedule risk on PyPSA learning curve outweighs application-narrative benefit. v4.4 stays focused on captive deep dive + RUPTL feedback. v5.0 absorbs both Phase 1 PoC and Phase 2 multi-site, post-applications.
5. **v5.3 removed.** Process chemistry change is out of dashboard scope per the locked boundary; v5.3's prior remit (sectoral decarbonization deep modeling) is no longer dashboard work. The wiki synthesis [[Carbon Capture and Storage for Indonesian Industrial Decarbonization]] carries the broader narrative; process pathways flagged with MPP/IEA/ETC pointers.

**Further refinement (May 2026 — anchor cases + financing stack + v4.4 slim):**
6. **Three anchor cases threaded through every release as the validation set:**
   - **Pupuk Kaltim Bontang** (ammonia, East Kalimantan, Tier A CCS proximity 50 km from Tangguh) — **cheapest decarbonization opportunity in the Indonesian dataset** at $10–30/tCO₂ blue ammonia. Tests CCS retrofit overlay + destination-weighted CBAM + financing stack at the easy end. Captive gas LCOE captured in v4.1 §5.4.
   - **IMIP Morowali** (nickel RKEF, Sulawesi Tengah) — *largest emissions volume per site*; tests architecture menu (scenario 6 if Lahendong–Morowali geothermal links work, scenario 5 fallback); M30=1.0 power-dominant logic; Tier C CCS gating sanity check (`captive_coal_ccs_retrofit_eligible = False`). Captive coal LCOE captured in v4.1 §4.4.
   - **Indocement Palimanan** (cement, West Java, Tier B CCS proximity) — canonical "calcination chemistry" Type 1 case; tests M30 = 0.12 demand-side ceiling, cement kiln CCS retrofit overlay, and Java Sea hub FID timing sensitivity.
   Each release includes spot-check validation against these three sites; the substack posts feature them as anchor narratives.
7. **v4.1 §4-§5 captive power coverage extended** to add Krakatau Posco (captive coal supercritical, Java steel BF-BOF) and Pupuk Kaltim Bontang (captive gas CCGT, ammonia anchor case). Anchor cases now have site-specific captive cost overrides in v4.1.
8. **v4.3 sharpened** with explicit per-site **financing stack computation**: concessional WACC + destination-weighted CBAM + IDX Carbon trajectory + premium pricing → composed into a single "stacked economics" output. **Java Sea hub FID timing as a sensitivity input** gating Tier B sites for cement / steel / ammonia CCS retrofit.
9. **v4.4 slimmed** from 5–6 days to 2–3 days. **Drop:** stranded asset risk, captive plant retirement scenarios, captive vs grid arbitrage analysis, most public disclosure mining. **Keep:** RUPTL feedback loop + v4.1 captive cost validation against JETP CPS Figure 5.2.2-1 (LCOE for supercritical coal at different coal prices and carbon prices). Reasoning: most chemistry-dominant sectors (cement, Java ammonia) are grid-connected, not captive; v4.0.5/v4.1 captive cost modeling already covers nickel adequately.

The roadmap preserves the original structure; refinements appear inline with **(Refined)** markers and as new release entries.

---

## Table of Contents

| § | Section |
|---|---|
| 1 | Strategic Framing |
| 2 | Architectural Foundations (build right once) |
| 3 | Roadmap Overview Table |
| 4 | v4.0.5: Current Dashboard Methodological Fixes (Refined — new release) |
| 5 | v4.1: Foundation Refactor + Methodology Refinements |
| 6 | v4.2: Project Finance Module |
| 7 | v4.3: Multi-Pathway Analysis (Refined — regulatory dimension + CCS retrofit scenarios §7.5) |
| 8 | v4.3.5: Architecture-Menu Primacy (Refined — new bridging release) |
| 9 | v4.4: RUPTL Feedback + Captive Cost Validation (Refined — slimmed May 2026) |
| 10 | v4.5: Buyer Pressure & Supply Chain Layer (Refined — analytical layer only; data lands in v4.1) |
| 11 | v5.0: PyPSA Dispatch Integration |
| 12 | v5.1+: Future Possibilities |
| 13 | Cross-Cutting: Data Sources & Refresh Cadence |
| 14 | Cross-Cutting: Persona Coverage Evolution |
| 15 | Cross-Cutting: Substack Content Calendar |
| 16 | Decision Points & Branching Logic |
| 17 | Open Questions for Knowledge Base Review |

---

## 1. Strategic Framing

### 1.1 Why a roadmap rather than one big spec

The dashboard's analytical core has multiple interconnected dimensions: cost comparison framework, project finance metrics, captive generation arrangements, CBAM and carbon pricing, financing pathways, supply chain pressure. Trying to ship all of these in one v4.2 release creates three problems:

**Problem 1: Scope creep.** Each addition tempts further additions. "We have captive coal cost; we should also segment captive gas. We have CBAM; we should add domestic carbon pricing scenarios. We have project finance; we should add corporate finance toggle." This is how a 4-week feature becomes a 4-month feature.

**Problem 2: Application timing pressure.** MIT Sloan and HKS R2 deadlines fall in early-to-mid January 2027. Essay writing season is September–November 2026. That means meaningful feature work has a hard deadline of August 2026. A roadmap forces honest sequencing decisions before time gets compressed.

**Problem 3: Architectural risk.** If v4.2 builds project finance metrics on the existing single-LCOE-vs-BPP framework, then v4.3 wants to add captive coal comparison, the project finance code has to be rewritten. Better to refactor the comparison framework first, then build everything on top.

### 1.2 Velocity assumptions

This roadmap assumes Claude Code as the implementation partner. With clear specs and good architectural foundations, Claude Code compresses pure code work substantially:

- Cash flow projections, calculation logic, test suites: 3–5x faster than manual
- Schema migrations, data pipeline integration: 3–4x faster
- Frontend components with established patterns: 2–3x faster
- Data compilation, methodology decisions, validation against benchmarks: 1x (still human time)

**What this means in practice:** A "3–4 week feature" in manual-coding terms becomes 7–10 days when most of the work is code. When the work is data compilation or methodology decisions, the compression is smaller. Time estimates throughout this roadmap reflect Claude Code velocity for code-heavy work and standard velocity for data-heavy work.

### 1.3 The narrative arc (Refined)

The roadmap tells a story across releases:

- **v4.0.5: "Methodological consistency."** *(Refined — new release)* Close 13 methodological gaps surfaced in the wiki review. Lands in parallel with v4.1.
- v4.1: "Better foundations. The comparison framework was too simple. Here's a richer one."
- v4.2: "Investment decision support. Beyond LCOE to actual project finance metrics."
- v4.3: "Multi-pathway analysis. Different sites need different interventions; the tool now shows which." *(Refined — adds regulatory dimension)*
- **v4.3.5: "Architecture-menu primacy."** *(Refined — new bridging release)* Make the wiki's six-scenario architecture menu first-class. Cross-walk action flags onto scenarios.
- v4.4: "Captive generation deep dive. The hidden majority of Indonesian industrial electricity demand." *(Refined — adds RUPTL feedback loop + PyPSA single-site PoC)*
- v4.5: "Supply chain pressure as decarbonization driver. Beyond carbon pricing." *(Refined — analytical layer only; OEM scope-3 data lands in v4.1)*
- v5.0: "Hourly dispatch optimization. Real grid simulation, not just annual averages."

Each release has a coherent thesis. Each can stand alone as a contribution. Together they build progressively more sophisticated analytical capability.

### 1.4 What this is NOT

- Not a binding commitment to ship every release in this timeline
- Not exhaustive of every possible feature
- Not independent of feedback from users, advisors, knowledge base review
- Not a substitute for shipping (working code beats elaborate plans)

The roadmap is a north star for architectural decisions, not a contract for delivery.

---

## 2. Architectural Foundations (build right once)

These are the core abstractions that need to be correct from the start because every later feature depends on them. Get these wrong and v4.3+ requires significant rework.

### 2.1 Cost Comparison Framework

The dashboard outputs solar costs and incumbent costs. Both have multiple variants depending on use case. Get this abstraction right early.

**Solar cost variants** (computed once, used everywhere):
```
solar_cost_generation_only          # pure plant LCOE
solar_cost_delivered                # + transmission
solar_cost_firm_partial_storage     # + 4-hour battery for evening peak
solar_cost_firm_baseload_storage    # + 8-hour battery for near-baseload
```

**Incumbent cost references** (per site, multiple may apply):
```
incumbent_pln_bpp                          # PLN regional average cost
incumbent_pln_marginal_daytime             # (Refined) PLN avoided generation cost — solar hours
incumbent_pln_marginal_nighttime           # (Refined) PLN avoided generation cost — non-solar hours
incumbent_industrial_tariff                # what grid-connected industrial pays PLN
incumbent_captive_fuel                     # specific to captive arrangement
  ├─ captive_coal_cost
  ├─ captive_gas_cost  
  ├─ captive_oil_cost
  └─ captive_hybrid_cost
```

**Carbon pricing layer** (Refined — destination-weighted, applied to incumbent):
```
carbon_pricing_scenarios:
  - none
  - domestic_low (~$5/tCO2)
  - domestic_high (~$25/tCO2)
  - destination_weighted_2025 (~$35/t for typical Indonesian nickel)
  - destination_weighted_2030 (~$70/t)
  - destination_weighted_2034 (~$130/t)
  - cbam_full_2026 ($90/tCO2 — stress test)
  - cbam_full_2030 ($150/tCO2 — stress test)
  - china_only_stress (~$12/t — sensitivity)
  - ccfd_floor (carbon contracts for difference)
```

**Export market shares layer** (Refined — replaces single eu_export_share):
```
export_market_shares_per_site:        # dict, per-market shares
  - china_stainless
  - battery_supply_chain_eu_oem
  - direct_eu_uk_us
  - korea_japan / korea_battery
  - asean_regional / domestic_indonesia / china_domestic

carbon_price_by_market:               # per-market trajectory
  - per market: {2025, 2030, 2034}
```

**Site classification** (determines which incumbents apply):
```
site_electricity_arrangement: enum
  - grid_only
  - grid_primary_with_captive
  - hybrid_captive_primary
  - pure_captive
  
captive_fuel_type: enum (when applicable)
  - coal_subcritical
  - coal_supercritical
  - natural_gas
  - oil_diesel
  - hybrid

captive_perpres_112_exempt: bool       # (Refined) regulatory variable, not just status string
```

**Why this matters architecturally:** Every feature in v4.2 through v5.0 needs these references. Build the data model once, build the calculation logic once, then compose features on top.

**(Refined) IEA-aligned column-naming convention from v4.1.** The dashboard adopts standard IEA cost terminology (LCOE / LCOS / Full System LCOE / VALCOE) as the primary column-name convention starting in v4.1, replacing both the v4.0 schema and the v4.1-baseline `lcoe_generation_*` / `lcoe_delivered_*` / `lcoe_firm_*` names. Rationale: the IEA terminology is widely used in the literature DFI analysts, energy economists, and policy makers already read; removing translation friction at the column-name level (not just UI labels) reduces onboarding cost and makes CSV exports directly usable. v4.0/v4.0.5 retain v4.0 column names for backwards compatibility; v4.1 is the cut-over with one-release deprecation aliases. v4.2+ inherits the IEA-aligned schema. Full mapping in `dashboard/refinement/v4_1_foundation_spec.md` §2.6 and §15.1.

### 2.2 Comparison Logic Pattern

For each (site, solar_variant, incumbent, carbon_scenario) tuple, compute:
- Cost differential
- Competitiveness flag (is solar cheaper)
- Required intervention (what closes the gap, if not currently competitive)

This matrix-based comparison is the foundation. Every UI view and every analytical output queries this matrix.

### 2.3 Pathway Analysis Pattern (Refined — adds regulatory dimension)

Different financing and policy pathways change different parts of the cost stack:

```
pathway_dimensions:
  solar_financing:
    - commercial_8.5%
    - concessional_5%
    - grant_equity
  
  transmission_financing:
    - project_financed
    - concessional_loan
    - outright_grant
  
  carbon_pricing:
    - none / domestic / destination_weighted / cbam_full / ccfd
  
  buyer_premium:
    - none / ev_supply_chain / corporate_voluntary
  
  regulatory_mandate:                   # (Refined) NEW dimension
    - status_quo_pr112_exempt           # current Perpres 112/2022 exemption
    - pr112_strict_2026                 # exemption tightened: new captive coal > 50 MW unbuildable
    - pr112_full_phaseout               # all new captive fossil unbuildable
```

For each combination of pathway dimensions, compute revised cost stack and competitiveness. This becomes the v4.3 multi-pathway analysis.

**Architecturally:** Implement pathway dimensions as composable modifiers, not hardcoded scenarios. Users can mix and match to explore policy combinations.

### 2.4 Architecture Menu Pattern (Refined — new section)

The wiki's six-scenario architecture menu (1 captive coal BAU through 6 solar+geothermal+battery) operationalises the question *"what's the cost-optimal long-term mix?"* differently from the dashboard's action flags (which answer *"what does this site need next?"*). v4.3.5 makes the architecture menu first-class:

```
architecture_menu:
  - scenario_1_captive_coal_bau
  - scenario_2_pln_grid_green_ppa
  - scenario_3_pure_solar_12hr_battery     # sanity-check baseline; never primary
  - scenario_4_solar_flex_coal_4hr_battery
  - scenario_5_solar_hydro_gas             # JETP least-cost for hydro-rich sites
  - scenario_6_solar_geothermal_battery    # for sites within reach of geothermal
```

For each site, all six scenarios are costed and carbon-adjusted. The cheapest scenario is the recommended architecture; action flags become tags on the cheapest scenario rather than primary outputs. v4.3.5 implements this refactor.

### 2.5 Project Finance Calculation Layer

Sits on top of cost framework. Inputs are tariff (from incumbent reference), CAPEX, OPEX, financing assumptions. Outputs are NPV, IRR, DSCR, etc.

The key architectural decision: project finance calculations should be parameterizable by:
- Tariff source (which incumbent reference is the offtake price)
- Tariff escalation scenario (Refined — flat_real / partial_reform / full_indexation)
- COD year (Refined — for CBAM trajectory alignment)
- Financing structure (project finance / corporate finance / blended)
- Debt terms (commercial / concessional / blended)

This way v4.2 builds project finance once, and v4.3 multi-pathway analysis just feeds different parameter combinations into the same engine.

### 2.6 Confidence and Provenance Tracking

Every numeric output should carry:
- Source attribution (PLN Statistik 2024 / GEM tracker / methodology default / public disclosure)
- Vintage (when data was last updated)
- Confidence flag (high / medium / low)
- Citation reference

This is non-negotiable for credibility. Build it into the data model from v4.1, not retrofitted later.

### 2.7 Site Classification Schema

The classification of each site (grid arrangement, captive fuel, sector, region, CBAM exposure, etc.) should be its own dataset, separable from the scorecard. This:

- Allows publishing the classification itself as a research artifact
- Allows updates without rerunning all scorecard calculations
- Allows other tools to reuse the classification

```
fct_site_classifications.csv:
  - site_id
  - site_name
  - sector
  - subsector  
  - region
  - grid_region
  - electricity_arrangement
  - captive_fuel_type
  - captive_capacity_mw (if applicable)
  - captive_perpres_112_exempt              # (Refined)
  - export_market_shares_json                # (Refined — replaces single eu_export_share)
  - export_market_shares_source
  - cbam_exposed (boolean)
  - tkbi_classification
  - confidence_classification
  - last_updated
```

This dataset is itself publishable on Zenodo as a standalone contribution.

---

## 3. Roadmap Overview Table

Time estimates assume Claude Code as implementation partner. "Calendar weeks" reflects realistic pace with parallel work (Systemiq day job, life). "Focused days" is total work effort.

(Refined May 2026 — table reflects scope discipline: v4.3 §7.5 rescoped to CCS retrofit overlays only; v4.3.5 extended with two-ceiling output; PyPSA reverted to v5.0; v5.3 removed.)

| Release | Theme | Focused days | Calendar | Target | Persona Impact |
|---|---|---|---|---|---|
| **v4.0** ✓ | Existing dashboard | Shipped | — | — | Baseline |
| **v4.0.5** *(Refined — new)* | Current-dashboard methodological fixes | 5–7 days | 1.5 weeks | Mid-May 2026 | All ↑ |
| **v4.1a** *(Refined 2026-05-07 — split from v4.1)* | Foundation: incumbents + IEA rename + provenance | 6–7 days | ~2 weeks | Late May 2026 | All |
| **v4.1b** *(Refined 2026-05-07 — split from v4.1)* | Foundation: destination-weighted CBAM + hydro hybrid | 5–6 days | ~1.5 weeks | Early June 2026 | All |
| **v4.2** | Project finance module (Tier 1+2) with COD-year + flat-tariff refinements | 7–11 days | 2–2.5 weeks | Mid-June 2026 | P5 (Investor) ↑↑ |
| **v4.3** *(Refined — CCS retrofit scenarios scope)* | Multi-pathway analysis (regulatory + CCS retrofit overlays: captive power and process stacks) | 12–15 days | 3–3.5 weeks | Mid-July 2026 | P3, P5, P6 ↑↑ |
| **v4.3.5** *(Refined — extended with two-ceiling output)* | Architecture-menu primacy + two-ceiling decomposition | 4.5–5.5 days | 1.5 weeks | Late July 2026 | All ↑ |
| **v4.4** *(Refined — slimmed May 2026)* | RUPTL feedback + captive cost validation | 2–3 days | 1 week | Early-August 2026 | P3, P5, P6 |
| **v4.5** | Buyer pressure analytical layer (data already in v4.1) | 3–5 days | 1.5 weeks | Mid-August 2026 | P5, P6 |
| **Apps** | Application preparation | — | Sept–Dec 2026 | Sept–Dec 2026 | (Maintenance only) |
| **v5.0 Full** *(Refined — absorbs Phase 1 PoC)* | PyPSA dispatch full implementation (PoC + multi-site) | 12–18 days | 3.5–4 weeks | Feb–Mar 2027 | All |
| **v5.1+** | Future possibilities (industrial demand expansion, rooftop solar, IDX Carbon, climate physical risk — all speculative) | TBD | 2027+ | — | — |

**Total v4.x effort (Refined 2026-05-07 — v4.1 split + anchor cases + slim v4.4):** **~40–55 focused work days** *(v4.1 split adds ~2–4 days for per-phase release independence; v4.4 slim still saves 3 days)*. Completable in **12–15 calendar weeks** (mid-May to mid-August 2026). Application essay buffer **4 weeks** before Sloan/HKS deadlines. Lower risk profile than the bundled v4.1 (per-phase release de-risks the IEA rename). Tighter scope discipline (CCS retrofit overlay only, process chemistry change out and flagged). **Three anchor cases (Pupuk Kaltim Bontang, IMIP Morowali, Indocement Palimanan) thread through every release as the cross-cutting validation set.**

**The pre-MIT v4.x narrative arc:** v4.0.5 + v4.1 = methodologically sound foundation with destination-weighted CBAM and hydro hybrid; v4.2 = investor-grade project finance; v4.3 = multi-pathway analysis with regulatory dimension and CCS retrofit overlays (captive power + process stacks, all gated by storage proximity); v4.3.5 = architecture-menu primacy + two-ceiling decomposition output; v4.4 = captive deep dive + RUPTL feedback (without PyPSA risk); v4.5 = buyer pressure layer. Six independently-shipped releases with paired Substack posts. Dashboard scope is power-side decarbonization for 81 Indonesian industrial sites; process chemistry change pathways flagged with cross-reference to MPP/IEA/ETC.

---

## 4. v4.0.5: Current Dashboard Methodological Fixes (Refined — new release)

**Theme:** Close 13 methodological gaps in the currently-shipped v4.0 dashboard against the wiki framework. Lands in parallel with v4.1; can ship as a separate Zenodo DOI or roll into v4.1.

**Why this exists.** Per [[Indonesia Dashboard Methodology Review]] §Review of the current dashboard, v4.0 has 4 errors / 6 structural gaps / 3 refinements that don't need to wait for v4.1's architectural refactor. Several findings carry forward into v4.1 multi-tier outputs (geothermal proximity, regulatory variable, curtailment cost), so closing them now avoids methodological debt. Several others are 1-line corrections (solar lifecycle EF, MacKay citation) that don't need to wait.

**Spec:** `dashboard/refinement/v4_0_dashboard_fixes_spec.md`

### 4.1 Scope

**Methodological errors (Findings 1–4):**
- Reframe pure solar+12hr battery as sanity-check baseline (extend Supply Blend cascade with dispatchable RE layer)
- Geothermal proximity matching (operating fleet + RUPTL pipeline; transmission feasibility tier)
- Wind nighttime fraction tiered by region (NTT 0.42 → Kalimantan 0.60)
- Apply solar lifecycle emissions correction (1-line fix; ~5–8% upward shift in carbon breakeven)

**Structural gaps (Findings 5–10):**
- RUPTL §V.11 grid-extension feasibility check (cross-check transmission-link recommendations against published RUPTL pipeline)
- Perpres 112/2022 as regulatory variable (replaces status-string-only treatment)
- RUPTL → demand → RUPTL feedback loop (deferred to v4.4; v4.0.5 documents the static-RUPTL assumption)
- Curtailment cost in supply blend (CF haircut for grid-connected sites)
- Scope 1 abatement options surfaced (qualitative pathway flags for cement / ammonia / BFBOF)
- Hybrid binding-constraint signal (per-site sensitivity output)

**Refinements (Findings 11–13):**
- MacKay citation correction (documentation only)
- Captive matching: contractual + spatial overrides
- GEAS empirical allocation alternative (alongside proportional default)

### 4.2 Effort estimate

5–7 focused work days. ~1.5 calendar weeks.

**Code work with Claude Code (~3–4 days):**
- Geothermal proximity pipeline + tier logic
- Perpres 112 regulatory classification pipeline
- RUPTL §V.11 feasibility check pipeline
- Supply Blend cascade extension
- Curtailment loss estimation
- Scope 1 abatement constants
- Hybrid binding-constraint computation
- Captive contractual override layer
- GEAS empirical allocation function
- Wind nighttime fraction regional constant
- Solar lifecycle EF correction

**Data compilation (~1.5–2 days):**
- Geothermal operating + pipeline geocoding
- RUPTL §V.11 transmission-link compilation (~30–40 rows)
- Site Perpres 112 classification (81 rows)
- Captive coal contractual overrides (~10 priority sites)

**Documentation (~0.5 day):**
- METHODOLOGY_CONSOLIDATED.md updates for all findings
- Static-RUPTL assumption explicitly flagged
- CHANGELOG v4.0.5 entry

### 4.3 Success criteria

- All 81 sites have geothermal adjacency tier populated
- All 81 sites have Perpres 112 regulatory classification populated
- All 81 sites have RUPTL §V.11 feasibility check populated
- Solar lifecycle EF correction applied (carbon breakeven shifts uniformly 5–8%)
- All 13 findings either implemented or explicitly deferred (with deferral documented)

---

## 5. v4.1: Foundation Refactor + Methodology Refinements

**Theme:** Better foundations. **Multiple LCOE variants, multiple incumbent references, captive arrangement classification, destination-weighted CBAM (replaces single-EU-share), hydro in the hybrid optimizer (replaces "future extensibility")**. No new features per se, but enables everything that follows.

**Why first:** Every subsequent release builds on this. If v4.2 hardcodes the BPP comparison, v4.3 has to rewrite it. Refactor first.

**Refined 2026-05-07: ships in two phases (v4.1a + v4.1b).** Per the /plan-eng-review (2026-05-07) decision, v4.1 is split into two independently-shippable releases rather than one bundled release with 5 features. v4.1a covers incumbents + IEA rename + provenance (~6–7 days). v4.1b covers destination-weighted CBAM + hydro hybrid (~5–6 days). Strict sequencing: v4.1a branches and ships before v4.1b branches. Each gets its own Zenodo DOI. Full mapping in `docs/refinement/v4_1_foundation_spec.md` §1.5.

**Spec:** `dashboard/refinement/v4_1_foundation_spec.md` (single file; phase routing in §1.5, §12.0, §14)

### 5.1 Scope (Refined)

**Core refactor:**
- Multi-tier solar LCOE outputs (generation, delivered, firm partial, firm baseload)
- Multi-incumbent cost references (BPP, marginal-daytime, marginal-nighttime, industrial tariff, captive)
- Captive arrangement classification per site (4 buckets)
- Captive fuel type classification (coal, gas, oil, hybrid)
- Confidence and provenance tracking on all numeric outputs

**Methodology refinements (Refined — expanded):**
- Marginal cost / merit order estimation per region with daytime/nighttime split
- Captive coal cost defaults by region and plant age
- Captive gas cost methodology
- Storage LCOS methodology (for firm LCOE variants)
- **Destination-weighted CBAM** (per-market shares × per-market carbon prices) — replaces single-EU-share
- **Hydro in the hybrid optimizer** (3-way solar × wind × hydro) — replaces "future extensibility"
- **Geothermal NCG handling pre-emption** (when geothermal lands, treat as 42–73 g/kWh not zero)
- **OEM scope-3 commitment dataset** (pulled forward from v4.5 to enable destination-weighted CBAM)

**Data work (Refined — expanded):**
- BPP refresh to PLN Statistik 2024
- Grid emission factor update
- Captive site classification dataset compilation
- **Per-site export market share defaults + 4–6 priority site overrides** (replaces simple sectoral table)
- Industrial tariff data per customer class
- **Daytime vs nighttime marginal cost calibration**
- **Hydro operating + pipeline geocoding**
- **OEM scope-3 commitment dataset**

**Deliverables:**
- Refactored cost comparison framework
- New `fct_site_classifications.csv` published as standalone Zenodo artifact
- New `fct_site_export_market_shares.csv` published alongside
- New `dim_carbon_price_by_market.csv` published alongside
- Updated methodology documentation
- Regression tests ensuring v4.0 numbers preserved (where applicable)
- v4.1 Zenodo DOI

### 5.2 Effort estimate (Refined)

7–9 focused work days. Roughly 2–2.5 calendar weeks with normal interruptions.

**Code work (~4–5 days with Claude Code):**
- Multi-tier LCOE calculation logic
- Multi-incumbent reference framework with daytime/nighttime split
- Captive arrangement classification schema
- Provenance tracking infrastructure
- Schema migrations for new fields
- **Destination-weighted CBAM module**
- **Hydro proximity matching pipeline**
- **3-way hybrid optimizer (solar × wind × hydro)**
- Regression tests

**Data compilation (~3 days, can't be accelerated):**
- BPP refresh from PLN Statistik 2024
- Captive site classification dataset
- **Per-site export market shares with priority overrides**
- Industrial tariff data
- Captive cost defaults by region
- **OEM scope-3 commitment dataset**
- **Hydro operating + pipeline geocoding**

**Methodology and documentation (~1 day):**
- Updated methodology doc
- Confidence flagging guidance
- Zenodo publication

### 5.3 Success criteria

- All 81 sites have multi-tier LCOE and applicable incumbents computed
- Captive arrangement classification covers all sites
- Methodology document explains every comparison option
- v4.0 single-LCOE numbers reproducible from new framework (regression test)
- (Refined) Destination-weighted CBAM matches [[Powering 24-7 Industrial Loads in Indonesia]] worked example for IMIP nickel within ±$10/t
- (Refined) Hybrid 3-way optimizer matches JETP Annex 2.1 cases within ±$5/MWh

---

## 6. v4.2: Project Finance Module

**Theme:** Investment decision support. Beyond LCOE to actual project finance metrics that investment committees use.

**Spec:** `dashboard/refinement/v4_2_project_finance_spec.md`

### 6.1 Scope (Refined)

**Tier 1 (essential):**
- NPV at user-specified discount rate
- Project IRR and Equity IRR
- Profitability Index
- Simple and discounted payback
- Annual cash flow projection table (with calendar_year column)
- Multiple tariff source options (BPP, industrial, captive)
- **(Refined) Tariff escalation scenarios (flat_real default / partial_reform / full_indexation)**
- **(Refined) Site-specific COD year (with CBAM trajectory aligned to COD)**

**Tier 2 (lender metrics):**
- Debt amortization schedule
- DSCR year-by-year (min, average)
- LLCR
- DER

**Tier 3 (advanced — optional):**
- Sensitivity analysis (tornado charts; tariff scenario + COD year as variables)
- Project finance vs corporate finance toggle
- Scenario comparison across sites

**Parallel data work:**
- TKBI green finance taxonomy tagging
- Fiscal incentive panel (KEK/KI tax holidays)
- Regulatory context panel
- Regional GDP context
- (Refined) PLN tariff freeze history documentation

**Deliverables:**
- v4.2 release with project finance metrics
- Validation against Cirata Floating PV benchmark (Refined — match within ±1pp under flat_real default)
- Methodology document with "What This Is Not" section
- Substack post: "Making Solar Bankable in Indonesia"
- v4.2 Zenodo DOI
- Follow-up to Pak Faiz with implementation

### 6.2 Effort estimate (Refined)

7–11 focused work days. Roughly 2.5 calendar weeks.

### 6.3 Success criteria

- (Refined) Cirata benchmark validates within ±1pp IRR under flat_real default
- Tier 1 metrics shipped first before Tier 2 polish
- "Indicative" framing on every metric
- Pak Faiz feedback loop closed
- (Refined) COD-year-aware CBAM trajectory verifiable per site

---

## 7. v4.3: Multi-Pathway Analysis (Refined — adds regulatory dimension + CCS retrofit scenarios)

**Theme:** Different sites need different interventions. The tool shows which pathway closes the gap for which site — including CCS retrofit (captive power + process stacks) for hard-to-abate sectors where solar caps at 7–12% CBAM relief. **Scope discipline:** CCS retrofit is in (overlay on existing infrastructure); process chemistry change is out (DRI-EAF, SCM, alt fuels, inert anodes, green H₂ as chemistry substitute) — flagged with cross-reference to MPP / IEA / ETC.

### 7.1 Why this is genuinely valuable

Current single-slider flip scenario answers "if WACC drops, what happens?" That's one dimension.

Real policy analysis needs multi-dimensional thinking:
- Solar financing pathway
- Transmission financing pathway
- Carbon pricing scenario
- Mandate or regulatory pressure
- Buyer premium (corporate procurement)

Different sites are sensitive to different combinations. Java grid-connected sites flip with concessional debt alone. Captive coal nickel sites need carbon pricing AND mandate AND buyer pressure stacked. Captive gas fertilizer sites flip easily with just concessional debt.

### 7.2 Scope (Refined — adds regulatory dimension)

**Pathway toggles (Refined — adds regulatory + CCS retrofit):**
- Solar financing: commercial / concessional / grant
- Transmission financing: project / concessional / grant  
- Carbon pricing: none / domestic / destination_weighted / cbam_full / ccfd
- Buyer premium: none / corporate voluntary / EV supply chain
- Storage scenario: no storage / partial firm / baseload firm
- **(Refined) Regulatory mandate: status_quo_pr112_exempt / pr112_strict_2026 / pr112_full_phaseout**
- **(Refined) CCS retrofit overlay: none / captive_power / process_stack / both** (gated by site-specific storage proximity tiers; see §7.5)

The regulatory dimension specifically toggles whether the strategic-industry exemption from Perpres 112/2022 stays in effect. Under `pr112_strict_2026`, sites with `captive_perpres_112_exempt = True` AND `commissioning_year > 2026` get their captive cost reference flipped from "captive coal LCOE" to "alternative architecture LCOE," forcing the menu to consider hybrid options.

The CCS retrofit overlay applies to sites with captive coal/gas (captive-power CCS) and/or sites in cement / ammonia / steel BF-BOF (process CCS), gated by `ccs_proximity_tier ∈ {A, B}`. Toggling shows the indicative CBAM relief from CCS overlay, sourced from IEA / IEAGHG / IRENA / MPP literature ranges. Process chemistry change (alt fuels, SCM, DRI-EAF, inert anodes, green H₂ as chemistry substitute) is *out of dashboard scope* — flagged in the Score Drawer with cross-reference to Mission Possible Partnership / IEA. Detail in §7.5.

**Financing stack composition output (Refined — May 2026 sharpening).** Per CBAM-exposed site, v4.3 composes the four financing levers into a single "stacked economics" output. For each site:
- `lever_concessional_finance_npv_uplift` — NPV change vs commercial WACC (typically ~$30–40/tCO₂ effective reduction for CCS projects)
- `lever_cbam_destination_weighted_revenue` — destination-weighted CBAM revenue per tCO₂ avoided (M3 from §7); export-share-driven
- `lever_idx_carbon_trajectory_revenue` — domestic carbon credit revenue assuming IEA APS trajectory ($5/t today → $40/t by 2030)
- `lever_premium_pricing_revenue` — corporate scope-3 / OEM-bound product premium for low-carbon Indonesian product (Tesla EV-grade nickel, Japanese blue ammonia, etc.)
- `stacked_economics_net_cost_per_tco2` — sum of capture cost − all four levers; positive means project still requires gap-closing
- `binding_constraint_lever` — which lever is largest contributor to closing the gap; identifies the policy lever that matters most per site

The financing stack analysis is what the dashboard's policy-maker persona actually needs: *for each site, which combination of mechanisms makes the project pencil, and what's the binding constraint?* Pupuk Kaltim Bontang anchor case will show that single mechanism (CBAM alone or premium pricing alone) is sufficient. Indocement Palimanan will show all four levers must stack to close the gap.

**Java Sea CCS hub FID timing as a sensitivity input (Refined — May 2026).** A new top-level scenario input `java_sea_hub_fid_year` ∈ {2027, 2028, 2030, never} gates Tier B sites for CCS retrofit eligibility. Sites at Tier B (most Java cement, Petrokimia Gresik, Krakatau Posco) become CCS-eligible only after the hub reaches FID + 3 years construction. This is the **single largest variable** in Indonesian industrial CCS deployment and should be a first-class scenario input, not a baked-in assumption.

**Analysis outputs:**
- Per-site competitiveness under each pathway combination
- Identification of "binding constraint" per site (which pathway is the smallest gap)
- Cost of intervention required (e.g., "this site needs $X/MWh subsidy or $Y/tCO2 carbon price OR PR 112 reform")
- Cross-site rankings: which sites flip first under which pathways
- **(Refined) CCS retrofit overlay chart per CBAM-exposed site** — indicative CBAM relief by 2034 / 2040 from captive-power CCS + process CCS, gated by site's storage proximity tier (§7.5)

**UI design:**
- Multi-toggle interface for pathway combinations (now 7 dimensions)
- Heatmap visualization showing site-by-pathway competitiveness
- "Binding constraint" diagnostic per site
- (Refined) Regulatory pathway prominently displayed with policy-maker-friendly framing
- (Refined) CCS retrofit overlay panel in Score Drawer for sites in CCS Tier A/B — shows captive-power CCS variant (where captive coal/gas exists) and process CCS variant (cement kiln / ammonia SMR / BF stack); footer links to Mission Possible Partnership / IEA for process chemistry change pathways outside dashboard scope

### 7.3 Effort estimate (Refined)

12–15 focused work days. Roughly 3–3.5 calendar weeks. Most of the calculation logic exists from v4.0.5 + v4.1 + v4.2; new work is composition and UI plus the regulatory dimension plus the CCS retrofit scenarios (§7.5, +5 days incremental).

**Code work with Claude Code (~8–10 days):**
- Pathway composition logic (composable modifiers, not hardcoded scenarios)
- (Refined) Regulatory pathway dimension — new constants + integration with v4.0.5 Perpres 112 classification
- (Refined) CCS retrofit scenarios (§7.5) — CCS basin proximity tiers, captive-power CCS retrofit (coal + gas) constants and LCOE computation, process CCS retrofit (cement kiln / ammonia SMR / BF stack) sourced ranges and overlay computation, CCS-pathway-stack composition
- Multi-toggle UI interface (now 7 dimensions)
- Heatmap visualization for site-by-pathway competitiveness
- (Refined) CCS retrofit overlay panel in Score Drawer
- Binding constraint diagnostic logic
- Cross-site analysis views
- Test suite

**Methodology and documentation (~2–3 days):**
- Updated methodology doc (regulatory dimension + CCS retrofit scenarios sections)
- Pathway descriptions with sources (CCS basin tiers from ESDM atlas / Lemigas / Perpres 14/2024; CCS retrofit cost ranges from IEA / IEAGHG / IRENA / MPP)
- Substack post explaining segmentation findings (Refined — emphasising the regulatory pathway as a primary lever for policy-maker persona)
- (Refined) Substack post on CCS retrofit: "Two ceilings — what solar can't reach, and what CCS can"

**Validation (~1–2 days):**
- Spot-checking pathway combinations on representative sites
- (Refined) CCS retrofit validation set: Pupuk Kaltim Bontang ammonia SMR (Tier A — anchor case), Indocement Palimanan kiln (Tier B), Krakatau Posco BF (Tier B), IMIP nickel (Tier C — gating sanity check)
- External review (e.g., DFI contact for pathway plausibility check; Indonesian policy contact for regulatory-pathway plausibility; cement/ammonia industry contact for CCS overlay ranges)

### 7.4 Success criteria

- All 81 sites analyzable under any combination of pathway toggles
- (Refined) Regulatory pathway flips at least 30 sites between architectures (captive coal → hybrid)
- Binding constraint identifiable per site
- "Cost of decarbonization" per site computable under each pathway
- Substack post explaining segmentation findings
- (Refined) CCS basin proximity tier classified for all 68 CBAM-exposed sites
- (Refined) All Tier A/B sites with captive coal/gas have `captive_*_ccs_retrofit_*` columns populated; all Tier A/B cement/ammonia/BFBOF sites have process CCS overlay columns populated
- (Refined) Score Drawer "CCS retrofit overlay" panel renders with indicative-confidence footer linking to MPP/IEA for out-of-scope process pathways
- (Refined) Substack post on CCS retrofit ("Two ceilings") with at least Pupuk Kaltim Bontang and Indocement Palimanan as case studies

### 7.5 CCS retrofit scenarios — captive power and process stacks (Refined — rescoped)

**Scope discipline.** The dashboard models *energy-side decarbonization*: renewable architectures + CCS retrofit on existing infrastructure. **CCS retrofit is in scope wherever it sits as a capture+T&S overlay on existing equipment** — captive coal CFPP, captive gas plant, cement kiln, ammonia SMR, steel BF stack. The line that holds is **overlay vs process change**: anything that adds capture+T&S to existing infrastructure stays in scope; anything that changes the underlying process (DRI-EAF conversion, green H₂ as chemistry substitute, SCM substitution, inert anodes, electric kiln, alt-fuel kiln conversion) is out of scope and flagged with cross-reference to MPP / IEA / ETC.

**Why this exists.** v4.0 §3.5 surfaces qualitative Scope 1 abatement pathway flags but provides no quantitative comparison. For 32 cement + 5 ammonia + steel BF-BOF sites — roughly half the CBAM-exposed dataset — solar covers only 7–12% of CBAM exposure (M30 RE-addressable demand-side ceiling). The dashboard's headline question is therefore not answered for these sites; users see a static ceiling and no decision-relevant alternative pathway view. v4.3 introduces a **CCS-overlay layer** (sourced literature ranges, gated by storage proximity — not full economic modeling) that lets users compare CCS-equipped variants side-by-side at the site level.

**The Indonesia CCS opportunity** (drawn from [[Carbon Capture and Storage for Indonesian Industrial Decarbonization]]):
- Tangguh CCUS (West Papua) operational; Sukowati (East Java offshore) in development; Java Sea pilots pre-FID; Natuna basin pre-FID
- Total prospective storage ~8–10 Gt CO₂; geology not the bottleneck
- Perpres 14/2024 establishes injection rights, leakage liability, **cross-border CO₂ trading** (Singapore, Korea, Japan as importers)
- **Ammonia SMR + CCS at Pupuk Kaltim Bontang** (50 km from Tangguh) is the cheapest decarbonization opportunity in Indonesia: $10–30/tCO₂ — the SMR process stream is *already pure CO₂*

**CCS retrofit modeling scope:**

1. **CCS storage basin proximity** for each CBAM-exposed site (cement, ammonia, steel, plus all sites with captive coal/gas):
   - Tier A: <100 km from operating/permitted CCS hub (Tangguh CCUS, Sukowati area, Java Sea pilots)
   - Tier B: 100–300 km from depleted hydrocarbon basin (most Java/Sumatra sites)
   - Tier C: >300 km or no candidate basin (eastern islands; most Sulawesi/Maluku nickel)
   - Sourced from ESDM CCS atlas + Lemigas basin assessments + Perpres 14/2024 storage permitting list
   - New columns: `nearest_ccs_basin_name`, `nearest_ccs_basin_distance_km`, `ccs_proximity_tier`

2. **Captive coal + CCS retrofit** as a power-side scenario sub-variant (gated to sites with `electricity_arrangement ∈ {pure_captive, hybrid_captive_primary}` AND `captive_fuel_type` includes coal AND `ccs_proximity_tier ∈ {A, B}`):
   - Constants: `CCS_RETROFIT_COAL_CAPEX_USD_PER_KW` (~$1,500–2,000), `CCS_RETROFIT_COAL_OPEX_USD_PER_MWH` (~$30–50), `CCS_PARASITIC_LOAD_PCT_COAL` (25–35%), `CCS_CAPTURE_RATE_COAL` (0.85–0.95)
   - Computation: `lcoe_captive_coal_with_ccs_usd_per_mwh = lcoe_captive_coal × (1 + parasitic_load_pct) + ccs_overlay_cost_usd_per_mwh`
   - New columns: `captive_coal_ccs_retrofit_lcoe_usd_per_mwh`, `captive_coal_ccs_retrofit_emissions_tco2_per_mwh`, `captive_coal_ccs_retrofit_eligible` (boolean)

3. **Captive gas + CCS retrofit** as a power-side scenario sub-variant (Pupuk Kaltim is the obvious anchor; gated similarly):
   - Constants: `CCS_RETROFIT_GAS_CAPEX_USD_PER_KW` (~$1,000–1,500), `CCS_RETROFIT_GAS_OPEX_USD_PER_MWH` (~$20–35), `CCS_PARASITIC_LOAD_PCT_GAS` (15–25%), `CCS_CAPTURE_RATE_GAS` (0.85–0.95)
   - New columns: `captive_gas_ccs_retrofit_lcoe_usd_per_mwh`, `captive_gas_ccs_retrofit_emissions_tco2_per_mwh`, `captive_gas_ccs_retrofit_eligible`

4. **Process stack CCS retrofit** for cement kilns, ammonia SMR, and steel BF stacks (overlay on existing process equipment, not process change). Gated to sites where `product_type ∈ {cement, ammonia, fertilizer, steel_bfbof}` AND `ccs_proximity_tier ∈ {A, B}`:
   - **Cement kiln post-combustion CCS**: $80–120/tCO₂ avoided (sourced range from IEAGHG cost studies; Heidelberg Brevik 400 kt/y operational 2025 as proof of concept). Constants: `CCS_CEMENT_KILN_USD_PER_TCO2_RANGE`, `CCS_CEMENT_KILN_CAPTURE_RATE` (0.85–0.90), `CCS_CEMENT_KILN_PARASITIC_HEAT_GJ_PER_TCO2` (3–4 GJ/tCO₂ for amine regeneration). New column: `cement_kiln_ccs_retrofit_overlay_usd_per_tco2`.
   - **Ammonia SMR + CCS (= blue H₂)**: $10–30/tCO₂ avoided — the SMR process CO₂ stream is *already pure*; only compression + dehydration + transport + storage. Sourced from IEA, IRENA, Pupuk Indonesia disclosures. Constants: `CCS_AMMONIA_SMR_USD_PER_TCO2_RANGE`, `CCS_AMMONIA_SMR_CAPTURE_RATE` (0.90–0.95). New column: `ammonia_smr_ccs_retrofit_overlay_usd_per_tco2`.
   - **Steel BF stack post-combustion CCS**: $90–130/tCO₂ avoided. Krakatau Posco is the single applicable site (no heterogeneity problem — site-specific modelable). Constants: `CCS_STEEL_BF_USD_PER_TCO2_RANGE`, `CCS_STEEL_BF_CAPTURE_RATE` (0.50–0.70 for partial post-combustion).
   - All process CCS columns carry a paired `*_confidence` tag (`indicative_range` for v4.3; not promoted to `modeled` until v5.0).

5. **CCS-pathway-stack indicative %** per CBAM-exposed site (combining captive-power CCS + process CCS, gated by proximity):
   - `cbam_relief_solar_pct` — already computed via M30 RE-addressable
   - `cbam_relief_captive_power_ccs_pct` — gated by captive-fuel-type + proximity tier
   - `cbam_relief_process_ccs_pct` — gated by product type + proximity tier
   - `cbam_relief_combined_pct` — solar + max(captive-power CCS, applicable process CCS), with explicit non-double-counting where solar already addresses captive-power emissions

**UI: Score Drawer "CCS retrofit overlay" panel.** For CBAM-exposed sites, shows a stacked bar of CBAM relief by 2034 / 2040: solar (current) → solar + captive-power CCS → solar + process CCS → solar + both. Footer: *"Indicative ranges from IEA/IEAGHG/IRENA/MPP. Process chemistry change pathways (alt fuels, SCM substitution, DRI-EAF, inert anodes, green H₂ as chemistry substitute) are out of dashboard scope; see Mission Possible Partnership / IEA sectoral reports."*

**Wiki cross-references.** Sources [[Carbon Capture and Storage for Indonesian Industrial Decarbonization]] (the methodology grandparent), [[Carbon Capture and Storage]] concept page, [[Powering 24-7 Industrial Loads in Indonesia]] §Solar-share ceiling. Open question raised in [[Indonesia Dashboard Methodology Review]] Finding 13 — closed at indicative resolution by this section.

**What's explicitly NOT in scope (and stays out, per the overlay-vs-process-change line):**
- Process chemistry change: SCM substitution, alt-fuel kiln conversion, biomass co-firing economics, DRI-EAF retrofit, inert anodes, electric kiln (CemZero-style), green H₂ as chemistry substitute (electrolyzer + Haber-Bosch retrofit modeled at full economics), turquoise H₂ (methane pyrolysis)
- Site-specific point cost estimates (always literature ranges, not points)
- Pipeline routing economics for shared CCS hubs (basin-level proximity only, not pipeline corridor optimization)
- Carbon credit revenue from CCS (overlaps v5.4)
- Time-dependent learning curves on capture cost (use static literature ranges; refresh annually)
- Site-specific clinker quality, ammonia plant retrofittability (these need plant-engineer assessment beyond dashboard scope)

**Effort estimate:** ~5 focused days incremental on top of v4.3 baseline.

| Component | Days |
|---|---|
| CCS basin proximity data + tier classification (ESDM atlas + Lemigas + Perpres 14/2024) | 1.0 |
| Captive-power CCS retrofit constants + LCOE computation (coal + gas) | 1.5 |
| Process CCS retrofit constants + computation (cement kiln, ammonia SMR, steel BF) — sourced ranges | 1.0 |
| CCS-pathway-stack indicative % composition | 0.5 |
| Score Drawer "CCS retrofit overlay" chart UI | 1.0 |

**Validation:**
- **Pupuk Kaltim Bontang** (Tier A, 50 km from Tangguh): ammonia SMR + CCS overlay should show ~75–85% CBAM relief at $10–30/tCO₂ — the cheapest decarbonization in the dataset (sanity-check anchor).
- **Indocement Palimanan** (Java cement, Tier B): kiln CCS overlay should show 50–70% CBAM relief at $80–120/tCO₂.
- **Krakatau Posco Cilegon** (Java steel BF-BOF, Tier B): BF stack CCS overlay should show 40–60% CBAM relief at $90–130/tCO₂.
- **IMIP nickel** (Sulawesi RKEF, Tier C — too far from any storage): captive-power CCS should show `eligible = False`; pathway-stack reverts to solar-only (sanity-check showing the proximity gating works).
- **A nickel site at IIA in Maluku, captive coal, Tier C**: same — captive-power CCS should show `eligible = False` despite captive coal being present.

**Success criteria for §7.5:**
- All 68 CBAM-exposed sites have `ccs_proximity_tier` populated
- All sites with captive coal/gas in Tier A or B have `captive_*_ccs_retrofit_*` columns populated
- All cement, ammonia, fertilizer, steel BF-BOF sites in Tier A or B have process CCS overlay columns populated
- Score Drawer CCS retrofit overlay panel renders with indicative-confidence footer
- Cost ranges sourced from at least 3 reputable references per pathway (IEA, IRENA, IEAGHG, Mission Possible Partnership, ETC, CEMBUREAU)
- Locked test fixtures: Pupuk Kaltim Bontang ammonia SMR + CCS overlay relief 75–85%, Indocement Palimanan kiln CCS overlay relief 50–70%, IMIP nickel `captive_coal_ccs_retrofit_eligible = False`

### 7.6 Why this is the strongest narrative release

This is where the dashboard tells a story that no other public tool tells. Most analyses treat Indonesian decarbonization as monolithic. v4.3 shows it's actually multiple distinct problems with different solutions. That's the kind of finding that gets cited.

(Refined) The regulatory pathway specifically tells the policy-maker persona's story: *"PR 112/2022 reform unlocks more decarbonization than any single financing intervention."* That's the single most consequential framing for Indonesian energy policy.

(Refined) The CCS retrofit scenarios (§7.5) close the dashboard's headline gap: solar can only decarbonize the half of CBAM-exposed sites where electricity dominates (nickel RKEF, aluminium, steel EAF). The other half — cement, ammonia, steel BF-BOF — needs CCS overlay (captive-power and process-stack) to get past the M30 demand-side ceiling. v4.3 finally models this within a disciplined scope: CCS retrofit (overlay on existing infrastructure) is in; process chemistry change (DRI-EAF, SCM, alt fuels, inert anodes) is out and flagged with cross-reference to MPP/IEA. That's a *complete and defensible* answer to "can Indonesia industrialize and decarbonize at once" — the dashboard models what energy-side decisions can address, and is honest about what process-side decisions it doesn't replicate. **The Pupuk Kaltim Bontang ammonia SMR + CCS case ($10–30/tCO₂, Tier A storage 50 km from Tangguh) is the cheapest decarbonization opportunity in the Indonesian dataset and the strongest single case study for the release.**

---

## 8. v4.3.5: Architecture-Menu Primacy + Two-Ceiling Output (Refined — new bridging release; extended)

**Theme:** Make the wiki's six-scenario architecture menu first-class. Cross-walk action flags onto scenarios. **(Refined — extended)** Surface the two-ceiling decomposition (demand-side M30 + supply-side solar-share cap) as a unified per-site output.

**Why this exists.** Per [[Indonesia Dashboard Methodology Review]] §Adjustments needed finding 25, the wiki's six-scenario architecture menu (1 captive coal BAU through 6 solar+geothermal+battery) doesn't map cleanly to the dashboard's 14-flag action taxonomy. Both can coexist, but the cross-walk has to be explicit. v4.3's multi-pathway analysis effectively forces this question — and absorbing the architecture-menu refactor into v4.3 inflates that release's scope. A separate bridging release between v4.3 and v4.4 keeps each release focused. **(Refined — extended)** v4.3.5 also unifies the two-ceiling framing that the dashboard already imposes mechanically (M30 RE-addressable + BESS bridge + hybrid optimizer + reliability tiers) but doesn't surface as a single output. The architecture menu is the natural home: each scenario already has a computed solar share via cost optimization; v4.3.5 exposes that as a derived per-site decomposition.

### 8.1 Scope

**Core refactor:**
- Compute all six scenarios per site (each costed and carbon-adjusted using v4.1 cost framework)
- Surface architecture menu as primary scorecard output
- Cross-walk action flags onto scenarios — flags become tags on the cheapest scenario
- Document cross-walk in methodology

**(Refined — extended) Two-ceiling decomposition output.** The dashboard already imposes both ceilings via separate mechanisms (`CBAM_RE_ADDRESSABLE_FRACTION` for M30 demand; `daytime_cap` + `bess_bridge_hours` + `hybrid_solar_share` for supply). v4.3.5 surfaces them as a unified per-site decomposition:

| Column | What |
|---|---|
| `achievable_re_blend_pct` | Total RE share at recommended scenario's cost-optimal mix (= `hybrid_solar_share + hybrid_wind_share + hybrid_hydro_share + geothermal_share`) |
| `dispatchable_residual_pct` | `1 - achievable_re_blend_pct` — what must come from dispatchable fossil |
| `dispatchable_backup_type` | enum: `none / geothermal / hydro / gas / coal / mix` — what fills the residual |
| `dispatchable_residual_addressable_via_ccs` | Boolean — gated by `ccs_proximity_tier ∈ {A, B}` AND `dispatchable_backup_type ∈ {coal, gas, mix}` |
| `dispatchable_residual_addressable_pct` | Indicative fraction of dispatchable residual addressable via CCS retrofit (~85–95% of stack CO₂) |
| `dashboard_addressable_cbam_relief_pct` | Headline summary: M30 × achievable_re_blend × in_scope_share + (CCS overlay if eligible) — the dashboard-addressable CBAM relief. Pairs with a `non_addressable_pct` companion column flagged "out of dashboard scope; see MPP/IEA/ETC for process pathways" |

These are *derived columns* over existing computations, not new modeling. Provides the unified narrative that the dashboard models a clear addressable fraction and is transparent about the rest.

**Output:**
- New table `fct_site_architecture_menu.csv` (long format: site_id, scenario_id, lcoe_usd_mwh, cbam_adjusted_lcoe_2025, cbam_adjusted_lcoe_2030, recommended boolean)
- New scorecard column: `recommended_scenario` (1–6)
- (Refined) Six new derived columns above (two-ceiling decomposition)
- Existing action_flag column preserved; mapping to scenario documented in methodology

**UI design:**
- New view: "Architecture Menu per site" — six-scenario cost stack with recommended highlighted
- Site Scorecard Action tab: shows recommended scenario at top, action flag as a tag
- Map markers: shape = recommended scenario; existing color encoding (economic tier) preserved
- **(Refined) Score Drawer "Two-ceiling decomposition" panel.** Stacked bar per site showing: (1) dashboard-addressable via solar/RE blend, (2) dashboard-addressable via CCS retrofit overlay, (3) non-addressable (out of dashboard scope; pointer to MPP/IEA/ETC for process chemistry change pathways). Footer: *"This dashboard models energy-side decarbonization. Process chemistry change pathways (alt fuels, SCM, DRI-EAF, inert anodes, green H₂ as chemistry substitute) are out of scope; see Mission Possible Partnership / IEA sectoral reports."*

### 8.2 Effort estimate

4.5–5.5 focused work days *(was 4–5; +0.5 day for two-ceiling output)*. ~1.5 calendar weeks.

**Code work (~3.5 days):**
- Compute all six scenarios per site (re-uses v4.1 cost framework)
- Build `fct_site_architecture_menu.csv` pipeline
- Update scorecard + action-flag flow to expose `recommended_scenario` field
- New "Architecture Menu" UI view + Site Scorecard updates
- (Refined) Six derived two-ceiling columns + Score Drawer panel

**Documentation (~1 day):**
- Methodology cross-walk: action-flag → scenario mapping table
- (Refined) Methodology section: "Two-ceiling decomposition" tying §3.x M30 + §6.x BESS bridge + §6A hybrid + §10.x daytime cap into a single principle
- Substack post: "Six scenarios, not one optimum" (Refined — now also covers the two-ceiling framing)

**Validation (~0.5–1 day):**
- Spot-check 5 sites: recommended scenario matches manual review against the wiki's per-site recipe
- (Refined) Two-ceiling decomposition validation: cement Indocement (~12% addressable), nickel IMIP (~85% addressable), ammonia Pupuk Kaltim (~85% with CCS overlay)

### 8.3 Success criteria

- All 81 sites have recommended_scenario populated (1–6)
- Architecture Menu view displays six-scenario cost stack
- Action flag → scenario cross-walk documented in methodology
- Existing dashboard users see continuity (action flags still surfaced)
- New users see the architecture menu as the primary frame
- (Refined) All 81 sites have the six two-ceiling decomposition columns populated
- (Refined) Score Drawer "Two-ceiling decomposition" panel renders for all sites with the addressable / non-addressable footer
- (Refined) Methodology principle write-up tying the existing mechanisms together as a unified two-ceiling decomposition

### 8.4 Why this is small but high-value

The refactor itself is small (composition over v4.1's cost framework). The methodological clarification is large: it aligns the dashboard with the wiki's accumulated framework, makes scenarios 5 and 6 visible as primary alternatives (rather than hidden inside the hybrid optimizer), and gives policy-maker users a frame that maps cleanly to Indonesian energy-sector discourse.

---

## 9. v4.4: RUPTL Feedback + Captive Cost Validation (Refined — slimmed May 2026; PyPSA PoC deferred to v5.0)

**Theme:** Validate v4.0.5 + v4.1 captive cost defaults against JETP CPS and other public sources. Run the RUPTL → demand → RUPTL feedback loop. **(May 2026 refinement: substantially slimmed.** Most chemistry-dominant sectors (cement, Java ammonia) are grid-connected, not captive — captive deep dive doesn't materially change their decarbonization story. For nickel, captive coal IS the story but v4.0.5/v4.1 captive cost modeling already covers it adequately. PyPSA PoC also deferred to v5.0 — schedule risk on learning curve outweighs application narrative benefit.)

### 9.1 Why a separate (slim) release rather than extending v4.1

v4.0.5 + v4.1 establish the framework with site-specific captive cost overrides for all three anchor cases (IMIP Morowali, Krakatau Posco, Pupuk Kaltim Bontang). v4.4 adds:

- **RUPTL feedback loop**: aggregate dashboard-projected captive-coal demand per region; compute "PLN demand case minus captive bypass"; recompute RUPTL geothermal/hydro additions accordingly; re-run scenario 6 availability per site
- **Validation of v4.1 captive cost defaults** against JETP CPS Figure 5.2.2-1 (LCOE for supercritical coal at different coal prices and carbon prices)
- **Add 2–3 more captive cost overrides** for non-anchor sites with public disclosure (e.g., Adaro Kaltara aluminium, Vale Sorowako, Trimegah Halmahera)

### 9.2 Scope (Refined — slimmed May 2026)

**In scope:**
- (Refined) RUPTL → demand → RUPTL feedback loop modeling (~0.75 day)
- Validation of v4.1 §4.4 captive coal defaults + §5.4 captive gas defaults against JETP CPS Figure 5.2.2-1 numbers (~0.5 day)
- Public disclosure overrides for 2–3 additional captive sites beyond v4.1 priority list (~1 day)
- Substack post: "Indonesia's hidden electricity demand" (with the captive-coal-eats-its-own-tail framing from the RUPTL feedback model) (~0.5 day)

**Dropped (May 2026 — not over-investing in captive deep dive):**
- ~~Stranded asset risk analysis~~ — interesting but not on the critical path for CBAM-driven decarbonization economics (the dashboard's primary use case)
- ~~Captive plant retirement scenarios~~ — would require detailed financial modeling beyond v4.2's project-finance framework
- ~~Captive vs grid arbitrage analysis~~ — niche; most captive sites can't physically connect to PLN grid without major transmission build
- ~~Coal supply chain vertical integration mapping~~ — captured in `confidence='medium'` defaults; site-specific deep mining unnecessary for site-level decisions
- ~~Expanding captive cost overrides from 4–6 to 10–15 sites~~ — diminishing returns; v4.1 anchor case coverage is sufficient
- ~~PyPSA single-site PoC~~ — deferred to v5.0 (separate decision)

### 9.3 Effort estimate (Refined — slimmed May 2026)

**2–3 focused work days** *(was 5–6 before slim; was 8–10 before PyPSA defer)*. Realistic 1 calendar week.

**Code work with Claude Code (~1.5 days):**
- RUPTL feedback loop modeling (~0.75 day)
- Captive cost validation logic (~0.5 day)
- Score Drawer additions for RUPTL feedback findings (~0.25 day)

**Data compilation (~0.5–1 day):**
- Validate v4.1 captive defaults against JETP CPS Figure 5.2.2-1
- Add 2–3 captive cost overrides

**Documentation (~0.25 day):**
- Substack post on captive economics + RUPTL feedback finding

**Deliverables:**
- v4.4 release with RUPTL feedback loop + captive cost validation
- Substack post on "Indonesia's hidden electricity demand"
- v4.4 Zenodo DOI

**Documentation (~0.5–1 day):**
- Methodology updates (including RUPTL feedback documentation)
- Substack post on captive economics
- Zenodo publication

### 9.4 Success criteria (Refined — slimmed May 2026)

- (Refined) v4.1 captive coal defaults validated against JETP CPS Figure 5.2.2-1
- (Refined) Site-specific captive cost overrides extended to 6–9 sites total (3 anchor cases from v4.1 + 2–3 additional)
- (Refined) RUPTL feedback loop produces a "captive-coal-eats-its-own-tail" finding (e.g., dashboard captive-coal projections reduce RUPTL geothermal availability for X% of sites)
- Captive coal economics defensible to industry experts (Pak Faiz, IESR, IEA reviewers)
- Substack post on captive economics published
- ~~Stranded asset risk computable per captive site~~ — dropped in slim
- ~~Site-specific overrides for 10+ sites~~ — reduced to 6–9 anchor + adjacent in slim

---

## 10. v4.5: Buyer Pressure & Supply Chain Layer (Refined — analytical layer only; data lands in v4.1)

**Theme:** Non-price decarbonization drivers. Beyond carbon pricing to commercial pressure.

**Refinement note:** Per [[Indonesia Dashboard Methodology Review]] §Adjustments needed finding 23, the OEM scope-3 commitment dataset that v4.5 originally produced is load-bearing for v4.1's destination-weighted CBAM. The data work splits forward to v4.1 (§11.8 of the refined v4.1 spec). v4.5 retains the broader analytical layer (per-site buyer pressure visualization, commercial pathway analysis, "renewable nickel" pricing scenarios) but ships smaller and faster as a result.

### 10.1 Why this matters

For captive coal nickel sites, pure economics never flip. They need either:
- Aggressive carbon pricing (politically hard)
- Regulatory mandate (slow to implement)
- Commercial pressure from buyers (already happening)

The third pathway is real and growing. Tesla, BYD, LG Energy Solution, CATL all have stated supply chain decarbonization commitments. They will increasingly pay premium for renewable-powered nickel and avoid coal-powered nickel.

This commercial pressure is invisible in pure cost comparisons but very real for site-level investment decisions.

### 10.2 Scope (Refined — narrowed)

**Buyer commitment data:** *Already shipped in v4.1 refined* (§11.8). The commitment database, per-OEM disclosed targets, and implied scope-3 prices live in `data/raw/oem_scope3_commitments.csv` and `dim_carbon_price_by_market.csv` — both feeding v4.1's destination-weighted CBAM.

**v4.5 analytical layer (new in v4.5):**
- Buyer pressure premium per site — translation of commitments into per-tonne premium for low-carbon material delivered to specific OEMs
- Site-buyer mapping (which sites supply which buyers — annual report mining)
- "Renewable nickel" pricing scenarios — what does a $20/t Ni green premium look like at each Indonesian smelter site?
- Commercial pathway analysis (if buyers pay $X premium, captive coal sites become uncompetitive at year Y)
- Per-site visualization of buyer pressure as a competitive lever, alongside carbon pricing

**Deliverables:**
- v4.5 release with supply chain pressure analysis
- Substack post on commercial pathways
- v4.5 Zenodo DOI

### 10.3 Effort estimate (Refined — smaller)

3–5 focused work days (vs baseline 5–7). 1.5 calendar weeks. Most data work already shipped in v4.1 refined; v4.5 does the per-site mapping and analytical layer.

**Code work with Claude Code (~2 days):**
- Buyer pressure premium calculation (uses v4.1's OEM commitment data)
- Site-buyer mapping data structure
- Commercial pathway analysis logic
- UI components for buyer pressure visualization

**Data compilation (~1–2 days):**
- Site-buyer mapping from annual reports for major Indonesian nickel sites (~10 sites)
- (v4.1 refined already covers the OEM commitment database)

**Documentation (~0.5 day):**
- Methodology with caveats about premium estimation
- Substack post on commercial pathways
- Zenodo publication

### 10.4 Risk

This release depends on buyer commitments being publicly disclosed and quantifiable. v4.1 refined's data compilation already de-risks this — if commitments turn out to be too thin to be quantitative, the v4.5 analytical layer narrows to a qualitative commentary using the data already collected. v4.5 still ships; it just has less quantitative detail.

### 10.5 Success criteria (Refined)

- (v4.1 refined deliverable) Buyer commitment database covers at least 10 major battery/EV manufacturers
- (v4.5) Site-buyer mapping for at least major Indonesian nickel sites
- (v4.5) Quantitative price premium estimates with confidence flagging
- (v4.5) Commercial pathway analysis identifies the carbon-price-equivalent of buyer pressure per site

---

## 11. v5.0: PyPSA Dispatch Integration

**Theme:** Hourly dispatch optimization. Real grid simulation, not just annual averages.

### 11.1 Why this is v5.0 not v4.x

This is a major architectural shift. PyPSA modeling requires:
- Hourly demand profiles per site
- Hourly solar generation profiles per location
- Storage dispatch optimization
- Transmission constraint modeling
- Multi-site coordination

This is qualitatively different from the annual-average methodology of v4.x. It's not an extension; it's a parallel analytical capability.

(May 2026 refinement: Phase 1 PoC reverted from v4.4 back to v5.0. v5.0 is the full PyPSA implementation, both PoC and multi-site. Schedule risk on PyPSA learning curve in v4.4 was the binding concern; pre-MIT v4.x stays focused on the architecture-menu / CCS-overlay narrative.)

### 11.2 Scope (Refined — full PyPSA, post-applications)

**Phase 1 (single-site PoC):** one representative industrial site (likely IMIP Morowali or Pupuk Kaltim Bontang) with synthetic hourly demand + 1 year of hourly solar/wind generation + battery dispatch optimization. Compare PyPSA-derived LCOE to v4.x annual-average LCOE. Resolves v4.x kludges around daytime/nighttime marginal, curtailment cost, and wind nighttime fraction for the chosen site.

**Phase 2 (multi-site):**
- Multiple sites within a grid system
- Portfolio optimization across sites
- Transmission constraint modeling
- Regional renewable share scenarios

**Phase 3 (national):**
- Indonesia-wide grid simulation
- Decarbonization pathway optimization
- Cost-optimal renewable expansion

### 11.3 Effort estimate (Refined — absorbs Phase 1 PoC)

**Phase 1 PoC: 2–3 days** (now within v5.0 scope, post-applications)
**Phase 2: 10–15 days** (multi-site portfolio optimization; lands in Spring 2027)
**Phase 3: 8–12 weeks** (national grid simulation; likely needs academic partnership)

PyPSA is the one feature where Claude Code provides less acceleration. The PyPSA library has its own learning curve. Synthetic demand profile generation requires domain judgment. Validation requires hourly data that's not always public.

### 11.4 Success criteria

For Phase 1 PoC (v5.0 opening):
- Single site dispatch model running
- Comparison to v4.x annual methodology shows expected differences
- Resolves at least one v4.x kludge (daytime/nighttime marginal, curtailment cost, or wind nighttime fraction) for the chosen site

For full v5.0 multi-site:
- Multi-site Phase 2 production-ready for 5–10 representative sites
- Methodology documented for academic-level review
- Substack post or academic paper on findings

### 11.5 Why this is post-applications

PyPSA implementation is a multi-month effort with uncertain narrative payoff for application essays vs the schedule risk it adds to v4.x. The pre-MIT v4.x narrative is strong without PyPSA: methodologically sound foundation (v4.0.5 + v4.1), investor-grade finance (v4.2), multi-pathway analysis with CCS retrofit (v4.3), architecture-menu primacy with two-ceiling output (v4.3.5), captive deep dive (v4.4), buyer-pressure layer (v4.5). PyPSA in v5.0 is the natural deepening release post-applications during the MIT era.

---

## 12. v5.1+: Future Possibilities

These are features identified but not yet committed. Some may merge into v4.x. Others wait for post-MIT bandwidth.

**v5.1: Industrial demand universe expansion** — 5,159 facility dataset, full Tier 1–3 demand estimation. Currently scoped as separate spec; may integrate as v5.1.

**v5.2: Rooftop solar potential** — Google Open Buildings integration, rooftop vs ground-mount split. Currently scoped as separate spec; may integrate.

**v5.3: ~~Sectoral decarbonization pathways~~ — REMOVED (May 2026 refinement).** Process chemistry change pathways (alt fuels, SCM substitution, DRI-EAF, inert anodes, electric kiln, green H₂ as chemistry substitute) are *out of dashboard scope* per the May 2026 scope discipline. The dashboard models energy-side decarbonization (renewables + CCS retrofit on existing infrastructure, both captive power and process stacks); chemistry change is flagged in the Score Drawer with cross-reference to Mission Possible Partnership / IEA / ETC sectoral reports. Process-side modeling stays in those tools, not this one. *(Captive-power CCS deep modeling beyond v4.3 §7.5 indicative ranges — site-specific T&S cost optimization, pipeline routing — could be a v5.x candidate if user demand emerges.)*

**v5.4: Indonesian carbon market integration** — when IDXCarbon matures, integrate carbon credit pricing into analysis.

**v5.5: Climate physical risk overlay** — sea level rise, flood risk, heat stress affecting industrial sites.

**v5.6: Workforce transition analysis** — job creation and just transition analysis (Pak Faiz suggestion, deferred).

**v5.7: Real-time data integration** — live grid data, live commodity prices, live carbon prices.

**v5.8: International benchmarking** — compare Indonesian sites to similar facilities globally.

**v6.0: Replication framework** — packaged methodology for other Southeast Asian countries (Vietnam, Philippines, Thailand industrial decarbonization).

These are explicitly speculative. Some will move into v4.x as priorities clarify. Some will stay in the backlog.

---

## 13. Cross-Cutting: Data Sources & Refresh Cadence

### 13.1 Primary public data sources

| Source | Update frequency | Used for |
|---|---|---|
| PLN Statistik | Annual | BPP, regional supply, peak load |
| BPS Statistik Industri | Annual | Industrial demand, GDP context |
| ESDM regulations | As issued | Tariff caps, fiscal incentives |
| BKPM | As issued | KEK incentives, investment policy |
| Global Energy Monitor | Quarterly | Coal plant tracker, captive identification |
| GADM/Natural Earth | Stable | Boundaries, geography |
| Global Solar Atlas | Stable | PVOUT, capacity factor |
| Global Wind Atlas | Stable | Wind speed; (Refined) hourly profiles for nighttime fraction calibration |
| OpenStreetMap | Continuous | Roads, ports, building footprints |
| Google Open Buildings | Periodic | Building polygons (May 2023 vintage) |
| World Bank IPCC | Periodic | Carbon pricing benchmarks |
| IRENA | Annual | Technology costs |
| IEA | Annual | Energy outlook, sectoral analysis |
| IESR | Annual + occasional | Indonesia-specific energy analysis |
| **(Refined) Tesla, BMW, VW, Hyundai, LG, CATL ESG/sustainability reports** | **Annual** | **OEM scope-3 commitments for destination-weighted CBAM** |
| **(Refined) BPS Comtrade per HS code** | **Quarterly** | **Per-site export market shares** |
| **(Refined) RUPTL §V.11 transmission link database** | **Annual (RUPTL refresh)** | **Grid-extension feasibility check** |
| **(Refined) ESDM geothermal operating + pipeline lists** | **As updated** | **Geothermal proximity matching** |
| **(Refined) ESDM CCS atlas + Lemigas basin assessments + Perpres 14/2024 storage permit list** | **As updated** | **CCS basin proximity tiers (v4.3 §7.5)** |
| **(Refined) RSPO / IPOP palm-oil mill registry + BPS rice-mill data** | **Annual** | **Biomass feedstock proximity for cement (v4.3 §7.5)** |
| **(Refined) IRENA electrolyzer cost trajectory + ESDM industrial gas tariff schedule** | **Annual / as updated** | **Blue vs green H₂ LCOH flip-point modeling (v4.3 §7.5)** |
| **(Refined) IEA / IRENA / Mission Possible Partnership / ETC / CEMBUREAU sectoral decarbonization reports** | **As published** | **Indicative pathway-stack ranges (v4.3 §7.5)** |

### 13.2 Refresh schedule

- v4.0.5: Methodological-fix data refresh (geothermal proximity, RUPTL §V.11, Perpres 112 classification, captive contractual overrides)
- v4.1: Full data refresh, baseline as of May 2026 (including OEM commitments, per-site export shares, hydro proximity)
- v4.3: Hard-to-abate pathway data load (CCS basins, biomass feedstock clusters, electrolyzer cost trajectory, industrial gas tariff)
- v4.2 / v4.3.5 / v4.4 / v4.5: Targeted updates as new data becomes available (e.g., BPS new vintage, RUPTL annual refresh)
- v5.0: Full refresh, hourly data integration
- Annual: PLN Statistik, BPS, IRENA refresh

### 13.3 Data provenance discipline

Every numeric output traces back to:
- Source dataset name and version
- Date data was downloaded
- Date data reflects (may differ from download date)
- Citation in methodology document
- License/attribution requirements

Build this into the data pipeline from v4.0.5/v4.1, not retrofitted.

---

## 14. Cross-Cutting: Persona Coverage Evolution (Refined)

| Persona | v4.0 | v4.0.5 | v4.1 (May) | v4.2 (Jun) | v4.3 (Jul) | v4.3.5 | v4.4 (Aug) | v4.5 (Aug) | v5.0 (Apr 27) |
|---|---|---|---|---|---|---|---|---|---|
| P1: Energy Economist | 85% | 88% | 90% | 92% | 95% | 96% | 96% | 96% | 97% |
| P2: Project Developer | 75% | 78% | 81% | 90% | 93% | 94% | 94% | 95% | 97% |
| P3: Policy Maker | 80% | 82% | 84% | 86% | 97% | 97% | 97% | 97% | 98% |
| P4: KEK Authority | 75% | 78% | 81% | 87% | 92% | 93% | 93% | 93% | 94% |
| P5: Industrial Investor | 80% | 82% | 85% | 93% | 96% | 96% | 96% | 97% | 97% |
| P6: Roadmap Planner | 80% | 84% | 87% | 89% | 97% | 97% | 97% | 97% | 99% |

(Refined — v4.0.5 lifts coverage modestly across all personas; v4.3 jumps Policy Maker (regulatory dimension), Industrial Investor (CCS retrofit visibility for cement/ammonia/BFBOF investments via overlay), and Roadmap Planner (architecture menu + CCS overlay); v4.3.5 small uniform lift from architecture-menu primacy + two-ceiling decomposition; v4.4 captive deep dive (PyPSA PoC reverted to v5.0). The CCS retrofit overlays in v4.3 §7.5 are the single highest-leverage persona-coverage gain in the v4.x cycle, since cement/ammonia/BFBOF sites previously had no decision-relevant pathway view at all. Pupuk Kaltim Bontang ammonia SMR + CCS at Tier A is the anchor case — the cheapest decarbonization opportunity in the dataset.)

### 14.1 Sloan/HKS application narrative impact

For applications, what matters most is shipped capability by August 2026. With the compressed timeline (and the new v4.0.5 + v4.3.5 inserted), shipping v4.0 → v4.5 by mid-August is tight but doable. The application story benefits from:
- v4.0 already shipped (proof of execution)
- (Refined) v4.0.5 methodological consistency (proof of self-correction discipline)
- v4.1 methodology depth (proof of analytical sophistication)
- v4.2 investment decision support (proof of product thinking)
- v4.3 multi-pathway analysis with regulatory dimension + CCS retrofit overlays (captive power + process stacks) — proof of strategic insight + complete coverage of CBAM-exposed sectors via in-scope CCS modeling, with explicit boundary marker pointing at MPP/IEA/ETC for out-of-scope process chemistry change pathways. **Defensible scope discipline rather than over-extended breadth.**
- (Refined) v4.3.5 architecture-menu primacy (proof of methodological maturity)
- v4.4 captive deep dive + PyPSA PoC (proof of methodological rigor + technical depth)
- v4.5 supply chain layer (proof of systems thinking)

Shipping all six v4.x releases by mid-August 2026 is realistic but tighter than the baseline plan. Materially stronger application narrative than the original 12-month timeline allowed.

---

## 15. Cross-Cutting: Substack Content Calendar (Refined)

Each major release pairs with a Substack post. Posts are the application-narrative artifact and the institutional-credibility artifact.

| # | Post | Pairs with | Theme | Target |
|---|---|---|---|---|
| 1 | "Why I built this" (already shipped) | v4.0 | Origin story | Done |
| 2 | "Can Indonesia industrialize and decarbonize at once?" | v4.0 ship | Core thesis (in progress) | Mid-May 2026 |
| 3 | (Refined) "What was wrong with v4.0" | v4.0.5 | Methodological consistency | Late May 2026 |
| 4 | "Making solar bankable in Indonesia" | v4.2 | Project finance metrics + Cirata-validation under realistic tariff | Mid-June 2026 |
| 5 | "Why captive coal makes nickel decarbonization different" | v4.3 | Segmentation finding | Early July 2026 |
| 6 | (Refined) "The regulatory pathway no one models" | v4.3 | PR 112 reform as the missing pathway dimension | Mid-July 2026 |
| 6b | (Refined) "Two ceilings — what solar can't reach, and what CCS can" | v4.3 §7.5 + v4.3.5 | Two-ceiling framing (M30 demand + supply-side cap) + CCS retrofit overlays for cement / ammonia / steel BF-BOF; Pupuk Kaltim Bontang as anchor case | Mid-July 2026 |
| 7 | (Refined) "Six scenarios, not one optimum" | v4.3.5 | Architecture-menu reframe | Late July 2026 |
| 8 | "Indonesia's hidden electricity demand" + "Captive coal eats its own tail" | v4.4 | Captive economics + RUPTL feedback | Early August 2026 |
| 9 | "Beyond carbon pricing: supply chain pressure" | v4.5 | Buyer commitments | Late August / early September 2026 |
| 10 | "What hourly modeling reveals" (post-applications) | v5.0 | PyPSA findings | Spring 2027 |

Cadence: roughly one post every 2–3 weeks during May–August, paired with each release. Pair with LinkedIn distribution.

This compressed cadence (10 posts in ~15 weeks) is aggressive but supports the application narrative. Each post takes ~1 day if the underlying analysis is already done by the release. Posts 6 and 6b can be paired (both v4.3) — same release, different angles: regulatory pathway for policy persona, hard-to-abate pathway for investor / industry-strategy persona.

---

## 16. Decision Points & Branching Logic

### 16.1 v4.0.5 ↔ v4.1 sequencing (Refined — new decision)

**Decision:** Ship v4.0.5 separately, or roll into v4.1?

**Recommended:** Ship separately as v4.0.5. Reasons:
- Two Zenodo DOIs better for citation
- v4.0.5 is methodological-consistency story, v4.1 is foundation-refactor story — different narratives
- v4.0.5 lands faster (1.5 weeks); v4.1 takes 2.5
- Substack post pairing works better separately

**Alternative:** Roll into v4.1 as v4.1.0, accepting longer release cycle but single DOI. Acceptable if calendar pressure forces compression.

### 16.2 v4.1 → v4.2 transition

**Decision:** Ship v4.1 first (foundation refactor), then v4.2 (project finance) on top, vs. doing both as one big release.

**Recommended:** Sequential. v4.1 as foundation, v4.2 as feature. Reasons:
- v4.1 alone is shippable and demonstrates methodological rigor
- v4.2 benefits from a stable foundation to build on
- Two Zenodo DOIs > one DOI for citation purposes
- Faster public progress signal

### 16.3 v4.2 Tier 3 inclusion

**Decision:** Ship v4.2 with Tier 1+2 only, or include Tier 3 (sensitivity, scenarios)?

**Branching:**
- If timeline pressure (applications nearing): ship Tier 1+2 only, defer Tier 3 to v4.2.5 patch
- If time available: include Tier 3 in v4.2

**Recommendation:** Plan for Tier 1+2 in v4.2. Tier 3 features that are easy can slot in (sensitivity charts), harder features (scenario comparison) defer to v4.3.

### 16.4 v4.3 vs v4.4 ordering

**Decision:** Multi-pathway analysis (v4.3) before captive deep dive (v4.4), or vice versa?

**Recommended:** v4.3 first. Reasons:
- Multi-pathway has higher narrative payoff for applications
- Captive deep dive depends on v4.3's pathway framework
- v4.3 is achievable before applications; v4.4 likely after

### 16.5 v4.3.5 inclusion (Refined — new decision)

**Decision:** Ship v4.3.5 architecture-menu refactor separately, fold into v4.3, or defer to v5.x?

**Recommended:** Ship separately as v4.3.5. Reasons:
- Folding into v4.3 inflates that release's scope (already 8–11 days)
- The architecture-menu primacy is a methodological reframe worth its own DOI + Substack post
- Small enough (4–5 days) that calendar pressure is manageable

**Alternative:** Defer to v4.4 (architecture menu becomes one of v4.4's UI views rather than a refactor). Acceptable if v4.3 timeline slips.

### 16.6 v5.0 PyPSA timing (Refined)

**Decision:** PyPSA Phase 1 PoC during applications (Sept–Dec 2026) or post-applications (Jan–Feb 2027)?

**Recommended (Refined):** Pull Phase 1 PoC into v4.4 (June–July 2026). Full Phase 2 multi-site implementation post-applications. Don't let PyPSA scope eat into application preparation time, but the PoC is small enough (~2 days) to fit inside v4.4 and resolves several v4.x methodological kludges.

### 16.7 Knowledge base review impact (Refined — already integrated)

The renewable energy knowledge base review has been done — see [[Indonesia Dashboard Methodology Review]]. Findings integrated into:
- v4.0.5 spec (current dashboard fixes)
- v4.1 refined spec (destination-weighted CBAM, hydro hybrid, daytime/nighttime marginal)
- v4.2 refined spec (COD-year CBAM, flat-tariff default)
- v4.3 (regulatory pathway dimension + hard-to-abate pathway proximity §7.5)
- v4.3.5 (architecture-menu primacy)
- v4.4 (RUPTL feedback loop, PyPSA PoC pulled forward)
- v4.5 (data work split forward to v4.1)

The roadmap should be revisited again after Pak Faiz's v4.2 feedback and any external review of v4.3+ findings.

---

## 17. Open Questions for Knowledge Base Review (Refined)

These are the questions still open after the review. Some have been answered by [[Indonesia Dashboard Methodology Review]]; others remain.

### 17.1 Methodology questions (Refined — most answered)

**Q1 (RESOLVED): Marginal cost adjustment factors per region.** Per [[Indonesia Dashboard Methodology Review]] §v4.1 gaps finding 16, the regional factor must split into daytime and nighttime. v4.1 refined integrates the split.

**Q2: Captive coal cost defaults.** Are the $35–55/MWh range and regional variations supported by Indonesian data? What public disclosures exist for major captive operators?

**Q3: Captive gas cost methodology.** Indonesian captive gas plants (Pupuk Kaltim, Gresik) — what's the typical LCOE range? How does it vary with gas pricing?

**Q4: Storage LCOS for Indonesian utility-scale.** Is the $300–400/kWh CAPEX assumption current? What round-trip efficiency and degradation should be assumed for tropical Indonesian conditions?

**Q5 (PARTIALLY RESOLVED): EU export share by sector.** The merged synthesis [[Powering 24-7 Industrial Loads in Indonesia]] gives destination-weighted defaults for nickel; v4.1 refined extends to all sectors via `EXPORT_MARKET_SHARES_BY_SUBSECTOR`. Site-specific overrides for non-priority sites still open (v4.4 work).

**Q6: Carbon emissions intensity.** Indonesian subcritical coal is assumed at 0.95 tCO2/MWh. Is this the right number? How does it vary by coal type and plant efficiency?

**Q7 (PARTIALLY RESOLVED): Buyer pressure quantification.** OEM commitments lifted into v4.1 refined. Per-site mapping (which sites supply which OEMs) still open for v4.4/v4.5.

### 17.2 Architectural questions (Refined — mostly answered)

**Q8 (RESOLVED): Pathway dimensions.** v4.3 refined adds regulatory mandate as the 6th dimension and hard-to-abate pathway view (§7.5) as the 7th. The hard-to-abate dimension is gated rather than uniform — only applies to sites where M30 RE-addressable < 0.50.

**Q9: Site classification taxonomy.** Are the four electricity arrangement buckets (grid_only, grid_primary_with_captive, hybrid_captive_primary, pure_captive) sufficient? Or should there be more granular distinctions?

**Q10 (RESOLVED): Carbon pricing scenarios.** Destination-weighted approach replaces enumerated CBAM scenarios. v4.1 refined integrates.

**Q21 (NEW): Architecture-menu vs action-flag cross-walk.** v4.3.5 is the proposed home for this. Is the menu the right taxonomy, or should there be a 7th scenario (e.g., 100% green hydrogen for hard-to-abate)? *(Partial answer from v4.3 §7.5: hard-to-abate pathways are surfaced as a separate proximity-gated dimension rather than as a 7th menu scenario, on the grounds that the same site can have multiple stacked pathways. v4.3.5 should decide whether the architecture menu absorbs this or remains orthogonal.)*

### 17.3 Data questions

**Q11: PLN dispatch data.** Is there any way to get hourly dispatch data from PLN for marginal cost validation? Academic partnerships?

**Q12: Captive plant operational data.** What data exists publicly on captive plant heat rates, fuel sourcing, age?

**Q13: CBAM regulatory data.** What's the latest on CBAM scope expansion timeline? Sectors expected to be added?

**Q14: TKBI taxonomy.** Is there a comprehensive KBLI-to-TKBI mapping available? Or does this need manual compilation?

**Q15: Industrial tariff data.** What's the most current PLN industrial tariff schedule per customer class and region?

### 17.4 Strategic questions (Refined)

**Q16: v4.3 multi-pathway feasibility.** Is the 7-dimension pathway analysis (now including regulatory + hard-to-abate proximity) too complex? Should it be simplified for v4.3 and elaborated in v4.4? *(Mitigation: the hard-to-abate dimension only applies to ~37 sites with M30 RE-addressable < 0.50, and surfaces in a dedicated Score Drawer panel rather than the multi-toggle UI — so the toggle UI complexity stays bounded.)*

**Q17: Buyer pressure data feasibility.** Is there enough public data on buyer commitments to quantify pressure, or does v4.5 become qualitative? *(v4.1 refined data work answers this in part — what gets compiled determines v4.5 depth.)*

**Q18: PyPSA partnership.** Should v5.0 (multi-site) be a solo effort or partnership with academic institution (ITB, UI, NUS, MIT)?

**Q19: Application timing.** Is the August 2026 cutoff for major feature work realistic given Tokyo move and Systemiq day job, *with the refined scope including v4.0.5 and v4.3.5*?

**Q20: Open source vs commercial pivot.** When does the dual model commercial offering activate? Is post-2026 timing aligned with MIT era?

---

## Appendix: How to Use This Roadmap

**For implementation:** Each release section has a corresponding feature spec in `dashboard/refinement/`:
- v4.0.5 → `dashboard/refinement/v4_0_dashboard_fixes_spec.md`
- v4.1 → `dashboard/refinement/v4_1_foundation_spec.md`
- v4.2 → `dashboard/refinement/v4_2_project_finance_spec.md`
- v4.3 / v4.3.5 / v4.4 / v4.5 / v5.0 — specs to be elaborated as each release approaches

**For prioritization:** Section 3 overview table is the quick-reference. Section 16 covers branching decisions.

**For applications:** Sections 14 and 15 cover persona coverage and content calendar. v4.0–v4.4 are the application-relevant arc.

**For knowledge base review:** Section 17 lists the open questions. Bring this list when reviewing.

**For Claude Code:** Skip most sections. Section 2 (architectural foundations) and individual release sections (4–11) are implementation-relevant.

---

*Cross-references: [[Indonesia Dashboard Methodology Review]] §Adjustments needed (the 5 roadmap adjustments integrated). Refined version supersedes baseline `dashboard_roadmap_v4_v5.md`. New releases inserted: v4.0.5 (current-dashboard fixes), v4.3.5 (architecture-menu primacy). New scope additions: v4.3 (regulatory pathway dimension), v4.4 (RUPTL feedback loop + PyPSA single-site PoC), v4.1 (OEM scope-3 data pulled forward from v4.5).*
