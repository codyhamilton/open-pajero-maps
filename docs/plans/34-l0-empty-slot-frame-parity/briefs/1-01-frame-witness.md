# Brief: 1-01 — G frames at L0 (0,541)/(0,562)/(0,563) vs R empty slots; block census

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/34-l0-empty-slot-frame-parity/` (new `frame_witness.py`, `witnesses/*.json`, `phase1_note.md`, report `reports/1-01-frame-witness.md`) and the synthetic test `parser/tests/test_l0_frame_witness.py`.
Touch nothing else. Commits: none.

## Outcome (DESIGN Phase 1)

For each of (0,541), (0,562) and (0,563), on G successor `2ee3456a…` and historical `4ed9cd80…`, record:
- the index path bytes (offsets, hex, sha256);
- frame offset, length, sha256, leaf path and frame class;
- name, background and road counts;
- payload class: empty shell (header only), padded shell, or content. Show which bytes are header, content and zero padding.

Also record:
- **R** (`8c2d2027…`) for the same cells: empty_slot with the index sentinel evidence, using plan 29's hardened reader. Import `witness_p1.py` from `docs/plans/04-c-core-orchestration/triage/name_anchor/` (after plan 29's close-out) or `docs/plans/29-k1-name-anchor-failure/`, whichever exists. Lookup failures are distinct and never count as absence.
- **Whole-block census:** for the 32×64 block containing ix=0 (block 0, blockset 32), count G frames on both G discs against R. List every cell where G has a frame and R has an empty slot. Any cells beyond the three are listed, never ignored.
- For each G frame: which spool source rows and levels feed that cell. This is an input to Phase 2's root cause. Cite the spool cell offsets via existing bounded spool readers (`parser/kiwiw/cenc.py` `E1Spool` or the plan 29 `witness_p1.py` spool-witness logic).

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool yourself.
- Write `--disc g_successor|g_historical|r` and `--spool` probe subcommands. They use bounded preads with full-pin verification for the G discs; cite R's pin.
- Add a `publish` subcommand.
- Run only your synthetic test, with `--basetemp output/scratch-34/tests`.
- List the guarded Execute commands (`.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/<name>.json -- .venv-rp/bin/python -B docs/plans/34-l0-empty-slot-frame-parity/frame_witness.py ...`).

## Not done

No fix, no O03 reseat, no Phase 3 close.
