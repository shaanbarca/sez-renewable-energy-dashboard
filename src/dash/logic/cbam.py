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
    CBAM_SCOPE_2_PRICED,
    SCOPE1_ABATEMENT_METHODOLOGY_NOTE,
    SCOPE1_ABATEMENT_PATHWAYS_BY_PRODUCT,
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
        out["cbam_scope_2_priced"] = None  # #63 — null for non-CBAM-exposed sites
        for year in [2026, 2030, 2034]:
            out[f"cbam_cost_{year}_usd_per_tonne"] = None
            out[f"cbam_savings_{year}_usd_per_tonne"] = None
        # F9: Scope 1 abatement flags — null for non-CBAM-exposed sites
        out["scope1_abatement_pathways"] = None
        out["scope1_abatement_indicative_addressable_pct"] = None
        out["scope1_abatement_methodology_note"] = None
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
        # #63 (v4.0.7) — EU Implementing Reg 2025/2547 sectoral split. Cement +
        # fertilizer (incl. ammonia) price Scope 1 + Scope 2. Steel / aluminium /
        # hydrogen price Scope 1 only in the initial definitive phase. Defaults
        # to True for unknown ctypes (conservative — keeps pre-v4.0.7 behavior
        # if a new sector lands without an explicit entry).
        scope_2_priced = CBAM_SCOPE_2_PRICED.get(ctype, True)
        priced_ei = scope1 + (scope2 if scope_2_priced else 0)
        # Reported emission intensity always includes Scope 2 (the reg requires
        # Scope 2 reporting even where it isn't priced). Use this for the
        # "current intensity" disclosure; gate the priced cost separately.
        reported_ei = scope1 + scope2

        metrics: dict = {
            "emission_intensity_current": round(reported_ei, 1),
            "emission_intensity_solar": round(scope1, 1),
            "scope_2_priced": scope_2_priced,
        }
        for year in [2026, 2030, 2034]:
            free_alloc = CBAM_FREE_ALLOCATION.get(year, 0.0)
            effective_rate = price_usd * (1 - free_alloc)
            metrics[f"cost_{year}_usd_per_tonne"] = round(priced_ei * effective_rate, 0)
            # RE-addressable savings only flow into the CBAM bill when Scope 2 is
            # priced. For steel / aluminium / H₂ under current rules, RE-switching
            # delivers physical emission reductions but zero CBAM relief.
            re_savings = scope2_re_addressable if scope_2_priced else 0.0
            metrics[f"savings_{year}_usd_per_tonne"] = round(re_savings * effective_rate, 0)
        per_product[ctype] = metrics

    out["cbam_per_product"] = per_product
    primary = per_product[cbam_types[0]]
    out["cbam_emission_intensity_current"] = primary["emission_intensity_current"]
    out["cbam_emission_intensity_solar"] = primary["emission_intensity_solar"]
    # #63 (v4.0.7) — per-site Scope 2 pricing flag. Mirrors the primary product
    # type. Frontend uses this to render the sectoral status (and v4.3 M-AT7
    # transparency pattern can toggle a sensitivity scenario where this flips
    # True for all sectors, simulating an EU Scope 2 expansion).
    out["cbam_scope_2_priced"] = primary["scope_2_priced"]
    for year in [2026, 2030, 2034]:
        out[f"cbam_cost_{year}_usd_per_tonne"] = primary[f"cost_{year}_usd_per_tonne"]
        out[f"cbam_savings_{year}_usd_per_tonne"] = primary[f"savings_{year}_usd_per_tonne"]

    # F9 (2026-05-07): qualitative Scope 1 abatement pathway flags. Surfaces
    # non-RE pathways (alt fuels, green-H2 DRI, electric kilns, SCM, inert
    # anodes) so the dashboard's RE-addressable ceiling isn't read as a hard
    # static limit. Cost modeling deferred to v5.x. Uses the PRIMARY product
    # type's pathways — for sites with multiple CBAM products (rare), the
    # primary type drives the badge. METHODOLOGY §14.2 / §14.3.
    primary_type = cbam_types[0]
    pathways, addressable_pct = SCOPE1_ABATEMENT_PATHWAYS_BY_PRODUCT.get(primary_type, ("", 0.0))
    out["scope1_abatement_pathways"] = pathways if pathways else None
    out["scope1_abatement_indicative_addressable_pct"] = (
        round(addressable_pct, 2) if pathways else None
    )
    out["scope1_abatement_methodology_note"] = (
        SCOPE1_ABATEMENT_METHODOLOGY_NOTE if pathways else None
    )
    return out


# ─── v4.1b: Destination-weighted CBAM (spec §7.2 + §7.3) ───────────────────
#
# The v4.1a baseline computes per-tonne CBAM cost as if 100% of every CBAM-
# product site's output goes to the EU. For Indonesian nickel that's a 4×
# error (~$9/t effective vs $35/t destination-weighted today, $70/t by 2030
# per spec §7.1).
#
# This layer is additive: it doesn't touch compute_cbam_trajectory (the
# per-tonne function above stays as a legacy column). It emits 9 new
# per-MWh incumbent-cost-adjusted columns into the scorecard schema.


def compute_destination_weighted_carbon_adder(
    emissions_intensity_t_co2_per_mwh: float,
    export_market_shares: dict[str, float],
    carbon_price_by_market: dict[str, dict[int, float]],
    year: int,
) -> float:
    """Compute the effective carbon adder per MWh for a site, weighted by
    export markets. Per spec §7.2.

    ``effective_carbon_price = Σ (share[market] × price[market, year])``
    Then ``carbon_adder = emissions_intensity × effective_carbon_price``.

    Units: $/tCO2 × tCO2/MWh = $/MWh.

    Year interpolation: if ``year`` is not a snapshot in the price dict,
    linearly interpolates between adjacent snapshots (spec §3.5).
    """
    effective_price = 0.0
    for market_id, share in export_market_shares.items():
        trajectory = carbon_price_by_market.get(market_id)
        if trajectory is None:
            continue
        price = _interpolate_carbon_price(trajectory, year)
        effective_price += share * price
    return emissions_intensity_t_co2_per_mwh * effective_price


def compute_destination_weighted_incumbent(
    base_incumbent_cost_usd_mwh: float,
    emissions_intensity_t_co2_per_mwh: float,
    export_market_shares: dict[str, float],
    carbon_price_by_market: dict[str, dict[int, float]],
    year: int,
) -> float:
    """Base incumbent + destination-weighted carbon adder. Per spec §7.2.

    The "incumbent" base is whatever the site is comparing solar against —
    grid cost (BPP / industrial tariff) for grid-connected sites, captive
    coal/gas LCOE for captive sites. v4.1b uses grid_cost as the universal
    base; the per-arrangement comparator is v4.3 work (#91).
    """
    adder = compute_destination_weighted_carbon_adder(
        emissions_intensity_t_co2_per_mwh,
        export_market_shares,
        carbon_price_by_market,
        year,
    )
    return base_incumbent_cost_usd_mwh + adder


def _interpolate_carbon_price(trajectory: dict[int, float], year: int) -> float:
    """Linearly interpolate price between snapshot years per spec §3.5.

    If ``year`` is below the first snapshot, returns the first snapshot value
    (constant extrapolation). Above the last snapshot, returns the last value.
    """
    if year in trajectory:
        return float(trajectory[year])
    years = sorted(trajectory.keys())
    if not years:
        return 0.0
    if year <= years[0]:
        return float(trajectory[years[0]])
    if year >= years[-1]:
        return float(trajectory[years[-1]])
    # Find bracketing snapshots
    for i in range(len(years) - 1):
        y_lo, y_hi = years[i], years[i + 1]
        if y_lo <= year <= y_hi:
            p_lo, p_hi = trajectory[y_lo], trajectory[y_hi]
            t = (year - y_lo) / (y_hi - y_lo)
            return float(p_lo + t * (p_hi - p_lo))
    return float(trajectory[years[-1]])


def resolve_export_shares(
    site_id: str,
    cbam_product_type: str | None,
    overrides: dict[str, dict[str, float]],
    sector_defaults: dict[str, dict[str, float]],
    process_to_subsector: dict[str, str],
) -> tuple[dict[str, float], str]:
    """Resolve a site's export market shares per the 3-layer fallback
    (locked decision 2A from /plan-eng-review 2026-05-21).

    Returns ``(shares_dict, provenance_source)`` where provenance is one of:
      - ``'site_override'`` — site_id matched in fct_site_export_shares_overrides
      - ``'sector_default'`` — fell through to SECTOR_EXPORT_MIX_DEFAULTS via
        PROCESS_TO_SUBSECTOR mapping
      - ``'eu_fallback'`` — last resort: 100% direct_eu_uk_us (matches v4.1a
        baseline behavior)
    """
    if site_id in overrides:
        return overrides[site_id], "site_override"
    if cbam_product_type:
        subsector = process_to_subsector.get(cbam_product_type)
        if subsector and subsector in sector_defaults:
            return sector_defaults[subsector], "sector_default"
    return {"direct_eu_uk_us": 1.0}, "eu_fallback"


# Stress-test variants per spec §7.3. Each is a fixed share distribution:
#   - "full":       100% direct_eu_uk_us (what v4.1a implicitly assumed)
#   - "china_only": 100% china_stainless (lower-bound for nickel-RKEF dominant)
_FULL_EU_SHARES: dict[str, float] = {"direct_eu_uk_us": 1.0}
_CHINA_ONLY_SHARES: dict[str, float] = {"china_stainless": 1.0}


def compute_destination_weighted_incumbent_columns(
    *,
    base_incumbent_usd_mwh: float,
    emissions_intensity_t_co2_per_mwh: float,
    export_market_shares: dict[str, float],
    carbon_price_by_market: dict[str, dict[int, float]],
    years: tuple[int, ...] = (2025, 2030, 2034),
) -> dict[str, float]:
    """Compute all 9 v4.1b CBAM incumbent columns per spec §7.3.

    Returns dict with keys:
      cbam_destination_weighted_incumbent_{year}_usd_mwh — realistic exposure
      cbam_full_incumbent_{year}_usd_mwh                 — 100% EU stress
      cbam_china_only_incumbent_{year}_usd_mwh           — 100% China stress
    """
    out: dict[str, float] = {}
    for year in years:
        out[f"cbam_destination_weighted_incumbent_{year}_usd_mwh"] = round(
            compute_destination_weighted_incumbent(
                base_incumbent_usd_mwh,
                emissions_intensity_t_co2_per_mwh,
                export_market_shares,
                carbon_price_by_market,
                year,
            ),
            2,
        )
        out[f"cbam_full_incumbent_{year}_usd_mwh"] = round(
            compute_destination_weighted_incumbent(
                base_incumbent_usd_mwh,
                emissions_intensity_t_co2_per_mwh,
                _FULL_EU_SHARES,
                carbon_price_by_market,
                year,
            ),
            2,
        )
        out[f"cbam_china_only_incumbent_{year}_usd_mwh"] = round(
            compute_destination_weighted_incumbent(
                base_incumbent_usd_mwh,
                emissions_intensity_t_co2_per_mwh,
                _CHINA_ONLY_SHARES,
                carbon_price_by_market,
                year,
            ),
            2,
        )
    return out
