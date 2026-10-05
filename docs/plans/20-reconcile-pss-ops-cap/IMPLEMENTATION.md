# Implementation — 20-reconcile-pss-ops-cap

- Tool: Open Pajero Maps Execute
- Start: 2026-10-06 Australia/Brisbane
- Assigned instance: OpenCode DeepSeek Flash (Execute implemented Phase 1 directly)

## Phase 1

### Units

- `1-01-reconcile-pss-ops` — 3-90 brief checks 2–4 at -j 6; WORKFLOW/OVERVIEW; CLI default + constants/tests — **closed** (see `reports/1-01-reconcile-pss-ops.md`)

### Outcomes

Phase 1 outcome met: live 3-90 K1 timing/PSS/determinism/dump gates use
`-j 6` against signed ceiling **9,726,501 kB** (unchanged); WORKFLOW states
ceiling enforced under ops ≤ `-j 6`; OVERVIEW frames PSS as contract mismatch
without clearing the bar; CLI default workers 6 via `OPS_MAX_WORKERS`;
`PLAN_WORKERS` remains 12; unit tests lock constants and default ≤ ops max.
Optional Gates one-liner only; Phase 2 `-j 12` history not rewritten. No
ceiling raise. No Phase 3 close. No full-AU acceptance run.
