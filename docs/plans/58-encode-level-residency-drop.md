# Encode: drop intermediates between levels (E1Spool close + Pool recycle)

Plan 58 cut encode peak residency without changing ALLDATA bytes. Plan 56 showed encode **tree ≫ wrapper RSS** (Perth tree ~13.9 GiB / AU cite ~15.2 GiB) with `-j4` worker Pool co-resident; tree peak alone was inventory, not a cut license. Phase 1 named the cut target: per-worker `E1Spool` was replaced on level change **without `.close()`**, so private COW memmaps could linger across levels `[12…0]`. Phase 2 closed prior-level spools, hardened `E1Spool.close()` (mmap `_mmap.close`), dropped `e1_out` before E2, and — after Codex HOLD — **recycled the fork Pool after each level** so every worker dies and frees its mapping (spill *files* retained via FrameTable paths). Perth sha stayed `04be2f6e…`. AU `-j4` ×3 stayed `88bd7852…`. Plan-41 close gates PASS. **No Phase 3 product-close claim.**

## Intent
Cody standing rule (2026-10-05): DVD-verifiable completeness; no unexplained deviations.
Primary (2026-10-07): after residency proof, designs that chunk/stream, free between phases, mmap, drop intermediates — no seat ask.
This plan = encode band only (mass/control → 57; dump finalize → 59).

## Why This Existed
Published AU/Perth encode tree peaks ~15 GiB at `-j4` without a named dominant class. Blind mmap changes risked byte drift. Plan 56 ledger + code inspection licensed the E1Spool lifecycle cut.

## What Was Built
**Changed:**
- `parser/kiwiw/cenc.py` — `E1Spool.close()` closes underlying numpy memmaps before nulling views.
- `parser/build_alldata.py` — `_e1spool` closes previous level; post-level Pool close/join + fresh fork Pool; early `del e1_out`; `_release_worker_encode_caches` helper.
- `parser/tests/test_e1spool_level_release.py` — close + cache level-switch tests.
- Incidental suite pin: `cell_local_2-01.py` refuse-uncapped before G sha; `G_SHA` → live `88bd7852`.

### Phase 1 — residency classes named
Cited plan 56 encode Perth stand-in (tree 13962.9 MB; wrapper ~3.25 GiB) + plan-48 cite (AU 15240.1 / Perth 13809.5). Dominant aggregate: worker Pool j=4. Cut target: E1Spool cross-level close gap. Anon vs file at peak labelled hypothesis (post-exit `memory.stat` not peak evidence).

### Phase 2 — drop-between-levels (sha-identical)
Perth `-j4` same-host harness (`bench_build` MB units):

| Arm | tree_mb | max_rss_kib | memory.peak | sha |
| --- | ---: | ---: | ---: | --- |
| baseline | 13848.7 | 3413788 | 2426187776 | `04be2f6e…` |
| cut (map release) | 13165.0 | 3234696 | 1379713024 | `04be2f6e…` |
| cut (pool recycle) | **13113.3** | **3200832** | **1681948672** | `04be2f6e…` |

### Phase 3 — AU confirm (no product-close)
AU `-j4` ×3 after pool-recycle: walls `[37.69, 37.38, 36.26]` → **median 37.38 s of 3 (spread 1.43 s)** vs plan-41 baseline 37.38 s; trees MB `[15274.2, 15476.1, 15389.1]`; sha **`88bd7852…` PASS** (3/3).

## Deviations
- First Codex review HOLD on `pool.map(release, range(workers))` not guaranteeing per-worker coverage — fixed by Pool recycle; Perth/AU re-measured.
- AU tree peaks remain ~15 GB-class (MB sampler); cut wins clearer on Perth / wrapper RSS/`memory.peak` than on AU tree headline.
- No Phase 3 product-close claim (Design).

## Review
- Codex first (65ce85c): PASS-WITH-CONCERNS / **HOLD** (Pool.map; GiB/MB wording).
- Codex re-review (tip 58e6d2f evidence): **LAND** — pool recycle verified; Perth/AU numbers; close_gates a/b/c; no product-close claim.

## QA
- Close gate (a): 1486 passed, 9 skipped in 740.67s at `d2de71a`.
- Close gate (b): median 37.38 s of 3 at `-j4` (spread 1.43 s) vs baseline 37.38 s.
- Close gate (c): AU `88bd7852` PASS (3/3), Perth `04be2f6e` PASS.
- `close_gates.py --base f616059` PASS at close tip.

## Residual Risks
- Soft: AU tree peak still large; further encode residency (spill page-cache / parent FrameTables) out of this plan’s licensed cut.
- Soft: Pool recycle after each level re-forks when parent already holds FrameTables (eager-fork benefit reduced for later levels) — accepted for guaranteed release.

## Follow-ups
- Plan **59** dump finalize out-of-core (next memory band) — start only after this close.
- Optional: further encode residency if Design opens a new cut class from AU tree samples.

Scratch: `output/scratch-58/` (regenerable benches/wrapper logs; see `docs/provenance.md`).
