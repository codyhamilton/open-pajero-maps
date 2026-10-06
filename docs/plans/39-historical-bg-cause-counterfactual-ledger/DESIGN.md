---
design_id:
---

# Historical background-family causes by counterfactual: 3-11 checked moves, 8,739 + 137 remainder, polygon 65623, R01 exclusivity

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual rows R-G4-1 and R-G5-1..4 from plan 35's `residuals.tsv`:
- the 3C-04 → `013586b5` checked moves;
- 8,739 background_boundary and 137 background historical unassigned rows;
- Region polygon 65623;
- R01 exclusivity against build.

Never relabel: a row vanishing on a later disc is not a cause. Oracle `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` or later. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`, bounded or streamed. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief. Do not reseat 170, 3-16 or 3-17.

## Problem

Plan 04 Phase 3's signed outcome requires every 3C-04 failing item to be assigned exactly one cause. Plan 35's G5 left four background-family items unattributed. G4 left the 3-11 hop's checked moves unexplained.

**Ground (master `b10e787`):**

| Row | Exact meaning | Evidence |
| --- | --- | --- |
| R-G4-1 | K1 checked on `013586b5` (3-90 rerun #3) minus 3C-04 on `87a01b14`: range +861,107, step +693,171, background +839,197, background_boundary +21,910, interior_cover +29. road_node, name_anchor and completeness 0 | plan 04 IMPLEMENTATION ≈L698–705 |
| R-G5-1 | 8,739 background_boundary rows unassigned after 3-12/3-13, counted on the `013586b5` basis; row mapping to the 3C-04 basis not stated | plan 32 `phase2_disposition.md`; `rebaseline_3-17_9064.md` |
| R-G5-2 | 137 background fill rows (180 groups combined with R-G5-1: 98 ambiguous producer, 45 non-longest crossing, 37 no crossing) | `causes_residual.md` H12; `review_3-12.md` item 8 |
| R-G5-3 | Region polygon 65623 = source (L0, home 1689,508, record 0, type 288, n 1810). Closing edge 1808 is 1,908,357.17 raw long; no proper crossing; finite-grid parity agreement; "zero rows established as caused by this source" in all five kinds | `cause_table.md` L48–52; `causes_bg.md` H4 |
| R-G5-4 | R01 (checker, `in_eo_same == 1`, 920,773 background rows) exclusivity against build unproven. 3-14, a build-only change, took R01 920,786 → 0 | `rules_bg.json` R01 note; `review_3-13.md` finding 3 |

**What makes a counterfactual possible now:**
- **K1 is fixed:** background-family K1 sources (`_k1_bg.c`, `_k1.c`, `_k1_cmp.c`) have had only dump/diagnostic and completeness changes since Phase 2 (`8d96e3a`, `1cf40f8`, `a890662`, `0dc5cac`). Phase 2's 3-02 run reproduced the 3C-04 report outside timing.
- **Encoder-only change:** the 3-14 hop (`33006aa` → `d35b565`) changed only `_cenc.c`.
- **Discs available:** plan 36 P1 replayed `87a01b14` byte-exact at `output/scratch-36/G_pre311` (encode 26 s at `-j4`). `013586b5` (`scratch-3-11/G_new`) and `4ed9cd80` (`scratch-14/G_new`) exist.
- **Dumps lost:** the 3-12-era dumps are gone (host `output/scratch-3-12` holds only `extend.py`). The remainder identities must be regenerated.
- **Plan 36 Phase 3** (running) produces per-cell 3-14 cause classes (`hop_3_14/cells_causes.tsv`).

## Solution shape

Fix the checker and spool, vary only the disc (or only the checker), and assign causes per row from the result.

### Domain: basis reconstruction (3C-04 ↔ 3-11 disc)

- **Owns:** `triage/historical_bg/` with K1 reports, dump manifests, regenerated identity tables and a basis map.
- **Contract:**
  1. K1 at HEAD (dump off, `-j6`) on `87a01b14` (replay) reproduces the 3C-04 checked and failing counts for range, step, road_node, name_anchor, background, background_boundary and interior_cover. Completeness failing is allowed to differ by the plan 14 rule change, and that difference is stated.
  2. Per-cell K1 checked counts (bounded windows, or the existing per-cell report option) on the 37 3-11 cells, old and new. The Σ delta equals the whole-disc delta per kind, and non-37 cells delta is 0. **R-G4-1 then reads:** "moves confined to the 37 O06 count-wrap cells, caused by the 3-11 same-class split exposing previously wrapped records". This holds only if the per-cell decode shows the extra checked items are records beyond 4095 in a wrapped class; otherwise the residual is named.
  3. Dumps (background, background_boundary, interior_cover) on `013586b5`, classified with `rules_bg.json` / `rules_other.json` as of the 3-13 land (`aa7e840` / `a9432c1`). This reproduces the 9,064 remainder split (137 / 8,739 / 188) and 180 groups exactly, or reports the exact difference. Identity tables are committed (keys only, bounded).
  4. Basis map: each remainder row on `013586b5` is mapped to its `87a01b14` row (identical outside the 37 cells), or named as 3-11-introduced.
- **Non-goals:** completeness (plan 28 closed it); new rules.

### Domain: build/checker counterfactual assignment

- **Owns:** `triage/historical_bg/assignment.tsv` (one row per remainder row and per R01 row) and an updated cause-table section.
- **Contract:**
  1. Same K1, same spool. Dump the three kinds on `4ed9cd80` (3-14 build change only).
  2. **Build-fixed predicate** (all must hold):
     - (a) the row is absent from the `4ed9cd80` dump;
     - (b) its item is still checked on `4ed9cd80` (same cell, type and shape; checked, not removed);
     - (c) its cell is in the 3-14 changed list with a plan 36 P3 class from the `d35b565` diff.
     If so, cause = `build:<class>`. Otherwise `unattributed`, named with the failing clause.
  3. **R01 exclusivity:** apply the same predicate to every R01 row. If all satisfy it, R01's checker attribution is contradicted for those rows, and the cause is recorded as `build:<class>` with R01's original note preserved and the supersession stated (as 3-13 did for S02–S05). Rows that fail it stay checker, with the reason. A mixed result is reported by count. Rule edits only append evidence and note text; predicates and order do not change unless the counterfactual proves it, and the proof is cited.
  4. Rows where (b) fails (item removed) are never `build-fixed`. They are named `removed-by-3-14`, and that becomes their own named residual if no other cause applies.
- **Non-goals:** re-litigating S02–S05; spool fixes.

### Domain: polygon 65623 classification

- **Owns:** a `cause_table.md` section replacing "unestablished" with the result.
- **Contract:**
  1. Exhaustive exact producer join (3-12 H12 `kw_bounds` arithmetic) of every failing row in all five kinds on `87a01b14` (3C-04 basis) against source (L0, 1689, 508, record 0, type 288, n 1810). Count per kind.
  2. If the count is 0: classify "no 3C-04 failing item is produced by source 65623". The alleged disc defect then has no failing-item footprint, and its geometry facts (long closing edge, no proper crossing) are stated as facts, not a cause.
  3. If the count is > 0: those rows take their cause from the counterfactual domain.
  4. If the old 3C narrative's "disc defect near 65623" refers to a specific cell or footprint, it is located from the 3C record and checked on all discs.
- **Non-goals:** a new spool repair.

## Decisions

1. Plan number 39. Master direct. Three phases.
2. Combined, because one basis reconstruction and one counterfactual pair serve all five rows.
3. Depends on plan 36 Phase 3's `cells_causes.tsv` for clause (c). If plan 36 P3 leaves cells `unattributed`, rows in those cells stay `unattributed`.
4. Dumps are bounded via `dump_io` memmap, per kind and serially. Large scratch is deleted after the identity tables are committed.

## Assumption ledger

### Assumption 1

- **Question:** Is "absent at fixed checker and spool after a build-only change, item still checked, cell changed by a named encoder mechanism" sufficient for a build cause?
- **Answer chosen:** Yes. It is the counterfactual the cause table uses: changing only the build removes the failure without removing the item.
- **Rationale:** 3-13's S02–S05 → build used the same logic with CF windows. This extends it exhaustively.
- **If wrong:** Cody requires a geometry-level defect witness per row. Phase 2 then adds stratified witnesses and the rest stay named.

### Assumption 2

- **Question:** Can HEAD K1 stand in for the 3-12-era K1 on background kinds?
- **Answer chosen:** Yes, once Phase 1 item 1 reproduces 3C-04 and item 3 reproduces 9,064 exactly.
- **Rationale:** No semantic change to background K1 since Phase 2 (git log).
- **If wrong:** the K1 at `1cf40f8` is built in a throwaway worktree and used instead.

## Open questions

1. R01's original checker rationale (Amendment 4 interior-for-fill) may remain true even if 3-14 removed the failures. If both hold, the rows are reported `build` with a checker note, and Cody's one-cause rule may need a ruling on dual-cause rows. That is raised only if Phase 2 finds such rows.

## Phases

### Phase 1: Basis reconstructed; R-G4-1 confined or named

- **Outcome:**
  1. HEAD K1 on the `87a01b14` replay reproduces 3C-04 (completeness difference stated).
  2. 3-11 checked moves confined to the 37 cells and explained by wrapped records, or the exact residual named.
  3. 9,064 remainder regenerated with identity tables and the 3C-04 basis map.
- **Surfaces:** `docs/plans/04-c-core-orchestration/triage/historical_bg/`; read-only K1, `k1_triage`, `dump_io`; `docs/provenance.md` (scratch-39).
- **Approach:** known. **Depends on:** plan 36 P1 (closed). **Refine:** skipped.

### Phase 2: Remainder and R01 assigned by counterfactual

- **Outcome:**
  1. `assignment.tsv` covers all 8,876 remainder rows and 920,773 R01 rows, each with `build:<class>`, `checker` (R01 only, with reason) or named `unattributed` / `removed-by-3-14`, and counts per cause.
  2. R01 exclusivity proven, disproven or mixed by count.
  3. `rules_bg.json` notes appended only.
- **Surfaces:** `triage/historical_bg/`, `triage/rules_bg.json` (notes), `triage/cause_table.md`.
- **Approach:** known. **Depends on:** Phase 1; plan 36 P3. **Refine:** skipped.

### Phase 3: Polygon 65623 classified; residual rows updated

- **Outcome:**
  1. Producer-join count per kind for source 65623, with the classification.
  2. `cause_table.md` 65623 section rewritten from evidence.
  3. `residuals.tsv` R-G4-1 and R-G5-1..4 updated to discharged, or to the exact remaining rows.
- **Surfaces:** `triage/cause_table.md`, `triage/historical_bg/`, `triage/phase3_synthesis/residuals.tsv`, OVERVIEW clause.
- **Approach:** known. **Depends on:** Phase 1 (dumps); Phase 2 for causes. **Refine:** skipped.

## Provenance

- Master `b10e787`. Sources:
  - plan 35 `residuals.tsv` / `synthesis.md`;
  - plan 04 IMPLEMENTATION 3-90 rerun #3 (check 5);
  - `cause_table.md`, `causes_bg.md`, `causes_residual.md`, `causes_rootcause.md`, `review_3-12/13.md`, `rules_bg.json`;
  - plan 32 disposition;
  - plan 36 IMPLEMENTATION P1 (replay at 26 s);
  - git log of `_k1*.c` and `_cenc.c`;
  - host read-only listing (3-12 dumps absent).
- Rejected:
  - live-0 as a cause;
  - forcing 180 groups into spool;
  - silent R01 flip.
- Box draft only.
