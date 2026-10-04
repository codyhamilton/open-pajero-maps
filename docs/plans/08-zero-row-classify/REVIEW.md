# Comprehensive review

Verdict: `PASS`

Reviewed SHA: `8b6eb55c582bbf25ee98a0405650b3b9ab4e0091` (`master`). The
review-time mechanical fix below is present in the worktree and is not committed.

## Phase outcome

### Phase 1 — Empty kinds partition as zero rows: met

The recorded real CLI replay exits 0 for background and background_boundary,
each with manifest/assigned/unclassified/cause counts `0/0/0/0` and
`PARTITION OK`. The non-empty name_anchor result remains `1/1/0/1` and every
output file matches the retained 3-17 reference. The saved before/after disc
hashes are equal. The changed-path audit contains no plan 07, 3-17, or 3-16
files. The root verification and replay evidence did not need to be repeated.

## Findings

### Medium — stale success partition survived early validation failures

**Resolved in review.** `cmd_classify` removed an old `partition.txt` only
after loading the manifest and rules. An invalid manifest or invalid rules
schema could therefore leave a previous `PARTITION OK` in the output folder.
The cleanup now happens before either validation step. A focused regression
covers both early failure paths and confirms they return 2 with no partition
left behind. Verification: the focused classify guard set passed, 6 tests.

No other findings remain open.

## Intent and assumptions

The implementation matches the scoped intent: classify treats a validated
zero-byte kind as a zero-row partition, leaves the existing non-empty partition
path intact, preserves default rejection in shared dump I/O, and does not
change predicates, causes, rules, or disc data. The assumption that the
zero-row rejection was a defect for already-empty failing kinds remains
supported by the recorded existing views and replay.

The empty-file path checks manifest/file row agreement, opens the named file,
checks the opened descriptor has zero size, and reads from it before reporting
success. Missing, malformed, non-empty, and unreadable inputs declared empty
are covered by regressions. The failure path removes stale partition output;
the empty assignment uses `O_NOFOLLOW` and replaces stale contents. Default
`file_rows`, `WindowedReader`, and `AssignWriter` zero-row guards remain in
place for other consumers.

## Plan sufficiency and residual risks

The design was sufficient to determine ownership, scope, the empty/non-empty
contract, protected records, and the verification evidence. The brief translated
that contract into suitable guard, assignment, regression, and replay checks.
No completeness re-tally or all-kind partition claim is implied by this phase.

No material residual risk remains for the designed behavior. The real replay
covers the selected existing kind views; the synthetic tests cover malformed
and inaccessible zero-row inputs. Concurrent external mutation of dump inputs
during classification is outside this phase's contract.

## Follow-up review

Verdict: `PASS_WITH_FOLLOWUPS`

Reviewed SHA: `8b6eb55c582bbf25ee98a0405650b3b9ab4e0091` (`master`), with the
review-time mechanical fix still present in the worktree.

### Low — malformed rules JSON raises an uncaught decode exception

**Follow-up:** record and address in `docs/design/k1-triage.md` during close-out.
`_load_rules` calls `json.loads`, but `cmd_classify` catches only `BadRules` for
the rules-loading path. Syntactically invalid JSON therefore raises
`JSONDecodeError` through the CLI instead of returning the usual validation
status 2. The reviewed stale-partition cleanup runs before rules loading, so
this exception cannot leave an earlier `PARTITION OK` in place. This behavior
predates the zero-row change and is non-blocking for its contract. The parser
behavior was not changed during this review.

The final post-review suite passed 43 tests in 11.74s, and the real CLI replay
passed with output identity unchanged.
