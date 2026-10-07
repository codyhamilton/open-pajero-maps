#!/usr/bin/env python3
"""Plan 44 Phase 2: decide every R-G5-4-a (weak) + joined R-G5-4-b (none) row under locked R=8.

Per row: unique-byte|unique-fragment producer via bbox-meet ∪ Moore(R=8), then OE/new-disc
limb → build:eo_bg_stitch, or a named residual (producer_home_outside_R_cap / ambiguous /
disagree_*). Cover unchanged.

After the mass pass, any producer_home_outside_R_cap rows get the Design right-censor
widen to R_widen=16 (residual set only) before final classification.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [
    str(ROOT / "parser"),
    str(ROOT / "parser/tools"),
    str(Path(__file__).resolve().parent),
]

from bg_owner_exclusive import (  # noqa: E402
    clip_ring,
    compile_probe,
    find_producer,
    identity_bearing_vertices,
    load_probe,
    owner_exclusive_vertices,
    wire_vertices,
)
from leaf_io import (  # noqa: E402
    cell_b4,
    frames,
    leaf_records,
    leaf_rect_raw,
    spool_candidates,
)
from kiwiw.spool import SpoolReader  # noqa: E402

OUT = Path(__file__).resolve().parent
OLD_DISC = ROOT / "output/scratch-36/G_pre311/ALLDATA.KWI"
NEW_DISC = ROOT / "output/scratch-14/G_new/ALLDATA.KWI"
SPOOL = ROOT / "output/extract_timing/spool"
CENC_PROD = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes/_cenc_33006aa.c")
CENC_EXCL = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes/_cenc_d35b565.c")
PROBE_DIR = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes")
FE_PATH = ROOT / "docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz"
LOCKED_R = 8


def load_tsv(path: Path):
    rows = []
    with gzip.open(path, "rt") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            d = dict(zip(header, line.rstrip("\n").split("\t")))
            rows.append({
                "level": int(d["level"]), "ix": int(d["ix"]), "iy": int(d["iy"]),
                "depth": int(d["depth"]), "p0": int(d["p0"]), "p1": int(d["p1"]),
                "p2": int(d["p2"]), "shape": int(d["shape"]), "vert": int(d["vert"]),
                "code": int(d["code"]),
            })
    return rows


def leaf_key(r):
    d = int(r["depth"])
    return (int(r["level"]), int(r["ix"]), int(r["iy"]),
            tuple(int(r[f"p{i}"]) for i in range(d)))


def load_fe():
    fe = {}
    with gzip.open(FE_PATH, "rt") as f:
        next(f)
        for line in f:
            x = line.split("\t")
            fe[(int(x[0]), int(x[1]), int(x[2]))] = (x[3], x[4])
    return fe


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--r", type=int, default=LOCKED_R, help="Locked Moore R (Design Decision 5)")
    ap.add_argument("--limit", type=int, default=0, help="Debug: first N rows only (0=all)")
    ap.add_argument("--smoke-leaves", type=int, default=0,
                    help="Debug: process only N distinct leaves")
    ap.add_argument("--out", type=Path, default=OUT / "phase2_decisions.tsv.gz")
    ap.add_argument("--summary", type=Path, default=OUT / "phase2_summary.json")
    args = ap.parse_args()
    R = int(args.r)

    os.environ.setdefault("TMPDIR", str(ROOT / "output/tmp-agent"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    print(f"compile probes… R={R}", flush=True)
    so_prod = compile_probe(CENC_PROD, PROBE_DIR / "probe_flex_prod_33006aa.so")
    so_excl = compile_probe(CENC_EXCL, PROBE_DIR / "probe_flex_excl_d35b565.so")
    probe_prod = load_probe(so_prod)
    probe_excl = load_probe(so_excl)

    print("load weak + none (R-G5-4-a/b)…", flush=True)
    weak = load_tsv(OUT / "rows_weak.tsv.gz")
    none = load_tsv(OUT / "rows_none.tsv.gz")
    # inventory_925: no per-row checker proofs → all none join test 2
    work = weak + none
    for r in weak:
        r["src"] = "weak"
    for r in none:
        r["src"] = "none"
    if args.limit:
        work = work[: args.limit]
    print(f"work={len(work)} (weak={len(weak)} none={len(none)})", flush=True)

    # Also load all R01 in work cells for failing-vert context
    identity = load_tsv(OUT / "rows_identity_proven.tsv.gz")
    fe = load_fe()
    cells = {(r["level"], r["ix"], r["iy"]) for r in work}
    if args.smoke_leaves:
        # take first N leaves' rows only
        leaf_order = []
        seen = set()
        for r in work:
            lk = leaf_key(r)
            if lk not in seen:
                seen.add(lk)
                leaf_order.append(lk)
            if len(leaf_order) >= args.smoke_leaves:
                break
        keep = set(leaf_order)
        work = [r for r in work if leaf_key(r) in keep]
        cells = {(r["level"], r["ix"], r["iy"]) for r in work}
        print(f"smoke-leaves={args.smoke_leaves} → rows={len(work)} cells={len(cells)}", flush=True)

    r01_all = identity + weak + none
    r01_in = [r for r in r01_all if (r["level"], r["ix"], r["iy"]) in cells]
    print(f"cells={len(cells)} r01_in_cells={len(r01_in)}", flush=True)

    print("frames walk…", flush=True)
    old_fr = frames(str(OLD_DISC), cells)
    new_fr = frames(str(NEW_DISC), cells)
    spool = SpoolReader(str(SPOOL))
    print(f"old leaves {len(old_fr)} new leaves {len(new_fr)}", flush=True)

    by_leaf = defaultdict(list)
    for r in work:
        by_leaf[leaf_key(r)].append(r)
    r01_by_leaf = defaultdict(list)
    for r in r01_in:
        r01_by_leaf[leaf_key(r)].append(r)

    decisions = []
    class_counts = Counter()
    n_done = 0
    n_leaves = 0

    with open(OLD_DISC, "rb") as fo, open(NEW_DISC, "rb") as fn, \
            gzip.open(args.out, "wt") as outfh:
        outfh.write("level\tix\tiy\tdepth\tshape\tvert\tcode\tsrc\tdecision\t"
                    "producer_class\trecover_r\tdx\tdy\tn_excl\tn_ib\textra\n")
        for lk, rows in by_leaf.items():
            n_leaves += 1
            level, ix, iy, path = lk
            cell = (level, ix, iy)

            def emit(r, decision, prod_class="", recover_r="", dx="", dy="",
                     n_excl="", n_ib="", extra=None):
                nonlocal n_done
                class_counts[decision] += 1
                n_done += 1
                ex = json.dumps(extra or {}, separators=(",", ":"))
                outfh.write(
                    f"{r['level']}\t{r['ix']}\t{r['iy']}\t{r['depth']}\t{r['shape']}\t"
                    f"{r['vert']}\t{r['code']}\t{r['src']}\t{decision}\t{prod_class}\t"
                    f"{recover_r}\t{dx}\t{dy}\t{n_excl}\t{n_ib}\t{ex}\n"
                )
                if n_done % 2000 == 0:
                    outfh.flush()
                    print(f"  progress rows={n_done} leaves={n_leaves} "
                          f"top={class_counts.most_common(5)}", flush=True)

            if fe.get(cell, ("", "0"))[1] != "1":
                for r in rows:
                    emit(r, "skip_footprints_changed")
                continue
            if lk not in old_fr or lk not in new_fr:
                for r in rows:
                    emit(r, "skip_leaf_missing")
                continue
            if len(path) > 1:
                for r in rows:
                    emit(r, "skip_divided_leaf")
                continue

            old_recs = list(leaf_records(fo, old_fr[lk]))
            by_shape = {s: (code, wire, verts) for s, code, wire, verts in old_recs}
            new_recs = list(leaf_records(fn, new_fr[lk]))
            new_by_type_verts = defaultdict(set)
            new_wires = defaultdict(list)
            for _s, code, wire, verts in new_recs:
                new_by_type_verts[code].update((int(x), int(y)) for x, y in verts)
                new_wires[code].append(wire)

            failing = defaultdict(set)
            for rr in r01_by_leaf.get(lk, []):
                sh = rr["shape"]
                if sh not in by_shape:
                    continue
                _c, _w, verts = by_shape[sh]
                vi = rr["vert"]
                if 0 <= vi < len(verts):
                    x, y = verts[vi]
                    failing[(sh, rr["code"])].add((int(x), int(y)))

            b4, cr = cell_b4(level, ix, iy)
            b4_enc = (0.0, float(cr), 0.0, float(cr))
            rect = leaf_rect_raw(level, len(path))
            cands = list(spool_candidates(spool, level, ix, iy, rect, b4, cr,
                                          neighbourhood=R))

            for r in rows:
                shape, code = r["shape"], r["code"]
                if shape not in by_shape:
                    emit(r, "skip_shape_missing")
                    continue
                c_shape, wire, old_verts = by_shape[shape]
                if c_shape != code:
                    emit(r, "skip_code_mismatch")
                    continue
                fail_set = failing.get((shape, code), set())
                ib = identity_bearing_vertices(old_verts, rect, failing=fail_set)
                status, pid = find_producer(
                    probe_prod, wire, cands, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                    record_verts=old_verts, failing=fail_set,
                )
                if status == "producer-ambiguous":
                    emit(r, "producer_ambiguous", n_ib=len(ib),
                         extra={"n_cands": len(cands)})
                    continue
                if status not in ("unique-byte", "unique-fragment"):
                    # Residual at locked R — widen pass later
                    emit(r, "producer_home_outside_R_cap", prod_class=status,
                         recover_r=R, n_ib=len(ib),
                         extra={"max_radius": R, "n_cands": len(cands), "n_spool": len(cands)})
                    continue

                hx, hy = int(pid[0]), int(pid[1])
                dx, dy = hx - ix, hy - iy
                ring = next(rng for cid, rng in cands if cid == pid)
                sz, _nrec, blob_e = clip_ring(
                    probe_excl, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                )
                if sz <= 0:
                    emit(r, "disagree_source_removed", prod_class=status,
                         recover_r=R, dx=dx, dy=dy, n_ib=len(ib),
                         extra={"sz": sz})
                    continue
                src_verts = [(int(x), int(y)) for x, y in wire_vertices(blob_e)]
                other = []
                for cid, oring in cands:
                    if cid == pid:
                        continue
                    s2, _, b2 = clip_ring(
                        probe_excl, oring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                    )
                    if s2 > 0:
                        other.append([(int(x), int(y)) for x, y in wire_vertices(b2)])
                excl = owner_exclusive_vertices(
                    src_verts, other, rect, failing=fail_set,
                )
                byte_hit = blob_e in new_wires.get(code, [])
                vert_hit = any(v in new_by_type_verts.get(code, ()) for v in excl)
                if byte_hit or vert_hit:
                    emit(r, "build:eo_bg_stitch", prod_class=status,
                         recover_r=R, dx=dx, dy=dy, n_excl=len(excl), n_ib=len(ib),
                         extra={"byte": int(byte_hit), "vert": int(vert_hit),
                                "producer_home": [hx, hy]})
                else:
                    emit(r, "disagree_no_oe", prod_class=status,
                         recover_r=R, dx=dx, dy=dy, n_excl=len(excl), n_ib=len(ib),
                         extra={"producer_home": [hx, hy]})

    summary = {
        "schema": 1,
        "locked_R": R,
        "n_work": len(work),
        "n_decisions": n_done,
        "n_leaves": n_leaves,
        "class_counts": dict(class_counts),
        "out": str(args.out),
        "inventory_925_joined_all": True,
    }
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    print("SUMMARY", json.dumps(summary), flush=True)
    print("MASS_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
