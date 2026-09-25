# Brief: 3C-07 — E2 Stage 1 kernel: merge, cover ring, per-cell encode, decline

Consumer: 3C-08, which wires E2 into `build_alldata.py` and feeds its declined list to the transitional Python divide; 3C-09, which moves division into this kernel.
Owned paths: new C source(s) for E2 under `parser/kiwiw/` (added to `cbuild`'s source list), `parser/kiwiw/_cenc.c` (refactor only: expose its per-cell encode internals to E2 without changing their output), `parser/kiwiw/cbuild.py` (source list only), `parser/kiwiw/cenc.py` (the E2 binding only), `parser/kiwiw/descriptor.py` (additions E2 needs), new `parser/kiwiw/ctest/` cases, new `parser/tests/test_e2.py`, and this brief file (amendments only). Touch nothing else. `build_alldata.py` is not changed here.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-06, 3C-03.
Runs alongside: 3C-04, 3C-05 if still open.
Tier: opus-medium.
Budget: 12 files to read, about 900 lines to change, 100 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Contract B — the build boundary", the E2 bullet and "Declined cells are transitional" (~356–376); Contract T; Phase 3C and its "Refine notes" (frame index, declined list, spill semantics).
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-06-descriptor-e1.md` — the descriptor and E1 row layout you consume.
3. `parser/build_alldata.py` — `_level_frames` (~247), `_level_frames_c` (~318), `_fill_masked` (~208), `_encode_chunk` (~423): today's per-cell order, merge of borrowed shapes, masked-empty frames, and when a cell goes to `divide.plan_divisions`.
4. `parser/kiwiw/overlap.py` — `open_rows`, `cover_ring`, and how borrowed shapes are merged and ordered (read to reproduce; never import from new code or tests).
5. `parser/kiwiw/divide.py` — `plan_divisions` (~698) and `_try_encode` (~352): the exact "needs division" condition (threshold, kind limits, 131,070-byte ceiling).
6. `parser/kiwiw/_cenc.c` — `kw_encode_cell` and what it calls.
7. `parser/kiwiw/frame_table.py` — `FRAME_DTYPE`, `ChunkSpill`.
8. `parser/kiwiw/spool.py` — `encode_columns` / `decode_columns` (declined merged-content format).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

E2, the one-call-per-range encoder, for Stage 1: it merges each cell's own and borrowed shapes (read in place from the spool via E1's rows), adds interior-cover rings, encodes every cell that fits, emits masked-in empty cells, and declines every cell that needs division with its merged content, all in one C call per range. Tested at the boundary against the goldens, not yet wired.

## Contract

- Contract B, E2, cited: "C orders each cell's borrowed shapes canonically, by source `(iy, ix)` then spool index. So the output does not depend on the range partition or on the order rows arrive." Outputs 1–6 as listed there; "E2 also emits the frames for masked-in empty cells (today's `_fill_masked`), so no per-cell Python remains."
- "Declined cells are transitional. While division is still Python (Stage 1), the only permitted reason is 'needs division'."
- Settled at refine (binding; a contradiction goes in an amendment):
  - **Frame index row**, packed, 36 bytes, canonical order (cell `(iy, ix)` as today's stream, then today's sub-frame order): `[("ix","<i4"),("iy","<i4"),("level","u1"),("pt","u1"),("sx","u1"),("sy","u1"),("off","<u8"),("len","<u4"),("road","<u4"),("bg","<u4"),("name","<u4")]`. `road`/`bg`/`name` are the per-kind sub-frame sizes.
  - **Frame buffer**: E2 writes frame bytes into a caller-provided file descriptor starting at a caller-given offset, so `off` is absolute in that spill file (ChunkSpill/FrameTable semantics). Python converts the index to `FRAME_DTYPE` vectorised.
  - **Declined list** row `[ix i4, iy i4, reason u4, off u8, len u8]`, pointing into a merged-content blob holding, per declined cell, its own plus borrowed shapes (and cover rings) in `spool.encode_columns` format, in exactly the order today's Python merge hands to `divide.plan_divisions`, so the transitional divide produces identical bytes.
  - Reason codes: `1` = needs division. No other reason exists.
  - Counters: whatever E2-side additive counters the manifest needs in Stage 1 (report which); the overlap counters come from E1. C-side stage timers go to the bench record.
- If today's merge order is not the canonical `(iy, ix)`-then-spool-index order, the goldens decide which order reproduces today's bytes. Record the finding as an amendment and report it; do not change the order silently.
- Contract T: tests are layer (a) on golden fixture spools (E1 run on the fixture, rows routed in the test by one numpy sort/split, then E2) and layer (b) for internals. No Python expected encoding.

## Changes

- E2 in C: for each cell of the range in canonical order, inside the descriptor's window and mask: gather own shapes and routed borrowed shapes, order borrowed canonically, add the cover ring for interior-cover rows (today's `cover_ring`, bit for bit), encode with the existing `_cenc.c` per-cell code, and either write the frame or decline the cell. Emit masked-in empty cells exactly as `_fill_masked` does, in the same positions in the stream.
- `cenc.py` binding: one ctypes call per range; inputs are the descriptor, range, spool mmaps, the routed E1 rows, the spill fd and start offset; outputs are numpy views over the index, declined list and merged-content blob, plus counters and timers. Buffer growth is handled in C or by a size query, never by a per-cell call.
- `_cenc.c` refactor is allowed only to share internals; `kw_encode_cell` keeps working until 3C-08 deletes it.

### Keep untouched

The build path. `overlap.py`, `divide.py`, `_fill_masked` (deleted by 3C-08). Existing exported ABI.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_e2.py parser/tests/test_c_units.py --basetemp=output/scratch-3C-07/pytest` → fails before, passes after. For every golden: every non-declined frame is byte-equal to the golden's frame; the declined set equals the golden's divided parents (cells with any `parcel_type != 0` frame); a range split into two calls gives the same frames and index as one call; merged content for each declined cell decodes with `decode_columns`.
- Local-only goldens are exercised on this machine (not skipped); report which ran.
- `.venv-rp/bin/python -m pytest parser/tests --basetemp=output/scratch-3C-07/pytest` → no new failures.
- Report E2's C time on the largest L0 golden, and the index, declined and blob sizes.

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
# output/scratch-3C-07/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-07
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
- Scratch: `output/scratch-3C-07/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-07/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
