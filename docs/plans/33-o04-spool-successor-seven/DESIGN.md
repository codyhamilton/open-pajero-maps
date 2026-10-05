---
design_id:
---

# Seven O04 spool successor rows

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close the plan-28 follow-up for the seven O04 / spool completeness rows (dump_row 138, 236, 282, 284, 317, 496, 563): each needs a proven root cause (already O04) and either a **fix** or a **proven non-deviation**. Never relabel. R presence is false for all seven — any spool repair that makes G emit the type in-cell would create a new G≠R presence deviation and is forbidden without an explicit, evidenced ruling. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Skip plan 29 close-out (Execute).

## Problem

Plan 28 reconciled all 776 baseline completeness assignments. Seven rows are **conflict-proven**: rule cause **O04 / spool**, plan-14 group amended 2-02, 3-03 checker disposition. They were carried to plan 04's successor spool list with penultimate-repair discriminators. No design has yet closed each row as fix or proven non-deviation under the standing DVD bar.

| dump_row | Cell/type | Penultimate repair | R presence |
| ---: | --- | --- | --- |
| 138 | (0,1695,699,288) | emits 1 representable piece | false |
| 236 | (0,913,876,578) | demand removed, 0 piece | false |
| 282 | (0,1915,1030,288) | demand removed, 0 piece | false |
| 284 | (0,1411,1044,288) | emits 1 representable piece | false |
| 317 | (0,1945,1110,578) | demand removed, 0 piece | false |
| 496 | (0,1248,1253,288) | emits 1 representable piece | false |
| 563 | (0,1505,1315,288) | demand removed, 0 piece | false |

Plan 28 already stated: this evidence does not authorise a spool edit or an R-parity claim. Live completeness on successor `2ee3456a…` is failing 0 (checker representability). The open question is DVD / spool honesty for these seven source defects: leave as proven non-deviation (G and R both lack the type), or apply a spool fix that cannot invent R-absent presence.

**Ground (tip `5ff9eb0`):** discriminators in `per_rule_phase2_discriminators.tsv` / `per_rule_phase2_reconciliation.md`; mechanism probes in `per_rule_completeness_mechanism.tsv`; R-zero in `r_contribution_3-02.tsv`; 2-02 member proofs. No K1/encode run for this design.

## Solution shape

Treat the seven as a bounded spool-successor unit. Root cause stays **O04 spool** (crossing-closing ring; penultimate deletion discriminator). Closing move is per-row (or per stratum) **`proven-non-deviation`** or **`fix`**, never a relabel to checker.

### Domain: DVD presence parity witness

- **Owns:** committed proof that for each of the seven keys, R and G (disc in force `2ee3456a…`, historical `4ed9cd80…` as control) agree on cell-local absence of the demanded type, or name any disagreement.
- **Contract:**
  1. Per row: full native key, R polygon count / cell-local verdict (reuse plan-14 proofs when hashes match), G type count on successor and historical.
  2. Expected: R absent, G absent for all seven. Any exception is listed and blocks non-deviation for that row.
  3. Reads via `run_heavy_python.py` + lock when discs are touched; prefer light reuse of `scratch-14` witnesses.
- **Non-goals:** no spool edit in this domain; no completeness reseat.

### Domain: fix or proven non-deviation

- **Owns:** a closing disposition for each of the seven rows.
- **Contract:**
  1. Verdict ∈ {`proven-non-deviation`, `fix-landed`, `conflict-open`}. Target 0 conflict-open.
  2. **`proven-non-deviation`:** G and R both lack the demanded type cell-locally; the historical completeness demand was checker-over-demand on unrepresentable geometry (plan 14/28); the O04 spool defect is named and retained as **spool hygiene residual** (does not create a live G≠R presence deviation). Allowed for either stratum only with the per-row byte/decode witness that G and R are both absent in that cell (Decision 3).
  3. **`fix-landed`:** a bounded spool repair (penultimate deletion or equivalent tracked extractor fix) is applied such that:
     - production C on the repaired source emits **0** records of the demanded type in the target cell (no inventing R-absent presence); and
     - a successor-oracle encode (new path, protected discs untouched) either is unnecessary (spool-only hygiene with byte-identical AU disc) or, if a new disc is built, its diff is confined to named cells and R presence parity still holds; and
     - live K1 completeness remains failing 0; other kinds unchanged or residuals named.
     Stratum **emit-piece** (138, 284, 496) cannot take this verdict via penultimate deletion alone — that path emits a piece where R has none, and the penultimate repair must never invent presence that R lacks. **There is no default verdict** (Design ruling, 2026-10-06): each of these rows reaches `proven-non-deviation` only with its own per-row byte or decode witness that G and R are both absent in that cell, or `fix-landed` only with a fix proven not to invent presence; otherwise it stays `conflict-open`.
  4. Stratum **demand-removed** (236, 282, 317, 563): optional hygiene fix under §3 if it yields byte-identical disc or presence-safe diff; otherwise `proven-non-deviation`.
  5. Never relabel O04 → checker. Never absorb into 2-01. Never claim Phase 3 closed.
  6. OVERVIEW / plan-28 follow-up wording narrowed: seven rows closed with counts per verdict; any spool-hygiene residual named.
- **Non-goals:** no full tip re-extract; no 3-90; no P4–6; no inventing WhereIS geometry.

## Decisions

1. Plan number **33**. Land on master directly. No feature branch. No PR.
2. Two phases. Approaches known. Refine skipped. One worker may carry both.
3. **No default verdict** (Design ruling, 2026-10-06, amending the draft's "default proven-non-deviation"). A row is `proven-non-deviation` only when a committed per-row byte or decode witness shows that G (successor `2ee3456a…`, historical `4ed9cd80…` as control) and R are both absent for the demanded type in that cell. Without that witness the row stays `conflict-open`. Penultimate emit-piece counterfactuals stay evidence, not a mandate to edit the spool, and a repair must not invent presence that R lacks.
4. Disc in force: `2ee3456a…`. Heavy only under wrapper + lock.
5. Hard constraints: no reseat 170/3-16/3-17; no P4–6/plan 06; no Phase 3 close claim; no 3-90; skip plan 29 close-out.

## Assumption ledger

### Assumption 1

- **Question:** Is O04 root cause already sufficient, needing only fix vs non-deviation?
- **Answer chosen:** Yes. Plan 28 discriminators stand; this plan does not re-litigate O04 predicates.
- **Rationale:** conflict-proven record; standing rule wants closure, not re-attribution.
- **If wrong:** A row fails re-probe — Phase 1 lists it conflict-open.

### Assumption 2

- **Question:** May we edit the spool to emit pieces where R has none?
- **Answer chosen:** No. That invents a G≠R presence deviation.
- **Rationale:** Standing DVD bar; plan 28 non-authorisation of R-parity claim.
- **If wrong:** Cody explicitly accepts presence invent for these cells — separate ruling; not this design's default.

### Assumption 3

- **Question:** Does closing these seven clear plan 04 Phase 3?
- **Answer chosen:** No.
- **Rationale:** PSS / joins / oracle gates remain other designs.
- **If wrong:** Later close synthesis cites this record.

## Open questions

1. Whether demand-removed stratum gets an optional presence-safe spool hygiene patch in Phase 2 or remains non-deviation-only — Execute chooses under Contract §4; must not invent presence.
2. Exact OVERVIEW sentence after closure counts exist.

## Phases

### Phase 1: Presence parity and O04 identity confirmed for all seven

- **Outcome:**
  1. Committed 7-row witness TSV: native key, dump_row, demander id, O04 proof refs, R presence, G type counts on successor + historical, penultimate stratum (`emit-piece` | `demand-removed`).
  2. All seven reaffirm R absent and O04/spool; exceptions named.
  3. Not done: no spool edit; no disposition verdicts yet; no Phase 3 close.
- **Surfaces:** `docs/plans/33-o04-spool-successor-seven/`; read-only plan-28 TSVs, scratch-14 proofs, discs.
- **Approach:** known. **Refine:** skipped.

### Phase 2: Each row closed as proven-non-deviation or fix-landed

- **Outcome:**
  1. Committed disposition TSV: verdict per row, rationale, any fix artefact paths / disc sha, K1 completeness failing 0 retained.
  2. Emit-piece stratum (138, 284, 496): no default. Each row is `proven-non-deviation` with its per-row G/R absence byte/decode witness, `fix-landed` with a non-emitting, presence-safe fix, or `conflict-open`.
  3. Demand-removed stratum: `proven-non-deviation` and/or presence-safe `fix-landed` per Contract.
  4. `conflict-open` = 0 or named.
  5. OVERVIEW / plan-28 follow-up narrowed; Phase 3 not closed.
- **Surfaces:** plan-33 folder; optional bounded spool patch + tests; optional successor encode under wrapper; `docs/OVERVIEW.md`.
- **Approach:** known. **Refine:** skipped.

## Provenance

- Tip `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7`. Plan 28 reconciliation + discriminators; plan 14/28 records; successor oracle plan 29.
- Rejected: inventing R-absent presence; relabel O04→checker; Phase 3 close; 3-90; P4–6; reseating 170/3-16/3-17.
- Box draft only. Adversarial in-context: emit-piece repair ≠ authorised fix; non-deviation is the honest default for presence.
