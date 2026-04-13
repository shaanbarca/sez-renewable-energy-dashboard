"""
wind_buildability_filters.py — Wind-adapted land suitability filter constants.

Wind turbines have different siting constraints than solar PV panels:
  - Slope: Relaxed to 20° (ridgelines are ideal for wind speed-up effect)
  - Cropland: ALLOWED (turbines coexist with agriculture, small footprint)
  - Min wind speed: 3.0 m/s (below IEC Class III cut-in, no generation)
  - Space: 25 ha/MWp (inter-turbine spacing 5-7 rotor diameters, ~4 MW/km²)
  - Elevation: Same 1,500m cap (air density drops, CF degrades)
  - Forest/peat/water/wetland/urban: Same exclusions as solar

The filter functions from buildability_filters.py (apply_exclusion_mask,
apply_slope_elevation_mask, apply_min_area_filter, compute_slope_degrees)
are technology-agnostic and reused directly. Only the thresholds differ.

Reference: ESDM Technology Catalogue 2024, Ch.4 (Wind Turbines)
           IRENA 2023 (onshore wind land use ~4 MW/km²)
"""

from __future__ import annotations

# ─── Wind-specific thresholds ────────────────────────────────────────────────

WIND_MAX_SLOPE_DEG: float = 20.0
"""Wind turbines tolerate steeper terrain than solar.
Ridgelines and hillcrests produce speed-up effects that improve CF.
20° is the practical limit for crane access during construction."""

WIND_MAX_ELEV_M: float = 1500.0
"""Same as solar. Air density at 1,500m is ~85% of sea level,
reducing turbine output by ~15%. Higher sites not viable in Indonesia."""

WIND_MIN_SPEED_MS: float = 3.0
"""IEC Class III cut-in wind speed. Below this, no generation is possible.
Pixels with mean annual wind speed < 3.0 m/s are excluded."""

WIND_MIN_AREA_HA: float = 10.0
"""Minimum contiguous buildable patch. Same as solar.
At ~1km raster resolution (~86 ha/pixel), this is a no-op."""

WIND_HA_PER_MWP: float = 25.0
"""Onshore wind space requirement: 25 ha/MWp (~4 MW/km²).
Based on inter-turbine spacing of 5-7 rotor diameters (630-880m for
a 126m rotor Vestas V126/3.45 MW). Source: IRENA 2023, ESDM 2024.
Solar uses 1.5 ha/MWp — wind needs ~17x more land per MWp."""

WIND_LAND_COVER_BUILDABLE_THRESHOLD: float = 0.5
"""Sub-pixel threshold for ESA WorldCover binary resampling.
Same as solar: >=50% of source 10m pixels must be buildable."""

# ESA WorldCover v200 (2021) — codes to EXCLUDE for wind siting.
# Key difference from solar: cropland (40) is INCLUDED (turbines coexist).
# Dense tree cover (10) still excluded: turbine hub height (~100m) needs
# clearance, and forest acts as roughness that reduces wind speed.
WIND_LAND_COVER_EXCLUDE_CODES: frozenset[int] = frozenset(
    [
        10,  # Tree cover (dense forest — roughness + clearance issues)
        50,  # Built-up / urban (noise setback constraints)
        80,  # Permanent water bodies
        90,  # Herbaceous wetland (foundation issues)
        95,  # Mangroves (protected + foundation issues)
    ]
)
"""Note: code 40 (cropland) is NOT excluded. Wind turbines routinely
operate in agricultural areas. The turbine footprint is ~0.5 ha each;
the rest of the inter-turbine spacing remains farmable."""

# ─── Constraint labels ───────────────────────────────────────────────────────

WIND_VALID_CONSTRAINTS: frozenset[str] = frozenset(
    [
        "kawasan_hutan",
        "slope",
        "peat",
        "land_cover",
        "low_wind",  # NEW: wind speed below cut-in
        "area_too_small",
        "unconstrained",
        "data_unavailable",
    ]
)


def compute_wind_buildability_constraint(
    n_pixels_raw: int,
    n_after_layer1a: int,
    n_after_layer1b: int,
    n_after_layer1cd: int,
    n_after_layer2: int,
    n_after_wind_speed: int,
    n_after_layer4: int,
) -> str:
    """Identify the dominant binding constraint for wind buildability.

    Same logic as solar's compute_buildability_constraint, plus a
    wind-speed filter layer between terrain and min-area.

    Returns one of: "kawasan_hutan" | "peat" | "land_cover" | "slope" |
                    "low_wind" | "area_too_small" | "unconstrained"
    """
    if n_pixels_raw == 0:
        return "unconstrained"

    removed = {
        "kawasan_hutan": n_pixels_raw - n_after_layer1a,
        "peat": n_after_layer1a - n_after_layer1b,
        "land_cover": n_after_layer1b - n_after_layer1cd,
        "slope": n_after_layer1cd - n_after_layer2,
        "low_wind": n_after_layer2 - n_after_wind_speed,
        "area_too_small": n_after_wind_speed - n_after_layer4,
    }

    if n_after_layer4 >= n_pixels_raw:
        return "unconstrained"

    return max(removed, key=lambda k: removed[k])
