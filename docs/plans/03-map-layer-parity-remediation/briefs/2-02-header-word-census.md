# Brief: 2-02 — Header-word census and rule (words 0, 6, 7, 9, 10, 11)

Consumer: implementation worker; result consumed by 2-04 and Phase 4 (header word generator, `header_words` check).
Owned paths: `parser/tools/header_word_census.py` (new), `parser/refdata/profile/coord_scale.json` (add the `header` section only; do not alter `ranges`/`class_rule`), `parser/tests/test_header_word_census.py` (new). Touch nothing else.
Commits: Commit to the current branch when done evidence passes.
Depends on: 2-01 (class rule and division state keys, and the file itself).
Runs alongside: 2-03.
Budget: 6 files to read, about 300 lines to change, 40 tool turns. Past the budget, stop: write a handoff under this brief's name in `IMPLEMENTATION.md` (done, not done, what you learned), commit if this brief commits, and report `over budget`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — Native encoding model Contract (header-word lines, exemption list); Phase 2 Outcome; Assumption Ledger item on word 0.
2. `docs/plans/03-map-layer-parity-remediation/FINDINGS.md` — F2.
3. `parser/kiwiw/parcel.py` — `decode_map_frame_header`; `parser/harness/walk.py` — `iter_parcels`.
4. `docs/schema/map-frame.md` — header rows (dipid, word 7, words 9-11) and their statuses.
5. `parser/refdata/profile/coord_scale.json` (from 2-01) — class keys.
6. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — Carried item 2 (pointers).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

A rule predicting R's Map Frame header words 0, 6 (`dipid`), 7, 9, 10, 11 from (level, parcel class, division state, position where the spec says so), validated on held-out parcels at >= 99% per word, with every exception explained.

## Contract

Cited: "Header words are never zero-filled: each is generated from the model or proven zero in R for that class"; "`n_intersections`, `route_planning_level`, `n_additional_data`, ext-frame slots and `nregion` are WP2-owned ... listed with R's census values in `coord_scale.json`'s header section" (DESIGN, Native encoding model); "R's word 0 differs from the first data-slot offset in 42 of 939 sampled leaves" (Phase 2 Outcome). Reference disc R is mounted read-only at `/run/media/codyh/464210-8480`; the current generated disc G is `output/ALLDATA.KWI` (repo root). Python: `.venv-rp/bin/python`. Never edit worktree copies under `.claude/worktrees/`. Census tools read R only through `parser/harness/` reading paths and must not import writer modules. Output is deterministic (sorted keys, no timestamps).

## Changes

- Census every header word over all R parcels, keyed by (level, class, division state); record value distributions.
- Split parcels deterministically into a fit set and a held-out set (fixed rule, e.g. hash of block/parcel id; record it). Derive the rule on the fit set only; report accuracy per word on the held-out set. Word 6: `dipid` structure (`11` undivided; `01`+type+position divided, per DESIGN). Word 0: header size (160/166/172 B) and its rule.
- Explain each of the 42 word-0 exceptions (re-find them: they are in the L6 sample where word 0 != first data-slot offset; if the sample is not recoverable, census all levels and explain every disagreement). "Explained" means a stated structural cause (e.g. extra header slots, different header size class) shown on the parcels, or the rule is extended to predict them. Unexplained residue above 1% of the held-out set is `blocked`.
- Write the `header` section: per-word rule/table, held-out accuracy, exceptions with cause, and the WP2-exempt words (`n_intersections`, `route_planning_level`, `n_additional_data`, ext-frame slots, `nregion`) with R's census values.
- Carried item 2 (strict `pointers` FAILs R on 65/4000 out-of-buffer idx>=3 targets): classify those 65 (which level, class, division state, header words) using the census; record the classification in your report and in `header` under `pointer_nonframe_targets`. Do not change the check; Phase 9 owns its allowance.

### Keep untouched

`parser/kiwiw/*`, `parser/harness/*`, `parser/refdata/harness.json`.

## Done evidence

- `.venv-rp/bin/python -m pytest parser/tests/test_header_word_census.py -q` passes (synthetic fixtures, determinism test).
- Tool run twice, `sha256sum` of `coord_scale.json` identical; `ranges` section byte-identical to 2-01's.
- Report lists held-out accuracy for each of words 0, 6, 7, 9, 10, 11 (each >= 99% or `blocked`), and the table of word-0 exceptions with causes.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. If the evidence contradicts the coordinate-range hypothesis, report `blocked` with the numbers: this phase is a gate and the design is bounced, not patched.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

