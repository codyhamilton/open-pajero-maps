#!/usr/bin/env python3
"""Plan 46: prove fast_spool_candidates + clip cache == reference path, row-exact.

Samples leaves from the 013586b5 dump (both kinds), runs scan_leaf_rows with
(a) reference: leaf_io.spool_candidates + _enrich_cands, find_producer uncached
(b) fast: fast_spool_candidates with direct_spool_cell, leaf-scoped clip cache
and asserts candidate lists and every output row dict are identical.
"""
import json, random, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive")]
from kiwiw.spool import SpoolReader
from leaf_io import spool_candidates, cell_b4, leaf_rect_raw, frames, leaf_records, _spool_cell, set_spool_cell_cache_max
set_spool_cell_cache_max(4096)
import bg_owner_exclusive as boe
import bg_producer_scan as ps

DUMP = ROOT / "output/scratch-46/dump_013586b5"
DISC = ROOT / "output/scratch-45/ref_33006aa/ALLDATA.KWI"
SP = "/home/codyh/workspace/open-pajero-maps/output/extract_timing/spool"
CENC = ROOT / "output/scratch-46/cenc_33006aa/kiwiw/_cenc.c"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
probe = boe.load_probe(boe.compile_probe(CENC, Path("/tmp/p46_eq_probe.so")))
shim = ps.load_shim(ps.compile_shim(CENC, Path("/tmp/p46_eq_shim.so")))
sp = SpoolReader(SP)
rng = random.Random(46)
res = {"leaves": 0, "rows": 0, "cand_mismatch": 0, "row_mismatch": 0}
for kind in ("background", "background_boundary"):
    rows, n, _ = ps.load_dump_kind(DUMP, kind)
    picks = sorted(rng.sample(range(n), N))
    for i0 in picks:
        d = int(rows["depth"][i0]); path = tuple(int(rows[f"p{j}"][i0]) for j in range(d))
        lk = (int(rows["level"][i0]), int(rows["ix"][i0]), int(rows["iy"][i0]), path)
        lv, ix, iy, _ = lk
        lo, hi = max(0, i0 - 20000), min(n, i0 + 20000)
        blk = rows[lo:hi]
        m = np.nonzero((blk["level"] == lv) & (blk["ix"] == ix) & (blk["iy"] == iy) & (blk["depth"] == d))[0] + lo
        m = np.array([i for i in m if tuple(int(rows[f"p{j}"][i]) for j in range(d)) == path])
        b4, cr = cell_b4(lv, ix, iy); rect = leaf_rect_raw(lv, len(path))
        ref = ps._enrich_cands(sp, lv, list(spool_candidates(sp, lv, ix, iy, rect, b4, cr, neighbourhood=8)), _spool_cell)
        fast = ps.fast_spool_candidates(sp, lv, ix, iy, rect, b4, cr, 8, None)  # direct cell reader
        if ref != fast:
            res["cand_mismatch"] += 1
        fr = frames(str(DISC), {(lv, ix, iy)})
        with open(DISC, "rb") as fh:
            dbs = {s: (c, w, v) for s, c, w, v in leaf_records(fh, fr[lk])} if lk in fr else None
        orig = boe.find_producer
        ps.find_producer = lambda *a, clip_cache=None, **k: orig(*a, **k)  # uncached reference
        try:
            out_ref = ps.scan_leaf_rows(rows, m, probe=probe, shim=shim, spool_cands=ref, rect=rect, cr=cr, disc_by_shape=dbs)
        finally:
            ps.find_producer = orig
        out_fast = ps.scan_leaf_rows(rows, m, probe=probe, shim=shim, spool_cands=fast, rect=rect, cr=cr, disc_by_shape=dbs)
        if out_ref != out_fast:
            res["row_mismatch"] += 1
        res["leaves"] += 1; res["rows"] += len(out_fast)
print(json.dumps(res))
sys.exit(0 if res["cand_mismatch"] == 0 and res["row_mismatch"] == 0 else 1)
