# Brief: 3C-06 — level descriptor and E1 (level pre-pass) in C

Consumer: 3C-07, which builds E2 on this descriptor and consumes E1's rows; 3C-08, which wires both into `build_alldata.py`.
Owned paths: `parser/kiwiw/mesh.py`, new `parser/kiwiw/descriptor.py`, new C source(s) for E1 under `parser/kiwiw/` (added to `cbuild`'s source list), `parser/kiwiw/cbuild.py` (source list only), `parser/kiwiw/cenc.py` (the E1 binding only), new `parser/kiwiw/ctest/` cases for E1, new `parser/tests/test_e1.py`, new `parser/tests/test_descriptor.py`, and this brief file (amendments only). Touch nothing else. `build_alldata.py` is not changed here.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-02.
Runs alongside: 3C-03, 3C-04, 3C-05 (heavy runs serialised by the lock).
Tier: opus-medium.
Budget: 12 files to read, about 700 lines to change, 90 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Contract B — the build boundary" in full (~346–415), Contract T (~450–483), Phase 3C and its "Refine notes" (E1 row layout, cell range, window).
2. `parser/kiwiw/overlap.py` — module docstring, `_scan`, `_scan_ranges`, `build_level`, `cover_ring`, `_Exists`: the behaviour E1 must reproduce as rows (read it; never import it from new code or tests).
3. `parser/build_alldata.py` — `_plan_chunks` (~366), `_level_rect` (~354), `_fixture_cell_range` (~119), `run` (~598–700): where the level's geometry, mask, thresholds and kind limits come from today.
4. `parser/osm_to_parcel_geometry.py` — `TileGrid`, `assign_to_parcel`, `g_frame_range`, `frame_bounds`, `FIXTURE_BBOXES` (~98): the rules that become descriptor data.
5. `parser/kiwiw/mesh.py` — whole file (381 lines).
6. `parser/kiwiw/_cenc.c` — how it reads spool records today (decode helpers only).
7. `parser/kiwiw/cbuild.py`, `parser/tests/boundary.py` (from 3C-02).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Build the level descriptor, the one piece of data Python hands C per level, and E1, the C level pre-pass that replaces `overlap.py`'s scan with routing rows and additive counters, called once per cell range. E1 is tested at the boundary but not yet wired into the build.

## Contract

- Contract B, "E1, level pre-pass" and "The level descriptor", cited: E1's input is "the level descriptor (below), the range, and the level's whole spool `.data`/`.idx`, zero-copy from the mmap"; its output is "fixed-width routing rows … These are rows only, with no geometry." "The build takes no imports from the extractor (`assign_to_parcel`, `g_frame_range` and `frame_bounds` today). Their rules become descriptor data from `kiwiw/mesh.py`."
- Settled at refine (binding; a contradiction goes in an amendment):
  - **Cell range** = today's `_plan_chunks` row span `[lo, hi)`; E1 runs once per encode range, over the same ranges as E2. A windowed or fixture build still partitions the whole level; the window travels in the descriptor as the output/receiver rectangle.
  - **E1 row**, packed little-endian, 32 bytes: `tix i4, tiy i4, six i4, siy i4, cell_off u8` (byte offset of the source cell's blob in the level `.data`), `shape u4` (shape index within that cell's columns), `kind u1` (0 = edge, 1 = interior cover), 3 pad bytes. One row per existing target cell outside its source cell that a shape passes through or that a polygon wholly covers, exactly the set `overlap.py` produces today.
  - **E1 also returns additive counters**: `shared_shapes`, `edge_cells`, `interior_cells`, `skipped_missing_cells` (today's `overlap` manifest stats). Summed over ranges they equal the manifest's `overlap` block. This output is a refine-settled addition to Contract B's E1 output; flag any reason it cannot hold.
  - **Descriptor** holds: grid geometry, the frame-class and range rule as a table (from `coord_scale.json` via `kiwiw/mesh.py`), the level mask of existing cells, the window rectangle, the 131,070-byte ceiling, the level threshold and kind limits, and every vocabulary table the encoders read that Python passes to C today. The priority and keep-order tables are added by 3C-09. Report any table currently hard-coded in `_cenc.c` rather than moving it.
  - **Extractor imports**: `TileGrid`'s geometry, `assign_to_parcel`'s rule, `g_frame_range`, `frame_bounds` and `FIXTURE_BBOXES` get build-side homes in `kiwiw/mesh.py` (or descriptor data). The extractor may import from `mesh.py`; the build never imports the extractor. Moving the extractor's own definitions is optional; equality tests between the old and new functions are verification, not build logic, and are allowed until 3C-08 removes the old imports from the build.
- Contract T: E1's tests are layer (a) and layer (b). Expected rows come from hand-computed geometry on hand-built fixture spools and from the golden fixtures (3C-03, when present), never from running `overlap.py`.

## Changes

- `descriptor.py` builds the descriptor as one contiguous bytes/numpy buffer with a versioned header; C reads it with a matching struct. Python builds it once per level; nothing per cell.
- E1 in C: iterates the range's source cells in the zero-copy spool, decodes shapes, computes the cells each shape crosses or wholly covers (same geometry and same float operation order as `overlap.py`, `-ffp-contract=off`, so the row set is identical), filters targets by the mask and by the descriptor's window (a full build's window is the whole level), writes rows into a caller-provided buffer (with a size query or a grow protocol), and fills the counters. Rows within a call are in a defined order (source cell, shape, target) so output is deterministic.
- `cenc.py` binding: one function per E1 call taking the descriptor, the range and the spool mmaps, returning a numpy array of the row dtype plus the counters. One ctypes call per range, no per-cell or per-shape call.
- Boundary tests (`test_e1.py`): hand-built spools with a shape crossing one edge, a corner, a polygon wholly covering a cell, a shape into a masked-out cell (skipped_missing), and a range split that must give the same union of rows as one range. Layer (b): the cell-coverage internals with hand-computed cases.
- Scratch check (not a committed test): run E1 over every range of every level of the full spool, under the heavy lock, and compare the counter totals with `output/scratch-3-11/G/manifest.json`'s `overlap` block. Do not run or import `overlap.py` to compare rows: the row set is proven byte-wise when 3C-08 wires E1 in against the full-disc sha.

### Keep untouched

The build path. `overlap.py` (deleted by 3C-08). Existing `_cenc.c` exports.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_e1.py parser/tests/test_descriptor.py parser/tests/test_c_units.py --basetemp=output/scratch-3C-06/pytest` → fails before, passes after.
- `.venv-rp/bin/python -m pytest parser/tests --basetemp=output/scratch-3C-06/pytest` → no new failures.
- One background script (Waiting rules), under the heavy lock: the full-spool E1 scan → counter totals equal to the 3-11 manifest's `overlap` block at every level; report E1 calls per level (= ranges at `-j 12`), total rows, and the E1 C time per level (target: L0 ≤ 5 s scaled to wall at `-j 12`, the H1 budget).
- `git grep -n "osm_to_parcel_geometry" parser/kiwiw/descriptor.py parser/kiwiw/mesh.py` → nothing.
- The descriptor layout and E1 row layout are documented in `descriptor.py` and the C header, matching the refine notes.

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
# output/scratch-3C-06/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-06
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
- Scratch: `output/scratch-3C-06/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-06/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
