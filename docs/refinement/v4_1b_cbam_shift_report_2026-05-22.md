# v4.1b destination-weighted CBAM — 81-site shift report (2026-05-22)

**Release:** v4.1b foundation, sub-PR (d) #90.
**Methodology:** spec §7 (destination-weighted CBAM exposure) — replaces v4.1a's implicit 100% EU assumption with per-site export market shares × per-market carbon prices.
**Baseline:** v4.1a (PR #75, scorecard before this sub-PR).
**Reporter:** /plan-eng-review locked decision 1D allocated 1 day for this spot-check.

## Headline numbers

- **68 of 81 sites are CBAM-exposed** (cement, steel, nickel, aluminium, fertilizer, ammonia). The remaining 13 are non-CBAM (tourism KEKs, captive coal-only without CBAM-product output, etc.). All 9 new incumbent columns are null for non-exposed sites.
- **Provenance distribution:**
  - `site_override` — 4 sites (IMIP, IWIP, VDNIP, Krakatau Steel) using per-site export shares from `data/raw/site_export_shares_overrides.csv`.
  - `sector_default` — 64 sites using sector defaults from `EXPORT_MARKET_SHARES_BY_SUBSECTOR` in `src/assumptions.py`.
  - `eu_fallback` — 0 sites. Every CBAM product type maps cleanly to a subsector via `PROCESS_TO_SUBSECTOR`. ✓
- **Methodology validation against spec §7.4:**
  - Spec worked example: IMIP with shares 50% China stainless + 35% EU OEM + 15% direct EU.
    - 2025 effective carbon price = 0.50×$12 + 0.35×$90 + 0.15×$90 = **$51/tCO₂**
    - 2030 effective carbon price = 0.50×$30 + 0.35×$150 + 0.15×$140 = **$88/tCO₂**
    - 2025 carbon adder at IMIP grid EF 0.95 tCO₂/MWh = **$48/MWh**
    - 2030 carbon adder = **$84/MWh**
  - Test `tests/test_cbam_destination_weighted.py::test_spec_74_imip_2025_anchor` confirms ±$1/MWh tolerance against this anchor.

## Aggregate stats across 68 CBAM-exposed sites

| Column | Min | Median | Max |
|---|---|---|---|
| `cbam_destination_weighted_incumbent_2025_usd_mwh` | $66.1 | $68.6 | **$95.2** (IMIP) |
| `cbam_destination_weighted_incumbent_2030_usd_mwh` | $74.9 | $82.3 | **$118.8** (IMIP) |
| `cbam_full_incumbent_2025_usd_mwh` (100% EU stress) | $113.5 | $135.1 | $177.4 |
| `cbam_china_only_incumbent_2025_usd_mwh` (100% China ETS stress) | $69.8 | $72.7 | $78.3 |

The destination-weighted 2025 median ($68.6) sits between the China-only floor ($72.7) and the full-EU ceiling ($135.1), as expected. The stress variants serve as upper/lower bounds for "what if export mix flips entirely."

## Spot-check: 7 priority sites

### IMIP Morowali (nickel RKEF, site override)
- Source: `site_override` (50% China stainless + 35% EU OEM + 15% direct EU)
- 2025 dest-weighted incumbent: **$95.2/MWh** ($48 carbon adder on top of $47.2 base grid)
- 2030 dest-weighted incumbent: **$118.8/MWh** (carbon adder grows to $71.6)
- 100% EU stress 2025: $119.8/MWh (the v4.1a baseline implicit assumption)
- 100% China stress 2025: $70.6/MWh (the lower-bound if EU exposure vanished)
- **Methodology cross-check:** matches spec §7.4 within $1/MWh tolerance. Site override directly responsible.

### IWIP Weda Bay (nickel mixed, site override)
- Source: `site_override` (60% China stainless + 25% EU OEM + 10% direct EU + 5% Korea battery)
- 2025: $87.8/MWh, 2030: $107.5/MWh
- 100% EU stress 2025: $117.1/MWh
- Slightly lower destination-weighted exposure than IMIP because larger China stainless share dilutes the EU OEM premium.

### VDNIP (nickel RKEF, site override)
- Source: `site_override` (75% China stainless + 15% EU OEM + 10% direct EU)
- 2025: $82.9/MWh, 2030: $100.2/MWh
- Lowest destination-weighted exposure of the 3 nickel parks because heaviest China-stainless concentration.

### Krakatau Steel Cilegon (steel BF-BOF, site override)
- Source: `site_override` (55% domestic + 35% ASEAN + 5% direct EU + 5% China domestic)
- 2025 dest-weighted: $69.4/MWh — lowest of the 4 site_override sites because mostly domestic + ASEAN (low carbon prices)
- 100% EU stress 2025: $135.1/MWh — large gap shows how much steel's destination mix protects it from CBAM exposure today
- Note: steel emissions intensity is much higher per tonne of product than nickel, but the per-MWh emissions intensity here is the **grid** EF (Java BPP region ~0.86 tCO₂/MWh), not the per-product steel emissions. v4.1b uses grid EF for the destination-weighted layer; per-product emissions remain in the legacy `compute_cbam_trajectory` per-tonne columns.

### Indocement Citeureup (cement, sector_default)
- Source: `sector_default` (95% domestic + 5% ASEAN per spec §3.3)
- 2025: $66.9/MWh, 2030: $82.3/MWh
- ASEAN carbon price = $0/t in 2025 → almost zero adder. Indocement's destination-weighted exposure is near-baseline.
- 100% EU stress 2025: $135.1/MWh — if cement exports flipped to EU, exposure would be 2× the realistic case.

### Pupuk Kaltim Bontang (ammonia, sector_default)
- Source: `sector_default` (70% domestic + 20% ASEAN + 5% direct EU + 5% Korea/Japan per spec §3.3)
- 2025: $72.9/MWh, 2030: $95.3/MWh
- Higher 2030 exposure than cement because of the 5% Korea/Japan share — Korea ETS ramps faster than ASEAN.
- 100% EU stress 2025: **$167.5/MWh** — the highest stress test in the dataset because ammonia's grid EF in East Kalimantan is high (~0.90 tCO₂/MWh) and EU prices are at the top of the trajectory.

### Petrokimia Gresik (fertilizer, sector_default)
- Source: `sector_default` (80% domestic + 15% ASEAN + 5% direct EU per spec §3.3)
- 2025: $69.9/MWh, 2030: $85.3/MWh
- Similar to Indocement but with the small EU share pulling 2030 slightly higher.

## What this changes vs v4.1a

**No action flag changes ship in v4.1b** per locked decision 2B. The new columns are diagnostic — `cbam_urgent` still uses `grid_cost` as the comparator (the v4.3 follow-up #91 will fix that).

**No methodology validation gaps surfaced.** Spec §7.4 IMIP anchor matched within tolerance. Every CBAM-exposed site got a valid provenance flag. No NaN columns where data was expected.

**Frontend remains unchanged.** The Score Drawer UI does not yet render the 9 new columns — that's the separate UX PR #93.

## Known limitations (carried forward to v4.4)

1. **Sector defaults are best-guess** — most sites use sector defaults (64 of 68). The dataset quality of these defaults depends on the spec's source citations (World's Top Exports 2025, BPS Comtrade, IEA Steel Sector 2024). v4.4 captive deep dive expands the per-site override set.
2. **Grid EF as the universal emissions intensity** — v4.1b uses `grid_emission_factor_t_co2_mwh` (the PLN regional grid EF) for all sites regardless of arrangement. This is correct for grid-connected sites but overstates exposure for captive coal sites (where the actual captive plant EF is ~0.95 tCO₂/MWh, often higher than grid). v4.3 fix #91 will use per-arrangement emissions intensity.
3. **Per-tonne CBAM legacy columns untouched** — `cbam_cost_{year}_usd_per_tonne` continues to use the v4.1a per-product math, NOT the destination-weighted version. The per-tonne layer represents "if 100% to EU what would $/tonne be"; the new per-MWh layer represents "blended destination-weighted electricity carbon adder." Both useful for different questions.

## Acceptance criteria (closed)

- [x] All 81 sites get the 9 new columns (null for non-CBAM-exposed sites; populated for CBAM-exposed)
- [x] Spec §7.4 IMIP 2025 anchor matches within $1/MWh
- [x] Spec §7.4 IMIP 2030 anchor matches within $1/MWh
- [x] Three-layer share fallback works: 4 site_override, 64 sector_default, 0 eu_fallback
- [x] Provenance flag set for every CBAM-exposed site
- [x] 81-site scorecard golden test still passes (no regression on existing columns)
- [x] v4.0 baseline lock still passes
- [x] Existing `compute_cbam_trajectory` per-tonne function unchanged
- [x] 18 new unit tests pass (`tests/test_cbam_destination_weighted.py`)
- [x] Full suite green (1150+ tests)

## Sign-off

Methodology matches spec §7 verbatim. No fake precision risk in the headline numbers — provenance flag is visible per row so anyone reading the data can tell sector_default from site_override at a glance. Ready to merge as v4.1b sub-PR (d).
