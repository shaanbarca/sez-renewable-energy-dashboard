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
| Fertilizer | Residual manual (this CSV); universe verified via `fertilizer_universe_v1.csv` (M26 closed 2026-04-18) | 5 |
| Ammonia | Pending — see TODOS M28 (top-down universe discovery) | 0 |
| Petrochemical | Pending — see TODOS M29 (top-down universe discovery) | 0 |
| **Total industrial sites** |  | **56** |

Combined with 25 KEKs via `build_dim_sites`, the unified dim table has
**81 sites** (25 kek + 46 standalone + 10 cluster).

### Fertilizer universe (M26 closed)

All 5 operating Pupuk Indonesia Group subsidiaries are now in-scope:

| Site | Province | Product |
|------|----------|---------|
| Pupuk Kaltim Bontang | East Kalimantan | Urea + ammonia |
| Pusri Palembang | South Sumatra | Urea + ammonia |
| Petrokimia Gresik | East Java | Urea + NPK + phosphate |
| Pupuk Kujang Cikampek | West Java | Urea + ammonia |
| Pupuk Iskandar Muda Lhokseumawe | Aceh | Urea + ammonia |

Candidates evaluated but not added (see `fertilizer_universe_v1.csv` for the
full 4-source discovery record): **Pupuk Fakfak (West Papua)** is
under-construction (target 2028) and stays out until it comes online; **PT
Multi Nitrotama Kimia (Cikampek)** produces ammonium nitrate only, which sits
outside CBAM Annex I so it adds electricity demand signal but zero CBAM value.

> Why no hand-picked ammonia or petrochemical rows? Picking sites from news
> coverage doesn't guarantee completeness — the fertilizer expansion (M26)
> itself caught 2 missing Pupuk subsidiaries that had been skipped in the
> original hand-curation. The plan in TODOS M28/M29 is to derive the
> ammonia/petrochemical universe from the intersection of (a) state holding
> company subsidiaries (Pupuk Indonesia, Pertamina), (b) industry association
> rosters (APPI, INAPLAS), (c) government filings (MEMR gas allocation
> letters, BKPM KBLI 20114/20231), and (d) BPS Direktori Industri + UN
> Comtrade producer lists — the same 4-source gate that validated fertilizer.

## Adding a new tracker

When a tracker is added for a new sector, its rows must be removed from this
CSV and generated inside `build_industrial_sites` via a new `_build_<sector>_rows()`
helper. See:

- `_build_cement_rows()` — simple country filter
- `_build_steel_rows()` — country + status filter
- `_build_nickel_rows()` — country + IIA filter + spatial KEK exclusion +
  proximity-based capacity aggregation from child Processing rows

Open tracker integration items: see `TODOS.md` row M25 (aluminium GAST).
M26 (fertilizer) was closed 2026-04-18 by running the 4-source
universe-discovery gate and adding the 2 missing Pupuk subsidiaries.

## `manual_polygon_overrides.geojson` — hand-drawn fence boundaries

A separate file in this directory, written by the in-dashboard polygon editor
(#31). It overrides the auto-generated fence-line polygon for any site whose
KEK / OSM / Claude-traced polygon is wrong, too tight, too loose, or missing
entirely.

The override file is the **highest-trust** source per
`src/model/polygon_provenance.py` — a site with an entry here reports
`polygon_source_tier = "manual_override"`, supersedes every auto-generated
source, and shows up with an `M` badge on the map when admin mode is on.

### When to override

| Symptom | Fix |
|---|---|
| Auto polygon cuts off active facility (too tight) | Re-draw to include the missing area |
| Auto polygon includes unrelated land (too loose) | Re-draw to exclude the bleed |
| Site shows `polygon_source_tier = "none"` (2 km buffer fallback) | Draw the real fence; promotes to `manual_override` |
| OSM polygon is misaligned with satellite imagery | Re-draw against the imagery |

If the auto polygon is roughly correct, leave it alone — the override is for
real corrections, not aesthetic preference.

### Workflow

```bash
# 1. Start the dashboard with admin tooling enabled
EEZ_ENABLE_ADMIN_TOOLS=1 uv run uvicorn src.api.main:app --port 8000

# Terminal 2
cd frontend && npm run dev
```

```
2. Open http://localhost:5173
3. Click any site marker — the Score Drawer opens
4. Click "✎ Draw fence polygon" near the top of the drawer
5. Map enters edit mode (orange crosshair cursor)
6. Click to add vertices around the facility on the satellite layer
7. Live area readout in ha shows in the bottom-right panel
8. Click "Save" — polygon is written to manual_polygon_overrides.geojson
9. The pipeline picks it up on next run (no rebuild needed for the
   override file itself; runs that read polygons see the new value
   immediately)
```

If the site already has an override, the button label flips to
**"✎ Edit fence polygon (override exists — will replace)"** so the operator
knows they're about to overwrite. The previous version is preserved in git
history.

### Committing overrides

After saving in the dashboard, the file mutates in your working tree. Treat
it like any other source change:

```bash
git status               # confirm only manual_polygon_overrides.geojson changed
git diff data/industrial_sites/manual_polygon_overrides.geojson  # review
git add data/industrial_sites/manual_polygon_overrides.geojson
git commit -m "data: manual fence polygon for <site_id>"
git push                 # to private (Render deploy) and origin (public mirror)
```

Features are sorted by `site_id` by `_safe_write` so diffs are clean and
review-friendly. The `.lock` file in the same directory is gitignored — it's
a flock target produced during writes, never content.

### Security model

The editor is gated by `EEZ_ENABLE_ADMIN_TOOLS=1` (env var, defaults to
unset) AND a localhost-only dependency on the admin router. Production
(Render) leaves the env var unset, so `/api/admin/polygons/*` returns 404
and the dashboard's admin button never renders. On a local machine the
localhost check additionally rejects cross-origin JS — if a malicious page
tries to fire a save while admin is enabled, it gets 403.

This is single-author tooling. No auth beyond the env flag. If you can set
the env var, you have local file-write access anyway.

### Resetting an override

```bash
# Drop one site's override (admin must be enabled)
curl -X DELETE http://localhost:8000/api/admin/polygons/<site_id>

# Or hand-edit manual_polygon_overrides.geojson and remove the Feature
# block — same effect.
```

After delete, the site reverts to its auto-generated polygon on next
pipeline run.
