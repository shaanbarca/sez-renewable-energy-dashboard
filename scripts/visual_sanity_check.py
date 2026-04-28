"""Render per-site satellite imagery with detected GoB v3 building polygons
overlaid, so we can visually categorize undercounted sites:
  (a) GoB v3 missed them (RV7 — data freshness / coverage gap)
  (b) Centroid is wrong (geocoded to head-office, not the plant)
  (c) Threshold dropped them (still possible despite 80% precision pass)

Output: outputs/data/visual_qa/<site_id>.png
        Each image: 1024x768, satellite base, detected polygons in red outline.

Run:
    PYTHONPATH=. uv run python scripts/visual_sanity_check.py
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import requests
from PIL import Image
from shapely import wkb

REPO_ROOT = Path(__file__).resolve().parent.parent
SITES_CSV = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
PARQUET = REPO_ROOT / "data" / "processed" / "sites_buildings_filtered.parquet"
OUT_DIR = REPO_ROOT / "outputs" / "data" / "visual_qa"
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

# Sites to investigate. (site_id, label, expected_finding)
SUSPECT_SITES = [
    ("indocement-citeureup", "Indocement Citeureup", "12 Mt/yr — should be huge"),
    ("semen-gresik-tuban", "Semen Gresik Tuban", "15 Mt/yr, only 13 MWp"),
    ("indocement-palimanan", "Indocement Palimanan", "3.6 Mt/yr, 1.8 MWp"),
    ("sbi-narogong", "SBI Narogong", "6.06 Mt/yr, 2.95 MWp"),
    ("red-lion-hongshi-tonga", "Red Lion Hongshi Tonga", "4 Mt/yr, 0 MWp"),
    ("cemindo-gemilang-bayah", "Cemindo Gemilang Bayah", "3.5 Mt/yr, 0 MWp"),
    ("krakatau-steel-cilegon", "Krakatau Steel Cilegon", "4 Mt/yr, 75 MWp — should be more"),
    ("pupuk-iskandar-muda-lhokseumawe", "Pupuk Iskandar Muda", "1.14 Mt/yr fertilizer, 0 MWp"),
    ("ispat-indo-sidoarjo", "Ispat Indo Sidoarjo", "39,635 bldgs — bleed-in?"),
    # Baselines — look-correct sites
    ("master-steel-jakarta", "Master Steel Jakarta (BASELINE)", "195 MWp — looks right"),
    ("semen-gresik-city", "Semen Gresik City (BASELINE)", "108 MWp — looks right"),
]


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
    import math

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

    # Right pane: overlay the detected polygons
    in_view = buildings_in_box[
        (buildings_in_box["longitude"] >= extent[0])
        & (buildings_in_box["longitude"] <= extent[1])
        & (buildings_in_box["latitude"] >= extent[2])
        & (buildings_in_box["latitude"] <= extent[3])
    ].copy()

    for _, b in in_view.iterrows():
        try:
            geom = wkb.loads(b["geometry"])
            xs, ys = geom.exterior.xy
            axes[1].fill(xs, ys, color="red", alpha=0.45, zorder=5)
            axes[1].plot(xs, ys, color="red", linewidth=0.6, zorder=6)
        except Exception:
            continue

    axes[1].set_title(
        f"GoB-detected buildings (red) — {len(in_view):,} in view  /  raw {raw_count:,} total assigned to site",
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


def main():
    sites = pd.read_csv(SITES_CSV)
    buildings = pd.read_parquet(PARQUET)
    fct = pd.read_csv(REPO_ROOT / "outputs" / "data" / "processed" / "fct_site_solar_potential.csv")

    for site_id, label, note in SUSPECT_SITES:
        site_row = sites[sites["site_id"] == site_id]
        if not len(site_row):
            print(f"SKIP {site_id}: not in dim_sites")
            continue
        s = site_row.iloc[0]
        site_buildings = buildings[buildings["site_id"] == site_id]
        rooftop = fct[fct["site_id"] == site_id]["rooftop_solar_mwp_potential"].iloc[0]
        out = render(
            site_id=site_id,
            site_name=label,
            note=note,
            lat=s["latitude"],
            lon=s["longitude"],
            buildings_in_box=site_buildings,
            rooftop_mwp=rooftop,
            raw_count=len(site_buildings),
        )
        print(f"  {label:<40}  {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
