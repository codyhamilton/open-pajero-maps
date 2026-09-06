# Brief: 06 — `DESIGN.md`: Map Frame shape, mfde/RP slot contract, ext-frame policy

Consumer: implementation worker (writing a design document; no code).
Owned paths: `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` (new). Do not touch
anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 03b (the committed profile is the evidence this document cites).
Runs alongside: 04, 05, 07, 08.

## Required reading, in order

1. `docs/design/target-disc.md` — "Pipeline shape and stage contracts": **Route-planning
   placement**, **Ext frames**, **Copy-through management data**, **Unknown bytes policy**;
   the file table rows for the route-guidance parcel list / mfde 3..19.
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — "Architectural Implications" bullet
   on `build_alldata_kwi` (slot contract "stated in this folder's `DESIGN.md`"); "Open
   Questions": **mfde entries 3..19**; the closing note that WP2's RP-placement spike may
   start once this file exists.
3. `parser/refdata/profile/map.json` (unit 03) — the `mfde`, `nregion`, region-list and
   ext-in-buffer sections.
4. `parser/kiwiw/parcel.py` — `decode_parcel` docstring; `parser/kiwiw/synth.py`
   `build_map_frame_bytes` (what is emitted today: 3 entries, `nregion=0`).
5. `spec/format_english/pdf/0701122e.pdf` (Ch.7.1 Main Map Data Frame: distribution header,
   region list, Basic/Extended Data Frame entries) and `spec/format_english/pdf/0600122e.pdf`
   (Ch.6, for the parcel-management side of divided parcels).
6. `parser/analyze_ext_frames.py` — the existing Ch.10.5 ext census, for what "ext" means on
   the RP side, so the two are not conflated.

## Goal

Write down, before any encoder changes, exactly what a WP1-generated Map Frame's header,
region list and mfde table contain, which slots WP1 leaves for WP2 and how an empty slot is
encoded, so units 09 and 12 implement it and WP2 can start its placement spike against it.

## Contract

Design doc, Unknown bytes policy (settled): "in from-scratch mode it must be either
generated from a decoded model or proven absent/zero on `R` — never silently zero-filled."
Plan Open Question (settled path): "Units 06/09 then either generate the entries from a decoded
model or emits the censused absent-slot value and leaves them for WP2. If neither is
possible, it is a format-analysis dead end and the choice … goes to the user."

The document must decide, with the profile as evidence, for each of: the 36-byte Map Frame
header fields beyond `llpid`/`llcode` (what `R` carries per level; what WP1 emits); `nregion`
and the 4-byte region-list entry at levels 0–8 (decode it from Ch.7.1 or record it as an
open format question with the exact bytes observed); the mfde table length per level (20 /
12 per the refinement spot check; confirm from the profile); the meaning and WP1 treatment
of each entry index 3..19, grouped as: always-absent on `R`, in-buffer Extended Data Frame
(indices 4 and 10 observed), out-of-buffer route-guidance pointers (12..19). For each group
state what WP1 emits (absent value `(0xFFFFFFFF, 0)` unless a decoded model exists) and what
WP2 owns. State how a slot's absence is judged by the harness (`checks/mfde.py`) so the
generated disc's declared deviations are checkable, not prose.

## Changes

### `DESIGN.md` sections (in this order)

1. **Scope and precedence** — this file governs Map Frame shape for WP1 and the slot
   handoff to WP2; the stable design doc wins on conflict.
2. **Map Frame header** — per-field table: offset, length, `R`'s observed values per level
   (from the profile or a short census you run read-only), WP1 emission, confidence.
3. **Region list** — decision and evidence.
4. **mfde table** — length per level; per-index table (index, `R` presence class per level,
   what it is, WP1 emission, owner).
5. **Ext frames in the Map Frame vs Ch.10.5 ext** — one paragraph disambiguating.
6. **Divided/integrated parcels** — the parcel types 1..3 sub-grids (2×2, 4×4, 1×1 from
   the LMR), how `R` uses them per level (occupancy from the profile), and the rule WP1
   applies (unit 13 implements it): divide when a Map Frame would exceed the profile's
   per-level maximum; which type to use first.
7. **Handoff to WP2** — the exact list of slots WP2 fills, their encoding when empty, and
   the `harness.json` / profile keys WP2 must update.
8. **Open format questions** — anything above you could not decide from the spec + profile,
   with the exact observed bytes, so the user can decide or WP2 can spike.

Keep it under ~250 lines. Cite spec sections by PDF file and section number.

### Keep untouched

Do not edit `PLAN.md` or the stable design doc; if you find a contradiction, put it in
section 8 and in your report.

## Done evidence

- The file exists with the eight sections; every numeric claim cites `parser/refdata/profile/map.json` or a spec section.
- Section 4's per-index table covers every index 0..19 with a WP1 emission decision, and none of the decisions is "zero-fill".
- Section 8 is either empty or lists questions with observed bytes.

## Report back

A short summary of the decisions taken, the open questions left, anything you deviated
from in this brief and why, and any contradiction you found between this brief, the profile
and the contracts it cites. **Do not resolve contradictions silently — report them.**

If you find a non-trivial bug outside what your own done evidence requires — real
debugging, not a one-line fix, and not blocking your own contract — do not fix it here.
Report it (symptom, location, root cause if you found one) and leave it; the orchestrator
will dispatch a small, fresh agent to resolve it.
