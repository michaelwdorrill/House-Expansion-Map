"""Generate per-scenario district maps for the whole country and export to docs/data/.

For each House size we apportion seats (Huntington-Hill), draw districts in
every state (districting.build_districts), then write a GeoJSON of districts
(geometry + raw vote columns so the browser can compute any partisan model
live). Also writes state outlines and a manifest with provenance.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import geopandas as gpd

import sources
from apportion import apportion, cube_root_size, people_per_rep, wyoming_rule_size
from districting import VOTE_COLS, build_districts
from states import FIPS_TO_NAME, FIPS_TO_USPS, STATES, TOTAL_APPORTIONMENT_POP
from units import CYCLES, load_counties

OUT = Path(__file__).resolve().parent.parent / "docs" / "data"
DISTRICT_SIMPLIFY_M = 700
STATE_SIMPLIFY_M = 1200
COORD_DECIMALS = 4

SCENARIOS = [435, wyoming_rule_size(), cube_root_size(), 870, 1000, 1500]


def _round_coords(obj):
    """Recursively round coordinate floats in a GeoJSON geometry tree."""
    if isinstance(obj, float):
        return round(obj, COORD_DECIMALS)
    if isinstance(obj, list):
        return [_round_coords(x) for x in obj]
    return obj


def _round_geojson(gdf: gpd.GeoDataFrame) -> list[dict]:
    """Return GeoJSON features with coordinates rounded to COORD_DECIMALS."""
    gj = json.loads(gdf.to_json())
    for f in gj["features"]:
        if f.get("geometry"):
            f["geometry"]["coordinates"] = _round_coords(f["geometry"]["coordinates"])
    return gj["features"]


def build_states(counties: gpd.GeoDataFrame) -> dict:
    diss = counties.dissolve(by="state_fips").reset_index()
    diss["geometry"] = diss.geometry.simplify(STATE_SIMPLIFY_M).buffer(0)
    diss["name"] = diss["state_fips"].map(FIPS_TO_NAME)
    diss["usps"] = diss["state_fips"].map(FIPS_TO_USPS)
    diss = diss[["state_fips", "name", "usps", "geometry"]].to_crs(4326)
    return {"type": "FeatureCollection", "features": _round_geojson(diss)}


def build_scenario(counties: gpd.GeoDataFrame, n: int) -> dict:
    seats = apportion(n)
    records = []
    for state_fips, sub in counties.groupby("state_fips"):
        name = FIPS_TO_NAME[state_fips]
        s = seats[name]
        rows = [
            dict(geom=r.geometry, pop=r["pop"], **{c: r[c] for c in VOTE_COLS})
            for _, r in sub.iterrows()
        ]
        districts = build_districts(rows, s)
        for i, d in enumerate(districts):
            rec = {
                "id": f"{FIPS_TO_USPS[state_fips]}-{i + 1:03d}",
                "st": FIPS_TO_USPS[state_fips],
                "pop": int(round(d.pop)),
                "geometry": d.geom.simplify(DISTRICT_SIMPLIFY_M).buffer(0),
            }
            for c in VOTE_COLS:
                rec[c] = int(round(d.votes[c]))
            records.append(rec)
    gdf = gpd.GeoDataFrame(records, geometry="geometry", crs=5070).to_crs(4326)
    return {"type": "FeatureCollection", "features": _round_geojson(gdf)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Loading counties ...")
    counties = load_counties()

    print("Building state outlines ...")
    (OUT / "states.geojson").write_text(json.dumps(build_states(counties)))

    manifest = {
        "scenarios": [],
        "cycles": CYCLES,
        "voteCols": VOTE_COLS,
        "totalApportionmentPop": TOTAL_APPORTIONMENT_POP,
        "currentHouseSize": 435,
        "references": {"wyomingRule": wyoming_rule_size(), "cubeRoot": cube_root_size()},
        "citations": sources.CITATIONS,
        "states": {usps: name for name, (_f, usps, _p) in STATES.items()},
    }

    for n in sorted(set(SCENARIOS)):
        t = time.time()
        fc = build_scenario(counties, n)
        path = OUT / f"scenario-{n}.json"
        path.write_text(json.dumps(fc))
        kb = path.stat().st_size / 1024
        manifest["scenarios"].append(
            {"size": n, "peoplePerRep": round(people_per_rep(n)), "file": path.name,
             "districts": len(fc["features"])}
        )
        print(f"  N={n}: {len(fc['features'])} districts, {kb:.0f} KB, {time.time() - t:.1f}s")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print("Wrote manifest with scenarios:", [s["size"] for s in manifest["scenarios"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
