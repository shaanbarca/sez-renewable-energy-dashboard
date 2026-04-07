"""Dashboard constants — colours, slider configs, column display names.

Source: DESIGN.md §4 (Action flag colours) and §3 (Component Architecture).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Action flag colours (DESIGN.md §4)
# ---------------------------------------------------------------------------

ACTION_FLAG_COLORS: dict[str, str] = {
    "solar_now": "#2E7D32",
    "invest_resilience": "#F57C00",
    "grid_first": "#1565C0",
    "plan_late": "#7B1FA2",
    "not_competitive": "#C62828",
}

ACTION_FLAG_LABELS: dict[str, str] = {
    "solar_now": "Solar Now",
    "invest_resilience": "Invest Resilience",
    "grid_first": "Grid First",
    "plan_late": "Plan Late",
    "not_competitive": "Not Competitive",
}

ACTION_FLAG_DESCRIPTIONS: dict[str, str] = {
    "solar_now": (
        "Solar LCOE is below grid cost AND PLN has grid infrastructure "
        "upgrades planned pre-2030 AND the KEK has sufficient GEAS green energy allocation"
    ),
    "invest_resilience": (
        "Solar LCOE is within the resilience gap threshold of grid cost "
        "(close to competitive) AND the KEK has high reliability requirements"
    ),
    "grid_first": (
        "Solar LCOE is competitive, but PLN's RUPTL grid expansion plan shows no "
        "substation or transmission upgrade scheduled for this region before 2030. "
        "Grid infrastructure must come first before solar can connect."
    ),
    "plan_late": (
        "Over 60% of RUPTL-planned solar capacity additions in this grid region "
        "are scheduled after 2030. Infrastructure delivery risk is high."
    ),
    "not_competitive": (
        "Solar LCOE exceeds grid cost beyond the resilience gap threshold. "
        "Solar is not yet cost-competitive in this region at current assumptions."
    ),
}

WIND_COLOR = "#00796B"

# ---------------------------------------------------------------------------
# WACC slider marks (9 snap points, 4–20% in 2% steps)
# ---------------------------------------------------------------------------

WACC_MARKS = {v: f"{v}%" for v in range(4, 22, 2)}
WACC_MIN = 4
WACC_MAX = 20
WACC_STEP = 2
WACC_DEFAULT = 10

# ---------------------------------------------------------------------------
# Slider configurations — (min, max, step, default, label, unit)
# ---------------------------------------------------------------------------

TIER1_SLIDERS = {
    "capex_usd_per_kw": {
        "min": 600,
        "max": 1500,
        "step": 10,
        "label": "CAPEX",
        "unit": "$/kW",
        "description": "Installed solar PV capital cost per kilowatt of capacity",
    },
    "lifetime_yr": {
        "min": 20,
        "max": 35,
        "step": 1,
        "label": "Lifetime",
        "unit": "years",
        "description": "Expected operating lifetime of the solar plant",
    },
}

WACC_DESCRIPTION = "Weighted average cost of capital, reflects financing risk premium"

TIER2_SLIDERS = {
    "fom_usd_per_kw_yr": {
        "min": 3,
        "max": 15,
        "step": 0.5,
        "label": "Fixed O&M",
        "unit": "$/kW-yr",
        "description": "Annual fixed operations & maintenance cost",
    },
    "gentie_cost_per_kw_km": {
        "min": 2,
        "max": 12,
        "step": 0.5,
        "label": "Gen-tie cost",
        "unit": "$/kW-km",
        "description": "Cost to build gen-tie line from solar plant to substation, per kW per km",
    },
    "substation_works_per_kw": {
        "min": 80,
        "max": 250,
        "step": 10,
        "label": "Substation works",
        "unit": "$/kW",
        "description": "Cost of substation upgrades/connection works per kW",
    },
    "transmission_lease_mid_usd_mwh": {
        "min": 3,
        "max": 20,
        "step": 1,
        "label": "Transmission lease",
        "unit": "$/MWh",
        "description": "Ongoing transmission access fee added to LCOE",
    },
    "firming_adder_mid_usd_mwh": {
        "min": 5,
        "max": 20,
        "step": 1,
        "label": "Firming adder",
        "unit": "$/MWh",
        "description": "Cost of battery/backup to firm intermittent solar output",
    },
    "idr_usd_rate": {
        "min": 14000,
        "max": 18000,
        "step": 100,
        "label": "IDR/USD rate",
        "unit": "",
        "description": "Indonesian Rupiah to USD exchange rate, affects grid tariff conversion",
    },
}

TIER3_SLIDERS = {
    "pvout_threshold": {
        "min": 1200,
        "max": 1800,
        "step": 50,
        "label": "PVOUT threshold",
        "unit": "kWh/kWp",
        "description": "Minimum annual solar yield for a site to be considered viable",
    },
    "plan_late_threshold": {
        "min": 0.3,
        "max": 1.0,
        "step": 0.05,
        "label": "Plan-late threshold",
        "unit": "",
        "description": "Share of planned grid capacity after 2030 that flags delayed infrastructure",
    },
    "geas_threshold": {
        "min": 0.05,
        "max": 0.50,
        "step": 0.05,
        "label": "GEAS threshold",
        "unit": "",
        "description": "Minimum green energy share from GEAS allocation for Solar Now flag",
    },
    "resilience_gap_pct": {
        "min": 5,
        "max": 50,
        "step": 5,
        "label": "Resilience gap",
        "unit": "%",
        "description": "Max LCOE-vs-grid gap (%) for Invest Resilience classification",
    },
    "min_viable_mwp": {
        "min": 5,
        "max": 50,
        "step": 5,
        "label": "Min viable capacity",
        "unit": "MWp",
        "description": "Minimum buildable capacity for a project to be flagged viable",
    },
    "reliability_threshold": {
        "min": 0.3,
        "max": 1.0,
        "step": 0.05,
        "label": "Reliability threshold",
        "unit": "",
        "description": "Reliability requirement level that triggers the Firming Needed flag",
    },
}

# ---------------------------------------------------------------------------
# Column display names for the ranked table
# ---------------------------------------------------------------------------

TABLE_COLUMNS = {
    "kek_name": "KEK Name",
    "province": "Province",
    "action_flag": "Action Flag",
    "lcoe_mid_usd_mwh": "LCOE ($/MWh)",
    "solar_competitive_gap_pct": "Gap (%)",
    "best_re_technology": "Best RE",
    "best_re_lcoe_mid_usd_mwh": "Best RE LCOE",
    "dashboard_rate_usd_mwh": "Grid Rate ($/MWh)",
    "carbon_breakeven_usd_tco2": "Carbon BE ($/tCO2)",
    "buildable_area_ha": "Buildable (ha)",
    "max_captive_capacity_mwp": "Max Cap (MWp)",
    "project_viable": "Viable",
}

# Indonesia map center
MAP_CENTER = {"lat": -2.5, "lon": 118.0}
MAP_ZOOM = 4
