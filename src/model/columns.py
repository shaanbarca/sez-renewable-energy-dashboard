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

    # ─── fct_site_solar_potential (NEW in v4.1 — rooftop solar work) ────────
    # Per-site rooftop + within-site ground potential metrics. Written by
    # `src/pipeline/build_fct_site_solar_potential.py` (planned). See
    # `docs/rooftop_solar_potential_feature_spec.md` §3.1 + §6.

    # Total rooftop solar potential (MWp) after §14 geometric classifier
    # filters out tanks, silos, conveyors, too-small structures, and complex
    # process equipment. The headline rooftop number.
    ROOFTOP_SOLAR_MWP_POTENTIAL = "rooftop_solar_mwp_potential"

    # Buildable ground-mount area within the site polygon boundary (ha),
    # after subtracting building footprints AND applying the existing 5-layer
    # buildability mask (kawasan hutan, peatland, land cover, road proximity,
    # slope/elevation).
    WITHIN_SITE_GROUNDMOUNT_AREA_HA = "within_site_groundmount_area_ha"

    # Within-site ground-mount capacity = within_site_groundmount_area_ha /
    # HA_PER_MWP. Distinct from REGIONAL_GROUNDMOUNT_POTENTIAL_MWP_50KM in
    # that this is INSIDE the site fence, not the 50 km region.
    WITHIN_SITE_GROUNDMOUNT_MWP = "within_site_groundmount_mwp"

    # Sum of detected building footprint area inside the site polygon (m²),
    # before any §14 type filtering. For audit / cross-check via map overlay.
    TOTAL_BUILDING_FOOTPRINT_M2 = "total_building_footprint_m2"

    # Usable rooftop area after §14 classifier × ROOFTOP_USABLE_SHARE (m²).
    # Drives the rooftop MWp calculation:
    #   rooftop_mwp = usable_roof_area_m2 × ROOFTOP_W_PER_M2 ×
    #                 THERMAL_DERATE_TROPICAL / 1_000_000
    USABLE_ROOF_AREA_M2 = "usable_roof_area_m2"

    # Total area filtered out by §14 type classifier (m²). For UI tooltip:
    # "We detected 240,000 m² of footprint; 85,000 m² classified as
    # tanks/silos/non-rooftop, excluded."
    TYPE_FILTER_EXCLUDED_M2 = "type_filter_excluded_m2"

    # Per-classification building counts. Sum to `building_count_total`.
    # See §14.3 for category definitions.
    BUILDING_COUNT_TOTAL = "building_count_total"
    BUILDING_COUNT_STANDARD_ROOF = "building_count_standard_roof"
    BUILDING_COUNT_ELONGATED = "building_count_elongated"
    BUILDING_COUNT_TANK_SILO = "building_count_tank_silo"
    BUILDING_COUNT_CONVEYOR = "building_count_conveyor"
    BUILDING_COUNT_OTHER_EXCLUDED = "building_count_other_excluded"

    # Per-site data confidence: `high` | `medium` | `low`. Derived from F4
    # signals (building density, polygon area ratio, imagery vintage). NEVER
    # from a hard-coded site list — always pipeline-derived.
    BUILDING_DATA_CONFIDENCE = "building_data_confidence"

    # Static metadata string for UI tooltips. See
    # `assumptions.BUILDING_DATA_VINTAGE`. Same value for every row in v4.1
    # (single dataset). Becomes per-row when we mix sources in v4.2.
    BUILDING_DATA_VINTAGE = "building_data_vintage"
