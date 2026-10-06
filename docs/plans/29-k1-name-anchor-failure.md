# K1 name_anchor failure: O03 at L0 (0,541) leaf 928

This work byte-identified the single K1 name_anchor failure, proved that R lacked
its name, and removed it through a counted assembly guard on the existing spool.
Verdict A led to a confined successor oracle on which live K1 exited 0. The
one-name repair met its intent with explained amendments and carried structural
residuals; complete DVD parity and overall Maps completeness remained unproven.

## Intent

User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Root-cause and fix (or prove a non-deviation for) the single K1 name_anchor failure that makes K1 exit 1. First identify the failing case precisely from code/tests/records on master. Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel.

## Why This Existed

The pre-plan-18 extractor clamped an out-of-span longitude into edge cell
(0,541), while retaining the source longitude in the name record. The encoder
then clamped its anchor to lon 90, raw (0,370), leaf 928. The spool restored in
plan 14 came from extractor tree `34a04cc`, before plan 18's admission fix
`16e2931`, so historical oracle `4ed9cd80…` still carried the stale O03 name.
Spool-contract evidence alone did not establish whether this differed from R.

## What Was Built

**Changed:** assembly admission in `parser/kiwiw/cenc.py` and
`parser/build_alldata.py`, synthetic guard/witness/comparator tests, O03's rule
note, successor provenance and pin references. The checker and tolerance stayed
unchanged. Lasting tools and evidence reside in
`docs/plans/04-c-core-orchestration/triage/name_anchor/`.
The lasting contract is [out-of-span name admission](../design/out-of-span-name-guard.md).

### Phase 1 — Byte identity and verdict A

- G: L0 (0,541), leaf [928], frame offset 197,597,600, length 320,
  SHA-256 `3c927c6b4868664907ab14c8a8c49fbf34d5debb8e5ef4d4a22d28e323251b48`.
  The class-288/string-type-6 name at raw (0,370) had offset 197,597,764,
  length 144, SHA-256 `a681fcc453e60a6ea0bde560254ab0d5f66ee58644e22de7632480f944d6b92a`.
  Its Latin-1 text named Île Saint-Paul's territorial waters; full string/record
  bytes are retained in `name_anchor/witnesses/g.json` under the triage directory.
- Spool: L0 (0,541), record 0; cell offset 248,992,624, length 2,616,
  SHA-256 `5b7c1a75a573ca9efbd55c6961b02b1fce06b0dd041b3f6f517f38a79f25d44c`.
  Disjoint name-column bytes hash to
  `e2a39a45284bd347400a40e313a7eaa5c2245994fef706710a0aac98fc618f9c`.
  Source lat/lon were −38.727285888405795 / 77.51903576666666; K1's nearest
  distance was 1,635,904.943991 raw against tolerance 0.5, without halo rescue.
- R: six in-coverage cells (0..1 × 540..542) had `absent_BMT_sentinel`.
  Blockset 32's BSMR entry at absolute offset 11,134 was
  `0020ffffffff00000000`, SHA-256
  `4cbaf49a6952d117e9a318a07af020f26641f0d4c47b14fb897bfc9a6ed41f55`.
  Raw BMT offset `FFFFFFFF` with size zero positively proved absence. The other
  three requested cells, ix −1, were outside coverage by retained LMR geometry.
  R pin: `8c2d20275227b9d2abb0f1802d4e0cbb6697f46545794d19e1a2024b6f169275`.
- The whole-spool scan checked 2,006,629 anchored names: exactly one plan-18
  rejection, O03 at L0; no extras. Both assignment twins returned `None`.
  Replayed index/name bytes gave verdict A, no drift and no concerns.

### Phase 2 — Counted admission and successor oracle

Route (a), assembly admission, won the recorded comparison 12–7 over cell-scoped
regeneration, avoiding a hybrid spool and unrelated extractor differences.
Private copy-on-write mappings dropped anchored names outside the lattice span;
stdout and manifest `out_of_span_names_dropped` counted AU L0=1, other levels=0.
Window restriction and pre-probe E2 accounting fixed the initial guard defects.
Probe-and-pad retained frame extents; the original spool remained untouched.

The successor at `output/scratch-29/G_new` has SHA-256
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.
An independent re-encode matched it. The historical oracle remains
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
Both discs were 1,692,105,152 bytes: nine ranges totaling 146 changed bytes,
confined to L0 (0,541) leaf 928 on both layouts, within the original frame extent.
The successor's leaf has zero names, matching R's absence for this item.

Live C K1 at `-j6` exited 0: name_anchor 2,317,055 checked / 0 failing;
completeness 1,800,514 / 0; range checked decreased by exactly one.
Range failures/error and every other per-kind/per-level record stayed equal.
The positive control still rejected an in-span misplaced name on both engines.

## Deviations

- Range checked also fell by the dropped count because each name anchor is a
  range-check vertex. The comparator amendment permits exactly that coupling.
- Execute completed unit 2-02 directly after the Codex worker hit its usage
  limit, losing the planned fresh-fixer separation; independent review covered it.
- DESIGN called G's decoded latitude −38.727284749 the spool latitude. The
  source latitude was −38.727285888405795; identity was corrected by the shared
  raw row, with no tolerance change.
- DESIGN's Perth `da13a775…` baseline was historical. Pre-plan-29 tip and
  post-fix Perth both hashed to `04be2f6e…`; plan 29 did not cause that older drift.
- R1 required remediation: absence labels were replaced by retained index-byte
  proofs, and lookup failures became unresolved. Commit `8798302` closed it.
- The full-suite clause retained the proven baseline inventory exception.

## Review

Initial independent review `c2cab9c` required R1 remediation. Appended re-review
`3dba40d` assessed `8798302` and returned **PASS_WITH_FOLLOWUPS**. R1's sentinel
and replay proof closed the negative-witness gap. R2's six-empty/three-outside
wording and R5's focused-test count were resolved in review. R3 (medium) and
R4 (low) remained non-blocking; no blocker or high finding stood.

## QA

Saved guarded measurements established AU confinement, the identical re-encode,
unchanged protected-disc hashes and spool fingerprint, and live K1 exit 0.
Perth was unchanged at
`04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`, with zero drops
at every level. The final measured full parser suite was **1 failed / 1060 passed /
7 skipped**, solely the pre-existing inventory failure; goldens, bench, wiring
and the name positive control passed. Independent re-review ran 25 light tests.
Close-out ran only `test_name_drop_guard.py`, `test_successor_oracle_tools.py`,
`test_r_absence_witness.py` and `test_build_wiring.py`: **37 passed in 1.35s**,
with `--basetemp output/scratch-29/closeout/tests` and bytecode/cache disabled.

## Residual Risks

Preserving frame extents proves confinement, not R layout equality. G still has
frames where R has empty slots. Heavy measurements and full-disc pins rely on
saved evidence; close-out opens no protected disc or spool. Full DVD parity,
Maps completeness and plan 04 Phase 3 remain open. There was no 3-90 rerun or
reseating of 170/3-16/3-17.

## Follow-ups

- R3: the nameless (0,541) frame and (0,562)/(0,563) frames versus R empty slots
  go to plan 34 for structural root causes and disposition.
- R4: the baseline `test_perf_inventory::test_inventory_covers_every_module`
  failure remains carried to plan 04's performance-inventory owner.
  **Discharged by plan 37 Phase 2:** the six missing modules are now in
  `parser/perf_inventory.json`, and `test_perf_inventory.py` passes 4/4
  (`docs/plans/37-3-17-f2-identity-and-perf-inventory/reports/2-01-perf-inventory.md`).
  Both carries are durable in the [contract's follow-up section](../design/out-of-span-name-guard.md#carried-follow-ups).

## Decisions Worth Keeping

R decides item parity. Negative evidence needs replayable index bytes and actual
sentinels; lookup failure cannot establish absence. Counted assembly admission
can repair stale inputs without changing the source spool, and a confined diff
plus unchanged collateral checks supports a successor while preserving history.
