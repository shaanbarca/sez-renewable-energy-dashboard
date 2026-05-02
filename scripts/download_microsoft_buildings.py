"""
download_microsoft_buildings.py — Fetch Microsoft Global ML Building Footprints
for Indonesia, the second building-detection source per spec §13.10 invariant 4.

# Why a second source

GoB v3 has two well-documented gaps surfaced by RV-eval:
  (a) Post-2023 buildings invisible (imagery cutoff May 2023). Galang Batang
      halls, IMIP/IWIP nickel mega-buildouts, Red Lion Hongshi 4-Mt cement
      plant — all real but absent.
  (b) Plants GoB just doesn't see even when fully visible — Cemindo Bayah
      pattern: kilns + silos + conveyors clearly on the satellite, GoB
      returns zero.

Microsoft GMLBF is a different model trained on different imagery vintage.
The two sources together close most of GoB's blind spots.

# What this script does

1. Fetches the dataset-links CSV from Microsoft's public Azure blob.
2. Filters to rows where Location == "Indonesia".
3. Downloads each gzipped GeoJSONL tile to data/microsoft_buildings/raw/.
4. Resumable — skips tiles already on disk.

The output of this script is the raw extract; preprocess_microsoft_buildings.py
(Phase 2) is the equivalent of preprocess_open_buildings.py — streams the raw
files and writes a per-site filtered parquet matching the spec §13.10 schema
(building_id with "ms_gmlbf:" prefix, source_name, source_vintage).

# Disk + time

- Indonesia is split across 601 quadkeys (verified via dry-run 2026-04-30).
- Each tile is 1-50 MB compressed (varies wildly by population density).
- Total download: ~4.7 GB gzipped (verified via dry-run).
- Time on standard fiber + 4 workers: 20-40 minutes.

# Dependencies

Already in pyproject.toml: pandas, requests, tqdm.

# Usage

    uv run python scripts/download_microsoft_buildings.py
    uv run python scripts/download_microsoft_buildings.py --workers 8
    uv run python scripts/download_microsoft_buildings.py --dry-run   # just count tiles

# Schema (per tile, gzipped GeoJSONL)

Each line is a GeoJSON Feature:
  {"type":"Feature","geometry":{"type":"Polygon","coordinates":[[...]]},
   "properties":{"height":12.3}}

Properties commonly include `height` (estimated meters); NO confidence score
(per spec §13.10 invariant 5 — confidence handling treats null gracefully).

# Provenance

Microsoft Global ML Building Footprints v2 (released 2023+, refreshed
periodically). Repo: https://github.com/microsoft/GlobalMLBuildingFootprints
Index: https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "microsoft_buildings"
RAW_DIR = DATA_DIR / "raw"
INDEX_URL = "https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv"
INDEX_CACHE = DATA_DIR / "dataset-links.csv"

USER_AGENT = "eez-rooftop-research/1.0 (shaan.b1223@gmail.com)"
# Retry transient failures: 5xx server errors, 429 rate-limit, connection
# resets. With ~600 tiles across 4-8 workers, even a 0.1% blip rate causes
# painful re-runs without retry — and Microsoft's CDN does occasionally 503.
# Backoff: 1s, 2s, 4s (3 attempts beyond the initial request).
RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "HEAD"]),
    raise_on_status=False,
)
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})
_ADAPTER = HTTPAdapter(max_retries=RETRY_STRATEGY)
SESSION.mount("http://", _ADAPTER)
SESSION.mount("https://", _ADAPTER)


def _parse_size_total(s: pd.Series) -> float:
    """Sum a 'Size' column whose values look like '12.3MB' / '456KB' / '1.2GB'.

    Returns total bytes. Unparseable rows count as 0 (defensive — MS may
    revise the schema and a single bad row shouldn't crash dry-run).
    """
    suffixes = {"B": 1, "KB": 1e3, "MB": 1e6, "GB": 1e9, "TB": 1e12}
    total = 0.0
    for raw in s.dropna().astype(str):
        v = raw.strip().upper()
        for suffix, mult in sorted(suffixes.items(), key=lambda kv: -len(kv[0])):
            if v.endswith(suffix):
                num = v[: -len(suffix)].strip()
                try:
                    total += float(num) * mult
                except ValueError:
                    pass
                break
    return total


def fetch_index(force: bool = False) -> pd.DataFrame:
    """Download dataset-links.csv (or use cached). Filter to Indonesia."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if force or not INDEX_CACHE.exists():
        print(f"Fetching index from {INDEX_URL} ...")
        r = SESSION.get(INDEX_URL, timeout=60)
        r.raise_for_status()
        INDEX_CACHE.write_bytes(r.content)
        print(f"  cached at {INDEX_CACHE} ({len(r.content):,} bytes)")
    df = pd.read_csv(INDEX_CACHE)
    print(f"Index has {len(df):,} rows; columns: {list(df.columns)}")
    # MS uses "Location" (country name) — case may vary in revisions.
    loc_col = next((c for c in df.columns if c.lower() == "location"), None)
    if loc_col is None:
        msg = f"Index CSV missing 'Location' column. Got: {list(df.columns)}"
        raise ValueError(msg)
    idn = df[df[loc_col].str.lower() == "indonesia"].copy()
    print(f"Indonesia rows: {len(idn):,}")
    return idn


def download_one(row: pd.Series, out_dir: Path) -> tuple[str, int, str]:
    """Download a single tile. Returns (quadkey, bytes, status)."""
    url = row["Url"]
    quadkey = str(row.get("QuadKey", row.get("quadkey", "")))
    out_path = out_dir / f"{quadkey}.geojsonl.gz"
    if out_path.exists() and out_path.stat().st_size > 0:
        return quadkey, out_path.stat().st_size, "skip"
    try:
        r = SESSION.get(url, timeout=120, stream=True)
        r.raise_for_status()
        out_path.write_bytes(r.content)
        return quadkey, len(r.content), "ok"
    except Exception as e:  # noqa: BLE001 — top-level retry handler
        return quadkey, 0, f"error: {e}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", maxsplit=1)[0])
    p.add_argument("--workers", type=int, default=4, help="Parallel downloads (default: 4)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch index + count Indonesia tiles without downloading any",
    )
    p.add_argument("--refresh-index", action="store_true", help="Re-download dataset-links.csv")
    args = p.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    idn = fetch_index(force=args.refresh_index)

    if args.dry_run:
        # Estimate disk via the Size column if present. MS publishes Size as
        # a string with units (e.g. "12.3MB" / "456KB") — parse defensively.
        size_col = next((c for c in idn.columns if "size" in c.lower()), None)
        if size_col is not None:
            total_bytes = _parse_size_total(idn[size_col])
            print(f"Total estimated download: {total_bytes / 1e9:.2f} GB across {len(idn)} tiles")
        else:
            print("(no Size column in index — can't estimate download size)")
        return 0

    print(f"Downloading {len(idn):,} tiles with {args.workers} workers → {RAW_DIR}")
    n_skip = n_ok = n_err = bytes_ok = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(download_one, row, RAW_DIR) for _, row in idn.iterrows()]
        for fut in tqdm(as_completed(futures), total=len(futures), unit="tile"):
            _qk, n_bytes, status = fut.result()
            if status == "skip":
                n_skip += 1
            elif status == "ok":
                n_ok += 1
                bytes_ok += n_bytes
            else:
                n_err += 1
                tqdm.write(f"  ERROR {_qk}: {status}")

    print()
    print(f"Done. ok={n_ok}  skip={n_skip}  err={n_err}  total_new={bytes_ok / 1e9:.2f} GB")
    print(f"Files at: {RAW_DIR}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
