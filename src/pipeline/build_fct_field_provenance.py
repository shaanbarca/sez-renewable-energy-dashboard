"""
Build fct_field_provenance — sidecar provenance table for v4.1+ numeric fields.

One row per `(site_id, field_name)` with `source`, `vintage`, `confidence`,
`citation` columns. Joined against `fct_site_scorecard.csv` by API consumers
that want to surface provenance in the methodology drawer or audit pipeline.

Architecture decision: sidecar table rather than inline 4-fields-per-output
in the main scorecard. See `src/utils/provenance.py` module docstring + the
`/plan-eng-review` 2026-05-15 finding A2 for the rationale.

Issue #65 (v4.1a §9). Foundation seed: 3 v4.0 fields with well-known
provenance. Downstream sub-PRs (#67–72) extend the registry as they add
new cost framework fields; the build step picks them up automatically.

Sources:
    src/utils/provenance.py — static PROVENANCE_REGISTRY
    outputs/data/processed/dim_sites.csv — site_id list

Writes:
    outputs/data/processed/fct_field_provenance.csv

Output schema:
    site_id      str — joins to dim_sites.site_id
    field_name   str — name of the provenance-tracked column in fct_site_scorecard
    source       str — canonical short source name (e.g. "Global Solar Atlas v2")
    vintage      str — ISO year / year-quarter / full date the data reflects
    confidence   str — one of "high" / "medium" / "low"
    citation     str — full citation reference, suitable for an investment memo

Row count: |sites| × |fields in registry|, minus any (site, field) pairs where
an override loader returns None (site has no value for that field).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.provenance import build_sidecar_rows

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"


def build_fct_field_provenance(
    dim_sites_csv: Path = PROCESSED / "dim_sites.csv",
) -> pd.DataFrame:
    """Emit the long-format sidecar provenance table.

    Reads the site list from `dim_sites.csv` and expands the static registry
    in `src.utils.provenance.PROVENANCE_REGISTRY` across every site.

    Returns
    -------
    pd.DataFrame
        Columns: site_id, field_name, source, vintage, confidence, citation.
        Sorted by (site_id, field_name) for stable CSV diffs.
    """
    dim_sites = pd.read_csv(dim_sites_csv)
    site_ids = dim_sites["site_id"].tolist()

    rows = build_sidecar_rows(site_ids)
    if not rows:
        # Registry is empty (shouldn't happen in v4.1a+, but defensively
        # return an empty df with the right schema rather than crashing).
        return pd.DataFrame(
            columns=["site_id", "field_name", "source", "vintage", "confidence", "citation"]
        )

    df = pd.DataFrame(rows)
    df = df.sort_values(["site_id", "field_name"], ignore_index=True)
    return df
