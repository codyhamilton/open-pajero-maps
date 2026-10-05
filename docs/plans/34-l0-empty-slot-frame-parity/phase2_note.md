# Phase 2 handoff

Status: implementation ready, uncommitted; real successor verification pending.
Per-cell verdict is `conflict-open` for (0,541), (0,562) and (0,563).
Plan 29's structural residual is not discharged and Plan 04 Phase 3 stays open.

The root cause is proven against source and retained bytes: each own polygon
lies west of longitude 90, ordinary clipping leaves zero records, and E2 indexes
an empty background-header frame solely because the own source row exists.
The L0 parcel mask starts at ix=576, so mask filling does not require these
ix=0 shells. Cell 541 additionally loses its sole stale name under plan 29's
counted private admission guard and retains a 320-byte extent through padding.
Cells 562/563 have never carried names in either witnessed G and retain
160-byte extents through alignment. No division or trimming explains them.
Detailed function/line references and evidence are in `phase2_cause.md`.

The proposed correction omits only the exact encoder shell layout for these
three witnessed L0 top-level identities, after the original guard's probe,
topology comparison and padding. Payload, unknown metadata/layouts, neighboring
cells, other levels and divided leaves are preserved. No checker, tolerance,
source spool, reference data or admission rule changes. Final layout will
relocate because omitted frames and the empty block no longer allocate space.
A BMT disappears only if no other block of that blockset carries frames;
otherwise its block-0 entry becomes the individual no-data sentinel.

Offline verification: **23 passed / 11 deselected**, exit 0, in the three
brief-authorized test files with basetemp `output/scratch-34/tests-p2`.
The new policy, original/filtered byte replay, sentinel layouts and streamed
frame-diff walker run on retained bytes and memory/synthetic spill fixtures.
The guard's actual C encoder, synthetic disc builds, synthetic spool readers
and K1 cases were deliberately deselected under the worker's explicit binding.
The safe static build-wiring test also passed. No encode, K1, ALLDATA.KWI,
R-disc or live-spool access was performed. The full regression command is for
Execute, not recorded here as a passing suite.

Exact worker command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest -q -p no:cacheprovider parser/tests/test_l0_empty_shell.py parser/tests/test_name_drop_guard.py parser/tests/test_build_wiring.py -k 'not private_guard and not build_drops and not coverage_boundaries and not worker_partition and not window_away and not wiring_fixture and not e1_e2_once and not manifest_overlap' --basetemp output/scratch-34/tests-p2
```

Execute runs the exact serial guarded commands in `phase2_commands.md`.
Required evidence: a new AU successor SHA, only these three pinned shell
removals by whole-frame multiset per cell, 2,048 block-0 empty slots with no
lookup failures, live C K1 at -j6 exit 0 and pass true, Perth pin
`04be2f6e…`, unchanged protected-disc hashes and full spool fingerprint.
`disposition.json` and `.tsv` contain explicit measurement placeholders.
Execute fills them, commits the candidate byte witness and gate results, and
promotes to `fix-landed` only after all gates pass. Any gate failure leaves
its named conflict open; no `proven-non-deviation` is claimed.

Execute must explicitly amend `docs/design/out-of-span-name-guard.md` to note
the subsequent witnessed-shell omission and cell-level confinement. The worker
was forbidden to edit that path. Provenance and OVERVIEW successor notes belong
to Execute as well. The worker left IMPLEMENTATION and all plans 30–33 untouched.

Residual risks: full AU and Perth gates are unrun, helper full-disc paths are
validated only with synthetic memory/SQLite fixtures, other blocks' occupancy
has not been measured, and concurrent producer changes can make a combined
diff exceed these three cells. Unknown future layouts are preserved and require
a new disposition. The rule intentionally covers only the three proven cells,
not every record-less frame. This does not close overall DVD parity or Maps
completeness.

## Unit 2-02 supersedes the whitelist above

Execute did not accept 2-01's three-cell coordinate whitelist. Unit 2-02
replaced it with the general outside-mask empty-shell rule described in
`phase2_cause.md` § Emission rule. That section, `phase2_commands.md` and
`reports/2-02-general-rule.md` are now authoritative. Where the lines above
say the rule covers "only the three proven cells", read instead: every
outside-mask exact empty shell. Each such shell is proven absent on R by
`r-check`.

2-02 was finished by Execute after the Codex usage limit. Restricted suite
(`test_l0_empty_shell.py`, `test_name_drop_guard.py`,
`test_build_wiring.py`, `--basetemp output/scratch-34/tests-p2b`):
**53 passed**.
