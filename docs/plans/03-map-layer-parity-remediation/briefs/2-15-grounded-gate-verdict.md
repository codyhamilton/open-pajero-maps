# Brief: 2-15 — Phase 2 grounded gate verdict (criteria 1–5) and the Assumption Ledger

Consumer: the orchestrator, who records the phase outcome; and any later reader of `docs/schema/` who needs to know what the coordinate model rests on.
Owned paths: `docs/plans/03-map-layer-parity-remediation/GATE-2.md` (rewritten in place, superseding 2-12's record), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-15.json` (new), `docs/schema/map-frame.md` and `docs/schema/UNKNOWNS.md` (rows for the coordinate model only), and — **only if the verdict is CLOSED** — the Assumption Ledger entry in `docs/plans/03-map-layer-parity-remediation/DESIGN.md` named below. Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-13, 2-14.
Runs alongside: nothing.
Budget: 12 files to read, about 250 lines to change, 45 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (user) — grounded phase gates": the grounded/necessarily-statistical definitions, the **Evidence status** paragraph, "#### Phase 2 — Outcome, as amended" criteria 1–5, and "#### Schema rows this amendment supersedes" including the sentence "Whoever closes Phase 2 must update that entry in the same change; closing it without doing so would be a scope violation." Then Decisions, "Amendment 2026-09-23 (design agent) — the adjacency unit is the frame, not the leaf slot", in full — it restates criteria 2 and 4 and governs where the two conflict. Then the Assumption Ledger entry "Coordinate range 4096/16384 is the true full-cell range."
2. `docs/plans/03-map-layer-parity-remediation/GATE-2.md` — 2-12's record, which you supersede. Its Carried list is the base for yours.
3. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-12.json` — the previous re-run's commands, shas and determinism findings; reuse its command lines for criteria 1 and 5.
4. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-14.json` and 2-14's handback — criteria 2, 3, 4.
5. 2-13's handback — the frame-adjacency API and the `coord_scale_census` `frame_bounds` fix, with its statement that criterion 1's `ranges` / `exceeds_max` did not move.
6. `parser/tools/coord_scale_census.py`, `parser/tools/header_word_census.py` — invocation only; do not modify either.
7. `docs/schema/map-frame.md` — the coordinate-frame rows.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Re-run all five grounded Phase 2 criteria for real in this repo state and write the verdict, honestly, either way.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23 (user), on what a grounded criterion is: a spec citation by chapter and section; or a per-record invariant whose violations are counted against a stated denominator, "passing at zero violations or at an enumerated residual explained record by record"; or a byte-exact, round-trip or closed-form identity.

Cited, the same amendment's Evidence status paragraph: "A phase closes only when the check asserting its invariant is committed under `parser/` and re-run."

Binding, and not negotiable: **if any criterion fails, the verdict is NOT CLOSED.** Do not soften a failure, do not average criteria, do not close on four of five, and do not override a tool's own `fail` with a narrative. Where you must depart from a tool's self-reported label — as 2-12 legitimately did for `L0_sparse` — quote the criterion's wording and say which reading you applied and why.

Run every criterion. Criteria 1 and 5 use the committed `coord_scale_census.py` and `header_word_census.py` with the command lines in `EVIDENCE-2-12.json`; criteria 2, 3 and 4 use the tools 2-14 committed. For each criterion record: the exact command, the number, the denominator, the sha256 of the output, whether it matches the committed evidence, and PASS / PASS WITH RESIDUAL / FAIL. A determinism check is part of the evidence: re-run and compare shas, as 2-12 did.

Criterion 1 has a new obligation from 2-13's `frame_bounds` fix: confirm `ranges` and `class_rule` are still structurally identical to `parser/refdata/profile/coord_scale.json` and `exceeds_max` is still 0 in all 28 classes. If they moved, that is a criterion-1 problem and the verdict reflects it.

Criteria 2 and 4 are judged against the **design-agent amendment's** restated wording, not the earlier wording: frame adjacency, exact global-lattice equality, corner nodes satisfied by any sharing frame per 7.2.2.1.1.3, `scale_mismatch` inside the denominator, and every residual record enumerated. State the residual count against `RESIDUAL_ENUM_CAP` explicitly, and state whether each residual record is individually explained — the criterion is not met by a plausible story about a residual. Call out the cross-class `L0_urban <-> L0_sparse` figure by name: it is the two-sided evidence for 16384 = 4 x 4096 that no earlier run produced.

Also record, because the design-agent amendment made them load-bearing and they are the reason the previous run's labels needed overriding: that `boundary_mirror_census`'s verdict logic now keys on residual coverage rather than on whether twenty examples could be printed, and that the `coord_scale_census` `frame_bounds` gap (2-12 Carried 5) is fixed. Carry forward every still-open 2-12 Carried item with its current status; close the ones 2-13 and 2-14 closed, naming the unit that closed each.

**The Assumption Ledger.** DESIGN.md line ~252: "Whoever closes Phase 2 must update that entry in the same change; closing it without doing so would be a scope violation."

- **Verdict CLOSED**: update the entry "**Coordinate range 4096/16384 is the true full-cell range.** Tested in Phase 2. If false: hard stop, re-analyse (user decision)" in the same commit, to state that Phase 2 tested it and what it now rests on — naming the global raw lattice at 4096 units per top-level leaf slot, the frame as n x n slots at range n x 4096, and the cross-class `L0_urban <-> L0_sparse` measurement as the two-sided evidence. This is the only edit to DESIGN.md this unit may make: the one ledger entry, nothing else, and no new amendment section.
- **Verdict NOT CLOSED**: leave the ledger entry exactly as it is and say in `GATE-2.md` that you left it, with the reason, as 2-12 did. Do not write replacement text "ready for later".

Do not relitigate the design. If the evidence contradicts the design-agent amendment — for instance if frame adjacency does not in fact bring `L0_sparse` to zero violations, or if the residual exceeds what can be explained — that is a `needs context` report with the numbers, not a redesign inside this unit, and the verdict is NOT CLOSED.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. R only; **no OSM input at all**. Python: `.venv-rp/bin/python`. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

`GATE-2.md` rewritten: one section per criterion with the quoted criterion wording, command, number, denominator, sha comparison and verdict; then the overall verdict; then Carried; then the Assumption Ledger disposition. `EVIDENCE-2-15.json` as the machine record. The coordinate-model rows in `docs/schema/map-frame.md` and `docs/schema/UNKNOWNS.md` brought up to date with the lattice rule and the frame-vs-leaf distinction, with their verification status set from what actually ran.

### Keep untouched

`parser/**` entirely — this unit runs tools, it does not change them. If a tool is wrong, report `needs context`. `EVIDENCE-2-10.json`, `EVIDENCE-2-11.json`, `EVIDENCE-2-12.json`, `EVIDENCE-2-14.json`, every brief, `IMPLEMENTATION.md`, and all of `DESIGN.md` except the single Assumption Ledger entry and only on a CLOSED verdict.

## Done evidence

- All five criteria run, with commands and shas recorded, each re-run once for determinism.
- `.venv-rp/bin/python -m pytest parser/tests -q` passes before and after (no code changes here; regression guard only — report the counts).
- `.venv-rp/bin/python parser/tools/lint_schema.py` — report before and after.
- `GATE-2.md` states one overall verdict in plain words, with the per-criterion verdicts above it.
- In the handback: the five verdicts, the overall verdict, the residual count against the cap, the Assumption Ledger disposition, and the Carried list's deltas.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`, plus the gate verdict stated separately and explicitly (`CLOSED` or `NOT CLOSED`) — the orchestrator reads that line directly. Then the per-criterion figures, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the verdict is NOT CLOSED, say which criterion failed and on what number; do not propose a redesign.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
