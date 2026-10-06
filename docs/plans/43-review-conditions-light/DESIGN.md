---
design_id:
---

# Plan 40 review conditions (light set): 3-14 and 3-17 evidence regenerated or superseded by proof

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's ruling 5 (2026-10-06): for the plan 40 review-condition rows, regenerate the lost evidence where possible. Otherwise each row becomes **superseded-by-proof** (citing a later committed proof that covers the claim) or a **named unverifiable residual**. Design grants no waivers. Oracle `4e6b0de7…`. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py`, at `-j4` or lower. Master direct. Never relabel. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Problem

Plan 40 discharged "review missing" for 3-14 to 3-17 but left 21 condition rows (`triage/phase3_synthesis/residuals.tsv`). This design takes the ones closable by light regeneration or a committed later proof. The completeness-evidence rows go to design 47, and R-G8-4-c goes to design 46.

**Ground (master `6538530`; host read-only 2026-10-06 AEST):**

| Row | Claim (review id) | Lost | Later committed proof or regenerable source |
| --- | --- | --- | --- |
| R-G8-1-b | b4: nine 3-13 CF windows clear target residuals to 0 on the original spool under the 3-14 encoder | `scratch-3-14/windows.*` | Plan 39 `historical_bg/p1/k1_314.json`: HEAD K1 on `4ed9cd80`, background / background_boundary / interior_cover failing **0** over the whole disc (the windows are subsets). The window definitions are committed in `causes_rootcause.md` L60–77 |
| R-G8-1-c | b7: AU K1 S02–S05 = 0, R01 → 0, completeness 776 | `k1_full.json` | `k1_314.json` (background-family 0; completeness 0 under HEAD rule). Old-rule completeness 776 is regenerable: K1 built at `1cf40f8` (plan 39 P1 used it for `k1old_pre311.json`) on `4ed9cd80` |
| R-G8-1-d | b2 + F7: seeded stress test; degenerate / capacity / termination cases | `review_stress.py` (last log a failure) | New tracked test |
| R-G8-1-e | b3: full suite at tip, incl. `test_dump_join_memory` outside a worktree | `pytest_full.log` | Plan 41 suites ran in the worktree `open-pajero-maps-14-completeness` (`runs.json` cwd), which is not "outside a worktree" |
| R-G8-1-h | c2/f1 citation gaps (LOW) | `goldens_changes.json`, `finish_gates.log`, `scratch-3-12/G_build.log` | Golden `l0_divided_trim_halo` sha (905d9c95…, 310,268 B) recordable now |
| R-G8-2-f | 3-15 forced-zero 31 vs 34 | per-row 3-17 bytes; `AU.differing_cells.tsv` never committed | Plan 37 corrected the explanation (34 = O05 30 + O04 4, per row). The remaining part is whether the 3-14 extension's cell list equals the plan 31 list |
| R-G8-4-a | 3-17 S2b/c/e: single-kind projection classify (468 / 308; name_anchor O03 kind-only OK) | `kind_views/`, `classify_kinds/` | Re-run on plan 28's retained 776-row dump (`1a91b1c2…`), with mechanism bytes forced to zero per the plan 31 cell list |
| R-G8-4-b | 3-17 S2a: full-CLI empty-kind abort stderr | `classify.stderr` | Light re-run of the unchanged CLI |

## Solution shape

### Domain: 3-14 conditions

- **Owns:** `triage/independent_reviews/3-14/conditions/` (small JSON plus logs) and a new tracked stress test.
- **Contract:**
  1. **R-G8-1-b → superseded-by-proof.** Cite `k1_314.json` with its disc sha binding. If the report lacks the sha, bind it from plan 39's run log; failing that, re-run the K1, dump off, `-j4`. Per-window "before" tables (pre-3-14 target residual counts per committed window) come from plan 39's keyed per-row arrays (`output/scratch-39/keep/`) if they survive, else from a bounded window K1 on `013586b5`. Reported as context, not required for the after-0 claim.
  2. **R-G8-1-c → regenerated.** K1 built at `1cf40f8` in a throwaway worktree on `4ed9cd80`, dump off, `-j4`, report bound to the disc sha. Required: S02–S05 kinds 0, R01 population 0 (background failing 0) and completeness exactly 776. A different count is named, not passed.
  3. **R-G8-1-d → regenerated.** `parser/tests/test_bg_eo_stress.py` with:
     - a fixed seed, ≥ 1,000 random self-crossing rings against the `bg_shape` probe, checking termination, capacity bounds and valid EO output;
     - explicit degenerate cases (collinear, zero-area, repeated vertices, ring touching the leaf edge), a capacity-overflow case and a guarded `eo_connect` termination case.

     If a case fails, the failure is recorded and becomes a named residual against the encoder (this is a test, not a fix).
  4. **R-G8-1-e → regenerated.** Full `parser/tests` in the main checkout (not a worktree) at master, under the lock. The summary line is quoted, and `test_dump_join_memory` is shown passing.
  5. **R-G8-1-h → regenerated.** Record the current golden sha and size. Each missing citation is replaced by a tracked equivalent where one exists, or dropped with a note.
- **Non-goals:** encoder fixes; re-running the 3-14 encode.

### Domain: 3-17 / 3-15 classify conditions

- **Owns:** `triage/independent_reviews/3-17/conditions/`.
- **Contract:**
  1. **R-G8-4-a → regenerated.** `k1_triage classify` on the retained `1a91b1c2…` completeness dump (sha re-verified; if absent, regenerated with K1 at `1cf40f8` on `4ed9cd80`). Mechanism bytes for rows in the plan 31 changed-cell list are forced to zero; the run covers the completeness-only and name_anchor kind views. The per-row assignment is committed. Required: 468 assigned / 308 unattributed, O01 363 / O04 3 / O05 102, plus name_anchor O03 kind-only `PARTITION OK`.
  2. **R-G8-2-f:** if item 1 reproduces the 3-17 counts exactly and the per-row deltas equal plan 37's 34-row identity, the claim is **superseded-by-proof** (the forced-zero identity is proven with the plan 31 list). The literal equality of the lost `AU.differing_cells.tsv` with the plan 31 list stays a **named unverifiable residual** (the file was never committed). It is non-material only if Cody's rule accepts that. It is listed, not decided here.
  3. **R-G8-4-b → regenerated.** Run the unchanged full CLI on a dump with zero-row kinds and commit its stderr and exit code.
- **Non-goals:** 3-17 reseat; new rules.

## Decisions

1. Plan number 43. Master direct. Two phases. Both approaches known. Refine skipped.
2. Each row's end state is one of {`regenerated`, `superseded-by-proof:<cite>`, `unverifiable:<root cause>`}. It is written into `residuals.tsv` with evidence.
3. R-G8-1-g (depends on 3-15/3-16 conditions) and the completeness rows belong to design 47. R-G8-4-c belongs to design 46. R-G8-1-f (window determinism) belongs to design 45.

## Assumption ledger

### Assumption 1

- **Question:** Does whole-disc K1 failing 0 on `4ed9cd80` supersede the nine-window claim?
- **Answer chosen:** Yes for the claim as stated (target residuals 0 on the original spool under the 3-14 encoder). The windows are subsets of the disc, and the same encoder and spool built it.
- **Rationale:** A later committed proof covers the claim.
- **If wrong:** the nine windows are rebuilt at `d35b565` on the original spool (window builds plus window K1, light), and the result is committed per window.

## Open questions

None blocking.

## Phases

### Phase 1: 3-14 conditions b, c, d, e, h closed

- **Outcome:** each of R-G8-1-b/c/d/e/h is `regenerated`, `superseded-by-proof` or `unverifiable`, with evidence committed and `residuals.tsv` updated. The stress test is tracked, with a perf-inventory entry if a helper is added.
- **Surfaces:** `triage/independent_reviews/3-14/conditions/`; `parser/tests/test_bg_eo_stress.py`; `residuals.tsv`; `docs/provenance.md`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2: 3-17 / 3-15 classify conditions closed

- **Outcome:** R-G8-4-a regenerated (per-row assignment committed); R-G8-4-b regenerated; R-G8-2-f superseded-by-proof plus a named unverifiable part; `residuals.tsv` updated.
- **Surfaces:** `triage/independent_reviews/3-17/conditions/`; `residuals.tsv`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

## Provenance

- Master `6538530`. Sources:
  - `residuals.tsv` rows R-G8-1-b..h, R-G8-2-f, R-G8-4-a/b;
  - `independent_reviews/3-1{4,7}/REVIEW.md`;
  - plan 39 `historical_bg/p1/k1_314.json`, `k1old_pre311.json`;
  - plan 37 erratum;
  - plan 41 `runs.json` (worktree cwd);
  - `causes_rootcause.md` L56–79.
- Box draft only.
