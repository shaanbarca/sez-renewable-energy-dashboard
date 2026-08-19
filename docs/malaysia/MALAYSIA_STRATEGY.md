# Malaysia Port — Commercialization Strategy

**Status:** brainstorm / not yet branched into work
**Date:** 2026-08-19
**Context:** A Malaysian renewables developer (solar farms + data centres) wants to commercialize
a Malaysia version. Government contacts are available for granular data on request.
**Target user shift:** from *DFI analyst screening a country* → *project developer deciding what to
build, what it costs, and whether it clears an investment committee.*

**Related:** [GOV_DATA_REQUEST.md](GOV_DATA_REQUEST.md) ·
[investment_decision_module_spec_v2.md](../investment_decision_module_spec_v2.md) ·
[ARCHITECTURE.md](../../ARCHITECTURE.md)

---

## 0. The one-paragraph version

The analytical core and the data contract port to Malaysia on open data alone (106 of 107 scorecard
columns are country-neutral); the presentation layer is about half country-flavoured and needs real
work — see §5 for the measured numbers. The
Indonesia-specific 30% is concentrated in four places: the site universe (KEK portal), the grid
layer (PLN substations + RUPTL), the tariff/regulatory layer (BPP, Permen ESDM, Perpres 112), and
the captive-industry trackers (nickel). Malaysia has public analogues for tariffs and a *partial*
one for the grid (TNB Nodal Points), which means the tool degrades gracefully rather than breaking.
The single highest-value thing the government contacts can unlock is **PMU-level available grid
capacity and the connection queue** — because in Malaysia, grid headroom is the binding constraint,
not solar resource. Two things must be built regardless of any data: the **project finance module**
(already spec'd, never built) and a **procurement-scheme layer** (LSS6 / CRESS / NEM / SelCo), which
is what turns a screening map into a developer's tool.

---

## 1. Why the timing is unusually good

| Signal | Why it matters to us |
|---|---|
| **LSS6 RFP is open right now** — 2,650 MW solar + 1,250 MW / 6,000 MWh BESS, RFP window Jul 27–Aug 28 2026, COD by 31 Dec 2029 | Every solar developer in Malaysia is doing site-selection math *this quarter*. Mandatory BESS pairing (~4.8h duration) is exactly what our BESS sizing module already does. |
| **CRESS** (open grid access, live since Sep 2024, opened to existing consumers Mar 2025, guidelines revised Dec 2025) | Creates a bilateral developer↔corporate market. The economics hinge on the System Access Charge — a per-MWh adder our cost taxonomy already has a slot for (T2→T3 delivered tier). |
| **Johor DC demand ≈ 3.8 GW max demand**, ~1.5× the state's *entire* current demand; T&D utilisation only ~30% nationally but heavily concentrated at Sedenak / Nusajaya | This is the core thesis: **substations and connection points are the bottleneck, not generation.** Our grid module (substation proximity, hosting capacity, utilisation, upgrade cost, transmission-link feasibility) is aimed straight at it. |
| TNB has 4 approved PMUs (630 MVA) + 9 planned (1,620 MVA) in Johor | A RUPTL-equivalent pipeline signal exists — it's just not published at the granularity the RUPTL PDF gave us. That's a government ask. |

The developer's actual question — *"where can I put 100 MW of solar, can I get it onto the grid, what
will it cost me, and does it clear 12% equity IRR under CRESS vs LSS6?"* — is a question this
codebase is about 60% of the way to answering.

---

## 2. Port surface — what the code actually says

Measured against the tree: 21.4k lines of Python across 68 modules, 847 tests, plus a React SPA.

### Layer A — ports unchanged (country-agnostic)

No Malaysia work required beyond feeding it different rows.

- `src/model/basic_model.py` — LCOE via CRF annuity, degradation, firming adders, BESS bridge-hour
  sizing, hybrid solar+wind sweep. Pure functions, no geography.
- `src/pipeline/buildability_filters.py`, `wind_buildability_filters.py` — pure raster predicates
  (slope, peat, land cover, road distance). Design decision #5 in ARCHITECTURE.md explicitly made
  these I/O-free and testable. They don't know what country they're in.
- `src/model/buildings.py`, `polygon_provenance.py` — §14 rooftop geometric classifier + the 4-tier
  provenance taxonomy. Works anywhere Google Open Buildings / Microsoft GMLBF have coverage.
- `src/model/site_types.py` — the `SiteTypeConfig` registry. Adding Malaysian site categories is
  adding dict entries, which is exactly what it was designed for.
- **The API and the data contract.** The frontend reads flat CSVs from `outputs/data/processed/`, and
  **106 of 107 scorecard columns are country-neutral** — the star-schema + precomputed-flat-table
  decision paid off. Feed it Malaysian CSVs with the same columns and the charts, table, and map
  render Malaysia.
  **Caveat:** the *components* are not as clean as the contract. 541 Indonesia-specific references sit
  across 36 of 70 frontend files (§5), a third of which are nickel/geothermal panels Malaysia deletes
  outright. Budget presentation-layer work; do not assume the UI is free.

### Layer B — global datasets, re-clip to a Malaysian bbox (cheap, days not weeks)

`scripts/download_buildability_data.py` already automates most of this.

| Dataset | Malaysia coverage | Note |
|---|---|---|
| Global Solar Atlas PVOUT | Full | Peninsular ~1,400–1,600 kWh/kWp/yr; Sabah/Sarawak similar. Narrower spread than Indonesia — resource will *not* be the differentiator. |
| Copernicus DEM GLO-30 | Full | Slope filter. Matters more than in Indonesia — Peninsular's Titiwangsa spine and Sarawak's interior are steep. |
| ESA WorldCover v200 | Full | Land cover. **Oil palm is the dominant class** — expect a large "agriculture" bucket that is *soft*-excluded and slider-overridable. This is the right behaviour: converted palm estate is a real solar land bank. |
| GFW Peatlands | Full | **High-stakes in Malaysia.** Coastal Sarawak, Sabah, and parts of Johor/Selangor/Pahang are deep peat. Keep as a HARD exclusion. |
| Google Open Buildings v3 + Microsoft GMLBF | Full | Rooftop module ports directly. |
| OSM roads | Good | Road-proximity filter. |
| WDPA protected areas | Full | Partial substitute for the forest-estate layer (see §3, B4). |
| GEM Cement / Iron & Steel / Coal trackers | Malaysia rows exist | Captive-industry modules get real rows. |

**Expected finding to plan for:** Global Wind Atlas will show Malaysia's wind resource as poor
(broadly ~2–4 m/s at 100 m, marginally better on the Peninsular east coast and parts of Sabah).
The hybrid optimiser will converge to ~100% solar almost everywhere. **Do not invest in the wind
path.** Run it once to produce the evidence, ship the near-zero result as a finding, and demote
wind in the UI. That frees the budget that Indonesia spent on `fct_lcoe_wind`, wind buildability
rasters, and nighttime-fraction tuning.

### Layer C — Indonesia-specific, needs a Malaysian analogue

This is the real work. Ordered by how hard the substitution is.

| Indonesia module | Malaysian analogue | Public? |
|---|---|---|
| PLN BPP regional cost of supply (`pdf_extract_bpp.py`) | ST/TNB published tariff schedule; RP4 base tariff + AFA replacing ICPT | ✅ **Easier than Indonesia.** Published, national, no PDF-scraping fragility. |
| Permen ESDM 7/2024 tariff ceilings | LSS6 RFP ceiling price; CRESS System Access Charge; NEM/SelCo rules | ✅ Public |
| ESDM Technology Catalogue (`dim_tech_cost`) | No direct national equivalent. Use IRENA / regional benchmarks + LSS bid history as the calibration anchor | ⚠️ Substitute; call it out in methodology |
| KEK portal → 25 SEZs + 56 industrial sites | Fragmented: MIDA industrial parks, state investment corps (Invest Johor, InvestPenang, Sarawak), Sedenak Tech Park, Kulim HTP, Samalaju, Gebeng, Pasir Gudang, JS-SEZ flagship zones | ⚠️ **Partly public, needs assembly.** No single portal. Biggest ingest effort. |
| PLN `substation.geojson` | **TNB Nodal Points** (published via SEDA) — 33 kV / 11 kV connection points | ⚠️ **Partial.** Gives locations + voltage. Does *not* give live headroom. → gov ask B1 |
| PLN RUPTL 2025–34 pipeline PDF | TNB Grid Development Plan / RP4 capex; ST *Peninsular Malaysia Electricity Supply Industry Outlook* | ⚠️ Aggregate public, PMU-level → gov ask B3 |
| Kawasan Hutan forest estate shapefile | **Permanent Reserved Forest (Hutan Simpan Kekal)** — but land and forestry are **state** matters, so there are 13 separate authorities, not one | ❌ → gov ask B4 |
| `fct_geothermal_proximity` | Essentially none in Malaysia (Tawau is negligible) | **Drop the module.** |
| CGSP nickel tracker | No nickel. Instead: **aluminium (Press Metal, Samalaju/Bintulu — hydro-powered, huge)**, steel, cement, oleochemicals/palm downstream, and **E&E/semiconductor (Penang, Kulim)** | Rebuild the sector list |
| `fct_captive_coal` (GEM proximity) | Little captive coal; the analogue is **captive gas cogeneration** at industrial parks | Reframe, low priority |
| Perpres 112 coal-retirement classification | NETR coal phase-out trajectory | Low priority — drop for v1 |

**Note on CBAM:** it survives the port and arguably gets *stronger*. Malaysia exports aluminium and
steel to the EU, and Press Metal is one of the largest CBAM-exposed aluminium assets in the region.
The `CBAM_RE_ADDRESSABLE_FRACTION` machinery transfers directly.

**Note on Sarawak:** Sarawak is a separate electricity jurisdiction (Sarawak Energy / its own
regulator, not ST / not TNB / not Single Buyer), and it is hydro-dominant. It needs its own grid
region and arguably its own `CountryConfig`-style sub-entry. Do not silently fold it into a
"Malaysia" average — it will produce wrong answers, and Sarawak is precisely where an aluminium-and-
data-centre "green energy hub" pitch lives.

### Layer D — genuinely new build (see §4)

Project finance module, procurement-scheme layer, LSS6-compliant BESS mode, data-centre load module.

---

## 3. What is blocked, and what it costs us

The user-facing question: *what can we build now, and what needs the government contact?*

**Buildable today with zero government data: M1 and M2 in full, and most of M3.** The tool would
already produce a defensible national screening map with solar resource, buildability, ground-mount
and rooftop MWp, LCOE, and indicative project economics.

Blocked items, ranked by damage-if-missing:

| # | Blocked data | What breaks without it | Fallback we already have | Damage |
|---|---|---|---|---|
| **B1** | **PMU/substation available capacity (MVA headroom), per node** | The headline claim. Without it we show *proximity to a substation*, not *whether you can actually connect*. In Johor this is the entire question. | `SUBSTATION_HOSTING_CAPACITY_PROXY_MVA` + `HOSTING_CAPACITY_AVAILABILITY_PCT` (0.30) — a proxy we already ship for Indonesia | 🔴 **Critical** |
| **B2** | **Grid connection queue / applications already lodged per PMU** | Headroom that is nominally free may already be spoken for. Without it we will overstate capacity, and a developer will catch that in the first meeting. | None. Must be disclaimed. | 🔴 **Critical** |
| **B3** | TNB Grid Development Plan at PMU granularity + energisation dates | Loses the RUPTL-equivalent forward signal — "wait 18 months and this node opens up" | Aggregate RP4 capex, state-level | 🟠 High |
| **B4** | State-level Permanent Reserved Forest boundaries + land status / alienation (13 states) | Buildability filter's HARD exclusion is weaker; land tenure is unanswered | WDPA protected areas + ESA WorldCover forest class as a soft proxy | 🟠 High |
| **B5** | Industrial park fence-line polygons | Site areas fall back to a radius buffer | **Already solved** — 2 km centroid buffer + ⚠ low-trust badge + 4-tier provenance taxonomy (v4.0.5) | 🟡 Medium — degrades gracefully |
| **B6** | LSS6/CRESS awarded prices + applicant pipeline | Scheme comparison uses ceiling prices rather than clearing prices | Public ceiling price; LSS1–5 historical bids | 🟡 Medium |
| **B7** | Water availability / allocation by district (for DC siting) | DC module can't flag the water constraint, which is a real Johor blocker | Qualitative flag only | 🟡 Medium |

**The strategic read on B1/B2:** these two are *the product*. Everything else in the tool is
reproducible by a competent consultant with open data in a few weeks. Privileged, current,
node-level grid headroom is not. If the government relationship yields exactly one thing, it should
be B1+B2. That also implies the commercial moat is a **data relationship**, not the code — which
should shape how the deal with the developer is structured.

**Corollary — build a private data path before ingesting anything sensitive.** Government data may
arrive under conditions that forbid publishing it in a public MIT repo. Add a gitignored
`data/private/` with a separate ingest step and a `data_confidentiality` provenance flag, so the
public repo continues to build from public sources and the private layer only enriches a private
deployment. Doing this *before* the first dataset arrives avoids an unpickable git-history problem.

---

## 4. Build plan — three milestones to the developer meeting

Sequenced so that each milestone is independently demoable, and so that nothing waits on government data.

### M1 — "Malaysia skeleton" (~2–3 weeks)

Goal: the existing dashboard, rendering Malaysia, off open data only.

1. **Resolve the fork / monorepo / shared-core decision (§5) before writing any Malaysia code** — and
   with it the proprietary-or-open question in §6.1, which determines the answer.
2. Re-clip Layer B rasters to a Malaysia bbox; run `download_buildability_data.py` for MY tiles.
3. Assemble the site universe: 40–60 industrial parks / tech parks / DC clusters across Peninsular,
   Sabah, Sarawak. Start with the ones that matter commercially (Sedenak, Nusajaya, Kulim HTP,
   Pasir Gudang, Gebeng, Samalaju, Bintulu, Penang/Batu Kawan) rather than chasing completeness.
4. Ingest TNB Nodal Points as the substation layer; wire `fct_substation_proximity`.
5. Tariff layer from published ST/TNB RP4 schedule (replaces BPP).
6. Run the pipeline. Produce solar resource, buildability, ground-mount + rooftop MWp, LCOE, scorecard.
7. Run wind once, document the near-zero result, demote it.
8. Drop geothermal; stub Perpres-112 and captive-coal modules.

**Demo state:** "Here is every industrial park in Malaysia ranked by solar competitiveness, with
buildable area and cost, on open data."

### M2 — "Project module" (~2 weeks) ← *the thing that was never built*

`docs/investment_decision_module_spec_v2.md` already specifies this in full (781 lines, Tier 1/2/3,
with framing guardrails and a validation strategy). It is **country-agnostic**, so building it for
Malaysia also upgrades Indonesia. Build Tier 1 + Tier 2:

- Tier 1 → `src/model/project_finance.py`: annual cash-flow stream, NPV, project IRR, equity IRR,
  profitability index, simple + discounted payback.
- Tier 2 → debt amortisation schedule, year-by-year DSCR, min/avg DSCR, LLCR, DER.
- Tier 3 (tornado sensitivity, project-vs-corporate finance toggle, scenario comparison) is
  explicitly optional — **defer it until after the developer meeting**, and let them tell you which
  of the three they actually want.

Two Malaysia-specific parameter changes to the spec's defaults: corporate tax rate (spec hardcodes
Indonesia's 22%) and the incentive regime (Malaysia's Green Investment Tax Allowance / GITA and
Green Income Tax Exemption / GITE, rather than KEK tax holidays).

**Keep the spec's framing guardrails.** §9 ("indicative" everywhere, mandatory disclaimer, no fake
precision, ranges over points) matters *more* in a commercial setting, not less. The target reaction
from a project-finance professional — *"good screening framework, I'd still build my own model"* —
is exactly the right reaction to engineer for in a developer meeting.

### M3 — "Malaysia commercial layer" (~1–2 weeks)

This is what makes it *their* tool rather than a ported academic one.

1. **Procurement-scheme selector.** LSS6 / CRESS / NEM 3.0 / SelCo / GETS / behind-the-meter captive.
   Each is a config entry carrying: eligibility, offtake counterparty, price basis (ceiling/bid vs
   bilateral vs displaced tariff), grid charges (CRESS System Access Charge), BESS requirement,
   export limits, tenure. Then run the project module *per scheme* and rank them. **A developer's
   first question is "which scheme, and what does it pay?" — no other tool answers this on a map.**
2. **LSS6-compliant BESS mode.** LSS6 mandates storage at roughly 4.8 h duration (1,250 MW /
   6,000 MWh against 2,650 MW solar). The BESS module currently sizes on a bridge-hour model;
   add a scheme-driven sizing mode so LSS6 bids are costed to spec.
3. **Data-centre load module.** Add DC as a site type: IT load MW, PUE, and — the interesting part —
   a **24/7 matching score**, since solar at ~15–17% CF against a flat 24/7 load is a genuinely hard
   problem and the honest answer (how much of a DC's load solar+BESS can actually serve, and what
   the last 20% costs) is a differentiated, defensible output. Flag water as a qualitative
   constraint pending B7.

**Then meet the developers** — with M1–M3 live, and §3's blocked table as the explicit ask.

---

## 5. The one architectural decision to make first — fork, monorepo, or shared core

**Revised 2026-08-19 after measuring the actual coupling.** An earlier draft of this section said
"don't fork, go multi-country in one repo, ~3–5 days." That was directionally reasonable but rested
on two claims that measurement did not support: that the frontend ports essentially free, and that
the model core is country-agnostic. Neither is true as stated. The numbers below are the real ones.

### Measured coupling

| Measurement | Value | Reading |
|---|---|---|
| Indonesia-specific terms in frontend (`KEK`, `RUPTL`, `BPP`, `PLN`, `Perpres`, `ESDM`, `Kawasan`, nickel, geothermal) | **541 hits across 36 of 70 files** | The presentation layer is ~half country-flavoured. Not free. |
| Of those, `nickel` + `geothermal` | **100 hits** | Malaysia **deletes** these rather than sharing them. Not portable *or* shared — just gone. |
| Scorecard columns that are Indonesia-named | **1 of 107** | ✅ **The data contract is genuinely clean.** This is the strongest portability asset. |
| Indonesia refs inside `src/model/basic_model.py` | **131** | ⚠️ Not logic coupling — *naming* coupling. Parameters are literally `grid_region_bpp_usd_mwh`, `demand_kek_mwh`, `RUPTL_PRE2030_END`. The math is universal; the vocabulary is Indonesian regulatory jargon. |
| Python that is Indonesia-only and deletable | **~2,600 LOC** (RUPTL extractors, nickel, Perpres 112, geothermal) | A fork drops these on day one. |
| Candidate country-agnostic core | **~3,500 LOC** (`src/model/` + buildability filters + geo utils) | Small, high-value, high-risk. |
| **Commits touching the model core, last 30** | **19** | 🔴 **The decisive number.** At that churn rate a forked model diverges within weeks. |

### The three options

| | Pure fork | Multi-country monorepo | **Shared core, forked apps** |
|---|---|---|---|
| Time to first Malaysia demo | Fastest | Slowest (refactor first) | Fast (core extraction can lag) |
| Model fixes propagate | ❌ Manual, will silently stop | ✅ Automatic | ✅ Automatic (versioned package) |
| Malaysia can be proprietary / hold NDA data | ✅ Clean | ❌ Awkward — public repo, Commons Clause | ✅ Clean |
| UX free to diverge for a different user | ✅ | ⚠️ Shared-abstraction tax on a layer that *should* differ | ✅ |
| Indonesia keeps its DOI/citation integrity | ✅ | ⚠️ Churned by commercial work | ✅ |
| Third country | ❌ Expensive | ✅ Cheap | ✅ Cheap |
| Malaysia inherits Indonesian vocabulary | ❌ Forever (`bpp`, `kek` mean nothing to a Malaysian developer) | Fixed by the rename | Fixed by the rename |

### Recommendation

**Split by layer, not by country.** Extract the ~3,500-line country-agnostic core as a versioned
package; let Indonesia and Malaysia be separate applications on top of it.

This captures the one thing that genuinely must stay single-sourced — the model, given 19/30 commit
churn and a module whose own docstring warns that unit bugs have historically produced 10–100×
errors — while letting everything that *should* diverge actually diverge.

The core extraction requires a rename pass to strip Indonesian regulatory vocabulary from the model
API (`grid_region_bpp_usd_mwh` → `grid_supply_cost_usd_mwh`, `demand_kek_mwh` → `demand_site_mwh`,
`KEK_TO_SUBSTATION_THRESHOLD_KM` → `SITE_TO_SUBSTATION_THRESHOLD_KM`). There is precedent and
appetite for exactly this: the v4.1 plan already locked a hard-rename of
`lcoe_usd_per_mwh` → `lcoe_generation_usd_per_mwh`, and 847 tests make it safe.

**Sequencing that avoids blocking the demo:** fork the application first and start Malaysia
immediately; extract the core in parallel, before the two model copies have diverged enough to make
reconciliation painful. The deadline for extraction is roughly the first Malaysia-driven model
change — after that, every day costs more.

### The decisive question

The choice actually hinges on one input that is not an engineering question: **does the Malaysia
version need to be proprietary?** If it must hold NDA'd government data (§3, B1/B2) or be sold as a
commercial product, separation is close to mandatory and pure-monorepo is off the table. If it stays
open and the developer relationship is a services engagement, the monorepo becomes viable again.
Resolve this before branching — see §6.1.

## 6. Non-code items that are genuinely "next"

These are cheap to overlook and expensive to fix late.

1. **Licensing.** The repo is MIT + **Commons Clause**, which specifically restricts *selling the
   software*. Under it the developer may freely use and modify the tool but may not resell it. If
   commercialization means the developer sells access, or a joint entity does, that needs an explicit
   commercial licence — and since you hold the copyright (`CITATION.cff`, Zenodo DOI
   10.5281/zenodo.19570542), you can grant one. Decide the structure *before* the meeting: licence
   fee, equity, services engagement, or joint venture. It changes what you should demo.
2. **Data confidentiality.** Per §3, stand up `data/private/` before any government dataset arrives.
3. **Attribution of the Indonesia work.** The Zenodo DOI and 847-test provenance are credibility
   assets in the meeting — this is a validated tool being ported, not a prototype. Lead with that.
4. **What to actually ask the developer for.** Their real value is calibration data you cannot get
   anywhere else: actual EPC costs per MWp in Malaysia, actual land lease rates, actual grid
   connection charges paid, actual timelines from application to energisation. That is worth more to
   the model than any public dataset, and it costs them nothing to share. Put it on the agenda.

---

## 7. Open questions to resolve before branching

1. **Scope:** Peninsular only for v1, or Peninsular + Sabah + Sarawak? Sarawak is a separate
   jurisdiction and roughly doubles the grid-layer work — but it is also where the aluminium and
   green-DC story lives. *Leaning: Peninsular + Sarawak, defer Sabah.*
2. **Site universe:** industrial parks (mirrors the Indonesia KEK framing) or **land parcels**
   (what a solar developer actually optimises over)? The Indonesia tool assumes a fixed site
   universe; a solar farm developer wants "anywhere with grid access and flat non-peat land."
   That is a real conceptual difference and may be the biggest hidden scope item in the whole port.
3. **Who is the user in the room** — the developer's origination team (wants land + grid + scheme
   economics) or their investment committee (wants DSCR and IRR)? M2 and M3 serve different people.
4. Does the developer want this hosted/white-labelled, or as an internal tool they run?

