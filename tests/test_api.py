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
    assert len(data["scorecard"]) == 25
    # Check required fields present
    first = data["scorecard"][0]
    for key in ["kek_id", "action_flag", "lcoe_mid_usd_mwh"]:
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
    """6. GET /api/kek/{valid_id}/polygon returns feature + bbox + center."""
    resp = client.get("/api/kek/industropolis-batang/polygon")
    assert resp.status_code == 200
    data = resp.json()
    assert "feature" in data
    assert "bbox" in data
    assert "center" in data
    assert "min_lon" in data["bbox"]
    assert "lat" in data["center"]


def test_kek_polygon_invalid(client):
    """7. GET /api/kek/invalid-id/polygon returns 404."""
    resp = client.get("/api/kek/invalid-id-xyz/polygon")
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
    """10. GET /api/kek/{valid_id}/substations returns substations with dist_km."""
    resp = client.get("/api/kek/industropolis-batang/substations?radius_km=50")
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
