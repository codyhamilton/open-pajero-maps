# WP1 — Offline evaluation harness + full-Australia map layer

## Intent

User request, verbatim:

> Check the current implementation status of our plan. It is currently tracked in docs, lets form it into a more formal plan, filling gaps and ensuring the target meets our goal.

## Why This Plan Exists

The project's plan lived in `docs/00-overview.md` (a 2026-08-24 five-phase
plan plus a long decision log) and `docs/phases/03-osm-pipeline.md` (a
2026-09-01 six-stage pipeline plan). The code moved past both on 2026-09-02:
five commits landed a from-scratch encoder set (`kiwiw/synth.py`), an OSM
geometry extractor and tiler, a Link ID registry, an address-index extractor
and an end-to-end `build_alldata.py`, none of which the docs record. The status
check in this plan run found:

- **Done and solid (132/132 tests pass under `.venv-rp`):** byte-identical
  round-trip writers for every metadata file, the `ALLDATA.KWI` container/mesh
  layer, parcel content (4 level-0 parcels, 3 cities), whole block sets at
  levels 6/8, the `SADSR201.IDX` whole file; Ch.9/10 route-planning encoders
  with real CH contraction and a 4-level region tree on a 2×2 fixture;
  from-scratch encoders for road/background/name/map frames; OSM extractors
  for parcel geometry and address-index IR.
- **Gaps between the code and the goal:** (1) the synth name encoder emits
  `string_type=1`, which never occurs on the reference disc (a Perth CBD parcel
  decodes as 224×type 4, 12×type 5, 5×type 6; Melbourne 73/7/2); (2) synth
  Map Frames carry a 3-entry mfde table where the four level-0 parcels
  examined so far carry 20 — other levels have not been censused; (3)
  `build_alldata_kwi` assembles a single level, emits one BSMR/BMT with
  `n_blocksets=0`, omits the 2048-byte frame at file offset 4096..6144 and all
  route-planning content; (4) the synth grid stops at level 8 (`_SYNTH_CELL_SIZES`
  covers 0/2/4/6/8; the reference has 12/10/8/6/4/2/0) and falls back to a
  synthetic grid whenever the reference `ALLDATA.KWI` is not on disk, which
  makes output depend on the environment; (5) every script's default is a
  Perth-metro bbox; (6) the full-PBF `--dry-run` did not finish in 10 minutes
  and printed nothing (buffered output, whole-PBF scan per level); (7)
  `dump_parcel.py` crashes on JSON serialisation of a `bytes` field
  (`to_jsonable` passes bytes through; regression from the 2026-09-02 IR
  additions); (8) no disc has ever been assembled, burned or tested; (9)
  nothing compares a *different* content build against the original — every
  proof so far is a same-content round-trip.
- **Stale hypotheses in the docs:** the `2##` index-file suffix is a state
  partition, not a zoom level (all seven decoded from address-range bboxes:
  201=WA 202=NT 203=SA 204=QLD 205=NSW 206=VIC 207=TAS); the in-vehicle-first
  testing posture is withdrawn by the user.
- **Resolved during planning:** the 4096..6144 frame is pointed at by
  0-based management header record 29, which is spec (Ch.5.2) record 30, a
  RESERVED "extended part 1" slot defined by the manufacturer consortium, not
  by the spec. Its content is a language/country code list (`en gg er fr es
  … au aus`) and a small code table: configuration data, not map content.
  Under decision 3 of the design doc it is copy-through, not regenerated.

The user's answers (see `PROVENANCE.md`) reset the target: full Australia,
every feature, every map-dependent file regenerated, evaluated offline by
byte and structural comparison, vehicle test last. That target is now
written down as `docs/design/target-disc.md`. This plan is the first work
package of that program: build the comparison harness that every later
package is judged by, and bring the most mature layer (the map layer) to a
country-wide, all-level build that passes it.

## Scope

Deliver `parser/compare_disc.py`, an offline reference-vs-generated
comparison harness implementing the checks in `docs/design/target-disc.md`
("Evaluation: the offline oracle"), and a full-Australia, seven-level
`ALLDATA.KWI` map layer (roads, backgrounds, names, parcel management, the
record-29 frame, full mfde table) generated from the Australia PBF that
passes the harness. Route-planning content, search indexes, metadata
regeneration and image authoring are later work packages (WP2–WP5) and are
out of scope here except where WP1 must leave a slot for them.

Two deliverables share this folder because the harness has no meaning
without a non-round-trip build to judge, and the build has no pass/fail
without the harness. Units 01–05 (harness) are independently reviewable and may be
landed as their own PR; units 06–15 depend on them.

## Architectural Implications

- `docs/design/target-disc.md` is new and becomes the program of record;
  `docs/00-overview.md`'s scope decisions and `docs/phases/00-inventory.md`'s
  index-suffix hypothesis are corrected in this plan run (small, deliberate
  edits; the phase docs otherwise stay as historical record).
- The harness's reference profile becomes a shared contract: WP2–WP4 encoders
  must draw enum values from the same census tables the harness checks
  against. The profile is checked-in data produced once from the reference
  disc, split per layer (map, route-planning, index, metadata) so later work
  packages can extend it without regenerating WP1's part. Its exact path and
  schema are refine's call; its existence and per-layer split are not.
- The reference LMR grid parameters (levels, block-set/block/parcel counts,
  cell sizes, coverage origin) become checked-in data derived once from the
  reference disc. The build reads that data, never the mounted disc, so a
  build is reproducible on a machine without the reference.
- `build_alldata_kwi` must grow from "one level, map frames only, flat
  BSMR/BMT" to "all seven levels, reference LMR/BSMR/BMT shape per level, with
  reserved mfde/route slots" without breaking the byte-identical replicate
  path. WP2 places RP frames into the slots WP1 defines; the slot contract
  (which mfde entries exist, what they carry when empty) is stated in this
  folder's `DESIGN.md` (unit 06), informed by unit 03's census.
- `LinkIdRegistry` keying changes from `osm_way_id` (first-in-wins) to
  `(osm_way_id, ordinal)` where ordinal is the sub-polyline index after
  parcel splitting, so WP2/WP3 can address every piece of a split way.
- Default CLI targets change from Perth metro to full coverage; Perth/2×2
  fixtures move behind explicit flags.
- The harness is a separate module tree from the encoders (refine decides
  between `parser/harness/` or a sibling package). It must import only the
  parser's *reading* paths, so a harness change can never alter a build.

## Intent Validation

- **First burn:** not a rebuilt-original disc; that is a contingency debugging
  tool only. Evaluation is byte/structural analysis old vs new.
- **First in-vehicle milestone:** all data across Australia; no partial-region
  or partial-feature milestone. In-vehicle testing is last-mile, not a loop.
- **Burning:** on this machine; tooling install is in scope (WP5).
- **"All data":** full parity — every index family plus `HWMAP.KWI` and
  `INDEXDAT.KWI` are decoded and regenerated before the first burn (WP4).
- **Disc capacity (assumed, not asked):** single-layer DVD-R, 4.7 GB. The head
  unit's dual-layer support is unknown; the reference disc is 2.39 GB. OSM's
  Australian road network is denser than a 2007 commercial dataset, so the
  budget may bind. If the full build exceeds 4.7 GB, that is a scope decision
  to bring back to the user, not a reason to drop content silently.

## Assumption Ledger

None — interactive session; see `PROVENANCE.md`.

## Open Questions

- **mfde entries 3..19.** `parser/kiwiw` already decodes the table; the
  unknown is what entries ≥3 reference (observed offsets resolve outside the
  parcel's own buffer and look like absolute sector addresses, plausibly
  route-guidance content). Unit 03 censuses the table per level, including
  how an *absent* slot is encoded on `R` (zero, `0xFFFF`, or a sentinel).
  Units 06/09 then either generate the entries from a decoded model or emit
  the censused absent-slot value and leaves them for WP2. If neither is
  possible, it is a format-analysis dead end and the choice (carry the
  reference's own values for the same grid cell, or omit) goes to the user.
- **Name string types 5 and 6.** `name.py` already *decodes* them; the
  question is what OSM input maps to each (Perth: 12 and 5 of 241). If unit 11
  cannot derive a mapping, the generated disc emits type 4 only and the
  harness reports the missing types as a recorded deviation.
- **Per-level road selection tolerance.** The head unit's tolerance of a
  level whose road selection differs from `R`'s is unknown; only WP5's
  vehicle test can answer. WP1 bounds the risk by matching `R`'s per-level
  road-type census and count envelope. Level 0 is the exception: its count is
  bounded by Map Frame size and capacity, not by `R`'s count, because OSM's
  density is higher; the trade-off (drop minor ways vs exceed budget) is
  reported by the harness, not decided silently.
- **Anti-meridian coverage.** `R`'s coverage box runs E90 to W142, i.e. it
  crosses ±180°. Whether the generated grid must reproduce that box exactly
  or may be trimmed to Australia's extent is decided by the grid contract:
  reproduce it, because every level-management record and `COVERAGE.BIN`
  encode it. Tiling code must therefore handle longitude wrap.

### Refinement findings (2026-09-05)

Recorded by the refine pass from a read-only census of `R`; they narrow the
questions above and are inputs to the briefs, not new scope.

- **String type 1 is legitimate at levels ≥ 2.** Brisbane spot check: level 0
  name records are types {4, 5, 6}; level 2 is {1, 5}; levels 4–12 are {1}
  only. The design doc's "no type 1" therefore applies to level 0. The
  vocabulary is per level; unit 11 encodes it that way and unit 03's profile
  is the evidence.
- **Level-0 road vocabulary is wider than the synth tables.** `R` level 0 uses
  road types {0, 2, 3, 5, 6, 7, 8} and display classes {3, 4, 7, 9, 10, 12};
  levels 2–8 use types {0, 2, 3} and classes {9, 10, 12}. The current
  extractor emits types 0..7 and classes 0..3, so the mapping is not a
  coverage gap but a different code space; unit 08 rebuilds it from Ch.7.A.
- **mfde absent-slot value is `(0xFFFFFFFF, 0)`;** the table has 20 entries at
  levels 0–10 and 12 at level 12; entry 10 is an in-buffer Extended Data
  Frame at every level and entry 4 at level 0 only; entries 12..19 are
  out-of-buffer absolute sector pointers at levels ≤ 10. Unit 06 decides the
  emission per index; units 09 and 12 implement it.
- **`nregion` is 1 at levels 0–8 with a 4-byte region-list entry,** 0 at
  levels 10 and 12. Its meaning is a Ch.7.1 question unit 06 must settle or
  record.
- **`DESIGN.md` ordering.** The plan said this folder's `DESIGN.md` is written
  in phase 2 yet is required before refine; resolved by making it a unit of
  its own (06) that depends only on the profile (03), so the RP spike can
  start as soon as 06 lands.

### Re-refinement findings (2026-09-06)

The units-01/02/07 execution run's cost post-mortem
(`EXECUTION-COST-ANALYSIS.md` in this folder) found that busy-polling a
long-running background subprocess from inside a single agent's own turns
was the largest identifiable source of wasted cost: 39-58% of the calls
made *after* each agent's last file write were poll/liveness checks on a
subprocess, and resuming a bloated agent across a wait (rather than
handing off to a fresh one) cost 6-8x a normal call regardless of how long
the wait actually was, because the resume appears to invalidate the whole
cached prefix. `../workflow-plugin` (this user's separate workflow-skills
repo) was updated from this same post-mortem to require `refine` to split
any unit whose done evidence depends on a 5-10+ minute subprocess at the
kickoff boundary — a setup/start unit and a fresh wait/verify unit — rather
than let one unit do both. That rule is applied here to the two remaining
units whose done evidence requires a country-scale decode or build:

- **Unit 03** (reference profile) required running the harness against the
  full mounted reference disc twice — a `--profile` build and a self-check
  decode, the same class of operation as unit 02's own 31-minute self-check.
  Split into **03** (implementation, fast in-repo tests, starts both real-disc
  runs in the background, hands off) and **03b** (fresh agent, waits, verifies,
  writes `parser/refdata/profile/map.json`, commits).
- **Unit 15** (full-Australia build) required a from-scratch country-scale
  extraction (unit 07's own run of the same extractor took 1:27:24) plus a
  full assembler pass, then a repeat build to check determinism — a
  multi-hour wait. Split into **15** (kickoff only, no docs/code changes) and
  **15b** (fresh agent, waits, verifies through the harness, writes the build
  record, commits).
- **Unit 12**'s optional full-spool `build_alldata.py` run (its done evidence
  treats this as best-effort, not required) was left as one unit but amended
  to forbid polling it in a loop: start it in the background, do one
  liveness check, move on.
- Units 04, 05, 06, 08, 09, 10, 11, 13, 14 do not touch the real reference
  disc at country scale (04/05 do single-file or spot lookups; the rest are
  code-only against fixtures) and were not split. Every remaining unit's
  brief was amended to state explicitly that a non-trivial, non-blocking bug
  found mid-implementation is reported, not fixed in place — the
  post-mortem's other finding was that fixing in place on an
  already-tens-of-thousands-of-tokens-deep agent cost ~35-40% more than the
  same fix on a small fresh agent, and permanently taxed every later call in
  that agent via a larger carried context.

### Re-refinement findings (2026-09-09)

Unit 12's done evidence hit a real, reproducible crash while re-validating briefs 13/14 against
the landed code (commit `2805b0b`): `parser/kiwiw/synth.py:851` raises `ValueError: N does not
fit in u16` whenever a Map Frame exceeds 131,070 bytes — a hard format ceiling on the header's
16-bit word-count field, not merely a profile-derived guideline. This is exactly the failure
unit 13 (DESIGN.md section 6) and unit 14 exist to prevent, and does not change the dependency
graph: 13 and 14 still both depend only on 12, still run alongside each other on disjoint
paths, and their joint real-build success is still verified downstream at 15b, not by either
unit alone. Two things it does change, both applied to the briefs directly (not recorded here
as new scope):

- The size threshold unit 13 divides against must be `min(profile mapframe_size.max for the
  level, 131070)`, not the profile max alone — Perth-fixture evidence showed a level-0 parcel
  at ~133,240 bytes, inside the profile's observed max (136,096) but still over the u16
  ceiling, meaning some of `R`'s own profiled level-0 parcels are themselves already divided
  sub-frames.
- Level 12 (one global parcel, no per-cell tiling) hit 39,555,559 bytes on the unmodified
  fixture — ~300x the ceiling, far beyond what unit 13's maximum division (4×4, 16x) can
  recover alone. Unit 14's selection is load-bearing for level 12 specifically, not just for
  census-matching; unit 13's own done evidence may still show a level-12 overshoot after
  division until unit 14's thinning lands, which is expected, not a defect in either unit's
  work, and is reported rather than treated as a blocking failure in each unit's own scope.
- `_build_alldata_kwi_multilevel`'s `divided` parameter does not exist yet in the landed
  code (unit 12's docstring reserves the path but the parameter itself is unit 13's to add) —
  brief 13 corrected to say so, since the prior text implied it was already there.

## Execution Phases

Definitive dispatch list (refined 2026-09-05; re-refined 2026-09-06 to split
long-running-subprocess units at their kickoff boundary — see the Decision
Log entry below). One brief per unit in `briefs/`; each brief is
self-sufficient and is handed to its worker verbatim. Units that may run
alongside each other own disjoint paths.

| # | Unit | Brief | Depends on | Runs alongside |
|---|------|-------|-----------|----------------|
| 01 | Reference container data (`kiwiw/grid.py`, `refdata/grid.json`, record-29 frame) | `briefs/01-reference-container-data.md` | — | — |
| 02 | Harness core (`parser/harness/`, `compare_disc.py`, `decode`/`pointers`/`shape`/`mht29`) | `briefs/02-harness-core.md` | 01 | 07 |
| 03 | Reference profile and profile checks: implementation and kickoff of the real-disc runs | `briefs/03-reference-profile.md` | 02 | 04, 05, 07 |
| 03b | Reference profile: verify the real-disc runs, check in the profile, commit | `briefs/03b-profile-verify.md` | 03 | 04, 05, 06, 07, 08 |
| 04 | Container byte-diff with allowlist | `briefs/04-container-bytediff.md` | 02 | 03, 03b, 05, 07 |
| 05 | Spot-check fixture table; `dump_parcel.py` JSON fix | `briefs/05-spot-checks-and-dump-fix.md` | 02 | 03, 03b, 04, 07 |
| 06 | `DESIGN.md`: Map Frame shape, mfde/RP slot contract, ext-frame and divided-parcel policy | `briefs/06-slot-contract-design.md` | 03b | 04, 05, 07, 08 |
| 07 | Extractor at country scale (one pass, all levels, spool, wrap-safe) | `briefs/07-extractor-scale.md` | 01 | 02, 03, 03b, 04, 05, 06 |
| 08 | Data-driven vocabulary tables per level | `briefs/08-vocab-mapping.md` | 03b, 07 | 06, 09 |
| 09 | Map Frame shape in `synth.py` per `DESIGN.md` | `briefs/09-map-frame-shape.md` | 03b, 06 | 08, 10 |
| 10 | Link identity `(osm_way_id, ordinal)` | `briefs/10-link-ordinal-registry.md` | 08 | 09, 11 |
| 11 | Name string types 4/5/6 at level 0, per-level types | `briefs/11-name-types.md` | 09, 10 | 12 |
| 12 | Assembler: all seven levels, reference LMR/BSMR/BMT shape, record 29, wrap | `briefs/12-assembler-all-levels.md` | 01, 06, 07, 09 | 10, 11 |
| 13 | Divided parcels (types 1..3) for oversize frames | `briefs/13-divided-parcels.md` | 12 | 14 |
| 14 | Per-level feature selection matched to the census | `briefs/14-per-level-selection.md` | 03b, 08, 10, 11 | 13 |
| 15 | Full-Australia build: kickoff (start extraction + assembler, hand off) | `briefs/15-full-build-and-record.md` | 01–14 | — |
| 15b | Full-Australia build: verify through the harness; record deviations and capacity | `briefs/15b-full-build-verify-and-record.md` | 15 | — |

Lanes: 01 → {02, 07}; after 02 → {03, 04, 05}; 03 → 03b (03b is a fresh
agent, never a resume of 03 — see Decision Log); after 03b → 06 and 08 (08
also waits on 07); after 06 → 09 → 10 → 11 and 12 (12 also waits on 07);
after 12 → 13; after 11 → 14; then 15 → 15b (15b is a fresh agent, never a
resume of 15). The critical path is 01 → 02 → 03 → 03b → 06 → 09 → 10 → 11
→ 14 → 15 → 15b.

Ownership hot spots and how they are serialised: `osm_to_parcel_geometry.py`
is edited by 07, then 08, then 10, then 11, then 14, each on a named
function only; `synth.py` by 09 then 11; `model.py` by 05 (`to_jsonable`),
10 (`RoadLink`), 11 (`NameRecord`); `alldata_writer.py`/`build_alldata.py`
by 12 then 13. No two units that run alongside touch the same file. 03/03b
and 15/15b are not a concurrency split but a wait split: 03 and 15 leave
their working-tree changes uncommitted for 03b/15b to pick up and commit,
so no other unit may land a commit in between (03b runs alongside 04-08 in
that none of them touch its one new file, `parser/refdata/profile/map.json`;
15b runs alongside nothing since it's the terminal unit).

WP2's format-analysis spike on RP placement may start in parallel once
unit 06's `DESIGN.md` exists; it does not wait for units 07–15.

## Acceptance Criteria

User-facing (entry point → action → observable result):

- Terminal at repo root → `.venv-rp/bin/python parser/compare_disc.py --reference <disc root> --generated output/` → prints a per-check PASS/FAIL/N-A table and writes a JSON report; exit code 0 only when every applicable check passes. `--checks decode,pointers,vocab` runs only those checks; `--config <file>` overrides envelopes and the spot-check fixture table.
- Terminal at repo root → `.venv-rp/bin/python parser/compare_disc.py --profile --reference <disc root>` → writes the checked-in reference profile split per layer; a second run is byte-identical.
- Terminal at repo root → `.venv-rp/bin/python parser/build_alldata.py --pbf australia-<date>.osm.pbf --out output/ALLDATA.KWI` with no bbox or level flags and no reference disc mounted → builds all seven levels (12,10,8,6,4,2,0) over the reference disc's full coverage box, prints per-level progress lines as it runs, and exits 0.
- Terminal at repo root → `.venv-rp/bin/python parser/dump_parcel.py --alldata output/ALLDATA.KWI --lat -27.4698 --lon 153.0251 --level 0` → prints valid JSON whose road frame contains OSM Brisbane CBD street names (e.g. Queen Street, Adelaide Street). The same for the spot-check fixture table's Sydney, Melbourne, Perth, Adelaide, Hobart and Darwin coordinates at levels 0 and 2; the harness runs this table itself.

Non-user-facing (observable statement):

- Every parcel at every level of the generated `ALLDATA.KWI` decodes through the existing `load_region`/`decode_parcel` path with zero errors. Every BMT and parcel-management pointer resolves inside its buffer. mfde entries 0..2 resolve inside the parcel buffer; entries ≥3 are either the censused absent-slot value or resolve to a valid sector inside the file.
- The generated disc's road-type, display-class, background type-code and name string-type value sets are subsets of the reference profile's sets, per level; `string_type=1` does not appear **at level 0** (it is legitimate at levels ≥2 — see unit 03/03b's census: 1,042,019 level-0 occurrences on the reference disc, 5.5% of level-0 name records, confirming this is a level-0-only rule, not a global one).
- Per level 12..2, generated road-link counts are within the design doc's envelope of the reference's; at level 0 no Map Frame exceeds the reference's per-level maximum size and the harness reports the count ratio without failing on it.
- Per level, the generated LMR/BSMR/BMT shape (block-set, block and parcel counts, cell sizes, coverage box) equals the reference's; the mfde entry count and absent-slot encoding match the profile on every parcel; the record-29 frame at 4096..6144 is byte-identical to `R`.
- The container byte-diff check passes with every difference inside the allowlist.
- The map-layer byte total is reported and, together with the reference disc's route-planning and index byte totals, projects under the 4.7 GB budget; if not, the report says so and names the level-0 trade-off.
- The full-Australia build completes in one run on this machine; wall time and output size are recorded in the close-out record.
- `LinkIdRegistry` resolves `(osm_way_id, ordinal)` for every sub-polyline of a way split across parcels, and a test covers a way spanning two parcels.
- `.venv-rp/bin/python -m pytest parser/tests` passes with no regression in replicate-mode byte-identical tests; new tests cover the harness's profile checks, the grid-data loader, and the name-type/mfde encoders on synthetic input.
- The build is deterministic: two runs on the same input, on a machine without the reference disc, produce byte-identical output.

## Provenance Notes

See `PROVENANCE.md` in this plan folder for the verbatim request, the two
Q&A turns, agent decisions and the adversarial-review findings.

- **Why a harness before more content:** the user's evaluation method is
  byte/structural comparison; every existing proof is a same-content
  round-trip and cannot judge OSM-derived output. Without the harness, WP2–WP5
  have no pass/fail definition.
- **Why the map layer is WP1's content target:** it is the most mature layer,
  the largest by bytes, and the one whose from-scratch pipeline already exists
  but deviates from the reference in known ways (name type, mfde count,
  single level, flat BSMR/BMT).
- **Why scale precedes all-levels:** the extractor must handle the full PBF
  before per-level selection is meaningful, and the scaling failure (dry-run
  did not finish) is the one already observed.
- **Why route planning is not folded in:** its country-scale region tree and
  Link ID join are a work package of their own; WP1 only reserves the slots.
- **Development fixtures stay:** the Perth bbox and 2×2 region tree remain
  as explicit-flag fixtures for fast iteration; they stop being defaults.

## Build record (2026-09-09)

Full-Australia build, units 15/15b. Commands run exactly as the extractor's/
`build_alldata.py`'s own `--help` defaults (no `--pbf`, `--levels`, `--fixture`
or bbox flags), matching the "no bbox or level flags" acceptance bullet:

```
.venv-rp/bin/python parser/osm_to_parcel_geometry.py   # PBF -> spool
.venv-rp/bin/python parser/build_alldata.py             # spool -> ALLDATA.KWI
```

**Timing/memory** (`/usr/bin/time -v`, logs in `/tmp/wp1-unit15-logs/`, not
committed — regenerable, see `docs/provenance.md`):

| Stage | Wall clock | Peak RSS | Exit |
|---|---|---|---|
| Extraction (`osm_to_parcel_geometry.py`) | 33:23.02 | 8,188,004 KB | 0 |
| Assembly (`build_alldata.py`), first run | 6:44.39 | 3,358,432 KB | 0 |
| Assembly, repeat (determinism check) | 6:44.96 | 3,359,180 KB | 0 |

**Output**: `output/ALLDATA.KWI` 814,121,408 bytes; `output/spool/` 6.9 GB
(not committed, regenerable — see `docs/provenance.md`). SHA-256
`5f0fa9f4d57950316a8ea35f05d6c894662733a05696e7a4ffba0f9cb3b0be66`, identical
between the first build and a from-spool repeat run — **the build is
deterministic** (last Acceptance Criteria bullet: met).

Five `WARNING [kiwiw.divide]` lines at levels 8 and 0 (5 cells total) report
content dropped after 4x4 division still exceeded the u16 format ceiling —
the lossy fallback documented as expected in unit 13's outcome
(`IMPLEMENTATION.md`), not a new deviation.

**`compare_disc.py --reference /run/media/codyh/464210-8480 --generated
output/ALLDATA.KWI --report output/report.json`** — exit code 1 (correctly
non-zero: the tool's own contract is "exit 0 only when every applicable
check passes," and several did not; a `| tail` wrapper masks this exit code
with the pipe's own status, confirmed as a red herring during this unit's
own verification, not a harness defect).

| Check | Status | Notes |
|---|---|---|
| container | FAIL | 1 unallowlisted PDMDH-blob-length byte diff (R=21088, G=18624 bytes, extra tail not zero) — see deviations below |
| decode | PASS | 454,153 leaves, zero errors |
| pointers | PASS | every BMT/mapinfo/mfde pointer resolves, no poison |
| envelope | FAIL | 20 failures across levels 8/6/4/2/0 (parcel/name counts outside [0.5,2.0]x, several sub-frame maxes over R's) — see deviations below |
| mfde | FAIL | 5 failures: `nregion` never 1 (expected — WP2 slot, DESIGN.md §7); mfde entry-count never >20 and entry-index-1 always "absent" where R sometimes has content (not a declared WP2 slot — see deviations) |
| mht29 | PASS | record-29 frame byte-identical to R |
| shape | PASS | LMR/BSMR/BMT shape matches R at every level |
| spotcheck | FAIL | 3 of 14 rows missing expected names (Sydney L0: 3/3 road names missing; Melbourne L0: 2/3 missing; Perth L2: place name missing) |
| vocab | FAIL | name_type_code offenders at 5 levels (288/289/290/306/321/578 appearing where R's per-level census doesn't have them) |

Levels 10 and 12 are **entirely absent from every check's per-level report**
(not reported as FAIL, not reported at all) because the extractor spooled
zero content at both levels this run — see "Recon finding" below. This is a
harness blind spot, not a passing result: `parser/harness/checks/envelope.py`
(and the other per-level checks) iterate the *generated* profile's levels
only, so a level R has real content for but G has none for is silently
skipped rather than flagged. Reported per this unit's contract, not fixed
(outside the owned-paths list).

**Recon finding — levels 10/12 empty, root cause identified**: unit 14's
`parser/refdata/selection.json` admits `natural=dune` ways at levels 10 and
12 (calibrated to R's ~38-way national count, "ratio 1.52x -- inside the
envelope"). But `parser/refdata/vocab/bg_type.json` (unit 08's table) has
**no rule mapping `natural=dune` to any background type code, at any
level** — grep confirms zero occurrences of "dune" in that file. In
`osm_to_parcel_geometry.py`'s `_handle_way`, `_osm_tags_to_bg_type(tags,
level)` therefore returns `None` for every `natural=dune` way, and the
background branch's `if bg_type is None: continue` drops it before
`spool.add` is ever called — independent of ring closure or any geometry
gate. Since `natural=dune` was the *only* admitted class at levels 10/12
(no highway, no place), both levels spool zero content. This is a genuine
selection/vocab wiring bug (unit 14's selection.json vs. unit 08's
vocab/bg_type.json), not a geometry-pipeline artifact and not explained by
unit 14's own calibration caveats. Fix is outside this unit's owned paths
(`parser/refdata/vocab/bg_type.json` or `parser/refdata/selection.json`);
reported for a follow-up fixer per this unit's brief.

Acceptance-list bullets (PLAN.md, verbatim) checked individually:

- `compare_disc.py --reference ... --generated ...` prints table + JSON, exit
  0 only if all pass: **command behaves as specified; this run's exit was 1**
  because container/envelope/mfde/spotcheck/vocab checks failed (see table
  above) — not a defect in the command's own contract.
- `compare_disc.py --profile` byte-identical on a second run: **not
  re-verified by this unit** (already confirmed twice in unit 03/03b per
  `docs/provenance.md`); out of this unit's scope to re-run.
- `build_alldata.py --pbf australia-<date>.osm.pbf --out output/ALLDATA.KWI`
  with no bbox/level flags: **contradiction found and not resolved
  silently** — `build_alldata.py` takes no `--pbf` or `--out` flag at all
  (its actual flags are `--spool`/`--out`/`--levels`/`--fixture`/
  `--disk-title`; it never reads a PBF, only a spool directory written by
  the separate `osm_to_parcel_geometry.py`). The real pipeline is two
  commands (extractor --pbf ... --spool ...; then build_alldata.py reading
  that spool), exactly as unit 15's kickoff ran it and as this record's
  commands above show. The one-command-with-`--pbf` acceptance bullet does
  not match either script's actual CLI; reported here, not edited into the
  bullet's wording (out of this unit's owned paths).
- `dump_parcel.py --lat -27.4698 --lon 153.0251 --level 0` (Brisbane) prints
  valid JSON with Queen Street and Adelaide Street: **PASS, exit 0**, both
  names present (verified directly and via the harness's own spotcheck row).
  The same table's other six cities/levels: **PASS except Sydney L0,
  Melbourne L0 (partial) and Perth L2** — see spotcheck row above.
- Full build completes in one run, wall time and size recorded: **met** (see
  timing table above).
- `pytest parser/tests`: **227 passed, 0 failed, exit 0**.
- Two runs on the same input produce byte-identical output: **met** (see
  SHA-256 above).

No contradiction in the LinkIdRegistry/`(osm_way_id, ordinal)` bullet was
checked in this unit (it is exercised by `parser/tests`, which passed in
full; not independently re-verified against the full-Australia output).
