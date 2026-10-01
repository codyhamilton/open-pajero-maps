# Brief: 3-05 — Triage tool: group, summarise and classify the failure dump

Consumer: 3-07 and 3-08 (they author rule files and read the tables), 3-90 (re-runs `classify` on the post-fix dump).
Owned paths: new `parser/tools/k1_triage.py`, new `parser/tests/test_k1_triage.py`, `parser/perf_inventory.json` (one module entry, class `orchestration`; the inventory test fails without it). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 3-03 (the dump format and columns).
Runs alongside: 3-06 only. This unit never loads the C library (it reads dump files with numpy).
Tier: Flash (mandatory Sonnet 5.5 review). Not RE-risky: no geometry; rules are column predicates.
Budget: 5 files to read, about 400 lines (300 tool, 100 test), 50 tool turns. Past the budget, stop; handoff in `IMPLEMENTATION.md`; report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/briefs/3-02-k1-failure-dump.md` and `3-03-k1-dump-diagnostics.md` — the dump files, manifest and every column (exact names).
2. `DESIGN.md` Phase 3 Outcome and Assumption 1 (cause classes; "exactly one cause"; pinned list is item identity).
3. `parser/tools/quantisation_roundtrip.py` — only the `--dump-failures` code (manifest writer) and the report `totals` keys.
4. `parser/perf_inventory.json` — one entry for the format; `parser/tests/test_perf_inventory.py` — what it checks.

## Goal

A deterministic offline tool that turns a dump directory into the tables the cause table is built from, and that PROVES a proposed set of rules assigns every dump row to exactly one cause.

## Contract

Cited from `DESIGN.md` Phase 3 Outcome: "every failing item behind the counts in Problem is assigned exactly one cause — checker rule wrong, build (disc) defect, or spool/extraction defect — with the count per cause recorded." The perf rule: a Python loop is allowed only when its trip count is bounded by ranges, levels, files, kinds or report rows. Therefore the tool works on numpy arrays in chunks of 2,000,000 rows (a `np.memmap` per kind) with no Python loop over rows; loops over rules, kinds, levels and groups are fine. Peak RSS ≤ 4 GB on the full 16.5 M-row dump.

Decisions this brief makes (do not reopen):

- `summary --dump DIR --out OUT` writes: `OUT/totals.tsv` (kind, rows from manifest, rows read, equal?); `OUT/by_level_type.tsv` (kind, level, type, rows, rows with onb≠0, in_eo_same=1, in_wn_same=1, in_eo_any=1, d_any not NaN, src sentinel); `OUT/groups_<kind>.tsv` (level, ix, iy, type, leaf path p0..p6, shape, rows, first vert, last vert, min/max of `d_src`; sorted by rows desc then key); `OUT/by_src.tsv` (kind, level, src_ix, src_iy, src_rec, src_tall, src_nv, src_maxseg, type, rows, groups; sorted by rows desc then key; capped at 5,000 lines with a final line stating how many were cut).
- `classify --dump DIR --rules RULES.json --out OUT`: rules file schema, version 1:
  `{"version":1,"rules":[{"id":"R01","cause":"checker|build|spool","kind":"background_boundary","where":[["level","==",0],["in_eo_any","==",1]],"note":"text"}, ...]}`.
  Operators: `== != < <= > >= in isnan notnan` (`in` takes a list). Columns are the dump column names plus `level`. A row's rule is the FIRST rule whose `kind` matches and all `where` terms hold. The tool writes `OUT/cause_counts.tsv` (rule id, cause, kind, level, rows, groups), `OUT/assign_<kind>.u16` (rule index per row, 65535 = none), `OUT/unclassified_groups.tsv` (same columns as groups, rows with no rule), `OUT/partition.txt` (per kind: manifest rows, assigned rows, unclassified rows, sum of cause_counts rows; a final line `PARTITION OK` or `PARTITION FAIL`). Exit code 0 only if every kind has unclassified = 0 and the sums equal the manifest rows; 1 otherwise. A rule with an unknown cause string or column is a hard error (exit 2) before any reading.
- `enumerate --dump DIR --assign OUT --rule R01 --out FILE`: the group-granularity list (kind, level, ix, iy, type, leaf path, shape, rows) of the rows a rule claims, sorted by key; this is the format of the pinned list.
- All output files are byte-identical across runs (sorted keys, fixed float formatting `%.6f`).

## Changes

The tool, its test, one inventory entry (path, class `orchestration`, reason `offline triage over dump files; numpy chunks, no per-row Python loop`).

### Keep untouched

Everything else. The tool never writes into the dump directory.

## Done evidence

Write `parser/tests/test_k1_triage.py` first (fails before: no module).

- A synthetic dump (built in the test from the manifest layout, 3,000 rows over three kinds, two levels) with a rules file that covers it: `classify` exits 0, `PARTITION OK`, `cause_counts` sums equal row counts; drop one rule → exit 1, `unclassified_groups.tsv` lists exactly the dropped rule's groups; an unknown column → exit 2; two overlapping rules → each row counted once (first wins); outputs byte-identical across two runs; `enumerate` row sum equals the rule's count.
- Real dump: `.venv-rp/bin/python parser/tools/k1_triage.py summary --dump output/scratch-3-03/dump --out output/scratch-3-05/summary` completes, `totals.tsv` shows rows equal on all five kinds (1,438,558 / 16,549,569 / 824 / 752 / 1), peak RSS (from `/usr/bin/time -v`) ≤ 4 GB, wall reported. Run `classify` with a one-rule-per-kind catch-all file (cause `spool`, no `where`) → `PARTITION OK` (proves the engine, not a cause).
- `.venv-rp/bin/python -m pytest parser/tests/test_k1_triage.py parser/tests/test_perf_inventory.py -q --basetemp=output/scratch-3-05/pytest` → pass.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
