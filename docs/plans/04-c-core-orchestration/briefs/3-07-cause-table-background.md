# Brief: 3-07 — Cause table for `background` and `background_boundary` (18 million rows)

Consumer: the orchestrator, who authors the fix units inline from this table (see DESIGN.md Phase 3 Units, "Fix units"); 3-08 (reuses the rules); 3-90.
Owned paths: new `docs/plans/04-c-core-orchestration/triage/rules_bg.json`, new `docs/plans/04-c-core-orchestration/triage/causes_bg.md`, `output/scratch-3-07/` (git-ignored scratch, scripts and tables). No other repo file. Do not edit any code, do not fix anything.
Commits: Commit the two `triage/` files to `master` and push when done evidence passes.
Depends on: 3-05, 3-06, 3-04 (the net for any later inside-rule fix; not read by this unit).
Runs alongside: nothing.
Tier: Flash is not recommended. RE-risky (HIGH): this unit decides what is a checker bug, a build bug or a spool bug. The orchestrator should ask for a stronger worker; if Flash is used, the Sonnet 5.5 review must re-run the witness (below) on its own sample. Mandatory Sonnet 5.5 review either way.
Budget: SUPERSEDED by Amendment 1 below (attempt 1 stopped at the old 12-file limit with 0 rows attributed).

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

## Amendments (attempt 2, orchestrator, after attempt 1 ended `over budget; blocked: unattributed`)

1. Budget lifted: no file-read limit, no turn limit; rules file at most 60 rules; scripts as long as needed. Work to completion. The only stops are: spool rule-level groups > 10,000, or a mechanism no witness explains after you have tried the steps (then `blocked: unattributed`, naming rows). Do not stop for budget. Write findings to `output/scratch-3-07/notes.md` as you go.
2. First step (before the original step 1 hypotheses), using the existing `output/scratch-3-05/summary/*` and the dump (you have `handoff.md` and `analysis_counts.json` in `output/scratch-3-07/` from attempt 1; facts there are unverified claims, re-derive what you rely on):
   a. SENTINEL SOURCES: 94.5% of the 17,988,127 rows have no same-type spool outline within `K1_DIAG_SAME` (64 raw) (type 291 L0 11,562,264; 288 L0 3,425,163; 289 L0 418,187; 578 L0 390,509; 289 L2 113,723; 288 L6 3,725). Establish what these are: for a sample of groups from each (kind, level, type), use the witness (below) over ALL spool shapes of the level to compute even-odd and winding inside, and the distance to the nearest same-type AND any-type outline at unbounded radius. State whether the failing pieces are far from any same-type outline (true fills/pieces off the polygon: `build`/`spool`), or the diagnostic is blind (radius too small: then rule predicates on `d_src` are useless and you must use witness-derived columns in `output/scratch-3-07/` side tables instead of dump columns).
   b. `onb=0` ROWS: 31,416 `background_boundary` rows have `onb=0`. Determine whether `onb` is a diagnostic frame/coordinate mismatch (read `_k1_bg.c` for how `onb` is set) or real.
   c. Only then continue with the original steps 1-6.
3. Rule predicates may use dump columns only (the `classify` schema below). If the witness shows a mechanism that dump columns cannot separate, you may extend the DUMP only through a recorded side table: write per-group witness results to `output/scratch-3-07/side_<kind>.npy` and state in `causes_bg.md` which rules depend on them; do not edit repo code. A rule whose predicate cannot be expressed in dump columns is still reportable by (kind, level, type, group-list from your side table); say how its groups are enumerated.
4. Witness criterion corrected (replaces step 3's "inside, or within 0.5 of an outline"). A `background` item is valid iff the point is even-odd inside some same-type shape polygon of the level (NOT "or near an outline"; a background piece is a fill so the 3C-04 rule requires the interior). A `background_boundary` item is valid iff the point is within the K1 boundary tolerance of a same-type outline: use the 3C-04 / `2-04-k1-background-kinds.md` tolerance as K1 applies it (`K1_TOL`, `K1_EPS`; read `_k1.h`) and state the number you used. The witness takes row-specific points and kinds from the dump; it still must not import `quantisation_roundtrip` or K1 code. `checker` requires witness VALID; `spool`/`build` requires witness INVALID (all 200 sample groups each).
5. Rule schema for `classify` (inlined from 3-05; do not read the brief): `{"version":1,"rules":[{"id":"R01","cause":"checker|build|spool","kind":"background_boundary","where":[["level","==",0],["in_eo_any","==",1]],"note":"text"}]}`. Operators `== != < <= > >= in isnan notnan` (`in` takes a list). Columns are the dump column names plus `level`. First matching rule wins. Unknown cause or column is exit 2. `classify` has no `--kinds`: temporary catch-all rules for the other three kinds live in `output/scratch-3-07/rules_all.json`, never in `triage/`. Outputs: `cause_counts.tsv`, `assign_<kind>.u16`, `unclassified_groups.tsv`, `partition.txt`.
6. Machine caps (standing): every heavy run under `flock output/.heavy.lock`; no two heavy jobs at once; cbuild/make at most -j4; K1/harness at most -j6; do not drop caches. Do NOT commit or push; leave the two `triage/` files uncommitted. Keep `output/scratch-2-07/`, `output/scratch-3-06/` untouched.
7. Counterfactual builds are heavy: run one window at a time.

## Amendments (attempt 3, orchestrator, after attempt 2 stopped on S02 = 145,960 groups)

Standing decision (parent; BTM notified; Cody can override): **spool rows are pinned at shape / source-ring level**, not group level and not as one opaque carried rule. Attempt 2's R01 (checker, 920,773) and S02 (spool, 11,127,845) and their witnesses/counterfactuals stand as evidence (after the Sonnet review's mechanical fixes in `triage/`); keep them.
1. The 10,000-group stop (Amendment 1 item 1) now applies to the number of distinct spool SHAPES / source rings a rule pins, not `classify` groups. Count and report both. If distinct pinned shapes per spool rule exceed 10,000, stop and bounce.
2. Pin enumeration: for each `spool` rule produce `output/scratch-3-07/pins_<rule>.tsv` with one row per distinct (level, source shape identity as home cell + record + tall, as the spool stores it; type; vertex count; the defect, e.g. the crossing edge pair), plus rows and groups it explains. Source identity must come from a witness-derived side table (Amendment 3 route allowed): the dump's nearest-source columns are not producer identity (attempt 2 finding 3: nearest-shape identity cannot establish a producer). State how the producer was found (e.g. the crossing ring that actually generates the failing outline piece) and test it on a sample: removing that one shape's defect must remove its rows (counterfactual, one window at a time).
3. Remaining work: the ~5.9 M unattributed rows (`background` 517,785; `background_boundary` 5,421,724). Attribute by mechanism with witnesses and counterfactuals; extend the side-table route for producer topology as needed. Do NOT force a cause: rows no witness explains stay unattributed and are named. A guess `build` from witness INVALID alone is not allowed (attempt 2).
4. Done evidence: `classify` with the final rules gives `PARTITION OK` for the two kinds only if every row is attributed; otherwise report `blocked: unattributed` with strata, counts and what evidence is missing. Also deliver: `triage/causes_bg.md` updated (pin table by shape per spool rule), `triage/rules_bg.json`, `pins_*.tsv` counts in the report headline.
5. Machine caps and no-commit/no-push stand. Keep the Sonnet-fixed `triage/` content as the base (read it first; edit, don't restart).
6. Review findings carried into attempt 3 (Sonnet 5.5, `triage/review_3-07.md`: ACCEPT, R01/S02 witnesses reproduced on a 50-group sample, seed 20261002): (a) S02's counterfactual (`cf_291`) removed only 240 of 829 window failures (29%) and the 589 residual is unexplained; S02 may stay `spool` for rows whose producer you identify, but state the residual and attribute or leave unattributed what the producer test does not explain; do not extend S02 by analogy. (b) In `cf_short_ring` completeness failing went 0 to 1 after the change; explain it in `causes_bg.md`.

## Amendments (attempt 4 decisions, parent standing decision; Cody HARD RULE: thresholds need a measurement story)

1. The 10,000 group / shape pin stop (Amendment 1 item 1, attempt-3 item 1, the original step-6 10k line) is RETIRED. It had no measurement story, and the S02 mechanism (crossing closing edge of an explicitly closed ring) is already proven by witness (200/200 and the Sonnet 50/30-sample reproductions) and byte-gated counterfactuals.
2. S02 is CARRIED as ONE rule: `spool`, with its row count, the witness result and the counterfactual evidence, and the pinned shapes already enumerated (10,001 rings, 25,772 groups, 1,939,053 rows) as evidence, not as an exhaustive pinned list. The ~9.19 M `background_boundary` rows the producer scan did not visit stay UNATTRIBUTED (not claimed `spool` by analogy).
3. The ~14.6 M unattributed `background_boundary` rows (and `background` 517,785) are CARRIED unattributed. No cause is forced; no further Sol dispatch on them without new predicates (a new mechanism hypothesis that dump columns or a side table can express).
4. Any pin list a later unit needs is enumerated with the `k1_triage.py enumerate` tool from the rule, at the granularity that unit's own measurement requires.
