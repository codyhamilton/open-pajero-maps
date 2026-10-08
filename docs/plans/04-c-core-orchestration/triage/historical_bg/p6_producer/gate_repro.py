#!/usr/bin/env python3
"""Plan 46 Phase 1 reproduction gate on 3C-04 / 013586b5.

Inputs: K1 dump of 013586b5 (144 B), sharded bg_producer_scan outputs
(<gate>/{bg,bb}.s*/side.npy) produced with the 33006aa `_cenc.c`.

Pipeline (tracked tools only):
  1. merge shard side tables -> side/side_<kind>.npy (status = residual bit),
     side/s02_background_boundary.npy (status = s02 bit)
  2. dump_join --mode s02     (144->152, byte144)                 -> dump_s02
  3. k1_triage classify  R01+S02                                   -> cls1
  4. dump_join --mode residual (byte146, rows assign==65535 only)  -> dump_ext
  5. k1_triage classify  R01+S02+S03+S04                           -> cls2
  6. figures vs historical: S02 1,939,053/25,772; residual 425,416 / 30,558 /
     216,488 / 3 / 70,999; remainder 137 / 8,739.
Heavy steps run under the caller's flock (run_heavy_python); no nested flock.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools")]
from kiwiw import dump_io  # noqa: E402

GROUP = ("level", "ix", "iy", "code", "p0", "p1", "p2", "p3", "p4", "p5", "p6", "shape")
INT32_MIN = np.iinfo(np.int32).min
NO_RULE = 0xFFFF
HIST = {
    "s02_rows": 1_939_053, "s02_groups": 25_772,
    "res_entries": 425_416, "res_fill_groups": 30_558, "res_bnd_groups": 216_488,
    "res_cover_groups": 3, "res_rings": 70_999,
    "rem_fill": 137, "rem_bnd": 8_739,
}
PY = str(ROOT / ".venv-rp/bin/python")
PIN_STOP = 10_000  # 3-07 attempt-3 Amendment 1: stop when distinct source rings exceed 10,000
HIST_S02_PIN = {"visited_groups": 25_775, "qualified_groups": 25_772, "qualified_rows": 1_939_053,
                "nomatch_groups": 3, "nomatch_rows": 319, "distinct_rings": 10_001,
                "unvisited_groups": 120_185, "unvisited_rows": 9_188_473}
HIST_S02_CANDIDATES = {"scope_groups": 145_960, "scope_rows": 11_127_845}


def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    r = subprocess.run(list(map(str, cmd)), cwd=ROOT)
    return r.returncode


def merge_side(gate: Path, short: str) -> np.ndarray:
    parts = sorted(gate.glob(f"{short}.s*/side.npy"))
    if not parts:
        raise SystemExit(f"no shard side tables for {short}")
    arr = np.concatenate([np.load(p) for p in parts])
    kd = np.dtype([(k, arr.dtype[k]) for k in GROUP])
    keys = np.empty(len(arr), kd)
    for k in GROUP:
        keys[k] = arr[k]
    if len(np.unique(keys)) != len(arr):
        raise SystemExit(f"{short}: duplicate group keys across shards")
    return arr


def load_dump(d: Path, kind: str):
    man = json.loads((d / "dump_manifest.json").read_text())
    TS = {"f64": "<f8", "i32": "<i4", "u16": "<u2", "u8": "u1"}
    dt = np.dtype([(f["name"], TS[f["type"]]) for f in man["fields"]], align=True)
    info = man["kinds"][kind]
    if dt.itemsize < info["row_size"]:
        dt = np.dtype({"names": dt.names, "formats": [dt.fields[n][0] for n in dt.names],
                       "offsets": [dt.fields[n][1] for n in dt.names], "itemsize": info["row_size"]})
    return np.memmap(d / info["file"], dtype=dt, mode="r"), man


PAD145 = "other_mechanism_not_rebuilt"


def declare_byte145(d: Path) -> None:
    """dump_join --mode residual writes byte 146 and appends one u8 field; the historical
    source (3-11 dump_new_ext, 3-08 dump_other) declared byte 145 as `other_mechanism`.
    3-08's other_mechanism is NOT rebuilt here (DESIGN dependency 3): byte 145 is verified
    all-zero and declared under an explicit not-rebuilt name so the appended field is
    declared at 146 where its bytes are."""
    mp = d / "dump_manifest.json"
    man = json.loads(mp.read_text())
    if man["fields"][-1]["name"] == PAD145:
        return
    if man["fields"][-1]["name"] != "s02_producer_verified":
        raise SystemExit(f"{d}: unexpected last field {man['fields'][-1]['name']}")
    for kind, info in man["kinds"].items():
        b = np.memmap(d / info["file"], "u1", mode="r").reshape(-1, 152)
        nz = int(np.count_nonzero(b[:, 145]))
        if nz:
            raise SystemExit(f"{kind}: byte145 has {nz} nonzero rows; cannot declare as zero pad")
        del b
    man["fields"].append({"name": PAD145, "type": "u8"})
    for info in man["kinds"].values():
        if "fields" in info:
            info["fields"] = man["fields"]
    man["byte145_declaration_plan46"] = {
        "field": PAD145, "all_zero_verified": True,
        "reason": "3-08 other_mechanism not rebuilt (DESIGN dependency 3); declared so the "
                  "residual flag is declared at byte 146 where dump_join writes it"}
    mp.write_text(json.dumps(man, indent=2))


def keyarr(rows, sel=None):
    kd = np.dtype([(k, rows.dtype[k]) for k in GROUP])
    src = rows if sel is None else rows[sel]
    out = np.empty(len(src), kd)
    for k in GROUP:
        out[k] = src[k]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", type=Path, required=True)
    ap.add_argument("--gate", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="gate result json")
    ap.add_argument("--skip-heavy", action="store_true", help="reuse existing work dirs")
    ap.add_argument("--s02-scope", choices=("pinstop", "full"), default="full",
                    help="full = whole S02 predicate, the re-baselined gate (Design ruling 2026-10-08, default); "
                         "pinstop = replay of the retired 3-07 attempt-3 pin-stop scope (diagnostic only)")
    ap.add_argument("--resume-residual", action="store_true",
                    help="reuse dump_s02 + cls1; rerun from the residual join")
    a = ap.parse_args(argv)
    W = a.work
    (W / "side").mkdir(parents=True, exist_ok=True)
    T = ROOT / "docs/plans/04-c-core-orchestration/triage"
    bg = json.loads((T / "rules_bg.json").read_text())
    rules = {r["id"]: r for r in bg["rules"]}
    (W / "rules_r01_s02.json").write_text(json.dumps(
        {"version": bg.get("version", 1), "rules": [rules["R01"], rules["S02"]]}, indent=1))
    (W / "rules_bg4.json").write_text(json.dumps(
        {"version": bg.get("version", 1),
         "rules": [rules[i] for i in ("R01", "S02", "S03", "S04")]}, indent=1))

    side_bg = merge_side(a.gate, "bg")
    side_bb = merge_side(a.gate, "bb")
    np.save(W / "side/side_background.npy", side_bg)
    np.save(W / "side/side_background_boundary.npy", side_bb)
    s02 = side_bb.copy()
    s02["status"] = s02["s02"].astype(s02["status"].dtype)
    # dump_join's aggregate assert sums side['rows'] over status==1; S02 applies only to
    # scope rows (L0, 291, sentinel), so 'rows' must be the scope row count per group.
    src_bb, _ = load_dump(a.dump, "background_boundary")
    scope = (src_bb["level"] == 0) & (src_bb["code"] == 291) & (src_bb["src_ix"] == INT32_MIN)
    uk, cnt = np.unique(keyarr(src_bb, scope), return_counts=True)
    sk = keyarr(s02)
    pos = np.searchsorted(uk, sk.astype(uk.dtype))
    pc = np.minimum(pos, len(uk) - 1)
    hit = (pos < len(uk)) & (uk[pc] == sk.astype(uk.dtype))
    s02["rows"] = np.where(hit, cnt[pc], 0)
    s02["status"] = np.where(hit, s02["status"], 0)
    s02 = np.ascontiguousarray(s02)
    full_q = s02["status"] == 1
    s02_full = {"scope_groups": int(len(uk)), "scope_rows": int(cnt.sum()),
                "qualified_groups": int(full_q.sum()), "qualified_rows": int(s02["rows"][full_q].sum())}
    # Historical S02 scope = 3-07 attempt-3 pin stop: walk the candidate groups (S02 column
    # predicate) in `k1_triage enumerate` order (sorted full group key; review_3-07 L29
    # "block-key order") and stop as soon as distinct source rings exceed PIN_STOP.
    sidx = np.full(len(uk), -1, np.int64)
    sidx[pos[hit]] = np.nonzero(hit)[0]
    seen, visited, qual, qrows, nomatch, nm_rows = set(), 0, 0, 0, 0, 0
    keep = np.zeros(len(s02), bool)
    for g in range(len(uk)):
        visited += 1
        j = sidx[g]
        if j >= 0 and s02["status"][j] == 1:
            r = s02[j]
            seen.add((int(r["level"]), int(r["producer_hx"]), int(r["producer_hy"]), int(r["producer_ri"])))
            keep[j] = True
            qual += 1
            qrows += int(cnt[g])
        else:
            nomatch += 1
            nm_rows += int(cnt[g])
        if len(seen) > PIN_STOP:
            break
    s02_pin = {"visited_groups": visited, "qualified_groups": qual, "qualified_rows": qrows,
               "nomatch_groups": nomatch, "nomatch_rows": nm_rows, "distinct_rings": len(seen),
               "unvisited_groups": int(len(uk) - visited), "unvisited_rows": int(cnt[visited:].sum())}
    if a.s02_scope == "pinstop":
        s02["status"] = np.where(keep, s02["status"], 0)
    np.save(W / "side/s02_background_boundary.npy", s02)

    if not a.skip_heavy:
        if not a.resume_residual:
            rc = run([PY, "-B", "parser/tools/dump_join.py", "--mode", "s02", "--dump", a.dump,
                      "--side", W / "side/s02_background_boundary.npy", "--s02-dst", W / "dump_s02"])
            if rc:
                return 2
            declare_byte145(W / "dump_s02")
            if run([PY, "-B", "parser/tools/k1_triage.py", "classify", "--dump", W / "dump_s02",
                    "--rules", W / "rules_r01_s02.json", "--out", W / "cls1"]) not in (0, 1):
                return 2
        else:
            declare_byte145(W / "dump_s02")
        if run([PY, "-B", "parser/tools/dump_join.py", "--mode", "residual", "--src", W / "dump_s02",
                "--side-dir", W / "side", "--assign-dir", W / "cls1", "--dst", W / "dump_ext",
                "--counts", W / "joined_counts.json"]):
            return 2
        if run([PY, "-B", "parser/tools/k1_triage.py", "classify", "--dump", W / "dump_ext",
                "--rules", W / "rules_bg4.json", "--out", W / "cls2"]) not in (0, 1):
            return 2

    res = {"historical": HIST, "measured": {}, "notes": [], "s02_scope": a.s02_scope,
           "s02_pinstop_replay": {k: {"hist": HIST_S02_PIN[k], "measured": v, "match": v == HIST_S02_PIN[k]}
                                  for k, v in s02_pin.items()},
           "s02_candidates": {k: {"hist_old_disc": HIST_S02_CANDIDATES[k], "measured": s02_full[k]}
                              for k in HIST_S02_CANDIDATES},
           "s02_full_predicate": s02_full}
    m = res["measured"]
    # --- S02
    rows_bb, _ = load_dump(W / "dump_ext", "background_boundary")
    a1 = np.fromfile(W / "cls1/assign_background_boundary.u16", "<u2")
    a2 = np.fromfile(W / "cls2/assign_background_boundary.u16", "<u2")
    s02_sel = a2 == 1
    m["s02_rows"] = int(s02_sel.sum())
    m["s02_groups"] = int(len(np.unique(keyarr(rows_bb, s02_sel))))
    # --- residual population (after R01+S02)
    entries = 0
    rings = set()
    for kind, short, side in (("background", "bg", side_bg), ("background_boundary", "bb", side_bb)):
        rows, _ = load_dump(W / "dump_ext", kind)
        asg = np.fromfile(W / f"cls1/assign_{kind}.u16", "<u2")
        rs = asg == NO_RULE
        k = keyarr(rows, rs)
        sent = (rows["src_ix"][rs] == INT32_MIN)
        ug = np.unique(k)
        m[f"res_{short}_groups"] = int(len(ug))
        # group/stratum entries: (group, sentinel-or-not)
        kd2 = np.dtype(k.dtype.descr + [("sent", "u1")])
        k2 = np.empty(len(k), kd2)
        for f in GROUP:
            k2[f] = k[f]
        k2["sent"] = sent
        entries += int(len(np.unique(k2)))
        # qualifying source rings among residual groups with status1
        skd = np.dtype([(f, side.dtype[f]) for f in GROUP])
        sk = np.empty(len(side), skd)
        for f in GROUP:
            sk[f] = side[f]
        st1 = side[side["status"] == 1]
        sk1 = sk[side["status"] == 1]
        ugc = ug.astype(skd)
        inres = np.isin(sk1, ugc)
        for r in st1[inres]:
            rings.add((int(r["level"]), int(r["producer_hx"]), int(r["producer_hy"]), int(r["producer_ri"])))
        m[f"res_{short}_status1_groups"] = int(inres.sum())
    m["res_fill_groups"] = m.pop("res_bg_groups")
    m["res_bnd_groups"] = m.pop("res_bb_groups")
    m["res_entries_fill_bnd"] = entries
    m["res_cover_groups"] = None
    m["res_rings_fill_bnd"] = len(rings)
    res["notes"].append("interior_cover not dumped (non-goal: non-background kinds); cover groups (3) "
                        "and their entries/rings are not measured -> named difference, not absorbed")
    # --- remainder
    for kind, short in (("background", "fill"), ("background_boundary", "bnd")):
        asg = np.fromfile(W / f"cls2/assign_{kind}.u16", "<u2")
        m[f"rem_{short}"] = int((asg == NO_RULE).sum())
        rows, _ = load_dump(W / "dump_ext", kind)
        m[f"rem_{short}_groups"] = int(len(np.unique(keyarr(rows, asg == NO_RULE))))
        for rid, idx in (("R01", 0), ("S02", 1), ("S03", 2), ("S04", 3)):
            n = int((asg == idx).sum())
            if n:
                m[f"cls2_{kind}_{rid}"] = n
    m["rem_groups_combined"] = m["rem_fill_groups"] + m["rem_bnd_groups"]
    cmp = {}
    for key, hv in HIST.items():
        mv = m.get(key)
        if mv is None:
            mv = m.get(key + "_fill_bnd")
        cmp[key] = {"hist": hv, "measured": mv, "match": (mv == hv)}
    res["compare"] = cmp
    # interior_cover is a DESIGN non-goal (non-background kinds) and is not in the dump. Its
    # 3 historical groups contribute 3..6 group/stratum entries (sentinel / non-sentinel) and
    # 0..3 qualifying rings. A fill+boundary figure is consistent iff the gap is in that range.
    ge = HIST["res_entries"] - (m.get("res_entries_fill_bnd") or 0)
    gr = HIST["res_rings"] - (m.get("res_rings_fill_bnd") or 0)
    res["cover_bound"] = {"entries_gap": ge, "entries_gap_allowed": [3, 6], "entries_ok": 3 <= ge <= 6,
                          "rings_gap": gr, "rings_gap_allowed": [0, 3], "rings_ok": 0 <= gr <= 3}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(cmp, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
