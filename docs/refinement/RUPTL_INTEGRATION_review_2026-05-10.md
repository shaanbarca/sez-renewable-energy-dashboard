# RUPTL_INTEGRATION.md — wiki-side review

**Reviewed:** `docs/RUPTL_INTEGRATION.md` (last-updated header 2026-05-10, after F5 / PR #33)
**Review date:** 2026-05-10
**Reviewer:** Wiki LLM (Energy/Renewables vault)
**Method:** Cross-checked the doc against wiki primary sources (`sources/PLN RUPTL 2025-2034.md`, `syntheses/Indonesia Grid Infrastructure and Renewable Adoption.md`, `syntheses/Indonesia Dashboard Methodology Review.md`), the dashboard's own `METHODOLOGY_CONSOLIDATED.md`, `EXECUTIVE_SUMMARY.md`, and the existence of every code path the doc cites.

---

## Verdict

**The doc is structurally good** — top-down framing, three-feed decomposition matches METHODOLOGY §8.4a + §8.5a, the end-to-end site examples are the right pedagogical move, and every code path it cites exists on disk. **Do not rewrite.**

But cross-checked against the methodology and the wiki's reading of the actual RUPTL PDF, **three substantive issues** need resolution before this becomes a reviewer-facing reference, plus two smaller hygiene items.

This file flags issues only — no edits applied to `RUPTL_INTEGRATION.md` or `METHODOLOGY_CONSOLIDATED.md`. Handoff is deliberate.

---

## Issues (priority order)

### 1. ⚠️ Substation utilization direction is inverted in Example A

**Where:** `RUPTL_INTEGRATION.md:152` (Example A — Cilegon).

**The claim:**

> *"Cilegon's nearest substation has a RUPTL-planned uprate by 2026 (`ruptl_strongest_status = 'konstruksi'`, `ruptl_mva_added_total = 250`). Effective utilization drops below 65% default → `available_capacity_mva` is generous → `invest_substation` does NOT fire."*

**The methodology says the opposite.** `METHODOLOGY_CONSOLIDATED.md:1059`:

> *"PLN only schedules uprates/extensions for substations that are already capacity-constrained, so a published upgrade plan is strong evidence the asset is running hotter than the fleet average. Conversely, substations absent from the plan's 10-year horizon are probably headroom assets."*

Tier mapping (`METHODOLOGY.md:1063`):

| RUPTL project type | `substation_utilization_pct_effective` |
|---|---|
| `uprate` | **85%** |
| `extension` | 75% |
| `line_bay` | 70% |
| `none` (matched, no upgrade) | 55% |
| no match | 65% (fleet default) |

So an `uprate` substation should show **85%** utilization (less headroom, more likely to fire `invest_substation`), not "drops below 65% default."

**Two ways to resolve:**

(a) **The example is wrong** — fix the narrative so Cilegon shows higher utilization on the existing nameplate (uprate evidence = constrained today), and explain that `invest_substation` is gated by something else (e.g., the planned uprate landing before the project's COD, or `available_capacity_mva` adding `ruptl_mva_added_total` on top of the constrained existing nameplate).

(b) **The methodology is incomplete on composition** — if the actual code adds `ruptl_mva_added_total` to capacity headroom regardless of utilization tier (effectively: "yes, existing nameplate is constrained at 85%, but +250 MVA lands by 2026 so available_capacity_mva is generous"), then METHODOLOGY §8.4a needs to describe that compositional rule. Right now §8.4a stops at the tier-utilization mapping and never explains how MVA additions enter the capacity calc.

The right fix depends on what `compute_grid_integration()` in `src/dash/logic/grid.py:95` actually computes. **Recommend reading the code, then fixing whichever doc is wrong.** This is the most concerning issue because it's a logical inversion that will confuse a reviewer.

---

### 2. Feed 1 source pointer probably mis-cites §III when content lives at §V.6

**Where:** `RUPTL_INTEGRATION.md:34` (Feed table) + line 48 (Feed 1 deep dive):

> *"§III RE-base / ARED supply forecasts (per-region MW additions per year)"*

**Wiki source ingest disagrees.** Per `sources/PLN RUPTL 2025-2034.md` (ingested 2026-05-03 from the actual RUPTL PDF at `raw/b967d-ruptl-pln-2025-2034-pub-.pdf`):

- **§III** is **Resource assessments** — what *could* be built, by resource type:
  - §III.2.1 Geothermal, §III.2.2 Hydro, §III.2.3 Solar, §III.2.4 Waste-to-energy, §III.2.5 Biomass/biogas, §III.2.6 Wind, §III.2.7 Marine, §III.2.8 Biofuels, §III.2.9 PLTD-to-EBT
- **§V.6** is **Energy mix projections** — what's *planned* to be built, per region under RE Base / ARED:
  - §V.6.1 Indonesia overall, §V.6.2 Sumatera, §V.6.3 JAMALI, §V.6.4 Kalimantan, §V.6.5 Sulawesi, §V.6.6 Maluku/Papua/NT

The hardcoded numbers in `build_fct_ruptl_pipeline.py` (planned per-region MW additions per year, by technology, 2025–2034) sound like §V.6 (per-region planned mix), not §III (resource potential).

**Recommendation:** Verify against the PDF — read the page range the pipeline numbers were transcribed from. Likely the citation in `RUPTL_INTEGRATION.md` should read *"§V.6 RE-base / ARED energy-mix projections per region"* rather than §III. Same fix in `METHODOLOGY_CONSOLIDATED.md` §8.4a / §11 wherever §III is cited as the source for *planned* additions.

---

### 3. §V.9 vs §V.11 — likely both exist, current attribution may be wrong

**Where:** `RUPTL_INTEGRATION.md:108` and `METHODOLOGY_CONSOLIDATED.md:1112` both flag:

> *"F5's spec referenced §V.11 — that anchor is from an older RUPTL version. The 2025–2034 RUPTL has the relevant content at §V.9.x per region."*

**Wiki source ingest says §V.11 is alive in 2025–2034.** From `sources/PLN RUPTL 2025-2034.md`:

> *"§V.11 covers system interconnection (V.11.1 antar-sistem, V.11.2 antar-pulau, V.11.3 antar-negara). Inter-island connections (V.11.2) are particularly relevant for the wiki's analyses of geographically stranded renewables (Sumba wind, Kalimantan hydro). Cross-border grid links (V.11.3) include Sarawak-Indonesia and possible ASEAN Power Grid integration."*

**Most likely reading:** Chapter V has both §V.9 (regional *Pengembangan Sistem Penyaluran* — per-region transmission expansion within a region) AND §V.11 (Interkoneksi Antar Sistem — inter-system / inter-island / cross-border links). They cover different scopes.

The 8 seed entries in `data/raw/ruptl_v9_transmission_links.csv` are predominantly **inter-island / cross-border**:

| Entry | Naturally lives in |
|---|---|
| Sumatra–Java HVDC | §V.11.2 (antar-pulau) |
| Java–Lombok | §V.11.2 |
| Bangka–Belitung | §V.11.2 (Bangka and Belitung islands ↔ Sumatera) |
| Seram–Ambon | §V.11.2 (deep-sea trench, inter-island) |
| Sulawesi internal Tongkonan–Bangkir | could be §V.9.4 (intra-Sulawesi transmission) |
| Sulbagsel–Baubau floating tower | could be §V.9.4 or §V.11.2 |
| Malaka GI | §V.11.3 (cross-border, near Timor-Leste) |
| Papua–PNG | §V.11.3 (cross-border) |

So the seed CSV is mostly §V.11 content, not §V.9. The variable/file name `ruptl_v9_transmission_links` and the column `recommended_grid_link_section` may be baked-in even if the actual section anchor is wrong.

**Resolution paths:**

(a) **Quick fix (preferred):** Read the relevant chapter-V sections in the PDF (`raw/b967d-ruptl-pln-2025-2034-pub-.pdf`). If §V.11 is the right anchor for the inter-island content, update the citation in `METHODOLOGY_CONSOLIDATED.md` §8.5a, in `RUPTL_INTEGRATION.md` Feed 3, and in the docstring of `build_fct_transmission_link_ruptl_signal.py`. Keep the file/variable names (`v9_transmission_links`) — renaming the path is churn — but add a comment noting the path is a legacy name and the actual anchor is §V.11.

(b) **Slower fix:** Rename `data/raw/ruptl_v9_transmission_links.csv` → `ruptl_v11_transmission_links.csv` and propagate. Higher cost, lower benefit.

(c) **If §V.9 actually does contain the inter-island content in this RUPTL:** keep everything as-is and the wiki source page is the one that's wrong (would update the wiki source page).

Need to read the PDF to settle which is right. Suggesting (a) as the most likely outcome.

---

### 4. (Hygiene) GEAS abbreviation drift across three docs

Three different expansions for the same column-set across three load-bearing docs:

| Doc | Expansion |
|---|---|
| `EXECUTIVE_SUMMARY.md` (Key Concepts table) | Government Energy Allocation for Solar |
| `METHODOLOGY_CONSOLIDATED.md` §11 (line 1461) | Green Energy Auction Scheme |
| `RUPTL_INTEGRATION.md` §3 Feed 1 (line 52) | Green Energy as a Service |

**Likely correct:** *Green Energy Auction Scheme* (this matches the actual PLN/Pertamina program name from public sources — the auction-based RE allocation framework, not "as a service"). Worth confirming against the PLN regulation that introduced it.

**Recommendation:** Pick one canonical expansion, unify across all three docs (and any UI tooltip text in `EconomicsTab.tsx`). Reviewer-grep-friendly: a Google search for the doc's term should land on the actual PLN program.

---

### 5. (Hygiene) F13 / GEAS empirical status drift

Three docs, three positions on whether the empirical GEAS variant is shipped:

| Doc | Status implied |
|---|---|
| `METHODOLOGY_CONSOLIDATED.md` §11.x (lines 1488–1500) | Empirical formula `geas_alloc_empirical()` exists; columns `geas_alloc_empirical_gwh`, `geas_allocation_used` are described as live |
| `RUPTL_INTEGRATION.md` §5 (line 192) | *"Today's GEAS allocation is proportional by demand share. The empirical variant exists in the column set but the empirical inputs aren't fully wired through. Tracked separately."* |
| `refinement/F13_GEAS_deprioritization_2026-05-08.md` | F13 (empirical alongside proportional) **deferred to v5.0+** — recommends striking `geas_alloc_empirical()`, distance-decay parameters, region multipliers, the `geas_alloc_empirical_gwh` and `green_share_geas_empirical_pct` columns, and the v4.1a UI toggle |

**Pick one outcome and reconcile:**

(a) **F13 stays deferred** (per 2026-05-08 decision) → strip the empirical formula from METHODOLOGY §11.x, keep only the proportional default; clarify in `RUPTL_INTEGRATION.md` that the empirical variant is *not in the column set*, just *speced and deferred*.

(b) **F13 was un-deferred since 2026-05-08** → leave methodology as-is, but `F13_GEAS_deprioritization_2026-05-08.md` should be amended with a "Reversed on YYYY-MM-DD" note, and `RUPTL_INTEGRATION.md` should say the empirical inputs *are* wired through (not "exist in column set but not fully wired").

The middle position ("exists in column set, not fully wired") is the most confusing for a reviewer because they can't tell whether to look for it.

---

## What the wiki contributes that's not in this doc

The doc cross-references code paths thoroughly (good), but doesn't link out to the wiki sources that ground the RUPTL claims. Optional addition — a "References" section pointing to:

- `sources/PLN RUPTL 2025-2034.md` (wiki) — primary source ingest with section-by-section structure
- `syntheses/Indonesia Grid Infrastructure and Renewable Adoption.md` — the structural argument for *why* RUPTL transmission buildout is the binding constraint on RE integration (§5–6× grid investment gap, IEA APS comparison)
- `syntheses/Indonesia Dashboard Methodology Review.md` §V3.8 — the wiki's prior review of the substation utilization methodology

These would let a reviewer trace from the dashboard claim → wiki understanding → primary source.

---

## Summary checklist for the dashboard side

- [ ] **Fix #1 (highest):** Read `compute_grid_integration()` in `src/dash/logic/grid.py:95` to confirm whether `available_capacity_mva` adds `ruptl_mva_added_total` on top of the existing-nameplate utilization. Update either `RUPTL_INTEGRATION.md` Example A or `METHODOLOGY_CONSOLIDATED.md` §8.4a with the actual composition rule.
- [ ] **Fix #2 (high):** Verify whether Feed 1's hardcoded RE additions came from §III (resources) or §V.6 (planned mix). Update the citation in `RUPTL_INTEGRATION.md` and `METHODOLOGY_CONSOLIDATED.md` accordingly.
- [ ] **Fix #3 (medium):** Read the PDF to confirm §V.9 vs §V.11 anchor for inter-island content. Update the section citation; keep file/variable names as legacy if churn isn't worth it.
- [ ] **Fix #4 (low):** Pick one GEAS expansion. Most likely *Green Energy Auction Scheme*. Unify across `EXECUTIVE_SUMMARY.md`, `METHODOLOGY_CONSOLIDATED.md`, `RUPTL_INTEGRATION.md`, and any UI tooltip strings.
- [ ] **Fix #5 (low):** Reconcile F13 / GEAS empirical status. Either strip from methodology (keeping the deferral) or amend the deprioritization note (if reversed).
- [ ] **Optional:** Add a "Wiki references" footer linking to the three wiki pages above.

None of these blocks the doc from being useful. #1 is the only one that actively misleads; #2–#3 are citation-correctness issues; #4–#5 are hygiene.
