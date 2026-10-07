# PSS at ≤ -j6 and plan 04 Phase 3 close synthesis

Plan 35 measured the operational and build gates on the oracle in force,
`4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`, and held
every plan 04 Phase 3 gate against evidence.

- **PSS bar cleared** at `-j6`: median of three is 79.661 s; PSS max is
  7,599,962 kB, under the 9,726,501 kB ceiling.
- `-j1` is deterministic.
- The AU rebuild and Perth reproduce their pins.
- The full suite is green: 1383 passed / 7 skipped / 0 failed.
- **Phase 3 is not closed.** G1, G4, G5, G8 and G9 are RESIDUAL. The outcome
  is the exact residual list, and the Phase 3 blockers are its 14
  `blocks-phase3` rows.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
> Plans 31, 32, 33 and 34 are closed. Draft the PSS at `-j6` or lower plus Phase 3 close synthesis. Its outcome is an evidenced plan 04 Phase 3 close, or an exact named residual list (including plan 30's open rows if they are still open). Reference the oracle in force `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`; `2ee3456a…` and `4ed9cd80…` are historical and protected. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `parser/tools/run_heavy_python.py` with bounded or streamed loads (plan 25). Execute pushes straight to master: no feature branch, no PR. Do not draw plan 04 Phases 4–6 or plan 06. No 3-90 re-run. Do not reseat 170, 3-16 or 3-17.

## Why This Existed
- Plans 16 and 27–34 discharged several 3-90 blockers.
- No single record listed, gate by gate on `4e6b0de7`, which Phase 3 gates
  were evidenced.
- OVERVIEW still named "PSS contract" and "close synthesis" as open.
- No PSS/timing trio, no `-j1` measurement and no close-HEAD rebuild existed
  on the oracle in force.

## What Was Built
Lasting files are in `docs/plans/04-c-core-orchestration/triage/phase3_synthesis/`:

- `gates.tsv`: G1–G10, each with state, evidence path, sha256 prefix and the
  quoted figure;
- `residuals.tsv`: every open item, with count or identity, evidence, owner
  and blocking class;
- `synthesis.md`;
- `commands.md`: the exact Phase 1 chain;
- `evidence/`: K1 reports, shas, protected snapshots, wrapper logs, chain
  log, pytest tails.

Commits:

- `e2a2c71`: DESIGN.
- `b5e3c34`: IMPLEMENTATION and commands.
- `c51f053`: P1 evidence.
- `0d1ecef`: P1 close.
- `9c5f20e`: P2 close.
- The close-out commit.

### Phase 1 — ops and build gates on 4e6b0de7 (11:05–11:21 AEST, HEAD 9c99dcb)
- **K1 `-j6` ×3:** failing 0 each.
  - Walls 79.887 / 79.485 / 79.661 s (median **79.661 s** ≤ 120).
  - `pss_peak_kb` 7,549,093 / 7,555,806 / 7,599,962 (max **7,599,962** ≤
    9,726,501, the held ceiling).
- **K1 `-j1`:** 417.7 s. The report is identical to all three `-j6` reports
  and the dump run after `strip_compare_excludes`.
- **Census:** failing 0 in all 9 kinds. The `--dump-failures` counts are 0
  for the 5 DUMP_KINDS.
- **AU rebuild `-j4`:** sha = `4e6b0de7…`. Perth `-j1` = `-j4` = `04be2f6e…`.
- **Protected discs and spool:** hashes equal before and after.
- **Full `parser/tests`:**
  - At `0f3e530`: 1 failed (plan 34 regression `test_parcel_mask`).
  - After the test fix `a906818`, at `873f161`: **1383 passed, 7 skipped,
    0 failed**.

### Phase 2 — close synthesis (residual branch)
- **Gate states:**
  - **PASS:** G2 (live failing 0), G3 (pin contract ∅ = ∅), G6 (ops),
    G7 (build).
  - **RESIDUAL:** G1 (3-14 payload causes, 3-14 container accounting, 3-11
    routed proof; plan 36), G4 (3-11 and 3-14 hop `checked` moves not
    explained; plans 29 and 34 reconciled), G5 (8,739 background_boundary +
    137 background in 180 groups, polygon 65623, R01 exclusivity), G8 (3-14
    not accepted; 3-15/3-16/3-17 reviews missing), G9 (plan 30 341/0/1; L8/L0
    encoder trim; ungated build wall).
  - **RESIDUAL, non-gating:** G10 ("+60 B" wording outside OVERVIEW, owned by
    plan 36 P1).
- **OVERVIEW:** the blocker paragraph now points to the `blocks-phase3` rows,
  and the CHM, plan-30 and +60 B drift is corrected.
- There is no plan 04 Phase 3 record and no Phase 3 trailer.

## Deviations
- **Synthesis seat.** Codex was weekly-limited (resets 2026-10-10 11:50
  AEST), so Execute wrote the synthesis. The independent review was by a
  Claude CLI clean-context seat. Both are disclosed.
- **Extra pytest run.** P1's full-suite gate failed on a plan 34 regression.
  The regression was root-caused (a stale test) and fixed on master before
  synthesis. A second guarded full run at `873f161` gives G7.
- **Owner fields.** `residuals.tsv` uses owner "unowned → Design" where no
  plan exists. Two non-gating classes, `process` and `G10`, are added beside
  `blocks-phase3` / `maps-parity-carried`.

## Review
Independent clean-context review (Claude CLI) re-derived every gate from the
cited artefacts.

- **First pass: REMEDIATE.** All gate states agreed. The findings were
  bookkeeping:
  - **F1 (high):** the L8 road TRIM ">1% BLOCKER" on `4e6b0de7` was carried
    nowhere. Added as R-G9-3.
  - **F2:** per-hop `checked` counts exist. R-G4 was split by hop, and plans
    29/34 are reconciled.
  - **F3:** plan 34 closed on a restricted suite. Added as R-G8-5.
  - **F4:** the per-kind × cause table and basis note were added to G5.
  - **F5–F7:** wording.
  - **F8:** the build wall versus the "≪ 60 s" budget. Added as R-G9-4.
- **Re-review of the remediation: PASS.** F1–F8 are resolved, gate states and
  verdict are unchanged, and the OVERVIEW blocker list equals the
  `blocks-phase3` rows. The reviewer recomputed the per-hop sums and G5 cause
  counts.
- **parcel_mask:** the reviewer judged the fix a stale test correctly fixed,
  not a relabel.

## Residual Risks
- Phase 3 stays open on the 14 `blocks-phase3` rows of `residuals.tsv`.
- Encoder content trim on the oracle in force (L8 road 2.198%) has no
  R-parity proof (R-G9-3).
- The ops figures are single-host measurements on codyh-ubuntu.

## Follow-ups
Each `residuals.tsv` row names its owner:

- **Plan 36:** R-G1-1..4, R-G4-2, R-G10-1.
- **Design:** R-G4-1, R-G5-1..4, R-G8-1..4 (or a Cody waiver), R-G9-3,
  R-G9-4, R-G8-5 (a workflow rule: full suite before close when a plan
  touches the encoder or build).
- **Plan 30 → Design:** R-G9-1 and R-G9-2.
- **Plan 31:** R-G5-5 (`pinned_candidates`, not required for live close).

## Decisions Worth Keeping
- "No 3-90 re-run" forbids executing brief 3-90, not plan-owned gate
  measurements. The ops/build gates were measured under this record.
- A Phase 3 close may be claimed only with G1–G9 all PASS. A gate with a
  named open item is RESIDUAL, never PASS-with-caveat.
- Per-hop K1 `checked` reconciliation uses recorded per-hop reports. Hops
  whose expected equals new (plan 29) or whose totals are unchanged (plan 34)
  are reconciled.

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

The plan-35 synthesis and the plan-54 block above are unchanged as history. Live state at tip
`b5c9ff9` (after plans 45, 50–53, 55):

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
