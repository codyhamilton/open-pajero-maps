Status: **done with concerns** (implementation complete; measured gates deferred to Execute by the binding heavy-run rule).

What changed:
- `phase2_routes.md` scores (a)/(b), picks (a), rejects hybrid-cell regeneration.
- Assembly filters names by plan 18's half-open lattice span in private copy-on-write `E1Spool` mappings. Source files remain untouched. Counts merge once per source row into stdout and `manifest.out_of_span_names_dropped`, including zero levels. K1 keeps the original spool input.
- To prevent relocation in the packed disc, affected chunks probe their original input and retain original frame extents with zero trailing padding. Topology changes/enlargement fail explicitly.
- `diff_disc.py`: ≤8 MiB streamed differences/hashes and bounded metadata reads; every changed range mapped on both layouts. Confinement requires equal sizes, a nonempty diff, and every changed byte inside frames of L0 (0,541) on both sides. Header/PDMDH/BMT/slot/padding/unmapped changes fail. Exact changed-leaf list is emitted.
- `compare_k1.py`: exact Phase 1 drops, per-kind/per-level comparison, name checked minus drops / failing zero, completeness 1,800,514 / 0, unchanged other kind records, tolerance 0.5, C engine and pass/exit expectation 0.
- Successor G witness lists every residual name and checks O03 absence; R witness can retain all names. New outputs preserve Phase 1 witnesses.
- Only O03's note changed in `rules_other.json`; measured-pin token `EXECUTE_MEASURED_SHA_PENDING` points to “see plan 29 record”.

Check output before/after:
- Before implementation: `test_name_drop_guard.py`: **5 failed** (unsupported guard argument / missing manifest counter).
- After: focused command below: **13 passed in 0.82s**. Synthetic inputs only, under `output/scratch-29/tests/`: private spool protection, preserved in-span name record bytes, neighboring frame/disc bytes, exact changed leaf [928], rejected header collateral, serial/parallel count equality, diff chunk boundaries, and K1 comparison failure controls. The tiny successor also passes C K1 against the unchanged synthetic spool: name_anchor failing 1→0 and checked minus exactly one.
- Existing `test_moved_road_node_and_name_are_caught` ran on both Python/C engines: in-span misplaced name still fails `name_anchor`. No checker change.
- Own argparse `--help` calls and `git diff --check`: exit 0.

Focused command:
```sh
.venv-rp/bin/python -B -m pytest -q parser/tests/test_name_drop_guard.py parser/tests/test_successor_oracle_tools.py parser/tests/test_quantisation_roundtrip.py::test_moved_road_node_and_name_are_caught parser/tests/test_build_alldata.py::test_pipeline_writes_output_and_manifest parser/tests/test_build_alldata.py::test_missing_spool_exits_nonzero --basetemp output/scratch-29/tests/final3
```

Exact ordered heavy commands for Execute (repo cwd; each completes before the next):
```sh
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_encode.json -- .venv-rp/bin/python -B parser/build_alldata.py --spool output/extract_timing/spool --out output/scratch-29/G_new/ALLDATA.KWI -j4
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_sha.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/diff_disc.py --sha-only output/scratch-29/G_new/ALLDATA.KWI --out docs/plans/29-k1-name-anchor-failure/witnesses/successor_sha.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_diff.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/diff_disc.py --old output/scratch-14/G_new/ALLDATA.KWI --new output/scratch-29/G_new/ALLDATA.KWI --out docs/plans/29-k1-name-anchor-failure/witnesses/successor_diff.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_k1_live.json -- .venv-rp/bin/python -B parser/tools/quantisation_roundtrip.py --disc output/scratch-29/G_new/ALLDATA.KWI --spool output/extract_timing/spool --out output/scratch-29/k1_live.json -j6 --engine c
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_compare_k1.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/compare_k1.py --new output/scratch-29/k1_live.json --manifest output/scratch-29/G_new/manifest.json --out docs/plans/29-k1-name-anchor-failure/witnesses/successor_k1_compare.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_g_witness.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py g-witness --successor --disc output/scratch-29/G_new/ALLDATA.KWI --out docs/plans/29-k1-name-anchor-failure/witnesses/g_successor.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_r_witness.json -- .venv-rp/bin/python -B docs/plans/29-k1-name-anchor-failure/witness_p1.py r-witness --disc /run/media/codyh/464210-8480/ALLDATA.KWI --keep-names --out docs/plans/29-k1-name-anchor-failure/witnesses/r_successor.json
.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/p2_parser_tests.json -- .venv-rp/bin/python -B -m pytest -q parser/tests --basetemp output/scratch-29/tests/full
```

Expected results, in order: encode 0 with L0 drops 1 and all other levels 0; new measured sha recorded; diff 0/confined/exact leaf list; live K1 0 with name_anchor 2,317,055 / 0; comparator 0; G witness 0/O03 absent and empty name set or explicitly listed residuals; R reader 0/empty covering frames; full tests/goldens pass (report skips explicitly). Execute must verify Perth `da13a775…`, record the measured successor pin, and update its owned provenance/OVERVIEW/3-90 notes. Protected discs and spool must remain untouched.

Deviations/known concerns: No heavy encode/K1/disc/spool/full-suite/Perth/golden reads or jobs ran here. Those gates remain actionable above. `rem01_k1_live.json` is a run log, not the per-kind report; the comparator follows its recorded `argv --out` to `output/scratch-14/p3/indep/rem01/k1_live.json`. Padding is necessary to satisfy byte confinement with the packed writer. No `_cenc.c` modification: plan 28's producer sha pin is unaffected. No commits; all changes left in the tree. No other deviations.

Contradictions with DESIGN: none. Phase 1's already-recorded source-vs-decoded latitude correction is preserved. Phase 2 measured outcomes are not claimed before Execute runs them.
