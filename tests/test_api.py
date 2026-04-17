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
    """18. KEKs with buildable_area=0 get no_solar_resource flag, not invest_battery."""
    body = _default_body(client)
    resp = client.post("/api/scorecard", json=body)
    data = resp.json()

    # Bitung has 0 buildable area — should get no_solar_resource
    bitung = next((r for r in data["scorecard"] if r["site_id"] == "kek-bitung"), None)
    assert bitung is not None, "kek-bitung not found in scorecard"
    assert bitung["action_flag"] == "no_solar_resource", (
        f"Expected no_solar_resource for Bitung, got {bitung['action_flag']}"
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
