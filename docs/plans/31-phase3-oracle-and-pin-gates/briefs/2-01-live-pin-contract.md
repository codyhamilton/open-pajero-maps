# Brief: 2-01 — live pin contract on the successor; historical 100/26650 disposition

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.
Owned paths: `docs/plans/31-phase3-oracle-and-pin-gates/` (new `pin_contract.py`, `pin_contract.tsv`, `pin_contract.json`, `phase2_note.md`, report `reports/2-01-live-pin-contract.md`) and the synthetic test `parser/tests/test_pin_contract.py`.
Touch nothing else. Commits: none.

## Outcome (DESIGN Phase 2)

1. **Live failing counts per K1 kind on successor `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`**, cited with path and sha256 rather than re-measured:
   - plan 29 compare: `docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/successor_k1_compare.json` (name_anchor 2,317,055 checked / 0 failing; completeness 1,800,514 / 0; range checked −1 by the drop);
   - plan 32 K1 `-j6` dump on the same disc: `output/scratch-32/k1_dump_report.json`, `output/scratch-32/run_p1.log`, `output/scratch-32/dump/` (interior_cover, name_anchor, background, background_boundary dump bins all 0 bytes; manifest sha `c29ed9f0…`).
   One row per kind in `pin_contract.tsv`: kind, checked, failing, source path, source sha256.
2. **Live pin contract:** the live pinned-failure set is empty iff failing is 0 for every kind. State the set-equality rule for the live Phase 3 close: the close compares the live failing set on the disc in force with the pinned set; with failing 0 everywhere both are ∅ and equality holds trivially. Any kind with failing > 0 or a missing count makes the contract **open** for that kind (no default).
3. **Historical `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv`:** verify sha256 `7dfe6ed7b99e9d234e688d6855a885d3cd1a140db409dc1f726a48bd094885…` (take the full digest from plan 27's pin ledger, `docs/plans/27-independent-fix-review-truncated-pins.md`), the 100-row view and the footer total 26,650. Search read-only for the full enumerations (`enumerate_*.tsv`, `pins_*.tsv`) under `output/` (follow symlinks; any depth) and in git history.
   - If found and hash-consistent: prove set-equality (26,650 groups / 1,939,931 checked) → `reproduced-exhaustive`.
   - Otherwise: `residual-unverifiable` or `residual-not-required-for-live-close`, with root cause (the live contract in item 2 does not need the historical S02 pins when the live failing set is ∅ on the disc in force). Never invent rows.
4. A `publish` subcommand builds the TSV/JSON from cited evidence, verifying each sha256.
5. Explicit in the note: plan 04 Phase 3 is **not** closed; PSS (≤ `-j6` live gate) remains a blocker; other-kind joins are handled by plan 32.

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool. Do not run K1.
- Run only your synthetic test, with `--basetemp output/scratch-31/tests-p2`.
- List any guarded Execute command if one is needed (expected: none, or a light `publish` under `parser/tools/run_heavy_python.py --log output/scratch-31/runs/p2_<name>.json`).

## Not done

No 3-90 rerun, no invented pin list, no Phase 3 close, no reseat of 170 / 3-16 / 3-17.
