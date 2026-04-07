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
# Source: METHODOLOGY.md Section 2.2 — "1,200–2,200 kWh/kWp/yr for Indonesian latitudes."
# Values below this indicate a unit error (daily value passed as annual) or bad coordinate.

PVOUT_ANNUAL_MAX: float = 2_200.0
# Upper plausibility bound for annual PVOUT in Indonesia (kWh/kWp/yr).
# Source: METHODOLOGY.md Section 2.2.

KM_PER_DEGREE_LAT: float = 111.32
# Approximate kilometres per degree of latitude (Earth mean radius = 6,371 km).
# Used in 50 km buffer calculation for best-PVOUT search radius.
# Source: geodetic constant, valid to ~0.1% accuracy across Indonesia's latitude range.

PVOUT_BUFFER_KM: float = 50.0
# Search radius (km) for best-within-radius PVOUT extraction from GeoTIFF.
# Source: METHODOLOGY.md Section 2.4.
# Rationale: 50 km captures typical industrial park siting flexibility (land constraints,
# grid connection distance) without expanding into a different solar resource regime.

PVOUT_SOURCE: str = "GlobalSolarAtlas-v2"
# Name tag for PVOUT raster provenance.
# Source: https://globalsolaratlas.info — World Bank / Solargis, Long-Term Average (LTAym).

# ─── LCOE MODEL ───────────────────────────────────────────────────────────────

WACC_VALUES: list[float] = [4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
# WACC sensitivity range (%) for precomputed LCOE table. 2% steps, 4–20%.
# Source: METHODOLOGY.md Section 3.3.
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
# Source: METHODOLOGY.md Section 3.3.
# Rationale: 10% reflects typical Indonesian IPP project finance cost of capital.
# Note: pass as decimal to lcoe_solar() → BASE_WACC / 100 = 0.10.

BASE_WACC_DECIMAL: float = BASE_WACC / 100.0
# BASE_WACC expressed as a decimal for direct use in lcoe_solar(wacc=...).

CAPEX_USD_PER_KW_MIN: float = 200.0
# Lower CAPEX plausibility bound (USD/kW). Below this = unit error (MUSD/MWe not converted).
# Source: METHODOLOGY.md Section 3.2.

CAPEX_USD_PER_KW_MAX: float = 4_000.0
# Upper CAPEX plausibility bound (USD/kW). Above this = likely unit error.
# Raised from 3000 to 4000 to accommodate wind CAPEX ($2,350 upper) + gen-tie adder.
# Source: METHODOLOGY.md Section 3.2.

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

# ─── GEN-TIE LINE COST (remote captive scenario) ──────────────────────────────

GENTIE_COST_PER_KW_KM: float = 5.0
# Gen-tie transmission line construction cost per kW of capacity per km of line length.
# Source: METHODOLOGY.md Section 2A.2 — industry benchmark range $3–10/kW-km.
# Rationale: Central estimate used for base-case remote captive LCOE; presented as an
# assumption in the dashboard. Sensitivity (low=$3, high=$10) deferred to Phase 3.
# Note: Applies to MV/HV transmission lines to nearest PLN substation; does not include
# land/ROW acquisition costs (typically developer-negotiated, not capitalized at $/kW-km).

SUBSTATION_WORKS_PER_KW: float = 150.0
# Capital cost of substation works (step-up transformer, protection systems, metering)
# at both the generator and PLN substation ends, per kW of generating capacity.
# Source: METHODOLOGY.md Section 2A.2 — industry benchmark range $100–200/kW.
# Rationale: Central estimate. PLN typically takes ownership of the gen-tie and substation
# works post-commissioning (Permen ESDM No. 27 Tahun 2017).

# ─── TRANSMISSION LEASE ADDER (remote captive scenario) ───────────────────────

TRANSMISSION_LEASE_LOW_USD_MWH: float = 5.0
# Operating cost of transmitting energy from a remote captive solar plant to the KEK
# via the PLN grid — optimistic case.
# Components: PLN wheeling tariff + grid backup reserve charge.
# Source: METHODOLOGY.md Section 5.5 — industry estimate range $5–15/MWh.
# Applies only to remote_captive siting scenario (within_boundary has no transmission lease).

TRANSMISSION_LEASE_HIGH_USD_MWH: float = 15.0
# Transmission lease adder — conservative case. Source: METHODOLOGY.md Section 5.5.

TRANSMISSION_LEASE_MID_USD_MWH: float = (
    TRANSMISSION_LEASE_LOW_USD_MWH + TRANSMISSION_LEASE_HIGH_USD_MWH
) / 2
# Mid-point transmission lease adder = $10/MWh.

# ─── PROJECT VIABILITY THRESHOLD ──────────────────────────────────────────────

PROJECT_VIABLE_MIN_MWP: float = 20.0
# Minimum max_captive_capacity_mwp for a project to be considered commercially viable.
# Below 20 MWp, fixed development costs (permitting, legal, engineering) typically make
# projects marginal for an IPP developer. DFI investors typically screen at ≥ 33 MWp
# (≥ 50 ha at 1.5 ha/MWp). 20 MWp is the conservative lower bound.
# Source: METHODOLOGY.md Section 2.5 (minimum contiguous area discussion).

# ─── FIRMING / WHEELING ADDER ─────────────────────────────────────────────────

FIRMING_ADDER_LOW_USD_MWH: float = 6.0
# All-in captive solar cost adder — optimistic case.
# Components: grid backup (~$3–8/MWh effective), wheeling (~$2–5/MWh), PLN permitting (~$1–3/MWh).
# Source: METHODOLOGY.md Section 5.5, industry estimates.

FIRMING_ADDER_HIGH_USD_MWH: float = 16.0
# All-in captive solar cost adder — conservative case.
# Source: METHODOLOGY.md Section 5.5.

FIRMING_ADDER_MID_USD_MWH: float = (FIRMING_ADDER_LOW_USD_MWH + FIRMING_ADDER_HIGH_USD_MWH) / 2
# Mid-point adder = $11/MWh.

# ─── ACTION FLAG THRESHOLDS ───────────────────────────────────────────────────

FIRMING_PVOUT_THRESHOLD: float = 1_550.0
# Minimum annual PVOUT (kWh/kWp/yr) for a zone to be considered solar-attractive.
# Source: METHODOLOGY.md Section 5.2.
# Rationale: Below ~1,550 kWh/kWp/yr (~18% CF), intermittency risk is high enough that
# firming (BESS or hybrid) is typically required to meet industrial load profiles.

PLAN_LATE_POST2030_SHARE_THRESHOLD: float = 0.60
# Share of RUPTL solar additions post-2030 above which grid planning is flagged late.
# Source: METHODOLOGY.md Section 5.2.
# Rationale: ≥60% post-2030 means most grid upgrades won't be ready to support KEK solar by 2030.

FIRMING_RELIABILITY_REQ_THRESHOLD: float = 0.75
# Minimum reliability requirement (0–1) above which firming_needed is flagged.
# Source: METHODOLOGY.md Section 5.2.
# Rationale: Industrial zones with ≥75% reliability requirement need BESS or grid backup
# to guarantee uptime — LCOE alone understates true cost.

GEAS_GREEN_SHARE_SOLAR_NOW_THRESHOLD: float = 0.30
# Minimum GEAS green share (0–1) required to trigger solar_now flag.
# Source: METHODOLOGY.md Section 5.2 (solar_now condition: GEAS ≥ 30%).
# Rationale: 30% green share means at least 30% of the KEK's demand can be covered by
# RUPTL-allocated solar — enough to make a captive project economically viable.

RESILIENCE_LCOE_GAP_THRESHOLD_PCT: float = 20.0
# Maximum LCOE premium (%) above grid cost for a KEK to still qualify as invest_resilience.
# Source: METHODOLOGY.md Section 5.3 (Resilience Layer).
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
# Source: METHODOLOGY.md Section 5.2 (plan_late threshold definition).

RUPTL_POST2030_END: int = 2034
# Last year in the RUPTL 2025–2034 horizon.
# Source: RUPTL PLN 2025-2034 (Keputusan Menteri ESDM No. 188.K/TL.03/MEM.L/2025).

REGION_CF_DEFAULT: float = 0.20
# System-level assumed capacity factor for RUPTL-planned solar in GEAS allocation.
# Source: METHODOLOGY.md Section 5.3.
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
