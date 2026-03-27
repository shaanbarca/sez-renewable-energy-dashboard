"""
Public API for the KEK Power Competitiveness model layer.

Import from here, not from basic_model directly:
    from src.model import lcoe_solar, action_flags, build_scorecard
"""

from src.model.basic_model import (
    CAPEX_USD_PER_KW_MAX,
    CAPEX_USD_PER_KW_MIN,
    FIRMING_ADDER_HIGH_USD_MWH,
    FIRMING_ADDER_LOW_USD_MWH,
    # Constants
    HOURS_PER_YEAR,
    PVOUT_ANNUAL_MAX,
    PVOUT_ANNUAL_MIN,
    # Action flags
    action_flags,
    # End-to-end pipeline
    build_scorecard,
    capacity_factor_from_pvout,
    # Economics
    capital_recovery_factor,
    # GEAS allocation
    geas_baseline_allocation,
    geas_policy_allocation,
    is_solar_attractive,
    lcoe_solar,
    lcoe_solar_with_firming,
    # Resource helpers
    pvout_daily_to_annual,
    # RUPTL metrics
    ruptl_region_metrics,
    # Competitiveness
    solar_competitive_gap,
    time_bucket,
)

__all__ = [
    "HOURS_PER_YEAR",
    "PVOUT_ANNUAL_MIN",
    "PVOUT_ANNUAL_MAX",
    "CAPEX_USD_PER_KW_MIN",
    "CAPEX_USD_PER_KW_MAX",
    "FIRMING_ADDER_LOW_USD_MWH",
    "FIRMING_ADDER_HIGH_USD_MWH",
    "pvout_daily_to_annual",
    "capacity_factor_from_pvout",
    "capital_recovery_factor",
    "lcoe_solar",
    "lcoe_solar_with_firming",
    "solar_competitive_gap",
    "is_solar_attractive",
    "action_flags",
    "geas_baseline_allocation",
    "geas_policy_allocation",
    "ruptl_region_metrics",
    "build_scorecard",
    "time_bucket",
]
