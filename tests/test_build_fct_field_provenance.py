"""Tests for src/pipeline/build_fct_field_provenance.py.

Pipeline-level smoke for the v4.1a §9 provenance sidecar (#65).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.build_fct_field_provenance import build_fct_field_provenance


@pytest.fixture
def tmp_dim_sites(tmp_path: Path) -> Path:
    """Three-site synthetic dim_sites for testing the build step in isolation."""
    csv = tmp_path / "dim_sites.csv"
    pd.DataFrame(
        {
            "site_id": ["kek-palu", "kek-bitung", "kek-arun-lhokseumawe"],
            "site_name": ["KEK Palu", "KEK Bitung", "KEK Arun Lhokseumawe"],
        }
    ).to_csv(csv, index=False)
    return csv


def test_build_returns_dataframe_with_expected_schema(tmp_dim_sites: Path) -> None:
    df = build_fct_field_provenance(dim_sites_csv=tmp_dim_sites)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == [
        "site_id",
        "field_name",
        "source",
        "vintage",
        "confidence",
        "citation",
    ]


def test_row_count_equals_sites_times_registry_size(tmp_dim_sites: Path) -> None:
    from src.utils.provenance import PROVENANCE_REGISTRY

    df = build_fct_field_provenance(dim_sites_csv=tmp_dim_sites)
    assert len(df) == 3 * len(PROVENANCE_REGISTRY)


def test_sorted_by_site_then_field(tmp_dim_sites: Path) -> None:
    """Stable sort order keeps CSV diffs reviewable."""
    df = build_fct_field_provenance(dim_sites_csv=tmp_dim_sites)
    sorted_df = df.sort_values(["site_id", "field_name"], ignore_index=True)
    pd.testing.assert_frame_equal(df, sorted_df)


def test_every_row_has_finite_strings(tmp_dim_sites: Path) -> None:
    """No NaN, no empty strings — every cell must be a real citation token.
    Caught at the ProvenanceFlag dataclass level too, but pin at the
    pipeline-output level for the CSV consumers."""
    df = build_fct_field_provenance(dim_sites_csv=tmp_dim_sites)
    for col in ["source", "vintage", "confidence", "citation"]:
        assert df[col].notna().all(), f"NaN in column {col}"
        assert (df[col].astype(str).str.len() > 0).all(), f"Empty string in column {col}"


def test_confidence_values_are_canonical(tmp_dim_sites: Path) -> None:
    df = build_fct_field_provenance(dim_sites_csv=tmp_dim_sites)
    assert set(df["confidence"].unique()) <= {"high", "medium", "low"}


def test_against_real_dim_sites() -> None:
    """Integration: build against the real dim_sites.csv (81 sites). Confirms
    the production path produces a non-empty sidecar."""
    real_csv = Path(__file__).parent.parent / "outputs" / "data" / "processed" / "dim_sites.csv"
    if not real_csv.exists():
        pytest.skip(f"dim_sites.csv not present at {real_csv}")
    df = build_fct_field_provenance(dim_sites_csv=real_csv)
    assert len(df) > 0
    # 81 sites × 3 seed registry fields = 243 rows on this fixture.
    # If/when downstream sub-PRs add to the registry, this lower bound holds
    # and the exact count can be re-pinned per-release.
    assert len(df) >= 81 * 3
