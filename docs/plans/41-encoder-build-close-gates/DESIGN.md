---
design_id:
---

# Encoder/build close gates: full-AU encode wall regression and the full-suite-before-close rule

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual rows R-G9-4 (build wall time against the "well under 60 s" budget) and R-G8-5 (rule: full test suite before any close). Say whether R-G8-5 is a workflow-plugin rule or a repo rule. Oracle `4e6b0de7…` or later; build output bytes must not change. Heavy work only under flock plus the wrapper (encode ≤ `-j4`). Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

**R-G9-4.** Plan 35 P1 measured full-AU encode at 115.99 s at `-j4` (L0 encode 102.6 s, assemble 9.2 s; `phase3_synthesis/evidence/runs.json` `p1_encode_au`, `run_p1.log`). Plan 34 measured 118 s, and plan 14 P1 about 119 s on `4ed9cd80`.

Plan 04 DESIGN L48 (Contract H, Decision 7) says the full build stays ≪ 60 s (3C close: 12.16 s at `-j12`). The regression rule says a rise above run-to-run spread names its mechanism. No plan has named it.

**Ground that localises it:** plan 36 P1 replayed the pre-3-11 encoder (`b7c7c42`) on the same host at `-j4` in **26 s** (`docs/plans/36-…/IMPLEMENTATION.md`, 12:15:43–12:16:09 AEST). The 3-11 build (`9269ebb`) recorded encode 11.4 s + assemble 9.0 s = 20.7 s at `-j6`.

So the regression arrived after `9269ebb`. Encoder-source commits since then:
- `d35b565` (3-14 EO stitch, +304 lines `_cenc.c`);
- `68aa329`;
- `a890662` / `a1ee98d` (plan 14);
- `ecfae1c` (plan 29 guard);
- `5182c83` (plan 34 empty-shell rule).

**R-G8-5.** Plan 34 changed encoder emission (`5182c83`) and closed on 53 restricted tests. Its terminal review missed `test_parcel_mask` (fixed `a906818`, reviewed in plan 35 P2 F3). The follow-up: a plan touching the encoder or build runs the full `parser/tests` before close.

**Where the rule belongs.** The workflow plugin's execute skill (`workflow-plugin@6dd6b9d3…/skills/execute/SKILL.md`) requires a cheap-tier check of the phase outcome's own entry point. Its close-out skill has no test-suite rule. The plugin is project-agnostic and names no suite. The rule's trigger (encoder or build surfaces) and command (`parser/tests` under `.venv-rp`) are specific to this repo, and this repo already keeps its run rules in `docs/WORKFLOW.md` (heavy lock, wrapper, caps). **It is a repo rule.** A generic plugin counterpart ("run the project's declared full suite before closing a phase that touches production code") would be a separate Workflow System Manager item. It is listed for routing, not designed here.

## Solution shape

### Domain: encode wall attribution and fix

- **Owns:** `docs/plans/41-encoder-build-close-gates/wall/`, holding a bench table, per-level timings and the mechanism record. Optionally, a byte-identical performance fix in the C encoder.
- **Contract:**
  1. **Bench:** full-AU encode at `-j4`, three runs each (spread = max − min), under the wrapper on the same host and spool, each in a throwaway worktree at: `9269ebb`, `33006aa`, `d35b565`, `a890662`, `ecfae1c`, `5182c83`, HEAD. Each output sha must equal that commit's recorded oracle (`013586b5` / `013586b5` / `4ed9cd80` / `4ed9cd80` / `2ee3456a` / `4e6b0de7` / `4e6b0de7`). A mismatch is recorded, not re-pinned. Per-level wall comes from the build's level timings (or `--bench` where present).
  2. **Mechanism:** the commit where the median rises beyond the combined spread is named, and the hot function is located by a C-level profile of one bounded L0 window (perf or call counters) at that commit and its parent. The rise is decomposed by level and function.
  3. **Fix (preferred):** a performance change that keeps every output byte-identical: AU `4e6b0de7`, Perth `04be2f6e` at `-j1` and `-j4`, goldens unchanged, full suite green. Encode wall median of three at `-j4` is under the budget basis Cody confirms (see Cody question), and below 60 s in any case.
  4. **If no byte-identical fix reaches the budget:** the inherent cost is recorded by level and function with the measured floor. The row goes to Cody as a budget question, with that evidence. The design does not rebase it.
- **Non-goals:** changing encoder output; raising `-j` above the cap.

### Domain: close rule for encoder/build plans

- **Owns:** a `docs/WORKFLOW.md` section "Encoder/build close gates" and a small checker, `parser/tools/close_gates.py`.
- **Contract:**
  1. **Trigger:** the plan's diff from its design-land commit to HEAD touches `parser/kiwiw/*.c|*.h`, `parser/kiwiw/cenc.py`, `parser/build_alldata.py`, `parser/kiwiw/alldata_writer.py`, `parser/kiwiw/disc.py`, or goldens.
  2. **Required before the phase-closing commit:**
     - (a) full `parser/tests` summary line, quoted in IMPLEMENTATION with HEAD sha;
     - (b) full-AU encode wall median of three at `-j4` against the last recorded baseline. A rise above spread names its mechanism (Contract H regression rule, made operational);
     - (c) the AU/Perth sha gate result.
  3. `close_gates.py --base <sha>` reports whether the trigger fires and whether (a)–(c) appear in the plan's IMPLEMENTATION. Exit non-zero when they are missing. Light, no lock. Synthetic tests are included, and it has a `perf_inventory.json` entry.
  4. Applied to this plan's own Phase 1 close as the first use.
- **Non-goals:** editing the workflow plugin; CI wiring (plan 06 is out of scope).

## Decisions

1. Plan number 41. Master direct. Two phases.
2. Combined, because both rows are the same gap: encoder/build plans closing without the build-side gates.
3. R-G8-5 is classified a **repo rule**. A generic plugin variant is routed to Workflow System Manager by the parent, not drafted here.
4. Byte-identical output is a hard constraint. No re-oracle.

## Assumption ledger

### Assumption 1

- **Question:** Is `-j4` the right basis for the build wall?
- **Answer chosen:** Measure at `-j4` (the encode cap, plan 25 / WORKFLOW). The 12.16 s reference was at `-j12`, now above the cap. The `-j4` pre-regression figure (26 s, `b7c7c42`) shows the budget was met at the cap before the regression.
- **Rationale:** Measured on the same host.
- **If wrong:** Cody names another basis, and the target number in Phase 1 item 3 changes. The mechanism work is unchanged.

### Assumption 2

- **Question:** Is three runs per commit enough given host load?
- **Answer chosen:** Yes, with the spread reported. If spreads overlap at the suspect commit, three more runs are added there only.
- **Rationale:** Contract H's regression rule is spread-based.
- **If wrong:** the bench grows; scope does not.

## Open questions

1. The budget basis (Cody question 1 in NEXT-CANDIDATES). It does not block Phase 1 measurement.

## Phases

### Phase 1: Wall regression attributed; byte-identical fix or measured floor

- **Outcome:**
  1. Bench table for 7 commits: medians, spreads, shas.
  2. Regressing commit and hot function named, with a per-level decomposition.
  3. Either a byte-identical fix with `-j4` median < 60 s (AU, Perth, goldens, full suite green), or the measured floor plus a Cody budget question.
  4. R-G9-4 updated.
- **Surfaces:** `docs/plans/41-encoder-build-close-gates/wall/`; `parser/kiwiw/_cenc.c` / `_e2.c` (performance only); `parser/tests/` (timing-independent tests only); `residuals.tsv`; `docs/provenance.md`.
- **Approach:** open (the fix depends on the mechanism). **Depends on:** none. **Refine:** skipped.

### Phase 2: Close-gate rule and checker landed

- **Outcome:**
  1. `docs/WORKFLOW.md` section.
  2. `close_gates.py` plus tests, with an inventory entry.
  3. The checker run on plans 34, 37 and 41 as worked examples: 34 → missing (a) at its close, 41 → pass.
  4. R-G8-5 discharged as a repo rule, with the plugin-variant routing note.
- **Surfaces:** `docs/WORKFLOW.md`; `parser/tools/close_gates.py`; `parser/tests/test_close_gates.py`; `parser/perf_inventory.json`; `residuals.tsv`.
- **Approach:** known. **Depends on:** none (Phase 1 supplies the wall baseline for (b)). **Refine:** skipped.

## Provenance

- Master `b10e787`. Sources:
  - plan 35 `residuals.tsv` R-G9-4, R-G8-5 and evidence `runs.json` / `run_p1.log`;
  - plan 36 IMPLEMENTATION P1 (26 s replay);
  - plan 04 DESIGN L44–48, IMPLEMENTATION L207 (3-11 timing);
  - plan 25 caps;
  - workflow plugin execute and close-out skills (read on box);
  - git log of encoder sources.
- Rejected:
  - rebasing the budget without a mechanism;
  - a plugin edit from a repo design.
- Box draft only.
