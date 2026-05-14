"""Tests for the manual polygon override feature (#31 phase 1).

Two layers of coverage:
1. Helper module round-trip: save/load/get/delete on an isolated temp file
   so we never touch the real overrides geojson during testing.
2. Admin API routes: env-flag gating (router not mounted when flag off) +
   end-to-end save/get/delete via TestClient when flag is on.
"""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

from src.pipeline import manual_polygon_overrides as mpo

# ---------------------------------------------------------------------------
# Fixtures — isolate every test from the real file on disk
# ---------------------------------------------------------------------------


@pytest.fixture
def override_path(tmp_path: Path) -> Path:
    """Per-test temp path for the override file. Pass to load/save/etc."""
    return tmp_path / "manual_polygon_overrides.geojson"


def _square_polygon(lon: float, lat: float, side_deg: float = 0.01) -> dict:
    """Build a small valid GeoJSON Polygon centered at (lon, lat)."""
    h = side_deg / 2
    coords = [
        [lon - h, lat - h],
        [lon + h, lat - h],
        [lon + h, lat + h],
        [lon - h, lat + h],
        [lon - h, lat - h],
    ]
    return {"type": "Polygon", "coordinates": [coords]}


# ---------------------------------------------------------------------------
# Helper-module tests
# ---------------------------------------------------------------------------


def test_load_overrides_returns_empty_dict_when_file_absent(override_path: Path):
    """The pipeline must run cleanly before any override is saved."""
    assert not override_path.exists()
    assert mpo.load_overrides(override_path) == {}


def test_save_then_load_round_trip(override_path: Path):
    """Save an override, reload it, verify the geometry survives."""
    geom = _square_polygon(99.4484, 3.3611)
    saved = mpo.save_override("inalum-asahan", geom, notes="test", path=override_path)
    assert saved["properties"]["site_id"] == "inalum-asahan"
    assert saved["properties"]["notes"] == "test"
    assert saved["properties"]["edited_at"]  # ISO datetime stamped

    loaded = mpo.load_overrides(override_path)
    assert "inalum-asahan" in loaded
    # shapely round-trip preserves the bounding box
    assert pytest.approx(loaded["inalum-asahan"].bounds[0], abs=1e-9) == 99.4434
    assert pytest.approx(loaded["inalum-asahan"].bounds[2], abs=1e-9) == 99.4534


def test_save_replaces_existing_override(override_path: Path):
    """Second save for the same site_id replaces the first; no duplicates."""
    geom1 = _square_polygon(99.0, 3.0)
    geom2 = _square_polygon(100.0, 4.0)
    mpo.save_override("inalum-asahan", geom1, notes="v1", path=override_path)
    mpo.save_override("inalum-asahan", geom2, notes="v2", path=override_path)

    raw = json.loads(override_path.read_text())
    assert len(raw["features"]) == 1
    assert raw["features"][0]["properties"]["notes"] == "v2"
    loaded = mpo.load_overrides(override_path)
    # New geometry is around (100, 4), not (99, 3)
    assert pytest.approx(loaded["inalum-asahan"].bounds[0], abs=1e-9) == 99.995


def test_get_override_returns_feature_or_none(override_path: Path):
    geom = _square_polygon(99.0, 3.0)
    mpo.save_override("inalum-asahan", geom, path=override_path)
    assert (
        mpo.get_override("inalum-asahan", path=override_path)["properties"]["site_id"]
        == "inalum-asahan"
    )
    assert mpo.get_override("missing-site", path=override_path) is None


def test_delete_override_returns_true_when_present_false_when_absent(override_path: Path):
    geom = _square_polygon(99.0, 3.0)
    mpo.save_override("inalum-asahan", geom, path=override_path)
    assert mpo.delete_override("inalum-asahan", path=override_path) is True
    assert mpo.delete_override("inalum-asahan", path=override_path) is False
    assert mpo.load_overrides(override_path) == {}


def test_list_override_site_ids_returns_sorted(override_path: Path):
    mpo.save_override("zzz-site", _square_polygon(99.0, 3.0), path=override_path)
    mpo.save_override("aaa-site", _square_polygon(100.0, 4.0), path=override_path)
    assert mpo.list_override_site_ids(override_path) == ["aaa-site", "zzz-site"]


def test_save_rejects_non_polygon_geometry(override_path: Path):
    with pytest.raises(ValueError, match="Polygon or MultiPolygon"):
        mpo.save_override(
            "inalum-asahan",
            {"type": "Point", "coordinates": [99.4484, 3.3611]},
            path=override_path,
        )


def test_save_rejects_empty_site_id(override_path: Path):
    with pytest.raises(ValueError, match="site_id"):
        mpo.save_override("", _square_polygon(99.0, 3.0), path=override_path)


def test_save_rejects_self_intersecting_polygon(override_path: Path):
    """A bowtie polygon (figure-8) should fail shapely.is_valid.

    Note: shapely accepts some near-degenerate polygons silently — this
    coordinate set is large enough that the self-intersection is geometric,
    not just floating-point noise. If shapely's `is_valid` ever stops
    catching this it's a regression in our validation contract, not a test
    fixture problem.
    """
    bowtie = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [4.0, 4.0],
                [0.0, 4.0],
                [4.0, 0.0],
                [0.0, 0.0],
            ]
        ],
    }
    # First confirm shapely actually flags it as invalid — if not, the test
    # would silently pass while the validation contract is broken.
    from shapely.geometry import shape as _shape  # noqa: PLC0415

    assert not _shape(bowtie).is_valid, "test fixture is no longer self-intersecting"

    with pytest.raises(ValueError, match="not a valid polygon"):
        mpo.save_override("bowtie-site", bowtie, path=override_path)


def test_features_sorted_by_site_id_for_clean_git_diffs(override_path: Path):
    """Sites added out of order should round-trip in sorted order."""
    mpo.save_override("nusantara-industri-sejati", _square_polygon(122.4, -3.8), path=override_path)
    mpo.save_override("inalum-asahan", _square_polygon(99.45, 3.36), path=override_path)
    mpo.save_override("buli-industrial-park", _square_polygon(128.25, 0.84), path=override_path)
    raw = json.loads(override_path.read_text())
    site_ids = [f["properties"]["site_id"] for f in raw["features"]]
    assert site_ids == sorted(site_ids)


def test_save_rejects_projected_coordinates(override_path: Path):
    """GeoJSON spec requires WGS84. Saving a polygon in projected meters
    (e.g. EPSG:23830 UTM coords in the hundreds of thousands) should be
    rejected at the boundary — the rest of the pipeline rasterizes against
    EPSG:4326 and would silently produce nonsense otherwise.

    Eng review #52 §failure-modes flagged this as a critical gap.
    """
    # Indonesia UTM zone 49S, central Java — y is ~9,000,000 in meters.
    projected = {
        "type": "Polygon",
        "coordinates": [
            [
                [600000, 9230000],
                [600100, 9230000],
                [600100, 9230100],
                [600000, 9230100],
                [600000, 9230000],
            ]
        ],
    }
    with pytest.raises(ValueError, match="out of range"):
        mpo.save_override("inalum-asahan", projected, path=override_path)


def test_save_accepts_multipolygon_round_trip(override_path: Path):
    """KEK Tanjung Sauh is a real MultiPolygon (6 island fragments per
    `_load_kek_polygons`). The save_override type signature accepts
    `Polygon | MultiPolygon`, but every other test uses a simple Polygon.
    Cover the MultiPolygon path explicitly so Phase 2 (editor) can trust
    the contract."""
    multi = {
        "type": "MultiPolygon",
        "coordinates": [
            # Two non-overlapping square islands
            [[[99.40, 3.30], [99.41, 3.30], [99.41, 3.31], [99.40, 3.31], [99.40, 3.30]]],
            [[[99.50, 3.40], [99.51, 3.40], [99.51, 3.41], [99.50, 3.41], [99.50, 3.40]]],
        ],
    }
    saved = mpo.save_override("tanjung-sauh", multi, notes="2 islands", path=override_path)
    assert saved["geometry"]["type"] == "MultiPolygon"
    assert len(saved["geometry"]["coordinates"]) == 2

    loaded = mpo.load_overrides(override_path)
    assert "tanjung-sauh" in loaded
    # MultiPolygon survives shapely round-trip — bounds span both pieces.
    minx, miny, maxx, maxy = loaded["tanjung-sauh"].bounds
    assert pytest.approx(minx, abs=1e-9) == 99.40
    assert pytest.approx(maxx, abs=1e-9) == 99.51


def test_save_is_atomic_no_temp_file_leak(override_path: Path):
    """The `_safe_write` helper writes to a temp file and atomically renames.
    Verify no `.tmp` file is left behind after a successful save."""
    mpo.save_override("inalum-asahan", _square_polygon(99.45, 3.36), path=override_path)
    tmp_files = list(override_path.parent.glob(f"{override_path.name}.*.tmp"))
    assert tmp_files == [], f"temp file leaked after successful save: {tmp_files}"


# ---------------------------------------------------------------------------
# Admin API tests — env-flag gating + happy path
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_enabled(monkeypatch, tmp_path):
    """Reload `src.api.main` with EEZ_ENABLE_ADMIN_TOOLS=1, redirect the
    override file to a tmp path, and yield the reloaded app. Teardown
    (via fixture finalization) ALWAYS unsets the env var and reloads back
    to disabled — fires even if the test fails mid-execution, preventing
    env-state leak into other test modules.

    Eng review #52 §3B flagged the leak risk in the prior ad-hoc cleanup.
    """
    import src.api.main as _main_module  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    os.environ["EEZ_ENABLE_ADMIN_TOOLS"] = "1"
    importlib.reload(_main_module)
    try:
        yield _main_module
    finally:
        os.environ.pop("EEZ_ENABLE_ADMIN_TOOLS", None)
        importlib.reload(_main_module)


@pytest.fixture
def admin_disabled():
    """Reload `src.api.main` with EEZ_ENABLE_ADMIN_TOOLS unset, yield the
    reloaded app. Teardown reloads again to ensure clean state."""
    import src.api.main as _main_module  # noqa: PLC0415

    os.environ.pop("EEZ_ENABLE_ADMIN_TOOLS", None)
    importlib.reload(_main_module)
    try:
        yield _main_module
    finally:
        os.environ.pop("EEZ_ENABLE_ADMIN_TOOLS", None)
        importlib.reload(_main_module)


def test_admin_routes_404_when_env_flag_off(admin_disabled):
    """Without EEZ_ENABLE_ADMIN_TOOLS=1 the router isn't mounted — production safety.

    Uses POST so the SPA fallback handler (which only catches GET) doesn't
    return HTML — that fallback is unrelated and exists for serving the
    frontend bundle. POST against a non-existent route returns 405 / 404
    via FastAPI, which is the safe signal we want.
    """
    from starlette.testclient import TestClient  # noqa: PLC0415

    with TestClient(admin_disabled.app) as client:
        r = client.post(
            "/api/admin/polygons/inalum-asahan",
            json={"geometry": _square_polygon(99.4484, 3.3611)},
        )
        assert r.status_code in (404, 405), (
            f"admin POST reachable when flag off (status={r.status_code}, body: {r.text[:200]})"
        )
        if r.headers.get("content-type", "").startswith("application/json"):
            body = r.json()
            assert "site_id" not in (body if isinstance(body, dict) else {}), (
                "admin route appears to have processed the POST when flag off"
            )


def test_admin_routes_mounted_when_env_flag_on(admin_enabled):
    """Full end-to-end cycle: list / get / post / delete via TestClient."""
    from starlette.testclient import TestClient  # noqa: PLC0415

    with TestClient(admin_enabled.app) as client:
        # LIST is empty initially
        r = client.get("/api/admin/polygons")
        assert r.status_code == 200, r.text
        assert r.json() == {"site_ids": [], "count": 0}

        # GET on missing site returns 404
        assert client.get("/api/admin/polygons/inalum-asahan").status_code == 404

        # POST saves
        body = {
            "geometry": _square_polygon(99.4484, 3.3611),
            "notes": "manual trace from satellite",
            "edited_by": "test",
        }
        r = client.post("/api/admin/polygons/inalum-asahan", json=body)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["properties"]["site_id"] == "inalum-asahan"
        assert saved["properties"]["notes"] == "manual trace from satellite"

        # GET now succeeds
        r = client.get("/api/admin/polygons/inalum-asahan")
        assert r.status_code == 200
        assert r.json()["properties"]["site_id"] == "inalum-asahan"

        # LIST shows the site
        assert client.get("/api/admin/polygons").json() == {
            "site_ids": ["inalum-asahan"],
            "count": 1,
        }

        # POST invalid geometry — 400
        bad_body = {"geometry": {"type": "Point", "coordinates": [0, 0]}}
        r = client.post("/api/admin/polygons/inalum-asahan", json=bad_body)
        assert r.status_code == 400

        # DELETE works once, 404 the second time
        assert client.delete("/api/admin/polygons/inalum-asahan").status_code == 200
        assert client.delete("/api/admin/polygons/inalum-asahan").status_code == 404
        assert client.get("/api/admin/polygons").json() == {"site_ids": [], "count": 0}


def test_require_localhost_rejects_non_loopback_host():
    """Admin routes carry a `require_localhost` dependency that rejects any
    request whose client.host isn't a loopback address. TestClient reports
    host='testclient' which IS in the loopback allowlist (test suite trusted),
    so verify the rejection path directly against the dependency function.

    Eng review #52 §1C decision — defense in depth against CORS-allowed cross-
    origin JS hitting admin routes when the env flag is on locally.
    """
    from fastapi import HTTPException  # noqa: PLC0415

    from src.api.routes.admin import _LOOPBACK_HOSTS, require_localhost  # noqa: PLC0415

    # Sanity: loopback addresses are accepted (no exception).
    class _MockClient:
        def __init__(self, host: str):
            self.host = host

    class _MockRequest:
        def __init__(self, host: str | None):
            self.client = _MockClient(host) if host is not None else None

    for host in _LOOPBACK_HOSTS:
        require_localhost(_MockRequest(host))  # should not raise

    # Non-loopback rejected
    for host in ("203.0.113.5", "10.0.0.1", "evil.example.com"):
        with pytest.raises(HTTPException) as exc_info:
            require_localhost(_MockRequest(host))
        assert exc_info.value.status_code == 403

    # No client info → reject (defensive)
    with pytest.raises(HTTPException) as exc_info:
        require_localhost(_MockRequest(None))
    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Pipeline integration — verify the merge step picks up overrides
# ---------------------------------------------------------------------------


def test_load_all_site_polygons_applies_manual_override(monkeypatch, tmp_path):
    """Save an override, run the resource pipeline's polygon loader, verify
    the override geometry wins over the auto-generated polygon."""
    from src.pipeline import build_fct_site_resource as bfr  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    # Save an override for an existing official_kek site (kek-palu).
    # The override polygon is a tiny square far from the real Palu polygon,
    # so we can detect the swap by checking the result's bounds.
    far_geom = _square_polygon(50.0, 0.0, side_deg=0.001)  # off the coast of Africa
    mpo.save_override("kek-palu", far_geom, path=tmp_overrides)

    polygons = bfr._load_all_site_polygons()
    assert "kek-palu" in polygons
    # The override polygon's bounds are near (50, 0), not Palu's real ~(120, -1)
    minx, miny, maxx, maxy = polygons["kek-palu"].bounds
    assert 49.9 < minx < 50.1, f"override didn't win — bounds {polygons['kek-palu'].bounds}"

    # Provenance also reports manual_override for that site.
    tiers = bfr._load_all_site_provenance()
    assert tiers["kek-palu"] == "manual_override"


def test_load_all_site_polygons_appends_new_site_via_override(monkeypatch, tmp_path):
    """Resource pipeline: an override for a site NOT in any auto-generated
    source (e.g. one of the 21 'none'-tier sites currently on buffer fallback)
    should be added to the polygon dict by the merge step.

    Eng review #52 §3A: covers the append path in `_load_all_site_polygons`.
    """
    from src.pipeline import build_fct_site_resource as bfr  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    # `inalum-asahan` has no entry in kek_polygons.geojson or
    # data/industrial_sites/site_polygons.geojson (#50 OSM-gap site).
    geom = _square_polygon(99.4484, 3.3611)
    mpo.save_override("inalum-asahan", geom, path=tmp_overrides)

    polygons = bfr._load_all_site_polygons()
    assert "inalum-asahan" in polygons, "override did not append new site"

    tiers = bfr._load_all_site_provenance()
    assert tiers.get("inalum-asahan") == "manual_override"


# ---------------------------------------------------------------------------
# Solar potential pipeline — eng review #52 §3A required these
# ---------------------------------------------------------------------------


def test_solar_potential_load_site_polygons_applies_override(monkeypatch, tmp_path):
    """The OTHER polygon consumer: build_fct_site_solar_potential.py. If this
    wiring breaks, rooftop calculations silently use auto-generated polygons
    even when an override exists — exactly the bug-by-omission this whole
    feature is meant to prevent.

    Verifies override REPLACES an existing KEK polygon in `_load_site_polygons`
    (which returns a GeoDataFrame, unlike the resource pipeline's dict).
    """
    from src.pipeline import build_fct_site_solar_potential as bfsp  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    # Override kek-palu with a far-away polygon to detect the swap.
    far_geom = _square_polygon(50.0, 0.0, side_deg=0.001)
    mpo.save_override("kek-palu", far_geom, path=tmp_overrides)

    polygons_gdf = bfsp._load_site_polygons()
    assert polygons_gdf is not None
    palu_rows = polygons_gdf[polygons_gdf["site_id"] == "kek-palu"]
    assert len(palu_rows) == 1, f"expected 1 kek-palu row, got {len(palu_rows)}"
    minx, _, _, _ = palu_rows.iloc[0].geometry.bounds
    assert 49.9 < minx < 50.1, (
        f"override didn't win in solar pipeline — bounds {palu_rows.iloc[0].geometry.bounds}"
    )


def test_solar_potential_load_site_polygons_appends_new_site(monkeypatch, tmp_path):
    """Solar pipeline: override for a site NOT in any auto-generated source
    (one of the OSM-gap sites from #50) should be appended as a new row.

    Verifies the append branch in `_load_site_polygons` where overrides
    populate sites the auto-generated sources don't cover.
    """
    from src.pipeline import build_fct_site_solar_potential as bfsp  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    geom = _square_polygon(99.4484, 3.3611)
    mpo.save_override("inalum-asahan", geom, path=tmp_overrides)

    polygons_gdf = bfsp._load_site_polygons()
    assert polygons_gdf is not None
    inalum_rows = polygons_gdf[polygons_gdf["site_id"] == "inalum-asahan"]
    assert len(inalum_rows) == 1, "override-only site was not appended"


def test_solar_potential_polygon_source_tiers_stamps_manual_override(monkeypatch, tmp_path):
    """Solar pipeline's `_load_polygon_source_tiers` must report
    `manual_override` for any site present in the override file — the
    feature's promise of 'highest trust wins' depends on this stamp
    propagating to the rooftop output's polygon_source_tier column."""
    from src.pipeline import build_fct_site_solar_potential as bfsp  # noqa: PLC0415

    tmp_overrides = tmp_path / "manual_polygon_overrides.geojson"
    monkeypatch.setattr(mpo, "OVERRIDES_PATH", tmp_overrides)

    geom = _square_polygon(50.0, 0.0, side_deg=0.001)
    mpo.save_override("kek-palu", geom, path=tmp_overrides)

    tiers = bfsp._load_polygon_source_tiers()
    assert tiers.get("kek-palu") == "manual_override"
