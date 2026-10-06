"""Plan 39 P1 item 2 decode: in the 37 3-11 cells, old (87a01b14) vs new (013586b5) background sub-frames.
Claim tested: payload records are byte-identical; old declares physical-4096 in one unit; the new unit table splits it,
so the only K1-visible change is the 4096 formerly-unread records per wrapped element. Light: targeted preads only."""
import sys, os, json, hashlib
sys.path.insert(0, "parser")
from pathlib import Path
import importlib.util
OC = "docs/plans/04-c-core-orchestration/triage/oracle_chain/"
spec = importlib.util.spec_from_file_location("sections", OC + "hop_3_14/sections.py"); sec = importlib.util.module_from_spec(spec); spec.loader.exec_module(sec)
oc = sec.oc
from kiwiw import volume
from kiwiw.bitutils import u16 as U16
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record
cells = {(int(l.split("\t")[0]), int(l.split("\t")[1]), int(l.split("\t")[2])) for l in open("output/scratch-36/diff-3-11-au.cells.tsv").read().splitlines()[1:]}
def frames(path):
    out = {}
    with Path(path).open("rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]; ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {m.level: m for m in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]; lm = levels[bs.level]
            if lm.level != 0: continue
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng); bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size: continue
                bx = (bsx * nbx + bi % nbx) * nx; by = (bsy * nby + bi // nbx) * ny
                if not any(bx <= c[1] < bx + nx and by <= c[2] < by + ny for c in cells): continue
                root = parse_parcel_mgmt_record(oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                for x, y, leaf, entry in oc.tree_leaves(root, lm):
                    if (0, bx + x, by + y) not in cells: continue
                    buf = oc.read_exact(f, volume.getsector(entry.dsa, ss, ls), entry.size * ls)
                    out[(bx + x, by + y, ".".join(map(str, leaf)))] = buf[:U16(buf, 0) * 2]
    return out
def bg_elems(bg):
    """[(n_units, [(count,class)], record_region_bytes)] per element, physical walk by rec_len (not declared count)."""
    hlen = sec.u16(bg, 0) * 2; off = 2; els = []
    while off < hlen:
        po = sec.u16(bg, off) * 2; ps = sec.u16(bg, off + 2) * 2; off += 4
        if sec.u16(bg, off - 4) == 0xFFFF: els.append(None); continue
        n = sec.u16(bg, po); units = [(sec.u16(bg, po + 2 + 4 * i + 2) & 0xFFF, sec.u16(bg, po + 2 + 4 * i + 2) >> 14) for i in range(n)]
        r0 = po + 2 + 4 * n; end = po + ps; recs = []; p = r0
        while p < end:
            L = (sec.u16(bg, p) & 0xFFF) * 2
            if L == 0: break
            recs.append(bg[p:p + L]); p += L
        els.append((n, units, recs))
    return els
O, N = frames("output/scratch-36/G_pre311/ALLDATA.KWI"), frames("output/scratch-3-11/G_new/ALLDATA.KWI")
res = {"leaves_old": len(O), "leaves_new": len(N), "same_leaf_keys": sorted(O) == sorted(N), "elements": []}
ok = True; nonbg_same = True; extra_recs = 0; extra_vertices = 0
for k in sorted(O):
    so, sn = sec.split(O[k]), sec.split(N[k])
    for s in ("road", "name", "regions", "ext"):
        nonbg_same &= so[s] == sn[s]
    eo, en = bg_elems(so["background"]), bg_elems(sn["background"])
    if len(eo) != len(en): ok = False; continue
    for a, b in zip(eo, en):
        if a is None or b is None:
            ok &= a == b; continue
        if a[2] != b[2]: ok = False                     # record bytes identical (physical walk)
        if a[1] != b[1]:
            decl_old = sum(c for c, _ in a[1]); phys = len(a[2]); unread = phys - decl_old
            recs = a[2][decl_old:]                       # formerly unread records (past the wrapped declared count)
            nv = sum((sec.u16(r, 2) & 0x7FF) + 1 for r in recs)
            extra_recs += len(recs); extra_vertices += nv
            res["elements"].append({"leaf": k, "old_units": a[1], "new_units": b[1], "physical": phys, "decl_old": decl_old,
                                    "unread_old": unread, "unread_vertices": nv})
res.update({"record_bytes_identical": ok, "non_bg_sections_identical": nonbg_same, "wrapped_elements": len(res["elements"]),
            "unread_records_total": extra_recs, "unread_vertices_total": extra_vertices,
            "all_unread_4096": all(e["unread_old"] == 4096 for e in res["elements"])})
json.dump(res, open("output/scratch-39/wrap37.json", "w"), indent=1)
print({k: v for k, v in res.items() if k != "elements"})
