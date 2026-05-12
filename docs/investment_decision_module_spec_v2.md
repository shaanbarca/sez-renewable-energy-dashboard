# Feature Spec: Investment Decision Support Module (v4.2)

**Status:** Drafted based on feedback from Pak Faiz (former CSO, Medco)
**Target version:** v4.2 (phased rollout: v4.1.5 → v4.2 → v4.2.5)
**Total estimated effort:** 6-8 weeks calendar time with parallel data work
**Framing:** Screening-level indicative metrics, NOT project-specific due diligence

---

## Table of Contents

| § | Section | Purpose | Can Skip? |
|---|---|---|---|
| 1 | Background and Framing | Context from Pak Faiz feedback; screening vs due diligence positioning | No — core framing |
| 2 | Triage of Feedback | What we build, defer, decline | No — decision record |
| 3 | Staged Implementation Strategy | Why we ship in 3 tiers instead of one big release | No — key architectural decision |
| 4 | Tier 1 Spec — Indicative Economics | Payback, NPV, IRR, PI implementation | No if implementing Tier 1 |
| 5 | Tier 2 Spec — Lender Metrics | DSCR, LLCR, debt schedule | Skip if only doing Tier 1 |
| 6 | Tier 3 Spec — Advanced Features | Sensitivity, scenarios, corporate finance toggle | Skip if only doing Tier 1-2 |
| 7 | Parallel Data Work | BPS, fiscal incentives, TKBI, regulatory context | Independent workstream |
| 8 | Learning Resources | For Shaan before implementation | Reference only |
| 9 | Credibility and Framing Guardrails | UI text, disclaimers, "what this is not" | No — critical for defensibility |
| 10 | Validation Strategy | Benchmark projects for cross-checking | No — required before public release |
| 11 | To-Do List (Prioritized) | Actionable task list with effort estimates | No if planning implementation |
| 12 | Success Criteria | How we know when each tier is done | No |
| 13 | Risks and Mitigations | Known problem areas | Reference |
| 14 | Relationship to Other v4.x Work | How this fits with substation fix, rooftop, etc. | Reference |

---

## 1. Background and Framing

Pak Faiz reviewed the dashboard and identified that the tool currently outputs LCOE (engineering-economic metric) but not the project finance metrics that actual investment committees use. His suggestions group around two use cases:

**Use case 1:** Policy-making aids (Government)
**Use case 2:** Investment strategy support (Companies — private and state-owned)

**Core positioning decision:** This feature builds **screening-level indicative project finance metrics**, NOT project-specific due diligence. The distinction is critical:

| Stage | What it does | Who does it | Data required |
|---|---|---|---|
| Stage 1: Universe screening | Rank sites across investment universe | Analysts, policy planners | Public data, standardized assumptions |
| Stage 2: Shortlist evaluation | Evaluate top 20 candidates | Investment teams | Public + some private data |
| Stage 3: Project due diligence | Build detailed financial model | Advisory firms with NDA access | Negotiated PPA, EPC contracts, etc. |

**This tool lives entirely in Stage 1.** It does not attempt Stage 3 precision and explicitly disclaims this limitation.

A project finance professional looking at this tool should think: "Good screening-level framework with defensible standardized assumptions. For my actual analysis I'd build a proper model, but this helps me see which sites are worth looking at." That's the target reaction.

---

## 2. Triage of Feedback

### 2.1 Accept and implement

| Suggestion | Tier | Rationale |
|---|---|---|
| IRR, NPV, PI, Payback | 1 | Foundation metrics; mechanically simple; high credibility value |
| DSCR, LLCR, DER | 2 | Lender metrics; requires debt schedule; high investor-user value |
| Project vs corporate finance toggle | 3 | Different financing structures affect defaults; medium complexity |
| Fiscal incentive summary | Parallel | KEK/KI tax holidays are well-documented; low effort, high value |
| Regional GDP by province | Parallel | BPS data pull; 2-hour task; useful context |
| TKBI green finance tagging | Parallel | Formal Indonesian taxonomy; directly relevant to DFI investors |
| Regulatory context panel | Parallel | Factual replacement for "Policy Consistency Score" |

### 2.2 Defer to v4.3+

| Suggestion | Reason |
|---|---|
| Export Connectivity Readiness | Computable from OSM + port data, 2-3 days work, not blocking |
| Job Creation Index | Sectoral labor intensities vary enormously; needs careful sourcing |
| Carbon Credit Opportunity | IDXCarbon market too nascent; methodology speculative |

### 2.3 Decline with reasoning

| Suggestion | Reason |
|---|---|
| Policy Consistency Score | Unquantifiable objectively; politically charged; replaced by Regulatory Context panel |
| Policy Stability Index | Same issue as above |
| PPP Leverage Ratio | Data fragmented, no reliable source |

---

## 3. Staged Implementation Strategy

**Why staged rollout instead of single release:**

1. Ships visible value within 2 weeks (Tier 1) instead of waiting 4+ weeks
2. Allows learning-during-building rather than front-loading finance expertise
3. Enables user feedback after each tier before committing to next-tier details
4. Provides graceful degradation if time gets constrained by other commitments
5. Enables relationship-closing with Pak Faiz earlier (show Tier 1 implementation, request feedback before Tier 2)

**Three tiers with clear scope boundaries:**

### Tier 1 (v4.1.5) — "Indicative Project Economics"
- Simple payback, discounted payback
- NPV at user-specified discount rate
- Equity IRR, Project IRR
- Profitability Index
- Annual cash flow table
- **Effort: ~1 week focused work**
- **Foundation for Tier 2-3; does not require advanced finance knowledge**

### Tier 2 (v4.2) — "Lender Metrics"
- Debt amortization schedule
- Year-by-year DSCR
- Minimum and average DSCR
- LLCR (Loan Life Coverage Ratio)
- DER (Debt/Equity Ratio)
- **Effort: additional ~1 week**
- **Requires understanding of debt structure, which Tier 1 implementation teaches**

### Tier 3 (v4.2.5) — "Advanced Features"
- Tornado sensitivity charts (tariff, CAPEX, CF)
- Project finance vs corporate finance toggle
- Scenario comparison across sites
- Monte Carlo risk analysis (optional, nice-to-have)
- **Effort: additional 1-2 weeks**
- **Polish and sophistication layer**

### Parallel Track — Data Additions
- BPP refresh to PLN Statistik 2024 (1 day)
- Grid emission factor update (0.5 day)
- Regional GDP by province (0.5 day)
- TKBI classification mapping (2-3 days)
- Fiscal incentive panel for KEK/KI sites (2-3 days)
- Regulatory context panel (2 days)
- **Runs in parallel with Tier 1-3 work; does not require finance expertise**

---

## 4. Tier 1 Spec — Indicative Economics (v4.1.5)

### 4.1 Scope

Output these metrics per site, framed as "Indicative" throughout:

| Metric | Definition | Use |
|---|---|---|
| Simple Payback | Years until cumulative cash flow ≥ initial investment | Intuitive screening |
| Discounted Payback | Same but using discounted cash flows | Slightly more rigorous screening |
| NPV (at user-set rate) | Present value of cash flows minus initial investment | Go/no-go indicator |
| Equity IRR | Discount rate where equity NPV = 0 | Equity investor ranking |
| Project IRR | Discount rate where total project NPV = 0 | Overall project return |
| Profitability Index | NPV / Initial Investment | Capital-constrained ranking |

### 4.2 Inputs

**Existing (no new inputs needed):**
- CAPEX per MW (from ESDM catalog, already in scorecard)
- OPEX per year (from ESDM catalog)
- Annual energy generation = capacity × 8760 × capacity factor
- Capacity factor (from Global Solar Atlas)
- Project lifetime (default 25 years)
- WACC (existing slider)

**New inputs with defaults:**
- Tariff assumption (default: regional BPP; user-adjustable)
- Annual degradation (default 0.5%/year for solar)
- Construction period (default 2 years)

### 4.3 Calculation logic

Build annual cash flow stream:

```
Year 0: -CAPEX (negative cash flow, investment)
Year 1 to N: Revenue - OPEX - Tax (positive cash flow, operations)

Where:
  Revenue(t) = Energy(t) × Tariff
  Energy(t) = Nameplate × CF × 8760 × (1 - degradation)^(t-1)
  OPEX(t) = Initial OPEX × (1 + inflation)^(t-1)
  Taxable_Income(t) = Revenue(t) - OPEX(t) - Depreciation(t)
  Tax(t) = max(0, Taxable_Income(t) × 22%)
```

Apply financial functions:

```python
import numpy as np

# NPV at discount rate
npv = np.npv(discount_rate, cash_flows)

# IRR
irr = np.irr(cash_flows)

# Profitability Index
pi = (npv + initial_investment) / initial_investment

# Simple payback
cumulative_cf = np.cumsum(cash_flows)
payback_year = np.argmax(cumulative_cf >= 0)
```

### 4.4 Implementation location

New module: `src/model/project_finance.py`

```python
def compute_tier1_metrics(
    capex_total_usd: float,
    opex_annual_usd: float,
    annual_energy_mwh: float,
    tariff_usd_per_mwh: float,
    lifetime_years: int = 25,
    degradation_rate: float = 0.005,
    tax_rate: float = 0.22,
    discount_rate: float = 0.10,
    inflation_rate: float = 0.03,
    construction_years: int = 2,
) -> dict:
    """
    Compute Tier 1 indicative project finance metrics.
    
    Returns dict with: npv, irr, pi, simple_payback_years,
                       discounted_payback_years, cash_flow_table
    
    NOTE: These are INDICATIVE screening metrics based on standardized
    assumptions. Not suitable for project-specific due diligence.
    """
```

### 4.5 UI integration (Tier 1)

New Score Drawer tab: **"Project Economics (Indicative)"**

```
┌─ Project Economics (Indicative) ───────────────────────────────┐
│                                                                 │
│  ⚠ Screening-level estimates using standardized assumptions    │
│     [What this is not →]                                        │
│                                                                 │
│  Inputs:                                                        │
│   Tariff assumption: $[85]/MWh  (Default: Regional BPP)        │
│   Discount rate:     [10.0]%    (Current WACC setting)         │
│                                                                 │
│  Indicative Returns:                                            │
│   Simple Payback:    8.2 years                                  │
│   Discounted Payback: 11.5 years                                │
│   NPV @ 10%:         $14.2M                                     │
│   Project IRR:       13.8%                                      │
│   Profitability Idx: 1.18                                       │
│                                                                 │
│  [View 25-year cash flow projection]                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6 Output fields added to fct_site_scorecard.csv

```
indicative_payback_years
indicative_discounted_payback_years  
indicative_npv_at_wacc_usd
indicative_project_irr_pct
indicative_profitability_index
tariff_assumption_used_usd_per_mwh
```

### 4.7 Tests required

- Cross-validate against numpy/scipy financial functions on simple cases
- Validate against Cirata floating PV published economics (expected IRR ~8-10%)
- Unit tests for edge cases (zero revenue, negative NPV, high degradation)
- Regression test: ensure LCOE outputs unchanged from v4.0

---

## 5. Tier 2 Spec — Lender Metrics (v4.2)

### 5.1 Scope

Add debt-focused metrics once Tier 1 is shipped and validated.

| Metric | Definition | Use |
|---|---|---|
| DSCR (year-by-year) | EBITDA / Debt Service each year | Lender covenant test |
| Minimum DSCR | Minimum across operating years | Worst-case lender view |
| Average DSCR | Mean across operating years | Typical lender view |
| LLCR | NPV(CF during loan) / Loan outstanding | Lender stress test |
| DER | Debt / Equity | Capital structure indicator |

### 5.2 Additional inputs

```
debt_share: float = 0.70          # Project finance typical
debt_tenor_years: int = 15         # Match to project economics
debt_interest_rate: float = 0.085  # Current Indonesian IPP market rate
```

### 5.3 Calculation logic

Build debt amortization schedule (equal annual payments):

```python
def compute_debt_service(principal, rate, tenor):
    """Equal annual debt service payments."""
    annual_payment = principal * (rate * (1+rate)**tenor) / ((1+rate)**tenor - 1)
    schedule = []
    outstanding = principal
    for year in range(1, tenor+1):
        interest = outstanding * rate
        principal_payment = annual_payment - interest
        schedule.append({
            'year': year,
            'interest': interest,
            'principal': principal_payment,
            'total_ds': annual_payment,
            'outstanding_start': outstanding,
            'outstanding_end': outstanding - principal_payment,
        })
        outstanding -= principal_payment
    return schedule
```

Compute DSCR per year:

```python
def compute_dscr_schedule(ebitda_annual, debt_service_annual):
    return [
        ebitda[y] / debt_service[y] 
        for y in range(len(ebitda))
    ]
```

Compute LLCR:

```python
def compute_llcr(cash_flows_during_loan, debt_outstanding, discount_rate):
    npv_cf = np.npv(discount_rate, cash_flows_during_loan)
    return npv_cf / debt_outstanding
```

### 5.4 UI additions (Tier 2)

Extend Project Economics tab:

```
│  Lender Metrics:                                                │
│   Min DSCR:          1.42    ✓ above 1.30 typical covenant     │
│   Avg DSCR:          1.68                                       │
│   LLCR:              1.55                                       │
│   DER:               2.33    (70/30 debt-equity)                │
│                                                                 │
│  Debt structure:                                                │
│   Debt share: [70]%    Tenor: [15] years   Rate: [8.5]%        │
│                                                                 │
│  [View debt amortization schedule]                              │
```

### 5.5 Additional output fields

```
indicative_dscr_min
indicative_dscr_avg
indicative_llcr
indicative_der
debt_assumption_share
debt_assumption_tenor_years
debt_assumption_interest_rate
```

---

## 6. Tier 3 Spec — Advanced Features (v4.2.5)

### 6.1 Sensitivity analysis (tornado chart)

For each site, show how IRR changes with:
- Tariff ±20%
- CAPEX ±15%
- Capacity factor ±10%
- WACC ±2 percentage points
- OPEX ±20%

Visual: horizontal bar chart with variables ranked by IRR impact.

### 6.2 Project finance vs corporate finance toggle

Two preset financing structures:

**Project finance mode:**
- 70% debt / 30% equity
- 15-year debt tenor
- Higher interest rate (project risk)
- DSCR is primary metric

**Corporate finance mode:**
- 50% debt / 50% equity  
- 10-year debt tenor
- Lower interest rate (corporate credit)
- DER and credit metrics are primary

Toggle switches defaults and emphasizes different outputs.

### 6.3 Scenario comparison across sites

"Which 10 sites have the highest Equity IRR under concessional financing?"

Cross-site ranking view with filters on:
- Financing scenario
- Sector
- Region
- CBAM exposure

### 6.4 Monte Carlo (optional, nice-to-have)

Probabilistic analysis with distributions around key assumptions. Probably too complex for v4.2.5; defer if time-constrained.

---

## 7. Parallel Data Work

These tasks run independently of Tier 1-3 implementation and do not require project finance expertise.

### 7.1 BPP refresh to PLN Statistik 2024

**Effort:** 1 day
**Deliverable:** Updated regional BPP values across all 81 sites
**Priority:** High (underlying all tariff assumptions)

### 7.2 Grid emission factor update

**Effort:** 0.5 day
**Deliverable:** Updated KESDM emission factors per grid system
**Priority:** Medium

### 7.3 Regional GDP by province

**Effort:** 0.5 day
**Deliverable:** Provincial GDP + growth rate added to site context
**Priority:** Medium-Low (nice context but not critical)

### 7.4 Fiscal incentive panel

**Effort:** 2-3 days
**Deliverable:** Per-site display of applicable incentives:
- KEK tax holiday eligibility and duration
- KI tax allowance per GR 78/2019
- Import duty exemptions
- VAT facility
- Sectoral renewable tax allowance under GR 50/2023

Structured data table, updated as regulations change.

### 7.5 TKBI green finance taxonomy tagging

**Effort:** 2-3 days
**Deliverable:** Per-site classification as Green/Amber/Red per TKBI v2
**Source:** Indonesia Sustainable Finance Taxonomy document
**Priority:** High (directly relevant to DFI users)

### 7.6 Regulatory context panel

**Effort:** 2 days
**Deliverable:** Per-sector display of applicable regulations:
- Perpres 112/2022
- ESDM 2/2024 (rooftop)
- KEK Law and amendments
- GR 78/2019 (tax allowance)
- GR 50/2023 (renewable tax)
- CBAM Implementing Regulations

Factual content, not scoring. Updates as regulations change.

---

## 8. Learning Resources (for Shaan)

**Minimum necessary learning before Tier 1 implementation:**

**Yescombe "Principles of Project Finance" (2nd ed, 2014), Chapters 12-13**
- Chapter 12: Financial Structure (debt/equity split, debt service, covenants)
- Chapter 13: Financial Modeling and Evaluation (NPV, IRR, DSCR, sensitivity)
- Time: ~4 hours focused reading
- Value: 80% of conceptual framework needed

**NREL "Project Finance Modeling" training materials (free, online)**
- Walks through solar project finance model step by step
- Practical rather than theoretical
- Time: ~6 hours one weekend
- Value: Implementation patterns

**Nice-to-have but not required:**
- Damodaran NYU Stern NPV/IRR lectures (YouTube, free)
- IFC Project Finance in Developing Countries case studies
- Breaking Into Wall Street Project Finance course (paid, overkill)

**Recommended schedule:**
- Weekend before Tier 1 implementation: Yescombe ch 12-13 + NREL materials
- Weekday: Sketch Tier 1 implementation on paper
- Following weekend: Implement Tier 1

---

## 9. Credibility and Framing Guardrails

### 9.1 "Indicative" framing everywhere

Every metric display uses "Indicative" as adjective:
- "Indicative IRR: 13.8%"
- "Indicative DSCR: 1.42"
- "Indicative Payback: 8.2 years"

This single word changes user expectation from "precise" to "approximate."

### 9.2 Mandatory disclaimer text

Every project finance output carries this text (in tooltip or footer):

> Based on standardized project finance assumptions. Actual project-specific analysis requires negotiated PPA terms, detailed EPC contracts, and site-specific diligence.

### 9.3 "What This Is Not" methodology section

Dedicated section in methodology doc:

> This tool provides screening-level project economics using standardized industry assumptions. It does not substitute for project-specific financial modeling, which requires:
> 
> - Negotiated PPA tariff with specific escalation and indexing
> - Detailed debt term sheets including covenants and reserves
> - EPC contract terms, construction schedule, warranties
> - Land lease specifics and escalation
> - Insurance, tax structuring, decommissioning provisions
> - Site-specific technical diligence
>
> Indicative metrics from this tool should be used for comparative site screening, not investment committee decisions. Actual project evaluation requires advisory firms with NDA access to deal documents.

### 9.4 Standardized assumptions transparency

Methodology section lists every assumption with source:

| Assumption | Value | Source |
|---|---|---|
| Debt share | 70% | Typical Indonesian solar IPP project finance |
| Debt tenor | 15 years | Match to 25-year project economics |
| Interest rate | 8.5% | Current IDX IPP market |
| Construction period | 2 years | IRENA benchmark for utility solar |
| Degradation | 0.5%/year | Solar panel manufacturer warranty standard |
| OPEX | $15/kW-yr | NREL benchmark |
| Corporate tax | 22% | Indonesian tax law |
| DSCR reserve | 6 months | Typical lender covenant |

### 9.5 No fake precision

Round appropriately:
- IRR: to 0.1% (not 0.01%)
- NPV: to nearest $0.1M (not nearest dollar)
- DSCR: to 0.01 (not 0.001)
- Payback: to 0.1 year

### 9.6 Ranges preferred over points

Where feasible, show ranges rather than point estimates:
- "Indicative IRR: 12-15%" rather than "Indicative IRR: 13.8%"
- "Payback: 7-9 years" rather than "Payback: 8.2 years"

Implementation: compute IRR at -10% and +10% tariff sensitivity, show the range.

---

## 10. Validation Strategy

### 10.1 Benchmark projects for cross-check

Before public release, validate Tier 1-2 outputs against known Indonesian solar projects:

**Cirata Floating PV**
- CAPEX: $145M
- Capacity: 192 MWp
- PPA tariff: $5.82 cents/kWh
- Financing: 70% ADB debt
- Expected IRR range: 8-10%
- Source: ADB board documents (public)

**Likupang Solar Project**
- CAPEX: ~$20M
- Capacity: 15 MWac
- PPA signed with PLN
- Source: PLN press releases

**Find 1-2 more similar benchmarks from IRENA or Bloomberg NEF databases**

### 10.2 Validation criteria

Each benchmark tested must produce:
- IRR within ±2 percentage points of published value
- DSCR within ±0.1 of typical lender range
- Payback within ±2 years

If not, investigate:
- Assumption mismatch
- Calculation error
- Scope difference (merchant tail, residual value)

### 10.3 Expert review

Before v4.2 public release, send to Pak Faiz with specific question:

> "For screening-level analysis of Indonesian solar projects, does this output set feel appropriately framed? Specifically, are there metrics I'm outputting that imply precision I don't have, or any I should add that would make the screening more useful?"

Incorporate feedback before Zenodo publication.

---

## 11. To-Do List (Prioritized)

### Week 1: Foundation + Learning + Parallel Data Work

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 1 | Read Yescombe ch 12-13 + NREL materials | Learn | 1 weekend | — |
| 2 | BPP refresh to PLN Statistik 2024 | Parallel | 1 day | — |
| 3 | Grid emission factor update | Parallel | 0.5 day | — |
| 4 | Close TODOs M27/M28/M29 | Cleanup | 2 days | — |
| 5 | Sketch Tier 1 implementation on paper | T1 | 0.5 day | #1 |

### Week 2: Tier 1 Implementation

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 6 | Create `project_finance.py` module | T1 | 1 day | #5 |
| 7 | Implement NPV, IRR, PI, payback | T1 | 1 day | #6 |
| 8 | Implement annual cash flow projection | T1 | 1 day | #6 |
| 9 | Unit tests for Tier 1 metrics | T1 | 0.5 day | #7, #8 |
| 10 | Cross-validate against Cirata benchmark | T1 | 0.5 day | #9 |
| 11 | Add Tier 1 fields to scorecard output | T1 | 0.5 day | #9 |

### Week 3: Tier 1 Frontend + First Parallel Features

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 12 | Build "Project Economics (Indicative)" tab | T1 | 1.5 days | #11 |
| 13 | Add "Indicative" framing throughout | T1 | 0.5 day | #12 |
| 14 | Write "What This Is Not" methodology section | T1 | 0.5 day | — |
| 15 | Regional GDP by province data pull | Parallel | 0.5 day | — |
| 16 | Fiscal incentive data compilation (start) | Parallel | 2 days | — |
| 17 | **SHIP Tier 1 as v4.1.5 to Zenodo** | T1 | 0.5 day | #12-14 |
| 18 | Email Pak Faiz with v4.1.5 notification | Relationship | 1 hour | #17 |

### Week 4: Tier 2 Implementation

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 19 | Implement debt amortization schedule | T2 | 1 day | #17 |
| 20 | Implement DSCR year-by-year | T2 | 0.5 day | #19 |
| 21 | Implement LLCR, DER | T2 | 0.5 day | #19 |
| 22 | Cross-validate Tier 2 against benchmarks | T2 | 1 day | #19-21 |
| 23 | Complete fiscal incentive panel | Parallel | 1 day | #16 |
| 24 | TKBI classification mapping | Parallel | 2 days | — |

### Week 5: Tier 2 Frontend + More Parallel Features

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 25 | Build lender metrics section in UI | T2 | 1.5 days | #22 |
| 26 | Build debt amortization table view | T2 | 1 day | #25 |
| 27 | Build fiscal incentive panel UI | Parallel | 1 day | #23 |
| 28 | Build TKBI badge UI | Parallel | 0.5 day | #24 |
| 29 | Regulatory context panel content | Parallel | 2 days | — |
| 30 | **SHIP Tier 2 as v4.2 to Zenodo** | T2 | 0.5 day | #26 |
| 31 | Request feedback meeting with Pak Faiz | Relationship | 1 hour | #30 |

### Week 6-7: Tier 3 Implementation (optional if time-constrained)

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 32 | Build sensitivity analysis (tornado chart) | T3 | 2 days | #30 |
| 33 | Implement PF vs corp finance toggle | T3 | 2 days | #30 |
| 34 | Build scenario comparison view | T3 | 3 days | #30 |
| 35 | Build regulatory context panel UI | Parallel | 1 day | #29 |
| 36 | **SHIP Tier 3 as v4.2.5 to Zenodo** | T3 | 0.5 day | #32-34 |

### Week 8+: Publishing and Follow-Up

| # | Task | Tier | Effort | Deps |
|---|---|---|---|---|
| 37 | Substack post: "Making Solar Bankable in Indonesia" | Publish | 1 day | #30 |
| 38 | LinkedIn post with v4.2 release | Publish | 1 hour | #37 |
| 39 | Update CHANGELOG, README, methodology docs | Publish | 1 day | #36 |
| 40 | Pak Faiz meeting re: DSCR thresholds | Relationship | 1 hour | #31 |

---

## 12. Success Criteria

### Tier 1 (v4.1.5) success

- [ ] All 81 sites output Indicative NPV, IRR, PI, Payback
- [ ] Cirata benchmark validates within ±2pp IRR
- [ ] "Indicative" framing appears on every metric
- [ ] "What This Is Not" section in methodology
- [ ] v4.1.5 Zenodo DOI published
- [ ] Pak Faiz notified

### Tier 2 (v4.2) success

- [ ] DSCR, LLCR, DER output for all sites
- [ ] Debt amortization table viewable per site
- [ ] Tier 1 outputs unchanged from v4.1.5 (regression)
- [ ] Fiscal incentive panel displays for KEK/KI sites
- [ ] TKBI classification for all 81 sites
- [ ] v4.2 Zenodo DOI published
- [ ] Pak Faiz feedback meeting scheduled

### Tier 3 (v4.2.5) success

- [ ] Sensitivity analysis tornado chart works
- [ ] PF vs corp finance toggle functional
- [ ] Scenario comparison across sites
- [ ] Regulatory context panel populated
- [ ] v4.2.5 Zenodo DOI published

### Overall narrative success

- [ ] Dashboard transformed from "cost comparison" to "decision support"
- [ ] Persona 5 readiness 80% → 90%
- [ ] Substack post published showing project finance view
- [ ] Pak Faiz closes feedback loop (provides post-implementation thoughts)
- [ ] Implementation visible on GitHub commit history

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Tier 1 math has bugs from rushed learning | Validate against Cirata benchmark before shipping; pair-review the calculations |
| Users misinterpret "Indicative" as precise | UI text repeated in multiple places; methodology section explicit; no fake precision in rounding |
| Tariff assumption dominates IRR output | User-adjustable tariff slider; show sensitivity prominently; default to regional BPP with citation |
| Tier 3 scope creep delays Tier 1-2 shipping | Tier 1 and Tier 2 ship independently; Tier 3 can be deferred without blocking v4.2 release |
| Pak Faiz doesn't respond after implementation | Send multiple touchpoints: v4.1.5 notification, v4.2 notification, LinkedIn tag on Substack post |
| Learning takes longer than weekend | Ship Tier 1 without Tier 2 conceptual prerequisites; learn debt structure during Tier 1 implementation |
| Standardized assumptions disagree with real deal economics | Document every assumption with source; be open to updating based on practitioner feedback |

---

## 14. Relationship to Other v4.x Work

| Feature | Status | Relationship |
|---|---|---|
| Substack Post 2 | To ship ASAP | Independent; ship before starting this |
| BPP refresh | Parallel track | Feeds tariff assumptions; should complete before Tier 1 validation |
| Substation-anchored solar fix | Planned v4.x | Independent; can proceed in parallel by different work session |
| Rooftop solar feature | Planned v4.3 | Independent; provides size proxy for potential future demand estimation |
| Industrial demand expansion | Phase 0 only | Low priority; defer full feature until post-applications |
| PyPSA Phase 1 | Deferred | Post-applications or MIT era |

**Recommended sequencing:**

1. **This week:** Ship Substack Post 2 + BPP refresh + M27 cleanup + Pak Faiz reply
2. **Week 2:** Learn project finance + start Tier 1 + start fiscal incentive compilation  
3. **Week 3:** Ship v4.1.5 + parallel data work continues
4. **Week 4-5:** Tier 2 implementation + parallel data finishing
5. **Week 6-7:** Tier 3 (if time) + substation-anchored fix (if not)
6. **Week 8+:** Publishing, relationship follow-ups, transition to rooftop solar work

---

## Appendix: Sections Safe to Remove for Claude Code

If feeding this to Claude Code for implementation, these sections are reference-only and can be removed without losing implementation guidance:

- §1 Background and Framing (context, not code)
- §2 Triage of Feedback (decision record, not code)
- §3 Staged Implementation Strategy (planning, not code)
- §8 Learning Resources (for Shaan, not Claude)
- §13 Risks and Mitigations (awareness, not code)
- §14 Relationship to Other v4.x Work (calendar planning)

**Keep for Claude Code implementation:**
- §4 Tier 1 Spec (actual implementation details)
- §5 Tier 2 Spec (if doing Tier 2)
- §6 Tier 3 Spec (if doing Tier 3)
- §7 Parallel Data Work (if doing parallel features)
- §9 Credibility and Framing Guardrails (affects code comments, UI text, methodology)
- §10 Validation Strategy (test cases)
- §11 To-Do List (task sequencing)
- §12 Success Criteria (definition of done)
