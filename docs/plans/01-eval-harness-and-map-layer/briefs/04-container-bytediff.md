# Brief: 04 — Container byte-diff check with allowlist

Consumer: implementation worker.
Owned paths: `parser/harness/checks/container.py` (new), `parser/harness/bytediff.py` (new),
`parser/tests/test_harness_container.py` (new), and the `container_allowlist` key of
`parser/refdata/harness.json` (only that key). Do not touch anything else.
Commit to the current branch when done evidence passes; push.
Depends on: 02.
Runs alongside: 03, 05, 07.

## Required reading, in order

1. `docs/design/target-disc.md` — "Evaluation: the offline oracle", row **Container
   byte-diff**: "The volume header, MHT, PDMDH, LMR tables and copy-through frames of `G`
   differ from `R` only in an allowlisted set of fields (build stamp, sizes, sector
   addresses)."
2. `docs/plans/01-eval-harness-and-map-layer/PLAN.md` — acceptance bullet "The container
   byte-diff check passes with every difference inside the allowlist."
3. `parser/kiwiw/volume.py` — `parse_volume_header`, `parse_volume_header_extras`,
   `parse_management_header_table`, `parse_pdmdh` (field offsets are the allowlist's
   coordinate system).
4. `parser/kiwiw/volume_writer.py` — the field layout the writers use (read only; do not
   import it from the harness).
5. `parser/harness/` as landed by unit 02.

## Goal

Make every byte of the container layer accountable: a generated disc's header, MHT, PDMDH
(with LMR/BSMR/BMT) and the record-29 frame may differ from the reference only where a
named field is allowed to.

## Contract

The design-doc row above is settled. Allowlisted fields are named, not ranged by hand: an
allowlist entry is `{"region": "volume_header" | "mht" | "pdmdh", "field": "<name>",
"reason": "<why it may differ>"}`, and the check translates names to byte ranges using the
same offsets `volume.py` decodes from. The initial allowlist is the design doc's three
classes: build stamp / data version / disk title strings, sizes, sector addresses (every
`dsa`/`size` in MHT entries and BMT entries, the PDMDH `total_size`/padding), plus BSMR
`bmt_offset`/`bmt_size` and MHT entries for layers the config lists as absent in `G`
(their sentinel vs. `R`'s pointer). Anything else that differs is a FAIL that prints
offset, length, `R` bytes, `G` bytes and the nearest decoded field name.

## Changes

### `parser/harness/bytediff.py`

`field_map(region, parsed) -> list[(name, start, end)]` for the three regions, built from
the decoder's offset constants (add named constants locally if `volume.py` uses literals;
do not edit `volume.py`). `diff_regions(r_bytes, g_bytes, fields, allow) -> list[Diff]`
where each `Diff` is classified `allowed` or `violation`. For the PDMDH region compare the
full blob at `R`'s size; if `G`'s PDMDH differs in length that is itself a violation unless
the only difference is trailing zero padding.

### `parser/harness/checks/container.py`

`container`: reads both files' header, MHT, PDMDH blob and the record-29 frame; FAIL on any
violation; details list allowed diffs (count per field) and violations (first 50). NA if
`--reference` was not given.

### Tests

Reference-independent: build two synthetic containers in-test (`alldata_writer.build_alldata_kwi`
with different coverage or disk title) and assert the diff classifies the title as allowed
and coverage as a violation; assert a one-byte change inside an LMR is a violation naming
the LMR field.

## Done evidence

- `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated /run/media/codyh/464210-8480/ALLDATA.KWI --checks container` → PASS with zero diffs.
- The same against the current `output/ALLDATA.KWI` (any single-level build) → FAIL, and the violations name LMR/BSMR fields rather than raw offsets only.
- `.venv-rp/bin/python -m pytest parser/tests -q` → all pass.

## Report back

A short summary: what you changed, the final allowlist, anything you deviated from in this
brief and why, and any contradiction you found between this brief and the contracts it
cites. **Do not resolve contradictions silently — report them.**
