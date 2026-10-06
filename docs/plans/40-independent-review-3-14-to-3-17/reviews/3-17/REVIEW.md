# Independent review — unit 3-17 (historic 9,064 unattributed ledger re-baseline)

- **Unit:** plan 04 unit 3-17. Brief `briefs/3-17-9064-rebaseline.md`; records `triage/rebaseline_3-17_9064.md` and `IMPLEMENTATION.md` §3-17. Commit `ac1a64d` ("done with concerns").
- **Seat:** Claude CLI clean-context reviewer (Opus 5.5). Disclosed: Codex is weekly-limited. Authored no 3-1x unit and no plan 28/37 unit.
- **Date:** 2026-10-06 AEST. Reviewed at master `ec90121`.
- **Method:** artifact-only, plus python on committed tables. The tables are plan 28 `per_rule_classify_assignment.tsv` (fresh classify on fresh dump `1a91b1c2…`), plan 37 `per_rule_phase1_f2_identity.{tsv,json}`, and the 188-row identity table embedded in the 3-17 note. No builds, K1, discs or lock. `output/scratch-3-17/` is absent on every host. That covers `disc.sha256`, `classify.stderr`, `kind_views/`, `classify_kinds/`, `historic_<kind>_rows.tsv`, `identity_audit.py`, `inputs.json` and `rules_*.before.json`. The 3-12 `dump_ext` and `classify/assign_*.u16` it read are gone too, and so is `scratch-3-14/dump_ext`.

## Clauses

| # | Clause (brief / record) | Verdict | Evidence |
| --- | --- | --- | --- |
| C1 | Base `ced98f8`; `e97c968` ancestor; design 170 record present; no prior 3-17 brief | PASS | Ancestry was verified with git. The brief was first added in `ac1a64d`. |
| C2 | Disc sha256 `4ed9cd80…` freshly computed and saved | PASS (value) / UNVERIFIABLE (fresh sum) | The value matches the 3-14/3-16 records and plan 28. `scratch-3-17/disc.sha256` is gone. |
| C3 | Quote 9,064 = 137 + 8,739 + 188; kind counts; 776 = 363 + 132 + 7 + 274; 3-16 0/89/0, without recompute | PASS | Quoted. Arithmetic recomputed: 9,064 and 776. |
| C4 | R01 `cause: checker`, `where in_eo_same == 1`; `rules_other.json` has no R01 | PASS | Live file: `checker [['in_eo_same','==',1]]`. `rules_other.json` ids are O01–O06. |
| S5 | R01 note: exact brief caveat appended, nothing else | PASS | The `ac1a64d` diff changes only the `note` string. The live note ends with `' ' +` the brief's quoted caveat (exact string match). |
| D1 | `git diff --stat`: no `parser/`, `docs/schema/`, plan 07, 3-90 brief or 3-16 file | PASS | `ac1a64d` touches 5 files: IMPLEMENTATION, brief, note, `rules_bg.json`, provenance. |
| B1 | background 137 and background_boundary 8,739: all **not in the failing set** | PASS (by entailment) / UNVERIFIABLE (per-row capture) | The §3-14 kind counts are 0. The per-row old identities (`historic_background_rows.tsv`, `historic_background_boundary_rows.tsv`) are gone. |
| B2 | Completeness 188: still failing, still unattributed, at full item identity | PASS | The embedded table has 188 rows and 188 unique keys (288: 182, 291: 6). Every "3-14 native row" equals plan 28's fresh-dump `dump_row` for the same key (188/188). Plan 28's fresh classify assigns NO_RULE to 188/188. Presence, position and rule are independent measurements. Plan 28's flag selection was taken from this table, but that does not bear on them. |
| B3 | Old→new: 3-12 native rows, and match to 3-15 `historic188_status.tsv` | UNVERIFIABLE | The 3-12 rows are monotone (238..729) and internally plausible. The 3-12 `dump_ext`, `assign_*.u16` and 3-15 `historic188_status.tsv` are deleted. |
| S2a | Full classify on the unchanged CLI exits 1 on a zero-row kind; stderr saved; not PARTITION OK | UNVERIFIABLE (stderr) / PASS (reasoning) | `classify.stderr` is gone. The record does not claim that the abort means PARTITION OK. |
| S2b | Single-kind projection runs (manifest/rule subsets, original order/predicates/causes) | UNVERIFIABLE | `kind_views/` and `classify_kinds/` are gone. This is a disclosed method deviation from brief step 2: scratch manifests stand in for the whole-dump CLI. It assigns no new cause, but the fidelity of the projection cannot be re-checked. |
| S2c | Completeness-only partition: 776 manifest / 468 assigned / 308 unattributed, PARTITION FAIL; O01 363, O04 3, O05 102 | PASS (aggregate) / UNVERIFIABLE (per-row) | Plan 37's forced-zero mechanism applied to plan 28's assignment predicts 363/3/102/308 (assigned 468) exactly. `match: true`, recomputed. The 3-17 per-row bytes are deleted (plan 37 Limit). |
| S2d | 308 ≠ 274 explained by inherited/forced-zero mechanism bytes; no recount claimed | PASS | Plan 37 confirms: 34 forced rows (O05 30, O04 4), giving 274 + 34 = 308. 3-17 did not repeat 3-15's "31" figure. |
| S2e | name_anchor kind-only: 1 row → O03 spool, PARTITION OK for that kind alone | UNVERIFIABLE | `classify_kinds/name_anchor/` is gone. |
| S6 | No build-caused row; nothing fixed | PASS (aggregate) | The cause counts contain no O06 or build rule. Plan 28 also measured O06 0. No code diff. |
| S4 | Sentence "these rows stay unattributed." recorded; no new cause named | PASS | Present verbatim. |
| S7 | IMPLEMENTATION §3-17: C1–C4, table, classify path, R01 diff, deviations; no trailer; Phase 3 not closed | PASS | Present. Phase 3 is stated open. |
| L1 | Land on master (brief) | PASS (disclosed deviation) | The unit committed on a feature branch per the user's instruction and disclosed it. `ac1a64d` is now an ancestor of master. |
| P1 | Provenance entry for scratch-3-17 | PASS (entry) | `docs/provenance.md` L614 exists. The data is gone. |
| S8 | Status `done with concerns` | PASS | Appropriate: there is no global partition and the completeness remainder is unattributed. |

## Recompute

| Claim | Recomputed | Source |
| --- | --- | --- |
| 9,064 = 137 + 8,739 + 188 | 9,064 | arithmetic |
| 776 = 468 + 308 | 776; predicted assigned = 468 | plan 28 assignment + plan 37 forced-zero set |
| O01 363 / O04 3 / O05 102 / NO_RULE 308 | 363 / 3 / 102 / 308; `match: true` | `per_rule_phase1_f2_identity.json`; re-applied to `per_rule_classify_assignment.tsv` |
| 308 − 274 = 34 forced-zero rows | 34 = O05 30 shared + O04 1 shared + O04 3 added; 0 in historic 188 | `per_rule_phase1_f2_identity.tsv` |
| 188 identity table | 188 rows / 188 unique keys; key set = plan 28 historic set; 3-14 native row = plan 28 dump_row 188/188; NO_RULE 188/188 | note table × `per_rule_classify_assignment.tsv` |
| Historic composition 182 L0/288 + 6 L0/291 | 182 + 6 | same |
| R01 caveat exact | `note.endswith(' ' + brief_caveat)` True; cause checker, where in_eo_same==1 | `rules_bg.json`, brief step 5 |

## Verdict

Verdict: ACCEPT-WITH-CONDITIONS

The substantive outcomes hold:

- The 188 completeness rows are still failing and unattributed at full identity and native row, independently corroborated by plan 28's fresh dump and classify.
- The 468/308 aggregate is exactly reproduced by plan 37's mechanism.
- The R01 append is exact and the diff scope is clean.

The classify stderr, the single-kind projection runs, the per-row 3-17 assignment and the old-row captures rest only on deleted scratch.

**Condition:** the residuals below are opened. None is counted as proven. R-G8-4 ("review missing") is discharged.

## Named residuals

| Id | Clause | Root cause | What would close it |
| --- | --- | --- | --- |
| R-G8-4-a | S2b/S2c/S2e: single-kind projection classify (468/308 per row; name_anchor O03 kind-only OK) | `scratch-3-17/kind_views/` and `classify_kinds/` deleted; the aggregate is matched only via plan 37's mechanism | Re-run the completeness-only and name_anchor classify on the retained `1a91b1c2…` dump with mechanism bytes forced-zero per the plan 31 cell list, and commit the per-row assignment (the same gap as plan 37's Limit) |
| R-G8-4-b | S2a: full-CLI empty-kind abort (stderr) | `scratch-3-17/classify.stderr` deleted | Re-run the unchanged CLI on any dump with zero-row kinds and commit the stderr (light) |
| R-G8-4-c | B1: per-row identity capture of the historic 137 background and 8,739 boundary rows | `historic_<kind>_rows.tsv`, 3-12 `dump_ext`, `assign_*.u16` deleted | Recover or regenerate the 3-12 assignment for `013586b5…` and commit the 8,876 old identities. The "not in failing set" conclusion does not depend on this |
| R-G8-4-d | B3: 3-12 native rows for the 188 and exact match to 3-15 `historic188_status.tsv` | 3-12 dump and 3-15 scratch deleted | Closes with R-G8-2-b (a committed pre-3-14 key list with native rows) |
| R-G8-4-e | C2: fresh disc sha saved by the unit | `scratch-3-17/disc.sha256` deleted | Non-material: the sha is pinned elsewhere (3-14, 3-16, plan 28). Close by citation |
