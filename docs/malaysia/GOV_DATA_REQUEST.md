# Malaysia Renewable Energy Siting Tool — Data Request

**Purpose:** This is a standalone, handable document. It lists the datasets that would materially
improve a renewable-energy siting and feasibility model for Malaysia, what each one unlocks, and
what we will do without it. It is ordered by impact, so a partial response is still useful.

**Background:** The tool is an existing, published analytical model (DOI
[10.5281/zenodo.19570542](https://doi.org/10.5281/zenodo.19570542)) currently covering 81 industrial
sites across Indonesia. It computes solar and wind LCOE, buildable land area, storage requirements,
grid integration cost, and carbon-border exposure under user-adjustable assumptions. We are porting
it to Malaysia. **Everything in the tool today is built from public data** — this request is about
raising precision, not about filling gaps that would otherwise block the work.

**On confidentiality:** we can hold any dataset in a private, non-published data layer, separated
from the open-source repository, and can work to whatever aggregation, redaction, or embargo terms
are required. We can also accept data at reduced granularity (e.g. banded rather than exact values)
where exact figures are sensitive.

---

## Tier 1 — Highest impact

### 1. Grid connection headroom by intake substation (PMU)

**Ask:** For each Main Intake Substation (PMU) / transmission connection point: location, voltage
level, installed capacity (MVA), and **currently available capacity for new generation connection**.

**Ideal:** exact MVA available. **Acceptable:** banded (e.g. >100 MVA / 50–100 / 10–50 / <10 /
none). **Also useful:** the year the figure is current as of.

**Why it matters:** This is the single most valuable dataset in this request. Malaysia's national
transmission and distribution utilisation is around 30%, but demand is heavily concentrated around
industrial and data-centre clusters — so the binding constraint on new renewable projects is not
solar resource or land, it is whether a given connection point can physically accept the power.
Public sources (TNB Nodal Points via SEDA) give us connection point *locations* and voltage, but not
available capacity.

**Without it:** we substitute a modelled proxy — installed capacity × an assumed availability
fraction — which is what we currently do for Indonesia. It is defensible for national screening but
cannot support a real siting decision, and any developer will identify it as the weak point.

### 2. Grid connection application queue

**Ask:** By connection point, the aggregate capacity (MW) of generation connection applications
already lodged, in study, or approved but not yet energised. Aggregate counts are sufficient —
we do not need applicant identities.

**Why it matters:** Headroom that appears free may already be committed. Without the queue, any
capacity figure we publish risks overstating what is genuinely available, which would make the tool
misleading precisely where it is most useful.

**Without it:** we must caveat all capacity figures as gross rather than net. This is a significant
credibility limitation and we would prefer to state a real number.

---

## Tier 2 — High impact

### 3. Transmission and distribution development plan, at connection-point granularity

**Ask:** Planned new and upgraded PMUs / transmission lines: location, capacity (MVA), and target
energisation year. Roughly the granularity of Indonesia's published RUPTL.

**Why it matters:** It converts a static map into a forward-looking one — it lets a developer see
that a currently constrained node opens up in, say, 2028, and time a project accordingly. In the
Indonesia version this is one of the most-used features.

**Without it:** we use publicly announced aggregate figures at state level, which is too coarse to
site a project against.

### 4. Land and forest status by state

**Ask:** Geospatial boundaries (shapefile / GeoJSON) for:
- Permanent Reserved Forest (Hutan Simpan Kekal) and other protected forest classifications
- State land vs alienated land
- Land currently designated or zoned for industrial use
- Where available, land categories that restrict transfer or development

**Why it matters:** This drives the buildability filter, which determines how many MW can physically
be built at a site. Land and forestry are state matters, so there is no single national source — a
pointer to the right authority per state would itself be valuable, even without the data.

**Without it:** we approximate using global datasets (WDPA protected areas, ESA WorldCover forest
classification). This catches the large protected blocks but misses national and state-level legal
designations, and tells us nothing about tenure — so we can say a site is *physically* buildable but
not whether it is *legally* available.

### 5. Industrial park and special zone boundaries

**Ask:** Fence-line boundary polygons for industrial parks, technology parks, free zones, and
Johor–Singapore SEZ flagship zones — with, where available, developer, total area, and occupancy.

**Why it matters:** Site area drives every capacity estimate in the model.

**Without it:** the tool falls back to a radius buffer around the site centroid and marks the result
with a low-confidence indicator. This already works — it is how we handle Indonesian sites lacking
official boundaries — but boundaries typically change estimated buildable area substantially.

---

## Tier 3 — Useful, lower priority

### 6. Renewable procurement scheme outcomes

**Ask:** For LSS rounds and CRESS: awarded capacity by location, and — if not commercially
sensitive — clearing or awarded price ranges. Aggregate or banded figures are fine.

**Why it matters:** Lets us calibrate cost assumptions against what projects actually clear at in
Malaysia, rather than against regional benchmarks. It also shows which areas are already saturated
with awarded capacity.

**Without it:** we use published ceiling prices and regional cost benchmarks, and state clearly that
they are benchmarks rather than observed Malaysian outcomes.

### 7. Water availability for industrial and data-centre use

**Ask:** Water allocation, availability, or stress indicators by district — particularly for
districts hosting or targeted for data-centre development.

**Why it matters:** For data-centre siting, water is a genuine constraint alongside power, and it is
currently absent from the model.

**Without it:** water is flagged qualitatively rather than quantitatively.

### 8. Industrial facility inventory

**Ask:** Location and, where available, sector and production capacity for large industrial energy
users — aluminium, steel, cement, oleochemicals, semiconductors and electronics, and data centres.

**Why it matters:** Drives the demand-side estimate and the EU Carbon Border Adjustment Mechanism
(CBAM) exposure analysis, which is directly relevant to Malaysian exporters of aluminium and steel.

**Without it:** we use global facility trackers, which cover the largest plants well but are
incomplete below that threshold.

---

## What we would provide in return

- Full methodology transparency: every formula, assumption, and data source is documented and
  published (the Indonesia version ships a complete data dictionary and methodology document).
- The Malaysia analysis outputs, at whatever granularity is useful — national screening results,
  per-site scorecards, or the underlying tables.
- Attribution of data sources on request, or confidential handling where preferred.
- The tool itself is open source under an MIT-based licence.

## Contact

Shaan Barca — shaan.b1223@gmail.com
