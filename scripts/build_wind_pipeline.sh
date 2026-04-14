#!/bin/bash
# Build the complete wind buildability pipeline.
# Run from project root: bash scripts/build_wind_pipeline.sh
#
# Steps:
#   1. Build nationwide wind buildable raster (~3-5 min)
#   2. Vectorize to GeoJSON polygons for map overlay
#   3. Update per-KEK wind resource CSV with buildability columns

set -e

echo "=== Wind Buildability Pipeline ==="
echo ""

# Optional: build road distance raster if not present
if [ ! -f "data/buildability/road_distance_km.tif" ]; then
    echo "Note: road_distance_km.tif not found. Road proximity filter will be skipped."
    echo "      Run 'uv run python scripts/download_road_data.py' to build it."
    echo ""
fi

echo "Step 1/3: Building wind buildable raster..."
uv run python -m src.pipeline.build_wind_buildable_raster
echo ""

echo "Step 2/3: Vectorizing to polygons..."
uv run python -m src.pipeline.build_wind_buildable_polygons
echo ""

echo "Step 3/3: Updating per-KEK wind resource..."
uv run python -m src.pipeline.build_fct_kek_wind_resource
echo ""

echo "=== Done ==="
echo "Outputs:"
echo "  outputs/assets/buildable_wind_web.tif"
echo "  outputs/assets/wind_buildable_polygons.geojson"
echo "  outputs/data/processed/fct_kek_wind_resource.csv"
