# Industrial captive solar — hard vs soft filter distinction + slider override semantic

**Date:** 2026-05-11 (rev 2)
**Status:** Methodology proposal, awaiting final review. Not yet a v-release commitment.
**Author:** Drafted with /general-purpose research agent + iterated with user
**Target release:** v4.0.5 or v4.1 (TBD post-review)

---

## TL;DR

The current `within_boundary_capacity_mwp` filter is a single 4-layer raster that treats all exclusions the same. In reality the layers split into two categories:

- **Hard filters** (physical / legal): slope >8°, peatland, Kawasan Hutan protected forest. These exclude land that **truly cannot host solar** regardless of intent. The slider should never override these.
- **Soft filters** (zoning / current use): built-up land cover, agricultural cover. These exclude land that's currently in another use but **the site owner can choose to redeploy** (canopy over parking, repurpose storage yards, etc.).

**Recommended fix:** rebind the slider from "haircut on what passed the filter" to **"% of soft-excluded land to override and bring back into deployable."** Math:

```
deployable_area = baseline_area + (soft_excluded_area × slider%)
where:
  baseline_area    = polygon ∩ (all 4 filters pass)     — unchanged from today
  hard_max_area    = polygon ∩ (only HARD filters)       — new pipeline column
  soft_excluded    = hard_max_area − baseline_area       — derived
```

At slider = 0% you get today's strict methodology. At slider = 100% you get the physical/legal maximum (polygon minus slope + peat + Kawasan Hutan). Default stays at **20%** but the meaning changes — from "20% of buildable land is realistically deployable" (haircut) to "20% of zoning-excluded land is overridable by the owner" (mild override).

**Methodological honesty:** the slider IS the user's local knowledge. At industrial sites the owner knows their site better than any raster — the slider lets them encode that knowledge. We provide a defensible default; users override per site.

**Critical implication:** **slider semantic is reversed.** Today, slider down = more conservative. Under the new model, slider down = more conservative (raster baseline only). Same direction → no UX reversal. But the **numerical effect of the default changes significantly** — see §5.

---

## 1. Problem statement

### What the pipeline does today

`src/pipeline/build_fct_site_resource.py` runs every site polygon through 4 buildability filters:

1. **Slope** — exclude pixels with slope >8° (solar) or >20° (wind)
2. **Land cover** — exclude forest, built-up, agriculture, etc.
3. **Kawasan Hutan** — exclude Indonesian protected forest reserves
4. **Peatland** — exclude peat-soil pixels (engineering / subsidence)

Pixels that survive all 4 → buildable raster → intersect with site polygon → `within_boundary_area_ha`. Divide by 1.5 ha/MWp → `within_boundary_capacity_mwp`.

At display time (`frontend/src/components/panels/scoredrawer/ResourceTab.tsx`), the user-adjustable `wb_buildout_footprint_ratio` slider haircuts this number further:

```
displayed = within_boundary_capacity_mwp × slider%
```

### Where the gap is — the 4 layers aren't equivalent

The filter conflates two fundamentally different kinds of exclusion:

| Layer | What it excludes | Owner can override? | Methodology category |
|---|---|---|---|
| Slope >8° | Steep terrain | No (terracing economically prohibitive at scale) | **HARD physical** |
| Peatland | Peat-soil land | No (subsidence + engineering disaster) | **HARD physical** |
| Kawasan Hutan | Indonesian state-protected forest | No (legal protection, even inside private fence) | **HARD legal** |
| Land cover (built-up) | Existing factory floors, warehouses, paved areas | **Yes** (canopy over, redeploy buffer zones) | **SOFT zoning** |
| Land cover (agricultural) | Crops, plantations | **Yes** (owner can convert their own land) | **SOFT zoning** |
| Land cover (forest, non-Kawasan-Hutan) | Mature non-protected forest | Partial (clearing requires permits, environmentally costly) | **SOFT-ish** — treat as soft for now |

The current slider haircuts the output of all 4 layers indiscriminately. For sites dominated by HARD constraints, that's wrong (you can't bring slope back with a slider). For sites dominated by SOFT constraints — fully-operating industrial factories — that's also wrong because the slider can only reduce, not bring back the soft-excluded land that the owner can actually redeploy.

### Concrete site walkthrough (using the dashboard screenshot)

The user's reference site shows:
- `within_boundary_area_ha` = 260 ha (passes all 4 filters)
- Slider at 10% → displayed "Available Area" = 26 ha → 17.1 MWp captive

What's invisible in this number:
- Polygon area might be (eyeballing) 400–500 ha
- Slope/peat/Kawasan Hutan excludes maybe 0–20 ha — the polygon is mostly flat coastal land
- Soft-excluded (built-up + agricultural inside polygon) = 220+ ha
- That soft-excluded land includes parking lots, factory roofs (already in V4.1 rooftop), storage yards, internal roads, buffer zones

The current slider, even cranked to 100%, can only display 260 ha (the raster baseline). It cannot surface the 220 ha of soft-excluded land that the owner could actually deploy on as canopy or repurposed ground-mount.

---

## 2. Sources reviewed

External research run via /general-purpose agent, 2026-05-11. URLs verified at time of writing.

### Authoritative — peer-reviewed / lab reports

- **[NREL/TP-6A20-79444 — LA100 Chapter 5: Utility Options for Local Solar](https://docs.nrel.gov/docs/fy21osti/79444-5.pdf)** — Canonical layered-potential methodology. **Parking-canopy is computed separately from rooftop and greenfield, never merged.**
- **[NREL/TP-6A20-65298 — Rooftop Solar Photovoltaic Technical Potential in the US](https://docs.nrel.gov/docs/fy16osti/65298.pdf)** — Methodology pattern for "developed-land" potential: lidar suitable area filtered by shading, tilt, azimuth, contiguous area.
- **[LBNL — Land Requirements for Utility-Scale PV (2022)](https://www.energy.gov/sites/default/files/2022-01/lbnl_ieee-land-requirements-for-utility-scale-pv.pdf)** — Empirical density: fixed-tilt 2.8 acres/MW ≈ 1.45 ha/MWp.
- **[NREL/TP-6A20-75548 — Solar Resource & Technical Potential Modeling](https://docs.nrel.gov/docs/fy20osti/75548.pdf)** — Standard utility-scale exclusion criteria; confirms why our 4-layer filter is blind to developed land.

### Indonesia-specific

- **[World Bank/ESMAP — Solar Resource & PV Potential in Indonesia (Solargis, 2017)](https://documents1.worldbank.org/curated/en/729411496240730378/pdf/115347-ESM-P145273-PUBLIC-IndonesiaSolarResourcePotentialWBESMAPMay.pdf)** — Resource-only, no industrial buildability fraction published.
- **[ETP — Decarbonize Captive Power Indonesia (2025)](https://www.energytransitionpartnership.org/wp-content/uploads/2025/08/INO_Decarbonize-Captive-Power-Market-for-Industrial-Decarbonization.pdf)** — Confirms no Indonesia-specific "% of fence-line deployable" number exists yet.
- **[JETP Captive Power Study (in progress)](https://jetp-id.org/news/jetp-secretariat-launches-landmark-captive-power-study-in-indonesia)** — Future empirical anchor.
- **[IESR — MEMR Regulation No. 2/2024](https://iesr.or.id/en/memr-regulation-no-2-2024-limits-public-participation-to-support-energy-transition-through-rooftop-solar-pv/)** — Regulatory ceiling: net metering abolished; industrial behind-the-meter still permitted.
- **[Cell Reports Sustainability — Solar+storage vs captive coal (Indonesia, 2025)](https://www.sciencedirect.com/science/article/pii/S2589004225020243)** — Indonesia industrial captive solar LCOE 5.6–7.9 ¢/kWh.

### Industry / policy benchmarks

- **California SB 49** — Mandate for solar canopy over **50%** of new nonresidential parking lot surface. Most aggressive published canopy-coverage benchmark.
- **[Yale E360 — Solar Canopies on Parking Lots](https://e360.yale.edu/features/putting-solar-panels-atop-parking-lots-a-green-energy-solution)** — LBNL urban land-use studies: pavement = 35–50% of urban surface, ~40% of pavement is parking → 15–20% of urban land is parking.
- **[AEE Center IJEM — Solar Canopies Can Turn Parking Lots Into Power Plants](https://www.aeecenter.org/wp-content/uploads/2025/05/IJEM-Vol7-Iss2-Solar-Canopies-Can-Turn-Parking-Lots-Into-Power-Plants.pdf)** — Canopy density rule of thumb: 1 MW per 2 acres ≈ 0.8 ha/MWp.

### Case studies (lower confidence, useful for plausibility)

- **EVRAZ Rocky Mountain Steel** — 240 MW behind-the-meter solar for a single steel mill ([PV Magazine 2018](https://www.pv-magazine.com/2018/08/20/big-steel-goes-big-solar-in-the-us/)).
- **Lockheed Martin canopy** — 4 acres → 2 MW ([DOE Better Buildings](https://betterbuildingssolutioncenter.energy.gov/showcase-projects/lockheed-martin-transforming-parking-lot-energy-generating-solar-carport)).
- **Bangladesh industrial rooftop survey** — 6,045 industrial plants → 7.4 GWp ([MDPI Energies 2022](https://www.mdpi.com/1996-1073/15/11/4037)). Closest SE Asia analog.

---

## 3. Methodology — hard/soft filter split + slider override semantic

### Filter classification

| Layer | Current behavior | Proposed classification | Slider can override? |
|---|---|---|---|
| Slope >8° (solar) | Excludes | HARD | No |
| Slope >20° (wind) | Excludes | HARD | No |
| Land cover: forest non-Kawasan-Hutan | Excludes | SOFT-ish (treat as SOFT for v1) | Yes (with permits) |
| Land cover: built-up | Excludes | **SOFT** | Yes |
| Land cover: agricultural | Excludes | **SOFT** | Yes |
| Land cover: bare / open | Passes | HARD-PASS | n/a |
| Kawasan Hutan | Excludes | HARD (legal) | No |
| Peatland | Excludes | HARD | No |

### Two new derived areas per site

```
baseline_area_ha   = polygon ∩ (slope OK ∧ land cover OK ∧ not Kawasan Hutan ∧ not peat)
                   = current within_boundary_area_ha — UNCHANGED at the pipeline level

hard_max_area_ha   = polygon ∩ (slope OK ∧ not Kawasan Hutan ∧ not peat)
                   = NEW pipeline column. Drops the land-cover constraint only.

soft_excluded_ha   = hard_max_area_ha − baseline_area_ha
                   = derived, no need to store. The "land that's currently zoned/used
                     for something else but is physically/legally buildable."
```

### Slider semantic — "soft-filter override %"

Slider value = the fraction of `soft_excluded_ha` that the site owner overrides:

```
deployable_area_ha    = baseline_area_ha + (soft_excluded_ha × slider%)
deployable_capacity_mwp = deployable_area_ha / 1.5
```

- **0%**: deployable = baseline only. Equivalent to "trust the 4-layer raster strictly."
- **20%** (default): baseline + a small override on zoning-excluded land.
- **100%**: deployable = hard_max. Equivalent to "the owner overrides all soft exclusions; only physical/legal constraints remain."

### Why this is defensible

1. **Hard exclusions stay rigorous** — slope, peat, Kawasan Hutan are physical or legal facts the dashboard cannot wave away.
2. **Soft exclusions surface as adjustable** — the slider explicitly exposes the assumption that today is hidden in the raster output.
3. **The slider IS the user's local knowledge** — at any specific site, only the user knows whether the storage yard is actively staging materials (can't override) or is underutilized (can override). The slider gives them a knob.
4. **Methodology citation chain**: NREL LA100 layered methodology validates separating different exclusion types; LBNL urban-pavement studies + CA SB 49 anchor the deployable-fraction defaults; the literature consistently treats "developed land canopy" as a distinct potential layer.

---

## 4. Worked examples

### Example A — the user's screenshot site (industrial polygon, partial built-up)

Estimated from the image (real numbers would come from the pipeline):

```
polygon_area_ha      = ~450 ha
hard_excluded        = ~10 ha   (small slope + maybe small peat patch)
hard_max_area_ha     = ~440 ha
baseline_area_ha     = 260 ha   (current raster output, dashboard shows this today)
soft_excluded_ha     = 180 ha   (built-up + agricultural inside polygon)
```

Slider sensitivity at this site:

| Slider | Deployable area | Captive MWp (÷1.5) |
|---|---|---|
| 0% | 260 ha | 173 MWp |
| 10% | 278 ha (+18 ha) | 185 MWp |
| 20% (default) | 296 ha (+36 ha) | 197 MWp |
| 50% | 350 ha (+90 ha) | 233 MWp |
| 100% | 440 ha (hard_max) | 293 MWp |

**Current dashboard display at this site** (slider=10%, old semantic): 17.1 MWp.
**Proposed display at the same slider position** (10%, new semantic): 185 MWp.

This is a **~10× jump in the displayed number** at this site. Not because the methodology is more generous — because the OLD slider was a 90% HAIRCUT on a 260 ha base (= 26 ha shown), while the NEW slider at 10% lets 100% of baseline through plus a 10% override (= 278 ha shown). See §5 for why this matters.

### Example B — fully-built single-factory industrial site (e.g., dense cement plant)

```
polygon_area_ha      = 80 ha
hard_excluded        = 0 ha
hard_max_area_ha     = 80 ha
baseline_area_ha     = 2 ha   (raster sees only edge buffer)
soft_excluded_ha     = 78 ha   (almost entirely built-up)
```

| Slider | Deployable area | Captive MWp |
|---|---|---|
| 0% | 2 ha | 1.3 MWp |
| 20% | 17.6 ha | 11.7 MWp |
| 100% | 80 ha | 53 MWp |

**Current display:** 0.4 MWp (raster × 20%). Effectively zero.
**Proposed at 20%:** 11.7 MWp. Realistic canopy + edge-zone estimate.

### Example C — greenfield KEK (e.g., a planned KEK with mostly undeveloped land)

```
polygon_area_ha      = 600 ha
hard_excluded        = 80 ha   (some slope + some peat patches)
hard_max_area_ha     = 520 ha
baseline_area_ha     = 480 ha   (raster picks up most of the undeveloped land)
soft_excluded_ha     = 40 ha    (a few existing factories already on the site)
```

| Slider | Deployable area | Captive MWp |
|---|---|---|
| 0% | 480 ha | 320 MWp |
| 20% | 488 ha | 325 MWp |
| 100% | 520 ha | 347 MWp |

**Current display:** 64 MWp (raster × 20%).
**Proposed at 20%:** 325 MWp.

At a greenfield KEK the slider barely matters — the raster baseline captures almost everything. But the JUMP from current 64 MWp to proposed 325 MWp is significant. See §5.

---

## 5. The big number jump — implications

### Why the displayed numbers jump significantly

The OLD slider was a **haircut**: `raster × slider%`. At default 20% this meant we were showing 20% of what the raster found — a hefty conservative cut to reflect "even in the raster-passing area, only 20% is realistically deployable after factoring in roads, factories, buffers within the buildable pixels."

The NEW slider is an **override**: `raster + (soft_excluded × slider%)`. At default 20% this counts 100% of the raster baseline + a small 20% override on zoning-excluded land.

These have DIFFERENT meanings even at the same numerical slider position. The OLD 20% was "80% conservative on what the raster found." The NEW 20% is "100% of raster + 20% of additional override potential."

**The new semantic produces larger displayed numbers** because we're no longer haircutting the raster. The 4-layer filter is now treated as the **methodologically rigorous floor**, not a starting point to be cut down.

### Is the bigger number the "right" number?

For industrial sites: **yes, more honest.** The current display showing ~0 MWp at fully-built factories is misleading — there's clearly deployment potential at those sites, the dashboard just couldn't surface it.

For greenfield KEKs: **maybe too generous.** The current haircut at KEKs was implicitly accounting for the fact that the coarse-resolution raster (1 km pixels) might count "buildable" pixels that contain finer-resolution roads / factories. Without the haircut, the KEK number is the unhaircut raster output, which could be optimistic.

If the KEK haircut is methodologically important, we need a **separate mechanism** to address coarse-raster optimism — e.g., a per-pixel built-up density estimate, or a finer-resolution raster, or a KEK-specific second slider. **Not the same slider as the override slider.**

For v1 we accept the regression at KEKs: the slider stops haircutting, KEKs display the raster baseline as-is. If real-world KEK overestimation is a problem, surface it as a follow-up issue.

### Default value reasoning

User confirmed: keep default at **20%**, with the new semantic. Reasoning:
- It's a sensible "mild override" default — assumes some owner override is realistic but most zoning-excluded land really is in active use.
- Users can always change it per site or globally.
- At industrial sites this gives a meaningful canopy estimate (~11.7 MWp in Example B).
- At KEKs the slider has small effect anyway (Example C: 5 MWp difference between 0% and 20%).

### Migration concern

This is a **behavioral change** to the existing slider. Saved scenarios, screenshots, exported CSVs, and downstream analyses using the old slider's haircut output will produce different numbers under the new semantic. Worth flagging in the §9 changelog explicitly: "the `wb_buildout_footprint_ratio` slider semantic changed from haircut to override on YYYY-MM-DD; pre-change numbers are not comparable."

---

## 6. Implementation impact

### Pipeline (`src/pipeline/build_fct_site_resource.py`)

New computation per site:
- `hard_max_area_ha` — re-run the buildability filter with only HARD layers (slope + Kawasan Hutan + peatland; drop land-cover layer). Intersect with site polygon. Sum.
- Optionally: `hard_max_pvout_kwh_kwp_yr` — average PVOUT across the hard-max pixels. Useful for the generation calculation (since soft-excluded land would inherit a PVOUT from somewhere; using the hard-max average is reasonable).

New columns in `outputs/data/processed/fct_site_resource.csv`:
- `within_boundary_hard_max_ha` (new)
- `within_boundary_capacity_hard_max_mwp` (derived: hard_max_ha / 1.5)

`within_boundary_area_ha`, `within_boundary_capacity_mwp` — unchanged.

### API (`src/api/routes/scorecard.py`)

Scorecard endpoint already passes raw values to the frontend; the new columns just flow through. No backend math change needed at request time — the slider math is all client-side (already the pattern for `wb_buildout_footprint_ratio`).

Soft-excluded area is derived client-side: `hard_max - baseline`.

### Frontend (`frontend/src/components/panels/scoredrawer/ResourceTab.tsx`)

New math in the Captive Solar → Ground-mounted subsection:

```typescript
const baseline = row.within_boundary_area_ha ?? 0;
const hardMax = row.within_boundary_hard_max_ha ?? baseline;
const softExcluded = Math.max(0, hardMax - baseline);

const deployableArea = baseline + softExcluded * buildoutPct;
const deployableCapacity = deployableArea / 1.5;
```

`adjustedCapacity`, `adjustedArea`, `adjustedGen`, `adjustedCoverage` all switch to the new formula.

### Frontend (`AssumptionsPanel.tsx`, `GridTab.tsx`)

Same slider state (`wb_buildout_footprint_ratio`) — just behaves differently downstream. No UI changes needed beyond the label rename below.

### Slider label change

"Usable ground %" no longer accurately describes the semantic. Options:

- **"Soft-filter override %"** — most precise, jargon-y
- **"Owner override %"** — captures the intuition (the owner can override zoning)
- **"Zoning override %"** — narrowest scope, doesn't capture "owner can clear soft-forest"
- **"Land-use override %"** — clean middle ground
- **"Usable ground % (incl. override)"** — minimal change from current label, adds clarification

Pending user choice.

### Methodology docs

`docs/METHODOLOGY_CONSOLIDATED.md` — rewrite §5 Within-boundary captive solar:
- Document the hard/soft filter distinction
- New formula: `deployable = baseline + soft_excluded × slider%`
- Updated default semantic
- Pointer to this doc as the canonical source review

`DATA_DICTIONARY.md` — add `within_boundary_hard_max_ha`, `within_boundary_capacity_hard_max_mwp` rows.

`DESIGN.md` — update §3 Assumption Sliders table entry for `wb_buildout_footprint_ratio` to reflect the override semantic.

### Tests

- `tests/test_pipeline_within_boundary.py` (if it exists) — add cases for hard_max calculation
- `tests/fixtures/scorecard_golden.pkl` — regenerate after pipeline change (numbers will shift across all sites)
- Backend test count expected unchanged

### Backwards compatibility

`wb_buildout_footprint_ratio` parameter retained for URL/scenario state compatibility. The math changes but the parameter name + range + default stay the same. Saved scenarios will produce different numbers (see §5 migration concern) but won't break.

---

## 7. Indonesia-specific considerations

### No empirical anchor exists yet for the override fraction

The 0%–100% range and 20% default are pure intuition. JETP CIPP 2024 captive power study (in progress per ETP 2025) will eventually publish a real empirical anchor. Frame the slider tooltip as "first-pass estimate, NREL-style layered methodology, awaiting empirical Indonesia data."

### Regulatory ceiling — behind-the-meter still permissible

MEMR Regulation No. 2/2024 abolished net metering and quotas grid-tied rooftop. Industrial **behind-the-meter self-consumption** is still allowed — the canopy use case here. Flag in tooltip: "technical potential ≠ regulatorily permissible export."

### Captive coal context

Nickel IIA clusters (Morowali, Weda Bay) have polygons >1000 ha hosting massive captive coal. Their `hard_max_area_ha` will be huge. At slider=20% the override adds significant capacity. Numerically correct but politically loaded — these are the highest-emission sites in the model. Worth a dedicated tooltip caveat:

> "At IIA-scale sites, override potential is large because the polygons are large. Whether 20% of an active smelter complex's footprint can host canopy solar is a deployment-feasibility question, not a methodology question. Use the slider to stress-test."

### Sectoral defaults — defer

Could default to lower override % at heavy-industrial site types (cement, steel, nickel, aluminium, fertilizer) and higher at KEKs. Per user direction in this rev: **keep flat 20%** until JETP CIPP gives empirical anchors. Premature differentiation creates bookkeeping without basis.

---

## 8. Alternatives considered

### Two-track canopy metric (the previous rev's recommendation)

Earlier draft proposed adding a parallel `canopy_potential_mwp` column with its own slider, computed as `polygon_area × canopy_fraction × 0.8 ha/MWp`, displayed as a separate subsection alongside the greenfield Ground-mounted subsection.

**Why dropped:** the user pointed out the slider already exists and should be the override mechanism. Adding a second slider creates two knobs for what is methodologically one decision (how much of the polygon do you trust as deployable). The single-slider override model is simpler, has the same defensibility (NREL LA100 still validates separating exclusion types — we just expose it via a slider rather than two metrics), and fits the existing UX without restructuring the Score Drawer card.

### Sector-aware floor on `within_boundary_capacity_mwp`

Floor `within_boundary_area_ha` at `polygon_area × 0.15` for industrial site_types. Simple but conflates greenfield with canopy in a single number, hard to defend methodologically. Dropped.

### Add raster layer for "developed industrial land"

Re-classify built-up cover as buildable with density haircut in the raster itself. Pollutes the filter that's methodologically correct for KEKs. Dropped.

### Single slider operating on polygon area directly (no baseline floor)

```
deployable = polygon_area × slider%
```

Cleaner math but doesn't surface the baseline as a methodological floor — at low slider values it'd display LESS than the rigorous raster output, which is wrong (you can't deploy less than what the strict filter says is buildable). The "baseline + override" model has the right asymmetry: the slider can only ADD to the rigorous filter result.

---

## 9. Edge cases

1. **KEK + industrial overlap** — some industrial sites sit inside KEK polygons (e.g., steel mill within a KEK). For now apply the same hard/soft model to both site_types. The site_type doesn't matter at the math level; it might matter for tooltip framing.

2. **Sites with no polygon (`polygon_source_tier = 'none'`)** — fallback to 2 km centroid buffer for both baseline and hard_max calculations. Already how the raster operates today.

3. **`polygon_source_tier = 'claude_building_hull_estimate'`** — these polygons union the largest detected buildings. They're tight to the buildings, NOT the actual fence. soft_excluded will be small (because the polygon is already mostly the buildings). Numerically the override has small effect. That's actually correct — we don't know the fence so we don't claim deployment potential outside it.

4. **Polygons with very small soft_excluded** — when hard_max ≈ baseline (greenfield KEKs), the slider has minimal effect. Display the slider anyway; users will see it doesn't change much, which is honest.

5. **Polygons with very large soft_excluded** (fully-built single factory) — slider has big effect. The 0% vs 100% range can be 10–50× the displayed number. Worth a tooltip caveat: "wide slider sensitivity at this site reflects high uncertainty about owner override potential."

6. **`hard_max < baseline`** — shouldn't be possible (hard_max is a strict superset of baseline by definition). Guard the math with `Math.max(0, hard_max - baseline)` and treat any inversion as a pipeline bug to flag.

---

## 10. Open questions for review

1. **Slider label change** — pick from §6 options:
   - "Soft-filter override %"
   - "Owner override %"
   - "Zoning override %"
   - "Land-use override %"
   - "Usable ground % (incl. override)"
   
2. **Default value confirmation** — keep at 20%? User said yes in the previous iteration, double-check now that you've seen the numerical implications (§4 examples).

3. **KEK haircut regression** — do we lose anything important by NOT haircutting raster output at KEKs? §5 walks through this — the current haircut was implicitly compensating for coarse-raster optimism. If this matters, log a follow-up issue. If it doesn't (KEK numbers are screening-level anyway), accept the regression.

4. **Behavioral change comms** — saved scenarios + screenshots + CSV exports will produce different numbers after this lands. Need a docs/CHANGELOG entry explicitly calling out the semantic change. Should this also trigger a version bump (v4.0.5 → v4.0.6, or v4.1)?

5. **Layer 2 forest classification** — should non-Kawasan-Hutan forest cover be SOFT (owner can clear with permits) or HARD (de facto protected)? Current draft says SOFT-ish. Could split: state forest reserves = HARD, secondary forest = SOFT.

6. **Issue tracking** — create a GitHub issue once the approach is locked, or land directly as v4.0.5 work?

7. **Methodology cross-reference** — should this also update the Supply Blend / Delivered Cost cascades? Both consume `within_boundary_capacity_mwp` — the new semantic means those cascade inputs change too. Need to verify downstream uses.

---

## 11. Out of scope

- **Per-site empirical soft-excluded measurement** (satellite-detected built-up area). v5.0+ data layer, requires new imagery pipeline.
- **Cost-of-canopy adjustment** to LCOE — canopy structures cost ~20–30% more per kW than ground-mount racking. Worth a follow-up in v4.2 alongside the investment decision module (#39).
- **Time-of-use / behind-the-meter regulatory modeling** — assumed permissible per MEMR 2/2024 read; deeper analysis in v4.2 fiscal-incentives workstream.
- **Per-pixel built-up density refinement** to reduce coarse-raster optimism at KEKs — separate methodology fix, not this issue.
- **Validation against JETP CIPP captive power study** — that study isn't published yet.

---

## 12. References (deduplicated)

- NREL/TP-6A20-79444 — LA100 Chapter 5: <https://docs.nrel.gov/docs/fy21osti/79444-5.pdf>
- NREL/TP-6A20-65298 — Rooftop PV Technical Potential: <https://docs.nrel.gov/docs/fy16osti/65298.pdf>
- NREL/TP-6A20-75548 — Solar Resource & Technical Potential Modeling: <https://docs.nrel.gov/docs/fy20osti/75548.pdf>
- LBNL — Land Requirements for Utility-Scale PV (2022): <https://www.energy.gov/sites/default/files/2022-01/lbnl_ieee-land-requirements-for-utility-scale-pv.pdf>
- World Bank/ESMAP — Indonesia Solar Resource (2017): <https://documents1.worldbank.org/curated/en/729411496240730378/pdf/115347-ESM-P145273-PUBLIC-IndonesiaSolarResourcePotentialWBESMAPMay.pdf>
- ETP — Decarbonize Captive Power Indonesia (2025): <https://www.energytransitionpartnership.org/wp-content/uploads/2025/08/INO_Decarbonize-Captive-Power-Market-for-Industrial-Decarbonization.pdf>
- JETP Captive Power Study: <https://jetp-id.org/news/jetp-secretariat-launches-landmark-captive-power-study-in-indonesia>
- IESR — MEMR Regulation No. 2/2024: <https://iesr.or.id/en/memr-regulation-no-2-2024-limits-public-participation-to-support-energy-transition-through-rooftop-solar-pv/>
- Cell Reports Sustainability — Solar+storage vs captive coal Indonesia (2025): <https://www.sciencedirect.com/science/article/pii/S2589004225020243>
- Yale E360 — Solar Canopies on Parking Lots: <https://e360.yale.edu/features/putting-solar-panels-atop-parking-lots-a-green-energy-solution>
- AEE Center IJEM — Solar Canopies (Vol 7 Iss 2): <https://www.aeecenter.org/wp-content/uploads/2025/05/IJEM-Vol7-Iss2-Solar-Canopies-Can-Turn-Parking-Lots-Into-Power-Plants.pdf>
- PV Magazine — EVRAZ Rocky Mountain Steel: <https://www.pv-magazine.com/2018/08/20/big-steel-goes-big-solar-in-the-us/>
- DOE Better Buildings — Lockheed Martin Solar Carport: <https://betterbuildingssolutioncenter.energy.gov/showcase-projects/lockheed-martin-transforming-parking-lot-energy-generating-solar-carport>
- MDPI Energies — Bangladesh industrial rooftop PV: <https://www.mdpi.com/1996-1073/15/11/4037>
- IEA Renewables 2024 — Electricity: <https://www.iea.org/reports/renewables-2024/electricity>

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 5 issues, 1 critical gap (downstream propagation, addressed via D1A) |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | not needed (no new UI surfaces) |
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | not needed (methodology refinement, not product scope) |
| Codex / Outside | `/codex review` | Independent 2nd opinion | 0 | skipped | small audience, well-iterated doc |

**Eng review decisions locked (D1-D4):**
- **D1A** Propagation: everything uses new math. Update `grid.py:112` + supply blend + delivered cost cascade alongside the Score Drawer math. Single source of truth.
- **D2A** Migration: accept silent change with changelog entry in `DESIGN.md §9`. Existing user is the primary user; cost of versioning the parameter outweighs benefit.
- **D3A** Pipeline refactor: single-pass filter returns both (full_mask, hard_mask). Filter classification (HARD: slope/Kawasan Hutan/peat; SOFT: land cover) lives in `src/dash/constants.py` as a dict.
- **D4A** Test coverage: full math invariants + regression at slider 0/20/100% across 3 representative sites + golden fixture audit. ~12-15 new test cases.

**Recommendations accepted inline** (no AskUserQuestion):
- PVOUT for soft-excluded land: use baseline `pvout_within_boundary` (conservative; <5% sub-1km variation in Indonesia).

**Critical-gap mitigation:** without D1A, dashboard would display "Captive 197 MWp" while backend computes delivered cost from "5 MWp" — user-visible inconsistency. D1A propagates the new math everywhere.

**Open follow-ups (not blocking, separate issues):**
- KEK coarse-raster optimism without the haircut → tracked as [#41](https://github.com/shaanbarca/eez/issues/41) (v4.1 scope).
- Layer 2 forest classification refinement (split state forest vs secondary forest) → optional v4.4+ work, not yet tracked.

**Primary tracking issue:** [#40 — v4.0.5: buildability hard/soft filter split + slider override semantic](https://github.com/shaanbarca/eez/issues/40)

**UNRESOLVED:** 0
**VERDICT:** ENG CLEARED — ready to implement, contingent on shipping the propagation + tests per D1A and D4A.

