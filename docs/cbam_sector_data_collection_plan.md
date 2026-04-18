# CBAM Sector Data Collection Plan: Fertilizer, Petrochemical, Hydrogen

> **Status:** Planning doc. Nothing in `dim_sites` yet for fertilizer beyond the 3 residual hand-picked rows in `data/industrial_sites/priority1_sites.csv`. This plan supersedes that residual approach for fertilizer.
>
> **Scope corrections vs. prior thinking:**
> 1. Current residual CSV (`data/industrial_sites/priority1_sites.csv`) has 3 Pupuk sites: Bontang, Pusri (Palembang), Petrokimia Gresik. It is **missing Pupuk Kujang (Cikampek, W. Java)** and **Pupuk Iskandar Muda / PIM (Lhokseumawe, Aceh)** — both operating subsidiaries of Pupuk Indonesia. Root cause: hand-picking without a universe-discovery step. This plan fixes that.
> 2. The current CBAM code (`src/dash/logic/cbam.py`) already separates Scope 1 (process) from Scope 2 (electricity) correctly. The real methodology gap is narrower and more technical than originally framed — see §4.1.
> 3. Petrochemicals are **not** in CBAM Annex I. Document but do not run the full CBAM pipeline.

## 1. The Problem

**Two problems, not one.**

### 1.1 Universe completeness (the Bontang miss)

For coal/steel/cement we rely on GEM trackers. For nickel we use the CGSP tracker. Industrial rows are generated programmatically inside `build_industrial_sites.py` — reproducible, pipeline-driven, provenance-attributed.

For fertilizer, ammonia, petrochemical, and hydrogen there is no equivalent open tracker. The sector is dominated by a handful of state-holding companies, not fragmented across hundreds of plants. Everything is "known" — just not compiled as GIS-ready data with emission intensities.

The previous approach (residual CSV with 3 hand-picked fertilizer rows — Bontang, Pusri, Gresik) missed **Pupuk Kujang (Cikampek, W. Java, ~0.33 MTPA)** and **PIM (Lhokseumawe, Aceh, ~0.5 MTPA)**. Both are wholly-owned Pupuk Indonesia subsidiaries producing ammonia + urea. The miss wasn't a judgment call — no one checked the Pupuk Indonesia subsidiary list against what was in the CSV. Hand-picking without a universe-discovery gate produces gaps like this every time.

**Fix: a 4-source intersection gate before any geocoding happens.** See §3.0. This mirrors TODOS M28 methodology.

### 1.2 CBAM methodology precision (the thermal-conflation gap)

The current pipeline uses two separate constant tables (`src/assumptions.py`):

- `CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` — used for CBAM Scope 2 cost calculations
- `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` — used for RE demand sizing

These are deliberately different — the explicit comment at `src/assumptions.py:622-625` says so:

```python
# NOT the same as CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE above, which includes
# thermal energy conversion for CBAM cost calculations. Key differences:
#   cement:     0.11 here vs 0.9 in CBAM (CBAM includes kiln thermal → electricity equiv)
#   fertilizer: 1.0  here vs 10.0 in CBAM (CBAM includes gas feedstock → electricity equiv)
```

What the CBAM cost code does today (`src/dash/logic/cbam.py:145-159`):

```python
scope2 = elec_intensity * grid_ef          # thermal+electric × grid factor
total_ei = scope2 + scope1                 # Scope 1 (process) kept separate — good
metrics["savings_{year}"] = scope2 * rate  # RE savings bounded to scope2 — good
```

Scope 1 vs Scope 2 separation is correct. The issue is inside Scope 2: `elec_intensity` for cement (0.9 MWh/t) and ammonia (10 MWh/t) includes combustion-for-heat converted to electricity equivalents. `scope2 × grid_ef` then treats kiln gas and SMR feedstock as if they were grid electricity that vanishes the moment a site switches to solar.

This implicitly assumes **full thermal electrification + renewable electricity supply** — a much bigger claim than "put solar on the park." Real solar deployment addresses only the electricity-only portion (cement 0.11 vs 0.9; ammonia 1.0 vs 10).

**Fix:** Tag each sector with an `re_addressable_fraction` that bounds `savings` to what RE can actually displace today, regardless of whether the headline intensity number includes thermal. See §4.1. This applies to the **32 cement sites already in the pipeline** too — not a fertilizer-only issue.

---

## 2. Sector Overview

### 2.1 Fertilizer (CBAM-covered: fertilizers category, Annex I)

Indonesia's fertilizer industry is a state-owned monopoly. PT Pupuk Indonesia holds all major ammonia and urea production. Total: ~7 MTPA ammonia, ~9.4 MTPA urea, ~4.6 MTPA compound fertilizers.

**Ammonia vs fertilizer:** Ammonia (NH₃) is the intermediate chemical. Urea/NPK/AN are finished products synthesized from ammonia on-site. Most Pupuk complexes do both. CBAM covers both categories when exported.

**Five operating facilities (one under construction):**

| # | Subsidiary | Location | Province | Products | Ammonia capacity (MTPA) | Status |
|---|---|---|---|---|---|---|
| 1 | Pupuk Sriwidjaja (Pusri) | Palembang | South Sumatra | Urea, ammonia | ~2.0 | Operating (1959) |
| 2 | Petrokimia Gresik (PG) | Gresik | East Java | Urea, NPK, ZA, ammonia, phosphoric acid | ~0.5 | Operating (1972) |
| 3 | Pupuk Kujang (PKC) | Cikampek | West Java | Urea, NPK, ammonia | ~0.33 | Operating (1975) |
| 4 | **Pupuk Kaltim (PKT)** | **Bontang** | **East Kalimantan** | **Urea, ammonia** | **~2.74** | **Operating (1977) — largest in Indonesia** |
| 5 | Pupuk Iskandar Muda (PIM) | Lhokseumawe | Aceh | Urea, ammonia | ~0.5 | Operating (1982) |
| 6 | Pupuk Kaltim (new) | Fakfak | West Papua | Urea, ammonia | ~0.83 | Under construction (target 2028) |

**Total operating ammonia capacity: ~6.07 MTPA across 5 sites.**

Decarbonization directions (context, not data inputs): Gresik has a Pupuk Indonesia + PLN + ACWA Power green hydrogen pilot (200 MW: 120 MW Pamekasan solar + 80 MW Banyuwangi wind). PIM Lhokseumawe is exploring blue ammonia with Mitsui using depleted Arun gas field CCS. Pupuk Kaltim is exploring nuclear (Copenhagen Atomics thorium molten salt).

### 2.2 Petrochemical (NOT CBAM-covered)

EU CBAM Annex I (Regulation 2023/956) does **not** cover petrochemicals. Potential future expansion to downstream chemical products has been signaled but has no timeline. Document for completeness, flag `cbam_exposed = False` with note, but do not run the full CBAM calculation pipeline.

| # | Company | Location | Province | Products | Notes |
|---|---|---|---|---|---|
| 1 | Chandra Asri | Cilegon | Banten | Ethylene, polyethylene, polypropylene | Indonesia's largest, 860 KTA ethylene |
| 2 | TPPI | Tuban | East Java | Condensate splitting, aromatics | |
| 3 | Lotte Chemical | Merak/Cilegon | Banten | Ethylene glycol | JV with Lotte (Korea) |

**Refineries (Pertamina Balikpapan, Cilacap, Dumai, Balongan, Plaju):** large energy consumers but not CBAM-covered and unlikely to be near-term. Exclude from this phase.

### 2.3 Hydrogen (CBAM-covered: hydrogen category, Annex I)

Indonesia has no standalone merchant hydrogen production. All hydrogen is an intermediate at ammonia plants (Haber-Bosch: natural gas → H₂ → NH₃). Covering fertilizer sites implicitly covers Indonesia's hydrogen CBAM exposure today.

Future green/blue hydrogen projects (Gresik ACWA pilot, PIM Mitsui blue ammonia) should be flagged as planned facilities only when they reach FID.

---

## 3. Data Collection Plan

### Phase 0 (NEW — gate for Phase 1): Universe discovery via 4-source intersection ✅ COMPLETE 2026-04-18

**Purpose:** eliminate the Bontang-type miss. No geocoding, no pipeline runs, until the universe-discovery gate produces a validated site list.

**Status:** closed. 4-source gate run → `data/industrial_sites/fertilizer_universe_v1.csv` produced (7 candidates: 5 operating Pupuk subsidiaries confirmed, Pupuk Fakfak deferred as under-construction, Multi Nitrotama Kimia flagged as ammonium-nitrate-only / outside CBAM Annex I). Gate caught the 2 previously-missing Pupuk sites (Kujang + PIM Lhokseumawe). See `data/industrial_sites/README.md` §Fertilizer universe (M26 closed).

Run this check across four independent sources. A site appears in the final list only if it shows up in ≥2 of the 4 sources (or is confirmed by a Pupuk Indonesia / ESDM official source directly).

| Source | What it provides | Access | Use for |
|---|---|---|---|
| **State holdings** — Pupuk Indonesia corporate disclosures, annual report, subsidiary list (pupuk-indonesia.com) | Authoritative list of all subsidiary ammonia/urea plants | Public, audited | Primary authoritative list |
| **Industry associations** — APPI (Indonesia Fertilizer Producers Association) member list | Independent cross-check; includes non-state producers like Multi Nitrotama Kimia (AN for mining) | Partly public | Cross-check for non-Pupuk entities |
| **Government regulation** — ESDM gas allocation directives (Kepmen ESDM No.91 K/HK.02/MEM.M/2023 and successors), Ministry of Industry Kawasan Industri registry | Identifies which facilities receive domestic gas feedstock allocation — a reliable proxy for operating ammonia capacity | Public (esdm.go.id, kemenperin.go.id) | Validates operating status + feedstock |
| **Trade statistics** — BPS Direktori Industri + UN Comtrade EU export flows by HS code (2814 ammonia, 3102 urea, 3105 NPK) | Independent measure that exports actually occurred; sizes true CBAM exposure (exports ≠ production for subsidized domestic fertilizer) | Public | Sizing and sanity check |

**Gate output:** a CSV `data/industrial_sites/fertilizer_universe_v1.csv` with columns: `candidate_name, location, province, sources_found_in (list), confirmed (bool), notes`. Sites with `confirmed=true` proceed to Phase 1. This file is version-controlled and referenced in the residual-rows README.

**Expected output:** the 5 operating Pupuk Indonesia sites in §2.1 plus a confirmation entry for Multi Nitrotama Kimia (Cikampek — produces ammonium nitrate for mining explosives; verify whether they operate their own ammonia unit or source from Pupuk Kujang next door).

**Effort:** 0.5-1 day. This is the step that prevents the next Bontang.

### Phase 1: Fertilizer site geocoding + pipeline integration (1-2 days) ✅ COMPLETE 2026-04-18

**Status:** closed. The 2 missing Pupuk subsidiaries (Pupuk Kujang Cikampek, West Java, 1.14 Mt/yr urea; Pupuk Iskandar Muda Lhokseumawe, Aceh, 1.14 Mt/yr urea) were added to `data/industrial_sites/priority1_sites.csv` with source URLs. `dim_sites` regenerated → 81 sites total (was 79). All downstream `fct_*` tables rebuilt (`fct_lcoe` 1,422 → 1,458 rows; CBAM-exposed 66/79 → 68/81). CBAM savings use the new RE-addressable fraction bound from §4.1 (shipped same day, M30).

For each confirmed site from Phase 0:

**Step 1 — Geocode facility polygon**
- Source: satellite imagery (Google Earth / Sentinel-2 via Copernicus Open Access Hub)
- Large industrial complexes, easily identifiable (hundreds of hectares each)
- Export polygon as GeoJSON → `data/industrial_sites/fertilizer_polygons.geojson`
- ~30 min per site

**Step 2 — Production data**
- Source: Pupuk Indonesia annual report (audited, public)
- Cross-check: APPI publications
- Columns: `ammonia_capacity_mtpa`, `urea_capacity_mtpa`, `other_products`
- ~1 hour total

**Step 3 — Demand estimation**
- Use `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE["fertilizer"]` (~1.0 MWh/t), **not** the CBAM thermal-inclusive intensity — this is what sizes actual solar demand
- Cross-reference: PLN industrial connection records for Gresik / Cikampek / Bontang if available
- ~1 hour total

**Step 4 — Emission intensity (dual-tag, per §4.1)**
- `cbam_elec_intensity_mwh_per_tonne` — thermal-inclusive (~10 MWh/t for ammonia) — for CBAM Scope 2 cost calculation
- `scope1_tco2_per_tonne` — 2.3 (Indonesia-specific SMR + urea route, ICGD research) — unaddressable by RE
- `re_addressable_fraction` — **NEW field** (see §4.1) — ~0.10 for ammonia = electricity-only share of the CBAM intensity = 1.0 / 10.0
- Document the calculation: `re_addressable_fraction = SECTOR_ELECTRICITY_ONLY / CBAM_ELECTRICITY_INTENSITY`

**Step 5 — Run through existing pipeline**
- Nearest substation (PLN SIMOL 2,913 rows)
- Grid integration category (three-point proximity + line connectivity)
- Buildable solar polygon within 50 km (existing 5-layer filter)
- PVOUT, solar LCOE, wind resource, wind LCOE, hybrid optimization
- BPP for grid region, grid emission factor
- CBAM cost and savings — **using the new bounding rule from §4.1**
- Mostly automated; ~2-3 hours of manual review

**Step 6 — Add to dashboard**
- Populate `dim_sites` with `site_type = standalone`, `sector = fertilizer`, direct assignment `cbam_product_type = fertilizer` (dual-mode CBAM detection already supports this, see `src/dash/logic/cbam.py` direct method)
- Populate `dim_cbam_params` (or equivalent assumptions entry) with `re_addressable_fraction` per sector
- Review action flags, confirm `project_viable` and `economic_tier` outputs
- ~1 hour

### Phase 2: Petrochemical sites (flag only, no full pipeline)

Lower priority. Geocode Chandra Asri, TPPI, Lotte Chemical. Add to `dim_sites` with `site_type = standalone`, `sector = petrochemical`, `cbam_exposed = False`, note `"potential future CBAM scope expansion"`. Skip Scope 2 CBAM cost calculation entirely. Runs LCOE + grid analysis for completeness.

Defer until CBAM scope expansion is official.

### Phase 3: Cross-validation pass (0.5-1 day)

After Phase 1 completes, verify:

- Pupuk Kaltim Bontang ammonia capacity (2.74 MTPA) matches annual report
- Gresik process emission share aligns with ACWA pilot MOU scope (the pilot is sized for the electricity portion only — a useful external sanity check on our `re_addressable_fraction` of ~0.10)
- Multi Nitrotama Kimia status: standalone CBAM entity vs. downstream customer of Pupuk Kujang
- BPS export volumes to EU vs. domestic (CBAM exposure only scales with exports — domestic subsidized fertilizer is out of scope)

---

## 4. Methodology Notes

### 4.1 The `re_addressable_fraction` fix — precise framing ✅ SHIPPED 2026-04-18 (M30)

**Status:** closed. `CBAM_RE_ADDRESSABLE_FRACTION` dict lives in `src/assumptions.py` (cement 0.12, fertilizer 0.10, ammonia 0.10, steel_bfbof 0.80, everything else 1.0). Wired into `src/dash/logic/cbam.py::compute_cbam_trajectory` exactly as the proposed code change below. Scope 1 path untouched. 4 new tests in `tests/test_logic_cbam.py` lock the bounding behaviour. Golden-master fixture regenerated. Observable impact on dashboard: cement 2034 Scope 2 RE savings 63.36 USD/t → 7.60 USD/t; fertilizer ~90% drop; nickel/steel EAF/aluminium unchanged. See `CHANGELOG.md` → Unreleased → M30 entry and `docs/METHODOLOGY_CONSOLIDATED.md` §14.3.

**This is the single most important methodological addition in this plan. It applies to fertilizer AND the 32 cement sites already in the pipeline.**

**What the current code does correctly:**

`src/dash/logic/cbam.py` (lines 145-159) already:
- Separates Scope 1 (process) from Scope 2 (electricity)
- Bounds `savings = scope2 × rate` to the electricity portion
- Keeps Scope 1 in `total_ei` and `cost` but NOT in `savings`

So "RE savings = full CBAM cost" — the initial worry — is **not** what the code does. That part is right.

**The actual gap:**

`CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` in `src/assumptions.py` (lines 591-601) includes thermal energy converted to electricity equivalents. The comment at lines 622-625 explicitly flags this:

```python
# NOT the same as CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE above, which includes
# thermal energy conversion for CBAM cost calculations. Key differences:
#   cement:     0.11 here vs 0.9 in CBAM (CBAM includes kiln thermal → electricity equiv)
#   fertilizer: 1.0  here vs 10.0 in CBAM (CBAM includes gas feedstock → electricity equiv)
```

So when the code computes `scope2 = elec_intensity × grid_ef`, it treats the kiln gas (cement) and SMR feedstock gas (ammonia) as if they were grid electricity that disappears when a site switches to solar. That is an implicit assumption of **full thermal electrification + renewable supply**. It is a much bigger real-world claim than "switch the park to solar." Solar PV does not displace gas combustion for process heat.

**What RE actually addresses:** the electricity-only portion — roughly `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE / CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` per sector.

| Sector | CBAM intensity (MWh/t, thermal-inclusive) | True electricity-only (MWh/t) | `re_addressable_fraction` |
|---|---|---|---|
| Nickel RKEF | 37.5 | 37.5 (already electricity-dominated) | ~1.00 |
| Steel EAF | 0.45 | 0.45 | ~1.00 |
| Steel BF-BOF | 0.25 | 0.20 | ~0.80 |
| Aluminium (Hall-Héroult) | 15.0 | 15.0 (already electricity-dominated) | ~1.00 |
| Cement | 0.9 | 0.11 | **~0.12** |
| Fertilizer / Ammonia | 10.0 | 1.0 | **~0.10** |

**Code change (shipped 2026-04-18, M30):**

```python
# src/dash/logic/cbam.py — proposed adjustment
re_fraction = CBAM_RE_ADDRESSABLE_FRACTION.get(ctype, 1.0)  # NEW
scope2 = elec_intensity * grid_ef
scope2_re_addressable = scope2 * re_fraction                 # NEW: bounds RE benefit
total_ei = scope2 + scope1                                   # unchanged
metrics["savings_{year}"] = scope2_re_addressable * rate     # CHANGED: was scope2 * rate
```

Effect on dashboard numbers:
- **Nickel/steel EAF/aluminium:** no change (re_fraction ≈ 1.0)
- **Cement:** 32 sites' RE savings drop by ~88%
- **Fertilizer/ammonia:** all 5 operating Pupuk sites' RE savings drop by ~90%

Scope 1 separation already protects us from the most egregious overclaim. `re_addressable_fraction` adds a second bound inside Scope 2 to prevent implicit "we electrified the kiln and built enough solar for it" assumptions.

**Why this matters for the decarbonization story:**

- Nickel/steel EAF/aluminium: "Switch electricity to solar → CBAM costs drop to near zero." ✓
- Cement/fertilizer: "Switch electricity to solar → CBAM costs drop by ~10%. The other ~90% needs CCS, electrified kilns, or green hydrogen — separate pathway, different CAPEX, different policy ask." ✓

A dashboard that says "solar solves CBAM for cement" is wrong. The process emission fraction visibility is what makes the roadmap honest for cement and fertilizer operators.

### 4.2 Demand profile for fertilizer plants

Haber-Bosch runs continuously at high temperature/pressure. Flat 24/7 profile, similar to nickel RKEF:
- Capacity factor: ~90-92% (maintenance turnarounds 2-4 weeks/year)
- `reliability_req = 0.90`
- BESS sizing: 14h bridge-hours (default for 24/7)

### 4.3 CBAM product mapping (Annex I CN codes)

| Indonesian product | CBAM category | CN codes (indicative) |
|---|---|---|
| Ammonia (NH₃) | Fertilizers | 2814 |
| Urea | Fertilizers | 3102 10 |
| Ammonium nitrate | Fertilizers | 3102 30 |
| Ammonium sulphate (ZA) | Fertilizers | 3102 21 |
| NPK compound | Fertilizers | 3105 |
| Hydrogen (merchant) | Hydrogen | 2804 10 |

Most Indonesian fertilizer production serves the subsidized domestic market. CBAM applies only to EU exports. Size exposure using BPS export data, not production — they can differ by >5× for urea where domestic distribution dominates.

---

## 5. Expected Findings (per-site hypothesis)

**Pupuk Kaltim (Bontang, E. Kalimantan):** largest plant (2.74 MTPA). Flat terrain, likely strong solar. Remote grid — may hit `invest_transmission` or `invest_substation`. Process emissions (~90% of CBAM cost after the §4.1 fix) require CCS (Arun depleted field talks) or nuclear-powered green ammonia (Copenhagen Atomics MOU).

**Petrokimia Gresik (E. Java):** strong JAMALI grid connectivity. ACWA 200 MW pilot already underway — this is likely the site with the most near-term transition potential because the land + interconnection work is partly paid for. Expect `solar_now` or similar best-of-class action flag.

**Pusri (Palembang, S. Sumatra):** decent solar, Sumatra grid (weaker than JAMALI). Check whether Sumatra-Java interconnector shifts grid integration category.

**Pupuk Kujang (Cikampek, W. Java):** strong grid but densely populated — buildable solar area likely constrained. May flag `invest_transmission` due to land, not grid.

**PIM (Lhokseumawe, Aceh):** isolated grid region, Mitsui CCS MOU for blue ammonia. Solar resource likely good (coastal, low latitude). Grid is probably binding.

---

## 6. Timeline

| Task | Effort | Target |
|---|---|---|
| Phase 0 — 4-source intersection universe-discovery gate | 0.5-1 day | Week 1, first |
| Phase 1.1 — Geocode 5 fertilizer site polygons | 3h | Week 1 |
| Phase 1.2 — Production capacity from Pupuk annual report | 1h | Week 1 |
| Phase 1.3 — Demand + emission intensity per site | 2h | Week 1 |
| Phase 1.4 — Run existing pipeline | 3h | Week 1 |
| Phase 1.5 — Add `re_addressable_fraction` field + adjust savings calc | 2h | Week 1-2 |
| Phase 3 — APPI + ESDM + BPS cross-validation | 3h | Week 2 |
| Phase 1.6 — Dashboard integration, action flag review | 2h | Week 2 |
| Methodology doc updates (`METHODOLOGY_CONSOLIDATED.md`, `DATA_DICTIONARY.md`) | 1h | Week 2 |
| Phase 2 (petrochemical flag-only) | 2h | When CBAM scope expands |

**Total fertilizer integration: 2-3 days focused work.**

**Dependencies:**
- Phase 1 cannot start until Phase 0 gate is complete (single most important rule from this plan)
- The §4.1 `re_addressable_fraction` change also updates cement outputs — coordinate with cement-sector review so the 32 existing cement sites' numbers update in the same PR, not in two separate passes that confuse reviewers

---

## 7. Data Sources Summary

| Data need | Source | License/Access | Quality |
|---|---|---|---|
| Phase 0 — state holdings baseline | Pupuk Indonesia annual report, subsidiary list | Public, audited | High |
| Phase 0 — industry association cross-check | APPI member list | Partly public | Medium |
| Phase 0 — government regulation cross-check | ESDM gas allocation Kepmen, Ministry of Industry KI registry | Public | High |
| Phase 0 — trade statistics cross-check | BPS Direktori Industri, UN Comtrade (HS 2814/3102/3105) | Public | High |
| Facility polygons | Google Earth / Sentinel-2 | Public | High (large complexes) |
| Production capacity | Pupuk Indonesia annual report | Public, audited | High |
| CBAM thermal-inclusive intensity | IEA Ammonia Technology Roadmap, IEA Cement Roadmap | Public (exec summary) | Medium-High |
| Electricity-only intensity | IRENA 2020, worldsteel 2023, IFA 2022, IEA Cement 2018 | Public | Medium-High |
| Indonesia-specific NH₃ Scope 1 (2.3 tCO₂/t) | ICGD "Indonesia Ammonia Decarbonization" research | Public | High (country-specific) |
| EU export volumes | BPS trade data, UN Comtrade | Public | Medium (HS-level, not plant-level) |
| CBAM Annex I coverage + CN codes | EU Regulation 2023/956 Annex I | Public | High (legislated) |
| Green/blue project status | Company press releases, AEA database | Public | Medium (announcements ≠ progress) |

---

## 8. Cross-references

- **`src/assumptions.py:591-626`** — CBAM intensity + Scope 1 constants (current state; the `re_addressable_fraction` dict is the new addition from this plan)
- **`src/dash/logic/cbam.py:145-169`** — where the `scope2_re_addressable` adjustment would land
- **`src/pipeline/build_industrial_sites.py`** — where new fertilizer rows are loaded (via residual CSV path today; could be extended to a new `_load_fertilizer_rows()` that reads from a tracker-style table once Phase 0 lands)
- **`data/industrial_sites/README.md`** — will need an update describing the new `fertilizer_universe_v1.csv` provenance gate
- **TODOS.md M28** — top-down universe discovery methodology; Phase 0 of this plan is the fertilizer execution of M28
- **TODOS.md M29** — residual manual rows automation (aluminium, fertilizer) — this plan delivers the fertilizer half

---

## 9. What this plan does NOT do

- **Does not change code yet.** This is a data collection + methodology spec. Implementation is a follow-up PR.
- **Does apply the §4.1 fix to the 32 cement sites** in the same implementation PR as fertilizer. Cement RE savings drop by ~88% (e.g. 2030 savings ~$32/t → ~$4/t in the default grid scenario). This is the more accurate number. CBAM outputs are not externally circulated yet, so no user re-education is required — we ship the correct numbers from day one rather than publishing overstated cement figures and walking them back later.
- **Does not build a petrochemical CBAM pipeline.** Petrochemicals are not in Annex I. We document location + grid + solar; skip CBAM cost/savings entirely.
- **Does not cover refineries.** Not CBAM-covered, not near-term, excluded.
- **Does not resolve hydrogen as a standalone category.** Indonesia has no standalone merchant hydrogen; fertilizer sites cover it implicitly. Revisit when green/blue hydrogen projects reach FID.
