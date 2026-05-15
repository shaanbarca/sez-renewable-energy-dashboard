"""Field-level data provenance for v4.1+ (#65, v4.1a foundation).

Per `docs/refinement/v4_1_foundation_spec.md` §9: every numeric output should
carry provenance so the dashboard's numbers stay auditable from cost framework
through scorecard. Without provenance, DFI investment committees cannot rely on
the values.

# Storage shape — sidecar table, not inline

The spec's first draft proposed inline denormalization: 4 columns per numeric
output added to `fct_site_scorecard.csv` (`<field>_source`, `<field>_vintage`,
`<field>_confidence`, `<field>_citation`). That would 5x the scorecard width
(~190 → ~950 columns) — bad for CSV consumers + frontend type complexity +
payload size.

`/plan-eng-review` finding A2 (2026-05-15) replaced that with a sidecar table
`fct_field_provenance.csv` keyed by `(site_id, field_name)`:

```
site_id, field_name,                source,                vintage, confidence, citation
kek-palu, pvout_centroid_kwh_kwp_yr, Global Solar Atlas v2, 2020,    high,      World Bank ESMAP / Solargis 2020
kek-palu, bpp_usd_mwh,               Kepmen ESDM 169/2021,  2020,    high,      Kementerian ESDM Lampiran A
kek-palu, captive_cost_usd_mwh,      industry_estimate,     2024,    medium,    IESR 2024 default
...
```

Benefits over inline:
- Scorecard width stays stable as more provenance-tracked fields land in v4.2+.
- Provenance schema is uniform across releases — same columns for every field.
- Size-conscious consumers can skip the sidecar entirely (frontend doesn't need
  it for the main UI; only the methodology drawer reads it).
- Provenance can be queried independently (e.g. "what's our weakest data
  point?") via the long format.

# Registry vs runtime collection

This module exposes a STATIC registry rather than a runtime collection
mechanism. Each provenance-tracked field is declared once in
`PROVENANCE_REGISTRY` with a default `ProvenanceFlag`; the build step joins
the registry against the site list to produce the sidecar.

Reasons for the static registry vs a runtime "every pipeline step calls
register()" pattern:
- No cross-step coupling — adding a field doesn't require modifying its
  producing pipeline step.
- The registry IS the canonical schema documentation; one place to look up
  what's audited and what isn't.
- Per-site overrides (e.g. captive cost is `confidence='high'` for IMIP with
  the IESR 2024 anchor but `confidence='medium'` for sites on the default)
  are handled by an optional override loader per field.
- The registry can be statically grep'd / linted for missing citations,
  stale vintages, etc.

# How sub-PRs extend the registry

v4.1a foundation (this PR) ships the module + a small registry seed of 3
v4.0 fields whose provenance is well-known. Each downstream sub-PR appends
its new fields:
- #67 (§2 multi-tier LCOE) — adds `lcoe_generation_usd_mwh`,
  `full_system_lcoe_delivered_usd_mwh`, etc.
- #68 (§6.2 marginal) — adds `incumbent_pln_marginal_daytime_usd_mwh`, etc.
- #69 (§8 LCOS) — adds `lcos_4h_usd_mwh`, `lcos_8h_usd_mwh`.
- #70/#71/#72 (§3-5 sectoral) — adds classification + captive cost fields.

See METHODOLOGY_CONSOLIDATED.md §9 for the canonical provenance schema.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from src.model.captive_economics import (
    is_coal_anchor_site,
    is_gas_anchor_site,
    load_captive_overrides,
)

ConfidenceLevel = Literal["high", "medium", "low"]
_VALID_CONFIDENCES: tuple[ConfidenceLevel, ...] = ("high", "medium", "low")


@dataclass(frozen=True)
class ProvenanceFlag:
    """Provenance metadata for one numeric field at one site (or default).

    Immutable on purpose — registry entries are constants; per-site overrides
    return new instances rather than mutating the default.

    Attributes:
        source: Where the value came from. Free text; prefer canonical names
            ("Global Solar Atlas v2", "Kepmen ESDM 169/2021", "industry_estimate").
        vintage: When the data reflects. ISO year, year-quarter, or full date
            ("2020", "2024-Q1", "2024-12-01"). NOT a publication date — the
            vintage of the underlying data the value reports.
        confidence: One of "high" / "medium" / "low". See module docstring for
            the rubric.
        citation: Full citation reference, suitable for an investment memo
            footnote. Includes the publisher, document name, section/page if
            applicable.

    Validation: `confidence` must be one of the three literal values; the
    constructor raises ValueError on anything else. The other fields are
    free-text — no whitespace stripping or normalization; the registry author
    is trusted.
    """

    source: str
    vintage: str
    confidence: ConfidenceLevel
    citation: str

    def __post_init__(self) -> None:
        if self.confidence not in _VALID_CONFIDENCES:
            raise ValueError(
                f"ProvenanceFlag.confidence must be one of {_VALID_CONFIDENCES}; "
                f"got {self.confidence!r}"
            )
        if not self.source:
            raise ValueError("ProvenanceFlag.source must be non-empty")
        if not self.vintage:
            raise ValueError("ProvenanceFlag.vintage must be non-empty")
        if not self.citation:
            raise ValueError("ProvenanceFlag.citation must be non-empty")


# Type alias: optional per-site override function. Returns a ProvenanceFlag
# if this site has a non-default provenance for the field, else None.
# `None` from the loader means "use the registry default for this field".
SiteOverrideLoader = Callable[[str], ProvenanceFlag | None]


# Registry: field_name → (default ProvenanceFlag, optional override loader).
#
# Foundation seed (#65 v4.1a): three v4.0 fields whose provenance is
# well-known and stable. Each downstream sub-PR (#67–72) extends this dict
# with its new fields. Adding a row here AND making sure the build step
# picks it up is sufficient to add provenance for a new field.
PROVENANCE_REGISTRY: dict[str, tuple[ProvenanceFlag, SiteOverrideLoader | None]] = {
    "pvout_centroid_kwh_kwp_yr": (
        ProvenanceFlag(
            source="Global Solar Atlas v2",
            vintage="2020",
            confidence="high",
            citation=(
                "World Bank ESMAP / Solargis (2020). Global Solar Atlas v2.0 — "
                "Indonesia long-term PV yield (PVOUT) 1 km raster. Geotiff."
            ),
        ),
        None,
    ),
    "bpp_usd_mwh": (
        ProvenanceFlag(
            source="Kepmen ESDM 169/2021",
            vintage="2020",
            confidence="high",
            citation=(
                "Kementerian ESDM Republik Indonesia (2021). Keputusan Menteri "
                "ESDM No. 169 K/20/MEM/2021, Lampiran A — BPP Pembangkitan "
                "Tenaga Listrik PLN per wilayah, fiscal year 2020."
            ),
        ),
        None,
    ),
    "industrial_tariff_usd_mwh": (
        ProvenanceFlag(
            source="Permen ESDM 7/2024",
            vintage="2024",
            confidence="high",
            citation=(
                "Kementerian ESDM Republik Indonesia (2024). Peraturan Menteri "
                "ESDM No. 7 Tahun 2024 — Tarif Tenaga Listrik PLN, kategori "
                "I-4/TT (industri besar 30 MVA ke atas). 996.74 Rp/kWh."
            ),
        ),
        None,
    ),
    # ─── v4.1a §2 multi-tier LCOE (issue #67) ─────────────────────────────
    "lcoe_generation_usd_mwh": (
        ProvenanceFlag(
            source="NREL ATB 2024",
            vintage="2024",
            confidence="high",
            citation=(
                "NREL (2024). Annual Technology Baseline 2024 — Utility-Scale "
                "Solar PV, Class 5 site, 2024 vintage. Generation-only LCOE "
                "(no transmission, no storage). IEA LCOE alignment per "
                "spec §2.1. Closest v4.0 alias: lcoe_within_boundary_usd_mwh."
            ),
        ),
        None,
    ),
    "full_system_lcoe_delivered_usd_mwh": (
        ProvenanceFlag(
            source="NREL ATB 2024 + connection cost model",
            vintage="2024",
            confidence="high",
            citation=(
                "Computed: lcoe_generation_usd_mwh + gen-tie transmission + "
                "substation connection cost per src/model/basic_model.py. "
                "IEA Full System LCOE (delivered). See METHODOLOGY §2.1."
            ),
        ),
        None,
    ),
    "full_system_lcoe_firm_4h_usd_mwh": (
        ProvenanceFlag(
            source="Lazard LCOE+S 2024 + IRENA Battery Storage 2024",
            vintage="2024",
            confidence="high",
            citation=(
                "Computed: lcoe_generation_usd_mwh + lcos_4h_usd_mwh × 0.20. "
                "Lazard (2024) LCOE+S v16 §firming methodology; storage share "
                "20% of solar nameplate at 4-hour duration. IEA Full System "
                "LCOE (firm 4h). See METHODOLOGY §2.1 and §8.5."
            ),
        ),
        None,
    ),
    "full_system_lcoe_firm_8h_usd_mwh": (
        ProvenanceFlag(
            source="Lazard LCOE+S 2024 + IRENA Battery Storage 2024",
            vintage="2024",
            confidence="high",
            citation=(
                "Computed: lcoe_generation_usd_mwh + lcos_8h_usd_mwh × 0.50. "
                "Lazard (2024) LCOE+S v16 §firming methodology; storage share "
                "50% of solar nameplate at 8-hour duration. IEA Full System "
                "LCOE (firm 8h). See METHODOLOGY §2.1 and §8.5."
            ),
        ),
        None,
    ),
    # ─── v4.1a §8 storage LCOS (issue #69) ────────────────────────────────
    "lcos_4h_usd_mwh": (
        ProvenanceFlag(
            source="IRENA 2024 + Lazard 2024",
            vintage="2024",
            confidence="high",
            citation=(
                "IRENA (2024). Battery Storage Cost Report — Utility-scale "
                "Li-ion at 4-hour duration. Cross-checked against Lazard "
                "LCOE+S v16 (2024) storage section. Defaults: $350/kWh "
                "installed capex, 15-year life, 365 cycles/year, RTE 0.90, "
                "DOD 0.85, $7/kW-year fixed O&M. See METHODOLOGY §8."
            ),
        ),
        None,
    ),
    "lcos_8h_usd_mwh": (
        ProvenanceFlag(
            source="IRENA 2024 + Lazard 2024",
            vintage="2024",
            confidence="high",
            citation=(
                "IRENA (2024). Battery Storage Cost Report — Utility-scale "
                "Li-ion at 8-hour duration. Cross-checked against Lazard "
                "LCOE+S v16 (2024). Same BATTERY_DEFAULTS as lcos_4h. See "
                "METHODOLOGY §8."
            ),
        ),
        None,
    ),
    # ─── v4.1a §6 marginal cost split (issue #68) ─────────────────────────
    "incumbent_pln_marginal_daytime_usd_mwh": (
        ProvenanceFlag(
            source="Kepmen ESDM 169/2021 + regional dispatch adjustment",
            vintage="2020",
            confidence="medium",
            citation=(
                "Computed: bpp_usd_mwh × MARGINAL_COST_ADJUSTMENT_BY_REGION"
                "[region]['daytime']. Regional factors calibrated against "
                "IESR 2024 dispatch analysis, IEA SEA Energy Outlook 2024 §5, "
                "and RUPTL 2025–2034 Bab IV regional dispatch composition. "
                "Daytime = PVOUT-weighted ~06:00–18:00 local. See "
                "METHODOLOGY §6.2 and src/dash/logic/marginal.py."
            ),
        ),
        None,
    ),
    "incumbent_pln_marginal_nighttime_usd_mwh": (
        ProvenanceFlag(
            source="Kepmen ESDM 169/2021 + regional dispatch adjustment",
            vintage="2020",
            confidence="medium",
            citation=(
                "Computed: bpp_usd_mwh × MARGINAL_COST_ADJUSTMENT_BY_REGION"
                "[region]['nighttime']. Same calibration sources as daytime. "
                "Nighttime = complementary ~18:00–06:00 local. Feeds storage "
                "/ dispatchable RE comparator per spec §6.5. See METHODOLOGY "
                "§6.2 and src/dash/logic/marginal.py."
            ),
        ),
        None,
    ),
    # ─── v4.1a §3 (#70) — site classification fields ──────────────────────
    # Default confidence is 'medium' (sectoral default rule applied);
    # site-level confidence comes through `classification_confidence` on
    # the scorecard itself, sourced from data/raw/site_classifications.csv.
    "electricity_arrangement": (
        ProvenanceFlag(
            source="classification logic (default rule)",
            vintage="2024",
            confidence="medium",
            citation=(
                "v4.1a §3.2 sector × region default rule table. Indonesia "
                "Dashboard Methodology §3. Site-specific overrides where "
                "public disclosure exists upgrade to confidence='high'."
            ),
        ),
        None,
    ),
    "captive_fuel_type": (
        ProvenanceFlag(
            source="dim_sites + GEM tracker + sectoral defaults",
            vintage="2024",
            confidence="high",
            citation=(
                "Global Energy Monitor coal plant tracker (2024) for captive "
                "coal sites; sectoral defaults applied otherwise per v4.1a §3.2. "
                "Indonesia Dashboard Methodology §3."
            ),
        ),
        None,
    ),
    # ─── v4.1a §4 (#71) — captive coal LCOE ───────────────────────────────
    # Default flag is 'medium' confidence (formula output with literature
    # defaults). The 5 anchor sites with overrides bump to 'high' via the
    # override loader assigned at module load (below).
    "captive_coal_lcoe_usd_mwh": (
        ProvenanceFlag(
            source="CAPTIVE_COAL_DEFAULTS formula (literature mid-range)",
            vintage="2024",
            confidence="medium",
            citation=(
                "Berkeley Goldman School (2023). 'Indonesia Can "
                "Cost-effectively Supplant Captive Coal-fired Power Plants "
                "with Solar Energy.' + IESR (2024). 'Captive Power Plants: "
                "Indonesia's hidden coal expansion.' v4.1a §4 default."
            ),
        ),
        None,  # see captive_coal_override_loader assigned below
    ),
    # ─── v4.1a §5 (#72) — captive gas LCOE ────────────────────────────────
    # Defaults are medium confidence; Pupuk Kaltim Bontang override bumps
    # to high via captive_gas_override_loader (assigned below).
    "captive_gas_lcoe_usd_mwh": (
        ProvenanceFlag(
            source="CAPTIVE_GAS_DEFAULTS formula (literature mid-range)",
            vintage="2024",
            confidence="medium",
            citation=(
                "IESR (2024). 'Indonesia captive gas economics — fertilizer "
                "+ petrochemical sectoral defaults.' v4.1a §5 default."
            ),
        ),
        None,  # see captive_gas_override_loader assigned below
    ),
}


# ─── Per-site override loaders for captive cost provenance ──────────────────
# These run after the registry is constructed so they can read the override
# CSV via the captive_economics module. We rebuild the registry entries with
# the loader callable attached.


def _captive_coal_override_loader(site_id: str) -> ProvenanceFlag | None:
    """Bump confidence to 'high' for sites with a coal_* override row.

    Returns None (use default) for sites without an override.
    """
    overrides = load_captive_overrides()
    if is_coal_anchor_site(site_id, overrides):
        return ProvenanceFlag(
            source="data/raw/captive_generation_overrides.csv",
            vintage="2024-12",
            confidence="high",
            citation=(
                "Site-specific captive coal LCOE from IESR (2024) industry "
                "estimates + plant-level engineering data. v4.1a §4.4 anchor."
            ),
        )
    return None


def _captive_gas_override_loader(site_id: str) -> ProvenanceFlag | None:
    """Bump confidence to 'high' for Pupuk Kaltim Bontang (gas anchor)."""
    overrides = load_captive_overrides()
    if is_gas_anchor_site(site_id, overrides):
        return ProvenanceFlag(
            source="data/raw/captive_generation_overrides.csv",
            vintage="2024-12",
            confidence="high",
            citation=(
                "Pupuk Indonesia disclosures + IEA Indonesia gas price 2024. "
                "v4.1a §5.4 anchor case."
            ),
        )
    return None


# Replace the None override-loader slots for the captive LCOE fields with
# the real loaders. Tuples are immutable, so reconstruct the entries.
PROVENANCE_REGISTRY["captive_coal_lcoe_usd_mwh"] = (
    PROVENANCE_REGISTRY["captive_coal_lcoe_usd_mwh"][0],
    _captive_coal_override_loader,
)
PROVENANCE_REGISTRY["captive_gas_lcoe_usd_mwh"] = (
    PROVENANCE_REGISTRY["captive_gas_lcoe_usd_mwh"][0],
    _captive_gas_override_loader,
)


def build_sidecar_rows(
    site_ids: list[str],
    registry: dict[str, tuple[ProvenanceFlag, SiteOverrideLoader | None]] | None = None,
) -> list[dict[str, str]]:
    """Expand the registry × site list into long-format sidecar rows.

    Each (site, field) pair gets one row. If the field has an override loader
    that returns None for a specific site, that site's row is omitted for that
    field (the site doesn't have a value for the field, so no provenance is
    emitted).

    Parameters
    ----------
    site_ids:
        List of site_id strings to expand the registry against (typically
        every row in `dim_sites.csv`).
    registry:
        Override the module-level `PROVENANCE_REGISTRY` for tests. Defaults
        to the production registry.

    Returns
    -------
    list[dict[str, str]]
        One dict per (site, field) row, with keys `site_id`, `field_name`,
        `source`, `vintage`, `confidence`, `citation`.
    """
    reg = registry if registry is not None else PROVENANCE_REGISTRY
    rows: list[dict[str, str]] = []
    for field_name, (default_flag, override_loader) in reg.items():
        for site_id in site_ids:
            flag: ProvenanceFlag | None
            if override_loader is None:
                flag = default_flag
            else:
                flag = override_loader(site_id) or default_flag
            if flag is None:
                continue
            rows.append(
                {
                    "site_id": site_id,
                    "field_name": field_name,
                    "source": flag.source,
                    "vintage": flag.vintage,
                    "confidence": flag.confidence,
                    "citation": flag.citation,
                }
            )
    return rows
