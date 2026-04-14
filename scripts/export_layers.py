#!/usr/bin/env python3
# Copyright (c) 2024-2026 Shaan Barca. Licensed under MIT + Commons Clause.
# See LICENSE and NOTICE files in the project root.
"""Pre-generate processed map layers for deployment.

Reads raw GeoTIFFs, shapefiles, and large GeoJSONs that live on disk locally
(4+ GB total), processes them into small web-ready files (~10 MB total), and
saves to outputs/layers/. These files get committed to git and shipped in
Docker, eliminating the need for raw geodata on the server.

Usage:
    uv run python scripts/export_layers.py

Layers exported:
    pvout.json               ~300 KB  (base64 PNG + coordinates)
    wind.json                ~200 KB  (base64 PNG + coordinates)
    peatland.geojson         ~2 MB    (dissolved + simplified)
    protected_forest.geojson ~2 MB    (filtered + dissolved + simplified)
    grid_lines.geojson       ~4.4 MB  (pass-through copy)
    industrial.json          ~50 KB   (point list)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path so we can import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "layers"
DATA_DIR = PROJECT_ROOT / "data"


def export_pvout() -> bool:
    """Export PVOUT raster as base64 PNG overlay."""
    from src.dash.map_layers import load_pvout_raster

    print("  Exporting PVOUT raster...")
    result = load_pvout_raster()
    if result is None:
        print("    SKIP: raw PVOUT zip not found")
        return False

    image_url, coordinates = result
    out = OUTPUT_DIR / "pvout.json"
    out.write_text(json.dumps({"image_url": image_url, "coordinates": coordinates}))
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB")
    return True


def export_wind() -> bool:
    """Export wind speed raster as base64 PNG overlay."""
    from src.dash.map_layers import load_wind_raster

    print("  Exporting wind raster...")
    result = load_wind_raster()
    if result is None:
        print("    SKIP: raw wind TIF not found")
        return False

    image_url, coordinates = result
    out = OUTPUT_DIR / "wind.json"
    out.write_text(json.dumps({"image_url": image_url, "coordinates": coordinates}))
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB")
    return True


def export_peatland() -> bool:
    """Export peatland as simplified/dissolved GeoJSON."""
    from src.dash.map_layers import load_peatland

    print("  Exporting peatland...")
    result = load_peatland()
    if result is None:
        print("    SKIP: raw peatland GeoJSON not found")
        return False

    out = OUTPUT_DIR / "peatland.geojson"
    out.write_text(json.dumps(result))
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB")
    return True


def export_protected_forest() -> bool:
    """Export kawasan hutan (conservation + protected) as dissolved GeoJSON."""
    from src.dash.map_layers import load_protected_forest

    print("  Exporting protected forest...")
    result = load_protected_forest()
    if result is None:
        print("    SKIP: raw kawasan hutan shapefile not found")
        return False

    out = OUTPUT_DIR / "protected_forest.geojson"
    out.write_text(json.dumps(result))
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB")
    return True


def export_grid_lines() -> bool:
    """Copy grid lines GeoJSON (already small, just needs to be in the right place)."""
    print("  Exporting grid lines...")
    src = DATA_DIR / "pln_grid_lines.geojson"
    if not src.exists():
        print("    SKIP: grid lines GeoJSON not found")
        return False

    out = OUTPUT_DIR / "grid_lines.geojson"
    out.write_bytes(src.read_bytes())
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB")
    return True


def export_industrial() -> bool:
    """Export industrial facilities as JSON point list."""
    from src.dash.map_layers import load_industrial_facilities

    print("  Exporting industrial facilities...")
    result = load_industrial_facilities()
    if not result:
        print("    SKIP: industrial shapefile not found")
        return False

    out = OUTPUT_DIR / "industrial.json"
    out.write_text(json.dumps(result))
    size_kb = out.stat().st_size / 1024
    print(f"    OK: {size_kb:.0f} KB ({len(result)} facilities)")
    return True


def main():
    print(f"Exporting processed layers to {OUTPUT_DIR}/")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    exporters = [
        ("pvout", export_pvout),
        ("wind", export_wind),
        ("peatland", export_peatland),
        ("protected_forest", export_protected_forest),
        ("grid_lines", export_grid_lines),
        ("industrial", export_industrial),
    ]

    for name, fn in exporters:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"    FAIL: {e}")
            results[name] = False

    # Summary
    print("\n--- Export summary ---")
    total_kb = 0
    for name, ok in results.items():
        if ok:
            # Find the output file
            for ext in [".json", ".geojson"]:
                p = OUTPUT_DIR / f"{name}{ext}"
                if p.exists():
                    kb = p.stat().st_size / 1024
                    total_kb += kb
                    print(f"  {name:25s} {kb:8.0f} KB")
                    break
        else:
            print(f"  {name:25s} SKIPPED")

    print(f"\n  Total: {total_kb / 1024:.1f} MB")
    n_ok = sum(1 for v in results.values() if v)
    n_skip = sum(1 for v in results.values() if not v)
    print(f"  {n_ok} exported, {n_skip} skipped")

    if n_ok > 0:
        print("\nNext: git add outputs/layers/ && git commit")


if __name__ == "__main__":
    main()
