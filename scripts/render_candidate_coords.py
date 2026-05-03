"""Render satellite imagery at arbitrary candidate (lat, lon) coordinates.

Companion to `scripts/visual_sanity_check.py`:
  visual_sanity_check  → verifies sites that ARE in dim_sites
  render_candidate_coords → tries new candidate coords BEFORE adding them
                            to dim_sites or coordinate_overrides.csv

Used when hunting down a wrong GEM tracker centroid:
  1. WebSearch for the actual plant address (village, district)
  2. Mapbox geocode the address → get (lat, lon)
  3. Add the candidates to CANDIDATES below + run this
  4. Eyeball the rendered PNGs to pick the one showing actual plant
  5. Add the verified coord to data/industrial_sites/coordinate_overrides.csv

Output (gitignored): outputs/data/visual_qa/candidates/<site_id>.png
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import matplotlib.pyplot as plt
import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "outputs" / "data" / "visual_qa" / "candidates"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MAPBOX_TOKEN = (
    os.environ.get("MAPBOX_TOKEN")
    or open(REPO_ROOT / ".env").read().split("MAPBOX_TOKEN=")[1].split("\n")[0].strip()
)

# Edit this dict per hunt. Each value is a list of (lat, lon, label) tuples.
# The script renders a side-by-side grid per site_id key.
# Current hunt (2026-04-30): Jakarta Prima Steel Industries — visual showed
# centroid in residential, plant upper-left of frame. Two OSM candidates.
CANDIDATES: dict[str, list[tuple[float, float, str]]] = {
    # 2026-05-03 round 3 — vision audit of urban over-counter risks.
    # All 6 sites have the highest current rooftop_MWp in the fleet but no
    # fence-line polygon, so the 2 km buffer is bleeding in neighboring
    # factories. Need to trace fence boundaries from satellite.
    "master-steel-jakarta": [
        (-6.184210, 106.920067, "current-dimsites"),
    ],
    "pupuk-sriwidjaja-palembang": [
        (-2.990000, 104.757000, "current-dimsites"),
    ],
    "jakarta-prima-steel-industries": [
        (-6.181643, 106.932331, "current-dimsites"),
    ],
    "indocement-citeureup": [
        (-6.479811, 106.899118, "current-dimsites"),
    ],
    "pupuk-kujang-cikampek": [
        (-6.410000, 107.457000, "current-dimsites"),
    ],
    "krakatau-steel-cilegon": [
        (-6.007021, 106.001766, "current-dimsites"),
    ],
}

ZOOM = 16  # higher = more zoomed in. Drop to 13 for region-scan, 17 for plant detail.


def fetch_sat(lat: float, lon: float, zoom: int = ZOOM, w: int = 800, h: int = 600) -> Image.Image:
    url = (
        f"https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static/"
        f"{lon},{lat},{zoom},0/{w}x{h}@2x?access_token={MAPBOX_TOKEN}"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def main() -> None:
    for site_id, candidates in CANDIDATES.items():
        if not candidates:
            continue
        n = len(candidates)
        fig, axes = plt.subplots(1, n, figsize=(8 * n, 7))
        if n == 1:
            axes = [axes]
        for ax, (lat, lon, label) in zip(axes, candidates, strict=False):
            sat = fetch_sat(lat, lon)
            ax.imshow(sat)
            ax.set_title(f"{label}\n({lat:.4f}, {lon:.4f})", fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
        fig.suptitle(f"Candidates — {site_id}")
        out = OUT_DIR / f"{site_id}.png"
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(out, dpi=110, bbox_inches="tight")
        plt.close(fig)
        print(f"  {site_id} -> {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
