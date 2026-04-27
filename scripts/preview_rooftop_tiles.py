"""
preview_rooftop_tiles.py — Open a site's buildings + panel tiles in your
browser for manual visual validation.

# What it does

For one site, render an interactive Leaflet map (via folium) showing:
  - Building polygons (gray, semi-transparent) — what GoB v3 detected
  - Panel tiles (blue) — what `build_rooftop_tiles.py` decided to render
  - Site marker — anchor point

Saves to data/processed/_previews/<site_id>.html and opens it in your
default browser. You can zoom, pan, click features for popups.

# Usage

    # Default: show the top-MWp site (Gunung Raja Paksi Bekasi)
    uv run python scripts/preview_rooftop_tiles.py

    # Specific site
    uv run python scripts/preview_rooftop_tiles.py --site krakatau-steel-cilegon

    # Open without launching browser (CI / headless)
    uv run python scripts/preview_rooftop_tiles.py --no-open

    # List available sites
    uv run python scripts/preview_rooftop_tiles.py --list
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
PREVIEW_DIR = DATA_PROCESSED / "_previews"

BUILDINGS_PARQUET = DATA_PROCESSED / "sites_buildings_filtered.parquet"
TILES_PARQUET = DATA_PROCESSED / "sites_rooftop_tiles.parquet"
FCT_CSV = PROCESSED / "fct_site_solar_potential.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render buildings + panel tiles for one site as an HTML map.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="site_id (e.g., 'gunung-raja-paksi-bekasi'). Default: top-MWp site.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Save HTML but don't launch the browser.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List sites that have tiles and their MWp.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fct = pd.read_csv(FCT_CSV)

    if args.list:
        with_tiles = fct[fct["building_count_standard_roof"] > 0].sort_values(
            "rooftop_solar_mwp_potential", ascending=False
        )
        print(f"{len(with_tiles)} sites with tiles:")
        for _, r in with_tiles.iterrows():
            print(
                f"  {r['site_id']:<40} {r['rooftop_solar_mwp_potential']:>8.1f} MWp DC  "
                f"({r['building_count_standard_roof']:>5} standard rooftops)"
            )
        return 0

    site_id = args.site
    if not site_id:
        # Default: highest-MWp site
        top = fct.sort_values("rooftop_solar_mwp_potential", ascending=False).iloc[0]
        site_id = top["site_id"]
        print(f"No --site given; defaulting to top: {site_id}")

    # Load data filtered to this site
    print(f"Loading data for {site_id}...")
    buildings = gpd.read_parquet(BUILDINGS_PARQUET)
    buildings = buildings[buildings["site_id"] == site_id]
    if buildings.empty:
        print(f"ERROR: no buildings for site {site_id}", file=sys.stderr)
        return 1

    tiles = gpd.read_parquet(TILES_PARQUET)
    tiles = tiles[tiles["site_id"] == site_id]

    # Compute centre of buildings for map anchor
    centroid_lat = buildings["latitude"].mean()
    centroid_lon = buildings["longitude"].mean()
    site_row = fct[fct["site_id"] == site_id].iloc[0]

    print(f"  buildings: {len(buildings):,}")
    print(f"  tiles:     {len(tiles):,}")
    print(f"  rooftop MWp DC: {site_row['rooftop_solar_mwp_potential']:.1f}")
    print(f"  std roofs:      {site_row['building_count_standard_roof']:,}")

    # Build map
    m = folium.Map(
        location=[centroid_lat, centroid_lon],
        zoom_start=16,
        tiles="OpenStreetMap",  # readable streetview
    )
    folium.TileLayer("CartoDB positron", name="Light", attr="© CartoDB").add_to(m)
    folium.TileLayer("Esri.WorldImagery", name="Satellite", attr="© Esri").add_to(m)

    # Building polygons (gray)
    bldg_layer = folium.FeatureGroup(name=f"Buildings ({len(buildings):,})")
    for _, b in buildings.iterrows():
        folium.GeoJson(
            b.geometry.__geo_interface__,
            style_function=lambda _: {
                "fillColor": "#666666",
                "color": "#222222",
                "weight": 0.5,
                "fillOpacity": 0.25,
            },
            tooltip=folium.Tooltip(
                f"<b>building_id:</b> {b['building_id']}<br>"
                f"<b>area:</b> {b['area_in_meters']:.0f} m²<br>"
                f"<b>confidence:</b> {b['confidence']:.2f}",
                sticky=True,
            ),
        ).add_to(bldg_layer)
    bldg_layer.add_to(m)

    # Tiles (blue) — represent solar panels
    tile_layer = folium.FeatureGroup(name=f"Solar panel tiles ({len(tiles):,} × 2.4 kW DC)")
    for _, t in tiles.iterrows():
        folium.GeoJson(
            t.geometry.__geo_interface__,
            style_function=lambda _: {
                "fillColor": "#1a3a8a",  # solar-panel-blue per spec §3.6 F9
                "color": "#0a1f4a",
                "weight": 0.3,
                "fillOpacity": 0.65,
            },
            tooltip=f"tile #{t['tile_idx']} · cluster {t['cluster_id']} · "
            f"{t['tile_kw_dc']:.1f} kW DC ({t['tile_kw_ac']:.1f} kW AC)",
        ).add_to(tile_layer)
    tile_layer.add_to(m)

    # Header info box
    info_html = f"""
    <div style="position: fixed; top: 12px; right: 12px;
                background: rgba(15,15,18,0.92); color: #f0f0f0;
                padding: 14px 18px; border-radius: 8px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px; max-width: 360px; z-index: 9999;
                box-shadow: 0 4px 16px rgba(0,0,0,0.4);">
      <div style="font-weight: 600; margin-bottom: 6px; color: #fff;">
        {site_row["site_name"]}
      </div>
      <div style="font-size: 11px; color: #aaa; margin-bottom: 10px;">
        {site_id}
      </div>
      <div style="line-height: 1.6;">
        <b style="color: #4d9eff;">{site_row["rooftop_solar_mwp_potential"]:.1f} MWp DC</b>
        rooftop (aggregator)<br>
        <b style="color: #4d9eff;">{len(tiles):,} × 2.4 kW</b> = {len(tiles) * 2.4 / 1000:.1f} MWp DC tiles<br>
        <span style="color: #888;">{site_row["building_count_standard_roof"]:,} standard rooftops &middot;
        {site_row["building_count_total"]:,} total buildings</span>
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    folium.LayerControl(collapsed=False).add_to(m)

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREVIEW_DIR / f"{site_id}.html"
    m.save(str(out_path))
    print(f"\n  preview saved: {out_path}")

    if not args.no_open:
        url = out_path.resolve().as_uri()
        print(f"  opening in browser: {url}")
        webbrowser.open(url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
