# v4.3 M-AT8b — Captive Power LCOE in the UI (proposal for design review)

**Filed**: 2026-05-16
**Trigger**: Post-merge of v4.1a/sectoral-economics (PR #75, M-AT8a backend). User audit revealed the LCOE values, tiers, and fuel-price scenarios exist as scorecard columns but **don't appear anywhere in the UI**. Worse, the score drawer's "gap to incumbent" comparison still uses PLN grid tariff for every site — including pure-captive ones where the right comparator is the captive plant's own LCOE.

**Anchor**: M-AT8a methodology refinement at `docs/refinement/methodology_captive_coal_lcoe_per_site_M-AT8_review_2026-05-15.md` (T1/T2/T3 framing, fuel-price scenarios, hydro fuel type).

## Three concrete user-facing changes

### Change 1 — Score drawer: switch incumbent comparator on captive sites

**Today**: every site's score drawer compares solar LCOE against `grid_cost_usd_mwh` (PLN BPP) — `src/dash/logic/scorecard.py:181` builds `grid_rate` from `ctx.grid_cost`, surfaced in:
- `OverviewTab.tsx:54` — "Grid Tariff" tile
- `EconomicsTab.tsx:436–438` — "Solar vs grid: $X/MWh (+Y% gap)"
- `ActionTab.tsx:106` — same gap framing

**Bug**: for IMIP (`electricity_arrangement: pure_captive`, `captive_incumbent_lcoe_usd_mwh: 50`), the drawer reports "+15% gap vs grid" when the real gap to the actual incumbent ($50 captive coal) is closer to **+30%**. DFI committees reading the drawer see the wrong comparator and conclude solar is closer to parity than it really is.

**Proposal**:
- When `electricity_arrangement == 'pure_captive'`, compare solar LCOE against `captive_incumbent_lcoe_usd_mwh` instead of `grid_cost_usd_mwh`
- When `electricity_arrangement == 'hybrid_captive_primary'` or `grid_primary_with_captive`, show BOTH comparators — captive primary uses captive incumbent, hybrid shows both with a 50/50 blend or user-toggleable share
- Tile label changes: "Grid Tariff" → context-aware ("Captive Coal Incumbent", "Captive Gas Incumbent", "Captive Hydro Incumbent", "Grid Tariff")
- Tier badge (T1/T2/T3) next to the value with hover-tooltip linking to METHODOLOGY §13.10

**Scope question for review**: should the "+gap%" calculation be additive (e.g. for hybrid sites, weighted gap = `0.7 × gap_to_captive + 0.3 × gap_to_grid`) or do we just show two separate values?

### Change 2 — New "Captive Power" tile/section in score drawer

For sites with `captive_fuel_type != 'none'`, add a dedicated section in the OverviewTab showing:

| Field | Display |
|---|---|
| Captive fuel type | "Coal (subcritical)" / "Coal (supercritical)" / "Natural Gas (HGBT)" / "Hydro" |
| Captive LCOE | "$50/MWh" with **🟢 T1 / 🟡 T2 / 🔴 T3** badge |
| Source | Hover tooltip: "Berkeley GSPP 2024 + IESR + CREA triangulation" (from CSV's source_citation column) |
| Fuel price scenario | "DMO baseline" / "HGBT regulated" / "Market gas" — links to v4.3 M-AT8c slider when shipped |

Hidden for `pure_grid` / `none` sites. Renders as a colored card matching the existing "Grid Cost" tile style.

### Change 3 — Table: surface captive arrangement + LCOE column

**Today**: DataTable shows `captive_power_type` + `captive_coal_count` + `captive_coal_mw` (legacy v4.0.5 coal-tracker columns). No display of the M-AT8a `captive_incumbent_lcoe_usd_mwh` or tier.

**Proposal**:
- Add a sortable column **"Captive LCOE"** showing `$50` for IMIP, `$62` for Krakatau Posco, etc. NULL for non-captive sites (renders as em-dash).
- Add a small tier badge inline with the value: `$50 🟢T1` / `$55 🟡T2` / `$63 🔴T3`
- Add a filter chip in the existing filter strip: "Captive Power" → multi-select dropdown {Coal, Gas, Hydro, None}
- Default visibility: hidden (in the show/hide column menu). Reveal via "Add column" picker. Reason: most analyst flows are PLN-grid centric; captive is a specialized lens.

**Alternative**: combine captive_fuel_type and captive_incumbent_lcoe into one merged column "Incumbent" that shows "$50 (Coal T1)" for captive sites and "$70 (Grid)" for grid-connected sites. Lower visual cost; might be the right move.

## Scope inclusions

- Backend changes in `scorecard.py` to plumb captive incumbent into the LCOE-gap calc
- Frontend changes in `OverviewTab.tsx`, `EconomicsTab.tsx`, `ActionTab.tsx`, `DataTable.tsx`, `columns.tsx`
- Methodology drawer entry (link from tier badge → METHODOLOGY §13.9–§13.11)
- Tests: golden test will drift (intentional — the gap-to-incumbent values change). Update golden + add explicit regression test that asserts IMIP gap = `(solar_lcoe - 50) / 50 * 100`, not `(solar_lcoe - 70) / 70 * 100`.

## Test plan

- New unit test: `tests/test_scorecard_competitive_gap_uses_captive_for_captive_sites.py` — asserts IMIP's gap is calculated against $50 captive coal, not $70 grid tariff.
- Frontend test: `OverviewTab.test.tsx` adds three cases for the new row rendering (pure_captive / hybrid / grid_only).
- Frontend test: `DataTable.test.tsx` adds a case for filter chip behavior (`captive_types: ['coal']` filters to coal-fueled rows).
- Visual regression: existing scorecard golden test (`test_scorecard_golden.py`) will drift — IMIP's `competitive_gap_pct` changes from old (vs grid) to new (vs captive). Update golden + add explicit regression test for the IMIP case so future drift is obvious.

## NOT in scope (M-AT8c, separate PR)

- Fuel-price scenario slider in the UI (live recompute on slider drag)
- URL state for the active scenario
- Trajectory overlay (year slider + IDX Carbon ramp)
- Methodology drawer composite badge (full M-AT8b drawer is bigger than just surfacing the tier)

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | not run (mid-PR UX fix) |
| Eng Review | `/plan-eng-review` | Architecture & tests | 0 | — | needed before merge — flag M-AT8b changes |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR | score: 6/10 → 9/10, 4 decisions made |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | optional |

- **UNRESOLVED:** 0
- **VERDICT:** DESIGN CLEAR — ready to implement. Eng review (or `/review` on the diff) recommended before merge.

## Design decisions (from /plan-design-review 2026-05-16)

| # | Decision | Rationale |
|---|---|---|
| **1A** | **Hybrid sites: two stacked rows (Captive primary + Grid secondary).** Pure-captive → only captive row. Pure-grid → only grid row. Hybrid → both, captive on top. Competitive Gap uses captive as dominant baseline. | Clear hierarchy. Reuses existing `StatRowWithTip` pattern. ~30px extra height affects only ~10 hybrid sites. |
| **1B** | **T3 sites: show gap % with tier badge inline.** `Competitive Gap: +12% [T3]` with hover tooltip "T3 = formula placeholder, low confidence — site-specific data would tighten this." | Honest about uncertainty without hiding the signal. Engaged readers get methodology context; quick scanners still get the number. |
| **1C** | **Tier badge = text pill (T1/T2/T3 with bordered color).** Green-bordered T1, amber T2, red-tinted T3. Matches existing badge family. | Accessibility (text + color, not color-alone). Scales to 10px legibly. Consistent with DataTable's action-flag chips. |
| **1D** | **Captive LCOE column default-VISIBLE + filter chip.** Filter chip = multi-select {Coal / Gas / Hydro / None}. | Matches M-AT1/M-AT6/M-AT7 default-visible transparency pattern. User-asked feature; surfacing it is the value. |

## Concrete UI spec

### Score drawer — OverviewTab "At a Glance" section

Replaces lines 52–57 of `frontend/src/components/panels/scoredrawer/OverviewTab.tsx`. Logic:

```
if electricity_arrangement == 'grid_only':
    <StatRowWithTip label="Grid Cost" value={grid_cost_usd_mwh} unit="$/MWh"
                    tip="PLN's cost to supply power here. If LCOE is lower, RE is already cheaper." />

elif electricity_arrangement == 'pure_captive':
    <StatRowWithTip label={fuelLabel}  // "Captive Coal", "Captive Gas", "Captive Hydro"
                    value={captive_incumbent_lcoe_usd_mwh}
                    unit="$/MWh"
                    badge={<TierPill tier={captive_lcoe_tier}/>}
                    tip={`Captive ${fuelType} LCOE at this site. ${tierExplanation(tier)}`} />

else:  // hybrid_captive_primary OR grid_primary_with_captive
    <StatRowWithTip label={fuelLabel}  // primary
                    value={captive_incumbent_lcoe_usd_mwh}
                    badge={<TierPill tier={captive_lcoe_tier}/>}
                    tip="..." />
    <StatRowWithTip label="Grid Cost"  // secondary
                    value={grid_cost_usd_mwh}
                    tip="PLN supply cost (site also buys from grid partially)." />
```

The `Competitive Gap` row math switches: when `electricity_arrangement != 'grid_only'`, gap is `(lcoe_re - captive_incumbent_lcoe) / captive_incumbent_lcoe`. When grid_only, gap is unchanged.

For T3 sites: gap row gains a small `[T3]` pill suffix with tooltip "Low-confidence incumbent value. Site-specific captive economics would tighten this — see methodology §13.10."

### DataTable — new column

Column header (per `UI_CONVENTIONS.md` tooltip pattern):

```tsx
<SortHeader
  label="Captive LCOE"
  sortKey="captive_incumbent_lcoe_usd_mwh"
  active={sort.key}
  dir={sort.dir}
  onSort={onSort}
  tooltip="On-site captive power cost ($/MWh). T1/T2 = site-specific anchor; T3 = formula placeholder. Empty for grid-only sites. See methodology §13.10."
/>
```

Cell render:

```tsx
{row.captive_incumbent_lcoe_usd_mwh == null ? (
  <span title="Site has no captive power arrangement (grid-only).">—</span>
) : (
  <span>
    ${row.captive_incumbent_lcoe_usd_mwh.toFixed(0)}
    <TierPill tier={row.captive_lcoe_tier} compact />
  </span>
)}
```

Filter chip added to the existing filter strip:

```tsx
<MultiSelectChip
  label="Captive Power"
  options={['Coal', 'Gas', 'Hydro', 'None']}
  value={filters.captiveTypes}
  onChange={...}
/>
```

Filter values map to `captive_fuel_type`: `'Coal'` → `{coal_subcritical, coal_supercritical}`, `'Gas'` → `natural_gas`, `'Hydro'` → `hydro`, `'None'` → `none`.

### TierPill component (new, shared)

```tsx
// frontend/src/components/ui/TierPill.tsx
export function TierPill({ tier, compact = false }: { tier: 'T1' | 'T2' | 'T3' | null; compact?: boolean }) {
  if (!tier) return null;
  const styles = {
    T1: { color: '#2E7D32', border: '#2E7D32', bg: 'rgba(46,125,50,0.1)' },
    T2: { color: '#F57C00', border: '#F57C00', bg: 'rgba(245,124,0,0.1)' },
    T3: { color: '#C62828', border: '#C62828', bg: 'rgba(198,40,40,0.1)' },
  }[tier];
  const tooltip = {
    T1: 'Tier 1 — High confidence anchor (multi-source verified)',
    T2: 'Tier 2 — Industry archetype extrapolation',
    T3: 'Tier 3 — Formula placeholder (low confidence)',
  }[tier];
  return (
    <span
      title={tooltip}
      aria-label={tooltip}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 2,
        padding: compact ? '1px 5px' : '2px 7px',
        marginLeft: 6,
        fontSize: compact ? 9 : 10,
        fontWeight: 600,
        borderRadius: 4,
        border: `1px solid ${styles.border}`,
        color: styles.color,
        background: styles.bg,
        lineHeight: 1.2,
      }}
    >
      {tier}
    </span>
  );
}
```

### Responsive

- Score drawer: already drawer-style on mobile (slides over content). Captive Coal/Gas row + Grid Cost row stack naturally.
- DataTable: Captive LCOE column hides on `<768px` via the existing responsive-column hide pattern (`captive_power_type` is already in the hide list at `DataTable.tsx:298`, follow same pattern for the new column).
- Filter chip: multi-select dropdown collapses to icon-only on `<480px`.

### Accessibility

- TierPill: `aria-label` explains the tier (not just color). Color contrast 4.5:1+ on each variant.
- Filter chip: keyboard-navigable (Tab to focus, arrow keys to navigate options, Space/Enter to toggle).
- New score-drawer rows inherit the `StatRowWithTip` keyboard support (already implemented in the existing component).
