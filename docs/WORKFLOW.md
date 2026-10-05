## Workflow plugin

This repo uses [workflow-plugin](https://github.com/codyhamilton/workflow-plugin) for design → per-phase execute → review → close-out.

- **Skills (core only, no lab):** bootstrap before the first phase, then `python3 <path-to-workflow-plugin>/tools/driver/check_skills.py` (exit 0). Cursor cloud: environment setup runs `tools/cloud-env/bootstrap-workflow-skills.sh` (or `docs/lab/bootstrap/cursor-cloud-setup.sh`); daily rebuild refreshes master (no session hook). Claude Code on the web: copy `docs/lab/bootstrap/session-start.sh` to `.claude/hooks/session-start.sh` and merge `docs/lab/bootstrap/claude-settings-fragment.json` into `.claude/settings.json`. Gitignore `<repo>/.cursor/skills/workflow/` if the Cursor path is used.
- **Phase loop (bot or human):** check skills → read-only status → one phase → assert → repeat until `done` or `unsuccessful`.
  - Skills: `python3 <path-to-workflow-plugin>/tools/driver/check_skills.py`
  - Status: `python3 <path-to-workflow-plugin>/tools/driver/status.py docs/plans/<NN>-<slug>/`
  - One phase: `python3 <path-to-workflow-plugin>/tools/driver/run.py <plan-folder> --once`
  - Assert: `python3 <path-to-workflow-plugin>/tools/driver/assert_phase.py --state <compact-state.json>` (see `tools/driver/README.md`)
- **Markers:** `Workflow-Plan:` on the PR; `Workflow-Phase: <slug>:<n>` / `<slug>:done` on closing commits (`skills/execute/SKILL.md`).
- **Status lives in the PR/issue tracker**, not in plan folder names.

Grok Bot does not auto-discover plugin skills. On Cursor cloud they have to be in the image before the process starts. On Claude Code remote the SessionStart hook installs them and reloads. Then call the driver CLIs.

**OpenCode + DeepSeek Flash:** skills-only install (`./install.sh --opencode-skills`); no driver provider. Flash is encouraged for brief/unit work when rationing capacity; [`GUIDANCE-flash-review-gate.md`](https://github.com/codyhamilton/workflow-plugin/blob/master/docs/lab/GUIDANCE-flash-review-gate.md) bounds sign-off only (Sonnet 5.5 on Flash work, hold for Claude or Grok — no Flash auto close-out or `Workflow-Phase:`).

### Cursor cloud bootstrap (Maps agents)

Cloud VMs do **not** inherit the marketplace plugin. Every Cursor cloud agent env/setup for this repo must run:

```bash
export WORKFLOW_WORKSPACE="${WORKFLOW_WORKSPACE:-/workspace}" && curl -fsSL https://raw.githubusercontent.com/codyhamilton/workflow-plugin/master/tools/cloud-env/bootstrap-workflow-skills.sh | bash
```

Then `python3 …/tools/driver/check_skills.py` must exit 0 (six core skills under `.cursor/skills/workflow/`).

Local Claude Code / OpenCode on this host keep using the installed plugin / skill symlinks; they do not need this curl path.


## Heavy jobs (memory)

Plan 05 (`docs/plans/05-heavy-job-memory.md`) cut peak residency for residual dump
joins, the K1 dump finalizer, the 3-07 extension, and `k1_triage` readers. The
rules below are the stable operational contract. Measured peaks and fixture
provenance live in that plan record and in the
`output/scratch-5-0{1,2,3}/` entries of `docs/provenance.md`.

### Lock

- Path (from repository root): **`output/.heavy.lock`**.
- Hold `flock output/.heavy.lock <command>` for the **entire process tree** of
  every memory benchmark, dump scan or join, K1 run, heavy fixture preparation,
  or other heavy task.
- **One worker and one heavy command at a time.** Existing caps (cbuild/make
  ≤ `-j4`, K1/harness ≤ `-j6`) do **not** authorize overlap with another heavy
  job.
- If `flock -n output/.heavy.lock true` fails, another job holds the lock (or
  skipped the advisory take): **wait**. Never stack beside an active job
  (including parallel plan04 seats such as 3-13 / 3-14). A worktree may symlink
  this same lock file; serial sharing still applies.
- Do **not** `drop_caches`. Prefer file-based EXIT markers over self-matching
  `pgrep` / `ps | grep` completion loops.

### Recommended transient scope

Not mandatory, but recommended for attribution and containment:

```bash
systemd-run --user --scope -p MemoryAccounting=yes -- \
  flock output/.heavy.lock \
  .venv-rp/bin/python parser/tools/bench_dump_memory.py --out output/scratch-5-01/results.json
```

Under systemd-oomd, pressure kills then target the job's scope rather than a
sibling terminal or browser, and the scope's cgroup v2 `memory.peak` /
`memory.pressure` stay attributable to that run. An optional per-job
`MemoryHigh=` throttle may be added the same way; there is **no** machine-wide
memory cap imposed by this repo.

### Flash / OpenCode heavy Python (plan 25)

**CHM hold (2026-10-06):** heavy Maps jobs stay on hold until plan 25 criteria
are met **and** Coding Harness Manager clears the hold — see
`docs/plans/25-oom-memory-rca/`. Landing plan 25 does **not** auto-clear.

Every Flash/OpenCode heavy Python under the lock **must** go through the argv +
`memory.peak` wrapper so the next OOM has a recoverable cmdline:

```bash
.venv-rp/bin/python -B parser/tools/run_heavy_python.py \
  --log output/scratch-25/runs/<tag>.json -- \
  .venv-rp/bin/python -B <script> [args…]
```

The wrapper takes `flock output/.heavy.lock` and runs inside
`systemd-run --user --scope -p MemoryAccounting=yes`. Missing `memory.peak` →
exit 2 (fail closed). Plan-14 cell-local triage requires `--max-seeds N` (or
explicit `--all-seeds`); do not whole-file `read()` ALLDATA / spool `level_*.data`
(see `parser/tools/whole_file_guard.py`).

### Bounded benchmark / replay commands

Run from the repository root with `.venv-rp/bin/python`. Controllers generate
seeded fixtures, launch fresh scoped workers, and exit **0** only when every
gate passes (byte SHA equality, ≤50% max RSS and `memory.peak` vs baseline where
applicable, growth and wall bounds). Delete large scratch trees under
`output/scratch-5-0{1,2,3}/` when finished — host disk is often tight.

| Surface | Command |
|---|---|
| Residual extension (Phase 1) | `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py --out output/scratch-5-01/results.json` |
| K1 `_finalize_dump` (Phase 2) | `TMPDIR=output/scratch-5-02/tmp flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py finalize-run --out output/scratch-5-02/finalize_results.json` |
| 3-07 extension (Phase 3) | `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py s07-run --out output/scratch-5-03/s07_results.json` |
| Triage summary/classify/enumerate (Phase 3) | `flock output/.heavy.lock .venv-rp/bin/python parser/tools/bench_dump_memory.py triage-run --out output/scratch-5-03/triage_results.json` |

Small correctness tests (few thousand rows) are **not** heavy and run outside
the lock, e.g. `pytest parser/tests/test_dump_join_memory.py
parser/tests/test_extend_s02_memory.py parser/tests/test_k1_triage.py
parser/tests/test_perf_inventory.py -q`.

Vendored frozen baselines (tracked SHA256SUMS):
`parser/tests/fixtures/dump_join_baseline/`,
`finalize_dump_baseline/`, `extend_3_07_baseline/`, `k1_triage_baseline/`.
Replay roots refuse to resolve into the live repository `output/` outside the
plan scratch trees so baseline scripts cannot overwrite real dumps.

### Interpreting KiB RSS vs `memory.peak`

| Metric | Source | What it includes | What it misses |
|---|---|---|---|
| Max RSS (KiB) | `/usr/bin/time -v` or `getrusage(RUSAGE_SELF)` | Touched anonymous memory **and** touched mapped file pages in the process page tables | Unmapped dirty page cache (e.g. a whole-file `copyfile` that never mapped the destination) |
| `memory.peak` | cgroup v2 on the worker's transient scope | Anonymous memory **plus** page cache charged to the job (including dirty / writeback output) | Work charged only to other scopes; host buff/cache shared reclaim |

Gate on **both**. RSS alone can pass a candidate that still dirties the whole
output in the page cache; `memory.peak` alone can look noisy under concurrent
host load. `tracemalloc` and logical mapped size are **not** RSS evidence. The
plan04 multiprocess **PSS** sampler gates are a separate contract and remain
unchanged; the K1 dump finalizer historically ran after that sampler stopped, so
PSS peaks did not include it.

### Signed PSS ceiling vs ops K1 cap

Plan 04's signed absolute PSS ceiling is **9,726,501 kB** (Phase 2 close;
historical measured peak of three dump-off K1 runs at `-j 12`; no margin).
That ceiling is enforced for live ops and Phase 3 / 3-90 K1 under the
standing K1/harness cap (**≤ `-j 6`**). Running above the ops cap can
exceed a no-margin peak that was signed at a higher worker count; do not
treat such exceedances as a license to raise the ceiling.

### Measured Phase 1–3 peaks (summary)

Full pair tables: `docs/plans/05-heavy-job-memory.md` (What Was Built). On the
seeded 1,000,013-row fixtures (fresh scoped workers):

- Residual: cand/base max RSS ≈ 0.17, `memory.peak` ≈ 0.20–0.26; wall ≈ 0.31×; growth within 19,456 KiB.
- Finalize: RSS drop ≥ one full array (~140,626 KiB gate) every pair (≈272 MiB observed); SHA equal.
- 3-07: RSS ≈ 0.21, peak ≈ 0.32; growth within 18,944 KiB.
- Triage summary/classify/enumerate: RSS ≈ 0.18–0.21, peak ≈ 0.21–0.36; growth within 9,728 KiB.

Limitations carried forward: high-cardinality triage 1M RSS pair not separately
re-measured after Phase 3 (unit artifact identity + fixed-cardinality 50% gates
stand in); `memory.peak` baseline spread widens under concurrent load; out-of-core
`_finalize_dump` remains deferred (see Architecture).
