# Independent terminal review — 2026-10-06

Verdict: **REMEDIATE** (post-mechanical-fix state).

Reviewed HEAD: `0ecbb954d8d0b1e42777d5e9a9bef4a5b99e0bee`, detached,
equal to the supplied `origin/master` tip. Local execution; no PR.
Scope is the plan-14 commits in `4f8a03d^..0ecbb95`, including design,
refinements, evidence, reproducers and checker implementation `a890662`.
Interleaved plans are excluded. In particular, the plan-18 O03 note change
in `rules_other.json` is not a plan-14 rule change. Plan-25 additions to
the cell-local harness are read as operational context, not reviewed here.

Method: read the requested
`/home/codyh/workspace/workflow-plugin/skills/comprehensive-review/SKILL.md`
first; assessed all phase outcomes and assumptions. Two independent focused
reviewers checked EO/wire correctness and multiplier/integration behavior;
the terminal reviewer checked phase evidence and repeated the defect probes.
No workflow service, commits, full K1, full-AU scripts or full-disc encodes
were run. Validation used small saved tables/dumps, lightweight pytest and
temporary synthetic fixtures/probes. All review changes remain uncommitted.

## Phase outcome assessment

| Phase | Assessment | Evidence and limit |
| --- | --- | --- |
| 1 — per-row evidence | **partial** | `triage/completeness_evidence.tsv` has 776 unique full native keys; all 188 historic and 89 added identities are present and disjoint. R/G witness paths exist, with 775 source triggers and one explicitly recorded source gap. G is the recorded restored `4ed9cd80…` oracle. The header honestly reports failing drift 0 and distinguishes +468/+502 missing-assignment deltas from live partition drift. However, every assignment is `evidence-gap:other_mechanism`; the requested live per-rule assignments/unattributed count were never established. This is acknowledged, not equivalent to the literal Phase 1 outcome. See F3. |
| 2 — proven groups or named questions | **met for the live dataset under the recorded refine** | `triage/phase2_membership.tsv` exactly covers the same 776 full keys, disjointly: 342 cell-local R-present omissions + 432 R-absent complete-repair-zero + 335/765 open. Committed `cell_local_2-01.py`, `complete_repair_2-02.py`, `residuals_2-03.py` package positive discriminators and expected movement, rather than inheriting a science label. Saved summaries show production C zero-record confirmation on the 432 and `phase2_open_questions.md` records confirmation on all 342. The densify correction, rejected tile alias, source search and why each residual was open are recorded. No Phase 2 checker/encoder/rule registration. The design refine deliberately expanded examination to all 776 because live assignments were unavailable. F1 limits generality of the research mirror but does not contradict the recorded live production-C zero-record measurements. |
| 3 — fix/disposition and count closure | **partial** | Saved before/after K1 reports and independently re-read native dumps establish checked 1,800,514 unchanged, failing 776 → 0, exactly all 776 keys removed, no new keys. Other-kind checked/failing counts match; name_anchor 1 remains out of scope. Production re-encode SHA equality is recorded in `IMPLEMENTATION.md` and provenance, backed by successful wrapper/log evidence; no large-disc rehash/re-encode was performed here. Row 765 has the explicit ruling and R-cell contribution proof, yielding 342 + 433 + 1. Row 335 still has no recorded disposition, so open questions 1 ≠ live unattributed 0 (F2). The new generic footprint filter also incorrectly passes a genuinely missing representable piece (F1), violating the narrow Phase 3 criterion despite the measured live count success. Plan 04 Phase 3 remains open as required. |

## Findings by severity

### High

**F1 — EO topology omissions suppress genuine missing geometry. Briefed:**
[briefs/remediation-01.md](briefs/remediation-01.md).

Locations: `parser/tools/k1_representable.py:178`, `:183`, `:200`;
`parser/kiwiw/_k1_cmp.c:244`, `:258`, `:304`.
Only proper crossings trigger decomposition; endpoint-touching lobes and
collinear/repeated traversals are mishandled, and empty arrangements can
revert to the original contour. The two implementations share the defect.

Independent tiny reproductions:

- Two oppositely wound 100×100 squares sharing one vertex: production emits
  2 records/40 bytes, but both missing-disc checkers report checked 1,
  failing **0**; required failing **1**.
- Square traversed twice: production emits 0 records, but both checkers
  report checked 1, failing **1**; required failing **0**.
- Asymmetric bowtie traversed twice: production emits 0 records, but Python
  returns a representable original contour through its empty-edge fallback.

Full rings, reproduction instructions and independent parity expectations
are in the brief. Fixing EO arrangement topology needs design/algorithm
judgment and regression coverage; no structural fix was attempted.

### Medium

**F2 — Phase 3 closes with an explicitly unresolved disposition. Briefed:**
[briefs/remediation-02.md](briefs/remediation-02.md).

Locations: `DESIGN.md:177`, `triage/phase3_membership.tsv` (dump_row 335),
`triage/phase3_groups.md`, `IMPLEMENTATION.md:157` and `:161`.
The evidence now proves the TOL-only demander and zero representability, but
the design still requires a ruling and Phase 3 still marks the key open.
Live unattributed 0 does not equal the one open question. Record a justified
disposition and consistent accounting; the reviewer cannot supply that ruling.

### Low

**F3 — Live Phase 1 classify evidence remains unavailable. Follow-up,
non-blocking.** Locations: `DESIGN.md:114`,
`triage/completeness_evidence.md`, `triage/completeness_evidence.tsv`.
All 776 assignments are evidence gaps because classify rejects the absent
`other_mechanism` column. No `NO_RULE` or live O01/O04/O05 partition is proven.
The later design refine examined all keys and the saved live failing set is
now empty, so this historical assignment gap does not leave an unchecked
current residual. Keep Phase 1 assessed partial; recover reproducible baseline
assignment evidence if required for forensic closure, or explicitly accept the
reduced Phase 1 contract in a later design record. Do not invent mechanism bytes.

**F4 — Long attribution key lists fail after publication. Resolved in review.**
Location: `triage/demand_attribution_3-01.py:49` and `:355`.
Previously, the entire key list became a filename and exceeded `NAME_MAX`
after proofs/table publication (recorded in the 3-01b handoff). Long labels
now use a bounded SHA256-derived name; short historical names are preserved.
`requested_keys` is retained in the JSON so shortening does not lose selection
provenance. Verified determinism, distinct selections, short-name compatibility,
an actual long-selection summary write/read in `/tmp`, and AST syntax. No
attribution rerun or evidence overwrite was needed. Closed; no remediation brief.

**F5 — Tall-row documentation omits multiplier carriage. Resolved in review.**
Location: `parser/kiwiw/cenc.py:900`. Updated the `k1_tall` docstring to the
actual seven fields `(type, cls, n, hx, hy, rec, mult)`; checked against its
dtype and C layout contract. Closed; no remediation brief.

**F6 — Baseline reproducer instructions lack an execution-version pin.
Follow-up, non-blocking.** Locations: `triage/completeness_evidence.md`
(`Reproduce` commands), `triage/demand_attribution_3-01.py:330`.
The Phase 1 commands expect 776 failures but HEAD produces zero. The attribution
helper still compares raw Python demands to the C missing set; the changed C
checker filters those misses. Rerunning at HEAD therefore cannot reproduce its
recorded zero-disagreement baseline. Record pre-3-03 checker pin `0b19b5e` (or
the relevant phase commit) and use isolated scratch destinations when rerunning
historical proofs. Current saved baseline artifacts were present and checked;
they were not regenerated or overwritten in this review.

No blocker-severity finding. Only F1 and F2 are blocking briefed findings.

## Intent, assumptions and plan sufficiency

The implementation follows the refined checker locus, retains the original
oracle and demand counts, names sources rather than registering a catch-all
rule, and preserves the exclusions for 3-16, 3-17, design 170 and plan 04's
later phases. The successful count movement is real evidence of a checker
over-demand correction on this dataset. F1 prevents treating C/Python agreement
or a zero current failure count as proof of the generic new filter's correctness.

Assumption ledger:

1. Existing disc/dumps were unavailable initially. The documented fallback
   restored G by encode and matched the full `4ed9cd80…` SHA. No new oracle.
   Recorded evidence supports the fallback; review did not rerun it.
2. Failure count stayed 776 and historic/added membership was verified.
   The assumed recoverability of the live partition did not hold: cleaned
   side tables were absent. Phase 2 widened coverage explicitly; F3 records
   the remaining literal Phase 1 gap without calling gap deltas partition drift.
3. R/G comparisons were retained. Sparse-tile alias 765 required the later
   geometric contribution proof, and 432 R-absent rows were rechecked under
   the amended definition. This assumption holds with the recorded decode
   contract, not a claim that frame presence always means cell-local presence.
4. Plan 04 Phase 3 cannot close here. Correctly maintained throughout.
5. Prior complete-repair labels are insufficient. New packaged reproducers,
   production C probes and demander enumeration were provided. Holds for
   measured live rows; the generic mirror topology limitation is now F1.

**Plan sufficient, with two closure gaps.** Verbatim intent, explicit phase
outcomes, pins, group contracts and conditional 765 ruling were enough to
derive independent QA and locate the findings. The design's wire/EO condition
requires more topology coverage than the supplied proper-bowtie tests. Phase 1's
assignment fallback never amended its literal outcome, and the explicit 335
ruling dependency remained open at phase close. A phase trailer is not evidence
that either gap was discharged.

The standing DVD-parity rule is broader than a completeness-counter pass.
The 342 R-present/spool-unrepresentable cells remain a carried source-data
parity observation, explicitly excluded from added scope by the signed refine.
This review does not establish the source-data root cause or DVD parity in
those cells and does not close plan 04 Phase 3.

## Validation, evidence and residual risks

Fresh lightweight tests:

```sh
.venv-rp/bin/python -B -m pytest -q \
  parser/tests/test_k1_completeness_representable.py \
  parser/tests/test_k1_completeness.py \
  parser/tests/test_quantisation_roundtrip.py \
  parser/tests/test_k1_background.py \
  parser/tests/test_k1_dump.py
```

**335 passed in 24.80 s.** Existing tests pass while the independent new
synthetic cases expose F1. Multiplier carriage through local/tall construction,
selection, compaction, concatenation and serialization was reviewed; unsupported
C geometry propagates an error rather than silently passing. No substantive
ABI/integration issue found. The mechanical edits change only a filename helper,
summary metadata and a docstring; the helper was separately verified.

Read-only re-counts of committed TSVs and small saved native dumps independently
established:

- Phase 2 coverage: 342 + 432 + 2 = 776; Phase 3: 342 + 433 + 1 = 776.
- 799 attribution entries cover all 776 keys, branches a 1 / b 797 / c 1;
  all recorded production counts are zero.
- Current before/after: 776 → 0 keys, identical checked counts, no other-kind
  checked/failing drift.
- All 776 R/G/requirement/classify witness paths exist. Fresh targeted R/G
  byte-range reads for rows 335 and 765 match all four recorded frame hashes.
- Older-disc control: old failures 739; `B = old failures − current baseline`
  has 52 keys; new-checker older-disc failures equal B exactly, and B has no
  intersection with the 776. Recomputed from `p3/indep/{old,new}_dump_311`,
  not merely accepted from `sets.json` or a commit message.

Recorded evidence cited without expensive reruns:

- `output/scratch-14/evidence_verification.json`: PASS, 776 keys, 1,791
  byte ranges rehashed, 775 source witnesses and one source gap. Review read
  the saved result, not a fresh audit of all disc byte ranges.
- `output/scratch-14/{cell_local,complete_repair,residuals}/summary.json`,
  `attribution/summary.json`, and R contribution proof `r_contribution/765.json`:
  matching group counts and positive discriminators. The 765 bbox is wholly
  west of target cell by 9,615 raw; empty clip and zero C records are recorded.
- `output/scratch-14/p3/k1_p3.json`, `p3/dump/`, and `runs/k1_p3.json`:
  live result and guarded 81.43 s run, exit 1 from the pre-existing other-kind
  failure. Not mistaken for a full K1 pass.
- `output/scratch-14/runs/p3_reencode.json`, `p3/reencode.log`,
  `IMPLEMENTATION.md:146` and `docs/provenance.md`'s scratch-14 entry:
  successful fresh rebuild and recorded SHA256
  `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
  Review did not independently hash the multi-GB discs.
- `output/scratch-14/runs/p3_tests.json`: exit 0, real systemd scope,
  memory_peak 191,049,728 bytes; implementation records **274 passed**, including
  `test_plan25_memory_guards`. The sandbox-specific failure is documented in
  the 3-03 report and `runs/k1_p3_tests_after.txt`; it was not rerun here.

Residual risks: proof bytes are ignored scratch artifacts rather than git
objects; historical reproduction needs the correct checker version and retained
disc/spool pins. Spool recovery was verified in the build record by witness
pins and re-encode equality, not repeated here. F1 is a proven generic blind
spot; its occurrence on additional real data is not measured by this review.

## Requested orchestrator spot checks

1. Outside the sandbox, rerun the specific scope-dependent check:
   `.venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_plan25_memory_guards.py::test_run_heavy_python_records_argv_and_peak`.
   Confirm exit 0 and positive memory peak. Existing recorded evidence supports
   the previous pass; this is an environmental verification request, not a new
   plan-25 code review.
2. Independently rehash `output/scratch-14/p3/G_reencode/ALLDATA.KWI` and
   `output/scratch-14/G_new/ALLDATA.KWI` against the full `4ed9cd80…` pin above.
   No new encode is requested for this spot check.
3. After F1 remediation, repeat its bounded synthetic endpoint/cancellation
   controls before any heavy validation. The subsequent live and older-disc
   checks required to retain the 776-removal/52-defect proof are specified in
   remediation-01; the orchestrator owns any heavy run outside this sandbox.

Append subsequent verdicts and resolutions; preserve this review and findings.

## Resolution record — F1 remediation (2026-10-06, appended by the orchestrator)

Verdict after remediation: **REMEDIATE**. F1 is resolved below, but F2 still stands and needs a Design ruling that neither the reviewer nor the orchestrator can supply.

**F1 — resolved** by a clean Codex `gpt-6.1-sol` (high) agent from `briefs/remediation-01.md` (session `01a10d2f-5163-7a33-850d-e8b0d42b0eee`; report `reports/remediation-01.md`). Both checkers now split at endpoint, repeated-vertex and collinear contacts, preserve parity cancellation, and walk the actual non-empty EO faces. There is no fallback to the original contour. `_cenc.c` is untouched, and neither checker calls the encoder.

Orchestrator verification, outside the sandbox and under plan-25 guards:

- Reproductions, re-run independently against the plan-14 production `bg_shape` probe:
  - `endpoint_lobes`: checker representable → true; production 2 records.
  - `twice_square`: false; production 0.
  - `twice_crossing`: false; production 0.
  - Control square: true; production 1.
  - The worker reports missing-disc C/Python completeness after the fix as lobes 1/1 failing and both doubled contours 1/0, for local and tall selection.
- Tests: 399 passed, including `test_bg_eo_stitch.py` and the systemd-dependent `test_plan25_memory_guards.py` (`runs/rem01_tests.json`). Spot check 1: the memory-guard file passes outside the sandbox (4 passed).
- Live K1 `-j6` on `4ed9cd80…` (`runs/rem01_k1_live.json`): completeness checked 1,800,514, failing **0**. Every other kind's checked/failing is identical to Phase 1. The 776 excused keys remain backed by 0 production records (3-01).
- Older-disc positive control, `scratch-3-11/G_new` (`013586b5…`, `runs/rem01_k1_311.json`): failing **52**, exactly the keys the 3-14 build fix repaired. Their intersection with the 776 is empty.
- Spot check 2: `p3/G_reencode` and `G_new` both hash to `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`. No re-encode was needed for remediation: only `_k1_cmp.c` changed, which is not on the encoder path.

**F2 — stands (Design).** dump_row 335 has a named, unrepresentable demander (3-01), but no group disposition. Folding it into 2-02 needs a ruling like the one 765 got.
