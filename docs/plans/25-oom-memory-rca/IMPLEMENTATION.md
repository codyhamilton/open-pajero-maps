# Implementation — 25 OOM memory RCA

- Tool: Grok Bot / Maps Execute background (plan 25); assigned instance Flash for workers
- Started: 2026-10-06 ~00:28 Australia/Brisbane
- Assumption 5: **Cody override** (Primary / Maps Manager 2026-10-06) — land concrete
  guards (wrapper + bound triage loads), not harness-only. Documented here.

## Phase 1 — Incident + inventory

**Closed.** Folder `docs/plans/25-oom-memory-rca/` with DESIGN (amended),
`host-evidence-2026-10-06.md`, `inventory.md`. Job class = plan-14 completeness
OpenCode path. No Phase 2/3 science restart. No 170/3-16/3-17 reseat.

## Phase 2 — Bounded harness + class

**Closed.** Small harness under flock + scope: `cell_local_2-01.py --max-seeds {8,32}`
with R+G+spool. Peaks ~64–68 MiB RSS / ~56–60 MiB `memory.peak`. Class:
inconclusive on 2881900 argv; cell_local-class capped (not the 6.5 GiB resident).
Logs under `output/scratch-25/runs/` (git-ignored). Report: `report.md`.

## Phase 2b — Concrete guards

**Closed (Cody widen).**

| Artifact | Role |
| --- | --- |
| `parser/tools/run_heavy_python.py` | Flash argv + `memory.peak` wrapper |
| `parser/tools/whole_file_guard.py` | Refuse whole-file ≥64 MiB |
| `docs/plans/14-…/triage/cell_local_2-01.py` | `--max-seeds` / `--all-seeds`; drop coords; batch GC; no TSV clobber on window |
| `parser/tests/test_plan25_memory_guards.py` | Wrapper peak + refuse + uncapped refuse |
| `docs/WORKFLOW.md` | Heavy-jobs recipe points at wrapper; CHM hold pointer |

No dump_join/finalize rewrite. No PSS ceiling change. No plan-14 Phase 2/3 restart.

## Phase 3 — Hold-lift criteria

**Closed (criteria published; hold NOT cleared).**

CHM may clear the heavy-Maps HOLD only when **all** of:

1. Plan 25 Phases 1–2 closed on master (this record).
2. Published peak + named class (`report.md`).
3. Phase 2b **named + capped path** landed **or** harness ceiling proof alone if Cody re-narrows — **both present** here for cell_local-class; 6.5 GiB argv still unnamed.
4. Future seats use `flock output/.heavy.lock` + `run_heavy_python.py` (WORKFLOW).
5. If residual unnamed 6.5 GiB class returns, follow-up fix design **or** Cody/CHM-accepted mitigation.
6. **CHM explicit clear** — this commit does not reseat heavy completeness.

**Forbid** seating plan-14 Phase 2/3 (or equivalent) OpenCode until (1)–(6).

## QA

- `pytest parser/tests/test_plan25_memory_guards.py` — 4 passed
- Harness exits 0 for max-seeds 8 and 32 under shared lock
- Membership TSVs unchanged (343 / 1)

## Residual

- Exact 2881900 cmdline unknown; next Flash heavy must use wrapper.
- HOLD remains until CHM clears.
- Plan 14 Phase 2/3 science not restarted; Phase 3 / 3-90 / PSS-PASS not claimed.
