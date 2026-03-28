# Methodology: Indonesia KEK Clean Power Competitiveness Model

**Version:** 0.2 (implemented)
**Status:** ✅ Fully implemented in code — 9 pipeline steps, 25 KEKs, 171 tests passing
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
  - [2A.5 Model Scope](#2a5-model-scope-phase-2-complete)
- [3. Levelized Cost of Energy (LCOE)](#3-levelized-cost-of-energy-lcoe)
  - [3.1 Formula](#31-formula)
  - [3.2 Technology parameters](#32-technology-parameters-tech006--utility-scale-solar-pv)
  - [3.3 WACC](#33-wacc)
  - [3.4 LCOE bands](#34-lcoe-bands)
- [4. Grid Cost Reference](#4-grid-cost-reference)
  - [4.1 What is being compared](#41-what-is-being-compared)
  - [4.2 Coverage by PLN grid system](#42-coverage-by-pln-grid-system)
- [5. Competitiveness Metrics and Action Flags](#5-competitiveness-metrics-and-action-flags)
  - [5.1 Solar competitive gap](#51-solar-competitive-gap)
  - [5.2 Action flags](#52-action-flags)
  - [5.2b Resilience layer](#52b-resilience-layer-invest_resilience)
  - [5.3 GEAS green share](#53-geas-green-share)
  - [5.3b Carbon breakeven price](#53b-carbon-breakeven-price)
  - [5.4 Flip scenario](#54-flip-scenario)
  - [5.5 All-in captive solar cost](#55-all-in-captive-solar-cost-investment-screen)
- [6. Known Limitations and Caveats](#6-known-limitations-and-caveats)
- [7. Assumptions Summary](#7-assumptions-summary)
- [8. Open Methodological Questions](#8-open-methodological-questions)
- [9. Reproducibility](#9-reproducibility)

---

## Workflow Summary

The model answers one question per KEK: **is captive solar cheaper than buying grid power, and if not, how close is it?**

### Data flow (5 steps)

```
Step 1 — Solar resource
  GeoTIFF (PVOUT daily, kWh/kWp/day)
    → × 365 → PVOUT_annual (kWh/kWp/yr)
    → ÷ 8760 → CF (capacity factor, decimal)

Step 2 — LCOE
  CAPEX [USD/kW] + FOM [USD/kW/yr] + WACC + lifetime + CF
    → CRF = WACC×(1+WACC)^n / ((1+WACC)^n − 1)
    → LCOE [USD/MWh] = (CAPEX×CRF + FOM) / (CF × 8.76)

Step 3 — Grid cost reference
  Permen ESDM No.7/2024, Lampiran IV
    → I-4/TT tariff = 996.74 Rp/kWh ≈ 63.1 USD/MWh  [uniform nationwide]
    → I-3/TM tariff = 1,035.78 Rp/kWh ≈ 65.6 USD/MWh [uniform nationwide]
    (BPP varies by PLN system — deferred; I-4/TT used as primary comparator)

Step 4 — Competitiveness gap
  solar_competitive_gap [%] = (LCOE − grid_cost) / grid_cost × 100
  Negative = solar already cheaper; Positive = solar more expensive

Step 5 — Action flags (per KEK)
  solar_now       : solar attractive AND grid ready AND GEAS ≥ 30%
  grid_first      : solar attractive BUT grid upgrade not yet pre-2030
  firming_needed  : solar attractive AND industrial reliability req ≥ 0.75
  plan_late       : ≥ 60% of RUPTL solar additions slip to post-2030
```

### Key inputs and sources

| Input | Value / Range | Source |
|-------|--------------|--------|
| PVOUT | 1,296–1,730 kWh/kWp/yr (extracted) | Global Solar Atlas v2 GeoTIFF |
| CF | 0.148–0.197 | Derived from PVOUT ÷ 8,760 |
| CAPEX (central) | 960 USD/kW | ESDM Tech Catalogue 2023, TECH006, p.66 (0.96 MUSD/MWe) |
| FOM | 7.5 USD/kW/yr | ESDM Tech Catalogue 2023, TECH006, p.66 (7,500 USD/MWe/yr) |
| WACC | 6–15% (slider); default 10% | User-adjustable |
| Lifetime | 27 years | ESDM Tech Catalogue 2023, TECH006, p.66 |
| Grid cost (primary) | 63.1 USD/MWh (I-4/TT) | Permen ESDM No.7/2024, uniform national |
| Grid cost (secondary) | 65.6 USD/MWh (I-3/TM) | Permen ESDM No.7/2024, uniform national |
| GEAS allocation | Pro-rata by demand share | RUPTL 2025–2034 pre-2030 solar additions |

### Critical caveats

- **PVOUT is an upper bound.** Buildability filters (forest, slope, peat, area) are not yet applied. All resource values carry `resource_quality = "provisional (no buildability filter)"`.
- **I-4/TT tariff ≠ BPP.** The tariff is what KEK tenants pay. PLN BPP (cost of supply) may be 15–35% higher. We use the tariff (correct), not BPP (incorrect comparator).
- **CAPEX/FOM are verified.** TECH006 values are sourced from the ESDM Technology Catalogue 2023, datasheet p.66, and stored as `VERIFIED_TECH006_DATA` in `src/pipeline/pdf_extract_esdm_tech.py`.
- **IDR/USD rate:** 15,800 IDR/USD (2024 reference). Tariff in IDR is subject to quarterly tariff adjustment (Pasal 6, Permen ESDM No.7/2024).

---

## 1. Scope and Core Question

**Question:** For each of Indonesia's 24 Special Economic Zones (KEK), is utility-scale solar captive generation currently cheaper than buying power from the PLN grid — and if not, how close is it, and what would change that?

**Unit of analysis:** KEK zone (24 zones). Results are at zone level, not tenant level or project level. A zone-level finding that "Kendal is 12% away from solar-competitive" means the representative economics for a utility-scale captive solar plant at that zone, not for any specific tenant's load profile.

**Technology scope (MVP):** Utility-scale ground-mounted PV (TECH006 in the ESDM Technology Catalogue). No wind, geothermal, or storage in the base model; architecture supports extension.

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

```
PVOUT_annual [kWh/kWp/yr] = PVOUT_daily [kWh/kWp/day] × 365
```

**Plausibility bounds for Indonesia:** 1,200 ≤ PVOUT_annual ≤ 2,200 kWh/kWp/yr. Values outside this range indicate a unit error or wrong raster band. Enforce as an assertion in `build_fct_kek_resource.py`.

### 2.3 Capacity factor

```
CF = PVOUT_annual / 8,760
```

Where 8,760 = hours per year. CF is dimensionless (decimal, not percent).

**Interpretation:** A KEK with PVOUT_annual = 1,650 kWh/kWp/yr has CF = 0.188 (18.8% capacity factor). This represents the fraction of time a 1 kWp panel produces its nameplate output, averaged over the year.

**Implementation note:** The formula assumes PVOUT is the production of a fixed-tilt, grid-connected PV system at standard conditions, which is how Global Solar Atlas defines it. No additional de-rating (soiling, temperature, inverter losses) is applied in the base model — these are embedded in Global Solar Atlas PVOUT estimates.

### 2.4 PVOUT extraction per KEK

Two PVOUT values are computed per KEK:

| Field | Definition | Use |
|-------|-----------|-----|
| `pvout_centroid` | PVOUT at the KEK centroid coordinate (lat, lon) | Reference point |
| `pvout_best_50km` | Maximum PVOUT pixel within 50km radius of centroid | **Primary: used for LCOE** |

**Rationale for `pvout_best_50km`:** A captive solar plant does not have to sit exactly at the KEK centroid — it can be sited at the best available location within 50km and power wheeled to the zone. Using the best resource within a reasonable siting radius gives a more actionable economics estimate. 50km is consistent with typical captive power project development radius in Indonesia.

**Radius calculation:** 50km in degrees is latitude-dependent. Use:
```
lat_buffer_deg = 50 / 111.32
lon_buffer_deg = 50 / (111.32 × cos(lat_rad))
```
where `lat_rad` is the KEK centroid latitude in radians. Do not use a fixed 0.45° buffer for both axes.

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

For **captive solar** (power consumed on-site by KEK tenants), this filter is different from grid-injection solar:
- If the solar plant is **inside the KEK boundary** or connected via a private dedicated line: no PLN substation proximity required — the plant connects directly to the KEK internal 20kV distribution network
- If the solar plant is **outside the KEK boundary** (the common case for `pvout_best_50km` siting): a gen-tie line (private dedicated transmission line) must be built to wheel power to the KEK. Typical wheeling cost: **$3–10/kW-km** of line length plus ~$100–200/kW for substation works
- PLN's 70kV/150kV substation proximity matters only for grid-injection projects or for hybrid captive-grid arrangements

**Practical threshold for the model:** If `pvout_best_50km` site is > 30km from the KEK boundary, flag as `wheeling_required = True` and apply the all-in cost adder range to account for gen-tie capex. The current model's $6–16/MWh firming/wheeling adder already covers this implicitly for near-site options; distant options may exceed this range.

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

**Key implication for this model:** Java KEKs (Kendal, JIIPE, Cirebon, etc.) are the most constrained by **agriculture and density**, not forest. Outer island KEKs are most constrained by **Kawasan Hutan**. The MVP's simplifying assumption that "buildable land exists within 50km" is most likely to hold for Sumatra outer-island KEKs and least likely for densely populated Java KEKs or forest-heavy Sulawesi KEKs.

---

#### v1.1 Implementation Status

**v1.1 (implemented):** Layers 1a/1b/1c-d/2a/2c/4 are implemented in code and ready to run.
`fct_kek_resource` now outputs `pvout_buildable_best_50km`, `buildable_area_ha`,
`max_captive_capacity_mwp`, and `buildability_constraint`. When `data/buildability/` files
are present, `fct_lcoe` and `fct_kek_scorecard` automatically use `pvout_buildable_best_50km`
in the `remote_captive` scenario; `resource_quality` is set to `"filtered"`.

**Current state (data acquisition):**
- ✅ `dem_indonesia.tif` — Copernicus DEM GLO-30, automated via `scripts/download_buildability_data.py`
- ✅ `esa_worldcover.vrt` — ESA WorldCover v200 2021, automated via `scripts/download_buildability_data.py`
- ❌ `kawasan_hutan.shp` — KLHK Kawasan Hutan, manual download from geoportal.menlhk.go.id
- ❌ `peatland_zones.shp` — KLHK peatland zones, manual download from geoportal.menlhk.go.id

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
| Forest estate boundary (Layer 1a) | KLHK Kawasan Hutan | geoportal.menlhk.go.id | Shapefile → `kawasan_hutan.shp` | Public, manual download |
| Land cover: forest, cropland, water, urban (Layer 1c/d) | ESA WorldCover v200 2021 | AWS S3 public mirror | Raster 10m → `esa_worldcover.vrt` | Free, automated |
| Peatland function zones (Layer 1b) | KLHK/BRG | geoportal.menlhk.go.id | Shapefile → `peatland_zones.shp` | Public, manual download |
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

This model evaluates two distinct captive solar configurations per KEK:

| Scenario | PVOUT input | Gen-tie needed? | PLN fees | LCOE treatment |
|---|---|---|---|---|
| **Within-boundary captive** | `pvout_centroid` | None — plant on KEK land, connects to KEK's own 20kV distribution | None (if purely internal) | Base LCOE only |
| **Remote captive (≤50km)** | `pvout_best_50km` | Yes, if plant is outside KEK boundary | Parallel operation charge + transmission lease | Base LCOE + gen-tie adder (`gentie_cost_per_kw(dist_km)`) |

**Gen-tie adder (Phase 2, implemented):** `dist_to_nearest_substation_km` from `fct_substation_proximity.csv` drives the gen-tie cost adder. Formula: `dist_km × GENTIE_COST_PER_KW_KM + SUBSTATION_WORKS_PER_KW` (USD/kW) — see `src/assumptions.py` for central values. Gen-tie is treated as additional overnight CAPEX, annualized via the same CRF as the solar plant.

### 2A.5 Model Scope (Phase 2 complete)

**Current implementation computes:**
- Within-boundary LCOE using `pvout_centroid`, `gentie = 0`
- Remote captive LCOE using `pvout_best_50km` + `gentie_cost_per_kw(dist_to_nearest_substation_km)`

**Output:** `fct_lcoe.csv` — 150 rows (25 KEKs × 3 WACCs × 2 scenarios). Scorecard uses `within_boundary` at WACC=10% as the base-case dashboard comparator.

**Deferred to Phase 3:**
- Transmission lease fee parameterisation (currently excluded; adds ~5–15 USD/MWh at scale)
- WACC sensitivity for gen-tie cost specifically (gen-tie often financed separately from plant)

**Regulatory sources:**
- UU No. 30 Tahun 2009 (Ketenagalistrikan)
- PP No. 14 Tahun 2012 (Kegiatan Usaha Penyediaan Tenaga Listrik)
- Permen ESDM No. 1 Tahun 2015 (Kerja Sama Pengaliran Tenaga Listrik)
- Permen ESDM No. 1 Tahun 2017 (Persyaratan Teknik Penyambungan ke Sistem Tenaga Listrik)
- Permen ESDM No. 27 Tahun 2017 (Tingkat Mutu Pelayanan dan Biaya yang Terkait dengan Penyaluran Tenaga Listrik)
- Permen ESDM No. 11 Tahun 2021 (Pelaksanaan Kegiatan Usaha Penyediaan Tenaga Listrik)

---

## 3. Levelized Cost of Energy (LCOE)

### 3.1 Formula

The LCOE for utility-scale solar PV is computed using the annuity method (standard capital recovery factor approach):

```
CRF(wacc, n) = wacc × (1 + wacc)^n / ((1 + wacc)^n − 1)

LCOE [USD/MWh] = (CAPEX × CRF + FOM) / (CF × 8.76)
```

Where:
- `CAPEX` = capital expenditure [USD/kW]
- `FOM` = fixed operations and maintenance cost [USD/kW/yr]
- `wacc` = weighted average cost of capital [decimal, e.g. 0.10 for 10%]
- `n` = project lifetime [years]
- `CF` = capacity factor [decimal]
- `8.76` = 8,760 hours/year ÷ 1,000 W/kW (unit conversion to MWh/kW/yr)

**Derivation:**
- `CAPEX × CRF` = annualized capital cost per kW of installed capacity [USD/kW/yr]
- `CAPEX × CRF + FOM` = total annual cost per kW [USD/kW/yr]
- `CF × 8.76` = annual energy production per kW [MWh/kW/yr]
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
```
CAPEX [USD/kW] = CAPEX_catalogue [MUSD/MWe] × 1,000
```
(1 MUSD/MWe = 1,000,000 USD / 1,000 kW = 1,000 USD/kW)

Add assertion: `assert 200 < CAPEX < 3000` to catch unit errors.

### 3.3 WACC

The WACC is the primary user-adjustable parameter in the dashboard (slider: 6–15%, default: 10%).

**Default 10% rationale:** ADB's benchmark weighted average cost of capital for renewable energy projects in Southeast Asia is approximately 8–12%. 10% is the midpoint and a common assumption in development bank screening models. The user can adjust to match their fund's actual hurdle rate.

**WACC=8% de-risked scenario:** The scorecard precomputes a static WACC=8% column (`lcoe_mid_wacc8_usd_mwh`, `solar_competitive_gap_wacc8_pct`, `solar_now_at_wacc8`) alongside the WACC=10% base case. At WACC=8%, **8 KEKs flip to solar-competitive** (vs. 0 at WACC=10%). This answers the DFI question "what financing de-risking is needed?" — if a green finance facility, concessional loan, or first-loss guarantee can bring a project's effective WACC from 10% to 8%, solar wins for those 8 KEKs without any change in the underlying resource or technology cost.

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
| PLN BPP | PLN's cost of supply (biaya pokok penyediaan) by grid system | PLN Statistik 2024 | ⚠️ deferred — `bpp_usd_mwh` column exists in `fct_grid_cost_proxy` but is null |
| I-4 industrial tariff | Tariff paid by large industrial consumers (≥30,000 kVA) | Permen ESDM No. 7 Tahun 2024 | ✅ implemented — $63.08/MWh, uniform nationwide |
| I-3 industrial tariff | Tariff paid by medium industrial consumers (200–30,000 kVA) | Permen ESDM No. 7 Tahun 2024 | ✅ implemented — $65.57/MWh, uniform nationwide |

**Critical distinction:** PLN BPP is PLN's *cost of supply*, not the tariff a KEK tenant actually pays. Industrial tariffs (Golongan I-3/I-4) are set by ESDM and may be 15–35% below BPP due to cross-subsidy policy. Using BPP as the comparator overstates the grid cost, making solar appear more competitive than it is in practice.

**Methodology decision (RESOLVED):**
- `dashboard_rate_usd_mwh` = I-4/TT tariff ($63.08/MWh) — the correct primary comparator for large industrial KEK tenants. Flagged `OFFICIAL` in `fct_grid_cost_proxy`.
- I-3/TM ($65.57/MWh) is stored as `tariff_i3_usd_mwh` — available for smaller tenant analysis.
- Both tariffs are **uniform nationwide** (Permen ESDM No. 7/2024, Lampiran IV). No regional variation.
- BPP is deferred — stored as null in `bpp_usd_mwh`. If added, it would be used only as a secondary reference with a `PROVISIONAL` caveat: *"Grid cost shown is PLN cost of supply (BPP), not the industrial tariff paid by tenants."*

### 4.2 Coverage by PLN grid system

Grid costs are at PLN **system level** (e.g., Sistem Jawa-Bali, Sistem Sumatera), not at KEK level. Each KEK inherits the grid cost of the system it belongs to, via the `grid_region_id` join.

✅ `data/kek_grid_region_mapping.csv` exists — 26 rows mapping all 25 KEKs to their PLN grid system (`grid_region_id`), province, and `reliability_req`. Created manually via KEK address data and PLN system boundary maps. Maintained as a lookup table; update if a KEK's grid connection changes.

---

## 5. Competitiveness Metrics and Action Flags

### 5.1 Solar competitive gap

```
solar_competitive_gap [%] = (lcoe_mid − grid_cost) / grid_cost × 100
```

Where `grid_cost` = `dashboard_rate_usd_mwh` from `fct_grid_cost_proxy`.

**Interpretation:**
- **Negative gap:** Solar LCOE < grid cost → solar is already cheaper at this WACC
- **Positive gap:** Solar LCOE > grid cost → grid is cheaper by this percentage
- **Example:** gap = −12% → solar is 12% cheaper than grid; gap = +20% → grid is 20% cheaper than solar

**Edge cases:**
- `grid_cost = 0` or `NaN`: return `NaN`
- `lcoe_mid = NaN` (PVOUT unavailable): return `NaN`

### 5.2 Action flags

Five mutually-ordered boolean flags. A KEK receives the first flag for which its conditions are satisfied:

| Flag | Conditions | Interpretation |
|------|-----------|----------------|
| `solar_now` | `solar_attractive AND NOT grid_first AND green_share_geas ≥ 0.30` | Go solar — economics work, grid supports it, GEAS allocation available |
| `grid_first` | `solar_attractive AND NOT grid_upgrade_pre2030` | Solar economics work but grid upgrade not planned before 2030 — wait for grid |
| `firming_needed` | `solar_attractive AND reliability_req ≥ 0.75` | Solar economics work but zone needs high reliability — add storage/firming |
| `invest_resilience` | `0 < solar_competitive_gap_pct ≤ 20 AND reliability_req ≥ 0.75` | Solar slightly above grid parity, but manufacturing uptime avoidance justifies the premium |
| `plan_late` | `post2030_share ≥ 0.60` | >60% of RUPTL additions for this region are planned post-2030 — pipeline is late |

**`not_competitive` fallback:** If all data is present but no flag fires, the KEK is labelled `not_competitive`. This is distinct from `data_missing` (missing inputs). At WACC=10%, with correct TECH006 CAPEX ($960/kW), most Indonesian KEKs fall here — the model correctly reports that solar is not yet at grid parity for the average KEK under these assumptions.

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
```
invest_resilience = (solar_competitive_gap_pct > 0)         # solar not yet at grid parity
                  AND (solar_competitive_gap_pct ≤ 20.0)    # within 20% of grid cost
                  AND (reliability_req ≥ 0.75)              # high reliability KEK
```

**Constant:** `RESILIENCE_LCOE_GAP_THRESHOLD_PCT = 20.0` (src/assumptions.py)
**Implementation:** `invest_resilience()` in `src/model/basic_model.py`

**Current results (WACC=10%):** 4 KEKs fire this flag — Kendal (gap=13.0%), Gresik (14.2%), Batang (14.6%), Bitung (17.4%). All are manufacturing KEKs in Java-Bali and Sulawesi. Carbon breakeven for these: $10–17/tCO2 — well within Indonesia's emerging carbon market trajectory.

**`solar_attractive` definition:**
```
solar_attractive = (pvout_best_50km ≥ 1,550 kWh/kWp/yr) AND (lcoe_mid ≤ [threshold USD/MWh])
```

⚠️ **Open question:** Should the LCOE threshold be a fixed value or WACC-dependent? Options:
- A) Fixed threshold (e.g., 60 USD/MWh at base-case WACC 10%) — simpler, but threshold choice is arbitrary
- B) WACC-dependent: `solar_attractive = (solar_competitive_gap ≤ 0)` — more rigorous, directly linked to grid cost comparison
- **Recommendation:** Option B — `solar_attractive` should simply mean "solar LCOE ≤ grid cost at current WACC." This makes the flag directly interpretable and removes the need for a hardcoded threshold.

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
```
geas_alloc_mwh[kek] = allocatable_green_mwh[region] × (demand_mwh[kek] / region_demand_mwh)

green_share_geas[kek] = min(1.0, geas_alloc_mwh[kek] / demand_mwh[kek])
```

Where `allocatable_green_mwh[region] = pre2030_solar_mw[region] × 8,760 × CF_region`.

`CF_region` = assumed regional average CF = 0.20 (20%). This is a system-level assumption for RUPTL-planned solar (not site-specific).

**Policy scenario allocation (proportional to demand × PVOUT):**
```
priority_score[kek] = demand_mwh[kek] × pvout_best_50km[kek]

geas_alloc_policy[kek] = allocatable_green_mwh_policy[region] × (priority_score[kek] / region_priority_score)
```

This prioritizes zones with both high demand and high solar resource.

### 5.3b Carbon breakeven price

The carbon breakeven price answers the policy question: **"At what carbon price does solar become cost-competitive with the grid?"**

**Formula:**
```
lcoe_gap_usd_mwh = lcoe_mid_usd_mwh - grid_cost_usd_mwh

if lcoe_gap_usd_mwh ≤ 0:
    carbon_breakeven = 0.0   # solar already competitive — no carbon price needed
else:
    carbon_breakeven = lcoe_gap_usd_mwh / grid_emission_factor_t_co2_mwh
```

Unit: USD/tCO2. Interpretation: if carbon is priced at or above this level (via Indonesia's carbon market, EU CBAM exposure, or corporate net-zero commitments), solar wins on adjusted total cost.

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

Source: KESDM Tier 2 grid emission factor database, 2019 vintage (`data/grid_emission_factors.xlsx`, gatrik.esdm.go.id). File: `src/assumptions.py → GRID_EMISSION_FACTOR_T_CO2_MWH`. Refine when KESDM publishes updated Tier 2 factors (typically every 2–3 years).

**Policy implications of corrected values:**
- Kalimantan (OM=1.16) has the highest emission intensity — solar displaces the most carbon per MWh, bringing breakeven carbon prices down to ~$16–17/tCO2 even at 30%+ LCOE premium.
- Mandalika/NTB (OM=1.27) has the most diesel-dependent grid — carbon breakeven only $3.4/tCO2, making any credible carbon pricing sufficient to flip the economics.
- Sorong/Papua (OM=0.56) is gas-dominant — carbon breakeven is $29/tCO2, requiring stronger policy signals.

**Implementation:** `carbon_breakeven_price()` in `src/model/basic_model.py`; emission factors in `GRID_EMISSION_FACTOR_T_CO2_MWH` (src/assumptions.py).

### 5.4 Flip scenario

The flip scenario identifies KEKs that are close to solar-competitive:

```
flip_threshold [%]: user-adjustable, default 20%

flip_candidates = [kek for kek in all_keks if 0 < solar_competitive_gap[kek] ≤ flip_threshold]
```

These are zones where solar is not yet competitive but is within `flip_threshold`% — meaning a modest policy intervention (CAPEX reduction via GBT program, lower WACC, or tariff adjustment) could make it competitive.

### 5.5 All-in captive solar cost (investment screen)

The LCOE formula captures generation cost only. A KEK tenant choosing captive solar also incurs:

| Cost component | Typical range | Source |
|---------------|--------------|--------|
| Grid backup contract (standby power) | ~$3–8/MWh on an effective basis | Industry estimates |
| Wheeling charges (if not on-site) | ~$2–5/MWh | PLN wheeling tariff |
| PLN permitting and connection costs | ~$1–3/MWh amortized | Industry estimates |
| **Total adder** | **~$6–16/MWh** | — |

The scorecard displays:
```
lcoe_all_in_low = lcoe_mid + 6   [USD/MWh]  (optimistic adder)
lcoe_all_in_high = lcoe_mid + 16  [USD/MWh]  (conservative adder)
```

This adder range is clearly labeled as an estimate. The competitive gap calculation uses `lcoe_mid` (generation cost only) as the primary metric; the all-in range is shown as a secondary context band.

---

## 6. Known Limitations and Caveats

| Limitation | Impact | Mitigation |
|-----------|--------|------------|
| PVOUT from Global Solar Atlas, not site-specific measurement | ±5–10% LCOE uncertainty | Use `pvout_best_50km` not centroid; show LCOE band (low/mid/high) |
| No geospatial buildability filter applied (slope, Kawasan Hutan, peat, agriculture, minimum area) | `pvout_best_50km` is an upper bound — actual buildable resource may be significantly lower, especially on Java (agriculture/density) and Sulawesi (Kawasan Hutan + steep terrain); expected available area after filters: 10–35% of 50km radius depending on island (see Section 2.5) | All resource values labeled `provisional (no buildability filter)` in scorecard; v1.1 adds 4-layer filter using Copernicus DEM 30m + KLHK Peta Penutupan Lahan + Kawasan Hutan boundary |
| No buildable area estimate (`max_captive_capacity_mwp`) | Cannot screen out zones where total buildable land < 10 ha (minimum viable 6–7 MWp project) — a KEK may appear resource-rich but have no contiguous buildable patch | Deferred to v1.1; morphological opening filter on buildability mask → `buildable_area_ha` column in `fct_kek_resource` |
| Grid cost proxy may be BPP, not actual industrial tariff | LCOE gap overstated if BPP > tariff | Show I-4 tariff as primary where available; flag BPP as provisional |
| LCOE excludes firming, wheeling, permitting costs | All-in cost understated by ~$6–16/MWh | Show all-in cost adder band in scorecard |
| KEK demand figures not available (using RUPTL region-level data) | GEAS allocation is approximate | Label `green_share_geas` as indicative, not contractual |
| RUPTL capacity additions are planned, not committed | `grid_upgrade_pre2030` and `plan_late` flags may change | Vintage-stamp RUPTL data; re-run on new RUPTL releases |
| No reliability data (SAIDI/SAIFI) | Cannot quantify reliability premium for captive solar | Deferred to v2 when PLN data is available |
| No wind or geothermal in base model | Understates clean power options for some zones (e.g., Sulawesi) | Architecture supports extension; add Wind CF as v1.1 |
| CAPEX from ESDM catalogue, not Indonesia-specific market data | Actual Indonesian solar CAPEX may vary ±15–20% from catalogue | Show CAPEX sensitivity (low/mid/high) in LCOE bands |

---

## 7. Assumptions Summary

| Assumption | Value | Rationale | Sensitivity |
|-----------|-------|-----------|-------------|
| Default WACC | 10% | ADB benchmark for SEA renewable energy | Dashboard slider: 6–15% |
| PVOUT siting radius | 50 km | Typical captive power siting radius in Indonesia | Fixed in MVP |
| Regional solar CF (GEAS) | 20% | Representative for RUPTL-planned utility solar in Indonesia | Low sensitivity |
| RUPTL GEAS baseline allocation | Pro-rata to demand | Simplest defensible allocation; no preferential treatment | Policy scenario uses demand × PVOUT |
| `plan_late` threshold | post2030_share ≥ 60% | Majority of regional additions post-2030 = late pipeline | Could be 50% or 70%; low sensitivity on flag count |
| `firming_needed` / `invest_resilience` reliability threshold | reliability_req ≥ 0.75 | Manufacturing/processing KEKs per sector classification in `kek_grid_region_mapping.csv` (Manufacturing=0.8, Service=0.6, Tourism=0.4). Threshold operationalized; stakeholder validation recommended for v2. | |
| PVOUT plausibility bounds | 1,000–2,500 kWh/kWp/yr | Indonesia solar range from Global Solar Atlas | Used for data validation, not analysis |
| Buildable land (≥ 10 ha contiguous, slope ≤ 8°, outside Kawasan Hutan / peat / flood zones) assumed to exist within 50km radius | MVP simplification — risk is highest for Java KEKs (dense agriculture) and Sulawesi KEKs (Kawasan Hutan + steep terrain); outer Sumatra KEKs are generally lower risk | `pvout_best_50km` labeled `provisional`; v1.1 applies 4-layer filter (Section 2.5) to compute `pvout_buildable_best_50km` and `buildable_area_ha` |
| Land use for captive solar assumed compliant with RTRW spatial plan | Local spatial plans (RTRW kabupaten/provinsi) may designate specific zones for industrial vs. agricultural use; solar on APL land is generally permissible but RTRW compliance must be verified per KEK by the developer | Not modeled; flagged as due diligence item for any KEK showing as `solar_now` |
| Firming/wheeling adder | $6–16/MWh | Industry estimates; not empirically validated for Indonesia | Shown as range, labeled as approximate |

---

## 8. Open Methodological Questions

**Resolved decisions (Phase 1 + 2):**

1. ✅ **`solar_attractive` threshold** — WACC-dependent: `lcoe_mid ≤ dashboard_rate_usd_mwh`. No fixed threshold needed.

2. ✅ **`clean_power_advantage`** — implemented as `−solar_competitive_gap_pct` (Option A: continuous, intuitive). Column present in scorecard.

3. ✅ **`reliability_req` values** — set in `data/kek_grid_region_mapping.csv` by sector type: Manufacturing=0.8, Service/Digital=0.6, Tourism=0.4. Used by `firming_needed` and `invest_resilience` flags.

4. ✅ **I-3 vs I-4 tariff** — I-4/TT ($63.08/MWh) used as primary comparator (correct for large industrial KEK tenants). I-3/TM ($65.57/MWh) stored as `tariff_i3_usd_mwh` for reference. Both are uniform nationwide.

5. ✅ **`grid_upgrade_pre2030`** — derived from RUPTL capacity addition table: `True if pre2030_solar_mw > 0` for the KEK's grid region. Uses `fct_ruptl_pipeline.csv` pre-2030 sum.

6. ✅ **Buildability threshold** — `pvout_best_50km` labeled provisional (upper bound, no terrain filter). Deferred to v1.1. All resource values carry `data_completeness` flag.

**Still open (genuine deferrals for Phase 3+):**

7. ⏳ **BPP data** — PLN Statistik 2024 regional BPP not yet sourced. `bpp_usd_mwh` column exists but is null. When available, add as secondary reference — do not replace I-4/TT as primary comparator.

8. ⏳ **Landcover buildability filter** — `pvout_best_50km` is an upper bound. Planned for v1.1: 4-layer filter (HCS/HCV, peatland, protected areas, slope > 15°) → `pvout_buildable_best_50km` + `buildable_area_ha`.

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
