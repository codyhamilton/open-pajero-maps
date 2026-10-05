# Unit 1-01 handoff

## Completed

- Added `docs/plans/15-sadsr-srmx-stfg/0x3f00-claim-evidence.md`, quoting
  the committed verified SADSR201/202 STFG/SRMX census, the reader's
  `7f 00` → STID..NAME interpretation, the false generator sentence, and
  the inconsistent legacy "NAME absent" gloss. The reference evidence
  wins; the generator claim is resolved as a defect.
- Changed the SADSR SRMX street STFG row in `docs/schema/flags.md` to
  `verified`, explicitly naming the defect and pointing to the note.
- Regenerated `docs/schema/UNKNOWNS.md` with
  `python3 parser/tools/lint_schema.py --write`. Unknown rows decreased
  from 94 to 93; total unverified rows decreased from 508 to 507. Only
  the resolved SRMX row left the generated census.
- Applied the optional documentation-only correction in
  `parser/kiwiw/index_data.py`: NAME is the seventh present field for
  `7f 00`.

## Verification

- `.venv-rp/bin/python -m pytest -q parser/tests/test_address_extractor.py
  -k 'srmx_dict_has_required_keys or stfg_bits_correct_for_srmx'`:
  **2 passed, 30 deselected**. Existing expectations were not edited;
  the current generator still emits bytes `3f 00`.
- `git diff --check`: passed.
- Compared schema lint results against committed `flags.md`: the same
  142 missing-path errors occur before and after this change. Verified
  generated content equals the linter's renderer, with precisely one
  fewer unverified row and no SRMX street STFG entry.
- Confirmed `parser/osm_to_address_index.py` and all tests are unchanged.
  No disc bytes or SHA metadata were written; the disc SHA is unchanged.

## Deviations, unfinished work, and known problems

No scope deviations. No unit work remains. The optional legacy docstring
correction was needed to remove the contradictory six-field gloss.

The schema linter exits 1 because of 142 pre-existing missing-path
references (including absent synth/divide modules, tests, and a generated
disc artifact). Regeneration succeeds despite these errors. No missing
artifact was created and no unrelated reference was repaired.

The generator's `3f 00` output and false docstring remain for Phase 2 to
repair. This work neither closes Phase 3 nor changes Phase 2 tests. Plan 14,
ALLDATA, disc encoding, and completeness work were not touched. No workflow
service action, phase-closing trailer, push, or PR is part of this unit.
