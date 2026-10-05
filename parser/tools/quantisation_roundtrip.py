#!/usr/bin/env python3
"""Check a built `ALLDATA.KWI` against the spool it was built from
(Plan 03, 3-04 / 3-07 / 3C-04).

The tool decodes the disc with the Python decoder (`harness.walk` block and
leaf enumeration, `kiwiw.parcel.decode_parcel`) and reads the spool with
`kiwiw.spool.SpoolReader`. It imports no build module: nothing here clips,
overlaps, divides, synthesises or encodes. It asserts the invariants of
DESIGN.md "Verification-tool decisions":

- every decoded vertex lies in its frame's `[0, range]` (kind `range`);
- every step between consecutive background vertices is representable:
  a multiple of `mult_const`, at most `127 * mult_const` (kind `step`);
- road nodes, road points and name anchors each lie within half a raw unit
  per axis of a spool record of the same kind (`road_node`, `road_point`,
  `name_anchor`);
- a background vertex not on its leaf rectangle's boundary lies within half
  a raw unit per axis (Chebyshev) of the outline of a same-type spool shape
  (`background`);
- a background vertex on the boundary lies inside or on a same-type spool
  polygon, with the same half-unit tolerance (`background_boundary`);
- completeness per `(cell, type)`: a cell that a spool polygon's interior
  demonstrably meets holds at least one decoded piece of that type
  (`completeness`, see `_required_cells`), and the centre of every
  interior-cover piece lies inside a same-type spool polygon
  (`interior_cover`).

Coordinates. Everything is compared in one global raw lattice per level:
`X = (lon - disc_lon_lo) / cell_lon * 4096`, `Y = (lat - disc_lat_lo) /
cell_lat * 4096` (`kiwiw.mesh.CellGrid`). A frame's raw coordinate is an
integer offset into it whenever the frame is 4096 raw per cell (every
frame G writes; an L0 sparse tile is 16384 over 4 cells, the same unit).
Frame-raw coordinates (for the range and step checks) come from the leaf
frame `harness.walk` decodes against.

Spatial index. Spool shapes are spooled in the cell holding their
centroid. A block's check reads the spool cells of the block's cell
rectangle grown by one cell (the "local" shapes), plus every "tall" shape:
one whose bounding box leaves its home cell grown by one cell, found by a
first parallel pass over the whole spool and shared copy-on-write (numpy
arrays only) with the block workers. Within a block every lookup is a
sorted-key join (vertex buckets, segment buckets) or a scan-line crossing
table, all vectorised.

Usage:
    quantisation_roundtrip.py --disc ALLDATA.KWI --spool SPOOL [--out J] [--workers N]
                              [--engine c|python]
`--engine c` (default) is a thin driver over K1 (`kiwiw.cenc.k1_check_band`, one call per
planned range, see "K1 driver" below); `--engine python` is the checking path described
above, kept as the count oracle until Phase 5. The report records its `engine`; its
`timing` section and `wall_s` are the only non-deterministic bytes (`compare_excludes`).
Exit code 1 on any failing check; the report is written either way.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

_PARSER_DIR = Path(__file__).resolve().parent.parent
if str(_PARSER_DIR) not in sys.path:
    sys.path.insert(0, str(_PARSER_DIR))

from harness import walk  # noqa: E402
from harness.checks.coord_scale import _block_keys  # noqa: E402
from kiwiw import volume  # noqa: E402
from kiwiw.mesh import CellGrid  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402
from kiwiw.spool import SpoolReader, decode_columns  # noqa: E402

RAW = 4096          # raw units per cell side in the global lattice
TOL = 0.5           # half a raw unit, per axis
EPS = 1e-6          # float slack on TOL comparisons
INT_EPS = 1e-3      # a decoded coordinate must be this close to an integer raw
SEARCH = 2.0        # outline search radius (raw) -- errors up to this are reported
SEG_BUCKET = 64     # raw units per segment-index bucket
SAMPLE = 10         # failure sample size per (level, kind)
KINDS = ("range", "step", "road_node", "road_point", "name_anchor", "background",
         "background_boundary", "interior_cover", "completeness")
# the kinds `--dump-failures` can write (brief 3-02: the five that fail on the 3-11 disc)
DUMP_KINDS = ("name_anchor", "background", "background_boundary", "interior_cover",
              "completeness")
# the canonical file order of a dump: identity first, then the total sample order
DUMP_ORDER = ("level", "iy", "ix", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "depth",
              "vx", "vy", "reason", "code", "lat", "lon", "err", "shape", "vert")
# failures of a point kind that a documented build rule explains; counted
# (and reported per level) rather than failed
EXPLAINED = ("road_node_subcell_on_polyline", "road_node_on_leaf_edge",
             "road_point_subcell_on_polyline", "road_point_on_leaf_edge", "name_anchor_halo")
_OFF = 1 << 24
_MASK26 = (1 << 26) - 1
_SHIFT = float(1 << 25)   # makes every along-line coordinate positive
_BIG = float(1 << 27)     # group stride for the interval prefix-max


# ------------------------------------------------------------------ lattice

class Lattice:
    """One level's global raw lattice (`kiwiw.mesh.CellGrid`)."""

    def __init__(self, level: int):
        g = CellGrid.from_reference(level)
        self.level = level
        self.nx, self.ny = g.nx, g.ny
        self.lon0, self.lat0 = g.disc_lon_lo, g.disc_lat_lo
        self.cell_lon, self.cell_lat = g.cell_lon, g.cell_lat
        # longitude offsets are wrapped into the 360-degree window centred
        # on the disc's span, so a point far outside it stays far outside
        self._wlo = g.disc_lon_span / 2.0 - 180.0

    def dlon(self, lon):
        d = np.asarray(lon, np.float64) - self.lon0
        return np.mod(d - self._wlo, 360.0) + self._wlo

    def gx(self, lon):
        return self.dlon(lon) / self.cell_lon * RAW

    def gy(self, lat):
        return (np.asarray(lat, np.float64) - self.lat0) / self.cell_lat * RAW


def _pack(t, X, Y):
    """Sortable int64 key of (type, X, Y); X, Y integers in [-2^24, 2^25)."""
    return (np.asarray(t, np.int64) << 52) | ((np.asarray(X, np.int64) + _OFF) << 26) \
        | (np.asarray(Y, np.int64) + _OFF)


def _in_key_range(X, Y):
    return (X >= -_OFF) & (X < _MASK26 - _OFF) & (Y >= -_OFF) & (Y < _MASK26 - _OFF)


def _pairs(skeys, qkeys):
    """All `(query_index, sorted_index)` pairs with equal keys."""
    lo = np.searchsorted(skeys, qkeys, "left")
    hi = np.searchsorted(skeys, qkeys, "right")
    cnt = hi - lo
    tot = int(cnt.sum())
    if tot == 0:
        e = np.zeros(0, np.int64)
        return e, e
    qi = np.repeat(np.arange(len(qkeys), dtype=np.int64), cnt)
    base = np.repeat(lo - (np.cumsum(cnt) - cnt), cnt)
    return qi, base + np.arange(tot, dtype=np.int64)


class PointSet:
    """Spool points (optionally typed) bucketed by integer floor, for exact
    Chebyshev nearest-within-half-unit queries."""

    def __init__(self, x, y, t=None):
        x = np.asarray(x, np.float64)
        y = np.asarray(y, np.float64)
        t = np.zeros(len(x), np.int64) if t is None else np.asarray(t, np.int64)
        fx, fy = np.floor(x), np.floor(y)
        ok = _in_key_range(fx, fy)
        keys = _pack(t[ok], fx[ok], fy[ok])
        order = np.argsort(keys, kind="stable")
        self.keys = keys[order]
        self.x = x[ok][order]
        self.y = y[ok][order]

    def nearest(self, X, Y, t=None):
        """Chebyshev distance to the nearest point within one raw unit
        (`inf` if none) for integer query points."""
        X = np.asarray(X, np.int64)
        Y = np.asarray(Y, np.int64)
        t = np.zeros(len(X), np.int64) if t is None else np.asarray(t, np.int64)
        out = np.full(len(X), np.inf)
        if len(X) == 0 or len(self.keys) == 0:
            return out
        for dx in (-1, 0):
            for dy in (-1, 0):
                qx, qy = X + dx, Y + dy
                ok = _in_key_range(qx, qy)
                idx = np.nonzero(ok)[0]
                qi, ci = _pairs(self.keys, _pack(t[idx], qx[idx], qy[idx]))
                if len(qi):
                    qi = idx[qi]
                    d = np.maximum(np.abs(self.x[ci] - X[qi]), np.abs(self.y[ci] - Y[qi]))
                    np.minimum.at(out, qi, d)
        return out


def _cheb_seg(px, py, x1, y1, x2, y2):
    """Chebyshev distance from points to segments (element-wise)."""
    ax, ay = x1 - px, y1 - py
    bx, by = x2 - x1, y2 - y1
    best = np.maximum(np.abs(ax), np.abs(ay))
    best = np.minimum(best, np.maximum(np.abs(ax + bx), np.abs(ay + by)))
    with np.errstate(divide="ignore", invalid="ignore"):
        for num, den in ((-ax, bx), (-ay, by), (ay - ax, bx - by), (-(ax + ay), bx + by)):
            t = np.clip(np.nan_to_num(num / den, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
            best = np.minimum(best, np.maximum(np.abs(ax + bx * t), np.abs(ay + by * t)))
    return best


# ------------------------------------------------------------------ spool side

class Shapes:
    """A set of spool shapes in global raw coordinates (numpy only)."""

    __slots__ = ("x", "y", "off", "type", "cls")

    def __init__(self, x, y, off, typ, cls):
        self.x, self.y, self.off, self.type, self.cls = x, y, off, typ, cls

    @classmethod
    def empty(cls):
        z = np.zeros(0, np.float64)
        zi = np.zeros(0, np.int64)
        return cls(z, z, np.zeros(1, np.int64), zi, zi)

    @property
    def n(self):
        return len(self.type)

    def lengths(self):
        return np.diff(self.off)

    def bbox(self):
        n = self.lengths()
        nz = n > 0
        starts = self.off[:-1][nz]
        out = [np.full(self.n, np.nan) for _ in range(4)]
        if len(starts):
            for k, (arr, fn) in enumerate(((self.x, np.minimum), (self.x, np.maximum),
                                           (self.y, np.minimum), (self.y, np.maximum))):
                out[k][nz] = fn.reduceat(arr, starts)
        return out

    def take(self, sel):
        sel = np.asarray(sel, np.int64)
        n = self.lengths()[sel]
        off = np.zeros(len(sel) + 1, np.int64)
        np.cumsum(n, out=off[1:])
        src = np.repeat(self.off[:-1][sel] - off[:-1], n) + np.arange(off[-1], dtype=np.int64)
        return Shapes(self.x[src], self.y[src], off, self.type[sel], self.cls[sel])

    @staticmethod
    def concat(parts):
        parts = [p for p in parts if p.n]
        if not parts:
            return Shapes.empty()
        offs, base = [np.zeros(1, np.int64)], 0
        for p in parts:
            offs.append(p.off[1:] + base)
            base += p.off[-1]
        return Shapes(np.concatenate([p.x for p in parts]), np.concatenate([p.y for p in parts]),
                      np.concatenate(offs), np.concatenate([p.type for p in parts]),
                      np.concatenate([p.cls for p in parts]))

    def segments(self, closed_classes=(2,)):
        """(x1, y1, x2, y2, shape) of every edge; rings of the given classes
        get their closing edge."""
        n = self.lengths()
        vs = np.repeat(np.arange(self.n, dtype=np.int64), n)
        i = np.arange(len(self.x), dtype=np.int64)
        nxt = i + 1
        last = self.off[1:] - 1
        has = n > 0
        closing = np.isin(self.cls, closed_classes)
        nxt_last = np.where(closing, self.off[:-1], -1)
        nxt[last[has]] = nxt_last[has]
        keep = nxt >= 0
        a, b = i[keep], nxt[keep]
        keep2 = a != b
        a, b = a[keep2], b[keep2]
        return self.x[a], self.y[a], self.x[b], self.y[b], vs[a]


def _road_segments(cols, lat):
    """Segments of the spool road polylines (points, or nodes where a road
    stores no points) as global raw floats (x1, y1, x2, y2)."""
    xs, ys, lens = [], [], []
    for c in cols:
        npts = c["r_npts"].astype(np.int64)
        if len(npts) == 0:
            continue
        ns = c["r_nstored"].astype(np.int64)
        po = np.concatenate([[0], np.cumsum(npts)])
        no = np.concatenate([[0], np.cumsum(ns)])
        use_p = npts > 0
        # per road: its points, else its stored nodes
        n = np.where(use_p, npts, ns)
        src_start = np.where(use_p, po[:-1], no[:-1])
        j = np.repeat(src_start, n) + (np.arange(int(n.sum())) - np.repeat(np.cumsum(n) - n, n))
        fromp = np.repeat(use_p, n)

        def pick(pk, nk):
            v = np.zeros(len(j))
            if fromp.any():
                v[fromp] = c[pk][j[fromp]]
            if (~fromp).any():
                v[~fromp] = c[nk][j[~fromp]]
            return v
        lat_, lon_ = pick("p_lat", "n_lat"), pick("p_lon", "n_lon")
        xs.append(lat.gx(lon_))
        ys.append(lat.gy(lat_))
        lens.append(n)
    if not xs:
        z = np.zeros(0)
        return z, z, z, z
    x, y, n = np.concatenate(xs), np.concatenate(ys), np.concatenate(lens)
    end = np.cumsum(n)
    ok = np.ones(len(x), bool)
    ok[end[n > 0] - 1] = False       # last point of a road starts no segment
    a = np.nonzero(ok)[0]
    a = a[a + 1 < len(x)]
    return x[a], y[a], x[a + 1], y[a + 1]


def _cells_to_shapes(lat_parts, cols_list, lat):
    """Concatenate the background shapes of decoded spool cell columns."""
    xs, ys, lens, typ, cls = [], [], [], [], []
    for c in cols_list:
        if len(c["b_type"]) == 0:
            continue
        xs.append(lat.gx(c["c_lon"]))
        ys.append(lat.gy(c["c_lat"]))
        lens.append(c["b_nstored"].astype(np.int64))
        typ.append(c["b_type"].astype(np.int64))
        cls.append(c["b_class"].astype(np.int64))
    if not xs:
        return Shapes.empty()
    n = np.concatenate(lens)
    off = np.zeros(len(n) + 1, np.int64)
    np.cumsum(n, out=off[1:])
    return Shapes(np.concatenate(xs), np.concatenate(ys), off,
                  np.concatenate(typ), np.concatenate(cls))


def _tall_mask(sh: Shapes, hx, hy):
    """Shapes whose bbox leaves home cell (hx, hy) grown by one cell less a
    raw unit -- the ones a neighbour-ring read of the spool cannot find."""
    x0, x1, y0, y1 = sh.bbox()
    with np.errstate(invalid="ignore"):
        local = ((x0 >= (hx - 1) * RAW + 1) & (x1 <= (hx + 2) * RAW - 1)
                 & (y0 >= (hy - 1) * RAW + 1) & (y1 <= (hy + 2) * RAW - 1))
    return ~local & (sh.lengths() > 0)


def _read_cells(reader: SpoolReader, level: int, positions):
    idx = reader._load_idx(level)
    offs, lens = idx.offset, idx.length
    for i in positions:
        yield decode_columns(reader._read_cell(level, int(offs[i]), int(lens[i])))


# ------------------------------------------------------------------ pass 1

_G: dict = {}   # per-process state (fork-shared in the parent, lazily filled in workers)


def _pass1(task):
    """Tall shapes of one contiguous spool index range."""
    spool, level, a, b = task
    reader = _G.get(("reader", spool))
    if reader is None:
        reader = _G[("reader", spool)] = SpoolReader(spool)
    lat = Lattice(level)
    idx = reader._load_idx(level)
    parts = []
    CH = 2048
    for s in range(a, b, CH):
        e = min(b, s + CH)
        cols = list(_read_cells(reader, level, range(s, e)))
        sh = _cells_to_shapes(None, cols, lat)
        if not sh.n:
            continue
        per_cell = np.array([len(c["b_type"]) for c in cols], np.int64)
        hx = np.repeat(idx.ix[s:e].astype(np.int64), per_cell)
        hy = np.repeat(idx.iy[s:e].astype(np.int64), per_cell)
        m = _tall_mask(sh, hx, hy)
        if m.any():
            parts.append(sh.take(np.nonzero(m)[0]))
    t = Shapes.concat(parts)
    return level, a, (t.x, t.y, t.off, t.type, t.cls)


# ------------------------------------------------------------------ pass 2 helpers

def _seg_distance(mx, my, mt, x1, y1, x2, y2, st):
    """Chebyshev distance from points (mx, my) of type mt to the nearest
    segment of the same type, `inf` beyond SEARCH. Segments are bucketed at
    SEG_BUCKET pitch, grown by SEARCH, and joined to the query buckets."""
    out = np.full(len(mx), np.inf)
    if len(mx) == 0 or len(x1) == 0:
        return out
    want = np.isin(st, np.unique(mt))
    lo_x, hi_x = mx.min() - SEARCH, mx.max() + SEARCH
    lo_y, hi_y = my.min() - SEARCH, my.max() + SEARCH
    sx0, sx1 = np.minimum(x1, x2), np.maximum(x1, x2)
    sy0, sy1 = np.minimum(y1, y2), np.maximum(y1, y2)
    want &= (sx1 >= lo_x) & (sx0 <= hi_x) & (sy1 >= lo_y) & (sy0 <= hi_y)
    k = np.nonzero(want)[0]
    if len(k) == 0:
        return out
    P = SEG_BUCKET
    qbx = np.floor(mx / P).astype(np.int64)
    qby = np.floor(my / P).astype(np.int64)
    qkeys = _pack(mt, qbx, qby)
    occupied = np.unique(qkeys)
    bx0 = np.maximum(np.floor((sx0[k] - SEARCH) / P), qbx.min()).astype(np.int64)
    bx1 = np.minimum(np.floor((sx1[k] + SEARCH) / P), qbx.max()).astype(np.int64)
    by0 = np.maximum(np.floor((sy0[k] - SEARCH) / P), qby.min()).astype(np.int64)
    by1 = np.minimum(np.floor((sy1[k] + SEARCH) / P), qby.max()).astype(np.int64)
    nbx, nby = bx1 - bx0 + 1, by1 - by0 + 1
    nb = nbx * nby
    CH = 1 << 22   # bound the expanded (segment, bucket) list
    ends = np.searchsorted(np.cumsum(nb), np.arange(CH, int(nb.sum()) + CH, CH), "right")
    a = 0
    for e in ends:
        e = max(int(e), a + 1) if a < len(k) else a
        if a >= len(k):
            break
        sl = slice(a, min(e, len(k)))
        a = sl.stop
        kk, nn, nx_ = k[sl], nb[sl], nbx[sl]
        seg = np.repeat(kk, nn)
        j = np.arange(int(nn.sum()), dtype=np.int64) - np.repeat(np.cumsum(nn) - nn, nn)
        rn = np.repeat(nx_, nn)
        keys = _pack(st[seg], np.repeat(bx0[sl], nn) + j % rn, np.repeat(by0[sl], nn) + j // rn)
        hit = np.isin(keys, occupied, assume_unique=False)
        keys, seg = keys[hit], seg[hit]
        if len(keys) == 0:
            continue
        order = np.argsort(keys, kind="stable")
        qi, ci = _pairs(keys[order], qkeys)
        if len(qi):
            s = seg[order][ci]
            d = _cheb_seg(mx[qi], my[qi], x1[s], y1[s], x2[s], y2[s])
            np.minimum.at(out, qi, d)
    out[out > SEARCH] = np.inf
    return out


class Region:
    """The spool content a block's check sees."""

    def __init__(self, reader, level, lat, tall: Shapes, tall_bb, c0, c1, r0, r1):
        idx = reader._load_idx(level)
        a = int(np.searchsorted(idx.iy, r0 - 1, "left"))
        b = int(np.searchsorted(idx.iy, r1 + 2, "left"))
        ix = idx.ix[a:b]
        iy = idx.iy[a:b]
        pos = a + np.nonzero((ix >= c0 - 1) & (ix <= c1 + 1))[0]
        own = (idx.ix[pos] >= c0) & (idx.ix[pos] <= c1) & (idx.iy[pos] >= r0) & (idx.iy[pos] <= r1)
        self.spool_cells = set(zip(idx.ix[pos][own].tolist(), idx.iy[pos][own].tolist()))
        cols = list(_read_cells(reader, level, pos.tolist()))
        local = _cells_to_shapes(None, cols, lat)
        # tall shapes meeting the block rectangle (grown by the search radius)
        bx0, bx1 = c0 * RAW - SEARCH - 1, (c1 + 1) * RAW + SEARCH + 1
        by0, by1 = r0 * RAW - SEARCH - 1, (r1 + 1) * RAW + SEARCH + 1
        tx0, tx1, ty0, ty1 = tall_bb
        sel = np.nonzero((tx1 >= bx0) & (tx0 <= bx1) & (ty1 >= by0) & (ty0 <= by1))[0]
        if len(sel):
            local_hx, local_hy = None, None
            # a shape homed in the ring and also tall is in both; keep the tall copy only
            per_cell = np.array([len(c["b_type"]) for c in cols], np.int64)
            local_hx = np.repeat(idx.ix[pos].astype(np.int64), per_cell)
            local_hy = np.repeat(idx.iy[pos].astype(np.int64), per_cell)
            keep = ~_tall_mask(local, local_hx, local_hy)
            local = local.take(np.nonzero(keep)[0])
            self.shapes = Shapes.concat([local, tall.take(sel)])
        else:
            self.shapes = local

        def pts(kx, ky, extra=None):
            parts = [(c[kx], c[ky]) for c in cols if len(c[kx])]
            if not parts:
                return np.zeros(0), np.zeros(0)
            return (lat.gx(np.concatenate([p[1] for p in parts])),
                    lat.gy(np.concatenate([p[0] for p in parts])))
        nx, ny = pts("n_lat", "n_lon")
        px, py = pts("p_lat", "p_lon")
        self.nodes = PointSet(nx, ny)
        self.road_pts = PointSet(np.concatenate([px, nx]), np.concatenate([py, ny]))
        sl = [(c["s_lat"][(c["s_present"] & 3) == 3], c["s_lon"][(c["s_present"] & 3) == 3])
              for c in cols if len(c["s_lat"])]
        if sl:
            sx = lat.gx(np.concatenate([s[1] for s in sl]))
            sy = lat.gy(np.concatenate([s[0] for s in sl]))
        else:
            sx = sy = np.zeros(0)
        self.names = PointSet(sx, sy)
        o = np.argsort(sy, kind="stable")
        self.name_xy = (sx[o], sy[o])
        self.road_segs = _road_segments(cols, lat)
        sh = self.shapes
        vt = np.repeat(sh.type, sh.lengths())
        self.verts = PointSet(sh.x, sh.y, vt)
        self._segs = None
        self._polys = None

    def segs(self):
        if self._segs is None:
            sh = self.shapes
            x1, y1, x2, y2, s = sh.segments()
            self._segs = (x1, y1, x2, y2, sh.type[s])
        return self._segs

    def polys(self):
        """Edges of class-2 rings: (x1, y1, x2, y2, shape, type)."""
        if self._polys is None:
            sh = self.shapes
            x1, y1, x2, y2, s = sh.segments()
            m = sh.cls[s] == 2
            self._polys = (x1[m], y1[m], x2[m], y2[m], s[m], sh.type[s[m]])
        return self._polys

    def outline_distance(self, X, Y, t):
        """Chebyshev distance to the nearest same-type outline within
        SEARCH (`inf` beyond), for integer points."""
        out = self.verts.nearest(X, Y, t)
        miss = np.nonzero(out > TOL + EPS)[0]
        if len(miss):
            x1, y1, x2, y2, st = self.segs()
            out[miss] = np.minimum(out[miss], _seg_distance(
                X[miss].astype(np.float64), Y[miss].astype(np.float64), t[miss],
                x1, y1, x2, y2, st))
        return out

    def road_distance(self, X, Y):
        """Chebyshev distance to the nearest spool road polyline within
        SEARCH (`inf` beyond)."""
        x1, y1, x2, y2 = self.road_segs
        z = np.zeros(len(X), np.int64)
        return _seg_distance(X.astype(np.float64), Y.astype(np.float64), z,
                             x1, y1, x2, y2, np.zeros(len(x1), np.int64))

    def inside(self, orient, c, a, t):
        """Point-in-polygon along scan lines: `orient` 0 = horizontal line
        y=c with the point at x=a, 1 = vertical line x=c with y=a. True where
        some same-type spool polygon holds the point (even-odd per polygon,
        within TOL along the line)."""
        res = np.zeros(len(c), bool)
        if len(c) == 0:
            return res
        x1, y1, x2, y2, es, et = self.polys()
        types, tq = np.unique(t, return_inverse=True)
        NT = len(types)
        for o in (0, 1):
            q = np.nonzero(orient == o)[0]
            if len(q) == 0:
                continue
            if o == 0:
                u1, v1, u2, v2 = x1, y1, x2, y2     # along = x, across = y
            else:
                u1, v1, u2, v2 = y1, x1, y2, x2
            lines, qline = np.unique(c[q], return_inverse=True)
            tm = np.searchsorted(types, et)
            tm_ok = (tm < NT) & (types[np.minimum(tm, NT - 1)] == et)
            vlo, vhi = np.minimum(v1, v2), np.maximum(v1, v2)
            i0 = np.searchsorted(lines, vlo, "left")
            i1 = np.searchsorted(lines, vhi, "left")
            cnt = np.where(tm_ok, i1 - i0, 0)
            tot = int(cnt.sum())
            if tot == 0:
                continue
            e = np.repeat(np.arange(len(cnt), dtype=np.int64), cnt)
            li = np.repeat(i0, cnt) + (np.arange(tot, dtype=np.int64)
                                       - np.repeat(np.cumsum(cnt) - cnt, cnt))
            cv = lines[li]
            au = u1[e] + (cv - v1[e]) * (u2[e] - u1[e]) / (v2[e] - v1[e])
            g = li * NT + tm[e]
            order = np.lexsort((au, es[e], g))
            g, sh, au = g[order], es[e][order], au[order]
            newgrp = np.ones(tot, bool)
            newgrp[1:] = (g[1:] != g[:-1]) | (sh[1:] != sh[:-1])
            gstart = np.maximum.accumulate(np.where(newgrp, np.arange(tot), 0))
            rank = np.arange(tot) - gstart
            st = np.nonzero((rank % 2) == 0)[0]
            st = st[(st + 1 < tot)]
            st = st[(g[st + 1] == g[st]) & (sh[st + 1] == sh[st])]
            ig, ia, ib = g[st], au[st], au[st + 1]
            o2 = np.lexsort((ia, ig))
            ig, ia, ib = ig[o2], ia[o2], ib[o2]
            gf = ig.astype(np.float64) * _BIG
            skey = gf + ia + _SHIFT
            pmax = np.maximum.accumulate(gf + ib + _SHIFT) - gf - _SHIFT
            qg = qline * NT + tq[q]
            qa = a[q]
            j = np.searchsorted(skey, qg.astype(np.float64) * _BIG + qa + _SHIFT + TOL, "right") - 1
            ok = j >= 0
            jj = np.maximum(j, 0)
            ok &= (ig[jj] == qg) & (pmax[jj] >= qa - TOL)
            res[q] = ok if len(ig) else False
        return res


# ------------------------------------------------------------------ decoded side

class Decoded:
    """A block's decoded leaves flattened into arrays."""

    def __init__(self, parcels, lat: Lattice):
        self.errors = []
        L = {k: [] for k in ("x0", "x1", "y0", "y1", "ix", "iy", "flo", "fla", "fwo",
                             "fwa", "rng")}
        self.paths = []
        bg_ll, bg_len, bg_t, bg_c, bg_m, bg_l = [], [], [], [], [], []
        nd_ll, nd_l, pt_ll, pt_l, nm_ll, nm_l = [], [], [], [], [], []
        for wp in parcels:
            li = len(self.paths)
            b, f = wp.bounds, wp.frame_bounds
            bx0 = float(lat.gx(b.lon_lo))
            by0 = float(lat.gy(b.lat_lo))
            bw = walk._lon_span(b.lon_lo, b.lon_hi) / lat.cell_lon * RAW
            bh = (b.lat_hi - b.lat_lo) / lat.cell_lat * RAW
            x0, y0 = round(bx0), round(by0)
            x1, y1 = round(bx0 + bw), round(by0 + bh)
            L["x0"].append(x0)
            L["x1"].append(x1)
            L["y0"].append(y0)
            L["y1"].append(y1)
            L["ix"].append((x0 + x1) // 2 // RAW)
            L["iy"].append((y0 + y1) // 2 // RAW)
            L["flo"].append(f.lon_lo)
            L["fla"].append(f.lat_lo)
            L["fwo"].append(walk._lon_span(f.lon_lo, f.lon_hi))
            L["fwa"].append(f.lat_hi - f.lat_lo)
            L["rng"].append(wp.frame_range or 0)
            self.paths.append(wp.leaf_path)
            if wp.error or wp.parcel is None:
                self.errors.append((li, wp.error or "no parcel"))
                continue
            p = wp.parcel
            if p.background is not None:
                for s in p.background.shapes:
                    if s.coords:
                        bg_ll.extend(s.coords)
                        bg_len.append(len(s.coords))
                        bg_t.append(s.type_code)
                        bg_c.append(s.shape_class)
                        bg_m.append(s.mult_const or 1)
                        bg_l.append(li)
            if p.road is not None:
                for lk in p.road.links:
                    nodes = lk.nodes
                    j, nn = 0, len(nodes)
                    for q in lk.points:
                        if j < nn and q[0] == nodes[j].lat and q[1] == nodes[j].lon:
                            j += 1
                        else:
                            pt_ll.append(q)
                            pt_l.append(li)
                    for nd in nodes:
                        nd_ll.append((nd.lat, nd.lon))
                        nd_l.append(li)
            if p.name is not None:
                for r in p.name.records:
                    if r.lat is not None and r.lon is not None:
                        nm_ll.append((r.lat, r.lon))
                        nm_l.append(li)
        self.leaf = {k: np.asarray(v) for k, v in L.items()}
        self.n_leaves = len(self.paths)

        def arr(ll, li):
            a = np.asarray(ll, np.float64).reshape(-1, 2)
            return a[:, 0], a[:, 1], np.asarray(li, np.int64)
        self.bg_lat, self.bg_lon, _ = arr(bg_ll, [])
        n = np.asarray(bg_len, np.int64)
        self.bg_off = np.zeros(len(n) + 1, np.int64)
        np.cumsum(n, out=self.bg_off[1:])
        self.bg_type = np.asarray(bg_t, np.int64)
        self.bg_cls = np.asarray(bg_c, np.int64)
        self.bg_mult = np.asarray(bg_m, np.int64)
        self.bg_leaf = np.asarray(bg_l, np.int64)
        self.nd = arr(nd_ll, nd_l)
        self.pt = arr(pt_ll, pt_l)
        self.nm = arr(nm_ll, nm_l)


# ------------------------------------------------------------------ per-block check

class Acc:
    """Per-level counters and bounded failure samples."""

    def __init__(self):
        self.k = {k: [0, 0, 0.0] for k in KINDS}   # checked, failing, worst passing error
        self.samples = {k: [] for k in KINDS}
        self.explained = {k: 0 for k in EXPLAINED}

    def add(self, kind, checked, failing, worst=0.0):
        e = self.k[kind]
        e[0] += int(checked)
        e[1] += int(failing)
        if worst is not None and np.isfinite(worst):
            e[2] = max(e[2], float(worst))

    def sample(self, kind, rows):
        s = self.samples[kind]
        s.extend(rows)
        s.sort(key=_sample_key)
        del s[SAMPLE:]

    def merge(self, other):
        for k in KINDS:
            a, b = self.k[k], other.k[k]
            a[0] += b[0]
            a[1] += b[1]
            a[2] = max(a[2], b[2])
            self.sample(k, other.samples[k])
        for k in EXPLAINED:
            self.explained[k] += other.explained[k]


def _sample_key(r):
    return (r["cell"][1], r["cell"][0], r.get("leaf_path", []), r.get("vertex", {}).get("raw", []),
            r["reason"])


def _fmt(v):
    return None if v is None or not np.isfinite(v) else round(float(v), 6)


def _fail_rows(kind, dec: Decoded, lat: Lattice, leaf, lat_a, lon_a, fx, fy, reason, err, limit=SAMPLE):
    rows = []
    for i in range(min(limit, len(leaf))):
        li = int(leaf[i])
        rows.append({"cell": [int(dec.leaf["ix"][li]), int(dec.leaf["iy"][li])],
                     "leaf_path": list(dec.paths[li]), "kind": kind,
                     "vertex": {"lat": round(float(lat_a[i]), 9), "lon": round(float(lon_a[i]), 9),
                                "raw": [int(fx[i]), int(fy[i])]},
                     "reason": reason, "error_raw": _fmt(err[i]) if err is not None else None})
    return rows


def _frame_raw(dec: Decoded, leaf, lat_a, lon_a, lat: Lattice):
    """Frame-raw coordinates of decoded points (floats) and their range."""
    L = dec.leaf
    dlon = np.mod(lon_a - L["flo"][leaf] + 180.0, 360.0) - 180.0
    rng = L["rng"][leaf].astype(np.float64)
    fx = dlon / L["fwo"][leaf] * rng
    fy = (lat_a - L["fla"][leaf]) / L["fwa"][leaf] * rng
    return fx, fy, rng


def _check_points(acc, kind, dec, lat, region_set, pts, rescue=None):
    la, lo, leaf = pts
    if len(la) == 0:
        return
    gx, gy = lat.gx(lo), lat.gy(la)
    X, Y = np.rint(gx).astype(np.int64), np.rint(gy).astype(np.int64)
    d = region_set.nearest(X, Y)
    # the spool value S rounds to the decoded D: |S - D| <= 0.5
    bad = ~(d <= TOL + EPS)
    if rescue is not None and bad.any():
        b = np.nonzero(bad)[0]
        for name, ok in rescue(b, X[b], Y[b], leaf[b]):
            bad[b[ok]] = False
            acc.explained[name] += int(ok.sum())
    fx, fy, _ = _frame_raw(dec, leaf, la, lo, lat)
    acc.add(kind, len(la), int(bad.sum()), float(d[~bad].max()) if (~bad).any() else 0.0)
    if bad.any():
        b = np.nonzero(bad)[0]
        order = np.lexsort((X[b], Y[b], dec.leaf["ix"][leaf[b]], dec.leaf["iy"][leaf[b]]))[:SAMPLE]
        b = b[order]
        acc.sample(kind, _fail_rows(kind, dec, lat, leaf[b], la[b], lo[b], np.rint(fx[b]),
                                    np.rint(fy[b]), "no spool record within half a raw unit",
                                    d[b]))


def _road_rescue(dec, region, kind):
    """Road vertices with no spool vertex within half a raw unit that a
    documented build rule explains, provided they lie within half a raw unit
    of a spool road polyline:
    - `<kind>_subcell_on_polyline`: in a divided sub-cell leaf, where a road
      is re-tiled into chains whose every point is a node, cut where it
      crosses a sub-cell edge (E2's retile, `_e2.c`);
    - `<kind>_on_leaf_edge`: elsewhere, a vertex on its leaf rectangle's
      edge -- the vertex the clip makes where a road leaves the leaf."""
    L = dec.leaf

    def f(b, X, Y, leaf):
        sub = ((L["x1"] - L["x0"])[leaf] < RAW) | ((L["y1"] - L["y0"])[leaf] < RAW)
        edge = ((np.abs(X - L["x0"][leaf]) <= TOL) | (np.abs(X - L["x1"][leaf]) <= TOL)
                | (np.abs(Y - L["y0"][leaf]) <= TOL) | (np.abs(Y - L["y1"][leaf]) <= TOL))
        on = np.zeros(len(b), bool)
        e = np.nonzero(sub | edge)[0]
        if len(e):
            on[e] = region.road_distance(X[e], Y[e]) <= TOL + EPS
        return [(f"{kind}_subcell_on_polyline", on & sub), (f"{kind}_on_leaf_edge", on & ~sub)]
    return f


def _halo_name_rescue(dec, region):
    """A name anchor in a sub-cell leaf that equals, within half a raw unit,
    a spool name lying outside the leaf (within one leaf extent) clamped to
    the leaf rectangle inset by 1% per side -- a halo name (DESIGN / brief 32)."""
    L = dec.leaf
    nx, ny = region.name_xy

    def f(b, X, Y, leaf):
        ok = np.zeros(len(b), bool)
        x0, x1, y0, y1 = L["x0"][leaf], L["x1"][leaf], L["y0"][leaf], L["y1"][leaf]
        sub = ((x1 - x0) < RAW) | ((y1 - y0) < RAW)
        for li in np.unique(leaf[sub]):
            q = np.nonzero(leaf == li)[0]
            ax0, ax1, ay0, ay1 = (float(L[k][li]) for k in ("x0", "x1", "y0", "y1"))
            w, h = ax1 - ax0, ay1 - ay0
            i0 = np.searchsorted(ny, ay0 - h, "left")
            i1 = np.searchsorted(ny, ay1 + h, "right")
            cx, cy = nx[i0:i1], ny[i0:i1]
            m = (cx >= ax0 - w) & (cx <= ax1 + w)
            m &= ~((cx >= ax0) & (cx <= ax1) & (cy >= ay0) & (cy <= ay1))
            cx, cy = cx[m], cy[m]
            if len(cx) == 0:
                continue
            px = np.clip(cx, ax0 + 0.01 * w, ax1 - 0.01 * w)
            py = np.clip(cy, ay0 + 0.01 * h, ay1 - 0.01 * h)
            hit = ((np.abs(px[None, :] - X[q][:, None]) <= TOL + EPS)
                   & (np.abs(py[None, :] - Y[q][:, None]) <= TOL + EPS)).any(axis=1)
            ok[q] = hit
        return [("name_anchor_halo", ok)]
    return f


def _range_check(acc, dec, lat, leaf, la, lo):
    if len(la) == 0:
        return
    fx, fy, rng = _frame_raw(dec, leaf, la, lo, lat)
    rx, ry = np.rint(fx), np.rint(fy)
    nonint = (np.abs(fx - rx) > INT_EPS) | (np.abs(fy - ry) > INT_EPS)
    out = (rx < 0) | (ry < 0) | (rx > rng) | (ry > rng) | (rng <= 0)
    bad = nonint | out
    acc.add("range", len(la), int(bad.sum()))
    if bad.any():
        b = np.nonzero(bad)[0][:SAMPLE]
        acc.sample("range", _fail_rows("range", dec, lat, leaf[b], la[b], lo[b], rx[b], ry[b],
                                       "outside [0, range] or non-integral", None))


def _iter_leaves(disc, container, key, lat: Lattice, rlo, rhi):
    """Decoded leaf `WalkedParcel`s of one block whose cell row lies in
    `[rlo, rhi]` -- `coord_scale._decode_block_parcels`' loop (the
    `harness.walk` block/leaf pieces), with the row filter applied before a
    leaf is decoded so a heavy block can be split across workers. A block
    that does not parse yields one error marker (`leaf_path == ()`)."""
    level, bsi, bidx, bsx, bsy, blx, bly, boff, blen = key
    pdmdh, hdr = container.pdmdh, container.hdr
    sector_sz, logical_sz = hdr.sector_size, hdr.logical_sector_size
    lmr = next(m for m in pdmdh.levels if m.level == level)
    block_bounds = walk._block_base_bounds(pdmdh, lmr, bsx, bsy, blx, bly)
    with open(disc, "rb") as fh:
        fh.seek(boff)
        try:
            root = parse_parcel_mgmt_record(fh.read(blen), lmr)
        except Exception as exc:  # noqa: BLE001 -- reported as a failure
            yield walk.WalkedParcel(level=level, blockset_index=bsi, block_index=bidx,
                                    parcel_type=0, leaf_path=(), bounds=block_bounds,
                                    file_offset=boff, length=blen, parcel=None,
                                    error=f"parse_parcel_mgmt_record: {exc}")
            return
        sparse_cache: dict = {}
        for leaf_path, entry, leaf_bounds, ptype in walk._iter_tree_leaves(
                root, block_bounds, lmr, ()):
            iy = math.floor(float(lat.gy((leaf_bounds.lat_lo + leaf_bounds.lat_hi) / 2)) / RAW)
            if not rlo <= iy <= rhi:
                continue
            frame_bounds, frame_class = walk._leaf_frame(
                root, level, ptype, leaf_path, leaf_bounds, block_bounds, lmr, sparse_cache)
            frame_range = walk.leaf_frame_range(level, ptype, leaf_path, frame_class)
            moff = volume.getsector(entry.dsa, sector_sz, logical_sz)
            mlen = entry.size * logical_sz
            try:
                fh.seek(moff)
                mapdata = fh.read(mlen)
                loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=bsi,
                                   block_index=bidx, parcel_index=leaf_path[-1],
                                   bounds=walk.with_range(frame_bounds, frame_range),
                                   sector_addr=entry.dsa, size_logical_sectors=entry.size)
                parcel = decode_parcel(loc, mapdata, n_basic_map=lmr.n_basic_map,
                                       n_ext_map=lmr.n_ext_map)
                err = None
            except Exception as exc:  # noqa: BLE001
                parcel, err = None, f"decode_parcel: {exc}"
            yield walk.WalkedParcel(level=level, blockset_index=bsi, block_index=bidx,
                                    parcel_type=ptype, leaf_path=leaf_path, bounds=leaf_bounds,
                                    file_offset=moff, length=mlen, parcel=parcel, error=err,
                                    frame_bounds=frame_bounds, frame_range=frame_range,
                                    frame_class=frame_class)


def _state(level):
    spool, disc = _G["spool"], _G["disc"]
    lat = _G.get(("lat", level))
    if lat is None:
        lat = _G[("lat", level)] = Lattice(level)
    reader = _G.get("reader")
    if reader is None:
        reader = _G["reader"] = SpoolReader(spool)
    container = _G.get("container")
    if container is None:
        container = _G["container"] = walk.read_container(disc)
    return disc, lat, reader, container


def _check_block(task):
    """Check the leaves of one block whose cell row is in `[rlo, rhi]`."""
    key, rlo, rhi = task
    level = key[0]
    disc, lat, reader, container = _state(level)
    acc = Acc()
    dec = Decoded(_iter_leaves(disc, container, key, lat, rlo, rhi), lat)
    for li, err in dec.errors:
        acc.add("range", 0, 1)
        acc.sample("range", [{"cell": [int(dec.leaf["ix"][li]), int(dec.leaf["iy"][li])],
                              "leaf_path": list(dec.paths[li]), "kind": "range",
                              "reason": f"leaf did not decode: {err}"}])
    c0, c1, r0, r1 = key_cells(container, key, lat)
    r0, r1 = max(r0, rlo), min(r1, rhi)
    tall = _G["tall"].get(level)
    region = Region(reader, level, lat, tall[0], tall[1], c0, c1, r0, r1)

    # --- roads and names
    for kind, pts in (("road_node", dec.nd), ("road_point", dec.pt), ("name_anchor", dec.nm)):
        _range_check(acc, dec, lat, pts[2], pts[0], pts[1])
    _check_points(acc, "road_node", dec, lat, region.nodes, dec.nd,
                  _road_rescue(dec, region, "road_node"))
    _check_points(acc, "road_point", dec, lat, region.road_pts, dec.pt,
                  _road_rescue(dec, region, "road_point"))
    _check_points(acc, "name_anchor", dec, lat, region.names, dec.nm,
                  _halo_name_rescue(dec, region))

    # --- background
    nv = len(dec.bg_lat)
    nsh = len(dec.bg_type)
    present = set()
    if nv:
        lens = np.diff(dec.bg_off)
        vshape = np.repeat(np.arange(nsh, dtype=np.int64), lens)
        vleaf = dec.bg_leaf[vshape]
        vtype = dec.bg_type[vshape]
        la, lo = dec.bg_lat, dec.bg_lon
        _range_check(acc, dec, lat, vleaf, la, lo)
        fx, fy, _ = _frame_raw(dec, vleaf, la, lo, lat)
        rfx, rfy = np.rint(fx).astype(np.int64), np.rint(fy).astype(np.int64)
        # steps
        same = vshape[1:] == vshape[:-1]
        m = dec.bg_mult[vshape[1:]]
        dx, dy = np.diff(rfx), np.diff(rfy)
        stepbad = same & ((dx % m != 0) | (dy % m != 0) | (np.abs(dx) > 127 * m)
                          | (np.abs(dy) > 127 * m))
        acc.add("step", int(same.sum()), int(stepbad.sum()))
        if stepbad.any():
            b = np.nonzero(stepbad)[0][:SAMPLE] + 1
            acc.sample("step", _fail_rows("step", dec, lat, vleaf[b], la[b], lo[b], rfx[b], rfy[b],
                                          "step not representable", None))
        X = np.rint(lat.gx(lo)).astype(np.int64)
        Y = np.rint(lat.gy(la)).astype(np.int64)
        Lf = dec.leaf
        lx0, lx1, ly0, ly1 = Lf["x0"][vleaf], Lf["x1"][vleaf], Lf["y0"][vleaf], Lf["y1"][vleaf]
        onh = (Y == ly0) | (Y == ly1)
        onv = (X == lx0) | (X == lx1)
        onb = onh | onv
        d = region.outline_distance(X, Y, vtype)
        near = d <= TOL + EPS
        # non-boundary
        nb = ~onb
        bad = nb & ~near
        acc.add("background", int(nb.sum()), int(bad.sum()),
                float(d[nb & near].max()) if (nb & near).any() else 0.0)
        if bad.any():
            b = np.nonzero(bad)[0]
            b = b[np.lexsort((X[b], Y[b]))][:SAMPLE]
            acc.sample("background", _fail_rows(
                "background", dec, lat, vleaf[b], la[b], lo[b], rfx[b], rfy[b],
                "not within half a raw unit of a same-type spool outline", d[b]))
        # boundary: on the outline, or inside a same-type polygon
        q = np.nonzero(onb & ~near)[0]
        ok_b = near.copy()
        if len(q):
            orient = np.where(onh[q], 0, 1)
            c = np.where(onh[q], Y[q], X[q]).astype(np.float64)
            a = np.where(onh[q], X[q], Y[q]).astype(np.float64)
            ok_b[q] = region.inside(orient, c, a, vtype[q])
        bad = onb & ~ok_b
        acc.add("background_boundary", int(onb.sum()), int(bad.sum()),
                float(d[onb & near].max()) if (onb & near).any() else 0.0)
        if bad.any():
            b = np.nonzero(bad)[0]
            b = b[np.lexsort((X[b], Y[b]))][:SAMPLE]
            acc.sample("background_boundary", _fail_rows(
                "background_boundary", dec, lat, vleaf[b], la[b], lo[b], rfx[b], rfy[b],
                "boundary vertex outside every same-type spool polygon", d[b]))

        # interior covers: a ring whose every vertex is on its leaf boundary
        # and whose area is the leaf rectangle's
        poly = dec.bg_cls == 2
        allb = np.logical_and.reduceat(onb, dec.bg_off[:-1]) if nsh else np.zeros(0, bool)
        xs, ys = X.astype(np.float64), Y.astype(np.float64)
        nxt = np.arange(nv) + 1
        nxt[dec.bg_off[1:] - 1] = dec.bg_off[:-1]
        cross = xs * ys[nxt] - xs[nxt] * ys
        area = np.abs(np.add.reduceat(cross, dec.bg_off[:-1])) / 2.0
        sl = dec.bg_leaf
        rect = ((Lf["x1"] - Lf["x0"]) * (Lf["y1"] - Lf["y0"]))[sl].astype(np.float64)
        cover = np.nonzero(poly & allb & (np.abs(area - rect) < 0.5))[0]
        if len(cover):
            cx = ((Lf["x0"] + Lf["x1"]) / 2.0)[sl[cover]]
            cy = ((Lf["y0"] + Lf["y1"]) / 2.0)[sl[cover]]
            ok = region.inside(np.zeros(len(cover), np.int64), cy, cx, dec.bg_type[cover])
            nf = int((~ok).sum())
            acc.add("interior_cover", len(cover), nf)
            if nf:
                b = cover[~ok][:SAMPLE]
                acc.sample("interior_cover", [{
                    "cell": [int(Lf["ix"][sl[i]]), int(Lf["iy"][sl[i]])],
                    "leaf_path": list(dec.paths[sl[i]]), "kind": "interior_cover",
                    "type": int(dec.bg_type[i]),
                    "reason": "interior-cover centre outside every same-type spool polygon"}
                    for i in b])
        pc = np.nonzero(poly & (lens >= 3))[0]
        present = set(zip(Lf["ix"][sl[pc]].tolist(), Lf["iy"][sl[pc]].tolist(),
                          dec.bg_type[pc].tolist()))

    # --- completeness per (cell, type)
    cells = set(zip(dec.leaf["ix"].tolist(), dec.leaf["iy"].tolist())) | region.spool_cells
    cells = {cr for cr in cells if c0 <= cr[0] <= c1 and r0 <= cr[1] <= r1}
    req = _required_cells(region, cells, c0, c1, r0, r1)
    missing = sorted((k for k in req if k not in present), key=lambda k: (k[1], k[0], k[2]))
    acc.add("completeness", len(req), len(missing))
    if missing:
        acc.sample("completeness", [{"cell": [ix, iy], "kind": "completeness", "type": t,
                                     "reason": "a spool polygon of this type meets the cell "
                                               "but no decoded piece of it does"}
                                    for ix, iy, t in missing[:SAMPLE]])
    return level, acc, dec.n_leaves


def _required_cells(region: Region, cells, c0, c1, r0, r1):
    """`(ix, iy, type)` of emitted block cells that a spool polygon's
    interior demonstrably meets:

    - a polygon inside one cell rectangle whose ring, rounded to the raw
      lattice, has non-zero area (it cannot clip or round away);
    - a polygon with a vertex at least one raw unit inside the cell;
    - a polygon holding the cell centre (the cell is wholly or largely
      covered).
    Cells the polygon only grazes along an edge are not required: whether
    such a sliver survives rounding is the clip's business, not a check."""
    sh = region.shapes
    req = set()
    if not cells or sh.n == 0:
        return req
    poly = np.nonzero((sh.cls == 2) & (sh.lengths() >= 3))[0]
    if len(poly) == 0:
        return req
    ps = sh.take(poly)
    cellkey = {(ix, iy) for ix, iy in cells}
    x0, x1, y0, y1 = ps.bbox()
    cx = np.floor((x0 + x1) / 2.0 / RAW)
    cy = np.floor((y0 + y1) / 2.0 / RAW)
    inside1 = (x0 >= cx * RAW) & (x1 <= (cx + 1) * RAW) & (y0 >= cy * RAW) & (y1 <= (cy + 1) * RAW)
    # (a) polygons inside one cell: rounded area
    rx, ry = np.rint(ps.x), np.rint(ps.y)
    n = ps.lengths()
    nxt = np.arange(len(rx)) + 1
    nxt[ps.off[1:] - 1] = ps.off[:-1]
    cr = rx * ry[nxt] - rx[nxt] * ry
    area = np.add.reduceat(cr, ps.off[:-1])
    a_ok = inside1 & (area != 0)
    for ix, iy, t in zip(cx[a_ok].astype(np.int64).tolist(), cy[a_ok].astype(np.int64).tolist(),
                         ps.type[a_ok].tolist()):
        if (ix, iy) in cellkey:
            req.add((ix, iy, t))
    # (b) polygons crossing cells: vertices at least one raw unit inside a cell
    vs = np.repeat(np.arange(ps.n), n)
    multi = ~inside1[vs]
    vx, vy = ps.x[multi], ps.y[multi]
    vt = ps.type[vs[multi]]
    kx, ky = np.floor(vx / RAW), np.floor(vy / RAW)
    fxr, fyr = vx - kx * RAW, vy - ky * RAW
    deep = (fxr >= 1) & (fxr <= RAW - 1) & (fyr >= 1) & (fyr <= RAW - 1) \
        & (kx >= c0) & (kx <= c1) & (ky >= r0) & (ky <= r1)
    if deep.any():
        k = np.unique(_pack(vt[deep], kx[deep].astype(np.int64), ky[deep].astype(np.int64)))
        for key in k.tolist():
            t = key >> 52
            ix = ((key >> 26) & _MASK26) - _OFF
            iy = (key & _MASK26) - _OFF
            if (ix, iy) in cellkey:
                req.add((ix, iy, t))
    # (c) cell centres inside a polygon of each type present
    types = np.unique(ps.type)
    cl = sorted(cellkey)
    if cl:
        cix = np.array([c[0] for c in cl], np.float64)
        ciy = np.array([c[1] for c in cl], np.float64)
        qx = np.tile((cix + 0.5) * RAW, len(types))
        qy = np.tile((ciy + 0.5) * RAW, len(types))
        qt = np.repeat(types, len(cl))
        ok = region.inside(np.zeros(len(qx), np.int64), qy, qx, qt)
        for i in np.nonzero(ok)[0].tolist():
            req.add((int(cix[i % len(cl)]), int(ciy[i % len(cl)]), int(qt[i])))
    return req


def key_cells(container, key, lat: Lattice):
    """Cell rectangle `(c0, c1, r0, r1)` (inclusive) of a block key."""
    level, _bsi, _bidx, bsx, bsy, blx, bly = key[:7]
    lmr = next(l for l in container.pdmdh.levels if l.level == level)
    bb = walk._block_base_bounds(container.pdmdh, lmr, bsx, bsy, blx, bly)
    c0 = int(round(float(lat.dlon(bb.lon_lo)) / lat.cell_lon))
    r0 = int(round((bb.lat_lo - lat.lat0) / lat.cell_lat))
    c1 = c0 + int(round(walk._lon_span(bb.lon_lo, bb.lon_hi) / lat.cell_lon)) - 1
    r1 = r0 + int(round((bb.lat_hi - bb.lat_lo) / lat.cell_lat)) - 1
    return c0, c1, r0, r1


# ------------------------------------------------------------------ driver

def _pass1_tasks(reader: SpoolReader, levels, workers):
    tasks = []
    for lv in levels:
        idx = reader._load_idx(lv)
        if idx is None or idx.n == 0:
            continue
        w = np.cumsum(idx.length.astype(np.float64))
        nchunks = max(1, min(idx.n, workers * 4))
        cuts = np.searchsorted(w, w[-1] * np.arange(1, nchunks) / nchunks)
        bounds = sorted(set([0] + cuts.tolist() + [idx.n]))
        tasks += [(str(reader.spool_dir), lv, a, b) for a, b in zip(bounds[:-1], bounds[1:]) if b > a]
    return tasks


def _block_tasks(reader, container, keys, lats, workers):
    """`(key, rlo, rhi)` tasks, heaviest first: each block split into bands
    of cell rows so that no band carries much more than 1/(8 * workers) of
    the level's spool bytes (a leaf's decode cost follows its content)."""
    rows = []
    for k in keys:
        c0, c1, r0, r1 = key_cells(container, k, lats[k[0]])
        idx = reader._load_idx(k[0])
        w = np.zeros(r1 - r0 + 1)
        if idx is not None and idx.n:
            a = int(np.searchsorted(idx.iy, r0, "left"))
            b = int(np.searchsorted(idx.iy, r1 + 1, "left"))
            m = (idx.ix[a:b] >= c0) & (idx.ix[a:b] <= c1)
            np.add.at(w, idx.iy[a:b][m].astype(np.int64) - r0, idx.length[a:b][m])
        rows.append((k, r0, w))
    total = sum(float(w.sum()) for _k, _r0, w in rows) or 1.0
    target = total / (8 * max(1, workers))
    tasks = []
    for k, r0, w in rows:
        lo, acc = 0, 0.0
        for i, x in enumerate(w):
            acc += x
            if acc >= target or i == len(w) - 1:
                tasks.append((acc, k, r0 + lo, r0 + i))
                lo, acc = i + 1, 0.0
    tasks.sort(key=lambda t: (-t[0], t[1][:3], t[2]))
    return [t[1:] for t in tasks]


def _pool(workers):
    return mp.get_context("fork").Pool(workers) if workers > 1 else None


def _imap(pool, fn, tasks):
    if pool is None:
        return map(fn, tasks)
    return pool.imap_unordered(fn, tasks, chunksize=1)


def roundtrip_python(disc: str, spool: str, workers: int = 12, levels=None, log=None) -> dict:
    """The Python checking path (`--engine python`): the count oracle until Phase 5."""
    log = log or (lambda *a: None)
    t0 = time.time()
    disc, spool = str(disc), str(spool)
    container = walk.read_container(disc)
    keys = _block_keys(disc)
    if levels is not None:
        keys = [k for k in keys if k[0] in levels]
    lvls = sorted({k[0] for k in keys})
    reader = SpoolReader(spool)
    log(f"{len(keys)} blocks over levels {lvls} ({time.time() - t0:.1f}s)")

    # pass 1: tall shapes per level
    tall_parts: dict = {lv: [] for lv in lvls}
    pool = _pool(workers)
    try:
        for lv, a, arrs in _imap(pool, _pass1, _pass1_tasks(reader, lvls, workers)):
            tall_parts[lv].append((a, Shapes(*arrs)))
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    tall = {}
    for lv in lvls:
        sh = Shapes.concat([s for _a, s in sorted(tall_parts[lv], key=lambda p: p[0])])
        tall[lv] = (sh, sh.bbox())
        log(f"level {lv}: {sh.n} tall shapes, {len(sh.x)} coords ({time.time() - t0:.1f}s)")
    del tall_parts

    # pass 2: blocks, heaviest first
    lat = {lv: Lattice(lv) for lv in lvls}
    tasks = _block_tasks(reader, container, keys, lat, workers)
    log(f"{len(tasks)} block-band tasks ({time.time() - t0:.1f}s)")
    _G.clear()
    _G.update({"spool": spool, "disc": disc, "tall": tall})
    gc.collect()
    gc.freeze()   # keep refcount writes off the shared pages after fork
    accs = {lv: Acc() for lv in lvls}
    leaves = {lv: 0 for lv in lvls}
    pool = _pool(workers)
    done = 0
    try:
        for lv, acc, nl in _imap(pool, _check_block, tasks):
            accs[lv].merge(acc)
            leaves[lv] += nl
            done += 1
            if done % 500 == 0 or done == len(tasks):
                log(f"{done}/{len(tasks)} tasks ({time.time() - t0:.1f}s)")
    finally:
        if pool is not None:
            pool.close()
            pool.join()
        gc.unfreeze()
        _G.clear()
    res = _report(disc, spool, accs, leaves, {k[0]: 0 for k in keys}, keys, tall,
                  time.time() - t0)
    res["engine"] = "python"
    return res


# ------------------------------------------------------------------ K1 driver (Plan 04, 2-06)
# The default engine: a thin driver. It plans (block, row band) ranges with the same
# planner as the Python path (with a FIXED worker count, so the plan -- and with it every
# byte of the report -- does not depend on `-j`), makes ONE binding call per range
# (`kiwiw.cenc.k1_check_band`: D1 decode + all nine kinds in C), merges the per-range
# accumulators (sums, max, first-N-of-union: order and partition invariant) and writes the
# report schema of the Python path. Wall, PSS and C-side timers go in `timing`, which
# (with `wall_s`) is the only part that varies between runs.

PLAN_WORKERS = 12          # the band plan is made for this many workers whatever `-j` is
OPS_MAX_WORKERS = 6        # WORKFLOW / plan 05 K1/harness ops cap (≤ -j 6)
PSS_CEILING_KB = 9_726_501  # signed Phase 2 absolute ceiling (no margin); historical -j 12 peak
PSS_INTERVAL = 0.25
COMPARE_EXCLUDES = ["timing", "wall_s"]


def strip_compare_excludes(report: dict) -> dict:
    """A copy of a K1 report dict with every top-level key in
    `COMPARE_EXCLUDES` (`timing` and `wall_s`) removed; every other top-level
    key and all nested content is unchanged. One source of truth for the
    determinism strip shared by the 3-90 check and the fixture tests."""
    return {k: v for k, v in report.items() if k not in COMPARE_EXCLUDES}


def normalise_k1_report_for_compare(report) -> str:
    """Canonical JSON text of a K1 report with `COMPARE_EXCLUDES` stripped,
    suitable for `cmp` between two `-j` runs. `report` is a report dict or a
    path to a report JSON file."""
    if not isinstance(report, dict):
        report = json.loads(Path(report).read_text())
    return json.dumps(strip_compare_excludes(report), indent=2, sort_keys=True)


_REASON_TEXT = {
    0: "outside [0, range] or non-integral",
    1: "no spool record within half a raw unit",
    2: "step not representable",
    3: "leaf did not decode",
    4: "not within half a raw unit of a same-type spool outline",
    5: "boundary vertex outside every same-type spool polygon",
    6: "interior-cover centre outside every same-type spool polygon",
    7: "a spool polygon of this type meets the cell but no decoded piece of it does",
}


def _pss_kb(pid):
    try:
        with open(f"/proc/{pid}/smaps_rollup") as f:
            for line in f:
                if line.startswith("Pss:"):
                    return int(line.split()[1])
    except (OSError, ValueError):
        pass
    return 0


class PssSampler:
    """Samples the summed `Pss:` (kB, `/proc/<pid>/smaps_rollup`) of this process and its
    live multiprocessing children every `interval` seconds; `peak_kb` is the maximum."""

    def __init__(self, interval=PSS_INTERVAL):
        import os
        import threading
        self.interval, self.peak_kb, self.samples = interval, 0, 0
        self._pid, self._stop = os.getpid(), threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def sample(self):
        pids = [self._pid] + [c.pid for c in mp.active_children() if c.pid]
        total = sum(_pss_kb(p) for p in pids)
        self.samples += 1
        self.peak_kb = max(self.peak_kb, total)

    def _run(self):
        while not self._stop.is_set():
            self.sample()
            self._stop.wait(self.interval)

    def start(self):
        self.sample()
        self._t.start()
        return self

    def stop(self):
        self._stop.set()
        self._t.join()
        self.sample()
        return self.peak_kb


def _k1_state():
    from kiwiw import cenc
    st = _G.get("k1")
    if st is None:
        import numpy as np
        st = _G["k1"] = {"container": walk.read_container(_G["disc"]),
                         "region": np.memmap(_G["disc"], dtype=np.uint8, mode="r"),
                         "cache": {}, "spools": {}}
    return cenc, st


def _k1_spool(cenc, st, level):
    sp = st["spools"].get(level)
    if sp is None:
        sp = st["spools"][level] = cenc.E1Spool(_G["spool"], level)
    return sp


def _k1_band(task):
    """One range: ONE binding call; returns the level and its accumulator. `task` is
    `(task index, key, rlo, rhi)`; with the dump on, this worker writes its own part
    file per kind (`part_<index>_<kind>.bin`) -- row buffers never cross the pool."""
    idx, key, rlo, rhi = task
    cenc, st = _k1_state()
    acc = cenc.K1Acc()
    row = cenc.d1_block_rows([key], st["container"], st["cache"])[0:1]
    dinfo = _G.get("dump")
    dump = cenc.K1Dump() if dinfo is not None else None
    cenc.k1_check_band(st["region"], row, rlo, rhi, _k1_spool(cenc, st, key[0]), acc,
                       dump=dump)
    if dump is not None and len(dump.rows):
        _write_dump_parts(dinfo["dir"], dinfo["index"], idx, dump.rows, dinfo["kinds"])
    return key[0], acc


def _write_dump_parts(dump_dir, kind_index, tidx, rows, kinds):
    """One file per kind with rows in this band (`DIR/part_<tidx:05d>_<kind>.bin`)."""
    kk = rows["kind"]
    for name in kinds:
        sel = rows[kk == kind_index[name]]
        if len(sel):
            sel.tofile(Path(dump_dir) / f"part_{tidx:05d}_{name}.bin")


def _finalize_dump(dump_dir, kinds, ntasks, log):
    """Concatenate the per-task parts per kind, order them canonically (independent of
    the band split), write `DIR/<kind>.bin`, delete the parts and write the manifest;
    return `{kind: rows}` for the report."""
    from kiwiw import cenc
    dump_dir = Path(dump_dir)
    fields = [{"name": n, "type": t} for n, t in cenc.K1_DUMP_FIELDS]
    row_size = cenc.K1_DUMP_DTYPE.itemsize
    counts = {}
    for name in kinds:
        paths, sizes = [], []
        for i in range(ntasks):
            p = dump_dir / f"part_{i:05d}_{name}.bin"
            if p.exists():
                paths.append(p)
                sizes.append(p.stat().st_size // row_size)
        total = sum(sizes)
        arr = np.empty(total, dtype=cenc.K1_DUMP_DTYPE) if total else np.zeros(0, cenc.K1_DUMP_DTYPE)
        off = 0
        for p, n in zip(paths, sizes):
            if n:
                with open(p, "rb") as fh:
                    if fh.readinto(arr[off:off + n]) != n * row_size:
                        raise OSError(f"short read of dump part: {p}")
            p.unlink()
            off += n
        del paths, sizes
        out_path = dump_dir / f"{name}.bin"
        if len(arr) > 1:
            order = np.argsort(arr, order=DUMP_ORDER, kind="stable")
            # Write in sorted order in bounded slices — identical bytes to
            # `arr[order].tofile`, without materialising a second full copy.
            _chunk = 65536
            with open(out_path, "wb") as fh:
                for start in range(0, len(order), _chunk):
                    arr[order[start:start + _chunk]].tofile(fh)
            del order
        else:
            arr.tofile(out_path)
        counts[name] = int(len(arr))
        del arr
    manifest = {"tool": "quantisation_roundtrip", "engine": "c", "row_size": row_size,
                "fields": fields,
                "kinds": {n: {"rows": counts[n], "row_size": row_size,
                              "file": f"{n}.bin", "fields": fields} for n in kinds}}
    (dump_dir / "dump_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    log("dump: " + ", ".join(f"{n} {counts[n]:,}" for n in kinds))
    return counts


def _k1_rows(res, kind):
    out = []
    for r in res["samples"][kind]:
        cell, rsn = [r["ix"], r["iy"]], r["reason"]
        if rsn == 7:
            row = {"cell": cell, "kind": kind, "type": r["code"], "reason": _REASON_TEXT[7]}
        elif rsn == 3:
            row = {"cell": cell, "leaf_path": r["path"], "kind": kind,
                   "reason": f"{_REASON_TEXT[3]} (K1 status {r['code']})"}
        elif rsn == 6:
            row = {"cell": cell, "leaf_path": r["path"], "kind": kind, "type": r["code"],
                   "reason": _REASON_TEXT[6]}
        else:
            row = {"cell": cell, "leaf_path": r["path"], "kind": kind,
                   "vertex": {"lat": round(r["lat"], 9), "lon": round(r["lon"], 9),
                              "raw": [r["vx"], r["vy"]]},
                   "reason": _REASON_TEXT[rsn], "error_raw": _fmt(r["err"])}
        out.append(row)
    return out


def _k1_report(disc, spool, accs, nblocks, tall_n, wall, pss_peak_kb, workers, nranges,
               dump=None):
    levels, totals = {}, {k: {"checked": 0, "failing": 0, "worst_error_raw": 0.0} for k in KINDS}
    stats = {}
    for lv in sorted(accs):
        r = accs[lv].result()
        kinds = {}
        for k in KINDS:
            c, w = r["kinds"][k], round(r["kinds"][k]["worst"], 6)
            kinds[k] = {"checked": c["checked"], "failing": c["failing"], "worst_error_raw": w}
            t = totals[k]
            t["checked"] += c["checked"]
            t["failing"] += c["failing"]
            t["worst_error_raw"] = max(t["worst_error_raw"], w)
        levels[str(lv)] = {"blocks": nblocks.get(lv, 0), "leaves": r["stats"]["leaves"],
                           "tall_shapes": tall_n[lv], "kinds": kinds,
                           "explained": dict(r["explained"]),
                           "failures": [x for k in KINDS for x in _k1_rows(r, k)]}
        for k, v in r["stats"].items():
            stats[k] = stats.get(k, 0) + v
    failing = sum(t["failing"] for t in totals.values())
    res = {"tool": "quantisation_roundtrip", "engine": "c", "disc": Path(disc).name,
           "spool": Path(spool).name, "tolerance_raw": TOL, "pass": failing == 0,
           "failing": failing, "totals": totals, "levels": levels, "wall_s": round(wall, 1),
           "compare_excludes": COMPARE_EXCLUDES,
           "timing": {"wall_s": round(wall, 3), "workers": workers, "ranges": nranges,
                      "pss_peak_kb": pss_peak_kb, "pss_interval_s": PSS_INTERVAL,
                      "c_ns": stats.get("ns", 0), "d1_ns": stats.get("d1_ns", 0),
                      "c_check_s": round(stats.get("ns", 0) / 1e9, 3),
                      "d1_decode_s": round(stats.get("d1_ns", 0) / 1e9, 3),
                      "c_stats": stats}}
    if dump is not None:
        res["dump"] = dump
    return res


def roundtrip_c(disc: str, spool: str, workers: int = 12, levels=None, log=None,
                dump_dir=None, dump_kinds=None) -> dict:
    """Run every check in C (K1); return the report dict. With `dump_dir`, also write
    every failing item of `dump_kinds` to `DIR/<kind>.bin` plus `DIR/dump_manifest.json`
    (brief 3-02), and add `"dump": {kind: rows}` to the report."""
    from kiwiw import cenc
    if cenc._load_lib() is None:
        raise RuntimeError("--engine c needs a C compiler (kiwiw.cbuild); use --engine python")
    log = log or (lambda *a: None)
    kind_index = None
    if dump_dir is not None:
        cenc._load_k1()
        names = list(cenc._k1_cols["kinds"])
        want = set(dump_kinds) if dump_kinds else set(DUMP_KINDS)
        bad = sorted(want - set(DUMP_KINDS))
        if bad:
            raise ValueError(f"--dump-kinds must be among {DUMP_KINDS}: {bad}")
        dump_kinds = tuple(k for k in DUMP_KINDS if k in want)
        kind_index = {k: names.index(k) for k in dump_kinds}
        d = Path(dump_dir)
        d.mkdir(parents=True, exist_ok=True)
        for p in list(d.glob("part_*.bin")) + [d / f"{k}.bin" for k in dump_kinds] \
                + [d / "dump_manifest.json"]:
            if p.exists():
                p.unlink()
    t0 = time.time()
    sampler = PssSampler()   # its thread starts after the pool forks (no fork of a threaded parent)
    sampler.sample()
    disc, spool = str(disc), str(spool)
    container = walk.read_container(disc)
    keys = _block_keys(disc)
    if levels is not None:
        keys = [k for k in keys if k[0] in levels]
    lvls = sorted({k[0] for k in keys})
    reader = SpoolReader(spool)
    lat = {lv: Lattice(lv) for lv in lvls}
    tasks = _block_tasks(reader, container, keys, lat, PLAN_WORKERS)
    nblocks = {}
    for k in keys:
        nblocks[k[0]] = nblocks.get(k[0], 0) + 1
    log(f"{len(keys)} blocks over levels {lvls}, {len(tasks)} ranges ({time.time() - t0:.1f}s)")
    plan = [(i, k, rlo, rhi) for i, (k, rlo, rhi) in enumerate(tasks)]
    _G.clear()
    _G.update({"spool": spool, "disc": disc})
    if kind_index is not None:
        _G["dump"] = {"dir": str(dump_dir), "kinds": dump_kinds, "index": kind_index}
    cenc_, st = _k1_state()
    tall_n = {}
    for lv in lvls:   # the level's tall shapes, once, before the fork
        k0 = next(k for k in keys if k[0] == lv)
        hit = cenc._k1_tallset(_k1_spool(cenc_, st, lv),
                               cenc.d1_block_rows([k0], st["container"], st["cache"])[0:1])
        tall_n[lv] = len(hit[0]) if hit[4] else 0
    gc.collect()
    gc.freeze()
    accs = {lv: cenc.K1Acc() for lv in lvls}
    sampler.sample()
    pool = _pool(workers)
    sampler.start()
    done = 0
    try:
        for lv, acc in _imap(pool, _k1_band, plan):
            accs[lv].merge(acc)
            done += 1
            if done % 500 == 0 or done == len(plan):
                log(f"{done}/{len(plan)} ranges ({time.time() - t0:.1f}s)")
    finally:
        if pool is not None:
            pool.close()
            pool.join()
        gc.unfreeze()
        _G.clear()
    peak = sampler.stop()
    dump_counts = None
    if kind_index is not None:
        dump_counts = _finalize_dump(dump_dir, dump_kinds, len(tasks), log)
    return _k1_report(disc, spool, accs, nblocks, tall_n, time.time() - t0, peak, workers,
                      len(tasks), dump=dump_counts)


def roundtrip(disc: str, spool: str, workers: int = 12, levels=None, log=None,
              engine: str = "python", dump_dir=None, dump_kinds=None) -> dict:
    """Run every check; return the report dict. `engine`: `c` (K1, the CLI default) or
    `python` (the oracle; the library default so Python-oracle callers are unchanged).
    `dump_dir`/`dump_kinds` are the `--dump-failures`/`--dump-kinds` options (C only)."""
    if engine == "c":
        return roundtrip_c(disc, spool, workers, levels, log, dump_dir, dump_kinds)
    if engine == "python":
        if dump_dir is not None:
            raise ValueError("--dump-failures needs --engine c")
        return roundtrip_python(disc, spool, workers, levels, log)
    raise ValueError(f"unknown engine {engine!r}")


def _report(disc, spool, accs, leaves, _unused, keys, tall, wall):
    levels = {}
    totals = {k: {"checked": 0, "failing": 0, "worst_error_raw": 0.0} for k in KINDS}
    nblocks = {}
    for k in keys:
        nblocks[k[0]] = nblocks.get(k[0], 0) + 1
    for lv in sorted(accs):
        acc = accs[lv]
        kinds = {}
        for k in KINDS:
            c, f, w = acc.k[k]
            kinds[k] = {"checked": c, "failing": f, "worst_error_raw": round(w, 6)}
            t = totals[k]
            t["checked"] += c
            t["failing"] += f
            t["worst_error_raw"] = max(t["worst_error_raw"], round(w, 6))
        levels[str(lv)] = {"blocks": nblocks.get(lv, 0), "leaves": leaves[lv],
                           "tall_shapes": int(tall[lv][0].n), "kinds": kinds,
                           "explained": dict(acc.explained),
                           "failures": [r for k in KINDS for r in acc.samples[k]]}
    failing = sum(t["failing"] for t in totals.values())
    return {"tool": "quantisation_roundtrip", "disc": Path(disc).name, "spool": Path(spool).name,
            "tolerance_raw": TOL, "pass": failing == 0, "failing": failing,
            "totals": totals, "levels": levels, "wall_s": round(wall, 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--disc", required=True, help="built ALLDATA.KWI")
    ap.add_argument("--spool", required=True, help="spool directory it was built from")
    ap.add_argument("--out", help="write the JSON report here")
    ap.add_argument("--workers", "-j", type=int, default=OPS_MAX_WORKERS)
    ap.add_argument("--engine", choices=("c", "python"), default="c",
                    help="c: K1 through libkiwiw (default); python: the count oracle")
    ap.add_argument("--levels", help="comma-separated levels to check (default: every level)")
    ap.add_argument("--dump-failures", metavar="DIR",
                    help="write every failing item of the dump kinds to DIR (<kind>.bin "
                         "plus dump_manifest.json); needs --engine c")
    ap.add_argument("--dump-kinds", default=",".join(DUMP_KINDS),
                    help=f"comma list of kinds to dump (default: {','.join(DUMP_KINDS)})")
    args = ap.parse_args(argv)
    levels = {int(x) for x in args.levels.split(",")} if args.levels else None
    dump_kinds = [x for x in args.dump_kinds.split(",") if x]

    def log(msg):
        print(f"[quantisation_roundtrip] {msg}", file=sys.stderr, flush=True)
    res = roundtrip(args.disc, args.spool, workers=args.workers, levels=levels, log=log,
                    engine=args.engine, dump_dir=args.dump_failures, dump_kinds=dump_kinds)
    text = json.dumps(res, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n")
    for k, v in res["totals"].items():
        log(f"{k}: checked {v['checked']:,} failing {v['failing']:,} "
            f"worst {v['worst_error_raw']}")
    if "timing" in res:
        tm = res["timing"]
        log(f"engine c: {tm['ranges']} ranges, PSS peak {tm['pss_peak_kb'] / 1024:.0f} MiB, "
            f"C check {tm['c_check_s']}s (D1 {tm['d1_decode_s']}s, summed over workers)")
    log(f"{'PASS' if res['pass'] else 'FAIL'} in {res['wall_s']}s")
    return 0 if res["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
