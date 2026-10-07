#!/usr/bin/env python3
"""Plan 44 Phase 1 control: re-test plan 39 identity-proven sample with owner-exclusive.

≥99% of evaluable samples must agree (unique 33006aa producer + ≥1 owner-exclusive
vertex of that source under d35b565 present on 4ed9cd80, or byte-equal d35b565 clip).
Every disagreement is reported; systematic disagreement stops the phase.

Vertices come from old-disc leaf records (dump_pre311 is not retained on host).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import random
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
IDENTITY = OUT / "rows_identity_proven.tsv.gz"


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


def _rid(r):
    return r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=44)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    n = 12 if args.smoke else args.n

    os.environ.setdefault("TMPDIR", str(ROOT / "output/tmp-agent"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    print("compile probes…", flush=True)
    so_prod = compile_probe(CENC_PROD, PROBE_DIR / "probe_flex_prod_33006aa.so")
    so_excl = compile_probe(CENC_EXCL, PROBE_DIR / "probe_flex_excl_d35b565.so")
    probe_prod = load_probe(so_prod)
    probe_excl = load_probe(so_excl)

    print("load identity pool…", flush=True)
    pool = load_tsv(IDENTITY)
    # R01 failing keys for sampled leaves (identity+weak+none)
    r01_all = []
    for name in ("rows_identity_proven.tsv.gz", "rows_weak.tsv.gz", "rows_none.tsv.gz"):
        r01_all.extend(load_tsv(OUT / name))
    fe = load_fe()

    rng = random.Random(args.seed)
    by_code = defaultdict(list)
    for r in pool:
        by_code[r["code"]].append(r)
    sample = []
    codes = sorted(by_code)
    per = max(1, n // max(1, len(codes)))
    for c in codes:
        sample.extend(rng.sample(by_code[c], min(per, len(by_code[c]))))
    if len(sample) < n:
        seen = {(r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]) for r in sample}
        rest = [r for r in pool
                if (r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]) not in seen]
        sample.extend(rng.sample(rest, min(n - len(sample), len(rest))))
    sample = sample[:n]
    rng.shuffle(sample)
    print(f"sample={len(sample)} codes={Counter(r['code'] for r in sample)}", flush=True)

    sampled_cells = {(r["level"], r["ix"], r["iy"]) for r in sample}
    # R01 rows in sampled cells → failing verts looked up from disc later
    r01_in_cells = [r for r in r01_all if (r["level"], r["ix"], r["iy"]) in sampled_cells]
    print(f"r01 rows in sampled cells: {len(r01_in_cells)}", flush=True)

    print("open discs + spool (frames walk)…", flush=True)
    old_fr = frames(str(OLD_DISC), sampled_cells)
    new_fr = frames(str(NEW_DISC), sampled_cells)
    spool = SpoolReader(str(SPOOL))
    print(f"old leaves {len(old_fr)} new leaves {len(new_fr)}", flush=True)

    agree = disagree = skip = 0
    details = []
    by_leaf_rows = defaultdict(list)
    for r in sample:
        by_leaf_rows[leaf_key(r)].append(r)
    r01_by_leaf = defaultdict(list)
    for r in r01_in_cells:
        r01_by_leaf[leaf_key(r)].append(r)

    with open(OLD_DISC, "rb") as fo, open(NEW_DISC, "rb") as fn:
        for lk, rows in by_leaf_rows.items():
            level, ix, iy, path = lk
            cell = (level, ix, iy)
            if fe.get(cell, ("", "0"))[1] != "1":
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_footprints_changed"))
                continue
            if lk not in old_fr or lk not in new_fr:
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_leaf_missing"))
                continue
            if len(path) > 1:
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_divided_leaf"))
                continue

            old_recs = list(leaf_records(fo, old_fr[lk]))
            by_shape = {s: (code, wire, verts) for s, code, wire, verts in old_recs}
            new_recs = list(leaf_records(fn, new_fr[lk]))
            new_by_type_verts = defaultdict(set)
            new_wires = defaultdict(list)
            for _s, code, wire, verts in new_recs:
                new_by_type_verts[code].update((int(x), int(y)) for x, y in verts)
                new_wires[code].append(wire)

            # Failing verts per (shape, code) from R01 rows of this leaf
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

            print(f"  spool cands leaf {lk}…", flush=True)
            cands = list(spool_candidates(spool, level, ix, iy, rect, b4, cr, neighbourhood=1))
            print(f"  cands={len(cands)} rows={len(rows)}", flush=True)

            for r in rows:
                shape = r["shape"]
                if shape not in by_shape:
                    skip += 1
                    details.append((*_rid(r), "skip_shape_missing"))
                    continue
                code, wire, old_verts = by_shape[shape]
                if code != r["code"]:
                    skip += 1
                    details.append((*_rid(r), "skip_code_mismatch"))
                    continue
                status, pid = find_producer(
                    probe_prod, wire, cands, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                )
                if status != "unique":
                    disagree += 1
                    details.append((*_rid(r), f"disagree_producer_{status}"))
                    continue
                ring = next(rng for cid, rng in cands if cid == pid)
                sz, _nrec, blob_e = clip_ring(
                    probe_excl, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                )
                if sz <= 0:
                    disagree += 1
                    details.append((*_rid(r), f"disagree_source_removed_sz{sz}"))
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
                    src_verts, other, rect, failing=failing.get((shape, code), set()),
                )
                byte_hit = blob_e in new_wires.get(code, [])
                vert_hit = any(v in new_by_type_verts.get(code, ()) for v in excl)
                if byte_hit or vert_hit:
                    agree += 1
                    details.append((*_rid(r),
                                    f"agree_excl={len(excl)}_byte={int(byte_hit)}_vert={int(vert_hit)}"))
                else:
                    disagree += 1
                    details.append((*_rid(r), f"disagree_no_oe_excl={len(excl)}"))

    total = agree + disagree
    rate = (agree / total) if total else 0.0
    summary = {
        "sampled": len(sample), "agree": agree, "disagree": disagree, "skip": skip,
        "rate": round(rate, 6), "seed": args.seed, "n": n, "smoke": bool(args.smoke),
    }
    print("CONTROL", json.dumps(summary), flush=True)
    out = OUT / ("control_result_smoke.json" if args.smoke else "control_result.json")
    out.write_text(json.dumps({
        **summary,
        "details": [
            {"level": a, "ix": b, "iy": c, "shape": d, "vert": e, "code": f, "verdict": g}
            for a, b, c, d, e, f, g in details
        ],
    }, indent=1))
    (OUT / "control_result.txt").write_text(
        f"agree={agree} disagree={disagree} skip={skip} rate={rate:.6f} "
        f"n={len(sample)} seed={args.seed}\n"
        + "\n".join(f"{a}\t{b}\t{c}\t{d}\t{e}\t{f}\t{g}" for a, b, c, d, e, f, g in details)
        + "\n"
    )
    ok = rate >= 0.99 and total >= max(5, n // 4)
    print("CONTROL_OK" if ok else "CONTROL_FAIL", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
