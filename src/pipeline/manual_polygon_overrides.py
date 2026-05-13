"""Manual polygon overrides — human-verified fence boundaries that supersede
the auto-generated polygons in `outputs/data/raw/kek_polygons.geojson` and
`data/industrial_sites/site_polygons.geojson`.

# Why this exists

Some auto-generated polygons are wrong — too tight (cuts off active facilities),
too loose (includes unrelated land), misaligned, or missing entirely (the
21 sites currently on the 2 km buffer fallback per polygon hunt #45 / #50).
Editing the auto-generated files by hand in QGIS or VS Code is slow and
loses provenance context.

Issue #31 builds an in-dashboard editor that writes here. This module is the
read/write side: load existing overrides for the pipeline, save new ones from
the admin API, delete on user demand.

# File contract

Single GeoJSON FeatureCollection at
`data/industrial_sites/manual_polygon_overrides.geojson`. One feature per
overridden site. Schema:

```json
{
  "type": "Feature",
  "geometry": {"type": "Polygon" | "MultiPolygon", "coordinates": [[[...]]]},
  "properties": {
    "site_id": "...",
    "edited_at": "ISO-8601 datetime UTC",
    "edited_by": "username string (optional)",
    "notes": "free-text (optional)"
  }
}
```

`site_id` is the unique key — at most one override per site. New overrides
replace older ones in-place (no version history; the audit trail is in git).

# Trust tier

Overrides win over every auto-generated tier in
`src/model/polygon_provenance.py`. A site with a manual override has
`polygon_source_tier = "manual_override"`. See pipeline merge step in
`build_fct_site_resource.py` and `build_fct_site_solar_potential.py`.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import shape as shapely_shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERRIDES_PATH = REPO_ROOT / "data" / "industrial_sites" / "manual_polygon_overrides.geojson"


def _empty_collection() -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": []}


def _resolve_path(path: Path | None) -> Path:
    """Module-level lookup so monkeypatching `mpo.OVERRIDES_PATH` in tests
    affects the default — Python evaluates default args at definition time,
    so the previous `path: Path = OVERRIDES_PATH` pattern captured the path
    once and couldn't be redirected from tests. Resolving at call time fixes
    that without forcing every caller to pass the path explicitly."""
    return path if path is not None else OVERRIDES_PATH


def _load_raw(path: Path | None = None) -> dict[str, Any]:
    """Load the raw FeatureCollection dict. Returns an empty collection if
    the file is missing — pipeline runs fine before any override is saved."""
    path = _resolve_path(path)
    if not path.exists():
        return _empty_collection()
    data = json.loads(path.read_text())
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: expected FeatureCollection, got {data.get('type')}")
    data.setdefault("features", [])
    return data


def _safe_write(path: Path, content: str) -> None:
    """Atomically write `content` to `path` with exclusive file locking.

    Addresses two correctness concerns from the eng review (PR #52):
    1. Concurrent writes from two POSTs are serialized via `fcntl.flock`
       on a sibling lock file. The lock is held only for the duration of
       the write — a few ms at most — so contention is negligible.
    2. The write itself is atomic: content goes to a temp file in the
       same directory, then `os.replace()` swaps it into place. POSIX
       guarantees `os.replace` is atomic on the same filesystem, so a
       crash mid-write leaves the original file intact (not half-rewritten).

    Same-directory temp file matters: `os.replace` only atomic when source
    and destination are on the same filesystem. Using `tempfile.gettempdir()`
    could land on a different mount; using `path.parent` is safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "w") as lock_fp:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX)
        try:
            # tempfile in the same directory so os.replace is atomic.
            fd, tmp_path_str = tempfile.mkstemp(
                prefix=path.name + ".",
                suffix=".tmp",
                dir=str(path.parent),
            )
            tmp_path = Path(tmp_path_str)
            try:
                with os.fdopen(fd, "w") as tmp_fp:
                    tmp_fp.write(content)
                os.replace(tmp_path, path)
            except Exception:
                # Best-effort cleanup of the temp file if anything fails
                # before the atomic replace. After replace there is no
                # tmp_path to clean up.
                if tmp_path.exists():
                    tmp_path.unlink()
                raise
        finally:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)


# GeoJSON spec (RFC 7946) requires coordinates in WGS84 lon/lat. The override
# file participates in that contract — projected coordinates (e.g. UTM meters)
# would silently corrupt every downstream pipeline that rasterizes against
# `EPSG:4326`. Validate at the save boundary so the file format guarantee
# holds for all readers.
_LON_MIN, _LON_MAX = -180.0, 180.0
_LAT_MIN, _LAT_MAX = -90.0, 90.0


def _validate_wgs84_bounds(geom_obj: BaseGeometry) -> None:
    """Raise ValueError if any coordinate falls outside valid lon/lat bounds.

    Catches the common mistake of saving a projected polygon (e.g. EPSG:23830
    UTM meters in the millions) into a GeoJSON file that the rest of the
    pipeline treats as WGS84. Doesn't prove the geometry IS in WGS84 — it
    just rejects the values that obviously aren't.
    """
    minx, miny, maxx, maxy = geom_obj.bounds
    if not (_LON_MIN <= minx <= _LON_MAX and _LON_MIN <= maxx <= _LON_MAX):
        raise ValueError(
            f"longitude out of range — got bounds lon=[{minx}, {maxx}], "
            f"expected within [{_LON_MIN}, {_LON_MAX}]. "
            f"GeoJSON requires WGS84 (lon/lat); did you save projected coordinates?"
        )
    if not (_LAT_MIN <= miny <= _LAT_MAX and _LAT_MIN <= maxy <= _LAT_MAX):
        raise ValueError(
            f"latitude out of range — got bounds lat=[{miny}, {maxy}], "
            f"expected within [{_LAT_MIN}, {_LAT_MAX}]. "
            f"GeoJSON requires WGS84 (lon/lat); did you save projected coordinates?"
        )


def load_overrides(path: Path | None = None) -> dict[str, BaseGeometry]:
    """Return {site_id: shapely_geometry} for every override in the file.

    Used by pipeline modules during polygon loading to merge over auto-generated
    sources. Keep this dict-shaped (not GeoDataFrame) so it composes with the
    existing _load_all_site_polygons() return type.
    """
    data = _load_raw(path)
    out: dict[str, BaseGeometry] = {}
    for feat in data["features"]:
        props = feat.get("properties") or {}
        sid = props.get("site_id")
        geom = feat.get("geometry")
        if not sid or not geom:
            continue
        try:
            out[sid] = shapely_shape(geom)
        except Exception as exc:
            # A bad polygon in the file should not break the whole pipeline.
            # Skip + log; tests cover the validation path.
            print(f"  WARNING: manual_polygon_overrides[{sid}] invalid geometry: {exc}")
            continue
    return out


def get_override(site_id: str, path: Path | None = None) -> dict[str, Any] | None:
    """Return the full GeoJSON Feature for `site_id`, or None if absent.

    Used by the admin GET endpoint to pre-fill the editor with the existing
    override (if any) so the user starts from the current saved state rather
    than the auto-generated polygon.
    """
    data = _load_raw(path)
    for feat in data["features"]:
        if (feat.get("properties") or {}).get("site_id") == site_id:
            return feat
    return None


def save_override(
    site_id: str,
    geometry: dict[str, Any],
    notes: str | None = None,
    edited_by: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Insert or replace the override for `site_id`. Returns the saved Feature.

    `geometry` must be a GeoJSON Polygon or MultiPolygon dict. Validates by
    constructing a shapely geometry and checking `.is_valid` — invalid
    polygons (self-intersecting, etc.) are rejected before write.
    """
    path = _resolve_path(path)
    if not site_id or not isinstance(site_id, str):
        raise ValueError("site_id must be a non-empty string")
    if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(
            f"geometry must be a Polygon or MultiPolygon GeoJSON; got type={geometry.get('type')}"
        )
    geom_obj = shapely_shape(geometry)
    if not geom_obj.is_valid:
        raise ValueError(
            f"geometry is not a valid polygon (shapely.is_valid=False): {explain_validity(geom_obj)}"
        )
    _validate_wgs84_bounds(geom_obj)

    data = _load_raw(path)
    feature: dict[str, Any] = {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "site_id": site_id,
            "edited_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "edited_by": edited_by,
            "notes": notes,
        },
    }
    # Replace existing override for this site_id if present; else append.
    replaced = False
    for i, feat in enumerate(data["features"]):
        if (feat.get("properties") or {}).get("site_id") == site_id:
            data["features"][i] = feature
            replaced = True
            break
    if not replaced:
        data["features"].append(feature)

    # Sort by site_id so git diffs are clean and reviewable.
    data["features"].sort(key=lambda f: (f.get("properties") or {}).get("site_id", ""))

    _safe_write(path, json.dumps(data, indent=2) + "\n")
    return feature


def delete_override(site_id: str, path: Path | None = None) -> bool:
    """Remove the override for `site_id`. Returns True if a feature was
    removed, False if nothing existed for that site_id."""
    path = _resolve_path(path)
    data = _load_raw(path)
    before = len(data["features"])
    data["features"] = [
        f for f in data["features"] if (f.get("properties") or {}).get("site_id") != site_id
    ]
    after = len(data["features"])
    if after == before:
        return False
    _safe_write(path, json.dumps(data, indent=2) + "\n")
    return True


def list_override_site_ids(path: Path | None = None) -> list[str]:
    """List every site_id that has an override. For admin LIST endpoint
    and the review tooling in Phase 3 of #31."""
    data = _load_raw(path)
    return sorted(
        (f.get("properties") or {}).get("site_id", "")
        for f in data["features"]
        if (f.get("properties") or {}).get("site_id")
    )
