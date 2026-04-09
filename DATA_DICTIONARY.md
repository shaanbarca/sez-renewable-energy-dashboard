# Data Dictionary — Indonesia KEK Power Competitiveness

Contract for the data pipeline. Three parts:

- **Part 1 — Raw inputs**: source, format, and column status for every input file
- **Part 2 — Dimension tables**: one row per entity (KEK, technology)
- **Part 3 — Fact tables**: computed outputs, with lineage and formulas for every derived column

**Status legend:** ✅ available | ⚠️ partial/needs cleaning | ❌ missing | 🔒 manual (human required)

---

## Table of Contents

- [Table Index](#table-index) — all 9 output tables at a glance
- [Part 1 — Raw Inputs](#part-1--raw-inputs)
  - [1.1 kek_info_and_markers.csv](#11-outputsdatarawkek_info_and_markerscsv)
  - [1.2 kek_distribution_points.csv](#12-outputsdatarawkek_distribution_pointscsv)
  - [1.3 kek_polygons.geojson](#13-outputsdatarawkek_polygonsgeojson)
  - [1.4 kek_grid_region_mapping.csv](#14-datakek_grid_region_mappingcsv)
  - [1.5 dim_tech_variant.csv + fct_tech_parameter.csv](#15-datadim_tech_variantcsv--datafct_tech_parametercsv)
  - [1.6 Global Solar Atlas GeoTIFF](#16-global-solar-atlas-geotiff-zipped)
  - [1.7 Permen ESDM 7/2024 (tariff PDF)](#17-docspermen-esdm-nomor-7-tahun-2024pdf)
  - [1.8 RUPTL 2025–2034 (PDF)](#18-docsb967d-ruptl-pln-2025-2034-pub-pdf)
  - [1.9 substation.geojson](#19-datasubstationgeojson)
- [Part 2 — Dimension Tables](#part-2--dimension-tables)
  - [2.1 dim_kek](#21-outputsdataprocesseddim_kekcsv)
  - [2.2 dim_tech_cost](#22-outputsdataprocesseddim_tech_costcsv)
- [Part 3 — Fact Tables](#part-3--fact-tables)
  - [3.1 fct_kek_resource](#31-outputsdataprocessedfct_kek_resourcecsv)
  - [3.2 fct_kek_demand](#32-outputsdataprocessedfct_kek_demandcsv)
  - [3.3 fct_grid_cost_proxy](#33-outputsdataprocessedfct_grid_cost_proxycsv)
  - [3.4 fct_ruptl_pipeline](#34-outputsdataprocessedfct_ruptl_pipelinecsv)
  - [3.4b fct_substation_proximity](#34b-outputsdataprocessedfct_substation_proximitycsv)
  - [3.5 fct_lcoe](#35-outputsdataprocessedfct_lcoecsv)
  - [3.6 fct_kek_scorecard](#36-outputsdataprocessedfct_kek_scorecardcsv)
- [Open Questions](#open-questions)

---

## Table Index

All processed output tables. Click a table name to jump to its full column spec.

| Table | Type | Rows | What it contains | Built from | Used for | Status |
|-------|------|------|------------------|------------|----------|--------|
| [dim_kek](#21-outputsdataprocesseddim_kekcsv) | dim | 25 | Master KEK list: name, province, grid region, lat/lon, area, reliability requirement | `kek_info_and_markers.csv` · `kek_distribution_points.csv` · `kek_polygons.geojson` · `kek_grid_region_mapping.csv` | The master reference for every KEK. Every fact table joins to this on `kek_id`. Also drives the map layer in the dashboard. | ✅ |
| [dim_tech_cost](#22-outputsdataprocesseddim_tech_costcsv) | dim | 1 | TECH006 solar PV CAPEX / FOM / lifetime, unit-converted for LCOE formula | `dim_tech_variant.csv` · `fct_tech_parameter.csv` | Holds the cost assumptions (CAPEX, fixed O&M, asset lifetime) that are plugged into the LCOE formula. Changing these numbers here flows through to all 150 LCOE rows automatically. | ✅ Verified from ESDM Tech Catalogue 2023 p.66 |
| [fct_kek_resource](#31-outputsdataprocessedfct_kek_resourcecsv) | fact | 25 | PVOUT at centroid + best-within-50km; capacity factors; buildability columns (NaN until `data/buildability/` populated) | `dim_kek` · Global Solar Atlas GeoTIFF · optional: `data/buildability/` | Answers "how much sun does each KEK get?" — and (when data available) "how much of that land is actually buildable?". | ⚠️ `pvout_buildable_best_50km` NaN until data/buildability/ populated (run `scripts/download_buildability_data.py`) |
| [fct_kek_demand](#32-outputsdataprocessedfct_kek_demandcsv) | fact | 25 | Estimated 2030 electricity demand per KEK (area × intensity) | `dim_kek` · `src/assumptions.py` (intensity constants) | Answers "how much electricity will this KEK need by 2030?" — used to compute what share of that demand could be met by GEAS-allocated solar, and to size infrastructure needs. | ⚠️ Provisional — area×intensity proxy, no tenant surveys |
| [fct_grid_cost_proxy](#33-outputsdataprocessedfct_grid_cost_proxycsv) | fact | 7 | I-4/TT and I-3/TM industrial tariffs per PLN grid system (USD/MWh) | `dim_kek` (grid_region_id list) · Permen ESDM 7/2024 (hardcoded tariffs) | The benchmark each KEK's solar LCOE is compared against. If solar LCOE < grid tariff, captive solar is already cost-competitive without any policy support. | ✅ Official — Permen ESDM 7/2024 |
| [fct_ruptl_pipeline](#34-outputsdataprocessedfct_ruptl_pipelinecsv) | fact | 70 | PLN solar capacity additions 2025–2034 by region, RE Base + ARED scenarios | `docs/b967d-ruptl-pln-2025-2034-pub-.pdf` (Tables 5.84–5.103, manually transcribed) | Answers "what grid-scale solar is PLN planning near this KEK's region?" — used to compute the GEAS green energy share each KEK can claim, and to flag KEKs where the grid upgrade comes too late (post-2030). | ✅ Manually verified from RUPTL PDF |
| [fct_substation_proximity](#34b-outputsdataprocessedfct_substation_proximitycsv) | fact | 25 | Nearest PLN substation per KEK — KEK-to-substation + solar-to-substation distances, grid_integration_category | `dim_kek` · `data/substation.geojson` · `raw/kek_polygons.geojson` · `fct_kek_resource` | V2: Three-point proximity (solar→substation→KEK). Drives connection cost in `fct_lcoe` grid_connected_solar scenario. Classifies grid readiness. | ✅ |
| [fct_lcoe](#35-outputsdataprocessedfct_lcoecsv) | fact | 450 | Precomputed LCOE bands — 25 KEKs × 9 WACC values (4–20% in 2% steps) × 2 siting scenarios (within_boundary/grid_connected_solar) | `dim_kek` · `fct_kek_resource` · `dim_tech_cost` · `fct_substation_proximity` | Powers the WACC slider and scenario comparison. `within_boundary` is base-case; `grid_connected_solar` adds connection cost (solar→substation). | ✅ |
| [fct_kek_scorecard](#36-outputsdataprocessedfct_kek_scorecardcsv) | fact | 25 | Full join: LCOE + grid cost + demand + RUPTL + action flags + competitive gap | `dim_kek` · `fct_lcoe` (WACC=10%) · `fct_kek_resource` · `fct_kek_demand` · `fct_grid_cost_proxy` · `fct_ruptl_pipeline` | The single table the dashboard reads. For each KEK it answers: is solar already cheaper than the grid? If not, how close? What action is recommended (go solar now / wait for grid / add firming / flag late pipeline)? What share of demand can green energy cover by 2030? | ⚠️ Provisional until CAPEX verified |

---

# Part 1 — Raw Inputs

---

## 1.1 `outputs/data/raw/kek_info_and_markers.csv`

**Source:** Scraped from OSS/KEK portal via `notebooks/kek_scraper.ipynb` (Playwright)
**Format:** CSV, one row per KEK
**Rows:** 24

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `xid` | str | ✅ | Unique ID from KEK portal (e.g., "FHE4Z6LV") |
| `slug` | str | ✅ | URL slug — used as `kek_id` throughout pipeline |
| `title` | str | ✅ | Full KEK name |
| `address` | str | ✅ | Human-readable address — province extracted from here |
| `latitude` | float | ✅ | Centroid latitude (WGS84) |
| `longitude` | float | ✅ | Centroid longitude (WGS84) |
| `category` | str | ✅ | KEK type string (e.g., "Manufacturing", "Tourism") |
| `legalBasis` | str | ✅ | Government decree reference |
| `developer` | str | ✅ | Developer entity name |
| `area` | float | ⚠️ | Area in unknown units — use `Luas_ha` from polygons instead |
| `infrastructures` | str | ⚠️ | JSON-like list; not used in model |
| `grid_region_id` | str | ❌ 🔒 | Not in source — add manually via `data/kek_grid_region_mapping.csv` |
| `province` | str | ❌ | Embedded in `address` — extracted by `build_dim_kek.py` |
| `status` | str | ❌ | Not in this file — joined from `kek_distribution_points.csv` on `xid` |

---

## 1.2 `outputs/data/raw/kek_distribution_points.csv`

**Source:** KEK portal distribution/status endpoint, scraped via `notebooks/kek_scraper.ipynb`
**Format:** CSV, one row per KEK
**Rows:** ~24

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `xid` | str | ✅ | Join key to 1.1 |
| `slug` | str | ✅ | Same slug |
| `status.id` | str | ✅ | Operational status ID |
| `status.name` | str | ✅ | Operational status — maps to `dim_kek.status` |
| `category.name` | str | ✅ | More structured than markers category |
| `createdAt` | str | ⚠️ | Not used |
| `updatedAt` | str | ⚠️ | Not used |

---

## 1.3 `outputs/data/raw/kek_polygons.geojson`

**Source:** Polygon boundaries scraped from KEK portal S3
**Format:** GeoJSON, one Feature per KEK
**CRS:** WGS84 (EPSG:4326)

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `slug` | str | ✅ | Join key to dim_kek |
| `JenisKEK` | str | ✅ | KEK type — maps to `kek_type` (e.g., "Industri", "Pariwisata") |
| `Luas_ha` | float | ✅ | Authoritative area in hectares — used in demand calculation |
| `DasarHukum` | str | ✅ | Legal basis |
| `geometry` | Polygon | ✅ | Zone boundary |
| `Shape_Area` | float | ⚠️ | Area in map units — redundant with `Luas_ha` |

**Note:** Some KEKs have multiple polygon features (sub-zones). `build_dim_kek.py` deduplicates by keeping the largest `Luas_ha` per `slug`.

---

## 1.4 `data/kek_grid_region_mapping.csv`

**Source:** Manual lookup — human-assigned based on PLN grid maps
**Format:** CSV
**Status:** 🔒 manually maintained

| Column | Type | Notes |
|--------|------|-------|
| `kek_id` | str | Matches `slug` from 1.1 |
| `grid_region_id` | str | PLN grid system: `JAVA_BALI` / `SUMATERA` / `SULAWESI` / `KALIMANTAN` / `MALUKU_PAPUA` / `NTB_NTT` |
| `pln_system_name` | str | Full PLN system name |
| `reliability_req` | float | Minimum reliability requirement (0–1); default 0.6 for service, 0.8 for manufacturing |
| `reliability_notes` | str | Rationale |

---

## 1.5 `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv`

**Source:** ESDM Technology Catalogue (parsed from `docs/esdm_technology_cost.pdf`)
**Format:** Two-table design — variant lookup + per-parameter values

**`dim_tech_variant.csv`** — technology types

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `tech_id` | str | ✅ | e.g., "TECH006" = solar PV ground-mounted utility-scale |
| `variant` | str | ✅ | Full description |
| `energy_source` | str | ✅ | e.g., "Solar" |

**`fct_tech_parameter.csv`** — cost parameters per technology/year/scenario

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `tech_id` | str | ✅ | e.g., "TECH006" |
| `year` | int | ✅ | Reference year (2023, 2030) |
| `parameter` | str | ✅ | `capex` / `fixed_om` / `lifetime` |
| `value_type` | str | ✅ | `central` / `lower` / `upper` |
| `value` | float | ✅ | Numeric value |
| `unit` | str | ✅ | `MUSD_per_MWe` / `USD_per_kW_yr` / `years` |
| `source_pdf` | str | ✅ | PDF filename |
| `source_page` | int | ✅ | Page number (0 = pending verification) |

**TECH006 central values (2023):**

| Parameter | Raw value | Unit | Converted | Notes |
|-----------|-----------|------|-----------|-------|
| `capex` | 0.96 | MUSD/MWe | 960 USD/kW | × 1,000 |
| `fixed_om` | 7,500 | USD/MWe/yr | 7.5 USD/kW/yr | ÷ 1,000 |
| `lifetime` | 27 | years | 27 yr | — |

**✅ VERIFIED** — Source: ESDM Technology Catalogue 2023, p.66 (PV ground-mounted, utility-scale). Stored as `VERIFIED_TECH006_DATA` in `src/pipeline/pdf_extract_esdm_tech.py`.

---

## 1.6 Global Solar Atlas GeoTIFF (zipped)

**Source:** World Bank / Solargis Global Solar Atlas v2 — Long-Term Average (LTAym)
**Files:** `data/Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip`
**CRS:** WGS84 (EPSG:4326)

| Layer | Unit | Status | Notes |
|-------|------|--------|-------|
| PVOUT | kWh/kWp/**day** | ✅ | **DAILY average** — must multiply by 365 before use |
| GHI | kWh/m²/yr | ✅ | Secondary; not used in model |

**Critical unit note:** The filename says `AvgDailyTotals` — the raster value is **daily** (e.g., 4.3 kWh/kWp/day), not annual. Multiplying by 365 gives ~1,570 kWh/kWp/yr (plausible for Indonesia). Forgetting this gives CF ≈ 0.05% and LCOE in the thousands. The `pvout_daily_to_annual()` function in `basic_model.py` validates the result is within [1,200, 2,200] kWh/kWp/yr.

---

## 1.7 `docs/Permen ESDM Nomor 7 Tahun 2024.pdf`

**Source:** Ministry of Energy regulation, effective 10 June 2024 — Lampiran IV (Industrial tariffs)
**Usage:** Hardcoded into `src/assumptions.py` and `build_fct_grid_cost_proxy.py`

| Field | Value | Notes |
|-------|-------|-------|
| I-3/TM LWBP | 1,035.78 Rp/kWh | Medium voltage off-peak energy charge |
| I-4/TT | 996.74 Rp/kWh | High voltage, WBP = LWBP (no peak surcharge) |

Both rates are **uniform nationwide** — they do not vary by PLN grid system.
I-4/TT is used as the primary dashboard comparator (`dashboard_rate_usd_mwh`).

---

## 1.8 `docs/b967d-ruptl-pln-2025-2034-pub-.pdf`

**Source:** RUPTL PLN 2025-2034 (Keputusan Menteri ESDM No. 188.K/TL.03/MEM.L/2025)
**Usage:** PLTS capacity additions per region/year, manually transcribed into `build_fct_ruptl_pipeline.py`

| Region | Source tables | Notes |
|--------|--------------|-------|
| JAVA_BALI | Tabel 5.88/5.89 | RE Base + ARED, 2025–2034 |
| SUMATERA | Tabel 5.84/5.85 | ARED ≈ RE Base (uplift is hydro/wind, not solar) |
| KALIMANTAN | Tabel 5.95/5.96 | Includes PLN + SH-PLN + IPP |
| SULAWESI | Tabel 5.102/5.103 | PLTS+BESS packages |
| MALUKU / PAPUA / NTB | Various | All zero in DMN solar tables |

---

## 1.9 `data/substation.geojson`

**Source:** PLN substation network
**Rows:** 2,913 point features

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `namobj` | str | ✅ | Substation name |
| `kapgi` | float | ✅ | Capacity (MVA) |
| `teggi` | str | ✅ | Voltage (e.g., "150 kV") |
| `statopr` | str | ✅ | Status — filter to "Operasi" |
| `geometry` | Point | ✅ | Location |

**Usage:** Source for `fct_substation_proximity.csv` — `dist_to_nearest_substation_km`, `has_internal_substation`, `siting_scenario` per KEK. Filter to `statopr == "Operasi"` before use. ✅

---

# Part 2 — Dimension Tables

Dimension tables describe *what a KEK is* or *what a technology costs*. They are built once and referenced by all fact tables.

---

## 2.1 `outputs/data/processed/dim_kek.csv`

**What it is:** Master KEK list — identity, location, grid assignment, reliability requirement.
**Builder:** `src/pipeline/build_dim_kek.py`
**Lineage:** `kek_info_and_markers.csv` + `kek_distribution_points.csv` + `kek_polygons.geojson` + `kek_grid_region_mapping.csv`
**Rows:** 25 ✅

**Build logic:**
1. Join markers + distribution points on `xid`
2. Join polygons on `slug` — take largest `Luas_ha` per KEK (dedup sub-zones)
3. Join grid mapping on `slug`
4. Extract province from `address` text

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `kek_id` | str | `slug` from markers | Stable URL slug used as primary key throughout pipeline |
| `kek_name` | str | `title` from markers | Full display name |
| `province` | str | extracted from `address` | Province name |
| `grid_region_id` | str | `kek_grid_region_mapping.csv` | PLN grid system (JAVA_BALI, SUMATERA, etc.) |
| `kek_type` | str | `JenisKEK` from polygons | Zone sector type (Industri / Pariwisata / Jasa lainnya / etc.) |
| `category` | str | `category.name` from distribution points | Category string |
| `status` | str | `status.name` from distribution points | Operational status (Active / Construction / Planned) |
| `area_ha` | float | `Luas_ha` from polygons | Total declared zone area in hectares |
| `legal_basis` | str | `legalBasis` from markers | Government decree reference |
| `developer` | str | `developer` from markers | Developer entity name |
| `reliability_req` | float | `kek_grid_region_mapping.csv` | Minimum reliability (0–1). Manufacturing=0.8, Service=0.6 |
| `reliability_notes` | str | `kek_grid_region_mapping.csv` | Rationale |
| `latitude` | float | markers | Centroid latitude |
| `longitude` | float | markers | Centroid longitude |
| `data_vintage` | str | pipeline run date | ISO date of last scrape |

---

## 2.2 `outputs/data/processed/dim_tech_cost.csv`

**What it is:** Solar PV cost parameters for TECH006 (utility-scale ground-mounted), unit-converted and ready for LCOE formula.
**Builder:** `src/pipeline/build_dim_tech_cost.py`
**Lineage:** `data/dim_tech_variant.csv` + `data/fct_tech_parameter.csv`
**Rows:** 1 ✅

**Build logic:** Filter `fct_tech_parameter` to `tech_id=TECH006`, `year=2023`. Pivot wide on `value_type`. Apply unit conversions:
- CAPEX: `MUSD/MWe × 1,000 = USD/kW`
- Fixed O&M: already in `USD/kW/yr` (verify units field)
- `is_provisional=True` when `source_page=0`

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `tech_id` | str | dim_tech_variant | "TECH006" |
| `tech_description` | str | dim_tech_variant | "PV ground-mounted, utility-scale, grid connected" |
| `year` | int | fct_tech_parameter | 2023 |
| `capex_usd_per_kw` | float | fct_tech_parameter | `central CAPEX × 1,000` (MUSD/MWe → USD/kW) |
| `capex_lower_usd_per_kw` | float | fct_tech_parameter | `lower CAPEX × 1,000` |
| `capex_upper_usd_per_kw` | float | fct_tech_parameter | `upper CAPEX × 1,000` |
| `fixed_om_usd_per_kw_yr` | float | fct_tech_parameter | Central fixed O&M (USD/kW/yr) |
| `lifetime_yr` | int | fct_tech_parameter | Asset lifetime (years) |
| `source_pdf` | str | fct_tech_parameter | PDF provenance passthrough |
| `source_page` | int | fct_tech_parameter | 0 = pending PDF verification |
| `is_provisional` | bool | derived | `True` when `source_page == 0` |

---

# Part 3 — Fact Tables

Fact tables describe *what a KEK has* — resource quality, demand, cost, scorecard. Each has a lineage block and explicit formulas for derived columns.

---

## 3.1 `outputs/data/processed/fct_kek_resource.csv`

**What it is:** Solar resource quality per KEK — PVOUT at centroid and best-within-50km, capacity factors.
**Builder:** `src/pipeline/build_fct_kek_resource.py`
**Lineage:** `dim_kek.csv` (centroid coords) + Global Solar Atlas GeoTIFF (PVOUT raster)
**Rows:** 25 ✅

**Build logic:**
1. For each KEK centroid, sample the PVOUT GeoTIFF pixel
2. Search a 50km radius (latitude-corrected: `km / 111.32 = degrees`) for the maximum PVOUT pixel
3. Convert daily → annual: `pvout_daily × 365`
4. Compute CF: `pvout_annual / 8760`

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `kek_id` | str | dim_kek | Join key |
| `kek_name` | str | dim_kek | Display name |
| `latitude` | float | dim_kek | Centroid latitude |
| `longitude` | float | dim_kek | Centroid longitude |
| `pvout_daily_centroid` | float | GeoTIFF | Raw pixel value at centroid (kWh/kWp/day) — audit trail |
| `pvout_centroid` | float | computed | `pvout_daily_centroid × 365` (kWh/kWp/yr) |
| `cf_centroid` | float | computed | `pvout_centroid / 8760` |
| `pvout_daily_best_50km` | float | GeoTIFF | Max pixel within 50km radius (kWh/kWp/day) — audit trail |
| `pvout_best_50km` | float | computed | `pvout_daily_best_50km × 365` (kWh/kWp/yr) |
| `cf_best_50km` | float | computed | `pvout_best_50km / 8760` |
| `pvout_source` | str | constant | "GlobalSolarAtlas-v2" |
| `pvout_buildable_best_50km` | float | computed | Max PVOUT within 50km after 4-layer buildability filter. NaN when `data/buildability/` files absent. |
| `buildable_area_ha` | float | computed | Total buildable area in 50km radius after all filters (ha). NaN when data absent. |
| `max_captive_capacity_mwp` | float | computed | `buildable_area_ha / 1.5` — max captive solar capacity (MWp). 1.5 ha/MWp for tropical fixed-tilt. |
| `buildability_constraint` | str | computed | Dominant binding constraint: `"kawasan_hutan"` \| `"slope"` \| `"peat"` \| `"land_cover"` \| `"area_too_small"` \| `"unconstrained"` \| `"data_unavailable"`. `"land_cover"` = ESA WorldCover layer (tree cover/forest, cropland, urban, water, wetland, mangrove) — dominant at all 25 KEKs because Indonesian forest cover is pervasive (60–93% of pixels removed). Peat and kawasan_hutan layers are also active and removing pixels but are numerically smaller than land cover. |

**Note:** `pvout_best_50km` is an upper bound — raw raster max with no buildability filter.
`pvout_buildable_best_50km` applies Layers 1–4 (METHODOLOGY.md §2.5) and is the
preferred value for LCOE when data is available. Until `data/buildability/` is populated,
both columns are available but `pvout_buildable_best_50km = NaN` and the pipeline
falls back to `pvout_best_50km`. Run `scripts/download_buildability_data.py` to acquire data.

---

## 3.2 `outputs/data/processed/fct_kek_demand.csv`

**What it is:** Estimated 2030 electricity demand per KEK, derived from zone area and sector intensity.
**Builder:** `src/pipeline/build_fct_kek_demand.py`
**Lineage:** `dim_kek.csv` (area_ha, kek_type) + `src/assumptions.py` (intensity constants)
**Rows:** 25 ✅

**Build logic:**
```
energy_intensity_mwh_per_ha_yr = building_intensity_kwh_m2 × footprint_ratio × 10
demand_mwh = area_ha × energy_intensity_mwh_per_ha_yr
```

Intensity constants by `kek_type` (from `src/assumptions.py`):

| kek_type | building_intensity (kWh/m²/yr) | footprint_ratio | derived intensity (MWh/ha/yr) |
|----------|-------------------------------|-----------------|-------------------------------|
| Industri | 120 | 0.55 | 660 |
| Industri dan Pariwisata | 184 | 0.40 | 736 |
| Pariwisata | 280 | 0.18 | 504 |
| Jasa lainnya | 200 | 0.40 | 800 |
| (unknown) | — | — | 675 (average fallback) |

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `kek_id` | str | dim_kek | Primary key |
| `year` | int | constant | 2030 (demand target year) |
| `area_ha` | float | kek_polygons.geojson via dim_kek | Total declared zone area |
| `kek_type` | str | dim_kek | Zone sector type |
| `energy_intensity_mwh_per_ha_yr` | float | assumptions.py | `building_intensity_kwh_m2 × footprint_ratio × 10` |
| `demand_mwh` | float | computed | `area_ha × energy_intensity_mwh_per_ha_yr` |
| `demand_mwh_user` | Float64 (nullable) | user input | Override value; `null` = use model default. Set by Dash app or analyst. |
| `demand_source` | str | computed | `"area_x_intensity"` or `"area_fallback_median"` (when area_ha was imputed) |
| `is_demand_provisional` | bool | constant | Always `True` — placeholder until real tenant load surveys available |

**Override contract:** Call `resolve_demand(fct_demand)` from `src/model/basic_model.py` before passing demand anywhere. It coalesces: when `demand_mwh_user` is non-null, it replaces `demand_mwh`. The Dash app populates `demand_mwh_user` from user input fields; the pipeline leaves it null.

---

## 3.3 `outputs/data/processed/fct_grid_cost_proxy.csv`

**What it is:** Grid reference electricity cost per PLN system — used to assess whether solar LCOE is competitive.
**Builder:** `src/pipeline/build_fct_grid_cost_proxy.py`
**Lineage:** `dim_kek.csv` (grid_region_id list) + hardcoded tariffs from Permen ESDM 7/2024
**Rows:** 7 (one per PLN grid system) ✅

**Build logic:** I-4/TT tariff is uniform nationwide (same value for all regions). BPP Pembangkitan (generation cost of supply) is sourced per region from Kepmen ESDM 169/2021 via `src/pipeline/pdf_extract_bpp.py`.

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `grid_region_id` | str | dim_kek | PLN grid system |
| `tariff_i3_rp_kwh` | float | Permen ESDM 7/2024 p.14 | I-3/TM LWBP energy charge = 1,035.78 Rp/kWh |
| `tariff_i4_rp_kwh` | float | Permen ESDM 7/2024 p.14 | I-4/TT energy charge = 996.74 Rp/kWh |
| `idr_usd_rate` | float | assumptions.py | IDR/USD rate used for conversion (15,800) |
| `tariff_i3_usd_mwh` | float | computed | `tariff_i3_rp_kwh × 1,000 / idr_usd_rate` = ~65.56 USD/MWh |
| `tariff_i4_usd_mwh` | float | computed | `tariff_i4_rp_kwh × 1,000 / idr_usd_rate` = ~63.08 USD/MWh |
| `dashboard_rate_usd_mwh` | float | derived | `= tariff_i4_usd_mwh` — primary dashboard comparator |
| `dashboard_rate_label` | str | constant | "I-4/TT LWBP, Permen ESDM No.7/2024" |
| `dashboard_rate_flag` | str | constant | "OFFICIAL" (not provisional) |
| `bpp_rp_kwh` | float | Kepmen ESDM 169/2021 | BPP Pembangkitan per region in Rp/kWh (simple avg of subsystems) |
| `bpp_usd_mwh` | float | computed | `bpp_rp_kwh × 1,000 / idr_usd_rate` — regional generation cost in USD/MWh |
| `bpp_source` | str | constant | "Kepmen ESDM 169/2021, BPP Pembangkitan FY2020" |
| `grid_emission_factor_t_co2_mwh` | float | KESDM 2019 Tier 2 OM | Grid emission factor by region (tCO2/MWh) |
| `notes` | str | constant | Caveats (peak multiplier for I-3, BPP vintage, emission factor source) |

**BPP vs tariff distinction:** `dashboard_rate_usd_mwh` is the industrial tariff paid by KEK tenants. `bpp_usd_mwh` is PLN's generation cost of supply (BPP Pembangkitan, Kepmen ESDM 169/2021, FY2020). BPP varies dramatically by region: Java-Bali ~$57/MWh (coal-heavy) vs Papua ~$133/MWh (diesel-heavy). This is **generation BPP only**, not full cost-of-supply BPP (which includes T&D + overhead, ~1,599 Rp/kWh per BPK audit). Generation BPP is the appropriate comparator for solar LCOE since solar also excludes T&D costs.

---

## 3.4 `outputs/data/processed/fct_ruptl_pipeline.csv`

**What it is:** PLTS (solar) capacity additions planned by PLN grid system and year, from RUPTL 2025–2034. Used to assess grid readiness and compute GEAS green share.
**Builder:** `src/pipeline/build_fct_ruptl_pipeline.py`
**Lineage:** `docs/b967d-ruptl-pln-2025-2034-pub-.pdf` (manually transcribed)
**Rows:** 70 (7 regions × 10 years) ✅

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `grid_region_id` | str | RUPTL | PLN grid system |
| `year` | int | RUPTL | Calendar year (2025–2034) |
| `plts_new_mw_re_base` | float | RUPTL | New solar additions (MW) in RE Base scenario |
| `plts_new_mw_ared` | float | RUPTL | New solar additions (MW) in ARED accelerated scenario |
| `plts_cumul_re_base` | float | computed | `cumsum(plts_new_mw_re_base)` per region from 2025 |
| `plts_cumul_ared` | float | computed | `cumsum(plts_new_mw_ared)` per region from 2025 |
| `ruptl_source_table` | str | manual | PDF table number (e.g., "Tabel 5.88/5.89") |
| `notes` | str | manual | Data quality flags per region |

**Derived metrics** (computed in `build_fct_kek_scorecard.py` via `ruptl_region_metrics()`):

| Derived field | Formula |
|---------------|---------|
| `pre2030_solar_mw` | `sum(plts_new_mw_re_base where year ≤ 2030)` per region |
| `post2030_share` | `post2030_mw / (pre2030_mw + post2030_mw)` per region |
| `grid_upgrade_pre2030` | `True if pre2030_solar_mw > 0` |
| `earliest_grid_upgrade_year` | `min(year where plts_new_mw_re_base > 0)` per region |

---

## 3.4b `outputs/data/processed/fct_substation_proximity.csv`

**What it is:** Nearest operational PLN substation per KEK — distance, connection details, siting scenario, and V2 three-point proximity analysis (grid integration category).
**Builder:** `src/pipeline/build_fct_substation_proximity.py`
**Lineage:** `dim_kek.csv` + `data/substation.geojson` + `outputs/data/raw/kek_polygons.geojson` + `fct_kek_resource.csv` (best solar site lat/lon)
**Rows:** 25 ✅

**Build logic:**
1. Filter substations to `statopr == "Operasi"` (operational only)
2. Haversine distance from each KEK centroid to every substation → take nearest
3. Point-in-polygon (shapely) for each KEK polygon → `has_internal_substation`
4. `siting_scenario = "within_boundary"` if `has_internal_substation` else `"remote_captive"` (V1 compat)
5. V2: Haversine from best solar site to nearest substation → `dist_solar_to_nearest_substation_km`
6. V2: `grid_integration_category` derived from three-point proximity thresholds (see METHODOLOGY_V2.md §2)

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `kek_id` | str | dim_kek | Join key |
| `kek_name` | str | dim_kek | Display name |
| `nearest_substation_name` | str | substation.geojson `namobj` | Name of nearest operational substation |
| `nearest_substation_voltage_kv` | str | substation.geojson `teggi` | e.g. "150 kV" |
| `nearest_substation_capacity_mva` | float | substation.geojson `kapgi` | Substation capacity (MVA). Source `kapgi` field has mixed units — values ≥ 10,000 are in VA (divided by 1,000,000); values 1–9,999 are already in MVA. Normalization via `_normalize_capacity_mva()`. 19/25 KEKs populated; 6 null (not recorded in PLN dataset). |
| `dist_to_nearest_substation_km` | float | computed | ✅ Haversine distance from KEK centroid to nearest operational substation, 2 decimals |
| `has_internal_substation` | bool | computed | True if any operational substation is inside the KEK polygon |
| `siting_scenario` | str | derived | `"within_boundary"` or `"remote_captive"` (V1 compat) |
| `dist_solar_to_nearest_substation_km` | float | computed | ✅ V2: Haversine from best solar site to nearest substation. NaN if solar coords unavailable. |
| `nearest_substation_to_solar_name` | str | computed | ✅ V2: Name of nearest substation to the solar site |
| `grid_integration_category` | str | computed | ✅ V2: `within_boundary` / `grid_ready` / `invest_grid` / `grid_first` — see METHODOLOGY_V2.md §2 |

---

## 3.5 `outputs/data/processed/fct_lcoe.csv`

**What it is:** Precomputed LCOE bands per KEK at 9 WACC values (4–20% in 2% steps) and 2 siting scenarios (within_boundary / grid_connected_solar). V2: replaces remote_captive with grid-connected solar; uses solar-to-substation distance; removes transmission lease adder.
**Builder:** `src/pipeline/build_fct_lcoe.py`
**Lineage:** `dim_kek.csv` + `fct_kek_resource.csv` (PVOUT) + `dim_tech_cost.csv` (CAPEX, FOM, lifetime) + `fct_substation_proximity.csv` (solar-to-substation distance)
**Rows:** 450 (25 KEKs × 9 WACC values × 2 scenarios) ✅

**Siting scenarios:**
- `within_boundary` — plant on KEK land; uses `pvout_centroid`; `connection_cost_per_kw = 0`
- `grid_connected_solar` — IPP solar connects to nearest PLN substation; uses `pvout_best_50km`; connection cost based on `dist_solar_to_nearest_substation_km`

**LCOE formula** (`src/model/basic_model.py → lcoe_solar()`):
```
connection_cost  = dist_km × CONNECTION_COST_PER_KW_KM + GRID_CONNECTION_FIXED_PER_KW  (grid_connected_solar only)
effective_capex  = capex + connection_cost
CRF              = wacc × (1 + wacc)^n / ((1 + wacc)^n − 1)
LCOE             = (effective_capex × CRF + FOM) / (CF × 8.76)
```

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `kek_id` | str | dim_kek | Join key |
| `wacc_pct` | float | assumptions.py | 4.0 / 6.0 / 8.0 / 10.0 / 12.0 / 14.0 / 16.0 / 18.0 / 20.0 |
| `scenario` | str | derived | `"within_boundary"` or `"grid_connected_solar"` |
| `pvout_used` | str | derived | `"pvout_centroid"` or `"pvout_best_50km"` |
| `cf_used` | float | fct_kek_resource | PVOUT / 8760; fallback to centroid if best_50km NaN |
| `connection_cost_per_kw` | float | computed | 0 for within_boundary; `dist_km × $5/kW-km + $80/kW` for grid_connected_solar |
| `effective_capex_usd_per_kw` | float | computed | `capex_central + connection_cost_per_kw` |
| `lcoe_usd_mwh` | float | computed | `lcoe_solar(effective_capex_central, fom, wacc/100, lifetime, cf)` |
| `lcoe_low_usd_mwh` | float | computed | `lcoe_solar(effective_capex_lower, ...)` |
| `lcoe_high_usd_mwh` | float | computed | `lcoe_solar(effective_capex_upper, ...)` |
| `is_cf_provisional` | bool | derived | `True` if centroid fallback was used for grid_connected_solar |
| `is_capex_provisional` | bool | dim_tech_cost | Propagated from `dim_tech_cost.is_provisional` |
| `tech_id` | str | dim_tech_cost | "TECH006" |
| `lifetime_yr` | int | dim_tech_cost | Asset lifetime |

---

## 3.6 `outputs/data/processed/fct_kek_scorecard.csv`

**What it is:** Dashboard-ready summary. One row per KEK — joins all upstream tables, computes action flags, GEAS green share, and competitive gap.
**Builder:** `src/pipeline/build_fct_kek_scorecard.py`
**Lineage:** `dim_kek.csv` + `fct_lcoe.csv` (wacc=10% rows) + `fct_kek_resource.csv` + `fct_kek_demand.csv` + `fct_grid_cost_proxy.csv` + `fct_ruptl_pipeline.csv`
**Rows:** 25 ✅

**Build logic:**
1. Filter `fct_lcoe` to `wacc_pct = 10.0` AND `scenario = "within_boundary"` — base case LCOE (on-site solar, no gen-tie)
2. Load `fct_kek_demand`, call `resolve_demand()` to apply any user overrides
3. Compute `ruptl_region_metrics()` → `post2030_share`, `grid_upgrade_pre2030`
4. Compute `geas_baseline_allocation()` → `green_share_geas`
5. Compute action flags per KEK from `action_flags()`

**Identity columns** (passed through from dim_kek):

| Column | Source |
|--------|--------|
| `kek_id`, `kek_name`, `province`, `grid_region_id`, `kek_type`, `status` | dim_kek |
| `latitude`, `longitude` | dim_kek |

**Resource columns** (from fct_kek_resource):
| `pvout_buildable_best_50km` | fct_kek_resource | NaN until data/buildability/ populated |
| `buildable_area_ha` | fct_kek_resource | NaN until data/buildability/ populated |
| `max_captive_capacity_mwp` | fct_kek_resource | NaN until data/buildability/ populated |
| `buildability_constraint` | fct_kek_resource | "data_unavailable" until populated |
| `resource_quality` | derived | `"filtered"` when buildable data applied; else `"provisional (no buildability filter)"` |


| Column | Source |
|--------|--------|
| `pvout_centroid`, `cf_centroid` | fct_kek_resource |
| `pvout_best_50km`, `cf_best_50km` | fct_kek_resource |

**LCOE columns** (from fct_lcoe at wacc=10%):

| Column | Source | Notes |
|--------|--------|-------|
| `lcoe_low_usd_mwh` | fct_lcoe | `lcoe_solar(capex_lower, fom, 0.10, lifetime, cf)` |
| `lcoe_mid_usd_mwh` | fct_lcoe | `lcoe_solar(capex_central, fom, 0.10, lifetime, cf)` |
| `lcoe_high_usd_mwh` | fct_lcoe | `lcoe_solar(capex_upper, fom, 0.10, lifetime, cf)` |
| `cf_used` | fct_lcoe | CF used in LCOE calc |
| `is_cf_provisional` | fct_lcoe | True if centroid fallback |
| `is_capex_provisional` | fct_lcoe | False — TECH006 verified from `docs/esdm_technology_cost.pdf` p.66 |

**Grid cost columns** (from fct_grid_cost_proxy):

| Column | Value | Source |
|--------|-------|--------|
| `dashboard_rate_usd_mwh` | ~63.08 | I-4/TT tariff converted to USD/MWh |
| `dashboard_rate_label` | "I-4/TT LWBP, Permen ESDM No.7/2024" | fct_grid_cost_proxy |
| `is_grid_cost_provisional` | False | OFFICIAL |
| `tariff_i3_usd_mwh`, `tariff_i4_usd_mwh` | ~65.56 / ~63.08 | Reference tariffs |

**Computed columns:**

| Column | Type | Formula |
|--------|------|---------|
| `solar_competitive_gap_pct` | float | `(lcoe_mid_usd_mwh − dashboard_rate_usd_mwh) / dashboard_rate_usd_mwh × 100`. Negative = solar already cheaper than grid. Base case WACC=10%. |
| `solar_attractive` | bool | `pvout_best_50km ≥ 1,550 kWh/kWp/yr AND lcoe_mid_usd_mwh ≤ dashboard_rate_usd_mwh` |
| `lcoe_mid_wacc8_usd_mwh` | float | LCOE at WACC=8% (de-risked finance scenario), within_boundary. Sourced from `fct_lcoe.csv` at `wacc_pct=8`. |
| `solar_competitive_gap_wacc8_pct` | float | Same formula as `solar_competitive_gap_pct` but using `lcoe_mid_wacc8_usd_mwh`. Negative = solar competitive under de-risked financing. |
| `solar_now_at_wacc8` | bool | `lcoe_mid_wacc8_usd_mwh ≤ dashboard_rate_usd_mwh` — True for 8 KEKs. The "what does a green finance facility unlock?" signal for DFI analysts. |
| `lcoe_grid_connected_usd_mwh` | float | V2: LCOE for `grid_connected_solar` scenario at `BASE_WACC=10%` — includes connection cost (solar→substation distance × $5/kW-km + $80/kW fixed). |
| `lcoe_grid_connected_low_usd_mwh` | float | Same using `capex_lower`. |
| `lcoe_grid_connected_high_usd_mwh` | float | Same using `capex_upper`. |
| `connection_cost_per_kw` | float | V2: Grid connection cost per kW for this KEK's solar site. 0 for within_boundary. |
| `grid_integration_category` | str | V2: `within_boundary` / `grid_ready` / `invest_grid` / `grid_first` — from fct_substation_proximity. |
| `project_viable` | bool | `max_captive_capacity_mwp ≥ PROJECT_VIABLE_MIN_MWP (20 MWp)`. True = minimum viable IPP project size met. All 25 KEKs = True at current 1km buildability resolution. DFI threshold is stricter (≥ 33 MWp / ≥ 50 ha). |
| `clean_power_advantage` | float | `−solar_competitive_gap_pct` — higher = more competitive |
| `green_share_geas` | float | Pro-rata share of 2030 demand covered by pre-2030 RUPTL solar. Formula: `min(1, (pre2030_mw × 8760 × 0.20 × kek_demand_share) / kek_demand_mwh)`. See `geas_baseline_allocation()`. |
| `pre2030_solar_mw` | float | `sum(plts_new_mw_re_base where year ≤ 2030)` for this KEK's region |
| `post2030_share` | float | `post2030_mw / total_ruptl_mw` for this region. ≥ 0.60 triggers `plan_late`. |
| `grid_upgrade_pre2030` | bool | `True if pre2030_solar_mw > 0` |
| `ruptl_summary` | str | `"{pre2030_solar_mw} MW solar planned in {region} by 2030"` |

**Action flag columns** (from `action_flags()` + `invest_resilience()` in `basic_model.py`):

| Flag | Formula |
|------|---------|
| `solar_attractive` | `pvout_best_50km ≥ 1,550 AND lcoe_mid ≤ dashboard_rate` |
| `solar_now` | `solar_attractive AND grid_upgrade_pre2030 AND green_share_geas ≥ 0.30` |
| `grid_first` | `solar_attractive AND NOT grid_upgrade_pre2030` |
| `firming_needed` | `solar_attractive AND reliability_req ≥ 0.75` |
| `invest_resilience` | `0 < solar_competitive_gap_pct ≤ 20 AND reliability_req ≥ 0.75` — solar slightly above grid cost but manufacturing reliability justifies the premium |
| `plan_late` | `post2030_share ≥ 0.60` |
| `action_flag` | Summary string: first true flag (priority: solar_now > grid_first > firming_needed > invest_resilience > plan_late); `"not_competitive"` if data complete but LCOE > grid; `"data_missing"` if required inputs are NaN |

**Resilience + carbon columns:**

| Column | Type | Formula |
|--------|------|---------|
| `grid_emission_factor_t_co2_mwh` | float | Grid emission intensity (tCO2/MWh) from `GRID_EMISSION_FACTOR_T_CO2_MWH[grid_region_id]` — Operating Margin (OM) values from KESDM Tier 2 database 2019 (`data/grid_emission_factors.xlsx`). ⚠️ 2019 vintage. |
| `carbon_breakeven_usd_tco2` | float | `max(0, lcoe_gap_usd_mwh) / grid_emission_factor` — carbon price (USD/tCO2) at which solar becomes cost-competitive. 0.0 if already competitive. |

**Data quality column:**

| Column | Type | Formula |
|--------|------|---------|
| `data_completeness` | str | `"complete"` if no null key columns and `is_capex_provisional=False`. `"provisional"` if `is_capex_provisional=True`. `"partial"` if key columns are null. |

---

## Open Questions

1. **BPP data** — ✅ Regional BPP Pembangkitan sourced from Kepmen ESDM 169/2021 (FY2020). `bpp_usd_mwh` populated for all 7 grid regions via `src/pipeline/pdf_extract_bpp.py`. Vintage: FY2020, valid until superseded.

2. ✅ **TECH006 CAPEX verified** — extracted from `docs/esdm_technology_cost.pdf` p.66. `source_page=66`, `is_capex_provisional=False` across all LCOE and scorecard rows. Values: CAPEX=$960/kW, FOM=$7.5/kW/yr, lifetime=27yr.

3. **Landcover buildability filter** — `pvout_best_50km` is currently an upper bound with no exclusion of forests, peat, protected areas. Planned for v1.1: 4-layer filter (HCS/HCV, peatland, protected areas, slope > 15°).

4. **Substation proximity** — ✅ Implemented in Phase 2. `fct_substation_proximity.csv` computes `dist_to_nearest_substation_km` and `siting_scenario` per KEK. Gen-tie cost adder integrated into `fct_lcoe.csv` remote_captive scenario.
