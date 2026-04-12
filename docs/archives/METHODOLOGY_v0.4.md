# Methodology: Indonesia KEK Clean Power Competitiveness Model

**Version:** 0.4 (updated April 2026) — V2 grid-connected solar thesis
**Status:** ✅ Fully implemented in code — 11 pipeline steps, 25 KEKs, 327 tests passing
**Intended audience:** Energy economists, development bank analysts, peer reviewers

This document specifies the analytical methodology used in the Indonesia KEK Power Competitiveness tool. It serves three purposes:
1. A specification that `src/model/basic_model.py` must implement exactly
2. A document for external methodology review before code is written
3. The basis for a future methods note / working paper

All formulas are stated with explicit units. All assumptions are documented with their source and rationale. Known limitations are in Section 6.

---

## Table of Contents

- [Workflow Summary](#workflow-summary)
- [1. Scope and Core Question](#1-scope-and-core-question)
- [2. Solar Resource: Capacity Factor from PVOUT](#2-solar-resource-capacity-factor-from-pvout)
  - [2.1 Input data](#21-input-data)
  - [2.2 Annual PVOUT conversion](#22-annual-pvout-conversion)
  - [2.3 Capacity factor](#23-capacity-factor)
  - [2.4 PVOUT extraction per KEK](#24-pvout-extraction-per-kek)
  - [2.5 Geospatial Buildability Constraints](#25-geospatial-buildability-constraints)
- [2A. Captive Solar: Legal Framework, Siting Scenarios, and PLN Connection Costs](#2a-captive-solar-legal-framework-siting-scenarios-and-pln-connection-costs)
  - [2A.1 Legal Definition of Captive Power](#2a1-legal-definition-of-captive-power-kepentingan-sendiri)
  - [2A.2 PLN Substation Connection](#2a2-pln-substation-connection--legality-and-fees)
  - [2A.3 Power Wheeling](#2a3-power-wheeling--legally-permitted-practically-blocked)
  - [2A.4 Two Siting Scenarios](#2a4-two-siting-scenarios)
  - [2A.5 Model Scope](#2a5-model-scope)
  - [2A.6 Three-Point Proximity Analysis](#2a6-three-point-proximity-analysis)
- [2B. Wind Resource: Capacity Factor from Wind Speed](#2b-wind-resource-capacity-factor-from-wind-speed)
  - [2B.1 Input data](#2b1-input-data)
  - [2B.2 Wind speed extraction per KEK](#2b2-wind-speed-extraction-per-kek)
  - [2B.3 Wind capacity factor](#2b3-wind-capacity-factor)
  - [2B.4 Wind LCOE](#2b4-wind-lcoe)
  - [2B.5 Best RE technology selection](#2b5-best-re-technology-selection)
- [3. Levelized Cost of Energy (LCOE)](#3-levelized-cost-of-energy-lcoe)
  - [3.1 Formula](#31-formula)
  - [3.2 Technology parameters](#32-technology-parameters-tech006--utility-scale-solar-pv)
  - [3.3 WACC](#33-wacc)
  - [3.4 LCOE bands](#34-lcoe-bands)
- [4. Grid Cost Reference](#4-grid-cost-reference)
  - [4.1 What is being compared](#41-what-is-being-compared)
  - [4.2 Coverage by PLN grid system](#42-coverage-by-pln-grid-system)
  - [4.3 Benchmark mode](#43-benchmark-mode-user-selectable)
- [5. Competitiveness Metrics and Action Flags](#5-competitiveness-metrics-and-action-flags)
  - [5.1 Solar competitive gap](#51-solar-competitive-gap)
  - [5.2 Action flags](#52-action-flags)
  - [5.2b Resilience layer](#52b-resilience-layer-invest_resilience)
  - [5.3 GEAS green share](#53-geas-green-share)
  - [5.3b Carbon breakeven price](#53b-carbon-breakeven-price)
  - [5.4 Flip scenario](#54-flip-scenario)
  - [5.5 Grid-connected solar cost model](#55-grid-connected-solar-cost-model)
  - [5.6 DFI Grid Infrastructure Investment Model](#56-dfi-grid-infrastructure-investment-model)
- [6. Known Limitations and Caveats](#6-known-limitations-and-caveats)
- [7. Assumptions Summary](#7-assumptions-summary)
- [8. Open Methodological Questions](#8-open-methodological-questions)
- [9. Reproducibility](#9-reproducibility)

---

## Workflow Summary

The model answers one question per KEK: **where do good solar sites, grid infrastructure, and industrial demand overlap — and what grid investment is needed to connect them?**

### Data flow (5 steps)

**Step 1 — Solar resource**

$$\text{PVOUT}_{\text{annual}} = \text{PVOUT}_{\text{daily}} \times 365 \quad [\text{kWh/kWp/yr}]$$

$$CF = \frac{\text{PVOUT}_{\text{annual}}}{8{,}760}$$

**Step 2 — LCOE**

$$CRF = \frac{r \cdot (1+r)^n}{(1+r)^n - 1}$$

$$LCOE = \frac{CAPEX \cdot CRF + FOM}{CF \times 8.76} \quad [\text{USD/MWh}]$$

**Step 2b — Wind resource** (v0.3, implemented)

$$CF_{\text{wind}} = f(\text{wind\_speed}_{100m})$$

Piecewise-linear empirical mapping (see Section 2B.3). Wind LCOE computed with same CRF annuity method using wind-specific CAPEX/FOM/lifetime.

**Step 3 — Grid cost reference** (Permen ESDM No.7/2024, Lampiran IV)
- I-4/TT tariff = 996.74 Rp/kWh $\approx$ 63.1 USD/MWh (uniform nationwide)
- I-3/TM tariff = 1,035.78 Rp/kWh $\approx$ 65.6 USD/MWh (uniform nationwide)
- BPP Pembangkitan varies by PLN system (Kepmen ESDM 169/2021)
- **Benchmark mode** (user-selectable): tariff (what tenants pay, default) or BPP (what electricity costs PLN to generate). Switches the grid cost comparator used in gap and action flag calculations.

**Step 4 — Competitiveness gap**

$$\text{gap} = \frac{LCOE - C_{\text{grid}}}{C_{\text{grid}}} \times 100\%$$

Negative = solar already cheaper; Positive = solar more expensive

**Step 5 — Action flags** (per KEK)
- `solar_now`: `grid_ready` category AND solar LCOE < grid cost AND PVOUT $\geq$ threshold
- `invest_grid`: `invest_grid` category AND solar resource viable — targeted grid investment unlocks solar
- `grid_first`: `grid_first` category — major grid expansion needed
- `firming_needed`: solar attractive AND industrial reliability req $\geq$ 0.75
- `plan_late`: $\geq$ 60% of RUPTL solar additions slip to post-2030

### Key inputs and sources

| Input | Value / Range | Source |
|-------|--------------|--------|
| PVOUT | 1,296–1,730 kWh/kWp/yr (extracted) | Global Solar Atlas v2 GeoTIFF |
| Solar CF | 0.148–0.197 | Derived from PVOUT ÷ 8,760 |
| Wind speed (100m) | 2–8 m/s (Indonesia range) | Global Wind Atlas v3 GeoTIFF |
| Wind CF | 0.00–0.27 | Piecewise-linear from wind speed (Section 2B.3) |
| Solar CAPEX (central) | 960 USD/kW | ESDM Tech Catalogue 2023, TECH006, p.66 |
| Solar FOM | 7.5 USD/kW/yr | ESDM Tech Catalogue 2023, TECH006, p.66 |
| Wind CAPEX/FOM/Lifetime | from ESDM catalogue | TECH_WIND_ONSHORE |
| WACC | 4–20% (slider, default 10%) | User-adjustable |
| Solar lifetime | 27 years | ESDM Tech Catalogue 2023, TECH006, p.66 |
| Grid cost (tariff mode) | 63.1 USD/MWh (I-4/TT) | Permen ESDM No.7/2024, uniform national |
| Grid cost (BPP mode) | 57–133 USD/MWh by region | Kepmen ESDM 169/2021 |
| Benchmark mode | Tariff (default) or BPP | User-selectable toggle |
| GEAS allocation | Pro-rata by demand share | RUPTL 2025–2034 pre-2030 solar additions |

### Critical caveats

- **PVOUT is filtered through all 4 buildability layers.** Kawasan Hutan (KLHK 66K-polygon forest estate, Sep 2017), peatland (KLHK vector boundaries), ESA WorldCover land cover, and DEM slope/elevation are all applied. With all files present, `resource_quality = "filtered"`. The pipeline falls back gracefully if any file is missing.
- **I-4/TT tariff ≠ BPP.** The tariff is what KEK tenants pay. PLN BPP Pembangkitan (generation cost of supply, Kepmen ESDM 169/2021) varies by region: Java-Bali ~$57/MWh vs Papua ~$133/MWh. Both are in the model. Users can toggle between tariff and BPP as the grid cost comparator (see Section 4.3).
- **CAPEX/FOM are verified.** TECH006 values are sourced from the ESDM Technology Catalogue 2023, datasheet p.66, and stored as `VERIFIED_TECH006_DATA` in `src/pipeline/pdf_extract_esdm_tech.py`.
- **Wind is included.** Onshore wind LCOE is computed per KEK using Global Wind Atlas v3 data and ESDM TECH_WIND_ONSHORE parameters. `best_re_technology` selects the cheaper of solar vs wind.
- **IDR/USD rate:** 15,800 IDR/USD (default, user-adjustable via Tier 2 slider: 14,000–18,000). Tariff in IDR is subject to quarterly tariff adjustment (Pasal 6, Permen ESDM No.7/2024).

---

## 1. Scope and Core Question

**Question:** For each of Indonesia's 25 Special Economic Zones (KEK), is utility-scale renewable captive generation currently cheaper than buying power from the PLN grid — and if not, how close is it, and what would change that?

**Unit of analysis:** KEK zone (25 zones). Results are at zone level, not tenant level or project level. A zone-level finding that "Kendal is 12% away from solar-competitive" means the representative economics for a utility-scale captive renewable plant at that zone, not for any specific tenant's load profile.

**Technology scope:** Utility-scale ground-mounted solar PV (TECH006) and onshore wind (TECH_WIND_ONSHORE) from the ESDM Technology Catalogue. The model computes LCOE for both technologies per KEK and selects the cheaper option as `best_re_technology`. No geothermal or storage in the base model; architecture supports extension.

**Time horizon:** Current economics (2023–2025 cost vintage). No forward cost projections in MVP.

---

## 2. Solar Resource: Capacity Factor from PVOUT

### 2.1 Input data

**Source:** Global Solar Atlas v2 (World Bank / Solargis), long-term average (LTAym)
**File:** `Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip`
**Layer used:** PVOUT (Photovoltaic Power Output)
**Native unit:** kWh/kWp/day (average daily totals)

### 2.2 Annual PVOUT conversion

The GeoTIFF stores **average daily** values. Convert to annual before any further calculation:

$$\text{PVOUT}_{\text{annual}} = \text{PVOUT}_{\text{daily}} \times 365 \quad [\text{kWh/kWp/yr}]$$

**Plausibility bounds for Indonesia:** 1,200 ≤ PVOUT_annual ≤ 2,200 kWh/kWp/yr. Values outside this range indicate a unit error or wrong raster band. Enforce as an assertion in `build_fct_kek_resource.py`.

### 2.3 Capacity factor

$$CF = \frac{\text{PVOUT}_{\text{annual}}}{8{,}760}$$

Where 8,760 = hours per year. CF is dimensionless (decimal, not percent).

**Interpretation:** A KEK with PVOUT_annual = 1,650 kWh/kWp/yr has CF = 0.188 (18.8% capacity factor). This represents the fraction of time a 1 kWp panel produces its nameplate output, averaged over the year.

**Implementation note:** The formula assumes PVOUT is the production of a fixed-tilt, grid-connected PV system at standard conditions, which is how Global Solar Atlas defines it. No additional de-rating (soiling, temperature, inverter losses) is applied in the base model — these are embedded in Global Solar Atlas PVOUT estimates. Specifically, GSA uses the Faiman thermal model to account for temperature-dependent efficiency losses (~0.35–0.5%/°C above 25°C STC). At Indonesia's average ambient temperatures (27–33°C), this represents a ~3–5% production reduction vs. STC, which is already reflected in the PVOUT values.

**Degradation note:** Solar panel output degrades ~0.5%/year over the asset lifetime. Over 27 years, cumulative output is ~93–94% of the constant-CF assumption used in the CRF annuity method. This means the LCOE values in this model are understated by ~6–7%. This is standard practice for screening-level LCOE models (IEA WEO, IRENA Power Generation Costs use the same simplification). For project-level financial models, apply a degradation-adjusted CF.

### 2.4 PVOUT extraction per KEK

Two PVOUT values are computed per KEK:

| Field | Definition | Use |
|-------|-----------|-----|
| `pvout_centroid` | PVOUT at the KEK centroid coordinate (lat, lon) | Reference point |
| `pvout_best_50km` | Maximum PVOUT pixel within 50km radius of centroid | **Primary: used for LCOE** |

**Rationale for `pvout_best_50km`:** A captive solar plant does not have to sit exactly at the KEK centroid — it can be sited at the best available location within 50km and power wheeled to the zone. Using the best resource within a reasonable siting radius gives a more actionable economics estimate. 50km is consistent with typical captive power project development radius in Indonesia.

**Radius calculation:** 50km in degrees is latitude-dependent. Use:
$$\Delta\phi = \frac{50}{111.32} \qquad \Delta\lambda = \frac{50}{111.32 \cdot \cos\phi}$$

where $\phi$ is the KEK centroid latitude in radians. Do not use a fixed 0.45° buffer for both axes.

**Circular mask:** The raster extraction uses a rectangular bounding box (computationally necessary for `rasterio.windows.from_bounds`). After extraction, a per-pixel haversine distance mask is applied to exclude corner pixels beyond the true 50km radius. Without this mask, corners of the bounding box would extend to ~70.7km (diagonal of 50x50 km square). The `best_solar_site_dist_km` column in `fct_kek_resource` verifies that the best buildable pixel is always within 50km.

### 2.5 Geospatial Buildability Constraints

**Core issue:** PVOUT is a resource measure — it tells you how much solar energy is available at a location. It does not tell you whether you can actually build a utility-scale solar plant there. The `pvout_best_50km` value in this model is therefore an **upper bound**. The practically achievable PVOUT is constrained by four filter layers applied in sequence:

```
Candidate zone (50km radius)
  └─ Layer 1: Hard regulatory exclusions  (Kawasan Hutan, protected areas, peat)
       └─ Layer 2: Terrain suitability     (slope, elevation, flood zones)
            └─ Layer 3: Infrastructure proximity  (road access, substation distance)
                 └─ Layer 4: Minimum contiguous area  (≥ 10 ha buildable patch)
                      └─ Buildable resource → pvout_buildable_best_50km
```

Each layer is described below with specific thresholds, rationale, and Indonesia-specific data sources.

---

#### Layer 1: Hard Regulatory Exclusions

These categories are **hard exclusions** — no utility-scale ground-mounted solar development is permissible regardless of terrain or economics.

**1a. Kawasan Hutan (Forest Estate) sub-categories:**

Indonesia designates approximately 63% of its land area as *Kawasan Hutan* under KLHK jurisdiction. Sub-categories vary in permissibility:

| Sub-category | Indonesian name | Solar permissible? | Notes |
|---|---|---|---|
| Conservation Areas | Kawasan Suaka Alam / Kawasan Pelestarian Alam | **No** — hard exclusion | Includes national parks, nature reserves, wildlife sanctuaries |
| Protection Forest | Hutan Lindung | **No** — hard exclusion | Watershed protection function prohibits clearing |
| Permanent Production Forest | Hutan Produksi Tetap (HP) | Technically possible with PPKH | Requires *Persetujuan Penggunaan Kawasan Hutan* (PPKH) permit from KLHK — multi-year process, high risk for project finance |
| Limited Production Forest | Hutan Produksi Terbatas (HPT) | Same as HP | See above |
| Convertible Production Forest | Hutan Produksi Konversi (HPK) | Possible with conversion | Requires full forest release (*pelepasan kawasan hutan*) — can take 3–5 years |

**MVP treatment:** Treat all *Kawasan Hutan* sub-categories as **excluded** (conservative). The PPKH/pelepasan pathway is not feasible for a captive solar project financed by a KEK tenant within a 3–5 year development timeline.

**1b. Presidential Instruction Moratorium Areas:**

The Inpres Moratorium (renewed through Perpres No. 5/2019) prohibits new concessions on primary natural forests and peatland, even within HPK. These overlap with but extend beyond the *Kawasan Hutan* boundary.

**1c. Peatland (Gambut):**

PP No. 57/2016 on Peatland Protection restricts development on peatland ecosystem function zones (*zona fungsi lindung*). Extensive peatlands exist in Kalimantan, Sumatra (Riau, Jambi, South Sumatra), and Papua. Solar plants are not categorically banned but financing is extremely difficult and construction on deep peat is technically challenged (subsidence, drainage). **Treat as excluded in MVP.**

**1d. Other hard exclusions (APL areas):**

Even outside *Kawasan Hutan*, certain land categories within APL (*Areal Penggunaan Lain*) are excluded:
- Water bodies (lakes, rivers, reservoirs, sea) — buffer: 500m setback from water body edge
- Mangrove ecosystems — hard exclusion under PP No. 23/2021
- Active irrigation rice fields (*sawah irigasi teknis*) — politically sensitive; excluded in practice even if legally possible
- Existing urban footprints and industrial estates — already built, no land available

**Data sources for Layer 1:**

| Dataset | Source | URL / Access | Format |
|---|---|---|---|
| Kawasan Hutan boundary | KLHK / BIG Geoportal | geoportal.menlhk.go.id | Shapefile |
| Peatland ecosystem function zones | BRG/KLHK | Perpres 57/2016 mapping | Shapefile |
| Land cover (mangrove, water, cropland, urban) | ESA WorldCover v200 2021 (10m) | esa-worldcover.s3.eu-central-1.amazonaws.com | Raster (10m, automated download) |
| Moratorium map | KLHK | Provided under Inpres / Perpres, updated periodically | Shapefile |

---

#### Layer 2: Terrain Suitability

**2a. Slope:**

| Criterion | Threshold | Basis |
|---|---|---|
| Hard exclusion | slope > 8° (14% grade) | Above this threshold, civil works costs for utility-scale PV become prohibitive; panel rows cannot be levelled without major earthworks |
| Preferred | slope ≤ 3° | Minimal earthworks required; standard row spacing assumptions valid |
| Acceptable | 3° < slope ≤ 8° | Moderate earthworks; cost adder ~10–20% on civil works |

Note: Some references cite 4–5° as the threshold for panel inter-row shading effects (relevant for fixed-tilt), but the practical development threshold for economic viability is 8°. For conservative analysis, apply **≤ 5° as the preferred threshold** and treat 5–8° as marginal.

**Data source:** Copernicus DEM 30m (GLO-30, free download) or SRTM 90m. Copernicus DEM 30m is preferred for Indonesia due to higher resolution in complex terrain. Derive slope raster using `gdaldem slope`.

**2b. Aspect (orientation):**

**Indonesia-specific:** Indonesia spans approximately 6°N to 11°S latitude — near-equatorial. At these latitudes, the sun is overhead or near-overhead for most of the year, and the optimal panel tilt angle is only 5–10°. This means:
- The energy loss on a north-facing slope vs. a south-facing slope is **much smaller** in Indonesia than at mid-latitudes (typically < 5% loss from suboptimal aspect, vs. 30–40% at 45° latitude)
- Global Solar Atlas PVOUT values already account for fixed-tilt optimal orientation in their calculation
- **Aspect is NOT a hard exclusion criterion for Indonesia** — do not apply the "south-facing only" rule used in Northern Hemisphere analyses

**Practical treatment:** No aspect filter applied. The slope filter is sufficient for terrain.

**2c. Elevation:**

| Criterion | Threshold | Rationale |
|---|---|---|
| Hard exclusion | > 1,500m above sea level | Access road construction cost becomes prohibitive; module soiling/maintenance difficult |
| Soft constraint | 500–1,500m | Note as marginal; add infrastructure cost flag |

High-elevation sites in Indonesia (Central Java volcanoes, Papua highlands, Central Sulawesi) are typically already excluded by slope and/or Kawasan Hutan filters. Elevation is a secondary check.

**2d. Flood and waterlogging zones:**

Sites in FEMA-equivalent flood zones (100-year flood plain) or areas with seasonal standing water are excluded — solar inverters and electrical infrastructure cannot be warranted in flood zones, and 25-year asset financing is not available.

**Data source:** BNPB flood hazard map (Peta Risiko Bencana) available via inarisk.bnpb.go.id; or HAND (Height Above Nearest Drainage) index derived from DEM as a proxy.

---

#### Layer 3: Infrastructure Proximity

These factors do not exclude sites but affect the economic feasibility of wheeling power from a siting location to the KEK. They are relevant because `pvout_best_50km` may point to a high-resource location that is too far from roads or substations to be economically viable.

**3a. Distance to existing road:**

| Distance | Development implication |
|---|---|
| < 5 km | Normal construction logistics; no significant cost adder |
| 5–20 km | Access road construction required (~$50,000–200,000/km in Indonesia); add to CAPEX |
| > 20 km | Material transport cost may add 10–25% to CAPEX; marginal sites only |

**Data source:** OpenStreetMap road network (osm2pgsql); or BIG's national road layer.

**3b. Distance to substation / transmission line:**

> **V2 update:** In the grid-connected solar model, substation proximity is critical for the **solar site** (not just the KEK). The IPP connects to the nearest PLN substation; PLN delivers to the KEK through its grid.

Two distance measures are relevant:
- **Solar-to-substation** (`dist_solar_to_nearest_substation_km`): determines the grid connection cost for the IPP. Shorter = cheaper connection. This drives `grid_integration_category`.
- **KEK-to-substation** (`dist_to_nearest_substation_km`): determines how well the KEK is served by PLN's existing grid. Shorter = more reliable delivery.

For **within-boundary captive solar** (plant inside KEK): no PLN substation proximity required — the plant connects directly to the KEK internal 20kV distribution network.

**Practical threshold:** See §2A.6 (Three-Point Proximity Analysis) for `grid_integration_category` thresholds. Connection cost is: `dist_solar_to_nearest_substation_km × $5/kW-km + $80/kW` (user-adjustable).

**3c. Distance to nearest water source:**

Solar plants require water for periodic panel cleaning (especially in dry-season dust conditions). Sites > 5km from a reliable water source (river, reservoir) may require water trucking, adding ~$1–3/MWh to O&M costs. Low sensitivity for Indonesia (abundant rainfall reduces cleaning frequency). **Not a hard exclusion; note as operational cost factor.**

---

#### Layer 4: Minimum Contiguous Buildable Area

After applying Layers 1–3, the remaining buildable area within the 50km radius must contain a **contiguous patch** large enough to host a meaningful captive solar project.

**Area requirements for utility-scale captive solar:**

| Project scale | Min contiguous area needed | Basis |
|---|---|---|
| 5 MWp (small KEK) | ~8–12 ha | 1.6–2.4 ha/MWp (fixed-tilt, tropical) |
| 10 MWp (typical KEK) | ~16–24 ha | LBNL: 1.13–1.70 ha/MW fixed-tilt |
| 50 MWp (large KEK) | ~80–120 ha | Same; consistent with Indonesian PLTS ground coverage |

**Note on ground coverage ratio (GCR):** At low tropical tilt angles (5–10°), rows can be placed closer together without inter-row shading, giving higher GCR (~0.45–0.55) and lower land use than temperate fixed-tilt (where GCR ~ 0.35–0.40). Use **1.5 ha/MWp** as a working estimate for Indonesia.

**Minimum viable project:** 10 ha contiguous buildable area = approximately **6–7 MWp** at Indonesian GCR. Below this, project economics are too small to justify dedicated transformer, feeder, and land acquisition overhead.

**Implementation:** Apply a morphological "opening" operation (erosion + dilation) with a 300m radius kernel to the buildable mask raster. Any remaining patches smaller than 10 ha (minimum contiguous area) are removed. The remaining patches define sitable locations; take the maximum PVOUT within these patches as `pvout_buildable_best_50km`.

---

#### Summary: Filter Hierarchy and Expected Exclusion Rates

Based on the West Kalimantan GIS study (Wijaya et al.) and Indonesia-wide land cover data, expected exclusion rates vary significantly by island:

| Region | Kawasan Hutan cover | Expected available area after all filters | Notes |
|---|---|---|---|
| Java (e.g., Kendal, Cirebon KEKs) | 15–20% | ~10–25% of 50km radius | High population density, intensive agriculture are primary constraints; slope secondary |
| Sumatra (e.g., Arun, Sungai Liat KEKs) | 40–60% | ~15–35% | Peatland and Kawasan Hutan are binding; APL areas exist but fragmented |
| Kalimantan (if any KEKs) | 55–70% | ~5–20% | Kawasan Hutan dominant; when protected areas excluded, only 34% of area is nominally available (Wijaya et al.) |
| Sulawesi (e.g., Bitung, Palu KEKs) | 60–70% | ~10–20% | Steep terrain compounds Kawasan Hutan exclusion |
| Eastern Indonesia (Papua, Maluku) | 70–80% | ~5–15% | Very high Kawasan Hutan coverage |

**Key implication for this model:** ESA WorldCover land cover (tree cover/forest + cropland + urban + water) is the numerically dominant exclusion at all 25 KEKs, removing 52–93% of raw pixels. This is expected — Indonesia has very high forest and agricultural cover. The `buildability_constraint` column is labeled `"land_cover"` for all KEKs, but peat and kawasan_hutan layers are also active and removing a meaningful share of pixels (peat: 5–39%, kawasan_hutan: 0–27% depending on site). These are confirmed active in the per-layer diagnostic output when running `run_pipeline.py fct_kek_resource`.

---

#### v1.1 Implementation Status

**v1.1 (implemented):** Layers 1a/1b/1c-d/2a/2c/4 are implemented in code and ready to run.
`fct_kek_resource` now outputs `pvout_buildable_best_50km`, `buildable_area_ha`,
`max_captive_capacity_mwp`, and `buildability_constraint`. When `data/buildability/` files
are present, `fct_lcoe` and `fct_kek_scorecard` automatically use `pvout_buildable_best_50km`
in the `grid_connected_solar` scenario; `resource_quality` is set to `"filtered"`.

**Current state (data acquisition):**
- ✅ `dem_indonesia.tif` — Copernicus DEM GLO-30, automated via `scripts/download_buildability_data.py`
- ✅ `esa_worldcover.vrt` — ESA WorldCover v200 2021, automated via `scripts/download_buildability_data.py`
- ✅ `kawasan_hutan.shp` — KLHK Kawasan Hutan (66,768 polygons, full forest estate map, Sep 2017 vintage)
- ✅ `peatland_klhk.shp` — KLHK peatland boundaries (1,524 MultiPolygon features, converted from GeoJSON via ogr2ogr)

With DEM + ESA WorldCover present, `resource_quality = "partial_filter (2/4 layers)"` (slope/elevation + land cover active). Full `"filtered"` status requires all 4 files.

**Deferred to v1.2:**
- Layer 2d (flood hazard) — BNPB portal inaccessible; low overlap with slope exclusions
- Layer 3a (road proximity) — soft constraint only; requires OSM PBF parsing

**Resolution note:** The PVOUT raster is at ~1km pixel (~86 ha/pixel). At this resolution,
Layer 4 (min contiguous area ≥ 10 ha) is a near-no-op — every valid pixel already exceeds
the 10 ha threshold. Layer 4 is retained for completeness and area counting. The exclusion
layers (1, 2) provide the primary buildability signal at 1km resolution.

**Data sources for v1.1:**

| Layer | Dataset | Source | Format | License |
|---|---|---|---|---|
| Slope / elevation (Layer 2a/2c) | Copernicus DEM GLO-30 | AWS S3 public mirror | GeoTIFF 30m → `dem_indonesia.tif` | Free, automated |
| Forest estate boundary (Layer 1a) | KLHK Kawasan Hutan (Sep 2017, 66K polygons) | geoportal.menlhk.go.id | Shapefile → `kawasan_hutan.shp` | ✅ Loaded |
| Land cover: forest, cropland, water, urban (Layer 1c/d) | ESA WorldCover v200 2021 | AWS S3 public mirror | Raster 10m → `esa_worldcover.vrt` | ✅ Automated |
| Peatland boundaries (Layer 1b) | KLHK peatland (1,524 features) | geoportal.menlhk.go.id | GeoJSON → `peatland_klhk.shp` (ogr2ogr) | ✅ Loaded |
| Flood hazard | BNPB | inarisk.bnpb.go.id | Raster | Public |
| Roads | OpenStreetMap | download.geofabrik.de/asia/indonesia | PBF/Shapefile | Open (ODbL) |

---

## 2A. Captive Solar: Legal Framework, Siting Scenarios, and PLN Connection Costs

### 2A.1 Legal Definition of Captive Power ("Kepentingan Sendiri")

Under Indonesian electricity law, "captive power" (pembangkit untuk kepentingan sendiri) is defined on an **entity/integration basis, not a distance basis**. No regulation specifies a maximum distance between the generating plant and the load it serves.

**Statutory basis:**
- **UU No. 30 Tahun 2009 tentang Ketenagalistrikan** (Electricity Law), Pasal 1: defines "kepentingan sendiri" as electricity supply for the entity's own operational needs. No spatial constraint.
- **PP No. 14 Tahun 2012 tentang Kegiatan Usaha Penyediaan Tenaga Listrik**: establishes the IUPTLS licensing regime for captive generation. Capacity threshold: generators >500 kW require an IUPTLS from MEMR (or governor for <10 MW in a single province). No distance threshold.

**Three-part qualification test** applied in practice:
1. Same legal entity owns both the generating plant and the consuming load
2. 100% of generation is dedicated to own use (no sales to third parties)
3. Plant and load are managed as a single integrated operational unit

No MEMR ruling or court decision has established a km threshold. The 50km radius used in this model's `pvout_best_50km` calculation is a siting economics constraint, not a legal limit.

### 2A.2 PLN Substation Connection — Legality and Fees

A private captive solar generator **may and in practice must** connect to the nearest PLN substation when the plant is located outside the KEK boundary or when KEK's internal distribution infrastructure is insufficient. The legal authority for this is **Permen ESDM No. 27 Tahun 2017** (grid connection standards for private generators).

**Cost structure for PLN substation connection:**

| Cost component | Formula / Range | Legal basis |
|---|---|---|
| **Gen-tie line construction** | Developer's cost; typically $3–10/kW-km × distance to nearest substation | Developer obligation; PLN typically takes ownership post-commissioning |
| **Substation works** (step-up/step-down, protection) | ~$100–200/kW | Part of interconnection study scope |
| **Parallel operation capacity charge** | Net capacity (MW) × 40 hrs × applicable PLN tariff; PLN may discount for intermittent sources (solar) | Permen ESDM No. 1 Tahun 2017 |
| **Transmission lease fee** | Negotiated with PLN, subject to MEMR approval; proportional to line distance and capacity | Permen ESDM No. 27 Tahun 2017 |
| **Standby/backup charge** | Capacity-based; charged during periods when solar is not producing | Part of parallel operation terms |

**Approval process for investors:**
1. Obtain IUPTLS from MEMR/governor (for capacity >500 kW)
2. Commission a grid interconnection study (required by PLN before any connection)
3. Negotiate gen-tie route, right-of-way, and PLN substation acceptance
4. Agree transmission lease fee (requires MEMR approval)
5. Obtain SLO (Sertifikat Laik Operasi — operational worthiness certificate)
6. Commercial operation

### 2A.3 Power Wheeling — Legally Permitted, Practically Blocked

**Permen ESDM No. 1 Tahun 2015** (kerja sama pengaliran tenaga listrik) authorises private generators to wheel power through PLN's transmission network to a load located at a different point. This would theoretically allow a solar farm at location A to supply a KEK tenant at location B via PLN infrastructure.

**Current status:** Wheeling has never been implemented in practice. PLN has rejected all wheeling requests, citing technical and operational grounds. This model does **not** assume wheeling is available as a pathway.

### 2A.4 Two Siting Scenarios

> **V2 update (April 2026):** The `remote_captive` scenario (private 50km gen-tie) has been replaced with `grid_connected_solar`. Research found no global precedent for a 50km private gen-tie for captive solar — the realistic model is IPP → PLN PPA → grid delivery. See `docs/METHODOLOGY_V2.md` for the full rationale.

This model evaluates two distinct solar configurations per KEK:

| Aspect | `within_boundary` | `grid_connected_solar` |
|---|---|---|
| **Description** | Solar plant inside KEK boundary, behind-the-meter captive | Solar farm connects to nearest PLN substation, sells to PLN via PPA |
| **PVOUT source** | `pvout_centroid` | `pvout_buildable_best_50km` |
| **Who builds it** | KEK tenant or on-site IPP | Independent IPP |
| **Who buys the power** | KEK tenant directly (no PLN) | PLN (via PPA), then PLN delivers to KEK |
| **Grid infrastructure needed** | None — internal distribution only | Solar-to-substation connection (typically <10 km) |
| **Cost to model** | Base LCOE only | Base LCOE + grid connection cost (`grid_connection_cost_per_kw(dist_km)`) |
| **PLN involvement** | None | Central — PLN is the offtaker and deliverer |

**Grid connection cost:** `dist_solar_to_nearest_substation_km` from `fct_substation_proximity.csv` drives the connection cost. Formula: `dist_km × CONNECTION_COST_PER_KW_KM + GRID_CONNECTION_FIXED_PER_KW` (USD/kW) — see `src/assumptions.py`. Connection cost is treated as additional overnight CAPEX, annualized via the same CRF as the solar plant. No transmission lease fee applies — in V2, PLN absorbs delivery cost in BPP/tariff.

**Key insight — separation of producer and consumer economics:**
1. **IPP economics**: "Can I build solar here and sell profitably to PLN?" → solar LCOE vs. regional BPP
2. **KEK tenant economics**: "What will my electricity cost from PLN?" → I-4 tariff, grid reliability, future rate trajectory
3. **Policy economics**: "Where should grid investment go to enable cheap solar?" → three-point proximity analysis

### 2A.5 Model Scope

**Current implementation computes:**
- Within-boundary LCOE using `pvout_centroid`, connection cost = 0
- Grid-connected solar LCOE using `pvout_buildable_best_50km` + `grid_connection_cost_per_kw(dist_solar_to_nearest_substation_km)`

**Output:** `fct_lcoe.csv` — 450 rows (25 KEKs × 9 WACCs × 2 scenarios). See §3.3 for the full WACC range. Scorecard uses `within_boundary` at WACC=10% as the base-case dashboard comparator.

**Regulatory sources:**
- UU No. 30 Tahun 2009 (Ketenagalistrikan)
- PP No. 14 Tahun 2012 (Kegiatan Usaha Penyediaan Tenaga Listrik)
- Permen ESDM No. 1 Tahun 2015 (Kerja Sama Pengaliran Tenaga Listrik)
- Permen ESDM No. 1 Tahun 2017 (Persyaratan Teknik Penyambungan ke Sistem Tenaga Listrik)
- Permen ESDM No. 27 Tahun 2017 (Tingkat Mutu Pelayanan dan Biaya yang Terkait dengan Penyaluran Tenaga Listrik)
- Permen ESDM No. 11 Tahun 2021 (Pelaksanaan Kegiatan Usaha Penyediaan Tenaga Listrik)

### 2A.6 Three-Point Proximity Analysis

V1 measured one distance: KEK centroid to nearest PLN substation. V2 introduces a **three-point proximity model** that captures the full solar-to-grid-to-KEK chain.

**Three geographic points:**

| Point | Source | Description |
|---|---|---|
| **A** — Best solar site | `fct_kek_resource` (`best_solar_site_lat`, `best_solar_site_lon`) | Location of the highest-PVOUT buildable pixel within 50 km of the KEK |
| **B** — Nearest PLN substation | `data/substation.geojson` | Nearest operational PLN substation to point A or C (may differ) |
| **C** — KEK centroid | `dim_kek` | Geographic center of the KEK polygon |

**Distance matrix:** For each KEK, compute:
- **d(A, B_solar)**: distance from best solar site to the nearest substation (`dist_solar_to_nearest_substation_km`)
- **d(C, B_kek)**: distance from KEK centroid to the nearest substation (`dist_to_nearest_substation_km`)

**Grid integration categories:**

| Category | Condition | Meaning |
|---|---|---|
| `within_boundary` | Has operational substation inside KEK polygon | Solar can be built on-site, no grid needed |
| `grid_ready` | d(A, B_solar) < 10 km AND d(C, B_kek) < 15 km | Substation near both solar and KEK — grid can absorb and deliver |
| `invest_grid` | One or more distance conditions fail, but solar resource is viable | Targeted infrastructure investment (line segment, substation upgrade) unlocks solar |
| `grid_first` | Both distances > thresholds AND no nearby substations | Major grid expansion needed before solar is relevant |

**Threshold values** (user-adjustable via `src/assumptions.py`):
- `SOLAR_TO_SUBSTATION_LOW_THRESHOLD_KM` = 10.0 km (range: 5–20 km)
- `KEK_TO_SUBSTATION_LOW_THRESHOLD_KM` = 15.0 km (range: 5–30 km)

**Resolution limitation:** Solar site coordinates are from the ~1 km resolution Global Solar Atlas GeoTIFF, accurate to approximately ±500 m. Sufficient for screening-level substation proximity analysis.

**Implementation:** `grid_integration_category()` in `src/model/basic_model.py`; proximity pipeline in `src/pipeline/build_fct_substation_proximity.py`.

---

## 2B. Wind Resource: Capacity Factor from Wind Speed

### 2B.1 Input data

**Source:** Global Wind Atlas v3 (DTU / World Bank), long-term average
**Layer used:** Mean annual wind speed at 100m hub height
**Native unit:** m/s

### 2B.2 Wind speed extraction per KEK

Same 50km radius methodology as solar PVOUT (Section 2.4). Two values per KEK:

| Field | Definition | Use |
|-------|-----------|-----|
| `wind_speed_centroid_ms` | Wind speed at KEK centroid | Reference |
| `wind_speed_best_50km_ms` | Maximum wind speed pixel within 50km | **Primary: used for wind LCOE** |

**Implementation:** `src/pipeline/build_fct_kek_wind_resource.py`

### 2B.3 Wind capacity factor

Wind speed is converted to capacity factor using an empirical piecewise-linear approximation calibrated to Indonesian conditions:

| Wind speed (m/s) | CF | Context |
|---|---|---|
| $\leq$ 3.0 | 0.00 | Below cut-in, no generation |
| 4.0 | 0.08 | Marginal, near cut-in |
| 5.0 | 0.15 | Low wind |
| 6.0 | 0.22 | Moderate (ESDM lower range) |
| 7.5 | 0.27 | ESDM catalogue central CF for best Indonesian sites |
| 8.5 | 0.32 | IEC Class II/III boundary |
| 10.0 | 0.38 | IEC Class I, excellent |
| $\geq$ 12.0 | 0.42 | Plateau (turbine at rated power) |

**Reference turbine:** Vestas V126/3.45 MW (IEC Class III, low-wind design). Calibrated to ESDM Technology Catalogue 2024, p.90.

**Implementation:** `wind_speed_to_cf()` in `src/model/basic_model.py`; linear interpolation between breakpoints.

### 2B.4 Wind LCOE

Wind LCOE uses the same CRF annuity formula as solar (Section 3.1), with wind-specific technology parameters from `dim_tech_cost_wind`:

| Parameter | Value | Source |
|-----------|-------|--------|
| CAPEX | from ESDM TECH_WIND_ONSHORE | `src/pipeline/build_dim_tech_cost_wind.py` |
| FOM | from ESDM TECH_WIND_ONSHORE | Same |
| Lifetime | from ESDM TECH_WIND_ONSHORE | Same |

**Implementation:** `src/pipeline/build_fct_lcoe_wind.py`

### 2B.5 Best RE technology selection

The scorecard compares solar LCOE and wind LCOE per KEK at the user's selected WACC. The cheaper technology is stored as `best_re_technology` (`"solar"` or `"wind"`) with corresponding `lcoe_best_re_usd_mwh`. This drives the dashboard's competitive gap and action flag calculations when `energyMode = "overall"`.

**Energy mode** (user-selectable in dashboard):

| Mode | Behavior |
|------|----------|
| `solar` | Show solar LCOE and flags only |
| `wind` | Show wind LCOE and flags only |
| `overall` | Use `best_re_technology` (cheaper of solar vs wind per KEK) |

---

## 3. Levelized Cost of Energy (LCOE)

### 3.1 Formula

The LCOE for utility-scale solar PV is computed using the annuity method (standard capital recovery factor approach):

$$CRF(r, n) = \frac{r \cdot (1 + r)^n}{(1 + r)^n - 1}$$

$$LCOE = \frac{CAPEX \cdot CRF + FOM}{CF \times 8.76} \quad [\text{USD/MWh}]$$

Where:
- $CAPEX$ = capital expenditure [USD/kW]
- $FOM$ = fixed operations and maintenance cost [USD/kW/yr]
- $r$ = weighted average cost of capital (WACC) [decimal, e.g. 0.10 for 10%]
- $n$ = project lifetime [years]
- $CF$ = capacity factor [decimal]
- $8.76 = 8{,}760 \div 1{,}000$ (unit conversion: hours/year to MWh/kW/yr)

**Derivation:**
- $CAPEX \times CRF$ = annualized capital cost per kW [USD/kW/yr]
- $CAPEX \times CRF + FOM$ = total annual cost per kW [USD/kW/yr]
- $CF \times 8.76$ = annual energy production per kW [MWh/kW/yr]
- Ratio = cost per unit of energy [USD/MWh]

### 3.2 Technology parameters (TECH006 — utility-scale solar PV)

**Source:** ESDM Technology Catalogue (Indonesia Ministry of Energy), parsed into `data/fct_tech_parameter.csv`

✅ **TECH006 parameters verified from PDF** (`docs/esdm_technology_cost.pdf`, page 66). Extracted by `src/pipeline/pdf_extract_esdm_tech.py`, with hardcoded fallback in `VERIFIED_TECH006_DATA`. `is_capex_provisional=False` across all LCOE and scorecard rows.

| Parameter | Verified value | Unit | Source |
|-----------|---------------|------|--------|
| CAPEX (central) | 960 | USD/kW | ESDM Technology Catalogue 2023, p.66 (0.96 MUSD/MWe × 1000) |
| CAPEX (lower) | 840 | USD/kW | ESDM p.66 (0.84 MUSD/MWe × 1000) |
| CAPEX (upper) | 1,080 | USD/kW | ESDM p.66 (1.08 MUSD/MWe × 1000) |
| FOM (central) | 7.5 | USD/kW/yr | ESDM p.66 (7,500 USD/MWe/yr ÷ 1000) |
| Lifetime | 27 | years | ESDM p.66 (central value) |

**Unit conversion required:** The Technology Catalogue stores CAPEX in MUSD/MWe (millions USD per MW electric). Convert to USD/kW:

$$CAPEX_{\text{USD/kW}} = CAPEX_{\text{MUSD/MWe}} \times 1{,}000$$

(1 MUSD/MWe = 1,000,000 USD / 1,000 kW = 1,000 USD/kW)

Add assertion: `assert 200 < CAPEX < 3000` to catch unit errors.

### 3.3 WACC

The WACC is the primary user-adjustable parameter in the dashboard (slider: 4–20%, default: 10%).

**Default 10% rationale:** ADB's benchmark weighted average cost of capital for renewable energy projects in Southeast Asia is approximately 8–12%. 10% is the midpoint and a common assumption in development bank screening models. The user can adjust to match their fund's actual hurdle rate.

**WACC=8% de-risked scenario:** The scorecard precomputes a static WACC=8% column (`lcoe_mid_wacc8_usd_mwh`, `solar_competitive_gap_wacc8_pct`, `solar_now_at_wacc8`) alongside the WACC=10% base case. At WACC=8%, **8 KEKs flip to solar-competitive** (vs. 0 at WACC=10%). This answers the DFI question "what financing de-risking is needed?" — if a green finance facility, concessional loan, or first-loss guarantee can bring a project's effective WACC from 10% to 8%, solar wins for those 8 KEKs without any change in the underlying resource or technology cost.

**Precomputed snap range (✅ implemented):** `fct_lcoe` precomputes LCOE at 9 WACC values: `[4, 6, 8, 10, 12, 14, 16, 18, 20]` (2% steps). This covers the full spectrum from DFI concessional blended finance (4–6%, e.g. IFC, AIIB, DFC facility rates) through commercial project finance (8–12%) to private equity scenarios (14–20%). No hard cap in code — `WACC_VALUES` in `src/assumptions.py` is a list. The `fct_lcoe` table is 25 KEKs × 9 WACC snaps × 2 scenarios = 450 rows.

**Edge cases:**
- `wacc = 0`: clamp to 0.01 (1%) to avoid division by zero in CRF. Show warning in UI.
- `CF = 0`: return `NaN` (no PVOUT data for this KEK). Show "unavailable" in UI.

### 3.4 LCOE bands

Three LCOE values are computed per KEK per WACC assumption:

| Field | CAPEX input | Interpretation |
|-------|------------|----------------|
| `lcoe_low` | CAPEX_lower (optimistic) | Best-case economics |
| `lcoe_mid` | CAPEX_central (base case) | **Primary value used in all comparisons** |
| `lcoe_high` | CAPEX_upper (conservative) | Worst-case economics |

All three use the same FOM, lifetime, WACC, and `cf_best_50km`.

---

## 4. Grid Cost Reference

### 4.1 What is being compared

The LCOE is compared against the **cost of grid-supplied electricity** to a KEK industrial tenant. Two candidate metrics:

| Metric | Definition | Source | Status |
|--------|-----------|--------|--------|
| PLN BPP Pembangkitan | PLN's generation cost of supply by grid system | Kepmen ESDM 169/2021 (FY2020) | ✅ `bpp_usd_mwh` populated for all 7 grid regions via `pdf_extract_bpp.py` |
| I-4 industrial tariff | Tariff paid by large industrial consumers (≥30,000 kVA) | Permen ESDM No. 7 Tahun 2024 | ✅ implemented — $63.08/MWh, uniform nationwide |
| I-3 industrial tariff | Tariff paid by medium industrial consumers (200–30,000 kVA) | Permen ESDM No. 7 Tahun 2024 | ✅ implemented — $65.57/MWh, uniform nationwide |

**Critical distinction:** PLN BPP Pembangkitan is PLN's *generation cost of supply*, not the tariff a KEK tenant actually pays. Industrial tariffs (Golongan I-3/I-4) are set by ESDM and may be 15–35% below BPP due to cross-subsidy policy. The model carries both: I-4/TT tariff as primary comparator (what tenants pay) and BPP as secondary reference (what electricity actually costs PLN to generate). BPP is sourced from Kepmen ESDM 169/2021 (FY2020, valid until superseded). Note: this is generation BPP only, not full cost-of-supply BPP which includes T&D + overhead (~1,599 Rp/kWh per BPK audit).

**Methodology decision (RESOLVED):**
- `dashboard_rate_usd_mwh` = I-4/TT tariff ($63.08/MWh) — the correct primary comparator for large industrial KEK tenants. Flagged `OFFICIAL` in `fct_grid_cost_proxy`.
- I-3/TM ($65.57/MWh) is stored as `tariff_i3_usd_mwh` — available for smaller tenant analysis.
- Both tariffs are **uniform nationwide** (Permen ESDM No. 7/2024, Lampiran IV). No regional variation.
- BPP Pembangkitan is now populated from Kepmen ESDM 169/2021 (FY2020). `bpp_usd_mwh` ranges from ~$57/MWh (Java-Bali) to ~$133/MWh (Papua). BPP is generation cost only, not full cost-of-supply.

### 4.3 Benchmark mode (user-selectable)

The dashboard provides a toggle between two grid cost comparators:

| Mode | Comparator | Use case |
|------|-----------|----------|
| **Tariff** (default) | I-4/TT ($63.08/MWh, uniform) | "Can a KEK tenant save money vs. their electricity bill?" |
| **BPP** | Regional BPP Pembangkitan ($57–133/MWh) | "Is captive solar cheaper than what it actually costs PLN to generate?" |

When benchmark mode is set to BPP, the competitive gap, action flags, and carbon breakeven are all recomputed using `bpp_usd_mwh` instead of the I-4 tariff. This dramatically changes results: at BPP, eastern Indonesia KEKs (Papua, NTB, Kalimantan) with high BPP become solar-competitive even at WACC=10%, while Java-Bali KEKs (low BPP ~$57/MWh) become harder to flip.

**Implementation:** `POST /api/scorecard` accepts `benchmark_mode: "bpp" | "tariff"`. Backend conditionally substitutes `bpp_usd_mwh` for `dashboard_rate_usd_mwh` before recomputing.

### 4.2 Coverage by PLN grid system

Grid costs are at PLN **system level** (e.g., Sistem Jawa-Bali, Sistem Sumatera), not at KEK level. Each KEK inherits the grid cost of the system it belongs to, via the `grid_region_id` join.

✅ `data/kek_grid_region_mapping.csv` exists — 26 rows mapping all 25 KEKs to their PLN grid system (`grid_region_id`), province, and `reliability_req`. Created manually via KEK address data and PLN system boundary maps. Maintained as a lookup table; update if a KEK's grid connection changes.

---

## 5. Competitiveness Metrics and Action Flags

### 5.1 Solar competitive gap

$$\text{solar\_competitive\_gap} = \frac{LCOE_{\text{mid}} - C_{\text{grid}}}{C_{\text{grid}}} \times 100\%$$

Where $C_{\text{grid}}$ = `dashboard_rate_usd_mwh` from `fct_grid_cost_proxy`.

**Interpretation:**
- **Negative gap:** Solar LCOE < grid cost → solar is already cheaper at this WACC
- **Positive gap:** Solar LCOE > grid cost → grid is cheaper by this percentage
- **Example:** gap = −12% → solar is 12% cheaper than grid; gap = +20% → grid is 20% cheaper than solar

**Edge cases:**
- `grid_cost = 0` or `NaN`: return `NaN`
- `lcoe_mid = NaN` (PVOUT unavailable): return `NaN`

### 5.2 Action flags

> **V2 update:** Flags reframed around grid-solar integration. `invest_grid` added. `invest_resilience` retained. Priority order updated.

Seven mutually-ordered flags. A KEK receives the first flag for which its conditions are satisfied:

| Flag | Conditions | Interpretation |
|------|-----------|----------------|
| `solar_now` | `grid_ready` category AND solar LCOE < grid cost AND PVOUT ≥ threshold | Grid infrastructure in place, solar economics favorable — IPP can build now |
| `invest_grid` | `invest_grid` category AND solar resource viable (PVOUT ≥ threshold) | Solar resource exists but grid connection is the bottleneck — targeted infrastructure investment unlocks solar |
| `grid_first` | `grid_first` category | No grid infrastructure near solar or KEK — major grid expansion needed |
| `invest_resilience` | `0 < solar_competitive_gap_pct ≤ 20 AND reliability_req ≥ 0.75` | Solar near grid parity + high reliability needs — investment case rests on energy security |
| `firming_needed` | `solar_attractive AND reliability_req ≥ 0.75` | Solar economics work but zone needs high reliability — add storage/firming |
| `plan_late` | `post2030_share ≥ 0.60` | >60% of RUPTL additions for this region are planned post-2030 — pipeline is late |
| `not_competitive` | None of the above | Solar LCOE exceeds grid cost under current assumptions |

**`not_competitive` fallback:** If all data is present but no flag fires, the KEK is labelled `not_competitive`. At WACC=10%, with correct TECH006 CAPEX ($960/kW), most Indonesian KEKs fall here — the model correctly reports that solar is not yet at grid parity for the average KEK under these assumptions.

### 5.2b Resilience layer (`invest_resilience`)

**Why it matters:** The `not_competitive` label captures only tariff economics — it answers "is solar cheaper than grid electricity?" But for manufacturing KEKs, the electricity bill is not the only cost at stake. Unplanned outages cost orders of magnitude more than the electricity itself: an automotive assembly line losing power for one hour can lose $500,000–$2M in scrapped production and restart costs. Captive solar (with backup) eliminates this tail risk. The `invest_resilience` flag surfaces KEKs where the investment case is real *even before* solar reaches price parity.

The `invest_resilience` flag captures scenarios where the investment case for captive solar rests on **energy security and reliability**, not tariff savings.

**Rationale for each threshold:**

| Condition | Value | Why this number |
|-----------|-------|----------------|
| `solar_competitive_gap_pct > 0` | — | Solar must not already be cheaper (that's `solar_now`) |
| `solar_competitive_gap_pct ≤ 20%` | 20% | At grid $63/MWh, this is a ~$12.6/MWh premium. Manufacturing KEKs face unplanned outage costs of $50–$200/MWh of lost production — far exceeding the $12.6 premium. 20% is the upper bound where resilience economics hold. |
| `reliability_req ≥ 0.75` | 0.75 | Manufacturing/processing sectors (steel, chemicals, automotive) that cannot tolerate outages. Tourism and services (below 0.75) can tolerate interruptions — their outage cost does not justify a premium. |

**`reliability_req` values by KEK type** (set in `data/kek_grid_region_mapping.csv`):
- Manufacturing/processing: 0.8–0.85 → `invest_resilience` eligible
- Service/digital: 0.6 → not eligible
- Tourism: 0.4 → not eligible

**Formula:**

$$\text{invest\_resilience} = \bigl(0 < \text{gap}_\% \leq 20\bigr) \;\wedge\; \bigl(\text{reliability\_req} \geq 0.75\bigr)$$

**Constant:** `RESILIENCE_LCOE_GAP_THRESHOLD_PCT = 20.0` (src/assumptions.py)
**Implementation:** `invest_resilience()` in `src/model/basic_model.py`

**Current results (WACC=10%):** 4 KEKs fire this flag — Kendal (gap=13.0%), Gresik (14.2%), Batang (14.6%), Bitung (17.4%). All are manufacturing KEKs in Java-Bali and Sulawesi. Carbon breakeven for these: $10–17/tCO2 — well within Indonesia's emerging carbon market trajectory.

**`solar_attractive` definition (✅ resolved — Option B implemented):**

$$\text{solar\_attractive} = \bigl(\text{PVOUT}_{\text{best50km}} \geq 1{,}550\bigr) \;\wedge\; \bigl(LCOE_{\text{mid}} \leq C_{\text{grid}}\bigr)$$

WACC-dependent: `solar_attractive` means "solar LCOE ≤ grid cost at current WACC AND resource is sufficient." This makes the flag directly interpretable — no hardcoded LCOE threshold needed. Implementation: `is_solar_attractive()` in `src/model/basic_model.py`.

**NaN handling:** If any input to an action flag computation is NaN:
- Use conservative defaults: `grid_upgrade_pre2030 = False`, `post2030_share = 1.0` (assumes worst case)
- Mark the KEK as `data_completeness = "provisional"` in the scorecard
- Do not silently apply defaults without flagging them

### 5.3 GEAS green share

**Why it matters:** GEAS (Green Energy Auction Scheme) is Indonesia's only legal mechanism for industrial buyers to claim grid-sourced renewable electricity — there is no bilateral corporate PPA market yet. `green_share_geas` answers: *"What fraction of this KEK's 2030 electricity demand could be covered by RUPTL-planned solar through the GEAS mechanism?"* This makes GEAS and captive solar **substitutes** — the dashboard uses `green_share_geas` to determine which lever a KEK needs:

| `green_share_geas` | What it means | Dashboard implication |
|--------------------|-------------|----------------------|
| ≥ 0.30 (30%) + solar competitive | GEAS supply is adequate AND solar wins on cost | `solar_now` flag fires — go solar |
| ≥ 0.30 but solar not competitive | Grid will deliver enough green energy without on-site solar | GEAS alone may satisfy tenant ESG requirements — captive solar not urgent |
| < 0.30 | RUPTL pipeline is too thin to cover industrial demand in this region | Captive solar is the only path to renewable coverage for tenants |

**For DFI Analysts (ADB, IFC, AIIB):** Green finance conditions (IFC Performance Standards, ADB Green Bond criteria) often require a minimum renewable energy share. High `green_share_geas` means those conditions can be met via GEAS offtake — no captive solar project required. Low `green_share_geas` strengthens the bankability case for an on-site captive solar project, which is what DFIs are typically financing.

**For Energy Policy Advisers (ESDM, BAPPENAS):** KEKs with low `green_share_geas` in regions with a weak RUPTL pipeline signal a planning gap — the grid won't deliver enough green energy for industrial demand by 2030. These are the zones that need captive solar policy support (streamlined permitting, BOOT structures, green industrial zone designation), not ones where GEAS will do the job automatically.

GEAS (Green Energy Auction Scheme) allocates renewable energy from RUPTL-planned solar additions to industrial zones on a pro-rata basis.

**Baseline allocation (proportional to demand):**

$$\text{GEAS}_{\text{alloc}}^{i} = E_{\text{green}}^{r} \times \frac{D^{i}}{D^{r}_{\text{total}}}$$

$$\text{green\_share}^{i} = \min\!\left(1,\;\frac{\text{GEAS}_{\text{alloc}}^{i}}{D^{i}}\right)$$

Where $E_{\text{green}}^{r} = \text{pre2030\_solar\_MW}^{r} \times 8{,}760 \times CF_r$ and $CF_r = 0.20$ (system-level assumption for RUPTL-planned solar).

**Policy scenario allocation (proportional to demand $\times$ PVOUT):**

$$w^{i} = D^{i} \times \text{PVOUT}_{\text{best50km}}^{i}$$

$$\text{GEAS}_{\text{policy}}^{i} = E_{\text{green,policy}}^{r} \times \frac{w^{i}}{\sum_{j \in r} w^{j}}$$

This prioritizes zones with both high demand and high solar resource.

### 5.3b Carbon breakeven price

The carbon breakeven price answers the policy question: **"At what carbon price does solar become cost-competitive with the grid?"**

**Formula:**

$$P_{\text{carbon}} = \begin{cases} 0 & \text{if } LCOE_{\text{mid}} \leq C_{\text{grid}} \\ \displaystyle\frac{LCOE_{\text{mid}} - C_{\text{grid}}}{EF_{\text{grid}}} & \text{otherwise} \end{cases} \quad [\text{USD/tCO}_2]$$

Interpretation: if carbon is priced at or above $P_{\text{carbon}}$ (via Indonesia's carbon market, EU CBAM exposure, or corporate net-zero commitments), solar wins on adjusted total cost.

**Simplification note:** This formula assumes zero lifecycle emissions from solar. Actual solar lifecycle emissions are ~40 gCO2/MWh (IPCC AR6 median, covering manufacturing, transport, installation, and decommissioning). The corrected formula would be `lcoe_gap / (grid_EF − 0.040)`, which raises breakeven prices by ~5–8% depending on the grid region. This simplification is standard for grid displacement calculations but should be noted when citing breakeven values in formal analysis.

**Grid emission factors by PLN system (Operating Margin, ⚠️ 2019 vintage):**

The Operating Margin (OM) is the correct metric here: it represents the emission intensity of **existing grid plants that captive solar displaces**, not the build margin.

| Grid Region | KEK(s) | OM (tCO2/MWh) | PLN System | Plants | Source |
|------------|--------|--------------|------------|--------|--------|
| JAVA_BALI | Batang, Kendal, Gresik, Lido, Singhasari, Kura-Kura, Sanur, Tanjung Lesung, BSD, Bumi Serpong | 0.80 | Java-Bali interconnected | 302 | KESDM 2019 |
| SUMATERA | Sei Mangkei, Arun, Galang Batang, Nongsa, BAT, Tanjung Kelayang, Batam-int'l, Tanjung Sauh | 0.77 | Sumatera interconnected | 463 | KESDM 2019 |
| KALIMANTAN | Setangga (Barito 1.20), Maloy Batuta (Mahakam 1.12) | 1.16 (avg) | Barito + Mahakam | 121+97 | KESDM 2019 |
| SULAWESI | Likupang, Bitung (Sulutgo 0.67), Palu (Palapas 0.54) | 0.63 (wtd avg) | Sulutgo + Palapas-Palu | 73+10 | KESDM 2019 |
| NTB | Mandalika | 1.27 | Lombok grid | 54 | KESDM 2019 |
| MALUKU | Morotai | 0.60 | Daruba-Morotai | 12 | KESDM 2019 |
| PAPUA | Sorong | 0.56 | Sorong | 11 | KESDM 2019 |

Source: KESDM Tier 2 grid emission factor database, 2019 vintage (`data/grid_emission_factors.xlsx`, gatrik.esdm.go.id). File: `src/assumptions.py → GRID_EMISSION_FACTOR_T_CO2_MWH`. **⚠️ These factors are now 7 years old (2019 vintage, as of April 2026).** Indonesia's grid mix has shifted since then (increased coal share in some regions, new gas and RE additions). Updated KESDM Tier 2 factors should be substituted when published.

**Policy implications of corrected values:**
- Kalimantan (OM=1.16) has the highest emission intensity — solar displaces the most carbon per MWh, bringing breakeven carbon prices down to ~$16–17/tCO2 even at 30%+ LCOE premium.
- Mandalika/NTB (OM=1.27) has the most diesel-dependent grid — carbon breakeven only $3.4/tCO2, making any credible carbon pricing sufficient to flip the economics.
- Sorong/Papua (OM=0.56) is gas-dominant — carbon breakeven is $29/tCO2, requiring stronger policy signals.

**Implementation:** `carbon_breakeven_price()` in `src/model/basic_model.py`; emission factors in `GRID_EMISSION_FACTOR_T_CO2_MWH` (src/assumptions.py).

### 5.4 Flip scenario

The flip scenario identifies KEKs that are close to solar-competitive:

$$\text{flip\_candidates} = \bigl\{k \;\big|\; 0 < \text{gap}_k \leq \tau_{\text{flip}}\bigr\}$$

Where $\tau_{\text{flip}}$ is user-adjustable (default 20%). These are zones where solar is not yet competitive but is within $\tau_{\text{flip}}\%$, meaning a modest policy intervention (CAPEX reduction via GBT program, lower WACC, or tariff adjustment) could make it competitive.

### 5.5 Grid-connected solar cost model

> **V2 update:** Replaces §5.5 "All-in captive solar cost." The transmission lease fee is removed — in the V2 model, PLN delivers power through its grid at system cost (reflected in BPP/tariff). The only cost adder is the grid connection from the solar site to the nearest PLN substation.

**Grid connection cost (grid_connected_solar scenario):**

$$C_{\text{connection}} = d_{\text{solar→sub}} \times C_{\text{per\_kw\_km}} + C_{\text{fixed}}$$

| Parameter | Default | Range | What it covers |
|---|---|---|---|
| `CONNECTION_COST_PER_KW_KM` | $5/kW-km | $2–15/kW-km | Line from solar plant to PLN substation |
| `GRID_CONNECTION_FIXED_PER_KW` | $80/kW | $30–200/kW | Switchgear, protection, metering at the PLN substation |

**Grid-connected solar LCOE:**

$$LCOE_{\text{gc}} = \frac{(CAPEX + C_{\text{connection}}) \times CRF + FOM}{CF \times 8.76}$$

Where CF uses `pvout_buildable_best_50km` and distance uses `dist_solar_to_nearest_substation_km`.

Implemented columns (`fct_lcoe` and scorecard): `lcoe_grid_connected_usd_mwh` (+low/high), `connection_cost_per_kw`.

**Firming adder (within_boundary, partially modelled):**
On-site captive plants may still need grid backup for intermittency. This is the `lcoe_solar_with_firming()` function in `basic_model.py` (adder: +$6/+$11/+$16/MWh low/mid/high). Not currently surfaced as a dedicated scorecard column.

**Primary metric:** The competitive gap uses `lcoe_mid_usd_mwh` (`within_boundary`) as the primary comparator. `lcoe_grid_connected_usd_mwh` shows the IPP's grid-connected solar economics.

### 5.6 DFI Grid Infrastructure Investment Model

Development Finance Institutions (ADB, World Bank, IFC, AIIB) regularly finance grid infrastructure in developing countries. The dashboard identifies WHERE grid investment unlocks the most solar potential — the `invest_grid` category is the DFI opportunity set.

**Investment instruments:**

| Instrument | How it works | Dashboard relevance |
|---|---|---|
| **Concessional loan to PLN** | DFI lends at below-market rates for transmission/substation | `invest_grid` KEKs show where PLN needs grid investment |
| **Viability gap funding** | DFI covers gap between infrastructure cost and recoverable tariff | Grid investment estimate sizes the gap |
| **Blended finance** | DFI funds grid, private IPP funds solar, PLN operates | `solar_now` + `invest_grid` KEKs are co-investment opportunities |
| **Green bonds** | PLN issues bonds for grid investment, DFI provides credit enhancement | Regional aggregation of `invest_grid` KEKs sizes the bond |

**Grid investment estimation** (screening-level, for `invest_grid` KEKs):

$$I_{\text{grid}} = d_{\text{gap}} \times C_{\text{transmission/km}} + N_{\text{substations}} \times C_{\text{substation}}$$

Where $C_{\text{transmission/km}} \approx$ $500K–1M/km for 150 kV in Indonesia, and $C_{\text{substation}} \approx$ $5–15M per 150/20 kV step-down. This is a screening estimate to help DFIs identify cost-effective grid investment opportunities relative to solar potential unlocked.

---

## 6. Known Limitations and Caveats

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| PVOUT from Global Solar Atlas, not site-specific measurement | ±5–10% LCOE uncertainty | Use `pvout_best_50km` not centroid; show LCOE band (low/mid/high) |
| ~~Buildability filter is partial (2/4 layers with automated data)~~ | ~~`pvout_buildable_best_50km` may overstate buildable resource~~ | ✅ Resolved — all 4 buildability layers now active (Kawasan Hutan, peatland, ESA WorldCover, DEM slope/elevation). `resource_quality = "filtered"` when all files present. 7/25 KEKs show zero buildable area due to kawasan hutan overlap. Flood hazard (Layer 2d) and road proximity (Layer 3a) deferred to v1.2. |
| Panel degradation not modeled | CRF annuity method assumes constant annual production. Solar panels degrade ~0.5%/yr; by year 27, output is ~87% of year 1. LCOE is understated by ~6–7% | Standard for screening-level models (IEA, IRENA use same simplification). For project-level analysis, apply degradation-adjusted CF = CF × (1 − 0.5% × n/2) |
| Solar lifecycle emissions excluded from carbon breakeven | `carbon_breakeven_usd_tco2` assumes zero solar emissions. Actual lifecycle: ~40 gCO2/MWh (IPCC AR6 median). Breakeven prices are ~5–8% too optimistic | Add footnote to carbon breakeven output; corrected formula: `gap / (grid_EF − 0.040)` |
| ~~IDR/USD exchange rate hardcoded (15,800)~~ | ~~No FX sensitivity~~ | ✅ Resolved — IDR/USD rate is now a user-adjustable Tier 2 slider (range: 14,000–18,000, default: 15,800). Changes affect grid tariff conversion and all downstream comparisons. |
| ~~Grid cost proxy may be BPP, not actual industrial tariff~~ | ~~LCOE gap overstated if BPP > tariff~~ | ✅ Resolved — I-4/TT tariff is primary comparator; BPP Pembangkitan (Kepmen ESDM 169/2021) now populated as secondary reference |
| LCOE excludes firming costs (within_boundary) | On-site all-in cost understated by ~$6–16/MWh for intermittency backup | `lcoe_solar_with_firming()` in `basic_model.py`; not yet a dedicated scorecard column |
| ~~LCOE excludes transmission lease (remote_captive)~~ | ~~All-in PPA cost understated for 23/25 KEKs~~ | ✅ Resolved (V2) — transmission lease removed. Grid-connected solar uses connection cost only; PLN delivers at system cost (in BPP/tariff). |
| Grid-connected solar requires PLN partnership | PLN controls procurement; scenario assumes PLN is willing to procure solar | Dashboard reads as "if solar procurement is enabled, here are the economics." Within-boundary remains PLN-independent. |
| Connection costs are highly site-specific | Terrain, land acquisition, permitting vary enormously across 25 KEKs | Connection cost parameters are user-adjustable with wide ranges ($2–15/kW-km, $30–200/kW fixed) |
| KEK demand figures not available (using RUPTL region-level data) | GEAS allocation is approximate | Label `green_share_geas` as indicative, not contractual |
| RUPTL capacity additions are planned, not committed | `grid_upgrade_pre2030` and `plan_late` flags may change | Vintage-stamp RUPTL data; re-run on new RUPTL releases |
| No reliability data (SAIDI/SAIFI) | Cannot quantify reliability premium for captive solar | Deferred to v2 when PLN data is available |
| ~~No wind or geothermal in base model~~ | ~~Understates clean power options~~ | ✅ Resolved — onshore wind fully implemented (Section 2B). Wind LCOE computed per KEK using Global Wind Atlas v3. `best_re_technology` selects cheaper of solar vs wind. Geothermal remains deferred. |
| CAPEX from ESDM catalogue, not Indonesia-specific market data | Actual Indonesian solar CAPEX may vary ±15–20% from catalogue | Show CAPEX sensitivity (low/mid/high) in LCOE bands |

---

## 7. Assumptions Summary

| Assumption | Value | Rationale | Sensitivity |
|-----------|-------|-----------|-------------|
| Default WACC | 10% | ADB benchmark for SEA renewable energy | Precomputed snaps: 4–20% (2% steps); dashboard slider: 4–20% |
| Grid connection cost | $5/kW-km + $80/kW fixed | Solar-to-substation connection (V2 model) | User-adjustable: $2–15/kW-km, $30–200/kW fixed |
| PVOUT siting radius | 50 km | Typical captive power siting radius in Indonesia | Fixed in MVP |
| Regional solar CF (GEAS) | 20% | Representative for RUPTL-planned utility solar in Indonesia | Low sensitivity |
| RUPTL GEAS baseline allocation | Pro-rata to demand | Simplest defensible allocation; no preferential treatment | Policy scenario uses demand × PVOUT |
| `plan_late` threshold | post2030_share ≥ 60% | Majority of regional additions post-2030 = late pipeline | Could be 50% or 70%; low sensitivity on flag count |
| `firming_needed` / `invest_resilience` reliability threshold | reliability_req ≥ 0.75 | Manufacturing/processing KEKs per sector classification in `kek_grid_region_mapping.csv` (Manufacturing=0.8, Service=0.6, Tourism=0.4). Threshold operationalized; stakeholder validation recommended for v2. | |
| PVOUT plausibility bounds | 1,000–2,500 kWh/kWp/yr | Indonesia solar range from Global Solar Atlas | Used for data validation, not analysis |
| Buildable land (≥ 10 ha contiguous, slope ≤ 8°, outside Kawasan Hutan / peat / flood zones) assumed to exist within 50km radius | MVP simplification — risk is highest for Java KEKs (dense agriculture) and Sulawesi KEKs (Kawasan Hutan + steep terrain); outer Sumatra KEKs are generally lower risk | `pvout_best_50km` labeled `provisional`; v1.1 applies 4-layer filter (Section 2.5) to compute `pvout_buildable_best_50km` and `buildable_area_ha` |
| Land use for captive solar assumed compliant with RTRW spatial plan | Local spatial plans (RTRW kabupaten/provinsi) may designate specific zones for industrial vs. agricultural use; solar on APL land is generally permissible but RTRW compliance must be verified per KEK by the developer | Not modeled; flagged as due diligence item for any KEK showing as `solar_now` |
| Firming adder | $6–16/MWh | Industry estimates; not empirically validated for Indonesia | Shown as range, labeled as approximate |
| Panel degradation | Not modeled (constant CF assumed) | CRF annuity method assumes flat annual production. Actual ~0.5%/yr degradation understates LCOE by ~6–7% over 27 years. Standard for IEA/IRENA screening models | For project-level analysis, adjust CF downward |
| Solar lifecycle emissions | Excluded from carbon breakeven | ~40 gCO2/MWh (IPCC AR6 median) not subtracted from grid displacement. Breakeven prices ~5–8% optimistic | Note in dashboard tooltip; use corrected formula for formal analysis |
| IDR/USD exchange rate | 15,800 (default) | 2024 reference. User-adjustable slider: 14,000–18,000 | Tier 2 slider; ~$3/MWh grid cost change per 5% FX move |

### User-adjustable parameters (dashboard sliders)

The dashboard exposes three tiers of adjustable parameters. All recompute the scorecard in real-time via `POST /api/scorecard`.

**Tier 1 (primary):**

| Slider | Default | Range | Effect |
|--------|---------|-------|--------|
| WACC | 10% | 4–20% (1% steps) | Changes LCOE via CRF; primary sensitivity lever |
| CAPEX | 960 USD/kW | 500–1500 (10 steps) | Solar overnight capital cost |
| Lifetime | 27 years | 20–35 (1 step) | Asset duration in CRF formula |

**Tier 2 (cost structure):**

| Slider | Default | Range | Effect |
|--------|---------|-------|--------|
| Fixed O&M | 7.5 $/kW-yr | 3–15 | Annual maintenance cost |
| Connection cost | 5 $/kW-km | 2–15 | Solar-to-substation line cost |
| Grid connection fixed | 80 $/kW | 30–200 | Substation interconnection works |
| Firming adder | 11 $/MWh | 5–20 | Battery/backup cost |
| IDR/USD rate | 15,800 | 14,000–18,000 | Exchange rate for tariff conversion |

**Tier 3 (thresholds and flags):**

| Slider | Default | Range | Effect |
|--------|---------|-------|--------|
| PVOUT threshold | 1,550 kWh/kWp | 1,200–1,800 | Minimum solar yield for `solar_attractive` |
| Plan-late threshold | 0.60 | 0.30–1.00 | Post-2030 share cutoff for `plan_late` flag |
| GEAS threshold | 0.30 | 0.05–0.50 | Minimum green share for `solar_now` flag |
| Resilience gap | 20% | 5–50% | Max LCOE gap for `invest_resilience` flag |
| Min viable capacity | 20 MWp | 5–50 | Minimum capacity for project viability |
| Reliability threshold | 0.75 | 0.30–1.00 | Reliability req for `firming_needed` flag |

**Implementation:** Slider configs defined in `src/dash/constants.py` (TIER1_SLIDERS, TIER2_SLIDERS, TIER3_SLIDERS). Served via `GET /api/defaults`. Frontend Zustand store tracks current values; changes trigger debounced `POST /api/scorecard` recomputation.

---

## 8. Open Methodological Questions

**Resolved decisions (Phase 1 + 2):**

1. ✅ **`solar_attractive` threshold** — WACC-dependent: `lcoe_mid ≤ dashboard_rate_usd_mwh`. No fixed threshold needed.

2. ✅ **`clean_power_advantage`** — implemented as `−solar_competitive_gap_pct` (Option A: continuous, intuitive). Column present in scorecard.

3. ✅ **`reliability_req` values** — set in `data/kek_grid_region_mapping.csv` by sector type: Manufacturing=0.8, Service/Digital=0.6, Tourism=0.4. Used by `firming_needed` and `invest_resilience` flags.

4. ✅ **I-3 vs I-4 tariff** — I-4/TT ($63.08/MWh) used as primary comparator (correct for large industrial KEK tenants). I-3/TM ($65.57/MWh) stored as `tariff_i3_usd_mwh` for reference. Both are uniform nationwide.

5. ✅ **`grid_upgrade_pre2030`** — derived from RUPTL capacity addition table: `True if pre2030_solar_mw > 0` for the KEK's grid region. Uses `fct_ruptl_pipeline.csv` pre-2030 sum.

6. ✅ **Buildability threshold** — All 4 buildability layers implemented (v1.1). `pvout_buildable_best_50km`, `buildable_area_ha`, `max_captive_capacity_mwp` all populated. 7/25 KEKs show zero buildable area. Flood hazard and road proximity deferred to v1.2.

7. ✅ **WACC expansion** — `WACC_VALUES` expanded to `[4, 6, 8, 10, 12, 14, 16, 18, 20]` (2% steps). `fct_lcoe` now 450 rows (was 150). Covers full concessional-to-equity spectrum: IFC/AIIB blended (4–6%), base case (10%), private equity ceiling (20%).

8. ✅ **Transmission lease fee** — V2 update: transmission lease removed entirely. In the grid-connected solar model, PLN absorbs delivery cost in BPP/tariff. Connection cost (solar→substation) replaces the gen-tie + lease model.

9. ✅ **Project viability threshold** — `project_viable` boolean added to `fct_kek_scorecard`. Derived from `max_captive_capacity_mwp ≥ 20 MWp` (IPP minimum; DFI screens at ≥ 33 MWp). All 25 KEKs = True at current 1km buildability resolution.

**Still open (genuine deferrals for Phase 3+):**

7. ✅ **BPP data** — Regional BPP Pembangkitan sourced from Kepmen ESDM 169/2021 (FY2020). `bpp_usd_mwh` populated for all 7 grid regions. Java-Bali ~$57/MWh, Papua ~$133/MWh. I-4/TT remains primary comparator; BPP is secondary reference.

8. ✅ **Buildability filter** — All 4 layers now active: Kawasan Hutan (KLHK 66K-polygon shapefile), peatland (KLHK vector boundaries), ESA WorldCover land cover, DEM slope > 8° / elevation > 1,500m. `pvout_buildable_best_50km`, `buildable_area_ha`, `max_captive_capacity_mwp` all populated. 7/25 KEKs show zero buildable area due to heavy kawasan hutan overlap.

9. ⏳ **Reliability threshold validation** — `reliability_req` thresholds are sector-derived (Manufacturing=0.8 etc.). Stakeholder validation with KEK operators recommended before using `invest_resilience` flag in formal policy advice.

---

## 9. Reproducibility

All inputs are publicly available:
- Global Solar Atlas GeoTIFFs: [globalatlas.solargis.com](https://globalatlas.solargis.com) (free download, registration required)
- ESDM Technology Catalogue: ESDM website (public)
- PLN Statistik: PLN website (public)
- RUPTL 2025–2034: ESDM/PLN website (public PDF)
- KEK data: OSS/KEK portal (public)

The pipeline is fully reproducible from raw inputs: `scripts/build_*.py` → `outputs/data/processed/` → `src/model/` → dashboard.

Versioned releases at GitHub Releases include the full `outputs/data/processed/` snapshot + this `METHODOLOGY.md` + `SOURCES.md`. The release version tag is shown in the dashboard footer.

---

*This document should be reviewed by an energy economist familiar with Indonesia's power sector before v1.0 is published. Key review areas: Section 4 (grid cost reference), Section 5.2 (action flag conditions), Section 5.3 (GEAS allocation assumptions).*
