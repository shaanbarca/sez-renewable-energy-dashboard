"""Tests for src/dash/logic/marginal.py — daytime/nighttime marginal cost split.

Pins the v4.1a §6 methodology (issue #68): 5 dispatch regions × 2
times-of-day = 10 happy cases, plus unknown-region + NaN propagation.
"""

from __future__ import annotations

import math

import pytest

from src.dash.logic.marginal import (
    MARGINAL_CONFIDENCE_BY_REGION,
    MARGINAL_COST_ADJUSTMENT_BY_REGION,
    estimate_marginal_cost,
    marginal_confidence_for,
    region_to_marginal_key,
)


class TestRegionFactorTable:
    """Pin the spec §6.2 factor values. Changing a factor is a deliberate
    methodology decision that should land in METHODOLOGY §6 + this test."""

    def test_jamali(self) -> None:
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["JAMALI"]["daytime"] == 1.10
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["JAMALI"]["nighttime"] == 1.20

    def test_sumatera(self) -> None:
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Sumatera"]["daytime"] == 1.20
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Sumatera"]["nighttime"] == 1.40

    def test_kalimantan(self) -> None:
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Kalimantan"]["daytime"] == 1.50
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Kalimantan"]["nighttime"] == 1.70

    def test_sulawesi(self) -> None:
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Sulawesi"]["daytime"] == 1.60
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Sulawesi"]["nighttime"] == 1.80

    def test_maluku_papua(self) -> None:
        # Spec §6.2: daytime > nighttime in Maluku_Papua because daytime peak
        # hits diesel SRMC while baseload diesel runs at lower SRMC overnight.
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Maluku_Papua"]["daytime"] == 2.50
        assert MARGINAL_COST_ADJUSTMENT_BY_REGION["Maluku_Papua"]["nighttime"] == 2.20

    def test_daytime_vs_nighttime_directionality_per_region(self) -> None:
        """Spec §6.2 invariant: most regions have nighttime > daytime (gas /
        diesel peaks at night); Maluku_Papua reverses (daytime diesel SRMC)."""
        for region in ("JAMALI", "Sumatera", "Kalimantan", "Sulawesi"):
            day = MARGINAL_COST_ADJUSTMENT_BY_REGION[region]["daytime"]
            night = MARGINAL_COST_ADJUSTMENT_BY_REGION[region]["nighttime"]
            assert night > day, f"{region}: expected nighttime > daytime"
        mp = MARGINAL_COST_ADJUSTMENT_BY_REGION["Maluku_Papua"]
        assert mp["daytime"] > mp["nighttime"], (
            "Maluku_Papua: daytime should be > nighttime per spec §6.2"
        )


class TestEstimateMarginalCost:
    """5 regions × 2 times-of-day = 10 happy cases at bpp=$100/MWh."""

    @pytest.mark.parametrize(
        "region,time_of_day,expected",
        [
            ("JAMALI", "daytime", 110.0),
            ("JAMALI", "nighttime", 120.0),
            ("Sumatera", "daytime", 120.0),
            ("Sumatera", "nighttime", 140.0),
            ("Kalimantan", "daytime", 150.0),
            ("Kalimantan", "nighttime", 170.0),
            ("Sulawesi", "daytime", 160.0),
            ("Sulawesi", "nighttime", 180.0),
            ("Maluku_Papua", "daytime", 250.0),
            ("Maluku_Papua", "nighttime", 220.0),
        ],
    )
    def test_happy_path_spec_regions(self, region: str, time_of_day: str, expected: float) -> None:
        # `pytest.approx` to absorb float multiplication rounding (1.1 × 100
        # = 110.00000…01 on IEEE 754).
        assert estimate_marginal_cost(100.0, region, time_of_day) == pytest.approx(  # type: ignore[arg-type]
            expected, rel=1e-9
        )

    @pytest.mark.parametrize(
        "grid_region_id,marginal_key",
        [
            ("JAVA_BALI", "JAMALI"),
            ("NTB", "JAMALI"),
            ("SUMATERA", "Sumatera"),
            ("KALIMANTAN", "Kalimantan"),
            ("SULAWESI", "Sulawesi"),
            ("MALUKU", "Maluku_Papua"),
            ("PAPUA", "Maluku_Papua"),
        ],
    )
    def test_codebase_grid_region_id_normalizes(
        self, grid_region_id: str, marginal_key: str
    ) -> None:
        # Codebase region IDs (`JAVA_BALI`, …) must produce the same result
        # as the spec keys (`JAMALI`, …) once normalized.
        for tod in ("daytime", "nighttime"):
            assert estimate_marginal_cost(100.0, grid_region_id, tod) == (  # type: ignore[arg-type]
                estimate_marginal_cost(100.0, marginal_key, tod)  # type: ignore[arg-type]
            )

    def test_unknown_region_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown grid_region"):
            estimate_marginal_cost(100.0, "ATLANTIS", "daytime")

    def test_unknown_time_of_day_raises(self) -> None:
        with pytest.raises(ValueError, match="time_of_day"):
            estimate_marginal_cost(100.0, "JAMALI", "morning")  # type: ignore[arg-type]

    def test_nan_bpp_propagates(self) -> None:
        """NaN BPP → NaN marginal. Tests that sites with missing BPP don't
        silently get a spurious marginal cost."""
        result = estimate_marginal_cost(math.nan, "JAMALI", "daytime")
        assert math.isnan(result)

    def test_zero_bpp_returns_zero(self) -> None:
        """Zero BPP × factor = 0; sanity check on the multiplication."""
        assert estimate_marginal_cost(0.0, "JAMALI", "daytime") == 0.0

    def test_negative_bpp_passes_through(self) -> None:
        """Negative BPP shouldn't happen, but the function should mirror the
        input sign rather than swallowing it — caller is responsible for
        BPP validation."""
        assert estimate_marginal_cost(-50.0, "JAMALI", "daytime") == pytest.approx(-55.0)


class TestRegionToMarginalKey:
    @pytest.mark.parametrize(
        "grid_region_id,expected_key",
        [
            ("JAVA_BALI", "JAMALI"),
            ("NTB", "JAMALI"),
            ("SUMATERA", "Sumatera"),
            ("KALIMANTAN", "Kalimantan"),
            ("SULAWESI", "Sulawesi"),
            ("MALUKU", "Maluku_Papua"),
            ("PAPUA", "Maluku_Papua"),
        ],
    )
    def test_known_mappings(self, grid_region_id: str, expected_key: str) -> None:
        assert region_to_marginal_key(grid_region_id) == expected_key

    def test_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError, match="Unknown grid_region"):
            region_to_marginal_key("ATLANTIS")


class TestMarginalConfidence:
    @pytest.mark.parametrize(
        "region,expected",
        [
            ("JAMALI", "jamali_coal_dominant"),
            ("Sumatera", "mixed_dispatch"),
            ("Kalimantan", "diesel_peaking"),
            ("Sulawesi", "diesel_peaking"),
            ("Maluku_Papua", "remote_diesel_dominated"),
        ],
    )
    def test_spec_keys(self, region: str, expected: str) -> None:
        assert marginal_confidence_for(region) == expected

    def test_codebase_id_normalizes(self) -> None:
        # JAVA_BALI → JAMALI → jamali_coal_dominant
        assert marginal_confidence_for("JAVA_BALI") == "jamali_coal_dominant"
        # PAPUA → Maluku_Papua → remote_diesel_dominated
        assert marginal_confidence_for("PAPUA") == "remote_diesel_dominated"

    def test_all_five_regions_have_confidence(self) -> None:
        """Pin the §6.3 confidence table; one entry per dispatch region."""
        assert set(MARGINAL_CONFIDENCE_BY_REGION.keys()) == set(
            MARGINAL_COST_ADJUSTMENT_BY_REGION.keys()
        )

    def test_unknown_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            marginal_confidence_for("ATLANTIS")


class TestDaytimeHourDefinition:
    """The module docstring locks in the PVOUT-weighted daytime hour
    definition per eng-review finding A6. This test pins that the docstring
    contains the canonical statement so it doesn't drift."""

    def test_module_docstring_mentions_pvout_weighted_window(self) -> None:
        from src.dash.logic import marginal

        doc = marginal.__doc__ or ""
        assert "PVOUT-weighted" in doc
        assert "06:00" in doc
        assert "18:00" in doc
