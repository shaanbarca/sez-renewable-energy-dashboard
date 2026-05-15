# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Levelized Cost of Storage (LCOS) for the multi-tier LCOE framework.

v4.1a §8 (issue #69). Computes IRENA/Lazard-style LCOS at 4-hour and 8-hour
durations and the simplified solar+storage "firm" LCOE adder used in §2's
`full_system_lcoe_firm_4h_usd_mwh` and `full_system_lcoe_firm_8h_usd_mwh`
columns.

Formulas:

    LCOS (USD per MWh delivered through storage) =
        (annualized_capex + fixed_om_annual) / annual_throughput_mwh

    where
        annualized_capex   = capex_total * CRF(discount_rate, lifetime)
        capex_total        = capacity_kwh * capex_per_kwh
        annual_throughput  = capacity_kwh * cycles_per_year * rte * dod  [kWh/yr]
        fixed_om_annual    = (capacity_kwh / duration_hours) * fixed_om_per_kw_year
        CRF                = r * (1+r)**n / ((1+r)**n - 1), or 1/n if r == 0.

Combining solar and storage (§8.5 simplified firming):

    direct_share              = 1 - storage_share
    effective_storage_share   = storage_share * RTE
    firm_lcoe = (direct_share * solar_lcoe
                 + effective_storage_share * (solar_lcoe + storage_lcos))
                / (direct_share + effective_storage_share)

This is a simplified firming approximation. Real dispatch optimization (with
PyPSA-style shadow prices) lands in v5.0. The simplification is documented
in METHODOLOGY_CONSOLIDATED.md §8.

Expected output bands at the v4.1a `BATTERY_DEFAULTS` ($350/kWh capex,
15-year life, 365 cycles/year, RTE 0.90, DOD 0.85, fixed O&M $7/kW-year,
discount 10%):
    LCOS_4h  ~ $30-50/MWh
    LCOS_8h  ~ $80-130/MWh

Sources: IRENA Battery Storage Cost Report 2024; Lazard LCOE+S v16 2024.
"""

from __future__ import annotations

import math

from src.assumptions import BATTERY_DEFAULTS


def _capital_recovery_factor(discount_rate: float, lifetime_years: int) -> float:
    """Standard CRF, with a zero-rate fallback to the simple averaging form."""
    if lifetime_years <= 0:
        raise ValueError(f"lifetime_years must be > 0, got {lifetime_years}")
    if discount_rate < 0:
        raise ValueError(f"discount_rate must be >= 0, got {discount_rate}")
    if discount_rate == 0:
        return 1.0 / lifetime_years
    pow_term = (1.0 + discount_rate) ** lifetime_years
    return discount_rate * pow_term / (pow_term - 1.0)


def compute_battery_lcos(  # noqa: PLR0913 — spec §8.4 signature; each kwarg is an independent IRENA assumption
    capacity_kwh: float,
    duration_hours: float,
    capex_per_kwh: float = float(BATTERY_DEFAULTS["capex_usd_per_kwh"]),
    lifetime_years: int = int(BATTERY_DEFAULTS["lifetime_years"]),
    cycles_per_year: int = int(BATTERY_DEFAULTS["cycles_per_year"]),
    rte: float = float(BATTERY_DEFAULTS["round_trip_efficiency"]),
    discount_rate: float = 0.10,
    dod: float = float(BATTERY_DEFAULTS["depth_of_discharge"]),
    fixed_om_per_kw_year: float = float(BATTERY_DEFAULTS["fixed_om_usd_per_kw_year"]),
) -> float:
    """Levelized Cost of Storage for a Li-ion battery.

    Parameters
    ----------
    capacity_kwh:
        Nameplate energy capacity (kWh). Cancels out of the ratio but kept
        explicit so the formula matches §8.4 of the spec.
    duration_hours:
        Storage duration at rated power (kWh / kW). Used to convert
        per-kW fixed O&M into per-kWh equivalent.
    capex_per_kwh:
        Installed system cost (USD/kWh) — battery + balance-of-plant + grid
        interconnection at utility scale. Default $350/kWh from IRENA 2024.
    lifetime_years:
        Calendar (and cycle) lifetime.
    cycles_per_year:
        Equivalent full-discharge cycles per year. 365 = daily cycling.
    rte:
        Round-trip AC-AC efficiency (fraction).
    discount_rate:
        WACC for annualization. Default 10%.
    dod:
        Depth of discharge (fraction). Reduces the effective throughput per
        cycle.
    fixed_om_per_kw_year:
        Annual fixed O&M ($/kW-year of rated power).

    Returns
    -------
    float
        LCOS in USD/MWh of energy delivered through storage.

    Raises
    ------
    ValueError
        On non-positive capacity, duration, lifetime; negative discount rate;
        or out-of-range RTE / DOD.
    """
    if capacity_kwh <= 0:
        raise ValueError(f"capacity_kwh must be > 0, got {capacity_kwh}")
    if duration_hours <= 0:
        raise ValueError(f"duration_hours must be > 0, got {duration_hours}")
    if not (0.0 < rte <= 1.0):
        raise ValueError(f"rte must be in (0, 1], got {rte}")
    if not (0.0 < dod <= 1.0):
        raise ValueError(f"dod must be in (0, 1], got {dod}")
    if cycles_per_year <= 0:
        raise ValueError(f"cycles_per_year must be > 0, got {cycles_per_year}")
    if fixed_om_per_kw_year < 0:
        raise ValueError(f"fixed_om_per_kw_year must be >= 0, got {fixed_om_per_kw_year}")

    crf = _capital_recovery_factor(discount_rate, lifetime_years)
    capex_total = capacity_kwh * capex_per_kwh
    annualized_capex = capex_total * crf

    rated_power_kw = capacity_kwh / duration_hours
    fixed_om_annual = rated_power_kw * fixed_om_per_kw_year

    annual_throughput_kwh = capacity_kwh * cycles_per_year * rte * dod
    if annual_throughput_kwh <= 0:
        return math.inf

    lcos_per_kwh = (annualized_capex + fixed_om_annual) / annual_throughput_kwh
    return lcos_per_kwh * 1000.0  # convert USD/kWh → USD/MWh


def lcos_at_duration(duration_hours: float, **overrides: float) -> float:
    """Convenience wrapper: LCOS at a given duration with default battery sizing.

    Uses `capacity_kwh = duration_hours * 1000` (i.e. a 1 MW battery rated at
    `duration_hours`). The choice of nameplate cancels out — duration is what
    drives the LCOS via the fixed-O&M-per-kW component.
    """
    return compute_battery_lcos(
        capacity_kwh=duration_hours * 1000.0,
        duration_hours=duration_hours,
        **overrides,
    )


def compute_firm_delivered_lcoe(
    solar_lcoe: float,
    storage_share: float,
    storage_duration_hours: float,
    storage_lcos: float,
    capacity_factor: float | None = None,
    rte: float = float(BATTERY_DEFAULTS["round_trip_efficiency"]),
) -> float:
    """Combined firm LCOE: solar generation + storage adder (simplified).

    Per spec §8.5. Treats a `storage_share` fraction of solar output as
    cycled through the battery (with round-trip losses) and the remainder
    as delivered directly.

        direct_share              = 1 - storage_share
        effective_storage_share   = storage_share * rte
        firm_lcoe = (direct_share * solar_lcoe
                     + effective_storage_share * (solar_lcoe + storage_lcos))
                    / (direct_share + effective_storage_share)

    `capacity_factor` and `storage_duration_hours` are not used by the
    simplified formula — they are accepted to keep the signature stable
    against the v5.0 PyPSA dispatch implementation that will use them.

    Parameters
    ----------
    solar_lcoe:
        Solar generation LCOE (USD/MWh).
    storage_share:
        Fraction of solar nameplate routed through storage (0-1). v4.1a uses
        0.20 for firm_4h and 0.50 for firm_8h per §2.1.1.
    storage_duration_hours:
        Hours of storage at rated power (4 or 8). Unused by the simplified
        formula but kept for v5.0 forward-compatibility.
    storage_lcos:
        LCOS at the matching duration (USD/MWh).
    capacity_factor:
        Solar capacity factor (0-1). Unused; reserved for v5.0.
    rte:
        Battery round-trip efficiency (fraction). Default IRENA 2024.

    Returns
    -------
    float
        Firm Full System LCOE in USD/MWh.
    """
    del storage_duration_hours, capacity_factor  # reserved for v5.0
    if not (0.0 <= storage_share <= 1.0):
        raise ValueError(f"storage_share must be in [0, 1], got {storage_share}")

    direct_share = 1.0 - storage_share
    effective_storage_share = storage_share * rte
    weighted = direct_share * solar_lcoe + effective_storage_share * (solar_lcoe + storage_lcos)
    denom = direct_share + effective_storage_share
    if denom <= 0:
        return math.inf
    return weighted / denom
