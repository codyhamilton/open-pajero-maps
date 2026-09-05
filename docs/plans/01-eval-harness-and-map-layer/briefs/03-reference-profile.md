# Brief: 03 — Reference profile (census) and profile-based checks

Consumer: implementation worker.
Owned paths: `parser/harness/profile.py` (new), `parser/harness/checks/vocab.py` (new),
`parser/harness/checks/envelope.py` (new), `parser/harness/checks/mfde.py` (new),
`parser/refdata/profile/map.json` (new), `parser/tests/test_harness_profile.py` (new), and
the `--profile` branch of `parser/compare_disc.py` (only that branch). Do not touch
anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 02.
Runs alongside: 04, 05, 07.

## Required reading, in order

1. `docs/design/target-disc.md` — "Evaluation: the offline oracle": **Same vocabulary** and
   **Profile envelope** rows; "Pipeline shape and stage contracts": **Vocabulary** and
   **Name records** bullets.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Execution Phases" row for unit 03
   (the census list), "Open Questions" (mfde entries 3..19; name string types; per-level
   road selection tolerance), and the acceptance bullets on vocabulary subsets, count
   envelopes and mfde entry count.
3. `parser/harness/` as landed by unit 02 (`walk.py`, `context.py`, check interface).
4. `parser/kiwiw/parcel.py`, `parser/kiwiw/name.py`, `parser/kiwiw/road.py`,
   `parser/kiwiw/background.py` — the fields you census.

## Goal

Produce the checked-in reference profile for the map layer, and the checks that judge a
generated disc against it. The profile is the shared vocabulary contract WP2–WP4 extend.

## Contract

Design doc (settled): "Type/class codes emitted by any encoder come from a census of the
reference disc (`R`), recorded in the harness config, not invented." Vocabulary check:
"Every enumerated value in `G` … is drawn from the set observed in `R`." Envelope check:
"default 0.5×–2× on counts, ≤ `R`'s observed maximum on any per-parcel or per-record size.
Level 0 road counts are exempt from the count envelope."

Plan acceptance (settled): "the mfde entry count and absent-slot encoding match the profile
on every parcel."

Refinement measurements (2026-09-05, one Brisbane parcel per level) that the full census
must confirm or correct — they are hypotheses, not the profile:

- mfde table length: 20 entries at levels 0–10, 12 at level 12. Absent slot encoded
  `(0xFFFFFFFF, 0)`. Entry 10 is in-buffer at every level; entry 4 in-buffer at level 0;
  entries 12..19 are out-of-buffer (absolute sector) at levels ≤10, with entry 17 absent
  at level 10.
- `nregion` is 1 at levels 0–8 and 0 at levels 10–12 (region list = 4 bytes).
- Name string types are **per level**: level 0 uses 4 (dominant), 5, 6; levels 2–12 use 1
  (and 5 at level 2). The plan's "`string_type=1` never occurs" holds at level 0 only.
- Level 0 road types observed {0,2,3,5,6,7,8}, display classes {3,4,7,9,10,12}; levels
  2–8 road types {0,2,3}, display classes {9,10,12}.

## Changes

### `parser/harness/profile.py`

`build_profile(alldata_path) -> dict` using `walk.iter_parcels`. Per level: parcel count by
`parcel_type`; block count and occupied-block count; Map Frame size min/max/mean/p95 and
byte total; per-frame-kind byte totals (road, background, name, ext in-buffer, tail); road
link count, node count, road-type histogram, display-class histogram, per-link flag
histograms (`toll_flag`, `oneway`, `link_id_flag` …); background shape count, type-code
histogram, shape-class histogram, `mult_const` histogram, max `n_coords`; name record
count, string-type histogram, type-code histogram, priority histogram, max text length;
mfde: entry-count histogram, per-entry-index histogram of {absent, in_buffer, out_of_buffer};
`nregion` histogram and the distinct region-list byte values (hex) with counts; tail-length
histogram. Also the whole-file byte total by layer using the MHT: map layer = PDMDH blob +
all blocks + all Map Frames; every other non-sentinel MHT entry's bytes reported under its
index (WP2–WP4 name them later). Write with sorted keys, indent 2, so a re-run is
byte-identical. Include `"source"` (disk title, data version) and `"profiled_at_commit"`.

### `--profile` in `parser/compare_disc.py`

`--profile --reference <root>` writes `parser/refdata/profile/map.json` (or `--profile-out`).
Print per-level progress; the reference has ≈ 1836 level-0 blocks, so this run takes
minutes — it must stream.

### Checks

- `vocab` (`checks/vocab.py`): per level, the sets of road type, display class, background
  type code, name string type, name type code observed in `G` are subsets of the profile's
  sets for that level. FAIL lists the offending values per level. Additionally FAIL if
  string type 1 appears at level 0 (the plan's explicit criterion).
- `envelope` (`checks/envelope.py`): per level, `G`'s parcel count, link count, background
  count, name count each within `config["envelopes"]["count_ratio"]` of the profile, except
  level-0 link count when `config["level0_count_exempt"]` (report the ratio, status PASS);
  every Map Frame ≤ the profile's per-level max; every road/background/name sub-frame ≤ the
  profile's per-level max. Report the map-layer byte total and the capacity projection:
  `G` map bytes + profile's non-map MHT byte totals vs 4,700,000,000 — FAIL if over, and the
  message names the level-0 trade-off.
- `mfde` (`checks/mfde.py`): every parcel's mfde entry count equals the profile's count for
  its level; every absent entry is encoded as the profile's absent value; per-entry-index
  presence classes in `G` are a subset of those in the profile (an entry that is always
  absent in `R` may not be present in `G`). `nregion` per level equals the profile's
  dominant value.

### Tests

Build a tiny profile from an in-test synthetic disc (via `alldata_writer.build_alldata_kwi`)
and assert the profile's structure; run `vocab` with a hand-built profile dict against a
disc containing an unlisted display class and assert FAIL with that value in `details`;
assert `envelope` exempts level 0 link counts and reports the ratio; assert `mfde` FAILs on
a 3-entry table when the profile says 20.

### Keep untouched

`checks/decode.py`, `checks/shape.py`, `walk.py`, `context.py`, `registry.py`.

## Done evidence

- `.venv-rp/bin/python parser/compare_disc.py --profile --reference /run/media/codyh/464210-8480` twice → `git status --porcelain parser/refdata/profile` shows no change after the second run.
- `parser/refdata/profile/map.json` records, for level 0: string types `{4,5,6}` (and whether 1 appears anywhere at level 0 — report the count), mfde entry count 20, absent value `[4294967295, 0]`; for level 12: mfde entry count 12. Report every deviation from the hypotheses in the Contract section.
- `.venv-rp/bin/python parser/compare_disc.py --reference <root> --generated <root>/ALLDATA.KWI --checks vocab,envelope,mfde` → all PASS (the reference passes its own profile).
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.

## Report back

A short summary: the per-level tables for string types, road types, display classes, mfde
presence by index, and `nregion`; the capacity numbers (map bytes and non-map bytes); the
profile run wall time; anything you deviated from in this brief and why; and any
contradiction you found between this brief and the contracts it cites. **Do not resolve
contradictions silently — report them.**
