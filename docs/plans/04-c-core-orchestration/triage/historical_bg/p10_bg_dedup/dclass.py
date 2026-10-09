#!/usr/bin/env python3
"""Plan 68 Phase 1: same-type, different-bytes record pairs in one leaf (D-classes), G and R.

Definitions (committed with this file before its first measuring run):
  pairs: two class>0 background records of one leaf frame, same type code, not byte-identical.
  D-rot:     same frame-local vertex ring up to start vertex and / or direction (exact; one frame).
  D-contain: not D-rot; every vertex of one piece lies inside the other (even-odd) or within 1 raw unit
             of its boundary, and no vertex of the other lies inside the first farther than 1 raw unit
             from its boundary (vertex criterion; tool probe showed a 48x48 grid test costs ~10 s per
             dense urban leaf, so the grid is used only for the overlap area below).
  D-overlap: neither; some vertex of one lies inside the other farther than 1 raw unit from its boundary,
             and the shared area (24x24 grid sample over the smaller piece's bbox) >= max(1 raw unit^2,
             1 % of the smaller piece's area).
  class-0 repeats: two or more class-0 records of one type in one leaf (byte-identical or not).
Pieces are frame-local raw coordinates (one frame, so no framing question). R frames are read whole
(r_census.py); G frames to their length word. Multiprocessing over blocks (-j). Output <out>.json with
counts per level / class / type and <out>.tsv.gz example rows (first 20,000 per class, deterministic)."""
from __future__ import annotations

import argparse, gzip, io, json, os, sys, time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import census as CZ  # noqa: E402
from r_corr import pip, seg_dist, segs, open_ring  # noqa: E402
L = CZ.L
from kiwiw import volume  # noqa: E402
from kiwiw.coordconv import decode_region_coord  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402

NS = 24
TOL = 1.0


def records(buf):
    """[(s, cls, code, wire, verts ndarray)] for every background record (verts empty for class 0)."""
    sec = L.sec; out = []
    bg = sec.split(buf)["background"]
    if not bg:
        return out
    hlen = sec.u16(bg, 0) * 2; off = 2; s = 0
    while off < hlen:
        w = sec.u16(bg, off); po = w * 2; off += 4
        if w == 0xFFFF:
            continue
        n = sec.u16(bg, po); u0 = po + 2; p = u0 + 4 * n
        for i in range(n):
            val = sec.u16(bg, u0 + 4 * i + 2); cnt, cls = val & 0xFFF, val >> 14
            for _ in range(cnt):
                ln = (sec.u16(bg, p) & 0xFFF) * 2; code = sec.u16(bg, p + 4)
                V = np.zeros((0, 2))
                if cls:
                    nco = sec.u16(bg, p + 2) & 0x7FF; mult = 1 << (sec.u16(bg, p + 6) & 7)
                    d = np.frombuffer(bg, np.int8, 2 * nco, p + 12).astype(np.int64).reshape(-1, 2) * mult
                    x0 = decode_region_coord(sec.u16(bg, p + 8)); y0 = decode_region_coord(sec.u16(bg, p + 10))
                    V = np.stack([np.concatenate(([x0], x0 + np.cumsum(d[:, 0]))),
                                  np.concatenate(([y0], y0 + np.cumsum(d[:, 1])))], 1).astype(float)
                out.append((s, cls, code, bytes(bg[p:p + ln]), V))
                s += 1; p += ln
    return out


def rot_equal(A, B):
    A = open_ring(A); B = open_ring(B)
    if len(A) != len(B) or not len(A):
        return False
    for BB in (B, B[::-1]):
        for k in np.nonzero((BB == A[0]).all(1))[0]:
            if (np.roll(BB, -k, 0) == A).all():
                return True
    return False


def grid(P):
    P = open_ring(P)
    x0, y0 = P.min(0); x1, y1 = P.max(0)
    dx = max((x1 - x0) / NS, 1e-9); dy = max((y1 - y0) / NS, 1e-9)
    gx = x0 + (np.arange(NS) + .5) * dx; gy = y0 + (np.arange(NS) + .5) * dy
    G = np.stack(np.meshgrid(gx, gy), -1).reshape(-1, 2)
    m = pip(G, P)
    return G[m], dx * dy


def inside_tol(Q, R):
    ins = pip(Q, R)
    out = Q[~ins]
    return len(out) == 0 or seg_dist(out, segs(open_ring(R), True)).max() <= TOL


def leaf_pairs(recs):
    res = Counter(); ex = []
    by = defaultdict(list)
    c0 = Counter()
    for s, cls, code, w, V in recs:
        if cls:
            if len(open_ring(V)) >= 3:
                by[code].append((s, w, V))
        else:
            c0[code] += 1
    for code, n in c0.items():
        if n >= 2:
            res[f"class0_repeat/{code}"] += 1
    for code, rs in by.items():
        if len(rs) < 2:
            continue
        bb = np.array([[*open_ring(V).min(0), *open_ring(V).max(0)] for _s, _w, V in rs])
        n = len(rs)
        # bbox prefilter (exact consequences of the definitions): D-rot needs equal bboxes; D-contain
        # needs one bbox inside the other (+tol); D-overlap needs a bbox intersection of area >= 1.
        ix0 = np.maximum(bb[:, None, 0], bb[None, :, 0]); ix1 = np.minimum(bb[:, None, 2], bb[None, :, 2])
        iy0 = np.maximum(bb[:, None, 1], bb[None, :, 1]); iy1 = np.minimum(bb[:, None, 3], bb[None, :, 3])
        iarea = np.clip(ix1 - ix0, 0, None) * np.clip(iy1 - iy0, 0, None)
        ins_ij = ((bb[:, None, 0] >= bb[None, :, 0] - TOL) & (bb[:, None, 2] <= bb[None, :, 2] + TOL) &
                  (bb[:, None, 1] >= bb[None, :, 1] - TOL) & (bb[:, None, 3] <= bb[None, :, 3] + TOL))
        ov = (iarea >= 1.0) | ins_ij | ins_ij.T
        rings = [open_ring(V) for _s, _w, V in rs]
        sgs = [segs(R, True) for R in rings]
        gcache = {}

        def deep_inside(P, i):
            """vertices of P strictly inside ring i farther than TOL from its boundary."""
            m = pip(P, rings[i])
            if not m.any():
                return np.zeros(len(P), bool)
            d = np.full(len(P), 0.0); d[m] = seg_dist(P[m], sgs[i])
            return m & (d > TOL)

        def in_or_near(P, i):
            m = pip(P, rings[i])
            if m.all():
                return True
            return bool(seg_dist(P[~m], sgs[i]).max() <= TOL)
        area = [abs(float(np.dot(R[:, 0], np.roll(R[:, 1], -1)) - np.dot(R[:, 1], np.roll(R[:, 0], -1)))) / 2 for R in rings]
        cand = np.argwhere(np.triu(ov, 1))
        for i, j in cand:
            if rs[i][1] == rs[j][1]:
                continue
            A, B = rings[i], rings[j]
            if len(A) == len(B) and (bb[i] == bb[j]).all() and rot_equal(A, B):
                k = "D-rot"
            else:
                k = None
                si, bj = (i, j) if area[i] <= area[j] else (j, i)
                if ins_ij[si, bj] and in_or_near(rings[si], bj) and not deep_inside(rings[bj], si).any():
                    k = "D-contain"
                elif iarea[i, j] >= 1.0 and (deep_inside(A, j).any() or deep_inside(B, i).any()):
                    if si not in gcache:
                        gcache[si] = grid(rings[si])
                    S, a = gcache[si]
                    sh = float(pip(S, rings[bj]).sum()) * a if len(S) else 0.0
                    if sh >= max(1.0, 0.01 * min(area[i], area[j])):
                        k = "D-overlap"
            if k:
                res[f"{k}/{code}"] += 1
                ex.append((k, code, rs[i][0], rs[j][0]))
    return res, ex


def work(job):
    path, level, items, whole = job
    res = Counter(); ex = []
    with open(path, "rb") as f:
        for lk, dsa, size, ss, ls in items:
            b = os.pread(f.fileno(), size * ls, volume.getsector(dsa, ss, ls))
            buf = b if whole else b[:L.U16(b, 0) * 2]
            r, e = leaf_pairs(records(buf))
            for k, v in r.items():
                res[f"{level}/{k}"] += v
            res[f"{level}/leaves"] += 1
            res[f"{level}/leaves_with_D"] += any(not k.startswith("class0") for k in r)
            ex.extend((*lk, *x) for x in e)
    return res, ex


def jobs(path, whole):
    oc = L.oc; seen = set()
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            nbx = 1 + lm.n_blocks_lng
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * (1 + lm.n_blocks_lat) + bi // nbx) * ny
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                items = []
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if entry.dsa in seen:
                        continue
                    seen.add(entry.dsa)
                    items.append(((lm.level, bx + x, by + y, ",".join(map(str, leaf))), entry.dsa, entry.size, ss, ls))
                if items:
                    yield (str(path), lm.level, items, whole)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--disc", type=Path, required=True)
    ap.add_argument("--whole", action="store_true", help="read whole leaf entries (R)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("-j", type=int, default=4)
    a = ap.parse_args(argv)
    t0 = time.time(); tot = Counter(); exs = defaultdict(list)
    with Pool(a.j) as pool:
        for n, (r, e) in enumerate(pool.imap(work, jobs(a.disc, a.whole), chunksize=1)):
            tot.update(r)
            for x in e:
                if len(exs[x[4]]) < 20000:
                    exs[x[4]].append(x)
            if n % 500 == 0:
                print(json.dumps({"blocks": n, "t": round(time.time() - t0, 1)}), flush=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(b"level\tix\tiy\tpath\tdclass\tcode\ts_a\ts_b\n")
        for k in sorted(exs):
            for x in sorted(exs[k]):
                g.write(("\t".join(map(str, x)) + "\n").encode())
    Path(str(a.out) + ".tsv.gz").write_bytes(buf.getvalue())
    summ = {"counts": dict(sorted(tot.items())), "definitions": __doc__, "wall_s": round(time.time() - t0, 1)}
    Path(str(a.out) + ".json").write_text(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    agg = Counter()
    for k, v in tot.items():
        p = k.split("/")
        agg[p[1]] += v
    print(json.dumps(dict(sorted(agg.items()))))


if __name__ == "__main__":
    main()
