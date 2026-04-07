"""
pdf_extract_bpp.py — Regional BPP Pembangkitan (generation cost of supply) extraction.

Source: Kepmen ESDM No. 169.K/HK.02/MEM.M/2021
        "Besaran Biaya Pokok Penyediaan Pembangkitan PT PLN (Persero) Tahun 2020"
        File: docs/Kepmen No. 169.K.HK.02.MEM.M.2021.pdf, Lampiran pp.6-8

This is **generation BPP only** (BPP Pembangkitan), not full cost-of-supply BPP.
Full BPP (1,599 Rp/kWh per BPK audit, PLN Statistik 2023 Graph 11) includes T&D
and overhead. Generation BPP (1,027.70 Rp/kWh national avg) is the appropriate
comparator for solar LCOE since solar also excludes T&D costs.

FX rate in document: 14,572 IDR/USD (2020 Bank Indonesia avg).
We convert at our model rate (15,800 IDR/USD) in the pipeline, not here.

Vintage: FY2020. Valid from 8 Sep 2021 until superseded (Diktum KEEMPAT: remains
in force until a newer decree is issued).

Pattern: hardcoded VERIFIED dict (vision-extracted from scanned PDF), same as
pdf_extract_esdm_tech.py. Public API returns {grid_region_id: bpp_rp_kwh}.
"""

from __future__ import annotations

# ─── VERIFIED BPP DATA ──────────────────────────────────────────────────────
# Vision-extracted from Kepmen 169/2021 Lampiran, pages 6-8.
# All values in Rp/kWh. Bold values in the PDF are system-level aggregates;
# sub-system values (islands, isolated grids) are listed but not used here
# because our grid_region_id maps to the system level.

VERIFIED_BPP_PEMBANGKITAN_2020: dict[str, dict] = {
    # ─── A. SUMATERA ───────────────────────────────────────────────
    "ACEH": {"bpp_rp_kwh": 1_349.72, "usc_kwh": 9.26},
    "SUMATERA_UTARA": {"bpp_rp_kwh": 1_247.24, "usc_kwh": 8.56},
    "SUMATERA_BARAT": {"bpp_rp_kwh": 995.58, "usc_kwh": 6.83},
    "RIAU": {"bpp_rp_kwh": 1_374.43, "usc_kwh": 9.43},
    "S2JB": {"bpp_rp_kwh": 1_038.29, "usc_kwh": 7.13},  # Sumatera Selatan, Jambi, Bengkulu
    "LAMPUNG": {"bpp_rp_kwh": 995.98, "usc_kwh": 6.83},
    "BANGKA": {"bpp_rp_kwh": 2_006.52, "usc_kwh": 13.77},
    "BELITUNG": {"bpp_rp_kwh": 1_962.01, "usc_kwh": 13.46},
    # ─── B. JAWA BALI ──────────────────────────────────────────────
    "DKI_JAKARTA": {"bpp_rp_kwh": 908.15, "usc_kwh": 6.23},
    "BANTEN": {"bpp_rp_kwh": 907.75, "usc_kwh": 6.23},
    "JAWA_BARAT": {"bpp_rp_kwh": 907.93, "usc_kwh": 6.23},
    "JAWA_TENGAH": {"bpp_rp_kwh": 907.77, "usc_kwh": 6.23},
    "JAWA_TIMUR": {"bpp_rp_kwh": 911.59, "usc_kwh": 6.26},
    "BALI": {"bpp_rp_kwh": 908.03, "usc_kwh": 6.23},
    # ─── C. KALIMANTAN ─────────────────────────────────────────────
    "KALIMANTAN_BARAT": {"bpp_rp_kwh": 1_539.19, "usc_kwh": 10.56},
    "KALIMANTAN_SELTENG": {"bpp_rp_kwh": 1_244.07, "usc_kwh": 8.54},
    "KALIMANTAN_TIMUT": {"bpp_rp_kwh": 1_321.11, "usc_kwh": 9.07},
    # ─── D. SULAWESI ───────────────────────────────────────────────
    # Sulawesi Utara, Tengah, Gorontalo — subsystems:
    "SULUT_MANADO": {"bpp_rp_kwh": 1_540.41, "usc_kwh": 10.57},
    "PALU_POSO": {"bpp_rp_kwh": 1_090.58, "usc_kwh": 7.48},
    # Sulawesi Selatan, Tenggara, Barat:
    "SULSEL": {"bpp_rp_kwh": 959.02, "usc_kwh": 6.58},
    "KENDARI": {"bpp_rp_kwh": 1_059.86, "usc_kwh": 7.27},
    # ─── E. NUSA TENGGARA ──────────────────────────────────────────
    "NTB_TAMBORA": {"bpp_rp_kwh": 1_841.12, "usc_kwh": 12.63},
    "NTB_LOMBOK": {"bpp_rp_kwh": 1_715.65, "usc_kwh": 11.77},
    # NTT subsystems:
    "NTT_SUMBA": {"bpp_rp_kwh": 2_147.66, "usc_kwh": 14.74},
    "NTT_TIMOR": {"bpp_rp_kwh": 2_067.93, "usc_kwh": 14.19},
    "NTT_FLORES_BARAT": {"bpp_rp_kwh": 1_634.50, "usc_kwh": 11.22},
    "NTT_FLORES_TIMUR": {"bpp_rp_kwh": 1_856.59, "usc_kwh": 12.74},
    # ─── F. MALUKU DAN PAPUA ───────────────────────────────────────
    "AMBON": {"bpp_rp_kwh": 2_413.34, "usc_kwh": 16.56},
    "TERNATE_TIDORE": {"bpp_rp_kwh": 2_199.09, "usc_kwh": 15.09},
    "TUAL": {"bpp_rp_kwh": 1_283.31, "usc_kwh": 8.81},
    # Papua:
    "JAYAPURA": {"bpp_rp_kwh": 1_800.36, "usc_kwh": 12.35},
    "SORONG": {"bpp_rp_kwh": 1_491.05, "usc_kwh": 10.23},
    "TIMIKA": {"bpp_rp_kwh": 1_962.06, "usc_kwh": 13.46},
    "MERAUKE": {"bpp_rp_kwh": 2_349.75, "usc_kwh": 16.12},
    "MANOKWARI": {"bpp_rp_kwh": 1_602.29, "usc_kwh": 11.00},
    # ─── NATIONAL ──────────────────────────────────────────────────
    "NASIONAL": {"bpp_rp_kwh": 1_027.70, "usc_kwh": 7.05},
}

# FX rate used in the Kepmen document (for reference only — not used in our pipeline)
BPP_DOCUMENT_FX_RATE: float = 14_572.0  # Rp/USD, 2020 Bank Indonesia average

# ─── MAPPING TO grid_region_id ──────────────────────────────────────────────
# Our model uses 7 grid_region_ids (from kek_grid_region_mapping.csv).
# Each maps to one or more Kepmen PLN systems. Where multiple subsystems exist,
# we use a simple average (appropriate since these are system-level BPP values
# and our KEKs don't have load-weighted capacity data per subsystem).

_GRID_REGION_BPP_MAPPING: dict[str, list[str]] = {
    "JAVA_BALI": [
        "DKI_JAKARTA",
        "BANTEN",
        "JAWA_BARAT",
        "JAWA_TENGAH",
        "JAWA_TIMUR",
        "BALI",
    ],
    "SUMATERA": [
        # All Sumatera systems including Riau Islands KEKs (Batam, Nongsa, etc.)
        # Riau Islands physically use Batam grid but mapped to SUMATERA in our model.
        "ACEH",
        "SUMATERA_UTARA",
        "SUMATERA_BARAT",
        "RIAU",
        "S2JB",
        "LAMPUNG",
        "BANGKA",
        "BELITUNG",
    ],
    "KALIMANTAN": [
        "KALIMANTAN_BARAT",
        "KALIMANTAN_SELTENG",
        "KALIMANTAN_TIMUT",
    ],
    "SULAWESI": [
        # Likupang + Bitung → Sulut/Manado system
        # Palu → Palu/Poso subsystem
        # Using all major systems
        "SULUT_MANADO",
        "PALU_POSO",
        "SULSEL",
        "KENDARI",
    ],
    "NTB": [
        "NTB_TAMBORA",
        "NTB_LOMBOK",
    ],
    "MALUKU": [
        # Morotai KEK → North Maluku (Ternate-Tidore system)
        "AMBON",
        "TERNATE_TIDORE",
        "TUAL",
    ],
    "PAPUA": [
        # Sorong KEK → Sorong system
        "JAYAPURA",
        "SORONG",
        "TIMIKA",
        "MERAUKE",
        "MANOKWARI",
    ],
}


def get_regional_bpp() -> dict[str, float]:
    """Return BPP Pembangkitan per grid_region_id in Rp/kWh.

    Values are simple averages of the Kepmen subsystem BPP values
    that map to each grid_region_id.

    Returns:
        dict mapping grid_region_id → BPP in Rp/kWh
    """
    result: dict[str, float] = {}
    for region_id, subsystems in _GRID_REGION_BPP_MAPPING.items():
        values = [VERIFIED_BPP_PEMBANGKITAN_2020[s]["bpp_rp_kwh"] for s in subsystems]
        result[region_id] = round(sum(values) / len(values), 2)
    return result


def get_national_bpp() -> float:
    """Return the national average BPP Pembangkitan in Rp/kWh."""
    return VERIFIED_BPP_PEMBANGKITAN_2020["NASIONAL"]["bpp_rp_kwh"]


# ─── Convenience: print summary when run as script ──────────────────────────
if __name__ == "__main__":
    from src.assumptions import IDR_USD_RATE, rp_kwh_to_usd_mwh

    print("Regional BPP Pembangkitan (Kepmen ESDM 169/2021, FY2020)")
    print(f"Document FX: {BPP_DOCUMENT_FX_RATE:,.0f} IDR/USD")
    print(f"Model FX:    {IDR_USD_RATE:,.0f} IDR/USD\n")

    bpp = get_regional_bpp()
    for region, rp_kwh in sorted(bpp.items()):
        usd_mwh = rp_kwh_to_usd_mwh(rp_kwh)
        print(f"  {region:25s}  {rp_kwh:>10.2f} Rp/kWh  →  ${usd_mwh:>6.1f}/MWh")

    nat = get_national_bpp()
    print(f"\n  {'NATIONAL':25s}  {nat:>10.2f} Rp/kWh  →  ${rp_kwh_to_usd_mwh(nat):>6.1f}/MWh")
