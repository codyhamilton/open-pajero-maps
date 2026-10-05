# Implementation — 33 seven O04 spool successor rows

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits.
- DESIGN landed at `9fb00da`, amended before landing to Design's ruling: **no default verdict**, and a per-row byte/decode witness that G and R are both absent.
- Disc in force: successor `2ee3456a…`. Historical control `4ed9cd80…`. R `8c2d2027…`. R absence must be proven from index sentinels or decoded frames, never from a lookup failure (plan 29 remediation-01 contract).
- Scratch: `output/scratch-33/`. Plan 04 Phase 3 is not closed by this plan.

## Phase 1 — Presence parity and O04 identity confirmed for all seven

Refine skipped. Unit `briefs/1-01-presence-witness.md`.
