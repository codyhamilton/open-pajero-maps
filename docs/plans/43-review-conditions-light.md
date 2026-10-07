# Plan 40 review conditions (light set): 3-14 and 3-17 evidence regenerated or superseded by proof

Plan 43 closed eight Design-owned residual rows left by plan 40's review-of-record
for 3-14 and 3-17. Each ends as `regenerated`, `superseded-by-proof:<cite>` or
`unverifiable:<root cause>`, with evidence committed under
`triage/independent_reviews/3-1{4,7}/conditions/`. Two new `blocks-phase3` children
were opened from findings (R-G8-1-d-a encoder decline; R-G8-2-f-a never-committed
file) and one from the terminal review (R-G8-1-b-a window count mismatch). Completeness
evidence rows and R-G8-4-c stay with designs 47 and 46. R-G8-1-f stays with design 45;
R-G8-1-g with 47. Plan 04 Phase 3 is **not** claimed closed.

## Intent
Cody's standing rule (2026-10-05, hard) and ruling 5 (2026-10-06): for the plan 40
review-condition rows, regenerate the lost evidence where possible; otherwise each
row becomes **superseded-by-proof** or a **named unverifiable residual**. Design
grants no waivers. Oracle `4e6b0de7…`. Heavy work under flock + `run_heavy_python.py`,
≤ `-j4`. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Why This Existed
Plan 40 discharged "review missing" for 3-14 to 3-17 but left 21 condition rows in
`residuals.tsv`. This plan took the ones closable by light regeneration or a later
committed proof. Lost scratch included `scratch-3-14/{windows,review_stress,k1_full,
pytest_full,goldens_changes,finish_gates}` and `scratch-3-17/{kind_views,classify_kinds,
classify.stderr}`.

## What Was Built
**Changed:**
- `parser/tests/test_bg_eo_stress.py` (new; seeded stress + degenerate/termination/capacity);
- `triage/independent_reviews/3-14/conditions/` (K1 evidence, golden+TRIM, stress
  characterisation, decline locus, suite logs, terminal REVIEW);
- `triage/independent_reviews/3-17/conditions/` (forced-zero classify, dump_ext43 rebuild,
  per-row assignment, S2a stderr);
- `residuals.tsv`; `docs/provenance.md` (`scratch-43`).

No encoder or build output bytes changed. No protected disc or spool was written.

### Phase 1 — 3-14 conditions b, c, d, e, h
- **R-G8-1-c → regenerated.** K1 built at `1cf40f8` on `4ed9cd80` (sha re-hashed),
  `-j4`, dump off, wrapper `--cwd` = throwaway worktree: completeness **776**,
  background / background_boundary / interior_cover **0**. First launch omitted
  `--cwd` and ran master's checker (completeness 0); kept as the HEAD K1 for b.
- **R-G8-1-b → superseded-by-proof.** Whole-disc K1 on `4ed9cd80` (3-14 encoder from
  the original spool) background family 0 — plan 39 `k1_314.json` (path pinned by
  `protected_after_39.json`) and this plan's HEAD K1. The nine 3-13 CF windows are
  subsets. Per-window before counts (`window_before.json`) are context; boundary
  counts disagree with the 3-13 table → **R-G8-1-b-a** (review F1).
- **R-G8-1-d → regenerated**, finding **R-G8-1-d-a.** Seeded stress (1,000 self-crossing
  rings, seed 4314) plus 10 degenerate/termination/capacity cases. All pass except
  ring 359 (decline −1). Characterisation: 5 / 20,000 (0.025%). Decline site
  `_cenc.c:885` (arms not split) for 3/5 under instrumentation (`decline_locus.json`);
  all 5 size −1 uninstrumented. Build treats a decline as an error (`_cenc.c:1070`,
  `_e2.c:48`). No built AU/Perth spool has reached it. Plan 48 owns the root cause
  and fix.
- **R-G8-1-e → regenerated.** Full `parser/tests` in the **main** checkout
  (`/home/codyh/workspace/open-pajero-maps`, `.git`), master `d185fb6`: **1458 passed,
  10 skipped, 1 xfailed**, exit 0. `test_dump_join_memory` 13/13 there. Two earlier
  launches were killed by host reboots (17:53, 18:47 AEST).
- **R-G8-1-h → regenerated.** Golden `l0_divided_trim_halo` sha `905d9c95…` (310,268 B)
  recorded; window rebuilt byte-identical with TRIM road 207/1,083 and background
  227/8,824 (replaces `finish_gates.log`). Full-AU TRIM lines quoted with plan 36
  log sha. `scratch-3-12/G_build.log` citation dropped.

### Phase 2 — 3-17 / 3-15 classify conditions
- **R-G8-4-a → regenerated.** Forced `other_mechanism` to 0 on plan 31 changed cells
  (34 rows = O05×30 + O04×4); classify on retained dump `1a91b1c2…` (also regenerated
  byte-identically by K1@`1cf40f8`): **776/468/308**, O01 363 / O04 3 / O05 102,
  identical on 3-17-era CLI (`ac1a64d`) and master. Per-row assignment committed.
  name_anchor kind view: 1 → O03 spool, PARTITION OK (byte 6 inferred from
  `cause_table.md:36` + unchanged cell; S2e verifies CLI on that inferred byte).
  Premise shared with R-G8-2-f-a (forced set from plan 31 list, not the lost
  `AU.differing_cells.tsv`).
- **R-G8-4-b → regenerated.** 3-17-era CLI on rebuilt dump_ext with zero-row kinds
  exits 1: `ValueError …background.bin: zero-row kinds are unsupported (as in the
  baseline)` — the S2a stderr.
- **R-G8-2-f → superseded-by-proof.** Plan 37's forced-zero identity re-executed
  through the classify CLI (consistent). Literal `AU.differing_cells.tsv` ≡ plan 31
  equality is **R-G8-2-f-a** (`unverifiable:never-committed`, Cody via Design).

## Decisions Made
1. Plan number 43. Master direct. Two phases. Refine skipped (both approaches known).
2. Each row's end state is one of {regenerated, superseded-by-proof:<cite>,
   unverifiable:<root cause>}.
3. R-G8-1-g and completeness rows → design 47; R-G8-4-c → 46; R-G8-1-f → 45.
4. Design advance ruling on R01 dual-cause (plan 39) and ruling 5 (regenerate /
   supersede / named unverifiable) applied; no new Cody rulings claimed.

## Review
Terminal review: Claude CLI clean-context seat (disclosed; Codex weekly-limited until
2026-10-10 11:50 AEST). Verdict **PASS_WITH_FOLLOWUPS**
(`triage/independent_reviews/3-14/conditions/review-REVIEW.md`). No blocker or high
findings. F1–F7 applied at close-out (R-G8-1-b-a opened; d-a locus reword + committed
instrumented trace; 2-f/4-a wording; build_ext cite; README sha-binding notes; stress
docstring; provenance hygiene).

## Residuals and follow-ups
| Row | State | Owner |
| --- | --- | --- |
| R-G8-1-b/c/d/e/h, R-G8-2-f, R-G8-4-a/b | discharged | plan 43 |
| R-G8-1-b-a | blocks-phase3 (window count mismatch) | Design |
| R-G8-1-d-a | blocks-phase3 (EO decline; plan 48) | Design |
| R-G8-2-f-a | blocks-phase3 (never-committed file; plan 49) | Cody via Design |

Evidence regenerators and sha pins: see the two `conditions/README.md` files.
Scratch: `output/scratch-43/` (BOM in `docs/provenance.md`).

## Provenance
Master `6538530` at design land (`616fe4c`); closed at the SHA of this record's
commit. Sources: plan 40 review residuals; plan 39 `k1_314.json` / `k1old_pre311.json`;
plan 37 F2 identity; plan 28 assignment; plan 41 suite posture; `causes_rootcause.md`
L56–79. Reviewer seat disclosed above.
