"""Tests for `compute_confidence_flag` and its mapping helpers
(`_human_readable_reason`, `_recommended_alt_data`).

The F4 confidence flag is the data-trust signal users see in the rooftop
drawer ("how reliable is this MWp number?"). It has 6 distinct cascade
branches, each firing on a different signal:

  1. zero buildings              → low / no_buildings_detected
  2. tourism KEK                  → low / tourism_kek
  3. site commissioned post-vintage → low / post_2023_imagery
  4. major facility, low count    → low / low_count_for_capacity
  5. large site, tiny footprint   → low / polygon_imagery_gap
  6. healthy count + ratio        → high / None
  ELSE                            → medium / None

Cascade order matters — branch (1) wins over (2) wins over (3) etc.
These tests pin each branch with synthetic inputs and verify the cascade
ordering. Until now the function was exercised only end-to-end via the
build pipeline, which made silent regressions easy.
"""

from __future__ import annotations

import pytest

from src.pipeline.build_fct_site_solar_potential import (
    _human_readable_reason,
    _recommended_alt_data,
    compute_confidence_flag,
)

# ─── compute_confidence_flag — cascade branches ──────────────────────────


def test_zero_buildings_is_low_no_buildings_detected():
    """Branch 1: zero buildings always wins regardless of other signals.

    A tourism KEK with 0 buildings still surfaces as no_buildings_detected
    because branch 1 fires before branch 2."""
    confidence, reason = compute_confidence_flag(
        building_count=0,
        total_footprint_m2=0.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=None,
        site_commissioning_year=None,
        site_zone_classification="tourism",
        source_vintage="2023-05",
    )
    assert confidence == "low"
    assert reason == "no_buildings_detected"


def test_tourism_kek_is_low_tourism_kek():
    """Branch 2: tourism KEK with buildings → low/tourism_kek (expected)."""
    confidence, reason = compute_confidence_flag(
        building_count=50,
        total_footprint_m2=10_000.0,
        site_polygon_area_ha=200.0,
        site_capacity_tonnes=None,
        site_commissioning_year=2018,
        site_zone_classification="Tourism",  # case-insensitive
        source_vintage="2023-05",
    )
    assert confidence == "low"
    assert reason == "tourism_kek"


def test_post_vintage_commissioning_is_low_post_2023_imagery():
    """Branch 3: site commissioned in 2024 (after May 2023 imagery) → low.

    This is the Hongshi pattern — plant exists physically, GoB/MS imagery
    predates it. The fix path is imagery refresh, not a pipeline bug."""
    confidence, reason = compute_confidence_flag(
        building_count=20,
        total_footprint_m2=50_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=4_000_000,
        site_commissioning_year=2024,
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert confidence == "low"
    assert reason == "post_2023_imagery"


def test_major_facility_low_count_is_low_count_for_capacity():
    """Branch 4: 4 Mt/yr capacity but only 2 buildings detected → likely
    undercount. Catches Cemindo Bayah pattern (operating plant, GoB
    sees nothing)."""
    confidence, reason = compute_confidence_flag(
        building_count=2,  # below BUILDING_COUNT_LOW_CONFIDENCE_MAX (3)
        total_footprint_m2=2_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=4_000_000,  # well above 100 ktpa threshold
        site_commissioning_year=2018,  # pre-vintage, so branch 3 doesn't fire
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert confidence == "low"
    assert reason == "low_count_for_capacity"


def test_large_polygon_tiny_footprint_is_polygon_imagery_gap():
    """Branch 5: 1000 ha site, 50,000 m² of buildings = 0.5% ratio,
    well below 1% imagery-gap threshold. Catches polygon-mapped sites
    where imagery missed the buildings."""
    confidence, reason = compute_confidence_flag(
        building_count=20,  # not low_count for capacity
        total_footprint_m2=50_000.0,
        site_polygon_area_ha=1_000.0,  # > 500 ha large-site threshold
        site_capacity_tonnes=50_000,  # below major-facility threshold
        site_commissioning_year=2018,
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert confidence == "low"
    assert reason == "polygon_imagery_gap"


def test_healthy_count_and_ratio_is_high():
    """Branch 6: 50 buildings + 8% footprint ratio in a 100 ha site
    → high confidence. The "looks like a real industrial site" case."""
    confidence, reason = compute_confidence_flag(
        building_count=50,  # >= BUILDING_COUNT_HIGH_CONFIDENCE_MIN (10)
        total_footprint_m2=80_000.0,  # 8% of 100 ha → in [5%, 40%] band
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=200_000,
        site_commissioning_year=2018,
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert confidence == "high"
    assert reason is None


def test_default_falls_to_medium():
    """When no specific branch fires, default to medium (not high, not low).

    Realistic case: 5 buildings (above zero, below high threshold) at a
    moderate-capacity facility with no polygon — neither low nor high."""
    confidence, reason = compute_confidence_flag(
        building_count=5,  # above 0 (branch 1), below 10 (branch 6 high)
        total_footprint_m2=2_000.0,
        site_polygon_area_ha=None,  # branch 5 needs polygon
        site_capacity_tonnes=50_000,  # below major-facility threshold
        site_commissioning_year=2018,
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert confidence == "medium"
    assert reason is None


# ─── Cascade ordering — earlier branch wins ─────────────────────────────


def test_zero_buildings_wins_over_tourism():
    """Branch 1 (zero buildings) fires before branch 2 (tourism)."""
    _, reason = compute_confidence_flag(
        building_count=0,
        total_footprint_m2=0.0,
        site_polygon_area_ha=200.0,
        site_capacity_tonnes=None,
        site_commissioning_year=None,
        site_zone_classification="Tourism",
        source_vintage="2023-05",
    )
    assert reason == "no_buildings_detected"


def test_tourism_wins_over_post_vintage():
    """Branch 2 (tourism) fires before branch 3 (post-vintage commissioning).

    A tourism KEK commissioned in 2024 should still surface as
    tourism_kek — that's the more useful signal for the persona."""
    _, reason = compute_confidence_flag(
        building_count=10,
        total_footprint_m2=5_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=None,
        site_commissioning_year=2024,  # would trigger branch 3
        site_zone_classification="Tourism",  # but branch 2 fires first
        source_vintage="2023-05",
    )
    assert reason == "tourism_kek"


def test_post_vintage_wins_over_major_facility():
    """Branch 3 fires before branch 4 — both signal undercount but the
    post-vintage reason is more specific (the fix path differs)."""
    _, reason = compute_confidence_flag(
        building_count=2,  # would trigger branch 4
        total_footprint_m2=1_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=4_000_000,  # major facility
        site_commissioning_year=2024,  # but post-vintage fires first
        site_zone_classification="Industrial",
        source_vintage="2023-05",
    )
    assert reason == "post_2023_imagery"


# ─── Vintage parsing (invariant #6) ──────────────────────────────────────


def test_invariant_6_per_row_vintage():
    """The vintage cutoff is per-row (from source_vintage), not a global
    constant. A site commissioned in 2025 with a 2026-vintage source
    should NOT trigger post_2023_imagery."""
    confidence, reason = compute_confidence_flag(
        building_count=20,
        total_footprint_m2=50_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=200_000,
        site_commissioning_year=2025,
        site_zone_classification="Industrial",
        source_vintage="2026-01",  # newer vintage covers 2025 build
    )
    # Should NOT fire post_2023_imagery (the source already saw it).
    assert reason != "post_2023_imagery"


def test_malformed_vintage_falls_back_to_default_cutoff():
    """If source_vintage doesn't parse (None, garbage, missing dash),
    fall back to BUILDING_DATA_VINTAGE_YEAR_CUTOFF (2023). Defensive
    against pre-v4.2 data without source_vintage column."""
    confidence, reason = compute_confidence_flag(
        building_count=20,
        total_footprint_m2=50_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=200_000,
        site_commissioning_year=2024,  # post-default-cutoff
        site_zone_classification="Industrial",
        source_vintage="not-a-date",  # unparseable
    )
    assert reason == "post_2023_imagery"


def test_null_vintage_uses_default_cutoff():
    """source_vintage=None → use BUILDING_DATA_VINTAGE_YEAR_CUTOFF."""
    confidence, reason = compute_confidence_flag(
        building_count=20,
        total_footprint_m2=50_000.0,
        site_polygon_area_ha=100.0,
        site_capacity_tonnes=200_000,
        site_commissioning_year=2024,
        site_zone_classification="Industrial",
        source_vintage=None,
    )
    assert reason == "post_2023_imagery"


# ─── Helper mappers ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "reason,expected_substring",
    [
        ("post_2023_imagery", "predates"),
        ("low_count_for_capacity", "below threshold"),
        ("polygon_imagery_gap", "Imagery gap"),
        ("tourism_kek", "tourism"),
        ("no_buildings_detected", "No buildings"),
    ],
)
def test_human_readable_reason_each_branch(reason, expected_substring):
    out = _human_readable_reason(reason)
    assert expected_substring.lower() in out.lower()


def test_human_readable_reason_unknown_passthrough():
    """Unknown reason strings pass through unchanged (defensive)."""
    assert _human_readable_reason("brand_new_reason") == "brand_new_reason"


def test_recommended_alt_data_tourism_no_alt_needed():
    """Tourism KEKs have minimal rooftop potential — no alt-data hunt
    is warranted."""
    assert _recommended_alt_data("tourism_kek", "tourism") == "no_alt_data_needed"
    # Even if reason is something else, sector="tourism" wins.
    assert _recommended_alt_data("post_2023_imagery", "tourism") == "no_alt_data_needed"


def test_recommended_alt_data_post_vintage_recommends_ms_gmlbf():
    """post_2023_imagery → MS GMLBF (different vintage)."""
    assert _recommended_alt_data("post_2023_imagery", "cement") == "microsoft_gmlbf"


def test_recommended_alt_data_no_buildings_recommends_ms_gmlbf():
    """no_buildings_detected → MS GMLBF (different model, different blind spots)."""
    assert _recommended_alt_data("no_buildings_detected", "steel") == "microsoft_gmlbf"


def test_recommended_alt_data_polygon_gap_or_low_count_recommends_manual():
    """Polygon gaps and low counts on major facilities — manual KML
    trace from satellite imagery is the right alt-data path."""
    assert _recommended_alt_data("polygon_imagery_gap", "cement") == "manual_kml"
    assert _recommended_alt_data("low_count_for_capacity", "steel") == "manual_kml"


def test_recommended_alt_data_unknown_falls_to_manual():
    """Defensive default: unknown reason → manual_kml (always achievable)."""
    assert _recommended_alt_data("brand_new_reason", "cement") == "manual_kml"
