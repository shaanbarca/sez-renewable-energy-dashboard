"""
pdf_extract_ruptl_substations — per-GI upgrade plan extractor from RUPTL PDF.

Extracts the "Rincian Rencana Pembangunan Gardu Induk" (Detailed Substation
Development Plan) tables from Lampiran A/B/C (per-province appendices). Each
row is one substation upgrade plan: name, voltage, project type
(new / extension / uprate), MVA added, target year, status.

These rows feed `fct_substation_ruptl_signal.csv`, which provides the
RUPTL-derived utilization default per substation — replacing the fixed 65%
assumption currently used in `capacity_assessment`.

Source PDF: docs/b967d-ruptl-pln-2025-2034-pub-.pdf
    Lampiran A (pp. 600-810): Sumatera + Kalimantan (15 provinces)
    Lampiran B (pp. 811-950): Jawa, Madura, Bali (7 provinces)
    Lampiran C (pp. 951-1189): Sulawesi, Maluku, Papua, Nusa Tenggara (12 provinces)

Table headers vary slightly by region but always contain 'Gardu Induk',
'Tegangan', and a project-type column matching one of:
    New/Ext/Upr         (Sumatera)
    Baru/Ext/Upr        (Kalimantan)
    Baru/Ext./Uprate    (Jawa-Bali)

Output columns (one row per GI upgrade plan):
    substation_name_raw   str    RUPTL GI label as written (e.g. "Sigli", "Arun (Arah Sigli)")
    substation_name       str    cleaned (arah/directional suffix stripped)
    voltage_kv_raw        str    as written, e.g. "150/20" or "275/150 kV"
    voltage_primary_kv    int    primary side kV (e.g. 275 for "275/150")
    voltage_secondary_kv  int    secondary side kV (e.g. 150 for "275/150"); None if single-level
    project_type          str    "new" | "extension" | "uprate" | "line_bay"
    mva_added             float  MVA added by this line item; 0.0 for line-bay-only entries
    target_year_re_base   int    COD year under RE Base scenario; None if "-"
    target_year_ared      int    COD year under ARED scenario; None if "-"
    status                str    "rencana" | "konstruksi" | "pengadaan" | "other"
    province              str    Indonesian province (from appendix header)
    grid_region_id        str    maps to dim_sites.grid_region_id
    ruptl_source_table    str    source table label, e.g. "A1.17"
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pdfplumber

# RUPTL GI-detail table column layout (fixed once header shape is known):
# [No, Gardu Induk, Tegangan, project-type, Kapasitas, COD_REbase, COD_ARED, Status]
_GI_HEADER_MIN_COLS = 6  # minimum columns to recognize header/continuation rows
_COD_RE_BASE_IDX = 5
_COD_ARED_IDX = 6
_STATUS_IDX = 7
_GI_ROW_MIN_COLS = _STATUS_IDX  # row needs ≥7 columns to reach COD_ARED/status safely

REPO_ROOT = Path(__file__).resolve().parents[2]
RUPTL_PDF = REPO_ROOT / "docs" / "b967d-ruptl-pln-2025-2034-pub-.pdf"

# Per-province page ranges (based on spike scan of Lampiran A/B/C headers).
# End page = (next province's start - 1). Last province caps at 1190 (Lampiran D).
PROVINCE_RANGES: dict[str, tuple[int, int, str]] = {
    # (province, start_page, end_page, grid_region_id)
    "ACEH": (601, 614, "SUMATERA"),
    "SUMATERA UTARA": (615, 631, "SUMATERA"),
    "RIAU": (632, 643, "SUMATERA"),
    "KEPULAUAN RIAU": (644, 656, "SUMATERA"),
    "KEPULAUAN BANGKA BELITUNG": (657, 667, "SUMATERA"),
    "SUMATERA BARAT": (668, 679, "SUMATERA"),
    "JAMBI": (680, 690, "SUMATERA"),
    "SUMATERA SELATAN": (691, 703, "SUMATERA"),
    "BENGKULU": (704, 714, "SUMATERA"),
    "LAMPUNG": (715, 726, "SUMATERA"),
    "KALIMANTAN BARAT": (727, 743, "KALIMANTAN"),
    "KALIMANTAN TENGAH": (744, 757, "KALIMANTAN"),
    "KALIMANTAN SELATAN": (758, 770, "KALIMANTAN"),
    "KALIMANTAN TIMUR": (771, 795, "KALIMANTAN"),
    "KALIMANTAN UTARA": (796, 810, "KALIMANTAN"),
    "BANTEN": (812, 823, "JAVA_BALI"),
    "DKI JAKARTA": (824, 840, "JAVA_BALI"),
    "JAWA BARAT": (841, 873, "JAVA_BALI"),
    "JAWA TENGAH": (874, 897, "JAVA_BALI"),
    "DI YOGYAKARTA": (898, 904, "JAVA_BALI"),
    "JAWA TIMUR": (905, 937, "JAVA_BALI"),
    "BALI": (938, 950, "JAVA_BALI"),
    "SULAWESI UTARA": (952, 970, "SULAWESI"),
    "SULAWESI TENGAH": (971, 989, "SULAWESI"),
    "GORONTALO": (990, 1000, "SULAWESI"),
    "SULAWESI SELATAN": (1001, 1028, "SULAWESI"),
    "SULAWESI TENGGARA": (1029, 1048, "SULAWESI"),
    "SULAWESI BARAT": (1049, 1060, "SULAWESI"),
    "MALUKU": (1061, 1083, "MALUKU"),
    "MALUKU UTARA": (1084, 1103, "MALUKU"),
    "PAPUA": (1104, 1129, "PAPUA"),
    "PAPUA BARAT": (1130, 1149, "PAPUA"),
    "NUSA TENGGARA BARAT": (1150, 1165, "NUSA_TENGGARA"),
    "NUSA TENGGARA TIMUR": (1166, 1189, "NUSA_TENGGARA"),
}

# ─── Row dataclass ────────────────────────────────────────────────────────────


@dataclass
class SubstationPlanRow:
    substation_name_raw: str
    substation_name: str
    voltage_kv_raw: str
    voltage_primary_kv: int | None
    voltage_secondary_kv: int | None
    project_type: str  # new | extension | uprate | line_bay
    mva_added: float
    target_year_re_base: int | None
    target_year_ared: int | None
    status: str
    province: str
    grid_region_id: str
    ruptl_source_table: str


# ─── Parsers ──────────────────────────────────────────────────────────────────

_NEW_TOKENS = {"new", "baru"}
_EXT_TOKENS = {"ext", "ext.", "extension", "perluasan"}
_UPR_TOKENS = {"upr", "uprate", "uprating"}
_LB_TOKENS = {"lb", "ext lb", "bay"}


def parse_project_type(raw: str | None) -> str:
    """Map RUPTL project-type label to a canonical value.

    Handles variants: New, Baru, Ext, Ext., Uprate, Upr, Ext LB.
    Returns one of: "new", "extension", "uprate", "line_bay", "other".
    """
    if not raw:
        return "other"
    s = str(raw).strip().lower().replace("\n", " ")
    # Check most specific first
    if "lb" in s.split() or s in {"ext lb", "ext. lb"}:
        return "line_bay"
    tokens = [t.strip(".") for t in s.replace("/", " ").split()]
    if any(t in _UPR_TOKENS for t in tokens):
        return "uprate"
    if any(t in _EXT_TOKENS for t in tokens):
        return "extension"
    if any(t in _NEW_TOKENS for t in tokens):
        return "new"
    return "other"


_MVA_PRODUCT_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)")
_MVA_BARE_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*$")
_LB_RE = re.compile(r"(\d+)\s*(?:LB|Bay|Dia)", re.IGNORECASE)


def parse_kapasitas(raw: str | None) -> float:
    """Parse the 'Kapasitas (MVA)/LB' cell into a float MVA value.

    Handles:
        "1x60"     -> 60.0
        "2x250"    -> 500.0
        "1 x 30"   -> 30.0
        "120"      -> 120.0   (Jawa-Bali uses bare numbers)
        "2 LB"     -> 0.0     (line bay, no transformer MVA)
        "4 Dia"    -> 0.0
        "-"        -> 0.0
    """
    if not raw:
        return 0.0
    s = str(raw).strip().replace(",", ".").replace("\n", " ")
    if not s or s == "-":
        return 0.0
    m = _MVA_PRODUCT_RE.search(s)
    if m:
        return float(m.group(1)) * float(m.group(2))
    m = _MVA_BARE_RE.match(s)
    if m:
        return float(m.group(1))
    # LB / Bay / Dia with no MVA → line-bay only
    if _LB_RE.search(s):
        return 0.0
    return 0.0


_VOLTAGE_SPLIT_RE = re.compile(r"(\d+)\s*(?:/\s*(\d+))?")


def parse_voltage(raw: str | None) -> tuple[int | None, int | None, str]:
    """Parse 'Tegangan (kV)' cell into (primary_kv, secondary_kv, raw).

    Examples:
        "150/20"     -> (150, 20)
        "275/150 kV" -> (275, 150)
        "500"        -> (500, None)
        "150"        -> (150, None)
    """
    if not raw:
        return (None, None, "")
    s = str(raw).strip().replace("\n", " ")
    m = _VOLTAGE_SPLIT_RE.search(s)
    if not m:
        return (None, None, s)
    primary = int(m.group(1)) if m.group(1) else None
    secondary = int(m.group(2)) if m.group(2) else None
    return (primary, secondary, s)


def parse_year(raw: str | None) -> int | None:
    """Parse COD year cell. Returns None for '-' or empty."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s or s == "-":
        return None
    m = re.search(r"20\d{2}", s)
    return int(m.group(0)) if m else None


_STATUS_MAP = {
    "rencana": "rencana",
    "konstruksi": "konstruksi",
    "pengadaan": "pengadaan",
    "studi": "studi",
    "komisioning": "komisioning",
    "committed": "committed",
}


def parse_status(raw: str | None) -> str:
    if not raw:
        return "other"
    key = str(raw).strip().lower().split()[0] if str(raw).strip() else ""
    return _STATUS_MAP.get(key, "other")


_ARAH_SUFFIX_RE = re.compile(r"\s*\(\s*(?:arah|ke|dari)\s.*?\)\s*$", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_substation_name(raw: str) -> str:
    """Strip directional suffixes (Arah X) and normalize whitespace.

    '(Arah Sigli)', '(arah Nias Barat)' — these refer to a bay on the substation
    pointing toward another site, not a separate substation. For matching
    purposes, the base GI name is what we need.
    """
    if not raw:
        return ""
    s = str(raw).replace("\n", " ").strip()
    s = _ARAH_SUFFIX_RE.sub("", s)
    s = _MULTI_SPACE_RE.sub(" ", s).strip()
    return s


# ─── Table detection ──────────────────────────────────────────────────────────


def _is_gi_detail_header(row: list) -> bool:
    """Header signature: has 'Gardu Induk' + 'Tegangan' + project-type column.

    Robust to embedded newlines inside cells (e.g. 'Baru/\\nExt./\\nUprate') and
    to regional header wording variants.
    """
    if not row or len(row) < _GI_HEADER_MIN_COLS:
        return False
    # Normalize: lower-case, strip newlines and collapse whitespace
    joined = " ".join(str(c or "").lower().replace("\n", " ") for c in row)
    joined = re.sub(r"\s+", " ", joined)
    if "gardu induk" not in joined or "tegangan" not in joined:
        return False
    # Require a kapasitas column. Project-type cell varies:
    #   Sumatera:     "New/Ext/Upr"
    #   Kalimantan:   "Baru/Ext/Upr"
    #   Jawa-Bali:    "Baru/Ext./Uprate"
    #   Maluku/Papua/NTB: "Ket" (values still in position 3)
    return "kapasitas" in joined


def _find_province_tables(pdf: pdfplumber.PDF, start_page: int, end_page: int) -> list:
    """Return all (page_idx, table_idx, rows) that look like the detail table
    or its continuation (rows starting with a numeric index in same format)."""
    collected = []
    in_detail = False
    for i in range(start_page - 1, end_page):
        page = pdf.pages[i]
        for ti, t in enumerate(page.extract_tables() or []):
            if not t:
                continue
            if _is_gi_detail_header(t[0]):
                collected.append((i + 1, ti, t))
                in_detail = True
                continue
            # Continuation heuristic: first cell is numeric, row width matches,
            # and we just saw a detail table.
            if in_detail and len(t) > 0 and len(t[0]) >= _GI_HEADER_MIN_COLS:
                first_cell = str(t[0][0] or "").strip()
                if first_cell.isdigit() and len(t[0]) >= _GI_ROW_MIN_COLS:
                    collected.append((i + 1, ti, t))
                    continue
            # Reset on clearly different tables
            if t and t[0] and any("Kriteria" in str(c or "") for c in t[0]):
                in_detail = False
    return collected


def _extract_rows_from_table(
    raw_table: list,
    province: str,
    grid_region_id: str,
    source_table: str,
) -> list[SubstationPlanRow]:
    """Parse a raw pdfplumber table (list of rows) into SubstationPlanRow objects.

    Skips header / sub-header / TOTAL rows. Columns assumed:
        [No, Gardu Induk, Tegangan, New/Ext/Upr, Kapasitas, COD_REbase, COD_ARED, Status]
    """
    rows: list[SubstationPlanRow] = []
    for r in raw_table:
        if not r or len(r) < _GI_ROW_MIN_COLS:
            continue
        no = str(r[0] or "").strip()
        if not no.isdigit():
            continue
        name_raw = str(r[1] or "").strip()
        if not name_raw:
            continue
        # Column indices are fixed once header shape is known
        voltage_raw = str(r[2] or "").strip()
        ptype_raw = str(r[3] or "").strip()
        kapasitas_raw = str(r[4] or "").strip()
        cod_re_base = str(r[_COD_RE_BASE_IDX] or "").strip() if len(r) > _COD_RE_BASE_IDX else ""
        cod_ared = str(r[_COD_ARED_IDX] or "").strip() if len(r) > _COD_ARED_IDX else ""
        status_raw = str(r[_STATUS_IDX] or "").strip() if len(r) > _STATUS_IDX else ""

        vp, vs, vraw = parse_voltage(voltage_raw)
        rows.append(
            SubstationPlanRow(
                substation_name_raw=name_raw,
                substation_name=clean_substation_name(name_raw),
                voltage_kv_raw=vraw,
                voltage_primary_kv=vp,
                voltage_secondary_kv=vs,
                project_type=parse_project_type(ptype_raw),
                mva_added=parse_kapasitas(kapasitas_raw),
                target_year_re_base=parse_year(cod_re_base),
                target_year_ared=parse_year(cod_ared),
                status=parse_status(status_raw),
                province=province,
                grid_region_id=grid_region_id,
                ruptl_source_table=source_table,
            )
        )
    return rows


# ─── Public API ───────────────────────────────────────────────────────────────


def extract_substation_plans(pdf_path: Path = RUPTL_PDF) -> list[SubstationPlanRow]:
    """Extract all per-GI upgrade plans from RUPTL PDF.

    Iterates every province appendix (A.1–A.15, B.1–B.7, C.1–C.12), finds
    the 'Rincian Rencana Pembangunan Gardu Induk' table and its continuations,
    parses each data row.
    """
    all_rows: list[SubstationPlanRow] = []
    with pdfplumber.open(pdf_path) as pdf:
        for province, (start, end, region) in PROVINCE_RANGES.items():
            tables = _find_province_tables(pdf, start, end)
            # source_table label — extract from first page if visible
            source_label = f"{province.title()} (pp.{start}-{end})"
            for _pg, _ti, raw_table in tables:
                all_rows.extend(
                    _extract_rows_from_table(
                        raw_table,
                        province=province,
                        grid_region_id=region,
                        source_table=source_label,
                    )
                )
    return all_rows


def to_dataframe(rows: list[SubstationPlanRow]):
    """Convert rows to a pandas DataFrame. Keeps None-years as nullable Int64."""
    df = pd.DataFrame([r.__dict__ for r in rows])
    if not df.empty:
        for col in (
            "target_year_re_base",
            "target_year_ared",
            "voltage_primary_kv",
            "voltage_secondary_kv",
        ):
            df[col] = df[col].astype("Int64")
    return df


RAW_OUT = REPO_ROOT / "outputs" / "data" / "processed" / "raw_ruptl_substation_plans.csv"


def build_raw_ruptl_substation_plans():
    """Zero-arg entry point for run_pipeline.py. Returns the DataFrame for serialization."""
    return to_dataframe(extract_substation_plans())


def main() -> None:
    rows = extract_substation_plans()
    print(f"Extracted {len(rows)} GI upgrade plan rows")
    by_region = Counter(r.grid_region_id for r in rows)
    for region, n in sorted(by_region.items()):
        print(f"  {region:20s} {n:4d} rows")
    by_type = Counter(r.project_type for r in rows)
    print("\nBy project_type:")
    for t, n in sorted(by_type.items()):
        print(f"  {t:12s} {n:4d}")

    df = to_dataframe(rows)
    RAW_OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(RAW_OUT, index=False)
    print(f"\nWrote {len(df)} rows -> {RAW_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
