# Brief: 2-01 — route choice, counted out-of-span name drop, successor-oracle tooling

Consumer: Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`.
Owned paths:
- `docs/plans/29-k1-name-anchor-failure/` (new: `phase2_routes.md`, `diff_disc.py`, `compare_k1.py`, generated outputs);
- the route's code surface: **route (a)** `parser/build_alldata.py` and the encoder name-input path only as needed (`parser/kiwiw/cenc.py`, `parser/kiwiw/_cenc.c` name read); **route (b)** a tracked cell-scoped spool regeneration step writing **only** under `output/scratch-29/`;
- new tests under `parser/tests/`;
- `docs/plans/04-c-core-orchestration/triage/rules_other.json` (the O03 `note` string only).

`docs/provenance.md`, `docs/OVERVIEW.md` and the 3-90 brief / plan-27 notes are **not** yours: Execute updates them after the measured runs. Touch nothing else.
Commits: leave changes in the working tree. Execute commits.
Report: write `docs/plans/29-k1-name-anchor-failure/reports/2-01-drop-guard-successor-oracle.md` (rubric `/home/codyh/workspace/workflow-plugin/tools/quality/checks/execution-report.json`).
Depends on: Phase 1 (closed at `a08d342`, verdict A).
Runs alongside: nothing.
Budget: about 25 files to read, about 600 lines to change, 120 tool turns.

## Required reading, in order

1. `docs/plans/29-k1-name-anchor-failure/DESIGN.md`: Domain "fix or proven non-deviation", contract **verdict A**, Assumptions 2–5, Phase 2 **A** outcomes and "Both branches". **Binding.**
2. `docs/plans/29-k1-name-anchor-failure/IMPLEMENTATION.md` (Phase 1 record and Carried) and `phase1_witness.md`.
3. `parser/build_alldata.py` (`run`, `_encode_level`, `_e1_job`, the manifest), `parser/kiwiw/cenc.py` (`E1Spool`, name encode), and the `_cenc.c` name path and `to_xy` clamp.
4. `parser/osm_to_parcel_geometry.py` `assign_to_parcel` and `parser/kiwiw/mesh.py` twin (the plan-18 coverage contract), plus `docs/plans/18-name-anchor-l0-extractor.md`.
5. `parser/tools/quantisation_roundtrip.py`: the name_anchor check; `parser/tests/test_k1_points.py`, `test_quantisation_roundtrip.py`, `k1_fixtures.py` (for a positive control).
6. `output/scratch-14/runs/rem01_k1_live.json` (read-only baseline per-kind totals).
7. `docs/plans/29-k1-name-anchor-failure/witness_p1.py` `disc_cells` (bounded leaf/frame locator, reusable for diff mapping).

## Goal

Make the generated disc stop carrying the O03 name, using a counted, contract-based route with no silent clamp. Then build the tooling that proves the successor disc's change is confined to that item and that K1 exits 0 with every other kind unchanged.

## Contract

The DESIGN verdict-A contract is settled:
- The drop count per level must equal Phase 1's prediction: exactly **1 at L0**, 0 elsewhere. Any extra drop fails, or is root-caused.
- Route (c), a full re-extract, is rejected.
- No K1 tolerance change. Any K1 change is counted, rule-documented and positive-controlled (Assumption 5).
- The new disc goes to `output/scratch-29/G_new/ALLDATA.KWI`. Both `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`) and `output/scratch-3-11/G_new/` (`013586b5…`) stay byte-untouched, and the spool `output/extract_timing/spool` stays byte-untouched.

## Changes

- **`phase2_routes.md`:** a short divergent-candidate comparison of (a) a counted assembly drop guard on the in-force spool versus (b) cell-scoped spool regeneration. Score both against the Phase 2 outcome on: spool protection, provenance, confinement, future re-extract behaviour, Perth/goldens risk, and test surface. Pick one. Record the rejected alternative's reason.
- **Implement the chosen route.**
  - For (a): the guard applies the plan-18 coverage contract, meaning names whose anchor lies outside the disc lattice span are not encoded. Per-level counts land in the build manifest and stdout. Default on, no flag needed for the AU build. Prefer the narrowest surface that is honest. If you must touch `_cenc.c`, say so: it changes `_cenc.c`'s sha, which plan 28's producer pins as `5c43e00d…` for its O06 contract proof. Record that impact in the report.
  - For (b): write only under `output/scratch-29/`, and never write the in-force spool.
- **Tests:**
  - (i) the guard drops a synthetic out-of-span name, counts it, and leaves in-span names byte-identical;
  - (ii) a **K1 positive control**: a missing or misplaced in-span name still fails name_anchor (cite an existing test if one already proves this, otherwise add one);
  - (iii) the existing Perth fixture / golden tests still pass.
- **`diff_disc.py`:** a streamed, chunked (≤ 8 MiB) byte compare of two discs, plus a mapping of every differing byte range to its structure (header, PDMDH, BMT/block slot table, frame with level/cell/leaf). It writes a JSON with the changed ranges, the changed-leaf list, and a boolean `confined_to_cell_0_541`, with the exact rule stated. It must use the guard argv form, with no whole-file reads.
- **`compare_k1.py`:** compares a new K1 report to `rem01_k1_live.json` per kind and per level. It asserts name_anchor failing 0, name_anchor checked = baseline − drops, completeness 1,800,514 / 0, every other kind identical, and states the expected K1 exit.
- **`rules_other.json` O03 note:** state the disposition: dropped by the chosen route on the in-force spool; successor oracle sha "see plan 29 record". Execute fills in the measured sha later, so leave a clear token.

### Keep untouched

- Everything outside the owned paths; the protected discs and the spool (read-only).
- Do not run `build_evidence.py`, `verify_evidence.py` or unverified scripts.

## Heavy-run rule (binding)

You may run:
- unit tests that build tiny synthetic inputs in a temporary directory under `output/scratch-29/tests/`;
- `--help` of your own argparse scripts.

You must **not** run any encode, K1, disc/spool read or full test suite. Put in the report the exact ordered commands for Execute, each in the form `.venv-rp/bin/python -B parser/tools/run_heavy_python.py --log output/scratch-29/runs/<name>.json -- .venv-rp/bin/python -B …`:
1. the encode at `-j4` to `output/scratch-29/G_new/ALLDATA.KWI`;
2. the sha;
3. `diff_disc.py` against `output/scratch-14/G_new/ALLDATA.KWI`;
4. live K1 at `-j6` with `--engine c` against `output/extract_timing/spool`, no dumps;
5. `compare_k1.py`;
6. the R parity re-run of `witness_p1.py g-witness/r-witness` on the new disc, adding `--disc`/`--out` options if needed, with outputs to new filenames so Phase 1 witnesses are preserved;
7. the full parser test command.

## Done evidence

- New tests fail before the change and pass after; the targeted suites pass.
- `phase2_routes.md` names the pick and the rejected route.
- The report lists the ordered heavy commands with expected results.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then:
- what changed;
- the check output before and after;
- the heavy command list;
- deviations;
- contradictions with DESIGN.

Do not spawn agents beyond read-only research helpers.
