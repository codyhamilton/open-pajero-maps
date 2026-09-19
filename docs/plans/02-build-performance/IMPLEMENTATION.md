## Run
- Tool: Claude Code
- Session/Run ID or session URL: https://claude.ai/code/session_01MPpkVMTLi6P51G9YCawPr5
- Started: 2026-09-19T04:10:03Z

Execution shape: no briefs (refine not run); phases executed sequentially by the orchestrator directly (strict phase dependencies, shared files).

## Phase 0 — Baseline and bench harness (done)
- Determinism at HEAD confirmed: two concurrent Perth builds under `PYTHONHASHSEED=7` and `14` produce identical sha256.
- **Perth baseline sha256** `e275879fe2266da471826250f1daffb7907e64ed4783bffa6d2229c92ac480ca` (29,708,672 B); wall 145–154 s, peak RSS ~260 MB (Perth, HEAD eea3fe8).
- Full baseline unchanged: `51c254ac…2743`, 1,397,923,200 B (from `output/manifest.json`).
- Added `parser/tools/bench_build.py` (wall + process-tree peak RSS sampled from /proc; JSON record separate from manifest).
- Added `build_alldata.py --frame-digest PATH` (per-frame sha256 listing keyed level/ix/iy/type/sub_ix/sub_iy). Perth listing (167 KB, 1943 frames) is committed as `baseline-perth.digest` in this plan folder (small enough to commit; deleted at close-out).
- numpy 2.5.3 installed in `.venv-rp`; recorded in `docs/provenance.md`.

## Phase 1 — streaming assembly (done)

- Built: `parser/kiwiw/spill.py` (`FrameSpill`/`FrameRef`), `AssembledFile` + streamed
  seek-write path in `alldata_writer._build_alldata_kwi_multilevel(return_bytes=False)`,
  `--frame-digest` flag and spill wiring in `build_alldata.py`. Test:
  `test_streaming_matches_bytes_path`.
- Perth: byte-identical (`e275879f…80ca`), sorted frame digest equals baseline.
- Full Australia: sha256 `51c254ac…2743` (matches baseline), **peak tree RSS 1,820 MB**
  (baseline 6.85 GB; target ≤ 3 GB met). Wall 805 s — measured while other jobs
  (test suite) shared the machine, so not a clean timing; Phase 5 re-measures.
- Deviation: none.

## Phase 2 — binary columnar spool (done)

- Built: `parser/kiwiw/spool.py` rewritten (little-endian fixed-width columns, `.data` per
  level sorted `(iy, ix)`, `.idx` = magic + totals + ix/iy/offset/length arrays; writer
  appends `.seg` partial records and merges them at `close()`). Public API unchanged
  (`SpoolWriter.add/close`, `SpoolReader.iter_level/stats/levels`); added `iter_cells`,
  `iter_cell_columns`, `cell_keys`, `n_cells`. Old format kept as `spool_legacy.py`.
  `parser/tools/convert_spool.py` converts pickle → binary and checks per-level stats.
  `parcel_occupancy.py` migrated to `SpoolReader.cell_keys`. Tests: `test_spool_binary.py`
  (dataclass equality vs legacy over all fields except `raw_*`, flush-threshold
  independence, determinism, converter). Full suite 285 passed.
- Real spool: converted in 280 s (one-off; converter peak 5.8 GB RSS), 6.9 GB → 4.5 GB, stats
  equal for all seven levels.
- Full Australia from converted spool: sha256 `51c254ac…2743` (matches), peak tree RSS
  1,854 MB, wall 771 s (co-load noise; decode was not the bottleneck — encode is).
- Finding: an mmap-backed reader put peak RSS at 6.67 GB (mapped file pages count as RSS);
  switched to per-cell `os.pread`, which restored 1.85 GB.
- Deviation: the "Record phase 1" commit also swept in the Phase 2 source files.

## Phase 3 — vectorized encoders (done, background shapes only)

- Profile (level 2, 231k cells): background-shape encoding was 58% of build time
  (`encode_background_shape_bytes` 47 s of 81 s), dominated by per-point `latlon_to_xy` +
  `_clamp_coord` calls. Roads (~8%), frame assembly (~12%) and spool decode (~6%) are small.
- Built: `synth._bg_fast` — vectorized pixel conversion (same float op order as
  `latlon_to_xy`; `numpy.rint` == half-to-even `round`), first-difference deltas when the
  accumulator provably tracks, otherwise an inlined integer accumulation loop over the
  clamped pixels. Scalar encoder retained as `encode_background_shape_bytes_scalar` (oracle).
  Fuzz test `test_synth_vectorized.py` (4000 shapes incl. saturating deltas, mult_const > 1,
  out-of-bounds clamping, half-pixel ties).
- Measured level 2: 81 s → 54 s (1.5x overall; background encode 47 → 19 s), output `cmp`-identical.
  Above the 1.3x keep threshold. Road/name encoders left scalar: gains are small next to
  process-level parallelism (phase 4).
