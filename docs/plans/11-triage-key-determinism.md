# Triage key determinism

The three baseline summary determinism failures recorded in plan 09 and
commit `07c3918` were resolved at `db75ce2`. Internal grouping keys now
exclude padding that NumPy copies could vary. Summary source/group counts
and output bytes agree across repeated runs and window sizes.

## Intent

User request, verbatim:

> Review the real status of open-pajero-maps against current origin/master. Read the plans and git history, including whatever the previous seat just pushed. Draw up designs only for remaining work that is actually still open in the repo, then continue that work. Land finished work on master and push origin/master. Do not invent a unit that is not in the repo. Do not open a pull request. Do not rerun a verification the repo already records as blocked unless that blocked check is still the unfinished signed work and the design says to rerun it. Do not delete scratch, symlink targets, disc, spool, or .venv-rp. One worker only. Stop when the remaining in-repo work you can finish is committed and pushed to master, or when you are genuinely blocked, and leave the result SHAs in the unit log.

## Why This Existed

Current `origin/master` at review was `7c4b78f`, including the previous seat's
eight landed commits. Plans 05 and 07–10 were already complete. Plan 04 was
blocked at 3-90; its later phases and plan 03 content were dependent/frozen.
No plan 06 design existed. This repair came from an explicitly recorded
baseline bug, independently of the blocked map verification.

Triage used aligned structured records as byte keys. Zeroing the initial
allocation did not control unnamed padding in NumPy unique/indexed copies.
Equal field values could then have different byte identities, splitting
groups across windows and losing source-group lookups.

## What Was Built

**Changed:** `parser/tools/k1_triage.py`, `parser/tests/test_k1_triage.py`,
the lasting triage contract and Architecture, the plan 09 resolution pointer
and Overview. Design preparation landed at `ed09722`; the repair and phase
record landed at `db75ce2`.

The four internal group, level/type, source and composite key dtypes are
packed. The aligned on-disk dump dtype remains separate and unchanged.
Keys retain independent storage. Field order, NaN source canonicalization,
TSV formatting/sorting, source-table cap, rule predicates/order/causes,
assignment layout and bounded window I/O retain their contracts.
No C algorithm, disc or spool changed.

The durable grouping contract is in
[K1 triage](../design/k1-triage.md#triage-report-grouping).

## Deviations

One bounded phase skipped refine. The user's one-worker requirement
overrode skill delegation and independent-agent review; implementation and
self-review were performed by this seat. The user authorized a direct
fast-forward push to master and prohibited a PR.

The advertised workflow skill version 2.8.0 was absent; installed 2.9.0
skills were used. No `artifact_feedback(path)` tool was exposed. The available
workflow-quality rating substitute was attempted for design and brief, but
its local service was unreachable. Report feedback had no callable adapter.
No rating, independent approval or execution-service identity was invented.

The first baseline attempt hit `/tmp` quota exhaustion. Tests then used
fresh `/dev/shm/maps-key-*-20261005` temporary fixture directories with the
existing prior-seat Python environment read-only. Existing files were kept.

## Review

Self-review found the phase outcome met with no remaining in-scope issue.
Every internal key consumer uses named fields and dynamic record sizes;
none exposes these keys through the file/C ABI. All four key builders were
covered so summary, classify and enumerate share stable identity.
This is explicitly not an independent review.

## QA

Before implementation, the original three repeated-run/window/high-cardinality
tests reproduced their assertion failures. An added regression also failed at
windows 1/17/997 when only unnamed bytes in NumPy copy output were varied.

Afterward, the whole triage file gave **25 passed in 4.51 s**, and shared
dump-join/S02-extension/inventory files gave **23 passed in 6.89 s**; no skips.
The final regression was strengthened with distinct groups sharing finite/NaN
sources and independent classify/enumerate group counts: **3 passed in 0.42 s**.
No other source or test changed after the focused suites. `git diff --check`
passed. The independent field-value reference checks correct source/group
counts rather than merely comparing two potentially wrong outputs.

No blocked verification, full-disc build, real dump scan or memory benchmark
was rerun. No new performance, build-byte or Phase 3 closure claim was made.

## Residual Risks

The evidence is bounded synthetic data, including the existing 5,003-source
capped-table test. No fresh full-disc or memory-budget measurement was made.
All protected scratch, symlink targets, disc, spool and .venv-rp paths were
preserved. Self-review and unavailable artifact feedback limit review proof.

## Follow-ups

None within this defect. Plan 04 Phase 3 still owns native attribution/joins,
exhaustive pins, oracle/exact-cell evidence, independent fix-review proof,
determinism comparison wording, recurring PSS failure and completeness
attribution. Its dependent phases and plan 03 frozen content remain gated;
these existing blockers were not converted into invented executable units.

## Decisions Worth Keeping

Internal structured byte keys must exclude padding: zeroing the original
allocation cannot guarantee padding after library copies. Keep report-key
representation separate from the aligned binary interchange layout.
