# Brief: 3C-12 — delete `synth`'s build encoders, `clip.py`, the per-shape C call and the last `KIWIW_NO_C`

Consumer: 3C-13, whose Outcome greps require these deletions.
Owned paths: `parser/kiwiw/synth.py` (delete the build encoders, or the whole file if nothing else needs it), `parser/kiwiw/clip.py` (delete), `parser/kiwiw/mesh.py` (receives `frame_range`), `parser/kiwiw/road_writer.py`, `parser/kiwiw/background_writer.py` and `parser/kiwiw/cenc.py` (import updates; `cenc.py` also loses `bg_shape_records`), `parser/kiwiw/_cenc.c` (remove the `kw_bg_shape` export; its internals stay if E2 uses them), `parser/kiwiw/alldata_writer.py` (the `KIWIW_NO_C` text and no-compiler fallback at ~869 only), `parser/tests/test_cenc.py` (remove the remaining C-vs-Python cases; delete the file if nothing is left), `parser/tests/test_clip.py` (delete), `parser/tests/test_synth_map_frame.py` and `parser/tests/test_synth_vectorized.py` (delete), `parser/tests/test_build_alldata.py` (import fixes only), and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-10, 3C-11.
Runs alongside: nothing.
Tier: Sonnet.
Budget: 10 files to read, about 150 lines changed plus deletions, 60 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 3C Outcome (the grep list), Stage 2's deletion list, Contract B "The R round-trip writers" (`synth.frame_range` moves to `kiwiw/mesh.py`), Contract T "Current exposure".
2. `git grep -n "synth\|clip\|bg_shape_records\|kw_bg_shape\|KIWIW_NO_C" -- parser` output, to find every remaining user before deleting.
3. `parser/kiwiw/synth.py` — `frame_range` and the four `build_*_frame_bytes` functions; which helpers only they use.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Finish Stage 2's deletions: no Python build encoder, clip or per-shape C call remains, the R round-trip writers keep working through `kiwiw/mesh.py`, and no test compares C against Python.

## Contract

- Phase 3C Outcome, cited: "None of the following exists anywhere in `parser/`, checked by grep: `parser/kiwiw/overlap.py`, `clip.py` or `divide.py`; `synth.py`'s `build_road_frame_bytes`, `build_background_frame_bytes`, `build_name_frame_bytes` and `build_map_frame_bytes`; `cenc.py`'s per-cell API (`kw_encode_cell`); `KIWIW_NO_C`; extractor imports in `build_alldata.py`." "No test imports a deleted module, and no test compares C against a Python encoder."
- Contract B, "The R round-trip writers … stay Python. … Their shared helper `synth.frame_range` moves to `kiwiw/mesh.py` when `synth.py`'s encoders are deleted." The R round-trip writers must still prove the decoders byte-exact: their tests keep passing unchanged.
- If a deletion would remove coverage that no golden, boundary test or C unit test replaces, add the missing boundary or layer (b) test (in a new test file you create) rather than keeping the Python.

## Changes

- Move `frame_range` to `kiwiw/mesh.py` and repoint `road_writer`, `background_writer` and any other importer.
- Delete as listed in Owned paths. Keep any `synth.py` helper still used by a verification tool, the harness or the R writers, or move it to the module that uses it; delete `synth.py` if nothing remains.

### Keep untouched

The R round-trip writers' behaviour; the harness; the build path's bytes.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Step gates

This unit changes the build path, so it is gated on every Phase 3C step gate (`DESIGN.md`, Phase 3C "Step gates"), run as **one** background script (Waiting rules) in this order, stopping at the first `FAIL`:

1. `pytest parser/tests --basetemp=output/scratch-3C-12/pytest` (includes the goldens, the boundary tests and the C unit binary; local-only goldens must run, not skip).
2. Perth `-j 1` and `-j 4` → both sha256 `da13a775064…`.
3. Three full-AU `-j 12` builds with `--bench`, each under the heavy lock → each sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B, manifest counters equal to `output/scratch-3-11/G/manifest.json`'s (compare with a small `json` diff, not by eye).
4. Contract H evidence from the three bench records (below).

On a sha mismatch, localise with `--frame-digest` against a 3-11 digest before changing anything, and report the first differing frames. The whole script should take about 8–10 minutes plus lock wait; if it takes much longer, that is a finding.

## Contract H evidence

This unit touches a hot path, so its done evidence includes Contract H's (`DESIGN.md`, "Contract H — hot paths and budgets", "Done evidence", "Measurement", "Regressions"), read from the build's bench record (`--bench`, from 3C-01):

- per level: the Python / C / handoff split, scaled to wall as in the 2026-09-25 profile, `stage_wall = level_wall × stage_worker_s / total_worker_s`;
- the full-AU `-j 12` wall as the **median of three** builds, each under the heavy lock;
- the E1 and E2 call counts per level (equal once E1/E2 are wired; the legacy per-cell counts before that);
- each figure set against the 3C budgets: L0 ≤ 38 s with pre-pass ≤ 5 s, L2 ≤ 2 s, L4–L12 together ≤ 2 s, outside-encode ≤ 10 s, wall ≤ 60 s.

Budgets are gates at Phase 3C's close (3C-13). For this unit the gate is Contract H's regression rule: the median wall may not rise above the previous recorded build by more than the 3C-01 run-to-run spread (recorded in `IMPLEMENTATION.md`'s Phase 3C run record) unless you name the specific mechanism. A trade-off is not a mechanism.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- The step gates above, all passing (this unit changes the build's import graph, so the full gates run even though no build logic changes).
- `git grep -nE "build_(road|background|name|map)_frame_bytes|kw_encode_cell|kw_bg_shape|bg_shape_records|KIWIW_NO_C|kiwiw\.clip|from kiwiw import .*\bclip\b|from \.clip|import clip" -- parser` → nothing.
- `test -e parser/kiwiw/clip.py` → false.
- The R round-trip writer tests (`parser/tests/test_roundtrip_*.py`) pass unchanged.

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
# output/scratch-3C-12/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-12
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
- Scratch: `output/scratch-3C-12/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-12/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
