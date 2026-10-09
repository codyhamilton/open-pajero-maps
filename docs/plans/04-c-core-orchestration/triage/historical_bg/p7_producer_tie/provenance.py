#!/usr/bin/env python3
"""Plan 63 Phase 2: emission provenance from the 33006aa sidecar window builds + rule table.

Inputs: windows.py output (frames.tsv/.bin + sidecar sc/*.tsv per window), the 013586b5 disc, the
33006aa clipper, the spool. Steps:
 G1  output-neutral gate: every window frame byte-equal to a 013586b5 leaf of its cell, and every
     disc leaf of an analysed cell matched (stop on any difference).
 SC  sidecar -> per-record emitter: W (whole cell) / F+P (divided sub-frame) entries list
     (merged background ordinal, class, records) in enc_bg emission order; expanded per record and
     checked against the leaf's record count and unit class; merged ordinal -> source via the C
     (own background count) and I (routed item j -> source cell, k, cover) lines.
 G2  sidecar control gate (tie cells): every class>0 record whose plan-46 scan hit set
     (Moore(8) U FarHomes, same type, 33006aa clip, piecewise byte) is a single candidate: the
     sidecar emitter equals it.
 PROV per-copy producer for every T1/T2 group of ties_all.json.
 RULES duplicate cases (byte-identical same-type class>0 records in one leaf) with sidecar emitters
     and scan hits, split derivation/holdout by the fixed cell hash HOLDOUT(), rules scored.
Deterministic outputs (gz mtime=0, sorted keys)."""
from __future__ import annotations

import argparse, atexit, csv, ctypes, gzip, hashlib, io, json, os, shutil, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / p) for p in ("parser", "parser/tools",
                "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive")]
import bg_producer_scan as S  # noqa: E402
import bg_owner_exclusive as O  # noqa: E402
import leaf_io as L  # noqa: E402
from leaf_io import cell_b4, frames  # noqa: E402
from kiwiw import volume  # noqa: E402

CODE_PATH = ("parser/kiwiw/_e2.c kw_e2 (routed-row loop: rows ordered by target (iy,ix), source (iy,ix), "
             "shape k) + e2_merge (own backgrounds first, then routed items in row order); "
             "parser/kiwiw/_cenc.c enc_bg (class-major, then merged background ordinal; bg_shape emits "
             "each background's pieces contiguously); divided leaves: _e2.c dv_bg_cells/dv_probe "
             "(sub-cell lists in ascending parent ordinal) at 33006aa")


def HOLDOUT(level, ix, iy):
    """Fixed before any rule was scored: sample cells with an odd first sha256 byte are holdout."""
    return hashlib.sha256(f"p63-holdout:{level},{ix},{iy}".encode()).digest()[0] & 1 == 1


FNV_C = r"""
#include <stdint.h>
uint64_t fnv(const uint8_t *p, int64_t n) {
    uint64_t h = 1469598103934665603ULL;
    for (int64_t i = 0; i < n; i++) { h ^= p[i]; h *= 1099511628211ULL; }
    return h;
}
"""


def load_fnv(tmp):
    c = tmp / "fnv.c"; c.write_text(FNV_C); so = tmp / "fnv.so"
    subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", str(so), str(c)], check=True)
    lib = ctypes.CDLL(str(so)); lib.fnv.restype = ctypes.c_uint64
    lib.fnv.argtypes = [ctypes.c_char_p, ctypes.c_int64]
    return lambda b: "%016x" % lib.fnv(b, len(b))


def leaf_all_records(buf):
    """[(s, cls, code, wire)] for every background record of a frame (class 0 included)."""
    out = []
    bg = L.sec.split(buf)["background"]
    if not bg:
        return out
    hlen = L.sec.u16(bg, 0) * 2; off = 2; s = 0
    while off < hlen:
        w = L.sec.u16(bg, off); po = w * 2; off += 4
        if w == 0xFFFF:
            continue
        n = L.sec.u16(bg, po); u0 = po + 2; p = u0 + 4 * n
        for i in range(n):
            val = L.sec.u16(bg, u0 + 4 * i + 2); cnt, cls = val & 0xFFF, val >> 14
            for _ in range(cnt):
                ln = (L.sec.u16(bg, p) & 0xFFF) * 2
                out.append((s, cls, L.sec.u16(bg, p + 4), bytes(bg[p:p + ln])))
                s += 1; p += ln
    return out


def parse_sidecar(d):
    items, cells, W, P, F = {}, {}, {}, defaultdict(list), {}
    for f in sorted((d / "sc").iterdir()):
        for line in f.read_text().splitlines():
            t = line.split("\t")
            if t[0] == "I":
                lv, ix, iy, j, sx, sy, kc = map(int, t[1:8])
                items[(lv, ix, iy, j)] = (sx, sy, kc >> 1, kc & 1)
            elif t[0] == "C":
                lv, ix, iy, own, nit, has = map(int, t[1:7])
                cells[(lv, ix, iy)] = (own, nit, has)
            else:
                lv, ix, iy, cell, fl = map(int, t[1:6]); h = t[6]
                ents = [tuple(map(int, e.split(":"))) for e in t[7].split(",")] if len(t) > 7 and t[7] else []
                if t[0] == "W":
                    W[(lv, ix, iy)] = (fl, h, ents)
                elif t[0] == "P":
                    P[(lv, ix, iy, cell, h)].append(ents)
                else:
                    F[(lv, ix, iy, cell)] = (fl, h)
    return items, cells, W, P, F


def source_of(items, cells, lk, i):
    lv, ix, iy = lk
    own = cells[lk][0]
    if i < own:
        return ("own", ix, iy, i)
    sx, sy, k, cover = items[(lv, ix, iy, i - own)]
    return ("cover" if cover else "routed", sx, sy, k)


def gzw(path, header, rows):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as g:
        g.write(("\t".join(header) + "\n").encode())
        for r in rows:
            g.write(("\t".join(map(str, r)) + "\n").encode())
    path.write_bytes(buf.getvalue())


class Scanner:
    def __init__(self, spool, far, probe):
        self.spool, self.far, self.probe = spool, far, probe

    def hits(self, lk, path, ptype, codes):
        """{(code, wire): sorted [(hx,hy,ri)]} for candidates of the given types (plan-46 scan)."""
        level, ix, iy = lk
        b4, cr, rect = S.leaf_clip_geometry(level, ix, iy, path, ptype, cell_b4)
        b4e = (0.0, cr, 0.0, cr)
        out = defaultdict(set)
        pieces_of = {}
        for cid, ring, _ll in S.fast_spool_candidates(self.spool, level, ix, iy, rect, b4, cr, 8, None,
                                                       extra_homes=self.far.query(ix, iy)):
            if cid[3] not in codes:
                continue
            sz, _n, blob = O.clip_ring(self.probe, ring, rect=rect, tc=cid[3], b4=b4e, cr=cr)
            if sz <= 0:
                continue
            ps = O.wire_records(blob)
            pieces_of[cid[:3]] = ps
            for p in ps:
                out[(cid[3], p)].add(tuple(cid[:3]))
        return {k: sorted(v) for k, v in out.items()}, pieces_of


def main(argv=None):
    ap = argparse.ArgumentParser()
    for k in ("win", "old_disc", "cenc_old", "spool", "out_dir"):
        ap.add_argument("--" + k.replace("_", "-"), type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p63_prov_")); atexit.register(shutil.rmtree, tmp, True)
    fnv = load_fnv(tmp)
    probe = O.load_probe(O.compile_probe(a.cenc_old.resolve(), (tmp / "p.so").resolve()))
    from kiwiw.spool import SpoolReader
    spool = SpoolReader(str(a.spool)); far = S.FarHomes(a.spool, 0)
    scan = Scanner(spool, far, probe)
    ties = json.loads((HERE / "ties_all.json").read_text())
    tie_leaves = defaultdict(list)
    for g in ties["groups"]:
        tie_leaves[(g["leaf"][0], g["leaf"][1], g["leaf"][2], tuple(g["leaf"][3]))].append(g)
    wins = json.loads((a.win / "windows.json").read_text())
    owner = {}
    for w in wins:
        lv, x0, y0, x1, y1 = w["window"]
        for y in range(y0, y1):
            for x in range(x0, x1):
                owner.setdefault((lv, x, y), (w["name"], w["set"]))
    g1 = Counter(); g1_fail = []; sc_fail = []; g2 = Counter(); g2_dis = []; g2_cover = []
    prov_rows = []; cases = []
    spool_cls = {}

    def src_class(hx, hy, ri):
        k = (hx, hy)
        if k not in spool_cls:
            c = S.direct_spool_cell(spool, 0, hx, hy)
            spool_cls[k] = [int(b.shape_class) for b in (c or {}).get("backgrounds") or []]
            if len(spool_cls) > 4096:
                spool_cls.pop(next(iter(spool_cls)))
        return spool_cls[k][ri]

    with open(a.old_disc, "rb") as fo:
        for w in wins:
            d = a.win / w["name"]
            rows = list(csv.reader(open(d / "frames.tsv"), delimiter="\t"))
            fb = (d / "frames.bin").read_bytes()
            mine = {(int(r[0]), int(r[1]), int(r[2])) for r in rows
                    if owner[(int(r[0]), int(r[1]), int(r[2]))][0] == w["name"]}
            if not mine:
                continue
            ptype = {}
            fr = frames(str(a.old_disc), mine, ptype_out=ptype)
            disc = defaultdict(dict)
            for k, (dsa, size, ss, ls) in fr.items():
                b = os.pread(fo.fileno(), size * ls, volume.getsector(dsa, ss, ls))
                disc[k[:3]][k[3]] = b[:L.U16(b, 0) * 2]
            items, cells, W, P, F = parse_sidecar(d)
            seen = defaultdict(set)
            for r in rows:
                lk = (int(r[0]), int(r[1]), int(r[2]))
                if lk not in mine:
                    continue
                pt, sxi, syi, o, n = int(r[3]), int(r[4]), int(r[5]), int(r[6]), int(r[7])
                buf = fb[o:o + n]
                match = [p for p, b in disc.get(lk, {}).items() if b == buf]
                if not match:
                    g1["frame_mismatch"] += 1; g1_fail.append([*lk, pt, sxi, syi]); continue
                g1["frames_equal"] += 1
                path = match[0] if len(match) == 1 else None
                if path is None:
                    nxp = 2 if pt == 1 else 4
                    cand = [p for p in match if len(p) >= 2 and p[-1] == syi * nxp + sxi]
                    path = cand[0] if len(cand) == 1 else min(match)
                seen[lk].add(path)
                h = fnv(buf)
                if pt == 0:
                    wl = W.get(lk)
                    if not wl or wl[1] != h:
                        sc_fail.append([*lk, list(path), "W-hash"]); continue
                    ents = wl[2]
                else:
                    nxp = 2 if pt == 1 else 4; c = syi * nxp + sxi
                    fl = F.get((*lk, c))
                    if not fl or fl[1] != h:
                        sc_fail.append([*lk, list(path), "F-hash"]); continue
                    pl = P.get((*lk, c, h), [])
                    if not pl or any(e != pl[0] for e in pl):
                        sc_fail.append([*lk, list(path), f"P-{len(pl)}"]); continue
                    ents = pl[0]
                recs = leaf_all_records(buf)
                emit = [(i, c) for i, c, k in ents for _ in range(k)]
                if len(emit) != len(recs) or any(e[1] != rc[1] for e, rc in zip(emit, recs)):
                    sc_fail.append([*lk, list(path), f"count {len(emit)}/{len(recs)}"]); continue
                g1["sidecar_frames"] += 1
                src = [source_of(items, cells, lk, i) for i, _c in emit]
                lkey = (*lk, path)
                # duplicate cases (class>0, same type, byte-identical)
                byw = defaultdict(list)
                for (s, cls, code, wire), so in zip(recs, src):
                    if cls:
                        byw[(code, wire)].append((s, so, emit[s][0]))
                dups = {k: v for k, v in byw.items() if len(v) >= 2}
                is_tie = w["set"] == "tie"
                codes = {k[0] for k in dups}
                if is_tie:
                    codes |= {code for _s, cls, code, _w in recs if cls}
                hitmap, pieces_of = scan.hits(lk, path, ptype.get(lkey, 0), codes) if codes else ({}, {})
                if is_tie:
                    for (s, cls, code, wire), so in zip(recs, src):
                        if not cls:
                            continue
                        hs = hitmap.get((code, wire), [])
                        g2[f"hits_{min(len(hs), 2)}"] += 1
                        if len(hs) == 1:
                            want = hs[0]
                            got = so[1:] if so[0] in ("own", "routed") else None
                            if got == want:
                                g2["agree"] += 1
                            elif so[0] == "cover" and tuple(so[1:]) == tuple(want):
                                # same source shape, emitted in its interior-cover form (E1 kind 1)
                                g2["agree_cover_form"] += 1
                                g2_cover.append({"leaf": [*lk, list(path)], "shape": s, "scan": list(want),
                                                 "sidecar": list(so)})
                            else:
                                g2["disagree"] += 1
                                g2_dis.append({"leaf": [*lk, list(path)], "shape": s, "scan": list(want),
                                               "sidecar": list(so)})
                    for g in tie_leaves.get(lkey, []):
                        for cs in g["duplicate_class"]:
                            so = src[cs]
                            cands = [tuple(h["cid"][:3]) for h in g["hits"]]
                            prov_rows.append([lk[0], lk[1], lk[2], ",".join(map(str, path)), g["shape"], g["class"],
                                              cs, so[0], so[1], so[2], so[3], emit[cs][0],
                                              int(so[0] in ("own", "routed") and tuple(so[1:]) in cands),
                                              ";".join(",".join(map(str, c)) for c in cands)])
                for (code, wire), v in sorted(dups.items(), key=lambda kv: kv[1][0][0]):
                    hs = hitmap.get((code, wire), [])
                    em = [x[1] for x in v]
                    # emitter identity = source shape (sx, sy, k); a cover-form item is its source shape
                    ident = [tuple(e[1:]) for e in em]
                    reason = "ok"
                    if len(set(ident)) != len(ident):
                        reason = "shared_emitter"
                    elif sorted(ident) != hs:
                        reason = "hits_ne_emitters"
                    # distinguishing pieces: per hit, first leaf position of a piece not equal to this wire
                    dist = {}
                    for hcid in hs:
                        pos = [s for s, cls, c2, w2 in recs if cls and c2 == code and w2 != wire
                               and w2 in pieces_of.get(hcid, [])]
                        dist[hcid] = min(pos) if pos else None
                    cases.append({"leaf": [*lk, list(path)], "set": w["set"],
                                  "split": "derivation" if is_tie or not HOLDOUT(*lk) else "holdout",
                                  "code": code, "depth": len(path), "copies": [x[0] for x in v],
                                  "cover_form": sum(e[0] == "cover" for e in em),
                                  "emitters": [list(e) for e in em], "merged": [x[2] for x in v],
                                  "hits": [list(h) for h in hs], "reason": reason,
                                  "hit_class": {",".join(map(str, h)): src_class(*h) for h in hs},
                                  "dist_piece": {",".join(map(str, h)): p for h, p in dist.items()}})
            for lk in mine:
                if set(disc.get(lk, {})) != seen[lk]:
                    g1["disc_leaf_unmatched"] += len(set(disc.get(lk, {})) - seen[lk])
                    g1_fail.append([*lk, "unmatched", sorted(map(list, set(disc.get(lk, {})) - seen[lk]))])
            g1["cells"] += len(mine)
            L.clear_spool_caches()
            print(json.dumps({"window": w["name"], "t": round(time.time() - t0, 1), "cases": len(cases)}), flush=True)
    rules = score_rules(cases)
    prov_rows.sort()
    gzw(a.out_dir / "provenance.tsv.gz",
        ["level", "ix", "iy", "path", "group_shape", "group_class", "copy_shape", "emitter_kind",
         "emitter_hx", "emitter_hy", "emitter_ri", "merged_ordinal", "emitter_in_candidates", "candidates"],
        prov_rows)
    cases.sort(key=lambda c: (c["leaf"][:3], c["leaf"][3], c["copies"]))
    gzw(a.out_dir / "dup_cases.tsv.gz", ["case_json"], [json.dumps(c, sort_keys=True) for c in cases])
    prov_summary = summarize_prov(prov_rows, ties)
    out = {"gate1": dict(sorted(g1.items())), "gate1_fail": g1_fail, "sidecar_fail": sc_fail,
           "gate2": dict(sorted(g2.items())), "gate2_disagree": g2_dis, "gate2_cover_form": g2_cover, "provenance": prov_summary,
           "cases": {"n": len(cases), "by_reason_split": dict(sorted(Counter(f"{c['reason']}/{c['split']}"
                                                                          for c in cases).items())),
                     "strata": dict(sorted(Counter(f"{c['split']}/d{c['depth']}/{c['code']}/{'cover' if c['cover_form'] else 'ring'}"
                                                   for c in cases if c["reason"] == "ok").items()))},
           "rules": rules, "code_path": CODE_PATH,
           "holdout_definition": "sample-window cells with sha256('p63-holdout:{level},{ix},{iy}')[0] odd; "
                                 "all tie-window cells and even sample cells are derivation"}
    (a.out_dir / "rules.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("gate1", "gate2", "provenance", "cases")}, indent=1, sort_keys=True))
    print(json.dumps({"rules": {k: {kk: vv for kk, vv in v.items() if kk != "fails"} for k, v in rules.items()}},
                     indent=1, sort_keys=True))
    print(json.dumps({"wall_s": round(time.time() - t0, 1)}))
    if g1.get("frame_mismatch") or g1.get("disc_leaf_unmatched") or sc_fail or g2.get("disagree"):
        sys.exit(3)


def summarize_prov(rows, ties):
    by_group = defaultdict(list)
    for r in rows:
        by_group[(r[0], r[1], r[2], r[3], r[4])].append(r)
    c = Counter()
    for k, rs in by_group.items():
        cls = rs[0][5]
        em = [(r[7], r[8], r[9], r[10]) for r in rs]
        c[f"{cls}/groups"] += 1
        c[f"{cls}/copies_named"] += len(rs)
        c[f"{cls}/all_in_candidates"] += all(r[12] for r in rs)
        c[f"{cls}/distinct_emitters"] += len(set(em)) == len(em)
    c["groups_expected"] = len(ties["groups"])
    return dict(sorted(c.items()))


def rule_keys(c):
    ix, iy = c["leaf"][1], c["leaf"][2]
    cls = c["hit_class"]

    def k(h):
        return ",".join(map(str, h))
    return {
        "candidate_key_order": lambda h: (h[0], h[1], h[2]),
        "nearest_home": lambda h: (max(abs(h[0] - ix), abs(h[1] - iy)), h[0], h[1], h[2]),
        "spool_order_in_home": lambda h: (h[2], h[0], h[1]),
        "global_spool_order": lambda h: (h[1], h[0], h[2]),
        "block_order": lambda h: (h[1] // 256, h[0] // 256, h[1] // 64, h[0] // 32, h[1], h[0], h[2]),  # L0: block 32x64 cells, blockset 8x4 blocks
        "contiguous_block_emission": lambda h: (cls[k(h)], 0 if (h[0], h[1]) == (ix, iy) else 1, h[1], h[0], h[2]),
        "disc_record_order_distinguishing_piece": lambda h: (c["dist_piece"][k(h)] is None, c["dist_piece"][k(h)] or 0),
        "divided_leaf_keep_order": lambda h: (cls[k(h)], 0 if (h[0], h[1]) == (ix, iy) else 1, h[1], h[0], h[2]),
    }


def score_rules(cases):
    names = list(rule_keys({"leaf": [0, 0, 0, []], "hit_class": {}, "dist_piece": {}}).keys()) + ["first_emitter"]
    res = {n: {"derivation": [0, 0], "holdout": [0, 0], "fails": []} for n in names}
    for c in cases:
        if c["reason"] != "ok":
            continue
        truth = [tuple(e[1:]) for _s, e in sorted(zip(c["copies"], c["emitters"]))]
        hits = [tuple(h) for h in c["hits"]]
        for n, key in rule_keys(c).items():
            if n == "divided_leaf_keep_order" and c["depth"] < 2:
                continue
            if n == "disc_record_order_distinguishing_piece" and any(
                    c["dist_piece"][",".join(map(str, h))] is None for h in hits):
                res[n].setdefault("abstain", Counter())[c["split"]] += 1
                pred = None
            else:
                pred = sorted(hits, key=key)
            ok = pred == truth
            res[n][c["split"]][0] += ok; res[n][c["split"]][1] += 1
            if not ok and len(res[n]["fails"]) < 20:
                res[n]["fails"].append({"leaf": c["leaf"], "copies": c["copies"], "truth": truth, "pred": pred})
        first = [min(hits)] * len(hits)
        ok = first == truth
        res["first_emitter"][c["split"]][0] += ok; res["first_emitter"][c["split"]][1] += 1
    for n, r in res.items():
        full = all(r[s][1] > 0 and r[s][0] == r[s][1] for s in ("derivation", "holdout"))
        r["pass_100"] = full
        r["code_path"] = CODE_PATH if n in ("contiguous_block_emission", "divided_leaf_keep_order") else None
        r["accepted"] = bool(full and r["code_path"])
        if "abstain" in r:
            r["abstain"] = dict(r["abstain"])
    return res


if __name__ == "__main__":
    main()
