"""Independent EO footprint / wire representability for K1 completeness.

Ported from the Phase 2 complete-repair mirror, without importing research
artifacts or calling the encoder. Crossings use exact Fraction predicates;
face clipping and wire densification use the encoder's floating arithmetic.
"""
from collections import defaultdict
from fractions import Fraction
import math

def _as_frac(poly):
    return [(Fraction(x), Fraction(y)) for x, y in poly]


def _seg_proper_intersect(a, b, c, d):
    ax, ay = a; bx, by = b; cx, cy = c; dx, dy = d
    den = (bx - ax) * (dy - cy) - (by - ay) * (dx - cx)
    if den == 0:
        return None
    t = ((cx - ax) * (dy - cy) - (cy - ay) * (dx - cx)) / den
    u = ((cx - ax) * (by - ay) - (cy - ay) * (bx - ax)) / den
    if t <= 0 or t >= 1 or u <= 0 or u >= 1:
        return None
    return (ax + t * (bx - ax), ay + t * (by - ay))


def _point_in_poly_eo(px, py, ring):
    n = len(ring)
    odd = False
    for i in range(n):
        ax, ay = ring[i]
        bx, by = ring[(i + 1) % n]
        if (ay > py) != (by > py):
            xint = ax + (py - ay) / (by - ay) * (bx - ax)
            if px < xint:
                odd = not odd
    return odd


def _find_crossings(ring):
    n = len(ring)
    out = []
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        for j in range(i + 1, n):
            if (j + 1) % n == i or (i + 1) % n == j:
                continue
            if i == 0 and j == n - 1:
                continue
            c, d = ring[j], ring[(j + 1) % n]
            pt = _seg_proper_intersect(a, b, c, d)
            if pt is not None:
                out.append((i, j, pt))
    return out


def _edge_param(p, a, b):
    if abs(b[0] - a[0]) >= abs(b[1] - a[1]):
        return (p[0] - a[0]) / (b[0] - a[0])
    return (p[1] - a[1]) / (b[1] - a[1])


def _split_ring_at_crossings(ring, crossings):
    n = len(ring)
    cuts = [[] for _ in range(n)]
    for i, j, pt in crossings:
        a, b = ring[i], ring[(i + 1) % n]
        c, d = ring[j], ring[(j + 1) % n]
        cuts[i].append((_edge_param(pt, a, b), pt))
        cuts[j].append((_edge_param(pt, c, d), pt))

    vids = {}
    verts = []

    def vid(p):
        if p not in vids:
            vids[p] = len(verts)
            verts.append(p)
        return vids[p]

    for p in ring:
        vid(p)
    for cuts_e in cuts:
        for _, p in cuts_e:
            vid(p)

    edge_parity = defaultdict(int)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        pts = [(Fraction(0), a)] + sorted(cuts[i], key=lambda t: t[0]) + [(Fraction(1), b)]
        cleaned = [pts[0]]
        for t, p in pts[1:]:
            if p != cleaned[-1][1]:
                cleaned.append((t, p))
        for k in range(len(cleaned) - 1):
            u, v = vid(cleaned[k][1]), vid(cleaned[k + 1][1])
            if u == v:
                continue
            key = (u, v) if u < v else (v, u)
            edge_parity[key] ^= 1

    edges = [(a, b) for (a, b), bit in edge_parity.items() if bit]
    return verts, edges


def _walk_faces(verts, edges):
    halves = []
    out_of = defaultdict(list)
    for a, b in edges:
        ia = len(halves)
        ib = ia + 1
        ang_ab = math.atan2(float(verts[b][1] - verts[a][1]),
                            float(verts[b][0] - verts[a][0]))
        ang_ba = math.atan2(float(verts[a][1] - verts[b][1]),
                            float(verts[a][0] - verts[b][0]))
        halves.append([a, b, ang_ab, ib])
        halves.append([b, a, ang_ba, ia])
        out_of[a].append(ia)
        out_of[b].append(ib)

    for v, hs in out_of.items():
        hs.sort(key=lambda h: halves[h][2])

    used = [False] * len(halves)
    faces = []
    for start in range(len(halves)):
        if used[start]:
            continue
        h = start
        cycle = []
        area2 = Fraction(0)
        guard = 0
        closed = False
        while not used[h] and guard < len(halves) + 2:
            used[h] = True
            a, b = halves[h][0], halves[h][1]
            cycle.append(a)
            area2 += verts[a][0] * verts[b][1] - verts[b][0] * verts[a][1]
            rev = halves[halves[h][3]][2]
            outs = out_of[b]
            best, best_turn = None, None
            for k in outs:
                turn = rev - halves[k][2]
                if turn <= 0:
                    turn += 2 * math.pi
                if best is None or turn < best_turn:
                    best, best_turn = k, turn
            if best is None:
                break
            h = best
            guard += 1
            if h == start:
                closed = True
                break
        if closed and len(cycle) >= 3 and area2 > 0:
            faces.append(cycle)
    return faces


def decompose_eo_faces(poly):
    """Decompose closed ring into EO simple faces (exact Fraction).

    Independent checker arrangement (ported from the Phase 2 mirror):
      * Fraction vertices; find proper edge-edge crossings (no endpoint touches).
      * No crossings -> one face.
      * Else split edges, cancel even-multiplicity coincident segments, walk CCW
        faces via leftmost-turn half-edge succession; keep faces whose mid-edge
        left-nudge sample is EO-interior of the original ring.
    """
    if len(poly) < 3:
        return []
    ring = list(poly)
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    if len(ring) < 3:
        return []
    fr = _as_frac(ring)
    crossings = _find_crossings(fr)
    if not crossings:
        return [[(float(x), float(y)) for x, y in fr]]

    verts, edges = _split_ring_at_crossings(fr, crossings)
    if not edges:
        return [[(float(x), float(y)) for x, y in fr]]
    cycles = _walk_faces(verts, edges)
    out = []
    for cyc in cycles:
        a, b = verts[cyc[0]], verts[cyc[1]]
        mx = (a[0] + b[0]) / 2
        my = (a[1] + b[1]) / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            continue
        scale = Fraction(1, 10 ** 9)
        sx = mx - dy * scale
        sy = my + dx * scale
        if not _point_in_poly_eo(sx, sy, fr):
            continue
        out.append([(float(verts[i][0]), float(verts[i][1])) for i in cyc])
    if not out:
        out = [[(float(x), float(y)) for x, y in fr]]
    return out



def clip_rect(poly, x0, y0, x1, y1):
    for axis, bound, lower in ((0, x0, True), (0, x1, False),
                               (1, y0, True), (1, y1, False)):
        out = []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            ia = a[axis] >= bound if lower else a[axis] <= bound
            ib = b[axis] >= bound if lower else b[axis] <= bound
            if ia:
                out.append(a)
            if ia != ib:
                t = (bound - a[axis]) / (b[axis] - a[axis])
                p = list(a)
                p[axis] = bound
                p[1 - axis] = a[1 - axis] + t * (b[1 - axis] - a[1 - axis])
                out.append(tuple(p))
        poly = out
    return poly


def wire_survives(poly, mc=1, *, densify=True):
    """Densify, ties-to-even round, adjacent/closing dedup, spikes, area2."""
    dn = []
    lim = 127.0 * max(1, mc) - 1.0
    for i, (ax, ay) in enumerate(poly):
        dn.append((ax, ay))
        bx, by = poly[(i + 1) % len(poly)]
        dx, dy = bx - ax, by - ay
        mx = max(abs(dx), abs(dy))
        if densify and mx > lim:
            k = math.ceil(mx / lim)
            if k >= 10 ** 7:
                raise ValueError("wire densification exceeds contract limit")
            dn.extend((ax + dx * (j / k), ay + dy * (j / k)) for j in range(1, k))
    q = []
    for x, y in dn:
        p = (round(x), round(y))
        if not q or p != q[-1]:
            q.append(p)
    while len(q) > 1 and q[-1] == q[0]:
        q.pop()
    while len(q) >= 3:
        found = next((i for i in range(len(q)) if q[i - 1] == q[(i + 1) % len(q)]), None)
        if found is None:
            break
        del q[found]
        del q[found % len(q)]
    return len(q) >= 3 and sum(q[i][0] * q[(i + 1) % len(q)][1]
                               - q[(i + 1) % len(q)][0] * q[i][1]
                               for i in range(len(q))) != 0


def representable(poly, ix, iy, mc=1):
    """Some EO face clipped to this cell survives the wire contract."""
    return any(wire_survives(clip_rect(face, ix * 4096, iy * 4096,
                                       (ix + 1) * 4096, (iy + 1) * 4096), mc)
               for face in decompose_eo_faces(poly))


def centre_demands(poly, ix, iy, tol):
    """Per-shape branch (c), resolved only for a missing pair."""
    x, y = (ix + 0.5) * 4096, (iy + 0.5) * 4096
    cr = []
    for i, (ax, ay) in enumerate(poly):
        bx, by = poly[(i + 1) % len(poly)]
        if min(ay, by) <= y < max(ay, by):
            cr.append(ax + (y - ay) * (bx - ax) / (by - ay))
    cr.sort()
    return any(cr[i] <= x + tol and cr[i + 1] >= x - tol
               for i in range(0, len(cr) - 1, 2))
