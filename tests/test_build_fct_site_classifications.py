"""Tests for src/pipeline/build_fct_site_classifications.py.

Pin the v4.1a §3.1a + §3.2 logic (#70):
- 8 sector × region default rules from §3.2 produce the expected
  electricity_arrangement + captive_fuel_type pairs.
- Override CSV trumps defaults; sites without overrides fall back to
  default with `classification_confidence='medium'`.
- Resulting schema matches the §3.1a column subset (v4.1b additions
  explicitly out-of-scope here).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.build_fct_site_classifications import (
    CAPTIVE_FUEL_TYPES,
    CONFIDENCE_LEVELS,
    ELECTRICITY_ARRANGEMENTS,
    _default_classification,
    _derive_subsector,
    build_fct_site_classifications,
)

# Expected v4.1a §3.1a column subset (v4.1b adds export-share columns).
_EXPECTED_COLUMNS = [
    "site_id",
    "site_name",
    "sector",
    "subsector",
    "region",
    "grid_region",
    "electricity_arrangement",
    "captive_fuel_type",
    "captive_capacity_mw",
    "captive_share_estimated",
    "last_updated",
    "classification_confidence",
    "notes",
]


@pytest.fixture
def tmp_dim_sites(tmp_path: Path) -> Path:
    """Fixture covering every §3.2 default rule + a few edge cases."""
    csv = tmp_path / "dim_sites.csv"
    pd.DataFrame(
        {
            "site_id": [
                # Rule 1: Nickel Sulawesi/Maluku → pure_captive coal_subcritical
                "test-nickel-sulawesi",
                "test-nickel-maluku",
                # Rule 2: Aluminium all → hybrid_captive_primary hybrid
                "test-aluminium-sumatera",
                "test-aluminium-java",
                # Rule 3: Cement Java → grid_only none
                "test-cement-java",
                # Rule 4: Cement outside Java → grid_primary_with_captive coal_subcritical
                "test-cement-sumatera",
                # Rule 5: Fertilizer all → pure_captive natural_gas
                "test-fertilizer-java",
                "test-fertilizer-kalimantan",
                # Rule 6: Steel Java → grid_primary_with_captive natural_gas
                "test-steel-java",
                # Rule 7: Steel Sulawesi → pure_captive coal_subcritical
                "test-steel-sulawesi",
                # Rule 8a: KEK Java → grid_only none
                "test-kek-java",
                # Rule 8b: KEK Eastern Indonesia → pure_captive coal_subcritical
                "test-kek-papua",
                "test-kek-maluku",
                # KEK other → middle default
                "test-kek-sumatera",
            ],
            "site_name": [
                "Test Nickel Sulawesi",
                "Test Nickel Maluku",
                "Test Aluminium Sumatera",
                "Test Aluminium Java",
                "Test Cement Java",
                "Test Cement Sumatera",
                "Test Fertilizer Java",
                "Test Fertilizer Kalimantan",
                "Test Steel Java",
                "Test Steel Sulawesi",
                "Test KEK Java",
                "Test KEK Papua",
                "Test KEK Maluku",
                "Test KEK Sumatera",
            ],
            "site_type": [
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "standalone",
                "kek",
                "kek",
                "kek",
                "kek",
            ],
            "sector": [
                "nickel",
                "nickel",
                "aluminium",
                "aluminium",
                "cement",
                "cement",
                "fertilizer",
                "fertilizer",
                "steel",
                "steel",
                "mixed",
                "mixed",
                "mixed",
                "mixed",
            ],
            "primary_product": [
                "NPI",
                "Nickel Matte",
                "Aluminium ingots",
                "Aluminium ingots",
                "Cement",
                "Cement",
                "Urea + Ammonia",
                "Ammonia",
                "EAF steel billet",
                "BF-BOF integrated steel slab",
                "Mixed industrial",
                "Mixed industrial",
                "Mixed industrial",
                "Mixed industrial",
            ],
            "province": ["", "", "", "", "", "", "", "", "", "", "", "", "", ""],
            "grid_region_id": [
                "SULAWESI",
                "MALUKU",
                "SUMATERA",
                "JAVA_BALI",
                "JAVA_BALI",
                "SUMATERA",
                "JAVA_BALI",
                "KALIMANTAN",
                "JAVA_BALI",
                "SULAWESI",
                "JAVA_BALI",
                "PAPUA",
                "MALUKU",
                "SUMATERA",
            ],
        }
    ).to_csv(csv, index=False)
    return csv


def test_schema_matches_v4_1a_subset(tmp_dim_sites: Path) -> None:
    """v4.1b export-share columns must NOT appear in v4.1a output."""
    df = build_fct_site_classifications(
        dim_sites_csv=tmp_dim_sites, overrides_csv=Path("/nonexistent")
    )
    assert list(df.columns) == _EXPECTED_COLUMNS
    # Explicit v4.1b column exclusion guard
    for forbidden in [
        "export_market_shares_json",
        "export_market_shares_source",
        "export_market_shares_confidence",
        "cbam_exposed",
    ]:
        assert forbidden not in df.columns, f"v4.1b column {forbidden} leaked into v4.1a output"


def test_all_8_default_rules(tmp_dim_sites: Path) -> None:
    """§3.2 sector × region defaults — 8 rules, plus the KEK 'other' bucket."""
    df = build_fct_site_classifications(
        dim_sites_csv=tmp_dim_sites, overrides_csv=Path("/nonexistent")
    )
    df = df.set_index("site_id")

    # Rule 1: Nickel Sulawesi/Maluku
    for sid in ["test-nickel-sulawesi", "test-nickel-maluku"]:
        assert df.loc[sid, "electricity_arrangement"] == "pure_captive"
        assert df.loc[sid, "captive_fuel_type"] == "coal_subcritical"

    # Rule 2: Aluminium all
    for sid in ["test-aluminium-sumatera", "test-aluminium-java"]:
        assert df.loc[sid, "electricity_arrangement"] == "hybrid_captive_primary"
        assert df.loc[sid, "captive_fuel_type"] == "hybrid"

    # Rule 3: Cement Java
    assert df.loc["test-cement-java", "electricity_arrangement"] == "grid_only"
    assert df.loc["test-cement-java", "captive_fuel_type"] == "none"

    # Rule 4: Cement outside Java
    assert df.loc["test-cement-sumatera", "electricity_arrangement"] == "grid_primary_with_captive"
    assert df.loc["test-cement-sumatera", "captive_fuel_type"] == "coal_subcritical"

    # Rule 5: Fertilizer all
    for sid in ["test-fertilizer-java", "test-fertilizer-kalimantan"]:
        assert df.loc[sid, "electricity_arrangement"] == "pure_captive"
        assert df.loc[sid, "captive_fuel_type"] == "natural_gas"

    # Rule 6: Steel Java
    assert df.loc["test-steel-java", "electricity_arrangement"] == "grid_primary_with_captive"
    assert df.loc["test-steel-java", "captive_fuel_type"] == "natural_gas"

    # Rule 7: Steel Sulawesi
    assert df.loc["test-steel-sulawesi", "electricity_arrangement"] == "pure_captive"
    assert df.loc["test-steel-sulawesi", "captive_fuel_type"] == "coal_subcritical"

    # Rule 8a: KEK Java
    assert df.loc["test-kek-java", "electricity_arrangement"] == "grid_only"
    assert df.loc["test-kek-java", "captive_fuel_type"] == "none"

    # Rule 8b: KEK Eastern (Papua/Maluku/NTB)
    for sid in ["test-kek-papua", "test-kek-maluku"]:
        assert df.loc[sid, "electricity_arrangement"] == "pure_captive"
        assert df.loc[sid, "captive_fuel_type"] == "coal_subcritical"

    # KEK other (Sumatera) — grid_primary_with_captive default
    assert df.loc["test-kek-sumatera", "electricity_arrangement"] == "grid_primary_with_captive"


def test_default_confidence_is_medium(tmp_dim_sites: Path) -> None:
    """§3.2 — default-only rows get confidence='medium'."""
    df = build_fct_site_classifications(
        dim_sites_csv=tmp_dim_sites, overrides_csv=Path("/nonexistent")
    )
    # All rows are default-only — should all be medium.
    assert (df["classification_confidence"] == "medium").all()


def test_override_trumps_default(tmp_path: Path, tmp_dim_sites: Path) -> None:
    """A row in the overrides CSV must replace the default fields."""
    overrides = tmp_path / "overrides.csv"
    pd.DataFrame(
        {
            "site_id": ["test-cement-java"],
            "electricity_arrangement": ["pure_captive"],  # contradicts default 'grid_only'
            "captive_fuel_type": ["coal_subcritical"],
            "captive_capacity_mw": [150.0],
            "captive_share_estimated": [1.0],
            "classification_confidence": ["high"],
            "notes": ["Test override"],
        }
    ).to_csv(overrides, index=False)

    df = build_fct_site_classifications(dim_sites_csv=tmp_dim_sites, overrides_csv=overrides)
    overridden = df[df["site_id"] == "test-cement-java"].iloc[0]
    assert overridden["electricity_arrangement"] == "pure_captive"
    assert overridden["captive_fuel_type"] == "coal_subcritical"
    assert overridden["captive_capacity_mw"] == 150.0
    assert overridden["captive_share_estimated"] == 1.0
    assert overridden["classification_confidence"] == "high"
    assert overridden["notes"] == "Test override"

    # Other sites still on defaults — confidence stays medium.
    untouched = df[df["site_id"] == "test-nickel-sulawesi"].iloc[0]
    assert untouched["classification_confidence"] == "medium"


def test_default_classification_function_directly() -> None:
    """Direct unit test of the rule table function — covers each branch."""
    # Nickel
    assert _default_classification("nickel", "SULAWESI", "standalone") == {
        "electricity_arrangement": "pure_captive",
        "captive_fuel_type": "coal_subcritical",
    }
    # Aluminium
    assert _default_classification("aluminium", "JAVA_BALI", "standalone") == {
        "electricity_arrangement": "hybrid_captive_primary",
        "captive_fuel_type": "hybrid",
    }
    # Cement Java vs non-Java split
    assert (
        _default_classification("cement", "JAVA_BALI", "standalone")["electricity_arrangement"]
        == "grid_only"
    )
    assert (
        _default_classification("cement", "SUMATERA", "standalone")["electricity_arrangement"]
        == "grid_primary_with_captive"
    )
    # Fertilizer always gas
    for region in ["JAVA_BALI", "SUMATERA", "KALIMANTAN", "PAPUA"]:
        assert (
            _default_classification("fertilizer", region, "standalone")["captive_fuel_type"]
            == "natural_gas"
        )
    # Steel Java vs Sulawesi
    assert (
        _default_classification("steel", "JAVA_BALI", "standalone")["electricity_arrangement"]
        == "grid_primary_with_captive"
    )
    assert (
        _default_classification("steel", "SULAWESI", "standalone")["electricity_arrangement"]
        == "pure_captive"
    )
    # KEK split
    assert (
        _default_classification("mixed", "JAVA_BALI", "kek")["electricity_arrangement"]
        == "grid_only"
    )
    assert (
        _default_classification("mixed", "PAPUA", "kek")["electricity_arrangement"]
        == "pure_captive"
    )
    assert (
        _default_classification("mixed", "MALUKU", "kek")["electricity_arrangement"]
        == "pure_captive"
    )
    assert (
        _default_classification("mixed", "NTB", "kek")["electricity_arrangement"] == "pure_captive"
    )


def test_derive_subsector() -> None:
    """Subsector inference from primary_product strings."""
    assert _derive_subsector("nickel", "NPI Class 1") == "nickel_npi"
    assert _derive_subsector("nickel", "Nickel Matte 75%") == "nickel_matte"
    assert _derive_subsector("nickel", "MHP intermediate") == "nickel_matte"
    assert _derive_subsector("steel", "EAF billet rebar") == "steel_eaf"
    assert _derive_subsector("steel", "BF-BOF integrated slab") == "steel_bfbof"
    assert _derive_subsector("steel", "BF/BOF coil") == "steel_bfbof"
    assert _derive_subsector("fertilizer", "Anhydrous ammonia + urea") == "ammonia"
    assert _derive_subsector("fertilizer", "Urea fertilizer") == "fertilizer"
    # Empty / NaN-ish fallback returns sector
    assert _derive_subsector("cement", "") == "cement"
    assert _derive_subsector("cement", None) == "cement"


def test_enum_validation_passes_for_clean_inputs(tmp_dim_sites: Path) -> None:
    """Every emitted row's enum fields are in the valid sets."""
    df = build_fct_site_classifications(
        dim_sites_csv=tmp_dim_sites, overrides_csv=Path("/nonexistent")
    )
    assert df["electricity_arrangement"].isin(ELECTRICITY_ARRANGEMENTS).all()
    assert df["captive_fuel_type"].isin(CAPTIVE_FUEL_TYPES).all()
    assert df["classification_confidence"].isin(CONFIDENCE_LEVELS).all()


def test_enum_validation_fails_on_invalid_override(tmp_path: Path, tmp_dim_sites: Path) -> None:
    """Spec invariant — invalid enum values in the overrides CSV raise."""
    bad_overrides = tmp_path / "bad.csv"
    pd.DataFrame(
        {
            "site_id": ["test-cement-java"],
            "electricity_arrangement": ["something_invalid"],
            "captive_fuel_type": ["natural_gas"],
            "captive_capacity_mw": [None],
            "captive_share_estimated": [None],
            "classification_confidence": ["high"],
            "notes": ["bad override"],
        }
    ).to_csv(bad_overrides, index=False)
    with pytest.raises(ValueError, match="electricity_arrangement"):
        build_fct_site_classifications(dim_sites_csv=tmp_dim_sites, overrides_csv=bad_overrides)


def test_against_real_dim_sites() -> None:
    """Integration: every site in the production dim_sites gets a row."""
    real_csv = Path(__file__).parent.parent / "outputs" / "data" / "processed" / "dim_sites.csv"
    if not real_csv.exists():
        pytest.skip(f"dim_sites.csv not present at {real_csv}")
    dim_sites = pd.read_csv(real_csv)
    df = build_fct_site_classifications(dim_sites_csv=real_csv)
    assert len(df) == len(dim_sites)
    assert set(df["site_id"]) == set(dim_sites["site_id"])
    # Anchor sites should hit the §3.2 rules as expected.
    rows = df.set_index("site_id")
    assert (
        rows.loc["indonesia-morowali-industrial-park-imip", "electricity_arrangement"]
        == "pure_captive"
    )
    assert (
        rows.loc["indonesia-morowali-industrial-park-imip", "captive_fuel_type"]
        == "coal_subcritical"
    )
    assert rows.loc["pupuk-kaltim-bontang", "electricity_arrangement"] == "pure_captive"
    assert rows.loc["pupuk-kaltim-bontang", "captive_fuel_type"] == "natural_gas"
    # Java cement → grid_only
    java_cements = dim_sites[
        (dim_sites["sector"] == "cement") & (dim_sites["grid_region_id"] == "JAVA_BALI")
    ]
    for sid in java_cements["site_id"]:
        assert rows.loc[sid, "electricity_arrangement"] == "grid_only"
