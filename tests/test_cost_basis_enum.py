"""Tests for the CostBasis enum (TAXONOMY §6.5)."""

from __future__ import annotations

from src.model import CostBasis
from src.model.basic_model import CostBasis as CostBasisDirect


def test_cost_basis_values():
    assert CostBasis.RAW == "raw"
    assert CostBasis.FIRMED == "firmed"
    assert CostBasis.DELIVERED == "delivered"


def test_cost_basis_count():
    assert len(list(CostBasis)) == 3


def test_cost_basis_is_reexported():
    assert CostBasis is CostBasisDirect


def test_cost_basis_str_comparison():
    assert CostBasis.RAW == "raw"
    d = {CostBasis.FIRMED: "T2"}
    assert d["firmed"] == "T2"


def test_cost_basis_matches_taxonomy():
    """Members map 1:1 to the TAXONOMY §7.3 resolver matrix columns (raw/firmed/delivered)."""
    assert {c.value for c in CostBasis} == {"raw", "firmed", "delivered"}
