# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_fct_lcoe — precomputed LCOE bands per KEK × WACC × siting scenario.

Sources:
    processed: dim_kek.csv                  kek_id list
    processed: fct_kek_resource.csv         pvout_centroid, pvout_best_50km
    processed: dim_tech_cost.csv            TECH006 capex / fixed_om / lifetime
    processed: fct_substation_proximity.csv dist_to_nearest_substation_km, dist_solar_to_nearest_substation_km

Output columns (one row per kek_id × wacc_pct × scenario):
    kek_id                  join key
    wacc_pct                WACC assumption: 8.0, 10.0, 12.0
    scenario                'within_boundary' or 'grid_connected_solar'
    pvout_used              'pvout_centroid' or 'pvout_best_50km'
    cf_used                 capacity factor used
    connection_cost_per_kw  0 for within_boundary; grid connection cost for grid_connected_solar
    effective_capex_usd_per_kw  capex + connection_cost_per_kw
    lcoe_usd_mwh            LCOE at central CAPEX (USD/MWh)
    lcoe_low_usd_mwh        LCOE at lower CAPEX bound (USD/MWh)
    lcoe_high_usd_mwh       LCOE at upper CAPEX bound (USD/MWh)
    is_cf_provisional       True if pvout value was a centroid fallback
    is_capex_provisional    True if dim_tech_cost.is_provisional
    tech_id                 "TECH006"
    lifetime_yr             lifetime used in calculation

Formula (src/model/basic_model.py):
    crf  = (wacc × (1+wacc)^n) / ((1+wacc)^n − 1)
    lcoe = (effective_capex × crf + fixed_om) / (cf × 8.76)

Siting scenarios:
    within_boundary        — uses pvout_centroid, no connection cost (plant on KEK land)
    grid_connected_solar   — uses pvout_best_50km, connection cost based on dist_solar_to_nearest_substation_km

V2: Replaces 'remote_captive' scenario with 'grid_connected_solar'. Uses dist_solar_to_nearest_substation_km
(solar → substation distance) instead of dist_to_nearest_substation_km (KEK → substation). Removes
transmission lease adder — in the grid-connected model, transmission is PLN's system cost in BPP/tariff.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.assumptions import LAND_COST_USD_PER_KW
from src.model.basic_model import grid_connection_cost_per_kw, lcoe_solar
from src.pipeline.assumptions import (
    HOURS_PER_YEAR,
    WACC_VALUES,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

DIM_KEK_CSV = PROCESSED / "dim_kek.csv"
FKR_CSV = PROCESSED / "fct_kek_resource.csv"
DIM_TECH_CSV = PROCESSED / "dim_tech_cost.csv"
FSP_CSV = PROCESSED / "fct_substation_proximity.csv"


def build_fct_lcoe(
    dim_kek_csv: Path = DIM_KEK_CSV,
    fct_kek_resource_csv: Path = FKR_CSV,
    dim_tech_cost_csv: Path = DIM_TECH_CSV,
    fct_substation_proximity_csv: Path = FSP_CSV,
    wacc_values: list[float] = WACC_VALUES,
) -> pd.DataFrame:
    """Compute LCOE bands for every KEK × WACC × siting scenario combination.

    V2: Uses grid_connected_solar (solar→substation distance) instead of
    remote_captive (KEK→substation distance + gen-tie + transmission lease).
    """

    # ─── RAW ──────────────────────────────────────────────────────────────────
    dim_kek = pd.read_csv(dim_kek_csv)[["kek_id"]]
    resource_raw = pd.read_csv(fct_kek_resource_csv)
    # Use pvout_buildable_best_50km for grid-connected scenario when available
    gc_pvout_col = (
        "pvout_buildable_best_50km"
        if "pvout_buildable_best_50km" in resource_raw.columns
        else "pvout_best_50km"
    )
    resource_cols = ["kek_id", "pvout_centroid", "pvout_best_50km"]
    if gc_pvout_col not in resource_cols:
        resource_cols.append(gc_pvout_col)
    resource = resource_raw[resource_cols]

    tech = pd.read_csv(dim_tech_cost_csv).iloc[0]

    # V2: read solar-to-substation distance for grid-connected scenario
    proximity_cols = ["kek_id", "dist_to_nearest_substation_km"]
    prox_raw = pd.read_csv(fct_substation_proximity_csv)
    if "dist_solar_to_nearest_substation_km" in prox_raw.columns:
        proximity_cols.append("dist_solar_to_nearest_substation_km")
    proximity = prox_raw[proximity_cols]

    # ─── STAGING ──────────────────────────────────────────────────────────────
    capex_c = float(tech["capex_usd_per_kw"])
    capex_l = float(tech["capex_lower_usd_per_kw"])
    capex_u = float(tech["capex_upper_usd_per_kw"])
    fom = float(tech["fixed_om_usd_per_kw_yr"])
    lifetime = int(tech["lifetime_yr"])
    tech_id = str(tech["tech_id"])
    is_capex_provisional = bool(tech.get("is_provisional", False))

    # within_boundary always uses pvout_centroid (on-site plant, no connection cost)
    # grid_connected_solar uses buildable PVOUT when available, else falls back to raw best_50km
    scenarios = [
        ("within_boundary", "pvout_centroid"),
        ("grid_connected_solar", gc_pvout_col),
    ]

    df = dim_kek.merge(resource, on="kek_id", how="left")
    df = df.merge(proximity, on="kek_id", how="left")

    # ─── TRANSFORM ────────────────────────────────────────────────────────────
    records = []
    for _, kek_row in df.iterrows():
        # V2: use solar-to-substation distance for grid-connected scenario
        dist_solar_to_sub = (
            float(kek_row["dist_solar_to_nearest_substation_km"])
            if "dist_solar_to_nearest_substation_km" in kek_row.index
            and pd.notna(kek_row.get("dist_solar_to_nearest_substation_km"))
            else None
        )
        # Fallback: KEK-to-substation distance (V1 behavior)
        dist_kek_to_sub = (
            float(kek_row["dist_to_nearest_substation_km"])
            if pd.notna(kek_row.get("dist_to_nearest_substation_km"))
            else 0.0
        )

        for scenario, pvout_col in scenarios:
            pvout_val = kek_row.get(pvout_col)
            is_cf_provisional = pd.isna(pvout_val)

            # Fallback: if preferred PVOUT is missing, try pvout_best_50km then pvout_centroid
            if is_cf_provisional and pvout_col == "pvout_buildable_best_50km":
                pvout_val = kek_row.get("pvout_best_50km")
                actual_pvout_col = "pvout_best_50km" if pd.notna(pvout_val) else "pvout_centroid"
                if pd.isna(pvout_val):
                    pvout_val = kek_row.get("pvout_centroid")
            elif is_cf_provisional:
                pvout_val = kek_row.get("pvout_centroid")
                actual_pvout_col = "pvout_centroid"
            else:
                actual_pvout_col = pvout_col

            cf = float(pvout_val) / HOURS_PER_YEAR if pd.notna(pvout_val) else None

            # Connection + land cost: 0 for within_boundary, computed for grid_connected_solar
            if scenario == "within_boundary":
                conn_cost = 0.0
                land_cost = 0.0
            else:
                # V2: use solar-to-substation distance; fallback to KEK-to-substation
                dist = dist_solar_to_sub if dist_solar_to_sub is not None else dist_kek_to_sub
                conn_cost = grid_connection_cost_per_kw(dist)
                land_cost = LAND_COST_USD_PER_KW

            eff_capex_c = capex_c + conn_cost + land_cost
            eff_capex_l = capex_l + conn_cost + land_cost
            eff_capex_u = capex_u + conn_cost + land_cost

            for wacc in wacc_values:
                wacc_dec = wacc / 100.0
                if cf is None or cf == 0:
                    lcoe_c = lcoe_l = lcoe_u = np.nan
                else:
                    lcoe_c = lcoe_solar(eff_capex_c, fom, wacc_dec, lifetime, cf)
                    lcoe_l = lcoe_solar(eff_capex_l, fom, wacc_dec, lifetime, cf)
                    lcoe_u = lcoe_solar(eff_capex_u, fom, wacc_dec, lifetime, cf)

                def _r(v: float) -> float:
                    return round(v, 2) if not np.isnan(v) else np.nan

                records.append(
                    {
                        "kek_id": kek_row["kek_id"],
                        "wacc_pct": wacc,
                        "scenario": scenario,
                        "pvout_used": actual_pvout_col,
                        "cf_used": round(float(cf), 4) if cf is not None else np.nan,
                        "connection_cost_per_kw": round(conn_cost, 1),
                        "effective_capex_usd_per_kw": round(eff_capex_c, 1),
                        "lcoe_usd_mwh": _r(lcoe_c),
                        "lcoe_low_usd_mwh": _r(lcoe_l),
                        "lcoe_high_usd_mwh": _r(lcoe_u),
                        "is_cf_provisional": is_cf_provisional,
                        "is_capex_provisional": is_capex_provisional,
                        "tech_id": tech_id,
                        "lifetime_yr": lifetime,
                    }
                )

    return pd.DataFrame(records)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "fct_lcoe.csv"
    df = build_fct_lcoe()
    df.to_csv(out, index=False)
    print(f"fct_lcoe: {len(df)} rows → {out.relative_to(REPO_ROOT)}")
    sample = df[(df["wacc_pct"] == 10.0)].sort_values(["kek_id", "scenario"])[
        ["kek_id", "scenario", "lcoe_usd_mwh", "connection_cost_per_kw", "cf_used"]
    ]
    print("\nLCOE at WACC=10% by scenario (USD/MWh):")
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
