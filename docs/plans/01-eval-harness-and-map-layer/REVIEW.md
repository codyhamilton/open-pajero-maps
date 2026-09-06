# Review — WP1 units 01, 02, 07

Reviewer: independent review agent (fresh context), following
`workflow:comprehensive-review`. Scope: only units 01 (reference container
data), 02 (harness core), 07 (extractor at country scale), as landed by
commits `e58b08f`, `1b9dedd`, `024ed7b`. Units 03–15 are not implemented
and are explicitly out of scope, per the run's own `IMPLEMENTATION.md`.

**Verdict: PASS_WITH_FOLLOWUPS**

Reviewed SHA: `024ed7b` (no fixes were needed; nothing was changed by this
review).

## Review shape

Single reviewer, three lenses: contract-and-correctness (per-unit brief
conformance and done-evidence), intent-and-assumptions (drift from
`docs/design/target-disc.md` and the plan's architectural rules —
harness-reads-only, build-never-reads-mounted-disc, determinism), and
failure-modes (what breaks silently). This is a small, well-briefed change
with disjoint file ownership per unit, so one focused pass was sufficient;
no cross-cutting risk justified parallel reviewers.

## Method

- Read `PLAN.md`, all three units' briefs, `IMPLEMENTATION.md`.
- Read the full diffs of `e58b08f`, `1b9dedd`, `024ed7b` (not just stats).
- Read `docs/design/target-disc.md`'s Grid contract, Copy-through
  management data, Determinism, and Evaluation/oracle sections and checked
  each unit's code against them line by line.
- Confirmed `parser/refdata/grid.json`'s level-12 LMR fields against
  `kiwiw.model.LevelMgmtRecord`'s field list (no key mismatch;
  `ReferenceGrid.to_level_mgmt_record` round-trips cleanly).
- Re-ran the full suite: `.venv-rp/bin/python -m pytest parser/tests -q` →
  **152 passed** (matches the reported baseline; no regression).
- Spot-checked the reference self-check claim with the disc still mounted
  at `/run/media/codyh/464210-8480`: `compare_disc.py --checks mht29`
  against the reference disc reproduced **PASS** in seconds (did not
  re-run the full 30-minute decode/pointers/shape self-check — no reason
  to distrust it; the fast mht29 check alone corroborates the container
  read path is wired correctly end-to-end).
- Checked brief 12 directly to verify the reported "expected, not a
  defect" judgment about `build_alldata.py` being left non-functional:
  confirmed — brief 12's owned paths and required changes explicitly
  include removing `_SYNTH_CELL_SIZES`, `_make_synth_grid`, and the
  disc-fallback path, and rewriting `build_alldata.py`'s CLI. The
  judgment is sound.

## Acceptance criteria reachable from units 01/02/07 alone

Most of the plan's listed acceptance criteria depend on units 03–15
(profile checks, byte-diff, spot-checks, vocabulary, name types, the
all-level assembler, the full build). Of the criteria stated in `PLAN.md`,
only these are reachable now:

| Criterion (paraphrased) | Status | Evidence |
|---|---|---|
| `compare_disc.py --reference ... --generated ...` prints a per-check table, writes a JSON report, exit 0 only when every applicable check passes; `--checks a,b,c` runs only those | **Met** | `parser/compare_disc.py` implements exactly this; reference self-check reported PASS/PASS/PASS/PASS at decode/pointers/shape/mht29, exit 0; spot-checked `--checks mht29` independently, PASS. |
| `--profile` reserved cleanly for unit 03 | **Met** | Prints "profile not implemented", exit 2, as specified. |
| Every parcel decodes through the existing decode path with zero errors; every BMT/pointer resolves; mfde entries 0..2 in-buffer, entries ≥3 absent-value-or-valid-sector | **Met (against `R` only; `G` not yet built)** | Verified on the reference disc itself (3,951,973 leaves, zero errors, zero pointer/poison failures). No generated (`G`) disc exists yet — that is units 08–15's job — so this criterion is proven only in the "harness correctly judges `R`" sense, not yet in the "harness judges a from-scratch `G`" sense. That gap is expected at this point in the plan, not a defect. |
| The harness imports only the parser's reading paths | **Met** | `grep -rn "synth\|alldata_writer\|_writer\|osm_to_" parser/harness/` → no matches; also enforced by `test_no_forbidden_imports`. |
| Build never reads the mounted disc (Grid contract) | **Met** | `kiwiw/grid.py` imports only `kiwiw.model` + stdlib; `TileGrid.from_reference()` in `osm_to_parcel_geometry.py` goes through `ReferenceGrid`, not the disc; `build_tile_grid_from_lmr` and the disc-path fallback are removed from the extractor. |
| One PBF pass feeding all levels, streaming, bounded memory, wrap-safe, documented full run | **Met** | Single `_GeomHandler` pass fans every way/node to all requested levels via `SpoolWriter`; full Australia PBF run completed (1:27:24, peak RSS ~9.7 GB, ~21 GB spool) with per-level progress lines; antimeridian wrap covered by `TestAntimeridianWrap` and `WAY_CROSS_180` in `test_extractor_scale.py`. |
| `LinkIdRegistry` resolves `(osm_way_id, ordinal)` | **Not reachable from these units** | Unit 10's job; the extractor here still tags links only with `osm_way_id` (no ordinal yet) — expected, not a defect, since `_make_road_link`/`LinkIdRegistry` are unit 10's owned surface. |
| `pytest parser/tests` passes with no regression; new tests cover the grid-data loader | **Met** | 152 passed (baseline 132 + 20 new across the three units); `test_grid_data.py` covers the loader per its own done-evidence list. |
| Build is deterministic (byte-identical across two runs) | **Met, for the extractor's spool output** | `test_iter_level_order_deterministic_byte_identical` byte-compares two independent `SpoolWriter` runs' `.data`/`.idx` files; `grid.json`/`mht29_frame.bin` re-extraction is asserted byte-identical via `git status --porcelain`. End-to-end `ALLDATA.KWI` determinism is not yet testable (no assembler yet). |

All other acceptance criteria (vocabulary subsets, count envelopes,
LMR/BSMR/BMT shape *of a generated disc*, container byte-diff, capacity
budget, full-Australia build completing end to end, close-out wall
time/size) require units 03–15 and are correctly out of scope here.

## Findings

### Low — harness layer-presence check duplicated (follow-up, non-blocking)

`parser/compare_disc.py`'s `main()` already returns `NA` for any check
whose `layer` isn't in `config["layers_present"]` before calling
`check.run(ctx)`. But `_run_decode`, `_run_pointers`, and `_run_shape` (in
`parser/harness/checks/decode.py` and `.../shape.py`) each independently
re-check `ctx.layer_present("map")` and return the same `NA`. This code
path is dead under the current CLI (the wrapper never lets it fire) but
is duplicated logic sitting in two places that could drift — e.g. a future
caller of `_run_decode` directly (as the tests already do) bypasses the
CLI's own gate and relies on the checks' internal one. Not a bug today;
worth collapsing to one place when unit 03+ add more checks.
**Follow-up, non-blocking.**

### Low — no early bbox short-circuit before per-level tiling (follow-up, non-blocking)

The previous extractor's `_GeomHandler._in_bbox()` skipped a way entirely,
before any tiling work, if none of its points fell in the target bbox.
The new streaming handler removed this: `split_polyline_by_parcel()` (for
roads) and the background/name centroid assignment now run unconditionally
for every way/node at every requested level (subject only to
`level_filter`, which defaults to always-true), with target-cell filtering
applied only *after* the tiling work is done. For the no-bbox (full
country) case this is essentially free since almost everything is in
coverage. But it means `--fixture perth` — the plan's explicitly-called-out
"fast iteration" fixture — no longer gets a cheap early skip when run
against the full Australia PBF: every road/background way in the country
is now fully tiled into every requested level before being discarded for
being outside the Perth cells, which is more expensive than the old
early-bbox-check path for that specific use case. This is a performance
regression against the "fixtures stay ... for fast iteration" intent
(`PLAN.md`, "Provenance Notes"), not a correctness regression — the brief
did not require preserving this optimization, and functional correctness
(each fixture still produces the right output) is intact and tested.
**Follow-up, non-blocking** — worth a cheap way-level bbox pre-check
(compare the way's own bounds against the union of all requested levels'
`target` bboxes) before calling `split_polyline_by_parcel`, if `--fixture`
iteration on the full PBF turns out to matter in practice; if all dev
iteration in fact uses smaller extract files, this may never bite.

### Low — `SpoolWriter._finalize_index` reads the whole spool twice (follow-up, non-blocking)

`_finalize_index()` does one full pass over a level's `.data` file to
build the offset index, then a second full pass (via `iter_level`-style
replay) purely to sum content-type totals. At the full-Australia scale
(~21 GB across 7 files) this roughly doubles the I/O cost of closing the
spool. Not incorrect — the reported run completed in 1:27:24 total — but
worth folding the totals computation into the first pass (accumulate
`len(content[key])` while building `by_key`) the next time this file is
touched. **Follow-up, non-blocking.**

No blocker, high, or medium findings. No structural findings requiring a
remediation brief.

## Intent and assumption-ledger assessment

- **Grid contract** ("a build never reads the mounted reference"): held.
  Verified by import-surface inspection of `kiwiw/grid.py` (imports only
  `kiwiw.model` + stdlib) and by `osm_to_parcel_geometry.py`'s removal of
  `build_tile_grid_from_lmr` and the `os.path.exists(DEFAULT_ALLDATA)`
  branch. The only code that still reads the mounted disc is
  `parser/extract_reference_data.py` (unit 01, run once, by design) and
  test-only cross-checks explicitly marked as such (`test_grid_data.py`'s
  disc-mounted, skip-when-unmounted test).
- **Harness reads only parser reading paths**: held, and enforced by a
  test (`test_no_forbidden_imports`), not just a convention. Good — this
  is exactly the kind of assumption a headless multi-worker run could
  silently violate, and it's the one place the plan called out review
  scrutiny explicitly.
- **Determinism**: held for what's buildable so far (spool output,
  `grid.json`/`mht29_frame.bin` re-extraction). Not yet testable end to
  end since there is no assembler.
- **Copy-through management data (record 29)**: held. `mht29_frame.bin` is
  extracted once, never regenerated, and the `mht29` harness check
  byte-compares it; spot-checked live against the mounted reference disc
  during this review, PASS.
- **Unit 07's reported contradiction** (removing `build_tile_grid_from_lmr`
  etc. leaves `build_alldata.py` non-functional until unit 12): checked
  brief 12 directly. Confirmed sound — brief 12 explicitly owns
  `build_alldata.py` and lists removing exactly those symbols
  (`_SYNTH_CELL_SIZES`, `_make_synth_grid`, the disc-fallback) as part of
  its contract. Not a defect; correctly not silently patched by unit 07.
- **Ownership discipline**: units 01/02/07 stayed within their owned-path
  lists with one minor, disclosed, justified exception each (unit 07
  edited `test_grid_data.py`, outside its owned list, to keep the suite
  green after removing a function that file depended on — reported in the
  commit message, not silently done, and the edit itself is a faithful
  local re-implementation of the removed helper for test-only,
  disc-mounted use).

No assumption-ledger entry failed. No drift from the plan's stated
architecture was found beyond the two low-severity, non-blocking items
above.

## Plan-sufficiency judgment

The plan and briefs were sufficient to build against and to review
against. Specifically:
- Each brief's "Owned paths" / "Do not touch" / "Depends on" / "Runs
  alongside" made file-ownership conflicts checkable mechanically (grep
  the diff against the owned-path list), and none occurred beyond the one
  disclosed, justified exception.
- Each brief's "Contract" section quoted the design doc and plan verbatim
  rather than paraphrasing, so drift was checkable by direct comparison
  (used above for the Grid contract, copy-through, and reading-paths-only
  rules).
- Each brief's "Done evidence" gave concrete, reproducible commands, which
  this review partially re-ran (mht29 spot check, full pytest run) rather
  than trusting blindly.
- The one place the plan structure showed friction was the "Report back:
  do not resolve contradictions silently" instruction interacting with a
  cross-file, out-of-scope breakage (`build_alldata.py`) — the brief
  system handled it correctly (unit 07 flagged it, didn't touch the file,
  and the report explains why brief 12 already owns the fix), but a
  reader of `IMPLEMENTATION.md` alone, without also reading brief 12,
  would not know whether the judgment "expected, not a defect" was
  verified or merely asserted. This review verified it by reading brief
  12; future runs might save a reviewer step by having the
  contradiction-reporting unit cite the owning brief by number when it
  can identify one (unit 07's report already does this correctly, in
  fact — "brief 12 ... already owns a full rewrite" — so this is really a
  compliment to note, not a gap to fix).

No plan or brief revision is needed as a result of this review.

## Residual risks

- **Peak RSS ~9.7 GB and ~21 GB spool for a from-scratch full-Australia
  extract** is a real resource number future units (especially 12, the
  assembler, and 15, the full build) need to plan around; it is recorded
  here and in `IMPLEMENTATION.md` but is not yet validated against the
  eventual 4.7 GB disc-capacity budget (that accounting is unit 15's job).
- **No generated (`G`) `ALLDATA.KWI` exists yet.** Every check this review
  verified was proven against `R` compared to itself; the harness's real
  test — judging OSM-derived output — is still ahead, starting once unit
  12's assembler exists. This is expected at this point in the plan
  (units 01/02/07 are container-data, harness-skeleton, and
  extractor-scale respectively — none of them produce `G`), not a gap in
  this review.
- **The two low-severity follow-ups above (fixture performance, spool
  double-read)** are real but do not block continuing to units 03–15;
  they're the kind of thing worth revisiting once the assembler (unit 12)
  makes end-to-end timing visible.

## Fixes applied in this review

None. No blocker/high/medium findings were found that required an
in-place fix; the two low-severity items above are recorded as
non-blocking follow-ups rather than fixed, since neither is a defect
against the units' actual contracts.
