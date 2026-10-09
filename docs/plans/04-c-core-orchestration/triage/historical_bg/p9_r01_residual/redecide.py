#!/usr/bin/env python3
"""Plan 62 Phase 2: R01 residual re-decide, RC ablation, same-type audit, R-G5-4-c gates G-c2..G-c4.

Input: census_join (all 95,139 plan-44/45 rows joined to the plan-46 scan; census_join.py).
Groups = (leaf, shape, code). For every group of the requested modes:
  residual: every non-build group (plan-44 residual of R-G5-4-a/b): configs FULL, -RC2..-RC5, PLAN44
            (exhaustive, not a sample), attribution per parser/tools/r01_redecide.attribute.
  audit:    every plan-44 proven (build) group: FULL and PLAN44; the PLAN44 producer's type vs the
            record code (same-type audit of the 87,743 proven rows).
  ceiling:  R-G5-4-c groups: FULL producer in the old (pardiv1) leaf; G-c3 per-row src evidence;
            G-c4 clip into every d35b565 leaf covering the old leaf rect (byte/OE witness restricted
            to the old rect).
Old disc 33006aa ref (record bytes; same disc as the plan-46 scan), new disc d35b565 ref
(4ed9cd80), producer encoder 33006aa cenc, decide clipper d35b565 cenc (as phase23 decide).
Deterministic outputs (gzip mtime 0, sorted keys); run twice and cmp.
"""
from __future__ import annotations

import argparse, csv, gzip, json, sys, time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p6_producer")]

from phase23 import det_gz_text, close_det, sha, relp, content_sha  # noqa: E402
import r01_redecide as rd  # noqa: E402

ABL = ("FULL", "-RC2", "-RC3", "-RC4", "-RC5", "PLAN44")


def rss_mib():
    try:
        for ln in open("/proc/self/status"):
            if ln.startswith("VmHWM:"):
                return int(ln.split()[1]) / 1024.0
    except OSError:
        pass
    return -1.0


def load_groups(path, modes):
    groups = defaultdict(list)
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            d = int(r["depth"])
            lk = (int(r["level"]), int(r["ix"]), int(r["iy"]), tuple(int(r[f"p{j}"]) for j in range(d)))
            oc = rd.old_class(r["p44_decision"])
            if r["parent"] == "R-G5-4-c":
                mode = "ceiling"
            elif oc == "build":
                mode = "audit"
            else:
                mode = "residual"
            if mode in modes:
                groups[(lk, int(r["shape"]), int(r["code"]))].append({**r, "_mode": mode, "_old": oc})
    return groups


def load_src(path):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f, delimiter="\t"):
            k = (int(r["level"]), int(r["ix"]), int(r["iy"]), int(r["p0"]), int(r["shape"]), int(r["vert"]))
            out[k] = (int(r["src_ix"]), int(r["src_iy"]), int(r["src_rec"]), int(r["src_nv"]), r["reason"])
    return out


class Leaf:
    """Per-leaf caches: candidate lists per (geometry, R, far) and clip results per probe."""

    def __init__(self, ctx, lk):
        self.ctx, self.lk = ctx, lk
        self.cands = {}
        self.clip_old = defaultdict(dict)   # geom -> {(cid, tc): (size, blob, vset)} (find_producer memo)
        self.clip_ex = defaultdict(dict)    # geom -> {(cid, tc): (size, blob, verts)}

    def geom(self, divided, path=None, ptype=None):
        c = self.ctx
        level, ix, iy, p = self.lk
        if path is None:
            path, ptype = p, c.old_pt.get(self.lk, 0)
        if divided:
            b4, cr, rect = c.ps.leaf_clip_geometry(level, ix, iy, path, ptype, c.cell_b4)
        else:
            b4, cr = c.cell_b4(level, ix, iy)
            cr = float(cr); rect = (0.0, 0.0, cr, cr)
        return (tuple(b4), float(cr), tuple(float(v) for v in rect))

    def get_cands(self, g, R, far):
        k = (g, R, far)
        if k not in self.cands:
            c = self.ctx
            level, ix, iy, _ = self.lk
            extra = c.far(level).query(ix, iy) if far else ()
            self.cands[k] = c.ps.fast_spool_candidates(c.spool, level, ix, iy, g[2], g[0], g[1], R, None,
                                                       extra_homes=extra)
        return self.cands[k]

    def clip_excl(self, g, cid, ring, code):
        m = self.clip_ex[g]
        k = (cid, code)
        if k not in m:
            c = self.ctx
            b4e = (0.0, g[1], 0.0, g[1])
            sz, _n, blob = c.clip_ring(c.probe_excl, ring, rect=g[2], tc=code, b4=b4e, cr=g[1])
            m[k] = (sz, blob, [(int(x), int(y)) for x, y in c.wire_vertices(blob)] if sz > 0 else [])
        return m[k]


class Ctx:
    def __init__(self, a, cells):
        from kiwiw.spool import SpoolReader
        from bg_owner_exclusive import compile_probe, load_probe, clip_ring, wire_vertices, \
            owner_exclusive_vertices, wire_records, find_producer
        from leaf_io import cell_b4, frames, leaf_records
        import bg_producer_scan as ps
        import tempfile
        self.ps, self.cell_b4, self.leaf_records = ps, cell_b4, leaf_records
        self.clip_ring, self.wire_vertices, self.wire_records = clip_ring, wire_vertices, wire_records
        self.oe, self.find_producer = owner_exclusive_vertices, find_producer
        import atexit, shutil
        tmp = Path(tempfile.mkdtemp(prefix="p62_redecide_"))
        atexit.register(shutil.rmtree, tmp, True)  # scratch hygiene: probe .so temp dir
        self.probe_old = load_probe(compile_probe(a.cenc_old.resolve(), (tmp / "probe_old.so").resolve()))
        self.probe_excl = load_probe(compile_probe(a.cenc_excl.resolve(), (tmp / "probe_excl.so").resolve()))
        self.old_pt, self.new_pt = {}, {}
        self.old_fr = frames(str(a.old_disc), cells, ptype_out=self.old_pt)
        self.new_fr = frames(str(a.new_disc), cells, ptype_out=self.new_pt)
        self.spool = SpoolReader(str(a.spool))
        self.spool_dir = a.spool
        self._far = {}

    def far(self, level):
        if level not in self._far:
            self._far[level] = self.ps.FarHomes(self.spool_dir, level)
        return self._far[level]


def run_config(ctx, leaf, cfg, rec, srs, new_by_code, divided_leaf):
    """-> dict(cls, status, pid, ...) for one group under one config."""
    shape, code, wire, verts = rec
    oc = srs[0]["_old"]
    if cfg.name in ("-RC4", "PLAN44") and divided_leaf and srs[0]["parent"] != "R-G5-4-c":
        # plan 44 never decided divided leaves (skip_divided_leaf): the -RC4 limb is plan 44's rule
        return {"cls": "skip", "status": "skip", "pid": None}
    g = leaf.geom(cfg.divided)
    R = rd.radius(cfg, oc, srs[0]["p44_recover_r"])
    cands = leaf.get_cands(g, R, cfg.far)
    cx = rd.filter_type(cands, code, cfg.same_type)
    dump_v = {(int(r["s46_vx"]), int(r["s46_vy"])) for r in srs}
    failing = dump_v & set(verts)
    b4e = (0.0, g[1], 0.0, g[1])
    status, pid = ctx.find_producer(ctx.probe_old, wire, cx, rect=g[2], tc=code, b4=b4e, cr=g[1],
                                    record_verts=verts, failing=failing, clip_cache=leaf.clip_old[g],
                                    piecewise=cfg.piecewise)
    out = {"status": status, "pid": list(pid) if pid is not None else None, "R": R, "n_cands": len(cx)}
    if rd.producer_class(status) == "ambiguous" and cfg.name == "FULL" and new_by_code is not None:
        # plan-63 evidence: the decide limb under each byte-hit (tied) candidate
        cxs = {cid for cid, _ in cx}
        ties = sorted(cid for (cid, tc), (sz, blob, _v) in leaf.clip_old[g].items()
                      if tc == code and sz > 0 and cid in cxs and wire and wire in ctx.wire_records(blob))
        out["tie_decide"] = [[list(t), decide_limb(ctx, leaf, g, cands, t, code, dump_v, new_by_code,
                                                    cfg.piecewise, "unique-byte")["cls"]] for t in ties]
    if rd.producer_class(status) != "unique":
        out["cls"] = rd.producer_class(status)
        return out
    if new_by_code is None:
        out["cls"] = "removed"
        return out
    out.update(decide_limb(ctx, leaf, g, cands, pid, code, dump_v, new_by_code, cfg.piecewise, status))
    out["producer_same_type"] = int(int(pid[3]) == code)
    return out


def decide_limb(ctx, leaf, g, cands, pid, code, dump_v, new_by_code, piecewise, status):
    ring = next(rg for cid, rg, *_ in cands if cid == pid)
    sz, blob, src_v = leaf.clip_excl(g, pid, ring, code)
    if sz <= 0:
        return {"cls": "source-removed", "sz": sz}
    others = []
    for cid, org, *_ in cands:
        if cid == pid:
            continue
        s2, _b2, v2 = leaf.clip_excl(g, cid, org, code)
        if s2 > 0:
            others.append(v2)
    excl = ctx.oe(src_v, others, g[2], failing=dump_v)
    nw, nv = new_by_code.get(code, (set(), set()))
    bh = rd.byte_hit(ctx.wire_records(blob), blob, nw, piecewise)
    vh = any(v in nv for v in excl)
    return {"cls": rd.decide_class(producer_status=status, leaf_on_new=True, clip_size=sz,
                                   byte_hit=bh, vert_hit=vh),
            "byte": int(bh), "vert": int(vh), "n_excl": len(excl)}


def ceiling(ctx, leaf, rec, srs, src_tab, full):
    """G-c3 per row and G-c4 covering-leaf decide for one R-G5-4-c group."""
    level, ix, iy, path = leaf.lk
    shape, code, wire, verts = rec
    g_old = leaf.geom(True)
    old_rect = g_old[2]
    cands_old = leaf.get_cands(g_old, 8, True)
    pid = tuple(full["pid"]) if full.get("pid") else None
    dump_v = {(int(r["s46_vx"]), int(r["s46_vy"])) for r in srs}
    # G-c3: per-row known answer against the K1 src (nearest same-type shape within 64 raw)
    rows3 = []
    for r in srs:
        s = src_tab[(level, ix, iy, path[0], shape, int(r["vert"]))]
        ka = rd.src_known_answer(s[:3], pid)
        ev = {"src": list(s[:3]), "src_nv": s[3], "src_reason": s[4], "known_answer": ka}
        if ka == "mismatch":
            hit = next(((cid, rg) for cid, rg, *_ in cands_old if cid[:3] == tuple(s[:3])), None)
            ev["src_in_cands"] = int(hit is not None)
            if hit is not None:
                cid, rg = hit
                ev["src_tc"] = int(cid[3]); ev["src_same_type"] = int(cid[3] == code)
                b4e = (0.0, g_old[1], 0.0, g_old[1])
                sz, _n, blob = ctx.clip_ring(ctx.probe_old, rg, rect=old_rect, tc=code, b4=b4e, cr=g_old[1])
                ev["src_clip_size"] = sz
                ev["src_byte_hit"] = int(sz > 0 and wire in ctx.wire_records(blob))
        rows3.append(ev)
    # G-c4: every d35b565 leaf over the old rect
    new_leaves = {}
    for nk in ctx.new_fr:
        if nk[:3] == (level, ix, iy):
            gn = leaf.geom(True, path=nk[3], ptype=ctx.new_pt.get(nk, 0))
            if gn[0] != g_old[0] or gn[1] != g_old[1]:
                raise RuntimeError(f"frame differs old/new for {nk}: {gn[:2]} vs {g_old[:2]}")
            new_leaves[nk] = gn
    cover = rd.covering_leaves(old_rect, {k: v[2] for k, v in new_leaves.items()})
    per = []
    any_build = any_clip = False
    if pid is None:
        return rows3, {"cls": rd.producer_class(full["status"]), "covering": [list(k[3]) for k in cover]}
    with open(ctx.new_disc_path, "rb") as fn:
        for nk in cover:
            gn = new_leaves[nk]
            inter = rd.rect_intersection(old_rect, gn[2])
            nl = Leaf(ctx, nk)
            cands_n = nl.get_cands(gn, 8, True)
            ring = next((rg for cid, rg, *_ in cands_n if cid == pid), None)
            e = {"leaf": list(nk[3]), "rect": list(gn[2]), "inter": list(inter)}
            if ring is None:
                e["why"] = "producer bbox misses this leaf"; per.append(e); continue
            sz, blob, src_v = nl.clip_excl(gn, pid, ring, code)
            e["sz"] = sz
            if sz <= 0:
                per.append(e); continue
            any_clip = True
            others = [v2 for cid, org, *_ in cands_n if cid != pid
                      for s2, _b, v2 in [nl.clip_excl(gn, cid, org, code)] if s2 > 0]
            excl = [v for v in ctx.oe(src_v, others, gn[2], failing=dump_v) if rd.strictly_inside(v, old_rect)]
            nw, nv = set(), set()
            for _s, c2, w2, v2s in ctx.leaf_records(fn, ctx.new_fr[nk]):
                if c2 == code:
                    nw.add(w2); nv.update((int(x), int(y)) for x, y in v2s)
            pieces = ctx.wire_records(blob)
            bh_any = any(p in nw for p in pieces)
            bh_old = any(p in nw and all(rd.strictly_inside(v, old_rect) or
                                         (old_rect[0] <= v[0] <= old_rect[2] and old_rect[1] <= v[1] <= old_rect[3])
                                         for v in ctx.wire_vertices(p)) for p in pieces)
            vw = sorted(v for v in excl if v in nv)
            e.update(byte_any=int(bh_any), byte_in_old_rect=int(bh_old), n_excl_in_old=len(excl),
                     vert_witness=[list(v) for v in vw[:4]], n_vert_witness=len(vw))
            if bh_old or vw:
                any_build = True
            per.append(e)
    cls = "build" if any_build else ("no_oe" if any_clip else "source-removed")
    return rows3, {"cls": cls, "covering": [list(k[3]) for k in cover], "per_leaf": per}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", type=Path, required=True)
    ap.add_argument("--src80", type=Path, required=True)
    ap.add_argument("--old-disc", type=Path, required=True)
    ap.add_argument("--new-disc", type=Path, required=True)
    ap.add_argument("--cenc-old", type=Path, required=True)
    ap.add_argument("--cenc-excl", type=Path, required=True)
    ap.add_argument("--spool", type=Path, required=True)
    ap.add_argument("--modes", default="residual,audit,ceiling")
    ap.add_argument("--out", type=Path, required=True, help="groups .tsv.gz; rows80 and json beside it")
    a = ap.parse_args(argv)
    t0 = time.time()
    modes = set(a.modes.split(","))
    groups = load_groups(a.census, modes)
    src_tab = load_src(a.src80)
    cells = {k[0][:3] for k in groups}
    ctx = Ctx(a, cells)
    ctx.new_disc_path = a.new_disc
    by_leaf = defaultdict(list)
    for k in groups:
        by_leaf[k[0]].append(k)
    out_rows, rows80 = [], []
    trans = Counter(); attr = Counter(); audit = Counter(); repro = Counter(); fullchk = Counter()
    with open(a.old_disc, "rb") as fo, open(a.new_disc, "rb") as fn:
        for li, lk in enumerate(sorted(by_leaf)):
            leaf = Leaf(ctx, lk)
            old = {s: (s, c, w, v) for s, c, w, v in ctx.leaf_records(fo, ctx.old_fr[lk])}
            new_by_code = None
            if lk in ctx.new_fr:
                new_by_code = defaultdict(lambda: (set(), set()))
                for _s, c2, w2, v2 in ctx.leaf_records(fn, ctx.new_fr[lk]):
                    ws, vs = new_by_code[c2]
                    ws.add(w2); vs.update((int(x), int(y)) for x, y in v2)
            divided = ctx.old_pt.get(lk, 0) in (1, 2) and len(lk[3]) >= 2
            for gk in sorted(by_leaf[lk]):
                srs = groups[gk]
                _, shape, code = gk
                s, c, w, v = old[shape]
                if c != code:
                    raise RuntimeError(f"record type mismatch {gk}: disc {c}")
                rec = (shape, code, w, [(int(x), int(y)) for x, y in v])
                mode = srs[0]["_mode"]; oc = srs[0]["_old"]
                names = ("FULL", "PLAN44") if mode == "audit" else ABL
                res = {n: run_config(ctx, leaf, rd.CONFIGS[n], rec, srs, new_by_code, divided) for n in names}
                full = res["FULL"]
                fullchk[(mode, full["status"] == srs[0]["s46_producer_raw"])] += len(srs)
                row = {"mode": mode, "parent": srs[0]["parent"], "level": lk[0], "ix": lk[1], "iy": lk[2],
                       "path": ".".join(map(str, lk[3])), "shape": shape, "code": code, "n_rows": len(srs),
                       "old_class": oc, "s46_producer_raw": srs[0]["s46_producer_raw"],
                       "full_class": full["cls"]}
                if mode == "residual":
                    abl = {n[1:]: res[n]["cls"] for n in ABL if n.startswith("-")}
                    at = rd.attribute(oc, full["cls"], abl)
                    row["attribution"] = "+".join(at) if at else "none"
                    trans[(srs[0]["parent"], oc, full["cls"])] += len(srs)
                    for f_ in at or ["none"]:
                        attr[(srs[0]["parent"], oc, full["cls"], f_)] += len(srs)
                if "PLAN44" in res:
                    p = res["PLAN44"]
                    repro[(mode, oc, p["cls"])] += len(srs)
                    row["plan44_reproduces"] = int(p["cls"] == oc)
                if mode == "audit":
                    p = res["PLAN44"]
                    st = p.get("producer_same_type")
                    p44home = json.loads(srs[0]["p44_extra"] or "{}").get("producer_home")
                    tag = ("same_type" if st == 1 else "cross_type" if st == 0 else "no_unique_producer")
                    audit[(tag, full["cls"])] += len(srs)
                    row["audit"] = tag
                    row["p44_home_matches_plan44cfg"] = int(bool(p.get("pid")) and p44home == p["pid"][:2])
                if mode == "ceiling":
                    r3, c4 = ceiling(ctx, leaf, rec, srs, src_tab, full)
                    row["full_class"] = c4["cls"]
                    trans[(srs[0]["parent"], oc, c4["cls"])] += len(srs)
                    for r, ev in zip(srs, r3):
                        rows80.append({"level": lk[0], "ix": lk[1], "iy": lk[2], "path": row["path"],
                                       "shape": shape, "vert": r["vert"], "vx": r["s46_vx"], "vy": r["s46_vy"],
                                       "producer": json.dumps(full.get("pid")), "gc3": ev["known_answer"],
                                       "gc3_evidence": json.dumps(ev, sort_keys=True, separators=(",", ":")),
                                       "gc4_class": c4["cls"]})
                    row["gc4"] = json.dumps(c4, sort_keys=True, separators=(",", ":"))
                    # G-c2 attribution on the producer class (plan 45's verdict was a producer verdict)
                    pab = {n[1:]: rd.producer_class(res[n]["status"]) if res[n]["status"] != "skip" else "skip"
                           for n in ABL if n.startswith("-")}
                    at = rd.attribute(oc, rd.producer_class(full["status"]), pab)
                    row["attribution"] = "+".join(at) if at else "none"
                    for f_ in at or ["none"]:
                        attr[(srs[0]["parent"], oc, "producer:" + rd.producer_class(full["status"]), f_)] += len(srs)
                row["configs"] = json.dumps(res, sort_keys=True, separators=(",", ":"))
                out_rows.append(row)
            if li % 200 == 0:
                print(f"[{time.time()-t0:7.1f}s] leaf {li}/{len(by_leaf)} rss_hwm={rss_mib():.0f}MiB", flush=True)
    keys = []
    for r in out_rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    f = det_gz_text(a.out)
    w = csv.DictWriter(f, fieldnames=keys, delimiter="\t", lineterminator="\n", restval="")
    w.writeheader(); w.writerows(out_rows); close_det(f)
    summ = {"groups": len(out_rows), "rows": sum(r["n_rows"] for r in out_rows),
            "transitions": {"|".join(k): n for k, n in sorted(trans.items())},
            "attribution": {"|".join(k): n for k, n in sorted(attr.items())},
            "plan44_reproduction": {"|".join(map(str, k)): n for k, n in sorted(repro.items())},
            "full_matches_s46": {f"{m}|{int(b)}": n for (m, b), n in sorted(fullchk.items())},
            "same_type_audit": {"|".join(k): n for k, n in sorted(audit.items())},
            "inputs": {"census": [relp(a.census), sha(a.census)], "src80": [relp(a.src80), sha(a.src80)],
                       "old_disc_sha": sha(a.old_disc)[:16], "new_disc_sha": sha(a.new_disc)[:16],
                       "cenc_old_sha": sha(a.cenc_old)[:16], "cenc_excl_sha": sha(a.cenc_excl)[:16]},
            "file": relp(a.out), "sha256": sha(a.out), "content_sha256": content_sha(a.out)}
    if rows80:
        p80 = a.out.with_name(a.out.name.replace(".tsv.gz", "_rows80.tsv.gz"))
        f = det_gz_text(p80)
        w = csv.DictWriter(f, fieldnames=list(rows80[0]), delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(rows80); close_det(f)
        summ["rows80"] = {"file": relp(p80), "sha256": sha(p80),
                          "gc3": dict(Counter(r["gc3"] for r in rows80)),
                          "gc4": dict(Counter(r["gc4_class"] for r in rows80))}
    perf = {"wall_s": round(time.time() - t0, 1), "vmhwm_mib": round(rss_mib(), 1)}
    a.out.with_name(a.out.name.replace(".tsv.gz", ".json")).write_text(json.dumps(summ, indent=1) + "\n")
    a.out.with_name(a.out.name.replace(".tsv.gz", ".perf.json")).write_text(json.dumps(perf) + "\n")
    print(json.dumps({k: summ[k] for k in ("groups", "rows", "transitions", "full_matches_s46")}, indent=1))
    print(json.dumps(perf))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
