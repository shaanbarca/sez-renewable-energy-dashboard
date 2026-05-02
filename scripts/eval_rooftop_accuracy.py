"""Rooftop accuracy eval — automated red flags for the rooftop pipeline.

Companion to scripts/validate_centroids.py (which validates inputs — site
centroids land on industrial land cover). This validates OUTPUTS — once
we've run the rooftop pipeline, do the per-site MWp numbers look right
when held against statistical and physical sanity?

Three checks, surfaced as six self-explanatory flag types:

  A. zero_mwp_with_capacity (🔴 actionable)
     Operating site (capacity > 0) but rooftop_MWp ≈ 0 — almost certainly
     the RV7 GoB-undercount pattern (Cemindo Bayah, Hongshi, IWIP) or a
     wrong centroid. Z-score won't catch this because zero pulls the
     median down. Explicit rule catches it cleanly.

  B. sector_outlier_above / sector_outlier_below (🔴 actionable)
     Per-sector z-score on rooftop_MWp / capacity_kt. Above 2σ = possible
     residential bleed, panels-on-quarry-pit, or polygon too tight.
     Below -2σ = possible undercount that wasn't already caught by the
     zero-rule. Direction matters — fix is different.

  C. footprint_below_band / footprint_above_band (🟡 sanity check)
     For sites with a fence-boundary polygon, total_building_footprint
     should be 5-30% of polygon area. Below 5% = under-detection; above
     30% = residential bleed or polygon too tight. Restricted to
     standalone/cluster site types — KEKs include undeveloped land by
     design and would always flag below 5%.

  D. sector_sample_too_small (ℹ info)
     Sectors with fewer than EVAL_SECTOR_MIN_SAMPLE sites can't form a
     reliable z-score band. Pass-through with a manual-review note.

Cross-source IoU agreement (between GoB v3 and Microsoft GMLBF) is the
fifth planned check, deferred until MS GMLBF is integrated.

Output: console report grouped by flag type (each group has a header
explaining the rule + suggested fix) plus a JSONL append to
docs/eval/rooftop-history.jsonl for trend tracking. Exit code 1 when
any actionable (🔴) findings exist — CI-friendly.

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
GOB_PARQUET = REPO_ROOT / "data" / "processed" / "sites_buildings_filtered.parquet"
MS_PARQUET = REPO_ROOT / "data" / "processed" / "sites_buildings_microsoft.parquet"

# Threshold for the cross-source IoU check (matches MS_DEDUP_IOU_THRESHOLD).
# Any MS building without a GoB match above this IoU is "net-new".
CROSS_SOURCE_IOU_THRESHOLD = 0.5
# A site qualifies as "MS reveals materially more buildings" when MS adds
# at least this many net-new buildings AND the gain is at least this
# fraction of the GoB count. Both gates avoid noise on small sites.
MS_REVEAL_MIN_NEW_BUILDINGS = 5
MS_REVEAL_MIN_GAIN_FRACTION = 0.5

# Both polygon sets are EPSG:4326. Reproject to UTM 50S for accurate area.
PROJECTED_CRS = "EPSG:23830"

# Threshold below which we treat rooftop_MWp as "effectively zero" — operating
# sites under this with non-zero capacity get the explicit zero-rule flag.
ZERO_MWP_THRESHOLD = 0.1

# Display order = priority order. The icon also encodes severity:
#   🔴 actionable — site-level fix needed (treated as "exit 1" in CI)
#   🟡 sanity check — investigate, may or may not be a real issue
#   ℹ  info — pass-through, no action expected
#
# `priority` is the categorical bucket used by main()'s exit code logic:
#   "actionable" — exit 1 if any present
#   "review"     — exit 0 (warning only)
#   "info"       — exit 0
#
# The user-facing report uses these display configs to render each group
# with a header that explains the rule + how to act on it.
FLAG_DISPLAY: dict[str, dict[str, str]] = {
    "zero_mwp_with_capacity": {
        "icon": "🔴",
        "title": "ZERO ROOFTOP — operating plant has no detected buildings",
        "rule": (
            "Capacity > 0 but rooftop_MWp ≈ 0. Either GoB v3 missed the plant "
            "(RV7 data freshness gap) or the centroid is still wrong."
        ),
        "fix": "Visual verification — run scripts/visual_sanity_check.py.",
        "priority": "actionable",
    },
    "sector_outlier_above": {
        "icon": "🔴",
        "title": "SECTOR OUTLIER (above) — possible residential bleed",
        "rule": (
            "MWp/kt ratio is >2σ ABOVE sector median. Common causes: "
            "residential bleed surviving the RV11 filter, panel-on-quarry-pit "
            "misidentification, or polygon clip not tight enough."
        ),
        "fix": "Visual check; tighten polygon or add to OSM exclusions.",
        "priority": "actionable",
    },
    "sector_outlier_below": {
        "icon": "🔴",
        "title": "SECTOR OUTLIER (below) — possible undercount",
        "rule": (
            "MWp/kt ratio is >2σ BELOW sector median. GoB v3 likely missed "
            "buildings (RV7) or RV11 over-clipped."
        ),
        "fix": "Cross-check with footprint band findings — same root cause.",
        "priority": "actionable",
    },
    "footprint_below_band": {
        "icon": "🟡",
        "title": "LOW FOOTPRINT — polygon coverage <5%",
        "rule": (
            "Building footprint is below 5% of the fence-boundary polygon — "
            "the plant is likely under-detected."
        ),
        "fix": "Cross-check with zero_mwp findings — same root cause.",
        "priority": "review",
    },
    "footprint_above_band": {
        "icon": "🟡",
        "title": "HIGH FOOTPRINT — polygon coverage >30%",
        "rule": (
            "Building footprint exceeds 30% of polygon — either residential "
            "bleed surviving RV11, or the polygon is too tight."
        ),
        "fix": "Visual check — extend polygon or add exclusions.",
        "priority": "review",
    },
    "sector_sample_too_small": {
        "icon": "ℹ ",
        "title": "MANUAL REVIEW — sector too small for z-score",
        "rule": (
            "Need at least the configured min sample to form a reliable band. "
            "These sectors pass through unchecked."
        ),
        "fix": "Eyeball the values manually; defer until sector grows.",
        "priority": "info",
    },
    "ms_gmlbf_reveals_buildings": {
        "icon": "🟢",
        "title": "RV7 FIX — MS GMLBF reveals buildings GoB missed",
        "rule": (
            "MS GMLBF added significantly more buildings than GoB v3 saw — "
            "confirms the RV7 GoB-undercount pattern (Cemindo Bayah, "
            "Hongshi, IWIP). Multi-source merge has filled the gap."
        ),
        "fix": "No action — informational. Validates the multi-source path.",
        "priority": "info",
    },
}


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
                "priority": FLAG_DISPLAY["zero_mwp_with_capacity"]["priority"],
                "site_id": row["site_id"],
                "site_name": row["site_name"],
                "sector": row["sector"],
                "capacity_kt": round(row["capacity_kt"], 1),
                "rooftop_mwp": round(row["rooftop_solar_mwp_potential"], 3),
                "reason": (
                    f"capacity {row['capacity_kt']:.1f} kt/yr but rooftop_MWp "
                    f"≈ 0 — likely RV7 (GoB undercount) or wrong centroid"
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
                    "priority": FLAG_DISPLAY["sector_sample_too_small"]["priority"],
                    "site_id": None,
                    "site_name": None,
                    "sector": sector,
                    "n": int(len(grp)),
                    "reason": (
                        f"only {len(grp)} sites — need ≥{EVAL_SECTOR_MIN_SAMPLE} "
                        f"for a reliable z-score band"
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
            if abs(zval) <= EVAL_SECTOR_ZSCORE_THRESHOLD:
                continue
            row = grp.loc[idx]
            # Direction matters — above sector = bleed/overcount; below = undercount.
            # Different root cause, different fix, so they get distinct flag types.
            check = "sector_outlier_above" if zval > 0 else "sector_outlier_below"
            sign = "+" if zval > 0 else "−"
            findings.append(
                {
                    "check": check,
                    "priority": FLAG_DISPLAY[check]["priority"],
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "sector": sector,
                    "mwp_per_kt": round(row["mwp_per_kt"], 4),
                    "sector_median_mwp_per_kt": round(median, 4),
                    "z_score": round(float(zval), 2),
                    "reason": (
                        f"ratio {row['mwp_per_kt']:.3f} is {sign}{abs(zval):.1f}σ "
                        f"vs sector median {median:.3f} (n={len(grp)})"
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
                    "priority": FLAG_DISPLAY["footprint_below_band"]["priority"],
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "footprint_m2": round(footprint_m2, 0),
                    "polygon_m2": round(polygon_area_m2, 0),
                    "ratio": round(ratio, 4),
                    "reason": (
                        f"footprint {ratio * 100:.1f}% of polygon "
                        f"({footprint_m2:,.0f} / {polygon_area_m2:,.0f} m²)"
                    ),
                }
            )
        elif ratio > EVAL_FOOTPRINT_RATIO_HIGH:
            findings.append(
                {
                    "check": "footprint_above_band",
                    "priority": FLAG_DISPLAY["footprint_above_band"]["priority"],
                    "site_id": row["site_id"],
                    "site_name": row["site_name"],
                    "footprint_m2": round(footprint_m2, 0),
                    "polygon_m2": round(polygon_area_m2, 0),
                    "ratio": round(ratio, 4),
                    "reason": (
                        f"footprint {ratio * 100:.1f}% of polygon "
                        f"({footprint_m2:,.0f} / {polygon_area_m2:,.0f} m²)"
                    ),
                }
            )
    return findings, n_covered, len(eligible)


def check_cross_source_audit(
    gob_path: Path | None = None,
    ms_path: Path | None = None,
    iou_threshold: float = CROSS_SOURCE_IOU_THRESHOLD,
) -> list[dict[str, Any]]:
    """Compare GoB v3 and MS GMLBF building parquets per site.

    Flags sites where MS GMLBF reveals materially more buildings than GoB
    saw — direct confirmation of the RV7 fix (Cemindo Bayah pattern).

    Cleanly no-ops when MS parquet is absent (Phase 1 reality before the
    download lands). Returns [] silently in that case so the eval still
    runs end-to-end against single-source GoB data.

    Methodology: per site, build STRtree on GoB polygons, then for each
    MS polygon check whether any GoB neighbor has IoU > threshold. MS
    rows with no match are "net-new". Site flagged when net-new count
    exceeds both absolute (MS_REVEAL_MIN_NEW_BUILDINGS) and relative
    (MS_REVEAL_MIN_GAIN_FRACTION) gates.
    """
    findings: list[dict[str, Any]] = []
    # Resolve at call time so tests can monkeypatch the module-level paths.
    if gob_path is None:
        gob_path = GOB_PARQUET
    if ms_path is None:
        ms_path = MS_PARQUET
    if not gob_path.exists() or not ms_path.exists():
        return findings

    # Lazy imports — these libs are heavy and only used by this check.
    import geopandas as gpd  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415
    from shapely.strtree import STRtree  # noqa: PLC0415

    gob = gpd.read_parquet(gob_path)
    ms = gpd.read_parquet(ms_path)

    for site_id, ms_grp in ms.groupby("site_id"):
        gob_grp = gob[gob["site_id"] == site_id]
        gob_count = len(gob_grp)
        ms_count = len(ms_grp)
        if ms_count == 0:
            continue

        # Count MS buildings with no IoU match in GoB → net-new buildings.
        if gob_count == 0:
            net_new = ms_count
        else:
            gob_geoms = list(gob_grp.geometry.to_numpy())
            gob_areas = np.array([g.area for g in gob_geoms])
            tree = STRtree(gob_geoms)
            net_new = 0
            for sg in ms_grp.geometry.to_numpy():
                sa = sg.area
                if sa <= 0:
                    continue
                cand_idx = tree.query(sg)
                matched = False
                for j in cand_idx:
                    pg = gob_geoms[int(j)]
                    inter = sg.intersection(pg).area
                    if inter <= 0:
                        continue
                    union = sa + gob_areas[int(j)] - inter
                    if union > 0 and (inter / union) >= iou_threshold:
                        matched = True
                        break
                if not matched:
                    net_new += 1

        # Two gates — absolute count + fractional gain — to cut noise.
        gain_fraction = net_new / max(gob_count, 1)
        if net_new >= MS_REVEAL_MIN_NEW_BUILDINGS and gain_fraction >= MS_REVEAL_MIN_GAIN_FRACTION:
            site_name_match = ms_grp["site_id"].iloc[0]
            findings.append(
                {
                    "check": "ms_gmlbf_reveals_buildings",
                    "priority": "info",
                    "site_id": site_id,
                    "site_name": site_name_match,
                    "gob_count": int(gob_count),
                    "ms_count": int(ms_count),
                    "net_new": int(net_new),
                    "gain_fraction": round(gain_fraction, 2),
                    "reason": (
                        f"MS GMLBF added {net_new} buildings (×{gain_fraction:.1f} "
                        f"of GoB count {gob_count}) that GoB v3 missed"
                    ),
                }
            )

    return findings


def format_report(
    findings: list[dict[str, Any]],
    poly_coverage: tuple[int, int],
) -> str:
    """Console output grouped by flag type.

    Each group is a self-contained block: icon + title + 1-line rule + 1-line
    fix + the findings themselves. Unknown check names (shouldn't happen but
    defensive) are appended at the end with no header.

    Backward compat: still prints the "HIGH-PRIORITY" header at the top so
    existing tests that grep for it still pass.
    """
    n_covered, n_total = poly_coverage
    actionable = [f for f in findings if f.get("priority") == "actionable"]
    review = [f for f in findings if f.get("priority") == "review"]
    info = [f for f in findings if f.get("priority") == "info"]

    lines: list[str] = []

    # Top-level summary line — the only place the user sees a count.
    n_act = len(actionable)
    n_rev = len(review)
    n_inf = len(info)
    if n_act:
        lines.append(f"🚨 HIGH-PRIORITY: {n_act} actionable finding(s)")
    else:
        lines.append("✅ No actionable findings.")
    if n_rev:
        lines.append(f"   plus {n_rev} sanity-check warning(s) and {n_inf} info note(s)")
    elif n_inf:
        lines.append(f"   plus {n_inf} info note(s)")
    lines.append("")

    # Render each flag type in FLAG_DISPLAY's declared order.
    for check, cfg in FLAG_DISPLAY.items():
        group = [f for f in findings if f.get("check") == check]
        if not group:
            continue
        lines.append(f"{cfg['icon']} {cfg['title']}  ({len(group)})")
        lines.append(f"    Rule: {cfg['rule']}")
        lines.append(f"    Fix:  {cfg['fix']}")
        lines.append("")
        for f in group:
            label = f.get("site_name") or f.get("sector") or f.get("site_id") or "?"
            lines.append(f"    • {label}  —  {f['reason']}")
        lines.append("")

    lines.append(f"Plant-area-band coverage: {n_covered}/{n_total} sites have a polygon")
    if n_covered < n_total:
        lines.append(
            f"  ({n_total - n_covered} sites pass through unchecked — "
            f"polygon needed to apply the area band)"
        )
    return "\n".join(lines)


def append_history(findings: list[dict[str, Any]]) -> None:
    """Append a single JSONL line per run for trend tracking.

    Defaults to outputs/data/eval/rooftop-history.jsonl (set in
    src/assumptions.py) — generated artifact, lives with other pipeline
    outputs. The path is configurable so tests can redirect it.
    """
    raw = Path(EVAL_HIST_PATH).expanduser()
    # Anchor relative paths to the repo root so the file lands in the same
    # place regardless of cwd. EVAL_HIST_PATH is configured as a relative
    # path in src/assumptions.py.
    path = raw if raw.is_absolute() else REPO_ROOT / raw
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = {
        "actionable": sum(1 for f in findings if f.get("priority") == "actionable"),
        "review": sum(1 for f in findings if f.get("priority") == "review"),
        "info": sum(1 for f in findings if f.get("priority") == "info"),
    }
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
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
    # Phase 4 cross-source check (RV7 fix confirmation). No-ops when MS
    # parquet is absent — single-source pipelines are unaffected.
    findings.extend(check_cross_source_audit())

    print(format_report(findings, (n_covered, n_total)))
    append_history(findings)

    n_actionable = sum(1 for f in findings if f.get("priority") == "actionable")
    return 1 if n_actionable > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
