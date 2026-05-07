# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""Lock test: tests/fixtures/scorecard_v4_0_baseline.csv must not change silently.

Distinct purpose from tests/test_scorecard_golden.py:
  - scorecard_golden.pkl  = "current expected output" — updated when code intentionally
    changes scorecard semantics (e.g., during a refactor or feature add).
  - scorecard_v4_0_baseline.csv = "frozen at v4.0" — the reference snapshot the
    refinement releases (v4.0.5, v4.1a, v4.1b, v4.2) write release-shift reports
    against. NEVER updated as features land — stays as the v4.0 boundary forever.

If you intentionally re-record this baseline (e.g., shipping a v4.0.x patch BEFORE
v4.0.5 branches), update BASELINE_HASH below to match the new file's SHA-256.
Otherwise: a hash mismatch means someone modified the v4.0 reference, which would
silently invalidate every release-shift report after this point.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "scorecard_v4_0_baseline.csv"

# SHA-256 of scorecard_v4_0_baseline.csv captured on 2026-05-07 from main @ 7aebcd1.
# Update only when intentionally re-recording the v4.0 boundary.
BASELINE_HASH = "ca31cee1d0b45b8ef7f01e933037cda8d30cd45ae2d04cf931e322a6a81adfb6"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_baseline_exists() -> None:
    assert FIXTURE.exists(), (
        f"v4.0 baseline missing: {FIXTURE.relative_to(Path.cwd())}. "
        "Re-capture with: cp outputs/data/processed/fct_site_scorecard.csv "
        f"{FIXTURE.relative_to(Path.cwd())}"
    )


def test_baseline_row_count() -> None:
    """v4.0 has 81 sites — 25 KEK + 56 industrial."""
    rows = FIXTURE.read_text().splitlines()
    # 1 header + 81 data rows
    assert len(rows) == 82, (
        f"v4.0 baseline should have 82 lines (1 header + 81 sites), got {len(rows)}"
    )


def test_baseline_hash_locked() -> None:
    """The v4.0 baseline file must not change silently.

    If this fails: either you re-captured the baseline intentionally (in which case
    update BASELINE_HASH above), or you accidentally overwrote the file (in which
    case restore from git).
    """
    actual = _hash(FIXTURE)
    assert actual == BASELINE_HASH, (
        f"v4.0 baseline hash mismatch.\n"
        f"  expected: {BASELINE_HASH}\n"
        f"  actual:   {actual}\n"
        f"If intentional, update BASELINE_HASH in {Path(__file__).name}. "
        f"Otherwise restore from git: git checkout {FIXTURE.relative_to(Path.cwd())}"
    )
