# Brief: 2-02 — replace the hard-coded three-cell omission with a general outside-mask empty-shell rule

Consumer: Codex `gpt-6.1-sol` (high), sandboxed. Fixer seat (fresh; not the 2-01 worker).
Owned paths: `parser/build_alldata.py` (the plan-34 omission only), `parser/tests/test_l0_empty_shell.py`, and `docs/plans/34-l0-empty-slot-frame-parity/` (`phase2_cause.md`, `phase2_commands.md`, `phase2_gates.py`, `frame_witness.py` if needed, `disposition.*`, `phase2_note.md`, new report `reports/2-02-general-rule.md`).
Touch nothing else. Commits: none.

## Why

Unit 2-01 (uncommitted) proved the cause well (`phase2_cause.md`): the three cells sit at ix=0, **outside** the L0 parcel mask (ix 576..2303, iy 0..2143); each exists only because the spool has an own record whose class-2 polygon lies wholly west of the cell; clipping emits nothing; `kw_e2` indexes the 158-byte empty shell anyway; the writer then allocates a block/BMT where R writes the absent sentinel. But its fix, `_omit_witnessed_l0_shells`, hard-codes `((0,541),(0,562),(0,563))` in the production builder. Execute will not land a coordinate whitelist: it is a special case fitted to the witnessed cells, not an emit policy.

`load_parcel_mask` documents the R behaviour that gives a general rule: inside each level's mask rectangle R materialises a Map Frame for every cell (that is why R has empty frames elsewhere); outside it, R has frames only where content exists.

## Outcome

1. Replace the whitelist with a general rule, applied per level using `load_parcel_mask()`: **a cell outside that level's parcel-mask rectangle whose final encoded frame is the encoder's empty shell (no road, name, background or extended records; the exact shell shape 2-01 already validates) is not indexed.** Inside the mask nothing changes. Keep 2-01's strict shell recognition (any metadata, payload or layout difference keeps the frame). Keep it after plan 29's probe-and-pad comparison.
2. State the rule and its R basis in `phase2_cause.md`, citing `load_parcel_mask`'s contract (brief 26c) and the Phase 1 R witness. Say what would falsify it.
3. Make `phase2_gates.py diff` report **every** cell whose frames differ (old vs new, all levels) and classify each as `removed_outside_mask_empty_shell` or `other`. The gate passes only if every changed cell is `removed_outside_mask_empty_shell` and all other cells' whole-frame multisets are identical. It must not hard-code the three cells; it must list them.
4. Add a bounded R check for the removed cells: a `frame_witness.py` (or `phase2_gates.py`) subcommand that takes the diff's removed-cell list and, through plan 29's hardened reader, proves each is `empty_slot` on R (`8c2d2027…`); a `lookup_failed` or a resolved R frame fails the gate. The three Phase 1 cells must appear in the removed list.
5. Synthetic tests: outside-mask empty shell omitted (any level); inside-mask empty shell kept; outside-mask cell with any record kept; unknown metadata / non-zero trailing bytes kept; plan-29 name-drop path intact; the diff gate classifies and refuses `other` changes. Run only `parser/tests/test_l0_empty_shell.py`, `parser/tests/test_name_drop_guard.py`, `parser/tests/test_build_wiring.py` with `--basetemp output/scratch-34/tests-p2b`.
6. Update `phase2_commands.md` with the exact serial guarded commands (encode to the **new** path `output/scratch-34/G_new/ALLDATA.KWI`, sha, the generalised diff vs `output/scratch-29/G_new/ALLDATA.KWI`, the R check on the removed list, block-0 re-witness, K1 `-j 6 --engine c`, Perth encode to a new path with sha vs `04be2f6e…`, protected snapshots before/after). Note: Perth may legitimately change if Perth has outside-mask empty shells; the Perth gate must then use the same classified diff rather than sha equality.

## Rules

- Never open any `ALLDATA.KWI`, the R disc or the spool; never run an encode or K1.
- Do not edit `docs/design/`; list the contract amendment (out-of-span name guard: probe-and-pad is intermediate; final outside-mask empty-shell omission) for Execute.
- No reseat of 170 / 3-16 / 3-17; no tolerance or checker change; no Phase 3 close.
