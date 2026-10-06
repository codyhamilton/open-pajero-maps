# Implementation — 40 independent review of 3-14 to 3-17

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

- **Adversarial report imported:** `reviews/3-14/adversarial-67e48d9.md`,
  sha256 `fbbaae5ae9d6be74a3b93e81b868464c5b4dfb3d3a32c9f1faae2d9c930e9ff6`.
  The source is host
  `/home/codyh/workspace/open-pajero-maps-3-14/output/CHM-3-14-adversarial.md`;
  the reviewer re-hashed both copies and they are identical.
- **Review:** `reviews/3-14/REVIEW.md` (sha256 `988d15d2…04e4`), against code
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
| 3-15 | `reviews/3-15/REVIEW.md` (`defd06ff…aaa2`) | 776 = 363 + 132 + 7 + 274 reproduced from a fresh classify. The 31 vs 34 defect is confirmed and corrected by plan 37 (counts stand) | R-G8-2-a..f. The "build regression" label on the 89 is overclaimed: R-G8-2-e needs a Design ruling on the 89's root cause. Representability, the set-diff and the 739 legacy recomputation are unverifiable (lost `scratch-3-15/`) |
| 3-16 | `reviews/3-16/REVIEW.md` (`defff73e…2248`) | outcome table complete: 89/89, 0/89/0, equal hash pairs, zero target records | R-G8-3-a..d: key provenance, byte gates, the 156-face intervention and audit, underlying witnesses (lost `scratch-3-16/`) |
| 3-17 | `reviews/3-17/REVIEW.md` (`4cc1157b…c9f1`) | the 188 still failing and unattributed (plan 28 corroborates). 468/308 reproduced by plan 37. R01 append exact | R-G8-4-a..e. R-G8-4-e (the disc sha) is discharged by citation (`4ed9cd80` is pinned in `docs/provenance.md` and plan 36's oracle chain) |

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
