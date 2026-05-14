# Methodology Refinement — CBAM Scope 2 Sectoral Coverage

**Filed**: 2026-05-14
**Trigger**: Cross-doc fact-check of CBAM Scope 2 mechanics against EU Commission Implementing Regulation (EU) 2025/2547 (10 December 2025). Surfaced two material inconsistencies between EU rules and wiki+dashboard treatment.
**Anchor**: Wiki fact-check at `syntheses/CBAM Scope 2 and REC Credibility-fact-check.md` (Energy/Renewables vault) — see for full source triangulation.

## TL;DR

The dashboard's M3 destination-weighted CBAM formula calculates `CBAM = embedded_emissions × destination-weighted_carbon_price` with `embedded_emissions` treated implicitly as Scope 1 + Scope 2 for all CBAM-covered sectors. Per EU Implementing Regulation 2025/2547 adopted 10 December 2025, **Scope 2 (indirect electricity emissions) is priced in the initial definitive phase only for cement and fertilizers**. For steel, aluminium, and hydrogen, only Scope 1 is priced; their Scope 2 is reported but not priced. This is asymmetric and material.

Three findings:

- **Finding 1 (High)**: Dashboard CBAM calculation overstates the CBAM-driven incentive for grid decarbonisation / captive-coal-to-grid-RE switching at steel / aluminium / hydrogen sites. The Scope 2 share of embedded emissions at these sites (~15-70% depending on sector) does not currently flow into the CBAM bill.
- **Finding 2 (Medium)**: A real electrification loophole exists. Switching from coal-fired heat (Scope 1) to electric heat for steel / aluminium / H₂ moves emissions from Scope 1 to Scope 2 — under current rules, this eliminates them from the CBAM bill regardless of electricity carbon intensity. This is an asymmetric incentive that current dashboard methodology does not surface explicitly.
- **Finding 3 (Future-state)**: When Scope 2 is included for cement / fertilizers, the actual-factor route (claiming below grid default) requires physical hourly PPA + smart-meter + grid-diagram per the December 2025 implementing rules. Stricter than GHG Protocol Scope 2 market-based method. M-AT6 (Transmission Charge Transparency — from the earlier IEEFA refinement) and a possible M-AT7 (CBAM Scope 2 Coverage Transparency) could surface this transparently in the dashboard methodology layer.

## Verbatim quotes

### From the EU implementing rules (via secondary sources — canonical text at EUR-Lex/CELEX 32025R2547, currently blocked from automated download):

> "By contrast, cement and fertilizers (including ammonia) include both direct and indirect emissions in their embedded emissions calculation." — *EnergyTag, "CBAM 2026 and the Physical Hourly PPA Shift"*

> "In the initial phase, only direct emissions are to be calculated for iron & steel, aluminium, and hydrogen" — *EnergyTag* (paraphrasing implementing regulation)

> "Cement and Fertilizers only [are] subject to indirect emissions taxation beginning 2026" — *I-TRACK Foundation*

> "All Annex I sectors report quarterly on direct AND indirect emissions" (transitional period) — *I-TRACK Foundation*

> "Purely financial PPAs or energy attribute certificates are not sufficient" — *EnergyTag*

> "Currently, CBAM does not recognise unbundled EAC purchases" — *ecohz*

### From the dashboard methodology (live `eez/docs/METHODOLOGY_CONSOLIDATED.md`):

The dashboard's CBAM treatment (per the running methodology document and `src/scoring/`) treats CBAM-exposed embedded emissions as a uniform Scope 1 + Scope 2 calculation across all 68 CBAM-exposed sites in the cohort. No sector-specific Scope 2 inclusion flag exists in the current implementation. The M3 destination-weighted formula uses sector-level export-share weights but applies them to the full embedded-emissions number, not to a sector-disaggregated direct-vs-indirect split.

The dashboard's `EXPORT_MARKET_SHARES_BY_SUBSECTOR` data (v4.1 refinement) correctly distinguishes sectors for *destination weighting* but not for *Scope 2 coverage in initial CBAM phase*.

## Finding 1 (High): Dashboard overstates CBAM-driven grid-RE incentive for steel / aluminium / H₂

**The bug**: For Indonesian sites in CBAM-covered sectors *other than cement and fertilizers*, the dashboard currently models grid decarbonisation (or wheeled-PPA RE switching) as reducing the CBAM bill via Scope 2 reduction. Under current EU rules (post–December 2025), this is incorrect — Scope 2 doesn't price into the CBAM bill for these sectors yet.

**Sectors affected**:

| Sector | Sites in dashboard | Approx. Scope 2 share of embedded emissions | Dashboard CBAM treatment | Should be |
|---|---|---|---|---|
| Cement | 32 | ~10% | Scope 1 + Scope 2 priced | Correct as-is (Scope 2 priced) |
| Fertilizer / ammonia | 5 | varies (~20-40% if H₂ feedstock is upstream grid; lower if SMR-feedstock is dominant) | Scope 1 + Scope 2 priced | Correct as-is |
| Steel BF-BOF | 1 (Krakatau Posco) | ~15% | Scope 1 + Scope 2 priced (incorrect under current rules) | **Scope 1 only — overstates by ~15% currently** |
| Steel EAF / general | 17 | ~40-50% (electricity-intensive) | Scope 1 + Scope 2 priced (incorrect) | **Scope 1 only — overstates by 40-50%** |
| Aluminium | 2 | ~70% (electricity-intensive) | Scope 1 + Scope 2 priced (incorrect) | **Scope 1 only — overstates by ~70%** |
| Hydrogen / ammonia upstream | — | varies | partial | **Scope 1 only for green H₂ component** |
| Nickel (RKEF + HPAL) | 10 | not currently CBAM-covered at all | N/A (nickel exposure is indirect, via downstream battery-OEM-bound flows through CBAM-covered metals) | Existing dashboard treatment may need separate review |

**Practical magnitude**: for an Indonesian aluminium smelter on captive coal, current dashboard CBAM calculation may overstate the CBAM-driven incentive for clean-electricity switching by ~3-4× (the ~70% Scope 2 share isn't priced today). For BF-BOF steel, overstatement is ~15-20% (Scope 1 dominates). For cement, no change.

**Why this matters for the architecture-menu rankings**: the dashboard's six-scenario cost stack ranks site-level decarbonisation pathways (per [[Powering 24-7 Industrial Loads in Indonesia]] in the wiki) including CBAM-cost as a destination-weighted input. If the CBAM input is overstated for steel / aluminium / H₂ sites, the relative ranking shifts:

- Captive coal pathways look *worse* than they actually are under current rules (because the Scope-2 emissions that captive coal generates aren't actually penalised by CBAM for those sectors today)
- Grid-RE switching pathways look *better* than they actually are (because the Scope-2 reduction they deliver isn't credited toward the CBAM bill for those sectors)
- CCS retrofit pathways look *correctly priced* for these sectors (CCS reduces Scope 1, which IS priced)
- Process-change pathways (BF-BOF → DRI-EAF; brown → green H₂) look correctly priced

The dashboard's Scope-1-vs-Scope-2 sensitivity is therefore biased toward over-recommending grid-RE / wheeling pathways for the steel / aluminium / hydrogen cohort and under-recommending CCS / process-change pathways.

**Recommended fix**: Add a per-sector flag `cbam_scope_2_priced` in the assumption layer (`src/assumptions.py` or equivalent). Set `True` for cement and fertilizer sites; `False` for steel / aluminium / hydrogen sites in the initial CBAM phase. The M3 formula in the scoring pipeline then uses sector-disaggregated embedded-emissions: `CBAM_bill = (scope_1_emissions + scope_2_emissions_if_priced) × P_effective`. Add a sensitivity scenario for future Scope 2 expansion (toggle the flag to `True` for all sectors and re-rank — useful for showing what shifts when EU eventually extends).

## Finding 2 (Medium): Electrification loophole — Scope 1 → Scope 2 removes emissions from CBAM under current rules

**The phenomenon**: For steel / aluminium / hydrogen sites under current CBAM rules, switching combustion-based heat or process energy to electric (e.g., electric arc furnace for steel; electric calcination for aluminium-precursor alumina; electric SMR for hydrogen) *converts* Scope 1 emissions to Scope 2 emissions. Under current rules, Scope 2 isn't priced for these sectors — so the same physical CO₂ emissions (assuming the electricity comes from coal generation) move from "priced as Scope 1" to "not priced as Scope 2." Effectively, electrification eliminates the CBAM bill for these sectors *regardless of the carbon intensity of the electricity*.

**Why this matters for the dashboard**: the dashboard's architecture-menu currently treats electrification + grid-RE as a pathway with both Scope 1 reduction (combustion eliminated) and Scope 2 emissions (electricity demand creates new Scope 2). Under current CBAM rules, this means:

- Electrification + clean electricity: real emissions reduction; CBAM bill drops to near-zero
- Electrification + captive coal: real emissions *stay roughly constant* (Scope 1 → Scope 2 substitution at similar carbon intensity); CBAM bill drops to near-zero anyway *for steel / aluminium / H₂ in the initial phase*

**The asymmetric incentive**: the second case is the loophole. A steel mill that electrifies its furnace and powers it from a new captive coal plant has roughly the same physical emissions footprint but a much smaller CBAM bill than it would have had under combustion. This is a real (likely unintended) feature of the initial-phase Scope 2 exclusion. The EU may close this loophole in future Scope 2 expansion; until then, it's the regulatory reality.

**Dashboard recommendation**: surface this asymmetry explicitly in the architecture-menu narrative — for steel / aluminium / H₂ sites, the CBAM-driven incentive for electrification is *partially decoupled* from the grid decarbonisation question under current rules. This is sensitive but important. The user-facing dashboard methodology should call this out so that scenario rankings are interpretable.

A useful dashboard treatment: add an explicit "post-CBAM-Scope-2-expansion" sensitivity scenario. Currently the architecture menu shows what's true today; the future-state sensitivity shows what shifts when the loophole closes (electrification + captive coal pathway looks much worse; CCS + Scope 1 abatement pathway looks less differentiated).

## Finding 3 (Future-state): M-AT7 candidate — CBAM Scope 2 Coverage Transparency

Following the existing v4.3 M-AT pattern (badge + override + methodology drawer + URL state + live recompute — established in [[Indonesian Transmission Financing Reform]]'s M-T1 + the earlier IEEFA refinement's M-AT6 transmission-charge candidate):

**M-AT7 — CBAM Scope 2 Coverage Transparency**:

- **Badge**: per-site indicator showing whether Scope 2 is priced in the current CBAM phase for this site's sector. Values: `priced` (cement / fertilizer) | `reported-only` (steel / aluminium / H₂) | `not-covered` (nickel — only downstream exposure).
- **Override**: user can toggle "Assume Scope 2 expansion" for sensitivity analysis — re-ranks the architecture menu accordingly.
- **Methodology drawer**: surfaces the EU Implementing Regulation 2025/2547 sectoral split + the wiki fact-check (`CBAM Scope 2 and REC Credibility-fact-check`).
- **URL state**: `?cbam_scope2_expansion=true` for sharing the alternate-state view.
- **Live recompute**: the M3 destination-weighted CBAM formula recomputes with the alternate Scope 2 coverage rule.

**Pairs with M-AT6** (Transmission Charge Transparency — from the earlier IEEFA refinement). Both surface CBAM-vs-grid-economics interactions that are currently buried in the methodology. M-AT6 = *what does transmission cost when wheeling activates*; M-AT7 = *what does CBAM Scope 2 cost when expansion happens*. Together they make the corporate-RE-procurement architecture-menu defensible across regulatory scenarios.

**Effort estimate**: M-AT7 is the smallest of the M-AT candidates. Per-sector flag + UI badge + sensitivity toggle. Roughly 1-2 working days; smaller than M-AT1 (substation utilisation, ~5 days) or M-AT6 (transmission charge transparency, 1-3 days).

## Recommendations

**Near-term** (v4.2 or v4.3 — pre-launch, low effort):
- (a) Add per-sector flag `cbam_scope_2_priced` in `src/assumptions.py` (or equivalent location). Set True for cement + fertilizer; False for steel / aluminium / hydrogen / electricity-imports. Wire into the M3 destination-weighted formula in the scoring pipeline.
- (b) Update `METHODOLOGY_CONSOLIDATED.md` §M3 to distinguish Scope 2 inclusion by sector under current rules; reference EU Implementing Regulation 2025/2547.
- (c) Update the architecture-menu narrative in `METHODOLOGY_CONSOLIDATED.md` and the dashboard's "Methodology" page to surface the Scope 1 / Scope 2 sectoral split and the electrification loophole.

**Medium-term** (v4.3 — alongside M-AT1 / M-T1 / M-AT6):
- (d) Implement **M-AT7 (CBAM Scope 2 Coverage Transparency)** per the spec above. Effort ~1-2 days. Pairs with M-AT6 from the IEEFA refinement.
- (e) Add an explicit "Scope 2 expansion" sensitivity scenario to the architecture menu (toggleable; defaults to current rules).

**Long-term** (post-launch, monitoring):
- (f) Track EU regulatory action on Scope 2 expansion timing. Sandbag policy briefs (Aug 2025) argue for expansion; EU review timing 2026+. When expansion happens, the dashboard's sectoral-Scope-2 flag is the natural integration point.
- (g) Consider per-sector Scope 1 vs Scope 2 disaggregation in the embedded-emissions input data, not just at the M3 stage. Currently the dashboard may use composite Scope-1-plus-2 emissions factors per sector; for the steel / aluminium / H₂ sectors specifically, the Scope 1 component should be separately addressable.

## Cross-doc consistency pattern observation (continued)

Fourth cross-doc inconsistency finding in 4 days:

1. RUPTL GEAS abbreviation drift (earlier)
2. METHODOLOGY line 4 site-count bug (earlier)
3. BPP / T&D treatment inconsistency in BPP mode (IEEFA-source refinement; mid-day 2026-05-13)
4. CBAM Scope 2 sectoral coverage mismatch (this refinement; 2026-05-14)

Cumulative case for a periodic cross-doc consistency lint as a skill is now compelling. Each finding has been the result of an ad-hoc cross-reference during another task (the IEEFA ingest surfaced the BPP issue; this CBAM fact-check surfaced the Scope 2 sectoral coverage issue). A scheduled or on-demand lint that systematically compares the wiki's regulatory claims against canonical sources + against dashboard implementation would catch these proactively rather than reactively. Worth formalising as a skill in the next iteration.

## Connections

- `syntheses/CBAM Scope 2 and REC Credibility-fact-check.md` (Energy/Renewables vault) — full wiki fact-check anchoring this refinement.
- `concepts/Carbon Border Adjustment Mechanism (CBAM).md` (Energy/Renewables vault) — wiki concept page updated with sectoral Scope 2 split.
- `syntheses/Corporate RE Procurement in Indonesia.md` (Energy/Renewables vault) — wiki synthesis updated with sectoral Scope 2 distinction.
- `eez/docs/refinement/methodology_transmission_cost_treatment_review_2026-05-13.md` — sister refinement on BPP / T&D treatment; pairs with this one as the two recent CBAM-grid-economics findings. Both anchor v4.3 / future M-AT pattern candidates.
- `eez/docs/refinement/v4_3_methodology_transparency_refinement.md` — the v4.3 transparency pattern foundation (M-AT1 + M-T1). This refinement is downstream and proposes M-AT7 as a natural extension.

## Verification trail

- EU Commission Implementing Regulation (EU) 2025/2547 (10 December 2025) — canonical legal text. EUR-Lex URL: `https://eur-lex.europa.eu/eli/reg_impl/2025/2547/oj/eng`. **Direct PDF download from EUR-Lex is currently blocked from automated access** (anti-scraping). Manual download recommended for future ingest.
- Pexapark, "CBAM Rules Set for 2026, with Physical Hourly PPAs at the Core" — `raw/Pexapark CBAM Rules Set for 2026 Physical Hourly PPAs at the Core.md` in Energy/Renewables vault.
- EnergyTag, "CBAM 2026 and the Physical Hourly PPA Shift" — `raw/EnergyTag CBAM 2026 and the Physical Hourly PPA Shift.md`.
- I-TRACK Foundation, "EACs and indirect emissions reporting under CBAM" — `raw/I-TRACK EACs and Indirect Emissions Reporting under CBAM.md`.
- ecohz, "How to use Power Purchase Agreements to decarbonise under CBAM" — `raw/ecohz Power Purchase Agreements and CBAM.md`.
- Sandbag policy briefs (Aug 2025) — argue for Scope 2 expansion; signal direction-of-travel.
