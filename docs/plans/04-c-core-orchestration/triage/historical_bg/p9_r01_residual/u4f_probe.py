#!/usr/bin/env python3
"""Plan 62: replay plan 44 Unit 4f's producer-ring lookup for the 5 rows whose plan-44 class
(disagree_source_removed) the PLAN44 matcher config does not reproduce (leaf 0/1249/881/(1569,), shape 1).
Unit 4f (proven_fixed_recovers.py L236-258) keeps only producer_home and picks the FIRST candidate ring
homed there; this prints that ring vs the true producer and the d35b565 clip size of each."""
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[6]
sys.path[:0] = [str(ROOT / "parser"), str(ROOT / "parser/tools"),
                str(ROOT / "docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive")]
from kiwiw.spool import SpoolReader
from bg_owner_exclusive import compile_probe, load_probe, clip_ring
from leaf_io import cell_b4, leaf_rect_raw, spool_candidates
level, ix, iy, path, code, R, home = 0, 1249, 881, (1569,), 288, 13, (1262, 881)
spool = SpoolReader(sys.argv[1])
pe = load_probe(compile_probe(Path(sys.argv[2]).resolve(), Path(tempfile.mkdtemp()) / "pe.so"))
b4, cr = cell_b4(level, ix, iy); rect = leaf_rect_raw(level, len(path)); b4e = (0.0, float(cr), 0.0, float(cr))
cands = list(spool_candidates(spool, level, ix, iy, rect, b4, cr, neighbourhood=R))
out = []
for cid, ring in cands:
    if (int(cid[0]), int(cid[1])) == home:
        sz, _n, _b = clip_ring(pe, ring, rect=rect, tc=code, b4=b4e, cr=float(cr))
        out.append({"cid": [int(v) for v in cid], "clip_size_d35b565": sz})
res = {"leaf": [level, ix, iy, list(path)], "shape": 1, "home": list(home), "R": R,
       "unit4f_first_ring": out[0]["cid"] if out else None, "rings_in_home": out,
       "plan46_producer": [1262, 881, 1, 288]}
Path(sys.argv[3]).write_text(json.dumps(res, indent=1) + "\n"); print(json.dumps(res))
