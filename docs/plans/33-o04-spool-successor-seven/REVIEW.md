# Review — plan 33 seven O04 spool successor rows

Verdict: **PASS_WITH_FOLLOWUPS**

Reviewed SHA: `c2cc6dc` (detached master; local review, no PR). Plan-33
commits: `9fb00da`, `67672f3`, `4c98943`, `c8cdb5e`, `373a38a`, `5f101f5`,
`05c5f64`. Surfaces:

- the plan folder;
- `parser/tests/test_o04_presence_witness.py`;
- `parser/tests/test_o04_disposition.py`;
- the plan-33 hunk of `docs/OVERVIEW.md`;
- the line appended to the plan-28 record.

**Reviewer independence is reduced.** The Codex review seat
(`output/scratch-33/codex-33-review.log`) died at the Codex usage limit
(~08:23 AEST) before producing findings. Codex stays unavailable until
11:19 AEST (re-probed at ~08:52). Execute (Grok Bot) wrote this review
itself. Execute did not write the unit code: Codex built units 1-01 and
2-01. Execute did run the guarded probes and publish, and committed the
work. Every claim below was re-derived from committed or retained bytes,
not taken from the reports.

## Phase outcome assessment

### Phase 1 — met

| Outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. 7-row witness TSV with native key, dump_row, demander, O04 refs, R presence, G counts on both discs, stratum | Met | `presence_witness.tsv` has 7 rows with every listed column. The strata are emit-piece 138/284/496 and demand-removed 236/282/317/563. |
| 2. All seven reaffirm R absent and O04/spool | Met | `source_rows()` re-checks the O04 predicate, the penultimate stratum and R-zero against hashed plan-28 TSVs. A light replay of `presence_witness.py publish` from the retained probe JSONs reproduced the committed TSV and JSON **byte for byte**. 0 exceptions. |
| 3. No spool edit, no verdicts, no Phase 3 close | Met | `dispositions_assigned: false`; no spool path is written. |

**Independent decode.**

- Every G frame was decoded by two paths, and their counts must agree:
  - `kiwiw.parcel.decode_parcel` (class-2 shapes with at least 3 coordinates);
  - plan 14's `decode_slot_shapes`.
- The replay above re-decodes all 21 frames from the committed hex and
  requires equality.
- For the emit-piece rows, the demanded code 288 is absent in every frame:
  - Row 138: G successor and historical have `{321: 8}` in leaf 1919; R has `{289: 2, 321: 1}`.
  - Row 284: G frames have no background polygons; R has `{289: 8}`.
  - Row 496: no background polygons in any of the three frames.
- The decoders return non-empty maps for other codes, so a decoder that
  returns nothing does not explain the zeros.
- Code 288 is a live R code (2.2 M L0 shapes, `docs/schema/map-background.md`),
  so its absence in R carries meaning.

**R extent.** Every R frame is an `l0_sparse_tile`. Its bounds strictly
contain the G cell; for example, row 138's R tile spans
142.875–143.0 / −35.5 to −35.417, which contains the G cell
142.969–143.0 / −35.4375 to −35.417. A demanded-type count of 0 over the
larger extent implies 0 inside the cell, so the containment makes the
witness stronger, not weaker.

**lookup_failed.** `validate_row` accepts only `resolved` or `empty_slot`.
Any decoder exception sets `lookup_failed` with `type_count = None`, which
publish records as an exception. A lookup failure cannot count as absence.

### Phase 2 — met

| Outcome | Assessment | Evidence |
| --- | --- | --- |
| 1. Disposition TSV with verdicts, rationale, fix paths, K1 completeness failing 0 | Met | `disposition.tsv` and `.json`. K1 completeness 1,800,514 checked / 0 failing is cited from `successor_k1_compare.json` (sha256 `d4d5038d…`). The same number appears in plan 31's pin contract. |
| 2. Emit-piece: no default verdict | Met | Each of 138/284/496 is `proven-non-deviation` on its own per-row witness. The penultimate counterfactual is recorded as evidence only ("would invent R-absent presence"). |
| 3. Demand-removed | Met | All four are `proven-non-deviation` under the same rule. |
| 4. conflict-open 0 or named | Met | `verdict_counts`: 7 proven-non-deviation, 0 fix-landed, 0 conflict-open. |
| 5. OVERVIEW and plan-28 narrowed; Phase 3 open | Met | The OVERVIEW sentence matches the evidence. The plan-28 line is append-only. `plan04_phase3_closed: false`. |

A light replay of `disposition.py publish` reproduced the committed TSV and
JSON byte for byte. Tests:
`pytest test_o04_presence_witness.py test_o04_disposition.py
--basetemp output/scratch-33/review/tests` gave **81 passed**.

## Findings by severity

No blocker, high or medium findings.

### Low

**L1 — follow-up (corroborated):** the R probe uses
`pin_verification: historical-citation`. The R disc was not stream-hashed
during the plan-33 probe (08:01 AEST); its pin comes from plan 29's R
witness. Corroboration from this review:

- The R file at the same mount has an mtime of 2007-12-21.
- Plan 34's guarded `phase2_gates.py snapshot` stream-hashed the same path
  at 08:36 AEST the same day to `8c2d2027…`
  (`output/scratch-34/protected_before.json`).

Non-blocking. A future probe tool should stream-hash R as it does for G.

**L2 — follow-up (accepted):** Execute ran the Phase 2 `publish` without the
heavy lock while another project held it. Execute used `prlimit
--as=3000000000`, and the step reads only committed JSON (48 MiB RSS). The
plan-25 guard targets disc, spool and encode work, so this step complies in
substance and is disclosed in IMPLEMENTATION. Recommendation: the guard's
written scope should say explicitly that light JSON-only publishers are
exempt.

**L3 — follow-up:** this review is not independent; see the top of this
file. A clean Codex confirmation pass may be run when the limit resets. It
does not block close-out, because every outcome was replayed from bytes.

## Intent and ledger assessment

- The intent is met. Each row is closed as fix or proven non-deviation
  under the DVD bar, with no relabel, no spool edit, no invented presence
  and no Phase 3 claim.
- Assumption 1 (O04 sufficient) holds: the predicates are re-checked and
  hashed.
- Assumption 2 (no presence-inventing spool edit) holds: no edit was made.
- Assumption 3 (Phase 3 not cleared) holds.
- The amended Decision 3 (no default verdict) is honoured by per-row
  witnesses.

## Plan-sufficiency judgment

The design was sufficient. It fixed the verdict set, the witness bar and
the strata, and it specified that an R lookup failure must never count as
absence. It did not say how R identity is attested during a probe (L1).

## Residual risks

- The O04 spool defect remains as a named spool-hygiene residual on all
  seven rows. The source is unchanged.
- The K1 figure is a retained citation, not a rerun. It applies to
  `2ee3456a…` only.
- If plan 34 lands a new successor disc, these cells' G frames must be
  re-attested only if plan 34's classified diff touches them. That diff is
  confined to outside-mask empty shells, and all seven cells are inside the
  L0 mask.

## Files changed by this review

- `REVIEW.md` only. Replay outputs and the pytest basetemp are under
  `output/scratch-33/review/`.
