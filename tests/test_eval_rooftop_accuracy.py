"""Tests for scripts/eval_rooftop_accuracy.py.

Synthetic-fixture tests covering all branches in the eval coverage diagram:
  - load_data: missing files, missing columns, empty CSVs
  - check_sector_ratio_band: small sample, zero-MWp rule, in-band, outlier, all-NaN
  - check_plant_area_band: in-band, below, above, no-polygon
  - format_report: HIGH/LOW priority output
  - main: exit-code semantics
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

# Add scripts/ to path so the script is importable as a module under test.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ruff: noqa: E402 (module-level import after path manipulation is intentional)
import eval_rooftop_accuracy as eval_rooftop  # type: ignore[import-not-found]

# ─── load_data ────────────────────────────────────────────────────────────


def test_load_data_missing_fct_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(eval_rooftop, "FCT_ROOFTOP", tmp_path / "nope.csv")
    with pytest.raises(FileNotFoundError, match="Missing"):
        eval_rooftop.load_data()


def test_load_data_missing_dim_sites_raises(tmp_path, monkeypatch):
    fct_path = tmp_path / "fct.csv"
    pd.DataFrame(
        {
            "site_id": ["a"],
            "site_name": ["A"],
            "rooftop_solar_mwp_potential": [1.0],
            "total_building_footprint_m2": [100.0],
        }
    ).to_csv(fct_path, index=False)
    monkeypatch.setattr(eval_rooftop, "FCT_ROOFTOP", fct_path)
    monkeypatch.setattr(eval_rooftop, "DIM_SITES", tmp_path / "nope.csv")
    with pytest.raises(FileNotFoundError, match="Missing"):
        eval_rooftop.load_data()


def test_load_data_missing_required_columns_raises(tmp_path, monkeypatch):
    fct_path = tmp_path / "fct.csv"
    sites_path = tmp_path / "dim.csv"
    pd.DataFrame({"site_id": ["a"]}).to_csv(fct_path, index=False)
    pd.DataFrame(
        {
            "site_id": ["a"],
            "sector": ["cement"],
            "site_type": ["standalone"],
            "capacity_annual_tonnes": [1000],
        }
    ).to_csv(sites_path, index=False)
    monkeypatch.setattr(eval_rooftop, "FCT_ROOFTOP", fct_path)
    monkeypatch.setattr(eval_rooftop, "DIM_SITES", sites_path)
    monkeypatch.setattr(eval_rooftop, "KEK_POLYGONS", tmp_path / "no_kek.geojson")
    monkeypatch.setattr(eval_rooftop, "INDUSTRIAL_POLYGONS", tmp_path / "no_ind.geojson")
    with pytest.raises(ValueError, match="missing columns"):
        eval_rooftop.load_data()


# ─── check_sector_ratio_band ─────────────────────────────────────────────


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_sector_band_skips_small_sample():
    """Aluminium n=2 → "manual review" LOW finding, no z-score band."""
    df = _make_df(
        [
            {
                "site_id": "a1",
                "site_name": "A1",
                "sector": "aluminium",
                "capacity_annual_tonnes": 250_000,
                "rooftop_solar_mwp_potential": 30.0,
                "total_building_footprint_m2": 100_000,
            },
            {
                "site_id": "a2",
                "site_name": "A2",
                "sector": "aluminium",
                "capacity_annual_tonnes": 300_000,
                "rooftop_solar_mwp_potential": 50.0,
                "total_building_footprint_m2": 100_000,
            },
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    assert len(findings) == 1
    assert findings[0]["priority"] == "info"
    assert findings[0]["check"] == "sector_sample_too_small"
    assert findings[0]["sector"] == "aluminium"


def test_sector_band_zero_mwp_rule_fires():
    """Operating site with capacity but ~zero MWp → HIGH-PRIORITY zero rule."""
    df = _make_df(
        [
            {
                "site_id": s,
                "site_name": s.upper(),
                "sector": "cement",
                "capacity_annual_tonnes": 1_000_000,
                "rooftop_solar_mwp_potential": v,
                "total_building_footprint_m2": 50_000,
            }
            for s, v in [
                ("ok-1", 10.0),
                ("ok-2", 12.0),
                ("ok-3", 11.0),
                ("ok-4", 9.0),
                ("zero", 0.0),
            ]
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    zero_findings = [f for f in findings if f["check"] == "zero_mwp_with_capacity"]
    assert len(zero_findings) == 1
    assert zero_findings[0]["priority"] == "actionable"
    assert zero_findings[0]["site_id"] == "zero"


def test_sector_band_in_band_no_finding():
    """All sites within 2σ of median → no outlier flags."""
    df = _make_df(
        [
            {
                "site_id": f"c{i}",
                "site_name": f"C{i}",
                "sector": "cement",
                "capacity_annual_tonnes": 1_000_000,
                "rooftop_solar_mwp_potential": 10.0 + i * 0.5,
                "total_building_footprint_m2": 50_000,
            }
            for i in range(5)
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    outliers = [
        f for f in findings if f["check"] in ("sector_outlier_above", "sector_outlier_below")
    ]
    assert outliers == []


def test_sector_band_outlier_above_threshold():
    """One site way above sector median → outlier_above (actionable)."""
    df = _make_df(
        [
            {
                "site_id": f"c{i}",
                "site_name": f"C{i}",
                "sector": "cement",
                "capacity_annual_tonnes": 1_000_000,
                "rooftop_solar_mwp_potential": v,
                "total_building_footprint_m2": 50_000,
            }
            for i, v in enumerate([10.0, 11.0, 10.5, 11.5, 200.0])
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    above = [f for f in findings if f["check"] == "sector_outlier_above"]
    below = [f for f in findings if f["check"] == "sector_outlier_below"]
    assert len(above) >= 1
    assert len(below) == 0  # no site below median by >2σ in this fixture
    # The wildly-high site should be flagged with positive z.
    flagged_ids = {f["site_id"] for f in above}
    assert "c4" in flagged_ids
    assert above[0]["z_score"] > 0
    assert above[0]["priority"] == "actionable"


def test_sector_band_outlier_below_threshold():
    """One site way below sector median → outlier_below (actionable).

    Direction matters — bleed (above) and undercount (below) need different
    fixes. The eval used to lump these into a single 'sector_ratio_outlier'
    flag; now they're separate so the report can route each correctly.
    """
    df = _make_df(
        [
            {
                "site_id": f"c{i}",
                "site_name": f"C{i}",
                "sector": "cement",
                "capacity_annual_tonnes": 1_000_000,
                "rooftop_solar_mwp_potential": v,
                "total_building_footprint_m2": 50_000,
            }
            for i, v in enumerate([100.0, 110.0, 105.0, 115.0, 0.5])
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    below = [f for f in findings if f["check"] == "sector_outlier_below"]
    assert len(below) == 1
    assert below[0]["site_id"] == "c4"
    assert below[0]["z_score"] < 0
    assert below[0]["priority"] == "actionable"


def test_sector_band_kek_with_nan_capacity_skipped():
    """KEKs have NaN capacity_annual_tonnes — must not raise, must be skipped."""
    df = _make_df(
        [
            {
                "site_id": "kek-1",
                "site_name": "KEK 1",
                "sector": "mixed",
                "capacity_annual_tonnes": None,  # NaN after CSV roundtrip; pandas treats None as NaN
                "rooftop_solar_mwp_potential": 5.0,
                "total_building_footprint_m2": 10_000,
            },
            {
                "site_id": "kek-2",
                "site_name": "KEK 2",
                "sector": "mixed",
                "capacity_annual_tonnes": None,
                "rooftop_solar_mwp_potential": 8.0,
                "total_building_footprint_m2": 20_000,
            },
        ]
    )
    findings = eval_rooftop.check_sector_ratio_band(df)
    # KEKs filtered out at the rated step → no findings of any kind for them.
    assert all(f.get("site_id") not in {"kek-1", "kek-2"} for f in findings if f.get("site_id"))


# ─── check_plant_area_band ───────────────────────────────────────────────


def _make_polys(items: list[tuple[str, Polygon]]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"site_id": [sid for sid, _ in items], "geometry": [g for _, g in items]},
        crs="EPSG:4326",
    )


def _square_around(lat: float, lon: float, half_deg: float) -> Polygon:
    return Polygon(
        [
            (lon - half_deg, lat - half_deg),
            (lon + half_deg, lat - half_deg),
            (lon + half_deg, lat + half_deg),
            (lon - half_deg, lat + half_deg),
        ]
    )


def _industrial(site_id: str, **overrides) -> dict:
    """Helper: standalone industrial site with sensible defaults."""
    base = {
        "site_id": site_id,
        "site_name": site_id.upper(),
        "sector": "cement",
        "site_type": "standalone",
        "capacity_annual_tonnes": 1_000_000,
        "rooftop_solar_mwp_potential": 10.0,
        "total_building_footprint_m2": 50_000,
    }
    base.update(overrides)
    return base


def test_plant_area_band_in_band_no_finding():
    """10% footprint ratio → in band [5, 30], no finding."""
    poly = _square_around(-6.5, 107.0, 0.005)  # ~1.1 km on a side ≈ 1.21 km² ≈ 1.21M m²
    polys = _make_polys([("p1", poly)])
    # Target ratio ≈ 10% → footprint ≈ 0.10 × polygon area
    polygon_area_m2 = polys.to_crs("EPSG:23830").geometry.area.iloc[0]
    df = _make_df([_industrial("p1", total_building_footprint_m2=0.10 * polygon_area_m2)])
    findings, n_covered, n_total = eval_rooftop.check_plant_area_band(df, polys)
    assert findings == []
    assert n_covered == 1
    assert n_total == 1


def test_plant_area_band_below_low_flags():
    """Footprint at 1% of polygon → below 5% floor → HIGH finding."""
    poly = _square_around(-6.5, 107.0, 0.005)
    polys = _make_polys([("p1", poly)])
    polygon_area_m2 = polys.to_crs("EPSG:23830").geometry.area.iloc[0]
    df = _make_df(
        [
            _industrial(
                "p1",
                rooftop_solar_mwp_potential=1.0,
                total_building_footprint_m2=0.01 * polygon_area_m2,
            )
        ]
    )
    findings, _, _ = eval_rooftop.check_plant_area_band(df, polys)
    assert len(findings) == 1
    assert findings[0]["check"] == "footprint_below_band"
    assert findings[0]["priority"] == "review"


def test_plant_area_band_above_high_flags():
    """Footprint at 50% of polygon → above 30% ceiling → HIGH finding."""
    poly = _square_around(-6.5, 107.0, 0.005)
    polys = _make_polys([("p1", poly)])
    polygon_area_m2 = polys.to_crs("EPSG:23830").geometry.area.iloc[0]
    df = _make_df(
        [
            _industrial(
                "p1",
                rooftop_solar_mwp_potential=50.0,
                total_building_footprint_m2=0.50 * polygon_area_m2,
            )
        ]
    )
    findings, _, _ = eval_rooftop.check_plant_area_band(df, polys)
    assert len(findings) == 1
    assert findings[0]["check"] == "footprint_above_band"
    assert findings[0]["priority"] == "review"


def test_plant_area_band_no_polygon_skipped_and_counted():
    """Industrial site without polygon → no finding, counted as uncovered."""
    polys = _make_polys([])
    df = _make_df([_industrial("no-poly")])
    findings, n_covered, n_total = eval_rooftop.check_plant_area_band(df, polys)
    assert findings == []
    assert n_covered == 0
    assert n_total == 1


def test_plant_area_band_kek_skipped():
    """KEK sites are mostly-empty zones by design — skipped from band check.

    Without this skip, every KEK with a small built area would flag below
    5% (Industropolis Batang at 0.1%, Mandalika at 0%, etc.) — true but
    not actionable.
    """
    poly = _square_around(-6.5, 107.0, 0.005)
    polys = _make_polys([("kek-empty", poly)])
    polygon_area_m2 = polys.to_crs("EPSG:23830").geometry.area.iloc[0]
    df = _make_df(
        [
            _industrial(
                "kek-empty",
                site_type="kek",
                sector="mixed",
                capacity_annual_tonnes=None,
                rooftop_solar_mwp_potential=0.5,
                total_building_footprint_m2=0.001 * polygon_area_m2,
            )
        ]
    )
    findings, n_covered, n_total = eval_rooftop.check_plant_area_band(df, polys)
    assert findings == []
    # KEK is excluded from eligible set so it doesn't count toward total either.
    assert n_total == 0


# ─── format_report + main exit-code ──────────────────────────────────────


def test_format_report_high_priority_visible():
    findings = [
        {
            "check": "zero_mwp_with_capacity",
            "priority": "actionable",
            "site_id": "x",
            "site_name": "X Plant",
            "reason": "operating with no rooftop",
        }
    ]
    out = eval_rooftop.format_report(findings, (5, 10))
    assert "HIGH-PRIORITY" in out  # top-level summary still uses this label
    assert "ZERO ROOFTOP" in out  # new descriptive group header
    assert "X Plant" in out
    assert "5/10" in out


def test_format_report_groups_above_and_below_separately():
    """Above and below outliers must render under distinct headers — same
    flag would conflate two opposite root causes."""
    findings = [
        {
            "check": "sector_outlier_above",
            "priority": "actionable",
            "site_id": "high",
            "site_name": "High Plant",
            "reason": "ratio +4σ vs median",
        },
        {
            "check": "sector_outlier_below",
            "priority": "actionable",
            "site_id": "low",
            "site_name": "Low Plant",
            "reason": "ratio -3σ vs median",
        },
    ]
    out = eval_rooftop.format_report(findings, (0, 0))
    assert "SECTOR OUTLIER (above)" in out
    assert "SECTOR OUTLIER (below)" in out
    assert "High Plant" in out
    assert "Low Plant" in out


def test_main_exit_code_zero_when_clean(tmp_path, monkeypatch):
    """No HIGH findings → exit 0 → CI passes."""
    fct_path = tmp_path / "fct.csv"
    sites_path = tmp_path / "dim.csv"
    pd.DataFrame(
        {
            "site_id": ["a", "b", "c", "d"],
            "site_name": ["A", "B", "C", "D"],
            "rooftop_solar_mwp_potential": [10.0, 11.0, 10.5, 11.5],
            "total_building_footprint_m2": [50_000] * 4,
        }
    ).to_csv(fct_path, index=False)
    pd.DataFrame(
        {
            "site_id": ["a", "b", "c", "d"],
            "sector": ["cement"] * 4,
            "site_type": ["standalone"] * 4,
            "capacity_annual_tonnes": [1_000_000] * 4,
        }
    ).to_csv(sites_path, index=False)
    monkeypatch.setattr(eval_rooftop, "FCT_ROOFTOP", fct_path)
    monkeypatch.setattr(eval_rooftop, "DIM_SITES", sites_path)
    monkeypatch.setattr(eval_rooftop, "KEK_POLYGONS", tmp_path / "no_kek.geojson")
    monkeypatch.setattr(eval_rooftop, "INDUSTRIAL_POLYGONS", tmp_path / "no_ind.geojson")
    monkeypatch.setattr(eval_rooftop, "EVAL_HIST_PATH", str(tmp_path / "history.jsonl"))
    rc = eval_rooftop.main()
    assert rc == 0


def test_main_exit_code_one_when_high_finding(tmp_path, monkeypatch):
    """One zero-MWp HIGH finding → exit 1 → CI fails."""
    fct_path = tmp_path / "fct.csv"
    sites_path = tmp_path / "dim.csv"
    pd.DataFrame(
        {
            "site_id": ["a", "b", "c", "d", "zero"],
            "site_name": ["A", "B", "C", "D", "ZERO"],
            "rooftop_solar_mwp_potential": [10.0, 11.0, 10.5, 11.5, 0.0],
            "total_building_footprint_m2": [50_000] * 5,
        }
    ).to_csv(fct_path, index=False)
    pd.DataFrame(
        {
            "site_id": ["a", "b", "c", "d", "zero"],
            "sector": ["cement"] * 5,
            "site_type": ["standalone"] * 5,
            "capacity_annual_tonnes": [1_000_000] * 5,
        }
    ).to_csv(sites_path, index=False)
    monkeypatch.setattr(eval_rooftop, "FCT_ROOFTOP", fct_path)
    monkeypatch.setattr(eval_rooftop, "DIM_SITES", sites_path)
    monkeypatch.setattr(eval_rooftop, "KEK_POLYGONS", tmp_path / "no_kek.geojson")
    monkeypatch.setattr(eval_rooftop, "INDUSTRIAL_POLYGONS", tmp_path / "no_ind.geojson")
    monkeypatch.setattr(eval_rooftop, "EVAL_HIST_PATH", str(tmp_path / "history.jsonl"))
    rc = eval_rooftop.main()
    assert rc == 1
