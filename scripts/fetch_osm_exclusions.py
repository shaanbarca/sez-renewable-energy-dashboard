"""Fetch OSM polygons that should exclude buildings from rooftop counting.

Tags queried:
  man_made=storage_tank   — round/cylindrical industrial tanks (already
                            partially caught by §14 circularity, but irregular
                            outlines slip through)
  man_made=water_tank     — water reservoirs
  man_made=wastewater_plant — settling ponds, treatment facilities
  landuse=basin           — open-top settling / cooling ponds
  natural=water           — ponds, reservoirs
  man_made=reservoir_covered — covered reservoirs (low roof, not buildable)

For every site_id, query the bounding box of its dim_sites centroid + 2 km
(matches the preprocess buffer). Save to
`data/industrial_sites/exclusion_polygons.geojson` keyed by `site_id`.

Run:
    PYTHONPATH=. uv run python scripts/fetch_osm_exclusions.py

Rate-limited to Overpass policy (~1 req per few seconds).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
DIM_SITES = REPO_ROOT / "outputs" / "data" / "processed" / "dim_sites.csv"
OUT_FILE = REPO_ROOT / "data" / "industrial_sites" / "exclusion_polygons.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass QL: bbox-clipped query for all exclusion tags. Returns ways +
# relations with their geometry resolved. Wrap in `out geom;` for
# Overpass to inline coords on each member.
QUERY_TEMPLATE = """
[out:json][timeout:60];
(
  way["man_made"="storage_tank"]({s},{w},{n},{e});
  way["man_made"="water_tank"]({s},{w},{n},{e});
  way["man_made"="wastewater_plant"]({s},{w},{n},{e});
  way["man_made"="reservoir_covered"]({s},{w},{n},{e});
  way["landuse"="basin"]({s},{w},{n},{e});
  way["natural"="water"]({s},{w},{n},{e});
  relation["man_made"="storage_tank"]({s},{w},{n},{e});
  relation["man_made"="wastewater_plant"]({s},{w},{n},{e});
  relation["landuse"="basin"]({s},{w},{n},{e});
  relation["natural"="water"]({s},{w},{n},{e});
);
out geom;
"""

BBOX_KM = 2.5  # Match the preprocess buffer + slight padding for edge polygons


def bbox_around(lat: float, lon: float, km: float = BBOX_KM) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) bbox around (lat, lon)."""
    import math

    deg_per_km_lat = 1 / 110.574
    deg_per_km_lon = 1 / (111.320 * math.cos(math.radians(lat)))
    return (
        lat - km * deg_per_km_lat,
        lon - km * deg_per_km_lon,
        lat + km * deg_per_km_lat,
        lon + km * deg_per_km_lon,
    )


MIN_RING_POINTS = 4  # Closed polygon ring needs ≥4 points (3 corners + close)


def way_to_polygon_coords(way: dict) -> list | None:
    """Convert an Overpass 'way' element with inlined geometry to a GeoJSON
    polygon coordinate ring. Skips open ways (lines, not polygons)."""
    geom = way.get("geometry") or []
    if len(geom) < MIN_RING_POINTS:
        return None
    coords = [[pt["lon"], pt["lat"]] for pt in geom]
    if coords[0] != coords[-1]:
        # Open way — close it. Most landuse=basin / natural=water are closed
        # in OSM, but be defensive.
        coords.append(coords[0])
    return coords


HEADERS = {"User-Agent": "eez-rooftop-research/1.0 (centroid+exclusion validator)"}


def fetch_for_site(lat: float, lon: float) -> list[dict]:
    bbox = bbox_around(lat, lon)
    q = QUERY_TEMPLATE.format(s=bbox[0], w=bbox[1], n=bbox[2], e=bbox[3])
    r = requests.post(OVERPASS_URL, data={"data": q}, headers=HEADERS, timeout=120)
    r.raise_for_status()
    elements = r.json().get("elements", [])

    polygons = []
    for el in elements:
        if el.get("type") != "way":
            # Relations need a separate geometry resolver; skip for now
            # — most basin/water in Indonesia are tagged as ways.
            continue
        ring = way_to_polygon_coords(el)
        if ring is None:
            continue
        tags = el.get("tags", {})
        polygons.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "osm_id": el.get("id"),
                    "tag_class": next(
                        (k for k in ("man_made", "landuse", "natural") if k in tags),
                        "unknown",
                    ),
                    "tag_value": tags.get("man_made") or tags.get("landuse") or tags.get("natural"),
                    "tags": tags,
                },
            }
        )
    return polygons


def main() -> int:
    sites = pd.read_csv(DIM_SITES)
    print(f"Querying Overpass for exclusion polygons in {len(sites)} site bboxes...")

    all_features: list[dict] = []
    for i, s in enumerate(sites.itertuples(index=False), start=1):
        print(f"  [{i:>2}/{len(sites)}] {s.site_id:<40} ", end="", flush=True)
        try:
            polys = fetch_for_site(s.latitude, s.longitude)
        except requests.HTTPError as e:
            print(f"  HTTP error {e.response.status_code} — backing off 30s")
            time.sleep(30)
            try:
                polys = fetch_for_site(s.latitude, s.longitude)
            except Exception as e2:  # noqa: BLE001
                print(f"  failed twice: {e2!r}")
                polys = []
        except Exception as e:  # noqa: BLE001
            print(f"  err: {e!r}")
            polys = []

        for p in polys:
            p["properties"]["site_id"] = s.site_id
        all_features.extend(polys)
        print(f"{len(polys)} polygons")
        # Overpass policy: throttle. ~1 req per 2-3s is courteous.
        time.sleep(2.5)

    out = {"type": "FeatureCollection", "features": all_features}
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(out))
    print(f"\nWrote {len(all_features)} exclusion polygons → {OUT_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
