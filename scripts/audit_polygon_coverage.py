"""Audit polygon coverage across all 81 sites, ranked by 2030 energy demand.

Phase 2 prioritization tool: tells us which sites still need a polygon
hunt and orders them by impact (highest-demand first). Without a polygon,
non-KEK industrial sites rely on the upstream 2 km buffer + RV11
residential filter, which over-counts adjacent residential — exactly
the kind of bleed RV-eval surfaces.

# What this produces

`outputs/data/processed/polygon_coverage_priority.csv` — one row per
site with:
  • site_id, site_name, sector, site_type
  • has_kek_polygon            — 25 KEKs (true) / non-KEK (false)
  • has_industrial_polygon     — 11 sites (true) / rest (false)
  • effective_polygon_coverage — has_kek_polygon OR has_industrial_polygon
  • capacity_annual_tonnes     — for industrial sites only
  • area_ha                    — KEK area
  • demand_mwh_2030            — annual electricity demand (proxy)
  • current_rooftop_mwp        — what the pipeline currently reports
  • polygon_priority           — "covered" | "high" | "medium" | "low"

# Priority ranking

For sites WITHOUT a polygon:
  • high   — top demand-proxy quartile (P75+) — biggest tariff/CBAM-relief lever
  • medium — middle two quartiles
  • low    — bottom quartile

Demand-proxy choice: `fct_site_demand` currently dispatches all 56 non-KEK
industrial sites to the `area_fallback_median` (a single constant
~376 GWh), so demand_mwh_2030 is useless as a per-site ranking signal
for non-KEKs. We rank by `capacity_annual_tonnes × SECTOR_ELECTRICITY_
ONLY_MWH_PER_TONNE` for industrial sites and by `area_ha × intensity`
for KEKs — same formula the demand pipeline *should* use, applied
inline so this audit isn't blocked on fixing the upstream dispatch
(flagged as a separate finding in TODOS).

# Output

CSV at `outputs/data/processed/polygon_coverage_priority.csv` plus a
console summary table of the top 20 high-priority uncovered sites.

Run:
    PYTHONPATH=. uv run python scripts/audit_polygon_coverage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.assumptions import (
    ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
    ENERGY_INTENSITY_MWH_PER_HA_YR,
)
from src.pipeline.demand_intensity import estimate_demand_sector_intensity

REPO_ROOT = Path(__file__).resolve().parents[1]
DEMAND_REFERENCE_YEAR = 2030
MIN_QUARTILE_SAMPLE = 4
DIM_SITES = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
FCT_DEMAND = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_demand.csv"
FCT_ROOFTOP = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_solar_potential.csv"
KEK_POLYGONS = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
INDUSTRIAL_POLYGONS = REPO_ROOT / "data" / "industrial_sites" / "site_polygons.geojson"
OUTPUT = REPO_ROOT / "outputs" / "data" / "processed" / "polygon_coverage_priority.csv"


def main() -> int:
    sites = pd.read_csv(DIM_SITES)
    demand = pd.read_csv(FCT_DEMAND)
    rooftop = pd.read_csv(FCT_ROOFTOP)

    # Latest demand row per site (the demand fct stores per-year rows).
    demand_2030 = (
        demand[demand["year"] == DEMAND_REFERENCE_YEAR][["site_id", "demand_mwh"]]
        .rename(columns={"demand_mwh": "demand_mwh_2030"})
        .drop_duplicates("site_id")
    )

    # Polygon coverage maps
    kek_gdf = gpd.read_file(KEK_POLYGONS)
    kek_ids = set(kek_gdf["slug"].dropna().astype(str)) if "slug" in kek_gdf.columns else set()
    ind_gdf = gpd.read_file(INDUSTRIAL_POLYGONS) if INDUSTRIAL_POLYGONS.exists() else None
    ind_ids = (
        set(ind_gdf["site_id"].dropna().astype(str))
        if ind_gdf is not None and "site_id" in ind_gdf.columns
        else set()
    )

    df = sites.merge(demand_2030, on="site_id", how="left")
    df = df.merge(
        rooftop[["site_id", "rooftop_solar_mwp_potential", "building_data_confidence"]],
        on="site_id",
        how="left",
    )

    df["has_kek_polygon"] = df["site_id"].isin(kek_ids)
    df["has_industrial_polygon"] = df["site_id"].isin(ind_ids)
    df["effective_polygon_coverage"] = df["has_kek_polygon"] | df["has_industrial_polygon"]

    # Real per-site demand proxy. The fct_site_demand pipeline currently
    # dispatches all 56 non-KEK sites to a constant area_fallback_median
    # (~376 GWh) — a known regression flagged separately. We compute the
    # *intended* per-site value inline so the priority ranking actually
    # discriminates between, say, 250 ktpa Inalum and 7 Mtpa Dexin Steel.
    def per_site_demand_mwh(row) -> float:
        st = row.get("site_type")
        sector = row.get("sector")
        if st == "kek":
            # KEKs use area-based demand; if no area, fall back to fleet median.
            area = row.get("area_ha")
            if pd.isna(area) or area is None or area <= 0:
                return float("nan")
            intensity = ENERGY_INTENSITY_MWH_PER_HA_YR.get(
                str(sector or "").lower(),
                ENERGY_INTENSITY_DEFAULT_MWH_PER_HA_YR,
            )
            return float(area) * float(intensity)
        # standalone / cluster — sector intensity × capacity
        cap = row.get("capacity_annual_tonnes")
        if pd.isna(cap) or cap is None or cap <= 0 or sector is None:
            return float("nan")
        try:
            return estimate_demand_sector_intensity(
                float(cap), str(sector), row.get("technology") or None
            )
        except KeyError:
            return float("nan")

    df["demand_proxy_mwh"] = df.apply(per_site_demand_mwh, axis=1)

    # Demand-quartile priority computed against the real per-site proxy.
    uncovered = df[~df["effective_polygon_coverage"]]
    real_demand = uncovered["demand_proxy_mwh"].dropna()
    if len(real_demand) >= MIN_QUARTILE_SAMPLE:
        q75 = real_demand.quantile(0.75)
        q50 = real_demand.quantile(0.50)
        q25 = real_demand.quantile(0.25)
    else:
        q75 = q50 = q25 = 0.0

    def priority(row) -> str:
        if row["effective_polygon_coverage"]:
            return "covered"
        d = row["demand_proxy_mwh"]
        if pd.isna(d):
            return "unknown"
        if d >= q75:
            return "high"
        if d >= q50:
            return "medium"
        if d >= q25:
            return "low"
        return "minimal"

    df["polygon_priority"] = df.apply(priority, axis=1)

    # Output column ordering — most useful for a reviewer scanning the CSV.
    cols = [
        "site_id",
        "site_name",
        "sector",
        "site_type",
        "has_kek_polygon",
        "has_industrial_polygon",
        "effective_polygon_coverage",
        "polygon_priority",
        "capacity_annual_tonnes",
        "area_ha",
        "demand_proxy_mwh",
        "demand_mwh_2030",
        "rooftop_solar_mwp_potential",
        "building_data_confidence",
    ]
    available = [c for c in cols if c in df.columns]
    df_out = df[available].sort_values(
        ["polygon_priority", "demand_proxy_mwh"],
        ascending=[True, False],
        na_position="last",
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT, index=False)

    # Console summary — the actionable bit.
    n_covered = df["effective_polygon_coverage"].sum()
    n_total = len(df)
    print(f"Polygon coverage: {n_covered}/{n_total} sites have a polygon")
    print(f"  KEK polygons:        {df['has_kek_polygon'].sum()}/25")
    print(f"  Industrial polygons: {df['has_industrial_polygon'].sum()}/56")
    print()

    by_priority = df["polygon_priority"].value_counts()
    print("Priority breakdown:")
    for tag in ("covered", "high", "medium", "low", "minimal", "unknown"):
        n = int(by_priority.get(tag, 0))
        if n:
            print(f"  {tag:<8} {n:>3}")
    print()

    high = df[df["polygon_priority"] == "high"].sort_values(
        "demand_proxy_mwh", ascending=False, na_position="last"
    )
    if not high.empty:
        print(f"Top {min(20, len(high))} HIGH-priority uncovered sites (by per-site demand proxy):")
        print()
        # Compact text table
        for _, r in high.head(20).iterrows():
            cap = (
                f"{r['capacity_annual_tonnes'] / 1000:>7.0f} kt"
                if pd.notna(r["capacity_annual_tonnes"])
                else "    n/a   "
            )
            demand_gwh = (
                r["demand_proxy_mwh"] / 1000.0 if pd.notna(r["demand_proxy_mwh"]) else float("nan")
            )
            roof = (
                f"{r['rooftop_solar_mwp_potential']:>6.1f}"
                if pd.notna(r["rooftop_solar_mwp_potential"])
                else "  n/a "
            )
            print(
                f"  {r['site_name'][:38]:<38} {r['sector']:<10} "
                f"cap={cap}  demand={demand_gwh:>7.0f} GWh  roof={roof} MWp"
            )
        print()
    print(f"Full CSV: {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
