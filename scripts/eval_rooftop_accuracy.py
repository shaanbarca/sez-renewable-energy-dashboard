"""Rooftop accuracy eval — automated red flags for the rooftop pipeline.

Companion to scripts/validate_centroids.py (which validates inputs — site
centroids land on industrial land cover). This validates OUTPUTS — once
we've run the rooftop pipeline, do the per-site MWp numbers look right
when held against statistical and physical sanity?

Three checks:

  A. Per-sector capacity-vs-MWp band
     For each sector with >= EVAL_SECTOR_MIN_SAMPLE sites, compute
     z-score on rooftop_MWp / capacity_kt. Flag |z| > 2 as HIGH-PRIORITY.
     Sectors below threshold (aluminium n=2) get a "manual review
     required" flag instead of a numerical band.

  B. Zero-rooftop-but-nonzero-capacity rule
     A site with capacity > 0 but rooftop_MWp ≈ 0 is almost certainly
     the RV7 GoB-undercount pattern (Cemindo Bayah, Hongshi, IWIP).
     Z-score won't catch this because zero pulls the median down.
     Explicit rule catches it cleanly.

  C. Plant-area band (sites with polygon)
     For sites with a fence-boundary polygon, total_building_footprint
     should be 5-30% of polygon area. Below 5% suggests we're missing
     most of the plant (RV7); above 30% suggests residential bleed or
     the polygon is too tight. Sites without polygon are skipped and
     reported as "uncovered."

Cross-source IoU agreement (between GoB v3 and Microsoft GMLBF) is the
fourth planned check, deferred until MS GMLBF is integrated.

Output: two-tier console report (HIGH / LOW priority) plus a JSONL
append to ~/.gstack/projects/eez/eval-history.jsonl for trend tracking.
Exit code 1 when any HIGH-PRIORITY findings exist — CI-friendly.

Run:
    PYTHONPATH=. uv run python scripts/eval_rooftop_accuracy.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from src.assumptions import (
    EVAL_FOOTPRINT_RATIO_HIGH,
    EVAL_FOOTPRINT_RATIO_LOW,
    EVAL_HIST_PATH,
    EVAL_SECTOR_MIN_SAMPLE,
    EVAL_SECTOR_ZSCORE_THRESHOLD,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FCT_ROOFTOP = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_solar_potential.csv"
DIM_SITES = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
KEK_POLYGONS = REPO_ROOT / "outputs" / "data" / "raw" / "kek_polygons.geojson"
INDUSTRIAL_POLYGONS = REPO_ROOT / "data" / "industrial_sites" / "site_polygons.geojson"

# Both polygon sets are EPSG:4326. Reproject to UTM 50S for accurate area.
PROJECTED_CRS = "EPSG:23830"

# Threshold below which we treat rooftop_MWp as "effectively zero" — operating
# sites under this with non-zero capacity get the explicit zero-rule flag.
ZERO_MWP_THRESHOLD = 0.1


def load_data() -> tuple[pd.DataFrame, gpd.GeoDataFrame]:
    """Read the rooftop output + dim_sites + polygon sources.

    Validates required columns up front so the eval fails loud if the
    pipeline schema drifts (rather than silently mis-checking).
    """
    if not FCT_ROOFTOP.exists():
        msg = f"Missing {FCT_ROOFTOP} — run build_fct_site_solar_potential first."
        raise FileNotFoundError(msg)
    if not DIM_SITES.exists():
        msg = f"Missing {DIM_SITES} — run build_dim_sites first."
        raise FileNotFoundError(msg)

    fct = pd.read_csv(FCT_ROOFTOP)
    sites = pd.read_csv(DIM_SITES)

    required_fct = {
        "site_id",
        "rooftop_solar_mwp_potential",
        "total_building_footprint_m2",
    }
    required_sites = {"site_id", "sector", "site_type", "capacity_annual_tonnes"}
    fct_missing = required_fct - set(fct.columns)
    sites_missing = required_sites - set(sites.columns)
    if fct_missing:
        msg = f"fct_site_solar_potential.csv missing columns: {fct_missing}"
        raise ValueError(msg)
    if sites_missing:
        msg = f"dim_sites.csv missing columns: {sites_missing}"
        raise ValueError(msg)

    df = fct.merge(
        sites[["site_id", "sector", "site_type", "capacity_annual_tonnes"]],
        on="site_id",
        how="left",
    )

    # Combine KEK + industrial polygons keyed on site_id for the area band.
    polys: list[gpd.GeoDataFrame] = []
    if KEK_POLYGONS.exists():
        kek = gpd.read_file(KEK_POLYGONS)
        if "slug" in kek.columns:
            kek = kek.rename(columns={"slug": "site_id"})
            polys.append(kek[["site_id", "geometry"]])
    if INDUSTRIAL_POLYGONS.exists():
        ind = gpd.read_file(INDUSTRIAL_POLYGONS)
        if "site_id" in ind.columns:
            polys.append(ind[["site_id", "geometry"]])
    polygons = (
        gpd.GeoDataFrame(pd.concat(polys, ignore_index=True), crs="EPSG:4326").dissolve(
            by="site_id", as_index=False
        )
        if polys
        else gpd.GeoDataFrame(columns=["site_id", "geometry"], crs="EPSG:4326")
    )

    return df, polygons


def check_sector_ratio_band(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Per-sector z-score on rooftop_MWp / capacity_kt.

    Includes the explicit zero-rule (issue #2 from review): any non-zero
    capacity site with ~zero rooftop is HIGH-PRIORITY regardless of
    z-score. Sectors below MIN_SAMPLE get a "manual review" flag.
    """
    findings: list[dict[str, Any]] = []

    # Drop sites without capacity (mostly KEKs — capacity_annual_tonnes is NaN).
    rated = df[df["capacity_annual_tonnes"].notna() & (df["capacity_annual_tonnes"] > 0)].copy()
    rated["capacity_kt"] = rated["capacity_annual_tonnes"] / 1000.0
    rated["mwp_per_kt"] = rated["rooftop_solar_mwp_potential"] / rated["capacity_kt"]

    # Zero-rule: explicit catch for the RV7 / centroid-still-wrong cases.
    zero_mwp = rated[rated["rooftop_solar_mwp_potential"] < ZERO_MWP_THRESHOLD]
    for _, row in zero_mwp.iterrows():
        findings.append(
            {
                "check": "zero_mwp_with_capacity",
                "priority": "HIGH",
                "site_id": row["site_id"],
                "site_name": row["site_name"],
                "sector": row["sector"],
                "capacity_kt": round(row["capacity_kt"], 1),
                "rooftop_mwp": round(row["rooftop_solar_mwp_potential"], 3),
                "reason": (
                    f"Operating site with {row['capacity_kt']:.1f} kt/yr capacity "
                    f"but rooftop_MWp ≈ 0 — likely RV7 (GoB undercount) or "
                    f"centroid still wrong"
                ),
            }
        )
    # Exclude zero-MWp from z-score so they don't pull the median.
    band_eligible = rated[rated["rooftop_solar_mwp_potential"] >= ZERO_MWP_THRESHOLD].copy()

    for sector, grp in band_eligible.groupby("sector"):
        if len(grp) < EVAL_SECTOR_MIN_SAMPLE:
            findings.append(
                {
                    "check": "sector_sample_too_small",
                    "priority": "LOW",
                    "site_id": None,
                    "site_name": None,
                    "sector": sector,
                    "n": int(len(grp)),
                    "reason": (
                        f"Sector '{sector}' has only {len(grp)} sites — "
                        f"can't form reliable z-score band (min {EVAL_SECTOR_MIN_SAMPLE}). "
                        f"Manual review required."
                    ),
                }
            )
            continue
        ratios = grp["mwp_per_kt"]
        median = ratios.median()
        std = ratios.std()
        if std == 0 or pd.isna(std):
            continue
        z = (ratios - median) / std
        for idx, zval in z.items():
            if abs(zval) > EVAL_SECTOR_ZSCORE_THRESHOLD:
                row = grp.loc[idx]
                findings.append(
                    {
                        "check": "sector_ratio_outlier",
                        "priority": "HIGH",
                        "site_id": row["site_id"],
                        "site_name": row["site_name"],
                        "sector": sector,
                        "mwp_per_kt": round(row["mwp_per_kt"], 4),
                        "sector_median_mwp_per_kt": round(median, 4),
                        "z_score": round(float(zval), 2),
                        "reason": (
                            f"MWp/kt ratio {row['mwp_per_kt']:.3f} is "
                            f"{abs(zval):.1f}σ from sector median "
                            f"{median:.3f} (n={len(grp)})"
                        ),
                    }
                )
    return findings


def check_plant_area_band(
    df: pd.DataFrame, polygons: gpd.GeoDataFrame
) -> tuple[list[dict[str, Any]], int, int]:
    """Footprint-as-share-of-polygon-area band.

    The 5-30% band is calibrated for industrial PLANTS — sites where the
    polygon is the actual fence boundary. KEKs and industrial parks
    (KIs) are zones that include lots of undeveloped land by design
    (Industropolis Batang, Sei Mangkei, Mandalika), so they would
    always flag below 5%. Skip them — the band check only applies to
    standalone and cluster industrial sites.

    Returns (findings, n_covered, n_total) so the report can show
    coverage of this check honestly. n_total counts only eligible
    (standalone/cluster) sites.
    """
    findings: list[dict[str, Any]] = []

    eligible = df[df["site_type"].isin(["standalone", "cluster"])].copy()

    if polygons.empty:
        return findings, 0, len(eligible)

    # Project polygons once for accurate metric area.
    polys_proj = polygons.to_crs(PROJECTED_CRS)
    polys_proj["polygon_area_m2"] = polys_proj.geometry.area

    n_covered = 0
    for _, row in eligible.iterrows():
        match = polys_proj[polys_proj["site_id"] == row["site_id"]]
        if match.empty:
            continue
        n_covered += 1
        polygon_area_m2 = float(match.iloc[0]["polygon_area_m2"])
        if polygon_area_m2 <= 0:
            continue
        footprint_m2 = float(row["total_building_footprint_m2"])
        ratio = footprint_m2 / polygon_area_m2

        if ratio < EVAL_FOOTPRINT_RATIO_LOW:
            findings.append(
                {
                    "check": "footprint_below_band",
                    "priority": "HIGH",
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "footprint_m2": round(footprint_m2, 0),
                    "polygon_m2": round(polygon_area_m2, 0),
                    "ratio": round(ratio, 4),
                    "reason": (
                        f"Building footprint is {ratio * 100:.1f}% of polygon area, "
                        f"below the 5% floor — plant likely under-detected"
                    ),
                }
            )
        elif ratio > EVAL_FOOTPRINT_RATIO_HIGH:
            findings.append(
                {
                    "check": "footprint_above_band",
                    "priority": "HIGH",
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "footprint_m2": round(footprint_m2, 0),
                    "polygon_m2": round(polygon_area_m2, 0),
                    "ratio": round(ratio, 4),
                    "reason": (
                        f"Building footprint is {ratio * 100:.1f}% of polygon area, "
                        f"above the 30% ceiling — possible residential bleed or "
                        f"polygon too tight"
                    ),
                }
            )
    return findings, n_covered, len(eligible)


def format_report(
    findings: list[dict[str, Any]],
    poly_coverage: tuple[int, int],
) -> str:
    """Two-tier console output matching scripts/validate_centroids.py."""
    high = [f for f in findings if f.get("priority") == "HIGH"]
    low = [f for f in findings if f.get("priority") == "LOW"]
    n_covered, n_total = poly_coverage

    lines = []
    if high:
        lines.append(f"🚨 HIGH-PRIORITY: {len(high)} finding(s)")
        lines.append("")
        for f in high:
            sid = f.get("site_id") or f.get("sector", "?")
            name = f.get("site_name") or sid
            lines.append(f"  [{f['check']}] {name}")
            lines.append(f"      {f['reason']}")
        lines.append("")
    else:
        lines.append("✅ No HIGH-PRIORITY findings.")
        lines.append("")

    if low:
        lines.append(f"ℹ LOWER-PRIORITY: {len(low)} finding(s)")
        lines.append("")
        for f in low:
            sid = f.get("sector") or f.get("site_id", "?")
            lines.append(f"  [{f['check']}] {sid}")
            lines.append(f"      {f['reason']}")
        lines.append("")

    lines.append(f"Plant-area-band coverage: {n_covered}/{n_total} sites have a polygon")
    if n_covered < n_total:
        lines.append(
            f"  ({n_total - n_covered} sites pass through unchecked — "
            f"polygon needed to apply the area band)"
        )
    return "\n".join(lines)


def append_history(findings: list[dict[str, Any]]) -> None:
    """Append a single JSONL line per run for trend tracking."""
    path = Path(EVAL_HIST_PATH).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    high = [f for f in findings if f.get("priority") == "HIGH"]
    low = [f for f in findings if f.get("priority") == "LOW"]
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_high": len(high),
        "n_low": len(low),
        "findings": findings,
    }
    with path.open("a") as f:
        f.write(json.dumps(record) + "\n")


def main() -> int:
    df, polygons = load_data()

    findings: list[dict[str, Any]] = []
    findings.extend(check_sector_ratio_band(df))
    plant_findings, n_covered, n_total = check_plant_area_band(df, polygons)
    findings.extend(plant_findings)

    print(format_report(findings, (n_covered, n_total)))
    append_history(findings)

    n_high = sum(1 for f in findings if f.get("priority") == "HIGH")
    return 1 if n_high > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
