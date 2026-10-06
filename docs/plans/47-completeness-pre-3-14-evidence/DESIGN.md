---
design_id:
---

# Regenerate the 3-15 / 3-16 / 3-17 completeness evidence (739 → 776, the 188, the 89)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ruling 5 (2026-10-06): for the plan 40 review-condition rows, regenerate the lost evidence where possible. Otherwise each row becomes superseded-by-proof (citing a later committed proof) or a named unverifiable residual.

This design takes the completeness rows that are too heavy for design 43:

| Rows | Unit |
| --- | --- |
| R-G8-2-a, -b, -c, -d, -e | 3-15 |
| R-G8-3-a, -b, -c, -d | 3-16 |
| R-G8-4-d | 3-17 |
| R-G8-1-g | depends on the 3-15 / 3-16 ACCEPT |

Design grants no waivers. Oracle `4e6b0de7…`. Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

Plan 40's reviews accepted 3-15 and 3-16 on conditions. Their scratch evidence is deleted (`scratch-3-12`, `-3-13`, `-3-15`, `-3-16`, `-3-17`).

**Ground (box master `6538530` plus Cody's host, read-only):**
- **Surviving:** `open-pajero-maps-14-completeness/output/scratch-14/p3/indep/old_dump_311/completeness.bin` (106,416 B = 739 rows; K1 on `013586b5`, old rule) and `new_dump_311`.
  - `sets.json`: A = 739, B = 52, P = 776, F = 52, with every set difference empty.
  - Plan 14 record L43 cites the 739 / 52 result.
- **Tracked:** `parser/tools/k1_representable.py` and `test_k1_completeness_representable.py` (plan 14, `a890662` / `0dc5cac`). These hold the representable-footprint proof that superseded the 3-16 window counterfactual's conclusion.
- **3-15 figures** for the 188:
  - 885 faces / 189 meets / 205 in-cell / 0 representable;
  - controls 725 / 781 and 16 / 16;
  - legacy contract 739 = 363 / 132 / 56 / 188;
  - 86 added unattributed + 3 added O04 not representable;
  - 3-16 result 0 / 89 pass.
- **3-16:** 34 rings → 156 faces, serialization error 1.86e-9. The scripts are lost.
- **TSV** carries `baseline_padded_frame_sha256` per key for the 89.

## Solution shape

### Domain: committed key lists and set arithmetic

- **Owns:** `triage/independent_reviews/3-15/conditions/keys/`.
- **Contract:**
  1. Copy the surviving `old_dump_311/completeness.bin` to the box (CopyToBox, read-only on the host). Record its sha.
  2. Cross-check with a fresh K1 built at `1cf40f8` on `013586b5` (at `-j4`, under the lock); it must give 739 rows, byte-equal after the canonical sort.
  3. Commit the 739 key list and the set-diff against plan 28's 776 on `4ed9cd80`: 739 − 52 cleared + 89 added = 776, with the 188 located as a subset of the 739 per the legacy partition 363 / 132 / 56 / 188 (any mismatch is named per key).
  4. Verify the 3-12 / 3-14 native-row order against the 3-17 identity table.
- **Closes:** R-G8-2-b, R-G8-3-a, R-G8-4-d.
- **Non-goals:** changing the K1 completeness rule.

### Domain: representability and legacy contract

- **Owns:** `triage/independent_reviews/3-15/conditions/representability/`.
- **Contract:**
  1. A per-key table for the 188 and the 89 via the tracked `k1_representable.py`: faces, meets, in-cell, representable. Compare with the 3-15 numbers (885 / 189 / 205 / 0) and the controls. Equal means R-G8-2-a and R-G8-2-d are regenerated; unequal means the difference is named per key.
  2. **Legacy-contract recomputation 363 / 132 / 56 / 188:**
     - regenerated if a tracked legacy-contract producer exists at a cited commit;
     - else superseded-by-proof if plan 14's representable rule covers the claim;
     - else `unverifiable:<producer deleted>`.

     This is R-G8-2-c.
- **3-16 numerics (R-G8-3-c, R-G8-3-d):**
  - The conclusion is superseded-by-proof by plan 14.
  - The face table is regenerated via `k1_representable`.
  - The 1.86e-9 serialization error and the home/index audits are named unverifiable unless the method is rewritten. It is not rewritten by default (Decision 3).

### Domain: root cause of the 89 (R-G8-2-e, R-G8-3-b)

- **Owns:** `triage/independent_reviews/3-16/conditions/r89/`.
- **Contract:**
  1. Re-extract the 89 target frames from `4ed9cd80` and match the TSV `baseline_padded_frame_sha256` per key (R-G8-3-b, first half).
  2. Decode the legacy `013586b5` records covering each of the 89 keys. Test them against the source EO interior with exact `kw_bounds` arithmetic:
     - **chord artefact:** a legacy piece covers area outside the source's EO interior;
     - **valid lost coverage:** the piece is inside the EO interior and the stitch omits it.

     Record whether R (the DVD) has a record there.
  3. **Label decision:**
     - "EO-stitch build regression" stands only for keys whose legacy piece was valid and R matches legacy.
     - Keys whose legacy piece was a chord artefact get that proven cause; the 3-16 0/89 counterfactual pass is consistent with this.
     - Any other key is a named residual.

     Labels are rewritten only by this evidence, not relabelled.
  4. The counterfactual half of R-G8-3-b is superseded by step 2 (a direct per-key cause). If step 2 cannot decide a key, that key is an unverifiable residual.

### Domain: R-G8-1-g

R-G8-1-g closes when every 3-15 and 3-16 condition row above has an end state.

## Decisions

1. Plan number 47. Master direct. Three phases.
2. Host evidence is read via CopyToBox only. Nothing runs on `codyh-ubuntu`.
3. 3-16's custom window counterfactual method is not rewritten: plan 14's tracked proof supersedes its conclusion. Rewriting it would only reproduce numerics.

## Assumption ledger

### Assumption 1

- **Question:** Is `old_dump_311` the 3-12 739 set?
- **Answer chosen:** Yes; `sets.json` and plan 14 L43.
- **Rationale:** Same disc, same K1 commit class.
- **If wrong:** the fresh K1 at `1cf40f8` becomes the source of record.

## Open questions

1. Whether R's per-key presence is decodable for all 89 frames (DVD frame extraction is already tracked). If not, the label decision falls back to the EO-interior test alone, and that is recorded.

## Phases

### Phase 1: Key lists and set arithmetic

- **Outcome:** the 739 list is committed and cross-checked; the set-diff is committed; the native order is verified. R-G8-2-b, R-G8-3-a and R-G8-4-d have end states.
- **Surfaces:** `triage/independent_reviews/3-15/conditions/keys/`, `residuals.tsv`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Representability and legacy contract

- **Outcome:** the per-key table; end states for R-G8-2-a, -c, -d and R-G8-3-c, -d.
- **Surfaces:** `…/3-15/conditions/representability/`, `residuals.tsv`.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

### Phase 3: The 89 root cause

- **Outcome:** the 89 frames sha-matched; a per-key proven cause (`chord-artefact` / `valid-lost` / residual). End states for R-G8-2-e and R-G8-3-b, then R-G8-1-g.
- **Surfaces:** `…/3-16/conditions/r89/`, `residuals.tsv`, the 3-16 REVIEW (appendix note only).
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `6538530`. Sources:
  - `residuals.tsv` R-G8-2-*, R-G8-3-*, R-G8-4-d, R-G8-1-g;
  - `independent_reviews/3-15`, `3-16`, `3-17` REVIEW.md;
  - plan 14 record L43;
  - host `scratch-14/p3/indep/{old_dump_311,new_dump_311,sets.json}` (read-only).
- Box draft only.
