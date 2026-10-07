---
design_id:
---

# EO clipper face-walk decline: root cause, a no-incidence proof from instrumentation, and a fix for all 20,000 seeded rings

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ask (2026-10-06, 19:34 AEST), for R-G8-1-d-a:

- **P1:** root-cause why the `_cenc.c:885` guard fires on the 5 seeded rings. Add a tracked tool or test that proves "no AU/Perth input reaches the guard" from instrumentation, not just from builds completing.
- **P2:** fix the clipper so all 20,000 pass, flipping ring 359 from expected failure to pass. The fix must satisfy:
  - AU still builds to `4e6b0de7` byte-identically, and Perth to `04be2f6e`;
  - K1 failing 0 in every kind;
  - the full suite green;
  - `close_gates.py` passing;
  - the build wall not regressing beyond plan 41's 37.38 s median at `-j4` by more than noise.

  If a byte-identical fix is impossible, the changed disc becomes a recorded successor oracle with its diff confined and explained.

Constraints:
- Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower.
- Master direct.
- Never relabel.
- No plan 04 Phases 4–6.
- Do not run the 3-90 brief.
- Do not reseat 170, 3-16 or 3-17.

## Problem

Plan 43's `parser/tests/test_bg_eo_stress.py` (seed 4314, 1,000 rings) and `stress_characterise_20k.py` → `stress_20k.json` (20,000 rings) found 5 declines: r359, r8475, r11892, r14503, r19650. Every one is −1, terminates, and has no parity, bounds or capacity failure. The decline comes from the face walk in `eo_clip`:

```c
if (g_eh[h].used || np >= ne) return -1; /* never close a partial walk with a chord */
```

**Ground (master `607e5b6`, `parser/kiwiw/_cenc.c`):**

1. **The arrangement.**
   - Segments are split at pairwise intersections (`eo_intersect`, split mode). The intersection point is `a + t·(b−a)` in long double, then **rounded to double**.
   - Vertices are merged within `eps = 32·DBL_EPSILON·max(1,|R2|,|R3|)` (`eo_vertex`), by linear scan.
   - Edges are deduplicated with a parity XOR (`eo_edge`). Edges with parity 0 that are not frame edges are dropped.
   - `eo_connect` adds horizontal bridges to connect components.
2. **The walk.** Half-edges are created with `angle = atan2(dy, dx)` in double. The next half-edge is the minimum of `turn = reverse − angle` (with `turn ≤ 0 → +2π`), with no tie-break.
3. **Why "already used" happens.** In a valid planar DCEL with a consistent angular order, the minimum-turn successor is a permutation of the half-edges, so a walk can never meet a used half-edge before returning to `start`. Hitting a used one therefore means the successor map is **not a permutation**, so two incoming half-edges choose the same outgoing one. Candidate mechanisms, all consistent with the ground:
   - **H1, rounding non-planarity.** A split vertex rounded to double moves off one of its segments. The sub-edges can then cross an edge that was never split, or reverse their order around a vertex, so the angular order is inconsistent.
   - **H2, equal-angle ties.** Two outgoing half-edges at a vertex have equal `atan2`: collinear overlap remnants after the parity XOR, or a bridge collinear with a ring edge. The `<` tie-break then picks the same successor for two predecessors.
   - **H3, merge or bridge inconsistency.**
     - `eo_vertex`'s eps-merge joins two distinct cut vertices, making a zero-length or folded edge.
     - Or an `eo_connect` bridge crosses an edge. Its hit `x` is computed by interpolation and rounded, and only the hit edge is split.
   - **H4, the `np ≥ ne` iteration bound.** Not expected: the bound is ne, the total half-edge count.
4. **Production incidence is inferred, not instrumented.** Today a decline becomes an E2 "declined" row and the build errors. Every AU build has completed, so incidence is zero by completion only.

## Solution shape

### Domain: decline root cause

- **Owns:** `parser/tools/eo_walk_diag.py`, plus a diagnostic build of `parser/tests/fixtures/bg_eo/probe.c` with a compile-time `EO_DIAG` hook in `_cenc.c` (absent from the production build: zero bytes and zero cost). Also `triage/independent_reviews/3-14/conditions/eo_decline/`.
- **Contract:** for each of the 5 rings, dump the arrangement: vertices, edges with parity/frame flags, bridges, per-vertex angular order, and the walk up to the decline. Then run exact checks with **rational arithmetic** (Python `Fraction` on the double-valued coordinates) for:
  - (a) any pair of non-adjacent edges that properly cross (H1, H3 bridge);
  - (b) any vertex whose double `atan2` order disagrees with the exact orientation order, or has exact ties (H1, H2);
  - (c) any merged pair whose source cuts were distinct points, and any zero-length edge (H3);
  - (d) the successor map's non-injective pairs.

  Each ring gets exactly one named mechanism, with its witness; "mixed" is allowed only with witnesses for each. The mechanism must explain all 5 rings, or each ring separately.
- **Non-goals:** changing behaviour in P1.

### Domain: no-incidence proof for AU and Perth

- **Owns:** a tracked counter in `_cenc.c`: a per-worker `eo_stats`, returned through the existing per-cell result path and summed by `cbuild` into a sidecar JSON. Also `parser/tools/eo_guard_census.py` and `parser/tests/test_eo_guard_census.py`.
- **Contract:**
  1. Count, per build: `eo_clip` entries; complex entries; declines by site (each `return -1` in `eo_clip`, `eo_connect` and the walk, with the `:885` guard distinguished); and, for the walk, the minimum margin seen.
  2. The census must not change disc bytes. Gate: AU `4e6b0de7` and Perth `04be2f6e` sha unchanged with the census on. Its wall cost is measured.
  3. An AU and a Perth build at `-j4` under the lock produce sidecars showing guard hits = 0 and total declines = 0, with entry counts recorded. A test checks the census logic on the seeded r359 (hits = 1) and on a clean ring (hits = 0).
  4. Optional: "near-miss" counters (exact ties and post-rounding crossings found by the H-check in a cheap form) show how close AU came. They are reported, not gated.
- **Non-goals:** the census replacing the error path; declines stay build errors.

### Domain: robust face walk

- **Owns:** `parser/kiwiw/_cenc.c` (`eo_intersect`, `eo_vertex`, `eo_connect` and the walk, as the root cause dictates), `test_bg_eo_stress.py` (`KNOWN_DECLINES` = ∅, the r359 xfail flipped to a pass, and the 20,000-ring characterisation promoted to a test or a gated tool), and new regression cases per mechanism.
- **Contract:**
  1. **The fix follows the P1 mechanism. Default candidates, in order of preference:**
     - **(i) Exact angular order.** Replace `atan2` with an exact orientation comparator: quadrant, then cross product in long double / int128, valid because coordinates are raw lattice or bounded rounded intersections. Add a deterministic tie-break on the exact zero-turn case (collinear outgoing edges merged or ordered by length). This fixes H2 and order-H1.
     - **(ii) Iterative re-split (snap rounding).** After rounding, re-run the intersection pass on the sub-edges until no proper crossing remains. A bounded number of rounds is reported; a non-converging case is a decline with a named site. This fixes crossing-H1 and H3 bridges.
     - **(iii) Bridges by exact predicates.** Split every edge the bridge meets, not only the hit edge.
  2. **Byte identity first.** The fix may change output only on inputs that declined before. Gates:
     - AU `4e6b0de7` and Perth `04be2f6e` byte-identical (at `-j4`; Perth also at `-j1`);
     - K1 failing 0 in every kind;
     - full `parser/tests` green;
     - `close_gates.py` passing;
     - wall: the plan 41 bench harness, median of 5 at `-j4`, within noise of 37.38 s. The noise band is set from the harness's recorded spread (plan 41 recorded a spread of 0.51 s at `c82f92e`).
  3. **If the fix changes any AU or Perth byte**, which is possible if (i) or (ii) changes a non-declining walk:
     - a confined diff by cell (`oracle_chain.py diff`) and an explanation for every changed cell (which tie or crossing changed, with the exact witness);
     - DVD-relative evidence that each change is no worse against R. Where R is mounted, use the plan 36 / 42 per-cell R comparison, otherwise name it as an unverifiable residual;
     - a recorded successor oracle row in `oracle_chain.tsv` with the census sidecar, and the K1 / suite / gates rerun on it.

     The design prefers a variant that keeps `4e6b0de7`, and records each variant that was tried and why it was rejected.
  4. The stress test asserts all 20,000 rings pass the existing parity, bounds and capacity checks, under the child-process timeout, and checks runtime.
- **Non-goals:** changing the legacy (non-complex) path; changing E2 decline handling.

## Decisions

1. Plan number 48. Master direct. Three phases: P1a root cause; P1b census; P2 fix. Cody's P1 is split into 1 and 2 so the census can land without waiting on the diagnosis. Both are known.
2. The diagnostic hook is compile-time (`EO_DIAG`), so it adds zero production bytes. The census counter is runtime but output-neutral, and gated by sha.
3. Fix preference is the smallest mechanism-matched change: (i) before (ii) before (iii).

## Assumption ledger

### Assumption 1

- **Question:** Does a non-permutation successor map require one of H1–H3?
- **Answer chosen:** Yes. For a planar straight-line graph with a strict angular order, minimum-turn successors form a permutation.
- **Rationale:** Standard DCEL property.
- **If wrong:** P1's exact checks find no violation. The walk logic itself (the `reverse` angle, or the `turn ≤ 0` wrap at exactly 2π) is then the defect, and it is named.

### Assumption 2

- **Question:** Can a census be returned without changing disc bytes or the wall?
- **Answer chosen:** Yes. Counters live in worker memory and are written to a sidecar only.
- **Rationale:** Plan 41's per-commit bench shows byte-identity is checkable.
- **If wrong:** the census becomes an env-gated build mode (the same code path, with a flag that only adds the writes), and its bytes are gated identical.

## Open questions

1. Whether the 20,000-ring characterisation (runtime TBD by P1) fits the suite budget, or becomes a gated tool run by `close_gates.py` while 1,000 rings stay in the suite.

## Phases

### Phase 1: Decline root cause

- **Outcome:** a named mechanism per ring for all 5, with exact witnesses. Regression fixtures for each mechanism are committed as strict xfails.
- **Surfaces:** `parser/tools/eo_walk_diag.py`, the `EO_DIAG` hook in `_cenc.c` (compiled out), `parser/tests/test_eo_walk_diag.py`, `triage/independent_reviews/3-14/conditions/eo_decline/`, `parser/perf_inventory.json`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: No-incidence census

- **Outcome:**
  - census landed;
  - AU and Perth sidecars showing guard hits 0 and declines 0, with entry and complex counts;
  - shas unchanged;
  - census wall delta measured.
- **Surfaces:** `_cenc.c` counters, `parser/kiwiw/cbuild.py` sidecar, `parser/tools/eo_guard_census.py`, `parser/tests/test_eo_guard_census.py`, `docs/provenance.md`.
- **Approach:** known. **Depends on:** none (parallel with Phase 1). **Refine:** skipped.

### Phase 3: Robust walk, all 20,000 pass

- **Outcome:**
  - `KNOWN_DECLINES` empty, and r359 plus the per-mechanism fixtures pass;
  - all 20,000 pass;
  - AU `4e6b0de7` and Perth `04be2f6e` byte-identical, or a recorded, confined and explained successor oracle;
  - K1 0 in every kind; suite green; `close_gates.py` pass; wall within noise of 37.38 s;
  - census rerun shows 0 declines;
  - R-G8-1-d-a discharged.
- **Surfaces:** `_cenc.c`, `test_bg_eo_stress.py`, `stress_characterise_20k.py` (or a gated tool), `residuals.tsv`, `oracle_chain.tsv` (only on a successor), `docs/provenance.md`.
- **Approach:** known. **Depends on:** Phases 1 and 2. **Refine:** skipped.

## Provenance

- Master `607e5b6`. Sources:
  - `residuals.tsv` R-G8-1-d-a;
  - `docs/plans/43-review-conditions-light/IMPLEMENTATION.md` L24–25, L49;
  - `parser/tests/test_bg_eo_stress.py`;
  - `triage/independent_reviews/3-14/conditions/stress_20k.json`;
  - `parser/kiwiw/_cenc.c` L681–898;
  - plan 41 record (37.38 s, spread 0.51).
- Box draft only.
