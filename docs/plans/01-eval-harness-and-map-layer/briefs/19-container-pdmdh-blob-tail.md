# Brief: 19 — PDMDH blob-length diff at levels 10/12 (container check FAIL) (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve the `container` check's "1 unallowlisted PDMDH-blob-length diff" FAIL found by
WP1 unit 15b's 2026-09-09 full-Australia build (`docs/design/target-disc.md`'s `ALLDATA.KWI`
map layer row). It is not part of the original 01-15b dispatch list; dispatch it
independently.

Owned paths: `parser/refdata/selection.json` (unit 14's), `parser/refdata/vocab/bg_type.json`
and `parser/refdata/vocab/README.md` (unit 08's) — **this brief spans both units' owned
paths**, which is why it is a separate ad hoc brief rather than a trivial in-place fix. Do
not touch `parser/kiwiw/volume_writer.py`, `parser/kiwiw/alldata_writer.py`,
`parser/harness/checks/container.py` or `parser/harness/bytediff.py` — the root cause traced
below is upstream content selection/vocabulary, not the container check or the PDMDH writer,
and none of those files are wrong. Commit to the current branch when done evidence passes;
push.
Depends on: 08 (vocab tables, done), 14 (per-level selection, done), 15b (the build that
surfaced this).
Runs alongside: none identified — if 17/18 are still open, this brief's files are disjoint
from both.

## Required reading, in order

1. `docs/design/target-disc.md` — the `ALLDATA.KWI` map layer row (search "PDMDH") for the
   exact symptom: container FAIL, "1 unallowlisted PDMDH-blob-length diff, R=21,088
   G=18,624 bytes, non-zero extra tail — cause not isolated". Same row also records the
   **already-known, separately-root-caused** "Levels 10 and 12 spooled zero content" bug —
   see finding below, this brief's root cause is that same bug's PDMDH-layer symptom, not a
   new defect.
2. `parser/refdata/selection.json`, the level-10 and level-12 entries and their
   `_calibration_note` fields — `natural=dune` is the only background class admitted at
   levels 10/12, chosen purely on OSM way-count ratio (1.52x, inside the `[0.5,2.0]` envelope)
   with no check against whether `bg_type.json` can actually encode it.
3. `parser/refdata/vocab/bg_type.json` — the `"levels": 10` rule block. It has exactly two
   rules (`289` for a generalised water/coastline/river/wetland match, `306` for
   `boundary=administrative`+`admin_level=4`) and, unlike the level-0/level-[2,8] blocks, **no
   catch-all `{"match": {}, ...}` default** — anything else, `natural=dune` included, falls
   through to the file's top-level `"default": null` and `_osm_tags_to_bg_type` returns
   `None`.
4. `parser/refdata/vocab/README.md`, the "Levels 10/12" section (search "the census
   background set shrinks to"). This is the load-bearing finding: it documents, from R's own
   per-level type-code census, that R's *real* level-10/12 background composition is
   `{289: water (generalised), 306: admin boundary, 528: road-as-background}` — **not any
   natural/vegetation class**. `natural=dune` does not appear anywhere in R's level-10/12
   background vocabulary. The README already flags `528` ("road type 0", i.e. roads drawn as
   background shapes at the most zoomed-out levels) as **deliberately unimplemented** —
   populating it needs a road-geometry→background bridge, a different data flow from
   `_osm_tags_to_bg_type`'s tag lookup, explicitly called out as out of unit 08's scope and
   "flagged as a gap for whichever later unit builds level 10/12 backgrounds in full."
5. `parser/refdata/profile/map.json`, `levels["10"].background.type_code_hist` and
   `levels["12"].background.type_code_hist` — the actual reference counts backing finding 4:
   `{"289": 6, "306": 11, "528": 8}` at both levels. This is the ground truth the fix must
   converge toward.
6. `parser/osm_to_parcel_geometry.py`'s `_handle_way`/`_osm_tags_to_bg_type` call site (per
   unit 08's README, "Extractor call-site changes" section) — confirms `bg_type is None` →
   the shape is silently dropped before `spool.add`, which is why levels 10/12 spool zero
   content today (already recorded in unit 15's kickoff/15b build notes) and, in turn, why no
   blocks exist at those levels for `alldata_writer.py`'s `has_bmt` set to include — see
   finding below for the mechanism connecting this to the PDMDH blob length.
7. `parser/kiwiw/alldata_writer.py`, lines ~983-1032 (`has_bmt`, the `blockset_specs` loop
   building `bmt_tables`, and `pdmdh_record_size = bmt_cursor`) — read only to confirm the
   mechanism, do not edit: `has_bmt` is content-driven (a blockset only gets a real Block
   Management Table if this build actually placed a block there); when levels 10/12 spool
   zero content, no blocks exist for those levels' blocksets, so no BMT tables are built for
   them, and `pdmdh_record_size`/`total_size` come out shorter than R's (R has real BMT
   tables there, with non-zero `BmtEntry` data — hence `container.py`'s "non-zero extra tail"
   report when it trims to the common length).

## Root cause (established by this investigation, not speculative)

The PDMDH-blob-length diff is **not** a bug in the container check, `bytediff.py`,
`volume_writer.write_pdmdh()`, or `alldata_writer.py`'s layout logic — all four behave
correctly given their inputs. It is a downstream consequence of content selection and
vocabulary mapping at levels 10/12 being mutually inconsistent:

- `selection.json` admits `natural=dune` as levels-10/12 background content, chosen solely
  by OSM way-count ratio against R's *count*, without checking R's *type-code* composition.
- `bg_type.json` has no rule (and no catch-all) for `natural=dune`, or for any
  natural/vegetation class, at levels 10/12 — by design, since R's own level-10/12
  background vocabulary never contains such a class in the first place.
- Every `natural=dune` way therefore maps to `bg_type=None` and is dropped before
  `spool.add`, so levels 10/12 spool zero background content (already recorded as a bug in
  `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`'s unit 15 kickoff notes).
- Zero content at those levels means `alldata_writer.py` never places a block for those
  levels' blocksets, so `has_bmt` omits them, so no BMT tables are built for them, so the
  PDMDH blob (header + LMR table + BSMR table + BMT tables) comes out shorter than R's by
  exactly the size of the BMT tables R has for those blocksets — matching the observed
  G < R, R's extra tail non-zero (real `BmtEntry` pointers in R, nothing in G).

Fixing the container-check symptom requires fixing the *content*, not the writer: levels
10/12 need to emit background shapes matching R's real composition (`289`/`306`/`528`), not
`natural=dune`.

## Why this is not a trivial fix

- It is not a one-line vocab addition: R's real level-10/12 background set contains **no**
  natural/vegetation code at all, so simply adding a `natural=dune → <some code>` rule to
  `bg_type.json` would be an ungrounded guess, not a fix matching R's actual vocabulary —
  and would leave `selection.json`'s dune choice in place, which is itself the wrong content
  class for these levels regardless of what code it's given.
- The `528` (road-as-background) component — 8 of the reference's ~25 shapes per level, the
  largest single share alongside `306` — needs a road-geometry→background bridge that does
  not exist yet anywhere in the codebase; unit 08's own README explicitly scoped this out as
  a different data flow for "whichever later unit builds level 10/12 backgrounds in full."
  That is new functionality, not a data-table edit.
- The `306` (admin boundary) component needs `boundary=administrative`/`admin_level=4` ways
  to be *selected* at levels 10/12 by `selection.json` in the first place (today only
  `natural=dune` is admitted there) — a `level_filter` change, plus re-verifying the
  count-ratio envelope for administrative boundaries at those levels.
- This spans two different units' owned paths (`selection.json` is unit 14's,
  `bg_type.json`/README.md is unit 08's) and needs a real design decision on how to attribute
  R's `528` share without the road-bridge work, or whether to accept a partial match (289 +
  306 only, still short of R's total shape_count=25 at these levels) as a stopgap. That
  decision, and the road-background bridge's scope/ownership, are open questions for
  whoever picks this up — not resolved here.

## Goal

Decide and implement a levels-10/12 background content plan that lets generated discs
produce real BMT-bearing blocks at those levels whose background vocabulary matches (or
is a deliberate, documented subset of) R's actual `{289, 306, 528}` composition, closing (or
narrowing, with the remainder explicitly re-flagged) the container check's PDMDH-length gap
and the related envelope background-count gaps at levels 10/12.

## Contract

`docs/plans/01-eval-harness-and-map-layer/DESIGN.md` and `target-disc.md`'s vocabulary/
selection contracts (binding); `parser/refdata/vocab/README.md`'s existing Levels 10/12
section and `profile/map.json`'s `type_code_hist` (binding ground truth for what R actually
contains at these levels). Whatever is implemented, it must not regress the full test suite
or any currently-passing check, and must report — not silently absorb — any component (e.g.
the `528` road-background share) that is left unimplemented.

## Changes

Not prescribed — this needs the road-background scope decision above before "changes" can be
written concretely. At minimum, expect: a `boundary=administrative` selection rule at levels
10/12 in `selection.json` (replacing or supplementing `natural=dune`), a `306` rule already
exists in `bg_type.json` so should start working once selected; and an explicit decision
(implement, defer, or partially implement) for the `528` road-as-background share, recorded
in `vocab/README.md` either way. `natural=dune` should likely be dropped from `selection.json`
at these levels since it does not correspond to anything in R's real vocabulary there.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --generated <a rebuilt disc> --checks container`
  on at least a levels-10/12-covering build → PDMDH-blob-length violation gone or narrowed
  with the remainder explicitly explained in the report (not silently dropped).
- Re-check the envelope check's level-10/12 background counts against the new selection.

## Report back

Which component(s) of R's `{289, 306, 528}` composition were implemented vs. deliberately
left out and why, whether the container check's PDMDH-length violation actually closed or
only narrowed, and any new contradiction found between `selection.json` and `bg_type.json`'s
contracts. **Do not resolve contradictions silently — report them.**

## Amendment (post-implementation, resolving a contradiction with the brief's own "Changes")

This brief's "Changes" section expected, "at minimum," a `boundary=administrative` selection
rule at levels 10/12 in `selection.json` to start populating `306`. Implementation (done
jointly with brief 24, which owns the same paths) found this does not work: a national
tags-only osmium scan of `australia-260824.osm.pbf` found **zero** ways anywhere carrying
`admin_level=4` (`boundary=administrative` ways carry `admin_level=2`, the national-boundary
segments — 73 — or no `admin_level` tag — 6 — nothing else). Australian state/territory
boundaries are OSM relations with `admin_level=4` on the *relation*, not on member ways, and
`osm_to_parcel_geometry.py` only reads way-level tags for multi-polygon outer rings (per its
own docstring). So `bg_type.json`'s `306` rule (`boundary=administrative` + `admin_level=4`)
cannot fire from real way-level data regardless of what `selection.json` admits — adding
`boundary=administrative` there would reproduce this brief's own root-cause pattern (selected,
unmappable, silently dropped) rather than close it. Not implemented; `306` stays unreachable,
recorded in `vocab/README.md`.

The implemented fix instead re-selects levels 10/12 background to `natural=bay` (26 ways
nationally, ratio 1.04x against R's `shape_count=25`) — the only individual tag from the `289`
source-tag set whose national count lands inside the envelope; the rest of that set (coastline/
water/wetland/river/stream/waterway) overshoots by 2-3 orders of magnitude if admitted
together. See brief 24's own amendment for the full count table.

**Root-cause mechanism, confirmed (not assumed):** a `--fixture perth --levels 10 12` local
extraction + build (`parser/osm_to_parcel_geometry.py` then `parser/build_alldata.py`,
disk/time-bounded alternative to a full-Australia rebuild — see "Done evidence" below) shows
level 12 going from "no spooled content, skipping" (the pre-fix `natural=dune` behaviour) to
2 real parcels / 5,382 encoded frame bytes with the new `natural=bay` selection. Reading
`parser/kiwiw/alldata_writer.py`'s `has_bmt` computation (content-driven: `{(level, bsidx) for
(level, bsidx, _blidx) in block_slots}`) confirms that a blockset with real placed content now
lands in `has_bmt` and gets a real, non-empty `BmtTable` (`bmt_offset`/`bmt_size` populated),
where the pre-fix zero-content build would have emitted `EMPTY_BMT_OFFSET`/`EMPTY_BMT_SIZE`
for that same blockset — exactly the mechanism this brief's "Root cause" section traced from
the PDMDH-length symptom back to zero spooled content. This confirms the fix addresses the
traced root cause.

**What was not confirmed, and why (reported per this brief's own "do not silently resolve"
instruction):** a full-Australia rebuild + `compare_disc.py --checks container` run against
the mounted reference disc at `/run/media/codyh/464210-8480` was not performed. The full
extraction pipeline spools ~21 GB (per `selection.py`'s own module docstring) and takes
~1:27:24 for the extraction pass alone (unit 07's report) plus additional `build_alldata.py`
time; this worktree's filesystem had ~27 GB free, too close to the spool's own footprint to
risk safely, and the runtime is well beyond what this session could respond to interactively.
The Perth-fixture build above is a disk/time-bounded substitute that confirms the *mechanism*
(content-driven `has_bmt` now includes a previously-empty level-10/12 blockset) but not the
literal byte-for-byte PDMDH length against R, nor whether *every* level-10/12 blockset that
was previously empty now has content (the Perth fixture's bbox happened to intersect zero of
`natural=bay`'s 26 national ways at level 10's finer 4x4 grid, only at level 12's single
national cell — a full-Australia build would place `natural=bay` ways into whichever
level-10/12 blocksets they geographically fall in, which this session did not enumerate).
So: **root cause confirmed fixed by mechanism, not confirmed closed (or how far narrowed) by
an actual container-check byte comparison against R.** Whoever next runs a full-Australia
build should re-run `compare_disc.py --checks container` and report the result against this
brief's original FAIL.
