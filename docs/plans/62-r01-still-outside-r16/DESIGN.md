---
design_id:
---

# R01 residual after plans 44 and 45: re-decide under the plan-46 producer, census, discharge or named children (R-G5-4-a / R-G5-4-b / R-G5-4-c)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Plan **44** closed as owner of R-G5-4-a / R-G5-4-b with a Phase-2 Design ruling (option c): mass default **R=8**; standing **widen@16** on `producer_home_outside_R_cap`; recoveries at recovering radius are proven-fixed candidates; **still outside at 16** stay named `producer_home_outside_R_cap` max=16. Tip OVERVIEW / `residuals.tsv` still list those parents as **`blocks-phase3`** ("still-outside@16 / named children").

This plan closes the **honesty + accounting** gap: publish the still-outside@16 set (counts, classes, evidence), finish or stitch any incomplete mass/decision artefacts under plan **57** residency levers without bumping R, and either (a) discharge R-G5-4-a/b with proven-fixed + named residual children, or (b) name irreducible outside@16 / Gate-B classes as explicit residual children with RC — **no waivers**.

Oracle in force **`aeae426c…`** (historical discs for R01 counterfactuals remain as plan 44/39 require). flock + wrapper; `-j4` where encode appears; Master direct; Flash; no plan 04 P4–6; no 3-90; no reseat 170 / 3-16 / 3-17.

**Reconciliation appended 2026-10-08 (Design; Intent above unchanged).**
- Per Design steering 09:24, and because Execute already started 62 with it in scope, R-G5-4-c is **in scope** with gates and an RC path. R-G5-4-c is plan 45's 80/80 R01 rows in `eo_division_ceiling` cells, still outside at 16.
- Cody's hard bar as restated 2026-10-08: every deviation needs a proven root cause; no waivers; carried is not closed; never pick an arbitrary rule and call it proven.
- The oracle in force is now **`0c22b266…`** (plan 53; Perth `5b86d33e…`). The decide-limb discs stay `013586b5` / `4ed9cd80` (encoders `33006aa` / `d35b565`).
- No F6 / kind-order / roads / L8 work.

**Scratch-rule note (Design, 2026-10-09):** Cody's standing rule added: every phase outcome now includes a scratch receipt with named keep / delete lists (see "Scratch hygiene" and each phase). No other change to this draft.

## Problem

**Ground (GitHub `origin/master` `8498eec`, read-only on the box, 2026-10-08):**

1. **Plan 44 finished the mass.** `p5_owner_exclusive/phase2_decisions_full.tsv.gz` (sha256 `3d221b6f…`) holds **95,059 / 95,059** decisions. The partial 30k / 451 figures in the earlier draft are superseded. Final classes (`phase2_summary_full.json`), split by parent with the `src` column (weak = R-G5-4-a, none = R-G5-4-b):

   | Class | R-G5-4-a (94,134) | R-G5-4-b (925) | Total |
   | --- | ---: | ---: | ---: |
   | build:eo_bg_stitch | 87,648 | 95 | 87,743 |
   | producer_home_outside_R_cap (max 16) | 3,023 | 193 | 3,216 |
   | producer_ambiguous | 2,783 | 189 | 2,972 |
   | skip_divided_leaf (all depth 2) | 525 | 16 | 541 |
   | disagree_source_removed | 37 | 432 | 469 |
   | disagree_no_oe | 118 | 0 | 118 |

   Still-outside@16 = 3,216 rows / 122 cells, 3.38% of decided (`phase2_still_outside_r16_summary.json`; `phase2_residuals_still_outside_r16.tsv` sha `d11bcae8…`). Plan 44 states R-G5-4-a/b "not discharged".
2. **R-G5-4-c (plan 45).** 80 R01 rows, all depth 2, in 3 of the 4 `eo_division_ceiling` cells: (1797,424) 12, (828,862) 52, (832,856) 16; (827,869) has none. Window control ALL_OK (topology 4→1, 4→1, 4→16, 4→1). 80/80 `producer_home_outside_R_cap` at R=8; widen@16 **saturated**: cands@8 == cands@16, so no radius can add a candidate (`p4_ceiling/widen16.json`). `residuals.tsv` reclassified the row to `maps-parity-carried`. Under Cody's bar, carried is not closed.
3. **The plan-44 / plan-45 producer predates plan 46's root-cause fixes.** At tip:
   - `mass_decide.py` / `widen_outside.py` use `leaf_rect_raw` (the full-frame stub that plan 46 **RC4** replaced with `leaf_clip_geometry` for divided leaves);
   - they call `find_producer` with `piecewise=False` (whole-blob match; plan 46 **RC2**);
   - they draw candidates from Moore(R) only, with no `FarHomes` (plan 46 **RC3**);
   - they do not filter candidates to the record's type, while `clip_ring` forces `tc=code` (plan 46 **RC5**).
   
   Plan 45's `ceiling_decide.py` uses `rect = (0, 0, cr, cr)` for its depth-2 leaves (RC4) and the same `find_producer`. In plan 46, RC2–RC6 moved the boundary remainder from 3,980,980 rows (v2 + RC1) through 1,105,637 (v3, RC2) and 12,879 (v4, RC3 + RC4) to the exact 8,739 (v5). They also turned 1,007 / 1,023 fill groups from `producer_none` into decided ones and turned depth-2 `producer_none` to 0.
4. **Known-answer evidence for R-G5-4-c.** `p4_ceiling/rows_80_keys.tsv` carries a historical source (`src_ix, src_iy, src_rec`) for **58 / 80** rows: 57 at Chebyshev ≤ 1 from the home cell, 1 at 3; 22 rows have `src = -1`. So for most of the 80 the producer home is well inside R=8. "outside_R_cap" is a label for "no unique hit in the searched set", not proof of a far producer.
5. **Consequence.** No plan-44 or plan-45 residual class can stand as a root cause until the rows are re-decided under the plan-46 producer. The same holds in reverse for the 87,743 proven rows: without RC5, a unique hit can be another-type ring when RC2–RC4 hid the same-type producer. So their producers need a same-type audit before discharge.
6. **Non-goals:** loosening cover / OE; bumping R; waiving rows; R-G5-1 / R-G5-2 children (plans 63 / 64).

## Solution shape

### Domain: R01 residual census committed

- **Owns:** `triage/historical_bg/p9_r01_residual/` (new): one table over all R01 residual rows — R-G5-4-a/b 7,316 non-stitch rows plus R-G5-4-c 80 rows — with the plan-44 / plan-45 class, parent, cell, depth, and plan-45 historical source where present.
- **Contract:**
  1. Counts reconcile to the table in Problem item 1 and to the 80 / 3 cells.
  2. Every row carries its parent (a / b / c) and plan-of-origin class. No row is dropped or merged.
  3. gz sha-pinned + json summary; deterministic.
- **Non-goals:** deciding anything (census only).

### Domain: re-decide under the plan-46 producer (incl. R-G5-4-c)

- **Owns:** a re-decide driver that calls the plan-46 producer (`bg_producer_scan` helpers: `find_producer(piecewise=True)`, `FarHomes`, `leaf_clip_geometry`, same-type filter, raw-unit stats; clipper `33006aa`), then the unchanged design-44 decide limb (`d35b565` clip; byte or owner-exclusive vertex on `4ed9cd80`; K1 cite). Outputs under `p9_r01_residual/`.
- **Contract (all residual rows):**
  1. Each row gets a new class under the plan-46 producer, and the transition from its old class is recorded.
  2. Each transition is attributed to the RC that caused it (RC2 / RC3 / RC4 / RC5 / RC6) by single-fix ablation on a stratified sample per class. Plan 46's attribution table method applies.
  3. **Same-type audit of the 87,743 plan-44 proven rows:** every proven row's producer type equals the record type, or the row is re-decided and the change named.
  4. `skip_divided_leaf` (541, all depth 2) is decided through `leaf_clip_geometry`; "skip" is not an end class.
  5. `disagree_source_removed` (469) is held for plan 64's classifier, and `producer_ambiguous` survivors for plan 63's rule or sidecar. Until those land, such rows are named children with owner 63 / 64 and status blocks-phase3.
- **Contract (R-G5-4-c gates):**
  - **G-c1 window control:** plan 45 `window_control.json` ALL_OK is reused sha-pinned. If windows are rebuilt, ALL_OK is re-proved.
  - **G-c2 producer under plan 46:** all 80 rows are re-decided with divided-leaf clip geometry for depth-2 leaves and the exact global bbox-meet candidate set (Moore(8) ∪ FarHomes).
  - **G-c3 known-answer control:** for the 58 rows with a historical source, the plan-46 producer equals `(src_ix, src_iy, src_rec)` (index mapping fixed in refine), or each mismatch is named row by row. The 22 `src = -1` rows are decided on evidence alone.
  - **G-c4 decide limb on `d35b565`:** for each resolved row, the producer is clipped into every `d35b565` window leaf covering the old leaf (4→1 / 4→16 topology). The result is `build:eo_bg_stitch` with a byte or OE witness, or a named residual. The plan-45 clause-(c) note (window K1 background failing 0) is cited, never used alone.
  - **G-c5 no radius label:** `producer_home_outside_R_cap` is **not** an accepted RC for any R-G5-4-c row, because plan 45 proved the candidate set saturated. Unresolved rows get the actual failing step: no byte or fragment hit in the exact global bbox-meet set, with per-candidate evidence; ambiguous → plan 63; or a new class with its definition.
  - **G-c6 determinism:** re-decide run twice, byte-identical outputs.
- **Non-goals:** changing the OE limb, K1 or cover; bumping R; encoder or oracle changes.

### Domain: discharge or named children

- **Owns:** `residuals.tsv` R-G5-4-a / R-G5-4-b / R-G5-4-c; OVERVIEW ownership line (plan 65 wording first).
- **Contract:**
  1. **Discharge** a parent only when every row is proven-fixed or moved to a **named child** with a proven RC (e.g. R-G5-4-a-1 …). Count text appended as "UPDATED by plan 62", never rewriting history.
  2. R-G5-4-c leaves `maps-parity-carried`. It ends as discharged or as exact children with a proven RC.
  3. No waiver language. No "acceptable unexplained". No "carried" end state.
- **Non-goals:** R-G5-1 / R-G5-2 rows.

### Memory guardrails (all phases)

- Serial under `flock output/.heavy.lock` + `run_heavy_python.py --memory-max 12G` (MemorySwapMax=0).
- Re-decide streams per leaf with bounded caches (plan 46 LRU 4096) and `--cache-clear-every` (plan 44/57 lever).
- The plan-46 RssAnon watchdog (`--max-rss-mib`, 3072 MiB per shard) is used for any scan-path work.
- Known high-water to avoid: the plan-44 mass at 30k reached ~17.1 GiB host RSS without cache clearing. Chunk2 with clearing was ~2 GiB, and widen@16 peaked at 3.17 GiB.
- A watchdog trip or OOM is a stop_for_design with peak + leaf index. R is never raised to finish.
- Peaks go into the plan-56 ledger as `ledger/r01_residual_plan62.json` + SUMMARY row.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-62/`, any git worktree this plan adds, any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs; `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-62/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-62` before cleanup and after;
  2. after: `test ! -e output/scratch-62` (gone), or `ls -A output/scratch-62` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-62` gone.

## Decisions

1. Plan number **62**. Product residual honesty for R-G5-4-a/b/c after 44 / 45 / 46; not a memory plan (61) and not docs-only (60 / 65).
2. Master direct. Three phases: census; re-decide under the plan-46 producer (R-G5-4-c gates included); discharge or children. The earlier Phase 2 "mass finish / stitch" is dropped because plan 44 decided 95,059 / 95,059.
3. Standing: **do not bump mass R**; widen@16 stays the ruling for a/b, and the plan-46 producer is the matcher.
4. R-G5-4-c is **in scope** (Design steering 09:24; reconciled 2026-10-08). The earlier non-goal "absorbing plan 45 (R-G5-4-c)" is withdrawn.
5. Residual owner wording for a/b is fixed first by plan **65** (docs-only). This plan's Phase 3 appends results after it.
6. Tip `8498eec`; live oracle `0c22b266…`; decide-limb discs `013586b5` / `4ed9cd80`.
7. Flash; no seat ask from Design.

## Assumption ledger

### Assumption 1

- **Question:** Did plan 44 already discharge R-G5-4-a/b?
- **Answer chosen:** **No.** Closed as *owner*; it states "Not discharged". Parents stay `blocks-phase3` until every row is proven or named with RC.
- **Rationale:** plan 44 IMPLEMENTATION "Phase 2 CLOSED"; residuals.tsv.
- **If wrong:** none material; Phase 3 confirms.

### Assumption 2

- **Question:** May still-outside@16 (a/b) or R-G5-4-c be waived or left carried because most rows were recovered?
- **Answer chosen:** **No.**
- **Rationale:** Cody's hard bar.
- **If wrong:** none. Cody would have to promote a waiver design explicitly.

### Assumption 3

- **Question:** Must plan-44 / plan-45 classes be re-decided under the plan-46 producer before naming children?
- **Answer chosen:** **Yes.** They were produced by a matcher with four root-caused defects (RC2–RC5). A class from a known-defective matcher is not a root cause.
- **Rationale:** Problem items 3–5; plan 46 RC table; `rows_80_keys.tsv` near-home sources.
- **If wrong:** re-decide reproduces the old classes exactly, the classes are then confirmed under the fixed matcher, and the cost is one re-decide run.

### Assumption 4

- **Question:** Should this plan wait for 63 / 64?
- **Answer chosen:** No for Phases 1–2. In Phase 3, rows that need 63 / 64 become named children owned by those plans, then updated when those plans land.
- **Rationale:** Queue 62 → 63 → 64; avoid blocking census and re-decide.
- **If wrong:** Execute pauses Phase 3 until 63 / 64 close.

## Open questions

1. `src_rec` index semantics in `rows_80_keys.tsv` vs the spool ring index (refine maps them before G-c3).
2. Child id scheme (R-G5-4-a-1 … / R-G5-4-c-1 …) — lock in Phase 3 before editing `residuals.tsv`.
3. Execute already started from the earlier draft: whatever census work exists is reused if it matches Phase 1's contract.

## Phases

### Phase 1 — R01 residual census committed

- **Outcome:** `p9_r01_residual/census.tsv.gz` (+ json) has every R01 residual row (a/b 7,316 non-stitch + c 80) with parent, old class, cell, depth and historical source. Counts reconcile to Problem items 1–2. sha-pinned; no R bump; no waiver.
- **Scratch cleared (part of the outcome):** keep `p9_r01_residual/census.tsv.gz` + json and its generator (committed); the 56-ledger row if the census ran under the wrapper. Phase 2 reads only the committed census. Delete everything else under `output/scratch-62/`: census intermediates, per-leaf extracts, double-run copies once the byte compare is recorded, wrapper logs once their peak fields are in the ledger. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `triage/historical_bg/p9_r01_residual/`; plan-62 note.
- **Approach:** known. **Depends on:** plan 44 / 45 committed artefacts. **Refine:** skipped.

### Phase 2 — Re-decide under the plan-46 producer (R-G5-4-c gates)

- **Outcome:**
  - Every census row has a new class under the plan-46 producer and the decide limb.
  - Old→new transitions are attributed to RC2–RC6 by ablation sample.
  - The 87,743-row same-type audit is committed.
  - G-c1–G-c6 pass for R-G5-4-c: known-answer control on 58 rows, no radius label, determinism.
  - The double run is byte-identical, and the peak is recorded in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep decisions gz, transitions json, same-type audit json, driver + unit test (committed); `ledger/r01_residual_plan62.json` + SUMMARY row with wrapper max_rss / `memory.peak` copied in (plan 61 Phase 1 cites this committed row, not scratch). Phase 3 needs nothing else. Delete `output/scratch-62/` contents: run logs, shard outputs, the second determinism run, decoded leaf frames and ring caches, ablation-sample outputs, temp dirs the driver created. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `p9_r01_residual/` (driver, decisions gz, transitions json, audit json); `parser/tests/` (driver unit test); `parser/perf_inventory.json`; `output/scratch-62/` (logs).
- **Approach:** known. **Depends on:** Phase 1; plan 46 producer on tip. **Refine:** src index mapping; ablation sample size.

### Phase 3 — Discharge parents or name residual children

- **Outcome:** R-G5-4-a, R-G5-4-b and R-G5-4-c are each discharged with proof, or split into named children with a proven RC (63 / 64-owned children named as such). R-G5-4-c is no longer `maps-parity-carried`. `residuals.tsv` and the OVERVIEW pointer are honest. No Phase 3 product-close claim. No waivers.
- **Scratch cleared (part of the outcome):** keep `residuals.tsv`, plan-62 IMPLEMENTATION and OVERVIEW edits (committed). Delete the whole `output/scratch-62/` (including any `keep/`); the receipt shows the path gone. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `residuals.tsv`; plan-62 IMPLEMENTATION; OVERVIEW ownership line.
- **Approach:** known. **Depends on:** Phase 2; plan 65 landed. **Refine:** child id scheme.

## Provenance

- Tip GitHub `origin/master` **`8498eec`** (plan 46 close-out). Earlier draft (tip `10a976a`, oracle `aeae426c`, partial 30k figures) kept at box `62-r01-still-outside-r16.bak/`.
- Sources at tip: plan 44 IMPLEMENTATION (Units 4c–4f, Phase 2 CLOSED); `p5_owner_exclusive/phase2_decisions_full.tsv.gz` (`3d221b6f…`), `phase2_summary_full.json`, `phase2_still_outside_r16_summary.json`, `phase2_residuals_still_outside_r16.tsv` (`d11bcae8…`), `mass_decide.py` L265–283, `widen_outside.py` L214–245; `docs/plans/45-eo-division-ceiling-window-rebuild.md`; `p4_ceiling/{rows_80_keys.tsv, per_row_decisions.tsv, widen16.json, window_control.json, ceiling_decide.py}`; plan 46 record + IMPLEMENTATION at `e7eba63` (RC table); `parser/tools/bg_owner_exclusive.py` `find_producer(piecewise=False)` default; OVERVIEW L85 / L95; `residuals.tsv` R-G5-4-a/b/c.
- Design Ground computation on the box: the a/b split by `src`; the 80-row cell / source breakdown.
- Siblings: **63** (ambiguous rule / sidecar), **64** (source-removed classifier), **65** (owner wording), **61** (RSS).
- Rejected: R bump; cover loosen; waivers; carried end states; accepting pre-46 matcher classes as RC; seat asks; plan 04 P4–6; 3-90.
- Box draft only. No commit from Design.
