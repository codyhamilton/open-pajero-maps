# Phase 2 route selection (verdict A)

Pick **(a): counted assembly admission on the in-force spool**. Scores below
are against Phase 2's fixed outcome; 2 = direct fit, 1 = extra proof needed,
0 = conflicts with the outcome.

| Criterion | (a) Assembly guard | (b) Cell-scoped regeneration |
| --- | --- | --- |
| Spool protection | 2: private copy-on-write mappings, original files never writable | 2: new scratch spool, original preserved |
| Provenance | 2: one existing spool plus an explicit counted build rule | 1: hybrid old/new extractor inputs need a cell-source ledger |
| Confinement | 2: remove only rejected name columns; preserve original frame allocations | 1: must prove regenerated cell differs only by O03 despite tip extractor drift |
| Future re-extract behaviour | 2: applies the same half-open lattice span as plan 18; clean inputs drop zero | 1: fixes this stale cell only; regenerated inputs still need coverage admission |
| Perth / goldens risk | 2: in-span columns pass through unchanged; no C source change | 1: regeneration can carry unrelated extractor changes |
| Test surface | 2: synthetic column, count, frame-extent and confinement controls | 1: needs cell extraction and hybrid-spool equivalence controls |
| Total | 12 | 7 |

Reject (b): it adds hybrid-spool provenance and a regenerated-cell equivalence
obligation without improving the measured one-name outcome. Full re-extraction
(c) remains rejected for the reasons recorded in the [plan 29 record](../../../29-k1-name-anchor-failure.md).

The chosen guard uses `E1Spool(..., guard_names=True)` only from assembly.
All other readers, including K1, use the original read-only mapping. Anchored
names outside the lattice's half-open latitude or wrapped longitude span are
removed from private column records before E1/E2; every source-row rejection
is counted once in E1, merged per level into stdout and manifest key
`out_of_span_names_dropped`. Missing anchors are unchanged; non-finite anchors
fail explicitly. Admission matches plan 18, rather than a cell-rectangle test
that could reject valid halo names. Every worker filters its whole level to
protect cross-range halo inputs; counts use disjoint source row partitions.

The packed writer would relocate later frames after a smaller frame. For a
chunk containing drops, assembly also probes its original unfiltered input,
requires identical frame topology, and pads shorter filtered frames with zeros
to their original extents. This preserves every later DSA and table entry.
A topology change or enlargement fails for root-cause work. The original
probe is scratch only, never assembled into the successor disc.

No `_cenc.c` change: plan 28's producer pin remains valid. No K1 code or
tolerance change. Historical discs and spool are never opened writable.
`diff_disc.py` proves byte confinement in both layouts; `compare_k1.py` enforces
Phase 1's exact per-level drops and per-kind/per-level successor totals.

Synthetic checks passed. Execute's guarded measurements produced successor
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`,
with AU L0 drops 1 and all other levels 0. R name parity, Perth equality and
golden results are recorded in the plan 29 record and the retained witnesses.
The O03 note carries the measured successor pin.
