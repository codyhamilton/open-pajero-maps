# Plan 67 — implementation log

Seat: operator on codyh-ubuntu, master direct; reviews on OpenCode DeepSeek Flash until 22:20 (CHM seat change 19:21), Codex after. Draft re-copied fresh from the box `/workspace/maps-design-drafts/67-l0-edge-coincident-128-rc/DESIGN.md` (2026-10-09 17:53 AEST, sha256 `2ccd06b3…`). Ground tip `4bb96f0`; working tip `451cf60` (`git log 4bb96f0..451cf60 -- parser/kiwiw/_e2.c parser/tools/bg_producer_scan.py` empty: encoder and clip-geometry code unchanged). Live oracle `0c22b266…`, Perth `5b86d33e…`.

**Dependency check (operator, 17:23 / 17:53):** the draft does not depend on R-G5-6 or plan 68 Phase 3/4 (roads at L0, not background dedup). **R reader:** plan 63's truncating cut `frame[:U16(frame,0)*2]` is not used by this plan; every R read here is whole-entry (plan 48 `RReader` / `r_parent` reads `entry.size * ls` bytes; plan 68 `reader_audit.py` showed the cut drops every R record).

Heavy runs: none started before the plan-68 rerun completed (operator 17:53); every disc read, census run and unit-test run under flock + `run_heavy_python.py --memory-max 12G`. Early-commit note: `DESIGN.md`, the Refine notes and a first `census.py` landed early in plan 68's close-out commit `e2afb29` (`git add -A docs`); content unchanged by that, reported to Design.

## Phase 1 — Refine (light; committed files only)

1. **Open question 1 (plan 53 generator):** not recoverable. `rg --no-ignore` over `output/` (all scratch), `/home/codyh/workspace`, `/tmp`, `/var/tmp` for `parents_outside|outside_by_edge` in `*.py`: no hit. P53 is reconstructed (Assumption 1). The `aeae426c` disc is still on the box: `output/scratch-50/G_new/ALLDATA.KWI` (manifest sha256 `aeae426cc62b…`), read-only; this plan does not delete it.
2. **Open question 2 (`lpath`):** `lpath = (slot, sub)` from the parcel-management tree walk (`oracle_chain.tree_leaves`): element 0 is the slot index of the L0 parent inside its block root record (sample values 521 / 553 / 650 / 681 are block-slot ordinals, not codes); element 1 is the sub-leaf index `i` of the divided parent's sub-record, with `x = i % nx`, `y = i // nx` — the same `c = sy·nx + sx` as `dv_assign` and `leaf_clip_geometry`. `nx = 1 + n_parcels_lng[sub-record parcel_type]` (2 for type 1, 4 for type 2). In `census.json` every sample record has `leaf == lpath[1]`.
3. **P53 predicate (to reproduce, then fix if it does not):** per decoded L0 road link of a divided leaf, parent-raw vertices (0…4096, y-up); "on parent edge" = every vertex has x ∈ {0, 4096} or y ∈ {0, 4096}; "outside leaf rect" = not every vertex inside the leaf rect `[sx·4096/nx, (sx+1)·4096/nx] × [sy·…]` (closed); by-edge class = set of parent edges the vertices lie on (E: x=4096, W: x=0, N: y=4096, S: y=0). Variants (nx from parcel_type vs fixed 2; rect closed vs half-open; `cr` 4096 vs slot frame range) are run side by side and the one that reproduces 5,969 (by-edge 5,871 / 39 / 26 / 29 + corners 2/1/1) on `aeae426c` **and** 128 on `0c22b266` is P53. Inside-rect (27) and coincident-not-on-parent-edge (209) on `aeae426c` are reproduced too.
4. **PE:** leaf rect from the committed `bg_producer_scan.leaf_clip_geometry(level, ix, iy, path, ptype, cell_b4)`; unit test drives the compiled `dv_assign` (via a ctypes harness on `_cenc.so`, not a re-implementation) on synthetic points on each edge / corner and epsilon past (closed east / open north per `_e2.c` L465–481 at tip).
5. **Hypothesis note for Phase 2:** `dv_halo` (`_e2.c` L1081) is `_halo_candidates` + `_add_name_halo` — it adds **names**, not road links. H3 (halo) can therefore only hold if a link record is shown to come from a halo path; Phase 2 checks it per link rather than assuming it away.
6. **R side:** R's L0 is mostly sparse shared 4×4-tile frames (plan 68: 231,300 alias frame addresses at L0); R parity per link reads R whole-entry through plan 48's reader and records alias status explicitly.
7. **Ledger:** `docs/plans/56-cross-phase-rss-profile/ledger/l0_edge_plan67.json`.

## Phase 1 — outcome (2026-10-09 19:32–20:10 AEST)

**Generator:** `l0_degen/census/census.py` (whole leaf entries through plan 48's `RReader` + `decode_parcel`; not plan 63's truncating cut). Per divided L0 leaf, every road link in frame-raw (the leaf frame's own range; all 2,656 divided-leaf frames have range 4,096) and parent-raw (lon/lat vs the parent slot bounds × 4096, y-up); the two agree on every recorded link. Variant grid: shape (coincident / all_on_edge) × coords (frame / parent) × nx (ptype / two / four) × rect (closed / flip / halfopen / assign). PE = `bg_producer_scan.leaf_clip_geometry` rect (nx from parcel_type, `cr` from `mesh.g_frame_range`), closed. `tsv.gz` holds every link with all vertices on a parent edge (any variant), with full vertex lists, `pe_rect`, `pe_outside`, edges and the variants flagging it outside.

**Reproduction gate — P53 found, exact.** Runs: `p1.sh` (shape × coords × nx∈{ptype,two}, closed) → no variant matched (closed/ptype: 5,841 on `aeae426c`, 0 on live; the 128 deficit = exactly the 155 − 27 "inside" links). `p1b.sh` added rect variants (flip came closest: 5,996 / 155, still +27). Offline on the `p1b` rows, a **fixed 4×4 division for every parent** reproduced both totals; `nx='four'` was then added to the generator and the full grid re-run (`p1c.sh`, runs A and B). `p53_check.py` → `p53_reproduction.json` (`3f0e7021…`), `all_equal: true`:

| | P53 = coincident / frame / **four** / closed | plan 53 recorded |
| --- | ---: | ---: |
| `aeae426c` outside | 5,969: E 5,871 / N 39 / S 26 / W 29; (E,N) 2, (E,S) 1, (W,N) 1 | same |
| `aeae426c` inside / coincident-not-on-edge | 27 / 209 | 27 / 209 |
| `aeae426c` links / divided parents / parents outside | 569,300 / 560 / 534, per-parent counts identical to `parents_outside` | same |
| `0c22b266` outside | **128**: E 32 / N 39 / S 26 / W 29; (E,N) 1, (W,N) 1 | same |
| `0c22b266` links | 563,528 | 563,528 |

- **What P53 is:** "coincident" = every vertex of the link identical (degenerate links of 3–28 identical vertices); "on parent edge" = that point has x or y ∈ {0, 4096}; "outside" = not in the closed rect of cell `lpath[-1]` of a **4×4** grid. Plan 53's generator divided every parent 4×4, including the 2×2 (`parcel_type` 1) parents.
- **Restored on live** (not recorded by plan 53 after the fix): P53 inside 27, coincident-not-on-edge 209, 110 parents with an outside link, 560 divided parents.

**PE on live (`census_live.json`, `a1912526…`):** 264 links have every vertex on a parent edge (155 coincident + 109 not); **all 264 are inside their own leaf rect; 0 outside.** Every one of the 128 P53 links is in a `parcel_type` 1 (2×2) parent (leaf 0/1/2/3: 16/35/31/46) and is PE-inside (`pe_outside` false for 128/128). On `aeae426c` PE has 5,842 outside (5,841 coincident, 1 not; E 5,840, (E,N) 1, (E,S) 1): the pre-fix east-edge lon-wrap set plan 53 fixed. The 20 committed `census_after.json` sample records all match a P53 row (point, leaf, vertex count).

- This is the Ground item 5 lead (20/20 inside with nx=2), now measured on all 128 links with `nx` from the record's parcel_type: H0 (predicate artefact) is the Phase 2 candidate for every link. It is **not** the per-link outcome yet: Phase 2 still owes the independent decode, the spool way behind each link, `dv_assign` per vertex and R parity (in particular: why E2 emits degenerate, all-identical-vertex road links on parent edges, and whether R carries the same).
- `osm_way_id` is null on every row: decoded D1 links carry no spool id. The spool way per link is a Phase 2 evidence field (`rc_table.json`), not a Phase 1 output.

**`dv_assign` test:** `parser/tests/test_l0_edge_dv_assign.py` + `parser/tests/fixtures/l0_edge/probe_dv.c` (compiles `_e2.c` with `_cenc.c` / `_e1.c` and calls the encoder's static `dv_assign` with `dv_tier_setup`'s sub-grid set-up; not a re-implementation). 2×2 and 4×4: cell centres = `leaf_clip_geometry` rects; south / west edges in; **north edge → −1 (half-open)**; **east edge → last column (closed)**; ε past east → −1 (no wrap, plan 53); NW / NE corners −1; interior boundaries go to the east / north cell while closed rects hold them in both. 8 passed, with `test_bg_producer_scan.py` (12) 20 passed (`cd parser && pytest`, under the wrapper).

**Double run:** runs A and B on both discs: `tsv.gz` byte-identical, `json` identical minus `wall_s`.

**Committed:** `census/census.py`, `census/p53_check.py`, `census_live.{json,tsv.gz}` (0c22b266; `a1912526…` / `7ef223ed…`), `census_p53_aeae426c.{json,tsv.gz}` (`78d9c472…` / `e50c653e…`), `p53_reproduction.json` (`3f0e7021…`); the test + probe; ledger `l0_edge_plan67.json`.

**Peaks (wrapper, 12G cap):** `p1.sh` max RSS 75,192 KiB / memory.peak 762 MB incl. file pages, 111 s; `p1b.sh` 89,476 KiB / 84 MB, 123 s; `p1c.sh` (A+B, check, test attempt) 98,308 KiB / 93 MB, 273 s; `p1d.sh` (pytest) 71,252 KiB / 94 MB, 2 s. `p1c.sh` exited 1 at its pytest step (run from the repo root: `kiwiw` not importable); re-run from `parser/` as `p1d.sh`, passed. Lock waits: `p1.sh` queued 19:32 behind another lane's job, `p1d.sh` ~4.5 min.
