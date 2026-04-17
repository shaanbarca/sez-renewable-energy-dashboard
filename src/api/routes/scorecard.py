"""Scorecard and defaults endpoints."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.dash.constants import (
    TIER1_SLIDERS,
    TIER2_SLIDERS,
    TIER3_SLIDERS,
    WACC_DEFAULT,
    WACC_DESCRIPTION,
    WACC_MARKS,
    WACC_MAX,
    WACC_MIN,
    WACC_STEP,
)
from src.dash.logic import (
    UserAssumptions,
    UserThresholds,
    compute_scorecard_live,
    get_default_assumptions,
    get_default_thresholds,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models for request validation
# ---------------------------------------------------------------------------


class AssumptionsInput(BaseModel):
    capex_usd_per_kw: float = Field(ge=0, description="CAPEX in USD/kW")
    lifetime_yr: int = Field(gt=0, le=50)
    wacc_pct: float = Field(gt=0, le=100)
    fom_usd_per_kw_yr: float = Field(ge=0)
    connection_cost_per_kw_km: float = Field(ge=0)
    grid_connection_fixed_per_kw: float = Field(ge=0)
    bess_capex_usd_per_kwh: float = Field(gt=0)
    bess_sizing_hours_override: float | None = Field(
        default=None, ge=1, le=24, description="BESS sizing override (hours). None = auto."
    )
    land_cost_usd_per_kw: float = Field(ge=0)
    substation_utilization_pct: float = Field(ge=0.0, le=1.0, default=0.65)
    idr_usd_rate: float = Field(gt=0)
    grid_benchmark_usd_mwh: float = Field(ge=0)
    grant_funded_transmission: bool = Field(
        default=False, description="DFI grant scenario: zero out all grid connection costs."
    )
    target_capacity_mwp: float | None = Field(
        default=None, ge=1, description="Target build size (MWp). None = use max buildable."
    )
    hybrid_solar_share: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Hybrid solar/wind mix ratio (0-1). None = auto-optimize per KEK.",
    )
    cbam_certificate_price_eur: float = Field(
        default=80.0,
        ge=0,
        le=200,
        description="EU ETS carbon certificate price (EUR/tCO2). Default 80.",
    )
    cbam_eur_usd_rate: float = Field(
        default=1.10,
        ge=0.5,
        le=2.0,
        description="EUR/USD exchange rate for CBAM cost conversion. Default 1.10.",
    )


class ThresholdsInput(BaseModel):
    pvout_threshold: float = Field(ge=0)
    plan_late_threshold: float = Field(ge=0, le=1)
    geas_threshold: float = Field(ge=0, le=1)
    resilience_gap_pct: float = Field(ge=0)
    min_viable_mwp: float = Field(ge=0)
    reliability_threshold: float = Field(ge=0, le=1)


class ScorecardRequest(BaseModel):
    assumptions: AssumptionsInput
    thresholds: ThresholdsInput
    benchmark_mode: Literal["bpp", "tariff"] = "tariff"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_nan(value):
    """Convert NaN/Inf to None for JSON serialization (recursive for nested dicts)."""
    if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: _clean_nan(v) for k, v in value.items()}
    return value


def _df_to_clean_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts with NaN replaced by None."""
    records = df.to_dict(orient="records")
    return [{k: _clean_nan(v) for k, v in row.items()} for row in records]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/defaults")
def get_defaults():
    """Return default assumptions, thresholds, and slider configurations."""
    assumptions = get_default_assumptions()
    thresholds = get_default_thresholds()

    return {
        "assumptions": assumptions.to_dict(),
        "thresholds": thresholds.to_dict(),
        "slider_configs": {
            "tier1": TIER1_SLIDERS,
            "tier2": TIER2_SLIDERS,
            "tier3": TIER3_SLIDERS,
            "wacc": {
                "min": WACC_MIN,
                "max": WACC_MAX,
                "step": WACC_STEP,
                "default": WACC_DEFAULT,
                "marks": WACC_MARKS,
                "description": WACC_DESCRIPTION,
            },
        },
    }


@router.post("/scorecard")
def post_scorecard(req: ScorecardRequest):
    """Recompute LCOE + action flags for all 25 KEKs."""
    from src.api.main import (  # noqa: PLC0415 — avoid circular import (main ← routes)
        resource_df,
        ruptl_metrics_df,
        tables,
        wind_tech,
    )

    assumptions = UserAssumptions.from_dict(req.assumptions.model_dump())
    thresholds = UserThresholds.from_dict(req.thresholds.model_dump())

    # Build grid_cost_by_region for BPP mode
    grid_cost_by_region = None
    if req.benchmark_mode == "bpp":
        grid_df = tables["fct_grid_cost_proxy"]
        grid_cost_by_region = grid_df.groupby("grid_region_id")["bpp_usd_mwh"].first().to_dict()

    scorecard_df = compute_scorecard_live(
        resource_df=resource_df,
        assumptions=assumptions,
        thresholds=thresholds,
        ruptl_metrics_df=ruptl_metrics_df,
        demand_df=tables["fct_site_demand"],
        grid_df=tables["fct_grid_cost_proxy"],
        grid_cost_by_region=grid_cost_by_region,
        wind_tech=wind_tech,
    )

    # Merge dim_sites columns
    dim_sites = tables["dim_sites"]
    merge_cols_sites = ["site_id"]
    for col in [
        "site_name",
        "province",
        "latitude",
        "longitude",
        "grid_region_id",
        "zone_classification",
        "category",
        "area_ha",
        "developer",
        "legal_basis",
        "site_type",
        "sector",
        "primary_product",
        "capacity_annual",
        "capacity_annual_tonnes",
        "technology",
        "parent_company",
        "cluster_members",
    ]:
        if col in dim_sites.columns and col not in scorecard_df.columns:
            merge_cols_sites.append(col)
    if len(merge_cols_sites) > 1:
        scorecard_df = scorecard_df.merge(dim_sites[merge_cols_sites], on="site_id", how="left")

    # Merge resource/grid columns (wind columns now come from compute_scorecard_live)
    for source_name, source_cols in [
        (
            "fct_site_resource",
            [
                "buildable_area_ha",
                "max_captive_capacity_mwp",
                "pvout_centroid",
                "pvout_best_50km",
            ],
        ),
        ("fct_grid_cost_proxy", ["dashboard_rate_usd_mwh", "bpp_usd_mwh"]),
    ]:
        source_df = tables.get(source_name)
        if source_df is None:
            continue
        available = [
            c for c in source_cols if c in source_df.columns and c not in scorecard_df.columns
        ]
        if available:
            # Need a join key
            if "site_id" in source_df.columns:
                scorecard_df = scorecard_df.merge(
                    source_df[["site_id"] + available].drop_duplicates("site_id"),
                    on="site_id",
                    how="left",
                )
            elif "grid_region_id" in source_df.columns and "grid_region_id" in scorecard_df.columns:
                scorecard_df = scorecard_df.merge(
                    source_df[["grid_region_id"] + available].drop_duplicates("grid_region_id"),
                    on="grid_region_id",
                    how="left",
                )

    # Rename columns to match frontend type names
    rename_map = {
        "pvout_centroid": "pvout_centroid_kwh_kwp_yr",
        "pvout_best_50km": "pvout_best_50km_kwh_kwp_yr",
    }
    scorecard_df = scorecard_df.rename(
        columns={k: v for k, v in rename_map.items() if k in scorecard_df.columns}
    )

    return {"scorecard": _df_to_clean_records(scorecard_df)}
