"""
build_fct_lcoe — precomputed LCOE bands per KEK × WACC assumption.

Sources:
    processed: dim_kek.csv           kek_id list
    processed: fct_kek_resource.csv  cf_best_50km (capacity factor)
    processed: dim_tech_cost.csv     TECH006 capex / fixed_om / lifetime

Output columns (one row per kek_id × wacc_pct):
    kek_id                join key
    wacc_pct              WACC assumption: 8.0, 10.0, 12.0
    lcoe_usd_mwh          LCOE at central CAPEX (USD/MWh)
    lcoe_low_usd_mwh      LCOE at lower CAPEX bound (USD/MWh)
    lcoe_high_usd_mwh     LCOE at upper CAPEX bound (USD/MWh)
    cf_used               capacity factor used (cf_best_50km, or cf_centroid fallback)
    pvout_used_kwh_kwp    PVOUT value that CF was derived from
    is_cf_provisional     True if pvout_best_50km was missing and centroid was used
    is_capex_provisional  True if dim_tech_cost.is_provisional (TECH006 not yet PDF-verified)
    tech_id               "TECH006"
    lifetime_yr           lifetime used in calculation

Formula (src/model/basic_model.py lcoe_solar):
    crf  = (wacc × (1+wacc)^n) / ((1+wacc)^n − 1)
    lcoe = (capex_usd_per_kw × crf + fixed_om_usd_per_kw_yr) / (cf × 8.76)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.model.basic_model import lcoe_solar
from src.pipeline.assumptions import HOURS_PER_YEAR, WACC_VALUES

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
FKR_CSV = PROCESSED / "fct_kek_resource.csv"
DIM_TECH_CSV = PROCESSED / "dim_tech_cost.csv"


def build_fct_lcoe(
    dim_kek_csv: Path = DIM_KEK_CSV,
    fct_kek_resource_csv: Path = FKR_CSV,
    dim_tech_cost_csv: Path = DIM_TECH_CSV,
    wacc_values: list[float] = WACC_VALUES,
) -> pd.DataFrame:
    """Compute LCOE bands for every KEK × WACC combination."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_kek = pd.read_csv(dim_kek_csv)[["kek_id"]]
    resource = pd.read_csv(fct_kek_resource_csv)[
        ["kek_id", "pvout_centroid", "pvout_best_50km"]
    ]
    tech = pd.read_csv(dim_tech_cost_csv).iloc[0]

    # ─── STAGING ──────────────────────────────────────────────────────────────
    capex_c = float(tech["capex_usd_per_kw"])
    capex_l = float(tech["capex_lower_usd_per_kw"])
    capex_u = float(tech["capex_upper_usd_per_kw"])
    fom = float(tech["fixed_om_usd_per_kw_yr"])
    lifetime = int(tech["lifetime_yr"])
    tech_id = str(tech["tech_id"])
    is_capex_provisional = bool(tech.get("is_provisional", False))

    df = dim_kek.merge(resource, on="kek_id", how="left")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    # CF: prefer best_50km; fall back to centroid if missing
    df["cf_used"] = np.where(
        df["pvout_best_50km"].notna(),
        df["pvout_best_50km"] / HOURS_PER_YEAR,
        df["pvout_centroid"] / HOURS_PER_YEAR,
    )
    df["pvout_used_kwh_kwp"] = np.where(
        df["pvout_best_50km"].notna(),
        df["pvout_best_50km"],
        df["pvout_centroid"],
    )
    df["is_cf_provisional"] = df["pvout_best_50km"].isna()

    records = []
    for _, kek_row in df.iterrows():
        cf = kek_row["cf_used"]
        for wacc in wacc_values:
            wacc_dec = wacc / 100.0
            if pd.isna(cf) or cf == 0:
                lcoe_c = lcoe_l = lcoe_u = np.nan
            else:
                lcoe_c = lcoe_solar(capex_c, fom, wacc_dec, lifetime, cf)
                lcoe_l = lcoe_solar(capex_l, fom, wacc_dec, lifetime, cf)
                lcoe_u = lcoe_solar(capex_u, fom, wacc_dec, lifetime, cf)

            records.append({
                "kek_id": kek_row["kek_id"],
                "wacc_pct": wacc,
                "lcoe_usd_mwh": round(lcoe_c, 2) if not np.isnan(lcoe_c) else np.nan,
                "lcoe_low_usd_mwh": round(lcoe_l, 2) if not np.isnan(lcoe_l) else np.nan,
                "lcoe_high_usd_mwh": round(lcoe_u, 2) if not np.isnan(lcoe_u) else np.nan,
                "cf_used": round(float(cf), 4) if not pd.isna(cf) else np.nan,
                "pvout_used_kwh_kwp": kek_row["pvout_used_kwh_kwp"],
                "is_cf_provisional": kek_row["is_cf_provisional"],
                "is_capex_provisional": is_capex_provisional,
                "tech_id": tech_id,
                "lifetime_yr": lifetime,
            })

    return pd.DataFrame(records)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "fct_lcoe.csv"
    df = build_fct_lcoe()
    df.to_csv(out, index=False)
    print(f"fct_lcoe: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    sample = df[df["wacc_pct"] == 10.0][
        ["kek_id", "lcoe_low_usd_mwh", "lcoe_usd_mwh", "lcoe_high_usd_mwh", "cf_used", "is_capex_provisional"]
    ]
    print("\nLCOE at WACC=10% (USD/MWh):")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
