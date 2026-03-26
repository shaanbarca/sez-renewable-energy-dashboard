"""
Build fct_grid_cost_proxy: grid reference cost per PLN system.

Source: Permen ESDM No. 7 Tahun 2024, Lampiran IV (Tarif Industri)
        docs/Permen ESDM Nomor 7 Tahun 2024.pdf, page 14

Key finding: I-3/TM and I-4/TT industrial tariffs are UNIFORM NATIONWIDE.
They do not vary by PLN grid system. Every KEK inherits the same national tariff.
PLN BPP (cost of supply) varies by system, but is not yet in the repo.

Tariff schedule (Lampiran IV, effective 10 June 2024):
    I-3/TM  (200 kVA – 30,000 kVA): WBP = K×1,035.78; LWBP = 1,035.78 Rp/kWh
    I-4/TT  (≥30,000 kVA):           WBP = LWBP = 996.74 Rp/kWh

KEK tenants are primarily I-4/TT (large industrial, high-voltage connection).
I-3/TM is used as a fallback for smaller KEK tenants.

LWBP (Luar Waktu Beban Puncak = off-peak) rate is used as reference.
WBP (Waktu Beban Puncak = peak hours) rate is K × LWBP where 1.4 ≤ K ≤ 2.
K varies by PLN system — not applied here (use LWBP as conservative floor).

Exchange rate: IDR 15,800 / USD (2024 reference average; update if needed).

Reads:
    data/kek_grid_region_mapping.csv  — to enumerate grid_region_ids

Writes:
    outputs/data/fct_grid_cost_proxy.csv

Output columns:
    grid_region_id            — PLN system
    tariff_i3_rp_kwh          — I-3/TM LWBP energy charge (Rp/kWh)
    tariff_i4_rp_kwh          — I-4/TT energy charge (Rp/kWh)
    idr_usd_rate              — IDR/USD exchange rate used for conversion
    tariff_i3_usd_mwh         — I-3/TM in USD/MWh
    tariff_i4_usd_mwh         — I-4/TT in USD/MWh
    dashboard_rate_usd_mwh    — primary comparator for the dashboard (I-4/TT)
    dashboard_rate_label       — human-readable source label
    dashboard_rate_flag        — "OFFICIAL" | "PROVISIONAL"
    bpp_usd_mwh               — PLN BPP cost of supply (NaN — not yet sourced)
    bpp_source                — source for BPP (NaN until PLN Statistik 2024 is added)
    notes                     — any caveats
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.pipeline.assumptions import (
    IDR_USD_RATE,
    TARIFF_I3_LWBP_RP_KWH,
    TARIFF_I4_RP_KWH,
    rp_kwh_to_usd_mwh,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"


def build_fct_grid_cost_proxy(
    dim_kek_csv: Path = DIM_KEK_CSV,
    idr_usd_rate: float = IDR_USD_RATE,
) -> pd.DataFrame:
    """Build one row per grid_region_id with national tariff values."""
    dim_kek = pd.read_csv(dim_kek_csv)
    grid_regions = dim_kek["grid_region_id"].dropna().unique()

    tariff_i3 = rp_kwh_to_usd_mwh(TARIFF_I3_LWBP_RP_KWH, idr_usd_rate)
    tariff_i4 = rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH, idr_usd_rate)

    rows = []
    for region in sorted(grid_regions):
        rows.append({
            "grid_region_id": region,
            # Raw Rp values (source: Lampiran IV)
            "tariff_i3_rp_kwh": TARIFF_I3_LWBP_RP_KWH,
            "tariff_i4_rp_kwh": TARIFF_I4_RP_KWH,
            "idr_usd_rate": idr_usd_rate,
            # USD equivalents
            "tariff_i3_usd_mwh": tariff_i3,
            "tariff_i4_usd_mwh": tariff_i4,
            # Primary dashboard comparator
            "dashboard_rate_usd_mwh": tariff_i4,
            "dashboard_rate_label": "I-4/TT LWBP, Permen ESDM No.7/2024",
            "dashboard_rate_flag": "OFFICIAL",
            # BPP — not yet sourced
            "bpp_usd_mwh": None,
            "bpp_source": None,
            "notes": (
                "I-3/I-4 tariffs are uniform nationwide (no regional variation). "
                "LWBP rate used; WBP peak rate = K×LWBP where K=1.4–2.0 (system-specific). "
                "BPP (PLN cost of supply) varies by region — to be added from PLN Statistik 2024."
            ),
        })

    return pd.DataFrame(rows)


def main() -> None:
    print("Building fct_grid_cost_proxy")
    print(f"  Source: Permen ESDM No.7/2024, Lampiran IV (Tarif Industri)")
    print(f"  I-3/TM LWBP: {TARIFF_I3_LWBP_RP_KWH:,.2f} Rp/kWh")
    print(f"  I-4/TT:      {TARIFF_I4_RP_KWH:,.2f} Rp/kWh")
    print(f"  IDR/USD rate: {IDR_USD_RATE:,.0f}")

    df = build_fct_grid_cost_proxy()

    out = PROCESSED / "fct_grid_cost_proxy.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    print(f"\nWrote {out.relative_to(REPO_ROOT)} ({len(df)} grid regions)")
    print(f"\n  I-3/TM → {rp_kwh_to_usd_mwh(TARIFF_I3_LWBP_RP_KWH):.1f} USD/MWh")
    print(f"  I-4/TT → {rp_kwh_to_usd_mwh(TARIFF_I4_RP_KWH):.1f} USD/MWh  ← dashboard primary")
    print(f"\n  Note: I-3/I-4 tariffs are UNIFORM NATIONWIDE.")
    print(f"  BPP (cost of supply) varies by region — not yet in repo.")
    print()
    print(df[["grid_region_id", "tariff_i3_usd_mwh", "tariff_i4_usd_mwh",
              "dashboard_rate_usd_mwh", "dashboard_rate_flag"]].to_string(index=False))


if __name__ == "__main__":
    main()
