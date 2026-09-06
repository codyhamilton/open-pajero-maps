# Brief: 12 — Assembler: all seven levels, reference LMR/BSMR/BMT shape, record-29 frame, wrap-safe coverage

Consumer: implementation worker.
Owned paths: `parser/kiwiw/alldata_writer.py`, `parser/build_alldata.py`,
`parser/tests/test_alldata_writer.py`, `parser/tests/test_build_alldata.py` (new). Do not
touch anything else (in particular not `synth.py`, the extractor, or the harness).
Commit to the current branch when done evidence passes; push.
Depends on: 01 (`ReferenceGrid`, `mht29_frame_bytes`), 06 (`DESIGN.md`), 07 (spool reader),
09 (Map Frame signature).
Runs alongside: 10, 11.

## Required reading, in order

1. `docs/design/target-disc.md` — **Grid contract**, **Copy-through management data**
   (record 29 byte-copied), **Determinism**, **Capacity accounting**; "Decisions that shape
   everything" 2 (no regional defaults, no silent disc fallback).
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Why This Plan Exists" gaps (2),
   (3), (4), (5); "Architectural Implications" bullet on `build_alldata_kwi`; Open Question
   **Anti-meridian coverage**; user-facing acceptance bullets 3 and 5 (no `--bbox`/`--levels`
   needed; no reference mounted; deterministic).
3. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` — sections 2–4, 6, 7.
4. `parser/kiwiw/grid.py` (unit 01: `to_level_mgmt_record(n)`, `mht29_frame_bytes()`),
   `parser/refdata/grid.json` (the per-level numbers: 7 LMRs at levels 12,10,8,6,4,2,0;
   lmr_size 170; blockset/block/parcel counts per level; n_basic_map 3, n_ext_map 9;
   n_basic_route 2 at levels 0 and 2 only; node_record_size 8; frame tables 16/32/16).
5. `parser/kiwiw/alldata_writer.py` (single level; `lon_span = lon_hi - lon_lo`;
   `LMR_BASE_SIZE = 40`), `parser/build_alldata.py` (`_SYNTH_CELL_SIZES`, `DEFAULT_LEVELS`,
   `os.path.exists(alldata_path)` fallback, `_make_synth_grid`).
6. `parser/kiwiw/volume.py` `parse_pdmdh` / LMR parsing, `parser/kiwiw/spool.py` (unit 07).
7. `parser/harness/checks/decode.py`, `shape.py`, `container.py` (what judges the output).

## Goal

`build_alldata.py` with no arguments reads the spool and writes an `ALLDATA.KWI` whose
container has the reference's structure at all seven levels, embeds the record-29 frame
byte-for-byte, and covers the reference's full box including the anti-meridian wrap.

## Contract

Settled by the design doc: grid and level records from checked-in data; record 29
copy-through at the reference's location (MHT entry 29: dsa 512, size 64 → bytes 4096..6144,
2048 bytes); determinism; no mounted-disc dependency. Settled here:

- `build_alldata_kwi(levels: dict[int, LevelBuild], grid: ReferenceGrid, *, disk_title,
  out_path)` replaces the single-level signature. Each `LevelBuild` supplies an iterator of
  `(ix, iy, map_frame_bytes)` in ascending `(iy, ix)`; the writer places parcels into the
  reference's blockset/block structure for that level (block and blockset indices computed
  from global cell indices via `grid.json`), writes one LMR per level (size 170: base 40 +
  frame tables 16/32/16 + the remaining fields `to_level_mgmt_record` supplies), 601 BSMRs
  laid out as `R` (all blocksets present; empty ones point at empty BMTs or `NO_DATA` —
  choose whichever `R` does for its empty blocksets and cite the profile), and BMTs for
  every non-empty block.
- Coverage: the reference box from `grid.json` (lat −50.0..35.3333, lon 90.0 → −142.0 with
  `lon_span` 128 across the wrap). Fix the span arithmetic so the writer accepts a box
  whose `lon_hi` < `lon_lo`.
- Parcel management records: type-0 parcels only in this unit; types 1..3 (`n_parcels`
  2×2 / 4×4 / 1×1) are written as empty in the form `R` uses for an unused divided type
  (unit 13 fills them). The writer takes an optional `divided` mapping so unit 13 can add
  them without changing the signature again.
- MHT: entry 0 (PDMDH), entry 29 (record-29 frame copied via `mht29_frame_bytes()`), the
  per-level map layer entries populated as `R` populates them; every other entry is the
  absent value, and the list of absent entries is written to the build's `manifest.json`
  (`layers_present`) so the harness config can be compared against it.
- `build_alldata.py`: defaults `--spool output/spool`, `--out output/ALLDATA.KWI`,
  `--levels 12 10 8 6 4 2 0`; `--fixture perth` restricts to the Perth cells at the same
  global indices (still the full container shape). Remove `_SYNTH_CELL_SIZES`,
  `_make_synth_grid` and the `os.path.exists(alldata_path)` fallback; if the spool is
  missing, exit non-zero with a message. Progress per level to stdout, line-buffered.
  Writes `manifest.json` beside the output: input spool stats, per-level parcel counts and
  byte totals, total size, and a SHA-256 of the output.

## Changes

- `alldata_writer.py`: multi-level PDMDH (LMR array, BSMR array, BMT tables) driven by
  `ReferenceGrid`; parcel placement; record-29 embedding; wrap-safe coverage; `NO_DATA`
  conventions per `R`.
- `build_alldata.py`: new CLI + `manifest.json`; remove disc fallback and synth grid.
- Tests: `test_alldata_writer.py` — a two-level build (12 and 0, three parcels each) decodes
  with `AllData` and `find_parcel` returns the right parcel at both levels; LMR count 7 and
  size 170; MHT entry 29 bytes equal `mht29_frame_bytes()` at byte 4096; a parcel at
  lon 179.9 and one at −179.9 both resolve; two builds byte-equal. `test_build_alldata.py` —
  running the CLI against a tiny spool (produced in-test by unit 07's writer) writes the
  file and manifest; missing spool → non-zero exit.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- Perth fixture end-to-end: `parser/osm_to_parcel_geometry.py --fixture perth --spool output/spool-perth` then `parser/build_alldata.py --spool output/spool-perth --out output/perth/ALLDATA.KWI`, then `parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/perth/ALLDATA.KWI --checks decode,pointers,shape,mht29,container,mfde` → `decode`, `pointers`, `shape`, `mht29`, `container` PASS; `mfde` PASS at every level; report each check's line.
- `.venv-rp/bin/python parser/build_alldata.py` (no args, spool from unit 07's full run present) completes; record wall time and output size. If the full spool is not present, say so. This is optional, best-effort evidence, not required for this unit's contract (unit 15/15b own the full-Australia build and its verification) — if you run it, start it in the background (`nohup ... & disown`), do one liveness check, and move on to your report-back rather than waiting on it. If it hasn't finished by the time the rest of this brief's done evidence passes, say so in your report and let it keep running or leave it; do not block your own commit on it and do not poll it in a loop.

## Report back

A short summary: the numbers above, the empty-blockset / empty-divided-type conventions you
matched, anything you deviated from in this brief and why, and any contradiction you found
between this brief, `DESIGN.md` and the contracts it cites. **Do not resolve contradictions
silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
