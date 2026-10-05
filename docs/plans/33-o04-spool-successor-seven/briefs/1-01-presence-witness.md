# Brief: 1-01 — per-row G/R presence byte/decode witnesses for the seven O04 rows

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/33-o04-spool-successor-seven/` (new `presence_witness.py`, `presence_witness.tsv`, `presence_witness.json`, `phase1_note.md`, report `reports/1-01-presence-witness.md`) and the synthetic test `parser/tests/test_o04_presence_witness.py`.
Touch nothing else. Commits: none.

## Rows

dump_row 138, 236, 282, 284, 317, 496, 563. Keys, penultimate strata and discriminators are in:
- `docs/plans/04-c-core-orchestration/triage/per_rule_phase2_discriminators.tsv`;
- `per_rule_phase2_reconciliation.md`;
- `per_rule_completeness_mechanism.tsv`;
- `r_contribution_3-02.tsv`.

Strata: emit-piece {138, 284, 496}; demand-removed {236, 282, 317, 563}.

## Outcome (DESIGN Phase 1, with the Design ruling)

A 7-row TSV with these columns:
- full native key, dump_row, demander id, O04 proof refs;
- stratum;
- **G type count for the demanded code in the target cell** on successor `2ee3456a…` and historical `4ed9cd80…`;
- **R type count in the same cell**;
- for each disc: the slot status and the evidence behind it.

Evidence rules:
- Resolved slot: frame offsets, lengths, sha256 and decoded shape-type counts.
- Empty: the index sentinel bytes (offset, hex, sha256), following plan 29's hardened reader contract.
- A `lookup_failed` status can never support absence.
- Reuse the readers rather than reimplementing:
  - G type counts: `docs/plans/30-2-01-source-data-parity/fingerprint.py`'s bounded `--disc` probe logic.
  - R index evidence: plan 29's hardened `witness_p1.py`. It lives at `docs/plans/29-k1-name-anchor-failure/witness_p1.py` or, after that plan's close-out, at `docs/plans/04-c-core-orchestration/triage/name_anchor/witness_p1.py`; import whichever exists.
  - R/G shape decode: `docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py` `decode_slot_shapes`.
- Reaffirm O04/spool identity for each row from the plan-28 TSVs, with hashes.
- Any row where G or R is present, or where evidence is missing, is listed as an exception.

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool yourself.
- Write `--disc g_successor|g_historical|r` probe subcommands with bounded preads and full-pin verification. G pins: successor `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`, historical `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`. For R, cite the historical pin `8c2d2027…` rather than re-hashing it, as plan 29 did.
- Add a `publish` subcommand that builds the TSV from the probe JSONs.
- Run only your synthetic test, with `--basetemp output/scratch-33/tests`.
- List the guarded Execute commands (`.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-33/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/33-o04-spool-successor-seven/presence_witness.py ...`; R disc `/run/media/codyh/464210-8480/ALLDATA.KWI`).

## Not done

No dispositions, no spool edit, no Phase 3 close.
