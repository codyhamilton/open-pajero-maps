# Map-layer parity remediation

## Intent

User request, verbatim:

> research each deviation and explain causes, not just the measured deviation. Further, conduct an analysis of what else is different between reference and target. In principle, we want to see the only deviations be natural - meaning they are derived from the source data, not out of the way we have processed it. Even so, we should look critically at structural differences in source data and how that might lead to problems in the generated disc. Structural differences in the source are worth calling out and may require compensation. So our analysis needs to understand root causes

> produce a design  which captures these changes

> produce using the /workflow:design

(Source analysis: `FINDINGS.md`. It carries the evidence, numbers and findings F1–F12 this design cites.)

## Problem

WP1 (`docs/plans/01-eval-harness-and-map-layer.md`) was declared functionally complete pending acceptance of nine "declared deviations". A root-cause review (2026-09-20) decoded R and the current G directly and found that most of those deviations are **processing artifacts, not natural source differences**, and that the harness passed several structural mismatches because its checks are subset-based, length-only or loosened. The generated map layer differs from R in ways that could make the disc wrong or unusable in the vehicle, and the project's rule is that the vehicle test is last-mile, so these must be found and fixed offline. The differences:

- G's parcel-local coordinates span 0..32767; R's span 0..4096 (L2–L8) and 0..16384 (sparse L0) (hypothesis, strong; G may be 8× too spread).
- G writes zeros in Map Frame header words where R writes real values (`dipid`, words 7, 9–11, and others), and writes word 0 as `total_size//2` where R writes the header size.
- The size cap is applied to the whole frame at the u16 ceiling; the real u16 limit is per sub-frame.
- OSM road classes are mapped to the wrong R road types and display classes; geometry is not generalised (2.5× R's urban vertex density, every vertex a 6-byte node); L0 backgrounds admit buildings; no ocean polygons or sea names; names miss R's type-4/1 records, casing, coverage and priority values; link flags and neighbour pointers are unset.

Until these are fixed or genuinely shown natural, WP2–WP5 build on a map layer that does not match R structurally.

## Solution Shape

After this change the generated map layer is *R-native* in every structural respect the harness and the spec can establish: the same coordinate model, header words, road/display vocabulary, generalisation density, background and name structure and link/neighbour fields as R, populated from OSM. Every remaining difference from R is one of a short, evidence-backed list of **natural deviations** (source data lacks it, or the extract excludes it), and each is stated with its cause. The harness can now detect the differences that used to pass (coverage-direction vocabulary, header words, coordinate scale, BMT presence, sub-frame advisories), and its report is bound to the exact `ALLDATA.KWI` it evaluated.

The work is one linear-then-fan-out sequence: establish the truth and harden the oracle, settle the coordinate model (a hard gate), apply the native encoding, then bring content (geometry, vocabulary, backgrounds/sea, names, flags) to R's shape, then verify and close the deviation ledger. Every phase's approach is known: where the correct approach is not yet established (e.g. the coordinate model), the phase's first unit is research that resolves it to a single canonical answer; the design is not a try-multiple-and-iterate one.

### Domain: Native encoding model

- Owns: the parcel-local coordinate range per (level, parcel class); the Map Frame header word generator; the per-sub-frame size cap.
- Contract:
  - `parser/refdata/profile/coord_scale.json`: for each level and parcel class, the R-observed coordinate maximum and the deterministic rule assigning a parcel to a class; plus the mapping from Map Frame header words 6, 7, 9, 10, 11 (and word 0 = header size) to (level, parcel class, division state). Generated from R, checked in, never read from the mounted disc at build time (Grid contract in `docs/design/target-disc.md`).
  - Encoders take the coordinate range from this data, not a constant: `coordconv.range_for(level, parcel_class)` replaces `COORD_RANGE`; the C encoder receives it as a parameter, not its own constant.
  - Header words are never zero-filled: each is generated from the model or proven zero in R for that class.
  - Size cap: every sub-frame (road, background, name, …) <= 131,070 bytes (mfde u16 word count). Whole-frame size is not capped. R's per-kind maxima are reported; any sub-frame above 2× R's per-kind maximum is an **advisory** (never a build failure), and a persisting advisory becomes a ledger entry with its cause. Where nothing exceeds R's maxima, output bytes are unchanged by the cap change.
- The schema is keyed by (level, parcel class, division state) and includes urban L0 (4096) and divided sub-parcels (2048/4096). The parcel-class rule must be content-independent (a function of grid position/level/division), so Phase 5 generalisation cannot invalidate it. `range_for(level, parcel_class, division_state) -> int`; the C encoder receives the value as an argument per call.
- Header-word exemption: `n_intersections`, `route_planning_level`, `n_additional_data`, ext-frame slots and `nregion` are WP2-owned. They are the only words allowed to differ from the model in Phase 4, and are listed with R's census values in `coord_scale.json`'s header section.
- Non-goals: populating the WP2-owned words above.

### Domain: Content generalisation and selection

- Owns: what OSM content reaches each level and in what geometric form (thinning, division), the road/display-class and background-type vocabularies, and the ocean/sea construction.
- Contract:
  - `parser/refdata/generalise.json`: per-level snap grid, Douglas-Peucker tolerance (in native grid pixels), and node-vs-intermediate-point rule; calibrated so per-level vertices-per-link and per-km fall within a stated band of R's (band recorded in `harness.json`).
  - `parser/refdata/vocab/road_type.json` / `display_class.json` derived from name-matched R↔OSM cells so a road's semantic class equals R's for the same road; unmapped tags drop, never fall through to a catch-all.
  - `parser/refdata/selection.json` admits only background classes R draws (from the R background census); buildings and sub-pixel polygons (after quantisation) are dropped by rule; `background_all` and the L0/L2 catch-all `288` rule are removed.
  - Ocean: land polygons derived from `natural=coastline`, complemented inside R's populated rectangle, emitted as background type 289 through the existing background path.
  - Division prefers R's 2×2 before deeper escalation, and every divided leaf carries a correct `dipid`.
- Ocean construction also covers `place=sea|ocean|bay|strait` admission, reserves (321) and rivers/lakes (291), per F7.
- Numeric bands (vertex density, class distribution, flag prevalence, distance tolerance, name mix) are fixed **before any tuning**: Phase 1 delivers a bands section in `harness.json` with a stated derivation rule (a tolerance around R's per-level statistic, stated as a fraction) and a recorded review. Bands are never adjusted after seeing G.
- Non-goals: content OSM cannot supply (PNG, Indonesia and NZ land, absent from `australia-260824.osm.pbf`) — a declared natural deviation; per-tag frequency as a vocabulary basis.

### Domain: Names and link fields

- Owns: name record structure and text form; link flag and node bit population; mfde neighbour entries 12–19.
- Contract:
  - Every populated cell carries a region or ocean name; type 4 `A=<suburb>,<REGION>` and `1=<ROAD>` records, type 5 per-segment labels, type 1 route shields from OSM `ref`.
  - Text is ASCII-folded and uppercase (user decision); `priority` and `display_scale_flag` assigned by name class from R's census, always drawn from R's observed values.
  - Link flags (`link_id_flag`, `selected_link_flag`, `route_planning_tag`, toll/bridge/tunnel/planned bits) populated from OSM tags or from R's per-class census rule; a flag whose meaning cannot be established takes R's value for the matching class and is recorded as unverified.
  - mfde 12–19 carry adjacent-parcel pointers computed from the WP1 grid, with R-style entry counts including divided-neighbour records (spec Ch.7.1.1 item 17 assigns these to WP1; `DESIGN.md` of plan 01 §7/§8 "contested" is resolved accordingly).
- Before name work, the `name_writer` encoding and search chain are audited against the schema (F8); the L0 name_count envelope rule stays as-is. Name attribution method: on a stride sample of R strings, the fraction with no OSM counterpart is the natural-shortfall figure; the remainder is a defect.
- Flag table: `docs/schema/flags.md` lists every link flag and node bit with its R census, the OSM source (if any), its status (*known* / *unknown*), and the value G writes. An unknown flag is never accepted silently: it takes R's per-class value, is recorded in the table and the ledger as a documented deviation with a stated test to run later, and is never left undocumented.
- Ledger classes: *natural* (source lacks it) and *documented-unknown* (flag-table entry with a pending test). Nothing else is admissible, and every entry states its cause.
- Non-goals: one-way and turn restrictions (WP2; R's map-layer node oneway is 0 on all 29.9M nodes); the head unit's use of `A=`/`1=` tags for search (unknown; emitted regardless).

### Domain: Verification and deviation ledger

- Owns: `parser/harness`, `parser/refdata/harness.json`, and the deviation ledger in `docs/design/target-disc.md`.
- Contract:
  - `compare_disc.py` report carries the sha256 and mtime of the `ALLDATA.KWI` it evaluated and refuses to compare when they differ from `output/manifest.json`.
  - New checks: `header_words`, `coord_scale`, `road_vocab` (distribution and named-arterial spot checks), `name_coverage`.
  - Strengthened checks: `mfde`/`vocab` gain a coverage direction (G must use a stated share of R's values by R frequency); `shape` and `container` compare BMT tables by (level, blockset) key and check DSA ordering; `pointers` requires targets to decode as Map Frames; `spotcheck` uses whole-word equality and gains a Grenfell-in-northern-cell row; envelope sub-frame rows become "<=131,070 with 2×-R advisory".
  - Ledger: every difference from R that remains after the final build is listed with its source-data cause; anything caused by processing is a failure, not an entry.
- Non-goals: head-unit behaviour (no in-vehicle test before the full-Australia burn); the WP2+ layers.

## Architectural Implications

- **Stable docs.** `docs/schema/` is the authoritative, validated definition of the disc structure (status per row: verified / observed / spec-only / assumed / unknown); the unknowns (WP2/WP3 spikes: ext frames `0xAF100100`/`0300`, turn-restriction yield, POI vendor category codes, suburb hierarchy, undecoded WP4 families) are its `UNKNOWNS.md` index, so they are not re-derived. `docs/OVERVIEW.md` and `docs/ARCHITECTURE.md` are rewritten by the docs consolidation. `docs/design/target-disc.md` is the working program of record. `docs/design/target-disc.md` is updated in Phase 10 (deviation ledger, header word 0, mfde 12–19 ownership, size-limit semantics).
- **Corrections to recorded assumptions.** `docs/plans/01-…/DESIGN.md` line 33 says Map Frame word 0 "matches buffer size"; R shows it is the header size. Its §7/§8 treat mfde 12–19 as contested/WP2; the spec assigns them to WP1. Brief 34's premise ("the only limit is the u16 whole-frame size") is superseded by the per-sub-frame cap.
- **Plan 01.** Its nine "proposed declared deviations" are withdrawn; the ledger is regenerated in Phase 10 and plan 01 is closed out afterwards, not before.
- **Rebuild cost.** The coordinate range is baked into the spool at extraction (`spool.py` stores pixel ints; the extractor calls `latlon_to_xy` at extraction time; `_cenc.c` has its own copy of the range), so both encoders must derive pixels from lat/lon (the spool stores lat/lon, and encoders already recompute pixels when x/y is unset), which lets Phase 3 reuse the existing spool without re-extraction or re-quantise. Extraction is still needed for Phase 8 (names live in the spool); its time is measured in Phase 1. Assembly is ~32 s. Worktree copies under `.claude/worktrees/` are stale and must not be edited.
- **Determinism.** Every phase preserves byte-for-byte reproducibility for the same PBF and config (Determinism contract, `target-disc.md`).
- **Sequencing.** WP2 route-planning work assumes the native coordinate model and header words; it should not start before Phase 4 closes.

## Decisions

- **Scope (user, 2026-09-20):** this design covers WP1 map-layer remediation only. The WP2/WP3 spikes are documented as unknowns in `docs/schema/`, not designed here.
- **Coordinate-range gate (user):** hard stop. If the offline test does not confirm R's range model, the design is bounced for re-analysis; nothing downstream proceeds on the current constant.
- **Names (user):** fold to ASCII uppercase.
- **Approach flags (user):** all phases are `known`. There is one canonical approach in each case, whether or not it is known today; where information is missing, the phase begins with research that resolves it. No divergent-candidate builds.
- **Principle (user, Intent):** only natural deviations (derived from source data) are accepted; processing artifacts are defects.

## Assumption Ledger

Each assumption names the phase that tests it and what happens if it is false.

- **Coordinate range 4096/16384 is the true full-cell range.** Tested in Phase 2. If false: hard stop, re-analyse (user decision).
- **Coastline lines in the extract close into land polygons** (extract-edge breaks, islands). Tested in Phase 6 by the no-land-labelled-as-sea audit. If false: ocean construction is re-analysed before Phase 6 closes.
- **Name-matched R↔OSM cells are a valid basis for road vocabulary.** Tested in Phase 7 on held-out named arterials. If false: research a different basis before mapping.
- **R's word 0 rule holds beyond the 95.5% (897/939) of sampled leaves where it equals the first data-slot offset.** Phase 2 explains the 42 exceptions before the gate closes; the criterion is "matches R's rule or the exception is explained".
- **Copying R's value for a flag whose meaning is unknown is harmless to the head unit.** Not accepted blindly (user decision): each such flag is a flag-table entry and a ledger deviation with a later test; none is undocumented.
- **Country-scale re-extraction is affordable** (needed for Phase 8). Phase 1 measures extraction wall time.

## Open Questions

- Foreign-land absence is accepted as natural (user). The 102 G-only L0 cells outside R's populated rectangle (13 BMT tables) are unexplained until Phase 6 lists them with lat/lon and content; each is then natural (source land outside R's rectangle) or a defect.
- Whether the head unit requires `A=`/`1=` name tags or reads header word 0 / `dipid` — unknowable offline; treated as risk, mitigated by R-equivalence.
- Extraction wall time at country scale (undocumented); affects how many full re-extractions Phases 3–5 can afford.

## Phases

The count and order are fixed at sign-off. Phases 6 and 7 both edit `selection.json` and are sequenced, not parallel. Phases 8 and 9 touch the same encoder and check files and are sequential (8 then 9). Phase 3 (coordinates) and Phase 4 (header words, cap) are separate so failures stay isolated.

### Phase 1 — Baseline truth and non-invasive harness hardening

- Outcome: running `parser/compare_disc.py` against the current `output/ALLDATA.KWI` produces a report whose recorded sha256 equals `output/manifest.json`'s ALLDATA sha256; running it against a different file refuses to compare and says why. The strengthened `mfde`, `vocab`, `shape`, `container`, `pointers` and `spotcheck` checks (F12 items that need no new census) run on the current G and report the differences already known (G-only BMT tables, non-monotonic BMT DSAs, poorer-than-R vocabulary coverage, Grenfell row) as FAIL or advisory as designed, with the expectation list recorded.
- Surfaces: `parser/compare_disc.py`, `parser/harness/{report,context,registry}.py`, `parser/harness/checks/{mfde,vocab,shape,container,decode,spotcheck}.py`, `parser/refdata/harness.json`, `parser/refdata/spot_checks.json`, `parser/tests/test_harness_*.py`.
- Also delivers: the numeric bands section in `harness.json` (a stated fractional tolerance around R's per-level statistic, reviewed, never adjusted after seeing G) used by every later "within band" outcome; a measured extraction wall time (for Phase 8); a vertices-per-km and road-length census of R (needed by Phase 5's density band); a recorded review of the bands before any run on G; and `docs/schema/` rows (status `unknown`) holding every WP2–WP5 unknown from the source analysis with a first test for each. Phase 1 succeeds when every FAIL the strengthened checks report on the current G is on the recorded expectation list.
- Approach: known
- Depends on: nothing
- Units:

| Unit | Brief | Depends on | May run alongside |
|---|---|---|---|
| 1-01 report binding | `briefs/1-01-report-binding.md` | nothing | 1-02, 1-05, 1-06, 1-07, 1-08 |
| 1-02 R density census | `briefs/1-02-density-census.md` | nothing | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-03 bands + review | `briefs/1-03-bands.md` | 1-02 | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-04 coverage direction (mfde, vocab) | `briefs/1-04-coverage-direction.md` | 1-03 | 1-01, 1-05, 1-06, 1-07, 1-08 |
| 1-05 shape/container BMT | `briefs/1-05-shape-container-bmt.md` | nothing | all others except 1-09 |
| 1-06 pointers + spotcheck | `briefs/1-06-pointers-spotcheck.md` | nothing | all others except 1-09 |
| 1-07 extraction timing kickoff | `briefs/1-07-extraction-timing-kickoff.md` | nothing | all others except 1-09 |
| 1-08 schema unknown rows | `briefs/1-08-schema-unknowns.md` | nothing | all others except 1-09 |
| 1-09 expectation run and record | `briefs/1-09-expectations-and-close.md` | 1-01, 1-03..1-08 (1-07 finished) | nothing |

### Phase 2 — Coordinate model and header-word census (gate)

- Outcome: `parser/refdata/profile/coord_scale.json` exists, and decoding R at its per-class range and overlaying it against OSM at four named cells (Brisbane CBD, Sydney, rural QLD, outback) puts matched roads within a recorded distance tolerance with no clustering into a sub-region of the cell, clipped links terminating at the cell edge; the header-word rules predict R's words 0, 6, 7, 9, 10, 11 on held-out cells at ≥99%, with every exception (R's word 0 differs from the first data-slot offset in 42 of 939 sampled leaves) explained; the tolerance is the Phase 1 band and "no clustering" is measured as the occupied fraction of the cell extent and coordinate maximum relative to the cell. If either fails, the phase does not close: the design is bounced for re-analysis (user decision).
- Surfaces: new `coord_scale.json`; a census tool under `parser/tools/`; `parser/kiwiw/coordconv.py` (read-only here); `parser/kiwiw/parcel.py` decode paths; `docs/schema/` rows for the model.
- Approach: known
- Depends on: Phase 1

### Phase 3 — Native coordinates

- Outcome: after assembly from the existing spool (encoders derive pixels from lat/lon; no re-extraction), decoding G shows per-level, per-class, per-division-state coordinate maxima equal to `coord_scale.json`; `range_for` feeds both the Python and C encoders (no `COORD_RANGE` constant remains); the `coord_scale` check PASSES; two builds are byte-identical at worker counts 1/4/12; `pytest parser/tests` passes.
- Surfaces: `parser/kiwiw/{coordconv,synth,cenc,spool}.py`, `parser/kiwiw/_cenc.c`, `parser/osm_to_parcel_geometry.py`, `parser/build_alldata.py`, new `coord_scale` check, `parser/tests/{test_cenc,test_synth_*,test_spool_binary,test_build_alldata}.py`.
- Approach: known
- Depends on: Phase 2

### Phase 4 — Header words and per-sub-frame size cap

- Outcome: header words 0, 6, 7, 9–11 match the model on every parcel except the WP2-owned exemption list and the Phase 2 explained exceptions; `dipid` is valid on divided and undivided parcels; the `header_words` check PASSES; the size cap applies per sub-frame at 131,070 and the whole-frame cap is gone; output bytes are unchanged where no sub-frame exceeds R's maxima; the stale comment at `synth.py` ~942 is corrected; builds are reproducible.
- Surfaces: `parser/kiwiw/{synth,parcel,divide,parcel_mgmt}.py`, `parser/build_alldata.py`, `parser/harness/checks/{envelope,decode}.py`, new `header_words` check, `parser/tests/{test_divide,test_synth_map_frame,test_build_alldata,test_harness_mfde}.py`.
- Approach: known
- Depends on: Phase 3

### Phase 5 — Geometry generalisation and division

- Outcome: on a full-Australia build, per-level vertices per link and vertices per km fall within the band recorded in `harness.json` around R's (L8 roads ≈ R's 28.9k vertices from 107k; urban L0 within band), intermediate points are written as `nip` deltas by both encoders, each sub-frame above 2× R's per-kind maximum at L0–L8 is an advisory with a ledger cause, and divided-parent counts fall toward R's (2×2 preferred; L0 far below the current 533).
- Surfaces: new `parser/refdata/generalise.json` and a generalisation stage in or beside `osm_to_parcel_geometry.py`; `parser/kiwiw/{synth,divide,road_writer}.py`, `parser/kiwiw/_cenc.c`/`cenc.py`; envelope and new density checks; `parser/tests/{test_road_encoder,test_cenc,test_divide}.py`.
- Approach: known
- Depends on: Phase 4

### Phase 6 — Background classes and ocean polygons

- Outcome: G's background type and count distribution per level, including reserves (321) and rivers/lakes (291), match R's per-class census within the Phase 1 band; L0 CBD cells hold shape counts in R's order of magnitude (Melbourne/Sydney/Adelaide/Perth CBD cells recorded against R's 17/31/23/122); every cell in the sampled 0.25° grid that R fills with sea carries an ocean polygon (type 289; sea names belong to Phase 8); the 102 G-only L0 cells are listed with lat/lon and content and each is classified natural or defect; the catch-all `288` cells are audited (land mislabelled as sea = 0); foreign land is the only listed cell content missing from R.
- Surfaces: `parser/refdata/{selection,vocab/bg_type}.json`, `parser/osm_to_parcel_geometry.py` (background loop, bg predicate ~694, coastline/land-polygon handling), background encode path in `parser/kiwiw/synth.py`/`_cenc.c`, `parser/tests/{test_vocab,test_selection,test_background_encoder,test_parcel_geometry}.py`.
- Approach: known
- Depends on: Phase 5

### Phase 7 — Road vocabulary and level selection

- Outcome: for streets present in both R and G (name-matched cells), G's road type and display class equal R's for ≥ a recorded share (named arterials Ipswich Rd, Logan Rd, Bradfield Hwy, Pacific Motorway, Cahill Expressway resolve to R's class); at L2–L8 the type distribution is within the band of R's (type 2 as backbone); tracks are not in R's arterial class; dual-carriageway duplicate geometry at coarse levels is within R's density; the `road_vocab` check PASSES.
- Surfaces: `parser/refdata/vocab/{road_type,display_class}.json`, `parser/refdata/selection.json`, `parser/kiwiw/{vocab,selection}.py`, `parser/harness/checks/vocab.py` and new `road_vocab`, `parser/tests/{test_vocab,test_selection}.py`.
- Approach: known
- Depends on: Phase 6 (sequenced after it: both edit `selection.json`)

### Phase 8 — Name structure

- Outcome (sea/ocean names are owned here, not by Phase 6): in G, every populated cell carries a region or ocean name; string types 4 (`A=`, `1=`, plain), 5 (per segment), 6 and 1 are emitted in proportions within the band of R's per-level mix; all text is uppercase ASCII; `priority` and `display_scale_flag` values on every name record are drawn from R's observed set; the `name_coverage` check PASSES and a dry-run tally shows the L0 name_count against R's 19.08M, with any remaining shortfall attributed record-by-record to source text OSM lacks.
- Surfaces: `parser/osm_to_parcel_geometry.py` (`_make_name_record` ~530 and name gates), `parser/refdata/selection.json`, `parser/build_alldata.py`, `parser/kiwiw/{cenc,model,spool}.py`, `parser/kiwiw/_cenc.c`, `parser/kiwiw/vocab.py` (remove the `string_type=1`-at-L0 rejection; R has 1,042,019 such records), `parser/kiwiw/synth.py` (name encoders ~528–719, latin-1 sites), `parser/kiwiw/name_writer.py` unchanged for round-trip, `parser/harness/checks/vocab.py`, new `name_coverage`, `parser/tests/{test_name_encode,test_name_encoder,test_name_record_vocab}.py`.
- Approach: known
- Depends on: Phase 6

### Phase 9 — Link flags, node bits and neighbour pointers

- Outcome: flag and node-bit prevalence per level within the band of R's (`link_id_flag`, `selected_link_flag`, `route_planning_tag`, toll, bridge, tunnel, planned); mfde entries 12–19 carry computed adjacent-parcel pointers that decode to the correct neighbouring Map Frame in the harness, with entry counts matching R's distribution including divided-neighbour records; `docs/schema/flags.md` exists and every link flag and node bit R uses has a row (R census, OSM source, known/unknown, G value, pending test); no flag is undocumented.
- Surfaces: `parser/osm_to_parcel_geometry.py` (flag defaults ~470–475), `parser/kiwiw/{synth,road_writer,divide,parcel_mgmt}.py`, `parser/harness/checks/{mfde,decode}.py`, `parser/tests/{test_road_encoder,test_boundary_links,test_harness_mfde,test_synth_map_frame}.py`.
- Approach: known
- Depends on: Phases 4, 5, 6 and 8 (both edit `synth.py`, `osm_to_parcel_geometry.py` and the mfde/decode checks, so they are sequential)

### Phase 10 — Full rebuild, verification and ledger closure

- Outcome: a single full-Australia extraction and build from the final code produces a `compare_disc.py` report (bound to its ALLDATA sha256) in which every check PASSES or its remaining difference is a ledger entry with a source-data cause, contributing no processing-caused differences; entries are only *natural* or *documented-unknown* (a flag-table entry with a pending test); `docs/design/target-disc.md`, plan 01's records and `docs/schema/` rows are updated (status changes carry evidence) (deviation ledger, word 0, mfde 12–19 ownership, size semantics); the user has accepted or rejected the final ledger; capacity is within 4.7 GB; determinism verified by two builds.
- Surfaces: `output/`, `docs/design/target-disc.md`, `docs/schema/`, `docs/plans/01-eval-harness-and-map-layer.md`, `docs/provenance.md`, `docs/schema/flags.md`.
- Approach: known
- Depends on: Phases 7 and 9

## Provenance Notes

- Brief 34 removed R-derived size caps ("R's maxima are observations, not limits") — correct in spirit, but it applied the u16 limit to the wrong quantity. The evidence that header word 0 is the header size means the ceiling is per sub-frame; the 2×-R advisory retains the safety signal without inventing a build limit the format does not have.
- The plan-01 claim that R's 19M L0 names include address strings OSM lacks was not supported by a stride sample; the gap is mostly structural (name coverage per cell, per-link copies, type-4/1 tags), so it is treated as a defect until re-measured.
- Rejected: continuing with the current 32767 constant while flagging risk (user chose hard stop); divergent-candidate builds for ocean polygons or road vocabulary (user: one canonical approach, research first).
- The stale `output/report.json` (pre-brief-34) is why Phase 1 binds reports to a build hash before anything else is trusted.
