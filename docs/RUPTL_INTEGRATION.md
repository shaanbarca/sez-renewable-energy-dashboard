# How RUPTL Connects to the Dashboard

**Last updated:** 2026-05-10 (after F5 / PR #33 lands the third RUPTL feed; revised same day per `docs/refinement/RUPTL_INTEGRATION_review_2026-05-10.md` — fixes substation-utilization direction in Example A, §V.6 (not §III) for Feed 1, §V.11 (not §V.9) for Feed 3, GEAS = "Green Energy Auction Scheme", F13 deprioritization clarified)

This doc traces every place the dashboard reads PLN's RUPTL ("Rencana Usaha Penyediaan Tenaga Listrik" — PLN's 10-year electricity master plan), how the data is processed, and which dashboard outputs (action flags, columns, UI cards) it drives.

It's organised top-down:
1. **Why RUPTL matters** — the dashboard's claim and what would be wrong without RUPTL
2. **Three feeds at a glance** — the table you'd start with on a whiteboard
3. **Per-feed deep dive** — source → extraction → CSV → scorecard → flag → UI
4. **End-to-end examples** — three sites, what RUPTL changes about each
5. **What's not yet wired** — deferred work and the rationale

---

## 1. Why RUPTL matters

The dashboard's core claim per site is: *"Here's how much it costs to deliver clean power, and here's whether you should `solar_now` / `invest_transmission` / wait." The cost numbers come from solar resource + LCOE math; the action flags compare those costs to a **comparator** (PLN tariff, BPP, captive coal cost) and decide.

Without RUPTL, we'd be assuming PLN's grid is everywhere, on time, with the right capacity. RUPTL is what makes the dashboard honest about the *PLN side* of that comparison:

| Question we'd otherwise duck | RUPTL section that answers it |
|---|---|
| "Is enough new RE planned in this region by 2030 that the policy support exists?" | §III RE-base / ARED supply forecasts |
| "Does the substation we'd connect to actually have headroom now, or is it RUPTL-planned for an upgrade?" | Lampiran A/B/C (per-province GI plans) |
| "Is the new transmission line we're recommending even in PLN's plan, or only `kajian lebih lanjut`?" | §V.9 (regional Pengembangan Sistem Penyaluran) |

Three different questions → three independent RUPTL feeds. Each is wired into the dashboard separately.

---

## 2. The three feeds at a glance

| Feed | Source pages | Pipeline output | Key scorecard columns | Action flags driven | UI surface |
|---|---|---|---|---|---|
| **(1) Regional pipeline timing** | RUPTL §V.6 RE-base / ARED energy-mix projections per region (V.6.2 Sumatera, V.6.3 JAMALI, V.6.4 Kalimantan, V.6.5 Sulawesi, V.6.6 Maluku/Papua/NT) | `fct_ruptl_pipeline.csv` | `green_share_geas`, `green_share_geas_proportional_pct` | `solar_now` (gate), `plan_late` (fires) | Bottom Panel "RUPTL Context" tab + Score Drawer Economics tab "GEAS Green Share" |
| **(2) Per-substation upgrade plans** | RUPTL Lampiran A/B/C (per-province "Rincian Rencana Pembangunan Gardu Induk") | `fct_substation_ruptl_signal.csv` | `substation_utilization_pct_effective`, `ruptl_project_type`, `ruptl_strongest_status`, `ruptl_earliest_target_year`, `ruptl_mva_added_total` | `invest_substation` (gates capacity assessment) | Score Drawer Grid tab "Substation Capacity" card |
| **(3) Inter-system transmission feasibility** (F5, 2026-05-09) | RUPTL §V.11 *Interkoneksi Antar Sistem* (V.11.1 antar-sistem, V.11.2 antar-pulau / inter-island, V.11.3 antar-negara / cross-border). A small number of intra-region links (e.g. Tongkonan–Bangkir) sit under §V.9.4 instead. | `fct_transmission_link_ruptl_signal.csv` | `recommended_grid_link_status`, `recommended_grid_link_section`, `comparator_feasibility` | **None yet — deferred** | **None yet — deferred** |

The three feeds cover progressively more local questions: country-level supply planning → substation-level capacity → corridor-level feasibility.

---

## 3. Per-feed deep dive

### Feed 1 — Regional pipeline timing (`fct_ruptl_pipeline`)

**What RUPTL section.** §V.6 — *Energy mix projections* under RE Base / ARED scenarios per region (V.6.1 Indonesia overall, V.6.2 Sumatera, V.6.3 JAMALI, V.6.4 Kalimantan, V.6.5 Sulawesi, V.6.6 Maluku/Papua/NT). These are the *planned* MW additions per technology per year — distinct from §III, which is *resource potential* (what could be built).

The numbers are hardcoded into the pipeline rather than PDF-extracted because they're stable and only ~50 numbers per region.

**Pipeline.** `src/pipeline/build_fct_ruptl_pipeline.py` writes one row per `(grid_region_id, year)` with columns like `plts_new_mw_re_base` (solar new build under RE-base), `pltb_new_mw_re_base` (wind), etc.

**How it becomes a per-site signal.** The site sees the regional pipeline through **GEAS** (Green Energy Auction Scheme) allocation:

- `compute_geas_proportional()` (`src/model/basic_model.py:1793`) takes the region's pre-2030 solar additions and pro-rates them across sites by demand share.
- Each site gets `geas_alloc_proportional_gwh` = its share of the regional RUPTL solar by 2030.
- `green_share_geas = min(1, geas_alloc / site_demand_2030)` — what % of the site's 2030 demand could in theory be claimed against PLN's regional pipeline under proportional REC attribution.

> **What `green_share_geas` actually verifies (and doesn't).** This is a **REC-attribution check**, not a decarbonization-quality check. Hyperscalers (24/7 CFE methodology), CBAM-exposed industrial exporters (Scope-2 attestation), and DFI investors (additionality screens) all **reject REC-based attribution** regardless of allocation method — for those buyer classes, a high `green_share_geas` does *not* mean the site is genuinely decarbonized. They need direct PPA, hourly physical matching, and additionality. The signal remains useful for the smaller buyer class (mid-tier industrial under softer ESG frameworks) that does accept REC attribution as a directional indicator. The Score Drawer Economics tab now flags this with a "REC-based · deprioritized" chip on the GEAS row. See `docs/refinement/F13_GEAS_deprioritization_2026-05-08.md`.

**Two action flags read this:**

1. **`solar_now`** (`basic_model.py:1482`) requires **both** the LCOE check AND `green_share_geas >= GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD`. The GEAS gate is therefore better understood as a **PLN-policy-availability check** ("the regional pipeline is large enough to back even the weakest scope-2 claim") than as a decarbonization-quality check. Useful as a minimum-viability filter; *not* sufficient on its own to mark a site as decarbonized for hyperscaler / CBAM-exporter use cases.

2. **`plan_late`** (`basic_model.py:1461`) is **purely RUPTL-derived**:
   ```python
   plan_late = post2030_share >= PLAN_LATE_POST2030_SHARE_THRESHOLD  # 0.60
   ```
   Where `post2030_share` is the fraction of regional RUPTL solar additions scheduled for 2031–2034 (vs. 2025–2030). Fires when PLN's plan is back-loaded — most of the new solar comes after 2030, so a 2030-target solar buyer can't rely on it.

**Where it shows in UI:**
- **Bottom panel "RUPTL Context" tab** (`frontend/src/components/charts/RuptlChart.tsx`) — area chart of RE pipeline additions per year, stacked by region. Direct view of the raw `fct_ruptl_pipeline.csv`.
- **Score Drawer Economics tab** (`EconomicsTab.tsx:533–536`) — "GEAS Green Share" stat row with the per-site %.
- **Walkthrough modal** (`WalkthroughModal.tsx:278–282`) — guides users to cross-reference `plan_late` sites against the RUPTL chart.

---

### Feed 2 — Per-substation upgrade plans (`fct_substation_ruptl_signal`)

**What RUPTL section.** Lampiran A (Sumatera + Kalimantan), Lampiran B (Jawa-Madura-Bali), Lampiran C (Sulawesi + Maluku + Papua + Nusa Tenggara) — per-province *"Rincian Rencana Pembangunan Gardu Induk"* (Detailed Substation Development Plan) tables. Each row is one substation upgrade: name, voltage, project type (new/extension/uprate), MVA added, target year, status (`konstruksi` / `committed` / `pengadaan` / `rencana` / `studi`).

**Pipeline (two stages):**
1. `src/pipeline/pdf_extract_ruptl_substations.py` — pdfplumber extracts ~600 rows from the Lampiran tables (page ranges hardcoded per province in `PROVINCE_RANGES`).
2. `src/pipeline/build_fct_substation_ruptl_signal.py` — fuzzy-matches each Lampiran row against the substation geojson (`data/substation.geojson`) using normalised names + province scoping. Output: per-substation row with `substation_utilization_pct_effective`, `ruptl_project_type`, `ruptl_strongest_status`, `ruptl_earliest_target_year`, `ruptl_mva_added_total`, `ruptl_match_confidence`.

**How it becomes a per-site signal — explicit logic chain.**

The Lampiran-derived signal flows through 4 distinct steps before it can fire `invest_substation`. Each step is a function call with a clear input/output. The most important non-obvious thing to know up front: **`ruptl_mva_added_total` is informational only — it does NOT compose into the available-capacity math.** The math uses the existing nameplate × the RUPTL-derived utilization tier; the planned MVA addition is narrated in the Score Drawer but not added to capacity. (Whether that's the right call long-term is a separate methodology question.)

#### Step 1 — RUPTL match → per-substation utilization tier

Set in `build_fct_substation_proximity.py::_ruptl_utilization_for_substation()`. METHODOLOGY §8.4a documents the rationale:

| RUPTL `project_type` for the substation | `substation_utilization_pct_effective` | Why |
|---|---|---|
| `uprate` | **85%** | PLN scheduled transformer replacement → asset is currently most-congested |
| `extension` | **75%** | Adding bay/feeder → capacity-limited on some dimension |
| `line_bay` | **70%** | Minor addition → slightly above fleet average |
| `none` (matched in Lampiran but no upgrade in 10-year horizon) | **55%** | PLN's plan ignores it → likely a headroom asset |
| unmatched (not found in Lampiran A/B/C) | **65%** | Fleet-default fallback |

Counter-intuitive bit: **the more aggressive PLN's RUPTL plan for the substation, the *less* headroom we assume today**. The plan is itself the evidence the asset is hot.

#### Step 2 — Override priority (`src/dash/logic/grid.py:88–96`)

The RUPTL tier from Step 1 isn't always what the site sees. Three-way priority:

| If... | Then `util_pct` becomes... | Rationale |
|---|---|---|
| `nearest_substation_capacity_source` starts with `"proxy_"` | `1 − HOSTING_CAPACITY_AVAILABILITY_PCT` (= 70%) | Voltage-class proxy nameplate is itself a guess; layering RUPTL on top would double-count uncertainty |
| User dragged the global utilization slider off the fleet default (65%) | The slider value, applied uniformly to all sites | Stress-test mode for scenario comparison — overrides per-substation RUPTL signal |
| Neither of the above | The RUPTL tier from Step 1 (or 65% if unmatched) | Default behaviour |

#### Step 3 — Available capacity formula (`src/model/basic_model.py:1735` `capacity_assessment`)

Once `util_pct` is locked in:

```
available_mva = substation_capacity_mva × (1 − util_pct)
available_mw  = available_mva × power_factor               (≈ 0.95)
ratio         = available_mw / planned_solar_capacity_mwp
```

Traffic-light:

| `ratio` | `capacity_assessment` | Substation upgrade cost |
|---|---|---|
| ≥ 1.0 | `green` | $0 — fits, no uprating |
| 0.5 – 1.0 | `yellow` | proportional partial deficit |
| < 0.5 | `red` | major upgrade needed |
| nameplate unknown | `unknown` | conservative — no penalty |

Worth re-stating: **`ruptl_mva_added_total` is not in this formula.** A substation with a RUPTL `uprate` plan adding +200 MVA by 2027 still has its `available_mva` computed against the *current* nameplate at 85% utilization. The +200 is a string surfaced to the Score Drawer narrative, nothing more. (Argument for the current behaviour: the addition might land after the project's COD, the exact COD is uncertain, and crediting un-built capacity to today's headroom would over-count. Argument against: it ignores otherwise-credible PLN commitments. METHODOLOGY §8.4a documents the tier mapping but is silent on this composition rule — future cleanup item.)

#### Step 4 — Category gate that fires `invest_substation` (`basic_model.py:1708–1716`)

Inside `grid_integration_category()`, after the within-boundary and proximity checks:

| If... | Then category becomes... |
|---|---|
| `solar_capacity_mwp > available_mva` (note: MVA, not MW — slight conservatism vs the traffic-light formula) | `invest_substation` |
| Otherwise (and other proximity checks pass) | One of `grid_ready` / `invest_transmission` / `grid_first` per the proximity logic |

So `invest_substation` fires when planned solar exceeds the substation's available headroom. The action flag is **the category itself** — there's no separate boolean.

**Where each piece shows in the UI:**

- **Score Drawer Grid tab → "Substation Capacity" card** (`GridTab.tsx:384–427`) — narrative built from the RUPTL fields:
  > *"Utilization default 75% (PLN RUPTL plans an extension adding +200 MVA by 2027 — committed)"*
- The narrative templates live in `RUPTL_PROJECT_LABELS` and `RUPTL_STATUS_LABELS` (`GridTab.tsx:21–35`).
- The `+MVA` line is *narrative*; the `75%` (utilization) is the value that actually drove the math.

**Indirect effect on other action flags.** `solar_now` / `cbam_urgent` both require `grid_integration_category` not to be `invest_substation` — so a site that fails Step 4 also can't fire those flags regardless of LCOE.

---

### Feed 3 — Inter-system transmission feasibility (F5, PR #33)

**What RUPTL section.** Primarily §V.11 — *Interkoneksi Antar Sistem*:
- §V.11.1 antar-sistem (system-to-system within a regional grid)
- §V.11.2 antar-pulau (inter-island, e.g. Sumatra–Java HVDC, Bangka–Belitung, Seram–Ambon, Java–Lombok)
- §V.11.3 antar-negara (cross-border, e.g. Malaka GI near Timor-Leste, Papua–PNG)

A small number of intra-region transmission links (e.g. Tongkonan–Bangkir, an intra-Sulawesi link) sit under §V.9.4 *Pengembangan Sistem Penyaluran Sulawesi* instead. The seed CSV today is 6/8 §V.11 + 1/8 §V.9.4 + 1/8 ambiguous (Sulbagsel–Baubau floating tower could fall under either).

> **Legacy file/variable name.** The raw CSV is `data/raw/ruptl_v9_transmission_links.csv` and the path is hardcoded into `src/pipeline/build_fct_transmission_link_ruptl_signal.py`. The `v9` suffix is a misnomer from an early reading that thought all entries lived at §V.9 — now corrected to §V.11 (plus the §V.9.4 minority). Renaming the file would propagate through CI, golden fixtures, and the data-loader merge — not worth the churn for a citation correction. The actual section anchor is set per-row by the `ruptl_section` column in the CSV (e.g. `V.11.2`, `V.9.4`).

**Pipeline.** `src/pipeline/build_fct_transmission_link_ruptl_signal.py` reads the manually compiled `data/raw/ruptl_v9_transmission_links.csv` (8 seed entries today: Sumatra–Java HVDC, Java–Lombok, Bangka–Belitung, Sulawesi internal, Sulbagsel–Baubau, Seram–Ambon, Malaka, Papua–PNG). Outputs `outputs/data/processed/fct_transmission_link_ruptl_signal.csv`.

**How it becomes a per-site signal — region rollup.** Today's implementation takes a **region-level worst-case** rather than per-link match (per-link match would need an inter-substation graph; that's a v4.x scope item). In `data_loader.py`:

```python
region_status = region_worst_status_map(links_df)
# {SULAWESI: 'not_feasible', JAVA_BALI: 'under_study',
#  PAPUA: 'cross_border', MALUKU: 'under_study', ...}
resource["recommended_grid_link_status"] = resource["grid_region_id"].map(...)
```

Severity ordering (most pessimistic first): `not_feasible` < `under_study` < `cross_border` < `pre_construction` < `in_construction`.

Then in `enrich_grid_passthroughs()` (`scorecard.py:97`):

```python
if grid_integration_category in {'invest_transmission', 'invest_substation', 'grid_first'}:
    if link_status == 'not_feasible':
        comparator_feasibility = 'pln_tariff_infeasible_captive_only'
    elif link_status in {'under_study', 'cross_border'}:
        comparator_feasibility = 'pln_tariff_uncertain_grid_first_required'
    else:
        comparator_feasibility = 'pln_tariff_feasible'
else:
    comparator_feasibility = 'pln_tariff_feasible'  # site doesn't need new transmission
```

The integration-category guard is important: a site that's already grid-ready doesn't care about feasibility of new lines.

**Action-flag impact today: NONE.** The column is informational only. The methodology change (using captive cost as the comparator when feasibility is `pln_tariff_infeasible_captive_only`, rewiring `compute_action_flag()`) is the **explicitly deferred follow-up** — see §5.

**Where it shows in UI today: NONE.** The columns are in the API response and types but not yet rendered in any tab. Deferred to a follow-up.

---

## 4. End-to-end examples

These are concrete walk-throughs of how RUPTL changes the dashboard's verdict per site. Three sites that exercise different RUPTL paths.

### Example A — Cilegon (Java, near grid)

- **Feed 1 (regional pipeline):** Java-Bali RUPTL pre-2030 solar additions are large and front-loaded → high `green_share_geas` for the region → Cilegon clears the GEAS gate for `solar_now`. `post2030_share` is below the 0.60 threshold → `plan_late` does NOT fire.
- **Feed 2 (substation):** Cilegon sits in a heavily-loaded Java industrial belt. The nearest substation in `data/substation.geojson` matches RUPTL Lampiran B with `ruptl_project_type = 'extension'`, `ruptl_strongest_status = 'committed'`, `ruptl_mva_added_total = 200` by 2027. Walking the chain:
   1. **Step 1 (tier):** `extension` → `substation_utilization_pct_effective = 75%` per METHODOLOGY §8.4a. *Above* the 65% fleet default — PLN's published plan is evidence the asset runs hot today.
   2. **Step 2 (override):** Cap source is `actual` (not proxy), user is at default slider → tier flows through.
   3. **Step 3 (capacity):** `available_mva = nameplate × 0.25`. The `+200 MVA` plan is **not** added in. So if Cilegon's planned solar is small relative to that 25%-of-nameplate, ratio ≥ 1.0 → green. Larger → yellow or red.
   4. **Step 4 (category):** if `solar_capacity_mwp > available_mva`, fires `invest_substation`. The substation upgrade cost is then proportional to the deficit; the `+200 MVA` shows in the UI narrative but is informational only.

The takeaway: an `extension` signal doesn't help a Cilegon-sized solar project clear the substation gate — it tightens it. The plan's *value* shows up as informational context (PLN intends to add capacity), but today's math runs on today's nameplate.
- **Feed 3 (V.11 link):** Java-Bali region rollup is `under_study` (Sumatra–Java HVDC SKTET in §V.11.2 is `kajian lebih lanjut`), but Cilegon's `grid_integration_category` is already `grid_ready`/`within_boundary` → the `enrich_grid_passthroughs` guard returns `pln_tariff_feasible` regardless of region rollup. Feed 3 is silent for this site.
- **Net action flag:** `solar_now` fires when LCOE wins, GEAS gate is met, and the substation capacity check (Feed 2) clears for the planned solar size.

### Example B — Morowali (Sulawesi, nickel cluster)

- **Feed 1:** Sulawesi RUPTL solar additions are smaller and more back-loaded → `green_share_geas` is moderate; whether it clears the `solar_now` gate depends on the threshold. Sulawesi `post2030_share` is high → `plan_late` may fire.
- **Feed 2:** The IMIP captive-power-heavy area has limited PLN substation upgrade plans nearby in Lampiran C → fleet-default 65% utilization → `available_capacity_mva` modest → `invest_substation` may fire if planned solar size is large.
- **Feed 3 (F5):** Sulawesi region rollup is `not_feasible` (the Tongkonan–Bangkir intra-Sulawesi link in §V.9.4 is explicitly *tidak layak* — note this is one of the §V.9 entries in the seed CSV; most other entries are §V.11). If Morowali's `grid_integration_category` is `invest_transmission` → `comparator_feasibility = pln_tariff_infeasible_captive_only`. **Today this is just a column on the row** — the action flag still computes against PLN tariff. After the deferred wiring lands, the comparator would become captive coal cost → solar's competitive gap is recomputed against captive (not PLN) → `solar_now` may flip to `not_competitive` or vice-versa, depending on local captive cost.

### Example C — Seram (Maluku, small-island grid)

- **Feed 1:** Maluku RUPTL is sparse → `green_share_geas` close to zero → `solar_now` does not clear the gate even if LCOE wins. `plan_late` fires (post2030 share is high).
- **Feed 2:** Few substations in Lampiran C for Maluku → fleet-default utilization → `invest_substation` likely fires.
- **Feed 3 (F5):** Maluku region rollup is `under_study` (Seram–Ambon deep-sea trench cable in §V.11.2 is `kajian lebih lanjut`). If category is `invest_transmission` → `comparator_feasibility = pln_tariff_uncertain_grid_first_required`. Informational today.
- **Net action flag:** `plan_late` + `invest_substation`. Site is flagged as needing both grid policy + grid infrastructure intervention.

---

## 5. What's not yet wired (deferred)

### F5 follow-up: action-flag flip when `comparator_feasibility = pln_tariff_infeasible_captive_only`

**Intended logic:**
```python
if comparator_feasibility == 'pln_tariff_infeasible_captive_only':
    comparator = captive_cost   # not PLN tariff
    solar_competitive_gap_pct  = recompute against captive
    invest_transmission flag   = may flip OFF (it's not feasible)
    not_competitive flag       = may flip ON if solar > captive
```

This changes outputs — sites in Sulawesi might switch from `invest_transmission` to a captive-cost-based label. Risky to ship without domain validation, so it's a separate PR. Tracked in #7's follow-up notes.

### Feed 3 → per-link site matching

Today's heuristic uses **region** worst-case. A truer answer matches each site's specific recommended new-transmission corridor (from `fct_substation_proximity`'s nearest substation + the next hop in PLN's grid topology) against the link table. That requires an inter-substation graph — out of scope for v4.0.5.

### Feed 1 → GEAS empirical allocation (F13, deprioritized — preserved-but-marked)

Today's GEAS allocation is proportional by demand share (`geas_alloc_proportional_gwh`). An empirical variant (F13 — distance-decay × region-multiplier on top of the proportional baseline) was speced for v4.0.5 but **deprioritized 2026-05-08** per the May 2026 strategic reprioritization. Reasoning (full text in `docs/refinement/F13_GEAS_deprioritization_2026-05-08.md`):

- The buyer classes that drive the dashboard's primary use cases (hyperscalers seeking 24/7 CFE, CBAM-exposed industrial exporters seeking Scope-2 attestation, DFI investors screening for additionality) **explicitly reject REC-based decarbonization accounting** — at any allocation method.
- For these audiences, the difference between proportional and empirical REC allocation is irrelevant; getting REC-allocation precision "right" doesn't change the analytical conclusion.
- The proportional default *stays* — it remains useful for the smaller buyer class (mid-tier industrial under softer ESG frameworks) that does accept REC attribution as a directional signal.

**State today (preserved-but-marked, not removed):** the F13 implementation is **kept in the codebase** with prominent deprioritization markers, rather than physically stripped. This is so the work can be revisited cheaply if the use case changes:

| What's in code | Status |
|---|---|
| `geas_alloc_empirical()` (`src/model/basic_model.py:231`) | ⚠️ Preserved with "DEPRIORITIZED" docstring marker. Not the operative path. |
| `REGION_GEAS_MULT`, `REGION_LOAD_CENTRE_LATLON`, `GEAS_DISTANCE_DECAY_*`, `GEAS_RUPTL_CAPACITY_FACTOR` (`src/assumptions.py:686+`) | ⚠️ Preserved with "DEPRIORITIZED" block-comment header. |
| Empirical scorecard columns (`geas_alloc_empirical_gwh`, `green_share_geas_empirical_pct`, `geas_allocation_used`) | Still emitted by the pipeline. Not surfaced in the UI. |
| Operative GEAS column on the scorecard | `green_share_geas` (proportional). Surfaced in Score Drawer Economics tab with the new "REC-based · deprioritized" chip flagging the REC-attribution caveat. |
| Direct-PPA / 24/7 CFE GEAS variant | **Not built.** Out of scope for v4.x; would be a separate methodology layer. |

**Revisit if** (a) a REC-accepting buyer class becomes a primary use case, (b) PLN's GEAS framework evolves to support hourly matching / additionality, or (c) a user explicitly requests the empirical variant. Direct-GEAS (PPA-based / hourly-matched) is a separate future addition, not a revival of F13.

### Feed 3 → UI surfacing

The F5 columns (`recommended_grid_link_status`, `comparator_feasibility`) are in the API response and types but not rendered anywhere in the UI. Surfacing them in the Score Drawer Grid tab (alongside the existing substation card) is a follow-up.

---

### v4.3 milestone — Methodology Transparency (covers Feeds 2 + 3)

Two of the deferred items above (Feed 2's substation utilization tier override + Feed 3's transmission-feasibility action-flag flip + UI surfacing) are paired into a single v4.3 release theme: **"Methodology Transparency"**. Feature plan: [`docs/refinement/v4_3_methodology_transparency_refinement.md`](refinement/v4_3_methodology_transparency_refinement.md).

| Feature | What it ships | Closes which deferred item |
|---|---|---|
| **M-AT1 — Substation Utilization Transparency** | Per-substation utilization override on the Score Drawer Grid tab; confidence-tier badge (`PLN-published` / `RUPTL-estimated` / `User-set`); methodology link to §8.4a | Feed 2's missing override at the right resolution + missing UI confidence visibility |
| **M-T1 — Transmission Feasibility Action-Flag Flip** | Wires the deferred `comparator_feasibility = pln_tariff_infeasible_captive_only` → captive-cost comparator flip in `compute_action_flag()`; surfaces the column with a validation-tier badge (`expert_confirmed` / `single_source` / `prose_inferred`) | Feed 3's deferred action-flag wiring + missing UI surfacing |

**Why paired:** both require a confidence-tier badge component, a Methodology Drawer side panel, and URL-state encoding for overrides. Building that infrastructure once and exercising it twice is materially cheaper than two separate releases. The shared pattern also becomes the template for **M-AT2 (GEAS, when un-deferred)**, **M-AT3 (demand intensity)**, **M-AT4 (captive cost)** — see the plan's "Pattern" section.

**Validation prerequisite (M-T1).** The 8 seed entries in `data/raw/ruptl_v9_transmission_links.csv` need confidence tagging via expert outreach (IESR, ESDM, JETP CPS authors) before the action-flag flip can ship. That outreach is calendar-bound and should start before the code work.

**Tracking:** [GitHub issue #34](https://github.com/shaanbarca/eez/issues/34) (filed 2026-05-10).

---

## 6. File map

If you want to navigate the code:

| Concern | File |
|---|---|
| Hardcoded RUPTL §III pipeline numbers | `src/pipeline/build_fct_ruptl_pipeline.py` |
| Lampiran A/B/C PDF extraction | `src/pipeline/pdf_extract_ruptl_substations.py` |
| Lampiran → substation geojson matcher | `src/pipeline/build_fct_substation_ruptl_signal.py` |
| §V.9 link CSV passthrough + region rollup | `src/pipeline/build_fct_transmission_link_ruptl_signal.py` |
| Raw §V.9 entries (manually curated) | `data/raw/ruptl_v9_transmission_links.csv` |
| Schema docs for raw RUPTL files | `data/raw/README.md` |
| GEAS allocation math | `src/model/basic_model.py::compute_geas_proportional()` |
| Action-flag definitions (`plan_late`, `solar_now` GEAS gate, `invest_substation`) | `src/model/basic_model.py::action_flags()` |
| Per-site grid-integration math (uses RUPTL substation utilization) | `src/dash/logic/grid.py::compute_grid_integration()` |
| Scorecard enricher (where F5 `comparator_feasibility` derives) | `src/dash/logic/scorecard.py::enrich_grid_passthroughs()` |
| Data loader (merges all three feeds onto resource_df) | `src/dash/data_loader.py::prepare_resource_df()` |
| RUPTL chart tab | `frontend/src/components/charts/RuptlChart.tsx` |
| Substation capacity card narrative | `frontend/src/components/panels/scoredrawer/GridTab.tsx` |
| GEAS green share row | `frontend/src/components/panels/scoredrawer/EconomicsTab.tsx` |

---

## TL;DR

RUPTL is **not** purely descriptive in the dashboard — it actively drives action flags through two of three feeds:

1. **Regional pipeline timing** (§V.6 RE-base / ARED) gates `solar_now` (via GEAS = Green Energy Auction Scheme) and fires `plan_late`
2. **Per-substation upgrade plans** (Lampiran A/B/C) drive substation utilization → headroom → `invest_substation`. An `uprate` signal means the substation is *constrained* (85% utilization), not generous; a `none` match means below-fleet utilization (55%) — opposite directions.
3. **Inter-system transmission feasibility** (§V.11, F5) is wired to a `comparator_feasibility` column but the action-flag flip is intentionally deferred — it's a real output change that needs domain validation

Each feed answers a different scope of question (regional planned mix / substation-asset capacity / inter-system corridor feasibility). Together they're how the dashboard avoids assuming PLN's grid will arrive on time, with capacity, where the sites need it.

---

## 7. Wiki references

For the analyst tracing dashboard claims back to primary sources:

- **`sources/PLN RUPTL 2025-2034.md`** — section-by-section structural ingest of the actual RUPTL PDF (`raw/b967d-ruptl-pln-2025-2034-pub-.pdf`). Use to verify any specific section anchor cited above.
- **`syntheses/Indonesia Grid Infrastructure and Renewable Adoption.md`** — the structural argument for *why* RUPTL transmission buildout is the binding constraint on RE integration (the ~5–6× grid-investment gap; IEA APS comparison).
- **`syntheses/Indonesia Dashboard Methodology Review.md`** §V3.8 — the wiki's prior review of the substation-utilization methodology that landed Feed 2.
- **`docs/refinement/RUPTL_INTEGRATION_review_2026-05-10.md`** — the wiki-side review pass that drove this doc's 2026-05-10 revisions (substation-direction inversion, §V.6 vs §III citation, §V.11 vs §V.9 anchor, GEAS expansion, F13 deprioritization).
- **`docs/refinement/F13_GEAS_deprioritization_2026-05-08.md`** — the May 2026 strategic-reprioritization decision that deferred the empirical GEAS allocation work.
