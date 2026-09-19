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
