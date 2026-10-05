# Implementation — 28 Phase 1 per-rule classify recovery

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` and makes the commits.
- Session: plan 28 Execute (Phases 1–2, terminal review, close-out)
- Started: 2026-10-06 ~04:17 Australia/Brisbane
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached, pushes fast-forward to `master`); DESIGN landed at `fe18160`.
- Scratch: `output/scratch-28/` (run logs under `output/scratch-28/runs/`).

## Input checks (before any use)

- `output/scratch-14/dump_raw/completeness.bin`: sha256 `1a91b1c26e474b2c689fef9811b73878a4ead144db97eea3aaf6f442ed30d323`, 111,744 B. **Matches** the pin in `docs/plans/04-c-core-orchestration/triage/completeness_evidence.md`.
- `output/scratch-14/dump_ext/completeness.bin` (mtime 04:10, operator slip): sha256 `1a91b1c2…`. **Byte-identical** to `dump_raw`, as the recorded original was. Its manifest is `28fa57f1…`, which is the gap-annotated manifest the evidence builder rewrites deterministically; no committed hash pin exists for it. Plan 28 does not read `dump_ext`; its source is `dump_raw` (manifest `90f45ef2…`, unchanged since 2026-10-05 23:19).
- `output/scratch-14/classify_invocation.json` (mtime 04:10): sha256 `09b64658…`. No committed hash pin exists. Content: argv `k1_triage.py classify --dump output/scratch-14/dump_ext --rules docs/plans/04-c-core-orchestration/triage/rules_other.json`, exit 2, which matches the recorded outcome. Plan 28 uses it only as a historical reference, never as input.

## Phase 1 — Every baseline row has a reproducible per-rule classify assignment

Refine skipped (DESIGN). One unit, with its brief authored inline: `briefs/1-01-mechanism-producer-classify.md`.

### 1-01 — completeness mechanism producer, byte-145 dump and classify

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 04:19–04:33. 153,411 tokens; the harness reports no turn count. Report: `reports/1-01-mechanism-producer-classify.md`. Status: `done with concerns`.
- **Built:**
  - tracked producer `triage/completeness_mechanism.py` (`produce` / `projection` / `publish`);
  - new `parser/tools/dump_join.py --mode other_mechanism` with `parser/tests/test_dump_join_other_mechanism.py` (14 new cases);
  - `phase1_note.md` (why the codes were never recovered);
  - `docs/provenance.md` scratch-3-07/3-08 corrections and a scratch-28 entry.
- **Full runs (Execute, under `run_heavy_python.py`, 04:35, `output/scratch-28/run_p1.{sh,log}`):** produce 0 (57 s, peak 81 MB) → projection 0 → dump-join 0 → classify **1** (`PARTITION FAIL`, valid) → publish 0. `dump_raw` re-hashed `1a91b1c2…` before and after.
- **Result:**
  - `triage/completeness_mechanism.tsv`: 776 rows, all on the `light` path. Codes 4: 363, 5: 132, 7: 7, 8: 0, 0: 274; no multi-match.
  - `triage/classify_assignment.tsv`: 776 rows, **O01 363 / O05 132 / O04 7 / O06 0 / NO_RULE 274**, no evidence gap.
  - Projection `triage/rules_completeness_projection.json` with `projection_hashes.json`.
  - Generated `triage/phase1_controls.md`.
- **Controls:**
  - historic 188: all `NO_RULE`, PASS;
  - added 89: O04 3 / NO_RULE 86, PASS;
  - 3-15 totals (363/132/7/274): PASS, exact;
  - 3-17 inherited-byte totals (O04 3, O05 102, NO_RULE 308): aggregate FAIL, as the DESIGN expects for inherited bytes. Per-row identity is unrecoverable because the 3-17 byte table is deleted, so the bucket members are listed as candidates.
  - Legacy-contract control (Open question 2): skipped, as allowed.
- **Deviations:**
  - The worker's windowed (≤25-row) development runs used plain light invocations in the sandbox, which read no spool or disc. All full runs went through the guard.
  - O06 is excluded by a pinned-encoder contract proof (`_cenc.c` `5c43e00d…`: classes split into units ≤ 4095, so no wrap), not by a per-cell physical count.
- **Contradiction reported (DESIGN arithmetic):** the 3-15 → 3-17 delta is 34 rows (O05 −30, O04 −4), but the DESIGN's explanation names 31 forced-zero rows (30 + 1). Three rows remain unexplained by that sentence. No count is forced. Carried to Phase 2 and the record.
- **Surfaces:** as listed above; `k1_triage.py`, `rules_*.json`, the encoder, checker and K1 are unchanged.

### Phase 1 verification (Execute, cheap tier)

`output/scratch-28/verify_p1.py`, under the guard (log `runs/p1_verify.json`, output `verify_p1.out`):
- side table 776 rows / 776 unique full native keys;
- assignment table 776 / 776, key set equal to `phase3_membership.tsv` (342 + 434);
- 0 evidence-gap cells;
- extended dump 776 × 152 B, with 0 rows whose original 144 bytes differ from `dump_raw` or whose byte 144 ≠ 0;
- byte 145 equals the side-table code on all 776 rows;
- the classifier's `assign_completeness.u16` has 776 entries;
- the projection is O01, O04, O05, O06 and equals the source rule objects in order.

Tests: `test_dump_join_other_mechanism.py` + `test_dump_join_memory.py` gave **27 passed** under the guard (`runs/p1_tests.json`).

`artifact_feedback` was not called: workflow-service calls are excluded for this run by standing instruction. The report and brief were checked by hand against the rubric headings (done / departures / deferred / known problems).

**Phase 1 outcome verified.**

#### Carried

1. The DESIGN 34-versus-31 arithmetic on the 3-17 yardstick. Three rows are unexplained by the DESIGN sentence; record them in the plan record, not as a defect in the measurement.
2. The 3-17 per-row identity comparison is impossible (the inherited-byte table is deleted). Only aggregate candidates are listed.
3. The legacy-contract control (Open question 2) is skipped.
4. Phase 2 needs a bounded discriminator for each of the 7 O04 rows. Three are among the added 89 rows; the other four are not.

## Phase 2 — Every assignment joins to its proven plan-14 cause, with conflicts discriminated

Refine skipped (DESIGN). One unit, with its brief authored inline: `briefs/2-01-join-reconcile.md`.
