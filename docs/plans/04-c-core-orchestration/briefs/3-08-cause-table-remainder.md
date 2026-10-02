# Brief: 3-08 — Cause table for `interior_cover`, `completeness`, `name_anchor` and the disc defect; consolidated table

Consumer: the orchestrator (fix-unit authoring and the pinned list); 3-90.
Owned paths: new `docs/plans/04-c-core-orchestration/triage/rules_other.json`, new `docs/plans/04-c-core-orchestration/triage/cause_table.md`, new `docs/plans/04-c-core-orchestration/triage/pinned_candidates.tsv`, `output/scratch-3-08/`. No other repo file. Do not edit code, do not fix anything.
Commits: Commit the three `triage/` files to `master` and push when done evidence passes.
Depends on: 3-07.
Runs alongside: nothing.
Tier: Flash is not recommended. RE-risky (HIGH, shares 3-07's causes). Mandatory Sonnet 5.5 review.
Budget: 8 files to read, scripts of about 150 lines, 70 tool turns. Past the budget, stop; handoff in `IMPLEMENTATION.md`; report `over budget`.

## Required reading, in order

1. `DESIGN.md` Phase 3 Outcome and Assumption 1; `docs/plans/04-c-core-orchestration/triage/causes_bg.md` and `rules_bg.json` (3-07).
2. `output/scratch-3-06/dossier.md` — D5, D6, D7 and D1.
3. `2-05-k1-completeness.md` (the completeness rules a, b, c), `2-04-k1-background-kinds.md` (interior cover rule), `parser/kiwiw/_k1_cmp.c`.
4. `output/scratch-3-05/summary/groups_interior_cover.tsv`, `groups_completeness.tsv`, `groups_name_anchor.tsv` (re-run summary if missing).

## Goal

All 824 interior_cover, 752 completeness and 1 name_anchor rows get a cause, one by one (these counts are small enough to enumerate every item), the disc defect near polygon 65623 is classified, and one consolidated table covers all five kinds.

## Contract

Cited from `DESIGN.md` Phase 3 Outcome: "`name_anchor`'s one failure (L0 cell (0,541), leaf 928) is such a carried spool item (the 3C record calls it an extractor defect), not an acceptance target" and "The disc defect near spool polygon 65623 is classified in the cause table; if build-caused it is fixed in the C build." Cause classes and their witnesses are exactly those of `3-07-cause-table-background.md` (checker / spool / build; unexplained rows stay unclassified and the unit reports `blocked`).

## Changes

1. Each of the 1,577 items is classified. For interior_cover and completeness reuse the mechanisms of 3-07 where the dossier (D5, D6) shows the same source shape or the same ring defect; otherwise name the mechanism. A completeness failure means "a spool polygon of this type meets the cell but no decoded piece of it": test whether the checker's rule (a, b, c) over-demands (checker), whether the polygon only grazes the cell by the build's clip rule (checker or build), or whether the polygon is the defective ring (spool). Witness: the 3-07 witness script extended with the completeness question, 200 groups or all if fewer; the 3-07 counterfactual for any new mechanism.
2. name_anchor: classify the single row from dossier D7. If the facts show the name lies on the lattice's west edge lon 90.0 with no spool record, record the facts and class `spool` only if the extractor code (dossier D3/D7 citation) is what produced the mismatch; otherwise state what is unestablished and report `blocked`.
3. The disc defect near polygon 65623: one section stating its class, with the 3-07 evidence, and the rows it accounts for per kind.
4. `triage/rules_other.json`: rules for the three kinds (schema of 3-05), run `classify` with both rules files merged (`rules_bg.json` rules first, then `rules_other.json`), `PARTITION OK` on all five kinds.
5. `triage/cause_table.md`: ONE table: rows = (kind, cause, rule id, rows, groups), per-kind sums equal 1,438,558 / 16,549,569 / 824 / 752 / 1; per-cause totals; for each `checker` and `build` rule: the code location (file, function) the fix would touch and the count it should move (this is the input to fix units: do NOT write fix briefs); for each `spool` rule: its group count. Also the list "decisions needed from Cody" if any (for example `spool` groups > 10,000, or a build cause whose fix changes more cells than expected).
6. `triage/pinned_candidates.tsv`: group-granularity enumeration (format of `k1_triage.py enumerate`) of all rows currently classed `spool`, header line stating the dump and K1 commit it came from. If it would exceed 10,000 lines write only the first 100 and a final line with the total, and flag it for Cody.

### Keep untouched

3-07's files except for reading; code; dump files.

## Done evidence

- `k1_triage.py classify` with merged rules → `PARTITION OK` for all five kinds; `partition.txt` copied to `output/scratch-3-08/partition.txt`.
- Witness outputs for the new rules.
- `cause_table.md` arithmetic: per-kind sums equal the K1 totals (`output/scratch-2-07/k1_a.json`), checked by a 10-line script whose output is quoted in the report.
- The report's first line: per-cause totals over all five kinds, and whether any decision for Cody is needed.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Amendments (orchestrator, after 3-07 attempts 1-3)

1. Budget lifted: no file-read or turn limit; work to completion. Stops only: spool pin stop (distinct source shapes/rings > 10,000 for a rule) or a mechanism no witness explains (`blocked: unattributed`, naming rows). Do not force causes; a `build` guess from witness INVALID alone is not allowed.
2. Use the 3-07 Amendments verbatim for: witness criterion (items 4), rule schema (5), machine caps (6), side-table route (3), spool pinned at shape/source-ring level (attempt-3). Read `triage/causes_bg.md`/`rules_bg.json` (3-07 state; 3-07 is not closed: `background_boundary` has 14.6 M unattributed rows and S02 hit a pin stop at 10,001 rings) and reuse the witness scripts in `output/scratch-3-07/`.
3. Do NOT commit or push; leave the three `triage/` files uncommitted. Do not edit 3-07's `rules_bg.json`/`causes_bg.md`. `consolidated cause_table.md` states 3-07's partial state honestly.

## Amendment (parent standing decision; Cody HARD RULE: thresholds need a measurement story)
The 10,000-line / 10,000-group stops in this brief (item 5 "decisions needed", item 6 pinned_candidates, Amendment 1 item 1) are RETIRED: they had no measurement story. S02 (3-07) is carried as ONE `spool` rule with count, witness and counterfactual evidence; unvisited and unattributed rows stay unattributed. `pinned_candidates.tsv` is a candidate view, not an exhaustive pinned list; a pinned list is enumerated from a rule with `k1_triage.py enumerate` by a later unit at the granularity it needs. See 3-07's matching amendment.
