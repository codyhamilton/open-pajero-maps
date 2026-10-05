# Brief: 3-90 — Fresh verification and Phase 3 record

Consumer: the orchestrator (Phase 3 close sign-off; Cody signs any re-oracle recorded here).
Owned paths: `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` (Phase 3 record, appended), `docs/provenance.md` (new non-committed material Phase 3 left that later phases rely on), `output/scratch-3-90/`. No code. Nothing under `parser/`.
Commits: Commit to `master` and push when the record is written.
Depends on: 3-08 and every inline fix unit (3-10 to 3-89) the orchestrator authored; if any fix unit is unreviewed, report `blocked`.
Runs alongside: nothing. This worker must be a fresh agent that did not write any 3-xx unit.
Tier: Sonnet (the one unit not on Flash). Verification only; not RE-risky.
Budget: 10 files to read, 40 tool turns, three K1 runs plus one `-j 1` run plus Perth. Past the budget: report `over budget` with what is checked.

## Required reading

1. `DESIGN.md` Phase 3 Outcome, Assumption 1, Gates (120 s, PSS ceiling 9,726,501 kB, determinism, sha).
2. `IMPLEMENTATION.md` Phase 2 record and the Phase 3 unit records; `docs/plans/04-c-core-orchestration/triage/cause_table.md` and `pinned_candidates.tsv` (or the final pinned list the orchestrator names in the run message).
3. `briefs/2-08-full-disc-verify-and-record.md` (the commands and run conventions; reuse them).

## Goal

Independent proof that, on the oracle disc in force, build-caused and checker-caused failures are 0 in every kind and spool-caused failures equal the pinned list as a set, within the time and memory bars, with determinism and gates intact.

## Contract

Cited from `DESIGN.md` Phase 3 Outcome: "On the oracle disc in force at phase close, the checker reports build-caused and checker-caused failures of 0 in every kind, and the failures that remain are exactly the enumerated spool-caused list (item identity, not only counts)… The run takes ≤ 120 s. Any sha change is a recorded re-oracle (Assumption 1); otherwise 87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862 stands (full form; was 87a01b14…)."

Successor-pin note (plan 29, 2026-10-06): the AU disc in force is now `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae` (`output/scratch-29/G_new`). It differs from the historical `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` only by 146 bytes in the L0 (0,541) leaf [928] frame, where the out-of-span O03 name was dropped. On it, K1 name_anchor failing is 0, not 1, and range checked is 1 lower. A 3-90 run must use the successor and name plan 29 as the fix unit. The Perth fixture at tip is `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`, which plan-29 code leaves unchanged; the 3-11-era `da13a775…` above is historical. Plan 29 record: `docs/plans/29-k1-name-anchor-failure.md`; lasting witnesses: `docs/plans/04-c-core-orchestration/triage/name_anchor/witnesses/`. This note does not run or sign off 3-90.

## Changes (checks, in order; every check: command, raw output saved, pass/fail)

All heavy runs under `flock output/.heavy.lock` (Contract W). Record the HEAD commit and `git status` first; the tree must be clean except for `output/`.

1. Disc in force: if the orchestrator's run message names a re-oracle disc, use it; else the 3-11 disc. Record sha256 of the disc image(s) and print the oracle disc in force as a `Parameters:` line.
2. K1 timing: three `quantisation_roundtrip` runs at `-j 6` (command as in 2-08, dump off; ops K1 cap), median wall ≤ 120 s, max PSS ≤ 9,726,501 kB (signed ceiling unchanged); record all three.
3. Determinism: one `-j 1` run; the report JSON byte-equals the `-j 6` one after removing every key in `quantisation_roundtrip.COMPARE_EXCLUDES` — `timing` **and** `wall_s` (the Phase 2 contract), not `timing` alone (`cmp` after stripping both keys with `quantisation_roundtrip.strip_compare_excludes`).
4. Dump check: one `-j 6` run with `--dump-failures` (ops K1 cap; dump bytes are worker-count-independent); run `k1_triage.py classify` with the final merged rules over it. Required: 0 rows of causes `build` and `checker` in every kind, no unclassified rows, `PARTITION OK`. Compare the `spool` rows at group granularity with the pinned list: set equality (print the two counts and the `diff` of the sorted lists; empty diff required).
5. Counts: per kind `checked`/`failing` in the report equal the 3C-04 `checked` values (Phase 2 DESIGN outcome), and `failing` equal the pinned list's row counts per kind. name_anchor failing 1 is allowed.
6. Build gates: full-AU build sha equals `87a01b14b612d58ba49f326542339ef4d6fc1871c9201842c7961108a2797862` (or the recorded re-oracle sha, with the fix unit that produced it named and the exact differing cells quoted from its record). Perth `-j 1` == `-j 4` == `da13a77506424c55e74df186d841d5198cefb6e1e4dac27be25ad9307201fbbc` (or recorded re-oracle value). Goldens and the H-budget tests pass: `.venv-rp/bin/python -m pytest parser/tests -q -x` (full), quote the summary line.
7. Perf inventory and `cbuild` staleness tests included in step 6; additionally run `grep -c` of nothing else; do not edit anything.
8. Write the Phase 3 record in `IMPLEMENTATION.md`: parameters line, the cause-per-kind table from `cause_table.md` with the post-fix counts, check results 1-6 with numbers, any re-oracle with its sha and exact cells, the pinned list's path and sha256, a "Carried" list (spool items and Phase 2 carried items not absorbed, per DESIGN.md Phase 3 Units, "Carried-item placement"). Add `docs/provenance.md` entries for the final dump and the pinned list if they live outside git.

## Done evidence

The record exists and is committed; every check has raw output under `output/scratch-3-90/`; the report's first line is PASS or FAIL per check number.

## Report back

Under 1,200 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Numbers first, then deviations. Never resolve a contradiction silently.
