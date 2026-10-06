Verdict: PASS_WITH_FOLLOWUPS

# Plan 30 terminal review: reopened Phase 2 increment (828667c..873f161)

Seat: Claude CLI, clean context (disclosed; Codex weekly-limited). Scope: only the reopened increment (828667c, 537da1e, f1a1368, 7913160, 4c07832, 59aeafd, 115d720, bf46547, 617c7c8, 873f161), checked against DESIGN Phase 2 outcome + Amendment 1. Base `master` 7909964.

Read from `HEAD` via `git show`/`git archive`, because the worktree had another session's **uncommitted, staged** close-out move (plan 30 folder → `docs/plans/04-c-core-orchestration/triage/source_parity/`, plus edits to tests/provenance). I did not touch it.

Tests were run on a `git archive HEAD` export (`output/scratch-30/review-close/head_src`): `test_parity_disposition.py` + `test_parity_fingerprint.py` → **75 passed**.

## Verified

- **Counts.** `disposition.tsv` has 342 rows: 341 supply-path / 0 unfixable-proven / 1 conflict-open. `disposition_summary.json` `counts` matches; `status: incomplete`.
- **Rows 396/397/775:** supply-path. Source is r2647638 (EEZ), `geometry_ways {cache:131, snapshot:16}`, `tags_members: pbf-cache`, boundary-clipped. Positive production-C records of code 288 (20 / 20 / 218 B), with coords sha recorded.
- **Row 246:** conflict-open, `outlier/stratum evidence insufficient`.
  - PBF and spool `blocking_gaps` are empty.
  - 284 code-321 candidates; emitters are 288×11 and 291×1 only.
  - The retained demander (source cell 0,834,885) touches the edge at vertex 18, `area2: 0`, `emits: False`.
  - `unresolved` is stated. It is **not** labelled unfixable-proven.
- **Amendment 1 conditions:**
  - §1 root cause before use: q1 attic response 10:57; proof committed 59aeafd 10:59; first snapshot use 11:42 (run_p2d, HEAD bf46547). Met.
  - §2 pin before use: pin + provenance committed 115d720 11:03. I re-hashed the snapshot: `39a836dd…` matches. Raw b1–b3 shas are recorded; the batch-3 504 retry is in `fetch.log`. Met.
  - §2 scope: nothing enters the spool, encoder, vocab, selection or disc (diffs touch only plan-30 files, tests, provenance and OVERVIEW). Scope drift: see F3.
  - §3 read-only originals: the snapshot (`r--r--r--`) has the same sha before and after in `run_p2e.log`. The cache is opened `mode=ro` and its digest re-verified against `cache_pin.json` (`verify_cache_provenance`). PBF sha is checked via provenance. Met.
  - §3 guarded heavy steps: every step goes through `run_heavy_python.py` under `output/.heavy.lock`, serially, all exit 0; peak 957 MB, 166.8 s. Met.
  - §4 verdict rule: supply-path only with a positive C witness. Row 246 is kept open because a demanded-type feature reaches the cell. Option (b) is not used. Met.
- **Code (`disposition.py` at HEAD, sha `32121392…` = summary `inputs_sha256`):**
  - The snapshot is verified before any use: sha, schema, request set, member schema.
  - Cache-first per way. Shared-node coordinate equality is checked against both cache ways and the node table.
  - A member mismatch becomes a gap and falls back to the legacy path.
  - Only the 61 relations plus area-role children are eligible.
  - The pinned-first `Accumulator` preference is correct, and the 338 earlier rows are unchanged per the report.
  - `RELATION_CAPS` covers r4095122 only, with topology still validated.
  - The antimeridian 0–360 shift applies only when no edge spans more than 180° in the shifted frame, otherwise the gap stands. Correct for 112–155 E cells.
  - Tests cover each of these.

## Findings

1. **Medium: the Design ruling for row 246 (12:45 AEST) is not recorded anywhere at HEAD; the docs still say "pending".**
   - Evidence:
     - `docs/OVERVIEW.md` says "1 conflict-open (dump_row 246, Design ruling needed)".
     - `open_rows_account.md` says "Owner: Design".
     - IMPLEMENTATION 2-03 says "Phase 2's outcome (0 conflict-open) is **not met**".
     - No plan 38 exists (`docs/plans` has only 36 and 37).
   - DESIGN Phase 2 outcome item 6 reads "`conflict-open` is 0, **or each open row lists discriminators tried**". Row 246's `discriminator_records` (lattice-identity, spool, pbf, retained-demander, unresolved) satisfies that, so the phase closes on item 6. The "not met" wording misreads it.
   - Fix (in the close-out commit):
     - Record the ruling verbatim in the plan record, or as DESIGN Amendment 2: row 246 is not unfixable-proven; it is carried as a named residual; the candidate cause is **UNPROVEN** (R's in-cell 321 record may come from the edge-touching relation under a different clip-inclusion rule; R keeps boundary-touching/degenerate clips, our encoder drops them); owner plan 38.
     - Correct "not met" to "met via item 6, with 1 residual carried".
     - Change the OVERVIEW wording to "1 carried residual (dump_row 246) → plan 38".
     - Point plan 38 (or its OVERVIEW stub) at row 246's discriminator record.

2. **Medium: the snapshot dependency of rows 396/397/775 is missing from their successor fields.**
   - Evidence: in the TSV, `successor_implement_path` reads "assemble the identified OSM relation from member node IDs…", and `production_C_counterfactual.source.input` is `australia-260824.osm.pbf`. Yet 16 of the 147 ways come only from the snapshot, which `geometry_ways` shows.
   - A successor implementing from the pinned PBF cannot reproduce these witnesses.
   - `phase2_snapshot.md` and the report already say this, but the per-row record (the hand-off contract, outcome item 4) does not.
   - Fix (either):
     - (a) In `successor()`, when `snapshot_backed(source)`, append "; requires the complete relation (16 member ways outside the pinned extract: date-matched snapshot `39a836dd…` or an equivalent build input; Design input decision)". Re-run `publish` under the guard (0.5 s).
     - (b) If no re-publish, state it in the close record and the plan 38/successor hand-off, naming the 3 rows.

3. **Low: snapshot use is wider than Amendment 1 §2 says.**
   - §2 limits use to "member-way (and member-node) geometry for those 61 relations". Brief 2-03 widened it: relation tags and members for the 5 never-retained relations (4095122, 15480206, 16308779, 16308787, 16308826) and the area-role children as eligible sources.
   - `docs/provenance.md` "Use:" still says geometry only.
   - No verdict depends on the wider use:
     - The 338 earlier rows are pinned-first and unchanged.
     - 396/397/775 take tags/members from the pinned cache.
     - r4095122 only emits 288 at row 246.
   - Fix: correct the provenance "Use:" line to say this, and note in the close record that the widening is a brief-level extension with no verdict depending on it.

4. **Low: row 396's PBF `blocking_gaps` has a misleading `resolution`.**
   - It lists the r16623818 "crossing/touching relation boundaries" gap with `resolution: "date-matched snapshot geometry (plan 30 unit 2-03)"`. The snapshot does not resolve a crossing; this is the generic snapshot `details` string being reused.
   - The gap is non-blocking because the positive covers it.
   - Fix: a record-only note in the close record. Optionally, don't attach the snapshot `details` to crossing gaps in `assemble_snapshot`.

5. **Info: the root-cause proof polygon is not date-matched.** It uses Geofabrik's current `australia.poly`, fetched 2026-10-06. The conclusion stands: the bbox equals the PBF header, and 3,386 of 3,619 ways are wholly outside the header bbox. No fix needed.

6. **Info: the in-flight close-out moves files.** Its staged move changes the path the tests import. Re-run the two test files after the move, before committing (75 passed at HEAD).

## Is closing at 341 / 0 / 1-carried honest?

**Yes, provided F1 and F2 are fixed in the close-out.**

- The 341 supply-path rows each carry a positive production-C witness.
- 0 unfixable-proven is correct: nothing was promoted by option (b).
- Row 246 is held open on the right grounds: a demanded-type feature reaches the cell, so absence is unprovable under Amendment 1 §4. Its discriminators are listed, which is outcome item 6.
- Calling the edge-touching or degenerate-clip explanation proven would be dishonest. The committed artefacts do not do that: the `mechanism` label describes why our encoder drops the spool demander, and `unresolved` is explicit.
- The close record must keep "candidate cause UNPROVEN" and the plan 38 owner.
