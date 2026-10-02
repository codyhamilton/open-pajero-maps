# Review: 05-heavy-job-memory

Verdict: **PASS_WITH_FOLLOWUPS**

Reviewed SHA: `120bc78` (origin/master tip at review start; Phases 1–4 closed).

Independence: this review did not author Phases 1–4. Evidence re-checked: design vs IMPLEMENTATION close records, landed surfaces (`dump_io`, `dump_join`, `_finalize_dump`, `k1_triage`, harness, fixtures, WORKFLOW/ARCHITECTURE), and `pytest` (128 passed: dump_join / extend_s02 / k1_triage / quantisation_roundtrip / perf_inventory). Full 1M controller benches were not re-run (disk ~96%; Phase 1–4 recorded PASS evidence retained).

## Phase outcome assessment

### Phase 1 — Residual extension cuts peak memory with identical bytes — **met**

- Tracked `parser/tools/dump_join.extend_residual` + harness + vendored baseline; byte identity (SHA ×3), ≤50% max RSS and `memory.peak`, growth and wall gates hold in worker and orchestrator re-runs (IMPLEMENTATION; `review_1-01.md` ACCEPT).
- Non-stable `argsort`, narrowing cast, leftmost match, byte146-from-flag, write-behind / no production `array_equal`, opt-in `--verify`, zero-row reject-before-write: confirmed in code.
- **Partial vs Assumption 6 wording:** live `output/scratch-3-12/extend.py` still the whole-file baseline (not switched to the adapter). Carried deliberately while plan04 3-13/3-14 share that tree — follow-up, not a phase fail (adapters + isolated replay are the durable path).

### Phase 2 — K1 dump finalizer drops redundant full copies — **met**

- `_finalize_dump`: prealloc + `readinto`, per-part unlink, stable `argsort(order=DUMP_ORDER)`, chunked permutation `tofile` (no `tobytes()` full copy). RSS delta ≥ one full array every pair; SHA equal; dump tests pass.
- Chunked write is an allowed elaboration of “write gathered rows without `tobytes()`” (no second full gather).

### Phase 3 — 3-07 + triage on window boundary — **met** (one gate substituted)

- `parser/kiwiw/dump_io.py` (DEFAULT_WINDOW 65536, write-behind, zero-row reject); residual on dump_io; `extend_s02_producer`; triage windowed + `_own_key`.
- 3-07 and triage summary/classify/enumerate: ≤50% RSS/peak on fixed-cardinality 1M fixtures; growth gates; SHA equal; Phase 1 residual re-check PASS.
- High-cardinality “candidate peak ≤ baseline at 1M” not separately measured; unit late-first / window-straddle identity (`test_high_cardinality_late_first_identical`) stands in — **follow-up**, documented in Phase 3 carry and WORKFLOW limitations.

### Phase 4 — Heavy-job commands reproduce serially — **met**

- WORKFLOW lock / scope wrapper / reproduce commands / RSS vs `memory.peak` / peaks / limitations; ARCHITECTURE bounded I/O, oomd, deferred out-of-core finalizer; build/kernel/PSS intact.
- Lock probe fail-while-held / succeed-after recorded; residual documented command re-run under flock PASS.
- Finalize / s07 / triage controllers not re-run in Phase 4 (disk); Phase 2–3 evidence + identical documented command strings — acceptable per brief 4-01; residual voluntary re-verify when disk allows is a non-blocking follow-up.

## Findings

| ID | Severity | Status | Notes |
|----|----------|--------|-------|
| F1 | low | **resolved in review** | `docs/WORKFLOW.md` still points at `docs/plans/05-heavy-job-memory/` and its `IMPLEMENTATION.md`. Close-out must rewrite those to `docs/plans/05-heavy-job-memory.md` (no live path into the deleted folder). |
| F2 | low | follow-up | Scratch `output/scratch-3-12/extend.py` not switched to `dump_join` (Assumption 6 / 3-13 coordination). |
| F3 | low | follow-up | High-cardinality triage 1M RSS pair not measured; unit identity + fixed-card 50% gates stand in. |
| F4 | low | follow-up | Optional serial re-run of finalize / s07 / triage documented commands when disk headroom allows. |

No blocker or high findings. No remediation briefs opened.

## Intent and ledger

- Verbatim intent (cut peak RSS / pressure for heavy dump joins without semantic change; streaming; drop asserts; heavy.lock docs): **matched** by Phases 1–4.
- Assumptions 1–5, 7–10: **hold** with recorded evidence.
- Assumption 6: **holds for tracked adapters / isolated baseline**; scratch-3-12 switch still open (F2). Scratch-3-07 is already a thin wrapper over `extend_s02_producer`.
- Assumption 8 fallback (`anon+dirty+writeback` at ≥100 Hz) never needed; peak spread under concurrent load noted, gates still passed.

## Plan-sufficiency

Design was sufficient to place outcomes, gates, and QA. Adversarial ledger items (triage key ownership, empty-kind rejection, cgroup `memory.peak`, baseline isolation, cast pinning, verify mode, finalizer in scope) landed. Execution correctly carried, rather than silently absorbing, Assumption 6 scratch-switch and high-card RSS measurement.

## Residual risks

- Live residual scratch entry still whole-file (oomd pressure if re-run from scratch-3-12 without the adapter).
- Finalize still one full in-memory kind array (out-of-core deferred — Architecture).
- `memory.peak` noisy under concurrent load; serial lock discipline remains load-bearing.

## Mechanical fixes applied in this wrap-up

- F1: rewrite WORKFLOW plan paths on close-out (same commit as folder collapse).
