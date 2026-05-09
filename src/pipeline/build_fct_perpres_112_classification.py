# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""F6 (2026-05-09): Perpres 112/2022 regulatory classification pipeline.

Replaces the legacy `perpres_112_status` string ("Subject to 2050 phase-out")
with a structured regulatory state. Each of the 81 sites carries:

  - exempt (bool)
  - exemption_basis (enum: strategic_industry / mining_specific / not_exempt / unclear)
  - phaseout_year_baseline (2050 under current Perpres 112)
  - phaseout_year_strict_scenario (2035 if exemption tightened in 2026+ regulatory cycle)
  - subject_to_strict_scenario (bool: True if strict scenario forces hybrid)

Source: `data/raw/site_perpres_112_classification.csv` (manually curated, one
row per site). Sector defaults from the F6 spec:

  - Nickel cluster, aluminium, steel, fertilizer → strategic_industry
  - Cement → not_exempt
  - KEK (any) → unclear (depends on tenant mix)

Site-specific overrides (e.g. IMIP's Perpres 70/2014 incentive ruling) are
edited in the raw CSV and carry verification_status='verified' per row.

The pipeline applies one derived field — `subject_to_strict_scenario` — and
otherwise passes the raw classification through to the processed CSV.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "site_perpres_112_classification.csv"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"
OUT_PATH = PROCESSED_DIR / "fct_perpres_112_classification.csv"


def derive_subject_to_strict_scenario(row: pd.Series) -> bool:
    """A site is subject to the strict scenario if it currently enjoys an
    exemption that the 2026+ tightening would remove — i.e., exempt today
    AND the strict phase-out year is earlier than baseline.
    """
    return bool(row.get("exempt", False)) and (
        row.get("phaseout_year_strict", 2050) < row.get("phaseout_year_baseline", 2050)
    )


def build_fct_perpres_112_classification(
    raw_path: Path | str = RAW_PATH,
) -> pd.DataFrame:
    """Load raw classification CSV, derive subject_to_strict_scenario, return.

    Returns a DataFrame ready to write to fct_perpres_112_classification.csv,
    with one row per site_id. Columns are renamed with the `captive_perpres_112_`
    or `captive_phaseout_year_` prefix to match the scorecard naming convention.
    """
    raw_path = Path(raw_path)
    if not raw_path.exists():
        return pd.DataFrame(
            columns=[
                "site_id",
                "captive_perpres_112_exempt",
                "captive_perpres_112_exemption_basis",
                "captive_phaseout_year_baseline",
                "captive_phaseout_year_strict_scenario",
                "captive_subject_to_strict_scenario",
                "captive_perpres_112_source",
                "captive_perpres_112_verification_status",
            ]
        )

    raw = pd.read_csv(raw_path)
    raw["subject_to_strict_scenario"] = raw.apply(derive_subject_to_strict_scenario, axis=1)

    out = pd.DataFrame(
        {
            "site_id": raw["site_id"],
            "captive_perpres_112_exempt": raw["exempt"].astype(bool),
            "captive_perpres_112_exemption_basis": raw["exemption_basis"],
            "captive_phaseout_year_baseline": raw["phaseout_year_baseline"].astype(int),
            "captive_phaseout_year_strict_scenario": raw["phaseout_year_strict"].astype(int),
            "captive_subject_to_strict_scenario": raw["subject_to_strict_scenario"],
            "captive_perpres_112_source": raw["source"],
            "captive_perpres_112_verification_status": raw["verification_status"],
        }
    )
    return out


if __name__ == "__main__":
    df = build_fct_perpres_112_classification()
    if not df.empty:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_PATH, index=False)
        print(f"  Wrote {len(df)} rows → {OUT_PATH}")
        counts = df["captive_perpres_112_exemption_basis"].value_counts()
        for basis, count in counts.items():
            print(f"    {basis}: {count}")
    else:
        print("  No raw classification file found, skipping write")
