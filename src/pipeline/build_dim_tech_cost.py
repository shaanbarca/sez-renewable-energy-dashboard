"""
build_dim_tech_cost — TECH006 solar PV parameters in wide format.

Sources:
    data/dim_tech_variant.csv        tech_id → description mapping
    docs/esdm_technology_cost.pdf    TECH006 capex / fixed_om / lifetime (via pdf_extract_esdm_tech)
                                     Falls back to VERIFIED_TECH006_DATA if datasheet is image-based

Output columns:
    tech_id                  "TECH006"
    tech_description         "PV ground-mounted, utility-scale, grid connected"
    year                     2023
    capex_usd_per_kw         CAPEX central, converted from MUSD/MWe × 1000
    capex_lower_usd_per_kw   CAPEX lower bound
    capex_upper_usd_per_kw   CAPEX upper bound
    fixed_om_usd_per_kw_yr   Fixed O&M central, converted from USD/MWe/yr ÷ 1000
    lifetime_yr              Lifetime (years), central value
    source_pdf               Provenance passthrough from fct_tech_parameter
    source_page              Provenance passthrough (0 = pending extraction)
    is_provisional           True if source_page == 0 (values not yet verified from PDF)

CAPEX unit conversion:
    fct_tech_parameter stores CAPEX in MUSD/MWe
    USD/kW = MUSD/MWe × 1_000_000 / 1_000 = value × 1_000
    (1 MUSD/MWe = 1,000,000 USD / 1,000 kW = 1,000 USD/kW)

Fixed O&M unit conversion:
    fct_tech_parameter stores fixed_om in USD/MWe/yr
    USD/kW/yr = USD/MWe/yr ÷ 1_000
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.assumptions import SOLAR_TECH_ID, SOLAR_TECH_YEAR
from src.pipeline.pdf_extract_esdm_tech import ESDM_PDF, get_tech006_params

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

TECH_VARIANT_CSV = REPO_ROOT / "data" / "dim_tech_variant.csv"
TECH_ID = SOLAR_TECH_ID
YEAR = SOLAR_TECH_YEAR


def build_dim_tech_cost(
    tech_variant_csv: Path = TECH_VARIANT_CSV,
    esdm_pdf: Path = ESDM_PDF,
    tech_id: str = TECH_ID,
    year: int = YEAR,
) -> pd.DataFrame:
    """Build a one-row-per-year wide table of TECH006 solar parameters.

    Parameters are sourced directly from the ESDM technology catalogue PDF via
    pdf_extract_esdm_tech.get_tech006_params(). If the PDF is unavailable or the
    datasheet pages are image-based, the verified hardcoded fallback is used.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    variants_raw = pd.read_csv(tech_variant_csv)
    params = get_tech006_params(esdm_pdf)

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
    out = PROCESSED / "dim_tech_cost.csv"
    df = build_dim_tech_cost()
    df.to_csv(out, index=False)
    print(f"dim_tech_cost: {len(df)} row → {out.relative_to(REPO_ROOT)}")
    print(df.to_string(index=False))
    if df["is_provisional"].any():
        print("\n  NOTE: TECH006 parameters are provisional (source_page=0).")
        print("  Update VERIFIED_TECH006_DATA in src/pipeline/pdf_extract_esdm_tech.py.")


if __name__ == "__main__":
    main()
