# Brief: 2-04 — Schema rows for the model and the gate verdict (rewritten for the restart)

Consumer: implementation worker, then the phase orchestrator (gate verdict); rows consumed by Phases 3, 4, 9 and 10.
Owned paths: `docs/schema/map-frame.md`, `docs/schema/UNKNOWNS.md` (rows for the model only), `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` (append the Phase 2 restart gate record). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-05, 2-06, 2-07, 2-08 (all finished and committed).
Runs alongside: nothing.
Budget: 8 files to read, about 150 lines to change, 35 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

> This brief replaces the pre-restart 2-04. The gate criteria below are the **redefined** ones from the user amendment; the absolute overlay thresholds the earlier version cited (`MATCH_MIN 0.8` and siblings) are superseded and must not be used as pass/fail.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Decisions, "Amendment 2026-09-22 (user) — Phase 2 restart" (all four items); Decisions, "Coordinate-range gate (user)"; "Domain: Native encoding model" (the header-word exemption list); Phase 2 Outcome (read subject to the amendment).
2. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 2-01 and 2-02 records, the "Phase 2 gate verdict: NOT CLOSED" section and its Carried list, and the restart records left by 2-05, 2-06, 2-07 and 2-08.
3. `docs/schema/README.md` — row format and status vocabulary (verified / observed / spec-only / assumed / unknown); `parser/tools/lint_schema.py` (usage).
4. `docs/schema/map-frame.md` and `docs/schema/UNKNOWNS.md` — the existing header and coordinate rows, including the pmcode row at line ~35.
5. `parser/refdata/profile/coord_scale.json` — `ranges`, `class_rule`, `header.words` (0, 6, 7, 9, 10, 11), `header.word0_exceptions`, `header.wp2_exempt`, `header.pointer_nonframe_targets`.
6. `docs/plans/03-map-layer-parity-remediation/EVIDENCE-2-08.json` (the re-run) and `EVIDENCE-2-03.json` (the first run, for the comparison). Grep; these are large.
7. `docs/plans/03-map-layer-parity-remediation/WORD7-ANALYSIS.md` — Result table and the "Adoption" section 2-07 appended.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Record the coordinate model and the header-word rules as schema rows carrying their evidence, and state the Phase 2 gate verdict against the redefined criteria, criterion by criterion, with numbers.

## Contract

Cited, DESIGN Phase 2 Surfaces: "`docs/schema/` rows for the model".

Cited, DESIGN Decisions: "**Coordinate-range gate (user):** hard stop. If the offline test does not confirm R's range model, the design is bounced for re-analysis; nothing downstream proceeds on the current constant."

Cited, Amendment item 1 — the gate is: "(a) **Relative discrimination.** For each parcel class, the assumed range beats every alternative range considered — including the 32768 negative control — by a clear, *pre-stated* relative margin. (b) **R-only measures pass.** Coordinate maximum vs the class range; clipped links terminating at the cell edge; occupied fraction of the cell extent (no clustering into a sub-region)." And: "Match rate against OSM is reported as a **diagnostic** with a recorded source-disagreement baseline. It is not pass/fail."

Cited, Amendment item 3: word 7 is Area Number 18 iff road data exists at L0 (for L2, iff any L0 descendant has a road sub-frame), else 255; L4 and above always 255; word 8 = 0 and word 7's low byte = 0; "The 28 single-link L0 misses are a recorded residual **tolerance**, not an exemption"; "the generator's need for an L2 post-pass (L2 headers read their L0 children) is recorded as Phase 4 scope"; "The meaning of area 18 in the metafile stays documented-unknown."

Cited, Amendment item 4: "**Unit 2-04 runs** (schema rows and gate verdict). If the redefined gate genuinely fails, the phase does not close and the run reports `unsuccessful` with the evidence."

Cited, `docs/schema/README.md`'s status vocabulary: a row's status must match its evidence. Measured on R and consistent on held-out data is `observed`; `verified` only where the spec independently states it. Do not raise a status above the evidence.

Header-word rules that hold at `1.0` or `0.99998` on held-out data (words 0, 6, 9, 10, 11) are 2-02's settled result and are not re-tested here.

Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`.

## Changes

- **Schema rows.** Add or update rows in `docs/schema/map-frame.md`:
  - per-(level, class, division) coordinate maximum, the content-independent class rule, and the *frame* each class's coordinates are expressed in — including that the L0 sparse frame is the 4x4 integrated-parcel tile at 16384 and that divided sub-parcel coordinates are absolute in the parent leaf's frame at 4096 (2-05's and 2-03's findings).
  - the y orientation: parcel-local y increases northward (2-06; evidence 2-03's pooled 12 cells x 7 classes).
  - header word 0 (header size, `word0*2 = 36 + 4*nregion + 6*n_mfde_entries`), correcting the plan-01 "matches buffer size" claim in the row itself; words 6, 9, 10, 11; and the WP2-exempt words with R's census values.
  - **the pmcode row (line ~35)**: rewrite it to the adopted rule — word 7 = Area Number, 18 iff road data exists at L0 or below, else 255; word 8 = 0; word 7 low byte = 0 — with the accuracy and the 28-parcel residual tolerance. The current row's "Conflict / Winner: the census" text is superseded; replace it, do not append to it.
  - every row cites `coord_scale.json` and, where relevant, `EVIDENCE-2-08.json`.
- **`UNKNOWNS.md`**: the meaning of Area Number 18 in the metafile stays `unknown` with its first test (the metafile is not on the disc and not in the archived spec). Add or keep exactly that row; do not invent others.
- **Word 16 `rg_size` (Phase 2 Carried item 4).** 2-02 found it nonzero on real L0 rg parcels while the DESIGN header-word exemption list ("`n_intersections`, `route_planning_level`, `n_additional_data`, ext-frame slots and `nregion` ... are the only words allowed to differ from the model in Phase 4") does not list it. Add a schema row recording R's observation at the status its evidence supports, and record in the gate record that the DESIGN exemption list has a gap here that **the orchestrator must resolve before Phase 4** — either word 16 joins the exemption list or Phase 4 must model it. You are not amending `DESIGN.md`; you are naming the gap.
- **Pointer non-frame targets (Carried item 5)** are **Phase 9's**, not Phase 2's: `header.pointer_nonframe_targets` in `coord_scale.json` is 2-02's classification (19,771 of 31,564,067; L8 5.4%, L6 0.72%), and Phase 9 owns the `pointers` allowance. Say that in the gate record's carried list and add no schema row obligation for it here.
- **The gate record.** Append a "Phase 2 gate verdict (restart)" section to `IMPLEMENTATION.md` stating, per redefined criterion, pass or fail **with the numbers**:
  - (a) relative discrimination, per parcel class: the assumed range's ratio against the best alternative, on both matched fraction and median distance, against the margins 2-08 stated in its docstring.
  - (b) R-only measures, per parcel class: coordinate maximum vs range, clipped-link exact share (and any class reporting `insufficient_data`), axis coverage.
  - the OSM match rate and the source-disagreement baseline, **labelled as diagnostics**, with a sentence saying they are not pass/fail.
  - header words: 0, 6, 9, 10, 11 from 2-02; word 7 from 2-07, with the residual tolerance stated as a count, not as an exemption; the 42 word-0 exceptions and their proven cause.
  - all four named cells, with their verdicts and link counts, including any reported `low_n`.
  - the carried list, updated: which of the previous Carried items 1–6 this restart closed and which remain, with each remaining one's owning phase.
  - Phase 4 scope recorded here: the L2 post-pass for word 7, and the `rg_size` exemption-list gap.
  - Phase 3 scope recorded here: 2-06's measured encoder impact (the y flip changes generated y values).
- **Do not soften a failure.** If any class fails (a) or (b), the record says the gate is **not closed**, the run is `unsuccessful`, and the design is bounced for re-analysis — with the numbers that say so. Equally, do not fail the phase on a diagnostic: an OSM match rate below the first run's absolute thresholds is not, by itself, a gate failure under the amendment.

### Keep untouched

Code of any kind. `parser/refdata/**` (including `coord_scale.json` and `harness.json`). `DESIGN.md` — the orchestrator owns it; gaps are named in your report and in the gate record, never edited in. `EVIDENCE-2-03.json` and `EVIDENCE-2-08.json`. The earlier records in `IMPLEMENTATION.md`: append, never rewrite history.

## Done evidence

- `.venv-rp/bin/python parser/tools/lint_schema.py` exits 0. Report the row/error counts before and after.
- Every number in a new or changed row appears in `coord_scale.json`, `EVIDENCE-2-08.json` or `WORD7-ANALYSIS.md`. Spot-check five by grep and name which five and where each was found.
- Every criterion in the gate record has a number next to it, and every number is traceable to a named file. No criterion reads "pass" without one.
- The gate record's verdict sentence states the phase outcome in one of exactly two forms: closed, or not closed and bounced.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. Lead with the gate verdict and the per-criterion numbers; the orchestrator acts on that line.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
