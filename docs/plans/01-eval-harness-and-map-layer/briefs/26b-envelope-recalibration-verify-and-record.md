# Brief: 26b — Full-Australia rebuild #3: verify the recalibration at scale; record final report

Consumer: implementation worker (fresh agent — do not resume unit 26's agent, same reasoning as
units 03b/15b/25b). Verification and documentation, plus committing unit 26's already-implemented
code change together with this unit's record — the same wait-split commit convention units 03b
and 15b use.
Owned paths: `parser/refdata/selection.json`, `parser/kiwiw/divide.py` (unit 26's change — commit
it, do not further edit it unless a check below fails; if it fails, report the failure, do not
silently patch the numbers to make it pass), `docs/plans/01-eval-harness-and-map-layer/PLAN.md`
(only: append a new "Build record (date)" heading — do **not** add Acceptance Criteria
checkmarks), `docs/design/target-disc.md` (only: the file table's WP1 `ALLDATA.KWI` map-layer
row's "deviations" cell), `docs/provenance.md` (only if a genuinely new non-committed artifact
class appears beyond the existing `output/*` entries).
Commit to the current branch when done evidence passes; push.
Depends on: 26 (its background run must be underway or finished, and its `selection.json`/
`divide.py` change must be present, uncommitted, in the working tree).
Runs alongside: nothing.

## Required reading, in order

1. Unit 26's report-back — the chosen lever(s), the rationale tied to 25b's numbers, the exact
   commands/log paths/PIDs it started, and its disk-space judgment. Do not re-derive or
   re-launch anything it already started.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — the Acceptance Criteria bullet marked
   `(units 26/26b)`, verbatim.
3. **Read this before doing any harness blind-spot workaround.** `PLAN.md`'s "Envelope harness
   blind spot, carried forward for 26b specifically" paragraph describes `envelope.py` (and
   sibling per-level checks) as iterating only the *generated* profile's levels, silently
   dropping a level `R` has content for but `G` does not. **This text is stale as of this
   writing.** `git log -- parser/harness/checks/envelope.py` shows commit `e629b91` ("Fix
   harness level-iteration gap...", 2026-09-14 — the day before this plan folder's 2026-09-15
   extension was authored) already changed `envelope.py`, `vocab.py`, and `mfde.py` to iterate
   the *union* of reference and generated level keys, treating a level missing from `G` as an
   all-zero level and genuinely FAILing it rather than skipping it. Confirm this fix is still
   present in the landed code (read `envelope.py` around its level-iteration loop; look for the
   "Iterate the union of R's and G's levels" comment) before doing anything else. Do **not**
   attempt to re-implement a fix that already exists, and do **not** assume the acceptance
   bullet's "every level R has content for is confirmed present" requirement needs a manual
   workaround — the current code already enforces it structurally. Report this discrepancy
   between `PLAN.md`'s text and the actual landed code either way, per this brief's own
   "do not resolve contradictions silently" instruction below.
4. `docs/plans/01-eval-harness-and-map-layer/briefs/20-envelope-selection-calibration.md` — for
   context on what "closes, or narrows, the gap" is allowed to mean (a residual gap is reported,
   not silently dropped).

## Goal

Confirm unit 26's rebuild reflects the recalibration, run it through the harness, and record
whether the envelope FAIL closes (or narrows, with the remainder named) at full scale — landing
unit 26's code change and this record as one commit.

## Contract

`PLAN.md`'s Acceptance Criteria bullet marked `(units 26/26b)`, verbatim: a second post-
recalibration full-Australia rebuild's `compare_disc.py --checks envelope` report shows every
level's `parcel_count`/`name_count` ratio inside `[0.5, 2.0]x`, or the report names which
level(s) remain out of range and why. Every level `R` has content for must be confirmed present
in the fresh report before this bullet is treated as met (see item 3 above for the current, not
stale, mechanism enforcing this). The harness config may not be loosened by this unit.

## Changes

1. Wait for unit 26's background job to finish (one blocking wait per stage, one tool call).
2. Read the `time -v` logs for wall time/RSS; read `output/manifest.json` for size and SHA-256.
3. Run the full harness: `.venv-rp/bin/python parser/compare_disc.py --reference
   /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/report.json`
4. Read `output/report.json`'s `envelope` check: for every level, is `parcel_count`/`name_count`
   inside `[0.5, 2.0]x`? Cross-check the set of levels present in the report against
   `parser/refdata/profile/map.json`'s level set (the reference's actual levels) to positively
   confirm no level is silently missing — this is the acceptance bullet's explicit requirement,
   not optional, even though (per item 3 above) the current code already guards against the
   underlying bug structurally.
5. If a gap remains at any level, name it explicitly (level, field, generated/reference/ratio
   values) rather than summarizing it away — per brief 20's escape hatch, a named residual gap
   satisfies the acceptance bullet; a silently-dropped one does not.
6. Round-trip regression: `.venv-rp/bin/python -m pytest parser/tests -q`.
7. Write the build record into `PLAN.md` (wall time, RSS, size, SHA-256, the full per-check
   table, the envelope per-level table for every level, and an explicit statement of level
   coverage confirmed against the reference profile's level set) and any genuine new deviation
   into `docs/design/target-disc.md`'s file table.
8. Commit unit 26's `selection.json`/`divide.py` change together with this unit's doc updates as
   one commit (mirroring how units 03b/15b commit the prior unit's code together with the
   verification record); push.

## Done evidence

- `output/report.json` exists; its `envelope` check's per-level `parcel_count`/`name_count`
  ratios recorded for every level, either inside `[0.5, 2.0]x` or explicitly named as a residual
  gap with generated/reference/ratio values.
- Level coverage cross-checked against `parser/refdata/profile/map.json`'s level set — no level
  silently absent.
- `pytest parser/tests -q` passes with no regression in replicate-mode byte-identical tests.
- `git log` shows one commit landing unit 26's `selection.json`/`divide.py` change together with
  the build record and any deviation entries.
- `git status` clean after commit; no file in `output/` staged.

## Report back

The full per-check table, the envelope per-level `parcel_count`/`name_count` table for every
level (quoted, not summarized), whether the gap closed or narrowed (naming what remains, if
anything), the level-coverage confirmation, the discrepancy between `PLAN.md`'s stale
blind-spot text and the already-fixed code (item 3 above), and any other contradiction you found.
**Do not resolve contradictions silently — report them.** If you find a non-trivial bug outside
this unit's own contract, report it (symptom, location, root cause if found) and leave it — do
not fix it here.
