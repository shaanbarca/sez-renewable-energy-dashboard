# `data/raw/` — manually-curated reference data

Files here are **manually compiled** raw reference data, in contrast to:
- `data/captive_power/`, `data/industrial_data/` — bulk-imported third-party datasets (GEM tracker, KAPSARC mirrors, MS Buildings, RUPTL PDFs)
- `outputs/data/processed/` — pipeline outputs (regenerated from raw)

Each file should:
- Be small (< 100 rows typically) and human-reviewable
- Include a `source` column citing the primary reference per row
- Include a `verification_status` column (`confirmed` / `inferred` / `placeholder`) so consumers know how much weight to give each row
- Document its schema in this README

---

## `captive_coal_contractual_overrides.csv`

**Purpose (F12, [#14](https://github.com/shaanbarca/eez/issues/14)).** Override the §13.2 50-km haversine match for sites with a known **contractual** relationship to a captive coal plant beyond the buffer. Sumatran mine-mouth coal plants supplying smelters > 50 km away are common; pure spatial matching misses these.

**Use the override to:**
- Pull in a captive plant the haversine missed (was `site_id = None`, override sets it)
- Re-route a plant from a wrong spatial nearest-neighbour to its actual contractual site

**Schema:**

| Column | Type | Description |
|---|---|---|
| `site_id` | str | The site that contractually owns / consumes this plant's output. Must match a `site_id` in `dim_sites`. |
| `plant_name` | str | Plant name as it appears in the GEM coal tracker (`plant` column). Used for the join. |
| `plant_lat`, `plant_lon` | float | Coordinates from GEM. Defensive: lets us catch ambiguous plant-name matches. |
| `source` | str | Primary reference (annual report, public disclosure, etc.) |
| `last_updated` | YYYY-MM | Date the entry was added or last verified |
| `distance_km` | float | Distance from site to plant in km. For audit; overrides apply regardless of distance. |
| `verification_status` | enum | `confirmed` (primary source reviewed), `inferred` (spec example or weaker citation), `placeholder` (schema example, do not use) |
| `notes` | str | Free-form context |

**Implementation.** Loaded by `src/pipeline/geo_utils.py::apply_contractual_overrides()` after the haversine match in `build_fct_captive_coal.py`. Output rows get `captive_match_method = 'contractual'` (vs. `'spatial'`) for provenance.

**Adding new entries.** Cite a primary source in `source`. Set `verification_status = 'confirmed'` only if you've personally reviewed the source. Otherwise `inferred`. The two seed rows from the F12 spec (IMIP, Krakatau Steel) are `inferred` until cross-checked against GEM.

---

## `ruptl_v9_transmission_links.csv`

**Purpose (F5, [#7](https://github.com/shaanbarca/eez/issues/7)).** Encode per-region transmission expansion plans + cross-island interconnection studies from RUPTL 2025–2034 §V.9 (regional Pengembangan Sistem Penyaluran sections). Drives the `comparator_feasibility` signal on the scorecard — when a site sits in a region whose only path to grid integration is a `kajian lebih lanjut` (further study) interconnection, the realistic comparator isn't PLN tariff, it's continued captive economics.

> **Spec discrepancy:** F5 spec referenced §V.11 (likely from an older RUPTL version). RUPTL 2025–2034 has the relevant content at §V.9.x per region. Schema + intent are unchanged.

**Schema:**

| Column | Type | Description |
|---|---|---|
| `link_id` | str | Synthetic ID — e.g. `SULAWESI_INTERCONNECT`, `SERAM::AMBON`, `PAPUA::PNG` |
| `from_region`, `to_region` | str | `grid_region_id` values (`SUMATERA`, `JAVA_BALI`, `KALIMANTAN`, `SULAWESI`, `MALUKU`, `PAPUA`, `NUSA_TENGGARA`, or `CROSS_BORDER`) |
| `voltage_kv` | int | Planned line voltage |
| `length_km` | float | Planned length where given; blank otherwise |
| `ruptl_section` | str | RUPTL subsection (e.g. `V.9.2`, `V.9.4`) |
| `status` | enum | `in_construction` / `pre_construction` / `under_study` / `not_feasible` / `cross_border` |
| `target_cod_year` | int | Target COD year if specified, blank otherwise |
| `verification_status` | enum | `confirmed` / `inferred` / `placeholder` |
| `ruptl_quote` | str | Direct Indonesian quote from RUPTL re feasibility |
| `source` | str | Page citation in the RUPTL PDF |
| `notes` | str | Free-form context |

**Coverage today.** 8 seed entries from RUPTL §V.9 cross-island interconnection passages (Sumatra–Java, Java–Lombok, Bangka–Belitung, Sulawesi internal, Sulbagsel–Baubau, Seram–Ambon, Malaka, Papua–PNG). All marked `inferred` pending domain review. Full regional substation pipeline transcription is a separate follow-up data task.

**Implementation.** Loaded by `src/pipeline/build_fct_transmission_link_ruptl_signal.py`. Output `outputs/data/processed/fct_transmission_link_ruptl_signal.csv` consumed by the scorecard enricher, which maps a site's `grid_region_id` to the worst-case feasibility status of its path to grid integration.

---

## `site_classifications.csv`

**Purpose (v4.1a §3, [#70](https://github.com/shaanbarca/eez/issues/70)).** Per-site override for `electricity_arrangement` + `captive_fuel_type` + `captive_capacity_mw` + `captive_share_estimated`. Per-site rows trump the §3.2 sectoral defaults in `build_fct_site_classifications.py`. Sites without overrides fall back to defaults with `classification_confidence='medium'`.

**Schema:**

| Column | Type | Description |
|---|---|---|
| `site_id` | str | Site identifier (must exist in `dim_sites`). |
| `electricity_arrangement` | enum | `grid_only` / `grid_primary_with_captive` / `hybrid_captive_primary` / `pure_captive`. Optional — leave blank to use sectoral default. |
| `captive_fuel_type` | enum | `coal_subcritical` / `coal_supercritical` / `natural_gas` / `oil_diesel` / `hybrid` / `none`. Optional. |
| `captive_capacity_mw` | float | Nameplate MW of on-site captive plant if applicable. |
| `captive_share_estimated` | float | 0.0–1.0 share of facility electricity from captive. |
| `classification_confidence` | enum | `high` (cited disclosure) / `medium` / `low`. Defaults to `high` for override rows when blank. |
| `notes` | str | Free-form rationale + citation. |

**Coverage today.** 6 anchor rows: IMIP, IWIP, Pupuk Kaltim Bontang, Krakatau Posco, Inalum (hydro-anchored hybrid), Freeport Gresik (gas-anchored grid-primary). All other 75 sites fall back to defaults.

---

## `captive_power_lcoe_defaults.csv` (v4.3 M-AT8a)

**Purpose.** Per-site captive power LCOE defaults with tier framing (T1/T2/T3). Renamed from `captive_generation_overrides.csv` in v4.3 M-AT8a; semantics expanded to cover **all captive sites** (~40 rows) rather than just the 6 v4.1a anchor overrides. Single column `captive_incumbent_lcoe_usd_mwh` on the scorecard reads from this file (was `captive_coal_lcoe_usd_mwh` + `captive_gas_lcoe_usd_mwh` in v4.1a — those columns are deleted).

**Schema:**

| Column | Type | Description |
|---|---|---|
| `site_id` | str | Site identifier (kebab-case — must match `dim_sites`). |
| `archetype` | str | Short descriptor (e.g. "IMIP nickel RKEF+HPAL", "Pupuk Kaltim fertilizer"). |
| `fuel_type` | str | `coal_subcritical` / `coal_supercritical` / `natural_gas` / `hydro`. Must match the site's `captive_fuel_type` in `fct_site_classifications.csv`. |
| `tier` | str enum | `T1` (high-confidence anchor) / `T2` (industry-archetype extrapolation) / `T3` (formula placeholder). |
| `default_lcoe_usd_mwh` | float | Site-specific captive LCOE ($/MWh). Scenario-invariant — anchor values don't track the market fuel-price slider. |
| `coal_cv_kcal_per_kg` | int/null | Coal calorific value (HHV) for coal-fueled sites. ~3,500 for low-CV imported subcritical; ~5,500 for mid-to-high CV supercritical. Null for non-coal. |
| `gas_pricing_regime` | str/null | `hgbt` (regulated $7/MMBtu — 7 covered sectors) / `market` (~$10/MMBtu non-HGBT) / `spot_lng` (~$14/MMBtu JKM). Null for non-gas. |
| `boiler_tech` | str | `subcritical` / `supercritical` / `ccgt` / `hydro`. |
| `cf_default` | float | Default capacity factor. ~0.85–0.95 captive baseload, ~0.45 hydro. |
| `source_citation` | str | Primary reference (Berkeley GSPP 2024, IESR LCOE Tool, Pupuk Indonesia disclosures, etc.). Placeholder rows tagged "formula placeholder". |

**Coverage today.** 4 T1 anchors (IMIP $50, Krakatau Posco $62, Pupuk Kaltim $50, Inalum $30 hydro), 7 T2 anchors (IWIP $55, Obi $58, Konawe $55, 4 Pupuk fertilizer T2 @ $55), ~30 T3 placeholders (coal at $63 formula at DMO; gas at $70 formula at HGBT; Freeport Manyar at $89 MARKET).

**Confidence bump.** Provenance sidecar (`fct_field_provenance.csv`) reflects tier status: any site in the CSV gets `confidence='high'` for `captive_incumbent_lcoe_usd_mwh`. Sites absent from the CSV (using formula fallback) get `confidence='medium'`. See `src/utils/provenance.py::_captive_lcoe_override_loader`.

**See also.** METHODOLOGY §13.9–§13.11 for the formula, tier definitions, and per-site rationale + citation trail.
