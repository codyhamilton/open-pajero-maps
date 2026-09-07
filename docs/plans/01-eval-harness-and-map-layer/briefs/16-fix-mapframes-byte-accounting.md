# Brief: 16 — Fix `mapframes_bytes_total` double-counting in `profile.py` (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve a genuine bug unit 03/03b found and deliberately did not fix (per its own brief's
"report it, don't fix it" instruction). It is not part of the original 01-15b dispatch list;
dispatch it independently, in parallel with units 06 and 08 (disjoint files from both).

Owned paths: `parser/harness/profile.py`, `parser/harness/walk.py` (read-mostly; only touch
if the root cause requires a `WalkedParcel.length` fix), `parser/harness/checks/envelope.py`
(only if its byte-total consumption needs to change shape), `parser/tests/test_harness_profile.py`.
Do not touch checks unrelated to byte totals, and do not touch `parser/refdata/profile/map.json`
by hand — regenerate it via the documented command if the fix changes its byte-total fields.
Commit to the current branch when done evidence passes; push.
Depends on: 03b (done — this is exactly the bug it flagged). Runs alongside: 06, 08.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, section "Unit 03 / 03b —
   Reference profile", finding 3 ("`envelope` FAIL — likely a real bug in `profile.py`'s
   byte-total accounting"). This is the full symptom report: `mapframes_bytes_total` computed
   as 4,680,715,968 bytes against a real `ALLDATA.KWI` of 1,529,729,025 bytes — level 0 alone
   (4,543,141,152 bytes) is already ~3x the whole file. The independently-computed
   `blocks_bytes_total` (26,568,960 bytes, summed from the PDMDH's BMT tables) is ~176x
   smaller than the leaf-frame total it should contain, i.e. the two accounting paths
   disagree with each other as well as with the file size.
2. `parser/harness/walk.py` — `iter_parcels()`, in particular `_iter_tree_leaves()` (yields
   one `(leaf_path, entry, leaf_bounds, ptype)` per leaf slot in the parcel-management
   subrecord tree) and the leaf-yield block in `iter_parcels` that reads `moff/mlen` from
   `entry.dsa`/`entry.size` per leaf and yields a `WalkedParcel` with `length=mlen`.
3. `parser/harness/profile.py` — `build_profile()`: `mapframes_bytes_total` sums `wp.length`
   over every `iter_parcels()` yield; `blocks_bytes_total` sums BMT entry sizes directly from
   the PDMDH, independent of the parcel tree walk.
4. `parser/kiwiw/parcel.py` — `parse_parcel_mgmt_record` and whatever decodes divided-parcel
   sub-grids (parcel types 1..3: 2x2, 4x4, 1x1 per the LMR). The suspected root cause is that
   sibling leaf slots in a divided parcel's subrecord tree reference the same on-disk `dsa`
   (the sub-slots point into one shared physical Map Frame, or into overlapping byte ranges),
   so `iter_parcels()` yields that frame's bytes once per referencing slot instead of once per
   unique on-disk byte range — read the record/subrecord structure to confirm or refute this
   against the actual entry `dsa`/`size` values you observe.

## Goal

Make `mapframes_bytes_total` (and any other total computed by summing `iter_parcels()`
yields) count each unique on-disk Map Frame byte range exactly once, so it is bounded by the
file size and agrees with `blocks_bytes_total`'s order of magnitude.

## Contract

Not settled — this is an investigation. Confirm the actual root cause before changing code
(it may be leaf-slot aliasing as hypothesized above, or a units/field mismatch in how `length`
is computed, or something else). Whatever the cause, the fix must preserve `iter_parcels()`'s
existing per-leaf semantics for every other consumer (`decode`, `pointers`, `shape`, `vocab`,
`mfde`, `spotcheck` checks all iterate it for parcel content, not byte totals) — do not change
what a leaf yields; only change how `build_profile()` accumulates byte totals from those
yields (e.g. dedupe by `(file_offset, length)` or `entry.dsa` before summing), unless your
root-cause finding shows the bug is actually in `WalkedParcel.length` itself, in which case
fix it there and re-check every consumer's tests still pass.

## Changes

Root-cause first; then the minimal fix in `profile.py` (preferred) or `walk.py` (only if the
bug is there). Add a regression test in `test_harness_profile.py` against a synthetic
`ALLDATA.KWI` built with `alldata_writer.build_alldata_kwi` using a divided parcel (type 1, 2
or 3), asserting `mapframes_bytes_total` does not exceed the file's actual on-disk Map Frame
region size.

## Done evidence

- `.venv-rp/bin/python parser/compare_disc.py --profile --reference /run/media/codyh/464210-8480 --profile-out /tmp/wp1-fix-mapframes.json` → `byte_totals_by_layer.mapframes_bytes` no longer exceeds the reference disc's actual `ALLDATA.KWI` file size (1,529,729,025 bytes) and is consistent in order of magnitude with `blocks_bytes` (26,568,960 bytes) plus the file's total.
- Re-run `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated /run/media/codyh/464210-8480/ALLDATA.KWI --profile --checks envelope` (self-check) → the capacity projection no longer reports over-budget against a disc that is well under budget.
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- If the fix changes `mapframes_bytes_total`'s value materially, regenerate and commit
  `parser/refdata/profile/map.json` in the same commit (document the old vs. new totals in
  your report).

## Report back

Root cause (with evidence — the specific `dsa`/`size` values that show aliasing, or whatever
you actually found), the fix, before/after byte totals, and any contradiction between this
brief and the code. **Do not resolve contradictions silently — report them.** If the true
root cause turns out to require touching `parser/kiwiw/parcel.py` itself (outside this
brief's owned paths), stop and report that rather than editing it — the orchestrator will
decide whether to widen this brief or hand it to whoever owns unit 06/12/13.
