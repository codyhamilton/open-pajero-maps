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

**Ground (master `6538530`; Phase 1 tool landed at `0551ed2`):**
- Plan 39 `historical_bg/p2/{shape_clause_b.py, r01_clause_b.py, r01_clause_b_control.py, assignment.tsv, allrows/}`.
- Per-row arrays are keyed in `output/scratch-39/keep/` (git-ignored, BOM in `docs/provenance.md`).
- Discs `87a01b14` (`scratch-36/G_pre311`), `013586b5`, `4ed9cd80` and the pinned spool are available.
- The tracked `parser/tools/k1_representable.py` carries the full-EO-topology clip contract (plan 14), and the `bg_shape` probe pattern is in `parser/tests/fixtures/bg_eo/probe.c`.
- `rules_bg.json` R01 note: "Independent all-level witness: 200/200 valid". That is a sample witness from 3-07, not a per-row proof.
- Phase 1 control stop at `0551ed2`: smoke n=12 rate 0.25; home-with-bg n=60 rate 0.3167; all disagrees `prod_none` / `disagree_producer_none`. OE limb 100% when a unique `33006aa` producer exists. Control analysis (`triage/historical_bg/p5_owner_exclusive/control_analysis.md`): plan 39 identity-proven R01 shapes are often EO fragments / cover pieces — bytes disagree with a full-leaf `33006aa` clip of the geometric source (e.g. 220 B probe vs 140 B disc). Systematic, not sample noise. R-G5-4-a/b unchanged; Phase 2 not started. Plans 45/46 blocked on this identity rule.

## Solution shape

### Domain: exact producer and owner-exclusive vertex sets

- **Owns:** a tracked tool `parser/tools/bg_owner_exclusive.py` with a C probe shim (built from the commit's `_cenc.c`, `-O2 -ffp-contract=off`, exact `kw_bounds` arithmetic), synthetic tests and a perf-inventory entry.
- **Contract:**
  1. **Producer (old), two classes.** For each row's old record (the record carrying the failing vertex, on `013586b5`), consider spool candidates S whose bbox meets leaf L at the same level. Probe each S at `33006aa` into L's exact integer rectangle. Classify:
     - **unique-byte:** exactly one S whose clip bytes equal the old record. Strongest.
     - **unique-fragment:** no unique-byte; exactly one S such that (a) every identity-bearing vertex of the record appears in S's `33006aa` clip into L, and (b) at least one of those vertices is not produced by any other candidate's `33006aa` clip into L. **Identity-bearing** = not on L's rectangle boundary and not R01-failing on the old disc.
     - Zero matching S → residual class **`producer_none`** (control's dominant disagreement class under the prior byte-equal-only contract).
     - More than one matching S (under either class's matching rule, when that class is the one being applied) → **`producer-ambiguous`**.
     EO cover/fragment pieces on disc are expected to take **unique-fragment**, not unique-byte. The prior byte-equal-only producer was the DESIGN-stop cause of the `0551ed2` control rates; it is not the contract.
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
  2. **Proven-fixed (`build:eo_bg_stitch`)** only if all hold (S may be unique-byte or unique-fragment):
     - (a) K1 failing 0 for the row's vertex position on `4ed9cd80` (plan 39 clause a);
     - (b) a record on `4ed9cd80` in L **byte-equals S's `d35b565` clip into L**, or holds at least one owner-exclusive vertex of S at its exact raw position;
     - (c) the cell is in the 3-14 changed list with class `eo_bg_stitch` (plan 36 P3).
  3. **Otherwise named residual** with the failing clause: `producer_none`, `producer-ambiguous`, `no-owner-exclusive-vertex`, `source-removed` (S emits nothing in L at `d35b565`), or `still-failing`.
  4. **Control:** a stratified sample of plan 39's 825,634 identity-proven rows is re-tested under the revised producer (unique-byte or unique-fragment, then the OE / new-disc check). ≥ 99% must agree (resolve unique-byte or unique-fragment, then pass OE/new-disc check), and every disagreement is reported. A systematic disagreement stops the phase. Phase 1 is not closed until this control passes under the revised contract (re-run after the tool grows fragment-producer support). Prior smoke/home rates under byte-equal-only are DESIGN-stop evidence, not a pass.
  5. `rules_bg.json` gets a note only. The per-row cause of record stays `assignment.tsv`.
- **Non-goals:** the 80 ceiling rows (design 45); non-R01 background rows (design 46).

## Decisions

1. Plan number 44. Master direct. Two phases.
2. R-G5-4-b is folded in (ruling 3).
3. Byte-equal producer match (unique-byte) is the strongest form of producer evidence. Unique-fragment plus owner-exclusive vertices is the ruling-2 path for non-full-leaf records (EO cover/fragment pieces on disc). Owner-exclusive vertices remain the minimum ruling-2 standard on the new disc.

## Assumption ledger

### Assumption 1

- **Question:** Is the candidate-supplier set "every source of any type whose bbox meets L" complete?
- **Answer chosen:** Yes for "no neighbouring polygon could supply". Any record in L must come from a source routed to L. The routing uses the build's E1 path with all source cells retained (3-12 H12 method).
- **Rationale:** A neighbour is defined by the build's own routing, not by old records.
- **If wrong:** the supplier set is widened to the 3×3 neighbourhood of home cells. Rows that change verdict are reported.

### Assumption 2

- **Question:** Can the `33006aa` probe reproduce old record bytes exactly for the identity-proven population?
- **Answer chosen (revised after `0551ed2` control stop):** No — a byte-exact full-leaf clip is **not** expected for the plan 39 identity-proven population. Many identity-proven R01 shapes are EO fragments / cover pieces whose disc bytes disagree with a full-leaf `33006aa` clip of the geometric source (control_analysis.md). Fragments are expected; they take unique-fragment, not unique-byte. Unique-byte remains the strongest class where it holds.
- **Rationale:** Control smoke and home-with-bg rates under byte-equal-only were systematically `producer_none`; OE limb was 100% whenever a unique producer existed. Same probe arithmetic; the records are not full-leaf clips.
- **If wrong:** if fragment attribution is wrong (false unique), widen the supplier set and report rows that flip class or verdict.

### Assumption 3

- **Question:** Where does the identity-bearing vertex set for fragment attribution come from?
- **Answer chosen:** Old-disc record vertices (the disc record carrying the failing vertex). The dump may not retain the full vertex set; use the disc record verts. Identity-bearing = not on L's rectangle boundary and not R01-failing on the old disc.
- **Rationale:** Fragment attribution compares record geometry to probe clips; the record on disc is the authoritative shape.
- **If wrong:** if dump verts are required and diverge, name the divergence per row and do not assign on mismatched sets.

## Open questions

None blocking. Fragment-producer support in `bg_owner_exclusive.py` and a control re-run under the revised contract are Phase 1 work, not open design questions.

## Phases

### Phase 1: Owner-exclusive tool landed and controlled

- **Outcome:**
  1. `bg_owner_exclusive.py` with tests: synthetic shared-vertex, edge and different-type supplier cases; **plus unique-fragment producer support** (identity-bearing vertex set; exclusive-among-candidates clause).
  2. Control re-test of the plan 39 proven sample under the revised producer contract (unique-byte or unique-fragment, then OE/new-disc), with an agreement figure ≥ 99%. Prior smoke n=12 / home-with-bg n=60 rates under byte-equal-only are recorded as DESIGN-stop evidence, not a pass. Phase 1 is not closed until the revised-contract control passes.
  3. The 925-row checker-rationale inventory, with the count keeping `checker` and the citations.
- **Surfaces:** `parser/tools/bg_owner_exclusive.py`, `parser/tests/test_bg_owner_exclusive.py`, `parser/perf_inventory.json`, `triage/historical_bg/p5_owner_exclusive/` (including `control_analysis.md`).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.
- **Status:** tool and byte-equal-only control landed at `0551ed2` and stopped on systematic `producer_none`. Fragment-producer + revised-contract control re-run remain before Phase 1 close.

### Phase 2: Every row of R-G5-4-a and the joined R-G5-4-b rows decided

- **Outcome:**
  1. Per-row table for all 95,059 rows (minus any kept as checker with a proof): `build:eo_bg_stitch` or a named residual class, with counts.
  2. `assignment.tsv` updated.
  3. `residuals.tsv` R-G5-4-a/b discharged, or replaced by exact residual children.
- **Surfaces:** `triage/historical_bg/p5_owner_exclusive/`, `p2/assignment.tsv`, `triage/rules_bg.json` (note), `residuals.tsv`, `cause_table.md` R01 note, `docs/provenance.md` (scratch-44).
- **Approach:** known. **Depends on:** Phase 1 (revised-contract control pass). **Refine:** skipped.

## Provenance

- Master `6538530`. Phase 1 tool commit `0551ed2` (control stop). Sources:
  - plan 39 record (P2 table, Residual Risks, re-review N1);
  - `historical_bg/reviews/review2-REVIEW.md`;
  - `rules_bg.json` R01;
  - plan 36 P3 classes;
  - `causes_residual.md` (H12 producer method);
  - `triage/historical_bg/p5_owner_exclusive/control_analysis.md` (fragment / cover-piece finding; smoke and home-with-bg rates).
- **Revision (box draft):** producer contract revised after the `0551ed2` control stop — unique-byte and unique-fragment replace byte-equal-only; `producer_none` named; Assumption 2 revised; Phase 1 not closed until revised-contract control passes. Designs 45 and 46 cite the revised identity rule in lockstep.
- Box draft only.
