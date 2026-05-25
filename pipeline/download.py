"""Fetch raw source data into data/raw/ (idempotent, cached)."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import sources

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def fetch(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  cached  {dest.name}")
        return
    print(f"  GET     {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "house-expansion-map/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.write_bytes(data)
    print(f"  saved   {dest.name}  ({len(data):,} bytes)")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    fetch(sources.GEOMETRY_US_10M, RAW / "us-10m.json")
    fetch(sources.COUNTY_POPULATION, RAW / "county_population.csv")
    for key, url in sources.COUNTY_RESULTS.items():
        fetch(url, RAW / f"results_{key}.csv")

    # Real congressional-district boundaries: only reachable on an unrestricted
    # network. Best-effort so the neutral pipeline still builds when it is blocked.
    try:
        fetch(sources.CD_BOUNDARIES, RAW / "cd119.zip")
    except Exception as exc:  # noqa: BLE001
        print(f"  SKIP    cd119.zip ({exc}) -- real-lines baseline will be omitted")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
