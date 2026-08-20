# How a Malaysian Project Developer Actually Decides — and Where a Tool Fits

**Date:** 2026-08-19
**Purpose:** Work the problem from the developer's workflow down, rather than from the existing
dashboard up. What are the real decision gates, what data does each need, how critical is each, and
what does the RM6–10M consultant spend actually buy?

**Related:** [MALAYSIA_STRATEGY.md](MALAYSIA_STRATEGY.md) · [GOV_DATA_REQUEST.md](GOV_DATA_REQUEST.md)

> **Calibration note.** Regulatory steps, thresholds, and the land-conversion figures below are
> sourced (see §7). **Consultant fee ranges are indicative market practice, not verified Malaysian
> quotes** — they are the least reliable numbers here and should be checked directly with the
> developer. Doing so is also a good meeting question.

---

## 1. The headline reframe

**The RM6–10M per site is almost certainly not "a feasibility study."** It is the full
development-phase consultant stack for a large project — most plausibly a data centre or a large
industrial/mixed development, not a standalone solar farm — spread across a dozen specialist firms
(§5). For a project with capex in the billions of ringgit, that is well under 1% of capex, which is
normal.

Two consequences, and they set the entire product strategy:

1. **A dashboard cannot displace that spend.** You cannot replace a geotechnical borehole, a title
   search, an EIA, or a TNB Connection Assessment Study with a map.
2. **But that spend is committed to *one site, after it has already been chosen*.** The waste isn't
   the RM6–10M — it is choosing the wrong site to spend it on, and burning months of business-
   development time on candidates that were always going to die at the grid gate or the land gate.

**So the product's job is triage, not replacement:** kill non-starters before anyone commissions a
study, rank the survivors so origination effort goes to the right places, and produce a shortlist
defensible enough to get an internal investment committee to release the study budget.

That is a *smaller* claim than "we replace consultants" and a much more defensible one — and it is
the claim that survives contact with a developer who knows what those consultants actually do.

---

## 2. The gates — utility-scale solar

A developer does not run these strictly in sequence; the good ones run 0–3 in parallel because each
can kill the project. But the *order of criticality* is stable, and it is not the order most
tools assume.

### Gate 0 — Route to market (offtake) 🔴 **Existential**

*Before anything else: who buys the power, under what scheme?*

| Route | Counterparty | Price basis | Notes |
|---|---|---|---|
| **LSS6** | Single Buyer / TNB | Competitive bid vs ceiling | 2,650 MW + mandatory BESS (1,250 MW / 6,000 MWh ≈ 4.8 h). RFP window Jul–Aug 2026, COD by 31 Dec 2029. |
| **CRESS** | Corporate, bilateral | Negotiated, minus System Access Charge | Open grid access. Live since Sep 2024; opened to existing consumers Mar 2025. |
| **NEM / SelCo / Solar ATAP** | Self, behind meter | Displaced retail tariff | Rooftop / self-consumption scale. |
| **Captive / behind-the-fence** | Co-located industrial or DC load | Bilateral | The solar-farm-plus-data-centre play. |
| **Export (ENEGEM)** | Cross-border, Singapore | Auction | Narrow, but high-value. |

**Why it ranks first:** the scheme determines required project size, tariff, whether you need an
offtaker signed *before* you have a site, the grid charges you pay, and whether BESS is mandatory.
Two developers looking at the same field will reach opposite conclusions depending on this answer.

**Data needed:** scheme rules, ceiling/clearing prices, quota remaining, CRESS System Access Charge,
BESS requirements, bid deadlines.
**Availability:** ✅ Mostly public — but scattered across ST, SEDA, PETRA and TNB documents, and it
changes often (CRESS guidelines were revised Dec 2025).

### Gate 1 — Land control 🔴 **Existential, and the slow killer**

Site identification → willing landowner → option or LOI → title due diligence → land use.

**Title due diligence** asks: what is the land *category of use* (agriculture / building /
industry)? What express conditions and restrictions-in-interest sit on the title? Is it Malay
Reserve? Leasehold, and how many years remain? Any encumbrances or caveats?

**Then land use conversion.** Agricultural → industrial conversion runs roughly **RM5k–50k per acre
and 6–18 months**, and varies by state because **land is a state matter, not federal**. Notably,
**Johor issues Special Permits letting agricultural land host solar for up to 25 years without full
conversion** — a materially different economics and timeline story from a state that requires
conversion. Kedah and Perak are reported to have the most streamlined processes, having handled
large LSS portfolios.

**Why it ranks second:** projects rarely die loudly here — they die slowly, 14 months in.

**Data needed:** cadastral lot boundaries, title/land status, category of land use, ownership,
lease/sale comparables, state-specific conversion rules and premiums.
**Availability:** ❌ **Hardest to get.** 13 state land offices, largely not open data. Individual
title searches are per-lot and paid.

### Gate 2 — Grid connection 🔴 **The binding constraint in Malaysia today**

Nearest intake substation (PMU) → available capacity → distance and voltage → interconnection cost
(gentie line, bay extension, substation works) → **TNB Connection Assessment Study (CAS)** or
Connection Confirmation Check (CCC) under TNB's Electricity Supply Application Handbook (ESAH) →
queue position → energisation date.

**Why it ranks this high:** national transmission and distribution utilisation is only ~30%, but
demand is heavily concentrated around industrial and data-centre clusters — so grid access is
locally scarce even where it is nationally abundant. In Johor, data-centre max demand has reached
~3.8 GW, about 1.5× the state's entire current demand, and substations have become the bottleneck
rather than generation.

**Data needed:** substation locations and voltages, **available capacity (MVA)**, **connection queue**,
planned grid reinforcement and dates, interconnection cost rules.
**Availability:** ⚠️ Locations partly public (TNB Nodal Points via SEDA). **Headroom and queue are
not** — these are exactly items B1 and B2 in the government data request, and they are the single
highest-value thing the government relationship can unlock.

### Gate 3 — Physical site screening 🟠 **High — mostly cost, sometimes binary**

Slope and topography · **flood risk** (monsoon; JPS drainage requirements) · **soil and geotech**
(peat is the big one — piling costs escalate sharply) · existing land cover (oil palm implies
clearing cost, and sometimes replanting or compensation obligations) · road access · shading and
orientation · proximity to the interconnection point.

Most of these change the cost rather than kill the project. **Peat and flood can be binary.**

**Data needed:** DEM/slope, flood hazard maps, peat maps, land cover, road network.
**Availability:** ✅ Largely open globally (Copernicus DEM, ESA WorldCover, GFW peatlands, OSM).
⚠️ Malaysian flood hazard mapping at parcel resolution is the weak point.

### Gate 4 — Energy yield 🟡 **Low for site choice, high for financing**

Early stage uses satellite resource data (Global Solar Atlas, Solargis, Meteonorm) for a P50
estimate. Bankable stage needs a **long-term corrected P50 *plus* P90 with a formal uncertainty
analysis**.

**This distinction matters more than it looks.** Lenders generally treat P50 as too aggressive for
debt sizing and size debt on **P90**, typically requiring **DSCR of 1.20–1.35**. A P50-only report
will not close financing in most utility-scale markets.

**Why it ranks low for *site selection* in Malaysia specifically:** the country's solar resource is
comparatively uniform. Resource will rarely be the deciding variable between two Malaysian sites —
which is precisely why a tool that leads with a resource map is answering a question nobody is
stuck on.

### Gate 5 — Permitting and environment 🟠 **High — drives the schedule**

Planning permission (*kebenaran merancang*) from the local authority (PBT) · development order ·
earthworks permit · JPS drainage/stormwater approval · DOE environmental clearance · Energy
Commission (ST) generation licence.

**On EIA:** solar farms are **not explicitly listed as a prescribed activity** under the
Environmental Quality (Prescribed Activities) (EIA) Order 2015 — but they have been treated as
falling under the *industrial estate development* and *power generation and transmission*
categories. That ambiguity is itself a cost: it creates uncertainty about whether a project needs a
First Schedule (state DOE) or Second Schedule (DOE HQ) review, which is a months-level schedule
difference. Proponents must appoint registered consultants and engage DOE early.

### Gate 6 — Financial close 🔴 **The actual go/no-go**

CAPEX build-up · EPC pricing · O&M · tariff/PPA terms · debt sizing on **P90 DSCR 1.20–1.35** ·
equity IRR vs hurdle · tax incentives (GITA / GITE) · currency and tenor.

---

## 3. The gates — data centre (what differs)

The DC developer's constraint set is different enough to be worth stating separately.

| Gate | Difference from solar |
|---|---|
| **Power** 🔴 | Inverted: it is a *demand* problem. Can I secure 100–300 MW, and **when**? TNB's Green Lane Pathway (launched 2023) exists specifically to compress this. Phased grid build matters — in Johor, 4 approved PMUs (630 MVA) plus 9 planned (1,620 MVA). |
| **Water** 🔴 | Cooling water is a genuine co-equal constraint and a live political issue. State water operator (e.g. Ranhill SAJ in Johor). Allocation, not just availability. |
| **Connectivity** 🔴 | Subsea cable landing stations, terrestrial fibre routes, latency to Singapore. Binary for some tenants. |
| **Land** 🟠 | Larger parcels, industrial zoning strongly preferred (conversion delay is often unacceptable), and **geotech is critical** — heavy floor loading makes peat and soft soil disqualifying rather than merely expensive. |
| **Regulatory** 🟠 | National Data Centre framework, MIDA incentives, and increasingly sustainability conditions (efficiency/PUE expectations). |
| **Offtake** | Inverted again: **the DC *is* the offtaker.** This is exactly where a developer doing both solar and DC has an edge — and where the interesting modelling problem lives (§6). |

---

## 4. What the developer is actually optimising

Stated as they would state it, in priority order:

1. **Can I get power, and when?** (solar: grid export capacity · DC: grid supply + water + fibre)
2. **Can I control the land, at what price, and how long until I can legally build on it?**
3. **What's my route to market and what does it pay?**
4. **What's all-in cost per MWp, and does it clear my hurdle IRR?**
5. **What kills me?** — flood, peat, EIA classification, community objection, title defect.

Note that **solar resource is not on this list.** In Indonesia, resource spread across an archipelago
was a real differentiator. In Malaysia it largely isn't. A Malaysian product that leads with a
resource map is leading with the answer to a question the developer has already stopped asking.

---

## 5. What the RM6–10M actually buys

For a large development, the consultant stack typically includes:

| Workstream | Typical provider |
|---|---|
| Master planning / concept design | Architect + planner |
| Topographic and cadastral survey | Licensed surveyor |
| **Geotechnical investigation** (boreholes) | Geotech firm |
| **EIA** (and social impact where required) | DOE-registered consultant |
| Traffic impact assessment | Traffic consultant |
| Drainage, stormwater, flood study | Civil / JPS-compliant consultant |
| **Utility feasibility** — power (TNB CAS), water, telco | Engineering consultant |
| Legal due diligence on title | Law firm |
| Financial modelling / transaction advisory | Financial advisor |
| **Owner's engineer / technical advisor** | Through construction |

A useful sizing sanity-check to run with the developer: for a **standalone utility-scale solar farm**,
this stack should land far below RM6–10M — indicatively a few hundred thousand to low millions of
ringgit. If a solar site is genuinely costing RM6–10M, the money is going somewhere specific
(unusual geotech, contested land, a bespoke grid solution) and **that** is the interesting question.
If the figure came from a *property* developer, it most likely describes a DC or mixed development,
where it is entirely normal.

**Study tiers, and where the product sits:**

| Tier | Duration | Indicative cost | Who reads it | Tool fit |
|---|---|---|---|---|
| **0. Desktop screening / triage** | Days | Internal, or low tens of RM'000s | Origination / BD | ✅ **This is the product** |
| 1. Prefeasibility | 2–6 weeks | Low hundreds of RM'000s | Investment committee | ⚠️ Tool feeds it |
| 2. Full feasibility | 4–12 weeks | Hundreds of RM'000s–low millions | IC + prospective lenders | ❌ Site-specific |
| 3. Bankable FS / technical due diligence | 8–16 weeks | RM1M+ | **Lenders** | ❌ Requires P90, geotech, CAS |
| 4. Owner's engineer | Construction | Ongoing | Sponsor | ❌ |

---

## 6. What this means for the product

### The honest boundary

State plainly what the tool does not do: geotech, parcel-level flood modelling, title search, EIA,
TNB's actual Connection Assessment Study, or a bankable P90. Saying this out loud is what makes the
rest credible to someone who has paid for all of them.

### Where it wins

1. **Grid-first, not resource-first.** Reorganise the product around Gate 2. "Which connection
   points still have headroom, how much, and what does it cost to reach them" is the question
   Malaysian developers are actually stuck on, and it happens to be what this codebase already
   models better than anything else it does.
2. **Scheme comparison (Gate 0).** Run the project economics per route-to-market — LSS6 vs CRESS vs
   captive — and rank them. No mapping tool answers this, and it is the developer's first question.
3. **Kill-list before spend.** An explicit disqualification pass — no grid headroom, deep peat, flood
   zone, protected forest, wrong land category — with the reason stated. Saving one wasted
   preliminary study pays for the tool many times over, and that is an easy number to put in front
   of a developer.
4. **The 24/7 matching problem (solar + DC together).** Solar at ~15–17% capacity factor against a
   flat 24/7 DC load is a genuinely hard problem. Quantifying how much of a DC's load solar+BESS can
   actually serve, and what the last 20% costs, is differentiated, defensible, and directly relevant
   to a developer doing both.
5. **Feed the study, don't replace it.** Output a scoping brief: here is the shortlist, here is what
   to investigate at each site, here is what we could not resolve from desk data. That is a natural
   handoff into the RM6–10M spend rather than a doomed attempt to compete with it.

### Two model implications worth noting now

- **P50 vs P90.** The current model is deterministic — effectively a P50-flavoured point estimate.
  Lenders size debt on P90 at DSCR 1.20–1.35. Adding an uncertainty band would move the output
  meaningfully closer to how the money is actually decided, and it composes naturally with the
  project finance module (§M2 in the strategy doc).
- **Sites vs parcels.** The Indonesia tool screens a *fixed universe of known sites*. A solar
  developer screens *land* — "anywhere with grid access and buildable ground." Gate 1 above is the
  reason this matters: land control is the thing they are actually searching for. This remains the
  biggest unresolved scope question in the whole port.

---

## 7. Sources

- Land conversion cost/timeline, Johor Special Permit, state variation — [Trexon: agrivoltaics / solar farming on agricultural land](https://trexon.my/blog/agrivoltaics-solar-farming-malaysia-2026-agriculture); [Planning Malaysia: solar farm approval considerations in Johor](https://www.planningmalaysia.org/index.php/pmj/article/view/1034); [FIG: land administration of solar farming](https://www.fig.net/resources/proceedings/fig_proceedings/fig2020/papers/ts08f/TS08F_rohani_sahid_et_al_10331.pdf)
- LSS6 structure and timeline — [pv magazine](https://www.pv-magazine.com/2026/07/16/malaysia-unveils-sixth-large-scale-solar-tender/); [SolarQuarter](https://solarquarter.com/2026/07/24/malaysia-launches-lss6-tender-for-2650-mw-solar-and-1250-mw-6000-mwh-battery-storage-projects/)
- CRESS status and Dec 2025 guideline revision — [Baker McKenzie](https://www.bakermckenzie.com/en/insight/publications/2026/01/malaysia-2026-updates-to-renewable-energy-schemes); [ASEAN Centre for Energy](https://aseanenergy.org/publications/policy-insight-corporate-renewable-energy-supply-scheme-cress)
- Grid concentration, Johor DC demand, PMU build-out — [Wood Mackenzie](https://www.woodmac.com/press-releases/jb-data-center-expansion/); [The Edge Malaysia](https://theedgemalaysia.com/node/807442)
- TNB connection process (CAS/CCC, ESAH), Nodal Points — [TNB RE Application Handbook](https://www.mytnb.com.my/-/media/Project/TNB/myTNBportal/Documents/Guides-and-Booklets/TNB_RENEWABLE_ENERGY_APPLICATION_HANDBOOK_REVISION_2020.pdf); [SEDA Nodal Points](https://www.seda.gov.my/download/tnb-nodal-points/)
- EIA Order 2015 treatment of solar farms — [AGV Environment](https://www.agvenvironment.com/solar-energy-project-eia/); [EIA requirements for solar farm development in Malaysia](https://www.researchgate.net/publication/343537204_Dokumen_Panduan_Keperluan_EIA_bagi_Pembangunan_Ladang_Solar_Di_Malaysia)
- DC due diligence scope — [IPM: Due Diligence Study for Data Centre Development in Malaysia](https://ipm.my/due-diligence-study-for-data-centre-development-in-malaysia/); [Christopher & Lee Ong: Cloud and Data Centres](https://www.christopherleeong.com/viewpoints/cloud-and-data-centres/)
- P50/P90, DSCR 1.20–1.35 — [PVcase energy yield bankability](https://pvcase.com/blog/energy-yield); [Lion Solar](https://lion-solar.com/solar-resource-assessment-bankable-solar/)
