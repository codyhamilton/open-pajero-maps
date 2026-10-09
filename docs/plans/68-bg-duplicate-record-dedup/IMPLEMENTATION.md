# Plan 68 — implementation log

Seat: Codex on codyh-ubuntu (master direct). Draft re-copied fresh from the box `/workspace/maps-design-drafts/68-bg-duplicate-record-dedup/DESIGN.md` at start (2026-10-09 ~15:45 AEST, sha256 `f6372e2a…`). Base: `origin/master` `c5d329c` (plan 64 close-out; the draft grounds at `61d2fe8`, and `61d2fe8..c5d329c` touches docs and triage tools only, no encoder change). Live oracle AU `0c22b266…`, Perth `5b86d33e…`, both built from `output/scratch-50/spool_overlay` (manifest `output/scratch-53/G_new/manifest.json`).

Hard stop: Phase 4 gate summary → report for Design accept before any oracle promotion.

## Phase 1 — R-side truth on a committed sample; R-G5-4-a-1 (in progress)

### Refine (fixed before any R read)

1. **Emitters on live (Assumption 4).** Plan 63's `sidecar_33006aa.patch` applies unchanged at tip (`git apply --check` clean; `_cenc.c` / `_e2.c` last changed by plan 53 `afce673`). Throwaway worktree `../open-pajero-maps-68-sidecar` at `c5d329c` + patch. Because a full AU encode is ~30 s at `-j4` (plan 53 ledger), the sidecar is run on the **whole of AU and Perth**, not a window sample. Output-neutral gate: full-disc sha256 equal to `0c22b266…` / `5b86d33e…`. Per-copy emitters are then national, and the plan-63 rule is re-checked on every duplicate class, not a sample.
2. **Census tool** `p10_bg_dedup/census.py`: plan-63 duplicate definition (class>0, same type, byte-identical, distinct frames, alias slots read once); per copy (record index, class, merged ordinal, source kind / cell / shape k) from the sidecar (W lines for whole cells, F+P for divided sub-cells, frame matched by FNV hash and record count / class sequence). Rule check per class: copies in leaf order strictly increasing in merged ordinal and in (class, own-first, source iy, ix, k).
3. **R reader (open question 1).** Plan 48's: `overlay_test.RReader` + `r_neighbours.LeafIndex` + `decode_parcel` (as `trim_witness.r_parent`), used identically on the G disc so both sides decode through one path; wire bytes via plan 63's `leaf_all_records`.
4. **Sample strata (G-side only).** (level, type, copies 2 | 3+, depth 1 | 2+, emitter form cover | ring | mixed from the sidecar kind). Framing equality vs R needs R's leaf index, which is an R read, so it is a measured column of the correspondence rather than a stratum. K = 60 per stratum, K = 240 for L0/288 strata (99.8 % of classes); smaller strata taken whole. Pick and holdout keys exactly as the draft (`p68-sample:` / `p68-holdout:` over `{level},{ix},{iy},{path},{sha}`).
5. **Class definitions** (in `sample.json`, before any R read): R-one-byte, R-one-geom, R-merged, R-absent, R-noncomparable (alias frame | type-set), plus R-other (named per case, never a pass). Tolerance 1 parent-raw unit. Position: first / last / middle / neither by anchor alignment on unique byte- or geometry-equal non-duplicate records.

### P1a — live sidecar encodes and national census (done, 16:00 AEST)

Wrapper `run_heavy_python.py --memory-max 12G` (flock; waited behind another agent's e2e job holding `.heavy.lock`): max RSS 3,580,680 KiB, memory.peak 8.52 GB (incl. file pages), 170 s.
- **Output-neutral gate:** full AU sidecar encode sha256 = `0c22b266…` (equal); Perth = `5b86d33e…` (equal). The sidecar disc was deleted after the gate; the census reads the oracle copy.
- **AU census** (`census_au.json` / `.tsv.gz`): 336,135 leaves with duplicates, 338,565 classes, 444,934 extra copies (equal to plan 63's `dup_census_0c22b266.json`). Every duplicate leaf matched to its sidecar entry (334,709 whole-cell W, 1,426 divided-sub-cell F+P), 0 unmatched, 0 count / class-sequence failures.
- **Perth census:** 1,812 leaves, 1,987 classes, 2,573 extra copies; all matched.
- **Plan-63 rule on live, national:** 338,565 / 338,565 AU classes and 1,987 / 1,987 Perth classes have copies in strictly increasing merged ordinal and (class, own-first, source iy, ix, k) order; 0 shared emitters (every copy from a distinct source). Assumption 4 holds on live without re-derivation.
- **Emitter form:** 768,130 of 783,499 AU copies are E1 interior-cover items (kind 1, a source whose ring covers the whole leaf); 242,645 of the 338,565 classes are cover-only pairs at L0/288.
- **Sample** (`sample.json`): 2,472 classes in 31 strata (derivation 1,237 / holdout 1,235), committed before any R read.
