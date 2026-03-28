"""
Tests for src/pipeline/buildability_filters.py

All tests use synthetic numpy arrays — no real geospatial data required.
This follows the plan's architecture decision: filter functions are pure functions
that accept arrays, enabling unit tests without the buildability data files.
"""

from __future__ import annotations

import math

import numpy as np

from src.pipeline.buildability_filters import (
    MAX_ELEV_M,
    MAX_SLOPE_DEG,
    VALID_CONSTRAINTS,
    apply_exclusion_mask,
    apply_min_area_filter,
    apply_slope_elevation_mask,
    compute_buildability_constraint,
    compute_slope_degrees,
)

# ── apply_exclusion_mask ──────────────────────────────────────────────────────

class TestApplyExclusionMask:
    def test_forest_pixels_zeroed(self):
        """Pixels where mask == 1 (excluded) should become 0.0."""
        pvout = np.array([[5.0, 5.0], [5.0, 5.0]])
        mask  = np.array([[1, 0], [0, 1]], dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0

    def test_buildable_pixels_retained(self):
        """Pixels where mask == 0 (buildable) should keep their PVOUT values."""
        pvout = np.array([[4.5, 4.8], [4.9, 5.1]])
        mask  = np.zeros((2, 2), dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        np.testing.assert_array_equal(result, pvout)

    def test_does_not_modify_input(self):
        """apply_exclusion_mask should return a copy, not modify in place."""
        pvout = np.array([[5.0, 5.0]], dtype=float)
        mask  = np.array([[1, 0]], dtype=np.uint8)
        _ = apply_exclusion_mask(pvout, mask)
        assert pvout[0, 0] == 5.0  # original unchanged

    def test_peat_mask_zeros_peat_pixels(self):
        """Peatland mask removes pixels identically to forest mask."""
        pvout = np.array([[4.0, 5.0], [3.5, 4.5]])
        peat_mask = np.array([[0, 1], [0, 0]], dtype=np.uint8)
        result = apply_exclusion_mask(pvout, peat_mask)
        assert result[0, 1] == 0.0
        assert result[0, 0] == 4.0
        assert result[1, 0] == 3.5


# ── apply_slope_elevation_mask ────────────────────────────────────────────────

class TestApplySlopeElevationMask:
    def test_steep_pixels_excluded(self):
        """Pixels with slope > MAX_SLOPE_DEG should be set to 0."""
        pvout = np.full((3, 3), 5.0)
        steep_slope = np.full((3, 3), MAX_SLOPE_DEG + 1)  # all steep
        elev  = np.full((3, 3), 100.0)                    # elevation OK
        result = apply_slope_elevation_mask(pvout, steep_slope, elev)
        assert np.all(result == 0.0)

    def test_flat_pixels_retained(self):
        """Pixels with slope = 0° should pass (PVOUT values kept)."""
        pvout = np.full((2, 2), 4.5)
        slope = np.zeros((2, 2))
        elev  = np.full((2, 2), 50.0)
        result = apply_slope_elevation_mask(pvout, slope, elev)
        np.testing.assert_array_almost_equal(result, pvout)

    def test_high_elevation_excluded(self):
        """Pixels with elevation > MAX_ELEV_M should be set to 0."""
        pvout = np.full((2, 2), 5.0)
        slope = np.zeros((2, 2))
        elev  = np.full((2, 2), MAX_ELEV_M + 1)
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert np.all(result == 0.0)

    def test_slope_nan_treated_as_excluded(self):
        """NaN in slope_arr should conservatively exclude the pixel."""
        pvout = np.array([[5.0]])
        slope = np.array([[np.nan]])
        elev  = np.array([[100.0]])
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert result[0, 0] == 0.0

    def test_mixed_terrain(self):
        """Pixels below both thresholds pass; above either threshold fail."""
        pvout = np.array([[5.0, 5.0, 5.0]])
        slope = np.array([[2.0, MAX_SLOPE_DEG + 1, 3.0]])
        elev  = np.array([[100.0, 100.0, MAX_ELEV_M + 1]])
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert result[0, 0] == 5.0   # passes both
        assert result[0, 1] == 0.0   # fails slope
        assert result[0, 2] == 0.0   # fails elevation


# ── apply_min_area_filter ─────────────────────────────────────────────────────

class TestApplyMinAreaFilter:
    def test_small_patch_removed(self):
        """A single isolated pixel (5 ha < 10 ha) should be removed."""
        # pixel_area_ha = 5.0 → 1 pixel = 5 ha < MIN_AREA_HA (10 ha)
        mask = np.array([[False, False], [False, True]])
        result = apply_min_area_filter(mask, pixel_area_ha=5.0, min_area_ha=10.0)
        assert not result[1, 1]

    def test_large_patch_retained(self):
        """A 4-pixel connected patch (4 × 5 ha = 20 ha ≥ 10 ha) should be kept."""
        mask = np.array([[True, True], [True, True]])
        result = apply_min_area_filter(mask, pixel_area_ha=5.0, min_area_ha=10.0)
        assert np.all(result)

    def test_empty_mask_returns_all_false(self):
        """All-false mask → all-false output."""
        mask = np.zeros((3, 3), dtype=bool)
        result = apply_min_area_filter(mask, pixel_area_ha=5.0)
        assert not np.any(result)

    def test_large_single_pixel_at_pvout_resolution(self):
        """At ~86 ha/pixel (PVOUT resolution), 1 pixel >> 10 ha threshold → passes."""
        mask = np.array([[True]])
        result = apply_min_area_filter(mask, pixel_area_ha=86.0, min_area_ha=10.0)
        assert result[0, 0]


# ── compute_slope_degrees ─────────────────────────────────────────────────────

class TestComputeSlopeDegrees:
    def test_flat_dem_gives_zero_slope(self):
        """A uniform DEM should yield zero slope everywhere."""
        dem = np.full((5, 5), 100.0)
        slope = compute_slope_degrees(dem, pixel_size_m=30.0)
        np.testing.assert_array_almost_equal(slope, np.zeros((5, 5)), decimal=5)

    def test_slope_positive_for_ramp(self):
        """A linearly sloping DEM should give positive slope values."""
        dem = np.tile(np.arange(5, dtype=float) * 30, (5, 1))  # 30m rise per 30m pixel = 45°
        slope = compute_slope_degrees(dem, pixel_size_m=30.0)
        # Interior pixels should be near 45° (rise/run = 1)
        assert np.all(slope[1:-1, 1:-1] > 0)


# ── compute_buildability_constraint ──────────────────────────────────────────

class TestComputeBuildabilityConstraint:
    def test_kawasan_hutan_dominant(self):
        """Kawasan Hutan removes most pixels → constraint = kawasan_hutan."""
        # 100 raw → 20 after KH (80 removed) → 18 after peat → 15 after LC → 14 after slope → 14 after area
        result = compute_buildability_constraint(100, 20, 18, 15, 14, 14)
        assert result == "kawasan_hutan"

    def test_slope_dominant(self):
        """Slope removes most pixels → constraint = slope."""
        result = compute_buildability_constraint(100, 95, 94, 93, 50, 50)
        assert result == "slope"

    def test_unconstrained_when_no_removal(self):
        """No pixels removed at any layer → unconstrained."""
        result = compute_buildability_constraint(50, 50, 50, 50, 50, 50)
        assert result == "unconstrained"

    def test_unconstrained_on_zero_pixels(self):
        """Zero raw pixels → unconstrained (no exclusion to report)."""
        result = compute_buildability_constraint(0, 0, 0, 0, 0, 0)
        assert result == "unconstrained"

    def test_output_is_valid_constraint(self):
        """All returned values are in the VALID_CONSTRAINTS set."""
        cases = [
            (100, 20, 18, 15, 14, 14),
            (100, 95, 94, 50, 49, 49),
            (100, 95, 60, 58, 57, 57),
            (100, 95, 94, 93, 90, 70),
            (50, 50, 50, 50, 50, 50),
        ]
        for args in cases:
            result = compute_buildability_constraint(*args)
            assert result in VALID_CONSTRAINTS, f"Unexpected constraint: {result}"


# ── Property tests ────────────────────────────────────────────────────────────

class TestProperties:
    def test_max_capacity_formula(self):
        """max_captive_capacity_mwp = buildable_area_ha / HA_PER_MWP."""
        from src.pipeline.buildability_filters import HA_PER_MWP
        buildable_area_ha = 150.0
        expected_mwp = buildable_area_ha / HA_PER_MWP
        assert math.isclose(expected_mwp, 100.0)  # 150 / 1.5 = 100 MWp

    def test_buildable_pvout_leq_raw(self):
        """After any exclusion, max PVOUT can only decrease or stay equal."""
        pvout = np.array([[5.0, 4.5, 3.8], [4.2, 5.1, 4.7]])
        mask  = np.array([[0, 1, 0], [0, 0, 1]], dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        # Max of filtered ≤ max of original
        assert result.max() <= pvout.max()
