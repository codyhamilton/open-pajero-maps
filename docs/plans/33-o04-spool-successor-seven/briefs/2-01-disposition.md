# Brief: 2-01 — per-row disposition of the seven O04 rows

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/33-o04-spool-successor-seven/` (new `disposition.py`, `disposition.tsv`, `disposition.json`, `phase2_note.md`, report `reports/2-01-disposition.md`) and the synthetic test `parser/tests/test_o04_disposition.py`.
Touch nothing else. Commits: none.

## Inputs

- Phase 1 witness: `presence_witness.tsv`/`.json` (7/7 `absence-proven`, 0 exceptions; probe JSON sha256 recorded in `presence_witness.json`).
- K1 completeness on successor `2ee3456a…`: `docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json` (completeness 1,800,514 checked / 0 failing). Cite with sha256.
- DESIGN Decision 3 (amended): **no default verdict.**

## Outcome (DESIGN Phase 2)

A 7-row disposition TSV: native key, dump_row, stratum, verdict, rationale, witness refs (TSV row + sha256 of the Phase 1 JSON and of each probe JSON), fix artefact paths / disc sha (none expected), K1 completeness failing on the disc in force.

Verdict rule, applied per row and never defaulted:
- `proven-non-deviation` only if that row's Phase 1 record has `presence_witness_status = absence-proven`, G successor, G historical and R type counts all 0, every slot status `resolved` or `empty_slot` with sentinel evidence (never `lookup_failed`), and no exceptions.
- Otherwise `conflict-open`, naming what is missing.
- `fix-landed` is out of scope for this unit: a spool edit that emits pieces would invent presence that R lacks (DESIGN Assumption 2). Record for emit-piece rows (138, 284, 496) that the penultimate counterfactual stays evidence only.

`publish` re-verifies the Phase 1 JSON and probe hashes and refuses any row that fails the rule. Synthetic tests must cover: a lookup_failed slot, a non-zero count on any disc, a missing witness, and a mismatched hash; each must yield `conflict-open` or a refusal.

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool. Do not run K1.
- Run only your synthetic test, with `--basetemp output/scratch-33/tests-p2`.
- List the guarded Execute command for `publish` (`.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/p2_publish.json -- ...`).

## Not done

No spool edit, no OVERVIEW edit (Execute owns it), no Phase 3 close.
