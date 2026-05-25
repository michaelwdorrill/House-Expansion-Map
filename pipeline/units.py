"""Build the atomic-unit table: county geometry + population + votes, per state.

Units are US counties. Geometry comes from the us-10m TopoJSON (EPSG:4326),
reprojected to US Albers Equal Area (EPSG:5070) so that area-balanced splits
are also population-balanced under a uniform-density assumption. Population
and presidential votes are joined on 5-digit FIPS.
"""
from __future__ import annotations

import csv
from pathlib import Path

import geopandas as gpd
import pandas as pd

from states import FIPS_TO_NAME

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
ALBERS = 5070
CYCLES = ["PRES16", "PRES20", "PRES24"]


def _fips5(value) -> str:
    return str(value).split(".")[0].zfill(5)


def load_population() -> dict[str, int]:
    out: dict[str, int] = {}
    with open(RAW / "county_population.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["Country_Region"] != "US" or not row["FIPS"] or not row["Admin2"]:
                continue
            try:
                pop = int(float(row["Population"]))
            except (ValueError, KeyError):
                continue
            if pop > 0:
                out[_fips5(row["FIPS"])] = pop
    return out


def load_results(cycle: str) -> dict[str, tuple[int, int]]:
    """Return {fips: (dem_votes, rep_votes)} for a presidential cycle."""
    out: dict[str, tuple[int, int]] = {}
    with open(RAW / f"results_{cycle}.csv", newline="") as f:
        for row in csv.DictReader(f):
            fips = row.get("county_fips") or row.get("combined_fips")
            if not fips:
                continue
            try:
                dem = int(float(row["votes_dem"]))
                rep = int(float(row["votes_gop"]))
            except (ValueError, KeyError):
                continue
            out[_fips5(fips)] = (dem, rep)
    return out


def load_counties() -> gpd.GeoDataFrame:
    """All US counties as a GeoDataFrame in EPSG:5070 with pop + vote columns."""
    gdf = gpd.read_file(RAW / "us-10m.json", layer="counties")
    gdf["fips"] = gdf["id"].map(_fips5) if "id" in gdf.columns else gdf.index.map(_fips5)
    gdf = gdf.set_crs(4326).to_crs(ALBERS)
    gdf["geometry"] = gdf.geometry.make_valid()

    pop = load_population()
    gdf["pop"] = gdf["fips"].map(pop).fillna(0).astype(int)

    for cycle in CYCLES:
        res = load_results(cycle)
        gdf[f"{cycle}_D"] = gdf["fips"].map(lambda f, r=res: r.get(f, (0, 0))[0]).astype(int)
        gdf[f"{cycle}_R"] = gdf["fips"].map(lambda f, r=res: r.get(f, (0, 0))[1]).astype(int)

    gdf["state_fips"] = gdf["fips"].str[:2]
    gdf = gdf[gdf["state_fips"].isin(FIPS_TO_NAME)].copy()
    # Drop zero-population slivers (water polygons etc.).
    gdf = gdf[gdf["pop"] > 0].copy()
    return gdf


def state_counties(gdf: gpd.GeoDataFrame, state_fips: str) -> gpd.GeoDataFrame:
    return gdf[gdf["state_fips"] == state_fips].copy()


if __name__ == "__main__":
    g = load_counties()
    print("counties:", len(g), "| total pop:", int(g["pop"].sum()))
    print("states present:", g["state_fips"].nunique())
    pa = state_counties(g, "42")
    print("PA counties:", len(pa), "| PA pop:", int(pa["pop"].sum()),
          "| PRES20 D/R:", int(pa["PRES20_D"].sum()), int(pa["PRES20_R"].sum()))
