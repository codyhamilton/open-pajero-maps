# Independent review — plan 29

Verdict: **REMEDIATE** (post-fix state; R1 is briefed).

Reviewed plan-29 SHA: `25f6a54b9d0f9e6b6ed609144a24d7a7d2b1c3d8`.
Workspace HEAD: `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7` (detached).
Review date: 2026-10-06. Reviewer did not build this change.

## Scope and verification

Read DESIGN, implementation, briefs/reports and the plan-29 witnesses.
Reviewed the eight specified commits with `git show`, and the scoped
`git diff 3fb5a35 25f6a54` over the requested surfaces. For the shared docs,
only the O03 note, scratch-29 section, WP1 plan-29 sentence, successor-pin
note and `4ed9cd80` ledger row were assessed. Interleaved plan-28 changes
were excluded and left untouched.

Ran the three permitted test files:

```sh
.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_name_drop_guard.py parser/tests/test_successor_oracle_tools.py parser/tests/test_build_wiring.py --basetemp output/scratch-29/review/tests
```

**15 passed**, 0.68 s; output: `output/scratch-29/review/pytest-before.log`.
These tests use synthetic inputs under the permitted basetemp. No direct
encode/K1 invocation, live-disc/spool read, Perth build, bench test or full
suite was performed by this reviewer. The existing C extension was current,
so these checks did not rebuild it. Bytecode/cache writes were disabled.

The light JSON/TSV audit is in
`output/scratch-29/review/audit_witnesses.py`, with passing output in
`witness_audit.json` and `witness_audit.log` in that directory. It checks
pins, frame extents, all nine changed ranges, record hashes, the reject TSV
hash/identity, per-level drops, R/control consistency and the saved K1
comparison. Six negative controls reject additional range-count changes or
changed range failure/error values. Saved run logs were read as evidence;
their figures are not new measurements by this reviewer. `git diff --check`
passes. All review scratch writes are under `output/scratch-29/review/`.

## Phase outcome assessment

### Phase 1 — partial

| Outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Pinned failing item | Met | `g.json`, saved failure sample: L0 (0,541), [928], raw (0,370), historical `4ed9cd80…`; one name-anchor failure. |
| 2. G byte identity | Met | Frame offset 197,597,600, length 320, hash; class 288/type 6, string/record bytes and record hash. Record hash recomputed from committed hex. |
| 3. Spool byte identity/distance | Met | `spool.json`: disjoint column segments, concatenated-record hash recomputed, source lon 77.51903576666666, nearest distance 1,635,904.943991 raw. Source latitude correction is honestly recorded. |
| 4. R covering-leaf/absence witness | Partial | Six in-coverage cells reported empty, three outside; same results in `r_successor.json`. Reader positive control resolves Perth. Actual index absence branch/bytes are not retained, and failed lookup is accepted as emptiness (R1). |
| 5. Verdict A/B | Partial | Committed verdict is **A**, consistent with the saved decoder results; not byte-proven to the required independent-review standard until R1 closes. No evidence here supports B. |
| 6. Plan-18 admission/provenance | Met | `spool.json`: both assignments None, ancestor exit 0, recorded pre-plan-18 tree `34a04cc`; provenance is cited rather than represented as intrinsic spool metadata. |
| 7. Whole-spool prediction | Met | `scan.json`/TSV: 2,006,629 anchored names, exactly one reject, L0 (0,541) record 0, no extras; other levels zero. |
| 8. No Phase-1 production change; guarded reads | Met | Phase-1 commits contain plan evidence only; saved witness/control run records carry the heavy accounting scope. |

### Phase 2 — branch A, partial

Verdict A originated in Phase 1; K1 passing does not independently establish
DVD absence. Branch B was not implemented and is not assessed as required.

| Outcome A | Assessment | Evidence |
| --- | --- | --- |
| 1. O03 absent; counted predicted drops | Met | `g_successor.json`: leaf [928] names empty, `o03_absent=true`; AU manifest and both run logs: L0=1, all other levels=0, equal to the scan. |
| 2. New-path successor, confinement/protection | Met on saved evidence | Successor full pin `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`; both sizes 1,692,105,152. Nine ranges/146 bytes, only leaf [928] on both layouts. Guarded encode/diff logs; re-encode identical; protected-disc hashes and spool fingerprint unchanged in both logs. |
| 3. Live K1 and collateral equality | Met with the documented range amendment; literal all-other-kinds equality is not met | Saved `p2_k1_live.json`: exit 0, `-j6`, C engine. Names 2,317,055/0; completeness 1,800,514/0. Only names and range checked fall by one; all other per-level/per-kind records are identical. Comparator passes and additional range changes fail the light controls. |
| 4. R name parity or named residuals | Partial | Successor has zero names. R is reported to have no covering frames, pending R1. Retained nameless (0,541) frame is explicitly named as a layout residual; full DVD frame parity is not claimed. |
| 5. Perth/goldens unchanged or explained | Met on saved evidence | `run_p2b.log`: pre-plan-29 and post-fix Perth both `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`, all drops zero. DESIGN's `da13a775…` is an older baseline. Full-suite report carries only the unrelated inventory failure. |
| 6. In-span name positive control | Met on saved evidence | 2-01 report records `test_moved_road_node_and_name_are_caught` passing on Python/C; source uses an in-span displaced name. Final full-suite record reports no failure in it. This reviewer did not rerun that excluded test. |
| 7. Provenance and successor-pin notes | Met | Scratch-29 provenance, WP1 sentence, 3-90 note and plan-27 ledger identify the successor and retain `4ed9cd80…` as history. References to the eventual collapsed plan record await close-out. |

Both-branch clauses: O03's disposition is updated. Focused tests pass;
the literal full-suite-pass clause has the disclosed pre-existing inventory
exception (R4). No checker/tolerance change or relabel appears in the scoped
commits. No 3-90 rerun, Phase-3 close, phases 4–6/plan 06 work or reseating
of 170/3-16/3-17 is evidenced. Heavy Python runs in the saved records use
`run_heavy_python.py`; this review initiates no heavy run.

## Contract and correctness assessment

**Confinement.** `diff_disc.py` streams differing bytes including chunk
boundaries and unequal-length tails. It partitions every difference at
structure boundaries from both layouts, labels headers/PDMDH/BMT/slot
tables separately, and accepts only a nonempty equal-size comparison with
every resulting segment owned by L0 (0,541) frames on both sides. Normal
metadata, padding outside frames and unmapped changes fail. For these
frozen AU layouts, this is a sound confinement check; the committed ranges
all lie within [197,597,600, 197,597,920), with identical old/new ownership.
Hashes agree across the diff, SHA witness and successor G witness. No live
re-diff is needed to assess this saved result.

**Admission/counts.** `E1Spool(guard_names=True)` is assembly-only;
default readers keep the original spool. Half-open latitude and wrapped
longitude comparisons match `mesh.assign_to_parcel`, rather than rejecting
valid names merely outside their home cell. Only anchored out-of-span
names are removed; missing anchors remain and nonfinite anchors fail.
Only affected cell records are repacked, with non-name columns retained.
Mappings are copy-on-write. `name_drops` counts disjoint source-row ranges
and restricts window counts by cell rectangle. E1 merges the counts once
per level into stdout/manifest; skipped levels also report zero.

**Probe/padding.** Only a chunk with in-window drops runs the unfiltered
E2 probe. E1 routes roads/backgrounds; removing names does not change those
routing rows or retained non-name indices. The probe requires matching
frame count and ix/iy/type/subcell keys; enlargement/topology changes fail.
Shorter frames are padded to the old indexed extent. Assembly copies the
indexed extents, preserving later addresses and index entries; the original
probe bytes are not assembled. The frame's new internal lengths delimit
the reduced content. The saved full-disc diff and live decoder/K1 results
support this for the actual O03 frame. Padding proves confinement, not R
layout equality. With zero in-window drops there is no probe/padding and
unmodified records are not repacked; the synthetic windows and measured
Perth equality support unchanged output. Capturing E2 stats before the
probe restores production-call accounting without changing the checker.

**R reader.** Reads are bounded and grid/coverage geometry is checked.
The positive control is real saved evidence of successful decoding, not
an invented assertion that the reader works. However, the negative result
does not retain its index evidence and conflates lookup failure with
absence. This is the blocking gap, detailed in R1.

## Findings by severity

No blocker or high-severity finding.

- **R1 — medium — briefed:** missing durable index-byte proof and failure
  distinction for R absence. Locations: `witness_p1.py:132–144,195`,
  `witnesses/r.json`, `r_successor.json`, `r_reader_control.json`.
  Brief: [remediation-01.md](briefs/remediation-01.md). Requires bounded
  orchestrator R reads after the reader is strengthened; exact commands
  are in the brief. Production repair has not been attempted here.
- **R2 — low — resolved in review:** `IMPLEMENTATION.md:43` called all
  nine requested cells empty while its in-coverage rectangle contains six.
  Corrected to six reported empty cells plus three outside coverage.
  Verified directly against both committed R JSONs. No brief/re-review
  needed for this correction.
- **R3 — medium — follow-up, non-blocking:** (0,562)/(0,563) frames and the
  retained nameless (0,541) frame are structural G/R differences carried
  to Design in `IMPLEMENTATION.md` and `r_reader_control.json` (the R
  absence side remains subject to R1). Their root causes are not established
  here. The carry is honest and permitted by A4's residual-difference
  clause; it prevents a claim of complete DVD parity.
- **R4 — low — follow-up, non-blocking:** pre-existing
  `test_perf_inventory::test_inventory_covers_every_module` failure.
  `run_p2.log`, `run_p2b.log`, `runs/p2_tests_base3.json` and the 2-02
  report support the baseline exception. The final suite exit is 1,
  not a clean pass: 1 failed / 1060 passed / 7 skipped. Fix inventory in
  its owning work package; do not relabel it as a passing check here.

## Intent, assumptions and plan sufficiency

The implementation matches the one-name repair intent: R selects the
branch, stale spool content is admitted under the existing plan-18
contract, the successor is separate, historical evidence is retained,
and no checker is relaxed. Final acceptance still depends on R1.

Ledger 1 holds for the pinned O03 identity; the spool latitude in DESIGN
was a quantised G value, and the record transparently corrects it by the
same raw row. Ledger 2 is discharged by the recorded (a)/(b) comparison:
private admission avoids a hybrid spool or unrelated re-extraction.
Ledger 3 holds: the repair does not close plan 04 Phase 3 or absorb the
other frame deviations. Ledger 4 is supported by the confined diff and
per-kind comparison; historical 3-90 evidence is not reseated or rerun.
Ledger 5 holds: no new failure required a K1 change.

The range amendment is mathematically necessary: `_k1.c:785–789` calls
`range_item` for each anchored decoded name before its name check. Dropping
one removes one vertex from both counters. `compare_k1.py` permits exactly
that decrease per level and total, with range failures/worst error unchanged.
This is an explained exception to DESIGN's wording, not a checker change
or a broader collateral allowance. The source/decoded latitude correction
and older Perth pin are also explained deviations.

2-02 was completed directly by the orchestrator after the fixer's usage
limit; both the report and implementation disclose this. It lost the
planned fresh-fixer separation, but does not hide an unreviewed production
change: this independent review assessed the final wiring/count fix and
the permitted tests pass. No worker-independence claim is made for 2-02.

The design was sufficient to establish scope, branch choice, ownership,
protection rules and most QA. Two specifications were incomplete: exact
range equality conflicts with removing a name vertex, and an empty R
region needs index evidence because there are no frame bytes to hash.
The implementation record resolves the former; remediation-01 addresses
the latter. Broad suite success also needs an explicit baseline exception.

Residual risks are the briefed negative-witness gap, carried frame-layout
differences and the pre-existing inventory failure. Disc/protection and
heavy-run conclusions rely on saved measurements within this review's
binding limits. The verdict does not authorize a 3-90 run, plan close-out
or a claim that Maps is complete. All changes remain uncommitted for the
orchestrator.
