"""
build_dim_tech_cost — TECH006 solar PV parameters in wide format.

Sources:
    data/dim_tech_variant.csv        tech_id → description mapping
    data/fct_tech_parameter.csv      TECH006 capex / fixed_om / lifetime (2023, central/lower/upper)

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

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

TECH_VARIANT_CSV = REPO_ROOT / "data" / "dim_tech_variant.csv"
TECH_PARAM_CSV = REPO_ROOT / "data" / "fct_tech_parameter.csv"
TECH_ID = SOLAR_TECH_ID
YEAR = SOLAR_TECH_YEAR


def build_dim_tech_cost(
    tech_variant_csv: Path = TECH_VARIANT_CSV,
    tech_param_csv: Path = TECH_PARAM_CSV,
    tech_id: str = TECH_ID,
    year: int = YEAR,
) -> pd.DataFrame:
    """Build a one-row-per-year wide table of TECH006 solar parameters."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    variants_raw = pd.read_csv(tech_variant_csv)
    params_raw = pd.read_csv(tech_param_csv, index_col=0)

    # ─── STAGING ──────────────────────────────────────────────────────────────
    desc_row = variants_raw[variants_raw["tech_id"] == tech_id]
    if desc_row.empty:
        raise ValueError(f"tech_id '{tech_id}' not found in {tech_variant_csv}")
    tech_description = desc_row["variant"].iloc[0]

    p = params_raw[(params_raw["tech_id"] == tech_id) & (params_raw["year"] == year)]
    if p.empty:
        raise ValueError(f"No parameters for {tech_id} year={year} in {tech_param_csv}")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    def _get(parameter: str, value_type: str) -> float:
        row = p[(p["parameter"] == parameter) & (p["value_type"] == value_type)]
        if row.empty:
            raise ValueError(f"Missing {tech_id}/{year}/{parameter}/{value_type}")
        return float(row["value"].iloc[0])

    def _get_source(parameter: str) -> tuple[str, int]:
        row = p[p["parameter"] == parameter]
        if row.empty:
            return "", 0
        return str(row["source_pdf"].iloc[0]), int(row["source_page"].iloc[0])

    capex_c = _get("capex", "central")
    capex_l = _get("capex", "lower")
    capex_u = _get("capex", "upper")
    fom_c = _get("fixed_om", "central")
    life_c = _get("lifetime", "central")

    source_pdf, source_page = _get_source("capex")

    result = pd.DataFrame([{
        "tech_id": tech_id,
        "tech_description": tech_description,
        "year": year,
        # MUSD/MWe × 1000 → USD/kW
        "capex_usd_per_kw": round(capex_c * 1000, 1),
        "capex_lower_usd_per_kw": round(capex_l * 1000, 1),
        "capex_upper_usd_per_kw": round(capex_u * 1000, 1),
        # USD/MWe/yr ÷ 1000 → USD/kW/yr
        "fixed_om_usd_per_kw_yr": round(fom_c / 1000, 2),
        "lifetime_yr": int(life_c),
        "source_pdf": source_pdf,
        "source_page": source_page,
        "is_provisional": source_page == 0,
    }])

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
        print("  Verify against docs/esdm_technology_cost.pdf and update fct_tech_parameter.csv.")


if __name__ == "__main__":
    main()
