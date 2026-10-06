"""Plan 38 Phase 1: row-246 witness (L0 (834,886), type 321).

Light and bounded: one R leaf-slot decode (bounded pread through RReader /
LeafIndex), the same slot on the oracle disc (G control), and one spool cell
pread by the recorded offset/length. No whole-file reads.

Writes witness/row246_witness.json (committed).

Match predicate (DESIGN Contract 4, fixed before measuring):
  R's record matches the demander iff
    (i)  every R vertex lies within 1 raw unit of the demander's clipped
         in-cell geometry (its clip-ring segments, unrounded) or of the cell
         edge segment it touches (implemented as the nearest of the four cell
         lines: looser than DESIGN, so it can only add matches); and
    (ii) R's ring area2 has the clip's sign and magnitude: same sign (0 counts
         as its own sign) and |A_R - A_clip| <= 2 * perimeter_R (a first-order
         bound on how far a 1-unit vertex band moves area2). The clip ring is
         oriented positive first, as bg_shape does.
  Otherwise no match; the nearest alternative among the R polygons and the
  spool's type-321 features near the cell is named (Hausdorff, cell units).
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "parser").is_dir() and (p / "docs").is_dir())
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]

from harness import walk  # noqa: E402
from kiwiw import cbuild  # noqa: E402
from kiwiw.coordconv import decode_region_coord  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402
from kiwiw.spool import SpoolReader, decode_columns  # noqa: E402
from overlay_test import RReader  # noqa: E402
from r_neighbours import LeafIndex  # noqa: E402
from quantisation_roundtrip import Lattice, RAW  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "cell_local", ROOT / "docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py")
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)

R_DISC = Path("/run/media/codyh/464210-8480")
G_DISC = ROOT / "output/scratch-34/G_new"           # oracle 4e6b0de7 (protected)
G_SHA = "4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448"
SPOOL = ROOT / "output/extract_timing/spool"
IX, IY, CODE = 834, 886, 321
SRC_CELL, ORD, SOFF, SLEN = (834, 885), 15, 2806410336, 34248
OUT = HERE / "row246_witness.json"


def slot_records(reader, index, ix, iy):
    """Every background record in the leaf slot of (ix, iy), with leaf buffers."""
    slot = index.get(ix, iy)
    recs = []
    leaves = []
    for (lmr, blk, leaf_row) in slot.handles:
        lpath, le, lb, ptype, _, (fb, fc) = leaf_row
        frng = walk.leaf_frame_range(0, ptype, lpath, fc)
        fbr = walk.with_range(fb, frng)
        off = reader.volume.getsector(le.dsa, reader.ss, reader.ls)
        length = le.size * reader.ls
        reader.fh.seek(off)
        buf = reader.fh.read(length)
        loc = MeshLocation(level=0, parcel_type=ptype, blockset_index=blk[1], block_index=blk[2],
                           parcel_index=lpath[-1], bounds=fbr, sector_addr=le.dsa,
                           size_logical_sectors=le.size)
        parcel = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
        bg = parcel.background
        leaves.append({"leaf_path": list(lpath), "file_offset": off, "length": length,
                       "sha256": hashlib.sha256(buf).hexdigest(),
                       "bg_units": [] if not bg else [
                           {"unit_table_raw": [list(map(int, u)) for u in e.unit_table_raw]}
                           for e in bg.elements if e.unit_table_raw]})
        for s in (bg.shapes if bg else []):
            recs.append((list(lpath), off, buf, s))
    return slot.status, recs, leaves


def frame_raw_coords(rb: bytes):
    """Frame-local raw lattice coords from a record's bytes (background.py layout)."""
    flag = int.from_bytes(rb[2:4], "big")
    addl = int.from_bytes(rb[6:8], "big")
    n = flag & 0x7FF
    mult = 1 << (addl & 7)
    x = decode_region_coord(int.from_bytes(rb[8:10], "big"))
    y = decode_region_coord(int.from_bytes(rb[10:12], "big"))
    out = [(x, y)]
    for k in range(n):
        dx = int.from_bytes(rb[12 + 2 * k:13 + 2 * k], "big", signed=True)
        dy = int.from_bytes(rb[13 + 2 * k:14 + 2 * k], "big", signed=True)
        x += dx * mult
        y += dy * mult
        out.append((x, y))
    return out, mult


def area2(pts):
    n = len(pts)
    return float(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                     for i in range(n)))


def perimeter(pts):
    n = len(pts)
    return sum(math.dist(pts[i], pts[(i + 1) % n]) for i in range(n))


def seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def dist_to_ring(p, ring):
    if not ring:
        return math.inf
    if len(ring) == 1:
        return math.dist(p, ring[0])
    return min(seg_dist(p, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring)))


def dist_to_edge(p):
    x, y = p
    return min(abs(x), abs(x - RAW), abs(y), abs(y - RAW)) if (
        -1 <= x <= RAW + 1 and -1 <= y <= RAW + 1) else math.inf


def hausdorff(a, b):
    if not a or not b:
        return math.inf
    return max(max(dist_to_ring(p, b) for p in a), max(dist_to_ring(p, a) for p in b))


def contacts(pts, tol=0.5):
    out = []
    for i, (x, y) in enumerate(pts):
        e = [n for n, v in (("x=0", abs(x)), ("x=4096", abs(x - RAW)), ("y=0", abs(y)),
                            ("y=4096", abs(y - RAW))) if v <= tol]
        if e:
            out.append({"vertex": i, "edges": e, "xy": [round(x, 3), round(y, 3)]})
    return out


def describe(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    rp = [(round(x), round(y)) for x, y in pts]
    return {"n": len(pts), "bbox_cell_raw": [round(min(xs), 3), round(max(xs), 3),
                                             round(min(ys), 3), round(max(ys), 3)],
            "area2": round(area2(pts), 3), "area2_rint": area2(rp),
            "closed_first_eq_last": rp[0] == rp[-1], "edge_contacts": contacts(pts),
            "n_edge_contacts": len(contacts(pts))}


def build_probe():
    d = Path(tempfile.mkdtemp(prefix="p38probe"))
    so = d / "probe246.so"
    subprocess.run([cbuild._find_cc(), *cbuild.CFLAGS, "-shared", f"-I{ROOT}", str(HERE / "probe246.c"), "-lm",
                    "-o", str(so)], check=True)
    lib = ctypes.CDLL(str(so))
    fn = lib.probe246
    fn.restype = ctypes.c_int64
    fn.argtypes = [ctypes.c_void_p] * 2 + [ctypes.c_int64] * 4 + [ctypes.c_void_p] * 2 + [
        ctypes.c_int64, ctypes.c_void_p]
    return fn


def raw_polygons(blob):
    out = []
    pos = 0
    while pos < len(blob):
        size = (int.from_bytes(blob[pos:pos + 2], "big") & 4095) * 2
        pts, _ = frame_raw_coords(blob[pos:pos + size])
        out.append({"hex": blob[pos:pos + size].hex(), "pts": pts})
        pos += size
    return out


def main():
    lat = Lattice(0)
    res = {"cell": [0, IX, IY], "code": CODE, "predicate": __doc__.split("Match predicate")[1].strip()}

    # 1. R record decode
    rr = RReader(str(R_DISC))
    st, recs, leaves = slot_records(rr, LeafIndex(rr, 0), IX, IY)
    r321 = []
    for lpath, off, buf, s in recs:
        if s.shape_class != 2 or s.type_code != CODE or len(s.coords) < 3:
            continue
        xs = [float(lat.gx(c[1])) - IX * RAW for c in s.coords]
        ys = [float(lat.gy(c[0])) - IY * RAW for c in s.coords]
        pts = list(zip(xs, ys))
        fr, mult = frame_raw_coords(s.raw_bytes)
        idx = buf.find(s.raw_bytes)
        meet = cl.r_meet_branches([x + IX * RAW for x in xs], [y + IY * RAW for y in ys], CODE, IX, IY)
        r321.append({"leaf_path": lpath, "record_frame_offset": s.raw_offset,
                     "record_file_offset": off + idx if idx >= 0 else None,
                     "record_bytes_hex": s.raw_bytes.hex(),
                     "record_sha256": hashlib.sha256(s.raw_bytes).hexdigest(),
                     "header_words": [int.from_bytes(s.raw_bytes[k:k + 2], "big") for k in range(0, 12, 2)],
                     "mult": mult, "frame_raw": fr,
                     "cell_raw": [[round(x, 3), round(y, 3)] for x, y in pts],
                     "latlon_bbox": [min(c[0] for c in s.coords), max(c[0] for c in s.coords),
                                     min(c[1] for c in s.coords), max(c[1] for c in s.coords)],
                     "meet_branches": [h["branch"] for h in meet], **describe(pts)})
    local = [r for r in r321 if "a" in r["meet_branches"]]
    res["R"] = {"disc": str(R_DISC / "ALLDATA.KWI"), "slot_status": st, "leaves": leaves,
                "n_type321": len(r321), "n_cell_local": len(local), "type321": r321}

    # 2. G control on the oracle
    gr = RReader(str(G_DISC))
    gst, grecs, gleaves = slot_records(gr, LeafIndex(gr, 0), IX, IY)
    hist = {}
    grec_list = []
    rloc = [r for r in r321 if "a" in r["meet_branches"]]
    rc = None
    if rloc:
        pts = rloc[0]["cell_raw"]
        rc = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    for _, _, _, s in grecs:
        k = f"class{s.shape_class}:code{s.type_code}"
        hist[k] = hist.get(k, 0) + 1
        gp = [(float(lat.gx(c[1])) - IX * RAW, float(lat.gy(c[0])) - IY * RAW) for c in s.coords]
        full = len(gp) >= 4 and all(min(abs(x), abs(x - RAW)) <= 0.5 and min(abs(y), abs(y - RAW)) <= 0.5 for x, y in gp)
        grec_list.append({"class": s.shape_class, "code": s.type_code, "n": len(gp),
                          "cell_raw": [[round(x, 2), round(y, 2)] for x, y in gp], "full_cell_rect": full,
                          "contains_R_centroid": bool(rc and s.shape_class == 2 and len(gp) >= 3 and
                                                      cl.point_in_poly(rc[0], rc[1], [q[0] for q in gp], [q[1] for q in gp]))})
    res["G"] = {"disc": str(G_DISC / "ALLDATA.KWI"), "expected_sha256": G_SHA,
                "sha_source": "output/scratch-41/bench/protected_before.json (phase2_gates snapshot)",
                "slot_status": gst, "leaves": gleaves, "records_by_class_code": dict(sorted(hist.items())),
                "records": grec_list, "R_centroid_cell_raw": rc,
                "n_type321": sum(v for k, v in hist.items() if k.endswith(f"code{CODE}"))}

    # 3. Spool demander and neighbourhood type-321 features
    sp = SpoolReader(SPOOL)
    idx = sp._load_idx(0)
    probe = build_probe()
    rect = np.array([0, 0, RAW, RAW], "f8")

    def feature(cols, o, cell):
        n = cols["b_nstored"].astype(np.int64)
        offs = np.r_[0, np.cumsum(n)]
        a, b = int(offs[o]), int(offs[o + 1])
        x = (lat.gx(cols["c_lon"][a:b]) - IX * RAW).astype("f8")
        y = (lat.gy(cols["c_lat"][a:b]) - IY * RAW).astype("f8")
        poly = list(zip(x.tolist(), y.tolist()))
        if int(cols["b_class"][o]) == 2 and len(poly) >= 3 and area2(poly) < 0:
            poly = poly[::-1]  # bg_shape orients closed rings positive before clipping (_cenc.c bg_shape)
        clip = cl.clip_rect(poly, 0, 0, RAW, RAW)
        q, a2, emits = cl.encoder_piece(clip)
        out = np.zeros(65536, "u1"); nr = ctypes.c_int64()
        size = probe(np.ascontiguousarray(y).ctypes.data, np.ascontiguousarray(x).ctypes.data, len(x),
                     int(cols["b_mult"][o]), int(cols["b_type"][o]), int(cols["b_flags"][o]),
                     rect.ctypes.data, out.ctypes.data, len(out), ctypes.byref(nr))
        prod = raw_polygons(out[:max(0, size)].tobytes()) if size > 0 else []
        lo = np.r_[0, np.cumsum(cols["b_label_len"].astype(np.int64))]
        label = bytes(cols["blob_bg_label"][lo[o]:lo[o + 1]]).decode("utf-8", "replace")
        return {"source_cell": list(cell), "ordinal": o, "class": int(cols["b_class"][o]),
                "type": int(cols["b_type"][o]), "mult": int(cols["b_mult"][o]),
                "flags": int(cols["b_flags"][o]), "label": label, "n_coords": len(poly),
                "bbox_cell_raw": [round(min(x), 3), round(max(x), 3), round(min(y), 3), round(max(y), 3)],
                "python_clip": {"n": len(clip), "clip": [[round(u, 3), round(v, 3)] for u, v in clip],
                                "area2": round(area2(clip), 3) if clip else 0.0,
                                "q": q, "area2_rint": a2, "emits": emits},
                "production_bg_shape": {"return": int(size), "nrec": int(nr.value),
                                        "records": [{"hex": p["hex"], "pts": p["pts"],
                                                     "area2": area2(p["pts"])} for p in prod]},
                "_clip": clip}

    pos = np.nonzero((idx.ix == SRC_CELL[0]) & (idx.iy == SRC_CELL[1]))[0]
    assert int(idx.offset[pos[0]]) == SOFF and int(idx.length[pos[0]]) == SLEN, "spool idx moved"
    blob = sp._read_cell(0, SOFF, SLEN)
    dem = feature(decode_columns(blob), ORD, SRC_CELL)
    dem["spool_cell_sha256"] = hashlib.sha256(blob).hexdigest()
    dem["osm_id_recorded"] = False  # bg columns carry no OSM id (Open question 1: geometry only)
    res["demander"] = dem

    neigh = []
    for cx in range(IX - 2, IX + 3):
        for cy in range(IY - 2, IY + 3):
            p = np.nonzero((idx.ix == cx) & (idx.iy == cy))[0]
            if not len(p):
                continue
            cols = decode_columns(sp._read_cell(0, int(idx.offset[p[0]]), int(idx.length[p[0]])))
            for o in np.nonzero(cols["b_type"] == CODE)[0]:
                f = feature(cols, int(o), (cx, cy))
                if f["python_clip"]["n"] or f["production_bg_shape"]["nrec"]:
                    neigh.append(f)
    res["spool_321_reaching_cell"] = [{k: v for k, v in f.items() if k != "_clip"} for f in neigh]
    anyt = []
    for cx in range(IX - 2, IX + 3):
        for cy in range(IY - 2, IY + 3):
            p = np.nonzero((idx.ix == cx) & (idx.iy == cy))[0]
            if not len(p):
                continue
            cols = decode_columns(sp._read_cell(0, int(idx.offset[p[0]]), int(idx.length[p[0]])))
            n = cols["b_nstored"].astype(np.int64); offs = np.r_[0, np.cumsum(n)]
            lo = np.r_[0, np.cumsum(cols["b_label_len"].astype(np.int64))]
            for o in range(len(n)):
                a, b = int(offs[o]), int(offs[o + 1])
                if b - a < 1 or int(cols["b_class"][o]) != 2:
                    continue
                x = (lat.gx(cols["c_lon"][a:b]) - IX * RAW).tolist(); y = (lat.gy(cols["c_lat"][a:b]) - IY * RAW).tolist()
                clip = cl.clip_rect(list(zip(x, y)), 0, 0, RAW, RAW)
                if not clip:
                    continue
                anyt.append({"source_cell": [cx, cy], "ordinal": o, "type": int(cols["b_type"][o]),
                             "label": bytes(cols["blob_bg_label"][lo[o]:lo[o + 1]]).decode("utf-8", "replace"),
                             "n_coords": b - a, "clip_n": len(clip),
                             "contains_R_centroid": bool(rc and cl.point_in_poly(rc[0], rc[1], x, y)),
                             "min_dist_to_R_vertex": round(min(dist_to_ring(tuple(q), clip) for q in rloc[0]["cell_raw"]), 1) if rloc else None})
    res["spool_any_type_class2_reaching_cell_5x5"] = anyt

    # 4. Match predicate
    def match(r, f):
        pts = [tuple(p) for p in r["cell_raw"]]
        clip = f["_clip"]
        far = [i for i, p in enumerate(pts) if min(dist_to_ring(p, clip), dist_to_edge(p)) > 1.0]
        ar, ac = r["area2"], f["python_clip"]["area2"]
        sgn = (ar > 0) - (ar < 0) == (ac > 0) - (ac < 0)
        mag = abs(ar - ac) <= 2 * perimeter(pts)
        return {"vertices_beyond_1u": len(far), "first_far": far[:5], "area2_R": ar, "area2_clip": ac,
                "sign_ok": sgn, "magnitude_ok": mag, "match": not far and sgn and mag,
                "hausdorff_cell_raw": round(hausdorff(pts, clip), 3) if clip else None}

    res["match"] = []
    for r in local:
        m = match(r, dem)
        alts = sorted(({"source_cell": f["source_cell"], "ordinal": f["ordinal"], **match(r, f)}
                       for f in neigh), key=lambda a: (not a["match"], a["hausdorff_cell_raw"] or 1e18))
        res["match"].append({"R_leaf_path": r["leaf_path"], "R_record_sha256": r["record_sha256"],
                             "vs_demander": m, "alternatives_ranked": alts[:10]})
    for r in res["R"]["type321"]:
        r["frame_raw"] = [list(map(int, p)) for p in r["frame_raw"]]
    for f in [dem] + neigh:
        f.pop("_clip", None)
    OUT.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"R_n321": len(r321), "R_local": len(local), "G_n321": res["G"]["n_type321"],
                      "demander_clip": dem["python_clip"]["q"], "prod_nrec": dem["production_bg_shape"]["nrec"],
                      "neigh": len(neigh), "match": [m["vs_demander"] for m in res["match"]]}, indent=1))


if __name__ == "__main__":
    main()
