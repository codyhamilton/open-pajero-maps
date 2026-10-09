#!/usr/bin/env python3
"""Plan 64 Phase 2: d35b565 stage trace of each group's producer ring in its leaf.

  build    window builds from a throwaway d35b565 worktree carrying stage_d35b565.patch (plan 63's
           sidecar + per-bg_shape stage counters; logging only), one single-cell window per group cell.
           Divided leaves: E2's dv_bg_cells pushes a parent background onto a sub-cell only when its
           clip there writes a record (_e2.c "_bg_sub_cells"); that assignment clip is logged as SD lines
           (tier ptype, sub-cell, parent ordinal, return, nrec, counters) -> dv_assign_calls.
  analyze  G0 output-neutral gate: every window frame byte-equal to a 4ed9cd80 leaf of the cell (and
           every 4ed9cd80 leaf matched). Then, per group, the bg_shape call(s) whose merged ordinal maps
           (C/I lines) to the recorded producer in the committed frame's SW/SP line, with its counters:
             n (ring points after closure drop), inside, m (clipped chains), whole,
             eo (eo_clip result: 1 = EO faces path taken, 0 = legacy path, -1 error),
             cx (why the EO arrangement ran: 1 proper crossing among clipped segments, 2 a chain not
                 locally CCW, 3 repeated vertex on a whole ring, 4 tie/reused successor), es (clipped
                 segments), ee (odd-parity + frame atomic edges), faces (closed walks), fpos (walks with
                 positive area), fleft (walks whose first edge has the ring's interior on its left ->
                 emit_piece), pieces (emit_piece calls), pzero (pieces dropped after densify/round), split as
                 pq3 (fewer than 3 distinct lattice points, d35b565 _cenc.c:586) and pa0 (zero lattice
                 area, _cenc.c:592), q / a2 (last piece's rounded point count / twice its lattice area),
                 rec (records written), path (1 EO, 2 inside, 3 open,
                 4 whole, 5 m==0 fill test, 6 legacy chain walk).
Writes stage.json."""
from __future__ import annotations

import argparse, csv, json, os, subprocess, sys, tempfile, time, shutil, atexit
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import trace as TR  # noqa: E402
from trace import PV, L, frames, volume  # noqa: E402

FIELDS = ["i", "c", "n", "inside", "m", "whole", "eo", "cx", "es", "ee", "faces", "fpos", "fleft",
          "path", "pieces", "pzero", "q", "a2", "rec", "pq3", "pa0"]
PATH = {1: "eo_faces", 2: "inside", 3: "open", 4: "whole", 5: "m0_fill_test", 6: "legacy_chain_walk", -1: "early_return"}


def parse_stage(d):
    SW, SP, SD = {}, defaultdict(list), defaultdict(list)
    for f in sorted((d / "sc").iterdir()):
        for line in f.read_text().splitlines():
            t = line.split("\t")
            if t[0] == "SD":
                lv, ix, iy, ptype, c, i, r, nrec = map(int, t[1:9])
                SD[(lv, ix, iy)].append({"ptype": ptype, "sub": c, "i": i, "ret": r, "nrec": nrec,
                                         **dict(zip(FIELDS[2:], map(int, t[9].split(":"))))})
                continue
            if t[0] not in ("SW", "SP"):
                continue
            lv, ix, iy, cell, fl = map(int, t[1:6]); h = t[6]
            ents = [dict(zip(FIELDS, map(int, e.split(":")))) for e in t[7].split(",")] if len(t) > 7 and t[7] else []
            if t[0] == "SW":
                SW[(lv, ix, iy)] = (fl, h, ents)
            else:
                SP[(lv, ix, iy, cell, h)].append(ents)
    return SW, SP, SD


def cmd_analyze(a):
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p64_stage_", dir=a.tmp)); atexit.register(shutil.rmtree, tmp, True)
    fnv = PV.load_fnv(tmp)
    gs = TR.groups()
    by_cell = defaultdict(list)
    for g in gs:
        by_cell[tuple(g["cell"])].append(g)
    res = []; g0 = Counter()
    with open(a.disc, "rb") as fo:
        for cell, cgs in sorted(by_cell.items()):
            lv, ix, iy = cell
            d = a.win / f"w_{lv}_{ix}_{iy}"
            rows = list(csv.reader(open(d / "frames.tsv"), delimiter="\t"))
            fb = (d / "frames.bin").read_bytes()
            fr = frames(str(a.disc), {cell})
            disc = {}
            for k, (dsa, size, ss, ls) in fr.items():
                b = os.pread(fo.fileno(), size * ls, volume.getsector(dsa, ss, ls))
                disc[k[3]] = b[:L.U16(b, 0) * 2]
            items, cells, W, P, F = PV.parse_sidecar(d)
            SW, SP, SD = parse_stage(d)
            seen = {}
            for r in rows:
                lk = (int(r[0]), int(r[1]), int(r[2]))
                if lk != cell:
                    continue
                pt, sxi, syi, o, n = int(r[3]), int(r[4]), int(r[5]), int(r[6]), int(r[7])
                buf = fb[o:o + n]
                match = [p for p, b in disc.items() if b == buf]
                if not match:
                    g0["frame_mismatch"] += 1; continue
                g0["frames_equal"] += 1
                path = match[0]
                if len(match) > 1:
                    nxp = 2 if pt == 1 else 4
                    cand = [p for p in match if len(p) >= 2 and p[-1] == syi * nxp + sxi]
                    path = cand[0] if len(cand) == 1 else min(match)
                h = fnv(buf)
                if pt == 0:
                    sw = SW.get(lk); ents = sw[2] if sw and sw[1] == h else None
                else:
                    nxp = 2 if pt == 1 else 4; c = syi * nxp + sxi
                    pl = SP.get((*lk, c, h), [])
                    ents = pl[0] if pl and all(e == pl[0] for e in pl) else None
                if ents is None:
                    g0["stage_line_missing"] += 1; continue
                seen[path] = ents
            g0["disc_leaves"] += len(disc); g0["disc_leaf_unmatched"] += len(set(disc) - set(seen))
            for g in cgs:
                hx, hy, ri, tc = g["producer"]
                ents = seen.get(tuple(g["path"]), [])
                calls = []
                for e in ents:
                    so = PV.source_of(items, cells, cell, e["i"])
                    if (so[1], so[2], so[3]) == (hx, hy, ri):
                        calls.append({**e, "source_kind": so[0], "path_name": PATH.get(e["path"], str(e["path"]))})
                sub_calls = []
                if len(g["path"]) >= 2:
                    for e in SD.get(cell, []):
                        if e["sub"] != g["path"][-1]:
                            continue
                        so = PV.source_of(items, cells, cell, e["i"])
                        if (so[1], so[2], so[3]) == (hx, hy, ri):
                            sub_calls.append({**e, "source_kind": so[0], "path_name": PATH.get(e["path"], str(e["path"]))})
                res.append({"gid": g["gid"], "row": g["row"], "leaf": [*cell, g["path"]], "producer": g["producer"],
                            "calls": calls, "n_calls": len(calls), "dv_assign_calls": sub_calls,
                            "records_from_producer": sum(c["rec"] for c in calls)})
                print(json.dumps({"gid": g["gid"], "calls": [(c["path_name"], c["cx"], c["faces"], c["fpos"], c["fleft"],
                                                               c["pieces"], c["pzero"], c["pq3"], c["pa0"], c["rec"]) for c in calls + sub_calls]}),
                      flush=True)
    out = {"gate0_vs_4ed9cd80": dict(sorted(g0.items())), "groups": res, "fields": FIELDS, "path_names": PATH,
           "patch": "p8_source_removed/stage_d35b565.patch"}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"gate0": out["gate0_vs_4ed9cd80"], "wall_s": round(time.time() - t0, 1)}))
    if g0.get("frame_mismatch") or g0.get("disc_leaf_unmatched") or g0.get("stage_line_missing"):
        sys.exit(3)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--worktree", type=Path, required=True); b.add_argument("--spool", type=Path, required=True)
    b.add_argument("--out", type=Path, required=True); b.add_argument("--python", default=sys.executable)
    b.add_argument("-j", type=int, default=4)
    z = sub.add_parser("analyze")
    for k in ("win", "disc", "out", "tmp"):
        z.add_argument("--" + k, type=Path, required=True)
    a = ap.parse_args(argv)
    (TR.cmd_build if a.cmd == "build" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
