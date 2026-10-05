# 3-01 — Demand attribution handoff

Status: **done with concerns**. The brief's timing stop applies: the 25-key
wrapper elapsed 19.377 s, projecting 601.5 s (10.02 min) for 776 keys. The
full run was not attempted. This commit contains the 335 result and the
25-key sample, rather than a complete 776-key prediction.

Added `triage/demand_attribution_3-01.py`, its TSV and evidence note, and this
report. The CLI accepts `--keys all`, comma-separated dump_rows, and
`--max-keys`. It resolves the checking block and row band through the oracle's
block enumeration and `PLAN_WORKERS=12`, constructs its actual `Region`, and
retains the halo, tall selection, and original source identities. Tall sets
are cached under the owned scratch path, with spool-index SHA, data size/mtime,
and oracle-source SHA validation. Every key is asserted present in the complete
block/band `_required_cells` union. Production C completeness failures are
compared with the Python required-minus-present set for each checked band.

Representability uses the imported EO decomposition, cell clipping and
`encoder_piece_densified` with the source's own `mc`, then production C
`bg_shape` on each EO face and target cell. JSON proofs also record original
C records, source coordinates, all matching branches, and disagreements.
The TSV has one row per distinct demander; `branch` is the first matching
a/b/c branch in checker order. No sampled demander matched multiple branches.

**335 answer:** `(level=0, ix=1379, iy=1138, type=288)` is demanded by
`tall=39083:L0:home(1379,1143):ordinal=0`, region shape 1531, via branch **c**.
The checking block is `[0,69,11,5,4,3,1]`, rectangle
`c=1376..1407, r=1088..1151`. This four-coordinate closed triangular sliver
has bbox raw x=5650352.1247232..5650750.806425601,
y=4649447.227391999..4718873.149439999. At the centre's y=4663296,
its interval is [5650431.651297411,5650431.651967155]; the centre x=5650432
is 0.348032845 raw outside. `TOL=0.5` makes the checker accept it. The ±32
search excluded the centre under strict EO; the source home was only five
rows away. Mirror: no emission (q=2, area2=0). C: zero original and EO-face
records. It is unrepresentable. This establishes the source; its Phase 3
disposition remains for the orchestrator.

**Counts, sampled only:** 26/776 keys have ≥1 demander; 28 distinct demanders;
branches a=0, b=27, c=1. All-demanders-unrepresentable keys: **26**.
Representable-demand exceptions: **none in the sample**. Error rows: 0.
C/Python checker disagreements: 0; mirror/C disagreements: 0.

Before changing code, the wrapped check of Phase 1's 335 witness printed
`dump_row 335: source=None` and failed with
`AssertionError: dump_row 335 has no named demander`, exit 1.
Afterward, `--keys 335` exited 0 and printed
`dump_row 335: demanders=1 error=None`. The 25-key run exited 0 with
25/25 selected keys attributed. A final 335 check after matching branch-a
reduction order exactly and removing an optional x-bbox prefilter also
exited 0. Artifact verification exited 0 and printed:

```
PASS: dump/evidence identity 776/776; sampled keys 26/26; unique demanders 28; error rows 0; C/Python and mirror/C disagreements 0
```

Logs: `output/scratch-14/runs/attribution_before.json`,
`attribution_335.json`, `attribution_25.json`, `attribution_335_final.json`,
and `attribution_verify.json`. Per-key proofs and the measured centre interval
are under `output/scratch-14/attribution/`. The internal 25-key timer was
18.889 s / 586.3 s projected; the wrapper's complete command elapsed time
includes startup and governs the stop decision.

Protected disc SHA256 before and after are identical:

| Disc | Before | After |
| --- | --- | --- |
| `output/scratch-3-11/G_new/ALLDATA.KWI` | `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` | `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` |
| `output/scratch-14/G_new/ALLDATA.KWI` | `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` | `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` |

Departures: the timing stop intentionally leaves 750 keys unfinished. The
brief does not specify which timer to project; this report explicitly uses
the required wrapper log, rather than silently choosing the shorter internal
timer. The report rubric is absent at the cited repository path; the identical
named rubric was read from the installed workflow plugin's
`tools/quality/checks/execution-report.json`. No workflow service was used.
The extra 335 run verifies the final arithmetic/attribution hardening without
attempting the prohibited full run.

Unfinished work: split the remaining dump_rows **25–334 and 336–775**, reusing
the CLI and cached tall set. Do not treat 26 as the full 3-03 prediction; merge
the split proofs/TSV by `(dump_row, shape_ref)` and require attribution of all
776 keys before establishing that prediction.

No contradiction with the cited demand or representability contracts was
observed. No non-trivial bug outside this unit's done evidence was found.
All parser sources, Phase 1/2 artifacts, protected discs, and spool were left
untouched; no output was deleted. Commit on the existing detached HEAD with
title `Attribute completeness demand for row 335 and timing sample`; no push.
