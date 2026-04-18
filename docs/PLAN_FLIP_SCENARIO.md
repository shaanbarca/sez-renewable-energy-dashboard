# Feature: Flip Scenario — A/B Policy Lever Compare (Tab in BottomPanel)

## Context

Flip Scenario was the original "core unique insight" of the dashboard (PLAN.md:37): **which sites are one policy lever from solar-competitive**. It shipped as a bottom-panel tab in the first Dash prototype, then got cut on 2026-04-15 during the React/Vite rebuild (DESIGN.md:140 changelog). The pipeline still produces `solar_now_at_wacc8` (src/pipeline/build_fct_site_scorecard.py:307) — a precomputed "flip at DFI concessional rate" column — but no UI surfaces it.

This feature brings the idea back, but better. Not a static "at 8% WACC" column, and not a vague "within X% of parity" slider. Instead: **A/B compare two full assumption snapshots** (baseline vs flip scenario) and show the delta — per site, in aggregate. The policy question "what does concessional finance unlock?" becomes a two-slider demo: move WACC from 10 → 8%, watch N sites cross into full_re tier, export the list.

Every persona has the same unanswered question (PERSONAS.md):
- **Energy Economist** — carbon breakeven + WACC sensitivity → which financing moves the needle
- **DFI Investor** — "quantify the concessional finance impact at site level"
- **Policy Maker** — the Perpres 112 / CBAM trade argument needs a counterfactual
- **IPP Developer** — which sites become bankable under improved terms
- **Industrial Investor** — subsidy exposure + future tariff risk

One A/B view answers all of them.

---

## UI shape — one tab, everything in it

The whole Compare interface lives inside a new **`Scenario Compare`** tab in `BottomPanel` (beside `Ranked Table`, `RUPTL Context`, `Sector Summary`). No header pill. No floating right drawer. No centered banner. One tab, one surface.

Reasoning:
- BottomPanel is where analysis artifacts already live (ranked table, sector chart, RUPTL chart). Flip Scenario is an analysis artifact — it belongs there.
- A floating drawer + banner + table-diff-columns spread the interaction across 3 z-layers and forced the user to track state across the map, the drawer, and the header pill simultaneously. One tab = one mental model.
- Users open the tab explicitly → `compareMode` becomes "is this tab active?" → no new state flag needed to gate other UI surfaces.

### Tab layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Ranked Table │ RUPTL Context │ Sector Summary │ [Scenario Compare]          │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ CONTROLS (360px) ──────────┐ ┌─ SUMMARY + DIFF TABLE (flex-1) ─────────┐ │
│ │ Preset                      │ │ 7 → Full RE · 3 improved · 0 worsened  │ │
│ │  ● Concessional finance     │ │ Median gap: +18% → +3% (−15pp)         │ │
│ │  ○ Cheap CAPEX              │ │ 2 new CBAM-urgent                       │ │
│ │  ○ CBAM max exposure        │ │                                         │ │
│ │  ○ Grant transmission       │ │ ┌─ diff table ─────────────────────┐   │ │
│ │  Custom — fields edited     │ │ │ Site │ Tier base → flip │ ΔLCOE │   │ │
│ │                             │ │ ├──────────────────────────────────┤   │ │
│ │ Flip overrides              │ │ │ Batang     │ near → full  │ −12  │   │ │
│ │  WACC            10 → [ 8 ] │ │ │ Kendal     │ near → full  │ −11  │   │ │
│ │  CAPEX          700 → [600] │ │ │ Galang     │ partial→full │ −8   │   │ │
│ │  Lifetime        25 → [ 25] │ │ │ ...                               │   │ │
│ │  FOM             12 → [ 12] │ │ └──────────────────────────────────┘   │ │
│ │  BESS CAPEX     250 → [250] │ │                                         │ │
│ │  CBAM cert €/t   50 → [ 80] │ │ [Export diff CSV]                       │ │
│ │  ☐ Grant transmission       │ │                                         │ │
│ │                             │ │                                         │ │
│ │ [Compute flip] [Reset]      │ │                                         │ │
│ └─────────────────────────────┘ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

Three regions inside the tab:
1. **Left column (360px, scrolls):** preset picker + lever editors + Compute / Reset
2. **Top-right summary row:** 5 headline stats (flipped to full_re, improved, worsened, median gap shift, new CBAM-urgent)
3. **Main area:** sortable diff table (`Site | Sector | Tier base → flip | ΔLCOE | Gap base | Gap flip | CBAM?`) + `Export diff CSV` button

Empty state (tab open but user hasn't clicked Compute yet): left column shows controls; right side shows a muted hint block — *"Adjust flip values or pick a preset, then Compute. Baseline: 81 sites at current assumptions."*

### User flow

1. User opens the **Scenario Compare** tab.
2. Left column loads with flip values pre-filled from the current baseline. No diff exists yet.
3. User picks a preset (e.g. *Concessional Finance*). Lever fields auto-fill with the preset's overrides and highlight (accent color on changed fields).
4. User clicks **Compute flip**. Frontend fires a second `POST /api/scorecard` with flip assumptions. Spinner on the button; disable during fetch.
5. Summary row + diff table populate.
6. User changes a baseline assumption in `AssumptionsPanel` → flip result marked stale (`Recompute` button label swaps in, small "stale" chip appears next to summary).
7. User clicks **Export diff CSV** → file downloads with site-by-site diff rows.
8. User picks a different preset or edits fields → preset changes to *Custom*.

### What this replaces (from the first draft of the plan)

- `components/panels/CompareDrawer.tsx` — **deleted.** Rolled into the tab.
- `components/ui/FlipSummaryBar.tsx` — **deleted.** Summary row is inside the tab.
- Header "Compare scenarios" pill — **not added.** Tab opens the compare surface.
- DataTable extra `Tier (Flip)` + `ΔLCOE` columns — **not added.** The diff table in the tab is a better home (dedicated layout, always shows deltas without cluttering the main ranked table).

### What stays optional (Phase 5)

- **Map glow rings** on flipped sites when `compareMode === true` (compareMode = "Scenario Compare tab is active AND flipScorecard exists"). Lower priority — tab alone delivers the value.
- **ScoreDrawer `FlipTab`** — side-by-side baseline vs flip for one site. Nice for deep-dive but not required for v1.

Both are cheap to add once the tab ships; including them in Phase 5 keeps the scope honest.

---

## Architecture

### State

Extend the Zustand store (`frontend/src/store/dashboard.ts`). Already partially wired (uncommitted):

```ts
interface DashboardStore {
  // ... existing
  flipAssumptions: UserAssumptions | null;
  flipThresholds: UserThresholds | null;
  flipScorecard: ScorecardRow[] | null;    // cached result of second POST
  flipPreset: FlipPreset | 'custom' | null;
  flipLoading: boolean;
  flipStale: boolean;                      // true when baseline changed post-Compute

  setFlipAssumptions: (a: Partial<UserAssumptions>) => void;
  applyFlipPreset: (p: FlipPreset) => void;
  computeFlip: () => Promise<void>;        // fires the second POST
  clearFlip: () => void;
  flipDiff: () => { rows: FlipDiffRow[]; summary: FlipSummary } | null;  // memoized selector
}

type FlipPreset =
  | 'concessional_finance'     // wacc_pct: 8
  | 'cheap_capex'              // capex_usd_per_kw: 600
  | 'cbam_max_exposure'        // cbam_certificate_price_eur: 80
  | 'grant_transmission';      // grant_funded_transmission: true
```

**No separate `compareMode` flag.** The tab being active (`activeTab === 'compare'`) IS compare mode. Keeps state minimal.

Baseline scorecard stays in the existing `scorecard` field. The diff is a derived selector — no duplicated state. When `setAssumptions` / `setThresholds` fire while `flipScorecard !== null`, set `flipStale = true`.

### Types

Add `'compare'` to `BottomTab` in `frontend/src/lib/types.ts`:

```ts
export type BottomTab = 'table' | 'ruptl' | 'sector' | 'compare';
```

### API

**No new endpoint.** Reuse `POST /api/scorecard`. Frontend fires it twice — once on mount/slider-change for baseline, once on "Compute flip" for the flip scenario. `compute_scorecard_live` takes ~50ms for 81 sites; two calls = 100ms. Acceptable.

### Diff computation (client-side, pure function)

Already implemented in `frontend/src/lib/flipDiff.ts` (uncommitted):

```ts
export interface FlipDiffRow {
  site_id: string;
  site_name: string;
  sector: string;
  tier_baseline: EconomicTier;
  tier_flip: EconomicTier;
  lcoe_baseline: number | null;
  lcoe_flip: number | null;
  delta_lcoe: number | null;
  gap_baseline_pct: number | null;
  gap_flip_pct: number | null;
  flip_direction: 'improved' | 'worsened' | 'unchanged';
  cbam_urgent_baseline: boolean;
  cbam_urgent_flip: boolean;
  cbam_urgent_changed: boolean;
}

export interface FlipSummary {
  total_sites: number;
  flipped_to_better_tier: number;
  flipped_to_worse_tier: number;
  flipped_to_full_re: number;
  median_gap_baseline_pct: number | null;
  median_gap_flip_pct: number | null;
  gap_closed_pct: number | null;
  new_cbam_urgent_count: number;
}

export function computeFlipDiff(baseline: ScorecardRow[], flip: ScorecardRow[]):
  { rows: FlipDiffRow[]; summary: FlipSummary };

export function flipDiffToCsv(rows: FlipDiffRow[]): string;
```

Tier ordering (better → worse): `full_re > partial_re > near_parity > not_competitive > no_resource`. Already in `frontend/src/lib/constants.ts` as `ECONOMIC_TIER_HIERARCHY`. `no_resource` rows excluded from median-gap math.

### File plan

New folder `frontend/src/components/panels/scenariocompare/` mirroring the scoredrawer/ pattern:

| File | Role |
|---|---|
| `ScenarioCompareTab.tsx` | Shell — flex layout, wires store state into sub-components |
| `FlipControls.tsx` | Preset picker + lever editors + Compute / Reset buttons (left column) |
| `FlipSummary.tsx` | 5 headline stats + stale chip (top-right) |
| `FlipDiffTable.tsx` | Sortable diff table + Export CSV button (main area) |

Files to delete (currently uncommitted):
- `frontend/src/components/panels/CompareDrawer.tsx`
- `frontend/src/components/ui/FlipSummaryBar.tsx`

Files to modify:
- `frontend/src/components/ui/BottomPanel.tsx` — add the 4th tab
- `frontend/src/lib/types.ts` — extend `BottomTab` union
- `frontend/src/App.tsx` — remove `<CompareDrawer />` and `<FlipSummaryBar />` imports + render
- `frontend/src/store/dashboard.ts` — ensure state matches §State (already mostly wired; drop `compareMode` if present)

Files retained unchanged:
- `frontend/src/lib/flipDiff.ts` (keep)
- `frontend/src/lib/flipPresets.ts` (keep)

### Out of compare mode

When user is on any other tab: `flipAssumptions` / `flipScorecard` stay in memory but nothing renders. No tax on non-compare users. Clicking back into the Scenario Compare tab shows the previous compute result immediately.

---

## Implementation Plan

Strict bottom-up. Each step passes type-check and lint before moving on.

### Phase 0: Cleanup (~30 min)
0. Delete `CompareDrawer.tsx` + `FlipSummaryBar.tsx`.
1. Remove their imports + renders from `App.tsx`.
2. Drop `compareMode` flag from the store if present; verify `setAssumptions`/`setThresholds` flip `flipStale = true` when `flipScorecard !== null`.

### Phase 1: Types + tab registration (~30 min)
3. Add `'compare'` to `BottomTab` in `types.ts`.
4. Add the tab entry in `BottomPanel.tsx` TAB_ITEMS + `<Tabs.Content value="compare">`.
5. Stub `<ScenarioCompareTab />` returning a "Coming soon" placeholder — verify tab opens.

### Phase 2: Controls column (~2 hours)
6. Build `FlipControls.tsx` — preset radio group, 6 number fields (WACC / CAPEX / Lifetime / FOM / BESS CAPEX / CBAM cert), grant-transmission checkbox. Port the lever UI from the deleted `CompareDrawer.tsx` — same fields, same store actions.
7. Wire Compute + Reset buttons to `computeFlip()` / `clearFlip()`.
8. Changed-field highlight: color input accent when `flipValue !== baselineValue`.

### Phase 3: Summary + diff table (~2 hours)
9. Build `FlipSummary.tsx` — 5 Stat pills reading from `flipDiff().summary`. Stale chip when `flipStale`.
10. Build `FlipDiffTable.tsx` — TanStack Table with 7 cols: Site, Sector, Tier base, Tier flip, ΔLCOE, Gap base → flip, CBAM changed. Sort by ΔLCOE default desc (biggest improvements first). Row click → select site on map (reuses `setSelectedSite`).
11. Export CSV button → `flipDiffToCsv(rows)` → trigger download.

### Phase 4: Assemble + polish (~1 hour)
12. Compose `ScenarioCompareTab.tsx` — flex layout, empty state when `flipScorecard === null`, stale banner when `flipStale`.
13. Manual smoke: Concessional Finance preset → Compute → verify ~5-12 flips → Export CSV → spot-check 3 rows.

### Phase 5: Optional polish (~2 hours, can defer)
14. Map glow rings on flipped sites when `activeTab === 'compare' && flipScorecard !== null`. Green for `improved`, amber for `worsened`, none for `unchanged`.
15. `ScoreDrawer` FlipTab — side-by-side baseline vs flip for the selected site.
16. Walkthrough step: new entry in Economist + DFI personas pointing to the tab.
17. `CHANGELOG.md` + `DESIGN.md` §9 entries.

**Total estimate: ~6 hours for Phases 0-4 (the MVP tab). Phase 5 adds ~2 hours.**

---

## Data Dictionary Impact

No new pipeline columns. No new API endpoints. All new state is client-side-only and derived from existing `ScorecardRow` fields.

`solar_now_at_wacc8` in `fct_site_scorecard` becomes vestigial. Leave it in — separate cleanup commit once we confirm no consumers.

---

## Failure Modes

| Risk | Detection | Mitigation |
|---|---|---|
| User changes baseline assumption mid-compare, flip scorecard goes stale silently | Visual test: compute flip, then drag baseline WACC | Set `flipStale = true` in `setAssumptions`/`setThresholds`; show "stale" chip in summary; button label swaps to "Recompute (stale)" |
| Second `POST /api/scorecard` is slow or fails | Network throttle test | Disable Compute during fetch; show spinner; on error, toast + leave previous result in place |
| Diff row counts confuse user when `no_resource` tier is in the set | Manual: Concessional preset should show ~7 flips, not ~11 | Exclude `no_resource` from median-gap math and from `flipped_to_full_re`; keep them in the diff table but greyed |
| Preset + custom edits interact weirdly | QA: apply Concessional, edit WACC, verify preset switches to Custom | `setFlipAssumptions` always sets `flipPreset = 'custom'` unless called from `applyFlipPreset` |
| Tab layout breaks on narrow windows (<1200px) | Resize window during review | Collapse to single column below 1100px: controls on top, diff table below; document as known limitation for v1 |
| Export CSV mismatches screen due to sort state | Manual: sort by Tier, export, compare first row | CSV exports the sorted view, not the original order. Document. |

---

## Verification

1. **Type-check:** `cd frontend && npx tsc --noEmit` — clean.
2. **Lint:** `cd frontend && npm run lint` — no new warnings.
3. **Manual smoke:**
   - Open Scenario Compare tab → empty state visible
   - Pick *Concessional Finance (8% WACC)* preset → WACC field highlights, fields fill in
   - Click Compute → spinner → summary + diff table appear
   - Expect ~5-12 sites flipping to `full_re`
   - Click a row in diff table → site selected on map
   - Change baseline WACC in AssumptionsPanel → stale chip appears, button swaps to "Recompute (stale)"
   - Recompute → stale clears
   - Click Reset → diff clears, controls return to baseline defaults
   - Export CSV → file downloads with all diff columns, rows match on-screen sort
   - Switch tabs → Compare state preserved, returning to tab shows previous result

---

## Out of Scope

- **Multi-way compare** (baseline vs 2+ flip scenarios). Two is enough for the policy story.
- **Server-side diff caching.** `compute_scorecard_live` is fast enough; caching adds complexity.
- **URL-shareable flip scenarios.** The existing `urlState.ts` serializes one assumption set; extending to two is deferred.
- **Sector-level flip rollup** inside the tab (e.g. "3 cement sites improved"). Tempting but doubles the table complexity; v1 stays at site-level only.
- **Deleting `solar_now_at_wacc8` from the pipeline.** Separate commit once we confirm no consumers.
- **Animating the tier transitions.** Static rings (Phase 5) are enough.

---

## Critical Files Referenced

- `frontend/src/store/dashboard.ts` — state extension (mostly wired already)
- `frontend/src/lib/types.ts` — extend `BottomTab` union
- `frontend/src/lib/constants.ts` — `ECONOMIC_TIER_HIERARCHY` (reused)
- `frontend/src/lib/api.ts` — `fetchScorecard` (reused, fired twice)
- `frontend/src/lib/flipDiff.ts` — pure diff (already written, uncommitted)
- `frontend/src/lib/flipPresets.ts` — 4 presets (already written, uncommitted)
- `frontend/src/components/ui/BottomPanel.tsx` — add 4th tab
- `frontend/src/components/panels/scenariocompare/*` — new folder with 4 files
- `frontend/src/components/panels/CompareDrawer.tsx` — **DELETE**
- `frontend/src/components/ui/FlipSummaryBar.tsx` — **DELETE**
- `frontend/src/App.tsx` — drop the two removed imports/renders
- `DESIGN.md:140` — changelog entry: "Flip Scenario restored as BottomPanel tab"
- `PLAN.md:37, 68, 200, 235` — original flip-scenario intent; update reference to new tab-based shape
- `PERSONAS.md:33, 96, 131, 289` — references to "flip under concessional finance"; becomes the canonical workflow
