# Project Canvas — draw a polygon, specify a project, get an assessment

**Date:** 2026-08-19 · **Status:** concept spec, not branched
**Origin:** "they can see all the potential sites for data centers, and then maybe even draw a
polygon and specification. example 250 mw data center, draw polygon etc"

**Related:** [DEVELOPER_WORKFLOW.md](DEVELOPER_WORKFLOW.md) · [MALAYSIA_STRATEGY.md](MALAYSIA_STRATEGY.md) ·
[investment_decision_module_spec_v2.md](../investment_decision_module_spec_v2.md)

---

## 1. What this resolves

This settles the open "sites vs parcels" question from the strategy doc, and the answer is **both**:

- **Discovery mode** — a curated layer of candidate sites (industrial parks, DC clusters, grid-
  adjacent land), ranked. This is what the Indonesia tool already does.
- **Canvas mode** — the user draws their own polygon, specifies a project ("250 MW data centre",
  "80 MWp solar farm, CRESS"), and gets the same assessment on *their* geometry.

Canvas mode is the commercial feature. Discovery answers "where should I look"; canvas answers
"is **this** site, which I am already negotiating for, actually viable" — and that is the question a
developer pays for.

It also changes what the product *is*: from a published analysis of a fixed universe to a tool the
developer uses on their own pipeline. That difference matters for pricing, for stickiness, and for
why it must be closed-source.

---

## 2. Worked example — the number that sells the tool

A 250 MW data centre on a drawn 100 ha polygon. **Illustrative, assumption-driven — every figure
below is a stated default the user can override, not a claim about a real site.**

| Assumption | Value |
|---|---|
| PUE | 1.30 (tropical, liquid-assisted; air-cooled ≈1.45+) |
| Annual load factor | 0.80 |
| Specific yield | 1,450 kWh/kWp/yr (Malaysia typical) |
| Ground-mount density | 1.3 ha/MWp |
| Buildable share of polygon | 60% (after buildings, roads, setbacks) |

| Output | Value |
|---|---|
| Facility load (IT × PUE) | **325 MW** |
| Grid connection required | **382 MVA** (at pf 0.85) |
| Annual consumption | **2,278 GWh/yr** |
| Solar needed for 100% annual match | **1,571 MWp** |
| — land that requires | **2,042 ha — 20× the drawn polygon** |
| On-site buildable | 60 ha |
| On-site solar potential | 46 MWp |
| On-site generation | 67 GWh/yr |
| **On-site solar covers** | **2.9% of demand** |

**That 2.9% is the product.** It reframes the conversation in one screen: on-site solar on a data
centre is a rounding error, and the real question is where the other 1,525 MWp comes from, under
which scheme, at what delivered cost. Nothing else on the market says this to a developer on a map,
against their own polygon, in ten seconds.

And note the second output: **382 MVA**. No single distribution PMU serves that. It forces a
dedicated transmission-level connection, which is a cost and schedule item measured in years — the
exact thing that kills DC projects late. Surfacing it at polygon-draw time is the whole value of
Gate 2 triage.

---

## 3. Outputs per project type

Common to both: buildable area within polygon · slope · **peat** · flood · land cover · nearest
PMU + distance + headroom · interconnection cost estimate · disqualification flags · project
finance metrics (NPV/IRR/payback, and DSCR once Tier 2 lands).

### Data centre (spec: IT load MW, PUE, cooling type, target CFE %)

1. Facility load, annual consumption, **MVA required**
2. **Land sufficiency** — does the spec physically fit the polygon at typical campus density?
3. **Grid verdict** — required MVA vs available headroom at reachable PMUs; distribution vs
   transmission-level connection; indicative cost and timeline
4. **On-site solar coverage %** (the 2.9%)
5. **Offsite requirement** — MWp needed for the target match, and at what land area
6. **24/7 vs annual matching** — annual netting is easy, hourly CFE is not; solar+BESS coverage
   curve and the cost of the last 20%
7. **Water** — cooling demand range by cooling type (flag; quantitative once B7 data lands)
8. **Kill flags** — peat (disqualifying for DC floor loading, not merely expensive), flood, slope

### Solar farm (spec: target MWp or "max", scheme, BESS on/off)

1. Buildable MWp within polygon (hard/soft split + existing land-use override slider)
2. Energy yield, LCOE, firmed and delivered cost tiers
3. **Grid** — export capacity vs headroom, gentie distance and cost
4. **Scheme comparison** — LSS6 vs CRESS vs captive, each with its own price basis, grid charges,
   and BESS requirement, ranked by IRR
5. Land conversion exposure — category of use, state rules, indicative cost/timeline
6. Kill flags

### The combination — the feature only they can build

**Draw a DC polygon → the tool finds the solar sites within X km that could serve it under CRESS.**
Demand side and supply side in one model, matched over the grid layer. A developer doing both solar
farms and data centres is the only user for whom this is one question rather than two, and it is
the single most defensible thing in this product.

---

## 4. Architecture — the one significant finding

**Canvas mode inverts a core design decision.** ARCHITECTURE.md decision #2 states it plainly:

> "All raster operations happen offline in `build_fct_site_resource.py` … the app never touches a
> GeoTIFF."

Drawing an arbitrary polygon requires raster work **at request time**, against geometry that did not
exist when the pipeline ran. The existing polygon editor does *not* solve this: `src/api/routes/
admin.py` is keyed to an existing `site_id`, gated to localhost, and its overrides are only picked
up on the **next pipeline run**. It is a data-correction tool, not an interactive one.

**The good news is that the codebase is unusually well prepared for the inversion**, in three ways
that were designed for other reasons:

| Existing asset | Why it matters here |
|---|---|
| `build_buildable_raster.py` already produces a **nationwide buildable raster** (`buildable_pvout_web.tif`) | Assessing a drawn polygon becomes *clip a precomputed national raster and count pixels* — milliseconds, not the 3-minute pipeline. This is the key enabler. |
| Decision #5: buildability filters are **pure numpy, zero I/O** | The filter logic is directly reusable at runtime. Only the windowing/integration layer is new. |
| `POST /api/scorecard` already **live-recomputes** on user assumption changes (and v4.1 RV15 recomputes rooftop from sliders) | Precedent exists for on-demand computation. This is an extension of an established pattern, not a new one. |
| Polygon persistence + provenance tiers (`manual_override` at the top of the trust ladder) already shipped | The storage half of drawing is built. |

**So the architecture becomes:** precompute national rasters once (buildable mask, PVOUT, slope,
peat, flood) → serve a new `POST /api/project/assess` that takes `{geometry, project_spec}`, clips
the national rasters to the polygon, runs the existing pure-function filters and model, and returns
the assessment. Decision #2 is amended rather than abandoned: *the heavy raster work still happens
offline; only the clip happens live.*

### Gaps to close

1. **No draw library in the frontend** — `frontend/package.json` has none. Add mapbox-gl-draw or
   terra-draw. Small.
2. **Project entity does not exist.** Everything is keyed to a known `site_id`. Need a `Project`:
   geometry + spec + results + owner, saveable and comparable. This is the real data-model change.
3. **Admin API must become a user API** — currently localhost-gated and site-keyed. Needs auth,
   per-user scoping, and decoupling from `site_id`.
4. **`SiteTypeConfig` needs a `DATA_CENTRE` entry** with a new `demand_method: "spec_driven"` —
   today it is only `area_based` or `sector_intensity`. Per decision #6 this is a two-file diff
   (one Python dict entry, one TypeScript), which is exactly what that registry was built for.
5. **Flood layer** — not currently ingested at all, and it is a genuine kill criterion in Malaysia.
6. **Hourly profiles** — 24/7 CFE matching needs an 8,760-hour solar profile and a load shape. The
   model is currently annual-energy based. This is the largest single piece of new modelling.

---

## 5. Sequencing

Slots into the strategy doc's milestones as follows:

- **M2 (project finance module)** is a hard prerequisite — canvas mode without NPV/IRR/DSCR is a
  land calculator.
- **M3a — Canvas mode, solar.** National raster precompute, `POST /api/project/assess`, draw tool,
  `Project` entity. Reuses everything built.
- **M3b — Data centre type.** `DATA_CENTRE` site type, spec-driven demand, MVA and land sufficiency
  checks, on-site coverage %. The 2.9% output ships here.
- **M3c — Matching.** Hourly profiles, CFE curve, and the DC→solar-site search. Largest new
  modelling; do it last, and only after the developer confirms they want it.

**Demo order for the meeting:** show discovery mode (the map), then draw a polygon on a site they
know, then hand them the mouse. The moment they draw their own site is the moment it stops being a
research project.

---

## 6. Honest limits to state up front

Canvas mode invites over-trust — a user-drawn polygon *feels* like a site-specific answer. It is
not. The same boundary from DEVELOPER_WORKFLOW.md §6 applies and should be on screen, not buried in
methodology: no geotech, no parcel-level flood modelling, no title search, no EIA, no TNB Connection
Assessment Study, no bankable P90. The tool triages; it does not underwrite.

Two specific traps worth guarding in the UI:

- **Land sufficiency and campus density** vary enormously by design (air vs liquid cooling, single
  vs multi-storey). Present as a range with the assumption visible, never a single number.
- **Grid headroom without the connection queue (B2)** overstates availability. Until that data
  exists, the verdict must read "nominal headroom" and say so.
