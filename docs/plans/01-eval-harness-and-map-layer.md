# Offline evaluation harness and full-Australia map layer (WP1)

WP1 built the offline reference-vs-generated comparison harness (`parser/compare_disc.py`, `parser/harness/`) and brought the map layer (`ALLDATA.KWI`) from a one-level, Perth-only prototype to a from-scratch, all-seven-level, full-Australia build generated from the OSM PBF. The harness works and the build passes most of it: container, decode, pointers, mfde, mht29, shape, vocab and spotcheck PASS on the final build. It did not fully meet its goal. The envelope check still FAILs on two counts, several content trims exceed 1%, and the work was never formally accepted. Those gaps were handed to the map-layer parity remediation plan (`docs/design/map-layer-parity-remediation.md`), which regenerates the deviation ledger from one final build.

## Intent

User request, verbatim:

> Check the current implementation status of our plan. It is currently tracked in docs, lets form it into a more formal plan, filling gaps and ensuring the target meets our goal.

## Why This Existed

The project plan predated a burst of code that added a from-scratch encoder set, an OSM geometry extractor, a Link ID registry and an end-to-end `build_alldata.py`. The docs recorded none of it, and the stated target was stale. The status check found the encoders solid but far from the goal:

- Synth name records used `string_type=1`, which does not occur at level 0 on the reference disc.
- Map Frames carried a 3-entry mfde table where the reference carries 20.
- The assembler built a single level with a flat BSMR/BMT, and fell back to a synthetic grid when the reference disc was absent, so output depended on the environment.
- Every script defaulted to a Perth bbox, and the full-PBF extraction did not finish.
- Nothing compared a different-content build against the original; every proof was a same-content round trip.

The user then reset the target: full Australia, every feature, every map-dependent file regenerated, and evaluation by offline byte and structural comparison with the reference disc as oracle. In-vehicle testing is last-mile acceptance, not a feedback loop, and a first burn is not a rebuilt-original. That target is the program of record in `docs/design/target-disc.md`. WP1 is its first work package: the harness every later package is judged by, plus the map layer as the most mature layer and largest byte share.

## What Was Built

**Changed:** `parser/compare_disc.py`, `parser/harness/` (with `checks/`), `parser/kiwiw/grid.py`, `parser/kiwiw/alldata_writer.py`, `parser/kiwiw/synth.py`, `parser/kiwiw/divide.py`, `parser/osm_to_parcel_geometry.py`, `parser/build_alldata.py`, `parser/dump_parcel.py`, `parser/refdata/` (grid, record-29 frame, per-layer profile, vocabulary tables, per-level selection, spot checks, harness config), and tests under `parser/tests/`.

**Harness.** `compare_disc.py --reference <disc> --generated <output>` prints a per-check PASS/FAIL/N-A table, writes a JSON report and exits 0 only when every applicable check passes. Checks: `container` (byte-diff against an allowlist), `decode`, `pointers`, `shape` (per-level LMR/BSMR/BMT), `mht29` (record-29 frame byte-identical), `envelope` (per-level count ratios and sub-frame size maxima), `mfde`, `vocab`, `spotcheck` (fixture table of city coordinates at levels 0 and 2). `--checks` selects a subset, `--config` overrides envelopes and fixtures, and `--profile` regenerates the checked-in reference profile, split per layer so later packages extend it without regenerating the map part. The harness imports only the parser's reading paths, enforced by a test, so a harness change cannot alter a build. Per-level checks iterate the union of reference and generated levels, so a level missing from the build fails rather than vanishing from the report.

**Build.** The reference grid parameters and the record-29 frame are checked-in data, so a build never reads the mounted disc and is deterministic. Extraction is one streaming PBF pass over all levels with a spool, antimeridian-safe. The assembler emits levels 12, 10, 8, 6, 4, 2, 0 with the reference LMR/BSMR/BMT shape and the full mfde table. Oversize frames are divided into type-1 (2x2) or type-2 (4x4) sub-cells, with per-kind sub-frame budgets and a fallback that trims content when a frame would still exceed the u16 ceiling. Link identity is `(osm_way_id, ordinal)`. Name records use string types 4/5/6 at level 0 and a level-0 road-name halo; vocabularies and per-level feature selection are data-driven from the reference census.

**Final build.** Full Australia: 1,428,500,032 bytes (about 30% of the 4.7 GB budget once the reference's non-map bytes are added), 3,967,170 leaves decoding with zero errors, 281 tests passing. The first full extraction took about 1.5 hours at about 9.7 GB peak RSS; per-level selection thinned the spool from about 21 GB to about 7 GB. Assembly alone takes about 17 minutes.

Map Frame, mfde, region-list and header format facts established here (spec-named header fields, slot ownership, divided-neighbour entries at slots 12-19, the extended-frame slot 10 duplicate of the name sub-frame) live in `docs/schema/map-frame.md` with per-row verification status; the grid and container facts are in `docs/schema/disc-layout.md` and `docs/schema/parcel-management.md`.

## Deviations

- **Bulk of WP1 was not planned up front.** The original plan was units 01-15. Roughly twenty ad-hoc briefs followed the first full build, covering a name-type vocabulary leak, dune/bay vocabulary consistency, missing spot-check names, an mfde entry-count gap, container PDMDH blob-length handling, envelope recalibration, per-kind budgets, a pinned-road-budget release and a ceiling-only size limit. Each was dispatched from build findings.
- **The mfde slots 12-19 hypothesis changed.** The design first treated them as route-guidance pointers (WP2's). Evidence showed they resolve to other parcels' Map Frames (adjacent-parcel address information), not to route-planning frames; the resolution and its remaining open questions are recorded in `docs/schema/map-frame.md` and the unknowns index.
- **Final-build differences were never accepted.** The last full build ended with nine "proposed declared deviations" that the user never accepted or rejected. They are unaccepted and are superseded by the parity remediation plan, which regenerates the ledger from a single final build:
  1. Level 0 name_count 0.149x of the reference (envelope [0.5, 2.0]); the reference's 19M includes address-style strings OSM lacks.
  2. Level 12 parcel_count 3 vs 1; the single cell is divided because its background shapes exceed the reference ceiling.
  3. Level 0 background trim, 1.46% in 214 sub-cells.
  4. Level 8 name trim, 12.9% in 6 sub-cells.
  5. Level 8 background trim, 13.0% (fallback path).
  6. Level 8 road trim, 18.8% in 3 sub-cells, after pinned motorway and trunk links were released from the road budget.
  7. Blockset coverage gap: about 60 reference-only blocksets (offshore fill), about 12 generated-only; not re-measured after the last fix.
  8. Container PDMDH tolerance: the check passes because lengths differ only by 6 bytes per BMT entry.
  9. Adelaide level-0 spot-check oracle amendment: "Grenfell Street" dropped from the expected names because the reference itself lacks it there.

## Review

One independent review covered only the first three units (reference container data, harness core, extractor at country scale). Verdict PASS_WITH_FOLLOWUPS with no blocker, high or medium findings, and the grid-contract, harness-reads-only and determinism assumptions held. The later units (profile, vocabulary, assembler, divided parcels, selection, rebuilds and the ad-hoc briefs) were verified by the harness and the test suite, not by an independent review. No blocker or high finding stands. The three low findings are under Follow-ups.

## QA

Verification was the harness itself. The final rebuild's report shows container (3,142 allowed diffs), decode, pointers, mfde, mht29, shape, vocab and spotcheck (14/14) PASS and envelope FAIL on the two items above; every sub-frame kind maximum was within the reference's. In-vehicle testing is deliberately out of scope until the whole program is built.

## Residual Risks

- Level 0 is the capacity and fidelity pressure point: OSM name density differs from the 2007 reference, and level 0 is exempt from failing on count.
- The final trims and the two envelope FAILs are unresolved (see Deviations). The parity remediation plan owns them, including the coordinate-model and encoding questions it found.
- Dual-layer media support on the head unit is unknown; single-layer 4.7 GB was assumed.
- The last code change (u16 ceiling as the only size limit, `7917b86`) had its rebuild started but no verification result was recorded. The final-build figures above predate it.

## Follow-ups

- Regenerate the deviation ledger from one final build and get user acceptance: parity remediation plan, `docs/design/map-layer-parity-remediation.md`, and the ledger in `docs/design/target-disc.md`.
- Low, from the review: collapse the duplicated layer-presence check in `checks/decode.py` and `checks/shape.py` into the CLI gate; add a cheap way-level bbox pre-check so `--fixture` runs on the full PBF are fast; fold the spool's content-type totals into its first index pass. No tracker exists; these are recorded here only.
- Open format questions carried to `docs/schema/UNKNOWNS.md`: the mfde 12-19 mechanism and its stride, the header census beyond a 49-read sample, and the level-0 residual idx10 variant.
- Route planning, search indexes, metadata regeneration and image authoring remain WP2-WP5 in `docs/design/target-disc.md`.

## Decisions Worth Keeping

- Evaluate offline against the reference; treat in-vehicle testing as last-mile. Rejected: a rebuilt-original first burn and any partial regional milestone.
- The harness must import only reading paths and a build must never read the mounted disc, so evaluation cannot change output and builds reproduce anywhere.
- A country-scale build is its own unit with a kickoff and a separate verifier that never resumes the kickoff worker, because the wait is long.
- The `2##` index-file suffix partitions by state, not zoom level (recorded in `docs/schema/index-idx.md`).
