---
design_id:
---

# Dump finalize: out-of-core / drop intermediates (ARCHITECTURE deferred)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody via Primary (2026-10-07): avoid keeping all data in memory at once — chunk/stream, free between phases, mmap, drop intermediates — after proven peaks. No seat ask — wait for CHM.

This plan addresses the **dump/extend band** residual named on master: ARCHITECTURE **Deferred: out-of-core dump finalizer** — `_finalize_dump` still scales with **one full in-memory kind array** after plan **05** removed redundant copies. Windowed `dump_join` / `dump_io` already bound join/extend; finalize remains the known open.

Plan **56** must publish dump/extend peaks (join vs finalize) before treating finalize as the live dominant spike. Plan-05 fixture wins stay; this plan extends to out-of-core or stricter drop of intermediates **without** changing dump bytes / counts / order.

Master direct; flock + wrapper; Flash Execute; no plan 04 P4–6; no 3-90; no reseat 170 / 3-16 / 3-17.

## Problem

Plan **05** cut residual/finalize/triage peaks on seeded fixtures and documented the finalize limitation: peak anonymous memory still tracks one full kind array (`docs/ARCHITECTURE.md`). Plan **17** pointed live extend at tracked `dump_join`. Primary now wants product-facing memory designs beyond plan-14/25 completeness-stop class — finalize out-of-core is the already-named dump-band follow-up, but **must not** assume it dominates live AU dumps without 56 numbers.

## Solution shape

### Domain: dump-band peak gate (consumes 56)

- **Owns:** join vs finalize peak attribution.
- **Contract:**
  1. Cite 56 dump/extend ledger (or CHM re-measure via `bench_dump_memory.py` finalize-run + residual run).
  2. If join windows dominate, document and **stop** (no forced out-of-core); open a different cut only with evidence.
  3. If finalize kind array dominates, proceed to Domain 2.
- **Non-goals:** re-litigating plan-05 window size without evidence.

### Domain: out-of-core or chunked finalize

- **Owns:** `parser/tools/quantisation_roundtrip.py` `_finalize_dump` (and baseline comparison discipline from plan 05).
- **Contract:**
  1. Output SHA / counts / stable `DUMP_ORDER` / part deletion semantics unchanged vs current candidate.
  2. Peak RSS and `memory.peak` on the plan-05 finalize fixture improve by ≥ one meaningful bound (publish KiB gate; prefer ≥ removal of a second large transient if any remain, else prove single-array → external sort / chunked merge bound).
  3. Reuse `bench_dump_memory.py finalize-run` controller under flock; add growth gate for larger synthetic kinds if CHM allows.
  4. Live extend path remains `dump_join` wrapper — no resurrection of whole-file scratch extend.
- **Non-goals:** changing K1 checker semantics; raising worker caps.

### Domain: free between dump kinds / phases

- **Owns:** ensuring finalized kinds are released before the next kind starts; no multi-kind co-residency beyond one working set.
- **Contract:** measured before/after kind teardown in the harness; documented recipe for multi-kind dumps.
- **Non-goals:** parallel finalize of multiple kinds.

## Decisions

1. Plan number **59**. Dump/extend only.
2. Contingent on 56 dump-band proof (or explicit CHM re-measure in Phase 1).
3. Prefer extending plan-05 controllers over new frameworks.
4. Master direct; sha/count gates; Flash; no seat ask.

## Assumption ledger

### Assumption 1

- **Question:** Is ARCHITECTURE deferred text enough to land out-of-core without 56?
- **Answer chosen:** Enough to **draft**; Phase 1 still requires peak attribution so we do not fight the wrong spike.
- **Rationale:** Primary prove-concurrent rule.
- **If wrong:** Cody prioritizes finalize out-of-core as standing debt — still keep fixture gates.

### Assumption 2

- **Question:** May finalize change row order or padding?
- **Answer chosen:** **No.** Stable order and bytes match tip finalize candidate.
- **Rationale:** DVD / dump consumers.
- **If wrong:** none.

## Open questions

1. 56: is finalize the dump-band peak?
2. External sort dependency policy (stdlib only vs existing numpy memmap).

## Phases

### Phase 1 — Join vs finalize peak attribution

- **Outcome:** Note cites 56 or flock harness numbers; decision **proceed** (finalize dominates) or **stop-with-evidence** (join dominates / inconclusive). No production change on stop path beyond the note.
- **Surfaces:** plan-59 note; `bench_dump_memory.py` results paths.
- **Approach:** known
- **Depends on:** 56 dump samples or CHM seat.
- **Refine:** skipped.

### Phase 2 — Out-of-core / chunked finalize lands

- **Outcome:** `_finalize_dump` bound lands; finalize-run controller PASS (RSS/peak/sha/counts/parts); architecture deferred section updated to “landed in plan 59” or residual limitation renamed honestly. No whole-file extend revival.
- **Surfaces:** `quantisation_roundtrip.py`, tests, ARCHITECTURE, plan-59.
- **Approach:** open on exact external-sort shape — refine against Phase 1 sizes.
- **Depends on:** Phase 1 proceed.
- **Refine:** algorithm sketch only; yardstick stays sha + peak gate.

### Phase 3 — Multi-kind free + live recipe

- **Outcome:** Recipe documents per-kind teardown; optional multi-kind harness; WORKFLOW pointer. No Phase 3 product close. No waivers.
- **Surfaces:** WORKFLOW / ARCHITECTURE / plan-59 IMPLEMENTATION.
- **Approach:** known
- **Depends on:** Phase 2.
- **Refine:** skipped.

## Provenance

- ARCHITECTURE deferred finalize; plan 05; plan 17; Primary 2026-10-07; plan 56 sibling; tip `094b11f`.
- Rejected: assuming finalize dominates; byte/order changes; seat asks; absorbing encode/mass.
