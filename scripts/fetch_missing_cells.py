"""
fetch_missing_cells.py — Direct HTTPS fetch of specific S2 cells from
the public Open Buildings v3 GCS bucket.

Companion to check_open_buildings_coverage.py: once you know which cells
are still missing, this script fetches them directly via
https://storage.googleapis.com/... — bypasses gcsfs and tensorflow,
runs much faster than the country-wide downloader.

Usage:
    # Fetch a specific list of tokens
    uv run python scripts/fetch_missing_cells.py 2d65 2e17 2fd5

    # Or auto-detect from the coverage check
    uv run python scripts/fetch_missing_cells.py --auto
"""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_CELLS_DIR = REPO_ROOT / "data" / "open_buildings" / "_tmp_cells"
HTTPS_BASE = (
    "https://storage.googleapis.com/open-buildings-data/v3/polygons_s2_level_6_gzip_no_header"
)


def fetch_one(token: str, retries: int = 3, timeout: int = 120) -> tuple[str, str | None]:
    """Download one cell's gzipped CSV directly. Returns (token, path or None)."""
    out_path = TMP_CELLS_DIR / f"{token}.csv.gz"
    if out_path.exists() and out_path.stat().st_size > 0:
        return token, str(out_path)

    url = f"{HTTPS_BASE}/{token}_buildings.csv.gz"
    for attempt in range(retries):
        try:
            t0 = time.time()
            r = requests.get(url, stream=True, timeout=timeout)
            HTTP_NOT_FOUND = 404
            if r.status_code == HTTP_NOT_FOUND:
                # No data file for this cell — that's fine, just means no detected buildings
                return token, None
            r.raise_for_status()
            tmp_path = out_path.with_suffix(".csv.gz.partial")
            size = 0
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):
                    f.write(chunk)
                    size += len(chunk)
            tmp_path.rename(out_path)
            elapsed = time.time() - t0
            mb = size / 1_000_000
            speed = mb / elapsed if elapsed > 0 else 0.0
            print(f"  ✓ {token}: {mb:.1f} MB in {elapsed:.1f}s ({speed:.1f} MB/s)")
            return token, str(out_path)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"  ⚠ {token}: attempt {attempt + 1}/{retries} failed ({type(e).__name__})")
            if attempt == retries - 1:
                print(f"  ✗ {token}: gave up after {retries} attempts")
                return token, None
            time.sleep(2**attempt)  # exponential backoff
        except Exception as e:
            print(f"  ✗ {token}: {type(e).__name__}: {e}")
            return token, None
    return token, None


def auto_detect_missing() -> list[str]:
    """Re-run coverage check to find missing tokens."""
    import subprocess

    result = subprocess.run(
        ["uv", "run", "python", "scripts/check_open_buildings_coverage.py"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    # Parse the "Missing tokens to download:" line
    for line in result.stdout.splitlines():
        if "Missing tokens to download:" in line:
            tokens_str = line.split(":", 1)[1].strip()
            # Format: ['t1', 't2', ...]
            tokens = [
                t.strip().strip("'").strip('"')
                for t in tokens_str.strip("[]").split(",")
                if t.strip().strip("'").strip('"')
            ]
            return tokens
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tokens", nargs="*", help="S2 level-6 tokens to fetch")
    parser.add_argument("--auto", action="store_true", help="Auto-detect missing cells")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=180, help="Per-cell timeout seconds")
    args = parser.parse_args()

    if args.auto:
        tokens = auto_detect_missing()
        if not tokens:
            print("No missing cells. ✅")
            return 0
    else:
        tokens = args.tokens

    if not tokens:
        print("Usage: fetch_missing_cells.py TOKEN [TOKEN ...] | --auto", file=sys.stderr)
        return 1

    TMP_CELLS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {len(tokens)} cells with {args.workers} parallel workers (HTTPS direct)")
    print(f"Output dir: {TMP_CELLS_DIR}\n")

    t0 = time.time()
    results: dict[str, str | None] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(fetch_one, token, retries=3, timeout=args.timeout): token for token in tokens
        }
        for fut in concurrent.futures.as_completed(futures):
            token, path = fut.result()
            results[token] = path

    elapsed = time.time() - t0
    success = sum(1 for v in results.values() if v)
    no_data = sum(1 for v in results.values() if v is None)
    print(
        f"\nDone in {elapsed:.0f}s. {success} cells with data, {no_data} with no data (404/empty)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
