#!/usr/bin/env python3
"""Plan 14 Phase 2 unit 2-02 -- group `r-absent-complete-repair-zero`.

New complete-repair reproducer under plan-14 triage (DESIGN Assumption 5:
3-15 science may be cited but does not close the group alone).

For every Phase 1 seed with R_polygon_count == 0 except dump_row 335 (432):

  1. Load meeting class-2 source ring from spool via Phase 1 requirement witness.
  2. Decompose to even-odd simple faces (exact-Fraction arrangement, 3-13-style).
     Simple rings (no proper crossing) are one face.
  3. Clip each face to the target cell; replay _cenc.c:emit_piece via
     encoder_piece_densified (densify lim=127*mc-1, then rint/dedup/spike/
     q<3/area2==0). The 2-01 no-densify mirror result is recorded alongside.
  3b. Cross-check with production C ``kw__bg_shape`` (scratch probe that
      #includes parser/kiwiw/_cenc.c read-only) on the ORIGINAL ring (which
      already carries the 3-14 EO stitch) and on every repaired face.
  4. Member iff every repaired face yields 0 representable pieces (Python
     mirror AND C records both zero).
     Emitters -> unit 2-03.

Positive control: in-cell square must emit under the same path.

Plan 25: --max-seeds / --all-seeds, batch gc, whole_file_guard, strip coords.
No rule/encoder/checker edit. Writes plan-14 triage + output/scratch-14/complete_repair/.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import sys
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
TRIAGE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"), str(TRIAGE)]

from kiwiw.spool import SpoolReader  # noqa: E402
from quantisation_roundtrip import Lattice, RAW  # noqa: E402
from whole_file_guard import refuse_whole_file_read  # noqa: E402
import importlib.util as _ilu  # noqa: E402
_cl_path = TRIAGE / "cell_local_2-01.py"
_cl_spec = _ilu.spec_from_file_location("cell_local_2_01", _cl_path)
_cl = _ilu.module_from_spec(_cl_spec)
_cl_spec.loader.exec_module(_cl)
clip_rect = _cl.clip_rect
encoder_piece = _cl.encoder_piece
spool_source_shape = _cl.spool_source_shape


def encoder_piece_densified(poly, mc: int = 1):
    """Replay `_cenc.c:emit_piece` INCLUDING densify (lines 534-558).

    2-01's `encoder_piece` omits the densify step. emit_piece first inserts
    k-1 evenly spaced points on every closed-ring edge whose Chebyshev length
    exceeds lim = 127*mc - 1, THEN rints, dedups, collapses spikes, applies
    `q < 3` and `area2 == 0`. Densified midpoints can round onto existing
    vertices and create spikes, so densify can only remove pieces here.
    The axis-aligned rect path (`rect_mult_for`) is not mirrored; production
    C `kw__bg_shape` is run alongside as the authority.
    """
    if not poly:
        return 0, 0, False
    lim = 127.0 * mc - 1.0
    n = len(poly)
    dn = []
    for i in range(n):
        ax, ay = poly[i]
        dn.append((ax, ay))
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        mx = max(abs(dx), abs(dy))
        if mx > lim:
            k = int(np.ceil(mx / lim))
            for j in range(1, k):
                tt = j / k
                dn.append((ax + dx * tt, ay + dy * tt))
    return encoder_piece(dn)

EVIDENCE = TRIAGE / "completeness_evidence.tsv"
SPOOL = ROOT / "output/extract_timing/spool"
G_DISC = ROOT / "output/scratch-14/G_new"
G_SHA = "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72"
SCRATCH = ROOT / "output/scratch-14/complete_repair"
PROOFS = SCRATCH / "proofs"

NATIVE = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
          "shape", "vert")
MEMBERSHIP_HEADER = [
    "level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6",
    "shape", "vert", "dump_row", "in_historic_188", "in_added_89",
    "R_polygon_count", "G_polygon_count",
    "spool_source_branch", "spool_source_cell", "spool_source_ncoord",
    "source_n_crossings", "n_eo_faces", "n_faces_clipped",
    "n_faces_emit", "max_clipped_area2", "c_records_original",
    "c_records_repaired", "any_encoder_emits",
    "mechanism", "membership", "proof_path",
]


def digest(path: Path) -> str:
    with Path(path).open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def assert_no_whole_file(spool_dir: Path, g_path: Path) -> None:
    for label, p in (("G", g_path), ("spool_L0", spool_dir / "level_0.data")):
        if not p.exists():
            raise SystemExit(f"missing {label} path {p}")
        try:
            refuse_whole_file_read(p)
            raise SystemExit(f"plan25: {label} {p} under refuse threshold")
        except Exception as e:
            if e.__class__.__name__ != "WholeFileReadError":
                raise


# ---- Exact-Fraction EO face decomposition (3-13-style) --------------------

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

    Documented algorithm (plan-14 reimplementation of 3-13-style arrangement):
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


def count_crossings(poly):
    ring = list(poly)
    if ring and ring[0] == ring[-1]:
        ring = ring[:-1]
    if len(ring) < 4:
        return 0
    return len(_find_crossings(_as_frac(ring)))


def positive_control(ix: int = 0, iy: int = 0) -> dict:
    x0, y0 = ix * RAW + 512, iy * RAW + 512
    x1, y1 = ix * RAW + 3584, iy * RAW + 3584
    square = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    # bowtie that EO-repairs into two triangles, both representable when large
    bow = [(x0, y0), (x1, y1), (x0, y1), (x1, y0)]
    faces_sq = decompose_eo_faces(square)
    faces_bow = decompose_eo_faces(bow)
    cl = clip_rect(faces_sq[0], ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
    q, area2, emits = encoder_piece_densified(cl)
    bow_emits = 0
    for f in faces_bow:
        c2 = clip_rect(f, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
        _, _, em = encoder_piece_densified(c2)
        if em:
            bow_emits += 1
    return {
        "square_n_faces": len(faces_sq),
        "square_q": q,
        "square_area2": area2,
        "square_emits": emits,
        "bowtie_n_faces": len(faces_bow),
        "bowtie_n_emit": bow_emits,
        "pass": bool(emits and area2 != 0 and q >= 3 and bow_emits >= 1),
    }


def source_cell_sha(spool, level, source_cell):
    """sha256 of the spool source cell bytes (Phase 1 witness pin)."""
    ix, iy = int(source_cell[1]), int(source_cell[2])
    idx = spool._load_idx(level)
    pos = np.nonzero((idx.ix == ix) & (idx.iy == iy))[0]
    if not len(pos):
        return None
    raw = spool._read_cell(level, int(idx.offset[pos[0]]), int(idx.length[pos[0]]))
    return hashlib.sha256(raw).hexdigest()


# ---- C cross-check: production bg_shape (read-only include of _cenc.c) ----

PROBE_C = """/* plan-14 2-02 scratch probe: read-only include of production _cenc.c */
#include "%s"
int64_t p14_bg_shape(const double *lat, const double *lon, int64_t nc, int closed,
                     int64_t mc, int64_t tc, int64_t fl, const double *b4,
                     double cr, uint8_t *out, int64_t room, int64_t *nrec) {
    return kw__bg_shape(lat, lon, nc, closed, mc, tc, fl, b4, NULL, cr, out, room, nrec);
}
"""


class CProbe:
    """Compile scratch probe from parser/kiwiw/_cenc.c (no edit) and call bg_shape."""

    def __init__(self, scratch: Path):
        import ctypes
        import subprocess
        src = ROOT / "parser/kiwiw/_cenc.c"
        scratch.mkdir(parents=True, exist_ok=True)
        c = scratch / "probe_bg.c"
        so = scratch / "probe_bg.so"
        c.write_text(PROBE_C % src)
        cmd = ["gcc", "-O2", "-ffp-contract=off", "-fPIC", "-shared",
               "-I", str(src.parent), str(c), "-lm", "-o", str(so)]
        subprocess.run(cmd, check=True)
        self.cenc_sha = digest(src)
        self.cmd = cmd
        self.lib = ctypes.CDLL(str(so))
        f = self.lib.p14_bg_shape
        D = ctypes.POINTER(ctypes.c_double)
        f.argtypes = [D, D, ctypes.c_int64, ctypes.c_int, ctypes.c_int64, ctypes.c_int64,
                      ctypes.c_int64, D, ctypes.c_double, ctypes.c_char_p, ctypes.c_int64,
                      ctypes.POINTER(ctypes.c_int64)]
        f.restype = ctypes.c_int64
        self.f = f
        self.ct = ctypes

    def run(self, lat, lon, mc, tc, fl, b4, cr=4096.0):
        ct = self.ct
        lat = np.ascontiguousarray(lat, np.float64)
        lon = np.ascontiguousarray(lon, np.float64)
        b = np.ascontiguousarray(b4, np.float64)
        room = 1 << 20
        out = ct.create_string_buffer(room)
        nrec = ct.c_int64(0)
        D = ct.POINTER(ct.c_double)
        r = self.f(lat.ctypes.data_as(D), lon.ctypes.data_as(D), len(lat), 1,
                   int(mc), int(tc), int(fl), b.ctypes.data_as(D), cr, out, room,
                   ct.byref(nrec))
        return int(r), int(nrec.value)


def source_attrs(spool, level, source_cell, ordinal):
    """Raw degrees + (mult, type, flags) of one spool background record."""
    from kiwiw.spool import decode_columns
    ix, iy = int(source_cell[1]), int(source_cell[2])
    idx = spool._load_idx(level)
    pos = np.nonzero((idx.ix == ix) & (idx.iy == iy))[0]
    cols = decode_columns(spool._read_cell(level, int(idx.offset[pos[0]]),
                                           int(idx.length[pos[0]])))
    n = cols["b_nstored"].astype(np.int64)
    off = np.r_[0, np.cumsum(n)]
    a, b = int(off[ordinal]), int(off[ordinal + 1])
    return (np.array(cols["c_lat"][a:b], np.float64), np.array(cols["c_lon"][a:b], np.float64),
            int(cols["b_mult"][ordinal]), int(cols["b_type"][ordinal]),
            int(cols["b_flags"][ordinal]), int(cols["b_class"][ordinal]))


def cell_b4(lat: "Lattice", ix: int, iy: int):
    """(lat_lo, lat_hi, lon_lo, lon_hi) of an L0 cell on the same lattice as gx/gy."""
    lat_lo = lat.lat0 + iy * lat.cell_lat
    lon_lo = lat.lon0 + ix * lat.cell_lon
    return [lat_lo, lat_lo + lat.cell_lat, lon_lo, lon_lo + lat.cell_lon]


def process_seed(r, spool, lat, proofs_dir, keep_coords: bool, cprobe=None):
    level = int(r["level"]); ix = int(r["ix"]); iy = int(r["iy"])
    dump_row = int(r["dump_row"])
    req = json.loads((ROOT / r["spool_K1_requirement_witness"]).read_text())
    src = req.get("source")
    base = {
        "dump_row": dump_row,
        "native_key": {k: int(r[k]) for k in NATIVE},
        "in_historic_188": int(r["in_historic_188"]),
        "in_added_89": int(r["in_added_89"]),
        "spool_requirement_witness": r["spool_K1_requirement_witness"],
    }

    def finish(fields, member, proof):
        path = proofs_dir / f"{dump_row}.json"
        path.write_text(json.dumps(proof, sort_keys=True, indent=1) + "\n")
        fields = dict(fields)
        fields["proof_path"] = str(path.relative_to(ROOT) if path.is_relative_to(ROOT)
                                   else path)
        return {"fields": fields, "member": member}

    if src is None:
        return finish(
            {"spool_source_branch": None, "spool_source_cell": None,
             "spool_source_ncoord": None, "source_n_crossings": None,
             "n_eo_faces": 0, "n_faces_clipped": 0, "n_faces_emit": 0,
             "max_clipped_area2": 0, "any_encoder_emits": False,
             "c_records_original": None, "c_records_repaired": None,
             "mechanism": "no_source", "membership": "2-03-open-no-source"},
            False,
            {**base, "error": "no_source", "mechanism": "no_source",
             "membership": "2-03-open-no-source"},
        )

    got = source_cell_sha(spool, level, src["source_cell"])
    if got != src.get("source_cell_sha256"):
        raise SystemExit(
            f"spool source cell sha mismatch for dump_row {dump_row}: "
            f"{got} != witness {src.get('source_cell_sha256')} (fail closed)")
    arrs = spool_source_shape(spool, lat, level, src["source_cell"],
                              src["background_ordinal"])
    if arrs is None:
        return finish(
            {"spool_source_branch": src.get("branch"),
             "spool_source_cell": src.get("source_cell"),
             "spool_source_ncoord": src.get("n_coords"),
             "source_n_crossings": None, "n_eo_faces": 0,
             "n_faces_clipped": 0, "n_faces_emit": 0,
             "max_clipped_area2": 0, "any_encoder_emits": False,
             "c_records_original": None, "c_records_repaired": None,
             "mechanism": "spool_cell_missing",
             "membership": "2-03-open-spool-gap"},
            False,
            {**base, "error": "spool_cell_missing", "source": src,
             "mechanism": "spool_cell_missing",
             "membership": "2-03-open-spool-gap"},
        )

    xs, ys = arrs
    poly = list(zip(xs.tolist(), ys.tolist()))
    n_cross = count_crossings(poly)
    faces = decompose_eo_faces(poly)

    face_results = []
    n_emit = 0
    n_emit_nodensify = 0
    max_a2 = 0
    n_clipped = 0
    n_faces = len(faces)
    for fi, face in enumerate(faces):
        cl = clip_rect(face, ix * RAW, iy * RAW, (ix + 1) * RAW, (iy + 1) * RAW)
        q0, a0, emits_nodens = encoder_piece(cl)
        q, area2, emits = encoder_piece_densified(cl)
        if cl:
            n_clipped += 1
        if emits_nodens:
            n_emit_nodensify += 1
        if emits:
            n_emit += 1
        if abs(area2) > abs(max_a2):
            max_a2 = area2
        entry = {"face_index": fi, "n_verts": len(face), "clipped_n": len(cl),
                 "q": q, "area2": area2, "emits": emits,
                 "nodensify_q": q0, "nodensify_area2": a0,
                 "nodensify_emits": emits_nodens}
        if keep_coords:
            entry["face_coords"] = face
            entry["clipped_coords"] = cl
        face_results.append(entry)

    c_orig_records = None
    c_face_records = None
    c_class = None
    if cprobe is not None:
        slat, slon, mc, tc, fl, c_class = source_attrs(spool, level, src["source_cell"],
                                                       src["background_ordinal"])
        b4 = cell_b4(lat, ix, iy)
        r0, n0 = cprobe.run(slat, slon, mc, tc, fl, b4)
        if r0 < 0:
            raise SystemExit(f"C bg_shape error {r0} on dump_row {dump_row} (fail closed)")
        c_orig_records = n0
        c_face_records = 0
        for face in faces:
            fx = np.array([v[0] for v in face]); fy = np.array([v[1] for v in face])
            flon = lat.lon0 + fx / RAW * lat.cell_lon
            flat = lat.lat0 + fy / RAW * lat.cell_lat
            rf, nf = cprobe.run(flat, flon, mc, tc, fl, b4)
            if rf < 0:
                raise SystemExit(f"C bg_shape error {rf} on face of {dump_row}")
            c_face_records += nf

    any_emit = n_emit > 0 or bool(c_orig_records) or bool(c_face_records)
    member = not any_emit
    mechanism = ("complete_repair_zero_representable" if member
                 else "complete_repair_emits")
    membership = "2-02-member" if member else "2-03-open-repair-emits"

    proof = {
        **base,
        "source": {
            "branch": src["branch"],
            "source_cell": src["source_cell"],
            "background_ordinal": src["background_ordinal"],
            "n_coords": src["n_coords"],
            "bbox_global_raw": src.get("bbox_global_raw"),
            "source_cell_sha256": src.get("source_cell_sha256"),
        },
        "source_n_crossings": n_cross,
        "n_eo_faces": n_faces,
        "faces": face_results,
        "n_faces_emit": n_emit,
        "max_clipped_area2": max_a2,
        "any_encoder_emits": any_emit,
        "c_source_class": c_class,
        "c_bg_shape_records_original": c_orig_records,
        "c_bg_shape_records_repaired_faces": c_face_records,
        "python_mirror_faces_emit": n_emit,
        "python_mirror_nodensify_faces_emit": n_emit_nodensify,
        "mechanism": mechanism,
        "membership": membership,
    }
    result = finish(
        {"spool_source_branch": src["branch"],
         "spool_source_cell": src["source_cell"],
         "spool_source_ncoord": src["n_coords"],
         "source_n_crossings": n_cross,
         "n_eo_faces": n_faces,
         "n_faces_clipped": n_clipped,
         "n_faces_emit": n_emit,
         "max_clipped_area2": max_a2,
         "any_encoder_emits": any_emit,
         "c_records_original": c_orig_records,
         "c_records_repaired": c_face_records,
         "mechanism": mechanism,
         "membership": membership},
        member,
        proof,
    )
    del poly, faces, face_results, proof, xs, ys
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-seeds", type=int, default=None)
    ap.add_argument("--seed-offset", type=int, default=0)
    ap.add_argument("--all-seeds", action="store_true")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--keep-proof-coords", action="store_true")
    ap.add_argument("--proofs-dir", type=Path, default=None)
    ap.add_argument("--skip-positive-control", action="store_true")
    ap.add_argument("--no-c-probe", action="store_true",
                    help="Skip production C bg_shape cross-check (Python mirror only)")
    args = ap.parse_args(argv)

    gdisc = G_DISC / "ALLDATA.KWI"
    assert digest(gdisc) == G_SHA, "G disc sha mismatch"
    assert_no_whole_file(SPOOL, gdisc)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    proofs_dir = Path(args.proofs_dir) if args.proofs_dir else PROOFS
    proofs_dir = proofs_dir.resolve() if proofs_dir.is_absolute() else (ROOT / proofs_dir).resolve()
    proofs_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_positive_control:
        ctrl = positive_control()
        (SCRATCH / "positive_control.json").write_text(
            json.dumps(ctrl, sort_keys=True, indent=2) + "\n")
        if not ctrl["pass"]:
            raise SystemExit(f"positive control FAILED: {ctrl}")

    rows = list(csv.DictReader(EVIDENCE.open(), delimiter="\t"))
    seeds_all = [r for r in rows
                 if int(r["R_polygon_count"]) == 0 and int(r["dump_row"]) != 335]
    assert len(rows) == 776 and len(seeds_all) == 432, (len(rows), len(seeds_all))

    if args.all_seeds:
        if args.max_seeds is not None:
            ap.error("pass only one of --all-seeds / --max-seeds")
        seeds = seeds_all[args.seed_offset:]
    else:
        if args.max_seeds is None:
            raise SystemExit(
                "plan25: refuse uncapped complete_repair run — pass --max-seeds N "
                "or explicit --all-seeds (see docs/plans/25-oom-memory-rca/)"
            )
        if args.max_seeds < 1:
            ap.error("--max-seeds must be >= 1")
        seeds = seeds_all[args.seed_offset: args.seed_offset + args.max_seeds]
    if not seeds:
        raise SystemExit("plan25: empty seed window")

    lat = Lattice(0)
    spool = SpoolReader(SPOOL)
    cprobe = None if args.no_c_probe else CProbe(SCRATCH / "cprobe")
    c_ctrl = None
    if cprobe is not None:
        # C positive control: in-cell square on an AU cell (1706,1512) must emit
        b4 = cell_b4(lat, 1706, 1512)
        fx = np.array([512.0, 3584.0, 3584.0, 512.0]) + 1706 * RAW
        fy = np.array([512.0, 512.0, 3584.0, 3584.0]) + 1512 * RAW
        r0, n0 = cprobe.run(lat.lat0 + fy / RAW * lat.cell_lat,
                            lat.lon0 + fx / RAW * lat.cell_lon, 1, 288, 0, b4)
        c_ctrl = {"bytes": r0, "records": n0, "pass": r0 > 0 and n0 >= 1,
                  "cenc_sha256": cprobe.cenc_sha, "compile": cprobe.cmd}
        (SCRATCH / "c_positive_control.json").write_text(
            json.dumps(c_ctrl, sort_keys=True, indent=2) + "\n")
        if not c_ctrl["pass"]:
            raise SystemExit(f"C positive control FAILED: {c_ctrl}")

    members, rejects = [], []
    hist = {"historic": 0, "added": 0, "neither": 0}
    mech_hist = {}
    cross_hist = {"zero": 0, "nonzero": 0}

    for i, r in enumerate(seeds):
        out = process_seed(r, spool, lat, proofs_dir, args.keep_proof_coords, cprobe)
        f = out["fields"]
        row_out = [int(r[k]) for k in NATIVE] + [
            int(r["dump_row"]), int(r["in_historic_188"]), int(r["in_added_89"]),
            int(r["R_polygon_count"]), int(r["G_polygon_count"]),
            f["spool_source_branch"], f["spool_source_cell"], f["spool_source_ncoord"],
            f["source_n_crossings"], f["n_eo_faces"], f["n_faces_clipped"],
            f["n_faces_emit"], f["max_clipped_area2"], f["c_records_original"],
            f["c_records_repaired"], f["any_encoder_emits"],
            f["mechanism"], f["membership"], f["proof_path"],
        ]
        (members if out["member"] else rejects).append(row_out)
        if int(r["in_historic_188"]):
            hist["historic"] += 1
        elif int(r["in_added_89"]):
            hist["added"] += 1
        else:
            hist["neither"] += 1
        mech_hist[f["mechanism"]] = mech_hist.get(f["mechanism"], 0) + 1
        if f["source_n_crossings"]:
            cross_hist["nonzero"] += 1
        else:
            cross_hist["zero"] += 1
        if (i + 1) % max(1, args.batch_size) == 0:
            gc.collect()

    def write_tsv(path, data):
        with path.open("w", newline="") as fh:
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            w.writerow(MEMBERSHIP_HEADER)
            w.writerows(data)

    if args.all_seeds:
        write_tsv(TRIAGE / "2-02_r-absent-complete-repair-zero_members.tsv", members)
        write_tsv(TRIAGE / "2-02_r-absent-complete-repair-zero_rejects.tsv", rejects)
    else:
        probe = SCRATCH / "windowed"
        probe.mkdir(parents=True, exist_ok=True)
        write_tsv(probe / f"members_offset{args.seed_offset}_n{len(seeds)}.tsv", members)
        write_tsv(probe / f"rejects_offset{args.seed_offset}_n{len(seeds)}.tsv", rejects)

    summary = {
        "seeds": len(seeds),
        "seeds_available": len(seeds_all),
        "seed_offset": args.seed_offset,
        "max_seeds": args.max_seeds,
        "all_seeds": bool(args.all_seeds),
        "plan25_memory_bounds": True,
        "members_2_02": len(members),
        "rejects_2_03_repair_emits_or_gap": len(rejects),
        "seed_set_histogram": hist,
        "mechanism_histogram": mech_hist,
        "crossing_histogram": cross_hist,
        "expected_completeness_movement": len(members),
        "disc": {"G_sha256": G_SHA, "spool": str(SPOOL)},
        "positive_control": (
            json.loads((SCRATCH / "positive_control.json").read_text())
            if (SCRATCH / "positive_control.json").exists() else None
        ),
        "rejects_dump_rows": [x[13] for x in rejects],
        "c_positive_control": c_ctrl,
        "c_records_original_nonzero": sum(1 for x in members + rejects
                                          if x[MEMBERSHIP_HEADER.index("c_records_original")]),
        "c_records_repaired_nonzero": sum(1 for x in members + rejects
                                          if x[MEMBERSHIP_HEADER.index("c_records_repaired")]),
        "python_mirror_emit_rows": sum(1 for x in members + rejects
                                       if x[MEMBERSHIP_HEADER.index("n_faces_emit")]),
        "added_89_cite_3_16": (
            "3-16 outcomes TSV excludes EO-stitch face-bypass recovery for "
            "added_89 (0/89 pass); complete-repair zero-emit is the positive "
            "close for this group"
        ),
    }
    (SCRATCH / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True, indent=2))
    spool.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(None))
