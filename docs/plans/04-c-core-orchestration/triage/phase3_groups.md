# Phase 3 membership — unit 3-02

Amended 2-02 definition: **"R polygons contributing 0 cell-local records"**.
dump_row 765 folds into 2-02; the Phase 2 ledger is unchanged.

Binding authority: plan 14 DESIGN Phase 3 refine, Design ruling on 765 (now the record `docs/plans/14-completeness-root-cause.md`).

Evidence: `output/scratch-14/r_contribution/765.json` and dump_row 765 in `r_contribution_3-02.tsv`; full decode, multiplier, bbox, EO faces, mirror, production C, and emitted-output footprint. Verdict: proven. Mechanism: outside the cell.

Re-check: 432/432 from actual covering-slot decodes; zero polygons and zero contribution. Per-row evidence: `r_contribution_3-02.tsv` and its proof paths.

776 = 342 (2-01) + 433 (2-02 amended) + 1 (Q-source-335) at 3-02 close; superseded by the 335 ruling below. Membership: 776 rows, unique native keys and dump_row IDs, exact ID coverage 0–775; exhaustive and disjoint assertions pass.

335 stays `open-question:Q-source-335`; 3-01 disposition is outside this unit. This records membership only; checker changes belong to 3-03. Plan 04 Phase 3 remains open.

Carried Design observation: R emits 288 in the 342 2-01 cells while the spool has no representable 288 source: a source-data parity difference outside this unit.

Census correction (plan 30, append-only): 341 of the 342 2-01 rows are type 288 and one (dump_row 246) is type 321; see `docs/plans/04-c-core-orchestration/triage/source_parity/fingerprint.tsv`.

## Design ruling on dump_row 335 (2026-10-06)

dump_row 335, key `(0, 1379, 1138, 288)`, is **folded into amended 2-02** on the evidence:
- the R decode of the key cell has 0 cell-local 288 (its R tile carries only 289);
- G lacks 288;
- the production encoder emits 0 records for the demanding source.

**Distinct sub-cause (trigger):** the demander is a type-288 tall triangular sliver, `tall=39083:L0:home(1379,1143):ordinal=0` (`demand_attribution_3-01.md`). It misses the key cell's centre by 0.348 raw. The pre-3-03 checker's 0.5-raw centre slack (`Region.inside` `TOL`) wrongly counted it as covering the cell. Fixed by 3-03 (checker demands only encodable footprints) and remediation-01.

Final accounting: **776 = 342 (2-01) + 434 (2-02 amended), 0 open questions**. `phase3_membership.tsv` was updated accordingly (exhaustive, disjoint).
