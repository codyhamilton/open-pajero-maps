# Brief: 3-03 — Checker demands only representable footprints (groups 2-01 and 2-02)

Consumer: Codex `gpt-6.1-sol`, reasoning high, in worktree `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached HEAD at the plan tip).
Owned paths:
- `parser/kiwiw/_k1_cmp.c`
- `parser/kiwiw/_k1.h`, `parser/kiwiw/_k1.c`, `parser/kiwiw/_k1_bg.c` — only to carry per-shape `mult_const` into `k1_shapes` if it is not already there
- `parser/tools/quantisation_roundtrip.py` — `_required_cells`, the completeness block of `_check_block`, and the per-shape mult carriage that feeds it; nothing else
- new `parser/tools/k1_representable.py`
- new `parser/tests/test_k1_completeness_representable.py`
- `parser/tests/k1_fixtures.py` — additions only
- `docs/plans/14-completeness-root-cause/reports/3-03-checker-representable-demand.md`
- scratch under `output/scratch-14/p3/` and `output/scratch-14/runs/`

Touch nothing else. **`parser/kiwiw/_cenc.c` is read-only.**
Commits: Commit to the current detached HEAD when done evidence passes, with a plain-summary title and no trailer. Do not push.
Report: before committing, write `docs/plans/14-completeness-root-cause/reports/3-03-checker-representable-demand.md` (a handoff; rubric in `tools/quality/checks/execution-report.json`) and include it in the commit.
Depends on: 3-01. Its `triage/demand_attribution_3-01.tsv` is the prediction. Dispatched after 3-02.
Runs alongside: nothing.
Budget: 14 files to read, about 450 lines changed or added (C, Python, tests), 90 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/14-completeness-root-cause/IMPLEMENTATION.md` (done, not done, what you learned), commit only if tests pass, and report `over budget`.

## Required reading, in order

1. `docs/plans/14-completeness-root-cause/DESIGN.md` — "Domain: fix or proven non-deviation", "Phase 3", and the "Phase 3 refine" record (locus decisions; settled).
2. `docs/plans/14-completeness-root-cause/triage/demand_attribution_3-01.md` and `.tsv` — the per-key demanders and the `all_demanders_unrepresentable` prediction.
3. `parser/kiwiw/_k1_cmp.c` — whole file.
4. `parser/tools/quantisation_roundtrip.py:1026–1100` — `_required_cells` and its docstring ("whether such a sliver survives rounding is the clip's business, not a check").
5. `parser/kiwiw/_cenc.c:534–603` — `emit_piece`, the wire contract (densify `lim = 127·mc − 1`, `rint`, dedup, area test). Read only.
6. `docs/plans/14-completeness-root-cause/triage/complete_repair_2-02.py` — `decompose_eo_faces`, `encoder_piece_densified`. These are the Phase 2 mirror, cross-checked against production C on 774 sources.
7. `parser/tests/test_k1_completeness.py`, `parser/tests/test_quantisation_roundtrip.py` (completeness cases), `parser/tests/k1_fixtures.py:297+`.
8. `parser/kiwiw/cbuild.py` — `EXT_SOURCES` and the hash-keyed rebuild of `_cenc.so`.
9. `parser/tools/run_heavy_python.py` — usage.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

DESIGN Phase 3 outcome (1), **checker**, for groups `g-omits-cell-local-dvd-type` (2-01, 342) and `r-absent-complete-repair-zero` (2-02, 432):
- the checker change lands;
- the predicted rows leave the failing set;
- the build sha is unchanged.

## Contract

- Settled locus (refine): both groups are checker over-demand. Phase 2 proved that every member's demanding source gives 0 production-C records in the target cell (2-01 342/342, 2-02 432/432). The builder emits nothing because the spool holds nothing representable there, so a build change would have to invent geometry. 3-01 shows which branch lets each such source through.
- New completeness rule. A demanded `(cell, type)` with no decoded piece fails **only if at least one of its demanding class-2 shapes has a representable in-cell footprint**: EO faces → clip to the cell → densify with the shape's `mc` → `rint` → the piece survives the wire contract's dedup/area test (≥3 distinct lattice points, area2 ≠ 0). Otherwise the pair passes as "demanded but unrepresentable".
  - `checked` keeps its meaning: the demanded-pair count is **unchanged** at 1,800,514.
  - Only `failing` moves.
  - The test runs only for demanded pairs that lack a piece, so the cost stays negligible.
- **Independence (settled):**
  - The checker must not call `_cenc.c`'s `emit_piece`, `kw__bg_shape`, or its EO/clip code. A checker that reuses the encoder cannot catch an encoder drop.
  - Implement the representability test in `_k1_cmp.c` (C, exact predicates: `int64`/`__int128` or exact rationals for crossings).
  - Implement it in lockstep in `parser/tools/k1_representable.py` for the Python oracle, ported from the Phase 2 mirror. `parser/tools` must not import from `docs/`.
  - C and Python must stay verdict-equal; `test_k1_completeness.py` asserts this.
- Do not loosen `TOL`, `SEARCH`, or any other kind's tolerance. Do not change branches (a)/(b)/(c) themselves; the new test filters their output. Do not touch `rules_*.json` or O01–O06 (DESIGN "Domain: fix or proven non-deviation", Non-goals).
- Disc in force: `output/scratch-14/G_new/ALLDATA.KWI`, sha `4ed9cd801bdd7099…`. Build sha unchanged means a fresh re-encode with the rebuilt `_cenc.so` hits the same sha. Plan-25 caps apply: encode `-j4`, K1 `-j6`, one heavy job at a time, everything through `run_heavy_python.py`.

## Changes

- Shape mult: if `k1_shapes` / the Python `Shapes` lack the per-shape `mult_const` the encoder uses for the spool shape, carry it. Find the spool source of `mc` via `complete_repair_2-02.py:source_attrs` and `_cenc.c`. Default to 1 only where the encoder does.
- `_k1_cmp.c`: after `req`/`pres` are sorted, keep for each missing pair its demanding shape indices (track them when pushing to `req`). Fail the pair only if some demander is representable. Update the file's header comment to state the rule.
- `quantisation_roundtrip.py`: give `_required_cells` the same demander tracking, and apply the same filter in the completeness block. Update the docstring to state the rule.
- Tests (`test_k1_completeness_representable.py` + fixtures). Each case asserts C == Python:
  - (i) A zero-width vertical sliver passing within `TOL` of the cell centre (branch c via `TOL`) → no failure.
  - (ii) A ring poking ≤2.5 raw into a cell with one vertex ≥1 raw inside (branch b) that rounds away → no failure.
  - (iii) A representable square, and a representable sliver that does survive densify + `rint`, with G missing → **still fails**. This is the positive control proving the check is not blinded.
  - (iv) A self-crossing bowtie with one representable lobe → still fails.
  - (v) 656-style: emits without densify, collapses with densify → no failure.
- Existing tests: run `parser/tests/test_k1_completeness.py`, `test_quantisation_roundtrip.py`, `test_k1_dump.py`, and `test_plan25_memory_guards.py`. If an existing expected completeness count changes, change it only after showing that fixture's demand is unrepresentable, and list every such edit in the report. Otherwise stop and report.

### Keep untouched

- `_cenc.c` and every encoder path.
- Every other K1 kind's logic and tolerance.
- Phase 1/2/3-01/3-02 artefacts.
- The protected outputs: `output/scratch-3-11/G_new` (`013586b5…`), `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`), and `output/extract_timing/spool`.
- Never delete anything under an `output` path.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- New tests fail before the change: (i), (ii), and (v) fail; (iii) and (iv) pass. After the change, all pass. The existing suites listed above pass.
- Live K1, through `run_heavy_python.py --log output/scratch-14/runs/k1_p3.json`:
  ```
  quantisation_roundtrip.py --disc output/scratch-14/G_new/ALLDATA.KWI --spool output/extract_timing/spool --out output/scratch-14/p3/k1_p3.json -j 6 --engine c --dump-failures output/scratch-14/p3/dump --dump-kinds completeness
  ```
  The expected result:
  - completeness `checked` 1,800,514, unchanged;
  - `failing` = 776 − (count of 3-01 keys with `all_demanders_unrepresentable`);
  - the surviving failing keys are **exactly** the 3-01 exceptions, as an identity diff against `output/scratch-14/dump_raw/`, with no new key;
  - every other kind's `checked`/`failing` is identical to `output/scratch-14/k1_full.json`.
- Every 2-01 and 2-02 member key is absent from the new failing set, except members that 3-01 lists as exceptions (a representable demander exists). Those survive by prediction and are named in the report as build-defect candidates. Any other surviving member is a prediction failure: name it, do not paper over it.
- Re-encode with the rebuilt `.so`:
  ```
  run_heavy_python.py … parser/build_alldata.py --spool output/extract_timing/spool --out output/scratch-14/p3/G_reencode/ALLDATA.KWI -j4
  ```
  Expected: sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`.
- Both protected disc shas are unchanged (record both).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then:
- what changed;
- test output before and after;
- K1 totals before and after (completeness `checked`/`failing`; the other kinds unchanged);
- the identity diff summary;
- the re-encode sha;
- any existing-test expectation edits, each with its proof;
- any deviation from this brief and why;
- any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
