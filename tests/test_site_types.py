"""
tests/test_site_types.py — SiteTypeConfig registry and StrEnum tests.

Covers:
  - All SiteType enum members have SITE_TYPES config entries
  - SiteTypeConfig is immutable (frozen dataclass)
  - Invalid SiteType values raise ValueError
  - Sector enum has all expected members
  - Each config has all required fields
"""

from __future__ import annotations

import pytest

from src.model.site_types import SITE_TYPES, Sector, SiteType, SiteTypeConfig


class TestSiteTypeEnum:
    def test_all_site_types_present(self):
        """Every SiteType enum member must have an entry in SITE_TYPES."""
        for st in SiteType:
            assert st in SITE_TYPES, f"SiteType.{st.name} missing from SITE_TYPES dict"

    def test_no_extra_keys(self):
        """SITE_TYPES should not have keys beyond the enum members."""
        for key in SITE_TYPES:
            assert key in SiteType.__members__.values(), f"Extra key '{key}' in SITE_TYPES"

    def test_invalid_site_type_raises(self):
        with pytest.raises(ValueError):
            SiteType("invalid_type")

    def test_site_type_string_values(self):
        assert SiteType.KEK == "kek"
        assert SiteType.STANDALONE == "standalone"
        assert SiteType.CLUSTER == "cluster"
        assert SiteType.KI == "ki"


class TestSectorEnum:
    def test_sector_enum_values(self):
        expected = {
            "steel",
            "cement",
            "aluminium",
            "fertilizer",
            "nickel",
            "ammonia",
            "petrochemical",
            "mixed",
        }
        actual = {s.value for s in Sector}
        assert actual == expected

    def test_invalid_sector_raises(self):
        with pytest.raises(ValueError):
            Sector("coal_mining")


class TestSiteTypeConfig:
    def test_config_immutable(self):
        """Frozen dataclass prevents mutation."""
        config = SITE_TYPES[SiteType.KEK]
        with pytest.raises(AttributeError):
            config.marker_shape = "triangle"  # type: ignore[misc]

    def test_each_config_has_required_fields(self):
        for st, config in SITE_TYPES.items():
            assert isinstance(config, SiteTypeConfig), f"{st}: not a SiteTypeConfig"
            assert config.demand_method in ("area_based", "sector_intensity"), (
                f"{st}: bad demand_method"
            )
            assert config.captive_power_method in ("proximity", "direct"), (
                f"{st}: bad captive_power_method"
            )
            assert config.cbam_method in ("3_signal", "direct"), f"{st}: bad cbam_method"
            assert 0 < config.default_reliability <= 1.0, f"{st}: reliability out of range"
            assert config.marker_shape in ("circle", "diamond", "hexagon", "square"), (
                f"{st}: bad marker_shape"
            )
            assert isinstance(config.identity_fields, tuple), f"{st}: identity_fields not tuple"
            assert len(config.identity_fields) > 0, f"{st}: empty identity_fields"

    def test_kek_uses_area_based_demand(self):
        assert SITE_TYPES[SiteType.KEK].demand_method == "area_based"

    def test_standalone_uses_sector_intensity(self):
        assert SITE_TYPES[SiteType.STANDALONE].demand_method == "sector_intensity"

    def test_kek_uses_proximity_captive_power(self):
        assert SITE_TYPES[SiteType.KEK].captive_power_method == "proximity"

    def test_standalone_uses_direct_captive_power(self):
        assert SITE_TYPES[SiteType.STANDALONE].captive_power_method == "direct"

    def test_kek_uses_3signal_cbam(self):
        assert SITE_TYPES[SiteType.KEK].cbam_method == "3_signal"

    def test_standalone_uses_direct_cbam(self):
        assert SITE_TYPES[SiteType.STANDALONE].cbam_method == "direct"
