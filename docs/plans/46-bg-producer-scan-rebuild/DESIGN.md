---
design_id:
---

# Tracked background producer scan: rebuild row identities on the 3C-04 basis for R-G5-1 (8,739) and R-G5-2 (137)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ruling 1 (2026-10-06): for R-G5-1 (8,739 `background_boundary`) and R-G5-2 (137 `background`), design a new tracked producer scan that rebuilds row identities against the committed 3C-04 basis (plan 39's replay of `87a01b14`). Each row then gets a proven cause or is named as a residual.

R-G8-4-c (the 8,876 old identities, 3-17 condition) is the same evidence and is carried here.

Design grants no waivers. Oracle `4e6b0de7…`. Heavy work only under flock plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

On `013586b5` the classify left 8,739 background_boundary rows and 137 background rows unattributed (`causes_residual.md` L1, L14). Their side columns came from scratch producers that were deleted:

| Column | Byte | From |
| --- | ---: | --- |
| `s02_producer_verified` | 144 | 3-07 |
| `other_mechanism` | 145 | 3-08 |
| `residual_crossing_verified` | 146 | 3-11, via `dump_join.py` residual mode |

`docs/provenance.md` (L376–422) says they are "not regenerable by this old recipe". 3-14 cleared all of them on `4ed9cd80` (kind failing 0), but no per-row cause exists. The 3-17 rebaseline kept the 8,876 old identities only as counts.

**Ground (master `6538530`):**
- **3C-04 basis:** `87a01b14`, replayed byte-exact by plan 39 P1 / plan 36 at `output/scratch-36/G_pre311` (encode 26 s, `-j4`). K1 built at `1cf40f8` reproduces 3C-04 exactly.
- **Documented semantics of `residual_crossing_verified`:**
  - a unique byte-exact original producer;
  - no E1 cover substitution;
  - explicit closure;
  - closing edge = longest edge;
  - at least one proper closing-edge crossing.

  It was computed with the C ring encoder (`-O2 -ffp-contract=off -fPIC`) and `kw_bounds` arithmetic. The full-scan figures are 425,416 entries, 30,558 fill groups, 216,488 boundary groups, 3 cover groups and 70,999 qualifying source rings.
- **S02 pin set:** `review_3-07.md` L27, `pins_S02.tsv`: 1,939,053 rows / 25,772 groups.
- **3-12 / 3-13 remainder:** 137 / 8,739 / 188 (completeness); 180 groups.

## Solution shape

### Domain: tracked producer scan

- **Owns:** `parser/tools/bg_producer_scan.py`, the C shim `parser/tools/_bg_producer_scan.c` (built from the commit's `_cenc.c` ring encoder, `-O2 -ffp-contract=off -fPIC`), tests, and a perf-inventory entry.
- **Contract:**
  1. **Input:** a disc, its K1 dump (144/152 B rows), the pinned spool, and the encoder commit whose ring code produced the disc.
  2. **Output:** per dump row, (a) the producer under design 44's classes — **unique-byte** (clip bytes equal the record) or **unique-fragment** (every identity-bearing vertex of the record appears in S's clip into L, and at least one of those is exclusive among candidates), or `producer_none` / `producer-ambiguous`; (b) bit fields reproducing `s02_producer_verified` and `residual_crossing_verified` exactly per the documented semantics (those historical bits remain byte-exact-producer predicates as documented; where a row is unique-fragment only, the bit is false and the mechanism tag records fragment attribution); (c) a mechanism tag where (b) is false.
  3. **Bounded:** streaming by `(level, home)` groups; under the lock.
  4. **Reproduction gate on 3C-04 / `013586b5`:** S02 1,939,053 rows / 25,772 groups; residual-mode full-scan figures 425,416 / 30,558 / 216,488 / 3 / 70,999; classify remainder 137 / 8,739. Any difference is named row-by-row, never absorbed. Plan 39's basis map (3C-04 ↔ `013586b5` row correspondence) is reused. Historical byte-exact figures are not rewritten to absorb fragments; fragment rows are named separately under the revised design 44 classes.
- **Non-goals:** changing K1 or rules order; non-background kinds.

### Domain: per-row cause of the 8,876

- **Owns:** `triage/historical_bg/p6_producer/` holding the committed 8,876 identity table (gz, sha-pinned, closing R-G8-4-c), per-row verdicts and a summary.
- **Contract:**
  1. **Identity:** from the scan, each row gets its key, its producer under unique-byte or unique-fragment (or `producer_none` / `producer-ambiguous`), and its failing mechanism.
  2. **Proven cause** only where demonstrated:
     - `build:eo_bg_stitch`: the row's vertex is not failing on `4ed9cd80`, and the producer's `d35b565` clip into the leaf byte-equals a `4ed9cd80` record or holds an owner-exclusive vertex (design 44 rule; S may be unique-byte or unique-fragment); or
     - another build or spool cause, with a byte witness (for example, closing-edge crossing proven by the shim, with the source ring cited).
  3. **Otherwise** a named residual with the failing step (`producer_none`, `producer-ambiguous`, `no-owner-exclusive-vertex`, `source-removed` / `removed`).
  4. `residuals.tsv` R-G5-1, R-G5-2 and R-G8-4-c are updated; `causes_residual.md` gets a note only.
- **Non-goals:** relabelling historical counts; the 188 completeness rows (design 47).

## Decisions

1. Plan number 46. Master direct. Three phases.
2. Depends on design 44 Phase 1 for the owner-exclusive tool, which is reused, not duplicated. Producer and identity rule are design 44's revised classes: **unique-byte or unique-fragment**, then the OE limb.
3. Whether 3-08's `other_mechanism` (byte 145) is reproduced: only if needed to explain the 137. Otherwise it is recorded as not rebuilt, with the reason.
4. Design 44's producer was revised for EO fragments after the Phase 1 control stop at `0551ed2` (byte-equal-only yielded systematic `producer_none`). This design cites the revised classes; phase counts and non-goals are unchanged. Historical reproduction gates that require byte-exact producers stay byte-exact; fragment attribution is additional, not a rewrite of those gates.

## Assumption ledger

### Assumption 1

- **Question:** Do the documented semantics suffice to rebuild the deleted producers byte-for-byte?
- **Answer chosen:** Probably. The provenance text gives the full predicate and the compile flags.
- **Rationale:** 3-12 H12 used the same arithmetic.
- **If wrong:** the reproduction gate fails. The difference is named per row and the original column is kept as historical; new verdicts come only from the tracked scan.

### Assumption 2

- **Question:** When a row has no unique-byte producer but has unique-fragment, can design 44's OE limb still prove `build:eo_bg_stitch`?
- **Answer chosen:** Yes. Unique-fragment is a valid producer class under revised design 44; proven-fixed still requires the OE / new-disc checks. Historical bits that demand byte-exact producers remain false for fragment-only rows.
- **Rationale:** Lockstep with revised design 44 after the `0551ed2` control stop (`control_analysis.md`: identity-proven shapes are often EO fragments).
- **If wrong:** fragment rows that fail OE stay named residuals; no waiver.

## Open questions

1. Whether the 180 groups count refers to boundary groups of the 8,739 or all 8,876. To be resolved from `review_3-13.md` in Phase 1.

## Phases

### Phase 1: Producer scan landed and reproduction-gated

- **Outcome:** the tool with tests. A reproduction table on 3C-04 / `013586b5` against every historical figure, with exact matches or named differences.
- **Surfaces:** `parser/tools/bg_producer_scan.py`, `_bg_producer_scan.c`, `parser/tests/test_bg_producer_scan.py`, `parser/perf_inventory.json`, `docs/provenance.md`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: 8,876 identities committed

- **Outcome:** the identity table, sha-pinned. R-G8-4-c discharged.
- **Surfaces:** `triage/historical_bg/p6_producer/`, `residuals.tsv`.
- **Approach:** known. **Depends on:** Phase 1. **Refine:** skipped.

### Phase 3: Per-row cause or named residual

- **Outcome:** all 8,876 decided. R-G5-1 and R-G5-2 discharged or replaced by exact residual children.
- **Surfaces:** `p6_producer/`, `residuals.tsv`, `causes_residual.md` (note).
- **Approach:** known. **Depends on:** Phase 2; design 44 Phase 1 under the revised producer contract. **Refine:** skipped.

## Provenance

- Master `6538530`. Sources:
  - `residuals.tsv` R-G5-1, R-G5-2, R-G8-4-c;
  - `causes_residual.md`;
  - `docs/provenance.md` L376–422;
  - `review_3-07.md`, `review_3-13.md`;
  - plan 39 P1;
  - `rebaseline_3-17_9064.md`;
  - design 44 revision after `0551ed2` (unique-byte / unique-fragment producer; `control_analysis.md`).
- Box draft only.
