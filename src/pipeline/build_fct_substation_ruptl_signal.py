"""
build_fct_substation_ruptl_signal — derive per-substation RUPTL upgrade signal.

Joins extracted RUPTL substation upgrade plans (raw_ruptl_substation_plans.csv)
against the physical substation stock (data/substation.geojson) and emits one
row per existing PLN substation with a rolled-up upgrade-intent signal.

This replaces the fixed 65% utilization assumption with a per-substation
default driven by whether PLN themselves plan to upgrade that asset in
RUPTL 2025-2034.

Matching strategy (tiered, highest confidence first):
    1. Exact normalized-name match within same grid region (high)
    2. Token-set ratio >= 85 within same grid region (medium)
    3. Token-set ratio >= 75 within same region + matching voltage_primary (lower)
    4. Unmatched -> no signal (fall back to default utilization downstream)

Noise filtered before matching:
    - Placeholder names ("Eksisting/Baru", "Tersebar", etc.) — these are
      province-level generation-connection line items with no specific GI.
    - project_type == "new" — these substations don't exist yet in the
      stock, so they can't match and shouldn't be attempted.

Aggregation: one RUPTL substation name may match one or many features in the
geojson (substation.geojson has ~2,913 features where many are per-bay / per-
line entries for the same GI site). We aggregate up to the GI level:
    - strongest project_type       (uprate > extension > line_bay)
    - sum of mva_added
    - strongest status              (konstruksi > committed > pengadaan > rencana)
    - earliest target year          (min of RE Base / ARED)
    - count of RUPTL line items

Output: outputs/data/processed/fct_substation_ruptl_signal.csv
Columns:
    namobj                        str   PLN substation label (join key to geojson)
    regpln                        str   PLN region (join key)
    has_planned_upgrade           bool
    mva_added_total               float sum of MVA across matched plans
    project_type_strongest        str   uprate / extension / line_bay
    strongest_status              str   konstruksi / committed / pengadaan / rencana
    earliest_target_year          int
    match_confidence              str   high / medium / lower
    n_ruptl_matches               int
    ruptl_substation_name_matched str   raw RUPTL name(s) matched (comma-joined)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

_ALIAS_SPLIT_PARTS = 2  # "X / Y" alias form has exactly 2 halves

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
RAW_PLANS = PROCESSED / "raw_ruptl_substation_plans.csv"
SUBSTATIONS_GEOJSON = REPO_ROOT / "data" / "substation.geojson"
OUT_CSV = PROCESSED / "fct_substation_ruptl_signal.csv"

# ─── Ranking ──────────────────────────────────────────────────────────────────

_PROJECT_TYPE_RANK = {"uprate": 3, "extension": 2, "line_bay": 1, "other": 0, "new": -1}
_STATUS_RANK = {
    "konstruksi": 4,
    "committed": 3,
    "pengadaan": 2,
    "rencana": 1,
    "studi": 0,
    "other": -1,
}


def strongest_project_type(types: list[str]) -> str:
    if not types:
        return "other"
    return max(types, key=lambda t: _PROJECT_TYPE_RANK.get(t, -2))


def strongest_status(statuses: list[str]) -> str:
    if not statuses:
        return "other"
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, -2))


# ─── Name normalization ───────────────────────────────────────────────────────

# Tokens that identify the substation type/voltage, not the name itself.
_STRIP_PATTERNS = [
    re.compile(r"^\s*gitet\b", re.IGNORECASE),
    re.compile(r"^\s*gis\b", re.IGNORECASE),
    re.compile(r"^\s*gi\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*kv\b", re.IGNORECASE),
    re.compile(r"\(\s*\d+\s*mva[^)]*\)", re.IGNORECASE),  # "(30 MVA No.1)"
    re.compile(r"\s+\d+\s*$"),  # trailing bare digit ("Parungmulya 1")
]

_PLACEHOLDER_PATTERNS = [
    re.compile(r"eksisting", re.IGNORECASE),
    re.compile(r"eksisiting", re.IGNORECASE),  # RUPTL typo variant
    re.compile(r"tersebar", re.IGNORECASE),
    re.compile(r"^(?:gi|gitet)\s+eksist", re.IGNORECASE),
]


def is_placeholder(raw_name: str) -> bool:
    """Reject province-level placeholder names that can't be matched to a specific GI."""
    if not raw_name:
        return True
    return any(p.search(raw_name) for p in _PLACEHOLDER_PATTERNS)


def normalize_name(name: str) -> str:
    """Aggressive normalization for fuzzy matching.

    Lowercase, strip GI/GITET/GIS prefix, drop voltage tokens, drop "(30 MVA No.1)"
    style annotations, collapse whitespace, remove trailing bare digits (so
    "Parungmulya" == "Parungmulya 1" == "Parungmulya 2").
    """
    if not name:
        return ""
    s = str(name).lower().strip()
    # Handle "X / Y" alias form — keep the longer half (real GI name,
    # not the functional alias).
    if "/" in s and "kv" not in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
        if len(parts) == _ALIAS_SPLIT_PARTS and " " in parts[0] and " " not in parts[1]:
            s = parts[0]  # "Teluk Jambe / Parungmulya" -> "teluk jambe"
        elif len(parts) == _ALIAS_SPLIT_PARTS:
            s = max(parts, key=len)
    for pat in _STRIP_PATTERNS:
        s = pat.sub(" ", s)
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Drop trailing " 1"/" 2" suffix on single-word names ("parungmulya 1" -> "parungmulya")
    s = re.sub(r"^(\w+)\s+\d+$", r"\1", s)
    return s


def token_set(name: str) -> set[str]:
    return set(normalize_name(name).split())


def token_set_ratio(a: str, b: str) -> float:
    """Simple token-set similarity: |intersect| / |union|."""
    ta, tb = token_set(a), token_set(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union)


# ─── Load ─────────────────────────────────────────────────────────────────────


def load_substations(geojson_path: Path = SUBSTATIONS_GEOJSON) -> pd.DataFrame:
    """Load substation.geojson into a DataFrame (one row per geojson feature)."""
    with geojson_path.open() as f:
        gj = json.load(f)
    rows = []
    for idx, feat in enumerate(gj["features"]):
        p = feat["properties"]
        teggi = p.get("teggi") or ""
        # teggi comes as "150 kV" — extract int
        vm = re.search(r"(\d+)", str(teggi))
        rows.append(
            {
                "feature_idx": idx,
                "namobj": p.get("namobj") or "",
                "regpln": p.get("regpln") or "",
                "teggi_raw": teggi,
                "voltage_primary_kv": int(vm.group(1)) if vm else None,
                "kapgi_mva": p.get("kapgi"),
            }
        )
    return pd.DataFrame(rows)


def load_ruptl_plans(csv_path: Path = RAW_PLANS) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Filter noise
    # 1. Drop project_type == "new" — these GIs don't exist yet, can't match stock
    df = df[df["project_type"] != "new"].copy()
    # 2. Drop placeholder substations (Eksisting/Baru etc.)
    df = df[~df["substation_name"].apply(is_placeholder)].copy()
    return df


# ─── Region mapping (RUPTL grid_region_id  ->  geojson regpln) ────────────────

_GRID_TO_REGPLN = {
    "SUMATERA": "Sumatera",
    "JAVA_BALI": "Jawa-Bali",
    "KALIMANTAN": "Kalimantan",
    "SULAWESI": "Sulawesi",
    "MALUKU": "Maluku",
    "PAPUA": "Papua",
    "NUSA_TENGGARA": "Nusa Tenggara",
}


# ─── Matcher ──────────────────────────────────────────────────────────────────


def match_ruptl_to_substation(
    ruptl: pd.DataFrame,
    substations: pd.DataFrame,
    fuzzy_threshold_high: float = 0.85,
    fuzzy_threshold_low: float = 0.75,
) -> pd.DataFrame:
    """For each RUPTL row, find matching substation features.

    Returns a long DataFrame with (ruptl_idx, feature_idx, namobj, confidence).
    One RUPTL row may match multiple geojson features (e.g. "Sigli" matches 3
    Sigli features because sub.geojson stores per-bay entries).
    """
    # Pre-compute normalized names + token sets on both sides
    substations = substations.copy()
    substations["name_norm"] = substations["namobj"].apply(normalize_name)
    substations["name_tokens"] = substations["namobj"].apply(token_set)
    ruptl = ruptl.copy()
    ruptl["name_norm"] = ruptl["substation_name"].apply(normalize_name)
    ruptl["name_tokens"] = ruptl["substation_name"].apply(token_set)

    # Build per-region substation indices for fast scoped lookup
    results = []
    for _, rrow in ruptl.iterrows():
        target_regpln = _GRID_TO_REGPLN.get(rrow["grid_region_id"])
        if not target_regpln:
            continue
        region_subs = substations[substations["regpln"] == target_regpln]
        if region_subs.empty:
            continue

        target_norm = rrow["name_norm"]
        target_tokens = rrow["name_tokens"]
        target_voltage = rrow.get("voltage_primary_kv")
        if pd.isna(target_voltage):
            target_voltage = None

        # Tier 1: exact normalized match
        tier_a = region_subs[region_subs["name_norm"] == target_norm]
        if len(tier_a) > 0:
            for _, srow in tier_a.iterrows():
                results.append(
                    {
                        "ruptl_idx": rrow.name,
                        "feature_idx": srow["feature_idx"],
                        "namobj": srow["namobj"],
                        "regpln": srow["regpln"],
                        "confidence": "high",
                    }
                )
            continue

        # Tier 2 & 3: token-set ratio
        best_score = 0.0
        best_rows = []
        for _, srow in region_subs.iterrows():
            if not srow["name_tokens"] or not target_tokens:
                continue
            inter = target_tokens & srow["name_tokens"]
            union = target_tokens | srow["name_tokens"]
            score = len(inter) / len(union) if union else 0.0
            if score > best_score:
                best_score = score
                best_rows = [srow]
            elif score == best_score and score > 0:
                best_rows.append(srow)

        if best_score >= fuzzy_threshold_high:
            for srow in best_rows:
                results.append(
                    {
                        "ruptl_idx": rrow.name,
                        "feature_idx": srow["feature_idx"],
                        "namobj": srow["namobj"],
                        "regpln": srow["regpln"],
                        "confidence": "medium",
                    }
                )
        elif best_score >= fuzzy_threshold_low and target_voltage is not None:
            # Extra guard: require voltage match at lower confidence
            for srow in best_rows:
                if srow["voltage_primary_kv"] == target_voltage:
                    results.append(
                        {
                            "ruptl_idx": rrow.name,
                            "feature_idx": srow["feature_idx"],
                            "namobj": srow["namobj"],
                            "regpln": srow["regpln"],
                            "confidence": "lower",
                        }
                    )
        # else: no match, RUPTL row is orphaned

    return pd.DataFrame(results)


# ─── Aggregation ──────────────────────────────────────────────────────────────


def build_fct_substation_ruptl_signal(
    ruptl: pd.DataFrame,
    substations: pd.DataFrame,
) -> pd.DataFrame:
    matches = match_ruptl_to_substation(ruptl, substations)
    if matches.empty:
        # Emit empty shell — nothing matched
        return pd.DataFrame(
            columns=[
                "namobj",
                "regpln",
                "has_planned_upgrade",
                "mva_added_total",
                "project_type_strongest",
                "strongest_status",
                "earliest_target_year",
                "match_confidence",
                "n_ruptl_matches",
                "ruptl_substation_name_matched",
            ]
        )

    # Join match rows back with RUPTL plan attributes
    enriched = matches.merge(
        ruptl[
            [
                "substation_name",
                "project_type",
                "mva_added",
                "target_year_re_base",
                "target_year_ared",
                "status",
            ]
        ],
        left_on="ruptl_idx",
        right_index=True,
        how="left",
    )

    # Earliest of the two COD years per line
    def earliest_year(row):
        candidates = [row["target_year_re_base"], row["target_year_ared"]]
        candidates = [c for c in candidates if pd.notna(c)]
        return int(min(candidates)) if candidates else None

    enriched["target_year"] = enriched.apply(earliest_year, axis=1)

    # Confidence ranking for rollup (high > medium > lower)
    conf_rank = {"high": 3, "medium": 2, "lower": 1}

    # Aggregate to one row per (namobj, regpln)
    grouped = []
    for (namobj, regpln), g in enriched.groupby(["namobj", "regpln"], dropna=False):
        types = g["project_type"].tolist()
        statuses = g["status"].tolist()
        confidences = g["confidence"].tolist()
        years = [y for y in g["target_year"].tolist() if pd.notna(y)]
        grouped.append(
            {
                "namobj": namobj,
                "regpln": regpln,
                "has_planned_upgrade": True,
                "mva_added_total": float(g["mva_added"].sum()),
                "project_type_strongest": strongest_project_type(types),
                "strongest_status": strongest_status(statuses),
                "earliest_target_year": int(min(years)) if years else None,
                "match_confidence": max(confidences, key=lambda c: conf_rank.get(c, 0)),
                "n_ruptl_matches": int(len(g)),
                "ruptl_substation_name_matched": ", ".join(
                    sorted(set(g["substation_name"].astype(str)))
                ),
            }
        )

    df = pd.DataFrame(grouped)
    df["earliest_target_year"] = df["earliest_target_year"].astype("Int64")
    return df


def build_fct_substation_ruptl_signal_from_disk() -> pd.DataFrame:
    """Zero-arg entry point for run_pipeline.py. Loads inputs, returns DataFrame.

    The pipeline runner writes the returned frame to OUT_CSV itself.
    """
    ruptl = load_ruptl_plans()
    substations = load_substations()
    return build_fct_substation_ruptl_signal(ruptl, substations)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    ruptl = load_ruptl_plans()
    substations = load_substations()
    print(f"RUPTL plans (filtered): {len(ruptl)} rows")
    print(f"PLN substations (features): {len(substations)}")

    df = build_fct_substation_ruptl_signal(ruptl, substations)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nMatched: {len(df)} unique (namobj, regpln) substation rows")

    if not df.empty:
        print("\nBy project_type_strongest:")
        for t, n in Counter(df["project_type_strongest"]).most_common():
            print(f"  {t:12s} {n:5d}")
        print("\nBy strongest_status:")
        for s, n in Counter(df["strongest_status"]).most_common():
            print(f"  {s:12s} {n:5d}")
        print("\nBy match_confidence:")
        for c, n in Counter(df["match_confidence"]).most_common():
            print(f"  {c:12s} {n:5d}")
        # Coverage: what fraction of the 2,913 feature stock is covered?
        # Count unique (namobj, regpln) in substation.geojson
        unique_subs = substations[["namobj", "regpln"]].drop_duplicates()
        print(
            f"\nCoverage: {len(df)} matched / {len(unique_subs)} unique substations "
            f"= {100 * len(df) / len(unique_subs):.1f}%"
        )
    print(f"\nWrote {len(df)} rows -> {OUT_CSV.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
