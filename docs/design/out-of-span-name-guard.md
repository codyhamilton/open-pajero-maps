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

## Carried follow-ups

- Review R3 goes to plan 34: investigate G L0 frames at (0,541), (0,562) and
  (0,563) where R has empty slots. Removing O03 establishes name parity for
  that item; the structural differences still need root causes and disposition.
- Review R4 remains carried to the performance-inventory owner under plan 04:
  `parser/tests/test_perf_inventory.py::test_inventory_covers_every_module`
  fails on the pre-plan-29 baseline as well as the final suite. Repair the
  inventory in its owning work package and verify it there. The recorded final
  suite is 1 failed / 1060 passed / 7 skipped, not a passing full suite.
