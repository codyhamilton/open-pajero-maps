# Brief: 3C-10 — harness and writer tests stop fabricating frames through `synth`

Consumer: 3C-12, which deletes `synth.py`'s build encoders and needs no test to import them; 3C-13, whose Outcome grep requires it.
Owned paths: `parser/tests/test_harness_core.py`, `parser/tests/test_harness_profile.py`, `parser/tests/test_harness_spotcheck.py`, `parser/tests/test_alldata_writer.py`, `parser/tests/test_name_encode.py`, new fixture bytes under `parser/tests/fixtures/harness/`, a new fixture generator under `parser/tests/fixtures/harness/` (script, not a test), new boundary tests in new `parser/tests/test_e2_names.py` (or similar) for what `test_name_encode.py`'s synth-itself cases covered, and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-09.
Runs alongside: 3C-11.
Tier: Sonnet.
Budget: 10 files to read, about 500 lines to change, 80 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Contract T (~450–483), especially "Current exposure": "Harness tests that use it to fabricate fixture frames switch to layer (a) fixtures produced through E2, or to committed fixture bytes."
2. `parser/tests/boundary.py` (3C-02) and `parser/tests/test_e2.py` (3C-07, 3C-09): how to build a fixture spool and run E1/E2.
3. The five owned test files: grep for `synth` first, then read only the fixtures and the cases that use them.
4. `parser/kiwiw/alldata_writer.py` — `SynthParcel`, `build_alldata_kwi` (entry points only).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Remove every test dependency on `synth`'s build encoders, so the encoders can be deleted: tests that need frame bytes get them from E2 (at test time through the boundary helpers, or as committed bytes produced once through E2), and tests of `synth` itself become boundary tests of E2.

## Contract

- Contract T, cited above, and: "The build logic has no Python copy, not even as a test oracle." "No test imports a deleted module, and no test compares C against a Python encoder" (Phase 3C Outcome).
- A test's intent is preserved: a harness check that must FAIL on a planted defect still gets a frame with that defect. Where the defect cannot be produced through E2 (for example a deliberately bad name in a spot-check), plant it in the fixture spool content, or patch the committed bytes at a documented offset; say which in the test.
- `test_name_encode.py`'s cases that test `synth`'s name encoder itself are replaced by boundary tests (name records through E2, decoded with `kiwiw.name.decode_name_frame`) with the same coverage per supported type; cases that only use the decoder stay.

## Changes

- Prefer building fixtures at test time through `boundary.py` (small, no committed bytes). Commit bytes only where test-time generation would be slow; then commit the generator script and a sha256 beside the bytes.
- Keep every existing assertion's meaning; list any assertion you had to drop and why.

### Keep untouched

Every file outside the owned paths. Assertions about the harness's behaviour.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `git grep -nE "kiwiw\.synth|from kiwiw import .*synth|build_(road|background|name|map)_frame_bytes|encode_name_record" -- parser/tests/test_harness_core.py parser/tests/test_harness_profile.py parser/tests/test_harness_spotcheck.py parser/tests/test_alldata_writer.py parser/tests/test_name_encode.py` → nothing.
- `.venv-rp/bin/python -m pytest parser/tests --basetemp=output/scratch-3C-10/pytest` → same pass count or higher; list tests removed and their replacements.
- No full build is needed: this unit does not change the build path.

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
# output/scratch-3C-10/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-10
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
- Scratch: `output/scratch-3C-10/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-10/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
