"""Clip background geometry to its parcel's rectangle, as R does (Plan 03, 3-07).

R clips background polygons and lines to the coordinate frame: across every
sampled class no background vertex lies outside `[0, range]`, frame-corner
vertices mirror exactly into the neighbouring frame, a polygon that leaves
and re-enters is written as separate closed pieces (no zero-width bridges),
whole-cell fills are frame-corner rectangles and pen-up is never used
(research 2026-09-24, `output/research-3-bg/bg_edge_probe_v2.json`). Spec:
7.3.2.2.1.1 (coordinates limited to the parcel), 7.3.2.2.1.1.1 (area data
closed, counter-clockwise, non-self-crossing); roads 7.A (2) for the same
rule on links.

The geometry lives in the level's global raw lattice (DESIGN.md, "one global
raw lattice per level"): `X = gx0 * 4096 + x_local`. The encoder only knows
the frame, so it works in frame-local raw floats -- the global lattice
translated by the frame origin, an exact integer offset -- and clips there,
*before* rounding: a crossing point is computed from the segment's own
geometry (endpoints in a canonical order, so both frames sharing the edge
evaluate the same expression) and lands exactly on the edge on its crossed
axis. Only then is every vertex rounded (half-to-even, as `latlon_to_xy`).

After clipping, each piece is densified so that no rounded step exceeds the
record's signed-8-bit delta (`127 * mult`): the encoder then writes every
vertex exactly, with no saturating drift.

`_cenc.c` implements the same algorithm with the same float operation order;
the two are byte-identical (`tests/test_cenc.py`). Keep them in step.

Clip rectangle: the parcel's own extent within its frame -- `[0, range]^2`
for an undivided parcel, the sub-cell's quadrant/cell of the parent's 4096
frame for a divided sub-parcel (`SubParcelBounds.clip_rect`, set by
`divide._sub_frame`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .model import BoundingBox

# Per-vertex provenance of a written vertex.
ORIG = 0      # an input vertex inside the rectangle
CROSS_X = 1   # an edge crossing on a vertical edge (x == x0 or x1 exactly)
CROSS_Y = 2   # an edge crossing on a horizontal edge (y == y0 or y1 exactly)
CORNER = 3    # a rectangle corner inserted along the boundary
DENSE = 4     # an interpolated point splitting a step longer than one delta

KIND_NAMES = {ORIG: "original", CROSS_X: "crossing", CROSS_Y: "crossing",
              CORNER: "corner", DENSE: "densified"}


@dataclass
class SubParcelBounds(BoundingBox):
    """A divided sub-parcel's frame: its parent's bounds and range, plus the
    raw rectangle `(x0, y0, x1, y1)` the sub-parcel occupies in that frame."""
    clip_rect: Optional[tuple] = None


def clip_rect(bounds: BoundingBox, coord_range: int) -> tuple:
    """The rectangle background geometry is clipped to, in frame raw units."""
    r = getattr(bounds, "clip_rect", None)
    if r is None:
        return (0, 0, coord_range, coord_range)
    return tuple(int(v) for v in r)


def sub_rect(coord_range: int, nx: int, ny: int, sub_ix: int, sub_iy: int) -> tuple:
    """Raw rectangle of sub-cell (sub_ix, sub_iy) of an nx x ny division."""
    return (sub_ix * coord_range // nx, sub_iy * coord_range // ny,
            (sub_ix + 1) * coord_range // nx, (sub_iy + 1) * coord_range // ny)


def to_raw(coords, bounds: BoundingBox, coord_range: int):
    """Frame-local raw floats, `latlon_to_xy`'s operation order, unrounded."""
    dlon = bounds.lon_hi - bounds.lon_lo
    dlat = bounds.lat_hi - bounds.lat_lo
    fx = [(lon - bounds.lon_lo) / dlon * coord_range for _lat, lon in coords]
    fy = [(lat - bounds.lat_lo) / dlat * coord_range for lat, _lon in coords]
    return fx, fy


# ------------------------------------------------------------------ segment

def _y_at(ax, ay, bx, by, xe):
    """y where segment (a, b) meets x = xe, endpoints in canonical order."""
    if (bx, by) < (ax, ay):
        ax, ay, bx, by = bx, by, ax, ay
    return ay + (by - ay) * ((xe - ax) / (bx - ax))


def _x_at(ax, ay, bx, by, ye):
    if (bx, by) < (ax, ay):
        ax, ay, bx, by = bx, by, ax, ay
    return ax + (bx - ax) * ((ye - ay) / (by - ay))


def _clampf(v, lo, hi):
    # Float guard for a crossing's *other* coordinate (ulp-level only: the
    # crossing lies on the rectangle mathematically). Not a vertex clamp.
    return lo if v < lo else hi if v > hi else v


def _seg(ax, ay, bx, by, rect):
    """Liang-Barsky over the closed rectangle. None when the inside portion
    is empty or a single point; else (start, end) points as (x, y, kind),
    with an input endpoint returned exactly when the portion reaches it."""
    x0, y0, x1, y1 = rect
    dx = bx - ax
    dy = by - ay
    t0, t1 = 0.0, 1.0
    e0 = e1 = 0  # edge that set t0/t1: 1 x0, 2 x1, 3 y0, 4 y1
    for p, q, edge in ((-dx, ax - x0, 1), (dx, x1 - ax, 2), (-dy, ay - y0, 3), (dy, y1 - ay, 4)):
        if p == 0.0:
            if q < 0.0:
                return None
            continue
        r = q / p
        if p < 0.0:
            if r > t0:
                t0, e0 = r, edge
        elif r < t1:
            t1, e1 = r, edge
    if not t0 < t1:
        return None
    return (_edge_pt(ax, ay, bx, by, e0, rect) if e0 else (ax, ay, ORIG),
            _edge_pt(ax, ay, bx, by, e1, rect) if e1 else (bx, by, ORIG))


def _edge_pt(ax, ay, bx, by, edge, rect):
    x0, y0, x1, y1 = rect
    if edge <= 2:
        xe = x0 if edge == 1 else x1
        return (xe, _clampf(_y_at(ax, ay, bx, by, xe), y0, y1), CROSS_X)
    ye = y0 if edge == 3 else y1
    return (_clampf(_x_at(ax, ay, bx, by, ye), x0, x1), ye, CROSS_Y)


# ------------------------------------------------------------------- chains

def _chains(fx, fy, rect, closed):
    """Inside runs of the polyline (ring when `closed`), in input order.
    Returns (chains, whole) -- `whole` True when a closed ring never leaves."""
    n = len(fx)
    nseg = n if closed else n - 1
    por = [_seg(fx[i], fy[i], fx[(i + 1) % n], fy[(i + 1) % n], rect) for i in range(nseg)]

    def joins(i):  # portion i continues portion i-1 through their shared vertex
        if por[i] is None or por[i][0][2] != ORIG:
            return False
        j = i - 1 if i else (nseg - 1 if closed else -1)
        return j >= 0 and por[j] is not None and por[j][1][2] == ORIG

    starts = [i for i in range(nseg) if por[i] is not None and not joins(i)]
    if closed and not starts:
        return [], all(p is not None for p in por) and nseg > 0
    chains = []
    for s in starts:
        a, b = por[s]
        ch = [a, b]
        i = (s + 1) % nseg if closed else s + 1
        while i < nseg and i != s and por[i] is not None and joins(i):
            ch.append(por[i][1])
            i = (i + 1) % nseg if closed else i + 1
        chains.append(ch)
    return chains, False


def _s(p, rect):
    """Counter-clockwise boundary parameter of a point on the rectangle."""
    x0, y0, x1, y1 = rect
    x, y = p[0], p[1]
    w, h = x1 - x0, y1 - y0
    if y == y0:
        return x - x0
    if x == x1:
        return w + (y - y0)
    if y == y1:
        return w + h + (x1 - x)
    return 2 * w + h + (y1 - y)


def _pip(px, py, fx, fy):
    """Even-odd point-in-polygon (ring without closing duplicate)."""
    inside = False
    n = len(fx)
    j = n - 1
    for i in range(n):
        if (fy[i] > py) != (fy[j] > py):
            xi = fx[i] + (py - fy[i]) / (fy[j] - fy[i]) * (fx[j] - fx[i])
            if px < xi:
                inside = not inside
        j = i
    return inside


def _ring_pieces(fx, fy, rect):
    """Weiler-Atherton against the rectangle for a CCW ring (no closing
    duplicate): one list of (x, y, kind) per closed piece."""
    x0, y0, x1, y1 = rect
    corners = [(x0, y0, CORNER), (x1, y0, CORNER), (x1, y1, CORNER), (x0, y1, CORNER)]
    chains, whole = _chains(fx, fy, rect, True)
    if whole:
        return [[(fx[i], fy[i], ORIG) for i in range(len(fx))]]
    if not chains:
        cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        return [list(corners)] if _pip(cx, cy, fx, fy) else []
    w, h = x1 - x0, y1 - y0
    per = 2.0 * (w + h)
    cs = [0.0, float(w), float(w + h), float(2 * w + h)]
    s_in = [_s(c[0], rect) for c in chains]
    s_out = [_s(c[-1], rect) for c in chains]
    m = len(chains)
    used = [False] * m
    pieces = []
    for c0 in range(m):
        if used[c0]:
            continue
        piece = []
        c = c0
        for _guard in range(m + 1):
            used[c] = True
            piece.extend(chains[c])
            sx = s_out[c]
            best, bd = -1, 0.0
            for k in range(m):
                d = s_in[k] - sx
                if d < 0.0:
                    d += per
                if best < 0 or d < bd:
                    best, bd = k, d
            ins = []
            for ci in range(4):
                dc = cs[ci] - sx
                if dc < 0.0:
                    dc += per
                if 0.0 < dc < bd:
                    ins.append((dc, ci))
            ins.sort()
            piece.extend(corners[ci] for _dc, ci in ins)
            if best == c0 or used[best]:
                break
            c = best
        pieces.append(piece)
    return pieces


# ------------------------------------------------------------------- finish

def _densify(pts, closed, lim):
    out = []
    n = len(pts)
    nseg = n if closed else n - 1
    for i in range(n):
        a = pts[i]
        out.append(a)
        if i >= nseg:
            break
        b = pts[(i + 1) % n]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        mx = max(abs(dx), abs(dy))
        if mx > lim:
            k = int(math.ceil(mx / lim))
            for j in range(1, k):
                t = j / k
                out.append((a[0] + dx * t, a[1] + dy * t, DENSE))
    return out


def _round_clean(pts, closed):
    """Round, drop repeated consecutive vertices and (rings) spikes; None
    when the piece is degenerate. Rings come back with the closing vertex."""
    q = []
    for p in pts:
        x, y = round(p[0]), round(p[1])
        if q and q[-1][0] == x and q[-1][1] == y:
            continue
        q.append((x, y, p[0], p[1], p[2]))
    if closed:
        while len(q) > 1 and q[-1][0] == q[0][0] and q[-1][1] == q[0][1]:
            q.pop()
        while len(q) >= 3:
            n = len(q)
            for i in range(n):
                a, c = q[i - 1], q[(i + 1) % n]
                if a[0] == c[0] and a[1] == c[1]:
                    break
            else:
                break
            # spike at i: drop it, then its successor (now repeating q[i-1])
            q.pop(i)
            q.pop(i if i < len(q) else 0)
        if len(q) < 3:
            return None
        area2 = 0
        n = len(q)
        for i in range(n):
            area2 += q[i][0] * q[(i + 1) % n][1] - q[(i + 1) % n][0] * q[i][1]
        if area2 == 0:
            return None
        if area2 < 0:  # a sliver whose orientation flipped on rounding
            q = [q[0]] + q[:0:-1]
        q.append(q[0])
    elif len(q) < 2:
        return None
    return q


def shape_pieces(fx, fy, closed: bool, rect: tuple, mult: int = 1):
    """Clip one shape (raw floats) to `rect`; each written piece as a list of
    `(x, y, fx, fy, kind)` -- rounded vertex, its exact pre-rounding position,
    provenance. Rings are closed (last == first) and counter-clockwise."""
    fx, fy = list(fx), list(fy)
    if closed:
        if len(fx) > 1 and fx[-1] == fx[0] and fy[-1] == fy[0]:
            fx.pop()
            fy.pop()
        a2 = 0.0
        n = len(fx)
        for i in range(n):
            j = (i + 1) % n
            a2 += fx[i] * fy[j] - fx[j] * fy[i]
        if a2 < 0.0:
            fx = [fx[0]] + fx[:0:-1]
            fy = [fy[0]] + fy[:0:-1]
    x0, y0, x1, y1 = rect
    if closed and len(fx) < 3 or len(fx) < 2:
        raw = []
    elif all(x0 <= x <= x1 for x in fx) and all(y0 <= y <= y1 for y in fy):
        raw = [[(fx[i], fy[i], ORIG) for i in range(len(fx))]]  # nothing to clip
    elif closed:
        raw = _ring_pieces(fx, fy, rect)
    else:
        raw = _chains(fx, fy, rect, False)[0]
    lim = 127.0 * (mult if mult >= 1 else 1) - 1.0
    out = []
    for p in raw:
        q = _round_clean(_densify(p, closed, lim), closed)
        if q is not None:
            out.append(q)
    return out
