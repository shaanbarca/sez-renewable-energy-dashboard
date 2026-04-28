"""RV13 — Centroid land-cover validator.

Samples ESA WorldCover v200 at each site centroid in dim_sites.csv and
flags sites whose centroid lands on land cover that is implausible for
an operating industrial facility (water, dense forest, mangrove, wetland).

This catches the GEM tracker miscoding pattern (Semen Gresik Tuban
offshore in the Java Sea, Red Lion Hongshi in jungle, Indocement
Palimanan in forest before fix, etc.) automatically across the whole
81-site set.

Usage:
    PYTHONPATH=. uv run python scripts/validate_centroids.py

Exit code 0 when no suspect centroids found, non-zero otherwise — so
this is CI-friendly.

ESA WorldCover v200 class codes:
    10 = Tree cover                     (suspect for industrial)
    20 = Shrubland                      (ambiguous)
    30 = Grassland                      (ambiguous)
    40 = Cropland                       (ambiguous — plant edge OK)
    50 = Built-up                       (OK — settlements / industrial)
    60 = Bare / sparse vegetation       (OK — quarry / kiln area)
    70 = Snow and ice                   (suspect)
    80 = Permanent water bodies         (suspect — definite miss)
    90 = Herbaceous wetland             (suspect — peat / swamp)
    95 = Mangroves                      (suspect — definite miss)
   100 = Moss and lichen                (suspect)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import rasterio

REPO_ROOT = Path(__file__).resolve().parent.parent
DIM_SITES = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
WORLDCOVER = REPO_ROOT / "data" / "buildability" / "esa_worldcover.vrt"

CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

# Land cover codes that are implausible for an operating industrial plant
# centroid. A correct GEM tracker geocode SHOULD land on built-up (50),
# bare ground (60, quarries / kilns), or rarely cropland edge (40).
SUSPECT_CODES: set[int] = {10, 70, 80, 90, 95, 100}


def sample_worldcover(lat: float, lon: float, ds) -> int | None:
    """Read the WorldCover class at (lat, lon). Returns None if outside extent."""
    try:
        for val in ds.sample([(lon, lat)]):
            return int(val[0])
    except (IndexError, ValueError):
        return None
    return None


def has_industrial_neighbor(lat: float, lon: float, ds, radius_m: float = 500.0) -> bool:
    """Check if there's any built-up (50) or bare (60) pixel within `radius_m`
    of the centroid. WorldCover v200 vintage is 2021 — quarries / plants built
    or expanded after that date often show as tree-cover at their centroid
    even though neighboring pixels are correctly classified as built-up.
    """
    import math

    # Convert metres → degrees (rough, fine at site scale)
    deg_per_m_lat = 1 / 111_320
    deg_per_m_lon = 1 / (111_320 * math.cos(math.radians(lat)))
    dlat = radius_m * deg_per_m_lat
    dlon = radius_m * deg_per_m_lon

    # Sample a 3×3 grid offset by ±radius_m
    INDUSTRIAL_CODES = {50, 60}
    points = [
        (lon + dx * dlon, lat + dy * dlat)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if (dx, dy) != (0, 0)
    ]
    try:
        for val in ds.sample(points):
            if int(val[0]) in INDUSTRIAL_CODES:
                return True
    except (IndexError, ValueError):
        return False
    return False


def main() -> int:
    if not WORLDCOVER.exists():
        print(f"WorldCover VRT not found at {WORLDCOVER}", file=sys.stderr)
        print(
            "Run: scripts/download_buildability_data.py to fetch the layer.",
            file=sys.stderr,
        )
        return 2

    sites = pd.read_csv(DIM_SITES)
    print(f"Validating {len(sites)} site centroids against ESA WorldCover...\n")

    suspect_rows = []
    with rasterio.open(WORLDCOVER) as ds:
        for _, s in sites.iterrows():
            code = sample_worldcover(s["latitude"], s["longitude"], ds)
            if code is None:
                continue
            if code in SUSPECT_CODES:
                neighbor_industrial = has_industrial_neighbor(s["latitude"], s["longitude"], ds)
                suspect_rows.append(
                    {
                        "site_id": s["site_id"],
                        "site_name": s["site_name"],
                        "site_type": s["site_type"],
                        "sector": s["sector"],
                        "lat": s["latitude"],
                        "lon": s["longitude"],
                        "lc_code": code,
                        "lc_name": CLASS_NAMES.get(code, f"Unknown ({code})"),
                        "industrial_within_500m": neighbor_industrial,
                    }
                )

    if not suspect_rows:
        print("All site centroids land on plausible industrial land cover.")
        return 0

    df = pd.DataFrame(suspect_rows).sort_values(["industrial_within_500m", "lc_code", "site_name"])

    # Two tiers: HIGH-PRIORITY (no industrial within 500 m) vs LOWER-PRIORITY
    # (industrial nearby — often a stale-WorldCover false positive).
    high = df[~df["industrial_within_500m"]]
    low = df[df["industrial_within_500m"]]

    if len(high):
        print(
            f"🚨 HIGH-PRIORITY: {len(high)} site centroid(s) with NO built-up "
            "or bare pixels within 500 m:\n"
        )
        pd.set_option("display.width", 200)
        pd.set_option("display.max_colwidth", 60)
        print(high.drop(columns=["industrial_within_500m"]).to_string(index=False))
        print()

    if len(low):
        print(
            f"ℹ LOWER-PRIORITY: {len(low)} site centroid(s) with industrial / "
            "bare pixels nearby (often stale WorldCover, but visually verify):\n"
        )
        print(low.drop(columns=["industrial_within_500m"]).to_string(index=False))

    print(
        "\nNext: visually inspect each via scripts/visual_sanity_check.py "
        "(add the site_id to SUSPECT_SITES) and add an override to "
        "data/industrial_sites/coordinate_overrides.csv if confirmed wrong."
    )
    return 1 if len(high) else 0


if __name__ == "__main__":
    sys.exit(main())
