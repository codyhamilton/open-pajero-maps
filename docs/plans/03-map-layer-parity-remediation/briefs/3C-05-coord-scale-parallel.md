# Brief: 3C-05 — `coord_scale` parallel and raw

Consumer: 3C-13, which runs `coord_scale` on the final disc as a Phase 3C Outcome check; Phases 3–10, which run it as a routine gate.
Owned paths: `parser/harness/checks/coord_scale.py`, `parser/compare_disc.py` (a workers option only), `parser/harness/context.py` (only if the workers value must travel through the check context), `parser/tests/test_harness_coord_scale.py`, `parser/tools/coord_scale_census.py` and `parser/tests/test_coord_scale_census.py` (only if they share the code you change; their output must stay identical), and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: nothing.
Runs alongside: 3C-01, 3C-02, 3C-03, 3C-04, 3C-06, 3C-07 (heavy runs serialised by the lock).
Tier: Sonnet.
Budget: 7 files to read, about 200 lines to change, 50 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Verification-tool decisions", the `coord_scale` bullet (~508–511).
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-11 stop record (~517): `coord_scale` took 783 s single-process.
3. `parser/harness/checks/coord_scale.py` — whole file (160 lines): `parcel_extent`, `judge`, `_run_coord_scale`.
4. `parser/harness/walk.py` — `iter_parcels`, `leaf_frame_range` (entry points only).
5. `parser/compare_disc.py` — `main`'s argparse (~51–70) and how checks get their context.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make the `coord_scale` check fast enough to run as a routine gate: decode in parallel over blocks and judge raw coordinates against the class range directly, with the identical verdict and counts.

## Contract

The "Verification-tool decisions" `coord_scale` bullet, cited: "It decodes in parallel over blocks. It judges raw coordinates against the class range directly, skipping `parcel_extent`'s lat/lon round-trip. On the 3-11 disc (`87a01b14…`) it must return the identical verdict and counts (PASS, 0 of 1,461,347 parcels, 73 classes) in ≤ 120 s at `-j 12`."

## Changes

- Partition the walk by block (or by an equivalent unit `walk` already exposes) across a process pool; each worker judges its parcels and returns counts per class plus bounded exceeding samples; the parent merges in a fixed order so the report is identical for any worker count.
- Judge the raw decoded coordinates against `walk.leaf_frame_range`'s range; drop the lat/lon `parcel_extent` round trip from the verdict path. If `parcel_extent` is still used for a human-readable sample, keep it off the hot path.
- `compare_disc.py --workers N` (default: today's behaviour, single process, so no other check changes). Pass it to the check through the context.
- Tests: the existing coord_scale tests keep passing; add a case that the verdict and counts are identical at 1 and 4 workers on a small disc (the Perth build, skip if absent), and a case with an injected out-of-range raw coordinate that is caught.

### Keep untouched

The check's id, its report keys and the verdict semantics. Other checks in `compare_disc.py`. The census's output, byte for byte, if you touch it.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_harness_coord_scale.py parser/tests/test_coord_scale_census.py --basetemp=output/scratch-3C-05/pytest` → passes.
- One background script (Waiting rules), under the heavy lock: `parser/compare_disc.py --generated output/scratch-3-11/G/ALLDATA.KWI --checks coord_scale --no-manifest --workers 12 --report output/scratch-3C-05/cs.json` → PASS, 0 of 1,461,347 parcels, 73 classes, wall ≤ 120 s. Compare the per-class counts with `output/scratch-3-11/cs_G.json`: identical.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

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
# output/scratch-3C-05/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-05
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
- Scratch: `output/scratch-3C-05/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-05/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
