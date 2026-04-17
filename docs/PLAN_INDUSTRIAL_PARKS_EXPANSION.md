# Plan: Industrial Parks Expansion — KEK Dashboard → Indonesia Industrial Decarbonization Platform

**Product spec:** `docs/industrial_parks_expansion_spec.md`
**Branch:** `feat/industrial-parks-expansion`

---

## Table of Contents

1. [Context](#context)
2. [What's Already Generic](#whats-already-generic-no-changes-needed)
3. [Design Principles](#design-principles)
4. [Architecture for Extensibility](#architecture-for-extensibility)
   - [DD1: SiteTypeConfig Registry](#design-decision-1-sitetypeconfig-registry)
   - [DD2: Captive Power Factory](#design-decision-2-captive-power-factory)
   - [DD3: Frontend Component Composition](#design-decision-3-frontend-component-composition)
   - [DD4: Type Safety](#design-decision-4-type-safety-to-prevent-rename-and-forgotten-variable-bugs)
   - [PyPSA Future Integration](#future-integration-pypsa-grid-optimization)
   - [Roadmap-Aware Design](#roadmap-aware-design-decisions)
5. [Existing Data Assets](#existing-data-assets-already-in-repo)
6. [Phase 1: Data Model Generalization](#phase-1-data-model-generalization)
7. [Phase 2: Rename Propagation](#phase-2-rename-propagation-kek_---site_)
8. [Phase 3: Add Priority 1 Sites](#phase-3-add-priority-1-sites)
9. [Phase 4: Frontend Sectoral Views](#phase-4-frontend-sectoral-views)
10. [Phase 5: New Fields from Spec](#phase-5-new-fields-from-spec)
11. [Files to Create / Modify](#files-to-create)
12. [Eng Review: Architecture Issues](#eng-review-architecture-issues-found)
13. [Implementation Order](#implementation-order-updated-with-eng-review)
14. [Eng Review: Quality, Tests, Performance](#eng-review-code-quality-tests-performance)
15. [Risk Mitigations](#risk-mitigations)
16. [TODOS.md Cross-Reference](#todosmd-cross-reference)
17. [Verification Checklist](#verification-checklist)
18. [NOT in Scope](#not-in-scope-this-branch)
19. [Appendix A: Methodology References](#appendix-a-methodology-references)

---

## Context

The dashboard currently analyzes 25 KEKs. Indonesia's industrial CO2 emissions come overwhelmingly from sites **outside** KEKs: Krakatau Steel in Cilegon, cement clusters across Java, Inalum in Asahan. The expansion adds ~20-25 Priority 1 sites (steel, cement, aluminum, fertilizer) to turn this from a KEK screening tool into Indonesia's first open-source industrial decarbonization planning platform.

---

## What's Already Generic (No Changes Needed)

Codebase exploration confirmed these are fully site-agnostic:
- `src/assumptions.py` — all 90+ constants work for any site type
- `src/model/basic_model.py` — LCOE formulas, action flags, economic tier, grid integration
- `frontend/src/lib/actionFlags.ts` — mode-aware flag helpers
- `frontend/src/lib/constants.ts` — color/label/description maps

**The expansion is a data+pipeline+UI exercise, not a business logic rewrite.**

---

## Design Principles

Every decision below is evaluated against these principles. When they conflict, the priority order is: **Readable > KISS > DRY > Low Coupling/High Cohesion**.

- **Low coupling:** Modules depend on interfaces (a dict key, a column name), not on each other's internals. Changing captive power logic doesn't require touching CBAM logic.
- **High cohesion:** Everything about a site type lives together. Everything about demand estimation lives together. No "a little bit in this file, a little bit in that file."
- **KISS:** Prefer a flat dict over a class hierarchy. Prefer a column in a CSV over a configuration framework. If a junior contributor can't understand the pattern in 30 seconds, it's too complex.
- **DRY:** The `_haversine_km()` function appears in 4 files today. That's a concrete bug risk, not an abstract concern. Fix it. But don't abstract things that only appear once.
- **Readable:** Code reads like a sentence. `SITE_TYPES["standalone"].demand_method` tells you what it does. `_compute_demand_type_3_v2()` does not.

---

## Architecture for Extensibility

This is an open source project. People will add new site types (petrochemical, textiles, mining), new data sources, new sectors. The architecture must make "add a new site type" a **1-file change**, not a 10-file scavenger hunt.

### The Problem

The original plan creates `if site_type == "kek"` branches in ~8 places: demand estimation, captive power matching, CBAM detection, ScoreDrawer rendering, marker shapes, reliability defaults, grid region assignment, identity display fields. Every new site type touches all 8. That's **high coupling** (change one type, edit 8 files) and **low cohesion** (type behavior scattered everywhere).

### Design Decision 1: SiteTypeConfig Registry

**What:** A frozen dataclass + dict mapping site type strings to their behavior config.

**Why this approach and not alternatives:**

| Alternative considered | Why rejected |
|----------------------|-------------|
| **Config columns in dim_sites.csv** (put `demand_method`, `marker_shape` as CSV columns) | KISS-er, but no validation. Typo `"sector_intesnity"` in CSV silently produces wrong results. Contributors edit CSVs, not Python. Safety at the boundary matters. |
| **Class hierarchy** (SiteType base class, KekSite(SiteType), StandaloneSite(SiteType)) | Over-engineered. These aren't different behaviors, they're different configs for the same behavior. A dict dispatch is simpler than polymorphism here. |
| **if/elif chains in each file** (the original plan) | Fails DRY and low coupling. Adding a type means editing 8 files. |
| **Plugin/decorator registration** (`@register_site_type("standalone")`) | Too clever. Harder to read than a flat dict. The number of site types will be <10, not <1000. A dict is fine. |

**Why a frozen dataclass:** Immutable. Can't accidentally mutate config at runtime. Follows `RESource` pattern already in `basic_model.py:77`.

**Why StrEnum for keys:** Same pattern as `ActionFlag` and `EconomicTier` (already in `basic_model.py:956-975`). Typo = import error. IDE autocomplete works.

**Coupling:** Pipeline modules import only `SITE_TYPES` dict and `SiteTypeConfig` type. They don't import each other. Demand estimation doesn't know about CBAM. CBAM doesn't know about captive power.

**Cohesion:** All behavior for `"standalone"` lives in one dict entry. All demand estimation logic lives in `demand_intensity.py`. No scattering.

The codebase already uses dict-based dispatch (`_SECTOR_CBAM_MAP` at `logic.py:1165`) and dataclass discriminators (`RESource` at `basic_model.py:77`). We extend that pattern, not invent a new one.

**New file: `src/model/site_types.py`**

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class SiteTypeConfig:
    """Everything that differs between site types. One entry = one type.
    
    Adding a new site type = adding one dict entry here.
    No other file needs modification for type-specific behavior.
    """
    demand_method: Literal["area_based", "sector_intensity"]
    captive_power_method: Literal["proximity", "direct"]
    cbam_method: Literal["3_signal", "direct"]
    default_reliability: float
    marker_shape: str                    # "circle", "diamond", "hexagon", "square"
    identity_fields: tuple[str, ...] = ()  # columns to show in ScoreDrawer identity section

SITE_TYPES: dict[str, SiteTypeConfig] = {
    "kek": SiteTypeConfig(
        demand_method="area_based",
        captive_power_method="proximity",
        cbam_method="3_signal",
        default_reliability=0.75,
        marker_shape="circle",
        identity_fields=("zone_classification", "category", "developer", "legal_basis", "area_ha"),
    ),
    "standalone": SiteTypeConfig(
        demand_method="sector_intensity",
        captive_power_method="direct",
        cbam_method="direct",
        default_reliability=0.90,
        marker_shape="diamond",
        identity_fields=("primary_product", "technology", "capacity_annual", "parent_company"),
    ),
    "cluster": SiteTypeConfig(
        demand_method="sector_intensity",
        captive_power_method="direct",
        cbam_method="direct",
        default_reliability=0.85,
        marker_shape="hexagon",
        identity_fields=("primary_product", "cluster_members", "capacity_annual", "parent_company"),
    ),
    "ki": SiteTypeConfig(
        demand_method="area_based",
        captive_power_method="proximity",
        cbam_method="direct",
        default_reliability=0.80,
        marker_shape="square",
        identity_fields=("sector", "area_ha", "developer"),
    ),
}
```

### How It's Used (No Conditionals in Business Logic)

**Demand estimation** (`build_fct_site_demand.py`):
```python
from src.model.site_types import SITE_TYPES

def estimate_demand(row):
    config = SITE_TYPES[row["site_type"]]
    return DEMAND_METHODS[config.demand_method](row)

DEMAND_METHODS = {
    "area_based": _area_based_demand,
    "sector_intensity": _sector_intensity_demand,
}
```

**CBAM detection** (`logic.py`):
```python
config = SITE_TYPES[site_type]
if config.cbam_method == "direct":
    product = row.get("cbam_product_type")
else:
    product = _detect_cbam_product_from_signals(row)
```

**Captive power** (see factory pattern below).

### Design Decision 2: Captive Power Factory

**The DRY violation today:** `_haversine_km()` is copy-pasted into 4 files (`build_fct_captive_coal.py:23`, `build_fct_captive_steel.py:23`, `build_fct_captive_cement.py:23`, `build_fct_captive_nickel.py`). The proximity-match loop (iterate sites, iterate plants, find nearest within buffer) is also duplicated 4 times with trivial differences.

**What's shared vs. what's different:**

| Shared (extract) | Different per builder (keep separate) |
|------------------|--------------------------------------|
| `haversine_km()` -- geometry math | Aggregation columns (coal: MW, steel: TPA, cement: MTPA) |
| Proximity loop -- site x plant distance check | Output column names |
| Distance filtering -- `<= buffer_km` | Chinese ownership detection (steel/cement have it, coal doesn't) |
| | Modal technology detection (steel only) |

**Why extract only the shared parts:** The aggregation IS the builder's identity. Each builder knows its domain (what columns to sum, what to call them). That's high cohesion. The geometry is generic infrastructure that doesn't belong to any single domain.

**New file: `src/pipeline/geo_utils.py`** (~60 lines, shared geospatial utilities — covers captive power builders AND `build_fct_substation_proximity.py`):

```python
def haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Single implementation. Imported by all captive power builders."""
    ...

def proximity_match(sites_df, plants_df, buffer_km, site_id_col="site_id") -> pd.DataFrame:
    """Generic: for each site, find plants within buffer_km. Returns plant rows with site_id + distance."""
    ...

def direct_match(sites_df, plants_df, site_id_col="site_id", plant_id_col="site_id") -> pd.DataFrame:
    """Direct: match by shared ID. For standalone sites that ARE the plant."""
    ...
```

Each captive builder becomes thin (~30 lines), keeping only its domain-specific aggregation:
```python
# build_fct_captive_steel.py (after refactor)
from .captive_power import proximity_match, direct_match
from src.model.site_types import SITE_TYPES

def build(dim_sites, gem_steel):
    prox_sites = dim_sites[dim_sites["site_type"].map(lambda t: SITE_TYPES[t].captive_power_method == "proximity")]
    direct_sites = dim_sites[dim_sites["site_type"].map(lambda t: SITE_TYPES[t].captive_power_method == "direct")]
    
    matched = pd.concat([
        proximity_match(prox_sites, gem_steel, 50),
        direct_match(direct_sites, gem_steel),
    ])
    return _aggregate_steel(matched)  # domain-specific: sum TPA, modal technology, etc.
```

**Why not a single generic captive power builder?** That would merge coal/steel/cement/nickel logic into one mega-function parameterized by config. Sounds DRY, but violates KISS and readability. Each builder is a separate pipeline step with its own CSV input and output. Keeping them separate means you can test, debug, and understand each one independently. The shared utility layer is the right level of abstraction.

**Line count:** ~520 lines (4 x 130) -> ~180 lines (60 shared + 4 x 30). Simpler to read, less surface area for bugs.

### Design Decision 3: Frontend Component Composition

**Why a TypeScript registry and not if/else in ScoreDrawer:**

ScoreDrawer is already 2,213 lines (`ScoreDrawer.tsx`). Adding `if (site_type === "kek") { ... } else if (site_type === "standalone") { ... }` blocks makes it longer and harder to read. More importantly, it couples the identity rendering to every site type, so adding `"mining"` later means editing this massive file.

**Why not separate components per type** (KekDrawer, StandaloneDrawer, etc.): That duplicates the tab structure, charts, and CBAM section across all drawers. The drawer layout is the same for every type. Only the identity section (name, type-specific fields) differs.

**The right split:** The drawer stays one component. The identity section reads from a config object. This follows the existing pattern in `constants.ts` where `ECONOMIC_TIER_COLORS`, `INFRA_READINESS_COLORS` are flat objects that drive rendering. No new concepts.

**New file: `frontend/src/lib/siteTypes.ts`** (~40 lines, mirrors Python registry):

```typescript
export type SiteType = "kek" | "standalone" | "cluster" | "ki";
export type Sector = "steel" | "cement" | "aluminium" | "fertilizer" | "nickel" | "mixed";

interface SiteTypeConfig {
  markerShape: "circle" | "diamond" | "hexagon" | "square";
  identityFields: string[];
  demandLabel: string;
  filterLabel: string;
  badgeColor: string;
}

export const SITE_TYPES: Record<SiteType, SiteTypeConfig> = {
  kek: {
    markerShape: "circle",
    identityFields: ["zone_classification", "category", "developer", "legal_basis", "area_ha"],
    demandLabel: "Area-based demand",
    filterLabel: "KEK (Special Economic Zone)",
    badgeColor: "blue",
  },
  standalone: {
    markerShape: "diamond",
    identityFields: ["primary_product", "technology", "capacity_annual", "parent_company"],
    demandLabel: "Production-based demand",
    filterLabel: "Standalone Plant",
    badgeColor: "amber",
  },
  cluster: {
    markerShape: "hexagon",
    identityFields: ["primary_product", "cluster_members", "capacity_annual", "parent_company"],
    demandLabel: "Cluster aggregate demand",
    filterLabel: "Industrial Cluster",
    badgeColor: "violet",
  },
  ki: {
    markerShape: "square",
    identityFields: ["sector", "area_ha", "developer"],
    demandLabel: "Area-based demand",
    filterLabel: "Industrial Park (KI)",
    badgeColor: "teal",
  },
};
```

ScoreDrawer identity section renders dynamically, no if/else:
```tsx
const config = SITE_TYPES[row.site_type];
{config.identityFields.map(field => (
  <InfoRow key={field} label={formatLabel(field)} value={row[field]} />
))}
```

**Why `Record<SiteType, ...>` not `Record<string, ...>`:** TypeScript will error if a SiteType member is missing from the object. Adding `"mining"` to the union type without adding the config entry = compile error. This is the TypeScript equivalent of the StrEnum safety on the Python side.

### "Add a New Site Type" Contributor Checklist

When someone wants to add a site type (e.g., `"mining_concession"`):

1. **Add registry entry** in `src/model/site_types.py` (1 dict entry)
2. **Add TS registry entry** in `frontend/src/lib/siteTypes.ts` (1 dict entry)
3. **Add rows** to `data/industrial_sites/` CSV (data, not code)
4. **Run pipeline** (`uv run python run_pipeline.py`)

That's it. No changes to demand estimation, captive power, CBAM, ScoreDrawer, markers, or the API. The registries drive all behavior.

If the new type needs a **new demand method** (not area-based or sector-intensity), add one function to `demand_intensity.py` and one key to `DEMAND_METHODS`. Still 2-file change, not 10.

### Design Decision 4: Type Safety to Prevent Rename and Forgotten-Variable Bugs

**The concrete problem we've hit:** Renaming `kek_id` -> `site_id` across 50+ string references. Miss one, and `df.merge(other, on="site_id")` joins against a column that doesn't exist in one table. Pandas returns all NaN for the unmatched columns. No error. The scorecard loads, the map renders, the numbers are just silently wrong. This is the worst class of bug.

**Why enums and not just careful find-and-replace:** Find-and-replace catches the string `"kek_id"`. It doesn't catch `f"kek_{suffix}"`, variable names like `kek_df`, or comments referencing the old name. Enums make the reference a Python/TypeScript symbol that the linter can trace.

**The fix has three layers:**

**Layer 1: StrEnum for discriminator fields** (same pattern as `ActionFlag`, `EconomicTier` in `basic_model.py:956-975`)

```python
# src/model/site_types.py

class SiteType(StrEnum):
    KEK = "kek"
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    KI = "ki"

class Sector(StrEnum):
    STEEL = "steel"
    CEMENT = "cement"
    ALUMINIUM = "aluminium"
    FERTILIZER = "fertilizer"
    NICKEL = "nickel"
    MIXED = "mixed"
```

Typo on `SiteType.STANDALNOE` fails at import time. `row["site_type"] == SiteType.STANDALONE` is checked by the linter. Adding a new type means adding one enum member, and the type checker flags every `match`/`if` that doesn't handle it.

**Layer 2: Column name constants** (deferred to v1.3)

```python
# src/model/columns.py

class Col:
    """Column names used across pipeline and API. Rename here, not in 50 files."""
    SITE_ID = "site_id"
    SITE_NAME = "site_name"
    SITE_TYPE = "site_type"
    SECTOR = "sector"
    # ... all 80+ scorecard columns
```

Pipeline builders use `Col.SITE_ID` instead of `"site_id"`. If tomorrow we rename to `"location_id"`, one change propagates everywhere. IDE "Find All References" works on class attributes, not on string literals.

**Why deferred:** The Col class requires changing every `row["site_id"]` reference in the codebase to `row[Col.SITE_ID]`. That's a large diff that mixes with the functional changes. Better approach: add Col in a separate PR after the expansion ships, incrementally, one pipeline file at a time. Layer 1 (StrEnums) and Layer 3 (TypeScript types) give us 80% of the safety with 20% of the churn.

**Layer 3: TypeScript union types** (already the pattern in `types.ts`)

```typescript
// frontend/src/lib/types.ts
export type SiteType = "kek" | "standalone" | "cluster" | "ki";
export type Sector = "steel" | "cement" | "aluminium" | "fertilizer" | "nickel" | "mixed";

export interface ScorecardRow {
  site_id: string;
  site_name: string;
  site_type: SiteType;  // not string -- compiler checks all uses
  sector: Sector;
  // ...
}
```

`npx tsc --noEmit` catches missing fields, wrong types, and unknown enum values at compile time. `ScorecardRow` is the contract between backend and frontend.

**Priority order for this expansion:**
1. StrEnums (`SiteType`, `Sector`) -- do now, prevents the most common bug
2. TypeScript union types -- do now, compiler catches missing fields
3. Col class -- do later, incremental adoption

### What This Replaces in the Plan

The Phase 1-4 implementation stays the same, but the approach changes:
- Phase 1 gains `src/model/site_types.py` as Step 0 (the registry defines everything)
- Phase 1D (captive power dual-mode) becomes a factory refactor, not 4 separate `if/else` edits
- Phase 1E (CBAM) is a 3-line lookup from the registry, not a conditional block
- Phase 4C (ScoreDrawer) renders from registry config, no `if (site_type === "kek")` branches
- Phase 4B (markers) reads `config.markerShape` from registry

### Future Integration: PyPSA Grid Optimization

The data model is being designed to export cleanly to [PyPSA](https://pypsa.org/) (Python for Power System Analysis) for grid optimization and capacity expansion planning. Not built now, but the architecture should not block it.

**What PyPSA needs from our data:**
- **Buses** (nodes): each site -> a PyPSA bus. `site_id`, coordinates, voltage level from `fct_substation_proximity`
- **Generators**: RE capacity at each site -> PyPSA generators. `max_captive_capacity_mwp`, `cf`, LCOE parameters
- **Loads**: site demand -> PyPSA loads. `demand_gwh` from `fct_site_demand`
- **Lines**: grid connections -> PyPSA lines. `fct_substation_proximity` already has substation capacity (MVA), distance, and `pln_grid_lines.geojson` has transmission topology

**What this means for current design:**
- Keep capacity in consistent units (MW/MWp, not mixed with TPA except in display)
- Keep `grid_region_id` consistent with PLN system topology (already mapped from substation `regpln`)
- The star schema join path `site -> substation -> grid_region -> RUPTL` is the natural PyPSA adapter boundary
- A future `src/integrations/pypsa_export.py` would read dim_sites + fact tables and build a `pypsa.Network`, no schema changes needed

**Not in scope now.** But every schema decision should ask: "Would this make the PyPSA adapter harder?" If yes, reconsider.

### Roadmap-Aware Design Decisions

Known future features that inform today's architecture choices:

| Future Feature | What it needs from us | Design implication |
|---------------|----------------------|-------------------|
| **PyPSA grid optimization** | Sites as buses, RE as generators, demand as loads, grid lines as edges | Keep MW units clean, star schema joins = PyPSA network topology |
| **PLN Supergrid visualization** | Transmission corridors, substation connectivity, inter-island links | `pln_grid_lines.geojson` (1,595 lines) already exists. Keep `grid_region_id` as the stable join key to RUPTL + supergrid corridor data |
| **Perpres 112/2022 compliance** | Captive coal commissioning year, phase-out deadlines per plant | `fct_captive_coal` already has plant-level data. Nullable columns reserved in plan Phase 5B |
| **Priority 2-3 sites** (petrochemical, mining, refining) | New site_type entries, possibly new sectors | SiteTypeConfig registry: 1-entry addition per type, no code changes |
| **Process emissions (Scope 1)** | Sector-specific calcination/electrolysis models | New fact table `fct_process_emissions`, joins on `site_id` + `sector`. Doesn't modify existing LCOE pipeline |

**Principle:** Each future feature should be addable as a new module (pipeline step, fact table, frontend component) that joins on `site_id`. The core pipeline (dim_sites -> fct_lcoe -> scorecard) stays untouched.

---

## Existing Data Assets (Already in Repo)

Before collecting new data, leverage what we already have:

| File | Records | What it provides |
|------|---------|-----------------|
| `data/industrial_data/*.shp` | 5,159 points | All Indonesian industrial facilities (50k+ employees, 2023). Name, province, district, industry classification code (`klskbli`), coordinates. Useful for cluster identification. |
| `data/industrial_location_info.csv` | 5,164 rows | Same data as CSV with geometry column. |
| `data/captive_power/gem_steel_plants.csv` | 7 plants | GEM Global Iron & Steel Tracker. Lat/lon, capacity TPA, technology (EAF/BF-BOF), ownership. |
| `data/captive_power/gem_cement_plants.csv` | 32 plants | GEM Global Cement Tracker. Lat/lon, capacity MTPA, plant type, ownership. |
| `data/captive_power/cgsp_nickel_tracker.csv` + `.json` | ~150+ entries | CGSP Nickel Tracker. Capacity, process type, ESG indicators, ownership, lat/lon. Geographic clusters visible: Morowali, Halmahera, Obi, Konawe. |
| `data/captive_power/gem_coal_plant_tracker_indonesia.csv` | 150+ entries | Coal plants with captive/industrial applications. |
| `data/wiup_indonesia.csv` | 8,557 rows | WIUP mining permits. Island, commodity, concession area, permit dates. Context for nickel/coal site identification. |

**Key insight:** The 5,159-point industrial shapefile can validate and enrich manual cluster definitions. Cross-reference `klskbli` industry codes with GEM plant data to identify facilities we might miss with manual curation alone.

---

## Phase 1: Data Model Generalization

**Goal:** Rename `kek_*` -> `site_*` throughout, add `site_type` discriminator, keep backward compat aliases during transition.

### 1A: Master Dimension Table

**Rename:** `build_dim_kek.py` -> `build_dim_sites.py`

New unified table `dim_sites.csv` with schema:

| Column | Type | Source (KEK) | Source (Industrial) |
|--------|------|-------------|-------------------|
| `site_id` | string | existing `kek_id` slug | new slug from plant name |
| `site_name` | string | existing `kek_name` | plant/park name |
| `site_type` | enum | `"kek"` for all 25 | `"ki"`, `"standalone"`, `"cluster"` |
| `sector` | string | inferred from `business_sectors` | direct from source data |
| `primary_product` | string | null for most KEKs | `"crude_steel"`, `"clinker"`, etc. |
| `province` | string | existing | from plant data |
| `latitude` | float | existing | from plant data |
| `longitude` | float | existing | from plant data |
| `area_ha` | float | from polygon | estimated or null |
| `grid_region_id` | string | from mapping CSV | auto-assign from nearest substation `regpln` |
| `reliability_req` | float | from mapping CSV | sector-based default (0.8 for manufacturing) |
| `capacity_annual` | string | null | `"4,000,000 TPA"`, `"15.0 MTPA"` |
| `capacity_annual_tonnes` | float | null | numeric extraction from capacity_annual (e.g., 4000000.0) |
| `technology` | string | null | `"EAF"`, `"BF-BOF"`, `"Integrated"` |
| `parent_company` | string | `developer` field | from source data |
| `cbam_product_type` | string | null (inferred by 3-signal) | direct assignment |

**Data sources for new sites:**
- Steel: `data/captive_power/gem_steel_plants.csv` (7 plants, already has lat/lon/capacity/tech)
- Cement: `data/captive_power/gem_cement_plants.csv` (32 plants, already has lat/lon/capacity)
- Aluminum: manual entry (Inalum Asahan, Freeport Gresik) -- 2 sites
- Fertilizer: manual entry (Pupuk Kaltim Bontang, Pupuk Sriwidjaja Palembang, Pupuk Petrokimia Gresik) -- 3 sites
- Nickel (non-KEK): manual entry (Weda Bay, Obi Island, Konawe) -- 3 sites

**New file:** `data/industrial_sites/priority1_sites.csv` -- master list of ~20 new sites with all columns above.

### 1B: Pipeline DAG Refactoring

**Modify:** `run_pipeline.py`

Current DAG starts with `dim_kek`. Refactor to:

```
Stage 0: Build unified dim_sites
|-- Read existing dim_kek (25 KEKs)
|-- Read priority1_sites.csv (new industrial sites)
|-- Union into dim_sites.csv with site_type discriminator
+-- Auto-assign grid_region_id for new sites (nearest substation regpln)

Stage 1: Resource extraction (runs on all sites in dim_sites)
|-- fct_site_resource (solar PVOUT -- replaces fct_kek_resource)
|-- fct_site_wind_resource (wind speed/CF -- replaces fct_kek_wind_resource)
+-- fct_site_demand (demand estimation -- replaces fct_kek_demand)

Stage 2: Grid & infrastructure (unchanged logic, new naming)
|-- fct_substation_proximity (already generic, just reads from dim_sites)
|-- fct_grid_cost_proxy (unchanged -- keyed on grid_region)
+-- fct_ruptl_pipeline (unchanged -- keyed on grid_region)

Stage 3: LCOE computation
|-- fct_lcoe (unchanged formula, reads from dim_sites)
+-- fct_lcoe_wind

Stage 4: Captive power (modified for dual-mode)
|-- fct_captive_coal (for KEK sites: proximity match; for standalone: direct assignment)
|-- fct_captive_nickel (same dual-mode)
|-- fct_captive_steel (same dual-mode)
+-- fct_captive_cement (same dual-mode)

Stage 5: Final scorecard
+-- fct_site_scorecard (replaces fct_kek_scorecard, adds site_type + sector columns)
```

**Key change in captive power builders:** For `site_type != "kek"`, skip the 50km proximity scan. The site IS the plant. Map directly: `site_id` -> plant data.

### 1C: New Assumptions in `src/assumptions.py`

Several expansion parameters are susceptible to change and should be configurable defaults, not hardcoded. Follow the existing pattern: constant + source comment + rationale.

**New constants to add:**

```python
# --- SECTOR DEMAND ESTIMATION (Industrial Parks Expansion) ---

SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE: dict[str, float] = {
    # NOTE: These are ELECTRICITY-ONLY consumption for RE demand sizing.
    # For CBAM total energy intensity (incl. thermal), see CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE.
    # Values differ significantly: cement 0.11 here vs 0.9 CBAM (includes kiln thermal).
    "steel_eaf": 0.50,       # Electric arc furnace: 0.4-0.6 MWh/t (IRENA 2020)
    "steel_bfbof": 0.20,     # Blast furnace-BOF: 0.15-0.30 MWh/t (IRENA 2020)
    "cement": 0.11,           # Cement grinding + kiln aux: 0.09-0.13 MWh/t (IEA Cement Roadmap)
    "aluminium": 15.0,        # Primary smelting (Hall-Heroult): 13-17 MWh/t (IAI 2023)
    "fertilizer_ammonia": 1.0, # Ammonia/urea: 0.8-1.2 MWh/t (IFA 2022)
    "nickel_rkef": 37.5,      # RKEF ferro-nickel/NPI: 30-45 MWh/t (JETP Ch.2)
    "nickel_hpal": 8.0,       # HPAL (hydromet): 6-10 MWh/t
}

SECTOR_RELIABILITY_REQUIREMENT: dict[str, float] = {
    "steel": 0.90,            # Continuous process -- furnace cannot cold-start cheaply
    "cement": 0.80,           # Kiln is continuous but grinding can flex
    "aluminium": 0.95,        # Smelter pots freeze if power drops -- catastrophic
    "fertilizer": 0.85,       # Ammonia synthesis continuous, some storage buffer
    "nickel": 0.90,           # RKEF furnaces similar to steel
    "mixed": 0.75,            # KEK default -- mixed tenants, some flexibility
}

CLUSTER_PROXIMITY_THRESHOLD_KM: float = 15.0
# Maximum distance (km) between facilities to be treated as a single analytical
# cluster (site_type = "cluster"). Source: typical industrial estate footprint 5-20km.
```

**Relationship to existing CBAM constants:** `CBAM_ELECTRICITY_INTENSITY_MWH_PER_TONNE` (line 591) already exists with similar values. The new `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` is for demand estimation (RE sizing), not emission calculation. Some values will match (aluminum = 15.0 in both), others differ (cement CBAM = 0.9, demand = 0.11 because CBAM includes thermal energy conversion factor). Keep both; document the distinction.

### 1D: Demand Estimation for Non-KEK Sites

Current `fct_kek_demand` uses KEK area x demand intensity. For standalone plants, use `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE` from `assumptions.py`:

Formula: `demand_gwh = capacity_tonnes_per_year x intensity_mwh_per_tonne / 1e3`

Demand estimation branches on `site_type` via SiteTypeConfig registry dispatch:
- `"kek"` -> existing area-based formula (unchanged)
- `"standalone"` / `"cluster"` -> sector intensity formula
- `"ki"` -> area-based if `area_ha` is available, else sector intensity fallback

**New file:** `src/pipeline/demand_intensity.py` -- thin wrapper that reads from `assumptions.py` and applies the formula. No hardcoded values in this file.

### 1E: CBAM Direct Assignment

**Modify:** `src/dash/logic.py` (CBAM section, lines 1138-1254)

For sites with `cbam_product_type` already set (non-KEK sites), skip the 3-signal detection and use the direct value. The 3-signal inference remains for KEK sites where product type is inferred from proximity + business sectors.

```python
# Pseudocode
if row.get("cbam_product_type"):
    # Direct assignment -- standalone industrial site
    product = row["cbam_product_type"]
else:
    # 3-signal detection -- KEK sites
    product = _detect_cbam_product_from_signals(row)
```

### 1F: Cluster Identification from Spatial Data

**Approach:** Use existing data to identify industrial clusters rather than pure manual curation.

**Step 1: Cross-reference GEM plants with industrial shapefile**
- The 5,159-point shapefile (`data/industrial_data/`) has `klskbli` industry classification codes
- Filter for relevant KBLI codes: 24xx (metals), 23xx (non-metallic minerals/cement), 20xx (chemicals/fertilizer)
- Match against GEM steel/cement CSVs by proximity (same haversine pattern from `build_fct_captive_*.py`)
- This catches facilities GEM missed and validates coordinates

**Step 2: Spatial clustering of matched facilities**
- Group facilities within `CLUSTER_PROXIMITY_THRESHOLD_KM` (15km default, configurable in `assumptions.py`)
- Use the existing `_haversine_km()` function from captive power builders
- Clusters with 2+ CBAM-relevant facilities become `site_type = "cluster"`
- Single isolated facilities become `site_type = "standalone"`

**Known clusters from spec + shapefile validation:**
- **Cilegon cluster:** Krakatau Steel + Gunung Steel + Chandra Asri (steel + petrochemical)
- **Gresik cluster:** Semen Gresik + Petrokimia Gresik + Freeport Smelter (cement + fertilizer + aluminum)
- **Bontang cluster:** Pupuk Kaltim + PT Badak LNG (fertilizer + LNG)
- **Tuban cluster:** Semen Gresik Tuban + TPPI (cement + petrochemical)

**Step 3: Cluster-level aggregation**
- `cluster_demand_gwh` = sum of member facility demands
- `cluster_capacity_tpa` = sum by product type
- `cluster_cbam_product_types` = list of distinct products
- Centroid = coordinates of **largest member facility** by capacity (not geographic mean, which could land in water for coastal clusters)

### 1G: Grid Region Auto-Assignment

**New function in** `build_dim_sites.py`:

For new sites without manual `grid_region_id`, assign by finding the nearest substation from `data/substation.geojson` (2,913 points) and using its `regpln` field.

This is the same data source `fct_substation_proximity` uses, but applied at dim-table build time.

---

## Phase 2: Rename Propagation (kek_* -> site_*)

**Scope:** Every file that references `kek_id`, `kek_name`, `selectedKek`, `KekMarkers`, etc.

### Backend renames

| File | Change |
|------|--------|
| `src/pipeline/build_fct_kek_scorecard.py` | Rename to `build_fct_site_scorecard.py`, update column names |
| `src/pipeline/build_fct_kek_resource.py` | Rename to `build_fct_site_resource.py` |
| `src/pipeline/build_fct_kek_wind_resource.py` | Rename to `build_fct_site_wind_resource.py` |
| `src/pipeline/build_fct_kek_demand.py` | Rename to `build_fct_site_demand.py` |
| `src/pipeline/build_dim_kek.py` | Rename to `build_dim_sites.py` |
| `src/dash/logic.py` | `kek_id` -> `site_id` in scorecard computation |
| `src/dash/data_loader.py` | Update CSV filenames |
| `src/dash/map_layers.py` | `kek_polygons` -> `site_polygons` |
| `src/api/routes/scorecard.py` | Update merge keys, comments |
| `src/api/routes/layers.py` | Rename `/api/kek/{kek_id}/` -> `/api/site/{site_id}/` (3 routes) |
| `run_pipeline.py` | Update step names and file references |
| All `build_fct_captive_*.py` | `kek_id` -> `site_id` in output columns |

### Frontend renames

| File | Change |
|------|--------|
| `frontend/src/lib/types.ts` | `kek_id` -> `site_id`, `kek_name` -> `site_name`, add `site_type` |
| `frontend/src/lib/api.ts` | `fetchKekPolygon` -> `fetchSitePolygon`, update URL paths |
| `frontend/src/store/dashboard.ts` | `selectedKek` -> `selectedSite`, `filteredKekIds` -> `filteredSiteIds` |
| `frontend/src/components/map/KekMarkers.tsx` | Rename to `SiteMarkers.tsx` |
| `frontend/src/components/map/KekSearch.tsx` | Rename to `SiteSearch.tsx` |
| `frontend/src/components/table/columns.tsx` | Update column accessors |
| `frontend/src/components/table/DataTable.tsx` | Update filter references |
| `frontend/src/components/panels/ScoreDrawer.tsx` | Generalize "KEK" labels, add site_type conditionals |
| `frontend/src/components/ui/Header.tsx` | Update title: "Indonesia Industrial Decarbonization Dashboard" |

### Test renames

| File | Change |
|------|--------|
| `tests/test_model.py` | Update any `kek_id` references in test data |
| `tests/test_pipeline.py` | Update scorecard column assertions |
| `tests/test_api.py` | Update endpoint paths if changed |

**Strategy:** Do the rename in ONE commit with find-and-replace across the repo. Clean break, no backward compat aliases (zero external API consumers, frontend and backend deploy together). Update notebooks in the same commit. Skip legacy `src/dash/app.py` (1,763 lines, zero imports, dead code).

---

## Phase 3: Add Priority 1 Sites

### 3A: Data Collection

Create `data/industrial_sites/priority1_sites.csv` with ~20 sites:

**Steel (7 from GEM + manual enrichment):**
- Krakatau Steel (Cilegon), Gunung Steel (Cilegon), Dexin Steel (Morowali), Sulawesi Mining (Morowali), Master Steel, Jatake, others

**Cement (top 10-12 from GEM by capacity):**
- Semen Gresik Tuban, Semen Padang, Indocement Citeureup, Holcim Narogong, Semen Tonasa, others

**Aluminum (2 manual):**
- Inalum (Asahan, North Sumatra), Freeport Smelter (Gresik)

**Fertilizer (3 manual):**
- Pupuk Kaltim (Bontang), Pupuk Sriwidjaja (Palembang), Petrokimia Gresik

**Nickel non-KEK (3 manual):**
- Weda Bay Industrial Park, Obi Island, Konawe

### 3B: Pipeline Run

Run the full pipeline on all ~45 sites (25 KEK + 20 new):
1. Extract solar PVOUT at each new site centroid + best within 50km
2. Extract wind speed at each site
3. Find nearest substations
4. Compute LCOE at 9 WACC values x 2 scenarios
5. Compute action flags, economic tier, infrastructure readiness
6. Compute CBAM exposure (direct assignment for non-KEK)
7. Assemble unified scorecard

### 3C: Validation

Compare results for sites near existing KEKs:
- Dexin Steel (Morowali) should have similar PVOUT/LCOE to KEK Morowali
- Semen Gresik (Tuban) should have similar grid cost to KEK Gresik
- Spot-check 5 sites against public benchmarks

---

## Phase 4: Frontend Sectoral Views

### 4A: Sector Filter

**Modify:** `frontend/src/components/table/DataTable.tsx`
- Add `sector` to `DROPDOWN_COLUMNS`
- Values: "Steel", "Cement", "Aluminum", "Fertilizer", "Nickel", "Mixed/KEK"

**Modify:** `frontend/src/components/table/columns.tsx`
- Add `sector` column with color-coded badges
- Add `site_type` column (KEK / KI / Standalone / Cluster)

### 4B: Map Differentiation

**Modify:** `SiteMarkers.tsx` (formerly KekMarkers)
- Marker shapes driven by `siteTypes.ts` registry config
- KEKs: circles (existing)
- Standalone plants: diamonds
- Clusters: hexagons
- Industrial parks: squares
- Color still by economic tier (existing)

### 4C: ScoreDrawer Site-Type Awareness

**Modify:** `ScoreDrawer.tsx`
- Identity section renders from `siteTypes.ts` registry config (no if/else chains)
- Demand section: show computed demand from electricity intensity (not area-based) for non-KEK sites
- CBAM section: works unchanged (already generic)

### 4D: Sectoral Aggregation (New Component)

**New file:** `frontend/src/components/charts/SectorSummaryChart.tsx`
- Bar chart: total CBAM exposure by sector (2026, 2030, 2034)
- Bar chart: total emissions by sector
- Table: sector x count of sites by action flag

This is a new tab or a new chart in the overview area.

---

## Phase 5: New Fields from Spec

### 5A: Pathway Flag

**New function in** `basic_model.py`:

```python
def pathway_flag(action_flag, economic_tier, wacc_flip_tier, cbam_adjusted_gap_pct):
    if action_flag == "solar_now": return "ready_now"
    if action_flag in ("invest_transmission", "invest_substation"): return "ready_with_grid_upgrade"
    if wacc_flip_tier <= 8: return "ready_with_concessional_finance"
    if cbam_adjusted_gap_pct < 0: return "ready_with_cbam_cost_stack"
    return "requires_structural_change"
```

### 5B: Perpres 112/2022 Fields (Deferred)

These require captive coal commissioning year data not yet available. Defer to Phase 4 of the spec (iteration based on user feedback). Add columns as nullable:
- `captive_coal_commissioning_year` -- null until populated
- `years_to_perpres_deadline` -- null
- `timeline_conflict_flag` -- null
- `corridor_arrival_year` -- null (requires RUPTL Super Grid corridor data)

### 5C: Sectoral Aggregation Metrics (Frontend-Only)

Computed in the frontend from the scorecard array:
- `sector_total_demand_gwh` -- sum by sector
- `sector_cbam_cost_2030_usd` -- sum by sector
- `sector_sites_solar_now` -- count by sector where action_flag == solar_now

No new backend columns needed. Frontend aggregates at render time.

---

## Files to Create

| File | Purpose |
|------|---------|
| **`src/model/site_types.py`** | **SiteTypeConfig registry + SiteType/Sector StrEnums (the architecture spine)** |
| **`src/pipeline/geo_utils.py`** | **Shared haversine, proximity_match, direct_match (replaces 5x duplication incl. substation_proximity)** |
| **`frontend/src/lib/siteTypes.ts`** | **TypeScript mirror of SiteTypeConfig registry** |
| `data/industrial_sites/priority1_sites.csv` | Master list of ~20 Priority 1 industrial sites |
| `src/pipeline/build_dim_sites.py` | Unified dimension table builder (KEKs + industrial sites) |
| `src/pipeline/build_fct_site_resource.py` | Renamed from build_fct_kek_resource.py |
| `src/pipeline/build_fct_site_wind_resource.py` | Renamed |
| `src/pipeline/build_fct_site_demand.py` | Renamed, with sector-based demand estimation via registry dispatch |
| `src/pipeline/build_fct_site_scorecard.py` | Renamed, with site_type + sector columns |
| `src/pipeline/demand_intensity.py` | Electricity intensity lookup by sector/technology |
| `frontend/src/components/map/SiteMarkers.tsx` | Renamed from KekMarkers.tsx, marker shape from siteTypes.ts |
| `frontend/src/components/map/SiteSearch.tsx` | Renamed from KekSearch.tsx |
| `frontend/src/components/charts/SectorSummaryChart.tsx` | New sectoral aggregation view |

## Files to Modify

| File | Change |
|------|--------|
| `run_pipeline.py` | Updated DAG with renamed steps |
| `src/assumptions.py` | Add sector intensity, reliability, cluster threshold constants |
| `src/dash/logic.py` | CBAM direct assignment via SiteTypeConfig, kek_id -> site_id |
| `src/dash/data_loader.py` | Updated CSV paths |
| `src/dash/map_layers.py` | site_polygons |
| `src/api/routes/scorecard.py` | site_id merge keys |
| `src/api/routes/layers.py` | `/api/kek/` -> `/api/site/` route paths |
| `frontend/src/lib/types.ts` | ScorecardRow with site_type, sector |
| `frontend/src/lib/api.ts` | Updated fetch function names and URL paths |
| `frontend/src/store/dashboard.ts` | selectedSite, filteredSiteIds |
| `frontend/src/components/table/columns.tsx` | sector + site_type columns |
| `frontend/src/components/table/DataTable.tsx` | sector in DROPDOWN_COLUMNS |
| `frontend/src/components/panels/ScoreDrawer.tsx` | Site-type-aware rendering from registry |
| `frontend/src/components/ui/Header.tsx` | Updated title |
| All `build_fct_captive_*.py` | Dual-mode via shared factory + SiteTypeConfig dispatch |
| `tests/test_model.py` | Updated test data |
| `tests/test_pipeline.py` | Parameterized column/row count assertions |
| `tests/test_api.py` | Updated endpoint assertions |

---

## Eng Review: Architecture Issues Found

Cross-referencing the plan against `DESIGN.md`, `ARCHITECTURE.md`, `DATA_DICTIONARY.md`, and the actual codebase surfaced these gaps. Each needs resolution before implementation.

### Issue 1: API Backward Compatibility (Breaking Change)

Three routes use `/api/kek/{kek_id}/` in the URL path:
- `src/api/routes/layers.py:99` -- `GET /api/kek/{kek_id}/polygon`
- `src/api/routes/layers.py:122` -- `GET /api/kek/{kek_id}/buildable`
- `src/api/routes/layers.py:131` -- `GET /api/kek/{kek_id}/substations`

Frontend calls match (`frontend/src/lib/api.ts:39-56`): `fetchKekPolygon()`, `fetchKekBuildable()`, `fetchKekSubstations()`.

**Fix:** Rename to `/api/site/{site_id}/...`. Since frontend and backend deploy together and there's no public API contract, a clean rename is fine. No aliases needed. Add to Phase 2 rename table.

### Issue 2: `capacity_annual` Needs Numeric Companion Column

The dim_sites schema has `capacity_annual` as string (`"4,000,000 TPA"`). But `demand_intensity.py` needs a numeric value for `demand_gwh = capacity_tpa x intensity / 1e3`.

**Fix:** Add `capacity_annual_tonnes` (float) column to dim_sites schema. Parse from the string during `build_dim_sites.py`. The string column stays for display.

### Issue 3: Cluster Centroid Selection

Plan originally said "Centroid = geographic mean of member coordinates." If Cilegon cluster members span the coast, the geographic mean could land in the Java Sea.

**Fix:** Use coordinates of the **largest member facility** by capacity, not the geographic mean. Simpler and always lands on an actual industrial site.

### Issue 4: fct_lcoe Row Count Growth

Currently 450 rows (25 KEKs x 9 WACC x 2 scenarios). With ~45 sites: **810 rows**. Not a performance concern, but test assertions checking `len(fct_lcoe) == 450` will fail.

**Fix:** Parameterize test assertions. Use `len(dim_sites) * 9 * 2` instead of hardcoded 450.

### Issue 5: Documentation Step Incomplete

Original step 12 listed: CLAUDE.md, DATA_DICTIONARY.md, EXECUTIVE_SUMMARY.md, PERSONAS.md.

Missing from the list:
- **DESIGN.md** -- state slices change (`selectedKek` -> `selectedSite`, `filteredKekIds` -> `filteredSiteIds`), ScorecardRow type gains `site_type`/`sector` fields, new sector dropdown filter, marker shape differentiation
- **ARCHITECTURE.md** -- mermaid diagram changes (`dim_kek` -> `dim_sites`), module map gains new files (`demand_intensity.py`, `build_dim_sites.py`), pipeline stages renumbered
- **TODOS.md** -- items L16, M17, L14, L2, C1, C4 are directly addressed or partially closed by this expansion

**Fix:** Add all three to step 15 in the updated implementation order.

### Issue 6: Demand Estimation Formula Needs Guard

`demand_gwh = capacity_annual_tonnes x intensity / 1e3` works for standalone plants. But for clusters, you sum member demands. What about KEKs that happen to have a `capacity_annual_tonnes` value? (Some KEKs might get one later.)

**Fix (decided):** Demand estimation branches on `site_type` via SiteTypeConfig registry:
- `"kek"` -> existing area-based formula (unchanged)
- `"standalone"` / `"cluster"` -> sector intensity formula
- `"ki"` -> area-based if `area_ha` is available, else sector intensity fallback

---

## Implementation Order (Updated with Eng Review)

Build bottom-up, each step testable. Changes from eng review in **bold**:

0. **`src/model/site_types.py`** -- **SiteTypeConfig registry (the single source of truth for per-type behavior)**
1. **`src/assumptions.py`** -- add `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE`, `SECTOR_RELIABILITY_REQUIREMENT`, `CLUSTER_PROXIMITY_THRESHOLD_KM`
2. **`frontend/src/lib/siteTypes.ts`** -- **TypeScript mirror of SiteTypeConfig registry**
3. `data/industrial_sites/priority1_sites.csv` -- curate master data file **with `capacity_annual_tonnes` float column**
4. `src/pipeline/demand_intensity.py` -- sector electricity intensity lookup + tests. **Reads method from SiteTypeConfig, no conditionals.**
5. **`src/pipeline/geo_utils.py`** -- **Extract shared `haversine_km()`, `proximity_match()`, `direct_match()` from 4 duplicated builders**
6. `src/pipeline/build_dim_sites.py` -- unified dimension table (union KEKs + new sites) + tests. **Cluster centroid = largest member by capacity.**
7. Rename propagation -- one big commit: kek_* -> site_* across backend, frontend, tests. **Include API route paths `/api/kek/` -> `/api/site/`.**
8. Captive power refactor -- **thin builders using shared factory + SiteTypeConfig dispatch**
9. CBAM direct assignment -- modify `logic.py` for SiteTypeConfig-driven CBAM method + tests
10. Pipeline run -- execute full pipeline, produce `fct_site_scorecard.csv` with ~45 rows
11. Validate -- spot-check LCOE, action flags, CBAM exposure for 5 new sites. **Parameterize test assertions (no hardcoded row counts).**
12. Frontend site_type awareness -- ScoreDrawer renders from **siteTypes.ts registry**, sector column, marker shapes from config
13. Sectoral aggregation -- SectorSummaryChart component
14. Manual testing -- full browser walkthrough with new sites
15. Documentation -- update CLAUDE.md, DATA_DICTIONARY.md, EXECUTIVE_SUMMARY.md, PERSONAS.md, **DESIGN.md, ARCHITECTURE.md, TODOS.md**
16. **Sync `docs/PLAN_INDUSTRIAL_PARKS_EXPANSION.md`** -- apply all eng review fixes + hyperlinked sources

---

## Eng Review: Code Quality, Tests, Performance

**Code quality:** Plan correctly reuses existing patterns. `_haversine_km()` from captive power builders for clustering. Builder function pattern (`build_dim_sites()` -> DataFrame) for the new dim table. Star schema join keys. No new abstractions needed.

**Test strategy:** Each implementation step includes tests. Key risk is step 7 (rename propagation), where all 433 tests must pass immediately. Mitigation: run `uv run pytest tests/ -x` after the rename commit, before any logic changes. Also: parameterize fct_lcoe row count assertions to `len(dim_sites) * 18` instead of hardcoded 450.

**Performance:** Scorecard computation in `logic.py` iterates over all sites. Growing from 25 to ~45 adds <100ms to a ~500ms endpoint. `fct_lcoe` grows from 450 to ~810 rows. Both negligible. The only potential bottleneck is GeoTIFF sampling for ~20 new site centroids during pipeline build, but that's offline and takes ~2s/site.

**Scope verdict:** 25+ files touched, but ~18 are mechanical renames (find-replace `kek` -> `site`). The 7 files with real logic changes are well-scoped. This passes the complexity check.

---

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| **Rename breaks 433 tests** | Do rename in one commit, run `pytest` immediately. The rename is mechanical. |
| **GeoTIFF sampling fails for new locations** | New sites are all in Indonesia; PVOUT/wind GeoTIFFs cover the entire country. Validate with known locations first. |
| **Grid region auto-assignment wrong** | Cross-check against BPP values. Eastern Indonesia sites should get high BPP, Java sites should get low BPP. |
| **Scope creep to 130+ sites** | Hard stop at Priority 1 (~20 sites). Priority 2-3 in future branches. |
| **Process emissions not modeled** | Cement calcination, aluminum electrolysis. Add caveat in methodology doc: "CBAM exposure covers Scope 2 (electricity). Process emissions (Scope 1) require sector-specific models not yet implemented." |

---

## TODOS.md Cross-Reference

These existing items in `TODOS.md` are directly affected by this expansion. Each should be updated when the expansion ships.

| # | Current Item | Impact | New Status |
|---|-------------|--------|-----------|
| **L16** | Industrial clustering benefit on LCOE | **Directly addressed.** Cluster site_type models aggregated demand. BESS sizing reflects cluster-level demand, not individual plants. | Move to "In Progress" or "Partially Done". Full LCOE benefit modeling (shared infrastructure discount) deferred. |
| **M17** | 30km "technically possible" grid integration layer | **Relevant for industrial sites.** New standalone plants outside KEK 5km/15km thresholds benefit from the 30km policymaker view. Expand to cover non-KEK sites. | Keep open, expand scope to non-KEK. |
| **L14** | Import JETP demand projections | **Partially addressed.** Sector-intensity demand estimation replaces area-proxy for non-KEK sites. JETP projections would further improve accuracy for overlapping KEK/industrial sites. | Keep open. Note: expansion adds sector-intensity alternative to area-proxy. |
| **L2** | SAIDI/SAIFI reliability indicators | **Partially addressed.** `SECTOR_RELIABILITY_REQUIREMENT` provides sector-based defaults for non-KEK sites. PLN SAIDI/SAIFI data would replace both area-type and sector-type proxies. | Keep open. Note: sector defaults now complement KEK type defaults. |
| **C1** | demand_mwh_2030 is area x intensity proxy | **Partially resolved for non-KEK sites.** Standalone plants use production-based demand (capacity_tpa x sector intensity), which is more accurate than area proxy. KEKs still use area proxy. | Update caveat tooltip to say "KEK demand estimated from area x intensity. Industrial sites use production-based calculation." |
| **C4** | reliability_req is type-based proxy | **Improved for non-KEK sites.** `SECTOR_RELIABILITY_REQUIREMENT` replaces generic type-based proxy with industry-specific values (steel=0.90, aluminum=0.95, etc.). KEKs still use type-based proxy. | Update caveat to reflect dual approach. |

### New TODOS Items to Add

| # | Item | Priority | Notes |
|---|------|----------|-------|
| NEW | **Process emissions (Scope 1) for CBAM** | L (v2.0) | Cement calcination, aluminum electrolysis. Current CBAM model covers Scope 2 (electricity) only. Requires sector-specific process models. |
| NEW | **PyPSA grid optimization integration** | L (v2.0) | Export dim_sites + fact tables as pypsa.Network for capacity expansion planning. Public data first, private data later. |
| NEW | **PLN Supergrid corridor visualization** | L (v2.0) | RUPTL Super Grid corridor data -> map overlay + `corridor_arrival_year` column per site. Requires RUPTL data parsing. |
| NEW | **Priority 2-3 industrial sites** | M (v1.3) | Petrochemical (Chandra Asri, TPPI), refining, non-KEK nickel expansion. SiteTypeConfig registry makes this a data-only addition. |
| NEW | **Col class for column name constants** | M (v1.3) | Replace string literals with `Col.SITE_ID` etc. Prevents rename bugs. Incremental adoption, one pipeline file at a time. |

---

## Verification Checklist

1. `uv run pytest tests/ -x` -- all tests pass after rename
2. `cd frontend && npx tsc --noEmit` -- frontend type-check clean
3. Pipeline produces `dim_sites.csv` with ~45 rows, `fct_site_scorecard.csv` with ~45 rows
4. Browser: map shows ~45 markers (circles for KEKs, different shape for industrial sites)
5. Browser: table shows sector column, filterable by dropdown
6. Browser: ScoreDrawer opens for a steel plant -> shows plant details, not KEK details
7. Browser: CBAM tab for Krakatau Steel shows steel-specific emission intensity
8. Spot-check: Krakatau Steel LCOE similar to nearby KEK Tanjung Lesung (same solar resource region)

---

## NOT in Scope (This Branch)

- Perpres 112/2022 compliance timelines (requires commissioning year data)
- Corridor arrival year from RUPTL Super Grid schedule
- Sectoral summary PDF export
- Site comparison view (side-by-side)
- Priority 2 sites (non-KEK nickel) and Priority 3 (petrochemical, refining)
- Process emissions modeling (Scope 1)
- KEK Planning Mode integration (separate feature branch)

---

## Appendix A: Methodology References

Our approach (site-level LCOE + grid integration + CBAM exposure + action flags) follows established patterns from international efforts. These validate our methodology and provide parameter calibration sources.

### Industrial Decarbonization Platforms

| Platform | Country/Org | What it does | What we borrow |
|----------|-------------|--------------|----------------|
| [IRENA Renewable Cost Database](https://www.irena.org/costs/Power-Generation-Costs) | Global (IRENA) | Tracks LCOE by technology, country, year. Published as "Renewable Power Generation Costs" annually. | CAPEX ranges, capacity factor benchmarks. Our CRF annuity formula matches IRENA's standard LCOE methodology. |
| [IEA Energy Technology Perspectives](https://www.iea.org/reports/energy-technology-perspectives-2023) | Global (IEA) | Models industrial decarbonization pathways for steel, cement, chemicals. Sector-specific electricity intensity, process emissions, technology roadmaps. | Sector electricity intensities (cement: 90-110 kWh/t, steel EAF: 400-600 kWh/t). IEA Cement Roadmap is our primary cement source. |
| [MPP Asset-Level Transition Tool](https://mfrb.org/) | Global (Mission Possible Partnership) | Asset-level tracker for hard-to-abate sectors (steel, cement, shipping, aviation). Maps every major plant globally with technology, capacity, emissions. | Asset-level data model. Their approach of tracking individual plants with technology type, capacity, and transition readiness directly inspired our `site_type = "standalone"` concept. |
| [Climate Action Tracker](https://climateactiontracker.org/) | Global (Climate Analytics / NewClimate) | Benchmarks industrial heat decarbonization by sector and country against Paris targets. | Emission intensity benchmarks for validation. |
| India Industrial Deep Decarbonization Initiative (IIDDI) | India (TERI / CII / RMI) | Site-level analysis of Indian steel and cement plants, mapping RE potential and grid constraints per industrial cluster. | Closest methodological precedent: site-level RE feasibility for heavy industry in a developing country. Their cluster-level analysis (e.g., Jamshedpur steel cluster) matches our Cilegon/Gresik cluster approach. |
| [EU Industrial Emissions Portal (E-PRTR)](https://www.eea.europa.eu/en/datahub/datahubitem-view/5fc498f5-0e8c-4407-a8b9-c87c1a1d3a7b) | Europe | Tracks emissions from 30,000+ industrial facilities. Site-level reporting of CO2, pollutants, energy use. | Data model for per-site emission tracking. Their site-level granularity is the standard we're building toward. |

### Electricity Intensity Sources (for `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE`)

| Sector | Source | Value Range | Our Default | Notes |
|--------|--------|-------------|-------------|-------|
| Steel (EAF) | [worldsteel Association](https://worldsteel.org/steel-topics/statistics/steel-statistical-yearbook/) 2023, [IRENA 2020](https://www.irena.org/publications/2020/Nov/Reaching-zero-with-renewables) | 0.35-0.60 MWh/t | 0.50 | Scrap-based EAF. Wide range depends on scrap quality and product mix. |
| Steel (BF-BOF) | [worldsteel Association](https://worldsteel.org/steel-topics/statistics/steel-statistical-yearbook/) 2023 | 0.15-0.30 MWh/t | 0.20 | Most energy is thermal (coke). Electricity is auxiliary (blowers, rolling). |
| Cement | [IEA Cement Roadmap 2018](https://www.iea.org/reports/technology-roadmap-low-carbon-transition-in-the-cement-industry), [GCCA](https://gccassociation.org/concretefuture/getting-the-numbers-right/) 2022 | 0.09-0.13 MWh/t | 0.11 | Grinding + kiln auxiliaries. Total energy is 3-4 GJ/t but mostly thermal. |
| Aluminium | [IAI](https://international-aluminium.org/statistics/primary-aluminium-smelting-energy-intensity/) 2023, [IRENA 2020](https://www.irena.org/publications/2020/Nov/Reaching-zero-with-renewables) | 13-17 MWh/t | 15.0 | Hall-Heroult electrolysis. Extremely electricity-intensive. |
| Fertilizer | [IFA](https://www.ifastat.org/) 2022, IRENA Green Hydrogen Report | 0.8-1.2 MWh/t | 1.0 | Ammonia synthesis. Most energy is natural gas feedstock, not electricity. |
| Nickel (RKEF) | JETP Captive Power Study Ch.2 | 30-45 MWh/t | 37.5 | RKEF is essentially an electric furnace. Highest electricity intensity after aluminum. |
| Nickel (HPAL) | BNEF 2024, JETP report | 6-10 MWh/t | 8.0 | Hydrometallurgical. Much lower electricity than RKEF but high chemical inputs. |

### Clustering Methodology References

| Approach | Used by | Method |
|----------|---------|--------|
| **Proximity-based grouping** | [EU E-PRTR](https://www.eea.europa.eu/en/datahub/datahubitem-view/5fc498f5-0e8c-4407-a8b9-c87c1a1d3a7b), India IIDDI | Group facilities within fixed radius (10-20km). Simple, transparent, reproducible. **This is our approach.** |
| **Administrative boundary** | China MEE emissions reporting | Group by industrial park boundary or district. Good when boundaries are official. We use this for KEKs (polygon boundary). |
| **DBSCAN spatial clustering** | Academic literature (e.g., Zheng et al. 2020) | Density-based spatial clustering. Better for discovering natural clusters from point clouds. Overkill for ~45 sites, but useful if we scale to 100+. |
| **Supply chain linkage** | [MPP Asset Tracker](https://mfrb.org/) | Group by shared infrastructure (port, power plant, water supply). Most accurate but requires data we don't have. |

Our hybrid approach: use `CLUSTER_PROXIMITY_THRESHOLD_KM` (15km, configurable) for automatic grouping, validate against the 5,159-point industrial shapefile, allow manual override in `priority1_sites.csv`. This matches the IIDDI/E-PRTR pattern and is appropriate for our scale (~45 sites).

---

## Eng Review Findings (2026-04-16)

### Decisions

| # | Issue | Decision | Rationale |
|---|-------|----------|-----------|
| R1 | `_haversine_km()` duplicated in 5 files (not 4), including `build_fct_substation_proximity.py:83` | **`geo_utils.py`** covers all 5 | One shared module for captive power builders AND substation proximity |
| R2 | `SECTOR_ELECTRICITY_INTENSITY` has cement=0.11 vs existing `CBAM_ELECTRICITY_INTENSITY` cement=0.9 (8x diff) | **Rename to `SECTOR_ELECTRICITY_ONLY_MWH_PER_TONNE`** + cross-reference docstring | "Electricity only" in name makes distinction unambiguous |
| R3 | Plan proposed backward compat `kek_id` alias | **Clean break. No alias.** | Zero external consumers. Alias adds complexity for no benefit |
| R4 | Legacy `src/dash/app.py` (1,763 lines, zero imports) | **Skip in rename** | Dead code. Don't touch it |
| R5 | `kek_type` column in unified `dim_sites` | **Rename to `zone_classification`** | Cleaner schema. KI sites may use their own classification values |
| R6 | Python/TS registry identity_fields can drift | **Runtime validation in `/api/scorecard`** (~10 lines) | Fails fast if registries are out of sync |

### Test Plan (~30 new tests)

```
tests/test_site_types.py (NEW, 5 tests)
  - test_all_site_types_present
  - test_site_type_config_immutable
  - test_invalid_site_type_raises
  - test_sector_enum_values
  - test_site_type_config_fields

tests/test_geo_utils.py (NEW, 8 tests)
  - test_haversine_zero_distance
  - test_haversine_known_distance (Jakarta-Surabaya ~660km)
  - test_proximity_match_finds_nearby
  - test_proximity_match_no_match
  - test_proximity_match_empty_sites
  - test_proximity_match_empty_plants
  - test_direct_match_by_id
  - test_direct_match_missing_id

tests/test_demand_intensity.py (NEW, 5 tests)
  - test_steel_eaf_demand (4M TPA x 0.50 = 2,000 GWh)
  - test_cement_demand (10M TPA x 0.11 = 1,100 GWh)
  - test_aluminium_demand (250K TPA x 15.0 = 3,750 GWh)
  - test_unknown_sector_raises
  - test_zero_capacity_returns_zero

tests/test_pipeline.py (MODIFIED, 6 tests)
  - test_build_dim_sites_preserves_keks
  - test_build_dim_sites_adds_industrial
  - test_build_dim_sites_no_duplicate_ids
  - test_grid_region_auto_assignment
  - test_cluster_centroid_is_largest_member
  - REGRESSION: parameterize len(df)==450 at line 429 -> len(dim_sites)*9*2

tests/test_dash_logic.py (MODIFIED, 3 tests)
  - test_cbam_direct_assignment_standalone
  - test_cbam_3signal_kek_preserved
  - test_cbam_non_kek_null_product

tests/test_captive_dual_mode.py (NEW, 4 tests)
  - test_captive_steel_proximity_kek
  - test_captive_steel_direct_standalone
  - test_captive_mixed_kek_and_standalone
  - test_captive_cement_direct_standalone

tests/test_api.py (MODIFIED, 2 tests)
  - test_scorecard_identity_fields_valid
  - test_site_endpoint_replaces_kek
```

### Failure Modes

| Scenario | What breaks | Detection | Mitigation |
|----------|------------|-----------|------------|
| Rename misses a `kek_id` string ref | Silent NaN join in pandas | `uv run pytest tests/ -x` after rename | StrEnums prevent future occurrences |
| New site centroid outside GeoTIFF | `pvout_daily` returns NaN | Pipeline logs warning | Guard: check lat/lon within Indonesia bounds |
| Standalone site within 15km of KEK | Captive power double-counted | Manual validation step 11 | proximity_match skips direct-mode sites |
| identity_fields references missing column | ScoreDrawer renders "undefined" | Runtime API validation (R6) | API returns 500 with clear error |
