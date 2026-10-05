# Implementation — 30 2-01 source-data parity

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one seat at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` (takes `output/.heavy.lock`) and commits. If Codex is usage-limited, Execute does the unit itself and says so here.
- Session: queued after plan 29 (Cody's approval, 2026-10-06 06:33 AEST). DESIGN landed at `3447b39`.
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached; fast-forward pushes to `master`).
- Scratch: `output/scratch-30/` (run logs in `output/scratch-30/runs/`).
- Disc in force: successor `2ee3456a…`. Historical control `4ed9cd80…`. R pin `8c2d2027…`. Plan 29 R1 remediation runs in parallel and does not touch this plan's 2-01 cells.
- Protected, byte-untouched: `output/scratch-14/G_new`, `output/scratch-3-11/G_new`, `output/scratch-29/G_new`, `output/extract_timing/spool`, and the R disc (read-only mount).

## Phase 1 — Every 2-01 row is fingerprinted; type census and 288-template identity are proven

Refine skipped (DESIGN). One unit: `briefs/1-01-fingerprint-census.md`.
