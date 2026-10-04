# Self-review under the one-worker constraint

Reviewer: the implementing Codex seat. This is not an independent review;
the user required one worker. Reviewed the final source/test diff, committed
design and brief, actual focused test outputs and stable doc changes.

The defect is grounded in plan 09 and `07c3918`, and all three baseline tests
were reproduced here. All four internal key builders previously had padding;
the dump dtype is still aligned. Their consumers access named fields, record
sizes and byte slices, so packed keys change no external file/C ABI.
NaN handling, report ordering, min/max reduction, assignment data and rules
are untouched. There is no new production loop or full-file allocation.

The dirty-padding regression changes only bytes outside declared fields in
NumPy unique outputs. It independently computes source counts/group sets
and checks shared finite/NaN sources, groups spanning windows, classify group
counts and enumerate membership/counts. Existing repeat/window/capped-source
tests check emitted bytes. This distinguishes deterministic field-value
identity from zeroing the initial allocation or merely suppressing a failure.

The design outcome holds on 48 focused passing tests, no skips; the final
three strengthened cases also pass. No blocker or high finding within this
repair remains. There is no full-disc, performance or Phase 3 closure claim.
Unreachable workflow feedback and self-review limitation are recorded.

Scope remains bounded: no blocked 3-90 rerun, oracle/rule change, scratch
switch, protected-path deletion or invented map-content unit. Later work
remains gated by the existing signed plan 04 outcome and its missing proof.
