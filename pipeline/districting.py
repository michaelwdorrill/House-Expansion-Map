"""Draw equal-population, compact districts inside a state.

Two stages:
  1. Subdivide any county larger than the per-district target into roughly
     equal-area pieces (uniform-density assumption), so no single unit
     dominates a district.
  2. Recursively bisect the set of units along its principal axis at the
     population-balancing point -- a shortest-splitline variant. The cut is
     perpendicular to the longest axis, which keeps districts compact.

All geometry is in EPSG:5070 (equal area), so area-balanced cuts are
population-balanced under the uniform-density assumption.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

from units import CYCLES

VOTE_COLS = [f"{c}_{p}" for c in CYCLES for p in ("D", "R")]
_BISECT_ITERS = 16
_RESOLUTION = 30.0  # pieces ~ target_pop / _RESOLUTION (controls equal-population accuracy)
_MAX_PIECES = 1500  # cap subdivisions per county (runtime guard)


@dataclass
class Unit:
    geom: object
    pop: float
    votes: dict[str, float]
    cx: float = 0.0
    cy: float = 0.0

    def __post_init__(self):
        c = self.geom.representative_point()
        self.cx, self.cy = c.x, c.y


def bisect_polygon(poly, frac: float):
    """Split poly with an axis-aligned line so the first part has `frac` of area."""
    minx, miny, maxx, maxy = poly.bounds
    target = poly.area * frac
    vertical = (maxx - minx) >= (maxy - miny)
    lo, hi = (minx, maxx) if vertical else (miny, maxy)
    for _ in range(_BISECT_ITERS):
        mid = (lo + hi) / 2
        cutbox = box(minx, miny, mid, maxy) if vertical else box(minx, miny, maxx, mid)
        if poly.intersection(cutbox).area < target:
            lo = mid
        else:
            hi = mid
    mid = (lo + hi) / 2
    if vertical:
        first = poly.intersection(box(minx, miny, mid, maxy))
        second = poly.intersection(box(mid, miny, maxx, maxy))
    else:
        first = poly.intersection(box(minx, miny, maxx, mid))
        second = poly.intersection(box(minx, mid, maxx, maxy))
    return first, second


def subdivide_polygon(poly, k: int) -> list:
    if k <= 1 or poly.area <= 0:
        return [poly]
    a = k // 2
    first, second = bisect_polygon(poly, a / k)
    out = []
    if not first.is_empty:
        out += subdivide_polygon(first, a)
    if not second.is_empty:
        out += subdivide_polygon(second, k - a)
    return out or [poly]


def make_atomic_units(rows: list[dict], target_pop: float) -> list[Unit]:
    """rows: dicts with geom, pop, and vote columns. Subdivide oversized counties."""
    units: list[Unit] = []
    for r in rows:
        pop = float(r["pop"])
        geom = r["geom"]
        if pop <= 0 or geom.is_empty:
            continue
        k = max(1, int(np.ceil(pop / max(target_pop / _RESOLUTION, 1))))
        k = min(k, _MAX_PIECES)
        pieces = subdivide_polygon(geom, k) if k > 1 else [geom]
        total_area = sum(p.area for p in pieces) or 1.0
        for piece in pieces:
            share = piece.area / total_area
            units.append(
                Unit(
                    geom=piece,
                    pop=pop * share,
                    votes={c: float(r[c]) * share for c in VOTE_COLS},
                )
            )
    return units


def _principal_axis(units: list[Unit]) -> tuple[float, float]:
    pts = np.array([[u.cx, u.cy] for u in units])
    w = np.array([max(u.pop, 1e-9) for u in units])
    mean = np.average(pts, axis=0, weights=w)
    centered = pts - mean
    cov = (centered * w[:, None]).T @ centered / w.sum()
    vals, vecs = np.linalg.eigh(cov)
    axis = vecs[:, int(np.argmax(vals))]
    return float(axis[0]), float(axis[1])


def split_districts(units: list[Unit], seats: int) -> list[list[Unit]]:
    if seats <= 1 or len(units) <= 1:
        return [units]
    total_pop = sum(u.pop for u in units)
    a = seats // 2
    target = total_pop * a / seats
    ux, uy = _principal_axis(units)
    ordered = sorted(units, key=lambda u: u.cx * ux + u.cy * uy)
    acc, idx = 0.0, 0
    for i, u in enumerate(ordered):
        acc += u.pop
        if acc >= target:
            idx = i + 1
            break
    idx = min(max(idx, 1), len(ordered) - 1)
    left = split_districts(ordered[:idx], a)
    right = split_districts(ordered[idx:], seats - a)
    return left + right


@dataclass
class District:
    geom: object
    pop: float
    votes: dict[str, float] = field(default_factory=dict)


def build_districts(rows: list[dict], seats: int) -> list[District]:
    """rows: county dicts (geom, pop, vote cols). Returns `seats` districts."""
    if seats < 1:
        return []
    total_pop = sum(float(r["pop"]) for r in rows)
    target = total_pop / seats
    units = make_atomic_units(rows, target)
    # Guarantee enough units to form `seats` districts.
    while len(units) < seats:
        units.sort(key=lambda u: u.pop, reverse=True)
        big = units.pop(0)
        a, b = bisect_polygon(big.geom, 0.5)
        ta = (a.area + b.area) or 1.0
        for piece in (a, b):
            if piece.is_empty:
                continue
            share = piece.area / ta
            units.append(Unit(piece, big.pop * share, {c: big.votes[c] * share for c in VOTE_COLS}))
    groups = split_districts(units, seats)
    districts = []
    for grp in groups:
        geom = unary_union([u.geom for u in grp])
        pop = sum(u.pop for u in grp)
        votes = {c: sum(u.votes[c] for u in grp) for c in VOTE_COLS}
        districts.append(District(geom=geom, pop=pop, votes=votes))
    return districts
