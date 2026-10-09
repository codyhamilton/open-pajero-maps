# R01 residual after plans 44 and 45, re-decided under the plan-46 producer (R-G5-4-a / R-G5-4-b / R-G5-4-c)

## Intent
Plans 44 and 45 left 7,396 R01 rows with classes produced by a matcher that has four defects plan 46 root-caused (RC2 per-piece byte match, RC3 FarHomes, RC4 divided-leaf rect, RC5 same-type filter). Those classes were not root causes. Plan 62 re-decided every one of them under the plan-46 producer. It attributed each class change to a fix and audited the 87,743 proven rows for producer type. It then discharged R-G5-4-a/b/c into exact named children with no waivers, and R-G5-4-c is no longer carried.

Design: box draft revised 2026-10-08 (REVISION-NOTE), plus the scratch-rule note of 2026-10-09. Base `8498eec`. Plan 65 (owner wording) landed first.

## What Was Built
Commits: land `f6ba75a`, review fix `a3ae73c`, close-out (this record).

### Phase 1: census
`historical_bg/p9_r01_residual/census.tsv.gz` (sha 07523d89…) holds 7,396 rows: a 6,486, b 830, c 80. It covers 307 cells, and c spans (1797,424) 12, (828,862) 52, (832,856) 16. It is built from `census_join.tsv.gz` (ac26effb…), which joins all 95,139 plan-44/45 rows to the plan-46 scan.

### Phase 2: re-decide
`redecide.py` (driver) and `parser/tools/r01_redecide.py` (pure helpers, unit-tested). Configs: FULL, plus single-fix -RC2..-RC5, all at Moore(8), plus PLAN44.
- Coverage is exhaustive over all 319 residual groups, plus FULL/PLAN44 on all proven groups.
- The double run is byte-identical. `redecide.tsv.gz` is 9c47f1ef….
- The harness checks out:
  - PLAN44 reproduces plan 44 on 95,054 / 95,059 rows. The 5 exceptions are U4F_RING: plan 44 Unit 4f took the first ring in the producer home, ri 0 with an empty clip, while the producer is ri 1 (`u4f_probe.json`).
  - FULL equals the plan-46 scan on 95,139 / 95,139 rows.
  - The phase23 decide limb agrees on 95,059 / 95,059 rows.

| Parent | Old → new | Rows | Single-fix attribution |
|---|---|---:|---|
| a | ambiguous → build | 2,561 | RC2 2,536, RC5 25 |
| a | ambiguous → ambiguous | 222 | — (child a-1) |
| a | outside@16 → build | 3,023 | RC3 2,525, RC2 466, RC2+RC3 32 |
| a | skip_divided → build | 525 | RC4 |
| a | no_oe → build | 118 | RC2 |
| a | source-removed → build | 5 | U4F_RING |
| a | source-removed → source-removed | 32 | — (child a-2) |
| b | ambiguous → build | 189 | RC2 |
| b | outside@16 → build | 96 | RC2 |
| b | outside@16 → source-removed | 97 | RC3 (child b-1) |
| b | skip_divided → source-removed | 16 | RC4 (child b-1) |
| b | source-removed → source-removed | 432 | — (child b-1) |
| c | outside@16 → build | 80 | RC4 |

- **Same-type audit:** 87,743 / 87,743 proven rows have a same-type producer and stay build under FULL.
- **R-G5-4-c gates:**
  - **G-c1:** `window_control.json` ALL_OK.
  - **G-c2:** 80/80 unique-byte. Every producer is within Chebyshev 1 of its home cell, and the -RC4 ablation reproduces plan 45's verdict.
  - **G-c3:** 14 match. 44 mismatches are named row by row: the src is the nearest same-type shape (brief 3-03), not the producer. 22 rows have src = -1.
  - **G-c4:** 80/80 build, with a byte or OE witness in every covering d35b565 leaf (4→1 / 4→16).
  - **G-c5:** no radius label.
  - **G-c6:** byte-identical.
- **Peak:** VmHWM 3.84 / 3.88 GiB; memory.peak 4.52 GiB (`56/ledger/r01_residual_plan62.json` + SUMMARY row).

### Phase 3: discharge and children
- **`residuals.tsv`:** "UPDATED by plan 62" appended. R-G5-4-a, R-G5-4-b and R-G5-4-c are `discharged-plan-62`; R-G5-4-c was maps-parity-carried before. Children, all `blocks-phase3`:
  - **R-G5-4-a-1:** 222 producer_ambiguous, 8 groups, owned by plan 63. In each group two same-type rings emit a byte-identical piece, and the decide limb builds under either candidate.
  - **R-G5-4-a-2:** 32 source-removed, owned by plan 64.
  - **R-G5-4-b-1:** 545 source-removed, owned by plan 64. The producer is in the candidate set, but its d35b565 clip is empty.
- **Other docs:** OVERVIEW ownership line updated, the R-G5-4-c carried row removed and the L108 pointer fixed. Notes added to `synthesis.md` and `causes_residual.md`, plus a provenance entry.
- No Phase 3 product-close claim. Out of scope and untouched: R bump, F6, kind-order, L8, plan 04 P4–6, 3-90.

## Review
Codex seat (CHM seat change 2026-10-09), `codex exec -s read-only`.
- **Review 1:** VERDICT FIX.
  - B: `-RC3` also switched to plan 44's radius.
  - H: there was no per-phase scratch receipt.
- **Fix `a3ae73c`:** `-RC3` made pure and rerun. Attribution moved only for 32 rows, now RC2+RC3. The Phase 1 receipt deviation is recorded and a fresh Phase 2 receipt added.
- **Review 2:** **VERDICT LAND.** Non-blocking: `redecide.json` counts the 32 joint rows under both RC keys, so totals overlap there. `transitions.json` gives the exclusive split.

## Scratch receipts
- **Phase 1:** deviation. The rule arrived after Phase 1 ran. Its two scratch inputs were consumed by Phase 2 and deleted in Phase 2's first receipt, after the committed copy was cmp-verified.
- **Phase 2, first run:** `output/scratch-62` 3,699,606 B → gone. Run-B copies deleted after cmp; wrapper peaks copied into the ledger first.
- **Phase 2 rerun:** 327,679 B → gone. `/tmp/p62_redecide_*` removed. 0 `maps-heavy` scopes.
- **Phase 3 (close-out, 2026-10-09):** `output/scratch-62` 159,249 B (Codex review 2 scratch only) → gone, and `output/scratch-65` 29,460 B → gone. `/tmp/p62_*`: 0. `maps-heavy` scopes: 0. `df -h /home`: 11 G free (97 %). Nothing kept outside git. The clean plan-60/65 worktree `open-pajero-maps-60` removed, `output/scratch-65` removed and `git worktree prune` run.
- **Stale-scratch clear before resuming:** `scratch-46/gatework_full_b` 5.2 G (plan-46 run B, identical to A), `gate_v2_blob` 170 M and `gate_v3_piece` 167 M. /home went from 5.0 G free to 11 G.

## Residual Risks
- Children a-1, a-2 and b-1 block Phase 3 until plans 63 and 64 land.
- "build:eo_bg_stitch" is a proven-fixed cause on the 4ed9cd80 decide basis; the live oracle 0c22b266 was not re-encoded here.

## Follow-ups
Design queue: 63 (consumes a-1), 64 (classifier over a-2 / b-1), 67, 66, 61.
