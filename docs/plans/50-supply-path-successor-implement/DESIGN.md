---
design_id:
---

# Successor implement for the 341 plan-30 supply-path rows (R-G9-2)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close R-G9-2: plan 30 left 341 rows at `verdict=supply-path` with a production-C witness and a per-row `successor_implement_path`. Plan 38 closed only row 246. This design is the successor implement unit.

Oracle `4e6b0de7…`. Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief. Design grants no waivers.

## Problem

G omits all 341 cells. Each row demands code 288 (stratum `288-template`). Plan 30 proved an OSM `type=boundary` / `protected_area` relation can supply the demanded code in-cell (presence parity, not a geometry clone). The witnesses are not an implementation.

**Ground (master `607e5b6`):**
- `triage/source_parity/disposition.tsv`: 341 × supply-path, 1 × proven-cause (row 246, plan 38), 0 unfixable.
- 10 supply relations: r8426743 (173), r8601872 (94), r8426822 (30), r8602593 (24), r8426745 (11), r2647638 (3), r8602093 (3), r8602037 / r80500 / r8390145 (1 each).
- Per-row path (all 341): assemble the OSM relation from member node IDs, inherit tags, preserve even-odd holes, retile; clip the original boundary at the target cell before encoding; presence match only; validate successor G and re-oracle under a separate implement unit.
- **Rows 396, 397, 775** need 16 member ways of r2647638 that exist only in the date-matched Overpass attic snapshot `39a836dd…` (plan 30 F2). The pinned Geofabrik PBF alone cannot reproduce them.
- Snapshot is ODbL, pinned in `docs/provenance.md`.

## Solution shape

### Domain: relation assembly and in-cell emission

- **Owns:** a tracked assembler under `parser/` (or `parser/tools/`) that, for each supply relation, builds rings from member ways (pinned PBF first; snapshot only for the 16 ways of r2647638), inherits relation tags, preserves even-odd holes, and emits background records of the demanded code into the named target cells by clipping the original boundary at the cell before encoding.
- **Contract:**
  1. **Presence parity:** for every one of the 341 dump rows, successor G emits at least one non-degenerate in-cell record of the demanded code. Geometry need not match R's tile.
  2. **Inputs:** pinned Geofabrik extract for 338 rows; for 396/397/775, the complete r2647638 from snapshot `39a836dd…` (or an equivalent extract that includes those 16 ways). Re-pin before use; fail closed on sha.
  3. **Scope:** only the 10 named relations and the 341 cells. No wholesale OSM import.
  4. **Diff confinement:** every changed cell is listed. Cells outside the 341 targets that change are named residuals or the change is rejected.
- **Non-goals:** cloning R geometry; fixing row 246 (closed); unfixable claims.

### Domain: successor oracle and gates

- **Owns:** a recorded successor oracle row; K1 and suite gates.
- **Contract:**
  1. Re-oracle under flock at `-j4`. New AU sha recorded in `oracle_chain.tsv` with the cell diff against `4e6b0de7`.
  2. K1 failing 0 for kinds that the change can affect (background family at minimum); other kinds unexplained rises are residuals.
  3. Full `parser/tests` green; `close_gates.py` pass.
  4. Wall: not required to meet the ≪ 60 s budget (R-G9-4 / R-G8-1-a are Cody questions). Report the median at `-j4`.
  5. `disposition.tsv` updated: the 341 rows move to `implemented` (or a named residual per row that still fails presence).
- **Non-goals:** rebasing the build budget.

## Decisions

1. Plan number 50. Master direct. Two phases (land the assembler with a small-cell proof; full 341 + re-oracle).
2. Snapshot `39a836dd…` is an authorised second source for the 16 ways only (Cody's plan-30 ruling on date-matched snapshots).
3. Presence match only, as plan 30 decided.

## Assumption ledger

### Assumption 1

- **Question:** Does assembling the 10 relations and clipping per cell produce a presence match in every target without large collateral emission?
- **Answer chosen:** Expected for marine-park boundaries already witnessed. Collateral into neighbouring cells is measured and either accepted as confined or cut by cell-local clip.
- **Rationale:** Plan 30 production-C witnesses already show in-cell supply under the same clip rule.
- **If wrong:** rows with collateral or no presence become named residuals; no silent expansion.

## Open questions

1. Whether the assembler lands in the live extract path or as a pinned overlay spool. Prefer overlay first (smaller blast radius); promote to live extract only if the overlay is byte-stable across rebuilds.

## Phases

### Phase 1: Assembler + stratified proof

- **Outcome:** tracked tool with tests; presence proven on a stratified sample (≥1 cell per relation, including 396/397/775 with the snapshot). Overlay or extract path chosen and recorded.
- **Surfaces:** assembler module, tests, `triage/source_parity/implement/`, `docs/provenance.md` (snapshot re-hash).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: All 341 + successor oracle

- **Outcome:** 341/341 presence or named residuals; successor oracle; K1 / suite / gates; `disposition.tsv` and `residuals.tsv` R-G9-2 updated.
- **Surfaces:** oracle_chain, disposition, residuals, IMPLEMENTATION record.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `607e5b6`. Sources: plan 30 record; `disposition.tsv`; `open_rows_account.md`; plan 38 (row 246 closed, 341 non-goal); `residuals.tsv` R-G9-2.
- Box draft only.
