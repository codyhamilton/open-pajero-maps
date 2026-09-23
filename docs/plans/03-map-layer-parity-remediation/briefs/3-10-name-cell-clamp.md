# Brief: 3-10 — a point outside the disc's coverage is not clamped into an edge cell

Consumer: 3-06, whose per-vertex round-trip must exit 0; future extractions.
Owned paths: `parser/osm_to_parcel_geometry.py` (`assign_to_parcel` and its callers only), `parser/build_alldata.py` (the drop guard below only), `parser/tools/quantisation_roundtrip.py` (only to agree with the guard), and tests under `parser/tests/` covering these (`test_osm_to_parcel_geometry*.py`, `test_build_alldata*.py`, `test_quantisation_roundtrip.py`). Touch nothing else; if another file must change, report `needs context`.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-09.
Runs alongside: nothing.
Budget: 6 files to read, about 150 lines to change, 45 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff in your report back, not in a file.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-04 and 3-07 records (the name-anchor round-trip failure).
2. `parser/osm_to_parcel_geometry.py` `assign_to_parcel` (around line 266) and `_lon_delta`, and the call sites (`grep -n assign_to_parcel`).
3. `parser/tools/quantisation_roundtrip.py`, the name-anchor (`s`) kind.

## Goal

The round-trip fails on one name anchor, at lat −38.7273, lon 77.519. That point is assigned to L0 cell (0, 541), whose frame starts at lon 90. The likely root cause is `assign_to_parcel`. It rejects latitudes outside coverage but clamps `ix`/`iy` into `[0, n−1]`, so a longitude outside the disc's span lands in an edge cell. Confirm the root cause, then fix it at both ends:

- **Extractor.** A point outside the grid's lon span returns `None`, just as an out-of-range lat already does. Check `_lon_delta`'s wrap so a point that is genuinely inside the span is still accepted. Check every caller: roads and backgrounds use centroids, so a shape inside coverage with its centroid outside it is now dropped at that level. Report whether any caller relied on the clamp, with counts on a small fixture if you can.
- **Current spool (not re-extracted).** At assembly, drop a name record whose anchor lies outside its cell's rectangle. Count the drops per level and report them, with no silent clamping. Make `quantisation_roundtrip.py` apply the same rule, so it measures what the build writes. Do not change how anchors are encoded.

Keep untouched: roads, backgrounds, `clip.py`, `_cenc.c`, `coordconv.py`, `divide.py`, `spool.py`, `parser/harness/**`, plan documents. Do not re-extract. Put scratch under `output/scratch-3-10/` with `TMPDIR` set there. Python is `.venv-rp/bin/python`. The spool is `output/extract_timing/spool`.

## Done evidence

Write the failing test first: `assign_to_parcel` for a lon just west of the span returns `None` (it returns an edge cell today). Report the before and after output.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report the counts before and after.
- `quantisation_roundtrip.py --spool output/extract_timing/spool --out <scratch>/roundtrip.json` **exits 0**. Report per-kind totals and the worst error for each kind.
- A full assembly at `-j 12` into scratch. Report its sha256 and size, and the names dropped per level. The Perth fixture must be identical at `-j 1` and `-j 4`; report its sha. `compare_disc.py ... --checks coord_scale` PASS.

## Report back

Keep it under 1,000 tokens. Report status, the root cause as confirmed, what changed, the check output before and after, the shas, and any deviation or contradiction. Never resolve a contradiction silently.
