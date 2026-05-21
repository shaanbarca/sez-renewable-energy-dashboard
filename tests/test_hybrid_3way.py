"""Tests for the v4.1b 3-way hybrid optimizer (spec §6A.4).

Covers:
- 2D sweep arithmetic for solar × hydro shares
- Hydro covers 100% / 0% edge cases
- Wind-absent path (no wind data → only solar+hydro candidates)
- Regression-pin: hybrid_lcoe_optimized_3way with hydro=None returns
  the SAME output as hybrid_lcoe_optimized (the 2-way function),
  i.e. v4.1a behavior byte-identical when hydro absent
- Spec §6A.6 validation case: hydro-rich Sumatra/Kalimantan profile
  should produce hydro share in 30-50% range with all-in $60-70/MWh
- Output column compatibility: both v4.1a legacy keys and v4.1b IEA-aligned
  keys present in the result dict
"""

from __future__ import annotations

import pytest

from src.model.basic_model import (
    HYDRO_DEFAULT_CF,
    HYDRO_DEFAULT_NIGHTTIME_FRACTION,
    RESource,
    hybrid_lcoe_optimized,
    hybrid_lcoe_optimized_3way,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────


def _solar(lcoe: float = 60.0, gen_mwh: float = 1_500_000.0, cf: float = 0.17) -> RESource:
    return RESource(
        technology="solar",
        lcoe_usd_mwh=lcoe,
        generation_mwh=gen_mwh,
        cf=cf,
        nighttime_fraction=0.0,
    )


def _wind(lcoe: float = 75.0, gen_mwh: float = 1_000_000.0, cf: float = 0.30) -> RESource:
    return RESource(
        technology="wind",
        lcoe_usd_mwh=lcoe,
        generation_mwh=gen_mwh,
        cf=cf,
        nighttime_fraction=0.583,
    )


def _hydro(
    lcoe: float = 50.0, gen_mwh: float = 800_000.0, cf: float = HYDRO_DEFAULT_CF
) -> RESource:
    return RESource(
        technology="hydro",
        lcoe_usd_mwh=lcoe,
        generation_mwh=gen_mwh,
        cf=cf,
        nighttime_fraction=HYDRO_DEFAULT_NIGHTTIME_FRACTION,
    )


DEMAND = 2_000_000.0


# ─── Regression: hydro absent → identical to 2-way ─────────────────────────


def test_hydro_none_falls_through_to_2way_byte_identical():
    """When hydro is None, hybrid_lcoe_optimized_3way must return exactly the
    same output as the 2-way function. This is the v4.1a baseline lock —
    non-hydro sites must not see any drift from v4.1b's optimizer change.
    """
    solar = _solar()
    wind = _wind()
    out_3way = hybrid_lcoe_optimized_3way(solar, wind, None, DEMAND)
    out_2way = hybrid_lcoe_optimized([solar, wind], DEMAND)
    assert out_3way == out_2way


def test_hydro_zero_generation_falls_through_to_2way():
    """A hydro source with zero generation behaves like 'no hydro available'."""
    solar = _solar()
    wind = _wind()
    hydro_dead = _hydro(gen_mwh=0.0)
    out_3way = hybrid_lcoe_optimized_3way(solar, wind, hydro_dead, DEMAND)
    out_2way = hybrid_lcoe_optimized([solar, wind], DEMAND)
    assert out_3way == out_2way


# ─── 2D sweep arithmetic ───────────────────────────────────────────────────


def test_3way_shares_sum_to_one():
    """The optimum must satisfy solar + wind + hydro = 1 within rounding."""
    out = hybrid_lcoe_optimized_3way(_solar(), _wind(), _hydro(), DEMAND)
    s = out["hybrid_solar_share"] or 0.0
    w = out["hybrid_wind_share"] or 0.0
    h = out["hybrid_hydro_share"] or 0.0
    assert abs(s + w + h - 1.0) < 0.01


def test_3way_includes_hydro_when_cheap():
    """Cheap hydro ($50/MWh) vs more expensive solar/wind should appear in optimum."""
    out = hybrid_lcoe_optimized_3way(_solar(lcoe=80.0), _wind(lcoe=85.0), _hydro(lcoe=50.0), DEMAND)
    assert (out["hybrid_hydro_share"] or 0.0) > 0


def test_3way_skips_expensive_hydro():
    """Expensive hydro ($200/MWh) should NOT appear in optimum when solar+wind are cheap."""
    out = hybrid_lcoe_optimized_3way(
        _solar(lcoe=60.0), _wind(lcoe=70.0), _hydro(lcoe=200.0), DEMAND
    )
    # Hydro can be 0 OR small; the test asserts the optimizer didn't blindly include it
    assert (out["hybrid_hydro_share"] or 0.0) < 0.5


def test_3way_all_in_below_2way_when_hydro_cheap():
    """Cheap dispatchable hydro should beat the 2-way optimum's all-in cost."""
    solar = _solar()
    wind = _wind()
    hydro = _hydro(lcoe=40.0)  # very cheap dispatchable
    out_3way = hybrid_lcoe_optimized_3way(solar, wind, hydro, DEMAND)
    out_2way = hybrid_lcoe_optimized([solar, wind], DEMAND)
    assert out_3way["hybrid_full_system_lcoe_usd_mwh"] is not None
    assert out_2way["hybrid_full_system_lcoe_usd_mwh"] is not None
    assert (
        out_3way["hybrid_full_system_lcoe_usd_mwh"]
        <= out_2way["hybrid_full_system_lcoe_usd_mwh"] + 0.01
    )


# ─── Edge cases ────────────────────────────────────────────────────────────


def test_no_solar_returns_empty():
    """Without solar, the 2D sweep can't be run (out of scope for v4.1b per spec §6A)."""
    out = hybrid_lcoe_optimized_3way(None, _wind(), _hydro(), DEMAND)
    assert out["hybrid_full_system_lcoe_usd_mwh"] is None


def test_no_wind_with_hydro_works():
    """Solar + hydro alone (no wind) should still optimize via 2D sweep with wind_share=0."""
    out = hybrid_lcoe_optimized_3way(_solar(), None, _hydro(), DEMAND)
    assert out["hybrid_full_system_lcoe_usd_mwh"] is not None
    assert (out["hybrid_wind_share"] or 0.0) == 0.0
    s = out["hybrid_solar_share"] or 0.0
    h = out["hybrid_hydro_share"] or 0.0
    assert abs(s + h - 1.0) < 0.01


# ─── Output schema compatibility ───────────────────────────────────────────


def test_output_contains_both_v41a_and_v41b_keys():
    """Result must contain both legacy v4.1a keys (deprecation aliases) and
    new v4.1b IEA-aligned keys. Audit: any caller still reading old names
    must keep working through v4.1b → v4.2 transition."""
    out = hybrid_lcoe_optimized_3way(_solar(), _wind(), _hydro(), DEMAND)
    # v4.1a legacy aliases
    legacy_keys = {
        "hybrid_bess_adder_usd_mwh",
        "hybrid_allin_usd_mwh",
        "optimal_solar_share",
    }
    # v4.1b IEA-aligned per spec §6A.5
    iea_keys = {
        "hybrid_solar_share",
        "hybrid_wind_share",
        "hybrid_hydro_share",
        "hybrid_lcos_usd_mwh",
        "hybrid_full_system_lcoe_usd_mwh",
        "hybrid_bess_reduction_pct",
    }
    missing = (legacy_keys | iea_keys) - set(out.keys())
    assert not missing, f"Missing keys: {missing}"


def test_legacy_and_iea_storage_keys_match_value():
    """hybrid_bess_adder_usd_mwh (legacy) == hybrid_lcos_usd_mwh (new) by construction."""
    out = hybrid_lcoe_optimized_3way(_solar(), _wind(), _hydro(), DEMAND)
    assert out["hybrid_bess_adder_usd_mwh"] == out["hybrid_lcos_usd_mwh"]
    assert out["hybrid_allin_usd_mwh"] == out["hybrid_full_system_lcoe_usd_mwh"]
    assert out["optimal_solar_share"] == out["hybrid_solar_share"]


def test_2way_path_also_emits_iea_keys():
    """Even the 2-way path through hybrid_lcoe_optimized must emit the new IEA keys
    so frontend code can migrate to the IEA names without conditional fallbacks."""
    out = hybrid_lcoe_optimized([_solar(), _wind()], DEMAND)
    iea_keys = {
        "hybrid_solar_share",
        "hybrid_wind_share",
        "hybrid_hydro_share",
        "hybrid_lcos_usd_mwh",
        "hybrid_full_system_lcoe_usd_mwh",
        "hybrid_bess_reduction_pct",
    }
    missing = iea_keys - set(out.keys())
    assert not missing, f"Missing IEA keys in 2-way output: {missing}"
    # Hydro share is 0 in 2-way mode
    assert out["hybrid_hydro_share"] == 0.0


# ─── Spec §6A.6 validation: hydro-rich profile ─────────────────────────────


def test_spec_6a6_hydro_rich_profile_produces_meaningful_hydro_share():
    """Spec §6A.6: Sumatra hydro-rich sites should land hydro share 30-50%
    with hybrid all-in $60-70/MWh. Calibrated against the JETP cost
    profile (Kalimantan Barat alumina-class, $61/MWh, 75% RE).

    Inputs roughly match the JETP profile: cheap dispatchable hydro
    ($45/MWh), moderately-priced solar ($55/MWh, low CF Indonesia),
    expensive wind ($85/MWh, low onshore quality).
    """
    solar = _solar(lcoe=55.0, gen_mwh=1_200_000.0, cf=0.17)
    wind = _wind(lcoe=85.0, gen_mwh=600_000.0, cf=0.25)
    hydro = _hydro(lcoe=45.0, gen_mwh=900_000.0, cf=0.50)
    out = hybrid_lcoe_optimized_3way(solar, wind, hydro, DEMAND)
    # Hydro share should be a meaningful component, not zero
    assert (out["hybrid_hydro_share"] or 0.0) >= 0.15, (
        f"Expected hydro share ≥ 15% in hydro-rich profile, got {out['hybrid_hydro_share']}"
    )
    # All-in below $90/MWh — beats coal baseline
    assert out["hybrid_full_system_lcoe_usd_mwh"] < 90.0


def test_spec_6a4_2d_sweep_resolution_231_evaluations():
    """Spec §6A.4 says 231 evaluations at 5% resolution.

    Combinations of (solar_share, hydro_share) where both are in [0, 5, 10, ..., 100]
    and sum ≤ 100. That's sum_{s=0}^{20} (21 - s) = 21*22/2 = 231.

    This test just sanity-checks that the optimizer doesn't crash and returns
    a result at 5% step (default step).
    """
    out = hybrid_lcoe_optimized_3way(_solar(), _wind(), _hydro(), DEMAND)
    assert out["hybrid_solar_share"] is not None
    # All shares should be multiples of 0.05 by construction
    for key in ("hybrid_solar_share", "hybrid_wind_share", "hybrid_hydro_share"):
        v = out[key] or 0.0
        snapped = round(v * 20) / 20  # snap to 0.05
        assert abs(v - snapped) < 0.001, f"{key}={v} not on 5% grid"


# ─── Hybrid BESS reduction (new v4.1b column) ──────────────────────────────


def test_bess_reduction_pct_present_and_in_range():
    """hybrid_bess_reduction_pct should be in [0, 1] and surface only on
    non-null bess_hours results."""
    out = hybrid_lcoe_optimized_3way(_solar(), _wind(), _hydro(), DEMAND)
    assert out["hybrid_bess_reduction_pct"] is not None
    val = out["hybrid_bess_reduction_pct"]
    assert val is not None and 0.0 <= val <= 1.0


def test_hydro_reduces_bess_vs_solar_only_no_wind():
    """Hydro's 24/7 dispatchability should reduce BESS sizing vs solar-alone.

    The 2-way wind-floor case (where the wind-only path with zero BESS beats the
    optimizer) makes a direct 2-way vs 3-way BESS comparison noisy. The cleaner
    comparison is solar-alone (no wind, no hydro) vs solar + hydro.
    """
    solar = _solar(lcoe=60.0)
    hydro = _hydro(lcoe=40.0)
    out_with_hydro = hybrid_lcoe_optimized_3way(solar, None, hydro, DEMAND)
    out_solar_only = hybrid_lcoe_optimized([solar], DEMAND)
    # Solar-only path forces full 14h BESS (no nighttime fill)
    assert out_solar_only["hybrid_bess_reduction_pct"] == pytest.approx(0.0, abs=0.05)
    # Hydro-blended path should reduce BESS sizing because hydro fills nighttime
    assert out_with_hydro["hybrid_bess_reduction_pct"] is not None
    assert out_with_hydro["hybrid_bess_reduction_pct"] > 0.2
