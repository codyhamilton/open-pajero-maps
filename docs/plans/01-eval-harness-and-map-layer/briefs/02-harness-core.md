# Brief: 02 — Harness core (walker, decode/pointer/shape checks, CLI, report)

Consumer: implementation worker.
Owned paths: `parser/harness/` (new package: `__init__.py`, `walk.py`, `context.py`,
`report.py`, `registry.py`, `checks/__init__.py`, `checks/decode.py`, `checks/shape.py`),
`parser/compare_disc.py` (new), `parser/refdata/harness.json` (new),
`parser/tests/test_harness_core.py` (new), `parser/tests/fixtures/` (new, small synthetic
files only). Do not touch anything else — in particular nothing under `parser/kiwiw/`.
Commit to the current branch when done evidence passes; push.
Depends on: 01 (uses `kiwiw.grid.ReferenceGrid` for the expected per-level shape).
Runs alongside: 07 (extractor scale) — disjoint paths.

## Required reading, in order

1. `docs/design/target-disc.md` — "Evaluation: the offline oracle": the check table and the
   paragraph after it (PASS/FAIL/N/A, applicability, config lists which files/layers exist in
   `G`) are binding.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Acceptance Criteria", the first
   two user-facing bullets (CLI shape, exit code, `--checks`, `--config`, `--profile`) and
   the non-user-facing bullets on decode, pointers and LMR/BSMR/BMT shape. Also
   "Architectural Implications", last bullet: the harness imports only the parser's
   *reading* paths.
3. `parser/kiwiw/alldata_writer.py` — `load_region`, `_walk_tree`, `_block_base_bounds`,
   `_narrow_bounds`: the only existing exhaustive traversal. You will reimplement the walk
   (streaming, all levels) rather than import this module, because `alldata_writer` is a
   writer module and the harness must not depend on writers.
4. `parser/kiwiw/parcel.py` — `decode_parcel` docstring (mfde table length rule, in-buffer
   vs out-of-buffer entries, `ext_frame_raw`, `tail_raw`).
5. `parser/kiwiw/parcel_mgmt.py`, `parser/kiwiw/volume.py`, `parser/kiwiw/mesh.py`.
6. `parser/kiwiw/grid.py` (unit 01).

## Goal

Deliver the comparison harness's skeleton: a streaming whole-disc walker, the decode /
pointer / container-shape checks, the check registry, the report and the `compare_disc.py`
CLI. Later units add the profiler, byte-diff and spot checks as plug-in modules without
editing this unit's files.

## Contract

Check definitions are the design doc's table, verbatim. This unit implements:

- **Decodes clean**: "Every structure in `G` is parsed by the project parser with zero
  errors, using the same code paths that parse `R`."
- **Pointers resolve**: "Every offset/sector/index pointer in `G` lands inside its target
  table or buffer, or (for pointers that on `R` reference another layer, e.g. mfde entries ≥3)
  carries the absent-slot value censused from `R` or a valid in-file sector; no `0xA5`
  poison, no out-of-range."
- The LMR/BSMR/BMT shape part of **Profile envelope** as the plan's acceptance criterion
  states it: "Per level, the generated LMR/BSMR/BMT shape (block-set, block and parcel
  counts, cell sizes, coverage box) equals the reference's." Shape means dimensions and
  coverage from `grid.json`, not which blocks are occupied.

Settled decisions (refine's calls under the plan's "refine decides" clauses):

- Module tree: `parser/harness/` package; `parser/compare_disc.py` is a thin CLI over it.
- The harness may import `kiwiw.volume`, `kiwiw.parcel`, `kiwiw.parcel_mgmt`,
  `kiwiw.mesh`, `kiwiw.disc`, `kiwiw.model`, `kiwiw.bitutils`, `kiwiw.coordconv`,
  `kiwiw.roadtypes`, `kiwiw.grid`, and the sub-frame decoders. It must never import
  `synth`, `alldata_writer`, `*_writer`, or `osm_to_*`. Enforce this with a test.
- Config file: `parser/refdata/harness.json`, the committed default; `--config` replaces it.
- Reference profile path (consumed by unit 03): `parser/refdata/profile/<layer>.json`.

## Changes

### `parser/harness/walk.py`

`iter_parcels(path) -> Iterator[WalkedParcel]` over every level, block set, block and leaf
of an `ALLDATA.KWI`, in on-disc table order. `WalkedParcel` carries: `level`,
`blockset_index`, `block_index`, `parcel_type`, `leaf_path` (tuple of mapinfo indices from
the block root), `bounds`, `file_offset`, `length`, `parcel` (the decoded `Parcel`, or
`None`), `error` (exception text, or `None`). Decoding happens inside the iterator, one
leaf at a time; nothing is retained. Also expose `read_container(path)` returning the
header, extras, MHT and full PDMDH (the same reads `load_region` does, without any level
filter) and `iter_blocks(path)` yielding each block's parsed `ParcelMgmtRecord` with its
BMT coordinates. Reference level 0 has 1836 non-empty blocks; the walk must not hold
decoded parcels in memory and must print a progress line per level (and per 200 blocks at
level 0) with `flush=True`.

### `parser/harness/context.py`, `registry.py`, `report.py`

`Context`: `reference` (path or `None`), `generated` (path), `config` (dict), `profile`
(lazily loaded per-layer dict from `parser/refdata/profile/`, `None` if a layer file is
absent), a memoised `walk_summary(path)` so several checks can share one traversal. A check
is `Check(id, layer, description, run)` where `run(ctx) -> CheckResult(status in
{"PASS","FAIL","NA"}, message, details: dict)`. `registry.discover()` imports every module in
`parser/harness/checks/` and collects its module-level `CHECKS` list; ordering is by module
name then list order. A check whose `layer` is not listed in `config["layers_present"]`
returns `NA` without running. `report.py` prints the table (`id`, status, one-line message)
and writes the JSON report (`{"generated", "reference", "checks": [...]}`) to `--report`
(default `output/compare_report.json`).

### `parser/harness/checks/decode.py`

`decode`: walk `G`; FAIL if any leaf's `error` is set or any block fails
`parse_parcel_mgmt_record`; details hold per-level parcel counts and the first 20 errors.
`pointers`: for every BMT entry and every mapinfo leaf entry, `getsector` result plus
length must lie inside the file; every mfde entry 0..2 must be 0xFFFFFFFF/0 or resolve
inside the parcel buffer; entries ≥3 must be the absent value from the profile
(`profile["map"]["mfde"]["absent"]`, default `[4294967295, 0]` when no profile is present)
or, when in-buffer, resolve inside the buffer, or, when out-of-buffer, decode to a sector
inside the file; any `0xA5` run of ≥ 32 bytes inside a parcel buffer's declared extent that
is not inside a sub-frame is a FAIL (poison leak).

### `parser/harness/checks/shape.py`

`shape`: compare `G`'s PDMDH against `ReferenceGrid`: coverage box (exact on the
sexagesimal-decoded floats within 1e-9), `lmr_size`, level list and order, per-level
blockset/block/parcel counts (all four parcel types), `n_basic_map`, `n_ext_map`,
`n_basic_route`, `n_ext_route`, `node_record_size`, frame-table lengths, `n_bsmr`, and the
volume header's coverage. `mht29`: the 2048 bytes at MHT entry 29 of `G` equal
`ReferenceGrid.mht29_frame_bytes()`; NA when `G`'s entry 29 is the sentinel and the config
says the layer is absent.

### `parser/compare_disc.py`

Arguments: `--reference <disc root or ALLDATA.KWI>`, `--generated <dir or ALLDATA.KWI>`,
`--checks a,b,c`, `--config <json>`, `--report <json>`, `--profile` (reserved for unit 03:
until then, print "profile not implemented" and exit 2). Exit 0 only when every non-NA check
is PASS. `--generated` is required unless `--profile`.

### `parser/refdata/harness.json`

`{"layers_present": ["map"], "envelopes": {"count_ratio": [0.5, 2.0]},
"level0_count_exempt": true, "container_allowlist": [], "spot_checks":
"parser/refdata/spot_checks.json"}`. Units 03–05 add keys; they do not change these.

### Tests and fixtures

`parser/tests/fixtures/` may hold only files you generate in the test itself or tiny
committed synthetic files (< 64 KB). Build a small `ALLDATA.KWI` in-test with
`alldata_writer.build_alldata_kwi` (tests may import writers; the harness may not) and run
`decode`, `pointers`, `shape` on it: `decode` PASS, `shape` FAIL (single-level flat file
does not match the reference shape — this is the expected negative control until unit 12).
Corrupt one mfde offset in a copy and assert `pointers` FAIL. Add a test that greps
`parser/harness/` for forbidden imports.

## Done evidence

- `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated /run/media/codyh/464210-8480/ALLDATA.KWI --checks decode,pointers,shape,mht29` → all four PASS, exit 0 (the reference passes its own harness). Record the wall time in your report.
- `.venv-rp/bin/python parser/compare_disc.py --generated output/ALLDATA.KWI --checks decode` on any current build → runs and prints the table (PASS/FAIL both acceptable).
- `grep -rn "synth\|alldata_writer\|_writer\|osm_to_" parser/harness/ --include=*.py` → no matches.
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.

## Report back

A short summary: what you changed, the reference self-check wall time and per-level parcel
counts, anything you deviated from in this brief and why, and any contradiction you found
between this brief and the contracts it cites. **Do not resolve contradictions silently —
report them.**
