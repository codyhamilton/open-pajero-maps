# Brief: 2-07 — Full-disc run kickoff (K1, D1 and gate runs on the 3-11 disc)

Consumer: 2-08 (verifies the numbers this unit produces and records them).
Owned paths: `output/scratch-2-07/` only (git-ignored; no commit of its contents). No repo file changes. If a defect needs a code change, report it; do not fix it here.
Commits: None expected. If you must record a provenance line for a scratch artifact, `docs/provenance.md` is the one permitted edit, committed and pushed.
Depends on: 2-06.
Runs alongside: nothing (every step is heavy and takes the lock).
Tier: Sonnet.
Budget: 5 files to read, about 150 lines of shell, 40 tool turns. Your own work ends at the kickoff hand-off below; you do not wait on the script past one Monitor.

This unit exists because the done evidence for Phase 2 waits on processes longer than ten minutes (a `-j 1` determinism run, the Python per-check baselines, full builds). You start them, watch them to their terminal state with one Monitor, and hand off a short summary. A fresh unit (2-08) judges the result.

## Required reading

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Phase 2 Outcome and Gates.
2. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` — Contract W, the count table.
3. `parser/tools/quantisation_roundtrip.py` `--help` (run it), `parser/kiwiw/cenc.py` D1 binding entry names, `parser/harness/` check names (`compare_disc --help`), `docs/plans/04-c-core-orchestration/briefs/1-01-policy-lock.md` for the H budget and gate commands.
4. `docs/provenance.md` for the discs and the spool.

## Goal

One chained script, `output/scratch-2-07/run.sh`, runs these steps in order under `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock` and leaves every output in `output/scratch-2-07/`:

1. `k1_a`, `k1_b`, `k1_c`: the round-trip entry point (default engine) at `-j 12` on G (`output/scratch-3-11/G/ALLDATA.KWI`) against the spool (`output/extract_timing/spool`), three runs, each with wall and summed-PSS peak in the report's `timing` section, JSON report to `k1_<x>.json`.
2. `k1_j1`: the same at `-j 1`, report to `k1_j1.json`; then `cmp` of `k1_a.json` vs `k1_j1.json` with the `timing` section dropped by the driver's documented switch (or by a `jq`/python one-liner you write in the script), result to `determinism.txt`.
3. `d1_decode`: D1 full-disc decode wall on G at `-j 12`, using the 2-02 walker through the binding (a small script in `output/scratch-2-07/`), wall and C-side counters to `d1_decode.json`.
4. `py_checks`: Python per-check wall for the harness checks `decode`, `container`, `envelope`, `mfde`, `shape`, `vocab`, `spotcheck`, `coord_scale` at `--workers 12` on G (the baselines Phase 4 improves), one wall per check to `py_checks.tsv`. A check that cannot be run singly: record that and its reason.
5. `gates`: full-AU build sha (expect `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` — see 1-01 for the command), Perth `-j 1` and `-j 4` sha (expect `da13a775…`; use the exact full sha from `docs/` or the goldens record), the goldens tests, and the H budget test, outputs to `gates.txt`.

## Waiting rules


Chain every slow step in one background script (`run_in_background`) that appends `STEP <name> OK <s>` or `STEP <name> FAIL <rc> <s>` to a status file and ends with `ALLDONE`; a `trap ... EXIT` appends `ABORT` if it ends without `ALLDONE`. Block on it with ONE Monitor (or one Bash with a real timeout) whose match covers `ALLDONE|ABORT|FAIL|Traceback`; timeouts at least cover heavy-lock wait. Never end your turn to wait, never poll with no-op turns, never pipe a long command through `| tail`; read logs with Read or a bounded grep. A check needing many waits is a finding.

The script's status file is `output/scratch-2-07/status.txt`. Pipe nothing through `| tail`; each step writes its own log in the scratch dir. A step that fails does not stop later independent steps, but `ABORT`/`FAIL` still match the Monitor so you hand off at once.

## Done evidence (kickoff)

- `run.sh` exists, is run once with `run_in_background`, and one Monitor reached a terminal state (`ALLDONE` or `ABORT`).
- Hand-off report (under 400 words): the status file verbatim, the three K1 walls and PSS peaks, the `-j 1` vs `-j 12` determinism verdict, the D1 decode wall, the `py_checks.tsv` rows, the gate lines, and the paths of every output. Do not judge counts against the 3C-04 table; 2-08 does.
- If the kickoff cannot start (missing G, spool, lock held by a process you do not own), report `blocked` with the evidence. Never kill another job.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it. Over budget: stop, commit what passes, put the handoff (done, not done, what you learned) in the report.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Machine facts

- Python is `.venv-rp/bin/python` from the repo root (`python` is not on PATH). gcc is required; `kiwiw/cbuild.py` builds `_cenc.so` on demand from `EXT_SOURCES`, content-hashed. Build flags (`-O2 -ffp-contract=off -fPIC`) are not to change: floating-point results must be bit-reproducible against Python.
- Plan 04 `DESIGN.md` Decisions 1-9 and Assumptions 1-5 are settled; do not reopen them. Workers are Sonnet; no Opus.
- Commit and push to `master` when done evidence passes (project `CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, compiled `.so` or test binaries.
- Scratch for your own files: `output/scratch-<brief number>/` with `TMPDIR` exported there; pytest `--basetemp=output/scratch-<brief number>/pytest`.
- Reference discs: R `/run/media/codyh/464210-8480/ALLDATA.KWI` (tests using it skip when absent); G `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`); spool `output/extract_timing/spool` (build_alldata's default spool is not it).
- One heavy job at a time: any full-AU build or `-j 12` run takes `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Pytest and small builds do not.
