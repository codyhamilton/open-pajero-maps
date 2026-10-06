---
design_id:
---

# R01 owner-exclusive identity test: 94,134 weak-identity rows plus the 925 untraceable rows

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's rulings (2026-10-06):

- **Ruling 2:** R-G5-4-a (94,134 R01 rows, fix unproven) gets a stronger per-source test using owner-exclusive vertices, meaning vertices no neighbouring polygon could supply. Plan 39's re-review found 15% were matched through shareable vertices. Each row ends proven-fixed (`build:eo_bg_stitch`) or residual.
- **Ruling 3:** R-G5-4-b (925) keeps `checker` only where a recorded checker-rationale proof exists per row. The rest join test 2.

Design grants no waivers. Oracle `4e6b0de7…`. Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

Plan 39 P2 tested R01 rows by shape-level clause (b) with an identity guard. A row's item persists if a same-type record in the same leaf on `4ed9cd80` holds at least one non-failing vertex that no other old same-type record in the leaf holds and that is not on the leaf edge.

**Two weaknesses:**
- The guard uses **old records** as the only possible suppliers, so a vertex shared with a source that had no old record in the leaf, or a different-type source, passes.
- The "leaf edge" is the leaf's **vertex bbox**, not the leaf rectangle (plan 39 Residual Risks).

| Child | Rows | Plan 39 status |
| --- | ---: | --- |
| R-G5-4-a | 94,134 | weak: every shared non-failing vertex is held by another old same-type record or lies on the leaf edge |
| R-G5-4-b | 925 | no traceable same-type record on `4ed9cd80` after excluding records identical to unchanged neighbours |

**Ground (master `6538530`):**
- Plan 39 `historical_bg/p2/{shape_clause_b.py, r01_clause_b.py, r01_clause_b_control.py, assignment.tsv, allrows/}`.
- Per-row arrays are keyed in `output/scratch-39/keep/` (git-ignored, BOM in `docs/provenance.md`).
- Discs `87a01b14` (`scratch-36/G_pre311`), `013586b5`, `4ed9cd80` and the pinned spool are available.
- The tracked `parser/tools/k1_representable.py` carries the full-EO-topology clip contract (plan 14), and the `bg_shape` probe pattern is in `parser/tests/fixtures/bg_eo/probe.c`.
- `rules_bg.json` R01 note: "Independent all-level witness: 200/200 valid". That is a sample witness from 3-07, not a per-row proof.

## Solution shape

### Domain: exact producer and owner-exclusive vertex sets

- **Owns:** a tracked tool `parser/tools/bg_owner_exclusive.py` with a C probe shim (built from the commit's `_cenc.c`, `-O2 -ffp-contract=off`, exact `kw_bounds` arithmetic), synthetic tests and a perf-inventory entry.
- **Contract:**
  1. **Producer (old):** for each row's old record (the record carrying the failing vertex, on `013586b5`), find the spool source S whose production clip at `33006aa` into that exact leaf rectangle byte-equals the record. It must be unique, otherwise the row is `producer-ambiguous`.
  2. **Candidate suppliers of leaf L:** every spool source of any type whose bbox meets L at the same level. This uses the build's E1 routing, with all source cells retained.
  3. **Owner-exclusive vertices of S in L (post-3-14):** vertices of S's `d35b565` clip output into L's exact integer rectangle that:
     - no other candidate supplier's `d35b565` clip into L produces at the same raw position; and
     - do not lie on L's rectangle boundary; and
     - are not R01-failing on the old disc.
  4. Bounded: per-leaf streaming over sorted rows, under the lock, with no whole-file loads.

### Domain: per-row verdict for the 94,134 + 925

- **Owns:** `triage/historical_bg/p5_owner_exclusive/` holding the per-row table (committed gz), a summary, and the `assignment.tsv` / `residuals.tsv` updates.
- **Contract:**
  1. **Ruling 3 inventory first.** For each of the 925 rows, search committed artefacts for a per-row checker-rationale proof: a recorded evaluation for that exact row key showing the K1 failure is a checker-rule artefact independent of build. The R01 predicate `in_eo_same == 1` and the 3-07 200-sample witness are **not** per-row proofs. Rows with such a proof keep `checker`, citing it; the rest join the test.
  2. **Proven-fixed (`build:eo_bg_stitch`)** only if all hold:
     - (a) K1 failing 0 for the row's vertex position on `4ed9cd80` (plan 39 clause a);
     - (b) a record on `4ed9cd80` in L **byte-equals S's `d35b565` clip into L**, or holds at least one owner-exclusive vertex of S at its exact raw position;
     - (c) the cell is in the 3-14 changed list with class `eo_bg_stitch` (plan 36 P3).
  3. **Otherwise named residual** with the failing clause: `producer-ambiguous`, `no-owner-exclusive-vertex`, `source-removed` (S emits nothing in L at `d35b565`), or `still-failing`.
  4. **Control:** a stratified sample of plan 39's 825,634 identity-proven rows is re-tested. ≥ 99% must agree, and every disagreement is reported. A systematic disagreement stops the phase.
  5. `rules_bg.json` gets a note only. The per-row cause of record stays `assignment.tsv`.
- **Non-goals:** the 80 ceiling rows (design 45); non-R01 background rows (design 46).

## Decisions

1. Plan number 44. Master direct. Two phases.
2. R-G5-4-b is folded in (ruling 3).
3. Byte-equal producer match counts as the strongest form of owner-exclusive evidence. Owner-exclusive vertices are the minimum ruling-2 standard.

## Assumption ledger

### Assumption 1

- **Question:** Is the candidate-supplier set "every source of any type whose bbox meets L" complete?
- **Answer chosen:** Yes for "no neighbouring polygon could supply". Any record in L must come from a source routed to L. The routing uses the build's E1 path with all source cells retained (3-12 H12 method).
- **Rationale:** A neighbour is defined by the build's own routing, not by old records.
- **If wrong:** the supplier set is widened to the 3×3 neighbourhood of home cells. Rows that change verdict are reported.

### Assumption 2

- **Question:** Can the `33006aa` probe reproduce old record bytes exactly?
- **Answer chosen:** Expected. Plan 36 rebuilt `013586b5` byte-exact at `33006aa`, and 3-12 H12 matched producer bytes with the same arithmetic.
- **Rationale:** Same code.
- **If wrong:** rows without a byte-exact producer are `producer-ambiguous` residuals, never assigned.

## Open questions

None blocking.

## Phases

### Phase 1: Owner-exclusive tool landed and controlled

- **Outcome:**
  1. `bg_owner_exclusive.py` with tests: synthetic shared-vertex, edge and different-type supplier cases.
  2. Control re-test of the plan 39 proven sample with an agreement figure.
  3. The 925-row checker-rationale inventory, with the count keeping `checker` and the citations.
- **Surfaces:** `parser/tools/bg_owner_exclusive.py`, `parser/tests/test_bg_owner_exclusive.py`, `parser/perf_inventory.json`, `triage/historical_bg/p5_owner_exclusive/`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Every row of R-G5-4-a and the joined R-G5-4-b rows decided

- **Outcome:**
  1. Per-row table for all 95,059 rows (minus any kept as checker with a proof): `build:eo_bg_stitch` or a named residual class, with counts.
  2. `assignment.tsv` updated.
  3. `residuals.tsv` R-G5-4-a/b discharged, or replaced by exact residual children.
- **Surfaces:** `triage/historical_bg/p5_owner_exclusive/`, `p2/assignment.tsv`, `triage/rules_bg.json` (note), `residuals.tsv`, `cause_table.md` R01 note, `docs/provenance.md` (scratch-44).
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `6538530`. Sources:
  - plan 39 record (P2 table, Residual Risks, re-review N1);
  - `historical_bg/reviews/review2-REVIEW.md`;
  - `rules_bg.json` R01;
  - plan 36 P3 classes;
  - `causes_residual.md` (H12 producer method).
- Box draft only.
