# Brief 34 - Use the u16 frame ceiling as the only size limit (kickoff)

## Decision (user, 2026-09-19)
The only known hard limit is the Map Frame header's u16 word-count field: 131,070 bytes
(`build_alldata.U16_MAPFRAME_BYTE_CEILING`). There is no reason to expect hardware limits that
differ per level or per kind; any real limit would come from the header structure and, above
that, memory. R's per-level `mapframe_size.max` and per-kind `frame_kind_max_bytes` are
observations of R, not limits, so they stop being build budgets.

## Change
1. `parser/build_alldata.py`: `_load_level_thresholds` and `_load_level_kind_budgets` must
   yield 131,070 for every level (and every kind). Remove the R-derived values rather than
   keeping a flag. Keep the CLI surface otherwise unchanged.
2. `parser/kiwiw/divide.py`: trimming (`_trim_kinds`, `_shrink_priority`, pin release) only
   fires when a frame would exceed 131,070. Keep the trim priority order. Keep the
   `trimmed_items` and `halo_names` manifest keys.
3. Harness `envelope` check (`parser/harness/checks/`): the per-kind sub-frame-maximum rows
   compared against R maxima become: pass iff `max <= 131,070`; report R's maximum alongside
   as context only. parcel_count and name_count ratio rows stay as they are.
4. Update tests in `parser/tests/test_divide.py`, `test_build_alldata.py` and the envelope
   check tests. Suite must pass with `.venv-rp/bin/pytest`.
5. Do NOT re-extract: `output/spool` stays valid. Assembly only.

## Environment (this is a worktree)
`.venv-rp/`, `output/` and `parser/refdata` inputs are untracked and live in the main checkout
(`/home/codyh/workspace/open-pajero-maps`). Symlink `.venv-rp` and `output` into the worktree
(both are gitignored; confirm with `git status` that nothing new becomes tracked). Never push
to master: commit on branch `worktree-brief-34-ceiling-only` and push that branch.

## Kickoff (this worker)
Implement 1-4, commit and push the branch. Then start the assembly in the background using
the brief 33b command (log dir `/tmp/wp1-unit34-logs/`; copy `output/report.json` to
`/tmp/wp1-unit34-prior-report.json` and record the old ALLDATA.KWI sha256 first). Record command,
log path and expected duration (~11-17 min) in IMPLEMENTATION.md under "Unit 34 kickoff",
commit and push, and END. Do not wait or poll. A fresh worker verifies (brief 34b).

## Watch for
- Fewer divided parcels: parcel_count ratios may drop; report them.
- Level 8 max frame was 127,142 and may approach 131,070. Report per-level max frame.
- Output size vs the 4.7 GB budget (was ~30% capacity).
- Update the PLAN.md deviation table only in the verify unit, not here.
