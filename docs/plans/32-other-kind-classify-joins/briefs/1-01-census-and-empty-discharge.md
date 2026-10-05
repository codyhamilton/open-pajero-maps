# Brief: 1-01 — successor census artefact and the empty-branch discharge

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/32-other-kind-classify-joins/` (new `census.py`, `census.tsv`, `census.json`, `phase1_note.md`, `assignments/<kind>_assignment.tsv` for the four kinds, `phase2_disposition.md`, report `reports/1-01-census-and-empty-discharge.md`) and the synthetic test `parser/tests/test_other_kind_census.py`.
Touch nothing else (not OVERVIEW; Execute narrows it). Commits: none.

## Phase 1 outcome (DESIGN)

`census.py census` reads only these:
- the dump directory `output/scratch-32/dump/` (manifest plus `<kind>.bin` sizes; row size from the manifest);
- the K1 report `output/scratch-32/k1_dump_report.json`;
- the guard log `output/scratch-32/runs/k1_dump.json`.

It writes `census.tsv`/`census.json` with these columns: kind, failing row count from the dump (bytes / row_size, which must be an integer), failing count from the K1 report totals (these must agree), dump file sha256, manifest sha256, workers (6), memory peak, and the disc pin `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`.

Also:
- The four in-scope kinds: interior_cover, name_anchor, background, background_boundary.
- Exclude completeness, with a pointer to plan 28. List point kinds as `out_of_scope` with their K1 failing counts.
- Branch flag: `all_live_empty` or `nonempty_kinds=[...]`.
- Plan-29 control: compare against `successor_k1_compare.json`. It is at `docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/`. Record pass/fail on the failing counts.

## Phase 2 outcome (empty branch)

Only if the census says `all_live_empty`; otherwise stop and report.

- `census.py publish` writes, per kind, a 0-row `assignments/<kind>_assignment.tsv`. Its header matches plan 28's `docs/plans/04-c-core-orchestration/triage/per_rule_classify_assignment.tsv` columns. Add a record of the native-key set being empty.
- `phase2_disposition.md` joins the historical story to proven dispositions:
  - name_anchor → plan 29 (O03 verdict A, successor drop);
  - interior_cover → O02 in `docs/plans/04-c-core-orchestration/triage/rules_other.json` and `cause_table.md`;
  - background → R01 / 3-14 clearance (`rules_bg.json`, cause_table);
  - background_boundary → S02 / residual, carried, with the unattributed historical remainder named.
  - Never relabel historical rows as live failures, and never invent historical assignments.
- Explicitly: plan 04 Phase 3 is not closed; PSS and the close synthesis remain open.

## Rules

- Never open any `ALLDATA.KWI` or the spool. The dump files are tiny and may be read.
- Run only your synthetic test, with `--basetemp output/scratch-32/tests`.
- List the Execute commands (guarded form `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-32/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/32-other-kind-classify-joins/census.py ...`). Execute runs `census` and `publish`.

## Report back

Status, files, tests, census numbers, the branch flag, and the commands.
