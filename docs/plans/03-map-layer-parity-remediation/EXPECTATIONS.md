# Phase 1 expectation list (unit 1-09)

Run: `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI --report output/compare_report.json` (exit 1, manifest-bound).

- `generated_sha256`: `51c254ac87328f652e88f0b10880e83992622bcd1d2db2dbd519edc0a5672743` (equals `sha256sum output/ALLDATA.KWI` and `output/manifest.json`; `manifest_bound: true`).
- Bands review (`parser/refdata/harness.json` `bands.review`): objections 1-11 recorded, resolution amendments applied a priori; **orchestrator confirmation pending, not marked accepted**.
- Extraction wall time (`output/extract_timing/run.log`, `osm_to_parcel_geometry.py`, australia-260824.osm.pbf): **26:03.27**, exit 0, 12 cores, load 0.12 at kickoff, max RSS 10.1 GB. Upper bound: other units ran concurrently.
- Known concern (1-06): strict `pointers` FAILs R itself on about 2% of targets; on G, `pointers` PASSES.

## Checks

| Check | Status | Message | Predicting finding |
|---|---|---|---|
| container | FAIL | 19 unallowlisted differences: 13 BMT tables present in G only, 6 BMT DSA order violations | G-only tables (F12 shape/container); DSA non-monotonic (F12) |
| decode | PASS | 3954097 leaves, zero errors | - |
| pointers | PASS | all pointers resolve on G | (strict check also FAILs R ~2%, see 1-06) |
| envelope | FAIL | L0 name_count ratio 0.119 outside [0.5, 2.0] | F8 (name records; L0 name_count rule stays, DESIGN line 65) |
| envelope | (same FAIL) | L10 Map Frame max 3616 > R 2336 | F3/F5 (G frame sizes above R's maxima; ratio 1.55, under the 2x-R advisory line that Phase 4 makes the rule). Added to list after orchestrator triage; check itself unchanged |
| envelope | (same FAIL) | L12 Map Frame max 4992 > R 3808 | F3/F5 (ratio 1.31, under 2x-R). As above |
| mfde | FAIL | 0 subset failures; 50 coverage failures (L0-L6: nregion, entries 10, 12-29 class) | poorer-than-R coverage (F12); nregion is WP2-owned (F2), entries 12-19 F11 |
| mht29 | PASS | frame byte-identical | - |
| shape | FAIL | 19 differences (same 13 G-only BMT tables + 6 DSA order) | F12 |
| spotcheck | PASS | 15/15 rows matched, including Grenfell row | - (Grenfell row predicted FAIL did not fire) |
| vocab | FAIL | coverage below 0.95 at L0, L2, L4, L6, L8 (road_type/display_class 2,3,10,9 at L2-L8; name_string_type/name_type_code 4,1,5,509,528,9,6,2,3; background 291,578,289) | F4 (road/display class), F8 (names), F6/F7 (background) |

## Detail

- G-only BMT tables: (L0 bs 0, 9, 25, 26, 32, 57, 89, 112, 113), (L2 bs 57, 112, 113), (L4 bs 24).
- DSA order: (L10,0), (L8,0), (L6,0), (L4,1), (L2,2), (L0,0 entry 16).
- mfde coverage L8-L12 clean; L6 also fails `entry_count`.
- No advisories in the report.

## Triaged FAILs (initially unexpected; now expected: 2)

1. envelope: L10 Map Frame max size 3616 exceeds R max 2336.
2. envelope: L12 Map Frame max size 4992 exceeds R max 3808.

Triage: the envelope check's absolute R-max rows are superseded by the 2x-R advisory (FINDINGS F3, Phase 4); G exceeds R by 1.55x and 1.31x, consistent with F5 density. Cause inferred from ratios, not separately measured; Phase 4/5 must confirm.

## Refusal demonstration

`compare_disc.py --generated <scratch dir with symlinked ALLDATA.KWI and manifest.json whose sha256 begins with 0 instead of 5> --checks decode` exit 2: "refusing to compare: ... sha256 51c254... != manifest ... sha256 01c254... (stale manifest/report or a different build)". (Manifest altered rather than a byte of the 1.4 GB disc; same code path.)
