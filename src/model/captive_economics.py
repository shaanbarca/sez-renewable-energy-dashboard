# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
Captive coal + captive gas LCOE math (v4.1a §4, §5; issues #71, #72).

Computes site-level captive coal LCOE and captive gas LCOE for sites whose
``electricity_arrangement`` (per #70 classification) involves on-site
captive generation. Per-site overrides in
``data/raw/captive_generation_overrides.csv`` trump the formula-derived
defaults; sites without overrides receive the default with
``confidence='medium'``.

# LCOE formula

For both coal and gas:

    LCOE ($/MWh) =
        fuel_component
      + variable_om_usd_mwh
      + (fixed_om_usd_per_kw_year / (HOURS_PER_YEAR × capacity_factor)) × 1000
      + capital_recovery_usd_mwh

where ``fuel_component`` is:

  - **Coal:** ($/tonne ÷ HHV_MMBTU_per_tonne) × (BTU/kWh ÷ 1000)
            = fuel_cost_per_MMBTU × heat_rate ÷ 1000

  - **Gas:** fuel_cost_per_MMBTU × heat_rate ÷ 1000

# Why coal needs an HHV conversion

Captive coal costs are quoted in $/tonne (the units Indonesian thermal coal
is traded at — e.g. HBA prices, mine-mouth contracts), while the heat-rate
parameter uses BTU/kWh. To make the units cancel we have to express fuel cost
per energy unit, which means dividing by coal's higher heating value (HHV).
``CAPTIVE_COAL_HHV_MMBTU_PER_TONNE`` in ``src/assumptions.py`` carries the
default value (19 MMBTU/tonne — representative of Indonesian sub-bituminous
~4,800 kcal/kg HHV).

# Note on spec's stated targets

Spec §4.3 claims defaults yield ~$45/MWh and §5.2 claims ~$65/MWh. The
formula above is the standard $/MWh = fuel + O&M + capital build-up used in
every captive-power LCOE analysis; with the spec's literal defaults it
returns ~$55/MWh for coal and ~$77/MWh for gas. The "$45" and "$65" anchor
numbers cited in the spec are the empirical Indonesian captive-power LCOE
range from Berkeley Goldman 2023 + IESR 2024, not the precise output of the
formula's defaults. The five site-specific overrides in
``data/raw/captive_generation_overrides.csv`` carry the empirical numbers
($48-60 for coal anchors, $65 for Pupuk Kaltim) and are what gets surfaced
for the anchor sites. Default-only sites get the formula output (clearly
medium confidence per #70's classification_confidence='medium' default).

The discrepancy is documented in docs/METHODOLOGY_CONSOLIDATED.md §4-§5.

Sources:
    src/assumptions.py — CAPTIVE_COAL_DEFAULTS, CAPTIVE_GAS_DEFAULTS,
                         CAPTIVE_COAL_HHV_MMBTU_PER_TONNE
    data/raw/captive_generation_overrides.csv — 5 coal + 1 gas anchor overrides
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.assumptions import (
    CAPTIVE_COAL_DEFAULTS,
    CAPTIVE_COAL_HHV_MMBTU_PER_TONNE,
    CAPTIVE_GAS_DEFAULTS,
    HOURS_PER_YEAR,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
OVERRIDES_CSV_DEFAULT = DATA_DIR / "raw" / "captive_generation_overrides.csv"

# Captive fuel types that count as "coal" for LCOE gating.
_COAL_FUEL_TYPES = frozenset({"coal_subcritical", "coal_supercritical"})
_GAS_FUEL_TYPES = frozenset({"natural_gas"})


def captive_coal_lcoe_usd_mwh(
    defaults: dict[str, float] = CAPTIVE_COAL_DEFAULTS,
    hhv_mmbtu_per_tonne: float = CAPTIVE_COAL_HHV_MMBTU_PER_TONNE,
) -> float:
    """Compute captive coal LCOE from defaults.

    Returns ~$55/MWh with the v4.1a foundation defaults. The mid-range
    Indonesian captive coal LCOE cited in Berkeley/IESR is ~$45/MWh —
    that's the *empirical range claim*, not the formula's output with
    these defaults. See module docstring for the discrepancy note.

    Parameters
    ----------
    defaults:
        Dict matching CAPTIVE_COAL_DEFAULTS schema.
    hhv_mmbtu_per_tonne:
        Coal higher heating value used to convert $/tonne fuel cost to
        $/MMBTU. Indonesian sub-bituminous default ~19 MMBTU/tonne.
    """
    fuel_cost_per_mmbtu = defaults["fuel_cost_usd_per_tonne"] / hhv_mmbtu_per_tonne
    fuel_component = fuel_cost_per_mmbtu * defaults["heat_rate_btu_per_kwh"] / 1000.0
    fixed_om_per_mwh = (
        defaults["fixed_om_usd_per_kw_year"] / (HOURS_PER_YEAR * defaults["capacity_factor"])
    ) * 1000.0
    return (
        fuel_component
        + defaults["variable_om_usd_mwh"]
        + fixed_om_per_mwh
        + defaults["capital_recovery_usd_mwh"]
    )


def captive_gas_lcoe_usd_mwh(
    defaults: dict[str, float] = CAPTIVE_GAS_DEFAULTS,
) -> float:
    """Compute captive gas LCOE from defaults.

    Returns ~$77/MWh with the v4.1a foundation defaults. The spec's stated
    ~$65/MWh is the empirical Indonesian captive gas LCOE — that's what the
    Pupuk Kaltim Bontang override carries.
    """
    fuel_component = (
        defaults["fuel_cost_usd_per_mmbtu"] * defaults["heat_rate_btu_per_kwh"] / 1000.0
    )
    fixed_om_per_mwh = (
        defaults["fixed_om_usd_per_kw_year"] / (HOURS_PER_YEAR * defaults["capacity_factor"])
    ) * 1000.0
    return (
        fuel_component
        + defaults["variable_om_usd_mwh"]
        + fixed_om_per_mwh
        + defaults["capital_recovery_usd_mwh"]
    )


def load_captive_overrides(overrides_csv: Path = OVERRIDES_CSV_DEFAULT) -> pd.DataFrame:
    """Load the per-site captive LCOE overrides CSV.

    Schema: site_id, captive_lcoe_usd_mwh, fuel_type, source, last_updated.

    Returns an empty DataFrame with the right columns if the file is missing
    — this allows fresh checkouts / golden tests to run without the data
    file in place.
    """
    if not overrides_csv.exists():
        return pd.DataFrame(
            columns=["site_id", "captive_lcoe_usd_mwh", "fuel_type", "source", "last_updated"]
        )
    return pd.read_csv(overrides_csv)


def site_captive_coal_lcoe(
    site_id: str,
    captive_fuel_type: str | None,
    overrides_df: pd.DataFrame,
    default_lcoe: float | None = None,
) -> float | None:
    """Resolve captive coal LCOE for one site.

    Returns
    -------
    float or None
        - The override value if a coal_* override exists for this site.
        - The default LCOE if the site's captive_fuel_type starts with "coal_".
        - None if the site doesn't have a captive coal arrangement.

    The `captive_fuel_type` argument comes from `fct_site_classifications`
    (issue #70). When it's not a coal type, this returns None — the column
    is NULL for non-coal sites, by design.
    """
    if not isinstance(captive_fuel_type, str) or captive_fuel_type not in _COAL_FUEL_TYPES:
        return None
    # Override match — preference over default.
    match = overrides_df[
        (overrides_df["site_id"] == site_id)
        & overrides_df["fuel_type"].str.startswith("coal_", na=False)
    ]
    if not match.empty:
        return float(match.iloc[0]["captive_lcoe_usd_mwh"])
    if default_lcoe is None:
        default_lcoe = captive_coal_lcoe_usd_mwh()
    return default_lcoe


def site_captive_gas_lcoe(
    site_id: str,
    captive_fuel_type: str | None,
    overrides_df: pd.DataFrame,
    default_lcoe: float | None = None,
) -> float | None:
    """Resolve captive gas LCOE for one site.

    Returns
    -------
    float or None
        - The override value if a natural_gas override exists for this site.
        - The default LCOE if captive_fuel_type == "natural_gas".
        - None otherwise.
    """
    if captive_fuel_type not in _GAS_FUEL_TYPES:
        return None
    match = overrides_df[
        (overrides_df["site_id"] == site_id) & (overrides_df["fuel_type"] == "natural_gas")
    ]
    if not match.empty:
        return float(match.iloc[0]["captive_lcoe_usd_mwh"])
    if default_lcoe is None:
        default_lcoe = captive_gas_lcoe_usd_mwh()
    return default_lcoe


def is_coal_anchor_site(site_id: str, overrides_df: pd.DataFrame) -> bool:
    """True if this site_id has a captive_coal_* row in the overrides CSV."""
    return bool(
        (
            (overrides_df["site_id"] == site_id)
            & overrides_df["fuel_type"].str.startswith("coal_", na=False)
        ).any()
    )


def is_gas_anchor_site(site_id: str, overrides_df: pd.DataFrame) -> bool:
    """True if this site_id has a natural_gas row in the overrides CSV."""
    return bool(
        ((overrides_df["site_id"] == site_id) & (overrides_df["fuel_type"] == "natural_gas")).any()
    )
