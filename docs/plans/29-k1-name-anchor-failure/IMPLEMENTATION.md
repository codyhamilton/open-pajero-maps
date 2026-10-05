# Implementation — 29 K1 name_anchor failure

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` and makes the commits.
- Session: plan 29 Execute (Phases 1–2, terminal review, close-out), run after plan 28 per CHM ordering, with no two heavy jobs at once.
- Started: 2026-10-06 ~04:22 Australia/Brisbane (brief authored while plan 28's worker ran).
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached, pushes fast-forward to `master`); DESIGN landed at `e6436a2`.
- Scratch: `output/scratch-29/` (run logs under `output/scratch-29/runs/`).
- Protected, byte-untouched throughout:
  - `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`);
  - `output/scratch-3-11/G_new/ALLDATA.KWI` (`013586b5…`);
  - `output/extract_timing/spool`;
  - the R disc `/run/media/codyh/464210-8480/ALLDATA.KWI` (`8c2d2027…`, read-only mount).

## Phase 1 — The single name_anchor failure is byte-identified against G, spool and R

Refine skipped (DESIGN). One unit, with its brief authored inline: `briefs/1-01-witnesses-verdict.md`.
