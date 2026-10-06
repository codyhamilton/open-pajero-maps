# Independent review — unit 3-16 (89-key original-spool window counterfactual)

- **Unit:** plan 04 unit 3-16. Brief `briefs/3-16-completeness-89-window-cf.md`; records `triage/completeness_3-16_window_cf.md`, `triage/completeness_3-16_outcomes.tsv` (sha `3ce6a141…`), `IMPLEMENTATION.md` §3-16. Commit `e97c968`.
- **Seat:** Claude CLI clean-context reviewer (Opus 5.5). Disclosed: Codex is weekly-limited. Authored no 3-1x unit.
- **Date:** 2026-10-06 AEST. Reviewed at master `ec90121`.
- **Method:** artifact-only, plus python on the committed outcomes TSV and the plan 28 tables. No builds, K1, discs or lock. `output/scratch-3-16/` is absent on every host. That covers `keys89.json`, `inputs.json`, `run.py`, `split.py`, `audit.py`, `results.json`, `tally.json`, `audit_summary.json`, `SHA256SUMS` and `key_NN/`. The 3-15 source packet (`open-pajero-maps-3-15/output/scratch-3-15/contract_comparison.json`, `mechanism_776_recomputed.jsonl`) is also gone.

## Clauses

| # | Clause (brief / record) | Verdict | Evidence |
| --- | --- | --- | --- |
| C1 | Tip contains 3-15 `6b8a68a` | PASS | `6b8a68a` is an ancestor of base `9b44b59` and of `e97c968`. |
| C2a | 89-key list recovered from the 3-15 packet, not reconstructed by disc diff | UNVERIFIABLE (source) | The packet and `keys89.json` (sha `1fe735cf…`) are gone, so the provenance of the list cannot be re-checked. |
| C2b | 89 unique full keys | PASS | The TSV has 89 rows and 89 unique 12-field keys, all L0 (288: 84, 291: 5). They are disjoint from the historic 188 and all present in plan 28's fresh 776 dump (`completeness_evidence.md` validation). |
| C3 | 3-15 arithmetic quoted once, not recomputed | PASS | The packet quotes 776 = 363 + 132 + 7 + 274 and 687/89/52 verbatim. |
| S2a | Every key is pass/fail/untested, untested listed | PASS | Recomputed: fail 89, pass 0, untested 0. Ordinals are 0..88 contiguous. 89/89 witness paths are `output/scratch-3-16/key_NN/outcome.json`. |
| S2b | One-cell half-open window `(0,ix,iy,ix+1,iy+1)` per key | PASS | 89/89 window strings match. |
| S2c | Baseline frames byte-equal to the stored 3-14 AU disc (padding only) | UNVERIFIABLE | `key_NN/baseline_byte_gate.json` and the frame bytes are gone. Re-checking against disc `4ed9cd80…` is outside this review's allowance. |
| S2d | Counterfactual frames byte-identical to baseline | PASS (internal) / UNVERIFIABLE (bytes) | The TSV padded-hash pairs are equal 89/89 and the raw-dump-hash pairs are equal 89/89. The hashed bytes are gone. |
| S2e | Baseline and counterfactual emit 0 target-class records; legacy probe still emits | PASS (as recorded) | `baseline_target_records` = 0 for 89/89 and `counterfactual_target_records` = 0 for 89/89. `legacy_spool_degree_records_max` > 0 for 89/89. Underlying D1 decodes are lost (see S2c). |
| S2f | Original completeness key persists under original-spool K1 before and after | PASS (as recorded) | `(before, after)` = (1, 1) for 89/89. The K1 JSON is lost. |
| S2g | 34 source rings → 156 EO faces | PASS (34) / UNVERIFIABLE (156) | 34 distinct source tokens across the `sources` column (33 distinct strings; one row has two sources). The face count lived in `source_changes.json` / `region_audit.json`, which are gone. |
| S2h | Serialization error ≤ 1.8617682673836184e-9 raw; home-record / L0 index hashes unchanged; cold audit PASS; wall 1,213.8 s | UNVERIFIABLE | `audit_summary.json`, `home_audit.json` and the run log are gone. |
| S2i | `key_00` = (0,906,1225,291,0…,−1), padded sha `b71240ec…` | PASS | Matches TSV row 0. |
| S3 | No encoder, checker or rule diff; no O07 | PASS | `e97c968` touches IMPLEMENTATION.md, the packet, the TSV and provenance only. `rules_other.json` is O01–O06. |
| S4 | Disposition accept-with-honesty for 89; no gate (b) pass; Design (c) unchanged; unit stops | PASS | This is consistent with the brief's all-fail branch. No fix branch was opened. |
| M1 | The tested correction is a topology-preserving EO-face bypass, not a localized C patch | PASS (disclosed limit) | The record says plainly that a "fail" does not exclude every conceivable C patch. This is the right honesty, and it is why R-G8-2-e (3-15 review) is left open rather than closed by this unit. |
| P1 | Provenance entry for scratch-3-16 with a reproduction recipe | PASS (entry) | `docs/provenance.md` L545+ exists. Running the recipe needs `keys89.json`/`run.py`, which are gone. |

## Recompute

| Claim | Recomputed | Source |
| --- | --- | --- |
| 89 rows | 89 rows, 89 unique keys | `completeness_3-16_outcomes.tsv` |
| 0 pass / 89 fail / 0 untested | fail 89 | same, `outcome` column |
| Keys = 3-15 added_89 | 89/89 equal to plan 28 `in_added_89` set (circular: plan 28 flags were built from this TSV); disjoint from the 188; present in the fresh 776 dump | TSV × `per_rule_completeness_mechanism.tsv`, `completeness_evidence.md` |
| Byte-identical frames | padded 89/89 equal, raw 89/89 equal | TSV hash columns |
| Legacy emits 89/89 | 89/89 > 0 | `legacy_spool_degree_records_max` |
| Stitch/counterfactual target records 0 | 89/89 and 89/89 | TSV |
| K1 failure persists | (1,1) × 89 | TSV |
| 34 source rings | 34 distinct source tokens | `sources` column |
| Added composition (context) | O04 3 + NO_RULE 86 | plan 28 assignment over the 89 |

## Verdict

Verdict: ACCEPT-WITH-CONDITIONS

The committed outcome table is complete and internally consistent: 89/89 keys, 0/89/0, equal hash pairs, zero target records, and the K1 failure persisting. The scope and no-diff clauses pass, and the method's limit is disclosed. The byte gates, the 156-face intervention, the audit and the 3-15 key-packet provenance rest only on deleted scratch.

**Condition:** the residuals below are opened. None is counted as proven. R-G8-3 ("review missing") is discharged.

## Named residuals

| Id | Clause | Root cause | What would close it |
| --- | --- | --- | --- |
| R-G8-3-a | C2a: 89-key list sourced from 3-15 `contract_comparison.json` `added_89` (packet sha `1fe735cf…`, sources sha `bd123cd7…`) | `scratch-3-15/` and `scratch-3-16/keys89.json` deleted | Closes with R-G8-2-b (a committed 739-vs-776 set-diff that re-derives the 89 independently) |
| R-G8-3-b | S2c/S2d: per-key baseline byte gate vs the 3-14 AU disc, and baseline ≡ counterfactual frame bytes | `scratch-3-16/key_NN/` frames and `baseline_byte_gate.json` deleted; only hashes survive in the TSV | Re-extract the 89 target-cell frames from disc `4ed9cd80…` under the lock and match them to the TSV `baseline_padded_frame_sha256` (baseline half). The counterfactual half needs a re-run |
| R-G8-3-c | S2g/S2h: 34 rings → 156 faces, serialization error 1.86e-9, home/index hash audit, cold-audit PASS | `source_changes.json`, `region_audit.json`, `home_audit.json`, `audit_summary.json` and `SHA256SUMS` deleted | A follow-on re-run of `run.py`/`audit.py` (scripts also lost, so they must be rewritten) that commits the face table and audit summary |
| R-G8-3-d | S2e/S2f underlying witnesses (D1 decodes, original-spool K1 JSON per key) | `key_NN/` deleted | The same re-run as R-G8-3-c; the TSV values are recorded but not re-derivable |
