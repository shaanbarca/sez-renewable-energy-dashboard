# UI conventions

Frontend conventions that bind across contributors. Lightweight, growing as new patterns emerge. Linked from CLAUDE.md so Claude Code sessions see it on init.

## Tooltips on UI-surfaced columns

Every column surfaced in a UI table or drawer with a **non-obvious name** must have a tooltip on the column header AND on per-row badges/values.

"Non-obvious" = anything a smart user couldn't infer from the label alone:

- Confidence tiers (e.g. `Confidence`, `Polygon`, `Source`)
- Provenance flags (e.g. `polygon_source_tier`, `building_data_confidence`, `data_vintage`)
- Raw metric names that don't carry units in the label (e.g. `PVOUT`, `CF`, `LCOE`)
- Computed indices and ratios (e.g. `wb_buildout_footprint_ratio`, `solar_competitive_gap_pct`)
- Anything whose interpretation depends on a methodology decision (e.g. baseline-vs-override semantics, cost-tier semantics like Raw/Firmed/Delivered)

**Why this matters.** Dashboards live or die on first-touch clarity. A development bank analyst opening this dashboard for the first time should be able to understand any number on screen by hovering it, without reading the methodology doc. Tooltips are the fastest way to deliver the methodology where the user already is.

### Pattern

Headers — `SortHeader` accepts a `tooltip` prop:

```tsx
<SortHeader
  label="Polygon"
  sortKey="polygon"
  active={sort.key}
  dir={sort.dir}
  onSort={onSort}
  tooltip="Trust level of the fence-line polygon used for clipping. Official > OSM > Estimated > Buffer."
/>
```

Per-row badges or values — wrap with `title={...}`:

```tsx
<span title={polyBadge.tooltip}>{polyBadge.label}</span>
```

For more elaborate descriptions in drawer surfaces — use `StatRowWithTip`:

```tsx
<StatRowWithTip
  label="Captive Capacity"
  value={adjustedCapacity?.toFixed(1)}
  unit="MWp"
  tip={`Baseline ${baseline} MWp + ${pct}% × ${softExcluded} MWp soft-excluded override...`}
/>
```

### Length

Aim for **one to two sentences** in tooltips. If the explanation would be longer, link to the relevant `docs/METHODOLOGY_CONSOLIDATED.md` § anchor inside the tooltip text. The tooltip is not the place to write a thesis.

### Anti-patterns

- Headers like `pvout_within_boundary` without a tooltip ("what is pvout?", "what's within-boundary mean?")
- A `Confidence` column where the badge values say `HIGH` / `MEDIUM` / `LOW` with no per-row tooltip explaining what they're confident _about_
- Tooltips that just repeat the column label ("Confidence — confidence level")
- Tooltips written in passive-voice / consultant tone ("The level of confidence in the underlying data may be considered...")

### Reviewer prompt

If you're reviewing a PR that adds or renames a UI-surfaced column, check:

- Does the header have a `tooltip`?
- If it's a badge or categorical value, does each badge/value have a per-row `title`?
- Is the tooltip one to two sentences max?
- Does it link to METHODOLOGY if the topic deserves more than two sentences?

A column without a tooltip on a name a non-author can't immediately decode is a regression.
