# Brief: 3C-08 — wire E1 and E2 into the build; delete overlap and the per-cell path (Stage 1)

Consumer: 3C-09, which moves division into E2 on top of this wiring; 3C-11 and 3C-13, which read its bench evidence.
Owned paths: `parser/build_alldata.py`, `parser/kiwiw/cenc.py`, `parser/kiwiw/_cenc.c` and the E1/E2 C sources (removals and wiring fixes only), `parser/kiwiw/divide.py` (only the adapter that lets the transitional divide take E2's decoded merged content; its division logic is unchanged), `parser/kiwiw/overlap.py` (delete), `parser/tests/test_overlap.py` (delete), `parser/tests/test_cenc.py` (remove only the cases that exercise deleted API: `make_encoder`, `CellEncoder`, `kw_encode_cell`), `parser/tests/test_build_alldata.py`, new boundary tests for the wiring, and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-07, 3C-04 (the round-trip no longer imports `overlap.py`), 3C-03.
Runs alongside: nothing that builds, except through the heavy lock; nothing that edits `build_alldata.py` or `cenc.py`.
Tier: opus-medium.
Budget: 12 files to read, about 600 lines to change (much of it deletion), 100 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Contract B in full (~346–415), Contract H (~417–448), Phase 3C Outcome, Stages (Stage 1), Step gates, and "Refine notes".
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-06-descriptor-e1.md` and `3C-07-e2-stage1-kernel.md` — the descriptor, row, index and declined layouts.
3. `parser/build_alldata.py` — whole file except `main` (790 lines; read in ranges).
4. `parser/kiwiw/cenc.py` — whole file (211 lines).
5. `parser/kiwiw/divide.py` — `plan_divisions` (~698) and its `measure`/`encode` callbacks; `_bg_sub_cells` (~242).
6. `parser/kiwiw/frame_table.py` — `FRAME_DTYPE`, `ChunkSpill`, `merge_tables`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Stage 1's build step: the build calls E1 then E2 once per cell range, Python only plans, routes rows and assembles, and the transitional Python divide handles E2's declined cells through E3. `overlap.py` and the per-cell ctypes path are deleted in the same unit.

## Contract

- Contract B, cited: "Both entry points are called once per cell range … So per level, E1 calls = E2 calls = number of ranges. The gate asserts that equality." "Python may only concatenate and partition these rows by target range, as one vectorised operation."
- Contract B, E3: "While division is still Python, the transitional divide may call a C measure once per candidate sub-parcel, as today's divide does. … E3 is the only permitted third entry point."
  - **Refine reading, flagged:** today's divide also calls `cenc.bg_shape_records` (`kw_bg_shape`) per shape in `_bg_sub_cells` while retiling. Refine reads E3 as "today's divide's C calls", `kw_measure_cell` and `kw_bg_shape`, both confined to the transitional divide and both deleted from the build path by 3C-09. If you find another reading forced, amend and report.
- Phase 3C Stage 1: "Delete `overlap.py`, the per-cell ctypes path, and their internals tests."
- Settled at refine: the object (no-C) `_encode_level` path uses `overlap.py`, so it goes here: delete it and `KIWIW_NO_C` from `cenc.py` and `build_alldata.py` (a build without a compiler fails with a clear error). `alldata_writer.py`'s `KIWIW_NO_C` goes in 3C-12.
- Phase 3C Outcome: "extractor imports in `build_alldata.py`" do not exist. Switch them to the `kiwiw/mesh.py` / descriptor homes 3C-06 created.

## Changes

- Per level: build the descriptor once; plan ranges with `_plan_chunks` (whole level, even with `--fixture` or `--window`; the window rides in the descriptor); run E1 per range in the pool; in the parent, concatenate rows and split by target range with one vectorised sort/split; run E2 per range in the pool, each worker writing into its `ChunkSpill`; in the same worker, run the transitional divide on that range's declined cells (decode merged content with `decode_columns`; divide measures through E3) and append their frames to the spill; merge the E2 index and the divided frames into canonical order vectorised (a stable sort on the cell key), convert to `FRAME_DTYPE`, and assemble as today.
- `--frame-digest`, `--frame-dump`, `--window`, `--fixture`, `--bench` keep working. The bench record gains `e1`, `e2` and `e3` call counts per level and the E1/E2 C timers.
- Delete: `parser/kiwiw/overlap.py`, `parser/tests/test_overlap.py`, `cenc.CellEncoder`, `cenc.make_encoder`, `kw_encode_cell`'s export (its internals stay, used by E2), `_fill_masked`, `_level_frames`, `_level_frames_c`, `_chunk_worker`, the object path in `_encode_level`, `KIWIW_NO_C` in `cenc.py` and `build_alldata.py`, and the extractor imports in `build_alldata.py`. Remove only the `test_cenc.py` cases that exercise the deleted API.
- Manifest: the `overlap` block now comes from E1's counters; all counters must equal 3-11's.

### Keep untouched

`divide.py`'s division, retile, trim and halo logic (3C-09 ports it). `synth.py`, `clip.py` (3C-12). `alldata_writer.py` (3C-11, 3C-12). The manifest's keys.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Step gates

This unit changes the build path, so it is gated on every Phase 3C step gate (`DESIGN.md`, Phase 3C "Step gates"), run as **one** background script (Waiting rules) in this order, stopping at the first `FAIL`:

1. `pytest parser/tests --basetemp=output/scratch-3C-08/pytest` (includes the goldens, the boundary tests and the C unit binary; local-only goldens must run, not skip).
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

- The step gates above, all passing.
- Bench: E1 calls = E2 calls = ranges at every level; E3 call count per level reported.
- `git grep -nE "overlap|KIWIW_NO_C|make_encoder|CellEncoder|kw_encode_cell|_fill_masked|osm_to_parcel_geometry" -- parser/build_alldata.py parser/kiwiw/cenc.py parser/tests` → only `overlap` as a manifest key or in prose you can justify line by line; nothing else.
- `test -e parser/kiwiw/overlap.py` → false.

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
# output/scratch-3C-08/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-08
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
- Scratch: `output/scratch-3C-08/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-08/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
