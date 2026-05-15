"""Tests for v4.1a §5 captive gas economics (issue #72).

- Default LCOE from CAPTIVE_GAS_DEFAULTS lands in the empirical $55-90/MWh
  range for Indonesian captive gas. NB: spec's "~$65/MWh" is the empirical
  range mid; the formula with literal spec defaults returns ~$77/MWh.
  See src/model/captive_economics.py docstring for the discrepancy.
- Pupuk Kaltim Bontang override resolves to $65/MWh (the only gas anchor
  per spec §5.4).
- Sites without natural_gas classification get NULL on the gas column
  (no false positives — coal sites must not populate gas LCOE).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.assumptions import CAPTIVE_GAS_DEFAULTS
from src.model.captive_economics import (
    captive_gas_lcoe_usd_mwh,
    is_gas_anchor_site,
    load_captive_overrides,
    site_captive_gas_lcoe,
)

# ─── Default LCOE ────────────────────────────────────────────────────────────


def test_default_gas_lcoe_in_indonesian_range() -> None:
    """Indonesian captive gas LCOE cited at $55-90/MWh in IESR 2024 + IEA
    Indonesia gas pricing. Spec §5.2 claims defaults yield ~$65/MWh; formula
    with literal spec defaults returns ~$77/MWh."""
    lcoe = captive_gas_lcoe_usd_mwh()
    assert 55.0 <= lcoe <= 90.0, f"Gas LCOE {lcoe:.2f} outside cited Indonesian range $55-90/MWh"


def test_default_gas_lcoe_components_sum_correctly() -> None:
    """LCOE = fuel + variable_om + fixed_om_per_mwh + capital_recovery.
    Pin the exact formula so unintended changes to defaults are caught."""
    # fuel: $8/MMBTU × (7,500 BTU/kWh / 1,000) = $60/MWh
    fuel = (
        CAPTIVE_GAS_DEFAULTS["fuel_cost_usd_per_mmbtu"]
        * CAPTIVE_GAS_DEFAULTS["heat_rate_btu_per_kwh"]
        / 1000.0
    )
    # fixed_om: $25/kW-yr / (8760 × 0.80) × 1000 = ~$3.57/MWh
    fixed_om = (
        CAPTIVE_GAS_DEFAULTS["fixed_om_usd_per_kw_year"]
        / (8760 * CAPTIVE_GAS_DEFAULTS["capacity_factor"])
    ) * 1000.0
    expected = (
        fuel
        + CAPTIVE_GAS_DEFAULTS["variable_om_usd_mwh"]
        + fixed_om
        + CAPTIVE_GAS_DEFAULTS["capital_recovery_usd_mwh"]
    )
    assert captive_gas_lcoe_usd_mwh() == pytest.approx(expected, abs=0.01)


def test_default_gas_lcoe_lower_emissions_than_coal() -> None:
    """Methodology sanity — gas emissions intensity (0.40 tCO2/MWh) is
    less than half coal's (0.95 tCO2/MWh). Pin so a future regression to
    the wrong emission factor surfaces."""
    assert CAPTIVE_GAS_DEFAULTS["emissions_intensity_tco2_per_mwh"] < 0.50
    assert CAPTIVE_GAS_DEFAULTS["emissions_intensity_tco2_per_mwh"] >= 0.35


def test_default_gas_lcoe_responds_to_fuel_cost() -> None:
    """Doubling gas $/MMBTU should add fuel_cost × heat_rate/1000 to LCOE."""
    lo = captive_gas_lcoe_usd_mwh(defaults={**CAPTIVE_GAS_DEFAULTS, "fuel_cost_usd_per_mmbtu": 4})
    hi = captive_gas_lcoe_usd_mwh(defaults={**CAPTIVE_GAS_DEFAULTS, "fuel_cost_usd_per_mmbtu": 16})
    # $4 → $16 = +$12/MMBTU. Delta = 12 × 7.5 = $90/MWh.
    assert (hi - lo) == pytest.approx(90.0, abs=0.5)


# ─── Override CSV (the gas anchor: Pupuk Kaltim Bontang) ─────────────────────


@pytest.fixture
def overrides_df() -> pd.DataFrame:
    return load_captive_overrides()


def test_pupuk_kaltim_is_only_gas_anchor(overrides_df: pd.DataFrame) -> None:
    """Spec §5.4 — Pupuk Kaltim Bontang is the single gas anchor in v4.1a."""
    gas_rows = overrides_df[overrides_df["fuel_type"] == "natural_gas"]
    assert len(gas_rows) == 1
    assert gas_rows.iloc[0]["site_id"] == "pupuk-kaltim-bontang"
    assert gas_rows.iloc[0]["captive_lcoe_usd_mwh"] == 65.0


def test_pupuk_kaltim_uses_real_kebab_case_site_id(overrides_df: pd.DataFrame) -> None:
    """A4 finding — spec lists `pupuk_kaltim_bontang` (snake_case); the real
    site_id is `pupuk-kaltim-bontang` (kebab-case)."""
    gas_rows = overrides_df[overrides_df["fuel_type"] == "natural_gas"]
    sid = gas_rows.iloc[0]["site_id"]
    assert sid == "pupuk-kaltim-bontang"
    assert "_" not in sid


# ─── Site-level resolver (override + default + gating) ───────────────────────


def test_pupuk_kaltim_resolves_to_override(overrides_df: pd.DataFrame) -> None:
    """Anchor case: Pupuk Kaltim returns $65 (override), not the formula default."""
    result = site_captive_gas_lcoe(
        site_id="pupuk-kaltim-bontang",
        captive_fuel_type="natural_gas",
        overrides_df=overrides_df,
    )
    assert result == 65.0


def test_other_gas_sites_get_default(overrides_df: pd.DataFrame) -> None:
    """The other 4 fertilizer/petrochemical sites (Petrokimia, Pupuk Iskandar
    Muda, Pupuk Kujang, Pupuk Sriwidjaja) get the formula default LCOE."""
    for sid in [
        "petrokimia-gresik",
        "pupuk-iskandar-muda-lhokseumawe",
        "pupuk-kujang-cikampek",
        "pupuk-sriwidjaja-palembang",
    ]:
        result = site_captive_gas_lcoe(sid, "natural_gas", overrides_df)
        assert result == pytest.approx(captive_gas_lcoe_usd_mwh(), abs=0.01)


def test_coal_sites_get_null_gas(overrides_df: pd.DataFrame) -> None:
    """Coal-fueled captive sites must have NULL on the gas column —
    the gas-vs-coal split is the entire point of separating §4 + §5."""
    for sid in [
        "indonesia-morowali-industrial-park-imip",
        "industrial-weda-bay-industrial-park-iwip",
        "obi-island-industrial-park",
    ]:
        assert site_captive_gas_lcoe(sid, "coal_subcritical", overrides_df) is None
    assert (
        site_captive_gas_lcoe("krakatau-posco-cilegon", "coal_supercritical", overrides_df) is None
    )


def test_grid_only_sites_get_null_gas(overrides_df: pd.DataFrame) -> None:
    """Java cement / KEK Java (captive_fuel_type='none') get NULL gas LCOE."""
    assert site_captive_gas_lcoe("kek-gresik", "none", overrides_df) is None


def test_hybrid_aluminium_sites_get_null_gas(overrides_df: pd.DataFrame) -> None:
    """Aluminium (captive_fuel_type='hybrid') is neither coal nor pure gas —
    must NULL on the gas column."""
    assert site_captive_gas_lcoe("inalum-asahan", "hybrid", overrides_df) is None


# ─── Anchor classification helper ────────────────────────────────────────────


def test_is_gas_anchor_site_only_pupuk_kaltim(overrides_df: pd.DataFrame) -> None:
    assert is_gas_anchor_site("pupuk-kaltim-bontang", overrides_df)
    # Other fertilizer sites are NOT anchors (no override row → default).
    for sid in [
        "petrokimia-gresik",
        "pupuk-iskandar-muda-lhokseumawe",
        "pupuk-kujang-cikampek",
        "pupuk-sriwidjaja-palembang",
    ]:
        assert not is_gas_anchor_site(sid, overrides_df), f"{sid} should not be a gas anchor"


def test_is_gas_anchor_rejects_coal_anchors(overrides_df: pd.DataFrame) -> None:
    """IMIP is in the CSV with fuel_type=coal_subcritical — must NOT be flagged as gas anchor."""
    assert not is_gas_anchor_site("indonesia-morowali-industrial-park-imip", overrides_df)


# ─── Scorecard integration ───────────────────────────────────────────────────


def test_scorecard_all_five_fertilizer_sites_populate_gas() -> None:
    """Acceptance — all 5 fertilizer sites in dim_sites get a non-null
    captive_gas_lcoe_usd_mwh after the scorecard runs."""
    scorecard_csv = (
        Path(__file__).parent.parent / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"
    )
    if not scorecard_csv.exists():
        pytest.skip(f"fct_site_scorecard.csv not present at {scorecard_csv}")
    df = pd.read_csv(scorecard_csv)
    if "captive_gas_lcoe_usd_mwh" not in df.columns:
        pytest.skip("captive_gas_lcoe_usd_mwh column not yet present in scorecard")
    fertilizers = df[df["sector"] == "fertilizer"]
    assert len(fertilizers) == 5, f"expected 5 fertilizer sites, found {len(fertilizers)}"
    assert fertilizers["captive_gas_lcoe_usd_mwh"].notna().all(), (
        "every fertilizer site should have a non-null captive_gas_lcoe_usd_mwh"
    )


def test_scorecard_pupuk_kaltim_override_visible() -> None:
    """Pupuk Kaltim override ($65) must surface in the scorecard."""
    scorecard_csv = (
        Path(__file__).parent.parent / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"
    )
    if not scorecard_csv.exists():
        pytest.skip(f"fct_site_scorecard.csv not present at {scorecard_csv}")
    df = pd.read_csv(scorecard_csv)
    if "captive_gas_lcoe_usd_mwh" not in df.columns:
        pytest.skip("captive_gas_lcoe_usd_mwh column not yet present in scorecard")
    row = df[df["site_id"] == "pupuk-kaltim-bontang"]
    assert not row.empty
    assert row.iloc[0]["captive_gas_lcoe_usd_mwh"] == 65.0


def test_scorecard_coal_sites_have_null_gas() -> None:
    """Nickel sites (captive coal) must have NULL on the gas column."""
    scorecard_csv = (
        Path(__file__).parent.parent / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"
    )
    if not scorecard_csv.exists():
        pytest.skip(f"fct_site_scorecard.csv not present at {scorecard_csv}")
    df = pd.read_csv(scorecard_csv)
    if "captive_gas_lcoe_usd_mwh" not in df.columns:
        pytest.skip("captive_gas_lcoe_usd_mwh column not yet present in scorecard")
    nickel = df[df["sector"] == "nickel"]["captive_gas_lcoe_usd_mwh"]
    assert nickel.isna().all(), "every nickel site should have null captive_gas_lcoe_usd_mwh"
