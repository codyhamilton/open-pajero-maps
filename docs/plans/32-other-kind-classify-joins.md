# Other-kind native classify joins

Plan 32 discharged the native classify joins for the four non-completeness kinds
on the successor disc in force. A fresh K1 failing-dump census established empty
live sets, and guarded publication produced empty assignment artefacts. Both
phase outcomes were met; historical causes and unresolved qualifications were
preserved, while plan 04 Phase 3 and PSS remained open.

## Intent

User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Discharge the OVERVIEW blocker "other kinds' native classify joins": for every non-completeness classify kind (`interior_cover`, `name_anchor`, `background`, `background_boundary`), produce a recorded per-rule assignment that joins to proven causes for every failing or historical row — or prove that the failing set is empty on the successor disc in force. Model the recovery path on plan 28 (tracked mechanism producer → dump_join → kind-projected classify → join to proven causes). Completeness is already closed by plan 28; do not reseat it. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel. Skip plan 29 close-out (Execute). Do not draft PSS / Phase 3 close synthesis here (depends on plans 31 and 32).

## Why This Existed

Plan 28 had recovered completeness assignments, leaving OVERVIEW's other-kind
native classify joins blocker open. Plan 29 showed zero successor failures for
these kinds, but a control comparison alone did not supply the fresh dump census
and owned assignment artefacts needed to discharge that blocker.

## What Was Built

**Changed:** the census validator/publisher, tracked TSV/JSON census, four empty
assignment tables, historical disposition note, synthetic tests, and the plan-32
OVERVIEW sentence. The lasting evidence lives in
[other_kind_census](04-c-core-orchestration/triage/other_kind_census/phase2_disposition.md).
The [empty-set contract](../design/k1-empty-classify-joins.md) preserves the
reusable discharge rule and the historical follow-up boundaries.

### Phase 1 — Successor failing-dump census

Execute ran C K1 with `--dump-failures` for the four kinds and `-j 6`, under
`run_heavy_python.py` and `output/.heavy.lock`. The recorded run exited 0,
reported **PASS in 83.1 s**, and measured peak summed PSS **7,303 MiB**
(7,478,057 kB). The separate cgroup peak was **5,940,453,376 bytes**.
The inherited successor pin was
`2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.

| Kind | Dump bytes | Live failing rows | Assignment rows |
| --- | ---: | ---: | ---: |
| interior_cover | 0 | 0 | 0 |
| name_anchor | 0 | 0 | 0 |
| background | 0 | 0 | 0 |
| background_boundary | 0 | 0 | 0 |

The four dump bins had SHA256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The manifest SHA256 was
`c29ed9f0bd2fb382729f7fba2d200c9ab3b514aca8154a27e4aaa34a59536839`.
The [census JSON](04-c-core-orchestration/triage/other_kind_census/census.json)
and [TSV](04-c-core-orchestration/triage/other_kind_census/census.tsv) recorded
matching dump, manifest and K1 counts, provenance, and **`all_live_empty`**.
Plan 29's successor control matched all four zero failing counts. Completeness
remained with plan 28; the four point kinds were out of scope with zero failing
counts and no carry. Exact native-key sets were empty and row intervals `[0, 0)`.

### Phase 2 — Empty assignments and historical dispositions

Guarded `census` and `publish` both exited 0. Publication revalidated source
hashes, control agreement and the plan-28 assignment schema, producing four
header-only, 16-column TSVs in
[assignments](04-c-core-orchestration/triage/other_kind_census/assignments/name_anchor_assignment.tsv).
No classifier execution or `PARTITION OK` was asserted.

The [disposition note](04-c-core-orchestration/triage/other_kind_census/phase2_disposition.md)
carried the historical story by kind:

- **name_anchor:** O03 retained spool attribution; plan 29 verdict A and its
  counted assembly guard explained the successor drop from 1 failing row to 0.
- **interior_cover:** O02 remained spool, 821 rows / 758 byte-exact source rings.
  Three additional covers joined S05 in 3-12; 3-13's build supersession of S05
  did not extend to O02.
- **background:** R01 retained checker attribution; 3-14 recorded 920,786 → 0.
  Exclusivity against build remained unproven, including possible overlap of
  31 type-291 fills in the L0/291 window.
- **background_boundary:** S02 retained producer-qualified scope of 1,939,053
  rows / 25,772 groups / 10,001 evidenced rings. S02/S04 build supersession
  and the historical unassigned remainder stayed carried: 8,739 boundary rows,
  alongside 137 fill rows and 180 combined groups, remained unattributed.

OVERVIEW narrowed other-kind native classify joins to discharged on this live
successor census. It retained the open PSS and Phase 3 closure work.

## Deviations

None. All kinds selected the designed empty branch, so nonempty producer,
classify and reconcile recovery was unnecessary. Historical mega-dumps and
per-row assignment recovery were outside this discharge.

## Review

Independent terminal review **PASS**, with no findings at any severity and no
remediation. It reviewed both phase outcomes at `e4d8ff2`; review commit
`097adc9` retained that verdict. The independent evidence audit also passed.
The implementation history was design `9fb00da` (shared with plans 33/34),
Phase 1 preparation and K1 run `698ccd0`, unit 1-01 `a56fb1c`, Phase 1 close
`02eb8b7`, and Phase 2 close `e4d8ff2`.

## QA

The synthetic `parser/tests/test_other_kind_census.py` suite passed **19 tests**
in implementation and terminal review. It covers malformed counts, provenance,
nonempty branching, failed controls, stale census refusal, schema checks,
point-kind carry, and file aliases. Close-out reran only this suite with
`--basetemp output/scratch-32/closeout/tests`: **19 passed**.
No new oracle, K1 run, protected-disc read or spool read was introduced.

## Residual Risks

R01 exclusivity against build remained unproven. S02's historical unassigned
remainder remained unattributed. The measurement depended on retained scratch
JSON/logs and Execute's recorded run; the successor pin was inherited from
plan 29 rather than independently rehashed here. These historical qualifications
were not converted into live failures or silently discharged.

## Follow-ups

[Recorded follow-up boundaries](../design/k1-empty-classify-joins.md#carried-follow-ups)
retain R01 exclusivity and the S02 historical remainder with their source records.
Plan 04 Phase 3 still requires PSS and the separate close synthesis; its
[implementation record](04-c-core-orchestration/IMPLEMENTATION.md) owns that work.
Terminal review introduced no additional follow-ups.

## Decisions Worth Keeping

A measured empty live failing set discharges its native classify join through
an empty assignment artefact. Historical counts remain science records, and
plan-29 control evidence supplements the fresh census. The lasting contract
keeps those boundaries explicit without closing plan 04 Phase 3.
