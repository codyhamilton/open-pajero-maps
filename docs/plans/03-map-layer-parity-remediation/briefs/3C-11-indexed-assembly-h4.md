# Brief: 3C-11 — H4: remove the per-frame Python from indexed assembly

Consumer: 3C-13, which verifies the outside-encode budget (≤ 10 s) and the Outcome's "vectorised over C's buffer and index".
Owned paths: `parser/kiwiw/frame_table.py`, `parser/kiwiw/alldata_writer.py` (the indexed assembly functions only, around lines 995–1080; not its `KIWIW_NO_C` text at ~869, which is 3C-12's), optionally a new C assembly source added to `cbuild`'s source list with its `cenc.py` binding (`parser/kiwiw/cbuild.py` source list and the binding only), new `parser/tests/test_indexed_assembly.py`, and this brief file (amendments only). Touch nothing else. Do not edit `parser/tests/test_alldata_writer.py` (3C-10 owns it).
Commits: Commit to the current branch and push when done evidence passes.
Depends on: 3C-09.
Runs alongside: 3C-10.
Tier: opus-medium.
Budget: 8 files to read, about 400 lines to change, 80 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Contract B "Python owns" (assembly orchestration; "Today `IndexedLayout` builds divided blocks per frame in Python. That is a leak"), Contract H's H4 row, Stage 2.
2. `docs/ARCHITECTURE.md` — "Spill and indexed assembly".
3. `parser/kiwiw/frame_table.py` — whole file (275 lines), especially `IndexedLayout` and the divided-parent sub-record sizing (`4 + 6*gn`).
4. `parser/kiwiw/alldata_writer.py` — the indexed assembly path (~995–1080): the per-frame loops over divided items.
5. The 3C-09 bench records (paths from the orchestrator or `output/scratch-3C-09/`) for today's outside-encode time.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make assembly vectorised over C's buffer and index with no Python object or loop per frame, including divided parents' blocks, so H4 fits the outside-encode budget and Contract B's "Python owns" line holds.

## Contract

- Contract B, cited: "assembly orchestration: the frame table, block placement, DSA/BMT and the `ALLDATA.KWI` write, all vectorised over C's buffer and index." "the assembly copy under H4" is the only other permitted crossing; "any per-frame work in C" (Contract H, H4).
- Output bytes are unchanged (a port): the full-disc sha is the gate.

## Changes

- Replace the per-divided-parent and per-frame loops with numpy over the frame table (group by parent key with `np.unique`/`np.cumsum` offsets). Where a byte layout cannot be expressed vectorised, do that part in one C call over the whole table (the H4 assembly copy), not per frame.
- `test_indexed_assembly.py`: before changing code, capture the current assembly's `ALLDATA.KWI` sha256 for a small build that includes divided parents with several sub-frames (a Perth build, or a windowed build over the divided-parent goldens' fixture spools); the test asserts the new assembly gives the same sha256, and that the Python disc decoder reads every divided parent's sub-frames back at their index offsets.

### Keep untouched

The spill format, `FRAME_DTYPE`, block placement rules, and every byte of the output.

## Boundary rule

Contract B (`DESIGN.md`, "Contract B — the build boundary") is absolute. No new build logic lands in Python, even temporarily, even as a test helper, and there is no Python oracle (Contract T: the oracle is the Python decoder, the goldens and invariants measured on R). If this brief seems to need one, stop and report `blocked`.

## Step gates

This unit changes the build path, so it is gated on every Phase 3C step gate (`DESIGN.md`, Phase 3C "Step gates"), run as **one** background script (Waiting rules) in this order, stopping at the first `FAIL`:

1. `pytest parser/tests --basetemp=output/scratch-3C-11/pytest` (includes the goldens, the boundary tests and the C unit binary; local-only goldens must run, not skip).
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
- `git grep -nE "for .* in .*(divided|parents|items|frames)" -- parser/kiwiw/frame_table.py` and the indexed section of `alldata_writer.py` → no per-frame loop left, or each remaining loop justified as per-level or per-block.
- Outside-encode time from the median bench record, against ≤ 10 s, and its before/after.

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
# output/scratch-3C-11/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-11
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
- Scratch: `output/scratch-3C-11/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-11/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
