---
design_id:
---

# Encoder content trim against R: L8 road 308, L0 road 207, L0 background 227

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual row R-G9-3: encoder content trim on the oracle in force, with no R-parity proof and invisible to K1. Outcome: expand-to-zero with a confined, recorded successor oracle, or a proven cause (including proven non-deviation if R drops exactly the same items). Never a relabel. Oracle `4e6b0de7…` or later. Heavy work only under flock plus the wrapper (encode ≤ `-j4`, K1 ≤ `-j6`). Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

The encoder trims items by priority when a divided sub-cell cannot fit the 131,070 B frame ceiling (`_e2.c` `dv_trim`, "last tier"). It prints `** >1% BLOCKER **` when a level's dropped share exceeds 1% (`parser/build_alldata.py` ~L645–652).

**Ground (master `b10e787`; manifest of `4e6b0de7` read-only on host):**

| Level | Kind | Dropped / total | Sub-cells | Note |
| --- | --- | --- | --- | --- |
| 8 | road | 308 / 14,012 (2.198%) | 1 (hard-ceiling fallback sub-cell (3,0), 308 / 2,417) | prints BLOCKER; identical on `87a01b14`, `013586b5`, `4ed9cd80`, `4e6b0de7` (3-14 TRIM ruling) |
| 0 | road | 207 / 3,015,057 | 1 | same absolutes as the `l0_divided_trim_halo` golden window (1755,591)–(1756,592) |
| 0 | background | 227 / 11,029,580 | 1 | same window |

- **Sources:** `output/scratch-34/G_new/manifest.json` `trimmed_items`; plan 35 `run_p1.log` L134, L152–153; plan 04 IMPLEMENTATION L230–233 (Design TRIM ruling 2026-10-03: "known budget … Design ticket for any expand-to-zero follow-up").
- **No R-parity measurement exists** for these items. K1 checks G against the spool only for emitted items, so trimmed items are invisible to it. The manifest gives counts only, not item identity or parent cell (except via the window golden and the build log).

R is the reference. If R carries the trimmed items in those parcels (for example, deeper division or a different sub-cell split), our trim is a deviation. If R carries none of them, or exactly the same subset, that is evidence for a shared budget rule.

## Solution shape

### Domain: trim witness against R

- **Owns:** `docs/plans/42-encoder-trim-r-parity/witness/`.
- **Contract:**
  1. **Item identity:** a bounded instrumented encode of only the affected parent cells (window builds that reproduce the same trim absolutes; equality with the full-AU counts required) emits the exact trimmed item list: level, parent, sub-cell, kind, spool shape id, priority, bytes.
  2. **R decode:** D1 decode of R's parcels covering the same parent at the same level. Record R's division topology for the parent (number of sub-cells, frame lengths) and, per trimmed G item, whether R contains a matching item. Roads match by spool polyline geometry within 1 raw unit plus class; background by type plus ring geometry. Each item gets a status: present / absent / ambiguous.
  3. **G control:** the emitted items in the same sub-cells, cross-checked against R the same way, so the match rule is shown to find known-present items.
  4. Verdict per level and kind: `R-has-trimmed` (count), `R-lacks-trimmed` (count), `ambiguous` (count), plus the R topology difference.
- **Non-goals:** any encoder change.

### Domain: expand-to-zero or proven cause

- **Owns:** an encoder division change (only if R evidences it), or the proven-cause record.
- **Contract:**
  1. If R carries trimmed items and uses a topology we can state as a rule (for example, divide one level deeper, or a different split order), implement that rule. Full-AU build to `output/scratch-42/`.
  2. **Landing gate:** trimmed totals 0 in every level; classified diff against `4e6b0de7` confined to the affected parents' frames and index entries (plan 36 region tool); every changed frame's added items present in R; K1 `-j6` failing 0 in every kind; Perth unchanged or byte-explained; goldens recaptured only for the trim window, with justification; full `parser/tests` green; protected discs hash-identical. The successor oracle is recorded at a new path (plan 34 discipline).
  3. If the rule changes cells beyond the affected parents, it is not landed. The census is recorded and the verdict is `proven-cause` (the R topology rule is broader). The follow-on is named.
  4. If R lacks exactly the trimmed items (same set), the verdict is `proven-non-deviation`, with the per-item evidence and R's topology. If R lacks a different subset, the priority difference is named as the cause and a fix is attempted under the same gate.
  5. The `>1% BLOCKER` print stays. This plan does not change a threshold.
- **Non-goals:** frame-ceiling changes (131,070 B is a format constant); plan 04 Phases 4–6.

## Decisions

1. Plan number 42. Master direct. Two phases.
2. Phase 1's approach is known. Phase 2's is open (topology rule from R) against the fixed outcome branches.
3. The oracle is `4e6b0de7`, or any later successor in force at execute time (for example from plan 38), named.
4. Sequencing: run after plan 41 Phase 1 if possible, so full-AU encodes are cheaper. Not required.

## Assumption ledger

### Assumption 1

- **Question:** Can windowed encodes reproduce full-AU trim absolutes?
- **Answer chosen:** Yes for L0: the golden window already shows 207 / 227 equal to full-AU. L8 needs a level-8 parent window. Equality of dropped counts is the gate. If it fails, an instrumented full-AU encode under the lock is used instead.
- **Rationale:** Trim is per sub-cell and local to the parent.
- **If wrong:** one full-AU instrumented encode is added (≈ 2 min at current wall).

### Assumption 2

- **Question:** Is the 3-14 Design ruling "known budget" a decision only Cody can reverse?
- **Answer chosen:** No. It was a Design ruling for 3-14 landing scope, and it explicitly opened an expand-to-zero ticket. R parity was never measured.
- **Rationale:** Standing rule; the ruling did not claim R parity.
- **If wrong:** Cody affirms the trim as an accepted deviation. That would need his explicit waiver, and Phase 2 stops after recording Phase 1 evidence.

## Open questions

1. Whether R's parent at L8 uses a different division depth. Phase 1 answers this.

## Phases

### Phase 1: Trimmed items identified and checked against R

- **Outcome:**
  1. Exact trimmed item list (308 + 207 + 227) with identities.
  2. R division topology for each affected parent.
  3. Per-item R presence with a validated match rule.
  4. Verdict per level and kind.
- **Surfaces:** `docs/plans/42-encoder-trim-r-parity/witness/`; read-only encoder with a bounded instrumentation hook (build-flag or debug path, output unchanged), D1.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: Expand-to-zero with confined successor, or proven cause / non-deviation

- **Outcome:**
  - **Either:** trimmed totals 0 with diff confined to the affected parents, R-present items added, K1 0, Perth/goldens/full suite green, successor recorded.
  - **Or:** `proven-cause` / `proven-non-deviation` with evidence.
  - R-G9-3 updated.
- **Surfaces:** `parser/kiwiw/_e2.c` (division/trim tier, R-evidenced rule only); `parser/build_alldata.py` (counters only); `parser/tests/`; plan 42 folder; `residuals.tsv`; OVERVIEW; `docs/provenance.md`.
- **Approach:** open. **Depends on:** Phase 1. **Refine:** skipped.

## Provenance

- Master `b10e787`. Sources:
  - plan 35 `residuals.tsv` R-G9-3;
  - `run_p1.log`;
  - plan 04 IMPLEMENTATION L230–233;
  - `parser/build_alldata.py` L640–652;
  - `_e2.c` `dv_trim`;
  - host read-only `output/scratch-34/G_new/manifest.json`.
- Rejected:
  - accepting "known budget" without R evidence;
  - raising the frame ceiling;
  - removing the BLOCKER print.
- Box draft only.
