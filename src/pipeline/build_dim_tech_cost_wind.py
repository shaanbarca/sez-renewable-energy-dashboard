"""
build_dim_tech_cost_wind — TECH_WIND_ONSHORE wind onshore parameters in wide format.

Sources:
    data/dim_tech_variant.csv        tech_id → description mapping
    docs/esdm_technology_cost.pdf    Wind onshore capex / fixed_om / lifetime (via pdf_extract_esdm_tech)
                                     Falls back to VERIFIED_TECH_WIND_ONSHORE_DATA if extraction fails

Output columns:
    tech_id                  "TECH_WIND_ONSHORE"
    tech_description         "Wind power - Onshore"
    year                     2023
    capex_usd_per_kw         CAPEX central, converted from MUSD/MWe × 1000
    capex_lower_usd_per_kw   CAPEX lower bound
    capex_upper_usd_per_kw   CAPEX upper bound
    fixed_om_usd_per_kw_yr   Fixed O&M central, converted from USD/MWe/yr ÷ 1000
    lifetime_yr              Lifetime (years), central value
    source_pdf               Provenance passthrough from extraction
    source_page              Provenance passthrough (0 = pending extraction)
    is_provisional           True if source_page == 0

CAPEX unit conversion:
    MUSD/MWe × 1000 → USD/kW (same as solar)

Fixed O&M unit conversion:
    USD/MWe/yr ÷ 1000 → USD/kW/yr (same as solar)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.assumptions import WIND_TECH_ID, WIND_TECH_YEAR
from src.pipeline.pdf_extract_esdm_tech import ESDM_PDF, get_tech_wind_onshore_params

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

TECH_VARIANT_CSV = REPO_ROOT / "data" / "dim_tech_variant.csv"
TECH_ID = WIND_TECH_ID
YEAR = WIND_TECH_YEAR


def build_dim_tech_cost_wind(
    tech_variant_csv: Path = TECH_VARIANT_CSV,
    esdm_pdf: Path = ESDM_PDF,
    tech_id: str = TECH_ID,
    year: int = YEAR,
) -> pd.DataFrame:
    """Build a one-row-per-year wide table of wind onshore parameters.

    Parameters are sourced directly from the ESDM technology catalogue PDF via
    pdf_extract_esdm_tech.get_tech_wind_onshore_params(). If the PDF is unavailable
    or extraction fails, the verified hardcoded fallback is used.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    variants_raw = pd.read_csv(tech_variant_csv)
    params = get_tech_wind_onshore_params(esdm_pdf)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    desc_row = variants_raw[variants_raw["tech_id"] == tech_id]
    if desc_row.empty:
        raise ValueError(f"tech_id '{tech_id}' not found in {tech_variant_csv}")
    tech_description = desc_row["variant"].iloc[0]

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    source_page = params["capex"]["source_page"]

    result = pd.DataFrame(
        [
            {
                "tech_id": tech_id,
                "tech_description": tech_description,
                "year": year,
                # MUSD/MWe × 1000 → USD/kW
                "capex_usd_per_kw": round(params["capex"]["central"] * 1000, 1),
                "capex_lower_usd_per_kw": round(params["capex"]["lower"] * 1000, 1),
                "capex_upper_usd_per_kw": round(params["capex"]["upper"] * 1000, 1),
                # USD/MWe/yr ÷ 1000 → USD/kW/yr
                "fixed_om_usd_per_kw_yr": round(params["fixed_om"]["central"] / 1000, 2),
                "lifetime_yr": int(params["lifetime"]["central"]),
                "source_pdf": "esdm_technology_cost.pdf",
                "source_page": source_page,
                "is_provisional": source_page == 0,
            }
        ]
    )

    return result


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "dim_tech_cost_wind.csv"
    df = build_dim_tech_cost_wind()
    df.to_csv(out, index=False)
    print(f"dim_tech_cost_wind: {len(df)} row → {out.relative_to(REPO_ROOT)}")
    print(df.to_string(index=False))
    if df["is_provisional"].any():
        print("\n  NOTE: Wind parameters are provisional (source_page=0).")
        print("  Update VERIFIED_TECH_WIND_ONSHORE_DATA in src/pipeline/pdf_extract_esdm_tech.py.")


if __name__ == "__main__":
    main()
