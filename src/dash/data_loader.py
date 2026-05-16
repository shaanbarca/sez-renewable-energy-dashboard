# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Data loading and validation for the dashboard.

Loads precomputed CSVs from the pipeline output directory, validates required
columns, and prepares DataFrames for live computation via logic.py.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from src.pipeline.build_fct_transmission_link_ruptl_signal import region_worst_status_map

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

# Required CSV files and their minimum expected columns
_REQUIRED_FILES = {
    "fct_site_scorecard": ["site_id", "site_name", "action_flag", "lcoe_mid_usd_mwh"],
    "fct_site_resource": ["site_id", "pvout_centroid", "pvout_best_50km"],
    "fct_lcoe": ["site_id", "scenario", "lcoe_usd_mwh"],
    "fct_substation_proximity": ["site_id", "dist_to_nearest_substation_km"],
    "fct_ruptl_pipeline": ["grid_region_id", "year"],
    "fct_grid_cost_proxy": ["grid_region_id", "dashboard_rate_usd_mwh"],
    "fct_site_demand": ["site_id", "demand_mwh"],
    "dim_sites": ["site_id", "site_name", "latitude", "longitude"],
}

# Optional CSV files — loaded if present, silently skipped otherwise.
# Used for v4.x feature additions where pipeline output is not always
# regenerated (e.g. v4.1 rooftop solar — fct_site_solar_potential.csv
# is generated only after running build_fct_site_solar_potential).
_OPTIONAL_FILES = {
    "fct_site_solar_potential": ["site_id", "rooftop_solar_mwp_potential"],
}


class DataLoadError(Exception):
    """Raised when required data files are missing or invalid."""


def load_all_data(data_dir: Path = PROCESSED) -> dict[str, pd.DataFrame]:
    """Load all pipeline CSVs and validate required columns.

    Returns dict keyed by table name (without .csv extension).
    Raises DataLoadError if any required file is missing or lacks required columns.
    """
    tables: dict[str, pd.DataFrame] = {}
    missing_files: list[str] = []

    for name, required_cols in _REQUIRED_FILES.items():
        csv_path = data_dir / f"{name}.csv"
        if not csv_path.exists():
            missing_files.append(name)
            continue

        df = pd.read_csv(csv_path)
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise DataLoadError(f"{name}.csv is missing required columns: {missing_cols}")
        tables[name] = df

    if missing_files:
        raise DataLoadError(
            f"Missing data files: {missing_files}. "
            f"Run 'uv run python run_pipeline.py' to generate them."
        )

    # Optional tables — present iff their generator has run. Frontend handles
    # absence gracefully (column will be missing in API response).
    for name, required_cols in _OPTIONAL_FILES.items():
        csv_path = data_dir / f"{name}.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            # Schema drift — log but don't crash the API
            print(f"WARNING: optional table {name} missing cols {missing_cols}, skipping")
            continue
        tables[name] = df

    return tables


def prepare_resource_df(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Prepare the resource DataFrame for compute_lcoe_live().

    Merges reliability_req from dim_sites and green_share_geas from scorecard
    onto fct_site_resource, since compute_scorecard_live() needs these columns.
    """
    resource = tables["fct_site_resource"].copy()
    dim_sites = tables["dim_sites"]
    scorecard = tables["fct_site_scorecard"]

    # Add reliability_req, business_sectors, and site-type/CBAM discriminators from dim_sites.
    # site_type + cbam_product_type + technology are required by _detect_cbam_types() to run
    # direct-mode detection for standalone/cluster/KI sites. Without them, every site falls
    # through to 3-signal KEK detection and industrial sites never show CBAM exposure.
    dim_sites_cols = ["site_id"]
    for col in [
        "reliability_req",
        "business_sectors",
        "site_type",
        "sector",
        "cbam_product_type",
        "technology",
        "capacity_annual_tonnes",
    ]:
        if col not in resource.columns and col in dim_sites.columns:
            dim_sites_cols.append(col)
    if len(dim_sites_cols) > 1:
        resource = resource.merge(dim_sites[dim_sites_cols], on="site_id", how="left")

    # Add green_share_geas and within_boundary_coverage_pct from scorecard
    # V3.7: also surface solar_regime + Perpres 112 capped LCOE for regulatory tab
    scorecard_cols = ["site_id"]
    for col in [
        "green_share_geas",
        "within_boundary_coverage_pct",
        # v4.0.5 (methodology #40): hard-max coverage drives the slider override
        # math in dash/logic/grid.py. Must be merged alongside the baseline.
        "within_boundary_coverage_hard_max_pct",
        "solar_regime",
        "lcoe_grid_connected_capped_usd_mwh",
        # F13: empirical GEAS allocation alongside the proportional baseline.
        # Already pre-computed by build_fct_site_scorecard at pipeline build time.
        "geas_alloc_proportional_gwh",
        "geas_alloc_empirical_gwh",
        "green_share_geas_proportional_pct",
        "green_share_geas_empirical_pct",
        "geas_allocation_used",
        # v4.3 M-AT8b — captive power LCOE + tier (replaces grid_cost as the
        # incumbent comparator for non-grid_only sites). The score drawer's
        # "Competitive Gap" math depends on these being available live.
        "electricity_arrangement",
        "captive_fuel_type",
        "captive_classification_confidence",
        "captive_incumbent_lcoe_usd_mwh",
        "captive_lcoe_tier",
        "captive_lcoe_fuel_price_scenario",
    ]:
        if col not in resource.columns and col in scorecard.columns:
            scorecard_cols.append(col)
    if len(scorecard_cols) > 1:
        resource = resource.merge(scorecard[scorecard_cols], on="site_id", how="left")

    # Add grid_region_id if missing
    if "grid_region_id" not in resource.columns and "grid_region_id" in dim_sites.columns:
        resource = resource.merge(
            dim_sites[["site_id", "grid_region_id"]], on="site_id", how="left"
        )

    # V2+V3.1: Add substation proximity columns for live LCOE + capacity recalculation
    if "fct_substation_proximity" in tables:
        prox = tables["fct_substation_proximity"]
        prox_cols = ["site_id", "dist_to_nearest_substation_km"]
        for col in [
            "dist_solar_to_nearest_substation_km",
            "grid_integration_category",
            "nearest_substation_name",
            "nearest_substation_capacity_mva",
            "has_internal_substation",
            "inter_substation_connected",
            "inter_substation_dist_km",
            "same_grid_region",
            "line_connected",
            "nearest_substation_capacity_source",
            "project_scale_solar_mwp",
            # V3.8: RUPTL-derived per-substation utilization signal
            "substation_utilization_pct_effective",
            "ruptl_project_type",
            "ruptl_strongest_status",
            "ruptl_earliest_target_year",
            "ruptl_mva_added_total",
            "ruptl_match_confidence",
        ]:
            if col in prox.columns:
                prox_cols.append(col)
        merge_cols = [c for c in prox_cols if c not in resource.columns or c == "site_id"]
        if len(merge_cols) > 1:
            resource = resource.merge(prox[merge_cols], on="site_id", how="left")

    # H9: Captive power summaries (optional — generated by pipeline H9 steps)
    coal_summary_path = PROCESSED / "fct_captive_coal_summary.csv"
    if coal_summary_path.exists():
        coal_sum = pd.read_csv(coal_summary_path)
        resource = resource.merge(coal_sum, on="site_id", how="left")

    nickel_summary_path = PROCESSED / "fct_captive_nickel_summary.csv"
    if nickel_summary_path.exists():
        nickel_sum = pd.read_csv(nickel_summary_path)
        resource = resource.merge(nickel_sum, on="site_id", how="left")

    steel_summary_path = PROCESSED / "fct_captive_steel_summary.csv"
    if steel_summary_path.exists():
        steel_sum = pd.read_csv(steel_summary_path)
        resource = resource.merge(steel_sum, on="site_id", how="left")

    cement_summary_path = PROCESSED / "fct_captive_cement_summary.csv"
    if cement_summary_path.exists():
        cement_sum = pd.read_csv(cement_summary_path)
        resource = resource.merge(cement_sum, on="site_id", how="left")

    # F6 (2026-05-09): Perpres 112/2022 structured regulatory state.
    # Replaces the legacy perpres_112_status string with 5 typed columns.
    perpres_path = PROCESSED / "fct_perpres_112_classification.csv"
    if perpres_path.exists():
        perpres = pd.read_csv(perpres_path)
        perpres_cols = [
            "site_id",
            "captive_perpres_112_exempt",
            "captive_perpres_112_exemption_basis",
            "captive_phaseout_year_baseline",
            "captive_phaseout_year_strict_scenario",
            "captive_subject_to_strict_scenario",
            "captive_perpres_112_source",
            "captive_perpres_112_verification_status",
        ]
        keep = [c for c in perpres_cols if c in perpres.columns]
        resource = resource.merge(perpres[keep], on="site_id", how="left")

    # F5 (2026-05-09): RUPTL §V.9 transmission-link feasibility — region rollup.
    # Produces a per-region worst-case status; the scorecard enricher derives
    # the per-site comparator_feasibility from this + grid_integration_category.
    transmission_path = PROCESSED / "fct_transmission_link_ruptl_signal.csv"
    if transmission_path.exists():
        links_df = pd.read_csv(transmission_path)
        region_status = region_worst_status_map(links_df)
        # Find the most-restrictive RUPTL section for each region (for citation)
        section_by_region: dict[str, str] = {}
        for _, row in links_df.iterrows():
            for region in [row.get("from_region"), row.get("to_region")]:
                if pd.notna(region) and region != "CROSS_BORDER":
                    section_by_region.setdefault(region, row.get("ruptl_section"))
        resource["recommended_grid_link_status"] = resource["grid_region_id"].map(
            lambda r: region_status.get(r, "not_in_ruptl")
        )
        resource["recommended_grid_link_section"] = resource["grid_region_id"].map(
            lambda r: section_by_region.get(r)
        )

    # F2: Geothermal proximity columns (optional — generated by
    # build_fct_geothermal_proximity.py). Drives the F1 dispatchable-RE layer
    # of the Supply Blend cascade. Sites without the file see no behavior
    # change (cascade falls through to v4.0 3-layer behaviour).
    geothermal_path = PROCESSED / "fct_geothermal_proximity.csv"
    if geothermal_path.exists():
        geo = pd.read_csv(geothermal_path)
        geo_cols = ["site_id"]
        for col in [
            "nearest_geothermal_operating_id",
            "nearest_geothermal_operating_km",
            "nearest_geothermal_operating_mw",
            "nearest_geothermal_operating_emission_factor_g_per_kwh",
            "nearest_geothermal_pipeline_id",
            "nearest_geothermal_pipeline_km",
            "nearest_geothermal_pipeline_mw",
            "nearest_geothermal_pipeline_target_year",
            "geothermal_adjacency_tier",
        ]:
            if col in geo.columns and col not in resource.columns:
                geo_cols.append(col)
        if len(geo_cols) > 1:
            resource = resource.merge(geo[geo_cols], on="site_id", how="left")

    # Wind resource columns (optional — generated by build_fct_site_wind_resource.py)
    wind_resource_path = PROCESSED / "fct_site_wind_resource.csv"
    if wind_resource_path.exists():
        wind_res = pd.read_csv(wind_resource_path)
        wind_cols = ["site_id"]
        for col in [
            "wind_speed_centroid_ms",
            "wind_speed_best_50km_ms",
            "cf_wind_centroid",
            "cf_wind_best_50km",
            "wind_class",
            "wind_buildable_area_ha",
            "max_wind_capacity_mwp",
            "wind_buildability_constraint",
            "wind_speed_buildable_best_ms",
            "cf_wind_buildable_best",
        ]:
            if col in wind_res.columns and col not in resource.columns:
                wind_cols.append(col)
        if len(wind_cols) > 1:
            resource = resource.merge(wind_res[wind_cols], on="site_id", how="left")

    # F8 (2026-05-08): per-site curtailment loss estimate, stamped on every
    # resource row so live LCOE can apply a CF haircut to the grid-connected
    # scenario. Computed once here from grid-region BPP (proxy for grid
    # maturity), inter-substation connectivity, and a representative solar
    # generation vs local-grid demand ratio. Within-boundary captive bypasses
    # this — see compute_lcoe_live.
    if "fct_grid_cost_proxy" in tables and "fct_site_demand" in tables:
        from src.model.basic_model import (  # noqa: PLC0415 — local import keeps module-level deps light
            estimate_curtailment_loss_pct,
        )

        grid_df = tables["fct_grid_cost_proxy"]
        demand_df = tables["fct_site_demand"]

        # Sum demand per grid_region, joined via dim_sites.
        if "grid_region_id" in dim_sites.columns:
            demand_with_region = demand_df.merge(
                dim_sites[["site_id", "grid_region_id"]], on="site_id", how="left"
            )
            region_demand = (
                demand_with_region.groupby("grid_region_id")["demand_mwh"].sum().to_dict()
            )
        else:
            region_demand = {}

        bpp_by_region = (
            grid_df.set_index("grid_region_id")["bpp_usd_mwh"].to_dict()
            if "bpp_usd_mwh" in grid_df.columns
            else {}
        )

        def _curtail(row: pd.Series) -> float:
            region = row.get("grid_region_id")
            mwp = row.get("regional_groundmount_potential_mwp_50km", 0)
            cf = row.get("pvout_centroid", 1700) / 8760  # rough CF from PVOUT
            if pd.isna(mwp) or mwp <= 0:
                return 0.05
            solar_gen_mwh = float(mwp) * float(cf) * 8760  # MW × hours
            local_demand = float(region_demand.get(region, 0))
            inter_conn = bool(row.get("inter_substation_connected", False))
            bpp = float(bpp_by_region.get(region, 100.0))
            return estimate_curtailment_loss_pct(
                solar_generation_mwh=solar_gen_mwh,
                local_grid_demand_mwh=local_demand,
                inter_substation_connected=inter_conn,
                grid_region_bpp_usd_mwh=bpp,
            )

        resource["curtailment_loss_pct"] = resource.apply(_curtail, axis=1)

    return resource


def compute_ruptl_region_metrics(ruptl_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fct_ruptl_pipeline into per-region metrics for compute_scorecard_live().

    Returns DataFrame with columns: grid_region_id, post2030_share, grid_upgrade_pre2030.
    """
    if ruptl_df is None or ruptl_df.empty:
        return pd.DataFrame(columns=["grid_region_id", "post2030_share", "grid_upgrade_pre2030"])

    grouped = ruptl_df.groupby("grid_region_id")

    rows = []
    for region_id, group in grouped:
        total_mw = (
            group["plts_new_mw_re_base"].sum() if "plts_new_mw_re_base" in group.columns else 0
        )
        post2030 = (
            group[group["year"] > 2030]["plts_new_mw_re_base"].sum()
            if "plts_new_mw_re_base" in group.columns
            else 0
        )
        post2030_share = post2030 / total_mw if total_mw > 0 else 1.0

        pre2030 = group[group["year"] <= 2030]
        grid_upgrade = (
            pre2030["plts_new_mw_re_base"].sum() > 0
            if "plts_new_mw_re_base" in pre2030.columns
            else False
        )

        rows.append(
            {
                "grid_region_id": region_id,
                "post2030_share": round(post2030_share, 4),
                "grid_upgrade_pre2030": bool(grid_upgrade),
            }
        )

    return pd.DataFrame(rows)


def load_wind_tech_defaults(data_dir: Path = PROCESSED) -> dict:
    """Load wind technology cost parameters from dim_tech_cost_wind.csv.

    Returns dict with capex_usd_per_kw, fom_usd_per_kw_yr, lifetime_yr.
    Falls back to hardcoded defaults if file is missing.
    """
    path = data_dir / "dim_tech_cost_wind.csv"
    if path.exists():
        df = pd.read_csv(path)
        if len(df):
            row = df.iloc[0]
            return {
                "capex_usd_per_kw": float(row.get("capex_usd_per_kw", 1650)),
                "fom_usd_per_kw_yr": float(row.get("fixed_om_usd_per_kw_yr", 40)),
                "lifetime_yr": int(row.get("lifetime_yr", 27)),
            }
    return {"capex_usd_per_kw": 1650.0, "fom_usd_per_kw_yr": 40.0, "lifetime_yr": 27}


def load_kek_infrastructure() -> dict[str, list[dict]]:
    """Load infrastructure markers per KEK from kek_info_and_markers.csv.

    Returns dict mapping site_id (slug) to list of infrastructure markers,
    each with keys: title, category, lat, lon.
    """
    path = (
        Path(__file__).resolve().parents[2]
        / "outputs"
        / "data"
        / "raw"
        / "kek_info_and_markers.csv"
    )
    if not path.exists():
        return {}

    df = pd.read_csv(path)
    result: dict[str, list[dict]] = {}
    for _, row in df.iterrows():
        slug = row.get("slug", "")
        infra_raw = row.get("infrastructures", "[]")
        try:
            infra_list = ast.literal_eval(infra_raw) if isinstance(infra_raw, str) else []
        except (ValueError, SyntaxError):
            infra_list = []

        markers = []
        for item in infra_list:
            lat = item.get("latitude")
            lon = item.get("longitude")
            if lat is not None and lon is not None:
                cat = item.get("category", {})
                cat_name = cat.get("name", "Unknown") if isinstance(cat, dict) else str(cat)
                markers.append(
                    {
                        "title": item.get("title", ""),
                        "category": cat_name,
                        "lat": float(lat),
                        "lon": float(lon),
                    }
                )
        if markers:
            result[slug] = markers

    return result
