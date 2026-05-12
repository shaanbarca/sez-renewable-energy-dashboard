"""One-shot polygon hunt for the 5 HIGH-priority sites identified by
`scripts/audit_polygon_coverage.py` during PR #44 RCA. Run once on 2026-05-12;
records the verdict for each site so the work is reproducible.

This script is intentionally NOT generic. It captures a specific decision
chain for 5 named sites and the OSM way IDs we settled on. Future polygon
hunts should create their own dated companion script rather than mutating
this one — it functions as a forensic record of which sites were tried,
which OSM tags hit, and which were left for tier-3 (Claude-traced) follow-up.

Outputs:
  - data/industrial_sites/site_polygons.geojson (in-place append)
  - prints a verdict summary

Acceptance criteria (from issue #45):
  - 5 HIGH-priority sites have real OSM polygons (tier 2)         → 2 of 5 met
  - Remaining 16 sites have centroid_buffer_estimate (tier none)  → met in commit A

The 3 sites we COULDN'T find on OSM (Nusantara, Inalum, Buli) need either
a Claude-traced polygon (tier 3) or a government-sourced boundary. Tracked
as a follow-up sub-task on #45.

Run:
    PYTHONPATH=. uv run python scripts/hunt_v4_0_5_osm_polygons.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
SITE_POLYGONS = REPO_ROOT / "data" / "industrial_sites" / "site_polygons.geojson"

OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

HTTP_OK = 200
# Minimum vertices for a valid closed polygon ring (3 unique + 1 repeated to close).
MIN_RING_VERTICES = 4

# Per-site hunt verdict captured 2026-05-12. way_id=None means OSM didn't
# have a confidently-matching polygon — site stays on the 2 km buffer
# fallback from commit A until tier-3 follow-up.
HUNT_VERDICTS: list[dict] = [
    {
        "site_id": "pupuk-kaltim-bontang",
        "way_id": 695713458,
        "verdict": "found",
        "osm_display_name": ("Pupuk Kaltim, Bontang, Kalimantan Timur, Kalimantan, Indonesia"),
        "note": "Named landuse=industrial polygon, 145 ha, 5.9 km from dim_sites centroid (centroid is regional, not site).",
    },
    {
        "site_id": "dexin-steel-morowali",
        "way_id": 299975400,
        "verdict": "found_via_parent_park",
        "osm_display_name": (
            "Indonesia Morowali Industrial Park, Bahodopi, Morowali, Sulawesi Tengah, Indonesia"
        ),
        "note": (
            "Dexin Steel is a tenant inside IMIP. Reusing IMIP's polygon "
            "(way/299975400, also used by indonesia-morowali-industrial-park-imip) "
            "as Dexin's fence. Reasonable approximation: both share the same physical estate."
        ),
    },
    {
        "site_id": "nusantara-industri-sejati",
        "way_id": None,
        "verdict": "osm_gap",
        "note": (
            "No matching polygon within 20 km — only 'Delong Nickel Phase II Power Station' "
            "(30 ha, 6.5 km away, different operator). Centroid may be regional rather than "
            "site-specific. Tier-3 follow-up: Claude-trace from buildings."
        ),
    },
    {
        "site_id": "inalum-asahan",
        "way_id": None,
        "verdict": "osm_gap",
        "note": (
            "0 polygons within 15 km despite Inalum being Indonesia's largest aluminium smelter. "
            "OSM coverage is genuinely missing for Kuala Tanjung. Tier-3 follow-up or government source."
        ),
    },
    {
        "site_id": "buli-industrial-park",
        "way_id": None,
        "verdict": "osm_gap",
        "note": (
            "Only 4 unnamed polygons within 15 km, closest at 9 km. Can't confidently identify the "
            "facility without local verification. Tier-3 follow-up."
        ),
    },
]


def fetch_way_geometry(way_id: int) -> dict:
    """Pull full geometry for a single OSM way via Overpass."""
    query = f"[out:json][timeout:60]; way({way_id}); out geom;"
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": "eez-dashboard-polygon-hunt/1.0"},
                timeout=90,
            )
            if r.status_code == HTTP_OK:
                elements = r.json().get("elements", [])
                if elements:
                    return elements[0]
        except requests.RequestException as exc:
            print(f"    {endpoint} failed: {exc}", file=sys.stderr)
            time.sleep(4)
    raise RuntimeError(f"Could not fetch way/{way_id} from any Overpass endpoint")


def way_to_feature(way: dict, site_id: str, display_name: str) -> dict:
    """Convert Overpass way result to a GeoJSON Feature matching the existing
    site_polygons.geojson schema. See provenance fields on existing entries
    (Indocement Palimanan et al.) for the exact key set."""
    geometry = way.get("geometry") or []
    coords = [(p["lon"], p["lat"]) for p in geometry]
    if len(coords) < MIN_RING_VERTICES:
        raise ValueError(f"way/{way.get('id')} has only {len(coords)} points")
    if coords[0] != coords[-1]:
        coords.append(coords[0])

    tags = way.get("tags") or {}
    osm_class = "landuse" if "landuse" in tags else ("man_made" if "man_made" in tags else "")
    osm_type = tags.get("landuse") or tags.get("man_made") or ""

    return {
        "type": "Feature",
        "properties": {
            "site_id": site_id,
            "osm_class": osm_class,
            "osm_type": osm_type,
            "osm_id": way["id"],
            "osm_display_name": display_name,
            "verified_date": "2026-05-12",
            "source_name": "OSM Nominatim (landuse=industrial / man_made=works)",
            "source_url": f"https://www.openstreetmap.org/way/{way['id']}",
            "polygon_source_tier": "osm_landuse_industrial",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
    }


def main() -> None:
    print("Loading existing site_polygons.geojson ...")
    data = json.loads(SITE_POLYGONS.read_text())
    existing_ids = {f["properties"].get("site_id") for f in data["features"]}
    print(f"  {len(data['features'])} existing features ({len(existing_ids)} unique site_ids)")

    added = 0
    skipped_gap = 0
    for v in HUNT_VERDICTS:
        site_id = v["site_id"]
        if v["verdict"].startswith("osm_gap"):
            print(f"  ⊘ {site_id}: OSM gap — {v['note']}")
            skipped_gap += 1
            continue
        if site_id in existing_ids:
            print(f"  = {site_id}: already in file — skipping (no overwrite)")
            continue
        way_id = v["way_id"]
        print(f"  ↓ {site_id}: fetching way/{way_id} ...")
        way = fetch_way_geometry(way_id)
        feature = way_to_feature(way, site_id, v["osm_display_name"])
        data["features"].append(feature)
        added += 1
        time.sleep(2)  # Be polite to Overpass

    if added:
        SITE_POLYGONS.write_text(json.dumps(data, indent=2) + "\n")
        print(f"\nWrote {SITE_POLYGONS.relative_to(REPO_ROOT)}: +{added} new features")
    else:
        print("\nNothing to append (all sites already in file or fell into OSM gap).")
    print(f"Summary: {added} added, {skipped_gap} OSM-gap (need tier-3 follow-up)")


if __name__ == "__main__":
    main()
