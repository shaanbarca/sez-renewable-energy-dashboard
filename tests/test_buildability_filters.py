"""
Tests for src/pipeline/buildability_filters.py

All tests use synthetic numpy arrays — no real geospatial data required.
This follows the plan's architecture decision: filter functions are pure functions
that accept arrays, enabling unit tests without the buildability data files.
"""

from __future__ import annotations

import math

import numpy as np
import rasterio.transform

from src.pipeline.buildability_filters import (
    MAX_ELEV_M,
    MAX_SLOPE_DEG,
    ROAD_MAX_DIST_KM,
    VALID_CONSTRAINTS,
    apply_exclusion_mask,
    apply_min_area_filter,
    apply_road_distance_mask,
    apply_slope_elevation_mask,
    compute_buildability_constraint,
    compute_distance_mask_km,
    compute_slope_degrees,
    haversine_km,
)

# ── apply_exclusion_mask ──────────────────────────────────────────────────────


class TestApplyExclusionMask:
    def test_forest_pixels_zeroed(self):
        """Pixels where mask == 1 (excluded) should become 0.0."""
        pvout = np.array([[5.0, 5.0], [5.0, 5.0]])
        mask = np.array([[1, 0], [0, 1]], dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        assert result[0, 0] == 0.0
        assert result[1, 1] == 0.0

    def test_buildable_pixels_retained(self):
        """Pixels where mask == 0 (buildable) should keep their PVOUT values."""
        pvout = np.array([[4.5, 4.8], [4.9, 5.1]])
        mask = np.zeros((2, 2), dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        np.testing.assert_array_equal(result, pvout)

    def test_does_not_modify_input(self):
        """apply_exclusion_mask should return a copy, not modify in place."""
        pvout = np.array([[5.0, 5.0]], dtype=float)
        mask = np.array([[1, 0]], dtype=np.uint8)
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
        elev = np.full((3, 3), 100.0)  # elevation OK
        result = apply_slope_elevation_mask(pvout, steep_slope, elev)
        assert np.all(result == 0.0)

    def test_flat_pixels_retained(self):
        """Pixels with slope = 0° should pass (PVOUT values kept)."""
        pvout = np.full((2, 2), 4.5)
        slope = np.zeros((2, 2))
        elev = np.full((2, 2), 50.0)
        result = apply_slope_elevation_mask(pvout, slope, elev)
        np.testing.assert_array_almost_equal(result, pvout)

    def test_high_elevation_excluded(self):
        """Pixels with elevation > MAX_ELEV_M should be set to 0."""
        pvout = np.full((2, 2), 5.0)
        slope = np.zeros((2, 2))
        elev = np.full((2, 2), MAX_ELEV_M + 1)
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert np.all(result == 0.0)

    def test_slope_nan_treated_as_excluded(self):
        """NaN in slope_arr should conservatively exclude the pixel."""
        pvout = np.array([[5.0]])
        slope = np.array([[np.nan]])
        elev = np.array([[100.0]])
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert result[0, 0] == 0.0

    def test_mixed_terrain(self):
        """Pixels below both thresholds pass; above either threshold fail."""
        pvout = np.array([[5.0, 5.0, 5.0]])
        slope = np.array([[2.0, MAX_SLOPE_DEG + 1, 3.0]])
        elev = np.array([[100.0, 100.0, MAX_ELEV_M + 1]])
        result = apply_slope_elevation_mask(pvout, slope, elev)
        assert result[0, 0] == 5.0  # passes both
        assert result[0, 1] == 0.0  # fails slope
        assert result[0, 2] == 0.0  # fails elevation


# ── apply_road_distance_mask ──────────────────────────────────────────────────


class TestApplyRoadDistanceMask:
    def test_far_pixels_zeroed(self):
        """Pixels > ROAD_MAX_DIST_KM from road should become 0.0."""
        pvout = np.full((2, 2), 5.0)
        road_dist = np.array([[5.0, 15.0], [8.0, 20.0]])
        result = apply_road_distance_mask(pvout, road_dist)
        assert result[0, 0] == 5.0  # 5 km < 10 km
        assert result[0, 1] == 0.0  # 15 km > 10 km
        assert result[1, 0] == 5.0  # 8 km < 10 km
        assert result[1, 1] == 0.0  # 20 km > 10 km

    def test_near_pixels_retained(self):
        """Pixels <= threshold from road keep their values."""
        pvout = np.array([[4.5, 4.8], [4.9, 5.1]])
        road_dist = np.full((2, 2), 3.0)  # all within 10km
        result = apply_road_distance_mask(pvout, road_dist)
        np.testing.assert_array_equal(result, pvout)

    def test_road_dist_nan_treated_as_excluded(self):
        """NaN in road_dist_arr should conservatively exclude the pixel."""
        pvout = np.array([[5.0, 5.0]])
        road_dist = np.array([[np.nan, 2.0]])
        result = apply_road_distance_mask(pvout, road_dist)
        assert result[0, 0] == 0.0  # NaN = excluded
        assert result[0, 1] == 5.0  # 2 km = retained

    def test_custom_threshold(self):
        """Custom max_dist_km overrides default."""
        pvout = np.full((1, 3), 5.0)
        road_dist = np.array([[3.0, 5.0, 8.0]])
        result = apply_road_distance_mask(pvout, road_dist, max_dist_km=4.0)
        assert result[0, 0] == 5.0  # 3 < 4
        assert result[0, 1] == 0.0  # 5 > 4
        assert result[0, 2] == 0.0  # 8 > 4

    def test_does_not_modify_input(self):
        """apply_road_distance_mask should return a copy, not modify in place."""
        pvout = np.array([[5.0, 5.0]], dtype=float)
        road_dist = np.array([[20.0, 2.0]])
        _ = apply_road_distance_mask(pvout, road_dist)
        assert pvout[0, 0] == 5.0  # original unchanged

    def test_exact_threshold_retained(self):
        """Pixels at exactly max_dist_km should be retained (> excludes, = does not)."""
        pvout = np.array([[5.0]])
        road_dist = np.array([[ROAD_MAX_DIST_KM]])
        result = apply_road_distance_mask(pvout, road_dist)
        assert result[0, 0] == 5.0  # exactly at threshold is NOT excluded

    def test_zero_distance_retained(self):
        """Pixels on a road (distance 0) should be retained."""
        pvout = np.array([[5.0]])
        road_dist = np.array([[0.0]])
        result = apply_road_distance_mask(pvout, road_dist)
        assert result[0, 0] == 5.0


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
        # 100 raw → 20 after KH (80 removed) → 18 after peat → 15 after LC → 15 road → 14 slope → 14 area
        result = compute_buildability_constraint(100, 20, 18, 15, 15, 14, 14)
        assert result == "kawasan_hutan"

    def test_slope_dominant(self):
        """Slope removes most pixels → constraint = slope."""
        result = compute_buildability_constraint(100, 95, 94, 93, 93, 50, 50)
        assert result == "slope"

    def test_far_from_road_dominant(self):
        """Road proximity removes most pixels → constraint = far_from_road."""
        # 100 raw → 95 KH → 94 peat → 93 LC → 30 road (63 removed!) → 28 slope → 28 area
        result = compute_buildability_constraint(100, 95, 94, 93, 30, 28, 28)
        assert result == "far_from_road"

    def test_unconstrained_when_no_removal(self):
        """No pixels removed at any layer → unconstrained."""
        result = compute_buildability_constraint(50, 50, 50, 50, 50, 50, 50)
        assert result == "unconstrained"

    def test_unconstrained_on_zero_pixels(self):
        """Zero raw pixels → unconstrained (no exclusion to report)."""
        result = compute_buildability_constraint(0, 0, 0, 0, 0, 0, 0)
        assert result == "unconstrained"

    def test_output_is_valid_constraint(self):
        """All returned values are in the VALID_CONSTRAINTS set."""
        # Args: (raw, 1a, 1b, 1cd, 3a, 2, 4)
        cases = [
            (100, 20, 18, 15, 15, 14, 14),
            (100, 95, 94, 50, 50, 49, 49),
            (100, 95, 60, 58, 58, 57, 57),
            (100, 95, 94, 93, 93, 90, 70),
            (100, 95, 94, 93, 30, 28, 28),  # road dominant
            (50, 50, 50, 50, 50, 50, 50),
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
        mask = np.array([[0, 1, 0], [0, 0, 1]], dtype=np.uint8)
        result = apply_exclusion_mask(pvout, mask)
        # Max of filtered ≤ max of original
        assert result.max() <= pvout.max()


# ── haversine_km ─────────────────────────────────────────────────────────────


class TestHaversineKm:
    def test_same_point_is_zero(self):
        """Distance from a point to itself is 0."""
        assert haversine_km(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_equator_one_degree_lon(self):
        """1° longitude at equator ≈ 111.32 km."""
        d = haversine_km(0.0, 0.0, 0.0, 1.0)
        assert 110.5 < d < 112.0

    def test_equator_one_degree_lat(self):
        """1° latitude at equator ≈ 111.32 km."""
        d = haversine_km(0.0, 0.0, 1.0, 0.0)
        assert 110.5 < d < 112.0

    def test_known_distance_jakarta_to_bandung(self):
        """Jakarta (-6.2, 106.8) to Bandung (-6.9, 107.6) ≈ 120 km."""
        d = haversine_km(-6.2, 106.8, -6.9, 107.6)
        assert 110 < d < 130

    def test_symmetry(self):
        """haversine(A, B) == haversine(B, A)."""
        d1 = haversine_km(-5.0, 110.0, -6.0, 111.0)
        d2 = haversine_km(-6.0, 111.0, -5.0, 110.0)
        assert math.isclose(d1, d2, rel_tol=1e-10)


# ── compute_distance_mask_km ──────────────────────────────────────────────────


class TestComputeDistanceMaskKm:
    def _make_transform(self, left: float, top: float, res_deg: float) -> rasterio.transform.Affine:
        """Create a simple affine transform for testing."""
        return rasterio.transform.Affine(res_deg, 0, left, 0, -res_deg, top)

    def test_center_pixel_near_zero_distance(self):
        """The pixel closest to the center should be near 0 km."""
        # 11×11 grid centered at (0, 0), resolution ~0.01° (≈1.1 km)
        res = 0.01
        transform = self._make_transform(-0.055, 0.055, res)
        dist = compute_distance_mask_km(0.0, 0.0, transform, (11, 11))
        # Center pixel (5, 5) should be very close to 0
        assert dist[5, 5] < 1.0  # less than 1 km

    def test_corners_farther_than_edges(self):
        """Corner pixels of a square grid should be farther than edge centers."""
        res = 0.01
        transform = self._make_transform(-0.05, 0.05, res)
        dist = compute_distance_mask_km(0.0, 0.0, transform, (10, 10))
        # Edge center (0, 5) vs corner (0, 0)
        assert dist[0, 0] > dist[0, 5]

    def test_50km_box_corners_exceed_50km(self):
        """Corners of a 50km bounding box should be beyond 50km radius."""
        # At equator, 50km ≈ 0.449°. Box is ±0.449°.
        buf_deg = 50.0 / 111.32
        res = 0.00833  # ~930m PVOUT pixel
        # Grid covers -buf to +buf in both axes
        n = int(2 * buf_deg / res) + 1
        transform = self._make_transform(-buf_deg, buf_deg, res)
        dist = compute_distance_mask_km(0.0, 0.0, transform, (n, n))
        # Corners should exceed 50km (diagonal ≈ 70.7km)
        assert dist[0, 0] > 50.0
        assert dist[0, -1] > 50.0
        assert dist[-1, 0] > 50.0
        assert dist[-1, -1] > 50.0
        # Edge centers should be ≤ 50km
        mid = n // 2
        assert dist[0, mid] < 52.0  # top edge center ≈ 50km
        assert dist[mid, 0] < 52.0  # left edge center ≈ 50km

    def test_all_distances_non_negative(self):
        """All distances should be non-negative."""
        transform = self._make_transform(100.0, 5.0, 0.01)
        dist = compute_distance_mask_km(-3.0, 100.05, transform, (5, 5))
        assert np.all(dist >= 0)
