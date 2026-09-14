# Brief: 20 — envelope FAIL: parcel_count/name_count out of [0.5,2.0]x range (ad hoc)

Consumer: implementation worker. This brief was authored by an investigation agent
tracing one of six unresolved deviations from WP1 unit 15b's 2026-09-09 full-Australia
build (`docs/design/target-disc.md`'s `ALLDATA.KWI` map layer row, envelope FAIL: "20
failures, levels 8/6/4/2/0: parcel_count and name_count outside the [0.5,2.0]x envelope
... several background/name sub-frame maxes exceed R's per-level max"). It is not part
of the original 01-15b dispatch list; dispatch it independently, the same way brief 17
was.

Owned paths: not yet assigned — this brief documents a *design* problem, not a
mechanical fix. Likely touches `parser/refdata/selection.json` (calibration only, if a
future worker concludes a numeric tweak suffices) and/or `parser/kiwiw/divide.py` /
`parser/osm_to_parcel_geometry.py` (name-record generation) and/or
`parser/harness/checks/envelope.py` (if the envelope's own tolerance, not the generator,
turns out to be miscalibrated). A future `refine` pass should scope owned paths once the
approach is chosen.
Depends on: unit 14 (done, `dfe4d7d`/`bfa8fe9`), unit 15/15b (done, `eda5c09`).
Blocks: nothing declared; the envelope FAIL is already recorded as an unresolved
deviation in `docs/design/target-disc.md`, so this brief is the follow-up, not a gate.

## Why this is a brief, not a direct fix

The investigation could not identify a safe, verifiable calibration-only fix, for two
reasons:

1. **The exact 2026-09-09 failure numbers no longer exist.** `output/report.json` (the
   file with the per-level `generated`/`reference`/`ratio` breakdown the `envelope`
   check writes) is explicitly non-committed/regenerable per `docs/provenance.md` and is
   not present in this worktree — `output/` is empty. The only surviving records are
   summary prose in `docs/design/target-disc.md` and
   `docs/plans/01-eval-harness-and-map-layer/PLAN.md`'s "Build record (2026-09-09)"
   section: "20 failures across levels 8/6/4/2/0 (parcel/name counts outside
   [0.5,2.0]x, several sub-frame maxes over R's)" — no per-level generated/reference
   values, no ratios, no indication of which sub-frame kind(s) (road/background/name)
   or which direction (over vs. under). Reproducing those numbers requires a full
   `osm_to_parcel_geometry.py` + `build_alldata.py` + `compare_disc.py --report` run
   (33:23 + 6:44 wall time per PLAN.md's timing table) — expensive/slow, and explicitly
   out of scope for this investigation to trigger.

2. **The failing counts are not levers `selection.json` controls directly**, so even
   with exact numbers a numeric tweak to `selection.json` cannot straightforwardly close
   the gap:

   - **`parcel_count`** (`parser/harness/checks/envelope.py`'s `_parcel_count`, sum of
     `parcel_count_by_type`) is not an extraction-time admission count at all. It is
     produced by `parser/kiwiw/divide.py`'s `divide_oversize_parcels` (see
     `divide.py:284-330`): a parcel is split into more parcels only when its *encoded
     byte size* exceeds `threshold_bytes`, which depends on the combined volume of
     admitted roads + backgrounds + names in that cell, not on any single admitted-class
     count. `selection.json` (unit 14, `parser/kiwiw/selection.py`) only gates *which*
     OSM features are admitted per level via `level_filter(level, tags)`; it has no
     input into `divide.py`'s size-driven splitting decision. Raising or lowering
     admission thins or fattens per-cell content, which only *indirectly* nudges
     `parcel_count` through a threshold comparison unit 14 never modeled — unit 14's own
     calibration notes (`parser/refdata/selection.json`'s per-level `_calibration_note`
     fields) discuss `link_count`/`background_count` ratios exclusively and never
     mention `parcel_count`.

   - **`name_count`** (`profile.py`'s `name_record_count`) is likewise not a directly
     admitted class. `parser/osm_to_parcel_geometry.py`'s `_handle_way` emits one
     `NameRecord` for **every admitted road that has a `name` tag** (lines ~751-759,
     triggered whenever `any_link` is true for that way) and one for **every admitted
     background shape that has a `name` tag** (lines ~775-778), in addition to the
     `place`-node records `_handle_node` emits (lines ~674-697, the only class unit 14's
     calibration notes actually discuss for `name_count`). So `name_count` at every
     level is `place_node_count + count(admitted named roads) + count(admitted named
     backgrounds)` — a byproduct of the `highway`/`background` admission lists unit 14
     tuned for `link_count`/`background_count`, not an independently calibrated
     quantity. Unit 14's own report (`IMPLEMENTATION.md` "Unit 14") never validated
     `name_count` against R's per-level name census at all — it flagged levels 4 and 8
     as "close to the 2.0x ceiling" and "approximation risk" for the *way-count* ratios
     only, and separately reported the level 10/12 `place=suburb` target as
     unreachable (left at 0, ~529x overshoot if admitted at all) — but never checked
     what the same admission lists imply for `name_count`.

   Given levels 4 and 8 were already flagged by unit 14 as sitting close to (1.95x,
   1.83x) the `link_count`/`background_count` ceiling on raw way counts alone, and that
   named-way admission adds a further `name_count` increment on top of the same
   admission lists, an overshoot at levels 8/6/4/2/0 on `parcel_count` (more admitted
   content -> more oversize splits) and `name_count` (more admitted named
   roads/backgrounds -> more name records) is the expected shape of the failure — but
   confirming the actual magnitude, and whether it is a modest overshoot fixable by
   trimming `selection.json`'s `highway`/`background` lists a notch further, or requires
   restructuring (e.g. decoupling `divide.py`'s split threshold from raw content volume,
   or a real name-count-aware calibration pass), needs the missing report.json data.

## Required reading, in order

1. `docs/design/target-disc.md` — the `ALLDATA.KWI` map layer row (search "envelope").
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md`, "Build record (2026-09-09)"
   section in full — the only surviving record of the actual FAIL, including the levels
   10/12 empty-content finding (a separate, already-diagnosed bug: `selection.json`
   admits `natural=dune` at levels 10/12 but `vocab/bg_type.json` has no mapping for it,
   so those levels spooled zero content and are silently absent from every per-level
   check, envelope included — this is why the envelope FAIL's failing levels are
   8/6/4/2/0, not 10/12).
3. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit 14 — Per-level
   feature selection" section — the calibration notes and self-reported approximation
   risks (levels 4/8 close to the 2.0x ceiling; level 10/12 place-name target
   unreachable).
4. `parser/harness/checks/envelope.py` — `_COUNT_FIELDS`, `_parcel_count`, and the
   `frame_kind_max_bytes` sub-frame-max comparison, to see exactly what's compared and
   how (`[0.5, 2.0]x` on counts, `<=` R's max on sizes).
5. `parser/refdata/selection.json` — the `_calibration_note` field on every level's
   rule, especially levels 4, 8, 10, 12.
6. `parser/kiwiw/divide.py` — `divide_oversize_parcels` (~line 260-330) and
   `_retile_content` (~line 128-174), for how `parcel_count` is actually produced and
   how names are re-tiled into sub-cells on division (one record per divided sub-cell it
   lands in, not duplicated per split — division does not by itself multiply
   `name_count`).
7. `parser/osm_to_parcel_geometry.py` — `_handle_node` (~line 674) and `_handle_way`
   (~line 699), for exactly which admitted features generate `NameRecord`s (place nodes,
   named admitted roads, named admitted background shapes).
8. `docs/provenance.md`'s `output/report.json` / `output/spool/` / `output/ALLDATA.KWI`
   entries, for how to reproduce a full build and report if a future worker decides
   that's warranted.

## Open questions for the next worker to resolve

- Reproduce `output/report.json` (or at minimum re-run `compare_disc.py --checks
  envelope --report ...` against a preserved `output/ALLDATA.KWI` if one still exists at
  dispatch time) to get exact per-level `parcel_count`/`name_count`
  generated/reference/ratio values and the specific sub-frame kind(s) whose max exceeds
  R's, before choosing a fix. Without this, any `selection.json` numeric change is a
  guess, not a calibration.
- Decide whether `parcel_count` should be brought into range by trimming admission
  (`selection.json`), by changing `divide.py`'s split threshold logic, or by treating
  `parcel_count` as not independently controllable and instead reconsidering whether the
  envelope check should apply a `[0.5, 2.0]x` ratio to a derived/structural count like
  `parcel_count` at all (vs. e.g. only bounding it by capacity, the way level-0 road
  counts are already exempted and bounded differently per
  `docs/design/target-disc.md`'s "Profile envelope" row).
- Decide whether `name_count` needs its own calibration pass (cross-checking R's
  per-level name census against the *combination* of admitted highway/background
  classes plus place nodes, not just link/background way-count ratios in isolation), and
  whether unit 14's `selection.json` format can express that without further plumbing
  (e.g. a way to admit a road/background class's geometry without also emitting its name
  record, if that turns out to be the overshoot driver).
- Confirm whether the "several background/name sub-frame maxes exceed R's per-level max"
  failures share the same root cause (more admitted named content -> bigger sub-frames)
  or are a distinct issue (e.g. `divide.py`'s `_shrink_to_fit` only shrinks down to the
  format's hard u16 ceiling, not down to R's smaller observed per-kind max, so a cell
  that needed shrinking can still legitimately exceed R's max even after division).

## Report back

Findings only from this investigation — no numeric fix was implemented and no
calibration change was made, because the actual 2026-09-09 failure magnitudes are not
recoverable from the repo without a full-Australia re-run, and the failing counts
(`parcel_count`, `name_count`) are downstream/derived quantities that `selection.json`
does not control directly (see "Why this is a brief" above). The next worker should
start by reproducing `output/report.json` before attempting any fix.
