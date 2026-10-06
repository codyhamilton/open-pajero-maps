# Independent review of 3-14 (landed tip) and science units 3-15, 3-16, 3-17

Plan 40 closed two phases. The independent reviews of record for 3-14,
3-15, 3-16 and 3-17 were written by a Claude CLI clean-context seat
(disclosed; Codex is weekly-limited). All four verdicts are
**ACCEPT-WITH-CONDITIONS**.

- **"Review missing" (R-G8-1..4):** discharged, per the Design ruling.
- **Conditions:** every UNVERIFIABLE or FAIL clause is a named residual
  (R-G8-1-a..h, R-G8-2-a..f, R-G8-3-a..d, R-G8-4-a..e). There are 22 open
  and 1 discharged by citation (R-G8-4-e). None is counted proven.
- **3-14 build wall FAIL (R-G8-1-a):** 26.28 s → 90.23 s at `-j4`. It is
  owned by plan 41 Phase 1 alongside R-G9-4.

Reviews and the imported adversarial report are kept in `docs/plans/04-c-core-orchestration/triage/independent_reviews/`. No unit
was re-run or rewritten. Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
> 
> Close Design-owned residual rows R-G8-1..4 (3-14 not accepted; independent reviews of 3-15, 3-16 and 3-17 missing). Model on plan 27's independent review. Review is not reseat: the units are not re-run and their records and outcomes are not rewritten. Oracle `4e6b0de7…` or later. Heavy work, if any, only under flock plus the wrapper. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief. Do not reseat 170, 3-16 or 3-17.

## Why This Existed
Plan 04's dependency gate (3-90 brief: "if any fix unit is unreviewed, report blocked") and plan 35 G8 leave four units without an independent review of record.

**Ground (master `b10e787`; host read-only 2026-10-06 AEST):**

| Row | Unit | State | Retained evidence |
| --- | --- | --- | --- |
| R-G8-1 | 3-14 EO-aware bg stitch (`d35b565`, merged `414c5fe`, tip `a10585a`) | DeepSeek adversarial review BOUNCED stale tip `67e48d9`; Design overruled against `a10585a`; no independent review of the landed tip | `IMPLEMENTATION.md` L218–235; `test_bg_eo_stitch.py`; goldens recapture. **The adversarial report exists at host `open-pajero-maps-3-14/output/CHM-3-14-adversarial.md`** (residual says "not retained": it was not copied into the repo). Plan 36 P1–P2 container accounting; P3 per-cell causes (running) |
| R-G8-2 | 3-15 cell-local representability (science) | no review | `triage/completeness_3-15_cell_local.md`; scratch-3-15 data gone (worktree has only CHM logs). **Plan 37 found an arithmetic error in it** (31 vs 34; erratum `per_rule_phase1_f2_identity.md`) |
| R-G8-3 | 3-16 89-key window counterfactual (science) | no review | `triage/completeness_3-16_window_cf.md`, `completeness_3-16_outcomes.tsv`; scratch-3-16 gone |
| R-G8-4 | 3-17 9,064 ledger re-baseline (docs/science) | "done with concerns"; no review | `triage/rebaseline_3-17_9064.md`; scratch-3-17 gone; plan 37 per-row F2 identity now committed |

Plan 27 pattern: a fresh `REVIEW.md` per unit, written by a seat that authored none of the units. Clause-by-clause verdict against the unit's own brief and outcome. Artifact-only plus light recompute. Unverifiable claims are named with root cause, never passed.

## What Landed

Master direct. Review only: no unit was re-run, and no unit record or outcome
was rewritten. No build, K1, encoder or disc read was run by the reviewers.

- **Seat:** Claude CLI clean-context reviewer (disclosed). Codex is
  weekly-limited until 2026-10-10 11:50 AEST.
- **Independence:** the seat authored no plan 04 3-1x unit and no plan 36
  unit.
- **Design rulings applied (advance, binding):**
  - A review that names its unverifiable clauses with a root cause (deleted
    scratch) discharges "review missing".
  - Each UNVERIFIABLE or FAIL clause becomes its own named residual. It is
    not counted proven.
  - The retained adversarial report is imported with its sha. Nothing is
    re-run.

## Phase 1 — 3-14 landed-tip review

- **Adversarial report imported:** `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/adversarial-67e48d9.md`,
  sha256 `fbbaae5ae9d6be74a3b93e81b868464c5b4dfb3d3a32c9f1faae2d9c930e9ff6`.
  The source is host
  `/home/codyh/workspace/open-pajero-maps-3-14/output/CHM-3-14-adversarial.md`;
  the reviewer re-hashed both copies and they are identical.
- **Review:** `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-14/REVIEW.md` (sha256 `988d15d2…04e4`), against code
  `d35b565`, merged at `414c5fe`, named tip `a10585a` (parser tree equal to
  `0e1fd74` and master).
- **Verdict: ACCEPT-WITH-CONDITIONS.**
  - **Pass:** clauses a1–a7 (the EO contract), c1 (golden recapture equals
    the changed-cell list) and e1–e3 (the re-oracle, with bytes accounted and
    attributed by plan 36). All 12 adversarial findings were re-judged.
  - **FAIL:** b6. The build wall was unrecorded. Plan 36 logs show 26.28 s →
    90.23 s at `-j4`, and the EO-only build takes 90.90 s.
  - **UNVERIFIABLE:** b2, b3, b4, b5 (window) and b7 (AU). The root cause is
    that `output/scratch-3-14/` was deleted.
  - Light suite: 52 passed.
- **Residuals:**
  - R-G8-1 is discharged as review of record.
  - Its conditions are opened as R-G8-1-a..h.
  - R-G8-1-a (the wall FAIL) is owned by plan 41 Phase 1, the same mechanism
    as R-G9-4.

## Phase 2 — 3-15, 3-16, 3-17 reviews

All three verdicts are **ACCEPT-WITH-CONDITIONS**. For each unit, "review
missing" is discharged and its named residuals are opened.

| unit | review (sha256) | holds | named residuals |
|---|---|---|---|
| 3-15 | `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-15/REVIEW.md` (`defd06ff…aaa2`) | 776 = 363 + 132 + 7 + 274 reproduced from a fresh classify. The 31 vs 34 defect is confirmed and corrected by plan 37 (counts stand) | R-G8-2-a..f. The "build regression" label on the 89 is overclaimed: R-G8-2-e needs a Design ruling on the 89's root cause. Representability, the set-diff and the 739 legacy recomputation are unverifiable (lost `scratch-3-15/`) |
| 3-16 | `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-16/REVIEW.md` (`defff73e…2248`) | outcome table complete: 89/89, 0/89/0, equal hash pairs, zero target records | R-G8-3-a..d: key provenance, byte gates, the 156-face intervention and audit, underlying witnesses (lost `scratch-3-16/`) |
| 3-17 | `docs/plans/04-c-core-orchestration/triage/independent_reviews/3-17/REVIEW.md` (`4cc1157b…c9f1`) | the 188 still failing and unattributed (plan 28 corroborates). 468/308 reproduced by plan 37. R01 append exact | R-G8-4-a..e. R-G8-4-e (the disc sha) is discharged by citation (`4ed9cd80` is pinned in `docs/provenance.md` and plan 36's oracle chain) |

- **`residuals.tsv`:**
  - R-G8-1..4 are `discharged (review of record; conditions as named
    children)`.
  - There are 23 child rows: 22 open, 1 discharged by citation.
  - Each open child carries `blocks-phase3 (inherited; Design may
    reclassify)`. The blocking class of a lost-evidence condition is Design's
    call; it is not decided here.
- **OVERVIEW:** the "3-14 to 3-17 independent fix reviews" blocker clause now
  reads "reviews of record landed (plan 40); their named conditions
  R-G8-1..4-x remain".

## Commits
- `76da9e4`: Phase 1 + Phase 2 (reviews, adversarial import, residuals, OVERVIEW).
- This close-out: the record; reviews moved to `docs/plans/04-c-core-orchestration/triage/independent_reviews/`; plan folder removed.

## Not done
- No re-run of any unit, and no fix of any named condition (review is not
  reseat).
- The blocking class of each child condition is inherited
  (`blocks-phase3`) pending a Design reclassification.
- Codex confirmation of these reviews was not sought; Codex is limited until
  2026-10-10 11:50 AEST.
