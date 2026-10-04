# Zero-row classify implementation

Run identity: Codex API, local run `08-zero-row-classify-ac1a64d`, started
2026-10-03 23:59:41 UTC (2026-10-04 Australia/Brisbane).
Repository: `/home/codyh/workspace/open-pajero-maps-08-zero-row-classify`.
Branch: `master`; starting HEAD: `ac1a64d`.

## Execution constraints

One phase, one implementation worker; refine skipped as instructed. The supplied
untracked design is included in the preparation commit. No feature branch, push,
PR, or workflow-service calls are authorized. Service registration and execution
logging are deliberately omitted under the user's explicit instruction, not
because of a service outage; execution identity is `none` and commits use
`[exec none]`.

Core skill files were read from the installed workflow plugin at version 2.8.0.
Its `check_skills.py --harness claude-code` reports missing legacy
`~/.claude/skills` entries; this is a Codex session with all six core plugin
skills available, so no external installation or bootstrap is performed.

## Phase 1 — Empty kinds partition as zero rows

Unit: `1-01-empty-kind-partition`; consumer: one implementation worker.
Brief: `briefs/1-01-empty-kind-partition.md`. Execution id: `none`.

Prepared: classify currently calls `file_rows`, `WindowedReader`, and
`AssignWriter`, all of which reject zero rows. A classify-only opt-in and empty
branch can preserve the existing guard for other dump I/O consumers. Validation
must inspect the existing file rather than trust a zero-row manifest alone.

## Carried

None.
