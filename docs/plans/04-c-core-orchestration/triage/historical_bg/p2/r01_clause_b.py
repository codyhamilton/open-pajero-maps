"""Plan 39 P2 clause (b) for R01 rows (87a01b14 basis, HEAD K1 dump): is the failing item (G vertex at raw (vx,vy) of a
type-t record in the same leaf) still present on 4ed9cd80? Item identity = (level, cell, leaf path, type, raw vertex);
leaf frames compared only where plan 36 P3 says footprints are equal (otherwise reported separately).
Mapping validated on 87a01b14: row (shape, vert) re-derives (vx,vy) from the record bytes (all rows)."""
import sys, os, json, gzip, hashlib
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, "parser")
exec(open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/../p1/wrap37.py").read().split("cells = {")[0])
from kiwiw.coordconv import decode_region_coord
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
m = json.load(open("output/scratch-39/dump_pre311/dump_manifest.json"))["kinds"]["background"]
dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
R = np.memmap("output/scratch-39/dump_pre311/background.bin", dtype=dt, mode="r")
a = np.fromfile("output/scratch-39/classifyR01_pre311/assign_background.u16", dtype="<u2")
rows = np.asarray(R[np.flatnonzero(a == 0)])
fe = {}
with gzip.open("docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz", "rt") as f:
    next(f)
    for l in f:
        x = l.split("\t"); fe[(int(x[0]), int(x[1]), int(x[2]))] = (x[3], x[4])
cells = set(zip(rows["level"].tolist(), rows["ix"].tolist(), rows["iy"].tolist()))
def frames(path):
    out = {}
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        want = defaultdict(set)
        for c in cells: want[c[0]].add((c[1], c[2]))
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            if lm.level not in want: continue
            W = want[lm.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size: continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
                if not any((x, y) in W for x in range(bx, bx + nx) for y in range(by, by + ny)): continue
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if (bx + x, by + y) not in W: continue
                    buf = oc.read_exact(f, volume.getsector(entry.dsa, ss, ls), entry.size * ls)
                    out[(lm.level, bx + x, by + y, tuple(leaf))] = buf[:U16(buf, 0) * 2]
    return out
def records(bg):
    recs = []
    if not bg: return recs
    hlen = sec.u16(bg, 0) * 2; off = 2
    while off < hlen:
        w = sec.u16(bg, off); po = w * 2; off += 4
        if w == 0xFFFF: continue
        n = sec.u16(bg, po); u0 = po + 2; p = u0 + 4 * n
        for i in range(n):
            val = sec.u16(bg, u0 + 4 * i + 2); cnt, cls = val & 0xFFF, val >> 14
            for _ in range(cnt):
                L = (sec.u16(bg, p) & 0xFFF) * 2; recs.append((p, sec.u16(bg, p + 4), cls)); p += L
    return recs
def verts(bg, p):
    nco = sec.u16(bg, p + 2) & 0x7FF; mult = 1 << (sec.u16(bg, p + 6) & 7)
    d = np.frombuffer(bg, np.int8, 2 * nco, p + 12).astype(np.int64).reshape(-1, 2) * mult
    x0, y0 = decode_region_coord(sec.u16(bg, p + 8)), decode_region_coord(sec.u16(bg, p + 10))
    xs = np.concatenate(([x0], x0 + np.cumsum(d[:, 0]))); ys = np.concatenate(([y0], y0 + np.cumsum(d[:, 1])))
    return xs, ys
def leafkey(r):
    d = int(r["depth"]); return tuple(int(r[f"p{i}"]) for i in range(d))
old = frames("output/scratch-36/G_pre311/ALLDATA.KWI"); print("old leaves", len(old), flush=True)
new = frames("output/scratch-14/G_new/ALLDATA.KWI"); print("new leaves", len(new), flush=True)
res = Counter(); per_type = defaultdict(Counter)
def leaf_index(fr, k, cache):
    if k not in cache:
        if len(cache) > 4000: cache.clear()
        bg = sec.split(fr[k])["background"]; recs = records(bg)
        bytype = defaultdict(set)
        for p, code, cls in recs:
            if cls:
                xs, ys = verts(bg, p); bytype[code].update(zip(xs.tolist(), ys.tolist()))
        cache[k] = (bg, recs, bytype)
    return cache[k]
co, cn = {}, {}
order = np.lexsort((rows["p1"], rows["p0"], rows["iy"], rows["ix"], rows["level"]))
for j in order:
    r = rows[j]; c = (int(r["level"]), int(r["ix"]), int(r["iy"])); k = c + (leafkey(r),)
    if k not in old: res["old_leaf_missing"] += 1; continue
    bg, recs, _ = leaf_index(old, k, co); s, vt = int(r["shape"]), int(r["vert"])
    xs, ys = verts(bg, recs[s][0]) if 0 <= s < len(recs) else (None, None)
    if xs is None or not (0 <= vt < len(xs)) or (int(xs[vt]), int(ys[vt])) != (int(r["vx"]), int(r["vy"])) or recs[s][1] != int(r["code"]):
        res["old_mapping_mismatch"] += 1; continue
    if fe.get(c, ("", "0"))[1] != "1": res["footprints_changed"] += 1; per_type[int(r["code"])]["footprints_changed"] += 1; continue
    if k not in new: res["new_leaf_missing"] += 1; per_type[int(r["code"])]["new_leaf_missing"] += 1; continue
    _, _, bt = leaf_index(new, k, cn)
    if (int(r["vx"]), int(r["vy"])) in bt.get(int(r["code"]), ()):
        res["item_present_on_4ed9cd80"] += 1; per_type[int(r["code"])]["present"] += 1
    else:
        res["item_removed_on_4ed9cd80"] += 1; per_type[int(r["code"])]["removed"] += 1
out = {"r01_rows": int(len(rows)), "cells": len(cells), **dict(res), "per_type": {str(k): dict(v) for k, v in per_type.items()}}
json.dump(out, open("output/scratch-39/r01_clause_b.json", "w"), indent=1); print(json.dumps(out)); print("CLAUSEBDONE")
