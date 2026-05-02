"""Building geometric classification and rooftop solar capacity math.

# What's here

The §14 classifier — categorizes detected building footprints by shape into
solar-suitable vs solar-unsuitable types — and the panel-area to rooftop-MWp
math from spec §5.3. Pure functions, no I/O.

# Why classify before computing rooftop MW

GoB v3 detects every above-ground structure: warehouses, tanks, silos,
conveyors, cooling towers. Most are NOT rooftop-solar candidates. A naive
"sum building footprints × usable share × W/m²" overstates rooftop potential
by 30-50% on heavy industry sites (nickel RKEF, steel BF-BOF, refineries).

# §14.3 categories (from rooftop_solar_potential_feature_spec.md)

| Category         | Heuristic                                | Usability multiplier |
|------------------|------------------------------------------|----------------------|
| `too_small`      | area < BUILDING_MIN_AREA_M2              | 0.0                  |
| `tank_silo`      | circularity > BUILDING_CIRCULARITY_TANK… | 0.0                  |
| `conveyor`       | aspect_ratio > BUILDING_ASPECT_CONVEY…   | 0.1                  |
| `complex`        | hull_ratio < BUILDING_HULL_RATIO_COMPLEX | 0.2                  |
| `possibly_round` | circularity > 0.75 (between thresholds)  | 0.3                  |
| `elongated`      | aspect_ratio > 5 (between thresholds)    | 0.6                  |
| `standard_roof`  | default — passes all filters             | 1.0                  |

The thresholds live in `src/assumptions.py` (mutable per F10 user sliders +
calibrated per §14.6 manual validation before merge).

# §5.3 panel-to-MWp math (decomposed model)

```
panel_density_w_per_m2 = panel_power_w_dc / panel_area_m2
rooftop_kw_dc          = footprint_m² × usability × layout_density × panel_density / 1000
rooftop_kw_ac          = rooftop_kw_dc × thermal_derate
rooftop_mwh_per_year   = rooftop_kw_ac × pvout_kwh_per_kwp_per_year / 1000
```
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from shapely.geometry.base import BaseGeometry

from src.assumptions import (
    BUILDING_ASPECT_CONVEYOR_THRESHOLD,
    BUILDING_CIRCULARITY_TANK_THRESHOLD,
    BUILDING_HULL_RATIO_COMPLEX_THRESHOLD,
    BUILDING_MIN_AREA_M2,
    ROOFTOP_LAYOUT_DENSITY,
    ROOFTOP_PANEL_AREA_M2,
    ROOFTOP_PANEL_POWER_W_DC,
    THERMAL_DERATE_TROPICAL,
)

# Geometric thresholds for the soft-derate categories (between the hard-reject
# thresholds in assumptions.py). Tuned per §14.6 manual validation if needed.
SOFT_ROUND_CIRCULARITY_THRESHOLD = 0.75  # round-ish but not a tank
SOFT_ELONGATED_ASPECT_THRESHOLD = 5.0  # long warehouse but not a conveyor
EPSILON_M = 1e-9  # numerical tolerance for zero-width bounding boxes

BuildingCategory = Literal[
    "too_small",
    "tank_silo",
    "conveyor",
    "complex",
    "possibly_round",
    "elongated",
    "standard_roof",
    # Residential cluster — small footprint with many similar-sized neighbors
    # in a tight radius. Multiplier 0.0. Detected per-site BEFORE the
    # geometric classifier in `build_fct_site_solar_potential.py`, since the
    # check requires looking at neighbors (not a single-polygon property).
    "residential",
]


@dataclass(frozen=True)
class BuildingClassification:
    """Per-building output of the §14 classifier."""

    category: BuildingCategory
    usability_multiplier: float
    circularity: float
    aspect_ratio: float
    hull_ratio: float


def classify_building(
    polygon: BaseGeometry,
    area_m2: float,
    *,
    circularity_tank_threshold: float = BUILDING_CIRCULARITY_TANK_THRESHOLD,
    aspect_conveyor_threshold: float = BUILDING_ASPECT_CONVEYOR_THRESHOLD,
    min_area_m2: float = BUILDING_MIN_AREA_M2,
    hull_ratio_complex_threshold: float = BUILDING_HULL_RATIO_COMPLEX_THRESHOLD,
) -> BuildingClassification:
    """Classify a single building polygon into a §14 category.

    `polygon` should be in EPSG:23830 (UTM 50S) so .area, .length, etc. are
    in metres. Caller is responsible for the reprojection — we don't do it
    here per call (would dominate runtime).

    Thresholds are passed in for two reasons:
      1. Tests can override them without monkeypatching assumptions.py
      2. F10 frontend slider recompute path could pass user-tuned values
    """
    if area_m2 < min_area_m2 or polygon.is_empty:
        return BuildingClassification(
            category="too_small",
            usability_multiplier=0.0,
            circularity=0.0,
            aspect_ratio=0.0,
            hull_ratio=0.0,
        )

    perimeter = polygon.length
    circularity = (4 * math.pi * polygon.area) / (perimeter * perimeter) if perimeter > 0 else 0.0

    bbox = polygon.minimum_rotated_rectangle
    bbox_coords = list(bbox.exterior.coords)[:-1]
    edge_lengths = sorted(
        math.hypot(b[0] - a[0], b[1] - a[1])
        for a, b in zip(bbox_coords, bbox_coords[1:] + [bbox_coords[0]], strict=False)
    )
    width = edge_lengths[0] if edge_lengths else 0.0
    length = edge_lengths[-1] if edge_lengths else 0.0
    aspect_ratio = length / width if width > EPSILON_M else float("inf")

    hull_area = polygon.convex_hull.area
    hull_ratio = polygon.area / hull_area if hull_area > 0 else 0.0

    # Cascade — first match wins. Order matters: hard rejects (tank, conveyor,
    # complex) precede soft derates (possibly_round, elongated).
    if circularity > circularity_tank_threshold:
        category: BuildingCategory = "tank_silo"
        multiplier = 0.0
    elif aspect_ratio > aspect_conveyor_threshold:
        category = "conveyor"
        multiplier = 0.1
    elif hull_ratio < hull_ratio_complex_threshold:
        category = "complex"
        multiplier = 0.2
    elif circularity > SOFT_ROUND_CIRCULARITY_THRESHOLD:
        # Between standard_roof (~0.6) and tank (>0.85) — soft derate
        category = "possibly_round"
        multiplier = 0.3
    elif aspect_ratio > SOFT_ELONGATED_ASPECT_THRESHOLD:
        # Between standard (1-4) and conveyor (>8) — long warehouse / shed
        category = "elongated"
        multiplier = 0.6
    else:
        category = "standard_roof"
        multiplier = 1.0

    return BuildingClassification(
        category=category,
        usability_multiplier=multiplier,
        circularity=circularity,
        aspect_ratio=aspect_ratio,
        hull_ratio=hull_ratio,
    )


def panel_density_w_per_m2(
    panel_power_w_dc: float = ROOFTOP_PANEL_POWER_W_DC,
    panel_area_m2: float = ROOFTOP_PANEL_AREA_M2,
) -> float:
    """W/m² of panel area. Default = 200 W/m² (400 W panel, 2.0 m²)."""
    return panel_power_w_dc / panel_area_m2 if panel_area_m2 > 0 else 0.0


def rooftop_kw_dc(
    footprint_m2: float,
    usability_multiplier: float,
    *,
    layout_density: float = ROOFTOP_LAYOUT_DENSITY,
    panel_power_w_dc: float = ROOFTOP_PANEL_POWER_W_DC,
    panel_area_m2: float = ROOFTOP_PANEL_AREA_M2,
) -> float:
    """Per-building DC nameplate from footprint + classifier multiplier.

    rooftop_kw_dc =
      footprint_m² × usability × layout_density × panel_density / 1000
    """
    if footprint_m2 <= 0 or usability_multiplier <= 0:
        return 0.0
    density_w_per_m2 = panel_density_w_per_m2(panel_power_w_dc, panel_area_m2)
    return (footprint_m2 * usability_multiplier * layout_density * density_w_per_m2) / 1000.0


def rooftop_kw_ac(
    kw_dc: float,
    thermal_derate: float = THERMAL_DERATE_TROPICAL,
) -> float:
    """DC → AC at meter, applying tropical thermal derate (default 0.88)."""
    return kw_dc * thermal_derate
