"""Tests for the FastAPI backend endpoints.

Uses Starlette TestClient which triggers the lifespan (startup) event
so all data is loaded before tests run.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from src.api.main import app

# ---------------------------------------------------------------------------
# Fixture: shared TestClient (data loads once across all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    """Create a TestClient that triggers startup data loading."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Helper: get default assumptions/thresholds for scorecard POST
# ---------------------------------------------------------------------------


def _default_body(client: TestClient) -> dict:
    """Fetch defaults and build a valid scorecard request body."""
    resp = client.get("/api/defaults")
    data = resp.json()
    return {
        "assumptions": data["assumptions"],
        "thresholds": data["thresholds"],
        "benchmark_mode": "tariff",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_scorecard_valid(client):
    """1. POST /api/scorecard with valid defaults returns 200 and 25 items."""
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert "scorecard" in data
    assert len(data["scorecard"]) >= 25  # at least 25 KEKs, plus industrial sites
    # Check required fields present
    first = data["scorecard"][0]
    for key in ["site_id", "action_flag", "lcoe_mid_usd_mwh"]:
        assert key in first


def test_scorecard_invalid_capex(client):
    """2. POST /api/scorecard with negative CAPEX returns 422."""
    body = _default_body(client)
    body["assumptions"]["capex_usd_per_kw"] = -100
    resp = client.post("/api/scorecard", json=body)
    assert resp.status_code == 422


def test_scorecard_max_captive_capacity_mwp_alias(client):
    """Deprecation alias: `max_captive_capacity_mwp` mirrors the renamed
    `regional_groundmount_potential_mwp_50km` for one release. See
    `src/api/routes/scorecard.py::_df_to_clean_records`. Remove this test
    + the alias when v4.2 ships.
    """
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    assert resp.status_code == 200
    data = resp.json()
    for row in data["scorecard"]:
        new = row.get("regional_groundmount_potential_mwp_50km")
        old = row.get("max_captive_capacity_mwp")
        # Either both null or both equal — never the case where one exists
        # and the other is missing.
        assert old == new, (
            f"alias mismatch on {row.get('site_id')}: "
            f"max_captive_capacity_mwp={old!r} vs "
            f"regional_groundmount_potential_mwp_50km={new!r}"
        )


def test_defaults(client):
    """3. GET /api/defaults returns assumptions, thresholds, and slider_configs."""
    resp = client.get("/api/defaults")
    assert resp.status_code == 200
    data = resp.json()
    assert "assumptions" in data
    assert "thresholds" in data
    assert "slider_configs" in data
    sc = data["slider_configs"]
    assert "tier1" in sc
    assert "tier2" in sc
    assert "tier3" in sc
    assert "wacc" in sc
    assert sc["wacc"]["default"] == 10


def test_layers_substations(client):
    """4. GET /api/layers/substations returns points list."""
    resp = client.get("/api/layers/substations")
    assert resp.status_code == 200
    data = resp.json()
    assert "points" in data
    assert isinstance(data["points"], list)


def test_layers_nonexistent(client):
    """5. GET /api/layers/nonexistent returns 404."""
    resp = client.get("/api/layers/nonexistent")
    assert resp.status_code == 404


def test_layers_industrial_polygons(client):
    """GET /api/layers/industrial_polygons returns valid FeatureCollection.

    Drives the "Site Boundaries" composite toggle in the dashboard. If this
    breaks, the orange industrial polygons stop loading on the map.
    """
    resp = client.get("/api/layers/industrial_polygons")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    feats = data["features"]
    assert len(feats) > 0, "no industrial polygons in payload — geojson missing/empty?"

    indonesia_lat = (-11.0, 6.0)
    indonesia_lon = (95.0, 141.0)
    site_ids: list[str] = []
    for feat in feats:
        sid = feat.get("properties", {}).get("site_id")
        assert sid, f"feature missing site_id: {feat.get('properties')}"
        site_ids.append(sid)

        geom = feat["geometry"]
        assert geom["type"] in {"Polygon", "MultiPolygon"}
        rings = (
            geom["coordinates"]
            if geom["type"] == "Polygon"
            else [r for poly in geom["coordinates"] for r in poly]
        )
        for ring in rings:
            for lon, lat in ring:
                assert indonesia_lat[0] <= lat <= indonesia_lat[1], (
                    f"{sid}: lat {lat} outside Indonesia"
                )
                assert indonesia_lon[0] <= lon <= indonesia_lon[1], (
                    f"{sid}: lon {lon} outside Indonesia"
                )

    # site_ids must be unique — frontend keys overlays by site_id.
    assert len(site_ids) == len(set(site_ids)), f"duplicate site_id: {site_ids}"


def test_layers_kek_polygons_aliased_to_site_polygons(client):
    """GET /api/layers/kek_polygons returns same data as /api/layers/site_polygons.

    The frontend uses kek_polygons as the layer key for KEK boundaries; both
    the kek_polygons and industrial_polygons layers feed the combined
    "Site Boundaries" toggle.
    """
    resp_kek = client.get("/api/layers/kek_polygons")
    resp_site = client.get("/api/layers/site_polygons")
    assert resp_kek.status_code == 200
    assert resp_site.status_code == 200
    kek = resp_kek.json()
    site = resp_site.json()
    assert kek["type"] == "FeatureCollection"
    assert len(kek["features"]) == len(site["features"])
    assert len(kek["features"]) >= 25, "expected at least 25 KEK polygons"


def test_kek_polygon_valid(client):
    """6. GET /api/site/{valid_id}/polygon returns feature + bbox + center."""
    resp = client.get("/api/site/industropolis-batang/polygon")
    assert resp.status_code == 200
    data = resp.json()
    assert "feature" in data
    assert "bbox" in data
    assert "center" in data
    assert "min_lon" in data["bbox"]
    assert "lat" in data["center"]


def test_kek_polygon_invalid(client):
    """7. GET /api/site/invalid-id/polygon returns 404."""
    resp = client.get("/api/site/invalid-id-xyz/polygon")
    assert resp.status_code == 404


def test_ruptl_metrics(client):
    """8. GET /api/ruptl-metrics returns pipeline + region_colors."""
    resp = client.get("/api/ruptl-metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "pipeline" in data
    assert "region_colors" in data
    assert isinstance(data["pipeline"], list)
    assert isinstance(data["region_colors"], dict)


def test_infrastructure(client):
    """9. GET /api/layers/infrastructure returns markers list."""
    resp = client.get("/api/layers/infrastructure")
    assert resp.status_code == 200
    data = resp.json()
    assert "markers" in data
    assert isinstance(data["markers"], list)


def test_kek_substations_valid(client):
    """10. GET /api/site/{valid_id}/substations returns substations with dist_km."""
    resp = client.get("/api/site/industropolis-batang/substations?radius_km=50")
    assert resp.status_code == 200
    data = resp.json()
    assert "substations" in data
    assert isinstance(data["substations"], list)
    # If there are substations, check structure
    if data["substations"]:
        s = data["substations"][0]
        assert "dist_km" in s
        assert "lat" in s
        assert "lon" in s
        # Exactly one should be nearest
        nearest_count = sum(1 for s in data["substations"] if s.get("is_nearest"))
        assert nearest_count == 1


def test_scorecard_gap_columns(client):
    """11. POST /api/scorecard returns gap_vs_tariff_pct and gap_vs_bpp_pct."""
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    assert resp.status_code == 200
    data = resp.json()
    first = data["scorecard"][0]
    assert "gap_vs_tariff_pct" in first
    assert "gap_vs_bpp_pct" in first


def test_scorecard_action_flag_values(client):
    """12. All action_flag values are valid ActionFlag enum members."""
    from src.model.basic_model import ActionFlag

    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    data = resp.json()
    valid_flags = {f.value for f in ActionFlag}
    for row in data["scorecard"]:
        assert row["action_flag"] in valid_flags, f"Invalid flag: {row['action_flag']}"


def test_scorecard_bpp_mode(client):
    """13. POST /api/scorecard with benchmark_mode='bpp' returns 200 with 25 rows."""
    body = _default_body(client)
    body["benchmark_mode"] = "bpp"
    resp = client.post("/api/scorecard", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["scorecard"]) >= 25  # at least 25 KEKs, plus industrial sites


# ---------------------------------------------------------------------------
# M15: Multi-substation comparison tests
# ---------------------------------------------------------------------------


def test_kek_substations_top3_have_costs(client):
    """14. Top 3 substations have cost breakdown fields."""
    resp = client.get("/api/site/kek-palu/substations?radius_km=50")
    assert resp.status_code == 200
    subs = resp.json()["substations"]
    ranked = [s for s in subs if s.get("rank") is not None]
    assert len(ranked) <= 3

    for s in ranked:
        assert "rank" in s and 1 <= s["rank"] <= 3
        assert "connection_cost_per_kw" in s
        assert "upgrade_cost_per_kw" in s
        assert "transmission_cost_per_kw" in s
        assert "total_grid_capex_per_kw" in s
        assert "lcoe_estimate_usd_mwh" in s
        assert "capacity_assessment" in s
        assert "dist_solar_km" in s


def test_kek_substations_total_equals_sum(client):
    """15. total_grid_capex_per_kw = connection + upgrade + transmission for each ranked sub."""
    resp = client.get("/api/site/kek-palu/substations?radius_km=50")
    subs = resp.json()["substations"]
    ranked = [s for s in subs if s.get("rank") is not None]

    for s in ranked:
        conn = s["connection_cost_per_kw"] or 0
        upgrade = s["upgrade_cost_per_kw"] or 0
        trans = s["transmission_cost_per_kw"] or 0
        total = s["total_grid_capex_per_kw"] or 0
        assert abs(total - (conn + upgrade + trans)) < 1.0, (
            f"Total {total} != conn {conn} + upgrade {upgrade} + trans {trans}"
        )


def test_kek_substations_rank1_is_nearest(client):
    """16. Rank 1 substation is marked as nearest and has shortest distance."""
    resp = client.get("/api/site/kek-palu/substations?radius_km=50")
    subs = resp.json()["substations"]
    ranked = [s for s in subs if s.get("rank") is not None]
    if not ranked:
        return

    rank1 = ranked[0]
    assert rank1["rank"] == 1
    assert rank1["is_nearest"] is True

    # Rank 1 should have shortest dist_km
    for s in ranked[1:]:
        assert s["dist_km"] >= rank1["dist_km"]


def test_kek_substations_unranked_have_nulls(client):
    """17. Substations beyond top 3 have null cost fields."""
    resp = client.get("/api/site/kek-palu/substations?radius_km=50")
    subs = resp.json()["substations"]
    unranked = [s for s in subs if s.get("rank") is None]

    for s in unranked:
        assert s["connection_cost_per_kw"] is None
        assert s["total_grid_capex_per_kw"] is None
        assert s["lcoe_estimate_usd_mwh"] is None


# ---------------------------------------------------------------------------
# No solar resource flag tests
# ---------------------------------------------------------------------------


def test_no_solar_resource_flag_for_zero_capacity(client):
    """18. Sites with buildable_area=0 get no_solar_resource flag, not invest_battery.

    Originally targeted kek-bitung when its 50km regional buildable area was
    zero. After #56 (Kawasan Hutan APL fix) every KEK has non-zero regional
    buildable, so the canary moved to a small industrial site whose 50km
    radius is entirely sea/conservation forest. semen-padang-indarung is on
    Sumatra's west coast next to Bukit Barisan protected forest.
    """
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    data = resp.json()

    site = next((r for r in data["scorecard"] if r["site_id"] == "semen-padang-indarung"), None)
    assert site is not None, "semen-padang-indarung not found in scorecard"
    assert site["action_flag"] == "no_solar_resource", (
        f"Expected no_solar_resource for semen-padang-indarung, got {site['action_flag']}"
    )


def test_normal_keks_not_affected_by_no_solar_flag(client):
    """19. KEKs with positive capacity still get normal flags (not no_solar_resource)."""
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    data = resp.json()

    # Palu has buildable area > 0 — should NOT get no_solar_resource
    palu = next((r for r in data["scorecard"] if r["site_id"] == "kek-palu"), None)
    assert palu is not None, "kek-palu not found in scorecard"
    assert palu["action_flag"] != "no_solar_resource"
