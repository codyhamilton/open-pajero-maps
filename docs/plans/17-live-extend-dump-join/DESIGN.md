---
design_id:
---

# Switch live scratch-3-12 extend to tracked dump_join

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Switch live `output/scratch-3-12/extend.py` to the tracked `parser/tools/dump_join.py` residual adapter (thin wrapper, same pattern as plan 05's 3-07 scratch wrapper). Prove with plan-05 fixture SHA gates. Land on master. No feature branch. No pull request. No full-AU encode. Runnable without Cody disc rebuild or plan 14 completeness dumps.

## Problem

Plan 05 cut residual dump-join peak residency by landing tracked `parser/tools/dump_join.py` (windowed pread/pwrite, write-behind, no whole-file `copyfile` / whole-file memmap) and proving byte identity against the vendored baseline under `parser/tests/fixtures/dump_join_baseline/` (SHA256SUMS; `extend.py` = `1b13b844…`). Memory gates and `test_dump_join_memory.py` already lock that contract.

The **live** scratch entry point was deliberately left on the whole-file baseline: plan 05 Assumption 6 / brief 1-01 deferred switching `output/scratch-3-12/extend.py` until plan04 unit 3-13 accepted, so 3-13 readers of scratch-3-12 would not see an in-flight entry-point change. Plan 05 close-out still lists that switch as the first follow-up; residual risk text still says re-running the live whole-file script dirties multi-GiB cache (OOM / oomd pressure).

Unit **3-13** is on master with independent review **ACCEPT-WITH-CONDITIONS** (`docs/plans/04-c-core-orchestration/triage/review_3-13.md`); Conditions A–C are recorded closed under 3-13 in provenance / root-cause docs. The coordination gate that blocked the switch is cleared. The tracked adapter is already the durable semantics path; the live script is still the unsafe entry operators re-run.

This is an **entry-point harden follow-up**, not a new join algorithm and not a re-encode. Verified on `origin/master` at `f01ed41` from committed plan 05 / 3-13 / dump_join / fixture records — no live disc or completeness dump required. Plans **01–05** and **07–16** occupy those numbers on master; **06** is not a work unit. This plan is **17**.

## Solution shape

One bounded change: replace the live residual entry `output/scratch-3-12/extend.py` with a thin wrapper that invokes the tracked residual `dump_join` adapter (defaults unchanged: src `output/scratch-3-11/dump_new_ext`, side/assign/dst/counts under the 3-11 / 3-12 paths already hard-coded in `dump_join.DEFAULT_*`). Keep the vendored whole-file baseline frozen for replay. Close the plan 05 follow-up in the docs that still teach the live whole-file risk. Prove with existing plan-05 fixture SHA / pytest gates — no full-AU, no disc rebuild, no plan 14 completeness dumps.

### Domain: live residual entry point

- Owns: the gitignored operator entry `output/scratch-3-12/extend.py` that residual attribution / classify reproduce paths invoke (provenance scratch-3-12 reproduce list).
- Contract: invoking that path (or an equivalent documented one-liner via `parser/tools/dump_join.py` with residual defaults) runs the tracked residual adapter, not the whole-file `copyfile` + whole-destination memmap baseline. Byte146 / other-bytes / joined_counts / `extension_3_12` manifest semantics remain those already proven for `dump_join` vs the vendored baseline. The vendored fixture file `parser/tests/fixtures/dump_join_baseline/extend.py` stays the frozen whole-file oracle (SHA `1b13b844…`) and is **not** overwritten by the wrapper.
- Non-goals: no change to `dump_join` join/sort/cast/window contracts; no rewrite of side tables, rules, or classify; no reseat of dump_io; no full-disc residual re-extend as a phase gate; no deletion of historical dump_ext evidence.

### Domain: plan-05 fixture gates and follow-up docs

- Owns: the acceptance proof that the switch did not drift semantics, and the stable wording that no longer leaves the live whole-file script as the recommended path.
- Contract: `sha256sum -c` on `parser/tests/fixtures/dump_join_baseline/SHA256SUMS` passes; `pytest parser/tests/test_dump_join_memory.py` (and sibling plan-05 small correctness tests already named in WORKFLOW) still pass. Plan 05 follow-up / residual-risk lines that say the live extend is still whole-file are updated to record the switch. Provenance scratch-3-12 reproduce may name the wrapper / tracked CLI when that section is touched; historical plan 05 records stay history.
- Non-goals: no re-run of the 1,000,013-row memory bench as a hard gate (already closed in plan 05); no plan 14 Phase 1 re-open; no 3-90 / Phase 3 close; no WORKFLOW scheduler redesign.

## Decisions

1. Plan number is **17**. Standalone plan; it **closes** the plan 05 live-extend follow-up, it is not a mega Phase-3-close plan and not a rewrite of plan 05.
2. Land on master directly. No feature branch. No pull request.
3. One phase. Refine skipped (approach known — same thin-wrapper pattern plan 05 already used for `output/scratch-3-07/extend_dump_attempt3.py`).
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close.
5. Gates are plan-05 fixture SHA + existing `test_dump_join_memory` suite. No full-AU encode; no Cody disc rebuild; no completeness dumps.
6. Assigned instance for this lane's workers is OpenCode DeepSeek Flash (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: can this close without remounting a disc, re-encoding AU, or re-running plan 14 completeness dumps?
- Answer chosen: yes. Semantics and memory cuts are already proven on tracked fixtures and `dump_join`. This plan only switches the live entry and updates follow-up docs.
- Rationale: ticket and Maps Quality Assessor require runnable without Cody disc rebuild / completeness dumps; plan 14 Phase 1 evidence is already closed on master (`f01ed41`) and is out of scope here.
- If wrong: Cody supplies an existing `scratch-3-12` tree; wrapper still must not require a new encode — at most an optional evidence-only --verify on existing dumps, never a phase gate.

### Assumption 2

- Question: rewrite live `extend.py` in place as a thin wrapper, or delete it and document only the tracked CLI?
- Answer chosen: thin wrapper at `output/scratch-3-12/extend.py` invoking tracked residual `dump_join.main` / residual defaults (mirror 3-07), so existing provenance reproduce lines that call `extend.py` keep working. Document the tracked CLI as the durable equivalent.
- Rationale: plan 05 Phase 3 already established the thin-wrapper pattern for scratch entry points; brief 1-01 deferred exactly this switch of the ignored scratch entry.
- If wrong: Cody prefers CLI-only; still remove or quarantine the whole-file script so it cannot be re-run by accident, and keep fixture gates.

### Assumption 3

- Question: what if `output/scratch-3-12/` is absent on the Execute host (as on this design box)?
- Answer chosen: create only the minimal gitignored path needed for the wrapper file (or restore from Cody's tree if present). Do **not** regenerate multi-GiB dumps, side tables, or classify outputs as part of this plan. Fixture SHA / pytest remain the semantic gate.
- Rationale: dumps are regenerable evidence (provenance); the defect is the entry script, not missing dump bytes on every agent box.
- If wrong: Cody restores the scratch tree first; Execute still only replaces `extend.py` and runs fixture gates.

### Assumption 4

- Question: does switching the live entry require re-proving the 1M-row RSS / `memory.peak` gates?
- Answer chosen: no. Plan 05 Phase 1 already closed those gates for `dump_join` vs the vendored baseline. This plan re-checks the small fixture SHA / pytest contract so the wrapper cannot point at a drifted adapter.
- Rationale: ticket asks for plan-05 fixture SHA gates and explicitly avoids full-AU / heavy confirmation as acceptance.
- If wrong: Cody orders an optional `bench_dump_memory.py` residual re-run under `output/.heavy.lock` as evidence-only — still not absorbed as a new algorithm phase.

### Assumption 5

- Question: does ACCEPT-WITH-CONDITIONS on 3-13 block the switch?
- Answer chosen: no. The blocking concern was concurrent mutation of scratch-3-12 while 3-13 ran. 3-13 review and root-cause records are on master; Conditions A–C are closed in the recorded follow-up path. This plan does not reopen 3-13 science or alter rules/side tables.
- Rationale: plan 05 follow-up text is "after plan04 3-13 is accepted"; ticket states 3-13 accepted on master; review verdict is ACCEPT-WITH-CONDITIONS with no high-severity defects.
- If wrong: Cody names a remaining 3-13 condition that still forbids touching the entry; then hold this plan and keep the follow-up open.

## Open questions

1. Should the closed plan 05 markdown follow-up bullet be edited in place, or only WORKFLOW / provenance / a one-line IMPLEMENTATION note under this plan? **Default:** update the live docs operators read (WORKFLOW residual-risk / limitations if still naming the live whole-file script; provenance scratch-3-12 reproduce when touched) and record the follow-up closed in this plan's IMPLEMENTATION — do not rewrite plan 05 history beyond a factual "follow-up landed in plan 17" pointer if a pointer is needed. Not a phase gate either way.
2. After the wrapper lands, when should a full residual re-extend on Cody's host be attempted? **Out of scope** — evidence-only under heavy lock if Cody orders it; not this plan's acceptance.

## Phases

### Phase 1 — Live extend is dump_join; plan-05 fixture SHA gates hold

- Outcome: `output/scratch-3-12/extend.py` is a thin wrapper over the tracked residual `dump_join` adapter (same defaults as `dump_join.DEFAULT_SRC` / `DEFAULT_SIDE` / `DEFAULT_ASSIGN` / `DEFAULT_DST` / `DEFAULT_COUNTS`), not the whole-file baseline. Invoking that entry (or `parser/tools/dump_join.py` with residual defaults) cannot reintroduce `shutil.copyfile` of the full dump or a whole-destination read-write memmap touch of every row. Vendored `parser/tests/fixtures/dump_join_baseline/{extend,study,witness}.py` SHAs remain exactly the tracked `SHA256SUMS` (`extend.py` `1b13b844…`, `study.py` `f9ae5776…`, `witness.py` `42d33e39…`). `pytest parser/tests/test_dump_join_memory.py -q` passes (candidate matches baseline bytes/counts; window sizes; collide-after-wrap; empty-kind rejection; verify mode; replay-root refusal). Docs that still list the live whole-file extend as an open plan 05 follow-up / residual OOM risk are updated so the live path is the wrapper / tracked CLI. Disc sha unchanged. No full-AU encode. No plan 14 completeness dumps. Plan 04 Phase 3 not marked closed. 170 / 3-16 / 3-17 not reseated.
- Surfaces: gitignored `output/scratch-3-12/extend.py` (wrapper only); docs touched only as needed to close the follow-up (`docs/WORKFLOW.md` and/or `docs/provenance.md` scratch-3-12 reproduce / plan 05 residual-risk pointer; this plan folder under `docs/plans/17-live-extend-dump-join/` when Execute lands). Tracked `parser/tools/dump_join.py` and fixture trees are **read-for-gate** unless a one-line import-path fix is required for the wrapper — no semantic edit.
- Approach: known
- Depends on: master tip with plan 05 adapters + fixtures and 3-13 acceptance records (present at `f01ed41`).
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `f01ed416f2530e7af3593cd2b1dd2286365816b0` (“Close plan 14 Phase 1 completeness evidence table”).
- Candidate: Maps Quality Assessor ticket — switch live scratch-3-12/extend.py to tracked dump_join (harden); plan 05 follow-up; 3-13 accepted on master; OOM risk on whole-file extend; small plan with plan-05 fixture SHA gates; no full-AU; runnable without Cody disc rebuild / completeness dumps for plan 14 Phase 1.
- Evidence cited (committed): `docs/plans/05-heavy-job-memory.md` (deviation + follow-up: live extend not switched; residual OOM risk); `/workspace/plan05/DESIGN.md` Assumption 6 / Phase 1 surfaces; `/workspace/plan05/briefs/1-01.md` (switch deferred after 3-13); `/workspace/plan05/IMPLEMENTATION.md` Phase 1 deviation item 1; `parser/tools/dump_join.py` (`DEFAULT_*` residual paths, `extend_residual`, CLI); `parser/tests/fixtures/dump_join_baseline/SHA256SUMS` + vendored `extend.py`; `parser/tests/test_dump_join_memory.py`; `docs/WORKFLOW.md` Heavy jobs / fixture SHA list; `docs/ARCHITECTURE.md` bounded dump I/O; `docs/provenance.md` scratch-3-12 dump extension + reproduce (`extend.py`) and scratch-5-01 baseline note; `docs/plans/04-c-core-orchestration/triage/review_3-13.md` (ACCEPT-WITH-CONDITIONS); plan 05 Phase 3 thin-wrapper precedent for `extend_dump_attempt3.py`.
- Rejected for this design: full residual re-extend on live dumps as acceptance; re-opening plan 05 memory algorithm work; name_anchor L0 `(0,541)` / leaf 928 extractor fix (Quality ticket 3 — separate; only drawable if this ticket were already done); plan 14 completeness science; plan 15/16 reseat; 3-90 / Phase 3 close; unsigned plan 04 phases 4–6 / plan 06.
- Draft format followed: `/workspace/maps-design-drafts/16-k1-determinism-wall-s/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
