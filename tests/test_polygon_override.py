"""Tests for the per-request polygon override resolver (#26).

The resolver patches resource_df row fields for sites that have an active
polygon override. These tests pin:

1. The happy path: a valid override updates the 6 expected fields.
2. Validation: out-of-bounds, NaN, missing-centroid, unknown-site all raise 422.
3. The scope invariant: within_boundary fields stay untouched.
4. Multi-site overrides apply independently.
5. The substation-distance helper handles empty and finite-result cases.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest
from fastapi import HTTPException

from src.dash.logic.polygon_override import (
    POLYGON_OVERRIDE_FIELDS,
    _nearest_substation_km,
    apply_polygon_overrides,
)


def _make_resource_df() -> pd.DataFrame:
    """Minimal resource_df with the columns the resolver touches + scope-invariant
    within_boundary columns we assert remain unchanged."""
    return pd.DataFrame(
        {
            "site_id": ["kek-a", "kek-b", "kek-c"],
            # Fields the resolver patches
            "pvout_buildable_best_50km": [1500.0, 1500.0, 1500.0],
            "pvout_best_50km": [1500.0, 1500.0, 1500.0],
            "best_solar_site_lat": [-3.0, -3.0, -3.0],
            "best_solar_site_lon": [120.0, 120.0, 120.0],
            "project_scale_solar_mwp": [100.0, 100.0, 100.0],
            "dist_solar_to_nearest_substation_km": [5.0, 5.0, 5.0],
            # Scope invariant — must NOT be touched
            "pvout_within_boundary": [1450.0, 1450.0, 1450.0],
            "pvout_centroid": [1480.0, 1480.0, 1480.0],
            "within_boundary_area_ha": [200.0, 200.0, 200.0],
        }
    )


def _make_polygons(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _valid_polygon(
    *, pvout: float = 1700.0, capacity: float = 5000.0, lat: float = -3.5, lon: float = 121.0
) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "feature_index": 0,
            "avg_pvout_annual": pvout,
            "capacity_mwp": capacity,
            "centroid_lat": lat,
            "centroid_lon": lon,
            "area_ha": capacity * 1.5,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[120, -3], [122, -3], [122, -4], [120, -3]]],
        },
    }


_SUBS = [
    {"lat": -3.5, "lon": 121.0, "name": "Sub A"},  # 0 km from polygon centroid
    {"lat": -4.0, "lon": 122.0, "name": "Sub B"},  # ~135 km away
]


# ── Happy path ─────────────────────────────────────────────────────────────


def test_no_overrides_returns_df_untouched():
    df = _make_resource_df()
    original = df.copy()
    out = apply_polygon_overrides(df, None, _make_polygons([]), _SUBS)
    pd.testing.assert_frame_equal(out, original)


def test_empty_overrides_dict_returns_df_untouched():
    df = _make_resource_df()
    original = df.copy()
    out = apply_polygon_overrides(df, {}, _make_polygons([]), _SUBS)
    pd.testing.assert_frame_equal(out, original)


def test_valid_override_patches_expected_fields():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon(pvout=1800.0, capacity=600.0, lat=-3.5, lon=121.0)])
    apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)
    row = df[df["site_id"] == "kek-a"].iloc[0]
    assert row["pvout_buildable_best_50km"] == 1800.0
    assert row["pvout_best_50km"] == 1800.0
    assert row["best_solar_site_lat"] == -3.5
    assert row["best_solar_site_lon"] == 121.0
    assert row["project_scale_solar_mwp"] == 600.0
    # Polygon centroid coincides with Sub A → distance ~0
    assert row["dist_solar_to_nearest_substation_km"] == pytest.approx(0.0, abs=0.01)


def test_within_boundary_fields_untouched_scope_invariant():
    """#26 explicitly scopes the override to grid_connected_solar. within_boundary
    captive LCOE uses the KEK polygon's own PVOUT and must not be patched."""
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon(pvout=1800.0)])
    apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)
    row = df[df["site_id"] == "kek-a"].iloc[0]
    # These columns are the captive scenario inputs — must equal the originals
    assert row["pvout_within_boundary"] == 1450.0
    assert row["pvout_centroid"] == 1480.0
    assert row["within_boundary_area_ha"] == 200.0


def test_multi_site_overrides_apply_independently():
    df = _make_resource_df()
    polygons = _make_polygons(
        [
            _valid_polygon(pvout=1700.0, capacity=400.0, lat=-3.5, lon=121.0),
            _valid_polygon(pvout=1900.0, capacity=800.0, lat=-2.0, lon=119.0),
        ]
    )
    apply_polygon_overrides(df, {"kek-a": 0, "kek-c": 1}, polygons, _SUBS)
    a = df[df["site_id"] == "kek-a"].iloc[0]
    b = df[df["site_id"] == "kek-b"].iloc[0]
    c = df[df["site_id"] == "kek-c"].iloc[0]
    assert a["pvout_buildable_best_50km"] == 1700.0
    assert b["pvout_buildable_best_50km"] == 1500.0  # untouched
    assert c["pvout_buildable_best_50km"] == 1900.0


def test_null_value_in_override_is_noop():
    """The frontend may transiently send {site_id: None} during a reset — the
    resolver should treat None as 'no override for this site' rather than 422."""
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon()])
    apply_polygon_overrides(df, {"kek-a": None}, polygons, _SUBS)  # type: ignore[dict-item]
    assert df[df["site_id"] == "kek-a"].iloc[0]["pvout_buildable_best_50km"] == 1500.0


# ── Validation: 422 on bad inputs ─────────────────────────────────────────


def test_out_of_bounds_feature_index_raises_422():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon()])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": 99}, polygons, _SUBS)
    assert exc.value.status_code == 422
    assert "out of bounds" in str(exc.value.detail)


def test_negative_feature_index_raises_422():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon()])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": -1}, polygons, _SUBS)
    assert exc.value.status_code == 422


def test_nan_avg_pvout_raises_422():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon(pvout=float("nan"))])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)
    assert exc.value.status_code == 422
    assert "avg_pvout_annual" in str(exc.value.detail)


def test_zero_capacity_raises_422():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon(capacity=0.0)])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)
    assert exc.value.status_code == 422
    assert "capacity_mwp" in str(exc.value.detail)


def test_missing_centroid_raises_422():
    df = _make_resource_df()
    bad = _valid_polygon()
    bad["properties"].pop("centroid_lat")
    polygons = _make_polygons([bad])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)
    assert exc.value.status_code == 422
    assert "centroid" in str(exc.value.detail)


def test_unknown_site_id_raises_422():
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon()])
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-zzz": 0}, polygons, _SUBS)
    assert exc.value.status_code == 422
    assert "kek-zzz" in str(exc.value.detail)


def test_polygons_layer_not_loaded_raises_422():
    df = _make_resource_df()
    with pytest.raises(HTTPException) as exc:
        apply_polygon_overrides(df, {"kek-a": 0}, None, _SUBS)
    assert exc.value.status_code == 422
    assert "not loaded" in str(exc.value.detail)


# ── Field-set constant: protects against drift ────────────────────────────


def test_override_fields_constant_matches_what_resolver_writes():
    """Smoke check that POLYGON_OVERRIDE_FIELDS is the authoritative list.
    If the resolver writes a field not in the constant, downstream code that
    iterates over the constant for typing / docs / display drifts silently."""
    df = _make_resource_df()
    polygons = _make_polygons([_valid_polygon()])
    snapshot = df.copy()
    apply_polygon_overrides(df, {"kek-a": 0}, polygons, _SUBS)

    changed_cols = {col for col in df.columns if not df[col].equals(snapshot[col])}
    assert changed_cols == set(POLYGON_OVERRIDE_FIELDS), (
        f"Resolver mutated columns {changed_cols} but POLYGON_OVERRIDE_FIELDS lists "
        f"{set(POLYGON_OVERRIDE_FIELDS)}. Keep these in sync."
    )


# ── Distance helper ───────────────────────────────────────────────────────


def test_nearest_substation_returns_zero_for_coincident_point():
    assert _nearest_substation_km(-3.5, 121.0, _SUBS) == pytest.approx(0.0, abs=0.001)


def test_nearest_substation_returns_inf_for_empty_list():
    assert math.isinf(_nearest_substation_km(0.0, 0.0, []))


def test_nearest_substation_returns_inf_for_none():
    assert math.isinf(_nearest_substation_km(0.0, 0.0, None))
