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
