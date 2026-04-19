# Priority 6 — Export and Reporting Improvements

**Status:** Stashed. Spec captured, implementation deferred.
**Owner persona:** Persona 6 (Green Industry Roadmap Planner) — BKPM / KESDM / Bappenas advisor, sustainability consultancy, research institution.
**Source:** Direct user ask, 2026-04-19. "This is the gap your institutional users will hit next. They can see the data in the dashboard but they need to get it OUT of the dashboard and INTO their deliverables."

---

## Why this exists

Institutional users don't live in the dashboard. They live in Google Slides, Word, and PDF appendices that get emailed to clients. Right now the dashboard gives them site-level CSV — fine for analysts, wrong shape for deliverables. A roadmap report needs sector-level rollups and one-page sector summaries. If the roadmap team can't paste our numbers into their deck in under 5 minutes, they won't cite us.

The gap is documented in `PERSONAS.md` under Persona 6 data-gaps: "Sectoral summary PDF export not yet built" + "Flip diff CSV does not aggregate to sector level."

## What to build

### Deliverable A — Sectoral summary PDF

One page per sector (cement, steel, nickel, aluminium, fertilizer, mixed). Each page:

- Sector name + site count
- Total 2030 demand (GWh)
- Total CBAM exposure 2026 / 2030 / 2034 (USD, current free-allocation schedule)
- Implied transition CAPEX (sum of solar + BESS + grid costs across buildable sites)
- Distribution of action flags (stacked bar or just counts)
- Top 5 sites by CBAM exposure, with LCOE, grid cost, gap-to-grid, flag
- Footer: data cutoff date, DOI, methodology URL

Rendered to PDF. Downloadable from a button on the Sector Summary bottom-panel tab.

**Format goes into a roadmap report appendix as-is — no re-layout.**

### Deliverable B — Flip scenario diff with sector rollups

Current CSV is one row per site. Add aggregate rows so the exported file reads:

```
scope,sector,metric,baseline_mean,flip_mean,delta_mean,flipped_count,total_count
sector,cement,lcoe_usd_mwh,76.3,61.2,-15.1,3,32
sector,steel,lcoe_usd_mwh,82.1,67.8,-14.3,2,7
...
site,cement,lcoe_usd_mwh,...
```

Sector rows enable the executive-summary line: "Across all 32 cement sites, 60% concessional finance reduces average LCOE by 20% and flips 3 sites from not-competitive to near-parity."

---

## Open scoping questions (resolve before coding)

### Q1. PDF rendering: server-side or client-side?

- **Server-side (ReportLab / WeasyPrint):** reproducible across browsers, no render drift, but adds a Python dep and a `/api/export/sector-pdf` endpoint. One more thing to keep running on Render.
- **Client-side (jsPDF + html2canvas):** zero backend changes, but PDF quality depends on user's browser + screen DPI, and the SectorSummaryChart rendering needs careful canvas snapshotting.

**Default lean:** server-side. Reproducibility matters for a citable artifact. Render has the Python runtime already.

### Q2. Include the SectorSummaryChart image in the PDF?

- **Yes:** the stacked bar is the best single view of the sector. Include it.
- **No:** table-only PDFs are smaller and easier to diff.

**Default lean:** yes, include the chart as a PNG embed. Roadmap reports are visual.

### Q3. CSV shape — one file or two?

- **One file** with a `scope` column (`sector` or `site`): sector rows at top, site rows below. Sortable/filterable downstream.
- **Two files** (`flip_diff_sectors.csv` + `flip_diff_sites.csv`): cleaner schema per file but users juggle two downloads.

**Default lean:** one file, `scope` column. Matches how pandas users actually pivot.

### Q4. What sector metrics matter in the rollup?

Candidates:
- `lcoe_usd_mwh` (solar / wind / hybrid / best)
- `grid_cost_usd_mwh` (BPP or tariff)
- `gap_to_grid_pct`
- `cbam_cost_2030_usd_per_tonne`
- `cbam_savings_2030_usd_per_tonne`
- `transition_capex_usd` (sum, not mean)
- `flipped_count` (sites that changed economic tier)

**Default lean:** all of the above, wide format. One row per (sector × metric). 6 sectors × ~7 metrics = ~42 rows. Fine.

### Q5. Who drives the roadmap team's actual workflow?

This is the blocking unknown. We don't know if they paste into Slides, Word, or PDF appendices. We don't know if the LCOE number that matters is mean, median, P10, or weighted-by-demand. We don't know if they want USD or IDR.

**Before building:** do one 30-minute call with a prospective roadmap user (Bappenas contact, SYSTEMIQ, IESR). Show the Sector Summary tab. Ask "if I gave you a PDF of this, where does it go in your report?" Their answer determines everything above.

---

## Size estimate

- Backend: `src/api/routes/export.py` — 2 new endpoints (`/api/export/sector-pdf`, `/api/export/flip-diff-csv`). ~300 LOC.
- PDF generation: `src/api/export/sector_pdf.py` using ReportLab. ~400 LOC (one page generator + data aggregation).
- Frontend: 2 new buttons (Sector Summary tab, Scenario Compare tab). ~80 LOC.
- Tests: 2 new test files — `tests/test_export_sector_pdf.py`, `tests/test_export_flip_diff.py`. Assert file generated, sector aggregation correct, DOI present in PDF metadata. ~200 LOC.
- Docs: update `EXECUTIVE_SUMMARY.md` ("Exports" section), `CHANGELOG.md`, `PERSONAS.md` (flip Persona 6 gaps from ❌ → ✅).

**Total:** ~1 week end-to-end including the 30-minute user call and one round of revision.

---

## Dependencies

- `reportlab` (BSD license, already allowed) — or `weasyprint` if we want HTML-to-PDF
- `matplotlib` already in deps for any chart embedding
- No new data pipeline steps — everything comes from existing `compute_scorecard_live` output

---

## Test plan

1. Golden-master PDF: generate sector PDF with locked assumptions, commit PDF hash, fail test if hash drifts.
2. Flip diff CSV round-trip: compute flip diff, export CSV, re-parse, assert sector rollup math matches `df.groupby('sector').mean()`.
3. DOI embedded in PDF metadata (citability check).
4. Smoke test: export all 6 sector PDFs under default assumptions, assert all files >10 KB and valid PDF magic bytes.

---

## Risks

| Risk | Mitigation |
|---|---|
| PDF rendering drifts between local + Render | Pin reportlab version, run golden-master hash in CI |
| Sector rollup math wrong on edge-case sectors (e.g. nickel clusters with NaN `capacity_annual_tonnes`) | Explicit NaN handling + test fixture with at least one NaN row |
| Roadmap team actually wants something else entirely | Q5 — do the 30-min call before writing code |
| Adds server-side latency on a free-tier Render plan | Generate PDFs on a background thread, return a job ID + poll endpoint. Not for MVP — do sync if <5s for 6 sectors. |

---

## When to revisit

Resume this when either:
- A named Persona-6 user (Bappenas, SYSTEMIQ, IESR, research lab) asks for the export capability, OR
- Ammonia + petrochem ingestion (M28/M29) closes — so the universe is stable before we lock the PDF format

Until then, Persona 6 readiness stays at 87% per PERSONAS.md.
