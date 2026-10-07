---
design_id:
---

# Bound mass_decide / control spool residency (chunk, clear, free)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody via Primary (2026-10-07) memory focus: after profiling, produce designs that avoid keeping all data in memory at once (**chunk/stream, free between phases, mmap, drop intermediates**). Keep the designs list filled. No seat ask — wait for CHM.

This plan is the **mass_decide / control band** optim package: prove and then cut concurrent spool/disc residency so Phase 2 mass can finish under flock without ~17 GiB host pressure kills, **without** bumping mass R default (standing widen@16 / R=8 lock).

DVD parity for any disc-touching side effects (this lane is triage decision TSVs — still no unexplained residuals). Master direct; flock + wrapper; `-j4` where encode appears; OpenCode DeepSeek Flash; no plan 04 P4–6; no 3-90; no reseat 170 / 3-16 / 3-17.

## Problem

Plan **44** Phase 2 mass (`mass_decide.py --r 8`) under flock reached **30000/95059** leaves (~63 min) and was **SIGTERM’d** on host memory pressure: RSS **~17.1 GiB**, MemAvailable ~3.2 GiB, SwapUsed ~6/8 GiB (`IMPLEMENTATION.md` Unit 4c). Tactical patches already on tip: `--resume-from`, `--cache-clear-every` (default 50) calling `leaf_io.clear_spool_caches`.

What is **not** yet proven (needs plan **56** ledger — label clearly):

- Whether `_SPOOL_KEY_CACHE` / `_SPOOL_CELL_CACHE` dominate vs dual ALLDATA frame maps vs flex probes vs Python process growth.
- Whether control.py neighbourhood expansion at R_cap=8 shares the same dominant class.
- Whether clear-every-50 is sufficient for the remaining ~65k leaves at steady state.

Skipping a measured dominant class risks “optimizing” the wrong structure while mass R and OE/cover contracts stay sacred.

## Solution shape

### Domain: residency proof gate (consumes 56)

- **Owns:** the go/no-go that names the dominant co-resident class for mass_decide and control.
- **Contract:**
  1. Before production cut acceptance, cite plan **56** ledger rows for mass_decide (and control if measured) **or** re-measure the same schema under this plan’s Phase 1 if 56 only partially seated.
  2. Label every pre-56 claim from plan 44 as **hypothesis** until ledger bytes attach.
  3. Do **not** bump `--r` / locked R=8 for memory relief.
- **Non-goals:** discharging R-G5-4-a/b science in this memory plan (still plan 44); changing OE predicates.

### Domain: spool cache + leaf chunking

- **Owns:** `leaf_io.py` / `mass_decide.py` / `control.py` residency behaviour.
- **Contract:**
  1. Spool access stays **cell-keyed** (`_spool_cell`); whole-level `spool_level_cells` stays off hot paths (or refuses under mass).
  2. Caches have an explicit bound: clear-every N leaves **and/or** max entries **and/or** process restart per chunk file — pick one primary mechanism after 56 evidence; document the KiB ceiling targeted.
  3. Mass resume remains correct: `--resume-from` row identity unchanged; decision TSV bytes for already-done rows not rewritten differently.
  4. Optional: stream leaf groups to separate chunk outputs then stitch (chunk/stream theme) so a killed worker loses at most one chunk — without changing per-row decision semantics.
  5. Fixture or small-leaf test: after N leaves with clear enabled, named cache dict sizes drop; without clear, they grow (proves the lever).
- **Non-goals:** rewriting `bg_owner_exclusive` OE math; enabling Cursor cloud for product work.

### Domain: free between control and mass

- **Owns:** process boundaries so control probes / disc maps are not left co-resident into mass (or the reverse) when run in one seat.
- **Contract:**
  1. Documented recipe: finish control → exit process / clear caches / close discs → start mass under a **fresh** `run_heavy_python.py` scope (prove via 56 inter-phase sample when available).
  2. If same-process sequencing remains, explicit teardown API with measured RSS delta.
- **Non-goals:** merging control and mass into one mega-script.

## Decisions

1. Plan number **57**. Separate from 56 (measure) and 58/59 (other bands).
2. Master direct. No PR. No feature branch.
3. Phases: proof gate → cache/chunk cut → free-between recipe + mass resume verification under CHM/flock.
4. Standing: **do not bump mass R** for memory; widen@16 STOP_FOR_DESIGN remains Design’s product ruling track on plan 44 — this plan only addresses residency.
5. Flash Execute constraint only; no seat ask from Design.
6. Contingency: if 56 shows disc mmap dominates over spool caches, retarget Phase 2 to frame-map lifecycle (still this plan’s band) rather than opening encode work (58).

## Assumption ledger

### Assumption 1

- **Question:** Is plan 44’s ~17 GiB stop already enough to land cache bounds without 56?
- **Answer chosen:** Enough to **draft** and to keep clear-every as default hygiene; **not** enough to claim dominant-class proof. Phase 1 requires 56 (or in-plan re-measure) before calling the cut “proven.”
- **Rationale:** Primary: prove concurrent residency — don’t assume.
- **If wrong:** Cody accepts plan-44 host facts as sufficient dominant-class evidence for spool caches — still keep RSS/`memory.peak` gates on a bounded leaf window.

### Assumption 2

- **Question:** May we raise R or disable widen protocol to save memory?
- **Answer chosen:** **No.**
- **Rationale:** Plan 44 standing; Primary memory focus is residency shape.
- **If wrong:** separate Design product ruling — not this plan.

### Assumption 3

- **Question:** Must byte-identical decision TSV vs the partial 30k snapshot be preserved for resumed rows?
- **Answer chosen:** **Yes** for already-emitted rows; new rows follow the same decision function as tip mass_decide.
- **Rationale:** Honesty / no unexplained deviation in triage artefacts.
- **If wrong:** document intentional recompute with RC — still no silent drift.

## Open questions

1. Dominant class from 56 (spool vs disc vs probes).
2. Whether control needs its own clear-every (likely yes if same `leaf_io` caches).

## Phases

### Phase 1 — Dominant residency named for mass/control

- **Outcome:** Committed note cites plan **56** ledger (or this plan’s flock-held re-measure under CHM seat) naming dominant co-resident class(es) for `mass_decide` and, if measured, `control`. Hypotheses vs proof labelled. No R bump. No residual discharge claim.
- **Surfaces:** `docs/plans/57-…/` note; references to `leaf_io.py` cache symbols.
- **Approach:** known
- **Depends on:** plan 56 Phase 2 subset **or** CHM-seated re-measure.
- **Refine:** skipped if 56 already published the rows.

### Phase 2 — Cache bound / chunk-stream cut lands

- **Outcome:** On master: mass/control path enforces bounded spool residency (clear-every and/or max cache and/or chunked workers) with a published KiB target for a named leaf-window harness; tests prove cache drop; `--resume-from` still correct. Peak for the harness is **below** the pre-cut baseline on the same window (RSS and `memory.peak`). No OE/cover contract change. No R bump.
- **Surfaces:** `leaf_io.py`, `mass_decide.py`, optionally `control.py`; tests under `parser/tests/` or plan triage tests; plan-57 note.
- **Approach:** known (mechanism choice may refine against Phase 1 class).
- **Depends on:** Phase 1.
- **Refine:** only which bound mechanism if ledger surprises.

### Phase 3 — Free-between recipe + resume path verified

- **Outcome:** WORKFLOW or plan-57 recipe documents fresh-scope sequencing control→mass; remaining mass resume under flock + wrapper completes a CHM-scoped chunk without host OOM class of Unit 4c (or publishes a new measured ceiling with RC). Plan 44 product STOP_FOR_DESIGN / R-G5-4 rows **not** auto-discharged here. No plan 04 P4–6 / 3-90 / waivers.
- **Surfaces:** docs recipe; optional IMPLEMENTATION cross-link on plan 44 “memory path owned by 57.”
- **Approach:** known
- **Depends on:** Phase 2.
- **Refine:** skipped.

## Provenance

- Primary memory-focus 2026-10-07; plan 44 Unit 4c; `leaf_io.clear_spool_caches`; plan 56 sibling; tip `094b11f`.
- Rejected: R bump; assuming spool caches dominate without ledger; absorbing encode/finalize; seat asks.
