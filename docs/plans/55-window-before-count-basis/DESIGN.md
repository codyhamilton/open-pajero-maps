---
design_id:
---

# Name the R-G8-1-b-a window_before vs 3-13 boundary count basis (or reclassify)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close **R-G8-1-b-a**: plan 43 review F1 (medium) found `window_before.json` per-window boundary "before" counts disagree with the 3-13 table in `causes_rootcause.md` L60–77 (e.g. **403 vs 255**, **1,224 vs 829**). Root cause not yet named — HEAD-checker dump rows vs the 3-13 report's counting. Context only for the after-0 supersession of **R-G8-1-b** (unaffected).

Oracle `4e6b0de7…`. Prefer light, offline-reproducible proof from committed artefacts; heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower, and only if a regenerable count cannot be reproduced from committed inputs. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief. Design grants no waivers. Assigned Execute instance: OpenCode DeepSeek Flash (Design does not start workers).

## Problem

Plan 43 discharged R-G8-1-b by whole-disc K1 failing 0 on `4ed9cd80` (superseded-by-proof). As context it committed `window_before.json` / `window_before.py`: for each of the nine 3-13 CF windows it records:

- `table_fill_before` / `table_boundary_before` — copied from `causes_rootcause.md` L60–77;
- `background_*` / `background_boundary_*` — counted from plan 39 keyed per-row arrays on the `87a01b14` basis (`output/scratch-39/keep/`).

**Ground (master `094b11f`):**

| Window (L0 examples) | `table_boundary_before` (3-13) | `background_boundary_all_types` (keyed dump) |
| --- | ---: | ---: |
| 0/288 [1769,202,1772,205] | 255 | 403 |
| 0/291 [828,745,831,748] | 829 | 1224 |

The residual is a **named unexplained deviation** between two committed figures. R-G8-1-b's after-0 claim does not depend on reconciling them; honesty still requires a root cause for the mismatch (or a documented dual-basis explanation that makes both numbers correct under named predicates).

Not covered by plans 44–53. Not a Cody-held waiver row.

## Solution shape

### Domain: column-basis proof

- **Owns:** `triage/independent_reviews/3-14/conditions/` evidence for R-G8-1-b-a (small JSON / md beside `window_before.*`).
- **Contract:**
  1. For every disagreeing window, state the **exact predicate** that produces each number:
     - 3-13 table boundary-before (cite `causes_rootcause.md` column / dump / checker / type filter / window inclusivity);
     - `window_before.py` keyed-array count (level/ix/iy/code filters; all-types vs type; `87a01b14` vs `013586b5` basis; overlap with the 37 3-11 cells).
  2. Reproduce both numbers from committed or regenerable inputs. If `scratch-39/keep/` is absent on the Execute host, regenerate the keyed arrays under flock at `-j4` from the pinned disc cited by plan 39, or name `unverifiable:<missing keep arrays>` with the blocker reported — do not invent counts.
  3. End state is one of:
     - **`explained-dual-basis`:** both figures correct under named, different predicates (document the map; residual discharged);
     - **`regenerated-agreement`:** one side was a counting bug; corrected committed context agrees with the table (or the table citation is amended with a pointer — do not silently rewrite 3-13 history);
     - **`named residual`:** disagreement remains after predicates are fixed; escalate with numbers (Design may reclassify).
  4. Update `residuals.tsv` R-G8-1-b-a accordingly. Touch OVERVIEW only if plan 54 has not already named the owner; prefer plan 54 for prose ownership sync.
- **Non-goals:** reopening R-G8-1-b; encoder changes; re-running 3-13 CF repairs; waivers.

### Domain: honesty surfaces

- **Owns:** a short note in the plan-43 conditions README (or sibling) stating the basis map; optional one-line in `docs/provenance.md` if a new scratch path is used.
- **Contract:** readers of `window_before.json` see which column matches the 3-13 table and which is the HEAD dump census. Fill-sentence / IMPLEMENTATION column basis stays single-named (plan 43 already restated this).
- **Non-goals:** mega-rewriting plan 43's collapsed record.

## Decisions

1. Plan number **55**. Master direct. Two phases. Refine skipped (approach known — column census vs committed table).
2. R-G8-1-b stays discharged. This plan does not weaken the after-0 supersession.
3. Prefer explained-dual-basis over rewriting history when both predicates are coherent.
4. No build-budget or waiver work (R-G8-1-a / R-G9-4 / R-G5-5 stay Cody holds).
5. Assigned instance: OpenCode DeepSeek Flash.

## Assumption ledger

### Assumption 1

- **Question:** Is the mismatch mainly all-types vs type-filtered, or checker-rule / basis drift?
- **Answer chosen:** Unknown until Phase 1. First compare type-filtered keyed counts to `table_boundary_before`; then checker generation / disc basis (`87a01b14` vs the 3-13 measurement disc).
- **Rationale:** The JSON already exposes both `_all_types` and `_type`; the cited examples (403/255, 1224/829) use all-types vs table.
- **If wrong:** the dual-basis explanation fails → regenerate under the 3-13 predicate or open a narrower residual.

### Assumption 2

- **Question:** Are plan 39 keep arrays required on disk?
- **Answer chosen:** Preferred. If missing, regenerate from the plan-39-cited disc under the lock, or stop with unverifiable naming the missing input — do not approximate.
- **Rationale:** Cody hard rule — unexplained deviation needs a root cause, not a guess.
- **If wrong:** host offline / arrays gone and discs unreadable → residual stays open as `unverifiable:keep-arrays-unavailable` until host is back (report; do not waive).

## Open questions

1. Should the 3-13 table's "Boundary before" column be annotated in `causes_rootcause.md` with the dual-basis pointer once explained? **Default yes** (one sentence under the table) if Phase 1 proves dual-basis; otherwise leave history untouched.

## Phases

### Phase 1 — Predicate census and reproduction

- **Outcome:** committed note listing, per disagreeing window, the predicate and reproduced integer for each side. Root-cause class chosen: dual-basis / counting bug / unreproducible.
- **Surfaces:** `triage/independent_reviews/3-14/conditions/` (b-a evidence); optional regenerator script under the same tree; `residuals.tsv` status note if still open pending Phase 2 wording.
- **Approach:** known. **Depends on:** none (host arrays or pinned disc). **Refine:** skipped.

### Phase 2 — Discharge or named residual

- **Outcome:** R-G8-1-b-a end state written (`explained-dual-basis` / regenerated agreement / named residual). README + optional `causes_rootcause.md` one-line pointer. No encoder change. Suite not required unless a tracked regenerator is added (then green under existing close gates).
- **Surfaces:** `residuals.tsv`; conditions README; optional provenance.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master tip used: GitHub `origin/master` **`094b11f`** (`094b11f0b0b719e4e7c7270d48f758a088be8dee`), box shallow fetch 2026-10-07 ~18:33 AEST. Host offline — not read.
- Sources: `residuals.tsv` R-G8-1-b-a; `window_before.json` / `window_before.py`; `causes_rootcause.md` L60–77; plan 43 close record; plan 39 keyed-array basis notes.
- Box draft only. No commit from Design.
