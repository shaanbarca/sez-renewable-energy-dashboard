# v4.3 M-AT8a — Captive Power LCOE Implementation Plan

**Filed**: 2026-05-15
**Status**: Plan signed off via `/plan-eng-review`, ready to implement
**Supersedes**: v4.1a/sectoral-economics (PR #75) — that branch gets repurposed for this work; the 6 anchor overrides + formula scaffolding are kept and extended.
**Source review**: [methodology_captive_coal_lcoe_per_site_M-AT8_review_2026-05-15.md](methodology_captive_coal_lcoe_per_site_M-AT8_review_2026-05-15.md)

## Context

The captive-coal/gas LCOE feature shipped in v4.1a sectoral (PR #75) had three concrete defects that surfaced during user review:

1. **Wrong year on Berkeley citation** — code says 2023; paper is March 2024 (Chojkiewicz, Abhyankar, Paliwal, Phadke).
2. **Wrong LCOE range claim** — comment says "$35-60/MWh midpoint per Berkeley." Berkeley Figure 4 (p9) actually shows $65-75/MWh at DMO-priced coal, $115/MWh at international pricing. IESR LCOE tool puts NEW captive coal at $77/MWh. Our claimed range doesn't exist in either source.
3. **Three site-value discrepancies** vs the M-AT8 spec wiki synthesis (also dated 2026-05-15):
   - Krakatau Posco: spec says $62 (T1, supercritical, mid-to-high CV imported sea-to-Java); PR #75 has $48
   - Pupuk Kaltim Bontang: spec says $50 (T1, HGBT $7/MMBtu gas, brownfield depreciated); PR #75 has $65
   - Inalum Asahan: spec says $30 hydro; PR #75 treats it as default coal/gas (no hydro fuel type exists)

Per `/plan-eng-review` Step 0 + Section 1.1A-1D decisions, PR #75 is held and the work is repurposed to ship the corrected values + the full M-AT8a backend (tier framing + fuel-price scenarios) in one coherent change.

M-AT8b (UI: methodology drawer + composite badge + URL state + live recompute) ships as a separate sub-PR after M-AT8a lands.
M-AT8c (trajectory overlay: year slider + IDX Carbon ramp + CBAM Scope 2 toggle) is deferred to v4.4 blocked on M-AT7.

## Decisions from /plan-eng-review (2026-05-15)

| # | Issue | Decision |
|---|---|---|
| Step 0 | PR #75 has wrong values vs M-AT8 spec written today | Hold PR #75; port full M-AT8a in within the same branch |
| 1A | CSV path | `data/raw/captive_power_lcoe_defaults.csv` (rename from `captive_generation_overrides.csv`) |
| 1B | Sub-PR slicing | M-AT8a (data + math) ships first; M-AT8b (UI) ships separately; M-AT8c (trajectory) deferred |
| 1C | Trajectory overlay | Deferred to M-AT8c, blocked on M-AT7 |
| 1D | Inalum hydro | Add `hydro` as a third fuel type; flat $30/MWh, no fuel-price sensitivity |
| 2A | Default LCOE functions | Delete `captive_coal_lcoe_usd_mwh()` + `captive_gas_lcoe_usd_mwh()`; replace with single `resolve_captive_lcoe()` resolver |
| 2B | Citation granularity | Paper-level in code/CSV; page-level only in METHODOLOGY |
| 2C | Two confidence systems | Keep both; rename existing `classification_confidence` → `captive_classification_confidence`; add new `captive_lcoe_tier` (T1/T2/T3) |
| 3A | Tier value regression | `test_captive_tier_values_match_methodology` — per-anchor assertion |
| 3B | Scenario math | Per fuel: each named scenario + bounds + linearity (~8 tests/fuel) |
| 3C | Override priority | Test override is scenario-invariant |
| 4A | Memoization | Cache CSV load + resolver output (M-AT8b's live recompute depends on this) |

## Scope

### In scope (M-AT8a)

- Rename `data/raw/captive_generation_overrides.csv` → `data/raw/captive_power_lcoe_defaults.csv`; expand schema to include all 81 sites + tier column
- Add `hydro` as a `captive_fuel_type` value (sole anchor: Inalum Asahan)
- New `resolve_captive_lcoe(site_id, fuel_type, fuel_price_scenario, overrides_df)` in `src/model/captive_economics.py`
- Delete v4.1a's `captive_coal_lcoe_usd_mwh()` + `captive_gas_lcoe_usd_mwh()` standalone defaults
- Add `CAPTIVE_FUEL_PRICE_SCENARIOS` constants in `src/assumptions.py` (4 coal scenarios, 4 gas scenarios)
- Update `CAPTIVE_COAL_DEFAULTS` + `CAPTIVE_GAS_DEFAULTS` to match Berkeley 2024 Table 1 anchor values (fix coal_price to $70/ton DMO baseline; fix capital cost to supercritical $1700/kW)
- Add 3 new scorecard columns: `captive_lcoe_tier` (T1/T2/T3), `captive_lcoe_fuel_price_scenario` (string), `captive_incumbent_lcoe_usd_mwh` (single resolved value, replacing `captive_coal_lcoe_usd_mwh` + `captive_gas_lcoe_usd_mwh`)
- Rename existing `classification_confidence` → `captive_classification_confidence` in scorecard + provenance
- Update provenance registry: 4 new entries (tier, fuel_price_scenario, incumbent_lcoe, plus renamed classification_confidence)
- Update METHODOLOGY §13.9 + §13.10 with page-numbered Berkeley 2024 citations + correct LCOE ranges
- Update `data/raw/README.md` to document the new CSV schema
- All tests from issues 3A/3B/3C
- v4.0 column-presence baseline preserved (no rename of v4.0 columns)

### NOT in scope (deferred)

- **M-AT8b (v4.3, separate PR)**: methodology drawer, composite badge UI, URL state for fuel-price scenarios, live frontend recompute
- **M-AT8c (v4.4, blocked on M-AT7)**: trajectory overlay (year slider + carbon-price ramp + CBAM Scope 2 toggle)
- **Hydro resource potential layer**: separate future feature (same pattern as solar/wind resource layers); independent from Inalum's incumbent modeling
- **Page-numbered citations in every CSV row**: paper-level cites only in CSV; page-numbered cites live in METHODOLOGY
- **T3 placeholder sites' specific values**: T3 means "we don't have a confident anchor yet" — sites in this tier get a generic flag with a clear "needs research" tag, not a precise number to defend
- **Backfilling v4.1a tier values for non-anchor sites**: all non-anchor sites get T3 with the formula default as the placeholder; v4.4 polish work tightens specific sites
- **CBAM Scope 2 expansion modeling**: separate M-AT7 work
- **Coal-CV per-site sensitivity**: requires site-specific coal data we don't have; T2/T3 sites use representative archetype CV
- **Pre-construction Kalimantan smelter additions** (mostly cancelled): tracked as T3 placeholders but not actively modeled

### What already exists (from v4.1a sectoral PR #75)

Reused without modification:
- `data/raw/site_classifications.csv` — classification overrides table from #70
- `fct_site_classifications.csv` pipeline step from #70
- Provenance registry structure (`PROVENANCE_REGISTRY` dict + override loaders) — extended with M-AT8 entries

Reused with modification:
- `data/raw/captive_generation_overrides.csv` → renamed `captive_power_lcoe_defaults.csv` + expanded schema
- `src/model/captive_economics.py` — formula functions deleted; resolver added
- `src/assumptions.py::CAPTIVE_COAL_DEFAULTS` + `CAPTIVE_GAS_DEFAULTS` — values corrected to Berkeley 2024 anchors
- `src/pipeline/build_fct_site_scorecard.py` — column writes updated to call resolver
- Existing tests in `tests/test_captive_coal_economics.py` + `tests/test_captive_gas_economics.py` — rewritten to test resolver, with new regression-lock tests added

## Implementation plan — file-by-file

### Step 1: Data files

**`data/raw/captive_power_lcoe_defaults.csv`** (rename + expand)

New schema:
```
site_id, archetype, fuel_type, tier, default_lcoe_usd_mwh, coal_cv_kcal_per_kg, gas_pricing_regime, boiler_tech, cf_default, source_citation
```

All 81 sites get a row. T1/T2 anchors get explicit values from the M-AT8 spec table. T3 placeholders get the formula-output value with `tier='T3'` and `source_citation='placeholder — not site-specific'`.

T1 rows (verbatim from M-AT8 spec):
- `indonesia-morowali-industrial-park-imip`, IMIP nickel RKEF+HPAL, `coal_subcritical`, T1, $50, ~3500 kcal/kg, n/a, subcritical, 0.95, "Berkeley GSPP 2024 Fig 4 + IESR + CREA"
- `industrial-weda-bay-industrial-park-iwip`, IWIP nickel IRNC, `coal_subcritical`, T2, $55, ~3500 kcal/kg, n/a, subcritical, 0.90, "IMIP archetype + remote-island logistics"
- `obi-island-industrial-park`, Obi nickel HPAL, `coal_subcritical`, T2, $58, ~3500 kcal/kg, n/a, subcritical, 0.90, "IMIP archetype + most-remote logistics"
- `indonesia-konawe-industrial-park-ikip`, Konawe nickel, `coal_subcritical`, T2, $55, ~3500 kcal/kg, n/a, subcritical, 0.90, "IMIP archetype + Sulawesi Tenggara"
- `krakatau-posco-cilegon`, Krakatau Posco steel BF-BOF, `coal_supercritical`, T1, $62, ~5500 kcal/kg, n/a, supercritical, 0.85, "JETP CPS + ESDM Tech Catalogue"
- `pupuk-kaltim-bontang`, Pupuk Kaltim fertilizer, `natural_gas`, T1, $50, n/a, hgbt, ccgt, 0.85, "HGBT 2025 regulation + Pupuk Indonesia disclosures"
- `inalum-asahan`, Inalum aluminium, `hydro`, T1, $30, n/a, n/a, n/a, 0.45, "Asahan hydroelectric 1980s+ — established"

T2 rows: Pupuk Sriwidjaja Palembang, Pupuk Kujang Cikampek (both `natural_gas`, HGBT, $55), Chandra Asri Cilegon petrochem (`natural_gas`, HGBT, $62), Pupuk Iskandar Muda Lhokseumawe (`natural_gas`, HGBT, $55).

T3 rows: remaining ~70 sites. Tier defaults applied (T3 = formula output at default scenario, low-confidence).

Sectoral exclusions (sites where captive electricity isn't a meaningful concept):
- Cement sites: coal is process fuel, not captive electricity. `captive_fuel_type = 'none'`, no LCOE column populated.
- Pulp/paper sites: biomass CHP archetype; flag in METHODOLOGY but exclude from M-AT8 modeling.

### Step 2: Code — src/assumptions.py

Add scenario constants (lines after existing CAPTIVE_GAS_DEFAULTS):

```python
CAPTIVE_COAL_PRICE_SCENARIOS = {
    "DMO": 70.0,              # Indonesian DMO-subsidized
    "HBA_2024": 130.0,        # HBA 2024 average
    "INTERNATIONAL": 200.0,   # International benchmark
}
CAPTIVE_GAS_PRICE_SCENARIOS = {
    "HGBT": 7.0,              # 7 covered sectors regulated rate
    "MARKET": 10.0,           # non-HGBT-eligible
    "SPOT_LNG_JKM": 14.0,     # JKM-linked spot
}
CAPTIVE_COAL_PRICE_BOUNDS = (50.0, 400.0)   # user input range
CAPTIVE_GAS_PRICE_BOUNDS = (4.0, 20.0)      # user input range
```

Update `CAPTIVE_COAL_DEFAULTS` to match Berkeley 2024 Table 1:
- `fuel_cost_usd_per_tonne`: 55 → **70** (DMO baseline)
- `coal_capital_usd_per_kw`: new field, $1700 (supercritical per Berkeley)
- Rest unchanged

Update `CAPTIVE_GAS_DEFAULTS`:
- `fuel_cost_usd_per_mmbtu`: 8 → **7** (HGBT baseline, not "typical")
- `gas_capital_usd_per_kw`: new field, $1000 (CCGT per Berkeley)
- Rest unchanged

Cite Berkeley GSPP 2024 March (not 2023). Cite Table 1 p.6 for capital costs, Figure 4 p.9 for LCOE ranges.

### Step 3: Code — src/model/captive_economics.py

Delete:
- `captive_coal_lcoe_usd_mwh()`
- `captive_gas_lcoe_usd_mwh()`
- `site_captive_coal_lcoe()`
- `site_captive_gas_lcoe()`

Add:

```python
@lru_cache(maxsize=1)
def _load_defaults_cached() -> pd.DataFrame:
    """Load the tier defaults CSV once per process. Cleared by test fixture if needed."""
    return pd.read_csv(DEFAULTS_CSV_DEFAULT)

def resolve_captive_lcoe(
    site_id: str,
    fuel_type: str,
    fuel_price_scenario: str = "default",  # "DMO" for coal, "HGBT" for gas, "default" picks by fuel
    overrides_df: pd.DataFrame | None = None,
) -> CaptiveLcoeResult:
    """Single resolver. Priority chain: explicit_override > tier_default + scenario_adjustment.
    Returns (lcoe_usd_mwh, tier, source_citation, scenario_used)."""
```

`CaptiveLcoeResult` is a frozen dataclass with `lcoe_usd_mwh`, `tier`, `source_citation`, `scenario_used` fields.

Hydro short-circuit: `fuel_type == 'hydro'` returns the tier default verbatim with `scenario_used='n/a'`.

### Step 4: Code — src/pipeline/build_fct_site_scorecard.py

Replace the v4.1a captive coal + captive gas column writes with:

```python
captive_results = df.apply(
    lambda r: resolve_captive_lcoe(
        r["site_id"], r["captive_fuel_type"], fuel_price_scenario="default"
    ),
    axis=1,
)
df["captive_incumbent_lcoe_usd_mwh"] = captive_results.map(lambda r: r.lcoe_usd_mwh if r else None)
df["captive_lcoe_tier"] = captive_results.map(lambda r: r.tier if r else None)
df["captive_lcoe_fuel_price_scenario"] = captive_results.map(lambda r: r.scenario_used if r else None)
```

Rename `classification_confidence` → `captive_classification_confidence` in the column list.

Delete v4.1a's `captive_coal_lcoe_usd_mwh` + `captive_gas_lcoe_usd_mwh` columns from the output (additive migration: they were only added today and haven't shipped). New single `captive_incumbent_lcoe_usd_mwh` replaces both.

### Step 5: Code — src/utils/provenance.py

Update PROVENANCE_REGISTRY entries:
- Remove: `captive_coal_lcoe_usd_mwh`, `captive_gas_lcoe_usd_mwh`
- Add: `captive_incumbent_lcoe_usd_mwh`, `captive_lcoe_tier`, `captive_lcoe_fuel_price_scenario`
- Rename: `classification_confidence` → `captive_classification_confidence`
- Override loaders: `captive_coal_override_loader` + `captive_gas_override_loader` collapsed into a single `captive_lcoe_override_loader` that checks the unified CSV

Update citations on all 4 to "Berkeley GSPP 2024" (not 2023) + paper-level only.

### Step 6: Tests

**Rewrite** existing test files:
- `tests/test_captive_coal_economics.py` — tests `resolve_captive_lcoe(fuel_type='coal_*')` paths
- `tests/test_captive_gas_economics.py` — tests `resolve_captive_lcoe(fuel_type='natural_gas')` paths
- New: `tests/test_captive_hydro_economics.py` — tests `fuel_type='hydro'` returns $30 flat, no scenario sensitivity

**Add** new test files / cases per /plan-eng-review:

1. `tests/test_captive_tier_values_match_methodology.py` (issue 3A regression lock):
   - Parameterized over each T1/T2 anchor
   - Asserts `resolve_captive_lcoe(site_id, fuel_type, scenario='default').lcoe_usd_mwh == expected` from the M-AT8 spec table
   - On failure, diagnostic points at the spec doc + line in `captive_power_lcoe_defaults.csv`

2. `tests/test_captive_scenarios.py` (issue 3B scenario math):
   - Coal: `DMO → tier_default` (no adjustment), `INTERNATIONAL → tier + ~$50`, `HBA_2024 → linear interp`, custom value bounds
   - Gas: `HGBT → tier_default`, `MARKET → tier + ~$19`, `SPOT_LNG_JKM → tier + ~$45`, custom value bounds
   - Both: bounds reject (raise) or clip (configurable)

3. `tests/test_captive_override_priority.py` (issue 3C):
   - IMIP with `scenario='DMO'` → $50 (override)
   - IMIP with `scenario='INTERNATIONAL'` → still $50 (override wins, scenario ignored)
   - Documents the priority chain in the test docstring

Existing scorecard golden test updates: the `fct_site_scorecard.csv` schema changes (coal+gas columns merged into incumbent column + tier + scenario columns; classification_confidence renamed). Regenerate the golden pkl as part of this PR.

### Step 7: METHODOLOGY_CONSOLIDATED.md updates

§13.9 (Captive coal LCOE) — rewrite:
- Cite Berkeley GSPP **March 2024** (not 2023)
- Replace "$35-60 mid-range" claim with actual ranges: Berkeley Fig 4 p.9 $65-75/MWh at DMO, $115/MWh at international; IESR LCOE tool $77/MWh new captive
- Document the tier framing (T1/T2/T3) + fuel-price scenarios
- Add a paragraph explaining why anchor values (IMIP $50, Krakatau $62) are below the literature midpoint: subcritical vs supercritical, mine-mouth/DMO coal pricing, partial depreciation, vertically-integrated owners (Tsingshan)
- Tier-by-tier anchor table

§13.10 (Captive gas LCOE) — rewrite:
- HGBT regulated pricing ($7/MMBtu) as the default scenario
- Sectoral coverage of HGBT (7 sectors: fertilizer, petrochem, oleochem, steel, ceramics, glass, rubber gloves)
- Why Pupuk Kaltim at $50 (T1) sits below the Berkeley reference (~$77 at $9/MMBtu LNG): HGBT regulated price + brownfield depreciated CCGT
- Tier-by-tier anchor table

§13.11 (new) — Captive hydro:
- Inalum Asahan archetype
- Why it's structurally different from coal/gas (no fuel cost, no fuel-price sensitivity)
- Why it's exceptionally hard for solar to beat (~$30/MWh hydro vs solar at $50-70/MWh)

### Step 8: data/raw/README.md

Document the renamed `captive_power_lcoe_defaults.csv` schema; note the migration from `captive_generation_overrides.csv`.

### Step 9: DATA_DICTIONARY.md

Add entries for `captive_incumbent_lcoe_usd_mwh`, `captive_lcoe_tier`, `captive_lcoe_fuel_price_scenario`. Mark old `captive_coal_lcoe_usd_mwh` + `captive_gas_lcoe_usd_mwh` as removed (only existed for ~24 hours; no migration burden).

## Test coverage diagram

```
M-AT8a code paths                                  Coverage target
─────────────────────────────────                  ──────────────
[+] src/model/captive_economics.py
  └── resolve_captive_lcoe()
      ├── override row exists                      ★★★ (3C: scenario-invariant)
      ├── coal + DMO scenario                      ★★★ (3B + 3A regression)
      ├── coal + INTERNATIONAL scenario            ★★  (3B)
      ├── coal + HBA_2024 (interpolated)           ★★  (3B linearity)
      ├── coal + custom user value (bounds)        ★★  (3B bounds)
      ├── gas + HGBT scenario                      ★★★ (3B + 3A regression)
      ├── gas + MARKET scenario                    ★★  (3B)
      ├── gas + SPOT_LNG_JKM scenario              ★★  (3B)
      ├── gas + custom user value (bounds)         ★★  (3B bounds)
      ├── hydro (Inalum)                           ★★★ (1D + 3A)
      └── unknown fuel_type → None                 ★★  (defensive)

[+] src/pipeline/build_fct_site_scorecard.py
  └── scorecard column population
      ├── all 81 sites get tier value              ★★★ (golden)
      ├── T1 anchors match spec values             ★★★ (3A regression lock)
      ├── T3 placeholders have explicit tier='T3'  ★★  (no silent default)
      └── hydro site has no fuel_price_scenario    ★★★ (1D)

COVERAGE TARGET: 14/14 paths (100%)
QUALITY TARGET: ≥8 ★★★ paths (behavior + edge + error)
```

No `[→E2E]` paths — M-AT8a is pure backend. E2E tests come in M-AT8b when slider UI ships.

## Implementation order (sequential)

1. **Data first**: write `data/raw/captive_power_lcoe_defaults.csv` (all 81 sites, with explicit T1/T2/T3 tier values)
2. **Math second**: `resolve_captive_lcoe()` + `CaptiveLcoeResult` dataclass; update `CAPTIVE_*_DEFAULTS` + add `CAPTIVE_*_PRICE_SCENARIOS`
3. **Scorecard third**: update `build_fct_site_scorecard.py` to write the new columns
4. **Provenance fourth**: update registry + override loader
5. **Tests fifth**: rewrite + add regression locks
6. **Docs sixth**: METHODOLOGY §13.9 / §13.10 / §13.11; DATA_DICTIONARY; README
7. **Regenerate seventh**: full pipeline run + regen golden pkl + verify tests pass
8. **Commit + push**: replace PR #75's title + body via `gh pr edit 75`; force-push to `v4.1a/sectoral-economics` branch (renamed via `gh pr edit --title`)

Estimated total: ~1.5-2 days of focused work. Sequential because each step depends on the previous; no parallelization opportunity.

## Rollout

**Branch handling**:
- The current `v4.1a/sectoral-economics` branch becomes the M-AT8a implementation branch
- Rename the open PR #75:
  - Title: `feat(v4.3 M-AT8a): captive power LCOE — tier framing + fuel-price scenarios + hydro`
  - Body: full Rich template with the corrected values and citations
- Squash the existing 2 commits (sectoral feature + scorecard regen) into a single commit for the v4.1a foundation, then add M-AT8a-specific commits on top — or alternatively, rewrite the whole branch history (less ideal; messier rebase).

**Risk if we ship M-AT8a without M-AT8b**: scorecard CSV has the new columns + correct values, but the frontend doesn't yet read them. Outcome: no visible UI change in the dashboard until M-AT8b ships. Risk is low (backend correctness lands; UI catches up in next PR), but the user-visible value of M-AT8a alone is limited to "people who read the scorecard CSV directly."

**Mitigation**: ship M-AT8a + M-AT8b within the same week if possible; otherwise note in the CHANGELOG that scorecard columns are correct but UI integration is M-AT8b.

## Failure modes

| Failure | Test that catches it | Manual fix |
|---|---|---|
| Krakatau Posco silently drifts back to $48 | `test_captive_tier_values_match_methodology[krakatau-posco-cilegon]` | Edit CSV row |
| Pupuk Kaltim Bontang gets the coal default applied | `test_captive_gas_economics::test_hgbt_scenario[pupuk-kaltim-bontang]` | Check fuel_type column in CSV |
| Inalum gets coal LCOE | `test_captive_hydro_economics::test_inalum_returns_hydro` | Check fuel_type = 'hydro' in CSV |
| Slider wiring breaks override priority | `test_captive_override_priority::test_imip_ignores_scenario` | Check resolver branch order |
| Berkeley citation regresses to 2023 | grep test in `tests/test_citation_year_correct.py` (new defensive test) | Update citation in code |

No critical gaps. All known failure modes have test coverage in the plan.

## Worktree parallelization

Sequential. M-AT8a steps are interdependent (data → math → scorecard → tests → docs). No parallelization opportunity inside M-AT8a. M-AT8b (UI, future PR) could be parallelized against an unrelated frontend stream but is itself sequential within (drawer → badge → URL state → live recompute).

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | not run (eng-driven refinement, not product-strategic) |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | not run (consider before implementing) |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 11 issues, 0 critical gaps, 0 unresolved decisions |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | n/a (M-AT8a is backend-only; M-AT8b will need it) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | not run |

- **UNRESOLVED:** 0
- **VERDICT:** ENG CLEARED — ready to implement. M-AT8b will need its own /plan-eng-review when frontend work begins.
