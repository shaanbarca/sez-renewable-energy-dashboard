# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""F13: geas_alloc_empirical — distance decay + region multiplier behavior.

Validates the spec §4.3 expectation that empirical allocation is lower for
remote eastern KEKs and roughly equal to proportional for Java sites near
load centres.
"""

from __future__ import annotations

import pytest

from src.assumptions import (
    GEAS_DISTANCE_DECAY_FAR_KM,
    GEAS_DISTANCE_DECAY_FLOOR,
    GEAS_DISTANCE_DECAY_NEAR_KM,
    REGION_GEAS_MULT,
    REGION_GEAS_MULT_DEFAULT,
)
from src.model.basic_model import geas_alloc_empirical

# ── Distance decay ─────────────────────────────────────────────────────────


def test_within_near_distance_no_decay():
    """At <= 100 km from load centre, distance_decay = 1.0 (no penalty)."""
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=50,
        region="JAVA_BALI",
    )
    # proportional × 1.0 × 1.2 = 0.2 × 10000 × 1.2 = 2400
    expected = 10_000 * (1_000 / 5_000) * 1.0 * REGION_GEAS_MULT["JAVA_BALI"]
    assert alloc == pytest.approx(expected)


def test_at_far_distance_floored():
    """Beyond 500 km, distance_decay = floor (0.4)."""
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=600,
        region="MALUKU",
    )
    expected = 10_000 * (1_000 / 5_000) * GEAS_DISTANCE_DECAY_FLOOR * REGION_GEAS_MULT["MALUKU"]
    assert alloc == pytest.approx(expected)


def test_distance_decay_linear_between_near_and_far():
    """At the midpoint between NEAR and FAR, decay ≈ (1 + floor) / 2."""
    midpoint_km = (GEAS_DISTANCE_DECAY_NEAR_KM + GEAS_DISTANCE_DECAY_FAR_KM) / 2
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=midpoint_km,
        region="SUMATERA",
    )
    expected_decay = (1.0 + GEAS_DISTANCE_DECAY_FLOOR) / 2
    expected = 10_000 * (1_000 / 5_000) * expected_decay * REGION_GEAS_MULT["SUMATERA"]
    assert alloc == pytest.approx(expected, rel=0.001)


# ── Region multiplier ──────────────────────────────────────────────────────


def test_java_multiplier_amplifies_share():
    """Java sites near load centre should get >= proportional (multiplier 1.2)."""
    java = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=20,
        region="JAVA_BALI",
    )
    proportional = 10_000 * (1_000 / 5_000)
    assert java > proportional


def test_eastern_indonesia_multiplier_dampens_share():
    """Maluku/Papua should get << proportional (multiplier 0.4 + distance penalty)."""
    eastern = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=400,
        region="MALUKU",
    )
    proportional = 10_000 * (1_000 / 5_000)
    assert eastern < proportional * 0.5  # more than halved


def test_unknown_region_uses_default_mult():
    """Defensive: unknown region falls back to REGION_GEAS_MULT_DEFAULT."""
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=50,
        region="UNKNOWN_REGION",
    )
    expected = 10_000 * (1_000 / 5_000) * 1.0 * REGION_GEAS_MULT_DEFAULT
    assert alloc == pytest.approx(expected)


# ── Edge cases ─────────────────────────────────────────────────────────────


def test_zero_region_demand_safe():
    """Division-by-zero guard."""
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=0,
        distance_to_load_centre_km=50,
        region="JAVA_BALI",
    )
    assert alloc == 0.0


def test_zero_green_energy_returns_zero():
    """No regional supply → no allocation regardless of distance/region."""
    alloc = geas_alloc_empirical(
        green_energy_regional_mwh=0,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=50,
        region="JAVA_BALI",
    )
    assert alloc == 0.0


# ── Spec validation: per-region comparison ─────────────────────────────────


def test_spec_validation_remote_eastern_significantly_lower_than_proportional():
    """Spec §4.3: remote eastern KEKs (Sorong/Morotai) should show empirical
    30-50%+ lower than proportional. Sorong is ~600 km from regional load centre."""
    common = dict(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=600,
    )
    proportional = 10_000 * (1_000 / 5_000)
    empirical = geas_alloc_empirical(region="PAPUA", **common)
    # 0.4 floor decay × 0.4 PAPUA multiplier = 16% of proportional
    assert empirical < proportional * 0.2


def test_spec_validation_java_near_load_centre_close_to_proportional():
    """Java sites near Jakarta (50 km) should show empirical >= proportional
    (1.2 multiplier × 1.0 distance decay)."""
    common = dict(
        green_energy_regional_mwh=10_000,
        demand_kek_mwh=1_000,
        demand_total_region_mwh=5_000,
        distance_to_load_centre_km=50,
    )
    proportional = 10_000 * (1_000 / 5_000)
    empirical = geas_alloc_empirical(region="JAVA_BALI", **common)
    assert empirical >= proportional  # 1.2 × 1.0 × proportional = 1.2 ×
