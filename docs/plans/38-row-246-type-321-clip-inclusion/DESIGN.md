---
design_id:
---

# Plan 30 row 246: type-321 record in L0 (834,886) and the clip-inclusion hypothesis

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Plan 38: plan 30 row 246. Byte-decode R's in-cell 321 record, match it to the kept edge-touching 321 relation, and test the clip-inclusion-rule hypothesis (R keeps boundary-touching or degenerate clips; our encoder drops them). The outcome is either a fix where no other cell or kind changes (K1 0 everywhere; disc diff confined; new successor oracle recorded) or a proven cause. Never a relabel. Oracle `4e6b0de785bdf454fbe928c53310c46a9861ad298f24539ba1e5ea3b6e19c448` or later. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`, bounded or streamed. Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

Plan 30 is closing at 341 supply-path / 0 unfixable / 1 carried. Row 246 is the carried row: `residuals.tsv` R-G9-1, `maps-parity-carried`.

**Ground (master `b10e787`):**

| Fact | Value | Source |
| --- | --- | --- |
| Row key | L0 (834,886), code 321, p0..p6 = 0, dump_row 246, plan 28 rule O05 | `30-2-01-source-data-parity/fingerprint.tsv` |
| R | 11 polygons of type 321 near the cell. **1 is cell-local** (meet branch a, leaf_path [1730], 28 coords). Normalised local signature spans the full 0–1 range on both axes | fingerprint `R_cell_local_meets`, `R_local_signatures`; `output/scratch-14/cell_local/proofs/246.json` |
| G | 0 type-321 records in the cell on `4ed9cd80` and `2ee3456a`. `4e6b0de7` differs only in 5 empty shells | fingerprint `G_*_type_count`; plan 34 |
| Spool demander | background ordinal 15 of source cell (0,834,885), branch b, 58 coords. Spool offset 2,806,410,336, length 34,248. Trigger vertex at cell_raw (4021.43, 2.39), lat/lon (−31.5416545, 116.0931811), on the shared edge | fingerprint `spool_demander_identity`; `output/scratch-14/witnesses/0246_requirement.json` |
| Clip | `clipped_ring_q` 2, `clipped_ring_area2` 0, `encoder_emits` False, mechanism `encoder_drops_clipped_source_sliver` | fingerprint |
| Supply search | PBF gap-free. 284 code-321 candidates reach the windows (natural=wood 274, scrub 10). Every one gives 0 in-cell records under original, clipped and unit-mult | `open_rows_account.md` (r4) |
| Related science | Plan 14 / 3-15: 188 + 86 completeness demands are sub-unit slivers that `rint` annihilates (`checker:repaired-not-representable`). K1 completeness now demands only representable footprints (`a890662`, `0dc5cac`) | `completeness_3-15_cell_local.md` L18 |

**Tension to resolve, not assume.** A 28-coord R polygon whose local signature spans the cell is not obviously a degenerate edge clip. The hypothesis is only true if R's record decodes to a boundary-hugging or zero/near-zero-area ring that matches our clipped sliver. If R's polygon has real interior area, the cause is elsewhere: different source geometry, or a different feature.

## Solution shape

### Domain: row-246 witness and match

- **Owns:** `docs/plans/38-row-246-type-321-clip-inclusion/witness/`, holding committed JSON plus a small driver.
- **Contract:**
  1. **R record decode:** bounded pread of R's L0 (834,886) leaf 1730 frame, D1 decode. Type-321 record: raw coordinates in cell units, ring closure, signed area2 at the encoder lattice, edge contacts (vertices on x=0/4096 or y=0/4096), the bbox, and the record and class header bytes. Byte offsets and sha256 are recorded.
  2. **G control:** the same cell on `4e6b0de7`, with every record listed by class, confirming 0 type-321.
  3. **Spool demander:** decode ordinal 15 of (0,834,885) from `level_0.data` by offset and length. Its in-cell clip under the production `bg_shape` contract (with q, area2, emitted points), plus its extract provenance (OSM object id and tags) where the spool records it.
  4. **Match predicate,** fixed before measuring: R's record matches the demander when every R vertex lies within 1 raw unit of the demander's clipped in-cell geometry or of the cell edge segment it touches, **and** the R ring's area2 sign and magnitude are those of the clip. Otherwise there is no match, and the nearest alternative among the 11 R polygons and the 284 candidates is named.
  5. Verdict ∈ {`H1-clip-inclusion` (R keeps the edge-touching or degenerate clip we drop), `H2-source-geometry` (R's ring has interior area that our source lacks in-cell), `H3-other-feature`, `unresolved`}, with the evidence.
- **Non-goals:** any encoder change; any other row.

### Domain: inclusion rule — fix or proven cause

- **Owns:** a guarded encoder change (only under H1) and its blast-radius census, or a proven-cause record.
- **Contract:**
  1. **H1:** write the inclusion rule R evidences as a byte-level predicate on the clip result (for example, keep a q ≥ 2 edge-collinear clip as R encodes it). Implement it behind a full-AU build to a new path under `output/scratch-38/`.
  2. **Blast-radius gate:** classified all-level diff against `4e6b0de7` (plan 36 region tool plus the plan 34 classified diff). **Fix-landed only if** the diff is confined to L0 (834,886) and adds exactly R's record bytes, and all of the following hold: K1 `-j6` failing 0 in every kind; Perth unchanged or byte-explained; goldens unchanged; full `parser/tests` green; protected discs hash-identical. A new successor oracle is recorded at a new path, with a classified diff record (plan 34 discipline).
  3. **If any other cell changes,** the fix is not landed. The changed-cell list with counts by level and kind is recorded, plus an R-check of a stated sample or all of them, and the verdict is `proven-cause` (the rule is real but broader than row 246). The broader rule becomes a named follow-on, never a partial landing.
  4. **H2 / H3:** the proven cause is recorded, with the R bytes and the spool or source evidence. Plan 30 row 246 is dispositioned `proven-cause:<class>` in `disposition.tsv` (append-only correction).
  5. No tolerance or checker change. No relabel to unfixable.
- **Non-goals:** the 341 supply-path implement unit; plan 04 Phases 4–6.

## Decisions

1. Plan number 38. Master direct. Two phases.
2. Phase 1's approach is known. Phase 2's is open: the rule shape depends on Phase 1's verdict, and the outcome branch is fixed.
3. Oracle `4e6b0de7`. A landed fix creates its successor. Any later oracle in force at execute time is used instead, and named.
4. R-G9-1 is dispositioned by this plan. It stays `maps-parity-carried` until Phase 2 closes.

## Assumption ledger

### Assumption 1

- **Question:** Is an R-check of every extra changed cell required before calling the broader rule `proven-cause`?
- **Answer chosen:** No. Extra cells already block landing (the confinement outcome). A sample or full R-check only informs the follow-on, and the sample rule is stated.
- **Rationale:** The requested outcome forbids other-cell changes; deciding their parity is follow-on scope.
- **If wrong:** Phase 2 adds an exhaustive R-check of the changed set.

### Assumption 2

- **Question:** Does H1 contradict plan 14's `repaired-not-representable` finding?
- **Answer chosen:** Not necessarily. Plan 14 measured rint-annihilated sub-unit faces (area 0 after quantisation). H1 is about R keeping an edge-touching clip. Phase 1 records whether row 246's clip is in the same class. If it is and R still has a record, plan 14's conclusion is named as challenged for that class, not silently overridden.
- **Rationale:** Never relabel.
- **If wrong:** the H1 rule touches the 274 representability rows. The blast-radius gate then blocks landing and the verdict is `proven-cause`.

## Open questions

1. Whether the spool records the OSM id for ordinal 15. If not, the match uses geometry only, and that is stated.

## Phases

### Phase 1: R record decoded and matched; hypothesis verdict

- **Outcome:**
  1. Committed witness: R record bytes, coordinates, area2 and edge contacts; G 0-record control; spool demander clip.
  2. Match result under the fixed predicate.
  3. Verdict H1 / H2 / H3 / unresolved, with evidence.
  4. Not done: no encoder change.
- **Surfaces:** `docs/plans/38-row-246-type-321-clip-inclusion/witness/`; read-only D1, spool reader, `bg_shape` probe (`parser/tests/fixtures/bg_eo/probe.c` pattern).
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Fix-landed with confined diff, or proven cause

- **Outcome:**
  - **Either:** successor disc with diff confined to L0 (834,886) adding R's record; K1 0 in every kind; Perth, goldens and full suite green; successor oracle record.
  - **Or:** `proven-cause` with the changed-cell census (H1 too broad) or the H2/H3 evidence.
  - Plan 30 row 246 dispositioned append-only. `residuals.tsv` R-G9-1 updated.
- **Surfaces:** `parser/kiwiw/_cenc.c` (H1 only); `parser/tests/`; plan 38 folder; `docs/plans/30-2-01-source-data-parity/disposition.tsv` (append-only); `triage/phase3_synthesis/residuals.tsv`; OVERVIEW; `docs/provenance.md`.
- **Approach:** open. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `b10e787`. Sources:
  - plan 30 `open_rows_account.md` (r4), `fingerprint.tsv`, `phase2_snapshot.md`;
  - `completeness_3-15_cell_local.md`;
  - plan 35 `residuals.tsv` R-G9-1;
  - plan 34 successor discipline.
- Rejected:
  - landing a rule that changes other cells;
  - `unfixable`;
  - asserting H1 from the mechanism label alone.
- Box draft only.
