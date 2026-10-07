#!/usr/bin/env python3
"""One-shot R_widen probe for producer_home_outside_R_cap residuals (Design confirm).

Expanding Moore 1→R_widen (default 16) ONLY on the named residual set from Phase 1
control (not the full 95k). Unique-byte|unique-fragment recoveries attributed at
recovering radius. If ≥20 recover at radius >8 → stop_for_design. Still-failing
rows keep producer_home_outside_R_cap with max_radius=R_widen + spool/clip/IB counts.
"""
from __future__ import annotations

import argparse
import gzip
import json
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
SPOOL = ROOT / "output/extract_timing/spool"
CENC_PROD = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes/_cenc_33006aa.c")
PROBE_DIR = Path("/home/codyh/workspace/open-pajero-maps/output/scratch-44/probes")
IDENTITY = OUT / "rows_identity_proven.tsv.gz"
FE_PATH = ROOT / "docs/plans/04-c-core-orchestration/triage/oracle_chain/hop_3_14/cells_causes-au.tsv.gz"


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
    ap.add_argument("--from-control", type=Path, default=None,
                    help="Phase 1 control_result.json (mutually exclusive with --from-decisions)")
    ap.add_argument("--from-decisions", type=Path, default=None,
                    help="Phase 2 phase2_decisions.tsv.gz; selects producer_home_outside_R_cap")
    ap.add_argument("--r-widen", type=int, default=16)
    ap.add_argument("--stop-threshold", type=int, default=20)
    ap.add_argument("--cache-clear-every", type=int, default=20,
                    help="Clear spool caches every N leaves (bound RSS; 0=never)")
    ap.add_argument("--out-json", type=Path, default=OUT / "widen16_result.json")
    args = ap.parse_args()
    r_widen = int(args.r_widen)

    if args.from_decisions:
        sample = []
        with gzip.open(args.from_decisions, "rt") as f:
            hdr = f.readline().rstrip("\n").split("\t")
            for line in f:
                d = dict(zip(hdr, line.rstrip("\n").split("\t")))
                if d.get("decision") != "producer_home_outside_R_cap":
                    continue
                sample.append({
                    "level": int(d["level"]), "ix": int(d["ix"]), "iy": int(d["iy"]),
                    "depth": int(d["depth"]), "p0": int(d.get("p0", 0) or 0),
                    "p1": int(d.get("p1", 0) or 0), "p2": int(d.get("p2", 0) or 0),
                    "shape": int(d["shape"]), "vert": int(d["vert"]), "code": int(d["code"]),
                })
        # depth path fields: mass_decide writes depth but not p0.. in decisions?
        # Re-load full row keys from weak+none by (level,ix,iy,shape,vert,code)
        target_keys = {
            (r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"])
            for r in sample
        }
        pool = []
        for name in ("rows_weak.tsv.gz", "rows_none.tsv.gz", "rows_identity_proven.tsv.gz"):
            pool.extend(load_tsv(OUT / name))
        sample = [r for r in pool
                  if (r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]) in target_keys]
        print(f"from_decisions target_keys={len(target_keys)} matched={len(sample)} "
              f"r_widen={r_widen}", flush=True)
    else:
        ctrl_path = args.from_control or (OUT / "control_result.json")
        ctrl = json.loads(ctrl_path.read_text())
        target_keys = {
            (int(r["level"]), int(r["ix"]), int(r["iy"]),
             int(r["shape"]), int(r["vert"]), int(r["code"]))
            for r in ctrl["details"]
            if r.get("verdict") == "producer_home_outside_R_cap"
        }
        print(f"target_keys={len(target_keys)} r_widen={r_widen}", flush=True)

        pool = load_tsv(IDENTITY)
        sample = [r for r in pool
                  if (r["level"], r["ix"], r["iy"], r["shape"], r["vert"], r["code"]) in target_keys]
        print(f"matched_identity_rows={len(sample)}", flush=True)
        if len(sample) != len(target_keys):
            print(f"WARN: matched {len(sample)} of {len(target_keys)}", flush=True)

    fe = load_fe()
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    so_prod = compile_probe(CENC_PROD, PROBE_DIR / "probe_flex_prod_33006aa.so")
    probe_prod = load_probe(so_prod)

    sampled_cells = {(r["level"], r["ix"], r["iy"]) for r in sample}
    # Also need all R01 in those cells for failing-vert context
    r01_all = []
    for name in ("rows_identity_proven.tsv.gz", "rows_weak.tsv.gz", "rows_none.tsv.gz"):
        r01_all.extend(load_tsv(OUT / name))
    r01_in = [r for r in r01_all if (r["level"], r["ix"], r["iy"]) in sampled_cells]

    old_fr = frames(str(OLD_DISC), sampled_cells)
    spool = SpoolReader(str(SPOOL))
    print(f"old leaves {len(old_fr)}", flush=True)

    by_leaf_rows = defaultdict(list)
    for r in sample:
        by_leaf_rows[leaf_key(r)].append(r)
    r01_by_leaf = defaultdict(list)
    for r in r01_in:
        r01_by_leaf[leaf_key(r)].append(r)

    results = []
    recover_gt8 = 0
    n_leaves_done = 0
    cache_every = int(args.cache_clear_every)

    with open(OLD_DISC, "rb") as fo:
        for lk, rows in by_leaf_rows.items():
            level, ix, iy, path = lk
            cell = (level, ix, iy)
            if fe.get(cell, ("", "0"))[1] != "1":
                for r in rows:
                    results.append({
                        "level": r["level"], "ix": r["ix"], "iy": r["iy"],
                        "shape": r["shape"], "vert": r["vert"], "code": r["code"],
                        "verdict": "skip_footprints_changed", "r_widen": r_widen,
                    })
                continue
            if lk not in old_fr:
                for r in rows:
                    results.append({
                        "level": r["level"], "ix": r["ix"], "iy": r["iy"],
                        "shape": r["shape"], "vert": r["vert"], "code": r["code"],
                        "verdict": "skip_leaf_missing", "r_widen": r_widen,
                    })
                continue
            if len(path) > 1:
                for r in rows:
                    results.append({
                        "level": r["level"], "ix": r["ix"], "iy": r["iy"],
                        "shape": r["shape"], "vert": r["vert"], "code": r["code"],
                        "verdict": "skip_divided_leaf", "r_widen": r_widen,
                    })
                continue

            old_recs = list(leaf_records(fo, old_fr[lk]))
            by_shape = {s: (code, wire, verts) for s, code, wire, verts in old_recs}
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
            cands_by_r: dict[int, list] = {}

            def cands_at(radius: int):
                if radius not in cands_by_r:
                    cands_by_r[radius] = list(
                        spool_candidates(spool, level, ix, iy, rect, b4, cr,
                                         neighbourhood=radius))
                return cands_by_r[radius]

            print(f"  leaf {lk} rows={len(rows)} widen≤{r_widen}…", flush=True)
            n_leaves_done += 1
            if cache_every and n_leaves_done % cache_every == 0:
                clear_spool_caches()
                print(f"  cache_clear after {n_leaves_done} leaves", flush=True)
            for r in rows:
                shape, code = r["shape"], r["code"]
                base = {k: r[k] for k in ("level", "ix", "iy", "shape", "vert", "code")}
                if shape not in by_shape:
                    results.append({**base, "verdict": "skip_shape_missing", "r_widen": r_widen})
                    continue
                c_shape, wire, old_verts = by_shape[shape]
                if c_shape != code:
                    results.append({**base, "verdict": "skip_code_mismatch", "r_widen": r_widen})
                    continue
                fail_set = failing.get((shape, code), set())
                ib = identity_bearing_vertices(old_verts, rect, failing=fail_set)

                status, pid, recover_r, cands = "producer_none", None, None, []
                for radius in range(1, r_widen + 1):
                    cands = cands_at(radius)
                    status, pid = find_producer(
                        probe_prod, wire, cands, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                        record_verts=old_verts, failing=fail_set,
                    )
                    if status in ("unique-byte", "unique-fragment", "producer-ambiguous"):
                        recover_r = radius
                        break

                if status in ("unique-byte", "unique-fragment"):
                    hx, hy = int(pid[0]), int(pid[1])
                    if recover_r and recover_r > 8:
                        recover_gt8 += 1
                    results.append({
                        **base, "verdict": status, "recover_r": recover_r,
                        "dx": hx - ix, "dy": hy - iy, "producer_home": [hx, hy],
                        "r_widen": r_widen, "n_cands": len(cands), "n_ib": len(ib),
                    })
                    print(f"    RECOVER {base} {status} r={recover_r} home=({hx},{hy})",
                          flush=True)
                elif status == "producer-ambiguous":
                    results.append({
                        **base, "verdict": "producer_ambiguous", "recover_r": recover_r,
                        "r_widen": r_widen, "n_cands": len(cands), "n_ib": len(ib),
                    })
                else:
                    clips = uncovered = 0
                    if ib and cands:
                        cover_count = Counter()
                        for cid, ring in cands:
                            sz, _, blob = clip_ring(
                                probe_prod, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                            )
                            if sz <= 0:
                                continue
                            clips += 1
                            vset = {(int(x), int(y)) for x, y in wire_vertices(blob)}
                            for pt in ib:
                                if pt in vset:
                                    cover_count[pt] += 1
                        uncovered = sum(1 for pt in ib if cover_count[pt] == 0)
                    elif ib:
                        uncovered = len(ib)
                    results.append({
                        **base, "verdict": "producer_home_outside_R_cap",
                        "max_radius": r_widen, "r_widen": r_widen,
                        "n_spool": len(cands), "n_clips": clips,
                        "n_ib": len(ib), "n_ib_uncovered": uncovered,
                    })
                    print(f"    STILL_OUT {base} spool={len(cands)} clips={clips} "
                          f"uncovered={uncovered}", flush=True)

    recovered = [r for r in results if r["verdict"] in ("unique-byte", "unique-fragment")]
    still = [r for r in results if r["verdict"] == "producer_home_outside_R_cap"]
    stop = recover_gt8 >= args.stop_threshold
    out = {
        "schema": 1,
        "r_widen": r_widen,
        "n_targets": len(target_keys),
        "n_matched": len(sample),
        "n_recovered": len(recovered),
        "n_still_outside": len(still),
        "n_ambiguous": sum(1 for r in results if r["verdict"] == "producer_ambiguous"),
        "n_recover_radius_gt8": recover_gt8,
        "stop_for_design": stop,
        "stop_threshold": args.stop_threshold,
        "by_recover_r": dict(Counter(r.get("recover_r") for r in recovered)),
        "results": results,
    }
    args.out_json.write_text(json.dumps(out, indent=2) + "\n")
    # Update residual TSV for still-outside with max_radius=16
    lines = ["level\tix\tiy\tshape\tvert\tcode\tmax_radius\tn_spool\tn_clips\tn_ib\tn_ib_uncovered\n"]
    for r in still:
        lines.append(
            f"{r['level']}\t{r['ix']}\t{r['iy']}\t{r['shape']}\t{r['vert']}\t{r['code']}\t"
            f"{r['max_radius']}\t{r['n_spool']}\t{r['n_clips']}\t{r['n_ib']}\t{r['n_ib_uncovered']}\n"
        )
    (OUT / "phase2_residuals_outside_R_cap.tsv").write_text("".join(lines))
    print("WIDEN", json.dumps({k: out[k] for k in out if k != "results"}), flush=True)
    if stop:
        print("STOP_FOR_DESIGN", flush=True)
        return 2
    print("WIDEN_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
