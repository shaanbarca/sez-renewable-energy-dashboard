# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
"""V3.7 substation-anchored solar picker — unit tests.

Covers _pick_anchored_patch, _search_radius_km, and the enrich_anchor_and_regime
live enricher. Uses synthetic numpy/rasterio fixtures so tests don't depend on
the ESDM GeoTIFF or the full pipeline.
"""

from __future__ import annotations

import numpy as np
import pytest
import rasterio.transform

from src.pipeline.assumptions import (
    KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM,
    KEK_TO_SUBSTATION_THRESHOLD_KM,
    MEANINGFUL_SHARE_PCT,
    PERPRES_112_CEILING_USD_MWH,
)
from src.pipeline.build_fct_site_resource import (
    _pick_anchored_patch,
    _search_radius_km,
)
from src.pipeline.demand_intensity import required_solar_mwp

# Batam-shaped fixture: small equatorial island, 19.8 GWh/yr (Batam Aero Technic)
BATAM_LAT = 1.12
BATAM_LON = 104.10
BATAM_DEMAND_MWH = 19_800.0
BATAM_CF = 0.18  # ~1600 kWh/kWp/yr / 8760

# Tropical pixel grid: 0.01 deg resolution ≈ 1.1 km pixels. 40×40 window spans
# ~44 km each side — enough to host candidate substations up to ~15 km out.
GRID_N = 40
PIX_DEG = 0.01
# Top-left of the window is NW of the site centroid.
WIN_WEST = BATAM_LON - (GRID_N / 2) * PIX_DEG
WIN_NORTH = BATAM_LAT + (GRID_N / 2) * PIX_DEG
WIN_TRANSFORM = rasterio.transform.from_origin(WIN_WEST, WIN_NORTH, PIX_DEG, PIX_DEG)

# One pixel ≈ 1.1 km × 1.1 km ≈ 121 ha at the equator.
PIX_HA = 121.0  # used for the picker's pix_ha argument

TECH_PARAMS = {
    "capex_usd_per_kw": 1000.0,
    "fixed_om_usd_per_kw_yr": 20.0,
    "wacc": 0.10,
    "lifetime_yr": 25,
}

# PVOUT patch: 5.2 kWh/kWp/day uniform → annual 1898, cf 0.217.
# This is tropical Indonesia typical.
PVOUT_UNIFORM_DAILY = 5.2


def _buildable_everywhere() -> np.ndarray:
    return np.ones((GRID_N, GRID_N), dtype=bool)


def _pvout_uniform() -> np.ndarray:
    return np.full((GRID_N, GRID_N), PVOUT_UNIFORM_DAILY, dtype=float)


class TestRequiredSolarMwp:
    def test_happy_path(self):
        # 19.8 GWh → 12.5 MWp at cf=0.18
        mwp = required_solar_mwp(19_800.0, 0.18)
        assert 12.0 < mwp < 13.0

    def test_zero_demand(self):
        assert required_solar_mwp(0.0, 0.18) == 0.0

    def test_zero_cf(self):
        assert required_solar_mwp(1000.0, 0.0) == 0.0


class TestSearchRadius:
    def test_jamali_tight(self):
        assert _search_radius_km("JAVA_BALI") == KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM["JAMALI"]

    def test_sumatra_medium(self):
        assert _search_radius_km("SUMATERA") == KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM["SUMATRA"]

    def test_papua_wide(self):
        assert _search_radius_km("PAPUA") == KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM["MALUKU_PAPUA"]

    def test_regpln_key(self):
        # Substation-level regpln values should also map to tiers.
        assert _search_radius_km("Jawa-Bali") == KEK_TO_SUBSTATION_RADIUS_BY_REGION_KM["JAMALI"]

    def test_unknown_region_fallback(self):
        assert _search_radius_km("MADE_UP") == KEK_TO_SUBSTATION_THRESHOLD_KM

    def test_none_region_fallback(self):
        assert _search_radius_km(None) == KEK_TO_SUBSTATION_THRESHOLD_KM


class TestAnchoredPickerHappyPath:
    """Batam-shaped site: small demand, close substation → anchor wins."""

    def test_returns_anchored_patch_with_near_substation(self):
        # One substation 4 km NE of the site centroid — well within 15 km JAMALI radius.
        substations = [
            {
                "name": "GI 150 kV Nongsa 1",
                "lat": BATAM_LAT + 0.03,
                "lon": BATAM_LON + 0.03,
            }
        ]
        result = _pick_anchored_patch(
            filtered_mask=_buildable_everywhere(),
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=BATAM_DEMAND_MWH,
            cf_centroid=BATAM_CF,
            substations=substations,
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is not None
        assert result["anchor_name"] == "GI 150 kV Nongsa 1"
        # Patch should easily clear meaningful_mwp = 12.5 × 0.30 = 3.75 MWp
        assert (
            result["patch_capacity_mwp"]
            > required_solar_mwp(BATAM_DEMAND_MWH, BATAM_CF) * MEANINGFUL_SHARE_PCT
        )
        # Supply share capped at 1.0 because patch covers full demand
        assert result["supply_share_pct"] == 1.0
        # Delivered share capped at 1.0 as well
        assert result["delivered_share_pct"] == 1.0

    def test_picker_selects_lowest_lcoe_not_nearest(self):
        """Two substations: the closer one gets picked because LCOE proxy is lowest.

        LCOE proxy = lcoe_solar(cf) + amortised connection cost(dist). PVOUT is
        uniform here, so lower connection cost = lower LCOE.
        """
        substations = [
            {  # 4 km away — should win
                "name": "GI 150 kV Close",
                "lat": BATAM_LAT + 0.03,
                "lon": BATAM_LON + 0.03,
            },
            {  # 12 km away — further, worse LCOE
                "name": "GI 150 kV Far",
                "lat": BATAM_LAT + 0.10,
                "lon": BATAM_LON + 0.05,
            },
        ]
        result = _pick_anchored_patch(
            filtered_mask=_buildable_everywhere(),
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=BATAM_DEMAND_MWH,
            cf_centroid=BATAM_CF,
            substations=substations,
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is not None
        assert result["anchor_name"] == "GI 150 kV Close"
        assert result["site_to_sub_km"] < 6.0


class TestAnchoredPickerFallback:
    """Galang-Batang-shaped: no candidate meets meaningful_mwp → returns None."""

    def test_no_substations_in_range(self):
        # All substations >>15 km from site
        substations = [
            {"name": "Far1", "lat": BATAM_LAT + 0.5, "lon": BATAM_LON + 0.5},
            {"name": "Far2", "lat": BATAM_LAT - 0.5, "lon": BATAM_LON - 0.5},
        ]
        result = _pick_anchored_patch(
            filtered_mask=_buildable_everywhere(),
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=BATAM_DEMAND_MWH,
            cf_centroid=BATAM_CF,
            substations=substations,
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is None

    def test_demand_too_large_for_buildable_patch(self):
        # Galang-Batang-scale demand (5,000 GWh/yr) needs ~3200 MWp → ~4800 ha buildable.
        # Our 40×40 grid at 121 ha/pixel = 193k ha total; within a 10 km radius around
        # one substation we get maybe ~300 pixels × 121 ha ≈ 36k ha. Meaningful_mwp =
        # 3200 × 0.30 = 960 MWp → 1440 ha. That's coverable in this synthetic grid,
        # so we need to starve the buildable mask to test the reject branch.
        starved_mask = np.zeros((GRID_N, GRID_N), dtype=bool)
        # Only a small 3×3 buildable patch (~1090 ha ≈ 7 MWp) — far below meaningful_mwp
        starved_mask[10:13, 10:13] = True
        substations = [{"name": "Nearby", "lat": BATAM_LAT + 0.02, "lon": BATAM_LON + 0.02}]
        result = _pick_anchored_patch(
            filtered_mask=starved_mask,
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=5_000_000.0,  # 5,000 GWh = Galang-Batang scale
            cf_centroid=BATAM_CF,
            substations=substations,
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is None

    def test_zero_demand_returns_none(self):
        result = _pick_anchored_patch(
            filtered_mask=_buildable_everywhere(),
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=0.0,
            cf_centroid=BATAM_CF,
            substations=[{"name": "X", "lat": BATAM_LAT, "lon": BATAM_LON}],
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is None

    def test_empty_substation_list_returns_none(self):
        result = _pick_anchored_patch(
            filtered_mask=_buildable_everywhere(),
            pvout_patch=_pvout_uniform(),
            win_transform=WIN_TRANSFORM,
            site_lat=BATAM_LAT,
            site_lon=BATAM_LON,
            site_demand_mwh=BATAM_DEMAND_MWH,
            cf_centroid=BATAM_CF,
            substations=[],
            grid_region_id="JAVA_BALI",
            pix_ha=PIX_HA,
            tech_params=TECH_PARAMS,
        )
        assert result is None


class TestRegimeAndPerpresCeiling:
    """enrich_anchor_and_regime: solar_regime classification + Perpres 112 ceiling."""

    def _make_ctx(self, kek: dict):
        """Minimal SiteContext stub — only .kek and .gc_row are read."""
        from types import SimpleNamespace

        return SimpleNamespace(kek=kek, gc_row=None)

    def test_captive_regime_for_nearby_kek(self):
        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx(
            {
                "site_type": "kek",
                "dist_solar_to_nearest_substation_km": 3.5,  # ≤ 10 km
            }
        )
        out = enrich_anchor_and_regime(ctx, {"lcoe_grid_connected_usd_mwh": 85.0})
        assert out["solar_regime"] == "co_located_captive"
        # Captive is not subject to Perpres ceiling — pass through unchanged
        assert out["lcoe_grid_connected_capped_usd_mwh"] == 85.0

    def test_ipp_regime_when_solar_far(self):
        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx(
            {
                "site_type": "kek",
                "dist_solar_to_nearest_substation_km": 15.0,  # > 10 km
            }
        )
        out = enrich_anchor_and_regime(ctx, {"lcoe_grid_connected_usd_mwh": 85.0})
        assert out["solar_regime"] == "grid_connected_ipp"
        # IPP hits the Perpres ceiling of $75/MWh
        assert out["lcoe_grid_connected_capped_usd_mwh"] == PERPRES_112_CEILING_USD_MWH

    def test_ipp_regime_below_ceiling_passes_through(self):
        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx(
            {
                "site_type": "kek",
                "dist_solar_to_nearest_substation_km": 15.0,
            }
        )
        out = enrich_anchor_and_regime(ctx, {"lcoe_grid_connected_usd_mwh": 60.0})
        assert out["solar_regime"] == "grid_connected_ipp"
        # 60 < 75 → passes through
        assert out["lcoe_grid_connected_capped_usd_mwh"] == 60.0

    def test_standalone_site_is_ipp(self):
        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx(
            {
                "site_type": "standalone",
                "dist_solar_to_nearest_substation_km": 2.0,  # close but not KEK/KI
            }
        )
        out = enrich_anchor_and_regime(ctx, {"lcoe_grid_connected_usd_mwh": 90.0})
        # Only kek/ki with close substation get captive regime
        assert out["solar_regime"] == "grid_connected_ipp"

    def test_unclear_regime_when_site_type_missing(self):
        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx({"dist_solar_to_nearest_substation_km": 3.0})
        out = enrich_anchor_and_regime(ctx, {"lcoe_grid_connected_usd_mwh": 90.0})
        assert out["solar_regime"] == "unclear"
        # Unclear regime — pass through, don't apply the ceiling
        assert out["lcoe_grid_connected_capped_usd_mwh"] == 90.0

    def test_missing_gc_lcoe_yields_nan(self):
        import pandas as pd

        from src.dash.logic.scorecard import enrich_anchor_and_regime

        ctx = self._make_ctx(
            {
                "site_type": "kek",
                "dist_solar_to_nearest_substation_km": 15.0,
            }
        )
        out = enrich_anchor_and_regime(ctx, {})
        assert out["solar_regime"] == "grid_connected_ipp"
        # _round(None) → NaN by design; the JSON layer serializes NaN as null.
        assert pd.isna(out["lcoe_grid_connected_capped_usd_mwh"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
