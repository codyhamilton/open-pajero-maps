Verdict: PASS_WITH_FOLLOWUPS

Reviewer: Claude CLI clean-context seat, re-review (disclosed; Codex weekly-limited until 2026-10-10). Scope: rework commit `25786bf` against the first review (`output/scratch-39/review/REVIEW.md`). I authored none of the work.

Commands run were light reads and one bounded probe, `output/scratch-39/review2/partial_probe.py`, with output in `partial_probe.json`. The probe sampled 600 R01 rows (300 per shape tier) and decoded the old and new leaves of 600 cells; it ran in about 12 s. No builds, K1, pytest or lock were used, and no tracked file was modified.

Why not FAIL: the F1 blocker is fixed in substance. The test is now at shape level, R-G5-4 stays open, and nothing is wrongly discharged. Exclusivity is disproven robustly on the strict tier alone.

Why not PASS: the headline count (920,686 rows "satisfy the build-fixed predicate") includes a weak tier with no identity guard. That count is repeated on five surfaces and is what the pending Cody ruling would read (N1).

## Prior findings

| # | Finding | Status | Note |
|---|---|---|---|
| F1 | Vertex-level (b) cannot separate fixed from removed | **Fixed (with N1 caveat)** | `p2/shape_clause_b.py` keys the item on the old record (leaf, type, record) and decides persistence from that record's exact non-failing vertices in a same-type, class>0 new record. This is a sound reading of "same cell, type and shape". The `old_mapping_mismatch` count is 0, and I re-derived `share.f32` to 1e-4 on 600/600 sampled rows. The weak tier is over-counted, see N1 |
| F2 | Overclaim on live surfaces | **Mostly fixed** | `rules_bg.json` R01 note, OVERVIEW, residuals R-G5-4 (open, `blocks-phase3`, Design) and R-G5-1/2 ("at most 1,254 / 72,937 … fail or untested") now state measured results; R-G5-4-a is folded back into R-G5-4; "removed-by-3-14", "exclusivity holds" and "none is build-fixed" are gone. Nothing is discharged that should not be. The remaining gap is N1 ("satisfy the predicate" is stated untiered) |
| F3 | cause_table self-contradiction | Fixed | L52 and L82 are marked historical and point to the plan 39 classification |
| F4 | scratch-39 BOM missing | Fixed (minor inaccuracies N3) | `docs/provenance.md` § `output/scratch-39/`. The named producers `run_k1.sh`, `run_rows.sh`, `run_p3.sh`, `make_cf_spool.py`, `allrows_311_cells.py` and `shape_clause_b.py` all exist; both worktrees exist |
| F5 | Design P3 contract 4 | Fixed | IMPLEMENTATION states that the 3C narrative's sampled covers (1728,162)/(1771,203) have other producers, and that the exhaustive join covers every row on `87a01b14` |
| F6 | 600-cell sample and window justification | Fixed | The sample sentence is withdrawn; source-bbox ⊂ window is stated; the twin-record caveat is stated |
| F7 | R-G4-1 band-level and per-kind split | Fixed (disclosure) | Both limits are in IMPLEMENTATION P1 item 2. The R-G4-1 residual row does not repeat them (acceptable; it cites the record) |
| F8 | Stale or contradictory text | Partly fixed | P2 `rules_bg.json` text is aligned; `r01_join.json` has `superseded_note`. OVERVIEW and residuals still link to `docs/plans/39-historical-bg-cause-counterfactual-ledger.md`, which does not exist yet (folder only). Close-out must create it |
| F9 | `assignment.tsv` at count level | Accepted, see N1 and N3 | R01 cause and reason changed as required |

## Attribution check

No decision is attributed to Cody or Design that the record does not show:
- "Dual-cause ruling pending (Cody via Design)" matches DESIGN open question 1, which says the question "is raised only if Phase 2 finds such rows".
- "A new producer scan is a Design ruling" is stated as pending, not as decided.
- `assignment.tsv` reports `build:eo_bg_stitch` with the checker note kept. That follows design rule 3 and open question 1 ("reported `build` with a checker note"), so it does not pre-empt the ruling.

One nit: "raised" has no artefact. Nothing in the record shows the question was put to Cody; it exists only as text in the residual. That is fine for a residual row, but the close-out should not say "Cody was asked" unless it happens.

## New findings

**N1 — MEDIUM. The weak tier ("traceable", ≥1 shared vertex) is counted as "satisfies (b)" with no identity guard. The headline 920,686 overstates what is proven.**
- *Evidence.* My probe: 300 random R01 rows from status 11 (partial) and 300 from status 10 (≥50%), each in a distinct cell, on `87a01b14` → `4ed9cd80`.
  - **Absolute shared vertices with the best new record:**
    - partial tier: min/p10/median/p90/max = 1 / 6 / 28 / 69 / 324; 9/300 rows have ≤2 shared vertices;
    - ≥50% tier: 5 / 22 / 39 / 111 / 1,174.
  - **Neighbour masquerade.** The best-matching new record is coordinate-identical to a *different, unchanged* old same-type record in the leaf in 15/300 partial rows and 14/300 ≥50% rows (about 5%). That is exactly the "adjacent polygon sharing vertices" false positive. If such unchanged neighbours are excluded:
    - partial tier: all 300 stay partial, so they still have some other matching record;
    - ≥50% tier: 291 stay ≥50%, 8 fall to partial and 1 falls to *no traceable record*.

    So the outright false-"persists" rate is low (1/600). Tier inflation is real.
  - **Identity-bearing vertices.** A shared vertex is identity-bearing only if it is held by no other old same-type record and is not on the leaf's outer bbox edge, where clipped same-type pieces of neighbours meet. 55/300 partial rows (18%, roughly 14–23%) and 26/300 ≥50% rows (9%) have **no** such vertex: every shared vertex is a leaf-edge or neighbour-shared coordinate. Extrapolated, that is about 112k + 27k ≈ 139k of 920,686 R01 rows (≈15%) whose (b) rests only on vertices a neighbour could supply.
  - **Shape changed.** Even taking the union over all same-type new records, the partial tier's union share median is 0.37: only 73/300 reach 50%. For most partial rows, most of the old record's non-failing vertices are gone. "Same shape" is then a stretch, even if the record is traceable.
- *Consequence.* "Exclusivity disproven by count" still stands: the strict tier alone gives ≥ ~280k rows. But the following statements present the weak tier as proven predicate satisfaction:
  - "920,686 rows satisfy the build-fixed predicate" in IMPLEMENTATION, `assignment.tsv`, the `rules_bg.json` note, OVERVIEW and residuals R-G5-4;
  - "all others satisfy it" in R-G5-1/2.

  The 50% and ≥1 thresholds are also the implementer's own, not the design's. That is not disclosed as a choice.
- *Fix.*
  1. Add an identity guard to `shape_clause_b.py`. Count only shared vertices that are (i) not present in any other old same-type record of the leaf and (ii) not on the leaf rectangle edge. Exclude new records that are coordinate-identical to an unchanged other old record.
  2. Re-run (443 s, under the lock).
  3. Report three tiers by count: identity-proven persists / weak (neighbour-explainable) / none.
  4. Restate the five surfaces as "exclusivity disproven by count: ≥N rows with identity-proven persistence; M rows weak (identity undetermined); 7 none; 80 untested". In `assignment.tsv`, give the weak tier its own row, `unattributed: (b) identity undetermined`, rather than `build:eo_bg_stitch`.
  5. Disclose the thresholds as implementer choices.

  This must land before R-G5-4 goes to Cody for the dual-cause ruling, and before close-out.

**N2 — LOW. The shape test excludes only the failing vertices of the kind being processed.** In `shape_clause_b.py`, `keep = ~np.isin(V[ms], cols["vert"][rows_s])` excludes only the failing vertices of the kind being processed. A record's background_boundary failing vertices are treated as "non-failing" in the background pass, and the reverse also applies. This direction is conservative: it can only lower shares, so it is not an overclaim. It does make `share` differ from its stated definition.
- *Fix.* Union both kinds' failing vertices per record, or document the deviation.

**N3 — LOW. BOM and per-row record durability.**
- *Evidence.*
  - (a) `provenance.md` says `dump_pre311/`, `dump_311/`, `dump_314/` are "about 2.5 GB each". In fact `dump_314` is 16 K (failing 0) and `dump_k1old_pre311` is 268 K.
  - (b) It says dumps are deleted at close "after the identity tables and status arrays are kept". But `shape/*.status.u8` (86 MB) and `allrows/` live in the same scratch tree, and no kept location is named. They are indexed by **dump row order**, which is only reproducible if a regenerated `--dump-failures -j6` emits rows in the same order. Nothing in the record shows that.
- *Fix.*
  - Correct the sizes.
  - Name where the status arrays survive, or commit a compact keyed form: `(level, ix, iy, leaf, shape, vert) → status`, gzip, for the non-trivial statuses only, or at least for R01 plus the remainder's candidate population.
  - Alternatively, state that K1 dump order is deterministic across `-j` and cite evidence. Without one of these, "the remainder can join it by row index once its identities exist" is fragile.

**N4 — INFO. "Dual cause" is the right escalation, but the question should be framed sharply for Cody.**
- The predicate cannot tell "3-14 fixed a defective vertex" from "3-14 stopped emitting a vertex that Amendment 4 says was valid (a checker false positive)".
- In the second case, "build" is not a defect cause. The build change merely *removed a checker false positive*.
- The residual text should state this distinction so that the ruling is not read as a choice between two equally supported defect causes.
- It is consistent with design rule 3 and open question 1 to report `build` with the checker note while the ruling is pending, and the rework does that.

## Required before close-out

- N1: tiered counts with an identity guard, and the surfaces restated.
- F8 residue: the record file must exist at the linked path.
- N3: BOM corrections and per-row durability.
- N2 and N4 are optional wording or code hygiene.
