# Brief: 3C-09 — division, retile, trim and name halo into E2; delete divide and E3 (Stage 2)

Consumer: 3C-10 and 3C-11, which build on a build path with no Python division; 3C-13, which proves the declined list empty and E3 gone.
Owned paths: the E2 C sources and `parser/kiwiw/_cenc.c`, `parser/kiwiw/cbuild.py` (source list only), `parser/kiwiw/cenc.py`, `parser/kiwiw/descriptor.py` (priority and keep-order tables), `parser/build_alldata.py` (remove the transitional divide wiring), `parser/kiwiw/divide.py` (delete), `parser/tests/test_divide.py` (delete), `parser/tests/test_cenc.py` (remove the `measure_content` cases and the `divide` import only), new `parser/kiwiw/ctest/` cases, new or extended `parser/tests/test_e2.py`, and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes. An intermediate commit is allowed at the stop point below if it passes every step gate.
Depends on: 3C-08.
Runs alongside: nothing that builds, except through the heavy lock; nothing that edits the owned paths.
Tier: opus-medium.
Budget: 12 files to read, about 1,200 lines to change, 140 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Contract B (~346–415, especially "Declined cells are transitional", "The level descriptor" and "C owns"), Contract T, Phase 3C Outcome, Stage 2, Step gates, and "Refine notes".
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-07-e2-stage1-kernel.md` and `3C-08-wire-e1-e2.md` — the E2 layouts and the Stage 1 wiring.
3. `parser/kiwiw/divide.py` — whole file (836 lines; read in ranges): `_road_rank`, the keep-order functions, `_kind_breach`, `_sub_tile_grid`, `_sub_frame`, `_bg_sub_cells`, `_retile_content`, `_try_encode`, `_shrink_to_fit`, `_trim_kinds`, `_shrink_priority`, `_halo_candidates`, `_add_name_halo`, `plan_divisions`.
4. `parser/kiwiw/cenc.py` — `measure_content`, `bg_shape_records`; `_cenc.c`'s `kw_measure_cell` and `kw_bg_shape`.
5. `parser/build_alldata.py` — the transitional divide wiring 3C-08 added, and `_measure_one` / `_encode_one`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Stage 2's build step: E2 divides, retiles, trims and adds the name halo itself, byte for byte as `divide.py` does today, so the declined list is empty, E3 and the merged-content output are gone, and a declined cell is a build error.

## Contract

- Contract B, cited: "At Phase 3C's close, no reason is permitted, E3 and output 4 are gone, a non-empty declined list is a build error, and no Python fallback exists." The descriptor holds "the priority and keep-order tables used for trimming and division". "C owns … division, retile, trim and name halo."
- Contract B, E2 output 5: counters "are exactly 3-11's counters (overlap statistics, trimmed items, halo names)". The trim and halo counters now come from C.
- Phase 3C Stage 2: "Delete `divide.py`, … E3, E2's merged-content output".
- Contract T: the goldens covering the divided L0 parent with trim and halo and the divided L4 parent are the byte yardstick; new internals get layer (b) tests with hand-computed values; no Python expected encoding.

## Changes

- Port in C, inside E2, with the same float operation order (`-ffp-contract=off`, `rint`) and the same iteration order as `divide.py`: the division decision, the sub-grid choice, retile of roads, backgrounds (today's `_bg_sub_cells` path, which calls the per-shape background encoder) and names into sub-cells, shrink-to-fit, kind trimming by priority and keep order, and the name halo. The priority and keep-order tables move into the descriptor as data built by Python once per level.
- Suggested order, with a **stop point**: first divided parents that need neither trim nor halo, declining the rest (reason stays "needs division", so the transitional divide still handles them and every gate still passes). That state may be committed if it passes the step gates. Then trim and halo, then the deletions.
- Delete: `parser/kiwiw/divide.py`, `parser/tests/test_divide.py`, `cenc.measure_content`, `kw_measure_cell`'s export, `_measure_one`, `_encode_one`, the transitional divide wiring, and E2's merged-content output. `build_alldata.py` raises a clear error naming the cells if any declined row comes back. `kw_bg_shape` / `bg_shape_records` are no longer called on the build path (3C-12 deletes them with `synth`).
- Remove the `test_cenc.py` cases that call `measure_content` and the `divide` import; leave the rest for 3C-12.

### Keep untouched

`synth.py`, `clip.py` and the remaining `test_cenc.py` cases (3C-12). `alldata_writer.py` and `frame_table.py` (3C-11). The manifest's keys.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Step gates

This unit changes the build path, so it is gated on every Phase 3C step gate (`DESIGN.md`, Phase 3C "Step gates"), run as **one** background script (Waiting rules) in this order, stopping at the first `FAIL`:

1. `pytest parser/tests --basetemp=output/scratch-3C-09/pytest` (includes the goldens, the boundary tests and the C unit binary; local-only goldens must run, not skip).
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
- Bench: E1 calls = E2 calls = ranges at every level; no `e3` calls; declined rows 0 at every level.
- `git grep -nE "\bdivide\b|measure_content|kw_measure_cell|plan_divisions" -- parser` → prose only, justified line by line.
- `test -e parser/kiwiw/divide.py` → false.
- The two divided-parent goldens pass through E2 alone (boundary test asserting the declined list is empty).

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
# output/scratch-3C-09/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-09
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
- Scratch: `output/scratch-3C-09/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-09/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
