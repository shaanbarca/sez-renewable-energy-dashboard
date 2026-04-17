# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Import-shim test for the `src.dash.logic` package.

Verifies every symbol in the public `__all__` is reachable via the top-level
`src.dash.logic` module. Catches accidental removal of a re-export when
modules are split, renamed, or refactored further.
"""

from __future__ import annotations

import src.dash.logic as logic

EXPECTED_SYMBOLS = {
    "UserAssumptions",
    "UserThresholds",
    "_detect_cbam_types",
    "_normalize_cbam_type",
    "compute_lcoe_live",
    "compute_lcoe_wind_live",
    "compute_scorecard_live",
    "get_default_assumptions",
    "get_default_thresholds",
}


def test_all_declared() -> None:
    assert set(logic.__all__) == EXPECTED_SYMBOLS


def test_every_symbol_importable() -> None:
    for name in EXPECTED_SYMBOLS:
        assert hasattr(logic, name), f"src.dash.logic missing re-export: {name}"


def test_external_import_paths_work() -> None:
    """The exact imports used by api/routes and tests must resolve."""
    from src.dash.logic import (  # noqa: F401
        UserAssumptions,
        UserThresholds,
        compute_lcoe_live,
        compute_lcoe_wind_live,
        compute_scorecard_live,
        get_default_assumptions,
        get_default_thresholds,
    )
