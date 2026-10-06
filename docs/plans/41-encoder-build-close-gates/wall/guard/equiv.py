"""Plan 41 guard fix: on the pinned spool, every level, the once-per-level screen (_name_rejects) equals the
pre-fix per-cell verdict (_guard_cell over every cell, private copy-on-write mappings), and the guarded private
data/lengths are byte-identical. Run inside the guard worktree (parser/ on sys.path). Read-only on the spool."""
import json, sys, time, hashlib
sys.path.insert(0, "parser")
import numpy as np
from kiwiw import cenc, mesh
SP = sys.argv[1]; out = {}
for lv in (0, 2, 4, 6, 8, 10, 12):
    t0 = time.perf_counter(); fast = cenc.E1Spool(SP, lv, guard_names=True); tf = time.perf_counter() - t0
    slow = cenc.E1Spool(SP, lv); slow.data = np.array(slow.data); slow.lengths = slow.lengths.copy()
    grid = mesh.CellGrid.from_reference(lv); t0 = time.perf_counter()
    for i in range(len(slow.offsets)): slow._guard_cell(i, grid)
    ts = time.perf_counter() - t0
    same = (fast.drops.tolist() == slow.drops.tolist() and fast.lengths.tolist() == slow.lengths.tolist()
            and hashlib.sha256(bytes(fast.data)).hexdigest() == hashlib.sha256(slow.data.tobytes()).hexdigest())
    out[lv] = {"cells": len(slow.offsets), "drops": int(slow.drops.sum()), "cells_with_drops": int((slow.drops > 0).sum()),
               "identical": bool(same), "guard_s_fast": round(tf, 3), "per_cell_scan_s": round(ts, 3)}
    print(lv, out[lv], flush=True); del fast, slow
json.dump(out, open(sys.argv[2], "w"), indent=1); print("EQUIVDONE", all(v["identical"] for v in out.values()))
