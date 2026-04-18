# Industrial sites — residual manual input

`priority1_sites.csv` holds **residual manual rows** for sectors where no
automated tracker step exists yet. It is consumed by
`src/pipeline/build_industrial_sites.py`, which unions these rows with
tracker-driven rows and emits
`outputs/data/processed/industrial_sites_generated.csv`.

## Reproducibility rule

Analytical inputs (which sites are in scope, what sector they are, what CBAM
product they produce) must be derived programmatically from public tracker
data wherever possible. This CSV is the **fallback** for sectors without a
tracker step — not a place to hand-edit site selection.

## Provenance columns (required)

Every row in `priority1_sites.csv` must populate:

| Column | Purpose |
|---|---|
| `source_name` | Human-readable source, e.g. "PT Inalum company profile" |
| `source_url` | Stable URL where the row's facts can be verified |
| `retrieved_date` | ISO date the URL was last confirmed |

`_load_residual_manual_rows()` in `build_industrial_sites.py` raises at
pipeline-build time if any row is missing `source_url`. This enforces the
reproducibility rule at the loader boundary, not in code review.

## Current state (2026-04-18)

| Sector | Source | Count |
|---|---|---|
| Cement | GEM Global Cement Plant Tracker (automated via `_build_cement_rows`, `status == "operating"`) | 32 |
| Steel | GEM Global Iron and Steel Plant Tracker (automated via `_build_steel_rows`, `status == "Active"`) | 7 |
| Nickel | CGSP Nickel Tracker IIA filter + KEK exclusion + 20km child aggregation (automated via `_build_nickel_rows`) | 10 |
| Aluminium | Residual manual (this CSV) | 2 |
| Fertilizer | Residual manual (this CSV) | 3 |
| Ammonia | Pending — see TODOS M28 (top-down universe discovery) | 0 |
| Petrochemical | Pending — see TODOS M29 (top-down universe discovery) | 0 |
| **Total industrial sites** |  | **54** |

Combined with 25 KEKs via `build_dim_sites`, the unified dim table has
**79 sites** (25 kek + 44 standalone + 10 cluster).

> Why no hand-picked ammonia or petrochemical rows? Picking sites from news
> coverage doesn't guarantee completeness — Pupuk Kaltim Bontang is Indonesia's
> largest ammonia producer (~3.4 Mt/yr) but is easy to miss without a
> systematic source. The plan in TODOS M28/M29 is to derive the universe from
> the intersection of (a) state holding company subsidiaries (Pupuk Indonesia,
> Pertamina), (b) industry association rosters (APPI, INAPLAS), (c) government
> filings (MEMR gas allocation letters, BKPM KBLI 20114/20231), and (d) BPS
> Direktori Industri + UN Comtrade producer lists.

## Adding a new tracker

When a tracker is added for a new sector, its rows must be removed from this
CSV and generated inside `build_industrial_sites` via a new `_build_<sector>_rows()`
helper. See:

- `_build_cement_rows()` — simple country filter
- `_build_steel_rows()` — country + status filter
- `_build_nickel_rows()` — country + IIA filter + spatial KEK exclusion +
  proximity-based capacity aggregation from child Processing rows

Open tracker integration items: see `TODOS.md` rows M25 (aluminium GAST) and
M26 (fertilizer).
