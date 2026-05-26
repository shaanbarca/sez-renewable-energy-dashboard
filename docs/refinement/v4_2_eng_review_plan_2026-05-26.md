# v4.2 Plan — Engineering Review Output

**Date:** 2026-05-26
**Skill:** `/plan-eng-review`
**Input:** `docs/refinement/v4_2_project_finance_spec.md` (1233 lines) + 7 open v4.2 issues (#39, #97, #85, #80, #79, #78, #58) + codex outside voice
**Outcome:** Scope split + 15 locked decisions + 3 regression-critical paths + 1 critical failure-mode gap

## Scope split

Original v4.2 = 1 bundled release, ~6-8 weeks. Split into 4 sequenced releases (Step 0 scope reduction, accepted):

| Release | Issues | Effort | Status |
|---|---|---|---|
| **v4.2a** UX + infra + comparator | #91 (cbam_urgent fix) + #78 URL persistence + #80 IEA range filters + #79 LCOS decomp + #85 Playwright | ~1.5-2 weeks | scoped |
| **v4.2b** PF module | #39 Tier 1 (NPV/IRR/PI/Payback) + Tier 2 (DSCR/LLCR) + S-curve capex + IDC + v4.1b CBAM scenario integration | ~2.5 weeks | scoped, spec respec needed |
| **v4.2c** sensitivity + data | #39 Tier 3 sensitivity tornado + #97 custom CBAM mode + #58 high-res buildability (audit-expanded) | ~2 weeks | scoped |
| **v4.3** comparator + carryover | (none — #91 pulled to v4.2a, #97 pulled to v4.2c) | TBD | empty after pulls |

## Locked decisions (D1–D15)

### Architecture (D1–D5, A6 = D4)

- **D1**: Respec v4.2 spec §4.4 before any v4.2b code. v4.2 spec was written pre-v4.1b; tariff source toggle needs to reflect v4.1b's CBAM scenario picker. Respec is not a doc tweak — defines economic meaning of PF outputs, blocks API + data model design.
- **D2**: For CBAM-at-COD-year in PF cash flow, use vectorized `np.interp` inside `enrich_project_finance` against v4.1b's 3 snapshot columns (`cbam_destination_weighted_incumbent_{2025,2030,2034}_usd_mwh`). No new columns, no helper module. Runs once per operating year inside the 25-year cash flow loop.
- **D3**: Playwright reserved ONLY for cross-page flows + real network I/O + file downloads. Vitest + @testing-library/react remains default. Rule lands in CLAUDE.md as part of #85.
- **D4** (A6): Per-site 30m SRTM/NASADEM mini-raster for sub-pixel + low-pixel buildability sites (scope expanded per D12 audit). Not a full 1km → 30m pipeline rebuild.
- **D5**: URL serde in v4.2a ships filter chips only, but with an extensible mapping-table shape so v4.2b's PF tab knobs are 5-LOC additions (caveat: codex flags 5-LOC as optimistic — budget more generously).

### Scope (D6)

- **D6**: #97 originally deferred to v4.3, then pulled forward to v4.2c (D14) to close the tornado + CBAM strategic gap.

### Code quality (D7, D8)

- **D7**: Extend `UserAssumptions` with 9 new PF fields. No structural refactor in v4.2b. Tracking issue #101 filed for future nested-dataclass split when UserAssumptions earns its keep.
- **D8**: New lazy `/api/site/{id}/cashflow` endpoint (mirrors `/api/site/{id}/rooftop-breakdown` pattern from #82). Scorecard ships only headline PF metrics inline (NPV, IRR, equity IRR, PI, payback, DSCR_min, LLCR). PF inner math factored as a pure function (D13).

### Tests (D9)

- **D9**: Playwright runs on every PR (~1 min added CI), not label-triggered.

### Performance (D10)

- **D10**: Sensitivity tornado debounced 500ms after last assumption change. 1620 PF computes per render = 160ms–1.6s at the high end; debounce keeps the UI responsive while assumption sliders move.

### Outside-voice tensions (D11–D14)

- **D11**: Pull #91 (cbam_urgent comparator fix) forward into v4.2a, before PF lands. PF inherits `solar_competitive_gap_pct`; without the comparator fix, PF metrics are computed against a known-wrong baseline. ~1-2 days added to v4.2a.
- **D12**: Before locking #58 scope, audit polygon_area_ha = 100-300 sites for 1km-vs-30m mini-raster delta. If material under-reporting exists, expand #58 scope past the 19 zero-MWp sites.
- **D13**: v4.2b ships `compute_pf_metrics(row, assumptions, year) -> dict` as a pure function alongside the scorecard columns + the lazy endpoint. Tornado in v4.2c wraps it; no v4.2b API reshape needed.
- **D14**: Pull #97 (custom CBAM) into v4.2c alongside tornado. Closes the "what if CBAM is X?" gap that tornado v1 would otherwise have. v4.2c grows from ~1 week to ~2 weeks.

### User feedback (D15)

- **D15**: Add S-curve capex disbursement + Interest During Construction (IDC) line to v4.2b's spec respec. Default Beta(2,2) over `construction_years`; user can override per-year capex split. Lump-sum year-0 capex (current spec §4.2) biases IRR 1-2pp upward — could blow the Cirata ±1pp anchor test. v4.2b grows from ~2 weeks to ~2.5 weeks.

## Regression-critical paths (IRON RULE, no AskUserQuestion)

1. **#79 LCOS decomp sum**: sum of 3 new sub-columns must equal existing `hybrid_lcos_usd_mwh` within $0.5/MWh. Spec acceptance criterion.
2. **#58 byte-identical for unaffected sites**: sites that don't need the 30m mini-raster stay byte-identical in the golden fixture (modulo D12 audit findings).
3. **v4.2b PF reads from unchanged v4.1b columns**: `cbam_active_scenario_value_usd_mwh`, `emissions_intensity_current`, `lcoe_generation_usd_per_mwh` semantics MUST NOT change.

## Critical failure-mode gap (must address)

- **URL serde malformed param**: a bad URL param could throw on mount and white-screen the dashboard. v4.2a #78 must include explicit try/catch + fallback to defaults in the serde.

## Cirata anchor + supplementary validation

The v4.2 spec §11 names Cirata Floating PV (CAPEX $145M, tariff $58.20/MWh, expected IRR 8-10%) as the ±1pp anchor for every other site's IRR. Codex flagged this as overtrust ("one floating PV project can't validate industrial decarb PF across heterogeneous sites"). Spec acknowledges Cirata is the only published Indonesian solar IPP data; weakening the gate leaves no anchor.

**Implementation note:** add to PF tab tooltip — "Cirata is a solar floating PV anchor; industrial site IRRs are extrapolated and carry higher uncertainty. Indicative only."

## Parallelization (worktree-friendly)

```
v4.2a (~1.5-2 weeks)
  ├── Lane 1 (sequential):  #91 cbam_urgent fix  →  #78 URL persistence  →  #80 IEA range filters
  ├── Lane 2 (independent): #79 LCOS decomposition
  └── Lane 3 (independent): #85 Playwright infra + first rooftop modal test

v4.2b (~2.5 weeks, sequential single worktree)
  step 1: Respec v4.2 spec §4.4 + add S-curve + IDC (D1 + D15)
  step 2: Extend UserAssumptions (D7) + compute_pf_metrics() pure function (D13)
  step 3: enrich_project_finance with np.interp CBAM (D2)
  step 4: /api/site/{id}/cashflow endpoint (D8)
  step 5: Score Drawer PF tab UI
  step 6: Cirata anchor regression test

v4.2c (~2 weeks)
  ├── Lane 1: sensitivity tornado (extends v4.2b PF; debounced 500ms)
  ├── Lane 2: #97 custom CBAM mode
  └── Lane 3: #58 high-res buildability (audit-expanded scope per D12)
```

**Codex concerns to apply per-release (not asking on, noting inline):**
- Each release needs acceptance criteria + demo script + rollback criteria written before its PR opens (C8).
- Render auto-deploys on push to main; no feature-flag infra in the project. v4.2b should consider an `EEZ_PF_ENABLED` env gate so a Cirata-test failure on main doesn't break prod indefinitely (C16).

## What's still in v4.3+

- (none from this review's deferrals — both #91 and #97 got pulled forward)
- #34 v4.3 substation utilization override + transmission feasibility flip (carryover)
- #101 v4.3+ UserAssumptions nested-dataclass refactor (filed in this review)
- #30 v5.0 PyPSA shadow prices (unchanged)
- #9 v4.4 RUPTL feedback loop (unchanged)

## Test plan

See `~/.gstack/projects/eez/shaanbarca-release-v4.1b-eng-review-test-plan-20260526.md` for the full coverage diagram. Key gates:

| Gate | Where | Test type |
|---|---|---|
| Cirata anchor ±1pp | v4.2b | pytest (loaded with published Cirata numbers) |
| #79 LCOS sub-bar sum | v4.2a | pytest (numerical assertion ±$0.5/MWh) |
| #58 unaffected-site invariance | v4.2c | golden fixture test (byte-identical) |
| URL serde round-trip | v4.2a | Playwright [→E2E] |
| PF tab fire + render | v4.2b | Playwright [→E2E] |
| Custom CBAM scenario edit | v4.2c | vitest + @testing-library/react |
| Tornado debounce | v4.2c | vitest + happy-dom |

## How to use this document

For each release, the kickoff is:
1. Open a fresh branch (`v4.2a/<theme>`, `v4.2b/pf-module`, `v4.2c/sensitivity`).
2. Read the relevant decisions above (D1–D15).
3. Write the release-level demo script per C8.
4. Sequence per the parallelization map.
5. PR + merge to main per the existing Rich-template workflow.
6. CHANGELOG: each release gets its own `[4.2a] - YYYY-MM-DD` section (no more single-Unreleased accumulation; v4.1b release-cut policy from `CHANGELOG.md`).

---

**Status:** scope review complete. Implementation can start with v4.2a; #91 (cbam_urgent fix) first, then #78 URL persistence, then fork.
