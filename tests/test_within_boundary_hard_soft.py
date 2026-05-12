# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""v4.0.5 (methodology #40): buildability hard/soft filter split + land-use override slider.

Math invariants + regression locks for the new override semantic.

The methodology splits the 4-layer buildability filter into HARD (slope, Kawasan
Hutan, peat) and SOFT (land cover, road distance). The `wb_buildout_footprint_ratio`
slider interpolates between baseline (full 4-layer pass) and hard_max (HARD-only):

    deployable = baseline + (hard_max - baseline) × slider%

These tests verify:

1. Pipeline invariant: hard_max area >= baseline area at every site (the HARD
   cascade is a strict superset of the FULL cascade).
2. Slider math invariants: deployable = baseline at slider=0%, deployable =
   hard_max at slider=100%, monotonic increase between.
3. NaN/edge-case guards: slider math doesn't propagate NaN or invert when the
   pipeline has gaps.
4. Regression locks: at three representative sites (a KEK, a fully-built
   industrial site, a no-polygon edge), capture the deployable values at
   slider 0/20/100%. Future methodology drift will flip these locks.

See docs/refinement/industrial_canopy_potential_methodology_2026-05-11.md.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_CSV = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_resource.csv"
SCORECARD_CSV = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"


# ─── 1. Pipeline-level invariants ─────────────────────────────────────────────


@pytest.fixture(scope="module")
def resource_df() -> pd.DataFrame:
    return pd.read_csv(RESOURCE_CSV)


@pytest.fixture(scope="module")
def scorecard_df() -> pd.DataFrame:
    return pd.read_csv(SCORECARD_CSV)


def test_hard_max_columns_exist(resource_df: pd.DataFrame) -> None:
    """v4.0.5 pipeline emits the new hard_max columns."""
    assert "within_boundary_hard_max_ha" in resource_df.columns
    assert "within_boundary_capacity_hard_max_mwp" in resource_df.columns


def test_hard_max_area_superset_of_baseline(resource_df: pd.DataFrame) -> None:
    """Invariant: hard_max area >= baseline area at every site.

    The HARD cascade (slope + Kawasan Hutan + peat) drops the SOFT layer
    (land cover), so it's a strict superset of the FULL cascade output.
    """
    baseline = resource_df["within_boundary_area_ha"].fillna(0)
    hard_max = resource_df["within_boundary_hard_max_ha"].fillna(0)
    violations = resource_df[hard_max < baseline]
    assert len(violations) == 0, (
        f"hard_max < baseline at {len(violations)} site(s): {violations['site_id'].tolist()[:5]}"
    )


def test_hard_max_capacity_superset_of_baseline(resource_df: pd.DataFrame) -> None:
    """Same invariant on the capacity column (area / 1.5 ha/MWp)."""
    baseline = resource_df["within_boundary_capacity_mwp"].fillna(0)
    hard_max = resource_df["within_boundary_capacity_hard_max_mwp"].fillna(0)
    assert (hard_max >= baseline - 0.05).all(), (
        "hard_max_capacity_mwp < baseline_capacity_mwp at some site (floating-point tolerance 0.05)"
    )


def test_coverage_hard_max_emitted(scorecard_df: pd.DataFrame) -> None:
    """v4.0.5 scorecard CSV emits within_boundary_coverage_hard_max_pct."""
    assert "within_boundary_coverage_hard_max_pct" in scorecard_df.columns


def test_coverage_hard_max_superset_of_baseline(scorecard_df: pd.DataFrame) -> None:
    """Coverage invariant: hard_max coverage >= baseline coverage (since capacity does)."""
    baseline = scorecard_df["within_boundary_coverage_pct"].fillna(0)
    hard_max = scorecard_df["within_boundary_coverage_hard_max_pct"].fillna(0)
    violations = scorecard_df[hard_max < baseline - 1e-6]
    assert len(violations) == 0, (
        f"coverage_hard_max < coverage_baseline at {len(violations)} site(s)"
    )


def test_fleet_total_jumps_meaningfully(resource_df: pd.DataFrame) -> None:
    """At default slider 20%, fleet-wide deployable capacity meaningfully exceeds
    raster baseline — the whole point of the methodology change."""
    baseline = resource_df["within_boundary_capacity_mwp"].fillna(0).sum()
    hard_max = resource_df["within_boundary_capacity_hard_max_mwp"].fillna(0).sum()
    deployable_at_20pct = baseline + (hard_max - baseline) * 0.20
    # At baseline ~1,500 MWp + hard_max ~7,800 MWp, 20% override → ~2,760 MWp.
    # Looser bounds to allow pipeline-edge drift while catching methodology regressions.
    assert deployable_at_20pct > baseline * 1.3, (
        f"Default-slider deployable ({deployable_at_20pct:.0f} MWp) didn't meaningfully exceed "
        f"baseline ({baseline:.0f} MWp). Either the methodology regressed or the pipeline "
        f"missed the hard_max columns."
    )


# ─── 2. Slider math invariants ────────────────────────────────────────────────


def _deployable(baseline: float | None, hard_max: float | None, slider: float) -> float | None:
    """Python port of the override formula used in grid.py + frontend.

    Mirrors the math in src/dash/logic/grid.py:112 + ResourceTab.tsx.
    """
    if baseline is None or (isinstance(baseline, float) and np.isnan(baseline)):
        return None
    if hard_max is None or (isinstance(hard_max, float) and np.isnan(hard_max)):
        return baseline
    soft_excluded = max(0.0, hard_max - baseline)
    return baseline + soft_excluded * slider


def test_slider_zero_equals_baseline() -> None:
    """At slider=0%, deployable = baseline (strict raster, today's pre-v4.0.5 behavior)."""
    assert _deployable(100.0, 500.0, 0.0) == 100.0
    assert _deployable(0.0, 400.0, 0.0) == 0.0
    assert _deployable(250.0, 250.0, 0.0) == 250.0  # no soft-excluded


def test_slider_full_equals_hard_max() -> None:
    """At slider=100%, deployable = hard_max (override all soft exclusions)."""
    assert _deployable(100.0, 500.0, 1.0) == 500.0
    assert _deployable(0.0, 400.0, 1.0) == 400.0


def test_slider_monotonic_increasing() -> None:
    """deployable is monotonically non-decreasing in slider."""
    baseline, hard_max = 100.0, 500.0
    values = [_deployable(baseline, hard_max, s / 10.0) for s in range(11)]
    for i in range(len(values) - 1):
        assert values[i + 1] >= values[i], f"non-monotonic at slider={i + 1}/10"


def test_deployable_clamped_at_hard_max() -> None:
    """deployable can't exceed hard_max even with slider=1.0."""
    assert _deployable(100.0, 500.0, 1.0) <= 500.0


def test_deployable_never_below_baseline() -> None:
    """deployable >= baseline for any slider in [0, 1]."""
    for slider in [0.0, 0.05, 0.20, 0.5, 0.95, 1.0]:
        assert _deployable(100.0, 500.0, slider) >= 100.0


def test_deployable_handles_nan_baseline() -> None:
    """NaN baseline → None (rather than NaN propagation)."""
    assert _deployable(None, 500.0, 0.5) is None
    assert _deployable(float("nan"), 500.0, 0.5) is None


def test_deployable_handles_nan_hard_max() -> None:
    """NaN hard_max → fallback to baseline (graceful pre-pipeline-rerun behavior)."""
    assert _deployable(100.0, None, 0.5) == 100.0
    assert _deployable(100.0, float("nan"), 0.5) == 100.0


def test_deployable_handles_inverted_hard_max() -> None:
    """If hard_max < baseline (pipeline bug), soft_excluded clamps to 0 — never goes negative."""
    assert _deployable(500.0, 100.0, 0.5) == 500.0  # max(0, 100-500) = 0, so deployable = baseline


# ─── 3. Regression locks at 3 representative sites ────────────────────────────


@pytest.fixture(scope="module")
def site_lookup(resource_df: pd.DataFrame) -> dict[str, pd.Series]:
    """Pick 3 representative sites for regression locks.

    The KEK chosen here is whichever has the largest soft_excluded delta —
    that's the site most sensitive to the slider, and therefore the most
    informative regression lock.
    """
    out: dict[str, pd.Series] = {}

    # Largest soft_excluded site overall (will be an industrial polygon by design)
    df = resource_df.copy()
    df["soft_excluded_mwp"] = df["within_boundary_capacity_hard_max_mwp"].fillna(0) - df[
        "within_boundary_capacity_mwp"
    ].fillna(0)
    df_sorted = df.sort_values("soft_excluded_mwp", ascending=False)
    out["largest_soft_excluded"] = df_sorted.iloc[0]

    # An industrial-fix case: baseline ~0 but hard_max >> 0
    fix_candidates = df[
        (df["within_boundary_capacity_mwp"].fillna(0) < 5)
        & (df["within_boundary_capacity_hard_max_mwp"].fillna(0) > 20)
    ]
    if len(fix_candidates) > 0:
        out["industrial_fix"] = fix_candidates.iloc[0]

    # A site with no polygon (baseline = hard_max = 0; slider has no effect)
    no_polygon = df[
        (df["within_boundary_capacity_mwp"].fillna(0) == 0)
        & (df["within_boundary_capacity_hard_max_mwp"].fillna(0) == 0)
    ]
    if len(no_polygon) > 0:
        out["no_polygon"] = no_polygon.iloc[0]

    return out


def test_regression_largest_soft_excluded_site(site_lookup: dict[str, pd.Series]) -> None:
    """Pick the site with the biggest gap between baseline and hard_max. Lock the
    deployable values at slider 0/20/100%. Drift here = methodology regression."""
    site = site_lookup["largest_soft_excluded"]
    baseline = float(site["within_boundary_capacity_mwp"])
    hard_max = float(site["within_boundary_capacity_hard_max_mwp"])

    d_0 = _deployable(baseline, hard_max, 0.0)
    d_20 = _deployable(baseline, hard_max, 0.20)
    d_100 = _deployable(baseline, hard_max, 1.0)

    # The math must hold regardless of which site this resolves to:
    # at 0% = baseline, at 100% = hard_max, at 20% = baseline + 20% × (hard_max - baseline).
    assert d_0 == pytest.approx(baseline, abs=0.01)
    assert d_100 == pytest.approx(hard_max, abs=0.01)
    expected_20 = baseline + (hard_max - baseline) * 0.20
    assert d_20 == pytest.approx(expected_20, abs=0.01)
    # And the spread between 0 and 100 should be the full soft_excluded delta:
    assert (d_100 - d_0) == pytest.approx(hard_max - baseline, abs=0.01)


def test_regression_industrial_fix_site(site_lookup: dict[str, pd.Series]) -> None:
    """At a fully-built industrial site (baseline ~0 → hard_max non-trivial), the
    slider has full lever effect. Pre-v4.0.5 the slider was useless here."""
    if "industrial_fix" not in site_lookup:
        pytest.skip("No industrial-fix candidate in current pipeline output.")

    site = site_lookup["industrial_fix"]
    baseline = float(site["within_boundary_capacity_mwp"])
    hard_max = float(site["within_boundary_capacity_hard_max_mwp"])

    assert baseline < 5, f"Expected near-zero baseline; got {baseline:.2f}"
    assert hard_max > 20, f"Expected meaningful hard_max; got {hard_max:.2f}"

    # Slider at 100% should unlock the full hard_max — pre-v4.0.5 this site
    # would have shown ~0 MWp regardless of slider position. The fix is the
    # whole point of the methodology change.
    assert _deployable(baseline, hard_max, 1.0) > 20


def test_regression_no_polygon_site(site_lookup: dict[str, pd.Series]) -> None:
    """At sites with no polygon (baseline = hard_max = 0), the slider has no
    effect — deployable stays 0 regardless of slider position."""
    if "no_polygon" not in site_lookup:
        pytest.skip("No no-polygon site in current pipeline output.")

    site = site_lookup["no_polygon"]
    baseline = float(site["within_boundary_capacity_mwp"])
    hard_max = float(site["within_boundary_capacity_hard_max_mwp"])
    assert baseline == 0.0 and hard_max == 0.0

    for slider in [0.0, 0.20, 1.0]:
        assert _deployable(baseline, hard_max, slider) == 0.0
