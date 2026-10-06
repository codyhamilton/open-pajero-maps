---
design_id:
---

# PSS at ≤ -j6 and plan 04 Phase 3 close synthesis

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Plans 31, 32, 33 and 34 are closed. Draft the PSS at `-j6` or lower plus Phase 3 close synthesis. Its outcome is an evidenced plan 04 Phase 3 close, or an exact named residual list (including plan 30's open rows if they are still open). Reference the oracle in force `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`; `2ee3456a…` and `4ed9cd80…` are historical and protected. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `parser/tools/run_heavy_python.py` with bounded or streamed loads (plan 25). Execute pushes straight to master: no feature branch, no PR. Do not draw plan 04 Phases 4–6 or plan 06. No 3-90 re-run. Do not reseat 170, 3-16 or 3-17.

## Problem

Plan 04's signed Phase 3 outcome (`docs/plans/04-c-core-orchestration/DESIGN.md` L152) has several parts:

- every failing item behind the 3C-04 counts is assigned exactly one cause, with the count per cause recorded;
- on the oracle disc in force, build-caused and checker-caused failures are 0 in every kind, and the remainder equals the enumerated spool list by item identity;
- the polygon 65623 defect is classified;
- the run takes ≤ 120 s;
- every sha change is a recorded re-oracle.

The 3-90 brief adds further gates: ≤ 120 s median of three at `-j 6`; PSS ≤ 9,726,501 kB; `-j 1` determinism after `COMPARE_EXCLUDES`; dump plus classify; per-kind counts; build sha, Perth, goldens and H budgets; full pytest; a complete independent fix-review chain; carried-item placement.

Since the 5c5823e 3-90 record, plans 16 and 27–34 have discharged several blockers. No single record yet lists, gate by gate on `4e6b0de7`, which gates are evidenced and which are not. OVERVIEW still names "PSS contract" and "close synthesis" as open.

**Ground (master `d2459b6a368577c14d6a806bd7897e5e9e6aa3ec`, fetched 2026-10-06 10:5x AEST):**

| Gate | Evidence on master | State |
| --- | --- | --- |
| Live K1 failing on `4e6b0de7` | `triage/l0_empty_slot/phase2/k1.json`: 0 in all 9 kinds, `-j6`, wall 82.769 s, `pss_peak_kb` 7,267,251 | single run; not a trio |
| PSS / timing trio at ≤ `-j6` | plan 20: ceiling 9,726,501 kB is the historical `-j12` peak; the gate runs at ≤ 6. Single `-j6` runs: plan 32 83.1 s / 7,478,057 kB on `2ee3456a`; plan 34 82.8 s / 7,267,251 kB on `4e6b0de7` | **no trio recorded**; OVERVIEW: "PSS bar not cleared" |
| `-j1` determinism (`timing` + `wall_s` stripped) | plan 16 fixed the strip; last `-j1` measurement predates the re-oracles | **not measured on `4e6b0de7`** |
| Build sha reproduction at HEAD | plan 34 encode produced `4e6b0de7` (118 s); Perth `04be2f6e…` byte-identical | from plan 34's own run; no independent reproduction at close HEAD |
| Pin contract | plan 31 `pin_contract.tsv`: ∅ = ∅ on `2ee3456a`; plan 34 K1 0 on `4e6b0de7` | needs re-applying on `4e6b0de7` |
| Other-kind classify joins | plan 32 `65e5eeb`: empty-set discharge on `2ee3456a` | 4e6b0de7 differs only in 5 empty shells; needs re-applying |
| Completeness joins | plan 28: 776 rows, 0 conflict-open; plan 14 3-03: K1 completeness failing 776 → 0 | closed |
| O04 seven | plan 33 `9b1980e`/`f4d4c96`: proven-non-deviation | closed |
| Oracle chain | plan 31 `oracle_chain.tsv` plus plan 34 successor record | chain recorded; 3-14 payload causes, 3-14 container scope and 3-11 routed proof still open (design 36) |
| 3-11 +60 B | plan 07 (`90b05b6` → `ced98f8`, review PASS at `176383a`): Map Frame allocation padding, 34×(−4)+7×(+28) | **attributed on master**; plan 31, oracle-chain contract and OVERVIEW still call it unattributed (stale) |
| Historical cause assignment | phase2_disposition: 8,739 boundary + 137 fill unattributed (180 groups); polygon 65623 "unestablished" (`cause_table.md` L50); R01 exclusivity unproven; 188 completeness → `checker:repaired-not-representable` (3-15 / plan 28) | **open** apart from completeness |
| Per-kind `checked` vs 3C-04 | 3C-04: range 309,192,246 / step 252,444,802 / road_node 42,995,770 / name_anchor 2,317,983 / background 174,332,105 / boundary 89,546,388 / completeness 1,800,514 / interior_cover 1,592,016. Now: 285,809,587 / 227,935,489 / 42,994,980 / 2,317,055 / 176,386,506 / 64,111,046 / 1,800,514 / 1,590,566 | moves not reconciled per hop |
| Independent fix-review chain | review_3-07/08/10/11/12/13 present; 3-14 BOUNCE plus rulings; **3-15, 3-16, 3-17 have no independent review file** (IMPLEMENTATION L713); plans 14, 28, 29, 31–34 have terminal reviews | **open** |
| Full pytest | `test_perf_inventory::test_inventory_covers_every_module` fails on `d2459b6` (6 modules missing; box run 1 failed / 3 passed) | **fails** (design 37 Phase 2) |
| Plan 30 (2-01 source parity) | 338 supply-path / 0 unfixable / **4 conflict-open** (dump_rows 246, 396, 397, 775); `open_rows_account.md`; Cody ruled that a pinned, date-matched OSM complete-relation snapshot may be admitted as a second source | **open**; ruling not yet executed |
| Docs drift | OVERVIEW L62 "CHM hold pending clear" (the hold is cleared); L79 "243 supply / 99 conflict-open" (now 338/0/4); "+60 B unattributed" (plan 07) | stale |

## Solution shape

Two domains: one bounded ops measurement, and one synthesis that holds every Phase 3 gate against evidence. The synthesis may close Phase 3 only if every gate passes. Otherwise it publishes the exact residuals, each with an owner. It invents no review, re-oracle, ceiling or pin.

### Domain: ops gate measurement on `4e6b0de7`

- **Owns:** fresh, raw-saved measurements of the operational gates on the oracle in force, under the wrapper and lock, in `output/scratch-35/`, with committed summaries in `docs/plans/35-pss-and-phase3-close-synthesis/evidence/`.
- **Contract:**
  1. Record HEAD, `git status`, and the sha256 of the disc in force (`4e6b0de7…`, 1,692,079,168 B) and of the Perth pin `04be2f6e…`.
  2. Timing trio: three dump-off `quantisation_roundtrip --engine c` runs at `-j 6` (the plan 20 ops cap), run serially. Report each wall and `timing.pss_peak_kb`, the median wall, and the max PSS. Pass = median ≤ 120 s **and** max PSS ≤ 9,726,501 kB. If `-j 6` fails the PSS bar, one more trio at `-j 4` is allowed, reported separately. The signed ceiling is never changed.
  3. Determinism: one `-j 1` run. Its report byte-equals a trio report after `strip_compare_excludes` (`timing`, `wall_s`).
  4. Empty-set census: one `-j 6 --dump-failures` run over every kind with failing > 0 in the trio. If none fail, census every K1 kind via the plan 32 empty-set contract (`docs/design/k1-empty-classify-joins.md`): dump bytes 0, manifest rows 0, K1 failing 0.
  5. Build gates: full-AU rebuild at the close HEAD to a new path gives sha `4e6b0de7…`; Perth `-j 1` == `-j 4` == `04be2f6e…`; full `parser/tests` pytest summary line quoted.
  6. Protected discs (`2ee3456a`, `4ed9cd80`, `013586b5`, plus the spool fingerprint) hash-identical before and after.
- **Non-goals:**
  - executing brief 3-90 or writing a "3-90" record;
  - re-signing the ceiling;
  - any encoder or checker change;
  - `-j > 6`.

### Domain: Phase 3 close synthesis

- **Owns:** `docs/plans/35-pss-and-phase3-close-synthesis/gates.tsv` (one row per gate), `residuals.tsv` (one row per open item), and `synthesis.md`. Plus, only on the close branch, the plan 04 Phase 3 record in `IMPLEMENTATION.md`. On either branch, the OVERVIEW blocker sentence is replaced by a pointer.
- **Contract:**
  1. Gates, each `PASS` / `FAIL` / `RESIDUAL`, with evidence path, sha256 and the exact quoted figure:
     - **G1** oracle in force and chain: every hop 87a01b14 → 013586b5 → 4ed9cd80 → 2ee3456a → 4e6b0de7 has a signing record, a confined cell list and attributed causes. Open causes are named (from design 36).
     - **G2** live failing is 0 in all 9 kinds on `4e6b0de7` (domain 1).
     - **G3** live pin contract ∅ = ∅, re-applied on `4e6b0de7`.
     - **G4** per-kind `checked` on `4e6b0de7` reconciled to the 3C-04 values through recorded hop deltas. Any move not accounted for by a hop record is a named residual.
     - **G5** historical cause assignment for every 3C-04 failing item: each kind's per-cause counts, with every unattributed row named (8,739 / 137 / 180 groups, polygon 65623, R01 exclusivity). `pinned_candidates` stays residual-not-required-for-live-close (plan 31) and is not rewritten.
     - **G6** ops gates (domain 1, contract items 2–3).
     - **G7** build gates (domain 1, contract items 5–6).
     - **G8** independent fix-review chain: one row per fix or science unit that changed code, rules or a disc (3-08 … 3-17; plans 14, 28, 29, 34). Each row gives the review artefact and verdict, or `missing`.
     - **G9** carried-item placement: plan 04 Phase 2 carried items as placed in DESIGN L173. Plan 30's open rows, quoted from master at synthesis time. The design-36 and design-37 outcomes.
     - **G10** doc consistency: OVERVIEW CHM wording, the L79 plan-30 counts, and "+60 B unattributed" versus plan 07.
  2. **Close branch:** only if G1–G9 are all PASS. Then write the plan 04 Phase 3 record (parameters, cause-per-kind table, gate figures, re-oracle chain with shas, pinned list ∅ with sha, Carried list) and the phase trailer.
  3. **Residual branch:** otherwise, `residuals.tsv` lists every non-PASS item with columns gate, item id, exact count or identity, evidence, owner (plan or "unowned → Design"), and blocking (`blocks-phase3` / `maps-parity-carried`). No Phase 3 trailer. OVERVIEW's blocker list becomes exactly the `blocks-phase3` rows.
  4. An independent clean-context review re-derives `gates.tsv` from the cited artefacts before landing.
- **Non-goals:**
  - fixing any residual;
  - writing reviews for 3-15–3-17;
  - re-running 3-17;
  - plan 30 execution;
  - plan 04 Phases 4–6;
  - plan 06.

## Decisions

1. Plan number 35. Master direct.
2. Two phases. Phase 1's approach is known. Phase 2's approach is known, and its outcome is a fixed branch (close or exact residual list). Refine is skipped.
3. Disc in force `4e6b0de7…`. Perth `04be2f6e…`. No re-oracle is expected; any sha mismatch in Phase 1 stops and is reported, not re-pinned.
4. PSS ceiling 9,726,501 kB stays as signed (plan 04 IMPLEMENTATION L135). The worker cap is ≤ 6 (plan 20).
5. Sequencing: design 37 Phase 2 (`test_perf_inventory`) should land before Phase 1's pytest gate, otherwise G7 is RESIDUAL. Design 36 feeds G1 and G4; if it has not closed, those gates carry its named open items.

## Assumption ledger

### Assumption 1

- **Question:** Does "no 3-90 re-run" forbid fresh gate measurements?
- **Answer chosen:** No. It forbids executing brief 3-90 (the fresh-verify unit and its record). Plan 35 measures the ops and build gates under its own record, which is what the request's "PSS at -j6 or lower" requires.
- **Rationale:** The PSS trio is explicitly requested. Determinism and build reproduction on the same disc and HEAD are needed for an evidenced close.
- **If wrong:** Phase 1 is limited to the timing/PSS trio. G6 determinism and G7 then become RESIDUAL "not measured on `4e6b0de7`", and the outcome is the residual list.

### Assumption 2

- **Question:** Do plan 30's 4 conflict-open rows and 338 supply-path rows block plan 04 Phase 3?
- **Answer chosen:** They are listed as `maps-parity-carried`, not `blocks-phase3`. Their K1 completeness failures already have a cause (checker over-demand, plan 14/28; K1 completeness failing 0). What stays open is DVD supply parity, owned by plan 30, which now has Cody's second-source ruling.
- **Rationale:** Phase 3's signed outcome is K1 cause attribution on the disc in force. The standing rule still keeps these rows open for Maps completeness, so they appear on the list by exact dump_row either way.
- **If wrong:** they move to `blocks-phase3`, and the close branch is unreachable until plan 30 closes.

### Assumption 3

- **Question:** Do historical 3C-04 rows that vanished after 3-14 without an attributed cause block the close?
- **Answer chosen:** Yes. The signed outcome says "every failing item … assigned exactly one cause". The 8,739 / 137 remainder, polygon 65623 and R01 exclusivity are `blocks-phase3` unless an evidence path assigns them.
- **Rationale:** Never relabel. Vanishing on a later disc is not a cause.
- **If wrong:** Cody rules that historical items are discharged by live 0. They then move to `maps-parity-carried` with that ruling cited.

### Assumption 4

- **Question:** Do missing independent reviews for 3-15, 3-16 and 3-17 block?
- **Answer chosen:** Yes, as G8 `missing`. They are not reseated or reviewed here.
- **Rationale:** The 3-90 dependency gate. No review is invented.
- **If wrong:** Cody waives. The waiver is cited in G8.

## Open questions

1. Ground predicts the residual branch (G5, G8, and G1 until design 36 closes). Whether Cody wants follow-on designs for the G5 historical remainder and the G8 review gap is decided after Phase 2 publishes `residuals.tsv`.
2. If `-j 6` fails PSS but `-j 4` passes PSS and misses 120 s, both figures are reported. Choosing between them is a Cody ruling, not a Phase 2 decision.

## Phases

### Phase 1: Ops and build gates measured on `4e6b0de7`

- **Outcome:**
  1. Trio at `-j 6`: three walls, median, three PSS peaks, max. PASS or FAIL against 120 s and 9,726,501 kB (plus an optional `-j 4` trio).
  2. `-j 1` determinism IDENTICAL or the exact differing keys.
  3. Empty-set census for every kind (or failing rows dumped).
  4. AU rebuild sha equal to `4e6b0de7…`; Perth `-j1` == `-j4` == `04be2f6e…`; pytest summary line.
  5. Protected hashes unchanged.
  6. Committed `evidence/` summaries with raw output under `output/scratch-35/`. Not done: no Phase 3 claim.
- **Surfaces:** `docs/plans/35-pss-and-phase3-close-synthesis/{evidence,commands.md}`; read-only `parser/tools/quantisation_roundtrip.py`, `run_heavy_python.py`, plan 32 census tool, `build_alldata`; `docs/provenance.md` (scratch-35).
- **Approach:** known. **Depends on:** plans 31–34 (closed); design 37 Phase 2 preferred before the pytest step. **Refine:** skipped.

### Phase 2: Close synthesis — evidenced close or exact residual list

- **Outcome:**
  1. `gates.tsv` G1–G10, each with evidence and sha.
  2. Either the plan 04 Phase 3 record with trailer (all of G1–G9 PASS), or `residuals.tsv` naming every open item with count/identity, owner and blocking class. That list includes plan 30's open rows as quoted from master (currently dump_rows 246, 396, 397, 775, and the 338 supply-path rows), the G5 remainder, G8 `missing` units, and any design 36/37 items still open.
  3. OVERVIEW blocker paragraph replaced by a pointer to `residuals.tsv` (or the close record), with the G10 drift corrected.
  4. Independent review PASS.
- **Surfaces:** `docs/plans/35-pss-and-phase3-close-synthesis/{gates.tsv,residuals.tsv,synthesis.md}`; `docs/OVERVIEW.md`; on the close branch only, `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md`.
- **Approach:** known. **Depends on:** Phase 1. Designs 36/37 if they have landed (otherwise their items are residual). **Refine:** skipped.

## Provenance

- Master `d2459b6a368577c14d6a806bd7897e5e9e6aa3ec`.
- Sources:
  - plan 04 DESIGN L152 (Phase 3 outcome), L133 (3C-04 counts), IMPLEMENTATION L135 (signed ceiling), L713 (review gap);
  - `briefs/3-90-fresh-verify.md` checks 1–8;
  - plan 20 (ops cap);
  - plan 31 `oracle_chain.tsv`, `pin_contract.tsv`;
  - plan 32 `phase2_disposition.md`;
  - plan 34 `phase2/k1.json`, `successor_oracle_4e6b0de7.json`;
  - plan 07 `docs/design/g-new-nonpayload-accounting.md`;
  - plan 30 `open_rows_account.md`;
  - box pytest run of `test_perf_inventory` on `d2459b6`.
- Rejected:
  - calling single `-j6` runs a trio;
  - treating live 0 as historical attribution;
  - treating plan 30 as silently closed;
  - re-signing the ceiling;
  - running brief 3-90.
- Box draft only.
