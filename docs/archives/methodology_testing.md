# Solar Farm–SEZ Grid Infrastructure: Key Parameters & Logic

## 1. Distance Thresholds

### Solar Farm → Nearest Substation
- **Ideal:** ≤ 2 miles (~3.2 km) from an existing substation
- **Maximum viable:** ~5 miles (~8 km) before project economics become unattractive
- **Distribution lines** (lower voltage, < 69 kV): must be within ~0.2 miles (~320 m)
- **Cost driver:** Gen-tie (generation tie-line) construction costs ~$1–3M per mile

### New Transmission Line (if none exists between solar substation and SEZ substation)
- **Practical limit:** ~10–15 km before LCOE impact kills project viability
- **Cost:** $1–3M per mile depending on voltage level and terrain
- **This cost must be factored into LCOE**

### Substation-to-Substation (on existing grid)
- **Distance is largely irrelevant** if a transmission line already exists between them
- Losses on 150 kV lines are ~0.5–1% over 50–100 km — negligible
- What matters: **does a line exist**, and **does it have available capacity**

## 2. Transmission Loss Reference

| Voltage Level | Loss per 1,000 km | Typical Use |
|---|---|---|
| HVDC ±800 kV | ~3% | Long-distance bulk transfer (1,000+ km) |
| HVAC 500 kV | ~7% | National backbone |
| HVAC 150 kV | ~moderate | Regional transmission (Indonesia standard) |
| Distribution < 69 kV | ~4% over a few miles | Local distribution |

## 3. Capacity Estimation

### Substation Total Capacity (can be estimated)
- Infer from **voltage class** and **transformer count/size**:
  - 150/20 kV substation: typically 1–3 transformers × 30–60 MVA each → 30–180 MVA total
  - 500/150 kV substation: significantly larger
- Physical footprint from satellite imagery is a reasonable proxy for size
- PLN's RUPTL lists planned substations and upgrades by region

### Substation Utilization % (user input)
- **This is a customizable assumption, not a modeled output**
- Default: 60–70%
- Proxies for smarter defaults (future enhancement):
  - Population density / urbanization around substation
  - Night-time light intensity (satellite data)
  - Industrial load presence (cement, smelter, etc.)
  - SEZ occupancy rate (if known)
  - PLN RUPTL flagging upgrades → signal of near-capacity
- Available capacity = Total capacity × (1 − utilization %)

### Transmission Line Capacity (can be estimated)
- Determined by voltage, conductor type, and number of circuits
- 150 kV single-circuit: ~150–300 MW
- Visible from satellite or PLN grid maps
- RUPTL planned upgrades signal congestion

## 4. LCOE Impact Calculation

### Standard LCOE Formula
```
LCOE = Total Lifecycle Cost / Total Lifetime Energy Produced (MWh)
```

### Grid infrastructure costs to include in numerator:
- **Gen-tie construction** (distance to nearest substation × cost per mile)
- **Substation upgrade costs** (if existing substation lacks capacity)
- **New transmission line** (if no line exists between solar and SEZ substations)
- **Transformer/switchgear upgrades** (if line exists but substation needs stepping up)

### Example impact:
- Solar farm cost: $50M
- Gen-tie (10 km): ~$15M
- → LCOE increases ~30%

## 5. Decision Tree for Site Evaluation

```
1. Identify buildable solar areas
   (irradiance, land use, slope, environmental constraints)

2. For each area, find nearest PLN substation
   → Distance > 5 miles? → Flag as high-cost / likely unviable

3. Check: does a transmission line connect this substation to the SEZ substation?
   → YES → proceed to capacity check
   → NO  → estimate new line cost, add to LCOE

4. Estimate available capacity
   → Total substation capacity (from voltage class / transformer sizing)
   → Apply utilization % (user input, default 60-70%)
   → Available capacity = total × (1 - utilization%)

5. Is available capacity sufficient for proposed solar farm output?
   → YES → viable site
   → NO  → estimate upgrade cost (new transformer, substation expansion)
            → add to LCOE

6. Rank sites by adjusted LCOE
```

## 6. Traffic Light System (Capacity Assessment)

For display in the app when precise data is unavailable:

| Status | Criteria |
|---|---|
| 🟢 Green | Rural/low density, new or recently upgraded substation, voltage class suggests large capacity relative to apparent load |
| 🟡 Yellow | Suburban, mixed load, mid-aged infrastructure, uncertain utilization |
| 🔴 Red | Dense urban, heavy industrial users nearby, PLN RUPTL flags upgrades |

**Always include disclaimer:** Actual available capacity requires a formal PLN grid study.

## 7. Key Assumptions (All User-Configurable)

| Parameter | Default | Unit | Notes |
|---|---|---|---|
| Gen-tie cost | 2 | $M / mile | Varies by terrain and voltage |
| Substation utilization | 65 | % | User should override if known |
| PPA rate | — | $/MWh | PLN tariff, region-specific |
| Discount rate | 8–10 | % | For LCOE calculation |
| Project lifetime | 25 | years | Standard for solar |
| Degradation rate | 0.5 | % / year | Panel output decline |
| Max viable gen-tie distance | 15 | km | Beyond this, flag as high-cost |

## 8. Data Sources

- **PLN RUPTL** — planned substations, upgrades, new transmission lines by region
- **PLN grid maps** — existing substation locations and voltage classes
- **Satellite imagery** — substation footprint, line routing, circuit count
- **Night-time light data (VIIRS/DMSP)** — proxy for electricity consumption/utilization
- **OpenStreetMap / OSM power data** — crowdsourced power infrastructure mapping
- **Global Solar Atlas** — irradiance data for buildable area assessment
- **Indonesia SEZ registry** — KEK locations and development status