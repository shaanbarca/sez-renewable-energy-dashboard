# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Data loading and validation for the dashboard.

Loads precomputed CSVs from the pipeline output directory, validates required
columns, and prepares DataFrames for live computation via logic.py.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"

# Required CSV files and their minimum expected columns
_REQUIRED_FILES = {
    "fct_kek_scorecard": ["kek_id", "kek_name", "action_flag", "lcoe_mid_usd_mwh"],
    "fct_kek_resource": ["kek_id", "pvout_centroid", "pvout_best_50km"],
    "fct_lcoe": ["kek_id", "scenario", "lcoe_usd_mwh"],
    "fct_substation_proximity": ["kek_id", "dist_to_nearest_substation_km"],
    "fct_ruptl_pipeline": ["grid_region_id", "year"],
    "fct_grid_cost_proxy": ["grid_region_id", "dashboard_rate_usd_mwh"],
    "fct_kek_demand": ["kek_id", "demand_mwh"],
    "dim_kek": ["kek_id", "kek_name", "latitude", "longitude"],
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

    return tables


def prepare_resource_df(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Prepare the resource DataFrame for compute_lcoe_live().

    Merges reliability_req from dim_kek and green_share_geas from scorecard
    onto fct_kek_resource, since compute_scorecard_live() needs these columns.
    """
    resource = tables["fct_kek_resource"].copy()
    dim_kek = tables["dim_kek"]
    scorecard = tables["fct_kek_scorecard"]

    # Add reliability_req from dim_kek
    if "reliability_req" not in resource.columns and "reliability_req" in dim_kek.columns:
        resource = resource.merge(dim_kek[["kek_id", "reliability_req"]], on="kek_id", how="left")

    # Add green_share_geas from scorecard
    if "green_share_geas" not in resource.columns and "green_share_geas" in scorecard.columns:
        resource = resource.merge(
            scorecard[["kek_id", "green_share_geas"]], on="kek_id", how="left"
        )

    # Add grid_region_id if missing
    if "grid_region_id" not in resource.columns and "grid_region_id" in dim_kek.columns:
        resource = resource.merge(dim_kek[["kek_id", "grid_region_id"]], on="kek_id", how="left")

    # V2: Add substation proximity columns for grid-connected solar LCOE
    if "fct_substation_proximity" in tables:
        prox = tables["fct_substation_proximity"]
        prox_cols = ["kek_id", "dist_to_nearest_substation_km"]
        for col in ["dist_solar_to_nearest_substation_km", "grid_integration_category"]:
            if col in prox.columns:
                prox_cols.append(col)
        merge_cols = [c for c in prox_cols if c not in resource.columns or c == "kek_id"]
        if len(merge_cols) > 1:
            resource = resource.merge(prox[merge_cols], on="kek_id", how="left")

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


def load_kek_infrastructure() -> dict[str, list[dict]]:
    """Load infrastructure markers per KEK from kek_info_and_markers.csv.

    Returns dict mapping kek_id (slug) to list of infrastructure markers,
    each with keys: title, category, lat, lon.
    """
    import ast

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
