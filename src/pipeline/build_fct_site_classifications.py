# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""
build_fct_site_classifications — per-site electricity arrangement + captive
fuel-type schema (v4.1a §3, issue #70).

Each site is classified into one of four electricity arrangements
(`grid_only`, `grid_primary_with_captive`, `hybrid_captive_primary`,
`pure_captive`) and one of six captive fuel types (`coal_subcritical`,
`coal_supercritical`, `natural_gas`, `oil_diesel`, `hybrid`, `none`).
The classification gates the captive cost references (§4 coal, §5 gas) used
by the scorecard.

# Default classification logic (§3.2 — 8 sector × region rules)

| Sector       | Region              | Default electricity_arrangement | captive_fuel_type    |
|--------------|---------------------|---------------------------------|----------------------|
| Nickel       | Sulawesi / Maluku   | pure_captive                    | coal_subcritical     |
| Aluminium    | All                 | hybrid_captive_primary          | hybrid (site-spec.)  |
| Cement       | Java                | grid_only                       | none                 |
| Cement       | Outside Java        | grid_primary_with_captive       | coal_subcritical     |
| Fertilizer   | All                 | pure_captive                    | natural_gas          |
| Steel        | Java                | grid_primary_with_captive       | natural_gas (varies) |
| Steel        | Sulawesi            | pure_captive                    | coal_subcritical     |
| KEK (mixed)  | Java                | grid_only                       | none                 |
| KEK (mixed)  | Eastern Indonesia   | pure_captive                    | coal_subcritical     |
| KEK (mixed)  | Other               | grid_primary_with_captive       | none                 |

Site-specific overrides in ``data/raw/site_classifications.csv`` trump
defaults. Sites covered by overrides get ``classification_confidence='high'``
(or whatever the override CSV specifies); default-only sites get ``'medium'``.

# v4.1a column subset only

This module ships the §3.1a column subset. The §3.1b export-market-share
columns are explicitly out-of-scope here — they land in v4.1b on the same
table (additive column extension, no migration of existing rows). See spec
§1.5 release split.

Sources:
    processed: dim_sites.csv               site identity + sector + grid_region_id
    raw: data/raw/site_classifications.csv site-specific overrides

Writes:
    outputs/data/processed/fct_site_classifications.csv

Output columns (§3.1a v4.1a subset):
    site_id, site_name, sector, subsector, region, grid_region,
    electricity_arrangement, captive_fuel_type, captive_capacity_mw,
    captive_share_estimated, last_updated, classification_confidence, notes
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import TypedDict

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DATA_DIR = REPO_ROOT / "data"

DIM_SITES_CSV = PROCESSED / "dim_sites.csv"
SITE_CLASSIFICATIONS_OVERRIDES_CSV = DATA_DIR / "raw" / "site_classifications.csv"


# Valid enums per §3.1a
ELECTRICITY_ARRANGEMENTS = (
    "grid_only",
    "grid_primary_with_captive",
    "hybrid_captive_primary",
    "pure_captive",
)
CAPTIVE_FUEL_TYPES = (
    "coal_subcritical",
    "coal_supercritical",
    "natural_gas",
    "oil_diesel",
    "hybrid",
    "none",
)
CONFIDENCE_LEVELS = ("high", "medium", "low")

# Grid regions classified as "Eastern Indonesia" for KEK default routing.
# Java is JAVA_BALI; "Eastern" is Maluku, Papua, NTB. Sulawesi/Kalimantan/
# Sumatera get the middle "grid_primary_with_captive" default.
_EASTERN_REGIONS = frozenset({"MALUKU", "PAPUA", "NTB"})
_JAVA_REGION = "JAVA_BALI"


class _DefaultClassification(TypedDict):
    electricity_arrangement: str
    captive_fuel_type: str


def _default_classification(
    sector: str, grid_region_id: str, site_type: str
) -> _DefaultClassification:
    """Apply the §3.2 sector × region rule table.

    Sites of type 'kek' / 'standalone' / 'cluster' map to the same rules with
    KEK behaviour gated on site_type == 'kek' (sector for KEKs is 'mixed').
    """
    # Nickel IIA Sulawesi/Maluku → pure captive coal
    if sector == "nickel":
        return {
            "electricity_arrangement": "pure_captive",
            "captive_fuel_type": "coal_subcritical",
        }
    # Aluminium all → hybrid captive primary (varies; Inalum has hydro+coal, Freeport gas)
    if sector == "aluminium":
        return {
            "electricity_arrangement": "hybrid_captive_primary",
            "captive_fuel_type": "hybrid",
        }
    # Cement Java → grid only; outside Java → grid primary with captive backup
    if sector == "cement":
        if grid_region_id == _JAVA_REGION:
            return {
                "electricity_arrangement": "grid_only",
                "captive_fuel_type": "none",
            }
        return {
            "electricity_arrangement": "grid_primary_with_captive",
            "captive_fuel_type": "coal_subcritical",
        }
    # Fertilizer all → pure captive gas
    if sector == "fertilizer":
        return {
            "electricity_arrangement": "pure_captive",
            "captive_fuel_type": "natural_gas",
        }
    # Steel: Java → grid_primary_with_captive (gas captive supplement);
    # Sulawesi/other → pure captive coal
    if sector == "steel":
        if grid_region_id == _JAVA_REGION:
            return {
                "electricity_arrangement": "grid_primary_with_captive",
                "captive_fuel_type": "natural_gas",
            }
        return {
            "electricity_arrangement": "pure_captive",
            "captive_fuel_type": "coal_subcritical",
        }
    # KEK (sector == 'mixed') by region
    if site_type == "kek" or sector == "mixed":
        if grid_region_id == _JAVA_REGION:
            return {
                "electricity_arrangement": "grid_only",
                "captive_fuel_type": "none",
            }
        if grid_region_id in _EASTERN_REGIONS:
            return {
                "electricity_arrangement": "pure_captive",
                "captive_fuel_type": "coal_subcritical",
            }
        return {
            "electricity_arrangement": "grid_primary_with_captive",
            "captive_fuel_type": "none",
        }
    # Final fallback — unknown sector defaults to grid only with no captive.
    # Defensive: shouldn't fire given the current sector enum.
    return {
        "electricity_arrangement": "grid_only",
        "captive_fuel_type": "none",
    }


def _derive_subsector(sector: str, primary_product: str | float | None) -> str:
    """Best-effort subsector inference from primary_product.

    Returns the sector itself when primary_product is missing or doesn't
    map to a known subsector tag — the schema allows that (subsector is a
    free-text helper, not a strict enum).
    """
    if not isinstance(primary_product, str) or not primary_product.strip():
        return sector
    p = primary_product.lower()
    if sector == "nickel":
        if "matte" in p or "mhp" in p or "hpal" in p:
            return "nickel_matte"
        if "npi" in p or "ferronickel" in p or "ferro-nickel" in p:
            return "nickel_npi"
        return "nickel"
    if sector == "steel":
        # Check BF-BOF / integrated indicators FIRST — "slab" can appear in
        # both EAF and BF-BOF product descriptions, but "bf" / "integrated"
        # / "blast" are bfbof-exclusive markers.
        if "bof" in p or "bf-" in p or "bf/" in p or "integrated" in p or "blast" in p:
            return "steel_bfbof"
        if "eaf" in p or "scrap" in p or "billet" in p or "slab" in p:
            return "steel_eaf"
        return "steel"
    if sector == "fertilizer":
        if "ammonia" in p:
            return "ammonia"
        return "fertilizer"
    return sector


def build_fct_site_classifications(
    dim_sites_csv: Path = DIM_SITES_CSV,
    overrides_csv: Path = SITE_CLASSIFICATIONS_OVERRIDES_CSV,
) -> pd.DataFrame:
    """Build the per-site classification table (v4.1a §3.1a subset).

    Defaults applied per §3.2 sector × region rule table; per-site overrides
    in ``overrides_csv`` trump defaults.

    Parameters
    ----------
    dim_sites_csv:
        Path to the unified dim_sites table.
    overrides_csv:
        Path to the per-site override CSV. Optional — missing file means
        every site uses defaults with ``confidence='medium'``.

    Returns
    -------
    pd.DataFrame
        Columns per §3.1a: site_id, site_name, sector, subsector, region,
        grid_region, electricity_arrangement, captive_fuel_type,
        captive_capacity_mw, captive_share_estimated, last_updated,
        classification_confidence, notes.
    """
    dim_sites = pd.read_csv(dim_sites_csv)

    overrides: pd.DataFrame
    if overrides_csv.exists():
        overrides = pd.read_csv(overrides_csv)
    else:
        overrides = pd.DataFrame(
            columns=[
                "site_id",
                "electricity_arrangement",
                "captive_fuel_type",
                "captive_capacity_mw",
                "captive_share_estimated",
                "classification_confidence",
                "notes",
            ]
        )

    rows: list[dict[str, object]] = []
    today = date.today().isoformat()

    for _, site in dim_sites.iterrows():
        site_id = site["site_id"]
        sector = site["sector"] if isinstance(site["sector"], str) else "mixed"
        grid_region = site["grid_region_id"] if isinstance(site["grid_region_id"], str) else ""
        site_type = site["site_type"] if isinstance(site["site_type"], str) else ""
        site_name = site["site_name"]
        province = site["province"] if isinstance(site["province"], str) else ""
        primary_product = site.get("primary_product")

        default = _default_classification(sector, grid_region, site_type)
        subsector = _derive_subsector(sector, primary_product)

        # Override merge — if a row in overrides matches site_id, its fields
        # replace the corresponding default fields; unset override fields fall
        # back to default.
        override_row = overrides[overrides["site_id"] == site_id]
        if not override_row.empty:
            ov = override_row.iloc[0]
            electricity_arrangement = (
                ov["electricity_arrangement"]
                if pd.notna(ov.get("electricity_arrangement"))
                else default["electricity_arrangement"]
            )
            captive_fuel_type = (
                ov["captive_fuel_type"]
                if pd.notna(ov.get("captive_fuel_type"))
                else default["captive_fuel_type"]
            )
            captive_capacity_mw = (
                ov["captive_capacity_mw"] if pd.notna(ov.get("captive_capacity_mw")) else None
            )
            captive_share_estimated = (
                ov["captive_share_estimated"]
                if pd.notna(ov.get("captive_share_estimated"))
                else None
            )
            classification_confidence = (
                ov["classification_confidence"]
                if pd.notna(ov.get("classification_confidence"))
                else "high"
            )
            notes = ov["notes"] if pd.notna(ov.get("notes")) else ""
        else:
            electricity_arrangement = default["electricity_arrangement"]
            captive_fuel_type = default["captive_fuel_type"]
            captive_capacity_mw = None
            captive_share_estimated = None
            classification_confidence = "medium"  # default-only confidence per §3.2
            notes = f"default classification: {sector} × {grid_region}"

        rows.append(
            {
                "site_id": site_id,
                "site_name": site_name,
                "sector": sector,
                "subsector": subsector,
                "region": province,
                "grid_region": grid_region,
                "electricity_arrangement": electricity_arrangement,
                "captive_fuel_type": captive_fuel_type,
                "captive_capacity_mw": captive_capacity_mw,
                "captive_share_estimated": captive_share_estimated,
                "last_updated": today,
                "classification_confidence": classification_confidence,
                "notes": notes,
            }
        )

    df = pd.DataFrame(rows)

    # Validate enums — fail loudly if a row falls outside the spec'd values.
    bad_arrangements = ~df["electricity_arrangement"].isin(ELECTRICITY_ARRANGEMENTS)
    if bad_arrangements.any():
        raise ValueError(
            "Invalid electricity_arrangement values: "
            f"{df.loc[bad_arrangements, ['site_id', 'electricity_arrangement']].to_dict('records')}"
        )
    bad_fuels = ~df["captive_fuel_type"].isin(CAPTIVE_FUEL_TYPES)
    if bad_fuels.any():
        raise ValueError(
            "Invalid captive_fuel_type values: "
            f"{df.loc[bad_fuels, ['site_id', 'captive_fuel_type']].to_dict('records')}"
        )
    bad_confidence = ~df["classification_confidence"].isin(CONFIDENCE_LEVELS)
    if bad_confidence.any():
        raise ValueError(
            "Invalid classification_confidence values: "
            f"{df.loc[bad_confidence, ['site_id', 'classification_confidence']].to_dict('records')}"
        )

    df = df.sort_values("site_id", ignore_index=True)
    return df
