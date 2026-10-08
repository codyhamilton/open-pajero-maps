"""Plan 46: producer-tie probe for the 6 S02-scope groups that fail the full predicate as
producer_ambiguous: (1481,1288,p265) shapes 0/2, (1753,1158,p217) 1/2, (1754,1158,p218) 1/3
(Design ruling 09:24).

For each record, list every same-type candidate whose clip contains the record bytes (RC2 piecewise,
RC3 far homes, RC4 divided-leaf geometry, RC5 same type), and test whether the tied candidates are
byte-identical over the whole compared extent = the full clip blob into the leaf (all pieces, not
just the matching piece). Source-ring identity is recorded as additional evidence.
Writes ties.json. Deterministic tie-break (if identical): lowest (level,hx,hy,ri).
"""
import json, sys, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / p) for p in ('parser', 'parser/tools',
                'docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive')]
import numpy as np
import bg_producer_scan as S, bg_owner_exclusive as O
from leaf_io import cell_b4, frames, leaf_records
from kiwiw.spool import SpoolReader

def one_leaf(lk, shapes, disc, spool, far, probe, shim):
    level, ix, iy, path = lk
    pt = {}; fr = frames(disc, {lk[:3]}, ptype_out=pt)
    b4, cr, rect = S.leaf_clip_geometry(level, ix, iy, path, pt.get(lk, 0), cell_b4)
    with open(disc, 'rb') as fh:
        rec = {s: (c, w, v) for s, c, w, v in leaf_records(fh, fr[lk])}
    res = {"leaf": [level, ix, iy, list(path)], "ptype": pt.get(lk, 0), "rect": list(map(int, rect)), "records": []}
    cands = list(S.fast_spool_candidates(spool, level, ix, iy, rect, b4, cr, 8, None,
                                         extra_homes=far.query(ix, iy)))
    for shape in shapes:
        code, wire, verts = rec[shape]
        hits = []
        for cid, ring, ll in cands:
            if cid[3] != code:
                continue
            sz, n, blob = O.clip_ring(probe, ring, rect=rect, tc=code, b4=(0, cr, 0, cr), cr=cr)
            if sz > 0 and wire in O.wire_records(blob):
                ra = np.asarray(ring, dtype=np.int64)
                hits.append({"cid": [int(x) for x in cid],
                             "n_ring": int(len(ll)),
                             "ring_sha256": hashlib.sha256(ra.tobytes()).hexdigest(),
                             "ll_sha256": hashlib.sha256(np.asarray(ll, np.float64).tobytes()).hexdigest(),
                             "clip_blob_sha256": hashlib.sha256(blob).hexdigest(),
                             "clip_pieces": len(O.wire_records(blob)),
                             "piece_sha256": [hashlib.sha256(pc).hexdigest() for pc in O.wire_records(blob)],
                             "piece_leaf_shapes": [[s_ for s_, (c_, w_, _v) in sorted(rec.items()) if c_ == code and w_ == pc]
                                                   for pc in O.wire_records(blob)],
                             "stats": {k: (v if not isinstance(v, (np.integer, np.floating)) else v.item())
                                       for k, v in S.ring_stats(shim, ll, scale=(cr / (b4[3] - b4[2]), cr / (b4[1] - b4[0]))).items()}})
        hits.sort(key=lambda h: (0, h["cid"][0], h["cid"][1], h["cid"][2]))
        ident_blob = len({h["clip_blob_sha256"] for h in hits}) == 1
        ident_ring = len({h["ring_sha256"] for h in hits}) == 1
        ident_pieces = len({tuple(sorted(h["piece_sha256"])) for h in hits}) == 1
        for h in hits:
            h["all_pieces_on_disc"] = all(len(x) > 0 for x in h["piece_leaf_shapes"])
        res["records"].append({"shape": shape, "code": int(code), "rows_record_sha256": hashlib.sha256(wire).hexdigest(),
                               "n_hits": len(hits), "hits": hits,
                               "clip_blob_identical": ident_blob, "source_ring_identical": ident_ring,
                               "piece_multiset_identical": ident_pieces,
                               "candidates_with_all_pieces_on_disc": [h["cid"] for h in hits if h["all_pieces_on_disc"]],
                               "verdict": ("proven-producer-tied" if len(hits) >= 2 and ident_blob
                                           else "open-rc-owed" if len(hits) >= 2 else "not-tied"),
                               "tie_break_lowest_key": hits[0]["cid"] if hits else None})
    return res


def main(argv):
    disc, spool_dir, cenc, work, out = argv
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    probe = O.load_probe(O.compile_probe(Path(cenc).resolve(), (work / 'p.so').resolve()))
    shim = S.load_shim(S.compile_shim(Path(cenc).resolve(), (work / 's.so').resolve()))
    spool = SpoolReader(spool_dir); far = S.FarHomes(spool_dir, 0)
    LEAVES = [((0, 1481, 1288, (265,)), (0, 2)), ((0, 1753, 1158, (217,)), (1, 2)),
              ((0, 1754, 1158, (218,)), (1, 3))]
    allres = []
    for lk, shapes in LEAVES:
        allres.append(one_leaf(lk, shapes, disc, spool, far, probe, shim))
    res = {"leaves": allres}
    Path(out).write_text(json.dumps(res, indent=1, default=str) + "\n")
    for L in res["leaves"]:
        print(L["leaf"], json.dumps([{k: r[k] for k in ('shape', 'n_hits', 'clip_blob_identical', 'source_ring_identical', 'verdict', 'tie_break_lowest_key')} for r in L["records"]]))

if __name__ == "__main__":
    main(sys.argv[1:])
