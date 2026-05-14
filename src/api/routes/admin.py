"""Admin-gated API routes for the in-dashboard polygon editor (#31).

# Why this exists

The 81 industrial sites have auto-generated fence polygons from KEK /
OSM / Claude-traced sources. Some are wrong, some missing. Issue #31 builds
an in-dashboard editor that writes hand-drawn overrides to
`data/industrial_sites/manual_polygon_overrides.geojson`. These routes are
the backend side of that flow.

# Security model

All routes are gated on `EEZ_ENABLE_ADMIN_TOOLS=1` (env var, defaults to off).
When the flag is off the router is NOT included in the FastAPI app at all
— consumers get a normal 404 from the framework, not a 401/403, so the
existence of the admin surface isn't even leaked. Production (Render) leaves
the var unset; local dev sets it in `.env`.

This is single-author tooling: no auth beyond the env flag, no RBAC, no
rate-limiting. The trust model assumes "if you can set the env var, you have
local file-write access anyway." Do NOT enable on a shared/public instance.

# Endpoints

- `GET /api/admin/polygons` — list every site_id with an override (review
  tooling, Phase 3 of #31)
- `GET /api/admin/polygons/{site_id}` — return the override Feature for
  `site_id` (or 404). Pre-fills the editor with the current override so the
  user can refine an existing fence rather than starting from auto.
- `POST /api/admin/polygons/{site_id}` — save/replace the override.
  Body: `{ "geometry": GeoJSON Polygon|MultiPolygon, "notes": string|null,
  "edited_by": string|null }`
- `DELETE /api/admin/polygons/{site_id}` — drop the override; pipeline
  reverts to the auto-generated polygon for that site on next run.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.pipeline.manual_polygon_overrides import (
    delete_override,
    get_override,
    list_override_site_ids,
    save_override,
)

# Loopback addresses we accept for admin endpoints. IPv4 + IPv6 + the
# hostname form that Starlette sometimes reports for dev-server requests.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def require_localhost(request: Request) -> None:
    """Reject any request whose `client.host` isn't a loopback address.

    Defense in depth on top of the env-flag gate in `src/api/main.py`. The
    env flag prevents the router from being mounted at all in production
    (Render), but on a dev machine with `EEZ_ENABLE_ADMIN_TOOLS=1` set,
    the CORSMiddleware's `allow_origins=["*"]` would otherwise let a
    malicious page from a different origin issue admin requests in the
    dev browser. Binding admin routes to localhost-only closes that hole.

    Returns None on success; raises 403 otherwise. The 'testclient' host
    is included so Starlette's TestClient (used by pytest) doesn't have
    to spoof an IP — the test suite is trusted.
    """
    host = request.client.host if request.client else None
    if host not in _LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(f"admin endpoints are bound to localhost; client.host={host!r} rejected"),
        )


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_localhost)],
)


class PolygonOverridePayload(BaseModel):
    """Request body for POST /api/admin/polygons/{site_id}."""

    geometry: dict[str, Any] = Field(
        ...,
        description="GeoJSON Polygon or MultiPolygon geometry to save as this site's fence.",
    )
    notes: str | None = Field(
        default=None,
        description="Optional free-text note describing why this override was made.",
    )
    edited_by: str | None = Field(
        default=None,
        description="Optional username string. Single-author tooling so this is informational.",
    )


@router.get("/polygons")
async def list_overrides() -> dict[str, Any]:
    """Return the list of site_ids that have a manual polygon override."""
    ids = list_override_site_ids()
    return {"site_ids": ids, "count": len(ids)}


@router.get("/polygons/{site_id}")
async def get_polygon_override(site_id: str) -> dict[str, Any]:
    """Return the override Feature for `site_id`, or 404 if absent."""
    feature = get_override(site_id)
    if feature is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No override exists for site_id={site_id!r}",
        )
    return feature


@router.post("/polygons/{site_id}", status_code=status.HTTP_200_OK)
async def save_polygon_override(site_id: str, payload: PolygonOverridePayload) -> dict[str, Any]:
    """Save or replace the override for `site_id`.

    Geometry is validated (must be Polygon/MultiPolygon, shapely.is_valid).
    Existing override is replaced in place; audit trail is in git history.
    """
    try:
        feature = save_override(
            site_id=site_id,
            geometry=payload.geometry,
            notes=payload.notes,
            edited_by=payload.edited_by,
        )
    except ValueError as exc:
        # Bad geometry, bad site_id, etc. Caller's fault.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return feature


@router.delete("/polygons/{site_id}", status_code=status.HTTP_200_OK)
async def delete_polygon_override(site_id: str) -> dict[str, Any]:
    """Remove the override for `site_id`. 404 if nothing existed."""
    removed = delete_override(site_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No override existed for site_id={site_id!r}",
        )
    return {"site_id": site_id, "deleted": True}
