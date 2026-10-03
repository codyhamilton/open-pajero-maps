---
brief_id:
design_id:
---

# Brief: 3-17 — Re-baseline the 9,064 unattributed ledger

Consumer: Maps Execute.
Base: `ced98f8272fc1e4a34ba0d34b0dbbb1535c5f205`.
Owned paths: this brief, landed at `docs/plans/04-c-core-orchestration/briefs/3-17-9064-rebaseline.md`, `docs/plans/04-c-core-orchestration/triage/rebaseline_3-17_9064.md` (new), the `note` string of rule `R01` in `docs/plans/04-c-core-orchestration/triage/rules_bg.json` (append only), a 3-17 heading appended to `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md`, a scratch entry in `docs/provenance.md`, and `output/scratch-3-17/` (git-ignored). Touch nothing else.
Commits: the owned doc paths when the done evidence below passes, and land them on master. Never stage discs, dumps, or `output/`. Do not open a pull request.
Depends on: 3-16 landed (`e97c968` is an ancestor; do not reseat it) and design 170 `PHASE.md` already on this base (do not reseat it). The disc in force is the post-3-14 AU image. `triage/completeness_3-16_window_cf.md` records it as sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` (stored 3-14 AU disc SHA). `IMPLEMENTATION.md` records the same re-oracle as `013586b5…` → `4ed9cd80…`.
Runs alongside: nothing. One unit. Do not open 3-18. Heavy work, if any, under `flock output/.heavy.lock`; cbuild/make ≤ `-j4`; K1 ≤ `-j6`; no cache drops. **No full-AU encode.**
A code fix is out of scope even if classify reports `build`.
Budget: ≤ 40 tool turns. Past the budget, append a 3-17 handoff to `IMPLEMENTATION.md` (done, not done, what you learned) and report `over budget`. Do not start another unit.

One unit, not a kickoff/verify split. Unit 3-12 produced this ledger in one classify-and-record unit (`triage/causes_residual.md`, native classify `PARTITION FAIL`). Unit 3-13 touched the same ledger in one unit and left it unchanged. Recorded `k1_triage.py classify` wall is 40 s (unit 3-05). Recorded full-disc dump-on walls are 115.7 s (3-02), 189.5 s (3-11), and 221.8 s (3-03). All are under ten minutes, and the done evidence is a re-classify of the disc already in force, not an encode. That is the same shape as 3-12's classify step, not 3-16's 1,213.8 s window encodes.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Phase 3 outcome, the failure-list sentence quoted under Contract. Do not read Phases 4–6 to act on them.
2. `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` — the 3-14, 3-15, and 3-16 unit records only (9,064, PARTITION FAIL, R01).
3. `docs/plans/04-c-core-orchestration/briefs/3-14-bg-shape-eo-stitch.md`, `briefs/3-15-completeness-cell-local.md`, `briefs/3-16-completeness-89-window-cf.md` — the sentences quoted under Cited facts.
4. `docs/plans/04-c-core-orchestration/triage/review_3-13.md` finding 3 and the 9,064 paragraph; `triage/causes_rootcause.md` opening status and the "Classification and honest remainder" table.
5. `docs/plans/04-c-core-orchestration/triage/rules_bg.json` — rule `R01` `note` (the checker-facing note). `rules_other.json` has no R01.
6. `docs/plans/07-g-new-nonpayload/DESIGN.md` Decisions 1–2 and the Phase 1 non-goal; `PHASE.md` "Verification and deviations". Do not edit that plan.

Read those ranges. Do not re-derive the 9,064 composition, the 776 arithmetic, or the 89 tally.

## Cited facts (do not re-derive)

- Phase 3 is open. `IMPLEMENTATION.md` ends the 3-16 record with "Phase 3 remains open; Execute owns landing." This unit does not close it.
- `review_3-13.md`: "Unattributed 137 + 8,739 + 188 = 9,064." `causes_rootcause.md`: "Remainder **9064** and PARTITION FAIL persist unchanged (recorded limitation D in that file)." The same file's remainder table is background 137, background_boundary 8,739, completeness 188. Those rows were left unattributed on purpose: `review_3-13.md` says "The 9,064 unattributed rows are correctly left alone."
- That ledger is pre-3-14. `briefs/3-15-completeness-cell-local.md`: "**9,064** unattributed + PARTITION FAIL is a **pre-3-14** classify ledger; re-baseline on 3-14 disc is a side deliverable here only if cheap (empty-dump tooling), else defer to backlog." `triage/completeness_3-15_cell_local.md`: "The 9,064 unattributed + PARTITION FAIL is not claimed live without re-classify."
- Unit 3-14 on the new disc, quoted from `IMPLEMENTATION.md`: "S02–S05 build-target rows: **17,058,955 → 0**"; "R01 checker background: **920,786 → 0**"; "R01 cause stays checker with the 3-13 caveat; not reclassified here"; "9,064 unattributed / PARTITION FAIL from 3-12 stays open"; "Classify CLI still aborts on empty residual dump (`k1_triage._memmap`)". Kind failing on `k1_full.json`: background 0, background_boundary 0, interior_cover 0, name_anchor 1, completeness 776. An empty-dump abort is not `PARTITION OK` and is not proof the 9,064 rows are gone.
- Unit 3-15 completeness recount, not to be recomputed: "**776 = O01 363 + O05 132 + O04 7 + unattributed 274**". "No checker/encoder fix is proposed." O07 was not registered.
- Unit 3-16, quoted from `triage/completeness_3-16_window_cf.md`: "**Status: done. Gate (b): 0 pass / 89 fail / 0 untested.**" "Disposition: **accept-with-honesty for all 89 tested keys**." "No pass is strong enough to justify a later C amendment." "No rule or ledger reclassification is implied." `IMPLEMENTATION.md`: "No protected oracle overwritten, no O07, no historic cause or 9,064-row ledger reopened."
- R01 exclusivity is already written in the 3-13 report and is **not** in the live rule note. `review_3-13.md` finding 3: "R01 is not shown to be exclusive of the build defect." "Condition: add an explicit caveat to R01 or the report that R01 may partly overlap the build defect, and that this was not tested beyond this window." `causes_rootcause.md`: "**R01 exclusivity vs build is unproven** (L0/291 window: 31 type-291 `in_eo_same=1` fills vanish after repair and may overlap build; not tested beyond that window)." `rules_bg.json` R01 `cause` is `checker` and its `note` still ends at the G_new row count. `rules_other.json` has no R01 entry.
- Design 170 `PHASE.md` already names the +60 bytes: "Map Frame allocation padding". "No schema edit is needed." "No encode, disc copy/write, checker change or build-sha edit occurred."

## Goal

On the oracle disc already in force, re-classify the stale 9,064 unattributed / `PARTITION FAIL` ledger and record whether those rows are still live. On that same record, append the R01 exclusivity caveat to the live R01 note. No other change.

## Contract

Cited, not restated. From `docs/plans/04-c-core-orchestration/DESIGN.md` Phase 3 outcome:

> On the oracle disc in force at phase close, the checker reports build-caused and checker-caused failures of 0 in every kind, and the failures that remain are exactly the enumerated spool-caused list (item identity, not only counts), carried to the successor design.

Also cited from that same outcome, not as this unit's exit: "background, background_boundary, interior_cover and completeness reach 0 unless a pinned spool-caused item remains."

This unit does not close Phase 3, does not write that enumerated list, and does not treat a failing count of 0 as that list. It records, per kind, whether the historic 9,064 rows are still failing and still unattributed on the disc in force, at item identity where the old keys are still on disk, and as "identity not recoverable" where they are not. Rows that stay unattributed stay unattributed. Do not name a new cause for them.

From `docs/plans/07-g-new-nonpayload/DESIGN.md` Decisions:

> 1. This is the item after 3-16. The 9,064 re-baseline and the R01 exclusivity note wait behind it.
> 2. One phase. The outcome is attribute-or-accept. A code fix is a later amendment, not a second phase guessed now.

That plan's own non-goal still holds for its folder: "Completeness, the 9,064 re-baseline, and R01 exclusivity stay outside this plan." Do the work in plan 04. Do not edit plan 07.

Settled: R01 stays `cause: checker`. The caveat is a note. A `build` row found by this re-classify is reported, not fixed.

## Non-goals

- No code change. No encoder, checker, rule predicate, tolerance, or disc-byte change. No C amendment for the 89 (0 pass / 89 fail, accept-with-honesty). No Map Frame padding change. No schema edit. Do not register O07.
- Do not close Phase 3. Do not brief or run 3-90. Do not draw plan 04 phases 4, 5, or 6. Do not touch the unsigned 06 CI-gate draft. Do not reseat or re-sign 3-16 or design 170.
- Do not edit S02–S05 or O01–O06 `id`, `cause`, `where`, or order. Do not reopen the 188 representability test, the 89 keys, name_anchor, L8 TRIM, or polygon 65623.
- If classify assigns any of the re-baseline rows `cause: build`, or any other build-caused defect turns up: **stop and report**. Do not fix it, do not edit `_cenc.c` / `_k1.c`, do not add a rule.

## Pre-edit checks (any fail → `blocked`)

C1. `git rev-parse HEAD` is `ced98f8272fc1e4a34ba0d34b0dbbb1535c5f205` or a descendant that still contains `e97c968` and `docs/plans/07-g-new-nonpayload/PHASE.md`. No `briefs/3-17*.md` exists on the base. There is no 3-17 brief at this SHA (confirmed before this brief was written).
C2. `sha256sum` of the on-disk post-3-14 AU `ALLDATA.KWI` equals `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`. If the file is absent, **blocked**. Do not encode or copy a replacement. Do not open `output/scratch-3-11/G_new` as a substitute (that image is `013586b5…`, the pre-3-14 ledger disc).
C3. Quote once, without recomputing: 9,064 = 137 + 8,739 + 188; 3-14 kind failing background 0, background_boundary 0, interior_cover 0, completeness 776, name_anchor 1; 776 = 363 + 132 + 7 + 274; 3-16 is 0 pass / 89 fail / 0 untested.
C4. `rules_bg.json` R01 `cause` is `checker` and `rules_other.json` has no R01. Read the current R01 `note` before appending.

## Steps

1. Locate the post-3-14 failure dump that was written against the sha in C2 (`output/scratch-3-14/` is read-only). Write every new classify artifact under `output/scratch-3-17/` only. Never overwrite `output/scratch-3-11/`, `scratch-3-12/`, `scratch-3-13/`, `scratch-3-14/`, `scratch-3-15/`, or `scratch-3-16/`.
2. Re-classify with the existing `parser/tools/k1_triage.py` classify entry, using `rules_bg.json` and `rules_other.json` **before** the R01 note append (the note text does not change predicates). If a kind's dump is empty and classify aborts on `k1_triage._memmap`, save the stderr. That abort is not `PARTITION OK`. For an empty kind, quote the `k1_full.json` failing count separately and say classify did not partition that kind.
3. If no dump for the C2 disc exists, one dump-on K1 against that existing file is allowed under the lock. Recorded dump-on walls are under ten minutes. If that run is still going at ten minutes, stop, write the handoff, and report `over budget`. Do not encode. Do not open a follow-on unit.
4. Write `triage/rebaseline_3-17_9064.md`. For background 137, background_boundary 8,739, and completeness 188, state one of: still failing and still unattributed (count, and item identity if the old keys are still on disk); not in the failing set (cite the kind's failing count and the classify output or the empty-dump abort); or identity not recoverable. Do not reconstruct missing keys and call them the same rows. Do not invent a cause for rows that stay unattributed. Record the sentence "these rows stay unattributed."
5. Append to the R01 `note` in `rules_bg.json` only, after the existing sentence, this caveat and nothing else: "R01 exclusivity vs the build defect is unproven (review_3-13 finding 3; causes_rootcause.md): in the L0/291 window, 31 type-291 in_eo_same=1 fills vanish after repair and may overlap build; not tested beyond that window. Unit 3-14 saw R01 checker background 920,786 → 0 and did not reclassify the cause. Note only." Do not change `id`, `cause`, `where`, or any other rule.
6. If step 2 shows a build-caused defect, write that finding into the 3-17 note with the row counts and the artifact path, then stop. Do not fix it. The R01 note append in step 5 is still required; it is not a fix.
7. Append the 3-17 record to `IMPLEMENTATION.md`: C1–C4, the live/not-live table, the classify or abort path, the R01 note diff, deviations. No `Workflow-Phase` trailer. Do not write "Phase 3 closed".

## Keep untouched

- `rules_bg.json` except the appended R01 `note` text. `cause` stays `checker` because 3-14 left it checker and this unit is the caveat, not a reclassification.
- `rules_other.json`, every S02–S05 predicate, `_cenc.c`, `_k1.c`, `docs/schema/`, plan 07, the 3-16 packet, and the unsigned 06 draft.
- The historic 9,064 numbers in `causes_rootcause.md`. The new file cites them. It does not rewrite them.

## Done evidence

- `sha256sum` of the disc equals `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`, saved under `output/scratch-3-17/`.
- Classify stdout, or the empty-dump abort stderr, is saved there. The 3-17 note quotes it and states, per the three historic buckets (137 / 8,739 / 188), still-live-unattributed, not in the failing set, or identity not recoverable. Unattributed rows are still labelled unattributed.
- `git diff -- docs/plans/04-c-core-orchestration/triage/rules_bg.json` changes only the R01 `note` string. A one-line check prints R01 `cause` still `checker` and the `where` clause still `in_eo_same == 1`.
- `git diff --stat` shows no path under `parser/`, no `docs/schema/`, no `docs/plans/07-g-new-nonpayload/`, no `briefs/3-90-fresh-verify.md`, and no 3-16 file.
- If a build-caused defect was found: the note names it and the worktree has no encoder, checker, rule-predicate, or disc diff. Status for that path is `blocked`, not `done`.

## Report back

Under 400 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then the three bucket outcomes, whether classify aborted on an empty dump, whether any build-caused row appeared (and that you did not fix it), and the R01 note confirmation. Any contradiction between this brief and the Phase 3 outcome sentence: report it. Never resolve a contradiction silently. Do not start another unit. Do not close Phase 3.
