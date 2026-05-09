# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.technology`.

Covers `compute_bess_metrics`, `compute_firm_coverage`, `compute_hybrid_metrics`.
Signature + output-shape guard; the numerical behaviour is re-verified by the
scorecard golden-master.
"""

from __future__ import annotations

from src.dash.logic.assumptions import get_default_assumptions, get_default_thresholds
from src.dash.logic.technology import (
    compute_bess_metrics,
    compute_firm_coverage,
    compute_hybrid_metrics,
)

BESS_KEYS = {
    "bess_sizing_hours",
    "battery_adder_usd_mwh",
    "lcoe_with_battery_usd_mwh",
    "bess_competitive",
}
FIRM_KEYS = {
    "firm_solar_coverage_pct",
    "nighttime_demand_mwh",
    "storage_required_mwh",
    "storage_gap_pct",
    "firm_wind_coverage_pct",
    "wind_firming_gap_pct",
    "wind_firming_hours",
}
HYBRID_KEYS = {
    "hybrid_lcoe_usd_mwh",
    "hybrid_bess_hours",
    "hybrid_bess_adder_usd_mwh",
    "hybrid_allin_usd_mwh",
    "hybrid_solar_share",
    "hybrid_supply_coverage_pct",
    "hybrid_nighttime_coverage_pct",
    "hybrid_bess_reduction_pct",
    "hybrid_carbon_breakeven_usd_tco2",
    "hybrid_wind_nighttime_fraction",
    "hybrid_binding_constraint",
    "hybrid_binding_narrative",
    "hybrid_constraint_sensitivity",
}


def test_compute_bess_metrics_shape_and_override() -> None:
    a = get_default_assumptions()
    a.bess_sizing_hours_override = 6.0
    out = compute_bess_metrics(
        lcoe_mid=70.0,
        primary_cf=0.18,
        reliability_req=0.9,
        dominant_process="Nickel Pig Iron",
        assumptions=a,
        thresholds=get_default_thresholds(),
        grid_cost=100.0,
    )
    assert set(out.keys()) == BESS_KEYS
    assert out["bess_sizing_hours"] == 6.0
    assert out["battery_adder_usd_mwh"] > 0
    assert out["lcoe_with_battery_usd_mwh"] == round(70.0 + out["battery_adder_usd_mwh"], 2)


def test_compute_bess_metrics_no_cf_yields_no_adder() -> None:
    out = compute_bess_metrics(
        lcoe_mid=70.0,
        primary_cf=0.0,
        reliability_req=0.5,
        dominant_process="",
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        grid_cost=100.0,
    )
    assert out["battery_adder_usd_mwh"] == 0.0
    assert out["lcoe_with_battery_usd_mwh"] == 70.0


def test_compute_bess_metrics_rkef_sizing_doubled() -> None:
    out = compute_bess_metrics(
        lcoe_mid=70.0,
        primary_cf=0.18,
        reliability_req=0.5,
        dominant_process="RKEF",
        assumptions=get_default_assumptions(),
        thresholds=get_default_thresholds(),
        grid_cost=100.0,
    )
    from src.assumptions import BESS_SIZING_HOURS

    assert out["bess_sizing_hours"] == BESS_SIZING_HOURS * 2.0


def test_compute_firm_coverage_shape() -> None:
    out = compute_firm_coverage(
        solar_gen_mwh=500_000.0,
        wind_gen_mwh=300_000.0,
        demand_mwh=1_000_000.0,
        wind_cf_best=0.35,
    )
    assert set(out.keys()) == FIRM_KEYS


def test_compute_hybrid_metrics_shape() -> None:
    out = compute_hybrid_metrics(
        solar_lcoe=60.0,
        wind_lcoe=55.0,
        solar_gen_mwh=500_000.0,
        wind_gen_mwh=400_000.0,
        primary_cf=0.18,
        wind_cf_best=0.35,
        solar_capacity_mwp=300.0,
        wind_capacity_mwp=150.0,
        demand_mwh=1_000_000.0,
        assumptions=get_default_assumptions(),
        grid_cost=100.0,
        emission_factor=0.8,
    )
    assert set(out.keys()) == HYBRID_KEYS
    assert 0.0 <= out["hybrid_solar_share"] <= 1.0


def _hybrid_with_region(grid_region_id: str | None) -> dict:
    return compute_hybrid_metrics(
        solar_lcoe=60.0,
        wind_lcoe=55.0,
        solar_gen_mwh=500_000.0,
        wind_gen_mwh=400_000.0,
        primary_cf=0.18,
        wind_cf_best=0.35,
        solar_capacity_mwp=300.0,
        wind_capacity_mwp=150.0,
        demand_mwh=1_000_000.0,
        assumptions=get_default_assumptions(),
        grid_cost=100.0,
        emission_factor=0.8,
        grid_region_id=grid_region_id,
    )


def test_compute_hybrid_metrics_wind_nighttime_fraction_tiered() -> None:
    """F3: wind nighttime fraction varies by grid_region_id."""
    # NTT (sea-breeze): lowest nighttime fraction
    ntt = _hybrid_with_region("NUSA_TENGGARA")
    assert ntt["hybrid_wind_nighttime_fraction"] == 0.42
    # Sulawesi
    sul = _hybrid_with_region("SULAWESI")
    assert sul["hybrid_wind_nighttime_fraction"] == 0.50
    # Java + Sumatra (same value)
    jav = _hybrid_with_region("JAVA_BALI")
    sum_ = _hybrid_with_region("SUMATERA")
    assert jav["hybrid_wind_nighttime_fraction"] == sum_["hybrid_wind_nighttime_fraction"] == 0.55
    # Kalimantan: highest nighttime fraction (doldrums)
    kal = _hybrid_with_region("KALIMANTAN")
    assert kal["hybrid_wind_nighttime_fraction"] == 0.60
    # Maluku/Papua + None: fall back to uniform 14/24 ≈ 0.583
    pap = _hybrid_with_region("PAPUA")
    none = _hybrid_with_region(None)
    assert pap["hybrid_wind_nighttime_fraction"] == 14.0 / 24.0
    assert none["hybrid_wind_nighttime_fraction"] == 14.0 / 24.0
    # Ordering invariant: NTT < Sulawesi < Java/Sumatra < default < Kalimantan
    assert (
        ntt["hybrid_wind_nighttime_fraction"]
        < sul["hybrid_wind_nighttime_fraction"]
        < jav["hybrid_wind_nighttime_fraction"]
        < none["hybrid_wind_nighttime_fraction"]
        < kal["hybrid_wind_nighttime_fraction"]
    )


def test_compute_hybrid_metrics_binding_constraint_present() -> None:
    """F10: binding-constraint signal returned for auto-optimized sites."""
    out = _hybrid_with_region("JAVA_BALI")
    binding = out["hybrid_binding_constraint"]
    narrative = out["hybrid_binding_narrative"]
    sensitivity = out["hybrid_constraint_sensitivity"]
    assert binding in {
        "bess_capex",
        "solar_capex",
        "wind_capex",
        "wacc",
        "storage_duration",
        "none_meaningful",
    }
    assert isinstance(narrative, str) and len(narrative) > 0
    assert isinstance(sensitivity, float) and sensitivity >= 0.0


def test_compute_hybrid_metrics_binding_constraint_skipped_under_override() -> None:
    """F10: when user pins solar_share, sensitivity analysis is skipped (returns None)."""
    a = get_default_assumptions()
    a.hybrid_solar_share = 0.7  # user-pinned mix
    out = compute_hybrid_metrics(
        solar_lcoe=60.0,
        wind_lcoe=55.0,
        solar_gen_mwh=500_000.0,
        wind_gen_mwh=400_000.0,
        primary_cf=0.18,
        wind_cf_best=0.35,
        solar_capacity_mwp=300.0,
        wind_capacity_mwp=150.0,
        demand_mwh=1_000_000.0,
        assumptions=a,
        grid_cost=100.0,
        emission_factor=0.8,
        grid_region_id="JAVA_BALI",
    )
    assert out["hybrid_binding_constraint"] is None
    assert out["hybrid_binding_narrative"] is None
    assert out["hybrid_constraint_sensitivity"] is None
