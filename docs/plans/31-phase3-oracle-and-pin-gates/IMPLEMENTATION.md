# Implementation — 31 Phase 3 oracle chain and pin gates (slice 1)

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits. If Codex is usage-limited, Execute does the unit and says so here.
- DESIGN landed at `b831244`. Disc in force: successor `2ee3456a…` (plan 29 verdict A, re-proven on R index bytes at `8798302`).
- Scratch: `output/scratch-31/`. Protected discs (`87a01b14…` if found, `013586b5…`, `4ed9cd80…`, `2ee3456a…`) and the spool are read-only.
- Plan 04 Phase 3 is **not** closed by this plan.

## Phase 1 — Every disc-in-force re-oracle hop has an exact changed-cell (or leaf) proof

Refine skipped. One unit: `briefs/1-01-oracle-chain.md`.
