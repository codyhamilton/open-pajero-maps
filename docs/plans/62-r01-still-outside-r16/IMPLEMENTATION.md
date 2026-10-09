# Plan 62 — IMPLEMENTATION

Status: Phases 1–3 done (2026-10-09 12:20 AEST); landing on `4bb96f0` (plan 65 close-out). Original base `origin/master` `8498eec` (plan 46 close-out). Checkout
`/home/codyh/workspace/open-pajero-maps-14-completeness` (clean at 8498eec; has the venv and the `output` link).

## Ground truth vs the DESIGN draft (the draft was grounded at `10a976a` and is stale)

| Draft says | Live | Source |
| --- | --- | --- |
| Oracle in force `aeae426c…` | AU **`0c22b266…`** (plan 53), Perth **`5b86d33e…`**. Not used here: no encode in this plan; the R01 counterfactual discs are 013586b5 → 4ed9cd80 | plan 53 record |
| R-G5-4-c (plan 45) is a non-goal | **In scope** (Design confirmation 2026-10-08 ~10:37). The 80 rows are part of the still-outside@16 census | parent / Design |
| Mass stopped at ~30k/95,059 | **Mass complete**: chunk1 30k + chunk2 65,059 = 95,059 (plan 44 Unit 4d), widen@16 on 7,258 (4,042 recovered / 3,216 still outside), proven-fixed applied (Unit 4f). Reused; nothing regenerated | `p5_owner_exclusive/phase2_summary_full.json` |
| 45 / 46 untouched | 45, 46 and 60 are **closed**. Plan 46's tracked producer scan (RC2–RC6) covers every background row of the 013586b5 dump | records 45, 46, 60 |

Rules in force:
- R = 8 is the mass default; widen@16 is only plan 44's historical result on the outside set.
- No waivers.
- No F6, kind-order or L8 changes.
- No plan 04 P4–6, no 3-90, no reseat.
- Flash seat only.
- Heavy work only under flock + `run_heavy_python --memory-max 12G`.
- Disk is critical (~5.3 GB free on /home): estimate before each run, delete nothing.

## Phase 1: census join (light, streaming, no clipping)

`historical_bg/p9_r01_residual/census_join.py` joins every R-G5-4 row to the plan-46 scan of the 013586b5 background dump: 95,059 plan-44 decisions (leaf paths from rows_weak/rows_none) plus plan 45's 80 rows. Join key: full leaf key + shape + vert + code. The background dump differs between 87a01b14 (the plan 44 basis) and 013586b5 only in cell 0/1769/587, and no R-G5-4 row lies there.

Result: **95,139 / 95,139 joined**, 0 rows in the basis cell.

Cross-tab of the plan-44 class against the plan-46 corrected-contract producer (Moore R=8 ∪ far bbox-meet homes, per-piece byte match, same-type producer, divided-leaf clip rect):

| Parent | Plan-44 class | Rows | Plan-46 producer |
|---|---|---|---|
| R-G5-4-a | build:eo_bg_stitch | 87,648 | unique-byte |
| R-G5-4-a | producer_home_outside_R_cap (still outside @16) | 3,023 | unique-byte |
| R-G5-4-a | producer_ambiguous | 2,561 | unique-byte |
| R-G5-4-a | producer_ambiguous | 222 | producer_ambiguous |
| R-G5-4-a | skip_divided_leaf | 525 | unique-byte |
| R-G5-4-a | disagree_no_oe | 118 | unique-byte |
| R-G5-4-a | disagree_source_removed | 37 | unique-byte |
| R-G5-4-b | build:eo_bg_stitch | 95 | unique-byte |
| R-G5-4-b | disagree_source_removed | 432 | unique-byte |
| R-G5-4-b | producer_ambiguous | 189 | unique-byte |
| R-G5-4-b | producer_home_outside_R_cap (still outside @16) | 193 | unique-byte |
| R-G5-4-b | skip_divided_leaf | 16 | unique-byte |
| R-G5-4-c | producer_home_outside_R_cap (@16, plan 45) | 80 | unique-byte |

What the cross-tab shows:
- **Still-outside@16 (3,216, plus R-G5-4-c's 80):** the corrected producer is found for every row.
  - 2,622 rows: producer home more than 16 cells away. This is plan 46 RC3, far producers. Plan 44's mass and widen used Moore(R) only; design 44's "bbox-meet ∪ Moore(R)" union was never implemented.
  - 32 rows: home within 9..16.
  - 562 rows: home within 8.
  - The 594 rows with homes within 16 point at RC2 (whole-blob vs per-piece match) or RC5. Phase 2 confirms which.
  - R-G5-4-c's 80 rows: all homes within 8. They are depth-2 divided leaves that plan 45 clipped with the full frame `[0,cr]`, which is plan 46 RC4.
- **skip_divided_leaf (541):** plan 44 skipped depth > 1 leaves (RC4 tool gap). All 541 have a unique-byte producer.
- **producer_ambiguous (2,972):** 2,750 become unique-byte, and 222 stay ambiguous. Plan 44 did not filter candidates to the record's type (RC5), and matched whole blobs (RC2).
- **Proven rows (87,743):** all stay unique-byte. **160 have a different producer home** from plan 44's, so their stitch must be re-verified with the corrected producer.

Disc note: plan 44's proven-fixed pass (Unit 4f) ran with `scratch-14/G_new` re-pointed at `scratch-48/G_new`. That file is 1,692,079,168 B, built 17:09 Oct 7, so it is the plan-48 successor and not 4ed9cd80 (1,692,105,152 B). The clause cites 4ed9cd80. Phase 2 re-decides every row against the 4ed9cd80 reference (`scratch-45/ref_d35b565`, MATCH per plan 45).

## Revised design (Design 2026-10-08 ~11:00) and resumption

DESIGN.md and REVISION-NOTE.md were re-copied from the box. Mass finish was dropped and replaced by the re-decide. R-G5-4-c is in scope with gates G-c1..G-c6, and `producer_home_outside_R_cap` is barred as an RC. Plan 65 (owner wording) landed first: `6032bce`, close-out `4bb96f0`.

The host was offline from 2026-10-08 ~11:37 to 2026-10-09 12:11 AEST, with no reboot. The phase 2b double run had already finished before the drop (REDECIDE_IDENTICAL). Disk was cleared on 2026-10-09 before resuming; see `docs/provenance.md` (Plan 62).

## Phase 1 — census (done)

`p9_r01_residual/census.tsv.gz` + `census.json`:
- **Rows:** 7,396 (a 6,486 / b 830 / c 80). The old classes reconcile exactly to plan 44's table and to plan 45's 80 rows:
  - by cell: (1797,424) 12, (828,862) 52, (832,856) 16;
  - by depth: d2 for a 525, b 16, c 80.
- **sha256:** `07523d89…`.
- **Input:** `census_join.tsv.gz` (`ac26effb…`; 95,139 rows; copied from `output/scratch-62`).

## Phase 2 — re-decide under the plan-46 producer (done)

### Drivers and runs
- **Driver:** `p9_r01_residual/redecide.py`, with pure helpers in `parser/tools/r01_redecide.py` (tests: `parser/tests/test_r01_redecide.py`, 8 pass; `perf_inventory` entry).
- **Configs:** FULL (plan 46), -RC2, -RC3, -RC4, -RC5 (single-fix ablations, all at Moore(8)) and PLAN44 (all off, plan 44's own Moore radius). The first run gave -RC3 plan 44's radius (16 on the outside set), which is not single-fix. Codex review B caught this; -RC3 is now pure (Moore(8), no FarHomes), and both runs were redone.
  - Every residual group got all six configs. This is exhaustive, so no sample was needed.
  - Every proven group got FULL and PLAN44.
- **Discs, clippers, spool:**
  - old disc `ref_33006aa`; new disc `ref_d35b565` (4ed9cd80);
  - producer clip `cenc_33006aa`; decide clip `cenc_d35b565`;
  - spool `extract_timing/spool`; R=8 ∪ FarHomes.
- **Run A:** `p9_r01_residual/redecide.tsv.gz`. **Run B:** `output/scratch-62/runs/redecide_b.tsv.gz`. They are **byte-identical** (cmp of both the groups and rows80 files).
- **Peak (rerun):** VmHWM A 3.84 / B 3.88 GiB, ~385 s per run; wrapper max RSS 3.88 GiB, memory.peak 4.52 GiB. Ledger: `56/ledger/r01_residual_plan62.json` + SUMMARY row.
- **Companion run:** phase23 decide (the unchanged design-44 limb) on all 95,139 rows, twice, DECIDE_IDENTICAL (`verdicts_census.tsv.gz`). It agrees with FULL on 95,059 / 95,059 a/b rows. For c it is superseded by G-c4: the old pardiv1 leaf keys do not exist on d35b565.

### Validation of the harness
- **PLAN44 reproduces plan 44's class for 95,054 / 95,059 rows.** The 5 exceptions are leaf 0/1249/881/(1569,), shape 1. Plan 44 Unit 4f (`proven_fixed_recovers.py` L246–251) kept only `producer_home` and took the first ring of (1262,881): ri 0, whose d35b565 clip is empty. The producer is ri 1 (clip 178). Evidence: `u4f_probe.json`. Named **U4F_RING**.
- **FULL equals the plan-46 scan producer status for 95,139 / 95,139 rows.**

### Transitions and attribution (`transitions.json`)

| Parent | Old → new | Rows | Fix whose single removal reverts it |
|---|---|---:|---|
| a | ambiguous → build | 2,561 | RC2 2,536, RC5 25 |
| a | ambiguous → ambiguous | 222 | — |
| a | outside@16 → build | 3,023 | RC3 2,525, RC2 466, RC2+RC3 32 (each single removal reverts) |
| a | skip_divided → build | 525 | RC4 |
| a | no_oe → build | 118 | RC2 |
| a | source-removed → build | 5 | U4F_RING |
| a | source-removed → source-removed | 32 | — |
| b | ambiguous → build | 189 | RC2 |
| b | outside@16 → build | 96 | RC2 |
| b | outside@16 → source-removed | 97 | RC3 |
| b | skip_divided → source-removed | 16 | RC4 |
| b | source-removed → source-removed | 432 | — |
| c | outside@16 → build (G-c4) | 80 | RC4 |

RC6 changes only the mechanism bit, so it moves no class.

### Same-type audit (`audit.json`)
- All 87,743 proven rows have a same-type producer under the plan-44 matcher.
- All of them stay build under FULL.

### Residuals
- **222 ambiguous** (8 groups; `ties_ambiguous.json`). Two same-type rings each emit a piece byte-equal to the record (the shared piece; byte-identical record pairs such as shapes 1/3). The decide limb builds under either tied candidate (8/8 build/build), but no unique producer is proven. Handed to **plan 63**.
- **577 source-removed** (a 32 / b 545). The producer is in the candidate set, but its d35b565 clip is sz 0, the same mechanism as R-G5-1-b. Handed to **plan 64**.

### R-G5-4-c gates

| Gate | Result |
|---|---|
| G-c1 | `window_control.json` ALL_OK, reused (sha `bd13acb3…`). |
| G-c2 | 80/80 unique-byte under Moore(8) ∪ FarHomes with divided geometry. All producers are within Chebyshev 1 of home. Ablation: -RC4 (full frame) gives producer_none for all 80, which is plan 45's verdict. |
| G-c3 | `redecide_rows80.tsv.gz`. Of 58 src rows: 14 match; 44 mismatches, each named row by row (src in the candidate set, same type, clip non-empty, not byte-equal to the record). Per brief 3-03, src is the nearest same-type shape within 64 raw, not the producer. 22 rows have src = -1 and are decided on evidence. |
| G-c4 | 80/80 build:eo_bg_stitch. Every covering d35b565 leaf was clipped: (828,862) 4→1 (988); (832,856) 4→16 (768,2/3/6/7); (1797,424) 4→1 (1285). Each has a byte and/or owner-exclusive-vertex witness inside the old rect. Clause (c) is cited but never used alone. |
| G-c5 | No radius label is used. |
| G-c6 | The double run is byte-identical. |

## Phase 3 — discharge / children (done)

- **`residuals.tsv`:** "UPDATED by plan 62" appended to R-G5-4-a/b/c. Parents now read `discharged-plan-62`, and R-G5-4-c is no longer maps-parity-carried. New children, all `blocks-phase3`:
  - R-G5-4-a-1: 222 ambiguous → plan 63;
  - R-G5-4-a-2: 32 source-removed → plan 64;
  - R-G5-4-b-1: 545 source-removed → plan 64.
- **OVERVIEW:** ownership row updated, the R-G5-4-c carried row removed, and the L108 pointer fixed.
- **Also updated:** the `synthesis.md` note, `causes_residual.md` note and provenance entry.
- No Phase 3 product-close claim. No waivers.

## Reproduction (the run scripts lived in scratch, which has been deleted)

```
H=docs/plans/04-c-core-orchestration/triage/historical_bg
python $H/p9_r01_residual/census_join.py        # -> output/scratch-62/census_join.tsv.gz (committed copy: p9_r01_residual/census_join.tsv.gz, sha ac26effb…)
python $H/p9_r01_residual/census.py             # -> p9_r01_residual/census.tsv.gz
python -B parser/tools/run_heavy_python.py --memory-max 12G --log <log.json> -- \
  .venv-rp/bin/python -B $H/p9_r01_residual/redecide.py --census $H/p9_r01_residual/census_join.tsv.gz \
  --src80 $H/p4_ceiling/rows_80_keys.tsv --old-disc output/scratch-45/ref_33006aa/ALLDATA.KWI \
  --new-disc output/scratch-45/ref_d35b565/ALLDATA.KWI --cenc-old output/scratch-46/cenc_33006aa/kiwiw/_cenc.c \
  --cenc-excl output/scratch-46/cenc_d35b565/kiwiw/_cenc.c --spool <extract_timing/spool> \
  --modes residual,audit,ceiling --out <out.tsv.gz>              # run twice, cmp
python $H/p9_r01_residual/summarize.py          # transitions.json, audit.json
```

The phase23 decide uses `p6_producer/phase23.py decide`, run with identity from `make_identity.py`, `--r 8`, and the same discs and clipper.

## scratch_receipt — Phase 1 (deviation, recorded honestly)

There is no separate Phase 1 receipt: Cody's scratch rule arrived on 2026-10-09, after Phase 1 had already run on 10-08. Phase 1's scratch was `output/scratch-62/census_join.tsv.gz` and `identity_census.tsv.gz`. Phase 2 consumed both, but they were not moved under `keep/`. They were deleted in the first Phase 2 receipt below. `census_join.tsv.gz` was first cmp-verified against its committed copy, sha ac26effb…. Phase 1's committed outputs are `census.tsv.gz` 07523d89… and `census.json`.

## scratch_receipt — Phase 2, first run (2026-10-09 12:33 AEST; taken late because the host was offline 10-08 11:37 → 10-09 12:11)

1. `du -sb output/scratch-62`: **3,699,606 B** before, path **gone** after (`test ! -e` → true). Real path: `/home/codyh/workspace/open-pajero-maps/output/scratch-62`.
   - Deleted: `census_join.tsv.gz` + json (cmp-identical to the committed copy), `identity_census.tsv.gz`, `tie/` (probe .so), and `runs/`.
   - `runs/` held: the phase2/phase2b/redecide scripts and logs, run-B copies (`verdicts_census_b`, `redecide_b*`; the byte compare was recorded as DECIDE_IDENTICAL / REDECIDE_IDENTICAL first), smoke_ceiling outputs, and wrapper JSON. Wrapper peaks had already been copied into `56/ledger/r01_residual_plan62.json`.
2. **Kept, all committed** under `p9_r01_residual/` (sha256):
   - `census.tsv.gz` 07523d89…
   - `census_join.tsv.gz` ac26effb…
   - `redecide.tsv.gz` ca6b5abe… (superseded by the rerun below)
   - `redecide_rows80.tsv.gz` 767865db…
   - `verdicts_census.tsv.gz` 69b49f6a…
   - `transitions.json` af60d14a…
   - `audit.json` a7802510…
   - `ties_ambiguous.json` 8fa40654…
   - `u4f_probe.json` 1eec00a3…
   - plus the ledger json.
   
   Nothing is kept in `keep/`.
3. **Worktrees:** plan 62 added none. It ran in the existing `open-pajero-maps-14-completeness` checkout, which holds the venv. Plan 65's worktree is handled in the Phase 3 receipt.
4. **Temp dirs and scopes:**
   - `/tmp/tmp4am5j1tn` (u4f probe .so) removed. `/tmp/p62_pytest.log` removed.
   - No `p62_redecide_*` or `p46_decide_*` temp dirs remain.
   - No `maps-heavy-*` scope remains. One stale *failed* plan-46 scope record (`maps-heavy-2728289`, a memory self-test) was cleared with `systemctl --user reset-failed`; nothing was running.
5. `df -h /home` after: 11 G free (97 %).

Stale-scratch clear before resuming (2026-10-09, Maps Manager request), in `output/scratch-46/`: `gatework_full_b` 5.2 G (plan-46 run B, identical to A), `gate_v2_blob` 170 M, `gate_v3_piece` 167 M. /home went from 5.0 G free to 11 G.

Tests: `parser/tests` 1513 passed, 9 skipped (10 m 36 s).

## Codex review 1 (land `f6ba75a`): VERDICT FIX

The seat is now Codex (CHM, 2026-10-09). `codex exec -s read-only`.
- **A, C, D, E, F, G: PASS.**
- **B: FAIL.** `-RC3` also switched to plan 44's radius, so it was not a single-fix ablation.
- **H: FAIL.** There was no per-phase Phase 1 receipt, and `output/scratch-62/review` existed after the receipt said the path was gone.
- **Non-blocking:** the residual rows cite `docs/plans/62-r01-still-outside-r16.md`. That record is created at close-out.

Fixes:
- **B:** `-RC3` is now pure (Moore(8), no FarHomes) and has a unit test. The re-decide was rerun twice under the wrapper (REDECIDE_IDENTICAL).
  - The only attribution change: of a's 3,023 outside→build rows, 32 rows (one group, producer 11 cells away) are now RC2+RC3. Each single removal reverts them. The remainder are RC3 2,525 and RC2 466.
  - Classes, the audit and rows80 are unchanged.
  - New `redecide.tsv.gz` 9c47f1ef…, `transitions.json` d51baafb…, `audit.json` fcafc023…; `redecide_rows80.tsv.gz` unchanged at 767865db….
  - Ledger and SUMMARY updated with the rerun peaks.
- **H:** the Phase 1 deviation is recorded above, and a fresh Phase 2 receipt for the rerun follows.
- The driver now removes its probe temp dir at exit (`atexit`).

## scratch_receipt — Phase 2 rerun (2026-10-09 ~13:25 AEST)

1. `du -sb output/scratch-62`: **327,679 B** before. Contents were `runs/` and `review/`:
   - `runs/`: rerun.sh, rerun.log, wrapper json/time, run-B copies `redecide_b*` (byte compare recorded first);
   - `review/`: codex review 1 prompt/stdout/stderr/last.md (verdict recorded above).
   
   After: path **gone** (`test ! -e` → true).
2. **Kept, all committed** under `p9_r01_residual/`: `redecide.tsv.gz` 9c47f1ef…, `redecide_rows80.tsv.gz` 767865db…, `transitions.json` d51baafb…, `audit.json` fcafc023…, plus the ledger json. No `keep/`.
3. **Worktrees:** none added by plan 62.
4. **Temp dirs and scopes:**
   - `/tmp/p62_redecide_g9hvwriy` and `/tmp/p62_redecide_potzbhhu` (probe .so) removed.
   - No `maps-heavy-*` scope remains (`systemctl --user list-units --type=scope --all`: 0).
5. `df -h /home`: 11 G free (97 %).
