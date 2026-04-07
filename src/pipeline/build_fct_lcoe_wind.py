"""
build_fct_lcoe_wind — precomputed wind LCOE bands per KEK × WACC × siting scenario.

Sources:
    processed: dim_kek.csv                       kek_id list
    processed: fct_kek_wind_resource.csv         wind_speed, cf_wind at centroid + best_50km
    processed: dim_tech_cost_wind.csv            TECH_WIND_ONSHORE capex / fixed_om / lifetime
    processed: fct_substation_proximity.csv      dist_to_nearest_substation_km

Output columns (one row per kek_id × wacc_pct × scenario):
    kek_id                      join key
    wacc_pct                    WACC assumption (4–20% in 2% steps)
    scenario                    'within_boundary' or 'remote_captive'
    cf_wind_used                wind capacity factor used
    wind_speed_ms               wind speed (m/s) for the scenario
    gentie_cost_per_kw          0 for within_boundary; dist-based for remote_captive
    effective_capex_usd_per_kw  capex + gentie_cost_per_kw
    lcoe_usd_mwh               LCOE at central CAPEX
    lcoe_low_usd_mwh            LCOE at lower CAPEX bound
    lcoe_high_usd_mwh           LCOE at upper CAPEX bound
    transmission_lease_adder_usd_mwh  lease for remote scenario
    lcoe_allin_usd_mwh          LCOE + transmission lease
    lcoe_allin_low_usd_mwh      all-in at lower bound
    lcoe_allin_high_usd_mwh     all-in at upper bound
    tech_id                     "TECH_WIND_ONSHORE"
    lifetime_yr                 lifetime used

Formula: same CRF annuity as solar (src/model/basic_model.py)
    lcoe = (effective_capex × crf + fixed_om) / (cf × 8.76)

Siting scenarios (same as solar):
    within_boundary — uses cf_wind_centroid, no gen-tie cost
    remote_captive  — uses cf_wind_best_50km, gen-tie CAPEX adder
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.model.basic_model import gentie_cost_per_kw, lcoe_solar
from src.pipeline.assumptions import (
    TRANSMISSION_LEASE_HIGH_USD_MWH,
    TRANSMISSION_LEASE_LOW_USD_MWH,
    TRANSMISSION_LEASE_MID_USD_MWH,
    WACC_VALUES,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
WIND_RESOURCE_CSV = PROCESSED / "fct_kek_wind_resource.csv"
DIM_TECH_WIND_CSV = PROCESSED / "dim_tech_cost_wind.csv"
FSP_CSV = PROCESSED / "fct_substation_proximity.csv"


def build_fct_lcoe_wind(
    dim_kek_csv: Path = DIM_KEK_CSV,
    wind_resource_csv: Path = WIND_RESOURCE_CSV,
    dim_tech_wind_csv: Path = DIM_TECH_WIND_CSV,
    fct_substation_proximity_csv: Path = FSP_CSV,
    wacc_values: list[float] = WACC_VALUES,
) -> pd.DataFrame:
    """Compute wind LCOE bands for every KEK × WACC × siting scenario combination.

    Uses the same LCOE formula as solar — the math is technology-agnostic.
    Only the inputs differ: wind CAPEX/FOM/lifetime and wind CF.
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_kek = pd.read_csv(dim_kek_csv)[["kek_id"]]
    wind_resource = pd.read_csv(wind_resource_csv)[
        [
            "kek_id",
            "wind_speed_centroid_ms",
            "wind_speed_best_50km_ms",
            "cf_wind_centroid",
            "cf_wind_best_50km",
        ]
    ]
    tech = pd.read_csv(dim_tech_wind_csv).iloc[0]
    proximity = pd.read_csv(fct_substation_proximity_csv)[
        ["kek_id", "dist_to_nearest_substation_km"]
    ]

    # ─── STAGING ──────────────────────────────────────────────────────────────
    capex_c = float(tech["capex_usd_per_kw"])
    capex_l = float(tech["capex_lower_usd_per_kw"])
    capex_u = float(tech["capex_upper_usd_per_kw"])
    fom = float(tech["fixed_om_usd_per_kw_yr"])
    lifetime = int(tech["lifetime_yr"])
    tech_id = str(tech["tech_id"])
    is_capex_provisional = bool(tech.get("is_provisional", False))

    scenarios = [
        ("within_boundary", "cf_wind_centroid", "wind_speed_centroid_ms"),
        ("remote_captive", "cf_wind_best_50km", "wind_speed_best_50km_ms"),
    ]

    df = dim_kek.merge(wind_resource, on="kek_id", how="left")
    df = df.merge(proximity, on="kek_id", how="left")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    records = []
    for _, kek_row in df.iterrows():
        dist_km = (
            float(kek_row["dist_to_nearest_substation_km"])
            if pd.notna(kek_row.get("dist_to_nearest_substation_km"))
            else 0.0
        )

        for scenario, cf_col, ws_col in scenarios:
            cf = float(kek_row[cf_col]) if pd.notna(kek_row.get(cf_col)) else None
            ws = float(kek_row[ws_col]) if pd.notna(kek_row.get(ws_col)) else np.nan

            # Gen-tie cost: 0 for within_boundary, computed for remote_captive
            if scenario == "within_boundary":
                gtie = 0.0
                lease_mid = 0.0
                lease_low = 0.0
                lease_high = 0.0
            else:
                gtie = gentie_cost_per_kw(dist_km)
                lease_mid = TRANSMISSION_LEASE_MID_USD_MWH
                lease_low = TRANSMISSION_LEASE_LOW_USD_MWH
                lease_high = TRANSMISSION_LEASE_HIGH_USD_MWH

            eff_capex_c = capex_c + gtie
            eff_capex_l = capex_l + gtie
            eff_capex_u = capex_u + gtie

            for wacc in wacc_values:
                wacc_dec = wacc / 100.0
                if cf is None or cf == 0:
                    lcoe_c = lcoe_l = lcoe_u = np.nan
                else:
                    # lcoe_solar is technology-agnostic — same CRF formula
                    lcoe_c = lcoe_solar(eff_capex_c, fom, wacc_dec, lifetime, cf)
                    lcoe_l = lcoe_solar(eff_capex_l, fom, wacc_dec, lifetime, cf)
                    lcoe_u = lcoe_solar(eff_capex_u, fom, wacc_dec, lifetime, cf)

                def _r(v: float, adder: float = 0.0) -> float:
                    return round(v + adder, 2) if not np.isnan(v) else np.nan

                records.append(
                    {
                        "kek_id": kek_row["kek_id"],
                        "wacc_pct": wacc,
                        "scenario": scenario,
                        "cf_wind_used": round(float(cf), 4) if cf is not None else np.nan,
                        "wind_speed_ms": round(ws, 2) if np.isfinite(ws) else np.nan,
                        "gentie_cost_per_kw": round(gtie, 1),
                        "effective_capex_usd_per_kw": round(eff_capex_c, 1),
                        "lcoe_usd_mwh": _r(lcoe_c),
                        "lcoe_low_usd_mwh": _r(lcoe_l),
                        "lcoe_high_usd_mwh": _r(lcoe_u),
                        "transmission_lease_adder_usd_mwh": lease_mid,
                        "lcoe_allin_usd_mwh": _r(lcoe_c, lease_mid),
                        "lcoe_allin_low_usd_mwh": _r(lcoe_l, lease_low),
                        "lcoe_allin_high_usd_mwh": _r(lcoe_u, lease_high),
                        "is_capex_provisional": is_capex_provisional,
                        "tech_id": tech_id,
                        "lifetime_yr": lifetime,
                    }
                )

    return pd.DataFrame(records)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "fct_lcoe_wind.csv"
    df = build_fct_lcoe_wind()
    df.to_csv(out, index=False)
    print(f"fct_lcoe_wind: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    sample = df[(df["wacc_pct"] == 10.0)].sort_values(["kek_id", "scenario"])[
        ["kek_id", "scenario", "lcoe_usd_mwh", "cf_wind_used", "wind_speed_ms"]
    ]
    print("\nWind LCOE at WACC=10% by scenario (USD/MWh):")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
