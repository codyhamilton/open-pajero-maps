"""Plan 39 P3: exact producer join of source 65623 = (L0,1689,508,rec0,type288,n1810) against every failing row on 87a01b14.
Producer identity by build counterfactual at the 87a01b14 producer commit (b7c7c42), L0 window [1414,1890)x[274,750):
  ctl = pinned spool; cf = pinned spool minus that source (its home cell held nothing else).
  (1) control: ctl frames == G_pre311 frames, per cell multiset of frame sha256;
  (2) a ctl background record is 65623-produced iff its bytes are absent from the cf frame of the same leaf (multiset);
  (3) each failing row (HEAD K1 dump on 87a01b14, kinds background/background_boundary/interior_cover) is joined to its
      leaf and record; the mapping is validated by re-deriving the row's raw vertex (vx,vy) from record bytes.
Rows outside the window cannot be produced by the source (window covers the source bbox's candidate cells; see screen)."""
import sys, os, json, hashlib, csv
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, "parser")
exec(open(__import__("os").path.dirname(__import__("os").path.abspath(__file__)) + "/../p1/wrap37.py").read().split("cells = {")[0])   # oc, sec, volume, U16, parse_parcel_mgmt_record
T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1", "i16": "<i2", "u32": "<u4", "i8": "i1", "f32": "<f4", "i64": "<i8", "u64": "<u8"}
def load(d, kind):
    m = json.load(open(f"{d}/dump_manifest.json"))["kinds"][kind]
    dt = np.dtype([(f["name"], T[f["type"]]) for f in m["fields"]], align=True); assert dt.itemsize == m["row_size"]
    return np.memmap(f"{d}/{kind}.bin", dtype=dt, mode="r"), m["rows"]
P = "output/scratch-39/p3"; X0, Y0, X1, Y1 = 1414, 274, 1890, 750
def frame_index(d):
    idx = {}
    for r in csv.reader(open(f"{d}/frames.tsv"), delimiter="\t"):
        lv, ix, iy, pt, sx, sy, off, ln, sha = r
        idx[(int(ix), int(iy), int(pt), int(sx), int(sy))] = (int(off), int(ln), sha)
    return idx
ctl, cf = frame_index(P + "/ctl"), frame_index(P + "/cf")
fctl, fcf = open(P + "/ctl/frames.bin", "rb"), open(P + "/cf/frames.bin", "rb")
def fbytes(fh, e): return os.pread(fh.fileno(), e[1], e[0])
# (1) control vs G_pre311 (targeted preads of window cells) + L0 layout for sub-slot mapping
gsha = defaultdict(list); lm0 = None
with open("output/scratch-36/G_pre311/ALLDATA.KWI", "rb") as f:
    hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
    mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
    prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
    pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
    levels = {m.level: m for m in pd.levels}; lm0 = levels[0]
    for table in pd.bmt_tables:
        bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
        if lm.level != 0: continue
        nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
        bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
        nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
        for bi, block in enumerate(table.entries):
            if block.dsa == 0xFFFFFFFF or not block.size: continue
            bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
            if bx + nx <= X0 or bx >= X1 or by + ny <= Y0 or by >= Y1: continue
            root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
            for x, y, leaf, entry in oc.tree_leaves(root, lm):
                cx, cy = bx + x, by + y
                if not (X0 <= cx < X1 and Y0 <= cy < Y1): continue
                buf = oc.read_exact(f, volume.getsector(entry.dsa, ss, ls), entry.size * ls)
                gsha[(cx, cy)].append(hashlib.sha256(buf[:U16(buf, 0) * 2]).hexdigest())
csha = defaultdict(list)
for k, e in ctl.items(): csha[(k[0], k[1])].append(e[2])
ctrl_mismatch = [c for c in set(gsha) | set(csha) if sorted(gsha.get(c, [])) != sorted(csha.get(c, []))]
out = {"window": [X0, Y0, X1, Y1], "control_cells": len(csha), "control_g_cells": len(gsha), "control_cell_mismatches": len(ctrl_mismatch),
       "control_mismatch_sample": sorted(ctrl_mismatch)[:10]}
print("control", out, flush=True)
# (2) per changed leaf: ctl records absent from cf
def records(bg):
    """Background records in D1 order (elements -> units -> declared count), with type code and raw vertices."""
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
                L = (sec.u16(bg, p) & 0xFFF) * 2; nco = sec.u16(bg, p + 2) & 0x7FF; code = sec.u16(bg, p + 4)
                recs.append((bg[p:p + L], code, cls, p, nco)); p += L
    return recs
def verts(bg, rec):
    from kiwiw.coordconv import decode_region_coord
    raw, code, cls, p, nco = rec
    mult = 1 << (sec.u16(bg, p + 6) & 7)
    x, y = decode_region_coord(sec.u16(bg, p + 8)), decode_region_coord(sec.u16(bg, p + 10)); v = [(x, y)]
    for m in range(nco):
        xo = bg[p + 12 + 2 * m]; yo = bg[p + 13 + 2 * m]
        x += (xo - 256 if xo > 127 else xo) * mult; y += (yo - 256 if yo > 127 else yo) * mult; v.append((x, y))
    return v
changed = [k for k in ctl if k not in cf or cf[k][2] != ctl[k][2]]
prod = {}; prod_types = Counter(); other_changes = Counter(); n_prod = 0
for k in changed:
    a = sec.split(fbytes(fctl, ctl[k]))
    b = sec.split(fbytes(fcf, cf[k])) if k in cf else {"background": b"", "road": None, "name": None}
    for s in ("road", "name"):
        if k in cf and a[s] != b[s]: other_changes[s] += 1
    ra, rb = records(a["background"]), records(b["background"])
    left = Counter(r[0] for r in rb); mine = set()
    for i, r in enumerate(ra):
        if left[r[0]] > 0: left[r[0]] -= 1
        else: mine.add(i); prod_types[r[1]] += 1
    added = sum(left.values())
    if added: other_changes["cf_records_not_in_ctl"] += added
    prod[k] = mine; n_prod += len(mine)
out.update({"changed_leaves": len(changed), "produced_records": n_prod, "produced_types": dict(prod_types), "other_changes": dict(other_changes)})
print("cf", {k: out[k] for k in ("changed_leaves", "produced_records", "produced_types", "other_changes")}, flush=True)
# (3) join failing rows
nxs = {pt: 1 + lm0.n_parcels_lng[pt] for pt in range(len(lm0.n_parcels_lng))}
leaves_by_cell = defaultdict(list)
for k in ctl: leaves_by_cell[(k[0], k[1])].append(k)
cache = {}
def leaf_records(k):
    if k not in cache:
        if len(cache) > 20000: cache.clear()
        bg = sec.split(fbytes(fctl, ctl[k]))["background"]; cache[k] = (bg, records(bg))
    return cache[k]
for kind in ("background", "background_boundary", "interior_cover"):
    R, n = load("output/scratch-39/dump_pre311", kind)
    lv, ix, iy = np.asarray(R["level"]), np.asarray(R["ix"]), np.asarray(R["iy"])
    win = np.flatnonzero((lv == 0) & (ix >= X0) & (ix < X1) & (iy >= Y0) & (iy < Y1))
    res = Counter(); prod_rows = []
    changed_cells = {(k[0], k[1]) for k in changed}
    for j in win:
        r = R[j]; c = (int(r["ix"]), int(r["iy"]))
        if c not in changed_cells: res["cell_unchanged_by_cf"] += 1; continue
        cand = leaves_by_cell[c]
        if len(cand) == 1: k = cand[0]
        else:
            if r["depth"] < 2: res["unmapped_depth"] += 1; continue
            sub = int(r["p1"]); pt = cand[0][2]
            k = (c[0], c[1], pt, sub % nxs[pt], sub // nxs[pt])
            if k not in ctl: res["unmapped_sub"] += 1; continue
        if k not in prod: res["leaf_unchanged_by_cf"] += 1; continue
        bg, recs = leaf_records(k); s = int(r["shape"]); vt = int(r["vert"])
        if not (0 <= s < len(recs)): res["shape_out_of_range"] += 1; continue
        if vt < 0:   # item-level row (interior_cover): no vertex; validate by record type code
            if recs[s][1] != int(r["code"]): res["type_mismatch"] += 1; continue
        else:
            vv = verts(bg, recs[s])
            if not (0 <= vt < len(vv)) or vv[vt] != (int(r["vx"]), int(r["vy"])): res["vertex_mismatch"] += 1; continue
        res["validated"] += 1
        if s in prod[k]:
            res["produced_by_65623"] += 1; prod_rows.append((c[0], c[1], k[3], k[4], s, vt, int(r["code"])))
        else: res["changed_leaf_other_record"] += 1
    out[kind] = {"rows_total": int(n), "rows_in_window": int(len(win)), **dict(res)}
    with open(f"{P}/produced_rows_{kind}.tsv", "w") as fh:
        fh.write("ix\tiy\tsub_ix\tsub_iy\tshape\tvert\tcode\n")
        for t in prod_rows: fh.write("\t".join(map(str, t)) + "\n")
    print(kind, out[kind], flush=True)
json.dump(out, open(P + "/join65623.json", "w"), indent=1); print("JOINDONE")
