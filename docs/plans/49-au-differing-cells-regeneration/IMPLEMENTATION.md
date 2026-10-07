# Plan 49 — IMPLEMENTATION

## Run identity
- Tool: Grok Bot (maps executor)
- Start: 2026-10-07 ~14:06 AEST
- Worktree: open-pajero-maps-14-completeness (master-direct)
- Close tip: see git log (`42dcd89` Phase 2 discharge)

## Phase 1 — pinned inputs — DONE
- Located retained discs under this worktree's `output/scratch-3-11/G_new` and `output/scratch-14/G_new`.
- sha256sum:
  - old `013586b58490873fec623a854ed16b6bea8afd3aab20565b83d65275ad595f04` (pin `013586b5`) — MATCH
  - new `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (pin `4ed9cd80`) — MATCH
- Plan 31 reference `output/scratch-31/diff-3-14-au.cells.tsv` sha `77ff1d86…` — MATCH (246,123 cells expected).
- Rebuild not needed. Recorded in `triage/independent_reviews/3-15/conditions/differing_cells/inputs.json`.

## Phase 2 — regenerate + compare — DONE (2026-10-07 ~14:49 AEST)
- `oracle_chain.py diff` under flock → `output/scratch-49/regen-20261007-140744/`.
- Regenerated `AU.differing_cells.tsv` sha **`77ff1d86ee9ca9d41e2d5137d304e0f52dee093cf2ccc2c0911d085eb448544f`** — **literal equal** to plan 31.
- counts: changed=246123, added=0, removed=0.
- Committed as `AU.differing_cells.tsv.gz`; `regen.json` + `compare.json` + README.
- Perth shared cells `0/828/862`, `0/827/869`, `0/832/856` present in regen.
- Residual **R-G8-2-f-a → discharged (regenerated: literal equal)**.

## Carried
- forced_zero re-apply consistency check optional (DESIGN §4); deferred if lock-contended.

## Flash review — 2026-10-07 ~15:00 AEST
- Seat: OpenCode DeepSeek Flash.
- Verdict: **PASS-WITH-CONCERNS**.
- Literal equality `77ff1d86…` independently re-hashed (regen / plan31 / gz decompress).
- R-G8-2-f-a discharge confirmed.
- Concerns: forced_zero re-apply not run (deferred; logically guaranteed by byte-identity); `docs/provenance.md` now has BOM entry (addressed in `e652811`).
- Transcript: `output/scratch-49/runs/flash.stdout`.

