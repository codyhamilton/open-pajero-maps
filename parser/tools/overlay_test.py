"""Overlay test (Plan 03 unit 2-08, re-run of 2-03): decode reference disc R
road links at the per-class coordinate range from
`refdata/profile/coord_scale.json` and decide the REDEFINED coordinate gate
(DESIGN Decisions, Amendment 2026-09-22, item 1): relative discrimination
against alternative ranges, plus R-only measures.  OSM match rate is a
diagnostic only.

Reads R only through `harness.walk` helpers (leaf frames from
`walk._leaf_frame`); imports no writer module.  y is up (coordconv, 2-06).

Stated rules and thresholds (fixed before any run; none is tuned afterwards):

  * thresholds: MARGIN_MATCH = 1.5, MARGIN_DIST = 2.0, MAX_REL_LO = 0.9,
    MAX_REL_HI = 1.0, AXIS_COVERAGE_MIN = 0.75, CLIP_EXACT_MIN = 0.9,
    CLIP_NEAR = 0.005, MIN_CLIPPED_LINKS = 50, MIN_LINKS = 20,
    MIN_LINKS_STRICT = 50, POOL_N = 12, GRID_N = 16, tol = harness.json
    bands.name_record_distance_tolerance.tol (0.005).
  * named cells: Brisbane CBD and Sydney from `spot_checks.json`; rural QLD
    (Longreach) and outback (Birdsville) as the nearest undivided leaf to the
    locality, searched from the finest listed level outwards, that has
    >= MIN_LINKS road links.  Ranked by (level order, distance from locality
    to leaf bbox, distance to bbox centre, ids).  Match quality is never an
    input to the choice.  All four are evaluated.
  * pooled cells: for each coordinate class (L0 urban, L0 sparse, L2, L4, L6,
    L8, divided) take POOL_N blocks spread evenly through that level's
    on-disc list of non-empty blocks (index round(i*(N-1)/(POOL_N-1))), and in
    each chosen block the first leaf of that class, in leaf index order, with
    >= MIN_LINKS road links; if a block has none, advance to the next block in
    the list.  Deterministic and independent of match quality.
  * cell_extent_m = max(width_m, height_m) of the cell bbox.  The cell used
    for the OSM comparison is the geographic region the links occupy: the 4x4
    integrated parcel for L0 sparse, else the leaf; it is the same for the
    model and every alternative.
  * OSM class set per level (like-for-like: R stores fewer roads at coarser
    levels) -- L0/L2 all roads, L4 motorway..tertiary, L6/L8 motorway/trunk/
    primary.  Non-road highway values are always excluded.
  * match: each R link -> the OSM way minimising the median point-to-polyline
    distance over the link's vertices.  Matched iff that median
    <= tol * tol_extent_m.
  * tol_extent (decided before the run): tol scales the FRAME extent
    (max(width_m, height_m) of the frame the coordinates are decoded in), not
    the leaf extent, because the band's own basis is R's quantisation grid and
    that grid spans the frame.  Leaf-basis matched fractions are reported as a
    diagnostic.
  * frames: the model frame of a leaf comes from `walk._leaf_frame` (L0 sparse:
    the 4x4 tile, range 16384); divided sub-parcels use the parent leaf's bbox
    at range 4096 (sub 0 = SW quadrant); every other class uses the leaf bbox.
    The range per class comes from coord_scale.json.
  * CRITERION (a), relative discrimination, pooled per parcel class.  The
    alternative set is {range/2, range*2, 32768}; divided adds own_bounds and
    quadrant_4096; L0 sparse adds own_leaf_16384, own_leaf_4096 and
    tile4x4_4096.  A class passes (a) iff the assumed range's pooled matched
    fraction >= MARGIN_MATCH x every alternative's AND its pooled median
    matched-link distance <= 1/MARGIN_DIST of every alternative's.  An
    alternative with a zero matched fraction (or no matched links) passes
    trivially (no division by zero).
  * CRITERION (b), R-only (no OSM input), pooled per parcel class:
      coord_max_over_range: pooled (over cells) median of each cell's
        max coordinate / class range >= MAX_REL_LO and pooled maximum
        <= MAX_REL_HI.
      axis_coverage: over a GRID_N x GRID_N grid on the frame,
        max(rows holding an R vertex, columns holding an R vertex) / GRID_N;
        pooled median >= AXIS_COVERAGE_MIN.  (OSM-relative occupied fraction is
        a diagnostic.)
      clip_exact_share: among links with an end node within CLIP_NEAR * range
        of a frame edge, the share where that coordinate is exactly 0 or
        exactly the range; pooled >= CLIP_EXACT_MIN over >= MIN_CLIPPED_LINKS
        such links, else `insufficient_data` (not a pass).
  * named cells: each is judged on (a) and (b) on its own links; a named cell
    is a gate failure only if it fails a criterion with >= MIN_LINKS_STRICT
    links, otherwise its verdict is `low_n`.  The gate itself is decided on the
    pooled per-class results.
  * DIAGNOSTICS (no threshold, cannot fail the gate): matched fraction, p50/p90
    residual distance of matched links, leaf-basis matched fraction, occupied
    ratio, y-down orientation, and `source_disagreement_baseline` = fraction of
    like-for-like OSM ways in the cell whose median distance to the nearest R
    link exceeds the tolerance (roads OSM has and R does not).  The first run's
    absolute criteria (MATCH_MIN 0.8, OCC_RATIO_MIN 0.5, CLIP_MIN 0.9 on the
    per-cell `analyze` result) are retained only as legacy per-cell diagnostics.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The pre-Plan-03 decoder's fixed 2**15 range, kept only as the named
# `control_32768` hypothesis variant; nothing decodes or inverts with it.
CONTROL_RANGE_32768 = 32768.0
GRID_N = 16
MIN_LINKS = 20
POOL_N = 12
MARGIN_MATCH = 1.5
MARGIN_DIST = 2.0
MAX_REL_HI = 1.0
AXIS_COVERAGE_MIN = 0.75
CLIP_EXACT_MIN = 0.9
MIN_CLIPPED_LINKS = 50
MIN_LINKS_STRICT = 50
MATCH_MIN = 0.8
OCC_RATIO_MIN = 0.5
MAX_REL_LO = 0.9
CLIP_MIN = 0.9
CLIP_NEAR = 0.005
CLIP_NEAR_TIGHT = 0.001

NON_ROAD = {"footway", "path", "cycleway", "steps", "pedestrian", "bridleway",
            "corridor", "proposed", "construction", "raceway", "platform"}
MAJOR = {"motorway", "trunk", "primary", "motorway_link", "trunk_link",
         "primary_link"}
MID = MAJOR | {"secondary", "tertiary", "secondary_link", "tertiary_link"}


def osm_class_set(level: int):
    """Like-for-like OSM highway values for a level; None = all roads."""
    if level >= 6:
        return MAJOR
    if level >= 4:
        return MID
    return None


CELL_SPECS = [
    {"name": "Brisbane CBD", "source": "spot_checks.json Brisbane", "levels": [2, 4],
     "lat": -27.4698, "lon": 153.0251, "window": 0.3},
    {"name": "Sydney", "source": "spot_checks.json Sydney", "levels": [2, 4],
     "lat": -33.8688, "lon": 151.2093, "window": 0.3},
    {"name": "rural QLD (Longreach)", "source": "named locality Longreach QLD",
     "levels": [2, 4, 6, 8], "lat": -23.4420, "lon": 144.2500, "window": 4.0},
    {"name": "outback (Birdsville)", "source": "named locality Birdsville QLD",
     "levels": [4, 6, 8], "lat": -25.9000, "lon": 139.3500, "window": 4.0},
]

# Pooled classes: (key, level, parcel_type, urban flag or None)
POOL_CLASSES = [
    ("L0_urban", 0, 0, True),
    ("L0_sparse", 0, 0, False),
    ("L2", 2, 0, None),
    ("L4", 4, 0, None),
    ("L6", 6, 0, None),
    ("L8", 8, 0, None),
    ("divided_pardiv1", 0, 1, None),
]


# ---------------------------------------------------------------- pure math

def densify(pts: np.ndarray, step: float) -> np.ndarray:
    """Sample a polyline (n,2) at ~step spacing, keeping vertices."""
    out = [pts[:1]]
    for a, b in zip(pts[:-1], pts[1:]):
        d = float(np.hypot(*(b - a)))
        k = max(1, int(math.ceil(d / step)))
        t = (np.arange(1, k + 1) / k)[:, None]
        out.append(a + (b - a) * t)
    return np.vstack(out)


def occupied_fraction(polys, n: int = GRID_N, step: float = 1.0 / 64) -> float:
    """Share of an n x n grid over the unit cell holding polyline samples."""
    cells = set()
    for p in polys:
        if len(p) == 0:
            continue
        q = densify(np.asarray(p, float), step) if len(p) > 1 else np.asarray(p, float)
        q = q[(q[:, 0] >= 0) & (q[:, 0] <= 1) & (q[:, 1] >= 0) & (q[:, 1] <= 1)]
        ij = np.minimum((q * n).astype(int), n - 1)
        cells.update(map(tuple, ij))
    return len(cells) / float(n * n)


def _seg_dist(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """Distance from each of pts (m,2) to polyline poly (k,2), same units."""
    if len(poly) == 1:
        return np.hypot(*(pts - poly[0]).T)
    a, b = poly[:-1], poly[1:]
    ab = b - a
    L2 = np.maximum((ab ** 2).sum(1), 1e-12)
    best = np.full(len(pts), np.inf)
    for i in range(0, len(pts), 512):
        p = pts[i:i + 512, None, :]
        t = np.clip(((p - a) * ab).sum(2) / L2, 0, 1)
        proj = a + t[..., None] * ab
        best[i:i + 512] = np.hypot(*(p - proj).transpose(2, 0, 1)).min(1)
    return best


class WayIndex:
    """Nearest-way lookup over densified OSM ways (metre coordinates)."""

    def __init__(self, ways_m: list[np.ndarray], spacing: float):
        self.ways = ways_m
        samp, wid = [], []
        for i, w in enumerate(ways_m):
            s = densify(w, spacing)
            samp.append(s)
            wid.append(np.full(len(s), i))
        self.samp = np.vstack(samp) if samp else np.zeros((0, 2))
        self.wid = np.concatenate(wid) if wid else np.zeros(0, int)

    def nearest_way(self, pts: np.ndarray) -> np.ndarray:
        out = np.empty(len(pts), int)
        for i in range(0, len(pts), 256):
            d = ((pts[i:i + 256, None, :] - self.samp[None]) ** 2).sum(2)
            out[i:i + 256] = self.wid[d.argmin(1)]
        return out

    def match(self, pts: np.ndarray) -> tuple[float, int]:
        """(median point-to-polyline distance, index) of the best-following way."""
        if len(self.ways) == 0 or len(pts) == 0:
            return math.inf, -1
        sub = pts if len(pts) <= 40 else pts[np.linspace(0, len(pts) - 1, 40).astype(int)]
        cand = self.nearest_way(sub)
        ids, cnt = np.unique(cand, return_counts=True)
        top = ids[np.argsort(-cnt, kind="stable")[:3]]
        scored = [(float(np.median(_seg_dist(pts, self.ways[i]))), int(i)) for i in sorted(top)]
        return min(scored)


# ----------------------------------------------------------------- decoding

def decode_uv(pts_raw: np.ndarray, frame, cell, scale: float, y_up: bool) -> np.ndarray:
    """Raw (x, y) -> (u, v) of `cell` (u east, v south, 0..1), decoding in
    `frame` (a BoundingBox) at `scale`."""
    u = pts_raw[:, 0] / scale
    t = pts_raw[:, 1] / scale
    lon = frame.lon_lo + u * (frame.lon_hi - frame.lon_lo)
    lat = (frame.lat_lo + t * (frame.lat_hi - frame.lat_lo)) if y_up else \
          (frame.lat_hi - t * (frame.lat_hi - frame.lat_lo))
    return np.column_stack([(lon - cell.lon_lo) / (cell.lon_hi - cell.lon_lo),
                            (cell.lat_hi - lat) / (cell.lat_hi - cell.lat_lo)])


def extent_m(b):
    lat = (b.lat_lo + b.lat_hi) / 2
    return ((b.lon_hi - b.lon_lo) * 111320.0 * math.cos(math.radians(lat)),
            (b.lat_hi - b.lat_lo) * 110574.0)


def clip_stats(links, scale: float, near: float):
    n = exact = 0
    for l in links:
        for x, y in l["ends"]:
            gap = min(x, y, scale - x, scale - y)
            if gap <= near * scale:
                n += 1
                exact += gap == 0
    return exact, n


def axis_coverage(raw_pts, scale: float, n: int = GRID_N) -> float:
    """R-only: max(rows, columns of an n x n grid on the frame holding a
    vertex) / n.  Vertices outside [0, scale] are ignored."""
    p = np.asarray(raw_pts, float).reshape(-1, 2)
    p = p[(p >= 0).all(1) & (p <= scale).all(1)]
    if not len(p):
        return 0.0
    ij = np.minimum((p / scale * n).astype(int), n - 1)
    return max(len(set(ij[:, 0])), len(set(ij[:, 1]))) / float(n)


def clip_links(links, scale: float, near: float = CLIP_NEAR):
    """(exact, clipped): links with an end node within near*scale of a frame
    edge, and those whose such end lies exactly on the edge (coordinate 0 or
    scale).  Each link counts once."""
    clipped = exact = 0
    for l in links:
        gaps = [min(x, y, scale - x, scale - y) for x, y in l["ends"]]
        gaps = [g for g in gaps if g <= near * scale]
        if gaps:
            clipped += 1
            exact += min(gaps) == 0
    return exact, clipped


def source_disagreement(ways_m, r_links_m, limit: float, spacing: float) -> dict:
    """Fraction of OSM ways (metre coords, cell at origin) whose median distance
    from their in-cell samples to the nearest R link exceeds `limit`."""
    cloud = [densify(np.asarray(p, float), spacing) for p in r_links_m if len(p)]
    cloud = np.vstack(cloud) if cloud else np.zeros((0, 2))
    n = miss = 0
    for w in ways_m:
        s = densify(w, max(spacing, 1.0))
        s = s[np.linspace(0, len(s) - 1, min(len(s), 24)).astype(int)]
        n += 1
        if not len(cloud):
            miss += 1
            continue
        d = np.empty(len(s))
        for i in range(len(s)):
            d[i] = np.sqrt(((cloud - s[i]) ** 2).sum(1).min())
        miss += float(np.median(d)) > limit
    return {"osm_ways": n, "ways_without_r_link": int(miss),
            "source_disagreement_baseline": round(miss / n, 4) if n else None}


def criterion_a(model: dict, alts: dict) -> dict:
    """Relative discrimination of `model` (a pooled dict) vs each pooled
    alternative: matched fraction >= MARGIN_MATCH x, median matched distance
    <= 1/MARGIN_DIST x.  A zero-matched alternative passes trivially."""
    mf, md = model["matched_fraction"], model["matched_distance_m_p50"]
    per, ok = {}, True
    for name, a in sorted(alts.items()):
        af, ad = a["matched_fraction"], a["matched_distance_m_p50"]
        if af == 0:
            r, rp = None, True
        else:
            r = mf / af
            rp = mf >= MARGIN_MATCH * af
        if ad is None or af == 0:
            dr, dp = None, True
        else:
            dr = None if md is None else md / ad
            dp = md is not None and md <= ad / MARGIN_DIST
        per[name] = {"matched_fraction": af, "matched_distance_m_p50": ad,
                     "match_ratio_model_over_alt": None if r is None else round(r, 3),
                     "match_ratio_trivial_zero_alt": af == 0,
                     "dist_ratio_model_over_alt": None if dr is None else round(dr, 3),
                     "match_pass": bool(rp), "dist_pass": bool(dp), "pass": bool(rp and dp)}
        ok = ok and rp and dp
    ratios = [(v["match_ratio_model_over_alt"], k) for k, v in per.items()
              if v["match_ratio_model_over_alt"] is not None]
    dists = [(v["dist_ratio_model_over_alt"], k) for k, v in per.items()
             if v["dist_ratio_model_over_alt"] is not None]
    return {"alternatives": per, "pass": bool(ok),
            "model_matched_fraction": mf, "model_matched_distance_m_p50": md,
            "match_ratio_vs_best_alt": min(ratios)[0] if ratios else None,
            "best_alt_by_match": min(ratios)[1] if ratios else None,
            "dist_ratio_vs_best_alt": max(dists)[0] if dists else None,
            "best_alt_by_dist": max(dists)[1] if dists else None,
            "margins": {"match": MARGIN_MATCH, "dist": MARGIN_DIST}}


def criterion_b(results: list) -> dict:
    """R-only measures pooled over cells (analyze results of the model)."""
    cm = [r["coord_max_over_range"] for r in results]
    ax = [r["axis_coverage"] for r in results]
    ex = sum(r["_clip_exact"] for r in results)
    cl = sum(r["_clip_n"] for r in results)
    cmed = float(np.median(cm)) if cm else None
    cmax = max(cm) if cm else None
    amed = float(np.median(ax)) if ax else None
    share = ex / cl if cl else None
    v_cm = bool(cm) and cmed >= MAX_REL_LO and cmax <= MAX_REL_HI + 1e-9
    v_ax = bool(ax) and amed >= AXIS_COVERAGE_MIN
    v_cl = ("insufficient_data" if cl < MIN_CLIPPED_LINKS else
            ("pass" if share >= CLIP_EXACT_MIN else "fail"))
    return {
        "coord_max_over_range": {"median": None if cmed is None else round(cmed, 4),
                                 "max": cmax, "verdict": "pass" if v_cm else "fail"},
        "axis_coverage": {"median": None if amed is None else round(amed, 4),
                          "verdict": "pass" if v_ax else "fail"},
        "clip_exact_share": {"share": None if share is None else round(share, 4),
                             "clipped_links": cl, "exact": ex, "verdict": v_cl},
        "pass": bool(v_cm and v_ax and v_cl == "pass")}


def analyze(links, osm_ways_uv, cell, tol, scale, frame=None, y_up=True,
            tol_extent=None, _idx=None):
    """Overlay metrics for one cell decoded in `frame` (default: the cell) at
    `scale`.  `links`: dicts {"pts": [(x, y) raw], "ends": [(x, y) raw]}.
    `osm_ways_uv`: ways as (k,2) arrays in the cell's unit (u, v) coords."""
    frame = frame if frame is not None else cell
    w, h = extent_m(cell)
    extent = max(w, h)
    m = np.array([w, h])
    ways_m = [np.asarray(x, float) * m for x in osm_ways_uv]
    idx = _idx if _idx is not None else WayIndex(ways_m, spacing=max(tol * extent / 2.0, 1.0))
    r_uv = [decode_uv(np.asarray(l["pts"], float), frame, cell, scale, y_up)
            for l in links if len(l["pts"])]
    pairs = [idx.match(p * m) for p in r_uv]
    dists = np.array([d for d, _ in pairs]) if pairs else np.zeros(0)
    # The band's basis is "~20 units of the 4096/16384 grid", so the extent it
    # scales is the span the coordinate RANGE covers -- the frame, which is
    # wider than the leaf for divided sub-parcels and for L0 sparse tiles.
    limit = tol * (tol_extent if tol_extent else extent)
    matched = float((dists <= limit).mean()) if len(dists) else 0.0
    finite = dists[np.isfinite(dists)]
    q = (lambda p: float(np.percentile(finite, p)) if len(finite) else None)
    raw = np.vstack([np.asarray(l["pts"], float) for l in links if len(l["pts"])]) \
        if r_uv else np.zeros((0, 2))
    max_rel = float(raw.max() / scale) if len(raw) else 0.0
    inside = float(np.mean([(p >= -1e-9).all() and (p <= 1 + 1e-9).all()
                            for p in np.vstack(r_uv)])) if r_uv else 0.0
    # Like-for-like OSM subset: ways that R links match within tolerance, plus
    # every unmatched OSM way of the same class set (already filtered by level).
    r_occ = occupied_fraction(r_uv)
    o_occ = occupied_fraction(list(osm_ways_uv))
    exact, near = clip_stats(links, scale, CLIP_NEAR)
    exact_t, near_t = clip_stats(links, scale, CLIP_NEAR_TIGHT)
    share = exact / near if near else None
    ax_cov = axis_coverage(raw, scale) if len(raw) else 0.0
    ex_l, cl_l = clip_links(links, scale)
    md = finite[finite <= limit]
    res = {
        "axis_coverage": round(ax_cov, 4),
        "matched_distance_m_p50": None if not len(md) else round(float(np.median(md)), 4),
        "clip_exact_share": None if share is None else round(share, 4),
        "clip_exact_share_tight": None if not near_t else round(exact_t / near_t, 4),
        "clip_touching_ends": near,
        "coord_max_over_range": round(max_rel, 4),
        "cell_extent_m": round(extent, 1),
        "distance_limit_m": round(limit, 2),
        "frame_extent_m": round(tol_extent if tol_extent else extent, 1),
        "matched_fraction_leaf_basis": (
            round(float((dists <= tol * extent).mean()), 4) if len(dists) else 0.0),
        "distance_m_p50": None if q(50) is None else round(q(50), 2),
        "distance_m_p90": None if q(90) is None else round(q(90), 2),
        "inside_cell_fraction": round(inside, 4),
        "links": len(links),
        "matched_fraction": round(matched, 4),
        "occupied_fraction_osm": round(o_occ, 4),
        "occupied_fraction_r": round(r_occ, 4),
        "occupied_ratio": round(r_occ / o_occ, 4) if o_occ else None,
    }
    res["criteria"] = {
        "clipped_at_edge": share is not None and share >= CLIP_MIN,
        "coord_max": MAX_REL_LO <= max_rel <= 1.0 + 1e-9,
        "no_clustering": bool(o_occ and r_occ >= OCC_RATIO_MIN * o_occ),
        "within_tolerance": matched >= MATCH_MIN,
    }
    res["pass"] = all(res["criteria"].values())
    res["_dists"] = dists
    res["_lims"] = np.full(len(dists), limit)
    res["_clip_exact"], res["_clip_n"] = ex_l, cl_l
    res["_r_m"] = [p * m for p in r_uv]
    return res


def pool(results: list[dict], tol: float, extents: list[float]) -> dict:
    """Pooled statistics over cells: every link counts once."""
    d = np.concatenate([r["_dists"] for r in results]) if results else np.zeros(0)
    lim = np.concatenate([np.full(len(r["_dists"]), tol * e)
                          for r, e in zip(results, extents)]) if results else np.zeros(0)
    fin = d[np.isfinite(d)]
    matched_d = d[d <= lim]
    rel = (d / lim)[np.isfinite(d)] if len(d) else np.zeros(0)
    occ = [r["occupied_ratio"] for r in results if r["occupied_ratio"] is not None]
    clip = [r["clip_exact_share"] for r in results if r["clip_exact_share"] is not None]
    return {
        "cells": len(results),
        "cells_passing": sum(r["pass"] for r in results),
        "clip_exact_share_median": round(float(np.median(clip)), 4) if clip else None,
        "coord_max_over_range_max": round(max((r["coord_max_over_range"] for r in results),
                                              default=0.0), 4),
        "coord_max_over_range_median": round(float(np.median(
            [r["coord_max_over_range"] for r in results])), 4) if results else None,
        "dist_over_limit_p50": round(float(np.percentile(rel, 50)), 3) if len(rel) else None,
        "dist_over_limit_p90": round(float(np.percentile(rel, 90)), 3) if len(rel) else None,
        "distance_m_p50": round(float(np.percentile(fin, 50)), 2) if len(fin) else None,
        "distance_m_p90": round(float(np.percentile(fin, 90)), 2) if len(fin) else None,
        "links": int(len(d)),
        "matched_distance_m_p50": (round(float(np.median(matched_d)), 4)
                                   if len(matched_d) else None),
        "matched_distance_m_p90": (round(float(np.percentile(matched_d, 90)), 4)
                                   if len(matched_d) else None),
        "matched_fraction": round(float((d <= lim).mean()), 4) if len(d) else 0.0,
        "occupied_ratio_median": round(float(np.median(occ)), 4) if occ else None,
    }


# --------------------------------------------------------------- R reading

def _raw(lat, lon, b):
    """Invert coordconv's (y-up) decode to recover the raw (x, y) stored on
    disc, at the SAME range the decoder used (`b.coord_range`, the frame's
    `range_for`)."""
    rng = float(b.coord_range)
    return (round((lon - b.lon_lo) / (b.lon_hi - b.lon_lo) * rng, 6),
            round((lat - b.lat_lo) / (b.lat_hi - b.lat_lo) * rng, 6))


def _links(parcel, b):
    out = []
    for lk in parcel.road.links if parcel.road else []:
        pts = [_raw(la, lo, b) for la, lo in (lk.points or [])]
        ends = [(lk.nodes[i].x, lk.nodes[i].y) for i in (0, -1)] if lk.nodes else []
        if not pts and lk.nodes:
            pts = [(n.x, n.y) for n in lk.nodes]
        out.append({"pts": pts, "ends": ends})
    return out


def _box_dist(spec, b):
    dlat = max(b.lat_lo - spec["lat"], 0, spec["lat"] - b.lat_hi)
    dlon = max(b.lon_lo - spec["lon"], 0, spec["lon"] - b.lon_hi)
    return math.hypot(dlat, dlon * math.cos(math.radians(spec["lat"])))


def _urban(class_rule, bs_index, blk_index, leaf_index) -> bool:
    n = class_rule["l0_grid_width"]
    t = class_rule["l0_tile"]
    key = [bs_index, blk_index, (leaf_index // n) // t, (leaf_index % n) // t]
    return key in class_rule["urban_tiles"]


class RReader:
    """One open ALLDATA.KWI; decodes leaves on demand through harness.walk."""

    def __init__(self, ref: str):
        from harness import walk
        from kiwiw import volume
        self.walk, self.volume = walk, volume
        self.path = str(Path(ref) / "ALLDATA.KWI")
        c = walk.read_container(self.path)
        self.pdmdh = c.pdmdh
        self.ss, self.ls = c.hdr.sector_size, c.hdr.logical_sector_size
        self.fh = open(self.path, "rb")

    def blocks(self, level: int):
        """[(blockset_ordinal, blockset_index, block_index, entry, bounds)] in
        on-disc order for `level`."""
        lmr = next(l for l in self.pdmdh.levels if l.level == level)
        nbs = 1 + lmr.n_blocksets_lng
        nbl = 1 + lmr.n_blocks_lng
        out = []
        for ordn, bs in enumerate(self.pdmdh.blocksets):
            if bs.level != level:
                continue
            tab = next((t for t in self.pdmdh.bmt_tables if t.blockset_ordinal == ordn), None)
            if tab is None:
                continue
            bsy, bsx = divmod(bs.blockset_index, nbs)
            for ei, ent in enumerate(tab.entries):
                if ent.dsa == self.walk.NO_DATA_DSA or not ent.size:
                    continue
                bly, blx = divmod(ei, nbl)
                bb = self.walk._block_base_bounds(self.pdmdh, lmr, bsx, bsy, blx, bly)
                out.append((ordn, bs.blockset_index, ei, ent, bb))
        return lmr, out

    def leaves(self, lmr, blk):
        """[(leaf_path, entry, bounds, parcel_type, parent_bounds)] of a block."""
        _, _, _, ent, bb = blk
        self.fh.seek(self.volume.getsector(ent.dsa, self.ss, self.ls))
        try:
            root = self.walk.parse_parcel_mgmt_record(self.fh.read(ent.size * self.ls), lmr)
        except Exception:  # noqa: BLE001
            return []
        gn_lat = 1 + lmr.n_parcels_lat[0]
        gn_lng = 1 + lmr.n_parcels_lng[0]
        out = []
        cache: dict = {}
        for lpath, le, lb, ptype in self.walk._iter_tree_leaves(root, bb, lmr, ()):
            parent = self.walk._narrow_bounds(bb, gn_lat, gn_lng, lpath[0])
            fr = self.walk._leaf_frame(root, lmr.level, ptype, lpath, lb, bb, lmr, cache)
            out.append((lpath, le, lb, ptype, parent, fr))
        return out

    def decode(self, lmr, blk, leaf):
        from kiwiw.model import MeshLocation
        from kiwiw.parcel import decode_parcel
        _, bs_index, ei, _, _ = blk
        lpath, le, lb, ptype, _, (fb, fc) = leaf
        fb = self.walk.with_range(fb, self.walk.leaf_frame_range(lmr.level, ptype, lpath, fc))
        self.fh.seek(self.volume.getsector(le.dsa, self.ss, self.ls))
        buf = self.fh.read(le.size * self.ls)
        loc = MeshLocation(level=lmr.level, parcel_type=ptype, blockset_index=bs_index,
                           block_index=ei, parcel_index=lpath[-1], bounds=fb,
                           sector_addr=le.dsa, size_logical_sectors=le.size)
        try:
            p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
        except Exception:  # noqa: BLE001
            return None
        return _links(p, fb)


def pick_named(rdr, specs, class_rule):
    """Nearest qualifying undivided leaf to each named locality."""
    best = {}
    levels = sorted({lv for s in specs for lv in s["levels"]})
    for level in levels:
        want = [s for s in specs if level in s["levels"]]
        lmr, blks = rdr.blocks(level)
        for blk in blks:
            near = [s for s in want if _box_dist(s, blk[4]) <= s["window"]]
            if not near:
                continue
            for leaf in rdr.leaves(lmr, blk):
                lpath, _, lb, ptype, _, _ = leaf
                if ptype != 0:
                    continue
                for s in near:
                    d = _box_dist(s, lb)
                    if d > s["window"]:
                        continue
                    key = (s["levels"].index(level), round(d, 9),
                           round(math.hypot((lb.lat_lo + lb.lat_hi) / 2 - s["lat"],
                                            (lb.lon_lo + lb.lon_hi) / 2 - s["lon"]), 9),
                           blk[1], blk[2], lpath)
                    if s["name"] in best and key >= best[s["name"]]["key"]:
                        continue
                    links = rdr.decode(lmr, blk, leaf)
                    if links is None or len(links) < MIN_LINKS:
                        continue
                    best[s["name"]] = {
                        "key": key, "spec": s, "bounds": lb, "parent": leaf[4],
                        "links": links, "ptype": ptype, "level": level,
                        "sub": lpath[-1] if ptype else None,
                        "tile": leaf[5][0] if leaf[5][1] == "l0_sparse_tile" else tile_frame(
                            blk[4], lpath[0], 1 + lmr.n_parcels_lat[0],
                            1 + lmr.n_parcels_lng[0]),
                        "walk_frame_class": leaf[5][1],
                        "class": _class_key(level, ptype, class_rule, blk, lpath),
                        "ids": {"level": level, "blockset_index": blk[1],
                                "block_index": blk[2], "leaf_path": list(lpath)}}
    return best


def _class_key(level, ptype, class_rule, blk, lpath):
    if ptype == 1:
        return "divided_pardiv1"
    if level == 0:
        return "L0_urban" if _urban(class_rule, blk[1], blk[2], lpath[0]) else "L0_sparse"
    return f"L{level}"


def tile_frame(block, leaf_index: int, gn_lat: int, gn_lng: int, tile: int = 4):
    """The `tile` x `tile` group of leaves ("integrated parcel") containing
    `leaf_index` within its block -- the same 4x4 tile the coord_scale class
    rule keys L0 urban/sparse on."""
    from kiwiw.model import BoundingBox
    x, y = leaf_index % gn_lng, leaf_index // gn_lng
    lon_step = (block.lon_hi - block.lon_lo) / gn_lng
    lat_step = (block.lat_hi - block.lat_lo) / gn_lat
    lon_lo = block.lon_lo + (x // tile) * tile * lon_step
    lat_lo = block.lat_lo + (y // tile) * tile * lat_step
    return BoundingBox(lat_lo=lat_lo, lat_hi=lat_lo + tile * lat_step,
                       lon_lo=lon_lo, lon_hi=lon_lo + tile * lon_step)


def spread(items, k):
    """`items` reordered: k evenly spaced positions first, then the rest in
    order.  Deterministic, and independent of anything in the items."""
    n = len(items)
    if n == 0:
        return []
    first = [min(n - 1, round(i * (n - 1) / max(k - 1, 1))) for i in range(max(k, 1))]
    seen, order = set(), []
    for i in first + list(range(n)):
        if i not in seen:
            seen.add(i)
            order.append(items[i])
    return order


def pick_pooled(rdr, class_rule):
    """POOL_N cells per class, spread evenly through each level's block list
    and, within a block, through that block's leaf list."""
    out = {k: [] for k, _, _, _ in POOL_CLASSES}
    for key, level, ptype, urban in POOL_CLASSES:
        lmr, blks = rdr.blocks(level)
        if not blks:
            continue
        # divided parcels exist in only a handful of blocks, so let one block
        # supply the whole quota for that class
        per_block = POOL_N if ptype else max(1, math.ceil(POOL_N / len(blks)))
        taken = set()
        # pass 1 caps each block's share so the cells spread; pass 2 (only if
        # the quota is still short) lifts the cap, in on-disc order
        for cap in (per_block, POOL_N):
            if len(out[key]) >= POOL_N:
                break
            for blk in spread(blks, POOL_N):
                if len(out[key]) >= POOL_N:
                    break
                cand = []
                for leaf in rdr.leaves(lmr, blk):
                    lpath, _, _, lptype, _, _ = leaf
                    if lptype != ptype:
                        continue
                    if urban is not None and _urban(class_rule, blk[1], blk[2], lpath[0]) != urban:
                        continue
                    cand.append(leaf)
                took = 0
                for leaf in spread(cand, max(per_block * 8, 64)):
                    if took >= cap or len(out[key]) >= POOL_N:
                        break
                    lpath, _, lb, lptype, parent, _ = leaf
                    ident = (level, blk[1], blk[2], tuple(lpath))
                    if ident in taken:
                        took += 1
                        continue
                    links = rdr.decode(lmr, blk, leaf)
                    if links is None or len(links) < MIN_LINKS:
                        continue
                    took += 1
                    taken.add(ident)
                    out[key].append({
                        "bounds": lb, "parent": parent, "links": links, "ptype": lptype,
                        "level": level, "class": key, "sub": lpath[-1] if lptype else None,
                        "tile": leaf[5][0] if leaf[5][1] == "l0_sparse_tile" else tile_frame(
                            blk[4], lpath[0], 1 + lmr.n_parcels_lat[0],
                            1 + lmr.n_parcels_lng[0]),
                        "walk_frame_class": leaf[5][1],
                        "ids": {"level": level, "blockset_index": blk[1],
                                "block_index": blk[2], "leaf_path": list(lpath)}})
    return out


def model_frame(c, ranges):
    """(frame, range) for a cell under the coordinate model.  The two frame
    rules (divided -> parent leaf, L0 sparse -> 4x4 integrated parcel) are the
    ones established by the hypothesis sections of this same run; the range per
    class always comes from coord_scale.json."""
    if c["ptype"] == 1:
        return c["parent"], float(class_range(ranges, c["level"], c["class"], 1))
    if c["class"] == "L0_sparse":
        return c["tile"], float(class_range(ranges, c["level"], c["class"]))
    return c["bounds"], float(class_range(ranges, c["level"], c["class"]))


def model_cell(c):
    """The geographic cell a leaf's links actually occupy: the 4x4 integrated
    parcel for L0 sparse (its 16 leaf slots share one frame), else the leaf."""
    return c["tile"] if c["class"] == "L0_sparse" else c["bounds"]


def osm_frame(c):
    """The widest frame a cell is decoded in, so the OSM window covers it."""
    if c["ptype"] == 1:
        return c["parent"]
    if c["class"] == "L0_sparse":
        return c["tile"]
    return c["bounds"]


def class_range(ranges: dict, level: int, cls: str, sub=None) -> int:
    lv = ranges[str(level)]
    if cls == "divided_pardiv1":
        return int(lv["divided"][f"pardiv1_sub{sub}"]["max"])
    if cls == "L0_urban":
        return int(lv["urban"]["normal"]["max"])
    if cls == "L0_sparse":
        return int(lv["sparse"]["normal"]["max"])
    return int(lv["full"]["normal"]["max"])


# --------------------------------------------------------------- OSM reading

def read_osm(pbf: str, boxes: dict):
    """One PBF pass. `boxes`: {name: (lat_lo, lat_hi, lon_lo, lon_hi, classes)}
    where classes is a set of highway values or None for all roads.
    Returns {name: [[(lat, lon), ...], ...]} sorted by way id."""
    import osmium

    grid = {}
    for k, (a, b, c, d, _) in boxes.items():
        for gy in range(int(math.floor(a)), int(math.floor(b)) + 1):
            for gx in range(int(math.floor(c)), int(math.floor(d)) + 1):
                grid.setdefault((gy, gx), []).append(k)
    out = {k: [] for k in boxes}

    class H(osmium.SimpleHandler):
        def way(self, w):
            hw = w.tags.get("highway")
            if not hw or hw in NON_ROAD:
                return
            try:
                pts = [(n.lat, n.lon) for n in w.nodes]
            except Exception:  # noqa: BLE001
                return
            if len(pts) < 2:
                return
            la = [p[0] for p in pts]
            lo = [p[1] for p in pts]
            lo0, lo1, la0, la1 = min(lo), max(lo), min(la), max(la)
            cand = set()
            for gy in range(int(math.floor(la0)), int(math.floor(la1)) + 1):
                for gx in range(int(math.floor(lo0)), int(math.floor(lo1)) + 1):
                    cand.update(grid.get((gy, gx), ()))
            for k in cand:
                a, b, c, d, cls = boxes[k]
                if cls is not None and hw not in cls:
                    continue
                if la1 >= a and la0 <= b and lo1 >= c and lo0 <= d:
                    out[k].append((w.id, pts))

    H().apply_file(pbf, locations=True, idx="flex_mem")
    return {k: [p for _, p in sorted(v, key=lambda t: t[0])] for k, v in out.items()}


def to_uv(pts, b):
    return np.array([((lo - b.lon_lo) / (b.lon_hi - b.lon_lo),
                      (b.lat_hi - la) / (b.lat_hi - b.lat_lo)) for la, lo in pts])


def box_of(b, classes, pad_frac=0.02):
    pad = pad_frac * max(b.lat_hi - b.lat_lo, b.lon_hi - b.lon_lo)
    return (b.lat_lo - pad, b.lat_hi + pad, b.lon_lo - pad, b.lon_hi + pad, classes)


def strip(d):
    """Drop private keys from a result dict."""
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ----------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", required=True)
    ap.add_argument("--pbf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--osm-cache", default=None,
                    help="developer aid: cache the PBF pass keyed by the box set")
    a = ap.parse_args()

    prof = json.load(open(ROOT / "refdata/profile/coord_scale.json"))
    ranges, class_rule = prof["ranges"], prof["class_rule"]
    band = json.load(open(ROOT / "refdata/harness.json"))["bands"]["name_record_distance_tolerance"]
    tol = band["tol"]

    rdr = RReader(a.reference)
    named = pick_named(rdr, CELL_SPECS, class_rule)
    missing = [s["name"] for s in CELL_SPECS if s["name"] not in named]
    if missing:
        print("blocked: no qualifying cell for", missing, file=sys.stderr)
        return 2
    pooled = pick_pooled(rdr, class_rule)

    boxes = {}
    for nm, c in named.items():
        boxes["named:" + nm] = box_of(osm_frame(c), osm_class_set(c["level"]))
    for key, cells in pooled.items():
        for i, c in enumerate(cells):
            boxes[f"{key}:{i}"] = box_of(osm_frame(c), osm_class_set(c["level"]))

    cache = Path(a.osm_cache) if a.osm_cache else None
    key = json.dumps({k: [v[:4], sorted(v[4]) if v[4] else None]
                      for k, v in sorted(boxes.items())}, sort_keys=True)
    osm = None
    if cache and cache.exists():
        blob = json.loads(cache.read_text())
        if blob.get("key") == key:
            osm = {k: [[tuple(p) for p in w] for w in v] for k, v in blob["osm"].items()}
    if osm is None:
        osm = read_osm(a.pbf, boxes)
        if cache:
            cache.write_text(json.dumps({"key": key, "osm": osm}))

    thresholds = {
        "axis_coverage_min": AXIS_COVERAGE_MIN, "clip_exact_min": CLIP_EXACT_MIN,
        "clip_near": CLIP_NEAR, "grid_n": GRID_N, "margin_dist": MARGIN_DIST,
        "margin_match": MARGIN_MATCH, "max_rel_hi": MAX_REL_HI, "max_rel_lo": MAX_REL_LO,
        "min_clipped_links": MIN_CLIPPED_LINKS, "min_links": MIN_LINKS,
        "min_links_strict": MIN_LINKS_STRICT, "pool_n": POOL_N,
        "tol": tol, "tol_extent": "frame"}
    result = {
        "criteria_rules": thresholds,
        "rules": __doc__.split("Stated rules and thresholds (fixed before any run; none is tuned afterwards):")[1].strip(),
        "tolerance": {"rule": band["rule"], "value": tol,
                      "source": "parser/refdata/harness.json bands.name_record_distance_tolerance.tol"},
    }

    def variants(c, rng, frame):
        """(name -> (frame, range)) alternatives for a cell's class."""
        v = {"range_half": (frame, rng / 2.0), "range_double": (frame, rng * 2.0),
             "control_32768": (frame, CONTROL_RANGE_32768)}
        if c["ptype"] == 1:
            v["own_bounds"] = (c["bounds"], float(class_range(
                ranges, c["level"], c["class"], c["sub"])))
            v["quadrant_4096"] = (c["bounds"], 4096.0)
        if c["class"] == "L0_sparse":
            v["own_leaf_16384"] = (c["bounds"], 16384.0)
            v["own_leaf_4096"] = (c["bounds"], 4096.0)
            v["tile4x4_4096"] = (c["tile"], 4096.0)
        return v

    def evaluate(cells, osm_key):
        """Model + alternatives + y-down over `cells`; returns per-cell result
        lists keyed by variant, plus extents and baselines."""
        res = {}
        ext, base, leafb = [], [], []
        for i, c in enumerate(cells):
            b = model_cell(c)
            frame, rng = model_frame(c, ranges)
            fe = max(extent_m(frame))
            ways = [to_uv(p, b) for p in osm[osm_key(i)]]
            w, h = extent_m(b)
            m = np.array([w, h])
            idx = WayIndex([np.asarray(x, float) * m for x in ways],
                           spacing=max(tol * fe / 2.0, 1.0))
            def run(fr, rg, y_up=True):
                return analyze(c["links"], ways, b, tol, rg, frame=fr, y_up=y_up,
                               tol_extent=fe, _idx=idx)
            r = {"model": run(frame, rng), "model_y_down": run(frame, rng, False)}
            for name, (fr, rg) in variants(c, rng, frame).items():
                r[name] = run(fr, rg)
            for k, v in r.items():
                res.setdefault(k, []).append(v)
            mres = r["model"]
            base.append(source_disagreement(
                [np.asarray(x, float) * m for x in ways], mres["_r_m"],
                tol * fe, max(tol * fe / 2.0, 1.0)))
            ext.append(fe)
        return res, ext, base

    def summarise(res, ext, base):
        pools = {k: pool(v, tol, ext) for k, v in res.items()}
        model = pools["model"]
        alts = {k: v for k, v in pools.items() if k not in ("model", "model_y_down")}
        a = criterion_a(model, alts)
        b = criterion_b(res["model"])
        nway = sum(x["osm_ways"] for x in base)
        miss = sum(x["ways_without_r_link"] for x in base)
        leaf_basis = float(np.mean(np.concatenate([
            [r["matched_fraction_leaf_basis"]] * r["links"] for r in res["model"]]))) \
            if res["model"] else None
        return {
            "alternatives": {k: v for k, v in sorted(alts.items())},
            "criterion_a": a, "criterion_b": b,
            "diagnostics": {
                "matched_fraction": model["matched_fraction"],
                "distance_m_p50_matched": model["matched_distance_m_p50"],
                "distance_m_p90_matched": model["matched_distance_m_p90"],
                "matched_fraction_leaf_basis_link_weighted":
                    None if leaf_basis is None else round(leaf_basis, 4),
                "occupied_ratio_median": model["occupied_ratio_median"],
                "source_disagreement_baseline": round(miss / nway, 4) if nway else None,
                "source_disagreement_ways": nway,
                "source_disagreement_ways_without_r_link": miss,
                "y_down_matched_fraction": pools["model_y_down"]["matched_fraction"],
                "y_down_distance_m_p50_matched": pools["model_y_down"]["matched_distance_m_p50"]},
            "model": model, "model_y_down": pools["model_y_down"]}

    # ---- named cells
    named_out = []
    for spec in CELL_SPECS:
        c = named[spec["name"]]
        res, ext, base = evaluate([c], lambda i, n="named:" + spec["name"]: n)
        sm = summarise(res, ext, base)
        n_links = len(c["links"])
        b_, a_ = sm["criterion_b"], sm["criterion_a"]
        crit = {"a": "pass" if a_["pass"] else "fail",
                "b_coord_max": b_["coord_max_over_range"]["verdict"],
                "b_axis_coverage": b_["axis_coverage"]["verdict"],
                "b_clip_exact_share": b_["clip_exact_share"]["verdict"]}
        if n_links < MIN_LINKS_STRICT:
            verdict = "low_n"
        elif "fail" in crit.values():
            verdict = "fail"
        elif "insufficient_data" in crit.values():
            verdict = "insufficient_data"
        else:
            verdict = "pass"
        b = model_cell(c)
        w, h = extent_m(b)
        sm["baseline_single_cell"] = base[0]
        named_out.append({
            "bounds": {"lat_hi": b.lat_hi, "lat_lo": b.lat_lo,
                       "lon_hi": b.lon_hi, "lon_lo": b.lon_lo},
            "cell_extent_m": round(max(w, h), 1), "class": c["class"],
            "criteria": crit, "ids": c["ids"], "links": n_links,
            "locality": {"lat": spec["lat"], "lon": spec["lon"], "source": spec["source"]},
            "model_range": model_frame(c, ranges)[1], "name": spec["name"],
            "osm_ways": len(osm["named:" + spec["name"]]),
            "single_cell_analysis": strip(res["model"][0]),
            "summary": sm, "verdict": verdict})
    result["named_cells"] = named_out

    # ---- pooled per class
    pooled_out = {}
    for key, cells in pooled.items():
        if not cells:
            pooled_out[key] = {"cells": 0, "note": "no qualifying cell"}
            continue
        res, ext, base = evaluate(cells, lambda i, k=key: f"{k}:{i}")
        sm = summarise(res, ext, base)
        sm["cells"] = len(cells)
        sm["cell_details"] = [{
            "ids": c["ids"], "links": len(c["links"]), "range": model_frame(c, ranges)[1],
            "walk_frame_class": c.get("walk_frame_class"),
            "matched_fraction": r["matched_fraction"],
            "axis_coverage": r["axis_coverage"],
            "coord_max_over_range": r["coord_max_over_range"],
            "clip_exact_share": r["clip_exact_share"],
            "occupied_ratio": r["occupied_ratio"]}
            for c, r in zip(cells, res["model"])]
        pooled_out[key] = sm
    result["pooled_classes"] = pooled_out
    result["l0_sparse_frame_check"] = {
        "sparse_cells_where_walk_frame_class_is_tile": sum(
            c["walk_frame_class"] == "l0_sparse_tile" for c in pooled.get("L0_sparse", [])),
        "sparse_cells": len(pooled.get("L0_sparse", []))}

    # ---- gate, per criterion
    classes = {k: v for k, v in pooled_out.items() if v.get("cells", 1)}
    def crit_map(f):
        return {k: f(v) for k, v in sorted(classes.items())}
    def allof(m):
        vals = set(m.values())
        return "pass" if vals == {"pass"} else ("fail" if "fail" in vals else "insufficient_data")
    ga = crit_map(lambda v: "pass" if v["criterion_a"]["pass"] else "fail")
    gcm = crit_map(lambda v: v["criterion_b"]["coord_max_over_range"]["verdict"])
    gax = crit_map(lambda v: v["criterion_b"]["axis_coverage"]["verdict"])
    gcl = crit_map(lambda v: v["criterion_b"]["clip_exact_share"]["verdict"])
    result["gate"] = {
        "a_relative_discrimination": {"per_class": ga, "verdict": allof(ga)},
        "b_coord_max_over_range": {"per_class": gcm, "verdict": allof(gcm)},
        "b_axis_coverage": {"per_class": gax, "verdict": allof(gax)},
        "b_clip_exact_share": {"per_class": gcl, "verdict": allof(gcl)},
        "named_cells": {c["name"]: c["verdict"] for c in named_out},
        "named_cells_failing": [c["name"] for c in named_out if c["verdict"] == "fail"],
        "classes_total": len(classes)}
    g = result["gate"]
    result["all_pass"] = bool(
        all(g[k]["verdict"] == "pass" for k in (
            "a_relative_discrimination", "b_coord_max_over_range",
            "b_axis_coverage", "b_clip_exact_share"))
        and not g["named_cells_failing"])
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True, default=float) + "\n")
    print(json.dumps({"all_pass": result["all_pass"], "gate": g}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
