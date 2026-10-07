#!/usr/bin/env python3
"""Plan 44 Phase 1 control (DESIGN revision 2): Gates A+B under expanding Moore search.

For each sample row, grow Moore neighbourhood radius from 1 to R_cap (default 8)
until unique-byte or unique-fragment, logging the recovering radius. Candidates =
bbox-meet ∪ Moore(R) via spool_candidates(neighbourhood=R).

Gate A: among rows that resolve unique-byte|unique-fragment, ≥99% must pass
OE/new-disc (d35b565 exclusive vert or byte-equal clip).

Gate B: 100% class coverage with RC — every evaluable row is unique-byte,
unique-fragment, producer_home_outside_R_cap, or producer_ambiguous.
Bare producer_none does not close.

Offset census of recovering (dx,dy)/min radius/class → control_analysis.md.
Vertices from old-disc leaf records (dump_pre311 not retained on host).
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
    ap.add_argument("--r-cap", type=int, default=8,
                    help="Design R_cap: max Moore radius for expanding search (17×17 at 8)")
    args = ap.parse_args()
    n = 12 if args.smoke else args.n
    r_cap = int(args.r_cap)

    os.environ.setdefault("TMPDIR", str(ROOT / "output/tmp-agent"))
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)

    print("compile probes…", flush=True)
    so_prod = compile_probe(CENC_PROD, PROBE_DIR / "probe_flex_prod_33006aa.so")
    so_excl = compile_probe(CENC_EXCL, PROBE_DIR / "probe_flex_excl_d35b565.so")
    probe_prod = load_probe(so_prod)
    probe_excl = load_probe(so_excl)

    print("load identity pool…", flush=True)
    pool = load_tsv(IDENTITY)
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
    print(f"sample={len(sample)} codes={Counter(r['code'] for r in sample)} r_cap={r_cap}", flush=True)

    sampled_cells = {(r["level"], r["ix"], r["iy"]) for r in sample}
    r01_in_cells = [r for r in r01_all if (r["level"], r["ix"], r["iy"]) in sampled_cells]
    print(f"r01 rows in sampled cells: {len(r01_in_cells)}", flush=True)

    print("open discs + spool (frames walk)…", flush=True)
    old_fr = frames(str(OLD_DISC), sampled_cells)
    new_fr = frames(str(NEW_DISC), sampled_cells)
    spool = SpoolReader(str(SPOOL))
    print(f"old leaves {len(old_fr)} new leaves {len(new_fr)}", flush=True)

    skip = 0
    details = []  # tuples: (*_rid, verdict, extra_dict)
    by_leaf_rows = defaultdict(list)
    for r in sample:
        by_leaf_rows[leaf_key(r)].append(r)
    r01_by_leaf = defaultdict(list)
    for r in r01_in_cells:
        r01_by_leaf[leaf_key(r)].append(r)

    # Offset census accumulators
    recover_offsets = []  # (dx, dy, radius, class, level, ix, iy, shape, code)

    with open(OLD_DISC, "rb") as fo, open(NEW_DISC, "rb") as fn:
        for lk, rows in by_leaf_rows.items():
            level, ix, iy, path = lk
            cell = (level, ix, iy)
            if fe.get(cell, ("", "0"))[1] != "1":
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_footprints_changed", {}))
                continue
            if lk not in old_fr or lk not in new_fr:
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_leaf_missing", {}))
                continue
            if len(path) > 1:
                for r in rows:
                    skip += 1
                    details.append((*_rid(r), "skip_divided_leaf", {}))
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

            # Expanding Moore search: cache cands by radius
            cands_by_r: dict[int, list] = {}

            def cands_at(radius: int):
                if radius not in cands_by_r:
                    cands_by_r[radius] = list(
                        spool_candidates(spool, level, ix, iy, rect, b4, cr,
                                         neighbourhood=radius))
                return cands_by_r[radius]

            print(f"  leaf {lk} rows={len(rows)} expanding≤{r_cap}…", flush=True)

            for r in rows:
                shape = r["shape"]
                if shape not in by_shape:
                    skip += 1
                    details.append((*_rid(r), "skip_shape_missing", {}))
                    continue
                code, wire, old_verts = by_shape[shape]
                if code != r["code"]:
                    skip += 1
                    details.append((*_rid(r), "skip_code_mismatch", {}))
                    continue

                fail_set = failing.get((shape, code), set())
                from bg_owner_exclusive import identity_bearing_vertices
                ib = identity_bearing_vertices(old_verts, rect, failing=fail_set)

                status = "producer_none"
                pid = None
                recover_r = None
                cands = []
                for radius in range(1, r_cap + 1):
                    cands = cands_at(radius)
                    status, pid = find_producer(
                        probe_prod, wire, cands, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                        record_verts=old_verts, failing=fail_set,
                    )
                    if status in ("unique-byte", "unique-fragment"):
                        recover_r = radius
                        break
                    if status == "producer-ambiguous":
                        recover_r = radius
                        break

                extra = {"recover_r": recover_r, "r_cap": r_cap,
                         "n_cands": len(cands), "n_ib": len(ib)}

                if status == "producer-ambiguous":
                    details.append((*_rid(r), "producer_ambiguous",
                                    {**extra, "gate_b": "producer_ambiguous"}))
                    continue

                if status not in ("unique-byte", "unique-fragment"):
                    # Gate B residual: producer_home_outside_R_cap
                    # IB uncover diagnostics at R_cap
                    clips = 0
                    uncovered = 0
                    if ib and cands:
                        # clip_ring / wire_vertices already imported at module scope;
                        # do not re-import here (makes them function-local → UnboundLocalError
                        # on the unique-* OE limb below).
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
                    details.append((*_rid(r), "producer_home_outside_R_cap", {
                        **extra, "gate_b": "producer_home_outside_R_cap",
                        "max_radius": r_cap, "n_clips": clips, "n_ib_uncovered": uncovered,
                        "n_spool": len(cands),
                    }))
                    continue

                # Resolved unique-* — offset census + OE limb
                assert pid is not None and recover_r is not None
                hx, hy = int(pid[0]), int(pid[1])
                dx, dy = hx - ix, hy - iy
                cheb = max(abs(dx), abs(dy))
                recover_offsets.append({
                    "dx": dx, "dy": dy, "radius": recover_r, "chebyshev": cheb,
                    "class": status, "level": level, "ix": ix, "iy": iy,
                    "shape": shape, "code": code,
                })
                extra.update({"dx": dx, "dy": dy, "producer_home": [hx, hy],
                              "gate_b": status})

                ring = next(rng_ for cid, rng_ in cands if cid == pid)
                prod_class = status
                sz, _nrec, blob_e = clip_ring(
                    probe_excl, ring, rect=rect, tc=code, b4=b4_enc, cr=float(cr),
                )
                if sz <= 0:
                    details.append((*_rid(r), f"disagree_source_removed_sz{sz}",
                                    {**extra, "oe": "source_removed"}))
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
                    details.append((*_rid(r),
                                    f"agree_{prod_class}_r{recover_r}_excl={len(excl)}"
                                    f"_byte={int(byte_hit)}_vert={int(vert_hit)}",
                                    {**extra, "oe": "pass", "excl": len(excl),
                                     "byte": int(byte_hit), "vert": int(vert_hit)}))
                else:
                    details.append((*_rid(r), f"disagree_no_oe_excl={len(excl)}",
                                    {**extra, "oe": "fail", "excl": len(excl)}))

    # --- Gate evaluations ---
    evaluable = []
    for a, b, c, d, e, f, verdict, extra in details:
        if verdict.startswith("skip_"):
            continue
        evaluable.append((a, b, c, d, e, f, verdict, extra))

    # Gate B classes
    gate_b_ok = 0
    gate_b_bad = 0
    class_counts = Counter()
    for *_, verdict, extra in evaluable:
        gb = extra.get("gate_b")
        if gb in ("unique-byte", "unique-fragment", "producer_home_outside_R_cap",
                  "producer_ambiguous"):
            gate_b_ok += 1
            class_counts[gb] += 1
        elif verdict.startswith("agree_unique-byte"):
            gate_b_ok += 1
            class_counts["unique-byte"] += 1
        elif verdict.startswith("agree_unique-fragment"):
            gate_b_ok += 1
            class_counts["unique-fragment"] += 1
        elif verdict.startswith("disagree_no_oe") or verdict.startswith("disagree_source_removed"):
            # still resolved unique-*; OE fail — Gate B class is unique-*
            cls = extra.get("gate_b") or ("unique-byte" if "byte" in verdict else "unique-fragment")
            # recover from verdict prefix when agree failed
            if extra.get("gate_b") in ("unique-byte", "unique-fragment"):
                gate_b_ok += 1
                class_counts[extra["gate_b"]] += 1
            else:
                gate_b_bad += 1
                class_counts["bare_or_oe_without_class"] += 1
        else:
            gate_b_bad += 1
            class_counts[f"unclassified:{verdict[:40]}"] += 1

    # Fix Gate B: any row with gate_b set counts; OE-disagree still has gate_b unique-*
    gate_b_ok = gate_b_bad = 0
    class_counts = Counter()
    for *_, verdict, extra in evaluable:
        gb = extra.get("gate_b")
        if gb in ("unique-byte", "unique-fragment", "producer_home_outside_R_cap",
                  "producer_ambiguous"):
            gate_b_ok += 1
            class_counts[gb] += 1
        else:
            gate_b_bad += 1
            class_counts[f"missing_gate_b:{verdict[:40]}"] += 1

    # Gate A: among unique-* resolved, OE pass rate
    resolved = [x for x in evaluable if x[7].get("gate_b") in ("unique-byte", "unique-fragment")]
    oe_pass = sum(1 for x in resolved if x[7].get("oe") == "pass")
    oe_fail = sum(1 for x in resolved if x[7].get("oe") != "pass")
    gate_a_rate = (oe_pass / len(resolved)) if resolved else 0.0

    gate_a_ok = gate_a_rate >= 0.99 and len(resolved) >= max(5, n // 4)
    gate_b_pass = gate_b_bad == 0 and len(evaluable) >= max(5, n // 4)
    ok = gate_a_ok and gate_b_pass

    summary = {
        "sampled": len(sample), "skip": skip, "evaluable": len(evaluable),
        "seed": args.seed, "n": n, "smoke": bool(args.smoke), "r_cap": r_cap,
        "gate_a": {
            "resolved_unique": len(resolved), "oe_pass": oe_pass, "oe_fail": oe_fail,
            "rate": round(gate_a_rate, 6), "pass": gate_a_ok,
        },
        "gate_b": {
            "ok": gate_b_ok, "bad": gate_b_bad, "pass": gate_b_pass,
            "classes": dict(class_counts),
        },
        "recover_offsets_n": len(recover_offsets),
    }
    print("CONTROL", json.dumps(summary), flush=True)

    out = OUT / ("control_result_smoke.json" if args.smoke else "control_result.json")
    out.write_text(json.dumps({
        **summary,
        "details": [
            {"level": a, "ix": b, "iy": c, "shape": d, "vert": e, "code": f,
             "verdict": g, **extra}
            for a, b, c, d, e, f, g, extra in details
        ],
        "recover_offsets": recover_offsets,
    }, indent=1))
    (OUT / "control_result.txt").write_text(
        f"gate_a_rate={gate_a_rate:.6f} gate_a={gate_a_ok} gate_b={gate_b_pass} "
        f"evaluable={len(evaluable)} skip={skip} n={len(sample)} seed={args.seed} r_cap={r_cap}\n"
        + "\n".join(f"{a}\t{b}\t{c}\t{d}\t{e}\t{f}\t{g}" for a, b, c, d, e, f, g, _ in details)
        + "\n"
    )
    # Write offset census fragment for control_analysis
    census_path = OUT / "offset_census.json"
    by_r = Counter(o["radius"] for o in recover_offsets)
    by_cls = Counter(o["class"] for o in recover_offsets)
    by_xy = Counter((o["dx"], o["dy"]) for o in recover_offsets)
    census_path.write_text(json.dumps({
        "r_cap": r_cap,
        "n_recovering": len(recover_offsets),
        "by_radius": dict(sorted(by_r.items())),
        "by_class": dict(by_cls),
        "by_offset_dx_dy": {f"{dx},{dy}": c for (dx, dy), c in by_xy.most_common()},
        "max_recovering_radius": max((o["radius"] for o in recover_offsets), default=None),
        "rows": recover_offsets,
    }, indent=1))
    print(f"offset_census → {census_path} max_r={summary.get('gate_a')}", flush=True)

    print("CONTROL_OK" if ok else "CONTROL_FAIL",
          f"gate_a={gate_a_ok} gate_b={gate_b_pass}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
