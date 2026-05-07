# Feature Spec: v4.1 Foundation Refactor (Refined)

**Theme:** Better foundations. Multi-tier LCOE, multi-incumbent references, captive arrangement classification, marginal cost methodology, **destination-weighted CBAM exposure** (replaces single-EU-share weighting), **hydro in the hybrid optimizer** (replaces "future extensibility"), storage LCOS, **per-region wind nighttime fraction**, **OEM scope-3 dataset for destination-weighted CBAM**. No new "features" per se, but enables everything that follows in v4.2 through v4.5.

**Why this ships first:** Every subsequent release builds on these abstractions. If v4.2 hardcodes the BPP comparison, v4.3 has to rewrite it. Refactor first.

**Refinement note (vs v4.1 baseline):** This refined spec supersedes the original `v4_1_foundation_spec.md`. The five methodological gaps surfaced in [[Indonesia Dashboard Methodology Review]] §v4.1 gaps are integrated as §6A (hydro in hybrid optimizer), §7 (destination-weighted CBAM with OEM scope-3 dataset), §6.5 (daytime/nighttime marginal cost split), §6.6 (geothermal NCG emission factor handling pre-empted before geothermal lands), and §3.5 (export-mix data tier with confidence flagging). The spec preserves the original §1–§15 structure; refinements appear inline with **(Refined)** markers and as new subsections.

**Effort:** ~7–9 focused work days (up from baseline 5–7). Roughly 2–2.5 calendar weeks with normal interruptions. The destination-weighted CBAM and hydro-in-optimizer additions add ~2 days of net effort vs the baseline spec.

**Status:** Ready for implementation, supersedes baseline `v4_1_foundation_spec.md`.

---

## What This Release Addresses

v4.1 is the foundation refactor — every subsequent release builds on it. This refined version integrates 5 methodological gaps surfaced by [[Indonesia Dashboard Methodology Review]] §v4.1 gaps directly into the original v4.1 scope, and adopts IEA cost terminology as the primary column-name convention. Changes group into 5 themes. Links jump to the detailed section covering methodology, rationale, schema, implementation, and validation.

### 1. Cost framework refactor (IEA-aligned) — 4 changes

*Replace single-LCOE-vs-BPP framework with multi-tier IEA-named LCOE / LCOS / Full System LCOE outputs and multi-incumbent references.*

| Section | What's changing | Why |
|---|---|---|
| [§2.1 Multi-tier solar cost outputs (IEA-aligned)](#21-multi-tier-solar-cost-outputs-refined--iea-aligned-column-names) | `lcoe_generation_usd_per_mwh` (LCOE), `full_system_lcoe_delivered_*`, `full_system_lcoe_firm_4h/8h_*` replace v4.1-baseline `lcoe_generation` / `lcoe_delivered` / `lcoe_firm_*` | v4.0 outputs single LCOE; v4.1's multi-tier is what investment decisions actually need. IEA-aligned naming reduces translation friction with DFI analysts and the energy-economist literature. |
| [§2.2 Multi-incumbent cost references](#22-multi-incumbent-cost-references) | BPP, marginal-daytime, marginal-nighttime, industrial tariff, captive incumbents | Different sites compete against different incumbents (grid-connected vs captive coal vs captive gas vs PLN). v4.0's "everyone vs PLN BPP" misranks captive sites by 30–50%. |
| [§2.6 IEA terminology alignment (column names ARE IEA-named)](#26-iea-terminology-alignment-refined--column-names-are-iea-named) | IEA terms as primary column-name convention; T1/T2/T3 framing preserved as parallel cross-walk | Column names show up in CSV exports analysts paste into investment memos. IEA-aligned names remove translation at the column-header level, not just UI labels. |
| [§10.1 Schema](#101-new-fields-added-refined--iea-aligned-column-names) + [§15.1 Backwards-compat aliases](#151-field-aliases-refined--iea-rename--v40-deprecation-handling) | 30+ new fields; v4.0 column kept as deprecation alias for one release | (Refined 2026-05-07) v4.0's `lcoe_usd_per_mwh` meant *delivered* LCOE; v4.1 adds `lcoe_generation_usd_per_mwh` as a NEW column for IEA generation-only semantics rather than reusing the bare name. v4.0's column survives one release with a deprecation warning, then is removed in v4.2. Eliminates silent-miscalibration risk for any v4.0 CSV already in stakeholder spreadsheets. |

### 2. Site classification & captive economics — 3 changes

*Per-site classification of electricity arrangement, captive fuel type, and export market shares replaces the v4.0 "everyone vs PLN BPP" framing.*

| Section | What's changing | Why |
|---|---|---|
| [§3 Site classification schema](#3-site-classification-schema), [§3.3 export market share defaults](#33-export-market-share-defaults-refined--replaces-simple-sectoral-table), [§3.4 site-specific overrides](#34-site-specific-export-mix-overrides-refined--new-subsection), [§3.5 per-market carbon prices](#35-per-market-effective-carbon-price-trajectory-refined--new-subsection) | Per-site `export_market_shares` dict + sectoral defaults + per-market `carbon_price_by_market` trajectory | The export-mix dict is the input that makes destination-weighted CBAM (§7) possible. Without it, model defaults to 100% EU exposure (over-counting) or single eu_export_share scalar (under-counting on China ETS + OEM scope-3). |
| [§4 Captive coal economics](#4-captive-coal-economics) | Defaults (~$45/MWh blended) + site-specific overrides for IMIP, IWIP, Obi, Konawe | Captive coal LCOE varies 30%+ by region (fuel transport, plant age, vertical integration). v4.0 has no captive cost reference at all; comparing solar to PLN BPP for captive sites gives the wrong economic signal. |
| [§5 Captive gas economics](#5-captive-gas-economics) | Separate methodology for fertilizer/petrochemical sites at ~$65/MWh | Captive gas is a fundamentally different economic story than coal. Solar at $80/MWh is a $15/MWh gap from gas vs $35/MWh from coal. Concessional financing flips the gas case but not the coal case — need separate modelling. |

### 3. Marginal cost & hybrid renewable optimizer — 2 changes

*Marginal cost split by daytime/nighttime (partial VALCOE elements). Hydro pulled forward into the hybrid optimizer as a 3-way solar × wind × hydro grid.*

| Section | What's changing | Why |
|---|---|---|
| [§6.2 Marginal cost methodology with daytime/nighttime split](#62-estimation-methodology-refined--daytimenighttime-split) | Region-specific factors per regime (Maluku/Papua daytime ~2.5×, nighttime ~2.2×) | Solar displaces *daytime* marginal generation. In Eastern Indonesia where diesel sets daytime peak, marginal isn't BPP × regional factor — it's diesel SRMC ($150–280/MWh). v4.1 baseline's single regional factor smears daytime/nighttime together. Partial VALCOE time-of-day component. |
| [§6A Hydro in the hybrid optimizer](#6a-hydro-in-the-hybrid-optimizer-refined--new-section-replaces-v41-68-reserved) | 3-way solar × wind × hydro optimization with `nighttime_fraction = 1.0` for hydro | JETP Captive Power Study site cases (Sulawesi Tengah, Kalimantan Barat, Kalimantan Utara) show solar+hydro+gas at $59–80/MWh — beating captive coal even before carbon pricing. Without hydro in the optimizer, scenario 5 (the cost-optimal architecture for hydro-rich Sumatra/Kalimantan sites) is unreachable. |

### 4. Destination-weighted CBAM — 2 changes

*Replace single-EU-share weighting with per-market shares × per-market carbon-price stack (M3 from the merged synthesis). Pull OEM scope-3 dataset forward from v4.5.*

| Section | What's changing | Why |
|---|---|---|
| [§7 Destination-weighted CBAM exposure](#7-destination-weighted-cbam-exposure-refined--replaces-single-eu-share-weighting) | Per-market `export_market_shares` × per-market `carbon_price_by_market` (M3 formula) | Indonesian nickel exports flow to multiple markets (China stainless 70%, EU OEM-bound 20%, direct EU/UK/US 10%), each with different effective carbon prices. Single-EU-share gives ~$9/t effective; destination-weighted gives ~$35/t today / ~$70/t by 2030 — **4× error** in the v4.1 baseline that causes `cbam_urgent` to fire late or not at all. |
| [§11.8 OEM scope-3 commitment dataset (pulled forward from v4.5)](#118-oem-scope-3-commitment-dataset-refined--pulled-forward-from-v45) | Tesla, BMW, VW, Hyundai, LG, CATL battery-grade carbon-intensity premium in `dim_carbon_price_by_market.csv` | Destination-weighted stack needs per-market carbon prices including OEM scope-3 ($10–30/t Ni today, growing). Without the data, v4.1 ships with a stub for `battery_supply_chain_eu_oem`; pulling forward avoids retrofit. |

### 5. Storage, provenance, and quality — 4 changes

*Storage as separate cost reference (LCOS at 4h/8h); provenance built in from v4.1 not retrofitted; geothermal NCG correction pre-empted; six-scenario coverage cross-reference.*

| Section | What's changing | Why |
|---|---|---|
| [§8 Storage and Firm LCOE methodology](#8-storage-and-firm-lcoe-methodology) | LCOS at 4h and 8h durations as IEA-named separate cost outputs (`lcos_4h_usd_per_mwh`, `lcos_8h_usd_per_mwh`) | Firmed solar's cost is two distinct things: solar LCOE and storage LCOS. Conflating them (as v4.0 does in `lcoe_with_battery`) hides which cost is the binding lever. Investors ask "is BESS or solar the constraint?" — separating the costs answers it. |
| [§9 Confidence and provenance tracking](#9-confidence-and-provenance-tracking) | Per-field `<field>_source / vintage / confidence / citation` built in from v4.1 | Without provenance, every numeric output is unauditable. DFI investment committees can't use unauditable numbers. Building it in from v4.1 (vs retrofitting later) is dramatically cheaper. |
| [Appendix A: Geothermal NCG handling (preventive)](#appendix-a-geothermal-ncg-handling-preventive--refined) | When geothermal lands, NCG emissions 42–73 g/kWh not zero (Wayang Windu 73, Kamojang 73, Ulubelu 43 per ESDM 2024 §1) | Indonesian geothermal NCG is non-trivial; treating as zero overstates Scope 2 savings by 5–10%. Pre-empt the bug before geothermal lands in scenario 6 architecture (v4.0.5 / v4.1). |
| [Appendix C: Six-scenario coverage cross-reference](#appendix-c-six-scenario-coverage-cross-reference-refined--new-appendix) | Maps wiki's six scenarios to where each is computed across v4.0/v4.0.5/v4.1/v4.2/v4.3.5 | Scenarios computed across multiple releases and code modules; cross-reference table prevents methodology gaps from hiding ("we cover scenario 5"; "actually you don't because hydro is reserved for v5"). Makes JETP-style analysis end-to-end reproducible. |

---

## Table of Contents

(Refined 2026-05-07: "Phase" column maps each section to v4.1a or v4.1b per §1.5 release split. Sections marked `a+b` carry a phase-aware structure with subsections per phase.)

| § | Section | Phase | Skip for Claude Code? |
|---|---|---|---|
| 1 | Strategic Context | both | Yes (reference) |
| 1.5 | Release split: v4.1a + v4.1b (Refined) | both | **No (sequencing)** |
| 2 | Cost Comparison Framework (incl. IEA rename §2.6) | **v4.1a** | **No (foundational)** |
| 3 | Site Classification Schema (3.1–3.2 v4.1a, 3.3–3.5 v4.1b) | a+b | **No (build)** |
| 4 | Captive Coal Economics | **v4.1a** | **No (build)** |
| 5 | Captive Gas Economics | **v4.1a** | **No (build)** |
| 6 | Marginal Cost Methodology (incl. daytime/nighttime split §6.2) | **v4.1a** | **No (build)** |
| 6A | Hydro in the Hybrid Optimizer (Refined — was v4.1 §6A.8 reserved) | **v4.1b** | **No (build)** |
| 7 | Destination-Weighted CBAM Exposure (Refined — was single-EU-share) | **v4.1b** | **No (build)** |
| 8 | Storage and Firm LCOE Methodology (LCOS at 4h/8h) | **v4.1a** | **No (build)** |
| 9 | Confidence and Provenance Tracking | **v4.1a (used by both)** | **No (build)** |
| 10 | Output Schema (a-columns and b-columns split) | a+b | **No (build)** |
| 11 | Data Compilation Tasks (11.1–11.7 v4.1a, 11.8 v4.1b) | a+b | **No (data work)** |
| 12 | To-Do List (with §12.0 phase-routing table) | a+b | **No (tasks)** |
| 13 | Validation Strategy | a+b | **No (test cases)** |
| 14 | Success Criteria (split into 14.1a, 14.1b, 14.2a, 14.2b, 14.3, 14.4) | a+b | **No (definition of done)** |
| 15 | Migration and Backwards Compatibility (IEA rename in v4.1a only) | **v4.1a** | **No (build)** |
| Appendix A | Geothermal NCG handling (preventive) | **v4.1b** | **No (1-line fix)** |
| Appendix B | What's NOT in v4.1 | both | Yes (reference) |
| Appendix C | Six-scenario coverage cross-reference (JETP-style analysis) | **v4.1b** | Yes (reference) |

---

## 1. Strategic Context

The v4.0 dashboard outputs a single solar LCOE value per site and compares it to a single regional BPP value. This is too simple. Five methodology gaps:

**Gap 1: Sites have different incumbent costs.** A grid-connected industrial site competes against PLN BPP. A captive coal nickel smelter competes against ~$45/MWh captive coal. A captive gas fertilizer plant competes against ~$65/MWh captive gas. Comparing all three to PLN BPP gives misleading results.

**Gap 2: BPP averages obscure marginal costs, both spatially and temporally.** PLN's regional BPP is the weighted average of all generation. Solar displaces marginal generation, not average — and specifically *daytime* marginal generation. In Eastern Indonesia where diesel sets the daytime peak, BPP comparison underestimates solar's economic value by 50–100%, and a flat regional adjustment factor averages over a 2–3× daytime/nighttime split.

**Gap 3: CBAM with single-EU-share weighting is structurally too simple.** Indonesian commodities flow into multiple markets, each with its own effective carbon price. For nickel: ~70% to China stainless (China ETS exposure), ~20% battery supply chain (EU CBAM + OEM scope-3 premium), ~10% direct EU/UK/US (CBAM + UK CBAM). A single `eu_export_share` scalar treats China exports as zero-carbon and misses OEM scope-3 entirely — a 4× error vs the destination-weighted carbon stack from [[Powering 24-7 Industrial Loads in Indonesia]].

**Gap 4: LCOE without storage cost is incomplete for baseload comparison.** Captive coal runs 24/7. Solar without storage only delivers daytime energy. Comparing the two requires firm delivered LCOE (solar + storage) for baseload competitiveness analysis.

**Gap 5: The hybrid optimizer is missing hydro.** Solar + hydro + gas is the JETP-modelled cost-optimal architecture for hydro-rich Sumatra and Kalimantan industrial sites — often beating captive coal even before carbon pricing. v4.1 baseline reserves hydro as "future extensibility"; the refined spec pulls it forward.

This release fixes all five gaps as the foundation for v4.2 onwards.

---

## 1.5 Release split: v4.1a + v4.1b (Refined 2026-05-07)

Per the /plan-eng-review (2026-05-07) decision, v4.1 ships in **two independently-shippable phases** rather than one bundled release. Both phases share this spec; the split is enforced at the implementation level via the section map below.

### Why split

Five major features in one release is the failure mode the dashboard_roadmap_v4_v5.md explicitly warns against (§1.1, "scope creep"). Splitting reduces blast radius per release: if v4.1a's IEA rename produces unexpected scorecard drift, that's debugged in isolation before the destination-weighted CBAM data + hydro optimizer changes land on top.

### Section map

| Phase | Theme | Sections | Realistic effort |
|---|---|---|---|
| **v4.1a** — *Foundation: incumbents + IEA rename + provenance* | Multi-tier LCOE outputs with IEA names, multi-incumbent references with daytime/nighttime split, captive coal/gas economics, provenance plumbing, LCOS at 4h/8h | §2 (all), §3.1–3.2, §4, §5, §6 (incl. 6.2), §8, §9, §10 (the v4.1a column subset), §11.1–11.7, §15 | ~6–7 focused work days |
| **v4.1b** — *Foundation: destination-weighted CBAM + hydro hybrid + geothermal NCG pre-empt* | Per-market export share dict, per-market carbon-price trajectory, destination-weighted CBAM exposure, hydro 3-way hybrid optimizer, OEM scope-3 dataset, geothermal NCG handling, six-scenario cross-reference | §3.3–3.5, §6A, §7, §10 (the v4.1b column subset), §11.8, Appendix A, Appendix C | ~5–6 focused work days |

Per-phase to-do lists, validation strategies, and success criteria are separated in §12, §13, §14 below.

### Cross-phase dependencies

- **§9 Provenance** is built once in v4.1a and used by both phases. v4.1b's new fields (e.g. `cbam_destination_weighted_*`) carry the standard `_source/_vintage/_confidence` pattern from day one.
- **§3 Site Classification** spans both. v4.1a needs §3.1–3.2 (electricity arrangement + captive fuel type) for captive cost matching; v4.1b needs §3.3–3.5 (export market shares + per-market carbon prices) for destination-weighted CBAM. Both write to `fct_site_classifications.csv` — v4.1a creates the table with the columns it needs, v4.1b extends it with the export-share columns.
- **§10 Output schema** has a column subset per phase. The v4.1a column block (multi-tier LCOE, incumbents, captive cost) is locked when v4.1a ships; v4.1b appends the destination-weighted-CBAM columns and hydro proximity columns without modifying v4.1a's columns.
- **§15 Migration** applies to v4.1a only (the IEA rename + bare `lcoe_usd_per_mwh` deprecation alias). v4.1b is purely additive — no breaking changes vs v4.1a.

### Sequencing

```
v4.0 (current)
   │
   ├── v4.0.5 (methodological fixes — separate release, ships first)
   │
   ├── v4.1a (incumbents + IEA rename + provenance)
   │     │
   │     ├── locked golden v4.0 baseline already captured (tests/fixtures/scorecard_v4_0_baseline.csv)
   │     ├── locks v4.1a baseline before v4.1b branches
   │     │
   │     └── ships independently with its own Zenodo DOI
   │
   └── v4.1b (CBAM + hydro)
         │
         ├── builds on v4.1a (depends on lcoe_generation_usd_per_mwh, multi-incumbent refs)
         │
         └── ships independently with its own Zenodo DOI

v4.2 (project finance) only branches after v4.1b ships.
```

Strict sequencing: v4.1a branches and ships before v4.1b branches. Parallel branches on the same scorecard schema are the merge nightmare the eng review flagged.

### Per-phase Zenodo DOIs

Both phases publish their own DOI for citation continuity:
- v4.1a → "v4.1a Foundation: incumbents and IEA rename"
- v4.1b → "v4.1b Foundation: destination-weighted CBAM and hydro hybrid"

The dashboard's CHANGELOG.md entries are also split per phase.

---

## 2. Cost Comparison Framework

This is the architectural core. Get this right once; everything else builds on it.

### 2.1 Multi-tier solar cost outputs (Refined — IEA-aligned column names)

Per site, output four solar cost variants. **Column names follow the IEA cost-terminology standard** (LCOE / LCOS / Full System LCOE / VALCOE) — see §2.6 for full mapping and the deprecation handling for v4.0 column names.

| Column | IEA term | Includes | Use case |
|---|---|---|---|
| `lcoe_generation_usd_per_mwh` | **LCOE** (base) | CAPEX + OPEX + financing | Comparison to global benchmarks; pure technology cost |
| `full_system_lcoe_delivered_usd_per_mwh` | **Full System LCOE** (delivered) | LCOE + gen-tie transmission | Grid-connected IPP screening; PLN procurement comparison |
| `full_system_lcoe_firm_4h_usd_per_mwh` | **Full System LCOE** (firm 4h) | LCOE + transmission + 4-hour storage at 20% nameplate | Daily peak shifting; partial firm capability |
| `full_system_lcoe_firm_8h_usd_per_mwh` | **Full System LCOE** (firm 8h) | LCOE + transmission + 8-hour storage at 50% nameplate | Near-baseload competition; captive coal replacement |

**⚠ Breaking-change note for v4.0 consumers (Refined — 2026-05-07 hard-rename decision).** v4.0's `lcoe_usd_per_mwh` column means *delivered* LCOE (LCOE + transmission). v4.1 introduces a NEW column `lcoe_generation_usd_per_mwh` for IEA generation-only semantics — does NOT reuse the `lcoe_usd_per_mwh` name. The original `lcoe_usd_per_mwh` column survives one release with a deprecation warning (now points at `full_system_lcoe_delivered_usd_per_mwh`), then is removed in v4.2. This eliminates the silent-miscalibration risk where same-name-different-value would have broken any v4.0 number already in a spreadsheet. See §15.1.

### 2.2 Multi-incumbent cost references

Per site, identify applicable incumbent cost references. Different sites have different relevant incumbents:

| Incumbent | Definition | When applies |
|---|---|---|
| `incumbent_pln_bpp` | PLN regional average cost of supply | Always (regulatory ceiling for grid-connected IPP) |
| `incumbent_pln_marginal_daytime` | PLN avoided generation cost during *solar* hours (Refined — was single `pln_marginal`) | Always (true economic value to grid for solar) |
| `incumbent_pln_marginal_nighttime` | PLN avoided generation cost during *non-solar* hours (Refined — new) | Always (true economic value to grid for storage / dispatchable RE) |
| `incumbent_industrial_tariff` | What grid-connected industrial customer pays | Sites with PLN grid connection |
| `incumbent_captive` | Self-generated electricity cost from captive plant | Sites with captive generation |

### 2.3 Comparison matrix by use case

Different use cases use different solar variants and different incumbents:

| Use case | Solar variant | Incumbent | Typical sites |
|---|---|---|---|
| PLN IPP procurement (Perpres 112/2022) | `lcoe_delivered` | `incumbent_pln_bpp` | Grid-connected greenfield |
| Behind-the-meter, partial coverage | `lcoe_delivered` | `incumbent_industrial_tariff` | KEKs on PLN grid |
| Captive solar replacing captive coal, daytime | `lcoe_delivered` | `incumbent_captive` | Nickel IIA partial replacement |
| Captive solar 24/7 baseload | `lcoe_firm_baseload` | `incumbent_captive` | Nickel IIA full baseload |
| Economic dispatch analysis (daytime) | `lcoe_delivered` | `incumbent_pln_marginal_daytime` | Policy analysis for solar |
| Economic dispatch analysis (nighttime) | `lcoe_firm_baseload` | `incumbent_pln_marginal_nighttime` | Policy analysis for dispatchable RE / storage |

### 2.4 Carbon pricing as orthogonal layer (Refined — destination-weighted)

Carbon pricing applies to incumbent costs based on emissions intensity AND the destination-weighted carbon-price stack (see §7). For v4.1, support these effective-carbon-price scenarios as toggles:

- `none`: 0 USD/tCO2
- `domestic_low`: 5 USD/tCO2 (current Indonesian IDX Carbon)
- `domestic_high`: 25 USD/tCO2 (potential 2030 Indonesia IDX)
- `effective_2025`: destination-weighted ~$35/t for typical Indonesian nickel (China ETS + EU CBAM + OEM scope-3, weighted)
- `effective_2030`: destination-weighted ~$70/t for typical Indonesian nickel (China ETS rises, full CBAM enforcement, OEM scope-3 premium grows)
- `cbam_full_2026`: 90 USD/tCO2 (current EU CBAM applied to 100% of output — stress test only)
- `cbam_full_2030`: 150 USD/tCO2 (projected full EU CBAM)

The default scenario for CBAM-exposed sites is `effective_2025` (realistic destination-weighted) rather than `cbam_full_2026`. Stress test toggle exposes the `cbam_full_*` scenarios.

### 2.5 Compute Once, Use Everywhere

All cost variants and incumbents should be computed in a single pipeline pass and stored as outputs. Do NOT recompute on every UI request. The new schema (§10) holds them all.

### 2.6 IEA terminology alignment (Refined — column names ARE IEA-named)

The dashboard's multi-tier cost framework adopts the standard IEA cost terminology (LCOE / LCOS / Full System LCOE / VALCOE) used in the wiki's [[Levelized Cost of Energy]] page **as the primary column-name convention** in v4.1. This is a deliberate departure from the v4.0 schema and the v4.1-baseline `lcoe_generation_*` / `lcoe_delivered_*` / `lcoe_firm_*` column names — both renamed in this refined spec to align with how DFI analysts, energy economists, and policy makers already discuss costs in the IEA-aligned literature.

| IEA term | v4.1 column name | What it captures | Where computed |
|---|---|---|---|
| **LCOE** (base) | `lcoe_generation_usd_per_mwh` | Lifetime cost / lifetime generation of the asset, before transmission, storage, or system effects. The IEA pure-technology LCOE. (Refined 2026-05-07: uses the explicit `_generation_` qualifier rather than reusing the bare `lcoe_usd_per_mwh` name from v4.0, which referred to delivered LCOE.) | §2.1 |
| **Full System LCOE** (delivered) | `full_system_lcoe_delivered_usd_per_mwh` | LCOE + transmission + connection costs. Approximates IEA Full System LCOE — full Full System LCOE also includes ancillary services, balancing, and capacity value (deferred to v5.x). | §2.1 |
| **Full System LCOE** (firm 4h / firm 8h) | `full_system_lcoe_firm_4h_usd_per_mwh`, `full_system_lcoe_firm_8h_usd_per_mwh` | LCOE + transmission + LCOS at 4h or 8h duration. Composes Full System LCOE with the LCOS component. | §2.1, §8 |
| **LCOS** | `lcos_4h_usd_per_mwh`, `lcos_8h_usd_per_mwh` | Storage-only cost per MWh delivered through storage. Per IEA / Lazard LCOS+ methodology. | §8 |
| **Hybrid LCOE** | `hybrid_lcoe_usd_per_mwh` | Blended generation LCOE across solar + wind + hydro before storage. | §6A |
| **Hybrid LCOS** | `hybrid_lcos_usd_per_mwh` | Storage cost adder at reduced sizing in the hybrid mix. | §6A |
| **Hybrid Full System LCOE** | `hybrid_full_system_lcoe_usd_per_mwh` | Hybrid LCOE + Hybrid LCOS — the architecture-menu cost output for the optimal mix. | §6A |
| **VALCOE elements** (partial — time-of-day) | `incumbent_pln_marginal_daytime_usd_per_mwh`, `incumbent_pln_marginal_nighttime_usd_per_mwh` | Daytime vs nighttime marginal cost split captures the time-of-day value component of VALCOE. Capacity value (partially via hybrid BESS-reduction) and flexibility value (not modeled) are deferred. | §6.2 |
| (no IEA term) — destination-weighted carbon-adjusted incumbent | `cbam_destination_weighted_incumbent_*_usd_per_mwh` | Per-market carbon price weighted by export market shares (M3 from [[Powering 24-7 Industrial Loads in Indonesia]]). Sits alongside Full System LCOE as an incumbent-side adjustment. | §7 |

**Column-name conventions:**
- IEA term (`lcoe`, `lcos`, `full_system_lcoe`, `valcoe` when modelled) is the family prefix.
- Variant qualifier follows (`_delivered`, `_firm_4h`, `_firm_8h`).
- Unit suffix is always `_usd_per_mwh` for $/MWh quantities, `_usd_per_tco2` for carbon prices, `_pct` for percentages. Existing inconsistencies (e.g., `hybrid_lcoe_usd_mwh` without `per_`) are corrected in this refinement.

**Backwards compatibility (v4.0 → v4.1 IEA rename — Refined 2026-05-07).** v4.0's `lcoe_usd_per_mwh` column means *delivered* LCOE (LCOE + transmission). v4.1 introduces `lcoe_generation_usd_per_mwh` as a NEW column for IEA generation-only semantics — the `lcoe_usd_per_mwh` name is NOT reused with a different meaning. The v4.0 column persists for one release as a deprecation alias for `full_system_lcoe_delivered_usd_per_mwh`, then is removed in v4.2. This was an explicit eng-review decision (2026-05-07) to eliminate the silent-miscalibration risk: any v4.0 CSV already pasted into an investment memo continues to read correctly until consumers migrate. See §15.1 for the alias table and the CHANGELOG breaking-change flag.

**Gap: VALCOE proper is not computed as a single metric.** VALCOE adjusts LCOE for three value dimensions:

| VALCOE component | What it captures | Status in v4.1 refined |
|---|---|---|
| **Time-of-day value** | Solar generation during high-demand daytime hours has higher value than equivalent generation at night | **Partial** — captured implicitly through `incumbent_pln_marginal_daytime` vs `_nighttime` split (§6.2) |
| **Capacity value** | Dispatchable RE (geothermal, hydro) has higher firm-capacity value than intermittent (solar, wind); contributes to peak adequacy | **Partial** — captured implicitly through hybrid optimizer's BESS-reduction when dispatchable RE is in the mix (§6A) |
| **Flexibility value** | Storage and flexible coal cycling provide ramping/balancing services; intermittent RE typically *consumes* flexibility | **Not modeled** — deferred to v5.0 PyPSA |

A full VALCOE output column (`valcoe_usd_per_mwh`) would require explicit valuation of capacity-payment-equivalent and flexibility-service-equivalent on top of the existing LCOE variants. Deferred to v5.x.

**UI labelling.** Score Drawer cost displays use the IEA term as the primary label with the column name in monospace tooltip for codebase traceability:

- "**LCOE**: $X/MWh" → from `lcoe_generation_usd_per_mwh`
- "**Full System LCOE (delivered)**: $X/MWh" → from `full_system_lcoe_delivered_usd_per_mwh`
- "**Full System LCOE (firm 8h)**: $X/MWh" → from `full_system_lcoe_firm_8h_usd_per_mwh`
- "**LCOS (4h)**: $X/MWh" / "**LCOS (8h)**: $X/MWh" → from `lcos_*_usd_per_mwh`
- "**Hybrid Full System LCOE (solar + wind + hydro)**: $X/MWh" → from `hybrid_full_system_lcoe_usd_per_mwh`
- "**Carbon-adjusted incumbent (destination-weighted, 2030)**: $X/MWh" → from `cbam_destination_weighted_incumbent_2030_usd_per_mwh`

This aligns dashboard outputs end-to-end (column names + UI labels + methodology narrative) with the IEA-aligned literature, removing translation friction. The wiki's [[Levelized Cost of Energy]] comparison table is the authoritative reference for what each term covers, includes, excludes, and the limitations of each.

**Methodology document update.** METHODOLOGY_CONSOLIDATED.md §0 (cost-column taxonomy) is rewritten to reference IEA standard names as primary, with the v4.0 / v4.1-baseline aliases listed for migration. The dashboard's pre-existing T1/T2/T3 family-tier framing (used in `docs/TAXONOMY.md`) maps cleanly:
- T1 generation = LCOE
- T2 firmed = Full System LCOE (firm 4h / firm 8h) and the LCOS component within
- T3 delivered = Full System LCOE (delivered) and the Supply Blend cascade outputs
- B benchmark = the incumbent comparison reference (BPP, marginal, captive, etc.)

This becomes the v4.1 deliverable for `docs/TAXONOMY.md`.

---

## 3. Site Classification Schema

The classification of each site is its own dataset, separable from the scorecard. This allows:
- Publishing the classification as a research artifact (`fct_site_classifications.csv`)
- Updates without rerunning all scorecard calculations
- Reuse by other tools

### 3.1 Classification fields per site

```
site_id                              # primary key
site_name                            # human-readable
sector                               # nickel, steel, cement, fertilizer, aluminium, kek
subsector                            # nickel_npi, nickel_matte, steel_eaf, steel_bfbof, etc.
region                               # province
grid_region                          # JAMALI / Sumatera / Kalimantan / Sulawesi / Maluku_Papua

# Electricity arrangement
electricity_arrangement              # enum: grid_only | grid_primary_with_captive | hybrid_captive_primary | pure_captive
captive_fuel_type                    # enum: coal_subcritical | coal_supercritical | natural_gas | oil_diesel | hybrid | none
captive_capacity_mw                  # nameplate of captive plant if applicable
captive_share_estimated              # 0.0 to 1.0; share of facility electricity from captive

# Export market shares (Refined — replaces single eu_export_share)
# ⚠ Phase: v4.1b only. Per §1.5 release split, §3.1 splits into:
#   - 3.1a (v4.1a): site_id, site_name, sector, subsector, region, grid_region,
#     electricity_arrangement, captive_fuel_type, captive_capacity_mw,
#     captive_share_estimated, last_updated, classification_confidence, notes
#   - 3.1b (v4.1b): the 4 export-share fields below + cbam_exposed
# fct_site_classifications.csv ships in v4.1a with the 3.1a columns; v4.1b
# extends it with the 3.1b columns (additive, no migration of existing rows).
export_market_shares_json            # JSON: {"china_stainless": 0.70, "battery_supply_chain_eu": 0.20, "direct_eu_uk_us": 0.10}
export_market_shares_source          # public_disclosure | sectoral_default | comtrade | unknown
export_market_shares_confidence      # high | medium | low
cbam_exposed                         # boolean — true if any market in the dict has effective carbon price > 0

# Tracking
last_updated                         # ISO date
classification_confidence            # high | medium | low
notes                                # free-text rationale
```

### 3.2 Electricity arrangement classification logic

For each site, classify into one of four buckets based on:
- GEM coal tracker data (where captive coal exists)
- Geographic location (remote = likely pure captive)
- Sectoral norms (nickel = captive, cement = grid, fertilizer = captive gas)
- Public disclosures where available

**Default classification by sector + region:**

| Sector | Region | Default | Rationale |
|---|---|---|---|
| Nickel IIA | Sulawesi/Maluku | `pure_captive`, `coal_subcritical` | Almost all major nickel parks run on captive coal |
| Aluminium | All | `hybrid_captive_primary`, varies by site | Inalum has hydro+coal mix |
| Cement | Java | `grid_only` | Most cement plants on PLN grid |
| Cement | Outside Java | `grid_primary_with_captive`, `coal_subcritical` | Some have captive backup |
| Fertilizer | All | `pure_captive`, `natural_gas` | Pupuk Kaltim, Petrokimia Gresik all captive gas |
| Steel | Java | `grid_primary_with_captive` | Krakatau Steel has gas captive supplement |
| Steel | Sulawesi | `pure_captive`, `coal_subcritical` | Newer integrated steel facilities |
| KEK | Java | `grid_only` | Existing Java KEKs on PLN grid |
| KEK | Eastern Indonesia | `pure_captive` or `hybrid_captive_primary` | Remote KEKs build their own |

Override with site-specific data where available. Document each override.

### 3.3 Export market share defaults (Refined — replaces simple sectoral table)

Replace the single `EU_EXPORT_SHARE_DEFAULTS` table with a structured **per-market** dict default, populated by sector:

```python
EXPORT_MARKET_SHARES_BY_SUBSECTOR = {
    'nickel_npi': {
        'china_stainless': 0.70,
        'battery_supply_chain_eu_oem': 0.20,
        'direct_eu_uk_us': 0.10,
    },
    'nickel_matte': {
        'battery_supply_chain_eu_oem': 0.65,
        'direct_eu_uk_us': 0.20,
        'korea_battery': 0.10,
        'china_stainless': 0.05,
    },
    'steel_eaf': {
        'asean_regional': 0.75,
        'direct_eu_uk_us': 0.05,
        'korea_japan': 0.10,
        'china_domestic': 0.10,
    },
    'steel_bfbof': {
        'domestic_indonesia': 0.50,
        'asean_regional': 0.40,
        'direct_eu_uk_us': 0.05,
        'china_domestic': 0.05,
    },
    'aluminium': {
        'asean_regional': 0.50,
        'direct_eu_uk_us': 0.10,
        'china_domestic': 0.20,
        'domestic_indonesia': 0.20,
    },
    'cement': {
        'domestic_indonesia': 0.95,
        'asean_regional': 0.05,
    },
    'fertilizer': {
        'domestic_indonesia': 0.80,
        'asean_regional': 0.15,
        'direct_eu_uk_us': 0.05,
    },
    'ammonia': {
        'domestic_indonesia': 0.70,
        'asean_regional': 0.20,
        'direct_eu_uk_us': 0.05,
        'korea_japan': 0.05,
    },
}
```

Source citations:
- World's Top Exports 2025: Indonesia overall 10% to Europe
- Bloomberg September 2024: NPI exports to Europe surged from 1,006 to 87,485 tonnes
- BPS Comtrade per HS code for sector-specific verification
- IEA Coal 2024: thermal coal trade flows
- IEA Steel Sector report 2024 for Indonesian steel exports

**Confidence flagging.** Sectoral defaults are tagged `confidence='medium'`. Site-specific overrides from annual reports get `confidence='high'`. Sites with neither default nor override get `confidence='low'` and the dashboard surfaces a "site-specific export mix data needed" warning. v4.4 site-specific override compilation is the data-side fix.

### 3.4 Site-specific export-mix overrides (Refined — new subsection)

For sites with public export-mix disclosure, override the sectoral default:

```
data/raw/site_export_shares_overrides.csv:
site_id, market_id, share, source, last_updated
imip_morowali, china_stainless, 0.50, "IMIP 2023 annual report p.45", 2024-12-01
imip_morowali, battery_supply_chain_eu_oem, 0.35, "IMIP 2023 annual report p.45", 2024-12-01
imip_morowali, direct_eu_uk_us, 0.15, "Bloomberg 2024-09 NPI export data", 2024-09-15
pt_vale_sorowako, battery_supply_chain_eu_oem, 0.45, "PT Vale 2023 annual report", 2024-12-01
pt_vale_sorowako, direct_eu_uk_us, 0.30, "PT Vale 2023 annual report", 2024-12-01
pt_vale_sorowako, korea_battery, 0.25, "PT Vale 2023 annual report", 2024-12-01
...
```

v4.1 ships with overrides for 4–6 priority sites (IMIP, IWIP, PT Vale, Harita, Trimegah, Krakatau Steel). Remaining 75 sites use sectoral defaults. v4.4 captive deep dive expands the override set.

### 3.5 Per-market effective carbon price trajectory (Refined — new subsection)

The carbon-price-by-market lookup that feeds destination-weighted CBAM (§7) lives in:

```python
CARBON_PRICE_BY_MARKET = {
    'china_stainless': {
        2025: 12.0,    # China ETS
        2030: 30.0,    # IEA APS trajectory
        2034: 50.0,
    },
    'battery_supply_chain_eu_oem': {
        2025: 90.0,    # EU CBAM + ~$10–30/t Ni OEM scope-3 (averaged)
        2030: 150.0,   # CBAM at full enforcement + premium growth
        2034: 200.0,
    },
    'direct_eu_uk_us': {
        2025: 90.0,    # EU CBAM (UK CBAM begins 2027)
        2030: 140.0,
        2034: 180.0,
    },
    'korea_japan': {
        2025: 20.0,    # Korea ETS
        2030: 50.0,
        2034: 80.0,
    },
    'korea_battery': {
        2025: 50.0,    # Korea ETS + battery-grade premium
        2030: 90.0,
        2034: 130.0,
    },
    'china_domestic': {
        2025: 12.0,
        2030: 30.0,
        2034: 50.0,
    },
    'asean_regional': {
        2025: 0.0,     # No carbon price; ASEAN market predominantly uncovered
        2030: 5.0,     # Indicative; Singapore introducing carbon tax
        2034: 15.0,
    },
    'domestic_indonesia': {
        2025: 5.0,     # Indonesia IDX Carbon
        2030: 25.0,    # Per IEA APS pathway
        2034: 60.0,
    },
}
```

Linear interpolation between snapshot years (2025 → 2026 → … → 2034). User-adjustable in v4.3 multi-pathway scenarios.

---

## 4. Captive Coal Economics

### 4.1 Why this matters

Several major industrial sites in your scorecard run on captive on-site coal generation, not PLN grid. For these sites, comparing solar LCOE to PLN BPP gives the wrong economic signal. The relevant alternative is the captive plant's own generation cost.

### 4.2 Methodology

Indonesian captive coal LCOE varies but falls in a defensible range based on:

**Coal cost:** $40–70/tonne for domestic Indonesian sub-bituminous. Plants near Kalimantan mines get lower end. Eastern Indonesia plants get higher end due to shipping.

**Heat rate:** 9,500–11,000 BTU/kWh for typical subcritical plants.

**Variable O&M:** $5–8/MWh

**Fixed O&M:** $30–50/kW-year

**Capital recovery:** Highly dependent on plant age:
- Fully depreciated plant: $5–15/MWh
- Recently built (post-2020): $20–35/MWh

**Resulting LCOE range:** $35–60/MWh for Indonesian captive coal

### 4.3 Default assumptions

```python
CAPTIVE_COAL_DEFAULTS = {
    'fuel_cost_usd_per_tonne': 55,           # mid-range domestic Indonesian thermal
    'heat_rate_btu_per_kwh': 10000,          # typical subcritical
    'variable_om_usd_per_mwh': 6,
    'fixed_om_usd_per_kw_year': 40,
    'capital_recovery_usd_per_mwh': 15,      # weighted average
    'capacity_factor': 0.85,                  # captive baseload runs hard
    'emissions_intensity_tco2_per_mwh': 0.95, # subcritical Indonesian coal
}

# Resulting default captive coal LCOE: ~$45/MWh
```

### 4.4 Site-specific overrides (Refined — anchor cases added)

Where public data exists, override defaults. Maintain in `data/raw/captive_generation_overrides.csv`:

```
site_id, captive_lcoe_usd_per_mwh, fuel_type, source, last_updated
imip_morowali, 50, coal_subcritical, "industry estimate (IESR 2024)", 2024-12-01
iwip_weda_bay, 55, coal_subcritical, "newer plants, higher capital recovery", 2024-12-01
obi_island, 60, coal_subcritical, "remote, higher fuel transport", 2024-12-01
konawe_nickel, 52, coal_subcritical, "Sulawesi Tenggara industry est", 2024-12-01
krakatau_posco_cilegon, 48, coal_supercritical, "Java steel BF-BOF, USC plant", 2024-12-01
```

**Anchor case coverage (Refined — May 2026 prioritization):** the priority override list now covers two of the three anchor cases (IMIP Morowali for nickel, Krakatau Posco for steel BF-BOF). The third anchor case (Pupuk Kaltim Bontang) is captive gas — see §5.4 for its override.

For sites without overrides, use defaults with `confidence='medium'`.

### 4.5 Citations required

- Berkeley Goldman School (2023): "Indonesia Can Cost-effectively Supplant Captive Coal-fired Power Plants with Solar Energy"
- IESR (2024): "Captive Power Plants: Indonesia's hidden coal expansion"
- IEA Southeast Asia coal-fired power costs

---

## 5. Captive Gas Economics

### 5.1 Why this is different from coal

Indonesian captive gas plants (Pupuk Kaltim, Petrokimia Gresik, Pertamina facilities) have different economics:
- Higher fuel cost than coal but lower carbon intensity
- Often long-term gas supply contracts
- Different emissions profile (0.40–0.45 tCO₂/MWh vs coal's 0.95)

### 5.2 Default assumptions

```python
CAPTIVE_GAS_DEFAULTS = {
    'fuel_cost_usd_per_mmbtu': 8,            # typical Indonesian industrial gas
    'heat_rate_btu_per_kwh': 7500,           # combined cycle
    'variable_om_usd_per_mwh': 4,
    'fixed_om_usd_per_kw_year': 25,
    'capital_recovery_usd_per_mwh': 18,
    'capacity_factor': 0.85,
    'emissions_intensity_tco2_per_mwh': 0.42,
}

# Resulting default captive gas LCOE: ~$65/MWh
```

### 5.3 Why this matters for the analysis

Captive gas at $65/MWh vs solar at $80/MWh is only a $15/MWh gap. With concessional financing dropping solar to $65–70/MWh, captive gas sites flip to solar competitive without needing carbon pricing.

This is fundamentally different from captive coal sites which need significant carbon pricing or commercial pressure to flip.

### 5.4 Site-specific overrides (Refined — anchor case added)

Where public data exists, override defaults. Maintained alongside captive coal overrides in `data/raw/captive_generation_overrides.csv` (with `fuel_type` column distinguishing them):

```
site_id, captive_lcoe_usd_per_mwh, fuel_type, source, last_updated
pupuk_kaltim_bontang, 62, gas_ccgt, "Pupuk Indonesia disclosures + IEA gas price", 2024-12-01
petrokimia_gresik, 68, gas_ccgt, "longer LNG supply chain; higher fuel cost", 2024-12-01
```

**Anchor case coverage:** Pupuk Kaltim Bontang (the dashboard's strongest near-term case at Tier A CCS proximity) has its captive gas LCOE captured here. Combined with the §4.4 captive coal overrides, all three anchor cases (IMIP Morowali, Krakatau Posco, Pupuk Kaltim Bontang) have site-specific captive cost references in v4.1.

For sites without overrides, use defaults with `confidence='medium'`.

---

## 6. Marginal Cost Methodology

### 6.1 The methodology gap

The dashboard currently uses regional BPP (PLN's average cost) as the comparison reference. But solar doesn't displace average generation; it displaces marginal generation (the most expensive plant currently running during solar hours).

For Eastern Indonesia where diesel sets the marginal price during daytime peak, BPP comparison can underestimate solar's value by 50–100%. **And for storage / dispatchable RE, the relevant marginal is different — it's the marginal during nighttime hours, not the daytime average.**

### 6.2 Estimation methodology (Refined — daytime/nighttime split)

PLN does not publish hourly dispatch data. Use regional fuel-mix-based adjustment factors **separately for daytime vs nighttime** (Refined — replaces single regional factor):

```python
MARGINAL_COST_ADJUSTMENT_BY_REGION = {
    'JAMALI': {
        'daytime': 1.10,        # Coal usually marginal; small premium during sun hours
        'nighttime': 1.20,      # Sometimes gas marginal
    },
    'Sumatera': {
        'daytime': 1.20,        # Mixed dispatch; peak more solar-displaceable
        'nighttime': 1.40,      # Mixed
    },
    'Kalimantan': {
        'daytime': 1.50,        # Coal+diesel peaking during industrial daytime
        'nighttime': 1.70,      # More diesel after solar drops
    },
    'Sulawesi': {
        'daytime': 1.60,        # Diesel-heavy peak, coal continuous
        'nighttime': 1.80,      # Mostly diesel + scarce coal
    },
    'Maluku_Papua': {
        'daytime': 2.50,        # Diesel-dominated peak — closer to diesel SRMC than fleet average
        'nighttime': 2.20,      # Slightly better; some baseload diesel runs continuously
    },
}

def estimate_marginal_cost(bpp_regional, grid_region, time_of_day):
    """
    time_of_day: 'daytime' or 'nighttime'
    """
    factor = MARGINAL_COST_ADJUSTMENT_BY_REGION[grid_region][time_of_day]
    return bpp_regional * factor
```

**Why daytime factors are higher than nighttime in some regions but lower in others:** depends on dispatch. In JAMALI, gas runs at night more than during day → nighttime marginal is gas (slightly more expensive than coal). In Maluku/Papua, daytime peak draws diesel → daytime marginal is diesel SRMC. In Kalimantan and Sulawesi, both daytime and nighttime have diesel at the margin but daytime hits peak diesel.

### 6.3 Confidence flagging

Mark marginal cost estimates with confidence:
- `jamali_coal_dominant`: narrower BPP-marginal gap, higher confidence
- `mixed_dispatch`: moderate uncertainty
- `diesel_peaking`: wider gap, lower precision
- `remote_diesel_dominated`: widest gap, methodological default

### 6.4 Citations required

- IESR analysis of Indonesian dispatch economics
- IRENA Indonesia renewable energy outlook
- Berkeley Goldman School Indonesia captive coal analysis (discusses dispatch costs)
- IEA SEA Energy Outlook 2024 §5 (dispatch tables)
- RUPTL 2025–2034 Bab IV operational reports (regional dispatch composition by season)

### 6.5 Implementation note (Refined — new subsection)

`incumbent_pln_marginal_daytime` feeds the comparator for solar (which displaces daytime generation). `incumbent_pln_marginal_nighttime` feeds the comparator for storage and dispatchable RE (geothermal, hydro). The downstream cost framework in §2.3 lists which use case picks which marginal.

---

## 6A. Hydro in the Hybrid Optimizer (Refined — new section, replaces v4.1 §6A.8 reserved)

### 6A.1 Why hydro must land in v4.1

Per [[Indonesia Dashboard Methodology Review]] §v4.1 gaps finding 14: the JETP Captive Power Study site-level cases — Sulawesi Tengah aluminium ($80/MWh, 66% RE, –87% emissions), Kalimantan Barat alumina ($61/MWh, 75% RE), Kalimantan Utara nickel ($59/MWh, 66% RE vs coal baseline $83/MWh) — *all* depend on hydro as the dispatchable backbone. Without hydro in the optimizer, the JETP-modelled cost-optimal architecture (scenario 5 in [[Powering 24-7 Industrial Loads in Indonesia]]) is unreachable from the dashboard. Sumatra (75 GW theoretical hydro potential) and Kalimantan industrial sites in particular get the wrong recommendation.

The `RESource` 2D extension is sub-millisecond compute (231 evaluations vs current 21). The blocker is the hydro proximity dataset, not the optimizer.

### 6A.2 RESource extension to hydro

Hydro is dispatchable, baseload, with `nighttime_fraction = 1.0`:

```python
hydro_resource = RESource(
    technology="hydro",
    lcoe_usd_mwh=...,           # Standalone hydro LCOE for the matched plant
    generation_mwh=...,          # Annual generation of the matched plant
    cf=0.50,                     # Indonesian run-of-river typical
    nighttime_fraction=1.0,      # Fully dispatchable
    capacity_mwp=...,            # Capacity available to the site
)
```

### 6A.3 Hydro proximity matching

Parallel to geothermal (v4.0 fixes spec finding 2). New columns on `dim_sites`:

| Column | Type | Description |
|---|---|---|
| `nearest_hydro_operating_id` | str | Name of closest operating PLTA/M |
| `nearest_hydro_operating_km` | float | Haversine distance |
| `nearest_hydro_operating_mw` | float | Capacity at that PLTA |
| `nearest_hydro_pipeline_id` | str | Name of closest pipeline RUPTL hydro addition |
| `nearest_hydro_pipeline_km` | float | Haversine distance |
| `nearest_hydro_pipeline_mw` | float | Capacity (RUPTL adds 11,890 MW RE Base / 11,690 MW ARED over 2025–2034) |
| `nearest_hydro_pipeline_target_year` | int | RUPTL-listed COD year |
| `hydro_adjacency_tier` | enum | `operating_within_50km` / `operating_within_200km` / `pipeline_within_200km_pre2030` / `pipeline_within_200km_post2030` / `none` |
| `hydro_transmission_feasibility` | enum | Same logic as geothermal |

**Source data.**
- **Operating fleet:** PLN PLTA/M list + ESDM hydro resource map. ~6 GW installed across Indonesia.
- **Pipeline:** RUPTL Tabel 3.2/3.3 hydro additions (11,890 MW RE Base / 11,690 MW ARED). Geocoded against ESDM resource map.

Both files in `data/raw/`:
- `data/raw/hydro_operating.geojson`
- `data/raw/hydro_pipeline.geojson`

### 6A.4 2D optimization grid

The optimizer extends from 1D solar-share sweep to 2D grid (solar share × hydro share, wind = remainder, with hydro available only when `hydro_adjacency_tier ∈ {operating_within_*, pipeline_within_*_pre2030}`):

```python
def hybrid_lcoe_optimized_3way(solar, wind, hydro):
    """
    2D optimizer: sweep solar_share × hydro_share, wind = 1 - solar - hydro.
    231 evaluations at 5% resolution. Sub-millisecond.
    """
    best = None
    for solar_share in range(0, 101, 5):
        for hydro_share in range(0, 101 - solar_share, 5):
            wind_share = 100 - solar_share - hydro_share
            if hydro is None and hydro_share > 0:
                continue
            blended_lcoe = compute_blended_lcoe(solar, wind, hydro, solar_share, wind_share, hydro_share)
            bess_hours = compute_hybrid_bess_hours(solar, wind, hydro, solar_share, wind_share, hydro_share)
            bess_adder = bess_storage_adder(bess_hours, blended_cf)
            allin = blended_lcoe + bess_adder
            if best is None or allin < best.allin:
                best = HybridResult(solar_share, wind_share, hydro_share, allin, ...)
    return best
```

**Hydro's nighttime fill.** With `nighttime_fraction = 1.0`, hydro covers the full overnight gap. A 30/30/40 solar/wind/hydro mix covers ~100% of daytime + ~70% of nighttime supply; BESS reduces from 14h to ~4h. This is exactly what flips scenario 5 to least-cost in JETP cases.

### 6A.5 Output fields (Refined — IEA-aligned column names)

| Column | IEA term | Type | Description |
|---|---|---|---|
| `hybrid_solar_share` | — | float | Optimal solar fraction |
| `hybrid_wind_share` | — | float | Optimal wind fraction (Refined — was implicit) |
| `hybrid_hydro_share` | — | float | Optimal hydro fraction (NEW) |
| `hybrid_lcoe_usd_per_mwh` | **Hybrid LCOE** (blended base) | float | Blended generation LCOE across solar + wind + hydro before storage |
| `hybrid_bess_hours` | — | float | Reduced BESS sizing (0–14h) |
| `hybrid_lcos_usd_per_mwh` | **Hybrid LCOS** (reduced) | float | Storage cost adder at reduced sizing — was `hybrid_bess_adder_usd_mwh` |
| `hybrid_full_system_lcoe_usd_per_mwh` | **Hybrid Full System LCOE** | float | Blended LCOE + reduced LCOS — the architecture-menu cost output. Was `hybrid_allin_usd_mwh`. |
| `hybrid_supply_coverage_pct` | — | float | Combined generation / demand |
| `hybrid_nighttime_coverage_pct` | — | float | Wind + hydro nighttime fill fraction |
| `hybrid_bess_reduction_pct` | — | float | `1 - hybrid_bess_hours / 14` |
| `hybrid_carbon_breakeven_usd_per_tco2` | — | float | Carbon price for hybrid competitiveness — standardised unit suffix |

### 6A.6 Validation

- Sumatra hydro-rich sites (Kalimantan Barat alumina-class): expect hydro share 30–50% in optimum, hybrid all-in $60–70/MWh.
- Sulawesi nickel sites with no operating hydro within 200 km: hydro share = 0; falls back to solar+wind+BESS (current v4.0 baseline).
- JETP Annex 2.1 site cases: re-run with v4.1 inputs; hybrid all-in should match JETP within ±$5/MWh.

---

## 7. Destination-Weighted CBAM Exposure (Refined — replaces single-EU-share weighting)

### 7.1 Why we don't assume single-share EU weighting

Per [[Indonesia Dashboard Methodology Review]] §v4.1 gaps finding 15: the v4.1 baseline proposes weighting CBAM by a single `eu_export_share` scalar:

```
weighted_cost = (1 - eu_export_share) × base + eu_export_share × (base + cbam_adder)
```

…which treats China exports (70% of Indonesian nickel) as zero-carbon and misses OEM scope-3 entirely. For nickel: v4.1 baseline gives ~$9/t effective; destination-weighted gives ~$35/t today, ~$70/t by 2030. **A 4× error on the core CBAM signal.**

The destination-weighted approach is M3 from the merged synthesis [[Powering 24-7 Industrial Loads in Indonesia]]:

$$LCOE_{eff,CBAM} = LCOE_{blend} + I \cdot \sum_j s_j \cdot P_j$$

### 7.2 Computation (Refined)

```python
def compute_destination_weighted_carbon_adder(
    emissions_intensity_tco2_per_mwh,
    export_market_shares,          # dict from §3.3: {market_id: share}
    carbon_price_by_market,        # dict from §3.5: {market_id: {year: price_usd_per_tco2}}
    year,
):
    """
    Compute the effective carbon adder per MWh for a site, weighted by export markets.
    """
    effective_carbon_price = sum(
        share * carbon_price_by_market[market_id].get(year, _interpolate(market_id, year))
        for market_id, share in export_market_shares.items()
    )
    return emissions_intensity_tco2_per_mwh * effective_carbon_price


def compute_destination_weighted_incumbent(
    base_incumbent_cost_usd_mwh,
    emissions_intensity_tco2_per_mwh,
    export_market_shares,
    carbon_price_by_market,
    year,
):
    """
    Incumbent cost adjusted for destination-weighted CBAM/ETS/scope-3.
    """
    carbon_adder = compute_destination_weighted_carbon_adder(
        emissions_intensity_tco2_per_mwh,
        export_market_shares,
        carbon_price_by_market,
        year,
    )
    return base_incumbent_cost_usd_mwh + carbon_adder
```

### 7.3 Three output variants

For each carbon pricing scenario, compute three variants of the carbon-adjusted incumbent (Refined — was two: weighted + full):

- `cbam_destination_weighted_incumbent_2025` — realistic exposure today (default)
- `cbam_destination_weighted_incumbent_2030` — realistic exposure 2030 (mid-trajectory)
- `cbam_destination_weighted_incumbent_2034` — realistic exposure full trajectory
- `cbam_full_incumbent_2025/2030/2034` — 100% EU CBAM stress test (kept for comparison)
- `cbam_china_only_incumbent_*` — 100% China stainless stress test (Refined — new, for scenario analysis)

The realistic case is the default. The full and china-only cases are stress-test toggles.

### 7.4 Worked example: IMIP Morowali nickel

IMIP exports majority to China stainless (Tsingshan-controlled supply chain). Override from §3.4: `{"china_stainless": 0.50, "battery_supply_chain_eu_oem": 0.35, "direct_eu_uk_us": 0.15}`.

For nickel RKEF emissions intensity 0.95 tCO₂/MWh (Sulawesi grid factor):

- **2025 effective price** = 0.50 × $12 + 0.35 × $90 + 0.15 × $90 = $6 + $31.50 + $13.50 = **$51/t**
- **2030 effective price** = 0.50 × $30 + 0.35 × $150 + 0.15 × $140 = $15 + $52.50 + $21 = **$88/t**

Carbon adder per MWh:
- **2025**: 0.95 × $51 = **$48/MWh**
- **2030**: 0.95 × $88 = **$84/MWh**

Compare to v4.1 baseline `eu_export_share = 0.20` × $90 = $18/t effective → 0.95 × $18 = $17/MWh in 2025. The baseline understates the IMIP carbon signal by ~3×.

### 7.5 Citations

- World's Top Exports 2025 (Indonesia 10% to Europe overall)
- Bloomberg September 2024 (NPI exports to Europe surge)
- BPS Comtrade per HS code
- [[Powering 24-7 Industrial Loads in Indonesia]] §The carbon-price stack (M3 derivation)
- IEA APS carbon-price trajectory (per-market projections)

---

## 8. Storage and Firm LCOE Methodology

### 8.1 Why this matters

Pure solar generates only during daylight. Industrial users typically need 24/7 power. To compete for industrial baseload (especially against captive coal that runs continuously), solar needs storage to firm output.

### 8.2 Three firming levels

For each site, compute LCOE under three storage scenarios:

**Level 0 (`lcoe_delivered`): No storage**
- Solar generates when sun shines
- Surplus exported or curtailed
- Daytime hours only effective

**Level 1 (`lcoe_firm_partial`): Partial firming**
- Battery sized to 20% of solar nameplate × 4-hour duration
- Covers evening peak (6–10 PM)
- Adds ~$30–50/MWh to delivered cost

**Level 2 (`lcoe_firm_baseload`): Near-baseload firming**
- Battery sized to 50% of solar nameplate × 8-hour duration
- Covers most evening and partial overnight
- Adds ~$80–130/MWh to delivered cost

### 8.3 Battery cost assumptions

```python
BATTERY_DEFAULTS = {
    'capex_usd_per_kwh': 350,                # IRENA 2024 benchmark
    'lifetime_years': 15,                     # cycle-limited
    'cycles_per_year': 365,                   # daily cycling
    'depth_of_discharge': 0.85,
    'round_trip_efficiency': 0.90,
    'fixed_om_usd_per_kw_year': 7,
}
```

### 8.4 LCOS calculation

```python
def compute_battery_lcos(
    capacity_kwh,
    duration_hours,
    capex_per_kwh=350,
    lifetime_years=15,
    cycles_per_year=365,
    rte=0.90,
    discount_rate=0.10
):
    """
    Levelized Cost of Storage for lithium-ion battery.
    Returns USD/MWh of energy delivered through storage.
    """
    capex_total = capacity_kwh * capex_per_kwh
    annual_throughput_kwh = capacity_kwh * cycles_per_year * rte * 0.85
    crf = (discount_rate * (1+discount_rate)**lifetime_years) / ((1+discount_rate)**lifetime_years - 1)
    annualized_capex = capex_total * crf
    fixed_om_annual = capacity_kwh / duration_hours * 7
    lcos = (annualized_capex + fixed_om_annual) / (annual_throughput_kwh / 1000)
    return lcos
```

### 8.5 Combining solar and storage

```python
def compute_firm_delivered_lcoe(
    solar_lcoe,
    storage_share,        # 0.20 for partial, 0.50 for near-baseload
    storage_duration_hours,
    storage_lcos,
    capacity_factor,
):
    """
    Combined LCOE for solar with storage firming.
    Simplified: storage cycles a fraction of solar output.
    """
    direct_share = 1 - storage_share
    effective_storage_share = storage_share * 0.90  # round-trip losses
    
    weighted_lcoe = (
        direct_share * solar_lcoe +
        effective_storage_share * (solar_lcoe + storage_lcos)
    )
    return weighted_lcoe / (direct_share + effective_storage_share)
```

This is a simplified firming approximation. Real dispatch optimization comes in v5.0 with PyPSA.

### 8.6 Citations

- IRENA 2024 Battery Storage Cost Report
- Lazard 2024 LCOE+S analysis
- BNEF Indonesia battery storage outlook

---

## 9. Confidence and Provenance Tracking

### 9.1 Why this is non-negotiable

Every numeric output should carry provenance. Without it, users can't audit numbers and can't distinguish high-confidence from estimated values.

### 9.2 Provenance fields per numeric output

For every cost field, also output:
- `<field>_source`: where it came from (e.g., "PLN Statistik 2024", "GEM tracker", "methodology default")
- `<field>_vintage`: when data reflects (e.g., "2024-Q1")
- `<field>_confidence`: high / medium / low
- `<field>_citation`: full citation reference

Example for captive cost:
```
captive_cost_usd_per_mwh: 50
captive_cost_source: "industry_estimate"
captive_cost_vintage: "2024"
captive_cost_confidence: "medium"
captive_cost_citation: "IESR 2024 captive coal economics; methodology default"
```

### 9.3 Implementation

Create a small utility module `src/utils/provenance.py`:

```python
@dataclass
class ProvenanceFlag:
    value: float
    source: str
    vintage: str
    confidence: str  # 'high' | 'medium' | 'low'
    citation: str
    
    def to_dict_with_prefix(self, prefix: str) -> dict:
        return {
            f"{prefix}_value": self.value,
            f"{prefix}_source": self.source,
            f"{prefix}_vintage": self.vintage,
            f"{prefix}_confidence": self.confidence,
            f"{prefix}_citation": self.citation,
        }
```

Use this consistently across the cost framework. Don't retrofit later.

---

## 10. Output Schema (fct_site_scorecard.csv changes)

### 10.1 New fields added (Refined — IEA-aligned column names; phase-tagged 2026-05-07)

Per the §1.5 release split, every column below is tagged `[a]` (v4.1a, ships first), `[b]` (v4.1b, ships second), or `[a→b]` (v4.1a creates, v4.1b extends additively). v4.1a's scorecard contains only `[a]` columns; v4.1b appends `[b]` columns to the existing schema without modifying any `[a]` column.

```
# Solar cost variants — IEA-aligned naming convention (§2.6)  [v4.1a]
lcoe_generation_usd_per_mwh                       # [a] IEA LCOE (base, generation only) — Refined 2026-05-07: explicit name, not bare lcoe_usd_per_mwh
full_system_lcoe_delivered_usd_per_mwh            # [a] IEA Full System LCOE (delivered, no storage)
full_system_lcoe_firm_4h_usd_per_mwh              # [a] IEA Full System LCOE (firm 4h)
full_system_lcoe_firm_8h_usd_per_mwh              # [a] IEA Full System LCOE (firm 8h)

# LCOS — IEA standard  [v4.1a]
lcos_4h_usd_per_mwh                               # [a] IEA LCOS at 4h duration
lcos_8h_usd_per_mwh                               # [a] IEA LCOS at 8h duration

# Incumbent costs (Refined — daytime/nighttime split)  [v4.1a]
incumbent_pln_bpp_usd_per_mwh                     # [a] renamed/clarified from existing bpp
incumbent_pln_marginal_daytime_usd_per_mwh        # [a] NEW (VALCOE time-of-day component)
incumbent_pln_marginal_nighttime_usd_per_mwh      # [a] NEW (VALCOE time-of-day component)
incumbent_industrial_tariff_usd_per_mwh           # [a] NEW
incumbent_captive_usd_per_mwh                     # [a] NEW (null for grid-only sites)
incumbent_captive_fuel_type                       # [a] NEW

# CBAM destination-weighted (Refined — replaces single eu_export_share)  [v4.1b]
cbam_destination_weighted_incumbent_2025_usd_per_mwh    # [b]
cbam_destination_weighted_incumbent_2030_usd_per_mwh    # [b]
cbam_destination_weighted_incumbent_2034_usd_per_mwh    # [b]
cbam_full_incumbent_2025_usd_per_mwh              # [b] 100% stress test
cbam_full_incumbent_2030_usd_per_mwh              # [b]
cbam_china_only_incumbent_2025_usd_per_mwh        # [b] 100% China stress test
cbam_china_only_incumbent_2030_usd_per_mwh        # [b]

# Hydro proximity (Refined — new)  [v4.1b]
nearest_hydro_operating_id                        # [b]
nearest_hydro_operating_km                        # [b]
nearest_hydro_operating_mw                        # [b]
nearest_hydro_pipeline_id                         # [b]
nearest_hydro_pipeline_km                         # [b]
nearest_hydro_pipeline_mw                         # [b]
nearest_hydro_pipeline_target_year                # [b]
hydro_adjacency_tier                              # [b]
hydro_transmission_feasibility                    # [b]

# Hybrid optimizer 3-way (Refined — adds hydro, IEA-aligned naming)  [v4.1b]
hybrid_solar_share                                # [b]
hybrid_wind_share                                 # [b]
hybrid_hydro_share                                # [b]
hybrid_lcoe_usd_per_mwh                           # [b] IEA Hybrid LCOE (blended generation)
hybrid_bess_hours                                 # [b]
hybrid_lcos_usd_per_mwh                           # [b] IEA Hybrid LCOS (reduced storage)
hybrid_full_system_lcoe_usd_per_mwh               # [b] IEA Hybrid Full System LCOE (blended + LCOS)
hybrid_supply_coverage_pct                        # [b]
hybrid_nighttime_coverage_pct                     # [b]
hybrid_bess_reduction_pct                         # [b]
hybrid_carbon_breakeven_usd_per_tco2              # [b]

# Site classification (joined from fct_site_classifications — see §3.1 phase split)
electricity_arrangement                           # [a]
captive_capacity_mw                               # [a]
captive_share_estimated                           # [a]
export_market_shares_json                         # [b] JSON string of per-market dict
export_market_shares_source                       # [b]
export_market_shares_confidence                   # [b]
cbam_exposed                                      # [b]

# Comparison flags
solar_below_pln_bpp                               # [a] bool
solar_below_industrial_tariff                     # [a] bool
solar_below_captive                               # [a] bool (where applicable)
firm_solar_below_captive                          # [a] bool (where applicable)
solar_below_marginal_daytime                      # [a] bool (Refined — was single solar_below_marginal)
hybrid_below_captive                              # [b] bool (NEW)

# v4.0 backwards-compatibility read aliases (Refined 2026-05-07: hard-rename strategy)  [v4.1a]
lcoe_usd_per_mwh                                  # [a] ⚠ DEPRECATED in v4.1, REMOVED in v4.2. Aliases full_system_lcoe_delivered_usd_per_mwh — keeps v4.0's delivered semantics until consumers migrate. Header carries deprecation warning.

# Provenance fields (one set per major numeric output)  [v4.1a — built once, used by both phases]
<field>_source, <field>_vintage, <field>_confidence, <field>_citation
```

### 10.2 New separate datasets

`fct_site_classifications.csv` — site classification dataset (per §3). This is published as a standalone Zenodo artifact.

`fct_site_export_market_shares.csv` (Refined — new) — per-site export market shares (long format: site_id, market_id, share, source, confidence). Joined into `fct_site_classifications` via `export_market_shares_json` aggregation.

`dim_carbon_price_by_market.csv` (Refined — new) — per-market carbon price trajectory.

### 10.3 Backwards compatibility (Refined 2026-05-07 — hard-rename strategy)

The new IEA generation-only LCOE ships under a NEW column name: `lcoe_generation_usd_per_mwh`. The bare `lcoe_usd_per_mwh` name is **not reused** — it would silently miscalibrate any v4.0 number already pasted into a stakeholder spreadsheet. Instead:

- v4.0's existing `lcoe_usd_per_mwh` (delivered LCOE semantics) **survives one release** as a deprecation alias for `full_system_lcoe_delivered_usd_per_mwh`. CSV header carries a `DEPRECATED in v4.2 — use full_system_lcoe_delivered_usd_per_mwh` warning. Consumers have one release window to migrate.
- v4.1 ships `lcoe_generation_usd_per_mwh` as the new column for IEA generation-only semantics (the column the §2.1 multi-tier table describes).
- v4.2 removes the `lcoe_usd_per_mwh` alias entirely. Reading v4.2 with v4.0-era expectations produces a missing-column error (visible failure), not a silent value drift.

Document both in CHANGELOG with the **breaking-change** flag prominent. The eng-review decision (2026-05-07) to use a hard-rename rather than a same-name semantic swap is the load-bearing rationale: investment-memo CSVs paste numbers, not column-name attribution.

The existing `bpp_usd_per_mwh` field gets renamed/clarified. Same one-release-alias approach.

The v4.1 baseline `eu_export_share` field gets deprecated in favour of `export_market_shares_json`. Compute `eu_export_share` for backwards compatibility as the sum of `direct_eu_uk_us` + `battery_supply_chain_eu_oem` shares.

---

## 11. Data Compilation Tasks

These run in parallel with code work. They cannot be accelerated by Claude Code.

### 11.1 BPP refresh from PLN Statistik 2024

**Effort:** 1 day
**Source:** web.pln.co.id, PLN Statistik 2024 annual report
**Deliverable:** Updated regional BPP values per region

### 11.2 Grid emission factor update

**Effort:** 0.5 day
**Source:** KESDM emission factors (latest available)
**Deliverable:** Updated emission factors per grid system

### 11.3 Captive site classification dataset

**Effort:** 2 days
**Sources:**
- GEM coal tracker (existing dashboard data)
- Sectoral defaults (per §3.2)
- Public disclosures from major operators
**Deliverable:** `fct_site_classifications.csv` for all 81 sites

### 11.4 Captive cost overrides

**Effort:** 1 day
**Sources:**
- Annual reports of major captive operators
- IESR sector reports
- Industry analyst estimates
**Deliverable:** `data/raw/captive_generation_overrides.csv` covering at least IMIP, IWIP, Obi, Konawe, Pupuk Kaltim, Petrokimia Gresik

### 11.5 Industrial tariff data

**Effort:** 0.5 day
**Source:** PLN tariff regulations (current)
**Deliverable:** Industrial tariff per customer class and region in `data/raw/pln_industrial_tariffs.csv`

### 11.6 Daytime vs nighttime marginal cost calibration (Refined — new)

**Effort:** 1 day
**Sources:**
- IEA SEA Energy Outlook 2024 §5 dispatch tables
- RUPTL 2025–2034 Bab IV operational reports (regional dispatch by hour)
- IRENA Indonesia renewable energy outlook
**Deliverable:** Calibrated `MARGINAL_COST_ADJUSTMENT_BY_REGION` dict with daytime/nighttime split, with confidence flagging per region

### 11.7 Hydro operating + pipeline geocoding (Refined — new)

**Effort:** 1 day
**Sources:**
- PLN PLTA/M list
- ESDM hydro resource map
- RUPTL 2025–2034 Tabel 3.2/3.3 hydro additions
**Deliverable:** `data/raw/hydro_operating.geojson` (~6 GW installed) and `data/raw/hydro_pipeline.geojson` (RUPTL adds ~12 GW over 10 years), with provenance enforced

### 11.8 OEM scope-3 commitment dataset (Refined — pulled forward from v4.5)

**Effort:** 2 days
**Sources:**
- Tesla 2023 Impact Report (battery supplier carbon commitments)
- BMW Group 2024 Sustainable Value Report
- Volkswagen 2024 Group Sustainability Report
- LG Energy Solution 2024 ESG Report
- CATL 2024 ESG Report
- Hyundai Motor Group 2024 sustainability disclosures
**Deliverable:** `data/raw/oem_scope3_commitments.csv` covering ~10 major battery/EV manufacturers, with disclosed commitment year, target carbon-intensity reduction, and implied premium for low-carbon nickel; `dim_carbon_price_by_market.csv` populated with the implied scope-3 price-per-tCO₂ for `battery_supply_chain_eu_oem` and `korea_battery` markets

### 11.9 Site export market share defaults + priority overrides (Refined — new)

**Effort:** 1.5 days
**Sources:**
- Annual reports for IMIP, IWIP, PT Vale, Harita, Trimegah, Krakatau Steel
- BPS Comtrade per HS code
- Bloomberg / Reuters market reports for nickel exports
**Deliverable:** `EXPORT_MARKET_SHARES_BY_SUBSECTOR` constants populated; `data/raw/site_export_shares_overrides.csv` covering 4–6 priority sites; remaining sites use sectoral defaults with `confidence='medium'`

### 11.10 EU export share defaults table (legacy — replaced by 11.9)

Replaced by §11.9. Original entry kept as the v4.1 baseline reference.

---

## 12. To-Do List

### 12.0 Phase routing (Refined 2026-05-07)

Per the §1.5 release split, every task below is routed to v4.1a or v4.1b. Tasks in **bold** are shared infrastructure built once in v4.1a and consumed by v4.1b.

| Task # | Title (abbrev) | Phase |
|---|---|---|
| 1 | BPP refresh | v4.1a |
| 2 | Grid emission factor update | v4.1a |
| 3 | Captive site classification dataset | v4.1a |
| 4 | Captive cost overrides | v4.1a |
| 5 | Industrial tariff schedule | v4.1a |
| 6 | Export market share defaults + overrides | **v4.1b** |
| 7 | OEM scope-3 commitment dataset | **v4.1b** |
| 8 | `src/utils/provenance.py` | **v4.1a (used by both)** |
| 9 | `src/model/cost_framework.py` (multi-tier LCOE) | v4.1a |
| 10 | `src/model/incumbent_costs.py` | v4.1a |
| 11 | `src/model/storage_lcos.py` | v4.1a |
| 12 | `src/model/cbam_destination_weighted.py` | **v4.1b** |
| 13 | Daytime/nighttime marginal cost factors | v4.1a |
| 14 | Hydro proximity matching pipeline | **v4.1b** |
| 15 | 3-way hybrid optimizer (solar × wind × hydro) | **v4.1b** |
| 16 | Scorecard schema migration | v4.1a (a-columns), v4.1b (b-columns appended) |
| 17 | `fct_site_classifications.csv` pipeline | **v4.1a (extended in v4.1b)** |
| 18 | `fct_site_export_market_shares.csv` + `dim_carbon_price_by_market.csv` | **v4.1b** |
| 19 | `build_fct_site_scorecard.py` updates | both phases — additive |
| 20 | Comparison flags | v4.1a |
| 21 | Backwards-compat aliases (lcoe rename) | v4.1a |
| 22 | Integration test | both phases — per-phase test |
| 23 | Regression test against v4.0 baseline | v4.1a (locks the IEA rename) |
| 24 | Cross-validate captive coal vs IESR/Berkeley | v4.1a |
| 25 | Cross-validate storage LCOS vs IRENA/Lazard | v4.1a |
| 26 | Cross-validate destination-weighted CBAM | **v4.1b** |
| 27 | Cross-validate hydro hybrid vs JETP Annex 2.1 | **v4.1b** |
| 28 | Spot-check 5 sites | both phases — different site mix per phase |
| 29 | Update METHODOLOGY_CONSOLIDATED.md | both phases — per-phase doc updates |
| 30 | CHANGELOG.md entry | both phases — separate entries |
| 31 | Zenodo DOI publish | both phases — separate DOIs |
| 32 | Publish `fct_site_classifications.csv` standalone | v4.1a (initial), v4.1b (re-publish with export-share columns) |

### v4.1a effort total

Tasks 1, 2, 3, 4, 5, 8, 9, 10, 11, 13, 16 (a-columns), 17 (initial), 19 (a-features), 20, 21, 22 (a-test), 23, 24, 25, 28 (a-sites), 29 (a-update), 30 (a-entry), 31 (a-DOI), 32 (a-publish) → **~6–7 focused work days**.

### v4.1b effort total

Tasks 6, 7, 12, 14, 15, 16 (b-columns), 17 (extension), 18, 19 (b-features), 22 (b-test), 26, 27, 28 (b-sites), 29 (b-update), 30 (b-entry), 31 (b-DOI), 32 (b-republish) → **~5–6 focused work days**.

Combined v4.1a + v4.1b: **~11–13 focused work days** (vs the bundled v4.1 estimate of ~9 days). The 2–4 day premium buys per-phase release independence: v4.1a's IEA rename can ship and be debugged in isolation before destination-weighted CBAM data + hydro optimizer changes layer on top.

### Day 1–2: Data foundations

| # | Task | Effort | Type |
|---|---|---|---|
| 1 | BPP refresh from PLN Statistik 2024 | 1 day | Data |
| 2 | Grid emission factor update | 0.5 day | Data |
| 3 | Compile captive site classification dataset | 1 day | Data |
| 4 | Compile captive cost overrides for major sites | 0.5 day | Data |
| 5 | Compile industrial tariff schedule | 0.5 day | Data |
| 6 | (Refined) Compile site export market share defaults + priority overrides | 1.5 days | Data |
| 7 | (Refined) Compile OEM scope-3 commitment dataset | 2 days | Data (parallel with code) |

### Day 3–4: Code framework

| # | Task | Effort | Type |
|---|---|---|---|
| 8 | Create `src/utils/provenance.py` module | 0.5 day | Code |
| 9 | Create `src/model/cost_framework.py` (multi-tier LCOE) | 1 day | Code |
| 10 | Create `src/model/incumbent_costs.py` (BPP, marginal-daytime, marginal-nighttime, industrial, captive) | 0.75 day | Code |
| 11 | Create `src/model/storage_lcos.py` | 0.5 day | Code |
| 12 | (Refined) Create `src/model/cbam_destination_weighted.py` | 0.75 day | Code |
| 13 | (Refined) Implement daytime/nighttime marginal cost adjustment factors | 0.25 day | Code |
| 14 | (Refined) Hydro proximity matching pipeline | 0.5 day | Code |
| 15 | (Refined) Extend hybrid optimizer to 3-way (solar × wind × hydro) | 0.75 day | Code |

### Day 5–6: Schema migration and integration

| # | Task | Effort | Type |
|---|---|---|---|
| 16 | Schema migration for new fields in `fct_site_scorecard.csv` (~30 fields total) | 0.75 day | Code |
| 17 | Build `fct_site_classifications.csv` pipeline | 0.5 day | Code |
| 18 | (Refined) Build `fct_site_export_market_shares.csv` + `dim_carbon_price_by_market.csv` | 0.5 day | Code |
| 19 | Update `build_fct_site_scorecard.py` to compute all new variants | 1 day | Code |
| 20 | Implement comparison flags | 0.25 day | Code |
| 21 | Backwards compatibility aliases (lcoe_usd_per_mwh, bpp_usd_per_mwh, eu_export_share) | 0.25 day | Code |
| 22 | Integration test: pipeline rebuilds successfully | 0.5 day | Test |

### Day 7: Validation and documentation

| # | Task | Effort | Type |
|---|---|---|---|
| 23 | Regression test: existing v4.0 LCOE values preserved via alias | 0.25 day | Test |
| 24 | Cross-validate captive coal defaults against IESR/Berkeley | 0.25 day | Validation |
| 25 | Cross-validate storage LCOS against IRENA/Lazard | 0.25 day | Validation |
| 26 | (Refined) Cross-validate destination-weighted CBAM against [[Powering 24-7 Industrial Loads in Indonesia]] worked example (IMIP nickel ~$35/t 2025, ~$70/t 2030) | 0.25 day | Validation |
| 27 | (Refined) Cross-validate hydro hybrid optimization against JETP Annex 2.1 site cases ($59–80/MWh, ±$5/MWh) | 0.25 day | Validation |
| 28 | Spot-check 5 representative sites manually | 0.5 day | Validation |
| 29 | Update `METHODOLOGY_CONSOLIDATED.md` with new sections | 1 day | Docs |
| 30 | Update CHANGELOG.md with v4.1 entry | 0.25 day | Docs |
| 31 | Publish v4.1 to Zenodo | 0.25 day | Docs |
| 32 | Publish `fct_site_classifications.csv` as standalone Zenodo dataset | 0.25 day | Docs |

**Total effort:** ~9 focused work days (vs baseline 5–7). Net additions from refinement: hydro proximity + 3-way optimizer (~1.25 days), destination-weighted CBAM + OEM dataset (~3 days, partially parallel data work), daytime/nighttime marginal split (~0.5 day).

---

## 13. Validation Strategy

### 13.1 Regression validation

**Critical (Refined 2026-05-07):** v4.0's `lcoe_usd_per_mwh` (delivered semantics) must be preserved as a deprecation alias for `full_system_lcoe_delivered_usd_per_mwh` for one release. Two regression checks: (1) `lcoe_usd_per_mwh` from v4.1 output ≡ v4.0's `lcoe_usd_per_mwh` within ±0.01 USD/MWh (the alias preserves v4.0 reads); (2) the new `lcoe_generation_usd_per_mwh` column is populated for all 81 sites and equals (delivered LCOE − transmission cost) within ±0.01 USD/MWh.

If divergence exceeds rounding error, investigate. Most likely cause: capacity factor or transmission cost calculation changed inadvertently.

### 13.2 Cross-validation against external benchmarks

**Captive coal cost methodology:**
- Berkeley Goldman School (2023): ~$45–55/MWh range
- IESR (2024): consistent with $35–60/MWh range
- IEA Southeast Asia: similar
- Target: methodology defaults produce values in $40–55/MWh range for typical Indonesian captive coal sites
- Pass criteria: Within ±20% of these benchmarks

**Storage LCOS:**
- IRENA 2024: $150–200/MWh for utility-scale lithium-ion
- Lazard 2024: similar range
- Target: methodology produces values in $150–220/MWh range
- Pass criteria: Within ±20%

**Destination-weighted CBAM (Refined — new):**
- [[Powering 24-7 Industrial Loads in Indonesia]] worked example: IMIP nickel effective price ~$35/t (2025), ~$70/t (2030)
- Target: dashboard's `cbam_destination_weighted_incumbent_2025_usd_per_mwh` minus base produces $30–50/t for IMIP-class nickel sites
- Pass criteria: Within ±$10/t

**Hydro hybrid optimization (Refined — new):**
- JETP Captive Power Study Annex 2.1: Sulawesi Tengah aluminium $80/MWh, Kalimantan Barat alumina $61/MWh, Kalimantan Utara nickel $59/MWh
- Target: re-run dashboard hybrid optimizer with JETP site inputs; expect all-in within ±$5/MWh
- Pass criteria: Match within ±$5/MWh

### 13.3 Spot-check validation

Pick 5 representative sites covering different arrangements:
- Krakatau Steel Cilegon (Java grid, mixed)
- Petrokimia Gresik (Java captive gas)
- IMIP Morowali (Sulawesi captive coal, high CBAM destination weighting)
- Indocement Citeureup (Java grid cement)
- KEK Sei Mangkei (Sumatra mixed, hydro-proximity-relevant)

For each, verify:
- Classification matches sectoral norms (§3.2)
- Captive cost (where applicable) is within defensible range
- Marginal cost adjustment is appropriate for region (daytime AND nighttime)
- All four solar variants computed
- All applicable incumbents computed
- Provenance fields populated
- Export market shares match override or sectoral default
- Destination-weighted CBAM scenarios produce 2025/2030/2034 trajectories
- Hybrid optimizer 3-way result populated (hydro share = 0 if no operating/pipeline hydro within reach)

### 13.4 Sanity checks (IEA-aligned column names)

- `lcoe_generation_usd_per_mwh < full_system_lcoe_delivered_usd_per_mwh < full_system_lcoe_firm_4h_usd_per_mwh < full_system_lcoe_firm_8h_usd_per_mwh` for every site (cost rises as more system effects are layered in). Note: bare `lcoe_usd_per_mwh` (the v4.0 deprecation alias) equals `full_system_lcoe_delivered_usd_per_mwh` by definition for v4.1, so the IEA generation-only check uses the explicit `lcoe_generation_usd_per_mwh` column.
- `lcos_4h_usd_per_mwh < lcos_8h_usd_per_mwh` for every site (longer storage costs more per MWh delivered)
- `incumbent_pln_marginal_daytime_usd_per_mwh >= incumbent_pln_bpp_usd_per_mwh` for every site (marginal at least equals average during peak)
- `incumbent_pln_marginal_nighttime_usd_per_mwh >= incumbent_pln_bpp_usd_per_mwh` for every site
- `cbam_full_incumbent >= cbam_destination_weighted_incumbent` for every site (full EU is the upper bound)
- `cbam_destination_weighted_incumbent_2025 < cbam_destination_weighted_incumbent_2030 < cbam_destination_weighted_incumbent_2034` (carbon trajectory rises)
- For pure_captive sites, `incumbent_captive_usd_per_mwh` is populated
- For grid_only sites, `incumbent_captive_usd_per_mwh` is null
- `hybrid_solar_share + hybrid_wind_share + hybrid_hydro_share = 1.0` (within rounding)
- `hybrid_hydro_share = 0` when `hydro_adjacency_tier = "none"`
- `hybrid_lcoe_usd_per_mwh <= hybrid_full_system_lcoe_usd_per_mwh` for every site (storage adder is non-negative)
- Sum of per-market shares in `export_market_shares_json` = 1.0 (within rounding)

---

## 14. Success Criteria

(Refined 2026-05-07: each criterion tagged with its phase per §1.5 release split. v4.1a must hit all `[a]` criteria before v4.1b branches. v4.1b additionally hits all `[b]` criteria. Criteria tagged `[a+b]` are evaluated independently per phase.)

### 14.1a Functional — v4.1a (incumbents + IEA rename)

- [ ] All 81 sites have 4 solar LCOE variants computed (generation, delivered, firm partial, firm baseload) `[a]`
- [ ] All 81 sites have applicable incumbent costs computed (BPP, marginal-daytime, marginal-nighttime, industrial tariff, captive where applicable) `[a]`
- [ ] All 81 sites have site classification populated for v4.1a fields (electricity_arrangement, captive_fuel_type) `[a]`
- [ ] All numeric outputs in v4.1a have provenance fields populated (the §9 plumbing built once and reused by v4.1b) `[a]`
- [ ] Marginal cost computed using daytime/nighttime regional adjustment factors `[a]`
- [ ] Storage LCOS computed for partial and baseload firming levels `[a]`
- [ ] Comparison flags populated correctly for v4.1a fields `[a]`
- [ ] `lcoe_generation_usd_per_mwh` populated for all 81 sites; v4.0 `lcoe_usd_per_mwh` alias preserves delivered semantics with deprecation header `[a]`

### 14.1b Functional — v4.1b (CBAM + hydro)

- [ ] All 81 sites have export_market_shares_json populated (sectoral default or site override) `[b]`
- [ ] Destination-weighted and full CBAM incumbent variants computed for all CBAM-exposed sites `[b]`
- [ ] China-only stress-test variant computed for all CBAM-exposed sites `[b]`
- [ ] Hydro proximity columns populated for all 81 sites `[b]`
- [ ] Hybrid 3-way optimizer (solar × wind × hydro) runs for all 81 sites `[b]`

### 14.2a Validation — v4.1a

- [ ] Regression test: v4.0 `lcoe_usd_per_mwh` (delivered) values reproducible via deprecation alias within ±0.01 USD/MWh `[a]`
- [ ] New `lcoe_generation_usd_per_mwh` column populated for all 81 sites and equals (delivered − transmission) within ±0.01 USD/MWh `[a]`
- [ ] Captive coal defaults validate within ±20% of IESR/Berkeley benchmarks `[a]`
- [ ] Storage LCOS validates within ±20% of IRENA/Lazard benchmarks `[a]`
- [ ] Spot-check sites for v4.1a (Krakatau Steel Cilegon, Petrokimia Gresik, IMIP Morowali, Indocement Citeureup, KEK Sei Mangkei) manually validated `[a]`
- [ ] Sanity checks pass for v4.1a column subset (LCOE ordering, LCOS monotone, marginal ≥ BPP, captive populated for pure_captive sites) `[a]`
- [ ] 81-site shift report against `tests/fixtures/scorecard_v4_0_baseline.csv` written; any per-site shift >5% on action_flag/economic_tier/delivered_cost documented in changelog `[a]`

### 14.2b Validation — v4.1b

- [ ] Destination-weighted CBAM matches [[Powering 24-7 Industrial Loads in Indonesia]] worked example (IMIP nickel ~$35/t 2025, ~$70/t 2030) within ±$10/t `[b]`
- [ ] Hybrid 3-way optimizer matches JETP Annex 2.1 cases (Sulawesi Tengah aluminium $80/MWh, Kalimantan Barat alumina $61/MWh, Kalimantan Utara nickel $59/MWh) within ±$5/MWh `[b]`
- [ ] Sanity checks pass for v4.1b column subset (cbam_full ≥ destination_weighted, 2025 < 2030 < 2034 trajectories rise, hybrid shares sum to 1.0, hydro_share = 0 when adjacency_tier = none, export_market_shares sum to 1.0) `[b]`
- [ ] 81-site shift report against the v4.1a-locked baseline written; document where v4.1b's CBAM + hydro changes shift action_flag/economic_tier `[b]`

### 14.3 Documentation `[a+b]`

- [ ] `METHODOLOGY_CONSOLIDATED.md` updated with v4.1a sections (multi-tier LCOE, multi-incumbent, marginal split, captive economics) before v4.1a ships `[a]`
- [ ] `METHODOLOGY_CONSOLIDATED.md` updated with v4.1b sections (destination-weighted CBAM, hydro hybrid, geothermal NCG) before v4.1b ships `[b]`
- [ ] CHANGELOG.md entry for v4.1a (with breaking-change flag for the IEA rename) `[a]`
- [ ] CHANGELOG.md entry for v4.1b (additive, no breaking changes vs v4.1a) `[b]`
- [ ] `fct_site_classifications.csv` published with v4.1a column documentation `[a]`
- [ ] `fct_site_classifications.csv` republished extended with v4.1b export-share columns `[b]`
- [ ] `fct_site_export_market_shares.csv` published as part of v4.1b release `[b]`
- [ ] `dim_carbon_price_by_market.csv` published as part of v4.1b release `[b]`
- [ ] Zenodo v4.1a DOI published `[a]`
- [ ] Zenodo v4.1b DOI published `[b]`

### 14.4 Data publication `[a+b]`

- [ ] `fct_site_classifications.csv` is itself a publishable research artifact with its own methodology note `[a]`
- [ ] Sources cited for every v4.1a classification decision (electricity arrangement, captive fuel type, captive cost overrides) `[a]`
- [ ] Confidence flags on every v4.1a assignment `[a]`
- [ ] Per-site export-mix data has source attribution; sectoral defaults flagged `confidence='medium'`, site overrides flagged `confidence='high'` `[b]`
- [ ] OEM scope-3 commitment dataset has source attribution per OEM (URL of public commitment, retrieval date, methodology for $/t Ni inference) `[b]`

---

## 15. Migration and Backwards Compatibility

### 15.1 Field aliases (Refined 2026-05-07 — hard-rename strategy)

Maintain these aliases for one release. The v4.0 → v4.1 IEA rename uses a **hard-rename** approach: the new IEA generation-only LCOE ships under a new column `lcoe_generation_usd_per_mwh` rather than reusing the bare `lcoe_usd_per_mwh` name with new semantics. v4.0's `lcoe_usd_per_mwh` (delivered LCOE) survives one release with a deprecation warning, then is removed in v4.2. This eliminates the silent-miscalibration risk where same-name-different-value would have broken any v4.0 number already in a stakeholder spreadsheet.

```python
# In src/model/scorecard.py
def get_legacy_v40_lcoe(scorecard_row):
    """
    v4.0 alias: returns the delivered LCOE for one-release backwards compat.

    The v4.0 column `lcoe_usd_per_mwh` (delivered LCOE = LCOE + transmission)
    is preserved in v4.1 as a deprecation alias for
    `full_system_lcoe_delivered_usd_per_mwh`. CSV header carries a
    "DEPRECATED in v4.2 — use full_system_lcoe_delivered_usd_per_mwh" warning.
    Removed entirely in v4.2.
    """
    return scorecard_row['full_system_lcoe_delivered_usd_per_mwh']

def get_legacy_v41_baseline_lcoe_generation(scorecard_row):
    """
    v4.1-baseline alias: returns generation-only LCOE.

    The v4.1-baseline name `lcoe_generation_usd_per_mwh` is preserved as the
    canonical column for IEA generation-only LCOE in the IEA-aligned schema
    (§2.6) — same column name, no rename needed.
    """
    return scorecard_row['lcoe_generation_usd_per_mwh']

def get_legacy_v41_baseline_firm_partial(scorecard_row):
    """v4.1-baseline alias: lcoe_firm_partial → full_system_lcoe_firm_4h."""
    return scorecard_row['full_system_lcoe_firm_4h_usd_per_mwh']

def get_legacy_v41_baseline_firm_baseload(scorecard_row):
    """v4.1-baseline alias: lcoe_firm_baseload → full_system_lcoe_firm_8h."""
    return scorecard_row['full_system_lcoe_firm_8h_usd_per_mwh']

def get_legacy_v41_baseline_lcos_partial(scorecard_row):
    """v4.1-baseline alias: lcos_partial_firming → lcos_4h."""
    return scorecard_row['lcos_4h_usd_per_mwh']

def get_legacy_v41_baseline_lcos_baseload(scorecard_row):
    """v4.1-baseline alias: lcos_near_baseload → lcos_8h."""
    return scorecard_row['lcos_8h_usd_per_mwh']

def get_legacy_v41_baseline_hybrid_allin(scorecard_row):
    """v4.1-baseline alias: hybrid_allin → hybrid_full_system_lcoe."""
    return scorecard_row['hybrid_full_system_lcoe_usd_per_mwh']

def get_legacy_bpp(scorecard_row):
    """Legacy field alias for v4.0 compatibility."""
    return scorecard_row['incumbent_pln_bpp_usd_per_mwh']

def get_legacy_eu_export_share(scorecard_row):
    """Legacy field alias for v4.1-baseline compatibility (Refined)."""
    market_shares = json.loads(scorecard_row['export_market_shares_json'])
    return market_shares.get('direct_eu_uk_us', 0) + market_shares.get('battery_supply_chain_eu_oem', 0)

def get_legacy_marginal(scorecard_row):
    """Legacy field alias mapping single marginal to daytime (Refined)."""
    return scorecard_row['incumbent_pln_marginal_daytime_usd_per_mwh']
```

**CSV-level deprecation alias (Refined 2026-05-07 — hard-rename strategy).** The v4.1 pipeline keeps `lcoe_usd_per_mwh` as a one-release deprecation alias pointing at the same data as `full_system_lcoe_delivered_usd_per_mwh` (i.e. v4.0's delivered-LCOE semantics, unchanged). The new IEA generation-only LCOE ships as a separate column `lcoe_generation_usd_per_mwh` — same name is NOT reused with a different meaning. The bare `lcoe_usd_per_mwh` is removed entirely in v4.2.

Mark all aliases as deprecated in the CSV header comment. Plan removal in v4.2.

**CHANGELOG entry must flag this clearly (Refined 2026-05-07):**

> ⚠ **DEPRECATION (not breaking) in v4.1, BREAKING in v4.2:** column `lcoe_usd_per_mwh` is preserved in v4.1 with its v4.0 delivered-LCOE semantics (now an alias for `full_system_lcoe_delivered_usd_per_mwh`) and is removed in v4.2. The new IEA generation-only LCOE ships under a NEW column name `lcoe_generation_usd_per_mwh` to avoid silent miscalibration of v4.0 CSVs already in stakeholder spreadsheets. Frontend/API consumers should migrate from `lcoe_usd_per_mwh` to `full_system_lcoe_delivered_usd_per_mwh` (for delivered-LCOE reads) or to `lcoe_generation_usd_per_mwh` (for IEA generation-only) by v4.2. v4.1 reads of the old column return delivered-LCOE values unchanged.

### 15.2 Frontend compatibility

The Score Drawer in v4.1 may not yet use all the new fields (those come in v4.2). For v4.1, ensure the existing UI continues to work using the legacy aliases. New fields are populated in the data layer but not yet surfaced in UI.

This way v4.1 ships safely without breaking the existing user experience. v4.2 builds the new UI on top of the now-available data.

### 15.3 API stability

Any existing API endpoints continue to work. New fields are additive, not destructive.

---

## Appendix A: Geothermal NCG handling (preventive — Refined)

Per [[Indonesia Dashboard Methodology Review]] §v4.1 gaps finding 17: when geothermal lands in the architecture menu (v4.0 fixes spec finding 2 + this spec's hydro extension), CBAM Scope 2 savings should multiply by `(grid_EF − geothermal_EF) / grid_EF`, not `(grid_EF − 0) / grid_EF`. Indonesian geothermal NCG emissions are 42–73 g/kWh (Wayang Windu 73, Kamojang 73, Ulubelu 43; default 50 for unspecified) — about half of CCGT.

**Implementation pre-emption:** the geothermal proximity dataset (v4.0 fixes spec finding 2) carries `nearest_geothermal_operating_emission_factor_g_per_kwh` per plant. In v4.1's destination-weighted CBAM logic, when scenario 6 is in play (geothermal hybrid), apply:

```python
def compute_scope2_savings_with_geothermal(
    scope2_baseline_tco2_per_t,
    re_addressable_fraction,
    geothermal_share_of_scope2,  # in the hybrid mix
    geothermal_ef_t_co2_per_mwh,
    grid_ef_t_co2_per_mwh,
):
    """
    When geothermal displaces grid generation, the saved emissions
    are NOT (scope2 × addressable) — they are (scope2 × addressable) 
    minus (geothermal_share × geothermal_ef), because geothermal isn't 
    zero-emission.
    """
    full_addressable_savings = scope2_baseline_tco2_per_t * re_addressable_fraction
    geothermal_residual = (
        scope2_baseline_tco2_per_t / grid_ef_t_co2_per_mwh
        * geothermal_share_of_scope2
        * geothermal_ef_t_co2_per_mwh
    )
    return full_addressable_savings - geothermal_residual
```

For solar/wind/hydro substitution, the residual is negligible (~5–13 gCO₂/MWh) — but still worth applying per Finding 4 in the v4.0 fixes spec.

**Effort:** ~0.25 day. Pre-emptive correction; saves a v4.4-era bug where geothermal-heavy hybrids appear cleaner than they are.

---

## Appendix B: What's NOT in v4.1 (Refined)

To prevent scope creep, these are explicitly out of scope for v4.1:

- Project finance metrics (NPV, IRR, DSCR, etc.) — v4.2
- Frontend UI for new cost framework — v4.2
- Multi-pathway analysis (toggles for financing/transmission/carbon scenarios) — v4.3
- Site-specific captive plant operational data mining (beyond priority 4–6 sites) — v4.4
- Buyer pressure / supply chain analytical layer (the **data** for OEM scope-3 lands in v4.1 §11.8 to feed destination-weighted CBAM, but the per-site buyer pressure analysis and pathway scenarios remain v4.5)
- PyPSA hourly dispatch — v5.0 (but consider single-site PoC pulled forward to v4.4 per [[Indonesia Dashboard Methodology Review]] §Adjustments needed)
- Substack post writing — pairs with v4.2 release, not v4.1

v4.1 is the foundation. Resist the urge to add features here. Ship the foundation cleanly; build features on top.

---

## Appendix C: Six-scenario coverage cross-reference (Refined — new appendix)

The wiki's six-scenario architecture menu from [[Powering 24-7 Industrial Loads in Indonesia]] maps to the refinement specs as follows. Each scenario has (a) a generation-cost computation, (b) a destination-weighted-CBAM-adjusted variant, and (c) an explicit architectural representation in the optimizer or as an incumbent reference:

| # | Scenario | Where computed | LCOE / cost columns | CBAM-adjusted (M3) | First-class scenario output | CCS retrofit overlay (v4.3 §7.5) |
|---|---|---|---|---|---|---|
| 1 | **Captive coal (BAU)** | v4.1 §4 (Captive Coal Economics) | `incumbent_captive` (subcritical/supercritical) | v4.1 §7 destination-weighted | v4.3.5 architecture menu | **1B**: captive coal + CCS retrofit (gated by `ccs_proximity_tier ∈ {A, B}`) |
| 2 | **PLN grid + green PPA** | v4.1 §6 (Marginal Cost) + §3 (classification) | `incumbent_pln_bpp`, `incumbent_industrial_tariff` | v4.1 §7 | v4.3.5 architecture menu | n/a (grid Scope 2 addressed via PPA, not CCS) |
| 3 | **Pure solar + 12hr Li-ion battery** | v4.1 §8 (Storage and Firm LCOE) | `full_system_lcoe_firm_8h_usd_per_mwh` (= LCOE + 8h × 50% LCOS) — wiki Scenario 3 sanity-check baseline. v4.0.5 Finding 1 demotes from primary signal. | v4.1 §7 | v4.3.5 architecture menu (flagged "sanity check, never primary") | n/a (zero-emission generation) |
| 4 | **Solar + flex coal + 4hr battery** | v4.0.5 Finding 1 (Supply Blend cascade with dispatchable RE) + v4.1 §4 (`incumbent_captive` cycled coal) | Composed: `full_system_lcoe_firm_4h_usd_per_mwh` + cycled `incumbent_captive` | v4.1 §7 | v4.3.5 architecture menu | **4B**: cycled-coal portion + CCS retrofit |
| 5 | **Solar + hydro + gas (JETP least-cost)** | v4.1 §6A (3-way hybrid optimizer with hydro pulled forward from §6A.8 reserved) | `hybrid_lcoe_usd_per_mwh`, `hybrid_full_system_lcoe_usd_per_mwh` (with `hybrid_hydro_share`) | v4.1 §7 | v4.3.5 architecture menu | **5B**: gas portion + CCS retrofit (Pupuk Kaltim case is the anchor) |
| 6 | **Solar + geothermal + battery** | v4.0.5 Finding 2 (geothermal proximity) + v4.1 §6A (geothermal as RESource) + Appendix A (NCG correction) | Composed via cascade + hybrid; NCG-aware Scope 2 savings | v4.1 §7 (with Appendix A NCG correction) | v4.3.5 architecture menu | n/a (geothermal NCG addressed at source per Appendix A; not via CCS) |

**Process CCS overlays (v4.3 §7.5)** apply orthogonally to the power-side scenarios above, gated by `product_type ∈ {cement, ammonia, fertilizer, steel_bfbof}` AND `ccs_proximity_tier ∈ {A, B}`:
- **P-Cement**: cement kiln post-combustion CCS retrofit (~$80–120/tCO₂)
- **P-Ammonia**: ammonia SMR + CCS, the blue H₂ overlay (~$10–30/tCO₂ — process stream is pure CO₂)
- **P-Steel-BF**: steel BF stack post-combustion CCS retrofit (~$90–130/tCO₂)

These are *overlays on existing process equipment* (not process change). Process chemistry change pathways (alt fuels, SCM, DRI-EAF, inert anodes, green H₂ as chemistry substitute) remain *out of dashboard scope* per the May 2026 scope discipline; flagged in Score Drawer with cross-reference to Mission Possible Partnership / IEA / ETC.

### Cross-cutting computations

- **Pure solar (LCOE only):** `lcoe_generation_usd_per_mwh` for any site — IEA LCOE, base technology cost.
- **Solar + transmission (Full System LCOE delivered):** `full_system_lcoe_delivered_usd_per_mwh` — IEA Full System LCOE without storage.
- **Solar + battery (Full System LCOE firm):** `full_system_lcoe_firm_4h_usd_per_mwh` and `full_system_lcoe_firm_8h_usd_per_mwh` — equivalent to wiki Scenarios 3a/3b at different firming levels.
- **Mix / hybrid:** `hybrid_lcoe_usd_per_mwh` (blended generation), `hybrid_lcos_usd_per_mwh` (reduced storage), `hybrid_full_system_lcoe_usd_per_mwh` (combined) — §6A 3-way optimizer covers the solar × wind × hydro space.
- **CBAM-adjusted any architecture:** §7 destination-weighted CBAM applied per-MWh on top of any LCOE variant — produces `cbam_adjusted_*_usd_per_mwh` for each scenario via M3 formula.
- **Carbon-breakeven price:** v4.0.5 Finding 4 (with solar lifecycle correction applied) + v4.1 — the carbon price at which solar becomes cost-competitive with each incumbent.

### Scenario availability per release

| Release | Scenarios with full computation | Scenarios as first-class menu output |
|---|---|---|
| v4.0 (existing) | 1, 2, 3 (sanity check) | None — collapsed into action flags |
| v4.0.5 | 1, 2, 3 (positioned correctly), 4 (cascade), 6 (geothermal proximity) | None — still action-flag-driven |
| v4.1 refined | 1, 2, 3, 4, 5 (hydro hybrid), 6 (with NCG correction) | None — but all six computable |
| v4.2 | (No scenario additions; project finance metrics layer) | None |
| v4.3 | (No scenario additions; pathway dimensions × scenarios) | Implicit via pathway analysis |
| **v4.3.5** | **All 6** | **All 6 — first-class architecture menu per site** |

### JETP-style analysis confirmation

The user's check ("pure solar / mix / CBAM-adjusted from the JETP synthesis") maps to:

- **Pure solar** → `lcoe_generation` (LCOE) and `lcoe_firm_*` (Full System LCOE with storage). ✓ in v4.0; refined naming in v4.1 §2.6.
- **Mix / hybrid (solar + wind + hydro)** → `hybrid_*` columns in §6A 3-way optimizer. ✓ Refined in v4.1 (hydro pulled forward).
- **CBAM-adjusted** → `cbam_destination_weighted_incumbent_*` columns from §7 M3 formula. ✓ Refined in v4.1 (destination-weighted replaces single-EU-share).
- **Pure-coal baseline (JETP comparator)** → `incumbent_captive` for sites with captive coal arrangement. ✓ in v4.1 §4.

The full JETP Annex 2.1 site cases (Sulawesi Tengah aluminium, Kalimantan Barat alumina, Kalimantan Utara nickel) are reproducible end-to-end after v4.1 refined ships — see §13.2 cross-validation criteria.

---

*Cross-references: [[Indonesia Dashboard Methodology Review]] §v4.1 gaps. Refined version supersedes baseline `v4_1_foundation_spec.md`. Refinements integrated: §2.6 (IEA terminology alignment), §3.3-§3.5 (export market shares), §6.2 (daytime/nighttime marginal), §6A (hydro hybrid), §7 (destination-weighted CBAM), Appendix A (geothermal NCG pre-emption), Appendix C (six-scenario coverage cross-reference + JETP-style analysis confirmation).*
