# Plan 30 source-data parity artefacts (lasting)

Record: [`docs/plans/30-2-01-source-data-parity.md`](../../../30-2-01-source-data-parity.md).

These files moved verbatim from `docs/plans/30-2-01-source-data-parity/` at
plan 30 close-out (2026-10-06).

**Embedded labels.** The sha-pinned data artefacts still carry their
historical repo-relative labels `docs/plans/30-2-01-source-data-parity/<name>`:

- `disposition.tsv`;
- `disposition_summary.json`;
- `fingerprint_summary.json`;
- `phase2_snapshot_pin.json`;
- `../o04_seven/disposition.json`.

Read each such label as this directory, `<name>` here. The files were not
rewritten, because their sha256 values are pinned by the summaries and the
wrapper logs.

**Scripts.** `disposition.py` and `fingerprint.py` now resolve `ROOT` five
levels up.

- Their sha256 differs from the `inputs_sha256` recorded in the summaries,
  so a replay or `publish` of the old summaries fails closed on the script
  sha.
- A successor re-run (plan 38 or an implement unit) must re-measure and
  re-pin.

**Contents:**

| File | What it is |
|---|---|
| `fingerprint.py`, `fingerprint.tsv`, `fingerprint_summary.json`, `phase1_note.md` | Phase 1: 342-row fingerprint; census 341 × 288 + 1 × 321 |
| `disposition.py`, `disposition.tsv`, `disposition_summary.json`, `phase2_note.md`, `phase2_candidates.md` | Phase 2: final disposition 341 supply-path / 0 unfixable-proven / 1 carried |
| `open_rows_account.md` | Per-row account of the open rows, including dump_row 246 |
| `missing_way_attic_proof.json`, `attic/` | Amendment 1 root-cause proof (extract clipping) and the Overpass query texts |
| `relation_requests.json`, `phase2_snapshot_pin.json`, `phase2_snapshot.md` | The 61 relations and the pin of the date-matched snapshot `39a836dd…` |
| `reports/` | Unit reports 1-01, 2-01, 2-03 |
