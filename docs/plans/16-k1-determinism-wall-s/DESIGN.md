---
design_id:
---

# K1 determinism strip: align with Phase 2 `wall_s`

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Align the 3-90 K1 determinism strip with Phase 2's `timing` + `wall_s` exclusion so content-identical `-j 1` / `-j 12` reports compare equal. Prove it with fixture-JSON unit tests. Land on master. No feature branch. No pull request. Runnable without a full-AU encode, disc `4ed9cd80…`, or completeness dumps.

## Problem

Phase 2 closed K1 determinism as byte-identical reports with **`timing` and `wall_s` excluded** (`docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` Phase 2 verification: `IDENTICAL (timing and wall_s excluded)`). The driver encodes that contract as `COMPARE_EXCLUDES = ["timing", "wall_s"]` in `parser/tools/quantisation_roundtrip.py`, and fixture tests already canonise via `_canon` / those excludes.

Brief `3-90-fresh-verify.md` check 3 still says: remove only the `timing` section, then `cmp` `-j 1` vs `-j 12`. Scratch `strip_timing.py` helpers used by every 3-90 rerun are five lines that pop **only** `timing`. Top-level `wall_s` is retained, so content-identical reports FAIL solely because walls differ (recorded examples: j12 ≈ 74–77 s vs j1 ≈ 447–449 s). Multiple 3-90 blocked records and `docs/OVERVIEW.md` name this as a Phase 3 blocker: "determinism comparison that retains varying `wall_s`".

This is a **verification-strip defect**, not a K1 content nondeterminism. The reports already declare `compare_excludes: ["timing", "wall_s"]`; the 3-90 strip disagrees with Phase 2 and with the driver.

Verified on `origin/master` at `4f8a03d` from committed files and plan records only — no live disc or dump was required. Plans **01–05** and **07–14** occupy those numbers on master; **15** is the in-progress SADSR draft; **06** is not a work unit. This plan is **16**.

## Solution shape

One bounded change: make the 3-90 determinism strip (and a fixture-JSON unit that locks it) remove every key in Phase 2 / `COMPARE_EXCLUDES` — `timing` **and** `wall_s` — so two reports that differ only in those fields compare equal. Do not re-run 3-90. Do not close Phase 3. Do not touch PSS, classify joins, pins, oracles, or completeness.

### Domain: report normalise strip

- Owns: the normalisation used when comparing two K1 report JSON files for determinism (the 3-90 check-3 strip, and any tracked helper the brief and tests share).
- Contract: after strip, keys `timing` and `wall_s` are absent; every other top-level key and nested content is unchanged. The excluded set equals `quantisation_roundtrip.COMPARE_EXCLUDES` (today `["timing", "wall_s"]`) — one source of truth, not a third hard-coded list. Two fixture reports that are equal once those keys are removed compare byte-equal (canonical JSON); two that differ in any non-excluded field do not.
- Non-goals: no change to report schema; no moving `wall_s` under `timing`; no change to PSS sampling, worker planning, dump layout, triage, or encode; no full-disc K1 rerun as this plan's gate.

### Domain: 3-90 brief check 3

- Owns: the signed wording of determinism in `briefs/3-90-fresh-verify.md` check 3 so a future fresh-verify run cannot FAIL solely because top-level `wall_s` differs.
- Contract: check 3 requires equality after removing the Phase 2 / `COMPARE_EXCLUDES` keys (`timing` and `wall_s`), not `timing` alone. Provenance/reproduce notes that still say "removes only timing" are updated when they are touched by this plan's surfaces; orphan historical 3-90 FAIL records stay as history.
- Non-goals: no rewrite of checks 1–2 or 4–8; no claim that other 3-90 blockers are cleared; no Phase 3 close trailer.

## Decisions

1. Plan number is **16**. Standalone plan; it **amends** the 3-90 brief as a surface, it is not a mega Phase-3-close plan.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known). Fixture-JSON unit is the highest-leverage gate; brief amend ships in the same phase.
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not claim Phase 3 closed.
5. Prefer one shared exclude list (`COMPARE_EXCLUDES`) over a second hard-coded pair in the strip helper or brief.
6. Assigned instance for this lane's workers is Codex (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: can this close without remounting a disc or re-running full-AU / 3-90 K1?
- Answer chosen: yes. The defect is strip normalisation vs Phase 2 / driver excludes. Fixture JSON (synthetic report dicts written to temp files) proves the strip; the brief amend aligns future 3-90 check 3. No disc sha gate.
- Rationale: ticket and Maps Quality Assessor tip name fixture-JSON as highest leverage and require runnable without Cody full-AU encode / disc `4ed9cd80…` / completeness dumps.
- If wrong: Cody supplies a stored `k1_a.json` / `k1_j1.json` pair; the same strip must still make them equal if they differ only in excluded keys — still no encode.

### Assumption 2

- Question: amend the 3-90 brief only, or also land a tracked strip helper + unit?
- Answer chosen: land fixture-JSON unit tests that prove strip removes `timing` **and** `wall_s`, and amend the brief in the same phase. A tiny tracked helper (or an exported function next to `COMPARE_EXCLUDES`) is preferred so the brief's script and the tests cannot drift; an ephemeral five-line scratch script alone is not enough.
- Rationale: ticket says fixture-JSON unit (or amend brief), highest leverage; both are needed so CI locks the contract and the next 3-90 run does not reintroduce "timing only".
- If wrong: Cody allows brief-only; still keep at least one unit that fails if only `timing` is stripped on content-identical fixtures.

### Assumption 3

- Question: does fixing the strip imply re-running 3-90 or marking Phase 3 closed?
- Answer chosen: no. Other blockers (PSS ceiling, native classify joins, truncated pins, 3-11 vs 3-14 oracle, review chain, completeness attribution) stay open. This plan only removes the false FAIL on retained `wall_s`.
- Rationale: OVERVIEW lists several independent 3-90 blockers; aligning the strip is one of them, not the phase outcome.
- If wrong: Cody orders a fresh 3-90 after this lands; that is a separate unit under plan 04, not absorbed here.

### Assumption 4

- Question: may the strip also drop nested `timing.wall_s` by deleting the whole `timing` object, and is top-level `wall_s` the only extra key?
- Answer chosen: yes — remove the entire `timing` object and the top-level `wall_s` key, matching `COMPARE_EXCLUDES` and Phase 2 records. Do not invent further excludes.
- Rationale: Phase 2 and the driver name exactly those two; 3-90 FAIL logs cite top-level `wall_s` as the sole remaining diff after timing-only strip.
- If wrong: a future report field is shown nondeterministic; widen `COMPARE_EXCLUDES` under a new design, do not silently extend this strip.

## Open questions

1. Should historical `docs/provenance.md` reproduce lines that say `strip_timing.py` removes only timing be rewritten in this phase, or left as accurate history of those blocked runs? **Default:** leave historical provenance rows; update only if this phase touches those entries. Not a phase gate.
2. After this lands, when should 3-90 be re-attempted? **Out of scope** — owned by plan 04 Phase 3 when other blockers have designs.

## Phases

### Phase 1 — Strip removes `timing` and `wall_s`; fixture JSON proves j1/j12 equality

- Outcome: A normalisation path shared by tests (and usable by the 3-90 check-3 script) removes every key in `COMPARE_EXCLUDES` (`timing` and `wall_s`) from a K1 report dict/JSON file and leaves all other content intact. Fixture-JSON unit tests (no disc, no spool, no encode) prove: (1) two reports that differ only in `timing` and/or `wall_s` compare equal after strip (canonical JSON / `cmp`); (2) two reports that also differ in any non-excluded field still compare unequal after strip; (3) a strip that removed only `timing` would leave a `wall_s` mismatch — the locked strip must not. Brief `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3 is amended so determinism equality is after excluding `timing` **and** `wall_s` (Phase 2 / `COMPARE_EXCLUDES`), not `timing` alone. Existing fixture tests that already use `_canon` / `COMPARE_EXCLUDES` keep passing. Disc sha unchanged. Plan 04 Phase 3 is not marked closed; PSS, classify, pins, oracle, and completeness blockers are untouched.
- Surfaces: `parser/tools/quantisation_roundtrip.py` (export or thin helper over `COMPARE_EXCLUDES` if needed), `parser/tests/test_quantisation_roundtrip.py` (or a sibling test module for pure JSON fixtures), `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3; optional one-line clarity in plan 04 `IMPLEMENTATION.md` or OVERVIEW only if required to stop teaching "timing only" as the live contract — not a phase-close claim.
- Approach: known
- Depends on: master tip with `COMPARE_EXCLUDES = ["timing", "wall_s"]` and Phase 2 determinism record (present at `4f8a03d`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `4f8a03d8c157d73da314b2613f6bba2dfaa4835f` (“docs: add plan 14 completeness root-cause design”).
- Candidate: Maps Quality Assessor tip on that commit — align 3-90 K1 determinism strip with Phase 2 `wall_s` exclusion; fixture-JSON unit highest leverage; runnable without full-AU / disc `4ed9cd80…` / completeness dumps. Also listed under plan 14 `NOTES.md` item 2 (3-90 blockers).
- Evidence cited (committed): `parser/tools/quantisation_roundtrip.py` (`COMPARE_EXCLUDES`, report `wall_s` + `timing`, module doc); `parser/tests/test_quantisation_roundtrip.py` (`_canon`, `test_j1_and_j4_are_byte_equal`, repeated-run pops); `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md` check 3; Phase 2 verification + multiple 3-90 blocked records in `IMPLEMENTATION.md` (timing-only strip; sole diff top-level `wall_s`); `docs/OVERVIEW.md` (retains varying `wall_s`); `docs/provenance.md` reproduce lines for scratch `strip_timing.py`; brief 3-02 / 2-06 already exclude both keys for dump-off / fixture compares.
- Rejected for this design: full 3-90 re-verify (needs disc, PSS, joins, pins); PSS ceiling redesign; native dump join reconstruction; completeness plan 14 Phase 1 (blocked on disc); SADSR plan 15 (separate schema unknown).
- Draft format followed: `/workspace/maps-design-drafts/15-sadsr-srmx-stfg/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
