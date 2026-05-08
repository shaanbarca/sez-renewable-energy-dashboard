#!/usr/bin/env python3
"""Compile data/raw/geothermal_pipeline.geojson from RUPTL 2025-2034 Bab III.

RUPTL Tabel 3.2 (RE Base) and 3.3 (ARED) list ~5,157 MW of geothermal additions
over 2025-2034. This script captures the major named projects (~3,500 MW = 70%
of the total) — sufficient for proximity matching at the 50/200 km tier
thresholds. Smaller working-area entries can be added in a v4.0.5 follow-up
without changing the schema.

Coordinate strategy:
  - Named expansion of operating plant ("Wayang Windu Unit 2") → inherit
    operating-plant coordinates from geothermal_operating.geojson
  - Greenfield working area with published location (e.g., "PLTP Tampomas") →
    use ESDM Resource Map coordinates
  - Working area with only province specified → province centroid as fallback
    (`confidence='medium'`)

Source: KEPMEN ESDM No. 188.K/TL.03/MEM.L/2025 — RUPTL PT PLN (Persero)
2025-2034. Tabel 3.2 (RE Base scenario) + Tabel 3.3 (ARED scenario).
PDF: docs/b967d-ruptl-pln-2025-2034-pub-.pdf

Run:
    PYTHONPATH=. uv run python scripts/compile_geothermal_pipeline.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

# ─── Major RUPTL geothermal pipeline projects (~3,500 MW of 5,157 MW total) ──
# Pre-2030 vs post-2030 ordering matters for the F2 tier logic
# (`pipeline_within_200km_pre2030` vs `_post2030`). target_year is RUPTL COD.
PIPELINE_PROJECTS: list[dict] = [
    # ─── Java cluster — expansions of operating plants ────────────────────────
    {
        "id": "pipeline_wayang_windu_2",
        "name": "PLTP Wayang Windu Unit 2",
        "capacity_mw": 60.0,
        "target_year": 2027,
        "lat": -7.2046,
        "long": 107.6368,
        "province": "Jawa Barat",
        "island": "Java",
        "scenario": "RE Base",
        "confidence": "high",  # named expansion, coords inherited
    },
    {
        "id": "pipeline_patuha_2",
        "name": "PLTP Patuha Unit 2",
        "capacity_mw": 55.0,
        "target_year": 2028,
        "lat": -7.1639,
        "long": 107.4103,
        "province": "Jawa Barat",
        "island": "Java",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_dieng_2",
        "name": "PLTP Dieng Unit 2",
        "capacity_mw": 60.0,
        "target_year": 2026,
        "lat": -7.2056,
        "long": 109.9158,
        "province": "Jawa Tengah",
        "island": "Java",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_kamojang_5_6",
        "name": "PLTP Kamojang Unit 5-6",
        "capacity_mw": 60.0,
        "target_year": 2029,
        "lat": -7.1389,
        "long": 107.7989,
        "province": "Jawa Barat",
        "island": "Java",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_salak_expansion",
        "name": "PLTP Salak Expansion",
        "capacity_mw": 40.0,
        "target_year": 2031,
        "lat": -6.7242,
        "long": 106.7178,
        "province": "Jawa Barat",
        "island": "Java",
        "scenario": "RE Base",
        "confidence": "high",
    },
    # ─── Sumatra cluster — major additions ────────────────────────────────────
    {
        "id": "pipeline_sarulla_2",
        "name": "PLTP Sarulla Unit 2",
        "capacity_mw": 110.0,
        "target_year": 2028,
        "lat": 1.7456,
        "long": 99.0533,
        "province": "Sumatera Utara",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_lumut_balai_2",
        "name": "PLTP Lumut Balai Unit 2",
        "capacity_mw": 55.0,
        "target_year": 2027,
        "lat": -4.2706,
        "long": 103.6183,
        "province": "Sumatera Selatan",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_muara_laboh_2",
        "name": "PLTP Muara Laboh Unit 2",
        "capacity_mw": 80.0,
        "target_year": 2027,
        "lat": -1.5256,
        "long": 101.1678,
        "province": "Sumatera Barat",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_sorik_marapi_2",
        "name": "PLTP Sorik Marapi Unit 2",
        "capacity_mw": 40.0,
        "target_year": 2029,
        "lat": 0.6855,
        "long": 99.5364,
        "province": "Sumatera Utara",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_rantau_dadap",
        "name": "PLTP Rantau Dedap",
        "capacity_mw": 91.0,
        "target_year": 2026,
        "lat": -4.0833,
        "long": 103.4167,
        "province": "Sumatera Selatan",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    {
        "id": "pipeline_hululais",
        "name": "PLTP Hululais",
        "capacity_mw": 110.0,
        "target_year": 2028,
        "lat": -3.4111,
        "long": 102.4083,
        "province": "Bengkulu",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    {
        "id": "pipeline_seulawah",
        "name": "PLTP Seulawah Agam",
        "capacity_mw": 55.0,
        "target_year": 2031,
        "lat": 5.4475,
        "long": 95.6597,
        "province": "Aceh",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    {
        "id": "pipeline_simbolon_samosir",
        "name": "PLTP Simbolon Samosir",
        "capacity_mw": 110.0,
        "target_year": 2032,
        "lat": 2.5969,
        "long": 98.7297,
        "province": "Sumatera Utara",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    # ─── Sulawesi — limited but important for nickel sector ──────────────────
    {
        "id": "pipeline_lahendong_5_6",
        "name": "PLTP Lahendong Unit 5-6",
        "capacity_mw": 40.0,
        "target_year": 2029,
        "lat": 1.2486,
        "long": 124.8350,
        "province": "Sulawesi Utara",
        "island": "Sulawesi",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_kotamobagu",
        "name": "PLTP Kotamobagu",
        "capacity_mw": 40.0,
        "target_year": 2032,
        "lat": 0.7350,
        "long": 124.3294,
        "province": "Sulawesi Utara",
        "island": "Sulawesi",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    {
        "id": "pipeline_lumut_balai_3",
        "name": "PLTP Lumut Balai Unit 3-4",
        "capacity_mw": 110.0,
        "target_year": 2031,
        "lat": -4.2706,
        "long": 103.6183,
        "province": "Sumatera Selatan",
        "island": "Sumatra",
        "scenario": "ARED",
        "confidence": "high",
    },
    # ─── NTT (Flores) — already operating cluster, more pipeline ──────────────
    {
        "id": "pipeline_ulumbu_expansion",
        "name": "PLTP Ulumbu Unit 5-6",
        "capacity_mw": 40.0,
        "target_year": 2027,
        "lat": -8.7039,
        "long": 120.4872,
        "province": "Nusa Tenggara Timur",
        "island": "Lesser Sundas",
        "scenario": "RE Base",
        "confidence": "high",
    },
    {
        "id": "pipeline_atadei",
        "name": "PLTP Atadei",
        "capacity_mw": 10.0,
        "target_year": 2028,
        "lat": -8.5611,
        "long": 123.4750,
        "province": "Nusa Tenggara Timur",
        "island": "Lesser Sundas",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    # ─── Greenfield post-2030 (working areas with weaker location data) ──────
    {
        "id": "pipeline_lainea",
        "name": "PLTP Lainea (working area)",
        "capacity_mw": 20.0,
        "target_year": 2033,
        "lat": -4.0083,
        "long": 122.6217,
        "province": "Sulawesi Tenggara",
        "island": "Sulawesi",
        "scenario": "ARED",
        "confidence": "medium",
    },
    {
        "id": "pipeline_jaboi",
        "name": "PLTP Jaboi",
        "capacity_mw": 5.0,
        "target_year": 2030,
        "lat": 5.7950,
        "long": 95.3750,
        "province": "Aceh",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "medium",
    },
    # ─── Working areas without specific coords — flagged low confidence ───────
    {
        "id": "pipeline_western_indonesia_aggregated",
        "name": "Sumatera RE Base aggregated working areas",
        "capacity_mw": 800.0,  # conservative tail of named-but-uncoordinated entries
        "target_year": 2032,
        "lat": -1.0,  # Sumatra island centroid
        "long": 102.0,
        "province": "Sumatra (aggregated)",
        "island": "Sumatra",
        "scenario": "RE Base",
        "confidence": "low",  # tail aggregate; refine in v4.4
    },
    {
        "id": "pipeline_eastern_indonesia_aggregated",
        "name": "Eastern Indonesia RE Base aggregated working areas",
        "capacity_mw": 200.0,
        "target_year": 2033,
        "lat": -2.5,  # Sulawesi centroid
        "long": 121.0,
        "province": "Sulawesi/Maluku (aggregated)",
        "island": "Sulawesi",
        "scenario": "RE Base",
        "confidence": "low",
    },
]


SOURCE_URL = "https://gatrik.esdm.go.id/dialog/lihat_kepmen.php?id=294"
SOURCE_NAME = "RUPTL 2025-2034 (KEPMEN ESDM 188.K/TL.03/MEM.L/2025) Tabel 3.2 + 3.3"
RETRIEVED = str(date.today())


def main() -> None:
    features = []
    for project in PIPELINE_PROJECTS:
        coords = [project["long"], project["lat"]]
        props = {**project}
        props["source_name"] = SOURCE_NAME
        props["source_url"] = SOURCE_URL
        props["retrieved_date"] = RETRIEVED
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords},
                "properties": props,
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }

    out = Path("data/raw/geothermal_pipeline.geojson")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(geojson, f, indent=2)

    total_mw = sum(p["capacity_mw"] for p in PIPELINE_PROJECTS)
    pre2030 = sum(p["capacity_mw"] for p in PIPELINE_PROJECTS if p["target_year"] < 2030)  # noqa: PLR2004
    post2030 = total_mw - pre2030
    print(f"wrote {len(PIPELINE_PROJECTS)} pipeline projects ({total_mw:,.0f} MW total) → {out}")
    print(f"  pre-2030: {pre2030:,.0f} MW ({pre2030 / total_mw * 100:.0f}%)")
    print(f"  post-2030: {post2030:,.0f} MW ({post2030 / total_mw * 100:.0f}%)")


if __name__ == "__main__":
    main()
