# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Module-boundary tests for `src.dash.logic.cbam`.

Covers the 3-signal vs direct detection dispatch, type normalization, and the
CBAM cost-trajectory aggregator. These tests are intentionally shallow — the
scorecard-level behaviour is covered by the golden-master fixture.
"""

from __future__ import annotations

import pandas as pd

from src.dash.logic.cbam import _detect_cbam_types, _normalize_cbam_type, compute_cbam_trajectory


def test_normalize_cbam_iron_steel_dispatches_on_technology() -> None:
    assert _normalize_cbam_type("iron_steel", "RKEF") == "nickel_rkef"
    assert _normalize_cbam_type("iron_steel", "BF-BOF") == "steel_bfbof"
    assert _normalize_cbam_type("iron_steel", "EAF") == "steel_eaf"
    assert _normalize_cbam_type("iron_steel", "") == "steel_eaf"


def test_normalize_cbam_passthrough_for_other_types() -> None:
    assert _normalize_cbam_type("cement", "") == "cement"
    assert _normalize_cbam_type("aluminium", "") == "aluminium"
    assert _normalize_cbam_type("", "") is None


def test_detect_cbam_direct_mode_reads_dim_sites_column() -> None:
    kek = pd.Series(
        {
            "site_type": "standalone",
            "cbam_product_type": "cement",
            "technology": "",
        }
    )
    assert _detect_cbam_types(kek, {}) == ["cement"]


def test_detect_cbam_direct_mode_handles_comma_list() -> None:
    kek = pd.Series(
        {
            "site_type": "cluster",
            "cbam_product_type": "iron_steel,cement",
            "technology": "RKEF",
        }
    )
    assert _detect_cbam_types(kek, {}) == ["nickel_rkef", "cement"]


def test_detect_cbam_direct_mode_empty_returns_empty() -> None:
    kek = pd.Series({"site_type": "standalone", "cbam_product_type": "", "technology": ""})
    assert _detect_cbam_types(kek, {}) == []


def test_detect_cbam_kek_3signal_uses_process() -> None:
    kek = pd.Series(
        {
            "site_type": "kek",
            "steel_plant_count": 0,
            "cement_plant_count": 0,
            "business_sectors": "",
        }
    )
    row = {"dominant_process_type": "Nickel Pig Iron"}
    assert _detect_cbam_types(kek, row) == ["nickel_rkef"]


def test_detect_cbam_kek_3signal_combines_signals() -> None:
    kek = pd.Series(
        {
            "site_type": "kek",
            "steel_plant_count": 1,
            "steel_dominant_technology": "BF-BOF",
            "cement_plant_count": 1,
            "business_sectors": "Bauxite Industry",
        }
    )
    row = {"dominant_process_type": ""}
    result = _detect_cbam_types(kek, row)
    assert "steel_bfbof" in result
    assert "cement" in result
    assert "aluminium" in result


def test_compute_cbam_trajectory_empty_types() -> None:
    out = compute_cbam_trajectory([], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08)
    assert out["cbam_exposed"] is False
    assert out["cbam_product_type"] is None
    for year in (2026, 2030, 2034):
        assert out[f"cbam_cost_{year}_usd_per_tonne"] is None


def test_compute_cbam_trajectory_returns_full_year_set() -> None:
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08
    )
    assert out["cbam_exposed"] is True
    assert out["cbam_product_type"] == "cement"
    assert "cement" in out["cbam_per_product"]
    for year in (2026, 2030, 2034):
        assert out[f"cbam_cost_{year}_usd_per_tonne"] is not None
        assert out[f"cbam_savings_{year}_usd_per_tonne"] is not None


def test_compute_cbam_trajectory_cost_monotone_increasing_2026_to_2034() -> None:
    out = compute_cbam_trajectory(
        ["cement"], grid_ef_t_co2_mwh=0.8, cbam_price_eur=80.0, eur_usd_rate=1.08
    )
    assert out["cbam_cost_2026_usd_per_tonne"] <= out["cbam_cost_2030_usd_per_tonne"]
    assert out["cbam_cost_2030_usd_per_tonne"] <= out["cbam_cost_2034_usd_per_tonne"]
