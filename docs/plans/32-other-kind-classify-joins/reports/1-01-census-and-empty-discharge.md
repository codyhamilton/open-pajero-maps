# Unit 1-01 handoff

Status: implemented, ready for Execute's guarded evidence generation; uncommitted as instructed.

`census.py census` validates the four dump sizes against manifest rows and K1 totals, hashes each bin and the input evidence, records argv/workers/memory/disc provenance, compares the plan-29 successor totals, excludes completeness with its plan-28 pointer, and names point-kind counts and any carry. Nonempty kinds retain exact native dump-row intervals tied to the bin hashes. `publish` rechecks that provenance, refuses nonempty or control-failing evidence, verifies the plan-28 assignment header, and produces four zero-row TSVs only for `all_live_empty`. File aliases cannot overwrite inputs. The notes retain O02/O03/R01/S02/residual dispositions and expressly leave PSS and Phase 3 open.

Verification: `.venv-rp/bin/python -B -m pytest -q parser/tests/test_other_kind_census.py --basetemp output/scratch-32/tests` passed **19 tests**. The test uses synthetic dump/report/control/guard fixtures only, including invalid counts, nonempty branching, stale provenance, publication refusal, and point-kind carry. No other tests were run.

Read-only inspection of Execute's supplied evidence found `interior_cover=0`, `name_anchor=0`, `background=0`, `background_boundary=0` dump rows, all matching K1 and plan 29. Observed branch: **`all_live_empty`**. Six workers; cgroup memory peak 5,940,453,376 bytes; summed-PSS peak 7,478,057 kB. The manifest, K1 report, guard log, and control hashes are recorded in `phase1_note.md`. The successor disc pin is inherited from Execute/plan 29, not independently rehashed; no ALLDATA.KWI or spool was opened.

Departures: none. Plan 29's witnesses were read at their closed-out path supplied by the invoker. No report rewrite, OVERVIEW change, commit, push, or edits/tests in the other workers' plans were performed.

Execute must run the commands below sequentially, check the first result says `all_live_empty` with both control checks true, and include the resulting `census.json`, `census.tsv`, and four `assignments/*_assignment.tsv` files in its evidence commit. Those generated artifacts were deliberately left to Execute, per the brief. `phase2_disposition.md` is conditional on these commands succeeding; this worker does not claim a closed phase or blocker clear.

```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-32/runs/census.json -- .venv-rp/bin/python -B docs/plans/32-other-kind-classify-joins/census.py census
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-32/runs/publish.json -- .venv-rp/bin/python -B docs/plans/32-other-kind-classify-joins/census.py publish
```

Known implementation problems: none found by the synthetic test. Live tool execution remains for Execute; the supplied fresh dump comes from Execute's existing K1 run. The historical 8,739 unassigned boundary rows and qualifications remain carried science, without invented per-row assignments. A nonempty census requires the recovery branch and refuses empty publication.
