# Independent review — unit 3-15 (completeness cell-local representability, +37 honesty)

- **Unit:** plan 04 unit 3-15. Brief `briefs/3-15-completeness-cell-local.md`; record `triage/completeness_3-15_cell_local.md` + `IMPLEMENTATION.md` §3-15. Science commit `7a12618`, landed `6b8a68a`.
- **Seat:** Claude CLI clean-context reviewer (Opus 5.5). Disclosed: Codex is weekly-limited. Authored no 3-1x unit or plan 28/36/37 unit.
- **Date:** 2026-10-06 AEST. Reviewed at master `ec90121`.
- **Method:** artifact-only, plus light python on committed TSV/JSON (plan 28 `per_rule_classify_assignment.tsv` sha `c73dc3fb…`, `per_rule_completeness_mechanism.tsv` sha `43cbc2c0…`, plan 37 `per_rule_phase1_f2_identity.{tsv,json}`). No builds, K1, discs or lock. `output/scratch-3-15/` is absent on every host (checked `open-pajero-maps-3-15/output/scratch-3-15`: missing). The pre-3-14 dump `scratch-3-11/dump_new_ext/` and `scratch-3-12/small_hypotheses.jsonl` are also absent at their recorded main-checkout paths.
- **Independence caveat on recompute:** plan 28's `in_historic_188` / `in_added_89` flags were built from 3-17's identity table and 3-16's TSV keys (`completeness_evidence.md` L26–29). Those flags are therefore not independent evidence for *which* keys are added. The rule-per-row assignment *is* independent: plan 28 ran a fresh classify on a fresh dump (`1a91b1c2…`).

## Clauses

| # | Clause (brief / record) | Verdict | Evidence |
| --- | --- | --- | --- |
| C1 | Tip contains 3-14 `414c5fe`; AU `4ed9cd80…` / Perth `04be2f6e…` in force | PASS | `git merge-base --is-ancestor 414c5fe adfbdbd` ok. The shas match the §3-14 record. |
| C2a | Total 776, net +37 | PASS | Plan 28's fresh classify has 776 unique keys and 776 unique dump_rows, all L0. 776 − 739 = 37. |
| C2b | Key-level churn 687 shared + 89 added + 52 cleared; 739 − 52 + 89 = 776 | PASS (arithmetic) / UNVERIFIABLE (set-diff) | Flags give 687 / 89 (with 188 ⊂ shared), and the arithmetic holds. The 52 cleared keys and the pre-3-14 739-row key list exist in no committed artefact. The set-diff itself rested on `scratch-3-11/dump_new_ext/completeness.bin` vs `scratch-3-14/dump_ext/completeness.bin`, and both are gone. |
| C2c | All 188 historic keys are present in both dumps | PASS (post) / UNVERIFIABLE (pre) | Post: all 188 are in plan 28's fresh 776 dump. Pre: the 739 dump is gone. |
| C3 | O01/O04/O05/O06 load; classify aborts on the empty residual dump; causes recomputed spool-side | PASS | `rules_other.json` ids are O01–O06. 3-17 observed the same empty-kind abort independently (`dump_io.file_rows`). |
| C4 | Baseline completeness 776, name_anchor 1, S02–S05 0; 9,064 not claimed live | PASS | 776 is corroborated by plan 28's fresh K1. The other counts are cited from the §3-14 record. The record does not claim 9,064 is live. |
| G1a | Historic 188 complete-repair: 885 faces / 189 meets / 205 in-cell / 0 representable | UNVERIFIABLE | `representability_188.py` and its outputs lived only in `scratch-3-15/`. No committed per-key table exists. |
| G1b | Harness control: 725/781 stored 3-08 clip bytes, 16/16 positive controls | UNVERIFIABLE | Same root cause: lost `scratch-3-15/`. |
| G1c | Disposition `checker:repaired-not-representable` ×188 | PASS (count) / UNVERIFIABLE (witness) | Plan 28: historic 188 → NO_RULE 188/188. That is consistent with "no rule registered". The representability witness behind the label is lost (G1a). |
| G2a | +37 census table of 89 added / 52 cleared: legacy>0 for 89/89 added, stitch records 0 | PASS (added, via 3-16) | 3-16's committed TSV has `legacy_spool_degree_records_max` > 0 for 89/89 and `baseline_target_records` = 0 for 89/89. |
| G2b | 52 cleared: stitch records > 0 for 52/52; the "5 legacy positives" are a frame artifact | UNVERIFIABLE | `contract_comparison.json` (scratch-3-15) is gone, and no committed table lists the 52. |
| G2c | Disposition of the 89: "EO-stitch side-effect (build regression)" | FAIL (superseded label) | The label was contract-level and disclosed as not byte-pinned. 3-16's window counterfactual then failed 89/89: "does not survive this counterfactual as a recoverable EO-stitch defect". The brief said "do not force EO attribution". The unit attached a build-regression label without the byte gate. Status `done with concerns` mitigates this but does not cure it. The 89 now have no named root cause beyond "legacy emitted, stitch does not". |
| G3a | Recount 776 = O01 363 + O05 132 + O04 7 + unattributed 274, remainder 0 | PASS | Plan 28's fresh classify gives O01 363 / O05 132 / O04 7 / NO_RULE 274 exactly (causes: checker 495, spool 7, unclassified 274). |
| G3b | Shared 687 = {O01 363, O05 132, O04 4, unattr 188}; added 89 = {O04 3, unattr 86} | PASS | Recomputed by joining the assignment to the mechanism flags (776/776 bijection). Added O04 dump_rows are 138, 282, 563. |
| G3c | Legacy contract reproduces pre 739 = 363 + 132 + 56 + 188 | PASS (arithmetic) / UNVERIFIABLE (measurement) | The sum is 739. The 3-08 probe rerun lived in scratch-3-15. |
| G3d | The 274 are all repaired-not-representable (188 historic + 86 added); the 3 added O04 are also not representable | UNVERIFIABLE | The complete-repair run over the 86 added keys and the 3 added O04 keys is in lost scratch only. |
| G3e | Explanation of the dump bytes: "30 O05 and 1 O04 on `AU.differing_cells.tsv` cells were zeroed" | FAIL (explanation; counts stand) | Plan 37 erratum (`per_rule_phase1_f2_identity.md`): the forced-zero set is **34** = O05 30 (shared) + O04 4 (shared 1, dump_row 317; added 3, dump_rows 138/282/563). Recomputed: 34 rows, none historic, and applying them to 3-15 gives 363/3/102/308 = the 3-17 yardstick. The 3-15 text omits the 3 added O04 rows, so it does not explain the 3-15 → 3-17 delta. `AU.differing_cells.tsv` is not in the repo; plan 37 used the plan 31 proxy. |
| G4 | No S02–S05 edit, no tolerance change, no L8 expand, no rule registered (O07 candidate only) | PASS | `7a12618` touches IMPLEMENTATION.md, `causes_residual.md`, the triage note and provenance only. There are no `parser/` or rules paths. `rules_other.json` has no O07. |
| G5 | Build-fix gate not passed; no fix proposed | PASS | Gate (b)/(c) are stated unmet. No code diff. 3-16 later confirms (b) fails. |
| G6 | Provenance entry for scratch-3-15 | PASS (entry) | `docs/provenance.md` L539 exists. The data it describes is gone. |
| G7 | Status `done with concerns`; deviations disclosed | PASS | The 89/52 churn, the untrustworthy dump bytes and the lack of a full-AU rebuild are all disclosed. |

## Recompute

| Claim | Recomputed | Source |
| --- | --- | --- |
| 776 total, all L0 | 776 rows, 776 unique keys, all level 0 | `per_rule_classify_assignment.tsv` |
| 363 + 132 + 7 + 274 = 776 | O01 363, O05 132, O04 7, NO_RULE 274 (sum 776) | same |
| 687 shared / 89 added / 188 historic | flags (0,0) 499, (1,0) 188, (0,1) 89; shared = 687 | `per_rule_completeness_mechanism.tsv` (flags derive from 3-16/3-17, not independent) |
| Shared {363,132,4,188} | O01 363, O05 132, O04 4, NO_RULE 188 | join of assignment × mechanism |
| Added {O04 3, unattr 86} | O04 3 (rows 138/282/563), NO_RULE 86 | same |
| Historic 188 = 182 L0/288 + 6 L0/291, all unattributed | code 288: 182, code 291: 6; NO_RULE 188 | same |
| 739 − 52 + 89 = 776; 687 + 52 = 739 | 776; 739 | arithmetic only (no 739/52 key list committed) |
| Legacy 363 + 132 + 56 + 188 = 739 | 739 | arithmetic only |
| Forced zero "30 O05 + 1 O04" (= 31) | **34** = O05 30 shared + O04 1 shared + O04 3 added | `per_rule_phase1_f2_identity.{tsv,json}` (34 rows; agrees with the assignment rule and key 34/34) |
| 3-15 → 3-17 predicted | O01 363 / O04 3 / O05 102 / NO_RULE 308 (assigned 468) = 3-17 yardstick | same, applied to the assignment |

## Verdict

Verdict: ACCEPT-WITH-CONDITIONS

The headline counts reproduce exactly from an independent fresh classify (776 = 363 + 132 + 7 + 274; shared/added composition). Five things remain:

- Plan 37 confirms a defect in the unit's forced-zero explanation (31 vs 34). The counts stand.
- The "build regression" label on the 89 is overclaimed and is refuted by 3-16.
- The representability science (885/189/205/0, harness controls) is unverifiable.
- The 52-cleared set-diff is unverifiable.
- The not-representable claim for the 86 added keys is unverifiable.

**Condition:** the residuals below are opened in `residuals.tsv`. None of them is counted as proven. R-G8-2 ("review missing") is discharged.

## Named residuals

| Id | Clause | Root cause | What would close it |
| --- | --- | --- | --- |
| R-G8-2-a | G1a/G1b/G1c: historic 188 complete-repair representability (885 faces / 189 meets / 205 in-cell / 0 representable; 725/781 and 16/16 controls) | `output/scratch-3-15/` deleted (`representability_188.py`, witnesses, control outputs); no committed per-key table | A follow-on unit that re-runs complete-topology-repair representability over the 188 and commits a per-key table (faces, in-cell faces, quantised area2, C records) with a control |
| R-G8-2-b | C2b/C2c/G2b: key-level set-diff 739 → 776 (52 cleared, pre-presence of the 188, stitch>0 for 52/52, 5-positive frame artifact) | Pre-3-14 dump `scratch-3-11/dump_new_ext/completeness.bin` and `scratch-3-15/contract_comparison.json` absent; the 739 key list was never committed | Commit the pre-3-14 739-key list (from a retained or regenerated `013586b5…` K1 dump) and a set-diff table against the plan 28 776 keys |
| R-G8-2-c | G3c: legacy-contract recomputation reproducing 739 = 363/132/56/188 | Lost `scratch-3-15/` legacy probe output | A committed per-row legacy-contract assignment for the 739 keys |
| R-G8-2-d | G3d: the 86 added unattributed (and 3 added O04) are not representable after complete repair | Lost `scratch-3-15/`; the record states it without a per-key table | The same as R-G8-2-a, extended to the 89 added keys |
| R-G8-2-e | G2c: "EO-stitch side-effect (build regression)" label on the 89 | Contract-level attribution without the byte gate; 3-16 counterfactual 0/89 pass refutes the recoverable-defect reading | A Design ruling on the 89's root cause: why legacy emitted and stitch does not, and whether the legacy piece was valid. Until then the 89 are an unexplained deviation, not "build regression" |
| R-G8-2-f | G3e: forced-zero explanation 31 (30 O05 + 1 O04) vs 34 | Unit explanation omitted the 3 added O04 rows (plan 37 erratum); `AU.differing_cells.tsv` was never committed | Explanation defect is **confirmed and corrected** by plan 37 (counts stand; identity named per row, aggregate exact). Residual part: the per-row 3-17 bytes are deleted, and the `AU.differing_cells.tsv` ≡ plan 31 cell-list equality is inferred, not pinned. It closes only if that file is recovered and hashed |
