# Plan 34 — Independent Review

## Verdict

**PASS_WITH_FOLLOWUPS**

## Seat

Independent terminal reviewer: opencode `deepseek/deepseek-flash`, a clean context that
did not build this plan (Codex and Claude were at usage limits until 11:19 / 11:20
AEST). This note was added by Execute.

## Reviewed SHA

`4ab27e8` (plan-34 Phase 2 close, the plan-34 tip). `HEAD` is `7913160` (later,
interleaved plan-30 work); `4ab27e8` is an ancestor and no commit after it
touches the plan-34 folder, `parser/build_alldata.py`, or
`parser/tests/test_l0_empty_shell.py`.

## Phase outcome assessment

### Phase 1 — three cells byte-witnessed; block census recorded — **MET**

- Three cells `(0,541)`, `(0,562)`, `(0,563)` byte-witnessed on **both** G discs:
  - `g_successor` `2ee3456a…`: `(0,541)` 320 B `967b1d86…`; `(0,562)` 160 B
    `e22e27df…`; `(0,563)` 160 B `0126fc2d…`.
  - `g_historical` `4ed9cd80…`: `(0,541)` 320 B `3c927c6b…`; `(0,562)`/`(0,563)`
    identical `e22e27df…`/`0126fc2d…`.
- R (`8c2d2027…`) has **0 frames**, block-0 census `{empty_slot: 2048}`, reason
  `absent_BMT_sentinel`, **0 lookup failures** (`witnesses/r.json`,
  `summary.json`, `phase1_note.md`).
- Block census: G successor and historical each have exactly 3 frames at the
  three cells; `extra_cells: []`; 2,048-cell block, 0 lookup failures.
- `lookup_failed` was forbidden as a publication condition (`frame_witness.py`
  via plan-29 hardened reader); none present.

### Phase 2 — root cause proven; fix-landed — **MET**

- Per-cell cause recorded (`phase2_cause.md`): one shared cause (own out-of-span
  class-2 polygon clips to zero records; own-row existence still indexes an
  empty background-header frame via `descriptor.py` / `_e2.c` / `_cenc.c`), plus
  for `(0,541)` the plan-29 O03 name-drop + probe-and-pad preserving a 320-byte
  shell. `disposition.json` `conflict_open_count: 0`, `plan29_residual_discharged:
  true`; all three cells `fix-landed`.
- New successor: `output/scratch-34/G_new/ALLDATA.KWI`, sha
  `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`
  (1,692,079,168 B), recorded as successor of `2ee3456a…` in
  `successor_oracle_4e6b0de7.json` (`predecessor_preserved: true`,
  `from_path_untouched`, `phase3_closed: false`).
- Classified diff vs `2ee3456a…`: **5** changed cells, all
  `removed_outside_mask_empty_shell`, **0 other** (`changed_cell_count: 5`,
  `counts_by_level {"0": {...: 5}}`, `other_cells: []`, `pass: true`); frame
  count 3,954,159 → 3,954,154.
- R check: 5/5 `empty_slot`, 0 failures, R pin checked before and after.
- K1 (`quantisation_roundtrip.py -j6`, engine c) retained record: exit 0,
  `failing: 0` (`run_p2b.log`, `phase2/k1.json`).
- Perth unchanged: `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`
  (classified diff 0 changed cells).
- Protected before == after (`protected_before.json == protected_after.json`,
  4 discs + 14-file spool + fingerprint `328c064e…`).
- Provenance/OVERVIEW notes landed in `4ab27e8`; **no** Phase 3 close claim
  (`phase3_closed: false`, OVERVIEW "review and close-out are pending").

All measured claims in the review brief reproduce against retained evidence:
successor pair, 5 cells all `removed_outside_mask_empty_shell` / 0 other,
`(0,141)`+`(0,176)` extra beyond the Phase 1 three, R 5/5, block-0 2,048 empty,
K1 failing 0, Perth byte-identical, protected before==after. All 12
successor-oracle evidence hashes re-hash clean; all `runs/*.json` exit 0.

## Findings

No blocker or high-severity findings. The fix is general, structurally sound,
and not coordinate-fitted.

### Classification gate — inspected closely, **no defect** (verified, not a finding)

The classification line reads `SELECT n,sha,shell FROM old WHERE level=? AND
ix=? AND iy=?`, so the `all(r[2] for r in old)` test is `is_empty_shell`, **not**
the `iy` coordinate (the `iy` column is filtered out of the projection). The
whole-frame multiset comparison (`GROUP BY level,ix,iy,n,sha` + two-way
`EXCEPT`, no level filter) lists every changed cell on every level. A non-shell
removal, an added frame, or an inside-mask removal all classify `other` → the
gate fails (`passed = not other and (phase1_removed or not require_phase1)`). The
gate cannot pass with an unclassified change. `outside()` raises `ValueError`
when a changed cell's level has no mask (fail-closed). The `r-check` fails on
`lookup_failed`/any non-`empty_slot` status, on a resolved R frame, on any
non-L0 removal, and when the L0 removed set is short (`len(rows) ==
len(cells)`). This is a correct, hard gate.

### Low

- **L1 — Diff gate is frame-multiset-only.** `phase2_gates.py diff` proves
  confinement at the level of indexed-frame bytes (offsets deliberately
  ignored); it does not by itself attest block metadata (BMT/DSA), offset
  placement, or any non-indexed byte. This is the design's stated contract
  ("whole-frame multiset identical"), and the block-0 census, live K1 roundtrip,
  Perth identity, and protected-spool equality mitigate it. Listed as a
  **follow-up** (residual risk), no fix.
- **L2 — SW-corner bytes 2–4/6–8 unconstrained.** `is_empty_shell`
  (`parser/build_alldata.py:266`) is otherwise byte-exact against the computed
  shell (declared length, `raw[10:12] == cell`, metadata+directory+background,
  zero-only trailing padding); it intentionally exempts the free SW-corner
  bytes, per its docstring. Accepted by design; **follow-up**/note.
- **L3 — OVERVIEW wording slightly broader than the proof.** `docs/OVERVIEW.md`
  (`4ab27e8`) says "Every other cell is identical"; the gate proves whole-frame
  *multiset* identity (offsets may relocate) and R-empty-slot for removals. The
  design doc and oracle scope this correctly. **Follow-up** for the orchestrator
  (OVERVIEW is out of my edit scope).
- **L4 — Assumption 1 under-anticipated cross-block extras.** DESIGN
  Assumption 1 scopes extras to "in that block" (the Phase-1 census block), but
  `(0,141)`/`(0,176)` lie in a different L0 block. Treatment is honest and in
  scope: the pre-authorized 2-02 brief (committed `f965e79`, before the code)
  mandates a general rule and requires the diff to list every changed cell; the
  extras are named in `disposition.json` `observed_diff_scope`, listed in the
  oracle (`additional_cells_beyond_phase1`), and covered by the design-doc
  amendment. **Follow-up**/ledger note, no remediation.
- **L5 — New test file outside the enumerated surfaces.**
  `parser/tests/test_l0_frame_witness.py` (new, `a881021`) is not in the review
  brief's surface list, but it is Phase-1 witness tooling, not a change to an
  existing checker or tolerance. Note; no action.
- **L6 — Phase-1 summary remains old-pin evidence.** `witnesses/summary.json`
  reports the predecessor block-0 census (`resolved: 3`); the post-fix witness
  is `witnesses/g_successor_4e6b0de7.json`. summary.json must not be cited as
  post-fix evidence. Note; no action.
- **L7 — Minor doc wording.** `IMPLEMENTATION.md` says the 2-01 whitelist
  `_L0_EMPTY_SLOT_CELLS` "is removed"; it was never committed (2-01 output held;
  `f965e79`), so the code never contained it. True in effect (no whitelist in
  the final builder), but the wording implies a removal hunk that does not
  exist. Note; no action.

No remediation briefs were warranted. No structural defect stands.

## Intent and ledger assessment

- **Intent match.** The verbatim intent — root-cause the plan-29 carried L0
  empty-slot residual at `(0,541)`/`(0,562)`/`(0,563)` and either fix or prove
  non-deviation, never relabel, no Phase 3 close — is met. The fix is a general
  per-level, outside-mask, undivided-cell, exact-empty-shell omission applied
  **after** plan 29's probe-and-pad and the declined-row check
  (`parser/build_alldata.py:381`), using `load_parcel_mask()`'s per-level
  rectangle. No hardcoded coordinates remain in production code; the 2-01
  whitelist is absent (it was never committed).
- **Ledger.** Assumption 2 (nameless padded frames not accepted as
  non-deviation) held; Assumption 3 (new successor oracle, predecessor
  preserved) held. Assumption 1's "in that block" wording is the only
  ledger mis-scope (L4), handled transparently.
- **Standing rules.** No tolerance loosened; no existing checker changed (the
  new gate `phase2_gates.py` is a plan-34 tool, exercised by
  `test_l0_empty_shell.py`); no relabel; protected discs and spool untouched; no
  3-90; no Phase 3 close claim; no reseat of 170 / 3-16 / 3-17; plan-31 review
  and plans 30 untouched.

## Plan-sufficiency judgment

The design was sufficient to determine intent and derive QA: phase outcomes were
provable, the assumption ledger named the scope risk, and Phase 2's "approach
open" correctly produced the `2-02` brief, which pre-authorized both the general
rule and the contract amendment later landed in the design doc. The one gap —
the DESIGN's "diff confined to those frames/cells" wording is narrower than the
general rule the design also licensed, requiring the amendment to remain
satisfiable — is a documentation seam, not a QA insufficiency.

## Verification performed (light only)

- Read-only over committed JSON/TSV and retained `output/scratch-34/` logs
  (`run_p2b.log`, `runs/*.json`, `phase2/*.json`, `witnesses/*`).
- `python -m pytest parser/tests/test_l0_empty_shell.py
  parser/tests/test_name_drop_guard.py parser/tests/test_build_wiring.py
  --basetemp output/scratch-34/review/tests -q` → **53 passed** (project venv
  `.venv-rp`; system `python` absent). Not committed.
- No K1 run, no diff, no encode, no disc/spool open, no full suite.

## Residual risks

- Confinement evidence is frame-multiset scope (L1).
- R evidence is bounded: the 5 removed cells plus the block-0 census, not a full
  R roam; the rule rests on the `load_parcel_mask` contract (brief 26c).
- `is_empty_shell` depends on encoder shell-format constants and the documented
  free SW-corner bytes (L2).

## Changes made in review

- **None.** No mechanical correction was required inside the plan-34 folder or
  `parser/tests/test_l0_empty_shell.py`. No file was edited; this `REVIEW.md` is
  the only addition and is left uncommitted.

## Accumulation

Initial review at `4ab27e8`.
