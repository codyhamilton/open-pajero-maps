"""Plan 39 P2: clause (b) presence test (r01_clause_b.py) for EVERY background and background_boundary failing row on
87a01b14 (HEAD K1 dump), vectorised per leaf. Writes a per-row status u8 array per kind (dump row order) to
output/scratch-39/allrows/<kind>.status.u8: 1 present on 4ed9cd80, 2 removed, 3 footprints changed (untested),
4 leaf missing on new, 5 old mapping mismatch, 6 old leaf missing. Lets any later remainder identity join by row index."""
import sys, os, json, gzip
from collections import Counter, defaultdict
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "parser")
exec(open(HERE + "/../p1/wrap37.py").read().split("cells = {")[0])
from kiwiw.coordconv import decode_region_coord
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
fe = {}
with gzip.open("docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz", "rt") as f:
    next(f)
    for l in f:
        x = l.split("\t"); fe[(int(x[0]), int(x[1]), int(x[2]))] = x[4]
def frames(path, cellset):
    out = {}
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size: continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
                if not any((lm.level, x, y) in cellset for x in range(bx, bx + nx) for y in range(by, by + ny)): continue
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if (lm.level, bx + x, by + y) not in cellset: continue
                    out[(lm.level, bx + x, by + y, tuple(leaf))] = (entry.dsa, entry.size)
    return out
def leaf_vertices(fh, ent, ss, ls):
    """All class>0 record vertices of a leaf: arrays (shape_index, vert_index, type, x, y) in D1 order."""
    buf = os.pread(fh.fileno(), ent[1] * ls, volume.getsector(ent[0], ss, ls)); buf = buf[:U16(buf, 0) * 2]
    bg = sec.split(buf)["background"]
    S, V, C, X, Y = [], [], [], [], []
    if not bg: return None
    hlen = sec.u16(bg, 0) * 2; off = 2; s = 0
    while off < hlen:
        w = sec.u16(bg, off); po = w * 2; off += 4
        if w == 0xFFFF: continue
        n = sec.u16(bg, po); u0 = po + 2; p = u0 + 4 * n
        for i in range(n):
            val = sec.u16(bg, u0 + 4 * i + 2); cnt, cls = val & 0xFFF, val >> 14
            for _ in range(cnt):
                L = (sec.u16(bg, p) & 0xFFF) * 2; code = sec.u16(bg, p + 4)
                if cls:
                    nco = sec.u16(bg, p + 2) & 0x7FF; mult = 1 << (sec.u16(bg, p + 6) & 7)
                    d = np.frombuffer(bg, np.int8, 2 * nco, p + 12).astype(np.int64).reshape(-1, 2) * mult
                    x0, y0 = decode_region_coord(sec.u16(bg, p + 8)), decode_region_coord(sec.u16(bg, p + 10))
                    X.append(np.concatenate(([x0], x0 + np.cumsum(d[:, 0])))); Y.append(np.concatenate(([y0], y0 + np.cumsum(d[:, 1]))))
                    S.append(np.full(nco + 1, s)); V.append(np.arange(nco + 1)); C.append(np.full(nco + 1, code))
                s += 1; p += L
    if not S: return (np.zeros(0, np.int64),) * 5
    return tuple(np.concatenate(a).astype(np.int64) for a in (S, V, C, X, Y))
def pack(c, x, y): return (c << 42) ^ ((x + (1 << 20)) << 21) ^ (y + (1 << 20))
os.makedirs("output/scratch-39/allrows", exist_ok=True)
out = {}
fo, fn = open("output/scratch-36/G_pre311/ALLDATA.KWI", "rb"), open("output/scratch-14/G_new/ALLDATA.KWI", "rb")
hdr = volume.parse_volume_header(oc.read_exact(fo, 0, volume.DATAVOL_SIZE)); ss, ls = hdr.sector_size, hdr.logical_sector_size
hdr2 = volume.parse_volume_header(oc.read_exact(fn, 0, volume.DATAVOL_SIZE)); ss2, ls2 = hdr2.sector_size, hdr2.logical_sector_size
for kind in ("background", "background_boundary"):
    m = json.load(open("output/scratch-39/dump_pre311/dump_manifest.json"))["kinds"][kind]
    dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True)
    R = np.memmap(f"output/scratch-39/dump_pre311/{kind}.bin", dtype=dt, mode="r")
    cols = {k: np.asarray(R[k]) for k in ("level", "ix", "iy", "depth", "p0", "p1", "p2", "shape", "vert", "vx", "vy", "code")}
    n = len(cols["level"]); status = np.zeros(n, np.uint8)
    assert int(cols["depth"].max()) <= 3
    key = np.stack([cols["level"].astype(np.int64), cols["ix"], cols["iy"], cols["depth"], cols["p0"], np.where(cols["depth"] > 1, cols["p1"], 0), np.where(cols["depth"] > 2, cols["p2"], 0)], 1)
    order = np.lexsort(key.T[::-1]); ks = key[order]
    brk = np.flatnonzero(np.any(ks[1:] != ks[:-1], axis=1)) + 1; starts = np.concatenate(([0], brk)); ends = np.concatenate((brk, [n]))
    cellset = set(map(tuple, np.unique(key[:, :3], axis=0).tolist()))
    old, new = frames("output/scratch-36/G_pre311/ALLDATA.KWI", cellset), frames("output/scratch-14/G_new/ALLDATA.KWI", cellset)
    print(kind, "rows", n, "leaves", len(starts), "old", len(old), "new", len(new), flush=True)
    for a, b in zip(starts, ends):
        k0 = ks[a]; idx = order[a:b]; c = (int(k0[0]), int(k0[1]), int(k0[2]))
        lk = c + (tuple(int(v) for v in k0[4:4 + int(k0[3])]),)
        if lk not in old: status[idx] = 6; continue
        ov = leaf_vertices(fo, old[lk], ss, ls)
        S, V, C, X, Y = ov
        # validate (shape, vert) -> (vx, vy, code)
        okey = S * 65536 + V; rkey = cols["shape"][idx].astype(np.int64) * 65536 + cols["vert"][idx]
        pos = np.searchsorted(okey, rkey); pos = np.minimum(pos, len(okey) - 1) if len(okey) else pos
        good = (len(okey) > 0) & (okey[pos] == rkey) & (X[pos] == cols["vx"][idx]) & (Y[pos] == cols["vy"][idx]) & (C[pos] == cols["code"][idx]) if len(okey) else np.zeros(len(idx), bool)
        status[idx[~good]] = 5
        gi = idx[good]
        if not len(gi): continue
        if fe.get(c, "0") != "1": status[gi] = 3; continue
        if lk not in new: status[gi] = 4; continue
        nv = leaf_vertices(fn, new[lk], ss2, ls2)
        nset = np.unique(pack(nv[2], nv[3], nv[4])) if nv[0].size else np.zeros(0, np.int64)
        pres = np.isin(pack(cols["code"][gi].astype(np.int64), cols["vx"][gi].astype(np.int64), cols["vy"][gi].astype(np.int64)), nset)
        status[gi[pres]] = 1; status[gi[~pres]] = 2
    status.tofile(f"output/scratch-39/allrows/{kind}.status.u8")
    names = {0: "unset", 1: "present_on_4ed9cd80", 2: "removed_on_4ed9cd80", 3: "footprints_changed", 4: "new_leaf_missing", 5: "old_mapping_mismatch", 6: "old_leaf_missing"}
    cnt = Counter(status.tolist()); out[kind] = {names[k]: v for k, v in sorted(cnt.items())}
    if kind == "background":
        a01 = np.fromfile("output/scratch-39/classifyR01_pre311/assign_background.u16", dtype="<u2")
        out["background_non_R01"] = {names[k]: v for k, v in sorted(Counter(status[a01 != 0].tolist()).items())}
    print(kind, out[kind], flush=True)
json.dump(out, open("output/scratch-39/allrows/allrows_clause_b.json", "w"), indent=1); print("ALLROWSDONE")
