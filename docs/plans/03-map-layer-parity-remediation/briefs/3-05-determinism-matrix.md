# Brief: 3-05 — the determinism matrix (kickoff and hand-off)

Consumer: 3-06, which verifies the phase outcome from the shas this unit hands off.
Owned paths: none under version control. Write builds and logs only into your scratch directory. Touch no tracked file, and do not promote anything into `output/`.
Commits: nothing to commit — this unit changes no tracked file. Report only.
Depends on: 3-03.
Runs alongside: nothing (it saturates the machine).
Budget: 3 files to read, no code to change, 30 tool turns. The wall clock is long — roughly an hour — and that is expected; the turn budget is what you count. Past the budget, stop and report `over budget` with whichever builds completed and their shas, **in your report back, not in a file**.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "#### Phase 3 — Outcome, as amended", the byte-identity clause.
2. 3-03's report back (your orchestrator has it) — the exact build command and the sha it produced.
3. `docs/plans/02-build-performance.md` — the assembly figures (263 s at `-j 12`; `-j 1` was 11–17 min and was **not** re-run after the parallel work landed, so budget generously for it) and the recorded Perth fixture behaviour.

Read ranges and grep; do not read a whole file to find one section, and truncate long tool output.

## Goal

Produce the evidence for one clause of the phase outcome and nothing else: that the rebuilt disc is byte-identical across repeated builds and across worker counts. This unit exists separately because the runs take far longer than a unit should hold; it starts them, collects shas, and hands off.

## Contract

Cited, DESIGN.md, "#### Phase 3 — Outcome, as amended":

> two builds are byte-identical at worker counts 1, 4 and 12

Binding:

- **Six builds: two each at `-j 1`, `-j 4`, `-j 12`.** All six from the same spool (`output/spool`), the same commit, the same command apart from `-j` and `--out`. All six shas must be equal — to each other and to the sha 3-03 reported. The clause is satisfied only by that single value.
- **Change nothing.** If a build's sha disagrees, do not investigate by editing code and do not re-run hoping it settles. Record which builds produced which sha, in order, and report `needs context`. A worker-count-dependent sha is a real defect in someone else's unit and diagnosing it is not this unit's job — though if the first differing offset is cheap to get from `parser/harness/bytediff.py`, include it.
- Run the builds **sequentially**, not concurrently: concurrent builds contend for memory (assembly peaks around 3 GB at `-j 12`) and would make the timings meaningless.
- Record for each build: worker count, wall time, peak RSS if cheap to capture, output size in bytes, and sha256. Sizes must all match too.
- Write every output into your scratch directory. Do not overwrite `output/ALLDATA.KWI` and do not touch `output/manifest.json`; 3-06 promotes the canonical disc. Never edit anything under `.claude/worktrees/`.
- Delete the scratch builds you no longer need as you go — six copies of a 1.4 GB disc is 8 GB — but keep one, and name its path in your report so 3-06 can promote it instead of rebuilding.

Python is `.venv-rp/bin/python`. The spool is `output/spool` (`output/manifest.json`'s `spool_dir` records a stale `.claude/worktrees/...` path; ignore it).

## Changes

None. This unit runs commands and reports.

### Keep untouched

Every tracked file. `output/ALLDATA.KWI`, `output/manifest.json`, `output/spool`. All plan documents.

## Done evidence

- A table of six rows: `-j`, run number, wall time, byte size, sha256. Report it in full.
- The explicit statement of whether all six shas are equal, and whether they equal the sha 3-03 reported.
- The scratch path of the retained build.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then the six-row table, the equality statement, the retained build's path, and any deviation from this brief and why. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Amendment after 3-02 (orchestrator, 2026-09-24)

- **Spool path.** Use `output/extract_timing/spool` (binary `KWSPIDX1`, stats match the manifest's `spool_stats`) wherever this brief says `output/spool`; `output/spool` is a legacy pickle spool that `SpoolReader` rejects.
- **Baseline.** 3-02 removed the encoders' stored-pixel preference; road nodes' y moved from the spool's stale y-down pixels onto the settled y-up orientation. The pre-3-03 baseline is full disc `9407122122b9…` / Perth `99d72f0b1cf14b8b…`; `51c254ac…` / `e275879f…` are retired (they predate 2-06).
- **Scratch.** `/tmp` hits its disk quota on full builds; put scratch under `output/scratch-<unit>/` (gitignored) and set `TMPDIR` there.

## Amendment after the R background-clip research (orchestrator, 2026-09-24)

Unit 3-07 (`briefs/3-07-clip-to-frame.md`) is inserted before 3-05: G now clips background geometry to the frame as R does, which changes the disc again. This unit depends on 3-07 as well; any baseline sha quoted above is superseded by 3-07's reported build. The per-vertex quantisation round-trip is measured over **written vertices after clipping** (3-07's definition in `quantisation_roundtrip.py`), not over raw spool vertices.
