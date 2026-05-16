# v4.1: per-tier IEA filter chips + tabbed LCOE waterfall modal

**Branch:** `v4.1/tier3-polygons-3-sites` (continuation after IEA stack UI shipped in `bb3412f`)
**Review:** `/plan-design-review` 2026-05-16
**Issues:** filed during proposal review

## Why this is happening

PR #74 shipped the 4-tier IEA cost stack data (Generation → Delivered → Firm 4h → Firm 8h) and `bb3412f` surfaced it as a single-column ladder in the ranked table + a Recharts waterfall in the score drawer Overview tab. But two design gaps remain — both blocking the DFI shortlisting workflow:

1. **Ranked table can only sort/filter on one tier at a time.** P2 DFI Investors and P4 IPP Developers run shortlists like *"show me sites where Firm 8h beats the PLN BPP"* — that's the bankability screen for a 24/7 PPA. The current UI buries each tier as a sub-label of one column with sort defaulting to Delivered. No per-tier filtering.
2. **LCOE breakdown modal only decomposes the base solar LCOE.** P1 Energy Economists open the modal to answer "why is Firm 8h $228/MWh?" The current waterfall shows CAPEX/FOM/Land/Grid for the Generation tier only. The LCOS storage adders that drive 4h and 8h are nowhere to be seen.

## D1 — Ranked table: per-tier "below BPP" filter chips

**LOCKED: Filter chips above the table** (alongside existing CBAM / KEK / Captive chips).

Four new toggle chips slot into the existing filter toolbar in `DataTable.tsx`:

```
existing:                                           new:
[KEKs only] [CBAM] [Captive Coal Gas Hydro None]   [Gen<BPP] [Del<BPP] [4h<BPP] [8h<BPP]
```

Each chip is independently toggleable and **composes via AND**. Active chip colored to match its IEA tier (the colors already shipped in `IEACostStackWaterfall.tsx`):

| Chip | Active fill | Active border | Active text |
|------|-------------|---------------|-------------|
| Gen<BPP | `rgba(76,175,80,0.1)` | `rgba(76,175,80,0.4)` | `#4CAF50` |
| Del<BPP | `rgba(66,165,245,0.1)` | `rgba(66,165,245,0.4)` | `#42A5F5` |
| 4h<BPP | `rgba(171,71,188,0.1)` | `rgba(171,71,188,0.4)` | `#AB47BC` |
| 8h<BPP | `rgba(126,87,194,0.1)` | `rgba(126,87,194,0.4)` | `#7E57C2` |

Inactive: standard `var(--text-secondary)` + `var(--text-muted)` border, matching existing chip pattern.

**Threshold follows `benchmarkMode`.** When the user has the global BPP/Tariff toggle on Tariff (Header), the chips read "Gen<Tariff", "Del<Tariff", etc. — the comparator switches in sync. Tooltip on hover explains: "Sites where the {tier} tier is cheaper than the {BPP/Tariff} grid cost in this region."

**State location:** local `useState` in `DataTable.tsx` (matches `cbamOnly`, `kekOnly`, `captiveFilter` precedent). NOT in Zustand. URL persistence deferred to v4.2 across all filter chips uniformly (raised as follow-up issue).

**Sort** stays as the existing column ▾ menu with the tier picker we already shipped in `bb3412f`. Filter (chips) and sort (column header) live in their native affordances — clarity over consistency.

**Empty state when chips zero out the table:**

```
┌─────────────────────────────────────────────────────────┐
│  No sites match these filters.                          │
│                                                         │
│  Active filters:  [Del<BPP]  [8h<BPP]                  │
│                                                         │
│  [Clear all filters]                                    │
└─────────────────────────────────────────────────────────┘
```

This replaces the table body, keeping the chip toolbar visible above so the user can deactivate individual chips without going through "clear all".

## D2 — LCOE waterfall modal: tabs with tier totals in labels

**LOCKED: Tabbed modal with tier totals embedded in tab labels.**

```
┌─ LCOE breakdown ─ IMIP ─────────────────────────────────┬─ × ─┐
│                                                         │     │
├─────────────────────────────────────────────────────────┴─────┤
│  [Gen $93]  [Delivered $144 •]  [Firm 4h $179]  [Firm 8h $228]│
├───────────────────────────────────────────────────────────────┤
│  $/MWh                                                        │
│                                                               │
│    ▓ CAPEX                       72                           │
│    ▓▓ +FOM                      +18 → 90                      │
│    ▓▓▓ +Land                     +3 → 93                      │
│    ▓▓▓▓ +Grid Connection        +51 → 144                     │
│    ▓▓▓▓▓ Total (Delivered)            144                     │
│                                                               │
│  Inputs: WACC 8% · lifetime 25yr · CF 18.3% · ...             │
└───────────────────────────────────────────────────────────────┘
```

### Tier → components mapping (single source of truth)

| Tab | Components included | Reference |
|-----|---------------------|-----------|
| **Generation** | CAPEX + FOM + Land | Existing `LcoeWaterfallModal.tsx:212-234` minus grid costs |
| **Delivered** | Generation components + Grid Connection (+ Transmission + Substation Upgrade where applicable) | Existing `LcoeWaterfallModal.tsx:235-266` (current default behaviour) |
| **Firm 4h** | Delivered components + LCOS 4h adder (`lcos_4h_usd_mwh`) | New |
| **Firm 8h** | Delivered components + LCOS 8h adder (`lcos_8h_usd_mwh`) | New |

The LCOS adders ship as a single colored bar per firm tier — not decomposed further. Decomposition (BESS CAPEX vs cycling vs round-trip efficiency) is deferred to a follow-up; the user can see the magnitude of the storage cost as a single bar against the underlying generation+grid stack.

### Tier labels carry totals

`[Gen $93] [Delivered $144 •] [Firm 4h $179] [Firm 8h $228]`

This makes the tab strip itself a comparison view. Users see all four tier totals at a glance and choose which one to decompose — no clicking required for the comparison story. Tab labels are read from `row.lcoe_generation_usd_mwh`, `row.full_system_lcoe_delivered_usd_mwh`, etc. (the columns already on every row).

### Modal launch points

1. **From OverviewTab IEACostStackWaterfall** (NEW): clicking any bar of the inline waterfall opens the modal **with that tier's tab pre-selected**. The waterfall bars get a `cursor: pointer` + hover state + tooltip ("Click for detailed breakdown").
2. **From EconomicsTab LCOE stat row** (EXISTING): the dashed-underline click target keeps working. Opens modal on the **Delivered tab** (matches current legacy behaviour where it showed grid-included LCOE).

Both paths hit the same modal component with `initialTier` prop.

### Modal size

Stays at `max-w-2xl` × `max-h-90vh` — same as existing. Tab strip eats ~36px, waterfall area shrinks by 36px. On a 13" MacBook (768px viewport) the modal is still scrollable but the waterfall + inputs panel both fit in the visible area. No layout breaks.

## Interaction states

| Surface | Loading | Empty | Error | Success | Partial |
|---------|---------|-------|-------|---------|---------|
| Filter chip | n/a (instant) | n/a | n/a | Active style swap | n/a |
| Filtered table | Existing skeleton | New "no sites match" panel | Existing error toast | Rows rerender | n/a |
| Modal tab strip | n/a (instant) | If row has no value for a tier → tab disabled + tooltip "Not enough data for this tier" | If `canCompute` false → existing "Not enough data" message in panel | Bar repaint | If only some firm-tier values are null → those tabs disabled, others active |

## Responsive

- **1440px+** (default): 4 new chips fit in the existing filter toolbar row without wrapping. Total chip count: `KEKs + CBAM + Captive(4) + IEA(4) = 10` chips + search + global toggles. Tested in DESIGN.md screenshots — toolbar wraps gracefully at ~1280px.
- **1024px (tablet)**: Toolbar wraps to 2 rows. The 4 IEA chips group on the second row, keeping visual unity.
- **768px (mobile)**: Bottom drawer is hidden by default; if expanded, the chip toolbar becomes horizontally scrollable. Modal becomes nearly full-screen — tab strip stays at top, scrolls horizontally if needed. (No design changes from existing mobile behaviour.)

## Accessibility

- Each chip: `<button>` element with `aria-pressed={active}`. Keyboard: Tab to focus, Space/Enter to toggle.
- Modal tabs: `role="tablist"` + `role="tab"` on each label, `role="tabpanel"` on the waterfall area. Arrow keys (←/→) cycle tabs.
- Tier color contrast: all four tier colors (`#4CAF50`, `#42A5F5`, `#AB47BC`, `#7E57C2`) have contrast ratio ≥4.5:1 against the existing dark drawer background. Verified.
- Hover-only affordances avoided: chip active state visible at rest (border + fill, not just text color shift).

## What's NOT in scope

- **URL persistence of filter state.** Existing chips don't persist; adding it for just IEA chips creates inconsistency. v4.2 should lift all filter chips into Zustand + URL as a uniform pass.
- **LCOS decomposition** (BESS CAPEX vs cycling vs RTE) inside the firm tier tabs. Single bar for now; deeper drill-down in v4.2 or v5.0.
- **Filter for "between BPP and Tariff"** or **"above BPP by N%"**. Binary `<BPP` is the deal-screen MVP; range-filters are a follow-up.
- **Cross-tier diff bars** on the modal (showing Δ between tiers visually). Tab labels embed the totals; if the user wants Δ they can mental-math from `$144 → $179 = +$35`. Adding diff lines clutters the waterfall.

## What already exists (reused, not reinvented)

- Filter chip pattern: `frontend/src/components/table/DataTable.tsx:410-471` (KEK / CBAM / Captive)
- Modal frame: `frontend/src/components/panels/scoredrawer/LcoeWaterfallModal.tsx:277-317` (backdrop + close + size)
- Waterfall computation: `LcoeWaterfallModal.tsx:196-268` (CRF + component stacking)
- Tier colors: `frontend/src/components/charts/IEACostStackWaterfall.tsx` (already shipped in bb3412f)
- benchmarkMode global state: `frontend/src/store/dashboard.ts` (BPP vs Tariff)

## Acceptance criteria

- 4 filter chips appear in DataTable toolbar after existing chips. Click toggles each independently; multiple active chips compose AND-style.
- Empty-state panel renders when chips zero out the table.
- Chips reflect benchmarkMode: label and tooltip swap between BPP/Tariff text.
- LcoeWaterfallModal has 4 tabs. Tab labels show `${tier} $${tier_total}`. Selected tab updates the waterfall.
- Clicking a bar in the OverviewTab IEACostStackWaterfall opens the modal on that bar's tier tab.
- EconomicsTab dashed-underline LCOE click still opens modal, defaulting to Delivered tab.
- Modal at viewport 768px: tab strip visible, no horizontal scroll on tab labels, waterfall scrolls if needed.
- 1066/1066 tests pass; no console errors in headless capture.

## Persona traceability

| Persona | What they do | Surface |
|---------|--------------|---------|
| P1 Energy Economist | "Why is Firm 8h $228?" → click Firm 8h bar in OverviewTab waterfall | Modal opens on Firm 8h tab |
| P2 DFI Investor | "Where can solar beat BPP at firm-8h reliability?" → click [8h<BPP] chip | Table filters to shortlist |
| P3 Policy Maker | "Where is solar already winning without subsidies?" → toggle [Del<BPP] | Table filters to grid-parity sites |
| P4 IPP Developer | "Show me Generation-LCOE-only ranking" → column header ▾ → Sort: Gen | Existing per-tier sort works |
| P5 KEK Tenant | "Is solar cheaper than my grid bill?" → toggle [Del<BPP] + filter by site name | Personal site visible in/out of shortlist |

## Implementation notes

- New state in `DataTable.tsx`: `belowBpp: { gen: bool, del: bool, firm4h: bool, firm8h: bool }` — single object reduces 4 separate `useState` calls. AND-composed with existing `cbamOnly` + `kekOnly` + `captiveFilter`.
- New `LcoeWaterfallModalProps`: `{ open, onClose, row, initialTier?: 'gen' | 'delivered' | 'firm4h' | 'firm8h' }`. Default `'delivered'`.
- `IEACostStackWaterfall` gets `onTierClick?: (tier: TierKey) => void` prop. OverviewTab passes a handler that sets modal state.
