"""Independent EO footprint / wire representability for K1 completeness.

Ported from the Phase 2 complete-repair mirror, without importing research
artifacts or calling the encoder. Topology uses exact Fraction predicates;
face clipping and wire densification use the encoder's floating arithmetic.
"""
from collections import defaultdict
from fractions import Fraction
import math

def _as_frac(poly):
    return [(Fraction(x), Fraction(y)) for x, y in poly]


def _contacts(ring):
    """All contacts, including overlap ends; adjacent shared ends are simple."""
    out = []
    n = len(ring)
    simple = len(set(ring)) == n
    for i, a in enumerate(ring):
        b = ring[(i + 1) % n]
        if a == b:
            simple = False
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        for j in range(i + 1, n):
            c, d = ring[j], ring[(j + 1) % n]
            if c == d:
                continue
            ex, ey = d[0] - c[0], d[1] - c[1]
            den = dx * ey - dy * ex
            if den:
                t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
                u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
                pts = [(a[0] + t * dx, a[1] + t * dy)] if 0 <= t <= 1 and 0 <= u <= 1 else []
            elif (c[0] - a[0]) * dy == (c[1] - a[1]) * dx:
                pts = [p for p in (a, b, c, d)
                       if min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                       and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
                       and min(c[0], d[0]) <= p[0] <= max(c[0], d[0])
                       and min(c[1], d[1]) <= p[1] <= max(c[1], d[1])]
            else:
                pts = []
            for pt in set(pts):
                adjacent = (i + 1) % n == j or (j + 1) % n == i
                if not (adjacent and pt in (a, b) and pt in (c, d)):
                    simple = False
                out.append((i, j, pt))
    return out, simple


def _edge_param(p, a, b):
    if abs(b[0] - a[0]) >= abs(b[1] - a[1]):
        return (p[0] - a[0]) / (b[0] - a[0])
    return (p[1] - a[1]) / (b[1] - a[1])


def _split_ring_at_contacts(ring, contacts):
    n = len(ring)
    cuts = [[] for _ in range(n)]
    for i, j, pt in contacts:
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

    edges = [(a, b, bit) for (a, b), bit in edge_parity.items() if bit]
    if not edges:
        return verts, []
    # Keep only a forest of even edges joining parity components. These are
    # zero-width cuts, needed to walk an outer boundary with nested holes.
    parent = list(range(len(verts)))

    def root(v):
        while v != parent[v]:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for a, b, _ in edges:
        parent[root(a)] = root(b)
    for (a, b), bit in edge_parity.items():
        if not bit and root(a) != root(b):
            parent[root(a)] = root(b)
            edges.append((a, b, 0))
    return verts, edges


def _walk_faces(verts, edges):
    from functools import cmp_to_key
    halves = []
    out_of = defaultdict(list)
    for a, b, odd in edges:
        h = len(halves)
        halves.extend([(a, b, odd), (b, a, odd)])
        out_of[a].append(h)
        out_of[b].append(h + 1)

    def direction_cmp(h, k):
        a, b = verts[halves[h][0]], verts[halves[h][1]]
        c, d = verts[halves[k][0]], verts[halves[k][1]]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ex, ey = d[0] - c[0], d[1] - c[1]
        upper = dy > 0 or (dy == 0 and dx > 0)
        other = ey > 0 or (ey == 0 and ex > 0)
        if upper != other:
            return -1 if upper else 1
        cross = dx * ey - dy * ex
        if not cross:
            raise ValueError("EO arrangement has coincident outgoing edges")
        return -1 if cross > 0 else 1

    successor = {}
    for hs in out_of.values():
        hs.sort(key=cmp_to_key(direction_cmp))
        for i, h in enumerate(hs):
            successor[h ^ 1] = hs[i - 1]
    face_of = {}
    faces = []
    for start in range(len(halves)):
        if start in face_of:
            continue
        h, cycle = start, []
        while h not in face_of:
            face_of[h] = len(faces)
            cycle.append(halves[h][0])
            h = successor[h]
        if h != start:
            raise ValueError("EO arrangement face walk did not close")
        faces.append(cycle)
    if not faces:
        return []
    # At the lowest vertex, the most CCW outgoing edge has exterior on its
    # left. Bridges make the graph connected, including nested boundaries.
    lowest = min(out_of, key=lambda v: (verts[v][1], verts[v][0]))
    outside = face_of[out_of[lowest][-1]]
    adjacent = defaultdict(list)
    for h in range(0, len(halves), 2):
        a, b = face_of[h], face_of[h ^ 1]
        odd = halves[h][2]
        adjacent[a].append((b, odd))
        adjacent[b].append((a, odd))
    parity = {outside: 0}
    pending = [outside]
    while pending:
        a = pending.pop()
        for b, odd in adjacent[a]:
            bit = parity[a] ^ odd
            if b in parity:
                if parity[b] != bit:
                    raise ValueError("EO arrangement has inconsistent face parity")
            else:
                parity[b] = bit
                pending.append(b)
    if len(parity) != len(faces):
        raise ValueError("EO arrangement has disconnected face topology")
    return [face for i, face in enumerate(faces) if parity[i]]



def decompose_eo_faces(poly):
    """Independent exact EO arrangement; empty parity stays empty.

    Split crossings, endpoint contacts and overlaps, cancel even edges, and
    walk faces with exact angular order and label them from exterior parity.
    Unlike the historical Phase 2 mirror, shortcut only proven simple rings.
    """
    ring = list(poly)
    if ring and ring[0] == ring[-1]:
        ring.pop()
    if len(ring) < 3:
        return []
    fr = _as_frac(ring)
    contacts, simple = _contacts(fr)
    if simple:
        return [[(float(x), float(y)) for x, y in fr]]
    verts, edges = _split_ring_at_contacts(fr, contacts)
    out = []
    for cyc in _walk_faces(verts, edges):
        out.append([(float(verts[i][0]), float(verts[i][1])) for i in cyc])
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
