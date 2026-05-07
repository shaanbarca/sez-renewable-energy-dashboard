"""Tests for the CostBasis enum (TAXONOMY §6.5)."""

from __future__ import annotations

from src.model import CostBasis
from src.model.basic_model import CostBasis as CostBasisDirect


def test_cost_basis_values():
    assert CostBasis.RAW == "raw"
    assert CostBasis.FIRMED == "firmed"
    assert CostBasis.DELIVERED == "delivered"
    assert CostBasis.FIRMED_24_7_SOLAR_ONLY == "firmed_24_7_solar_only"


def test_cost_basis_count():
    # 4 members as of F1 (2026-05-07): RAW, FIRMED, DELIVERED, FIRMED_24_7_SOLAR_ONLY.
    assert len(list(CostBasis)) == 4


def test_cost_basis_is_reexported():
    assert CostBasis is CostBasisDirect


def test_cost_basis_str_comparison():
    assert CostBasis.RAW == "raw"
    d = {CostBasis.FIRMED: "T2"}
    assert d["firmed"] == "T2"


def test_cost_basis_matches_taxonomy():
    """Members map 1:1 to the TAXONOMY §7.3 resolver matrix columns + F1 sanity-check basis."""
    assert {c.value for c in CostBasis} == {
        "raw",
        "firmed",
        "delivered",
        "firmed_24_7_solar_only",  # F1: solar+12h-battery sanity-check baseline
    }
