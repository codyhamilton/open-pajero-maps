# Plan 64 — revision note (Design, 2026-10-09 ~14:45 AEST, tip `61d2fe8`)

Execute has already started 64. This note says what changes for work in progress.

## Scope

Was: R-G5-1-b only (50 rows / 1 group). Now: **23 groups / 627 rows**:

| Row | Groups | Rows | From |
| --- | ---: | ---: | --- |
| R-G5-1-b | 1 | 50 | plan 46 (unchanged) |
| R-G5-4-a-2 | 1 | 32 | plan 62 child (`b889c2e`) |
| R-G5-4-b-1 | 21 | 545 | plan 62 child: 432 source-removed + 97 RC3 far-producer + 16 RC4 divided-leaf |

Group list: `p9_r01_residual/transitions.json` `source_removed_groups` (sha `d51baafb…`). All 23 are L0 type 288 with `clip_size_d35b565` 0; 17 distinct producers in total.

## What changes

1. **Same five-way test (H1–H5) per group.** No group is discharged by analogy; each gets its own verdict and proof.
2. **Phase 1** now covers all 23 groups: sidecar producer proof per group, extract trace per distinct producer (17), on-frame vertex counts, R / `013586b5` / `4ed9cd80` / `0c22b266` footprint per group. H1 is checked first for the 113 rows plan 46's fixes brought in (RC3 97, RC4 16).
3. **Sidecar:** plan 63 closed; use the committed `p7_producer_tie/sidecar/sidecar_33006aa.patch`. The weaker fallback is dropped.
4. **The classifier** is run over all 23 groups here, instead of being handed to plan 62 (62 is closed). The old "469 rows" figure is superseded (plan 62: 5 → build via U4F_RING, 464 stay, +113).
5. **Residuals:** R-G5-1-b, R-G5-4-a-2 and R-G5-4-b-1 are each discharged only when all their groups have a proven outcome; otherwise exact per-group children.
6. **Oracle order:** if an H2 / H5 fix moves the oracle, it lands before plan 68's successor work, and 68 re-bases on it.

## What does not change

- Intent, the H1–H5 definitions, the two-proof bar for H4, the R comparison before any discharge, memory guardrails, scratch hygiene and receipts.
- Work already done for R-G5-1-b stands and is reused.

## Not changed by this revision

F6 / kind-order, roads preference, L8 expansion (Cody). All 23 groups are type 288, the L0 catch-all; this plan proves the empty-clip cause and does not decide F6.
