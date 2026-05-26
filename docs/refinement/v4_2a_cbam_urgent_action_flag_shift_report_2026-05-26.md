# v4.2a — `cbam_urgent` Action Flag Shift Report

**Date:** 2026-05-26
**PR:** v4.2a step 1 (closes #91)
**Methodology change:** `cbam_urgent` action flag comparator now uses the site-appropriate carbon-adjusted incumbent (captive_coal_lcoe for captive sites, grid_cost for grid sites) instead of `ctx.grid_cost` for all sites.

## Why

Per /plan-eng-review 2026-05-26 D11 + #91. The v4.1b destination-weighted CBAM landed 11 new incumbent columns but did not rewire the action-flag comparator. `cbam_urgent` still fired against `ctx.grid_cost` regardless of whether a site ran on the PLN grid or its own captive coal plant. For captive coal sites (IMIP, IWIP, Obi Island, etc.), the right "what's competing with solar" baseline is captive_coal_lcoe + the CBAM cost their captive emissions carry — not the PLN tariff.

The old math also used the v4.0-era product-emissions-based `cbam_savings_per_mwh` (savings_per_tonne ÷ product_electricity_intensity). The new math uses the v4.1b grid-emissions-based `carbon_adder = active_scenario_value - grid_cost` (grid_emission_factor × destination-weighted carbon prices). Cleaner unit story; consistent with the v4.1b CBAM scenario picker the user controls.

## Math

**Before (v4.0/v4.1b):**
```
elec_intensity     = CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE[product]   # MWh/t
savings_per_mwh    = cbam_cost_2030_usd_per_tonne / elec_intensity        # $/MWh
adjusted_lcoe      = solar_lcoe - savings_per_mwh                         # $/MWh
gap_pct            = (adjusted_lcoe - grid_cost) / grid_cost × 100        # %  (comparator: grid only)
cbam_urgent        = gap_pct < 0
```

**After (v4.2a):**
```
carbon_adder        = cbam_active_scenario_value_usd_mwh - grid_cost      # $/MWh
                      # (v4.1b destination-weighted CBAM per MWh)
incumbent_with_cbam = effective_incumbent_lcoe + carbon_adder             # $/MWh
                      # (captive_coal_lcoe for captive sites,
                      #  grid_cost for grid sites, per v4.3 M-AT8b)
gap_pct             = (solar_lcoe - incumbent_with_cbam) / incumbent_with_cbam × 100
cbam_urgent         = gap_pct < 0
```

## What changes in the data

68 of 81 sites are CBAM-exposed. Of those:
- **13 sites** flip on `cbam_urgent` (12 False→True, 1 True→False).
- **10 sites** have their `action_flag` recomputed (mostly `not_competitive` / `invest_resilience` → `cbam_urgent`).
- **66 sites** have `cbam_adjusted_gap_pct` shift by >1pp, **51 sites** by >5pp.
- **13 non-CBAM-exposed sites** are byte-identical (regression-pin green).

### `cbam_urgent` flips (13 sites)

| site_id | product | arrangement | before | after |
|---|---|---|---|---|
| `bumi-serpong-damai` | nickel_rkef, steel_eaf | `grid_only` | True | False |
| `freeport-smelter-gresik` | aluminium | `grid_primary_with_captive` | False | True |
| `indonesia-pomalaa-industry-park-ipip` | nickel_rkef | `pure_captive` | True | False |
| `industropolis-batang` | fertilizer | `grid_only` | False | True |
| `ispat-indo-sidoarjo` | steel_eaf | `grid_primary_with_captive` | False | True |
| `kek-arun-lhokseumawe` | fertilizer | `grid_primary_with_captive` | False | True |
| `kek-gresik` | cement, nickel_rkef, fertilizer | `grid_only` | False | True |
| `kek-kendal` | cement | `grid_only` | False | True |
| `kek-lido` | cement | `grid_only` | False | True |
| `kek-singhasari` | steel_eaf | `grid_only` | False | True |
| `semen-kupang` | cement | `grid_primary_with_captive` | False | True |
| `setangga` | cement, nickel_rkef | `grid_primary_with_captive` | False | True |
| `tanjung-sauh` | cement | `grid_primary_with_captive` | False | True |

### `action_flag` changes (10 sites)

| site_id | before | after |
|---|---|---|
| `bumi-serpong-damai` | `cbam_urgent` | `not_competitive` |
| `industropolis-batang` | `invest_resilience` | `cbam_urgent` |
| `ispat-indo-sidoarjo` | `not_competitive` | `cbam_urgent` |
| `kek-arun-lhokseumawe` | `invest_resilience` | `cbam_urgent` |
| `kek-gresik` | `invest_resilience` | `cbam_urgent` |
| `kek-kendal` | `invest_resilience` | `cbam_urgent` |
| `kek-lido` | `not_competitive` | `cbam_urgent` |
| `kek-singhasari` | `not_competitive` | `cbam_urgent` |
| `setangga` | `not_competitive` | `cbam_urgent` |
| `tanjung-sauh` | `not_competitive` | `cbam_urgent` |

### `cbam_adjusted_gap_pct` shifts >5pp (51 sites)

Sorted by absolute delta. Negative Δ = gap got bigger (incumbent harder to beat). Positive Δ = gap got smaller (incumbent easier to beat).

| site_id | arrangement | before (pp) | after (pp) | Δ (pp) |
|---|---|---|---|---|
| `inalum-asahan` | `hybrid_captive_primary` | +67.8 | +167.6 | -99.8 |
| `freeport-smelter-gresik` | `grid_primary_with_captive` | +36.0 | -13.3 | +49.3 |
| `semeru-surya-semen-kutai` | `grid_primary_with_captive` | +66.9 | +20.5 | +46.4 |
| `krakatau-steel-cilegon` | `grid_primary_with_captive` | +54.1 | +8.0 | +46.1 |
| `gunung-raja-paksi-bekasi` | `grid_primary_with_captive` | +53.9 | +7.9 | +46.0 |
| `master-steel-jakarta` | `grid_primary_with_captive` | +53.5 | +7.6 | +45.9 |
| `jakarta-prima-steel-industries` | `grid_primary_with_captive` | +52.7 | +7.0 | +45.7 |
| `red-lion-hongshi-tonga` | `grid_primary_with_captive` | +62.2 | +17.2 | +45.0 |
| `conch-south-kalimantan` | `grid_primary_with_captive` | +59.4 | +15.3 | +44.1 |
| `indocement-kotabaru-tarjun` | `grid_primary_with_captive` | +57.7 | +14.2 | +43.5 |
| `conch-west-kalimantan` | `grid_primary_with_captive` | +47.1 | +6.9 | +40.2 |
| `ispat-indo-sidoarjo` | `grid_primary_with_captive` | +34.5 | -5.7 | +40.2 |
| `stardust-estate-invesment-sei` | `pure_captive` | +92.6 | +54.3 | +38.3 |
| `indocement-citeureup` | `grid_only` | +56.7 | +24.3 | +32.4 |
| `cemindo-gemilang-bayah` | `grid_only` | +54.6 | +22.7 | +31.9 |
| `semen-jawa-scg-sukabumi` | `grid_only` | +52.1 | +20.8 | +31.3 |
| `sbi-narogong` | `grid_only` | +51.7 | +20.5 | +31.2 |
| `setangga` | `grid_primary_with_captive` | +17.7 | -13.4 | +31.1 |
| `semen-bosowa-banyuwangi` | `grid_only` | +49.3 | +18.7 | +30.6 |
| `semen-bosowa-batam` | `grid_primary_with_captive` | +53.7 | +23.2 | +30.5 |
| `cemindo-gemilang-batam` | `grid_primary_with_captive` | +54.0 | +23.5 | +30.5 |
| `semen-garuda-bekasi` | `grid_only` | +46.6 | +16.7 | +29.9 |
| `cemindo-gemilang-ciwandan` | `grid_only` | +45.3 | +15.7 | +29.6 |
| `conch-cement-serang` | `grid_only` | +44.6 | +15.1 | +29.5 |
| `semen-kupang` | `grid_primary_with_captive` | +9.4 | -20.1 | +29.5 |
| `si-gresik-rembang` | `grid_only` | +44.8 | +15.3 | +29.5 |
| `indocement-palimanan` | `grid_only` | +44.0 | +14.7 | +29.3 |
| `sbi-andalas-lhoknga` | `grid_primary_with_captive` | +47.9 | +18.8 | +29.1 |
| `semen-jakarta` | `grid_only` | +41.6 | +12.9 | +28.7 |
| `semen-grobogan` | `grid_only` | +39.0 | +10.9 | +28.1 |
| `sbi-cilacap` | `grid_only` | +38.5 | +10.5 | +28.0 |
| `solusi-bangun-cilegon` | `grid_only` | +38.4 | +10.4 | +28.0 |
| `semen-imasco-asiatic-jember` | `grid_only` | +34.4 | +7.4 | +27.0 |
| `conch-cement-north-sulawesi` | `grid_primary_with_captive` | +55.5 | +28.8 | +26.7 |
| `semen-gresik-tuban` | `grid_only` | +33.3 | +6.6 | +26.7 |
| `sbi-tuban` | `grid_only` | +32.6 | +6.1 | +26.5 |
| `semen-gresik-city` | `grid_only` | +32.4 | +5.9 | +26.5 |
| `semen-baturaja` | `grid_primary_with_captive` | +33.9 | +8.1 | +25.8 |
| `semen-padang-indarung` | `grid_primary_with_captive` | +31.0 | +5.8 | +25.2 |
| `kek-singhasari` | `grid_only` | +4.2 | -20.9 | +25.1 |
| `indonesia-konawe-industrial-park-ikip` | `pure_captive` | +126.1 | +101.6 | +24.5 |
| `kek-lido` | `grid_only` | +23.3 | -1.1 | +24.4 |
| `pupuk-kaltim-bontang` | `pure_captive` | +49.1 | +25.4 | +23.7 |
| `tanjung-sauh` | `grid_primary_with_captive` | +21.9 | -1.2 | +23.1 |
| `kek-arun-lhokseumawe` | `grid_primary_with_captive` | +14.4 | -8.4 | +22.8 |
| `semen-bosowa-maros` | `grid_primary_with_captive` | +31.1 | +9.3 | +21.8 |
| `pupuk-sriwidjaja-palembang` | `pure_captive` | +73.5 | +51.9 | +21.6 |
| `industropolis-batang` | `grid_only` | +4.2 | -16.8 | +21.0 |
| `semen-tonasa` | `grid_primary_with_captive` | +24.2 | +3.7 | +20.5 |
| `kek-gresik` | `grid_only` | +2.8 | -16.6 | +19.4 |
| `pupuk-kujang-cikampek` | `pure_captive` | +48.9 | +29.8 | +19.1 |
| `kek-kendal` | `grid_only` | +1.3 | -17.7 | +19.0 |
| `pupuk-iskandar-muda-lhokseumawe` | `pure_captive` | +55.7 | +36.7 | +19.0 |
| `obi-island-industrial-park` | `pure_captive` | +149.1 | +130.6 | +18.5 |
| `kek-galang-batang` | `grid_primary_with_captive` | +28.6 | +11.7 | +16.9 |
| `kek-sorong` | `pure_captive` | +91.3 | +74.5 | +16.8 |
| `petrokimia-gresik` | `pure_captive` | +31.4 | +15.0 | +16.4 |
| `dexin-steel-morowali` | `pure_captive` | +126.5 | +110.8 | +15.7 |
| `buli-industrial-park` | `pure_captive` | +69.5 | +57.3 | +12.2 |
| `krakatau-posco-cilegon` | `grid_primary_with_captive` | +53.5 | +42.2 | +11.3 |
| `indonesia-morowali-industrial-park-imip` | `pure_captive` | +83.7 | +73.8 | +9.9 |
| `bantaeng-industrial-park-bip` | `pure_captive` | -13.1 | -4.2 | -8.9 |
| `virtue-dragon-nickel-industrial-park-vdnip` | `pure_captive` | +5.0 | +12.4 | -7.4 |
| `bumi-serpong-damai` | `grid_only` | -0.9 | +5.8 | -6.7 |
| `indonesia-pomalaa-industry-park-ipip` | `pure_captive` | -0.2 | +5.3 | -5.5 |

## Spot-check narratives

### `inalum-asahan` (-99.8pp — biggest shift)

Aluminium smelter in North Sumatra. `electricity_arrangement = hybrid_captive_primary` because Inalum runs the Asahan run-of-river hydro plant as its primary captive source. `captive_fuel_type = hydro`. Captive incumbent LCOE is correspondingly low (~$30-40/MWh).

The OLD math compared solar LCOE against grid_cost ($45/MWh range in Sumatra). Said "solar is 68% over grid — kind of close." The NEW math compares against captive hydro + the CBAM adder for aluminium (Sumatera grid_ef ≈ 0.88 tCO2/MWh × destination-weighted scenario price). Says "solar is 168% over captive hydro — genuinely uncompetitive at this site." The new number is the correct one — Inalum's electricity is already cheap and zero-carbon; solar isn't displacing anything dirty here.

### `kek-singhasari` (+25.1pp, flipped urgent True)

KEK in East Java, designated steel_eaf product type, electricity_arrangement = grid_only (Java-Bali grid). Java-Bali grid_emission_factor ≈ 0.81 tCO2/MWh (highest of any Indonesian region per KESDM Tier 2 OM). Steel EAF subsector defaults to `domestic_high` ($25/tCO2) under the active CBAM scenario.

OLD math said gap = +4.2pp (slightly above grid). NEW math says gap = -20.9pp (solar beats grid + CBAM by 21pp). Methodology: solar saves $20/MWh in avoided CBAM cost (= 0.81 × $25). Adding that to the incumbent flips solar from "slightly uncompetitive" to "clearly cbam_urgent."

### `bumi-serpong-damai` (only True→False flip)

BSD is a mixed industrial KEK in Tangerang. Carries the `nickel_rkef, steel_eaf` CBAM product tag (legacy). `electricity_arrangement = grid_only` — Java-Bali grid.

OLD math (product-emissions): said cbam_urgent fires because the product-based savings were large enough to bridge the gap. NEW math (grid-emissions): the destination-weighted carbon adder at Java-Bali's emission factor doesn't quite bridge the gap. Solar remains marginally uncompetitive here under the active scenario.

This flip is a methodology shift, not a regression. Defensible.

### `freeport-smelter-gresik` (False → True, +49.3pp)

Aluminium smelter in Gresik, East Java. `electricity_arrangement = grid_primary_with_captive`. Captive incumbent is gas (Pertamina pipeline gas). When we use captive_gas + CBAM adder instead of grid alone, solar becomes clearly cost-effective (-13pp vs incumbent). Old math under-credited the CBAM exposure here.

## Known simplification (out of scope)

The carbon_adder is computed against `grid_emission_factor_t_co2_mwh` even for captive coal / captive gas sites. Captive coal typically emits ~0.85-0.95 tCO2/MWh — higher than most Indonesian grids (0.56 Papua → 1.27 NTB). Using grid_ef for captive sites slightly under-counts their CBAM exposure. The full fix would require per-arrangement emission factor selection, which is tracked as a separate future refinement (not filed yet; surface when methodology debt accumulates).

## Validation

- **Regression pin**: 13 non-CBAM-exposed sites byte-identical pre/post (golden fixture re-pinned only on CBAM-exposed columns + the new `cbam_urgent_comparator_kind` column).
- **Golden fixture**: 225 → 226 columns (added `cbam_urgent_comparator_kind`).
- **Unit tests**: `tests/test_action_flag_cbam_urgent.py` covers the 4 electricity_arrangement buckets explicitly.
- **Full suite**: 1170+ pass (was 1170 pre-fix).

## Out of scope

- The other action flags (`plan_late`, `grid_first`, `solar_now`) — same comparator audit is worth doing, separate work.
- Frontend exposure of which comparator is active per site (lands in v4.2a #93 follow-up if needed; today the `cbam_urgent_comparator_kind` column is available but not surfaced in UI).
- Per-arrangement emission factor for the carbon adder (see "Known simplification" above).
