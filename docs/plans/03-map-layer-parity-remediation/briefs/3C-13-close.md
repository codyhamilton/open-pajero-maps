# Brief: 3C-13 — close: ARCHITECTURE rewrite, budget table, Outcome evidence

Consumer: the orchestrator, which closes Phase 3C in `IMPLEMENTATION.md` from this report; Phase 3's resumed units (3-10, 3-13, 3-05, 3-06), which start from this state.
Owned paths: `docs/ARCHITECTURE.md`, and this brief file (amendments only). Touch nothing else. Any code defect found is reported, not fixed.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-01 to 3C-12.
Runs alongside: nothing.
Tier: Sonnet.
Budget: 8 files to read, about 150 lines to change, 60 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Phase 3C Outcome (every bullet), Contract B, Contract H (the budget table), and "Refine notes".
2. `docs/ARCHITECTURE.md` — whole file: "Module map", "Partition and merge", "C kernel", "Spill and indexed assembly", "Output invariance".
3. The 3C-01 baseline and the last build unit's bench records (paths from the orchestrator or `output/scratch-3C-*/`).
4. `git log --oneline` since `d7d3cc3`, to name each 3C commit in the report.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Prove every Phase 3C Outcome bullet on the final tree and make `docs/ARCHITECTURE.md` describe Contract B's pipeline instead of the per-cell kernel.

## Contract

Phase 3C "Outcome", every bullet, cited there; Contract H's budget table. The Contract H budgets are ceilings: if the median bench misses one, report the stage, the figure and the mechanism. Do not tune code here and do not soften the Outcome.

## Changes

- `docs/ARCHITECTURE.md`: rewrite the module map for the new and deleted modules (`cbuild`, `descriptor`, the E1/E2 C sources, `mesh.frame_range`; no `overlap`, `clip`, `divide`, `synth` build encoders); replace "C kernel" with E1/E2 and the descriptor per Contract B (cite, do not restate, the contract); rewrite "Spill and indexed assembly" for C's buffer and index and the vectorised H4; fix "Partition and merge": ranges are contiguous row spans balanced by weight (`_plan_chunks`), not "by cell count", and E1 and E2 use the same ranges. State gcc as a build requirement.
- Budget table in the report: the median of three full builds, per stage, against Contract H's budgets, with the per-level Python / C / handoff split.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Contract H evidence

This unit touches a hot path, so its done evidence includes Contract H's (`DESIGN.md`, "Contract H — hot paths and budgets", "Done evidence", "Measurement", "Regressions"), read from the build's bench record (`--bench`, from 3C-01):

- per level: the Python / C / handoff split, scaled to wall as in the 2026-09-25 profile, `stage_wall = level_wall × stage_worker_s / total_worker_s`;
- the full-AU `-j 12` wall as the **median of three** builds, each under the heavy lock;
- the E1 and E2 call counts per level (equal once E1/E2 are wired; the legacy per-cell counts before that);
- each figure set against the 3C budgets: L0 ≤ 38 s with pre-pass ≤ 5 s, L2 ≤ 2 s, L4–L12 together ≤ 2 s, outside-encode ≤ 10 s, wall ≤ 60 s.

Budgets are gates at Phase 3C's close (3C-13). For this unit the gate is Contract H's regression rule: the median wall may not rise above the previous recorded build by more than the 3C-01 run-to-run spread (recorded in `IMPLEMENTATION.md`'s Phase 3C run record) unless you name the specific mechanism. A trade-off is not a mechanism.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

One background script (Waiting rules), heavy steps under the lock, in this order:

1. `pytest parser/tests --basetemp=output/scratch-3C-13/pytest` → all pass, including goldens (none skipped), boundary tests and the C unit binary.
2. Perth `-j 1` and `-j 4` → both `da13a775064…`.
3. Three full-AU `-j 12` builds with `--bench` → each `87a01b14…`, 1,731,021,568 B, manifest counters equal to 3-11's; declined rows 0 and E1 calls = E2 calls at every level; no E3.
4. `parser/tools/quantisation_roundtrip.py --disc <final disc> --spool output/extract_timing/spool --out output/scratch-3C-13/roundtrip.json --workers 12` → 0 background failures, exactly 1 name-anchor failure, ≤ 120 s. (The tool exits 1 because of the one known name anchor; treat exit 1 with exactly that count as the expected result, and record the step as `OK` only after checking the counts.)
5. `parser/compare_disc.py --generated <final disc> --checks coord_scale --no-manifest --workers 12 --report output/scratch-3C-13/cs.json` → PASS, 0 of 1,461,347 parcels, 73 classes, ≤ 120 s.

Then, outside the script:

- The Outcome greps: `test -e` false for `parser/kiwiw/overlap.py`, `clip.py`, `divide.py`; `git grep -nE "build_(road|background|name|map)_frame_bytes|kw_encode_cell|KIWIW_NO_C" -- parser` → nothing; `git grep -n osm_to_parcel_geometry -- parser/build_alldata.py` → nothing; no test imports `overlap`, `clip`, `divide` or `synth`'s encoders.
- The budget table (median of three) with a met / missed column.
- `docs/ARCHITECTURE.md` diff summary.

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
# output/scratch-3C-13/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-13
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
- Scratch: `output/scratch-3C-13/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-13/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
