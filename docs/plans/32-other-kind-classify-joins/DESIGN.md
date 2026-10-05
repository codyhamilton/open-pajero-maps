---
design_id:
---

# Other-kind native classify joins

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Discharge the OVERVIEW blocker "other kinds' native classify joins": for every non-completeness classify kind (`interior_cover`, `name_anchor`, `background`, `background_boundary`), produce a recorded per-rule assignment that joins to proven causes for every failing or historical row — or prove that the failing set is empty on the successor disc in force. Model the recovery path on plan 28 (tracked mechanism producer → dump_join → kind-projected classify → join to proven causes). Completeness is already closed by plan 28; do not reseat it. Heavy work only under `flock output/.heavy.lock` plus `run_heavy_python.py` with bounded/streamed loads (plan 25). Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4–6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel. Skip plan 29 close-out (Execute). Do not draft PSS / Phase 3 close synthesis here (depends on plans 31 and 32).

## Problem

Plan 28 recovered per-rule classify assignments for **completeness only**. OVERVIEW still lists "other kinds' native classify joins" as a Phase 3 blocker. Plan 31 (oracle + pin gates) and plan 30 (2-01 parity) are handed to Execute; this unit is the remaining joins slice before a PSS + Phase 3 close synthesis design.

| Surface (tip `5ff9eb0`) | What it shows | Gap |
| --- | --- | --- |
| OVERVIEW | "other kinds' native classify joins" still open | Completeness joins do not clear it |
| Plan 28 | Completeness projection of `rules_other.json`; O02/O03 deliberately excluded (unknown-kind on completeness-only dump) | interior_cover / name_anchor never classified under plan 28 |
| `rules_other.json` | O02 `interior_cover` (`other_mechanism==1`); O03 `name_anchor` (`other_mechanism==6`) | Same missing-column class as pre-28 completeness; producers were scratch `side_interior_cover.npy` / `side_name_anchor.npy` |
| `rules_bg.json` | R01 `background` (`in_eo_same==1`); S02+ `background_boundary` (`s02_producer_verified` / residual fields) | `dump_join` has `s02` and `residual` modes; live reproducible classify+join on successor not recorded as a Phase 3 gate artefact |
| Plan 29 successor compare | On `2ee3456a…`, failing **0** for background, background_boundary, interior_cover, name_anchor (name_anchor was 1→0) | Live empty set is evidenced in plan-29 witnesses but not promoted as the joins-blocker discharge |
| Cause tables (3-07–3-13) | Historical attributions exist (O02 821, O03 1, R01 ~920k, S02 ~1.9M, large unattributed boundary residual) | Side tables / dumps largely scratch-deleted (same class of loss as plan 28 Assumption 1); mega historical recompute is not required if live empty is accepted as the close-gate discharge |

**Ground:**

1. Disc in force: successor `2ee3456a9aeb…e6ae`. Plan 29 close-out not yet collapsed on tip.
2. Live K1 failing on successor is 0 for all in-scope kinds (plan-29 `successor_k1_compare.json`).
3. Plan 28 pattern to reuse: tracked producer → `dump_join` extension → kind projection of rules → unchanged `k1_triage.py classify` → join/reconcile TSV; `NO_RULE` valid; predictions as yardsticks; never relabel; light path first.
4. `dump_join.py` already modes: `residual`, `s02`, `other_mechanism` (completeness-only). Interior_cover/name_anchor need `other_mechanism` on *their* kind dumps (or an equivalent tracked join), not the completeness projection.

The ticket is **not** already satisfied: OVERVIEW still names the blocker; no committed per-kind empty-dump or assignment artefact discharges it for the successor.

## Solution shape

Mirror plan 28, scoped to non-completeness kinds. Prefer the **live-empty** discharge on the successor when it holds. Only if a kind has live failing rows, run the full producer→join→classify→reconcile path for those rows. Historical mega-dumps (millions of boundary rows) are not re-materialised unless live failing is non-zero or Cody requires historical set-equality as a separate residual.

### Domain: live failing census on the successor

- **Owns:** a committed per-kind proof that the successor disc's failing dump for each in-scope kind has row count 0 (or the exact non-zero count and native-key list).
- **Contract:**
  1. In-scope kinds: **`interior_cover`**, **`name_anchor`**, **`background`**, **`background_boundary`**. Completeness out of scope (plan 28). Point kinds (`range`, `step`, `road_node`, `road_point`) out of scope unless a dump unexpectedly shows failing &gt; 0 — then name them as carry.
  2. Measurement on disc `2ee3456a…` under `run_heavy_python.py` + lock: K1 `--dump-failures` (or equivalent bounded dump) at ops ≤`-j6`, kinds restricted to in-scope set; record per-kind row counts, dump dir sha/manifest, and peak memory.
  3. Citing plan-29 compare alone is allowed as a **control**, not as the sole discharge: Phase 1 must produce a fresh dump-row census (or a byte-identical re-read of a retained successor dump if one exists and re-hashes).
  4. Outcome branch:
     - **All in-scope kinds row count 0:** live-empty path; Phase 2 records the empty assignment tables and joins to proven dispositions (plan 29 for O03; cause-table / 3-14 for R01 clearance; O02/S02 historical notes as carried, not re-labelled).
     - **Any kind non-zero:** recovery path for that kind only (Domain: plan-28-style recovery).
  5. Protected discs (`2ee3456a…`, `4ed9cd80…`, `013586b5…`) stay byte-untouched except read.
- **Non-goals:** no full multi-kind historical dump of the 3-11-era millions; no PSS trio; no Phase 3 close; no completeness reseat.

### Domain: plan-28-style recovery (non-empty kinds only)

- **Owns:** tracked mechanism production, dump extension, kind-projected classify, and join to proven causes for every live failing row of a non-empty kind.
- **Contract:**
  1. **Producer (recompute, not recover):** documented predicates from `rules_other.json` / `rules_bg.json` notes and cause tables — e.g. O02 code 1 (interior_cover crossing-closing producer), O03 code 6 (name_anchor out-of-span; expect 0 on successor after plan 29), R01 `in_eo_same`, S02 `s02_producer_verified`. Fresh measurement under current contract; not restoration of deleted 3-08 bytes.
  2. **Join:** reuse or extend `dump_join.py` (new mode only if needed; prefer existing `other_mechanism` / `s02` / `residual`). Read-only on inputs; refuse path/symlink/hardlink aliases (plan 28 F1).
  3. **Rules projection:** per-kind projection of the relevant rules file with raw rule objects byte-preserved and hashes recorded (same discipline as plan 28 completeness projection). Never hand-edit projections.
  4. **Classify:** unchanged `k1_triage.py classify`. Exit 1 / `PARTITION FAIL` with `NO_RULE` is a valid recorded outcome. Exit 2 (unknown column/kind) is a defect to fix in the producer/projection, not an evidence-gap label.
  5. **Reconcile:** each row joins a proven cause reference (rule cause + cause_table / plan-29 / 3-13 disposition). Verdicts: `consistent` | `conflict-proven` | `conflict-open`. Target 0 conflict-open; spool causes stay spool.
  6. Windowed/streamed loads only; no whole-file disc/spool materialisation.
- **Non-goals:** no new catch-all rules; no tolerance changes; no inventing pins for historical 26,650 groups (plan 31 owns pin disposition).

### Domain: empty-set discharge and OVERVIEW narrowing

- **Owns:** the committed artefacts that clear (or residual) the OVERVIEW bullet, without claiming Phase 3 closed.
- **Contract:**
  1. Per kind: either `live_empty` with dump census + empty assignment stub, or `assigned` with plan-28 artefacts and reconcile TSV.
  2. Historical attributions (O02, O03 pre-29, R01, S02, unattributed boundary remainder) remain cited as science records; they are **not** silently declared live failures.
  3. OVERVIEW narrows "other kinds' native classify joins" to discharged or to an exact named residual (kind + count + why). PSS and Phase 3 close stay open.
  4. Optional lasting note under `docs/design/` only if a reusable contract appears (Execute chooses; not required for phase close).
- **Non-goals:** no plan 04 P4–6; no 3-90; no PSS synthesis design in this folder.

## Decisions

1. Plan number **32**. Land on master directly. No feature branch. No pull request.
2. Two phases. Phase 1 approach **known**. Phase 2 approach **known** for the live-empty branch; **open** only if a kind is non-empty (discriminator/producer shape under divergent candidates against the fixed reconcile outcome). Refine skipped.
3. Completeness stays plan 28's. This plan never reopens completeness assignments.
4. Live-empty on successor is a first-class discharge of the joins blocker for Phase 3 close readiness — matching the user "or proof that the set is empty" clause. Historical mega reclassify is out of default scope.
5. name_anchor: expect live empty after plan 29; disposition cites plan 29 verdict A / successor drop. Do not reseat plan 29.
6. Heavy work only under `run_heavy_python.py` + lock (plan 25). Prefer light paths.
7. Do not reseat 170 / 3-16 / 3-17. Do not draw P4–6 or plan 06. Do not claim Phase 3 closed. No 3-90 re-run. Skip plan 29 close-out. Do not draft PSS + close synthesis here.

## Assumption ledger

### Assumption 1

- **Question:** Does live failing 0 on successor discharge "other kinds' native classify joins" without recovering historical side tables?
- **Answer chosen:** Yes for the Phase 3 close-gate meaning of the OVERVIEW bullet: native joins are vacuously satisfied on an empty failing dump, with committed empty census artefacts. Historical cause_table science stays carried, not deleted.
- **Rationale:** User allows empty-set proof; plan 29 already cleared live name_anchor; other kinds already 0 failing on successor compare.
- **If wrong:** Cody requires historical per-row assignments for pre-fix dumps. Phase 2 expands to bounded historical recovery per kind (likely a follow-on design for background_boundary scale).

### Assumption 2

- **Question:** Are `range` / `step` / `road_*` in scope?
- **Answer chosen:** No, unless Phase 1 dump shows failing &gt; 0 (then carry into Phase 2 with a named residual or assignment).
- **Rationale:** OVERVIEW "other kinds" in context of classify joins / rules_other|rules_bg mechanism columns; point kinds have not been the joins blocker.
- **If wrong:** Add them to the census table as explicit `out_of_scope_zero` rows.

### Assumption 3

- **Question:** May Phase 1 rely solely on plan-29 `successor_k1_compare.json` without a fresh dump?
- **Answer chosen:** No — fresh dump census (or re-hash of a retained successor dump under the wrapper) is required. Plan-29 compare is a control.
- **Rationale:** Standing rule; joins blocker needs an artefact owned by this plan.
- **If wrong:** Cody accepts plan-29 compare as sufficient — Phase 1 still writes a pointer artefact with hashes.

### Assumption 4

- **Question:** Does this plan close Phase 3 when joins discharge?
- **Answer chosen:** No. PSS + close synthesis remains a separate candidate after 31 and 32.
- **Rationale:** User instruction; NEXT-CANDIDATES.
- **If wrong:** A later design's outcome is exactly Phase 3 close with evidence.

## Open questions

1. Whether a retained successor multi-kind dump already exists under `output/scratch-29/` — Execute inventories before scheduling a new K1 dump.
2. If any kind is non-empty, exact producer home (`parser/tools/` vs plan-folder triage) — Execute chooses; must be tracked.
3. Whether to promote a short `docs/design/` note on multi-kind classify projections — optional.

## Phases

### Phase 1: Every in-scope kind has a successor failing-dump census (0 or exact keys)

- **Outcome:**
  1. Committed per-kind census TSV/JSON: kind, failing row count on `2ee3456a…`, dump path + manifest/bin hashes, run log under `run_heavy_python.py` (argv, `memory.peak`, workers ≤6).
  2. In-scope kinds listed: interior_cover, name_anchor, background, background_boundary. Completeness explicitly excluded with pointer to plan 28.
  3. Branch flag recorded: `all_live_empty` **or** `nonempty_kinds=[…]` with native-key lists / dump row ids for each non-empty kind.
  4. Plan-29 compare cited as control (pass/fail match on failing counts).
  5. Not done: no classify recovery yet; no OVERVIEW claim of full blocker clear; no PSS; no Phase 3 close.
- **Surfaces:** `docs/plans/32-other-kind-classify-joins/` (census + note); read-only successor disc, plan-29 witnesses; `parser/tools/quantisation_roundtrip.py` dump path via wrapper.
- **Approach:** known.
- **Depends on:** tip ≥ `5ff9eb0`; successor disc retained.
- **Refine:** skipped.

### Phase 2: Per-kind discharge — empty assignment artefacts, or plan-28-style assign+join for non-empty kinds

- **Outcome:**
  1. **If `all_live_empty`:** for each in-scope kind, a committed empty assignment artefact (0-row TSV or classify-on-empty record with PARTITION OK / exit documented) plus a disposition note joining to proven causes for the historical story (name_anchor→plan 29; interior_cover→O02 cause_table; background→R01/3-14 clearance; background_boundary→S02/residual carried, unattributed remainder named — never relabelled live-failing).
  2. **If any kind non-empty:** for each such kind, plan-28 pipeline artefacts: mechanism side table, dump_join extension, rules projection+hashes, classify assignment TSV, reconcile TSV with verdicts; 0 conflict-open or named opens.
  3. OVERVIEW "other kinds' native classify joins" narrowed to discharged or exact residual (kind, count, reason).
  4. Explicit: plan 04 Phase 3 **not** closed; PSS + close synthesis remain; plan 31 gates separate.
  5. Not done: no 3-90; no P4–6; 170 / 3-16 / 3-17 not reseated; no inventing historical 16M-row assignments.
- **Surfaces:** plan-32 folder; optional `dump_join.py` mode + tests; `docs/OVERVIEW.md`; read-only rules JSON, cause tables, plan 28/29 records.
- **Approach:** known for empty branch; open for nonempty recovery producers.
- **Depends on:** Phase 1.
- **Refine:** skipped.

## Provenance

- Ground tip: `origin/master` `5ff9eb0759c0dc2b38f9167682d99435cbd66fb7` (fetch already up to date). Plan 29 folder still present (close-out pending).
- Evidence cited: OVERVIEW other-kind joins bullet; plan 28 record (completeness-only; O02/O03 excluded); `rules_other.json` O02/O03; `rules_bg.json` R01/S02; `dump_join.py` modes; plan 29 successor compare (live failing 0); cause_table / causes_residual historical counts; draft 31 split note; plan 25 memory guards.
- Rejected: reseating completeness; inventing historical mega assignments; claiming Phase 3 closed; 3-90 re-run; P4–6 / plan 06; drafting PSS+close here; reseating 170 / 3-16 / 3-17; plan 29 close-out work.
- Draft format followed: `/workspace/maps-design-drafts/28-phase1-per-rule-classify-recovery/DESIGN.md` and `/workspace/maps-design-drafts/31-phase3-oracle-and-pin-gates/DESIGN.md`.
- Design method: workflow design skill; headless assumption ledger.
- Adversarial pass in-context (disclosed): (1) empty live set is valid discharge per user OR-clause; (2) must not pretend plan-29 compare alone is enough without a plan-owned census; (3) background_boundary historical scale must not be default scope; (4) completeness stays sealed under plan 28.
- Workflow-service / `artifact_feedback` skipped. Box draft only: no commit or push.
