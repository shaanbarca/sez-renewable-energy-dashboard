# Plan: Substation-Anchored Solar Search (Fix "Build Substation" False Positive)

**Status:** Drafted. Thresholds resolved. Awaiting implementation approval.
**Branch:** `fix/substation-proximity-build-substation-mismatch`
**Source:** Bug report 2026-04-19 — Batam Aero Technic ScoreDrawer shows "Build Substation" despite multiple substation markers visible 4 km away on the map.

---

## Problem

The dashboard labels Batam Aero Technic (and similar small-demand sites) as **"Build Substation"** even though multiple substation markers are visibly close on the map.

Concrete numbers from `outputs/data/processed/fct_substation_proximity.csv`:

| Field | Value |
|---|---|
| Site | Batam Aero Technic |
| Site demand | 19.8 GWh/yr (~12-20 MWp solar would meet it) |
| Nearest substation to site | **GI 150 kV Nongsa 1 — 3.96 km away** |
| Best PVOUT pixel within 50 km | ~50 km away in Bintan |
| That pixel's nearest substation | GI 150 kV Tg. Kasam — **17.9 km away** |
| Resulting label | `invest_substation` ("Build Substation") |

The label is logically consistent with the model. The user-visible bug is in the *model definition*, not the code execution.

---

## Current approach

`grid_integration_category()` in `src/model/basic_model.py:1163-1279` evaluates a **3-point proximity test** between:

- **A** — site centroid
- **B** — best-PVOUT buildable solar pixel anywhere within 50 km of the site
- **C** — the substation closest to A (and the substation closest to B)

The "best solar site" is selected upstream in `_compute_buildable_pvout()` at `src/pipeline/build_fct_site_resource.py:566-581` by:

1. Take the 50 km bounding box around the site centroid.
2. Apply 5-layer buildability mask (forest, peatland, slope, land cover, road proximity).
3. **Take `argmax(PVOUT)` over remaining pixels.**

This single best pixel is written as `best_solar_site_lat/lon` to `fct_site_resource.csv` and read by `build_fct_substation_proximity.py:268-291`. The chosen pixel is then locked in for all downstream logic — substation distance, grid integration category, capacity assessment, transmission cost.

The pathology: **PVOUT varies by ~1-2% across a 50 km radius in tropical Indonesia, but substation distance can vary by 10x+ over the same area.** Optimizing for the 1% PVOUT delta sends the model to a pixel that's geometrically far from any substation, even when an *almost-as-good* pixel sits next door to an existing substation.

The model also ignores site demand entirely. A 19.8 GWh site needs ~12-20 MWp; a 5,000 GWh site needs ~3-4 GWp. Both currently get the same single best pixel and the same buildable area accounting.

---

## Solution

**Substation-anchored solar search with a meaningful-share capacity floor and LCOE-driven candidate selection.**

Replace the "best PVOUT pixel" picker with a multi-step search that first asks *"is there a buildable solar patch sitting next to an existing substation that can still meet a useful share of this site's demand?"* — and only falls back to the current best-PVOUT logic if the answer is no.

### Algorithm

For each site, in `_compute_buildable_pvout()`:

1. **Compute required solar capacity** from site demand:
   `required_mwp = annual_demand_mwh / (8760 × cf_centroid)`
   where `cf_centroid` is the capacity factor at the site's centroid PVOUT.
   Demand source: `fct_site_demand.demand_2030_gwh` (solar projects are sized for lifetime).

2. **Define meaningful-share floor:**
   `meaningful_mwp = required_mwp × MEANINGFUL_SHARE_PCT`
   `MEANINGFUL_SHARE_PCT = 0.30` — patches that cannot cover at least 30% of demand are thrown out.

3. **Find candidate substation-anchored patches:**
   For each substation within `KEK_TO_SUBSTATION_THRESHOLD_KM` (15 km) of the site:
   a. Query buildable polygons within `SUBSTATION_COLOCATION_RADIUS_KM = 10 km` of that substation.
   b. Sum buildable area in that radius. Convert to MWp via `area_ha / HA_PER_MWP` (existing constant from spacing rules).
   c. Compute mean PVOUT over that buildable area.
   d. Keep candidate if `candidate_mwp >= meaningful_mwp`.

4. **Pick the candidate with the lowest LCOE.**
   For each viable candidate (substation-anchored patch that meets the meaningful-share floor), compute an all-in LCOE proxy:
   `lcoe_proxy = lcoe_solar(capex, fom, wacc, lifetime, cf_candidate) + grid_connection_cost_per_kw(dist_solar_to_substation_km) × annualisation_factor`
   where `cf_candidate` is the capacity factor implied by the candidate patch's mean PVOUT.
   Pick the candidate with the lowest `lcoe_proxy`. This naturally trades the small PVOUT loss against the (sometimes large) connection cost saving.

5. **Fallback:** If no substation within `KEK_TO_SUBSTATION_THRESHOLD_KM` has enough buildable area within `SUBSTATION_COLOCATION_RADIUS_KM` to meet `meaningful_mwp`, write the existing best-PVOUT pixel as today — and additionally write a flag `solar_search_method = "best_pvout_fallback"` so the UI can explain why the site got `invest_substation`. **This is the only path that should produce `invest_substation`.** If even one viable anchored candidate exists, it wins and the site gets `grid_ready`.

6. **Output (new + changed columns in `fct_site_resource.csv`):**
   - `best_solar_site_lat/lon` — now points to the chosen anchored patch (or fallback pixel)
   - `pvout_buildable_best_50km` — mean PVOUT of chosen patch (slightly lower than today's argmax)
   - `buildable_area_ha`, `regional_groundmount_potential_mwp_50km` — sized to chosen patch, not the whole 50 km radius
   - **NEW** `solar_search_method` — `"substation_anchored"` or `"best_pvout_fallback"`
   - **NEW** `chosen_anchor_substation_name` — for traceability in ScoreDrawer
   - **NEW** `solar_supply_share_pct` — chosen patch capacity ÷ required_mwp; lets the UI distinguish "full coverage" vs "meaningful but partial" vs "fallback only"

### Why this fixes Batam Aero Technic

- `required_mwp ≈ 19.8 GWh / (8760 × 0.18) ≈ 12.5 MWp`
- `meaningful_mwp = 12.5 × 0.30 = 3.75 MWp`
- Step 3a finds GI 150 kV Nongsa 1 at 3.96 km from site, plus other substations within 15 km.
- Step 3b queries buildable polygons within **10 km** of each candidate substation. Batam has ~280 km² of land, much of it buildable when forest+peatland+slope+road filters are relaxed for a small island.
- If even 1 km² of buildable area exists within 10 km of Nongsa 1 → ~40 MWp capacity → easily clears 3.75 MWp floor.
- Step 4 ranks candidates by LCOE proxy. Nongsa 1 (3.96 km substation distance, slightly lower PVOUT) wins over Tg. Kasam (17.9 km, slightly higher PVOUT) because the connection cost saving dominates.
- `dist_solar_to_substation_km` drops from 17.9 km to <5 km. `solar_near = True` (passes the 5 km classification threshold). `kek_near = True`. `grid_integration_category = "grid_ready"`. Label becomes "Grid Ready" instead of "Build Substation."

### Files to modify

| File | What changes |
|---|---|
| `src/pipeline/build_fct_site_resource.py:420-611` | Replace single-pixel argmax in `_compute_buildable_pvout()` with the substation-anchored loop above. Add new output columns. |
| `src/pipeline/build_fct_substation_proximity.py:268-291` | No code change needed — it already reads `best_solar_site_lat/lon`. Optionally surface `solar_search_method` and `chosen_anchor_substation_name` so they reach the scorecard. |
| `src/pipeline/demand_intensity.py` | Add inverse helper: `required_solar_mwp(annual_demand_mwh, cf) → float`. Tiny utility, lives where the demand→intensity logic already lives. |
| `src/dash/data_loader.py` | Surface `solar_search_method` + `solar_supply_share_pct` to `resource_df` for ScoreDrawer. |
| `frontend/src/components/panels/scoredrawer/GridTab.tsx` | Show `solar_search_method` + chosen anchor substation when fallback fired (so user understands why `invest_substation` is labeled). |
| `docs/METHODOLOGY_CONSOLIDATED.md` §8.1-8.3 | Update "best solar site" definition. Add the meaningful-share floor + substation-anchored search to §8.3 thresholds. |
| `tests/test_model.py:547-751` | Update `TestGridIntegrationCategory::test_invest_substation_kek_near_solar_far` (line 569) — fixture inputs change shape; fundamental contract of the function is unchanged. Add new test class `TestSubstationAnchoredSearch` for the new picker. |
| `tests/test_pipeline_site_resource.py` (new) | Golden-master test on a fixture with one Batam-shaped site and one Galang-Batang-shaped site, asserting the picker returns the anchored patch for the small-demand site and the best-PVOUT pixel for the large-demand site. |

### Resolved thresholds

**Q1 — Meaningful-share floor (`MEANINGFUL_SHARE_PCT`) — RESOLVED: 30%.**
User-confirmed. Patches that cannot cover at least 30% of `demand_2030_gwh` are thrown out and the search falls back to best-PVOUT.

**Q2 — Substation-co-location radius (`SUBSTATION_COLOCATION_RADIUS_KM`) — RESOLVED: 10 km.**

**Source check:** The current `SOLAR_TO_SUBSTATION_THRESHOLD_KM = 5 km` is *not* Indonesia-specific. It cites YSG Solar (3.2 km) and IFC Utility-Scale Solar Guide (8 km), both global benchmarks. The comment in `src/assumptions.py:232` notes: *"V3.1: Tightened from 10km to 5km per industry practice"* — i.e., the tool used to use 10 km. There is no Indonesian gen-tie distance dataset cited anywhere.

**Resolution: 10 km for the new anchor radius.** Rationale:
- Restores the original pre-V3.1 threshold, which had no Indonesian counter-evidence to motivate tightening
- Indonesian land economics + permitting density allow longer gen-ties than US/EU benchmarks assume
- The LCOE-aware tiebreaker in step 4 naturally penalises long connections — we don't need a tight radius to enforce economic discipline
- Keeps `SOLAR_TO_SUBSTATION_THRESHOLD_KM = 5 km` for the *classification* step in `grid_integration_category()`. The 10 km is only the *search radius* for finding candidate anchored patches. Two different concepts, two different constants.

**Q3 — Demand source for `required_mwp` — RESOLVED: `demand_2030_gwh`.**
Solar projects are sized for the lifetime, so 2030 makes sense.

**Q4 — Tiebreaker — RESOLVED.**
Picking the lowest-LCOE candidate (per step 4) replaces the earlier "closest substation" tiebreaker. The LCOE proxy already weighs PVOUT against connection cost, so no separate tiebreaker is needed.

---

## Verification

1. `uv run pytest tests/ -x` — all existing tests + new `TestSubstationAnchoredSearch` pass
2. `uv run python -m src.pipeline.build_fct_site_resource` — pipeline rebuilds in <2 min, no errors
3. `uv run python -m src.pipeline.build_fct_substation_proximity` — downstream rebuild succeeds
4. **Spot-check fixture sites:**
   - Batam Aero Technic — `solar_search_method == "substation_anchored"`, `grid_integration_category == "grid_ready"` (was `invest_substation`)
   - Galang Batang (large nickel KEK) — `solar_search_method` likely still `"best_pvout_fallback"` because demand is huge and best-PVOUT pixel is the only patch big enough; behavior unchanged
   - At least one site that gets `invest_substation` legitimately (e.g. far inland with no nearby substation at all) — confirm fallback fires correctly
5. **Audit table:** dump `solar_search_method` distribution across all 81 sites. Expect ~40-60% to flip from fallback to anchored. If <10% flip or >90% flip, thresholds Q1/Q2 are wrong.
6. Browser smoke: open ScoreDrawer for Batam Aero Technic — confirm Grid tab shows "Grid Ready" with anchor substation name.
7. Commit checklist: update `METHODOLOGY_CONSOLIDATED.md` §8 + `DATA_DICTIONARY.md` for new columns + `CHANGELOG.md` Unreleased.

---

## Risks

| Risk | Mitigation |
|---|---|
| Picker becomes much slower (substation × buildable polygon intersection per site) | 81 sites × ~5 nearby substations × spatial query ≈ 400 ops; should be <30s with pre-built polygon spatial index. Profile before assuming. |
| Anchored patch has materially worse PVOUT, dragging LCOE up enough to cross a threshold | The LCOE proxy in step 4 already prices this in — if PVOUT loss > connection cost saving, the picker stays with the high-PVOUT pixel anyway. Track `Δpvout_pct` per site in audit table for visibility. |
| Fallback fires too often → no apparent change | Tune `MEANINGFUL_SHARE_PCT` down (e.g. 20%) or `SUBSTATION_COLOCATION_RADIUS_KM` up (e.g. 15 km) and re-audit |
| Methodology change is harder to defend than expected | The current model is also a simplification; new model is closer to what a developer would actually do (build solar near existing substations). Document the reasoning explicitly in METHODOLOGY §8. |
| Tests in `TestGridIntegrationCategory` give false impression that grid logic broke | The function `grid_integration_category()` itself doesn't change. Only its *inputs* change. Update test fixture expectations, don't change function contract. |

---

## Out of scope

- Changing `grid_integration_category()` itself — function contract stays identical
- Re-doing wind buildable resource picker (`fct_site_wind_resource`) — wind density is much lower, search behavior is different, defer
- Multiple anchored patches per site (e.g. dual-substation feed) — add later if needed
- Changing the classification thresholds (`SOLAR_TO_SUBSTATION_THRESHOLD_KM = 5 km`, `KEK_TO_SUBSTATION_THRESHOLD_KM = 15 km`) — only the search radius changes; classification stays as-is
