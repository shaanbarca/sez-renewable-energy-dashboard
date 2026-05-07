# Feature Spec: v4.0 Dashboard Methodological Fixes

**Theme:** Close 13 methodological gaps in the currently-shipped v4.0 dashboard against the wiki's accumulated framework. These are issues with the codebase as it sits today, not the v4.1 architectural refactor.

**Why this ships in parallel with v4.1:** Several fixes carry forward into v4.1 multi-tier outputs (geothermal proximity, regulatory variable, curtailment cost), so closing them now avoids methodological debt. Several others are 1-line corrections that don't need to wait. v4.1 lands cleaner if v4.0 is methodologically consistent first.

**Effort:** ~5–7 focused work days aggregate. Several findings are 1-line or half-day changes; the heavier ones are the geothermal proximity dataset (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4)) and the RUPTL §V.11 feasibility check (Finding 5, [#7](https://github.com/shaanbarca/eez/issues/7)).

**Status:** Ready for implementation in parallel with v4.1.

**Sources:**
- Findings 1–13 of [Indonesia Dashboard Methodology Review] (in `syntheses/`)
- `dashboard/METHODOLOGY_CONSOLIDATED.md` (V3.7) — the existing methodology this spec amends
- The wiki framework: `syntheses/Powering 24-7 Industrial Loads in Indonesia.md`, `syntheses/Indonesia Grid Infrastructure and Renewable Adoption.md`, `concepts/Geothermal Power.md`, `concepts/Energy Storage and Grid Fluctuations.md`

---

## What This Release Addresses

This release closes 13 methodological gaps in the currently-shipped v4.0 dashboard, surfaced by [[Indonesia Dashboard Methodology Review]]. Findings group into 5 themes. Each link below jumps to the detailed section covering methodology, default assumptions, implementation, and validation.

### 1. Solar / wind / storage methodology — 4 changes

*Methodological consistency around how solar, wind, and storage are modeled.*

| Section | What's changing | Why |
|---|---|---|
| [§2.1 Reframe pure solar+12hr battery as sanity-check baseline](#21-reframe-pure-solar12hr-battery-as-sanity-check-baseline-finding-1) (F1) | Demote `bess_competitive` from primary signal; extend Supply Blend cascade with dispatchable RE layer between within-boundary captive and remote IPP | Pure solar+battery is the wiki's scenario 3 sanity-check baseline, not a candidate architecture for Indonesian industrial loads (~3× cost vs captive coal). Flagging as primary misleads users — the real question is "what's the cost-optimal hybrid architecture." |
| [§2.3 Wind nighttime fraction tiered by region](#23-wind-nighttime-fraction-tiered-by-region-finding-3) (F3) | Replace uniform `nighttime_fraction = 0.583` with region-specific values (NTT 0.42 → Kalimantan 0.60) | Uniform fraction is structurally biased — too pessimistic for NTT/Sulawesi sea-breeze sites (afternoon wind strengthens), too generous for equatorial doldrums. Biases the hybrid optimizer's BESS-reduction output. |
| [§2.4 Apply solar lifecycle emissions correction](#24-apply-solar-lifecycle-emissions-correction-finding-4) (F4) | One-line denominator fix in `carbon_breakeven_price()`: `(grid_EF − 0.040)` | Methodology §9.2 already documents the ~5–8% optimism (40 gCO₂/MWh lifecycle per IPCC AR6) but doesn't apply it. Documenting an error ≠ fixing it; one-line change closes a credibility gap energy-economist reviewers would notice immediately. |
| [§3.6 Hybrid binding-constraint signal](#36-hybrid-binding-constraint-signal-finding-10) (F10) | Per-site `hybrid_binding_constraint` field with narrative — *"60/40 solar/wind today; flips to 90/10 if BESS drops to $80/kWh"* | Optimizer picks the cost-minimum mix but doesn't expose what flips it. Developers and policy analysts need to know where the marginal lever is — BESS cost vs WACC vs storage duration are different interventions. |

### 2. Spatial dispatchable RE access — 1 change

*Add geothermal as a spatial variable. The highest-leverage missing dimension for Sulawesi/Maluku nickel decarbonization.*

| Section | What's changing | Why |
|---|---|---|
| [§2.2 Geothermal proximity matching](#22-geothermal-proximity-matching-finding-2) (F2) | Add `nearest_geothermal_operating_*`, `nearest_geothermal_pipeline_*`, `geothermal_adjacency_tier` columns; source from ESDM Tech Catalogue 2024 §1 (18 sites) + RUPTL Tabel 3.2/3.3 (5,157 MW pipeline) | Geothermal is invisible as a spatial variable in v4.0 — captive coal and nickel get spatial proximity treatment but geothermal doesn't. ~60% of unbuilt potential is on islands not grid-connected; the wiki's Morowali recipe (build solar+battery now, parallel-track geothermal for scenario 6 by 2032+) is currently unreachable from the dashboard. |

### 3. Grid infrastructure & captive power — 5 changes

*Reality-check grid-extension comparators; treat regulatory variables as variables, not status strings.*

| Section | What's changing | Why |
|---|---|---|
| [§3.1 RUPTL §V.11 grid-extension feasibility check](#31-ruptl-v11-grid-extension-feasibility-check-finding-5) (F5) | Build `fct_transmission_link_ruptl_signal.csv`; flip comparator to captive economics when link is `kajian lebih lanjut` (further study) | RUPTL grid investment is ~5–6× short of IEA APS implied need. For sites whose transmission link sits in §V.11.2, the realistic comparator is captive economics, not PLN tariff. "Solar competitive vs PLN" verdict is silently optimistic for sites depending on transmission PLN can't fund. |
| [§3.2 Perpres 112/2022 as regulatory variable](#32-perpres-1122022-as-regulatory-variable-finding-6) (F6) | Replace `perpres_112_status` string with structured columns (`captive_perpres_112_exempt`, `captive_phaseout_year_baseline`, `captive_phaseout_year_strict_scenario`) | The strategic-industry exemption is the single most consequential regulatory lever in Indonesian industrial decarbonisation. v4.3 will add it as a pathway dimension; v4.0.5 puts the data structure in place so v4.3 doesn't refactor. |
| [§3.3 RUPTL → demand → RUPTL feedback loop](#33-ruptl--demand--ruptl-feedback-loop-finding-7--deferred-to-v44) (F7) — deferred | Documentation only in v4.0.5: flag the static-RUPTL assumption in METHODOLOGY §13 and §A.1 | Dashboard treats RUPTL adds as fact, but PLN sizes contracts conditional on demand growth (Take-or-Pay risk per §III.2.1). Long-horizon scenario 6 availability is a best-case upper bound. Flagging now (full modeling deferred to v4.4) prevents users misreading static projections as guarantees. |
| [§3.4 Curtailment cost in supply blend](#34-curtailment-cost-in-supply-blend-finding-8) (F8) | Add `curtailment_loss_pct` per site; apply as CF haircut for grid-connected scenarios | IEA APS projects curtailment provides ~25% of Indonesia's seasonal flexibility by 2050. v4.0 caps overproduction physically but doesn't price the curtailed energy. For Maluku/Papua sites this is a 20–35% cost adder silently missing from grid-connected economics. |
| [§4.2 Captive matching: contractual + spatial](#42-captive-matching-contractual--spatial-finding-12) (F12) | Add `data/raw/captive_coal_contractual_overrides.csv` for Sumatran mine-mouth relationships beyond 50 km; override layer in `build_fct_captive_coal.py` | §13.2's haversine 50 km match misses long-distance captive arrangements (mine + dedicated rail/conveyor). Common in Sumatra. Relevant for stranded-asset analysis (v4.4) and accurate captive cost reference (v4.1 §4). |

### 4. CBAM & GEAS allocation — 2 changes

| Section | What's changing | Why |
|---|---|---|
| [§3.5 Scope 1 abatement options surfaced](#35-scope-1-abatement-options-surfaced-finding-9) (F9) | Add `scope1_abatement_pathways`, `scope1_abatement_indicative_addressable_pct` per site; flag alt fuels / green H₂ DRI / SCM substitution for cement/ammonia/BFBOF | v4.0's RE-addressable fractions (cement 0.12, ammonia 0.10, BFBOF 0.80) are right for *today's* technology stack. But green-H₂ DRI / alt fuels can take cement and ammonia from 10–12% relief to 50%+. Without flagging, the dashboard creates a static-ceiling misimpression. |
| [§4.3 GEAS empirical allocation alternative](#43-geas-empirical-allocation-alternative-finding-13) (F13) | Add `geas_alloc_empirical_gwh` alongside proportional default; user-toggleable via `geas_allocation_used` enum | §11's proportional-to-demand allocation isn't how PLN actually allocates. PLN's empirical pattern is urban-anchored, slower-rural — proportional baseline over-credits remote KEKs. Empirical scenario surfaces what's *likely to* happen vs what *should*. |

### 5. Documentation only — 1 change

| Section | What's changing | Why |
|---|---|---|
| [§4.1 MacKay citation correction](#41-mackay-citation-correction-finding-11) (F11) | Reframe BESS bridge-hours derivation as "first-principles physics" rather than citing MacKay Ch. 26 | MacKay Ch. 26 covers UK 5-day winter lulls, EV-as-storage, pumped hydro economics — not tropical industrial 14h overnight bridge. Math is right; citation is a stretch that weakens credibility with energy-economist reviewers. Let the math stand on its own. |

---

## Table of Contents

| §          | Section                                                      | Skip for Claude Code?       |
| ---------- | ------------------------------------------------------------ | --------------------------- |
| 1          | Strategic Context                                            | Yes (reference)             |
| 2          | Methodological Errors (Findings 1–4)                         | **No (build)**              |
|            | 2.1 Reframe pure solar+12hr battery as sanity-check baseline | **No (build)**              |
|            | 2.2 Geothermal proximity matching                            | **No (build)**              |
|            | 2.3 Wind nighttime fraction tiered by region                 | **No (build)**              |
|            | 2.4 Apply solar lifecycle emissions correction               | **No (1-line fix)**         |
| 3          | Structural Gaps (Findings 5–10)                              | **No (build)**              |
|            | 3.1 RUPTL §V.11 grid-extension feasibility check             | **No (build)**              |
|            | 3.2 Perpres 112/2022 as regulatory variable                  | **No (build)**              |
|            | 3.3 RUPTL→demand→RUPTL feedback loop (deferred to v4.4)      | **No (doc only)**           |
|            | 3.4 Curtailment cost in supply blend                         | **No (build)**              |
|            | 3.5 Scope 1 abatement options surfaced                       | **No (build)**              |
|            | 3.6 Hybrid binding-constraint signal                         | **No (build)**              |
| 4          | Refinements (Findings 11–13)                                 | **No (build)**              |
|            | 4.1 MacKay citation correction                               | **No (doc fix)**            |
|            | 4.2 Captive matching: contractual + spatial                  | **No (build)**              |
|            | 4.3 GEAS empirical allocation alternative                    | **No (build)**              |
| 5          | Output Schema Changes                                        | **No (build)**              |
| 6          | Validation Strategy                                          | **No (test cases)**         |
| 7          | Success Criteria                                             | **No (definition of done)** |
| 8          | To-Do List                                                   | **No (tasks)**              |
| 9          | Migration and Backwards Compatibility                        | **No (build)**              |
| Appendix A | Cross-reference matrix                                       | Yes (reference)             |

---

## 1. Strategic Context

The v4.0 dashboard ships with substantial methodological wins over the V1/V2 baseline:

- **M30 RE-addressable fraction correction** (cement 0.12, ammonia 0.10, steel BF-BOF 0.80) cleanly distinguishes Scope 1 from thermal-inclusive Scope 2.
- **V3.7 substation-anchored solar search** picks the lowest-LCOE buildable patch co-located with a substation, fixing the false `invest_substation` flag.
- **V3.9.1 buildout-footprint haircut** (default 0.20 for operating parks) accounts for vacant land earmarked for future factories.
- **V3.3 BESS bridge-hours physics** (14h overnight gap × 1/RTE) replaces the flat 2h firming adder.
- **V3.4 panel degradation** (midpoint approximation, ~7.2% LCOE increase) and **power factor correction** (substation MVA→MW, saves 15% phantom capacity).
- **V3.8 RUPTL-driven substation utilisation tiers** (uprate 85%, none 55%, unmatched 65%) instead of fleet-average.
- **Dual-mode CBAM detection** (KEK 3-signal + industrial direct) covering 68/81 sites.
- **V3.10/V3.11 Supply Blend cascade** (within-boundary captive → remote IPP → grid).
- **Provenance enforcement** at pipeline build time (`source_url` required for residual rows).

Against these wins, [Indonesia Dashboard Methodology Review] surfaces 13 methodological gaps that the wiki framework requires. They break into three groups:

- **Errors** (Findings 1–4): findings that produce the wrong answer at the model level — pure solar+12hr battery framed as a candidate rather than baseline; geothermal invisible as a spatial variable; wind nighttime fraction uniform 0.583; solar lifecycle correction documented but not applied.
- **Gaps** (Findings 5–10): findings the methodology doesn't address — no grid-extension feasibility check, regulatory pathway as static string only, RUPTL→demand feedback loop ignored, no curtailment cost in the supply blend, no Scope 1 abatement signal, no hybrid binding-constraint output.
- **Refinements** (Findings 11–13): findings that are basically right but could be sharper — MacKay citation, captive matching radius, GEAS proportional allocation idealised.

This spec covers all 13 fixes. Items deferred to later releases (Finding 7, [#9](https://github.com/shaanbarca/eez/issues/9)) are documented but not implemented in v4.0; the rest land in this release.

**Architectural principle:** every fix should be backwards-compatible at the schema level. New columns added; existing columns preserved. v4.1 builds on top of a methodologically consistent v4.0; no breaking changes to action flags, economic tier, or 2D classification.

---

## 2. Methodological Errors

### 2.1 Reframe pure solar+12hr battery as sanity-check baseline (Finding 1, [#3](https://github.com/shaanbarca/eez/issues/3))

**Why this matters.** §6.3 computes `lcoe_with_battery = solar + 14h BESS adder` and surfaces a `bess_competitive` boolean flagging when this exceeds grid cost. The math is correct as a lower bound. But for Indonesian industrial loads, pure solar + 12hr battery is the **sanity-check baseline** (scenario 3 in the wiki framework), not a candidate architecture. Modeling it as a primary signal will mislead users into thinking solar+battery is the headline solar question, when in reality the question is "what's the cost-optimal hybrid architecture for this site, with what mix of solar / dispatchable RE / grid backfill?"

The Supply Blend cascade (§5.4) is the right shape for delivered cost — within-boundary captive → remote IPP → grid backfill — but currently caps real-time solar at the daytime fraction with no dispatchable RE backbone. For sites with reachable geothermal or hydro, those layers should slot between solar and grid in the cascade.

**Methodology change.** Three coupled changes:

1. **Demote `bess_competitive`** from primary signal to secondary "what if storage costs collapse" sensitivity. Continue to compute the field; do not allow it to override action flags. Add to the action-flag priority chain only as an explicit toggle: `costBasis = "firmed_24_7_solar_only"` (a new CostBasis option that makes the firmed solar+battery LCOE the comparator).

2. **Extend Supply Blend cascade** to accept a dispatchable RE layer between within-boundary captive and remote IPP. New layer: `f_dispatchable_re` for sites where geothermal or hydro is within transmission reach (per the new tier columns landing in Finding 2 and the v4.1 hydro extension).

   Updated formula:
   ```
   daytime_cap   = SOLAR_PRODUCTION_HOURS / 24
   f_wb          = min(within_boundary_coverage_effective_pct, daytime_cap)
   f_disp_re     = min(dispatchable_re_coverage_pct, 1 − f_wb)  [NEW]
   headroom      = max(0, daytime_cap − f_wb − f_disp_re_daytime)
   f_remote      = headroom if gc_row exists else 0
   f_grid        = 1 − f_wb − f_disp_re − f_remote
   delivered     = f_wb·LCOE_wb + f_disp_re·LCOE_disp_re + f_remote·LCOE_gc + f_grid·grid_rate
   ```

   Where `dispatchable_re_coverage_pct` is the fraction of demand covered by reachable dispatchable RE (geothermal or hydro), capped at the architecture's economic ceiling for that site (typically 60–90% depending on resource scale and transmission availability). `LCOE_disp_re` is the blended LCOE of the dispatchable RE source(s).

3. **Document explicitly** in METHODOLOGY_CONSOLIDATED §5.4 and §6.3 that pure solar+battery is the sanity-check baseline, not the recommended path. Add a paragraph to §5.4 referencing the wiki's six-scenario architecture menu with the specific note that Scenario 3 (pure solar + 12hr battery) loses on cost everywhere except diesel-replacement sites.

**Implementation.**
- `src/dash/logic/scorecard.py::enrich_delivered_cost()` — extend cascade with `f_dispatchable_re` layer. Reads from new columns `geothermal_adjacency_tier` (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4)) and `hydro_adjacency_tier` (v4.1 extension).
- `src/dash/logic/cost_basis.py` — add `firmed_24_7_solar_only` to the CostBasis enum; default to `firmed` for `EnergyMode = overall`, `raw` otherwise (unchanged from current).
- METHODOLOGY_CONSOLIDATED.md update.

**Validation.** Sites with reachable geothermal (e.g., Java cement plants near Patuha pipeline) should show delivered-cost reduction of $5–15/MWh vs current cascade. Spot-check 3 such sites manually. `bess_competitive` continues to be computed for all sites; verify it no longer fires `solar_now` action.

**Effort.** ~1.5 days. Half a day for the cost-basis enum extension; one day for the cascade refactor + documentation.

---

### 2.2 Geothermal proximity matching (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4))

**Why this matters.** §13 matches captive coal and nickel within 50km but doesn't surface geothermal proximity. Per the wiki, ~60% of unbuilt geothermal potential sits on islands not grid-connected to demand centres, and Sulawesi (3 GW potential, 124 MW installed, 4% utilisation) is the worst-mismatched. For Morowali-class sites, the wiki's recipe is: build solar+battery now (scenario 4), parallel-track geothermal exploration (scenario 6 by 2032+). That recipe is unreachable from the dashboard because the spatial signal isn't computed.

This is the spatial parity finding for dispatchable RE — captive coal and nickel get spatial treatment; geothermal and hydro don't. Fix that here for geothermal; v4.1 covers hydro.

**New columns** on `dim_sites` (and joined through `fct_site_scorecard`):

| Column | Type | Description |
|---|---|---|
| `nearest_geothermal_operating_id` | str | Name of closest operating PLTP |
| `nearest_geothermal_operating_km` | float | Haversine distance (km) |
| `nearest_geothermal_operating_mw` | float | Capacity at that PLTP (MW) |
| `nearest_geothermal_operating_emission_factor_g_per_kwh` | float | Site-specific NCG emissions (Wayang Windu 73, Kamojang 73, Ulubelu 43, etc.); fallback 50 |
| `nearest_geothermal_pipeline_id` | str | Name of closest pipeline RUPTL geothermal addition |
| `nearest_geothermal_pipeline_km` | float | Haversine distance (km) |
| `nearest_geothermal_pipeline_mw` | float | Capacity of that addition (MW) |
| `nearest_geothermal_pipeline_target_year` | int | RUPTL-listed target COD year |
| `geothermal_adjacency_tier` | enum | `operating_within_50km` / `operating_within_200km` / `pipeline_within_200km_pre2030` / `pipeline_within_200km_post2030` / `none` |
| `geothermal_transmission_feasibility` | enum | `same_island_connected` / `same_island_grid_first` / `cross_island_unconnected` |

**Source data.**
- **Operating fleet:** ESDM Tech Catalogue 2024 §1 Table 1.5 (2,598 MW across 18 sites). Per-plant coordinates from PLN PLTP list + manual verification against Wikidata. NCG emission factors from ESDM 2024 §1 (Wayang Windu 73, Kamojang 73, Ulubelu 43; default 50 for unspecified plants).
- **Pipeline:** RUPTL 2025–2034 Tabel 3.2 (RE Base) and 3.3 (ARED) — 5,157 MW over 10 years. Geocode each row against the ESDM resource map. Where a plant name is given (e.g., "PLTP Wayang Windu Unit 2"), inherit coordinates from the operating-plant entry. Where only a working area is given (e.g., "PLTP Tampomas"), geocode the working-area centroid.

Both files in `data/raw/`:
- `data/raw/geothermal_operating.geojson`
- `data/raw/geothermal_pipeline.geojson`

Provenance: each feature carries `source_name`, `source_url`, `retrieved_date`. Pipeline-build raises if any feature is missing these.

**Implementation.**
- New pipeline file: `src/pipeline/build_fct_geothermal_proximity.py`. Reuses `proximity_match()` from `src/pipeline/geo_utils.py` (haversine + nearest-N).
- Tier logic in `src/model/geothermal_adjacency.py`:
  ```python
  def geothermal_tier(operating_km, pipeline_km, pipeline_year):
      if operating_km is not None and operating_km <= 50:
          return "operating_within_50km"
      if operating_km is not None and operating_km <= 200:
          return "operating_within_200km"
      if pipeline_km is not None and pipeline_km <= 200:
          return "pipeline_within_200km_pre2030" if pipeline_year < 2030 else "pipeline_within_200km_post2030"
      return "none"
  ```
- `geothermal_transmission_feasibility` checks the `regpln` column on both site and nearest plant; if same `regpln` AND `inter_substation_connected = True` between site's nearest substation and plant's nearest substation, mark `same_island_connected`. Otherwise `same_island_grid_first` or `cross_island_unconnected`.
- Map view: new toggleable layer "Geothermal (Operating)" with color-coded markers by emission factor; "Geothermal (Pipeline)" layer with target-year encoding.
- Score Drawer: new card in Pipeline tab showing geothermal adjacency, target year, and the architectural implication ("Scenario 6 viable from 2032+" or "No reachable geothermal").

**Validation.**
- Sulawesi sites (Morowali, Konawe, Lahendong-adjacent): expect `pipeline_within_200km_post2030` tier on the latter due to RUPTL Sulawesi adds (80 MW total over 10 years, mostly post-2030).
- Java sites near Patuha/Wayang Windu/Kamojang: expect `operating_within_200km` tier.
- Sumatra Riau Islands sites: expect `pipeline_within_200km_pre2030` tier from Sarulla/Lumut Balai pipeline adds.
- Spot-check 5 sites against the ESDM resource map; tier assignment should match manual review.

**Effort.** ~2 days. Half a day for raw data compilation; half a day for pipeline; half a day for tier logic + tests; half a day for map + scorecard surfacing.

---

### 2.3 Wind nighttime fraction tiered by region (Finding 3, [#5](https://github.com/shaanbarca/eez/issues/5))

**Why this matters.** §6A.2 sets wind `nighttime_fraction = 14/24 ≈ 0.583` uniformly. For Indonesia specifically, this is too pessimistic for the few wind-resource sites (NTT, sea-breeze regions where afternoon wind strengthens) and too generous for the equatorial-doldrums majority. The hybrid optimizer's "wind reduces BESS by X" output is structurally biased.

**Methodology change.** Tier the constant by region, calibrated against Global Wind Atlas v3 hourly profiles:

```python
WIND_NIGHTTIME_FRACTION_BY_REGION = {
    "NTT": 0.42,                  # Strong afternoon sea-breeze cycle
    "Sulawesi_coastal": 0.45,     # Sulawesi Selatan, Sulawesi Tenggara coastal sites
    "Maluku_Papua": 0.48,         # Mixed; some monsoon-night dominance
    "Sumatera": 0.55,             # Mixed monsoon profile
    "JAMALI": 0.58,               # Java-Bali, mixed
    "Kalimantan": 0.60,           # Doldrums-dominated, some nighttime monsoon
    "default": 0.583,             # Conservative legacy value for unmatched regions
}
```

**Calibration source.** Sample 5 sites per region from Global Wind Atlas v3 hourly mesoscale data (or equivalent ERA5 reanalysis 100m wind speed). Compute `mean_nighttime_CF / mean_24h_CF` per site, then per-region average. Document calibration in METHODOLOGY_CONSOLIDATED §6A.2.

**Implementation.**
- New constant in `src/assumptions.py`: `WIND_NIGHTTIME_FRACTION_BY_REGION`.
- Update `RESource(technology="wind", ...)` instantiation in `src/dash/logic/technology.py::compute_hybrid_metrics()` to look up region-specific fraction by `regpln` (or a sub-region mapping for NTT-vs-Sulawesi distinction).
- Validation test in `tests/test_hybrid_lcoe.py`: optimizer with NTT inputs produces wind share ≥10pp higher than with default fraction.

**Validation.** Re-run hybrid optimizer for NTT sites. Expected effect: wind share rises 5–10pp at the optimum; BESS reduction increases ~10–15%. Spot-check Bitung (Sulawesi) and Sumba (NTT). For doldrums regions (Kalimantan), expect mild downward shift in wind contribution.

**Effort.** ~0.5 day code + 0.5 day calibration. The calibration depends on Global Wind Atlas hourly data availability; if not licensed, fall back to literature defaults from IEA Wind Annex 80 reanalysis benchmarks for SE Asia.

---

### 2.4 Apply solar lifecycle emissions correction (Finding 4, [#6](https://github.com/shaanbarca/eez/issues/6))

**Why this matters.** §9.2 caveats that the carbon-breakeven formula assumes zero solar lifecycle emissions when actual is ~40 gCO₂/MWh per IPCC AR6. The methodology says breakeven prices are "5–8% too optimistic" but doesn't apply the correction. Currently documenting an error rather than fixing it.

**Methodology change.** One-line denominator correction in `carbon_breakeven_price()`:

```python
SOLAR_LIFECYCLE_EF_TCO2_PER_MWH = 0.040  # IPCC AR6, crystalline silicon LCA
WIND_LIFECYCLE_EF_TCO2_PER_MWH = 0.013   # IPCC AR6, onshore wind LCA

def carbon_breakeven_price(lcoe, grid_cost, grid_emission_factor, technology="solar"):
    if lcoe <= grid_cost:
        return 0.0
    lifecycle_ef = SOLAR_LIFECYCLE_EF_TCO2_PER_MWH if technology == "solar" else WIND_LIFECYCLE_EF_TCO2_PER_MWH
    delta_ef = max(grid_emission_factor - lifecycle_ef, 1e-3)
    return (lcoe - grid_cost) / delta_ef
```

**Source.** IPCC. (2022). *Climate Change 2022: Mitigation of Climate Change. Contribution of Working Group III to the Sixth Assessment Report*. Annex III: Lifecycle GHG emission factors. Solar PV crystalline silicon median: ~40 gCO₂/kWh. Onshore wind median: ~13 gCO₂/kWh.

**Implementation.**
- One-line constant additions in `src/assumptions.py`.
- Update `carbon_breakeven_price()` in `src/model/basic_model.py` and `src/dash/logic/scorecard.py::enrich_grid_passthroughs()`.
- Update fixture: regression test fixture for scorecard golden file shifts ~5–8% on `carbon_breakeven_usd_tco2` and `wind_carbon_breakeven_usd_tco2`. Re-record fixture.
- METHODOLOGY_CONSOLIDATED §9.2 update: remove the "documented but not applied" caveat; replace with a one-paragraph note that solar lifecycle is now subtracted.

**Validation.** All 81 sites' carbon breakeven values shift ~5–8% upward (more conservative). Per-site delta should be uniform within a grid region (since `grid_EF` is regional). Regression test fixture updated.

**Effort.** Half a day. The longest part is updating the regression fixture; the code change is one constant + one denominator.

---

## 3. Structural Gaps

### 3.1 RUPTL §V.11 grid-extension feasibility check (Finding 5, [#7](https://github.com/shaanbarca/eez/issues/7))

**Why this matters.** §8 computes infrastructure costs (gen-tie, new transmission, substation upgrade) on the *solar* side and compares to PLN BPP / I-4 tariff. But the wiki's grid synthesis identifies the ~5–6× grid-investment gap (RUPTL plans $2.4B/y on transmission; IEA APS implies need for ~$15B/y). The comparator grid the dashboard assumes won't always be there.

For sites where the comparison logic recommends "build $X of new transmission to connect this site," the dashboard should cross-check: *is this transmission link in RUPTL §V.11?* If the link is `kajian lebih lanjut` (further study), the realistic comparator isn't PLN tariff — it's continued captive economics.

**New data source.** Extend the existing `fct_substation_ruptl_signal` pattern to inter-substation links. Build `fct_transmission_link_ruptl_signal.csv` from RUPTL §V.11.1–V.11.3 (p. 320–326):

| Column | Type | Description |
|---|---|---|
| `link_id` | str | Synthetic ID — `<from_sub_id>::<to_sub_id>` |
| `from_substation_id` | str | Source substation |
| `to_substation_id` | str | Destination substation |
| `voltage_kv` | int | Line voltage |
| `length_km` | float | Planned length |
| `ruptl_section` | str | V.11.1 (in construction), V.11.2 (under study), V.11.3 (cross-border) |
| `status` | enum | `in_construction` / `pre_construction` / `under_study` / `not_feasible` / `cross_border` |
| `target_cod_year` | int | Target year if specified, NaN otherwise |
| `ruptl_quote` | str | Direct quote from RUPTL re feasibility (e.g., "biaya pembangunan ... menjadi sangat mahal") |

**New columns** on `fct_site_scorecard`:

| Column | Type | Description |
|---|---|---|
| `recommended_grid_link_status` | enum | Status of the recommended new-transmission link from RUPTL, or `not_in_ruptl` if absent |
| `recommended_grid_link_target_year` | int | Target COD year if the link is in RUPTL |
| `comparator_feasibility` | enum | `pln_tariff_feasible` / `pln_tariff_uncertain_grid_first_required` / `pln_tariff_infeasible_captive_only` |
| `comparator_used_for_action_flag` | enum | `pln_bpp` / `industrial_tariff` / `captive_coal` / `captive_gas` (which incumbent the action flag actually compared against) |

**Logic.** When `grid_integration_category ∈ {invest_transmission, invest_substation, grid_first}` and the recommended new link is **not** in RUPTL §V.11.1 (in construction) or V.11.2 (committed), the comparator defaults to captive economics (per the v4.1 captive cost framework). Action flags then compare solar LCOE against captive cost rather than PLN tariff.

For sites where the link is in V.11.2 (under study) with no committed COD year, surface a `comparator_feasibility = pln_tariff_uncertain_grid_first_required` warning and let the user toggle which comparator to use.

**Implementation.**
- New raw data: `data/raw/ruptl_v11_transmission_links.csv` — manually compiled from RUPTL §V.11. ~30–40 rows.
- New pipeline: `src/pipeline/build_fct_transmission_link_ruptl_signal.py`.
- Update `src/dash/logic/grid.py::compute_grid_integration()` to attach `comparator_feasibility` per site.
- Update `src/dash/logic/scorecard.py::compute_action_flag()` to flow comparator choice through to action flag logic.
- METHODOLOGY_CONSOLIDATED §8 update.

**Validation.** Eastern Indonesia industrial sites (Halmahera, North Maluku) should default to `pln_tariff_infeasible_captive_only` — most of their transmission links sit in RUPTL §V.11.3 cross-border or are flagged "not financially feasible at proposed COD." Sumatra-Java HVDC-dependent sites get `pln_tariff_uncertain_grid_first_required`.

**Effort.** ~1.5 days. Half a day for raw data compilation; one day for pipeline + logic + tests.

---

### 3.2 Perpres 112/2022 as regulatory variable (Finding 6, [#8](https://github.com/shaanbarca/eez/issues/8))

**Why this matters.** §13.3 surfaces compliance as a status string (`perpres_112_status = "Subject to 2050 phase-out"`) but doesn't model the regulatory variable. The grid synthesis identifies this exemption as *the policy gap through which most of Indonesia's new industrial-scale fossil capacity flows*. v4.3 will add Perpres 112 reform as a pathway dimension; v4.0 should put the data structure in place so v4.3 can compose on top.

**Methodology change.** Replace the static `perpres_112_status` string with a structured regulatory state. New columns on `fct_site_scorecard`:

| Column | Type | Description |
|---|---|---|
| `captive_perpres_112_exempt` | bool | True if site qualifies for strategic-industry exemption (Perpres 112/2022 Art. 10) |
| `captive_perpres_112_exemption_basis` | enum | `strategic_industry` / `mining_specific` / `not_exempt` / `unclear` |
| `captive_phaseout_year_baseline` | int | 2050 under current Perpres 112 |
| `captive_phaseout_year_strict_scenario` | int | 2035 if exemption tightened in 2026+ regulatory cycle (v4.3 default for "strict" pathway) |
| `captive_subject_to_strict_scenario` | bool | True if the strict scenario would force this site to hybrid |

**Default classification by sector + region** (data work, populated in `data/raw/site_perpres_112_classification.csv`):

| Sector + region | Default `captive_perpres_112_exemption_basis` |
|---|---|
| Nickel IIA, Sulawesi/Maluku | `strategic_industry` (Perpres 112 Art. 10 explicit) |
| Aluminium, all | `strategic_industry` |
| Steel, all | `strategic_industry` |
| Fertilizer, all | `strategic_industry` |
| Cement, all | `not_exempt` (general-industry, subject to baseline phase-out) |
| KEK (any) | `unclear` (depends on tenant mix) |

Override with site-specific data where public legal disclosure exists (e.g., IMIP's Perpres 70/2014 incentive rulings).

**Implementation.**
- New raw data: `data/raw/site_perpres_112_classification.csv`. 81 rows; provenance-required.
- New pipeline: `src/pipeline/build_fct_perpres_112_classification.py`.
- Update `src/dash/logic/scorecard.py::enrich_captive_context()` to populate the new columns.
- Score Drawer: replace status-string display with structured fields ("Exempt: yes (strategic industry)" / "Phase-out: 2050 baseline / 2035 strict").
- METHODOLOGY_CONSOLIDATED §13.3 update.

**Validation.** All 17 nickel/aluminium/steel/fertilizer industrial sites should classify as `strategic_industry`. All 32 cement plants should classify as `not_exempt`. Spot-check 5 KEKs; classification depends on dominant tenant sector.

**Effort.** ~1 day. Mostly data work.

---

### 3.3 RUPTL → demand → RUPTL feedback loop (Finding 7, [#9](https://github.com/shaanbarca/eez/issues/9)) — deferred to v4.4

**Why this matters.** The grid feedback loop where captive coal demand reduces PLN's geothermal additions is methodologically real but deferred to v4.4 captive deep dive (per [Indonesia Dashboard Methodology Review] §Adjustments needed, finding 22). v4.0 should at least flag the static-RUPTL assumption explicitly in the methodology document so users don't read the long-horizon scenario 6 availability as static fact.

**v4.0 action.** Documentation only.

Add a paragraph to METHODOLOGY_CONSOLIDATED §13 (Captive Power Context) and §A.1 (limitations):

> **Static RUPTL assumption.** The dashboard treats PLN's RUPTL 2025–2034 as fixed — i.e., the planned generation additions (5,157 MW geothermal, 11,890 MW hydro in RE Base) are assumed to materialise regardless of how much industrial demand siphons off-grid via captive coal. In reality, PLN sizes geothermal and hydro contracts conditional on demand growth on its grid (RUPTL §III.2.1, *"Take-or-Pay obligations can be avoided"*). If the dashboard's projected captive-coal expansion materially reduces PLN's industrial-demand growth, the realistic geothermal pipeline shrinks — which makes Scenario 6 less available for the same smelter sites whose demand siphoned off PLN. v4.4 captive deep dive will model this feedback. For v4.0 / v4.1 / v4.2 / v4.3, treat the geothermal pipeline columns as a best-case upper bound conditional on PLN's demand case being met.

**v4.4 implementation** (deferred). Aggregate dashboard-projected captive-coal demand per region. Compute "PLN demand case minus captive bypass." Recompute RUPTL geothermal/hydro additions accordingly. Re-run scenario 6 availability per site.

**Effort.** ~0.25 day (documentation only).

---

### 3.4 Curtailment cost in supply blend (Finding 8, [#10](https://github.com/shaanbarca/eez/issues/10))

**Why this matters.** The wiki's energy storage page identifies curtailment as a major flexibility lever in IEA APS — providing ~25% of Indonesia's seasonal flexibility by 2050. For high-VRE-penetration grid-connected sites in low-demand regions (Maluku/Papua), curtailment is a real $/MWh cost. §9.5's `firm_solar_coverage_pct` handles overproduction *physically* (caps at daytime_demand) but doesn't price the curtailed energy.

**Methodology change.** Add a `curtailment_loss_pct` per site, derived from local demand absorption capacity vs. solar generation. Apply as a CF haircut for grid-connected scenarios.

```python
def estimate_curtailment_loss_pct(
    solar_generation_mwh,
    local_grid_demand_mwh,
    inter_substation_connected,
    grid_region_bpp_usd_mwh,
):
    """
    Estimate the fraction of solar generation that gets curtailed
    because the local grid can't absorb it.
    
    Logic:
    - If local demand > solar generation × 2.5 (oversupply factor for a 24/7 industrial offtaker),
      curtailment ≈ 0
    - If local demand << solar generation (small island, large solar farm), 
      curtailment scales with the oversupply ratio
    - inter_substation_connected = True allows export to broader grid → reduces curtailment
    """
    if inter_substation_connected and grid_region_bpp_usd_mwh < 100:
        return 0.05  # Java/Sumatra default, broad grid absorbs surplus
    
    oversupply_ratio = solar_generation_mwh / max(local_grid_demand_mwh, 1)
    if oversupply_ratio < 0.5:
        return 0.05
    elif oversupply_ratio < 1.0:
        return 0.10
    elif oversupply_ratio < 2.0:
        return 0.20
    else:
        return 0.35  # Maluku/Papua small island, large solar
```

Apply as effective CF haircut: `effective_cf = cf × (1 - curtailment_loss_pct)`. Feeds into LCOE for grid-connected scenarios only (within-boundary captive bypasses curtailment because it's behind-the-meter).

**Source data.** IEA SEA Outlook 2024 Figure 5.7 (regional curtailment under APS) for calibration. Cross-check against current PLN VRE penetration data (Bali Energy Vision, Sumba MEG case study).

**Implementation.**
- New constant block in `src/assumptions.py`: `CURTAILMENT_*` thresholds and ratios.
- New function in `src/model/basic_model.py`: `estimate_curtailment_loss_pct()`.
- Update `src/dash/logic/lcoe.py::compute_grid_connected_lcoe()` to apply CF haircut.
- New column on `fct_site_scorecard`: `curtailment_loss_pct`, `lcoe_grid_connected_pre_curtailment_usd_mwh` (for transparency).
- METHODOLOGY_CONSOLIDATED §9.5 update.

**Validation.** Maluku/Papua sites (Buli, Halmahera, Tual) should show curtailment 20–35% with corresponding LCOE uplift. Java sites (Karawang, Cikampek) should show <5%. Spot-check 5 sites against the IEA SEA Outlook regional figures.

**Effort.** ~1 day.

---

### 3.5 Scope 1 abatement options surfaced (Finding 9, [#11](https://github.com/shaanbarca/eez/issues/11))

**Why this matters.** §14.2 correctly says solar can't address Scope 1 (cement calcination, ammonia SMR feedstock, BF-BOF coke). RE-addressable fractions (cement 0.12, ammonia 0.10, steel BF-BOF 0.80) are right for *today's* technology stack. But abatement options exist (alt fuels, green H₂ DRI, green ammonia) that can take cement/ammonia/BFBOF sites from 10–12% relief to 50%+. The dashboard currently shows a static ceiling.

**Methodology change.** Don't model the abatement *cost* (out of scope until v5.x). Do add a flag and a qualitative tier indicating Scope 1 abatement availability:

| Column | Type | Description |
|---|---|---|
| `scope1_abatement_pathways` | str | Comma-separated pathway names — e.g., `"alt_fuels,scm_substitution"` for cement; `"green_h2_smr"` for ammonia; `"hydrogen_dri,scrap_substitution"` for BF-BOF |
| `scope1_abatement_indicative_addressable_pct` | float | Indicative additional Scope 1 fraction addressable via these pathways (0–1 scale). Cement 0.30, ammonia 0.50, BF-BOF 0.70. Aluminium 0.10 (inert anodes still emerging). Nickel RKEF 0.0 (process emissions are reductant chemistry). |
| `scope1_abatement_methodology_note` | str | One-line caveat ("Indicative — full cost modeling deferred to v5.x") |

**Implementation.**
- New constant in `src/assumptions.py`:
  ```python
  SCOPE1_ABATEMENT_PATHWAYS_BY_PRODUCT = {
      "cement": ("alt_fuels,scm_substitution,electric_kiln", 0.30),
      "ammonia": ("green_h2_smr", 0.50),
      "fertilizer": ("green_h2_smr", 0.50),
      "steel_bfbof": ("hydrogen_dri,scrap_substitution", 0.70),
      "steel_eaf": ("scrap_substitution", 0.10),
      "aluminium": ("inert_anodes", 0.10),
      "nickel_rkef": ("", 0.0),
  }
  ```
- Update `src/dash/logic/cbam.py::compute_cbam_trajectory()` to populate `scope1_abatement_*` columns.
- Score Drawer Industry tab: add a "Scope 1 abatement pathways" section under the CBAM trajectory chart. Display the pathway list and indicative addressable %, with the "Indicative — full cost modeling deferred to v5.x" caveat.
- Tooltip on the CBAM trajectory chart: "Scope 2 only. Scope 1 has additional abatement pathways (see Industry tab)."
- METHODOLOGY_CONSOLIDATED §14.2 / §14.3 update.

**Validation.** Cement and ammonia sites should display non-empty `scope1_abatement_pathways`. Nickel RKEF sites should display empty (process chemistry can't be electrified). Spot-check Indocement (cement, alt_fuels visible), Pupuk Kaltim (ammonia, green_h2_smr visible), IMIP (RKEF, empty).

**Effort.** ~0.5 day.

---

### 3.6 Hybrid binding-constraint signal (Finding 10, [#12](https://github.com/shaanbarca/eez/issues/12))

**Why this matters.** §6A.5 sweeps `solar_share` 0–100% and picks the cost-minimum hybrid. The natural follow-up question for any user is: *what does it take to flip the optimum?* (Lower BESS cost? Higher wind CF? Different storage hours?) v4.3 multi-pathway analysis will compute this implicitly across the whole site set; surface it explicitly per-site too.

**Methodology change.** Add a per-site `hybrid_binding_constraint` field. Computed by perturbing each input parameter and identifying which one flips the optimum mix by the largest amount:

```python
def compute_hybrid_binding_constraint(site_inputs):
    """
    Returns the input parameter whose perturbation produces the largest 
    optimum-mix shift. Five candidates tested:
    - BESS CAPEX (-30%, +30%)
    - Solar CAPEX (-15%, +15%)
    - Wind CAPEX (-15%, +15%)
    - WACC (-2pp, +2pp)
    - Storage duration (-25%, +25%)
    
    For each, re-run hybrid_lcoe_optimized() and record the resulting solar_share.
    The constraint with the largest |delta_solar_share| is the binding constraint.
    """
    base_solar_share = hybrid_lcoe_optimized(**site_inputs).solar_share
    
    deltas = {}
    for param, (low, high) in PERTURBATIONS.items():
        perturbed_low = {**site_inputs, param: site_inputs[param] * (1 + low)}
        perturbed_high = {**site_inputs, param: site_inputs[param] * (1 + high)}
        share_low = hybrid_lcoe_optimized(**perturbed_low).solar_share
        share_high = hybrid_lcoe_optimized(**perturbed_high).solar_share
        deltas[param] = max(abs(share_low - base_solar_share), abs(share_high - base_solar_share))
    
    binding = max(deltas, key=deltas.get)
    return {
        "binding_constraint": binding,
        "narrative": format_narrative(binding, site_inputs, deltas[binding]),
    }
```

**New columns** on `fct_site_scorecard`:

| Column | Type | Description |
|---|---|---|
| `hybrid_binding_constraint` | enum | `bess_capex` / `solar_capex` / `wind_capex` / `wacc` / `storage_duration` / `none_meaningful` |
| `hybrid_binding_narrative` | str | One-sentence narrative — e.g., "60/40 solar/wind today; flips to 90/10 if BESS drops to $80/kWh" |
| `hybrid_constraint_sensitivity` | float | Magnitude of solar-share shift under the binding-constraint perturbation |

**Implementation.**
- New function in `src/model/basic_model.py`: `compute_hybrid_binding_constraint()`.
- Update `src/dash/logic/technology.py::compute_hybrid_metrics()` to call it per site.
- Score Drawer Economics tab: add a "Binding constraint" callout below the hybrid mix display.
- METHODOLOGY_CONSOLIDATED §6A.7 update (output fields).

**Validation.** Sites with high BESS share (Maluku/Papua, NTT) should mostly show `bess_capex` as binding constraint. Sites near grid parity should show `wacc` as binding. Spot-check 5 sites.

**Effort.** ~0.75 day.

---

## 4. Refinements

### 4.1 MacKay citation correction (Finding 11, [#13](https://github.com/shaanbarca/eez/issues/13))

**Why this matters.** §6.3 cites MacKay Ch. 26 as the physical basis for the 14h bridge-hours model. MacKay Ch. 26 covers UK-style 5-day winter lulls, EV-as-storage, pumped-hydro economics — it doesn't endorse a 14h bridge-hours model for tropical industrial loads. The math is right; the citation is a stretch.

**Methodology change.** In METHODOLOGY_CONSOLIDATED §6.3, replace:

> **Physical basis:** MacKay, *Sustainable Energy Without the Hot Air*, Ch. 26. Storage must bridge the gap between solar production hours and demand hours.

with:

> **Physical basis (first principles):** Storage must bridge the gap between solar production hours and demand hours. At equatorial Indonesian latitudes with ~10h effective solar production and 24/7 industrial demand, the overnight gap is 14h. BESS must store `14h × load_MW / RTE` of energy. The framing draws on the broader storage-system thinking in [[Sustainable Energy Without the Hot Air]] Ch. 26 (UK-context analysis of grid-scale storage requirements) but the 14h tropical-equatorial bridge-hours figure is derived from Indonesia-specific solar production hours, not endorsed by MacKay's UK case study.

**Effort.** ~0.1 day. Documentation correction.

---

### 4.2 Captive matching: contractual + spatial (Finding 12, [#14](https://github.com/shaanbarca/eez/issues/14))

**Why this matters.** §13.2 uses 50 km haversine for matching captive coal and nickel. Sumatran mine-mouth coal plants > 50 km from the smelter they supply are common. Pure spatial matching misses contractual mine-to-smelter relationships — relevant for the captive-cost reference (v4.1) and for stranded-asset analysis (v4.4).

**Methodology change.** Add a manual-override layer alongside the haversine match. Sites with a known contractual coal supplier (from public disclosures, annual reports) get the supplier's data even if the supplier sits beyond 50 km.

**New raw data.** `data/raw/captive_coal_contractual_overrides.csv`:

| site_id | captive_coal_plant_id | source | last_updated | distance_km | notes |
|---|---|---|---|---|---|
| imip_morowali | tsingshan_unit_1_coal | "IMIP 2023 annual report" | 2024-12 | 1.2 | On-site |
| krakatau_steel_cilegon | banten_coal_plant_a | "PT Krakatau Steel 2022 annual report" | 2024-11 | 8.5 | Captive but separate site |
| ... | ... | ... | ... | ... | ... |

**Implementation.**
- New raw data file as above.
- New utility in `src/pipeline/geo_utils.py`: `match_with_contractual_overrides(site_id, default_50km_match, overrides_df)`. Override wins if `distance_km` is within a stricter business-relationship threshold (e.g., explicit captive ownership).
- Update `src/pipeline/build_fct_captive_coal.py` to use the override layer.
- METHODOLOGY_CONSOLIDATED §13.2 update.

**Validation.** Sumatran sites with known mine-mouth captive arrangements (e.g., Lampung industrial corridor) should match to the contractually-linked plant even at >50 km. Spot-check 3 sites.

**Effort.** ~1 day. Mostly data compilation (annual report mining for ~10 priority sites); pipeline change is small.

---

### 4.3 GEAS empirical allocation alternative (Finding 13, [#15](https://github.com/shaanbarca/eez/issues/15))

**Why this matters.** §11 assumes proportional-to-demand GEAS allocation:

```
GEAS_alloc = E_green × D_kek / D_total_region
```

PLN's empirical allocation is urban-anchored and slower-rural — large urban industrial customers in Java get more than their proportional share; remote KEKs get less. The proportional baseline systematically over-credits remote KEKs.

**Methodology change.** Add a second allocation scenario with a region-and-distance-to-load-centre weighting:

```python
def geas_alloc_empirical(green_energy_regional, demand_kek, demand_total_region, 
                         distance_to_load_centre_km, region):
    """
    PLN-empirical allocation: proportional-to-demand × distance-decay × region-multiplier.
    
    Distance decay: 1.0 within 100 km of load centre, linearly down to 0.4 at 500 km.
    Region multiplier: JAMALI 1.2, Sumatera 1.0, Kalimantan 0.7, Sulawesi 0.6, Maluku/Papua 0.4.
    """
    distance_decay = max(0.4, 1.0 - 0.6 * max(0, distance_to_load_centre_km - 100) / 400)
    region_mult = REGION_GEAS_MULT[region]
    proportional_share = demand_kek / max(demand_total_region, 1)
    return green_energy_regional * proportional_share * distance_decay * region_mult
```

**New columns** on `fct_site_scorecard`:

| Column | Type | Description |
|---|---|---|
| `geas_alloc_proportional_gwh` | float | Existing proportional baseline |
| `geas_alloc_empirical_gwh` | float | New PLN-empirical allocation (above) |
| `green_share_geas_proportional_pct` | float | Existing |
| `green_share_geas_empirical_pct` | float | New |
| `geas_allocation_used` | enum | Which method drives the action flag — `proportional` (default) or `empirical` (user-toggleable) |

**Implementation.**
- New function in `src/model/basic_model.py`: `geas_alloc_empirical()`.
- Update `src/dash/logic/scorecard.py::enrich_geas()` to compute both allocations.
- Score Drawer Economics tab: toggle between proportional and empirical allocation; show side-by-side.
- METHODOLOGY_CONSOLIDATED §11 update.

**Validation.** Remote eastern Indonesia KEKs (Sorong, Morotai) should show `green_share_geas_empirical_pct` ~30–50% lower than proportional. Java KEKs (Kendal, Batang) should show similar values across both. Spot-check 5 sites.

**Effort.** ~0.5 day.

---

## 5. Output Schema Changes

New fields added to `fct_site_scorecard` by this spec:

```
# Finding 1 — solar+battery cascade
delivered_cost_dispatchable_re_fraction
delivered_cost_dispatchable_re_lcoe_used_usd_mwh

# Finding 2 — geothermal proximity
nearest_geothermal_operating_id
nearest_geothermal_operating_km
nearest_geothermal_operating_mw
nearest_geothermal_operating_emission_factor_g_per_kwh
nearest_geothermal_pipeline_id
nearest_geothermal_pipeline_km
nearest_geothermal_pipeline_mw
nearest_geothermal_pipeline_target_year
geothermal_adjacency_tier
geothermal_transmission_feasibility

# Finding 3 — wind nighttime fraction
wind_nighttime_fraction_used  # the region-specific value applied to this site

# Finding 4 — solar lifecycle correction
# (no new columns; existing carbon_breakeven_usd_tco2 values shift)

# Finding 5 — RUPTL §V.11 feasibility
recommended_grid_link_status
recommended_grid_link_target_year
comparator_feasibility
comparator_used_for_action_flag

# Finding 6 — Perpres 112/2022 regulatory variable
captive_perpres_112_exempt
captive_perpres_112_exemption_basis
captive_phaseout_year_baseline
captive_phaseout_year_strict_scenario
captive_subject_to_strict_scenario

# Finding 8 — curtailment cost
curtailment_loss_pct
lcoe_grid_connected_pre_curtailment_usd_mwh

# Finding 9 — Scope 1 abatement
scope1_abatement_pathways
scope1_abatement_indicative_addressable_pct
scope1_abatement_methodology_note

# Finding 10 — hybrid binding constraint
hybrid_binding_constraint
hybrid_binding_narrative
hybrid_constraint_sensitivity

# Finding 12 — captive matching contractual override
captive_coal_match_basis  # spatial / contractual / both

# Finding 13 — GEAS empirical alternative
geas_alloc_proportional_gwh
geas_alloc_empirical_gwh
green_share_geas_proportional_pct
green_share_geas_empirical_pct
geas_allocation_used
```

Total: 26 new columns. All nullable; existing rows unaffected if data is missing.

New separate tables:
- `data/raw/geothermal_operating.geojson` (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4))
- `data/raw/geothermal_pipeline.geojson` (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4))
- `data/raw/ruptl_v11_transmission_links.csv` (Finding 5, [#7](https://github.com/shaanbarca/eez/issues/7))
- `data/raw/site_perpres_112_classification.csv` (Finding 6, [#8](https://github.com/shaanbarca/eez/issues/8))
- `data/raw/captive_coal_contractual_overrides.csv` (Finding 12, [#14](https://github.com/shaanbarca/eez/issues/14))

New pipeline files:
- `src/pipeline/build_fct_geothermal_proximity.py`
- `src/pipeline/build_fct_transmission_link_ruptl_signal.py`
- `src/pipeline/build_fct_perpres_112_classification.py`

---

## 6. Validation Strategy

### 6.1 Regression validation

**Critical:** Existing v4.0 LCOE, action flags, and economic tier values must be preserved for sites where no new column changes the comparator. Run the pipeline end-to-end; for sites where:
- `geothermal_adjacency_tier = "none"` AND
- `comparator_feasibility = "pln_tariff_feasible"` AND
- `curtailment_loss_pct < 0.05` AND
- `captive_coal_match_basis = "spatial"`

…all existing scorecard fields should match v4.0 within rounding error. Sites where the new columns shift the comparator (e.g., Eastern Indonesia sites where `comparator_feasibility = "pln_tariff_infeasible_captive_only"`) will have different action flags by design — document each shift.

### 6.2 Per-finding validation

| Finding | Validation method |
|---|---|
| 1 | `bess_competitive` no longer drives `solar_now`; cascade delivered cost matches manual calculation for 3 spot-check sites |
| 2 | Geothermal tier matches manual ESDM resource map for 5 spot-check sites; map view layer renders correctly |
| 3 | NTT site optimum solar share rises 5–10pp; Kalimantan site shifts mildly downward |
| 4 | All 81 carbon breakeven values shift 5–8% upward; per-region uniformity within rounding |
| 5 | Eastern Indonesia sites default to `pln_tariff_infeasible_captive_only`; Java sites stay `pln_tariff_feasible` |
| 6 | All 17 nickel/aluminium/steel/fertilizer sites classify `strategic_industry`; all 32 cement sites `not_exempt` |
| 7 | Documentation review only |
| 8 | Maluku/Papua sites curtailment 20–35%; Java sites <5% |
| 9 | Cement sites display `alt_fuels,scm_substitution`; nickel RKEF sites display empty |
| 10 | High-BESS-share sites bind on `bess_capex`; near-parity sites bind on `wacc` |
| 11 | Documentation review only |
| 12 | 3 Sumatran mine-mouth contractual overrides apply correctly |
| 13 | Remote KEK empirical allocation 30–50% lower than proportional |

### 6.3 Cross-validation against external benchmarks

- Geothermal NCG emission factors (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4)): cross-validate Wayang Windu 73, Kamojang 73, Ulubelu 43 against ESDM 2024 §1 published values.
- Curtailment estimates (Finding 8, [#10](https://github.com/shaanbarca/eez/issues/10)): cross-validate Maluku/Papua range (20–35%) against IEA SEA Outlook 2024 Figure 5.7 and IRENA SE Asia VRE flexibility report.
- Solar lifecycle EF (Finding 4, [#6](https://github.com/shaanbarca/eez/issues/6)): cross-validate 40 gCO₂/MWh against IPCC AR6 Annex III median.

### 6.4 Sanity checks

For every site:
- `nearest_geothermal_*_km` ≥ 0
- `geothermal_adjacency_tier` consistent with the *_km values
- `curtailment_loss_pct` ∈ [0, 0.5]
- `captive_perpres_112_exempt = True` ⟹ `captive_phaseout_year_strict_scenario < captive_phaseout_year_baseline`
- `lcoe_grid_connected_pre_curtailment` ≤ `lcoe_grid_connected` (curtailment uplift is non-negative)
- `comparator_used_for_action_flag` is one of the v4.1 incumbent options when v4.1 ships; legacy `pln_bpp` for v4.0

---

## 7. Success Criteria

### 7.1 Functional

- [ ] All 81 sites have geothermal proximity columns populated (Finding 2, [#4](https://github.com/shaanbarca/eez/issues/4))
- [ ] All 81 sites have RUPTL §V.11 feasibility check (Finding 5, [#7](https://github.com/shaanbarca/eez/issues/7))
- [ ] All 81 sites have Perpres 112/2022 regulatory classification (Finding 6, [#8](https://github.com/shaanbarca/eez/issues/8))
- [ ] All 81 sites have curtailment loss estimate (Finding 8, [#10](https://github.com/shaanbarca/eez/issues/10))
- [ ] All 81 sites have Scope 1 abatement pathway flag (Finding 9, [#11](https://github.com/shaanbarca/eez/issues/11))
- [ ] All 81 sites have hybrid binding-constraint signal (Finding 10, [#12](https://github.com/shaanbarca/eez/issues/12))
- [ ] Wind nighttime fraction tiered by region (Finding 3, [#5](https://github.com/shaanbarca/eez/issues/5))
- [ ] Solar lifecycle correction applied (Finding 4, [#6](https://github.com/shaanbarca/eez/issues/6))
- [ ] GEAS empirical allocation computed alongside proportional (Finding 13, [#15](https://github.com/shaanbarca/eez/issues/15))
- [ ] Supply Blend cascade extended with dispatchable RE layer (Finding 1, [#3](https://github.com/shaanbarca/eez/issues/3))
- [ ] Captive matching uses contractual overrides where available (Finding 12, [#14](https://github.com/shaanbarca/eez/issues/14))

### 7.2 Validation

- [ ] Per-finding validation criteria pass (§6.2 above)
- [ ] Cross-validation against external benchmarks passes
- [ ] All sanity checks pass
- [ ] Regression test passes for unaffected sites

### 7.3 Documentation

- [ ] METHODOLOGY_CONSOLIDATED.md updated for findings 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
- [ ] Static-RUPTL assumption explicitly flagged in §13 and §A.1 (Finding 7, [#9](https://github.com/shaanbarca/eez/issues/9))
- [ ] CHANGELOG.md entry for v4.0.5 (this release)
- [ ] Methodology review cross-reference matrix updated

### 7.4 Release

- [ ] v4.0.5 Zenodo DOI published (or rolled into v4.1 if same release window)
- [ ] [[Indonesia Dashboard Methodology Review]] log updated with implementation status

---

## 8. To-Do List

### Day 1 — Data foundations and 1-line fixes

| # | Task | Effort | Type | Finding |
|---|---|---|---|---|
| 1 | Apply solar lifecycle EF correction (1-line + fixture update) | 0.5 day | Code | 4 |
| 2 | MacKay citation correction in METHODOLOGY §6.3 | 0.1 day | Docs | 11 |
| 3 | Static-RUPTL assumption documentation in METHODOLOGY §13 / §A.1 | 0.25 day | Docs | 7 |
| 4 | Compile geothermal operating + pipeline raw data | 0.5 day | Data | 2 |
| 5 | Compile RUPTL §V.11 transmission links raw data | 0.5 day | Data | 5 |

### Day 2 — Geothermal proximity + Perpres 112 + RUPTL §V.11

| # | Task | Effort | Type | Finding |
|---|---|---|---|---|
| 6 | `build_fct_geothermal_proximity.py` pipeline | 0.5 day | Code | 2 |
| 7 | `build_fct_perpres_112_classification.py` pipeline + raw data | 0.5 day | Code+Data | 6 |
| 8 | `build_fct_transmission_link_ruptl_signal.py` pipeline | 0.5 day | Code | 5 |
| 9 | Compile site Perpres 112 classification raw data | 0.5 day | Data | 6 |

### Day 3 — Schema integration + cascade extension

| # | Task | Effort | Type | Finding |
|---|---|---|---|---|
| 10 | Schema migration: add 26 new columns to scorecard | 0.5 day | Code | All |
| 11 | Extend Supply Blend cascade with dispatchable RE layer | 0.75 day | Code | 1 |
| 12 | Comparator feasibility check in `compute_grid_integration` | 0.5 day | Code | 5 |
| 13 | Tier wind nighttime fraction by region | 0.5 day | Code | 3 |

### Day 4 — Curtailment + Scope 1 + binding constraint

| # | Task | Effort | Type | Finding |
|---|---|---|---|---|
| 14 | Curtailment loss estimation function + LCOE haircut | 0.75 day | Code | 8 |
| 15 | Scope 1 abatement pathway constants + scorecard population | 0.5 day | Code | 9 |
| 16 | Hybrid binding-constraint computation | 0.75 day | Code | 10 |

### Day 5 — Refinements + frontend

| # | Task | Effort | Type | Finding |
|---|---|---|---|---|
| 17 | Captive coal contractual override layer | 0.5 day | Code+Data | 12 |
| 18 | GEAS empirical allocation function + toggle | 0.5 day | Code | 13 |
| 19 | Geothermal map layer (operating + pipeline markers) | 0.5 day | UI | 2 |
| 20 | Score Drawer updates: Pipeline tab geothermal card, Industry tab Scope 1 abatement, Economics tab binding-constraint callout, GEAS toggle | 0.5 day | UI | 2, 9, 10, 13 |

### Day 6 — Validation + documentation

| # | Task | Effort | Type |
|---|---|---|---|
| 21 | Per-finding validation criteria (§6.2) | 0.75 day | Test |
| 22 | Regression test against v4.0 baseline (§6.1) | 0.5 day | Test |
| 23 | Cross-validate against IPCC AR6, IEA SEA Outlook, ESDM 2024 (§6.3) | 0.5 day | Validation |
| 24 | METHODOLOGY_CONSOLIDATED.md updates for all findings | 0.75 day | Docs |
| 25 | CHANGELOG.md v4.0.5 entry | 0.25 day | Docs |

### Day 7 — Release

| # | Task | Effort | Type |
|---|---|---|---|
| 26 | Spot-check 5 representative sites (IMIP, Indocement, Pupuk Kaltim, Sumba PV-megaproject, Krakatau Steel) | 0.5 day | Validation |
| 27 | Update [[Indonesia Dashboard Methodology Review]] log with v4.0.5 fix status | 0.25 day | Docs |
| 28 | Zenodo v4.0.5 DOI publish (or roll into v4.1 release) | 0.25 day | Release |
| 29 | Update DATA_DICTIONARY.md with 26 new columns | 0.5 day | Docs |

**Total effort:** 7 focused work days. Several findings (4, 11, 7) are sub-day; the heavier ones (2, 5) span data + pipeline.

---

## 9. Migration and Backwards Compatibility

### 9.1 Schema additions are additive

All 26 new columns are appended to `fct_site_scorecard`; no existing column is renamed or removed. Frontend continues to work using existing columns; new columns become available for new UI elements.

### 9.2 Action-flag stability

The action-flag taxonomy (10 solar-mode flags + 14 across all energy modes) is unchanged. The *behaviour* of `solar_now` and `cbam_urgent` may shift for sites where `comparator_used_for_action_flag` changes (e.g., Eastern Indonesia sites flipping from `pln_bpp` to `captive_coal` comparator). Document each behavioural shift with a banner ("v4.0.5 changed comparator for this site from PLN tariff to captive coal because the planned transmission link is `under_study` in RUPTL §V.11 with no committed COD year").

### 9.3 No frontend-breaking changes

Frontend reads existing columns; new columns are surfaced in new UI elements (geothermal layer, Scope 1 callout, binding-constraint card, GEAS toggle). Existing views (Map, Ranked Table, Quadrant Chart, Site Scorecard) work unchanged.

### 9.4 Test fixture updates

Regression test fixture `tests/fixtures/scorecard_v4_0_baseline.csv` extends with the 26 new columns. Existing rows shift on:
- `carbon_breakeven_usd_tco2` (Finding 4, ~5–8% per row)
- `wind_carbon_breakeven_usd_tco2` (Finding 4, ~5–8% per row)
- `delivered_cost_usd_mwh` (Finding 1, sites with reachable geothermal/hydro)
- `lcoe_grid_connected_usd_mwh` (Finding 8, high-curtailment sites)
- `green_share_geas_*` (Finding 13, all sites)
- `action_flag` and `economic_tier` (Findings 5, 6 — for sites where comparator shifts)

Re-record fixture; document deltas in CHANGELOG.

---

## Appendix A: Cross-reference Matrix

| Finding | Wiki source | Existing methodology section | New module/data | Output column(s) |
|---|---|---|---|---|
| 1 | Powering 24-7 §Six scenarios | §5.4 (Supply Blend), §6.3 (BESS) | `enrich_delivered_cost` extension | `delivered_cost_dispatchable_re_*` |
| 2 | Geothermal Power §Indonesia + Powering 24-7 §Why doesn't Indonesia use more geothermal | §13 (Captive Power Context) | `build_fct_geothermal_proximity` | `nearest_geothermal_*`, `geothermal_adjacency_tier`, `geothermal_transmission_feasibility` |
| 3 | (calibration finding) | §6A.2 (RESource abstraction) | `WIND_NIGHTTIME_FRACTION_BY_REGION` constant | `wind_nighttime_fraction_used` |
| 4 | LCOE concept page | §9.2 (Carbon breakeven) | `carbon_breakeven_price()` correction | (existing) `carbon_breakeven_usd_tco2` shift |
| 5 | Indonesia Grid §V.11 + §What needs to happen | §8 (Three-point proximity) | `build_fct_transmission_link_ruptl_signal` | `recommended_grid_link_*`, `comparator_*` |
| 6 | Indonesia Grid §What needs to happen + §How to do it | §13.3 (Perpres 112) | `build_fct_perpres_112_classification` | `captive_perpres_112_*`, `captive_phaseout_*` |
| 7 | Geothermal Power §Indonesia + RUPTL §III.2.1 | §13 (deferred) | (deferred to v4.4) | (deferred) |
| 8 | Energy Storage §Curtailment + Indonesia Grid §VRE flexibility | §9.5 (Firm solar coverage) | `estimate_curtailment_loss_pct()` | `curtailment_loss_pct`, `lcoe_grid_connected_pre_curtailment_usd_mwh` |
| 9 | Powering 24-7 §Why it matters + §14.2 (existing) | §14.2 (Two kinds of emissions) | `SCOPE1_ABATEMENT_PATHWAYS_BY_PRODUCT` constant | `scope1_abatement_*` |
| 10 | (UX finding from review) | §6A.5 (Mix optimization) | `compute_hybrid_binding_constraint()` | `hybrid_binding_*` |
| 11 | (citation correction) | §6.3 (BESS) | (docs only) | (none) |
| 12 | Indonesia Grid §Captive coal as parallel grid escape | §13.2 (Spatial matching) | Override layer in `build_fct_captive_coal` | `captive_coal_match_basis` |
| 13 | (PLN empirical allocation finding) | §11 (GEAS Green Share) | `geas_alloc_empirical()` | `geas_alloc_*`, `green_share_geas_*` |

---

*Cross-references: [[Indonesia Dashboard Methodology Review]] §Review of the current dashboard. Spec authored against METHODOLOGY_CONSOLIDATED.md V3.7 (April 2026).*
