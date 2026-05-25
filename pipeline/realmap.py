"""Build the real-current-districts baseline from Census TIGER CD boundaries.

Every other scenario in this project draws *neutral* (partisan-blind) districts.
This one is different: it uses the ACTUAL 119th-Congress district boundaries --
the real, gerrymandered map -- so the app can show today's distortion as a
baseline rather than a hypothetical fair redraw.

Counties split across districts, so county-level presidential votes are
apportioned onto each district by area of intersection (the same uniform-
density assumption the splitline districting already relies on). The partisan
lean of a real district is therefore an areal estimate, not a precinct-exact
figure -- consistent with the county-resolution honesty caveat in the README.

Requires data/raw/cd119.zip (Census TIGER), which only resolves on an
unrestricted network. See .github/workflows/build-data.yml.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from districting import VOTE_COLS
from states import FIPS_TO_NAME, FIPS_TO_USPS
from units import load_counties

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
ALBERS = 5070
CD_ZIP = RAW / "cd119.zip"


def _state_col(cols) -> str:
    for c in cols:
        if c.upper().startswith("STATEFP"):
            return c
    raise KeyError("no STATEFP column in CD shapefile")


def _cd_col(cols) -> str:
    for c in cols:
        u = c.upper()
        if u.startswith("CD") and u.endswith("FP"):
            return c
    raise KeyError("no CD###FP column in CD shapefile")


def _geoid_col(cols) -> str:
    for c in cols:
        if c.upper().startswith("GEOID"):
            return c
    raise KeyError("no GEOID column in CD shapefile")


def _district_label(usps: str, cd: str) -> str:
    """Real-district id, e.g. 'TX-7' or at-large 'WY-AL'."""
    if cd in ("00", "98"):
        return f"{usps}-AL"
    try:
        return f"{usps}-{int(cd)}"
    except ValueError:
        return f"{usps}-{cd}"


def build_real_map(counties: gpd.GeoDataFrame | None = None) -> gpd.GeoDataFrame | None:
    """Return real CDs (EPSG:5070) with id, st, pop, and vote columns, or None.

    Returns None when the CD shapefile is unavailable, so callers can skip the
    real-lines baseline without failing the rest of the build.
    """
    if not CD_ZIP.exists():
        print("  (no cd119.zip; skipping real-lines baseline)")
        return None

    cds = gpd.read_file(f"zip://{CD_ZIP}")
    statecol, cdcol, geoidcol = _state_col(cds.columns), _cd_col(cds.columns), _geoid_col(cds.columns)
    cds = cds[cds[statecol].isin(FIPS_TO_NAME)].copy()
    cds = cds[cds[cdcol] != "ZZ"].copy()  # drop water / unassigned areas
    cds = cds.to_crs(ALBERS)
    cds["geometry"] = cds.geometry.make_valid()
    cds = cds.rename(columns={geoidcol: "geoid"})[["geoid", statecol, cdcol, "geometry"]]

    if counties is None:
        counties = load_counties()
    counties = counties.to_crs(ALBERS).copy()
    counties["geometry"] = counties.geometry.make_valid()
    counties["_carea"] = counties.geometry.area
    cpoly = counties[["fips", "_carea", "pop", *VOTE_COLS, "geometry"]]

    # Areal apportionment: split county vote/pop by share of county area in each CD.
    inter = gpd.overlay(cds, cpoly, how="intersection", keep_geom_type=True)
    inter["_frac"] = (inter.geometry.area / inter["_carea"]).clip(upper=1.0)
    for col in ("pop", *VOTE_COLS):
        inter[col] = inter[col] * inter["_frac"]
    agg = inter.groupby("geoid", as_index=False)[["pop", *VOTE_COLS]].sum()

    gdf = cds.merge(agg, on="geoid", how="left")
    gdf[["pop", *VOTE_COLS]] = gdf[["pop", *VOTE_COLS]].fillna(0)
    gdf["st"] = gdf[statecol].map(FIPS_TO_USPS)
    gdf["id"] = [_district_label(u, c) for u, c in zip(gdf["st"], gdf[cdcol])]
    for col in ("pop", *VOTE_COLS):
        gdf[col] = gdf[col].round().astype(int)

    out = gpd.GeoDataFrame(
        gdf[["id", "st", "pop", *VOTE_COLS, "geometry"]], geometry="geometry", crs=ALBERS
    )
    print(f"  real-lines baseline: {len(out)} districts from cd119.zip")
    return out


if __name__ == "__main__":
    g = build_real_map()
    if g is not None:
        print(g[["id", "st", "pop"]].head(10).to_string(index=False))
        print("total districts:", len(g), "| total pop:", int(g["pop"].sum()))
