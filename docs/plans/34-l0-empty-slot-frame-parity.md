# L0 empty-slot frame parity (0,541) / (0,562) / (0,563)

Plan 34 found the root cause of, and fixed, plan 29's carried structural
residual. On successor `2ee3456a…`, G indexed L0 frames at (0,541), (0,562)
and (0,563), where the original DVD (R) has empty slots. Each frame was an
encoder empty shell for a cell outside the L0 parcel mask. A general emission
rule now omits such shells, and the new successor disc `4e6b0de7…` is the
oracle disc in force. All three cells are fix-landed, and the plan did what
it set out to do.

## Intent
User request, verbatim:
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Root-cause and fix (or prove a non-deviation for) the plan-29 carried structural residual: on successor `2ee3456a…`, G still has L0 frames at cells **(0,541)** (nameless after O03 drop), **(0,562)**, and **(0,563)** where R has **empty_slot** (no frames) in the same block. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Skip plan 29 close-out (Execute). Do not reseat the O03 name drop.

## Why This Existed
Plan 29 cleared the O03 name_anchor failure. It left G with frames where R
has none:

- a nameless 320-byte padded frame at (0,541);
- 160-byte frames at (0,562) and (0,563).

No K1 check failed on these cells, but under the standing rule frame
occupancy versus an R empty slot is a verifiable DVD deviation. It needed a
root cause.

## What Was Built
**Current oracle:** `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`
(`output/scratch-34/G_new/ALLDATA.KWI`, 1,692,079,168 bytes, protected).
**Historical oracles, kept and protected:** `2ee3456a…` (plan 29) and
`4ed9cd80…` (3-14).

The successor record, with its classified diff scope and sha256-pinned
evidence, is
`docs/plans/04-c-core-orchestration/triage/l0_empty_slot/successor_oracle_4e6b0de7.json`.

**Changed:**

- `parser/build_alldata.py`: `is_empty_shell`, `_empty_shell_header` and
  `_omit_outside_mask_shells`;
- `parser/tests/test_l0_empty_shell.py` and
  `parser/tests/test_l0_frame_witness.py`;
- `docs/design/out-of-span-name-guard.md` § Final outside-mask empty-shell
  omission;
- `docs/OVERVIEW.md`, `docs/provenance.md` and the 3-90 brief's
  successor-pin note.

Lasting tools and evidence are in
`docs/plans/04-c-core-orchestration/triage/l0_empty_slot/`.

### Phase 1 — three cells byte-witnessed
Bounded witnesses on G successor, G historical and R covered L0 block 0
(2,048 cells):

- Both G discs have frames at exactly the three cells.
- R has 2,048 empty slots, each proven by the absent-BMT sentinel, with no
  lookup failures.
- All three successor frames are padded shells with no records. The
  historical (0,541) frame still carried its one name.

### Phase 2 — root cause and fix
**Cause.**

- Each cell lies at ix 0, outside the L0 parcel mask (ix 576..2303).
- Its only input is its own spool record, whose class-2 polygon lies wholly
  west of the cell, so clipping emits nothing.
- `kw_e2` still indexes the encoder's empty shell, and the writer gives it a
  block where R writes the absent sentinel.
- (0,541) also kept plan 29's probe-and-pad extent.

**Fix.** After probe-and-pad, a cell outside its level's `load_parcel_mask`
rectangle whose final frame is exactly the encoder's record-less shell (zero
padding only) is not indexed. Inside the mask nothing changes, and any
record, metadata or unknown layout keeps the frame.

**Measurement.** It ran serially under the wrapper and lock, and every step
exited 0:

- AU encode, 118 s.
- Classified all-level diff vs `2ee3456a…`: 5 changed cells, all
  `removed_outside_mask_empty_shell`, 0 `other`. The cells are L0 (0,141),
  (0,176), (0,541), (0,562) and (0,563). Frames went from 3,954,159 to
  3,954,154, and every other cell's whole-frame multiset is identical.
- R check: 5/5 `empty_slot`.
- Block 0 on the new disc: 2,048 cells empty.
- Live K1 `-j6 --engine c`: failing 0 in every kind.
- Perth: byte-identical at `04be2f6e…`.
- Protected discs and the full spool fingerprint: unchanged before and
  after.

## R empty-slot witness for the out-of-scope cells

(0,141) and (0,176) stay a recorded scope deviation. Each has the same kind of
R byte witness as the three named cells. `r-check` read each one through the
same hardened reader as the Phase 1 R witness (`frame_witness.disc_rows`, the
plan 29 reader) on R `8c2d2027…`. Each row in
`docs/plans/04-c-core-orchestration/triage/l0_empty_slot/phase2/r_check.json`
retains the following, so the proof replays without opening R:

- the L0 blockset entry's offset, raw bytes and sha256, with BMT offset
  `FFFFFFFF` paired with size 0;
- the LMR and PDMDH header reads and their byte references.

| Cell | Blockset | Ordinal | Offset | Raw entry | Entry sha256 | Status |
|---|---:|---:|---:|---|---|---|
| (0,141) | 0 | 345 | 10814 | `0000ffffffff00000000` | `bb1fbe4c6bddd467…` | empty_slot (absent_BMT_sentinel) |
| (0,176) | 0 | 345 | 10814 | `0000ffffffff00000000` | `bb1fbe4c6bddd467…` | empty_slot (absent_BMT_sentinel) |
| (0,541) | 32 | 377 | 11134 | `0020ffffffff00000000` | `4cbaf49a6952d117…` | empty_slot (absent_BMT_sentinel) |
| (0,562) | 32 | 377 | 11134 | `0020ffffffff00000000` | `4cbaf49a6952d117…` | empty_slot (absent_BMT_sentinel) |
| (0,563) | 32 | 377 | 11134 | `0020ffffffff00000000` | `4cbaf49a6952d117…` | empty_slot (absent_BMT_sentinel) |

The two extra cells sit in L0 blockset 0. The named cells sit in blockset 32,
which is also the Phase 1 2,048-cell census block. Both blocksets carry the
absent-BMT sentinel on R.

## Deviations
- 2-01's fix hard-coded the three coordinates. Execute held it and briefed a
  general rule (2-02) instead.
- The Codex fixer seat for 2-02 hit its usage limit. Execute (Grok Bot)
  therefore implemented 2-02 and ran the measurement itself, and disclosed
  this. Review was by an independent clean seat.
- The diff covers two cells beyond the Phase 1 set, (0,141) and (0,176). They
  are in a different L0 block from the Phase 1 census, and they are the same
  class. The general rule removed them; the classified diff names them and
  R-check proves both empty. DESIGN Assumption 1 had scoped extras to the
  censused block only.
- At close-out, the `snapshot` gate was extended to also pin the oracle disc
  in force when it is present.

## Review
The independent terminal review (opencode `deepseek/deepseek-flash`, a clean
context; Codex and Claude were usage-limited) returned
**PASS_WITH_FOLLOWUPS**, with no blocker or high findings. The classification
gate was inspected and found to be a hard gate. Low notes:

- L1: confinement is at the indexed-frame multiset level, not BMT/DSA
  placement.
- L2: SW-corner bytes are exempt from shell matching, by design.
- L3: the OVERVIEW said "identical" rather than "whole-frame multiset
  identical". Fixed at close-out.
- L4: Assumption 1 did not anticipate cross-block extras.
- L5: a new witness test file sits outside the brief's surface list.
- L6: `witnesses/summary.json` is predecessor evidence only.
- L7: IMPLEMENTATION wording about "removing" the never-committed whitelist.

## Residual Risks
- The rule's R basis is the mask contract plus the measured empty slots. An
  R frame at an outside-mask record-less cell would falsify it.
- Block metadata and offset placement are covered only indirectly (K1, block
  census, Perth identity), not by the diff gate.
- This does not close overall DVD parity, Maps completeness or plan 04
  Phase 3.

## Follow-ups
- None specific to this change. The falsifier and the confinement method are
  recorded in `docs/design/out-of-span-name-guard.md`.
- Plan 04 Phase 3 blockers (PSS, the close synthesis) stay in OVERVIEW.

## Post-close regression note (2026-10-06)
The full `parser/tests` run (plan 35 Phase 1, collected at `0f3e530`) found
one failure that plan 34's restricted suite and its review both missed:
`parser/tests/test_parcel_mask.py::test_fill_only_masked_and_absent_cells`.

- **Bisect.** Only this file was run, in throwaway detached worktrees.
  `5182c83^` gives 4 passed. `5182c83` (unit 2-02, the outside-mask
  empty-shell omission) gives 1 failed / 3 passed.
- **Root cause: a stale test, not a code defect.**
  - The synthetic spooled cell (720, 30) carries only an out-of-span name.
    After the name drop, its frame is exactly the encoder's empty shell
    (`build_alldata.is_empty_shell` is True).
  - The cell lies outside the synthetic mask `{0: (700, 702, 10, 11)}`, so
    `_omit_outside_mask_shells` correctly omits it under this plan's rule.
  - The test predates the rule and still asserted that (720, 30) passes
    through, with frame count `n0 + 3`.
- **Fix (test only; `parser/build_alldata.py` unchanged).**
  - The test now asserts that (720, 30) is an empty shell and is omitted.
    The frame count is `n0 + 3 filled − 1 omitted`.
  - The test adds a cell (721, 30) outside the mask with an in-span name at
    its centre. That cell is not a shell, and the test asserts it passes
    through byte-stable. This keeps the original intent.
  - `test_parcel_mask.py` + `test_l0_empty_shell.py`: 45 passed.
- **Lesson.** A behaviour change in `build_alldata` needs the full suite,
  not a restricted one, before close.

## Decisions Worth Keeping
- Emission policy is fixed by a general, R-grounded rule, never a coordinate
  whitelist.
- A successor disc's confinement is proven by classified cell identity, with
  every removal proven absent on R. A new oracle is written to a new path,
  and earlier oracles are never overwritten.
