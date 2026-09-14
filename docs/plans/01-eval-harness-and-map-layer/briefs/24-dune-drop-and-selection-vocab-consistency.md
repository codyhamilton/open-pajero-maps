# Brief: 24 — Levels 10/12 background selection vs. vocab consistency (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve one of the two unresolved deviations from unit 15b's 2026-09-09 full-Australia
build (`docs/design/target-disc.md`'s `ALLDATA.KWI` map layer row, "Levels 10 and 12 spooled
zero content"). It is not part of the original 01-15b dispatch list; dispatch it
independently. See also brief 25 for the companion harness-iteration gap (already fixed
outside a brief — trivial).

Owned paths: `parser/refdata/selection.json`, `parser/refdata/vocab/bg_type.json`,
`parser/refdata/vocab/README.md`, `parser/tests/test_selection.py`, `parser/tests/test_vocab.py`
(only if a new coverage assertion is needed). Do not touch `parser/osm_to_parcel_geometry.py`,
`parser/kiwiw/selection.py`'s or `parser/kiwiw/vocab.py`'s *code* (loader/lookup logic) —
this is a data-calibration fix, not a code fix, unless investigation shows the loader itself
needs a catch-all-rule capability it doesn't have (see "Open question" below).
Depends on: 08 (vocab tables, done), 14 (selection, done).

## Required reading, in order

1. `docs/design/target-disc.md` — the `ALLDATA.KWI` map layer row (search "dune") for the
   exact bug description this brief resolves.
2. `docs/plans/01-eval-harness-and-map-layer/briefs/14-per-level-selection.md` and
   `docs/plans/01-eval-harness-and-map-layer/briefs/08-vocab-mapping.md` — the two briefs
   whose outputs are inconsistent.
3. `parser/refdata/selection.json` — the `"levels": 10` and `"levels": 12` rules' calibration
   notes: unit 14 picked `natural=dune` for these levels purely to match R's `shape_count=25`
   in *magnitude* (national dune-way count 38, ratio 1.52x — "inside the envelope"), without
   checking whether `bg_type.json` could ever map that tag to a non-null value.
4. `parser/refdata/vocab/bg_type.json` and `parser/refdata/vocab/README.md`'s "Levels 10/12"
   section (around line 194). This is the key finding: **R's own per-level census
   (`parser/refdata/profile/map.json`, levels `"10"`/`"12"`, `background.type_code_hist`) is
   `{"289": 6, "306": 11, "528": 8}` — there is no dune/sand-related code in R's real
   background vocabulary at these levels at all.** `natural=dune` was never a plausible
   choice on reference-disc evidence; unit 14 matched a *count*, not R's actual vocabulary.
   - `289` (water, generalised) and `306` (state boundary) are already correctly mapped in
     `bg_type.json`'s `[10, 12]` rule range, sourced from `natural=coastline/bay/sea/ocean/
     water/wetland/river/stream`, `waterway=river/stream/canal`, and
     `boundary=administrative`+`admin_level=4` respectively.
   - `528` ("road type 0" — roads rendered *as background shapes* at zoomed-out levels) is
     explicitly and deliberately unmapped: producing it requires a road-geometry-to-background
     data flow that unit 08's brief scoped out (`_osm_tags_to_bg_type` is tag-driven only).
     The README already flags this as "a gap for whichever later unit builds level 10/12
     backgrounds in full" — still open.
5. `parser/refdata/profile/map.json` — levels `"10"`/`"12"` entries in full (background,
   name, road sections) — the target this brief's fix should move `G` towards.
6. `parser/kiwiw/vocab.py` — note `bg_type.json`'s `[0, 0]` and `[2, 8]` rule ranges both end
   in a catch-all `{"match": {}, "value": ...}` rule, but the `[10, 12]` range has **no
   catch-all** — `default: null` applies directly. This means *any* tag `selection.json`
   admits at levels 10/12 other than the three already-mapped classes (coastline/water/
   wetland/river/stream/waterway, or boundary=administrative+admin_level=4) will silently
   drop, exactly as `natural=dune` does today. This is the general form of the bug, not a
   dune-specific one — flagged in unit 15b's report as "unit 14's own selection.json vs.
   unit 08's vocab/bg_type.json are inconsistent" (general, not dune-only).

## Why this was not fixed as a trivial one-liner

Two options were considered and rejected as trivial:

- **Map `natural=dune` to a bg_type code.** Rejected: R's real level-10/12 census has no
  dune/sand-related code at all (`{289, 306, 528}` only). Inventing a code for dune would not
  be reference-backed; it would just move the mismatch from "silently dropped" to "wrong code
  emitted," which the `vocab` check would then FAIL on for a different reason.
- **Just delete `natural=dune` from `selection.json`.** This removes the wasted
  computation (ways matched, converted to a shape, then dropped) but does **not** fix the
  actual symptom the design doc row complains about ("spooled zero content") — level 10/12
  background output stays at zero either way, since `selection.json`'s levels 10/12 rules
  currently admit *only* `natural=dune` and nothing that maps to `289` or `306`.

The real fix — making levels 10/12 spool genuine, R-shaped content — requires
**re-selecting** `selection.json`'s level 10/12 background rules to match the tags
`bg_type.json` already supports (coastline/water/wetland/river/stream/waterway, and
`boundary=administrative`+`admin_level=4`), and then **recalibrating** the selection against
a real national tag count (unit 14's own method: an osmium tags-only pass over
`australia-260824.osm.pbf`) to check the resulting count lands inside the harness's
`count_ratio` envelope ([0.5, 2.0]x around R's `background_count=25` at both levels). That PBF
extract is a large, regenerable, non-committed file (see `docs/provenance.md`) not available
in this worktree, and the calibration step is exactly the kind of design/data work unit 14's
own brief treated as real effort ("Do not run a full-Australia extract+build to iterate; use
the cheap counting path for every tuning pass"). Blindly swapping the tag list in without that
verification risks trading one silent failure (zero content, at least honestly reported once
brief 25's harness fix lands) for an uncalibrated over- or under-shoot that's harder to
diagnose. This is a genuine "broader selection/vocab consistency problem needing design work,"
per the dispatching task's own classification criteria — not implemented here.

`528` (roads-as-background) remains **out of scope** for this brief too: R's `type_code_hist`
shows it is 8 of the 25 background shapes at each of levels 10/12 (32%) — a meaningful chunk
of the target, but closing it needs the road-geometry-to-background bridge the vocab README
already flagged as future work, not a selection/vocab table edit.

## Goal

1. Change `selection.json`'s `"levels": 10` and `"levels": 12` rules' `"background"` list from
   `[{"key": "natural", "value": "dune"}]` to the tag set `bg_type.json`'s `[10, 12]` range
   actually maps (see reading item 4), OR determine (via the calibration method below) that
   this over-shoots the envelope so badly that a narrower subset is needed, and record which
   subset and why.
2. Recalibrate using unit 14's own dry-run counting mode (`selection.py`, cheap tags-only
   osmium pass — see brief 14's "Calibration method" comment in `selection.json`) against
   `australia-260824.osm.pbf` (provenance: `docs/provenance.md`; re-download/re-extract per
   that entry if not already present locally) to confirm the resulting national way count for
   the new tag set lands inside `[0.5, 2.0]x` of R's `background_count=25` at levels 10 and 12.
3. Decide whether to add a catch-all rule to `bg_type.json`'s `[10, 12]` range (matching the
   pattern already used at `[0, 0]` and `[2, 8]`) to make this class of bug structurally
   impossible at these levels going forward — and if so, what value it should emit (R has no
   catch-all-shaped code at these levels the way `288` serves that role at 0/2-8, so this may
   not have a clean answer; report the finding either way, don't force a catch-all that isn't
   reference-backed).
4. Update `parser/refdata/vocab/README.md`'s "Levels 10/12" section to reflect whatever is
   decided (it currently documents the `528` gap but not this selection/vocab mismatch).

## Contract

Same envelope contract as brief 14: `harness.json`'s `envelopes.count_ratio` (default
[0.5, 2.0]) at levels 2..12. Do not change the tolerance to make a level pass. If the
achievable selection (given only tag-driven, no road-geometry-bridge background types) cannot
be brought inside the envelope, report the achievable numbers and stop, per brief 14's own
rule — this is not new scope, it's finishing brief 14's job with the missing cross-check
against `bg_type.json` that should have happened the first time.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- Dry-run counts (via `selection.py`'s counting mode) showing the new levels 10/12 background
  selection's national count vs. R's `background_count=25` at each level, with the resulting
  ratio.
- `.venv-rp/bin/python parser/compare_disc.py --checks vocab --generated <a real or synthetic
  build with the new selection>` (once brief 25's harness fix has landed) should no longer show
  levels 10/12 silently absent from the report.

## Report back

A short summary: the tag set landed on, the calibration ratio achieved, whether a `bg_type.json`
catch-all was added (and its value/rationale, or why not), and any remaining gap against R's
real `{289, 306, 528}` census (expect `528` to remain unaddressed — that's a separate,
larger unit). Do not resolve the `528` gap silently by inventing a tag-driven proxy for it —
report it as still open, per the vocab README's existing note.
