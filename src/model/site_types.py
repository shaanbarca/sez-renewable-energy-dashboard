# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
Site type registry — the single source of truth for per-type behavior.

Adding a new site type = adding one dict entry to SITE_TYPES.
No other file needs modification for type-specific behavior.

Design: frozen dataclass + dict dispatch, following the RESource pattern
in basic_model.py. StrEnums follow the ActionFlag / EconomicTier pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class SiteType(StrEnum):
    """Discriminator for industrial site categories."""

    KEK = "kek"
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    KI = "ki"


class Sector(StrEnum):
    """Industrial sector for CBAM exposure and demand estimation."""

    STEEL = "steel"
    CEMENT = "cement"
    ALUMINIUM = "aluminium"
    FERTILIZER = "fertilizer"
    NICKEL = "nickel"
    MIXED = "mixed"


@dataclass(frozen=True)
class SiteTypeConfig:
    """Everything that differs between site types. One entry = one type.

    Adding a new site type = adding one dict entry to SITE_TYPES below.
    Pipeline modules import SITE_TYPES and dispatch on config fields,
    so no if/elif chains are needed in business logic.
    """

    demand_method: Literal["area_based", "sector_intensity"]
    captive_power_method: Literal["proximity", "direct"]
    cbam_method: Literal["3_signal", "direct"]
    default_reliability: float
    marker_shape: str  # "circle", "diamond", "hexagon", "square"
    identity_fields: tuple[str, ...] = ()  # columns shown in ScoreDrawer identity section


SITE_TYPES: dict[SiteType, SiteTypeConfig] = {
    SiteType.KEK: SiteTypeConfig(
        demand_method="area_based",
        captive_power_method="proximity",
        cbam_method="3_signal",
        default_reliability=0.75,
        marker_shape="circle",
        identity_fields=(
            "zone_classification",
            "category",
            "developer",
            "legal_basis",
            "area_ha",
        ),
    ),
    SiteType.STANDALONE: SiteTypeConfig(
        demand_method="sector_intensity",
        captive_power_method="direct",
        cbam_method="direct",
        default_reliability=0.90,
        marker_shape="diamond",
        identity_fields=(
            "primary_product",
            "technology",
            "capacity_annual",
            "parent_company",
        ),
    ),
    SiteType.CLUSTER: SiteTypeConfig(
        demand_method="sector_intensity",
        captive_power_method="direct",
        cbam_method="direct",
        default_reliability=0.85,
        marker_shape="hexagon",
        identity_fields=(
            "primary_product",
            "cluster_members",
            "capacity_annual",
            "parent_company",
        ),
    ),
    SiteType.KI: SiteTypeConfig(
        demand_method="area_based",
        captive_power_method="proximity",
        cbam_method="direct",
        default_reliability=0.80,
        marker_shape="square",
        identity_fields=("sector", "area_ha", "developer"),
    ),
}
