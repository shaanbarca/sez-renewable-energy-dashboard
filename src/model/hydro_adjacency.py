# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Hydro adjacency tier — single source of truth for hydro proximity classification.

Mirrors ``src.model.geothermal_adjacency``. Used by:

1. ``build_fct_hydro_proximity`` — assigns each site a tier.
2. ``hybrid_lcoe_optimized_3way`` — gates hydro inclusion in the 2D solar × hydro
   sweep. Per spec §6A.4, hydro is available to the optimizer only when
   ``hydro_adjacency_tier ∈ {operating_within_50km, operating_within_200km,
   pipeline_within_200km_pre2030}``.

Pipeline-within-200km-post-2030 is intentionally excluded — projects landing
post-2030 do not relieve a 2030 decarbonization decision, the same logic
applied to geothermal.

Tier thresholds and rationale parallel geothermal exactly (see
``src.model.geothermal_adjacency`` module docstring) — the v4.1b spec §6A.3
chose this on purpose so the two adjacency models stay symmetric.
"""

from __future__ import annotations

from typing import Final, Literal

HydroTier = Literal[
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

# Tiers that make hydro available to the hybrid 2D optimizer.
# Per spec §6A.4: hydro is available only when adjacency_tier is in this set.
HYDRO_OPTIMIZER_ELIGIBLE_TIERS: Final[frozenset[str]] = frozenset(
    {
        "operating_within_50km",
        "operating_within_200km",
        "pipeline_within_200km_pre2030",
    }
)


def hydro_tier(
    operating_km: float | None,
    pipeline_km: float | None,
    pipeline_year: int | None,
) -> HydroTier:
    """Classify a site's hydro adjacency.

    Operating plants score first because realised dispatchable RE > planned.
    Pipeline plants are bucketed by RUPTL target year vs the
    ``PIPELINE_DECISION_HORIZON_YEAR`` (2030) — projects landing post-2030
    don't relieve a 2030 decarbonization decision.
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


def is_optimizer_eligible(tier: str | None) -> bool:
    """True if the tier admits hydro into the hybrid 2D optimizer sweep.

    Per spec §6A.4 gating logic — post-2030 pipeline projects and 'none'
    return False; everything else returns True.
    """
    return tier in HYDRO_OPTIMIZER_ELIGIBLE_TIERS
