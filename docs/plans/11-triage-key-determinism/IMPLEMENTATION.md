# Triage key determinism execution

Run identity: Codex, one worker, worktree
`/home/codyh/workspace/open-pajero-maps-status-continue-2`,
branch `chm/maps-status-continue-2`, 2026-10-05 Australia/Brisbane.
Start HEAD and fetched origin/master: `7c4b78f57248224a8dba4b674c5cd77386e7030f`.

Design and brief grounded in the three baseline summary failures explicitly
recorded in plan 09 QA and commit `07c3918`; no Phase 3 fix unit invented.
The previous seat's changes are already landed. One-worker/no-PR instructions
override skill delegation and PR creation; self-review will be identified as
such. Protected input and scratch paths remain untouched.

Artifact feedback: no `artifact_feedback(path)` tool is exposed. The available
workflow-quality `rate_artifact` substitute was called for DESIGN and failed
with a transport error to `127.0.0.1:8765/mcp`. The service is unreachable;
no rating or execution identity is fabricated. Continue per skill instruction.

## 1-01-existing-key-determinism

Preparation commit: `ed09722`. Before implementation, the three recorded
repeat/window/high-cardinality tests all reproduced their assertion failures.
The added adversarial copy-padding regression also failed at windows 1/17/997:
duplicate logical source rows or zero source-group counts. These are observed
failures, not reused results from the previous seat.

The first baseline attempt could not write its generated files because of
`/tmp` quota exhaustion. No files were removed. Reproduction used a fresh
`--basetemp=/dev/shm/maps-key-baseline-20261005`; the new regression used
`/dev/shm/maps-key-regression-before-20261005`. These are small pytest-generated
fixtures, not project scratch inputs. No blocked verification was run.

Built: all four internal key builders use packed dtypes. The dump-manifest
dtype remains aligned. Keys retain the same fields and independent ownership;
source NaN canonicalization, report sorting, formatting, assignments and
window I/O stay intact. The stable triage contract/Architecture describe this
boundary; plan 09 now points to the resolution, keeping its historic QA.

Verification: focused triage suite **25 passed in 4.51 s**, no skips, using
the existing environment read-only at
`/home/codyh/workspace/open-pajero-maps-status-continue/.venv-rp/bin/python`
and a fresh `/dev/shm/maps-key-triage-after-20261005` basetemp. This includes
the original three failures, independent source/group-count references with
deliberately dirty copy padding, and classify/enumerate validation.

Shared-I/O/inventory suite: **23 passed in 6.89 s**, no skips, fresh
`/dev/shm/maps-key-shared-after-20261005`. Final regression was strengthened
to include finite/sentinel sources shared by distinct groups and independent
classify/enumerate group-count checks. Those changed tests gave **3 passed in
0.42 s** at `/dev/shm/maps-key-final-regression-20261005`. Other code/tests
were unchanged after the 25-test pass. `git diff --check` passes.

Brief feedback via `rate_artifact` also failed with the same transport error.
Report feedback has no callable adapter (`rate_artifact` accepts only design
or brief), and the service is already unreachable. No result is invented.

Self-review against the phase outcome found no remaining in-scope issue:
all key consumers use named fields/dynamic sizes, packed keys stay wholly
inside triage, dump alignment remains unchanged, and shared group keys cover
classify/enumerate as well as summary. The adversarial test changes unnamed
copy bytes only and compares with an independently calculated logical reference.
This is one-worker self-review, not independent terminal review.

### Phase 1 record — outcome verified

The original three failing tests now pass. Summary bytes agree across runs
and windows including the 5,003-source capped table. Source/group counts and
classify/enumerate identities match the synthetic field-value references.
Focused suites total **48 passed**, no skips; strengthened tests also pass.
One bounded unit completes this design. No code outside triage was changed.

**Carried:** None within this repair. Plan 04's unchanged 3-90 blockers,
review/sign-off prerequisites and dependent/frozen phases remain outside it.
Existing scratch, symlink targets, disc, spool and .venv-rp were preserved.
