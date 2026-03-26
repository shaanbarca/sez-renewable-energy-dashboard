"""
build_fct_kek_resource — PVOUT at centroid and best-within-50km for each KEK.

Sources:
    processed: dim_kek.csv                                   KEK centroids (lat/lon)
    data: Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip

Output columns (PVOUT values in kWh/kWp/year, CF values unitless 0–1):
    kek_id                   slug from dim_kek — join key
    kek_name                 display name
    latitude                 centroid latitude
    longitude                centroid longitude
    pvout_daily_centroid     raw daily value from GeoTIFF (kWh/kWp/day) — for audit
    pvout_centroid           annual PVOUT at centroid (kWh/kWp/year) = daily × 365
    cf_centroid              capacity factor at centroid = pvout_centroid / 8760
    pvout_daily_best_50km    raw daily max within 50km radius — for audit
    pvout_best_50km          annual PVOUT best within 50km (kWh/kWp/year)
    cf_best_50km             capacity factor best within 50km = pvout_best_50km / 8760
    pvout_source             "GlobalSolarAtlas-v2"

Methodology reference: METHODOLOGY.md Section 2.4
50km buffer formula: lat_buf = 50/111.32, lon_buf = 50/(111.32×cos(lat_rad))
"""

from __future__ import annotations

import io
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import from_bounds

from src.model.basic_model import pvout_daily_to_annual
from src.pipeline.assumptions import HOURS_PER_YEAR, KM_PER_DEGREE_LAT, PVOUT_BUFFER_KM, PVOUT_SOURCE

REPO_ROOT = Path(__file__).resolve().parents[2]
GEOTIFF_ZIP = (
    REPO_ROOT
    / "data"
    / "Indonesia_GISdata_LTAym_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF.zip"
)
PVOUT_TIF_PATH = (
    "Indonesia_GISdata_LTAy_AvgDailyTotals_GlobalSolarAtlas-v2_GEOTIFF/PVOUT.tif"
)
PROCESSED = REPO_ROOT / "outputs" / "data" / "processed"
DIM_KEK_CSV = PROCESSED / "dim_kek.csv"


# ─── Raster extraction helpers ────────────────────────────────────────────────

def _load_pvout_tif_bytes() -> bytes:
    """Extract PVOUT.tif bytes from the zip archive."""
    with zipfile.ZipFile(GEOTIFF_ZIP) as z:
        return z.read(PVOUT_TIF_PATH)


def _sample_centroid(
    src: rasterio.DatasetReader, arr: np.ndarray, lon: float, lat: float
) -> float:
    """Return the PVOUT pixel value at (lon, lat). Returns np.nan if out of bounds."""
    try:
        row, col = src.index(lon, lat)
        if 0 <= row < arr.shape[0] and 0 <= col < arr.shape[1]:
            val = float(arr[row, col])
            return val if np.isfinite(val) else np.nan
        return np.nan
    except Exception:
        return np.nan


def _sample_best_50km(src: rasterio.DatasetReader, lon: float, lat: float) -> float:
    """Return the max valid PVOUT daily value within 50km of (lon, lat)."""
    lat_buf = PVOUT_BUFFER_KM / KM_PER_DEGREE_LAT
    lon_buf = PVOUT_BUFFER_KM / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))
    window = from_bounds(
        left=lon - lon_buf,
        bottom=lat - lat_buf,
        right=lon + lon_buf,
        top=lat + lat_buf,
        transform=src.transform,
    )
    try:
        patch = src.read(1, window=window)
    except Exception:
        return np.nan
    valid = patch[np.isfinite(patch)]
    return float(valid.max()) if len(valid) > 0 else np.nan


# ─── Builder ──────────────────────────────────────────────────────────────────

def build_fct_kek_resource(
    geotiff_zip: Path = GEOTIFF_ZIP,
    kek_csv: Path = DIM_KEK_CSV,
) -> pd.DataFrame:
    """Extract PVOUT and CF at centroid and best-within-50km for all KEKs."""

    # ─── RAW ──────────────────────────────────────────────────────────────────
    kek_df = pd.read_csv(kek_csv)
    tif_bytes = _load_pvout_tif_bytes()  # uses module-level GEOTIFF_ZIP; geotiff_zip param reserved for override

    # ─── STAGING + TRANSFORM ──────────────────────────────────────────────────
    # (extraction and conversion happen together per-KEK in the raster loop)
    records = []
    with rasterio.open(io.BytesIO(tif_bytes)) as src:
        arr = src.read(1)
        for _, row in kek_df.iterrows():
            lat = float(row["latitude"])
            lon = float(row["longitude"])

            pvout_daily_c = _sample_centroid(src, arr, lon, lat)
            pvout_daily_b = _sample_best_50km(src, lon, lat)

            # Daily → annual. pvout_daily_to_annual validates plausibility range.
            # Try/except surfaces per-KEK issues without aborting the full run.
            try:
                pvout_c = pvout_daily_to_annual(pvout_daily_c) if np.isfinite(pvout_daily_c) else np.nan
            except ValueError as e:
                print(f"  WARNING centroid {row['kek_id']}: {e}")
                pvout_c = np.nan

            try:
                pvout_b = pvout_daily_to_annual(pvout_daily_b) if np.isfinite(pvout_daily_b) else np.nan
            except ValueError as e:
                print(f"  WARNING best_50km {row['kek_id']}: {e}")
                pvout_b = np.nan

            records.append({
                "kek_id": row["kek_id"],
                "kek_name": row["kek_name"],
                "latitude": lat,
                "longitude": lon,
                "pvout_daily_centroid": round(pvout_daily_c, 4) if np.isfinite(pvout_daily_c) else np.nan,
                "pvout_centroid": round(pvout_c, 1) if np.isfinite(pvout_c) else np.nan,
                "cf_centroid": round(pvout_c / HOURS_PER_YEAR, 4) if np.isfinite(pvout_c) else np.nan,
                "pvout_daily_best_50km": round(pvout_daily_b, 4) if np.isfinite(pvout_daily_b) else np.nan,
                "pvout_best_50km": round(pvout_b, 1) if np.isfinite(pvout_b) else np.nan,
                "cf_best_50km": round(pvout_b / HOURS_PER_YEAR, 4) if np.isfinite(pvout_b) else np.nan,
                "pvout_source": PVOUT_SOURCE,
            })

    return pd.DataFrame(records)


def main() -> None:
    print(f"Loading KEK centroids from {DIM_KEK_CSV.relative_to(REPO_ROOT)}")
    print(f"Loading PVOUT raster from {GEOTIFF_ZIP.relative_to(REPO_ROOT)}")

    df = build_fct_kek_resource()

    n_miss_c = df["pvout_centroid"].isna().sum()
    n_miss_b = df["pvout_best_50km"].isna().sum()
    print(f"\nExtracted {len(df)} KEKs")
    print(f"  pvout_centroid:  {len(df) - n_miss_c}/{len(df)} valid")
    print(f"  pvout_best_50km: {len(df) - n_miss_b}/{len(df)} valid")
    print(f"  cf range (best): {df['cf_best_50km'].min():.3f} – {df['cf_best_50km'].max():.3f}")

    out = PROCESSED / "fct_kek_resource.csv"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nWrote {out.relative_to(REPO_ROOT)}")
    print(df[["kek_id", "pvout_centroid", "cf_centroid", "pvout_best_50km", "cf_best_50km"]].to_string(index=False))


if __name__ == "__main__":
    main()
