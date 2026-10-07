# Dump finalize: out-of-core / drop intermediates

Plan 59 replaced the remaining one-full-kind-array `_finalize_dump` with **per-part stable sort + packed-key k-way merge**, cutting finalize fixture peak without changing dump bytes. Plan 56 dump ledger (~473 kKiB / ~0.45 GiB) attributed the dump-band spike to the finalize kind array → Phase 1 **proceed**. finalize-run gates PASS: cand median **~88880 KiB** (tip ~201 k / base ~473 k), wall ratio **~1.406**, sha/counts/parts identical. ARCHITECTURE deferred → landed. **No Phase 3 product-close claim.**

## Intent
Cody standing rule (2026-10-05): DVD-verifiable completeness; no unexplained deviations.
Primary (2026-10-07): after residency proof, chunk/stream, free between phases, mmap, drop intermediates.
This plan = dump finalize band only (mass/control → 57; encode → 58).

## Why This Existed
ARCHITECTURE named deferred out-of-core finalize after plan 05 removed redundant copies but left peak scaling with one full kind array. Plan 56 published the dump fixture peak; plan 59 consumed it.

## What Was Built
**Changed:**
- `parser/tools/quantisation_roundtrip.py` — `_sortable_dump_keys` (order-preserving packed uint8 keys) + `_finalize_dump` per-part stable sort, k-way `heapq` merge on key bytes, buffered write, `gc.collect()` between kinds.
- `docs/ARCHITECTURE.md` — deferred section → “Dump finalizer residency (plan 59)”.
- `docs/WORKFLOW.md` — Heavy jobs finalize command + pointer.

### Phase 1 — Join vs finalize attribution
Cited plan 56 `ledger/dump_finalize.json` (wrapper max_rss **473352 KiB**). Finalize kind-array dominates measured dump fixture → **proceed** (not stop-with-evidence).

### Phase 2 — Out-of-core finalize
| Arm | median max_rss_kib | median wall_s |
| --- | ---: | ---: |
| baseline | ~473268 | ~1.01 |
| tip candidate (pre-59) | ~201200 | ~1× class |
| **plan 59** | **~88880** | **~1.42** (ratio **1.406**) |

Gates (3 pairs, 1 000 013 rows, 8 parts): all PASS (`output/scratch-59/runs/finalize_results2.json`). SHA cand≡base `96c7b512…` / `240b7628…`; counts `{background_boundary: 1000013}`.

### Phase 3 — Multi-kind free + recipe
Kinds finalize sequentially; peak ≈ largest part of current kind + key rows + merge buffers. Recipe documents in-process free + optional fresh wrapper scopes. No product-close claim.

## Deviations
- First finalize-run (pre-packed-key Python-tuple heap) failed `median_wall_le_2x` (~27×); packed-key merge fixed wall under 2×. Superseded log kept as `finalize_results.json` — cite **`finalize_results2.json`** only.
- Seat soft-roll Codex → Flash (Codex 5h limit ~5:35 AM AEST); no new Codex sessions.

## Review
- Codex: usage-limited (not completed).
- Flash (`deepseek/deepseek-flash`): **PASS-WITH-CONCERNS** → **LAND** after doc-pointer fix to passing artifacts. Concerns: thin wall margin; flat-path cite resolved by this collapse.

## QA
- Unit 5 k rows BYTE_OK vs `finalize_dump_baseline`.
- finalize-run 16/16 gates PASS; `failed=[]`.
- Lock FREE around heavy runs; wrapper alone (no outer flock).

## Residual Risks
- Soft: wall ratio ~1.4× vs in-core argsort (under 2× gate; fragile if merge regresses).
- Soft: tip ~201 k KiB cited from plan-56 controller, not re-sampled this session.

## Follow-ups
- None required for dump finalize band. Further memory plans only with new Design evidence.

Scratch: `output/scratch-59/` (regenerable; see `docs/provenance.md` if listed).
