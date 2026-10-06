---
design_id:
---

# Independent review of 3-14 (landed tip) and science units 3-15, 3-16, 3-17

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual rows R-G8-1..4 (3-14 not accepted; independent reviews of 3-15, 3-16 and 3-17 missing). Model on plan 27's independent review. Review is not reseat: the units are not re-run and their records and outcomes are not rewritten. Oracle `4e6b0de7…` or later. Heavy work, if any, only under flock plus the wrapper. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief. Do not reseat 170, 3-16 or 3-17.

## Problem

Plan 04's dependency gate (3-90 brief: "if any fix unit is unreviewed, report blocked") and plan 35 G8 leave four units without an independent review of record.

**Ground (master `b10e787`; host read-only 2026-10-06 AEST):**

| Row | Unit | State | Retained evidence |
| --- | --- | --- | --- |
| R-G8-1 | 3-14 EO-aware bg stitch (`d35b565`, merged `414c5fe`, tip `a10585a`) | DeepSeek adversarial review BOUNCED stale tip `67e48d9`; Design overruled against `a10585a`; no independent review of the landed tip | `IMPLEMENTATION.md` L218–235; `test_bg_eo_stitch.py`; goldens recapture. **The adversarial report exists at host `open-pajero-maps-3-14/output/CHM-3-14-adversarial.md`** (residual says "not retained": it was not copied into the repo). Plan 36 P1–P2 container accounting; P3 per-cell causes (running) |
| R-G8-2 | 3-15 cell-local representability (science) | no review | `triage/completeness_3-15_cell_local.md`; scratch-3-15 data gone (worktree has only CHM logs). **Plan 37 found an arithmetic error in it** (31 vs 34; erratum `per_rule_phase1_f2_identity.md`) |
| R-G8-3 | 3-16 89-key window counterfactual (science) | no review | `triage/completeness_3-16_window_cf.md`, `completeness_3-16_outcomes.tsv`; scratch-3-16 gone |
| R-G8-4 | 3-17 9,064 ledger re-baseline (docs/science) | "done with concerns"; no review | `triage/rebaseline_3-17_9064.md`; scratch-3-17 gone; plan 37 per-row F2 identity now committed |

Plan 27 pattern: a fresh `REVIEW.md` per unit, written by a seat that authored none of the units. Clause-by-clause verdict against the unit's own brief and outcome. Artifact-only plus light recompute. Unverifiable claims are named with root cause, never passed.

## Solution shape

### Domain: 3-14 landed-tip review

- **Owns:** `docs/plans/40-independent-review-3-14-to-3-17/reviews/3-14/REVIEW.md`, and the retained adversarial report imported as `reviews/3-14/adversarial-67e48d9.md` with sha256 and host provenance.
- **Contract:**
  1. The reviewer has authored no 3-1x unit and no plan 36 unit.
  2. Clauses come from `briefs/3-14-bg-shape-eo-stitch.md` and the 3-14 record. Each clause gets PASS / FAIL / UNVERIFIABLE with evidence. The clauses cover:
     - the code diff `33006aa..d35b565` versus the stated EO stitch contract;
     - tests (`test_bg_eo_stitch` + bg/cenc suite, light, outside the lock);
     - golden recapture justification;
     - every BOUNCE finding of the adversarial report, each re-judged against tip `a10585a`, with Design's overrule cited and independently assessed;
     - the re-oracle scope, against plan 36's container accounting and P3 `cells_causes.tsv` once available;
     - the TRIM ruling (fact check only; parity is design 42).
  3. Verdict ACCEPT / ACCEPT-WITH-CONDITIONS / BOUNCE. A BOUNCE is recorded as a named residual with the failing clause. Nothing is fixed here.
- **Non-goals:** re-running the 3-14 encode (plan 36 has the endpoint replays); fixing findings.

### Domain: science-unit reviews 3-15 / 3-16 / 3-17

- **Owns:** `reviews/3-15/REVIEW.md`, `reviews/3-16/REVIEW.md`, `reviews/3-17/REVIEW.md`.
- **Contract:**
  1. Clauses come from each unit's brief (`briefs/3-1{5,6,7}-*.md`) and record.
  2. **Recompute:** each numeric claim derivable from committed artefacts is recomputed (light, outside the lock). For example: 3-15's 776 = 363 + 132 + 7 + 274 and 687/89/52 key partition against plan 28 tables; 3-16's 89-row outcomes TSV totals; 3-17's 776 = 468 + 308 and the 188 identity table against plan 28's assignment.
  3. Claims resting only on lost scratch are UNVERIFIABLE, with the missing artefact named. They are not passed.
  4. Plan 37's erratum is folded into the 3-15 verdict as a confirmed defect in the unit's explanation (the counts themselves stand).
  5. Each REVIEW ends with a verdict and, for any non-ACCEPT, the exact condition that remains.
- **Non-goals:** re-running any unit; rebuilding lost scratch; changing rules or counts.

## Decisions

1. Plan number 40. Master direct. Two phases (3-14 code review; science reviews), independent of each other.
2. Plan 27 is the template. Reviews are offline and artifact-only, except the light pytest and table recomputes.
3. The 3-14 review's re-oracle clause depends on plan 36 P3. If P3 is still running, that clause is UNVERIFIABLE-pending and the review lands with the condition.
4. A Cody waiver is not designed here. A residual a review cannot pass is reported as such.

## Assumption ledger

### Assumption 1

- **Question:** Does an UNVERIFIABLE clause discharge the "review missing" residual?
- **Answer chosen:** The review discharges "missing". Its UNVERIFIABLE or FAIL clauses become new named residuals with the root cause (lost scratch), as plan 27 did for `pinned_candidates`.
- **Rationale:** The gate needs an independent review of record. Absence of evidence is reported, not hidden.
- **If wrong:** Cody requires PASS on every clause. Units with lost-evidence clauses then stay `blocks-phase3` until regenerated by a follow-on.

### Assumption 2

- **Question:** May the reviewer copy the host adversarial report into the repo?
- **Answer chosen:** Yes: a read-only copy with sha256 and host path provenance. It is repo-internal evidence, not an external post.
- **Rationale:** It closes the "not retained" half of R-G8-1.
- **If wrong:** it is cited by host path and sha only.

## Open questions

None blocking.

## Phases

### Phase 1: 3-14 landed-tip independent review

- **Outcome:**
  1. `reviews/3-14/REVIEW.md` with every clause judged.
  2. Adversarial report imported with sha.
  3. Verdict. R-G8-1 updated to discharged or to the named conditions.
- **Surfaces:** `docs/plans/40-independent-review-3-14-to-3-17/reviews/3-14/`; `triage/phase3_synthesis/residuals.tsv`; read-only code and tests.
- **Approach:** known. **Depends on:** plan 36 P3 for one clause (else pending). **Refine:** skipped.

### Phase 2: 3-15, 3-16, 3-17 independent reviews

- **Outcome:**
  1. Three REVIEW.md files with recomputed figures.
  2. Verdicts.
  3. R-G8-2..4 updated, with any UNVERIFIABLE clause turned into a named residual.
- **Surfaces:** `reviews/3-1{5,6,7}/`; `residuals.tsv`; OVERVIEW clause.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

## Provenance

- Master `b10e787`. Sources:
  - plan 35 `residuals.tsv` R-G8-1..4;
  - plan 04 IMPLEMENTATION L218–300, L713;
  - briefs 3-14..3-17;
  - plan 27 record (template);
  - plan 37 erratum;
  - host read-only listing (`open-pajero-maps-3-14/output/CHM-3-14-adversarial.md` present; 3-15/16/17 scratch absent).
- Rejected:
  - reseating units;
  - passing lost-scratch claims;
  - designing a waiver.
- Box draft only.
