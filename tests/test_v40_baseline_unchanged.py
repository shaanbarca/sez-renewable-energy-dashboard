"""Regression test: v4.0 LCOE column names preserved in v4.1+ output.

Per the additive migration plan (#66, METHODOLOGY §18.6): v4.1 adds new
IEA-named LCOE columns alongside the existing v4.0 columns. **No v4.0
columns are renamed or removed.** This test pins the column-presence
invariant — dropping any of these column names is a breaking change.

Value-level regression (every cell matches a known-good snapshot) is
covered by `tests/test_scorecard_golden.py`, which regenerates after every
methodology fix and locks the current production values. Here we only assert
the column-name contract that the additive migration story relies on.

If a downstream sub-PR genuinely needs to rename one of these columns, it
must:
1. Document the rename in `docs/METHODOLOGY_CONSOLIDATED.md` §18.6.
2. Flag it as a breaking change in CHANGELOG.md.
3. Update this test to drop the renamed column.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE_CSV = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_scorecard.csv"

# v4.0 LCOE-family column names that v4.1+ must preserve (additive migration).
# Sourced from a live `head -1` of fct_site_scorecard.csv before v4.1a began.
V40_LCOE_COLUMNS = (
    "lcoe_low_usd_mwh",
    "lcoe_mid_usd_mwh",
    "lcoe_high_usd_mwh",
    "lcoe_grid_connected_usd_mwh",
    "lcoe_grid_connected_capped_usd_mwh",
    "lcoe_grid_connected_low_usd_mwh",
    "lcoe_grid_connected_high_usd_mwh",
    "lcoe_wind_mid_usd_mwh",
    "lcoe_wind_allin_mid_usd_mwh",
    "best_re_lcoe_mid_usd_mwh",
    "lcoe_mid_wacc8_usd_mwh",
)
# Note: lcoe_within_boundary_usd_mwh and lcoe_with_battery_usd_mwh are
# live-API columns (returned by compute_scorecard_live, not persisted to
# fct_site_scorecard.csv). The live-API regression is covered by
# tests/test_api.py + the scorecard golden.


@pytest.fixture(scope="module")
def live_df() -> pd.DataFrame:
    if not LIVE_CSV.exists():
        pytest.skip("live scorecard missing — run `uv run python run_pipeline.py` first")
    return pd.read_csv(LIVE_CSV)


def test_every_v40_lcoe_column_still_present(live_df: pd.DataFrame) -> None:
    """Additive migration: v4.0 columns must STILL EXIST in v4.1 output.
    Renaming or dropping any of them is a breaking change. See METHODOLOGY §18.6."""
    missing = [c for c in V40_LCOE_COLUMNS if c not in live_df.columns]
    assert not missing, (
        f"v4.0 LCOE columns missing from v4.1 scorecard: {missing}. "
        f"v4.1 is additive — no v4.0 columns should be removed or renamed."
    )


def test_v40_columns_have_finite_values_for_at_least_some_sites(live_df: pd.DataFrame) -> None:
    """Smoke check that every v4.0 LCOE column still gets populated. NaN-only
    columns suggest the underlying pipeline step was accidentally turned off."""
    for col in V40_LCOE_COLUMNS:
        if col not in live_df.columns:
            continue  # caught by the other test
        finite = live_df[col].notna().sum()
        assert finite > 0, (
            f"Column {col} present but ALL values are NaN — pipeline step "
            "may have been disabled. Check src/dash/logic/lcoe.py."
        )


def test_naming_convention_no_per_mwh_in_lcoe_columns(live_df: pd.DataFrame) -> None:
    """The amended convention (§18.6) uses `_usd_mwh` not `_usd_per_mwh` for
    $/MWh columns. Pin so a new column doesn't accidentally drift convention."""
    bad = [c for c in live_df.columns if c.endswith("_usd_per_mwh")]
    assert not bad, (
        f"Found columns with '_usd_per_mwh' suffix: {bad}. "
        f"Convention (§18.6): use `_usd_mwh` for $/MWh; `_per_` is reserved for "
        f"per-kW / per-tonne / per-tCO2 denominators."
    )
