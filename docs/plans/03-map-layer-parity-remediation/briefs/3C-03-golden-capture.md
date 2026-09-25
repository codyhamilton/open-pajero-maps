# Brief: 3C-03 — golden capture for the seven Contract T ranges

Consumer: 3C-07, 3C-08 and 3C-09, which must reproduce these goldens byte for byte; every later unit, which keeps them as regression tests.
Owned paths: new `parser/tools/golden_capture.py`, new `parser/tests/fixtures/goldens/`, new `parser/tests/test_goldens.py`, `docs/provenance.md` (append your own entry only), and this brief file (amendments only). Local-only outputs go under `output/goldens-3C/`. Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes. Commit the `docs/provenance.md` entry promptly: 3C-02 appends to the same file.
Depends on: 3C-01 (`--window`, `--frame-dump`).
Runs alongside: 3C-02, 3C-04, 3C-05, 3C-06.
Tier: Sonnet.
Budget: 8 files to read, about 400 lines to change, 70 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Contract T — tests", layer (c) (~466–478), Open Questions "Do fixture goldens for all seven ranges fit in git?" (decided), Phase 3C "Refine notes".
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-01-bench-window-baseline.md` — the `--window` and `--frame-dump` semantics.
3. `parser/kiwiw/spool.py` — `SpoolWriter`, `SpoolReader`, the `.idx`/`.data` layout per level.
4. `parser/tools/quantisation_roundtrip.py` — as precedent for a verification tool with its own spatial index (read the index part only).
5. `output/scratch-3-11/G/manifest.json` and a `--frame-digest` listing, to pick cells (divided parents are rows with `parcel_type != 0`).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Capture, from the current (3-11) build, a closed fixture spool and its expected frame bytes for each range Contract T names, so every port step has a byte-identity yardstick that does not depend on the Python build code surviving.

## Contract

- Contract T (c), cited: "A golden is a **closed fixture spool**: a cell range plus every cell whose shapes reach into it, in spool format, together with the expected frame bytes and their sha256. The pre-pass is never stored." The ranges: L0 urban dense; L0 sparse; a cell receiving borrowed edge shapes and one receiving an interior-cover rectangle; a divided L0 parent with trim and name halo; L2; a divided L4 parent; an edge-of-coverage cell.
- Decided (user): small goldens are committed; large ones stay local under `output/goldens-3C/`, recorded in `docs/provenance.md` with the regeneration command, and their tests skip when the spool is absent.
- Settled at refine: **closure is a conservative bounding-box superset.** The fixture spool holds every source cell at that level containing any shape whose lat/lon bbox meets the golden window's cells, sliced out through `SpoolReader` and rewritten through `SpoolWriter`. The tool has its own bbox index and never feeds the build (Contract B's verification-tool rule). A superset is harmless: extra sources only matter if they reach the window, and then they belong.
- Settled at refine: the golden test drives `build_alldata.py --spool <fixture> --window … --frame-dump …` as a subprocess, so it survives the port unchanged (it tests the build, not any module).

## Changes

- **`golden_capture.py`**: given a level and window, write the closed fixture spool, run the windowed build on it with `--frame-dump`, and store the spool, the dump and a small `golden.json` (level, window, frame count, per-frame sha256, total sha256, which Contract T range it covers, source cells included). A `--list` or `--select` helper may propose candidate cells from a frame digest and manifest, but the chosen windows are written into `golden.json` explicitly.
- **Closure proof**, per golden, three-way: the matching rows of the full-AU `--frame-digest` (one full build under the heavy lock, sha256 `87a01b14…`), a windowed build on the full spool, and a windowed build on the fixture spool must agree byte for byte. Any mismatch means closure or `--window` is wrong: find which and fix the tool (not the build; if `--window` is at fault, report it against 3C-01).
- Pick windows as small as each range allows (one or a few cells). The divided L0 parent must show both trim and name halo in the manifest-counter sense; the edge-of-coverage cell must include a mask-filled or coverage-boundary cell. The interior-cover case and the borrowed-edge case may be two goldens.
- **`test_goldens.py`**: for each golden, run the windowed build on its fixture spool with `--frame-dump` into tmp and compare every frame's bytes and sha256. Local-only goldens skip with a clear reason when `output/goldens-3C/` or its spool is absent. The test uses `-j 1`; add one `-j 4` case on the largest committed golden.
- Measure each fixture's size. Commit under `parser/tests/fixtures/goldens/` whatever is small (aim under ~2 MB per golden and ~10 MB total; state the figure you used). The rest goes to `output/goldens-3C/` with a provenance entry.

### Keep untouched

The build. This unit reads it and never edits it.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- One background script (Waiting rules): full-AU `--frame-digest` build under the heavy lock → sha256 `87a01b14…`; then per golden, the three-way comparison → identical.
- `.venv-rp/bin/python -m pytest parser/tests/test_goldens.py --basetemp=output/scratch-3C-03/pytest` → every golden passes (none skipped on this machine); report the wall.
- A table: golden, level, window, Contract T range covered, frames, fixture bytes, committed or local.
- `docs/provenance.md` has the local-golden entry with its regeneration command.

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
# output/scratch-3C-03/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-03
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
- Scratch: `output/scratch-3C-03/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-03/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
