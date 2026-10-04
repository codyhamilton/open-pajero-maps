# Existing triage key determinism

Resolved the baseline summary failures named by plan 09. Four internal
grouping dtypes are packed; NumPy record-copy padding no longer changes byte
identity. The manifest-defined aligned dump dtype and assignment bytes retain
their existing layout. No C, checker predicate or cause rule changed.

Before the fix, the three existing repeated-run/window/high-cardinality tests
failed. The new bounded regression also failed at windows 1/17/997 when only
unnamed bytes in NumPy unique outputs were varied. Afterward all 25 triage
tests passed in 4.51 s with no skips, including the field-value reference for
per-source row/group counts and existing classify/enumerate checks.

The first attempt hit `/tmp` quota; subsequent tests used fresh named
`/dev/shm` basetemps. Existing data was preserved. The existing Python
environment was consumed read-only; no new environment or project scratch
was needed. No blocked verification, real dump scan or full-disc build ran.

One-worker instruction supersedes the workflow's independent-agent review.
Self-review is explicitly identified; service feedback is unreachable, so no
independent approval or service identity is claimed. Shared-I/O/inventory
checks gave 23 passes in 6.89 s with no skips. The final strengthened regression
(shared sources and classify/enumerate logical group counts) gave three passes
in 0.42 s. Final diff review found no in-scope issue; diff whitespace checks pass.

Plan 04 Phase 3 still needs native attribution/joins, exhaustive pins,
oracle/exact-cell evidence, its review chain, determinism-check correction,
memory-budget proof and completeness attribution before 3-90 can close.
Later phases and plan 03 content remain dependent/frozen. This scoped report
repair supplies no new full-disc, memory-budget or phase-close claim.
