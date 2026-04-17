"""
tests/test_demand_intensity.py — sector-based demand estimation tests.

Covers:
  - Steel EAF demand calculation
  - Cement demand calculation
  - Aluminium demand calculation (highest intensity)
  - Unknown sector raises KeyError
  - Zero capacity returns zero
  - Technology-specific lookup (BF-BOF vs EAF)
  - RKEF vs HPAL nickel intensity
"""

from __future__ import annotations

import pytest

from src.pipeline.demand_intensity import (
    estimate_demand_sector_intensity,
    get_intensity_key,
)


class TestDemandEstimation:
    def test_steel_eaf_demand(self):
        """4M TPA × 0.50 MWh/t = 2,000,000 MWh."""
        result = estimate_demand_sector_intensity(4_000_000, "steel", "EAF")
        assert result == pytest.approx(2_000_000.0)

    def test_steel_bfbof_demand(self):
        """3M TPA × 0.20 MWh/t = 600,000 MWh."""
        result = estimate_demand_sector_intensity(3_000_000, "steel", "BF-BOF")
        assert result == pytest.approx(600_000.0)

    def test_cement_demand(self):
        """10M TPA × 0.11 MWh/t = 1,100,000 MWh."""
        result = estimate_demand_sector_intensity(10_000_000, "cement")
        assert result == pytest.approx(1_100_000.0)

    def test_aluminium_demand(self):
        """250K TPA × 15.0 MWh/t = 3,750,000 MWh."""
        result = estimate_demand_sector_intensity(250_000, "aluminium")
        assert result == pytest.approx(3_750_000.0)

    def test_fertilizer_demand(self):
        """2.4M TPA × 1.0 MWh/t = 2,400,000 MWh."""
        result = estimate_demand_sector_intensity(2_400_000, "fertilizer")
        assert result == pytest.approx(2_400_000.0)

    def test_nickel_rkef_demand(self):
        """60K TPA × 37.5 MWh/t = 2,250,000 MWh."""
        result = estimate_demand_sector_intensity(60_000, "nickel", "RKEF")
        assert result == pytest.approx(2_250_000.0)

    def test_nickel_hpal_demand(self):
        """60K TPA × 8.0 MWh/t = 480,000 MWh."""
        result = estimate_demand_sector_intensity(60_000, "nickel", "HPAL")
        assert result == pytest.approx(480_000.0)

    def test_unknown_sector_raises(self):
        with pytest.raises(KeyError, match="Unknown sector"):
            estimate_demand_sector_intensity(1_000, "petrochemical")

    def test_zero_capacity_returns_zero(self):
        assert estimate_demand_sector_intensity(0, "steel") == 0.0

    def test_negative_capacity_returns_zero(self):
        assert estimate_demand_sector_intensity(-100, "cement") == 0.0

    def test_steel_no_tech_defaults_to_eaf(self):
        """Without technology, steel defaults to EAF (conservative: higher intensity)."""
        result = estimate_demand_sector_intensity(1_000_000, "steel")
        eaf_result = estimate_demand_sector_intensity(1_000_000, "steel", "EAF")
        assert result == eaf_result


class TestIntensityKeyResolution:
    def test_sector_tech_lookup(self):
        assert get_intensity_key("steel", "EAF") == "steel_eaf"
        assert get_intensity_key("steel", "BF-BOF") == "steel_bfbof"
        assert get_intensity_key("nickel", "RKEF") == "nickel_rkef"
        assert get_intensity_key("nickel", "HPAL") == "nickel_hpal"

    def test_sector_only_fallback(self):
        assert get_intensity_key("cement") == "cement"
        assert get_intensity_key("aluminium") == "aluminium"
        assert get_intensity_key("fertilizer") == "fertilizer"

    def test_unknown_tech_falls_back_to_sector(self):
        """Unknown technology should fall back to sector default."""
        assert get_intensity_key("steel", "DRI") == "steel_eaf"
