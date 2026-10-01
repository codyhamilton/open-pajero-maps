# Template: Phase 3 fix unit (authored inline by the orchestrator, NOT a refined brief)

Use this only after `triage/cause_table.md` exists and has been reviewed. Number fix units `3-10` to `3-89`; write each as `briefs/3-NN-<slug>.md` from `templates/brief.md` with the standard header, Tier `Flash`, `Review: Sonnet 5.5`, a countable budget, exact commands and paths. One unit per mechanism (one `checker` or `build` rule in the table, or one coherent set sharing one code location). Never invent a fix for a row without a cause.

The brief MUST state, copied from the cause table: the rule id(s), the cause, the code location (file, function), the row count the fix must move to 0, and the witness (the 200-group witness script path) the worker re-runs after the fix.

## Rules by cause class

Checker-side fix (rule, window, tie or tolerance in `_k1*.c`):
- Land the same rule change in the Python oracle `parser/tools/quantisation_roundtrip.py` in lockstep, so `--engine python` still equals C on a fixture set. The Python engine is deleted only in Phase 5.
- The build sha (87a01b14…) and Perth (da13a775…) stay byte-identical; the unit fails if either moves.
- A tolerance or rule change records: the cause (rule id), the reason, and the moved count per kind (before, after) in the unit's IMPLEMENTATION.md record. Tolerance changes are permitted only here in Phase 3 (Gates).
- Retain the inside-side tolerance mutation net from 3-04; its fixtures must still fail on their mutations.
- Dump-off K1 wall stays ≤ 72 s on the 3-11 disc (that is the Phase 2 margin to the 120 s bar); record it.

Build-side fix in C (`_e2.c`, `_cenc.c`):
- This is a recorded re-oracle per Assumption 1. Before editing, capture the full-AU disc and the Perth disc as the old oracle. After the fix, the unit records: the new full-AU sha, the new Perth sha only if it moved, and the EXACT differing cells (a list produced by a cell-by-cell compare, with counts per level), checked equal to the cells the cause table predicted. Any extra differing cell is a stop: report `blocked`.
- Goldens are re-captured only for affected goldens, named in the record. `-j 1` == `-j 12`, H-budget tests and the full-AU assembly time budget (under about 1 min) hold; a regression needs its cause named.
- Cody signs the re-oracle at phase close; do not delete the old oracle disc.
- Tier: RE-risky; mark it, and ask for Sonnet 5.5 review of the cell list.

Spool-side (extraction defect):
- Not fixed in Phase 3 (Assumption 4). The unit, if any, only freezes the pinned list: `docs/plans/04-c-core-orchestration/triage/pinned.tsv`, group granularity (the `k1_triage.py enumerate` format), header naming the dump and K1 commit, sha256 recorded in `IMPLEMENTATION.md`.

## Every fix unit

- Done evidence: a post-fix dump (or the dump-mode run) classified with `k1_triage.py classify` shows the unit's rule rows = 0 and every other rule's rows unchanged (the cause table's per-rule counts, quoted before and after).
- Heavy runs under `flock output/.heavy.lock`; no worker waits more than one command; a long run is kicked off by one unit and verified by another if it is about ten minutes or more.
- Serial: every unit touching `parser/kiwiw/` or the C library runs alone.
