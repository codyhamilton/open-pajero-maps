#!/usr/bin/env python3
"""Plan 44 option (c): proven-fixed OE path for widen@16 recovers.

Widen recovers (unique-byte|unique-fragment) → OE/new-disc limb like mass_decide:
  pass → build:eo_bg_stitch with recover_r in 9..16
  fail → disagree_no_oe
Rewrites matching producer_home_outside_R_cap rows in the decisions TSV.
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
    identity_bearing_vertices,
    load_probe,
    owner_exclusive_vertices,
    wire_vertices,
)
from leaf_io import (  # noqa: E402
    cell_b4,
    clear_spool_caches,
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
CENC_EXCL = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes/_cenc_d35b565.c")
PROBE_DIR = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes")
FE_PATH = ROOT / "docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz"


def load_tsv(path: Path):
    rows = []
    with gzip.open(path, "rt") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            d = dict(zip(header, line.rstrip("\n").split("\t")))
            rows.append({
                "level": int(d["level"]), "ix": int(d["ix"]), "iy": int(d["iy"]),
                "depth": int(d["depth"]), "p0": int(d.get("p0") or 0),
                "p1": int(d.get("p1") or 0), "p2": int(d.get("p2") or 0),
                "shape": int(d["shape"]), "vert": int(d["vert"]),
                "code": int(d["code"]),
            })
    return rows


def load_fe():
    fe = {}
    with gzip.open(FE_PATH, "rt") as f:
        next(f)
        for line in f:
            x = line.split("\t")
            fe[(int(x[0]), int(x[1]), int(x[2]))] = (x[3], x[4])
    return fe


def load_decisions(path: Path):
    with gzip.open(path, "rt") as f:
        hdr = f.readline().rstrip("\n").split("\t")
        rows = [dict(zip(hdr, line.rstrip("\n").split("\t"))) for line in f]
    return hdr, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", type=Path, required=True)
    ap.add_argument("--widen-json", type=Path, required=True)
    ap.add_argument("--out-decisions", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--cache-clear-every", type=int, default=20)
    args = ap.parse_args()

    os.environ.setdefault("TMPDIR", str(ROOT / "output/tmp-agent"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    widen = json.loads(args.widen_json.read_text())
    recovers = [r for r in widen["results"]
                if r["verdict"] in ("unique-byte", "unique-fragment")]
    print(f"proven-fixed targets={len(recovers)}", flush=True)
    if not recovers:
        args.out_json.write_text(json.dumps({
            "schema": 1, "n_targets": 0, "n_stitch": 0, "n_disagree_no_oe": 0,
            "n_skip": 0, "n_updates": 0,
        }, indent=2) + "\n")
        print("PROVEN_FIXED_EMPTY", flush=True)
        return 0

    hdr, dec_rows = load_decisions(args.decisions)
    outside_idx = {}
    for i, dr in enumerate(dec_rows):
        if dr["decision"] != "producer_home_outside_R_cap":
            continue
        k = (int(dr["level"]), int(dr["ix"]), int(dr["iy"]),
             int(dr["shape"]), int(dr["vert"]), int(dr["code"]))
        outside_idx[k] = i

    work = []
    for r in recovers:
        k = (int(r["level"]), int(r["ix"]), int(r["iy"]),
             int(r["shape"]), int(r["vert"]), int(r["code"]))
        if k not in outside_idx:
            continue
        work.append((r, outside_idx[k]))
    print(f"matched outside rows={len(work)}", flush=True)

    cells = {(int(r["level"]), int(r["ix"]), int(r["iy"])) for r, _ in work}
    print(f"compile probes… cells={len(cells)}", flush=True)
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    probe_excl = load_probe(compile_probe(CENC_EXCL, PROBE_DIR / "probe_flex_excl_d35b565.so"))

    fe = load_fe()
    # R01 failing context for OE limb (same sources as mass_decide)
    identity = load_tsv(OUT / "rows_identity_proven.tsv.gz")
    weak = load_tsv(OUT / "rows_weak.tsv.gz")
    none = load_tsv(OUT / "rows_none.tsv.gz")
    r01_in = [r for r in (identity + weak + none)
              if (r["level"], r["ix"], r["iy"]) in cells]
    r01_by_cell = defaultdict(list)
    for r in r01_in:
        r01_by_cell[(r["level"], r["ix"], r["iy"])].append(r)

    print("frames walk…", flush=True)
    old_fr = frames(str(OLD_DISC), cells)
    new_fr = frames(str(NEW_DISC), cells)
    spool = SpoolReader(str(SPOOL))
    print(f"old leaves {len(old_fr)} new leaves {len(new_fr)}", flush=True)

    by_cell = defaultdict(list)
    for item in work:
        r, idx = item
        by_cell[(int(r["level"]), int(r["ix"]), int(r["iy"]))].append(item)

    n_stitch = n_oe = n_src = n_skip = n_fe = n_div = 0
    updates = []
    n_cells_done = 0

    with open(OLD_DISC, "rb") as fo, open(NEW_DISC, "rb") as fn:
        for (level, ix, iy), group in by_cell.items():
            n_cells_done += 1
            if args.cache_clear_every and n_cells_done % args.cache_clear_every == 0:
                clear_spool_caches()
                print(f"  cache_clear after cells={n_cells_done} "
                      f"stitch={n_stitch} oe={n_oe} skip={n_skip}", flush=True)

            cell = (level, ix, iy)
            if fe.get(cell, ("", "0"))[1] != "1":
                n_fe += len(group)
                n_skip += len(group)
                print(f"  skip fe cell {cell} n={len(group)}", flush=True)
                continue

            # Discover undivided / depth-1 leaves for this cell
            leaf_keys = [lk for lk in old_fr if lk[0] == level and lk[1] == ix and lk[2] == iy]
            # Prefer path len <= 1 (mass skips len>1)
            leaf_keys = [lk for lk in leaf_keys if len(lk[3]) <= 1]
            if not leaf_keys:
                n_skip += len(group)
                print(f"  no leaf keys {cell}", flush=True)
                continue

            # Build shape→(code,wire,verts,path) across allowed leaves; prefer single leaf
            by_shape = {}
            new_wires = defaultdict(list)
            new_by_type_verts = defaultdict(set)
            path_for_shape = {}
            for lk in leaf_keys:
                if lk not in new_fr:
                    continue
                path = lk[3]
                if len(path) > 1:
                    n_div += 1
                    continue
                for sh, code, wire, verts in leaf_records(fo, old_fr[lk]):
                    by_shape[sh] = (code, wire, verts, path)
                    path_for_shape[sh] = path
                for sh, code, wire, verts in leaf_records(fn, new_fr[lk]):
                    new_wires[code].append(wire)
                    new_by_type_verts[code].update((int(x), int(y)) for x, y in verts)

            if not by_shape:
                n_skip += len(group)
                print(f"  no shapes {cell}", flush=True)
                continue

            failing = defaultdict(set)
            for rr in r01_by_cell.get(cell, []):
                sh = rr["shape"]
                if sh not in by_shape:
                    continue
                _c, _w, verts, _p = by_shape[sh]
                vi = rr["vert"]
                if 0 <= vi < len(verts):
                    x, y = verts[vi]
                    failing[(sh, rr["code"])].add((int(x), int(y)))

            b4, cr = cell_b4(level, ix, iy)
            b4_enc = (0.0, float(cr), 0.0, float(cr))

            for r, idx in group:
                shape, code = int(r["shape"]), int(r["code"])
                if shape not in by_shape:
                    n_skip += 1
                    continue
                c_shape, wire, old_verts, path = by_shape[shape]
                if c_shape != code:
                    n_skip += 1
                    continue
                if len(path) > 1:
                    n_div += 1
                    n_skip += 1
                    continue

                rect = leaf_rect_raw(level, len(path))
                recover_r = int(r.get("recover_r") or 16)
                hx, hy = int(r["producer_home"][0]), int(r["producer_home"][1])
                pid = (hx, hy)
                dx, dy = hx - ix, hy - iy
                fail_set = failing.get((shape, code), set())
                ib = identity_bearing_vertices(old_verts, rect, failing=fail_set)

                cands = list(spool_candidates(
                    spool, level, ix, iy, rect, b4, cr, neighbourhood=recover_r,
                ))
                ring = next((rng for cid, rng in cands if cid == pid), None)
                if ring is None:
                    ring = next(
                        (rng for cid, rng in cands
                         if int(cid[0]) == hx and int(cid[1]) == hy),
                        None,
                    )
                if ring is None:
                    n_skip += 1
                    continue

                sz, _nrec, blob_e = clip_ring(
                    probe_excl, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                )
                if sz <= 0:
                    decision = "disagree_source_removed"
                    n_src += 1
                    byte_hit = vert_hit = 0
                    n_excl = 0
                else:
                    src_verts = [(int(x), int(y)) for x, y in wire_vertices(blob_e)]
                    other = []
                    for cid, oring in cands:
                        if (int(cid[0]), int(cid[1])) == pid:
                            continue
                        s2, _, b2 = clip_ring(
                            probe_excl, oring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                        )
                        if s2 > 0:
                            other.append([(int(x), int(y)) for x, y in wire_vertices(b2)])
                    excl = owner_exclusive_vertices(
                        src_verts, other, rect, failing=fail_set,
                    )
                    n_excl = len(excl)
                    byte_hit = int(blob_e in new_wires.get(code, []))
                    vert_hit = int(any(v in new_by_type_verts.get(code, ()) for v in excl))
                    if byte_hit or vert_hit:
                        decision = "build:eo_bg_stitch"
                        n_stitch += 1
                    else:
                        decision = "disagree_no_oe"
                        n_oe += 1

                status = r["verdict"]
                dr = dec_rows[idx]
                dr["decision"] = decision
                dr["producer_class"] = status
                dr["recover_r"] = str(recover_r)
                dr["dx"] = str(dx)
                dr["dy"] = str(dy)
                dr["n_excl"] = str(n_excl)
                dr["n_ib"] = str(len(ib))
                dr["extra"] = json.dumps({
                    "byte": byte_hit, "vert": vert_hit,
                    "producer_home": [hx, hy],
                    "widen_recover_r": recover_r,
                    "option_c_proven_fixed": True,
                }, separators=(",", ":"))
                updates.append({
                    "cell": [level, ix, iy], "shape": shape,
                    "decision": decision, "recover_r": recover_r,
                })

            if n_cells_done % 10 == 0:
                print(f"  progress cells={n_cells_done}/{len(by_cell)} "
                      f"stitch={n_stitch} oe={n_oe} src={n_src} skip={n_skip}",
                      flush=True)

    with gzip.open(args.out_decisions, "wt") as f:
        f.write("\t".join(hdr) + "\n")
        for dr in dec_rows:
            f.write("\t".join(str(dr.get(h, "")) for h in hdr) + "\n")

    counts = Counter(dr["decision"] for dr in dec_rows)
    out = {
        "schema": 1,
        "n_widen_recovers": len(recovers),
        "n_matched_outside": len(work),
        "n_stitch": n_stitch,
        "n_disagree_no_oe": n_oe,
        "n_disagree_source_removed": n_src,
        "n_skip": n_skip,
        "n_fe_skip": n_fe,
        "n_updates": len(updates),
        "class_counts_after": dict(counts),
        "updates_sample": updates[:30],
        "new_disc": str(NEW_DISC.resolve()),
    }
    args.out_json.write_text(json.dumps(out, indent=2) + "\n")
    print("PROVEN_FIXED", json.dumps({k: out[k] for k in out if k != "updates_sample"}),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
