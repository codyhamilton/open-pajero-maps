# 2-01 source-data parity (342 cells)

Plan 30 disposed of all 342 plan-14 `g-omits-cell-local-dvd-type` (2-01)
rows. Final result:

- **341 supply-path.** Each row is backed by a production-C witness from OSM
  boundary relations. They are successor implement candidates, not fixes.
- **0 unfixable-proven.**
- **1 carried residual: dump_row 246.**
  - Design ruled on 2026-10-06 at 12:45 AEST that it is **not**
    unfixable-proven.
  - Its candidate cause is named but **unproven**.
  - It is owned by plan 38.

No disc, encoder, vocabulary, selection or spool changed. The oracle in
force stays `4e6b0de7…`. Lasting artefacts are in
`docs/plans/04-c-core-orchestration/triage/source_parity/` (see its
`README.md`).

## Intent
User request, verbatim (DESIGN):

> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> The Maps designs pipeline is empty. Pick the single highest-value next unit. The 342 plan-14 group `g-omits-cell-local-dvd-type` (2-01) rows carry a source-data parity observation: R emits a cell-local DVD type while the spool holds no encodable source of that type, so G cannot match R without inventing geometry. Prove, for every row, whether an encodable source can be supplied or the deviation is unfixable — with a named root cause either way. Never invent geometry. Never relabel. Heavy Python/encode only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed unless a design's provable outcome is exactly that and it is evidenced; no 3-90 re-run. Skip anything plan 29's pending close-out will cover.

## Why This Existed
- Plan 14 fixed completeness as checker over-demand, so live completeness
  failing is 0.
- That left 342 cells where R has a cell-local polygon of the demanded type
  and G has none. These were carried only as an unproven "source data"
  observation, with a false census ("342 × 288").

## What Was Built
Commits: `3447b39` (DESIGN), `9c808c9`, `5147554`, `10a4e66` (Phase 1
close), `5d2fe64`, `1a08dc2`, `10ac108` (Phase 2 close, 243/0/99),
`9f72ece` (terminal review PASS), `828667c`, `537da1e`, `f1a1368`
(338/0/4), `7913160`, `4c07832` (Amendment 1), `59aeafd`, `115d720`,
`bf46547`, `617c7c8`, `873f161` (341/0/1), and this close-out.

### Phase 1: fingerprint and census
- `fingerprint.py` / `fingerprint.tsv` cover 342 rows.
- **Census: 341 × 288 + 1 × 321** (dump_row 246, L0 (834,886)).
  - The plan-14, `phase3_groups.md` and plan-28 wording was corrected
    append-only.
- **The 288 cohort is one 5′ × 7.5′ 13-vertex template:**
  - T1 191 / T2 150, which share a winding and differ only in start corner;
  - 0 exceptions.
- G emits 0 of the demanded type in all 342 cells on both `2ee3456a…` and
  historical `4ed9cd80…`.

### Phase 2: disposition
- **Unit 2-01:** spool + PBF + lattice discriminators give 243 / 0 / 99.
  - Every supply witness is an OSM `type=boundary` / `protected_area`
    relation that the spool lacks as an emitting source.
- **Unit 2-02:** PBF relation-gap correction (area-role ring assembly,
  cache replay/pin, member-limit gaps) gives 338 / 0 / 4.
- **Amendment 1** (Design option (a)):
  - Root cause first: all 3,619 missing member ways of the 29 relations
    existed in OSM at the PBF timestamp `2026-08-24T20:20:50Z` and lie
    outside the extract polygon, so this is extract clipping
    (`missing_way_attic_proof.json`).
  - Pin before use: a date-matched Overpass attic snapshot of the
    61 relations, `39a836dd…`, ODbL, recorded in `docs/provenance.md`.
- **Unit 2-03:**
  - The snapshot is an opt-in, hash-pinned supplement to the `pbf-cache`
    probe, with pinned-first supply preference, a Mainland Australia
    relation cap and an antimeridian 0–360 frame.
  - The no-flag control is identical to r2.
  - **Result: 341 / 0 / 1.** Rows 396, 397 and 775 are supplied by r2647638
    Australia (EEZ), using 131 cache + 16 snapshot ways.
- `disposition.tsv` / `disposition_summary.json` record:
  - the verdict, cause class and discriminators for every row;
  - the production-C counterfactual and successor implement path for every
    supply row.

## Residual: dump_row 246 (carried, cause unproven)
- **Cell and code:** L0 (834,886), demanded code 321 (wood/grass/park).
- **Evidence** (`open_rows_account.md`, `reports/2-03-…`):
  - the PBF leg is gap-free;
  - 284 code-321 candidates (natural=wood 274, scrub 10) give 0 in-cell
    records.
  - The retained spool 321 demander touches the cell edge (vertex 18,
    −31.5416545 116.0931811), and its clip collapses
    (`encoder_drops_clipped_source_sliver`).
  - So absence of supply is not provable.
- **Design ruling (2026-10-06, 12:45 AEST):** **not** unfixable-proven.
- **Candidate cause (UNPROVEN):** R's in-cell 321 record may come from that
  edge-touching relation under a different clip-inclusion rule. R would keep
  boundary-touching or degenerate clips that our encoder drops.
- **Owner: plan 38** (Design drafting). Its steps:
  1. Byte-decode R's record.
  2. Match it to the relation.
  3. Then either fix the clip rule with no other cell or kind change, or
     record the proven cause.

## Deviations
- **Workers.** Units 1-01 and 2-01 were Codex workers. Units 2-02 and 2-03
  were done by Execute, because Codex is weekly-limited until 2026-10-10
  11:50 AEST.
- **Terminal review of the reopened increment** was by a Claude CLI
  clean-context seat, not Codex. Disclosed; see Review.
- **Phase 2 outcome is met via item 6** ("`conflict-open` is 0, or each
  open row lists discriminators tried"). Row 246's `discriminator_records`
  list lattice-identity, spool, PBF, the retained demander and `unresolved`.
  Per Design's ruling it is carried as a named residual, not as
  `unfixable-proven`. The 2-03 IMPLEMENTATION note "outcome not met"
  misread item 6 and is superseded here.
- **Snapshot use is wider than Amendment 1 §2's wording.** Brief 2-03 also
  admitted, from the snapshot, relation tags and members for the 5
  never-retained relations (4095122, 15480206, 16308779, 16308787,
  16308826), and area-role children as eligible sources.
  - This is a brief-level extension.
  - No verdict depends on it:
    - the 338 earlier rows are pinned-first and unchanged;
    - 396/397/775 take tags and members from the pinned cache;
    - r4095122 emits only 288 at row 246.
  - The `docs/provenance.md` "Use:" line is corrected.
- **Paths after the move.**
  - The sha-pinned data artefacts keep historical labels under
    `docs/plans/30-2-01-source-data-parity/`; the `source_parity/README.md`
    maps them.
  - The scripts' `ROOT` depth changed, so replaying the old summaries now
    fails closed on the script sha. A successor must re-pin.

## Review
- **Phases 1–2 at 243/0/99:** clean Codex terminal review, PASS (`9f72ece`).
  One low finding (boundary-relation wording) was fixed in review.
- **Reopened increment (2-02 / Amendment 1 / 2-03):** a Claude CLI
  clean-context terminal review at close-out (2026-10-06). Verdict and
  findings are below.

- **Verdict: PASS_WITH_FOLLOWUPS**
  (`docs/plans/04-c-core-orchestration/triage/source_parity/reviews/terminal-review-reopened.md`, Claude CLI seat).
- **Verified:**
  - the counts;
  - rows 246/396/397/775 field by field;
  - every Amendment 1 condition, with timestamps (proof 10:59, pin 11:03,
    first use 11:42; snapshot re-hashed `39a836dd…`; originals read-only;
    guarded steps);
  - the `disposition.py` snapshot logic (sha `32121392…` = summary input);
  - tests: 75 passed.
- **F1 (medium):** record the Design ruling, correct "not met", and point
  OVERVIEW and plan 38 at row 246. Done in this record, in OVERVIEW and in
  the post-close note in `open_rows_account.md`.
- **F2 (medium):** the per-row `successor_implement_path` for **rows 396,
  397 and 775** does not say that 16 of their 147 member ways come only
  from the date-matched snapshot.
  - Fixed by hand-off note (option b): a successor implementing from the
    pinned PBF alone cannot reproduce these three witnesses.
  - It needs the complete relation r2647638: the snapshot `39a836dd…` or an
    equivalent build input. That is a Design input decision for plan 38 or
    the implement unit.
  - `disposition.tsv` was not re-published, because the heavy lock was held
    by the plan 36 encode, and the scripts' sha changed with the move.
- **F3 (low):** snapshot use is wider than the §2 wording; see Deviations.
  Provenance is corrected.
- **F4 (low):** row 396's PBF `blocking_gaps` entry for the r16623818
  crossing/touching gap carries the generic snapshot `resolution` string.
  The snapshot does not resolve a crossing. The gap is non-blocking because
  a positive witness covers the row. Record-only.
- **F5 (info):** the root-cause polygon is Geofabrik's current
  `australia.poly`, not a date-matched one. The conclusion stands: the bbox
  equals the PBF header bbox, and 3,386 / 3,619 ways lie wholly outside it.
- **F6 (info):** the tests were re-run after the move: plan 30 and O04
  tests, 156 passed.

## Residual Risks
- Row 246 cause is unproven; see Residual.
- The 341 supply rows are witnesses, not an implementation. G still omits
  all 342 cells until a successor implement unit lands.
- Rows 396, 397 and 775 depend on 16 ways that exist only in the
  date-matched snapshot. A successor needs that snapshot, or an extract
  that includes them. Their per-row `successor_implement_path` does not
  say so (review F2).

## Follow-ups
- **Plan 38 (Design drafting):** the row 246 clip-inclusion question, and
  the successor implement path for the 341 supply rows.
  - Plan 35 `residuals.tsv` R-G9-1 / R-G9-2 point here and to plan 38.
- Both are Maps parity carried, not Phase 3 blockers.

## Decisions Worth Keeping
- **Presence parity, not geometry clone:** an honest in-cell emission of
  the demanded type is supply. R's tile is never copied.
- **The verdict rule is strict.** Without a supply witness, a row stays
  open until absence from the date-matched source is proven. Option (b)
  ("outside the pinned source ⇒ unfixable") is rejected.
- **Second pinned sources:** date-matched, root cause proven first, pinned
  before use, and scoped to the named geometry only.
