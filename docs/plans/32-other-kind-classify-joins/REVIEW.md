# Independent comprehensive review — plan 32

Verdict: **PASS**

Reviewed SHA: `e4d8ff2050d4701c119c300d9198cabb4f4665a8` (detached HEAD).
Review date: 2026-10-06, Australia/Brisbane.

## Scope and method

Independent review against `DESIGN.md`, following
`/home/codyh/workspace/workflow-plugin/skills/comprehensive-review/SKILL.md`.
Reviewed plan-32 changes from `9fb00da`, `698ccd0`, `a56fb1c`, `02eb8b7`
and `e4d8ff2`: this folder, `parser/tests/test_other_kind_census.py`, and
only the plan-32 OVERVIEW changes. Interleaved plans' implementation changes
are outside this verdict. Plan 28/29 and plan 04 records were read as evidence.

Validation was light: committed TSV/JSON, retained scratch-32 JSON/logs,
source inspection, and the permitted synthetic test file. Dump bins were
stat'ed only; their zero lengths determine the empty-content hash. No disc,
R input or spool was opened. No K1, full pytest suite, 3-90, encode or
historical recovery was run. All validation outputs are under
`output/scratch-32/review/`. No implementation fix was needed; this review
is left uncommitted for the orchestrator.

## Phase outcome assessment

### Phase 1 — successor failing-dump census: met

1. **Census and provenance: met.** The committed TSV's four rows agree with
   `census.json`, the retained manifest, K1 totals and K1 dump counts. All
   source JSON hashes match the committed provenance. Every bin exists with
   size 0; manifest row size is 144 and manifest rows are 0. The evidence
   establishes zero failures independently of the zero-byte files:

   | Kind | K1 checked | K1 failing | Report dump rows | Manifest rows |
   | --- | ---: | ---: | ---: | ---: |
   | interior_cover | 1,590,566 | 0 | 0 | 0 |
   | name_anchor | 2,317,055 | 0 | 0 | 0 |
   | background | 176,386,506 | 0 | 0 | 0 |
   | background_boundary | 64,111,046 | 0 | 0 | 0 |

   The report is C K1, PASS, aggregate failing 0, tolerance 0.5, over levels
   0/2/4/6/8/10/12 and 2,165 ranges. The recorded argv has no level restriction.
   `quantisation_roundtrip.py::_finalize_dump` writes each requested bin even
   when no part rows exist, then records the manifest and report dump counts.
   An unwritten failure dump cannot establish emptiness by itself;
   `census.py` additionally requires agreement with K1 failing totals and
   report dump counts and refuses missing bins or count disagreements.
2. **Scope: met.** Exactly the four intended kinds are censused.
   Completeness is explicitly excluded with its plan-28 pointer. All four
   point-kind failing counts are 0 and no point-kind carry is needed.
3. **Branch: met.** `all_live_empty`, no nonempty kinds, and empty native-key
   sets and row intervals `[0, 0)` are recorded for each kind.
4. **Plan-29 control: met and honest.** The control hash is
   `d4d5038d9d66d420e6e9788100a894006051ee28fe785ed069281b761d1d5d4b`;
   its verdict is pass with no errors. Each in-scope total and each per-level
   checked/failing/error record matches its successor `new` record exactly.
   Name-anchor's historical baseline is 1 failing, successor 0. The fresh
   plan-32 dump/report supplies the discharge; the control is not substituted
   for that measurement. The committed plan-29 `successor_sha.json` binds
   the recorded disc path to the declared `2ee3456a…e6ae` pin.
5. **Phase boundaries: met.** Phase 1 records no classifier partition result,
   OVERVIEW discharge, PSS clearance or Phase 3 closure. OVERVIEW narrowing
   belongs to the later Phase 2 commit.

### Phase 2 — empty-set discharge and OVERVIEW narrowing: met

1. **Empty assignments and disposition: met.** All four assignment TSVs are
   exactly plan 28's 16-column assignment header followed by one newline,
   with zero data rows. `publish` revalidates the census, refuses nonempty or
   control-failing inputs and checks the assignment schema. The artifacts
   are identified as stubs; no classifier execution or PARTITION OK is claimed.
   Historical references in `phase2_disposition.md` agree with their sources:
   - O03 remains spool; plan 29's verdict A, counted admission guard and
     name-anchor 1→0 successor comparison support its disposition.
   - O02 remains spool at 821 rows / 758 source rings. The three additional
     covers belong to S05; 3-13's build conclusion is not extended to O02.
   - R01 remains checker. Plan 04's 3-14 record reports 920,786→0 without
     reclassification. The possible build overlap of 31 L0/291 fills and
     unproven exclusivity remain explicit.
   - S02 retains producer-qualified scope: 1,939,053 rows / 25,772 groups /
     10,001 evidenced rings, without reviving the broad 11,127,845-row predicate.
     The frozen 3-08 boundary remainder 14,610,516 is distinguished from
     3-12's 14,610,990; the remaining 8,739 boundary and 137 fill rows and
     180 combined groups are historical and unattributed. S02–S05→build
     supersession is preserved. The 9,064-row historical total correctly
     includes 188 completeness rows, whose later recovery belongs to plan 28.
2. **Nonempty recovery: not applicable.** No kind selects that branch.
   Historical per-row recovery is not silently claimed as completed.
3. **OVERVIEW: met.** The plan-32 hunks remove the joins blocker from the
   open list and unfinished-work row, and record discharge with the census
   reference, successor pin, four zero counts and historical-disposition pointer.
4. **Remaining gates: met.** PSS remains open. Plan 04 Phase 3 is expressly
   not closed; close synthesis and plan 31's gates remain separate.
5. **Standing constraints: met within the reviewed changes.** No checker,
   tolerance, rule predicate or cause label changed. No 3-90, later-phase
   work, reseating of 170/3-16/3-17, or invented historical assignments appears.

## Guard compliance

The retained `run_p1.sh` invokes `run_heavy_python.py` with `-j 6`.
The wrapper's default path takes `flock output/.heavy.lock` inside a
MemoryAccounting scope; no bypass flag is present. `runs/k1_dump.json`
records that scope, the matching argv, exit 0 and no cgroup error.
`run_p1.log` reports PASS and `EXIT k1 0`.

The K1 cgroup memory peak is **5,940,453,376 bytes** and summed-PSS peak is
**7,478,057 kB** (about 7,303 MiB). These are correctly distinguished in the
notes and do not discharge PSS. Census and publish also used the wrapper,
exited 0 without cgroup errors, and recorded peaks of 20,025,344 and
20,029,440 bytes respectively. Their retained log reports both exits 0.

## Findings by severity

| Severity | Findings | Disposition |
| --- | --- | --- |
| blocker | None | No remediation required |
| high | None | No remediation required |
| medium | None | No remediation required |
| low | None | No remediation required |

No resolved-in-review findings, remediation briefs or non-blocking follow-ups.

## Intent and assumption ledger

The implementation satisfies the chosen live-successor empty-set discharge
without changing historical science or claiming Maps completeness.

| Ledger entry | Assessment |
| --- | --- |
| 1: Empty successor set can discharge joins | Holds under the design's explicit empty-set option; historical recovery remains outside this discharge. |
| 2: Point kinds excluded unless failing | Holds; all four have zero failing counts and no carry. |
| 3: Plan-29 compare cannot be the sole proof | Holds; fresh plan-32 report/dump evidence is retained and hashed. |
| 4: Joins discharge does not close Phase 3 | Holds in the notes, implementation record and OVERVIEW narrowing. |

## Plan sufficiency

Sufficient. The design fixes the kind set, successor, empty/nonempty branch,
control role, phase outcomes and boundaries precisely enough to judge this
implementation and derive light QA. The brief adds the exact assignment-header
contract. No intent reconstruction or additional design decision was necessary.

## Verification and residual risks

- `PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_other_kind_census.py --basetemp output/scratch-32/review/tests`:
  **19 passed in 0.15s**; log `output/scratch-32/review/pytest.log`.
- Independent audit `output/scratch-32/review/check_evidence.py`: **PASS**;
  results `output/scratch-32/review/evidence_checks.json`. It checks source
  hashes, TSV/JSON agreement, report coverage and controls, bin metadata,
  assignment bytes, successor-pin record and guard metadata without opening bins.

The live measurement relies on retained ignored scratch evidence and Execute's
recorded run. This review verifies that chain, not protected-disc bytes or a
new K1 execution. The successor hash is inherited from the committed plan-29
record; no new hash measurement is asserted. Historical attributions and their
qualifications remain science records, not newly recovered assignments or live
failures. PSS, remaining oracle/pin gates and Phase 3 closure remain outside
this verdict. No heavy command is needed for this review's outcomes, and none
is pending for the orchestrator.
