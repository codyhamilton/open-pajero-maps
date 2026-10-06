---
design_id:
---

# 3-14 cause and container attribution, with the AU 3-11 routed proof

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Root-cause designs for the AU 3-11 +60 B gap (and its routed proof) and for 3-14 payload cause attribution. Combine them if they share a mechanism. Void any item already resolved on master, with evidence. Reference the oracle in force `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448`. Never relabel. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded or streamed loads (plan 25). Master direct. Do not draw plan 04 Phases 4–6 or plan 06. Do not claim Phase 3 closed. No 3-90 re-run. Do not reseat 170, 3-16 or 3-17.

## Problem

Plan 31 recorded the chain hops and carried four residuals (`docs/design/oracle-chain-and-live-pin-contract.md` § Carried follow-ups; `oracle_chain.tsv`):

1. **AU 3-11 routed completeness.** The 37-cell list (sha `9f2b0e55…`) is complete under the multiset identity only. Plan 31 review F1: no routed run.
2. **3-14 payload causes.** AU 246,123 changed cells (L0 244,060 / L2 1,944 / L6 118 / L8 1) and Perth 795 (L0 784 / L2 11) are listed with no attributed causes. The 3-14 record's explanation census (AU 246,116 background-payload-only + 4 division-topology + 3 frame-ceiling; Perth 792 + 3) is lost (`explanations.json` not located). Its 7 AU / 3 Perth non-payload-only cells were "inference, not byte-proven".
3. **3-14 container/index/padding scope unmeasured.** The cell identity excludes offsets, container, index and sector padding by construction.
4. **AU 3-11 +60 B non-payload growth.** **Voided: attributed on master.** Plan 07 (`90b05b6` → landed `ced98f8`, independent review PASS at `176383a`, `docs/design/g-new-nonpayload-accounting.md`) named it Map Frame allocation padding: 21,570,746 → 21,570,806 B. The 41 changed spans give 34×(−4) + 7×(+28) = +60. Every other region was identical or relocation-only, with 0 unaccounted bytes. That comparison read both 3-11 discs in place (2026-10-03). Plan 31 (2026-10-06), the oracle-chain contract, the `oracle_chain.tsv` 3-11 residual and OVERVIEW L62 still call it unattributed. **That is stale wording, not an open cause.**

**Shared mechanism (why combined):**
- Items 1, 3 and 4 are the same question: where does every byte of a disc pair go, by region? Plan 07 answered it for 3-11 with a region partition. Applying that partition to the 3-14 hop answers item 3.
- Item 2 is the payload half of the same hop accounting: payload delta = Σ changed-frame deltas, attributed per cell.
- One committed region-accounting tool plus one per-cell payload attributor covers all of them. Reproducing plan 07's 41 rows is the tool's control.

**Ground (master `d2459b6`; host read-only listing 2026-10-06 AEST):**

| Item | Evidence | Note |
| --- | --- | --- |
| 3-11 hop | code `9269ebb` (parent `b7c7c42`); AU `87a01b14…` (1,731,021,568 B) → `013586b5…` (1,731,021,792 B); Perth unchanged | **`output/scratch-3-11/G/` (the `87a01b14` disc) is gone from the host** (oracle_chain residual "pre-3-11 disc not located"); `scratch-3-11/G_new` (`013586b5`) present |
| 3-14 hop | code `d35b565` (merged `414c5fe`), only `_cenc.c` among encoder sources between `9269ebb` and `d35b565`; AU `013586b5` → `4ed9cd80` (`output/scratch-14/G_new`); Perth `da13a775` (`scratch-3-11/perth_fix`) → `04be2f6e` (`scratch-29/perth_base`) | both discs present; routed diff 0 routed-only (`evidence/routed-3-14-{au,perth}.json`) |
| Region partition | plan 07 accounting: Data Volume, MHT, record-29 frame, PDMDH/LMR/BSMR, BMT/BMR address arrays, PMR buffers + tails, frame allocation padding, trailing pad; "fixed prefix, frame allocations and block buffers partition each file" | method recorded; **no committed tool** |
| Tools | `oracle_chain.py` `diff` / `routed-diff` / `check-census` / `publish`; plan 29 leaf-proof region classifier (Header, PDMDH, BMT, slot tables, padding) | reusable |

## Solution shape

### Domain: hop replay and region accounting

- **Owns:** a committed region-accounting tool, `triage/oracle_chain/region_accounting.py`, plus its synthetic tests. Given two discs, it partitions each file into the plan 07 regions with structure paths and reports per-region old→new size, relocation-only versus content change, and unaccounted bytes. Also owns the 3-11 predecessor replay.
- **Contract:**
  1. The partition is complete and disjoint for each file: Σ regions = file size, with 0 gaps or overlaps. Otherwise the tool exits non-zero.
  2. Changed-content comparison is by index path, so relocation never counts as content.
  3. Bounded preads only, under the wrapper and lock.
  4. 3-11 replay: build full AU from a worktree at `b7c7c42` (pre-3-11) with the pinned spool, to `output/scratch-36/G_pre311/`. Pin gate: sha `87a01b14…` and size 1,731,021,568. On a mismatch, stop and record `replay-mismatch` with both shas; never re-pin.
  5. Control: the tool on (`G_pre311`, `scratch-3-11/G_new`) reproduces plan 07: +164 payload (manifest 1,597,341,290 → 1,597,341,454), padding 21,570,746 → 21,570,806, the same 41 spans and deltas, 0 unaccounted.
  6. 3-11 routed proof: `oracle_chain.py routed-diff` on the 3-11 pair against the 37-cell list. Required: 0 routed-only and 0 baseline-missing cells.
- **Non-goals:** any encoder change; overwriting protected discs; reopening plan 07's conclusion except as a reproduced control.

### Domain: 3-14 container and payload attribution

- **Owns:** `triage/oracle_chain/hop_3_14/` with region accounting (AU, Perth), `cells_causes.tsv` (one row per changed cell) and `summary.json`.
- **Contract:**
  1. Container: the region tool on AU (`013586b5` → `4ed9cd80`) and Perth (`da13a775` → `04be2f6e`). Every byte delta is named by region, with 0 unaccounted. Payload delta = Σ per-cell frame deltas over the changed-cell list.
  2. Payload: for every changed cell, decode old and new frames with D1 by sub-layer section (background / road / name / other) and divided leaf. Record which sections differ, plus the footprint/leaf topology and frame length against the 131,070 ceiling.
  3. Cause classes are drawn only from mechanisms evidenced in the `d35b565` `_cenc.c` diff (for example the EO-aware `bg_shape` stitch via `eo_clip`, and its knock-on division-topology and frame-ceiling effects). Each class needs a stated byte-level predicate. A cell gets a class only when its predicate holds on its bytes. Otherwise it is `unattributed` and named.
  4. Endpoint control: rebuild at `33006aa` (parent of `d35b565`) and at `d35b565`. Each must reproduce `013586b5` / `4ed9cd80`, so the code diff is the only input change. A mismatch is reported, not re-pinned.
  5. The 7 AU / 3 Perth non-payload-only cells are byte-proven or named `unattributed`.
  6. Per-kind K1 `checked` delta for the hop, recomputed on changed cells only, equals the whole-disc delta. This feeds design 35 G4.
- **Non-goals:**
  - proving the 3-14 changes match R. DVD parity of the changed cells is named as a follow-on question, not asserted;
  - historical 3C-04 remainder attribution (design 35 G5);
  - plan 29 / 34 hops (already byte-proven).

## Decisions

1. Plan number 36. Master direct. Three phases.
2. Combined, because one region-accounting mechanism serves 3-11 and 3-14, and payload attribution is the per-cell half of the same hop account.
3. "+60 B gap" is **voided** as a root-cause item (plan 07). Phase 1 still reproduces it, because the tool needs a control and the routed proof needs the same replayed disc. Phase 1 also corrects the stale wording (plan 31 record follow-up line, oracle-chain contract, `oracle_chain.tsv` 3-11 residual, OVERVIEW) to cite plan 07 and the reproduction.
4. New discs only under `output/scratch-36/`. Protected discs are hash-checked before and after.
5. Oracle in force stays `4e6b0de7`. This design records evidence on historical hops and changes no disc in force.

## Assumption ledger

### Assumption 1

- **Question:** Can `87a01b14` be rebuilt byte-exact from `b7c7c42`?
- **Answer chosen:** Expected. The encoder and spool are deterministic (Perth `-j1` == `-j4` history), and the pinned spool fingerprint is unchanged (plan 34 protected_before/after).
- **Rationale:** Same inputs, same code.
- **If wrong:** `replay-mismatch` is recorded. The routed proof and plan-07 reproduction stay residual, named with both shas. Phase 2/3 proceed on the present 3-14 discs.

### Assumption 2

- **Question:** Do cause classes need a counterfactual per cell, or does whole-disc endpoint reproduction suffice?
- **Answer chosen:** Endpoint reproduction proves the code diff is the sole input change. Per-cell class assignment still needs each cell's byte predicate. Mechanism ambiguity (more than one class predicate holding) is reported as such, not resolved by rule order.
- **Rationale:** Never relabel. "Changed by 3-14" is not the same as "changed by the EO stitch".
- **If wrong:** Cody accepts hop-level attribution. Phase 3 then shrinks to the class census.

### Assumption 3

- **Question:** Phase 3 decodes 246,918 cells' old and new frames. Is that bounded?
- **Answer chosen:** Yes. Streamed per-cell preads from the changed-cell lists via D1, chunked, under the wrapper. No whole-file load.
- **Rationale:** Plan 25.
- **If wrong:** chunk size is reduced, not the scope.

## Open questions

1. Whether DVD (R) parity of 3-14-changed cells needs its own design. Raised only after `cells_causes.tsv` exists.
2. Whether the class predicates can also attribute the historical 8,739 / 137 background-family remainder (design 35 G5). That is not in scope here; Phase 3 output is the input to that question.

## Phases

### Phase 1: Region tool, 3-11 replay, routed proof

- **Outcome:**
  1. `region_accounting.py` plus tests.
  2. `G_pre311` sha `87a01b14…` (or `replay-mismatch` named).
  3. Plan 07's 41-row accounting reproduced exactly, with 0 unaccounted.
  4. 3-11 `routed-diff`: 0 routed-only, 0 missing against the 37-cell list.
  5. `oracle_chain.tsv` 3-11 row updated with the evidence. Plan 31 F1 discharged. "+60 B unattributed" wording replaced by a citation to plan 07 and the reproduction.
- **Surfaces:** `docs/plans/04-c-core-orchestration/triage/oracle_chain/{region_accounting.py,oracle_chain.tsv,oracle_chain.json,evidence/}`; `parser/tests/` (tool tests); `docs/design/oracle-chain-and-live-pin-contract.md`; `docs/plans/31-phase3-oracle-and-pin-gates.md` (follow-up pointer only); `docs/OVERVIEW.md` (one clause); `docs/provenance.md` (scratch-36); `parser/perf_inventory.json` (new module entry).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: 3-14 container/index/padding accounted

- **Outcome:**
  1. AU and Perth region accounting committed. Every byte delta is named by region, with 0 unaccounted.
  2. Payload delta equals Σ changed-frame deltas.
  3. The `oracle_chain.tsv` residual "container/index/padding outside this measurement" is replaced by the evidence.
- **Surfaces:** `triage/oracle_chain/hop_3_14/`, `oracle_chain.tsv` / `.json`.
- **Approach:** known. **Depends on:** Phase 1 (tool). **Refine:** skipped.

### Phase 3: 3-14 per-cell payload causes attributed

- **Outcome:**
  1. Endpoint rebuilds reproduce `013586b5` / `4ed9cd80` (or a mismatch is named).
  2. `cells_causes.tsv` covers all 246,123 AU and 795 Perth cells. Each row has a class with a byte predicate, or `unattributed`, with a count per class.
  3. The 7 AU / 3 Perth non-payload-only cells are byte-proven or named.
  4. Per-kind K1 `checked` hop delta is confined to changed cells.
  5. The `oracle_chain.tsv` 3-14 residual "payload causes not measured" is replaced by per-class counts, with `unattributed` = 0 or an exact list.
- **Surfaces:** `triage/oracle_chain/hop_3_14/`; a read-only D1 decode driver; `oracle_chain.tsv` / `.json`; OVERVIEW clause.
- **Approach:** open (class predicates are derived from the `d35b565` diff against the fixed outcome). **Depends on:** Phase 2. **Refine:** skipped.

## Provenance

- Master `d2459b6`. Sources:
  - plan 31 record and `oracle_chain.tsv` / `.json` residuals;
  - `evidence/routed-3-14-{au,perth}.json`;
  - plan 04 IMPLEMENTATION L206–213 (3-11), L221 (3-14 census);
  - `review_3-11.md` finding 3;
  - plan 07 record and `g-new-nonpayload-accounting.md`;
  - `git log` of encoder sources (`9269ebb`, `d35b565`);
  - host read-only listing of `output/scratch-3-11/` (no `G/`).
- Rejected:
  - re-attributing +60 B from scratch (already done);
  - hop-level "3-14 did it" as a per-cell cause;
  - re-pinning on replay mismatch.
- Box draft only.
