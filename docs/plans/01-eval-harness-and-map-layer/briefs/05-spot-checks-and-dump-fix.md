# Brief: 05 — Spot-check fixture table and `dump_parcel.py` JSON fix

Consumer: implementation worker.
Owned paths: `parser/kiwiw/model.py` (function `to_jsonable` only), `parser/dump_parcel.py`,
`parser/harness/checks/spotcheck.py` (new), `parser/refdata/spot_checks.json` (new),
`parser/tests/test_dump_parcel.py` (new), `parser/tests/test_harness_spotcheck.py` (new).
Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 02.
Runs alongside: 03, 03b, 04, 07.

## Required reading, in order

1. `docs/design/target-disc.md` — the paragraph after the check table: "Content-level spot
   checks (named coordinates in Brisbane, Sydney, Melbourne, Perth, Hobart, Darwin, Adelaide
   resolving to the expected OSM street/place names) are a fixture table consumed by the
   harness, not ad-hoc."
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — user-facing acceptance bullet 4
   (`dump_parcel.py … --lat -27.4698 --lon 153.0251 --level 0` prints valid JSON with Queen
   Street / Adelaide Street; the same for the fixture table at levels 0 and 2) and "Why This
   Plan Exists" gap (7) (`to_jsonable` passes `bytes` through).
3. `parser/kiwiw/disc.py` — `AllData.find_parcel` (the locate path both the CLI and the
   check use).
4. `parser/dump_parcel.py`, `parser/kiwiw/model.py` `to_jsonable`.

## Goal

Make the spot checks a data table the harness runs, and make `dump_parcel.py` usable again
on any parcel (the IR now carries `bytes` fields).

## Contract

Settled: `bytes` serialise as lowercase hex strings under the same key (no key renames, no
dropped fields). Settled: the fixture table lives at `parser/refdata/spot_checks.json`,
referenced from `harness.json`'s `spot_checks` key; each row is `{"city", "lat", "lon",
"levels": [0, 2], "expect_road_names": [...], "expect_place_names": [...]}`. A row passes at
a level when a parcel is found and every expected name for that level appears in the
decoded road/name records (case-insensitive substring match on `NameRecord.text`); level 2
rows expect place names only. Seed rows: Brisbane −27.4698, 153.0251 (Queen Street,
Adelaide Street); Sydney −33.8688, 151.2093; Melbourne −37.8136, 144.9631; Perth −31.9505,
115.8605; Adelaide −34.9285, 138.6007; Hobart −42.8821, 147.3272; Darwin −12.4634,
130.8456. Fill each row's expected names from OpenStreetMap's actual CBD street names at
those coordinates (two or three well-known streets per city; verify against the PBF or a
map, and say in the report where each came from). The fixture is judged against `G`, so
expectations are OSM names, not the reference disc's.

## Changes

### `to_jsonable`

Add `bytes`/`bytearray` → `.hex()`. Leave every other branch as is.

### `parser/dump_parcel.py`

No behaviour change beyond working again; add `--alldata` default of `output/ALLDATA.KWI`
resolved from the repo root so the acceptance command works as written without the
reference mounted.

### `parser/harness/checks/spotcheck.py`

`spotcheck`: for each row and level, `find_parcel` on `G`; details per row: found/not,
matched names, missing names. FAIL if any row/level misses. NA when the table file is
absent.

### Tests

`test_dump_parcel.py`: `to_jsonable` on a `Parcel` built with a non-empty `raw_bytes` and
`ext_frame_raw` produces `json.dumps`-able output with hex strings. `test_harness_spotcheck.py`:
against an in-test synthetic disc with one parcel containing a name record "Queen Street",
a table row expecting it PASSes and a row expecting "Nowhere Road" FAILs.

## Done evidence

- `.venv-rp/bin/python parser/dump_parcel.py --alldata /run/media/codyh/464210-8480/ALLDATA.KWI --lat -27.4698 --lon 153.0251 --level 0 | .venv-rp/bin/python -m json.tool > /dev/null` → exit 0.
- `.venv-rp/bin/python parser/compare_disc.py --generated /run/media/codyh/464210-8480/ALLDATA.KWI --checks spotcheck` → runs; every row reports found; matches may FAIL (the reference is 2007 WhereIS data, not OSM) — report which names matched anyway.
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.

## Report back

A short summary: the final fixture rows and the source of each expected name, anything you
deviated from in this brief and why, and any contradiction you found between this brief and
the contracts it cites. **Do not resolve contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
