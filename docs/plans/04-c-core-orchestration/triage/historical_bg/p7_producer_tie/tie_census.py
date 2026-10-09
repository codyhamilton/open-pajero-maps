#!/usr/bin/env python3
"""Plan 63 Phase 1: generalised producer-tie census over every producer_ambiguous group of
p6_producer/verdicts.tsv.gz (98 groups / 47 leaves; includes the plan-46 scope-delta groups).

Per group (leaf, shape): the plan-46 candidate set (Moore R=8 U FarHomes, leaf_clip_geometry, same type,
33006aa clipper, piecewise byte hit), per hit: ring / blob / piece shas, piece -> leaf-shape map,
all-pieces-on-disc flag, ring stats; full-record duplicate class on 013586b5; per hit the unchanged
phase-23 decide limb (d35b565 clip into the leaf; byte or owner-exclusive vertex on a 4ed9cd80 same-type
record; failing = the group's dump vertices). Class T0/T1/T2 via parser/tools/producer_tie.py.
Deterministic JSON (sorted keys)."""
from __future__ import annotations

import argparse, csv, gzip, hashlib, json, sys, tempfile, atexit, shutil, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / p) for p in ("parser", "parser/tools",
                "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive")]
import bg_producer_scan as S  # noqa: E402
import bg_owner_exclusive as O  # noqa: E402
import producer_tie as PT  # noqa: E402
from leaf_io import cell_b4, frames, leaf_records  # noqa: E402

SCOPE_DELTA = {(0, 1481, 1288, (265,)), (0, 1753, 1158, (217,)), (0, 1754, 1158, (218,))}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def fsha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_groups(path):
    g = defaultdict(list)
    with gzip.open(path, "rt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if r["verdict"] != "producer_ambiguous":
                continue
            d = int(r["depth"])
            lk = (int(r["level"]), int(r["ix"]), int(r["iy"]), tuple(int(r[f"p{j}"]) for j in range(d)))
            g[(lk, int(r["shape"]))].append(r)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    for k in ("verdicts", "old_disc", "new_disc", "cenc_old", "cenc_excl", "spool", "out"):
        ap.add_argument("--" + k.replace("_", "-"), type=Path, required=True)
    a = ap.parse_args(argv)
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="p63_tie_")); atexit.register(shutil.rmtree, tmp, True)
    probe = O.load_probe(O.compile_probe(a.cenc_old.resolve(), (tmp / "p.so").resolve()))
    pex = O.load_probe(O.compile_probe(a.cenc_excl.resolve(), (tmp / "x.so").resolve()))
    shim = S.load_shim(S.compile_shim(a.cenc_old.resolve(), (tmp / "s.so").resolve()))
    groups = load_groups(a.verdicts)
    cells = {lk[:3] for lk, _ in groups}
    opt, npt = {}, {}
    ofr = frames(str(a.old_disc), cells, ptype_out=opt)
    nfr = frames(str(a.new_disc), cells, ptype_out=npt)
    from kiwiw.spool import SpoolReader
    spool = SpoolReader(str(a.spool)); far = S.FarHomes(a.spool, 0)
    by_leaf = defaultdict(list)
    for lk, s in groups:
        by_leaf[lk].append(s)
    out_groups = []
    with open(a.old_disc, "rb") as fo, open(a.new_disc, "rb") as fn:
        for lk in sorted(by_leaf):
            level, ix, iy, path = lk
            b4, cr, rect = S.leaf_clip_geometry(level, ix, iy, path, opt.get(lk, 0), cell_b4)
            b4e = (0.0, cr, 0.0, cr)
            recs = {s: (c, w, v) for s, c, w, v in leaf_records(fo, ofr[lk])}
            new = None
            if lk in nfr:
                new = defaultdict(lambda: (set(), set()))
                for _s, c, w, v in leaf_records(fn, nfr[lk]):
                    new[c][0].add(w); new[c][1].update((int(x), int(y)) for x, y in v)
            cands = list(S.fast_spool_candidates(spool, level, ix, iy, rect, b4, cr, 8, None,
                                                 extra_homes=far.query(ix, iy)))
            ex_cache = {}

            def clip_ex(cid, ring, code):
                k = (cid, code)
                if k not in ex_cache:
                    sz, _n, blob = O.clip_ring(pex, ring, rect=rect, tc=code, b4=b4e, cr=cr)
                    ex_cache[k] = (sz, blob, [(int(x), int(y)) for x, y in O.wire_vertices(blob)] if sz > 0 else [])
                return ex_cache[k]

            dup = PT.duplicate_pairs([(s, c, w) for s, (c, w, _v) in recs.items()], by_leaf[lk])
            for shape in sorted(by_leaf[lk]):
                rows = groups[(lk, shape)]
                code, wire, verts = recs[shape]
                assert code == int(rows[0]["code"]), (lk, shape)
                fail = {(int(r["vx"]), int(r["vy"])) for r in rows}
                hits = []
                for cid, ring, ll in cands:
                    if cid[3] != code:
                        continue
                    sz, _n, blob = O.clip_ring(probe, ring, rect=rect, tc=code, b4=b4e, cr=cr)
                    pieces = O.wire_records(blob) if sz > 0 else []
                    if not (sz > 0 and wire in pieces):
                        continue
                    # unchanged phase-23 decide limb with this candidate as producer
                    if new is None:
                        dec = "removed"; dx = {}
                    else:
                        s2, b2, src_v = clip_ex(cid, ring, code)
                        if s2 <= 0:
                            dec = "source-removed"; dx = {"sz": s2}
                        else:
                            other = [clip_ex(c2, r2, code)[2] for c2, r2, _l in cands if c2 != cid]
                            other = [v for v in other if v]
                            excl = O.owner_exclusive_vertices(src_v, other, rect, failing=fail)
                            bh = any(p in new[code][0] for p in O.wire_records(b2))
                            vh = any(v in new[code][1] for v in excl)
                            dec = "build:eo_bg_stitch" if (bh or vh) else "no-owner-exclusive-vertex"
                            dx = {"byte": int(bh), "vert": int(vh), "n_excl": len(excl)}
                    st = S.ring_stats(shim, ll, scale=(cr / (b4[3] - b4[2]), cr / (b4[1] - b4[0])))
                    hits.append({"cid": [int(x) for x in cid], "n_ring": int(len(ll)),
                                 "ring_sha256": sha(np.asarray(ring, np.float64).tobytes()),
                                 "clip_blob_sha256": sha(blob), "clip_pieces": len(pieces),
                                 "piece_sha256": [sha(p) for p in pieces],
                                 "piece_leaf_shapes": [sorted(s_ for s_, (c_, w_, _v) in recs.items()
                                                              if c_ == code and w_ == p) for p in pieces],
                                 "stats": {k: (v.item() if hasattr(v, "item") else v) for k, v in st.items()},
                                 "decide": dec, "decide_extra": dx})
                hits.sort(key=lambda h: h["cid"])
                for h in hits:
                    h["all_pieces_on_disc"] = all(len(x) > 0 for x in h["piece_leaf_shapes"])
                cls, why = PT.tie_class(hits)
                kinds = Counter(r["kind"] for r in rows)
                out_groups.append({
                    "leaf": [level, ix, iy, list(path)], "shape": shape, "code": int(code),
                    "ptype": opt.get(lk, 0), "rect": [float(v) for v in rect],
                    "rows": len(rows), "rows_by_kind": dict(sorted(kinds.items())),
                    "scope_delta": lk in SCOPE_DELTA,
                    "record_sha256": sha(wire),
                    "duplicate_class": next((d for d in dup if shape in d), [shape]),
                    "n_hits": len(hits), "hits": hits,
                    "clip_blob_identical": len({h["clip_blob_sha256"] for h in hits}) == 1 and len(hits) > 0,
                    "source_ring_identical": len({h["ring_sha256"] for h in hits}) == 1 and len(hits) > 0,
                    "class": cls, "class_reason": why,
                    "identity_lowest_key": list(PT.lowest_key(hits)) if cls == "T1" else None,
                    "candidate_ids": [h["cid"] for h in hits]})
    summ = {"groups": len(out_groups), "rows": sum(g["rows"] for g in out_groups),
            "leaves": len({tuple(map(str, g["leaf"])) for g in out_groups}),
            "by_class_groups": dict(sorted(Counter(g["class"] for g in out_groups).items())),
            "by_class_rows": dict(sorted(Counter(g["class"] for g in out_groups for _ in range(g["rows"])).items())),
            "by_kind_rows": dict(sorted(Counter(k for g in out_groups for k, n in g["rows_by_kind"].items()
                                                for _ in range(n)).items())),
            "scope_delta": {"groups": sum(g["scope_delta"] for g in out_groups),
                            "rows": sum(g["rows"] for g in out_groups if g["scope_delta"])},
            "inputs": {"verdicts": fsha(a.verdicts), "old_disc": fsha(a.old_disc)[:16],
                       "new_disc": fsha(a.new_disc)[:16], "cenc_old": fsha(a.cenc_old)[:16],
                       "cenc_excl": fsha(a.cenc_excl)[:16]}}
    a.out.write_text(json.dumps({"summary": summ, "groups": out_groups}, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ, indent=1))
    print(json.dumps({"wall_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
