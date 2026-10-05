---
design_id:
---

# Plan-14 Phase 1 per-rule classify recovery

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Recover plan-14 Phase 1 per-rule classify assignments so every one of the 776 rows has a recorded per-rule assignment that joins to its proven 2-01/2-02 cause. Find why they were never recovered (classify exit 2 / other_mechanism missing were noted earlier) and design the recovery. Heavy runs are allowed only under `flock output/.heavy.lock` plus the plan-25 `run_heavy_python.py` memory wrapper with bounded/streamed triage loads; prefer a light path if one exists. Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel.

## Problem

Plan 14 closed Phase 3 at `0ecbb95`. Review fix F1 landed at `0dc5cac`, and the F2 Design ruling (`726092d`) folded dump_row 335 into amended 2-02. Plan 14 was then closed out at `3fb5a35` into the record `docs/plans/14-completeness-root-cause.md`, with its triage evidence moved to `docs/plans/04-c-core-orchestration/triage/` (`e4fd813`). Its accounting partitions the 776 baseline completeness rows by **proven mechanism**: 2-01 **342** + amended 2-02 **434**, 0 open. It never established the Phase 1 **per-rule classify assignment** for those rows. The terminal review records this as **F3**: Phase 1 is *partial*, every assignment is `evidence-gap:other_mechanism`, and no `NO_RULE` or O01/O04/O05 partition is proven.

| Surface (tip `3fb5a35`) | What it shows | Gap |
| --- | --- | --- |
| `docs/plans/04-c-core-orchestration/triage/completeness_evidence.tsv` (plan 14) | 776 rows; `classify_assignment` = `evidence-gap:other_mechanism` for all 776 | No per-rule assignment |
| `docs/plans/04-c-core-orchestration/triage/completeness_evidence.md`; plan 14 record (the 1-01 handoff is summarised there) | Unchanged-rule classify exits **2**: `rule O01: unknown column 'other_mechanism'`. Brief 1-01 step 2 offered (a) recover sides, (b) **recompute reproducibly**, (c) evidence-gap. The worker took (c): "historical experimental mechanism predicates were not reconstructed from rule notes" | (b) was never attempted |
| Plan 14 Phase 2 refine, candidate B (now summarised in `docs/plans/14-completeness-root-cause.md`) | "Recover `other_mechanism` then group only NO_RULE": rejected as a gate | Recovery was never scheduled afterwards |
| Plan 14 record, Review section: F3 / F6 | Phase 1 partial (F3, follow-up). F6 is resolved: the pre-3-03 checker pin `0b19b5e` is recorded in `completeness_evidence.md` | F3 open follow-up |
| `docs/plans/04-c-core-orchestration/triage/rules_other.json` | O01–O06 all key on `other_mechanism` (`==4` O01 checker, `==7` O04 spool, `==5` O05 checker, `==8` O06 build). O02 and O03 are other kinds | The column has **no tracked producer** |
| `…/triage/cause_table.md`, `docs/provenance.md` (scratch-3-07/3-08 entries) | `other_mechanism` = byte 145, joined from `side_completeness.npy` built by **scratch-only** 3-08 audit scripts. Provenance says "Reproduce: 3-07 entry, then the scripts in `output/scratch-3-08/`" | The producer lived only in scratch |
| `parser/tools/k1_triage.py:343–416` | `_load_rules` rejects an unknown column (exit 2). After that, a rule whose `kind` is not in the manifest is also exit 2 | The plan-14 baseline dump manifest declares **only** `completeness`. Even with the column, unchanged `rules_other.json` would next fail on O02 (`interior_cover`) and O03 (`name_anchor`) |
| `parser/tools/dump_join.py` | Tracked windowed join, modes `residual` (byte 146) and `s02` (byte 144) | No `other_mechanism` (byte 145) mode |

**Root cause of the non-recovery (Ground, read-only on the host `codyh-ubuntu`, 2026-10-06 ~04:20 AEST):**

1. **Producer and side tables deleted.** In `open-pajero-maps-3-14/output/`, `scratch-3-07`, `scratch-3-08` and `scratch-3-13` are dangling symlinks into `open-pajero-maps/output/`, where the targets no longer exist. `scratch-3-11/` has no `dump_new_ext/` or `classify_new/`. `scratch-3-12/` holds only plan 17's `extend.py`. `scratch-3-14/` is gone (no 3-14 `dump_ext` with inherited byte 145), and `scratch-3-15/` is absent. Plan 14's own `scratch-14/mechanism_recovery_search.txt` is **0 bytes**.
2. **The column was never reproducible from git.** `rules_other.json` predicates are opaque codes whose only producer was untracked scratch, so tracked provenance overstates it as regenerable.
3. **Plan-14 process.** 1-01 chose fallback (c), and the Phase 2 refine rejected recovery as a gate without scheduling it. Phase 1's literal outcome was never amended (F3).
4. **Manifest shape.** A completeness-only dump cannot take the unprojected `rules_other.json` (unknown-kind exit 2), which 3-17 had already worked around with per-kind rule views.

**What survives and makes a light path possible** (same read-only Ground):
- `output/scratch-14/dump_raw/completeness.bin`: 776 rows × 144 B = 111,744 B. sha256 `1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323` matches the committed pin. This is the pre-3-03 baseline dump on `4ed9cd80…`; its manifest fields end at `dnv`, with no byte 144 or 145.
- `scratch-14/{attribution,complete_repair,cell_local,r_contribution,witnesses}/` per-row proofs.
- `scratch-14/p3/indep/old_dump_311/` (older-disc 739-row dump, checker `0b19b5e`).
- `scratch-3-11/G_new` (`013586b5…`) and `scratch-3-11/extend_dump_new.py` (the inherit script).
- Committed plan-14 TSVs (now under `docs/plans/04-c-core-orchestration/triage/`): `demand_attribution_3-01.tsv` (799 demanders, branch, representability), 2-01/2-02 member tables (source bbox, ncoord, crossings, EO faces, clipped area2, C records), and `phase3_membership.tsv`.

**Predictions on record (inputs to test, never to force):**

| Source | Prediction |
| --- | --- |
| 3-15 recount, 3-14 stitch contract | 776 = O01 **363** + O05 **132** + O04 **7** + unattributed **274**. Shared 687 `{363, 132, 4, 188}`; added 89 `{O04 3, unattributed 86}` |
| 3-17 classify on inherited bytes | O01 363, O04 3, O05 102; unclassified 308. The 31-row gap is 30 O05 + 1 O04 forced to zero on changed cells |
| 3-17 identity table (committed) | All **188** historic keys `NO_RULE` (65535) on this disc |
| Committed cross-tab (computed at Ground) | `neither` 499 = 342 (2-01, R>0) + 156 (2-02, R=0) + 1 (row 335). `historic` 188 all 2-02 (187 R=0, 1 R>0). `added` 89 all 2-02 (R=0) |

Together these predict: rule-assigned rows = all 499 `neither` + 3 added O04. All 342 2-01 rows carry O01/O05/O04. `NO_RULE` = 188 historic + 86 added, all in 2-02.

The ticket is **not** already satisfied on master. It was verified on `origin/master` `0dc5cac85deb3e7d9d919a66742f97aac674bc4f` from committed files plus read-only host listings, then re-checked after rebasing onto `3fb5a35`: F3 is still a follow-up in the plan 14 record. No K1, encode, classify or disc read was run for this design.

## Solution shape

The fix makes `other_mechanism` reproducible from tracked code for completeness rows. With it, the existing classifier assigns per-rule outcomes on the saved 776-row baseline, and those assignments join to plan 14's proven groups. Rule rows whose cause disagrees with plan 14's disposition are discriminated, not relabelled. The shape has three steps:

1. A **tracked** completeness-mechanism producer recomputes the 3-08 predicates under the current build contract.
2. The **unchanged** `k1_triage.py classify` runs on a byte-145 extension of the saved baseline dump, with a **projection** of `rules_other.json` that holds only its completeness rules, verbatim.
3. A per-row join to `phase3_membership.tsv`, with a reconciliation verdict.

No rule, checker, encoder or K1 change. No relabel.

### Domain: completeness mechanism producer

- **Owns:** a tracked, re-runnable computation of `other_mechanism` ∈ {0, 4, 5, 7, 8} for each row of a completeness dump, plus its per-row witness.
- **Contract:**
  1. Predicates are the 3-08 rule definitions as recorded in `cause_table.md` and the `rules_other.json` notes:
     - **4 (O01):** every meeting/demanding source has exact zero bbox width or height, zero area and no interior, and the demand comes from branch (b) deep vertex.
     - **5 (O05):** every demanding source is a well-formed ring (no proper crossings, non-adjacent touches or overlaps) whose builder clip/densify/round gives zero area, and production C emits nothing.
     - **7 (O04):** every demanding source is an identified crossing-closing ring, production C emits nothing, and deleting only the penultimate coordinate removes the crossings and eliminates the required-but-missing mismatch in a direct probe.
     - **8 (O06):** the declared 12-bit class count wraps while physical records include the required type.
     - **0:** none of the above holds.
  2. Evaluation runs under the **current** build contract (the 3-14 stitch production `bg_shape`). The legacy pre-3-14 contract is used only as an optional control (Open question 2).
  3. Demanders are the plan-14 3-01 enumeration (the checker's own `Region` demand set, 799 shapes over 776 keys). A row's code requires the predicate to hold for **all** of its demanders. Mixed-demander rows get 0 unless a single predicate covers every demander.
  4. If more than one predicate holds, `rules_other.json` order decides (first match). Every multi-match row is listed, never silently resolved.
  5. Each row records: native key, code, demander ids, the predicate inputs used (bbox, crossings, area2, C records, probe result), and which path produced it (`light`: committed TSV or saved proof only; `heavy`: bounded spool/C probe).
  6. The producer lives in git (plan folder `triage/` or `parser/tools/`, Execute's choice), never scratch-only. It writes a committed side table keyed on the complete native group key `(level, ix, iy, code, p0..p6, shape, vert)`.
  7. Disc- or spool-touching steps run only through `run_heavy_python.py` (which takes `output/.heavy.lock`), windowed by `--keys` or similar, with no whole-file `ALLDATA.KWI` or spool materialisation.
- **Non-goals:** no new mechanism code (no O07); no change to O01–O06 predicates or causes; no re-derivation of plan-14 group science; no all-kind producer (interior_cover, name_anchor and background kinds stay out).

### Domain: classify on the saved baseline

- **Owns:** a real `k1_triage.py classify` partition of the 776 baseline rows and the per-row assignment array.
- **Contract:**
  1. Input is the saved pre-3-03 baseline dump (sha256 `1a91b1c2…`, checked before use). The 3-03 checker removed these rows from live K1, so re-running K1 at HEAD cannot regenerate the baseline. If the dump has to be regenerated, use checker pin `0b19b5e` in an isolated scratch destination (F6), and the regenerated `.bin` must re-hash to `1a91b1c2…`.
  2. Byte 145 `other_mechanism` (u8) is written by a tracked windowed join, indicatively a new `dump_join.py` mode under plan-05 bounded-I/O rules. The manifest gains the field; the original 144 bytes of every row are verified unchanged. Byte 144 (`s02_producer_verified`) stays zero, since completeness is out of S02 scope.
  3. The rules input is a **completeness projection** of `rules_other.json`: O01, O04, O05, O06 with id, cause, kind, `where` and order byte-for-byte equal to the source. The projection is generated by a tracked step that records both file hashes, and is not hand-edited.
  4. `classify` code is unchanged. Exit 1 / `PARTITION FAIL` with `NO_RULE` rows is a valid recorded outcome, not an error to work around.
  5. The committed per-row TSV has 776 rows: full native key, `dump_row`, assigned rule id or `NO_RULE`, rule cause, plus counts per rule.
- **Non-goals:** no K1 re-run as acceptance; no live classify (the live completeness dump is empty after 3-03); no catch-all rule.

### Domain: join and cause reconciliation

- **Owns:** the per-row join of per-rule assignment to plan-14 proven cause, and a verdict for every row.
- **Contract:**
  1. The join is on full native key against tip `docs/plans/04-c-core-orchestration/triage/phase3_membership.tsv`. The join target is master's accounting: **342 (2-01) + 434 (amended 2-02, including 765 and 335 by Design rulings), 0 open**.
  2. Each row carries: rule id and cause; plan-14 group; plan-14 disposition (3-03 checker); proof references (3-01 demander verdict, 2-01 / 2-02 / 3-02 proof path); R presence (Phase 1 evidence plus cell-local verdict); and a verdict.
  3. Verdict is `consistent`, `conflict-proven` or `conflict-open`:
     - **`consistent`:** rule cause `checker` (O01/O05) with plan-14 checker disposition, or `NO_RULE` with a plan-14 proven group. The row's cause is that group's proof; no new rule is registered.
     - **`conflict-proven`:** the rule cause is `spool` (O04) or `build` (O06) while plan 14 disposed the row as checker, **and** a bounded discriminator settles how both hold. Example: the spool ring is defective, and under the current contract the repaired ring does or does not yield a representable piece. The result is recorded together with R presence.
     - **`conflict-open`:** no discriminator settled it. The row is named with the discriminators tried.
  4. A spool-caused row stays a spool item for plan 04's successor list. It is never absorbed into checker by label.
- **Non-goals:**
  - The 2-01 source-data parity observation (R emits 288 where the spool holds no representable 288 source) stays a separately carried Design observation. This plan only labels which rule rows sit in it.
  - No rewrite of plan 14's Phase 1 TSV history.
  - No plan 04 Phase 3 close.

## Decisions

1. Plan number **28**. Master occupies 01–05 and 07–27. **06** is not a work unit. 29 is drafted alongside for the K1 name_anchor ticket.
2. Land on master directly. No feature branch. No pull request.
3. Two phases. Refine is skipped for Phase 1's light path; the producer predicates are already documented. Phase 2 is known once Phase 1's assignments exist. One worker may carry both sequentially.
4. **Recompute, not recover.** The side tables and producer are physically gone. Recomputing from documented predicates with tracked code is the only reproducible path. A recomputed code is a fresh measurement against stated predicates, not a restoration of 3-08 bytes, and the record says so.
5. **Light path first.** Derive each row's code from committed plan-14 TSVs and saved `scratch-14` proofs where those already decide the predicate. Only undecided rows go to a bounded heavy probe under `run_heavy_python.py`, which takes `output/.heavy.lock`. Each row records its path.
6. `NO_RULE` is a valid recorded per-rule assignment. Its cause is the joined plan-14 proof. No O07 or other rule is registered here.
7. Do not reseat 170, 3-16 or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not claim plan 04 Phase 3 closed. No 3-90 re-run, no full-AU encode, and no K1 re-run as acceptance.
8. Predictions (3-15, 3-17, cross-tab) are tested yardsticks. A mismatch is reported per row with its discriminator, never forced to match.

## Assumption ledger

### Assumption 1

- **Question:** Can the original 3-08 side tables be recovered anywhere?
- **Answer chosen:** No. They are gone on the host (dangling symlinks, absent dirs, 0-byte recovery search), so the plan recomputes. If Execute nevertheless finds an intact `side_completeness.npy` or 3-14 `dump_ext` with sha provenance, it is used **only** as a cross-check control on the unchanged cells, not as the assignment source.
- **Rationale:** Ground listing above; brief 1-01 option (b) is the reproducible route.
- **If wrong:** A recovered table becomes an extra per-row control column. Phase outcomes are unchanged.

### Assumption 2

- **Question:** Which build contract do the predicates run under?
- **Answer chosen:** The current one (the 3-14 stitch, production `bg_shape` built from the tip `_cenc.c`, which 3-03 and F1 did not change). The disc in force is still `4ed9cd80…`.
- **Rationale:** 3-15 already showed inherited bytes go stale on changed cells. The assignment must describe the disc in force.
- **If wrong:** Cody wants 3-08-era (legacy-contract) codes. A legacy-contract run on `old_dump_311` becomes the primary output for those rows, and current-contract codes become a second column.

### Assumption 3

- **Question:** Should the 274-ish `NO_RULE` rows get a new rule so the partition reads OK?
- **Answer chosen:** No. `NO_RULE` plus a joined plan-14 proof is the honest record. Registering a rule is a separate rules decision with its own reproducer gate (3-15 refused O07 for the same reason).
- **Rationale:** Never relabel. Plan 14 Phase 3 left `rules_*.json` untouched by design.
- **If wrong:** A later design registers a rule from plan-14 proofs. This plan's join table is its input.

### Assumption 4

- **Question:** May the producer use plan-14 3-01's demander set as "meeting sources"?
- **Answer chosen:** Yes, as the demanding-source set for the O01/O04/O05 predicates. Rows whose 3-08 definition needs non-demanding meeting sources (the all-source required-cell audit) are flagged, and those sources are enumerated in the bounded heavy probe.
- **Rationale:** 3-01 derives from the checker's own `Region` (799 demanders, branches a 1 / b 797 / c 1). 3-08's "meeting sources" were the sources driving the requirement.
- **If wrong:** More rows take the heavy path. The outcome is unchanged.

### Assumption 5

- **Question:** Does Phase 2 rewrite plan 14's committed Phase 1 TSV or close plan 14?
- **Answer chosen:** No to both:
  - Plan 28's TSVs are the recorded assignments. Plan 14 is closed out, so its record `docs/plans/14-completeness-root-cause.md` gets an appended F3 resolution pointing at them, as an addition to its Review/Follow-ups only, with no rewrite of existing text.
  - The Phase 1 history stays as written.
- **Rationale:** Preserve history. F2 is already ruled and landed (`726092d`).
- **If wrong:** Design wants the F3 pointer elsewhere. No content change.

### Assumption 6

- **Question:** Does landing this clear OVERVIEW's "native classify joins" and "historic completeness attribution" blockers?
- **Answer chosen:** Only for the completeness kind and only to the extent recorded. OVERVIEW wording narrows to say completeness per-rule assignments are recovered and joined, and names any `conflict-open` rows. Other kinds' native joins stay open, and plan 04 Phase 3 stays open.
- **Rationale:** Standing rule; don't over-claim.
- **If wrong:** Cody keeps the bullets verbatim until 3-90. No phase change.

## Open questions

1. Exact producer home (plan folder `triage/` vs `parser/tools/`) and dump-join form (new `dump_join.py` mode vs a plan-folder script reusing `dump_io`). **Execute chooses**; tracked either way.
2. Whether to run the legacy-contract control: recompute on `old_dump_311` (739 rows) and reproduce 3-15's legacy recount O01 363 / O05 132 / O04 56 / unattributed 188. It is optional, because it needs a pre-3-14 `bg_shape` build. If skipped, the record says so, and the per-row identity controls (188 and 89) carry validation.
3. Where a recomputed code contradicts a 3-17 inherited-byte count on unchanged cells (e.g. O01 ≠ 363), which side is wrong? **Phase 1 answers per row** with the predicate inputs. Nothing is forced.

## Phases

### Phase 1: Every baseline row has a reproducible per-rule classify assignment

- **Outcome:**
  1. A committed note states why Phase 1 assignments were never recovered: deleted scratch producer and side tables (with the paths found absent), the untracked column producer, 1-01 fallback (c), and the unknown-kind manifest shape. `docs/provenance.md`'s scratch-3-07/3-08 entries are corrected to say those artefacts are deleted, not regenerable.
  2. A tracked producer emits a committed 776-row side table: full native key, `other_mechanism` code, demander ids, predicate inputs, and `light`/`heavy` path.
  3. A byte-145 extension of the baseline dump is built. The source is verified first at sha256 `1a91b1c2…`, and all original bytes are verified unchanged afterwards.
  4. Unchanged `k1_triage.py classify` runs with a hash-recorded completeness projection of `rules_other.json`. It produces a committed 776-row per-rule assignment TSV (rule id or `NO_RULE`, cause) with per-rule counts. No row is `evidence-gap`.
  5. The controls are stated with pass/fail:
     - all 188 historic keys `NO_RULE`;
     - the 89 added keys split O04 3 / `NO_RULE` 86;
     - totals compared against 3-15 (363 / 132 / 7 / 274) and against 3-17 (363 / 3 / 102 / 308, explained by the 31 forced-zero rows).
     Every mismatching row is listed with its predicate inputs, not forced.
  6. Heavy steps ran only through `run_heavy_python.py`, which takes `output/.heavy.lock`, with argv and `memory.peak` logs under the plan scratch.
  7. Not done here: no rule, checker, encoder or K1 edits; no K1 re-run; no full-AU encode; 170 / 3-16 / 3-17 untouched.
- **Surfaces:**
  - new `docs/plans/28-phase1-per-rule-classify-recovery/` (note, producer, side table TSV, assignment TSV);
  - optional new mode in `parser/tools/dump_join.py` with a fixture test under `parser/tests/`;
  - `docs/provenance.md` (scratch entries);
  - read-only: `parser/tools/k1_triage.py`, `rules_other.json`, plan-14 TSVs in `docs/plans/04-c-core-orchestration/triage/`, `output/scratch-14/` proofs and dump, `parser/kiwiw/` production `bg_shape` / `cenc.py`.
- **Approach:** known. Light path first; heavy probe only for undecided rows.
- **Depends on:** master at or after `3fb5a35`, and the saved `output/scratch-14/dump_raw` (or a `0b19b5e`-pinned regeneration that re-hashes equal).
- **Refine:** skipped.

### Phase 2: Every assignment joins to its proven plan-14 cause, with conflicts discriminated

- **Outcome:**
  1. A committed 776-row join TSV pairs each row's per-rule assignment and rule cause with:
     - its tip `phase3_membership.tsv` group;
     - plan-14 disposition and proof references;
     - R presence;
     - a verdict: `consistent`, `conflict-proven` or `conflict-open`.
  2. Counts per (rule × group × verdict) are stated, and the cross-tab predictions are tested against them (e.g. all 342 2-01 rows rule-assigned; `NO_RULE` ⊆ 2-02).
  3. Every O04 (spool) or O06 (build) row has a bounded discriminator record:
     - the repair counterfactual under the current contract, and whether it yields a representable piece;
     - R presence;
     - the verdict.
     Spool-caused rows are named for plan 04's successor spool list, not relabelled checker.
  4. Row 335 is in amended 2-02 per the F2 ruling. Its distinct trigger is recorded: the TOL-only centre hit of a type-288 sliver.
  5. The plan 14 record `docs/plans/14-completeness-root-cause.md` gets an appended F3 resolution citing these TSVs.
  6. OVERVIEW narrows the completeness portion of "native classify joins / historic completeness attribution" per Assumption 6.
  7. The 2-01 source-data parity observation stays carried and is not absorbed.
  8. Not done here: no Phase 3 close; no plan 04 phases 4–6 or plan 06; no 3-90 re-run; 170 / 3-16 / 3-17 not reseated.
- **Surfaces:**
  - plan-28 folder (join TSV, reconciliation note);
  - append-only addition to `docs/plans/14-completeness-root-cause.md` (F3 resolution);
  - `docs/OVERVIEW.md` blocker sentence;
  - read-only: plan-14 TSVs and proofs, `rules_other.json`. A bounded discriminator probe via `run_heavy_python.py` only if needed.
- **Approach:** known.
- **Depends on:** Phase 1.
- **Refine:** skipped.

## Provenance

- Ground tip read: `origin/master` `0dc5cac85deb3e7d9d919a66742f97aac674bc4f` ("K1 completeness representability: full EO topology (plan 14 remediation-01, review F1)"). The box checkout `/workspace/open-pajero-maps` was fast-forwarded from `df1f071`.
- **Rebased by Execute onto `3fb5a35` (2026-10-06):**
  - the F2 ruling landed (`726092d`), so `phase3_membership.tsv` is 342 + 434, 0 open;
  - F6 was pinned (`593c504`);
  - triage moved to `docs/plans/04-c-core-orchestration/triage/` (`e4fd813`);
  - plan 14 was collapsed to `docs/plans/14-completeness-root-cause.md` (`3fb5a35`).
  At draft time (`0dc5cac`), plan 14 was not closed out and membership was 342 + 433 + 1.
- Evidence cited (committed):
  - (draft time; since collapsed into the plan 14 record) plan 14 `DESIGN.md`, `IMPLEMENTATION.md`, `REVIEW.md` (F3, F6), `triage/completeness_evidence.{md,tsv}`, `reports/1-01-evidence-table.md`, `briefs/1-01-evidence-table.md` step 2, `phase3_membership.tsv`, `demand_attribution_3-01.tsv`, 2-01/2-02 member TSVs;
  - plan 04 `triage/{rules_other.json, cause_table.md, completeness_3-15_cell_local.md, rebaseline_3-17_9064.md, review_3-08.md}`;
  - `docs/provenance.md` scratch-3-07/3-08 entries;
  - `parser/tools/{k1_triage.py, dump_join.py, run_heavy_python.py}`;
  - plan 17 record;
  - plan 25 design.
- Read-only host Ground on `codyh-ubuntu` (directory listings, one sha256 of the 111,744-byte baseline dump, two small JSON reads; no K1 / classify / encode / disc reads):
  - dangling `scratch-3-07`/`3-08`/`3-13` symlinks; absent 3-11 `dump_new_ext` / `classify_new`, 3-12 `dump_ext`, 3-14 scratch, 3-15 scratch;
  - `mechanism_recovery_search.txt` 0 bytes;
  - surviving `scratch-14/dump_raw` (sha matches pin), proofs, `p3/indep/old_dump_311`;
  - `classify_invocation.json` exit 2 `rule O01: unknown column 'other_mechanism'`.
- The host main checkout sits at `bbd1571`; plan-14 work ran in `open-pajero-maps-14-completeness`.
- `scratch-14/dump_ext/` and `classify_invocation.json` carry mtime 2026-10-06 04:10 AEST. Cause: Execute's `--help` smoke test during plan 14 close-out ran `build_evidence.py`/`verify_evidence.py` (recorded in `docs/provenance.md`). The content was verified equivalent at the time: `dump_ext` is byte-identical to `dump_raw`, and the audit is PASS. Execute re-verifies hashes before any use.
- Rejected for this design:
  - fabricating mechanism bytes;
  - treating 3-15/3-17 counts as assignments;
  - registering O07 or any rule;
  - re-running K1 at HEAD to rebuild the baseline;
  - full-AU encode;
  - editing O01–O06 predicates;
  - ruling on 335;
  - absorbing the 2-01 source-data parity observation;
  - reseating 170 / 3-16 / 3-17;
  - plan 04 phases 4–6 or plan 06;
  - Phase 3 close;
  - a 3-90 re-run.
- Draft format followed: `/workspace/maps-design-drafts/27-independent-fix-review-truncated-pins/DESIGN.md`.
- Design method: the workflow design skill (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger).
- The adversarial pass ran in-context, not in a clean context; that is disclosed. It applied two findings: the manifest unknown-kind trap (hence the rules projection) and the O04 spool-vs-checker conflict (hence the Phase 2 verdicts).
- Workflow-service posts and `artifact_feedback` were skipped under the user instruction. Box draft only: no commit or push.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
