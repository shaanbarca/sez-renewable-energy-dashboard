"""Render per-site satellite imagery for sites flagged by the rooftop eval.

The companion to scripts/eval_rooftop_accuracy.py. The eval surfaces sites
that look statistically/physically off (zero rooftop, sector outliers,
footprint-band hits); this script renders satellite + detected-polygon
images for those exact sites so the human reviewer can categorize each:
  (a) GoB v3 missed them (RV7 — data freshness / coverage gap)
  (b) Centroid is wrong (geocoded to head-office, not the plant)
  (c) Residential bleed survived RV11
  (d) Polygon clip is too tight/loose

The site list is data-driven from the latest record in
outputs/data/eval/rooftop-history.jsonl — no hardcoded SUSPECT_SITES.
Each site gets one image, even if it has multiple findings; all flag
reasons are shown in the title.

Output: outputs/data/visual_qa/<site_id>.png
        Each image: 1024x768, satellite base, detected polygons in red,
        residential-cluster filtered buildings in gray.

Run:
    PYTHONPATH=. uv run python scripts/eval_rooftop_accuracy.py  # writes JSONL
    PYTHONPATH=. uv run python scripts/visual_sanity_check.py    # renders flagged sites

CLI: pass --site-ids a,b,c to force-render specific sites instead of the
eval-flagged set (useful for verifying baselines or fix-targets).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from PIL import Image
from shapely import wkb

from src.pipeline.build_fct_site_solar_potential import detect_residential_clusters

PROJECTED_CRS = "EPSG:23830"

REPO_ROOT = Path(__file__).resolve().parent.parent
SITES_CSV = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
PARQUET = REPO_ROOT / "data" / "processed" / "sites_buildings_filtered.parquet"
OUT_DIR = REPO_ROOT / "outputs" / "data" / "visual_qa"
EVAL_HISTORY = REPO_ROOT / "outputs" / "data" / "eval" / "rooftop-history.jsonl"
FCT_ROOFTOP = REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_solar_potential.csv"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Read MAPBOX_TOKEN from env or .env
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")
if not MAPBOX_TOKEN:
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("MAPBOX_TOKEN="):
                MAPBOX_TOKEN = line.split("=", 1)[1].strip()
                break
assert MAPBOX_TOKEN, "MAPBOX_TOKEN not found in env or .env"

# Icon per check name — kept in sync with FLAG_DISPLAY in eval_rooftop_accuracy.py
# (not imported because the eval script lives alongside this one and a relative
# import would couple the two; this map is small enough to maintain in two places).
# ASCII tokens used because matplotlib's default DejaVu Sans doesn't render
# the 🟡 LARGE YELLOW CIRCLE glyph and emits warnings for every figure.
FLAG_ICONS: dict[str, str] = {
    "zero_mwp_with_capacity": "[!]",
    "sector_outlier_above": "[!]",
    "sector_outlier_below": "[!]",
    "footprint_below_band": "[?]",
    "footprint_above_band": "[?]",
    "sector_sample_too_small": "[i]",
}


def fetch_satellite(
    lat: float, lon: float, zoom: int = 15, w: int = 800, h: int = 600
) -> Image.Image:
    """Mapbox satellite tile centered on the site."""
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{w}x{h}@2x"
        f"?access_token={MAPBOX_TOKEN}"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def render(  # noqa: PLR0913
    site_id: str,
    site_name: str,
    note: str,
    lat: float,
    lon: float,
    buildings_in_box: pd.DataFrame,
    rooftop_mwp: float,
    raw_count: int,
):
    """Render: left = satellite-only, right = same satellite + building polygons."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    sat = fetch_satellite(lat, lon, zoom=15)
    # Compute extent of the satellite image so polygons line up.
    # Mapbox Web Mercator math: at zoom z, pixel resolution at lat is
    # 156543.03 * cos(lat) / 2^z metres per pixel (at retina/2x: half that).
    z = 15
    px_size_m = 156543.03 * math.cos(math.radians(lat)) / (2**z) / 2  # @2x
    img_w_m = sat.width * px_size_m
    img_h_m = sat.height * px_size_m
    # ° per metre (rough) — 1° lat ≈ 111,320 m
    deg_per_m_lat = 1 / 111_320
    deg_per_m_lon = 1 / (111_320 * math.cos(math.radians(lat)))
    extent = (
        lon - (img_w_m / 2) * deg_per_m_lon,
        lon + (img_w_m / 2) * deg_per_m_lon,
        lat - (img_h_m / 2) * deg_per_m_lat,
        lat + (img_h_m / 2) * deg_per_m_lat,
    )

    for ax in axes:
        ax.imshow(sat, extent=extent, origin="upper")
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.scatter([lon], [lat], color="cyan", s=120, marker="x", linewidths=2.5, zorder=10)
        ax.set_xticks([])
        ax.set_yticks([])

    axes[0].set_title("Satellite (centroid = cyan ×)", fontsize=11)

    # Right pane: overlay the detected polygons, with residential-cluster
    # buildings shown in gray (filtered out by RV11) vs red (counted).
    in_view = buildings_in_box[
        (buildings_in_box["longitude"] >= extent[0])
        & (buildings_in_box["longitude"] <= extent[1])
        & (buildings_in_box["latitude"] >= extent[2])
        & (buildings_in_box["latitude"] <= extent[3])
    ].copy()

    # Residential detection runs on the FULL site-buildings set (need
    # neighborhood context), not just the in-view subset.
    is_residential_full = np.zeros(len(buildings_in_box), dtype=bool)
    if len(buildings_in_box):
        geoms_full = [wkb.loads(g) for g in buildings_in_box["geometry"]]
        gdf_full = gpd.GeoDataFrame(
            buildings_in_box.reset_index(drop=True),
            geometry=geoms_full,
            crs="EPSG:4326",
        ).to_crs(PROJECTED_CRS)
        is_residential_full = detect_residential_clusters(gdf_full)

    n_res_view = 0
    n_kept_view = 0
    # Map from buildings_in_box position → in_view position
    buildings_in_box_reset = buildings_in_box.reset_index(drop=True)
    in_view_ids = set(in_view.index)
    for pos, (_, b) in enumerate(buildings_in_box_reset.iterrows()):
        if b.name not in in_view_ids and pos not in in_view_ids:
            # iterating buildings_in_box, but we only want to plot in_view
            pass
        # Fallback: just plot buildings whose lat/lon land in extent
        lat = b["latitude"]
        lon = b["longitude"]
        if not (extent[0] <= lon <= extent[1] and extent[2] <= lat <= extent[3]):
            continue
        try:
            geom = wkb.loads(b["geometry"])
            xs, ys = geom.exterior.xy
            if is_residential_full[pos]:
                axes[1].fill(xs, ys, color="lightgray", alpha=0.4, zorder=4)
                axes[1].plot(xs, ys, color="gray", linewidth=0.4, zorder=5)
                n_res_view += 1
            else:
                axes[1].fill(xs, ys, color="red", alpha=0.55, zorder=6)
                axes[1].plot(xs, ys, color="darkred", linewidth=0.6, zorder=7)
                n_kept_view += 1
        except Exception:
            continue

    axes[1].set_title(
        f"Counted (red) {n_kept_view:,}  /  residential-filtered (gray) {n_res_view:,}"
        f"   in view ({len(in_view):,})  •  site total {raw_count:,}",
        fontsize=11,
    )

    fig.suptitle(
        f"{site_name}    →    rooftop_solar_mwp_potential = {rooftop_mwp:.2f} MWp\n{note}",
        fontsize=12,
        y=0.98,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out_path = OUT_DIR / f"{site_id}.png"
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return out_path


def load_latest_eval() -> dict[str, Any]:
    """Read the last record from outputs/data/eval/rooftop-history.jsonl.

    Raises FileNotFoundError with a hint if the eval hasn't been run yet —
    the visual check is downstream of the eval, not a standalone tool.
    """
    if not EVAL_HISTORY.exists():
        msg = (
            f"Missing {EVAL_HISTORY} — run "
            f"`PYTHONPATH=. uv run python scripts/eval_rooftop_accuracy.py` first."
        )
        raise FileNotFoundError(msg)
    last_record: dict[str, Any] | None = None
    with EVAL_HISTORY.open() as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                last_record = json.loads(stripped)
    if last_record is None:
        msg = f"{EVAL_HISTORY} is empty — eval has never run successfully."
        raise ValueError(msg)
    return last_record


def group_findings_by_site(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group findings by site_id. Sector-level findings (no site_id) are dropped —
    they have no site to render."""
    by_site: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        sid = f.get("site_id")
        if not sid:
            continue
        by_site.setdefault(sid, []).append(f)
    return by_site


def compose_note(findings: list[dict[str, Any]]) -> str:
    """Build a multi-line title note from one site's findings.

    Each finding becomes one line: icon + flag_name + reason. Most sites
    have 1 finding; under-detected ones often have 2 (zero_mwp_with_capacity
    AND footprint_below_band — same root cause, both worth seeing).
    """
    lines = []
    for f in findings:
        check = f.get("check", "?")
        icon = FLAG_ICONS.get(check, "•")
        reason = f.get("reason", "")
        lines.append(f"{icon} [{check}]  {reason}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    p.add_argument(
        "--site-ids",
        type=str,
        default=None,
        help=(
            "Comma-separated site_ids to render instead of the eval-flagged "
            "set. Useful for verifying a baseline or a known fix-target."
        ),
    )
    return p.parse_args()


def main():
    args = parse_args()
    sites = pd.read_csv(SITES_CSV)
    buildings = pd.read_parquet(PARQUET)
    fct = pd.read_csv(FCT_ROOFTOP)

    if args.site_ids:
        # Ad-hoc mode: render specific sites with no eval context.
        target_site_ids = [sid.strip() for sid in args.site_ids.split(",") if sid.strip()]
        by_site: dict[str, list[dict[str, Any]]] = {sid: [] for sid in target_site_ids}
        print(f"Rendering {len(by_site)} site(s) from --site-ids (no eval context).")
    else:
        # Default mode: read latest eval record, render every flagged site.
        record = load_latest_eval()
        counts = record.get("counts", {})
        by_site = group_findings_by_site(record.get("findings", []))
        print(
            f"Rendering {len(by_site)} flagged site(s) from latest eval "
            f"(actionable={counts.get('actionable', 0)}, "
            f"review={counts.get('review', 0)}, info={counts.get('info', 0)})."
        )

    for site_id, findings in by_site.items():
        site_row = sites[sites["site_id"] == site_id]
        if not len(site_row):
            print(f"  SKIP {site_id}: not in dim_sites")
            continue
        s = site_row.iloc[0]
        site_buildings = buildings[buildings["site_id"] == site_id]
        rooftop_match = fct[fct["site_id"] == site_id]["rooftop_solar_mwp_potential"]
        rooftop = float(rooftop_match.iloc[0]) if len(rooftop_match) else 0.0
        note = compose_note(findings) if findings else "(ad-hoc render — no eval finding)"
        # If the site has multiple findings, suffix the count for at-a-glance scan.
        site_label = s["site_name"]
        if len(findings) > 1:
            site_label = f"{site_label}  ({len(findings)} findings)"
        out = render(
            site_id=site_id,
            site_name=site_label,
            note=note,
            lat=s["latitude"],
            lon=s["longitude"],
            buildings_in_box=site_buildings,
            rooftop_mwp=rooftop,
            raw_count=len(site_buildings),
        )
        flag_summary = ",".join(f.get("check", "?") for f in findings) or "ad-hoc"
        print(f"  {site_label:<48}  [{flag_summary}]  {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
