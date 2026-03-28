"""
Build fct_ruptl_pipeline: planned PLTS (solar PV) capacity additions by PLN grid region and year.

Source: RUPTL PLN 2025-2034 (Keputusan Menteri ESDM No. 188.K/TL.03/MEM.L/2025, 26 May 2025)
        docs/b967d-ruptl-pln-2025-2034-pub-.pdf

Data extracted from the following tables (PDF Chapter V):
    Tabel 5.80  — National total RE Base (V-96/97)
    Tabel 5.81  — National total ARED (V-97/98)
    Tabel 5.84  — Sumatera RE Base (V-108/109)
    Tabel 5.85  — Sumatera ARED (V-109)
    Tabel 5.88  — Jawa-Madura-Bali RE Base (V-124/125)
    Tabel 5.89  — Jawa-Madura-Bali ARED (V-125/126)
    Tabel 5.95  — Kalimantan RE Base (V-145/146)
    Tabel 5.96  — Kalimantan ARED (V-146)
    Tabel 5.102 — Sulawesi RE Base (V-165/166)
    Tabel 5.103 — Sulawesi ARED (V-166)

Scenarios:
    RE Base  — Workability-driven baseline; does not chase EBT/emission targets.
    ARED     — Accelerated Renewable Energy Development; targets -151 Mt CO2 vs. BAU by 2030.

Output columns:
    grid_region_id         — PLN grid system (matches kek_grid_region_mapping.csv)
    year                   — Calendar year (2025–2034)
    plts_new_mw_re_base    — New PLTS capacity additions (MW) — RE Base scenario
    plts_new_mw_ared       — New PLTS capacity additions (MW) — ARED scenario
    plts_cumul_re_base     — Cumulative PLTS additions 2025–year (MW) — RE Base
    plts_cumul_ared        — Cumulative PLTS additions 2025–year (MW) — ARED
    ruptl_source_table     — Source table number from RUPTL 2025-2034
    notes                  — Data quality flags

Notes on data quality:
    - JAVA_BALI and SUMATERA: standalone PLTS MW extracted directly from Total rows.
    - KALIMANTAN: PLTS from Tabel 5.95/96 Total; values include PLN + SH-PLN + IPP.
    - SULAWESI: RUPTL reports solar as PLTS+BESS combined packages (no standalone PLTS row).
      Values here are the PLTS+BESS total; actual PLTS MW is ~80–90% of listed figure.
    - MALUKU, PAPUA, NTB: PLTS additions are minimal — only asterisked quota allocations
      not counted in DMN capacity (distributed/off-grid programs). Treated as 0 for grid
      context until detailed isolated-system tables are added.
    - All values are NEW capacity additions per year, not cumulative installed.
    - Numbers marked with * in the RUPTL ("tidak diperhitungkan ke dalam DMN") are
      distributed/off-grid allocations excluded from the grid planning balance.
    - SUMATERA ARED PLTS ≈ RE Base (Tabel 5.85 shows minimal delta vs. 5.84).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.pdf_extract_ruptl import VERIFIED_PLTS_DATA, extract_plts_from_pdf

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

YEARS = list(range(2025, 2035))


def build_fct_ruptl_pipeline() -> pd.DataFrame:
    """Build one row per (grid_region_id, year) with PLTS additions and cumulative totals.

    Data source priority:
        1. PDF extraction via pdf_extract_ruptl.extract_plts_from_pdf()
        2. Hardcoded fallback _PLTS_DATA (manually verified from RUPTL 2025-2034)
    """
    plts_data = extract_plts_from_pdf() or VERIFIED_PLTS_DATA
    rows = []
    for region, data in plts_data.items():
        re_vals = data["re_base"]
        ared_vals = data["ared"]
        cumul_re = 0
        cumul_ared = 0
        for i, year in enumerate(YEARS):
            new_re = re_vals[i]
            new_ared = ared_vals[i]
            cumul_re += new_re
            cumul_ared += new_ared
            rows.append(
                {
                    "grid_region_id": region,
                    "year": year,
                    "plts_new_mw_re_base": new_re,
                    "plts_new_mw_ared": new_ared,
                    "plts_cumul_re_base": cumul_re,
                    "plts_cumul_ared": cumul_ared,
                    "ruptl_source_table": data["source"],
                    "notes": data["notes"],
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    print("Building fct_ruptl_pipeline")
    print("  Source: RUPTL PLN 2025-2034")
    print("  Scenarios: RE Base + ARED")
    print(f"  Regions: {list(VERIFIED_PLTS_DATA.keys())}")

    df = build_fct_ruptl_pipeline()

    out = PROCESSED / "fct_ruptl_pipeline.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"\nWrote {out.relative_to(REPO_ROOT)} ({len(df)} rows)")
    print("\nTotal PLTS additions 2025-2034 by region (MW):")
    summary = (
        df.groupby("grid_region_id")
        .agg(
            total_re_base=("plts_new_mw_re_base", "sum"),
            total_ared=("plts_new_mw_ared", "sum"),
        )
        .reset_index()
        .sort_values("total_re_base", ascending=False)
    )
    print(summary.to_string(index=False))

    print("\nSample — JAVA_BALI PLTS pipeline (RE Base vs ARED):")
    jb = df[df["grid_region_id"] == "JAVA_BALI"][
        ["year", "plts_new_mw_re_base", "plts_new_mw_ared", "plts_cumul_re_base", "plts_cumul_ared"]
    ]
    print(jb.to_string(index=False))


if __name__ == "__main__":
    main()
