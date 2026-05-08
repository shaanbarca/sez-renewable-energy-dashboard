# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Geothermal adjacency tier + dispatchable-RE translator.

Single source of truth for two related questions:

1. ``geothermal_tier(operating_km, pipeline_km, pipeline_year)`` — which adjacency
   bucket a site falls into. Used by ``build_fct_geothermal_proximity`` and tests.

2. ``dispatchable_re_from_geothermal_tier(tier)`` — how the tier translates into
   the (coverage_pct, lcoe_usd_mwh) pair that the F1 Supply Blend cascade reads
   from ``dispatchable_re_coverage_pct`` / ``dispatchable_re_lcoe_usd_mwh``.

Why a translator. F1 (PR #17 batch / merged into v4.0.5) extended
``enrich_delivered_cost`` with a dispatchable-RE layer between within-boundary
solar and grid backfill, but reads from columns the pipeline didn't yet
populate. Until F2 lands, the cascade silently falls through to the v4.0
3-layer behaviour. This module is the activation gate.

Coverage assumptions (intentionally conservative for v4.0.5 — refine in
v4.1b/v5.0 once we have site-specific resource estimates and PSA-driven
sizing):

| Tier                                  | dispatchable_re_coverage_pct |
|---------------------------------------|------------------------------|
| ``operating_within_50km``             | 0.30 — within transmission gentie reach, dispatchable backbone |
| ``operating_within_200km``            | 0.15 — needs new transmission, partial reach |
| ``pipeline_within_200km_pre2030``     | 0.10 — planned within decision horizon |
| ``pipeline_within_200km_post2030``    | 0.0 — too late to factor into 2030 decarbonization decisions |
| ``none``                              | 0.0 |

LCOE: ESDM Technology Catalogue 2024 §1 Table 1.5 lists geothermal at roughly
$80–110/MWh (HT/LT split). We use $90/MWh as a fleet-mid PPA proxy until we
wire per-plant capacity-weighted LCOE in v5.0. This is intentionally simpler
than the solar live-LCOE machinery because the dispatchable-RE layer in F1
is a delivered-cost approximation, not a project-finance number.
"""

from __future__ import annotations

from typing import Final, Literal

GeothermalTier = Literal[
    "operating_within_50km",
    "operating_within_200km",
    "pipeline_within_200km_pre2030",
    "pipeline_within_200km_post2030",
    "none",
]

OPERATING_NEAR_KM: Final[float] = 50.0
OPERATING_FAR_KM: Final[float] = 200.0
PIPELINE_REACH_KM: Final[float] = 200.0
PIPELINE_DECISION_HORIZON_YEAR: Final[int] = 2030

# Tier → (coverage fraction, blended LCOE USD/MWh). See module docstring.
DISPATCHABLE_RE_COVERAGE_BY_TIER: Final[dict[str, float]] = {
    "operating_within_50km": 0.30,
    "operating_within_200km": 0.15,
    "pipeline_within_200km_pre2030": 0.10,
    "pipeline_within_200km_post2030": 0.0,
    "none": 0.0,
}

# Fleet-mid proxy from ESDM Tech Catalogue 2024 §1 Table 1.5 (geothermal HT/LT
# range ≈$80–110/MWh). Refine in v5.0 with per-plant capacity-weighted LCOE.
GEOTHERMAL_LCOE_USD_MWH_PROXY: Final[float] = 90.0


def geothermal_tier(
    operating_km: float | None,
    pipeline_km: float | None,
    pipeline_year: int | None,
) -> GeothermalTier:
    """Classify a site's geothermal adjacency.

    Operating plants are scored first because realised dispatchable RE > planned.
    Pipeline plants are bucketed by RUPTL target year vs the
    ``PIPELINE_DECISION_HORIZON_YEAR`` (2030) — projects landing post-2030 don't
    relieve a 2030 decarbonization decision.
    """
    if operating_km is not None and operating_km <= OPERATING_NEAR_KM:
        return "operating_within_50km"
    if operating_km is not None and operating_km <= OPERATING_FAR_KM:
        return "operating_within_200km"
    if pipeline_km is not None and pipeline_km <= PIPELINE_REACH_KM:
        if pipeline_year is not None and pipeline_year < PIPELINE_DECISION_HORIZON_YEAR:
            return "pipeline_within_200km_pre2030"
        return "pipeline_within_200km_post2030"
    return "none"


def dispatchable_re_from_geothermal_tier(
    tier: str | None,
    lcoe_usd_mwh: float = GEOTHERMAL_LCOE_USD_MWH_PROXY,
) -> tuple[float, float | None]:
    """Translate a geothermal adjacency tier into the F1 cascade inputs.

    Returns (``dispatchable_re_coverage_pct``, ``dispatchable_re_lcoe_usd_mwh``).
    Coverage is 0.0 when no useful adjacency; LCOE is ``None`` in that case so
    the F1 layer cleanly skips (avoids spurious zero-LCOE contribution).
    """
    if tier is None:
        return 0.0, None
    coverage = DISPATCHABLE_RE_COVERAGE_BY_TIER.get(tier, 0.0)
    if coverage <= 0.0:
        return 0.0, None
    return coverage, float(lcoe_usd_mwh)
