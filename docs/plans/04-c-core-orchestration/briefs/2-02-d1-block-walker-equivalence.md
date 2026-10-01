# Brief: 2-02 — D1 block walker and equivalence on goldens, G and R

Consumer: 2-03 (K1 core calls the walker-plus-decoder entry per block row band); the Phase 2 close (D1 gates K1).
Owned paths: `parser/kiwiw/_d1.c`, `parser/kiwiw/_d1.h` (extend), `parser/kiwiw/cenc.py` (D1 section only), `parser/tests/test_d1_equivalence.py` (new), `parser/tests/fixtures/d1_sample.json` (new, small), `docs/provenance.md` (one entry for the sample). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 2-01.
Runs alongside: nothing.
Tier: Sonnet.
Budget: 10 files to read, about 900 lines changed (about 450 C, 300 test, sample file), 80 tool turns. Past the budget: stop, commit what passes, report `over budget` with the handoff.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — D1 and Granularity contract bullets; Gates "Oracle changes" (the last sentence on R); Phase 2 Outcome (D1 half).
2. `parser/harness/walk.py` — `_block_base_bounds`, `_leaf_frame`, `_iter_tree_leaves`, `iter_parcels`, `iter_blocks` (the tree walk and per-leaf frame rule this unit moves to C).
3. `parser/kiwiw/parcel_mgmt.py` (101 lines, whole) — the record parser; `parser/kiwiw/mesh.py` lines 80-195 (`narrow_bounds`, `is_sparse_tile`, `leaf_frame_range`, `leaf_frame_shape`, `leaf_frame`, `sparse_memo`).
4. `parser/tools/quantisation_roundtrip.py` lines 832-880 (`_iter_leaves`): the exact per-block walk, row filter and error marker the checker uses; `parser/harness/checks/coord_scale.py` `_block_keys` and `_decode_block_parcels`.
5. `parser/kiwiw/_d1.h` and `_d1.c` as 2-01 left them; `parser/tests/test_d1_frames.py`.

Read ranges and grep; do not re-read a file already in context.

## Goal

D1 takes a block (or a row band of a block) of a disc and decodes its leaves in one C call, reproducing what `walk` + `decode_parcel` yield, so Python never loops over leaves; and prove D1 equals the Python decoders on goldens, G and a fixed R sample.

## Contract

Cited from `DESIGN.md`:

- Phase 2 Outcome (D1 half), verbatim: "D1 reproduces every field of the Python decoders on all goldens and on a fixed sample of R parcels covering all four sub-layers (a field-for-field equality test, one of the two permitted Python-oracle uses), and decodes R and G identically to the Python decoders."
- "**Granularity.** One C call per contiguous range of cells (build) or frames (decode/check)." A Python loop over parcels or leaves of a block is a violation (Python orchestration contract: "Perf-sensitive means: any loop whose trip count scales with the vertices, shapes, parcels, frames or cells of a full-AU disc").
- "R is the reference disc; D1 must decode R and G identically to the Python decoders on the equivalence set (Phase 2) before they are deleted."

Decisions this brief makes (do not reopen):

- The walker is in C. The entry takes a block descriptor (the tuple `walk`/`_block_keys` produce: level, block-set index, block index, bsx, bsy, blx, bly, file offset, length; plus the level's LMR fields it needs: `n_parcels_lat/lng`, `n_basic_map`, `n_ext_map`, grid, and the disc coverage, as a small fixed-width descriptor declared in `_d1.h`) plus a leaf row band `[rlo, rhi]` (the filter `_iter_leaves` applies on the leaf's cell row) and the mapped region. Python builds block descriptors once per level (bounded by blocks); the block key listing may stay Python (`_block_keys`, bounded by block count) only if you show its trip count is blocks, not leaves.
- The walker output per leaf: the 2-01 leaf-frame row (so 2-01's decoders run on it inside the same call) plus `leaf_path` (packed), `parcel_type`, the leaf slot bounds, the frame bounds, `frame_range`, `frame_class`, the cell (ix, iy) the checker needs, and a status. A block whose record does not parse yields one error-marker row exactly as `_iter_leaves` yields one (`leaf_path == ()`).
- Equivalence set (fixed, deterministic): (a) every frame of every committed golden (2-01 already covers frames; here also the golden spools' discs if a block-level path exists, else frames only); (b) a sample of G: a deterministic selection rule recorded in `d1_sample.json` (rule, seed, and the resulting (level, block key, leaf_path) list, at most about 400 leaves, covering every level present, all four sub-layers non-empty, L0 sparse tiles, divided parents and sub-parcels, and at least one frame with a name record and one with background polygons); (c) the same rule applied to R. Both skip when the disc is absent. The sample file is committed (small); the discs are not (add the `docs/provenance.md` entry saying how to regenerate the list from the rule).
- Decode of G and R "identically": the test decodes the sampled leaves through D1 (via the walker, per block) and through `walk`/`decode_parcel`, and compares all fields; it also compares whole-block leaf counts and error markers for a few complete blocks per level of each disc (not only sampled leaves).

## Changes

- Extend `_d1.c`: parcel-management-record parse (the layout `parcel_mgmt.parse_parcel_mgmt_record` reads), tree walk with `narrow_bounds` bound arithmetic (bit-exact doubles, same operation order), sparse-tile test and `leaf_frame_shape`/`leaf_frame_range` rules, row-band filter, then the 2-01 frame decode per leaf; all in one call per block band, buffers growing on "needs more space".
- `cenc.py`: `d1_blocks(...)` wrapper and stats (ranges = block-band calls; the counter must show calls == ranges planned).
- `test_d1_equivalence.py`, `d1_sample.json`, provenance entry.

### Keep untouched

Python `walk`, `mesh`, decoders (oracle). The build path and its gates.

## Done evidence

Write the equivalence test first; report before and after.

- `.venv-rp/bin/python -m pytest parser/tests/test_d1_equivalence.py parser/tests/test_d1_frames.py -q --basetemp=output/scratch-2-02/pytest` → fails before the walker, passes after, with the G and R cases RUN (report the pass count; a skip on G or R is `blocked`, not a pass).
- The report states the leaf counts compared per disc and per level, and that all four sub-layers and the three leaf classes (`leaf`, `l0_sparse_tile`, `divided_parent`) occur in the sample (print the counts from the test).
- One mutation (e.g. off-by-one in the sparse-tile test) makes the test fail naming a leaf; revert.
- D1 call counter equals the number of block bands planned in the test (assert it).
- `parser/tests/test_goldens.py`, `test_perf_inventory.py` pass.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it. Over budget: stop, commit what passes, put the handoff (done, not done, what you learned) in the report.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Machine facts

- Python is `.venv-rp/bin/python` from the repo root (`python` is not on PATH). gcc is required; `kiwiw/cbuild.py` builds `_cenc.so` on demand from `EXT_SOURCES`, content-hashed. Build flags (`-O2 -ffp-contract=off -fPIC`) are not to change: floating-point results must be bit-reproducible against Python.
- Plan 04 `DESIGN.md` Decisions 1-9 and Assumptions 1-5 are settled; do not reopen them. Workers are Sonnet; no Opus.
- Commit and push to `master` when done evidence passes (project `CLAUDE.md`), staging your owned paths by name. Never stage binaries, spools, discs, scratch, logs, compiled `.so` or test binaries.
- Scratch for your own files: `output/scratch-<brief number>/` with `TMPDIR` exported there; pytest `--basetemp=output/scratch-<brief number>/pytest`.
- Reference discs: R `/run/media/codyh/464210-8480/ALLDATA.KWI` (tests using it skip when absent); G `output/scratch-3-11/G/ALLDATA.KWI` (sha256 `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862`); spool `output/extract_timing/spool` (build_alldata's default spool is not it).
- One heavy job at a time: any full-AU build or `-j 12` run takes `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`. Pytest and small builds do not.
