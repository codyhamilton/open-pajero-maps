"""Overlay test (Plan 03 unit 2-03): decode reference disc R road links at the
per-class coordinate range from `refdata/profile/coord_scale.json` and overlay
them on OSM; run the same overlay at the current decoder constant (32768) as
the negative control.

Reads R only through `harness.walk` helpers; imports no writer module.

Stated rules and thresholds (fixed before any run):

  * named cells: Brisbane CBD and Sydney from `spot_checks.json`; rural QLD
    (Longreach) and outback (Birdsville) as the nearest undivided leaf to the
    locality, searched from the finest listed level outwards, that has
    >= MIN_LINKS road links.  Ranked by (level order, distance from locality
    to leaf bbox, distance to bbox centre, ids).  Match quality is never an
    input to the choice.
  * pooled cells: for each coordinate class (L0 urban, L0 sparse, L2, L4, L6,
    L8, divided) take POOL_N blocks spread evenly through that level's
    on-disc list of non-empty blocks (index round(i*(N-1)/(POOL_N-1))), and in
    each chosen block the first leaf of that class, in leaf index order, with
    >= MIN_LINKS road links; if a block has none, advance to the next block in
    the list.  Deterministic and independent of match quality.
  * cell_extent_m = max(width_m, height_m) of the cell bbox.
  * OSM class set per level (like-for-like: R stores fewer roads at coarser
    levels) -- L0/L2 all roads, L4 motorway..tertiary, L6/L8 motorway/trunk/
    primary.  Non-road highway values are always excluded.
  * match: each R link -> the OSM way minimising the median point-to-polyline
    distance over the link's vertices.  Matched iff that median
    <= tol * cell_extent_m, tol = harness.json
    bands.name_record_distance_tolerance.tol.
  * a cell passes iff matched fraction >= MATCH_MIN; R's occupied fraction of a
    GRID_N x GRID_N grid over the cell >= OCC_RATIO_MIN * the occupied fraction
    of the like-for-like OSM roads; coordinate max / range in [MAX_REL_LO, 1.0];
    and clipped-link exact share >= CLIP_MIN (ends within CLIP_NEAR of the range
    from an edge; exact = that coordinate is 0 or the range).
  * orientation: y-up means raw y increases northward (lat = lat_lo + y/range *
    height); y-down is `coordconv.xy_to_latlon`'s current convention.  Decided
    by pooled matched fraction and median distance over all pooled cells, not
    by any single cell.
  * divided (pardiv1) frame hypotheses, tested against OSM over the pooled
    divided cells:
      own_bounds   - sub-parcel's own quadrant bbox, range = the per-sub max
                     from coord_scale.json (2048 for sub 0, else 4096);
      parent_4096  - the parent leaf's bbox, range 4096, coordinates absolute
                     in the parent frame (so sub 0, the y-up SW quadrant,
                     never exceeds 2048 -- which is what the census observed);
      quadrant_4096- sub-parcel's own quadrant bbox, range 4096 for every sub.
  * L0 sparse frame hypotheses, tested the same way: own_leaf_16384 (the leaf's
    own bbox at the census range), own_leaf_4096, tile4x4_16384 (the 4x4
    "integrated parcel" of leaves -- the tile the class rule keys urban/sparse
    on, and the size of one L2 leaf -- at 16384 = 4 x 4096) and tile4x4_4096.
    `inside_cell_fraction` is the OSM-free discriminator: under a wrong wider
    frame the leaf's links scatter outside the leaf.
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

DECODER_RANGE = 32768.0
GRID_N = 16
MIN_LINKS = 20
POOL_N = 12
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


def analyze(links, osm_ways_uv, cell, tol, scale, frame=None, y_up=True,
            tol_extent=None):
    """Overlay metrics for one cell decoded in `frame` (default: the cell) at
    `scale`.  `links`: dicts {"pts": [(x, y) raw], "ends": [(x, y) raw]}.
    `osm_ways_uv`: ways as (k,2) arrays in the cell's unit (u, v) coords."""
    frame = frame if frame is not None else cell
    w, h = extent_m(cell)
    extent = max(w, h)
    m = np.array([w, h])
    ways_m = [np.asarray(x, float) * m for x in osm_ways_uv]
    idx = WayIndex(ways_m, spacing=max(tol * extent / 2.0, 1.0))
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
    res = {
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
    return res


def pool(results: list[dict], tol: float, extents: list[float]) -> dict:
    """Pooled statistics over cells: every link counts once."""
    d = np.concatenate([r["_dists"] for r in results]) if results else np.zeros(0)
    lim = np.concatenate([np.full(len(r["_dists"]), tol * e)
                          for r, e in zip(results, extents)]) if results else np.zeros(0)
    fin = d[np.isfinite(d)]
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
        "matched_fraction": round(float((d <= lim).mean()), 4) if len(d) else 0.0,
        "occupied_ratio_median": round(float(np.median(occ)), 4) if occ else None,
    }


# --------------------------------------------------------------- R reading

def _raw(lat, lon, b):
    """Invert coordconv's decode to recover the raw (x, y) stored on disc."""
    return ((lon - b.lon_lo) / (b.lon_hi - b.lon_lo) * DECODER_RANGE,
            (b.lat_hi - lat) / (b.lat_hi - b.lat_lo) * DECODER_RANGE)


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
        for lpath, le, lb, ptype in self.walk._iter_tree_leaves(root, bb, lmr, ()):
            parent = self.walk._narrow_bounds(bb, gn_lat, gn_lng, lpath[0])
            out.append((lpath, le, lb, ptype, parent))
        return out

    def decode(self, lmr, blk, leaf):
        from kiwiw.model import MeshLocation
        from kiwiw.parcel import decode_parcel
        _, bs_index, ei, _, _ = blk
        lpath, le, lb, ptype, _ = leaf
        self.fh.seek(self.volume.getsector(le.dsa, self.ss, self.ls))
        buf = self.fh.read(le.size * self.ls)
        loc = MeshLocation(level=lmr.level, parcel_type=ptype, blockset_index=bs_index,
                           block_index=ei, parcel_index=lpath[-1], bounds=lb,
                           sector_addr=le.dsa, size_logical_sectors=le.size)
        try:
            p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
        except Exception:  # noqa: BLE001
            return None
        return _links(p, lb)


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
                lpath, _, lb, ptype, _ = leaf
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
                        "tile": tile_frame(blk[4], lpath[0], 1 + lmr.n_parcels_lat[0],
                                           1 + lmr.n_parcels_lng[0]),
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
                    lpath, _, _, lptype, _ = leaf
                    if lptype != ptype:
                        continue
                    if urban is not None and _urban(class_rule, blk[1], blk[2], lpath[0]) != urban:
                        continue
                    cand.append(leaf)
                took = 0
                for leaf in spread(cand, max(per_block * 8, 64)):
                    if took >= cap or len(out[key]) >= POOL_N:
                        break
                    lpath, _, lb, lptype, parent = leaf
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
                        "tile": tile_frame(blk[4], lpath[0], 1 + lmr.n_parcels_lat[0],
                                           1 + lmr.n_parcels_lng[0]),
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

    result = {
        "criteria_rules": {
            "clip_exact_share_min": CLIP_MIN, "clip_near_fraction_of_range": CLIP_NEAR,
            "clip_near_tight": CLIP_NEAR_TIGHT, "coord_max_rel_min": MAX_REL_LO,
            "grid": GRID_N, "match_fraction_min": MATCH_MIN, "min_links": MIN_LINKS,
            "occupied_ratio_min": OCC_RATIO_MIN, "pool_n": POOL_N},
        "rules": __doc__.split("Stated rules and thresholds (fixed before any run):")[1].strip(),
        "tolerance": {"rule": band["rule"], "value": tol,
                      "source": "parser/refdata/harness.json bands.name_record_distance_tolerance.tol"},
    }

    # ---- named cells (headline): model vs 32768 control, chosen orientation
    named_out = []
    for spec in CELL_SPECS:
        c = named[spec["name"]]
        b = model_cell(c)
        frame, rng = model_frame(c, ranges)
        fe = max(extent_m(frame))
        ways = [to_uv(p, b) for p in osm["named:" + spec["name"]]]
        model = analyze(c["links"], ways, b, tol, rng, frame=frame, y_up=True, tol_extent=fe)
        ctrl = analyze(c["links"], ways, b, tol, DECODER_RANGE, y_up=True, tol_extent=fe)
        ydown = analyze(c["links"], ways, b, tol, rng, frame=frame, y_up=False, tol_extent=fe)
        w, h = extent_m(b)
        named_out.append({
            "bounds": {"lat_hi": b.lat_hi, "lat_lo": b.lat_lo,
                       "lon_hi": b.lon_hi, "lon_lo": b.lon_lo},
            "cell_extent_m": round(max(w, h), 1), "class": c["class"],
            "control_32768": strip(ctrl), "ids": c["ids"],
            "locality": {"lat": spec["lat"], "lon": spec["lon"], "source": spec["source"]},
            "model": strip(model), "model_range": rng,
            "model_y_down": strip(ydown), "name": spec["name"],
            "osm_ways": len(ways),
            "verdict": "pass" if model["pass"] and not ctrl["pass"] else "fail"})
    result["named_cells"] = named_out

    # ---- pooled per class: model, control, and both orientations
    pooled_out = {}
    orient = {}
    for key, cells in pooled.items():
        if not cells:
            pooled_out[key] = {"cells": 0, "note": "no qualifying cell"}
            continue
        m, ctl, dn, ext, det = [], [], [], [], []
        for i, c in enumerate(cells):
            b = model_cell(c)
            frame, rng = model_frame(c, ranges)
            fe = max(extent_m(frame))
            ways = [to_uv(p, b) for p in osm[f"{key}:{i}"]]
            r_up = analyze(c["links"], ways, b, tol, rng, frame=frame, y_up=True, tol_extent=fe)
            r_dn = analyze(c["links"], ways, b, tol, rng, frame=frame, y_up=False, tol_extent=fe)
            r_ct = analyze(c["links"], ways, b, tol, DECODER_RANGE, y_up=True, tol_extent=fe)
            m.append(r_up)
            dn.append(r_dn)
            ctl.append(r_ct)
            ext.append(fe)
            det.append({"ids": c["ids"], "links": len(c["links"]), "range": rng,
                        "matched_fraction": r_up["matched_fraction"],
                        "distance_m_p50": r_up["distance_m_p50"],
                        "occupied_ratio": r_up["occupied_ratio"],
                        "clip_exact_share": r_up["clip_exact_share"],
                        "coord_max_over_range": r_up["coord_max_over_range"],
                        "pass": r_up["pass"]})
        pooled_out[key] = {
            "cell_details": det,
            "control_32768": pool(ctl, tol, ext),
            "model": pool(m, tol, ext),
            "model_y_down": pool(dn, tol, ext),
        }
        orient[key] = {"y_up_matched": pooled_out[key]["model"]["matched_fraction"],
                       "y_down_matched": pooled_out[key]["model_y_down"]["matched_fraction"],
                       "y_up_p50_m": pooled_out[key]["model"]["distance_m_p50"],
                       "y_down_p50_m": pooled_out[key]["model_y_down"]["distance_m_p50"]}
    result["pooled_classes"] = pooled_out

    wins = sum(1 for v in orient.values() if v["y_up_matched"] > v["y_down_matched"])
    result["orientation"] = {
        "classes": orient,
        "classes_favouring_y_up": wins,
        "classes_total": len(orient),
        "coordconv_current": "y_down (lat = lat_hi - y/range * height)",
        "finding": ("y_up" if wins * 2 > len(orient) else "y_down") +
                   " fits: pooled matched fraction and median distance per class",
        "note": "coordconv.py is NOT edited here; Phase 3 owns it.",
    }

    # ---- frame hypotheses: divided sub-parcels, and the L0 sparse class
    def test_frames(cells, prefix, variants):
        out = {}
        for name, fn in variants.items():
            res, ext = [], []
            for i, c in enumerate(cells):
                b = c["bounds"]
                frame, rng = fn(c)
                fe = max(extent_m(frame))
                ways = [to_uv(p, b) for p in osm[f"{prefix}:{i}"]]
                res.append(analyze(c["links"], ways, b, tol, rng, frame=frame,
                                   y_up=True, tol_extent=fe))
                ext.append(fe)
            out[name] = pool(res, tol, ext) if res else {"cells": 0}
            if res:
                out[name]["inside_cell_fraction_median"] = round(float(np.median(
                    [r["inside_cell_fraction"] for r in res])), 4)
        return out

    div = pooled.get("divided_pardiv1", [])
    hyp = test_frames(div, "divided_pardiv1", {
        "own_bounds": lambda c: (c["bounds"],
                                 float(class_range(ranges, c["level"], c["class"], c["sub"]))),
        "parent_4096": lambda c: (c["parent"], 4096.0),
        "quadrant_4096": lambda c: (c["bounds"], 4096.0)})
    best = max(hyp, key=lambda k: (hyp[k].get("matched_fraction", 0.0))) if hyp else None

    sparse = pooled.get("L0_sparse", [])
    shyp = test_frames(sparse, "L0_sparse", {
        "own_leaf_16384": lambda c: (c["bounds"], 16384.0),
        "own_leaf_4096": lambda c: (c["bounds"], 4096.0),
        "tile4x4_16384": lambda c: (c["tile"], 16384.0),
        "tile4x4_4096": lambda c: (c["tile"], 4096.0)})
    sbest = max(shyp, key=lambda k: (shyp[k].get("matched_fraction", 0.0))) if shyp else None
    result["l0_sparse_rule"] = {
        "hypotheses": shyp,
        "best_fit": sbest,
        "census_maximum": 16384,
        "canonical": (
            "L0 sparse coordinates are absolute in the 4x4 'integrated parcel' "
            "(the same 4x4 tile the coord_scale class rule keys urban/sparse on, "
            "and the size of one L2 leaf) at range 16384 = 4 x 4096 -- which is "
            "exactly the census maximum"
            if sbest == "tile4x4_16384" else
            "no hypothesis fits: see hypotheses for the numbers"),
    }
    result["divided_rule"] = {
        "hypotheses": hyp,
        "sub_index_layout": "idx = 2*row + col, row 0 = south (walk._narrow_bounds)",
        "best_fit": best,
        "census_maxima": {"pardiv1_sub0": 2048, "pardiv1_sub1..3": 4096},
        "canonical": (
            "sub-parcel coordinates are absolute in the PARENT leaf's frame at range "
            "4096; each sub covers a 2x2 quadrant, so sub 0 (SW under y-up) never "
            "exceeds 2048 -- which is exactly the census maximum"
            if best == "parent_4096" else
            "no hypothesis fits: see hypotheses for the numbers"),
    }

    # ---- verdicts
    model_classes = {k: v for k, v in pooled_out.items() if v.get("cells", 1)}
    result["gate"] = {
        "classes_model_matched_ok": sum(
            1 for v in model_classes.values()
            if v["model"]["matched_fraction"] >= MATCH_MIN),
        "classes_control_matched_ok": sum(
            1 for v in model_classes.values()
            if v["control_32768"]["matched_fraction"] >= MATCH_MIN),
        "classes_control_clustered": sum(
            1 for v in model_classes.values()
            if (v["control_32768"]["occupied_ratio_median"] or 0) < OCC_RATIO_MIN),
        "classes_total": len(model_classes),
        "named_cells_passing": sum(c["verdict"] == "pass" for c in named_out),
    }
    result["all_pass"] = bool(
        result["gate"]["named_cells_passing"] == len(named_out)
        and result["gate"]["classes_model_matched_ok"] == len(model_classes)
        and result["gate"]["classes_control_clustered"] == len(model_classes))
    Path(a.out).write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"all_pass": result["all_pass"],
                      "named": {c["name"]: c["verdict"] for c in named_out},
                      "orientation": result["orientation"]["finding"],
                      "divided_best": best, "l0_sparse_best": sbest,
                      "gate": result["gate"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
