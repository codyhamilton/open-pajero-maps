# Report: 2-02 — general outside-mask empty-shell rule

Seat: the Codex `gpt-6.1-sol` (high) fixer seat died at the Codex usage limit
(~08:23 AEST) before producing a usable diff. Execute (Grok Bot) implemented
the brief and ran the guarded measurement itself; this is disclosed here and in
IMPLEMENTATION. The independent review must be a fresh seat.

## Change

- `parser/build_alldata.py`: `is_empty_shell` / `_empty_shell_header` recognise
  the exact record-less `encode_common` frame for a cell and level, allowing only
  zero padding. `_omit_outside_mask_shells` drops an undivided cell outside its
  level's `load_parcel_mask` rectangle when its final frame (after plan 29's
  probe-and-pad and the declined-row check) is that shell. The 2-01 whitelist is
  removed. Nothing changes without a mask or inside the mask.
- `phase2_gates.py`: classified all-level `diff` (every changed cell listed;
  passes only with 0 `other`), `--old-sha`, `--no-require-phase1`, and `r-check`
  (each removed L0 cell must be `empty_slot` on R through plan 29's hardened
  reader; non-L0 removals fail closed).
- Tests: `parser/tests/test_l0_empty_shell.py` (+ name-drop guard and build
  wiring): 53 passed (`--basetemp output/scratch-34/tests-p2b`).

## Guarded measurement (`output/scratch-34/run_p2b.{sh,log}`, all exit 0, ALLDONE 10:00:43 AEST)

| Step | Result | Evidence |
|---|---|---|
| Snapshot before/after | byte-identical (4 protected discs + full spool fingerprint) | `phase2/protected_{before,after}.json` |
| AU encode `-j4` | 118 s, peak RSS 3.0 GiB; new disc `output/scratch-34/G_new/ALLDATA.KWI` | `phase2/runs.json` |
| AU sha (first and final) | `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`, 1,692,079,168 B (25,984 B smaller than `2ee3456a…`) | `phase2/successor_sha.json`, `successor_final_sha.json` |
| Classified diff vs `2ee3456a…` | 5 changed cells, all `removed_outside_mask_empty_shell`, 0 `other`; frames 3,954,159 → 3,954,154 | `phase2/au_cell_diff.json` |
| R check | 5/5 `empty_slot` (absent BMT sentinel) on `8c2d2027…`, 0 lookup failures | `phase2/r_check.json` |
| Block-0 re-witness + check | 2,048 cells empty on the new disc | `witnesses/g_successor_4e6b0de7.json`, `phase2/block_check.json` |
| K1 `-j6 --engine c` | failing 0 for every kind, pass true (83 s) | `phase2/k1.json` |
| Perth encode + sha + diff | `04be2f6e…` byte-identical, 0 changed cells | `phase2/perth_sha.json`, `phase2/perth_cell_diff.json` |

Removed cells (L0, ix 0, all outside the L0 mask ix 576..2303):

| Cell | Old frame | Phase 1 cell |
|---|---|---|
| (0,141) | 160 B `6445327e…` | no (different L0 block from the Phase 1 census) |
| (0,176) | 160 B `40f561d1…` | no (different L0 block) |
| (0,541) | 320 B `967b1d86…` (padded shell after plan 29's name drop) | yes |
| (0,562) | 160 B `e22e27df…` | yes |
| (0,563) | 160 B `0126fc2d…` | yes |

The two extra cells are the expected consequence of a general rule rather than a
whitelist: they are the same class (outside-mask exact empty shells), the
classified diff names them, and `r-check` proves R has no frame there. They sit
in an L0 block outside the Phase 1 2,048-cell census, which is why Phase 1 did
not list them.

## Verdict

All three Phase 1 cells: **fix-landed**. Conflict-open: 0. New successor oracle
recorded at `successor_oracle_4e6b0de7.json`; `2ee3456a…` is preserved and not
overwritten. No Phase 3 close.

## Residuals

- The rule's R basis is the mask contract in `load_parcel_mask` plus the
  measured R empty slots; a future R witness with a frame at an outside-mask
  record-less cell would falsify it (`phase2_cause.md` § Emission rule).
- Plan 31/32 live results were measured on `2ee3456a…`; K1 on `4e6b0de7…`
  is again failing 0 for every kind, so the live pinned set stays ∅.
