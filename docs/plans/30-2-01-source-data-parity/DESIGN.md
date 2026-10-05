---
design_id:
---

# 2-01 source-data parity (342 cells)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

The Maps designs pipeline is empty. Pick the single highest-value next unit. The 342 plan-14 group `g-omits-cell-local-dvd-type` (2-01) rows carry a source-data parity observation: R emits a cell-local DVD type while the spool holds no encodable source of that type, so G cannot match R without inventing geometry. Prove, for every row, whether an encodable source can be supplied or the deviation is unfixable — with a named root cause either way. Never invent geometry. Never relabel. Heavy Python/encode only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed unless a design's provable outcome is exactly that and it is evidenced; no 3-90 re-run. Skip anything plan 29's pending close-out will cover.

## Problem

Plan 14 closed completeness as checker over-demand and fixed the checker (3-03 + remediation-01). Live completeness is 0 failing and K1 exits 0 on the successor oracle `2ee3456a…` (plan 29). That does **not** discharge DVD parity for the 342 cells where R has a cell-local polygon of the demanded type and G has none.

| Surface (tip `5ff9eb0`) | What it shows | Gap |
| --- | --- | --- |
| Plan 14 record follow-up | "2-01 source-data parity, a proven deviation cause: in the 342 cells R emits type 288 while the spool holds no encodable 288 source… Carried to Design." | Carried; no disposition plan |
| `phase3_groups.md` | Same observation; wording says "288 in the 342 cells" | Type census not corrected |
| Plan 28 `per_rule_phase2_reconciliation.md` | Observation retained; rule rows O01 340 + O05 2 (246, 567). Notes member TSV is **341 type-288 + 1 type-321 (246)** | Wording discrepancy recorded, not closed |
| `2-01_…_members.tsv` (342 rows) | Every row: `encoder_drops_clipped_source_sliver`, spool branch `b`, `G_polygon_count=0`, R cell-local present | Proves G omits and spool clip collapses; does not ask whether OSM can supply a different encodable source, or prove that R's geometry is WhereIS-only |
| OVERVIEW | "carried completeness source-data parity / spool successor items remain" | Still open |

**Ground (read-only, tip `5ff9eb0` + host scratch-14 proofs, 2026-10-06 ~06:05 AEST):**

1. **Type census.** Membership is **341 × code 288** and **1 × code 321** (dump_row 246, cell `(834,886)`). The historical "288 in the 342 cells" sentence is false as written.
2. **Type-288 cohort is one template.** All 341 R polygons have exactly 13 vertices and span exactly **0.083333° × 0.125°** (5′ × 7.5′). There are exactly **two** local shape signatures (opposite winding / start corner), counts 191 and 150. Meet branch is **c** (cell centre) for all 341. They sit in bands around the Australian coverage, including far-west (lon &lt; 113), far-east (lon &gt; 153.5), and southern latitudes (e.g. −36.75) that are offshore of the mainland. This is a tiled WhereIS background lattice, not an OSM building/admin footprint.
3. **Type-321 outlier.** Row 246: 11 R polygons (10–58 coords), meet branch **a**, centre ≈ (−31.58, 116.11) near Perth vegetation. Mechanism still `encoder_drops_clipped_source_sliver` on a 58-coord spool source.
4. **Spool demanders are not the R tiles.** For every 2-01 row the K1 demander is a nearby spool ring whose clip into the target cell yields `area2=0` (q 2 or 3). The R 13-vertex tile is a different geometry. Proving "spool demander unrepresentable" does not prove "no OSM source of the demanded type could ever emit in this cell."
5. **Disc in force.** Successor `2ee3456a…` (plan 29) differs from historical `4ed9cd80…` only in L0 `(0,541)` leaf 928 names. Background omission in the 342 cells is unchanged by that diff; Phase 1 re-checks a sample on the successor anyway.
6. **Vocab context.** Type 288 is the L0 catch-all (buildings, admin, campus, unmatched). Type 321 is wood/grass/park. Type 289 is water/coast. A maritime lattice encoded as 288 on R may have no honest OSM→288 path; mapping it as 289 would be a different deviation (type mismatch), not a silent fix.

The ticket is **not** already satisfied. Completeness-pass ≠ DVD parity. The observation names a cause class ("source data") without a per-row proof that the source is unrecoverable from OSM, and without a supply counterfactual where one exists.

## Solution shape

Treat the 342 rows as a **DVD presence parity** set. For each row, either (a) prove a supply path from OSM inputs that yields an encodable cell-local piece of the demanded type under the production encoder, without copying R geometry, or (b) prove the deviation unfixable with a named root cause. Disposition is per row (or per proven stratum that shares one root cause with an exhaustive member list). No inventing of WhereIS tiles into G.

### Domain: R / G / spool / OSM fingerprint census

- **Owns:** a committed per-row fingerprint table and the corrected type census; the type-288 template proof; separation of the type-321 outlier.
- **Contract:**
  1. 342 rows, full native key, join to `phase3_membership.tsv` / `2-01_…_members.tsv` / plan-28 join (rule id).
  2. Per row: R polygon count, R vertex count(s), R bbox, R meet branch(es), R shape signature id (for 288: one of the two templates or `other`); G presence of the demanded type on the **disc in force** (`2ee3456a…`, with `4ed9cd80…` as historical control); spool demander identity and clip/emit result (cite existing proof paths; do not re-derive 2-01 science).
  3. The type census is stated as **341 × 288 + 1 × 321**. Historical "288 in the 342" wording is corrected in OVERVIEW / plan-14 follow-up pointer / reconciliation note — append-only, no rewrite of closed Phase 1 TSVs.
  4. Type-288 template identity is proven: all 341 share the 5′×7.5′ span and one of the two recorded local signatures; any exception is listed.
  5. Geographic bands (west / east / south-offshore / other) are recorded as descriptive strata inputs for Phase 2, not as dispositions.
  6. Heavy reads (disc, spool) go through `run_heavy_python.py` (takes `output/.heavy.lock`), windowed/streamed; no whole-file `ALLDATA.KWI` or spool loads. Prefer light reuse of `output/scratch-14/cell_local/proofs/` and witnesses where hashes still match.
- **Non-goals:** no disposition in this domain; no encoder/checker/vocab change; no inventing geometry; no re-running plan-14 group science; no plan 29 close-out surfaces.

### Domain: supply vs unfixable disposition

- **Owns:** a verdict for every one of the 342 rows, and the evidence that settles it.
- **Contract:**
  1. Verdict ∈ {`supply-path`, `unfixable-proven`, `conflict-open`}. Target is **0 conflict-open**; any remainder is named with discriminators tried.
  2. **`supply-path`:** a bounded counterfactual shows that some OSM-derived source (existing spool record, or a named extract/vocab/selection change that does not copy R coordinates) produces ≥1 production-C record of the **demanded type** in the target cell. Evidence: source identity, encode probe result, and how it relates to R's presence (presence match only — vertex-for-vertex equality with R is not required for this verdict). The path is recorded for a successor implement unit; this plan does **not** require a full-AU re-encode as acceptance.
  3. **`unfixable-proven`:** every honest supply discriminator fails, and a named root cause holds. Allowed cause classes (must be evidenced, not labelled):
     - **WhereIS-only lattice:** R's polygon matches the proven 5′×7.5′ template cohort; no OSM polygon of any background type in a stated search window would emit the demanded type in-cell under production C; inventing the tile (copying R or synthesising the lattice) is the only way to match presence — forbidden under full regeneration from OSM.
     - **Type-semantic mismatch:** OSM can supply a representable footprint in-cell only under a **different** background code than R's (e.g. water→289 vs R's 288). Matching presence at R's code would require a false vocab mapping. Recorded as unfixable-at-code with the alternate-type observation named, not absorbed as "fixed."
     - **Representability ceiling:** OSM geometry of the correct type exists but every repair that stays within the wire contract (clip/densify/round; no coordinate invention) still emits 0 in-cell — with the probes listed.
  4. Type-288 rows may share one stratum disposition **only if** the template proof plus a uniform discriminator result cover every member; members that fail the uniform test are split out.
  5. Type-321 row 246 is disposed on its own evidence (not folded into the 288 lattice story).
  6. Spool successor items (the seven O04 rows from plan 28) stay out of this set; they are not 2-01 members.
  7. Never relabel a `supply-path` row as natural deviation, or an `unfixable-proven` row as a build bug, without the matching evidence.
  8. OVERVIEW's carried "source-data parity" bullet is narrowed to the residual after dispositions (counts per verdict; link to the TSV).
- **Non-goals:**
  - no copying R polygons into the spool or disc;
  - no full tip re-extract as the default route;
  - no 3-90 re-run; no plan 04 Phase 3 close claim;
  - no plan 04 phases 4–6 or plan 06;
  - 170 / 3-16 / 3-17 not reseated;
  - plan 29 close-out and OVERVIEW path fix for plan 29 are owned by Execute — not this plan.

## Decisions

1. Plan number **30**. Master occupies 01–05 and 07–29 (06 is not a work unit). Land on master directly. No feature branch. No pull request.
2. Two phases. Phase 1 approach **known**. Phase 2 approach **open** on the discriminator set (divergent candidates scored against the fixed disposition outcome); no separate refine document. One worker may carry both sequentially.
3. **Why this unit over Phase 3 / other residuals (Quality Assessor 2026-10-06):** CHM heavy hold is fully cleared, so plan 04 Phase 3 remainder (PSS at ≤`-j6`, other-kind classify joins, 3-11 vs 3-14 oracle, `pinned_candidates` set-equality) is drawable. Those gates unlock Phase 3 close and are ranked next. They do not remove the standing-rule DVD gap that G still omits R's cell-local type in 342 cells while K1 exits 0. Plan 29 close-out is skipped (Execute). Among carried residuals, 2-01 is the largest proven G≠R presence set with unfinished root-cause proof.
4. Presence parity, not geometry clone: a supply path that emits the demanded type in-cell is enough for `supply-path`; matching R's 13-vertex tile vertex-wise is out of scope.
5. Inventing WhereIS lattice tiles is forbidden. If that is the only way to match R, the verdict is `unfixable-proven` with that root cause — which **satisfies** the standing rule for those rows.
6. Disc in force for G checks: successor `2ee3456a…`. Historical `4ed9cd80…` may be cited as control. R pin remains `8c2d2027…`.
7. Heavy work only under `run_heavy_python.py` + `output/.heavy.lock`, bounded/streamed (plan 25). Prefer light paths from committed TSVs and retained scratch-14 proofs.
8. Do not reseat 170, 3-16, 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not claim plan 04 Phase 3 closed. No 3-90 re-run.

## Assumption ledger

### Assumption 1

- **Question:** Is "source data" already a closed root cause for all 342?
- **Answer chosen:** No. Plan 14/28 carried an observation. Completeness disposition (checker) is closed; DVD presence parity is not. This plan supplies per-row proof.
- **Rationale:** Standing rule; never relabel.
- **If wrong:** Cody treats the observation as already final. Phase 2 collapses to a documentation census only; Phase 1 still corrects the type wording.

### Assumption 2

- **Question:** May the type-288 5′×7.5′ template cohort take a single stratum disposition?
- **Answer chosen:** Yes, when Phase 1 proves template identity and Phase 2's uniform discriminators hold for every member. Any exception is split to its own verdict.
- **Rationale:** Ground shows 341/341 identical span and 2 signatures only.
- **If wrong:** Every row is disposed individually; outcome unchanged, more wall clock.

### Assumption 3

- **Question:** Does `supply-path` require landing extract/vocab/encode changes in this plan?
- **Answer chosen:** No. A bounded production-C counterfactual plus a named successor implement path is enough. Landing a full-AU supply is a follow-on unless Execute finds a trivial tracked fix that fits the phase outcome without a re-oracle scope fight.
- **Rationale:** Keep this unit at disposition altitude; avoid conflating with Phase 3 / re-oracle.
- **If wrong:** Cody wants presence fixed on the disc in force here. Add an optional Phase 3 only for rows already `supply-path`, with successor-oracle rules matching plan 29.

### Assumption 4

- **Question:** Is matching R at type 289 (or another code) an acceptable supply for an R-288 cell?
- **Answer chosen:** No for verdict `supply-path`. That is `unfixable-proven` under type-semantic mismatch (or `conflict-open` if undecided), with the alternate-type observation recorded.
- **Rationale:** DVD parity is type-specific in the 2-01 membership key `(cell, type)`.
- **If wrong:** Cody accepts presence-at-any-background-type. Verdict labels change; membership science does not.

### Assumption 5

- **Question:** Does disposing 2-01 close plan 04 Phase 3?
- **Answer chosen:** No. Phase 3 remaining work (PSS, other-kind joins, 3-11 vs 3-14, pinned_candidates) stays separate; listed in NEXT-CANDIDATES.
- **Rationale:** OVERVIEW blockers; Quality Assessor list.
- **If wrong:** A later design's outcome is exactly Phase 3 close with evidence.

## Open questions

1. Search window and OSM surfaces for the supply discriminator (spool-only vs windowed PBF tag query). **Execute chooses** under Phase 2's open approach; must be bounded and logged.
2. Whether a trivial tracked vocab/selection fix for row 246 (type 321) lands here or as a one-row follow-on once `supply-path` is proven.
3. Exact OVERVIEW sentence form after disposition counts exist (Execute drafts; must not claim Phase 3 closed).

## Phases

### Phase 1: Every 2-01 row is fingerprinted; type census and 288-template identity are proven

- **Outcome:**
  1. A committed 342-row fingerprint TSV (full native key, dump_row, code, rule_id from plan-28 join, R counts/branches/vertex counts/bbox/shape-signature id, G demanded-type count on successor `2ee3456a…` and on historical `4ed9cd80…`, spool demander proof reference, clip/emit summary).
  2. Stated census: **341 × 288 + 1 × 321 (246)**. Append-only corrections land where the false "288 in the 342" wording still appears (OVERVIEW / plan-14 follow-up pointer / plan-28 reconciliation note as needed). Closed plan-14 member TSVs are not rewritten.
  3. Type-288 template proof: 341/341 share span 0.083333° × 0.125° and one of two recorded local signatures (counts stated); exceptions listed or count 0.
  4. Geographic band labels recorded per row (descriptive only).
  5. Heavy steps only via `run_heavy_python.py` + lock; argv and `memory.peak` under plan scratch.
  6. Not done: no disposition verdicts; no encoder/checker/vocab edits; no 3-90; no Phase 3 close; plan 29 close-out untouched.
- **Surfaces:**
  - new `docs/plans/30-2-01-source-data-parity/` (fingerprint TSV, note);
  - append-only wording fixes (`docs/OVERVIEW.md`, plan-14 record follow-up line, and/or plan-28 reconciliation carried item);
  - read-only: plan-14/28 triage TSVs, `output/scratch-14/cell_local/proofs/`, witnesses, discs `2ee3456a…` / `4ed9cd80…` / R, spool.
- **Approach:** known.
- **Depends on:** master at or after `5ff9eb0`; retained scratch-14 proofs (or regeneration under pin if absent).
- **Refine:** skipped.

### Phase 2: Every 2-01 row has a supply-path or unfixable-proven disposition

- **Outcome:**
  1. A committed 342-row disposition TSV: fingerprint key, verdict, cause class, discriminator records, proof paths. Counts: `supply-path` / `unfixable-proven` / `conflict-open`.
  2. Type-288 stratum: either one evidenced uniform disposition covering all template members, or an explicit split list.
  3. Type-321 row 246 disposed on its own evidence.
  4. Every `supply-path` row names a bounded production-C counterfactual and a successor implement path (no R-copy).
  5. Every `unfixable-proven` row names a root cause in the allowed classes with negative supply evidence.
  6. `conflict-open` is 0, or each open row lists discriminators tried.
  7. OVERVIEW carried source-data-parity bullet narrowed to residual counts and the disposition TSV link. Seven O04 spool rows and plan 04 Phase 3 blockers remain listed elsewhere as appropriate.
  8. Not done: no 3-90; no plan 04 Phase 3 close; no phases 4–6 or plan 06; 170 / 3-16 / 3-17 not reseated; no plan 29 close-out work.
- **Surfaces:**
  - plan-30 folder (disposition TSV, reconciliation note, optional probe scripts under plan folder or `parser/tools/`);
  - `docs/OVERVIEW.md` residual wording;
  - optional windowed probes via `run_heavy_python.py`;
  - read-only: Phase 1 TSV, spool, discs, vocab (`parser/refdata/vocab/bg_type.json`), selection.
- **Approach:** open (discriminator candidates scored against this outcome).
- **Depends on:** Phase 1.
- **Refine:** skipped (short candidate comparison recorded in the plan record only).

## Provenance

- Ground tip: `origin/master` `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7` ("plan 28 close-out: record, per_rule_ evidence in plan 04 triage, contract promoted"). Box checkout `/workspace/open-pajero-maps` fast-forwarded from `0dc5cac`.
- Plan 28 closed out; plan 29 Phase 2 closed with close-out pending (Execute owns; skipped here). Successor oracle in force: `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.
- Evidence cited (committed): plan 14 record follow-ups; plan 28 record + `per_rule_phase2_reconciliation.md`; `phase3_groups.md`; `2-01_…_members.tsv`; `docs/design/k1-completeness.md`; `docs/design/osm-vocabulary-mapping.md`; OVERVIEW WP1 / unfinished rows; plan 25 memory guards; plan 29 IMPLEMENTATION carried structural residuals (out of scope here).
- Read-only host Ground on `codyh-ubuntu` (`open-pajero-maps-14-completeness` scratch-14 proofs/witnesses): type census 341+1; 288 template span and two signatures; sample R/G/requirement witnesses; geographic band sketch. No K1 / encode / classify run for this design.
- Quality Assessor (2026-10-06): CHM heavy hold fully cleared; Phase 3 remainder drawable; plan 29 close-out skip; carried residuals listed. Weighed in Decisions §3 and NEXT-CANDIDATES.
- Rejected for this design: inventing R tiles into G; absorbing 2-01 into checker non-deviation; folding O04 spool rows into 2-01; claiming Phase 3 closed; 3-90 re-run; plan 04 P4–6 / plan 06; reseating 170 / 3-16 / 3-17; doing plan 29 close-out.
- Draft format followed: `/workspace/maps-design-drafts/28-phase1-per-rule-classify-recovery/DESIGN.md`.
- Design method: workflow design skill (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger).
- Adversarial pass ran in-context (disclosed): applied findings — (1) completeness-pass ≠ DVD parity; (2) spool demander ≠ R tile, so "unrepresentable demander" is not "unfixable source"; (3) type-321 must not ride the 288 lattice story; (4) wrong-code OSM supply is not `supply-path`.
- Workflow-service posts and `artifact_feedback` skipped under user instruction. Box draft only: no commit or push.
