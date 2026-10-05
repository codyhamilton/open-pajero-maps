# Implementation — 21-r-empty-name-vs-g-street-name

- Tool: Open Pajero Maps Execute
- Start: 2026-10-06 Australia/Brisbane
- Assigned instance preference: OpenCode DeepSeek Flash; executor implemented Phase 1 directly (bounded edit).

## Phase 1

### Units

- `1-01-empty-name` — street_to_srmx_dict NAME=""; tests + flags.md presence vs content

### Outcomes

- `street_to_srmx_dict`: STFG still `0x7f00` (bits 0–6); `KYCH=street.name`; `NAME=""`; docstring retires plan 15 Assumption 2; cites plan 15 residual / plan 21.
- Tests (`test_srmx_dict_has_required_keys`, `test_stfg_bits_correct_for_srmx`, `test_srmx_record_roundtrip_bit6_name`): empty NAME, key present, bit 6 set, KYCH=street name; fail if NAME equals non-empty street under 7f00.
- `docs/schema/flags.md` SADSR SRMX STFG row: presence=`0x7f00`; content=empty NAME on dominant SADSR201; G emits empty NAME.
- `docs/schema/index-idx.md` STFG one-liner: bit 6 = NAME present (value may be empty).
- Evidence note: `EVIDENCE-NAME-EMPTY.md` (offline cite only; no new disc bytes).
- Tests: `PYTHONPATH=parser .venv-rp/bin/python -m pytest parser/tests/test_address_extractor.py -q` → **33 passed** (shared `/home/codyh/workspace/open-pajero-maps/.venv-rp`; no `.venv-rp` created in this worktree).
- No STFG regression to `0x3f00`. No ALLDATA encode. No Phase 3 close. No reseat 170/3-16/3-17. `output/scratch-3-11/G_new` untouched.
