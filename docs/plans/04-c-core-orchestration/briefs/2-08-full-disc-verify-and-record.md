# Brief: 2-08 — Verify the full-disc results and record Phase 2

Consumer: the orchestrator (Phase 2 close sign-off; Cody signs the Phase 4 budgets and the PSS ceiling from this unit's numbers).
Owned paths: `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` (the Phase 2 record, appended), `docs/provenance.md` (entries for any new non-committed material 2-07 left that later phases rely on). No code. Nothing under `parser/`.
Commits: Commit to `master` and push when the record is written.
Depends on: 2-07 (its outputs in `output/scratch-2-07/` must exist and `status.txt` must end `ALLDONE`; otherwise report `blocked`).
Runs alongside: nothing.
Tier: Sonnet.
Budget: 6 files to read, no code, 30 tool turns. Past the budget: report `over budget` with what is checked.

## Required reading

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Phase 2 Outcome (the exact count table), Gates, Assumption 2, the H-budget wording.
2. `output/scratch-2-07/status.txt`, `k1_a.json`, `k1_b.json`, `k1_c.json`, `k1_j1.json`, `determinism.txt`, `d1_decode.json`, `py_checks.tsv`, `gates.txt`.
3. `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` (the format of the Phase 1 record) and `docs/provenance.md`.

## Goal

A judged, recorded verdict on every clause of the Phase 2 Outcome, from the files above only (rerun nothing heavy; if a file is missing or inconclusive, that clause is `unproven`, not assumed).

## Contract

Cited from `DESIGN.md`:

- "**K1 check.** Input: D1 rows plus the spool via the same zero-copy reader. Output: for each check kind an exact `checked` count and an exact `failing` count, plus a bounded sample of failing items per kind (cell, type, shape id, vertex) so triage can start from them. Counts are exact; only samples are capped. Check kinds and tolerances are those of 3C-04's brief (`range`, `step`, `road_node`, `name_anchor` with its halo and subcell explained-categories, `background`, `background_boundary`, `completeness`, `interior_cover`); a tolerance or rule change is made only in Phase 3, with the reason and the count it moves recorded."
- "**Determinism.** D1 and K1 output is byte-identical for any worker count. The sample for each kind is the first N failing items in `(level, iy, ix)` order, then shape/vertex order; N is fixed in the header. Gate: a `-j 1` and a `-j 12` K1 run compare byte-equal."
- "Contract H budgets ... Decode and check join as hot paths H5 and H6." and "**Evidence.** Every hot call reports C-side wall and call counts."

## Changes

Write the Phase 2 record into `IMPLEMENTATION.md`, in the Phase 1 record's format, containing:

- A table of K1 `checked`/`failing` per kind against the 3C-04 table (range 309,192,246 / 0; step 252,444,802 / 0; road_node 42,995,770 / 0; name_anchor 2,317,983 / 1; background 174,332,105 / 1,438,558; background_boundary 89,546,388 / 16,549,569; completeness 1,800,514 / 752; interior_cover 1,592,016 / 824) and the explained counters (name_anchor_halo 311,347; road_node_subcell_on_polyline 551,530). Any difference is listed cell by cell as a deviation; do not round or call "close".
- The three K1 walls and their median against the 120 s bar; the summed-PSS peak against the provisional 22 GB ceiling; the proposed re-signed ceiling (peak plus the margin the DESIGN names, or, if it names none, state the peak and ask Cody; invent no margin).
- `-j 1` vs `-j 12` byte-equality verdict.
- D1 equivalence: cite the 2-02 record of the goldens and R-sample equality and the G/R full results; the D1 full-disc decode wall.
- Per-check wall for the harness checks (`py_checks.tsv`) and D1 decode wall, laid out so Cody can sign the Phase 4 budgets (provisional 20 s `coord_scale`, 60 s others stand unless he changes them).
- Gate lines (sha 87a01b14…, Perth, goldens, H budgets) verbatim.
- A `Carried` section: what Phase 3 must know (the failing samples files and their paths), and anything unproven.

## Done evidence

- Every outcome clause appears in the record with `met`, `not met` (with the number) or `unproven` (with the missing file). No clause is blank.
- `git log -1` shows the commit; the record is pushed.
- `.venv-rp/bin/python -m pytest parser/tests/test_perf_inventory.py -q --basetemp=output/scratch-2-08/pytest` still passes (docs-only change check).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the commit sha, check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently: write it into this brief as a dated `## Amendment` and report it. Over budget: stop, commit what passes, put the handoff (done, not done, what you learned) in the report.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
