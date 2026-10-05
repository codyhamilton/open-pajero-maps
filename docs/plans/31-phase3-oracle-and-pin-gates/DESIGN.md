---
design_id:
---

# Plan 04 Phase 3 — oracle chain and pin gates (slice 1)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Draft the plan 04 Phase 3 close package. The full package (PSS PASS at ≤`-j6` / plan-20 re-verify; other-kind native classify joins; 3-11 versus 3-14 oracle; `pinned_candidates` set-equality) is too large for three phases, so this design is **slice 1 only**: the oracle exact-cell-identity gate and the `pinned_candidates` Phase-3 disposition. The provable final outcome of the *whole* package may later be an evidenced plan 04 Phase 3 close, or an exact named residual list; this slice never claims that close. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; no 3-90 re-run. Skip plan 29 close-out (Execute).

## Problem

Plan 04 Phase 3 remains open. OVERVIEW's remaining Phase 3 blockers (tip `5ff9eb0`) are: PSS contract (ceiling held; live gate ≤`-j6`, bar not cleared), other kinds' native classify joins, **3-11 versus 3-14 oracle**, and **`pinned_candidates` exhaustive set-equality** (100/26650, unverifiable from git — plan 27). CHM heavy hold is cleared (Quality Assessor 2026-10-06), so the package is drawable under the memory wrapper. Plan 29 close-out has **not** landed on tip yet (folder still present; no collapsed `29-…md`); successor disc in force is already `2ee3456a…` per OVERVIEW / 3-90 successor-pin note.

| Blocker | What tip shows | Why it blocks Phase 3 close |
| --- | --- | --- |
| 3-11 vs 3-14 oracle | IMPLEMENTATION / OVERVIEW: "exact changed-cell proof for the prescribed 3-11 versus later 3-14 oracle" unresolved. 3-11 re-oracle: 37 L0 cells (`Gnew.diff_cells.txt`). 3-14 re-oracle: 246,123 AU cells with explanation census. Plan 29: +1 leaf in L0 `(0,541)`. No committed chain table joining these to the disc in force. | DESIGN Phase 3 / 3-90 gates require knowing which oracle is in force and that every sha move is a recorded re-oracle with exact cells. |
| `pinned_candidates.tsv` | 100 shown groups; footer `TOTAL_GROUPS=26650 TOTAL_ROWS=1939931 SHOWN=100 TRUNCATED=yes`. Plan 27: exhaustive identity **unverifiable from git** (enumerate artefacts non-committed). File sha256 `7dfe6ed7…`. | 3-90 check 4 set-equality needs a pinned list; inventing 26,650 rows is forbidden. Live K1 on successor has **0 failing in every kind** (plan 29 compare), so the *live* spool-pin set for close may be empty — that relationship is unstated. |
| Other-kind classify joins | Completeness joins recovered by plan 28 only. Background / boundary / interior_cover / name_anchor side-table producers were scratch-era (like pre-28 completeness). | Separate mega-unit; not this slice. |
| PSS PASS at ≤`-j6` | Plan 20 amended the contract; live trio not run; bar not cleared. | Separate heavy follow-on; not this slice. |

**Ground (committed + read-only, tip `5ff9eb0`):**

1. Disc-in-force chain (full digests): `87a01b14b612…7862` (pre-3-11) → `013586b58490…5f04` (3-11 `G_new`) → `4ed9cd801bdd…9d72` (3-14) → `2ee3456a9aeb…e6ae` (plan 29 successor, in force). Perth: `da13a775…` → `04be2f6e…` (unchanged by plan 29 code).
2. Live K1 on successor: exit 0; failing 0 for background, background_boundary, completeness, interior_cover, name_anchor (and other kinds in the compare). Historical name_anchor failing 1 cleared by plan 29.
3. `pinned_candidates.tsv` is an intentional candidate view, not the exhaustive pin list. Plan 27 already ledgered unverifiable-from-git; it did not settle Phase 3 close semantics under a 0-failing successor.
4. Host listing (2026-10-06): `output/scratch-3-11/Gnew.diff_cells.txt` present (37 lines). `scratch-3-08/enumerate_*.tsv` not found in the main or plan-14 checkouts sampled — recovery or re-enumerate must be evidenced, not assumed.

The ticket for **this slice** is not satisfied: neither oracle cell-identity proof nor pin disposition for Phase 3 close exists as a committed gate artefact.

## Solution shape

Discharge the two **honesty / identity** Phase 3 leftovers. Leave PSS and other-kind joins to follow-on designs. Never claim plan 04 Phase 3 closed here.

### Domain: re-oracle cell-identity chain

- **Owns:** a committed proof that every sha move from the Phase 2 / 3-11 baseline through the disc in force is a recorded re-oracle with an exact changed-cell (or changed-leaf) set, and that unexplained cells are named.
- **Contract:**
  1. A committed table (plan-31 folder) with one row per hop:
     - from_sha → to_sha (full digests);
     - unit that signed the hop (3-11, 3-14, plan 29, …);
     - changed-cell / changed-leaf count and artefact path + sha256 of the authoritative list;
     - confinement claim (e.g. 3-11: exactly 37 predicted L0 cells; plan 29: L0 `(0,541)` leaf 928 only);
     - unexplained count (0 required, or listed).
  2. Hops in scope: at minimum `87a01b14…→013586b5…` (3-11), `013586b5…→4ed9cd80…` (3-14), `4ed9cd80…→2ee3456a…` (plan 29). Perth hops ledgered or explicitly N/A with proof.
  3. Evidence may reuse existing scratch lists (`Gnew.diff_cells.txt`, 3-14 `explanations.json` / diff artefacts, plan-29 `successor_diff.json`) when their sha256 is recorded and contents match the hop claim. Missing artefacts are regenerated only under `run_heavy_python.py` + lock, at a new scratch path, without overwriting protected discs (`4ed9cd80…`, `013586b5…`, `2ee3456a…`).
  4. This domain does **not** re-sign a re-oracle; it proves the chain that already landed.
  5. OVERVIEW's "3-11 versus 3-14 oracle" bullet is narrowed to discharged or to an exact named residual (e.g. a hop whose cell list cannot be reproduced).
- **Non-goals:** no new encode; no Phase 3 close; no Phases 4–6; no 3-90 brief execution; no other-kind classify; no PSS trio.

### Domain: pinned list disposition for Phase 3 close

- **Owns:** the relationship between `pinned_candidates.tsv` (100/26650 candidate view), any recoverable exhaustive enumerate, and the **live** pin set on the disc in force required by DESIGN Phase 3 ("spool-caused failures equal the pinned list").
- **Contract:**
  1. **Live pin set on successor `2ee3456a…`:** state with evidence whether live K1 failing per kind is 0 (cite plan-29 compare and/or a bounded re-measure under the wrapper). If failing is 0 in every kind, the live pinned-failure set for close is **empty**; set-equality against that empty set is recorded as the live close pin contract — **not** as a fabrication of historical S02 rows.
  2. **Historical candidate view:** `pinned_candidates.tsv` remains a brief-required 100-row view (`TRUNCATED=yes`, sha256 `7dfe6ed7…`). Exhaustive 26,650-group identity is either:
     - **reproduced:** enumerate artefacts recovered or regenerated under the wrapper, sha-pinned, and set-equality against the historical spool-assigned groups proven; or
     - **residual:** `unverifiable` / `not required for live close` with root cause (scratch gone; live failing 0), never a silent "fine".
  3. No invented pin rows. No rewriting the 100-row TSV into a fake full list.
  4. OVERVIEW's `pinned_candidates` exhaustive set-equality bullet is narrowed to the live-empty contract and/or the historical residual named above.
  5. Relationship to 3-90 check 4: this slice documents what a *future* close verify must compare (live empty set on successor). It does **not** execute `briefs/3-90-fresh-verify.md`.
- **Non-goals:** no full residual dump re-extend; no registering new rules; no Phase 3 close claim; no PSS.

## Decisions

1. Plan number **31**. Land on master directly. No feature branch. No pull request.
2. **Split.** Full Phase 3 close package exceeds three phases (other-kind joins ≈ plan-28 scale; PSS is a heavy trio; close synthesis depends on both). This design is slice 1: oracle chain + pin disposition. Follow-ons listed in `NEXT-CANDIDATES.md`.
3. Two phases. Approaches **known**. Refine skipped. One worker may carry both.
4. **No Phase 3 close in this plan.** Final outcome of this slice is: both blockers discharged **or** an exact named residual list for either. The eventual close claim belongs to a later design whose outcome is exactly that and is evidenced.
5. **No 3-90 re-run.** Bounded reads/diffs under the wrapper are allowed; executing the full 3-90 brief is not.
6. Disc in force: `2ee3456a…`. Historical oracles retained byte-untouched.
7. Heavy work only under `run_heavy_python.py` + `output/.heavy.lock` (plan 25). Prefer light reuse of committed and retained scratch artefacts.
8. Do not reseat 170, 3-16, 3-17. Do not draw plan 04 phases 4–6 or plan 06. Skip plan 29 close-out surfaces (Execute).

## Assumption ledger

### Assumption 1

- **Question:** With live K1 failing 0 on the successor, is the Phase 3 "pinned list" for close the historical 26,650-group S02 candidate set?
- **Answer chosen:** No. On the disc in force, spool-caused *failures* equal the empty set. Historical `pinned_candidates` / S02 enumerations remain science evidence for pre-fix dumps, disposed separately under Contract §2.
- **Rationale:** DESIGN Phase 3 outcome is on the oracle disc **in force at phase close**; plan 29 moved that disc and cleared live failures.
- **If wrong:** Cody requires historical exhaustive pin set-equality before any close design. Phase 2 then prioritises enumerate recovery; live-empty contract becomes a second column.

### Assumption 2

- **Question:** Must this slice regenerate missing `enumerate_*.tsv` from a live dump?
- **Answer chosen:** Only if recoverable scratch hashes fail and Cody/Execute authorise a bounded regenerate. Default is: prove live-empty; mark historical exhaustive set unverifiable or recovered — do not invent.
- **Rationale:** Plan 27 standing rule; standing rule against fabricated pins.
- **If wrong:** A follow-on owns authorised full enumerate + set-equality.

### Assumption 3

- **Question:** Does discharging these two blockers clear OVERVIEW's Phase 3 blocked status?
- **Answer chosen:** No. PSS and other-kind joins remain. OVERVIEW narrows only the two bullets this slice covers.
- **Rationale:** Honest residual list.
- **If wrong:** Cody wants a single "Phase 3 evidence" umbrella sentence — still without a close claim.

### Assumption 4

- **Question:** Is plan 29's 146-byte L0 `(0,541)` hop in scope for the oracle chain?
- **Answer chosen:** Yes — it is the tip of the disc-in-force chain. Evidence already in plan-29 witnesses; this plan records it in the chain table.
- **Rationale:** Close gates need the disc in force, not a historical intermediate alone.
- **If wrong:** Chain stops at `4ed9cd80…` and successor is a footnote — worse for close readiness.

## Open questions

1. Whether host `enumerate_*.tsv` / 3-14 diff artefacts still exist under another worktree path — Execute inventories under read-only listing before any regenerate.
2. Whether OVERVIEW should still say "blocked at 3-90" after this slice (yes, until PSS + joins + a close design land).

## Phases

### Phase 1: Every disc-in-force re-oracle hop has an exact changed-cell (or leaf) proof

- **Outcome:**
  1. Committed chain table covering `87a01b14…→013586b5…`, `013586b5…→4ed9cd80…`, `4ed9cd80…→2ee3456a…` (full digests), each with artefact path, artefact sha256, changed count, confinement claim, unexplained count.
  2. Unexplained cells for each hop are 0, or each is named with why it is open.
  3. OVERVIEW "3-11 versus 3-14 oracle" wording narrowed to discharged or to the exact residual hop/cells.
  4. Protected discs re-hashed unchanged when touched only for read.
  5. Not done: no Phase 3 close; no PSS; no other-kind joins; no 3-90 brief; no P4–6.
- **Surfaces:** `docs/plans/31-phase3-oracle-and-pin-gates/` (table + note); `docs/OVERVIEW.md` (narrow one bullet); read-only plan 29 witnesses, scratch-3-11/3-14 artefacts, provenance.
- **Approach:** known.
- **Depends on:** tip ≥ `5ff9eb0`; retained hop artefacts or wrapper-bounded regeneration.
- **Refine:** skipped.

### Phase 2: Live pin contract for Phase 3 close is stated; historical 100/26650 disposed without invention

- **Outcome:**
  1. Committed disposition note + TSV/JSON: live failing counts per kind on successor (cited or re-measured under wrapper); live pinned-failure set = empty iff failing 0 everywhere; set-equality statement for live close.
  2. Historical `pinned_candidates.tsv`: sha256 verified; disposition `reproduced-exhaustive` **or** `residual-unverifiable` / `residual-not-required-for-live-close` with root cause; if reproduced, set-equality proof against enumerate artefacts with counts 26650 / 1939931 checked.
  3. OVERVIEW `pinned_candidates` exhaustive set-equality bullet narrowed accordingly.
  4. Explicit: plan 04 Phase 3 **not** closed; PSS and other-kind joins remain blockers.
  5. Not done: no full 3-90; no invent pin list; no P4–6; 170 / 3-16 / 3-17 not reseated.
- **Surfaces:** plan-31 folder; `docs/OVERVIEW.md`; optional bounded K1 read via `run_heavy_python.py`; read-only plan 27 ledger, pinned TSV, plan 29 compare.
- **Approach:** known.
- **Depends on:** Phase 1 (disc in force identity settled).
- **Refine:** skipped.

## Provenance

- Ground tip: `origin/master` `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7`. Plan 29 close-out not yet on tip (folder present). Box `/workspace/open-pajero-maps` already at that tip (`git fetch` / ff no-op).
- Quality Assessor 2026-10-06: CHM hold cleared; Phase 3 package drawable; plan 29 close-out skip; carried residuals listed. Weighed in Decisions §2 (split).
- Evidence cited: OVERVIEW blockers; plan 04 DESIGN Phase 3 outcome / Assumption 1; IMPLEMENTATION remaining-blocker paragraphs; `briefs/3-90-fresh-verify.md` successor-pin note; plan 20 residual (PSS trio still needed); plan 27 pin ledger (`pinned_candidates` unverifiable); plan 28 completeness joins only; plan 29 successor compare (live failing 0); `pinned_candidates.tsv` footer 26650/100; 3-11 `Gnew.diff_cells.txt` (37 cells) on host.
- Rejected: claiming Phase 3 closed; inventing 26,650 pins; full 3-90 re-run; folding PSS or other-kind joins into this slice; P4–6 / plan 06; reseating 170 / 3-16 / 3-17; plan 29 close-out work.
- Draft format followed: `/workspace/maps-design-drafts/30-2-01-source-data-parity/DESIGN.md` / plan 28 draft.
- Design method: workflow design skill; headless assumption ledger.
- Adversarial pass in-context (disclosed): (1) package too big — split required; (2) live failing 0 changes pin-close semantics vs historical S02 view; (3) oracle chain must include plan 29 hop; (4) no close claim without PSS + joins.
- Workflow-service / `artifact_feedback` skipped. Box draft only: no commit or push.
