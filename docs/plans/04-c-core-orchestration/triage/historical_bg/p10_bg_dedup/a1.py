#!/usr/bin/env python3
"""Plan 68 Phase 1: R-G5-4-a-1 (222 R01 rows / 8 groups, producer_ambiguous) per-copy producers.

build:   single-cell sidecar windows at 33006aa (plan 63 sidecar_33006aa.patch in a throwaway worktree)
         for the 4 leaves of p9_r01_residual/transitions.json ambiguous_groups.
analyze: G1 output-neutral gate (every window frame byte-equal to a 013586b5 leaf of its cell, every disc
         leaf matched); per group: the group's shape and its byte-identical same-type copy, each copy's
         sidecar emitter; checks: emitter in the plan-62 tie candidates, the two copies by distinct
         candidates, plan-63 rule order (class, own-first, iy, ix, k), and the plan-62 decide verdict
         under the proven producer of the group's own shape (tie_decide). Cross-check vs plan 63
         provenance.tsv.gz for (1176,1591). Writes a1_verdicts.json + a1_verdicts.tsv.gz."""
from __future__ import annotations

import argparse, atexit, csv, gzip, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HB = ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg"
sys.path[:0] = [str(HB / "p5_owner_exclusive"), str(HB / "p7_producer_tie"), str(ROOT / "parser")]
import leaf_io as L  # noqa: E402
from leaf_io import frames  # noqa: E402
from kiwiw import volume  # noqa: E402
from provenance import gzw, leaf_all_records, load_fnv, parse_sidecar, source_of  # noqa: E402

TRANS = HB / "p9_r01_residual/transitions.json"


def groups():
    return json.loads(TRANS.read_text())["ambiguous_groups"]


def cmd_build(a):
    a.out = a.out.resolve(); a.spool = a.spool.resolve()
    cells = sorted({tuple(g["leaf"][:3]) for g in groups()})
    t0 = time.time()
    for lv, ix, iy in cells:
        d = a.out / f"w_{lv}_{ix}_{iy}"
        if (d / "DONE").exists():
            continue
        (d / "sc").mkdir(parents=True, exist_ok=True)
        for p in (d / "sc").iterdir():
            p.unlink()
        env = dict(os.environ, KW_SIDECAR_DIR=str(d / "sc"), PYTHONDONTWRITEBYTECODE="1")
        cmd = [a.python, "-B", "parser/build_alldata.py", "--spool", str(a.spool), "--out", str(d / "ALLDATA.KWI"),
               "-j", "4", "--window", str(lv), str(ix), str(iy), str(ix + 1), str(iy + 1), "--frame-dump", str(d / "frames")]
        r = subprocess.run(cmd, cwd=a.worktree, env=env, capture_output=True, text=True)
        (d / "build.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            print(json.dumps({"window": d.name, "rc": r.returncode})); sys.exit(2)
        (d / "ALLDATA.KWI").unlink(missing_ok=True)
        (d / "DONE").write_text("ok\n")
        print(json.dumps({"window": d.name, "t": round(time.time() - t0, 1)}), flush=True)


def cmd_analyze(a):
    tmp = Path(tempfile.mkdtemp(prefix="p68_a1_")); atexit.register(shutil.rmtree, tmp, True)
    fnv = load_fnv(tmp)
    gs = groups()
    cells = sorted({tuple(g["leaf"][:3]) for g in gs})
    fr = frames(str(a.old_disc), set(cells))
    disc = defaultdict(dict)
    with open(a.old_disc, "rb") as fo:
        for k, (dsa, size, ss, ls) in fr.items():
            b = os.pread(fo.fileno(), size * ls, volume.getsector(dsa, ss, ls))
            disc[k[:3]][k[3]] = b[:L.U16(b, 0) * 2]
    g1 = Counter(); leafsrc = {}
    for lk in cells:
        d = a.win / f"w_{lk[0]}_{lk[1]}_{lk[2]}"
        rows = list(csv.reader(open(d / "frames.tsv"), delimiter="\t"))
        fb = (d / "frames.bin").read_bytes()
        items, cl, W, P, F = parse_sidecar(d)
        seen = set()
        for r in rows:
            if (int(r[0]), int(r[1]), int(r[2])) != lk:
                continue
            pt, sxi, syi, o, n = map(int, r[3:8])
            buf = fb[o:o + n]
            match = [p for p, b in disc[lk].items() if b == buf]
            if not match:
                g1["frame_mismatch"] += 1; continue
            g1["frames_equal"] += 1
            path = match[0]; seen.add(path)
            h = fnv(buf)
            if pt == 0:
                ents = W[lk][2] if W.get(lk) and W[lk][1] == h else None
            else:
                c = syi * (2 if pt == 1 else 4) + sxi
                pl = P.get((*lk, c, h), [])
                ents = pl[0] if pl and all(e == pl[0] for e in pl) and F.get((*lk, c), (0, None))[1] == h else None
            if ents is None:
                g1["sidecar_unmatched"] += 1; continue
            recs = leaf_all_records(buf)
            emit = [(i, c) for i, c, k in ents for _ in range(k)]
            if len(emit) != len(recs) or any(e[1] != rc[1] for e, rc in zip(emit, recs)):
                g1["sidecar_count_fail"] += 1; continue
            g1["sidecar_frames"] += 1
            leafsrc[(*lk, path)] = (recs, emit, [source_of(items, cl, lk, i) for i, _c in emit])
        g1["disc_leaf_unmatched"] += len(set(disc[lk]) - seen)
    prov = {}
    with gzip.open(HB / "p7_producer_tie/provenance.tsv.gz", "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            prov[(int(r["ix"]), int(r["iy"]), r["path"], int(r["copy_shape"]))] = (r["emitter_kind"], int(r["emitter_hx"]), int(r["emitter_hy"]), int(r["emitter_ri"]))
    out = []; c = Counter()
    for g in gs:
        lv, ix, iy, ps = g["leaf"]; path = tuple(int(x) for x in str(ps).split(","))
        recs, emit, src = leafsrc[(lv, ix, iy, path)]
        s0 = g["shape"]; _s, cls, code, w = recs[s0]
        copies = [s for s, c2, cd, w2 in recs if c2 and cd == code and w2 == w]
        cands = sorted(tuple(t[0][:3]) for t in g["tie_decide"])
        decide = {tuple(t[0][:3]): t[1] for t in g["tie_decide"]}
        em = [src[s] for s in copies]
        ident = [tuple(e[1:]) for e in em]
        keys = [(emit[s][1], 0 if e[0] == "own" else 1, e[2], e[1], e[3]) for s, e in zip(copies, em)]
        mine = tuple(src[s0][1:])
        x63 = [prov.get((ix, iy, ps if isinstance(ps, str) else ",".join(map(str, path)), s)) for s in copies]
        rec = {"leaf": [lv, ix, iy, list(path)], "shape": s0, "rows": g["rows"], "code": code, "class": cls,
               "copies": copies, "emitters": [list(e) for e in em], "candidates": [list(x) for x in cands],
               "all_in_candidates": sorted(ident) == cands, "distinct": len(set(ident)) == len(ident),
               "rule63_order": all(k1 < k2 for k1, k2 in zip(keys, keys[1:])),
               "producer_of_shape": list(mine), "decide_under_producer": decide.get(mine),
               "plan63_crosscheck": None if all(x is None for x in x63) else [list(x) if x else None for x in x63] == [list(e) for e in em]}
        ok = rec["all_in_candidates"] and rec["distinct"] and rec["rule63_order"] and rec["decide_under_producer"] == "build"
        rec["verdict"] = "build:eo_bg_stitch" if ok else "open"
        c[rec["verdict"]] += g["rows"]; c["groups_" + rec["verdict"]] += 1
        out.append(rec)
    res = {"gate1": dict(sorted(g1.items())), "groups": out, "rows_by_verdict": dict(sorted(c.items())),
           "inputs": {"transitions_sha256": hashlib.sha256(TRANS.read_bytes()).hexdigest(),
                      "old_disc": str(a.old_disc)}}
    a.out.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"gate1": res["gate1"], "rows_by_verdict": res["rows_by_verdict"]}))
    if g1.get("frame_mismatch") or g1.get("disc_leaf_unmatched") or g1.get("sidecar_unmatched") or g1.get("sidecar_count_fail"):
        sys.exit(3)


def main(argv=None):
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("build"); b.add_argument("--worktree", type=Path, required=True)
    b.add_argument("--spool", type=Path, required=True); b.add_argument("--out", type=Path, required=True)
    b.add_argument("--python", default=sys.executable)
    z = sp.add_parser("analyze"); z.add_argument("--win", type=Path, required=True)
    z.add_argument("--old-disc", type=Path, required=True); z.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    (cmd_build if a.cmd == "build" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
