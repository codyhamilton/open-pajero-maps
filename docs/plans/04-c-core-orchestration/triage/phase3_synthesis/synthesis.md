# Plan 35 Phase 2 — plan 04 Phase 3 close synthesis

**Verdict: residual branch. Plan 04 Phase 3 is NOT closed.** G2, G3, G6 and G7 PASS; G1, G4, G5, G8 and G9 are RESIDUAL, so the close branch is not available.
No Phase 3 trailer is written.

- **Oracle in force:**
  `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`
  (`output/scratch-34/G_new/ALLDATA.KWI`).
- **Historical oracles, protected:** `2ee3456a…` and `4ed9cd80…`. Perth:
  `04be2f6e…`.
- **Gate table:** `gates.tsv`, one row per gate with state, evidence path,
  sha256 prefix and the quoted figure.
- **Open items:** `residuals.tsv`, one row each, with count or identity,
  evidence, owner and blocking class.

## Gate summary

| Gate | State | One line |
|---|---|---|
| G1 oracle chain | RESIDUAL | Every hop is signed and confined. 3-14 per-cell payload causes (AU 246,123 / Perth 795), 3-14 container accounting and the 3-11 routed proof are open (plan 36, Phase 1 in progress). |
| G2 live failing | PASS | 0 in all 9 kinds on `4e6b0de7` (P1 census). |
| G3 pin contract | PASS | ∅ = ∅ re-applied on `4e6b0de7`. |
| G4 checked reconciliation | RESIDUAL | Per-hop counts are recorded and sum exactly. Plans 29 and 34 are reconciled; the 3-11 and 3-14 hop moves are not explained. |
| G5 historical causes | RESIDUAL | The per-kind × cause table is in `gates.tsv`. 8,739 background_boundary + 137 background (180 groups) are unattributed (3-11 disc basis), as are polygon 65623 and R01 exclusivity. |
| G6 ops | PASS | `-j6` median 79.661 s; PSS max 7,599,962 kB ≤ 9,726,501; `-j1` identical. |
| G7 build | PASS | AU rebuild = `4e6b0de7`; Perth `-j1` = `-j4` = `04be2f6e`; pytest 1383 passed / 7 skipped / 0 failed at `873f161`. |
| G8 fix-review chain | RESIDUAL | 3-14 is not accepted (BOUNCE + overrule); 3-15, 3-16 and 3-17 are missing. Process note R-G8-5: plan 34 closed on a restricted suite. |
| G9 carried placement | RESIDUAL | Plan 30: 341 / 0 / 1 (row 246 open). Design 36 in progress. Design 37 closed. L8/L0 encoder trim on `4e6b0de7` and the ungated build wall are carried. |
| G10 doc consistency | RESIDUAL (non-gating) | OVERVIEW fixed here. The plan 31 / contract / `oracle_chain.tsv` "+60 B" wording belongs to plan 36 P1. |

## Blocking list

These are the `blocks-phase3` rows of `residuals.tsv`; OVERVIEW points here.

- **G1:** R-G1-1 to R-G1-4 (plan 36).
- **G4:** R-G4-1 (the 3-11 hop, unowned → Design) and R-G4-2 (the 3-14 hop,
  plan 36 Phase 3).
- **G5:** R-G5-1 to R-G5-4 (unowned → Design).
- **G8:** R-G8-1 to R-G8-4 (unowned → Design, or a Cody waiver).

## Carried, not Phase 3-blocking (`maps-parity-carried`)

- R-G5-5: historical `pinned_candidates.tsv`.
- R-G9-1: plan 30 row 246.
- R-G9-2: plan 30's 341 supply-path rows to implement.
- R-G9-3: encoder content trim on `4e6b0de7` (L8 road 308/14,012, the
  ">1% BLOCKER" line; L0 road 207; background 227). Design may promote it
  to `blocks-phase3`.
- R-G9-4: the full-build wall is 115.99 s against plan 04's "≪ 60 s", and it
  is ungated.

## Non-gating

- R-G8-5 (process): a plan that touches the encoder or build runs the full
  `parser/tests` before close.
- R-G10-1: "+60 B" wording (plan 36 P1).

## The parcel_mask regression (G7 input)

- **Failure:** `test_parcel_mask.py::test_fill_only_masked_and_absent_cells`
  failed in P1. It was bisected to plan 34 `5182c83`.
- **Root cause: a stale test.** The synthetic cell (720, 30) has only an
  out-of-span name, so its frame is the exact empty shell. It lies outside
  the synthetic mask, so plan 34's `_omit_outside_mask_shells` correctly
  omits it.
- **Fix (test only, at `a906818`):**
  - The test now expects the omission.
  - It adds an in-span outside-mask cell that must pass through byte-stable.
  - `build_alldata` is unchanged.
- **Record:** a note was added to `docs/plans/34-l0-empty-slot-frame-parity.md`.
- **Review:** the fix was independently reviewed in this phase's review.
- **Rebuild sha:** `9c99dcb..873f161` touches no build code outside the tests
  (only `parser/perf_inventory.json`), so the P1 rebuild sha stands at the
  close HEAD.

## Method and limits

- Synthesis is by Execute (Codex weekly-limited until 2026-10-10 11:50 AEST).
  This is disclosed.
- Every figure is quoted from the cited committed evidence or plan records.
  No review, re-oracle, ceiling or pin was invented.
- No brief 3-90 was run. No reseat of 170, 3-16 or 3-17.
- Codex confirmation reviews of plans 31/33/34 are pending the Codex reset.
  They are not part of G8: each of those plans already has a terminal review.

## Post-close residual ownership (plan 54 — 2026-10-08)

Historical synthesis above is unchanged: at plan-35 close time, G1/G4/G5/G8/G9 were
RESIDUAL and Phase 3 was not closed. **That verdict stands as history.**

Live ownership (tip `residuals.tsv` after plans 36–53 / 44 / 48–49; docs sync **54**):

- **Phase 3 still not closed.** No plan 04 P4–6. No 3-90. No reseat 170 / 3-16 / 3-17.
- **Oracle in force:** `88bd7852…` (plan **48** Design-accepted; Perth `04be2f6e…`).
  `4e6b0de7…` is historical (plan 34), protected.
- **G1 / G4 rows discharged** (plans 36 / 39) — not live undifferentiated blockers.
- **Closed residual work:** plans **43** (light set), **47** (completeness evidence),
  **49** (R-G8-2-f-a), **48** (R-G8-1-d-a + live oracle).
- **Live `blocks-phase3` owners:** plan **44** closed owner of R-G5-4-a/b (rows still
  open); plan **45** → R-G5-4-c, R-G8-1-f; plan **46** → R-G5-1/2, R-G8-4-c;
  plan **55** (closed, explained-dual-basis) discharged R-G8-1-b-a; Cody via Design (no waiver) → R-G8-1-a.
- **`maps-parity-carried` owners:** plan **50** → R-G9-2; **51** → R-G9-3-a;
  **52** → R-G9-3-b/c; **53** → R-G9-3-d; Cody via Design (no waiver) → R-G5-5, R-G9-4.
- Plans **56–59** (memory band) are closed ops work, not residual-row owners.

Authoritative table: `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/residuals.tsv`.
OVERVIEW Phase-3 blocker prose matches this map.

## Post-close residual ownership refresh (plan 60 — 2026-10-08)

The plan-35 synthesis and the plan-54 block above are unchanged as history. Live state at base
`b5c9ff9`, the parent of the plan-60 commits (after plans 45, 50–53, 55):

- **Phase 3 still not closed.** No plan 04 P4–6. No 3-90. No reseat 170 / 3-16 / 3-17.
- **Oracle in force:** AU `0c22b266…` (plan **53**, encoder `dv_assign` lon-wrap fix), over
  `aeae426c…` (plan **50**), over `88bd7852…` (plan **48**). Perth in force `5b86d33e…`
  (plan 53; `04be2f6e…` historical). All earlier oracles are historical and protected.
- **Discharged since plan 54:** R-G9-2 (plan **50**), R-G8-1-f (plan **45**), R-G9-3-d
  (plan **53**). R-G8-1-b-a (plan **55**) and R-G8-1-d-a (plan **48**) stay discharged.
- **Live `blocks-phase3` owners:** plan **44** (closed) for R-G5-4-a/b, with the
  still-outside@16 children going to Design (plan **62** is a box draft, not landed);
  plan **46** for R-G5-1/2 and R-G8-4-c, in progress (Execute) with nothing landed;
  Cody via Design (no waiver) for R-G8-1-a.
- **`maps-parity-carried`:** R-G5-4-c (plan 45: 80/80 `producer_home_outside_R_cap` at R=8;
  still-outside@16 is plan 62's scope, box draft); R-G9-3-a (plan 51: emission proven-cause;
  volume goes to Cody, F6 / kind-order); R-G9-3-b (plan 52: piece-count residual); R-G9-3-c
  (plan 52: volume goes to Cody, L8 selection expand); R-G9-3-d-rem (plan 53: 128 links); and
  the Cody holds R-G5-5 and R-G9-4. **Carried is not closed for parity.** These rows are
  named deviations that still count against end-to-end parity. They are only exempt from
  blocking the Phase 3 product close.
- No waivers, and no F6 / kind-order / L8-expand drafts (Cody open). Plans 56–59 are closed
  ops work, not residual owners. Plans 61 and 62 are box drafts only.

The authoritative table is still `residuals.tsv`; OVERVIEW matches this map.

**UPDATED by plan 62 (2026-10-09):** R-G5-4-a/b/c were re-decided under the plan-46 producer
(`p9_r01_residual/`). All three parents are discharged. R-G5-4-c (80/80 proven-fixed) is no
longer `maps-parity-carried`. The exact children are `blocks-phase3`:
- R-G5-4-a-1 (222 producer_ambiguous), owned by plan **63**;
- R-G5-4-a-2 (32 source-removed), owned by plan **64**;
- R-G5-4-b-1 (545 source-removed), owned by plan **64**.
