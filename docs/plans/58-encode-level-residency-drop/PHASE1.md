# Plan 58 Phase 1 — Encode residency classes named

Tip at Phase 1: `f616059` (plan 57 closed). Live AU oracle `88bd7852`. Perth sha anchor `04be2f6e`. No code cut in this note.

## Sources (plan 56 ledger + FINDINGS)

| Row | Path | Peak | Role |
| --- | --- | --- | --- |
| encode Perth stand-in `-j4` | `docs/plans/56-cross-phase-rss-profile/ledger/encode_perth_j4.json` | wrapper max_rss **3412576 KiB** (~3.25 GiB); `memory.peak` **1366241280** (~1.27 GiB scope); **tree_peak_mb 13962.9** | Fresh measure; Perth sha `04be2f6e…` |
| encode cite_prior plan48 | `…/ledger/encode_cite_prior_plan48.json` | AU tree **15240.1 MB**; Perth tree **13809.5 MB** | Inventory only (no phase-tagged co-residency) |
| FINDINGS (box) | `maps-design-drafts/memory-profile-2026-10-07/FINDINGS.md` | same published peaks | Hypotheses pre-56; 56 confirms tree ≫ wrapper |

Plan 56 SUMMARY: **Encode tree ≫ wrapper RSS**; worker Pool j=4 + parent co-resident; level-resident structures stay live across encode → plan **58** target.

## Dominant co-resident classes

### Proof (process tree)

**Worker Pool children (`-j4`) co-resident with the parent dominate the encode process-tree peak.**

Evidence: plan 56 Perth stand-in tree sampler **13962.9 MB** vs wrapper/cgroup peaks ~3.25 / ~1.27 GiB. Residency rows `encode_process_tree_peak` + `worker_pool_j4`. Aligns with plan-48 cite (~13809.5 MB Perth / ~15240.1 MB AU).

Tree peak alone is **inventory**, not a cut license (Design Decision / Domain contract).

### Proof (lifecycle gap — cut target)

**Per-worker `_e1spool` replaces the cached `E1Spool` on level change without calling `.close()`.**

Evidence: `parser/build_alldata.py` `_e1spool` (lines ~227–233). Replacing the `_WORKER["e1spool"]` entry drops the Python reference but does not close numpy memmaps; with a long-lived fork Pool reused across levels `[12,10,8,6,4,2,0]`, prior-level private mappings can remain mapped until GC. Name-guard path uses `E1Spool(..., guard_names=True)` → memmap mode **`"c"`** (copy-on-write private) — pages dirtied by admission become **anon** RSS in the worker.

This is the Phase 2 primary drop site: close previous `E1Spool` on level switch + explicit post-level worker release + harden `E1Spool.close()` to release mmap handles.

### Anon vs file/mmap (labelled)

| Class | Label | Notes |
| --- | --- | --- |
| Worker RSS in tree peak | **Proof** (tree sampler) | Dominant aggregate |
| Prior-level E1Spool still mapped across levels | **Proof of mechanism gap** (code); **hypothesis** of KiB share of the ~14 GiB tree | Phase 2 measures before/after |
| Private COW (`mode="c"`) dirtied pages → anon | **Hypothesis** (API mode) | Plan 56 post-exit `memory.stat` anon/file are **not** peak co-residency (scope torn down) — cannot cite as peak split |
| Read-only spool file pages / spill file page cache | **Hypothesis** (file/mmap) | Spill FDs stay open until assemble (needed for FrameTable offsets) — not closed between levels |
| Parent merge / FrameTable `rec` arrays across all levels | **Secondary / expected** | Required until `build_alldata_kwi`; not the Phase 2 drop target |
| eo_census sidecar accumulators | **Hypothesis / small** | Plan 48 sidecar; measure, don’t assume (Design open Q2) |

## Contingency

If Phase 2 close-of-E1Spool yields **no** peak improvement on Perth, retarget still inside encode (spill FD recycle / parent temps) — do **not** open dump (59) or mass (57).

## Phase 1 outcome

Go for Phase 2: drop/close E1Spool between levels (and explicit post-level worker release); sha-identical Perth then AU; `-j4` max; no algorithm/byte change.
