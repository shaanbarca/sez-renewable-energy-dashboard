# Gap Analysis: Existing App vs. Conversation Spec

## TL;DR

Your existing methodology is far more mature than the spec I produced. About 70% of what we discussed is already built. The remaining 30% contains genuine improvements, but several of my suggestions were based on assumptions that your app had already addressed differently (and often better). Below is the honest breakdown.

---

## Part 1: What's Already Built (My Spec Was Redundant)

These items from our conversation spec are already implemented in your codebase. No action needed.

| Topic | My Spec Said | Your App Already Has |
|---|---|---|
| Buildability filters | 8-step filter process (irradiance, slope, land cover, protected areas, peatland, airports, floods, contiguity) | 4-layer filter: Kawasan Hutan, peatland, ESA WorldCover, DEM slope/elevation, min 10ha contiguity. More Indonesia-specific and legally grounded. |
| Slope threshold | 5° | 8° with rationale: "civil works prohibitive" above 8°. Yours is more permissive but defensible for Indonesia. Keep yours. |
| LCOE formula | Standard CRF-based LCOE with grid connection costs in numerator | Already implemented: `lcoe_solar_grid_connected()` with `CONNECTION_COST_PER_KW_KM` + `GRID_CONNECTION_FIXED_PER_KW` + `LAND_COST_USD_PER_KW`. |
| 50 km search radius | Suggested as default | Already the standard: `pvout_buildable_best_50km` with haversine distance mask. |
| Substation proximity | Find nearest substation, calculate distance | Three-point proximity already built: solar→substation, KEK→substation, with 2,913 substations. |
| Substation capacity traffic light | Green/yellow/red based on utilization | Already implemented: `capacity_assessment()` with green/yellow/red/unknown. |
| Inter-substation connectivity | Check if transmission line exists between substations | Already built: geometric check against 1,595 PLN grid lines + PLN region fallback. |
| User-adjustable assumptions | Sliders for all key parameters | 3-tier slider system (core, cost structure, thresholds) already live. |
| Grid integration categories | Gap analysis showing what's missing | Already built: `within_boundary` / `grid_ready` / `invest_transmission` / `invest_substation` / `grid_first`. |
| Action flags | Policy-relevant flags per KEK | 8 flags already implemented with priority ordering. |
| Who pays for grid infrastructure | Developer builds gen-tie, transfers to PLN | Correctly reflected in Appendix B: "Gen-tie ownership typically transfers to PLN post-commissioning." |
| RUPTL as informational overlay | Don't use as hard filter | Already treated this way: `plan_late` flag is informational, not exclusionary. |
| Personas | Policymaker, investor | 5 personas already defined with readiness scores, data gaps, and user journeys. |

---

## Part 2: Genuine Improvements from Our Conversation

These items are either missing from your current app or represent meaningful upgrades to existing features.

### 2.1 Buildable Land Polygons (HIGH VALUE)

**Current state:** Your app picks the SINGLE best pixel per KEK (`pvout_buildable_best_50km`) and records its coordinates. It calculates aggregate `buildable_area_ha` and `max_captive_capacity_mwp` but doesn't generate discrete polygons.

**What our conversation adds:** Convert contiguous buildable pixels into individual polygon objects, each with its own area, max capacity, centroid, average irradiance, and slope. This enables:
- Showing the user WHERE the buildable areas are on the map (not just one point)
- Comparing multiple buildable areas within the same KEK's radius
- Different polygons may be near different substations — enabling the multi-substation comparison logic

**Recommendation:** This is the highest-value addition. Your current "best pixel" approach is good for ranking KEKs against each other, but the polygon approach is essential for the investor/developer who needs to see actual site options within a KEK's vicinity.

**Caveat:** Your PVOUT raster is ~1km resolution (~86 ha/pixel). At this resolution, polygons will be coarse. The value improves dramatically if you ever move to higher-resolution data.

### 2.2 Multi-Substation Comparison (MEDIUM VALUE)

**Current state:** Your app finds the single nearest substation to each point (solar site and KEK). It doesn't compare multiple substation options.

**What our conversation adds:** For a given solar site, evaluate ALL substations within 40 km. Compare total interconnection cost across options:
- Closer substation with insufficient capacity → gen-tie + upgrade cost
- Farther substation with full capacity → higher gen-tie, no upgrade
- Downsize farm to match closer substation → lower gen-tie, lower revenue

**Recommendation:** Medium priority. Your current single-nearest approach works for 25-KEK screening. Multi-substation comparison becomes important when users drill into specific sites for investment decisions.

### 2.3 Capacity Slider with LCOE Curve (MEDIUM VALUE)

**Current state:** Your app has a WACC slider that shows how LCOE changes with financing cost. But there's no slider for "desired build capacity" that shows how LCOE changes with project scale.

**What our conversation adds:** A capacity slider (e.g., 10 MW to polygon max) that dynamically recalculates LCOE. At small scale, fixed costs dominate → high LCOE. At the sweet spot, LCOE is minimized. Beyond grid constraint, upgrade costs push LCOE back up. Display as a curve.

**Recommendation:** High value for the IPP persona. They think in terms of "how big should I build?" Your current tool tells them where to build but not how big.

### 2.4 Substation Upgrade Cost in LCOE (MEDIUM VALUE)

**Current state:** Section 8.6 says "Substation upgrade: Flagged via capacity assessment; cost estimation deferred." The traffic light tells the user the substation may need upgrading, but the cost isn't folded into the LCOE.

**What our conversation adds:** When `capacity_assessment == "red"`, estimate the upgrade cost and include it in the LCOE numerator. This turns a qualitative flag into a quantitative impact on project economics.

**Recommendation:** Add as a user-adjustable parameter ($/MVA of added capacity, default TBD). When the substation is flagged red, compute the LCOE with and without the upgrade cost so the user sees the impact.

### 2.5 SEZ-Anchored "What's Missing" Framing (LOW-MEDIUM VALUE)

**Current state:** Your app already does gap analysis via `grid_integration_category`. But the framing is scorecard-style ("here's this KEK's status") rather than spatial-story ("here's your SEZ, here's the solar around it, here's what's missing between them").

**What our conversation adds:** Start from the SEZ, radiate outward to show solar potential, then color-code by gap type. The output tells policymakers: "if you build this one substation here, you unlock X MW of solar for this SEZ."

**Recommendation:** This is more of a UX/presentation change than a data model change. Your backend already has the data to support this view. Consider adding a "spatial story" view alongside the existing scorecard view.

---

## Part 3: Where My Spec Was Wrong or Inferior

Items where your existing approach is better than what I suggested. Do NOT adopt my version.

| My Spec Said | Your App Does (Better) | Why Yours Is Better |
|---|---|---|
| Gen-tie cost: $1-3M per mile (absolute) | $5/kW-km + $80/kW (per-kW basis) | Per-kW cost scales with project size. A 10 MW and 100 MW project don't pay the same absolute gen-tie cost. Your formulation is standard for LCOE modeling. |
| Capacity factor: flat 18% default | Derived from actual PVOUT: `CF = PVOUT_annual / 8,760` (range 14.8-19.7%) | Location-specific CF from actual solar data is far superior to a flat assumption. |
| Slope threshold: 5° | 8° with rationale | 5° is overly conservative for flat-panel solar. 8° is within industry norms and your rationale (civil works prohibitive above 8°) is defensible. |
| Airport buffer zones as a filter | Not included | At 1km raster resolution, airport buffers would remove at most 1-2 pixels per KEK. Not worth the data layer complexity. Correct omission. |
| Flood zones as a filter | Deferred to v1.2 (BNPB portal inaccessible) | Pragmatic. Slope already removes most flood-prone lowlands indirectly. |
| Solar farm cost: $900K/MW default | $960/kW from ESDM Technology Catalogue 2023, with low/mid/high bands | Sourced from official Indonesian government catalogue with bands. Much more credible than my generic global estimate. |
| Distance thresholds: 2-5 miles (US) / 20-40 km (Indonesia) | 5 km solar-to-substation, 15 km KEK-to-substation | Your thresholds are calibrated to your model's purpose (screening, not project finance). The US benchmarks I cited are for a different context. |

---

## Part 4: Suggested Changes to Each Document

### METHODOLOGY_CONSOLIDATED.md

| Change | Section Affected | Priority | Detail |
|---|---|---|---|
| Add polygon generation methodology | §3.3 Buildability filters | P1 | After the current filter pipeline, add a step: "Group contiguous buildable pixels into discrete polygons. Calculate per-polygon: area, max MW, centroid, average PVOUT." Currently the output is a single best-pixel coordinate. |
| Add multi-substation evaluation | §8.1 Three geographic points | P2 | Currently finds single nearest substation. Add option to evaluate top 3 substations within search radius and compare total interconnection cost. |
| Add substation upgrade cost estimate | §8.6 Infrastructure cost layers | P1 | Row 3 currently says "cost estimation deferred." Add a parametric estimate: upgrade cost = capacity_gap_mva × $/MVA (user-adjustable). Fold into grid-connected LCOE when capacity_assessment is red. |
| Add capacity-dependent LCOE logic | §6.2 Grid-connected LCOE | P2 | Currently LCOE is computed at `max_captive_capacity_mwp`. Add ability to compute LCOE at user-specified capacity to show the scale-vs-LCOE tradeoff. |
| Add Indonesia transmission corridor context | §8.3 Threshold values | P0 (low effort) | Add a note citing Norton Rose Fulbright: "In Indonesian IPP practice, transmission corridors of 20-40 km from plant to nearest PLN substation are common." This contextualizes the 5 km threshold as an optimistic screening cutoff, not the outer limit. |
| Reconcile gen-tie cost units with global context | §6.2 / §8.6 | P0 (low effort) | Add a note translating between your $5/kW-km and the industry-standard $1-3M/mile. Example: at 25 MW and 5 km, your formula gives $105/kW × 25,000 kW = $2.625M, which equals ~$0.5M/km — on the low end of global benchmarks. This helps users who come in with global frame of reference. |

### PERSONAS.md

| Change | Persona | Priority | Detail |
|---|---|---|---|
| Strengthen IPP capacity sizing question | P4: IPP Developer | P1 | The IPP persona's journey doesn't include "how big should I build?" Add a step: "Use capacity slider to find LCOE sweet spot — the build size where LCOE is minimized given grid constraints and fixed cost amortization." This requires the capacity slider feature (§2.3 above). |
| Add spatial exploration to IPP journey | P4: IPP Developer | P2 | IPP currently sees one best pixel per KEK. With polygons, add: "Browse buildable polygons on map. Compare multiple sites within the same KEK radius — different polygons may have different substation access and LCOE." |
| Add "build vs. buy" framing for Tenant | P5: KEK Tenant | P1 (low effort) | The Tenant persona notes that all KEKs pay the same tariff today. Our conversation surfaced that the differentiation for tenants is about future risk. Add a note: "If wheeling is ever adopted, KEKs near strong solar potential and grid-ready substations would benefit first — making grid_ready status a forward-looking site selection criterion." |
| Add DFI aggregate investment sizing | P2: DFI Investor | P1 | Gap already noted: "`grid_investment_needed_usd` not yet a first-class column." Our conversation confirmed this is high-value. Prioritize: multiply `transmission_cost_per_kw × solar_capacity × 1000` to get total investment estimate. |

### USER_JOURNEYS.md

| Change | Journey | Priority | Detail |
|---|---|---|---|
| Add "size the project" step to IPP journey | Journey 4 | P1 | Currently goes from "rank by capacity" to "filter actionable sites." Insert a step between 5 and 6: "Adjust capacity slider to find the LCOE sweet spot for this site. Compare full-build (may need substation upgrade) vs. downsized (fits existing capacity)." |
| Add spatial browsing step | Journey 4 | P2 | With polygon data, add: "Click buildable area polygons on the map to see individual site options. Each polygon shows its own area, max capacity, and distance to nearest substation." |
| Add "what would it take" step to Policy journey | Journey 3 | P1 (low effort) | Between steps 2 and 3, add: "For invest_substation/invest_transmission KEKs, note the estimated grid investment cost and the solar capacity it would unlock. The ratio (MW unlocked / $M invested) is the policy efficiency metric." This data already exists in your model. |

---

## Part 5: What to Prioritize

### Do Now (P0 — low effort, high clarity)
1. ~~Add Indonesia transmission corridor context note to §8.3~~ → ✅ Done (2026-04-11, TODOS Q1)
2. ~~Add gen-tie cost unit translation note to §6.2~~ → ✅ Done (2026-04-11, TODOS Q2)
3. ~~Add "build vs. buy" future wheeling note to Tenant persona~~ → ✅ Done (2026-04-11, TODOS Q3)
4. Compute `grid_investment_needed_usd` as a first-class column → TODOS Q4

### Do Next (P1 — medium effort, high value)
5. Polygon generation from buildability raster → TODOS M14
6. Substation upgrade cost estimate folded into LCOE → TODOS M12
7. Capacity slider + LCOE curve visualization → TODOS M16

### Do Later (P2 — higher effort, incremental value)
8. Multi-substation comparison optimizer → TODOS M15
9. Spatial story / SEZ-anchored map view → TODOS L10
10. Per-polygon substation distance calculations → included in TODOS M14

---

## Part 6: What NOT to Change

- **Do NOT change your slope threshold from 8° to 5°.** Yours is better calibrated for Indonesia.
- **Do NOT change your gen-tie cost formulation.** Per-kW-km is correct for LCOE modeling.
- **Do NOT change your capacity factor derivation.** PVOUT-derived is superior to flat defaults.
- **Do NOT add airport buffer zones.** Not worth it at your current resolution.
- **Do NOT make RUPTL a hard filter.** Your current informational approach is correct, especially given Prabowo's acceleration beyond RUPTL targets.
- **Do NOT adopt the US 2-5 mile distance benchmarks.** Your 5 km / 15 km thresholds are calibrated to your screening purpose. Add the Indonesia 20-40 km context as a note, not a threshold change.
