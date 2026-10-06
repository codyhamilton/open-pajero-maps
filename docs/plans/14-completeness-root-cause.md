# Completeness root cause

Plan 14 proved a root cause for every K1 completeness failure still unattributed on the post-3-14 AU disc (`4ed9cd80…`) after plan 04's 3-15/3-16/3-17 work: 776 failing `(cell, type)` keys. It built a per-row R/G/spool evidence table and split the rows into two reproducer-backed groups. It found that the checker demanded footprints the wire format cannot represent, and fixed the checker so the demand applies only to representable footprints. Live completeness went from 776 failing to 0 with `checked` unchanged and the build sha unchanged. Every row has a named cause, and no row was closed by relabelling. Phase 1's per-rule classify assignments were never recovered, so that phase is recorded as partial.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Maps Manager asked Design to produce the next design so the lane can move again. The open remainder is the still-unattributed completeness failures after 3-15 / 3-16 / 3-17. Prove root causes from R vs G vs spool evidence; never close a row by relabelling. Land each phase on master. No feature branch. No pull request. Do not reseat 170, 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06.

## Why This Existed

K1 completeness still failed on the disc in force, and plan 04 Phase 3 could not close while the remainder was unattributed.
- 3-15 had labelled most of it `checker:repaired-not-representable`, a science label with no live rule, byte proof or registered cause.
- 3-16 had only rejected one EO-stitch hypothesis for the 89 added keys.
- 3-17's classify left 308 rows unclassified.

## What Was Built

**Evidence.**
- Every failing key appears once in a committed table (`docs/plans/04-c-core-orchestration/triage/completeness_evidence.{tsv,md}`). Each row carries its full native key, its historic-188/added-89 membership, and witnesses: original DVD (R) and generated (G) byte-range decodes, plus the spool/K1 requirement.
- All 1,791 byte ranges are audited.

**Groups.** Exhaustive and disjoint: `phase3_membership.tsv`.
- **2-01 `g-omits-cell-local-dvd-type`, 342 rows.**
  - R emits the type cell-locally; G does not.
  - Each row's demanding spool source gives 0 records from the production encoder in the target cell.
- **2-02 `r-absent-complete-repair-zero`, 434 rows.** Defined as "R polygons contributing 0 cell-local records".
  - The 432 R-absent rows: a complete-repair reproducer (exact EO faces, the encoder's clip/densify/round mirror, and the production C `bg_shape` probe) gives 0 records on all of them.
  - dump_row 765 (R polygon wholly in column 1304, 9,615 raw west of the cell) and dump_row 335 joined by Design ruling. Both have 0 R cell-local records and 0 encoder records.
- **Attribution.** All 799 demanding shapes behind the 776 keys were enumerated from the checker's own block region: branch a 1, b 797, c 1. All were unrepresentable.
- **335's distinct trigger.** A type-288 triangular sliver (home cell (1379,1143)) misses key cell (1379,1138)'s centre by 0.348 raw. The old checker's 0.5-raw centre slack wrongly counted it.

**Fix (checker).**
- The completeness checker fails an absent pair only if some demander has a representable in-cell footprint, implemented independently of the encoder in C and Python (contract: `docs/design/k1-completeness.md`).
- Review then found shared EO-topology gaps (vertex-touching lobes, retraced contours), and both implementations were completed.

**Changed:** `parser/kiwiw/_k1_cmp.c`, `_k1.c`, `_k1.h`, `cenc.py` (tall-row multiplier); `parser/tools/quantisation_roundtrip.py`; new `parser/tools/k1_representable.py`; new `parser/tests/test_k1_completeness_representable.py` plus fixtures; plan-14 reproducers and evidence under `docs/plans/04-c-core-orchestration/triage/` (`cell_local_2-01.py`, `complete_repair_2-02.py`, `residuals_2-03.py`, `demand_attribution_3-01.py`, `r_contribution_3-02.py`, `build_evidence.py`, `verify_evidence.py`, and their TSV/notes); `docs/provenance.md` (`output/scratch-14/`).

**Verification.**
- Live K1 on `4ed9cd80…`: checked 1,800,514 → 1,800,514, failing 776 → 0. The removed set equals the attribution prediction exactly, and every other kind is unchanged.
- A re-encode with the rebuilt library reproduces `4ed9cd80…`.
- Real-data positive control: on the pre-3-14 disc built from the same spool (`scratch-3-11/G_new`), the old checker fails 739 and the new one fails exactly the 52 keys the later build fix repaired, i.e. genuine missing footprints, none of them among the 776. This holds after the topology remediation too.
- 399 tests pass.

### Phase 1 — Per-row evidence table
Delivered the 776-row table on the restored oracle disc. **Partial:** the per-rule classify assignments were never recovered (classify rejects the absent `other_mechanism` column), so every assignment is an evidence gap. No live O01/O04/O05/`NO_RULE` partition is claimed.

### Phase 2 — Root-cause groups
Delivered 2-01 (342) and 2-02 (432), with packaged reproducers, plus two named open questions (335, 765).

### Phase 3 — Fix or proven non-deviation
Both groups were closed as checker over-demand. The fix landed with the counts above, and 765 and 335 were folded into 2-02 by Design rulings.

## Deviations

- Phase 1's literal outcome, per-row rule assignments, was not met. See Phase 1.
- 2-02's membership definition was widened by Design ruling from `R_polygon_count == 0` to "R polygons contributing 0 cell-local records", to admit 765 and 335.
- "Each group is one worker": 2-01 and 2-02 shared one fix site and criterion, so one checker change carried both.
- A spool-destroying symlink step during Phase 2 setup was recovered: the spool was restored with extractor tree `34a04cc` and proven by 775/775 witness pins plus a byte-identical re-encode (recorded in `docs/provenance.md`).
- A `--help` smoke test of the moved triage scripts regenerated Phase 1 scratch outside the heavy-job wrapper. The content was verified equivalent (provenance).
- Codex workers ran in a `workspace-write` sandbox after Auto-review blocked sandbox bypass, so the orchestrator ran the heavy verification and made the commits.

## Review

Independent terminal review (Codex). Initial verdict REMEDIATE; final **PASS_WITH_FOLLOWUPS**.
- **F1 (high), resolved:** EO-topology gaps let two vertex-touching lobes be excused and retraced contours be demanded. Remediated in both checkers and re-verified live and on the older disc.
- **F2 (medium), resolved:** 335 lacked a disposition; resolved by Design ruling.
- **F4 and F5 (low), fixed in review:** the attribution summary filename overflow and a tall-row docstring.
- **F6 (low), resolved in close-out:** the old reproduce instructions now pin the pre-3-03 checker `0b19b5e`.
- **F3 (low), follow-up:** the Phase 1 classify gap.

## Residual Risks

- Proof bytes (`output/scratch-14/`) are ignored scratch, not git objects. Historical reproduction needs the pinned checker (`0b19b5e`) and the retained disc/spool pins.
- The representability filter is proven on this dataset and on synthetic topology cases. A future spool with geometry outside the covered topology classes raises a checker error rather than passing silently.

## Follow-ups

- **Phase 1 classify assignments** (review F3): resolved by plan 28; see the F3 resolution below.
- **2-01 source-data parity, a proven deviation cause:** in the 342 cells R emits type 288 while the spool holds no encodable 288 source, so G cannot match R without inventing geometry. The cause is the source data; it is not a non-deviation. Carried to Design. **Census correction (plan 30, append-only):** the 342 rows are 341 × type 288 plus 1 × type 321 (dump_row 246), not 342 × 288; see `docs/plans/04-c-core-orchestration/triage/source_parity/fingerprint.tsv`.
- **K1 name_anchor 1:** a pre-existing failure outside plan 14; Design is drafting a separate design. K1 therefore still exits 1.
- Plan 04 Phase 3 is not closed by this plan.

**F3 resolution (plan 28).** Fresh current-contract classify assignments cover all 776 baseline native keys: O01 363, O05 132, O04 7, O06 0, NO_RULE 274; their full-key join to 342 (2-01) + 434 (amended 2-02) gives 769 consistent, 7 conflict-proven and 0 conflict-open verdicts, with both cross-tab predictions passing. Each O04 spool cause is retained for plan 04's successor spool list: penultimate deletion produces a representable piece for 138, 284 and 496, and removes demand without a piece for 236, 282, 317 and 563; all seven have zero R presence. The historical Phase 1 record stays partial as written; its assignment gap is resolved by the new evidence. Evidence: `docs/plans/04-c-core-orchestration/triage/per_rule_phase2_join.tsv`, `docs/plans/04-c-core-orchestration/triage/per_rule_phase2_crosstab.tsv`, `docs/plans/04-c-core-orchestration/triage/per_rule_phase2_discriminators.tsv` and `docs/plans/04-c-core-orchestration/triage/per_rule_phase2_reconciliation.md`. The 2-01 source-data parity observation and Phase 1's 3-17 arithmetic/identity limits remain carried; other kinds' joins and plan 04 Phase 3 remain open.

**K1 name_anchor resolution (plan 29, append-only).** The historical follow-up
above was resolved by [plan 29](29-k1-name-anchor-failure.md): byte-backed R
absence established verdict A, and a counted assembly guard removed the single
out-of-span O03 name. Live K1 exits 0 on successor
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`, with
name_anchor 2,317,055 checked / 0 failing and completeness 1,800,514 / 0.
The historical `4ed9cd80…` observations above remain as measured; plan 04
Phase 3 remains open.

## Decisions Worth Keeping

- Locus for unrepresentable demand: the checker, not the build. When the production encoder emits nothing because the source footprint cannot survive clip/densify/round, a build change would have to invent geometry.
- The checker's representability test is an independent implementation of the wire contract and never calls the encoder, so encoder drops stay detectable. A real-data positive control (an older disc with known build defects) is the acceptance test for any change that lowers a failing count through the checker.
