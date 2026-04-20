# Substation-Anchored Solar Siting Plan: Validation and Improvement Actions

## Verdict

**Ship the plan. The core algorithm is sound and matches international best practice.** The research turned up direct Indonesian precedent (ETP/UNOPS 2024 JAMALI 1 GW study did exactly this), strong academic backing (Ruiz et al. 2020 West Kalimantan; Metegam et al. 2026 CONUS), and a perfect analog at NREL (`reV` supply-curve module). Four refinements below will strengthen it further — none are structural fixes, all are worth doing before merging to main.

---

## What the Plan Gets Right

**1. The pivot from argmax-PVOUT to substation-anchored search is the correct diagnosis.** The "scattered high-suitability pixels with no contiguous developable area" failure mode is a known methodological problem in the MCDA literature (Metegam et al. explicitly call this out and apply Getis-Ord Gi* hot-spot detection as their fix). In humid-tropical Indonesia, Solargis reports ±8% GHI uncertainty and Ruiz et al. measured only ±8% variation across West Kalimantan — meaning 1-2% PVOUT deltas are smaller than measurement error. Optimizing for them is genuinely noise-chasing.

**2. The LCOE-proxy tiebreaker (Step 4) is the strongest element of the plan.** This matches NREL's `reV` supply-curve module, which "sorts developable sites based on both LCOE and transmission access… calculates grid interconnection costs for all potential links from developable sites to nearby transmission assets." Functionally identical. Also matches Sunarso et al. (2020, W. Kalimantan) and IFC's 2015 Project Developer's Guide framing of site selection as a **joint** screen rather than sequential. Best-in-class choice.

**3. The 10 km co-location radius is defensible and lands in the right cost band.** LBL's 3,382-project interconnection database shows $167/kW average solar interconnection cost. Thunder Said Energy's synthesis gives $3–10/kW-km over 10–70 km. At 10 km, expected gen-tie cost is ~$60-100/kW — well below the $200-300/kW (15-20% of CAPEX) developer kill threshold inferred from PJM withdrawn-project data. This is why the "Build Substation" false positive was appearing at 50 km but disappears at 10 km.

**4. The 30% meaningful-share floor as a screening filter is sensible.** Not formally standardized in any IRENA/NREL reference, but falls within the 30-70% range of typical corporate PPAs globally and above India's 51% group-captive floor. Defensible as a "this project is big enough to bother with" filter.

**5. The fallback flag (`solar_search_method = "best_pvout_fallback"`) is a correct UX choice.** It preserves honesty — "the site got 'Build Substation' because we couldn't find any anchored alternative" is a very different claim from "the site got 'Build Substation' because we didn't look." Keeping both paths in the output makes the methodology auditable.

**6. Preserving the 5 km classification threshold while using 10 km as the search radius is the right call.** Two different concepts, two different constants. Mixing them would have broken the downstream `grid_integration_category()` contract unnecessarily.

**7. Demand-sized sizing (`required_mwp = annual_demand / (8760 × CF)`) is appropriate for a dashboard that pairs specific industrial sites with specific solar plants.** Generic MW tranches (50/100/500) would be wrong here because the whole point is matching supply to a named demand node.

---

## Four Improvement Actions Before Shipping

### Action 1: Replace the flat 15 km search radius with a geography-tiered radius

**The issue:** Norton Rose Fulbright's Indonesia renewables briefing states bluntly that *"it is common for the transmission corridor to be 20 to 40 kilometres long"* for Indonesian IPPs. Inter-substation spacing varies enormously by island:

| Region | Inter-substation spacing | Applies to |
|---|---|---|
| Jakarta-Bekasi industrial corridor | <10 km | Dense Java industrial estates |
| Java-Bali industrial belt | 15–30 km | Cikarang, Serang, Gresik |
| Sumatra 150kV radials | 15–40 km | Dumai, Medan, Palembang |
| Kalimantan / Sulawesi | 40–100 km | IMIP Morowali, IWIP Weda Bay, Obi |
| Maluku / Papua | Captive-only, no PLN backbone | Most nickel industrial parks |

A flat 15 km radius will trigger the best-PVOUT fallback for **most sites in Sulawesi, Kalimantan, Maluku, and Papua** — which is precisely where the highest-CBAM-exposed facilities are (nickel, aluminum). The fallback label then undermines the tool's credibility for exactly the users (roadmap planners, DFI investors in Eastern Indonesia) who need it most.

**What to change:** Introduce a region-aware search radius constant. Add to `src/assumptions.py`:

```python
# Geography-tiered substation search radius based on observed
# inter-substation spacing and gen-tie corridor practice
# Source: Norton Rose Fulbright (2020) Indonesian Power Projects;
# PLN RUPTL 2024; ETP/UNOPS 2024 JAMALI study
KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM = {
    "JAMALI": 15,        # Java-Madura-Bali, dense grid
    "Sumatra": 25,       # Sumatra 150kV radials
    "Kalimantan": 30,    # Sparser grid
    "Sulawesi": 30,      # Sparser grid, many captive
    "Maluku_Papua": 40,  # Mostly captive; generous radius
}
KEK_TO_SUBSTATION_RADIUS_DEFAULT_KM = 15  # fallback if region unknown
```

Determine region from the existing grid region classification (`bpp_grid_region` or similar in the scorecard). Document that the geography-tiered radius is **only** for the search step; classification thresholds remain unchanged at 5 km.

**Why this is Action 1:** It has the largest effect on which sites benefit from the fix. Without it, the whole methodology change delivers value for Java but misses half of Indonesia's industrial emissions.

---

### Action 2: Add a crude substation hosting-capacity proxy

**The issue:** Every developer-facing source — Carsey/NCSP, SunShare, PSU Extension, Searchland — treats substation hosting capacity (available MVA) as a **primary** early-stage screen, not a distance proxy. From SunShare: *"Constraints on the infrastructure (e.g. if there are too many solar projects interconnecting to the same substation) can also halt a project, even if the proximity is ideal."* The ETP/UNOPS JAMALI study explicitly used a substation hosting-capacity gate.

Without this, the algorithm will confidently recommend a solar plant next to a substation that is already fully subscribed. This is arguably a worse false positive than the "Build Substation" false negative the plan fixes.

**What to change:** PLN does not publish substation-level hosting capacity. Use a simple proxy — voltage class × transformer capacity × assumed headroom. Add to `src/pipeline/build_fct_substation_proximity.py`:

```python
# Crude hosting capacity proxy per substation
# Based on voltage class and typical transformer sizing
SUBSTATION_HOSTING_CAPACITY_PROXY_MVA = {
    "500 kV": 500,   # Extra-high voltage, backbone
    "150 kV": 60,    # Typical industrial/regional
    "70 kV":  20,    # Sub-transmission
    "20 kV":   5,    # Distribution-level
}
# Assume 30% of nameplate is available for new solar injection
# (rest is loaded with existing demand + safety margin)
HOSTING_CAPACITY_AVAILABILITY_PCT = 0.30
```

For each candidate substation in Step 3, compute `available_mw_proxy = nameplate_mva * 0.30`. Reject candidates where `required_mwp > available_mw_proxy`. Surface this in `fct_substation_proximity.csv` as a new column `substation_hosting_capacity_mw_proxy` with a docstring flagging it as "proxy only — PLN does not publish actual loading data; conservative 30% assumption."

Document in the methodology that this is a *bankability screen*, not a physical assertion. If PLN ever publishes real hosting-capacity data, this proxy gets replaced.

**Why this matters for the roadmap team:** A DFI analyst cannot take a "grid_ready" recommendation to an investment committee if the substation is fully subscribed. This field is what makes the output actually financeable.

---

### Action 3: Clarify nameplate-sized share vs delivered-energy share in the UI

**The issue:** At Indonesia's typical ~17% capacity factor, `required_mwp = annual_demand / (8760 × CF)` implies a solar plant sized to roughly 1.3–1.8× peak industrial load. For a continuous 24/7 nickel smelter without storage or export, midday solar will over-generate and **effective offtake caps at ~17-20% of annual energy**. The 30% "meaningful share" threshold is actually a nameplate-based screen, not a delivered-energy claim.

This is not a bug — it's the right screening threshold — but the dashboard UI needs to not overstate decarbonization impact. A user seeing "covers 30% of demand" will reasonably interpret that as 30% Scope 2 reduction.

**What to change:** Add a second computed field alongside `solar_supply_share_pct`:

```python
# In fct_site_resource.csv output
solar_supply_share_pct        # nameplate / required_mwp (existing)
solar_delivered_share_pct     # new: approximates actual energy delivered
                              # without storage or export
```

Compute `solar_delivered_share_pct = min(solar_supply_share_pct, CF/load_factor)` as a screening approximation. In the ScoreDrawer's overview tab, show both:

> "Nameplate covers 30% of annual demand. Without storage or export, actual energy delivered ≈ 17%. Storage or wheeling regulation would close this gap."

Add a one-line methodology footnote citing that full coverage requires behind-the-meter consumption within a Wilayah Usaha, export under Perpres 112/2022, or storage — none of which is free.

**Why this matters for Persona 6 (Roadmap Planner):** Aggregating site-level "30% covered" across 81 sites into a national decarbonization figure would overstate achievable Scope 2 reduction by ~2x. Making this explicit in the data model prevents that error at the source.

---

### Action 4: Distinguish IPP vs captive regime in the output labeling

**The issue:** Indonesia lacks a power-wheeling regulation. A solar plant built 15 km from a factory cannot freely sell to that factory through PLN's grid. Two economically distinct regimes govern what's actually buildable:

| Regime | Scale ceiling | Regulatory basis | Economics |
|---|---|---|---|
| Co-located captive | 100s of MW physical limit | Behind-the-meter within Wilayah Usaha | No PLN tariff; capex + OpEx only |
| Grid-connected IPP | 30-50 MWp realistic under PLN single-buyer | Perpres 112/2022 ceiling tariffs | PLN PPA required; ceiling tariff caps LCOE |

The current plan treats both as "solar next to industrial site." For Batam Aero Technic (a commercial site that needs grid-connected supply), the IPP constraints apply. For IMIP Morowali (a captive industrial estate), different rules apply. Same spatial analysis, very different buildable outcomes.

**What to change:** Add a new column to the scorecard:

```python
# In fct_site_scorecard.csv
solar_regime     # enum: "co_located_captive" | "grid_connected_ipp" | "unclear"
```

Heuristic for populating:
- Site is in a gazetted industrial estate (KEK or Kawasan Industri) AND anchor solar patch is within estate boundary → `co_located_captive`
- Site is outside an industrial estate OR anchor patch is outside estate boundary → `grid_connected_ipp`
- Other cases → `unclear` (flag for manual review)

Surface this in the ScoreDrawer's regulatory/economics tab. For `grid_connected_ipp` cases, apply Perpres 112/2022 ceiling tariff as an upper bound on the LCOE that PLN will actually pay.

**Why this matters:** It's the difference between "you can build this" and "you can build this and it's financially viable under current Indonesian regulation." The dashboard should not conflate the two.

---

## Optional: Two Smaller Nice-to-Haves

**Split the fallback reason.** Currently `solar_search_method = "best_pvout_fallback"` lumps together two different failure modes:
- (a) No substation within the search radius at all → *transmission gap, grid expansion needed*
- (b) Substation exists within radius, but insufficient buildable land within 10 km of it → *land-use conflict, unlock via exclusion review*

These have different policy implications. Split into `fallback_no_substation_in_range` and `fallback_no_buildable_near_substation`. Two extra string values, zero logic complexity.

**Add a network upgrade adder to the LCOE proxy.** LBL's 2023 data shows ~75% of total interconnection cost comes from network upgrades beyond the point of interconnection, not the spur line itself. Your current formula only captures the spur line. Consider adding a second cost term like `network_upgrade_cost_per_kw` (could be a flat $50-100/kW placeholder, or scaled by project MWp relative to substation capacity proxy from Action 2). Not urgent for v1 of the fix, but worth documenting as a known conservative bias in current LCOE outputs.

---

## Summary of Deltas from Original Plan

| # | Change | Files | Effort |
|---|---|---|---|
| 1 | Geography-tiered search radius dict + region lookup | `assumptions.py`, `build_fct_site_resource.py` | Low |
| 2 | Hosting-capacity proxy + screening reject | `build_fct_substation_proximity.py`, `assumptions.py` | Medium |
| 3 | `solar_delivered_share_pct` column + UI footnote | `build_fct_site_resource.py`, `ScoreDrawer/OverviewTab.tsx`, methodology doc | Low |
| 4 | `solar_regime` enum + Perpres 112 ceiling in IPP cases | `build_fct_site_scorecard.py`, `ScoreDrawer/EconomicsTab.tsx` | Medium |

All four are additive (new columns, new logic branches) rather than destructive. They don't invalidate any existing tests; they require new test cases in `TestSubstationAnchoredSearch`.

## Sources Backing This Review

**Indonesian precedent:** ETP/UNOPS (2024) *1 GW Solar Mapping and Development Plan (Indonesia)*; Ruiz et al. (2020) *GIS-Based Assessment of Utility-Scale Solar PV Plants in West Kalimantan* (MDPI Sustainability); Sunarso et al. (2020) *GIS-AHP Multi-Decision-Criteria Analysis for Solar Energy Plants at Indonesia*; Norton Rose Fulbright (2020) *Indonesian Power Projects: Ten Things to Know*.

**International practice:** IFC (2015) *Utility-Scale Solar PV: A Project Developer's Guide*; NREL `reV` model documentation; LBL interconnection cost database (Seel et al. 2023); Thunder Said Energy tie-in cost synthesis; Metegam et al. (2026) *Solar farm suitability mapping for the Contiguous United States*.

**Academic framing:** Spyridonidou & Vagiona (2023) *Systematic review of GIS-MCDA for renewable energy siting*; Al Garni & Awasthi (2017) *Solar PV site selection GIS-AHP Saudi Arabia*; Sabo et al. (2017) *Large-scale PV siting in Peninsular Malaysia* (Applied Energy); Bani-Mustafa et al. (2026) *GIS-based spatial modeling for PV solar farm suitability in Syria*.