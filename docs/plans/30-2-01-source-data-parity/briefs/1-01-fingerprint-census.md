# Brief: 1-01 — 342-row fingerprint, type census, 288-template proof

Consumer: Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`.
Owned paths: `docs/plans/30-2-01-source-data-parity/` (new `fingerprint.py`, `fingerprint.tsv`, `fingerprint_summary.json`, `phase1_note.md`, report), plus a focused synthetic test `parser/tests/test_parity_fingerprint.py`. Touch nothing else. In particular, do not edit plan-14/28 triage TSVs, OVERVIEW, the plan-14 record, or any plan-29 file. Execute applies the append-only wording fixes.
Commits: none; leave changes in the tree.
Report: `docs/plans/30-2-01-source-data-parity/reports/1-01-fingerprint-census.md` (rubric `/home/codyh/workspace/workflow-plugin/tools/quality/checks/execution-report.json`).

## Outcome (DESIGN Phase 1, verbatim intent)

A committed 342-row fingerprint TSV with these columns:
- full native key, dump_row, code;
- rule_id from the plan-28 join (`docs/plans/04-c-core-orchestration/triage/per_rule_phase2_join.tsv`);
- R polygon count, vertex counts, bbox (lat/lon) and meet branches;
- R shape signature id (for 288: `T1`/`T2` templates or `other`);
- G demanded-type count on the successor `2ee3456a…` and on historical `4ed9cd80…`;
- spool demander proof reference and clip/emit summary;
- geographic band (`west` lon<113, `east` lon>153.5, `south_offshore`, `other`; define the rule in the note).

Also:
- Census stated as 341 × 288 + 1 × 321 (dump_row 246), or the measured contrary.
- 288-template proof: span 0.083333° × 0.125° (state the tolerance) and one of two local signatures, with counts (Ground: 191 / 150). Exceptions are listed, or the count is 0.
- Define a signature as the normalised vertex sequence relative to the bbox (start corner plus winding). Compute it from bytes or decoded coordinates, never by assumption.

## Inputs

All light reads; prefer them:
- `docs/plans/04-c-core-orchestration/triage/2-01_g-omits-cell-local-dvd-type_members.tsv` (342 rows; `r_proof_path` and `g_cell_type_count` on `4ed9cd80…`);
- `output/scratch-14/cell_local/proofs/<dump_row>.json` (R matching polygons with coordinates, meet branches, spool mechanism) and `output/scratch-14/witnesses/*_requirement.json`;
- `phase3_membership.tsv`;
- the plan-28 join.

Record the sha256 of every input you use.

G on the successor is a disc read. Write it as a `--disc` subcommand of `fingerprint.py`:
- bounded `pread` per cell via the existing decoders (see `docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py` `decode_slot_shapes` and `assert_no_whole_file_discs`);
- per-cell type counts for the 342 keys;
- output JSON under `output/scratch-30/`.

Execute runs it on both `2ee3456a…` and `4ed9cd80…`. The 4ed9cd80 result must equal the members TSV's `g_cell_type_count` as a control.

## Heavy-run rule (binding)

- Never open any `ALLDATA.KWI`, the R disc, or the spool yourself. Run only your synthetic test and light subcommands over committed TSVs and scratch-14 JSON proofs, with `--basetemp output/scratch-30/tests`.
- List the exact guarded disc commands for Execute in this form: `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/fingerprint.py ...`.
- The TSV's successor G columns may be filled by a `merge` subcommand from Execute's disc JSON. Never fill them by hand.

## Not done

No disposition verdicts, no encoder/checker/vocab edits, no 3-90, no Phase 3 close, no plan-29 surfaces.

## Report back

Status, files, test results, census numbers, signature counts, exceptions, and the exact Execute commands.
