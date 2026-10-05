# Independent comprehensive review — plan 30

**Verdict: PASS** (post-fix state).

**Reviewed SHA:** `10ac10896ea1a7fbfe38cfe9852f90cdfb2ac6f2`, the plan-30 Phase 2 close. Reviewed only plan-30 commits `3447b39`, `9c808c9`, `5147554`, `10a4e66`, `5d2fe64`, `1a08dc2`, and `10ac108`, including the specified census corrections and OVERVIEW hunks. Concurrent commits for plans 29/31/32/33/34 are outside this verdict. The workspace advanced during review; their changes were preserved.

Independent review followed `/home/codyh/workspace/workflow-plugin/skills/comprehensive-review/SKILL.md`. Changes are deliberately **uncommitted** for the orchestrator. No structural findings or remediation briefs.

## Phase outcome assessment

### Phase 1 — met

| DESIGN outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Complete native-key fingerprint and measured G counts | Met | All 342 fingerprint/disposition keys and dump rows join exactly to the 2-01 members, Phase 3 membership, and plan-28 join. Rules are O01 340 / O05 2 (246, 567). R counts, signatures, demander identity, and clip/emit fields are present. Both pinned G count columns are zero for every row, with disc-verified statuses; retained wrapper logs corroborate the successful probes. |
| 2. Correct census and append-only corrections | Met | 341 × 288 + 1 × 321, row 246 at L0 (834,886). Commit `10a4e66` appends corrections to the three specified historical documents; it does not rewrite closed member TSVs. |
| 3. Template identity | Met | Every one of the 341 code-288 rows has one 13-coordinate cell-local polygon, branch c, span 1/12° × 1/8° within 1e-9°. T1 191 / T2 150; no exceptions. Complete sequences and their hashes match the TSV. Both have signed doubled area +2 in (longitude, latitude); the sequences differ only by cyclic start. The erroneous opposite-winding Ground statement is explicitly corrected in the phase note and implementation record. |
| 4. Descriptive bands | Met | West 85 / east 86 / south_offshore 129 / other 42. Labels are descriptive midpoint windows, not absence or coastline proofs. |
| 5. Guarded heavy steps and memory evidence | Met | `run_p1.log` and `runs/g_successor.json`, `g_historical.json`, and `merge.json` show successful wrapper invocations, scoped accounting and retained argv/peaks. Disc code streams pin hashing and caps each pread at 64 MiB. |
| 6. Scope prohibitions | Met | These commits add evidence/probes/tests and append documentation corrections; no production encoder/checker/vocabulary changes, 3-90 rerun, Phase 3 close, or plan-29 close-out work. |

R evidence is the retained, hashed scratch-14 decoded proofs, as the design permits. This review verified committed manifestations of that evidence, not the protected R disc or the scratch-14 proof files themselves.

### Phase 2 — met under the explicit Outcome 6 exception

The disposition package meets the numbered outcomes, including the allowance for individually named open rows. The stronger target of settling every row remains **partial**: the summary honestly says `status=incomplete`. This is not a claim that DVD parity is complete.

| DESIGN outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Complete disposition TSV | Met | 342 exact fingerprint keys/dump rows; reconstructed verdict totals are 243 supply-path / 0 unfixable-proven / 99 conflict-open. TSV SHA256 `67c0f28549afc9cec249373a8fae524652575a88ba3c4d55822186716eff36e2`; summary SHA256 `0051c538ae11072b2e76fac1159fc4a21956c88252929e17cfaf013f34741d85`. |
| 2. Uniform cohort or explicit split | Met | The exhaustive summary groups exactly cover 341 code-288 rows: 243 supply / 98 open. All 341 aligned-grid identities were checked against the retained inventory. |
| 3. Separate row-246 evidence | Met | Row 246 is code 321 and conflict-open. Spool tests 275 code-321 candidates; PBF tests 284. Neither finds a code-321 emitter. Emitters at codes 288/291 remain alternate observations, never supply for 321. |
| 4. Demanded-code C counterfactual and successor path | Met | All 243 chosen witnesses are original-geometry production-C positives at code 288, from 12 named OSM relations. Their tags map to 288 under unchanged production vocabulary; all record selection admission. Every TSV counterfactual exactly matches its reconstructed proof-log witness, including source identity, coordinate hash, byte/record counts, variant and successor implement path. |
| 5. Allowed unfixable root causes with negative evidence | Met, vacuously | No row claims unfixable-proven. Template identity or a failed demander is never used alone to settle an actual negative. |
| 6. Zero open rows or each open row names discriminators | Met via named-open alternative | Exactly 99 summary entries join to the open TSV rows and reproduce their discriminator records: retained demander, lattice identity, completed spool/PBF results, PBF gap state and `pbf-coverage-gap`. They are 98 code-288 rows plus row 246; bands are south_offshore 85 / other 12 / east 2. |
| 7. OVERVIEW narrowing | Met after mechanical wording fix | Both plan-30 hunks preserve the 243 / 0 / 99 counts, the valid disposition TSV path, successor implementation work and the separate seven O04 rows. They retain the explicit statement that plan 04 Phase 3 is not closed. |
| 8. Scope prohibitions | Met | No production data/checker/tolerance changes, relabel, geometry copy from R, 3-90 rerun, reseating 170/3-16/3-17, or drawing later phases. |

## Contract, correctness and failure-mode assessment

The spool claim is supported at the required level: **no emitting demanded-code source exists in the scanned L0 spool**, rather than no candidates existing. Its complete scan reports 432,295 cells, 7,546,320 class-2 backgrounds, verified demander cells and zero gaps. The 1,267 retained probe events reconstruct exactly: all 342 rows have demanded-code candidates, zero have demanded-code emitters or supply witnesses. Some alternate-code sources emit, so an unqualified claim of zero emitters of any code would be false. The production extractor's way-only handling also supports the named relation-assembly successor path.

The PBF log has 1,785 successful candidate events (1,268 way / 517 relation). Replaying its per-code counters and witness selection exactly reproduces the published summaries. Its proof-log SHA256 is `1cb7724a6c1263edc21ce97089675f8c36bf7c68e209aa318ee4d0d8c15327fc`; spool proof-log SHA256 is `4fcf747a1d3655e7df4e562f0d9207306dee3bc7995d2e16f97026402ed1d780`. Summary input hashes match the retained probe JSONs, run JSONs, Phase 1 artifacts and script.

`Accumulator.accept()` selects a supply only when the source code equals the demanded code and a production-C variant emits. `read_probe()` checks PBF tag mapping and reconstructs summaries from the hashed event stream. `CProbe` compiles a read-only include of production `_cenc.c`, calls `kw__bg_shape` with the source type, and production emission writes that type. The chosen 243 witnesses all use the original variant, not a speculative clipping or multiplier repair. Relation assembly requires complete members, joins by node IDs, validates roles/topology and preserves even-odd holes; synthetic C tests include exclusion of a target wholly inside a hole.

`decide()`'s positive-over-gap rule is sound for this existential presence contract: a separate missing source cannot negate an already validated emitting source. Both completed probes and no affected gap are prerequisites for a negative; missing probes and gaps stay open. This review approves the **published** results and these gates, not an exhaustive proof of every possible future repair for a hypothetical gap-free negative.

PBF gaps are 7,922 missing/nested relation members, 8 relation vertex limits, 7 topology edge limits, 5 member limits and 1 open/branched ring. Unknown/partial bounds conservatively affect every row; the log confirms **all 342** have PBF coverage gaps, including the 243 positive rows. Consequently gaps cannot manufacture a supply verdict, and cannot manufacture an unfixable verdict. They can withhold a true negative, which is correctly represented by the 99 conflict-open rows. Per-row publication carries global gap-class totals when affected; source IDs and exact affected-row lists remain in the exhaustive log.

## Findings by severity

No blocker, high or medium findings.

**F1 — low — resolved in review.** The result prose called every selected source an OSM multipolygon relation. All 243 witnesses actually carry `type=boundary` and `boundary=protected_area`. This matters to the successor implementer: supporting only `type=multipolygon` would miss every chosen source. Corrected to OSM boundary relations in `IMPLEMENTATION.md`, `phase2_note.md`, and the plan-30 clause of `docs/OVERVIEW.md`. Verified against all retained witnesses; scientific artifacts, counts and labels are unchanged. No brief or re-review required.

No new non-blocking findings. The already-designed successor implementation and 99 open-row investigation remain residual work, not newly discovered review defects.

## Intent and assumption ledger

The implementation preserves the distinction between checker completeness and DVD presence parity. It supplies evidence and implement paths without copying R geometry or declaring the unresolved rows natural deviations. Full settlement of all 342 is not achieved; the explicit named-open alternative is used honestly.

| Ledger entry | Assessment |
| --- | --- |
| 1. Source-data observation is not already a closed root cause | Holds: no blanket unfixable verdict; 243 recoverable presence paths and 99 unresolved rows are distinguished. |
| 2. Template stratum may share a verdict only with uniform evidence | Holds: template identity is uniform, supply evidence is not; the exhaustive split is published. |
| 3. Supply-path requires a counterfactual, not a landed full-AU fix | Holds: original production-C positives and named successor paths; no disc fix is claimed. |
| 4. Wrong code does not satisfy supply | Holds: vocabulary and demanded-code equality checked for every positive; row 246's alternate emitters do not settle it. |
| 5. This work does not close plan 04 Phase 3 | Holds: OVERVIEW explicitly keeps that phase open. |

The separate Ground assumption of opposite winding failed. Its correction is evidenced and already recorded; it changes no cohort membership or downstream disposition.

## Plan sufficiency, operability and residual risks

**Plan sufficiency: sufficient.** The native-key contract, type-specific presence criterion, separate outlier, allowed causes, Outcome 6 exception, and heavy-run boundaries made intent, findings and QA determinate. Phase 2's open approach was bounded by the recorded candidate comparison and search windows. This is one evidence workflow, not a cross-cutting production change needing parallel reviewers.

Retained run logs show serial `run_heavy_python.py` invocations with the shared lock and scoped memory accounting; all relevant steps exit zero. The PBF wrapper reports **6,051,131,392 bytes memory.peak** (6.05 GB decimal) and **264,544 KiB max RSS** (258.34 MiB). Its final file-cache charge is 5,783,113,728 bytes: RSS alone would substantially understate the accounted load. The implementation uses streamed PBF passes, disk SQLite with a 4 MiB cache, per-source geometry/topology caps, and gap reporting when limits prevent a probe. These observations establish the named bounded path and accounting, not a new PSS ceiling or authority to skip future guards. DESIGN records CHM clear as Ground; stale shared hold prose outside the plan-30 clauses is not changed by this review.

Protected inputs were read-only in the reviewed probe code, with source stamp checks and retained pins. No scoped commit mutates discs or spool. Under the binding review rule, no ALLDATA.KWI, protected spool, production PBF or R disc was opened or rehashed here, so this review does not independently certify their current bytes. Production-scale reruns, a full pytest suite and K1/3-90 were not run. No additional heavy check is required for this verdict.

Residual work is explicit: implement and re-oracle the 243 supply paths in a successor unit; resolve the 99 open rows with further bounded discriminators. Before relying on future unfixable-proven conclusions, retain the no-gap requirement and establish the relevant root-cause/repair evidence within the stated source/window scope. This PASS accepts plan-30 disposition evidence, not end-to-end Maps completion.

## Review verification and changed files

Only the two authorized test files ran:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_parity_fingerprint.py parser/tests/test_parity_disposition.py --basetemp output/scratch-30/review/tests
```

**58 passed in 9.01s.** Review logs and read-only evidence audits are under `output/scratch-30/review/`: `pytest.log`, `audit.py`, `audit.log`, `audit.json`, `provenance.json`, and `inventory_check.json`. The audits check committed TSV/JSON joins, retained event streams and hashes, all supply/open rows, inventory identities and search windows. `git diff --check` passes. No code or test changes required a repeat test run after the documentation fix.

Changed tracked surfaces: this new `REVIEW.md`, `IMPLEMENTATION.md`, `phase2_note.md`, and only the plan-30 relation-type phrase in `docs/OVERVIEW.md`. All review-generated test/probe fixtures and audit outputs are under the authorized review scratch directory. No plans 31–34 surfaces were edited; no commits were made.
