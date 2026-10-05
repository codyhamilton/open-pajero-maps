# Implementation — 34 L0 empty-slot frame parity

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits.
- DESIGN landed at `9fb00da`. It rebases on plan 29's record: the out-of-span name drop gives successor `2ee3456a…`, whose (0,541) leaf is nameless but retained. The R side uses plan 29's hardened reader (remediation-01, `8798302`). R's block 0 has an absent BMT sentinel at blockset 32 (BSMR offset 11,134, `0020ffffffff00000000`), so all 2,048 cells are empty, with 0 lookup failures.
- Scratch: `output/scratch-34/`. Never overwrite `2ee3456a…` or any older disc. If a fix changes bytes, the new disc goes to a new path with its own successor record. Plan 04 Phase 3 is not closed by this plan.

## Phase 1 — Three cells byte-witnessed; block census recorded

Refine skipped. Unit `briefs/1-01-frame-witness.md`.
