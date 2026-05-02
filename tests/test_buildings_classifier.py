"""Tests for `src/model/buildings.py` — §14 geometric classifier + §5.3
footprint→MWp math.

The §14 classifier maps each building polygon to one of 7 categories
(too_small, tank_silo, conveyor, complex, possibly_round, elongated,
standard_roof) with a usability multiplier (0.0–1.0). These tests use
synthetic shapely polygons whose geometry is trivially verifiable so
we can lock the cascade ordering and threshold behavior.

The §5.3 power math (rooftop_kw_dc / rooftop_kw_ac) is small but
load-bearing — these tests pin the formula coefficients so a future
slider implementation (RV15) can't silently drift from spec.
"""

from __future__ import annotations

import math

import pytest
from shapely.geometry import Point, Polygon, box

from src.model.buildings import (
    classify_building,
    panel_density_w_per_m2,
    rooftop_kw_ac,
    rooftop_kw_dc,
)

# ─── classify_building ─────────────────────────────────────────────────────


def test_classifier_too_small_below_min_area():
    """Below BUILDING_MIN_AREA_M2 (default 200 m²) → too_small, multiplier 0."""
    tiny = box(0, 0, 5, 5)  # 25 m²
    out = classify_building(tiny, area_m2=tiny.area)
    assert out.category == "too_small"
    assert out.usability_multiplier == 0.0


def test_classifier_empty_polygon_is_too_small():
    """Empty geometry shouldn't crash — fall through to too_small."""
    empty = Polygon()
    out = classify_building(empty, area_m2=0.0)
    assert out.category == "too_small"


def test_classifier_circle_is_tank_silo():
    """A near-circular polygon (high circularity) → tank_silo, multiplier 0.

    Tanks are flat tops without rooftop panel access. RV-tank-fix (OSM
    exclusion layer) catches what the classifier misses.
    """
    # Buffer a point to get a near-circle. 64 segments → circularity ~0.99.
    circle = Point(0, 0).buffer(20, quad_segs=16)
    out = classify_building(circle, area_m2=circle.area)
    assert out.category == "tank_silo"
    assert out.usability_multiplier == 0.0
    assert out.circularity > 0.9


def test_classifier_long_thin_is_conveyor():
    """Aspect ratio above the conveyor threshold (default 15) → multiplier 0.1."""
    thin = box(0, 0, 200, 5)  # 1000 m², aspect 40:1
    out = classify_building(thin, area_m2=thin.area)
    assert out.category == "conveyor"
    assert out.usability_multiplier == 0.1
    assert out.aspect_ratio >= 15


def test_classifier_l_shape_is_complex():
    """Concave polygon (low hull_ratio) → complex, multiplier 0.2.

    Real example: an L-shaped factory floorplan with a thin arm. Convex
    hull is the bounding box → polygon area / hull area drops below 0.55.
    """
    # 40x40 bounding box, ~375 m² actual area → hull ratio ~0.23
    l_shape = Polygon([(0, 0), (40, 0), (40, 5), (5, 5), (5, 40), (0, 40)])
    out = classify_building(l_shape, area_m2=l_shape.area)
    assert out.category == "complex"
    assert out.usability_multiplier == 0.2
    assert out.hull_ratio < 0.55


def test_classifier_elongated_warehouse():
    """Aspect ratio between 4-15 (default soft elongated threshold) →
    elongated, multiplier 0.6. Real warehouses + halls land here."""
    hall = box(0, 0, 100, 12)  # ~8.3:1 aspect
    out = classify_building(hall, area_m2=hall.area)
    assert out.category == "elongated"
    assert out.usability_multiplier == 0.6


def test_classifier_standard_roof():
    """A modestly-elongated rectangular industrial roof → standard_roof,
    multiplier 1.0. Aspect ~3-4 gives circularity below the soft-round
    threshold without crossing into elongated territory."""
    standard = box(0, 0, 30, 8)  # 240 m², aspect 3.75 — squarely standard
    out = classify_building(standard, area_m2=standard.area)
    assert out.category == "standard_roof"
    assert out.usability_multiplier == 1.0


def test_classifier_threshold_overrides_propagate():
    """Threshold args override defaults — proves test/F10 hooks work
    without monkeypatching assumptions.py."""
    rect = box(0, 0, 60, 10)  # 600 m², aspect 6:1 — normally elongated
    out_strict = classify_building(rect, area_m2=rect.area, aspect_conveyor_threshold=4.0)
    assert out_strict.category == "conveyor"  # we just made it qualify as conveyor
    out_lenient = classify_building(rect, area_m2=rect.area, aspect_conveyor_threshold=20.0)
    assert out_lenient.category == "elongated"


def test_classifier_cascade_order_tank_beats_conveyor():
    """Hard rejects (tank) precede soft rejects in the cascade. Even an
    elongated near-circle should resolve to tank_silo (the rejection
    that fires first wins)."""
    circle = Point(0, 0).buffer(20, quad_segs=16)
    out = classify_building(circle, area_m2=circle.area)
    assert out.category == "tank_silo"  # tank check beats anything else


# ─── §5.3 footprint→MWp math ──────────────────────────────────────────────


def test_panel_density_default():
    """200 W/m² panel density: 400 W ÷ 2.0 m² = 200 W/m²."""
    assert panel_density_w_per_m2() == pytest.approx(200.0, abs=0.1)


def test_panel_density_zero_area_safe():
    """Zero panel area → 0.0, no DivisionByZero."""
    assert panel_density_w_per_m2(panel_area_m2=0.0) == 0.0


def test_rooftop_kw_dc_zero_footprint_safe():
    assert rooftop_kw_dc(0.0, 1.0) == 0.0


def test_rooftop_kw_dc_zero_multiplier_safe():
    """Tank/too_small categories have multiplier=0 → 0 kW DC regardless of footprint."""
    assert rooftop_kw_dc(1000.0, 0.0) == 0.0


def test_rooftop_kw_dc_known_value():
    """1000 m² × 1.0 multiplier × 0.5 layout × 200 W/m² ÷ 1000 = 100 kW DC.
    Locks the formula coefficients."""
    kw = rooftop_kw_dc(
        footprint_m2=1000.0,
        usability_multiplier=1.0,
        layout_density=0.5,
        panel_power_w_dc=400.0,
        panel_area_m2=2.0,
    )
    assert kw == pytest.approx(100.0, abs=0.1)


def test_rooftop_kw_dc_multiplier_scales_linearly():
    """Halving the multiplier halves the kW. Pins the linear application."""
    full = rooftop_kw_dc(1000.0, 1.0)
    half = rooftop_kw_dc(1000.0, 0.5)
    assert half == pytest.approx(full / 2, abs=0.01)


def test_rooftop_kw_ac_thermal_derate():
    """100 kW DC × 0.88 tropical derate = 88 kW AC."""
    assert rooftop_kw_ac(100.0) == pytest.approx(88.0, abs=0.01)


def test_rooftop_kw_ac_custom_derate():
    """Derate parameter is respected."""
    assert rooftop_kw_ac(100.0, thermal_derate=0.95) == pytest.approx(95.0, abs=0.01)


def test_rooftop_kw_ac_zero_dc():
    assert rooftop_kw_ac(0.0) == 0.0


# ─── Numerical sanity ──────────────────────────────────────────────────────


def test_circularity_perfect_square():
    """A 20x20 square (above min-area threshold) has circularity = π / 4 ≈ 0.785
    — known constant. Asserting this pins the formula."""
    square = box(0, 0, 20, 20)  # 400 m², above MIN_AREA
    out = classify_building(square, area_m2=square.area)
    expected = math.pi / 4
    assert out.circularity == pytest.approx(expected, abs=0.01)
