# v4.1: IEA-aligned cost stack in the dashboard UI

**Filed**: 2026-05-16
**Trigger**: PR #74 (v4.1a foundation) shipped the IEA-aligned 4-tier cost stack as new scorecard columns. Subsequent work (M-AT8a, M-AT8b, this branch's polygon work) didn't surface them in the UI. A user-facing dashboard with rigorous IEA terminology in the methodology doc but NO IEA labels in the score drawer or ranked table is failing on its own premise — DFI analysts (Persona 1, 2) expect to see IEA terminology.

**Anchor**: spec at `docs/refinement/v4_1_foundation_spec.md` §2 + METHODOLOGY §18.6 (additive migration story).

## The 4 tiers and why they matter

| Tier | Column | What it represents | DFI question it answers |
|---|---|---|---|
| 1 | `lcoe_generation_usd_mwh` | On-site solar LCOE alone — no transmission, no connection, no storage | "What's the raw cost to generate a MWh of solar at this site?" |
| 2 | `full_system_lcoe_delivered_usd_mwh` | Generation + gen-tie + connection cost | "What does it cost to deliver that MWh to the offtaker (vs PLN doing the same)?" |
| 3 | `full_system_lcoe_firm_4h_usd_mwh` | Delivered + 4h LCOS × storage_share (0.20) | "Adjusted for 4h battery firming — is it competitive with peaking gas?" |
| 4 | `full_system_lcoe_firm_8h_usd_mwh` | Delivered + 8h LCOS × storage_share (0.50) | "Adjusted for 8h battery — competitive with **baseload captive coal**?" |

**Invariant**: Tier 1 ≤ Tier 2 ≤ Tier 3 ≤ Tier 4 (monotone-rising). Pinned by `test_v4_1_foundation` regression test (all 81 sites).

For **IMIP** today: $83 generation → $144 delivered → $179 firm-4h → $228 firm-8h. Captive coal incumbent is $50. Solar isn't competitive even at the raw generation tier — that's the right signal once the IEA stack lands in the UI.

## Persona mapping

| Persona | Why they need IEA terminology |
|---|---|
| **P1 Energy Economist** (ADB, IFC analyst) | Speaks IEA terminology fluently — "Full System LCOE" is in every IEA Energy Outlook chapter. Showing this language signals methodological rigor. |
| **P2 DFI Infrastructure Investor** | Compares against IEA-published reference values (NREL ATB, IRENA Battery Cost Report). Needs to see WHICH IEA tier our number maps to. |
| **P3 Policy Maker** (primary) | Less fluent in IEA jargon but follows it. Wants the gap math (LCOE - incumbent / incumbent) in the right basis — Firm 8h vs captive coal at IMIP, not "Solar LCOE" vs PLN tariff. |
| **P4 IPP Developer** | Cares most about Tier 2 (Delivered) — that's the PPA-relevant number. |
| **P5 KEK Tenant** | Cares about Tier 1-2 for behind-the-meter rooftop economics; Tier 4 for full self-supply scenarios. |
| **P6 Green Industry Roadmap Planner** | Wants to compare sector-rolled IEA tiers across cohorts (cement vs steel vs nickel). |

## Three concrete UI changes

### 1. Score drawer — new "IEA Cost Stack" section in OverviewTab

Inserted between existing "At a Glance" and "Energy Balance" sections. 4 rows, each labelled per IEA convention. Each row carries the value + a small ladder indicator showing position relative to the incumbent (the same `effective_incumbent_lcoe_usd_mwh` we just shipped in M-AT8b).

```
┌─────────────────────────────────────────────────┐
│ IEA Cost Stack (?)                              │
│ The 4-tier IEA-aligned LCOE ladder              │
│                                                 │
│ Generation                       $83 /MWh  ↓    │
│ Full System (Delivered)         $144 /MWh  ▼    │
│ Full System Firm 4h             $179 /MWh  ▼    │
│ Full System Firm 8h             $228 /MWh  ▼    │
│                                                 │
│ vs Captive Power $50 [Coal][T1]                 │
└─────────────────────────────────────────────────┘
```

Tooltip on `?` header: "IEA-aligned LCOE breakdown per docs/METHODOLOGY §18.6. Each tier adds a cost layer to the one above (transmission, then storage). Solar-cheaper-than-incumbent at any tier is the competitiveness signal."

Per-row tooltips: short IEA-style definitions ("Generation: on-site cost only, no transmission. NREL ATB-aligned.")

### 2. Economics tab — replace the lcoe-with-battery block with the IEA stack

EconomicsTab currently shows `lcoe_with_battery_usd_mwh` and a "Still Competitive" check. M-AT8a already produces Firm 4h/8h values that supersede this. Replace the block with the IEA 4-tier table (same shape as above), plus a "Storage Adder Breakdown" sub-row showing LCOS 4h / 8h independently.

### 3. Ranked table — two new sortable columns

Per the design system in `docs/UI_CONVENTIONS.md` (column tooltips required for non-obvious names):

| Column | Name | Tooltip |
|---|---|---|
| `lcoe_generation_usd_mwh` | "Generation LCOE" | "On-site solar LCOE only (no transmission, no storage). IEA Tier 1. Most directly comparable to NREL ATB benchmarks." |
| `full_system_lcoe_delivered_usd_mwh` | "Full System LCOE" | "Generation + gen-tie + connection cost. IEA Tier 2. The PPA-relevant number for grid-connected solar IPPs." |

Both default-visible. The Firm 4h/8h columns stay opt-in via the column picker (most users won't sort by them; advanced users can add them).

## Out of scope (deferred)

- Trajectory: how the IEA stack changes over time (year slider) — that's the same M-AT8c work blocked on M-AT7
- Per-WACC sensitivity bands (Firm 8h at 4% concessional vs 10% commercial) — v4.4
- Methodology drawer with stacked-bar visualization — v4.4 polish
- Sector-rolled IEA averages in SectorSummaryChart — out of scope for this PR

## Risk

Low. Additive — the 4 columns already exist in scorecard CSV; just exposing them. Existing "Solar LCOE" / "Competitive Gap" rows stay; the IEA stack is a new section that DFI analysts can scan independently. No behavior change to action flags or gap math.

## Design decisions (from /plan-design-review 2026-05-16)

| # | Decision | Rationale |
|---|---|---|
| **1** | **Single IEA vocabulary everywhere.** Rename "Solar LCOE" → "Full System LCOE (Delivered)" in OverviewTab + Action Tab + DataTable. The current `lcoe_mid_usd_mwh` ≈ Tier-2 Delivered, so this is relabeling, not math change. | DFI/IFC analysts recognize IEA terms instantly. Dual vocabularies (Solar LCOE + IEA stack) on same page = goodwill drain per Krug. |
| **2** | **Inline waterfall chart IS the cost section in OverviewTab.** Reuses Recharts (already in stack); pattern matches `LcoeWaterfallModal.tsx`. Renders inline (not modal). Replaces the numeric ladder. Competitive Gap row stays below the waterfall. | Visual storytelling: the monotone-rising IEA stack is fundamentally a "this much, then this much more, then this much more" narrative. Numbers say the values; the chart says the story. |
| **3** | **Inline mini-ladder in ONE table column** showing all 4 tiers compactly: `$83 → 144 → 179 → 228` with sub-labels (G / D / 4h / 8h) below. Sort defaults to Delivered ($144); column header has a small switcher to sort by any of the 4 tiers. | All 4 tiers visible per user request, but space-efficient. ~140px wide cell; readable at default table density. Single sortable column. |
| **4** | **Waterfall replaces the numeric "Solar LCOE / Grid Cost" rows** in OverviewTab's "At a Glance". Competitive Gap row STAYS below the waterfall (it's the action signal). The captive comparator rows (M-AT8b) stay above as the incumbent context. | One canonical place for cost story. Clean visual hierarchy: incumbent context → cost stack → gap signal. |
| **5** | **Empty-state fallback**: when `lcoe_generation_usd_mwh` is null but legacy `lcoe_mid_usd_mwh` is populated, render a degraded waterfall with one bar at lcoe_mid + "Estimated (legacy)" badge. Table cell shows `$144 [est]` instead of full ladder. | Graceful degradation. Older / wind-only sites still show something useful with a flag explaining why it's not the full IEA stack. Avoids data-shaped holes in the UI. |

## Concrete UI spec

### OverviewTab — new structure (with M-AT8b context preserved)

```
[Identity card] (unchanged)

┌─ Location & Grid ──────────────────────────┐
│ Province / Grid Region (unchanged)         │
└────────────────────────────────────────────┘

[EnergyBalanceChart] (unchanged)

┌─ Cost & Competitiveness ───────────────────┐
│ [Captive Power $50 [Coal][T1]]  ← M-AT8b   │
│ [Grid Cost (secondary, if hybrid)]         │
│                                            │
│ ┌─ IEA Cost Stack ──────────────────────┐  │
│ │ [WATERFALL]                           │  │
│ │  $83 → +$61 → +$35 → +$49 = $228      │  │
│ │  Gen  Deliv  Firm4h Firm8h            │  │
│ │ Tooltip per bar: IEA definition       │  │
│ └───────────────────────────────────────┘  │
│                                            │
│ Competitive Gap +185% (vs Captive Coal)    │
│ [T1 pill if tier=T1]                       │
└────────────────────────────────────────────┘

[Best RE / Coverage / etc.] (unchanged)
```

Tooltips per bar (Recharts onMouseEnter on each Bar):
- Generation: "IEA Tier 1 — On-site LCOE only. No transmission, no storage. NREL ATB-aligned. The raw cost to generate a MWh of solar at this site."
- Delivered (Tier 2): "IEA Tier 2 — Generation + gen-tie + connection cost. The PPA-relevant number for grid-connected solar IPPs."
- Firm 4h: "IEA Tier 3 — Delivered + 4h battery storage adder. Adjusted for peaking-gas equivalence."
- Firm 8h: "IEA Tier 4 — Delivered + 8h battery. Adjusted for baseload captive coal equivalence."

### DataTable — new "IEA Cost Stack" column

Replaces the existing "Solar LCOE" column position in the Cost group. Cell:

```tsx
<div className="flex flex-col text-[10px] tabular-nums">
  <span className="inline-flex items-center gap-1">
    {gen?.toFixed(0) ?? '—'}
    <span className="text-[9px] opacity-60">→</span>
    {delivered?.toFixed(0) ?? '—'}
    <span className="text-[9px] opacity-60">→</span>
    {firm4h?.toFixed(0) ?? '—'}
    <span className="text-[9px] opacity-60">→</span>
    {firm8h?.toFixed(0) ?? '—'}
  </span>
  <span className="text-[8px] text-muted flex justify-between" style={{ minWidth: 110 }}>
    <span>G</span><span>D</span><span>4h</span><span>8h</span>
  </span>
</div>
```

Column header includes a small sort switcher (dropdown or buttons G/D/4h/8h) defaulting to D (Delivered). Tooltip:

> IEA-aligned cost stack: Generation (on-site only) → Delivered (+ transmission) → Firm 4h (+ 4h battery) → Firm 8h (+ 8h battery). Sort by any tier. See methodology §18.6.

For sites with null IEA fields: cell renders `$144 [est]` using legacy `lcoe_mid_usd_mwh` with a small "estimated" tag.

### ActionTab

Keeps the captive/grid comparator rows (M-AT8b). The IEA waterfall lives in OverviewTab as the canonical cost surface; ActionTab links to it via the existing tab nav. No duplication.

### EconomicsTab

The existing `LcoeWaterfallModal` (CAPEX + FOM + connection breakdown) stays — that's a DIFFERENT waterfall (component breakdown, not IEA tier stack). The new IEA waterfall in OverviewTab is at the per-tier level. Both can coexist; they answer different questions:
- LcoeWaterfallModal: "What's IN the LCOE?" (CAPEX / FOM / land / transmission)
- IEA waterfall: "What's the LCOE AT EACH TIER of the IEA hierarchy?"

A linking sentence in OverviewTab's IEA chart caption: "Click any bar for component breakdown" launches the existing LcoeWaterfallModal scoped to that tier.

### Responsive

- **Mobile (<768px)**: drawer is full-width slide-over. Waterfall has minimum 280px width — fits comfortably. Bar labels stack below bars in compact mode.
- **Table ladder cell on mobile**: collapses to just the Delivered value `$144 (D)` with the full ladder shown on tap (mobile tooltip pattern).

### A11y

- Waterfall: Recharts `accessibility={{ enabled: true }}` already supported. Each Bar gets `aria-label` summarizing its tier + value.
- Table column header sort switcher: keyboard-navigable per existing pattern.
- Empty-state badge "[est]": `aria-label="Estimated value, not based on full IEA cost stack"`.

## Implementation order

1. Backend: confirm IEA fields flow through `data_loader.py` + `scorecard.py` → ScorecardRow (already done in this branch via M-AT8b's same pattern).
2. New component: `frontend/src/components/charts/IEACostStackWaterfall.tsx` — Recharts waterfall, identical pattern to `LcoeWaterfallModal` but rendering tier deltas not component breakdown.
3. OverviewTab: replace "Solar LCOE" row + cost-section structure with waterfall + Competitive Gap (preserving M-AT8b captive context above).
4. DataTable: new inline-ladder column + sort switcher in the existing Cost group.
5. Rename `lcoe_mid_usd_mwh` references to "Full System LCOE (Delivered)" labels in any user-visible string (tooltips, labels). Internal column name stays unchanged for backwards compat.
6. Add empty-state fallback logic for null IEA fields.
7. Tests: `IEACostStackWaterfall.test.tsx` + table column rendering.
