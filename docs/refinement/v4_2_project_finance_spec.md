# Feature Spec: v4.2 Project Finance Module (Refined)

**Theme:** Investment decision support. Beyond LCOE to actual project finance metrics that investment committees use.

**Why this ships after v4.1:** Project finance metrics need cost framework foundations from v4.1. NPV depends on incumbent cost (which incumbent depends on v4.1's classification logic). DSCR needs a tariff assumption (which comes from incumbent references). If we build these on the v4.0 single-LCOE framework, they need rewriting when v4.1 lands.

**Refinement note (vs v4.2 baseline):** This refined spec supersedes the original `v4_2_project_finance_spec.md`. The two methodological gaps surfaced in [[Indonesia Dashboard Methodology Review]] §v4.2 gaps are integrated as §4.6 (CBAM trajectory at COD year, not analysis year) and §4.7 (tariff escalation defaulting to flat real terms, not 3%/y, given the 2017 PLN tariff freeze). The spec preserves the original §1–§14 structure; refinements appear inline with **(Refined)** markers and as new subsections.

**IEA terminology (Refined — inherited from v4.1).** v4.2 reads from v4.1 refined's IEA-aligned column schema (LCOE / LCOS / Full System LCOE), per `dashboard/refinement/v4_1_foundation_spec.md` §2.6. Throughout this spec, references to "tariff" and "incumbent" use IEA-aligned column names: `lcoe_generation_usd_per_mwh` (LCOE base — Refined 2026-05-07: explicit name, not bare `lcoe_usd_per_mwh` which retains v4.0 delivered semantics for one deprecation release), `full_system_lcoe_delivered_usd_per_mwh` (Full System LCOE delivered), `full_system_lcoe_firm_4h_usd_per_mwh` / `full_system_lcoe_firm_8h_usd_per_mwh` (Full System LCOE firmed). Tariff inputs to the project-finance cash-flow projection (§4.1) accept any of these as the offtake-price source via the `tariff_source_label` user toggle. v4.2 introduces no new LCOE column-name conventions beyond what v4.1 establishes.

**Effort:** ~7–11 focused work days (up from baseline 7–10 by ~1 day for the COD-year + flat-tariff additions). Roughly 2–3 calendar weeks.

**Status:** Ready for implementation after v4.1 ships, supersedes baseline `v4_2_project_finance_spec.md`.

**Depends on:** v4.1 Foundation Refactor must be complete and shipped (refined version).

---

## What This Release Addresses

v4.2 transforms the dashboard from "cost comparison tool" to "investment decision support tool" by adding the project finance metrics that investment committees actually use (Pak Faiz's feedback on v4.0). This refined version integrates 2 methodological gaps surfaced by [[Indonesia Dashboard Methodology Review]] §v4.2 gaps and inherits v4.1's IEA-aligned column schema. Changes group into 4 themes. Links jump to the detailed section covering methodology, rationale, schema, implementation, and validation.

### 1. Project finance metrics (3 phases) — the headline content

*NPV, IRR, DSCR, LLCR, payback, equity IRR, sensitivity. Tariff source toggleable across v4.1 incumbents.*

| Section | What's changing | Why |
|---|---|---|
| [Phase 1 — Indicative project returns (§4)](#4-phase-1-indicative-project-returns) | NPV at user discount rate, project IRR, equity IRR, profitability index, simple payback, discounted payback, annual cash-flow projection with calendar_year column | Pak Faiz feedback: "the dashboard outputs LCOE but not project finance metrics that investment committees actually use." LCOE alone doesn't speak the investment language; transforms tool from cost-comparison to investment-decision-support. |
| [Phase 2 — Lender metrics (§5)](#5-phase-2-lender-metrics) | Debt amortization schedule, DSCR (year-by-year, min, avg), LLCR, DER | Lender covenants gate every Indonesian solar IPP. DSCR < 1.30 is a deal-breaker; LLCR / DER frame the debt structure. Without these, the tool stays in screening but doesn't connect to financing. |
| [Phase 3 — Sensitivity and scenarios (§6, optional)](#6-optional-sensitivity-and-scenarios) | Tornado charts (with tariff scenario + COD year as variables), PF vs corporate finance toggle, scenario combinations | Point estimates are misleading; investors want to see "what flips this site." Sensitivity charts answer that with one visualization. |

### 2. Tariff & CBAM refinements — 2 changes

*CBAM phase-in respects site-specific COD year (matters for project-finance NPV); tariff escalation defaults to flat real terms (PLN tariff frozen since 2017).*

| Section | What's changing | Why |
|---|---|---|
| [§4.6 CBAM trajectory at site-specific COD year](#46-refined-cbam-trajectory-at-site-specific-cod-year) | CBAM rate looked up at `calendar_year` for each project year, starting at COD not analysis year | Projects deciding today have 2-yr (solar) or 5–8-yr (geothermal) lead times. By COD, early CBAM low-rate years (2026 2.5%, 2027 5%) are gone. Baseline mis-applies year-1-of-analysis CBAM, biasing project-finance NPV by 25–30% for late-COD projects. |
| [§4.7 Flat real tariff default + reform toggle](#47-refined-flat-real-tariff-default--reform-toggle) | `flat_real` default + `partial_reform` (1.5%/y) and `full_indexation` (3%/y) toggles | PLN's I-4 industrial tariff has been frozen since May 2017. 3%/y indexing biases NPV upward 30–40% over 25-yr horizons — exactly the optimism that costs credibility with investment committees. **Cirata benchmark match: ±1pp under flat_real default; +3–4pp mismatch under v4.2 baseline 3%/y default.** |

### 3. Frontend & credibility framing — 4 changes

*"Indicative" framing on every metric. Mandatory tooltips, standardized assumptions table, no fake precision, ranges where feasible.*

| Section | What's changing | Why |
|---|---|---|
| [§8 Frontend integration](#8-frontend-integration) | New Score Drawer tab "Project Economics (Indicative)" with COD slider, tariff scenario toggle, cash-flow visualization, debt amortization view, CBAM-trajectory-vs-COD overlay | Project finance metrics need a UI that supports the analyst workflow (toggle assumptions, see ranking shifts). Without it, the data layer is invisible. |
| [§10 Credibility and framing guardrails](#10-credibility-and-framing-guardrails) | "Indicative" adjective everywhere, mandatory tooltips, standardized assumptions transparency (incl. PLN tariff freeze history + CBAM phase-in citations), no fake precision | Tool is screening-level, not due-diligence-level. Without explicit framing, an analyst pasting the IRR into an investment memo creates false precision that costs credibility on the first miss. |
| [§2 Positioning: screening vs due diligence](#2-positioning-screening-vs-due-diligence) | "What This Is Not" methodology section explicitly bounds the tool to Stage 1 universe screening | Project finance advisors at real banks spend 4–6 weeks per project on Stage 3 due diligence; the dashboard cannot compete and shouldn't try. Explicit bounding is what makes Stage 1 screening credible. |
| [§11 Validation strategy with Cirata benchmark](#11-validation-strategy) | Cirata Floating PV (CAPEX $145M, tariff $58.20/MWh, expected IRR 8–10%) as benchmark | The only Indonesian solar IPP with disclosed financials. If dashboard output mismatches Cirata, the rest of the rankings are suspect. Refined defaults match within ±1pp; baseline mismatched by ~3–4pp. |

### 4. Parallel data enrichment — 5 datasets

*Non-blocking data work that runs alongside Phase 1–2 code.*

| Section | What's changing | Why |
|---|---|---|
| [§7 Parallel data work](#7-parallel-data-work) | TKBI taxonomy (Green/Amber/Red), fiscal incentives (KEK Law 39/2009, GR 78/2019, GR 50/2023), regulatory context per sector, BPS provincial GDP, PLN tariff freeze history note | Lifts persona coverage for Policy Maker and DFI Investor without delaying core release. Each dataset answers a specific user question (TKBI green-eligibility, fiscal incentives applicable, sector regulations, regional growth context). |
| [§8.6 Other panel additions](#86-other-panel-additions-parallel-work) | TKBI badge in scorecard, fiscal incentives panel (collapsed by default), regulatory context panel per sector, provincial GDP context | UI surfacing for the parallel data so it's visible per-site, not buried in tables. |

> **IEA terminology inheritance.** v4.2 reads from v4.1 refined's IEA-aligned column schema (LCOE / LCOS / Full System LCOE). Tariff inputs to the cash-flow projection accept any of `lcoe_generation_usd_per_mwh`, `full_system_lcoe_delivered_*`, or `full_system_lcoe_firm_*` as the offtake-price source via `tariff_source_label`. v4.2 introduces no new LCOE column-name conventions.

---

## Table of Contents

| § | Section | Skip for Claude Code? |
|---|---|---|
| 1 | Strategic Context | Yes (reference) |
| 2 | Positioning: Screening vs Due Diligence | **No (UI text)** |
| 3 | Tier Structure (Phase 1 vs Phase 2 of v4.2) | Yes (planning) |
| 4 | Phase 1: Indicative Project Returns | **No (build)** |
|   | 4.1 Required inputs | **No (build)** |
|   | 4.2 Cash flow projection logic | **No (build)** |
|   | 4.3 Metric calculations | **No (build)** |
|   | 4.4 Tariff assumption: which incumbent? | **No (build)** |
|   | 4.5 Module structure | **No (build)** |
|   | 4.6 (Refined) CBAM trajectory at site-specific COD year | **No (build)** |
|   | 4.7 (Refined) Flat real tariff default + reform toggle | **No (build)** |
| 5 | Phase 2: Lender Metrics | **No (build)** |
| 6 | Optional: Sensitivity and Scenarios | **No (build if time)** |
| 7 | Parallel Data Work | **No (build)** |
| 8 | Frontend Integration | **No (build)** |
| 9 | Output Schema (fct_site_scorecard.csv changes) | **No (build)** |
| 10 | Credibility and Framing Guardrails | **No (UI text)** |
| 11 | Validation Strategy | **No (test cases)** |
| 12 | To-Do List | **No (tasks)** |
| 13 | Success Criteria | **No (definition of done)** |
| 14 | Relationship to Other Releases | Yes (calendar) |

---

## 1. Strategic Context

Pak Faiz (former CSO, Medco) reviewed v4.0 and identified that the dashboard outputs LCOE (engineering-economic metric) but not project finance metrics that investment committees actually use. His strongest single suggestion: add IRR, NPV, DSCR, PI.

This release transforms the dashboard from "cost comparison tool" to "investment decision support tool." Pak Faiz framed the two primary use cases as:
- Policy-making aids (Government)
- Investment strategy support (Companies — private and state-owned)

For the second use case, project finance metrics are the language. LCOE alone doesn't speak it.

The v4.1 foundation gives us multi-tier LCOE, multi-incumbent references, and destination-weighted CBAM. v4.2 builds the project finance calculations on top.

**Refinement context:** Two methodological gaps in the v4.2 baseline surfaced in [[Indonesia Dashboard Methodology Review]]:
- The CBAM trajectory phases in 2026 → 2034 for everyone, but for projects with 2-year (solar) or 5–8-year (geothermal) lead times, the early-low-rate years are gone by COD. The trajectory should start at site-specific COD year.
- The tariff escalation defaults to 3%/y inflation, but PLN's I-4 industrial tariff has been frozen since May 2017. Default should be flat real terms, with an explicit "tariff reform" toggle.

Both are integrated below.

---

## 2. Positioning: Screening vs Due Diligence

### 2.1 The framing decision

Real project finance for a specific Indonesian solar project requires data this tool does not have:
- Negotiated PPA tariff with escalation clauses
- Detailed debt term sheets including covenants
- EPC contract terms, construction schedule
- Land lease specifics
- Tax structuring details
- Site-specific technical diligence

A project finance advisor at a real bank spends 4–6 weeks of analyst time on this for a single project. The dashboard cannot compete with that and shouldn't try.

**This tool lives in screening, not due diligence:**

| Stage | What it does | Who does it | Data required |
|---|---|---|---|
| Stage 1: Universe screening | Rank sites across investment universe | Analysts, policy planners | Public data, standardized assumptions |
| Stage 2: Shortlist evaluation | Evaluate top 20 candidates | Investment teams | Public + some private data |
| Stage 3: Project due diligence | Build detailed financial model | Advisory firms with NDA access | Negotiated PPA, EPC contracts, etc. |

**This tool lives entirely in Stage 1.** Frame everything accordingly.

### 2.2 The "Indicative" framing

Every metric uses "Indicative" as adjective:
- "Indicative IRR: 13.8%"
- "Indicative DSCR: 1.42"
- "Indicative Payback: 8.2 years"

This single word changes user expectation from "precise" to "approximate."

### 2.3 Mandatory disclaimer text

Every project finance output carries this text in tooltip or footer:

> Based on standardized project finance assumptions. Actual project-specific analysis requires negotiated PPA terms, detailed EPC contracts, and site-specific diligence.

### 2.4 "What This Is Not" methodology section

Dedicated section in methodology doc:

> This tool provides screening-level project economics using standardized industry assumptions. It does not substitute for project-specific financial modeling, which requires:
> 
> - Negotiated PPA tariff with specific escalation and indexing
> - Detailed debt term sheets including covenants and reserves
> - EPC contract terms, construction schedule, warranties
> - Site-specific captive plant cost data including coal contracts
> - Hourly dispatch modeling for storage sizing
> - Land lease specifics and escalation
> - Insurance, tax structuring, decommissioning provisions
>
> Indicative metrics from this tool should be used for comparative site screening, not investment committee decisions. Actual project evaluation requires advisory firms with NDA access to deal documents.

---

## 3. Tier Structure (Phase 1 vs Phase 2 of v4.2)

To ship visible value quickly and de-risk the implementation, v4.2 ships in two phases:

### Phase 1 (~3–5 days, ships as v4.2-alpha or directly to v4.2)

**Indicative Project Returns** — the headline metrics any investment analyst would expect:
- NPV at user-specified discount rate
- Project IRR
- Equity IRR
- Profitability Index
- Simple Payback
- Discounted Payback
- Annual cash flow projection table

These have clean math. numpy/scipy provide the financial functions. Validation against Cirata benchmark is straightforward.

**Phase 1 refinements (Refined — pulled from v4.2 baseline):**
- COD-year-aware CBAM trajectory (§4.6)
- Flat real tariff default with reform toggle (§4.7)

### Phase 2 (~3–4 days)

**Lender Metrics** — adds debt structure:
- Debt amortization schedule
- DSCR (year-by-year, min, average)
- LLCR (Loan Life Coverage Ratio)
- DER (Debt/Equity Ratio)

Requires modeling debt amortization. Slightly more complex but mechanically simple.

### Phase 3 (optional, ~2–3 days if time allows)

**Sensitivity and Scenarios:**
- Tornado chart showing IRR sensitivity to tariff, CAPEX, CF, WACC
- PF vs corporate finance toggle
- Sensitivity to scenario combinations

Can defer to v4.2.5 patch if v4.3 work is more pressing.

---

## 4. Phase 1: Indicative Project Returns

### 4.1 Required inputs

All of these come from v4.1 (already computed) or have v4.1 defaults:

**From v4.1 cost framework:**
- `capex_total_usd` (from existing scorecard)
- `opex_annual_usd` (from existing scorecard)
- `annual_energy_mwh` (from capacity × CF × 8760)
- One of `incumbent_pln_bpp` / `incumbent_industrial_tariff` / `incumbent_captive` as tariff assumption (user-selectable)

**Project finance defaults (new in v4.2):**
- `lifetime_years`: 25 (default; from existing methodology)
- `degradation_rate`: 0.005 (0.5%/year; solar warranty standard)
- `tax_rate`: 0.22 (Indonesian corporate tax)
- `discount_rate`: from existing WACC slider
- `inflation_rate_opex`: 0.03 (Refined — applied to OPEX only, not tariff; see §4.7)
- `tariff_escalation_rate`: 0.0 default (Refined — see §4.7)
- `construction_years`: 2 (typical utility solar)
- `cod_year`: analysis_year + construction_years (Refined — see §4.6)

### 4.2 Cash flow projection logic

```python
def compute_cash_flow_projection(
    capex_total_usd: float,
    opex_annual_usd: float,
    annual_energy_mwh: float,
    tariff_usd_per_mwh: float,
    cod_year: int,                            # Refined — explicit COD year
    cbam_trajectory: dict,                    # Refined — {year: $/MWh adder}
    cbam_exposed: bool,                       # Refined — whether to apply CBAM trajectory
    lifetime_years: int = 25,
    degradation_rate: float = 0.005,
    tax_rate: float = 0.22,
    inflation_rate_opex: float = 0.03,        # Refined — split OPEX vs tariff
    tariff_escalation_rate: float = 0.0,      # Refined — flat real default
    construction_years: int = 2,
) -> list[dict]:
    """
    Build year-by-year cash flow projection.
    
    Returns list of dicts with year, calendar_year, revenue, opex, depreciation, 
    cbam_adder (if applicable), taxable_income, tax, net_cash_flow.
    """
    cash_flows = []
    
    # Year 0: capex investment (negative)
    cash_flows.append({
        'year': 0,
        'calendar_year': cod_year - construction_years,  # Refined — capex starts pre-COD
        'capex': -capex_total_usd,
        'revenue': 0,
        'opex': 0,
        'depreciation': 0,
        'cbam_adder': 0,
        'taxable_income': 0,
        'tax': 0,
        'net_cash_flow': -capex_total_usd,
    })
    
    # Linear depreciation over lifetime
    annual_depreciation = capex_total_usd / lifetime_years
    
    # Years 1 to lifetime (operations)
    for year in range(1, lifetime_years + 1):
        calendar_year = cod_year + year - 1   # Refined — explicit calendar mapping
        
        # Energy degrades over time
        energy_t = annual_energy_mwh * (1 - degradation_rate) ** (year - 1)
        
        # Tariff escalation (Refined — default flat real)
        tariff_t = tariff_usd_per_mwh * (1 + tariff_escalation_rate) ** (year - 1)
        revenue_t = energy_t * tariff_t
        
        # OPEX grows with inflation (separate from tariff escalation)
        opex_t = opex_annual_usd * (1 + inflation_rate_opex) ** (year - 1)
        
        # CBAM adder (Refined — at calendar year, not analysis year 1)
        cbam_t = cbam_trajectory.get(calendar_year, 0) * energy_t if cbam_exposed else 0
        
        # Taxable income (revenue - opex - depreciation - cbam)
        taxable_t = revenue_t - opex_t - annual_depreciation - cbam_t
        tax_t = max(0, taxable_t * tax_rate)
        
        # Net cash flow
        net_t = revenue_t - opex_t - cbam_t - tax_t
        
        cash_flows.append({
            'year': year,
            'calendar_year': calendar_year,
            'capex': 0,
            'revenue': revenue_t,
            'opex': opex_t,
            'depreciation': annual_depreciation,
            'cbam_adder': cbam_t,
            'taxable_income': taxable_t,
            'tax': tax_t,
            'net_cash_flow': net_t,
        })
    
    return cash_flows
```

### 4.3 Metric calculations

```python
import numpy_financial as npf

def compute_indicative_metrics(
    cash_flows: list[dict],
    discount_rate: float,
) -> dict:
    """
    Compute NPV, IRR, PI, payback from cash flow projection.
    """
    # Extract net cash flow series
    cf_series = [cf['net_cash_flow'] for cf in cash_flows]
    
    # NPV at user-specified discount rate
    npv = npf.npv(discount_rate, cf_series)
    
    # Project IRR
    try:
        irr = npf.irr(cf_series)
    except:
        irr = None
    
    # Profitability Index
    initial_investment = -cf_series[0]
    pi = (npv + initial_investment) / initial_investment if initial_investment > 0 else None
    
    # Simple payback (cumulative cash flow first reaches zero)
    cumulative = 0
    simple_payback = None
    for i, cf in enumerate(cf_series):
        cumulative += cf
        if cumulative >= 0 and simple_payback is None:
            simple_payback = i  # year reached
    
    # Discounted payback
    cumulative_disc = 0
    disc_payback = None
    for i, cf in enumerate(cf_series):
        cumulative_disc += cf / (1 + discount_rate) ** i
        if cumulative_disc >= 0 and disc_payback is None:
            disc_payback = i
    
    return {
        'npv_usd': npv,
        'project_irr_pct': irr * 100 if irr else None,
        'profitability_index': pi,
        'simple_payback_years': simple_payback,
        'discounted_payback_years': disc_payback,
    }
```

### 4.4 Tariff assumption: which incumbent?

The tariff assumption is the single biggest IRR driver. Default to context-appropriate incumbent:

```python
def get_default_tariff(site_classification: dict, incumbents: dict) -> tuple[float, str]:
    """
    Pick default tariff based on site arrangement.
    Returns (tariff_value, tariff_source_label).
    """
    arrangement = site_classification['electricity_arrangement']
    
    if arrangement == 'pure_captive':
        # Use captive cost (this is what they'd avoid by going solar)
        return incumbents['captive'], 'captive_displacement'
    elif arrangement == 'grid_only':
        # Use industrial tariff (behind-the-meter scenario)
        return incumbents['industrial_tariff'], 'industrial_tariff_displacement'
    else:
        # Hybrid case — use BPP (PLN procurement scenario)
        return incumbents['pln_bpp'], 'pln_procurement'
```

User can override via UI to explore other scenarios.

### 4.5 Module structure

Create `src/model/project_finance.py`:

```python
"""
Project finance metric calculations.

NOTE: These are INDICATIVE screening metrics based on standardized
assumptions. Not suitable for project-specific due diligence.
"""

def compute_cash_flow_projection(...) -> list[dict]: ...
def compute_indicative_metrics(...) -> dict: ...
def get_default_tariff(...) -> tuple[float, str]: ...
def derive_cbam_trajectory_from_cod(...) -> dict: ...   # Refined — see §4.6

# Wrapper for full per-site calculation
def compute_site_project_finance(
    site_id: str,
    site_data: dict,           # from scorecard
    classifications: dict,     # from fct_site_classifications
    incumbents: dict,          # from v4.1 cost framework
    user_inputs: dict = None,  # for tariff overrides, COD year, escalation
) -> dict:
    """
    Full project finance calculation for one site.
    Returns dict with all metrics, cash flow table, and metadata.
    """
    ...
```

### 4.6 (Refined) CBAM trajectory at site-specific COD year

**Why this matters.** The CBAM trajectory in METHODOLOGY_CONSOLIDATED §14.4 phases in 2026 → 2034 for everyone:

| Year | Free Allocation (%) | Effective CBAM Rate (%) |
|---|---|---|
| 2026 | 97.5% | 2.5% |
| 2027 | 95.0% | 5.0% |
| 2028 | 90.0% | 10.0% |
| 2029 | 77.5% | 22.5% |
| 2030 | 51.5% | 48.5% |
| 2031 | 39.0% | 61.0% |
| 2032 | 26.5% | 73.5% |
| 2033 | 14.0% | 86.0% |
| 2034 | 0.0% | 100.0% |

For a project deciding today (2026 analysis year) with 2-year solar lead time, COD is 2028 — already inside CBAM's exposure window but missing the 2026 (2.5%) and 2027 (5%) low-rate years. For geothermal projects with 5–8-year permitting + drilling, COD is 2031–2034 — entering CBAM at 61–100% rate, with all the ramp-up years gone.

Currently the cash-flow projection iterates `year 1 to lifetime` and applies the CBAM trajectory starting at `year 1` regardless of when the project comes online. Wrong for project-finance NPV.

**Methodology change.** Pass `cod_year` explicitly into the cash-flow projection. CBAM phase-in starts at `cod_year`, not at year 1 of analysis. The cash-flow projection's `calendar_year` mapping in §4.2 makes this explicit; the CBAM lookup uses `calendar_year` directly:

```python
def derive_cbam_trajectory_from_cod(
    cod_year: int,
    lifetime_years: int,
    cbam_phase_in: dict,   # {2026: 0.025, 2027: 0.05, ..., 2034: 1.0}
    cbam_full_rate_year: int = 2034,
    full_rate_extension: bool = True,  # post-2034 stays at 100% (user-toggleable)
) -> dict:
    """
    Build per-calendar-year CBAM rate trajectory aligned to project COD.
    
    Returns {calendar_year: cbam_rate_fraction} for each year of project operation.
    For years before 2026: rate = 0 (CBAM not yet in force).
    For years 2026 - cbam_full_rate_year: lookup from cbam_phase_in.
    For years after cbam_full_rate_year: 1.0 (full rate, unless toggled off).
    """
    trajectory = {}
    for year in range(cod_year, cod_year + lifetime_years):
        if year < 2026:
            trajectory[year] = 0.0
        elif year <= cbam_full_rate_year:
            trajectory[year] = cbam_phase_in.get(year, 0)
        else:
            trajectory[year] = 1.0 if full_rate_extension else 0  # default keeps full rate
    return trajectory


def compute_cbam_adder_per_mwh_at_year(
    emissions_intensity_tco2_per_mwh,
    cbam_rate_fraction,
    effective_carbon_price_at_year,  # destination-weighted from v4.1 §7
):
    """
    CBAM adder for a specific calendar year, applied to project cash flow.
    """
    return emissions_intensity_tco2_per_mwh * cbam_rate_fraction * effective_carbon_price_at_year
```

This integrates with v4.1's destination-weighted carbon stack: the trajectory's `cbam_rate_fraction` multiplies the destination-weighted price, which itself varies by calendar year (per `dim_carbon_price_by_market.csv`).

**User control.** v4.2 UI exposes:
- `cod_year` slider (default = analysis_year + construction_years; range 2025–2035)
- `cbam_post_2034_rate` toggle (default 100%, alternative: 100% with EU-only premium escalation per IEA APS)

**Validation.** Solar IPP at COD 2028, lifetime 25 years, CBAM-exposed nickel: cash-flow CBAM adder is 0 in operation-years 1–2 (2028 falls in CBAM 2028 = 10% rate), rises through years 3–7 (covering 2029–2034 phase-in), saturates at 100% from 2034 onward. Total CBAM cost over project life ~25–30% lower than if computed with year-1-of-analysis = 2026 framing.

For a geothermal project at COD 2032, the trajectory enters at year 1 = 2032 (CBAM 73.5%); the early-low-rate years are entirely missed.

### 4.7 (Refined) Flat real tariff default + reform toggle

**Why this matters.** v4.2 baseline §4.1 default `inflation_rate = 0.03` is applied to OPEX *and* (implicitly via tariff_t in the original cash-flow projection) to revenue. PLN's I-4 industrial tariff has been frozen since May 2017 (per RUPTL Bab VI). The regulatory reality is that tariff escalation is politically constrained, not inflation-indexed.

For long-horizon NPV, defaulting to 3%/y tariff growth biases project-finance NPV upward — particularly for sites whose offtake is the I-4 tariff (grid-connected industrial). For investment-committee-grade screening, this is exactly the kind of optimism that costs credibility.

**Methodology change.** Two changes to the cash-flow projection:

1. **Split inflation into OPEX-only and tariff-only rates** (§4.2 above):
   ```python
   inflation_rate_opex: float = 0.03,        # OPEX grows with general inflation
   tariff_escalation_rate: float = 0.0,      # Default flat real terms
   ```

2. **Add a "tariff reform" scenario toggle.** v4.2 UI exposes three tariff scenarios:
   - `flat_real` (default): tariff stays at v4.1 incumbent value in real terms throughout project life. Reflects the 9-year I-4 freeze (2017–2026).
   - `partial_reform`: tariff grows at 1.5%/y (half of CPI). Reflects a partial-recovery scenario where political constraint loosens but tariff doesn't fully index.
   - `full_indexation`: tariff grows at `inflation_rate_opex` (3%/y default). Reflects full inflation indexing — historically not the Indonesian pattern but standard project-finance assumption elsewhere.

```python
TARIFF_ESCALATION_SCENARIOS = {
    'flat_real': 0.0,
    'partial_reform': 0.015,
    'full_indexation': 0.03,
}
```

**Per-site default selection.** Sites whose tariff source is `incumbent_pln_bpp` or `incumbent_industrial_tariff` default to `flat_real` (PLN-controlled tariffs that have been frozen). Sites whose tariff source is `incumbent_captive_*` default to `partial_reform` (captive plants escalate fuel costs partially with markets but absorb some). Sites whose tariff source is the captive coal LCOE displacement specifically default to `flat_real` (coal cost is bounded by domestic price ceiling under PR 112/2022).

**Validation impact.** A 25-year solar IPP using `incumbent_industrial_tariff = $63.08/MWh` (the I-4 rate from v4.0 baseline):
- v4.2 baseline (3%/y escalation): year-25 tariff = $63.08 × 1.03^24 = $128/MWh. NPV bias ~30–40% upward.
- v4.2 refined `flat_real` (default): year-25 tariff = $63.08/MWh constant. Realistic for PLN tariff history.
- v4.2 refined `partial_reform`: year-25 tariff = $63.08 × 1.015^24 = $90/MWh. Mid-trajectory.

Document the choice in tooltip: "Tariff scenario: flat real (PLN tariff frozen since 2017). Toggle reform scenarios to see NPV under tariff-indexation alternatives."

**Sites to spot-check.**
- Krakatau Steel Cilegon (industrial tariff offtake): default `flat_real`. NPV vs baseline 3% should drop materially (~25–35%).
- IMIP Morowali (captive coal displacement): default `flat_real`. NPV similar to baseline (captive coal cost barely escalates).
- Cirata benchmark validation: PT PJB published Cirata IRR is 8–10% under realistic PPA. v4.2 baseline at 3%/y produces ~13–14% IRR, which mismatches. v4.2 refined at `flat_real` produces ~9–10% IRR, matching the public benchmark.

This refinement also improves the Cirata benchmark validation in §11.2.

---

## 5. Phase 2: Lender Metrics

### 5.1 Additional inputs

Beyond Phase 1 inputs, lender metrics need:

```python
debt_share: float = 0.70           # Project finance typical
debt_tenor_years: int = 15         # Match to project economics
debt_interest_rate: float = 0.085  # Current Indonesian IPP market rate
```

These should be exposed as user-adjustable parameters in the UI, with defaults representing current Indonesian solar IPP project finance practice.

### 5.2 Debt amortization schedule

```python
def compute_debt_amortization(
    principal: float,
    rate: float,
    tenor_years: int,
) -> list[dict]:
    """
    Equal annual debt service payments (typical project finance).
    
    Returns year-by-year schedule with interest, principal, total DS,
    and outstanding balance.
    """
    annual_payment = principal * (
        rate * (1 + rate) ** tenor_years
    ) / ((1 + rate) ** tenor_years - 1)
    
    schedule = []
    outstanding = principal
    for year in range(1, tenor_years + 1):
        interest = outstanding * rate
        principal_payment = annual_payment - interest
        outstanding_end = outstanding - principal_payment
        
        schedule.append({
            'year': year,
            'interest': interest,
            'principal': principal_payment,
            'total_ds': annual_payment,
            'outstanding_start': outstanding,
            'outstanding_end': outstanding_end,
        })
        outstanding = outstanding_end
    
    return schedule
```

### 5.3 DSCR computation

```python
def compute_dscr_schedule(
    cash_flows: list[dict],     # from Phase 1
    debt_schedule: list[dict],  # from above
) -> list[dict]:
    """
    Year-by-year DSCR.
    
    DSCR = EBITDA / Debt Service
    EBITDA approximated as net_cash_flow + tax + depreciation
    """
    dscr_by_year = []
    
    for year_idx, cf in enumerate(cash_flows[1:], start=1):  # skip year 0
        # Find matching debt service year
        ds_entry = next(
            (d for d in debt_schedule if d['year'] == year_idx),
            None,
        )
        
        if ds_entry is None:
            # Past loan tenor; DSCR not meaningful
            dscr = float('inf')
        else:
            # EBITDA = net CF + tax + depreciation (approximate)
            ebitda = cf['net_cash_flow'] + cf['tax'] + cf['depreciation']
            dscr = ebitda / ds_entry['total_ds'] if ds_entry['total_ds'] > 0 else float('inf')
        
        dscr_by_year.append({
            'year': year_idx,
            'dscr': dscr,
        })
    
    return dscr_by_year
```

### 5.4 LLCR

```python
def compute_llcr(
    cash_flows: list[dict],
    debt_schedule: list[dict],
    discount_rate: float,
) -> float:
    """
    Loan Life Coverage Ratio.
    LLCR = NPV(EBITDA during loan life) / Debt outstanding at start
    """
    loan_tenor = max(d['year'] for d in debt_schedule)
    
    # EBITDA series during loan life
    ebitda_during_loan = []
    for year in range(1, loan_tenor + 1):
        cf = next((c for c in cash_flows if c['year'] == year), None)
        if cf:
            ebitda = cf['net_cash_flow'] + cf['tax'] + cf['depreciation']
            ebitda_during_loan.append(ebitda)
    
    npv_ebitda = npf.npv(discount_rate, [0] + ebitda_during_loan)
    debt_outstanding = debt_schedule[0]['outstanding_start']
    
    return npv_ebitda / debt_outstanding if debt_outstanding > 0 else None
```

### 5.5 Equity IRR

After Phase 2 lands, distinguish project IRR from equity IRR:

```python
def compute_equity_irr(
    cash_flows: list[dict],
    debt_schedule: list[dict],
    debt_share: float,
    capex_total: float,
) -> float:
    """
    Equity IRR uses equity-only cash flows after debt service.
    """
    equity_investment = capex_total * (1 - debt_share)
    
    equity_cash_flows = [-equity_investment]
    
    for year_idx, cf in enumerate(cash_flows[1:], start=1):
        ds = next(
            (d for d in debt_schedule if d['year'] == year_idx),
            None,
        )
        ds_total = ds['total_ds'] if ds else 0
        equity_cf = cf['net_cash_flow'] - ds_total
        equity_cash_flows.append(equity_cf)
    
    try:
        return npf.irr(equity_cash_flows)
    except:
        return None
```

### 5.6 Aggregation

Add to the per-site calculation:

```python
def compute_site_project_finance(...) -> dict:
    # Phase 1 calculations (already implemented, with COD-year and flat-tariff refinements)
    cash_flows = compute_cash_flow_projection(
        ...,
        cod_year=cod_year,
        cbam_trajectory=derive_cbam_trajectory_from_cod(cod_year, lifetime, cbam_phase_in),
        cbam_exposed=site_data['cbam_exposed'],
        tariff_escalation_rate=TARIFF_ESCALATION_SCENARIOS[tariff_scenario],
    )
    metrics_p1 = compute_indicative_metrics(cash_flows, discount_rate)
    
    # Phase 2 additions
    debt_schedule = compute_debt_amortization(
        principal=capex * debt_share,
        rate=interest_rate,
        tenor_years=debt_tenor,
    )
    dscr_schedule = compute_dscr_schedule(cash_flows, debt_schedule)
    
    dscr_values = [d['dscr'] for d in dscr_schedule if d['dscr'] != float('inf')]
    
    return {
        **metrics_p1,
        'equity_irr_pct': compute_equity_irr(...) * 100,
        'dscr_min': min(dscr_values) if dscr_values else None,
        'dscr_avg': sum(dscr_values) / len(dscr_values) if dscr_values else None,
        'llcr': compute_llcr(cash_flows, debt_schedule, discount_rate),
        'der': debt_share / (1 - debt_share),
        'debt_amortization_table': debt_schedule,
        'dscr_year_by_year': dscr_schedule,
        'cod_year': cod_year,                              # Refined — surfaced for transparency
        'tariff_scenario': tariff_scenario,                # Refined — surfaced for transparency
        'cbam_total_npv_usd': sum(...),                    # Refined — total CBAM cost over project life
    }
```

---

## 6. Optional: Sensitivity and Scenarios

If time allows, add Phase 3 features.

### 6.1 Tornado sensitivity chart

For each site, show how IRR changes with:
- Tariff ±20%
- Tariff escalation scenario (flat / partial / full) — Refined
- COD year (2025 / 2028 / 2031) — Refined
- CAPEX ±15%
- Capacity factor ±10%
- WACC ±2 percentage points
- OPEX ±20%

Visual: horizontal bar chart with variables ranked by IRR impact.

### 6.2 Project finance vs corporate finance toggle

```python
PROJECT_FINANCE_DEFAULTS = {
    'debt_share': 0.70,
    'debt_tenor_years': 15,
    'debt_interest_rate': 0.085,
    'primary_metric': 'dscr',
}

CORPORATE_FINANCE_DEFAULTS = {
    'debt_share': 0.50,
    'debt_tenor_years': 10,
    'debt_interest_rate': 0.075,  # corporate credit, slightly cheaper
    'primary_metric': 'der',
}
```

Toggle switches defaults and emphasizes different outputs.

### 6.3 Scenario combinations

Defer most of this to v4.3 multi-pathway analysis. v4.2 should focus on per-site metrics under default assumptions. v4.3 adds the cross-site, cross-pathway analytical layer.

---

## 7. Parallel Data Work

These tasks run in parallel with code work and don't require Claude Code:

### 7.1 TKBI green finance taxonomy tagging

**Effort:** 2–3 days
**Source:** Indonesia Sustainable Finance Taxonomy (TKBI) v2 document
**Deliverable:** Per-site classification as Green / Amber / Red
**Why:** Directly relevant to DFI investors evaluating green financing eligibility

### 7.2 Fiscal incentive panel data

**Effort:** 2–3 days
**Sources:**
- BKPM (Investment Coordinating Board) KEK schedules
- KEK Law (Law 39/2009 and amendments)
- GR 78/2019 (Tax Allowance)
- GR 50/2023 (Renewable Energy Tax Allowance)
**Deliverable:** Per-site display of applicable incentives in `data/raw/fiscal_incentives.csv`

### 7.3 Regulatory context panel content

**Effort:** 2 days
**Deliverable:** Per-sector display of applicable regulations (factual, not scored)
**Replaces Pak Faiz's "Policy Consistency Score" suggestion** with a more defensible factual approach

### 7.4 Regional GDP context

**Effort:** 0.5 day
**Source:** BPS provincial GDP data
**Deliverable:** Provincial GDP, growth rate, industrial share added to site context

### 7.5 (Refined) PLN tariff freeze history documentation

**Effort:** 0.5 day
**Source:** RUPTL Bab VI; ESDM Permen tariff regulations history
**Deliverable:** Concise note + table in METHODOLOGY_CONSOLIDATED §7.1 documenting the I-4 tariff history (frozen since May 2017) and the rationale for `flat_real` default

---

## 8. Frontend Integration

### 8.1 New Score Drawer tab: "Project Economics (Indicative)"

```
┌─ Project Economics (Indicative) ───────────────────────────────┐
│                                                                 │
│  ⚠ Screening-level estimates using standardized assumptions    │
│     [What this is not →]                                        │
│                                                                 │
│  Inputs:                                                        │
│   Tariff source:     [Captive displacement ▾]                   │
│   Tariff value:      $[45]/MWh                                  │
│   Tariff scenario:   [Flat real (default) ▾]    (Refined)     │
│   COD year:          [2028]    (Construction 2 yr)  (Refined)│
│   Discount rate:     [10.0]%   (Current WACC)                  │
│                                                                 │
│  Indicative Returns:                                            │
│   Simple Payback:    8.2 years                                  │
│   Discounted Payback: 11.5 years                                │
│   NPV @ 10%:         $14.2M                                     │
│   Project IRR:       9.8% (vs Cirata public 8–10%)             │
│   Equity IRR:        13.4%                                      │
│   Profitability Idx: 1.18                                       │
│                                                                 │
│  Lender Metrics (Phase 2):                                      │
│   Min DSCR:          1.42    ✓ above 1.30 covenant             │
│   Avg DSCR:          1.68                                       │
│   LLCR:              1.55                                       │
│   DER:               2.33                                       │
│                                                                 │
│  Debt structure:                                                │
│   Debt: [70]%   Tenor: [15]y   Rate: [8.5]%                    │
│                                                                 │
│  CBAM exposure (CBAM-exposed sites only):                       │
│   Total CBAM NPV:    $2.1M  (Refined)                           │
│   CBAM cost trajectory: 2028 (10%) → 2034 (100%)                │
│                                                                 │
│  [View 25-year cash flow projection]                            │
│  [View debt amortization schedule]                              │
│  [View CBAM trajectory aligned to COD]    (Refined)            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Cash flow visualization

When user clicks "View 25-year cash flow projection," show:
- Year-by-year table (calendar year, revenue, opex, CBAM adder, tax, net CF)
- Cumulative cash flow line chart with payback point highlighted
- (Refined) Calendar-year x-axis labels

### 8.3 Debt amortization view

When user clicks "View debt amortization schedule," show:
- Year-by-year table (interest, principal, balance)
- Stacked bar chart showing interest vs principal over time

### 8.4 (Refined) CBAM trajectory aligned to COD

When user clicks "View CBAM trajectory aligned to COD," show:
- Calendar-year x-axis from COD to COD+lifetime
- Y-axis: CBAM cost ($/MWh of generation)
- Annotation: which calendar years correspond to project years 1, 5, 10, 25
- Comparison line: "If COD were 2026" — overlays the trajectory if project came online at start of CBAM phase-in
- The delta between curves quantifies how much CBAM exposure is "missed" or "incurred" by the actual COD year

### 8.5 Tooltip integration

Every metric carries a hover tooltip with:
- Definition
- "Indicative" framing
- Source assumptions
- Citation reference

(Refined) Tariff tooltip: "Tariff scenario: flat real (default). Reflects PLN's I-4 industrial tariff frozen since May 2017. Toggle to partial_reform (1.5%/y) or full_indexation (3%/y) to test reform sensitivity."

(Refined) COD-year tooltip: "Project commercial operation date. CBAM exposure phases in from 2026 to 2034. Adjust COD to see how lead-time affects CBAM cost."

### 8.6 Other panel additions (parallel work)

- TKBI badge in scorecard (Green / Amber / Red)
- Fiscal incentives panel (collapsed by default)
- Regulatory context panel (per-sector)
- Provincial GDP context

These are smaller UI additions; design them cleanly without cluttering the main score view.

---

## 9. Output Schema (fct_site_scorecard.csv changes)

### 9.1 New fields added (Refined)

```
# Phase 1 metrics
indicative_npv_usd
indicative_project_irr_pct
indicative_equity_irr_pct
indicative_profitability_index
indicative_simple_payback_years
indicative_discounted_payback_years

# Phase 2 lender metrics
indicative_dscr_min
indicative_dscr_avg
indicative_llcr
indicative_der

# Assumptions used
tariff_assumption_used_usd_per_mwh
tariff_source_label                    # which incumbent was used
tariff_escalation_scenario             # Refined — flat_real / partial_reform / full_indexation
debt_assumption_share
debt_assumption_tenor_years
debt_assumption_interest_rate

# Refined — COD year and CBAM trajectory
cod_year                               # Refined — explicit COD year used
cbam_trajectory_first_year_rate_pct    # Refined — CBAM rate at project year 1 (varies by COD)
cbam_total_npv_usd                     # Refined — total NPV of CBAM cost over project life
cbam_post_2034_rate_assumption         # Refined — full / capped (user-toggleable)

# Provenance (per v4.1 standard)
indicative_metrics_source
indicative_metrics_vintage
indicative_metrics_confidence

# TKBI (parallel data work)
tkbi_classification                    # Green / Amber / Red
tkbi_classification_rationale
```

### 9.2 New separate tables

`fct_site_cashflow_projections.csv` — year-by-year cash flows per site (one row per site-year, with calendar_year column — Refined)
`fct_site_debt_schedules.csv` — year-by-year debt amortization per site

These are large but separable from the main scorecard. Generated on-demand or pre-computed during pipeline run.

---

## 10. Credibility and Framing Guardrails

### 10.1 "Indicative" everywhere

Every metric display includes "Indicative" as adjective. No exceptions. Code reviewers should flag any UI text that drops "Indicative" from a finance metric.

### 10.2 Mandatory tooltips

Every numeric field has a tooltip. The tooltip includes:
- Definition (e.g., "DSCR = EBITDA / Debt Service")
- Methodology note (e.g., "Computed using standardized 70/30 debt-equity, 15-year tenor, 8.5% interest")
- Disclaimer reference (e.g., "Indicative — see methodology")

### 10.3 Standardized assumptions transparency (Refined)

Methodology section lists every assumption with source:

| Assumption | Value | Source |
|---|---|---|
| Debt share | 70% | Typical Indonesian solar IPP project finance |
| Debt tenor | 15 years | Match to 25-year project economics |
| Interest rate | 8.5% | Current Indonesian IPP market |
| Construction period | 2 years | IRENA benchmark for utility solar |
| Degradation | 0.5%/year | Solar panel manufacturer warranty standard |
| OPEX | $15/kW-yr | NREL benchmark (for sites where not in scorecard) |
| Corporate tax | 22% | Indonesian tax law |
| DSCR reserve | 6 months | Typical lender covenant |
| OPEX inflation | 3.0%/yr | Indonesian historical CPI average |
| **Tariff escalation default** | **0.0%/yr (flat real)** | **Refined — RUPTL Bab VI documents I-4 frozen since May 2017** |
| **CBAM trajectory start** | **Site COD year, not analysis year** | **Refined — EU Reg 2023/956 phase-in 2026 → 2034** |

### 10.4 No fake precision

Round appropriately:
- IRR: to 0.1% (not 0.01%)
- NPV: to nearest $0.1M (not nearest dollar)
- DSCR: to 0.01 (not 0.001)
- Payback: to 0.1 year

### 10.5 Show ranges where feasible

For top-line metrics, show ranges:
- "Indicative IRR: 9–11%" rather than "Indicative IRR: 9.8%"
- "Indicative IRR (flat real): 9.8% / (partial reform): 11.4% / (full indexation): 13.5%" — Refined, three scenarios when relevant

Implementation: compute IRR at flat_real / partial_reform / full_indexation and show all three in the UI when the user views a site-level scorecard.

---

## 11. Validation Strategy

### 11.1 Unit tests

Standard tests for each financial function:
- NPV with simple cases (constant cash flow, zero growth)
- IRR convergence on standard examples
- Payback calculation edge cases
- Debt amortization correctness vs Excel-computed reference values
- (Refined) CBAM trajectory derivation: COD 2028 → first-year rate 10%; COD 2026 → first-year rate 2.5%; COD 2032 → first-year rate 73.5%
- (Refined) Tariff escalation scenarios: year-25 tariff under flat_real = year-1; under partial_reform = year-1 × 1.015^24; under full_indexation = year-1 × 1.03^24

### 11.2 Cirata Floating PV benchmark (Refined — improves the benchmark match)

Cirata is the largest published Indonesian solar IPP with disclosed economics:
- CAPEX: $145M
- Capacity: 192 MWp
- PPA tariff: $5.82 cents/kWh ($58.20/MWh)
- Financing: ~70% ADB debt
- Expected IRR range from public analysis: 8–10%

**Validation.** Feed Cirata inputs into v4.2 calculation under v4.2 refined defaults (flat_real tariff). Expect output IRR in 8–11% range.

**v4.2 baseline (3%/y escalation):** would produce ~13–14% IRR — mismatches the public benchmark.
**v4.2 refined (flat_real default):** produces ~9–10% IRR — matches the public benchmark.

The refinement directly improves the benchmark validation. Document this in the validation log: *"v4.2 refined `flat_real` default produces IRR within ±1pp of Cirata public range; v4.2 baseline default biases ~3–4pp upward, attributable to inflation-indexed tariff growth that does not reflect Indonesian regulatory reality."*

Possible causes if mismatch persists:
- Capacity factor difference (expected ~16% for floating PV, vs default utility-scale ~17–19%)
- Tax holiday treatment (Cirata may have specific incentives)
- Construction period
- ADB concessional debt interest rate (lower than $0.085/y default)

### 11.3 Sanity checks

For every site:
- Cash flow profile passes "reasonable" eye test (revenue flat-ish with degradation, OPEX growing slowly, tax appearing after depreciation runs out, CBAM adder rising over time for CBAM-exposed sites)
- IRR > 0 if NPV > 0
- DSCR > 0 in operating years
- Equity IRR > Project IRR (because of leverage)
- Payback period > construction period
- (Refined) `cbam_trajectory_first_year_rate_pct = cbam_phase_in[cod_year]` for CBAM-exposed sites
- (Refined) Year-1 revenue under `flat_real` = year-25 revenue × (1 - degradation)^24 (no escalation, only degradation)

### 11.4 Pak Faiz feedback loop

After Phase 1 ships:
- Email Pak Faiz with implementation summary
- Show him the methodology and one or two screenshots
- Ask: "For screening-level analysis, does this output set feel appropriately framed?"
- (Refined) Specifically ask him to validate the `flat_real` tariff default and the COD-year-aware CBAM trajectory

His feedback shapes Phase 2 implementation. If he flags concerns, address before Phase 2 ships.

---

## 12. To-Do List

### Phase 1: Core metrics (3–5 days, Refined)

| # | Task | Effort | Type |
|---|---|---|---|
| 1 | Create `src/model/project_finance.py` module | 0.5 day | Code |
| 2 | Implement `compute_cash_flow_projection` (with calendar_year mapping) | 0.5 day | Code |
| 3 | Implement `compute_indicative_metrics` (NPV, IRR, PI, payback) | 0.5 day | Code |
| 4 | (Refined) Implement `derive_cbam_trajectory_from_cod()` | 0.5 day | Code |
| 5 | (Refined) Implement tariff escalation scenarios + per-site default selection | 0.25 day | Code |
| 6 | Implement `get_default_tariff` based on site classification | 0.25 day | Code |
| 7 | Implement `compute_site_project_finance` wrapper | 0.5 day | Code |
| 8 | Unit tests for Phase 1 functions | 0.75 day | Test |
| 9 | Cross-validate against Cirata benchmark (Refined — expect match within 1pp under flat_real) | 0.5 day | Validation |
| 10 | Update scorecard schema with Phase 1 fields | 0.25 day | Code |
| 11 | Build Project Economics tab UI (Phase 1 view, with COD slider + tariff scenario toggle) | 0.5 day | UI |

### Phase 2: Lender metrics (3–4 days)

| # | Task | Effort | Type |
|---|---|---|---|
| 12 | Implement `compute_debt_amortization` | 0.5 day | Code |
| 13 | Implement `compute_dscr_schedule` | 0.5 day | Code |
| 14 | Implement `compute_llcr` | 0.25 day | Code |
| 15 | Implement `compute_equity_irr` | 0.25 day | Code |
| 16 | Update scorecard schema with Phase 2 fields | 0.25 day | Code |
| 17 | Extend Project Economics tab with lender metrics | 0.5 day | UI |
| 18 | Build debt amortization table view | 0.5 day | UI |
| 19 | (Refined) Build CBAM-trajectory-vs-COD overlay chart | 0.5 day | UI |
| 20 | Cross-validate against Cirata benchmark with debt | 0.5 day | Validation |
| 21 | Pak Faiz interim feedback (after Phase 1, before Phase 2 ships, including flat_real + COD-year refinements) | 0.25 day | Relationship |

### Phase 3: Optional polish (2–3 days)

| # | Task | Effort | Type |
|---|---|---|---|
| 22 | Build sensitivity tornado chart (with tariff scenario + COD year as variables — Refined) | 1 day | UI |
| 23 | Implement PF vs corporate finance toggle | 0.5 day | Code+UI |
| 24 | Cash flow projection visualization (chart with calendar-year x-axis — Refined) | 0.5 day | UI |
| 25 | Show ranges for IRR/payback (sensitivity-based, including tariff scenarios) | 0.5 day | UI |

### Parallel data work (can run alongside Phase 1–2)

| # | Task | Effort | Type |
|---|---|---|---|
| 26 | Compile TKBI classifications for 81 sites | 2–3 days | Data |
| 27 | Compile fiscal incentive data for KEK/KI sites | 2–3 days | Data |
| 28 | Compile regulatory context per sector | 2 days | Data |
| 29 | Pull provincial GDP from BPS | 0.5 day | Data |
| 30 | Build TKBI badge UI in scorecard | 0.5 day | UI |
| 31 | Build fiscal incentive panel UI | 1 day | UI |
| 32 | Build regulatory context panel UI | 1 day | UI |
| 33 | (Refined) PLN tariff freeze history note for §7.1 of methodology | 0.5 day | Data+Docs |

### Documentation and release

| # | Task | Effort | Type |
|---|---|---|---|
| 34 | Update `METHODOLOGY_CONSOLIDATED.md` with project finance section (including COD-year and tariff-scenario refinements) | 1 day | Docs |
| 35 | Add "What This Is Not" section to methodology | 0.25 day | Docs |
| 36 | CHANGELOG entry for v4.2 | 0.25 day | Docs |
| 37 | Substack post: "Making Solar Bankable in Indonesia" (with Cirata-validation framing) | 1 day | Content |
| 38 | Publish v4.2 to Zenodo | 0.25 day | Release |
| 39 | Email Pak Faiz with v4.2 launch announcement | 1 hour | Relationship |
| 40 | Request feedback meeting with Pak Faiz | 1 hour | Relationship |
| 41 | LinkedIn post about v4.2 release | 0.5 day | Content |

**Total effort:** ~8–11 focused work days (vs baseline 7–10). Net additions from refinement: ~1–1.5 days for COD-year derivation + tariff scenario toggle + CBAM-trajectory overlay UI.

---

## 13. Success Criteria

### 13.1 Functional

- [ ] All 81 sites have Phase 1 metrics computed (NPV, IRR, PI, payback)
- [ ] All 81 sites have Phase 2 lender metrics computed (DSCR, LLCR, DER)
- [ ] User can toggle between tariff source assumptions
- [ ] (Refined) User can toggle tariff escalation scenarios (flat_real / partial_reform / full_indexation)
- [ ] (Refined) User can adjust COD year (default = analysis_year + construction_years)
- [ ] User can adjust debt structure assumptions
- [ ] Cash flow projection viewable per site (with calendar_year column)
- [ ] Debt amortization schedule viewable per site
- [ ] (Refined) CBAM trajectory aligned to COD viewable per CBAM-exposed site

### 13.2 Validation

- [ ] (Refined) Cirata benchmark validates within ±1pp IRR under `flat_real` default; ±2pp under `partial_reform`; ±3pp under `full_indexation`
- [ ] All unit tests pass (including CBAM trajectory derivation and tariff escalation scenarios)
- [ ] Sanity checks pass for every site
- [ ] Pak Faiz feedback obtained on methodology, including refinements

### 13.3 Credibility

- [ ] "Indicative" framing on every metric in UI
- [ ] "What This Is Not" section in methodology document
- [ ] Standardized assumptions documented with sources (including PLN tariff freeze history and CBAM phase-in citations — Refined)
- [ ] No fake precision (appropriate rounding throughout)
- [ ] Tooltips on every numeric field, including new COD-year and tariff-scenario tooltips

### 13.4 Parallel data

- [ ] TKBI classification for all 81 sites
- [ ] Fiscal incentive data for major KEK/KI sites
- [ ] Regulatory context per sector
- [ ] Provincial GDP integrated
- [ ] (Refined) PLN tariff freeze history documented

### 13.5 Release

- [ ] v4.2 Zenodo DOI published
- [ ] CHANGELOG updated
- [ ] Methodology documented (with refinements)
- [ ] Substack post published
- [ ] Pak Faiz relationship loop closed

---

## 14. Relationship to Other Releases

**Depends on:**
- v4.1 Foundation Refactor — refined version (cost framework, classifications, multi-incumbent including marginal-daytime/nighttime split, destination-weighted CBAM, hydro hybrid)

**Enables:**
- v4.3 Multi-Pathway Analysis (uses project finance metrics with pathway combinations, including the regulatory pathway from [[Indonesia Dashboard Methodology Review]] §Adjustments needed)
- v4.4 Captive Deep Dive (uses project finance metrics with refined captive cost data and stranded asset risk)
- v4.5 Buyer Pressure (uses project finance metrics with buyer premium adjustments — but the OEM scope-3 dataset already lands in v4.1 refined for destination-weighted CBAM)

**Architectural decisions made here that v4.3+ depends on:**

The project finance module should be designed to accept different assumption combinations easily. v4.3 will feed it different tariff/financing/carbon scenarios. Design `compute_site_project_finance` to be parameterizable, not hardcoded.

Specifically:
- Tariff is a parameter, not derived
- Tariff escalation scenario is a parameter (Refined)
- COD year is a parameter (Refined — for CBAM trajectory alignment and for parallel-track scenarios in v4.3 e.g. "if PR 112 reform passes 2027, CBAM-exposed sites with COD ≥ 2028 see different trajectory")
- Debt structure is a parameter, not hardcoded
- Carbon pricing is composable on top of tariff (using v4.1 destination-weighted stack)
- All assumptions can be overridden by upstream callers

This way v4.3 just feeds different parameter combinations into the same engine, rather than rewriting it.

---

## Appendix: What's NOT in v4.2 (Refined)

To prevent scope creep, these are explicitly out of scope:

- Multi-pathway scenario analysis (toggles for financing/transmission/carbon) — v4.3
- **Regulatory pathway scenario** (Perpres 112 reform) — v4.3 (per [[Indonesia Dashboard Methodology Review]] §Adjustments needed finding 21)
- Cross-site comparison and ranking views — v4.3
- Stranded asset risk analysis — v4.4
- **RUPTL → demand → RUPTL feedback loop** — v4.4 (per [[Indonesia Dashboard Methodology Review]] §Adjustments needed finding 22)
- Buyer pressure premium modeling (analytical layer) — v4.5 (the **data** for OEM scope-3 lands in v4.1 refined per finding 23)
- PyPSA hourly dispatch — v5.0 (with single-site PoC potentially pulled forward to v4.4 per finding 24)
- Real PPA term modeling (escalation, indexing) — out of scope, requires NDA data
- Project-specific debt covenants — out of scope, requires NDA data
- Real tax structuring — out of scope

v4.2 is screening-level project finance. Resist the urge to add Stage 2/3 features. Ship the screening cleanly; add depth in subsequent releases.

---

*Cross-references: [[Indonesia Dashboard Methodology Review]] §v4.2 gaps. Refined version supersedes baseline `v4_2_project_finance_spec.md`. Refinements integrated: §4.6 (CBAM trajectory at site-specific COD year), §4.7 (flat real tariff default + reform toggle), §10.3 (assumptions table updated), §11.2 (Cirata benchmark validation under refined default).*
