"""Per-request polygon override resolver for #26 — clickable polygon → LCOE recompute.

When the user clicks a buildable polygon on the dashboard map, the picker's
substation-anchored choice for that site is replaced with the clicked polygon's
centroid, PVOUT, and capacity. This module is the row-level patch that flows
the override through to the grid_connected_solar LCOE pipeline.

Scope: grid_connected_solar scenario only. The within_boundary captive LCOE
keeps using the KEK polygon's avg PVOUT — most clicked polygons sit within 50km
of the KEK but outside its fence-line, so forcing them onto within_boundary
would mislabel the scenario.

The resolver is a pure-ish function: callers pass a per-request copy of
resource_df, the override dict, and the loaded polygons/substations layers.
Mutating the cached startup-loaded df would corrupt state across requests —
the route handler in src/api/routes/scorecard.py owns the copy boundary.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
from fastapi import HTTPException

from src.pipeline.buildability_filters import haversine_km

# Single source of truth for the fields the resolver patches. compute_lcoe_live
# (src/dash/logic/lcoe.py) and compute_grid_integration_live (src/dash/logic/
# grid.py) both read from this set. Keeping it as a named constant prevents
# drift between the patch and what downstream code actually consumes.
POLYGON_OVERRIDE_FIELDS: tuple[str, ...] = (
    "pvout_buildable_best_50km",
    "pvout_best_50km",
    "best_solar_site_lat",
    "best_solar_site_lon",
    "project_scale_solar_mwp",
    "dist_solar_to_nearest_substation_km",
)


def apply_polygon_overrides(
    resource_df: pd.DataFrame,
    overrides: dict[str, int] | None,
    polygons_geojson: dict[str, Any] | None,
    substations: list[dict[str, Any]] | None,
) -> pd.DataFrame:
    """Mutate `resource_df` in-place, applying per-site polygon overrides.

    Parameters
    ----------
    resource_df:
        Per-request copy of the resource df. Mutated. Caller is responsible
        for copying the cached startup-loaded df before passing it in.
    overrides:
        {site_id: feature_index} from the request body. None or empty = no-op.
    polygons_geojson:
        Loaded buildable_polygons.geojson dict (already in memory at startup).
    substations:
        List of substation dicts with `lat`/`lon` keys (~3000 points).

    Returns
    -------
    pd.DataFrame
        The mutated `resource_df` (same object as input).

    Raises
    ------
    HTTPException
        422 if any override is invalid:
        - feature_index out of bounds
        - polygon has non-finite/non-positive avg_pvout_annual or capacity_mwp
        - polygon missing centroid_lat / centroid_lon
        - site_id not in resource_df
        - polygons layer not loaded at server startup
    """
    if not overrides:
        return resource_df

    if polygons_geojson is None:
        raise HTTPException(
            status_code=422,
            detail="polygon_overrides supplied but buildable_polygons layer not loaded",
        )

    features = polygons_geojson.get("features") or []
    n_features = len(features)

    for site_id, feature_index in overrides.items():
        if feature_index is None:
            continue  # explicit null = no-op for this site

        if not isinstance(feature_index, int) or feature_index < 0 or feature_index >= n_features:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"polygon_override[{site_id}]: feature_index {feature_index} "
                    f"out of bounds (0..{n_features - 1})"
                ),
            )

        feat = features[feature_index]
        props = feat.get("properties") or {}
        pvout = props.get("avg_pvout_annual")
        capacity_mwp = props.get("capacity_mwp")
        lat = props.get("centroid_lat")
        lon = props.get("centroid_lon")

        if pvout is None or not math.isfinite(pvout) or pvout <= 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"polygon_override[{site_id}]: polygon {feature_index} has invalid "
                    f"avg_pvout_annual={pvout!r}"
                ),
            )
        if capacity_mwp is None or not math.isfinite(capacity_mwp) or capacity_mwp <= 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"polygon_override[{site_id}]: polygon {feature_index} has invalid "
                    f"capacity_mwp={capacity_mwp!r}"
                ),
            )
        if lat is None or lon is None or not math.isfinite(lat) or not math.isfinite(lon):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"polygon_override[{site_id}]: polygon {feature_index} missing "
                    "centroid_lat / centroid_lon"
                ),
            )

        mask = resource_df["site_id"] == site_id
        if not mask.any():
            raise HTTPException(
                status_code=422,
                detail=f"polygon_override: site_id {site_id!r} not in resource_df",
            )

        dist_km = _nearest_substation_km(float(lat), float(lon), substations)

        resource_df.loc[mask, "pvout_buildable_best_50km"] = float(pvout)
        resource_df.loc[mask, "pvout_best_50km"] = float(pvout)
        resource_df.loc[mask, "best_solar_site_lat"] = float(lat)
        resource_df.loc[mask, "best_solar_site_lon"] = float(lon)
        resource_df.loc[mask, "project_scale_solar_mwp"] = float(capacity_mwp)
        resource_df.loc[mask, "dist_solar_to_nearest_substation_km"] = dist_km

    return resource_df


def _nearest_substation_km(
    lat: float, lon: float, substations: list[dict[str, Any]] | None
) -> float:
    """Great-circle distance in km from (lat, lon) to the nearest substation.

    Returns `inf` if the substations list is empty / None. ~3000 substations
    nationally, so the linear scan is microseconds per override.
    """
    if not substations:
        return float("inf")
    min_km = float("inf")
    for s in substations:
        s_lat = s.get("lat")
        s_lon = s.get("lon")
        if s_lat is None or s_lon is None:
            continue
        km = haversine_km(lat, lon, float(s_lat), float(s_lon))
        if km < min_km:
            min_km = km
    return min_km
