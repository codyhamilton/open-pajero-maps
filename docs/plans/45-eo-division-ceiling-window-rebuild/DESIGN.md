---
design_id:
---

# Window rebuild at d35b565 for the 80 R01 rows in eo_division_ceiling cells, plus the 3-14 window determinism condition

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ruling 4 (2026-10-06): R-G5-4-c (80 R01 rows in `eo_division_ceiling` cells) gets a window rebuild at `d35b565` to test them. Ruling 5 covers R-G8-1-f: regenerate where possible, else superseded-by-proof or a named unverifiable residual. Design grants no waivers. Oracle `4e6b0de7…`. Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

**R-G5-4-c.** Plan 39's clause (b) needs equal footprints. 80 R01 rows sit in the 4 AU cells that plan 36 P3 classed `eo_division_ceiling`: L0 (827,869), (828,862), (832,856), (1797,424). There, 3-14 re-divided the quadtree near the frame ceiling (old 4 leaves → new 1 / 1 / 16 / 1). So leaf identity cannot follow the item, and the rows stay `checker`.

Plan 36's residual risk: for these cells the causal link is the whole-disc EO-only counterfactual, not a per-cell probe.

**R-G8-1-f.** 3-14 claimed window determinism `-j1 == -j4` at sha `c4965442…` (window `(0,828,745,831,748)`) and that `-j12` was never run. `determinism.json` is lost. `-j12` is above the encode cap (≤ `-j4`, plan 25 / WORKFLOW).

**Ground (master `6538530`):**
- `oracle_chain/hop_3_14/cells_causes-au.tsv.gz`: 4 ceiling cells, with old/new leaf counts.
- Plan 39 `historical_bg/p2/assignment.tsv`: 80 rows untested.
- Plan 36 built EO-only and chord-only patched discs (`output/scratch-36/M_eo`, `M_chord`, `E_pre314`, `E_at314`) in throwaway worktrees at `33006aa` / `d35b565`.
- Plan 41 has a byte-identical bench harness per commit.

## Solution shape

### Domain: source-tagged window rebuild

- **Owns:** `triage/historical_bg/p4_ceiling/` (scripts, small JSON, per-row table).
- **Contract:**
  1. **Windows:** for each of the 4 cells, the smallest L0 source window that reproduces the cell's frames byte-exact (control: frames equal `013586b5` at `33006aa` and `4ed9cd80` at `d35b565`). Throwaway worktrees, `-j4`, under the lock.
  2. **Source-tag sidecar:** a debug-only build path at each commit records, per emitted background record, its spool source identity (level, home cell, record ordinal) and leaf path. The control requires frames with tags enabled to be byte-equal to frames without tags. If tagging changes bytes, it is rejected.
  3. **Item identity across topology:** for each of the 80 rows, the old record carrying the failing vertex gets its source from the `33006aa` tags. A row is **proven-fixed (`build:eo_bg_stitch`)** only when all of the following hold:
     - (a) at `d35b565`, records from the same source exist in the new leaves covering the old leaf's area;
     - (b) the same-source record holds at least one owner-exclusive vertex (design 44's definition: no other source's clip into that leaf produces it, and it is not on the exact leaf rectangle edge);
     - (c) window K1 against the original spool reports the row's vertex position, and every vertex of that source's new records in the cell, as non-failing.

     Otherwise the row is a named residual with the failing clause (`removed` if the source emits nothing in the cell).
  4. The per-row table is committed. `assignment.tsv` and `residuals.tsv` are updated (R-G5-4-c discharged, or the exact remaining rows).
- **Non-goals:** changing encoder output; other R01 rows (design 44).

### Domain: window determinism (R-G8-1-f)

- **Owns:** `triage/independent_reviews/3-14/conditions/determinism/`.
- **Contract:**
  1. Window `(0,828,745,831,748)` built at `d35b565` with `-j1` and `-j4`. Both sha256 must equal `c4965442…`. The same window at master with `-j1` and `-j4` is equal to each other (sha recorded).
  2. `-j12`: not run, because the encode cap is ≤ `-j4`. Recorded as `unverifiable:cap` unless a committed proof of worker-count independence of the encoder covers it. Candidate: plan 04 2-0x canonical sort / zeroed padding contract for dumps. That contract is K1, not the encoder, so it does not apply unless a build-side equivalent is found and cited.
- **Non-goals:** lifting the cap.

## Decisions

1. Plan number 45. Master direct. Two phases (the ceiling rows; the determinism window). Both known.
2. Identity standard matches design 44's owner-exclusive test, so all R01 children are judged by one rule.
3. Window builds only; no full-AU encode.

## Assumption ledger

### Assumption 1

- **Question:** Can a source-tag sidecar be added without changing bytes?
- **Answer chosen:** Yes, behind a debug flag that only writes a side file. Byte-equality is the gate.
- **Rationale:** Plan 42 used a bounded instrumentation hook the same way.
- **If wrong:** source identity is computed offline by exact producer matching with the `bg_shape` probe at each commit (design 44's method) instead.

## Open questions

1. Whether owner-exclusive vertices exist in the 16-leaf re-division for every source. If not, those rows are named residuals.

## Phases

### Phase 1: 80 ceiling rows tested

- **Outcome:** a per-row table of 80 rows, each `build:eo_bg_stitch` with evidence or a named residual. Windows byte-controlled. `residuals.tsv` R-G5-4-c updated.
- **Surfaces:** `triage/historical_bg/p4_ceiling/`; debug tag path in `parser/kiwiw/_cenc.c` (behind a flag, byte-neutral) with a test; `assignment.tsv`; `residuals.tsv`; `parser/perf_inventory.json` if a new module is added.
- **Approach:** known. **Depends on:** design 44 Phase 1 owner-exclusive definition (or its own copy of the same rule). **Refine:** skipped.

### Phase 2: Window determinism regenerated

- **Outcome:** `c4965442…` reproduced at `-j1` and `-j4`, or the mismatch named. Master window `-j1 == -j4`. `-j12` recorded as `unverifiable:cap`. R-G8-1-f updated.
- **Surfaces:** `triage/independent_reviews/3-14/conditions/determinism/`; `residuals.tsv`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

## Provenance

- Master `6538530`. Sources:
  - `residuals.tsv` R-G5-4-c, R-G8-1-f;
  - plan 36 record L110, L167 and `hop_3_14/cells_causes-au.tsv.gz`;
  - plan 39 record and `p2/assignment.tsv`;
  - 3-14 REVIEW b5 and L69 (closes with `-j1 == -j4` at the current tip);
  - `IMPLEMENTATION.md` L228 (window and full sha `c4965442effea2ea…`).
- Box draft only.
