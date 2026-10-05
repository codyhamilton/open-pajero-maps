# Implementation — 28 Phase 1 per-rule classify recovery

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` and makes the commits.
- Session: plan 28 Execute (Phases 1–2, terminal review, close-out)
- Started: 2026-10-06 ~04:25 Australia/Brisbane
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached, pushes fast-forward to `master`); DESIGN landed at `fe18160`.
- Scratch: `output/scratch-28/` (run logs under `output/scratch-28/runs/`).

## Input checks (before any use)

- `output/scratch-14/dump_raw/completeness.bin`: sha256 `1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323`, 111,744 B. **Matches** the pin in `docs/plans/04-c-core-orchestration/triage/completeness_evidence.md`.
- `output/scratch-14/dump_ext/completeness.bin` (mtime 04:10, operator slip): sha256 `1a91b1c2…`. **Byte-identical** to `dump_raw`, as the recorded original was. Its manifest is `28fa57f1…`, which is the gap-annotated manifest the evidence builder rewrites deterministically; no committed hash pin exists for it. Plan 28 does not read `dump_ext`; its source is `dump_raw` (manifest `90f45ef2…`, unchanged since 2026-10-05 23:19).
- `output/scratch-14/classify_invocation.json` (mtime 04:10): sha256 `09b64658…`. No committed hash pin exists. Content: argv `k1_triage.py classify --dump output/scratch-14/dump_ext --rules docs/plans/04-c-core-orchestration/triage/rules_other.json`, exit 2, which matches the recorded outcome. Plan 28 uses it only as a historical reference, never as input.

## Phase 1 — Every baseline row has a reproducible per-rule classify assignment

Refine skipped (DESIGN). One unit, with its brief authored inline: `briefs/1-01-mechanism-producer-classify.md`.
