# Brief: 2-12 — Phase 2 grounded gate verdict and schema rows (criteria 1–5)

Consumer: the orchestrator, who records the phase outcome and applies the Assumption Ledger change; and any later reader of `docs/schema/` who needs to know what the coordinate model rests on.
Owned paths: `docs/schema/map-frame.md`, `docs/schema/UNKNOWNS.md` (rows for the coordinate model only), `docs/plans/03-map-layer-parity-remediation/GATE-2.md` (new), `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-12.json` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-09, 2-10, 2-11.
Runs alongside: nothing.
Budget: 12 files to read, about 200 lines to change, 45 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` and no unit of this phase writes to it.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-23 (user) — grounded phase gates" in full: what makes a criterion grounded, the "Evidence status" paragraph, "#### Phase 2 — Outcome, as amended" criteria 1–5 with its "Carried into the re-run" paragraph, "#### Schema rows this amendment supersedes" (line 252 on the Assumption Ledger), and "#### Recommendation on closing Phase 2". Also the Assumption Ledger entry "Coordinate range 4096/16384 is the true full-cell range" and the Phase 2 section's Outcome and Surfaces.
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — **read only, never write** — the Phase 2 history: the two failed closes, the "Phase 2 gate verdict (restart): NOT CLOSED" section and its Carried list, and the records for 2-05, 2-06, 2-07, 2-08 and 2-04.
3. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-09.json`, `EVIDENCE-2-10.json`, `EVIDENCE-2-11.json` — the three new evidence files, plus 2-09/2-10/2-11's handbacks.
4. `docs/schema/README.md` — the row format and the status vocabulary (verified / observed / spec-only / assumed / unknown); `parser/tools/lint_schema.py` for usage.
5. `docs/schema/map-frame.md` and `docs/schema/UNKNOWNS.md` — the coordinate and header rows as 2-04 left them, including whatever row 2-04 added saying the gate had not closed.
6. `parser/refdata/profile/coord_scale.json` — `ranges` (`max`, `exceeds_max`, `exceptions`, `share_at_max`), `class_rule`, `header`.
7. `parser/tools/coord_scale_census.py` and `parser/tools/header_word_census.py` — their CLIs and the keys they emit (read only; you do not modify either).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Run all five grounded criteria for real in one repo state, write the schema rows the model has actually earned, and state the Phase 2 verdict criterion by criterion with numbers — closed, or not closed and bounced.

## Contract

Cited, DESIGN Decisions, Amendment 2026-09-23, "Evidence status": "A phase closes only when the check asserting its invariant is committed under `parser/` and re-run."

Cited, the same amendment, Phase 2 criterion 1: "No parcel coordinate exceeds its class range, and the per-class maximum equals the range. Denominator the full-disc census in `coord_scale.json` over all content-bearing parcels; zero exceedances in every class."

Cited, the same amendment, Phase 2 criterion 5: the header-word rules hold at their stated rates with every exception explained (read the criterion's own wording from DESIGN and quote it in `GATE-2.md`; do not paraphrase it here or there).

Cited, the same amendment, line 252: "The Assumption Ledger entry 'Coordinate range 4096/16384 is the true full-cell range' is deliberately left untouched, because Phase 2 is not closed here. Whoever closes Phase 2 must update that entry in the same change; closing it without doing so would be a scope violation."

Cited, `docs/schema/README.md`'s status vocabulary: a row's status must match its evidence. Measured on R and consistent on held-out data is `observed`; `verified` only where the spec independently states it. **Do not raise a status above the evidence**, and do not mark a row `verified` on the strength of an R-internal census alone.

Settled and not to be re-derived: criteria 1 and 5 are already carried by committed tested tools (`coord_scale_census.py`, `header_word_census.py`) whose outputs are in `coord_scale.json`; your job on those two is to **re-run and confirm currency**, not to re-derive or re-brief them. Criteria 2, 3 and 4 are carried by 2-10 and 2-11.

Two things known in advance about the re-run, so you neither chase them nor let them pass unremarked:

- The committed `coord_scale.json` key `header.pointer_nonframe_targets.examples` does not regenerate identically (recorded by 2-08 as a carried concern). A whole-file sha comparison will therefore differ for a reason that has nothing to do with this gate. Compare `ranges`, `class_rule` and `header.words` structurally instead, and report the `examples` drift as the pre-existing carried item it is.
- In `ranges`, `exceeds_max` is criterion 1's quantity. `exceptions` is a different count (a class's observed peak not sitting at the bucket max) and is **not** an exceedance. Cite `exceeds_max` and say which you are citing.

Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`. Python: `.venv-rp/bin/python`. You run existing tools and write documents; you change no tool and no refdata file. Output is deterministic (sorted keys, no timestamps). Never edit worktree copies under `.claude/worktrees/`.

## Changes

**1. Re-run every criterion in this repo state** and record each command and its result in `EVIDENCE-2-12.json`:

- `coord_scale_census.py` against R, output to a scratch path (**not** over `parser/refdata/profile/coord_scale.json`), compared key by key against the committed profile's `ranges` and `class_rule`. Report `exceeds_max` per class and the per-class `max` against its range.
- `header_word_census.py` against R, its word rules and rates compared against the committed `header` block.
- `continuity_census.py` and `boundary_mirror_census.py`, each to a scratch path, compared against the committed `EVIDENCE-2-10.json` / `EVIDENCE-2-11.json`. A difference in a headline number is a determinism finding: report it, do not average it away.
- If a re-run's structural comparison differs from what is committed, that is a gate finding. Record it and let it drive the verdict; **do not edit the committed profile or the evidence files to match** — they are not your owned paths.

**2. Schema rows** in `docs/schema/map-frame.md` (and `UNKNOWNS.md` where a row retires or remains unknown):

- The per-class coordinate range and the class rule, with the criterion 1 denominator and `exceeds_max`.
- The coordinate frame: leaf bbox, the L0 sparse 4x4 tile frame, the divided parent frame (2-05), and y increasing northward (2-06).
- Cross-parcel continuity, citing criterion 2's numbers from `EVIDENCE-2-10.json` and naming the alternatives it discriminates against.
- Divided-parcel quadrant containment, with the spec citation that names the 2x2 sub-parcel model and criterion 3's per-point numbers.
- The boundary-node mirror, with criterion 4's denominator, matched count and the exclusion counts — and, in the row's own words, what the `scale_mismatch` exclusions mean for the claim's reach.
- Update or retire whatever row 2-04 wrote that says the Phase 2 gate had not closed, and record the amendment's dispositions for the retired measures (the occupied-fraction clause, `axis_coverage` at 0.75 for divided, `clip_exact_share`) so a reader does not go looking for them.
- `parser/tools/lint_schema.py` passes.

**3. `GATE-2.md`** — the gate record, in this shape: each criterion 1 through 5 as its own heading, with the criterion quoted verbatim from DESIGN, the command that produced its number, the number, the denominator, and `PASS` / `PASS WITH RESIDUAL` / `FAIL`; then the overall verdict, `CLOSED` or `NOT CLOSED`; then a Carried list. **If any criterion fails, the verdict is NOT CLOSED and the record says so in those words.** Do not soften a failure, do not average criteria, and do not close on four of five. Carry forward, restated with their current status, the items the restart's verdict left open: `rg_size` (item 4, OPEN, a DESIGN gap, not a code bug), pointer non-frame targets (Phase 9's), the stale `LENGTH_BASIS` wording in `road_density_census.py`, and the non-regenerating `header.pointer_nonframe_targets.examples`. Add any new item this run produces, including this one if you confirm it: `coord_scale_census._work` constructs its `WalkedParcel` without `frame_bounds`, so `frame_bounds` defaults to the leaf bbox and the 075fc99 fixer ("invert against the frame bbox, not the leaf") never takes effect inside that tool's own worker path — harmless for `ranges`, because decode and inversion use the same bbox and raw values round-trip exactly, but it means that tool is not frame-aware and its test passes only on a synthetic parcel. Verify this yourself before recording it; do not fix it here.

**4. The Assumption Ledger.** You do **not** edit `DESIGN.md`. Instead, if and only if the verdict is `CLOSED`, put in `GATE-2.md` under a heading "Assumption Ledger replacement, for the orchestrator to apply" the exact replacement text for the entry "**Coordinate range 4096/16384 is the true full-cell range.** Tested in Phase 2. If false: hard stop, re-analyse (user decision)." — one bullet, ready to paste, naming what tested it, the criteria and numbers that settled it, and what remains untested about it. Say in your report back that the orchestrator must apply it in the same change that closes Phase 2, citing line 252. If the verdict is `NOT CLOSED`, write no replacement text and say the entry stays as it is.

### Keep untouched

`parser/**` entirely — every tool, test and refdata file, including `parser/refdata/profile/coord_scale.json`. `docs/plans/03-map-layer-parity-remediation/DESIGN.md`, `IMPLEMENTATION.md`, and the briefs. `EVIDENCE-2-03.json`, `EVIDENCE-2-08.json`, `EVIDENCE-2-09.json`, `EVIDENCE-2-10.json`, `EVIDENCE-2-11.json`. Other files in `docs/schema/` beyond the two named, including the rows this amendment assigns to Phases 4, 6, 7, 8 and 9.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `.venv-rp/bin/python parser/tools/lint_schema.py` passes (report output before and after).
- `.venv-rp/bin/python -m pytest parser/tests -q` passes (report the counts; you changed no code, so this is a regression guard).
- Every re-run command in change 1 recorded in `EVIDENCE-2-12.json` with its result and, where it produced a file, its `sha256` beside the committed file's.
- `GATE-2.md` states five criterion verdicts with numbers and denominators, and one overall verdict.
- In your handback, the five criterion verdicts with their numbers, the overall verdict, and the Carried list.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Lead with the overall gate verdict in the first line. Then the five criterion lines with numbers, what changed in `docs/schema/`, whether the Assumption Ledger replacement text exists and where it is, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. **A `done` status does not mean the gate closed; say which it is.**

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
