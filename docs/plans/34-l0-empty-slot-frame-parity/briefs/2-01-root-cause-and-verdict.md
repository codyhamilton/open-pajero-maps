# Brief: 2-01 — root cause of the three record-less L0 shells; fix or proven non-deviation

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/34-l0-empty-slot-frame-parity/` (new `phase2_cause.md`, `disposition.tsv`, `disposition.json`, `phase2_note.md`, report `reports/2-01-root-cause-and-verdict.md`, any helper script), the synthetic test `parser/tests/test_l0_empty_shell.py`, and — **only if you choose a fix** — the narrow emit-policy change in `parser/build_alldata.py` and/or `parser/kiwiw/` assembly code with tests.
Touch nothing else. Commits: none.

## Facts (Phase 1, committed)

- L0 blockset 32 / block 0: G successor `2ee3456a…` and G historical `4ed9cd80…` have frames only at (0,541), (0,562), (0,563); R `8c2d2027…` has 2,048 `empty_slot` (`absent_BMT_sentinel`), 0 lookup failures. Witnesses: `witnesses/{g_successor,g_historical,r,spool,summary}.json`.
- Successor frames are all record-less `padded_shell`s (0 names, 0 backgrounds, 0 roads): (0,541) 320 B (plan 29 dropped its only name and zero-padded the frame to keep layout), (0,562)/(0,563) 160 B on both G discs.
- Spool L0 source rows 11689, 13990, 14169 feed the three cells.

## Outcome (DESIGN Phase 2)

1. **Root cause per cell**, proven from code and the committed witnesses: why the builder writes a frame (and a non-empty BMT entry) for a cell whose records all vanish after filtering, division and trimming, while R writes the empty BMT sentinel. Cite exact functions and lines (`parser/build_alldata.py`, `parser/kiwiw/alldata_writer.py` `EMPTY_BMT_*`, cenc/assembly). Distinguish (0,541)'s probe-and-pad origin (plan 29, `docs/design/out-of-span-name-guard.md`) from (0,562)/(0,563).
2. **Verdict per cell**: `fix-landed`, `proven-non-deviation` or `conflict-open` (named). No default.
   - A fix is preferred when it is a narrow emit-policy rule (e.g. a cell with zero records after assembly gets the empty BMT sentinel instead of a frame) that is presence-safe, invents nothing, and keeps every other cell's records identical. Mind plan 29's probe-and-pad contract: if a fix removes the (0,541) shell, the out-of-span guard contract must stay true and be updated only through an explicit note for Execute (do not edit `docs/design/` yourself).
   - If a fix would relocate frames, say so: Execute will then prove confinement at the cell-identity level (plan 31's `docs/plans/31-phase3-oracle-and-pin-gates/oracle_chain.py diff`, whole-frame multiset by cell), not byte-equal sizes.
   - `proven-non-deviation` needs an argument that a record-less shell and an empty slot are equivalent for every consumer the DVD bar covers; if you cannot prove that from code, do not choose it.
3. If you change code: synthetic tests for the new rule (zero-record cell → sentinel; one-record cell unchanged; plan 29's name-drop path), and run only `parser/tests/test_l0_empty_shell.py` plus `parser/tests/test_name_drop_guard.py` and `parser/tests/test_build_wiring.py`, with `--basetemp output/scratch-34/tests-p2`.
4. Exact guarded Execute commands, run serially, for: a full AU encode to a **new** path `output/scratch-34/G_new/ALLDATA.KWI` (`.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-34/runs/p2_encode.json -- .venv-rp/bin/python -B parser/build_alldata.py --spool output/extract_timing/spool --out output/scratch-34/G_new/ALLDATA.KWI -j4`); sha256; the cell diff against `output/scratch-29/G_new/ALLDATA.KWI` (expected: exactly the cells you name); the block-0 re-witness via `frame_witness.py` with `--path`; K1 `-j 6 --engine c` on the new disc (`parser/tools/quantisation_roundtrip.py`); a Perth build to a new path and its sha against `04be2f6e…`; and the hashes of the protected discs and the spool fingerprint before and after. Never overwrite `2ee3456a…`, `4ed9cd80…`, `013586b5…` or any existing disc.
5. `disposition.tsv`/`.json` with per-cell cause, verdict, evidence refs, and placeholders that Execute fills from the guarded runs (new disc sha, diff scope, K1 result).

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool yourself; do not run encodes or K1.
- No O03 reseat; no reseat of 170 / 3-16 / 3-17; no Phase 3 close; no tolerance or checker change.
