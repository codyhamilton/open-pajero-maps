# 3-14 cause and container attribution, with the AU 3-11 routed proof

Plan 36 closed three phases. Each phase was reviewed by an independent
Claude CLI clean-context seat (disclosed; Codex is weekly-limited); all three
verdicts were PASS_WITH_FOLLOWUPS and every follow-up was fixed before the
phase closed.

- **3-11 replay:** byte-exact.
- **3-11 routed proof:** 0 routed-only, 0 missing.
- **Plan 07's +60 B ledger:** reproduced exactly.
- **3-14 container:** every byte accounted.
- **3-14 changed cells:** every cell classed by a byte predicate, 0
  unattributed.
- **The whole 3-14 hop** is caused by the EO hunks of `d35b565`.
- **The 3-14 K1 `checked` delta** is confined to changed cells.

Six plan 35 residual rows are discharged: R-G1-1..4, R-G4-2 and R-G10-1.
Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.
>
> Root-cause designs for the AU 3-11 +60 B gap (and its routed proof) and for 3-14 payload cause attribution. Combine them if they share a mechanism. Void any item already resolved on master, with evidence. Reference the oracle in force `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded or streamed loads (plan 25). Master direct. Do not draw plan 04 Phases 4–6 or plan 06. Do not claim Phase 3 closed. No 3-90 re-run. Do not reseat 170, 3-16 or 3-17.

## Why This Existed
Plan 35's close synthesis left these residual rows open in
`triage/phase3_synthesis/residuals.tsv`:

- **Oracle-chain rows:**
  - R-G1-1/2: the 3-14 per-cell payload causes, unattributed for 246,123
    AU and 795 Perth cells.
  - R-G1-3: the 3-14 container, index and padding changes, unmeasured.
  - R-G1-4: the 3-11 routed proof, with no pre-3-11 disc.
- **R-G4-2:** the 3-14 hop's `checked` moves, not confined.
- **R-G10-1:** stale "+60 B unattributed" wording.

The "+60 B gap" was already attributed by plan 07, so it was **voided** as a
root-cause item and kept only as a control.

## What Was Built
Commits:

| Commit | What |
| --- | --- |
| `233d09e` | DESIGN |
| `0cb872e` | P1 |
| `b10e787` | P1 close (`:1`), with the P2 container account |
| `7909964` | P2 close (`:2`) |
| `af0178b` | P3 |
| `ece6ba9` | P3 close (`:3`) |
| close-out commit | this record; the plan folder is removed |

All lasting files are in `docs/plans/04-c-core-orchestration/triage/oracle_chain/`:
`region_accounting.py`, `evidence/`, `hop_3_14/`, `oracle_chain.{py,tsv,json}`.
Heavy work ran under the wrapper and lock, one job at a time, with protected
snapshots equal before and after. Scratch is in `output/scratch-36/`
(`docs/provenance.md`).

### Phase 1 — region tool, 3-11 replay, routed proof
- **Region tool:** `region_accounting.py` partitions each disc into plan 07
  regions by index path. It fails closed on gaps, overlaps, nonzero padding
  or tails, and oversize padding (tool sha `183d0ee0…`).
- **Replay:** `b7c7c42` rebuilt `87a01b14…` byte-exact (1,731,021,568 B,
  26 s at `-j4`).
- **Routed diff** `87a01b14 → 013586b5`: 0 routed-only and 0 missing out of
  37 cells.
- **Region account:** +164 payload; padding 21,570,746 → 21,570,806; the same
  41 spans as plan 07, checked row by row against the ledger; 0
  unaccounted.
- **Publication:** the `oracle_chain` 3-11 row is now
  `replay-routed-verified`. The "+60 B unattributed" wording is replaced by
  citations to plan 07 (contract, plan 31 record, OVERVIEW).
- R-G1-4 and R-G10-1 are discharged.

### Phase 2 — 3-14 container accounted
- **AU `013586b5 → 4ed9cd80`:** −38,916,640 B =
  - payload −38,913,410;
  - padding −3,198;
  - PMR records −12;
  - PMR tails −20.

  The payload equals Σ per-cell deltas over the 246,123 cells.
  - PDMDH: 5,943 address bytes, plus 3 BMT size-field bytes of the three
    size-changed PMR blocks (`L0 23/16`, `51/9`, `51/10`).
  - Topology: 12 only-old / 15 only-new frames.
- **Perth `da13a775 → 04be2f6e`:** −160,992 = −161,380 + 388 + 16 − 16.
  Payload equals Σ over the 795 cells.
- **Files:** `hop_3_14/{container_summary.py, pdmdh_fields.py, container-{au,perth}.json, pdmdh-fields-3-14.json, region-3-14-perth.spans.tsv}`.
- R-G1-3 is discharged.

### Phase 3 — 3-14 per-cell causes
- **Endpoints:** rebuilds at `33006aa` and `d35b565` reproduce all four pins.
  Only `parser/kiwiw/_cenc.c` reaches the build.
- **Mechanism counterfactual (beyond the design):**
  - `33006aa` + `d35b565`'s EO hunks 1–4 (`hop_3_14/eo_only.patch`) builds
    **exactly `4ed9cd80` / `04be2f6e`**.
  - The chord hunk 5 (`chord_only.patch`) contributes 0 bytes when EO is
    present.
  - Alone, the chord hunk changes 77,071 AU cells (leaves 3.95 M → 5.00 M).
  - Facts: `hop_3_14/mech.json`.
- **Per-cell classes** (`sections.py`, `detail.py`, `cells_causes.py` →
  `cells_causes-{au,perth}.tsv.gz`, `summary-{au,perth}.json`):

  | class | AU | Perth |
  |---|---:|---:|
  | `eo_bg_stitch` (only background sub-frame bytes differ) | 246,041 | 792 |
  | `eo_bg_stitch_ext_relocation` (plus ext entries moved by exactly the background delta) | 75 | 0 |
  | `eo_frame_ceiling_name` (name trades against background at the 131,070 ceiling) | 3 | 0 |
  | `eo_division_ceiling` (one quadtree re-division near the ceiling) | 4 | 3 |
  | `unattributed` | **0** | **0** |

  The 7 AU / 3 Perth non-payload-only cells are the 4 + 3 division cells and
  the 3 name-ceiling cells.
- **K1 `checked` confinement** (`k1_rows.py` drives the unmodified K1 checker
  with one-row bands):
  - band totals equal the recorded whole-disc reports;
  - AU whole Δ (range −24,243,765 … background_boundary −25,457,252) lies
    entirely in the 29,824 bands that hold a changed cell (29,790 bands with
    a delta);
  - Perth likewise, 107/107;
  - cell level follows from the checker's per-leaf / per-cell counting.
  - Files: `hop_3_14/k1-confine-{au,perth}.json`.
- **Publication:** `oracle_chain.py publish --causes-3-14-*` makes both 3-14
  rows `measured-identities-causes-attributed`, with 0 unexplained and no
  residuals.
- R-G1-1, R-G1-2 and R-G4-2 are discharged.
- **Tests:** `parser/tests/test_oracle_chain.py`, `test_region_accounting.py`
  and `test_hop_3_14_causes.py`. Oracle / region / pin / successor / hop:
  98 passed.

## Deviations
- **P3 beyond design:** the mechanism-isolated builds (EO-only, chord-only)
  were added. They turn the hop-level attribution into a whole-disc
  counterfactual.
- **P3 outcome 4:** confinement is measured at row-band granularity, because
  K1 bands are cell rows and the checker was not modified. Cell level is a
  code-reading argument, which the reviewer judged sound.
- **`cells_causes` is committed gzip** (AU 715 KB), with gz and raw shas in
  the summary. The large region JSON/TSV (P2) and the K1 band TSVs (P3) stay
  in `output/scratch-36/`, sha-pinned.
- **P2 F4 partly done:** there is no whole-disc `pmr_tail_oversize` check in
  `region_accounting.py` (a writer-wide property, not a hop delta).

## Review
Per-phase reviews by the Claude CLI clean-context seat. Full text:
`docs/plans/04-c-core-orchestration/triage/oracle_chain/reviews/plan-36-REVIEW.md`.


- **P1:** on `0cb872e`, PASS_WITH_FOLLOWUPS.
  - The reviewer re-checked the 41 plan-07 rows.
  - F1–F5 were fixed in `b10e787`: padding fail-closed and r2 re-runs,
    account tests, a row-level ledger check, wording, union inline compare.
- **P2:** on `b10e787`, PASS_WITH_FOLLOWUPS.
  - The reviewer re-ran `container_summary.py` to byte-identical output.
  - F1–F5 were fixed in `7909964`; F4 was partly done.
- **P3:** on `af0178b`, PASS_WITH_FOLLOWUPS.
  - The reviewer recomposed the patches and recounted the classes and the
    K1 compare.
  - F1–F7 were fixed in `ece6ba9`: residuals/OVERVIEW, provenance, the
    division-predicate caveat, all predicates evaluated, worktree `_cenc.c`
    shas, and publish gz/level checks.
- Codex confirmation was not run (weekly limit until 2026-10-10 11:50
  AEST).

## Residual Risks
- **The `eo_division_ceiling` predicate bounds plausibility only.** Its
  background sums compare different topologies. For those 7 cells the causal
  link is the whole-disc EO-only counterfactual, not a per-cell encoder
  probe.
- **DVD (R) parity of the 3-14-changed cells is not asserted** (design
  non-goal; design 42 owns trim parity).
- **The recorded whole-disc K1 reports carry no disc sha.** Identity rests on
  provenance plus exact equality with the sha-checked band runs.

## Follow-ups
- Optional per-cell encoder probe of the coarse-frame size under `33006aa`
  vs EO for the 4 AU division cells.
- A whole-disc `pmr_tail_oversize` check in `region_accounting.py` (P2 F4).
- R-G4-1 (the 3C-04 → 3-11 hop's `checked` moves) remains unowned → Design.
- Throwaway worktrees `../open-pajero-maps-36-{pre311,pre314,at314,eo-only,chord-only}`
  are removed with `git worktree remove` at close-out. The scratch discs
  remain in `output/scratch-36/`.

## Decisions Worth Keeping
- **A hop's cause is proven by a mechanism-isolated rebuild that reproduces
  the new disc byte-exact.** The per-cell byte predicates then classify the
  effect, not the cause.
- **"Payload causes not measured" is removed only by a summary that covers
  every cell of the authoritative list.** That summary must have class sums,
  per-level sums and a gz sha that all check out.
- **K1 `checked` counts are partition-invariant** (K1Acc sums), so one-row
  bands are a valid confinement instrument without changing the checker.
