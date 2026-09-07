# Brief: 17 — `checks/mfde.py` should tolerate real per-parcel distributions (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve unit 03/03b's finding 2, deliberately deferred until unit 06's `DESIGN.md`
existed to ground it. It is not part of the original 01-15b dispatch list; dispatch it
independently.

Owned paths: `parser/harness/checks/mfde.py`, `parser/tests/test_harness_mfde.py` (create
if it does not already exist; otherwise extend it). Do not touch `parser/harness/profile.py`
(entry_count_hist/nregion_hist are already correctly censused; this is a comparison-logic
fix, not a profiling fix) or any other check. Commit to the current branch when done
evidence passes; push.
Depends on: 06 (`DESIGN.md`, done — this is exactly the contract this fix must match).
Runs alongside: 18 (disjoint file), 09, 10.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit 03 / 03b — Reference
   profile", finding 2: the symptom is that `mfde.py`'s entry-count and `nregion` checks
   currently compare against only the profile's *dominant* value (`_dominant_key`) and FAIL
   if a generated disc shows any other value — but `DESIGN.md` section 4 and section 3
   confirm the reference disc itself legitimately carries a real distribution of values, not
   a single constant, at every level: entry_count_hist has a long tail of 21-35-entry
   divided/integrated parcels above the dominant 20 (12 at level 12); nregion_hist shows a
   nontrivial minority of `nregion=0` parcels alongside the dominant 1 (or 0) value (Section
   3's open question 2 — the exact population isn't resolved, but the *presence* of the
   minority is confirmed data, not noise).
2. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` — sections 3 and 4 in full,
   especially the per-entry-index presence-class subset logic already implemented for the
   per-index check ("How the harness judges a slot's absence" in section 4) — this is the
   pattern to generalize, not invent from scratch.
3. `parser/harness/checks/mfde.py` — read the whole file. Note it already does the right
   thing (profile-subset comparison) for `per_entry_index_class_hist`; only the entry-count
   and nregion checks use the narrower dominant-only comparison.
4. `parser/harness/profile.py` — `build_profile()`, to confirm `entry_count_hist` and
   `nregion_hist` are already full per-level histograms (not just the dominant value) in
   both the reference profile and `generated_profile()`'s output, so no profiling change is
   needed, only how the check consumes them.

## Goal

`mfde.py`'s entry-count and `nregion` checks should judge a generated disc's *set* of
observed values as a subset of the reference profile's observed set for that level/index —
the same subset logic the per-index presence-class check already uses — instead of
requiring every generated parcel to match only the profile's single dominant value.

## Contract

`DESIGN.md` sections 3-4 (binding) plus `mfde.py`'s existing per-index subset pattern
(binding as the shape to follow). WP1 today (before unit 13 lands divided-parcel support)
only ever emits the dominant entry count and `nregion=0`, so this change must not turn any
currently-passing check into a FAIL — it only widens what *would* pass once unit 13 starts
emitting non-dominant values. Keep the check's FAIL messages informative: report which
observed values are outside the reference's set, not just that a mismatch occurred.

## Changes

- Replace the entry-count check's `g_entry_counts - {ref_dominant_count}` subset test with
  `g_entry_counts - set(ref_entry_hist.keys())` (full histogram, not just the dominant key).
- Replace the `nregion` check's equivalent `g_nregion_values - {ref_dominant_nregion}` test
  the same way, against `set(ref_nregion_hist.keys())`.
- Keep `_dominant_key` if still used elsewhere in the file (e.g. purely informational
  `level_detail` reporting); if it becomes unused, remove it.
- Tests: synthetic profiles (small dicts, not a real disc) where a generated histogram has a
  non-dominant-but-profiled value (should PASS) and a value absent from the reference profile
  entirely (should still FAIL), for both entry-count and nregion.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --generated output/ALLDATA.KWI --checks mfde` on
  an existing single-level build → still PASS (confirms the widening didn't regress today's
  dominant-only case).

## Report back

A short summary, anything you deviated from in this brief and why, and any contradiction you
found between this brief, `DESIGN.md`, and the code. **Do not resolve contradictions
silently — report them.**
