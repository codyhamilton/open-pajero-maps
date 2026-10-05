# Phase 1 report — 1-01-reconcile-pss-ops

Status: **done**

Assigned instance named OpenCode DeepSeek Flash; Execute implemented this
unit directly (docs + small Python) for speed. No seat asked.

Base tip: `f82e2a5` (`docs: add plan 20 reconcile PSS ops cap design`) =
`origin/master` at start. Detached worktree
`/home/codyh/workspace/open-pajero-maps-20`. Left other plan WTs untouched;
did not touch `?? .venv-rp` or `output/scratch-3-11/G_new`.

## Outcome vs DESIGN Phase 1

| Requirement | Result |
|---|---|
| 3-90 check 2 at `-j 6`, median wall ≤120 s, max PSS ≤ 9,726,501 kB | Amended |
| 3-90 check 3 determinism `-j 1` vs `-j 6` after COMPARE_EXCLUDES | Amended |
| 3-90 check 4 dump/classify K1 at `-j 6` | Amended |
| Signed ceiling unchanged at 9,726,501 kB | Held (`PSS_CEILING_KB`) |
| WORKFLOW: ceiling enforced under ops K1 ≤ `-j 6` | Added subsection |
| OVERVIEW: PSS as contract mismatch; bar not cleared; Phase 3 blocked | Amended |
| CLI default workers 12→6; named constants; PLAN_WORKERS=12 | Done |
| Unit tests lock constants + default ≤ ops max | Two new tests |
| No Phase 2 historical `-j 12` rewrite | Held; optional Gates one-liner only |
| No ceiling raise / Phase 3 close / full-AU / reseat 170/3-16/3-17 / P4–6 / 06 | Held |

## Surfaces touched

- `docs/plans/04-c-core-orchestration/briefs/3-90-fresh-verify.md`
- `docs/WORKFLOW.md`
- `docs/OVERVIEW.md`
- `docs/plans/04-c-core-orchestration/DESIGN.md` (Gates one-liner only)
- `parser/tools/quantisation_roundtrip.py`
- `parser/tests/test_quantisation_roundtrip.py`
- this report; `IMPLEMENTATION.md`

## Constants

- `PSS_CEILING_KB = 9_726_501`
- `OPS_MAX_WORKERS = 6`
- `PLAN_WORKERS = 12` (unchanged)
- CLI `--workers`/`-j` `default=OPS_MAX_WORKERS`

## QA

Focused: `test_signed_pss_ops_contract_constants`,
`test_cli_default_workers_at_most_ops_max`, plus existing strip / compare
excludes fixtures as relevant. No full-AU / 3-90 K1 trio (Assumption 1).

## Explicit non-claims

Ceiling still **9,726,501**. PSS bar not cleared. Plan 04 Phase 3 not closed.
