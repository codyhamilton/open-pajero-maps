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

Dispatched: `/root/empty_kind_worker`, Codex `gpt-6-luna`, high reasoning,
with the committed brief path, repository, branch, and execution id. No service
call was made under the user override. The brief's reading/change/tool budget
and requirement for before/after regression evidence were clarified in place.

Verification preparation: existing 3-17 single-kind views for background,
background_boundary, and name_anchor were located. New evidence is confined to
this checkout's ignored `output/scratch-08-zero-row-classify/`; the shared heavy
lock is a local symlink to the main checkout's lock. A read-only SHA256 under
the lock confirms the existing 3-14 disc is
`4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`
before replay. The replay will compare name_anchor's entire output against the
retained 3-17 output and verify source input hashes again.

Unit outcome: done. Built `file_rows(..., allow_empty=True)` as a keyword-only
classify opt-in, an empty classify branch, and regression tests. The default
dump reader/writer guards remain. Classify validates actual length against the
manifest, opens and reads accepted empty inputs, writes a zero-byte assignment
with the same no-follow output policy as ordinary assignments, and removes a
stale partition before processing. Invalid dump preflight returns exit 2.
No predicates, causes, or disc data changed. No deviations or gaps reported.

Worker evidence: five regression failures before implementation; targeted
suite after implementation: 22 passed. Root verification of triage, inventory,
dump join, and extension tests: 41 passed in 11.89s. Worker turns, token usage,
and cost were not exposed by the harness; not estimated.

Real CLI replay: background and background_boundary each exit 0, write their
own `0/0/0/0` partition line, empty assignment, and header-only count/group
tables. Name_anchor exits 0 with its original `1/1/0/1` partition; every output
file is byte-identical to the retained 3-17 result. All replay input hashes match
afterward. Before/after disc SHA files are identical. Root diff inspection and
`git diff --check` pass; no protected record, plan 07, or 3-16 file is edited.

Phase verification: `/root/phase_verifier`, Codex `gpt-6-luna`, high reasoning,
independently reran the real CLI verifier (exit 0), compared the disc SHA files,
and checked the changed paths against `ac1a64d`. Verdict: phase outcome **met**;
no partial outcomes. The phase is closed by its `Workflow-Phase` commit trailer.

## Carried

None.
