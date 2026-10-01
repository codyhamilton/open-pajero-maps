# Brief: 3-07 — Cause table for `background` and `background_boundary` (18 million rows)

Consumer: the orchestrator, who authors the fix units inline from this table (see DESIGN.md Phase 3 Units, "Fix units"); 3-08 (reuses the rules); 3-90.
Owned paths: new `docs/plans/04-c-core-orchestration/triage/rules_bg.json`, new `docs/plans/04-c-core-orchestration/triage/causes_bg.md`, `output/scratch-3-07/` (git-ignored scratch, scripts and tables). No other repo file. Do not edit any code, do not fix anything.
Commits: Commit the two `triage/` files to `master` and push when done evidence passes.
Depends on: 3-05, 3-06, 3-04 (the net for any later inside-rule fix; not read by this unit).
Runs alongside: nothing.
Tier: Flash is not recommended. RE-risky (HIGH): this unit decides what is a checker bug, a build bug or a spool bug. The orchestrator should ask for a stronger worker; if Flash is used, the Sonnet 5.5 review must re-run the witness (below) on its own sample. Mandatory Sonnet 5.5 review either way.
Budget: 12 files to read, rules file of at most 40 rules, scripts of about 300 lines, 100 tool turns. Past the budget, stop; write a handoff in `IMPLEMENTATION.md` (rules authored, rows classified, what is left); commit the partial rules file; report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Phase 3 Outcome; Assumption 1; Assumption 4; Gates ("A check tolerance moves only in Phase 3, on a recorded cause").
2. `output/scratch-3-06/dossier.md` — the facts on polygon 65623 and the sample cells (from 3-06).
3. `output/scratch-3-05/summary/*` — run `k1_triage.py summary` again if missing (3-05 brief for the command), especially `by_level_type.tsv`, `by_src.tsv`, `groups_background*.tsv`.
4. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` Amendment (findings 2 and 3); `2-04-k1-background-kinds.md` (the rules as K1 applies them).
5. `parser/tools/quantisation_roundtrip.py` — `Region.inside`, `outline_distance`, the `_check_block` background half (lines about 928-1005), and how the shape window (cells grown by one, plus the tall set) is chosen.
6. Build side, read only to know the rule: `parser/kiwiw/_e2.c` and `parser/build_alldata.py` for how a shape reaches every overlapped cell and how fill/interior covers are produced (3-07 "overlap cover" brief `docs/plans/03-map-layer-parity-remediation/briefs/3-09-shape-to-every-overlapped-cell.md`).

## Goal

Every row of the two kinds (1,438,558 + 16,549,569) is assigned by the rules file to exactly one cause class (`checker`, `build`, `spool`), proven by `k1_triage.py classify` (`PARTITION OK`), each rule independently witnessed, so the orchestrator can write fix units from facts.

## Contract

Cited from `DESIGN.md` Phase 3: "every failing item … is assigned exactly one cause — checker rule wrong, build (disc) defect, or spool/extraction defect — with the count per cause recorded." and Assumption 4: "extraction … get enumerated and carried … Only a build-side (C) cause is fixed in Phase 3". And Gates: "A check tolerance moves only in Phase 3, on a recorded cause." A tolerance loosened to reduce a count is not a cause.

Cause class definitions (fixed; use these words exactly):

- `checker`: the disc item is correct against the spool under the 3C-04 rule as written, but K1 (and the Python oracle that equals it) reports a failure because of the checker's own window, tie, tolerance, orientation or type handling. Witness: the brute-force check below says the item is valid.
- `spool`: the disc item is the build's faithful output for a spool shape (or spool cell content) that is itself defective, so the 3C-04 rule cannot hold for it. Witness: the counterfactual experiment below.
- `build`: the disc item differs from what the build's own rule produces for the spool shape. Witness: the same experiment, with the disc item persisting after the spool defect is removed or with the windowed rebuild differing from G.
- Rows that none of the three explain are NOT given a cause. They stay unclassified and the unit reports `blocked` naming them.

Candidate hypotheses to test, none assumed true (record for each: tested, how, outcome, rows):

- H1 checker: the shape window (cell ring plus tall pass) omits the source shape of far-reaching pieces (a polygon whose bounding box meets the block but whose home cell is farther than the ring and is not "tall").
- H2 checker: the boundary rule's tolerance applies along the scan line only; a vertex exactly on a polygon edge that is collinear with the scan line (and with the frame edge) falls out (float-key tie; this absorbs the Phase 2 carried "float-key tie").
- H3 checker: type handling (a disc type that spool stores under another type code; compare `any_type`).
- H4 spool: polygon rings carrying a bogus long edge (D2 of the dossier): the spool polygon contradicts itself (winding vs parity differ), so no rule holds.
- H5 build: fill pieces or interior covers written in cells the polygon does not cover (pieces whose cell centre is outside the polygon by both winding and parity, with a well-formed ring).
- H6 build: clip leaving sliver/chord pieces whose vertices are not on any outline (vertices off the spool outline by more than 0.5 along a clip chord).
- H7 any other mechanism you can name from `by_src.tsv`/`groups` evidence; name it, test it, record it.

## Changes

Procedure (do the steps in order; each has a stop rule):

1. Run `k1_triage.py summary` on the 3-03 dump (full G). From `by_level_type.tsv` and `by_src.tsv` list the top 30 (type, level, src) combinations by rows and the share of rows each covers. Record the cumulative share table in `causes_bg.md`. Stop rule: if the top 30 combinations cover < 90 % of rows, say so and continue by columns (`onb`, `in_eo_any`, `d_any`) rather than by source.
2. Draft rules from column predicates only (the schema in 3-05). Start with the largest groups. One rule per mechanism, not per cell; no rule may list cells. Run `classify` after each batch; stop when `PARTITION OK` or when 10 consecutive new rules claim < 0.1 % of the remaining rows each (then the remainder is reported, not forced).
3. Witness each rule independently of K1: script `output/scratch-3-07/witness.py` takes a rule id, draws 200 groups from `enumerate` (every k-th group of the key-sorted list with seed 20260930; all groups if fewer than 200), and for the first vertex of each group recomputes, with fresh numpy code that does NOT import `quantisation_roundtrip` or any K1 function and uses ALL spool shapes of the level (no cell window, no tall pass): even-odd inside any same-type shape; winding inside; distance to the nearest same-type outline. A `checker` rule needs the witness to say valid (inside, or within 0.5 of an outline) for all 200. A `spool` or `build` rule needs the witness to say invalid for all 200. A disagreement means the rule is wrong: split it by a column that separates the disagreements, or drop it.
4. Counterfactual experiment for every proposed `spool` or `build` rule (one experiment per distinct mechanism, not per rule): choose one failing cell with its neighbours as a window; make a copy of the spool cells for that window under `output/scratch-3-07/spool_cf/` with the suspected defect removed (for the bogus long edge: drop the closing edge or the offending vertex; state exactly what you changed); build the window with the repo's windowed build (see `parser/build_alldata.py --help` and the Perth/window options used by `parser/tests/test_build_alldata.py`; run it with the original spool first and confirm its cell bytes equal G's cell bytes) and re-run K1 on the rebuilt window (`--levels` and the block selection the driver supports, or the fixtures API in `parser/tests/k1_fixtures.py`). Outcome rule: failing pieces vanish with the defect removed → `spool`; they persist → `build`. If the windowed build cannot reproduce G's cell bytes from the original spool (window effects), report that as the blocker; do not guess.
5. Count per cause per kind per level. Write `triage/rules_bg.json` (final) and `triage/causes_bg.md` with: the cumulative table of step 1; one section per rule (id, cause, mechanism in one sentence, rows, groups, witness result "200/200" or the numbers, the experiment, hypothesis ids it settles); the hypotheses table (H1 to H7 with outcome); the per-kind per-cause sums with the arithmetic that they equal 1,438,558 and 16,549,569; the `enumerate` group counts for every `spool` rule (how many groups a pinned list would have).
6. If the `spool` rows' groups exceed 10,000, say so in the report headline: the orchestrator must ask Cody how to pin them (Assumption 1).

### Keep untouched

Dump files, all code, `output/scratch-2-07/`.

## Done evidence

- `.venv-rp/bin/python parser/tools/k1_triage.py classify --dump output/scratch-3-03/dump --rules docs/plans/04-c-core-orchestration/triage/rules_bg.json --out output/scratch-3-07/classify_bg` → `partition.txt` shows, for `background` and `background_boundary`, unclassified 0 and `PARTITION OK` (the other three kinds are classified in 3-08; use `--kinds background,background_boundary` if the tool supports it, else a rules file with temporary catch-alls kept in `output/scratch-3-07/`, not in `triage/`).
- Witness output for every rule: `output/scratch-3-07/witness_<rule>.txt` with 200/200 or the exception explained.
- Counterfactual output for every `spool`/`build` mechanism.
- The report's first line is the per-cause sums for the two kinds.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
