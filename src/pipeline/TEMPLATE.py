"""
TEMPLATE.py — copy this to build_<name>.py to add a new data source.

Steps:
    1. cp src/pipeline/TEMPLATE.py src/pipeline/build_<name>.py
    2. Implement the three stages below
    3. Import and add one Step(...) entry in run_pipeline.py

Naming convention:
    dim_*   — dimension table (slowly-changing reference data, one row per entity)
    fct_*   — fact table (measurements, computed values, one row per KEK or region/year)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"


def build_<name>(  # noqa: E999 — rename before using
    dep_csv: Path = PROCESSED / "dep.csv",  # declare upstream deps as path params
) -> pd.DataFrame:
    """One-line description of what this table contains.

    Sources:
        dep_csv: what it contains and where it comes from

    Output columns:
        col_name | type | description
    """

    # ─── RAW ─────────────────────────────────────────────────────────────────
    # Load source files as-is. No transforms here.
    raw = pd.read_csv(dep_csv)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    # Rename columns to project conventions. Type-cast. Drop unused columns.
    # No business logic — only structural changes that mirror the source 1:1.
    df = raw.rename(columns={
        "source_col": "project_col",
    })

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    # Joins, computations, derived columns, filtering.
    # This is the business logic layer.
    df["derived_col"] = df["col_a"] / df["col_b"]

    return df[[
        "col_a", "col_b", "derived_col",  # explicit column selection
    ]]


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "<name>.csv"
    df = build_<name>()
    df.to_csv(out, index=False)
    print(f"<name>: {len(df)} rows → {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
