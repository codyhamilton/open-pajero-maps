# Brief: 2-01 — supply-path vs unfixable-proven disposition (342 rows)

Consumer: Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`.
Owned paths: `docs/plans/30-2-01-source-data-parity/` (new `phase2_candidates.md`, `disposition.py`, `disposition.tsv`, `disposition_summary.json`, `phase2_note.md`, report `reports/2-01-disposition.md`) and a synthetic test `parser/tests/test_parity_disposition.py`.
Touch nothing else. In particular, not OVERVIEW, not plan-29 or plan-29 close-out surfaces (another seat is collapsing plan 29 concurrently), and no encoder/checker/vocab/extractor code.
Commits: none.

## Outcome (DESIGN Phase 2)

Read DESIGN.md Phase 2 and the Domain "supply vs unfixable disposition" contract 1–8. Required:
- **`disposition.tsv`**, 342 rows: fingerprint key, verdict ∈ {`supply-path`, `unfixable-proven`, `conflict-open`}, cause class, discriminator records, proof paths. Counts in the summary.
- **Type-288 stratum (341 rows):** one evidenced uniform disposition, or an explicit split list.
- **Row 246 (type 321):** disposed on its own evidence.
- Every `supply-path` row names a bounded production-C counterfactual and a successor implement path.
- Every `unfixable-proven` row names a root cause in the allowed classes (WhereIS-only lattice / type-semantic mismatch / representability ceiling), with negative supply evidence.
- Target: `conflict-open` 0, or each open row lists the discriminators tried.
- **Never copy R geometry.** A wrong-code supply (e.g. water→289 for an R-288 cell) is not `supply-path` (DESIGN Assumption 4).

## Candidates (score them in `phase2_candidates.md` against the outcome; pick and justify)

- (a) **Spool-window discriminator:** within a stated window around each target cell, does any existing spool background record of *any* code clip into the cell with area2>0 under the encoder's clip/densify/round mirror? Which code does it map to?
- (b) **OSM PBF tag query:** a bounded, windowed query of `/home/codyh/workspace/open-pajero-maps/australia-260824.osm.pbf` for features that the production vocab (`parser/refdata/vocab/bg_type.json`, `docs/design/osm-vocabulary-mapping.md`) maps to the demanded code within the target cell. It must use streamed reads with a bbox filter.
- (c) **Lattice-identity discriminator:** the R tile equals the 5′×7.5′ WhereIS grid tile, with no OSM feature boundary coincident with it.
- A combination is fine.

The production-C encode probe must reuse the existing mirror, which is independent of the encoder. See `docs/plans/04-c-core-orchestration/triage/cell_local_2-01.py` (`clip_rect`, `encoder_piece`) and plan 14's complete-repair reproducer. Alternatively call the production `bg_shape` C probe that plan 14 used. Cite which.

## Inputs

- Phase 1: `fingerprint.tsv`, `fingerprint_summary.json`.
- `output/scratch-14/cell_local/proofs/`, `output/scratch-14/witnesses/`.
- The spool `output/extract_timing/spool`: Execute only.
- The PBF: Execute only.
- Vocab JSON.

## Heavy-run rule (binding)

- Never open the spool, the PBF, any ALLDATA.KWI or the R disc yourself. Write the probes as subcommands that take explicit paths and stream with bounded windows.
- Run only synthetic tests with `--basetemp output/scratch-30/tests/p2`.
- List the exact guarded commands for Execute: `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-30/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/30-2-01-source-data-parity/disposition.py ...`, writing JSON under `output/scratch-30/`.
- The disposition TSV is built by a `merge`/`publish` subcommand from Execute's probe outputs, never by hand.
- Each probe must log its window, its memory, and every input's sha256.

## Report back

Status, files, tests, the chosen candidate set with scores, the Execute commands, and the expected verdict shape.
