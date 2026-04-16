# Analysis: Are We Being Prescriptive About Battery Storage?

## The Problem

The dashboard currently frames the energy story as: "Can renewables power this KEK 24/7?" That framing leads to the `invest_battery` action flag, which says "add 14h of BESS to cover nighttime." But 14h BESS at $250/kWh adds **~$100-250/MWh** to the solar LCOE. That makes the all-in cost way higher than grid for almost every KEK.

The question: are we telling a KEK tenant to build something that doesn't make economic sense?

---

## What the Current System Does

### Action Flag: `invest_battery`

**Triggers when:** Solar LCOE < grid cost (solar is "attractive") AND reliability_req >= 0.75

**What it says to the user:** "Solar economics work, but reliability needs require battery storage (Xh). Solar + battery: $Y/MWh."

**The issue:** "Solar economics work" is true for **daytime only**. The moment you add 14h BESS for nighttime, the all-in cost often exceeds grid cost. The flag is technically correct (you need storage for 24/7), but it's misleading because it implies this is a sensible investment.

### The Math

For a typical KEK with good solar (PVOUT ~1600, CF ~0.18):
- Solar LCOE: ~$55-70/MWh (competitive with grid BPP of $60-80/MWh)
- BESS adder at 14h bridge: ~$100-250/MWh (depending on WACC)
- Solar + BESS all-in: ~$155-320/MWh (way above grid)

For 2h cloud-firming only:
- BESS adder: ~$25-40/MWh
- Solar + BESS all-in: ~$80-110/MWh (sometimes competitive)

The 14h overnight bridge is what kills the economics. Almost no KEK can justify it at current battery prices.

### What Actually Happens in Practice

A nickel smelter at Maloy Batuta isn't going to build 14h of BESS. They'll:
1. Install solar panels and run them during the day
2. Stay on the grid at night (or use captive coal)
3. Maybe add 2-4h of BESS for cloud cover and peak shaving
4. Wait for battery costs to drop before going fully off-grid

The dashboard should reflect this reality, not the theoretical 100%-renewable ideal.

---

## Current Framing vs. Proposed Reframing

### Current (prescriptive, assumes 100% RE goal)

| Flag | Message |
|------|---------|
| `solar_now` | "Deploy solar now" (implying 24/7) |
| `invest_battery` | "Add battery storage" (14h, very expensive) |
| `invest_resilience` | "Within 20% of parity, invest for resilience" |
| `not_competitive` | "Solar can't beat grid" |

### Proposed (descriptive, shows economic reality)

| Concept | Meaning | When |
|---------|---------|------|
| **Full Solar** | Solar + storage beats grid even with BESS costs. Go 100% renewable. | Solar+BESS all-in < grid cost |
| **Partial Solar** | Solar is cheaper than grid for daytime. Use grid (or future storage) at night. This is still a win... you're cutting 42% of your energy bill. | Solar LCOE < grid cost, but Solar+BESS > grid cost |
| **Solar + Wind (Hybrid)** | Wind covers nighttime, reducing or eliminating BESS need. Best economics when both resources exist. | Hybrid all-in < solar+BESS all-in |
| **Grid First** | Solar isn't competitive yet. Grid is the right choice. | Solar LCOE > grid cost |

### What Changes for the User

**An IPP developer** reads "Add Battery Storage" and thinks: "Is that the recommendation? At $250/kWh for 14h? That doesn't pencil." They lose trust in the dashboard.

**With the new framing**, they'd read "Partial Solar, daytime solar saves X% vs grid" and think: "OK, solar for daytime makes sense, I'll size the plant for daytime demand and keep the grid for nighttime. That's a real project."

---

## The Deeper Question: What Does the Energy Balance Chart Show?

The energy balance chart currently shows:
- **Demand bar:** 42% daytime / 58% nighttime
- **Supply bar:** Solar (42%) + Storage/Grid (58%) + Gap

With the new framing, the chart would tell a clearer story:

**For "Partial Solar" KEKs:**
> "Solar covers your daytime demand (42%) at $X/MWh, saving Y% vs grid. Nighttime (58%) stays on grid at $Z/MWh. Overall energy cost drops W%."

**For "Full Solar" KEKs:**
> "Solar + storage covers 100% of demand at $X/MWh all-in, beating grid cost of $Z/MWh."

**For "Hybrid" KEKs:**
> "Solar covers daytime (42%), wind covers nighttime (58%). No storage needed. All-in $X/MWh."

The chart becomes part of the economic story, not a separate display.

---

## Implications for Action Flags

### Option A: Rename existing flags (minimal change)
- `invest_battery` becomes `partial_solar` when BESS makes all-in uncompetitive
- `invest_battery` stays only when solar+BESS all-in < grid cost
- Add new flag: `full_solar` (solar + BESS beats grid)
- Change: backend flag selection logic in `logic.py:676-698`

### Option B: Add economic tiers to solar_now (moderate change)
- `solar_now` gets a qualifier: "Solar Now (daytime)" vs "Solar Now (24/7)"
- Keep `invest_battery` for the case where BESS actually pencils out
- Add text to explain: "Daytime solar covers 42% of demand. For 24/7 coverage, battery storage adds $X/MWh."
- Change: flag explanation text, energy balance summary

### Option C: Rethink the flag ladder entirely (big change)

See full deep-dive below.

---

## Option C Deep Dive: Two-Dimensional Flag System

### The Core Insight

The current system is a **1D priority ladder**. One flag wins, the rest are hidden. A KEK that is `solar_now` AND `invest_battery` only shows `solar_now`. A KEK that is `invest_transmission` AND `plan_late` only shows `invest_transmission`.

But each persona asks a DIFFERENT question:
- **Energy Economist**: "How competitive is RE vs grid?" (economic dimension)
- **DFI Investor**: "What infrastructure investment unlocks RE?" (infrastructure dimension)
- **Policy Maker**: Both dimensions + RUPTL timing + CBAM
- **IPP Developer**: "Can I build a project here today?" (economics + infrastructure)
- **Industrial Investor**: "What's my energy cost risk over 15 years?" (economics + CBAM + timeline)

A single flag can't answer all five questions. The fix: **split the flag into two independent dimensions + modifier badges**.

---

### Dimension 1: Economic Tier (answers "how much RE makes economic sense?")

| Tier | Condition (Solar Mode) | Meaning | Color |
|------|----------------------|---------|-------|
| **Full RE** | Solar+BESS all-in <= grid cost | 24/7 renewable is cheaper than grid, even with 14h storage. Deploy now. | Dark green |
| **Partial RE** | Solar LCOE <= grid cost, but Solar+BESS > grid | Daytime solar (42%) beats grid. Nighttime stays on grid. Still a 42% energy cost reduction. | Light green |
| **Near Parity** | Solar LCOE within 20% of grid cost | Solar is close. Resilience value, CBAM avoidance, or concessional finance could tip it. | Orange |
| **Not Competitive** | Solar LCOE > 120% of grid cost | Grid is the right choice at current prices. | Red |
| **No Resource** | Buildable area = 0 or PVOUT < threshold | No suitable RE land within 50km. | Gray |

**How it varies by energy mode:**

| Mode | "RE LCOE" (daytime) | "All-in 24/7" | Notes |
|------|---------------------|---------------|-------|
| **Solar** | `lcoe_solar` | `lcoe_solar + bess_adder(14h)` | 14h bridge is the honest 24/7 cost |
| **Wind** | `lcoe_wind` | `lcoe_wind + firming_adder` | Wind generates at night, so firming is 2-4h, not 14h |
| **Hybrid** | `hybrid_lcoe_usd_mwh` (blended) | `hybrid_allin_usd_mwh` (includes reduced BESS) | Wind nighttime coverage reduces BESS from 14h to X hours |

**Why this matters for each persona:**

- **Energy Economist** reads "Partial RE" and knows: LCOE < grid for daytime, BESS kills 24/7. They model what WACC or BESS cost drop would push it to Full RE.
- **IPP Developer** reads "Partial RE" and thinks: I can build a daytime solar project, sell to grid during day, the KEK buys grid at night. Real project, real returns.
- **Industrial Investor** reads "Partial RE" and thinks: my daytime energy costs drop 42%, nighttime stays the same. Net savings of ~15-20% on total energy bill. That's real money.
- **Policy Maker** reads "Partial RE" and knows: solar works here, but 24/7 decarbonization needs storage policy (BESS supply chain, grid codes for storage, incentives).

---

### Dimension 2: Infrastructure Readiness (answers "what do you need to build?")

This stays **exactly** as the current `grid_integration_category` from methodology section 8.2. It's already well-designed:

| Category | Condition | Meaning |
|----------|-----------|---------|
| **Within Boundary** | Substation inside KEK or on-site solar covers 100%+ of demand | Deploy behind-the-meter. No grid export needed. |
| **Grid Ready** | Solar < 5km from substation AND KEK < 15km from substation | Minor connection costs. Can proceed. |
| **Invest Transmission** | Solar near substation, KEK far | Build transmission line to KEK. DFI opportunity. |
| **Invest Substation** | KEK near substation, solar far | Build substation near solar site. DFI opportunity. |
| **Grid First** | Both distances exceed thresholds | Major grid infrastructure needed. Long-term play. |

No changes needed. This dimension is solid.

---

### Modifier Badges (additional context, not primary classification)

| Badge | Condition | What it tells the user |
|-------|-----------|----------------------|
| **CBAM Urgent** | KEK is CBAM-exposed AND cbam_adjusted_gap < 0 | "EU border tax savings flip the economics. Even if `near_parity` on pure LCOE, RE is cheaper when you factor in avoided CBAM costs." |
| **Plan Late** | post2030_share >= 60% | "RUPTL pipeline is delayed. Grid upgrades won't arrive on schedule. This increases the value of captive RE." |
| **Storage Info** | Always shown when economic tier is computed | Informational, not prescriptive: "14h storage adds $X/MWh. At 4h (cloud-firming only): $Y/MWh." Not a recommendation to build storage, a data point. |

**What changes:** `invest_battery` stops being a prescriptive flag ("Add Battery Storage") and becomes an informational badge ("Storage costs $X/MWh for Y hours"). The economic tier already tells you whether storage pencils out (Full RE) or not (Partial RE).

`invest_resilience` is absorbed into `near_parity`. The resilience argument IS the near-parity argument: "Solar is within 20% of grid cost. Manufacturing outage costs ($50-200/MWh) exceed the LCOE premium ($12/MWh). Invest for resilience."

---

### How Each KEK Would Display (Examples)

**Maloy Batuta (nickel smelting, Kalimantan):**
- Current: `solar_now` (hides that 24/7 needs $290/MWh storage)
- New: **Partial RE + Within Boundary** | Badge: CBAM Urgent
- Story: "Solar covers daytime demand (42%) at $62/MWh vs grid $78/MWh. Nighttime stays on grid. Storage for 24/7 would add $290/MWh, not economic. But: CBAM avoidance saves $15/MWh, improving the case for partial RE. In hybrid mode, wind covers nighttime, reducing storage to 0h."

**Kendal (manufacturing, Java):**
- Current: `invest_resilience` (gap = 13%, reliability = 0.8)
- New: **Near Parity + Grid Ready** | Badge: Plan Late
- Story: "Solar LCOE is 13% above grid. But manufacturing outage costs ($50-200/MWh) exceed the $8/MWh premium. RUPTL pipeline delayed (plan_late). Captive solar builds resilience."

**Galang Batang (nickel, Sulawesi):**
- Current: `solar_now`
- New: **Partial RE + Within Boundary** | Badge: CBAM Urgent
- Story: "Strong solar resource. Daytime solar at $58/MWh beats grid ($85/MWh BPP). On-site deployment (within boundary). In hybrid mode: wind covers nighttime, all-in $72/MWh beats grid."

**Sei Mangkei (petrochemical, Sumatra):**
- Current: `not_competitive`
- New: **Not Competitive + Invest Substation**
- Story: "Solar LCOE ($95/MWh) exceeds grid ($68/MWh). Solar site is far from nearest substation. Neither economics nor infrastructure support RE at current prices."

---

### Backend Logic Changes

#### New function: `economic_tier()`

```python
def economic_tier(
    lcoe_re: float,              # bare RE LCOE (solar/wind/hybrid blended)
    allin_24_7: float,           # all-in including storage for 24/7
    grid_cost: float,            # BPP or tariff
    gap_threshold_pct: float = 20.0,  # near-parity threshold
    pvout_ok: bool = True,       # resource passes threshold
    buildable_area_ok: bool = True,
) -> str:
    if not buildable_area_ok or not pvout_ok:
        return "no_resource"
    if allin_24_7 <= grid_cost:
        return "full_re"
    if lcoe_re <= grid_cost:
        return "partial_re"
    gap_pct = (lcoe_re - grid_cost) / grid_cost * 100
    if gap_pct <= gap_threshold_pct:
        return "near_parity"
    return "not_competitive"
```

#### Changes to `logic.py`

Instead of the current priority loop (lines 676-698), the scorecard row would carry three fields:

```python
row["economic_tier"] = economic_tier(
    lcoe_re=lcoe_mid,
    allin_24_7=lcoe_mid + bess_adder,  # solar mode
    grid_cost=grid_cost,
    pvout_ok=pvout_best_50km >= thresholds.pvout_threshold,
    buildable_area_ok=max_mwp > 0,
)
row["infra_readiness"] = grid_integration_cat  # already computed
row["badges"] = []  # list of modifier badges
if plan_late:
    row["badges"].append("plan_late")
if cbam_urgent:
    row["badges"].append("cbam_urgent")
```

The existing `action_flag` field stays for backwards compatibility, derived from the two dimensions:

```python
# Derive legacy action_flag from 2D system
if row["economic_tier"] == "full_re":
    if infra == "within_boundary" or infra == "grid_ready":
        row["action_flag"] = "solar_now"  # or "full_re_now"
    elif infra == "invest_transmission":
        row["action_flag"] = "invest_transmission"
    elif infra == "invest_substation":
        row["action_flag"] = "invest_substation"
    else:
        row["action_flag"] = "grid_first"
elif row["economic_tier"] == "partial_re":
    if infra in ("within_boundary", "grid_ready"):
        row["action_flag"] = "partial_re_now"  # NEW
    elif infra == "invest_transmission":
        row["action_flag"] = "invest_transmission"
    # ... etc
elif row["economic_tier"] == "near_parity":
    row["action_flag"] = "invest_resilience"
else:
    row["action_flag"] = "not_competitive"
```

#### What stays the same in the backend

- `is_solar_attractive()` — still the gating check (PVOUT + LCOE vs grid)
- `grid_integration_category()` — infrastructure dimension, unchanged
- `solar_competitive_gap()` — feeds into `economic_tier()`
- `bess_storage_adder()` — feeds into `allin_24_7` for economic tier
- `hybrid_lcoe_optimized()` — feeds into hybrid mode economic tier
- `firm_solar_metrics()` — supports the energy balance chart narrative
- All LCOE computation — untouched

---

### Frontend Changes

#### ScoreDrawer Header

Current: single flag badge (e.g., green "Solar Now")

New: two badges stacked or side by side:
- **Economic tier badge**: "Partial RE" (light green) or "Full RE" (dark green) or "Near Parity" (orange) etc.
- **Infrastructure badge**: "Within Boundary" (gray) or "Invest Transmission" (blue) etc.
- **Modifier badges** (small, inline): "CBAM" (orange), "Plan Late" (purple)

#### Action Tab (Flag Ladder)

Current: single 10-step ladder with one highlighted position.

New: two shorter ladders side by side:

**Economic Ladder** (left):
1. Full RE (dark green)
2. Partial RE (light green)
3. Near Parity (orange)
4. Not Competitive (red)
5. No Resource (gray)

**Infrastructure Ladder** (right):
1. Within Boundary (green)
2. Grid Ready (light blue)
3. Invest Transmission (blue)
4. Invest Substation (teal)
5. Grid First (dark blue)

Each KEK lights up its position on BOTH ladders. The explanation text combines both: "This KEK is **Partial RE** (daytime solar at $62/MWh beats grid at $78/MWh) with **Within Boundary** infrastructure (on-site solar covers 150% of demand)."

#### Energy Balance Chart Summary

The summary text becomes tier-aware:

| Tier | Summary Template |
|------|-----------------|
| **Full RE** | "Solar + storage covers 100% of demand at $X/MWh all-in, beating grid ($Y/MWh). Deploy 24/7 RE." |
| **Partial RE** | "Solar covers daytime (42%) at $X/MWh, saving Z% vs grid. Nighttime (58%) stays on grid at $Y/MWh. 14h storage would add $W/MWh, not yet economic." |
| **Near Parity** | "Solar ($X/MWh) is within Z% of grid ($Y/MWh). Manufacturing resilience value ($50-200/MWh outage cost) may justify the premium." |
| **Not Competitive** | "Grid ($Y/MWh) is cheaper than solar ($X/MWh). Gap: Z%." |

#### Constants / Colors / Labels

```typescript
// Economic tier
const ECONOMIC_TIER_COLORS = {
  full_re: '#2E7D32',        // dark green
  partial_re: '#66BB6A',     // light green
  near_parity: '#F57C00',    // orange
  not_competitive: '#C62828', // red
  no_resource: '#78909C',    // gray
};

const ECONOMIC_TIER_LABELS = {
  full_re: 'Full RE',
  partial_re: 'Partial RE',
  near_parity: 'Near Parity',
  not_competitive: 'Not Competitive',
  no_resource: 'No Resource',
};

// Infrastructure stays as current grid_integration_category colors
```

---

### What This Means for Each Persona

**Energy Economist:** Sees economic tier directly. Can model: "At what WACC / BESS price does Partial RE become Full RE?" The tier makes the LCOE vs LCOE+BESS distinction explicit instead of hiding it behind `solar_now`.

**DFI Investor:** Filters by infrastructure dimension. "Show me all Invest Transmission KEKs that are Partial RE or better." Ranks by solar ROI per infrastructure dollar. The economic tier tells them whether the investment unlocks viable projects.

**Policy Maker:** Reads both dimensions: "12 KEKs are Partial RE + Within Boundary. These are immediate wins for daytime solar policy. 3 KEKs are Near Parity + Invest Transmission. These need both grid investment and small policy nudge (concessional finance or carbon pricing)."

**IPP Developer:** Sees "Partial RE + Grid Ready" and knows: "I can build a daytime solar PPA here. The KEK buys solar during the day at below-grid cost, stays on PLN at night. That's a bankable project." No confusion about whether they need to finance $290/MWh of storage.

**Industrial Investor:** Sees "Partial RE" and understands: "My daytime energy costs drop. Nighttime stays the same. Net savings ~15-20%. If I'm CBAM-exposed (badge), the savings are larger." No misleading "Add Battery Storage" recommendation that doesn't pencil out.

---

### Migration Path (Current → New)

| Current Flag | Maps to (New System) |
|-------------|---------------------|
| `solar_now` | Full RE + (Within Boundary or Grid Ready), OR Partial RE + (Within Boundary or Grid Ready) |
| `invest_battery` | Absorbed into economic tier. Partial RE = daytime only. Full RE = storage pencils out. Storage cost becomes informational badge, not prescriptive flag. |
| `invest_resilience` | Near Parity tier. Resilience rationale is the explanation for this tier. |
| `invest_transmission` | Any economic tier + Invest Transmission infrastructure |
| `invest_substation` | Any economic tier + Invest Substation infrastructure |
| `grid_first` | Any economic tier + Grid First infrastructure |
| `plan_late` | Badge modifier on any combination |
| `cbam_urgent` | Badge modifier. Can upgrade effective tier (Near Parity → effectively Partial RE when CBAM savings are included). |
| `not_competitive` | Not Competitive tier |
| `no_solar_resource` | No Resource tier |

---

### Scope of Changes

| Component | Change Size | What Changes |
|-----------|------------|--------------|
| `src/model/basic_model.py` | Small | Add `economic_tier()` function (~20 lines). Keep all existing functions. |
| `src/dash/logic.py` | Medium | Add economic_tier + badges computation. Keep legacy `action_flag` derivation for backwards compat. |
| `frontend/src/lib/types.ts` | Small | Add `EconomicTier` type, `badges` field to ScorecardRow. |
| `frontend/src/lib/actionFlags.ts` | Medium | Add tier hierarchy, tier explanations. Keep legacy flag support. |
| `frontend/src/lib/constants.ts` | Small | Add tier colors/labels alongside existing flag colors. |
| `frontend/src/components/panels/ScoreDrawer.tsx` | Medium | Dual-badge header, two-ladder Action tab. |
| `frontend/src/components/charts/EnergyBalanceChart.tsx` | Small | Tier-aware summary text. |
| `frontend/src/components/table/` | Small | Add economic_tier column, keep action_flag column. |
| `docs/METHODOLOGY_CONSOLIDATED.md` | Medium | Update section 10 with 2D system. |
| `PERSONAS.md` | Small | Update flag interpretation tables. |
| Tests | Medium | New tests for `economic_tier()`, update existing flag tests. |

---

### Open Questions

1. **Should `solar_now` still exist as a label?** In the new system, it would be "Full RE + Grid Ready" or "Partial RE + Grid Ready". Is "Solar Now" a better label for IPP audiences than "Partial RE"?

2. **CBAM as tier override vs badge?** Currently `cbam_urgent` can override `not_competitive`. In the new system, should CBAM savings adjust the economic tier directly (e.g., Near Parity → Partial RE when cbam_adjusted_gap < 0), or stay as a badge?

3. **Hybrid mode tier:** When hybrid_allin < grid, is that "Full RE" even though it uses wind (not storage) for nighttime? Technically yes, the 24/7 cost beats grid. The technology mix is in the energy balance chart, the economic tier just says "it works."

4. **Table view:** The ranked table currently shows one action flag column. Add a second column for infrastructure? Or a combined "Partial RE / Grid Ready" string?

5. **GEAS threshold for `solar_now`:** Currently `solar_now` requires GEAS green share >= 30%. In the new system, does this gate Full RE / Partial RE, or become a badge?

---

## Default Assumptions and First Impression

### The Problem With Current Defaults

The first thing a policy maker or investor sees when they open the dashboard is the result of our default assumptions. If the defaults are too pessimistic, every KEK shows "Not Competitive" and the reaction is "then what's the point of this tool?" If too optimistic, every KEK shows "Full RE" and they don't trust the numbers.

Current defaults and their effect:

| Parameter | Default | Effect on First Impression |
|-----------|---------|---------------------------|
| WACC | 10% | Reasonable market rate. Makes ~15 KEKs solar-competitive. Good. |
| Solar CAPEX | $750/kW | From ESDM Technology Catalogue 2023. Defensible. |
| BESS CAPEX | $250/kWh | BNEF 2024 Asia utility-scale. Honest. |
| BESS sizing | 14h bridge (reliability >= 0.75) | Physics-correct for 24/7 loads. But adds ~$290/MWh. |
| BESS sizing | 2h cloud-firming (reliability < 0.75) | Only smoothing cloud events. Adds ~$45/MWh. |
| Grid benchmark | BPP (cost of supply) | Higher than tariff. Makes solar look better. Honest for PLN economics. |

**The result at first load:**
- Solar LCOE: $55-70/MWh at most KEKs (competitive with BPP of $60-85/MWh)
- Solar + 14h BESS: $345-360/MWh (way above grid at every KEK)
- Solar + 2h BESS: $80-115/MWh (borderline at some KEKs)

With the current 1D system, this produces a confusing mix: some KEKs show `solar_now` (hiding that 24/7 needs $290/MWh storage), others show `invest_battery` (sounding like a recommendation to spend $290/MWh).

### How Option C Fixes the First Impression

With the 2D system, the same defaults produce a clear, honest picture:

**Solar mode at first load (est. 25 KEKs):**
- ~0 KEKs as **Full RE** (14h BESS at $250/kWh kills 24/7 economics everywhere)
- ~12-15 KEKs as **Partial RE** (daytime solar beats grid)
- ~4 KEKs as **Near Parity** (within 20% of grid, resilience value)
- ~3-4 KEKs as **Not Competitive** (poor solar resource or high grid subsidy)
- ~2-3 KEKs as **No Resource** (no buildable land)

**Hybrid mode at first load:**
- ~3-5 KEKs as **Full RE** (wind covers nighttime, hybrid all-in beats grid)
- ~10-12 KEKs as **Partial RE**
- ~4 KEKs as **Near Parity**
- Rest as Not Competitive / No Resource

This is the story the dashboard should tell on first load:

> "In solar mode, about half of Indonesia's KEKs can profitably use solar during the daytime. None can go 24/7 solar at current battery prices. Switch to hybrid mode and you'll see 3-5 KEKs where solar+wind together beat the grid 24/7, because wind covers the nighttime gap that batteries can't yet afford to fill."

That's honest. That's useful. And it naturally guides the user to explore hybrid mode.

### Why "Partial RE" Needs to Feel Like a Win

The whole system depends on "Partial RE" reading as a POSITIVE result, not a consolation prize. A policy maker sees "Partial RE" on 12 KEKs and needs to think "great, that's 12 KEKs where we can start deploying solar today" not "only partial? that's disappointing."

The framing:
- **Color**: Light green (not yellow or orange). Green = good.
- **Label**: "Partial RE" or maybe "Solar Ready" or "Daytime RE" (something that sounds actionable)
- **First line of explanation**: "Solar cuts daytime energy costs by X%. Deploy now, expand to 24/7 when storage costs drop."
- **Energy balance chart**: Shows the 42% daytime bar in green (covered!) with 58% nighttime in a neutral tone (grid). Visually, almost half the bar is green. That feels substantial.

Alternative labels to consider (instead of "Partial RE"):
- **"Daytime RE"** — describes what you get, not what you're missing
- **"Solar Ready"** — action-oriented, positive
- **"RE Competitive"** — true (it is competitive, for daytime)
- **"Deploy Solar"** — most direct

vs the negative framing we want to avoid:
- ~~"Partial Coverage"~~ — sounds incomplete
- ~~"Needs Storage"~~ — sounds like a problem
- ~~"Daytime Only"~~ — sounds limited

### What About the BESS Default Specifically?

The 14h bridge at $250/kWh is the physics-correct default for high-reliability KEKs. It should stay as the default because:

1. **It's honest.** Manufacturing smelters DO need 24/7 power. Pretending 2h of cloud-firming solves their nighttime demand would be misleading.
2. **It creates the right first impression with Option C.** At 14h, zero KEKs are Full RE in solar mode. That's TRUE. It drives users to explore hybrid mode (where wind covers nighttime) or to adjust the BESS slider to see when storage pencils out.
3. **The slider lets them explore.** User drags BESS CAPEX from $250 to $150 (projected 2030 prices) and watches KEKs flip from Partial RE to Full RE. That's the "aha" moment: "at $150/kWh, 24/7 solar works at 5 KEKs."

The alternative (defaulting to 2h or 4h) would make the dashboard look more optimistic on first load, but it would be lying. A nickel smelter running 24/7 can't survive on 2h of cloud-firming BESS. The 14h default is the honest answer.

**The key shift:** with the old 1D system, the 14h default was a problem because it made `invest_battery` fire (sounding prescriptive about expensive storage). With Option C, the 14h default is fine because it just puts KEKs in "Partial RE" tier — which is honest and positive.

### Default Sensitivity: What Moves KEKs Between Tiers

| Parameter Change | Effect on Tier Distribution |
|-----------------|---------------------------|
| WACC 10% → 8% (concessional finance) | ~3-4 more KEKs move from Near Parity → Partial RE |
| WACC 10% → 6% (DFI blended) | ~6-8 more KEKs become Partial RE, 1-2 become Full RE |
| BESS CAPEX $250 → $150/kWh (2030 projection) | ~3-5 KEKs move from Partial RE → Full RE in solar mode |
| BESS CAPEX $250 → $100/kWh (2035 projection) | ~8-10 KEKs become Full RE |
| Solar CAPEX $750 → $500/kW (global trend) | Most KEKs become Partial RE or better |
| Switch to Hybrid mode | ~3-5 KEKs gain Full RE (wind covers nighttime) |
| Add CBAM savings | ~3-4 CBAM-exposed KEKs effectively upgrade one tier |

This table is the dashboard's real power. A policy maker adjusts one slider and watches KEKs light up. The defaults are the starting point. The sliders are the story.

### Summary: The Right Default is One That Tells a True Story

The defaults should produce a dashboard where:
- **About half** the KEKs are in a positive tier (Partial RE or better) — "solar works here, at least for daytime"
- **A few** are in Near Parity — "close, small policy nudge could tip it"
- **Some** are Not Competitive — "grid is genuinely cheaper here"
- **Zero** are Full RE in solar mode — "24/7 solar doesn't pencil at current battery prices" (honest)
- **A few** are Full RE in hybrid mode — "wind+solar together can do 24/7" (hopeful, real)

Current defaults already produce roughly this distribution. The problem isn't the defaults. The problem is the 1D flag system that either hides the nuance (`solar_now` hiding the storage gap) or sounds prescriptive about unrealistic investments (`invest_battery`). Option C fixes the framing without changing the math.

---

## Updated Cost Research (April 2026)

The ESDM Technology Catalogue is from 2023. Solar and BESS costs have moved a lot since then. Here's where prices actually are.

### BESS: $250/kWh Is Outdated. Current Reality is $110-150/kWh.

This is the biggest finding. Battery costs dropped faster than anyone expected.

| Metric | Our Default | 2025 Reality | Source |
|--------|-------------|-------------|--------|
| LFP pack price (stationary) | — | **$70/kWh** | BNEF Dec 2025 |
| Full system cost (4h, global) | $250/kWh | **$110/kWh** | BNEF 2025 system survey |
| Full system cost (non-China/US) | $250/kWh | **$125/kWh** | Ember Dec 2025 |
| Chinese competitive tenders | — | **$63/kWh** | BNEF 2025 |

**Projections:**
- $150/kWh installed system: **already passed** globally (BNEF global avg is $117/kWh)
- $100/kWh installed system: expected **2027-2028** outside China
- Goldman Sachs: pack prices below $60/kWh by 2030

**What this means for the 14h bridge adder:**

| BESS CAPEX | 14h Bridge Adder | 2h Cloud-Firming Adder |
|-----------|-----------------|----------------------|
| $250/kWh (current default) | ~$290/MWh | ~$45/MWh |
| $150/kWh (Indonesia 2025) | ~$174/MWh | ~$27/MWh |
| $125/kWh (global 2025) | ~$145/MWh | ~$22/MWh |
| $100/kWh (est. 2028) | ~$116/MWh | ~$18/MWh |

At $150/kWh, the 14h bridge is still too expensive for Full RE at most KEKs (solar $65 + $174 BESS = $239/MWh vs grid $85/MWh). But 2-4h cloud-firming becomes very cheap ($27/MWh). And hybrid mode (wind covers night) gets even more attractive since the reduced BESS hours × lower CAPEX compounds.

**Recommendation:** Update default to **$150/kWh** for Indonesia. It's conservative relative to global benchmarks ($110-125/kWh) but accounts for Indonesia's nascent BESS market, logistics to remote sites, and regulatory uncertainty. PLN's first integrated solar+BESS was only deployed in 2025 (IKN Nusantara). Slider range: $80-400/kWh.

Sources: BNEF Battery Price Survey 2025, Ember "How Cheap is Battery Storage?" Dec 2025, Goldman Sachs Oct 2024 outlook.

### Solar CAPEX: $960/kW Is High-End But Defensible. Could Justify $850/kW.

| Metric | Our Default | 2024 Reality | Source |
|--------|-------------|-------------|--------|
| Global weighted average | $960/kW | **$691/kW** | IRENA RPGC 2024 |
| Asia excl. China/India | $960/kW | **$1,133/kW** | IRENA RPGC 2024 |
| Indonesia market estimate | $960/kW | **$800-1,000/kW** | Industry analysis |
| Module price (cell level) | — | **$0.07-0.09/W** | BNEF 2024 (historic low) |

Indonesia sits between the global average (pulled down by China at $591/kW) and the regional average for rest-of-Asia ($1,133/kW). The $960/kW from ESDM is from 2023 price year. Market reality for well-executed Indonesian projects is now $800-900/kW.

**Note:** Chinese module oversupply drove prices to historic lows in 2024, but Chinese government intervention (VAT rebate removal, production caps) is pushing module prices back up ~9% in late 2025. So the floor may have been reached.

**IEA finding on WACC:** Indonesia's median WACC for utility-scale solar = 9.4% (IEA Cost of Capital Observatory 2024). Our 10% default is slightly conservative. Good.

**Recommendation:** Could update default to **$850/kW** to reflect 2024-2025 market. Or keep $960/kW as the "official ESDM" reference and note the gap in methodology docs. The slider range ($600-$1,500/kW) already covers the full spectrum.

Sources: IRENA Renewable Power Generation Costs 2024, IEA Cost of Capital Observatory 2024.

### Wind CAPEX: $1,650/kW Is Correct for Indonesia.

| Metric | Our Default | 2024 Reality | Source |
|--------|-------------|-------------|--------|
| Global weighted average | $1,650/kW | **$1,041/kW** | IRENA RPGC 2024 |
| Indonesia actual projects | $1,650/kW | **$1,667-2,000/kW** | Sidrap ($2,000/kW), Tolo ($1,667/kW) |
| Non-China emerging markets | $1,650/kW | **$1,200-1,800/kW** | IRENA regional data |

Indonesia has only ~150 MW of onshore wind total (two projects in Sulawesi). No local supply chain, no local service infrastructure. The $1,650/kW from ESDM 2024 sits right between the global average (too optimistic for Indonesia) and realized Indonesian costs (which included first-mover premiums).

**Recommendation:** Keep $1,650/kW. Well-sourced and appropriate. O&M at $40/kW/yr is high-end of global ($20-35/kW) but defensible for Indonesia.

### Impact on First Impression (Updated Defaults)

If we update BESS from $250 to $150/kWh and solar from $960 to $850/kW:

**Solar mode:**
- Solar LCOE drops from ~$55-70/MWh to ~$48-62/MWh (more KEKs become Partial RE)
- 14h BESS adder drops from ~$290 to ~$174/MWh (still too expensive for Full RE)
- Result: **more** KEKs in Partial RE, **still zero** Full RE in solar mode
- 2-4h cloud-firming becomes very cheap ($27-54/MWh), making daytime solar + light firming competitive

**Hybrid mode:**
- Hybrid all-in improves because reduced BESS hours × lower BESS CAPEX compounds
- Result: possibly **5-8** KEKs in Full RE (up from 3-5), more in Partial RE

**The story improves without becoming unrealistic.** More green on the map at first load, but the 24/7 solar gap stays visible (still requires hybrid or future battery cost drops).

---

## Color System: Every Color Needs a Reason

Colors are not decoration. They're the first thing a policy maker reads, before any text. A green dot next to a KEK name means "good" and a red dot means "problem" before anyone reads the label. If the colors are arbitrary or inconsistent, the dashboard loses trust.

### Design Principles

1. **Green spectrum = economic viability.** Traffic light metaphor. Green = go/deploy. Red = stop/not viable. Universal, no learning curve.
2. **Blue spectrum = infrastructure investment.** Blue = build/physical/investment. Common in infrastructure and engineering dashboards. Distinct from the economics dimension.
3. **Warm tones (orange, amber) = external pressure or time-sensitive.** CBAM is an external EU policy that creates urgency. Near Parity is "almost there, needs a nudge."
4. **Purple = planning/timeline.** RUPTL timing is a planning dimension, distinct from economics and infrastructure.
5. **Gray = N/A.** Physical constraint (no land), nothing the user can act on.

### Economic Tier Colors

| Tier | Color | Hex | Why This Color |
|------|-------|-----|---------------|
| **Full RE** | Dark green | `#2E7D32` | "Go. Deploy 24/7 RE now." Strongest positive signal. Same green family as current `solar_now`. |
| **Partial RE** | Light green | `#66BB6A` | "Positive. Actionable. Deploy daytime solar." Still green (good!), but lighter to signal "not the whole picture." User sees green and thinks "there's something to do here." |
| **Near Parity** | Amber | `#F57C00` | "Close. One policy lever could tip it." Amber = caution/opportunity, not failure. Same color family as current `invest_resilience` (which is the conceptual ancestor). |
| **Not Competitive** | Red | `#C62828` | "Stop. Grid is genuinely cheaper." Clear negative signal. Matches current `not_competitive`. |
| **No Resource** | Gray | `#78909C` | "N/A. Physical constraint." Not a judgment, just a fact. Matches current `no_solar_resource`. |

**Why light green for Partial RE and not yellow or orange:** This is the most important color choice. ~12-15 KEKs will land here at first load. If this tier is yellow/orange, the dashboard screams "warning" on half the KEKs. If it's light green, the dashboard says "opportunity here" on half the KEKs. Same data, completely different emotional read.

A policy maker opens the dashboard and sees 12 green dots (light + dark) and 4 orange dots and 6 red/gray dots. That reads as: "About half of our KEKs have RE potential. Let's look at which ones." That's the right first impression.

If those 12 were yellow, the read would be: "Everything is borderline." That kills momentum.

### Infrastructure Colors

| Category | Color | Hex | Why This Color |
|----------|-------|-----|---------------|
| **Within Boundary** | Subtle green check or no badge | — | No infrastructure needed. Don't clutter with a badge for "nothing to do." |
| **Grid Ready** | Light blue | `#42A5F5` | "Infrastructure is there, minor work." Light = easy. Blue = infrastructure family. |
| **Invest Transmission** | Medium blue | `#0277BD` | "Investment needed. Build transmission." Deeper blue = bigger investment. |
| **Invest Substation** | Teal | `#00838F` | Same investment family, slightly different hue to distinguish from transmission. |
| **Grid First** | Dark blue | `#1565C0` | "Heavy infrastructure. Biggest investment." Darkest blue = most work needed. |

**Why blue for infrastructure:** Blue is the standard "build/invest/engineering" color in infrastructure dashboards. It's visually distinct from the green-amber-red economic spectrum, so a user can instantly tell "green badge = economics, blue badge = infrastructure" without reading labels.

The gradient from light to dark blue maps to investment size: light blue (Grid Ready, minor) → dark blue (Grid First, major). A DFI investor scanning the table sees the blue intensity and knows where the big infrastructure opportunities are.

### Badge Colors

| Badge | Color | Hex | Why This Color |
|-------|-------|-----|---------------|
| **CBAM Urgent** | Orange | `#FF6F00` | External EU policy pressure. Orange = urgency, distinct from amber (which is "close/opportunity"). Slightly warmer/brighter than Near Parity amber to signal "act now, external deadline." |
| **Plan Late** | Purple | `#7B1FA2` | RUPTL timeline risk. Purple = planning dimension. Completely distinct from economics (green/red) and infrastructure (blue), signaling this is about TIMING, not viability. |
| **Storage Info** | No color / text only | — | Informational, not a recommendation. Just shows "$X/MWh for Yh of storage." No badge color needed. It's data, not a signal. |

### How It Reads Together (Examples)

**Maloy Batuta:** `Partial RE` (light green) + no infra badge (within boundary) + `CBAM` (orange)
→ User sees: green dot, orange accent. "Something positive here, with urgency."

**Sei Mangkei:** `Not Competitive` (red) + `Invest Substation` (teal)
→ User sees: red dot, blue accent. "Economics don't work AND needs infrastructure."

**Kendal:** `Near Parity` (amber) + no infra badge (grid ready) + `Plan Late` (purple)
→ User sees: amber dot, purple accent. "Close, with timeline risk."

**Galang Batang (hybrid mode):** `Full RE` (dark green) + no infra badge (within boundary) + `CBAM` (orange)
→ User sees: dark green dot, orange accent. "Best case. Deploy now, CBAM adds urgency."

### Color Accessibility

- Green/red distinction: we avoid relying on green vs red alone. The tier LABELS ("Full RE" vs "Not Competitive") carry the meaning. Colors reinforce but don't replace text.
- Blue is safe for color-blind users (most common deficiency is red-green, not blue).
- Each tier also has a distinct ICON or SHAPE in the flag ladder, not just color.

### What Changes From Current

| Current | New | Why |
|---------|-----|-----|
| `solar_now` = dark green | `Full RE` = dark green | Same color, clearer meaning |
| `invest_battery` = light orange | Absorbed into tier system | No longer a standalone badge |
| `invest_resilience` = medium orange | `Near Parity` = amber | Same color family, clearer name |
| `invest_transmission` = blue | `Invest Transmission` = blue | Unchanged (moved to infrastructure dimension) |
| `invest_substation` = teal | `Invest Substation` = teal | Unchanged |
| `grid_first` = dark blue | `Grid First` = dark blue | Unchanged |
| `not_competitive` = red | `Not Competitive` = red | Unchanged |
| `plan_late` = purple | `Plan Late` = purple badge | Same color, now a badge not primary flag |
| `no_solar_resource` = gray | `No Resource` = gray | Unchanged |

The infrastructure and modifier colors stay the same. The big change is the economic tier (green spectrum replaces the confusing `solar_now` / `invest_battery` / `invest_resilience` trio).

---

## Recommended Default Updates (Applied April 2026)

These defaults have been updated in `src/assumptions.py` and `docs/METHODOLOGY_CONSOLIDATED.md`.

| Parameter | Old Default | New Default | Source | Rationale |
|-----------|-------------|-------------|--------|-----------|
| Solar CAPEX | $960/kW | **$850/kW** | IRENA RPGC 2024 | ESDM 2023 is 3yr old; $850 = Indonesia mid-range 2025. Pipeline still extracts 960 from ESDM PDF. |
| BESS CAPEX | $250/kWh | **$150/kWh** | BNEF + Ember 2025 | Global system $110-125/kWh; $150 = conservative Indonesia estimate (+logistics, import duties) |
| Wind CAPEX | $1,650/kW | $1,650/kW | Keep | Limited Indonesia wind market, no downward pressure data |
| WACC | 10% | 10% | IEA 2024 | Indonesia RE financing cost unchanged |
| Solar FOM | $7.5/kW/yr | $7.5/kW/yr | Keep | ESDM value still reasonable |
| BESS RTE | 87% | 87% | Keep | Reflects utility-scale LFP AC-to-AC |
| Solar lifetime | 27 yr | 27 yr | Keep | ESDM value reasonable |

### Impact on BESS economics

At the new $150/kWh default:
- **14h bridge (high-reliability):** ~$174/MWh adder (was ~$290 at $250/kWh). Still above grid for most KEKs, but the gap is closing.
- **2h cloud-firming:** ~$27/MWh adder (was ~$45). Now competitive with grid for several KEKs.
- **4h RKEF nickel:** ~$54/MWh adder (was ~$90). Getting close to grid parity.

### Sources

- BNEF Dec 2025: LFP battery pack $70/kWh; utility-scale system $110/kWh (global)
- BNEF 2025: Chinese domestic tender average $63/kWh
- Ember Dec 2025: Battery system cost $125/kWh (non-China/US markets)
- IRENA RPGC 2024: Global solar PV $691/kW; Asia ex-China/India $1,133/kW
- IEA Cost of Capital Observatory 2024: Indonesia RE WACC ~10%
- Goldman Sachs Oct 2024: Battery cost projections (confirms BNEF trajectory)
