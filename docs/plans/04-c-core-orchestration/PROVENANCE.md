# Provenance: C core, Python orchestration

## Session

- Session: Initial design (October 1, 2026)
- Timestamp: 2026-10-01
- CWD: /home/codyh/workspace/open-pajero-maps

## Initial Request (verbatim)

> /workflow:design
>
> Posture: interactive. Hold the Cody checkpoint when DESIGN.md is ready — do NOT start refine, execute, or build.
>
> Repo: /home/codyh/workspace/open-pajero-maps @ 0cf5d99 (master). Create folder docs/plans/04-c-core-orchestration/ (slug may be refined if skill wants a better key; keep NN=04) with DESIGN.md + PROVENANCE.md.
>
> Standing model: Sonnet only for this orchestrator and workers. Do not switch to Opus.
>
> Intent: C for all perf-sensitive work; Python orchestration only. Close 3C as debt into plan 04/3D. Grow libkiwiw from existing C; C decoder+checker first; delete Python decoders once C matches goldens/R; checker-first keep SHA; freeze old Phase 4–10 briefs.
>
> Locked Cody decisions (ledger, do not re-ask): Approach B (C for encode, decode, check, geometry/adjacency; Python orchestration only). Close Phase 3C / plan 03 as debt into 04/3D (done at 0cf5d99). Delete Python decoders once C decoder+checker match goldens/R. Checker-first triage; keep current SHA oracle until intentional re-oracle. Freeze plan 03 Phase 4–10 briefs until rewritten under C-first rule. Grow libkiwiw from existing _cenc/_e1/_e2 in monorepo; defer greenfield. Hard gates: full AU sha 87a01b14…, Perth da13a775…, goldens, Contract H build ≪60s; C checker ≤120s target. Agents: Flash draft OK with mandatory Sonnet 5.5 review; Claude/Grok phase sign-off.
>
> Phases proposed: 1 policy/contracts lock; 2 C decoder + C checker skeleton (≤120s wall even if fails high); 3 triage 3C-04 debt → 0 background fails + exactly 1 name-anchor; 4 move harness/coord_scale hot checks to C; 5 thin Python driver over libkiwiw; 6 resume map-layer content under C-first. Optional later: extraction boundary (deferred).
>
> Rules: ask only if scope-shaping is still unknown; prefer Assumption Ledger/Decisions; contracts precise, no briefs in DESIGN; one adversarial pass before the checkpoint; stop at the checkpoint, commit DESIGN+PROVENANCE locally, report SHA; do not push; do not start refine/execute.

## Design Conversation

### Turn 1

**User responded:** Direction volunteered in full in the request: the intent, nine locked decisions, the six-phase shape, and the rule to ledger rather than ask. No question was put to the user before drafting.

**Agent decisions:**

- Ledger the locked decisions under Decisions without re-asking.
- Settle five points as Assumptions (zero-failures vs keep-SHA, harness budget numbers, fate of replicate writers and scripts, extraction-caused failures, where plan 03's unstarted units go).
- Treat Phase 6 as a successor *design*, not briefs: no briefs exist for plan 03 Phases 4–10 (recon), and refine needs surfaces that exist only after Phase 5.
- Treat extraction as a non-goal in Domain text, not a speculative folder or doc.

## Agent Decisions

- **Oracle wording for Phase 3**: "0 failures on the oracle disc in force at close", not "on 87a01b14…". Rationale: the confirmed disc defect cannot reach zero without either a build fix (sha moves) or a loosened checker.
- **Decoder equivalence**: Python decoders are the oracle for D1 until Phase 5, an explicit amendment to plan 03's Contract T. Rationale: delete-after-match needs a comparison.
- **Lettered trailer**: the 3C close commit's `Workflow-Phase: …:3C` may not match a numeric phase driver; noted in Architectural Implications, not fixed.
- **Untracked file**: `.scratch-design-04-prompt.txt` in the repo root is the user's prompt scratch; left untracked and not committed.

## Adversarial pass

A clean-context reviewer (Sonnet) attacked the first draft. Applied: Phase 3 outcome restated around causes (build/checker-caused 0, spool-caused pinned) with name_anchor labelled a carried extractor defect; K1 given an oracle in Phase 2 (reproduce the 3C-04 table exactly); Phase 5 Surfaces extended to `alldata_writer.py` and `disc.py` (build-module imports of the decoders); Phase 4 baselines captured first and made to depend on Phase 3; census kernels given a contract and a call-counter test; invented numbers marked provisional and signed at the Phase 2 close; Contract B's "nothing else crosses" sentence listed as superseded for verification only; K1 determinism defined with a fixed sample order. Not applied: merging Phase 2's decoder and checker (kept as one phase with D1 gating K1).
