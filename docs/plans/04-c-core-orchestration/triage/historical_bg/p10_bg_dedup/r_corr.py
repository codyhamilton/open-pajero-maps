#!/usr/bin/env python3
"""Plan 68 Phase 1: R correspondence of duplicate classes (definitions committed in sample.json).

For each class (sample rows, or --all: every census row): decode G's leaf (live disc) and every R leaf of
the same cell through one reader (plan 48: overlay_test.RReader + r_neighbours.LeafIndex + decode_parcel,
as trim_witness.r_parent; parent-raw coordinates of the cell, 4096 raw / cell), wire bytes via plan 63's
leaf_all_records. Classify per sample.json "classes" (first match in this order): R-noncomparable(alias),
R-one-byte, R-one-geom, R-merged, R-noncomparable(type-set), R-absent, R-other. Position per "position".
numpy only (even-odd point-in-polygon on a sample grid; 1 parent-raw unit tolerance)."""
from __future__ import annotations

import argparse, csv, gzip, hashlib, io, json, os, sys, time
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
TRI = ROOT / "docs/plans/04-c-core-orchestration/triage"
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"), str(TRI / "trim_r_parity"),
                str(TRI / "historical_bg/p7_producer_tie"), str(TRI / "historical_bg/p5_owner_exclusive"),
                str(Path(__file__).resolve().parent)]
from trim_witness import RReader, LeafIndex, Lattice, RAW, seg_dist, segs  # noqa: E402
from kiwiw.model import MeshLocation  # noqa: E402
from kiwiw.parcel import decode_parcel  # noqa: E402
from provenance import leaf_all_records  # noqa: E402
import leaf_io as L  # noqa: E402
from kiwiw import volume  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402

R_DISC = "/run/media/codyh/464210-8480"
FNV = []  # set in main (plan 63 load_fnv)
RALIAS = {}
TOL = 1.0
NGRID = 96


def alias_dsas(path, level):
    """frame addresses used by more than one leaf slot of `level`."""
    oc = L.oc; cnt = Counter()
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            if lm.level != level:
                continue
            for block in table.entries:
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for _x, _y, _leaf, entry in oc.tree_leaves(root, lm):
                    cnt[entry.dsa] += 1
    return {d for d, n in cnt.items() if n > 1}


class Disc:
    def __init__(self, ref, cache=256):
        self.rr = RReader(ref); self.idx = {}; self.cache = OrderedDict(); self.cmax = cache

    def cell(self, level, ix, iy):
        k = (level, ix, iy)
        if k in self.cache:
            self.cache.move_to_end(k); return self.cache[k]
        if level not in self.idx:
            self.idx[level] = LeafIndex(self.rr, level)
        v = read_cell(self.rr, self.idx[level], level, ix, iy, Lattice(level))
        self.cache[k] = v
        if len(self.cache) > self.cmax:
            self.cache.popitem(last=False)
        return v


def read_cell(rr, idx, level, ix, iy, lat):
    nb = idx.get(ix, iy)
    leaves = []
    for (lmr, blk, leaf_row) in nb.handles:
        lpath, le, lb, ptype, _, (fb, fc) = leaf_row
        frng = rr.walk.leaf_frame_range(level, ptype, lpath, fc)
        fbr = rr.walk.with_range(fb, frng)
        off = rr.volume.getsector(le.dsa, rr.ss, rr.ls)
        rr.fh.seek(off); buf = rr.fh.read(le.size * rr.ls)
        loc = MeshLocation(level=level, parcel_type=ptype, blockset_index=blk[1], block_index=blk[2],
                           parcel_index=lpath[-1], bounds=fbr, sector_addr=le.dsa, size_logical_sectors=le.size)
        p = decode_parcel(loc, buf, n_basic_map=lmr.n_basic_map, n_ext_map=lmr.n_ext_map)
        cv = lambda la, lo: (float(lat.gx(lo)) - ix * RAW, float(lat.gy(la)) - iy * RAW)
        shapes = list(p.background.shapes) if p.background else []
        wires = leaf_all_records(buf)  # whole leaf entry: R's word 0 is not the frame length (r_census.py)
        recs = []
        if len(shapes) == len(wires):
            for (s, cls, code, w), sh in zip(wires, shapes):
                recs.append((s, cls, code, w, np.array([cv(a, o) for a, o in sh.coords], float).reshape(-1, 2)))
            ok = all(sh.type_code == r[2] for sh, r in zip(shapes, recs))
        else:
            ok = False
        frame = (round(fbr.lat_lo, 12), round(fbr.lat_hi, 12), round(fbr.lon_lo, 12), round(fbr.lon_hi, 12), frng)
        leaves.append({"path": tuple(lpath), "dsa": le.dsa, "frame": frame, "recs": recs, "aligned": ok,
                       "ptype": ptype, "fnv": FNV[0](buf[:L.U16(buf, 0) * 2]) if FNV else None})
    return nb.status, leaves


# ---------------- geometry (numpy) ----------------
def open_ring(P):
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        return P[:-1]
    return P


def ring_equal(A, B, tol=TOL):
    A = open_ring(A); B = open_ring(B)
    if len(A) != len(B) or len(A) == 0:
        return False
    for BB in (B, B[::-1]):
        ks = np.nonzero(np.abs(BB - A[0]).max(1) <= tol)[0]
        for k in ks:
            if np.abs(np.roll(BB, -k, 0) - A).max() <= tol:
                return True
    return False


def pip(P, R):
    R = open_ring(R)
    if len(R) < 3:
        return np.zeros(len(P), bool)
    x, y = P[:, 0][:, None], P[:, 1][:, None]
    x1, y1 = R[:, 0][None], R[:, 1][None]
    x2, y2 = np.roll(R[:, 0], -1)[None], np.roll(R[:, 1], -1)[None]
    c = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / np.where(y2 != y1, y2 - y1, 1) + x1)
    return (c.sum(1) & 1).astype(bool)


def samples(R, n=NGRID):
    """grid sample points inside R (even-odd) and the area each represents."""
    R = open_ring(R)
    if len(R) < 3:
        return np.zeros((0, 2)), 0.0
    x0, y0 = R.min(0); x1, y1 = R.max(0)
    dx = max((x1 - x0) / n, 1e-9); dy = max((y1 - y0) / n, 1e-9)
    gx = x0 + (np.arange(n) + 0.5) * dx; gy = y0 + (np.arange(n) + 0.5) * dy
    G = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2)
    inside = np.zeros(len(G), bool)
    for s in range(0, len(G), 2048):
        inside[s:s + 2048] = pip(G[s:s + 2048], R)
    return G[inside], dx * dy


def rings_cross(A, B, chunk=256):
    """some edge of closed ring A properly or improperly intersects some edge of closed ring B."""
    a0 = A; a1 = np.roll(A, -1, 0); b0 = B; b1 = np.roll(B, -1, 0)
    bx0 = np.minimum(b0[:, 0], b1[:, 0]); bx1 = np.maximum(b0[:, 0], b1[:, 0])
    by0 = np.minimum(b0[:, 1], b1[:, 1]); by1 = np.maximum(b0[:, 1], b1[:, 1])

    def orient(p, q, r):
        return np.sign((q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0]))
    for s in range(0, len(A), chunk):
        p, q = a0[s:s + chunk, None, :], a1[s:s + chunk, None, :]
        m = ((np.maximum(p[..., 0], q[..., 0]) >= bx0[None]) & (np.minimum(p[..., 0], q[..., 0]) <= bx1[None]) &
             (np.maximum(p[..., 1], q[..., 1]) >= by0[None]) & (np.minimum(p[..., 1], q[..., 1]) <= by1[None]))
        if not m.any():
            continue
        r, u = b0[None], b1[None]
        d1, d2 = orient(p, q, r), orient(p, q, u); d3, d4 = orient(r, u, p), orient(r, u, q)
        if (m & (d1 * d2 <= 0) & (d3 * d4 <= 0)).any():
            return True
    return False


def near(A, B, tol=TOL):
    """distance(A ring, B ring) <= tol (edges cross, vertex-to-segment both ways, or one inside the other).
    Review fix (plan 68 Codex review 1): crossing rings whose vertices are all far from the other's edges
    (e.g. perpendicular rectangles) were missed; edge intersection is now tested first."""
    A = open_ring(A); B = open_ring(B)
    if len(A) == 0 or len(B) == 0:
        return False
    a0, a1 = A.min(0), A.max(0); b0, b1 = B.min(0), B.max(0)
    if (a0 > b1 + tol).any() or (b0 > a1 + tol).any():
        return False
    if pip(A[:1], B)[0] or pip(B[:1], A)[0]:
        return True
    if rings_cross(A, B):
        return True
    if seg_dist(A, segs(B, True)).min() <= tol or seg_dist(B, segs(A, True)).min() <= tol:
        return True
    return False


def covered_area(S, area_each, R):
    """area of sample set S (points inside some piece) that lies inside ring R."""
    if len(S) == 0:
        return 0.0
    R = open_ring(R)
    r0, r1 = R.min(0), R.max(0)
    m = (S[:, 0] >= r0[0]) & (S[:, 0] <= r1[0]) & (S[:, 1] >= r0[1]) & (S[:, 1] <= r1[1])
    if not m.any():
        return 0.0
    return float(pip(S[m], R).sum()) * area_each


def contains(R, piece_S, piece_ring, tol=TOL):
    """every sample point and vertex of the piece is inside R or within tol of R's boundary."""
    P = np.vstack([piece_S, open_ring(piece_ring)]) if len(piece_S) else open_ring(piece_ring)
    ins = pip(P, R)
    out = P[~ins]
    if len(out) == 0:
        return True
    return bool(seg_dist(out, segs(open_ring(R), True)).max() <= tol)


# ---------------- classification ----------------
def classify(row, G, Rd, ralias):
    """committed order: alias first; for alias rows the geometry class inside the shared frame is
    also recorded (geom_class), measured, never a pass."""
    res = classify_geom(row, G, Rd)
    if res.get("class") != "error" and res.get("_alias"):
        res = {**res, "geom_class": res["class"], "geom_sub": res.get("sub"), "class": "R-noncomparable", "sub": "alias"}
    res.pop("_alias", None)
    return res


def classify_geom(row, G, Rd):
    ralias = RALIAS[row["level"]]
    lv, ix, iy, path, code = row["level"], row["ix"], row["iy"], tuple(row["path"]), row["code"]
    cp = row["emitters"]  # [s, class, merged, kind, sx, sy, k]
    gst, gleaves = G.cell(lv, ix, iy)
    gl = next((l for l in gleaves if l["path"] == path), None)
    if gl is None or not gl["aligned"]:
        return {"class": "error", "why": "G leaf not found / not aligned"}
    s0 = cp[0][0]
    _s, gcls, gcode, gw, gpiece = gl["recs"][s0]
    rst, rleaves = Rd.cell(lv, ix, iy)
    res = {"framing_equal": None, "r_status": rst, "r_leaves": [list(l["path"]) for l in rleaves]}
    res["_alias"] = any(l["dsa"] in ralias for l in rleaves)
    if not rleaves:
        return {**res, "class": "R-absent", "sub": f"r_{rst}"}
    if any(not l["aligned"] for l in rleaves):
        return {**res, "class": "error", "why": "R leaf decode/wire misaligned"}
    same = [l for l in rleaves if l["path"] == path and l["frame"] == gl["frame"]]
    res["framing_equal"] = bool(same)
    # R-one-byte
    for l in same:
        hit = [r for r in l["recs"] if r[1] and r[2] == code and r[3] == gw]
        if len(hit) == 1:
            res.update({"class": "R-one-byte", "r_leaf": list(l["path"]), "r_s": hit[0][0]})
            res["position"] = position(gl, l, cp, hit[0][0], bytes_ok=True)
            return res
    rT = [(l, r) for l in rleaves for r in l["recs"] if r[1] and r[2] == code]
    geq = [(l, r) for l, r in rT if ring_equal(r[4], gpiece)]
    if len(geq) == 1:
        l, r = geq[0]
        res.update({"class": "R-one-geom", "r_leaf": list(l["path"]), "r_s": r[0]})
        res["position"] = position(gl, l, cp, r[0], bytes_ok=bool(l["path"] == path and l["frame"] == gl["frame"]))
        return res
    if len(geq) > 1:
        return {**res, "class": "R-other", "sub": f"geom_equal_{len(geq)}"}
    pS, pa = samples(gpiece)
    piece_area = len(pS) * pa
    res["piece_area_raw2"] = round(piece_area, 3)
    # R-merged: an R same-type record containing the piece and covering a different piece of an emitter
    emit_ords = {c[2] for c in cp}
    others = []
    # other pieces of the same sources in this G leaf: records whose emitter merged ordinal is one of cp's
    emit = leaf_emit(row, gl)
    if emit is None:
        return {**res, "class": "error", "why": "G leaf sidecar entries not matched"}
    for r in gl["recs"]:
        if r[1] and r[2] == code and r[3] != gw and emit[r[0]] in emit_ords:
            others.append(r)
    res["other_pieces_of_emitters"] = len(others)
    for l, r in rT:
        if not near(r[4], gpiece):
            continue
        if contains(r[4], pS, gpiece):
            for o in others:
                oS, oa = samples(o[4])
                if covered_area(oS, oa, r[4]) > 1.0:
                    res.update({"class": "R-merged", "r_leaf": list(l["path"]), "r_s": r[0], "other_s": o[0]})
                    return res
    if not rT:
        for l in rleaves:
            for r in l["recs"]:
                if r[1] and r[2] != code and covered_area(pS, pa, r[4]) > 1.0:
                    res.update({"class": "R-noncomparable", "sub": "type-set", "r_type": r[2], "r_leaf": list(l["path"])})
                    return res
        return {**res, "class": "R-absent", "sub": "no_type_in_cell"}
    nearT = [(l, r) for l, r in rT if near(r[4], gpiece)]
    if not nearT:
        return {**res, "class": "R-absent", "sub": "type_elsewhere_in_cell"}
    det = []
    for l, r in nearT[:6]:
        cov = covered_area(pS, pa, r[4])
        det.append({"r_leaf": list(l["path"]), "r_s": r[0], "piece_frac_inside": round(cov / piece_area, 4) if piece_area else None,
                    "contains": contains(r[4], pS, gpiece), "n_r": len(open_ring(r[4])), "n_g": len(open_ring(gpiece))})
    return {**res, "class": "R-other", "sub": "near_same_type", "near": det}


SC = {}  # (items, own, W, P, F) for the sampled cells


def leaf_emit(row, gl):
    """merged ordinal per record of the G leaf, from the live sidecar (census.py matching)."""
    items, own, W, P, F = SC["v"]
    lk = (row["level"], row["ix"], row["iy"]); path = tuple(row["path"])
    ents = None
    wl = W.get(lk)
    if wl and wl[1] == gl["fnv"]:
        ents = wl[2]
    elif len(path) >= 2:
        pl = P.get((*lk, path[-1], gl["fnv"]), [])
        if pl and all(e == pl[0] for e in pl):
            ents = pl[0]
    if ents is None:
        return None
    emit = [i for i, c, k in ents for _ in range(k)]
    return emit if len(emit) == len(gl["recs"]) else None


def frames_of(D, level, ix, iy):
    if level not in D.idx:
        D.idx[level] = LeafIndex(D.rr, level)
    nb = D.idx[level].get(ix, iy)
    out = {}
    for (_lmr, _blk, leaf_row) in nb.handles:
        lpath, le, lb, ptype, _, (fb, fc) = leaf_row
        frng = D.rr.walk.leaf_frame_range(level, ptype, lpath, fc)
        out[tuple(lpath)] = ((round(fb.lat_lo, 12), round(fb.lat_hi, 12), round(fb.lon_lo, 12), round(fb.lon_hi, 12), frng), le.dsa)
    return out


def framing_prefilter(row, G, Rd):
    """national mode: framing_equal | r_alias | r_no_leaf | frame_differs (no decode)."""
    lv, ix, iy, path = row["level"], row["ix"], row["iy"], tuple(row["path"])
    rf = frames_of(Rd, lv, ix, iy)
    if not rf:
        return "r_no_leaf"
    if any(d in RALIAS[lv] for _f, d in rf.values()):
        return "r_alias"
    gf = frames_of(G, lv, ix, iy)
    if path in rf and path in gf and rf[path][0] == gf[path][0]:
        return "framing_equal"
    return "frame_differs"


def position(gl, rl, cp, r_s, bytes_ok):
    """first / last / middle / neither: anchor alignment on unique non-duplicate class>0 records."""
    gpos = [c[0] for c in sorted(cp, key=lambda c: c[2])]  # copies in emitter (merged-ordinal) order
    dup_s = {c[0] for c in cp}
    gk = defaultdict(list); rk = defaultdict(list)
    for s, cls, code, w, P in gl["recs"]:
        if cls and s not in dup_s:
            gk[(code, w) if bytes_ok else None].append(s)
    if bytes_ok:
        for s, cls, code, w, P in rl["recs"]:
            if cls and s != r_s:
                rk[(code, w)].append(s)
        pairs = [(gk[k][0], rk[k][0]) for k in gk if len(gk[k]) == 1 and len(rk.get(k, [])) == 1]
    else:
        gr = [(s, code, P) for s, cls, code, w, P in gl["recs"] if cls and s not in dup_s]
        rr = [(s, code, P) for s, cls, code, w, P in rl["recs"] if cls and s != r_s]
        pairs = []
        for s, code, P in gr:
            m = [t for t, c2, Q in rr if c2 == code and ring_equal(P, Q)]
            if len(m) == 1:
                pairs.append((s, m[0]))
        rs = Counter(t for _s, t in pairs)
        pairs = [(s, t) for s, t in pairs if rs[t] == 1]
    pairs.sort(key=lambda p: p[1])
    gseq = [g for g, _r in pairs]
    mono = all(a < b for a, b in zip(gseq, gseq[1:]))
    prev = max((g for g, r in pairs if r < r_s), default=None)
    nxt = min((g for g, r in pairs if r > r_s), default=None)
    inside = [j for j, s in enumerate(gpos) if (prev is None or prev < s) and (nxt is None or s < nxt)]
    lab = "neither"
    if len(inside) == 1:
        j = inside[0]; lab = "first" if j == 0 else ("last" if j == len(gpos) - 1 else "middle")
    return {"label": lab, "anchors": len(pairs), "anchors_monotone": mono, "prev_g": prev, "next_g": nxt,
            "g_copies_emitter_order": gpos, "inside": inside}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=Path, required=True)
    ap.add_argument("--g", type=Path, required=True, help="dir holding the live ALLDATA.KWI")
    ap.add_argument("--r", default=R_DISC)
    ap.add_argument("--out", type=Path, required=True, help="prefix")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sc", type=Path, required=True, help="live sidecar dir (census.py input)")
    ap.add_argument("--all-census", type=Path, default=None,
                    help="national mode: every census row; only framing-equal classes are classified")
    a = ap.parse_args(argv)
    t0 = time.time()
    rows = json.loads(a.sample.read_text())["rows"]
    if a.all_census:
        rows = []
        with gzip.open(a.all_census, "rt") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                rows.append({"stratum": "national", "split": "national", "level": int(r["level"]), "ix": int(r["ix"]),
                             "iy": int(r["iy"]), "path": [int(x) for x in r["path"].split(",")], "code": int(r["code"]),
                             "copies": int(r["copies"]), "record_sha256": r["record_sha256"],
                             "emitters": json.loads(r["emitters"])})
    if a.limit:
        rows = rows[:a.limit]
    RALIAS.update({lv: alias_dsas(str(Path(a.r) / "ALLDATA.KWI"), lv) for lv in sorted({r["level"] for r in rows})})
    print(json.dumps({"r_alias_frames": {k: len(v) for k, v in RALIAS.items()}, "t": round(time.time() - t0, 1)}), flush=True)
    import atexit, shutil, tempfile
    from provenance import load_fnv
    from census import parse_sidecar_filtered
    tmp = Path(tempfile.mkdtemp(prefix="p68_rcorr_")); atexit.register(shutil.rmtree, tmp, True)
    FNV.append(load_fnv(tmp))
    SC["v"] = parse_sidecar_filtered(a.sc, {(r["level"], r["ix"], r["iy"]) for r in rows})
    G = Disc(str(a.g)); Rd = Disc(str(a.r))
    # other pieces of the copies' emitters in the G leaf: from the census emitters we only know the copies;
    # the merged ordinals of all records come from the sidecar-free fact that enc_bg writes each background's
    # pieces contiguously: records adjacent to a copy with the same type and class are taken as candidates.
    out = []; c = Counter(); pre = Counter()
    for n, row in enumerate(rows):
        row = dict(row)
        if a.all_census:
            fe = framing_prefilter(row, G, Rd)
            pre[fe] += 1
            if fe != "framing_equal":
                continue
        try:
            res = classify(row, G, Rd, None)
        except Exception as e:  # noqa: BLE001
            res = {"class": "error", "why": repr(e)[:200]}
        rec = {k: row[k] for k in ("stratum", "split", "level", "ix", "iy", "path", "code", "copies", "record_sha256")}
        rec["emitter_kinds"] = sorted({e[3] for e in row["emitters"]})
        rec.update(res)
        out.append(rec)
        c[f"{rec['class']}" + (f"/{rec.get('sub')}" if rec.get("sub") else "")] += 1
        if n % 200 == 0:
            print(json.dumps({"n": n, "t": round(time.time() - t0, 1), "c": dict(c)}), flush=True)
            L.clear_spool_caches()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(b"row_json\n")
        for r in out:
            gz.write((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    summ = {"prefilter": dict(sorted(pre.items())), "n": len(out), "by_class": dict(sorted(c.items())),
            "by_split_class": dict(sorted(Counter(f"{r['split']}/{r['class']}" for r in out).items())),
            "by_stratum_class": dict(sorted(Counter(f"{r['stratum']}/{r['class']}" for r in out).items())),
            "position": dict(sorted(Counter(f"{r['split']}/{r['class']}/{(r.get('position') or {}).get('label')}"
                                            for r in out if r["class"] in ("R-one-byte", "R-one-geom")).items())),
            "framing_equal": dict(sorted(Counter(f"{r['class']}/{r.get('framing_equal')}" for r in out).items())),
            "alias_geom_class": dict(sorted(Counter(f"{r['split']}/{r.get('geom_class')}/{r.get('geom_sub')}" for r in out if r.get("sub") == "alias").items())),
            "alias_position": dict(sorted(Counter(f"{r['split']}/{r.get('geom_class')}/{(r.get('position') or {}).get('label')}" for r in out if r.get("sub") == "alias" and r.get("geom_class") in ("R-one-byte", "R-one-geom")).items())),
            "sample_sha256": hashlib.sha256(a.sample.read_bytes()).hexdigest(), "wall_s": round(time.time() - t0, 1)}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
