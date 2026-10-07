# Plan 49 — IMPLEMENTATION

## Run identity
- Tool: Grok Bot (maps executor)
- Start: 2026-10-07 ~14:06 AEST
- Worktree: open-pajero-maps-14-completeness (master-direct)
- Tip at Phase 1 open: see git log

## Phase 1 — pinned inputs
- Located retained discs under this worktree's `output/scratch-3-11/G_new` and `output/scratch-14/G_new`.
- sha256sum:
  - old `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` (pin `013586b5`) — MATCH
  - new `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (pin `4ed9cd80`) — MATCH
- Plan 31 reference `output/scratch-31/diff-3-14-au.cells.tsv` sha `77ff1d86…` — MATCH (246,123 cells expected).
- Rebuild not needed. Recorded in `triage/independent_reviews/3-15/conditions/differing_cells/inputs.json`.

## Phase 2 — regenerate + compare (in flight / queued)
- Tool: tracked `oracle_chain.py diff` with `--old-sha` / `--new-sha` enforced.
- Fresh scratch under `output/scratch-49/regen-*` (must not exist beforehand).
- Commit `AU.differing_cells.tsv` (gz if large) + `regen.json` + `compare.py` → `compare.json` + README.
- Compare to plan 31 sha `77ff1d86…`; consistency checks per DESIGN.
- Residual R-G8-2-f-a → regenerated / named-diff / unverifiable per DESIGN.

## Carried
- Heavy lock contended (SC plan 98, garcia-music PW/builds). Diff queued behind plan 44 expand smoke + plan 47 representability nb=32.
