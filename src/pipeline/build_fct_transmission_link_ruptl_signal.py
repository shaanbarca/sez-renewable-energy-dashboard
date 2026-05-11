# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""F5 (2026-05-09): RUPTL §V.9 transmission-link feasibility pipeline.

Reads `data/raw/ruptl_v9_transmission_links.csv` (manually curated from
RUPTL 2025-2034 §V.9 regional Pengembangan Sistem Penyaluran sections),
passes through with a derived per-region rollup column.

Spec note: F5 referenced RUPTL §V.11 — that anchor is from an older
RUPTL version. The 2025-2034 RUPTL has the relevant content at §V.9.x
per region. Schema and intent are unchanged.

Output rows are unchanged from input + the rollup column.

Per-region feasibility rollup (`worst_case_status`):
  - Take the most-pessimistic status across all links touching the
    region (from_region or to_region).
  - Severity ordering: not_feasible > under_study > cross_border >
    pre_construction > in_construction.
  - Used downstream by the scorecard enricher to set
    `comparator_feasibility` per site based on its grid_region_id.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = REPO_ROOT / "data" / "raw" / "ruptl_v9_transmission_links.csv"
PROCESSED_DIR = REPO_ROOT / "outputs" / "data" / "processed"
OUT_PATH = PROCESSED_DIR / "fct_transmission_link_ruptl_signal.csv"


# Severity for region-rollup: lower is more pessimistic.
_STATUS_SEVERITY = {
    "not_feasible": 0,
    "under_study": 1,
    "cross_border": 2,
    "pre_construction": 3,
    "in_construction": 4,
}


def _worst_status(statuses: list[str]) -> str | None:
    """Return the lowest-severity (most pessimistic) status from the list."""
    if not statuses:
        return None
    ranked = [(s, _STATUS_SEVERITY.get(s, 99)) for s in statuses if pd.notna(s)]
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[1])
    return ranked[0][0]


def build_fct_transmission_link_ruptl_signal(
    raw_path: Path | str = RAW_PATH,
) -> pd.DataFrame:
    """Pass through raw transmission-link CSV; no transforms."""
    raw_path = Path(raw_path)
    if not raw_path.exists():
        return pd.DataFrame(
            columns=[
                "link_id",
                "from_region",
                "to_region",
                "voltage_kv",
                "length_km",
                "ruptl_section",
                "status",
                "target_cod_year",
                "verification_status",
                "ruptl_quote",
                "source",
                "notes",
            ]
        )
    df = pd.read_csv(raw_path)
    return df


def region_worst_status_map(
    links_df: pd.DataFrame | None = None,
) -> dict[str, str]:
    """Build a `{grid_region_id: worst_status}` mapping for the scorecard.

    A region's worst-case status is the most-pessimistic status across all
    links that touch it as either from_region or to_region. Used to set
    `comparator_feasibility` per site.

    Returns an empty dict when the input has no links — the scorecard
    falls back to the default `pln_tariff_feasible` for every site.
    """
    if links_df is None:
        links_df = build_fct_transmission_link_ruptl_signal()
    if links_df.empty:
        return {}

    rollup: dict[str, list[str]] = {}
    for _, row in links_df.iterrows():
        for region in [row.get("from_region"), row.get("to_region")]:
            if pd.notna(region) and region != "CROSS_BORDER":
                rollup.setdefault(region, []).append(row.get("status"))

    return {region: _worst_status(statuses) for region, statuses in rollup.items()}


def comparator_feasibility_for_region(
    grid_region_id: str | None,
    region_status_map: dict[str, str] | None = None,
    grid_integration_category: str | None = None,
) -> str:
    """Map (region, integration_category) → comparator feasibility enum.

    Returns one of:
      - `pln_tariff_feasible` — region has no flagged links, or integration
        category doesn't depend on new transmission
      - `pln_tariff_uncertain_grid_first_required` — region depends on
        under-study or cross-border links
      - `pln_tariff_infeasible_captive_only` — region is fed only by links
        marked `not_feasible` in RUPTL

    The integration-category guard prevents flipping comparators for sites
    that don't actually need new transmission (already grid-ready).
    """
    if region_status_map is None:
        region_status_map = {}

    if grid_integration_category not in {
        "invest_transmission",
        "invest_substation",
        "grid_first",
    }:
        return "pln_tariff_feasible"

    worst = region_status_map.get(grid_region_id)
    if worst is None:
        return "pln_tariff_feasible"
    if worst == "not_feasible":
        return "pln_tariff_infeasible_captive_only"
    if worst in {"under_study", "cross_border"}:
        return "pln_tariff_uncertain_grid_first_required"
    return "pln_tariff_feasible"


if __name__ == "__main__":
    df = build_fct_transmission_link_ruptl_signal()
    if not df.empty:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUT_PATH, index=False)
        print(f"  Wrote {len(df)} rows → {OUT_PATH}")
        rollup = region_worst_status_map(df)
        print("  Per-region worst-case status:")
        for region, status in sorted(rollup.items()):
            print(f"    {region}: {status}")
    else:
        print("  No raw transmission-link file found, skipping write")
