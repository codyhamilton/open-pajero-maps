"""Plan 39 P2: the allrows clause (b) test for the failing rows of the 37 3-11 cells on 013586b5 (the 3-11 disc, the basis
the 9,064 remainder was counted on). The basis map shows every row outside these cells is identical on 87a01b14, so with
allrows_clause_b.py this covers every background/background_boundary failing row of 013586b5. Status codes as there."""
import sys, os, json
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(HERE + "/allrows_clause_b.py").read()
exec(src.split('os.makedirs("output/scratch-39/allrows"')[0])
cells37 = {(int(l.split("\t")[0]), int(l.split("\t")[1]), int(l.split("\t")[2])) for l in open("output/scratch-36/diff-3-11-au.cells.tsv").read().splitlines()[1:]}
assert len(cells37) == 37
D, OLD, NEW = "output/scratch-39/dump_311", "output/scratch-3-11/G_new/ALLDATA.KWI", "output/scratch-14/G_new/ALLDATA.KWI"
fo, fn = open(OLD, "rb"), open(NEW, "rb")
hdr = volume.parse_volume_header(oc.read_exact(fo, 0, volume.DATAVOL_SIZE)); ss, ls = hdr.sector_size, hdr.logical_sector_size
hdr2 = volume.parse_volume_header(oc.read_exact(fn, 0, volume.DATAVOL_SIZE)); ss2, ls2 = hdr2.sector_size, hdr2.logical_sector_size
old, new = frames(OLD, cells37), frames(NEW, cells37)
names = {0: "unset", 1: "present_on_4ed9cd80", 2: "removed_on_4ed9cd80", 3: "footprints_changed", 4: "new_leaf_missing", 5: "old_mapping_mismatch", 6: "old_leaf_missing"}
out = {}
for kind in ("background", "background_boundary"):
    m = json.load(open(D + "/dump_manifest.json"))["kinds"][kind]
    dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
    R = np.memmap(f"{D}/{kind}.bin", dtype=dt, mode="r")
    lv, ix, iy = np.asarray(R["level"]).astype(np.int64), np.asarray(R["ix"]).astype(np.int64), np.asarray(R["iy"]).astype(np.int64)
    ck = (lv << 40) | (ix << 20) | iy
    want = np.array(sorted((l << 40) | (x << 20) | y for l, x, y in cells37), np.int64)
    sel = np.flatnonzero(np.isin(ck, want))
    cols = {k: np.asarray(R[k][sel]) for k in ("level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert", "vx", "vy", "code")}
    n = len(sel); status = np.zeros(n, np.uint8)
    for i in range(n):
        c = (int(cols["level"][i]), int(cols["ix"][i]), int(cols["iy"][i])); d = int(cols["depth"][i])
        lk = c + (tuple(int(cols[p][i]) for p in ("p0", "p1", "p2")[:d]),)
        if lk not in old: status[i] = 6; continue
        S, V, C, X, Y = leaf_vertices(fo, old[lk], ss, ls)
        hit = np.flatnonzero((S == cols["shape"][i]) & (V == cols["vert"][i]))
        if not (len(hit) == 1 and X[hit[0]] == cols["vx"][i] and Y[hit[0]] == cols["vy"][i] and C[hit[0]] == cols["code"][i]): status[i] = 5; continue
        if fe.get(c, "0") != "1": status[i] = 3; continue
        if lk not in new: status[i] = 4; continue
        nv = leaf_vertices(fn, new[lk], ss2, ls2)
        pres = bool(np.any((nv[2] == cols["code"][i]) & (nv[3] == cols["vx"][i]) & (nv[4] == cols["vy"][i]))) if nv[0].size else False
        status[i] = 1 if pres else 2
    out[kind] = {"rows_in_37_cells": n, **{names[k]: v for k, v in sorted(Counter(status.tolist()).items())}}
    print(kind, out[kind], flush=True)
os.makedirs("output/scratch-39/allrows", exist_ok=True)
json.dump(out, open("output/scratch-39/allrows/allrows_311_cells.json", "w"), indent=1); print("ALLROWS311DONE")
