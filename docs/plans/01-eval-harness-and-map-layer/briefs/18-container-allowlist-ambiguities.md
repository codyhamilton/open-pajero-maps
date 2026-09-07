# Brief: 18 — Resolve unit 04's three container-allowlist ambiguities (ad hoc)

Consumer: implementation worker. This brief was authored by the orchestrator (not `refine`)
to resolve three ambiguities unit 04 reported and deliberately did not resolve, deferred
until unit 06's `DESIGN.md` existed to ground the header-field questions. It is not part of
the original 01-15b dispatch list; dispatch it independently.

Owned paths: `parser/harness/bytediff.py`, `parser/harness/checks/container.py`, the
`container_allowlist` key of `parser/refdata/harness.json` (only that key), and
`parser/tests/test_harness_container.py`. Do not touch other checks or other
`harness.json` keys. Commit to the current branch when done evidence passes; push.
Depends on: 04 (done, `c25c55d`), 06 (`DESIGN.md`, done — grounds ambiguity (b) below).
Runs alongside: 17 (disjoint file), 09, 10.

## Required reading, in order

1. `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`, "Unit 04 — Container
   byte-diff check with allowlist", the "Reported ambiguities" paragraph — the three items
   this brief resolves:
   (a) whether a `media_version` field should be allowlisted;
   (b) MHT absent-layer handling (sentinel vs. `R`'s pointer) is folded into one blanket
   rule rather than driven per-layer from `harness.json`'s config;
   (c) `record_size`/`trailing_padding` field-name interpretation may not match the design
   doc's exact intent.
2. `docs/design/target-disc.md` — "Evaluation: the offline oracle", **Container byte-diff**
   row (the settled contract unit 04 implemented against) and any section naming
   `media_version`, per-layer absence config, or `record_size`/padding fields by name.
3. `parser/harness/bytediff.py` and `parser/harness/checks/container.py` as landed by unit
   04 — read the current allowlist logic and the named-field-to-byte-range mapping in full.
4. `parser/refdata/harness.json`'s current `container_allowlist` value and whatever
   per-layer "absent in G" config already exists elsewhere in that file (unit 04's brief
   references "layers the config lists as absent in `G`" — find that key).
5. `parser/kiwiw/volume.py` — `parse_volume_header`, `parse_volume_header_extras`,
   `parse_management_header_table`, `parse_pdmdh` (the field offsets/names this brief's
   fixes must stay consistent with).
6. `docs/plans/01-eval-harness-and-map-layer/DESIGN.md` section 2 — the Map Frame header
   field table's precedent for how a spec-named field vs. an inferred one is documented with
   a confidence level; use the same style for whatever you resolve or leave open here.

## Goal

Settle each of the three ambiguities against the spec/design doc, or confirm it cannot be
settled without information this unit doesn't have and say so explicitly rather than
guessing.

## Contract

Not fully settled — this is a small investigation per ambiguity, same posture as unit 04's
own brief. For (a): check whether the volume/MHT spec names a `media_version` field
distinct from the already-allowlisted format/data-version and disk-title strings; if it
exists and is legitimately variable between `R` and `G`, allowlist it with a `reason`; if it
doesn't exist as a named field, report that and leave the allowlist as is. For (b): the
current code folds "layer absent in G" handling into one blanket rule; determine whether
`harness.json` already has (or should gain) a per-layer flag driving this instead, and if
so wire `container.py`'s allowlist logic to read it rather than hard-coding the blanket
rule — but only if this doesn't require touching layers/config outside this brief's owned
`container_allowlist` key (if it does, report that as a scope conflict rather than widening
your owned paths silently). For (c): check the PDMDH's actual field name in
`volume.py`/spec against the allowlist's `record_size`/`trailing_padding` naming; rename in
the allowlist (not in `volume.py`) if the spec's name differs, or confirm the current naming
is correct and close the ambiguity with that evidence.

## Changes

Whatever each investigation concludes: allowlist entries added/renamed with accurate
`reason` strings, and `container.py` logic changes only if (b)'s per-layer wiring is in
scope per the contract above. Update `test_harness_container.py` for any behavior change.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.
- `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated /run/media/codyh/464210-8480/ALLDATA.KWI --checks container` (self-check against the mounted reference disc) → PASS, confirming the resolved allowlist doesn't regress the real-disc case.

## Report back

For each of (a), (b), (c): what you found, what you changed (or why you left it
unresolved and what's blocking), and evidence. **Do not resolve contradictions
silently — report them.** If (b) turns out to require touching files outside this brief's
owned paths, stop and report that rather than editing them.
