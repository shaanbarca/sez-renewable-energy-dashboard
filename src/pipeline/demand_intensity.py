# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
demand_intensity — sector-based electricity demand estimation for industrial sites.

For standalone plants and clusters, demand = capacity_annual_tonnes × intensity.
For KEKs and KIs with area data, the existing area-based method is used instead.

This module is dispatched by SiteTypeConfig.demand_method:
    "sector_intensity" → estimate_demand_sector_intensity() (this module)
    "area_based"       → existing build_fct_site_demand logic

Sources:
    IEA Cement Roadmap 2018, worldsteel 2023, IAI 2023, IFA 2022, JETP Ch.2
    See SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE in src/assumptions.py for values.
"""

from __future__ import annotations

from src.assumptions import SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE

# Map (sector, technology) → intensity key in SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE.
# Falls back to sector-only lookup if technology doesn't match.
_SECTOR_TECH_KEY: dict[tuple[str, str], str] = {
    ("steel", "EAF"): "steel_eaf",
    ("steel", "BF-BOF"): "steel_bfbof",
    ("nickel", "RKEF"): "nickel_rkef",
    ("nickel", "HPAL"): "nickel_hpal",
}

# Default key when technology is unknown or not sector-specific
_SECTOR_DEFAULT_KEY: dict[str, str] = {
    "steel": "steel_eaf",  # conservative: EAF is higher electricity per tonne
    "cement": "cement",
    "aluminium": "aluminium",
    "fertilizer": "fertilizer",
    "nickel": "nickel_rkef",  # conservative: RKEF is higher electricity per tonne
    "ammonia": "ammonia",
    "petrochemical": "petrochemical",
}


def get_intensity_key(sector: str, technology: str | None = None) -> str:
    """Resolve the lookup key into SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE.

    Tries (sector, technology) first, falls back to sector default.

    Raises
    ------
    KeyError
        If sector is not recognized.
    """
    if technology:
        key = _SECTOR_TECH_KEY.get((sector, technology))
        if key:
            return key

    if sector not in _SECTOR_DEFAULT_KEY:
        raise KeyError(
            f"Unknown sector '{sector}'. Valid sectors: {sorted(_SECTOR_DEFAULT_KEY.keys())}"
        )
    return _SECTOR_DEFAULT_KEY[sector]


def estimate_demand_sector_intensity(
    capacity_annual_tonnes: float,
    sector: str,
    technology: str | None = None,
) -> float:
    """Estimate annual electricity demand from production capacity and sector intensity.

    Parameters
    ----------
    capacity_annual_tonnes
        Annual production capacity in metric tonnes.
    sector
        Industrial sector (steel, cement, aluminium, fertilizer, nickel).
    technology
        Optional technology type (EAF, BF-BOF, RKEF, HPAL) for sector-specific lookup.

    Returns
    -------
    float
        Estimated annual electricity demand in MWh.
    """
    if capacity_annual_tonnes <= 0:
        return 0.0

    key = get_intensity_key(sector, technology)
    intensity = SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE[key]
    return capacity_annual_tonnes * intensity
