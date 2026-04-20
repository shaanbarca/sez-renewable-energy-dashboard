# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Tests for the RUPTL per-substation utilization signal (TODOS M11).

Covers:
  - Name normalization + placeholder filtering in build_fct_substation_ruptl_signal
  - Matcher ranking + voltage guard at the fuzzy threshold
  - Per-substation utilization lookup in build_fct_substation_proximity
  - End-to-end aggregation (strongest project_type, sum of MVA)
  - Slider override precedence in grid.py / lcoe.py
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.assumptions import (
    HOSTING_CAPACITY_AVAILABILITY_PCT,
    SUBSTATION_UTILIZATION_PCT,
    SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL,
)
from src.dash.logic.assumptions import UserAssumptions, get_default_assumptions
from src.dash.logic.grid import compute_grid_integration
from src.dash.logic.lcoe import compute_lcoe_live
from src.model.basic_model import capacity_assessment
from src.pipeline.build_fct_substation_proximity import _ruptl_utilization_for_substation
from src.pipeline.build_fct_substation_ruptl_signal import (
    build_fct_substation_ruptl_signal,
    is_placeholder,
    normalize_name,
    strongest_project_type,
    strongest_status,
    token_set_ratio,
)

# ─── Name normalization ───────────────────────────────────────────────────────


def test_normalize_name_strips_gi_prefix() -> None:
    assert normalize_name("GI Arun 150 kV") == "arun"
    assert normalize_name("GITET Sigli 275 kV") == "sigli"
    assert normalize_name("GIS Cibatu") == "cibatu"


def test_normalize_name_drops_trailing_single_digit() -> None:
    # "Parungmulya" == "Parungmulya 1" == "Parungmulya 2"
    assert normalize_name("Parungmulya") == normalize_name("Parungmulya 1")
    assert normalize_name("Parungmulya 1") == normalize_name("Parungmulya 2")


def test_normalize_name_drops_mva_annotation() -> None:
    # "(30 MVA No.1)" is noise, not part of the substation name
    assert normalize_name("Cikande (30 MVA No.1)") == "cikande"


def test_normalize_name_handles_alias_form() -> None:
    # "Teluk Jambe / Parungmulya" — alias form, prefer the multi-word half
    result = normalize_name("Teluk Jambe / Parungmulya")
    assert "teluk" in result or "parungmulya" in result


def test_normalize_name_empty_input() -> None:
    assert normalize_name("") == ""
    assert normalize_name(None) == ""  # type: ignore[arg-type]


# ─── Placeholder filter ───────────────────────────────────────────────────────


def test_is_placeholder_rejects_eksisting() -> None:
    assert is_placeholder("GI Eksisting Sumatera")
    assert is_placeholder("GI Eksisiting")  # RUPTL typo variant
    assert is_placeholder("GITET Tersebar")


def test_is_placeholder_accepts_real_names() -> None:
    assert not is_placeholder("GI Arun")
    assert not is_placeholder("GITET Sigli 275 kV")


def test_is_placeholder_handles_empty() -> None:
    assert is_placeholder("")
    assert is_placeholder(None)  # type: ignore[arg-type]


# ─── Ranking helpers ──────────────────────────────────────────────────────────


def test_strongest_project_type_prefers_uprate() -> None:
    assert strongest_project_type(["extension", "uprate", "line_bay"]) == "uprate"
    assert strongest_project_type(["line_bay", "extension"]) == "extension"
    assert strongest_project_type(["line_bay"]) == "line_bay"
    assert strongest_project_type([]) == "other"


def test_strongest_status_prefers_konstruksi() -> None:
    assert strongest_status(["rencana", "konstruksi", "pengadaan"]) == "konstruksi"
    assert strongest_status(["pengadaan", "rencana"]) == "pengadaan"
    assert strongest_status([]) == "other"


def test_token_set_ratio_exact_match() -> None:
    assert token_set_ratio("Arun", "Arun") == 1.0


def test_token_set_ratio_disjoint() -> None:
    assert token_set_ratio("Arun", "Sigli") == 0.0


def test_token_set_ratio_partial() -> None:
    # {"teluk","jambe"} vs {"teluk"} → 1 / 2
    assert token_set_ratio("Teluk Jambe", "Teluk") == pytest.approx(0.5)


# ─── Matcher + aggregation ────────────────────────────────────────────────────


def _ruptl_row(
    substation_name: str,
    grid_region_id: str = "SUMATERA",
    project_type: str = "uprate",
    mva_added: float = 60.0,
    status: str = "committed",
    voltage_primary_kv: int | None = 150,
    target_year_re_base: float = 2028.0,
    target_year_ared: float | None = None,
) -> dict:
    return {
        "substation_name": substation_name,
        "grid_region_id": grid_region_id,
        "project_type": project_type,
        "mva_added": mva_added,
        "status": status,
        "voltage_primary_kv": voltage_primary_kv,
        "target_year_re_base": target_year_re_base,
        "target_year_ared": target_year_ared,
    }


def _sub_row(
    namobj: str,
    regpln: str = "Sumatera",
    voltage_primary_kv: int = 150,
    kapgi_mva: float | None = 60.0,
) -> dict:
    return {
        "feature_idx": hash(namobj) % 10_000,
        "namobj": namobj,
        "regpln": regpln,
        "teggi_raw": f"{voltage_primary_kv} kV",
        "voltage_primary_kv": voltage_primary_kv,
        "kapgi_mva": kapgi_mva,
    }


def test_build_signal_exact_match_high_confidence() -> None:
    ruptl = pd.DataFrame([_ruptl_row("GI Arun", project_type="uprate", mva_added=60.0)])
    subs = pd.DataFrame([_sub_row("Arun")])
    result = build_fct_substation_ruptl_signal(ruptl, subs)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["namobj"] == "Arun"
    assert row["regpln"] == "Sumatera"
    assert row["has_planned_upgrade"]
    assert row["project_type_strongest"] == "uprate"
    assert row["mva_added_total"] == 60.0
    assert row["match_confidence"] == "high"


def test_build_signal_multiple_plans_same_substation_aggregate() -> None:
    ruptl = pd.DataFrame(
        [
            _ruptl_row("GI Arun", project_type="extension", mva_added=30.0),
            _ruptl_row("GI Arun", project_type="uprate", mva_added=60.0),
        ]
    )
    subs = pd.DataFrame([_sub_row("Arun")])
    result = build_fct_substation_ruptl_signal(ruptl, subs)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["project_type_strongest"] == "uprate"  # strongest wins
    assert row["mva_added_total"] == 90.0  # sum across plans


def test_build_signal_placeholder_rows_dropped() -> None:
    ruptl = pd.DataFrame(
        [
            _ruptl_row("GI Eksisting Sumatera"),
            _ruptl_row("GITET Tersebar"),
        ]
    )
    subs = pd.DataFrame([_sub_row("Arun")])
    result = build_fct_substation_ruptl_signal(ruptl, subs)
    assert result.empty


def test_build_signal_region_scoped() -> None:
    # RUPTL row in SUMATERA should not match a substation in Jawa-Bali
    ruptl = pd.DataFrame([_ruptl_row("GI Arun", grid_region_id="SUMATERA")])
    subs = pd.DataFrame([_sub_row("Arun", regpln="Jawa-Bali")])
    result = build_fct_substation_ruptl_signal(ruptl, subs)
    assert result.empty


# ─── Utilization lookup ───────────────────────────────────────────────────────


def _sig(
    project_type: str | None,
    has_planned_upgrade: bool = True,
    confidence: str | None = "high",
) -> dict:
    return {
        "has_planned_upgrade": has_planned_upgrade,
        "project_type_strongest": project_type,
        "strongest_status": "committed",
        "earliest_target_year": 2028,
        "mva_added_total": 60.0,
        "match_confidence": confidence,
    }


def test_ruptl_utilization_uprate_returns_85() -> None:
    lookup = {("Arun", "Sumatera"): _sig("uprate")}
    util, sig = _ruptl_utilization_for_substation("Arun", "Sumatera", lookup, fallback_pct=0.65)
    assert util == pytest.approx(0.85)
    assert sig is not None
    assert sig["project_type_strongest"] == "uprate"


def test_ruptl_utilization_extension_returns_75() -> None:
    lookup = {("Arun", "Sumatera"): _sig("extension")}
    util, _ = _ruptl_utilization_for_substation("Arun", "Sumatera", lookup, fallback_pct=0.65)
    assert util == pytest.approx(0.75)


def test_ruptl_utilization_line_bay_returns_70() -> None:
    lookup = {("Arun", "Sumatera"): _sig("line_bay")}
    util, _ = _ruptl_utilization_for_substation("Arun", "Sumatera", lookup, fallback_pct=0.65)
    assert util == pytest.approx(0.70)


def test_ruptl_utilization_matched_but_no_upgrade_returns_55() -> None:
    # has_planned_upgrade=False → "none" tier (55%)
    lookup = {("Arun", "Sumatera"): _sig(None, has_planned_upgrade=False)}
    util, sig = _ruptl_utilization_for_substation("Arun", "Sumatera", lookup, fallback_pct=0.65)
    assert util == pytest.approx(SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL["none"])
    assert sig is not None  # still returns the signal dict


def test_ruptl_utilization_unmatched_uses_fallback() -> None:
    # Substation absent from RUPTL lookup entirely → fleet fallback
    util, sig = _ruptl_utilization_for_substation("Ghost", "Sumatera", {}, fallback_pct=0.65)
    assert util == pytest.approx(0.65)
    assert sig is None


def test_ruptl_utilization_empty_inputs_use_fallback() -> None:
    util, sig = _ruptl_utilization_for_substation(None, None, {}, fallback_pct=0.65)
    assert util == pytest.approx(0.65)
    assert sig is None
    util, sig = _ruptl_utilization_for_substation("", "", {}, fallback_pct=0.65)
    assert util == pytest.approx(0.65)
    assert sig is None


def test_ruptl_utilization_unknown_project_type_falls_to_none() -> None:
    # Signal present but project_type not in the tier dict → "none" tier
    lookup = {("Arun", "Sumatera"): _sig("other")}
    util, _ = _ruptl_utilization_for_substation("Arun", "Sumatera", lookup, fallback_pct=0.65)
    assert util == pytest.approx(SUBSTATION_UTILIZATION_PCT_BY_RUPTL_SIGNAL["none"])


# ─── capacity_assessment with per-substation utilization ─────────────────────


@pytest.mark.parametrize(
    "utilization,expected_light",
    [
        # 100 MVA substation × (1 - util) × 0.85 PF vs 30 MWp solar.
        # util=0.85 → available 15 MVA × 0.85 = 12.75 MW < 15 (=0.5 × 30) → red
        # util=0.75 → available 25 MVA × 0.85 = 21.25 MW ≥ 15 (0.5×) but < 30 → yellow
        # util=0.55 → available 45 MVA × 0.85 = 38.25 MW ≥ 30 → green
        (0.85, "red"),
        (0.75, "yellow"),
        (0.55, "green"),
    ],
)
def test_capacity_assessment_utilization_sweep(utilization: float, expected_light: str) -> None:
    light, _avail = capacity_assessment(
        substation_capacity_mva=100.0,
        solar_capacity_mwp=30.0,
        utilization_pct=utilization,
    )
    assert light == expected_light


# ─── Slider override precedence in grid.py / lcoe.py ─────────────────────────


def _kek(**overrides) -> pd.Series:
    base = {
        "nearest_substation_capacity_mva": 100.0,
        "max_captive_capacity_mwp": 30.0,
        "has_internal_substation": False,
        "dist_solar_to_nearest_substation_km": 5.0,
        "dist_to_nearest_substation_km": 7.0,
        "inter_substation_connected": True,
        "within_boundary_coverage_pct": 0.0,
        "same_grid_region": True,
        "line_connected": True,
        "inter_substation_dist_km": 0.0,
        "nearest_substation_capacity_source": "actual",
        "substation_utilization_pct_effective": 0.85,  # RUPTL uprate tier
        "nearest_substation_name": "Arun",
        "ruptl_project_type": "uprate",
        "ruptl_strongest_status": "committed",
        "ruptl_earliest_target_year": 2028,
        "ruptl_mva_added_total": 60.0,
        "ruptl_match_confidence": "high",
    }
    base.update(overrides)
    return pd.Series(base)


def _gc_row(**overrides) -> pd.Series:
    base = {
        "connection_cost_per_kw": 105.0,
        "transmission_cost_per_kw": 25.0,
        "substation_upgrade_cost_per_kw": 12.0,
        "effective_capacity_mwp": 30.0,
    }
    base.update(overrides)
    return pd.Series(base)


def test_grid_slider_at_default_uses_ruptl_effective() -> None:
    """Slider at fleet default → per-site RUPTL tier drives capacity light."""
    out = compute_grid_integration(_kek(), _gc_row(), get_default_assumptions())
    # RUPTL effective util = 0.85 → available 15 MVA × 0.85 PF = 12.75 MW vs 30 MWp → red
    assert out["capacity_assessment"] == "red"
    assert out["substation_utilization_pct_effective"] == pytest.approx(0.85)
    # RUPTL passthroughs surface on the output dict for the ScoreDrawer
    assert out["ruptl_project_type"] == "uprate"
    assert out["ruptl_earliest_target_year"] == 2028


def test_grid_slider_off_default_overrides_ruptl() -> None:
    """Slider moved → uniform stress-test wins regardless of RUPTL tier."""
    assumptions = get_default_assumptions()
    assumptions.substation_utilization_pct = 0.55  # stress-test low
    out = compute_grid_integration(_kek(), _gc_row(), assumptions)
    # 0.55 util → available 45 MVA × 0.85 PF = 38.25 MW ≥ 30 MWp → green
    assert out["capacity_assessment"] == "green"
    assert out["substation_utilization_pct_effective"] == pytest.approx(0.55)


def test_grid_proxy_source_bypasses_ruptl_and_slider() -> None:
    """Proxy-source substations use 1 − HOSTING_CAPACITY_AVAILABILITY_PCT regardless."""
    expected = 1.0 - HOSTING_CAPACITY_AVAILABILITY_PCT
    kek = _kek(
        nearest_substation_capacity_source="proxy_150kV",
        substation_utilization_pct_effective=0.85,  # should be ignored
    )
    # Slider off default should also be ignored for proxy rows
    assumptions = get_default_assumptions()
    assumptions.substation_utilization_pct = 0.30
    out = compute_grid_integration(kek, _gc_row(), assumptions)
    assert out["substation_utilization_pct_effective"] == pytest.approx(expected)


def test_grid_missing_ruptl_effective_falls_back_to_default() -> None:
    """Actual-source row with no RUPTL effective column → default slider value."""
    kek = _kek(substation_utilization_pct_effective=None)
    out = compute_grid_integration(kek, _gc_row(), get_default_assumptions())
    assert out["substation_utilization_pct_effective"] == pytest.approx(SUBSTATION_UTILIZATION_PCT)


def _resource_row(**overrides) -> dict:
    base = {
        "site_id": "sample-site",
        "pvout_centroid": 1600.0,
        "pvout_best_50km": 1700.0,
        "pvout_buildable_best_50km": 1700.0,
        "dist_solar_to_nearest_substation_km": 5.0,
        "dist_to_nearest_substation_km": 7.0,
        "nearest_substation_capacity_mva": 60.0,
        "max_captive_capacity_mwp": 50.0,
        "project_scale_solar_mwp": 50.0,
        "inter_substation_connected": True,
        "inter_substation_dist_km": 0.0,
        "within_boundary_coverage_pct": 0.0,
        "substation_utilization_pct_effective": 0.85,  # RUPTL tight tier
        "nearest_substation_capacity_source": "actual",
    }
    base.update(overrides)
    return base


def test_lcoe_slider_at_default_uses_ruptl_for_upgrade_cost() -> None:
    """Slider at default → upgrade cost sized against RUPTL effective utilization."""
    resource = pd.DataFrame([_resource_row()])
    a = get_default_assumptions()
    result = compute_lcoe_live(resource, a, demand_by_site={"sample-site": 100_000.0})
    gc = result[result["scenario"] == "grid_connected_solar"].iloc[0]
    # With util=0.85, available capacity is tight → upgrade cost > 0
    assert gc["substation_upgrade_cost_per_kw"] > 0


def test_lcoe_slider_off_default_overrides_ruptl_for_upgrade_cost() -> None:
    """Slider moved to a headroom value → upgrade cost shrinks or zeroes."""
    resource = pd.DataFrame([_resource_row()])
    a_ruptl = get_default_assumptions()  # uses RUPTL 0.85
    a_loose = get_default_assumptions()
    a_loose.substation_utilization_pct = 0.40  # plenty of headroom
    up_ruptl = compute_lcoe_live(resource, a_ruptl, demand_by_site={"sample-site": 100_000.0})
    up_loose = compute_lcoe_live(resource, a_loose, demand_by_site={"sample-site": 100_000.0})
    ruptl_upgrade = up_ruptl[up_ruptl["scenario"] == "grid_connected_solar"].iloc[0][
        "substation_upgrade_cost_per_kw"
    ]
    loose_upgrade = up_loose[up_loose["scenario"] == "grid_connected_solar"].iloc[0][
        "substation_upgrade_cost_per_kw"
    ]
    assert loose_upgrade < ruptl_upgrade


def test_user_assumptions_default_matches_fleet_constant() -> None:
    """Regression guard: UserAssumptions default must equal the fleet constant.

    The slider-override check (`assumptions.substation_utilization_pct !=
    SUBSTATION_UTILIZATION_PCT`) only works when they start equal.
    """
    a = UserAssumptions()
    assert a.substation_utilization_pct == SUBSTATION_UTILIZATION_PCT
