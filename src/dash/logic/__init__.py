# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Public API for src.dash.logic.

External callers (api routes, tests, notebooks) import from here. Internal
structure lives in sibling modules and may be reorganised without breaking
external imports.
"""

from src.dash.logic.assumptions import (
    UserAssumptions,
    UserThresholds,
    get_default_assumptions,
    get_default_thresholds,
)
from src.dash.logic.cbam import (
    _detect_cbam_types,
    _normalize_cbam_type,
)
from src.dash.logic.lcoe import (
    compute_lcoe_live,
    compute_lcoe_wind_live,
)
from src.dash.logic.scorecard import compute_scorecard_live

__all__ = [
    "UserAssumptions",
    "UserThresholds",
    "_detect_cbam_types",
    "_normalize_cbam_type",
    "compute_lcoe_live",
    "compute_lcoe_wind_live",
    "compute_scorecard_live",
    "get_default_assumptions",
    "get_default_thresholds",
]
