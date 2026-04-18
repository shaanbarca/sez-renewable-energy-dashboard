# Data Dictionary — Indonesia Industrial Decarbonization

Contract for the data pipeline. Three parts:

- **Part 1 — Raw inputs**: source, format, and column status for every input file
- **Part 2 — Dimension tables**: one row per entity (site, technology)
- **Part 3 — Fact tables**: computed outputs, with lineage and formulas for every derived column

**Status legend:** ✅ available | ⚠️ partial/needs cleaning | ❌ missing | 🔒 manual (human required)

**Scope:** 79 sites total — 25 KEKs (Special Economic Zones) + 54 industrial sites (32 cement, 17 steel, 2 aluminium, 3 fertilizer, 10 nickel IIA clusters). Industrial site selection is pipeline-driven and reproducible from public trackers (GEM Cement, GEM Iron & Steel, CGSP Nickel) with residual manual entries (2 aluminium + 3 fertilizer = 5 rows) provenance-enforced via required `source_url`. Ammonia + petrochemical sector scaffolding is in place (enum, intensity, CBAM constants) pending top-down universe discovery (TODOS M28/M29). The unified dimension table is `dim_sites` keyed on `site_id`; `site_type` discriminates KEK vs KI vs standalone vs cluster behavior across the pipeline.

---

## Table of Contents

- [Table Index](#table-index) — all 14 output tables at a glance
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
  - [1.10 priority1_sites.csv](#110-dataindustrial_sitespriority1_sitescsv)
- [Part 2 — Dimension Tables](#part-2--dimension-tables)
  - [2.1 dim_sites](#21-outputsdataprocesseddim_sitescsv)
  - [2.2 dim_tech_cost](#22-outputsdataprocesseddim_tech_costcsv)
- [Part 3 — Fact Tables](#part-3--fact-tables)
  - [3.1 fct_site_resource](#31-outputsdataprocessedfct_site_resourcecsv)
  - [3.2 fct_site_demand](#32-outputsdataprocessedfct_site_demandcsv)
  - [3.3 fct_grid_cost_proxy](#33-outputsdataprocessedfct_grid_cost_proxycsv)
  - [3.4 fct_ruptl_pipeline](#34-outputsdataprocessedfct_ruptl_pipelinecsv)
  - [3.4b fct_substation_proximity](#34b-outputsdataprocessedfct_substation_proximitycsv)
  - [3.5 fct_lcoe](#35-outputsdataprocessedfct_lcoecsv)
  - [3.6 fct_site_scorecard](#36-outputsdataprocessedfct_site_scorecardcsv)
  - [3.7 fct_captive_coal_summary](#37-outputsdataprocessedfct_captive_coal_summarycsv)
  - [3.8 fct_captive_nickel_summary](#38-outputsdataprocessedfct_captive_nickel_summarycsv)
  - [3.9 fct_captive_steel_summary](#39-outputsdataprocessedfct_captive_steel_summarycsv)
  - [3.10 fct_captive_cement_summary](#310-outputsdataprocessedfct_captive_cement_summarycsv)
  - [3.11 fct_site_wind_resource](#311-outputsdataprocessedfct_site_wind_resourcecsv)
- [Open Questions](#open-questions)

---

## Table Index

All processed output tables. Click a table name to jump to its full column spec.

| Table | Type | Rows | What it contains | Built from | Used for | Status |
|-------|------|------|------------------|------------|----------|--------|
| [dim_sites](#21-outputsdataprocesseddim_sitescsv) | dim | 79 | Master site list (25 KEK + 44 standalone + 10 cluster): name, site_type, sector, province, grid region, lat/lon, area, reliability req, product/capacity/technology/parent. Industrial rows built pipeline-first from GEM Cement + GEM Steel + CGSP Nickel IIA trackers; residual CSV holds 5 manual rows (2 aluminium + 3 fertilizer) with required provenance columns. | `kek_info_and_markers.csv` · `kek_distribution_points.csv` · `kek_polygons.geojson` · `kek_grid_region_mapping.csv` · `data/captive_power/gem_cement_plants.csv` · `data/captive_power/gem_steel_plants.csv` · `data/nickel/cgsp_nickel_projects.csv` · `data/industrial_sites/priority1_sites.csv` | The master reference for every site. Every fact table joins to this on `site_id`. Drives map layer + site-type dispatch throughout pipeline. | ✅ |
| [dim_tech_cost](#22-outputsdataprocesseddim_tech_costcsv) | dim | 1 | TECH006 solar PV CAPEX / FOM / lifetime, unit-converted for LCOE formula | `dim_tech_variant.csv` · `fct_tech_parameter.csv` | Holds the cost assumptions (CAPEX, fixed O&M, asset lifetime) that are plugged into the LCOE formula. Changing these numbers here flows through to all LCOE rows automatically. | ✅ Verified from ESDM Tech Catalogue 2023 p.66 |
| [fct_site_resource](#31-outputsdataprocessedfct_site_resourcecsv) | fact | 79 | PVOUT at centroid + best-within-50km; capacity factors; buildability columns (NaN until `data/buildability/` populated) | `dim_sites` · Global Solar Atlas GeoTIFF · optional: `data/buildability/` | Answers "how much sun does each site get?" — and (when data available) "how much of that land is actually buildable?". | ⚠️ `pvout_buildable_best_50km` NaN until data/buildability/ populated (run `scripts/download_buildability_data.py`) |
| [fct_site_demand](#32-outputsdataprocessedfct_site_demandcsv) | fact | 79 | Estimated 2030 electricity demand per site — dual-mode: area × intensity (KEK/KI) OR capacity_tpa × sector_intensity (standalone/cluster) | `dim_sites` · `src/pipeline/demand_intensity.py` · `src/assumptions.py` | Answers "how much electricity will this site need by 2030?" — used for GEAS share, BESS sizing, infrastructure needs. Dual-mode dispatches via `SITE_TYPES[site_type].demand_method`. | ⚠️ Provisional — area-proxy for KEKs; production-based for industrial sites |
| [fct_grid_cost_proxy](#33-outputsdataprocessedfct_grid_cost_proxycsv) | fact | 7 | I-4/TT and I-3/TM industrial tariffs per PLN grid system (USD/MWh) | `dim_sites` (grid_region_id list) · Permen ESDM 7/2024 (hardcoded tariffs) | The benchmark each site's solar LCOE is compared against. If solar LCOE < grid tariff, captive solar is already cost-competitive without any policy support. | ✅ Official — Permen ESDM 7/2024 |
| [fct_ruptl_pipeline](#34-outputsdataprocessedfct_ruptl_pipelinecsv) | fact | 70 | PLN solar capacity additions 2025–2034 by region, RE Base + ARED scenarios | `docs/b967d-ruptl-pln-2025-2034-pub-.pdf` (Tables 5.84–5.103, manually transcribed) | Answers "what grid-scale solar is PLN planning near this site's region?" — used to compute the GEAS green energy share each site can claim, and to flag sites where the grid upgrade comes too late (post-2030). | ✅ Manually verified from RUPTL PDF |
| [fct_substation_proximity](#34b-outputsdataprocessedfct_substation_proximitycsv) | fact | 79 | Nearest PLN substation per site — site-to-substation + solar-to-substation distances, grid connectivity, capacity assessment | `dim_sites` · `data/substation.geojson` · `data/pln_grid_lines.geojson` · `raw/kek_polygons.geojson` · `fct_site_resource` | V3.1: Three-point proximity + geometric grid line connectivity check + substation capacity utilization assessment. Drives connection and transmission cost in `fct_lcoe`. | ✅ |
| [fct_lcoe](#35-outputsdataprocessedfct_lcoecsv) | fact | 1,422 | Precomputed LCOE bands — 79 sites × 9 WACC values (4–20% in 2% steps) × 2 siting scenarios (within_boundary/grid_connected_solar) | `dim_sites` · `fct_site_resource` · `dim_tech_cost` · `fct_substation_proximity` | Powers the WACC slider and scenario comparison. `within_boundary` is base-case; `grid_connected_solar` adds connection cost (solar→substation). Row count is `len(dim_sites) × 9 × 2` — never hardcoded. | ✅ |
| [fct_site_scorecard](#36-outputsdataprocessedfct_site_scorecardcsv) | fact | 79 | Full join: LCOE + grid cost + demand + RUPTL + action flags + competitive gap + captive power + CBAM exposure + site_type/sector | `dim_sites` · `fct_lcoe` (WACC=10%) · `fct_site_resource` · `fct_site_demand` · `fct_grid_cost_proxy` · `fct_ruptl_pipeline` · `fct_captive_{coal,nickel,steel,cement}_summary` | The single table the dashboard reads. For each site: is solar already cheaper than the grid? If not, how close? What action is recommended? What captive fossil power could solar displace? What CBAM exposure? | ⚠️ Provisional until CAPEX verified |
| [fct_captive_coal_summary](#37-outputsdataprocessedfct_captive_coal_summarycsv) | fact | variable | Per-site captive coal plant aggregation — dual-mode: 50km proximity (KEK/KI) OR direct site_id match (standalone/cluster) | `dim_sites` · GEM Global Coal Plant Tracker (KAPSARC mirror) | Identifies sites with existing captive coal subject to Perpres 112/2022 phase-out. Feeds `has_captive_coal` and `perpres_112_status` on scorecard. | ✅ |
| [fct_captive_nickel_summary](#38-outputsdataprocessedfct_captive_nickel_summarycsv) | fact | variable | Per-site nickel smelter aggregation — dual-mode | `dim_sites` · CGSP Nickel Tracker | Identifies sites near nickel processing with high baseload demand. Process type informs BESS sizing requirements. | ✅ |
| [fct_captive_steel_summary](#39-outputsdataprocessedfct_captive_steel_summarycsv) | fact | variable | Per-site steel plant aggregation — dual-mode | `dim_sites` · GEM Steel Tracker | CBAM-exposed steel plants. EAF/BF-BOF technology, Chinese ownership. Feeds Industry tab + sector summary. | ✅ |
| [fct_captive_cement_summary](#310-outputsdataprocessedfct_captive_cement_summarycsv) | fact | variable | Per-site cement plant aggregation — dual-mode | `dim_sites` · GEM Cement Tracker | CBAM-exposed cement plants. High process emissions (0.52 tCO₂/t calcination). Feeds Industry tab + sector summary. | ✅ |
| [fct_site_wind_resource](#311-outputsdataprocessedfct_site_wind_resourcecsv) | fact | 79 | Wind speed, capacity factor, and buildability per site (centroid + best 50km + buildable-area metrics) | `dim_sites` · Global Wind Atlas v3 GeoTIFF · `buildable_wind_web.tif` | Wind analog of `fct_site_resource`. Answers "how much wind does each site get and how much land is buildable for wind?" Feeds wind LCOE and supply coverage. | ✅ |

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

**Usage:** Source for `fct_substation_proximity.csv` — `dist_to_nearest_substation_km`, `has_internal_substation`, `siting_scenario` per site. Filter to `statopr == "Operasi"` before use. ✅

---

## 1.10 `data/industrial_sites/priority1_sites.csv`

**Source:** **Residual manual rows only** — sectors for which no free global tracker exists yet
**Format:** CSV, one row per site
**Rows:** 5 (2 aluminium + 3 fertilizer)

**Reproducibility rule:** Site selection for sectors with available trackers (cement, steel, nickel IIA) is derived programmatically inside `src/pipeline/build_industrial_sites.py` — those rows are NOT in this CSV. This file is the fallback for sectors without a tracker step (currently aluminium and fertilizer). Open tracker integration items: TODOs M25 (aluminium GEM GAST) and M26 (fertilizer).

**Provenance enforcement:** `_load_residual_manual_rows()` raises at pipeline-build time if any row is missing `source_url`. `source_name`, `source_url`, and `retrieved_date` are required columns — not just recommended.

| Column | Type | Status | Notes |
|--------|------|--------|-------|
| `site_id` | str | ✅ | Slug, unique across KEK + industrial (e.g., `inalum-asahan`) |
| `site_name` | str | ✅ | Display name |
| `site_type` | str | ✅ | One of `ki`, `standalone`, `cluster` (KEK sites have `site_type="kek"` and live in the scraper output, not this file) |
| `sector` | str | ✅ | One of `steel`, `cement`, `aluminium`, `fertilizer`, `nickel`, `mixed` |
| `primary_product` | str | ✅ | e.g., `primary_aluminium`, `urea`, `copper_cathode` |
| `technology` | str | ⚠️ | e.g., `Hall-Heroult`, `Ammonia Synthesis`, `Flash Smelting`; some manual entries may be null |
| `capacity_annual` | str | ✅ | Display-friendly string (e.g., `"2,400,000 TPA"`) |
| `capacity_annual_tonnes` | float | ✅ | Numeric extraction from capacity_annual; feeds `demand_intensity.py` for sector-intensity demand |
| `parent_company` | str | ⚠️ | Owner entity; joint ventures encoded as "CoA / CoB" |
| `cluster_members` | str | ⚠️ | For `site_type="cluster"`: semicolon-separated list of member facilities |
| `latitude` | float | ✅ | WGS84 centroid (clusters = largest member by capacity, per eng review R3) |
| `longitude` | float | ✅ | WGS84 centroid |
| `province` | str | ✅ | Province name |
| `grid_region_id` | str | ⚠️ | PLN grid system; auto-assigned from nearest substation `regpln` if unset |
| `reliability_req` | float | ✅ | Sector-based default (steel=0.90, aluminium=0.95, cement=0.85, nickel=0.85, fertilizer=0.90) via `SITE_TYPES[...].default_reliability` |
| `cbam_product_type` | str | ✅ | Direct CBAM product assignment — bypasses 3-signal detection for `site_type in {"standalone","cluster","ki"}` |
| `source_name` | str | ✅ 🔒 | Human-readable source, e.g., "PT Inalum company profile" |
| `source_url` | str | ✅ 🔒 | Stable URL where the row's facts can be verified. **Loader raises if missing.** |
| `retrieved_date` | str | ✅ 🔒 | ISO date the URL was last confirmed (e.g., `2026-04-17`) |

---

# Part 2 — Dimension Tables

Dimension tables describe *what a site is* or *what a technology costs*. They are built once and referenced by all fact tables.

---

## 2.1 `outputs/data/processed/dim_sites.csv`

**What it is:** Master site list — unified dimension covering KEKs (25) + 54 industrial sites (32 cement, 17 steel, 2 aluminium, 3 fertilizer, 10 nickel IIA clusters). Identity, location, grid assignment, site-type discriminator, sector, industrial identity fields.
**Builder:** `src/pipeline/build_dim_sites.py` (KEK half) + `src/pipeline/build_industrial_sites.py` (industrial half, union of tracker filters + residual CSV)
**Lineage:** `kek_info_and_markers.csv` + `kek_distribution_points.csv` + `kek_polygons.geojson` + `kek_grid_region_mapping.csv` + `data/captive_power/gem_cement_plants.csv` + `data/captive_power/gem_steel_plants.csv` + `data/nickel/cgsp_nickel_projects.csv` + `data/industrial_sites/priority1_sites.csv` (residual manual rows) + `data/substation.geojson` (for auto grid_region_id)
**Rows:** 79 ✅

**Build logic:**
1. Build KEK half: join markers + distribution points on `xid`; join polygons on `slug` (largest `Luas_ha`); extract province from `address`; set `site_type="kek"`
2. Build industrial half via `build_industrial_sites.py` — three tracker-driven streams plus one residual manual stream:
   - `_build_cement_rows()` — GEM Global Cement Plant Tracker, `country_name == "Indonesia"` AND `status == "operating"` → 32 standalone rows
   - `_build_steel_rows()` — GEM Global Iron and Steel Plant Tracker, `country_name == "Indonesia"` AND `status == "Active"` → 7 standalone rows
   - `_build_nickel_rows()` — CGSP Nickel Tracker, `parent_project_type == "Integrated Industrial Area"` AND haversine ≥ 5 km from any KEK centroid (excludes Palu SEZ to prevent double-count); capacity aggregated from CGSP Processing children within 20 km → 10 cluster rows
   - `_load_residual_manual_rows()` — reads remaining rows from `priority1_sites.csv` (aluminium + fertilizer). Raises at build time if any row is missing `source_url`. → 5 standalone rows
3. Auto-assign `grid_region_id` for industrial sites without manual mapping: nearest substation's `regpln`
4. For `site_type="cluster"`: centroid = coordinates of largest member by capacity (not geographic mean — see eng review R3)
5. Parse `capacity_annual` string → `capacity_annual_tonnes` float
6. Union into unified `dim_sites.csv`; enforce unique `site_id`

**Known gap:** Two nickel IIA clusters (IKIP, Stardust Estate Investment) carry `capacity_annual_tonnes = NaN` — their nearest CGSP Processing children (37 km, 21 km) fall outside the 20 km aggregation window. Tracked as TODO M27.

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `site_id` | str | scraped slug (KEK) / priority1 CSV (industrial) | Stable primary key throughout pipeline. Replaces legacy `kek_id`. |
| `site_name` | str | `title` from markers / `site_name` column | Full display name |
| `site_type` | enum | derived (`"kek"` for KEK rows) / CSV `site_type` | One of `kek`, `ki`, `standalone`, `cluster`. Drives registry dispatch via `SITE_TYPES[site_type]` |
| `sector` | str | inferred for KEK (from business_sectors) / CSV `sector` | One of `steel`, `cement`, `aluminium`, `fertilizer`, `nickel`, `mixed` |
| `primary_product` | str | null for most KEK / CSV `primary_product` | e.g., `crude_steel`, `clinker`, `ammonia`, `primary_aluminium` |
| `province` | str | extracted from `address` / CSV `province` | Province name |
| `latitude` | float | markers / CSV (cluster: largest-member coords) | Centroid latitude (WGS84) |
| `longitude` | float | markers / CSV | Centroid longitude (WGS84) |
| `area_ha` | float | `Luas_ha` from polygons / CSV (null for most standalone) | Total declared zone area (KEK/KI) |
| `grid_region_id` | str | `kek_grid_region_mapping.csv` / auto from nearest substation `regpln` | PLN grid system (JAVA_BALI, SUMATERA, etc.) |
| `reliability_req` | float | `kek_grid_region_mapping.csv` / sector default via `SITE_TYPES[...].default_reliability` | Minimum reliability (0–1). Steel=0.90, Aluminium=0.95, Cement=0.85, Fertilizer=0.90, Nickel=0.85, KEK Manufacturing=0.80, KEK Service=0.60 |
| `reliability_notes` | str | mapping CSV / derived | Rationale |
| `capacity_annual` | str | null (KEK) / CSV `capacity_annual` | Display string (e.g., `"4,000,000 TPA"`, `"15.0 MTPA"`) |
| `capacity_annual_tonnes` | float | null (KEK) / parsed from `capacity_annual` | Numeric; feeds sector-intensity demand estimation |
| `technology` | str | null (KEK) / CSV `technology` | e.g., `BF-BOF`, `EAF`, `Integrated`, `RKEF`, `HPAL` |
| `parent_company` | str | `developer` (KEK) / CSV `parent_company` | Owner entity |
| `cluster_members` | str | null (KEK) / CSV `cluster_members` | For `site_type="cluster"`: semicolon-separated list of member facilities |
| `cbam_product_type` | str | null (KEK; inferred at scorecard time via 3-signal) / CSV direct | Direct assignment for industrial sites; feeds `_detect_cbam_types()` dispatch in `src/dash/logic/cbam.py` |
| `zone_classification` | str | `JenisKEK` from polygons (KEK only) / null | KEK-only: Industri / Pariwisata / Jasa lainnya (renamed from legacy `kek_type`, per eng review R5) |
| `category` | str | `category.name` from distribution points (KEK only) / null | KEK category |
| `status` | str | `status.name` from distribution points (KEK only) / null | Operational status |
| `legal_basis` | str | `legalBasis` from markers (KEK only) / null | Government decree reference (KEK only) |
| `developer` | str | `developer` from markers (KEK only) / see `parent_company` | KEK developer entity |
| `data_vintage` | str | pipeline run date | ISO date of last build |

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

Fact tables describe *what a site has* — resource quality, demand, cost, scorecard. Each has a lineage block and explicit formulas for derived columns.

---

## 3.1 `outputs/data/processed/fct_site_resource.csv`

**What it is:** Solar resource quality per site — PVOUT at centroid and best-within-50km, capacity factors.
**Builder:** `src/pipeline/build_fct_site_resource.py`
**Lineage:** `dim_sites.csv` (centroid coords) + Global Solar Atlas GeoTIFF (PVOUT raster)
**Rows:** 79 ✅

**Build logic:**
1. For each site centroid, sample the PVOUT GeoTIFF pixel
2. Search a 50km radius (latitude-corrected bounding box + circular haversine mask to exclude corners beyond 50km) for the maximum PVOUT pixel
3. Convert daily → annual: `pvout_daily × 365`
4. Compute CF: `pvout_annual / 8760`

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `site_id` | str | dim_sites | Join key |
| `site_name` | str | dim_sites | Display name |
| `latitude` | float | dim_sites | Centroid latitude |
| `longitude` | float | dim_sites | Centroid longitude |
| `pvout_daily_centroid` | float | GeoTIFF | Raw pixel value at centroid (kWh/kWp/day) — audit trail |
| `pvout_centroid` | float | computed | `pvout_daily_centroid × 365` (kWh/kWp/yr) |
| `cf_centroid` | float | computed | `pvout_centroid / 8760` |
| `pvout_daily_best_50km` | float | GeoTIFF | Max pixel within 50km radius (kWh/kWp/day) — audit trail |
| `pvout_best_50km` | float | computed | `pvout_daily_best_50km × 365` (kWh/kWp/yr) |
| `cf_best_50km` | float | computed | `pvout_best_50km / 8760` |
| `pvout_source` | str | constant | "GlobalSolarAtlas-v2" |
| `pvout_buildable_best_50km` | float | computed | Max PVOUT within 50km after 5-layer buildability filter (kawasan hutan, peatland, land cover, road proximity, slope/elevation). NaN when `data/buildability/` files absent. |
| `buildable_area_ha` | float | computed | Total buildable area in 50km radius after all filters (ha). NaN when data absent. |
| `max_captive_capacity_mwp` | float | computed | `buildable_area_ha / 1.5` — max captive solar capacity (MWp). 1.5 ha/MWp for tropical fixed-tilt. |
| `buildability_constraint` | str | computed | Dominant binding constraint: `"kawasan_hutan"` \| `"slope"` \| `"peat"` \| `"land_cover"` \| `"far_from_road"` \| `"area_too_small"` \| `"unconstrained"` \| `"data_unavailable"`. `"land_cover"` = ESA WorldCover layer (tree cover/forest, cropland, urban, water, wetland, mangrove) — dominant at most KEKs. `"far_from_road"` = >10km from motorable OSM road (motorway/trunk/primary/secondary/tertiary). |
| `best_solar_site_lat` | float | computed | Latitude of the highest-PVOUT buildable pixel within 50km. NaN when data absent or no buildable area. |
| `best_solar_site_lon` | float | computed | Longitude of the highest-PVOUT buildable pixel within 50km. NaN when data absent or no buildable area. |
| `best_solar_site_dist_km` | float | computed | Haversine distance (km) from site centroid to best buildable pixel. Always ≤ 50km (enforced by circular mask). NaN when data absent. |
| `within_boundary_area_ha` | float | computed | Buildable area (ha) inside the site polygon (KEK only — non-KEK sites have no polygon, so this is 0.0) after 5-layer buildability filter. **0.0 when spatial intersection finds no buildable pixels** (no theoretical fallback). 12 KEKs have raster-derived values; 13 KEKs are 0.0. |
| `within_boundary_capacity_mwp` | float | computed | `within_boundary_area_ha / 1.5` — max captive solar capacity inside site boundary (MWp). 0.0 when area is 0 or no polygon exists. |
| `pvout_within_boundary` | float | computed | Mean annual PVOUT (kWh/kWp/yr) of buildable pixels inside the site polygon. NaN when no buildable pixels exist or site has no polygon. |
| `within_boundary_source` | str | computed | `"raster"` if spatial buildable pixels were found inside the site polygon; `"theoretical"` if no pixels survived the buildability filter (area/capacity zeroed); null for non-KEK sites without a polygon. |

**Note:** `pvout_best_50km` is an upper bound — raw raster max with no buildability filter.
`pvout_buildable_best_50km` applies Layers 1–4 (METHODOLOGY_CONSOLIDATED.md §3.3) and is the
preferred value for LCOE when data is available. Until `data/buildability/` is populated,
both columns are available but `pvout_buildable_best_50km = NaN` and the pipeline
falls back to `pvout_best_50km`. Run `scripts/download_buildability_data.py` to acquire data.

---

## 3.2 `outputs/data/processed/fct_site_demand.csv`

**What it is:** Estimated 2030 electricity demand per site, dispatched by `SiteTypeConfig.demand_method`:
- **Area-based** (KEK + KI): `area_ha × energy_intensity_mwh_per_ha_yr` (legacy formula, unchanged)
- **Sector-intensity** (standalone + cluster): `capacity_annual_tonnes × sector_intensity_mwh_per_tonne` via `demand_intensity.py`

**Builder:** `src/pipeline/build_fct_site_demand.py`
**Lineage:** `dim_sites.csv` (area_ha, zone_classification, site_type, sector, capacity_annual_tonnes) + `src/assumptions.py` (area intensity constants) + `src/pipeline/demand_intensity.py` (sector intensity constants)
**Rows:** 79 ✅ (25 KEK area-based + 44 standalone sector-intensity + 10 cluster sector-intensity)

**Build logic (area-based, KEK + KI):**
```
energy_intensity_mwh_per_ha_yr = building_intensity_kwh_m2 × footprint_ratio × 10
demand_mwh = area_ha × energy_intensity_mwh_per_ha_yr
```

Area intensity constants by `zone_classification` (from `src/assumptions.py`):

| zone_classification | building_intensity (kWh/m²/yr) | footprint_ratio | derived intensity (MWh/ha/yr) |
|----------|-------------------------------|-----------------|-------------------------------|
| Industri | 120 | 0.55 | 660 |
| Industri dan Pariwisata | 184 | 0.40 | 736 |
| Pariwisata | 280 | 0.18 | 504 |
| Jasa lainnya | 200 | 0.40 | 800 |
| (unknown / KI) | — | — | 675 (average fallback) |

**Build logic (sector-intensity, standalone + cluster):**
```
demand_mwh = capacity_annual_tonnes × SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE[sector_or_technology]
```

Sector intensity constants (from `src/pipeline/demand_intensity.py`, calibrated to IRENA/IEA/worldsteel/IAI 2020–2023):

| sector / technology | MWh/tonne | Source |
|---------------------|-----------|--------|
| steel (EAF) | 0.50 | worldsteel 2023, IRENA 2020 |
| steel (BF-BOF) | 0.20 | worldsteel 2023 |
| cement | 0.11 | IEA Cement Roadmap 2018, GCCA 2022 |
| aluminium | 15.00 | IAI 2023 (Hall-Héroult) |
| fertilizer (ammonia) | 1.00 | IFA 2022 |
| nickel (RKEF) | 37.50 | JETP Captive Power Study Ch.2 |
| nickel (HPAL) | 8.00 | BNEF 2024, JETP |

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `site_id` | str | dim_sites | Primary key |
| `site_type` | str | dim_sites | `kek` / `ki` / `standalone` / `cluster` — drives method dispatch |
| `sector` | str | dim_sites | `steel` / `cement` / `aluminium` / `fertilizer` / `nickel` / `mixed` |
| `year` | int | constant | 2030 (demand target year) |
| `area_ha` | float | dim_sites | Total declared site area (area-based only) |
| `capacity_annual_tonnes` | float | dim_sites | Production capacity (sector-intensity only) |
| `demand_method` | str | computed | `"area_x_intensity"` or `"capacity_x_sector_intensity"` |
| `energy_intensity_mwh_per_ha_yr` | float | assumptions.py | Area-based sites only |
| `sector_intensity_mwh_per_tonne` | float | demand_intensity.py | Sector-intensity sites only |
| `demand_mwh` | float | computed | Final demand value (from whichever method applied) |
| `demand_mwh_user` | Float64 (nullable) | user input | Override value; `null` = use model default. |
| `demand_source` | str | computed | `"area_x_intensity"` \| `"capacity_x_sector_intensity"` \| `"area_fallback_median"` |
| `is_demand_provisional` | bool | constant | `True` for area-based KEK/KI (placeholder until load surveys); `False` for sector-intensity (production-based is more accurate) |

**Override contract:** Call `resolve_demand(fct_demand)` from `src/model/basic_model.py` before passing demand anywhere. It coalesces: when `demand_mwh_user` is non-null, it replaces `demand_mwh`. The frontend populates `demand_mwh_user` from user input fields; the pipeline leaves it null.

---

## 3.3 `outputs/data/processed/fct_grid_cost_proxy.csv`

**What it is:** Grid reference electricity cost per PLN system — used to assess whether solar LCOE is competitive.
**Builder:** `src/pipeline/build_fct_grid_cost_proxy.py`
**Lineage:** `dim_sites.csv` (grid_region_id list) + hardcoded tariffs from Permen ESDM 7/2024
**Rows:** 7 (one per PLN grid system) ✅

**Build logic:** I-4/TT tariff is uniform nationwide (same value for all regions). BPP Pembangkitan (generation cost of supply) is sourced per region from Kepmen ESDM 169/2021 via `src/pipeline/pdf_extract_bpp.py`.

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `grid_region_id` | str | dim_sites | PLN grid system |
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

**Derived metrics** (computed in `build_fct_site_scorecard.py` via `ruptl_region_metrics()`):

| Derived field | Formula |
|---------------|---------|
| `pre2030_solar_mw` | `sum(plts_new_mw_re_base where year ≤ 2030)` per region |
| `post2030_share` | `post2030_mw / (pre2030_mw + post2030_mw)` per region |
| `grid_upgrade_pre2030` | `True if pre2030_solar_mw > 0` |
| `earliest_grid_upgrade_year` | `min(year where plts_new_mw_re_base > 0)` per region |

---

## 3.4b `outputs/data/processed/fct_substation_proximity.csv`

**What it is:** Nearest operational PLN substation per site — distance, connection details, siting scenario, V2 three-point proximity analysis (grid integration category), and V3.1 geometric grid connectivity check + substation capacity utilization assessment.
**Builder:** `src/pipeline/build_fct_substation_proximity.py` (uses shared `geo_utils.haversine_km`)
**Lineage:** `dim_sites.csv` + `data/substation.geojson` + `data/pln_grid_lines.geojson` + `outputs/data/raw/kek_polygons.geojson` + `fct_site_resource.csv` (best solar site lat/lon)
**Rows:** 79 ✅

**Build logic:**
1. Filter substations to `statopr == "Operasi"` (operational only); extract `regpln` (PLN region)
2. Haversine distance from each site centroid to every substation → take nearest (B_site)
3. Point-in-polygon (shapely) for each KEK polygon → `has_internal_substation` (KEK sites only; non-KEK sites have no polygon → always False)
4. `siting_scenario = "within_boundary"` if `has_internal_substation` else `"remote_captive"` (V1 compat)
5. V2: Haversine from best solar site to nearest substation (B_solar) → `dist_solar_to_nearest_substation_km`
6. V2: `grid_integration_category` derived from three-point proximity thresholds (see METHODOLOGY_CONSOLIDATED.md §7)
7. V3.1: If B_solar ≠ B_site, load PLN grid lines (1,595 lines from `data/pln_grid_lines.geojson`) and check geometric connectivity — does any grid line pass within 2km buffer of both substations?
8. V3.1: Check PLN region (`regpln`) match as fallback connectivity proxy
9. V3.1: Compute `available_capacity_mva = capacity_mva × (1 − utilization_pct)` and traffic light assessment

**Data source: `data/pln_grid_lines.geojson`** — 1,595 PLN transmission lines with geometry (LineString/MultiLineString), voltage (`tegjar` kV: 150kV=1286, 500kV=86, 275kV=34, 70kV=177), and names encoding endpoints (e.g. `SUTT 150kV PEKALONGAN-COMAL`).

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| `site_id` | str | dim_sites | Join key |
| `site_name` | str | dim_sites | Display name |
| `nearest_substation_name` | str | substation.geojson `namobj` | Name of nearest operational substation to site (B_site) |
| `nearest_substation_voltage_kv` | str | substation.geojson `teggi` | e.g. "150 kV" |
| `nearest_substation_capacity_mva` | float | substation.geojson `kapgi` | Substation capacity (MVA). Source `kapgi` field has mixed units — values ≥ 10,000 are in VA (divided by 1,000,000); values 1–9,999 are already in MVA. Normalization via `_normalize_capacity_mva()`. Most sites populated; some null (not recorded in PLN dataset). |
| `dist_to_nearest_substation_km` | float | computed | ✅ Haversine distance from site centroid to nearest operational substation, 2 decimals |
| `has_internal_substation` | bool | computed | True if any operational substation is inside the KEK polygon (always False for non-KEK sites) |
| `siting_scenario` | str | derived | `"within_boundary"` or `"remote_captive"` (V1 compat) |
| `dist_solar_to_nearest_substation_km` | float | computed | ✅ V2: Haversine from best solar site to nearest substation (B_solar). NaN if solar coords unavailable. |
| `nearest_substation_to_solar_name` | str | computed | ✅ V2: Name of nearest substation to the solar site (B_solar) |
| `grid_integration_category` | str | computed | ✅ V2: `within_boundary` / `grid_ready` / `invest_substation` / `invest_transmission` / `grid_first` — see METHODOLOGY_CONSOLIDATED.md §7. V3.1: split `invest_grid` into `invest_substation` (upgrade existing) and `invest_transmission` (new line needed). |
| `nearest_substation_regpln` | str | substation.geojson `regpln` | ✅ V3.1: PLN region of site's nearest substation (B_site) |
| `nearest_substation_to_solar_regpln` | str | substation.geojson `regpln` | ✅ V3.1: PLN region of solar site's nearest substation (B_solar) |
| `same_grid_region` | bool | computed | ✅ V3.1: True if B_site and B_solar are in the same PLN region (`regpln` match) |
| `line_connected` | bool | computed | ✅ V3.1: True if any PLN grid line (from `pln_grid_lines.geojson`) passes within 2km buffer of both B_solar and B_site. Geometric connectivity proxy. |
| `inter_substation_connected` | bool | computed | ✅ V3.1: `line_connected OR same_grid_region`. If True, no new transmission line needed between substations. |
| `inter_substation_dist_km` | float | computed | ✅ V3.1: Haversine distance between B_solar and B_site. 0 if same substation. |
| `available_capacity_mva` | float | computed | ✅ V3.1: `capacity_mva × (1 − substation_utilization_pct)`. Default utilization = 65%. NaN if capacity unknown. |
| `capacity_assessment` | str | computed | ✅ V3.1: Traffic light — `green` (available > 2× solar), `yellow` (0.5–2×), `red` (< 0.5×), `unknown` (data unavailable). See METHODOLOGY_CONSOLIDATED.md §7. |

**M15: Multi-substation comparison (API-only, not stored in CSV)**

`GET /api/site/{id}/substations` extends the above with per-substation cost fields for the top 3 substations by distance. These are computed live using model functions from `src/model/basic_model.py`:

| Field | Type | Description |
|-------|------|-------------|
| `rank` | int\|null | 1–3 for top 3 by distance, null for others |
| `dist_solar_km` | float\|null | Haversine distance from best solar site to this substation (km) |
| `available_capacity_mva` | float\|null | Rated capacity × (1 − utilization_pct) |
| `capacity_assessment` | str\|null | Traffic light: green/yellow/red/unknown |
| `connection_cost_per_kw` | float\|null | Grid connection: dist × $5/kW-km + $80/kW fixed |
| `upgrade_cost_per_kw` | float\|null | Substation upgrade: deficit_fraction × $80/kW |
| `transmission_cost_per_kw` | float\|null | New inter-substation line cost (rank 2+ only) |
| `total_grid_capex_per_kw` | float\|null | Sum of connection + upgrade + transmission |
| `lcoe_estimate_usd_mwh` | float\|null | LCOE at default assumptions with this substation's grid costs |

---

## 3.5 `outputs/data/processed/fct_lcoe.csv`

**What it is:** Precomputed LCOE bands per site at 9 WACC values (4–20% in 2% steps) and 2 siting scenarios (within_boundary / grid_connected_solar). V2: replaces remote_captive with grid-connected solar; uses solar-to-substation distance; removes transmission lease adder. V3.1: adds inter-substation transmission cost when `inter_substation_connected == False`.
**Builder:** `src/pipeline/build_fct_lcoe.py`
**Lineage:** `dim_sites.csv` + `fct_site_resource.csv` (PVOUT) + `dim_tech_cost.csv` (CAPEX, FOM, lifetime) + `fct_substation_proximity.csv` (solar-to-substation distance, inter-substation connectivity)
**Rows:** 1,422 (79 sites × 9 WACC values × 2 scenarios) ✅ — general form: `len(dim_sites) × 9 × 2`

**Siting scenarios:**
- `within_boundary` — plant on-site; uses `pvout_centroid`; `connection_cost_per_kw = 0`. For non-KEK sites with no polygon, "within_boundary" means at the site centroid.
- `grid_connected_solar` — IPP solar connects to nearest PLN substation; uses `pvout_best_50km`; connection cost based on `dist_solar_to_nearest_substation_km`

**LCOE formula** (`src/model/basic_model.py → lcoe_solar()`):
```
gen_tie_cost     = dist_solar_to_sub_km × CONNECTION_COST_PER_KW_KM + GRID_CONNECTION_FIXED_PER_KW  (grid_connected_solar only)
transmission_cost= inter_sub_dist_km × TRANSMISSION_LINE_COST_USD_PER_KM / (solar_mwp × 1000)  (V3.1: only if inter_substation_connected == False)
effective_capex  = capex + gen_tie_cost + transmission_cost
CRF              = wacc × (1 + wacc)^n / ((1 + wacc)^n − 1)
LCOE             = (effective_capex × CRF + FOM) / (CF × 8.76)
```

| Column | Type | Source | Calculation |
|--------|------|--------|-------------|
| `site_id` | str | dim_sites | Join key |
| `wacc_pct` | float | assumptions.py | 4.0 / 6.0 / 8.0 / 10.0 / 12.0 / 14.0 / 16.0 / 18.0 / 20.0 |
| `scenario` | str | derived | `"within_boundary"` or `"grid_connected_solar"` |
| `pvout_used` | str | derived | `"pvout_centroid"` or `"pvout_best_50km"` |
| `cf_used` | float | fct_site_resource | PVOUT / 8760; fallback to centroid if best_50km NaN |
| `connection_cost_per_kw` | float | computed | 0 for within_boundary; `dist_km × $5/kW-km + $80/kW` for grid_connected_solar |
| `effective_capex_usd_per_kw` | float | computed | `capex_central + connection_cost_per_kw` |
| `lcoe_usd_mwh` | float | computed | `lcoe_solar(effective_capex_central, fom, wacc/100, lifetime, cf)` |
| `lcoe_low_usd_mwh` | float | computed | `lcoe_solar(effective_capex_lower, ...)` |
| `lcoe_high_usd_mwh` | float | computed | `lcoe_solar(effective_capex_upper, ...)` |
| `transmission_cost_per_kw` | float | computed | ✅ V3.1: Inter-substation new line cost per kW. 0 if `inter_substation_connected == True` or same substation. `inter_sub_dist_km × $1.25M/km ÷ (solar_mwp × 1000)`. |
| `is_cf_provisional` | bool | derived | `True` if centroid fallback was used for grid_connected_solar |
| `is_capex_provisional` | bool | dim_tech_cost | Propagated from `dim_tech_cost.is_provisional` |
| `tech_id` | str | dim_tech_cost | "TECH006" |
| `lifetime_yr` | int | dim_tech_cost | Asset lifetime |

---

## 3.6 `outputs/data/processed/fct_site_scorecard.csv`

**What it is:** Dashboard-ready summary. One row per site — joins all upstream tables, computes action flags, GEAS green share, competitive gap, CBAM exposure, and 2D classification tiers.
**Builder:** `src/pipeline/build_fct_site_scorecard.py`
**Lineage:** `dim_sites.csv` + `fct_lcoe.csv` (wacc=10% rows) + `fct_site_resource.csv` + `fct_site_demand.csv` + `fct_grid_cost_proxy.csv` + `fct_ruptl_pipeline.csv` + all four captive summaries + `fct_site_wind_resource.csv`
**Rows:** 79 ✅ (25 KEK + 44 standalone + 10 cluster)

**Build logic:**
1. Filter `fct_lcoe` to `wacc_pct = 10.0` AND `scenario = "within_boundary"` — base case LCOE (on-site solar, no gen-tie)
2. Load `fct_site_demand`, call `resolve_demand()` to apply any user overrides
3. Compute `ruptl_region_metrics()` → `post2030_share`, `grid_upgrade_pre2030`
4. Compute `geas_baseline_allocation()` → `green_share_geas`
5. Compute action flags per site from `action_flags()`
6. CBAM exposure detection dispatched via `SITE_TYPES[site_type].cbam_method`: `3_signal` (KEK) vs `direct` (standalone/cluster/KI). 66/79 sites exposed (12 KEK + 54 industrial direct).

**Identity columns** (passed through from dim_sites):

| Column | Source |
|--------|--------|
| `site_id`, `site_name`, `province`, `grid_region_id`, `status` | dim_sites |
| `site_type` (`kek`/`ki`/`standalone`/`cluster`), `sector` (`steel`/`cement`/`aluminium`/`fertilizer`/`nickel`/`mixed`) | dim_sites |
| `zone_classification` (legacy kek_type; null for non-KEK) | dim_sites |
| `primary_product`, `capacity_annual`, `capacity_annual_tonnes`, `technology`, `parent_company`, `cluster_members` | dim_sites (null for KEKs) |
| `latitude`, `longitude` | dim_sites |

**Resource columns** (from fct_site_resource):
| `pvout_buildable_best_50km` | fct_site_resource | NaN until data/buildability/ populated |
| `buildable_area_ha` | fct_site_resource | NaN until data/buildability/ populated |
| `max_captive_capacity_mwp` | fct_site_resource | NaN until data/buildability/ populated |
| `buildability_constraint` | fct_site_resource | "data_unavailable" until populated |
| `resource_quality` | derived | `"filtered"` when buildable data applied; else `"provisional (no buildability filter)"` |


| Column | Source |
|--------|--------|
| `pvout_centroid`, `cf_centroid` | fct_site_resource |
| `pvout_best_50km`, `cf_best_50km` | fct_site_resource |

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
| `solar_attractive` | bool | `pvout_best_50km ≥ 1,350 kWh/kWp/yr AND lcoe_mid_usd_mwh ≤ dashboard_rate_usd_mwh` |
| `lcoe_mid_wacc8_usd_mwh` | float | LCOE at WACC=8% (de-risked finance scenario), within_boundary. Sourced from `fct_lcoe.csv` at `wacc_pct=8`. |
| `solar_competitive_gap_wacc8_pct` | float | Same formula as `solar_competitive_gap_pct` but using `lcoe_mid_wacc8_usd_mwh`. Negative = solar competitive under de-risked financing. |
| `solar_now_at_wacc8` | bool | `lcoe_mid_wacc8_usd_mwh ≤ dashboard_rate_usd_mwh` — True for 8 KEKs. The "what does a green finance facility unlock?" signal for DFI analysts. |
| `lcoe_grid_connected_usd_mwh` | float | V2: LCOE for `grid_connected_solar` scenario at `BASE_WACC=10%` — includes connection cost (solar→substation distance × $5/kW-km + $80/kW fixed). |
| `lcoe_grid_connected_low_usd_mwh` | float | Same using `capex_lower`. |
| `lcoe_grid_connected_high_usd_mwh` | float | Same using `capex_upper`. |
| `connection_cost_per_kw` | float | V2: Grid connection cost per kW for this site's solar project. 0 for within_boundary. |
| `within_boundary_coverage_pct` | float | V3.2: Fraction of site 2030 demand coverable by within-boundary solar. `wb_capacity_mwp × pvout_within_boundary / demand_mwh_2030`. If >= 1.0, overrides `grid_integration_category` to `within_boundary`. |
| `grid_integration_category` | str | V2/V3.1/V3.2: `within_boundary` / `grid_ready` / `invest_substation` / `invest_transmission` / `grid_first` — from fct_substation_proximity, overridden by within-boundary coverage >= 100% (V3.2). |
| `same_grid_region` | bool | V3.1: B_site and B_solar in same PLN region. |
| `line_connected` | bool | V3.1: Grid line geometrically connects both substations. |
| `inter_substation_connected` | bool | V3.1: `line_connected OR same_grid_region`. |
| `inter_substation_dist_km` | float | V3.1: Haversine between B_solar and B_site. |
| `available_capacity_mva` | float | V3.1: Substation headroom = `capacity_mva × (1 − utilization_pct)`. |
| `capacity_assessment` | str | V3.1: Traffic light — `green` / `yellow` / `red` / `unknown`. |
| `transmission_cost_per_kw` | float | V3.1: New inter-substation line cost per kW (0 if connected). |
| `substation_upgrade_cost_per_kw` | float | V3.2: Additional $/kW when substation capacity insufficient. `deficit_fraction × $80/kW` where `deficit = (solar_mwp − available) / solar_mwp` and `available = rated_mva × (1 − utilization_pct)`. 0 if capacity sufficient or unknown. |
| `grid_investment_needed_usd` | float | Total grid infrastructure cost: `(connection_cost_per_kw + transmission_cost_per_kw + substation_upgrade_cost_per_kw) × max_captive_capacity_mwp × 1000`. Screening estimate for DFI investment sizing. NaN if capacity is 0 or no infrastructure cost. |
| `project_viable` | bool | `max_captive_capacity_mwp ≥ PROJECT_VIABLE_MIN_MWP (20 MWp)`. True = minimum viable IPP project size met. All 79 sites = True at current 1km buildability resolution. DFI threshold is stricter (≥ 33 MWp / ≥ 50 ha). |
| `clean_power_advantage` | float | `−solar_competitive_gap_pct` — higher = more competitive |
| `green_share_geas` | float | Pro-rata share of 2030 demand covered by pre-2030 RUPTL solar. Formula: `min(1, (pre2030_mw × 8760 × 0.20 × site_demand_share) / site_demand_mwh)`. See `geas_baseline_allocation()`. |
| `pre2030_solar_mw` | float | `sum(plts_new_mw_re_base where year ≤ 2030)` for this site's region |
| `post2030_share` | float | `post2030_mw / total_ruptl_mw` for this region. ≥ 0.60 triggers `plan_late`. |
| `grid_upgrade_pre2030` | bool | `True if pre2030_solar_mw > 0` |
| `ruptl_summary` | str | `"{pre2030_solar_mw} MW solar planned in {region} by 2030"` |

**Action flag columns** (from `action_flags()` + `invest_resilience()` in `basic_model.py`):

| Flag | Formula |
|------|---------|
| `solar_attractive` | `pvout_best_50km ≥ 1,350 AND lcoe_mid ≤ dashboard_rate` |
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

**Solar supply coverage columns (live-computed):**

| Column | Type | Formula |
|--------|------|---------|
| `max_solar_generation_gwh` | float | `max_captive_capacity_mwp × pvout_best_50km / 1000` — maximum annual solar generation if all buildable capacity were built at best-resource sites within 50km. |
| `solar_supply_coverage_pct` | float | `max_solar_generation_gwh / demand_2030_gwh` — fraction of site demand coverable by buildable solar. >= 1.0 means solar can fully supply the site. |

**Wind columns (from `fct_site_wind_resource`, merged at API startup + live-computed in `logic/scorecard.py`):**

| Column | Type | Source | Formula / Notes |
|--------|------|--------|-----------------|
| `lcoe_wind_mid_usd_mwh` | float | Live | Wind LCOE at current WACC, mid CAPEX. Same CRF formula as solar with wind parameters. |
| `lcoe_wind_allin_mid_usd_mwh` | float | Live | Wind LCOE including connection costs. |
| `cf_wind` | float | CSV | Capacity factor at best 50km wind site. |
| `wind_speed_ms` | float | CSV | Wind speed at best 50km site (m/s). |
| `best_re_technology` | str | Live | `"solar"`, `"wind"`, or `"hybrid"`, whichever has lower all-in LCOE (3-way comparison, see §6A.6). |
| `best_re_lcoe_mid_usd_mwh` | float | Live | LCOE of the better technology. |
| `wind_competitive_gap_pct` | float | Live | `(lcoe_wind_mid - grid_cost) / grid_cost × 100`. Negative = wind cheaper. |
| `max_wind_capacity_mwp` | float | CSV | Buildable wind capacity at 25 ha/MWp density. |
| `wind_buildable_area_ha` | float | CSV | Buildable wind area within 50km after 6-layer filter. |
| `wind_buildability_constraint` | str | CSV | Binding constraint in wind buildability cascade. |
| `max_wind_generation_gwh` | float | Live | `max_wind_capacity_mwp × cf_wind_buildable_best × 8760 / 1000`. |
| `wind_supply_coverage_pct` | float | Live | `max_wind_generation_gwh / demand_2030_gwh`. Fraction of site demand coverable by buildable wind. |
| `wind_carbon_breakeven_usd_tco2` | float | Live | Carbon price at which wind becomes cost-competitive. Same formula as solar (§9.2). |
| `firm_wind_coverage_pct` | float | Live | Demand fraction wind serves without storage. CF-dependent (65-85%). |
| `wind_firming_gap_pct` | float | Live | Fraction requiring firming (15-35%, CF-dependent). |
| `wind_firming_hours` | float | Live | BESS bridge hours for wind intermittency (2-4h). |

**Hybrid RE columns** (live-computed in `logic/technology.py::compute_hybrid_metrics()` via `hybrid_lcoe_optimized()`; see §6A):

| Column | Type | Source | Formula / Notes |
|--------|------|--------|-----------------|
| `hybrid_lcoe_usd_mwh` | float | Live | Blended LCOE = generation-weighted avg of solar + wind LCOE. |
| `hybrid_bess_hours` | float | Live | Reduced BESS sizing (0-14h). `14 × (1 - nighttime_coverage)`. |
| `hybrid_bess_adder_usd_mwh` | float | Live | BESS cost at reduced sizing via `bess_storage_adder()`. |
| `hybrid_allin_usd_mwh` | float | Live | `hybrid_lcoe + hybrid_bess_adder`. Primary hybrid cost metric. |
| `hybrid_solar_share` | float | Live | Optimal solar fraction (0-1). Auto-optimized or user-overridden. |
| `hybrid_supply_coverage_pct` | float | Live | `(scaled_solar_gen + scaled_wind_gen) / demand`. |
| `hybrid_nighttime_coverage_pct` | float | Live | Fraction of nighttime demand covered by wind. |
| `hybrid_bess_reduction_pct` | float | Live | `1 - hybrid_bess_hours / 14`. 0% = no reduction, 100% = no BESS needed. |
| `hybrid_carbon_breakeven_usd_tco2` | float | Live | Carbon price at which hybrid all-in beats grid cost. Same formula as solar (§9.2). |

**Data quality column:**

| Column | Type | Formula |
|--------|------|---------|
| `data_completeness` | str | `"complete"` if no null key columns and `is_capex_provisional=False`. `"provisional"` if `is_capex_provisional=True`. `"partial"` if key columns are null. |

**Captive power columns** (from `fct_captive_coal_summary` + `fct_captive_nickel_summary` + `fct_captive_steel_summary` + `fct_captive_cement_summary`, merged via left join):

| Column | Type | Source | Formula / Notes |
|--------|------|--------|-----------------|
| `captive_coal_count` | int/null | GEM GCPT | Count of captive coal plants within 50 km of site centroid (proximity mode) or exact site match (direct mode). Null for sites with no match. |
| `captive_coal_mw` | int/null | GEM GCPT | Sum of `capacity_mw` for matched coal plants. |
| `captive_coal_plants` | str/null | GEM GCPT | Semicolon-separated plant names. |
| `nickel_smelter_count` | int/null | CGSP | Count of nickel processing facilities within 50 km. |
| `nickel_projects` | str/null | CGSP | Semicolon-separated project names. |
| `dominant_process_type` | str/null | CGSP | Mode of process types among matched facilities (RKEF, Ferro Nickel, HPAL, Laterite). |
| `has_chinese_ownership` | bool | CGSP | True if any matched nickel facility has Chinese ownership. False if no nickel data. |
| `has_captive_coal` | bool | Derived | `captive_coal_count > 0`. Indicates site is subject to Perpres 112/2022. |
| `perpres_112_status` | str/null | Derived | `"Subject to 2050 phase-out"` if `has_captive_coal`, else null. Status-based proxy (commissioning_year unavailable). |
| `effective_capacity_mwp` | float/null | User input (H10) | User-selected project capacity for LCOE recalculation. When set, overrides `max_captive_capacity_mwp` for gen-tie cost and substation capacity assessment. Null = use max buildable. |
| `captive_coal_generation_gwh` | float/null | Derived | Estimated annual coal generation: `captive_coal_mw × 8.76 × 0.40` (40% CF assumption for Indonesian captive coal). |
| `solar_replacement_pct` | float/null | Derived | `max_solar_generation_gwh / captive_coal_generation_gwh × 100`. What % of captive coal output is replaceable by buildable solar. |
| `bess_sizing_hours` | float | Derived | BESS storage sizing (hours). V3.6 hierarchy: user override > bridge-hours 14h (reliability >= 0.75) > RKEF 4h > cloud-firming 2h. Drives `battery_adder_usd_mwh` and `lcoe_with_battery_usd_mwh`. |
| `bess_sizing_hours_override` | float/null | User input | Optional BESS sizing override (1-16h). When set, overrides the auto-computed sizing for all sites. None = auto (2h/4h/14h by load type). Adjustable via ScoreDrawer Economics tab slider. |
| `steel_plant_count` | int/null | GEM Steel | Count of steel plants within 50 km of site centroid (proximity mode) or direct match (standalone/cluster steel sites). |
| `steel_capacity_tpa` | float/null | GEM Steel | Sum of capacity (tonnes per annum) for matched steel plants. |
| `steel_plants` | str/null | GEM Steel | Semicolon-separated plant names. |
| `steel_has_chinese_ownership` | bool/null | GEM Steel | True if any matched steel facility has Chinese ownership. |
| `steel_dominant_technology` | str/null | GEM Steel | Mode of steel plant technology within 50 km (`EAF` or `BF-BOF`). From `fct_captive_steel_summary`. |
| `cement_plant_count` | int/null | GEM Cement | Count of cement plants within 50 km of site centroid (proximity mode) or direct match (standalone/cluster cement sites). |
| `cement_capacity_mtpa` | float/null | GEM Cement | Sum of capacity (million tonnes per annum) for matched cement plants. |
| `cement_plants` | str/null | GEM Cement | Semicolon-separated plant names. |
| `cement_has_chinese_ownership` | bool/null | GEM Cement | True if any matched cement facility has Chinese ownership. |

**CBAM exposure columns** (live-computed in `logic/cbam.py`; see METHODOLOGY_CONSOLIDATED.md):

| Column | Type | Source | Formula / Notes |
|--------|------|--------|-----------------|
| `cbam_exposed` | bool | Derived | True if site has CBAM-covered products. Detection method dispatched via `SITE_TYPES[site_type].cbam_method`: **3_signal** (KEK) — (1) nickel process types (RKEF/FeNi), (2) plant-level counts (steel/cement), (3) KEK business sectors; **direct** (standalone/cluster/KI) — uses `cbam_product_type` from `dim_sites.csv`. **66/79 sites exposed** (12 KEK via 3-signal + 54 industrial via direct: 32 cement + 17 iron_steel + 3 fertilizer + 2 aluminium). |
| `cbam_product_type` | str/null | Derived | Primary CBAM product category. Product types: `nickel_rkef` (37.5 MWh/t), `steel_eaf` (0.45 MWh/t), `steel_bfbof` (0.25 MWh/t), `cement` (0.11 MWh/t), `aluminium` (15.0 MWh/t), `fertilizer` (1.0 MWh/t). Standalone/cluster/KI sites set this column directly in `dim_sites.csv`; KEKs infer via 3-signal detection. |
| `cbam_emission_intensity_current` | float/null | Derived | Current grid-based emission intensity for this product (tCO2/t product). |
| `cbam_emission_intensity_solar` | float/null | Derived | Emission intensity if powered by solar (tCO2/t product). Near-zero for electricity-only emissions. |
| `cbam_cost_2026_usd_per_tonne` | float/null | Derived | CBAM cost per tonne of product in 2026. EU ETS ~EUR80/tCO2 x free allocation phase-out schedule (97.5% free in 2026). |
| `cbam_cost_2030_usd_per_tonne` | float/null | Derived | CBAM cost per tonne in 2030 (free allocation declining). |
| `cbam_cost_2034_usd_per_tonne` | float/null | Derived | CBAM cost per tonne in 2034 (0% free allocation). |
| `cbam_savings_2026_usd_per_tonne` | float/null | Derived | CBAM savings per tonne from switching to solar in 2026. |
| `cbam_savings_2030_usd_per_tonne` | float/null | Derived | CBAM savings per tonne from switching to solar in 2030. |
| `cbam_savings_2034_usd_per_tonne` | float/null | Derived | CBAM savings per tonne from switching to solar in 2034. |
| `cbam_per_product` | dict/null | Derived | Nested dict of per-product CBAM metrics. Keys: product type strings (`nickel_rkef`, `steel_eaf`, `steel_bfbof`, `cement`, etc.). Values: `CbamProductMetrics` with `emission_intensity_current`, `emission_intensity_solar`, cost/savings at 2026/2030/2034. Enables per-product drill-down in ScoreDrawer. |
| `cbam_savings_per_mwh` | float/null | Derived | CBAM savings converted to $/MWh of electricity: `savings_per_tonne / electricity_intensity_mwh_per_tonne`. Bridges CBAM product-level savings to electricity-cost comparisons. Used for CBAM-adjusted gap calculation. |
| `cbam_adjusted_gap_pct` | float/null | Derived | Competitive gap with CBAM savings factored in: `(lcoe_mid_usd_mwh - dashboard_rate_usd_mwh - cbam_savings_per_mwh) / dashboard_rate_usd_mwh x 100`. More negative = solar + CBAM avoidance strongly beats grid. Null for non-CBAM-exposed sites. |

**2D classification columns** (live-computed in `logic/scorecard.py`; V3.7):

| Column | Type | Source | Formula / Notes |
|--------|------|--------|-----------------|
| `economic_tier` | str | Live | Economic competitiveness tier: `full_re` (RE+storage ≤ grid), `partial_re` (bare RE ≤ grid), `near_parity` (RE within 20% of grid), `not_competitive` (RE > 20% above grid), `no_resource` (no buildable area). Computed via `economic_tier()` from `basic_model.py`. |
| `infrastructure_readiness` | str | Live | Infrastructure readiness axis: reuses `grid_integration_category` values (`within_boundary`, `grid_ready`, `invest_transmission`, `invest_substation`, `grid_first`). |
| `modifier_badges` | list[str] | Live | Overlay modifier badges that cross-cut both axes: `cbam_urgent` (CBAM-adjusted gap < 0), `plan_late` (post2030_share ≥ 0.60), `storage_info` (BESS sizing > 2h). |

---

### 3.7 `outputs/data/processed/fct_captive_coal_summary.csv`

**Rows:** Sites with captive coal plants within 50 km (proximity mode for KEK/KI) or direct match (standalone/cluster)
**Built from:** `dim_sites` centroids × GEM Global Coal Plant Tracker (KAPSARC mirror, filtered to Indonesia captive)
**Pipeline:** `build_captive_coal_summary()` in `src/pipeline/build_fct_captive_coal.py`. Uses shared `proximity_match()` / `direct_match()` from `src/pipeline/geo_utils.py` dispatched via `SITE_TYPES[site_type].captive_power_method`.

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | str | Site identifier (join key to `dim_sites`) |
| `captive_coal_count` | int | Number of captive coal plants within 50 km |
| `captive_coal_mw` | float | Total captive coal capacity (MW) |
| `captive_coal_plants` | str | Semicolon-separated plant names |

**Data source:** GEM Global Coal Plant Tracker, CC BY 4.0. Downloaded via KAPSARC mirror. Filtered to `country="Indonesia"` and captive status. 26 plants in raw data.

---

### 3.8 `outputs/data/processed/fct_captive_nickel_summary.csv`

**Rows:** Sites with nickel smelters within 50 km (proximity) or direct match (standalone nickel sites — Weda Bay, Obi Island, Konawe)
**Built from:** `dim_sites` centroids × CGSP Nickel Tracker
**Pipeline:** `build_captive_nickel_summary()` in `src/pipeline/build_fct_captive_nickel.py`. Uses shared `proximity_match()` / `direct_match()` from `src/pipeline/geo_utils.py`.

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | str | Site identifier (join key to `dim_sites`) |
| `nickel_smelter_count` | int | Number of nickel processing facilities within 50 km |
| `nickel_projects` | str | Semicolon-separated project names |
| `dominant_process_type` | str | Most common nickel process type (RKEF, Ferro Nickel, HPAL, Laterite) |
| `has_chinese_ownership` | bool | True if any matched facility has Chinese ownership |

**Data source:** CGSP Nickel Tracker (chinaglobalsouth.com/nickel), CC license, updated quarterly. 107 facilities in raw data.

---

### 3.9 `outputs/data/processed/fct_captive_steel_summary.csv`

**Rows:** Sites with steel plants within 50 km (proximity) or direct match (standalone/cluster steel sites — Krakatau, Dexin, Gunung, Morowali cluster, etc.)
**Built from:** `dim_sites` centroids × GEM Global Iron and Steel Plant Tracker
**Pipeline:** `build_captive_steel_summary()` in `src/pipeline/build_fct_captive_steel.py`. Uses shared `proximity_match()` / `direct_match()` from `src/pipeline/geo_utils.py`.

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | str | Site identifier (join key to `dim_sites`) |
| `steel_plant_count` | int | Number of steel plants within 50 km |
| `steel_capacity_tpa` | float | Total capacity in tonnes per annum |
| `steel_plants` | str | Semicolon-separated plant names |
| `steel_has_chinese_ownership` | bool | True if any matched facility has Chinese ownership |
| `steel_dominant_technology` | str | Mode of steel plant technology within 50 km (`EAF` or `BF-BOF`). Determines CBAM product type split: EAF maps to `steel_eaf` (0.45 MWh/t), BF-BOF maps to `steel_bfbof` (0.25 MWh/t). |

**Data source:** GEM Global Iron and Steel Plant Tracker, CC BY 4.0. 7 plants in raw data (`data/captive_power/gem_steel_plants.csv`).

---

### 3.10 `outputs/data/processed/fct_captive_cement_summary.csv`

**Rows:** Sites with cement plants within 50 km (proximity) or direct match (standalone/cluster cement sites — Semen Gresik Tuban, Indocement Citeureup, etc.)
**Built from:** `dim_sites` centroids × GEM Global Cement Plant Tracker
**Pipeline:** `build_captive_cement_summary()` in `src/pipeline/build_fct_captive_cement.py`. Uses shared `proximity_match()` / `direct_match()` from `src/pipeline/geo_utils.py`.

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | str | Site identifier (join key to `dim_sites`) |
| `cement_plant_count` | int | Number of cement plants within 50 km |
| `cement_capacity_mtpa` | float | Total capacity in million tonnes per annum |
| `cement_plants` | str | Semicolon-separated plant names |
| `cement_has_chinese_ownership` | bool | True if any matched facility has Chinese ownership |

**Data source:** GEM Global Cement Plant Tracker, CC BY 4.0. 32 plants in raw data (`data/captive_power/gem_cement_plants.csv`).

---

### 3.11 `outputs/data/processed/fct_site_wind_resource.csv`

**Rows:** 79 (one per site — 25 KEK + 44 standalone + 10 cluster)
**Built from:** `dim_sites` centroids × Global Wind Atlas v3 GeoTIFF × `buildable_wind_web.tif`
**Pipeline:** `build_fct_site_wind_resource.py`

| Column | Type | Description |
|--------|------|-------------|
| `site_id` | str | Site identifier (join key to `dim_sites`) |
| `site_name` | str | Site display name |
| `latitude` | float | Site centroid latitude |
| `longitude` | float | Site centroid longitude |
| `wind_speed_centroid_ms` | float | Mean annual wind speed at site centroid (100m hub height, m/s) |
| `wind_speed_best_50km_ms` | float | Best wind speed within 50km radius (m/s) |
| `cf_wind_centroid` | float | Capacity factor at centroid (from `wind_speed_to_cf()`) |
| `cf_wind_best_50km` | float | Capacity factor at best 50km site |
| `wind_class` | str | Wind resource classification (marginal/low/moderate/good/excellent) |
| `wind_source` | str | Data source identifier |
| `wind_buildable_area_ha` | float | Buildable area for wind within 50km after 6-layer filter (ha) |
| `max_wind_capacity_mwp` | float | Maximum wind capacity at 25 ha/MWp density (MWp) |
| `wind_buildability_constraint` | str | Binding constraint in buildability cascade |
| `wind_speed_buildable_best_ms` | float | Wind speed at best buildable pixel (m/s) |
| `cf_wind_buildable_best` | float | Capacity factor at best buildable pixel |
| `best_wind_site_lat` | float | Latitude of best buildable wind site |
| `best_wind_site_lon` | float | Longitude of best buildable wind site |
| `best_wind_site_dist_km` | float | Distance from site centroid to best wind site (km) |

**Wind buildability pipeline:** `buildable_wind_web.tif` is produced by `build_wind_buildable_raster.py` using 5 exclusion layers (kawasan hutan, peatland, land cover, slope/elevation, wind speed minimum). See METHODOLOGY_CONSOLIDATED.md §4.1.

**Live-computed wind columns** (in `logic/scorecard.py`, not stored in CSV):

| Column | Type | Description |
|--------|------|-------------|
| `wind_supply_coverage_pct` | float | Fraction of site demand coverable by buildable wind |
| `wind_carbon_breakeven_usd_tco2` | float | Carbon price at which wind becomes cost-competitive |
| `max_wind_generation_gwh` | float | Maximum annual wind generation from buildable capacity |
| `firm_wind_coverage_pct` | float | Demand fraction wind serves directly (without storage) |
| `wind_firming_gap_pct` | float | Fraction of demand requiring firming (CF-dependent: 15-35%) |
| `wind_firming_hours` | float | BESS bridge hours for wind intermittency (2-4h) |

---

## Open Questions

1. **BPP data** — ✅ Regional BPP Pembangkitan sourced from Kepmen ESDM 169/2021 (FY2020). `bpp_usd_mwh` populated for all 7 grid regions via `src/pipeline/pdf_extract_bpp.py`. Vintage: FY2020, valid until superseded.

2. ✅ **TECH006 CAPEX verified** — extracted from `docs/esdm_technology_cost.pdf` p.66. `source_page=66`, `is_capex_provisional=False` across all LCOE and scorecard rows. Values: CAPEX=$960/kW, FOM=$7.5/kW/yr, lifetime=27yr.

3. **Landcover buildability filter** — `pvout_best_50km` is currently an upper bound with no exclusion of forests, peat, protected areas. Planned for v1.1: 4-layer filter (HCS/HCV, peatland, protected areas, slope > 15°).

4. **Substation proximity** — ✅ Implemented in Phase 2, expanded in V3.1. `fct_substation_proximity.csv` computes distances, grid integration category, geometric grid line connectivity (1,595 PLN lines), substation capacity utilization assessment (traffic light), and inter-substation connectivity. V3.1 adds transmission cost to `fct_lcoe.csv` when `inter_substation_connected == False`.
