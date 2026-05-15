"""Tests for v4.1a §4 captive coal economics (issue #71).

- Default LCOE from CAPTIVE_COAL_DEFAULTS lands in the empirical $35-60/MWh
  range (Berkeley Goldman 2023 + IESR 2024). NB: spec's "~$45/MWh" is the
  empirical-range mid; the formula's literal output with these defaults is
  ~$55/MWh — see src/model/captive_economics.py module docstring for the
  discrepancy explanation.
- Each of the 5 override sites in data/raw/captive_generation_overrides.csv
  resolves to the expected anchor value (IMIP $50, IWIP $55, Obi $60,
  Konawe $52, Krakatau Posco $48).
- Krakatau Posco fuel_type is coal_supercritical (not subcritical).
- Sites without coal classification get NULL on the coal column.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.assumptions import (
    CAPTIVE_COAL_DEFAULTS,
    CAPTIVE_COAL_HHV_MMBTU_PER_TONNE,
)
from src.model.captive_economics import (
    captive_coal_lcoe_usd_mwh,
    is_coal_anchor_site,
    load_captive_overrides,
    site_captive_coal_lcoe,
)

# ─── Default LCOE ────────────────────────────────────────────────────────────


def test_default_lcoe_in_indonesian_captive_coal_range() -> None:
    """Berkeley + IESR 2024 cite Indonesian captive coal at $35-60/MWh.
    Spec §4.3 claims defaults yield ~$45/MWh; the formula with literal
    spec defaults actually returns ~$55/MWh (see module docstring)."""
    lcoe = captive_coal_lcoe_usd_mwh()
    assert 35.0 <= lcoe <= 60.0, f"LCOE {lcoe:.2f} outside cited Indonesian range $35-60/MWh"


def test_default_lcoe_components_sum_correctly() -> None:
    """LCOE = fuel + variable_om + fixed_om_per_mwh + capital_recovery.
    Pin the exact formula output so unintended changes to defaults are caught.
    """
    # fuel: ($55/tonne / 19 MMBTU/tonne) × (10,000 BTU/kWh / 1,000) = ~$28.95/MWh
    fuel = (
        CAPTIVE_COAL_DEFAULTS["fuel_cost_usd_per_tonne"]
        / CAPTIVE_COAL_HHV_MMBTU_PER_TONNE
        * CAPTIVE_COAL_DEFAULTS["heat_rate_btu_per_kwh"]
        / 1000.0
    )
    # fixed_om: $40/kW-yr / (8760 × 0.85) × 1000 = ~$5.37/MWh
    fixed_om = (
        CAPTIVE_COAL_DEFAULTS["fixed_om_usd_per_kw_year"]
        / (8760 * CAPTIVE_COAL_DEFAULTS["capacity_factor"])
    ) * 1000.0
    expected = (
        fuel
        + CAPTIVE_COAL_DEFAULTS["variable_om_usd_mwh"]
        + fixed_om
        + CAPTIVE_COAL_DEFAULTS["capital_recovery_usd_mwh"]
    )
    assert captive_coal_lcoe_usd_mwh() == pytest.approx(expected, abs=0.01)


def test_default_lcoe_responds_to_fuel_cost() -> None:
    """Sensitivity check — doubling fuel cost roughly doubles the fuel
    component, so LCOE should rise by ~$29/MWh."""
    lo_lcoe = captive_coal_lcoe_usd_mwh(
        defaults={**CAPTIVE_COAL_DEFAULTS, "fuel_cost_usd_per_tonne": 27.5}
    )
    hi_lcoe = captive_coal_lcoe_usd_mwh(
        defaults={**CAPTIVE_COAL_DEFAULTS, "fuel_cost_usd_per_tonne": 110}
    )
    # Going from 27.5 → 110 ($/tonne) is +$82.5/tonne. Fuel-component delta
    # = (82.5/19) × 10 = ~$43/MWh.
    assert (hi_lcoe - lo_lcoe) == pytest.approx(43.42, abs=0.5)


# ─── Override CSV ────────────────────────────────────────────────────────────


@pytest.fixture
def overrides_df() -> pd.DataFrame:
    """The shipped overrides CSV — 5 coal anchor + 1 gas anchor."""
    return load_captive_overrides()


def test_overrides_csv_has_5_coal_anchors(overrides_df: pd.DataFrame) -> None:
    coal_rows = overrides_df[overrides_df["fuel_type"].str.startswith("coal_", na=False)]
    assert len(coal_rows) == 5
    expected_anchors = {
        "indonesia-morowali-industrial-park-imip",
        "industrial-weda-bay-industrial-park-iwip",
        "obi-island-industrial-park",
        "indonesia-konawe-industrial-park-ikip",
        "krakatau-posco-cilegon",
    }
    assert set(coal_rows["site_id"]) == expected_anchors


@pytest.mark.parametrize(
    "site_id,expected_lcoe,expected_fuel_type",
    [
        ("indonesia-morowali-industrial-park-imip", 50.0, "coal_subcritical"),
        ("industrial-weda-bay-industrial-park-iwip", 55.0, "coal_subcritical"),
        ("obi-island-industrial-park", 60.0, "coal_subcritical"),
        ("indonesia-konawe-industrial-park-ikip", 52.0, "coal_subcritical"),
        ("krakatau-posco-cilegon", 48.0, "coal_supercritical"),
    ],
)
def test_each_override_matches_spec(
    overrides_df: pd.DataFrame,
    site_id: str,
    expected_lcoe: float,
    expected_fuel_type: str,
) -> None:
    """Spec §4.4 anchor coverage — each override hits the expected LCOE."""
    row = overrides_df[overrides_df["site_id"] == site_id]
    assert not row.empty, f"override row missing for {site_id}"
    assert row.iloc[0]["captive_lcoe_usd_mwh"] == expected_lcoe
    assert row.iloc[0]["fuel_type"] == expected_fuel_type


def test_krakatau_posco_uses_supercritical(overrides_df: pd.DataFrame) -> None:
    """Anchor — only Krakatau Posco uses USC, others are subcritical."""
    krakatau = overrides_df[overrides_df["site_id"] == "krakatau-posco-cilegon"]
    assert krakatau.iloc[0]["fuel_type"] == "coal_supercritical"
    others = overrides_df[
        (overrides_df["fuel_type"].str.startswith("coal_", na=False))
        & (overrides_df["site_id"] != "krakatau-posco-cilegon")
    ]
    assert (others["fuel_type"] == "coal_subcritical").all()


# ─── Site-level resolver (override + default + gating) ───────────────────────


def test_site_resolver_returns_override(overrides_df: pd.DataFrame) -> None:
    """IMIP has an override → resolver returns the override value, not default."""
    result = site_captive_coal_lcoe(
        site_id="indonesia-morowali-industrial-park-imip",
        captive_fuel_type="coal_subcritical",
        overrides_df=overrides_df,
    )
    assert result == 50.0


def test_site_resolver_returns_default_for_unanchored_coal(overrides_df: pd.DataFrame) -> None:
    """A coal site without an override gets the default LCOE."""
    result = site_captive_coal_lcoe(
        site_id="some-unanchored-coal-site",
        captive_fuel_type="coal_subcritical",
        overrides_df=overrides_df,
    )
    assert result == pytest.approx(captive_coal_lcoe_usd_mwh(), abs=0.01)


def test_site_resolver_none_for_gas_site(overrides_df: pd.DataFrame) -> None:
    """A natural_gas site gets None on the coal column — no false positives."""
    result = site_captive_coal_lcoe(
        site_id="pupuk-kaltim-bontang",
        captive_fuel_type="natural_gas",
        overrides_df=overrides_df,
    )
    assert result is None


def test_site_resolver_none_for_none_fuel_type(overrides_df: pd.DataFrame) -> None:
    """Sites with captive_fuel_type='none' (e.g. grid-only Java cement) get NULL."""
    result = site_captive_coal_lcoe(
        site_id="kek-gresik",
        captive_fuel_type="none",
        overrides_df=overrides_df,
    )
    assert result is None


def test_site_resolver_none_for_missing_fuel_type(overrides_df: pd.DataFrame) -> None:
    """Defensive — None / NaN fuel_type returns None, doesn't crash."""
    assert site_captive_coal_lcoe("s", None, overrides_df) is None


# ─── Anchor classification helper ────────────────────────────────────────────


def test_is_coal_anchor_site_recognizes_all_five(overrides_df: pd.DataFrame) -> None:
    for sid in [
        "indonesia-morowali-industrial-park-imip",
        "industrial-weda-bay-industrial-park-iwip",
        "obi-island-industrial-park",
        "indonesia-konawe-industrial-park-ikip",
        "krakatau-posco-cilegon",
    ]:
        assert is_coal_anchor_site(sid, overrides_df), f"{sid} not flagged as coal anchor"


def test_is_coal_anchor_site_rejects_non_coal_overrides(overrides_df: pd.DataFrame) -> None:
    """Pupuk Kaltim is in the CSV with fuel_type=natural_gas — it must NOT
    be flagged as a coal anchor."""
    assert not is_coal_anchor_site("pupuk-kaltim-bontang", overrides_df)


def test_is_coal_anchor_site_rejects_random_site(overrides_df: pd.DataFrame) -> None:
    assert not is_coal_anchor_site("kek-palu", overrides_df)


# ─── Site_id format defensive check (eng-review finding A4) ──────────────────


def test_overrides_use_kebab_case_site_ids(overrides_df: pd.DataFrame) -> None:
    """A4: spec §4.4 lists overrides keyed by snake_case shorthand
    (imip_morowali, etc.); real dashboard site_ids are kebab-case.
    Pin so a future regression to snake_case fails loudly."""
    for site_id in overrides_df["site_id"]:
        assert "_" not in site_id, (
            f"Override site_id {site_id!r} contains underscore — "
            "must be kebab-case to match dim_sites.csv (#71 finding A4)"
        )
        assert "-" in site_id, f"Override site_id {site_id!r} not in kebab form"


def test_overrides_match_real_dim_sites_ids() -> None:
    """Every override site_id must exist in the production dim_sites table.
    Catches drift between spec shorthand and real ids."""
    real_csv = Path(__file__).parent.parent / "outputs" / "data" / "processed" / "dim_sites.csv"
    if not real_csv.exists():
        pytest.skip(f"dim_sites.csv not present at {real_csv}")
    real_ids = set(pd.read_csv(real_csv)["site_id"])
    overrides = load_captive_overrides()
    for sid in overrides["site_id"]:
        assert sid in real_ids, f"override site_id {sid!r} not in production dim_sites"


# ─── Scorecard integration ───────────────────────────────────────────────────


def test_scorecard_captive_coal_column_populated_for_anchors() -> None:
    """Integration: after running fct_site_scorecard, anchor sites carry
    their override LCOE in the captive_coal_lcoe_usd_mwh column."""
    scorecard_csv = (
        Path(__file__).parent.parent / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"
    )
    if not scorecard_csv.exists():
        pytest.skip(f"fct_site_scorecard.csv not present at {scorecard_csv}")
    df = pd.read_csv(scorecard_csv)
    if "captive_coal_lcoe_usd_mwh" not in df.columns:
        pytest.skip("captive_coal_lcoe_usd_mwh column not yet present in scorecard")
    by_id = df.set_index("site_id")["captive_coal_lcoe_usd_mwh"]
    assert by_id["indonesia-morowali-industrial-park-imip"] == 50.0
    assert by_id["industrial-weda-bay-industrial-park-iwip"] == 55.0
    assert by_id["obi-island-industrial-park"] == 60.0
    assert by_id["indonesia-konawe-industrial-park-ikip"] == 52.0
    assert by_id["krakatau-posco-cilegon"] == 48.0


def test_scorecard_captive_coal_null_for_non_coal_sites() -> None:
    """Java cement (grid_only, captive_fuel_type='none') must have NULL on
    the coal LCOE column."""
    scorecard_csv = (
        Path(__file__).parent.parent / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"
    )
    if not scorecard_csv.exists():
        pytest.skip(f"fct_site_scorecard.csv not present at {scorecard_csv}")
    df = pd.read_csv(scorecard_csv)
    if "captive_coal_lcoe_usd_mwh" not in df.columns:
        pytest.skip("captive_coal_lcoe_usd_mwh column not yet present in scorecard")
    # Grid-only Java cement sites should have NaN coal LCOE.
    java_cement = df[(df["sector"] == "cement") & (df["grid_region_id"] == "JAVA_BALI")][
        "captive_coal_lcoe_usd_mwh"
    ]
    assert java_cement.isna().all(), "Java cement should have null captive_coal_lcoe_usd_mwh"
    # Pupuk Kaltim (gas) should also be null on the coal column.
    pupuk = df[df["site_id"] == "pupuk-kaltim-bontang"]["captive_coal_lcoe_usd_mwh"].iloc[0]
    assert pd.isna(pupuk), "Pupuk Kaltim (gas) should have null captive_coal_lcoe_usd_mwh"
