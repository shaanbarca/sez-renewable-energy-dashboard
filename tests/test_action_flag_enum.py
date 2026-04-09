"""Tests for the ActionFlag enum."""

from __future__ import annotations

from src.model.basic_model import ActionFlag


def test_action_flag_values():
    """ActionFlag members have expected string values."""
    assert ActionFlag.SOLAR_NOW == "solar_now"
    assert ActionFlag.INVEST_RESILIENCE == "invest_resilience"
    assert ActionFlag.GRID_FIRST == "grid_first"
    assert ActionFlag.FIRMING_NEEDED == "firming_needed"
    assert ActionFlag.PLAN_LATE == "plan_late"
    assert ActionFlag.NOT_COMPETITIVE == "not_competitive"


def test_action_flag_count():
    """There are exactly 6 action flags."""
    assert len(list(ActionFlag)) == 6


def test_action_flag_str_comparison():
    """StrEnum members compare equal to their string values."""
    assert ActionFlag.GRID_FIRST == "grid_first"
    assert "solar_now" in {f.value for f in ActionFlag}
    # Can be used as dict keys interchangeably with strings
    d = {ActionFlag.SOLAR_NOW: "green"}
    assert d["solar_now"] == "green"
