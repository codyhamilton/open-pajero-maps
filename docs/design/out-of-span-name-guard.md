# Out-of-span name admission and absence evidence

Assembly drops anchored names outside the plan-18 lattice span, using each
level's half-open latitude and wrapped longitude coverage. Admission is a
lattice-coverage check; a valid anchor outside its home cell remains valid.
Names without anchors are preserved; nonfinite anchors fail explicitly.

Every dropped source name is counted once over disjoint source-row ranges,
restricted to the requested build window. Counts are reported per level in
stdout and the manifest's `out_of_span_names_dropped`, including zero levels.
`E1Spool(guard_names=True)` applies the guard only during assembly through
private copy-on-write spool mappings. The source spool stays untouched, and
K1 continues to compare against its original contents.

For chunks with in-window drops, assembly probes the unfiltered input and
zero-pads shorter filtered frames to their original indexed extents. Frame
count and topology must agree; enlargement or topology changes fail.
The probe remains scratch evidence, and its calls are excluded from production
E2 accounting. Zero-drop chunks need no probe or padding. Preserved extents
prove confined changes, not equality with R's frame allocation.

R absence must be proven by index sentinels, never by lookup failure. An absent
BMT requires raw BSMR offset `FFFFFFFF` paired with size zero; a block or parcel
requires DSA `FFFFFFFF`. A non-sentinel zero-size parcel may be a nested record
and must resolve. Retain offsets, raw bytes, hashes, decoded identities and
coverage geometry so the evidence can be replayed without opening R. Missing
lookups, invalid extents and decode failures remain unresolved and forbid an
absence verdict. Resolved frames require validated name-directory/subframe
bytes; outside-coverage claims require validated index geometry.

The [plan 29 record](../plans/29-k1-name-anchor-failure.md) establishes the O03
application of these contracts. Lasting tools and byte witnesses are under
`docs/plans/04-c-core-orchestration/triage/name_anchor/`.

## Final outside-mask empty-shell omission (plan 34)

Probe-and-pad is an intermediate step, not the final emission rule. After
probe-and-pad and the declined-row check, assembly does not index a cell that
lies outside its level's `load_parcel_mask` rectangle when its final frame is
the encoder's exact record-less shell (zero padding only). Inside the mask, and
for any frame with a record, metadata difference or unknown layout, the frame
is kept. R materialises frames for every in-mask cell but only for content
outside it; a witnessed R frame at an outside-mask record-less cell falsifies
the rule.

Confinement of a successor is therefore proven by classified cell identity, not
by preserved extents: every changed cell must be
`removed_outside_mask_empty_shell` and proven `empty_slot` on R through the
hardened reader, and every other cell's whole-frame multiset must be identical.
Plan 34 applied this to `2ee3456a…`, producing successor
`4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` (five L0
cells removed: (0,141), (0,176), (0,541), (0,562), (0,563)). See
`docs/plans/34-l0-empty-slot-frame-parity/successor_oracle_4e6b0de7.json`.

## Carried follow-ups

- Review R3 went to plan 34: the G L0 frames at (0,541), (0,562) and (0,563)
  where R has empty slots are fix-landed by the omission rule above.
- Review R4 remains carried to the performance-inventory owner under plan 04:
  `parser/tests/test_perf_inventory.py::test_inventory_covers_every_module`
  fails on the pre-plan-29 baseline as well as the final suite. Repair the
  inventory in its owning work package and verify it there. The recorded final
  suite is 1 failed / 1060 passed / 7 skipped, not a passing full suite.
