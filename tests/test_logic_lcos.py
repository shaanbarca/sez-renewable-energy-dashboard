"""Tests for src/dash/logic/lcos.py — storage LCOS + firm LCOE adder.

Pins the v4.1a §8 methodology (issue #69). The LCOS values themselves at the
v4.1a `BATTERY_DEFAULTS` land at ~$170/MWh for both 4h and 8h (the
generation cost is dominated by capex_per_kwh, which is the same at every
duration). The IEA bands "$30-50/MWh at 4h, $80-130/MWh at 8h" referenced
in the issue and spec §2.1.1 are the *storage-cost-adders* to LCOE,
i.e. LCOS × storage_share (0.20 for 4h, 0.50 for 8h). Both interpretations
are pinned below.
"""

from __future__ import annotations

import math

import pytest

from src.assumptions import BATTERY_DEFAULTS
from src.dash.logic.lcos import (
    _capital_recovery_factor,
    compute_battery_lcos,
    compute_firm_delivered_lcoe,
    lcos_at_duration,
)


class TestCapitalRecoveryFactor:
    def test_zero_rate_returns_inverse_lifetime(self) -> None:
        # With r=0, CRF → 1/n (the simple-averaging form).
        assert _capital_recovery_factor(0.0, 10) == pytest.approx(0.10)
        assert _capital_recovery_factor(0.0, 15) == pytest.approx(1.0 / 15)

    def test_positive_rate_standard_formula(self) -> None:
        # 10% discount, 15-year life: well-known CRF ≈ 0.1315.
        assert _capital_recovery_factor(0.10, 15) == pytest.approx(0.13147, rel=1e-3)

    def test_zero_lifetime_raises(self) -> None:
        with pytest.raises(ValueError, match="lifetime_years"):
            _capital_recovery_factor(0.10, 0)

    def test_negative_rate_raises(self) -> None:
        with pytest.raises(ValueError, match="discount_rate"):
            _capital_recovery_factor(-0.05, 10)


class TestComputeBatteryLCOS:
    """Happy-path LCOS values at the v4.1a IRENA defaults."""

    def test_lcos_4h_at_defaults(self) -> None:
        # 4h Li-ion @ $350/kWh, 15yr, 365 cy/yr, RTE 0.90, DOD 0.85, $7/kW-yr,
        # 10% discount → ~$170/MWh delivered through storage.
        lcos = lcos_at_duration(4.0)
        # Sanity band: $100-300/MWh is the public Lazard 2024 LCOS-4h range.
        assert 100.0 < lcos < 300.0
        # Pin within ±$5 of computed value.
        assert lcos == pytest.approx(171.07, abs=0.5)

    def test_lcos_8h_at_defaults(self) -> None:
        lcos = lcos_at_duration(8.0)
        assert 100.0 < lcos < 300.0
        assert lcos == pytest.approx(167.93, abs=0.5)

    def test_lcos_4h_adder_in_iea_band(self) -> None:
        """Per spec §2.1.1: LCOS_4h × 20% storage share → ~$30-50/MWh adder
        to the solar LCOE for firm_4h. Issue #69 acceptance criterion."""
        lcos_4h = lcos_at_duration(4.0)
        adder = lcos_4h * 0.20
        assert 30.0 <= adder <= 50.0, f"4h adder {adder:.2f} outside [$30, $50]"

    def test_lcos_8h_adder_in_iea_band(self) -> None:
        """Per spec §2.1.1: LCOS_8h × 50% storage share → ~$80-130/MWh adder
        to the solar LCOE for firm_8h. Issue #69 acceptance criterion."""
        lcos_8h = lcos_at_duration(8.0)
        adder = lcos_8h * 0.50
        assert 80.0 <= adder <= 130.0, f"8h adder {adder:.2f} outside [$80, $130]"

    def test_zero_discount_rate_lcos_is_lower(self) -> None:
        """Sanity: zero WACC strips the capex-annualization premium →
        LCOS at r=0 < LCOS at r=10%."""
        baseline = lcos_at_duration(4.0)
        free = lcos_at_duration(4.0, discount_rate=0.0)
        assert free < baseline

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity_kwh"):
            compute_battery_lcos(capacity_kwh=0.0, duration_hours=4.0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity_kwh"):
            compute_battery_lcos(capacity_kwh=-1.0, duration_hours=4.0)

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="duration_hours"):
            compute_battery_lcos(capacity_kwh=4000.0, duration_hours=0.0)

    def test_invalid_rte_raises(self) -> None:
        with pytest.raises(ValueError, match="rte"):
            compute_battery_lcos(capacity_kwh=4000.0, duration_hours=4.0, rte=1.5)
        with pytest.raises(ValueError, match="rte"):
            compute_battery_lcos(capacity_kwh=4000.0, duration_hours=4.0, rte=0.0)

    def test_invalid_dod_raises(self) -> None:
        with pytest.raises(ValueError, match="dod"):
            compute_battery_lcos(capacity_kwh=4000.0, duration_hours=4.0, dod=1.5)
        with pytest.raises(ValueError, match="dod"):
            compute_battery_lcos(capacity_kwh=4000.0, duration_hours=4.0, dod=0.0)

    def test_capacity_independence(self) -> None:
        """LCOS should be independent of nameplate (capex and throughput
        both scale linearly with capacity_kwh)."""
        small = compute_battery_lcos(capacity_kwh=1000.0, duration_hours=4.0)
        large = compute_battery_lcos(capacity_kwh=1_000_000.0, duration_hours=4.0)
        assert small == pytest.approx(large, rel=1e-6)

    def test_lower_capex_lowers_lcos(self) -> None:
        baseline = lcos_at_duration(4.0, capex_per_kwh=350.0)
        cheap = lcos_at_duration(4.0, capex_per_kwh=150.0)
        assert cheap < baseline

    def test_more_cycles_lower_lcos(self) -> None:
        """Higher throughput → lower $/MWh."""
        baseline = lcos_at_duration(4.0, cycles_per_year=365)
        higher = lcos_at_duration(4.0, cycles_per_year=500)
        assert higher < baseline


class TestBatteryDefaults:
    """Pin the BATTERY_DEFAULTS dict from src/assumptions.py."""

    def test_defaults_match_irena_2024(self) -> None:
        assert BATTERY_DEFAULTS["capex_usd_per_kwh"] == 350
        assert BATTERY_DEFAULTS["lifetime_years"] == 15
        assert BATTERY_DEFAULTS["cycles_per_year"] == 365
        assert BATTERY_DEFAULTS["depth_of_discharge"] == 0.85
        assert BATTERY_DEFAULTS["round_trip_efficiency"] == 0.90
        assert BATTERY_DEFAULTS["fixed_om_usd_per_kw_year"] == 7


class TestFirmDeliveredLCOE:
    def test_firm_4h_adder_typical(self) -> None:
        """solar_lcoe=$50, storage_share=0.20, lcos_4h=$170 →
        firm ≈ $50 + small storage adder per simplified formula."""
        firm = compute_firm_delivered_lcoe(
            solar_lcoe=50.0,
            storage_share=0.20,
            storage_duration_hours=4.0,
            storage_lcos=170.0,
        )
        # The simplified formula's adder ≈ 0.20 × RTE / (1 + 0.20×RTE-0.20) × $170
        # ≈ ~$26. Total ≈ $76-$85 — wider band to cover RTE assumption shifts.
        assert 70.0 < firm < 90.0

    def test_firm_8h_adder_typical(self) -> None:
        firm = compute_firm_delivered_lcoe(
            solar_lcoe=50.0,
            storage_share=0.50,
            storage_duration_hours=8.0,
            storage_lcos=168.0,
        )
        assert 100.0 < firm < 140.0

    def test_zero_storage_share_returns_solar_lcoe(self) -> None:
        firm = compute_firm_delivered_lcoe(
            solar_lcoe=50.0,
            storage_share=0.0,
            storage_duration_hours=4.0,
            storage_lcos=170.0,
        )
        assert firm == pytest.approx(50.0)

    def test_invalid_share_raises(self) -> None:
        with pytest.raises(ValueError, match="storage_share"):
            compute_firm_delivered_lcoe(
                solar_lcoe=50.0,
                storage_share=1.5,
                storage_duration_hours=4.0,
                storage_lcos=170.0,
            )

    def test_zero_solar_lcoe_returns_pure_storage_share(self) -> None:
        """If solar LCOE is free, firm = effective_storage_share × LCOS /
        (direct + effective_storage_share). Sanity check."""
        firm = compute_firm_delivered_lcoe(
            solar_lcoe=0.0,
            storage_share=0.20,
            storage_duration_hours=4.0,
            storage_lcos=170.0,
        )
        assert firm > 0.0
        assert firm < 170.0  # not the full LCOS — only the share routed


class TestMaxDurationEdgeCase:
    def test_24h_duration_completes(self) -> None:
        """Max-duration edge case (24h battery): formula should still
        produce a finite, positive number."""
        lcos = lcos_at_duration(24.0)
        assert math.isfinite(lcos) and lcos > 0
