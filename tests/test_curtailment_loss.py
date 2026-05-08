# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""F8: estimate_curtailment_loss_pct — bucket boundary + override tests.

Bucket structure (from spec §3.4):
    broad-grid override   → 0.05  (inter-substation connected AND BPP < $100/MWh)
    oversupply < 0.5      → 0.05  (load >> solar; no curtailment)
    oversupply 0.5-1.0    → 0.10
    oversupply 1.0-2.0    → 0.20
    oversupply > 2.0      → 0.35  (Maluku/Papua small-island scenario)
"""

from __future__ import annotations

import pytest

from src.assumptions import (
    CURTAILMENT_BROAD_GRID_DEFAULT_PCT,
    CURTAILMENT_EXTREME_OVERSUPPLY_PCT,
    CURTAILMENT_HIGH_OVERSUPPLY_PCT,
    CURTAILMENT_LOW_OVERSUPPLY_PCT,
    CURTAILMENT_MID_OVERSUPPLY_PCT,
)
from src.model.basic_model import estimate_curtailment_loss_pct

# ── Broad-grid override ─────────────────────────────────────────────────────


def test_broad_grid_java_uses_default_curtailment():
    """Java grid: inter_substation_connected + low BPP → 5% baseline regardless of oversupply."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=100_000,
        local_grid_demand_mwh=50_000,  # solar > demand, would be 0.20 normally
        inter_substation_connected=True,
        grid_region_bpp_usd_mwh=80,
    )
    assert pct == CURTAILMENT_BROAD_GRID_DEFAULT_PCT


def test_broad_grid_threshold_inclusive_below():
    """BPP just below $100 still gets the broad-grid default."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=100_000,
        local_grid_demand_mwh=50_000,
        inter_substation_connected=True,
        grid_region_bpp_usd_mwh=99.0,
    )
    assert pct == CURTAILMENT_BROAD_GRID_DEFAULT_PCT


def test_high_bpp_disables_broad_grid_override():
    """Diesel-dominant island grid (BPP $200+) doesn't get the broad-grid pass even when connected."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=100_000,
        local_grid_demand_mwh=20_000,  # 5x oversupply
        inter_substation_connected=True,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == CURTAILMENT_EXTREME_OVERSUPPLY_PCT


def test_disconnected_disables_broad_grid_override():
    """Without inter-substation connectivity, BPP value alone doesn't trigger the override."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=100_000,
        local_grid_demand_mwh=200_000,  # oversupply 0.5 → mid bucket
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=80,
    )
    assert pct == CURTAILMENT_MID_OVERSUPPLY_PCT


# ── Oversupply tier boundaries ──────────────────────────────────────────────


def test_low_oversupply_5pct():
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=10_000,
        local_grid_demand_mwh=100_000,  # ratio 0.1
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == CURTAILMENT_LOW_OVERSUPPLY_PCT


def test_mid_oversupply_10pct():
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=70_000,
        local_grid_demand_mwh=100_000,  # ratio 0.7
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == CURTAILMENT_MID_OVERSUPPLY_PCT


def test_high_oversupply_20pct():
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=150_000,
        local_grid_demand_mwh=100_000,  # ratio 1.5
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == CURTAILMENT_HIGH_OVERSUPPLY_PCT


def test_extreme_oversupply_35pct_maluku_scenario():
    """Spec validation: Maluku/Papua small-island, large solar → 35%."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=300_000,
        local_grid_demand_mwh=100_000,  # ratio 3.0
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == CURTAILMENT_EXTREME_OVERSUPPLY_PCT


# ── Edge cases ──────────────────────────────────────────────────────────────


def test_zero_demand_safe():
    """Division-by-zero guard: empty grid → still returns a value, not NaN."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=10_000,
        local_grid_demand_mwh=0,
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    # 10,000 / max(0, 1) = 10,000 → ratio >> 2 → extreme bucket
    assert pct == CURTAILMENT_EXTREME_OVERSUPPLY_PCT


@pytest.mark.parametrize(
    "ratio,expected",
    [
        (0.1, CURTAILMENT_LOW_OVERSUPPLY_PCT),
        (0.49, CURTAILMENT_LOW_OVERSUPPLY_PCT),
        (0.5, CURTAILMENT_MID_OVERSUPPLY_PCT),
        (0.99, CURTAILMENT_MID_OVERSUPPLY_PCT),
        (1.0, CURTAILMENT_HIGH_OVERSUPPLY_PCT),
        (1.99, CURTAILMENT_HIGH_OVERSUPPLY_PCT),
        (2.0, CURTAILMENT_EXTREME_OVERSUPPLY_PCT),
        (5.0, CURTAILMENT_EXTREME_OVERSUPPLY_PCT),
    ],
)
def test_oversupply_buckets_at_boundaries(ratio: float, expected: float):
    """Boundary-test the oversupply tiers — confirms < vs <= semantics match the spec."""
    pct = estimate_curtailment_loss_pct(
        solar_generation_mwh=ratio * 100_000,
        local_grid_demand_mwh=100_000,
        inter_substation_connected=False,
        grid_region_bpp_usd_mwh=200,
    )
    assert pct == expected


def test_curtailment_pct_in_unit_interval():
    """Sanity: every reasonable input returns a fraction in [0, 1)."""
    for sg, ld, ic, bpp in [
        (10_000, 100_000, True, 50),
        (500_000, 100_000, False, 250),
        (0, 100_000, True, 80),
    ]:
        pct = estimate_curtailment_loss_pct(sg, ld, ic, bpp)
        assert 0 <= pct < 1
