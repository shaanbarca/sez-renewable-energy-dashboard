# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""User-adjustable assumption dataclasses for live scorecard computation.

`UserAssumptions` covers model parameters (CAPEX, WACC, lifetime, BESS sizing,
CBAM scenario, etc.) exposed via dashboard sliders. `UserThresholds` covers
action-flag thresholds (Tier 3). Both round-trip through dict for dcc.Store.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.assumptions import (
    BASE_WACC,
    BESS_CAPEX_USD_PER_KWH,
    CBAM_CERTIFICATE_PRICE_EUR_TCO2,
    CBAM_EUR_USD_RATE,
    CONNECTION_COST_PER_KW_KM,
    FIRMING_RELIABILITY_REQ_THRESHOLD,
    GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD,
    GRID_CONNECTION_FIXED_PER_KW,
    IDR_USD_RATE,
    LAND_COST_USD_PER_KW,
    PLAN_LATE_POST2030_SHARE_THRESHOLD,
    PROJECT_VIABLE_MIN_MWP,
    RESILIENCE_LCOE_GAP_THRESHOLD_PCT,
    SUBSTATION_UTILIZATION_PCT,
    TECH006_CAPEX_USD_PER_KW,
    TECH006_FOM_USD_PER_KW_YR,
    TECH006_LIFETIME_YR,
)


@dataclass
class UserAssumptions:
    """Model assumptions adjustable via dashboard sliders (Tier 1 + Tier 2)."""

    # Tier 1: Primary controls
    capex_usd_per_kw: float = TECH006_CAPEX_USD_PER_KW
    lifetime_yr: int = TECH006_LIFETIME_YR
    wacc_pct: float = BASE_WACC  # percent, e.g. 10.0

    # Tier 2: Advanced panel
    fom_usd_per_kw_yr: float = TECH006_FOM_USD_PER_KW_YR
    connection_cost_per_kw_km: float = CONNECTION_COST_PER_KW_KM
    grid_connection_fixed_per_kw: float = GRID_CONNECTION_FIXED_PER_KW
    bess_capex_usd_per_kwh: float = BESS_CAPEX_USD_PER_KWH
    land_cost_usd_per_kw: float = LAND_COST_USD_PER_KW
    substation_utilization_pct: float = SUBSTATION_UTILIZATION_PCT
    idr_usd_rate: float = IDR_USD_RATE
    grid_benchmark_usd_mwh: float = 63.08

    # BESS sizing override — None = auto (2h/4h/14h by reliability), set = fixed hours
    bess_sizing_hours_override: float | None = None

    # M18: DFI grant scenario — zero out grid connection costs
    grant_funded_transmission: bool = False

    # Project sizing — optional capacity override (H10)
    target_capacity_mwp: float | None = None

    # Hybrid RE: solar/wind mix ratio (None = auto-optimize per KEK)
    hybrid_solar_share: float | None = None

    # CBAM scenario parameters
    cbam_certificate_price_eur: float = CBAM_CERTIFICATE_PRICE_EUR_TCO2
    cbam_eur_usd_rate: float = CBAM_EUR_USD_RATE

    @property
    def wacc_decimal(self) -> float:
        return self.wacc_pct / 100.0

    @property
    def capex_low(self) -> float:
        """Lower bound: -12.5% of central CAPEX (matches ESDM band)."""
        return self.capex_usd_per_kw * 0.875

    @property
    def capex_high(self) -> float:
        """Upper bound: +12.5% of central CAPEX (matches ESDM band)."""
        return self.capex_usd_per_kw * 1.125

    def to_dict(self) -> dict:
        """Serialise for dcc.Store."""
        d = {
            "capex_usd_per_kw": self.capex_usd_per_kw,
            "lifetime_yr": self.lifetime_yr,
            "wacc_pct": self.wacc_pct,
            "fom_usd_per_kw_yr": self.fom_usd_per_kw_yr,
            "connection_cost_per_kw_km": self.connection_cost_per_kw_km,
            "grid_connection_fixed_per_kw": self.grid_connection_fixed_per_kw,
            "bess_capex_usd_per_kwh": self.bess_capex_usd_per_kwh,
            "land_cost_usd_per_kw": self.land_cost_usd_per_kw,
            "substation_utilization_pct": self.substation_utilization_pct,
            "idr_usd_rate": self.idr_usd_rate,
            "grid_benchmark_usd_mwh": self.grid_benchmark_usd_mwh,
            "cbam_certificate_price_eur": self.cbam_certificate_price_eur,
            "cbam_eur_usd_rate": self.cbam_eur_usd_rate,
        }
        if self.bess_sizing_hours_override is not None:
            d["bess_sizing_hours_override"] = self.bess_sizing_hours_override
        if self.target_capacity_mwp is not None:
            d["target_capacity_mwp"] = self.target_capacity_mwp
        if self.grant_funded_transmission:
            d["grant_funded_transmission"] = True
        if self.hybrid_solar_share is not None:
            d["hybrid_solar_share"] = self.hybrid_solar_share
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "UserAssumptions":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class UserThresholds:
    """Action flag thresholds adjustable via dashboard sliders (Tier 3)."""

    pvout_threshold: float = 1350.0
    plan_late_threshold: float = PLAN_LATE_POST2030_SHARE_THRESHOLD
    geas_threshold: float = GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD
    resilience_gap_pct: float = RESILIENCE_LCOE_GAP_THRESHOLD_PCT
    min_viable_mwp: float = PROJECT_VIABLE_MIN_MWP
    reliability_threshold: float = FIRMING_RELIABILITY_REQ_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "pvout_threshold": self.pvout_threshold,
            "plan_late_threshold": self.plan_late_threshold,
            "geas_threshold": self.geas_threshold,
            "resilience_gap_pct": self.resilience_gap_pct,
            "min_viable_mwp": self.min_viable_mwp,
            "reliability_threshold": self.reliability_threshold,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UserThresholds":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def get_default_assumptions() -> UserAssumptions:
    """Return default assumptions from src/assumptions.py constants."""
    return UserAssumptions()


def get_default_thresholds() -> UserThresholds:
    """Return default thresholds from src/assumptions.py constants."""
    return UserThresholds()
