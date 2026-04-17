# Industrial Parks Expansion: From KEK Dashboard to Indonesia Industrial Decarbonization Platform

## 1. The So-What

Indonesia's industrial CO₂ emissions come overwhelmingly from cement, steel, aluminum, nickel, petrochemicals, and fertilizers. Of these, roughly 15-20% of output sits inside KEKs. The rest is in Kawasan Industri (industrial parks under Ministry of Industry designation) and standalone facilities.

A tool that analyzes 25 KEKs tells the story of where Indonesia **plans** to industrialize. A tool that covers all major industrial sites tells the story of where Indonesia **actually** industrializes and emits.

For a green industry decarbonization roadmap, the gap matters. The steel sector's emissions don't come from KEKs — they come from Krakatau Steel in Cilegon. Cement emissions don't come from KEKs — they come from plants spread across Java and Sulawesi. If the roadmap ignores these sites, it misses the majority of the problem.

**The expansion turns the dashboard from a KEK investment screening tool into Indonesia's first open-source industrial decarbonization planning platform.** Same methodology, same data layers, same action flags — applied to the sites that actually drive industrial CO₂.

## 2. Working Backwards: What Insights Matter for Decarbonization Planning?

The roadmap process needs to answer specific questions. The dashboard exists to answer them.

### 2.1 Sector-level insights (aggregate across all sites)

**Where is industrial carbon concentrated?**
- Total CO₂ from steel sites vs. cement vs. nickel vs. aluminum
- Geographic clustering: which provinces host the most emissions-intensive production?
- Captive coal capacity by sector: how much coal is locked into current industrial operations?

**Which sectors have the most CBAM exposure?**
- Steel and aluminum are already covered; cement and fertilizers added with the 2028 expansion
- Ranked list: which individual sites face the largest CBAM costs at 2030 and 2034?
- Aggregated: what is the total annual CBAM cost Indonesian industry faces at each phase-in year?

**Which sectors have the most Perpres 112/2022 exposure?**
- How much captive coal capacity must reduce emissions by 35% within 10 years?
- Which plants face cessation deadlines by 2050?
- How is that exposure distributed by sector and region?

### 2.2 Site-level insights (per facility or park)

**Can this site decarbonize economically?**
- Solar LCOE at this site vs. current power source (grid, captive coal, captive gas)
- Wind LCOE if the site has wind resource
- Hybrid solar + wind + BESS LCOE for 24/7 industrial loads
- CBAM-adjusted gap: does avoided CBAM cost close the renewable premium?

**What's stopping it from decarbonizing?**
- Action flag: grid_first, invest_transmission, invest_substation, solar_now, etc.
- Specific infrastructure gap: which substation needs upgrading, how many km of transmission needed, what's the cost
- Buildable land constraint: is there enough area within 50 km for the required renewable capacity?

**What's the transition pathway?**
- If the site has captive coal: Perpres deadline timeline
- If the site exports to EU: CBAM cost trajectory 2026-2034
- If the site is solar_now or solar_now_wacc8: ready for immediate procurement
- If invest_transmission: grid upgrade required before transition possible

### 2.3 Capital allocation insights (for investment planning)

**Where does each dollar of infrastructure investment unlock the most emissions reduction?**
- Impact ratio per grid corridor: (MW renewables unlocked + MW coal displaced) / $M transmission investment
- Impact ratio per substation upgrade: same metric at the single-site level
- Priority ranking: which 10 infrastructure investments deliver the most impact?

**Where does concessional finance catalyze the most transition?**
- Which sites flip from `not_competitive` to `solar_now` when WACC drops from 10% to 8%?
- Which sites remain uncompetitive even at 4% WACC? (These need structural solutions, not just cheaper capital.)
- Total MW of renewable deployment unlocked by concessional financing across the portfolio

**What's the total investment need for sector-wide transition?**
- Sum of renewable capacity × CAPEX across all sites in a sector
- Sum of grid infrastructure investment across all flagged sites
- Sum of BESS investment needed for 24/7 industrial loads
- Aggregated to produce a sector-wide financing requirement for the roadmap

### 2.4 Risk insights

**Stranded asset risk from captive coal**
- Captive coal plants with Perpres deadlines before Super Grid corridor arrival
- Plants with long remaining PPA terms that conflict with emission reduction mandates
- Aggregate value of coal assets at risk under different transition scenarios

**Competitiveness risk from CBAM**
- Sites exporting to EU with high emission intensity and no renewable transition plan
- Quantified: how much export value is at risk under full CBAM exposure by 2034?
- Relative competitiveness: Indonesian steel CBAM exposure vs. Turkish, Indian, Chinese competitors

**Grid reliability risk**
- Sites with high grid dependency (imports > 50% of demand) in regions with weak transmission
- Firm supply coverage: can renewable + BESS meet 24/7 demand or is grid import essential?
- Vulnerability mapping: which industrial clusters depend on fragile grid infrastructure?

**Land and community risk**
- Sites where buildable renewable capacity is insufficient for full transition
- Sites where solar buildable area conflicts with Kawasan Hutan, peatland, or agricultural land
- Concentration risk: sites where multiple industrial tenants compete for the same limited renewable supply

## 3. The Expansion: What to Add

### 3.1 Scope decision — don't boil the ocean

Indonesia has 130+ designated Kawasan Industri plus dozens of standalone facilities. Adding all of them in one pass is unnecessary and would dilute focus. Instead, prioritize by decarbonization relevance.

**Priority 1 — CBAM-exposed heavy industry (target: top 20 sites by emissions)**

Steel:
- Krakatau Steel (Cilegon) — largest integrated steel complex in Indonesia
- Gunung Steel (Cilegon)
- Dexin Steel (Morowali — already partly within IMIP KEK, but the steel-specific analysis is distinct)
- Sulawesi Mining Investment (Morowali)
- Master Steel, Jatake, and other major EAF operators

Cement:
- Major cement production clusters across Java and Sulawesi (Tuban, Gresik, Rembang, Citeureup, Cirebon, Narogong, Cilacap, Tonasa, Padang)
- The top 10-12 individual cement plants by capacity account for the majority of Indonesia's cement emissions

Aluminum:
- Inalum (Asahan, North Sumatra) — state-owned, major CBAM exposure
- Freeport aluminum smelter (Gresik, under construction)

Fertilizers:
- Pupuk Indonesia complex (Bontang, Palembang, Gresik)
- Pupuk Kaltim (Bontang)

**Priority 2 — Nickel sites not already captured as KEKs**

Several major nickel industrial parks operate outside or partially outside KEK status:
- Weda Bay Industrial Park (Halmahera)
- Obi Island nickel complex (Maluku)
- Konawe nickel sites (Southeast Sulawesi)

**Priority 3 — Petrochemical and refining clusters**

These are long-term CBAM expansion candidates and important for emissions but not immediate priorities:
- Chandra Asri (Cilegon)
- TPPI (Tuban)
- Pertamina refining complexes (Balikpapan, Cilacap, Dumai)

Start with Priority 1. That covers the bulk of CBAM exposure and most of Mari Pangestu's likely roadmap scope. Priority 2 and 3 extend the tool as needed.

### 3.2 Data model generalization

Current state: `kek_scorecard` table keyed on `kek_id`.

Target state: `industrial_site_scorecard` table keyed on `site_id` with a `site_type` column:

| site_type | Description | Example |
|-----------|-------------|---------|
| KEK | Special Economic Zone under Law 39/2009 | KEK Sei Mangkei, KEK Morowali |
| KI | Kawasan Industri under Law 3/2014 industrial estates framework | Kawasan Industri Jababeka, KI Cilegon |
| STANDALONE | Individual facility not in a designated zone | Krakatau Steel main complex, individual Semen Indonesia plants |
| CLUSTER | Multiple related facilities treated as one analytical unit | Bontang industrial cluster (Pupuk Kaltim + PT Badak LNG) |

All existing methodology — LCOE calculation, grid integration category, action flags, CBAM exposure, Perpres flag, GEAS allocation, BPP gap — operates on any site_type. The analytical machinery is already generic; only the data entry layer needs to accept new polygon types.

### 3.3 Additional metadata per site_type

Beyond the existing KEK fields, industrial parks and standalone facilities need:

**Regulatory framework**
- Regulatory authority: BKPM (KEK), Ministry of Industry (KI), or sector-specific (SOEs)
- Operator/owner: KEK administrator, KI operator company, or facility owner
- Legal status: operational, under construction, planned

**Production specifics (for standalone facilities)**
- Primary product (steel billets, clinker, aluminum ingots, ammonia, etc.)
- Annual production capacity (tonnes/year)
- Production technology (EAF vs BF-BOF for steel, dry vs wet process for cement)
- Year of commissioning (drives Perpres 112/2022 compliance timeline for captive coal)

**Anchor tenant information (for industrial parks)**
- Major tenants with named CBAM exposure
- Sector mix within the park
- Estimated share of park's emissions from the top 3 tenants

### 3.4 New calculated fields for industrial decarbonization

Beyond existing metrics, the expanded scope needs:

**Sectoral aggregation metrics**
- `sector_total_co2_tonnes_year` — aggregated across all sites in a sector
- `sector_cbam_cost_2030_usd` — aggregated CBAM exposure by sector
- `sector_renewable_transition_capex_usd` — total investment need to decarbonize the sector

**Site-level transition metrics**
- `captive_coal_mw_at_site` — specific captive coal capacity (from GEM GCPT integrated to site level)
- `captive_coal_commissioning_year` — drives Perpres compliance deadline
- `years_to_perpres_deadline` — computed from commissioning year
- `corridor_arrival_year` — from RUPTL 2025-2034 Super Grid schedule (once corridor feature built)
- `timeline_conflict_flag` — True if corridor arrives after Perpres deadline

**Decarbonization pathway**
- `pathway_flag` — one of: `ready_now`, `ready_with_grid_upgrade`, `ready_with_concessional_finance`, `ready_with_cbam_cost_stack`, `requires_structural_change`
- The pathway flag synthesizes existing metrics into a single decarbonization readiness classification

## 4. New Persona: Green Industry Roadmap Planner

This persona covers policy advisory teams, government planning units, sustainability consultancies, and research institutions building sector-by-sector decarbonization strategies for Indonesian heavy industry.

**Role:** Senior policy analyst or advisory partner working on Indonesia green industry transition strategy

**Context:** Building a sector-by-sector decarbonization roadmap for Indonesian heavy industry. Needs to quantify the problem (total emissions, CBAM exposure, stranded asset risk), identify the pathway (which sites decarbonize first, what infrastructure is needed), and size the investment (total capital needs by sector, concessional vs commercial breakdown).

**Primary question:** *For each CBAM-exposed sector, which sites should transition first, what does the transition cost, what infrastructure unlocks it, and where do the biggest risks concentrate?*

### What only this dashboard shows them

The only open-source tool that combines sector-level industrial emissions data with site-level renewable energy economics, grid infrastructure gaps, CBAM exposure, and Perpres 112/2022 compliance timelines. Existing tools cover one dimension each — GEM for coal assets, IRENA for LCOE, RUPTL for grid, CGSP for nickel. This combines them at the site level and aggregates up to sector level for roadmap planning. A planner can answer "what is the steel sector's total CBAM exposure, which specific sites drive it, what investment is needed to transition them, and what grid infrastructure unlocks the transition" in a single session rather than across multiple weeks of standalone analysis.

### Readiness target — 85%+

Key enablers:
- Site_type generalization complete, 20+ non-KEK industrial sites added
- Sectoral aggregation views in the UI
- Pathway flag synthesizing existing metrics
- Export formats sized for roadmap documents (sectoral summary tables, pathway charts)

### Key data needs

- `site_type`, `sector`, `primary_product`, `captive_coal_mw_at_site`, `cbam_cost_2030_usd`, `renewable_transition_capex_usd`, `pathway_flag`, `timeline_conflict_flag`, `grid_investment_needed_usd`
- Sector-level aggregations: total emissions, total CBAM exposure, total transition capex, total coal MW to displace

### User journey

1. **Land on sectoral overview** — a new view showing Indonesia's heavy industry by sector, with total emissions, total CBAM exposure, and number of sites per sector
2. **Drill into a sector (e.g., steel)** — see all steel sites (Krakatau, Dexin, Gunung, etc.) ranked by CBAM exposure or emissions
3. **Open ranked table filtered to sector** — review pathway flags: how many sites are ready_now vs requires_structural_change
4. **Identify bottlenecks** — sort by `grid_investment_needed_usd` to see which sites need the most infrastructure
5. **Quantify risk** — export the `timeline_conflict_flag` subset showing sites where Perpres deadlines arrive before grid infrastructure
6. **Drill into top 3 sites** — review individual site scorecards: LCOE, CBAM trajectory, renewable capacity available, grid gap specifics
7. **Export sectoral summary** — CSV and PDF formats sized for roadmap report integration
8. **Cite in roadmap document** — reference Zenodo DOI and GitHub release tag

### What they export

- Sectoral summary PDF: one-page per sector with total emissions, CBAM exposure, transition capex, priority site list, and pathway flag distribution
- Site ranking CSV: all sites in a sector ranked by chosen metric (CBAM cost, emissions, transition readiness)
- Timeline conflict table: sites facing Perpres deadlines before renewable infrastructure arrives
- Investment sizing table: total capex by sector for renewable + grid + storage

### What they'd cite

> "Source: Indonesia Industrial Decarbonization Dashboard v4.0 (Zenodo DOI: ...). Steel sector analysis covers X sites representing Y% of national production capacity. CBAM exposure calculated per EU Regulation 2023/956 phase-out schedule. Renewable LCOE uses ESDM Technology Catalogue 2023 with adjustable WACC. Grid infrastructure gap methodology per METHODOLOGY_CONSOLIDATED.md §7."

## 5. How Existing Personas Benefit from the Expansion

### Persona 1: Energy Economist (85% → 90%+)

Currently limited to 25 KEKs for country-level competitiveness analysis. With expansion:
- Analysis covers the sites that actually drive Indonesia's industrial energy demand, not just planned zones
- Sector-by-sector solar competitiveness — can answer "is solar economically viable for the cement sector as a whole?"
- National aggregation: what share of industrial electricity demand can be met by competitive renewables at 8% WACC?

New key data needs: `sector_renewable_fraction_competitive_wacc8`, `sector_total_demand_mwh`

### Persona 2: DFI Infrastructure Investor (85% → 92%+)

Currently screens grid investment opportunities across 25 KEKs. With expansion:
- Pipeline expands to include major industrial clusters (Cilegon, Gresik, Bontang)
- Higher-value targets because industrial parks have larger and more certain demand than planned KEKs
- Cross-sector prioritization: should DFI capital go to nickel KEK grid investment or cement cluster grid investment?

The existing action flags (`invest_transmission`, `invest_substation`) work identically on industrial parks. The ranked table just has more rows. For a DFI analyst, 45 sites in the pipeline is dramatically more useful than 25.

### Persona 3: Policy Maker (85% → 93%+)

Currently 25 KEKs for RUPTL acceleration and grid infrastructure prioritization. With expansion:
- Sector-specific policy insights (steel sector needs X, cement sector needs Y)
- Perpres 112/2022 compliance tracking across all major captive coal, not just KEK-based coal
- GEAS allocation prioritization across the full industrial base

For policymakers writing decarbonization regulation, the ability to see "what does this policy affect across the full industrial landscape, not just KEKs" is the difference between partial and complete analysis.

### Persona 4: IPP / Solar Developer (85% → 88%)

Modest improvement. Developers mostly care about bankable sites regardless of zone designation. Expansion adds:
- More potential offtake opportunities (especially near industrial parks with clear anchor tenants)
- Dedicated source (DS) pathway analysis for specific major tenants like Krakatau Steel
- Site comparisons that go beyond KEKs

### Persona 5: Industrial Investor / KEK Tenant (80% → 90%+)

The biggest gain. A tenant or investor comparing where to locate a new smelter or factory wants to see ALL options, not just KEKs. Expansion adds:
- Industrial park alternatives with comparable analysis
- Side-by-side comparison: a prospective steel investor can compare Cilegon (KI) vs KEK Sei Mangkei (KEK)
- CBAM exposure comparison by site, driving location decisions

### Persona 6 (NEW): Green Industry Roadmap Planner

Covered in Section 4. The primary beneficiary of the expansion.

## 6. Implementation Plan

### Phase 1: Data model generalization (1 week)

- Rename `kek_scorecard` to `industrial_site_scorecard` (keep alias for backward compatibility)
- Add `site_type`, `sector`, `primary_product` columns
- Populate existing 25 KEK rows with `site_type=KEK`
- Update all references in the UI and methodology doc
- Test that existing functionality is unchanged

Output: v3.7 release on Zenodo with generalized data model, same 25 sites.

### Phase 2: Add Priority 1 industrial parks and standalone sites (2-3 weeks)

Target 20-25 new sites covering steel, cement, aluminum, fertilizer, and any missing nickel.

Per site:
- Geocode polygon from GEM (steel, cement) and official sources
- Estimate demand from production capacity × electricity intensity by process
- Run the full existing methodology pipeline
- Validate results against any public benchmarks

Output: v3.8 release with ~50 sites total.

### Phase 3: Sectoral views and new persona support (2 weeks)

- Add sector filter to ranked table and overview map
- Build sectoral aggregation view
- Add `pathway_flag` calculated field
- Add sectoral summary PDF export
- Update PERSONAS.md with Persona 6 (Green Industry Roadmap Planner)

Output: v4.0 release, repositioned as "Indonesia Industrial Decarbonization Dashboard."

### Phase 4: Iteration based on user feedback (ongoing)

Feedback from institutional users (policy advisers, sectoral roadmap teams, DFI programming groups) will drive subsequent features. Likely candidates:
- Investment timeline tool (when to build what, given cost curves and CBAM phase-in)
- Scenario comparison (business as usual vs. accelerated transition vs. CBAM-forced)
- Specific sector deep-dives (steel roadmap mode, cement roadmap mode)

## 7. Risks of the Expansion

**Scope creep.** 130+ industrial parks exist. The temptation to cover all of them is real. Discipline is: stop at Priority 1 plus whatever Mari's team specifically needs. Adding marginal sites dilutes quality and delays delivery of high-impact features.

**Data quality variance.** Industrial park data quality varies. Some KIs have well-documented polygons and operator information; others are barely documented publicly. Sites with poor data quality should be flagged in the tool so users know where to apply more caution.

**Sector-specific methodology gaps.** Cement has embedded process emissions (calcination of limestone) that don't go away with renewable electricity — you need carbon capture or alternative chemistry. The current methodology doesn't distinguish between electrification-addressable emissions and process emissions. For cement specifically, this becomes a critical caveat. Methodology needs a process-vs-energy emissions split for cement and potentially aluminum and steel.

**Positioning risk.** The tool's reputation as "KEK dashboard" is building. Changing the scope and name mid-growth could dilute that reputation rather than strengthen it. Mitigation: keep the KEK-focused view as a first-class filter, and phase the expansion so early users aren't confused.

## 8. What This Enables That Nothing Else Does

No open-source tool currently combines these data layers at site level across Indonesia's full industrial base:

- Site polygon and demand estimate
- Solar, wind, and hybrid LCOE at site-specific resource quality
- Grid infrastructure gap (substation, transmission, capacity) per site
- Captive coal presence and Perpres 112/2022 compliance timeline
- CBAM exposure trajectory 2026-2034 per site
- Pathway flag synthesizing all of the above into a readiness classification
- Sectoral aggregation for national roadmap planning

Commercial tools like Wood Mackenzie's Power & Renewables dataset or BloombergNEF's analytics platforms cost $50K-200K/year per seat and don't have Indonesian industrial site granularity. Government datasets (ESDM, BKPM, Ministry of Industry) are fragmented and rarely integrated. Academic work on Indonesian energy transition is mostly sector-wide or national, not site-level.

The expansion to industrial parks is what makes the tool genuinely useful for the roadmap work that policy advisers, government planning units, and DFIs need to do. Without it, the tool stays a niche KEK-focused resource. With it, the tool becomes the open-source analytical foundation for Indonesia's industrial decarbonization decade.
