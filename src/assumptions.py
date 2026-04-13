# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
assumptions.py — single source of truth for all model constants and assumptions.

Shared by src/model/basic_model.py AND src/pipeline/* builders.
When a number changes, change it here — nowhere else.

Layout:
    FX / MONETARY       — exchange rates, tariff values
    SOLAR RESOURCE      — GeoTIFF extraction, PVOUT bounds, radius
    LCOE MODEL          — WACC range, tech parameters, CAPEX bounds
    ACTION FLAG THRESHOLDS — firming, plan_late, GEAS, reliability
    RUPTL ANALYSIS      — year brackets, CF defaults
    DERIVED             — convenience values computed from the above

Every constant has:
    - Source: where the number comes from
    - Rationale: why this value was chosen
"""

from __future__ import annotations

# ─── FX / MONETARY ────────────────────────────────────────────────────────────

IDR_USD_RATE: float = 15_800.0
# Indonesian Rupiah per US Dollar — 2024 annual average reference rate.
# Source: Bank Indonesia monthly average 2024, rounded to nearest 100.
# Rationale: RUPTL and PLN cost data are in IDR; LCOE in USD/MWh for comparability.
# Update: replace with Bank Indonesia published annual average each year.

# ─── PLN INDUSTRIAL TARIFFS ───────────────────────────────────────────────────

TARIFF_I3_LWBP_RP_KWH: float = 1_035.78
# I-3/TM industrial tariff (medium voltage, 200 kVA–30,000 kVA) — off-peak (LWBP) rate.
# Source: Permen ESDM No. 7 Tahun 2024, Lampiran IV (Tarif Industri), effective 10 June 2024.
# File: docs/Permen ESDM Nomor 7 Tahun 2024.pdf, page 14.
# Note: WBP (peak) rate = K × LWBP where 1.4 ≤ K ≤ 2.0 (system-specific). LWBP used as floor.

TARIFF_I4_RP_KWH: float = 996.74
# I-4/TT industrial tariff (high voltage, ≥30,000 kVA) — WBP = LWBP (no peak surcharge).
# Source: Permen ESDM No. 7 Tahun 2024, Lampiran IV, effective 10 June 2024.
# File: docs/Permen ESDM Nomor 7 Tahun 2024.pdf, page 14.
# Note: UNIFORM NATIONWIDE — does not vary by PLN grid system.
# Rationale: Primary dashboard comparator. Most KEK tenants connect at I-4/TT voltage.

# ─── SOLAR RESOURCE ───────────────────────────────────────────────────────────

HOURS_PER_YEAR: int = 8_760
# Calendar hours per year (365 × 24). Used to convert PVOUT → capacity factor.
# Source: physical constant (no leap-year adjustment; standard solar industry convention).

PVOUT_ANNUAL_MIN: float = 1_200.0
# Lower plausibility bound for annual PVOUT in Indonesia (kWh/kWp/yr).
# Source: METHODOLOGY_CONSOLIDATED.md Section 2.2 — "1,200–2,200 kWh/kWp/yr for Indonesian latitudes."
# Values below this indicate a unit error (daily value passed as annual) or bad coordinate.

PVOUT_ANNUAL_MAX: float = 2_200.0
# Upper plausibility bound for annual PVOUT in Indonesia (kWh/kWp/yr).
# Source: METHODOLOGY_CONSOLIDATED.md Section 2.2.

KM_PER_DEGREE_LAT: float = 111.32
# Approximate kilometres per degree of latitude (Earth mean radius = 6,371 km).
# Used in 50 km buffer calculation for best-PVOUT search radius.
# Source: geodetic constant, valid to ~0.1% accuracy across Indonesia's latitude range.

PVOUT_BUFFER_KM: float = 50.0
# Search radius (km) for best-within-radius PVOUT extraction from GeoTIFF.
# Source: METHODOLOGY_CONSOLIDATED.md Section 2.4.
# Rationale: 50 km captures typical industrial park siting flexibility (land constraints,
# grid connection distance) without expanding into a different solar resource regime.

PVOUT_SOURCE: str = "GlobalSolarAtlas-v2"
# Name tag for PVOUT raster provenance.
# Source: https://globalsolaratlas.info — World Bank / Solargis, Long-Term Average (LTAym).

# ─── LCOE MODEL ───────────────────────────────────────────────────────────────

WACC_VALUES: list[float] = [4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
# WACC sensitivity range (%) for precomputed LCOE table. 2% steps, 4–20%.
# Source: METHODOLOGY_CONSOLIDATED.md Section 3.3.
# Rationale:
#   4–6%  — DFI concessional blended finance (IFC, AIIB, DFC facility rates)
#   8%    — DFI de-risked / policy-supported project finance
#   10%   — base case: typical Indonesian IPP project finance cost of capital
#   12%   — pessimistic: unstructured project finance
#   14–16% — equity premium / higher-risk scenarios
#   18–20% — opportunistic equity; SE Asia ceiling (above 20% no renewable project closes)
# No hard cap in code — WACC_VALUES is just a list; extend if needed.

BASE_WACC: float = 10.0
# Base-case WACC (%) used for action flags and competitive gap calculation.
# Source: METHODOLOGY_CONSOLIDATED.md Section 3.3.
# Rationale: 10% reflects typical Indonesian IPP project finance cost of capital.
# Note: pass as decimal to lcoe_solar() → BASE_WACC / 100 = 0.10.

BASE_WACC_DECIMAL: float = BASE_WACC / 100.0
# BASE_WACC expressed as a decimal for direct use in lcoe_solar(wacc=...).

CAPEX_USD_PER_KW_MIN: float = 200.0
# Lower CAPEX plausibility bound (USD/kW). Below this = unit error (MUSD/MWe not converted).
# Source: METHODOLOGY_CONSOLIDATED.md Section 3.2.

CAPEX_USD_PER_KW_MAX: float = 4_000.0
# Upper CAPEX plausibility bound (USD/kW). Above this = likely unit error.
# Raised from 3000 to 4000 to accommodate wind CAPEX ($2,350 upper) + gen-tie adder.
# Source: METHODOLOGY_CONSOLIDATED.md Section 3.2.

SOLAR_TECH_ID: str = "TECH006"
# Technology identifier for utility-scale ground-mounted PV in dim_tech_variant.csv.
# Source: data/dim_tech_variant.csv (ESDM technology catalogue).

SOLAR_TECH_YEAR: int = 2023
# Reference year for solar CAPEX / O&M data.
# Source: data/fct_tech_parameter.csv (ESDM technology cost data).
# Rationale: Most recent year available in the ESDM technology cost catalogue.

# Default TECH006 parameters used by build_scorecard() when dim_tech_cost is unavailable.
# Verified from ESDM Technology Catalogue 2023, datasheet p.66 (PV ground-mounted, utility-scale).
# Stored as VERIFIED_TECH006_DATA in src/pipeline/pdf_extract_esdm_tech.py.
TECH006_CAPEX_USD_PER_KW: float = 960.0
# Source: ESDM Technology Catalogue 2023, p.66. 0.96 MUSD/MWe × 1000 = 960 USD/kW.

TECH006_FOM_USD_PER_KW_YR: float = 7.5
# Source: ESDM Technology Catalogue 2023, p.66. 7,500 USD/MWe/yr ÷ 1000 = 7.5 USD/kW/yr.

TECH006_LIFETIME_YR: int = 27
# Source: ESDM Technology Catalogue 2023, p.66. Central value = 27 years.

SOLAR_DEGRADATION_ANNUAL_PCT: float = 0.5
# Annual panel output degradation (%). Median ~0.5%/yr for crystalline silicon.
# Source: NREL "Photovoltaic Degradation Rates" (Jordan & Kurtz, 2013).
# Applied as midpoint linear approximation in lcoe_solar():
#   degradation_factor = 1 - (rate × lifetime / 2)
# Over 27yr: factor = 0.9325, LCOE increases ~7.2%.

# ─── WIND TECH ─────────────────────────────────────────────────────────────────

WIND_TECH_ID: str = "TECH_WIND_ONSHORE"
# Technology identifier for onshore wind in dim_tech_variant.csv.
# Source: ESDM Technology Catalogue 2024, Chapter 4, datasheet p.90 (Wind power - Onshore).

WIND_TECH_YEAR: int = 2023
# Reference year for wind CAPEX / O&M data (price year 2022 USD, reference year 2023).
# Source: ESDM Technology Catalogue 2024, p.90.

TECH_WIND_CAPEX_USD_PER_KW: float = 1650.0
# Source: ESDM Technology Catalogue 2024, p.90. 1.65 MUSD/MWe × 1000 = 1650 USD/kW.
# IEC Class III turbine (low wind, appropriate for Indonesia).

TECH_WIND_FOM_USD_PER_KW_YR: float = 40.0
# Source: ESDM Technology Catalogue 2024, p.90. 40,000 USD/MWe/yr ÷ 1000 = 40 USD/kW/yr.
# Includes insurance, land lease, and regular replacement of inverters/gearbox components.

TECH_WIND_LIFETIME_YR: int = 27
# Source: ESDM Technology Catalogue 2024, p.90. Central value = 27 years (range 25–35).

# ─── WIND RESOURCE ─────────────────────────────────────────────────────────────

WIND_BUFFER_KM: float = 50.0
# Search radius (km) for best wind speed within radius, same as solar for consistency.
# Source: mirrors PVOUT_BUFFER_KM rationale.

WIND_CF_MIN: float = 0.05
# Lower plausibility bound for wind capacity factor.
# Source: ESDM catalogue notes: majority of Indonesia has CF below 20%,
# some sites near 0% wind viability. 5% allows for marginal sites.

WIND_CF_MAX: float = 0.55
# Upper plausibility bound for wind capacity factor.
# Source: ESDM catalogue shows best sites globally reach ~45-50% CF.
# 55% ceiling with margin.

WIND_SOURCE: str = "GlobalWindAtlas-v3"
# Name tag for wind speed raster provenance.
# Source: https://globalwindatlas.info — DTU / World Bank, mean wind speed at 100m.

# ─── GRID CONNECTION COST (V2: grid-connected solar scenario) ────────────────
# V2 replaces "gen-tie" model with "grid connection" model. Solar farm connects to
# nearest PLN substation via short MV/HV line; PLN operates the wider transmission.
# See METHODOLOGY_V2.md §3 for full rationale.

CONNECTION_COST_PER_KW_KM: float = 5.0
# Grid connection line cost per kW of solar capacity per km of line length.
# Covers MV/HV cable from solar farm to nearest PLN substation.
# Source: METHODOLOGY_V2.md §3 — industry benchmark range $2–15/kW-km.
# Default $5/kW-km: mid-range for Indonesian conditions (terrain, permitting).
# User-adjustable in dashboard with range $2–15/kW-km.
# Note: Does not include land/ROW acquisition (developer-negotiated, site-specific).

GRID_CONNECTION_FIXED_PER_KW: float = 80.0
# Fixed grid connection cost per kW: step-up transformer, switchgear, protection,
# metering at the solar farm end. PLN substation end assumed existing infrastructure.
# Source: METHODOLOGY_V2.md §3 — range $30–200/kW.
# Default $80/kW: lower than V1's $150/kW because V2 assumes only solar-side works
# (no new substation at KEK end — KEK already connected to PLN grid).
# User-adjustable in dashboard with range $30–200/kW.

# V1 aliases — kept at V1 values for backward compatibility until downstream code
# is updated in V2-B5/B6/B7. These will be removed once all consumers are migrated.
# TODO(V2): Remove these aliases after completing V2-B5 (model renames).
GENTIE_COST_PER_KW_KM: float = 5.0
SUBSTATION_WORKS_PER_KW: float = 150.0

# ─── TRANSMISSION LEASE ADDER (V2: DEPRECATED) ──────────────────────────────
# V2 removes the transmission lease adder. In the grid-connected model, transmission
# cost is PLN's system cost reflected in BPP/tariff — not a separate line item for
# the solar developer. V1 values retained until downstream code is updated.
# TODO(V2): Remove these constants after completing V2-B6 (LCOE pipeline update).

TRANSMISSION_LEASE_LOW_USD_MWH: float = 5.0
TRANSMISSION_LEASE_HIGH_USD_MWH: float = 15.0
TRANSMISSION_LEASE_MID_USD_MWH: float = (
    TRANSMISSION_LEASE_LOW_USD_MWH + TRANSMISSION_LEASE_HIGH_USD_MWH
) / 2

# ─── GRID INTEGRATION THRESHOLDS (V2: three-point proximity) ────────────────
# Used by build_fct_substation_proximity.py to classify grid_integration_category.
# All thresholds are user-adjustable in the dashboard.
# Source: METHODOLOGY_V2.md §2.

SOLAR_TO_SUBSTATION_THRESHOLD_KM: float = 5.0
# Maximum distance (km) from best buildable solar site to nearest PLN substation
# for the connection to be considered "short" (i.e., grid_ready or invest_transmission/invest_substation).
# V3.1: Tightened from 10km to 5km per industry practice.
# Source: YSG Solar (ideal ≤ 2 miles / 3.2 km), IFC Utility-Scale Solar Guide (max 5 miles / 8 km).
# 5 km is a conservative mid-point; gen-tie costs ~$1–3M/mile make longer connections uneconomic.

KEK_TO_SUBSTATION_THRESHOLD_KM: float = 15.0
# Maximum distance (km) from KEK centroid to nearest PLN substation for the KEK
# to be considered "well-connected" to the grid.
# Source: METHODOLOGY_V2.md §2 — reflects that KEKs are typically sited near
# existing infrastructure; 15 km is generous for a connected industrial zone.

SUBSTATION_MIN_CAPACITY_MVA: float = 30.0
# Minimum substation rated capacity (MVA) to be considered viable for absorbing
# new solar generation. Below this, grid reinforcement may be needed.
# Source: METHODOLOGY_V2.md §2 — rule of thumb: 70-80% of rated MVA is the
# practical absorption limit; 30 MVA allows ~21-24 MW injection.

SUBSTATION_UTILIZATION_PCT: float = 0.65
# Default assumed utilization of existing substation capacity (fraction, 0–1).
# Available capacity = rated_capacity_mva × (1 − utilization_pct).
# Source: docs/methodology_testing.md §3 — default 60–70%, mid-point 65%.
# User-adjustable in dashboard. Range: 0.30–0.95.
# Proxies for smarter defaults (future): night-light intensity, industrial load, PLN RUPTL flags.

SUBSTATION_UPGRADE_COST_PER_KW: float = 80.0
# Cost to upgrade substation capacity when available capacity is insufficient to absorb
# solar output (USD/kW of solar capacity). Covers: transformer upgrade, new bay, buswork,
# protection relay upgrades at the substation end.
# Source: IRENA Renewable Power Generation Costs 2023 — substation upgrade costs typically
# $50–150/kW depending on scope. $80/kW = mid-range for Indonesian conditions.
# Applied proportionally to the capacity deficit: if available capacity covers 60% of solar,
# only 40% of the upgrade cost is added (you only upgrade what's missing).

SUBSTATION_POWER_FACTOR: float = 0.85
# Power factor for converting substation apparent power (MVA) to real power (MW).
# MW = MVA × power_factor. Industrial loads in Indonesia typically PF 0.85–0.90.
# Source: PLN grid code requires minimum PF 0.85 for industrial connections.
# Without PF correction, a 60 MVA substation appears to deliver 60 MW but only delivers 51 MW.
# Used by capacity_assessment() and substation_upgrade_cost_per_kw().

# ─── INTER-SUBSTATION TRANSMISSION (V3.1: new line cost) ─────────────────────
# When the solar site's nearest substation (B_solar) differs from the KEK's
# nearest substation (B_kek) and no existing transmission line connects them,
# someone must build a new line. This cost is added to grid-connected LCOE.
# Source: docs/methodology_testing.md §1–§2.

TRANSMISSION_LINE_COST_USD_PER_KM: float = 1_250_000
# Cost to build a new transmission line per km (USD/km).
# Source: industry range $1–3M/mile → $0.6–1.9M/km. Mid-range: $1.25M/km.
# Varies by voltage level, terrain, and permitting. User-adjustable.

TRANSMISSION_LINE_MAX_VIABLE_KM: float = 15.0
# Maximum inter-substation distance (km) before new line economics kill viability.
# Source: docs/methodology_testing.md §1 — practical limit ~10–15 km.
# Beyond this, LCOE impact is too large for project finance.

GRID_LINE_BUFFER_KM: float = 2.0
# Buffer distance (km) for geometric grid line connectivity check.
# A grid line is considered to "connect" a substation if it passes within
# this distance. Accounts for GIS digitization error and substation footprint.

TRANSMISSION_FALLBACK_CAPACITY_MWP: float = 20.0
# Conservative default solar capacity (MWp) used for transmission cost calculation
# when max_captive_capacity_mwp is unavailable. All 25 KEKs currently have capacity
# data, so this only fires for future KEKs with missing buildability data.

# ─── PROJECT VIABILITY THRESHOLDS ────────────────────────────────────────────
# V2 splits the viability threshold by siting scenario.
# Source: METHODOLOGY_V2.md §1.1.

PROJECT_VIABLE_MIN_MWP_WB: float = 0.5
# Minimum capacity (MWp) for within-boundary solar to be viable.
# Source: Indonesian IUPTLS regulatory threshold is 500 kW (Permen ESDM).
# Below this, the licensing and development overhead is disproportionate.

PROJECT_VIABLE_MIN_MWP_GC: float = 20.0
# Minimum capacity (MWp) for grid-connected solar to be viable.
# Same rationale as V1: below 20 MWp, fixed development costs make projects
# marginal for an IPP developer.
# Source: METHODOLOGY_V2.md §1.1 (minimum contiguous area discussion).

# V1 alias — kept for backward compatibility until downstream code is updated.
# TODO(V2): Remove this alias after completing V2-B7 (dashboard logic update).
PROJECT_VIABLE_MIN_MWP: float = PROJECT_VIABLE_MIN_MWP_GC

# ─── WITHIN-BOUNDARY SOLAR CAPACITY ─────────────────────────────────────────

WB_SOLAR_FRACTION: float = 0.10
# FALLBACK ONLY: used when the KEK polygon is too small to intersect any
# buildable raster pixel at ~1km resolution, or when buildability data is absent.
# For KEKs with raster data, the actual buildable area from the spatial intersection
# of the KEK polygon with the buildability-filtered raster is used instead.
# Source: METHODOLOGY_V2.md §1.1 — typical industrial zones allocate 50-60% to buildings,
# 20-25% to roads/utilities, 10-20% to green space/buffer. 10% is a conservative floor.
# User-adjustable in dashboard. Range: 0.05–0.25 (5–25% of KEK area).
# Note: At 10%, a 500 ha KEK yields 50 ha × (1 MWp / 1.5 ha) ≈ 33 MWp.

# ─── FIRMING / WHEELING ADDER ─────────────────────────────────────────────────

FIRMING_ADDER_LOW_USD_MWH: float = 6.0
# All-in captive solar cost adder — optimistic case.
# Components: grid backup (~$3–8/MWh effective), wheeling (~$2–5/MWh), PLN permitting (~$1–3/MWh).
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.5, industry estimates.

FIRMING_ADDER_HIGH_USD_MWH: float = 16.0
# All-in captive solar cost adder — conservative case.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.5.

FIRMING_ADDER_MID_USD_MWH: float = (FIRMING_ADDER_LOW_USD_MWH + FIRMING_ADDER_HIGH_USD_MWH) / 2
# Mid-point adder = $11/MWh.

# ─── BESS (Battery Energy Storage System) ────────────────────────────────────

BESS_CAPEX_USD_PER_KWH: float = 250.0
# Battery pack + BOS installed cost (USD/kWh of usable capacity).
# Source: BNEF 2024 Lithium-ion Battery Price Survey — utility-scale Asia benchmark.
# Range: $150–400/kWh. $250 = mid-range for Indonesia 2025.

BESS_DISCHARGE_HOURS: float = 4.0
# Battery system duration (hours). 4-hour systems are the utility-scale standard.

BESS_SIZING_HOURS: float = 2.0
# Hours of battery per kW of solar for industrial firming applications.
# 2h = enough to bridge cloud events and early evening ramp.
# This determines battery kWh per kW-solar: 2h × $250/kWh = $500/kW-solar CAPEX.
# NOTE: For 24/7 industrial loads, use bridge-hours scaling (see BESS_BRIDGE_HOURS_ENABLED).

BESS_BRIDGE_HOURS_ENABLED: bool = True
# When True, BESS sizing scales to bridge the overnight gap for high-reliability loads.
# bridge_hours = 24 - SOLAR_PRODUCTION_HOURS = 14h for equatorial Indonesia.
# When False, falls back to fixed BESS_SIZING_HOURS (legacy 2h behaviour).
# Source: MacKay "Sustainable Energy Without the Hot Air" Ch. 26 — storage must bridge
# the gap between solar production hours and demand hours.

SOLAR_PRODUCTION_HOURS: float = 10.0
# Effective solar production hours per day at equatorial Indonesian latitudes.
# At ~18% CF and ~12h daylight, weighted production window is ~10h.
# Used for: (1) bridge-hours BESS sizing, (2) firm solar coverage metric.
# Nighttime gap = 24 - 10 = 14 hours.

BESS_ROUND_TRIP_EFFICIENCY: float = 0.87
# Round-trip AC-to-AC efficiency of BESS (fraction).
# Source: BNEF 2024 — utility-scale Li-ion LFP: 85-90%. 87% = mid-range.
# Energy stored overnight loses 13%: 100 MWh in → 87 MWh out.
# Affects: (1) effective solar output when storage is needed, (2) BESS sizing
# must be oversized by 1/RTE to deliver required night-time energy.

BESS_LIFETIME_YR: int = 15
# Calendar lifetime of BESS (years). Li-ion NMC/LFP warranty period.

BESS_DOD: float = 0.85
# Usable depth of discharge (fraction). Operating range to preserve cycle life.

BESS_DEGRADATION_ANNUAL_PCT: float = 1.5
# Annual capacity degradation (%). 1–2% typical for utility Li-ion.

BESS_FOM_USD_PER_KW_YR: float = 5.0
# Annual fixed O&M for BESS (USD/kW-yr). Covers monitoring, HVAC, insurance.

BESS_CYCLES_PER_YEAR: int = 365
# Number of full discharge cycles per year (once per day = 365).

# ─── LAND ACQUISITION ────────────────────────────────────────────────────────

LAND_COST_USD_PER_KW: float = 45.0
# Default land acquisition cost per kW of solar capacity.
# Derivation: $3/m² (rural Indonesian land) × 15,000 m²/MW (1.5 ha/MW at utility scale)
#            = $45,000/MW = $45/kW.
# Range: $10–500/kW depending on location. Rural: $10–50, peri-urban: $50–200.
# Only applied to grid_connected_solar scenario (within_boundary uses existing KEK land).

# ─── ACTION FLAG THRESHOLDS ───────────────────────────────────────────────────

FIRMING_PVOUT_THRESHOLD: float = 1_350.0
# Minimum annual PVOUT (kWh/kWp/yr) for a zone to be considered solar-attractive.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.2.
# Rationale: Indonesia is equatorial with PVOUT range 1,300-1,700. The mean across
# 25 KEKs is ~1,518. A threshold of 1,350 (~15.4% CF) keeps all viable sites in
# analysis while excluding truly poor solar locations.

PLAN_LATE_POST2030_SHARE_THRESHOLD: float = 0.60
# Share of RUPTL solar additions post-2030 above which grid planning is flagged late.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.2.
# Rationale: ≥60% post-2030 means most grid upgrades won't be ready to support KEK solar by 2030.

FIRMING_RELIABILITY_REQ_THRESHOLD: float = 0.75
# Minimum reliability requirement (0–1) above which invest_battery is flagged.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.2.
# Rationale: Industrial zones with ≥75% reliability requirement need BESS or grid backup
# to guarantee uptime — LCOE alone understates true cost.

GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD: float = 0.30
# Minimum GEAS green share (0–1) required to trigger solar_now flag.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.2 (solar_now condition: GEAS ≥ 30%).
# Rationale: 30% green share means at least 30% of the KEK's demand can be covered by
# RUPTL-allocated solar — enough to make a captive project economically viable.

RESILIENCE_LCOE_GAP_THRESHOLD_PCT: float = 20.0
# Maximum LCOE premium (%) above grid cost for a KEK to still qualify as invest_resilience.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.3 (Resilience Layer).
# Rationale: A 20% premium above grid cost (~$63 I-4 → $76 effective ceiling) represents the
# upper bound of a reasonable "reliability insurance" premium for industrial KEKs. Manufacturing
# tenants facing unplanned outage costs typically value uptime at $50–200/MWh of lost production.
# At 20%, the premium is $12.6/MWh — well within avoided-downtime economics for heavy industry.

# ─── GRID EMISSION FACTORS ────────────────────────────────────────────────────

GRID_EMISSION_FACTOR_T_CO2_MWH: dict[str, float] = {
    # Key = grid_region_id as used in kek_grid_region_mapping.csv and fct_grid_cost_proxy.
    # Value = Operating Margin (OM) in tCO2/MWh from KESDM Tier 2 database.
    # OM = emission rate of existing grid plants displaced by captive solar — the correct
    # metric for carbon_breakeven_price() and avoided-emissions accounting.
    "JAVA_BALI": 0.80,  # Java-Bali interconnected: 302 plants (Banten, DKI, Jabar, Jateng, DIY, Jatim, Bali)
    "SUMATERA": 0.77,  # Sumatera interconnected: 463 plants (gas + hydro + coal mix)
    "KALIMANTAN": 1.16,  # Weighted avg: Barito/S+C Kalimantan OM=1.20 (Setangga KEK) +
    #   Mahakam/E Kalimantan OM=1.12 (Maloy Batuta KEK); avg=(1.20+1.12)/2
    "SULAWESI": 0.63,  # Weighted avg: Sulutgo OM=0.67 × 2 KEKs (Likupang, Bitung) +
    #   Palapas-Palu OM=0.54 × 1 KEK (Palu); avg=(0.67+0.67+0.54)/3
    "NTB": 1.27,  # Lombok grid (NTB province): 54 plants — diesel-dominant island grid
    #   (Mandalika KEK). Highest OM of any KEK grid system.
    "MALUKU": 0.60,  # Daruba-Morotai system: 12 plants (Morotai KEK — North Maluku)
    "PAPUA": 0.56,  # Sorong system: 11 plants (Sorong KEK — West Papua); gas-dominant
    "BATAM": 0.76,  # Batam-Tanjung Pinang: 47 plants — not mapped to any KEK (Riau
    #   Islands KEKs use SUMATERA). Retained for documentation only.
}
# Grid emission intensity by PLN system (tCO2/MWh), using Operating Margin (OM) values.
# Source: KESDM Tier 2 grid emission factor database, 2019 vintage
#         (Ministry of Energy & Mineral Resources, gatrik.esdm.go.id).
#         File: data/grid_emission_factors.xlsx
# Mapping: each grid_region_id maps to the PLN operational system serving the KEKs in that region.
# Status: ⚠️ PROVISIONAL — 2019 vintage; update when KESDM publishes newer Tier 2 factors.
# Use: carbon_breakeven_price() divides the LCOE gap by OM to compute the CO2 price
# at which solar becomes cost-competitive with the grid.

GRID_EMISSION_FACTOR_DEFAULT: float = 0.77
# Fallback emission factor for grid_region_ids not in GRID_EMISSION_FACTOR_T_CO2_MWH.
# Source: Sumatera interconnected OM from KESDM 2019 (0.77 tCO2/MWh) — used as a
# mid-range national default. All active KEK grid_region_ids are explicitly mapped above.

# ─── RUPTL ANALYSIS ───────────────────────────────────────────────────────────

RUPTL_PRE2030_END: int = 2030
# Last year of the "pre-2030" RUPTL bucket. Additions in [2025, 2030] count as pre-2030.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.2 (plan_late threshold definition).

RUPTL_POST2030_END: int = 2034
# Last year in the RUPTL 2025–2034 horizon.
# Source: RUPTL PLN 2025-2034 (Keputusan Menteri ESDM No. 188.K/TL.03/MEM.L/2025).

REGION_CF_DEFAULT: float = 0.20
# System-level assumed capacity factor for RUPTL-planned solar in GEAS allocation.
# Source: METHODOLOGY_CONSOLIDATED.md Section 5.3.
# Rationale: 20% is a reasonable aggregate CF for utility-scale solar across Indonesia's
# grid systems; site-specific CFs are used for KEK LCOE but this system average is used
# to estimate total RUPTL-derived green energy supply.

# ─── DEMAND ESTIMATION ────────────────────────────────────────────────────────

BUILDING_INTENSITY_KWH_M2_YR: dict[str, float] = {
    "Industri": 120.0,
    "Industri dan Pariwisata": 184.0,
    "Pariwisata": 280.0,
    "Jasa lainnya": 200.0,
}
# Electricity intensity of *built structures* within the zone (kWh/floor-area-m²/yr).
# Calibrated against PLN Statistics 2023 (Table 12: industrial voltage class sales) and
# ESDM Handbook 2023 (§5.1.1 industry electricity 115,341 GWh; §5.3.1 commercial 77,176 GWh).
#   - Industri: 120 kWh/m²/yr — Indonesian light manufacturing (garments, electronics, food
#     processing). PLN I-4 anchor tenants average 179 GWh/yr (127 customers nationwide).
#     Range: 80–180 kWh/m²/yr.
#   - Pariwisata: 280 kWh/m²/yr — tropical resort hotels (heavy AC, pools, F&B). ESDM
#     commercial sector is 90.5% electrified (§5.3.2), confirming very high electricity share.
#     Range: 200–400 kWh/m²/yr.
#   - Jasa lainnya: 200 kWh/m²/yr — tropical offices/retail. Similar ESDM §5.3 calibration.
#     Range: 150–280 kWh/m²/yr.
#   - Industri dan Pariwisata: 184 kWh/m²/yr — weighted average: 0.6 × Industri + 0.4 × Pariwisata.
# Source: notebooks/research_demand_intensity.ipynb; docs/demand_intensity_research_summary.csv.
# ⚠️ PROVISIONAL — replace with KEK-specific tenant load surveys when available.

BUILDING_FOOTPRINT_RATIO: dict[str, float] = {
    "Industri": 0.55,
    "Industri dan Pariwisata": 0.40,
    "Pariwisata": 0.18,
    "Jasa lainnya": 0.40,
}
# Share of total declared zone area (Luas_ha from kek_polygons.geojson) that is active
# building footprint. The remainder is roads, green space, undeveloped buffer, beach/waterfront.
#   - Industri 0.55: factory + warehouse buildings dense; roads and utilities take ~45%.
#   - Pariwisata 0.18: resort/beach zones — hotels/villas spread across beach, mangroves, golf.
#     Only 15–25% of the declared area is actual building footprint.
#   - Jasa lainnya 0.40: offices + car parks + landscaping; denser than tourism, less than industry.
#   - Industri dan Pariwisata 0.40: weighted average: 0.6 × 0.55 + 0.4 × 0.18.
# Source: notebooks/research_demand_intensity.ipynb; BPS industrial census land-use calibration.
# ⚠️ PROVISIONAL — expert judgment; update with cadastral land-use data when available.

ENERGY_INTENSITY_MWH_PER_HA_YR: dict[str, float] = {
    k: round(BUILDING_INTENSITY_KWH_M2_YR[k] * BUILDING_FOOTPRINT_RATIO[k] * 10, 1)
    for k in BUILDING_INTENSITY_KWH_M2_YR
}
# Annual electricity demand per hectare of zone area, by JenisKEK category.
# Derived: building_intensity_kwh_m2 × footprint_ratio × 10
#   (unit conversion: kWh/m² × 10,000 m²/ha ÷ 1,000 kWh/MWh = kWh/m² × 10 → MWh/ha)
# Central values: Industri=660.0, Industri dan Pariwisata=736.0, Pariwisata=504.0, Jasa lainnya=800.0
# Source: notebooks/research_demand_intensity.ipynb; docs/demand_intensity_research_summary.csv.
# ⚠️ PROVISIONAL — all demand estimates using these intensities should set is_demand_provisional=True.

ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR: float = round(
    sum(ENERGY_INTENSITY_MWH_PER_HA_YR.values()) / len(ENERGY_INTENSITY_MWH_PER_HA_YR), 1
)
# Fallback intensity for KEKs with unknown or unmapped JenisKEK.
# Value = simple average of the four derived categories (= 675.0 MWh/ha).
# Source: derived from ENERGY_INTENSITY_MWH_PER_HA_YR values above.

DEMAND_TARGET_YEAR: int = 2030
# Target year for demand estimation. Matches the RUPTL and LCOE horizon.
# Source: consistent with RUPTL_PRE2030_END and model target_year default.

# ─── DERIVED (convenience) ────────────────────────────────────────────────────


def rp_kwh_to_usd_mwh(rp_kwh: float, idr_usd: float = IDR_USD_RATE) -> float:
    """Convert Rp/kWh → USD/MWh at the reference IDR/USD rate."""
    return round(rp_kwh * 1_000.0 / idr_usd, 2)


TARIFF_I3_USD_MWH: float = rp_kwh_to_usd_mwh(TARIFF_I3_LWBP_RP_KWH)
TARIFF_I4_USD_MWH: float = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH)
