# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Marginal cost methodology with daytime / nighttime split.

v4.1a §6 (issue #68). The dashboard's v4.0 comparison uses regional BPP
(PLN's *average* cost of supply) as the reference. But solar doesn't
displace average generation — it displaces the *marginal* plant currently
running. And the marginal differs between daytime hours (when solar
delivers) and nighttime hours (when storage / dispatchable RE would
displace fuel).

PLN does not publish hourly dispatch data. This module applies regional
fuel-mix-based adjustment factors per `MARGINAL_COST_ADJUSTMENT_BY_REGION`
to the regional BPP, calibrated separately for daytime vs nighttime per
spec §6.2.

Daytime hour definition (eng-review finding A6, locked here):

    "Daytime" is the PVOUT-weighted hour window during which solar
    generation contributes to dispatch — approximately 06:00–18:00 local
    time at equatorial latitudes, weighted by the diurnal PVOUT profile.
    "Nighttime" is the complementary 18:00–06:00 window.

    This is the IEEE / IRENA convention used in dispatch analysis: solar
    LCOE comparisons use the daytime marginal; storage and dispatchable
    RE (geothermal, hydro) comparisons use the nighttime marginal.

    The 06:00–18:00 window is approximate — actual PVOUT contribution
    falls sharply outside ~07:30–16:30. The factor calibration below
    accounts for the actual generation-weighted hours, not the literal
    sunrise/sunset window.

Why daytime factors differ from nighttime in some regions but not others:

  - JAMALI (Java-Bali): gas runs at night more than during day → nighttime
    marginal is gas (slightly more expensive than coal). Daytime coal
    sets the floor.
  - Sumatera: mixed dispatch, similar profile to Java but more diesel
    peaking at night.
  - Kalimantan / Sulawesi: coal + diesel peaking in daytime; more diesel
    overnight; both above coal SRMC.
  - Maluku_Papua: daytime peak hits diesel SRMC (much higher than fleet
    average); nighttime baseload diesel runs continuously at a lower
    SRMC — daytime factor is HIGHER than nighttime in this region.

Region naming: spec uses `JAMALI` and `Maluku_Papua`; the codebase's
`grid_region_id` values are `JAVA_BALI`, `KALIMANTAN`, `MALUKU`, `NTB`,
`PAPUA`, `SULAWESI`, `SUMATERA`. The `region_to_marginal_key` helper
maps the codebase IDs onto the spec's region keys (JAVA_BALI → JAMALI;
MALUKU + PAPUA → Maluku_Papua; NTB → JAMALI sister region per RUPTL §V).

Citations (per spec §6.4):
  - IESR (2024). Analysis of Indonesian Dispatch Economics.
  - IRENA (2024). Indonesia Renewable Energy Outlook.
  - Berkeley Goldman School (2023). Indonesia Captive Coal Analysis.
  - IEA (2024). Southeast Asia Energy Outlook 2024 §5 (dispatch tables).
  - RUPTL 2025–2034 Bab IV — Regional Dispatch Composition by Season.
"""

from __future__ import annotations

import math
from typing import Literal

TimeOfDay = Literal["daytime", "nighttime"]


# Regional dispatch adjustment factors: BPP_marginal = BPP_regional × factor.
# Calibrated per spec §6.2 against regional fuel-mix + dispatch literature.
MARGINAL_COST_ADJUSTMENT_BY_REGION: dict[str, dict[str, float]] = {
    "JAMALI": {
        "daytime": 1.10,  # Coal usually marginal; small premium during sun hours
        "nighttime": 1.20,  # Sometimes gas marginal at night
    },
    "Sumatera": {
        "daytime": 1.20,  # Mixed dispatch; peak more solar-displaceable
        "nighttime": 1.40,  # More diesel peaking
    },
    "Kalimantan": {
        "daytime": 1.50,  # Coal + diesel peaking during industrial daytime
        "nighttime": 1.70,  # More diesel after solar drops
    },
    "Sulawesi": {
        "daytime": 1.60,  # Diesel-heavy peak, coal continuous
        "nighttime": 1.80,  # Mostly diesel + scarce coal
    },
    "Maluku_Papua": {
        "daytime": 2.50,  # Diesel-dominated peak — closer to diesel SRMC
        "nighttime": 2.20,  # Slightly lower; some baseload diesel runs continuously
    },
}


# Confidence rubric per spec §6.3 — captures methodological uncertainty in the
# marginal cost estimate, not data freshness. Coal-dominant regions (JAMALI)
# have the narrowest BPP-marginal gap; diesel-dominated remote regions have
# the widest.
MARGINAL_CONFIDENCE_BY_REGION: dict[str, str] = {
    "JAMALI": "jamali_coal_dominant",
    "Sumatera": "mixed_dispatch",
    "Kalimantan": "diesel_peaking",
    "Sulawesi": "diesel_peaking",
    "Maluku_Papua": "remote_diesel_dominated",
}


# Mapping from the codebase's `grid_region_id` values to the spec's region keys.
# Spec uses 5 dispatch regions; the codebase has 7 grid_region_id values.
#   JAVA_BALI → JAMALI (Java-Madura-Bali interconnected system, the original
#               PLN spelling 'Jamali')
#   NTB       → JAMALI (Nusa Tenggara Barat — connected via Lombok to Bali
#               grid in the RUPTL §V planning area; same dispatch profile)
#   SUMATERA  → Sumatera (1:1)
#   KALIMANTAN→ Kalimantan (1:1)
#   SULAWESI  → Sulawesi (1:1)
#   MALUKU    → Maluku_Papua (merged with Papua as a single dispatch region)
#   PAPUA     → Maluku_Papua (merged with Maluku)
_GRID_REGION_TO_MARGINAL_KEY: dict[str, str] = {
    "JAVA_BALI": "JAMALI",
    "NTB": "JAMALI",
    "SUMATERA": "Sumatera",
    "KALIMANTAN": "Kalimantan",
    "SULAWESI": "Sulawesi",
    "MALUKU": "Maluku_Papua",
    "PAPUA": "Maluku_Papua",
}


def region_to_marginal_key(grid_region_id: str) -> str:
    """Map a `grid_region_id` (codebase convention) to a `MARGINAL_*` dict key.

    Raises
    ------
    KeyError
        If the region is not recognized. The dashboard's 7 grid_region_id
        values are all explicitly mapped above; any new value must be added
        here AND in the cost-adjustment table.
    """
    try:
        return _GRID_REGION_TO_MARGINAL_KEY[grid_region_id]
    except KeyError:
        raise KeyError(
            f"Unknown grid_region_id={grid_region_id!r}. "
            f"Known: {sorted(_GRID_REGION_TO_MARGINAL_KEY)}"
        ) from None


def estimate_marginal_cost(
    bpp_regional: float,
    grid_region: str,
    time_of_day: TimeOfDay,
) -> float:
    """Marginal generation cost = regional BPP × dispatch-time factor.

    Parameters
    ----------
    bpp_regional:
        Regional BPP Pembangkitan (USD/MWh) from `fct_grid_cost_proxy.csv`.
        NaN propagates through (returns NaN).
    grid_region:
        Either a dispatch-region key from `MARGINAL_COST_ADJUSTMENT_BY_REGION`
        (`JAMALI`, `Sumatera`, `Kalimantan`, `Sulawesi`, `Maluku_Papua`) or a
        codebase `grid_region_id` value (`JAVA_BALI`, `NTB`, `SUMATERA`, …).
        The latter is normalized via `region_to_marginal_key`.
    time_of_day:
        `'daytime'` for solar comparator (PVOUT-weighted ~06:00–18:00 local)
        or `'nighttime'` for storage / dispatchable RE comparator.

    Returns
    -------
    float
        Estimated marginal generation cost (USD/MWh). NaN if `bpp_regional`
        is NaN.

    Raises
    ------
    KeyError
        If `grid_region` is not a known region.
    ValueError
        If `time_of_day` is not 'daytime' or 'nighttime'.
    """
    if time_of_day not in ("daytime", "nighttime"):
        raise ValueError(f"time_of_day must be 'daytime' or 'nighttime', got {time_of_day!r}")
    if isinstance(bpp_regional, float) and math.isnan(bpp_regional):
        return math.nan

    if grid_region in MARGINAL_COST_ADJUSTMENT_BY_REGION:
        key = grid_region
    else:
        key = region_to_marginal_key(grid_region)

    factor = MARGINAL_COST_ADJUSTMENT_BY_REGION[key][time_of_day]
    return float(bpp_regional) * factor


def marginal_confidence_for(grid_region: str) -> str:
    """Return the confidence flag for a region's marginal cost estimate.

    See `MARGINAL_CONFIDENCE_BY_REGION` and spec §6.3.

    Accepts both spec keys (`JAMALI`, `Maluku_Papua`, ...) and codebase
    `grid_region_id` values (`JAVA_BALI`, `MALUKU`, ...).

    Raises
    ------
    KeyError
        If the region is not recognized.
    """
    if grid_region in MARGINAL_CONFIDENCE_BY_REGION:
        return MARGINAL_CONFIDENCE_BY_REGION[grid_region]
    return MARGINAL_CONFIDENCE_BY_REGION[region_to_marginal_key(grid_region)]
