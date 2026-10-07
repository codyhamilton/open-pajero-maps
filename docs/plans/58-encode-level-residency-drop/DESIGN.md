---
design_id:
---

# Encode: drop intermediates between levels/chunks (mmap discipline)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody via Primary (2026-10-07): designs that avoid keeping all data in memory at once — **chunk/stream, free between phases, mmap, drop intermediates** — after proven residency. No seat ask — wait for CHM.

This plan is the **encode band** optim package for `parser/build_alldata.py`: reduce peak process-tree RSS without changing ALLDATA bytes (AU/Perth sha gates; oracle succession only via proven RC elsewhere).

Published motivation (not yet a concurrent ledger): plan **48** P2 census benches on tip record AU **`peak_rss_tree_mb`: 15240.1** and Perth **13809.5** at `-j4` via `parser/tools/bench_build.py`. Plan **56** must prove what of that tree is co-resident (per-worker `E1Spool`, spills, parent merge, level overlap) before claiming a dominant cut.

Master direct; flock + wrapper; `-j4`; Flash Execute; no plan 04 P4–6; no 3-90; no reseat 170 / 3-16 / 3-17; no PSS ceiling raise.

## Problem

Encode already chunks work (`_plan_chunks`, worker Pool, per-level `_encode_level`) and memory-maps spool via `cenc.E1Spool`. Yet published **~15 GiB** tree peaks show the process tree still retains a large concurrent footprint. Without a residency ledger it is unknown whether:

- workers’ E1Spool mmaps overlap across chunks/levels longer than needed;
- spill/index buffers accumulate in the parent across levels;
- name-drop re-encode paths double-hold spool views;
- page-cache dirty from spills inflates `memory.peak` beyond anon RSS.

A blind “use more mmap” change without sha gates and without 56 proof risks DVD deviation or zero peak win.

## Solution shape

### Domain: encode residency ledger gate (consumes 56)

- **Owns:** naming dominant co-resident classes for AU/Perth `-j4` encode.
- **Contract:**
  1. Cite plan **56** encode rows (or re-measure under CHM with `bench_build.py` + scope `memory.peak` + smaps/accounting).
  2. Separate **anon** vs **file/mmap** contributions when evidence exists (WORKFLOW: gate both RSS and `memory.peak`).
  3. Tree peak alone is inventory, not a cut license.
- **Non-goals:** changing Contract H wall median rules (plan 41) except to re-measure after cuts.

### Domain: free between levels / chunks

- **Owns:** lifecycle of per-level and per-chunk structures in `build_alldata.py` / `cenc` worker entrypoints.
- **Contract:**
  1. After each level (and, if ledger demands, each chunk): drop references to finished spills, close or recycle E1Spool views, `gc` where Python holds large buffers — with **measured** RSS/`memory.peak` delta on a named fixture (Perth first) and full-AU confirmation under CHM.
  2. Disc bytes unchanged: AU sha gate and Perth sha gate (live oracle or Design-accepted successor — currently Design-accepted `88bd7852` awaiting Execute land; do not invent a third oracle here).
  3. Worker cap stays ≤ `-j4`. Eager-fork comment in tip (`Pool` while parent small) preserved or improved with evidence.
  4. Bench JSON continues to record wall + peak_rss_tree via `bench_build.py`.
- **Non-goals:** algorithmic EO/clip changes; census semantics changes that alter disc.

### Domain: mmap / window discipline (encode spool)

- **Owns:** ensuring spool mapping stays true mmap windows, not accidental whole-level materialization in Python.
- **Contract:**
  1. Audit worker paths for `.read()` / full copies of level data; refuse or stream (align with `whole_file_guard.py` spirit for any Python-side loads).
  2. Document which objects are expected file-backed vs anon.
- **Non-goals:** rewriting spool format.

## Decisions

1. Plan number **58**. Encode-only; mass/control → 57; dump finalize → 59.
2. Master direct. Sha gates mandatory on any land.
3. Phases: ledger gate → level/chunk drop cut on Perth then AU → close_gates / plan-41 wall honesty.
4. No seat ask; live AU measure waits on CHM.
5. Do not raise PSS or `-j`.

## Assumption ledger

### Assumption 1

- **Question:** Does ~15 GiB tree peak prove E1Spool is the dominant class?
- **Answer chosen:** **No** — hypothesis only until 56 ledger.
- **Rationale:** Primary concurrent-residency rule.
- **If wrong:** 56 names another class — Phase 2 retargets to that class still inside encode.

### Assumption 2

- **Question:** May peak drop waive sha identity?
- **Answer chosen:** **No.** Byte-identical discs required unless a separate Design oracle RC exists (not this plan’s job to promote).
- **Rationale:** DVD parity standing.
- **If wrong:** none.

### Assumption 3

- **Question:** Is Perth fixture enough acceptance for the cut?
- **Answer chosen:** Perth for mechanism proof; **AU `-j4` under flock** required before close (CHM-seated), plus plan 41 close gates if trigger surfaces touched.
- **Rationale:** Plan 41 encoder close gates; published AU peak is the operational pain.
- **If wrong:** Cody allows Perth-only for a docs-only lifecycle patch with no C changes — still publish AU measure when seated.

## Open questions

1. 56 dominant encode class.
2. Interaction with eo_census sidecar merge memory (plan 48) — measure, don’t assume.

## Phases

### Phase 1 — Encode residency classes named

- **Outcome:** Note under `docs/plans/58-…/` cites 56 (or CHM re-measure) for encode: dominant co-resident rows, anon vs file, per-level peaks if available. No code cut required yet.
- **Surfaces:** plan-58 note; pointers to `build_alldata.py` `_encode_level` / `_e1spool` / Pool.
- **Approach:** known
- **Depends on:** 56 encode samples **or** CHM seat.
- **Refine:** skipped.

### Phase 2 — Drop-between-levels/chunks lands (sha-identical)

- **Outcome:** Production encode path drops finished intermediates per Phase 1 target; Perth sha unchanged; harness shows peak RSS and `memory.peak` improved vs baseline on the same host recipe; tests or bench scripts record before/after. No `-j` raise. No algorithm change that alters bytes.
- **Surfaces:** `parser/build_alldata.py` and any small helper; benches under `output/scratch-58/`; plan-58 note.
- **Approach:** known; exact drop sites refine from Phase 1.
- **Depends on:** Phase 1.
- **Refine:** drop site list only.

### Phase 3 — AU confirm + close gates honesty

- **Outcome:** CHM-seated AU `-j4` under flock + wrapper/`bench_build.py`: sha gate PASS vs live oracle (or accepted successor); peak published; if plan-41 trigger surfaces touched, `close_gates.py` PASS with markers. Wall median regression named if any (Contract H). No Phase 3 product close claim. No waivers.
- **Surfaces:** IMPLEMENTATION markers; provenance peek as needed.
- **Approach:** known
- **Depends on:** Phase 2 + CHM AU seat.
- **Refine:** skipped.

## Provenance

- Primary 2026-10-07; plan 48 census peaks; `bench_build.py`; ARCHITECTURE mmap vs window; plan 56 sibling; tip `094b11f`.
- Rejected: assuming E1Spool dominance; sha waiver; `-j`/PSS raise; seat asks; absorbing mass/dump plans.
