# Implementation — 15 SADSR SRMX STFG

- Tool: Codex (assigned instance; model `gpt-6.1-sol` after `gpt-5.1-codex` rejected by account)
- Session: Phase 1 closed on master in worktree `open-pajero-maps-3-90`
- Started: 2026-10-05 ~23:10 Australia/Brisbane
- Worker: Codex pid 2035132; worker commit (rebased) `b46132f`; phase close follows

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
