# Unit 2-01 handoff — G emits SRMX STFG `0x7f00` with NAME

## Completed

- `parser/osm_to_address_index.py` `street_to_srmx_dict` now sets STFG bit 6
  in `_stfg_bytes`, so STFG is bytes `7f 00`, and adds `"NAME": street.name`
  (Assumption 2 — same string as KYCH). The false "matches the real disc's
  `STFG = 0x3F00`" docstring was replaced with the R-aligned `0x7f00` + NAME
  rationale citing `0x3f00-claim-evidence.md`. Bits 7-11 (RPAT, RPNK, RPNF,
  RPNS, RPNC) remain absent.
- `parser/tests/test_address_extractor.py`:
  - `test_stfg_bits_correct_for_srmx` now expects `STFG[0] == 0x7F`,
    `STFG[1] == 0x00`, and asserts `NAME == street.name`.
  - `test_srmx_dict_has_required_keys` now requires `NAME` and checks its
    value.
  - Added `test_srmx_record_roundtrip_bit6_name`, a synthetic write/parse
    smoke using `write_matching_record` + `parse_matching_record` (no
    mounted disc required). It builds a minimal 16-field SRMX `FieldDef`
    list mirroring the verified SADSR201 SRMX `DCTF` frame, round-trips one
    record, and asserts STFG bit 6 set / NAME+KYCH+STID+nibbles survive.
- `docs/schema/flags.md` SADSR SRMX street STFG row (status stays
  **verified**): description now records that G emits `0x7f00` + NAME and
  that the false `0x3F00` claim is repaired; Evidence/Code now cite
  `test_stfg_bits_correct_for_srmx` and `test_srmx_record_roundtrip_bit6_name`.

## Verification

- `.venv-rp/bin/python -m pytest -q parser/tests/test_address_extractor.py
  -k 'srmx or stfg_bits'`: **4 passed, 29 deselected**.
- `.venv-rp/bin/python -m pytest -q parser/tests/test_address_extractor.py`:
  **33 passed**.
- `.venv-rp/bin/python -m pytest -q parser/tests/test_roundtrip_idx.py`
  (disc present): **9 passed**.
- `parser/tools/lint_schema.py` (no `--write`): no "UNKNOWNS.md is stale"
  error; 507 unverified rows, 142 pre-existing missing-path errors. No
  regeneration needed, so `UNKNOWNS.md` was not touched.
- No ALLDATA / disc encode / completeness / plan 14 work. No disc bytes or
  SHA metadata written; ALLDATA sha unchanged (IDX-only helper). No push,
  PR, feature branch, or workflow-service post.

## Deviations, unfinished work, and known problems

1. **STFG field type.** The instruction described the on-disc STFG as
   "2-byte BF". The verified SADSR201 SRMX `DCTF` definition frame actually
   declares `STFG` as `NORM UB count 2` (not `BF`); a `BF`-typed STFG
   returns `bytes` from `search_frame._read_scalar` and crashes
   `parse_matching_record`'s bitmap setup (`bytes([raw])`). The synthetic
   FieldDef list therefore uses the real `UB × 2` type, which decodes to
   `[0x7f, 0x00]` and round-trips byte-identically.

2. **R writes NAME empty (open question 1 answered).** Reading the mounted
   reference disc (read-only) shows that in every SADSR street record the
   NAME bit is set but the NAME value is the **empty string**: all 38,120
   records in SADSR201 (0 with non-empty NAME; STFG `7f00` on 38,119 and
   `ff0f` on the known 1 exception), and the first records of SADSR202-207
   likewise carry `NAME == ""`. This contradicts Assumption 2 (`NAME ==
   KYCH == street.name`). Per the binding instruction this unit still emits
   `NAME = street.name`; the STFG-bit defect that plan 15 targets is
   repaired, but byte-exact R match on NAME content is **not** achieved and
   needs a follow-up decision (DESIGN Open Question 1 anticipated this:
   "if distinct, a follow-up adjusts NAME only"). No committed master
   evidence distinguishes the two, so the assumption was retained rather
   than silently changed.

3. The single SADSR201 record whose STFG is `ff0f` remains an out-of-scope
   named residual (DESIGN Open Question 2).

No unit work remains beyond items 1-2, which are parent-decision items.
Plan 04 Phase 3 is not closed, plan 14 is untouched, and no `Workflow-Phase`
trailer was added (parent owns the phase close).
