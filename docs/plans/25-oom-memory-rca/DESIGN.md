---
design_id:
---

# OOM recovery RCA — plan-14 completeness OpenCode stopped

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

OOM recovery RCA after Coding Harness Manager stopped the live plan-14 completeness OpenCode for host memory pressure. Heavy Maps jobs stay on hold until this RCA lands outcomes and CHM clears the hold. Bounded design: evidence inventory, small-harness peak reproduce, leak/spike class, **concrete guards** (Flash argv + `memory.peak` wrapper; bound/stream plan-14 triage ALLDATA/spool loads), and CHM hold-lift criteria. Cody via Primary (2026-10-06) widened past harness-only: land those guards on master in this plan. No full plan-14 completeness re-run. No seating heavy completeness seats until CHM clears. Land on master. No feature branch. No pull request. Do not reseat 170 / 3-16 / 3-17. Do not draw plan 04 P4–6 or plan 06. Do not claim Phase 3 closed. Do not restart plan 14 Phase 2/3 science in this design.

## Problem

**Incident (named):** Coding Harness Manager stopped the live **plan-14 completeness** heavy OpenCode seat for OOM / host memory pressure. Heavy Maps jobs (including further plan-14 completeness seats) are **on hold** until a memory RCA finishes and CHM clears the hold. Assigned instance for this lane remains OpenCode DeepSeek Flash; Design may ticket RCA only — no heavy completeness seats until RCA clears.

What already exists on master is memory **mitigation and ops contract** history, not an attribution of *this* stop:

| Surface (on master) | What it already proves | Gap vs this incident |
| --- | --- | --- |
| Plan **05** `docs/plans/05-heavy-job-memory.md` | Windowed dump_join / finalize / 3-07 / triage cut peak RSS + `memory.peak` on seeded fixtures; `output/.heavy.lock` + scoped `systemd-run` discipline; gates in `bench_dump_memory.py` | Gates cover residual/finalize/s07/triage fixture classes — not the plan-14 completeness OpenCode job class that was stopped |
| Plan **17** `docs/plans/17-live-extend-dump-join.md` | Live `scratch-3-12/extend.py` is thin wrapper over tracked residual `dump_join` (whole-file baseline retired) | Entry harden only; does not measure plan-14 completeness reproducers |
| Plan **14** Phase 1 (`IMPLEMENTATION.md`) | Fresh full-AU encode under `flock output/.heavy.lock` (encode ~119 s, assemble ~13.5 s, `-j4`) re-hit oracle `4ed9cd80…`; completeness-only dump under flock `-j6` → 776 failing identities | Records that heavy encode+dump *ran* under lock; does **not** publish peak RSS / `memory.peak` / PSS for that encode, the dump, or later Phase 2 unit workloads |
| Plan **14** Phase 2 unit **2-01** (closed on master) | Cell-local R membership + mechanism note for `g-omits-cell-local-dvd-type` | Science packet; not a memory profile of the OpenCode seat that CHM stopped |
| Plan **20** `docs/plans/20-reconcile-pss-ops-cap.md` | Signed PSS ceiling **9,726,501 kB** stays absolute; live 3-90/ops K1 gates use ≤ `-j 6`; framed as contract mismatch, not unexplained blow-up | PSS ceiling ≠ host oomd stop of a completeness OpenCode; bar not claimed cleared |
| `docs/WORKFLOW.md` Heavy jobs / `docs/ARCHITECTURE.md` oomd section | One heavy under `flock output/.heavy.lock`; RSS vs `memory.peak`; siblings can die first under oomd | Operational law; no hold-lift criteria for *this* CHM hold |

Without a bounded RCA, CHM cannot distinguish “plan-05 class already fixed, this stop was concurrent pressure / lock skip / new spike class” from “completeness OpenCode path still unsafe to reseat.” A full plan-14 Phase 2/3 re-run would itself be another heavy completeness seat — exactly what the hold forbids.

Verified on `origin/master` at `022a8af` from committed plan 05 / 14 / 17 / 20 / WORKFLOW / ARCHITECTURE / OVERVIEW records — no disc mount or full-AU re-encode required for the design. Plans **01–05** and **07–22** occupy those numbers on master; `/workspace/maps-design-drafts/` has **23** (copy-through graphics cmp); **24** reserved soft for a possible pickle draft in flight; **06** is not a work unit. This plan is **25**.

## Solution shape

One bounded memory-incident RCA package: name the stop, inventory the master evidence surfaces above (including `/workspace/maps-oom-2026-10-06.md` host facts when copied into the plan folder), reproduce **peak residency of the stopped job class** in a **small harness** (not a full plan-14 completeness re-run), classify the leak/spike, **land concrete guards** so the next Flash/completeness seat cannot silently whole-file-load ALLDATA/spool and so argv + `memory.peak` are always recorded, and publish **hold-lift criteria** for CHM. Hold clear still needs a **named + capped path** **or** harness ceiling proof, **plus CHM explicit clear**. Prefer offline fixtures / windowed samples / existing plan-05 controllers. Do not restart plan 14 Phase 2/3 science. Do not claim Phase 3 or 3-90 PSS cleared.

### Domain: incident evidence inventory

- Owns: the committed record of what the stop was, which master surfaces already constrain memory, and which metrics are still missing for the stopped job class.
- Contract: (1) Incident name string stable and greppable: **plan-14 completeness heavy OpenCode stopped for OOM** (CHM hold on heavy Maps jobs pending this RCA). (2) Inventory table (or equivalent note under this plan) cites plan 05 gates, plan 17 live-extend close, plan 14 Phase 1 flock encode+dump facts, plan 20 PSS/ops split, WORKFLOW lock / ARCHITECTURE oomd — each with “proves / does not prove.” (3) Stopped **job class** named for measurement: the OpenCode completeness workload class CHM stopped (plan-14 Phase 2-style heavy Python under flock — cell-local / complete-repair / related dump or encode paths as recorded in CHM stop notes or plan-14 briefs), distinct from plan-05 residual/finalize fixture classes. (4) No claim that plan 05 alone clears the hold.
- Non-goals: no rewriting plan 05/14/17/20 history beyond factual pointers; no plan 14 Phase 2/3 restart; no 3-90 re-run.

### Domain: bounded peak-residency harness

- Owns: a small, serial, flock-held measurement that reproduces peak residency **of the stopped job class** without re-running full plan-14 completeness attribution.
- Contract: (1) Harness runs under `flock output/.heavy.lock`, preferably `systemd-run --user --scope -p MemoryAccounting=yes`, K1/cbuild caps unchanged (≤ `-j6` / ≤ `-j4`). (2) Workload is a **bounded stand-in** for the stopped class (e.g. windowed/sample cell-local or complete-repair over a fixed small key set, or a documented minimal subset of the OpenCode path) — **not** 776-row full membership, **not** full-AU encode as acceptance, **not** reseating plan-14 Phase 2/3. (3) Records max RSS (KiB) and cgroup `memory.peak` (and `memory.stat` anon/file/file_dirty when available); optional comparison to plan-05 fixture peaks for the nearest related class. (4) Outcome states whether peak is consistent with plan-05 mitigated patterns, a new spike class, lock/concurrency violation, or inconclusive — with the evidence paths named.
- Non-goals: no changing dump_join / finalize / triage algorithms unless a later fix plan is opened after this RCA; no inventing PSS margin; no machine-wide MemoryMax.

### Domain: concrete memory guards (Cody widen)

- Owns: landable mitigations that make the stopped job class safer **without** reseating full plan-14 Phase 2/3 science: (1) Flash/OpenCode argv + `memory.peak` wrapper for heavy Python under `flock output/.heavy.lock`; (2) bound/stream (or mmap-window / chunked) loads in plan-14 triage scripts that today can whole-file ALLDATA / completeness spool into anon RSS.
- Contract: (1) A tracked wrapper (or WORKFLOW-mandated one-liner) records full argv, start/end wall time, max RSS, and cgroup `memory.peak` for every heavy Maps Python invocation that uses the lock; missing peak → job fails closed or is documented as non-compliant. (2) Plan-14 triage paths that previously did whole-file ALLDATA or spool materialization either stream/window with an explicit byte/row cap, or refuse to run without `--window` / sample args that keep peak under a published KiB ceiling for the stand-in class. (3) Unit or small-fixture tests prove the wrapper records peak and that a deliberately oversized whole-file load is rejected or streamed. (4) These guards land on master in this plan — they are not deferred to a follow-up after harness-only RCA.
- Non-goals: no full 776-row Phase 2 science; no full-AU encode as acceptance; no raising plan-20 PSS ceiling; no auto CHM hold-clear.

### Domain: leak/spike class + CHM hold-lift criteria

- Owns: the classification CHM needs, and the written criteria that must be true before heavy completeness may be reseated.
- Contract: (1) Leak/spike class is one of a closed set recorded in the plan note, e.g. **anonymous spike** / **page-cache dirty** / **multiprocess PSS sum** / **concurrent lock skip** / **new completeness-path class** / **inconclusive — needs Cody sample** — each tied to harness evidence. (2) **Hold-lift criteria** (proposed for CHM) are explicit, checkable statements — at minimum: (a) this plan’s Phase outcomes closed on master; (b) harness peak for the stopped job class is published and classified; (c) if class is mitigated by existing plan-05 discipline, WORKFLOW lock + scope recipe is confirmed for the seat; (d) **named + capped path** is landed (concrete guards domain) **or** harness ceiling proof for the stopped class is published; (e) if residual new class remains after guards, a follow-up fix design exists **or** Cody/CHM accepts a bounded mitigation; (f) **CHM explicitly clears the hold** — landing this RCA alone does not auto-reseat. (3) Design and docs state: **do not seat heavy completeness OpenCode (plan 14 Phase 2/3 or equivalent) until (a)–(f)**.
- Non-goals: no CHM policy rewrite beyond proposed criteria; no auto-clear; no Phase 3 / plan 14 completeness close by side effect.

## Decisions

1. Plan number is **25**. Soft-skip **24** (possible pickle draft in flight; absent from drafts at authoring). Master occupies 01–05, 07–22; draft **23** is graphics cmp. Standalone RCA; does not absorb draft 23, plan 14 science, or plan 20 PSS clear.
2. Land on master directly when Execute later builds it. No feature branch. No pull request.
3. Four phase slots (1, 2, 2b, 3). Phase 1–2 approach known for inventory + harness; Phase 2b lands concrete guards (Cody widen); Phase 3 hold-lift criteria. Phase 2 classification may be refined if harness surprises.
4. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write a mega 3-90 Phase-3-close. Do **not** restart plan 14 Phase 2/3 in this design.
5. Prefer small harness + existing plan-05 measurement patterns. Full-AU encode and full 776-row completeness dumps are **forbidden as acceptance** for this RCA.
6. Explicit forbid: seat **no** heavy completeness OpenCode until RCA phase outcomes land **and** CHM clears the hold.
7. Assigned instance for this lane’s workers is OpenCode DeepSeek Flash (Design does not start workers; Design does not post workflow seats for heavy completeness).

## Assumption ledger

### Assumption 1

- Question: must acceptance re-run full plan-14 Phase 1 encode + completeness dump, or full Phase 2 unit 2-02 complete-repair over all 432 seeds?
- Answer chosen: **no**. Acceptance is evidence inventory + bounded small-harness peak reproduce + class + hold-lift criteria. Full completeness re-runs remain under CHM hold.
- Rationale: ticket forbids full plan-14 completeness re-run as phase outcome; hold exists precisely because that class OOMed.
- If wrong: Cody/CHM orders one evidence-only scoped sample under flock still smaller than a full seat — still not Phase 2/3 restart; still not auto hold-lift.

### Assumption 2

- Question: is the stopped job class the plan-14 Phase 1 full-AU encode, the completeness dump, Phase 2 OpenCode (2-01/2-02 style), or concurrent siblings?
- Answer chosen: treat CHM’s named stop as **plan-14 completeness heavy OpenCode** (Phase 2-style completeness seat). Phase 1 encode under flock is inventory evidence (it ran; peaks unpublished). Concurrent sibling kill remains a possible class the harness must be able to distinguish (scope vs session oomd).
- Rationale: incident text names plan-14 completeness OpenCode stopped; 2-01 already closed on master before the hold narrative.
- If wrong: Phase 1 inventory rewrites the job-class label from CHM notes without changing the no-full-rerun rule.

### Assumption 3

- Question: may this plan lift the CHM hold itself when phases close?
- Answer chosen: **no**. This plan **proposes** hold-lift criteria; **CHM clears** the hold. Landing DESIGN/IMPLEMENTATION does not reseat heavy completeness.
- Rationale: ticket: “until RCA outcomes land and CHM clears the hold.”
- If wrong: none — still must not silently reseat.

### Assumption 4

- Question: raise signed PSS ceiling or relax ops ≤ `-j 6` because of this OOM?
- Answer chosen: **no**. Plan 20 contract stands. This RCA does not re-sign PSS or widen worker caps.
- Rationale: plan 20 framed PSS as contract mismatch; oomd stop of OpenCode is a different surface (RSS/`memory.peak`/session pressure).
- If wrong: separate Cody-signed design; do not invent margin here.

### Assumption 5

- Question: implement memory-cut / guard code in this plan, or stop at harness-only RCA?
- Answer chosen: **land concrete guards in this plan** (Cody via Primary 2026-10-06 widen): (1) Flash argv + `memory.peak` wrapper for heavy Python under flock; (2) bound/stream plan-14 triage ALLDATA/spool loads so whole-file anon spikes are capped or refused. Still **no** full plan-14 Phase 2/3 science restart and **no** second plan-05 rewrite of dump_join/finalize unless Phase 2 proves that exact path is the named class and a tiny patch closes it.
- Rationale: Manager/Primary: do not stop at harness; land guards now so Execute can put them on master. Hold clear still needs named+capped path **or** harness ceiling proof, plus CHM.
- If wrong: Cody narrows back to harness-only; drop Phase 2b guards and keep Phase 2 harness + Phase 3 criteria — still no Phase 2/3 science restart.

### Assumption 6

- Question: may this plan claim plan 04 Phase 3 closed, plan 14 Phase 2/3 closed, or 3-90 PSS PASS?
- Answer chosen: **no**.
- Rationale: standing rule and ticket forbids; OVERVIEW blockers remain.
- If wrong: none — still must not claim those closes.

## Open questions

1. Exact CHM stop timestamp / host journal snippet (oomd unit vs kernel OOM vs manual stop) — **Phase 1** cites if available on the host; absence → class may stay “inconclusive on killer” while harness peaks still publish.
2. Whether a follow-up fix plan is required after classification — **Phase 2/3** answers; out of scope to author that fix design here unless Assumption 5 trivial path.

## Phases

### Phase 1 — Incident named; master evidence inventory committed

- Outcome: Plan folder `docs/plans/25-oom-memory-rca/` records the incident name (**plan-14 completeness heavy OpenCode stopped for OOM**; CHM heavy-Maps hold pending RCA). A committed inventory cites plan 05 dump_join memory gates, plan 17 live-extend, plan 14 Phase 1 flock encode+dump facts, plan 20 PSS/ops notes, WORKFLOW `output/.heavy.lock`, and ARCHITECTURE oomd — each with proves/does-not-prove vs this stop. Stopped job class label is explicit and distinct from plan-05 fixture classes. No full-AU encode. No plan-14 Phase 2/3 restart. No heavy completeness seat. No Phase 3 close. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated.
- Surfaces: this plan’s DESIGN (lands with Execute) + short inventory note under `docs/plans/25-oom-memory-rca/` (and optional one-line WORKFLOW / OVERVIEW pointer that a CHM hold exists pending plan 25 — **without** claiming clear). Plan 05/14/17/20 records are **read-only** except factual “cited by plan 25” pointers if needed.
- Approach: known
- Depends on: master tip with plans 05, 14, 17, 20, 22 present (`022a8af` ground).
- Refine: skipped for this phase.

### Phase 2 — Peak residency of stopped job class reproduced in small harness; leak/spike class identified

- Outcome: Under `flock output/.heavy.lock` (scoped worker recommended), a **small harness** runs a bounded stand-in of the stopped completeness OpenCode job class and records max RSS + `memory.peak` (and available `memory.stat`). Result is **not** a full plan-14 completeness re-run (no full-AU acceptance encode; no full 776/432 membership gate). A committed note names the leak/spike class from the closed set (anonymous spike / page-cache dirty / multiprocess PSS sum / concurrent lock skip / new completeness-path class / inconclusive). Comparison to nearest plan-05 fixture peaks is stated when meaningful. No encoder/checker/rules edits. No plan 14 Phase 2/3 science close. No CHM hold auto-clear. No Phase 3 close.
- Surfaces: measurement script or reuse of `parser/tools/bench_dump_memory.py` patterns under plan-25 scratch (`output/scratch-25/` git-ignored); committed note/report under `docs/plans/25-oom-memory-rca/`; tests only if a tiny fixture controller is added (optional). Completeness triage scripts and discs are **read-only** inputs for sampling keys if needed.
- Approach: known (harness shape); classification **open** if peaks surprise — refine only the class label against Phase 2 outcome, not a new full workload.
- Depends on: Phase 1 inventory + job-class label.
- Refine: only if class set must split; yardstick stays “class named from harness evidence.”

### Phase 2b — Concrete guards land on master (Cody widen)

- Outcome: On master: (1) a Flash/OpenCode **argv + `memory.peak` wrapper** (or equivalent tracked helper + WORKFLOW recipe) is required for heavy Maps Python under `flock output/.heavy.lock`, recording argv, wall time, max RSS, and cgroup `memory.peak`; (2) plan-14 triage scripts that load ALLDATA / completeness spool **bound or stream** (window/chunk/cap) instead of whole-file anon materialization, or refuse without explicit sample/window args that keep peak under the published stand-in ceiling; (3) fixture or unit proof that the wrapper records peak and that an uncapped whole-file path fails closed or streams. Host evidence note `/workspace/maps-oom-2026-10-06.md` (or a copy under the plan folder) is cited. No full plan-14 Phase 2/3 science. No full-AU acceptance encode. No CHM auto-clear. No Phase 3 close.
- Surfaces: wrapper under `parser/tools/` (or `scripts/`), plan-14 triage load sites under `docs/plans/04-c-core-orchestration/triage/`, WORKFLOW heavy-jobs recipe, tests under `parser/tests/`, plan-25 note.
- Approach: known
- Depends on: Phase 1 inventory; preferably Phase 2 class (may land in parallel with Phase 2 if class is already “anonymous spike / whole-file load” from host evidence).
- Refine: skipped unless a specific triage loader needs a short approach note.

### Phase 3 — Hold-lift criteria published; heavy completeness remains forbidden until CHM clears

- Outcome: Committed **hold-lift criteria** for CHM include at least: (1) plan 25 Phases 1–2 closed on master; (2) published peak + named leak/spike class for the stopped job class; (3) Phase 2b concrete guards landed (**named + capped path**) **or** harness ceiling proof alone if Cody re-narrows Assumption 5; (4) if mitigated by existing discipline, flock + scope recipe confirmed for any future seat; (5) if residual new class remains after guards, follow-up fix design filed **or** Cody/CHM-accepted mitigation recorded; (6) **CHM explicit clear** required — this phase does not reseat. Docs state **forbid seating heavy completeness** (plan 14 Phase 2/3 or equivalent OpenCode) until criteria (1)–(6). No heavy completeness worker started by this plan. No plan 14 Phase 2/3 science restart. No Phase 3 / 3-90 / PSS-PASS claim. No plan 04 P4–6 / plan 06. 170 / 3-16 / 3-17 not reseated.
- Surfaces: hold-lift section in plan-25 report / IMPLEMENTATION; optional WORKFLOW “CHM hold” sentence pointing at plan 25 criteria (hold not claimed cleared).
- Approach: known
- Depends on: Phase 2 class + Phase 2b guards (unless Assumption 5 re-narrowed).
- Refine: skipped.

## Provenance

- Ground tip read: `origin/master` `022a8af63c7a79c40e642214d663c32221a0ca0d` (“Close out plan 20: collapse PSS ops-cap reconcile record”); plan **22** harness map-only honesty already on master as collapsed record.
- Candidate: Coding Harness Manager — OOM recovery; heavy Maps jobs on hold until memory RCA; plan-14 completeness heavy OpenCode stopped; Design may ticket RCA only; assigned OpenCode DeepSeek Flash.
- Evidence cited (committed): `docs/plans/05-heavy-job-memory.md` (gates, lock, RSS/`memory.peak`); `docs/plans/17-live-extend-dump-join.md` (live extend → dump_join); `docs/plans/14-completeness-root-cause.md` (Phase 1 flock full-AU encode + `-j6` dump; Phase 2 refine; 2-01 closed); `docs/plans/20-reconcile-pss-ops-cap.md` + WORKFLOW Signed PSS vs ops ≤ `-j 6`; `docs/ARCHITECTURE.md` Why RSS alone was the wrong story (oomd); OVERVIEW plan 14 open / Phase 3 blocked.
- Cody via Primary / Maps Manager 2026-10-06: widen past Assumption 5 harness-only — land Flash argv+memory.peak wrapper and bound/stream plan-14 triage ALLDATA/spool loads in this plan. Hold clear still needs named+capped path OR harness ceiling proof + CHM.
- Host evidence: `/workspace/maps-oom-2026-10-06.md` (python ≈6.5GiB; cursor killed; plan-14 Phase 2 / 2-02 window).
- Rejected for this design: full plan-14 completeness re-run as RCA acceptance; reseating heavy completeness OpenCode before CHM clear; restarting plan 14 Phase 2/3 science here; raising PSS ceiling; claiming Phase 3 / 3-90 PSS PASS; reseating 170 / 3-16 / 3-17; drawing plan 04 P4–6 or plan 06; absorbing draft 23 graphics; claiming NN 24 (pickle soft-reserve).
- Draft format followed: `/workspace/maps-design-drafts/23-copy-through-graphics-cmp/DESIGN.md` and `/workspace/maps-design-drafts/22-harness-map-only-honesty/DESIGN.md`.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated. Plan 14 Phase 2/3 not restarted here.
- NN verification: `origin/master` occupies 01–05, 07–22; `/workspace/maps-design-drafts/` has through **23** (graphics); **24** not present but flagged pickle-in-flight → this draft is **25**.
