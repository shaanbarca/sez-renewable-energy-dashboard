# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""EU CBAM exposure detection and cost trajectory.

`_detect_cbam_types` dispatches on `site_type`: KEKs use 3-signal inference
(nickel process + plant counts + business sectors); standalone/cluster sites
read `cbam_product_type` straight from dim_sites. `compute_cbam_trajectory`
derives emission intensity and 2026/2030/2034 cost trajectory given a list
of detected types.
"""

from __future__ import annotations

import pandas as pd

from src.assumptions import (
    CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE,
    CBAM_FREE_ALLOCATION,
    CBAM_RE_ADDRESSABLE_FRACTION,
    CBAM_SCOPE1_TCO2_PER_TONNE,
)
from src.model.site_types import SITE_TYPES, SiteType

_SECTOR_CBAM_MAP: dict[str, str] = {
    "Base Metal Industry": "nickel_rkef",
    "Nickel Smelter Industry": "nickel_rkef",
    "Bauxite Industry": "aluminium",
    "Petrochemical Industry": "fertilizer",
    "Cement Industry": "cement",
}

# Raw cbam_product_type values in dim_sites (e.g., "iron_steel") map to
# technology-specific cost-model keys (e.g., "steel_eaf", "steel_bfbof", "nickel_rkef")
# using the site's `technology` column for disambiguation.
_NICKEL_TECHS = {"RKEF", "HPAL", "FERRO NICKEL", "NPI", "NICKEL PIG IRON"}


def _normalize_cbam_type(raw: str, technology: str) -> str | None:
    """Normalize dim_sites cbam_product_type to a cost-model key. Returns None if unknown."""
    raw = raw.strip().lower()
    tech = technology.strip().upper()
    if not raw:
        return None
    if raw == "iron_steel":
        if tech in _NICKEL_TECHS:
            return "nickel_rkef"
        if tech == "BF-BOF":
            return "steel_bfbof"
        return "steel_eaf"
    return raw


def _detect_cbam_types(kek: pd.Series, row: dict) -> list[str]:
    """Return CBAM product-type keys for a site.

    KEK/KI sites use 3-signal detection (nickel process + plant counts + business sectors).
    Standalone/cluster sites use the cbam_product_type column from dim_sites directly.
    """
    site_type_raw = str(kek.get("site_type") or "kek").lower()
    try:
        site_type = SiteType(site_type_raw)
    except ValueError:
        site_type = SiteType.KEK
    cbam_method = SITE_TYPES[site_type].cbam_method

    if cbam_method == "direct":
        raw_val = kek.get("cbam_product_type")
        if raw_val is None or (isinstance(raw_val, float) and pd.isna(raw_val)):
            return []
        raw = str(raw_val).strip()
        if not raw or raw.lower() == "nan":
            return []
        tech_val = kek.get("technology")
        technology = (
            ""
            if tech_val is None or (isinstance(tech_val, float) and pd.isna(tech_val))
            else str(tech_val)
        )
        types: list[str] = []
        for part in raw.split(","):
            normalized = _normalize_cbam_type(part, technology)
            if normalized and normalized not in types:
                types.append(normalized)
        return types

    cbam_types: list[str] = []

    process = str(row.get("dominant_process_type") or "").strip()
    if process in {"Nickel Pig Iron", "Ferro Nickel"}:
        cbam_types.append("nickel_rkef")

    steel_count = kek.get("steel_plant_count")
    if pd.notna(steel_count) and int(steel_count) > 0:
        steel_tech = str(kek.get("steel_dominant_technology") or "").strip()
        if steel_tech == "BF-BOF":
            if "steel_bfbof" not in cbam_types:
                cbam_types.append("steel_bfbof")
        elif "steel_eaf" not in cbam_types:
            cbam_types.append("steel_eaf")

    cement_count = kek.get("cement_plant_count")
    if pd.notna(cement_count) and int(cement_count) > 0 and "cement" not in cbam_types:
        cbam_types.append("cement")

    sectors_str = str(kek.get("business_sectors") or "")
    for sector_name, cbam_type in _SECTOR_CBAM_MAP.items():
        if sector_name in sectors_str and cbam_type not in cbam_types:
            cbam_types.append(cbam_type)

    return cbam_types


def compute_cbam_trajectory(
    cbam_types: list[str],
    grid_ef_t_co2_mwh: float | None,
    cbam_price_eur: float,
    eur_usd_rate: float,
) -> dict:
    """Compute CBAM cost trajectory (2026, 2030, 2034) for a site.

    Returns a dict with all cbam_* fields to merge into the scorecard row:
    cbam_exposed, cbam_product_type (comma-joined), cbam_per_product (per-type
    breakdown), cbam_emission_intensity_current/solar, and
    cbam_cost/savings_{2026,2030,2034}_usd_per_tonne.

    When ``cbam_types`` is empty, all numeric fields are set to None.
    """
    out: dict = {
        "cbam_exposed": len(cbam_types) > 0,
        "cbam_product_type": ",".join(cbam_types) if cbam_types else None,
    }

    if not cbam_types:
        out["cbam_per_product"] = None
        out["cbam_emission_intensity_current"] = None
        out["cbam_emission_intensity_solar"] = None
        for year in [2026, 2030, 2034]:
            out[f"cbam_cost_{year}_usd_per_tonne"] = None
            out[f"cbam_savings_{year}_usd_per_tonne"] = None
        return out

    grid_ef = grid_ef_t_co2_mwh or 0.8  # fallback: Indonesia avg
    price_usd = cbam_price_eur * eur_usd_rate

    per_product: dict[str, dict] = {}
    for ctype in cbam_types:
        elec_intensity = CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE.get(ctype, 0)
        scope1 = CBAM_SCOPE1_TCO2_PER_TONNE.get(ctype, 0)
        re_fraction = CBAM_RE_ADDRESSABLE_FRACTION.get(ctype, 1.0)
        scope2 = elec_intensity * grid_ef
        scope2_re_addressable = scope2 * re_fraction
        total_ei = scope2 + scope1

        metrics: dict = {
            "emission_intensity_current": round(total_ei, 1),
            "emission_intensity_solar": round(scope1, 1),
        }
        for year in [2026, 2030, 2034]:
            free_alloc = CBAM_FREE_ALLOCATION.get(year, 0.0)
            effective_rate = price_usd * (1 - free_alloc)
            metrics[f"cost_{year}_usd_per_tonne"] = round(total_ei * effective_rate, 0)
            metrics[f"savings_{year}_usd_per_tonne"] = round(
                scope2_re_addressable * effective_rate, 0
            )
        per_product[ctype] = metrics

    out["cbam_per_product"] = per_product
    primary = per_product[cbam_types[0]]
    out["cbam_emission_intensity_current"] = primary["emission_intensity_current"]
    out["cbam_emission_intensity_solar"] = primary["emission_intensity_solar"]
    for year in [2026, 2030, 2034]:
        out[f"cbam_cost_{year}_usd_per_tonne"] = primary[f"cost_{year}_usd_per_tonne"]
        out[f"cbam_savings_{year}_usd_per_tonne"] = primary[f"savings_{year}_usd_per_tonne"]
    return out
