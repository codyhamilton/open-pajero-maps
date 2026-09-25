# Brief: 3C-01 — bench split, `--window`, `--frame-dump`, and the 3-11 baseline

Consumer: every later 3C unit, which reads its Contract H evidence from the bench record this unit adds and gates on the run-to-run spread it measures. 3C-03, which captures goldens through `--window` and `--frame-dump`. The orchestrator, which records the baseline in `IMPLEMENTATION.md`.
Owned paths: `parser/build_alldata.py` (CLI, planning, timers only), `parser/kiwiw/cenc.py` (wrapper timers and call counters only), `parser/kiwiw/_cenc.c` (C-side timer accumulators and a getter only), `parser/tools/bench_build.py`, new `parser/tests/test_bench_record.py`, and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: nothing.
Runs alongside: 3C-04, 3C-05 (full builds serialised by the heavy lock).
Tier: Sonnet.
Budget: 8 files to read, about 300 lines to change, 60 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Contract H — hot paths and budgets" (lines ~417–448) and Phase 3C's "Stages" (Stage 0) and "Refine notes".
2. `docs/ARCHITECTURE.md` — "Output invariance" (timings never reach the manifest) and "Partition and merge".
3. `parser/build_alldata.py` — `_plan_chunks` (~366), `_encode_chunk` (~423), `_encode_level_indexed` (~460), `run` (~598), `main` (~756).
4. `parser/kiwiw/cenc.py` — the ctypes calls (`CellEncoder.encode`, `bg_shape_records`, `measure_content`).
5. `parser/tools/bench_build.py` — whole file (short).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Stage 0 instrumentation and baseline: make the build report Contract H's per-level Python / C / handoff split and call counts in a bench record, add the two CLI hooks golden capture needs, and measure the 3-11 build three times to fix the run-to-run spread every later gate uses. Output bytes do not change.

## Contract

- Contract H, "Done evidence" and "Measurement". Timings go to the bench record, never the manifest.
- Phase 3C Outcome: the disc stays sha256 `87a01b14…` and the Perth build stays `da13a775064…` at `-j 1` and `-j 4`. This unit is output-invariant.
- Settled at refine: a cell range is today's `_plan_chunks` row span (`jobs*64` weight-balanced chunks); E1 and E2 will be called once per such range.

## Changes

- **`--bench PATH`** on `build_alldata.py` writes a JSON bench record. Per level: `wall_s` (parent wall for the level), `prepass_s` (parent time in the overlap pre-pass), `py_s`, `c_s`, `handoff_s` (worker time summed over workers), `ranges` (chunks encoded), `workers`, and `calls` (a dict of call counts). Top level: `wall_s` (whole run) and `outside_encode_s` (wall minus the sum of level walls). Without `--bench`, nothing is timed beyond today's cost and the manifest is unchanged.
- **C time** comes from C-side accumulators in `_cenc.c` (`clock_gettime(CLOCK_MONOTONIC)` around each exported entry point's body, summed into a static), read and reset by a new exported getter. **Handoff** is the wrapper's time around each ctypes call minus the C time for that call. **Python** is the rest of the worker's task time. Workers return their three sums with each chunk result; the parent sums them per level.
- **Call counts** for the baseline are the legacy per-cell ones: `kw_encode_cell`, `kw_measure_cell` (the measure path) and the per-shape background call behind `bg_shape_records`, per level. Name the keys so E1/E2 counts (`e1`, `e2`) slot in later.
- **`bench_build.py`**: if the command writes a `--bench` record, merge its wall and peak RSS into the same JSON (or document that it keeps a separate file); do not change its existing CLI.
- **`--window LEVEL IX0 IY0 IX1 IY1`** (half-open cell rectangle): builds that one level only, emits frames only for cells inside the rectangle, and reads source shapes from the whole level's spool so borrowed shapes from outside the window still arrive. Mask-filled empty cells are emitted only inside the window. This is planning, not build logic: it only narrows which cells are emitted. Ranges still partition the whole level (settled at refine), so later E1 and E2 call counts stay equal.
- **`--frame-dump PATH`** writes every emitted frame's bytes to `PATH.bin` and an index `PATH.tsv` with columns `level ix iy parcel_type sub_ix sub_iy offset len sha256`, in the build's canonical frame order. It works with or without `--window`, and at any `-j`, with identical output.
- **`parser/tests/test_bench_record.py`**: the Perth fixture build with `--bench` writes a record with every key above, and its `ALLDATA.KWI` and `manifest.json` are byte-identical to a run without `--bench`; a `--window` + `--frame-dump` run over a small Perth L0 rectangle gives the same rows and bytes as the matching rows of a full Perth `--frame-digest`.
- **Baseline.** Three full-AU `-j 12` builds with `--bench`, each under the heavy lock, each checked against sha256 `87a01b14…`, plus Perth at `-j 1` and `-j 4` (`da13a775064…`). Report the median wall and the spread (max minus min). If the spread exceeds 10 % of the median, find out why (contention, cold cache, thermal) before reporting; do not just widen the gate.

### Keep untouched

Every byte the build writes, and the manifest's keys and values. `_cenc.c`'s encode logic: only timer lines and the getter are added. `--frame-digest` keeps its current format.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_bench_record.py --basetemp=output/scratch-3C-01/pytest` → fails before, passes after.
- `.venv-rp/bin/python -m pytest parser/tests --basetemp=output/scratch-3C-01/pytest` → the same pass count as before plus the new tests, no new failures.
- One background script (Waiting rules): Perth `-j 1` and `-j 4` → both sha256 `da13a775064…`; then three full-AU `-j 12` builds with `--bench`, each under the heavy lock → each sha256 `87a01b14…`, 1,731,021,568 B, manifest counters equal to `output/scratch-3-11/G/manifest.json`'s.
- Report: the per-level table (wall, prepass, py / C / handoff scaled to wall, ranges, call counts) for the median run; the three walls, the median and the spread; the bench record paths.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Contract H evidence

This unit touches a hot path, so its done evidence includes Contract H's (`DESIGN.md`, "Contract H — hot paths and budgets", "Done evidence", "Measurement", "Regressions"), read from the build's bench record (`--bench`, from 3C-01):

- per level: the Python / C / handoff split, scaled to wall as in the 2026-09-25 profile, `stage_wall = level_wall × stage_worker_s / total_worker_s`;
- the full-AU `-j 12` wall as the **median of three** builds, each under the heavy lock;
- the E1 and E2 call counts per level (equal once E1/E2 are wired; the legacy per-cell counts before that);
- each figure set against the 3C budgets: L0 ≤ 38 s with pre-pass ≤ 5 s, L2 ≤ 2 s, L4–L12 together ≤ 2 s, outside-encode ≤ 10 s, wall ≤ 60 s.

Budgets are gates at Phase 3C's close (3C-13). For this unit the gate is Contract H's regression rule: the median wall may not rise above the previous recorded build by more than the 3C-01 run-to-run spread (recorded in `IMPLEMENTATION.md`'s Phase 3C run record) unless you name the specific mechanism. A trade-off is not a mechanism.

## Waiting rules

Contract W (`DESIGN.md`, "Contract W — worker waiting rules"), verbatim:

1. Chain every slow check (builds, `compare_disc`, round-trips, probes) in one background script that writes a status line per step: `STEP <name> OK|FAIL <seconds>`, then a final `DONE` or `ABORT`.
2. Block on that script with **one** monitor whose match covers every terminal state (`DONE`, `ABORT`, any `FAIL`, script exit).
3. Never end the turn to wait. A subagent that ends its turn has ended. Never spend no-op turns polling.
4. Never pipe a long command through `| tail` (or any filter that hides progress and defeats backgrounding). Redirect to a log file and read the log.
5. A check slow enough to need many waits is a finding to investigate, not a thing to wait out.

How this phase applies it (refine-settled, binding):

- Never end your turn to wait. For a subagent, ending the turn ends the agent.
- No no-op commands (`true`, `echo`, `sleep` on their own) and no polling turns.
- The background script sends each step to its own log and appends `STEP <name> OK <seconds>` or `STEP <name> FAIL <rc> <seconds>` to one status file, then `ALLDONE` (which carries Contract W's `DONE`). A `trap … EXIT` appends `ABORT` if the script ends without writing `ALLDONE`. Stop at the first `FAIL`.
- Block with **one** command: `until grep -qE 'ALLDONE|ABORT|FAIL|Traceback' <status>; do sleep 10; done` under a real timeout that covers every terminal state, including heavy-lock wait (use at least 60 minutes for any script that takes the heavy lock). Use the Monitor tool, or one Bash call with `timeout`. If the timeout fires, that is a finding: read the logs, do not re-arm blindly.
- Never pipe long commands through `| tail` or `| head`. Read logs with the Read tool or a bounded `grep`.
- A check needing many waits is a finding. Report it.

Skeleton (adapt the steps; keep the mechanics):

```bash
#!/usr/bin/env bash
# output/scratch-3C-01/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-01
export TMPDIR=$S/tmp; mkdir -p "$TMPDIR"
ST=$S/status.txt; : > "$ST"
trap 'grep -q ALLDONE "$ST" || echo ABORT >> "$ST"' EXIT
step() { local n=$1; shift; local t0=$SECONDS
  "$@" > "$S/$n.log" 2>&1; local rc=$?
  if [ $rc -eq 0 ]; then echo "STEP $n OK $((SECONDS-t0))" >> "$ST"
  else echo "STEP $n FAIL $rc $((SECONDS-t0))" >> "$ST"; exit $rc; fi; }
cd "$R"
step build1 flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_build.py \
     --out $S/bench1.json -- .venv-rp/bin/python parser/build_alldata.py \
     --spool output/extract_timing/spool --out $S/G1/ALLDATA.KWI -j 12
echo ALLDONE >> "$ST"
```

`flock` sits outside `bench_build.py`, so lock wait never counts as build wall.

## Machine facts

- **One heavy job at a time.** Every full-Australia build and every `-j 12` verification or timing run (`quantisation_roundtrip`, `compare_disc … coord_scale`, E1 full-level scans) runs under `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Other units hold it too. Waiting on it is normal, not a finding. Pytest, Perth fixture builds and windowed builds do not need it.
- Reference disc R: `/run/media/codyh/464210-8480`.
- Spool: `output/extract_timing/spool`. `build_alldata.py`'s default (`output/spool`) is not it. Always pass `--spool`.
- Python: `.venv-rp/bin/python` from the repo root.
- Scratch: `output/scratch-3C-01/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-01/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
