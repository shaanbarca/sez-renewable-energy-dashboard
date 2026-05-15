# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Captive power LCOE resolution (v4.3 M-AT8a).

Single resolver `resolve_captive_lcoe()` that returns the captive-power LCOE for
one site given its fuel type and the active fuel-price scenario. Replaces
v4.1a's separate `compute_captive_coal_lcoe()` + `compute_captive_gas_lcoe()`
+ `site_captive_*_lcoe()` helpers per `/plan-eng-review` finding 2A.

# Priority chain

    1. Per-site tier default from `data/raw/captive_power_lcoe_defaults.csv`
       (the T1/T2 anchors and T3 placeholders the methodology owns).
    2. Formula fallback for sites NOT in the CSV (uses
       `CAPTIVE_COAL_DEFAULTS` / `CAPTIVE_GAS_DEFAULTS` from `assumptions.py`
       with the active fuel-price scenario substituted in).
    3. None for sites with `fuel_type == 'none'` or unknown — the caller is
       expected to leave the scorecard column NULL.

Per-site tier defaults take priority over the formula because the methodology
treats them as load-bearing site-specific anchors. They're scenario-invariant
by design — Krakatau Posco at $62 reflects its vertically-integrated supply,
not the active coal-price slider (issue 3C in the eng-review).

# Fuel types

Four `captive_fuel_type` values are recognised:

    - `coal_subcritical` / `coal_supercritical` → coal path. Uses
      `CAPTIVE_COAL_PRICE_SCENARIOS` for fuel-price adjustment.
    - `natural_gas` → gas path. Uses `CAPTIVE_GAS_PRICE_SCENARIOS`.
    - `hydro` → flat `CAPTIVE_HYDRO_DEFAULT_USD_MWH` (no fuel-price sensitivity;
      Asahan hydroelectric — Inalum is the sole anchor).

Anything else (`none`, missing) returns `None`.

# LCOE formula (fallback only)

For coal and gas, when no CSV row exists:

    LCOE = fuel_component
         + variable_om_usd_mwh
         + (fixed_om_usd_per_kw_year / (HOURS_PER_YEAR × capacity_factor)) × 1000
         + capital_recovery_usd_mwh

with the fuel component computed differently per fuel:

    Coal: fuel_cost_usd_per_tonne / HHV_MMBTU_per_tonne × heat_rate_BTU_per_kWh / 1000
    Gas:  fuel_cost_usd_per_mmbtu                       × heat_rate_BTU_per_kWh / 1000

Hydro skips the formula and returns the flat default.

# Caching (4A)

`_load_defaults_cached()` uses `lru_cache(maxsize=1)` so the CSV loads once per
process. The frontend's live-recompute use case (M-AT8b — slider drag) calls
the resolver many times per second; caching the CSV keeps that <1ms per call.
Pure-function nature of the math means we don't need to cache the resolver
output itself.

# Test pinning (3A)

`test_captive_tier_values_match_methodology` asserts the per-anchor LCOE in the
CSV matches the methodology table — if anyone bumps a T1/T2 value, the test
fails with a diagnostic pointing at the spec.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd

from src.assumptions import (
    CAPTIVE_COAL_DEFAULTS,
    CAPTIVE_COAL_HHV_MMBTU_PER_TONNE,
    CAPTIVE_COAL_PRICE_SCENARIOS,
    CAPTIVE_GAS_DEFAULTS,
    CAPTIVE_GAS_PRICE_SCENARIOS,
    CAPTIVE_HYDRO_DEFAULT_USD_MWH,
    HOURS_PER_YEAR,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULTS_CSV_DEFAULT = REPO_ROOT / "data" / "raw" / "captive_power_lcoe_defaults.csv"

_COAL_FUEL_TYPES = frozenset({"coal_subcritical", "coal_supercritical"})
_GAS_FUEL_TYPES = frozenset({"natural_gas"})
_HYDRO_FUEL_TYPES = frozenset({"hydro"})

Tier = Literal["T1", "T2", "T3"]
FuelType = Literal["coal_subcritical", "coal_supercritical", "natural_gas", "hydro", "none"]

# Default scenario per fuel — used when caller passes scenario="default".
_DEFAULT_SCENARIO_BY_FUEL: dict[str, str] = {
    "coal_subcritical": "DMO",
    "coal_supercritical": "DMO",
    "natural_gas": "HGBT",
    "hydro": "n/a",
}


@dataclass(frozen=True)
class CaptiveLcoeResult:
    """The output of `resolve_captive_lcoe()` for one site.

    Attributes:
        lcoe_usd_mwh: The resolved LCOE. None when the site has no captive
            arrangement (fuel_type='none' or unrecognised).
        tier: T1/T2/T3 for sites in the defaults CSV; None for formula-only
            fallback sites (rare — they'd usually have at least a T3 placeholder).
        source_citation: Free-text citation. From the CSV's `source_citation`
            column for CSV-resolved sites; "formula fallback (CAPTIVE_*_DEFAULTS)"
            for sites not in the CSV.
        scenario_used: Which fuel-price scenario was applied. "n/a" for hydro
            sites and CSV-resolved sites (the CSV value is scenario-invariant).
            For formula-fallback sites: "DMO" / "HBA_2024" / "INTERNATIONAL"
            (coal) or "HGBT" / "MARKET" / "SPOT_LNG_JKM" (gas).
    """

    lcoe_usd_mwh: float | None
    tier: Tier | None
    source_citation: str
    scenario_used: str


@lru_cache(maxsize=1)
def _load_defaults_cached() -> pd.DataFrame:
    """Load the tier defaults CSV exactly once per process (4A).

    Returns an empty DataFrame with the right columns when the file is missing
    so fresh checkouts / unit tests can run without the data file in place.
    Call `_load_defaults_cached.cache_clear()` from a pytest fixture if you
    need to force a reload between tests.
    """
    if not DEFAULTS_CSV_DEFAULT.exists():
        return pd.DataFrame(
            columns=[
                "site_id",
                "archetype",
                "fuel_type",
                "tier",
                "default_lcoe_usd_mwh",
                "coal_cv_kcal_per_kg",
                "gas_pricing_regime",
                "boiler_tech",
                "cf_default",
                "source_citation",
            ]
        )
    return pd.read_csv(DEFAULTS_CSV_DEFAULT)


def load_captive_defaults(csv_path: Path | None = None) -> pd.DataFrame:
    """Public load function. Pass `csv_path` to override the default location
    (only used by tests that point at a fixture). The CACHE is bypassed when a
    non-default path is provided.
    """
    if csv_path is None or csv_path == DEFAULTS_CSV_DEFAULT:
        return _load_defaults_cached()
    return pd.read_csv(csv_path)


def _coal_fuel_component(fuel_cost_per_tonne: float) -> float:
    """$/MWh fuel cost for coal, given $/tonne input + default HHV + heat rate."""
    per_mmbtu = fuel_cost_per_tonne / CAPTIVE_COAL_HHV_MMBTU_PER_TONNE
    return per_mmbtu * CAPTIVE_COAL_DEFAULTS["heat_rate_btu_per_kwh"] / 1000.0


def _gas_fuel_component(fuel_cost_per_mmbtu: float) -> float:
    """$/MWh fuel cost for gas, given $/MMBtu input + default heat rate."""
    return fuel_cost_per_mmbtu * CAPTIVE_GAS_DEFAULTS["heat_rate_btu_per_kwh"] / 1000.0


def _fixed_om_per_mwh(fixed_om_per_kw_year: float, capacity_factor: float) -> float:
    """Convert fixed O&M from $/kW-year to $/MWh given the capacity factor."""
    return (fixed_om_per_kw_year / (HOURS_PER_YEAR * capacity_factor)) * 1000.0


def _formula_coal_lcoe(fuel_cost_per_tonne: float) -> float:
    """Coal LCOE from CAPTIVE_COAL_DEFAULTS with substituted fuel price."""
    d = CAPTIVE_COAL_DEFAULTS
    return (
        _coal_fuel_component(fuel_cost_per_tonne)
        + d["variable_om_usd_mwh"]
        + _fixed_om_per_mwh(d["fixed_om_usd_per_kw_year"], d["capacity_factor"])
        + d["capital_recovery_usd_mwh"]
    )


def _formula_gas_lcoe(fuel_cost_per_mmbtu: float) -> float:
    """Gas LCOE from CAPTIVE_GAS_DEFAULTS with substituted fuel price."""
    d = CAPTIVE_GAS_DEFAULTS
    return (
        _gas_fuel_component(fuel_cost_per_mmbtu)
        + d["variable_om_usd_mwh"]
        + _fixed_om_per_mwh(d["fixed_om_usd_per_kw_year"], d["capacity_factor"])
        + d["capital_recovery_usd_mwh"]
    )


def _resolve_scenario_fuel_price(fuel_type: str, fuel_price_scenario: str) -> tuple[float, str]:
    """Return (fuel_price_value, scenario_label_used).

    For named scenarios, looks up the dict. For "default", picks DMO for coal /
    HGBT for gas. For any other string, attempts to parse as a custom numeric
    user value (M-AT8b slider input).
    """
    if fuel_price_scenario == "default":
        fuel_price_scenario = _DEFAULT_SCENARIO_BY_FUEL[fuel_type]

    if fuel_type in _COAL_FUEL_TYPES:
        if fuel_price_scenario in CAPTIVE_COAL_PRICE_SCENARIOS:
            return CAPTIVE_COAL_PRICE_SCENARIOS[fuel_price_scenario], fuel_price_scenario
        # Custom numeric user input (M-AT8b slider).
        try:
            return float(fuel_price_scenario), f"custom_{fuel_price_scenario}"
        except ValueError as exc:
            raise ValueError(
                f"Unknown coal fuel_price_scenario: {fuel_price_scenario!r}. "
                f"Expected one of {sorted(CAPTIVE_COAL_PRICE_SCENARIOS)} or a "
                f"numeric $/tonne value."
            ) from exc

    if fuel_type in _GAS_FUEL_TYPES:
        if fuel_price_scenario in CAPTIVE_GAS_PRICE_SCENARIOS:
            return CAPTIVE_GAS_PRICE_SCENARIOS[fuel_price_scenario], fuel_price_scenario
        try:
            return float(fuel_price_scenario), f"custom_{fuel_price_scenario}"
        except ValueError as exc:
            raise ValueError(
                f"Unknown gas fuel_price_scenario: {fuel_price_scenario!r}. "
                f"Expected one of {sorted(CAPTIVE_GAS_PRICE_SCENARIOS)} or a "
                f"numeric $/MMBtu value."
            ) from exc

    raise ValueError(f"Cannot resolve scenario for fuel_type={fuel_type!r}")


def resolve_captive_lcoe(
    site_id: str,
    fuel_type: str | None,
    fuel_price_scenario: str = "default",
    defaults_df: pd.DataFrame | None = None,
) -> CaptiveLcoeResult | None:
    """Resolve captive LCOE for one site, including tier + scenario metadata.

    Returns None when the site is not captive (`fuel_type` is None / "none"
    or unrecognised). Callers should leave scorecard columns NULL in that case.

    Priority chain:
        1. Site has a row in captive_power_lcoe_defaults.csv → return the
           CSV value verbatim (scenario-invariant — anchor values reflect
           site-specific economics that don't track market scenarios).
        2. Site is captive but absent from the CSV → return formula output
           computed against the active fuel-price scenario.

    Parameters
    ----------
    site_id:
        Kebab-case site_id matching dim_sites.csv.
    fuel_type:
        One of coal_subcritical / coal_supercritical / natural_gas / hydro
        (or None / "none" / unknown → returns None).
    fuel_price_scenario:
        Named scenario or numeric custom value. Defaults to "default" which
        picks DMO for coal and HGBT for gas. Hydro ignores this.
    defaults_df:
        Optional preloaded CSV DataFrame. Mostly for tests; production code
        relies on the LRU cache.
    """
    if not isinstance(fuel_type, str) or fuel_type == "none":
        return None

    df = defaults_df if defaults_df is not None else _load_defaults_cached()

    # Hydro short-circuit (1D + 4A) — flat default, no scenario sensitivity.
    if fuel_type in _HYDRO_FUEL_TYPES:
        match = df[df["site_id"] == site_id] if not df.empty else df
        if not match.empty:
            row = match.iloc[0]
            return CaptiveLcoeResult(
                lcoe_usd_mwh=float(row["default_lcoe_usd_mwh"]),
                tier=row["tier"] if pd.notna(row["tier"]) else None,
                source_citation=str(row["source_citation"]),
                scenario_used="n/a",
            )
        # Hydro site absent from CSV — fall back to flat default. Rare.
        return CaptiveLcoeResult(
            lcoe_usd_mwh=CAPTIVE_HYDRO_DEFAULT_USD_MWH,
            tier=None,
            source_citation="hydro default (CAPTIVE_HYDRO_DEFAULT_USD_MWH)",
            scenario_used="n/a",
        )

    # Coal + gas paths: try CSV first, fall back to formula.
    if fuel_type in _COAL_FUEL_TYPES or fuel_type in _GAS_FUEL_TYPES:
        match = df[df["site_id"] == site_id] if not df.empty else df
        if not match.empty:
            row = match.iloc[0]
            # Sanity: the CSV row's fuel_type should match the caller's claim.
            csv_fuel = str(row["fuel_type"]) if pd.notna(row["fuel_type"]) else None
            if csv_fuel and csv_fuel != fuel_type:
                # Disagreement — prefer the CSV's authoritative fuel_type
                # (the classifications table is the source of truth for the
                # `captive_fuel_type` column).
                pass
            return CaptiveLcoeResult(
                lcoe_usd_mwh=float(row["default_lcoe_usd_mwh"]),
                tier=row["tier"] if pd.notna(row["tier"]) else None,
                source_citation=str(row["source_citation"]),
                scenario_used="n/a",  # CSV values are scenario-invariant
            )

        # Formula fallback — site not in CSV but classified as captive.
        fuel_price, scenario_label = _resolve_scenario_fuel_price(fuel_type, fuel_price_scenario)
        if fuel_type in _COAL_FUEL_TYPES:
            lcoe = _formula_coal_lcoe(fuel_price)
        else:
            lcoe = _formula_gas_lcoe(fuel_price)
        return CaptiveLcoeResult(
            lcoe_usd_mwh=round(lcoe, 2),
            tier=None,
            source_citation=f"formula fallback (CAPTIVE_*_DEFAULTS at {scenario_label})",
            scenario_used=scenario_label,
        )

    return None


def is_csv_anchor_site(site_id: str, defaults_df: pd.DataFrame | None = None) -> bool:
    """True if this site has a row in captive_power_lcoe_defaults.csv.

    Used by the provenance loaders to bump anchor sites to confidence='high'.
    """
    df = defaults_df if defaults_df is not None else _load_defaults_cached()
    if df.empty:
        return False
    return bool((df["site_id"] == site_id).any())


def captive_lcoe_tier(site_id: str, defaults_df: pd.DataFrame | None = None) -> str | None:
    """Return T1/T2/T3 for sites in the defaults CSV, None otherwise."""
    df = defaults_df if defaults_df is not None else _load_defaults_cached()
    if df.empty:
        return None
    match = df[df["site_id"] == site_id]
    if match.empty:
        return None
    val = match.iloc[0]["tier"]
    return str(val) if pd.notna(val) else None
