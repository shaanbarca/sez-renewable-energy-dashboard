"""Polygon source provenance — classifies where each site's fence-boundary
polygon came from so the dashboard can flag which numbers are grounded in
official government data vs. estimated by automated methods.

# Why this matters

The rooftop_solar_mwp_potential number for a site depends entirely on what
buildings the polygon clip catches. Wide / loose / wrong polygons over-count
(adjacent factory bleed); tight / accurate polygons match reality. Without
provenance, a user looking at a 50 MWp number can't tell whether they're
seeing a government KEK boundary (high trust) or a Claude-traced estimate
(verify before quoting in a report).

# Tiers (ordered by trust descending)

  1. `manual_override`     — Polygon hand-drawn in the dashboard's admin-mode
                             polygon editor (#31) against satellite imagery
                             + buildings overlay, then saved to
                             `data/industrial_sites/manual_polygon_overrides.geojson`.
                             Highest trust — a human verified the fence
                             against ground-truth imagery, knows the site
                             context, and committed the polygon to git.
                             Wins over every auto-generated tier below.
  2. `official_kek`        — Indonesian KEK boundaries published by OSS/KEK
                             national portal. 25 polygons in
                             `outputs/data/raw/kek_polygons.geojson`.
                             High confidence; government-issued.
  3. `osm_landuse_industrial`
                           — Community-maintained OpenStreetMap polygons
                             tagged `landuse=industrial` or `man_made=works`.
                             Verified by OSM contributors but not government
                             official. Quality varies by region (Java >
                             outer islands).
  4. `claude_building_hull_estimate`
                           — Polygon traced in-session from the union of
                             GoB+MS detected buildings ≥1500 m² + buffer
                             dilate/erode. Rooftop count is conservative
                             but the fence boundary is approximated, not
                             verified against any authoritative source.
                             Requires human visual verification before
                             relying on for site selection.
  5. `none`                — No fence-line polygon found. Both the rooftop
                             building catchment and the within-boundary
                             ground-mounted calculation fall back to a 2 km
                             centroid buffer. Likely over-counts when site
                             sits in dense industrial corridors (rooftop:
                             adjacent factory bleed; ground-mount: same).
                             UI surfaces a warning badge for this tier.
"""

from __future__ import annotations

from typing import Literal

PolygonSourceTier = Literal[
    "manual_override",
    "official_kek",
    "osm_landuse_industrial",
    "claude_building_hull_estimate",
    "none",
]

TIER_LABELS: dict[str, str] = {
    "manual_override": "Manual (human-verified)",
    "official_kek": "Official KEK (government)",
    "osm_landuse_industrial": "OSM (community-verified)",
    "claude_building_hull_estimate": "Estimated (Claude vision)",
    "none": "No polygon (2 km buffer fallback)",
}

TIER_DESCRIPTIONS: dict[str, str] = {
    "manual_override": (
        "Polygon hand-drawn in the admin-mode polygon editor against satellite "
        "imagery and the buildings overlay, then committed to git. A human "
        "verified this fence against ground-truth and chose to override the "
        "auto-generated source. Highest trust."
    ),
    "official_kek": (
        "Government-published KEK boundary from the Indonesian OSS/KEK national portal. High trust."
    ),
    "osm_landuse_industrial": (
        "OpenStreetMap polygon (landuse=industrial / man_made=works) maintained by "
        "the OSM community. Verified by contributors but not government-issued."
    ),
    "claude_building_hull_estimate": (
        "Estimated fence boundary — Claude traced this by unioning the largest "
        "GoB+MS detected buildings inside the site catchment. Rooftop number is "
        "conservative, but the polygon itself has not been independently verified. "
        "Treat as an estimate; verify visually before relying on for site selection."
    ),
    "none": (
        "No fence-line polygon found yet. Both rooftop and ground-mounted "
        "estimates use a 2 km centroid buffer, which over-counts when the "
        "site sits in a dense industrial corridor (adjacent factories' "
        "rooftops and land get included). Treat numbers as low-trust; "
        "verify visually or hunt a real polygon."
    ),
}


def classify_industrial_polygon_props(props: dict) -> PolygonSourceTier:
    """Classify a feature from `data/industrial_sites/site_polygons.geojson`.

    Looks at the `source_name` field first (set explicitly for newer entries),
    then falls back to inspecting `osm_*` fields (older entries that came from
    OSM Nominatim queries before we started tracking source_name).
    """
    src = (props.get("source_name") or "").lower()
    if "claude" in src or "building_footprint_hull" in src:
        return "claude_building_hull_estimate"
    if "osm" in src or props.get("osm_id") or props.get("osm_class"):
        return "osm_landuse_industrial"
    if src:
        # Unknown source label — be conservative and treat as estimate.
        return "claude_building_hull_estimate"
    # No source info at all — older entry, almost certainly OSM-Nominatim.
    if any(k in props for k in ("osm_class", "osm_id", "osm_type", "osm_display_name")):
        return "osm_landuse_industrial"
    return "claude_building_hull_estimate"
