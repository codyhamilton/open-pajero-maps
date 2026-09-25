# Brief: 3C-02 — Contract T scaffolding: multi-source C build, layer (a) helpers, layer (b) binary

Consumer: 3C-06 and 3C-07, which add E1/E2 C sources, their boundary tests and their C unit tests on top of this scaffolding; every later unit whose tests run through `pytest parser/tests`.
Owned paths: new `parser/kiwiw/cbuild.py`, `parser/kiwiw/cenc.py` (its load/compile path only), new `parser/kiwiw/ctest/` (C test sources), new `parser/tests/test_c_units.py`, new `parser/tests/boundary.py`, new `parser/tests/test_boundary_helpers.py`, `.gitignore`, `docs/provenance.md` (append your own entry only), and this brief file (amendments only). Touch nothing else.
Commits: Commit to the current branch and push when done evidence passes. Commit the `docs/provenance.md` entry promptly and on its own lines: 3C-03 appends to the same file.
Depends on: 3C-01 (it edits `cenc.py` first).
Runs alongside: 3C-03, 3C-04, 3C-05, provided `docs/provenance.md` edits are rebased, not overwritten.
Tier: Sonnet.
Budget: 8 files to read, about 350 lines to change, 60 tool turns.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — "Contract T — tests" (~450–483), Open Questions "How the multi-file C extension and the layer (b) test binary are built" (decided), Phase 3C "Refine notes".
2. `parser/kiwiw/cenc.py` — `_build`, `_load_lib`, `lib` (~1–90, ~169).
3. `parser/kiwiw/spool.py` — `SpoolWriter` (~279), `SpoolReader` (~405), `encode_columns` / `decode_columns`.
4. The Python frame decoders the harness uses (`parser/kiwiw/parcel.py`, `road.py`, `background.py`, and the name decoder): only their entry points.
5. `docs/provenance.md` — the existing `_cenc.so` entry, as the model for yours.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Stand up the Contract T machinery before any port step: a compile-on-demand build for several C sources and for a C unit-test binary, run from pytest, and the layer (a) helpers that let a boundary test write a fixture spool, run a C entry point on it, and decode what comes back.

## Contract

- Contract T, layers (a) and (b), cited not paraphrased: "(b) … It is built by the same mechanism that builds the extension. It is run from pytest, so `pytest parser/tests` stays the single entry point."
- Decided (user, 2026-09-25): "compile on demand, as today. Build products are gitignored and recorded in `docs/provenance.md`, and gcc is a stated requirement."
- Contract B: `KIWIW_NO_C` and the no-compiler fallback are deleted later (3C-08, 3C-12), not here. This unit must not add any new fallback; a missing compiler is a clear error from `cbuild`.

## Changes

- **`cbuild.py`** compiles a declared list of C sources into one shared object, with today's flags (`-O2 -ffp-contract=off -fPIC -shared`) unchanged, and the same atomic temp-then-rename install. It is stale when any source, header or the flag list changed (content hash stored beside the product is simplest; mtime alone is acceptable if you state why). A build that several worker processes might start at once must be safe (the atomic rename already is; keep it). `cenc.py` loads through it. The source list is one place, so 3C-06 adds a file by adding one entry.
- **Layer (b).** `cbuild` also builds a test executable from `parser/kiwiw/ctest/*.c` plus the extension's sources. Test sources `#include` the extension's `.c` files directly, so `static` internals are testable without exporting them. The binary prints one line per case and exits non-zero on any failure. `test_c_units.py` builds it on demand and runs it, one pytest case per C case or one case asserting exit 0 with the failing lines in the message.
- Seed layer (b) with real tests of existing internals of `_cenc.c` that the boundary reaches poorly (the 3-11 edge-step split for coarse `mult_const` rectangles and rectangle detection are named in Contract T), with hand-computed expected values. No expected value may come from running Python build code.
- **Layer (a) helpers, `parser/tests/boundary.py`:** write a fixture spool from hand-described shapes via `SpoolWriter` (in a tmp dir); read a golden fixture spool; decode a Map Frame's bytes with the Python decoders into plain structures; invariant asserts (every vertex in `[0, range]`, clip-rectangle containment, delta representability, frame-size ceiling). No helper computes an expected encoding. `test_boundary_helpers.py` exercises them on a hand-built spool and on frames from `output/scratch-3-11/perth_j1` (skip if absent).
- **`.gitignore`** rule for the test binary (and any other new product), with its `docs/provenance.md` entry in the same commit: what it is, built from what, how to rebuild (`pytest parser/tests/test_c_units.py`, or the `cbuild` call).

### Keep untouched

`_cenc.c`'s code and exported ABI. `KIWIW_NO_C` behaviour (deleted by 3C-08 and 3C-12). The `_cenc.so` path, unless you move it and update `.gitignore` and provenance together.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_c_units.py parser/tests/test_boundary_helpers.py --basetemp=output/scratch-3C-02/pytest` → fails before (missing), passes after.
- Touch one C source and re-run: the extension and binary rebuild; run again: no rebuild (show how you observed it).
- `.venv-rp/bin/python -m pytest parser/tests --basetemp=output/scratch-3C-02/pytest` → previous pass count plus the new tests.
- Perth `-j 1` build → sha256 `da13a775064…` (the loader change is output-invariant). No full-AU build is required.
- `git status --short` after commit shows no build product.

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
# output/scratch-3C-02/checks.sh -- run with run_in_background
set -u
R=/home/codyh/workspace/open-pajero-maps
S=$R/output/scratch-3C-02
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
- Scratch: `output/scratch-3C-02/` (this unit's number). Export `TMPDIR` there (the /tmp quota is small), and pass `--basetemp=output/scratch-3C-02/pytest` to pytest.
- 3-11 references: disc `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`, 1,731,021,568 B), its manifest `output/scratch-3-11/G/manifest.json`, and the Perth builds `output/scratch-3-11/perth_j1`, `perth_j4` (sha256 `da13a775064…`, identical).
- Build commands: full AU is `build_alldata.py --spool output/extract_timing/spool --out <path> -j 12`. Perth is the same with `--fixture perth` at `-j 1` and at `-j 4`. `manifest.json` is written beside `--out`.
- Commit and push after each change (`CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, bench records, compiled `.so` files or test binaries. A new `.gitignore` rule gets its `docs/provenance.md` entry in the same commit.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha(s), the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites.

Contradictions: write each one into this brief file as a dated `## Amendment` section at the end (commit it with your work) and report it. Never resolve a contradiction silently.

Over budget: stop, commit what passes, and put the handoff (done, not done, what you learned) **in your report back, not in a file**. The orchestrator owns `IMPLEMENTATION.md`.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
