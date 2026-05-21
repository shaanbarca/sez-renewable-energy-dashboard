"""Schema + invariant tests for v4.1b CBAM datasets.

These tests catch CSV / dict drift that would break the destination-weighted
CBAM logic in sub-PR (d). They run on every PR — schema failures here mean
no CBAM number is trustworthy downstream.

Covers spec §3.3 (EXPORT_MARKET_SHARES_BY_SUBSECTOR), §3.4 (site overrides
CSV), §3.5 (CARBON_PRICE_BY_MARKET), and the PROCESS_TO_SUBSECTOR mapping.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.assumptions import (
    CARBON_PRICE_BY_MARKET,
    EXPORT_MARKET_IDS,
    EXPORT_MARKET_SHARES_BY_SUBSECTOR,
    PROCESS_TO_SUBSECTOR,
)
from src.dash.data_loader import DataLoadError, load_export_shares_overrides

REPO_ROOT = Path(__file__).resolve().parents[1]
OVERRIDES_CSV = REPO_ROOT / "data" / "raw" / "site_export_shares_overrides.csv"


# ─── EXPORT_MARKET_SHARES_BY_SUBSECTOR (spec §3.3) ─────────────────────────


def test_subsector_shares_sum_to_one():
    """Every subsector's market share dict must sum to 1.0 ± 0.001."""
    for subsector, shares in EXPORT_MARKET_SHARES_BY_SUBSECTOR.items():
        total = sum(shares.values())
        assert abs(total - 1.0) < 0.001, (
            f"{subsector!r} shares sum to {total:.4f}, expected 1.0 ± 0.001"
        )


def test_every_subsector_market_id_is_valid():
    """Every market_id referenced by a subsector must exist in CARBON_PRICE_BY_MARKET.

    A typo in a market_id silently breaks destination-weighted CBAM at runtime
    (the carbon-adder lookup returns 0 for unknown markets). This catches at CI.
    """
    for subsector, shares in EXPORT_MARKET_SHARES_BY_SUBSECTOR.items():
        for market_id in shares:
            assert market_id in EXPORT_MARKET_IDS, (
                f"{subsector!r} references unknown market_id {market_id!r}; "
                f"valid markets: {sorted(EXPORT_MARKET_IDS)}"
            )


def test_all_eight_spec_subsectors_present():
    """Spec §3.3 lists 8 subsectors — all must be present."""
    expected = {
        "nickel_npi",
        "nickel_matte",
        "steel_eaf",
        "steel_bfbof",
        "aluminium",
        "cement",
        "fertilizer",
        "ammonia",
    }
    assert set(EXPORT_MARKET_SHARES_BY_SUBSECTOR.keys()) == expected


def test_no_negative_shares():
    """Shares must be in [0, 1]."""
    for subsector, shares in EXPORT_MARKET_SHARES_BY_SUBSECTOR.items():
        for market_id, share in shares.items():
            assert 0.0 <= share <= 1.0, (
                f"{subsector}/{market_id} share = {share}, expected in [0, 1]"
            )


# ─── CARBON_PRICE_BY_MARKET (spec §3.5) ─────────────────────────────────────


def test_carbon_price_anchor_years_present():
    """Spec §3.5 requires snapshot prices for 2025, 2030, 2034."""
    for market_id, trajectory in CARBON_PRICE_BY_MARKET.items():
        assert set(trajectory.keys()) >= {2025, 2030, 2034}, (
            f"{market_id} missing snapshot years; got {sorted(trajectory.keys())}"
        )


def test_carbon_price_monotonic_non_decreasing():
    """Carbon prices must rise (or stay flat) across snapshot years.

    A market price that falls 2025 → 2030 → 2034 would imply policy reversal
    not currently in any forecast. Locked as an invariant; if a real scenario
    needs decreasing prices (e.g. ETS oversupply), revisit explicitly.
    """
    for market_id, trajectory in CARBON_PRICE_BY_MARKET.items():
        years = sorted(trajectory.keys())
        for prev, curr in zip(years, years[1:], strict=False):
            assert trajectory[curr] >= trajectory[prev], (
                f"{market_id} carbon price drops {prev}→{curr}: "
                f"${trajectory[prev]} → ${trajectory[curr]}"
            )


def test_carbon_price_anchors_match_spec_74():
    """Spec §7.4 IMIP worked example anchors. Drift breaks the headline 4× error claim."""
    assert CARBON_PRICE_BY_MARKET["china_stainless"][2025] == 12.0
    assert CARBON_PRICE_BY_MARKET["battery_supply_chain_eu_oem"][2025] == 90.0
    assert CARBON_PRICE_BY_MARKET["direct_eu_uk_us"][2025] == 90.0
    assert CARBON_PRICE_BY_MARKET["china_stainless"][2030] == 30.0
    assert CARBON_PRICE_BY_MARKET["battery_supply_chain_eu_oem"][2030] == 150.0
    assert CARBON_PRICE_BY_MARKET["direct_eu_uk_us"][2030] == 140.0


def test_every_market_referenced_by_at_least_one_subsector():
    """A market in CARBON_PRICE_BY_MARKET that no subsector uses is dead code.

    Either remove it or wire it into a subsector's share dict. Catches drift
    where a market gets added speculatively but never integrated.
    """
    referenced: set[str] = set()
    for shares in EXPORT_MARKET_SHARES_BY_SUBSECTOR.values():
        referenced.update(shares.keys())
    unreferenced = EXPORT_MARKET_IDS - referenced
    assert not unreferenced, f"Markets defined but unused: {sorted(unreferenced)}"


# ─── PROCESS_TO_SUBSECTOR mapping (codes alignment) ─────────────────────────


def test_process_to_subsector_targets_exist():
    """Every value in PROCESS_TO_SUBSECTOR must be a valid subsector key."""
    valid_subsectors = set(EXPORT_MARKET_SHARES_BY_SUBSECTOR.keys())
    for process, subsector in PROCESS_TO_SUBSECTOR.items():
        assert subsector in valid_subsectors, (
            f"PROCESS_TO_SUBSECTOR[{process!r}] = {subsector!r} not in "
            f"EXPORT_MARKET_SHARES_BY_SUBSECTOR"
        )


# ─── Site overrides CSV (spec §3.4) ─────────────────────────────────────────


def test_overrides_csv_exists():
    assert OVERRIDES_CSV.exists(), f"Override CSV missing at {OVERRIDES_CSV}"


def test_overrides_csv_schema():
    df = pd.read_csv(OVERRIDES_CSV)
    expected_cols = {"site_id", "market_id", "share", "source", "last_updated"}
    assert expected_cols.issubset(set(df.columns)), (
        f"Missing columns: {expected_cols - set(df.columns)}"
    )


def test_overrides_per_site_shares_sum_to_one():
    df = pd.read_csv(OVERRIDES_CSV)
    for site_id, group in df.groupby("site_id"):
        total = group["share"].sum()
        assert abs(total - 1.0) < 0.001, (
            f"{site_id} override shares sum to {total:.4f}, expected 1.0 ± 0.001"
        )


def test_overrides_market_ids_valid():
    df = pd.read_csv(OVERRIDES_CSV)
    for market_id in df["market_id"].unique():
        assert market_id in EXPORT_MARKET_IDS, (
            f"Override references unknown market_id {market_id!r}; "
            f"valid markets: {sorted(EXPORT_MARKET_IDS)}"
        )


def test_overrides_loader_returns_nested_dict():
    """load_export_shares_overrides should produce the dict shape sub-PR (d) consumes."""
    overrides = load_export_shares_overrides()
    assert isinstance(overrides, dict)
    # IMIP is the spec §7.4 worked example anchor — must be present
    assert "indonesia-morowali-industrial-park-imip" in overrides
    imip_shares = overrides["indonesia-morowali-industrial-park-imip"]
    assert imip_shares["china_stainless"] == pytest.approx(0.50)
    assert imip_shares["battery_supply_chain_eu_oem"] == pytest.approx(0.35)
    assert imip_shares["direct_eu_uk_us"] == pytest.approx(0.15)


def test_overrides_loader_rejects_bad_sums(tmp_path: Path):
    """Loader must raise DataLoadError when a site's shares don't sum to 1.0."""
    bad_csv = tmp_path / "site_export_shares_overrides.csv"
    bad_csv.write_text(
        "site_id,market_id,share,source,last_updated\n"
        "bad-site,china_stainless,0.3,test,2024-01-01\n"
        "bad-site,direct_eu_uk_us,0.4,test,2024-01-01\n"
    )
    with pytest.raises(DataLoadError, match="sum to 0.7000"):
        load_export_shares_overrides(raw_dir=tmp_path)


def test_overrides_loader_returns_empty_when_missing(tmp_path: Path):
    """Loader gracefully degrades when the override CSV is absent."""
    out = load_export_shares_overrides(raw_dir=tmp_path)
    assert out == {}
