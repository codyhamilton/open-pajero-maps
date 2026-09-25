# Brief: 3C-04 — `quantisation_roundtrip` redesign: decoded disc against spool

Consumer: 3C-08, which deletes `overlap.py` (this tool's current dependency) and must not break it; 3C-13, which runs this tool on the final disc as a Phase 3C Outcome check.
Owned paths: `parser/tools/quantisation_roundtrip.py`, `parser/tests/test_quantisation_roundtrip.py`, and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes.
Depends on: nothing.
Runs alongside: 3C-01, 3C-02, 3C-03, 3C-05, 3C-06, 3C-07 (heavy runs serialised by the lock). Must land before 3C-08.
Tier: Sonnet.
Budget: 8 files to read, about 400 lines to change, 70 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Verification-tool decisions", the `quantisation_roundtrip` bullet and its sub-bullets (~495–507), and the Assumption Ledger entry on giving up the per-origin breakdown.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-11 entry's round-trip evidence (background 0 failing; name anchors exactly 1 failing).
3. `parser/tools/quantisation_roundtrip.py` — whole file (369 lines).
4. The harness's disc walker and the Python frame decoders (`parser/harness/walk.py`, `parser/kiwiw/background.py`, `road.py`, the name decoder): entry points only.
5. `parser/kiwiw/spool.py` — `SpoolReader`.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Turn the round-trip into a check of the built `ALLDATA.KWI`, decoded with the Python decoder, against the spool, with no build module imported, parallel over blocks, so it outlives `overlap.py` and `clip.py` and actually exercises coarse-`mult_const` rectangles and interior covers.

## Contract

The "Verification-tool decisions" bullet for `quantisation_roundtrip.py` is the whole contract; implement every invariant it lists, cited there, and nothing it gives up. In particular: "It imports no build module"; "It runs in parallel over blocks"; boundary vertices are checked by point-in-polygon against same-type spool polygons with half-unit tolerance; completeness per `(cell, type)`, and the interior-cover cell centre inside its source polygon.

Phase 3C Outcome: on the 3-11 disc, 0 background failures and exactly 1 name-anchor failure, in ≤ 120 s at `-j 12`.

## Changes

- New CLI: `--disc <ALLDATA.KWI>` (required), `--spool` (required), `--out`, `--workers` (default 12). The tool no longer builds anything.
- Its own spatial index over spool shapes per level (grid bucketing is enough), built once per worker or shared read-only; `SpoolReader` is the only spool access.
- Output JSON: per level and per kind, counts checked and failing, worst error, and a bounded sample of failures (cell, kind, vertex, reason). Exit 1 on any failure, as today, so the known single name-anchor failure makes it exit 1: record that and the expected-failure count in the report rather than special-casing it in code.
- Map disc coordinates to spool lat/lon through the same public geometry the decoders and harness already use (`kiwiw/mesh.py`, `harness`); never through `clip`, `overlap`, `synth`, `divide` or the extractor's build helpers.
- Rewrite `test_quantisation_roundtrip.py` for the new tool on small committed or Perth-built inputs (skip if absent), including a case that injects a vertex outside every source polygon and one that removes a piece, and asserts each is caught.

### Keep untouched

Every build module. The tool's name and location, and exit-1-on-failure.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `git grep -nE "^(from|import) .*(clip|overlap|synth|divide|cenc|build_alldata)" parser/tools/quantisation_roundtrip.py` → nothing.
- `.venv-rp/bin/python -m pytest parser/tests/test_quantisation_roundtrip.py --basetemp=output/scratch-3C-04/pytest` → passes.
- One background script (Waiting rules), under the heavy lock: `parser/tools/quantisation_roundtrip.py --disc output/scratch-3-11/G/ALLDATA.KWI --spool output/extract_timing/spool --out output/scratch-3C-04/roundtrip.json --workers 12` → 0 background failures, exactly 1 name-anchor failure, wall ≤ 120 s (report the wall and counts per kind; note where the one name anchor is).
- If the new tool finds background failures the old one did not, that is a finding about the disc (report it with samples), not a reason to loosen a tolerance.

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
# output/scratch-3C-04/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-04
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
- Scratch: `output/scratch-3C-04/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-04/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
