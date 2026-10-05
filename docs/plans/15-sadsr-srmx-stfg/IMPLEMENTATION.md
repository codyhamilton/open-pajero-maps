# Implementation — 15 SADSR SRMX STFG

- Tool: OpenCode DeepSeek Flash (Phase 2 assigned instance); Phase 1 used Codex
- Session: Phase 2 closed on master in worktree `open-pajero-maps-3-90`
- Started: 2026-10-05 ~23:27 Australia/Brisbane
- Worker: Flash pid 2255706; worker commit (rebased) `56a5462`; phase close follows

## Phase 1

### What built

- Evidence note `docs/plans/15-sadsr-srmx-stfg/0x3f00-claim-evidence.md` citing verified `index-idx.md` SADSR201/202 STFG/SRMX census (`7f00`), `search_frame.py`'s `7f 00` → STID..NAME reading, the false `osm_to_address_index.py` "matches the real disc" sentence, and the inconsistent `index_data.py` "NAME absent" gloss of a seven-bit mask.
- `docs/schema/flags.md` SADSR SRMX street STFG row promoted from **unknown** to **verified**, Conflict resolved-as-defect (G wrong; R `0x7f00`+NAME stands); Evidence → the note.
- `docs/schema/UNKNOWNS.md` regenerated via `parser/tools/lint_schema.py --write` (unknown rows 94→93; unverified 508→507); SRMX street STFG left the census.
- Optional documentation-only correction in `parser/kiwiw/index_data.py`: NAME listed as the seventh present field for `7f 00` (decoder behaviour unchanged).
- Unit report `docs/plans/15-sadsr-srmx-stfg/reports/1-01-prove-0x3f00-claim-false.md`.

### Surfaces

Owned: plan 15 evidence + report, `docs/schema/flags.md`, regenerated `UNKNOWNS.md`, comment-only `parser/kiwiw/index_data.py`. Encoder `street_to_srmx_dict` and Phase 2 test expectations untouched (still emit / assert `0x3f00`).

### Deviations

None in scope. Worker first landed on `58bdbfd`; origin advanced with plan 14 Assumption 1 (`f385ef5`) during the run — worker commit rebased onto `origin/master` before phase close (paths disjoint). `gpt-5.1-codex` failed account support; used `gpt-6.1-sol`. Workflow `artifact_feedback` MCP tool unreachable (not in available dynamic namespaces); not posted. Blank `design_id` left intentional; no workflow-service post.

### Verification

- `.venv-rp/bin/python -m pytest -q parser/tests/test_address_extractor.py -k 'srmx_dict_has_required_keys or stfg_bits_correct_for_srmx'`: **2 passed, 30 deselected** (post-rebase recheck).
- `street_to_srmx_dict` still builds STFG bits 0–5 only (`3f 00`); false docstring retained for Phase 2.
- Schema lint regeneration succeeded despite 142 pre-existing missing-path errors (unchanged before/after).
- No plan 14 disc encode, ALLDATA, reseat of 170 / 3-16 / 3-17, PR, or feature branch.

Phase 1 closed.

## Phase 2

### What built

- `parser/osm_to_address_index.py` `street_to_srmx_dict` emits STFG `7f 00` (bits 0–6 incl. NAME) and `"NAME": street.name` (Assumption 2); false "matches the real disc 0x3F00" docstring replaced with R-aligned rationale.
- `parser/tests/test_address_extractor.py`: `test_stfg_bits_correct_for_srmx` expects `0x7F`/`0x00` + NAME; required-keys includes NAME; new `test_srmx_record_roundtrip_bit6_name` synthetic write/parse smoke (16-field SRMX FieldDefs, no disc).
- `docs/schema/flags.md` SADSR SRMX street STFG row: G now emits `0x7f00`+NAME; Evidence/Code cite the new tests. Status remains **verified**.
- Unit report `docs/plans/15-sadsr-srmx-stfg/reports/2-01-emit-0x7f00-with-name.md`.

### Surfaces

Owned: `parser/osm_to_address_index.py`, `parser/tests/test_address_extractor.py`, `docs/schema/flags.md` (Evidence/Code + G-repaired description), plan 15 Phase 2 report. No ALLDATA/disc encode. Plan 04 Phase 3 not closed.

### Deviations

1. Worker committed at `4942167` on tip `742d8ad`; origin advanced with plan 16 Phase 1 (`d15a46f`, `2a9f3a7`) during the run — worker commit rebased onto `origin/master` as `56a5462` before phase close (paths disjoint aside from unrelated plan-16 files).
2. Synthetic STFG FieldDef uses real on-disc type `NORM UB count=2`, not `BF` (a BF-typed STFG crashes `parse_matching_record` bitmap setup).
3. Read-only probe of mounted R disc: SADSR street NAME bit is set but NAME value is **empty** on all sampled records (0/38,120 non-empty in SADSR201). Contradicts Assumption 2 content equality; STFG presence fix retained with `NAME = street.name` per binding DESIGN Assumption 2 / Open Question 1 (follow-up may adjust NAME value only). Not silently changed.
4. Plan folder close-out (collapse) deferred: Phase 2 is the last DESIGN phase, but standing Maps close-out was not run in this commit; parent may follow up if required.

### Verification

- `.venv-rp/bin/python -m pytest -q parser/tests/test_address_extractor.py -k 'srmx or stfg_bits'`: **4 passed, 29 deselected** (post-rebase).
- Full `test_address_extractor.py`: **33 passed**.
- `street_to_srmx_dict` → STFG `[0x7f, 0x00]`, NAME == KYCH == street.name.
- No plan 14 encode, ALLDATA sha change, reseat of 170 / 3-16 / 3-17, PR, or feature branch. Plan 04 Phase 3 stays open.

Phase 2 closed.
