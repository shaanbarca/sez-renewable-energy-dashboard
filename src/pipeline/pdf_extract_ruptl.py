"""
pdf_extract_ruptl.py — extract PLTS (solar PV) capacity additions from RUPTL PDF.

This module provides two functions:
    extract_plts_from_pdf()   — parse PLTS tables directly from the PDF
    verify_plts_against_hardcoded() — diff PDF extraction vs. hardcoded fallback

Usage
-----
    # Run standalone to verify or re-extract:
    uv run python -m src.pipeline.pdf_extract_ruptl

    # Import in build_fct_ruptl_pipeline.py (optional live extraction):
    from src.pipeline.pdf_extract_ruptl import extract_plts_from_pdf

Source PDF
----------
    docs/b967d-ruptl-pln-2025-2034-pub-.pdf
    Keputusan Menteri ESDM No. 188.K/TL.03/MEM.L/2025

Target tables (physical PDF page numbers, 0-indexed via pdfplumber):
    Tabel 5.84  — Sumatera RE Base      → ~pages 171-172
    Tabel 5.85  — Sumatera ARED         → ~pages 172
    Tabel 5.88  — Jawa-Madura-Bali RE   → ~pages 187-188
    Tabel 5.89  — Jawa-Madura-Bali ARED → ~pages 188-189
    Tabel 5.95  — Kalimantan RE Base    → ~pages 207-208
    Tabel 5.96  — Kalimantan ARED       → ~pages 208
    Tabel 5.102 — Sulawesi RE Base      → ~pages 227-228
    Tabel 5.103 — Sulawesi ARED         → ~pages 228

Note on page numbers: The RUPTL uses chapter-prefixed page numbers (V-124, V-108).
Physical PDF page offsets are approximate — use `_find_table_page()` for reliable lookup.

Limitations
-----------
    The RUPTL PDF tables use complex multi-column headers with merged year cells.
    pdfplumber can extract text but column alignment requires post-processing.
    If extraction fails (layout change, scan artifact), `extract_plts_from_pdf()`
    returns None and the caller should fall back to the verified hardcoded data.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[2]
RUPTL_PDF = REPO_ROOT / "docs" / "b967d-ruptl-pln-2025-2034-pub-.pdf"

YEARS = list(range(2025, 2035))

# Maps grid_region_id → (RE Base table number, ARED table number)
REGION_TABLES: dict[str, tuple[str, str]] = {
    "SUMATERA": ("5.84", "5.85"),
    "JAVA_BALI": ("5.88", "5.89"),
    "KALIMANTAN": ("5.95", "5.96"),
    "SULAWESI": ("5.102", "5.103"),
}

# Row label patterns that identify the PLTS total row in each table
PLTS_ROW_PATTERNS = [
    r"(?i)total.*plts",
    r"(?i)plts.*total",
    r"(?i)^plts$",
    r"(?i)plts\s*\+\s*bess",  # Sulawesi uses PLTS+BESS packages
]

# ---------------------------------------------------------------------------
# VERIFIED_PLTS_DATA — single source of truth for hardcoded RUPTL values.
#
# Used as fallback when PDF extraction fails, and as the reference in
# verify_plts_against_hardcoded(). Also imported by build_fct_ruptl_pipeline.py
# so neither file duplicates the arrays.
#
# fmt: off
VERIFIED_PLTS_DATA: dict[str, dict] = {
    "JAVA_BALI": {
        # Source: Tabel 5.88 (RE Base) and 5.89 (ARED), Jawa-Madura-Bali, Total PLTS row
        "re_base": [666, 113, 157, 230,   0, 444,  80,    0,    0,  874],
        "ared":    [666, 433, 541, 330, 200, 849, 1858, 1813, 2593, 1036],
        "source":  "Tabel 5.88/5.89",
        "notes":   "Standalone PLTS extracted from Total row. Includes PLTS Atap (rooftop) quota.",
    },
    "SUMATERA": {
        # Source: Tabel 5.84 (RE Base) and 5.85 (ARED), Total PLTS row
        "re_base": [  5,  64,  57,  27, 314, 193,  53, 179, 603, 111],
        "ared":    [  5,  64,  57,  27, 314, 193,  53, 179, 603, 111],
        # Note: Tabel 5.85 ARED shows similar PLTS to RE Base; primary ARED uplift
        # in Sumatera is from PLTA and PLTB (wind), not PLTS.
        "source":  "Tabel 5.84/5.85",
        "notes":   "ARED PLTS ≈ RE Base for Sumatera; ARED uplift primarily from PLTA/PLTB.",
    },
    "KALIMANTAN": {
        # Source: Tabel 5.95 (RE Base) and 5.96 (ARED), Kalimantan Total PLTS row
        "re_base": [ 55,  17, 146,  50,  15,  44,   0,  40,  50,  50],
        "ared":    [ 55,  97, 346, 290, 335, 244,   0,  40,  50,  50],
        "source":  "Tabel 5.95/5.96",
        "notes":   "Includes PLN (IKN *50MW in 2025 not in DMN), SH-PLN, and IPP PLTS.",
    },
    "SULAWESI": {
        # Source: Tabel 5.102 (RE Base) and 5.103 (ARED), Total PLTS+BESS row
        "re_base": [ 13,  15,  79,  72,  22,   5,  74,  47,  80,   0],
        "ared":    [ 13,  15,  79, 309,  90, 234, 294,  47, 450,   0],
        "source":  "Tabel 5.102/5.103",
        "notes":   "Values are PLTS+BESS combined packages. Actual PLTS MW ≈ 80-90% of listed.",
    },
    "MALUKU": {
        # All PLTS entries are asterisked (*) = not in DMN capacity balance
        "re_base": [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "ared":    [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "source":  "Tabel 5.104/5.105/5.106/5.107",
        "notes":   "All PLTS is asterisked (quota/distributed only, not in DMN balance).",
    },
    "PAPUA": {
        "re_base": [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "ared":    [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "source":  "Tabel 5.108/5.109 (Jayapura); Sorong system not in available tables",
        "notes":   "PLTS+BESS 100 MWac quota (2028-2030) asterisked/not in DMN balance.",
    },
    "NTB": {
        "re_base": [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "ared":    [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        "source":  "V.5.7.6 Maluku/Papua/Nusa Tenggara section",
        "notes":   "NTB (Lombok-Sumbawa) isolated system; detailed PLTS table not available.",
    },
}
# fmt: on


# ─── Page finder ──────────────────────────────────────────────────────────────


def _find_table_page(pdf: pdfplumber.PDF, table_number: str) -> Optional[int]:
    """
    Search PDF pages for a table heading matching 'Tabel {table_number}'.
    Returns 0-indexed physical page number, or None if not found.
    """
    pattern = re.compile(rf"Tabel\s+{re.escape(table_number)}\b", re.IGNORECASE)
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if pattern.search(text):
            return i
    return None


# ─── Row extractor ────────────────────────────────────────────────────────────


def _extract_plts_row(page: pdfplumber.page.Page) -> Optional[list[float]]:
    """
    Extract the 10 annual PLTS MW values from a single PDF page.

    Strategy:
        1. Extract all tables on the page via pdfplumber.
        2. For each table row, check if the first cell matches a PLTS pattern.
        3. Parse the remaining cells as floats (10 year values: 2025–2034).

    Returns a list of 10 floats, or None if no PLTS row found.
    """
    tables = page.extract_tables()
    for table in tables:
        for row in table:
            if not row or not row[0]:
                continue
            cell_text = str(row[0]).strip()
            if any(re.search(p, cell_text) for p in PLTS_ROW_PATTERNS):
                # Try to parse numeric values from the rest of the row
                values = []
                for cell in row[1:]:
                    try:
                        # Remove thousand separators and trailing notes
                        clean = re.sub(r"[^\d.\-]", "", str(cell) or "")
                        values.append(float(clean) if clean else 0.0)
                    except (ValueError, TypeError):
                        values.append(0.0)
                # Keep only first 10 values (year columns 2025–2034)
                if len(values) >= 10:
                    return [round(v) for v in values[:10]]
    return None


# ─── Main extractor ───────────────────────────────────────────────────────────


def extract_plts_from_pdf(
    pdf_path: Path = RUPTL_PDF,
) -> Optional[dict[str, dict]]:
    """
    Extract PLTS additions per grid region from the RUPTL PDF.

    Returns a dict with the same structure as VERIFIED_PLTS_DATA:
        {region: {"re_base": [...], "ared": [...], "source": "..."}}

    Returns None if the PDF is missing or extraction fails for any region.
    The caller should fall back to the hardcoded verified data on None.
    """
    if not pdf_path.exists():
        print(f"  [pdf_extract] PDF not found: {pdf_path.name} — using hardcoded fallback")
        return None

    result: dict[str, dict] = {}
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for region, (re_table, ared_table) in REGION_TABLES.items():
                re_page_num = _find_table_page(pdf, re_table)
                ared_page_num = _find_table_page(pdf, ared_table)

                if re_page_num is None or ared_page_num is None:
                    print(
                        f"  [pdf_extract] {region}: table pages not found — using hardcoded fallback"
                    )
                    return None

                # Table may span to the next page — search current + next
                re_vals: Optional[list[float]] = None
                for offset in range(3):
                    pg_idx = re_page_num + offset
                    if pg_idx >= len(pdf.pages):
                        break
                    re_vals = _extract_plts_row(pdf.pages[pg_idx])
                    if re_vals:
                        break

                ared_vals: Optional[list[float]] = None
                for offset in range(3):
                    pg_idx = ared_page_num + offset
                    if pg_idx >= len(pdf.pages):
                        break
                    ared_vals = _extract_plts_row(pdf.pages[pg_idx])
                    if ared_vals:
                        break

                if re_vals is None or ared_vals is None:
                    print(
                        f"  [pdf_extract] {region}: PLTS row not found — using hardcoded fallback"
                    )
                    return None

                result[region] = {
                    "re_base": re_vals,
                    "ared": ared_vals,
                    "source": f"Tabel {re_table}/{ared_table} — extracted from {pdf_path.name}",
                }
    except Exception as e:
        print(f"  [pdf_extract] extraction error: {e} — using hardcoded fallback")
        return None

    # Regions with no PDF tables — copy from VERIFIED_PLTS_DATA (all zeros + notes)
    for region in ["MALUKU", "PAPUA", "NTB"]:
        result[region] = VERIFIED_PLTS_DATA[region].copy()

    return result


# ─── Verification ─────────────────────────────────────────────────────────────


def verify_plts_against_hardcoded(pdf_path: Path = RUPTL_PDF) -> bool:
    """
    Extract PDF data and diff against the hardcoded verified values.

    Prints a per-region, per-year comparison.  Returns True if all values match
    within ±5 MW (rounding tolerance), False if any material discrepancy found.
    """
    print("\nVerifying PLTS extraction against hardcoded values...")
    print(f"  PDF: {pdf_path.name}")

    extracted = extract_plts_from_pdf(pdf_path)
    if extracted is None:
        print("  RESULT: extraction failed — cannot verify")
        return False

    all_ok = True
    for region in REGION_TABLES:
        if region not in extracted or region not in VERIFIED_PLTS_DATA:
            continue
        ext = extracted[region]
        hc = VERIFIED_PLTS_DATA[region]
        for scenario in ("re_base", "ared"):
            for i, year in enumerate(YEARS):
                e_val = ext[scenario][i]
                h_val = hc[scenario][i]
                if abs(e_val - h_val) > 5:
                    print(
                        f"  MISMATCH  {region}/{scenario}/{year}: "
                        f"extracted={e_val}, hardcoded={h_val}"
                    )
                    all_ok = False

    if all_ok:
        print("  RESULT: all values match — hardcoded data is consistent with PDF")
    else:
        print("  RESULT: discrepancies found — review and update hardcoded data or PDF extraction")

    return all_ok


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("RUPTL PDF extractor")
    print("=" * 60)

    extracted = extract_plts_from_pdf()
    if extracted is None:
        print(
            "\nExtraction failed. Hardcoded fallback in build_fct_ruptl_pipeline.py will be used."
        )
    else:
        print(f"\nExtracted {len(extracted)} regions:")
        for region, data in extracted.items():
            total_re = sum(data["re_base"])
            total_ared = sum(data["ared"])
            print(
                f"  {region:12s}  RE Base: {total_re:5.0f} MW  ARED: {total_ared:5.0f} MW  ({data['source']})"
            )

    print()
    verify_plts_against_hardcoded()
