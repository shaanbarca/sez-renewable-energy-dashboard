"""Canonical column-name constants for pandas DataFrames flowing through the
pipeline + dash logic.

# Why this exists

Pandas joins on string keys. If you rename a column and miss one reference,
`df.merge(other, on="site_id")` joins against a column that doesn't exist in
one table — pandas returns all NaN for the unmatched columns, no error. The
scorecard renders, the map loads, the numbers are silently wrong. Worst class
of bug.

`Col` wraps each column name as a class attribute. Instead of
`df["regional_groundmount_potential_mwp_50km"]`, write
`df[Col.REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM]`. To rename the column, change
ONE attribute value here. Every reader updates by re-importing.

IDE "Find All References" works on the attribute. Linters catch typos in the
attribute name. The string only lives in one place.

# Adoption status

This module is being adopted **incrementally** per TODOS.md M23. Today's scope:

1. Phase 0 rename PR (2026-04-25, this PR): introduces `Col` with the renamed
   column. Files updated to use `Col` for that one column:
   - `src/pipeline/build_fct_site_resource.py` (write site)
   - `src/pipeline/build_fct_lcoe.py`, `build_fct_site_scorecard.py`,
     `build_fct_substation_proximity.py` (reads)
   - `src/dash/logic/grid.py`, `lcoe.py`, `site_context.py` (reads)
   - `src/api/routes/scorecard.py`, `layers.py` (reads + alias)

2. Future PRs should migrate **all** column references in any file they touch
   for other reasons. Add the new column constants here as you go. Don't try
   to migrate the whole codebase at once.

3. Frontend (TypeScript) stays as-is — `frontend/src/lib/types.ts` already
   gives compile-time column safety via the `ScorecardRow` interface.

# Conventions

- Constant name: SCREAMING_SNAKE_CASE matching the column string.
- Constant value: the exact column string used in DataFrames.
- Group constants by table of origin (`fct_site_resource`, `fct_lcoe`, etc.)
  so adding a column near related ones is mechanical.
"""

from __future__ import annotations


class Col:
    """Canonical column names. Use `df[Col.X]` instead of `df["x"]`."""

    # ─── fct_site_resource ──────────────────────────────────────────────────
    # Per-site solar resource + buildability metrics. Written by
    # `src/pipeline/build_fct_site_resource.py`.

    # Renamed 2026-04-25 (Phase 0 of v4.1 rooftop solar work) from
    # `max_captive_capacity_mwp`. Old name suggested on-site capacity but the
    # number is actually the upper bound on ground-mount within 50 km of the
    # site centroid (regional, not captive). See
    # `docs/rooftop_solar_potential_feature_spec.md` §3.1 F5.
    REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM = "regional_groundmount_potential_mwp_50km"
