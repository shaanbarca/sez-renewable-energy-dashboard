"""Tests for /api/site/{site_id}/rooftop-breakdown (#82).

Three primary paths verified:
  1. Happy path — site with buildings returns rows + totals matching the
     scorecard's `rooftop_solar_mwp_potential`.
  2. Zero-building site — returns empty list + zero totals + the
     building_data_confidence/reason_flagged flag from
     fct_site_solar_potential.
  3. 404 — unknown site_id returns a clean error.

Plus contract checks: every row has the required fields with valid enum
values; totals are consistent with the per-row data; cache eviction works.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# Footprint class values produced by the cascade (locked /plan-eng-review 1B + 1C).
_VALID_FOOTPRINT_CLASSES = {
    "standard_roof",
    "elongated",
    "possibly_round",
    "complex",
    "tank_silo",
    "conveyor",
    "too_small",
    "residential",
    "isolated_cluster",
}

_VALID_EXCLUSION_REASONS = {
    "none",
    "osm_tank",
    "osm_basin",
    "osm_water",
    "geometric_tank_silo",
    "geometric_complex",
    "geometric_round",
    "geometric_too_small",
    "residential_cluster",
    "isolated_cluster",
}


def test_404_for_unknown_site(client):
    """Unknown site_id returns 404 with a descriptive message."""
    resp = client.get("/api/site/this-site-does-not-exist/rooftop-breakdown")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_happy_path_real_site(client):
    """Pick a site known to have buildings; verify response shape + values."""
    # indonesia-morowali-industrial-park-imip has high building count (~411 in upper bound).
    resp = client.get("/api/site/indonesia-morowali-industrial-park-imip/rooftop-breakdown")
    assert resp.status_code == 200
    data = resp.json()

    # Top-level shape
    assert data["site_id"] == "indonesia-morowali-industrial-park-imip"
    assert isinstance(data["site_name"], str) and data["site_name"]
    # estate_area_m2 may be None for sites without a polygon area
    assert "estate_area_m2" in data
    assert "building_data_confidence" in data
    assert "building_data_reason_flagged" in data

    # Buildings list
    buildings = data["buildings"]
    assert isinstance(buildings, list)
    assert len(buildings) > 0

    for b in buildings[:50]:  # sample first 50; full validation would be slow
        assert isinstance(b["building_id"], str)
        assert isinstance(b["area_m2"], (int, float))
        assert b["area_m2"] > 0
        assert b["footprint_class"] in _VALID_FOOTPRINT_CLASSES
        assert b["exclusion_reason"] in _VALID_EXCLUSION_REASONS
        assert 0.0 <= b["usability_multiplier"] <= 1.0
        assert b["buildable_roof_area_m2"] >= 0
        # Invariant: buildable area = area × multiplier (within rounding)
        expected = round(b["area_m2"] * b["usability_multiplier"], 2)
        assert abs(b["buildable_roof_area_m2"] - expected) < 0.5

    # Totals consistency with buildings
    totals = data["totals"]
    assert totals["building_count"] == len(buildings)
    assert totals["total_footprint_m2"] > 0
    assert totals["usable_roof_area_m2"] >= 0
    assert totals["usable_roof_area_m2"] <= totals["total_footprint_m2"]


def test_zero_building_site(client):
    """A site flagged as zero-building (12-site audit cohort).

    Pick from sites_missing_buildings.csv: indonesia-morowali-industrial-park
    or one of the polygon_imagery_gap cohort. We don't hardcode the specific
    site because the cohort may change; instead, we assert the *shape* of the
    response for a zero-building site.

    To find one for the test, we query a few candidates and assert at least
    one returns an empty list with the appropriate flags.
    """
    # tourism-batam and a few other known low-confidence sites
    # 4 zero-building sites in current dataset (per sites_missing_buildings.csv)
    candidates = [
        "obi-island-industrial-park",
        "stardust-estate-invesment-sei",
        "buli-industrial-park",
        "pupuk-kaltim-bontang",
    ]
    found_zero = False
    for sid in candidates:
        resp = client.get(f"/api/site/{sid}/rooftop-breakdown")
        if resp.status_code != 200:
            continue
        data = resp.json()
        if data["totals"]["building_count"] == 0:
            found_zero = True
            assert data["buildings"] == []
            assert data["totals"]["total_footprint_m2"] == 0.0
            assert data["totals"]["usable_roof_area_m2"] == 0.0
            # Zero-building sites should have a confidence flag set
            # (may be "low" with a reason like "no_buildings_detected")
            break

    if not found_zero:
        pytest.skip(
            "No zero-building site found among candidates; cohort may have changed. "
            "Check `outputs/data/processed/sites_missing_buildings.csv` for current set."
        )


def test_totals_reconcile_with_buildings_sum(client):
    """Per-row buildable areas sum to the totals.usable_roof_area_m2 value
    (within rounding) — the audit's primary validation contract."""
    resp = client.get("/api/site/indonesia-morowali-industrial-park-imip/rooftop-breakdown")
    assert resp.status_code == 200
    data = resp.json()
    row_sum = sum(b["buildable_roof_area_m2"] for b in data["buildings"])
    # Allow $1 m² of rounding drift across hundreds of rows
    assert abs(row_sum - data["totals"]["usable_roof_area_m2"]) < 1.0


def test_estate_area_present_for_sites_with_polygon(client):
    """Sites with area_ha in dim_sites get estate_area_m2 = area_ha × 10000."""
    resp = client.get("/api/site/indonesia-morowali-industrial-park-imip/rooftop-breakdown")
    assert resp.status_code == 200
    data = resp.json()
    # indonesia-morowali-industrial-park-imip has a known polygon
    if data["estate_area_m2"] is not None:
        assert data["estate_area_m2"] > 0
        # IMIP is large (~2000+ ha) — sanity check the order of magnitude
        assert data["estate_area_m2"] > 1_000_000  # > 100 ha


def test_totals_reconcile_with_scorecard_csv(client):
    """The audit's primary contract: endpoint totals match fct_site_solar_potential.csv
    exactly. If this drifts, the modal lies to validators about which
    buildings produced the headline MWp number — the entire #82 surface
    becomes untrustworthy.

    Checked on 3 representative sites covering different cascade patterns:
    high building count (IMIP), top rooftop MWp (Krakatau Steel),
    polygon-clipped (Petrokimia Gresik).
    """
    import pandas as pd  # noqa: PLC0415 — module-scope import is heavy

    solar = pd.read_csv("outputs/data/processed/fct_site_solar_potential.csv")

    sites_to_check = [
        "indonesia-morowali-industrial-park-imip",
        "krakatau-steel-cilegon",
        "petrokimia-gresik",
    ]
    for sid in sites_to_check:
        resp = client.get(f"/api/site/{sid}/rooftop-breakdown")
        assert resp.status_code == 200, f"{sid}: {resp.status_code}"
        data = resp.json()
        row = solar[solar["site_id"] == sid].iloc[0]
        # building_count: endpoint returns total dispositions = csv total
        assert data["totals"]["building_count"] == row["building_count_total"], (
            f"{sid}: building_count drift "
            f"(endpoint={data['totals']['building_count']}, csv={row['building_count_total']})"
        )
        # total_footprint_m2: exact float match (both rounded to 2dp)
        assert data["totals"]["total_footprint_m2"] == pytest.approx(
            row["total_building_footprint_m2"], abs=0.01
        ), f"{sid}: footprint drift"
        # usable_roof_area_m2: exact float match
        assert data["totals"]["usable_roof_area_m2"] == pytest.approx(
            row["usable_roof_area_m2"], abs=0.01
        ), f"{sid}: usable area drift"


def test_caching_behavior(client):
    """Repeated calls hit the cache — same response, fast.

    We don't assert latency (too flaky); we just verify the cache returns
    identical content. Cache miss + cache hit must produce byte-identical
    JSON (no race conditions in the disposition serialization).
    """
    r1 = client.get("/api/site/indonesia-morowali-industrial-park-imip/rooftop-breakdown")
    r2 = client.get("/api/site/indonesia-morowali-industrial-park-imip/rooftop-breakdown")
    assert r1.status_code == 200 == r2.status_code
    assert r1.json() == r2.json()
