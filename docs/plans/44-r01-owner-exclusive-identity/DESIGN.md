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

Cody HARD (reaffirmed for this second revision): no waivers; every deviation needs a proven root cause. Loosening cover (partial / Jaccard) is not justified. Carving the control to ignore no-cover without a named RC is not justified.

## Problem

Plan 39 P2 tested R01 rows by shape-level clause (b) with an identity guard. A row's item persists if a same-type record in the same leaf on `4ed9cd80` holds at least one non-failing vertex that no other old same-type record in the leaf holds and that is not on the leaf edge.

**Two weaknesses:**
- The guard uses **old records** as the only possible suppliers, so a vertex shared with a source that had no old record in the leaf, or a different-type source, passes.
- The "leaf edge" is the leaf's **vertex bbox**, not the leaf rectangle (plan 39 Residual Risks).

| Child | Rows | Plan 39 status |
| --- | ---: | --- |
| R-G5-4-a | 94,134 | weak: every shared non-failing vertex is held by another old same-type record or lies on the leaf edge |
| R-G5-4-b | 925 | no traceable same-type record on `4ed9cd80` after excluding records identical to unchanged neighbours |

**Ground (master `6538530`; Phase 1 tool landed at `0551ed2`; fragment-producer + Assump-1-window control at `8ee2559`):**
- Plan 39 `historical_bg/p2/{shape_clause_b.py, r01_clause_b.py, r01_clause_b_control.py, assignment.tsv, allrows/}`.
- Per-row arrays are keyed in `output/scratch-39/keep/` (git-ignored, BOM in `docs/provenance.md`).
- Discs `87a01b14` (`scratch-36/G_pre311`), `013586b5`, `4ed9cd80` and the pinned spool are available.
- The tracked `parser/tools/k1_representable.py` carries the full-EO-topology clip contract (plan 14), and the `bg_shape` probe pattern is in `parser/tests/fixtures/bg_eo/probe.c`.
- `rules_bg.json` R01 note: "Independent all-level witness: 200/200 valid". That is a sample witness from 3-07, not a per-row proof.
- First DESIGN-stop at `0551ed2`: smoke n=12 rate 0.25; home-with-bg n=60 rate 0.3167; all disagrees `prod_none`. Root cause: byte-equal-only producer; identity-proven shapes are EO fragments. First revision added unique-fragment.
- Second DESIGN-stop at `8ee2559` (stratified control n=200 seed=44): rate **0.7576 (150/198)**; agree 91 unique-fragment + 59 unique-byte; all **48 disagrees** `producer_none` / no-cover under neighbourhood=1. Cover definition held; OE limb was 100% whenever a unique producer existed. Critical: `leaf_io` neighbourhood=1 **already is** the Assump-1 3×3 window — that fallback is exhausted; do **not** revise to "just enable 3×3."
- Post-commit `diag_nbhd` on the same 48 (recovery includes unique-byte as routing signal):

| Moore radius | recovered of 48 | projected agree/198 |
| ---: | ---: | ---: |
| 1 (3×3) | 0 | 0.7576 |
| 2 (5×5) | 16 | 0.8384 |
| 3 (7×7) | 25 | 0.8838 |
| 5 (11×11) | 37 | 0.9444 |

  Still 11 `producer_none` at nb=5 → still short of ≥0.99 under the old full-set agreement gate. Bucket of 48 at nb=1: ~18 zero spool; ~20 few clips incomplete IB cover; ~10 many clips incomplete IB cover. Mostly full uncover (41/48). Plan 39 identity-proven never consults spool — definitional routing gap (search-window understatement, not OE failure).

## Solution shape

### Domain: exact producer and owner-exclusive vertex sets

- **Owns:** a tracked tool `parser/tools/bg_owner_exclusive.py` with a C probe shim (built from the commit's `_cenc.c`, `-O2 -ffp-contract=off`, exact `kw_bounds` arithmetic), synthetic tests and a perf-inventory entry.
- **Contract:**
  1. **Producer, two classes.** For each row's old record (the record carrying the failing vertex, on `013586b5`), consider spool candidates S from the **revised candidate set** (below). Probe each S at `33006aa` into L's exact integer rectangle. Classify:
     - **unique-byte:** exactly one S whose clip bytes equal the old record. Strongest.
     - **unique-fragment:** no unique-byte; exactly one S such that (a) every identity-bearing vertex of the record appears in S's `33006aa` clip into L, and (b) at least one of those vertices is not produced by any other candidate's `33006aa` clip into L. **Identity-bearing** = not on L's rectangle boundary and not R01-failing on the old disc.
     - Zero matching S under the search in force → residual class **`producer_none`** as a pre-census label only; Gate B requires promoting it to a named producer residual with proven RC (below).
     - More than one matching S (under either class's matching rule, when that class is the one being applied) → **`producer_ambiguous`** (tool / residual spelling; census class `producer_ambiguous`).
     EO cover/fragment pieces on disc take **unique-fragment**, not unique-byte. The prior byte-equal-only producer was the first DESIGN-stop cause (`0551ed2`). The Assump-1 bbox-meet / nb=1 window was the second (`8ee2559`).
  2. **Candidate suppliers of leaf L (revised; Assump-1 chosen answer marked wrong):** the union of
     - (a) every spool source of any type whose bbox meets L at the same level; and
     - (b) every spool source of any type whose home cell lies in a Moore neighbourhood of radius **R** around the leaf home cell.
     R is **not** preset to 1. `leaf_io` neighbourhood=1 already implements Assump-1's former "3×3" fallback and recovered 0 of 48 — that path is exhausted. Phase 1 must run an **offset census** on control disagrees (distribution of recovering `(dx,dy)` / min radius / class) before locking R for the Phase 2 tool default. Interim Phase 1 control re-runs use **expanding search**: for each row, grow Moore radius from 1 upward until unique-byte or unique-fragment, or hit Design cap **R_cap=8** (17×17), logging the recovering radius. R_cap is a bound for the census, not a claim that 8 suffices for ≥99% agreement-rate.
  3. **Cover definition (unchanged):** cover = all identity-bearing verts of the disc record appear in one candidate's `33006aa` clip into L; exclusive-among-candidates for unique-fragment. Do **not** loosen (no partial / Jaccard).
  4. **Owner-exclusive vertices of S in L (post-3-14):** vertices of S's `d35b565` clip output into L's exact integer rectangle that:
     - no other candidate supplier's `d35b565` clip into L produces at the same raw position; and
     - do not lie on L's rectangle boundary; and
     - are not R01-failing on the old disc.
  5. Bounded: per-leaf streaming over sorted rows, under the lock, with no whole-file loads.

### Domain: per-row verdict for the 94,134 + 925

- **Owns:** `triage/historical_bg/p5_owner_exclusive/` holding the per-row table (committed gz), a summary, and the `assignment.tsv` / `residuals.tsv` updates.
- **Contract:**
  1. **Ruling 3 inventory first.** For each of the 925 rows, search committed artefacts for a per-row checker-rationale proof: a recorded evaluation for that exact row key showing the K1 failure is a checker-rule artefact independent of build. The R01 predicate `in_eo_same == 1` and the 3-07 200-sample witness are **not** per-row proofs. Rows with such a proof keep `checker`, citing it; the rest join the test.
  2. **Proven-fixed (`build:eo_bg_stitch`)** only if all hold (S may be unique-byte or unique-fragment under the locked R after census, or under expanding search ≤R_cap during Phase 1):
     - (a) K1 failing 0 for the row's vertex position on `4ed9cd80` (plan 39 clause a);
     - (b) a record on `4ed9cd80` in L **byte-equals S's `d35b565` clip into L**, or holds at least one owner-exclusive vertex of S at its exact raw position;
     - (c) the cell is in the 3-14 changed list with class `eo_bg_stitch` (plan 36 P3).
  3. **Otherwise named residual** with the failing clause: a Gate-B producer residual class (below), `producer_ambiguous`, `no-owner-exclusive-vertex`, `source-removed` (S emits nothing in L at `d35b565`), or `still-failing`. Bare unexplained `producer_none` does not close.
  4. **Control gates (revised; both required to close Phase 1).** The prior ≥99% agreement-rate against all plan-39 identity-proven rows **conflated** spool producer attribution under a narrow window with OE/new-disc correctness. Plan 39 never used spool producers. Replace with:

     **Gate A — OE limb (unchanged spirit):** Among stratified-sample rows that resolve unique-byte or unique-fragment under the expanding search (≤R_cap), ≥99% must pass the OE/new-disc check. Every disagreement reported. Systematic OE disagreement still stops.

     **Gate B — producer census (new):** Every evaluable stratified-sample row must receive exactly one of: unique-byte, unique-fragment, or a **named producer residual with proven root cause** recorded in `control_analysis.md`. Allowed producer residual classes for census:
     - `producer_home_outside_R_cap` — expanding search to R_cap still no-cover; record max radius tried, spool/clip counts, IB/uncovered counts;
     - `producer_ambiguous` — >1 cover at the recovering radius.
     Tool-level `producer_none` remains only as the pre-census label; Gate B forbids closing on bare `producer_none` without one of the named RC classes. Gate B passes at **100% class coverage with RC**, not at 99% unique-* rate. This is not a waiver: unexplained `producer_none` still blocks.
  5. `rules_bg.json` gets a note only. The per-row cause of record stays `assignment.tsv`.
- **Non-goals:** the 80 ceiling rows (design 45); non-R01 background rows (design 46).

## Decisions

1. Plan number 44. Master direct. Two phases.
2. R-G5-4-b is folded in (ruling 3).
3. Byte-equal producer match (unique-byte) is the strongest form of producer evidence. Unique-fragment plus owner-exclusive vertices is the ruling-2 path for non-full-leaf records (EO cover/fragment pieces on disc). Owner-exclusive vertices remain the minimum ruling-2 standard on the new disc. Cover stays full IB cover; no partial / Jaccard.
4. **Control gates are Gate A + Gate B** as above. Agreement-rate ≥99% against the full identity-proven set is **retired** as the Phase 1 stop condition because it measured search-window understatement under Assump-1, not OE failure (`8ee2559` + `diag_nbhd`).
5. **R for Phase 2 defaults is locked only after the offset census** lands in `control_analysis.md`. Design amends the number in a follow-up note if needed. For this revision: Execute reports the census and uses expanding search ≤R_cap=8 for Gate A/B; if Gate A+B pass, Phase 1 closes and Execute proposes R = max recovering radius among unique-* in the sample (or a percentile with proof) in IMPLEMENTATION for Design to confirm before Phase 2 mass run. Rows that remain `producer_home_outside_R_cap` after census become named Phase 2 residuals (or residual children of R-G5-4), never silent.

## Assumption ledger

### Assumption 1 — CHOSEN ANSWER MARKED WRONG

- **Question:** Is the candidate-supplier set "every source of any type whose bbox meets L" complete?
- **Answer previously chosen:** Yes for "no neighbouring polygon could supply". Any record in L must come from a source routed to L. The routing uses the build's E1 path with all source cells retained (3-12 H12 method). Former fallback: widen to the 3×3 neighbourhood of home cells.
- **Answer now (second revision):** **Wrong.** Evidence: the Assump-1 window (bbox-meet, and equivalently `leaf_io` neighbourhood=1 = 3×3) understates true producer homes for a large fraction of identity-proven R01 fragments. At `8ee2559`, 48/198 stratified control rows were `producer_none` / no-cover at nb=1; `diag_nbhd` recovered 16/48 at radius 2, 25 at 3, 37 at 5 (including unique-byte as routing signal). The former "if wrong → 3×3" branch is exhausted — nb=1 already is that window and recovered 0 of those 48.
- **New candidate definition:** union of (a) every spool source whose bbox meets L, and (b) every spool source whose home cell lies in a Moore neighbourhood of radius R around the leaf home cell. R is not preset to 1. Phase 1 runs an offset census on control disagrees (distribution of recovering `(dx,dy)` / min radius / class) before locking R for Phase 2. Interim control uses expanding search from radius 1 to **R_cap=8** (17×17), logging recovering radius. R_cap bounds the census; it does not claim 8 yields ≥99% agreement.
- **Rationale:** Plan 39 identity-proven never consults spool — definitional routing gap. Widening via census + expanding search is the proven root-cause response; loosening cover or ignoring no-cover without RC is not.
- **If still wrong after census:** rows outside R_cap are named `producer_home_outside_R_cap` with counts; Design amends R / R_cap only with further proven evidence. No waiver.

### Assumption 2

- **Question:** Can the `33006aa` probe reproduce old record bytes exactly for the identity-proven population?
- **Answer chosen (revised after `0551ed2` control stop):** No — a byte-exact full-leaf clip is **not** expected for the plan 39 identity-proven population. Many identity-proven R01 shapes are EO fragments / cover pieces whose disc bytes disagree with a full-leaf `33006aa` clip of the geometric source (`control_analysis.md`). Fragments are expected; they take unique-fragment, not unique-byte. Unique-byte remains the strongest class where it holds.
- **Rationale:** Control smoke and home-with-bg rates under byte-equal-only were systematically `producer_none`; OE limb was 100% whenever a unique producer existed. Same probe arithmetic; the records are not full-leaf clips. Confirmed again at `8ee2559` (91 unique-fragment + 59 unique-byte among 150 agrees).
- **If wrong:** if fragment attribution is wrong (false unique), widen the supplier set further via census and report rows that flip class or verdict.

### Assumption 3

- **Question:** Where does the identity-bearing vertex set for fragment attribution come from?
- **Answer chosen:** Old-disc record vertices (the disc record carrying the failing vertex). The dump may not retain the full vertex set; use the disc record verts. Identity-bearing = not on L's rectangle boundary and not R01-failing on the old disc.
- **Rationale:** Fragment attribution compares record geometry to probe clips; the record on disc is the authoritative shape. Cover = all IB verts in one candidate's clip (unchanged; not loosened).
- **If wrong:** if dump verts are required and diverge, name the divergence per row and do not assign on mismatched sets.

## Open questions

None blocking. Offset census + expanding search ≤R_cap=8, Gate A, and Gate B are Phase 1 work. Locking the Phase 2 default R is a Design follow-up after Execute's census lands in `control_analysis.md` / IMPLEMENTATION proposal.

## Phases

### Phase 1: Owner-exclusive tool landed and controlled

- **Outcome:**
  1. `bg_owner_exclusive.py` with tests: synthetic shared-vertex, edge and different-type supplier cases; **unique-fragment producer support** (identity-bearing vertex set; exclusive-among-candidates clause) — **done** (fragment-producer landed; Assump-1-window control at `8ee2559`).
  2. **Offset census + expanding search:** on control disagrees, record recovering `(dx,dy)` / min radius / class; re-run control with Moore radius growing from 1 to R_cap=8 per row until unique-byte or unique-fragment (or residual). Log recovering radius. Write census into `control_analysis.md`.
  3. **Gate A:** ≥99% OE/new-disc pass among rows that resolve unique-byte or unique-fragment under expanding search ≤R_cap. Every disagreement reported. Systematic OE disagreement stops.
  4. **Gate B:** 100% class coverage with RC — every evaluable stratified-sample row is unique-byte, unique-fragment, `producer_home_outside_R_cap`, or `producer_ambiguous`, with proven RC in `control_analysis.md`. Bare `producer_none` does not close.
  5. The 925-row checker-rationale inventory, with the count keeping `checker` and the citations — **done** (inventory complete; join/keep counts as recorded).
- **Surfaces:** `parser/tools/bg_owner_exclusive.py`, `parser/tests/test_bg_owner_exclusive.py`, `parser/perf_inventory.json`, `triage/historical_bg/p5_owner_exclusive/` (including `control_analysis.md`).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.
- **Status:** tool + fragment-producer + Assump-1-window control landed at `8ee2559` and stopped on search-window understatement (48/198 `producer_none` at nb=1; `diag_nbhd` shows recovery at nb≥2). Offset census + expanding search + Gate A + Gate B remain before Phase 1 close. Prior ≥99% full-set agreement-rate is retired.

### Phase 2: Every row of R-G5-4-a and the joined R-G5-4-b rows decided

- **Outcome:**
  1. Per-row table for all 95,059 rows (minus any kept as checker with a proof): `build:eo_bg_stitch` or a named residual class, with counts. S from unique-byte|unique-fragment under the **locked R** (Decision 5, after census). Rows that remain `producer_home_outside_R_cap` after census become named Phase 2 residuals (or residual children of R-G5-4), never silent.
  2. `assignment.tsv` updated.
  3. `residuals.tsv` R-G5-4-a/b discharged, or replaced by exact residual children.
- **Surfaces:** `triage/historical_bg/p5_owner_exclusive/`, `p2/assignment.tsv`, `triage/rules_bg.json` (note), `residuals.tsv`, `cause_table.md` R01 note, `docs/provenance.md` (scratch-44).
- **Approach:** known. **Depends on:** Phase 1 (Gate A + Gate B pass) and Design confirmation of proposed R before mass run. **Refine:** skipped.

## Provenance

- Master `6538530`. Phase 1 tool commit `0551ed2` (first control stop, byte-equal-only). Fragment-producer + Assump-1-window control commit `8ee2559` (second control stop). Sources:
  - plan 39 record (P2 table, Residual Risks, re-review N1);
  - `historical_bg/reviews/review2-REVIEW.md`;
  - `rules_bg.json` R01;
  - plan 36 P3 classes;
  - `causes_residual.md` (H12 producer method);
  - `triage/historical_bg/p5_owner_exclusive/control_analysis.md` (fragment / cover-piece finding; smoke and home-with-bg rates; `8ee2559` stratified rates; `diag_nbhd` table).
- **First revision (box draft):** producer contract revised after `0551ed2` — unique-byte and unique-fragment replace byte-equal-only; `producer_none` named; Assumption 2 revised.
- **Second revision (box draft):** Assump-1 chosen answer marked **wrong**; candidate set = bbox-meet ∪ Moore(R); R not preset; offset census + expanding search ≤R_cap=8; control gates replaced by Gate A (OE ≥99% among resolved) + Gate B (100% class coverage with RC); full-set ≥99% agreement-rate retired; `8ee2559` rates + `diag_nbhd` recorded as DESIGN-stop evidence under Assump-1 window; cover unchanged; no waivers. Designs 45 and 46 cite expanding Moore search / post-census R in lockstep (not Assump-1-only bbox-meet).
- Box draft only.


## Decision 5 lock (Execute 2026-10-07 15:09 AEST)

Design confirmed Phase 2 default **R=8** after Phase 1 Gate A+B close (`64120f6`) and offset census (max recovering radius among unique-* = 8). Right-censor protocol: residual-only widen to R_widen=16 before final `producer_home_outside_R_cap` classification; ≥20 recovers at radius >8 stops for Design. Cover and OE limbs unchanged.
