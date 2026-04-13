# Physics vs. Tool: Technical Gaps from MacKay's Framework

Comparing the physical principles from "Sustainable Energy Without the Hot Air" against your METHODOLOGY_CONSOLIDATED.md to identify where the tool's logic doesn't fully reflect physical reality.

---

## Gap 1: Solar Supply Coverage Ignores Temporal Mismatch (SIGNIFICANT)

**The physics (MacKay Ch. 26):** Solar produces during ~10 hours of daylight. Industrial smelters consume 24 hours. Even if total annual solar MWh equals total annual demand MWh, half the energy arrives when you don't need extra (daytime) and none arrives when you do (nighttime). Matching total energy is necessary but not sufficient — you must also match the timing.

**What your tool does:** Section 11's `solar_supply_coverage` divides total annual solar generation by total annual demand. A coverage of 100% means "solar produces enough energy across the year." But your own caveat acknowledges: "Does not account for temporal mismatch (solar is daytime-only without storage)."

**The problem:** A KEK showing 100% solar supply coverage might actually need 60-70% of that energy stored and time-shifted to nighttime. The storage cost for that is enormous. Without accounting for this, the supply coverage metric overstates solar's ability to replace baseload power. A user might see "100% coverage" and think "solar can fully power this KEK" when in reality it can only do so with $hundreds of millions in batteries.

**Recommendation:** Add a "firm supply coverage" metric alongside the current one:

```
firm_solar_coverage = solar_daytime_generation / demand_daytime
night_gap_mwh = demand_nighttime - 0  (solar produces nothing at night)
storage_needed_mwh = night_gap_mwh × (1 / round_trip_efficiency)
```

Or simpler: add a note/field showing "of this X% coverage, Y% requires storage to be usable." Even a rough split (e.g., assume 10h production / 14h gap, so ~58% of daily demand occurs when solar isn't producing) would ground the metric in physical reality.

**Priority:** P1 — this is conceptually important for credibility with technical reviewers. The current caveat text is honest but the metric itself is still misleading without a companion indicator.

---

## Gap 2: BESS Sizing Doesn't Reflect Physical Demand Profile (MODERATE)

**The physics (MacKay Ch. 26):** Storage sizing depends on how long you need to bridge the gap between supply and demand. A 100 MW smelter running 24/7 with solar-only supply needs to store roughly 14 hours × 100 MW = 1,400 MWh to get through the night. That's the physical minimum, before accounting for cloudy days, round-trip losses, and multi-day weather events.

**What your tool does:** BESS sizing is fixed at 2 hours per kW of solar (`BESS_SIZING_HOURS = 2.0`). For a 100 MW solar installation, that's 200 MWh of storage. This is a standard "grid-support" BESS sizing — enough to smooth a few hours of cloud cover, NOT enough to bridge a 14-hour overnight gap.

**The problem:** Your `invest_battery` flag fires when `reliability_req >= 0.75`, signaling that storage is needed alongside solar. But the BESS cost adder in the LCOE uses 2h sizing regardless of the demand profile. For a 24/7 nickel RKEF smelter, the actual storage need is 7-10x higher than what your model costs. The LCOE with battery is therefore significantly understated for high-reliability industrial loads.

A 2h BESS at $250/kWh adds ~$43/MWh to LCOE. A physically realistic 10-14h BESS would add ~$215-300/MWh — completely changing the economics and likely flipping many KEKs from "competitive with battery" to "not competitive."

**Recommendation:** Two options:

Option A (simple): Add the "high-reliability" multiplier we discussed. When `reliability_req >= 0.75`, multiply BESS sizing by a factor (user-adjustable, default 5x) to approximate overnight bridging. This is crude but directionally honest.

Option B (better): Make BESS sizing a function of the demand-supply timing gap. At 18% CF, solar produces for ~10h/day on average. A 24/7 load needs 14h of bridging. BESS sizing = bridge_hours × load_MW. This creates a physically grounded BESS size that varies by KEK based on their demand profile.

**Priority:** P1 — the current 2h default is physically unrealistic for the industrial loads your tool targets. This is the gap most likely to be challenged by an energy economist or engineer reviewing the methodology.

---

## Gap 3: Panel Degradation Not in LCOE Denominator (KNOWN, MINOR)

**The physics (MacKay Ch. 6):** Solar panels degrade ~0.5% per year. Over 27 years, cumulative output is ~93-94% of what a constant-CF assumption would predict. Energy production declines year over year.

**What your tool does:** Your methodology doc acknowledges this: "LCOE is understated by ~6-7%. Standard for screening models (IEA, IRENA use the same simplification)."

**The problem:** Minor. Your LCOE is ~6-7% too optimistic. At $55/MWh, the corrected value would be ~$59/MWh. This could flip a KEK that's marginally competitive ($55 vs $63 tariff = 13% gap) to less competitive ($59 vs $63 = 6% gap). Won't change the action flags for clearly competitive or clearly uncompetitive KEKs, but affects the borderline ones.

**Recommendation:** This is already documented as a known limitation. If you want to fix it, adjust the denominator:

```
degraded_annual_output = CF × 8.76 × (1 - degradation/2 × lifetime)  # midpoint approximation
```

Or more precisely, sum the geometric series of degraded annual output over the lifetime. Low effort, small but real improvement in accuracy.

**Priority:** P2 — standard simplification, already documented. Fix when convenient but not urgent.

---

## Gap 4: Round-Trip Efficiency Not in BESS Model (MODERATE)

**The physics (MacKay Ch. 26):** Battery storage has round-trip efficiency of ~85-90%. For every 100 MWh you put in, you get 85-90 MWh out. The other 10-15% is lost as heat. This means you need to generate MORE solar than the demand gap — you need to oversize both the solar array and the battery to account for these losses.

**What your tool does:** The BESS formula calculates a cost adder but doesn't appear to account for round-trip efficiency losses. The storage cost is based on `sizing_hours × CAPEX × CRF`, divided by solar output. But the solar output in the denominator should be reduced by the round-trip loss for the portion that passes through storage.

**The problem:** If 50% of solar output needs to go through storage (nighttime bridging), and round-trip efficiency is 87%, then 6.5% of total solar output is lost to storage. That means you need 6.5% more solar panels to produce the same net delivered energy. LCOE is understated by this amount.

**Recommendation:** Add a round-trip efficiency parameter (default 87%) and adjust the effective solar output:

```
storage_fraction = nighttime_hours / 24  # ~0.58 for 14h night
efficiency_loss = storage_fraction × (1 - round_trip_efficiency)
effective_CF = CF × (1 - efficiency_loss)
```

At 18% CF: effective_CF = 0.18 × (1 - 0.58 × 0.13) = 0.18 × 0.925 = 0.166. LCOE increases by ~8%.

**Priority:** P1 — physically real, meaningful impact on LCOE, easy to implement.

---

## Gap 5: No Power Density Validation Against Buildable Area (MINOR)

**The physics (MacKay Ch. 6):** Solar power density is ~10 W/m² of land in Indonesia, or equivalently ~2-3 hectares per MW. This is a physical constraint — you can't squeeze more MW onto less land without changing panel technology.

**What your tool does:** Uses a fixed 1.5 ha/MW in the assumptions (`LAND_COST_USD_PER_KW = $45/kW` based on `$3/m² × 1.5 ha/MW`). But the methodology mentions power density from the ESDM Technology Catalogue without explicitly stating the ha/MW conversion used for `max_captive_capacity_mwp`.

**The problem:** If your tool uses 1.5 ha/MW for land cost but a different value for capacity calculation, there could be an internal inconsistency. The ESDM catalogue's power density might differ from the 2.5 ha/MW we discussed. At 1.5 ha/MW, you're assuming more panels per hectare than at 2.5 ha/MW, which would overestimate capacity for a given buildable area.

**Recommendation:** Verify that the ha/MW used in `max_captive_capacity_mwp` is consistent with the land cost calculation and with the ESDM catalogue's power density. Document the specific value and its source. If using the ESDM catalogue value, cross-check it against MacKay's first-principles derivation (~2-2.5 ha/MW for utility-scale ground-mount in the tropics).

**Priority:** P0 — quick check for internal consistency. May already be correct but worth verifying.

---

## Gap 6: No Reactive Power or Power Factor Consideration (MINOR FOR SCREENING)

**The physics:** Industrial loads (motors, smelters, compressors) consume reactive power in addition to real power. A substation's capacity is rated in MVA (apparent power = real power + reactive power), not MW (real power only). A substation rated at 60 MVA serving loads with a power factor of 0.85 can only deliver ~51 MW of real power. The remaining capacity handles reactive power.

**What your tool does:** Section 8.4 uses `available_capacity_mva` directly compared against solar capacity in MWp. But solar injection is mostly real power (power factor ~1.0) while the substation's existing load draws reactive power (power factor ~0.8-0.9). The available headroom for solar injection isn't simply `rated_mva × (1 - utilization)` — it depends on the power factor of the existing load and the power factor of the solar injection.

**The problem:** Minor for screening. Your traffic light system already uses broad categories (green = 2x capacity, yellow = 0.5-2x, red = <0.5x). The power factor correction would shift the numbers by maybe 10-15%, which rarely changes the traffic light color. But if someone does a detailed feasibility study based on your capacity assessment, the MVA vs MW distinction matters.

**Recommendation:** Add a note in the methodology that MVA ≠ MW, and that actual injection capacity depends on power factor. For a more precise model, multiply available MVA by an assumed power factor (0.85-0.90) to get available MW. Low effort, improves technical accuracy without changing the model structure.

**Priority:** P2 — doesn't affect screening results materially but strengthens technical credibility with power engineers.

---

## Gap 7: The Balance Sheet Isn't Explicit (CONCEPTUAL)

**The physics (MacKay Ch. 2):** MacKay's core methodology is the explicit balance sheet — red column (demand) vs green column (supply), both in the same units, for every location. The gap between them IS the answer.

**What your tool does:** Your tool implicitly calculates both sides but doesn't present them as a balance sheet to the user. The supply side is `max_captive_capacity_mwp` and LCOE. The demand side is `demand_mwh_2030` (area proxy). The gap is `solar_supply_coverage`. But these numbers appear in different tabs of the Score Drawer (Resource tab vs Demand tab) rather than as an explicit side-by-side comparison.

**The problem:** This isn't a calculation error — it's a presentation gap. A policymaker looking at the Score Drawer sees supply metrics in one place and demand metrics in another. MacKay's lesson is that presenting them SIDE BY SIDE, in the same units, is what creates the "aha moment." "This KEK needs 500 GWh/year. Solar can provide 200 GWh/year. The gap is 300 GWh/year. That gap requires either grid imports, storage, or other generation."

**Recommendation:** Add a simple "Energy Balance" visualization to the Score Drawer — a stacked bar or two-column chart showing demand (one bar) vs solar supply (another bar), with the gap explicitly labeled. Optional: break the solar supply bar into "daytime direct use" and "requires storage" segments to address Gap 1 simultaneously.

**Priority:** P1 for presentation/UX. The data already exists. This is a frontend addition that would make the tool's output much more intuitive, especially for the policymaker and tenant personas.

---

## Gap 8: Transmission Loss Not in LCOE (NEGLIGIBLE)

**The physics (MacKay):** Electricity loses ~7% per 1,000 km on HVAC lines, ~3% on HVDC. Over 5-15 km gen-tie distances, losses are ~0.1-0.5%. Negligible at your tool's scale.

**What your tool does:** Doesn't model transmission losses in the LCOE or solar supply calculations.

**The problem:** At the distances your tool operates (5-40 km), transmission losses are <1%. This rounds to zero in LCOE terms (maybe $0.30/MWh on a $55/MWh LCOE). Not worth modeling.

**Recommendation:** None. Correctly omitted. Add a one-line note in the methodology: "Transmission losses over gen-tie distances (<40 km) are <1% and excluded from LCOE calculations."

**Priority:** None — already handled correctly by omission.

---

## Summary: Priority-Ranked Gaps

| # | Gap | Physics Impact | LCOE Impact | Priority |
|---|---|---|---|---|
| 1 | Solar supply coverage ignores temporal mismatch | High — 58% of demand occurs when solar produces zero | Metric is misleading, not LCOE | P1 |
| 2 | BESS sizing unrealistic for 24/7 industrial loads | High — actual storage need is 5-7x the 2h default | LCOE understated by $170-250/MWh for high-reliability loads | P1 |
| 4 | Round-trip efficiency not in BESS model | Moderate — 6-8% of solar output lost to storage cycling | LCOE understated by ~8% when storage is included | P1 |
| 7 | Balance sheet not presented explicitly to user | None (calculation exists) — presentation gap | None | P1 (UX) |
| 5 | Power density ha/MW internal consistency check | Low — may be correct already | Depends on finding | P0 (quick check) |
| 3 | Panel degradation not in LCOE | Low — ~6-7% LCOE understatement | Known, documented, standard simplification | P2 |
| 6 | Reactive power / power factor not in capacity check | Low — ~10-15% capacity overestimation | Rarely changes traffic light | P2 |
| 8 | Transmission losses not modeled | Negligible at gen-tie distances | <$0.30/MWh | None |

---

## The Most Important Takeaway

**Gaps 1 and 2 are connected and they're your biggest physics vulnerability.** The tool currently says "this KEK has 100% solar supply coverage" and prices BESS at 2h sizing ($43/MWh adder). The physical reality is that 100% coverage with 24/7 industrial demand requires ~14h of storage, which costs $215-300/MWh — roughly 5-7x what the tool shows.

This means your `invest_battery` flag and `lcoe_with_battery` metric systematically underestimate the true cost of firming solar for high-reliability industrial loads. An energy economist reviewing this would immediately flag it.

The fix doesn't require hourly dispatch modeling. It just requires making BESS sizing proportional to the gap between solar production hours and demand hours, rather than fixed at 2h. A simple formula:

```
bridge_hours = 24 × (1 - solar_production_hours/24)  # ~14h for 10h solar
bess_sizing = bridge_hours × load_mw × (1 / round_trip_efficiency)
```

This is still parametric, still user-adjustable, but physically grounded. It would make the tool's battery cost estimates honest without requiring Balmorel-level complexity.
