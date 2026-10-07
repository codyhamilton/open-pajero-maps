---
design_id:
---

# Cross-phase peak RSS + concurrent residency ledger

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody via Primary (2026-10-07), top focus verbatim:

> memory profiling → optimisation designs.
> Run agents that carefully profile peak RSS / spikes across Maps phases (mass_decide, representability, control, encode, dump/extend). Prove what is resident concurrently — don’t assume. Then produce designs that avoid keeping all data in memory at once (chunk/stream, free between phases, mmap, drop intermediates).
> Keep designs list filled with those optim packages. No seat ask — wait for CHM instance. Report findings + design branches to Maps Manager / Primary when first ones are draw-ready.

This plan is the **profiling package** whose outcome is a proven peak-RSS and concurrent-residency ledger across those phases. Optim packages are separate designs (**57+**). Live heavy measurements are **Execute-owned once CHM assigns a seat** — Design does not start seats, does not ask for a seat, and does not run heavy encode / mass / completeness jobs from this draft.

DVD parity; every deviation needs proven RC; no waivers. Master direct; flock + `run_heavy_python.py`; `-j4`; no plan 04 P4–6; no 3-90 re-run; no reseat 170 / 3-16 / 3-17. Assigned Execute harness: OpenCode DeepSeek Flash (constraint only).

## Problem

Memory evidence on tip is **band-fragmented**:

| Band | Published evidence | Gap vs Primary ask |
| --- | --- | --- |
| Dump/extend (plan **05**) | Fixture RSS/`memory.peak` gates; windowed `dump_io` | Not a cross-phase product ledger; finalize still one full kind array (ARCHITECTURE deferred) |
| Completeness stop (plan **25**) | ~6.5 GiB unnamed argv; cell_local stand-in ~60–70 MiB; guards landed | Job class ≠ mass_decide / encode / control / representability |
| Encode (plan **48** P2 benches) | AU `peak_rss_tree_mb` **15240.1**; Perth **13809.5** via `bench_build.py` | Tree peak only — no phase tags, no co-resident object ledger |
| mass_decide (plan **44** Unit 4c) | ~17.1 GiB host RSS at 30k/95059 leaves; `cache-clear-every` patched | No proven breakdown of spool caches vs discs vs probes vs parent |
| control / representability | Control Gates A+B closed; `k1_representable.py` exists | **No** published peak RSS for control mass-neighbourhood or full representability/K1 passes |

Without a serial, flock-held, phase-tagged ledger that **proves co-residency** (not assumptions), follow-on optim plans cannot claim a dominant resident set. Plan 25 alone does not answer Primary’s cross-phase ask.

Ground: `origin/master` `094b11f`; plan 05 / 25 / WORKFLOW Heavy jobs / ARCHITECTURE oomd present; tools `run_heavy_python.py`, `bench_dump_memory.py`, `bench_build.py`, `whole_file_guard.py` on tip. Host inventory allowed; **no** Design-started heavy RSS jobs.

## Solution shape

One measurement package: extend (or compose) existing wrappers into a **phase ledger** that records, per named phase invocation: max RSS, cgroup `memory.peak`, `memory.stat` anon/file/file_dirty when available, process-tree peak (encode), wall, argv, and a **concurrent residency table** built from evidence (sampler snapshots, explicit size accounting of named structures, or before/after free deltas) — never from “we assume X was dropped.”

### Domain: phase catalog + measurement recipe

- **Owns:** the named phase list and the exact entrypoints Execute may measure under flock + wrapper once CHM seats.
- **Contract:**
  1. Phase labels match Primary: **mass_decide**, **representability**, **control**, **encode**, **dump/extend**.
  2. Entrypoints (as on tip — do not invent alternates):
     - mass_decide → `docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/mass_decide.py`
     - control → `…/p5_owner_exclusive/control.py`
     - representability → callers of `parser/tools/k1_representable.py` / K1 path in `parser/tools/quantisation_roundtrip.py` (name the exact argv Execute uses; if only a bounded stand-in is CHM-allowed, label it stand-in)
     - encode → `parser/build_alldata.py` (optionally under `parser/tools/bench_build.py`)
     - dump/extend → `parser/tools/dump_join.py` and/or `_finalize_dump` via `bench_dump_memory.py finalize-run` / live residual CLI
  3. Every heavy invocation: `flock output/.heavy.lock` via `parser/tools/run_heavy_python.py` (or encode recipe that still records peak + argv). Missing `memory.peak` → fail closed.
  4. **Serial only** — one heavy at a time. Caps: encode `-j4`; K1 ≤ `-j6` where applicable. No stacking beside plan 44/48 seats.
  5. Live full-AU / full-mass / full-K1 runs **wait on CHM seat assignment**. Design never posts seat asks.
- **Non-goals:** implementing optim cuts in this plan; raising PSS ceiling; reseating plan-14 Phase 2/3 science; claiming CHM hold cleared.

### Domain: concurrent residency ledger

- **Owns:** proof of what is co-resident at peak (and at named phase boundaries).
- **Contract:**
  1. For each phase run, publish a ledger with rows = named resident classes (examples: spool cell/key caches; E1Spool mmap; worker Pool children; disc frame maps; dump windows; finalize kind array; probe modules). Each row has: evidence method (size accounting / before-after free / `/proc/<pid>/smaps` rollup / sampler), bytes or KiB, and whether it was **still live at peak**.
  2. **Forbidden:** “assumed freed after level N” without a measured delta or explicit teardown + re-sample.
  3. At least one **inter-phase boundary** sample where Execute deliberately finishes phase A, forces known frees (e.g. `clear_spool_caches`, closing readers), then starts phase B under the same scope recipe — to separate leftover residency from true overlap.
  4. Outcome artefact under `docs/plans/56-cross-phase-rss-profile/` (and scratch logs under `output/scratch-56/` gitignored): JSON/MD ledger + per-run wrapper logs.
- **Non-goals:** inventing new RSS metrics that ignore WORKFLOW (must still gate RSS and `memory.peak`); machine-wide MemoryMax.

### Domain: publish peaks → unlock optim drafts

- **Owns:** the handoff surface that plans **57+** consume.
- **Contract:**
  1. A committed summary table: phase → max RSS → memory.peak → tree peak if any → dominant ledger rows → “optim candidate ids (57/58/59)”.
  2. Explicit **unknown** cells remain labelled unknown (no fill-in from plan-05 fixture peaks).
  3. Does not itself land production memory cuts — only measurement + docs.
- **Non-goals:** DVD/oracle changes; residual row discharges.

## Decisions

1. Plan number **56**. Standalone profiling; does not absorb 57–59 optim bodies.
2. Master direct when Execute builds. No feature branch. No PR.
3. Three phases: catalog+harness recipe; serial measured ledger (CHM-gated live); publish summary + Cross-refs to 57–59.
4. Prefer composing `run_heavy_python.py` + `bench_build.py` + plan-05 controllers over a greenfield profiler.
5. Do not bump mass R default for memory (plan 44 standing). Do not waive DVD parity.
6. Assigned instance: OpenCode DeepSeek Flash. Design does not start workers / does not ask CHM for seats.
7. Tip ground `094b11f`; plan 48 P3 Design-accepted `88bd7852` is product oracle succession — orthogonal to this memory plan (Execute may land 48 before or after 56 measurement).

## Assumption ledger

### Assumption 1

- **Question:** May Design run live heavy RSS profiling without a CHM seat?
- **Answer chosen:** **No.** Design drafts the recipe and offline/doc inventory only. Live heavy mass/encode/K1/completeness measures are Execute-owned after CHM assigns.
- **Rationale:** Primary: “No seat ask — wait for CHM instance.”
- **If wrong:** Cody/CHM explicitly assigns Design a measurement seat — still flock + wrapper; still serial.

### Assumption 2

- **Question:** Are plan-05 fixture peaks and plan-48 tree peaks enough to skip a cross-phase ledger?
- **Answer chosen:** **No.** They are inventory inputs; Primary requires proven concurrent residency across the five phase labels.
- **Rationale:** Tree peak and fixture gates do not name co-resident structures.
- **If wrong:** Cody accepts a narrower encode-only or mass-only ledger — shrink Phase 2 scope in IMPLEMENTATION, keep the no-assumption rule.

### Assumption 3

- **Question:** Must representability mean a full-AU K1 completeness run?
- **Answer chosen:** Prefer the lightest CHM-allowed argv that still exercises `k1_representable` / representability filter on a **named** disc+spool pair; label full-AU separately if CHM permits later.
- **Rationale:** Hold posture + Primary “prove, don’t assume” — a labelled stand-in beats a silent full run.
- **If wrong:** CHM orders full-AU K1 under lock — still one serial heavy; still ledger required.

### Assumption 4

- **Question:** Implement optimisations in plan 56?
- **Answer chosen:** **No.** Optimisations are **57+**. This plan only measures and publishes.
- **Rationale:** Primary sequencing: profile → then designs that avoid keeping all data in memory.
- **If wrong:** none — still must not mix unmeasured cuts into acceptance.

### Assumption 5

- **Question:** Raise plan-20 PSS ceiling or relax `-j4` because of high encode tree RSS?
- **Answer chosen:** **No.**
- **Rationale:** Standing Maps rules; plan 20 contract; memory optim is residency shape, not cap raise.
- **If wrong:** separate Cody-signed design.

## Open questions

1. CHM seat timing / which phases are cleared for live full vs stand-in — Execute records what was allowed.
2. Whether `/proc/smaps` rollups are available inside the transient scope without extra privileges — Phase 1 recipe picks an evidence method that works on `codyh-ubuntu`.

## Phases

### Phase 1 — Phase catalog + measurement recipe committed

- **Outcome:** Plan folder `docs/plans/56-cross-phase-rss-profile/` names the five phases, tip entrypoints, wrapper recipe (`run_heavy_python.py` / `bench_build.py` / plan-05 controllers), serial flock rules, CHM-seat wait language, and the residency-ledger schema (columns: class, evidence method, bytes, live_at_peak). No live heavy job started by Design. No optim code. No oracle change. No plan 04 P4–6 / 3-90 / 170 / 3-16 / 3-17.
- **Surfaces:** plan-56 DESIGN (lands with Execute) + recipe note; optional tiny helper under `parser/tools/` **only if** needed to tag phases in logs (approach known: wrap existing tools). WORKFLOW may gain a one-line pointer to plan 56 ledger — without claiming peaks.
- **Approach:** known
- **Depends on:** tip with plan 05/25 tools (`094b11f` ground or later).
- **Refine:** skipped.

### Phase 2 — Serial measured ledger under CHM seat (Execute)

- **Outcome:** Under `flock output/.heavy.lock` + wrapper, Execute runs the CHM-allowed subset of phases (stand-in or full as seated). Each run records max RSS, `memory.peak`, available `memory.stat`, tree peak for encode, argv, wall. Concurrent residency ledger rows are **evidence-backed**. At least one inter-phase free-then-reenter sample when two phases share the host session. Scratch under `output/scratch-56/`. No production algorithm change. No mass R bump. No DVD waiver. No auto CHM hold-clear for completeness science.
- **Surfaces:** logs + ledger JSON/MD under plan-56 docs; wrapper JSON logs.
- **Approach:** known (recipe); which phases are full vs stand-in **open** until CHM seat text — refine only the allowed argv set.
- **Depends on:** Phase 1 + **CHM seat assignment** (Execute waits; Design does not ask).
- **Refine:** only argv scope labels.

### Phase 3 — Published summary table; handoff to 57–59

- **Outcome:** Committed summary: per phase peaks + dominant co-resident classes + explicit unknowns + pointers to optim drafts **57** (mass/control spool), **58** (encode level drop), **59** (dump finalize out-of-core). States that optim landings remain separate plans. No claim Phase 3 / 3-90 closed. No waivers.
- **Surfaces:** plan-56 report / IMPLEMENTATION summary; optional OVERVIEW one-liner under memory/ops if needed (prefer plan folder).
- **Approach:** known
- **Depends on:** Phase 2 ledger (partial ledger allowed if CHM seated only a subset — mark gaps).
- **Refine:** skipped.

## Provenance

- Primary / Maps Manager memory-focus 2026-10-07 via Grok Bot relay.
- Tip: `094b11f0b0b719e4e7c7270d48f758a088be8dee`.
- Cited: plan 05, plan 25 report/IMPLEMENTATION, WORKFLOW Heavy jobs, ARCHITECTURE window/oomd/finalize deferred, plan 44 Unit 4c mass OOM, plan 48 census `peak_rss_tree_mb`, tools listed above.
- Sibling drafts: `57-mass-control-spool-residency`, `58-encode-level-residency-drop`, `59-dump-finalize-out-of-core`; findings `memory-profile-2026-10-07/FINDINGS.md`.
- Plan 48 P3 Design ACCEPT `88bd7852` (orthogonal).
- Rejected: Design starting heavy seats; seat asks; mega-plan absorbing 57–59; assuming frees; raising PSS/`-j`; plan 04 P4–6; 3-90; waivers.
