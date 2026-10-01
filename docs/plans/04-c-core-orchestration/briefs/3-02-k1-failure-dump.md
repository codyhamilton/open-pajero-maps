# Brief: 3-02 — K1 failure dump (every failing item, with identity)

Consumer: 3-03 (adds diagnostic columns to the same rows), 3-05 (groups and classifies the rows), 3-90 (compares the post-fix dump with the pinned list).
Owned paths: `parser/kiwiw/_k1.h`, `parser/kiwiw/_k1.c`, `parser/kiwiw/_k1_bg.c`, `parser/kiwiw/_k1_cmp.c`, `parser/kiwiw/cenc.py` (K1 section only), `parser/tools/quantisation_roundtrip.py`, new `parser/tests/test_k1_dump.py`, `docs/provenance.md` (one entry for the dump files). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 3-01.
Runs alongside: 3-06 only.
Tier: Flash (mandatory Sonnet 5.5 review). RE-risky (moderate): edits the exact-count machinery in C. If Flash returns `over budget` or breaks equality twice, the orchestrator should hand this unit to a stronger worker.
Budget: 8 files to read, about 450 lines changed (about 250 C, 120 Python, 80 test), 70 tool turns. Past the budget, stop; write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned); commit what passes; report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — K1 check, Determinism, Evidence (contract bullets); Gates (the 120 s bar, the PSS ceiling).
2. `parser/kiwiw/_k1.h` — whole file (the `k1_sample` layout, `k1_acc`, `k1_push_sample`, `k1_ctx`, `kw_k1_band` signature).
3. `parser/kiwiw/_k1.c` — grep `k1_push_sample`, `k1_make_sample`, `kw_k1_band`, and every call site that builds a failing sample (`grep -n "k1_push_sample\|k1_make_sample" parser/kiwiw/_k1*.c`).
4. `parser/kiwiw/cenc.py` K1 section (lines about 600-870): `K1Acc`, `k1_check_band`, the descriptor check.
5. `parser/tools/quantisation_roundtrip.py` — `main`, the C engine driver (`grep -n "k1_check_band\|PssSampler\|def main\|_block_tasks"`), how the pool returns per-band accumulators.
6. `parser/tests/test_k1_points.py` (style, fixtures), `parser/tests/k1_fixtures.py` names only.

Read ranges and grep; do not read whole files to find one section.

## Goal

An opt-in dump mode that writes EVERY failing item of the five failing kinds (`name_anchor`, `background`, `background_boundary`, `interior_cover`, `completeness`) to disk as fixed-width binary rows with stable identity, so triage (3-05..3-08) can group, filter and enumerate failures by cell, type, leaf, shape and vertex instead of from the first 10 per kind per level. Default behaviour is unchanged.

## Contract

Cited from `DESIGN.md`: "**K1 check.** … Counts are exact; only samples are capped." and "**Determinism.** D1 and K1 output is byte-identical for any worker count. … Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal." and "**Layout single-source.** Every row layout is declared once in a C header and mirrored in Python by a checked descriptor, as `COLS[]` is today; a mismatch fails at load." and Gates: "C checker: ≤ 120 s wall at `-j 12` … peak memory measured as the sum of per-process PSS".

Decisions this brief makes (do not reopen):

- Dump row = the existing `k1_sample` fields (cell `ix`,`iy`, `vx`,`vy`, `reason`, `code` (the shape type for background kinds), leaf path `depth`,`p0..p6`, `lat`,`lon`,`err`) PLUS three new fields: `kind` (u8, index in `K1_KINDS`), `level` (u8), `shape` (i32: ordinal of the decoded background shape inside its leaf, -1 if the kind has none), `vert` (i32: vertex index inside that shape, -1 if none). Declared once in `_k1.h` as an X-macro (`K1_F_DUMP`), mirrored in `cenc.py` by the existing descriptor mechanism.
- Row order inside a band is the order K1 emits failing items today; bands are concatenated in task order of the driver's fixed band plan. The result is therefore independent of `-j`.
- Opt-in only: `quantisation_roundtrip.py --dump-failures DIR` (default off) with `--dump-kinds` (comma list, default all five). Workers write their own per-task part files `DIR/part_<task:05d>_<kind>.bin`; the driver concatenates parts in task order into `DIR/<kind>.bin` and writes `DIR/dump_manifest.json` (per kind: rows, row size, field list). Row buffers are NOT pickled through the pool. Delete part files after concatenation.
- With the dump off, the C path takes no extra branch per item; only one branch per FAILING item may be added. Counts, samples and report bytes with the dump off equal `output/scratch-2-07/k1_a.json` excluding `timing`/`wall_s`.
- The C side grows a per-band dump buffer with the same grow-and-retry rule D1 uses (return a "need more" code and have Python call again with a bigger buffer); no realloc surprises across the boundary.

## Changes

- `_k1.h`/`_k1.c`/`_k1_bg.c`/`_k1_cmp.c`: add the `k1_dump` struct, a dump sink in `k1_acc` (null when off), and an `emit` at each failing-item site. Every call site that pushes a failing sample for the five kinds also emits a dump row (the sites found by the grep in Required reading 3). `completeness` and `interior_cover` items have no vertex: `vert` = -1.
- `cenc.py` K1 section: layout descriptor, a `dump=` argument to `k1_check_band`, grow-and-retry.
- `quantisation_roundtrip.py`: the two flags, part files, concatenation, manifest. The JSON report gains `"dump": {kind: rows}` only when the dump is on.
- `docs/provenance.md`: one entry for `output/scratch-3-02/dump/` (what, source command, size, how to reproduce).

### Keep untouched

Counting logic, sample rule, explained counters, `K1_SAMPLE` (10), all kinds' arithmetic, D1, build entry points.

## Done evidence

Write `parser/tests/test_k1_dump.py` first (fails before: no `--dump-failures`).

- Fixture test: for every fault fixture in `k1_fixtures.py` that fails a background-family or name kind, the dump's row count per kind equals the report's `failing` for that kind, every sample in the report appears in the dump (compare `ix,iy,vx,vy,reason`), and dump bytes are identical at `-j 1`, `-j 4` and under a different band split used by existing band-split tests.
- Dump off: `.venv-rp/bin/python -m pytest parser/tests/test_k1_points.py parser/tests/test_k1_background.py parser/tests/test_k1_completeness.py parser/tests/test_goldens.py parser/tests/test_perf_inventory.py -q --basetemp=output/scratch-3-02/pytest` → pass (these also prove equality with the Python oracle).
- Full-disc run on G, under the heavy lock, dump on:
  `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock .venv-rp/bin/python parser/tools/quantisation_roundtrip.py --disc output/scratch-3-11/G/ALLDATA.KWI --spool output/extract_timing/spool -j 12 --dump-failures output/scratch-3-02/dump --out output/scratch-3-02/k1_dump.json`
  (foreground with `timeout 600000`; expected about 2 to 4 minutes). Then: `manifest rows` equal `1,438,558 / 16,549,569 / 824 / 752 / 1` for `background / background_boundary / interior_cover / completeness / name_anchor`; the report's `totals` equal `output/scratch-2-07/k1_a.json` `totals`.
- A `-j 1` dump on level 6 only (`--levels 6`), and the same at `-j 12`, byte-equal `*.bin` files (`cmp`).
- Dump off, full disc, one run under the lock: `timing.wall_s` ≤ 72 s and `report` equal to `k1_a.json` excluding `timing`/`wall_s` (use `output/scratch-2-07/cmp_j.py <a> <b>`). If wall is 72 to 90 s, run twice more and report the three values; above 90 s is a failure to report.
- A mutation (change one dump `emit` to skip `background_boundary` rows) makes the fixture test fail; revert.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Amendments (orchestrator, 2026-10-02, after Flash run 1)

- "Three new fields" lists four (`kind`, `level`, `shape`, `vert`); four is correct.
- Decision bullet 2 (task-order concatenation) conflicts with the byte-equality done evidence under a different band split. Resolution accepted: the driver sorts each kind canonically before writing `<kind>.bin`; the `k1_dump` padding is zeroed so files `cmp`.
- Dump-off must add NO per-queued-item work: the `shape`/`vert` side arrays in `_k1_bg.c` `qs_t` must be allocated, grown and written only when the dump sink is on. (Run 1 maintained them unconditionally; dump-off wall measured 84–91 s against the 72 s bar.)
- Dump-off timing proof is an A/B on a quiet machine: build HEAD (`git stash` is NOT allowed; use `git worktree` at HEAD into `output/scratch-3-02/headwt` or the saved `output/scratch-2-07` k1_a walls as reference only) and the working tree, run each dump-off full-disc `-j 12` under the heavy lock back to back, report both walls plus `uptime` load before each.
