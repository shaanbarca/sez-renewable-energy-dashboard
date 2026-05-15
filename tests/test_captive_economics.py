"""Tests for src/model/captive_economics.py (v4.3 M-AT8a).

Coverage targets (from /plan-eng-review test review):

    3A — Tier value regression lock per anchor site
    3B — Fuel-price scenario math (each scenario + bounds + linearity)
    3C — Override is scenario-invariant

Replaces the v4.1a tests in `tests/test_captive_coal_economics.py` +
`tests/test_captive_gas_economics.py`, which tested deleted helper functions.
"""

from __future__ import annotations

import pytest

from src.assumptions import (
    CAPTIVE_COAL_DEFAULTS,
    CAPTIVE_COAL_HHV_MMBTU_PER_TONNE,
    CAPTIVE_COAL_PRICE_SCENARIOS,
    CAPTIVE_GAS_DEFAULTS,
    CAPTIVE_GAS_PRICE_SCENARIOS,
    CAPTIVE_HYDRO_DEFAULT_USD_MWH,
    HOURS_PER_YEAR,
)
from src.model.captive_economics import (
    CaptiveLcoeResult,
    _load_defaults_cached,
    captive_lcoe_tier,
    is_csv_anchor_site,
    load_captive_defaults,
    resolve_captive_lcoe,
)


@pytest.fixture(autouse=True)
def _clear_defaults_cache():
    """Each test gets a fresh CSV load (the LRU cache is process-global)."""
    _load_defaults_cached.cache_clear()
    yield
    _load_defaults_cached.cache_clear()


# ─── 3A: Tier value regression lock ────────────────────────────────────────


@pytest.mark.parametrize(
    "site_id,fuel_type,expected_lcoe,expected_tier",
    [
        # T1 anchors — high-confidence, multi-source-verified site economics.
        ("indonesia-morowali-industrial-park-imip", "coal_subcritical", 50.0, "T1"),
        ("krakatau-posco-cilegon", "coal_supercritical", 62.0, "T1"),
        ("pupuk-kaltim-bontang", "natural_gas", 50.0, "T1"),
        ("inalum-asahan", "hydro", 30.0, "T1"),
        # T2 anchors — industry-archetype extrapolation.
        ("industrial-weda-bay-industrial-park-iwip", "coal_subcritical", 55.0, "T2"),
        ("obi-island-industrial-park", "coal_subcritical", 58.0, "T2"),
        ("indonesia-konawe-industrial-park-ikip", "coal_subcritical", 55.0, "T2"),
        ("pupuk-sriwidjaja-palembang", "natural_gas", 55.0, "T2"),
        ("petrokimia-gresik", "natural_gas", 55.0, "T2"),
        ("pupuk-kujang-cikampek", "natural_gas", 55.0, "T2"),
        ("pupuk-iskandar-muda-lhokseumawe", "natural_gas", 55.0, "T2"),
    ],
)
def test_captive_tier_values_match_methodology(
    site_id: str, fuel_type: str, expected_lcoe: float, expected_tier: str
) -> None:
    """3A: Anchor LCOE values pinned to METHODOLOGY §13.9–§13.11.

    If this test fails, someone bumped a tier value in
    `data/raw/captive_power_lcoe_defaults.csv` without updating the
    methodology. Either revert the CSV change or update §13.9–§13.11 AND
    this test in the same commit.
    """
    result = resolve_captive_lcoe(site_id, fuel_type, fuel_price_scenario="default")
    assert result is not None, f"Resolver returned None for {site_id}"
    assert result.lcoe_usd_mwh == pytest.approx(expected_lcoe, abs=0.5), (
        f"{site_id}: expected ~${expected_lcoe}/MWh per methodology, "
        f"got ${result.lcoe_usd_mwh}/MWh. Either revert the CSV change or "
        f"update METHODOLOGY §13.9–§13.11 + this test."
    )
    assert result.tier == expected_tier, (
        f"{site_id}: expected tier={expected_tier}, got {result.tier}"
    )


def test_csv_anchors_are_scenario_invariant_t1() -> None:
    """3C: T1 IMIP value should NOT change with the coal-price scenario.

    The override semantics treat per-site anchors as authoritative — they
    reflect site-specific economics (mine-mouth pricing, integrated supply)
    that don't track the market scenario slider.
    """
    imip_dmo = resolve_captive_lcoe(
        "indonesia-morowali-industrial-park-imip",
        "coal_subcritical",
        fuel_price_scenario="DMO",
    )
    imip_intl = resolve_captive_lcoe(
        "indonesia-morowali-industrial-park-imip",
        "coal_subcritical",
        fuel_price_scenario="INTERNATIONAL",
    )
    imip_custom = resolve_captive_lcoe(
        "indonesia-morowali-industrial-park-imip",
        "coal_subcritical",
        fuel_price_scenario="300",  # custom user input
    )
    assert imip_dmo.lcoe_usd_mwh == imip_intl.lcoe_usd_mwh == imip_custom.lcoe_usd_mwh == 50.0
    # All anchors are scenario-invariant.
    assert imip_dmo.scenario_used == "n/a"
    assert imip_intl.scenario_used == "n/a"


# ─── 3B: Fuel-price scenario math ──────────────────────────────────────────


def _expected_coal_formula(fuel_cost_per_tonne: float) -> float:
    """Reproduce the formula from `_formula_coal_lcoe` for assertion."""
    d = CAPTIVE_COAL_DEFAULTS
    per_mmbtu = fuel_cost_per_tonne / CAPTIVE_COAL_HHV_MMBTU_PER_TONNE
    fuel_component = per_mmbtu * d["heat_rate_btu_per_kwh"] / 1000.0
    fixed_om = (d["fixed_om_usd_per_kw_year"] / (HOURS_PER_YEAR * d["capacity_factor"])) * 1000.0
    return fuel_component + d["variable_om_usd_mwh"] + fixed_om + d["capital_recovery_usd_mwh"]


def _expected_gas_formula(fuel_cost_per_mmbtu: float) -> float:
    d = CAPTIVE_GAS_DEFAULTS
    fuel_component = fuel_cost_per_mmbtu * d["heat_rate_btu_per_kwh"] / 1000.0
    fixed_om = (d["fixed_om_usd_per_kw_year"] / (HOURS_PER_YEAR * d["capacity_factor"])) * 1000.0
    return fuel_component + d["variable_om_usd_mwh"] + fixed_om + d["capital_recovery_usd_mwh"]


@pytest.mark.parametrize("scenario,expected_price", list(CAPTIVE_COAL_PRICE_SCENARIOS.items()))
def test_coal_named_scenarios_match_assumption_dict(scenario: str, expected_price: float) -> None:
    """3B: For a coal site NOT in the CSV, each named scenario picks the right fuel price."""
    result = resolve_captive_lcoe(
        "not-a-real-site", "coal_subcritical", fuel_price_scenario=scenario
    )
    assert result is not None
    assert result.scenario_used == scenario
    expected_lcoe = _expected_coal_formula(expected_price)
    assert result.lcoe_usd_mwh == pytest.approx(expected_lcoe, abs=0.5)


@pytest.mark.parametrize("scenario,expected_price", list(CAPTIVE_GAS_PRICE_SCENARIOS.items()))
def test_gas_named_scenarios_match_assumption_dict(scenario: str, expected_price: float) -> None:
    """3B: For a gas site NOT in the CSV, each named scenario picks the right fuel price."""
    result = resolve_captive_lcoe("not-a-real-site", "natural_gas", fuel_price_scenario=scenario)
    assert result is not None
    assert result.scenario_used == scenario
    expected_lcoe = _expected_gas_formula(expected_price)
    assert result.lcoe_usd_mwh == pytest.approx(expected_lcoe, abs=0.5)


def test_coal_scenario_linearity_dmo_to_international() -> None:
    """3B: The HBA_2024 scenario ($130/ton) should sit linearly between DMO ($70)
    and INTERNATIONAL ($200) since the formula is linear in fuel cost."""
    dmo = resolve_captive_lcoe("not-a-real-site", "coal_subcritical", "DMO").lcoe_usd_mwh
    intl = resolve_captive_lcoe("not-a-real-site", "coal_subcritical", "INTERNATIONAL").lcoe_usd_mwh
    hba = resolve_captive_lcoe("not-a-real-site", "coal_subcritical", "HBA_2024").lcoe_usd_mwh

    # HBA ($130) is (130-70)/(200-70) = 60/130 ≈ 0.46 of the way from DMO to INTL.
    fraction = (130.0 - 70.0) / (200.0 - 70.0)
    expected_hba = dmo + fraction * (intl - dmo)
    assert hba == pytest.approx(expected_hba, abs=0.5)


def test_coal_custom_user_value() -> None:
    """3B: A numeric string scenario is parsed as a custom $/tonne value."""
    result = resolve_captive_lcoe("not-a-real-site", "coal_subcritical", "125")
    assert result is not None
    assert result.scenario_used == "custom_125"
    expected = _expected_coal_formula(125.0)
    assert result.lcoe_usd_mwh == pytest.approx(expected, abs=0.5)


def test_gas_custom_user_value() -> None:
    """3B: Gas custom value parsed as $/MMBtu."""
    result = resolve_captive_lcoe("not-a-real-site", "natural_gas", "12")
    assert result is not None
    assert result.scenario_used == "custom_12"
    expected = _expected_gas_formula(12.0)
    assert result.lcoe_usd_mwh == pytest.approx(expected, abs=0.5)


def test_unknown_scenario_raises() -> None:
    """3B: Garbage scenario strings raise ValueError."""
    with pytest.raises(ValueError, match="Unknown coal fuel_price_scenario"):
        resolve_captive_lcoe("not-a-real-site", "coal_subcritical", "GARBAGE")
    with pytest.raises(ValueError, match="Unknown gas fuel_price_scenario"):
        resolve_captive_lcoe("not-a-real-site", "natural_gas", "NONSENSE")


# ─── Hydro path (1D) ───────────────────────────────────────────────────────


def test_inalum_hydro_returns_30_flat() -> None:
    """1D: Inalum is sole hydro anchor; returns $30 with no fuel-price sensitivity."""
    result = resolve_captive_lcoe("inalum-asahan", "hydro")
    assert result is not None
    assert result.lcoe_usd_mwh == 30.0
    assert result.tier == "T1"
    assert result.scenario_used == "n/a"


def test_hydro_site_not_in_csv_uses_flat_default() -> None:
    """Hydro fallback returns CAPTIVE_HYDRO_DEFAULT_USD_MWH unchanged."""
    result = resolve_captive_lcoe("hypothetical-hydro-site", "hydro")
    assert result is not None
    assert result.lcoe_usd_mwh == CAPTIVE_HYDRO_DEFAULT_USD_MWH
    assert result.tier is None
    assert result.scenario_used == "n/a"


def test_hydro_ignores_scenario_param() -> None:
    """1D: Passing a coal-style scenario to a hydro site is silently ignored."""
    a = resolve_captive_lcoe("inalum-asahan", "hydro", "DMO")
    b = resolve_captive_lcoe("inalum-asahan", "hydro", "INTERNATIONAL")
    assert a.lcoe_usd_mwh == b.lcoe_usd_mwh == 30.0


# ─── Defensive: fuel_type = none / unknown ─────────────────────────────────


@pytest.mark.parametrize("fuel_type", ["none", None, "", "unknown", "biomass_chp"])
def test_non_captive_returns_none(fuel_type: str | None) -> None:
    """Sites with fuel_type='none' or unrecognised fuel type get None."""
    result = resolve_captive_lcoe("anything", fuel_type)
    assert result is None


def test_resolver_returns_dataclass_instance() -> None:
    """API contract — result is a CaptiveLcoeResult frozen dataclass."""
    result = resolve_captive_lcoe("indonesia-morowali-industrial-park-imip", "coal_subcritical")
    assert isinstance(result, CaptiveLcoeResult)
    # Frozen — can't mutate.
    with pytest.raises((AttributeError, Exception)):
        result.lcoe_usd_mwh = 999  # type: ignore[misc]


# ─── Helpers ───────────────────────────────────────────────────────────────


def test_is_csv_anchor_site_true_for_anchors() -> None:
    assert is_csv_anchor_site("indonesia-morowali-industrial-park-imip") is True
    assert is_csv_anchor_site("krakatau-posco-cilegon") is True
    assert is_csv_anchor_site("pupuk-kaltim-bontang") is True
    assert is_csv_anchor_site("inalum-asahan") is True
    assert is_csv_anchor_site("not-a-real-site") is False


def test_captive_lcoe_tier_returns_tier_string() -> None:
    assert captive_lcoe_tier("indonesia-morowali-industrial-park-imip") == "T1"
    assert captive_lcoe_tier("industrial-weda-bay-industrial-park-iwip") == "T2"
    assert captive_lcoe_tier("semen-tonasa") == "T3"
    assert captive_lcoe_tier("not-a-real-site") is None


def test_load_captive_defaults_includes_all_anchors() -> None:
    """Spec table check — the CSV must include all 4 T1 + all 7 T2 anchors."""
    df = load_captive_defaults()
    required_t1 = {
        "indonesia-morowali-industrial-park-imip",
        "krakatau-posco-cilegon",
        "pupuk-kaltim-bontang",
        "inalum-asahan",
    }
    required_t2 = {
        "industrial-weda-bay-industrial-park-iwip",
        "obi-island-industrial-park",
        "indonesia-konawe-industrial-park-ikip",
        "pupuk-sriwidjaja-palembang",
        "petrokimia-gresik",
        "pupuk-kujang-cikampek",
        "pupuk-iskandar-muda-lhokseumawe",
    }
    sites_in_csv = set(df["site_id"])
    missing_t1 = required_t1 - sites_in_csv
    missing_t2 = required_t2 - sites_in_csv
    assert not missing_t1, f"T1 anchors missing from CSV: {missing_t1}"
    assert not missing_t2, f"T2 anchors missing from CSV: {missing_t2}"


# ─── Citation year defensive test (per /plan-eng-review failure modes) ─────


def test_berkeley_citation_year_is_2024() -> None:
    """Defensive — Berkeley working paper is March 2024, not 2023.

    Past versions of this codebase had "Berkeley Goldman School (2023)" which
    was wrong. This test fails if anyone reintroduces the wrong year.
    """
    from src.assumptions import (
        CAPTIVE_COAL_DEFAULTS as _C,  # noqa: F401 — import to load module + verify comment
    )
    from src.utils import provenance as _prov

    # The provenance registry's incumbent LCOE entry must cite Berkeley GSPP 2024.
    flag = _prov.PROVENANCE_REGISTRY["captive_incumbent_lcoe_usd_mwh"][0]
    assert "Berkeley GSPP" in flag.citation and "2024" in flag.citation, (
        f"Berkeley citation should mention 'Berkeley GSPP' + '2024'; got: {flag.citation}"
    )
    # Anti-regression: must not say 2023.
    assert "Berkeley Goldman School (2023)" not in flag.citation, (
        "Berkeley citation regressed to 2023. Paper is March 2024."
    )
