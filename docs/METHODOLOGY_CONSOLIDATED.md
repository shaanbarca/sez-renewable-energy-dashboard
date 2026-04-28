# Methodology: Indonesia KEK Clean Power Competitiveness Model

**Version:** 3.7 (Consolidated, April 2026)
**Status:** Implemented in code. 81 sites (25 KEKs + 56 industrial: 32 cement + 17 steel + 5 fertilizer + 2 aluminium + 10 nickel IIA), 541 tests passing. CBAM Layer 3 complete (68/81 sites exposed; Scope 2 RE savings bounded by `CBAM_RE_ADDRESSABLE_FRACTION` per sector to reflect the electric share of thermal-inclusive intensity values — see §4.1), hybrid optimization, panel degradation modeled, site selection driven by GEM/CGSP trackers. Ammonia + petrochemical scaffolding in place pending top-down universe discovery (TODOS M28/M29).
**Intended audience:** Energy economists, development bank analysts, policy makers, peer reviewers
**Supersedes:** `METHODOLOGY.md` (v0.4), `docs/METHODOLOGY_V2.md` (draft), `docs/methodology_testing.md` (research notes)

This document is the single authoritative methodology reference for the Indonesia KEK Power Competitiveness tool. It consolidates all prior versions into one coherent specification that matches the current codebase (as of April 2026).

**Cost-column taxonomy.** Every `$/MWh` field in the model is catalogued in [`docs/TAXONOMY.md`](TAXONOMY.md). Three stacked tiers (T1 generation → T2 firmed → T3 tenant-delivered) plus a grid benchmark (B) the stack gets compared against. Read that first if you are confused about which LCOE is which. Note: "blended" appears in two different meanings in this doc (§5.4 delivered cost = captive+grid blend; §6A.3 hybrid LCOE = solar+wind blend). TAXONOMY.md §4.1 flags the collision and proposes the rename.

---

## Table of Contents

- [1. Core Question and Scope](#1-core-question-and-scope)
- [2. Data Flow Summary](#2-data-flow-summary)
- [3. Solar Resource](#3-solar-resource)
  - [3.1 PVOUT extraction](#31-pvout-extraction)
  - [3.2 Capacity factor](#32-capacity-factor)
  - [3.3 Buildability filters](#33-buildability-filters)
  - [3.4 Solar site coordinates](#34-solar-site-coordinates)
- [4. Wind Resource](#4-wind-resource)
- [5. Siting Scenarios](#5-siting-scenarios)
  - [5.1 Within-boundary (captive)](#51-within-boundary-captive)
  - [5.2 Grid-connected solar](#52-grid-connected-solar)
  - [5.3 Why remote captive was removed](#53-why-remote-captive-was-removed)
  - [5.4 Supply Blend (cascaded delivered cost)](#54-supply-blend-cascaded-delivered-cost)
- [6. LCOE Formula](#6-lcoe-formula)
  - [6.1 Base LCOE](#61-base-lcoe)
  - [6.2 Grid-connected LCOE](#62-grid-connected-lcoe)
  - [6.3 BESS storage model](#63-bess-storage-model)
  - [6.4 Technology parameters](#64-technology-parameters)
  - [6.5 WACC](#65-wacc)
  - [6.6 LCOE bands](#66-lcoe-bands)
- [7. Grid Cost Reference](#7-grid-cost-reference)
  - [7.1 I-4 industrial tariff](#71-i-4-industrial-tariff)
  - [7.2 BPP generation cost](#72-bpp-generation-cost)
  - [7.3 Benchmark mode](#73-benchmark-mode)
- [8. Three-Point Proximity and Grid Integration](#8-three-point-proximity-and-grid-integration)
  - [8.1 Three geographic points](#81-three-geographic-points)
  - [8.2 Grid integration categories](#82-grid-integration-categories)
  - [8.3 Threshold values](#83-threshold-values)
  - [8.4 Substation capacity check](#84-substation-capacity-check)
  - [8.5 Inter-substation connectivity](#85-inter-substation-connectivity)
  - [8.6 Infrastructure cost layers](#86-infrastructure-cost-layers)
- [9. Competitiveness Metrics](#9-competitiveness-metrics)
  - [9.1 Solar competitive gap](#91-solar-competitive-gap)
  - [9.2 Carbon breakeven price](#92-carbon-breakeven-price)
  - [9.3 Flip scenario](#93-flip-scenario)
  - [9.4 Solar supply coverage](#94-solar-supply-coverage)
  - [9.5 Firm solar coverage (V3.3)](#95-firm-solar-coverage-v33)
- [10. Action Flags](#10-action-flags)
  - [10.1 Flag definitions (10 solar-mode flags; 14 total across all energy modes)](#101-flag-definitions-10-solar-mode-flags-14-total-across-all-energy-modes)
  - [10.2 Priority ordering](#102-priority-ordering)
  - [10.3 solar_attractive definition](#103-solar_attractive-definition)
  - [10.4 invest_resilience rationale](#104-invest_resilience-rationale)
  - [10.5 CostBasis resolver (M31)](#105-costbasis-resolver-m31)
- [11. GEAS Green Share](#11-geas-green-share)
- [12. DFI Grid Infrastructure Investment Model](#12-dfi-grid-infrastructure-investment-model)
- [13. Captive Power Context](#13-captive-power-context)
  - [13.1 Data sources](#131-data-sources)
  - [13.2 Spatial matching](#132-spatial-matching)
  - [13.3 Perpres 112/2022 compliance](#133-perpres-1122022-compliance)
  - [13.4 Scorecard fields](#134-scorecard-fields)
  - [13.5 Map overlays](#135-map-overlays)
- [14. EU CBAM Exposure](#14-eu-cbam-exposure)
  - [14.1 CBAM signal detection](#141-cbam-signal-detection)
  - [14.2 Product-specific parameters](#142-product-specific-parameters)
  - [14.3 Emission intensity calculation](#143-emission-intensity-calculation)
  - [14.4 CBAM cost trajectory](#144-cbam-cost-trajectory)
  - [14.5 CBAM-adjusted competitive gap](#145-cbam-adjusted-competitive-gap)
  - [14.6 Per-product breakdown](#146-per-product-breakdown)
- [15. User-Adjustable Parameters](#15-user-adjustable-parameters)
- [16. Known Limitations](#16-known-limitations)
- [17. Codebase Audit Notes](#17-codebase-audit-notes)
- [18. Assumptions Summary](#18-assumptions-summary)
- [19. Reproducibility](#19-reproducibility)
- [20. Regulatory References](#20-regulatory-references)
- [References](#references)
- [Appendix A: Buildability Filter Details](#appendix-a-buildability-filter-details)
- [Appendix B: Legal Framework for Captive Solar](#appendix-b-legal-framework-for-captive-solar)
- [Appendix C: Evolution from V1 to V3](#appendix-c-evolution-from-v1-to-v3)

---

## 1. Core Question and Scope

**Question:** For each Indonesian industrial site (25 KEKs + 56 priority industrial plants/clusters), where do good solar sites, grid infrastructure, and industrial demand overlap, and what grid investment is needed to connect them?

**Unit of analysis:** Industrial site (81 sites). Site types: `kek` (25), `standalone` (46 individual heavy-industry plants), `cluster` (10 multi-plant industrial areas, mostly nickel IIAs). Results are at site level, not tenant or project level.

### 1.1 Site selection methodology

Site inclusion is **pipeline-driven and reproducible** from public trackers, not hand-curated. The master dimension table `dim_sites.csv` unions three streams inside `src/pipeline/build_industrial_sites.py`:

| Sector | Source | Filter rule | Count |
|---|---|---|---|
| KEKs | OSS/KEK portal scrape (`notebooks/kek_scraper.ipynb`) | all operating KEKs | 25 |
| Cement | GEM Global Cement Plant Tracker | `country_name == "Indonesia"` AND `status == "operating"` | 32 |
| Steel | GEM Global Iron and Steel Plant Tracker | `country_name == "Indonesia"` AND `status == "Active"` | 7 |
| Nickel | CGSP Nickel Tracker | `parent_project_type == "Integrated Industrial Area"` AND haversine ≥ 5 km from any KEK centroid; capacity aggregated from Processing children within 20 km | 10 |
| Aluminium | Residual manual (`data/industrial_sites/priority1_sites.csv`) | provenance-enforced (`source_url` required) | 2 |
| Fertilizer | Residual manual (`data/industrial_sites/priority1_sites.csv`) | provenance-enforced (`source_url` required) | 3 |

**Reproducibility enforcement:** `_load_residual_manual_rows()` in `build_industrial_sites.py` raises at pipeline-build time if any row is missing `source_url`. Residual CSV rows must populate `source_name`, `source_url`, `retrieved_date` so every analytical fact is verifiable against a stable URL.

**Known data gaps:**
- Palu SEZ (Kawasan Ekonomi Khusus Palu) is both a KEK and a CGSP IIA — the 5 km haversine filter excludes it from the CGSP cluster stream to prevent double-counting.
- Two nickel IIA clusters (IKIP, Stardust Estate Investment) have `capacity_annual_tonnes = NaN` because their nearest CGSP Processing children lie 37 km and 21 km away — outside the 20 km aggregation window. Documented as TODO M27 (widen radius, fix upstream geocodes, or add a manual override map).
- Aluminium and fertilizer have no free global tracker, so those 5 rows remain in the residual CSV pending an integration path (TODOs M25/M26).

**Technology scope:** Utility-scale ground-mounted solar PV (ESDM TECH006) and onshore wind (TECH_WIND_ONSHORE). The model computes LCOE for both and selects the cheaper option as `best_re_technology`.

**Time horizon:** Current economics (2023-2025 cost vintage). No forward cost projections.

**Two siting scenarios per KEK:**
1. **Within-boundary** (captive solar inside the KEK, behind-the-meter)
2. **Grid-connected solar** (IPP builds near best solar site, sells to PLN via PPA, PLN delivers to KEK)

---

## 2. Data Flow Summary

```
Step 1 — Solar resource
  PVOUT_annual = PVOUT_daily x 365    [kWh/kWp/yr]
  CF = PVOUT_annual / 8,760

Step 2 — LCOE
  CRF = WACC x (1+WACC)^n / ((1+WACC)^n - 1)
  LCOE = (CAPEX x CRF + FOM) / (CF x 8.76)    [USD/MWh]

Step 2b — Wind resource
  CF_wind = f(wind_speed_100m)    (piecewise-linear)
  Wind LCOE via same CRF formula with wind-specific CAPEX/FOM/lifetime

Step 3 — Grid cost reference
  I-4/TT tariff = 996.74 Rp/kWh ~ \$63.1/MWh (uniform nationwide)
  BPP varies by PLN system (\$57-133/MWh)
  Benchmark mode (user-selectable): tariff or BPP

Step 4 — Competitiveness gap
  gap = (LCOE - C_grid) / C_grid x 100%

Step 5 — Action flags (14 flags across 4 energy modes, priority-ordered; includes `cbam_urgent`)
  solar_now | invest_transmission | invest_substation | grid_first
  invest_battery | invest_resilience | plan_late | not_competitive | no_solar_resource
```

### Key inputs and sources

| Input | Value / Range | Source |
|-------|--------------|--------|
| PVOUT | 1,296-1,730 kWh/kWp/yr (extracted) | Global Solar Atlas v2 GeoTIFF |
| Solar CF | 0.148-0.197 | Derived: PVOUT / 8,760 |
| Wind speed (100m) | 2-8 m/s | Global Wind Atlas v3 GeoTIFF |
| Wind CF | 0.00-0.27 | Piecewise-linear from wind speed |
| Solar CAPEX (central) | 850 USD/kW | Market-adjusted 2025 (ESDM 2023 = 960; IRENA RPGC 2024 Indonesia = \$800-1,000) |
| Solar FOM | 7.5 USD/kW/yr | ESDM Tech Catalogue 2023, p.66 |
| Solar lifetime | 27 years | ESDM Tech Catalogue 2023, p.66 |
| WACC | 4-20% (slider, default 10%) | User-adjustable |
| Grid cost (tariff mode) | \$63.1/MWh (I-4/TT) | Permen ESDM No.7/2024, uniform nationwide |
| Grid cost (BPP mode) | \$57-133/MWh by region | Kepmen ESDM 169/2021 |

---

## 3. Solar Resource

### 3.1 PVOUT extraction

**Source:** Global Solar Atlas v2 (World Bank / Solargis), long-term average (LTAym)
**Layer:** PVOUT (Photovoltaic Power Output)
**Native unit:** kWh/kWp/day (average daily totals)

**Annual conversion:**

$$\text{PVOUT}_{\text{annual}} = \text{PVOUT}_{\text{daily}} \times 365 \quad [\text{kWh/kWp/yr}]$$

**Plausibility bounds:** 1,200 <= PVOUT_annual <= 2,200 kWh/kWp/yr.

Two PVOUT values per KEK:

| Field | Definition | Use |
|-------|-----------|-----|
| `pvout_centroid` | PVOUT at KEK centroid | Within-boundary LCOE |
| `pvout_buildable_best_50km` | Max PVOUT within 50km, filtered through buildability layers | Grid-connected solar LCOE |

**Radius calculation:** 50km in degrees is latitude-dependent:
$$\Delta\phi = \frac{50}{111.32} \qquad \Delta\lambda = \frac{50}{111.32 \cdot \cos\phi}$$

A per-pixel haversine distance mask is applied after rectangular bounding box extraction to exclude corner pixels beyond 50km.

**Implementation:** `src/pipeline/build_fct_kek_resource.py`

### 3.2 Capacity factor

$$CF = \frac{\text{PVOUT}_{\text{annual}}}{8{,}760}$$

The formula assumes PVOUT represents a fixed-tilt, grid-connected PV system at standard conditions (Global Solar Atlas definition). Global Solar Atlas uses the Faiman thermal model for temperature-dependent efficiency, so a ~3-5% production reduction from Indonesia's ambient temperatures (27-33C) is already reflected.

**Degradation (V3.4):** Panel output degrades ~0.5%/yr (`SOLAR_DEGRADATION_ANNUAL_PCT`). The LCOE formula applies a midpoint linear approximation:

$$\text{degradation\_factor} = 1 - \frac{\text{rate} \times \text{lifetime}}{2}$$

Over 27yr at 0.5%/yr: factor = 0.9325, LCOE increases ~7.2%. This is more accurate than the constant-CF assumption while avoiding year-by-year geometric degradation (which yields a nearly identical result for screening purposes). Source: NREL "Photovoltaic Degradation Rates" (Jordan & Kurtz, 2013), median 0.5%/yr for crystalline silicon.

### 3.3 Buildability filters

PVOUT is a resource measure, not a siting viability measure. Four filter layers constrain the practically achievable resource:

```
Candidate zone (50km radius)
  -> Layer 1: Hard regulatory exclusions (Kawasan Hutan, peatland)
       -> Layer 2: Terrain suitability (slope, elevation)
            -> Layer 3: Land cover (ESA WorldCover — forest, urban, water, cropland)
                 -> Layer 4: Minimum contiguous area (>= 10 ha buildable patch)
                      -> pvout_buildable_best_50km
```

**Current status:** All 4 layers active. `resource_quality = "filtered"` when all files present. 7/25 KEKs show zero buildable area due to Kawasan Hutan overlap.

| Layer | Dataset | Status |
|-------|---------|--------|
| Kawasan Hutan (66K polygons) | KLHK Sep 2017 | Active |
| Peatland (1,524 features) | KLHK vector boundaries | Active |
| ESA WorldCover 10m | 2021 v200 | Active |
| DEM slope >8 deg / elevation >1,500m | Copernicus GLO-30 | Active |
| Road proximity (>10km from motorable road) | OSM via Geofabrik PBF | Active |
| Flood hazard | BNPB | Deferred |

**Resolution note:** The PVOUT raster is ~1km resolution (~86 ha/pixel). Layer 4 is a near-no-op at this resolution. See Appendix A for full filter specifications.

**Buildable land polygons (implemented).** Contiguous buildable pixels are vectorized into polygon objects by `build_buildable_polygons.py`, each with area (ha), max capacity (MWp), centroid, and average PVOUT. These are displayed on the map as the "Solar Buildable Areas" layer (clickable popups). When a KEK is selected, a within-boundary overlay clips buildable polygons to the KEK boundary using `get_within_boundary_buildable()` in `map_layers.py`. The clipping applies a 220m buffer (`BUFFER_DEG = 0.002`) to catch near-miss polygons from raster vectorization, then intersects with the actual KEK polygon. Within-boundary area is capped at the KEK polygon's geographic area to prevent inflation when coarse raster pixels (~1,370 ha each) partially overlap small KEKs. Resolution note: at ~1km PVOUT resolution, polygon boundaries are approximate (~500m accuracy).

### 3.4 Solar site coordinates

The pipeline records **`best_solar_site_lat`** and **`best_solar_site_lon`** for the pixel where `pvout_buildable_best_50km` was found. These coordinates feed the three-point proximity analysis (Section 8). Accuracy: ~500m (1km raster resolution).

**Implementation:** `build_fct_kek_resource.py` outputs `fct_kek_resource.csv` with `best_solar_site_lat`, `best_solar_site_lon`, `best_solar_site_dist_km` columns. 18/25 KEKs have valid solar site coordinates.

---

## 4. Wind Resource

**Source:** Global Wind Atlas v3 (DTU / World Bank), mean annual wind speed at 100m hub height.

Same 50km radius extraction as solar. Two values per KEK: `wind_speed_centroid_ms` and `wind_speed_best_50km_ms`.

**Capacity factor mapping** (piecewise-linear, calibrated to Indonesian conditions):

| Wind speed (m/s) | CF | Context |
|---|---|---|
| <= 3.0 | 0.00 | Below cut-in |
| 4.0 | 0.08 | Marginal |
| 5.0 | 0.15 | Low wind |
| 6.0 | 0.22 | Moderate |
| 7.5 | 0.27 | ESDM catalogue central CF |
| 8.5 | 0.32 | IEC Class II/III boundary |
| 10.0 | 0.38 | Excellent |
| >= 12.0 | 0.42 | Plateau |

**Reference turbine:** Vestas V126/3.45 MW (IEC Class III, low-wind). Calibrated to ESDM Technology Catalogue 2024, p.90.

Wind LCOE uses the same CRF annuity formula as solar with wind-specific CAPEX/FOM/lifetime from `dim_tech_cost_wind`. **No panel degradation is applied to wind** (`degradation_annual_pct=0.0`); mechanical wear is captured in FOM.

The scorecard compares solar and wind LCOE per KEK. The cheaper technology is stored as `best_re_technology` (`"solar"` or `"wind"`).

**CF source distinction:** Wind LCOE uses `cf_wind_best_50km` (theoretical best site within 50km, regardless of buildability), while wind supply coverage uses `cf_wind_buildable_best` (best site that passes land-use filters). These can differ by 2-3x when the best wind pixel falls on protected forest or steep terrain. This parallels solar, where LCOE uses `pvout_best_50km` and supply coverage uses buildable capacity. The LCOE represents theoretical potential at the best accessible site; supply coverage represents what's actually deployable.

**Implementation:** `wind_speed_to_cf()` in `basic_model.py`; `build_fct_kek_wind_resource.py`; `build_fct_lcoe_wind.py`

### 4.1 Wind Buildability Filters

Wind uses a 5-layer exclusion cascade, adapted from solar (Appendix A) with wind-specific thresholds:

| Layer | Solar | Wind | Rationale |
|-------|-------|------|-----------|
| Kawasan Hutan | Excluded | Excluded | Same regulatory hard exclusion |
| Peatland | Excluded | Excluded | Same PP 57/2016 restriction |
| Land cover (ESA WorldCover) | Tree, crop, urban, water excluded | Tree, urban, water excluded; **cropland allowed** | Wind turbines coexist with agriculture |
| Slope | > 8 deg excluded | > 20 deg excluded | Wind turbines tolerate steeper terrain than solar arrays |
| Elevation | > 1,500m excluded | > 1,500m excluded | Same access cost constraint |
| Wind speed minimum | N/A | < 3.0 m/s excluded | Below cut-in speed, zero generation |
| Minimum contiguous area | 10 ha | 50 ha | Wind farms require larger contiguous parcels |
| Area density | ~1.5 ha/MWp (solar) | 25 ha/MWp (wind) | Wind turbine spacing (5-7 rotor diameters) |

**Pipeline:** `build_wind_buildable_raster.py` produces `buildable_wind_web.tif`. `build_wind_buildable_polygons.py` vectorizes to `wind_buildable_polygons.geojson` (3,402 polygons). `wind_buildability_filters.py` defines filter thresholds.

**Memory-efficient processing:** The raster pipeline uses `rasterio.band()` lazy references with `Resampling.mode` to stream the 10m ESA WorldCover VRT without loading it into memory. Each filter layer is applied as an intermediate step file.

---

## 4A. Rooftop Solar Potential

Per-site rooftop nameplate ceiling derived from Google Open Buildings v3 (vintage 2023-05). Distinct from §3 ground-mount potential — this counts **panels-on-existing-roofs**, the kind of distributed solar that lives behind the meter at industrial parks and tenant facilities. See [docs/rooftop_solar_potential_feature_spec.md](rooftop_solar_potential_feature_spec.md) for the full v4.1 spec.

### 4A.1 Pipeline

Single entry point — `load_buildings_for_pipeline()` in `src/pipeline/build_fct_site_solar_potential.py` (spec §13.10 invariant 4). Both the aggregator (`build_fct_site_solar_potential.py`) and tile generator (`build_rooftop_tiles.py`) read through this loader so any change to the building set propagates to both.

```
preprocess_open_buildings.py  →  sites_buildings_filtered.parquet (raw, 102k buildings × 81 sites)
       ↓
load_buildings_for_pipeline()  ←  Site polygon clip (§4A.4)
       ↓
classify_building() per row    ←  §4A.2 §14 classifier
       ↓
fct_site_solar_potential.csv   →  18 columns per site
sites_rooftop_tiles.parquet    →  703k panel-tile polygons (visual sanity-check overlay)
```

### 4A.2 §14 building classifier

GoB v3 detects every above-ground structure (warehouses, tanks, silos, conveyors, cooling towers). A naive `footprint × usable_share × W/m²` overstates rooftop potential by 30–50% on heavy industry sites. The classifier applies geometric filters on each polygon (in EPSG:23830 metric units) and assigns a usability multiplier:

| Category         | Heuristic                                         | Usability |
|------------------|---------------------------------------------------|-----------|
| `too_small`      | area < 200 m²                                     | 0.0       |
| `tank_silo`      | circularity > 0.85                                | 0.0       |
| `conveyor`       | aspect_ratio > 15                                 | 0.1       |
| `complex`        | hull_ratio < 0.55                                 | 0.2       |
| `possibly_round` | 0.75 < circularity ≤ 0.85                         | 0.3       |
| `elongated`      | 5 ≤ aspect_ratio ≤ 15                             | 0.6       |
| `standard_roof`  | passes all filters                                | 1.0       |

Cascade — first match wins. Hard rejects (tank, conveyor, complex) precede soft derates. Thresholds live in `src/assumptions.py` (`BUILDING_*_THRESHOLD`); calibrated against Semen Imasco Asiatic Jember in 9a61ee0 (hull_ratio 0.70 → 0.55; aspect 8 → 15) to stop dropping legitimate ~9,000 m² halls into `complex` and ~4,300 m² halls into `conveyor`.

### 4A.3 Footprint → MWp math (decomposed model, §5.3 of spec)

```
panel_density_w_per_m2 = panel_power_w_dc / panel_area_m2          (= 200 W/m²)
rooftop_kw_dc          = footprint × usability × layout_density × panel_density / 1000
rooftop_kw_ac          = rooftop_kw_dc × thermal_derate            (tropical = 0.88)
```

Defaults: `ROOFTOP_PANEL_POWER_W_DC = 400 W`, `ROOFTOP_PANEL_AREA_M2 = 2.0`, `ROOFTOP_LAYOUT_DENSITY = 0.50` (range 0.40–0.65 — accounts for inter-row spacing, parapets, HVAC, walkways), `THERMAL_DERATE_TROPICAL = 0.88`. F10 user sliders deferred to a later release.

### 4A.4 Site polygon clip

`preprocess_open_buildings.py` uses a 2 km buffer around each site centroid to assign buildings. For sites whose actual fence boundary is smaller, this over-includes adjacent residential structures, industrial parks, or open water. After preprocess, `load_buildings_for_pipeline()` applies a centroid-within-polygon filter against two polygon sources:

1. **KEK polygons** (`outputs/data/raw/kek_polygons.geojson`, 25 sites). Boundaries from official OSS/KEK portal scrapes. Handles split-island KEKs (Tanjung Sauh has 6 fragments) by dissolving on `slug`.
2. **Industrial site polygons** (`data/industrial_sites/site_polygons.geojson`, 9 sites as of 2026-04-28). OSM `landuse=industrial` and `man_made=works` polygons captured for non-KEK industrial plants where they exist: Indocement Palimanan, Cemindo Gemilang Bayah, Petrokimia Gresik, Ispat Indo Sidoarjo, Freeport Smelter Gresik, Semen Padang Indarung, Semen Baturaja, Krakatau Posco Cilegon, Gunung Raja Paksi Bekasi.

Sites without a polygon pass through unchanged — their 2 km preprocess buffer remains the catchment, with RV11 (residential-pattern filter) at the building level providing the additional precision lever. Side effect: when the OSM polygon centroid is materially off from the dim_sites centroid (Ispat Indo at 10 km, Freeport at 9.8 km, Krakatau Posco at 3 km), the polygon centroid is also captured as a coordinate override in `data/industrial_sites/coordinate_overrides.csv` — the same audit-trail layer used for the GEM tracker miscodes (Tuban, Palimanan, Narogong).

### 4A.5 Cluster aggregation (visual layer)

The tile generator runs DBSCAN (`eps = 50 m`, `min_samples = 1`) on usable buildings per site to group physically-adjacent rooftops into clusters. Each cluster gets one popup on the map showing aggregate kW + building count — the "show your work" loop (spec §3.6.1). Output: 9,622 clusters across 62 sites with ≥1 usable building (703,001 individual panel tiles, ~25 MB parquet).

### 4A.6 Confidence + missing-data flagging

A per-site confidence score (`high` / `medium` / `low`) is derived from building count and footprint-to-site-area ratio:

| Confidence | Building count | Footprint ratio  | Reason flag      |
|------------|----------------|------------------|------------------|
| high       | ≥ 10           | 0.05–0.40        | none             |
| low        | < 3            | < 0.01           | `imagery_gap`    |
| medium     | otherwise      | otherwise        | `partial`        |

Sites with zero buildings (18 of 81) are written to `sites_missing_buildings.csv` with the reason flag — spec §3.7 "flag, don't hide" rather than silently zeroing the rooftop column.

### 4A.7 Known limits

- **GoB v3 vintage.** 2023-05. Post-2023 buildings are missing entirely (TODOS RV7 — refresh when v4 ships, or fan out to Microsoft / Overture / OSM as a second source per spec §13.10 invariant 4).
- **Detection asymmetry.** Two visually-identical adjacent rooftops can produce different tile counts when GoB detected one cleanly and fragmented or missed the other (TODOS RV7).
- **Industrial catchment radius.** 2 km buffer over-counts non-roof buildings around standalone cement/steel/nickel plants (TODOS RV8).
- **Fragmented detection.** A single physical roof occasionally arrives as several `too_small` polygons; merging them before classification is an open option (TODOS RV9 — deferred pending visual validation of the merge tolerance).
- **No manual validation pass yet.** Spec §16 calls for ±20% accuracy on 10 sample sites and ≥80% classifier accuracy on 100 manually-labelled buildings before declaring v4.1 final (Phase 4).

---

## 5. Siting Scenarios

### 5.1 Within-boundary (captive)

Solar plant inside KEK boundary, behind-the-meter. No PLN involvement.

- **PVOUT source:** `pvout_centroid`
- **Who builds it:** KEK tenant or on-site IPP
- **Grid infrastructure needed:** None (internal distribution only)
- **Cost:** Base LCOE only (no connection cost, no land cost)
- **Minimum viable capacity:** 0.5 MWp (Indonesian IUPTLS regulatory threshold)
- **Buildable area visualization:** When a KEK is selected, buildable polygons within the KEK boundary are displayed as a green overlay on the map. These are clipped from the 50km-radius buildable polygons (§3.3) using the KEK polygon boundary, with a 220m buffer to catch edge polygons from raster vectorization. Metrics: `within_boundary_area_ha`, `within_boundary_capacity_mwp`, `pvout_within_boundary` (see `build_fct_kek_resource.py`).

### 5.2 Grid-connected solar

Solar farm connects to nearest PLN substation, sells to PLN via PPA. PLN delivers to KEK.

- **PVOUT source:** `pvout_buildable_best_50km`
- **Who builds it:** Independent IPP
- **Grid infrastructure needed:** Solar-to-substation connection (typically <5 km)
- **Cost:** Base LCOE + grid connection cost + land acquisition cost
- **Minimum viable capacity:** 20 MWp (utility-scale threshold, user-adjustable)

**Key insight: separation of economics.** Under this model:
1. **IPP economics:** "Can I build solar here and sell profitably to PLN?" ... solar LCOE vs. regional BPP
2. **KEK tenant economics:** "What will my electricity cost?" ... I-4 tariff (unchanged by solar procurement)
3. **Policy economics:** "Where should grid investment go?" ... three-point proximity analysis

### 5.3 Why remote captive was removed

The V1 methodology assumed KEKs could build remote captive solar connected by a private 50km gen-tie line. Research revealed:

- **No global precedent exists** for a 50km private gen-tie for captive solar. Not in Indonesia, not in India (the most mature captive solar market), not anywhere.
- **The economics don't work:** 50km of transmission infrastructure costs ~\$40-55M, rivaling the solar plant itself for 20-100 MWp projects.
- **What actually exists globally:** on-site/behind-the-meter captive (common), grid-wheeled captive via utility grid (India model), or IPP-to-utility PPA (dominant globally).
- **Indonesia-specific:** IMIP Morowali (5+ GW captive coal) builds power inside the park. PLN has rejected all wheeling requests in practice despite legal authorization.

The realistic model for delivering cheap solar to KEKs is through PLN's grid, not through private infrastructure.

### 5.4 Supply Blend (cascaded delivered cost)

**Version:** V3.11 (cascade). Replaces the V3.10 two-layer blend (captive + grid).

The `within_boundary` gate (§8.2) is binary: a site either clears the `meaningful_share_pct` threshold (after the V3.9.1 buildout-footprint haircut) and is treated as fully self-sufficient on captive solar, or it doesn't — in which case `lcoe_mid_usd_mwh` reports the grid-connected LCOE with transmission/substation/connection costs loaded onto 100% of effective capacity. Neither picture matches what an industrial tenant actually pays when on-site solar can supply, say, 16% of demand, a remote IPP with a gentie can fill another 26%, and PLN covers the rest.

**Supply Blend** fills this gap. It is a tenant-view cascade — what the load's effective $/MWh bill looks like when supply stacks across three layers in order of economic preference: within-boundary captive first, then remote captive IPP, then grid.

**Formula:**

```
daytime_cap = SOLAR_PRODUCTION_HOURS / 24         (default 10h / 24h ≈ 0.417)

f_wb        = min(within_boundary_coverage_effective_pct, daytime_cap)
headroom    = daytime_cap − f_wb
f_remote    = headroom  if gc_row exists else 0
f_grid      = 1 − f_wb − f_remote

delivered_cost_usd_mwh = f_wb × LCOE_wb + f_remote × LCOE_gc + f_grid × grid_rate
```

**Physical cap rationale.** Without BESS, solar can only serve load during daylight hours. For a flat 24/7 industrial load that caps real-time *total* solar share (on-site plus remote) at `SOLAR_PRODUCTION_HOURS / 24` ≈ 42% (10h/24h). Oversizing solar beyond daytime demand curtails the excess — it cannot roll over to overnight consumption. The remaining ~58% of annual demand is served by the grid regardless of how much solar is built. Supply Blend is *inherently* a partial blend with no storage. Full 24/7 RE coverage is the job of the Solar 24/7 basis (T2 — see §7.3 and TAXONOMY.md), which adds a BESS storage adder to bridge the overnight gap.

The ceiling matches the temporal model in §8.2 (`firm_solar_metrics`): `daytime_fraction = SOLAR_PRODUCTION_HOURS / 24`, and real-time solar share = `min(solar_gen, daytime_demand) / annual_demand`.

**Remote captive layer (directional, not optimized).** There is no pre-computed "remote captive coverage" metric in the pipeline today. We treat remote captive as *available up to the daytime ceiling* whenever the site has a grid-connected siting scenario (`gc_row` exists) — i.e., an IPP within the 50 km buffer could fill the daytime headroom. This is the directional upper bound: it tells the viewer "even maxing out solar at this site, your tenant bill looks like this." Economic optimization (would the tenant actually build remote at gc_LCOE if it exceeds grid_rate?) is deferred to a future PSA-driven pass. See TODOS.

**Glossary:**

- `within_boundary_coverage_effective_pct` — haircut-adjusted on-site coverage: `wb_coverage × wb_buildout_footprint_ratio`. Same figure the `within_boundary` gate in §8.2 checks.
- `daytime_cap` — `SOLAR_PRODUCTION_HOURS / 24` (physical ceiling on real-time solar share for a flat 24/7 industrial load).
- `LCOE_wb` — within-boundary scenario LCOE (§5.1 / §6.1): centroid PVOUT, no connection cost, no transmission build, no substation upgrade. Read from `wb_row.lcoe_mid_usd_mwh`.
- `LCOE_gc` — grid-connected scenario LCOE (§6.2): best PVOUT within 50 km, includes gen-tie + land + substation upgrade. Read from `gc_row.lcoe_mid_usd_mwh`. Represents the remote IPP's cost of delivering to the site with a dedicated transmission line.
- `grid_rate` — the regional grid reference cost the `SiteContext` resolves. Defaults to the PLN I-4/TT industrial tariff (§7.1); resolves to regional BPP (§7.2) when BPP benchmark mode is active. Same rate that feeds `solar_competitive_gap_pct`, so `delivered_cost_gap_vs_grid_pct` inherits the user's tariff/BPP toggle without a new switch.

**Degeneracy:**

- **No solar siting** (both `wb_row` and `gc_row` missing): all cascade columns null.
- **No grid access** (`gc_row` missing, `wb_row` present): pre-V3.11 two-layer behavior — `f_remote = 0`, delivered = `f_wb × LCOE_wb + (1 − f_wb) × grid_rate`.
- **No on-site siting** (`wb_row` missing, `gc_row` present): `f_wb = 0`, remote fills the cap — delivered = `daytime_cap × LCOE_gc + (1 − daytime_cap) × grid_rate`.
- **Oversized WB** (`eff_cov ≥ daytime_cap`): `f_wb` saturates at the cap, no headroom for remote.
- **Zero everywhere**: degenerates to `grid_rate` when `f_wb = 0` and no `gc_row`.

**Additive, not a replacement.** The gate-driven `lcoe_mid_usd_mwh`, `solar_competitive_gap_pct`, action flags, economic tier, carbon breakeven, and all downstream flag mechanics are unchanged. Supply Blend is a decision-support column for the tenant view. Repointing action flags / economic tier / competitive gap at the blended number is a separate methodology decision (deferred — see TODOS).

**Worked example (3-layer cascade).** Galang Batang: raw 78% within-boundary coverage × 0.20 footprint ratio = 15.68% effective. With `LCOE_wb = $81.13`, `LCOE_gc = $100.17`, and `grid_rate = $63.08` (I-4 tariff):

```
f_wb     = min(0.1568, 0.4167)       = 0.1568
headroom = 0.4167 − 0.1568            = 0.2599
f_remote = 0.2599                     (gc_row exists)
f_grid   = 1 − 0.1568 − 0.2599        = 0.5833

delivered = 0.1568 × 81.13 + 0.2599 × 100.17 + 0.5833 × 63.08
          = 12.72 + 26.03 + 36.79
          = $75.54/MWh
```

On-site solar covers 16% of the bill; a remote IPP covers another 26% (filling the daytime ceiling); grid covers 58% overnight.

**Worked example (no WB, remote fills cap).** A cement plant with no within-boundary solar but grid access — `eff_cov = 0`, `LCOE_gc = $78`, `grid_rate = $63`:

```
f_wb     = 0
f_remote = 0.4167
delivered = 0.4167 × 78 + 0.5833 × 63 = 32.5 + 36.75 = $69.25/MWh
```

**Cross-references.**
- Haircut + gate mechanics: §8.2 (Grid integration categories, V3.9 override + V3.9.1 buildout-footprint haircut).
- `LCOE_wb` and `LCOE_gc` derivation: §5.1, §6.1, §6.2.
- Grid rate resolution (tariff vs BPP): §7.1, §7.2, §7.3.
- Taxonomy and naming: TAXONOMY.md §3 (T3 Supply Blend tier).

**Implementation.** `enrich_delivered_cost()` in `src/dash/logic/scorecard.py` (appended to `STAGES` after `enrich_grid_passthroughs`). Reads `ctx.wb_row.lcoe_mid_usd_mwh`, `ctx.gc_row.lcoe_mid_usd_mwh`, `ctx.grid_cost`, and `ctx.grid_out["within_boundary_coverage_effective_pct"]`. Emits eight columns: `delivered_cost_usd_mwh`, `captive_fraction`, `delivered_cost_remote_fraction`, `grid_fraction`, `delivered_cost_grid_rate_used_usd_mwh`, `delivered_cost_wb_lcoe_used_usd_mwh`, `delivered_cost_gc_lcoe_used_usd_mwh`, `delivered_cost_gap_vs_grid_pct`. Null when both siting rows missing, or when `grid_cost ≤ 0`.

---

## 6. LCOE Formula

### 6.1 Base LCOE

$$CRF(r, n) = \frac{r \cdot (1 + r)^n}{(1 + r)^n - 1}$$

$$LCOE = \frac{CAPEX \cdot CRF + FOM}{CF \times 8.76} \quad [\text{USD/MWh}]$$

Where:
- CAPEX = capital expenditure [USD/kW]
- FOM = fixed O&M [USD/kW/yr]
- r = WACC [decimal]
- n = project lifetime [years]
- CF = capacity factor [decimal]
- 8.76 = 8,760 / 1,000 (unit conversion)

**Implementation:** `lcoe_solar()` in `src/model/basic_model.py`

### 6.2 Grid-connected LCOE

$$LCOE_{\text{gc}} = \frac{(CAPEX + C_{\text{connection}} + C_{\text{land}}) \times CRF + FOM}{CF \times 8.76}$$

Where:
- CF uses `pvout_buildable_best_50km`
- `C_connection = dist_solar_to_substation x $5/kW-km + $80/kW` (user-adjustable)
- `C_land = \$45/kW` (user-adjustable, grid-connected only)

**Connection cost parameters:**

| Parameter | Default | Range | What it covers |
|---|---|---|---|
| `CONNECTION_COST_PER_KW_KM` | \$5/kW-km | \$2-15/kW-km | MV/HV line from solar plant to PLN substation |
| `GRID_CONNECTION_FIXED_PER_KW` | \$80/kW | \$30-200/kW | Switchgear, protection, metering at substation |
| `LAND_COST_USD_PER_KW` | \$45/kW | \$0-300/kW | Land for solar farm (grid-connected only) |

**Example at defaults (5 km):**
```
Connection cost = 5 km x $5/kW-km + $80/kW = $105/kW
Effective CAPEX = $960 + $105 + $45 = $1,110/kW
```

**Global context note:** The \$5/kW-km gen-tie cost translates to real-world figures as follows: at 25 MW and 5 km, the formula gives \$105/kW x 25,000 kW = \$2.625M, which is ~\$0.5M/km, on the low end of industry benchmarks (\$1-3M/mile or \$0.6-1.9M/km). In Indonesian IPP practice, transmission corridors of 20-40 km from plant to nearest PLN substation are common (practitioner benchmark, Norton Rose Fulbright, 2020). The 5 km screening threshold is therefore an optimistic cutoff for "grid-ready" sites, not the outer limit of what gets built.

**Implementation:** `lcoe_solar_grid_connected()` and `grid_connection_cost_per_kw()` in `basic_model.py`

### 6.3 BESS storage model

V3 replaces the flat firming adder (\$6/\$11/\$16 per MWh) with a proper BESS storage cost model. V3.3 adds physically grounded bridge-hours sizing and round-trip efficiency.

**Formula (V3.3):**
```
effective_sizing_hours = sizing_hours / round_trip_efficiency
bess_capex_per_kw_solar = BESS_CAPEX_per_kWh × effective_sizing_hours
nighttime_fraction = (24 - SOLAR_PRODUCTION_HOURS) / 24
efficiency_loss = nighttime_fraction × (1 - round_trip_efficiency)
effective_CF = CF_solar × (1 - efficiency_loss)
bess_storage_adder = (bess_capex_per_kw_solar × CRF_bess + FOM_bess_adj) / (effective_CF × 8760 / 1000)
```

**Parameters:**

| Parameter | Default | Range | Source |
|---|---|---|---|
| `BESS_CAPEX_USD_PER_KWH` | \$150/kWh | \$100-300/kWh | Market-adjusted 2025 (BNEF system \$110, Ember \$125, +Indonesia premium) |
| `BESS_DISCHARGE_HOURS` | 4.0h | - | Standard 4-hour system |
| `BESS_SIZING_HOURS` | 2.0h | - | Cloud-firming default (low-reliability loads) |
| `BESS_ROUND_TRIP_EFFICIENCY` | 0.87 | 0.75-0.95 | BNEF 2024, utility-scale Li-ion LFP AC-to-AC |
| `SOLAR_PRODUCTION_HOURS` | 10.0h | - | Effective solar hours/day at equatorial Indonesia |
| `BESS_BRIDGE_HOURS_ENABLED` | True | - | Enables physics-based bridge-hours sizing |
| `BESS_LIFETIME_YR` | 15 years | - | Li-ion warranty period |
| `BESS_FOM_USD_PER_KW_YR` | \$5/kW-yr | - | Monitoring, HVAC, insurance |

**Bridge-hours sizing (V3.3):** For high-reliability loads (reliability_req >= 0.75), BESS is sized to bridge the overnight gap when solar produces nothing:

```
bridge_hours = 24 - SOLAR_PRODUCTION_HOURS = 14h
```

This replaces the fixed 2h sizing for KEKs with 24/7 industrial demand (manufacturing, smelting). The 2h default remains for low-reliability loads where BESS only needs to smooth cloud events and early evening ramp.

**Round-trip efficiency (V3.3):** Battery storage has 85-90% AC-to-AC round-trip efficiency. Energy stored overnight loses ~13%. Two adjustments:

1. **BESS capacity oversizing:** To deliver X MWh overnight, you must store X / RTE MWh. At RTE=0.87, a 14h bridge requires 14/0.87 = 16.1h of effective storage capacity. This is reflected in `effective_sizing_hours = sizing_hours / RTE`.

2. **Effective output reduction:** The BESS adder denominates against the solar energy actually available after storage losses, not the raw panel output. For a system where 58% of energy must pass through storage (14h/24h nighttime fraction), the effective CF drops: `effective_CF = CF_solar x (1 - 0.583 x 0.13) = CF_solar x 0.924`. At CF=0.18, this means the denominator uses 0.166 instead of 0.18, a ~7.6% reduction that makes the per-MWh adder higher. This is physically correct: you are paying for storage infrastructure but getting less usable energy out of it.

**Sizing logic (V3.6):**

| Load type | Condition | BESS sizing | Rationale |
|---|---|---|---|
| **User override** | `bess_sizing_hours_override` is set | 1-16h (user-set) | Explore cost tradeoffs at different storage durations via ScoreDrawer slider |
| High-reliability industrial | reliability_req >= 0.75 | 14h (bridge) | Covers 14h overnight gap for 24/7 loads |
| RKEF nickel (legacy) | dominant_process_type = "RKEF" | 4h | M19 multiplier, applies when bridge-hours disabled |
| Standard/tourism | All others | 2h | Cloud-firming and early evening ramp |

**Result at defaults (\$150/kWh, 14h bridge sizing, 87% RTE, 10% WACC, CF=0.18):** ~\$174/MWh battery adder for high-reliability loads. This is the honest cost of firming solar for 24/7 industrial demand. At 2h cloud-firming sizing: ~\$27/MWh. (Prior default of \$250/kWh produced ~\$290/MWh and ~\$45/MWh respectively.)

**Physical basis:** MacKay, *Sustainable Energy Without the Hot Air*, Ch. 26. Storage must bridge the gap between solar production hours and demand hours. At equatorial latitudes with ~10h effective solar production and 24/7 industrial demand, the overnight gap is 14h. BESS must store 14h × load_MW / RTE of energy.

**BESS competitive indicator (V3.5):** Battery economics (`battery_adder_usd_mwh`, `lcoe_with_battery_usd_mwh`) are computed for all KEKs with solar resource, not only those flagged `invest_battery`. This allows users to see the full cost of 24/7 solar+BESS for any KEK, regardless of reliability tier. A `bess_competitive` boolean indicates whether `lcoe_with_battery <= grid_cost`. This surfaces a previously hidden scenario: KEKs where daytime solar is competitive but 24/7 solar+BESS exceeds grid cost.

```
LCOE_with_battery = LCOE_solar + bess_storage_adder
```

**Implementation:** `bess_bridge_hours()`, `bess_storage_adder()`, and `lcoe_solar_with_battery()` in `basic_model.py`

### 6.4 Technology parameters

**Solar (TECH006):** ESDM Technology Catalogue 2023, p.66 (`VERIFIED_TECH006_DATA` in `pdf_extract_esdm_tech.py`). Pipeline extraction preserves the catalogue value (960 USD/kW). The user-facing slider default is market-adjusted to 850 USD/kW based on IRENA RPGC 2024 Indonesia pricing (\$800-1,000/kW range).

| Parameter | ESDM Catalogue | Slider Default | Unit |
|-----------|---------------|----------------|------|
| CAPEX (central) | 960 | 850 | USD/kW |
| CAPEX (lower) | 840 | - | USD/kW |
| CAPEX (upper) | 1,080 | - | USD/kW |
| FOM | 7.5 | 7.5 | USD/kW/yr |
| Lifetime | 27 | 27 | years |

**Wind (TECH_WIND_ONSHORE):** From ESDM Technology Catalogue 2024, p.90. CAPEX \$1,650/kW, FOM \$40/kW/yr, Lifetime 27 years.

**Unit conversion:** Catalogue stores CAPEX in MUSD/MWe. Convert: MUSD/MWe x 1,000 = USD/kW.

### 6.5 WACC

Default: 10% (ADB, 2020, SE Asia renewable energy benchmark; IRENA, 2023). Dashboard slider: 4-20% in 1% steps.

**Precomputed snap range:** `fct_lcoe` stores LCOE at 9 WACC values: [4, 6, 8, 10, 12, 14, 16, 18, 20]%. This produces 1,458 rows (81 sites x 9 WACCs x 2 scenarios).

| Range | Represents |
|-------|-----------|
| 4-6% | DFI concessional / blended finance |
| 8% | De-risked project finance. 8 KEKs flip to solar-competitive here. |
| 10% | Base case: typical Indonesian IPP |
| 12-16% | Equity premium / higher-risk |
| 18-20% | Ceiling: above 20% no renewable project closes |

### 6.6 LCOE bands

Three LCOE values per KEK per WACC: `lcoe_low` (CAPEX_lower), `lcoe_mid` (CAPEX_central, primary), `lcoe_high` (CAPEX_upper).

### 6.7 LCOE sensitivity to project scale

The dashboard includes an "LCOE vs Project Scale" chart that shows how LCOE varies with project capacity (MW). This is a **sensitivity visualization only**, it does not change the scorecard LCOE, which uses the per-kW formulas at actual capacity.

**Capacity-dependent cost components:**

| Cost | How it scales | Formula in chart |
|------|--------------|------------------|
| Connection line | Fixed total cost / capacity (economies of scale) | `(dist_km x $125k/km + $2M) / cap_kW` |
| Transmission line | Fixed total cost / capacity | `(inter_sub_dist x $1.25M/km) / cap_kW` (only if substations not connected) |
| Substation upgrade | Deficit grows with capacity (diseconomy) | `max(0, 1 - avail_mva / (cap_mw x util)) x $80/kW` |
| CAPEX, land, FOM | Constant per kW | No scale effect |

**Reference calibration:** The connection line total cost (\$125k/km) is derived from the per-kW formula at ~25MW reference scale: \$5/kW-km x 25,000 kW = \$125,000/km. The \$2M fixed cost is \$80/kW x 25,000 kW. At exactly 25MW, both formulations give the same LCOE.

**Typical curve shape:** Declining at small capacity (connection costs dominate, spread over more kW), flattening at medium capacity, potentially rising at large capacity if substation upgrade costs grow. KEKs with red capacity assessment show a more pronounced uptick at high capacity.

**Implementation:** `LcoeCurveChart.tsx` (frontend only, no backend computation).

---

## 6A. Hybrid Solar+Wind RE Framework

### 6A.1 Motivation

Solar-only 24/7 industrial supply requires 14 hours of BESS bridging (nighttime gap from 6pm to 8am). At current Li-ion costs (\$200/kWh), this adds \$160-380/MWh to solar LCOE, making firm solar structurally uneconomic for most KEKs.

Wind generation is temporally complementary: it produces power day and night with roughly uniform output across hours. Adding wind to the mix partially fills the nighttime gap, reducing BESS sizing and total system cost. A 60/40 solar/wind blend with wind covering 30% of nighttime demand can cut BESS from 14h to ~10h, saving ~\$100/MWh in storage costs.

### 6A.2 RESource abstraction

Each renewable technology is represented as an `RESource` dataclass:

| Field | Type | Solar | Wind | Hydro (future) |
|-------|------|-------|------|-----------------|
| `technology` | str | `"solar"` | `"wind"` | `"hydro"` |
| `lcoe_usd_mwh` | float | Standalone LCOE | Standalone LCOE | Standalone LCOE |
| `generation_mwh` | float | Annual generation | Annual generation | Annual generation |
| `cf` | float | Capacity factor | Capacity factor | Capacity factor |
| `nighttime_fraction` | float | 0.0 | 14/24 ≈ 0.583 | 1.0 (dispatchable) |
| `capacity_mwp` | float | Buildable capacity | Buildable capacity | Installed capacity |

Solar has `nighttime_fraction = 0.0` (zero production at night). Wind uses `14/24` (conservative: assumes uniform CF across all hours, so 14 of 24 hours fall at night). Hydro will use `1.0` (fully dispatchable baseload).

### 6A.3 Blended LCOE

Generation-weighted average across sources:

```
blended_lcoe = Σ(source_gen × source_lcoe) / Σ(source_gen)
```

For solar+wind with shares `s` and `(1-s)`:

```
blended_lcoe = (solar_gen × s × solar_lcoe + wind_gen × (1-s) × wind_lcoe)
               / (solar_gen × s + wind_gen × (1-s))
```

Blended LCOE always falls between the two standalone LCOEs. But hybrid all-in cost (LCOE + BESS) can beat both standalone technologies because the BESS reduction is nonlinear.

### 6A.4 BESS reduction formula

```
nighttime_demand = total_demand × (14/24)

For each source:
  nighttime_contribution = generation × nighttime_fraction

total_nighttime_supply = Σ(nighttime_contribution)
nighttime_coverage = min(total_nighttime_supply / nighttime_demand, 1.0)

hybrid_bess_hours = 14.0 × (1.0 - nighttime_coverage)
```

Wind's nighttime contribution = `wind_generation × (14/24)`. When wind covers 50% of nighttime demand, BESS drops from 14h to 7h.

The BESS storage adder is then computed using the existing `bess_storage_adder()` function with the reduced `hybrid_bess_hours` and the blended capacity factor.

### 6A.5 Mix ratio optimization

The optimizer sweeps `solar_share` from 0% to 100% in 5% steps (21 evaluations per KEK). For each candidate share:

1. Scale solar and wind generation by their respective shares
2. Compute blended LCOE
3. Compute hybrid BESS hours from nighttime coverage
4. Compute BESS adder using `bess_storage_adder()` with reduced hours and blended CF
5. All-in = blended LCOE + BESS adder

The share that minimizes all-in cost is selected. This is pure arithmetic, sub-ms per KEK.

**User override:** `hybrid_solar_share` in `UserAssumptions` (0.0-1.0). When set, the optimizer is bypassed and the exact specified share is used. `None` (default) = auto-optimize.

**No-wind fallback:** When `cf_wind <= 0` or wind generation is zero, the optimizer returns `solar_share = 1.0` and all hybrid fields equal their solar-only equivalents.

### 6A.6 Three-way technology comparison

`best_re_technology` compares three candidates:

| Candidate | Cost metric |
|-----------|------------|
| Solar | `lcoe_with_battery` (solar LCOE + 14h BESS adder) |
| Wind | `lcoe_wind_mid` (standalone, no BESS) |
| Hybrid | `hybrid_allin_usd_mwh` (blended LCOE + reduced BESS adder) |

The lowest all-in cost wins. Hybrid can beat both standalone technologies: it beats solar because BESS is smaller, and it can beat wind because blended LCOE is lower when solar is cheaper per MWh.

### 6A.7 Output fields

| Field | Type | Description |
|-------|------|-------------|
| `hybrid_lcoe_usd_mwh` | float | Blended LCOE before BESS |
| `hybrid_bess_hours` | float | Reduced BESS sizing (0-14h) |
| `hybrid_bess_adder_usd_mwh` | float | BESS cost at reduced sizing |
| `hybrid_allin_usd_mwh` | float | Blended LCOE + BESS adder |
| `hybrid_solar_share` | float | Optimal solar fraction (0-1) |
| `hybrid_supply_coverage_pct` | float | Combined generation / demand |
| `hybrid_nighttime_coverage_pct` | float | Wind nighttime fill fraction |
| `hybrid_bess_reduction_pct` | float | `1 - hybrid_bess_hours / 14` |
| `hybrid_carbon_breakeven_usd_tco2` | float | Carbon price for hybrid competitiveness |

### 6A.8 Hydro extensibility

When hydro proximity data ships, adding hydro requires:
1. Create `RESource(technology="hydro", nighttime_fraction=1.0, ...)` (dispatchable baseload)
2. Pass 3-element sources list to `hybrid_lcoe_optimized()`
3. Optimizer expands from 1D sweep to 2D grid (solar x wind, hydro = remainder). 231 evaluations at 5% steps, still sub-ms.

Hydro's firm nighttime output directly offsets BESS further. No refactoring needed.

**Implementation:** `src/model/basic_model.py` (`RESource`, `hybrid_bess_hours()`, `hybrid_lcoe_optimized()`), `src/dash/logic/technology.py` (`compute_hybrid_metrics()`; called per-row from `logic/scorecard.py::compute_scorecard_live()`).

---

## 7. Grid Cost Reference

### 7.1 I-4 industrial tariff

**Source:** Permen ESDM No. 7/2024, Lampiran IV
**Value:** 996.74 Rp/kWh ~ \$63.08/MWh at 15,800 IDR/USD
**Coverage:** Uniform nationwide (all KEKs pay the same)
**Use:** Primary dashboard comparator for KEK tenant economics

I-3/TM tariff (\$65.57/MWh) stored as `tariff_i3_usd_mwh` for smaller tenant analysis.

**Important:** I-4 tariff != BPP. The tariff is what tenants pay. In most regions, PLN supplies at a loss (tariff < BPP). This subsidy gap is itself policy-relevant.

### 7.2 BPP generation cost

**Source:** Kepmen ESDM 169/2021 (FY2020)
**Range:** \$57/MWh (Java-Bali) to \$133/MWh (Papua)
**Use:** Secondary comparator, primarily for IPP economics ("is solar cheaper than PLN's cost of supply?")

BPP is generation cost only (BPP Pembangkitan), not full cost-of-supply including T&D and overhead.

### 7.3 Benchmark mode

User-selectable toggle:

| Mode | Comparator | Use case |
|------|-----------|----------|
| **Tariff** (default) | I-4/TT (\$63.08/MWh) | "Can a KEK tenant save money?" |
| **BPP** | Regional BPP (\$57-133/MWh) | "Is solar cheaper than PLN's generation cost?" |

When set to BPP, competitive gap, action flags, and carbon breakeven all recompute using `bpp_usd_mwh`. Eastern Indonesia KEKs (high BPP) become solar-competitive even at WACC=10%.

**IDR/USD rate:** 15,800 (default, user-adjustable slider: 14,000-18,000). Tariff is subject to quarterly adjustment (Pasal 6, Permen ESDM No.7/2024).

---

## 8. Three-Point Proximity and Grid Integration

### 8.1 Three geographic points

| Point | Source | Description |
|---|---|---|
| **A** - Chosen solar site | `fct_site_resource` (`best_solar_site_lat/lon`) | V3.7: substation-anchored patch (lowest LCOE proxy) if one qualifies, else fallback to highest-PVOUT buildable pixel within 50km. See §8.7. |
| **B** - Nearest PLN substation | `data/substation.geojson` (2,913 substations) | Nearest to point A or C (may differ) |
| **C** - Site centroid | `dim_sites` | Geographic center of site polygon (KEK) or tracker coordinate (industrial) |

For each KEK:
- **d(A, B_solar):** solar site to nearest substation
- **d(C, B_kek):** KEK centroid to nearest substation
- B_solar and B_kek may be different substations

### 8.2 Grid integration categories

| Category | Condition | Meaning |
|---|---|---|
| `within_boundary` | Operational substation inside KEK polygon, OR within-boundary solar coverage >= `meaningful_share_pct` of demand (KEK-only) | No grid connection needed (behind-the-meter) |
| `grid_ready` | d(A, B_solar) < 5km AND d(C, B_kek) < 15km | Both short distances, grid can absorb and deliver |
| `invest_transmission` | d(A, B_solar) < 5km AND d(C, B_kek) >= 15km | Solar near substation but KEK far. **Build transmission to KEK.** |
| `invest_substation` | d(C, B_kek) < 15km AND d(A, B_solar) >= 5km | KEK near grid but solar far. **Build substation near solar.** |
| `grid_first` | Both distances exceed thresholds | No nearby grid infrastructure. Major grid expansion needed. |

**Within-boundary override (V3.9):** If buildable solar within the KEK boundary can cover >= `meaningful_share_pct` of the KEK's 2030 demand (live slider, default 30%), the project classifies as `within_boundary` — self-sufficient on-site, deployed behind-the-meter, no grid export. When this fires:

- The primary LCOE reported on the scorecard is the **within-boundary LCOE** (centroid PVOUT, no connection/transmission/upgrade costs baked in), not the grid-connected LCOE. See `src/dash/logic/site_context.py`.
- The infrastructure cost rollup zeros out gen-tie, new transmission, and substation upgrade costs in `src/dash/logic/grid.py`.

**Gate is KEK-only.** The rule requires `site_type == "kek"` because only KEKs have real polygon boundaries (`kek_polygons.geojson`). Non-KEK sites (standalone, cluster, KI) get their `within_boundary_coverage_pct` from a synthetic 50km-radius buffer around their point coordinates — that number has no physical meaning as "on-site." Excluding them from this gate is defense-in-depth; in practice their `within_boundary_capacity_mwp` is already 0 because `_compute_within_boundary_buildable()` in `build_fct_site_resource.py` requires a KEK polygon.

**V3.2 history:** The original override required >= 100% coverage (no slider). V3.9 replaces the hard-coded threshold with the live `meaningful_share_pct` slider so the gate aligns with phase-1 project sizing: if on-site solar can meet the user's chosen "meaningful share" of demand, grid infrastructure is not part of the captive project.

**Buildout-footprint haircut (V3.9.1):** Before comparing `within_boundary_coverage_pct` to the meaningful-share threshold, it is multiplied by `wb_buildout_footprint_ratio` (default 0.20, user slider range 0.05–1.00). Motivation: the raw `within_boundary_capacity_mwp` is derived from the spatial intersection of the KEK polygon with the buildability-filtered raster — that filter rejects forest, peatland, steep slope, and built-up pixels, but still counts every remaining vacant pixel as "buildable for solar." Inside an operating industrial park, most vacant land is earmarked for future factories, roads, utilities, and buffers, so the raw number systematically overstates what is actually free for on-site solar today. Galang Batang triggered this: the raster flagged ~59% of the KEK as buildable, which at face value made the KEK look self-sufficient on solar alone and incorrectly zeroed out all grid-infrastructure costs.

The ratio is a **gate-only haircut**: it gates whether the KEK clears the `meaningful_share_pct` threshold (and therefore whether grid infrastructure costs load into the LCOE). It does **not** scale the installed volume or the $/MWh LCOE — CAPEX and CF are volume-independent. Default 0.20 is tuned to operating parks. Greenfield KEKs should use higher values (0.50–1.00). Implementation: `effective_wb_coverage = wb_coverage × wb_buildout_footprint_ratio` in `src/dash/logic/grid.py` before the call to `grid_integration_category()`. Exposed to the UI as `within_boundary_coverage_effective_pct` so banners can narrate "raw 59% × 0.20 → 12% effective, below 30% threshold."

**Implementation:** `grid_integration_category()` in `basic_model.py` (takes `meaningful_share_pct` + `site_type` args); plumbed through `compute_grid_integration()` in `src/dash/logic/grid.py`; primary LCOE picker in `src/dash/logic/site_context.py` flips to `wb_row` when category is `within_boundary`.

### 8.3 Threshold values

| Parameter | Default | Rationale |
|---|---|---|
| `SOLAR_TO_SUBSTATION_THRESHOLD_KM` | 5.0 km | V3.1: tightened from 10km. Gen-tie costs ~\$1-3M/mile make longer connections uneconomic. Source: IFC (2015), industry benchmarks. |
| `KEK_TO_SUBSTATION_THRESHOLD_KM` | 15.0 km | PLN distribution reach to industrial estates. Indonesia's grid density varies between Java (dense) and eastern islands (sparse). |
| `SUBSTATION_MIN_CAPACITY_MVA` | 30 MVA | Minimum for viable grid injection. Allows ~21-24 MW solar at 70-80% utilization. |

All thresholds are user-adjustable in the dashboard.

**Indonesia context:** In Indonesian IPP practice, transmission corridors of 20-40 km from plant to PLN substation are common. The 5 km `SOLAR_TO_SUBSTATION_THRESHOLD_KM` is a screening cutoff for sites that can connect with minimal infrastructure cost, not the outer limit of what gets built. Sites at 5-20 km are economically viable but carry higher connection costs that the model captures via `grid_connection_cost_per_kw()`. Beyond ~20 km, connection costs typically exceed the solar LCOE savings.

### 8.4 Substation capacity check

Distance alone is insufficient. A substation 2km away but rated at 20 MVA cannot absorb a 50 MWp solar farm.

```
available_capacity_mva = rated_capacity_mva x (1 - utilization_pct)
available_capacity_mw  = available_capacity_mva x power_factor
```

Default `utilization_pct`: per-substation tier derived from PLN's RUPTL 2025-2034 upgrade plan — see §8.4a. User-adjustable slider (range 30-95%) overrides the per-site defaults uniformly.

**Power factor (V3.4):** Substation capacity is rated in MVA (apparent power), but solar output is measured in MWp (real power). The model applies a power factor of 0.85 (`SUBSTATION_POWER_FACTOR`) to convert MVA to MW before comparing to solar capacity. Industrial loads in Indonesia typically operate at PF 0.85-0.90 (PLN grid code minimum: 0.85). Without this correction, a 60 MVA substation appears to deliver 60 MW but only delivers 51 MW real power, overstating capacity by ~15%.

The returned `available_capacity_mva` column retains the MVA value for display. The PF correction is applied internally for the traffic light classification and upgrade cost calculation.

**Traffic light display:**

| Status | Criteria |
|---|---|
| Green | Available real power (MW) >= solar potential (fits, no uprating) |
| Yellow | Available real power (MW) 0.5-1x solar potential (partial overflow, uprating needed) |
| Red | Available real power (MW) < 0.5x solar potential (major upgrade) |
| Unknown | Capacity data unavailable |

Bands are aligned with `substation_upgrade_cost_per_kw`: green is exactly the regime where the upgrade cost is $0, so the UI's traffic light and the cost column never contradict each other.

**Implementation:** `capacity_assessment()` in `basic_model.py`

### 8.4a RUPTL-driven substation utilization (V3.8)

Rather than applying a uniform 65% fleet-average utilization to all 2,913 PLN substations, the model derives a per-substation default from whether PLN themselves plan to upgrade that specific asset in the RUPTL 2025-2034 plan. The reasoning: PLN only schedules uprates/extensions for substations that are already capacity-constrained, so a published upgrade plan is strong evidence the asset is running hotter than the fleet average. Conversely, substations absent from the plan's 10-year horizon are probably headroom assets.

**Tier mapping (`src.assumptions.SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL`):**

| RUPTL project type | Utilization | Rationale |
|---|---|---|
| `uprate` | 85% | Transformer replacement planned — most congested tier |
| `extension` | 75% | Adding bay/feeder — capacity-limited on some dimension |
| `line_bay` | 70% | Minor addition — slightly above fleet average |
| `none` (matched but no upgrade) | 55% | No RUPTL activity — below fleet average |
| unmatched (absent from Lampiran A/B/C) | 65% | Neutral fleet-default fallback |

**Source pipeline:** `src/pipeline/pdf_extract_ruptl_substations.py` extracts per-GI upgrade rows from RUPTL 2025-2034 Lampiran A/B/C (Sumatera, Jawa-Bali, Kalimantan, Sulawesi, Maluku, Papua, Nusa Tenggara). `src/pipeline/build_fct_substation_ruptl_signal.py` matches those rows to `data/substation.geojson` features via a tiered matcher:
  1. **High confidence** — exact normalized-name match within same PLN region (`regpln`). Normalization strips GI/GITET/GIS prefixes, voltage tokens (e.g. "150 kV"), MVA annotations (e.g. "(30 MVA No.1)"), and trailing single digits so "Parungmulya" == "Parungmulya 1" == "Parungmulya 2".
  2. **Medium** — token-set Jaccard ratio ≥ 0.85 within same region.
  3. **Lower** — token-set ratio ≥ 0.75 within same region *and* matching `voltage_primary_kv`.
  4. **Unmatched** — no signal emitted; substation falls through to the 65% fallback.

Province-level placeholders ("Eksisting", "Tersebar") and `project_type == "new"` rows are filtered before matching because they don't correspond to a specific existing substation. When multiple RUPTL plans match the same substation, the builder aggregates: strongest `project_type` wins (`uprate > extension > line_bay`), strongest status wins (`konstruksi > committed > pengadaan > rencana`), MVA additions sum, earliest target year wins. Output: `outputs/data/processed/fct_substation_ruptl_signal.csv`.

**Proxy-source substations bypass RUPTL.** When the PLN geojson has no published `kapgi`, `build_fct_substation_proximity.py` substitutes a voltage-class proxy nameplate and derates it at `1 − HOSTING_CAPACITY_AVAILABILITY_PCT` (0.70). Because the nameplate is itself a guess, the 30%-availability derating already subsumes utilization uncertainty — layering a RUPTL tier on top would double-count uncertainty.

**Slider interaction.** `assumptions.substation_utilization_pct` (the dashboard's global slider, default 65%) acts as an override. When the user leaves it at the fleet default, each site uses its per-substation RUPTL tier. When the user drags it off default, the slider value wins uniformly across all sites — a stress-test mode for scenario comparison. Proxy-source rows are unaffected by the slider (they always use 0.70). This priority rule is enforced identically in `src/dash/logic/grid.py` (for capacity assessment + integration category) and `src/dash/logic/lcoe.py` (for substation upgrade cost).

**Output columns** on `fct_substation_proximity` (surfaced through the scorecard to the ScoreDrawer Grid tab): `substation_utilization_pct_effective`, `ruptl_project_type`, `ruptl_strongest_status`, `ruptl_earliest_target_year`, `ruptl_mva_added_total`, `ruptl_match_confidence`.

**Implementation:** `_ruptl_utilization_for_substation()` in `build_fct_substation_proximity.py`; override priority in `dash/logic/grid.py` and `dash/logic/lcoe.py`.

### 8.5 Inter-substation connectivity

When B_solar and B_kek are different substations, the model checks whether an existing transmission line connects them.

**Data source:** `data/pln_grid_lines.geojson` (1,595 PLN transmission lines). Voltage: 150 kV (1,286), 500 kV (86), 275 kV (34), 70 kV (177).

**Geometric check:** Any grid line geometry passing within 2km of BOTH substations = connected.

**Fallback:** Same PLN region (`regpln`) = assumed connected through regional 150kV mesh.

**Output columns:**
- `line_connected` - True if geometric line connection found
- `same_grid_region` - True if both substations share regpln
- `inter_substation_connected` - True if either of the above

If `inter_substation_connected == False`, the category becomes `invest_transmission` or `grid_first`.

**New line cost (V3.1):** `new_transmission_cost_per_kw()` = dist x \$1.25M/km / solar_capacity_mwp. Practical limit: ~10-15km before economics fail.

### 8.6 Infrastructure cost layers

| # | Cost | Who pays | Implementation |
|---|---|---|---|
| 1 | Gen-tie (solar -> B_solar) | Developer/IPP | `grid_connection_cost_per_kw()`: dist x \$5/kW-km + \$80/kW |
| 2 | New transmission line (B_solar -> B_kek) | PLN / DFI | `new_transmission_cost_per_kw()`: dist x \$1.25M/km / capacity |
| 3 | Substation upgrade | PLN / DFI | `substation_upgrade_cost_per_kw()`: deficit_fraction x \$80/kW |

**Substation upgrade cost (V3.2).** When available substation capacity is less than the solar capacity to be injected, a proportional upgrade cost is added to the grid-connected LCOE effective CAPEX. The formula:

$$\text{available\_mw} = \text{capacity\_mva} \times (1 - \text{utilization\_pct}) \times \text{power\_factor}$$

$$\text{deficit\_fraction} = \frac{\text{solar\_mwp} - \max(0, \text{available\_mw})}{\text{solar\_mwp}}$$

$$\text{upgrade\_cost} = \text{deficit\_fraction} \times \$80/\text{kW}$$

The power factor conversion (0.85, see §8.4) ensures the comparison is between real power quantities. Cost is \$0 when available real power exceeds solar capacity, and scales linearly to \$80/kW when the substation has zero available capacity. The \$80/kW default covers transformer upgrade, new bay, buswork, and protection relay upgrades (IRENA 2023: \$50-150/kW range). Returns \$0 when capacity data is unknown (conservative).

**Multi-substation comparison (implemented V3.1).** The `/kek/{id}/substations` API endpoint evaluates the top 3 substations within search radius and compares total interconnection cost per substation (connection + upgrade + transmission). Displayed in the ScoreDrawer Grid tab as a side-by-side comparison with capacity traffic lights and rank-coded map markers (gold/silver/cyan).

### 8.7 Substation-anchored solar search (V3.7)

**Problem.** Pre-V3.7, point A was `argmax(PVOUT)` over the 50 km buildable mask. PVOUT varies ~1-2% across 50 km in tropical Indonesia, but substation distance can vary 10× over the same area. Optimizing for the 1% PVOUT delta sent the model to pixels geometrically far from any substation, producing false "Build Substation" labels for small-demand sites whose nearest substation was visibly adjacent on the map (e.g. Batam Aero Technic: labeled `invest_substation` with a 17.9 km solar-to-substation distance, when GI 150 kV Nongsa 1 sat 3.96 km from the site).

**Solution.** Pick the lowest-LCOE buildable patch co-located with an existing substation, falling back to `argmax(PVOUT)` only when no patch meets a meaningful-share floor. The fallback path is the only one that should produce `invest_substation`.

**Algorithm** (implemented in `_pick_anchored_patch()` in `src/pipeline/build_fct_site_resource.py`):

1. **Required capacity** from 2030 demand:
   $$\text{required\_mwp} = \frac{\text{demand\_mwh}}{8760 \times \text{cf\_centroid}}$$
2. **Meaningful-share floor:**
   $$\text{meaningful\_mwp} = \text{required\_mwp} \times \text{MEANINGFUL\_SHARE\_PCT}$$
3. **For each substation** within `KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM[region]` of the site:
   - intersect the 5-layer buildable mask with an `ANCHOR_SEARCH_RADIUS_KM` (10 km) circular buffer around the substation
   - if buildable area × (1 / `HA_PER_MWP`) ≥ `meaningful_mwp`, keep as candidate
4. **LCOE proxy** for each candidate:
   $$\text{lcoe\_proxy} = \text{lcoe\_solar}(\text{cf\_candidate}) + \frac{\text{conn\_capex\_per\_kw}(d_\text{site→sub}) \times \text{CRF}}{cf \times 8.76}$$
   where the second term amortises the gen-tie CAPEX over annual generation. This trades the small PVOUT delta against the often-larger connection cost saving.
5. **Pick** the candidate with the lowest `lcoe_proxy` → `solar_search_method = "substation_anchored"`.
6. **Fallback.** If no substation within the tiered radius has enough buildable area within 10 km to meet `meaningful_mwp`, revert to the legacy argmax pixel and flag `solar_search_method = "best_pvout_fallback"`. Only the fallback path can legitimately produce `invest_substation`.

**Thresholds:**

| Parameter | Value | Rationale |
|---|---|---|
| `MEANINGFUL_SHARE_PCT` | 0.30 (default, **user-adjustable via slider**) | Patches covering <30% of demand are too small to count as a meaningful decarbonization play; fallback produces a legitimate "Build Substation" label instead. The pipeline-time picker floor remains fixed at 30%; the slider controls live project sizing (`project_scale_solar_mwp = min(required × share, max_buildable)`) which in turn drives `capacity_assessment` and the `invest_substation` label. Raising the slider makes more sites appear to need substation upgrades; lowering it makes more sites appear Grid Ready. |
| `ANCHOR_SEARCH_RADIUS_KM` | 10.0 km | Search-candidate radius around each substation (picker). Restores pre-V3.1 radius; `SOLAR_TO_SUBSTATION_THRESHOLD_KM` (5 km) remains the classification threshold. Indonesian permitting + land economics allow longer gen-ties than US/EU 5 km benchmarks. |
| `CAPTIVE_REGIME_MAX_KM` | 10.0 km | Classification cutoff between `co_located_captive` and `grid_connected_ipp` regimes. Kept separate from `ANCHOR_SEARCH_RADIUS_KM` so tuning the picker's reach doesn't silently move the regulatory-regime boundary. Same starting value today because the thresholds happen to coincide. |
| `KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM` | JAMALI 15, SUMATRA 25, KALIMANTAN 30, SULAWESI 30, MALUKU_PAPUA 40 | Geography-tiered — Indonesia's grid density varies by order of magnitude across regions. |

**New output columns** (`fct_site_resource` + surfaced on scorecard):

| Column | Description |
|---|---|
| `solar_search_method` | `substation_anchored` or `best_pvout_fallback` |
| `chosen_anchor_substation_name` | Name of the substation anchoring the chosen patch (null on fallback) |
| `solar_supply_share_pct` | Chosen patch nameplate MWp / required_mwp (capped 1.0) |
| `solar_delivered_share_pct` | Chosen patch annual generation MWh / demand MWh, capped 1.0 — the CF-corrected version of supply share |
| `project_scale_solar_mwp` | min(required_mwp, max_buildable) — what actually gets built to cover site demand, not the full buildable area |

**Hosting-capacity proxy (V3.7 Action 2).** PLN `kapgi` (nameplate MVA) is missing for ~XX% of operational substations. Without a proxy, every capacity check silently passes on NaN. When `kapgi` is missing, the pipeline substitutes a voltage-class proxy from `SUBSTATION_HOSTING_CAPACITY_PROXY_MVA` (500 kV = 500 MVA, 275 kV = 250, 150 kV = 60, 70 kV = 20, 20 kV = 5) and applies `HOSTING_CAPACITY_AVAILABILITY_PCT = 0.30` instead of the `SUBSTATION_UTILIZATION_PCT = 0.65` used for actual kapgi. The `nearest_substation_capacity_source` column records which path fired: `actual` / `proxy_500kV` / `proxy_150kV` / etc.

**Regulatory regime and Perpres 112/2022 ceiling (V3.7 Action 4).** A new `solar_regime` enum distinguishes:
- `co_located_captive` — `site_type ∈ {kek, ki}` AND solar patch ≤ `CAPTIVE_REGIME_MAX_KM` from a substation inside the site. Self-consumption, no sale to PLN, no tariff ceiling.
- `grid_connected_ipp` — everything else that reaches the grid. Subject to Perpres 112/2022 Art. 10 ceiling tariff (`PERPRES_112_CEILING_USD_MWH = 75.0`).
- `unclear` — when `site_type` is missing.

For IPP rows, `lcoe_grid_connected_capped_usd_mwh = min(lcoe_grid_connected_usd_mwh, 75)`. Captive rows pass through unchanged. The cap is economically binding across the 81-site portfolio — all 68 IPP rows hit the ceiling at default assumptions, which is precisely the signal: Indonesian LCOEs run above the statutory cap, so the ceiling functions as a procurement constraint rather than a pricing guide.

**Verification — Batam Aero Technic:** Pre-V3.7 label `invest_substation` (17.9 km to Tg. Kasam). Post-V3.7: `solar_search_method = substation_anchored`, anchor = GI 150 kV Nongsa 1, solar-to-substation distance = 1.22 km, `project_scale_solar_mwp = 14.89`, label = `grid_ready`.

---

## 9. Competitiveness Metrics

### 9.1 Solar competitive gap

$$\text{gap} = \frac{LCOE_{\text{mid}} - C_{\text{grid}}}{C_{\text{grid}}} \times 100\%$$

- Negative = solar cheaper
- Positive = grid cheaper

**Two gap perspectives:**

| Perspective | Formula | Use |
|---|---|---|
| IPP gap | (LCOE_gc - BPP_region) / BPP_region | "Can I sell solar profitably to PLN?" |
| Tenant gap | (LCOE_wb - Tariff_I4) / Tariff_I4 | "Can I save money with on-site solar?" |

### 9.2 Carbon breakeven price

$$P_{\text{carbon}} = \begin{cases} 0 & \text{if } LCOE \leq C_{\text{grid}} \\ \frac{LCOE - C_{\text{grid}}}{EF_{\text{grid}}} & \text{otherwise} \end{cases} \quad [\text{USD/tCO}_2]$$

The carbon price at which solar becomes cost-competitive.

**Grid emission factors (Operating Margin, KESDM 2019):**

| Grid Region | OM (tCO2/MWh) | Notes |
|---|---|---|
| JAVA_BALI | 0.80 | 302 plants |
| SUMATERA | 0.77 | 463 plants, gas + hydro + coal |
| KALIMANTAN | 1.16 | Avg of Barito (1.20) + Mahakam (1.12) |
| SULAWESI | 0.63 | Wtd avg: Sulutgo (0.67 x2) + Palapas (0.54 x1) |
| NTB | 1.27 | Lombok, diesel-dominant |
| MALUKU | 0.60 | Daruba-Morotai |
| PAPUA | 0.56 | Sorong, gas-dominant |

**Warning:** These factors are 2019 vintage (7 years old as of April 2026). Indonesia's grid mix has shifted. Update when KESDM publishes newer factors.

**Simplification:** Formula assumes zero solar lifecycle emissions. Actual: ~40 gCO2/MWh (IPCC AR6). Breakeven prices are ~5-8% too optimistic.

### 9.3 Flip scenario

KEKs where 0 < gap <= 20% are "flip candidates" where modest policy intervention (CAPEX reduction, lower WACC, tariff adjustment) could make solar competitive.

### 9.4 Solar supply coverage

How much of a KEK's electricity demand could be met by buildable solar within the search radius.

$$\text{max\_solar\_generation\_gwh} = \text{max\_captive\_capacity\_mwp} \times \frac{\text{pvout\_best\_50km}}{1000}$$

$$\text{solar\_supply\_coverage} = \frac{\text{max\_solar\_generation\_gwh}}{\text{demand\_2030\_gwh}}$$

Where:
- `regional_groundmount_potential_mwp_50km` = buildable solar capacity from buildability filters (§3, Appendix A)
- `pvout_best_50km` = best annual solar yield within 50km (kWh/kWp/yr)
- `demand_2030_gwh` = estimated KEK annual electricity demand (from area x industrial intensity)
- Generation formula: capacity x yield converts MWp to MWh/yr, then /1000 for GWh

**Capacity factor is already embedded:** PVOUT = CF x 8,760, so the generation formula is equivalent to `capacity_mwp x CF x 8,760 / 1000`. Supply coverage is not comparing nameplate capacity to demand; it compares expected energy output (accounting for solar intermittency, temperature losses, and system efficiency already baked into the Global Solar Atlas PVOUT value) to energy demand. A 100 MWp array with CF=0.18 produces 157.7 GWh/yr, not 876 GWh/yr.

**Interpretation:**
- Coverage >= 100%: solar can fully supply the KEK's demand (excess capacity available)
- 50-99%: partial coverage, grid or other sources needed for the remainder
- < 50%: solar alone cannot meet most demand, grid dependency remains high

**Caveats:**
- Demand is estimated from KEK area x intensity proxy, not actual metered consumption
- Solar generation assumes the entire buildable capacity is built at best-resource sites
- Annual coverage does not account for temporal mismatch (see §9.5 Firm Solar Coverage below)
- Coverage > 100% does not mean grid-independent (intermittency, night-time demand)

### 9.5 Firm solar coverage (V3.3)

Annual supply coverage (§9.4) overstates solar's ability to serve 24/7 industrial loads because it ignores the day/night mismatch. A KEK showing "100% coverage" actually needs ~58% of that energy stored and time-shifted to nighttime via battery storage.

V3.3 adds four companion metrics that ground solar coverage in physical reality:

**Temporal split (flat demand profile assumption):**
```
daytime_fraction = SOLAR_PRODUCTION_HOURS / 24 = 10/24 = 0.417
nighttime_fraction = 1 - daytime_fraction = 14/24 = 0.583
daytime_demand = demand_mwh × daytime_fraction
nighttime_demand = demand_mwh × nighttime_fraction
```

**Firm solar coverage:** What fraction of daytime-only demand can solar serve directly, without storage:
```
firm_solar_coverage = solar_generation_mwh / daytime_demand
```

At 100% annual coverage, firm_solar_coverage = 1.0 / 0.417 = 2.4x. Solar overproduces during the day. The surplus must be stored for nighttime use.

**Storage required:** Total MWh of battery throughput needed per year to serve nighttime demand, accounting for round-trip efficiency losses:
```
storage_required_mwh = nighttime_demand / BESS_ROUND_TRIP_EFFICIENCY
```

**Storage gap:** Fixed at ~58% for equatorial Indonesia (14h night / 24h day). This is the fraction of total demand that physically cannot be served by solar without storage.

**Physical basis:** MacKay, *Sustainable Energy Without the Hot Air*, Ch. 26. Solar produces during ~10 hours of daylight. Industrial smelters consume 24 hours. Matching total energy is necessary but not sufficient. You must also match the timing. The firm coverage metric addresses this by only counting what solar can deliver directly during production hours.

**Implementation:** `firm_solar_metrics()` in `basic_model.py`. Output fields: `firm_solar_coverage_pct`, `nighttime_demand_mwh`, `storage_required_mwh`, `storage_gap_pct`.

### 9.6 Wind supply coverage

Same formula as solar supply coverage (§9.4), using wind buildability data:

$$\text{max\_wind\_generation\_gwh} = \text{max\_wind\_capacity\_mwp} \times \text{cf\_wind\_buildable\_best} \times 8760 / 1000$$

$$\text{wind\_supply\_coverage} = \frac{\text{max\_wind\_generation\_gwh}}{\text{demand\_2030\_gwh}}$$

Where:
- `max_wind_capacity_mwp` = buildable wind capacity from wind buildability filters (§4.1)
- `cf_wind_buildable_best` = capacity factor at best buildable wind site within 50km
- `demand_2030_gwh` = estimated KEK annual electricity demand

**Capacity factor is explicit here** (unlike solar where CF is embedded in PVOUT). The formula multiplies capacity x CF x 8760 directly, so generation reflects actual expected output from wind intermittency, not nameplate capacity.

**Implementation:** Live-computed in `logic/scorecard.py` (not precomputed in CSV). Uses `max_wind_capacity_mwp` and `cf_wind_buildable_best` from `fct_kek_wind_resource`, merged into `resource_df` at API startup.

### 9.7 Wind carbon breakeven

Uses the same technology-agnostic `carbon_breakeven_price()` function as solar (§9.2):

$$P_{\text{carbon,wind}} = \begin{cases} 0 & \text{if } LCOE_{\text{wind}} \leq C_{\text{grid}} \\ \frac{LCOE_{\text{wind}} - C_{\text{grid}}}{EF_{\text{grid}}} & \text{otherwise} \end{cases} \quad [\text{USD/tCO}_2]$$

**Implementation:** Live-computed in `logic/scorecard.py` using `lcoe_wind_mid_usd_mwh` and `grid_cost_usd_mwh`. Output field: `wind_carbon_breakeven_usd_tco2`.

### 9.8 Firm wind coverage (intermittency model)

Wind's temporal profile differs from solar. Solar has a predictable day/night split (10h production, 14h gap). Wind is intermittent across all hours, with availability depending on capacity factor.

**CF-dependent intermittency tiers:**

| CF range | Firming gap | Bridge hours | Context |
|----------|-------------|-------------|---------|
| >= 35% | 15% | 2h | Strong wind resource, short calm spells |
| 25-34% | 25% | 3h | Moderate wind, longer intermittent gaps |
| < 25% | 35% | 4h | Low wind, frequent and extended calms |

**Firm wind coverage:** Fraction of demand that wind can serve directly (without storage):
```
firm_wind_coverage_pct = (1 - firming_gap) * wind_supply_coverage_pct
```

At 100% annual wind coverage with 25% firming gap, firm wind coverage = 75%. The remaining 25% requires battery or backup.

**Compared to solar:** Solar's gap is fixed at ~58% (14h night). Wind's gap is smaller (15-35%) but less predictable. Solar's temporal mismatch is a scheduling problem (store during day, discharge at night). Wind's is a weather problem (calms can last hours to days). This distinction matters for BESS sizing: solar needs long-duration storage, wind needs shorter but less predictable firming.

**Implementation:** `firm_wind_metrics()` in `basic_model.py`. Output fields: `firm_wind_coverage_pct`, `wind_firming_gap_pct`, `wind_firming_hours`.

---

## 10. Action Flags

### 10.1 Flag definitions (10 solar-mode flags; 14 total across all energy modes)

| Flag | Condition | Meaning | Primary audience |
|---|---|---|---|
| `solar_now` | `grid_ready`/`within_boundary` AND LCOE < grid cost AND GEAS >= 30% | Ready to build. IPP can proceed, PLN should procure. | IPP, Policy Maker |
| `cbam_urgent` | CBAM-exposed AND `cbam_adjusted_gap_pct` < 0 | RE + avoided CBAM border tax beats grid cost. Act now. See §14 and [Layer 3 spec](../docs/layer3_green_industrial_products_spec.md). | KEK Tenant, Policy Maker |
| `invest_transmission` | `invest_transmission` grid category AND solar_attractive | Solar near substation but KEK far. **Build transmission to KEK.** | Policy Maker, DFI |
| `invest_substation` | `invest_substation` grid category AND solar_attractive | KEK near grid but solar far. **Build substation near solar.** | Policy Maker, DFI |
| `grid_first` | `grid_first` grid category | No substation near KEK or solar site. New grid infrastructure needed. | Policy Maker |
| `invest_battery` | solar_attractive AND reliability_req >= 0.75 | High reliability needs, battery storage required alongside solar. | IPP, Tenant |
| `invest_resilience` | 0 < gap <= 20% AND reliability_req >= 0.75 | Near parity. Investing builds resilience against grid cost increases. | IPP, Policy Maker |
| `plan_late` | post2030_share >= 60% | Most planned solar additions slip past 2030. RUPTL needs acceleration. | Policy Maker, DFI |
| `not_competitive` | None of the above AND buildable area > 0 | Solar LCOE exceeds grid cost by too wide a margin. | All |
| `no_solar_resource` | Buildable area = 0 | No suitable land for solar within 50km after buildability filters. | Policy Maker |

**`cbam_urgent` note (V3.6):** Overrides `not_competitive` and `invest_resilience` when fired. A KEK that would be `not_competitive` on energy economics alone becomes `cbam_urgent` if the CBAM-adjusted competitive gap (§14) is negative, meaning RE + avoided CBAM border tax is cheaper than the current energy source. 12/25 KEKs are CBAM-exposed. The flag speaks to the KEK Tenant persona: CBAM savings justify the renewable switch regardless of pure LCOE economics.

### 10.2 Priority ordering

When multiple flags could apply, the dashboard displays the **first true** flag:

1. `solar_now` (highest)
2. `cbam_urgent` (overrides `not_competitive` / `invest_resilience` when CBAM-adjusted gap < 0)
3. `invest_transmission`
4. `invest_substation`
5. `grid_first`
6. `invest_battery`
7. `invest_resilience`
8. `plan_late`
9. `not_competitive`
10. `no_solar_resource` (lowest — no buildable land)

**Note:** In the frontend, the priority ordering is mode-dependent (solar/wind/hybrid/overall modes have separate hierarchies). The ordering above is for solar mode. Wind mode replaces `solar_now` with `wind_now`; hybrid mode uses `hybrid_now`; overall mode uses whichever technology is best per KEK.

### 10.3 solar_attractive definition

$$\text{solar\_attractive} = \bigl(\text{PVOUT}_{\text{best50km}} \geq 1{,}350\bigr) \;\wedge\; \bigl(LCOE_{\text{mid}} \leq C_{\text{grid}}\bigr)$$

WACC-dependent. "Solar LCOE <= grid cost at current WACC AND resource is sufficient."

**Threshold rationale:** Indonesia is equatorial with PVOUT range 1,300-1,700 kWh/kWp/yr. The mean across all 25 KEKs is ~1,518. A threshold of 1,350 (~15.4% CF) keeps all viable sites in analysis while excluding truly poor solar locations. User-adjustable via Tier 3 slider (range 1,200-1,800).

**Implementation:** `is_solar_attractive()` in `basic_model.py`

### 10.4 invest_resilience rationale

The `not_competitive` label only captures tariff economics. For manufacturing KEKs, unplanned outages cost \$500K-\$2M per hour in scrapped production. Captive solar with backup eliminates this tail risk.

| Threshold | Value | Why |
|---|---|---|
| Gap > 0 | - | Solar not yet cheaper (otherwise it's `solar_now`) |
| Gap <= 20% | 20% | At \$63/MWh grid cost, premium is ~\$12.6/MWh. Manufacturing outage costs are \$50-200/MWh, far exceeding the premium. |
| reliability_req >= 0.75 | 0.75 | Manufacturing/processing sectors (steel, chemicals, automotive). Tourism/services can tolerate interruptions. |

**`reliability_req` values:** Manufacturing=0.8, Service/Digital=0.6, Tourism=0.4 (set in `kek_grid_region_mapping.csv`).

**Current results (WACC=10%):** 4 KEKs fire: Kendal (13.0%), Gresik (14.2%), Batang (14.6%), Bitung (17.4%). Carbon breakeven: \$10-17/tCO2.

**Implementation note:** `invest_resilience()` is a separate function in `basic_model.py`, not part of the `action_flags()` return dict. The scorecard builder (`build_fct_kek_scorecard.py`) and dashboard logic (`logic/scorecard.py`) compute it separately and merge it into the flag priority chain.

### 10.5 CostBasis resolver (M31)

`action_flag`, `economic_tier`, `solar_competitive_gap_pct`, and `carbon_breakeven_usd_tco2` all need a cost number to compare against the grid benchmark. Which cost — raw generation LCOE, firmed LCOE, or delivered blended cost — depends on the persona, not on the model. M31 adds a user-selectable `CostBasis` toggle (`raw` / `firmed` / `delivered`) that picks the cost column at render time. See [TAXONOMY §7.3](TAXONOMY.md#73-costbasis-toggle--let-the-user-pick-which-layer-of-the-stack-feeds-the-action-flags) for the framing and per-persona defaults.

**Resolver matrix.** `(EnergyMode × CostBasis)` → scorecard column:

| | `raw` (T1) | `firmed` (T2) | `delivered` (T3) |
|---|---|---|---|
| **solar** | `lcoe_mid_usd_mwh` | `lcoe_with_battery_usd_mwh` | `delivered_cost_usd_mwh` |
| **wind** | `lcoe_wind_mid_usd_mwh` | `lcoe_wind_allin_mid_usd_mwh` | — *not modelled* |
| **hybrid** | `hybrid_lcoe_usd_mwh` | `hybrid_allin_usd_mwh` | — *not modelled* |
| **overall** | — *no single raw* | `best_re_lcoe_mid_usd_mwh` | — *not modelled* |

Empty cells render the toggle option disabled in the UI with a "Not modelled for {mode}" tooltip. No silent fallback.

**Default basis.** `firmed` when `EnergyMode = overall`, `raw` otherwise. Preserves pre-M31 behaviour: solar/wind/hybrid flags were already computed against T1 LCOE; overall mode used the firmed best-RE LCOE.

**Implementation (frontend-derivation).** The backend does **not** precompute flags/tiers for every (mode × basis) combo and fan them out on the scorecard row. Instead:
- `frontend/src/lib/costBasis.ts::resolveCost(row, mode, basis)` picks the cost column per the matrix above.
- `frontend/src/lib/actionFlags.ts::getEffectiveActionFlag / getEffectiveEconomicTier / getEffectiveCarbonBreakeven` take `(row, mode, basis)` and re-derive the flag/tier/breakeven at render time using the resolved cost.
- Carbon breakeven uses `row.grid_emission_factor_t_co2_mwh` directly (newly surfaced by `enrich_grid_passthroughs` in `src/dash/logic/scorecard.py`) — same EF the backend uses, no reverse-derivation.

Deviation from the original spec in TAXONOMY §7.3: the spec proposed a nested `action_flags_by_basis` dict on the backend, frontend picks the active one. Frontend-derivation is simpler (no API schema growth, no serialization of 9 flag/tier tuples per row) and equally instant. If a future consumer needs the resolver without touching frontend code, we can lift `resolveCost` into a Python helper and fan out on the scorecard.

**Callsites respecting `costBasis`.** Map markers (flag color + shape), table cells (`EconomicTierCell`, `ReAssessmentCell`), table filters (economic tier facet), CSV export metadata, ScoreDrawer header + Action tab, QuadrantChart x-axis. All subscribe to the `costBasis` Zustand selector.

**Tests.** `tests/test_cost_basis_enum.py` (5 tests): CostBasis enum invariants + supported-cell table for every (mode, basis) combo. Scorecard golden fixture regenerated (81 × 143 cols; new col: `grid_emission_factor_t_co2_mwh`).

---

## 11. GEAS Green Share

GEAS (Green Energy Auction Scheme) allocates renewable energy from RUPTL-planned solar to industrial zones on a pro-rata basis.

**Baseline allocation (proportional to demand):**

$$\text{GEAS}_{\text{alloc}}^{i} = E_{\text{green}}^{r} \times \frac{D^{i}}{D^{r}_{\text{total}}}$$

$$\text{green\_share}^{i} = \min\!\left(1,\;\frac{\text{GEAS}_{\text{alloc}}^{i}}{D^{i}}\right)$$

Where $E_{\text{green}}^{r} = \text{pre2030\_solar\_MW}^{r} \times 8{,}760 \times CF_r$ and $CF_r = 0.20$.

**Policy scenario allocation (proportional to demand x PVOUT):**

$$w^{i} = D^{i} \times \text{PVOUT}_{\text{best50km}}^{i}$$

Prioritizes zones with both high demand and high solar resource.

**Interpretation:**
- green_share >= 30% + solar competitive -> `solar_now` fires
- green_share >= 30% but not competitive -> GEAS may satisfy tenant ESG without captive solar
- green_share < 30% -> captive solar is the only path to renewable coverage

GEAS and captive solar are substitutes. The dashboard uses `green_share_geas` to determine which lever a KEK needs.

---

## 12. DFI Grid Infrastructure Investment Model

Development Finance Institutions (ADB, World Bank, IFC, AIIB) regularly finance grid infrastructure. The `invest_transmission` and `invest_substation` categories are the DFI opportunity set.

**Investment instruments:**

| Instrument | Dashboard relevance |
|---|---|
| Concessional loan to PLN | `invest_transmission`/`invest_substation` KEKs show where PLN needs investment |
| Viability gap funding | Grid investment estimate sizes the gap |
| Blended finance | DFI funds grid, private IPP funds solar, PLN operates |
| Green bonds | Regional aggregation of grid-investment KEKs sizes the bond |

**Grid investment estimation (screening-level):**

$$I_{\text{grid}} = d_{\text{gap}} \times C_{\text{transmission/km}} + N_{\text{substations}} \times C_{\text{substation}}$$

Where $C_{\text{transmission/km}} \approx$ \$500K-1M/km for 150kV in Indonesia, $C_{\text{substation}} \approx$ \$5-15M per 150/20kV step-down.

**Screening heuristic:**
```
Screening ratio = Solar_capacity_unlocked_MWp / I_grid_USD_million
```

High ratio = small grid investment unlocks large solar potential. This is a screening estimate, not a bankable figure.

---

## 13. Captive Power Context

The dashboard integrates two external datasets to characterize captive (behind-the-meter) fossil fuel generation near each KEK. This creates the demand-side signal: which KEKs have existing coal or nickel-related power that solar could displace?

### 13.1 Data sources

| Source | Dataset | License | Coverage | Update frequency |
|--------|---------|---------|----------|-----------------|
| **China Global South Project (CGSP)** | Nickel Tracker | CC | 107 nickel processing facilities across Indonesia | Quarterly |
| **Global Energy Monitor (GEM)** | Global Coal Plant Tracker | CC BY 4.0 | 26 captive coal plants in Indonesia (filtered from global dataset) | Semi-annual |

**CGSP fields used:** project name, latitude, longitude, capacity, process type (RKEF, Ferro Nickel, HPAL, Laterite), ownership nationality (Chinese/non-Chinese), status.

**GEM fields used:** plant name, latitude, longitude, capacity_mw, status, parent company, region. Note: the KAPSARC mirror of GEM data lacks `commissioning_year`, which limits Perpres 112/2022 compliance dating (see §13.3).

### 13.2 Spatial matching

Both datasets are spatially joined to KEK polygons using a **50 km buffer** (haversine distance from KEK centroid). Per-KEK aggregation produces:

- **Coal:** count of plants, total capacity (MW), semicolon-separated plant names
- **Nickel:** count of facilities, semicolon-separated project names, dominant process type (mode), Chinese ownership flag (any)

Pipeline functions:
- `build_captive_coal_summary()` in `src/pipeline/build_fct_captive_coal.py`
- `build_captive_nickel_summary()` in `src/pipeline/build_fct_captive_nickel.py`

Output CSVs: `fct_captive_coal_summary.csv` (5 KEKs matched), `fct_captive_nickel_summary.csv` (3 KEKs matched). Merged into `resource_df` via left join on `kek_id` in `data_loader.py:prepare_resource_df()`.

### 13.3 Perpres 112/2022 compliance

Presidential Regulation (Perpres) 112/2022 mandates emission reduction for captive coal power in Indonesia:

- Plants commissioned **post-2022**: 35% emission reduction within 10 years
- **All captive coal** must cease operations by 2050

**Implementation limitation:** The GEM KAPSARC mirror lacks `commissioning_year`, so we cannot determine individual plant compliance deadlines. Instead, a status-based proxy is used:

- Any KEK with `captive_coal_count > 0` → `has_captive_coal = True`, `perpres_112_status = "Subject to 2050 phase-out"`
- KEKs with no matched coal → `has_captive_coal = False`, `perpres_112_status = None`

This is a **regulatory compliance signal**, not an action flag. It lives alongside the 8 solar readiness flags as supplementary context. When `commissioning_year` data becomes available (e.g., from ESDM Minerba Geoportal), the status can be refined to per-plant deadlines.

### 13.4 Scorecard fields

Fields added to `fct_kek_scorecard` from captive power summaries:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `captive_coal_count` | int/null | GEM | Coal plants within 50 km |
| `captive_coal_mw` | int/null | GEM | Total captive coal capacity (MW) |
| `captive_coal_plants` | str/null | GEM | Semicolon-separated plant names |
| `nickel_smelter_count` | int/null | CGSP | Nickel facilities within 50 km |
| `nickel_projects` | str/null | CGSP | Semicolon-separated project names |
| `dominant_process_type` | str/null | CGSP | Most common process (RKEF, Ferro Nickel, HPAL) |
| `has_chinese_ownership` | bool | CGSP | Any Chinese-owned facility within 50 km |
| `has_captive_coal` | bool | Derived | `captive_coal_count > 0` |
| `perpres_112_status` | str/null | Derived | Compliance status string |

### 13.5 Map overlays

Two toggleable map layers in LayerControl (default off):

| Layer | Icon | Color | Data |
|-------|------|-------|------|
| Nickel Smelters (CGSP) | Factory SVG in circle | `#FF6D00` (orange) | 107 points |
| Captive Coal Plants (GEM) | Smokestack SVG in circle | `#B71C1C` (dark red) | 26 points |

Both use the `createIconImage(pathData, color, size)` pattern (colored circle background + white SVG path), consistent with infrastructure markers. Click popup shows facility details.

Nickel smelter popups include enriched CGSP fields: production capacity (tons), investment cost (USD), shareholder names, and ESG impact flags (ecological + social). Coal popups show plant name, capacity (MW), unit count, status, and parent company.

### 13.6 Solar replacement potential

For KEKs with matched captive coal, the dashboard computes what percentage of coal generation could be displaced by buildable solar capacity:

```
captive_coal_generation_gwh = captive_coal_mw × 8.76 × 0.40
solar_replacement_pct = max_solar_generation_gwh / captive_coal_generation_gwh × 100
```

Where 0.40 is a typical capacity factor for Indonesian captive coal plants. This gives a concrete signal: "buildable solar near this KEK could replace X% of existing captive coal output." Displayed in the Captive Power card in the ScoreDrawer Pipeline tab.

### 13.7 BESS sizing for industrial loads (M19 + V3.3)

**V3.3 bridge-hours model supersedes the M19 RKEF-only multiplier.** All high-reliability loads (reliability_req >= 0.75) now use physics-based bridge-hours sizing (14h), regardless of process type. See §6.3 for the full BESS storage model.

The M19 RKEF 2x multiplier (2h → 4h) is retained as a fallback when `BESS_BRIDGE_HOURS_ENABLED = False`, for backward compatibility testing.

**Sizing hierarchy (V3.6):**
0. If `bess_sizing_hours_override` is set: **use that value** (user exploring tradeoffs via ScoreDrawer slider, range 1-16h)
1. If `BESS_BRIDGE_HOURS_ENABLED` and `reliability_req >= 0.75`: **14h bridge-hours** (24 - 10h solar)
2. Else if `dominant_process_type == "RKEF"`: **4h** (M19 legacy)
3. Else: **2h** (cloud-firming default)

Rationale: The 2h/4h defaults were identified as the tool's biggest physics vulnerability (see `docs/physics_vs_tool_technical_gaps.md`, Gaps 1-2). A 24/7 industrial load requires ~14h of overnight bridging. At 2h sizing, LCOE with battery was understated by \$170-250/MWh. The bridge-hours model produces honest storage economics without requiring hourly dispatch simulation.

---

## 14. EU CBAM Exposure

**Feature spec:** [docs/layer3_green_industrial_products_spec.md](../docs/layer3_green_industrial_products_spec.md) — describes the product design rationale, persona impact, and calculation logic for this feature layer.

The EU Carbon Border Adjustment Mechanism (CBAM, Regulation 2023/956) imposes a carbon cost on imports of carbon-intensive goods into the EU. For Indonesian sites producing CBAM-covered products (iron/steel, aluminium, cement, fertilizer, ammonia), switching the site's electricity supply from coal grid to solar cuts its **Scope 2** emissions and reduces — but does not eliminate — future CBAM charges. The remaining **Scope 1** emissions are from the chemistry itself (calcination, feedstock reforming, metallurgical coke) and are not addressable by renewable electricity. §14.2 makes this distinction concrete; §14.3 shows why the split produces very different CBAM relief across sectors. This section documents how the dashboard detects CBAM exposure, computes emission intensities, and projects cost trajectories across the 68 CBAM-exposed sites of the 81 total.

**V3.6 additions:** `cbam_urgent` action flag (§10.1), user-adjustable CBAM certificate price (€30-150) and EUR/USD rate (1.00-1.30) via Tier 2 sliders, 2030 crossover year marker on trajectory chart.

### 14.1 CBAM signal detection

CBAM exposure is detected via a **three-signal approach**. Signals are evaluated in order; duplicates are suppressed (each product type appears at most once per KEK).

**Signal 1: Nickel process types** (from CGSP Nickel Tracker via `fct_captive_nickel`).
If `dominant_process_type` is `"Nickel Pig Iron"` or `"Ferro Nickel"`, append `nickel_rkef`. These RKEF/FeNi processes produce ferro-nickel or nickel pig iron — both covered under CBAM as iron and steel precursors.

**Signal 2: Plant-level industrial data** (from GEM trackers via `fct_captive_steel`, `fct_captive_cement`).
- Steel: if `steel_plant_count > 0`, use `steel_dominant_technology` from GEM. `"BF-BOF"` maps to `steel_bfbof`; all others (including missing) default to `steel_eaf` (EAF is the most common steel technology in Indonesia).
- Cement: if `cement_plant_count > 0`, append `cement`.

**Signal 3: KEK business sectors** (from `kek_business_sectors.csv`).
Maps registered KEK industry classifications to CBAM product types:

| KEK Business Sector | CBAM Product Type |
|---|---|
| Base Metal Industry | `nickel_rkef` |
| Nickel Smelter Industry | `nickel_rkef` |
| Bauxite Industry | `aluminium` |
| Petrochemical Industry | `fertilizer` |
| Cement Industry | `cement` |

**Output fields:**
- `cbam_exposed` (bool): `True` if any signal matched
- `cbam_product_type` (str/null): comma-separated list of matched product types (e.g., `"nickel_rkef,cement"`)

**Implementation:** `logic/cbam.py::_detect_cbam_types()`, called per-row from `logic/scorecard.py::compute_scorecard_live()`.

### 14.2 Two kinds of emissions: Energy vs Process

Every CBAM-covered product has **two emission sources**, and solar only addresses one of them. This is the single most important distinction in the CBAM model.

**Energy emissions (Scope 2):** CO₂ from generating the electricity the site consumes. A nickel RKEF smelter pulls power from the grid; that grid burns coal. Switch the site to solar and these emissions go to zero. Renewable energy directly replaces the emission source.

**Process emissions (Scope 1):** CO₂ released by the chemical reaction itself, regardless of what energy source you use. The raw material transforms and releases CO₂ as a byproduct of the chemistry, not the combustion. Examples:
- **Cement:** limestone calcination, CaCO₃ → CaO + CO₂. Happens in the kiln at any temperature from any heat source.
- **Ammonia:** steam methane reforming, CH₄ + 2H₂O → CO₂ + 4H₂. The carbon in the natural gas feedstock has to come out somewhere.
- **Nickel RKEF:** metallurgical coke is a chemical reductant that strips oxygen from nickel ore — not a fuel.
- **Steel BF-BOF:** coking coal reduces iron oxide; same story.

Solar cannot touch Scope 1. It only zeros out Scope 2.

**The practical consequence: CBAM cuts differently by sector.** The same €/t ETS certificate turns into very different $/t cost relief depending on how much of a sector's emission intensity is electricity-driven vs chemistry-driven:

| Sector | Scope 1 (tCO₂/t) | Scope 2 at Indonesia grid (tCO₂/t) | What solar cuts |
|---|---|---|---|
| Nickel RKEF | 3.0 | ~24 (37.5 × 0.63) | ~89% of CBAM bill |
| Aluminium | 1.5 | ~12 (15.0 × 0.8) | ~89% of CBAM bill |
| Steel EAF | 0.3 | ~0.36 (0.45 × 0.8) | ~55% of CBAM bill |
| Steel BF-BOF | 1.8 | ~0.20 (0.25 × 0.8) | ~10% of CBAM bill |
| Cement | 0.52 | ~0.72 (0.9 × 0.8) | ~58% nominally — but see §14.3 M30 wrinkle |
| Ammonia | 2.3 | ~8.0 (10.0 × 0.8) | ~78% nominally — but see §14.3 M30 wrinkle |
| Fertilizer (legacy) | 1.2 | ~8.0 (10.0 × 0.8) | same M30 wrinkle as ammonia |

The first four rows are clean: the electricity numbers are genuinely electricity. The last three are not — the Scope 2 figures roll in kiln heat and SMR feedstock gas as "electricity equivalents," which solar can't actually displace. §14.3 explains the fix.

**Product-specific parameters (Scope 1 + electricity intensity per tonne of product):**

| Product Type | Electricity Intensity (MWh/t) | Scope 1 (tCO₂/t) | Source | Notes |
|---|---|---|---|---|
| `nickel_rkef` | 37.5 | 3.0 | JETP Captive Power Study Ch.2 | RKEF/NPI: 30-45 MWh/t, midpoint. Electric arc furnace — essentially all electric. |
| `steel_eaf` | 0.45 | 0.3 | worldsteel Association | EAF scrap-based: 0.4-0.5 MWh/t. Electricity-driven by definition. |
| `steel_bfbof` | 0.25 | 1.8 | worldsteel Association | BF-BOF: most energy from coke, low electricity. Coke is Scope 1 (reductant). |
| `aluminium` | 15.0 | 1.5 | IEA | Primary Hall-Héroult electrolysis: 13-17 MWh/t. Scope 1 = anode consumption. |
| `fertilizer` | 10.0 | 1.2 | IEA (legacy aggregated) | Ammonia+urea rolled together. Thermal-inclusive MWh/t (see §14.3). |
| `ammonia` | 10.0 | 2.3 | ICGD Indonesia (gas-SMR route) | Indonesia-specific Scope 1 from SMR feedstock gas, higher than legacy "fertilizer." Thermal-inclusive MWh/t (see §14.3). |
| `cement` | 0.9 | 0.52 | IEA | Thermal-inclusive MWh/t — includes kiln heat (see §14.3). True electric-only ≈ 0.11 MWh/t. Scope 1 = calcination. |

**Constants:** `CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE`, `CBAM_SCOPE1_TCO2_PER_TONNE`, and `CBAM_RE_ADDRESSABLE_FRACTION` (§14.3) in `src/assumptions.py`.

### 14.3 Emission intensity calculation

For each site × product type combination, two emission intensities and one addressable-savings figure are computed. The three variables that matter:

$$\text{scope2} = \text{electricity\_intensity} \times EF_{\text{grid}}$$
$$EI_{\text{current}} = \text{Scope 1} + \text{scope2}$$
$$EI_{\text{solar}} = \text{Scope 1}$$
$$\text{scope2\_addressable} = \text{scope2} \times \text{RE\_addressable\_fraction}$$

Where `EF_grid` is the site's regional grid emission factor (KESDM 2019 OM, same as §9.2; fallback 0.8 tCO₂/MWh).

**CBAM liability and solar savings per tonne of product (§14.4 applies the price × phase-out):**

$$C_{\text{CBAM}}(Y) = EI_{\text{current}} \times P_{\text{CBAM}} \times (1 - \text{free\_alloc}(Y))$$
$$S_{\text{CBAM}}(Y) = \text{scope2\_addressable} \times P_{\text{CBAM}} \times (1 - \text{free\_alloc}(Y))$$

Note that the cost uses **full** scope2 (the EU bills the whole electricity Scope 2 at the border regardless of what the local solar build can address), but the savings use the **addressable** fraction (solar can only cut what solar can actually displace). This asymmetry is the whole point of the M30 correction below.

**Worked examples at CBAM 2034 full exposure (€80/tCO₂ × 1.10 FX = $88/tCO₂):**

*Nickel RKEF at Morowali (SULAWESI grid EF = 0.63, RE-addressable = 1.0):*
- scope2 = 37.5 × 0.63 = 23.6 tCO₂/t
- EI_current = 3.0 + 23.6 = **26.6 tCO₂/t** → cost = 26.6 × $88 = **$2,341/t**
- scope2_addressable = 23.6 × 1.0 = 23.6 → savings = 23.6 × $88 = **$2,077/t** (~89% of cost)

*Cement at a Java site (Java-Bali grid EF ≈ 0.8, RE-addressable = 0.12):*
- scope2 = 0.9 × 0.8 = 0.72 tCO₂/t
- EI_current = 0.52 + 0.72 = **1.24 tCO₂/t** → cost = 1.24 × $88 = **$109/t**
- scope2_addressable = 0.72 × 0.12 = 0.086 → savings = 0.086 × $88 = **$7.6/t** (~7% of cost)

Solar cuts ~89% of the CBAM bill for nickel RKEF but only ~7% for cement. Same tool, very different leverage. That asymmetry is exactly what the Scope 1 / Scope 2 / RE-addressable split is designed to reveal.

**Why the RE-addressable fraction exists (M30, shipped 2026-04-18):**

For cement (0.9 MWh/t) and ammonia/fertilizer (10 MWh/t), `CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` is **thermal-inclusive** — the source figures convert kiln gas and SMR feedstock gas into electricity equivalents. Naively treating the full $EI_{\text{current}} - EI_{\text{solar}}$ as "avoided by solar" would quietly assume full thermal electrification **plus** 100% renewable supply — a much larger claim than "switch the site to solar." True electricity-only intensities are ~0.11 MWh/t for cement and ~1.0 MWh/t for fertilizer/ammonia (see `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` in `src/assumptions.py`).

**The fix:** `CBAM_RE_ADDRESSABLE_FRACTION` dict in `src/assumptions.py` scales scope2 savings down to the electric share:

| Product Type | RE-Addressable Fraction | Reasoning |
|---|---|---|
| `nickel_rkef` | 1.0 | Essentially electric arc furnace — the 37.5 MWh/t is real electricity |
| `steel_eaf` | 1.0 | Electricity-driven by definition |
| `aluminium` | 1.0 | Hall-Héroult electrolysis is all electric |
| `steel_bfbof` | 0.80 | Most energy is coke (Scope 1); ~0.20/0.25 ≈ 80% of the small Scope 2 is genuinely electric |
| `cement` | 0.12 | ~0.11/0.9 — kiln thermal dominates the thermal-inclusive MWh/t |
| `ammonia` | 0.10 | SMR gas is Scope 1 feedstock, not electricity |
| `fertilizer` | 0.10 | Same SMR dynamic as ammonia |

`src/dash/logic/cbam.py::compute_cbam_trajectory` multiplies Scope 2 savings by this fraction before rate × FX conversion; Scope 1 cost is unchanged. Effect (locked by `tests/test_logic_cbam.py`): cement 2034 savings 63.36 USD/t → 7.60 USD/t (~88% drop), ammonia savings ≈ 70 USD/t, nickel_rkef savings unchanged at ≈ $2,077/t. **Total CBAM cost (Scope 1 + full Scope 2) is unaffected** — only the claimed savings from switching to solar.

Full derivation in [docs/cbam_sector_data_collection_plan.md](cbam_sector_data_collection_plan.md) §4.1.

**Simplification:** The model assumes 100% electricity substitution to solar on the RE-addressable fraction. Partial substitution would scale savings proportionally. Hybrid heat strategies (electric kilns, green hydrogen SMR, green ammonia) that would raise the RE-addressable fraction over time are out of scope — the RE-addressable dict captures today's technology, not a 2040 decarbonized heat stack.

### 14.4 CBAM cost trajectory

CBAM charges phase in as free allocation of EU ETS certificates declines from 97.5% (2026) to 0% (2034).

**Certificate price:**
$$P_{\text{CBAM}} = \text{EU ETS price} \times \text{EUR/USD rate} = \text{€}80/\text{tCO}_2 \times 1.10 = \$88/\text{tCO}_2$$

**Free allocation phase-out schedule** (EU Regulation 2023/956, Art. 31):

| Year | Free Allocation (%) | Effective CBAM Rate (%) |
|---|---|---|
| 2026 | 97.5% | 2.5% |
| 2027 | 95.0% | 5.0% |
| 2028 | 90.0% | 10.0% |
| 2029 | 77.5% | 22.5% |
| 2030 | 51.5% | 48.5% |
| 2031 | 39.0% | 61.0% |
| 2032 | 26.5% | 73.5% |
| 2033 | 14.0% | 86.0% |
| 2034 | 0.0% | 100.0% |

**Cost per tonne of product at year Y** (EU bills the full scope2 at the border):
$$C_{\text{CBAM}}(Y) = EI_{\text{current}} \times P_{\text{CBAM}} \times (1 - \text{free\_alloc}(Y)) \quad [\text{USD/t product}]$$

**Savings per tonne from switching to solar at year Y** (solar only cuts the RE-addressable fraction of scope2 — see §14.3):
$$S_{\text{CBAM}}(Y) = \text{scope2\_addressable} \times P_{\text{CBAM}} \times (1 - \text{free\_alloc}(Y)) \quad [\text{USD/t product}]$$

$$\text{where } \text{scope2\_addressable} = \text{electricity\_intensity} \times EF_{\text{grid}} \times \text{RE\_addressable\_fraction}$$

For sectors where the intensity table is pure electricity (nickel_rkef, steel_eaf, aluminium), RE_addressable_fraction = 1.0 and savings equal the full Scope 2 × price. For thermal-inclusive sectors (cement, ammonia, fertilizer, steel_bfbof), RE_addressable_fraction < 1.0 and savings are correspondingly smaller — because solar doesn't electrify a cement kiln.

**Output fields:** `cbam_cost_2026/2030/2034_usd_per_tonne`, `cbam_savings_2026/2030/2034_usd_per_tonne`. Three snapshot years capture the trajectory shape: 2026 (minimal), 2030 (mid-transition), 2034 (full exposure).

**Constants:** `CBAM_CERTIFICATE_PRICE_EUR_TCO2`, `CBAM_EUR_USD_RATE`, `CBAM_FREE_ALLOCATION` in `src/assumptions.py`.

### 14.5 CBAM-adjusted competitive gap

For CBAM-exposed KEKs, the avoided carbon cost effectively reduces the solar LCOE gap versus grid power. The dashboard computes a CBAM-adjusted competitive gap that incorporates these savings.

**Step 1 — Convert savings from per-tonne to per-MWh:**
$$S_{\text{MWh}} = \frac{S_{\text{CBAM}}(2030)}{\text{electricity\_intensity}} \quad [\text{USD/MWh}]$$

This uses the 2030 savings (mid-transition) and divides by the product's electricity intensity to convert from "savings per tonne of product" to "savings per MWh of electricity consumed." The primary product type (first in the `cbam_product_type` list, i.e., highest electricity intensity) is used.

**Step 2 — Adjusted gap:**
$$\text{cbam\_adjusted\_gap} = \frac{LCOE_{\text{mid}} - S_{\text{MWh}} - C_{\text{grid}}}{C_{\text{grid}}} \times 100 \quad [\%]$$

A negative adjusted gap means solar is already competitive when CBAM savings are factored in. For high-intensity sectors like nickel RKEF (37.5 MWh/t), even modest per-MWh savings compound into large per-tonne savings, potentially flipping the economics.

**Output fields:** `cbam_savings_per_mwh` (USD/MWh), `cbam_adjusted_gap_pct` (%).

### 14.6 Per-product breakdown

Multi-product KEKs (e.g., a KEK with both nickel smelting and cement production) receive independent CBAM trajectories for each product type. This is necessary because:

1. **Units are incommensurable.** Nickel savings are in USD per tonne of ferro-nickel; cement savings are in USD per tonne of cement. These cannot be summed or averaged.
2. **Intensities differ by orders of magnitude.** Nickel RKEF consumes 37.5 MWh/t; cement consumes 0.9 MWh/t. The CBAM impact per tonne is vastly different.
3. **Scope 1 fractions differ.** Cement emissions are 60%+ Scope 1 (calcination), so solar addresses a smaller share. Nickel RKEF emissions are 85%+ Scope 2 (electric furnaces), so solar eliminates the dominant source.

The `cbam_per_product` field (dict, keyed by product type) stores per-product metrics:
- `emission_intensity_current` — total tCO2/t under current grid
- `emission_intensity_solar` — total tCO2/t with solar (= Scope 1 only)
- `cost_2026/2030/2034_usd_per_tonne` — CBAM liability at snapshot years
- `savings_2026/2030/2034_usd_per_tonne` — avoided CBAM cost from solar switch

For backward compatibility, flat `cbam_*` fields at the KEK level use the **primary product** (first matched, typically the highest electricity intensity). The per-product dict enables the ScoreDrawer CBAM trajectory chart to show independent cost curves for each product at a multi-product KEK.

**Implementation:** `logic/cbam.py::compute_cbam_trajectory()`, called from `logic/scorecard.py::compute_scorecard_live()`. The `CbamTrajectoryChart` component (`frontend/src/components/charts/CbamTrajectoryChart.tsx`) renders per-product trajectories.

---

## 15. User-Adjustable Parameters

**Tier 1 (primary):**

| Slider | Default | Range | Effect |
|---|---|---|---|
| WACC | 10% | 4-20% | Changes LCOE via CRF |
| CAPEX | 960 USD/kW | 500-1500 | Solar overnight capital cost |
| Lifetime | 27 years | 20-35 | Asset duration |

**Tier 2 (cost structure):**

| Slider | Default | Range | Effect |
|---|---|---|---|
| Fixed O&M | 7.5 $/kW-yr | 3-15 | Annual maintenance |
| Connection cost | 5 $/kW-km | 2-15 | Solar-to-substation line |
| Grid connection fixed | 80 $/kW | 30-200 | Substation interconnection |
| BESS CAPEX | 150 $/kWh | 100-300 | Battery storage cost |
| BESS Sizing Override | None (auto) | 1-16h | Override auto sizing (2h/4h/14h) to explore tradeoffs |
| IDR/USD rate | 15,800 | 14,000-18,000 | Exchange rate |

**Tier 3 (thresholds):**

| Slider | Default | Range | Effect |
|---|---|---|---|
| PVOUT threshold | 1,350 kWh/kWp | 1,200-1,800 | Minimum for `solar_attractive` |
| Plan-late threshold | 0.60 | 0.30-1.00 | Post-2030 share cutoff |
| GEAS threshold | 0.30 | 0.05-0.50 | Min green share for `solar_now` |
| Resilience gap | 20% | 5-50% | Max LCOE gap for `invest_resilience` |
| Min viable capacity | 20 MWp | 5-50 | Project viability floor |
| Reliability threshold | 0.75 | 0.30-1.00 | Reliability req for `invest_battery` |

**Implementation:** Slider configs in `src/dash/constants.py` (TIER1_SLIDERS, TIER2_SLIDERS, TIER3_SLIDERS). Served via `GET /api/defaults`. Changes trigger `POST /api/scorecard` recomputation. V3.6: BESS CAPEX and BESS Sizing sliders are co-located with battery output in the ScoreDrawer Economics tab (not the Assumptions panel), so the user sees cost impact immediately next to the slider.

---

## 16. Known Limitations

| Limitation | Impact | Mitigation |
|---|---|---|
| PVOUT from Global Solar Atlas, not site measurement | +/- 5-10% LCOE uncertainty | Use `pvout_best_50km` not centroid; show LCOE bands |
| ~~Panel degradation not modeled~~ | ~~LCOE understated ~6-7%~~ | ✅ **Resolved (V3.4):** Panel degradation modeled via midpoint approximation: `degradation_factor = 1 - (0.005 × lifetime / 2)`. Default 0.5%/yr over 27yr → factor 0.9325 → ~7% LCOE increase. `lcoe_solar()` param `degradation_annual_pct`. Source: NREL Jordan & Kurtz 2013. |
| Solar lifecycle emissions excluded from carbon breakeven | Breakeven ~5-8% too optimistic | Corrected formula: gap / (grid_EF - 0.040) |
| Grid emission factors are 2019 vintage | Indonesia grid mix has shifted | Update when KESDM publishes newer Tier 2 factors |
| Grid-connected solar requires PLN partnership | PLN controls procurement | Dashboard reads as "if procurement enabled, here are the economics" |
| Connection costs are highly site-specific | Terrain, land, permitting vary enormously | Parameters are user-adjustable with wide ranges |
| KEK demand figures not available | GEAS allocation approximate | Label as indicative, not contractual |
| RUPTL capacity additions are planned, not committed | Flags may change | Vintage-stamp RUPTL data |
| No reliability data (SAIDI/SAIFI) | Cannot quantify reliability premium | Deferred until PLN data available |
| Substation capacity data inconsistent | Some entries have normalized values | Dashboard flags as "capacity unverified" |
| CAPEX from ESDM catalogue, not market data | Actual +/- 15-20% | Show CAPEX sensitivity via LCOE bands |

---

## 17. Codebase Audit Notes

Audit performed April 2026 against the current implementation. The codebase is ~95% aligned with this methodology document.

### Discrepancies found and status

| Finding | Status | Detail |
|---|---|---|
| `action_flags()` returns 6 keys, not 10 | By design | `invest_resilience` is computed by a separate `invest_resilience()` function. `not_competitive` is derived in the scorecard builder as the fallback when no other flag fires. `cbam_urgent` is computed in `logic/scorecard.py` from CBAM-adjusted gap. All are merged in `logic/scorecard.py` before the API serves them. Total: 10 flags in solar-mode `ActionFlag` enum (14 across all energy modes). |
| Docs referenced `SOLAR_TO_SUBSTATION_LOW_THRESHOLD_KM = 10.0` | Resolved | V3.1 tightened to `SOLAR_TO_SUBSTATION_THRESHOLD_KM = 5.0` in `assumptions.py:216`. This document uses the current 5km value. |
| Old docs used `invest_grid` (umbrella) | Resolved | V3 splits into `invest_transmission` + `invest_substation`. Code matches. |
| Old docs used `firming_needed` | Resolved | Renamed to `invest_battery` in V3. Code matches. |
| Grid emission factors 2019 vintage | Known limitation | 7 years old. Documented as provisional in `assumptions.py:402`. |
| V1 aliases still in `assumptions.py` | Tech debt | `GENTIE_COST_PER_KW_KM`, `SUBSTATION_WORKS_PER_KW`, `TRANSMISSION_LEASE_*` retained for backward compatibility. Marked with `TODO(V2): Remove`. |

### Key implementation files

| Component | File |
|---|---|
| Core model (all formulas) | `src/model/basic_model.py` |
| All constants/assumptions | `src/assumptions.py` |
| Solar resource pipeline | `src/pipeline/build_fct_kek_resource.py` |
| Wind resource pipeline | `src/pipeline/build_fct_kek_wind_resource.py` |
| Wind buildability raster | `src/pipeline/build_wind_buildable_raster.py` |
| Wind buildability filters | `src/pipeline/wind_buildability_filters.py` |
| Wind buildable polygons | `src/pipeline/build_wind_buildable_polygons.py` |
| Substation proximity (3-point) | `src/pipeline/build_fct_substation_proximity.py` |
| LCOE pipeline | `src/pipeline/build_fct_lcoe.py` |
| Buildability filters | `src/pipeline/buildability_filters.py` |
| Scorecard builder | `src/pipeline/build_fct_kek_scorecard.py` |
| Dashboard logic | `src/dash/logic/` (package: assumptions, lcoe, cbam, grid, technology, scorecard) |
| API routes | `src/api/routes/scorecard.py` |
| Captive coal pipeline | `src/pipeline/build_fct_captive_coal.py` |
| Captive nickel pipeline | `src/pipeline/build_fct_captive_nickel.py` |
| Captive steel pipeline | `src/pipeline/build_fct_captive_steel.py` |
| Captive cement pipeline | `src/pipeline/build_fct_captive_cement.py` |
| Hybrid optimization | `src/model/basic_model.py:hybrid_lcoe_optimized()` |
| Grid cost proxy pipeline | `src/pipeline/build_fct_grid_cost_proxy.py` |
| Demand pipeline | `src/pipeline/build_fct_kek_demand.py` |
| Wind LCOE pipeline | `src/pipeline/build_fct_lcoe_wind.py` |
| RUPTL pipeline | `src/pipeline/build_fct_ruptl_pipeline.py` |
| Wind tech cost dimension | `src/pipeline/build_dim_tech_cost_wind.py` |
| KEK dimension table | `src/pipeline/build_dim_kek.py` |
| Solar tech cost dimension | `src/pipeline/build_dim_tech_cost.py` |
| Solar buildable raster | `src/pipeline/build_buildable_raster.py` |
| Solar buildable polygons | `src/pipeline/build_buildable_polygons.py` |
| CBAM trajectory chart | `frontend/src/components/charts/CbamTrajectoryChart.tsx` |
| CBAM logic (flag + costs) | `src/dash/logic/cbam.py` |
| Walkthrough guide | `frontend/src/components/ui/WalkthroughModal.tsx` |
| Action flag legend | `frontend/src/components/ui/ActionFlagLegend.tsx` |
| Tests | `tests/test_model.py`, `tests/test_pipeline.py`, `tests/test_action_flag_enum.py` |

---

## 18. Assumptions Summary

| Assumption | Value | Source | Sensitivity |
|---|---|---|---|
| Default WACC | 10% | ADB (2020), IRENA (2023) | Slider: 4-20% |
| Grid connection cost | \$5/kW-km + \$80/kW | Industry estimates | Slider: \$2-15/kW-km, \$30-200/kW |
| Land cost | \$45/kW | \$3/m2 x 1.5 ha/MW | Slider: \$0-300/kW |
| BESS CAPEX | \$150/kWh | Market-adjusted 2025 (BNEF \$110, Ember \$125, +Indonesia premium) | Slider: \$100-300/kWh |
| PVOUT siting radius | 50km | Typical siting flexibility | Fixed |
| Regional solar CF (GEAS) | 20% | Representative for Indonesia | Low sensitivity |
| Plan-late threshold | post2030 >= 60% | Majority post-2030 = late | Low sensitivity |
| Reliability threshold | >= 0.75 | Manufacturing/processing sectors | Per kek_grid_region_mapping.csv |
| Solar PVOUT threshold | 1,350 kWh/kWp/yr | ~15.4% CF minimum | User-adjustable |
| IDR/USD rate | 15,800 | 2024 reference | Slider: 14,000-18,000 |

---

## 19. Reproducibility

All primary inputs are publicly available. See the [References](#references) section for full citations, URLs, and access details.

| Dataset | Access | License |
|---|---|---|
| Global Solar Atlas v2 GeoTIFFs | https://globalsolaratlas.info | CC BY 4.0 |
| Global Wind Atlas v3 GeoTIFF | https://globalwindatlas.info | CC BY 4.0 |
| ESDM Technology Catalogue 2023 | ESDM publications portal | Government publication |
| PLN RUPTL 2025-2034 | ESDM/PLN publications | Government publication |
| PLN SIMOL (substations, grid lines) | PLN geoportal | Government data |
| KEK boundary polygons | OSS/KEK portal | Government data |
| ESA WorldCover 10m v200 | https://worldcover2021.esa.int | CC BY 4.0 |
| Copernicus DEM GLO-30 | https://spacedata.copernicus.eu | Open license |
| GFW Peatland Map | https://data.globalforestwatch.org | CC BY 4.0 |
| GEM Global Coal Plant Tracker | https://globalenergymonitor.org | CC BY 4.0 |
| CGSP Nickel Tracker | https://chinaglobalsouth.com | CC BY 4.0 |

Pipeline: `run_pipeline.py` -> `outputs/data/processed/` -> `src/model/` -> dashboard.

---

## 20. Regulatory References

See the [Indonesian Regulatory Framework](#indonesian-regulatory-framework) table in the References section for full regulation titles. Summary of regulations referenced in this methodology:

| Regulation | Relevance to this model |
|---|---|
| UU No. 30/2009 | Electricity Law. PLN as sole grid operator, captive power provisions. |
| PP No. 14/2012 | IUPTLS licensing for captive generation (>500 kW). |
| PP No. 57/2016 | Peatland ecosystem protection (buildability filter). |
| PP No. 112/2022 | KEK-specific power procurement exemptions. Captive coal phase-out by 2050. |
| Permen ESDM No. 1/2015 | Authorizes grid wheeling (not implemented in practice). |
| Permen ESDM No. 1/2017 | Grid connection standards for private generators. |
| Permen ESDM No. 27/2017 | Connection standards. Gen-tie ownership transfers to PLN post-commissioning. |
| Permen ESDM No. 11/2021 | IUPTLS licensing regime. |
| Permen ESDM No. 7/2024 | I-4/TT industrial tariff (996.74 Rp/kWh). Updated renewable procurement framework. |
| Kepmen ESDM 169/2021 | BPP Pembangkitan (cost of supply) by grid region, FY2020 vintage. |

---

## Appendix A: Buildability Filter Details

### Layer 1: Hard Regulatory Exclusions

**1a. Kawasan Hutan:** All sub-categories treated as excluded (conservative). PPKH permits take 3-5 years, infeasible for captive solar timelines.

| Sub-category | Solar permissible? |
|---|---|
| Conservation Areas (Suaka Alam / Pelestarian Alam) | No, hard exclusion |
| Protection Forest (Hutan Lindung) | No, hard exclusion |
| Production Forest (HP, HPT, HPK) | Possible with PPKH but excluded in model |

**1b. Peatland:** PP No. 57/2016 restricts development on peatland ecosystem function zones. Excluded in model.

**1c. Land cover (ESA WorldCover):** Tree cover, cropland, urban, water excluded. Numerically dominant filter (removes 52-93% of raw pixels across KEKs).

### Layer 2: Terrain Suitability

- Slope > 8 deg: hard exclusion (civil works prohibitive)
- Elevation > 1,500m: hard exclusion (access cost)
- Aspect: NOT filtered (Indonesia is near-equatorial, <5% energy loss from suboptimal aspect)

### Layer 3: Infrastructure Proximity

**Layer 3a: Road proximity (v1.2).** Pixels more than 10km from a motorable road are excluded. Data source: OpenStreetMap via Geofabrik Indonesia PBF extract. Road types included: motorway, trunk, primary, secondary, tertiary. Residential, service, track, footway, and path roads are excluded. Distance computed via Euclidean distance transform (`scipy.ndimage.distance_transform_edt`) on the nationwide rasterized road network at ~1km resolution, with latitude-corrected pixel sampling. The 10km threshold represents a practical construction access limit: sites beyond this distance face prohibitive access road costs in Indonesian terrain. Applies to both solar and wind pipelines with the same threshold.

**Layer 3b: Substation proximity** is captured separately in `fct_substation_proximity` (see Section 8).

### Layer 4: Minimum Contiguous Area

10 ha minimum after all filters. At ~1km PVOUT resolution (~86 ha/pixel), this is a near-no-op. Retained for area counting and future higher-resolution data.

---

## Appendix B: Legal Framework for Captive Solar

Under Indonesian electricity law, "captive power" (pembangkit untuk kepentingan sendiri) is defined on an entity/integration basis, not a distance basis. No regulation specifies a maximum km distance.

**Three-part qualification test:**
1. Same legal entity owns both generation and load
2. 100% dedicated to own use (no third-party sales)
3. Plant and load managed as single integrated unit

The 50km radius in this model is a siting economics constraint, not a legal limit.

**PLN substation connection:** Private generators may connect to PLN substations (Permen ESDM No. 27/2017). Gen-tie ownership typically transfers to PLN post-commissioning. Connection cost covers gen-tie construction, substation works, parallel operation capacity charge, and transmission lease.

**Power wheeling:** Legally authorized (Permen ESDM No. 1/2015) but PLN has rejected all requests in practice. Not assumed as a pathway in this model.

---

## Appendix C: Evolution from V1 to V3

| Change | V1 | V3 (current) |
|---|---|---|
| Siting scenario | `remote_captive` (50km private gen-tie) | `grid_connected_solar` (solar to nearest substation) |
| Gen-tie cost | \$5/kW-km + \$150/kW fixed | \$5/kW-km + \$80/kW fixed (short connection) |
| Distance used | KEK-to-substation | Solar-to-substation (3-point proximity) |
| Transmission lease | \$5-15/MWh operating adder | Removed (PLN system cost, in BPP/tariff) |
| Land cost | Not modeled | \$45/kW (grid-connected only, user-adjustable) |
| Firming/battery | Flat \$6/\$11/\$16 per MWh | BESS LCOE model: 14h bridge-hours + 87% RTE for high-reliability loads (~\$290/MWh); 2h cloud-firming for others (~\$45/MWh) |
| Action flags | 5 flags | 14 flags across 4 energy modes (split invest_grid, add not_competitive, no_solar_resource, cbam_urgent, wind_now, hybrid_now, no_wind_resource, no_re_resource) |
| Grid integration | Not present | 5 categories from 3-point proximity |
| Solar site coordinates | Not stored | `best_solar_site_lat/lon` |
| Substation connectivity | Not checked | Geometric check against PLN grid lines |
| Substation capacity | Not assessed | Traffic light system (green/yellow/red/unknown) |
| Competitive gap | Single (LCOE vs tariff/BPP) | Split: IPP gap (vs BPP) + tenant gap (vs tariff) |

### Constants renamed or deprecated

| V1 constant | V3 replacement | Old default | New default |
|---|---|---|---|
| `GENTIE_COST_PER_KW_KM` | `CONNECTION_COST_PER_KW_KM` | \$5.0 | \$5.0 |
| `SUBSTATION_WORKS_PER_KW` | `GRID_CONNECTION_FIXED_PER_KW` | \$150.0 | \$80.0 |
| `TRANSMISSION_LEASE_*` | Deprecated | \$5-15/MWh | Removed |
| `FIRMING_ADDER_MID_USD_MWH` | `BESS_CAPEX_USD_PER_KWH` | \$11 flat | \$250/kWh |
| - | `BESS_ROUND_TRIP_EFFICIENCY` (V3.3) | - | 0.87 |
| - | `SOLAR_PRODUCTION_HOURS` (V3.3) | - | 10.0h |
| - | `BESS_BRIDGE_HOURS_ENABLED` (V3.3) | - | True |
| `SOLAR_TO_SUBSTATION_LOW_THRESHOLD_KM` | `SOLAR_TO_SUBSTATION_THRESHOLD_KM` | 10.0 km | 5.0 km |
| - | `LAND_COST_USD_PER_KW` (new) | - | \$45.0 |

---

*This document should be reviewed by an energy economist familiar with Indonesia's power sector before public release. Key review areas: Section 7 (grid cost reference), Section 10 (action flags), Section 11 (GEAS allocation), Section 14 (CBAM exposure and product parameters).*

---

## References

### Solar and Wind Resource Data

- World Bank / Solargis. (2020). *Global Solar Atlas v2.0: Technical Report*. Washington, DC: World Bank Group. Available at: https://globalsolaratlas.info. Dataset: PVOUT (Photovoltaic Power Output), long-term average (LTAym), ~1 km resolution. License: CC BY 4.0.
- DTU Wind Energy / World Bank. (2022). *Global Wind Atlas v3.0*. Technical University of Denmark. Available at: https://globalwindatlas.info. Dataset: wind speed at 100m hub height, ~1 km resolution. License: CC BY 4.0.

### Technology Cost Parameters

- Kementerian ESDM (Ministry of Energy and Mineral Resources). (2023). *Katalog Teknologi: Katalog Teknologi Energi Baru, Terbarukan, dan Konservasi Energi 2023* (Technology Catalogue for New, Renewable Energy and Energy Conservation). Jakarta: ESDM. Solar PV parameters from p. 66 (TECH006); wind parameters from p. 90. Pipeline extraction preserves catalogue values (960 USD/kW); slider default adjusted to 850 USD/kW per 2025 market data.
- BloombergNEF. (2025). *Lithium-ion Battery Price Survey 2025*. Global utility-scale system price: \$110/kWh (pack-only LFP: \$70/kWh). Chinese tender average: \$63/kWh. Used for BESS storage model (§6.3).
- Ember. (2025). *Global Electricity Mid-Year Insights 2025*. Battery system cost for non-China/US markets: \$125/kWh. Confirms BNEF pricing trajectory.
- IRENA. (2024). *Renewable Power Generation Costs in 2023*. Global solar PV: \$691/kW; Asia excl. China/India: \$1,133/kW; Indonesia range: \$800-1,000/kW. Used to market-adjust ESDM 2023 catalogue default.
- IEA. (2024). *Cost of Capital Observatory*. Indonesia RE project WACC: ~10%. Confirms existing default.

### Grid Cost and Tariff Data

- Kementerian ESDM. (2024). *Peraturan Menteri ESDM Nomor 7 Tahun 2024 tentang Tarif Tenaga Listrik* (Regulation on Electricity Tariffs). Jakarta. Lampiran IV: I-4/TT industrial tariff = 996.74 Rp/kWh.
- Kementerian ESDM. (2021). *Keputusan Menteri ESDM Nomor 169.K/HK.02/MEM.L/2021 tentang Biaya Pokok Penyediaan Tenaga Listrik* (Ministerial Decree on Cost of Electricity Supply). Jakarta. BPP (Biaya Pokok Penyediaan) by PLN grid region, FY2020 vintage.

### Geospatial and Buildability Data

- European Space Agency. (2021). *ESA WorldCover 10m v200*. Available at: https://worldcover2021.esa.int. Land cover classification used for buildability exclusion (tree cover, cropland, urban, water). License: CC BY 4.0.
- European Space Agency / Copernicus. (2021). *Copernicus DEM GLO-30*. Available at: https://spacedata.copernicus.eu. Digital elevation model at 30m resolution, used for slope and elevation filters.
- Global Forest Watch. (2023). *GFW Peatland Map v20230315*. World Resources Institute. Available at: https://data.globalforestwatch.org. Peatland exclusion layer for Indonesia.
- KLHK (Ministry of Environment and Forestry). (2017). *Kawasan Hutan* (Forest Zone) dataset, September 2017 vintage. Used for hard regulatory exclusion of conservation and protection forests.

### Captive Power and Industrial Data

- Global Energy Monitor. (2024). *Global Coal Plant Tracker (GCPT)*. Available at: https://globalenergymonitor.org/projects/global-coal-plant-tracker. Captive coal plants within 50km of each KEK. License: CC BY 4.0. Accessed April 2026.
- China Global South Project. (2024). *CGSP Indonesia Nickel Tracker*. Available at: https://chinaglobalsouth.com. Nickel smelter locations, ownership, and process types. License: CC BY 4.0. Accessed April 2026.

### Grid Infrastructure

- PLN (Perusahaan Listrik Negara). (2024). *SIMOL: Sistem Informasi Monitoring Online*. Substation data (2,913 substations with capacity, voltage, PLN region, operational status) and transmission line data (1,595 lines). Accessed via public GeoJSON export.
- PLN. (2024). *RUPTL 2025-2034: Rencana Usaha Penyediaan Tenaga Listrik* (Electricity Supply Business Plan). Jakarta. Planned generation capacity additions by region and year.

### Emissions and Carbon Pricing

- KESDM (Kementerian ESDM). (2019). *Grid Emission Factor: Operating Margin by PLN Grid Region*. Used for carbon breakeven price calculation (§9.2). Tier 2 OM factors by grid region.
- IPCC. (2022). *Climate Change 2022: Mitigation of Climate Change. Contribution of Working Group III to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change*. Cambridge University Press. doi:10.1017/9781009157926. Solar PV lifecycle emissions: ~40 gCO2/kWh.
- European Parliament and Council. (2023). *Regulation (EU) 2023/956 establishing a carbon border adjustment mechanism*. Official Journal of the European Union, L 130/52. Art. 31: free allocation phase-out schedule 2026-2034. Used for CBAM cost trajectory (§14.4).
- worldsteel Association. (2023). *Steel Statistical Yearbook 2023*. Brussels. EAF and BF-BOF electricity intensity and process emission benchmarks. Used for steel CBAM parameters (§14.2).
- JETP Secretariat. (2023). *Indonesia Just Energy Transition Partnership: Captive Power Study*. Ch. 2: nickel RKEF electricity intensity (30-45 MWh/t). Used for nickel CBAM parameters (§14.2).

### Infrastructure Cost Benchmarks

- IFC (International Finance Corporation). (2015). *Utility-Scale Solar Photovoltaic Power Plants: A Project Developer's Guide*. Washington, DC: IFC. Used for gen-tie and substation connection cost benchmarks.
- IRENA (International Renewable Energy Agency). (2023). *Renewable Power Generation Costs in 2022*. Abu Dhabi: IRENA. Reference for substation upgrade cost ranges.

### Indonesian Regulatory Framework

| Regulation | Full Title | Relevance |
|---|---|---|
| UU No. 30/2009 | Undang-Undang tentang Ketenagalistrikan (Electricity Law) | PLN as sole grid operator, captive power provisions |
| PP No. 14/2012 | Peraturan Pemerintah tentang IUPTLS | Licensing for captive generation (>500 kW) |
| PP No. 57/2016 | Peraturan Pemerintah tentang Perlindungan Ekosistem Gambut | Peatland development restrictions |
| PP No. 112/2022 | Peraturan Pemerintah tentang KEK | KEK-specific power procurement exemptions, captive coal phase-out by 2050 |
| Permen ESDM No. 1/2015 | Peraturan Menteri tentang Wheeling | Authorizes grid wheeling (not implemented in practice) |
| Permen ESDM No. 1/2017 | Peraturan Menteri tentang Koneksi Grid | Grid connection standards for private generators |
| Permen ESDM No. 27/2017 | Peraturan Menteri tentang Sambungan Tenaga Listrik | Connection standards. Gen-tie ownership transfers to PLN post-commissioning |
| Permen ESDM No. 11/2021 | Peraturan Menteri tentang IUPTLS | Updated IUPTLS licensing regime |
| Permen ESDM No. 7/2024 | Peraturan Menteri tentang Tarif Tenaga Listrik | I-4/TT industrial tariff. Updated renewable procurement framework |
| Kepmen ESDM 169/2021 | Keputusan Menteri tentang BPP | BPP Pembangkitan by grid region (FY2020) |
