# Plan 59 Phase 1 — Join vs finalize peak attribution

Tip: `22a4797`. Decision: **proceed**.

## Evidence (plan 56 dump/extend ledger)

| Source | Peak | Attribution |
| --- | --- | --- |
| `ledger/dump_finalize.json` | wrapper max_rss **473352 KiB** (~0.45 GiB); `memory.peak` 357117952 | finalize-run fixture via `bench_dump_memory.py` |
| Controller `dump_finalize_results.json` | baseline median ~**473k KiB**; tip candidate ~**201k KiB** | plan-05 removed second full copy; **one kind array remains** |
| SUMMARY handoff | finalize kind array (1 000 013 rows × parts) | Optim candidate **59** |

Residency row `finalize_kind_array_fixture` (sampler): kind array co-resident at peak. ARCHITECTURE deferred: peak anon still scales with one full in-memory kind array.

## Join vs finalize

Plan 56 dump/extend stand-in is **finalize-run only** (no separate live join residual row in the ledger). Windowed `dump_join` remains plan-05 bounded; SUMMARY does not name join as the dump-band spike. Attribution: **finalize kind-array dominates** the measured dump fixture peak → **proceed** to out-of-core / chunked merge (Domain 2). Not stop-with-evidence.

## Labels

| Claim | Label |
| --- | --- |
| Finalize kind array dominates plan-56 dump fixture peak | **Proof** (ledger + controller + ARCHITECTURE) |
| Tip candidate already < baseline (plan-05) | **Proof** (~201k vs ~473k KiB) |
| Further bound requires external sort / no full-array hold | **Proceed** (Design Domain 2) |
| Live AU join dominates finalize | **Not evidenced** this session — not used to stop |

## Outcome

**Proceed** to Phase 2: external per-part sort + k-way merge in `_finalize_dump`; sha/counts/DUMP_ORDER/parts gates; peak below tip candidate.
