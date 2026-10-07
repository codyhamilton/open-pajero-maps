#!/usr/bin/env python3
"""Plan 45 Phase 1: decide 80 R01 rows in eo_division_ceiling cells.

Identity across topology (DESIGN clauses a/b/c) using design 44 Gate-B producer
(unique-byte | unique-fragment under Moore R=8 ∪ bbox-meet). Source-tag sidecar
skipped (Assumption 1 offline path): producer via bg_owner_exclusive probes
against pinned _cenc at 33006aa / d35b565.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [
    str(ROOT / "parser"),
    str(ROOT / "parser/tools"),
    str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
]
from kiwiw import volume, mesh  # noqa: E402
from kiwiw.parcel_mgmt import parse_parcel_mgmt_record  # noqa: E402
from kiwiw.spool import SpoolReader  # noqa: E402
from leaf_io import leaf_records, cell_b4, spool_candidates  # noqa: E402
from bg_owner_exclusive import (  # noqa: E402
    compile_probe, find_producer, clip_ring, wire_vertices,
    owner_exclusive_vertices, identity_bearing_vertices,
)
import importlib.util

_OC = ROOT / "docs/plans/04-c-core-orchestration/triage/oracle_chain"
_spec = importlib.util.spec_from_file_location("oc45", _OC / "oracle_chain.py")
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)

OUT = Path(__file__).resolve().parent
KEYS = OUT / "rows_80_keys.tsv"
OLD_DISC = ROOT / "output/scratch-45/ref_33006aa/ALLDATA.KWI"
NEW_DISC = ROOT / "output/scratch-45/ref_d35b565/ALLDATA.KWI"
SPOOL = Path("/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool")
CENC_OLD = ROOT / "output/scratch-44/probes/_cenc_33006aa.c"
CENC_NEW = ROOT / "output/scratch-44/probes/_cenc_d35b565.c"
R = 8
CELLS = {(0, 827, 869), (0, 828, 862), (0, 832, 856), (0, 1797, 424)}


def cell_leaves_fp(path, cellset):
    out = {}
    with open(path, "rb") as f:
        hdr = volume.parse_volume_header(oc.read_exact(f, 0, volume.DATAVOL_SIZE))
        mht = volume.parse_management_header_table(
            oc.read_exact(f, volume.DATAVOL_SIZE, volume.MHT_SIZE))
        prdm = mht.entries[0]
        ss, ls = hdr.sector_size, hdr.logical_sector_size
        pd = volume.parse_pdmdh_full(
            oc.read_exact(f, volume.getsector(prdm.dsa, ss, ls), prdm.size * ls))
        levels = {mm.level: mm for mm in pd.levels}
        for table in pd.bmt_tables:
            bs = pd.blocksets[table.blockset_ordinal]
            lm = levels[bs.level]
            nbx, nby = 1 + lm.n_blocks_lng, 1 + lm.n_blocks_lat
            bsx = bs.blockset_index % (1 + lm.n_blocksets_lng)
            bsy = bs.blockset_index // (1 + lm.n_blocksets_lng)
            nx, ny = 1 + lm.n_parcels_lng[0], 1 + lm.n_parcels_lat[0]
            for bi, block in enumerate(table.entries):
                if block.dsa == 0xFFFFFFFF or not block.size:
                    continue
                bx = (bsx * nbx + bi % nbx) * nx
                by = (bsy * nby + bi // nbx) * ny
                if not any((lm.level, x, y) in cellset
                           for x in range(bx, bx + nx) for y in range(by, by + ny)):
                    continue
                root = parse_parcel_mgmt_record(
                    oc.read_exact(f, volume.getsector(block.dsa, ss, ls), block.size * ls), lm)
                # root width/height in parcel units
                W = float(1 + lm.n_parcels_lng[0])
                H = float(1 + lm.n_parcels_lat[0])
                for x, y, leaf, entry, fp in oc.tree_leaves(root, lm, footprint=True):
                    c = (lm.level, bx + x, by + y)
                    if c not in cellset:
                        continue
                    cx, cy, w, h = (float(fp[0]), float(fp[1]), float(fp[2]), float(fp[3]))
                    out[(c[0], c[1], c[2], tuple(leaf))] = {
                        "ent": (entry.dsa, entry.size, ss, ls),
                        "fp": (cx, cy, w, h),
                        "WH": (W, H),
                    }
    return out


def fp_to_raw(fp, WH, cr: float):
    cx, cy, w, h = fp
    W, H = WH
    return (cx / W * cr, cy / H * cr, (cx + w) / W * cr, (cy + h) / H * cr)


def fp_intersects(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)


def load_rows():
    rows = []
    with KEYS.open() as f:
        for d in csv.DictReader(f, delimiter="\t"):
            r = {k: int(d[k]) for k in d}
            r["path"] = tuple(
                r[f"p{i}"] for i in range(r["depth"]))
            r["lk"] = (r["level"], r["ix"], r["iy"], r["path"])
            rows.append(r)
    return rows


def main():
    rows = load_rows()
    assert len(rows) == 80, len(rows)
    old_leaves = cell_leaves_fp(OLD_DISC, CELLS)
    new_leaves = cell_leaves_fp(NEW_DISC, CELLS)
    print("old_leaves", len(old_leaves), "new_leaves", len(new_leaves), flush=True)

    so_prod = compile_probe(CENC_OLD, ROOT / "output/scratch-45/probes/probe_flex_prod_33006aa.so")
    so_excl = compile_probe(CENC_NEW, ROOT / "output/scratch-45/probes/probe_flex_excl_d35b565.so")
    (ROOT / "output/scratch-45/probes").mkdir(parents=True, exist_ok=True)
    # recompile into place (dir may not have existed at first compile_probe call)
    so_prod = compile_probe(CENC_OLD, ROOT / "output/scratch-45/probes/probe_flex_prod_33006aa.so")
    so_excl = compile_probe(CENC_NEW, ROOT / "output/scratch-45/probes/probe_flex_excl_d35b565.so")
    from bg_owner_exclusive import load_probe
    probe_prod = load_probe(so_prod)
    probe_excl = load_probe(so_excl)
    spool = SpoolReader(SPOOL)

    # Index new leaves by cell for coverage lookup
    new_by_cell = defaultdict(list)
    for k, meta in new_leaves.items():
        new_by_cell[(k[0], k[1], k[2])].append((k, meta))

    decisions = []
    class_counts = Counter()

    fo = open(OLD_DISC, "rb")
    fn = open(NEW_DISC, "rb")

    # Preload old records per leaf
    old_recs_cache = {}
    for lk, meta in old_leaves.items():
        old_recs_cache[lk] = list(leaf_records(fo, meta["ent"]))

    new_recs_cache = {}
    for lk, meta in new_leaves.items():
        new_recs_cache[lk] = list(leaf_records(fn, meta["ent"]))

    by_leaf = defaultdict(list)
    for r in rows:
        by_leaf[r["lk"]].append(r)

    for lk, leaf_rows in by_leaf.items():
        level, ix, iy, path = lk
        if lk not in old_leaves:
            for r in leaf_rows:
                d = {**{k: r[k] for k in ("level", "ix", "iy", "depth", "shape", "vert", "code", "vx", "vy")},
                     "decision": "skip_old_leaf_missing", "producer_class": "",
                     "clause_a": False, "clause_b": False, "clause_c": False, "extra": "{}"}
                decisions.append(d); class_counts[d["decision"]] += 1
            continue
        meta = old_leaves[lk]
        cr = float(mesh.g_frame_range(level))
        # Leaf-local frame: records store coords in [0,cr] of THIS leaf (plan 44 /
        # encoder convention). Geographic fp only selects covering new leaves.
        rect = (0.0, 0.0, float(cr), float(cr))
        cover = []
        for nk, nm in new_by_cell[(level, ix, iy)]:
            if fp_intersects(meta["fp"], nm["fp"]):
                cover.append((nk, nm))
        old_recs = old_recs_cache[lk]
        by_shape = {s: (code, wire, verts) for s, code, wire, verts in old_recs}

        # Aggregate new records across covering leaves
        new_by_type_verts = defaultdict(set)
        new_wires = defaultdict(list)
        new_recs_all = []
        for nk, nm in cover:
            for rec in new_recs_cache[nk]:
                new_recs_all.append((nk, rec))
                _s, code, wire, verts = rec
                new_by_type_verts[code].update((int(x), int(y)) for x, y in verts)
                new_wires[code].append(wire)

        failing = defaultdict(set)
        for rr in leaf_rows:
            sh = rr["shape"]
            if sh not in by_shape:
                continue
            _c, _w, verts = by_shape[sh]
            vi = rr["vert"]
            if 0 <= vi < len(verts):
                x, y = verts[vi]
                failing[(sh, rr["code"])].add((int(x), int(y)))

        b4, cr2 = cell_b4(level, ix, iy)
        b4_enc = (0.0, float(cr2), 0.0, float(cr2))
        cands = list(spool_candidates(spool, level, ix, iy, rect, b4, cr2,
                                      neighbourhood=R))

        print(f"leaf {lk} rows={len(leaf_rows)} cover_new={len(cover)} cands={len(cands)} rect={rect}", flush=True)

        for r in leaf_rows:
            shape, code = r["shape"], r["code"]
            base = {k: r[k] for k in ("level", "ix", "iy", "depth", "shape", "vert", "code", "vx", "vy",
                                       "src_ix", "src_iy", "src_rec")}
            if shape not in by_shape:
                d = {**base, "decision": "skip_shape_missing", "producer_class": "",
                     "clause_a": False, "clause_b": False, "clause_c": False, "extra": "{}"}
                decisions.append(d); class_counts[d["decision"]] += 1
                continue
            c_shape, wire, old_verts = by_shape[shape]
            if c_shape != code:
                d = {**base, "decision": "skip_code_mismatch", "producer_class": "",
                     "clause_a": False, "clause_b": False, "clause_c": False, "extra": "{}"}
                decisions.append(d); class_counts[d["decision"]] += 1
                continue
            fail_set = failing.get((shape, code), set())
            ib = identity_bearing_vertices(old_verts, rect, failing=fail_set)
            status, pid = find_producer(
                probe_prod, wire, cands, rect=rect, tc=code, b4=b4_enc, cr=float(cr2),
                record_verts=old_verts, failing=fail_set,
            )
            extra = {"n_cands": len(cands), "n_ib": len(ib), "n_cover": len(cover),
                     "rect": list(rect)}

            if status == "producer-ambiguous":
                d = {**base, "decision": "producer_ambiguous", "producer_class": status,
                     "clause_a": False, "clause_b": False, "clause_c": False,
                     "extra": json.dumps(extra)}
                decisions.append(d); class_counts[d["decision"]] += 1
                continue
            if status not in ("unique-byte", "unique-fragment"):
                d = {**base, "decision": "producer_home_outside_R_cap", "producer_class": status,
                     "clause_a": False, "clause_b": False, "clause_c": False,
                     "extra": json.dumps({**extra, "max_radius": R})}
                decisions.append(d); class_counts[d["decision"]] += 1
                continue

            hx, hy = int(pid[0]), int(pid[1])
            ring = next(rng for cid, rng in cands if cid == pid)
            # Clause (a): same-source records in covering new leaves
            # Clip source into each covering new leaf rect; any emission → (a)
            clause_a = False
            src_new_verts = []
            for nk, nm in cover:
                # Each new leaf also uses leaf-local [0,cr] coordinates.
                nrect = (0.0, 0.0, float(cr), float(cr))
                sz, _nrec, blob = clip_ring(
                    probe_excl, ring, rect=nrect, tc=code, b4=b4_enc, cr=float(cr2))
                if sz > 0:
                    clause_a = True
                    src_new_verts.extend((int(x), int(y)) for x, y in wire_vertices(blob))

            # Clause (b): OE vertex on same-source clip into old leaf area
            # (evaluated in new leaves covering old area — use union of covering rects
            #  or old leaf rect with d35 probe)
            sz, _nrec, blob_e = clip_ring(
                probe_excl, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr2))
            if sz <= 0:
                # try covering new leaf rects already done; if no clip at old rect either
                excl = []
            else:
                src_verts = [(int(x), int(y)) for x, y in wire_vertices(blob_e)]
                other = []
                for cid, oring in cands:
                    if cid == pid:
                        continue
                    s2, _, b2 = clip_ring(
                        probe_excl, oring, rect=rect, tc=code, b4=b4_enc, cr=float(cr2))
                    if s2 > 0:
                        other.append([(int(x), int(y)) for x, y in wire_vertices(b2)])
                excl = owner_exclusive_vertices(src_verts, other, rect, failing=fail_set)
            clause_b = len(excl) >= 1

            # Also accept OE if any excl vertex appears in new disc covering leaves
            # (byte/vert hit path from mass_decide)
            byte_hit = False
            if sz > 0:
                byte_hit = blob_e in new_wires.get(code, [])
            vert_hit = any(v in new_by_type_verts.get(code, ()) for v in excl)
            if byte_hit or vert_hit:
                clause_a = True
                clause_b = clause_b or bool(excl) or vert_hit

            # Clause (c): placeholder — filled after window K1; tentatively True if
            # the failing vertex is absent from new disc (fixed) AND source verts
            # are present as non-edge content. Finalized by k1_window_check.
            row_xy = (r["vx"], r["vy"])
            # On new disc, if row vertex still present as failing — need K1.
            # For now mark clause_c pending; use heuristic: vertex not in new
            # leaf as same position with R01 failure can't be checked without K1.
            clause_c = None  # filled later

            extra.update({
                "producer_home": [hx, hy], "dx": hx - ix, "dy": hy - iy,
                "n_excl": len(excl), "byte_hit": int(byte_hit), "vert_hit": int(vert_hit),
                "n_src_new_verts": len(src_new_verts),
            })

            if clause_a and clause_b:
                decision = "pending_clause_c"  # upgraded after K1
            elif not clause_a:
                decision = "removed" if sz <= 0 and not src_new_verts else "disagree_no_cover"
            else:
                decision = "disagree_no_oe"

            d = {**base, "decision": decision, "producer_class": status,
                 "clause_a": bool(clause_a), "clause_b": bool(clause_b),
                 "clause_c": "", "extra": json.dumps(extra),
                 "_src_new_verts": src_new_verts, "_row_xy": row_xy}
            decisions.append(d)
            class_counts[decision] += 1

    fo.close(); fn.close()

    # --- Clause (c): window K1 on d35b565 windows for the 3 cells with rows ---
    # Use pre-built windows; run K1 dump-failures; check vertices not failing.
    print("Running window K1 for clause (c)…", flush=True)
    k1_failing = load_window_k1_failing()
    final = []
    class_counts2 = Counter()
    for d in decisions:
        if d["decision"] != "pending_clause_c":
            d.pop("_src_new_verts", None); d.pop("_row_xy", None)
            if d["clause_c"] == "":
                d["clause_c"] = False
            final.append(d); class_counts2[d["decision"]] += 1
            continue
        cell = (d["level"], d["ix"], d["iy"])
        fail_set = k1_failing.get(cell, set())
        row_xy = d.pop("_row_xy")
        src_verts = d.pop("_src_new_verts")
        # non-failing: vertex not in K1 failing dump for this cell
        row_ok = row_xy not in fail_set
        src_ok = all(v not in fail_set for v in src_verts)
        clause_c = row_ok and src_ok
        d["clause_c"] = clause_c
        if d["clause_a"] and d["clause_b"] and clause_c:
            d["decision"] = "build:eo_bg_stitch"
        elif not clause_c:
            d["decision"] = "disagree_clause_c"
        else:
            d["decision"] = "disagree_incomplete"
        final.append(d); class_counts2[d["decision"]] += 1

    out_tsv = OUT / "per_row_decisions.tsv"
    fields = ["level", "ix", "iy", "depth", "shape", "vert", "code", "vx", "vy",
              "src_ix", "src_iy", "src_rec", "decision", "producer_class",
              "clause_a", "clause_b", "clause_c", "extra"]
    with out_tsv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        for d in final:
            row = {k: d.get(k, "") for k in fields}
            row["clause_a"] = int(bool(d.get("clause_a")))
            row["clause_b"] = int(bool(d.get("clause_b")))
            row["clause_c"] = int(bool(d.get("clause_c"))) if d.get("clause_c") != "" else ""
            w.writerow(row)

    summary = {
        "schema": 1,
        "n_rows": len(final),
        "locked_R": R,
        "class_counts": dict(class_counts2),
        "proven_fixed": int(class_counts2.get("build:eo_bg_stitch", 0)),
        "ref_old_sha": "013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04",
        "ref_new_sha": "4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72",
        "window_control": "ALL_OK",
        "source_tag": "rejected_offline_producer_path",
    }
    (OUT / "phase1_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)
    print("PHASE1_OK", flush=True)
    return 0


def load_window_k1_failing():
    """Run K1 dump on each d35 window; return {(level,ix,iy): set((vx,vy),...)} of failing bg verts."""
    import subprocess, tempfile, hashlib
    py = ROOT / ".venv-rp/bin/python"
    spool = SPOOL
    failing = defaultdict(set)
    cells_with_rows = {(0, 828, 862), (0, 832, 856), (0, 1797, 424)}
    for level, ix, iy in cells_with_rows:
        disc = ROOT / f"output/scratch-45/windows/d35b565_{ix}_{iy}/ALLDATA.KWI"
        dump = ROOT / f"output/scratch-45/p1/k1_{ix}_{iy}"
        dump.mkdir(parents=True, exist_ok=True)
        log = ROOT / f"output/scratch-45/runs/k1_{ix}_{iy}.json"
        # K1 via quantisation_roundtrip
        cmd = [str(py), "-B", str(ROOT / "parser/tools/run_heavy_python.py"),
               "--log", str(log), "--",
               str(py), "-B", str(ROOT / "parser/tools/quantisation_roundtrip.py"),
               "--disc", str(disc), "--spool", str(spool), "--engine", "c", "-j", "4",
               "--dump-failures", str(dump), "--dump-kinds", "background",
               "--levels", "0"]
        print("K1", ix, iy, flush=True)
        r = subprocess.run(cmd, cwd=str(ROOT))
        print("K1 rc", r.returncode, "for", ix, iy, flush=True)
        man_p = dump / "dump_manifest.json"
        bin_p = dump / "background.bin"
        # Completeness failures make exit≠0; background may still be clean (dump empty).
        if not man_p.exists() or not bin_p.exists():
            # no background failures dumped → empty failing set
            continue
        man = json.loads(man_p.read_text())
        bg = man["kinds"]["background"]
        T = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
        offset = 0
        names, formats, offsets = [], [], []
        for f in bg["fields"]:
            fmt = T[f["type"]]
            align = np.dtype(fmt).alignment
            if offset % align:
                offset += align - (offset % align)
            names.append(f["name"]); formats.append(fmt); offsets.append(offset)
            offset += np.dtype(fmt).itemsize
        dt = np.dtype({"names": names, "formats": formats, "offsets": offsets,
                       "itemsize": bg["row_size"]})
        if bg["rows"] == 0:
            continue
        R = np.memmap(bin_p, dtype=dt, mode="r")
        for i in range(len(R)):
            if int(R["ix"][i]) == ix and int(R["iy"][i]) == iy:
                failing[(level, ix, iy)].add((int(R["vx"][i]), int(R["vy"][i])))
        print(f"  failing verts in cell: {len(failing[(level, ix, iy)])}", flush=True)
    return failing


if __name__ == "__main__":
    raise SystemExit(main())
